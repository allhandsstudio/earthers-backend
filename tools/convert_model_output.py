"""
Convert the time-series output of a single variable from a model run to 
a geodesic map suitable for display
"""

from netCDF4 import Dataset
import json
import subprocess
import numpy as np

s3_bucket = 'cesm-output-data'
# run_id = 'i-d4c62640'
# run_id = 'i-ae73943a'
run_id = 'i-5240bec6'
model = 'atm'
varname = 'TS'

# remap_file = '../grids/rmp_C40962_to_4x5_conservative.nc'
remap_file = '../grids/rmp_C40962_to_1.9x2.5_conservative.nc'

s3_url = 's3://{}/{}/output/{}/ts_{}.nc'.format(s3_bucket, run_id, model, varname)
local_nc_file = 'run_{}_ts_{}.nc'.format(run_id, varname)
print('copying to {}'.format(local_nc_file))
subprocess.run('aws s3 cp {} {}'.format(s3_url, local_nc_file), shell=True)

var_ds = Dataset(local_nc_file, 'r')
rmp_ds = Dataset(remap_file, 'r')

# print(rmp_ds.variables['area_a'][:])

print('Initializing weights')
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

# print(a_to_b)
# import sys
# sys.exit(0)

b_areas = {}
for gi in range(1, rmp_ds.variables['xc_a'].shape[0] + 1):
    b_inds = a_to_b[gi]
    b_areas[gi] = rmp_ds.variables['area_b'][b_inds][:]

print('Mapping variable')
output = {}
var = var_ds.variables[varname]
for i in range(var.shape[0]):
    d = int(var_ds['time'][i])
    print('time {}'.format(d))
    output[d] = [0] * (rmp_ds.variables['xc_a'].shape[0] + 1)   
    var_slice = var[i][:].reshape([np.prod(var.shape[1:]), 1])
    for gi in range(1, rmp_ds.variables['xc_a'].shape[0]):
        if gi not in a_to_s or gi not in a_to_b:
            print('grid {} not found'.format(gi))
            continue
        w = a_to_s[gi]
        b_inds = a_to_b[gi]
        try:
            v = var_slice[b_inds][:]
            v = v.reshape((v.shape[0],))
            a = b_areas[gi]
            output[d][gi] = np.dot(np.multiply(v,a),w) / rmp_ds.variables['area_a'][gi]
        except IndexError as e:
            print('error {}'.format(gi))
            print(e)

with open('run_{}_ts_{}.json'.format(run_id, varname), 'w') as fd:
    fd.write(json.dumps(output, indent=2))

