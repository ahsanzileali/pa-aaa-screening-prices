"""Figure 1 (statewide hospitals by cash price band) and Figure 2 (Philadelphia and Pittsburgh regions, labeled with system and cash price)."""
import csv, json, os, re
from _common import config
import geopandas as gpd, pandas as pd, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
HALO = [pe.withStroke(linewidth=2.2, foreground='white')]
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D
from adjustText import adjust_text

plt.rcParams.update({'font.family': 'Arial', 'font.size': 8, 'axes.linewidth': 0, 'pdf.fonttype': 42, 'svg.fonttype': 'none'})
COL = ['#0a5c32', '#e0a800', '#f0602e']          # green / yellow / red; CVD-separated (validator all-pairs)
HERSHEY = '390256'
NODATA, EDGE, INK, MUTED = '#e6e6e3', '#ffffff', '#1f1f1f', '#6b6b6b'

# ---- data -------------------------------------------------------------
d = pd.read_csv(config.DERIVED / 'hospital_analysis.csv', dtype={'CCN': str})
d = d[d.cash.notna()]
G = {r[0]: r for r in csv.reader(open(config.RAW / 'geocoder_output.csv'))}
Z = {}
with open(config.EXTERNAL / '2023_Gaz_zcta_national' / '2023_Gaz_zcta_national.txt') as f:
    for i, line in enumerate(f):
        if i:
            p = line.split('	'); Z[p[0]] = (float(p[6]), float(p[5]))
ZIP = {h['facility_id']: h['zip_code'][:5] for h in json.load(open(config.RAW / 'cms_hospital_general_info_pa.json'))['results']}

def short(n):
    n = n.title().replace('Upmc', 'UPMC').replace('Ahn ', 'AHN ').replace("'S", "'s").replace('Univ Of', 'University of')
    n = re.sub(r'\s+', ' ', n).replace(' Of ', ' of ').replace(' And ', ' and ').replace(' The', '')
    fix = {'Hospital of University of Pennsylvania': 'Hospital of the Univ. of Pennsylvania', 'Milton S Hershey Medical Center': 'Penn State Hershey Medical Center',
           'Mercy Catholic Medical Center- Mercy Fitzgerald': 'Mercy Fitzgerald Hospital', 'Washington Hospital,': 'UPMC Washington',
           'Chan Soon- Shiong Medical Center At Windber': 'Chan Soon-Shiong Med. Ctr. Windber', 'Upmc Pinnacle Hospitals': 'UPMC Harrisburg'}
    for k, v in fix.items():
        if n.startswith(k): n = v
    return n.replace(' Medical Center', ' Med. Ctr.').replace('Excela Health ', '').replace('Independence Health System ', '').replace(' At ', ' at ').replace('Wellspan', 'WellSpan').replace('St Mary', 'St. Mary')

recs = []
for _, r in d.iterrows():
    g = G[r.CCN]
    lon, lat = map(float, g[5].split(',')) if g[2] == 'Match' else Z[ZIP[r.CCN]]  # ZCTA centroid when the geocoder had no match
    recs.append(dict(ccn=r.CCN, name=short(r['Hospital (CMS name)']), county=r.County, v=r.cash, sys=r.system, lon=lon, lat=lat))
df = pd.DataFrame(recs)
cty = gpd.read_file(config.EXTERNAL / 'cb_2023_us_county_500k' / 'cb_2023_us_county_500k.shp')
cty = cty[cty.STATEFP == '42'].to_crs(2272)
cty['key'] = cty.NAME.str.title()
pts = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs=4326).to_crs(2272)
state = cty.dissolve()
HERSHEY = config.HERSHEY_CCN
SHORT = {'Allegheny Health Network': 'AHN', "St. Luke's University Health Network": "St. Luke's", 'Trinity Health Mid-Atlantic': 'Trinity Health',
         'Heritage Valley Health System': 'Heritage Valley', 'Commonwealth Health': 'Commonwealth', 'Prime Healthcare': 'Prime',
         'Jefferson Health': 'Jefferson', 'Main Line Health': 'Main Line', 'Tower Health': 'Tower', 'WellSpan Health': 'WellSpan',
         'St. Clair Health': 'St. Clair', 'Penn State Health': 'Penn State Health', 'Holy Redeemer': 'Holy Redeemer', 'Independent': 'Independent'}
pts['sys'] = [SHORT.get(s, s) for s in pts.sys]
# fixed dollar bands (thirds split a large tie at UPMC $248)
BANDS = [250, 500]
for t_ in (pts,):
    t_['t'] = np.select([t_.v <= BANDS[0], t_.v <= BANDS[1]], [0, 1], 2)
rng = [(pts.v[pts.t == k].min(), pts.v[pts.t == k].max(), int((pts.t == k).sum())) for k in range(3)]
LAB = ['\\$250 or less', '\\$251 to \\$500', 'Over \\$500']
NAME_OFF = {'Philadelphia': (14000, -26000), 'Delaware': (-30000, -18000), 'Montour': (0, 14000)}

def save(fig, stem):
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(config.FIGURES / f'{stem}.png', dpi=300, bbox_inches='tight', facecolor='white')
    fig.savefig(config.FIGURES / f'{stem}.tiff', dpi=600, bbox_inches='tight', facecolor='white', pil_kwargs={'compression': 'tiff_lzw'})

