"""Geocode hospital addresses with the US Census Bureau batch geocoder (optional; the October 2026 output is in data/raw/)."""
import csv
import json
import subprocess
from _common import config

H = json.load(open(config.RAW / 'cms_hospital_general_info_pa.json'))['results']
with open(config.RAW / 'geocoder_input.csv', 'w', newline='') as f:
    csv.writer(f).writerows([h['facility_id'], h['address'], h['citytown'], h['state'], h['zip_code'][:5]] for h in H)
subprocess.run(['curl', '-s', '--form', f'addressFile=@{config.RAW / "geocoder_input.csv"}', '--form', 'benchmark=Public_AR_Current',
                'https://geocoding.geo.census.gov/geocoder/locations/addressbatch', '-o', str(config.RAW / 'geocoder_output.csv')], check=True)
print('geocoded', sum(1 for _ in open(config.RAW / 'geocoder_output.csv')))
