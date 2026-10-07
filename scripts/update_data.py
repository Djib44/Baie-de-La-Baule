import os,re,json,datetime,requests
from zoneinfo import ZoneInfo
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; API=ROOT/"api"; API.mkdir(exist_ok=True)

# TIDES — 7-day table for Pornichet.
# Source: maree.info/116. The page exposes a 7-day tide table.
html=requests.get("https://maree.info/116",timeout=30,headers={"User-Agent":"Mozilla/5.0"}).text
txt=re.sub(r"<[^>]+>"," ",html)
txt=re.sub(r"&nbsp;"," ",txt)
txt=re.sub(r"\s+"," ",txt)

now=datetime.datetime.now(ZoneInfo("Europe/Paris"))
fr_months={"janvier":1,"février":2,"mars":3,"avril":4,"mai":5,"juin":6,"juillet":7,"août":8,"septembre":9,"octobre":10,"novembre":11,"décembre":12}

# First try to recover the current month/year shown on the page.
mdate=re.search(r"(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})",txt,re.I)
month=fr_months.get(mdate.group(1).lower(),now.month) if mdate else now.month
year=int(mdate.group(2)) if mdate else now.year

txt=txt.split("PM : Pleine Mer BM : Basse Mer",1)[0]

# Parse day rows from the tide table. A row has a day, 3–4 times, heights and 1–2 coefficients.
# We use the visible text sequence between successive day labels.
daypat=re.compile(r"\b(?:Lun|Mar|Mer|Jeu|Ven|Sam|Dim)\.?\s*(\d{1,2})\b",re.I)
matches=list(daypat.finditer(txt))
tides=[]
for i,m in enumerate(matches[:8]):
    day=int(m.group(1))
    chunk=txt[m.end():matches[i+1].start() if i+1<len(matches) else m.end()+500]
    times=re.findall(r"\b(\d{1,2})h(\d{2})\b",chunk)
    heights=[float(x.replace(",",".")) for x in re.findall(r"(\d+[,.]\d+)\s*m\b",chunk)]
    coeffs=[int(x) for x in re.findall(r"\b(1[01]\d|120|[2-9]\d)\b",chunk)]
    # Keep only plausible tide coefficients and avoid numbers embedded in heights/times.
    coeffs=[c for c in coeffs if 20<=c<=120]
    if not 3<=len(times)<=4 or len(times)!=len(heights):
        continue
    try:
        date=datetime.date(year,month,day)
    except ValueError:
        continue

    # The Pornichet table alternates BM/PM. Infer first type from height:
    first_type="BM" if heights[0] < heights[1] else "PM"
    types=[]
    typ=first_type
    for _ in times[:len(heights)]:
        types.append(typ)
        typ="PM" if typ=="BM" else "BM"

    # Coefficients conventionally apply to high waters. Associate each event with
    # the nearest day's coefficient so every candidate slot has a usable coefficient.
    pm_indices=[j for j,t in enumerate(types) if t=="PM"]
    pm_coeff={}
    for j,c in zip(pm_indices,coeffs[:len(pm_indices)]):
        pm_coeff[j]=c
    for j,(hh,mm) in enumerate(times[:len(heights)]):
        nearest=min(pm_indices,key=lambda k:abs(k-j)) if pm_indices else None
        coef=pm_coeff.get(nearest, coeffs[0] if coeffs else None)
        dt=datetime.datetime(date.year,date.month,date.day,int(hh),int(mm),tzinfo=now.tzinfo)
        if dt>=now and dt<=now+datetime.timedelta(days=7):
            tides.append({"type":types[j],"date":date.isoformat(),"time":f"{int(hh):02d}:{mm}","height":round(heights[j],2),"coefficient":coef,"_dt":dt})

