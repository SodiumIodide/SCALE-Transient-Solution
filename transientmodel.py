#!/usr/bin/env python3

'''
A transient model for critical solution systems.

By Corey Skinner.

Dependencies:
re for regular expression pattern matching in output files
os for calling the batch6.1 process via command interface, file existence for debug
numpy for arrays and mathematical methods
coolprop for water properties (assuming aqueous mixture is approximated by water)
    - Imported in module file "tm_material"
'''

# External
import re
from os import system, path
import numpy as np

# Shared
from tm_material import Material  # Requires CoolProp
import tm_constants as c
import tm_fileops as fo

def set_materials(elems, ndens, tot_height, tot_radius, **kwargs):
    '''Return a list of materials and geometries'''
    mat_counter = 1  # Materials begin with number 1
    base_height = 0  # cm, start at planar origin
    materials = []  # Two dimensional list of materials for return
    for height in calc_heights(tot_height):
        h_list = []  # Second dimension empty list for appending
        for radius in calc_radii(tot_radius):
            if 'temp' in kwargs:
                temperature = kwargs['temp'][mat_counter - 1]
                h_list.append(Material(mat_counter, elems, ndens, height,
                                       base_height, radius, temperature))
            else:
                h_list.append(Material(mat_counter, elems, ndens, height, base_height, radius))
            mat_counter += 1
        base_height = height
        materials.append(h_list)
    return materials

def propagate_neutrons(k_eff, lifetime, neutrons):
    '''Propagate the number of neutrons over delta-t'''
    return neutrons * np.exp((k_eff - 1)/lifetime * c.DELTA_T)

# This function is largely present for refactoring purposes
def increase_height(height, incr):
    '''Return an incremented height'''
    return height + incr  # cm

def calc_heights(tot_height):
    '''Returns a list of the ranges of height based on total'''
    height_diff = tot_height / c.NUM_AXIAL  # cm
    heights = list(map(lambda ind: ind * height_diff, range(1, c.NUM_AXIAL + 1)))  # cm
    return heights  # cm

def calc_radii(tot_rad):
    '''Returns a list of the ranges of radii based on total'''
    rad_diff = tot_rad / c.NUM_RADIAL  # cm
    radii = list(map(lambda ind: ind * rad_diff, range(1, c.NUM_RADIAL + 1)))  # cm
    return radii  # cm

