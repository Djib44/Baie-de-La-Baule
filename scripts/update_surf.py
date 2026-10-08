"""Cache Surf Sentinel's published easyREPORT values without recomputing ratings."""
import html
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SPOTS = {
    'p': ('Pornichet', 'Plage de Pornichet', 'https://www.surf-sentinel.com/surf-report/france/loire-atlantique/pornichet/plage-de-pornichet'),
    'g': ('La Govelle', 'La Govelle', 'https://www.surf-sentinel.com/surf-report/france/loire-atlantique/batz-sur-mer/la-govelle'),
}
TZ = ZoneInfo('Europe/Paris')

def text(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()

def parse(page):
    rows = []
    for day, clock, block in re.findall(r'<div\b[^>]*id="box-(\d{4}-\d{2}-\d{2})-(\d{3,4})"[^>]*>(.*?)</div>', page, re.S):
        rating = re.search(r'<strong>\s*([A-E])\s*<span[^>]*class="swell-metric"[^>]*>\s*([0-5])\s*</span>', block)
        if not rating:
            continue
        plain = text(block)
        def number(pattern):
            m = re.search(pattern, plain)
            if not m:
                raise ValueError('Missing forecast field: '+pattern)
            return float(m[1].replace(',', '.'))
        wind = re.search(r'Vent :.*?Orientation : (.*?) Houle :', plain)
        swell = re.search(r'Houle :.*?Orientation : (.*?) Plus la période', plain)
        hour = int(clock[:-2]); minute = int(clock[-2:])
        time = datetime.fromisoformat(f'{day}T{hour:02}:{minute:02}').replace(tzinfo=TZ).isoformat()
        rows.append(dict(time=time, rating=rating[1]+rating[2], quality=rating[1], size=int(rating[2]),
                         height=number(r'Houle : ([\d.,]+) m'), period=number(r'Période : ([\d.,]+) s'),
                         wind=number(r'Vent : ([\d.,]+) km/h'), gusts=number(r'Rafales : ([\d.,]+) km/h'),
                         wind_direction=wind[1].strip() if wind else '', swell_direction=swell[1].strip() if swell else ''))
    rows = sorted({r['time']: r for r in rows}.values(), key=lambda r:r['time'])
    if len(rows) < 6 or not any(datetime.fromisoformat(r['time']) > datetime.now(TZ) for r in rows):
        raise ValueError('Incomplete or expired Surf Sentinel forecast')
    return rows

def main():
    path = ROOT/'api/surf_sentinel.json'
    try:
        data = json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        data = {'source':'Surf Sentinel', 'spots':{}}
    for key, (name, reference, url) in SPOTS.items():
        try:
            with urllib.request.urlopen(url, timeout=40) as response:
                rows = parse(response.read().decode('utf-8'))
            data['spots'][key] = dict(name=name, reference=reference, url=url, fetched_at=datetime.now(TZ).isoformat(), rows=rows)
            print(name+': '+str(len(rows))+' forecast slots')
        except Exception as exc:
            print(name+': kept last valid cache ('+str(exc)+')')
    if not data['spots']:
        raise RuntimeError('No valid Surf Sentinel data')
    path.parent.mkdir(parents=True, exist_ok=True)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temp.replace(path)

if __name__ == '__main__':
    main()
