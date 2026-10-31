"""Download each hospital price file and extract CPT 76706, 76770 and 76775 (optional; slow).

The extraction results used in the paper are already in data/derived/extraction/ (retrieved October 2026).
Hospitals update their files, so a rerun reflects current prices, not the study snapshot.

Usage: python src/04_extract_prices.py [--force] [--workers 3]
Large files (up to several GB) are streamed; some sites block automated downloads and must be fetched by hand,
then extracted with: python src/extract_one.py file:///path/to/file OUT.json WORKDIR
"""
import argparse
import concurrent.futures as cf
import csv
import json
import subprocess
import sys
import time
from _common import config, url_hash

STEMS = {'391304': 'bucktail', '390268': 'mountnittany', '391308': 'corry'}  # links found outside an index file

ap = argparse.ArgumentParser()
ap.add_argument('--force', action='store_true', help='re-download files that already have a result')
ap.add_argument('--workers', type=int, default=3)
a = ap.parse_args()

rows = list(csv.DictReader(open(config.REF / 'hospital_list.csv')))
jobs = {}
for r in rows:
    u = r['Price file link (MRF)']
    if u:
        jobs[u] = STEMS.get(r['CCN'], url_hash(u))
config.EXTRACTION.mkdir(parents=True, exist_ok=True)
work = config.INTERIM / 'work'


def run(item):
    u, stem = item
    out = config.EXTRACTION / f'{stem}.json'
    if out.exists() and not a.force:
        return
    subprocess.run([sys.executable, '-I', str(config.ROOT / 'src' / 'extract_one.py'), u, str(out), str(work / stem)])
    d = json.load(open(out))
    print(time.strftime('%H:%M'), 'ERR' if d['error'] else 'ok', d.get('bytes'), d['error'][:60], u[:90], flush=True)


with cf.ThreadPoolExecutor(a.workers) as ex:
    list(ex.map(run, jobs.items()))
print('files', len(jobs))
