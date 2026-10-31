"""Shared paths and constants for the PA AAA screening price analysis."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data' / 'raw'              # frozen source snapshots (CMS hospital list, cms-hpt.txt index files, geocoder output)
REF = ROOT / 'data' / 'reference'        # curated hospital list with price-file links
INTERIM = ROOT / 'data' / 'interim'      # intermediate files rebuilt by the pipeline
DERIVED = ROOT / 'data' / 'derived'      # extraction results and analytic datasets
EXTERNAL = ROOT / 'data' / 'external'    # public files downloaded by src/06_download_external.py (not versioned)
EXTRACTION = DERIVED / 'extraction'
TABLES = ROOT / 'results' / 'tables'
FIGURES = ROOT / 'results' / 'figures'

CODES = ['76706', '76770', '76775']
EXTRACTION_DATE = '2026-10-30'
HERSHEY_CCN = '390256'
