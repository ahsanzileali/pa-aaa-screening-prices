#!/usr/bin/env bash
# Reproduce every table, number and figure from the October 2026 snapshot.
# Optional live refresh steps (00_fetch_index_files, 00_geocode, 04_extract_prices) are not run here; see README.
set -euo pipefail
cd "$(dirname "$0")/src"
python 01_parse_index_files.py
python 02_match_hospitals.py > /dev/null
python 03_build_hospital_list.py
python 05_build_price_table.py
python 06_download_external.py
python 07_market_hhi.py
python 08_analysis.py
python 09_figures.py
echo "Done. See results/key_numbers.md, results/tables/ and results/figures/."
