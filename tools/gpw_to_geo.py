# Convert Gridded Population of the World data from TIFF format to the geodesic
# grid that we use

import gdal
import numpy as np
import pandas as pd
import json
from math import pi as PI
from math import sin, cos, acos, exp


DATA_DIR = '/Users/beau/Downloads/gpw-v4/'

def to_rad_pt(pt):
	return [to_rad(pt[0]), to_rad(pt[1])]

def to_rad(d):
    return ((d % 360) / 360) * 2 * PI

def dist(p1, p2):
    # https://en.wikipedia.org/wiki/Great-circle_distance
    t = sin(p1[0])*sin(p2[0]) + cos(p1[0])*cos(p2[0])*cos(abs(p1[1]-p2[1]))
    if t < 0.5:
        return 100
    return acos(t)

# Load country codes from CSV file; these were previously extracted from the GPW xlsx metadata 
print('Reading country codes')
codes_df = pd.read_csv(DATA_DIR+'country_codes.csv')
country_codes=dict(zip(list(codes_df['ISONumeric']), list(codes_df['Country or Territory Name'])))

print('Reading country data')
countries_ds = gdal.Open(DATA_DIR+'gpw-v4-national-identifier-grid.tif')
countries_a = np.array(countries_ds.ReadAsArray())
print(countries_a.shape)

lats = np.linspace(85, -60, 17400, False)
lons = np.linspace(-180, 180, 43200, False)

with open('../web/data/geodesic_data.json') as fd:
	geo_data = json.loads(fd.read())
geo_pts = [to_rad_pt([x['center'][1], x['center'][0]]) for x in geo_data]

geo_countries = [[] for i in range(40962)]
geo_gpw_pixels = [[] for i in range(40962)]

def backup(countries_data, gpw_pixels):
	output = [list(x) for x in countries_data]
	with open('countries_40962.json', 'w') as fd:
		fd.write(json.dumps(output))
	with open('gpw_pixels_40962.json', 'w') as fd:
		fd.write(json.dumps(gpw_pixels))


# find closest geo cell
for i in range(len(lats)):
	if i % 10 != 0:
		continue
	for j in range(len(lons)):
		if j % 10 != 0:
			continue
		country_code = str(int(countries_a[i, j]))
		country_name = country_codes.get(country_code, None)
		if not country_name:
			continue
		gpw_pt = to_rad_pt([lats[i], lons[j]])
		d = map(lambda x: dist(x, gpw_pt), geo_pts)
		gi = np.argmin(d)
		geo_gpw_pixels[gi].append([i, j])
		geo_countries[gi].append(country_name)
		print('({},{}):{} <=> {} = {} [{}]'.format(i, j, gpw_pt, geo_pts[gi], d[gi], country_name))

	print('backing up {}'.format(i))
	backup(geo_countries, geo_gpw_pixels)
