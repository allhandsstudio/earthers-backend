import json
import gdal
import numpy as np

DATA_DIR = '/Users/beau/Downloads/gpw-v4/'

print('Reading pixel data')
with open('gpw_pixels_40962.json', 'r') as fd:
    pixels = json.loads(fd.read())

print('Reading population data')
pop_ds = gdal.Open(DATA_DIR+'gpw-v4-population-count-adjusted-to-2015-unwpp-country-totals_2015.tif')
pop_a = np.array(pop_ds.ReadAsArray())
print(pop_a.shape)

M = pop_a.shape[0]
N = pop_a.shape[1]
pops = []
for gi in range(len(pixels)):
    pop = 0
    for p in pixels[gi]:
        for i in range(p[0]-5, p[0]+5):
            for j in range(p[1]-5, p[1]+5):
                if i < 0 or i >= M or j < 0 or j >= N:
                    continue
                x = pop_a[i][j]
                if x > 0:
                    pop += x
    pops.append({ 'population_2015': pop })
    print('{:05} {}'.format(gi, pop))

with open('geodesic_populations.json', 'w') as fd:
    fd.write(json.dumps(pops, indent=2))

