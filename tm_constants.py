'''
Import only module. Contains constants for the Python calculations.
'''

TIMESTEP_MAGNITUDE = -3
DELTA_T = 10**TIMESTEP_MAGNITUDE  # s
INIT_NEUTRONS = 1e10  # Small initiating fission accident source -> Flux build-up
SPEC_HEAT = 0.82 * 4186  # J/g-C
DENS = 1.161  # g/cm^3
INIT_HEIGHT = 53  # cm
RAD = 15  # cm
NUM_AXIAL = 4
NUM_RADIAL = 3
NUM_MATERIALS = NUM_AXIAL * NUM_RADIAL  # Equivalent to the number of regions in the model
