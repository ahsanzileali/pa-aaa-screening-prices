"""Download one hospital price file and pull AAA ultrasound codes.
Usage: extract.py URL OUT.json WORKDIR"""
import sys, os, json, csv, re, subprocess, zipfile, io, statistics, time

CODES = {'76706', '76770', '76775'}
csv.field_size_limit(2**31 - 1)
url, out, work = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(work, exist_ok=True)
tmp = os.path.join(work, 'f.bin')


def num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r'[$,\s]', '', str(v))
    try:
        x = float(s)
        return x if x > 0 else None
    except ValueError:
        return None


def new():
    return {'rows': 0, 'settings': set(), 'desc': set(), 'gross': [], 'cash': [], 'min': [], 'max': [], 'neg': []}


res = {c: {'none': new(), 'mod': new()} for c in CODES}
info = {'url': url, 'format': '', 'hospital_name_in_file': '', 'last_updated': '', 'error': ''}


def add(code, setting, desc, gross, cash, mn, mx, negs, modifier):
    # Facility files: keep unmodified rows; fall back to TC/other rows; never the -26 professional component
    mods = [m for m in re.split(r'[,|;\s]+', str(modifier or '').upper()) if m and m not in ('NONE', 'NULL', 'NAN')]
    if '26' in mods:
        return
    r = res[code]['mod' if mods else 'none']
    if mods:
        r.setdefault('mods', set()).update(mods)
    r['rows'] += 1
    r['settings'].add((setting or '').lower())
    if desc:
        r['desc'].add(desc[:80])
    for k, v in (('gross', gross), ('cash', cash), ('min', mn), ('max', mx)):
        v = num(v)
        if v:
            r[k].append(((setting or '').lower(), v))
    for n in negs:
        n = num(n)
        if n:
            r['neg'].append(((setting or '').lower(), n))


def parse_csv(fh):
    rd = csv.reader(fh)
    head = []
    meta = None
    for i in range(6):
        row = next(rd, None)
        if row is None:
            break
        low = [c.strip().lower() for c in row]
        if i == 0:
            meta = low
            metarow0 = row
        if i == 1 and meta:
            md = dict(zip(meta, row))
            info['hospital_name_in_file'] = md.get('hospital_name', '')
            info['last_updated'] = md.get('last_updated_on', '')
        if any(c.startswith('code|') or c == 'code' for c in low) and any('standard_charge' in c or 'gross' in c for c in low):
            head = low
            break
    if not head:
        raise ValueError('no recognizable CSV header')
    codecols = [i for i, c in enumerate(head) if re.fullmatch(r'code(\|\d+)?', c)]
    typecols = {i: head.index(head[i] + '|type') for i in codecols if head[i] + '|type' in head}

    def col(*names):
        for n in names:
            if n in head:
                return head.index(n)
        return None
    cg, cc = col('standard_charge|gross'), col('standard_charge|discounted_cash')
    cmin, cmax = col('standard_charge|min'), col('standard_charge|max')
    cneg = col('standard_charge|negotiated_dollar')
    cset, cdesc, cmod = col('setting'), col('description'), col('modifiers')
    widecols = [i for i, c in enumerate(head) if c.startswith('standard_charge|') and c.endswith('|negotiated_dollar') and c.count('|') >= 3]
    info['format'] += ' CSV-' + ('tall' if 'payer_name' in head else 'wide')
    for row in rd:
        hit = None
        for i in codecols:
            if i < len(row):
                v = row[i].strip()
                if v in CODES:
                    t = row[typecols[i]].strip().upper() if i in typecols and typecols[i] < len(row) else ''
                    if t in ('', 'CPT', 'HCPCS'):
                        hit = v
                        break
        if not hit:
            continue
        g = lambda j: row[j] if j is not None and j < len(row) else None
        negs = [g(cneg)] if cneg is not None else []
        negs += [row[j] for j in widecols if j < len(row)]
        add(hit, g(cset), g(cdesc), g(cg), g(cc), g(cmin), g(cmax), negs, g(cmod))


def parse_json(fh):
    import ijson
    info['format'] += ' JSON'
    # header fields appear before the big array in most files; grab cheaply
    for item in ijson.items(fh, 'standard_charge_information.item'):
        hits = [c.get('code', '').strip() for c in item.get('code_information', []) or []
                if str(c.get('code', '')).strip() in CODES and str(c.get('type', '')).upper() in ('CPT', 'HCPCS', '')]
        if not hits:
            continue
        for sc in item.get('standard_charges', []) or []:
            negs = [p.get('standard_charge_dollar') for p in sc.get('payers_information', []) or []]
            mod = sc.get('modifier_code') or sc.get('modifiers')
            if isinstance(mod, list):
                mod = ','.join(map(str, mod))
            add(hits[0], sc.get('setting'), item.get('description'), sc.get('gross_charge'), sc.get('discounted_cash'),
                sc.get('minimum'), sc.get('maximum'), negs, mod)


def open_text(path):
    with open(path, 'rb') as f:
        b = f.read(4)
    if b[:2] == b'PK':
        z = zipfile.ZipFile(path)
        name = max(z.namelist(), key=lambda n: z.getinfo(n).file_size)
        info['format'] += ' ZIP'
        return name, z.open(name)
    if b[:2] == b'\x1f\x8b':
        import gzip
        return path, gzip.open(path)
    return path, open(path, 'rb')


try:
    t0 = time.time()
    r = subprocess.run(['curl', '-sL', '--fail', '--http1.1', '-m', '7200', '--retry', '5', '--retry-all-errors', '--retry-delay', '10', '-C', '-', '-o', tmp, url], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'download failed curl={r.returncode}')
    info['bytes'] = os.path.getsize(tmp)
    name, bfh = open_text(tmp)
    head = bfh.read(2048)
    bfh.close()
    name, bfh = open_text(tmp)
    lead = head.lstrip(b'\xef\xbb\xbf \r\n\t')[:1]
    if lead in (b'{', b'['):
        parse_json(bfh)
    elif lead == b'<':
        raise ValueError('file is a web page (HTML), not a data file')
    else:
        enc = 'utf-16' if head[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8-sig'
        parse_csv(io.TextIOWrapper(bfh, encoding=enc, errors='replace', newline=''))
    info['seconds'] = round(time.time() - t0)
except Exception as e:
    info['error'] = f'{type(e).__name__}: {e}'[:300]
finally:
    if os.path.exists(tmp):
        os.remove(tmp)


def summarize(r):
    def pick(lst):
        op = [v for s, v in lst if s in ('outpatient', 'both', '')]
        return op or [v for s, v in lst]
    g, c, mn, mx, ng = pick(r['gross']), pick(r['cash']), pick(r['min']), pick(r['max']), pick(r['neg'])
    return {'rows': r['rows'], 'settings': sorted(r['settings']), 'desc': sorted(r['desc'])[:3],
            'gross': max(g) if g else None, 'gross_n_distinct': len(set(g)),
            'cash': max(c) if c else None,
            'min': min(mn) if mn else (min(ng) if ng else None),
            'max': max(mx) if mx else (max(ng) if ng else None),
            'median_neg': statistics.median(ng) if ng else None, 'n_neg': len(ng)}


info['format'] = ' '.join(dict.fromkeys(info['format'].split()))
def best(b):
    r = b['none'] if b['none']['rows'] else b['mod']
    s = summarize(r)
    s['modifier_used'] = ','.join(sorted(r.get('mods', ())))
    return s


info['codes'] = {k: best(v) for k, v in res.items()}
json.dump(info, open(out, 'w'), indent=1)
