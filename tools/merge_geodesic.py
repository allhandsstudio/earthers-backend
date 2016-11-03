import json
import sys

file1 = sys.argv[1]
file2 = sys.argv[2]
# file3 = sys.argv[3]

with open(file1, 'r') as fd:
    obj1 = json.loads(fd.read())
with open(file2, 'r') as fd:
    obj2 = json.loads(fd.read())

if len(obj1) != 40962:
    print('wrong file1 object size {}'.format(len(obj1)))
if len(obj2) != 40962:
    print('wrong file2 object size {}'.format(len(obj2)))

for gi in range(40962):
    obj1[gi].update(obj2[gi])

# with open(file3, 'w') as fd:
#     fd.write(json.dumps(obj1, indent=2))
print(json.dumps(obj1, indent=2))
