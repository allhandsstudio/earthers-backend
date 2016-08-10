"""
Create a geodesic data file suitable for display from source static data files,
remapping from a standard grid to the geodesic grid
"""

from netCDF4 import Dataset
import numpy as np
import json
import pickle

mapping_file = '../grids/rmp_C40962_to_0.9x1.25_conserv.nc'
weights_file = '../tools/remap_weights_0.9x1.25_to_C40962_at_0.01.pickle'
weights_file = '../tools/remap_weights_0.9x1.25_to_C40962.pickle'
geocode_file = '../data/geocodes_40962.json'
source_data = [
    {
        'filename': '../data/surfdata_0.9x1.25_simyr2000_c120319.nc',
        'vars': [
            {'name': 'PCT_URBAN', 'type': '2D'},
            {'name': 'PCT_GLACIER', 'type': '2D'},
            {'name': 'PCT_WETLAND', 'type': '2D'},
            {'name': 'PCT_LAKE', 'type': '2D'},
            {'name': 'SLOPE', 'type': '2D'},
            {'name': 'STD_ELEV', 'type': '2D'},
            {'name': 'SOIL_COLOR', 'type': '2D'},
            {'name': 'LANDFRAC_PFT', 'type': '2D'}
        ]
    }
]

plant_types = [
    "not vegetated",
    "needleleaf evergreen temperate tree",
    "needleleaf evergreen boreal tree",
    "needleleaf deciduous boreal tree",
    "broadleaf evergreen tropical tree",
    "broadleaf evergreen temperate tree",
    "broadleaf deciduous tropical tree",
    "broadleaf deciduous temperate tree",
    "broadleaf deciduous boreal tree",
    "broadleaf evergreen shrub",
    "broadleaf deciduous temperate shrub",
    "broadleaf deciduous boreal shrub",
    "c3 arctic grass",
    "c3 non-arctic grass",
    "c4 grass",
    "corn",
    "wheat"   
]

def init_geodesic_data(mapping_ds):
    print('Initializing geodesic data')
    xc = mapping_ds.variables['xc_a']
    yc = mapping_ds.variables['yc_a']
    xv = mapping_ds.variables['xv_a']
    yv = mapping_ds.variables['yv_a']
    area = mapping_ds.variables['area_a']
    # print(xc[0:10])
    data = []
    for i in range(len(xc)):
        if i % 10000 == 0:
            print(i)
        cell = {
            'grid_index': i,
            'center': (xc[i], yc[i]),
            'vertices': list(zip(xv[i], yv[i])),
            'area': area[i],
            'atts': {}
        }
        if len(set(cell['vertices'])) == 5:
            cell['shape'] = 'pentagon'
        else:
            cell['shape'] = 'hexagon'
        data.append(cell)
    return data


def add_variable_to_geodesic_data(geodesic_data, vars_filename, varname, W, I):
    """
    Adds a single variable defined on the source grid to the target (geodesic) grid,
    applying the remapping and weights appropriately.
    """
    ds = Dataset(vars_filename, 'r')
    print('adding variable {}'.format(varname))
    var = ds.variables[varname][:]
    var = var.reshape((np.prod(var.shape), ))
    for cell in geodesic_data:
        gi = cell['grid_index']
        cell['atts'][varname] = np.dot(var[I[gi]], W[gi])


def add_geocodes_to_geodesic_data(geodesic_data, geocode_file):
    print('Adding place names from {}'.format(geocode_file))
    with open(geocode_file, 'r') as fd:
        geocodes = json.loads(fd.read())
        for cell in geodesic_data:
            gi = str(cell['grid_index'])
            if gi in geocodes and geocodes[gi]:
                cell['location_name'] = geocodes[gi]


mapping_ds = Dataset(mapping_file, 'r')
geodesic_data = init_geodesic_data(mapping_ds)
weights = pickle.load(open(weights_file, 'r'))
W = weights['W']
I = weights['I']
add_geocodes_to_geodesic_data(geodesic_data, geocode_file)
for sd in source_data:
    for v in sd['vars']:
        add_variable_to_geodesic_data(
            geodesic_data, sd['filename'], v['name'], W, I)

with open('geodesic_data.json', 'w') as fd:
    fd.write(json.dumps(geodesic_data, indent=2))
