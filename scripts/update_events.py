"""Collect public official agendas, preserving last good records on source failures."""
import concurrent.futures, datetime as dt, html, json, re, urllib.request
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
NOW=dt.datetime.now(ZoneInfo('Europe/Paris')); TODAY=NOW.date(); LIMIT=TODAY+dt.timedelta(days=90)
SOURCES={
 'tourism':('Office de tourisme La Baule–Presqu’île de Guérande','https://www.labaule-guerande.com/explorer/agenda/'),
 'tickets':('Office de tourisme — billetterie','https://reservation.labaule-guerande.com/spectacles-et-concerts.html'),
 'pornichet':('Pornichet Tourisme','https://www.pornichet.fr/sejourner/tous-les-evenements-pornichet'),
 'croisic':('Ville du Croisic','https://www.lecroisic.fr/fr/'),
 'pouliguen':('Ville du Pouliguen','https://www.lepouliguen.fr/evenements/'),
}
MONTHS={m:i+1 for i,m in enumerate(['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'])}
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def get(u):
 with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as r:return r.read().decode('utf-8')
def event(key,title,place,start,end,url,label=''):
 start=dt.date.fromisoformat(start[:10]);end=dt.date.fromisoformat((end or start.isoformat())[:10])
 if end<TODAY or start>LIMIT:return None
 if not url.startswith('https://'):return None
 return dict(title=clean(title),place=clean(place),date=start.isoformat(),end_date=end.isoformat(),date_label=label or (start.strftime('%d/%m/%Y') if start==end else f"Du {start:%d/%m/%Y} au {end:%d/%m/%Y}"),url=url,source=SOURCES[key][0],source_key=key)
def frdate(s):
 m=re.search(r'(\d{1,2})\s+('+'|'.join(MONTHS)+r')\s+(\d{4})',clean(s),re.I)
 return dt.date(int(m[3]),MONTHS[m[2].lower()],int(m[1])).isoformat() if m else None
def tourism_detail(u):
 s=get(u);out=[]
 for block in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',s,re.S):
  try:d=json.loads(block)
  except ValueError:continue
  for x in d.get('@graph',[]):
   if x.get('@type')!='Event':continue
   place=x.get('location',{}).get('address',{}).get('addressLocality','')
   periods=re.findall(r'<[^>]*period-parser[^>]*\bstart="([^"]+)"[^>]*\bend="([^"]+)"',s)
   if not periods:periods=[(x.get('startDate',''),x.get('endDate',''))]
   for start,end in set(periods):
    if start:
     e=event('tourism',x['name'],place,start,end,u)
     if e:out.append(e)
 return out

def collect(key):
 name,u=SOURCES[key];s=re.sub(r'<!--.*?-->','',get(u),flags=re.S);out=[]
 if key=='tourism':
  urls=set(re.findall(r'href="(https://www\.labaule-guerande\.com/offres/[^"#]+)"',s))
  # Retain linked upcoming offers so they remain visible after leaving the first agenda page.
  cache=ROOT/'api/events.json'
  if cache.exists():
   urls.update(e['url'] for e in json.loads(cache.read_text()).get('events',[]) if e.get('source_key')=='tourism' and e.get('end_date',e['date'])>=TODAY.isoformat())
  urls.update([
   'https://www.labaule-guerande.com/offres/randonnee-gourmande-saveurs-doctobre-batz-sur-mer-fr-6790037/',
   'https://www.labaule-guerande.com/offres/enquete-au-village-saveurs-doctobre-batz-sur-mer-fr-6790058/',
   'https://www.labaule-guerande.com/offres/cum-grano-salis-avec-un-grain-de-sel-saveurs-doctobre-batz-sur-mer-fr-6790066/',
  ])
  with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
   for results in pool.map(tourism_detail,sorted(urls)):out.extend(results)
 elif key=='pornichet':
  for block in re.findall(r'<article\b[^>]*>(.*?)</article>',s,re.S):
   h=re.search(r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',block,re.S)
   if not h:continue
   for start,end,label in re.findall(r'<li[^>]*data-date-start="(\d+)"[^>]*data-date-end="(\d+)"[^>]*>(.*?)</li>',block,re.S):
    dates=[dt.datetime.fromtimestamp(int(t),ZoneInfo('Europe/Paris')).date().isoformat() for t in (start,end)]
    e=event(key,h[2],'Pornichet',*dates,urljoin(u,html.unescape(h[1])),clean(label))
    if e:out.append(e)
 elif key=='croisic':
  for link,block in re.findall(r'<a[^>]*href="([^"]*/ev/[^"#]+)"[^>]*>(.*?)</a>',s,re.S):
   title=re.search(r'<h3[^>]*>(.*?)</h3>',block,re.S);dates=re.findall(r'\d{2}/\d{2}/\d{4}',clean(block))
   if not title or not dates:continue
   a=[dt.datetime.strptime(t,'%d/%m/%Y').date().isoformat() for t in dates]
   e=event(key,title[1],'Le Croisic',a[0],a[-1],urljoin(u,link))
   if e:out.append(e)
 elif key=='tickets':
  for title,block in re.findall(r'<h2\b[^>]*>(.*?)</h2>(.*?)(?=<h2\b|$)',s,re.S):
   h=re.search(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',title,re.S)
   place=re.search(r'<span class="sous-titre">(.*?)</span>\s*</span>',block,re.S)
   date=re.search(r'<p class="date"[^>]*>(.*?)</p>',block,re.S)
   if not h or not place or not date:continue
   d=frdate(date[1])
   if d:
    e=event(key,h[2],clean(place[1]),d,d,urljoin(u,html.unescape(h[1]).split('?')[0]))
    if e:out.append(e)
 elif key=='pouliguen':
  months={'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
  for title,dd,mon,yy in re.findall(r'<h2[^>]*>(.*?)</h2>.*?(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})',s,re.I|re.S):
   d=dt.date(int(yy),months[mon.title()],int(dd)).isoformat();h=re.search(r'href="([^"]+)"',title)
   e=event(key,title,'Le Pouliguen',d,d,urljoin(u,html.unescape(h[1])) if h else u)
   if e:out.append(e)
 if not out:raise ValueError('No dated events parsed')
 return out

def main():
 p=ROOT/'api/events.json';previous=json.loads(p.read_text()) if p.exists() else {};events=[];status=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
  jobs={pool.submit(collect,key):key for key in SOURCES}
  for job in concurrent.futures.as_completed(jobs):
   key=jobs[job]
   try:rows=job.result();state='ok'
   except Exception as ex:
    print(key,ex);rows=[e for e in previous.get('events',[]) if e.get('source_key')==key and e.get('end_date',e.get('date',''))>=TODAY.isoformat()];state='cached' if rows else 'unavailable'
   events.extend(rows);status.append(dict(name=SOURCES[key][0],url=SOURCES[key][1],status=state,count=len(rows)))
 unique={}
 for e in events:
  if e['place']=='Saint-Nazaire':continue
  unique.setdefault((e['title'].casefold(),e['place'].casefold(),e['date']),e)
 if not unique:raise RuntimeError('All event sources failed; existing cache retained')
 data=dict(source='Agendas officiels de la presqu’île',updated=NOW.isoformat(),coverage_start=TODAY.isoformat(),coverage_end=LIMIT.isoformat(),sources=status,events=sorted(unique.values(),key=lambda e:(max(e['date'],TODAY.isoformat()),e['place'],e['title'])),agenda_url=SOURCES['tourism'][1])
 p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');print(len(data['events']),'events',sorted({e['place'] for e in data['events']}))
if __name__=='__main__':main()
