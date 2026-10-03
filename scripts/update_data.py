import os,re,json,datetime,requests
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; API=ROOT/"api"; API.mkdir(exist_ok=True)

# TIDES — official Ville de Pornichet page.
html=requests.get("https://ville-pornichet.fr/",timeout=30).text
txt=re.sub(r"<[^>]+>"," ",html)
txt=re.sub(r"\s+"," ",txt)
pat=re.compile(r"Marée (basse|haute) le ([A-Za-zÀ-ÿ]+) (\d{1,2}) à (\d{2}:\d{2}) \(Coeff:\s*(\d+)\)",re.I)
items=[]
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2)))
months={} # page does not expose month in tide snippet; order on page is used, then upcoming clock/date reconstructed.
for typ,daynum,hhmm,coef in pat.findall(txt):
    items.append({"type":"BM" if typ.lower()=="basse" else "PM","time":hhmm,"coefficient":int(coef)})
# Deduplicate and choose next items based on today's clock; official page typically exposes current adjacent tides.
uniq=[]
for x in items:
    if (x["type"],x["time"],x["coefficient"]) not in [(y["type"],y["time"],y["coefficient"]) for y in uniq]: uniq.append(x)
mins=lambda h:int(h[:2])*60+int(h[3:])
cur=now.hour*60+now.minute
future=sorted(uniq,key=lambda x:((mins(x["time"])-cur)%1440))
(API/"tides.json").write_text(json.dumps({"source":"Ville de Pornichet","updated":now.isoformat(),"next":future[:2]},ensure_ascii=False,indent=2))

# CLARITY — Copernicus Marine ZSD (Secchi depth). Requires repository secrets
# COPERNICUSMARINE_SERVICE_USERNAME and COPERNICUSMARINE_SERVICE_PASSWORD.
try:
 import copernicusmarine, xarray as xr
 user=os.environ["COPERNICUSMARINE_SERVICE_USERNAME"]; pwd=os.environ["COPERNICUSMARINE_SERVICE_PASSWORD"]
 end=datetime.datetime.now(datetime.timezone.utc); start=end-datetime.timedelta(days=8)
 fn=ROOT/"zsd.nc"
 copernicusmarine.subset(dataset_id="cmems_obs-oc_atl_bgc-transp_my_l3-multi-1km_P1D",
   variables=["ZSD"],minimum_longitude=-2.43,maximum_longitude=-2.37,
   minimum_latitude=47.22,maximum_latitude=47.28,start_datetime=start.isoformat(),end_datetime=end.isoformat(),
   output_filename=str(fn),username=user,password=pwd,overwrite=True)
 ds=xr.open_dataset(fn); z=ds["ZSD"]
 spatial=[d for d in z.dims if d.lower() not in ("time",)]
 mean=z.mean(dim=spatial,skipna=True)
 vals=[]
 for t,v in zip(ds["time"].values,mean.values):
  try: val=float(v)
  except: continue
  if val==val:
   vals.append((str(t)[:10],val))
 vals=vals[-3:][::-1]
 def rating(v):
  return "Très bonne" if v>=5 else "Bonne" if v>=3 else "Moyenne" if v>=2 else "Faible" if v>=1 else "Mauvaise"
 days=[]
 labels=["Aujourd’hui / dernière mesure","Mesure précédente","J-2 / mesure précédente"]
 for i,(d,v) in enumerate(vals): days.append({"label":labels[i],"date":d,"value":round(v,2),"rating":rating(v)})
 (API/"clarity.json").write_text(json.dumps({"source":"Copernicus Marine ZSD","updated":end.isoformat(),"days":days},ensure_ascii=False,indent=2))
except Exception as e:
 print("Clarity update skipped:",e)
