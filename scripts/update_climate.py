"""Refresh climate caches without replacing good files on API failures."""
import datetime as dt,json,urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1];now=dt.datetime.now(ZoneInfo('Europe/Paris'))
def get(url):
 with urllib.request.urlopen(url,timeout=45) as r:return json.load(r)
def write(path,d):
 daily=d['daily'];assert daily['time'] and len(daily['time'])==len(daily['temperature_2m_mean'])==len(daily['precipitation_sum'])
 d['updated']=now.isoformat();path.write_text(json.dumps(d,ensure_ascii=False)+'\n')
def main():
 base='latitude=47.29&longitude=-2.39&daily=temperature_2m_mean,precipitation_sum&timezone=Europe%2FParis'
 path=ROOT/'api/climate_history.json'
 try:
  old=json.loads(path.read_text()) if path.exists() else {}
  if old.get('through_year')!=now.year-1:
   d=get(f'https://archive-api.open-meteo.com/v1/archive?{base}&start_date=2000-01-01&end_date={now.year-1}-12-31&models=era5')
   ids=[i for i,t in enumerate(d['daily']['time']) if t[5:7]=='10']
   d['daily']={k:[v[i] for i in ids] for k,v in d['daily'].items()};d['through_year']=now.year-1;write(path,d)
 except Exception as e:print('Historical cache retained:',e)
 try:
  d=get(f'https://api.open-meteo.com/v1/forecast?{base}&past_days=31&forecast_days=1');write(ROOT/'api/climate_current.json',d)
 except Exception as e:print('Current climate cache retained:',e)
if __name__=='__main__':main()
