"""Refresh the temperature caches already consumed by the site."""
import datetime as dt
import html
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

API = Path(__file__).resolve().parents[1] / "api"
CITY_URL = "https://www.labaule.fr/decouvrir-et-sortir/meteo/"
BUOY_URL = "https://www.infoclimat.fr/mer/bouees.php?id=CETF04403"
PARIS = ZoneInfo("Europe/Paris")


def text(markup):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", markup))).strip()


def fetch(url):
    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as response:
        return response.read().decode("utf-8")


def parse_city(markup, now):
    plain = text(markup)
    months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    day = re.search(rf"\b(?:Lundi|Mardi|Mercredi|Jeudi|Vendredi|Samedi|Dimanche)\s+0?{now.day}\s+{months[now.month-1]}\s+Température\b", plain, re.I)
    if not day:
        raise ValueError("Current day's municipal weather not found")
    section = plain[day.end():]
    section = re.split(r"\b(?:Lundi|Mardi|Mercredi|Jeudi|Vendredi|Samedi|Dimanche)\s+\d", section, maxsplit=1)[0]

    def value(pattern):
        match = re.search(pattern, section, re.I)
        return float(match.group(1).replace(",", ".")) if match else None

    number = r"([+-]?\d+(?:[.,]\d+)?)"
    result = {
        "source": "Ville de La Baule", "url": CITY_URL,
        "updated": now.isoformat(), "date": now.date().isoformat(),
        "air_temperature": value(r"Air\s*:\s*" + number + r"\s*°C"),
        "water_temperature": value(r"Eau\s*:\s*" + number + r"\s*°C"),
        "wind_direction_deg": value(r"Vent\s+Orientation\s*:?\s*" + number + "°"),
        "wind_kmh": value(r"Vitesse\s*:\s*[\d.,]+\s*nd\s*\|\s*" + number + r"\s*km/h"),
        "gust_kmh": value(r"Rafale\s*:\s*[\d.,]+\s*nd\s*\|\s*" + number + r"\s*km/h"),
        "wave_direction_deg": value(r"Houle\s*:.*?Orientation\s*:\s*" + number),
        "wave_height": value(r"Hauteur\s*:\s*" + number + r"\s*m\b"),
        "wave_period": value(r"Période\s*:\s*" + number + r"\s*s\b"),
    }
    if any(result[key] is None for key in ("air_temperature", "water_temperature")):
        raise ValueError("Municipal temperatures missing")
    return result


def parse_buoy(markup, now):
    readings = []
    for row in re.findall(r'<tr\b[^>]*\bid="cdata\d+"[^>]*>(.*?)</tr>', markup, re.S):
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S)
        if len(cells) < 2:
            continue
        temperature = re.search(r"([+-]?\d+(?:[.,]\d+)?)\s*°C", text(cells[1]))
        title = re.search(r'title="([^"]*)"', cells[0])
        stamp = re.search(r"(\d{2})/(\d{2})/(\d{4}).*?(\d{1,2})h(\d{2}) UTC",
                          text(html.unescape(title.group(1))), re.S) if title else None
        if temperature and stamp:
            day, month, year, hour, minute = map(int, stamp.groups())
            observed = dt.datetime(year, month, day, hour, minute, tzinfo=dt.timezone.utc).astimezone(PARIS)
            if dt.timedelta(0) <= now - observed <= dt.timedelta(days=2):
                readings.append((observed, float(temperature.group(1).replace(",", "."))))
    if not readings:
        raise ValueError("No recent buoy water temperature")
    observed, temperature = max(readings)
    return {"temperature": temperature, "observed": observed.isoformat(),
            "source": "Cerema — bouée Plateau du Four 04403, diffusée par Infoclimat", "url": BUOY_URL}


def write(name, data):
    API.mkdir(exist_ok=True)
    target = API / name
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)


def main():
    now = dt.datetime.now(PARIS)
    water_path = API / "water.json"
    water = json.loads(water_path.read_text()) if water_path.exists() else {}
    try:
        city = parse_city(fetch(CITY_URL), now)
        write("labaule_weather.json", {key: city[key] for key in
                                      ("source", "url", "updated", "date", "air_temperature", "water_temperature")})
        condition_keys = ("wind_kmh", "gust_kmh", "wind_direction_deg", "wave_height", "wave_period", "wave_direction_deg")
        if all(city[key] is not None for key in condition_keys):
            write("fishing_conditions.json", {key: city[key] for key in
                                              ("source", "url", "updated", "date") + condition_keys})
        water["bay"] = {"temperature": city["water_temperature"], "source": city["source"],
                        "url": CITY_URL, "date": city["date"], "updated": city["updated"]}
        print("Municipal temperatures refreshed")
    except Exception as error:
        print("Municipal temperature update skipped:", error)
    try:
        water["buoy"] = parse_buoy(fetch(BUOY_URL), now)
        print("Buoy temperature refreshed")
    except Exception as error:
        print("Buoy temperature update skipped:", error)
    if water:
        write("water.json", water)


if __name__ == "__main__":
    main()
