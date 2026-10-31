"""Build the curated hospital list (data/reference/hospital_list.csv) from CMS data and the matched index records.
Manual curation (system assignment, specialty flags, links found outside the index) is recorded in the tables below."""
import csv,json,re
from _common import config
H={x['facility_id']:x for x in json.load(open(config.RAW/'cms_hospital_general_info_pa.json'))['results']}
M=json.load(open(config.INTERIM/'matched.json')); R=json.load(open(config.INTERIM/'hpt_rows.json'))
def row(dom,name):
    return next((r for r in R if r['domain']==dom and r['location-name']==name),None)
IND={'390112':('windbercare.org','Chan Soon Shiong Medical Center at Windber','Independent'),'391304':('bucktailmedicalcenter.org','Bucktail Medical Center','Independent'),
'391303':('fcmcpa.org','Fulton County Medical Center','Independent'),'390070':('lowerbuckshosp.com','Lower Bucks Hospital','Prime Healthcare'),
'390325':('osshealth.com','OSS Health','Independent'),'390237':('commonwealthhealth.net','Moses Taylor Hospital','Commonwealth Health'),
'390137':('commonwealthhealth.net','Wilkes-Barre General Hospital','Commonwealth Health'),'390304':('roxboroughmemorial.com','Roxborough Memorial Hospital','Prime Healthcare'),
'390116':('suburbanhosp.org','Suburban Behavioral Health Campus of Roxborough Memorial Hospital','Prime Healthcare'),'391314':('titusvillehospital.org','Titusville Area Hospital','Meadville Medical Center'),
'390272':('vfmc.net','Valley Forge Medical Center & Hospital','Independent'),'390331':('willseye.org','Wills Eye Hospital','Independent'),'390323':('ashospital.net','Advanced Surgical Hospital','Independent'),
'391306':('endlesscare.org',None,'Independent'),'390332':('slhn.org','St Lukes Hospital Geisinger Campus',"St. Luke's University Health Network")}
NOTE={'390237':'Hospital index file lists the Regional Hospital and Moses Taylor links swapped; link here is the file named for Regional Hospital of Scranton',
'390116':'Index lists this site as Suburban Behavioral Health Campus (Prime); confirm acute services still offered',
'390180':'Crozer-Chester closed in 2025; no current file expected','390333':'AHN Emerus micro-hospital; not listed in AHN index file',
'390164':'UPMC files Presbyterian and Shadyside separately; Presbyterian file used, Shadyside also available','390115':'Jefferson Northeast files by campus (Torresdale, Frankford); Torresdale used',
'390133':'LVHN files by campus; Cedar Crest (main) used','390057':"St. Luke's renamed Grand View as Sacred Heart in index; verify campus",
'390042':'Washington Hospital is now UPMC Washington','390150':'Listed as UPMC Green in UPMC index'}
SPEC={'390323','390307','390324','390322','390316','390325','390331','390327','390278','390272','390333','390025'}
WEB={'390323':'ashospital.net','390307':'edgewoodsurgical.com','391309':'barnes-kasson.org','390180':'crozerhealth.org','390278':'eaglevillehospital.org','391306':'endlesscare.org',
'390173':'irmc.org','390025':'kensingtonhospital.org','391308':'lecomhealth.com','390268':'mountnittany.org','390324':'physicianscaresurgicalhospital.com','390199':'pah.org',
'390322':'rothmanortho.com','390211':'sharonregionalmedical.org','390316':'sireading.com','390333':'ahn.org'}
cols=['No','CCN','Hospital (CMS name)','City','County','CMS type','Specialty hospital','Health system','Website','Price index file (cms-hpt.txt)','Name in hospital file','Price transparency page','Price file link (MRF)','File format','Link status','Notes']
out=[]
for i,m in enumerate(M,1):
    c=m['ccn']; h=H[c]; dom,sysn,loc,src,mrf=m['dom'],m['sys'],m['loc'],m['src'],m['mrf']
    if c=='390333': loc=src=mrf=''
    if c in IND:
        d,n,s=IND[c]; r=row(d,n) if n else next((r for r in R if r['domain']==d),None)
        dom,sysn=d,s
        if r: loc,src,mrf=r['location-name'],r.get('source-page-url',''),r.get('mrf-url','').strip()
        if c=='390237': loc='Regional Hospital of Scranton'; mrf='https://commonwealthhealth.net//wp-content/uploads/sheets/274564798_regional-hospital-of-scranton_standardcharges.csv'
    web=dom or WEB.get(c,'')
    idx=f'https://www.{dom}/cms-hpt.txt' if mrf else ''
    fmt=(re.search(r'\.(csv|json|zip|xlsx)',mrf.lower()) or [None,''])[1].upper() if mrf else ''
    if mrf and not fmt: fmt='Web page / other'
    status='Found in hospital index file' if mrf else ('Closed' if c=='390180' else 'Not found, locate manually')
    out.append([i,c,h['facility_name'],h['citytown'].title(),h['countyparish'].title(),'Critical access' if h['hospital_type'].startswith('Crit') else 'Acute care','Yes' if c in SPEC else 'No',
      sysn or 'Independent',f'https://www.{web}' if web else '',idx,loc,src,mrf,fmt,status,NOTE.get(c,'')])
# Links found on hospital price pages rather than in an index file
LINKS={'391304':'https://bucktailmedicalcenter.org/wp-content/uploads/2026/04/240701920_bucktail-medical-center_standardcharges-1.zip',
 '390268':'https://app-mnmc02saas3n8jpp001.cms.optimizely.com/globalassets/uploads/2026/01/240795682_mount-nittany-health_standardcharges-2.csv',
 '391308':'https://lecomhealth.com/wp-content/uploads/2024/08/CHARGEMASTER2022_0209.csv'}
for r in out:
    if r[1] in LINKS:
        r[12]=LINKS[r[1]]; r[14]='Found on hospital price page'
        if r[1]=='391308':
            r[15]='Only file posted is a 2022 chargemaster (outdated, legacy format); values entered by hand from rows US AAA SCREENING, US RETROPERITONEAL COMP, US AORTA'
config.REF.mkdir(parents=True,exist_ok=True)
with open(config.REF/'hospital_list.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(cols); w.writerows(out)
print('hospitals',len(out),'general acute (non-specialty acute care, open):',sum(1 for r in out if r[5]=='Acute care' and r[6]=='No' and r[14]!='Closed'))
