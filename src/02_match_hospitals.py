"""Match each CMS hospital to its system's cms-hpt.txt location record (system domain, aliases, fuzzy name match)."""
import json,difflib,re
from _common import config
H=[x for x in json.load(open(config.RAW/'cms_hospital_general_info_pa.json'))['results'] if x['hospital_type'] in('Acute Care Hospitals','Critical Access Hospitals')]
R=json.load(open(config.INTERIM/'hpt_rows.json'))
SYS=[('UPMC|MAGEE','upmc.com','UPMC'),('WELLSPAN|GETTYSBURG','wellspan.org','WellSpan Health'),('GEISINGER','geisinger.org','Geisinger'),
('JEFFERSON (ABINGTON|EINSTEIN|LANSDALE|HEALTH)|THOMAS JEFFERSON','jeffersonhealth.org','Jefferson Health'),('LEHIGH VALLEY|SCHUYLKILL','lvhn.org','Lehigh Valley Health Network (Jefferson)'),
('ST LUKE','slhn.org',"St. Luke's University Health Network"),('PENN HIGHLANDS','phhealthcare.org','Penn Highlands Healthcare'),
('PENN STATE|HERSHEY','pennstatehealth.org','Penn State Health'),('UNIV OF PENN|PENN PRESBY|PENNSYLVANIA HOSPITAL|CHESTER COUNTY|LANCASTER GENERAL|DOYLESTOWN','pennmedicine.org','Penn Medicine'),
('BRYN MAWR|PAOLI|LANKENAU|RIDDLE','mainlinehealth.org','Main Line Health'),('TEMPLE','templehealth.org','Temple Health'),('PHOENIXVILLE|POTTSTOWN|READING HOSPITAL','towerhealth.org','Tower Health'),
('ALLEGHENY|FORBES|WEXFORD|WEST PENN|CANONSBURG|JEFFERSON HOSPITAL|SAINT VINCENT|GROVE CITY|EMERUS','ahn.org','Allegheny Health Network'),
('EXCELA|INDEPENDENCE|UNIONTOWN','wvumedicine.org','WVU Medicine'),('HERITAGE','heritagevalley.org','Heritage Valley Health System'),
('CONEMAUGH','conemaugh.org','Conemaugh Health System'),('MERCY CATHOLIC|NAZARETH|ST MARY','trinityhealthma.org','Trinity Health Mid-Atlantic'),
('ROBERT PACKER|TROY','guthrie.org','Guthrie'),('LECOM','lecomhealth.com','LECOM Health'),('MEADVILLE|TITUSVILLE','mmchs.org','Meadville Medical Center'),
('WAYNE MEMORIAL','wmh.org','Wayne Memorial Health System'),('WARREN','wgh.org','Warren General'),('ST CLAIR','stclair.org','St. Clair Health'),('ACMH','acmh.org','ACMH'),('HOLY REDEEMER','holyredeemer.com','Holy Redeemer'),('WASHINGTON HOSPITAL','upmc.com','UPMC')]
ALIAS={'390067':'UPMC Harrisburg','390164':'UPMC Presbyterian','390150':'UPMC Green','390042':'UPMC Washington','390107':'UPMC Passavant-McCandless','390178':'UPMC Horizon-Greenville','390114':'UPMC Magee','390117':'UPMC Bedford',
'390145':'Westmoreland Hospital','390219':'Latrobe Hospital','390217':'Frick Hospital','390168':'Butler Memorial Hospital','390093':'Clarion Hospital','390160':'CANONSBURG HOSPITAL','390266':'GROVE CITY HOSPITAL',
'390133':'Lehigh Valley Hospital - Cedar Crest','390030':'Lehigh Valley Hospital - Schuylkill S. Jackson Street','390430':'CHP-LVHN JV, LLC d/b/a Lehigh Valley Hospital - Macungie',
'390049':'St Lukes Hospital Bethlehem Campus','390057':"St Lukes Hospital Sacred Heart Campus",'390332':'St Lukes Hospital Geisinger Campus','390183':'St Lukes Hospital Miners Campus','390335':'St Lukes Hospital Carbon Campus',
'390115':'Jefferson Torresdale Hospital','390100':'Penn Medicine Lancaster General Health','390111':'The Hospital of the University of Pennsylvania','390027':'Temple University Hospital - Main Campus','390009':'SAINT VINCENT HOSPITAL',
'390195':'Lankenau Medical Center','390156':'Mercy Fitzgerald Hospital','390001':'Geisinger Community Medical Center','390270':'Geisinger Wyoming Valley','390079':'Guthrie Robert Packer Hospital','390065':'WellSpan Gettysburg Hospital'}
out=[]
for h in sorted(H,key=lambda x:x['facility_name']):
    n=h['facility_name']; dom=sysn=''
    for pat,d,s in SYS:
        if re.search(pat,n): dom,sysn=d,s; break
    cands=[r for r in R if r['domain']==dom]; m=None
    if cands:
        if h['facility_id'] in ALIAS: m=next((r for r in cands if r['location-name']==ALIAS[h['facility_id']]),None)
        if not m:
            names=[r['location-name'].upper() for r in cands]; b=difflib.get_close_matches(n,names,1,0.45)
            if b: m=cands[names.index(b[0])]
    out.append(dict(h=h,sys=sysn,dom=dom,m=m))
json.dump([dict(ccn=o['h']['facility_id'],name=o['h']['facility_name'],sys=o['sys'],dom=o['dom'],loc=(o['m'] or {}).get('location-name',''),src=(o['m'] or {}).get('source-page-url',''),mrf=(o['m'] or {}).get('mrf-url','')) for o in out],open(config.INTERIM/'matched.json','w'),indent=0)
for o in out: print(o['h']['facility_id'],o['h']['facility_name'][:40].ljust(40),'->',(o['m'] or {}).get('location-name','--- NONE'))
