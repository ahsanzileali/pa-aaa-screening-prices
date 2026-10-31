"""Re-download each system's cms-hpt.txt index file into data/raw/hpt_index/ (optional; overwrites the October 2026 snapshot).
Index files list the location of each hospital's machine-readable standard charge file under 45 CFR 180."""
import urllib.request
from _common import config

for f in sorted((config.RAW / 'hpt_index').glob('*.txt')):
    for url in (f'https://www.{f.stem}/cms-hpt.txt', f'https://{f.stem}/cms-hpt.txt'):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'pa-aaa-screening-prices research download'})
            f.write_bytes(urllib.request.urlopen(req, timeout=60).read())
            print('ok  ', url)
            break
        except Exception as e:
            print('fail', url, type(e).__name__)
