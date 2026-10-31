"""All statistics reported in the manuscript: price distributions, variance decomposition, within-county gaps, market associations.
Writes results/tables/*.csv and results/key_numbers.md."""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from _common import config

d = pd.read_csv(config.DERIVED / 'hospital_analysis.csv', dtype={'CCN': str})
config.TABLES.mkdir(parents=True, exist_ok=True)
L = []  # key numbers


def fmtp(p):
    return '<0.001' if p < 0.001 else f'{p:.3f}' if p < 0.01 else f'{p:.2f}'


def dist(s):
    s = s.dropna()
    return f'n = {len(s)}, median ${s.median():,.0f} (IQR ${s.quantile(.25):,.0f}-${s.quantile(.75):,.0f}; range ${s.min():,.0f}-${s.max():,.0f})'


# ---------- sample ----------
has = d[d.neg.notna() | d.cash.notna()]
vc = has.system.value_counts()
multi = vc[(vc >= 2) & (vc.index != 'Independent')]
L += ['## Sample',
      f'- General acute care hospitals: {len(d)}',
      f'- Listing a price for 76706: {len(has)} ({len(has) / len(d):.1%}); in {len(multi)} multihospital systems: {multi.sum()}; single-hospital or independent: {len(has) - multi.sum()}',
      f'- Price file not accessible: {d["Extraction note"].fillna("").str.match("Could not|No file").sum()}; file without the code: {(d["Extraction note"] == "Codes not listed in file").sum() + ((d["Codes found"].notna()) & ~d["Codes found"].fillna("").str.contains("76706")).sum()}']

# ---------- three prices ----------
both = d.dropna(subset=['cash', 'neg'])
r = both.cash / both.neg
gn = d.dropna(subset=['gross', 'neg'])
rho, p = stats.spearmanr(gn.gross, gn.neg)
L += ['', '## Prices for CPT 76706',
      f'- Gross charge: {dist(d.gross)}',
      f'- Median negotiated rate: {dist(d.neg)}',
      f'- Cash price: {dist(d.cash)}',
      f'- Gross vs negotiated: rho = {rho:.2f}, p = {fmtp(p)} (n = {len(gn)})',
      f'- Cash at or above negotiated: {(r >= 1).sum()} of {len(both)} ({(r >= 1).mean():.1%}); median cash-to-negotiated ratio {r.median():.1f}']


# ---------- variance decomposition ----------
def icc(df, y, g):
    df = df.dropna(subset=[g])
    m = smf.mixedlm(f'np.log({y}) ~ 1', df, groups=df[g]).fit(reml=True)
    vb = float(m.cov_re.iloc[0, 0])
    return vb / (vb + m.scale)


vr = []
for y, lab in [('cash', 'Cash price'), ('neg', 'Median negotiated rate')]:
    dd = d.dropna(subset=[y])
    for g, gl in [('system_group', 'Health system'), ('County', 'County'), ('hrrnum', 'Hospital referral region')]:
        f = smf.ols(f'np.log({y}) ~ C({g})', dd.dropna(subset=[g])).fit()
        vr.append({'price': lab, 'grouping': gl, 'hospitals': len(dd), 'groups': dd[g].nunique(), 'icc': round(icc(dd, y, g), 3), 'adj_r2': round(f.rsquared_adj, 3)})
    ly = np.log(dd[y])
    dm = ly - ly.groupby(dd.County).transform('mean')
    vr.append({'price': lab, 'grouping': 'Within-county share of variance', 'hospitals': len(dd), 'groups': None,
               'icc': round(dm[dd.County.map(dd.County.value_counts()) >= 2].var() / ly.var(), 3), 'adj_r2': None})
vr = pd.DataFrame(vr)
vr.to_csv(config.TABLES / 'variance_decomposition.csv', index=False)
L += ['', '## Share of variation explained (intraclass correlation, log price)'] + \
     [f'- {x.price}, {x.grouping}: {x.icc:.0%}' for x in vr.itertuples()]

# ---------- by system ----------
g = d.dropna(subset=['cash', 'neg'], how='all').groupby('system')
bys = pd.DataFrame({'hospitals': g.CCN.size(), 'counties': g.County.nunique(), 'median_cash': g.cash.median(), 'min_cash': g.cash.min(),
                    'max_cash': g.cash.max(), 'median_negotiated': g.neg.median(), 'min_negotiated': g.neg.min(), 'max_negotiated': g.neg.max()}).round(2)
