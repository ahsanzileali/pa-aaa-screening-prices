"""Combine the hospital list with the extraction results into one hospital-level price table."""
import json
import pandas as pd
from _common import config, url_hash

STEMS = {'391304': 'bucktail', '390268': 'mountnittany', '391308': 'corry'}
FIELDS = [('gross', 'gross charge'), ('cash', 'cash price'), ('min', 'min negotiated'), ('median_neg', 'median negotiated'), ('max', 'max negotiated')]

h = pd.read_csv(config.REF / 'hospital_list.csv', dtype=str).fillna('')
out = []
for _, r in h.iterrows():
    rec = r.to_dict()
    u = r['Price file link (MRF)']
    stem = STEMS.get(r['CCN']) or (url_hash(u) if u else None)
    p = config.EXTRACTION / f'{stem}.json' if stem else None
    note, found = '', []
    if not p or not p.exists():
        note = 'No file processed'
    else:
        d = json.load(open(p))
        if d['error']:
            note = 'Could not read file: ' + d['error']
        else:
            for c in config.CODES:
                v = d['codes'][c]
                if v['rows']:
                    found.append(c)
                for k, lab in FIELDS:
                    val = v.get(k)
                    rec[f'{c} {lab}'] = round(val, 2) if val else None
            note = 'Codes not listed in file' if not found else ''
            odd = [c for c in config.CODES if d['codes'][c].get('max') and d['codes'][c].get('gross') and d['codes'][c]['max'] > 5 * d['codes'][c]['gross']]
            if odd:
                note = f"Max negotiated for {', '.join(odd)} is over 5 times the gross charge (likely a bundled or case rate); use median negotiated"
            mods = sorted({d['codes'][c].get('modifier_used') for c in config.CODES if d['codes'][c].get('modifier_used')})
            if mods:
                note = (note + '; ' if note else '') + f"Prices are from {'/'.join(mods)} modifier rows (no unmodified row listed)"
    rec['Codes found'] = ', '.join(found)
    rec['Extraction note'] = note
    out.append(rec)
cols = list(h.columns) + [f'{c} {lab}' for c in config.CODES for _, lab in FIELDS] + ['Codes found', 'Extraction note']
df = pd.DataFrame(out).reindex(columns=cols)
df.to_csv(config.DERIVED / 'hospital_prices.csv', index=False)
g = df[(df['CMS type'] == 'Acute care') & (df['Specialty hospital'] == 'No') & (df['Link status'] != 'Closed')]
print('hospitals', len(df), 'general acute', len(g), 'with 76706 price', g['76706 median negotiated'].notna().sum() + 0,
      'listing 76706', g['Codes found'].str.contains('76706').sum())
