'''
Import only module. Material definition for transient model.

Dependencies:
CoolProp for material properties
'''

from CoolProp.CoolProp import PropsSI  # Assuming that the solution is approximated by water

class Material():
    '''Generic class for the material in question, and associated geometry'''
    def __init__(self, matnum, elems, ndens, height, base_height, radius, temp=300):
        self.matnum = matnum
        self.elems = elems
        self.ndens = ndens  # a/b-cm
        self.temp = temp  # K
        self.height = height  # cm
        self.base_height = base_height  # cm
        self.radius = radius  # cm
        self.volume = 0.0  # cm^3, placeholder until calculated
        self.base = 0.0  # cm, placeholder until calculated
        self.mass = 0.0  # g, placeholder until calculated
        self.delta_temp = 0.0  # K, placeholder until required for expansion
        self.atoms = [0.0] * len(ndens)  # _, placeholder until calculated
        # Pressure: Assume atmospheric conditions (allow for expansion of fluid)
        self.pressure = 101325  # Pa

    def append_volume_mass_init(self, volume, mass):
        '''Append a material volume after the initial file calculation: USE ONCE'''
        self.volume = volume  # cm^3
        self.mass = mass  # g
        self.__calc_init()

    def append_height(self, newheight):
        '''Append a new volume after adjusting height'''
        self.height = newheight  # cm
        self.volume = self.base * self.height  # cm
        self.__update()

    def calc_temp(self, fissions):
        '''Adjust material temperature'''
        heatgen = fissions * 180 * 1.6022e-13  # J
        spec_heat = PropsSI('C', 'T', self.temp, 'P', self.pressure, 'WATER')  # J/kg-K
        newtemp = self.temp + heatgen / (self.mass / 1e3) / spec_heat  # K
        self.delta_temp = newtemp - self.temp  # K
        self.temp = newtemp  # K

    def expand(self):
        '''Self-regulate the expansion of the material'''
        # The isobaric expansion coefficient of water is calculated
        expansion = PropsSI('ISOBARIC_EXPANSION_COEFFICIENT', 'T', self.temp,
                            'P', self.pressure, 'WATER')  # 1/K
        # Coefficient is defined as: alpha = 1/V * (dV/dT) over constant P
        # Where V is volume, T is temperature, P is pressure, and alpha is the coefficient
        # In this case, changing differential into delta, and solving for a delta height
        # while maintaining base area
        delta_height = self.delta_temp * self.volume * expansion / self.base  # cm
        newheight = self.height + delta_height  # cm
        self.append_height(newheight)  # Book-keeping for number densities and such

    def __calc_init(self):
        '''Self-called method to calculate some constants after initial file run'''
        # Ideally only called ONE time after each material definition
        self.atoms = [nden * 1e24 * self.volume for nden in self.ndens]  # a
        self.base = self.volume / self.height  # cm^2

    def __update(self):
        '''Self-called method to update the number densities'''
        self.ndens = [atom * 1e-24 / self.volume for atom in self.atoms]  # a/b-cm

    def __str__(self):
        # Material representation, overload built-in string definition
        ret = ""
        template = " {0}       {1} 0 {2} {3}   end\n"
        for ind, elem in enumerate(self.elems):
            ret += template.format(elem, self.matnum, self.ndens[ind], self.temp)
        return ret  # str

    def geometry_string(self):
        '''Returns the geometry definition of the material'''
        template = " cylinder {0}       {1}       {2}        {3}\n"
        return template.format(self.matnum, self.radius, self.height, self.base_height)  # str