bys = bys.sort_values('median_cash').reset_index()
bys.to_csv(config.TABLES / 'by_system.csv', index=False)
ms = bys[bys.system.isin(multi.index)]
L += ['', '## Health systems',
      f'- Median system cash price: ' + '; '.join(f'{x.system} ${x.median_cash:,.0f}' for x in bys.dropna(subset=['median_cash']).itertuples()),
      f'- Multihospital systems with median negotiated rate $102-$143: {ms.median_negotiated.round().between(102, 143).sum()} of {len(ms)}']

# ---------- within county ----------
rows = []
for cty, gg in d.dropna(subset=['cash']).groupby('County'):
    s = gg.groupby('system').cash.median().sort_values()
    if len(s) >= 2:
        rows.append({'county': cty, 'systems': len(s), 'lowest_system': s.index[0], 'lowest_cash': round(s.iloc[0]),
                     'highest_system': s.index[-1], 'highest_cash': round(s.iloc[-1]), 'fold': round(s.iloc[-1] / s.iloc[0], 1),
                     'all_systems': ' | '.join(f'{k} ${v:,.0f}' for k, v in s.items())})
wc = pd.DataFrame(rows).sort_values('fold', ascending=False)
wc.to_csv(config.TABLES / 'within_county.csv', index=False)
cm = d.dropna(subset=['cash']).groupby(['system', 'County']).cash.median()
span = lambda s: f'${cm[s].min():,.0f}-${cm[s].max():,.0f}'
L += ['', '## Within county',
      f'- Counties served by more than 1 system: {len(wc)}; 2-fold or greater gap: {(wc.fold >= 2).sum()}',
      *[f'- {x.county}: {x.lowest_system} ${x.lowest_cash:,} vs {x.highest_system} ${x.highest_cash:,} ({x.fold}-fold)' for x in wc.head(5).itertuples()],
      f'- County-level system cash prices: Allegheny Health Network {span("Allegheny Health Network")}; Penn State Health {span("Penn State Health")}; Tower Health {span("Tower Health")}']

# ---------- how cash prices are set: system-wide discount from the gross charge ----------
c = d.dropna(subset=['cash', 'gross']).copy()
c['cash_pct_of_gross'] = c.cash / c.gross * 100
rho_cg, p_cg = stats.spearmanr(c.cash, c.gross)
m = smf.mixedlm('cash_pct_of_gross ~ 1', c, groups=c.system_group).fit(reml=True)
icc_pct = float(m.cov_re.iloc[0, 0]) / (float(m.cov_re.iloc[0, 0]) + m.scale)
gp = c.groupby('system').cash_pct_of_gross
disc = pd.DataFrame({'hospitals': gp.size(), 'median_pct': gp.median(), 'min_pct': gp.min(), 'max_pct': gp.max()}).round(1).sort_values('median_pct').reset_index()
disc.to_csv(config.TABLES / 'cash_discount_by_system.csv', index=False)
md = disc[disc.system.isin(multi.index)]
rng_ = lambda s: f"{disc.set_index('system').loc[s, 'min_pct']:.0f}%-{disc.set_index('system').loc[s, 'max_pct']:.0f}%"
negn = d.neg.dropna()
L += ['', '## How cash prices are set',
      f'- Cash vs gross charge: rho = {rho_cg:.2f}, p{fmtp(p_cg) if fmtp(p_cg).startswith("<") else " = " + fmtp(p_cg)} (n = {len(c)})',
      f'- Cash price as % of gross charge: median {c.cash_pct_of_gross.median():.0f}% (IQR {c.cash_pct_of_gross.quantile(.25):.0f}%-{c.cash_pct_of_gross.quantile(.75):.0f}%; range {c.cash_pct_of_gross.min():.0f}%-{c.cash_pct_of_gross.max():.0f}%)',
      f'- Health system share of variation in that percentage (ICC): {icc_pct:.0%}',
      f'- Multihospital systems whose percentage varied by 10 points or less: {((md.max_pct - md.min_pct) <= 10).sum()} of {len(md)}',
      f'- UPMC {rng_("UPMC")}; WellSpan Health {rng_("WellSpan Health")}; Penn Medicine {rng_("Penn Medicine")}; Prime Healthcare {rng_("Prime Healthcare")}',
      f'- Negotiated rate between $100 and $150: {negn.between(100, 150).sum()} of {len(negn)} ({negn.between(100, 150).mean():.1%})']

