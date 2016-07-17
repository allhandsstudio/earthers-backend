import json
import requests
from netCDF4 import Dataset

rmp_file = '../grids/rmp_C40962_to_0.9x1.25_conserv.nc'
ds = Dataset(rmp_file, 'r')
xc = ds.variables['xc_a'][:]
yc = ds.variables['yc_a'][:]

URL = 'https://search.mapzen.com/v1/reverse?api_key=search-uuTGMMB&point.lat={}&point.lon={}'

locations = {}
errors = 0
for i in range(len(xc)):
    if i % 100 == 0:
        print(i)
    lat = yc[i]
    lon = xc[i]
    if lon > 180:
        lon = lon - 360

    resp = None
    try:
        resp = requests.get(URL.format(lat, lon))
    except:
        errors += 1
        print('error 1')
        if errors > 5:
            print('too many errors; exiting')
            break
        else:
            continue

    if resp.status_code == 429:
        print('429 seen; saving and exiting')
        break
    elif resp.status_code != 200:
        print('{} for {} {}'.format(resp.status_code, lat, lon))
        continue
    obj = resp.json()
    if len(obj['features']) == 0:
        # print('no location found for {} {}'.format(lat, lon))
        locations[i] = None
    else:
        # print('{} features found for {} {}'.format(len(obj['features']), lat, lon))
        feature = obj['features'][0]['properties']
        if 'region' in feature and 'country' in feature:
            locations[i] = '{}, {}'.format(feature['region'], feature['country'])
            print(locations[i])
        else:
            print('region and country not found')

with open('geocodes.json','w') as fd:
    fd.write(json.dumps(locations, indent=2))