# Fallback to Ville de Pornichet for the immediate tides if 7-day parsing fails.
if len(tides)<4:
    html2=requests.get("https://ville-pornichet.fr/",timeout=30).text
    txt2=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",html2))
    pat=re.compile(r"Marée (basse|haute) le ([A-Za-zÀ-ÿ]+) (\d{1,2}) à (\d{2}:\d{2}) \(Coeff:\s*(\d+)\)",re.I)
    tides=[]
    for typ,weekday,daynum,hhmm,coef in pat.findall(txt2):
        daynum=int(daynum)
        poss=[(now+datetime.timedelta(days=d)).date() for d in range(-1,8) if (now+datetime.timedelta(days=d)).day==daynum]
        if not poss: continue
        date=min(poss,key=lambda d:abs((d-now.date()).days))
        hh,mm=map(int,hhmm.split(":"))
        dt=datetime.datetime(date.year,date.month,date.day,hh,mm,tzinfo=now.tzinfo)
        if dt>=now:
            tides.append({"type":"BM" if typ.lower()=="basse" else "PM","date":date.isoformat(),"time":hhmm,"coefficient":int(coef),"_dt":dt})

tides.sort(key=lambda x:x["_dt"])
clean=[{k:v for k,v in x.items() if k!="_dt"} for x in tides]
if clean:
    (API/"tides.json").write_text(json.dumps({"source":"maree.info Pornichet / fallback Ville de Pornichet","updated":now.isoformat(),"next":clean[:2],"week":clean},ensure_ascii=False,indent=2))
else:
    print("Tide source unavailable: last valid cache retained")

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
    mean=z.mean(dim=spatial,skipna=True); vals=[]
    for t,v in zip(ds["time"].values,mean.values):
        try: val=float(v)
        except: continue
        if val==val: vals.append((str(t)[:10],val))
    vals=vals[-3:][::-1]
    def rating(v): return "Très bonne" if v>=5 else "Bonne" if v>=3 else "Moyenne" if v>=2 else "Faible" if v>=1 else "Mauvaise"
    days=[{"date":d,"value":round(v,2),"rating":rating(v)} for d,v in vals]
    (API/"clarity.json").write_text(json.dumps({"source":"Copernicus Marine ZSD","updated":end.isoformat(),"days":days},ensure_ascii=False,indent=2))
except Exception as e:
    print("Clarity update skipped:",e)

# Events are refreshed separately by scripts/update_events.py.
# ATMO FRANCE — qualité de l’air
# Référence utilisée : Saint-Nazaire (code INSEE 44184)
# car l'indice communal de La Baule n'est pas disponible dans le flux ATMO testé.

try:
    atmo_user = os.environ["ATMO_USERNAME"]
    atmo_password = os.environ["ATMO_PASSWORD"]

    # 1. Connexion à l'API ATMO et récupération du JWT
    login_url = "https://admindata.atmo-france.org/api/login"

    login_response = requests.post(
        login_url,
        json={
            "username": atmo_user,
            "password": atmo_password
        },
        timeout=30
    )
    login_response.raise_for_status()

    token = login_response.json()["token"]

    # 2. Récupération de l'indice ATMO de Saint-Nazaire
    atmo_url = "https://admindata.atmo-france.org/api/v2/data/indices/atmo"

    today = now.date().isoformat()

    response = requests.get(
        atmo_url,
        params={
            "format": "geojson",
            "date": today,
            "code_zone": "44184"
        },
        headers={
            "Authorization": f"Bearer {token}"
        },
        timeout=30
    )

    response.raise_for_status()
    data = response.json()

    features = data.get("features", [])

    if not features:
        raise RuntimeError("Aucun indice ATMO disponible pour Saint-Nazaire")

    # On prend l'enregistrement le plus récent
    feature = max(
        features,
        key=lambda f: f.get("properties", {}).get("date_maj", "")
    )

    p = feature["properties"]

    atmo = {
        "source": p.get("source", "Air Pays de la Loire"),
        "reference": "Saint-Nazaire",
        "code_zone": p.get("code_zone", "44184"),
        "updated": p.get("date_maj"),
        "date": p.get("date_ech", today),
        "index": p.get("code_qual"),
        "label": p.get("lib_qual"),
        "color": p.get("coul_qual"),
        "pollutants": {
            "NO2": p.get("code_no2"),
            "O3": p.get("code_o3"),
            "PM10": p.get("code_pm10"),
            "PM2.5": p.get("code_pm25"),
            "SO2": p.get("code_so2")
        }
    }

    (API/"air_quality.json").write_text(
        json.dumps(
            atmo,
            ensure_ascii=False,
            indent=2
        )
    )

    print(
        f"ATMO OK: Saint-Nazaire — "
        f"{atmo['label']} (indice {atmo['index']})"
    )

except Exception as e:
    print("ATMO update skipped:", e)
