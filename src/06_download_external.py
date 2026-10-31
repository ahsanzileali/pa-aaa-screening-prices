"""Download the public files used for market concentration and maps into data/external/ (about 60 MB)."""
import io
import urllib.request
import zipfile
from _common import config

FILES = {
    # CMS Hospital Provider Cost Report, 2023 (beds, discharges, residents, payer days)
    'CostReport_2023_Final.csv': 'https://data.cms.gov/sites/default/files/2026-10/e48e1326-aeeb-4ad4-acf6-a506871b6d20/CostReport_2023_Final.csv',
    # Dartmouth Atlas ZIP Code to hospital service area and hospital referral region crosswalk, 2019
    'ZipHsaHrr19.csv.zip': 'https://data.dartmouthatlas.org/downloads/geography/ZipHsaHrr19.csv.zip',
    # US Census Bureau 2023 cartographic boundary file, counties, 1:500,000
    'cb_2023_us_county_500k.zip': 'https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip',
    # US Census Bureau 2023 Gazetteer, ZIP Code tabulation areas (centroids for addresses the geocoder could not match)
    '2023_Gaz_zcta_national.zip': 'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_zcta_national.zip',
}
config.EXTERNAL.mkdir(parents=True, exist_ok=True)
for name, url in FILES.items():
    dest = config.EXTERNAL / name
    if not dest.exists():
        print('downloading', name)
        req = urllib.request.Request(url, headers={'User-Agent': 'pa-aaa-screening-prices research download'})
        dest.write_bytes(urllib.request.urlopen(req, timeout=600).read())
    if name.endswith('.zip'):
        zipfile.ZipFile(dest).extractall(config.EXTERNAL / name[:-4].replace('.csv', ''))
print('external files ready in', config.EXTERNAL)
