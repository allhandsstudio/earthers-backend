from netCDF4 import Dataset
import json
import subprocess
import numpy as np
from math import pi as PI
from math import sin, cos, acos, exp
import pickle

# src_grid = '0.9x1.25'
src_grid = '4x5'
src_file = '../grids/fv{}.nc'.format(src_grid)
src_ds = Dataset(src_file, 'r')

tgt_grid = 'C40962'
tgt_file = '../grids/{}.global.nc'.format(tgt_grid)
tgt_ds = Dataset(tgt_file, 'r')

# sigma = .005 # for 0.9x1.25
sigma = .05  # for 4x5

def to_deg(r):
    return ((r % 2*PI) / (2*PI)) * 360 - 180

def to_rad(d):
    return ((d % 360) / 360) * 2 * PI - (PI/24)

def dist(p1, p2):
    # https://en.wikipedia.org/wiki/Great-circle_distance
    t = sin(p1[0])*sin(p2[0]) + cos(p1[0])*cos(p2[0])*cos(abs(p1[1]-p2[1]))
    if t < 0.5:
        return 100
    return acos(t)

def get_weight(d):
    return exp(-.5 * pow((d/sigma), 2))

print('zipping')
tgt_points = list(zip(tgt_ds.variables['grid_center_lat'][:], tgt_ds.variables['grid_center_lon'][:]))

src_points = [(to_rad(x[0]), to_rad(x[1]))
    for x in list(zip(src_ds.variables['grid_center_lat'][:], src_ds.variables['grid_center_lon'][:]))]

print('computing distances')
distances = []
for j in range(len(tgt_points)):
    if j % 1000 == 0:
        print(j)
    # print(pt)
    pt = tgt_points[j]
    dists = [dist(src_points[i], pt) for i in range(len(src_points))]
    deltas = [(i, src_points[i], dists[i]) for i in range(len(src_points)) if dists[i] < 4*sigma]
    deltas.sort(key=lambda x: x[2], reverse=True)
    distances.append(deltas)

print('computing indexes')
I = [[a[0] for a in x] for x in distances]

print('computing weights')
W = [[get_weight(a[2]) for a in x] for x in distances]
for i in range(len(W)):
    a = W[i]
    s = sum(a)
    W[i] = [x/s for x in a]
    # print(max(W[i]))
    # print(len(W[i]))

print('saving')
output = {
    "W": W,
    "I": I,
    "src": src_grid,
    "tgt": tgt_grid,
    "sigma": sigma
}

pickle_file = 'remap_weights_{}_to_{}.pickle'.format(src_grid, tgt_grid, sigma)
with open(pickle_file, 'wb') as fd:
    pickle.dump(output, fd, pickle.HIGHEST_PROTOCOL)