# Insurance Coverage Provides Low and Consistent Prices for Abdominal Aortic Aneurysm Screening Compared With Variable Hospital Self-Pay Prices Set by Health System Policies

Code and data for a cross-sectional study of posted prices for abdominal aortic aneurysm (AAA) screening ultrasound
(CPT 76706) at 118 Pennsylvania general acute care hospitals, using files published under the federal Hospital Price
Transparency rule (45 CFR §180).

**Main finding.** Insurance coverage protects patients from price variation. Insurers paid a median of $119 (IQR $113–$139),
whereas self-pay cash prices ranged from $95 to $1,411 and differed up to 10-fold between systems within the same county.
Health system accounted for 86% of the variation in cash prices (county 15%, market 14%), because each system sets its cash
price as a fixed percentage of its own list price (median 60%; range 7% to 100%).

## Reproduce the results

Requires Python 3.14 and an internet connection (about 60 MB of public reference files are downloaded).

```bash
git clone https://github.com/ahsanzileali/pa-aaa-screening-prices.git
cd pa-aaa-screening-prices
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run_all.sh
```

Outputs

| File | Contents |
|---|---|
| `results/key_numbers.md` | Every number reported in the manuscript |
| `results/tables/variance_decomposition.csv` | Share of price variation explained by health system, county and market |
| `results/tables/by_system.csv` | Cash price and negotiated rate by health system |
| `results/tables/cash_discount_by_system.csv` | Cash price as a percentage of the gross charge, by health system |
| `results/tables/within_county.csv` | Highest and lowest system cash price in each county served by more than 1 system |
| `results/tables/associations.csv` | Market concentration, size, teaching and payer mix versus each price |
| `results/figures/` | Figure 1 (statewide map) and Figure 2 (Philadelphia and Pittsburgh) |
| `data/derived/hospital_prices.csv` | 148 hospitals with gross, cash and negotiated prices for CPT 76706, 76770 and 76775 |
| `data/derived/hospital_analysis.csv` | 118 general acute care hospitals with system, market, cost report and price variables |

## Pipeline

| Step | Script | What it does |
|---|---|---|
| 0 (optional) | `src/00_fetch_index_files.py` | Re-download each system's `cms-hpt.txt` index file |
| 0 (optional) | `src/00_geocode.py` | Geocode hospital addresses with the US Census Bureau batch geocoder |
| 1 | `src/01_parse_index_files.py` | Parse index files into location records |
| 2 | `src/02_match_hospitals.py` | Match CMS hospitals to index records (system domain, aliases, fuzzy names) |
| 3 | `src/03_build_hospital_list.py` | Build the curated hospital list, including manual curation tables |
| 4 (optional) | `src/04_extract_prices.py` | Download each price file and extract the CPT codes (slow; files up to several GB) |
| 5 | `src/05_build_price_table.py` | Combine the hospital list and extraction results |
| 6 | `src/06_download_external.py` | Download the CMS cost report, Dartmouth crosswalk and Census files |
| 7 | `src/07_market_hhi.py` | Link the cost report and hospital referral regions; compute HHI |
| 8 | `src/08_analysis.py` | All statistics in the manuscript |
| 9 | `src/09_figures.py` | Figures 1 and 2 |

`run_all.sh` runs steps 1–3 and 5–9 from the October 2026 snapshot. Steps 0 and 4 query live websites; hospitals update
their files at least yearly and some sites block automated downloads, so a rerun reflects current prices rather than the study snapshot.

## Methods summary

- **Hospitals.** CMS Hospital General Information file (Provider Data Catalog dataset xubh-q36u), Pennsylvania, accessed
  October 29, 2026. Of 131 acute care hospitals, 12 specialty hospitals and 1 closed hospital were excluded, leaving 118.
  Critical access hospitals (n = 17) are in the price table but not the analysis.
- **Price files.** Located through each website's `cms-hpt.txt` index (snapshots in `data/raw/hpt_index/`), or the price
  transparency page when no index existed; downloaded October 29–30, 2026. Third-party aggregators were not used.
- **Extraction** (`src/extract_one.py`). Rows for CPT 76706, 76770 and 76775; modifier 26 (professional component) excluded;
  unmodified rows used when available, otherwise technical-component rows; outpatient rows prioritized; when more than one
  gross charge or cash price was listed, the highest was used; negotiated rate is the median across all payer and plan
  dollar amounts. Maximum negotiated values above 5 times the gross charge are flagged as bundled or case rates.
- **Health systems.** Assigned from hospital and system websites; Lehigh Valley Health Network is counted with Jefferson Health
  after their 2024 merger. Hospitals with no system are treated as their own group.
- **Market concentration.** Herfindahl-Hirschman Index of system-level bed shares in each Dartmouth Atlas hospital referral
  region (2019 ZIP crosswalk), including all short-term and critical access hospitals in the region and in neighboring states,
  from the CMS Hospital Provider Cost Report 2023. Above 1,800 is highly concentrated (DOJ and FTC 2023 Merger Guidelines).
- **Statistics.** Intraclass correlation from random-intercept models of log price (statsmodels MixedLM, REML); Spearman
  correlation; cash price expressed as a percentage of the gross charge; linear regression of log price on HHI with and without system fixed effects, standard errors clustered by region.
- **Maps.** Census geocoder with ZIP Code tabulation area centroids for 17 unmatched addresses; 2023 cartographic boundary
  files; EPSG:2272; fixed cash price bands ($250 or less, $251–$500, more than $500).

## Data sources and licenses

| Source | Location in repo | Terms |
|---|---|---|
| Hospital machine-readable price files | Links in `data/reference/hospital_list.csv`; extracted values in `data/derived/extraction/` | Published under federal requirement |
| CMS Hospital General Information | `data/raw/cms_hospital_general_info_pa.json` | US government work, public domain |
| CMS Hospital Provider Cost Report 2023 | Downloaded by step 6 | US government work, public domain |
| Dartmouth Atlas ZIP to HRR crosswalk 2019 | Downloaded by step 6 | Free with attribution to the Dartmouth Atlas Project |
| US Census Bureau geocoder, boundaries and gazetteer | `data/raw/geocoder_*.csv`; others downloaded by step 6 | US government work, public domain |

Code is released under the MIT License (`LICENSE`). Derived data in `data/derived/` and `data/reference/` are released under
CC BY 4.0.

## Notes and known limitations

- Posted prices may differ from amounts paid and do not reflect financial assistance.
- Negotiated rates are weighted equally across plans regardless of enrollment.
- Files from 13 of the 118 hospitals could not be accessed (website access controls or no file found); see the
  `Extraction note` column of `data/derived/hospital_prices.csv`.
- Corry Memorial Hospital (critical access, not in the analysis) posted only a 2022 chargemaster; its values were entered by hand.

## Citation

If you use this code or data, please cite the article and this repository (see `CITATION.cff`).

Contact: Ahsan Zil-E-Ali, Division of Vascular Surgery, Penn State Milton S. Hershey Medical Center (azileali@pennstatehealth.psu.edu).
