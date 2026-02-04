import ast
import glob
import sys

root = r"c:/Users/sagar/Documents/PCAN_Auto/app"
files = glob.glob(root + "/**/*.py", recursive=True)
fails = []
for f in files:
    try:
        s = open(f, 'rb').read()
        ast.parse(s, filename=f)
    except Exception as e:
        fails.append((f, str(e)))

print('checked', len(files), 'files')
print('fail_count=', len(fails))
for p, e in fails:
    print(p, '->', e)

if fails:
    sys.exit(2)
else:
    sys.exit(0)
