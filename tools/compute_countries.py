import json
from collections import Counter

def argmax(c):
    mx = 0
    amx = None
    for k, v in c.items():
        if v > mx:
            amx = k
    return amx

with open('countries_40962.json', 'r') as fd:
    raw = json.loads(fd.read())

with open('../web/data/geodesic_data.json', 'r') as fd:
    geo = json.loads(fd.read())

countries = []
for gi in range(len(raw)):
    n = len(raw[gi])
    if n == 0:
        countries.append({})
    else:
        c = Counter(raw[gi])
        am = argmax(c)
        countries.append({'country': am})

with open('geodesic_countries.json', 'w') as fd:
    fd.write(json.dumps(countries, indent=2))
