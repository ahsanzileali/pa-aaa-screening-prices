"""Parse the cms-hpt.txt index files (one per hospital or system website) into one list of location records."""
import json
import re
from _common import config

rows = []
for f in sorted((config.RAW / 'hpt_index').glob('*.txt')):
    dom = f.stem
    t = f.read_text(errors='ignore')
    if '<html' in t.lower()[:500]:
        continue
    cur = {'domain': dom}
    for line in t.splitlines():
        m = re.match(r'\s*([a-z-]+)\s*:\s*(.*)', line, re.I)
        if not m:
            continue
        k, v = m.group(1).lower(), m.group(2).strip()
        if k == 'location-name':
            if cur.get('location-name'):
                rows.append(cur)
            cur = {'domain': dom}
        cur[k] = v
    if cur.get('location-name'):
        rows.append(cur)
config.INTERIM.mkdir(parents=True, exist_ok=True)
json.dump(rows, open(config.INTERIM / 'hpt_rows.json', 'w'), indent=0)
print('index locations', len(rows))
