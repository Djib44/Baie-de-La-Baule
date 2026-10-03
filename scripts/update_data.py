import os,re,json,datetime,requests
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; API=ROOT/"api"; API.mkdir(exist_ok=True)

# TIDES — official Ville de Pornichet page.
html=requests.get("https://ville-pornichet.fr/",timeout=30).text
txt=re.sub(r"<[^>]+>"," ",html)
txt=re.sub(r"\s+"," ",txt)

pat=re.compile(
    r"Marée (basse|haute) le ([A-Za-zÀ-ÿ]+) (\d{1,2}) à "
    r"(\d{2}:\d{2}) \(Coeff:\s*(\d+)\)",
    re.I
)

now=datetime.datetime.now(
    datetime.timezone(datetime.timedelta(hours=2))
)

raw=pat.findall(txt)
items=[]

# Reconstruit la date réelle à partir du numéro du jour.
# La page fournit les marées autour de la date courante.
for typ,weekday,daynum,hhmm,coef in raw:
    daynum=int(daynum)

    possible_dates=[]
    for delta in range(-3,8):
        d=(now + datetime.timedelta(days=delta)).date()
        if d.day == daynum:
            possible_dates.append(d)

    if not possible_dates:
        continue

    # Date la plus proche de maintenant
    date=min(
        possible_dates,
        key=lambda d: abs((d-now.date()).days)
    )

    hour,minute=map(int,hhmm.split(":"))

    dt=datetime.datetime(
        date.year,
        date.month,
        date.day,
        hour,
        minute,
        tzinfo=now.tzinfo
    )

    items.append({
        "type":"BM" if typ.lower()=="basse" else "PM",
        "date":date.isoformat(),
        "time":hhmm,
        "coefficient":int(coef),
        "_datetime":dt
    })

# Suppression des éventuels doublons
uniq=[]
seen=set()

for x in items:
    key=(x["type"],x["date"],x["time"],x["coefficient"])
    if key not in seen:
        seen.add(key)
        uniq.append(x)

# On ne conserve que les marées réellement futures
future=[
    x for x in uniq
    if x["_datetime"] >= now
]

future.sort(key=lambda x:x["_datetime"])

# Nettoyage du champ interne _datetime
next_tides=[]

for x in future[:2]:
    next_tides.append({
        "type":x["type"],
        "date":x["date"],
        "time":x["time"],
        "coefficient":x["coefficient"]
    })

(API/"tides.json").write_text(
    json.dumps(
        {
            "source":"Ville de Pornichet",
            "updated":now.isoformat(),
            "next":next_tides
        },
        ensure_ascii=False,
        indent=2
    )
)
# COPERNICUSMARINE_SERVICE_USERNAME and COPERNICUSMARINE_SERVICE_PASSWORD.
try:
 import copernicusmarine, xarray as xr
 user=os.environ["COPERNICUSMARINE_SERVICE_USERNAME"]; pwd=os.environ["COPERNICUSMARINE_SERVICE_PASSWORD"]
end=datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=9)
start=end-datetime.timedelta(days=10)
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
