from netCDF4 import Dataset
import numpy as np
import json

mapping_file = '../grids/rmp_C40962_to_0.9x1.25_conserv.nc'
geocode_file = 'geocodes_40962.json'
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

def init_weights(mapping_ds):
    """
    reshape the weights provided by the remapping file into the form most
    suitable for use here: a map from target (geodesic) cells to the weights, and a 
    corresponding map from the target grid cells to the source cells
    """
    print('Initializing weights')
    S = mapping_ds.variables['S']
    a_inds = mapping_ds.variables['col']
    b_inds = mapping_ds.variables['row']
    a_to_s = {}
    a_to_b = {}
    for i in range(len(S)):
        if i % 10000 == 0:
            print(i)
        a_i = a_inds[i]
        b_i = b_inds[i]
        if a_i not in a_to_s:
            a_to_s[a_i] = []
            a_to_b[a_i] = []
        a_to_s[a_i].append(S[i])
        a_to_b[a_i].append(b_inds[i])

    return a_to_s, a_to_b

def add_variable_to_geodesic_data(geodesic_data, mapping_ds, vars_filename, var_info, a_to_s, a_to_b):
    """
    Adds a single variable defined on the source grid to the target (geodesic) grid,
    applying the remapping and weights appropriately.
    """
    ds = Dataset(vars_filename, 'r')
    varname = var_info['name']
    print('adding variable {}'.format(varname))
    var = ds.variables[varname][:]
    var = var.reshape([np.prod(var.shape), 1])
    for cell in geodesic_data:
        gi = cell['grid_index']
        if gi not in a_to_s or gi not in a_to_b:
            print('grid {} not found'.format(gi))
            continue
        w = np.array(a_to_s[gi])
        b_inds = a_to_b[gi]


        # assume 2D for now
        if varname.startswith('PCT_') or True:
            try:
                v = var[b_inds][:]
                v = v.reshape((v.shape[0],))
                a = mapping_ds.variables['area_b'][b_inds][:]
                cell['atts'][varname] = np.dot(np.multiply(v,a),w) / cell['area']
                # print(cell['atts'][varname])
            except IndexError as e:
                print(e)
        else:
            pass

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
add_geocodes_to_geodesic_data(geodesic_data, geocode_file)
a_to_s, a_to_b = init_weights(mapping_ds)
for sd in source_data:
    for v in sd['vars']:
        add_variable_to_geodesic_data(
            geodesic_data, mapping_ds, sd['filename'], v, a_to_s, a_to_b)

with open('geodesic_data.json', 'w') as fd:
    fd.write(json.dumps(geodesic_data, indent=2))