def main():
    '''Main wrapper'''
    print("\nWelcome to the Transient Solution Modeling software.")
    print("Developed by Corey Skinner for the purposes of a revision of")
    print("DOE-HDBK-3010, Chapter 6: Accidental Criticality using the Python 3.6")
    print("programming language in 2017.")
    print("\nPlease enter a filename ('.inp' will be appended):")
    filename = input(">>> ")
    if not filename.endswith(".inp"):
        filename += ".inp"
    if not filename.strip():
        print("Must include a filename...")
        raise ValueError
    tot_height = c.INIT_HEIGHT  # cm
    tot_radius = c.RAD  # cm
    # Parallel arrays for materials
    elems = ["h", "n", "o", "u-234", "u-235", "u-236", "u-238"]
    ndens = [6.258e-2, 1.569e-3, 3.576e-2, 1.060e-6, 1.686e-4, 4.350e-7, 1.170e-5]  # a/b-cm
    # Uranyl nitrate
    materials = set_materials(elems, ndens, tot_height, tot_radius)
    print("Running preliminary file, to determine masses, volumes, etc...")
    timer = 0 #s
    fo.write_file(filename, materials, tot_height, volcalc=True)
    outfilename = filename.replace("inp", "out")
    if not path.isfile(outfilename):
        system("batch6.1 {}".format(filename))
    volumes = fo.get_volumes(outfilename)  # cm^3
    masses = fo.get_masses(outfilename)  # g
    counter = 0  # Two dimensional loops prevent use of enumerate()
    temperatures = []  # K
    for material_layer in materials:
        for material in material_layer:
            material.append_volume_mass_init(volumes[counter], masses[counter])
            temperatures.append(material.temp)
            counter += 1
    maxtemp = max(temperatures)  # K
    total_neutrons = c.INIT_NEUTRONS  # Start of the flux
    lifetime, keff, keffmax, nubar = fo.get_transient(outfilename)  # s, _, _
    timer = 0  # s
    total_fissions = total_neutrons / nubar
    # Start results file
    with open("results.txt", 'w') as resfile:
        resfile.write("Time (s), Number of Fissions, Max Temperature, " + \
                      "Neutron Lifetime (s), k-eff, k-eff+2sigma\n")
    fo.record(timer, total_fissions, maxtemp, lifetime, keff, keffmax)
    # Material addition loop
    print("Beginning main calculation...")
    # while keff < 1.01:
    #     # Proceed in time
    #     timer += c.DELTA_T  # s
    #     # Read previous output file for information and calculate new changes
    #     fission_profile = fo.count_fissions(outfilename)
    #     total_neutrons = propagate_neutrons(keff, lifetime, total_neutrons)
    #     # Correlation between flux profile and fission density
    #     fissions = [frac * total_neutrons / nubar for frac in fission_profile]
    #     total_fissions = sum(fissions)
    #     # Increase total height, requires creating new material information
    #     tot_height = increase_height(tot_height, 0.2)  # cm
    #     # Re-apply materials with incresed height
    #     # (Adding material to system, maintaining even dimension split)
    #     materials = set_materials(elems, ndens, tot_height, tot_radius, temp=temperatures)
    #     filename = re.sub(r'\d', r'', filename.strip(".inp")) + \
    #                re.sub(r'\.', r'', str(round(timer, abs(c.TIMESTEP_MAGNITUDE) + 1))) + \
    #                ".inp"
    #     # Allow SCALE to calculate volumes to account for increasing mass
    #     fo.write_file(filename, materials, tot_height, volcalc=True)
    #     system("batch6.1 {}".format(filename))
    #     outfilename = filename.replace("inp", "out")
    #     volumes = fo.get_volumes(outfilename)  # cm^3
    #     masses = fo.get_masses(outfilename)  # g
    #     lifetime, keff, keffmax, nubar = fo.get_transient(outfilename)
    #     temperatures = []  # K, reset of list
    #     counter = 0  # Two dimensional loops prevent use of enumerate()
    #     for material_layer in materials:
    #         for material in material_layer:
    #             material.append_volume_mass_init(volumes[counter], masses[counter])
    #             material.calc_temp(fissions[counter])
    #             temperatures.append(material.temp)  # K
    #             counter += 1
    #     maxtemp = max(temperatures)
    #     fo.record(timer, total_fissions, maxtemp, lifetime, keff, keffmax)
    #     print("Current time: {} s".format(round(timer, abs(c.TIMESTEP_MAGNITUDE) + 1)))
    #     print("Current k-eff: {}".format(keff))
    #     print("Maximum k-eff: {}".format(keffmax))
    #     print("Number of fissions: {0:E}".format(sum(fissions)))
    #     print("Maximum temperature: {}".format(maxtemp))
    # Material expansion loop
    # print("Finished adding material. Now expanding system by temperature...")
    # Store heights in two-dimensional matrix
    heights = np.zeros([c.NUM_AXIAL, c.NUM_RADIAL])
    for ax_ind, material_layer in enumerate(materials):
        for rad_ind, material in enumerate(material_layer):
            heights[ax_ind, rad_ind] = material.height
    # with open("results.txt", 'a') as appfile:
        # appfile.write("# Expanding material #\n")
    while keff > 1.0:
        # Proceed in time
        timer += c.DELTA_T  # s
        # Read previous output file for information and calculate new changes
        fission_profile = fo.count_fissions(outfilename)
        total_neutrons = propagate_neutrons(keff, lifetime, total_neutrons)
        # Correlation between flux profile and fission density
        fissions = [frac * total_neutrons / nubar for frac in fission_profile]
        total_fissions = sum(fissions)
        # Begin total expansion of material
        for ax_ind, material_layer in enumerate(materials):
            for rad_ind, material in enumerate(material_layer):
                if ax_ind != 0:
                    height_shift = heights[ax_ind - 1, rad_ind] - material.base_height
                    material.base_height = heights[ax_ind - 1, rad_ind]
                    material.height += height_shift
                material.expand()
                heights[ax_ind, rad_ind] = material.height
                # Keep checks on total height such that void data doesn't get overwritten
                if tot_height < material.height:
                    tot_height = material.height
        filename = re.sub(r'\d', r'', filename.strip(".inp")) + \
                   re.sub(r'\.', r'', str(round(timer, abs(c.TIMESTEP_MAGNITUDE) + 1))) + \
                   ".inp"
        # Do not need to recalculate masses (thus volumes) for materials at this stage
        fo.write_file(filename, materials, tot_height, volcalc=True)
        system("batch6.1 {}".format(filename))
        outfilename = filename.replace("inp", "out")
        lifetime, keff, keffmax, nubar = fo.get_transient(outfilename)
        temperatures = []  # K, reset of list
        counter = 0  # Two dimensional loops prevent use of enumerate()
        for material_layer in materials:
            for material in material_layer:
                material.calc_temp(fissions[counter])
                temperatures.append(material.temp)  # K
                counter += 1
        maxtemp = max(temperatures)
        fo.record(timer, total_fissions, maxtemp, lifetime, keff, keffmax)
        print("Current time: {} s".format(round(timer, abs(c.TIMESTEP_MAGNITUDE) + 1)))
        print("Current k-eff: {}".format(keff))
        print("Maximum k-eff: {}".format(keffmax))
        print("Number of fissions: {0:E}".format(sum(fissions)))
        print("Maximum temperature: {}".format(maxtemp))

if __name__ == '__main__':
    try:
        main()
    except ValueError:
        pass
    finally:
        print("\nProgram terminated\n")
