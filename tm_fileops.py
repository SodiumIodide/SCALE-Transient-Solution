'''Import only module. Contains operations on input and output files.'''

import re
import tm_constants as c

def count_fissions(filename):
    '''Read an output file to determine the fission (flux) distribution'''
    pat = re.compile(r'\s+\d?\s+?(\d+)\s+(\S+)\s+\S+\s+(\S+)')
    fissionsum = 0
    profile = [0] * c.NUM_MATERIALS
    with open(filename, mode='r') as ofile:
        found = False
        for line in ofile:
            if not found:
                if "**** fission densities ****" in line:
                    found = True
            else:
                if "frequency" in line:
                    found = False
                if re.match(pat, line):
                    matches = re.findall(pat, line)
                    # Avoid geometric wrapper geometry (void)
                    if int(matches[0][0]) != c.NUM_MATERIALS + 1:
                        fissionsum += float(matches[0][2])
                        profile[int(matches[0][0]) - 1] = float(matches[0][2])
    for ind in range(c.NUM_MATERIALS):
        profile[ind] /= fissionsum
    return profile  # [_]

def get_transient(filename):
    '''
    Read an output file to determine the k-eff and neutron lifetime
    Returns tuple of lifetime, k-eff, and maximum k-eff
    '''
    ltpat = re.compile(r'\slifetime\s=\s+(\S+)\s')
    kepat = re.compile(r'k-eff\s+(\S+)\s\+\sor\s-\s(\S+)')
    nbpat = re.compile(r'system\snu\sbar\s+(\S+)\s')
    with open(filename, mode='r') as ofile:
        for line in ofile:
            if "lifetime" in line:
                matches = re.findall(ltpat, line)
                lifetime = float(matches[0])  # s
            if "best estimate system k-eff" in line:
                matches = re.findall(kepat, line)
                keff = float(matches[0][0])
                maxkeff = round(keff + 2 * float(matches[0][1]), 5)
            if "system nu bar" in line:
                matches = re.findall(nbpat, line)
                nubar = float(matches[0])  # n/fis
    return (lifetime, keff, maxkeff, nubar)  # s, _, _, n/fis

def get_volumes(filename):
    '''Read an output file to determine the material volumes'''
    pat = re.compile(r'\s+\d?\s*\d?\s*\d+\s+(\d+)\s+(\S+)')
    volumes = [0.0] * c.NUM_MATERIALS
    with open(filename, mode='r') as ofile:
        found = False
        for line in ofile:
            if not found:
                if "total region volume" in line:
                    found = True
            else:
                if "total mixture volume" in line:
                    found = False
                if re.match(pat, line):
                    matches = re.findall(pat, line)
                    if int(matches[0][0]) != 0:
                        volumes[int(matches[0][0]) - 1] = float(matches[0][1])  # cm^3
    return volumes  # [cm^3]

def get_masses(filename):
    '''Read an output file to determine the material density'''
    pat = re.compile(r'\s+(\d+)\s+\S+\s\+/-\s\S+\s+(\S+)')
    masses = [0.0] * c.NUM_MATERIALS
    with open(filename, mode='r') as ofile:
        found = False
        for line in ofile:
            if not found:
                if "total mixture volume" in line and "total mixture mass" in line:
                    found = True
            else:
                if "biasing information" in line:
                    found = False
                if re.match(pat, line):
                    matches = re.findall(pat, line)
                    masses[int(matches[0][0]) - 1] = float(matches[0][1])
    return masses


def write_file(filename, materials, tot_height, volcalc=False):
    '''Function to create the series of input files'''
    with open(filename, mode='w') as fhan:
        fhan.write("'Input generated for SCALE 6.1 by TransientModel.py\n")
        fhan.write("'batch_args \\-m\n")
        # Cross-section parsing with CSAS6
        fhan.write("=csas6\n")
        fhan.write("solutionmodel\n")
        # ENDF-B VII cross section library with 238 groups
        fhan.write("v7-238\n")
        fhan.write("read composition\n")
        # Material data
        for material_level in materials:
            for material in material_level:
                fhan.write(str(material))
        fhan.write("end composition\n")
        # Cross section processing
        fhan.write("read celldata\n")
        fhan.write("  multiregion cylindrical left_bdy=reflected right_bdy=vacuum end\n")
        fhan.write("           1           {}  \n".format(c.RAD))
        fhan.write("      end zone\n")
        fhan.write("end celldata\n")
        fhan.write("read parameter\n")
        # A restart file is not necessary, but the number of material interfaces
        # affects the results of k-eff from boundary calculation residuals
        # (i.e. a solid cylinder will produce a different numerical value than
        # a cylinder broken into three or nine material segments)
        # An attempted alleviation is included by increasing the standard number
        # of calculational generations from 203
        fhan.write(" gen=406\n")
        fhan.write(" htm=no\n")
        fhan.write(" wrs=35\n")
        fhan.write("end parameter\n")
        # Geometry
        fhan.write("read geometry\n")
        fhan.write("global unit 1\n")
        fhan.write("com=\"global unit 1\"\n")
        for ind, material_level in enumerate(materials):
            for material in material_level:
                fhan.write(material.geometry_string())
        # Encasing geometry for boundary
        fhan.write(" cylinder {0}       {1}       {2}       -1\n"
                   .format(c.NUM_MATERIALS + 1, c.RAD + 1, tot_height + 1))
        # Materials and media
        for material_level in materials:
            for ind, material in enumerate(material_level):
                fhan.write(" media {0} 1 {0}".format(material.matnum))
                if ind != 0:
                    fhan.write(" -{}\n".format(material.matnum - 1))
                else:
                    fhan.write("\n")
        fhan.write(" media 0 {}".format(c.NUM_MATERIALS + 1))
        # Void material in encasing geometry
        for num in range(1, c.NUM_MATERIALS + 1):
            if num % c.NUM_RADIAL == 0:
                fhan.write(" -{}".format(num))
        fhan.write("\n")
        fhan.write(" boundary {}\n".format(c.NUM_MATERIALS + 1))
        fhan.write("end geometry\n")
        if volcalc:
            fhan.write("read volume\n")
            fhan.write("  type=trace\n")
            fhan.write("end volume\n")
        fhan.write("end data\n")
        fhan.write("end\n")

def record(time, numfissions, maxt, lifetime, keff, keffmax):
    '''Record current step to a results file'''
    with open("results.txt", 'a') as appfile:
        appfile.write("{0}, {1:E}, {2}, {3}, {4}, {5}\n"
                      .format(round(time, abs(c.TIMESTEP_MAGNITUDE) + 1),
                              numfissions, maxt, lifetime, keff, keffmax))