# ---------- market and hospital characteristics ----------
mk = pd.read_csv(config.DERIVED / 'markets.csv')
ass = []
for y, lab in [('neg', 'Median negotiated rate'), ('cash', 'Cash price'), ('gross', 'Gross charge')]:
    for x, xl in [('hhi_hrr_beds', 'Market HHI (beds)'), ('hhi_hrr_dis', 'Market HHI (discharges)'), ('hhi_cty_beds', 'County HHI (beds)'),
                  ('beds', 'Beds'), ('mcaid', 'Medicaid share'), ('mcare', 'Medicare share')]:
        dd = d.dropna(subset=[x, y])
        rr, pp = stats.spearmanr(dd[x], dd[y])
        ass.append({'price': lab, 'factor': xl, 'hospitals': len(dd), 'rho': round(rr, 2), 'p': fmtp(pp)})
    for flag, fl in [(d.res > 0, 'Teaching (any residents)'), (d.system.map(d.system.value_counts()) >= 5, 'Large system (5 or more hospitals)')]:
        a, b = d[flag][y].dropna(), d[~flag][y].dropna()
        ass.append({'price': lab, 'factor': fl, 'hospitals': len(a) + len(b), 'p': fmtp(stats.mannwhitneyu(a, b).pvalue),
                    'median_yes': round(a.median()), 'median_no': round(b.median())})
    dd = d.dropna(subset=[y, 'hhi_hrr_beds']).copy()
    dd['h'] = dd.hhi_hrr_beds / 1000
    dd['s2'] = np.where(dd.system_group.map(dd.system_group.value_counts()) >= 2, dd.system_group, 'single')
    for f, fl in [(f'np.log({y}) ~ h', 'HHI per 1,000, clustered by HRR'), (f'np.log({y}) ~ h + C(s2)', 'HHI per 1,000, clustered by HRR, system fixed effects')]:
        m = smf.ols(f, dd).fit(cov_type='cluster', cov_kwds={'groups': dd.hrrnum})
        ass.append({'price': lab, 'factor': fl, 'hospitals': len(dd), 'p': fmtp(m.pvalues.h), 'pct_change': round((np.exp(m.params.h) - 1) * 100, 1)})
ass = pd.DataFrame(ass)
ass.to_csv(config.TABLES / 'associations.csv', index=False)
pick = lambda pr, fa: ass[(ass.price == pr) & (ass.factor == fa)].iloc[0]
a1, a2 = pick('Median negotiated rate', 'Market HHI (beds)'), pick('Cash price', 'Market HHI (beds)')
a3 = pick('Cash price', 'HHI per 1,000, clustered by HRR, system fixed effects')
a4, a5 = pick('Median negotiated rate', 'Beds'), pick('Cash price', 'Teaching (any residents)')
L += ['', '## Market concentration',
      f'- Hospital referral regions: {len(mk)}; HHI above 1,800: {(mk.hhi_hrr_beds > 1800).sum()}; range {mk.hhi_hrr_beds.min():,.0f} ({mk.iloc[0].hrrcity}) to {mk.hhi_hrr_beds.max():,.0f} ({mk.iloc[-1].hrrcity})',
      f'- HHI vs negotiated rate: rho = {a1.rho:.2f}, p = {a1.p}',
      f'- HHI vs cash price: rho = {a2.rho:.2f}, p = {a2.p}; after system adjustment {a3['pct_change']:+.1f}% per 1,000 points, p = {a3.p}',
      f'- Beds vs negotiated rate: rho = {a4.rho:.2f}, p{a4.p if a4.p.startswith('<') else ' = ' + a4.p}; teaching vs cash price p = {a5.p}']

(config.ROOT / 'results' / 'key_numbers.md').write_text('# Key numbers (CPT 76706, general acute care hospitals)\n\n' + '\n'.join(L) + '\n')
print('\n'.join(L))