def legend(fig, y, star=True, ncol=3):
    h = [Line2D([], [], marker='o', ls='none', markersize=6.5, markerfacecolor=COL[k], markeredgecolor='#3a3a3a', markeredgewidth=0.5,
                label=f'{LAB[k]} (n = {rng[k][2]} hospitals)') for k in range(3)]
    if star:
        h.append(Line2D([], [], marker='*', ls='none', markersize=10, markerfacecolor='white', markeredgecolor='#1f1f1f', label='Penn State Hershey Medical Center'))
    fig.legend(handles=h, loc='upper center', bbox_to_anchor=(0.5, y), ncol=ncol, frameon=False, fontsize=9, handletextpad=0.4, columnspacing=1.6)

# ---------- Figure 1: statewide ----------
fig = plt.figure(figsize=(7.0, 4.35))
ax = fig.add_axes([0, 0, 1, 0.9])
cty.plot(ax=ax, color='#f1f1ee', edgecolor='white', linewidth=0.8)
state.boundary.plot(ax=ax, color='#8a8a86', linewidth=0.7)
for _, c in cty.iterrows():
    p = c.geometry.representative_point(); dx, dy = NAME_OFF.get(c.key, (0, 0))
    ax.text(p.x + dx, p.y + dy, c.NAME, ha='center', va='center', fontsize=6.2, color='#55554f', path_effects=[pe.withStroke(linewidth=1.8, foreground='#f1f1ee')], zorder=2)
    if (dx, dy) != (0, 0):
        ax.plot([p.x, p.x + dx * 0.72], [p.y, p.y + dy * 0.72], color='#b5b5b0', lw=0.4, zorder=2)
d = pts
for k in range(3):
    dd = d[d.t == k]
    ax.scatter(dd.geometry.x, dd.geometry.y, s=34, color=COL[k], edgecolor='#2b2b2b', linewidth=0.45, zorder=4)
ax.set_axis_off(); ax.set_aspect('equal')
legend(fig, 1.0, star=False)
fig.text(0.5, -0.01, 'Each dot is a hospital colored by its posted cash (self-pay) price for CPT 76706 (AAA screening ultrasound); n = 94 hospitals.\n'
         'High- and low-price hospitals sit side by side across the state, including within the same county.', ha='center', va='top', fontsize=8, color='#3f3f3b')
save(fig, 'Figure 1 AAA Screening Cash Price by Hospital')
plt.close(fig)

# ---------- Figure 2: metro regions ----------
REG = [('A', 'Philadelphia region', ['Philadelphia', 'Delaware', 'Montgomery', 'Bucks', 'Chester']),
       ('B', 'Pittsburgh region', ['Allegheny', 'Beaver', 'Butler', 'Washington', 'Westmoreland'])]
fig = plt.figure(figsize=(7.5, 12.0))
axes = [fig.add_axes([0, 0.50, 1, 0.44]), fig.add_axes([0, 0.02, 1, 0.44])]
for ax, (letter, title, counties) in zip(axes, REG):
    inn = pts[pts.county.isin(counties)]
    x0, y0, x1, y1 = inn.total_bounds
    pos = ax.get_position(); ratio = pos.width * 7.5 / (pos.height * 12.0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hw = max((x1 - x0) * 0.62, (y1 - y0) * 0.62 * ratio); hh_ = hw / ratio
    x0, x1, y0, y1 = cx - hw, cx + hw, cy - hh_, cy + hh_
    cty.plot(ax=ax, color=['#f4f4f2' if k in counties else '#fbfbfa' for k in cty.key], edgecolor='#c4c4bf', linewidth=0.6)
    state.boundary.plot(ax=ax, color='#8a8a86', linewidth=0.8)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.set_axis_off()
    for _, c in cty.iterrows():
        p = c.geometry.representative_point()
        if x0 < p.x < x1 and y0 < p.y < y1:
            ax.text(p.x, p.y, c.NAME.upper(), ha='center', va='center', fontsize=10, color='#c4c4be', fontweight='bold', zorder=1)
    X0, X1 = ax.get_xlim(); Y0, Y1 = ax.get_ylim()
    sub = pts[pts.geometry.x.between(X0, X1) & pts.geometry.y.between(Y0, Y1) & pts.county.isin(counties)]
    for k in range(3):
        dd = sub[sub.t == k]
        ax.scatter(dd.geometry.x, dd.geometry.y, s=60, color=COL[k], edgecolor='#3a3a3a', linewidth=0.5, zorder=4)
    labs = [ax.text(p.geometry.x, p.geometry.y, f'{p.sys}  \\${p.v:,.0f}', fontsize=8.6, color=INK, path_effects=HALO, zorder=6) for _, p in sub.iterrows()]
    adjust_text(labs, ax=ax, x=list(sub.geometry.x), y=list(sub.geometry.y), expand=(1.2, 1.5), force_text=(0.3, 0.5), max_move=60,
                arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.45))
    lo, hi = sub.loc[sub.v.idxmin()], sub.loc[sub.v.idxmax()]
    ax.text(0.0, 1.01, letter, transform=ax.transAxes, fontsize=12, fontweight='bold', va='bottom', color=INK)
    ax.text(0.035, 1.01, f'{title} ({", ".join(counties)} counties; n = {len(sub)} hospitals; cash price \\${lo.v:,.0f} to \\${hi.v:,.0f})',
            transform=ax.transAxes, fontsize=9.2, va='bottom', color=INK)
legend(fig, 1.0, star=False)
fig.text(0.5, 0.0, 'Each hospital is labeled with its health system and posted cash (self-pay) price for CPT 76706; colors match Figure 1.',
         ha='center', va='top', fontsize=8.5, color='#3f3f3b')
save(fig, 'Figure 2 AAA Screening Cash Price Philadelphia and Pittsburgh')
print('bands', rng)
