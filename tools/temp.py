from netCDF4 import Dataset
import json
import numpy as np
import pickle

target_grids = ['C10242', 'C40962']
source_grids = ['4x5', '1.9x2.5', '0.9x1.25']
target_grids = ['C40962']
source_grids = ['4x5']

for target_grid in target_grids:
    for source_grid in source_grids:
        remap_file = '../grids/rmp_{}_to_{}_conservative.nc'.format(target_grid, source_grid)
        print(remap_file)

        rmp_ds = Dataset(remap_file, 'r')
        S = rmp_ds.variables['S']
        a_inds = rmp_ds.variables['col']
        b_inds = rmp_ds.variables['row']
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
            a_to_b[a_i].append(b_inds[i] - 1)

        for k, v in a_to_s.items():
            a_to_s[k] = np.array(a_to_s[k])

        b_areas = {}
        for gi in range(1, rmp_ds.variables['xc_a'].shape[0] + 1):
            b_inds = a_to_b[gi]
            b_areas[gi] = rmp_ds.variables['area_b'][b_inds][:]

        output = {
            'a_to_s': a_to_s,
            'a_to_b': a_to_b,
            'area_a': rmp_ds.variables['area_a'][:],
            'b_areas': b_areas,
            'target_size': rmp_ds.variables['xc_a'].shape[0] + 1
        }

        with open('remap_data_{}_to_{}.pickle'.format(source_grid, target_grid), 'wb') as fd:
            pickle.dump(output, fd, 2)
