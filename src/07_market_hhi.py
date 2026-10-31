"""Link hospitals to the 2023 cost report and hospital referral regions, and compute market concentration (HHI)."""
import numpy as np
import pandas as pd
from _common import config

h = pd.read_csv(config.DERIVED / 'hospital_prices.csv', dtype={'CCN': str})
sysmap = dict(zip(h.CCN, h['Health system']))

cr = pd.read_csv(config.EXTERNAL / 'CostReport_2023_Final.csv', dtype={'Provider CCN': str, 'Zip Code': str}, low_memory=False)
cr['ccn'] = cr['Provider CCN'].str.zfill(6)
cr = cr.sort_values('Fiscal Year End Date').drop_duplicates('ccn', keep='last')
suf = cr.ccn.str[2:].astype(int)
cr = cr[((suf >= 1) & (suf <= 879)) | ((suf >= 1300) & (suf <= 1399))].copy()  # short-term acute and critical access
cr['zip'] = cr['Zip Code'].str[:5]
z = pd.read_csv(config.EXTERNAL / 'ZipHsaHrr19' / 'ZipHsaHrr19.csv', dtype={'zipcode19': str})
z['zip'] = z.zipcode19.str.zfill(5)
cr = cr.merge(z[['zip', 'hrrnum', 'hrrcity', 'hrrstate']], on='zip', how='left')
num = lambda c: pd.to_numeric(cr[c], errors='coerce')
cr['beds'] = num('Number of Beds')
cr['dis'] = num('Total Discharges (V + XVIII + XIX + Unknown)')
cr['res'] = num('Number of Interns and Residents (FTE)').fillna(0)
cr['mcare'] = (num('Total Discharges Title XVIII') / cr.dis * 100).round(1)
cr['mcaid'] = (num('Total Discharges Title XIX') / cr.dis * 100).round(1)
cr['rural'] = cr['Rural Versus Urban'].map({'U': 'Urban', 'R': 'Rural'})


def system(r):
    # study hospitals use the curated system; out-of-state hospitals are grouped by name for the large PA systems
    s = sysmap.get(r.ccn)
    if s and s != 'Independent':
        return s.replace('Lehigh Valley Health Network (Jefferson)', 'Jefferson Health')
    n = str(r['Hospital Name']).upper()
    for k, v in [('UPMC', 'UPMC'), ('JEFFERSON', 'Jefferson Health'), ('PENN ', 'Penn Medicine'), ('GEISINGER', 'Geisinger'),
                 ('ST LUKE', "St. Luke's"), ('GUTHRIE', 'Guthrie'), ('WELLSPAN', 'WellSpan'), ('ALLEGHENY', 'AHN')]:
        if k in n and r['State Code'] != 'PA':
            return v
    return 'IND-' + r.ccn


cr['sys'] = cr.apply(system, axis=1)
pa = h[(h['CMS type'] == 'Acute care') & (h['Specialty hospital'] == 'No') & (h['Link status'] != 'Closed')].copy()
hrrs = set(cr[cr.ccn.isin(pa.CCN)].hrrnum.dropna())
mk = cr[cr.hrrnum.isin(hrrs)]


def hhi(df, grp, size):
    out = {}
    for g, d in df.groupby(grp):
        s = d.groupby('sys')[size].sum()
        out[g] = ((s / s.sum() * 100) ** 2).sum()
    return out


for size in ['beds', 'dis']:
    cr['hhi_hrr_' + size] = cr.hrrnum.map(hhi(mk.dropna(subset=[size]), 'hrrnum', size))
pac = cr[cr['State Code'] == 'PA']
cr['hhi_cty_beds'] = cr.County.map(hhi(pac.dropna(subset=['beds']), 'County', 'beds'))

d = pa.merge(cr[['ccn', 'hrrnum', 'hrrcity', 'beds', 'dis', 'res', 'mcare', 'mcaid', 'rural', 'sys', 'hhi_hrr_beds', 'hhi_hrr_dis', 'hhi_cty_beds']],
             left_on='CCN', right_on='ccn', how='left').drop(columns='ccn')
d['sys'] = d.sys.fillna(d['Health system'].str.replace('Lehigh Valley Health Network (Jefferson)', 'Jefferson Health', regex=False))
d['system'] = np.where(d.sys.str.startswith('IND-'), 'Independent', d.sys)          # label
d['system_group'] = np.where(d.sys.str.startswith('IND-'), 'Independent ' + d.CCN, d.sys)  # each independent is its own group
d['neg'] = d['76706 median negotiated']
d['cash'] = d['76706 cash price']
d['gross'] = d['76706 gross charge']
d.drop(columns='sys').to_csv(config.DERIVED / 'hospital_analysis.csv', index=False)
pd.DataFrame({'hrrnum': list(hrrs)}).merge(cr.drop_duplicates('hrrnum')[['hrrnum', 'hrrcity', 'hrrstate', 'hhi_hrr_beds', 'hhi_hrr_dis']], on='hrrnum') \
  .assign(hospitals_in_market=lambda x: x.hrrnum.map(mk.groupby('hrrnum').size()), study_hospitals=lambda x: x.hrrnum.map(d.groupby('hrrnum').size())) \
  .sort_values('hhi_hrr_beds').to_csv(config.DERIVED / 'markets.csv', index=False)
print('general acute', len(d), 'HRRs', len(hrrs), 'market hospitals', len(mk), 'out of state', (mk['State Code'] != 'PA').sum(),
      'missing cost report', d.hrrnum.isna().sum())
