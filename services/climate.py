"""Location climate and water context for crop guidance.

NASA POWER supplies temperature, rainfall, humidity, sunlight, and root-zone
wetness. USGS supplies nearby streamflow and groundwater depth. OpenET supplies
satellite evapotranspiration when OPENET_API_KEY is set and the point is inside
the western United States.
"""
import json
import math
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

POWER_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"
USGS_ITEMS = "https://api.waterdata.usgs.gov/ogcapi/v1/collections/{collection}/items"
OPENET_URL = "https://openet-api.org/raster/timeseries/point"
USER_AGENT = "falconXNasa-educational-demo/1.0 (contact: local-development)"
FILL = -999

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
MONTH_DAYS = {
    "JAN": 31, "FEB": 28, "MAR": 31, "APR": 30, "MAY": 31, "JUN": 30,
    "JUL": 31, "AUG": 31, "SEP": 30, "OCT": 31, "NOV": 30, "DEC": 31,
}
SEASON_MONTHS = {
    "spring": ["MAR", "APR", "MAY"],
    "summer": ["JUN", "JUL", "AUG"],
    "fall": ["SEP", "OCT", "NOV"],
    "winter": ["DEC", "JAN", "FEB"],
}


def _get_json(url, timeout, headers=None):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})})
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _post_json(url, payload, timeout, headers=None):
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
            **(headers or {}),
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _mean(values):
    usable = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number <= FILL + 1:
            continue
        usable.append(number)
    if not usable:
        return None
    return sum(usable) / len(usable)


def _season_keys(season):
    return SEASON_MONTHS.get((season or "").lower(), SEASON_MONTHS["summer"])


def _season_value(series, season):
    if not isinstance(series, dict):
        return None
    return _mean(series.get(key) for key in _season_keys(season))


def _c_to_f(celsius):
    if celsius is None:
        return None
    return celsius * 9 / 5 + 32


def _fmt(number, digits=1):
    if number is None:
        return None
    return f"{number:.{digits}f}"


def in_usgs_area(latitude, longitude):
    conus = 24 <= latitude <= 50 and -125 <= longitude <= -66
    alaska = 51 <= latitude <= 72 and -170 <= longitude <= -129
    hawaii = 18 <= latitude <= 23 and -161 <= longitude <= -154
    return conus or alaska or hawaii


def in_openet_area(latitude, longitude):
    """Approximate OpenET western-state footprint."""
    return 25 <= latitude <= 49 and -125 <= longitude <= -94


def fetch_power(latitude, longitude, season):
    params = urlencode({
        "parameters": "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN,GWETROOT",
        "community": "AG",
        "longitude": f"{longitude:.4f}",
        "latitude": f"{latitude:.4f}",
        "format": "JSON",
    })
    payload = _get_json(f"{POWER_URL}?{params}", timeout=12)
    series = payload["properties"]["parameter"]
    temperature = _season_value(series.get("T2M"), season)
    precipitation = _season_value(series.get("PRECTOTCORR"), season)
    wetness = _season_value(series.get("GWETROOT"), season)
    keys = _season_keys(season)
    days = sum(MONTH_DAYS[key] for key in keys)
    season_rain = None if precipitation is None else precipitation * days
    summary = {
        "available": temperature is not None or precipitation is not None,
        "season": season,
        "temperature_c": None if temperature is None else round(temperature, 2),
        "temperature_f": None if temperature is None else round(_c_to_f(temperature), 1),
        "temperature_max_c": _round(_season_value(series.get("T2M_MAX"), season)),
        "temperature_min_c": _round(_season_value(series.get("T2M_MIN"), season)),
        "precipitation_mm_day": _round(precipitation, 2),
        "season_precipitation_mm": None if season_rain is None else round(season_rain, 1),
        "humidity_percent": _round(_season_value(series.get("RH2M"), season)),
        "solar_mj": _round(_season_value(series.get("ALLSKY_SFC_SW_DWN"), season), 2),
        "root_zone_wetness": _round(wetness, 2),
        "annual_temperature_c": _round(_mean([series.get("T2M", {}).get("ANN")])),
        "annual_precipitation_mm_day": _round(_mean([series.get("PRECTOTCORR", {}).get("ANN")]), 2),
        "source": "NASA POWER agroclimatology (long-term monthly climatology)",
    }
    return summary


def _round(value, digits=2):
    if value is None:
        return None
    return round(value, digits)


def _bbox(latitude, longitude, kilometers):
    delta_lat = kilometers / 111.0
    delta_lon = kilometers / (111.0 * max(0.2, math.cos(math.radians(latitude))))
    west, south = longitude - delta_lon, latitude - delta_lat
    east, north = longitude + delta_lon, latitude + delta_lat
    return f"{west:.4f},{south:.4f},{east:.4f},{north:.4f}"


def _distance_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _parse_day(value):
    text = str(value or "")[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _usgs_features(collection, latitude, longitude, parameter_code, kilometers, api_key):
    params = {
        "f": "json",
        "limit": 40,
        "bbox": _bbox(latitude, longitude, kilometers),
        "parameter_code": parameter_code,
    }
    if api_key:
        params["api_key"] = api_key
    url = USGS_ITEMS.format(collection=collection) + "?" + urlencode(params)
    payload = _get_json(url, timeout=12)
    found = []
    today = date.today()
    for feature in payload.get("features") or []:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates") or []
        if len(coords) < 2:
            continue
        try:
            value = float(props.get("value"))
            site_lon, site_lat = float(coords[0]), float(coords[1])
        except (TypeError, ValueError):
            continue
        observed = _parse_day(props.get("time"))
        age_days = None if observed is None else (today - observed).days
        found.append({
            "id": props.get("monitoring_location_id") or "",
            "parameter_code": props.get("parameter_code") or parameter_code,
            "value": value,
            "unit": props.get("unit_of_measure") or "",
            "time": props.get("time"),
            "age_days": age_days,
            "recent": age_days is not None and age_days <= 45,
            "distance_km": round(_distance_km(latitude, longitude, site_lat, site_lon), 1),
            "latitude": site_lat,
            "longitude": site_lon,
        })
    found.sort(key=lambda item: (0 if item["recent"] else 1, item["distance_km"]))
    return found


def _site_name(site_id, api_key):
    if not site_id:
        return ""
    params = {"f": "json", "limit": 1, "monitoring_location_id": site_id}
    if api_key:
        params["api_key"] = api_key
    url = USGS_ITEMS.format(collection="monitoring-locations") + "?" + urlencode(params)
    try:
        payload = _get_json(url, timeout=8)
    except Exception:
        return ""
    features = payload.get("features") or []
    if not features:
        return ""
    return (features[0].get("properties") or {}).get("monitoring_location_name") or ""


def fetch_usgs(latitude, longitude, country_code=""):
    if country_code and country_code not in {"us", "pr", "gu", "vi", "as", "mp"}:
        return {
            "available": False,
            "observations": [],
            "note": "USGS water monitoring covers the United States, so no gage was queried for this country.",
            "source": "USGS Water Data API",
        }
    if not country_code and not in_usgs_area(latitude, longitude):
        return {
            "available": False,
            "observations": [],
            "note": "This point is outside the USGS United States monitoring footprint.",
            "source": "USGS Water Data API",
        }
    api_key = os.environ.get("USGS_API_KEY", "").strip()
    chosen = []
    for parameter, kind in (("00060", "streamflow"), ("72019", "groundwater")):
        matches = []
        for kilometers in (25, 60):
            for collection in ("latest-continuous", "latest-daily"):
                try:
                    matches = _usgs_features(collection, latitude, longitude, parameter, kilometers, api_key)
                except Exception:
                    matches = []
                if matches:
                    break
            if matches:
                break
        if not matches:
            continue
        best = matches[0]
        best["kind"] = kind
        best["name"] = _site_name(best["id"], api_key)
        chosen.append(best)
    note = ""
    if not chosen:
        note = "No USGS streamflow or groundwater reading was found within about 60 km."
    elif not api_key:
        note = "USGS was queried without an API key. Add USGS_API_KEY to .env if you need a higher rate limit."
    return {
        "available": bool(chosen),
        "observations": chosen,
        "note": note,
        "source": "USGS Water Data OGC API (latest continuous, then latest daily)",
    }


def _openet_rows(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "timeseries", "results", "features", "values"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def _row_et(row):
    if not isinstance(row, dict):
        return None, None
    when = row.get("time") or row.get("date") or row.get("datetime") or row.get("Date")
    for key in ("et", "ET", "value", "mean", "et_mm"):
        if row.get(key) not in (None, ""):
            try:
                return when, float(row[key])
            except (TypeError, ValueError):
                return when, None
    return when, None


def fetch_openet(latitude, longitude, country_code=""):
    source = "OpenET ensemble evapotranspiration (gridMET reference ET)"
    if country_code and country_code != "us":
        return {"available": False, "configured": False, "note": "OpenET covers the western United States.", "source": source}
    if not in_openet_area(latitude, longitude):
        return {
            "available": False,
            "configured": bool(os.environ.get("OPENET_API_KEY", "").strip()),
            "note": "OpenET covers the western United States, so evapotranspiration was not requested here.",
            "source": source,
        }
    api_key = os.environ.get("OPENET_API_KEY", "").strip()
    if not api_key:
        return {
            "available": False,
            "configured": False,
            "note": "Add OPENET_API_KEY to the project .env file to include OpenET evapotranspiration.",
            "source": source,
        }
    year = date.today().year - 1
    payload = {
        "date_range": [f"{year}-01-01", f"{year}-12-31"],
        "interval": "monthly",
        "geometry": [round(longitude, 5), round(latitude, 5)],
        "model": "Ensemble",
        "variable": "ET",
        "reference_et": "gridMET",
        "units": "mm",
        "file_format": "JSON",
    }
    try:
        body = _post_json(OPENET_URL, payload, timeout=20, headers={"Authorization": api_key})
    except HTTPError as exc:
        if exc.code in (401, 403):
            message = "OpenET rejected OPENET_API_KEY. Check the key in the .env file."
        else:
            message = f"OpenET did not return data for this point (HTTP {exc.code})."
        return {"available": False, "configured": True, "note": message, "source": source}
    except Exception:
        return {
            "available": False,
            "configured": True,
            "note": "OpenET could not be reached. The rest of the recommendation still uses NASA POWER.",
            "source": source,
        }
    monthly = {}
    for row in _openet_rows(body):
        when, amount = _row_et(row)
        observed = _parse_day(when)
        if observed is None or amount is None or amount < 0:
            continue
        monthly[MONTHS[observed.month - 1]] = monthly.get(MONTHS[observed.month - 1], 0) + amount
    if not monthly:
        return {
            "available": False,
            "configured": True,
            "note": f"OpenET responded for {year}, but no monthly evapotranspiration values were recognized.",
            "source": source,
        }
    return {
        "available": True,
        "configured": True,
        "year": year,
        "monthly_mm": {key: round(value, 1) for key, value in monthly.items()},
        "annual_et_mm": round(sum(monthly.values()), 1),
        "note": "",
        "source": source,
    }


def empty_climate():
    return {"available": False, "lines": [], "power": None, "usgs": None, "openet": None}


def fetch_climate(latitude, longitude, season, country_code=""):
    """Load POWER, USGS, and OpenET together. A failed source does not fail the others."""
    season_name = (season or "Summer").strip()

    def safe(fn):
        try:
            return fn()
        except Exception as exc:
            return {"available": False, "note": str(exc) or "unavailable"}

    with ThreadPoolExecutor(max_workers=3) as pool:
        power_job = pool.submit(lambda: safe(lambda: fetch_power(latitude, longitude, season_name)))
        usgs_job = pool.submit(lambda: safe(lambda: fetch_usgs(latitude, longitude, country_code)))
        openet_job = pool.submit(lambda: safe(lambda: fetch_openet(latitude, longitude, country_code)))
        power = power_job.result()
        usgs = usgs_job.result()
        openet = openet_job.result()
    if openet.get("available") and power.get("season_precipitation_mm") is not None:
        season_et = _season_et(openet, season_name)
        if season_et is not None:
            openet["season_et_mm"] = round(season_et, 1)
            openet["season_water_balance_mm"] = round(power["season_precipitation_mm"] - season_et, 1)
    climate = {
        "available": bool(power.get("available") or usgs.get("available") or openet.get("available")),
        "latitude": latitude,
        "longitude": longitude,
        "power": power,
        "usgs": usgs,
        "openet": openet,
    }
    climate["lines"] = describe_climate(climate, season_name)
    return climate


def _season_et(openet, season):
    monthly = openet.get("monthly_mm") or {}
    values = [monthly[key] for key in _season_keys(season) if key in monthly]
    if not values:
        return None
    return sum(values)


def describe_climate(climate, season):
    """Plain-language lines for the result panel."""
    if not climate:
        return []
    lines = []
    power = climate.get("power") or {}
    if power.get("available"):
        season_label = (season or power.get("season") or "").lower()
        temp = _fmt(power.get("temperature_f"), 1)
        temp_c = _fmt(power.get("temperature_c"), 1)
        high = _fmt(_c_to_f(power.get("temperature_max_c")), 0)
        low = _fmt(_c_to_f(power.get("temperature_min_c")), 0)
        if temp:
            span = f" Typical daily max {high}°F and min {low}°F." if high and low else ""
            lines.append(
                f"NASA POWER {season_label} temperature averages {temp}°F ({temp_c}°C).{span}"
            )
        rain = power.get("season_precipitation_mm")
        daily = power.get("precipitation_mm_day")
        wetness = power.get("root_zone_wetness")
        if rain is not None:
            wet = f" Root-zone soil wetness averages {wetness} on a 0–1 scale." if wetness is not None else ""
            lines.append(
                f"NASA POWER {season_label} rainfall averages {daily} mm/day, about {rain:.0f} mm over the season.{wet}"
            )
        humidity = power.get("humidity_percent")
        solar = power.get("solar_mj")
        if humidity is not None or solar is not None:
            bits = []
            if humidity is not None:
                bits.append(f"relative humidity {humidity:.0f}%")
            if solar is not None:
                bits.append(f"sunlight {solar} MJ/m²/day")
            lines.append("NASA POWER also reports " + " and ".join(bits) + ".")
    elif power.get("note"):
        lines.append(f"NASA POWER climate was unavailable ({power['note']}).")

    usgs = climate.get("usgs") or {}
    for obs in usgs.get("observations") or []:
        label = obs.get("name") or obs.get("id") or "USGS site"
        distance = obs.get("distance_km")
        when = str(obs.get("time") or "")[:10]
        stale = "" if obs.get("recent") else f" Last value is from {when} and may be an inactive record."
        if obs.get("kind") == "groundwater":
            lines.append(
                f"Nearest USGS groundwater depth is {obs['value']:.1f} {obs.get('unit') or 'ft'} "
                f"at {label}, {distance} km away, on {when}.{stale}"
            )
        else:
            lines.append(
                f"Nearest USGS streamflow is {obs['value']:.0f} {obs.get('unit') or 'ft^3/s'} "
                f"at {label}, {distance} km away, on {when}.{stale}"
            )
    if not usgs.get("observations") and usgs.get("note"):
        lines.append(usgs["note"])

    openet = climate.get("openet") or {}
    if openet.get("available"):
        balance = openet.get("season_water_balance_mm")
        season_et = openet.get("season_et_mm")
        annual = openet.get("annual_et_mm")
        year = openet.get("year")
        text = f"OpenET ensemble evapotranspiration for {year} totals about {annual} mm."
        if season_et is not None:
            text += f" The selected season accounts for about {season_et:.0f} mm."
        if balance is not None:
            if balance < -20:
                text += (
                    f" Rainfall minus evapotranspiration is about {balance:.0f} mm, "
                    "so irrigation is likely part of the seasonal water budget."
                )
            else:
                text += f" Rainfall minus evapotranspiration is about {balance:.0f} mm for that season."
        lines.append(text)
    elif openet.get("note"):
        lines.append(openet["note"])
    return lines


def water_need(text):
    """Map a variety water note onto high, moderate, or low."""
    lowered = (text or "").lower()
    if not lowered.strip():
        return None
    if "drought" in lowered and "high" not in lowered:
        return "low"
    if lowered.startswith("low") or " low " in f" {lowered} ":
        return "low"
    if "high" in lowered or "consistent moisture" in lowered or "per week" in lowered:
        return "high"
    return "moderate"


def temperature_preference(growing_season):
    lowered = (growing_season or "").lower()
    if "cool" in lowered:
        return "cool"
    if "warm" in lowered or lowered.strip() == "summer":
        return "warm"
    return "flexible"


def _usgs_moisture_signal(usgs):
    """Map recent nearby USGS readings to dry, wet, moderate, or None.

    Groundwater depth (ft below land surface): deeper → drier signal.
    Streamflow is only a soft regional cue when the gage is close and recent.
    """
    if not usgs or not usgs.get("available"):
        return None
    dry_votes = 0
    wet_votes = 0
    saw = False
    for obs in usgs.get("observations") or []:
        if not obs.get("recent"):
            continue
        try:
            value = float(obs.get("value"))
            distance = float(obs.get("distance_km") or 99)
        except (TypeError, ValueError):
            continue
        if obs.get("kind") == "groundwater":
            saw = True
            # Deeper water table → drier local moisture cue.
            dry_votes += value >= 25
            wet_votes += value <= 8
        elif obs.get("kind") == "streamflow" and distance <= 40:
            saw = True
            # Very low nearby streamflow can hint at a dry regional setting.
            dry_votes += value < 5
            wet_votes += value > 200
    if not saw:
        return None
    if dry_votes > wet_votes and dry_votes:
        return "dry"
    if wet_votes > dry_votes and wet_votes:
        return "wet"
    return "moderate"


def _dryness(power, openet, usgs=None):
    """Return dry, wet, or moderate from rainfall, soil wetness, ET deficit, and USGS."""
    rain = None if not power else power.get("precipitation_mm_day")
    wetness = None if not power else power.get("root_zone_wetness")
    balance = None if not openet else openet.get("season_water_balance_mm")
    usgs_signal = _usgs_moisture_signal(usgs)
    dry_votes = 0
    wet_votes = 0
    if rain is not None:
        dry_votes += rain < 1.2
        wet_votes += rain > 3
    if wetness is not None:
        dry_votes += wetness < 0.35
        wet_votes += wetness > 0.55
    if balance is not None:
        dry_votes += balance < -25
        wet_votes += balance > 20
    if usgs_signal == "dry":
        dry_votes += 1
    elif usgs_signal == "wet":
        wet_votes += 1
    if dry_votes > wet_votes and dry_votes:
        return "dry"
    if wet_votes > dry_votes and wet_votes:
        return "wet"
    if rain is None and wetness is None and balance is None and usgs_signal is None:
        return None
    return "moderate"


def score_climate(water_requirement, growing_season, climate):
    """Return score points plus short crop-specific notes. Missing data is not penalized."""
    power = (climate or {}).get("power") or {}
    openet = (climate or {}).get("openet") or {}
    usgs = (climate or {}).get("usgs") or {}
    if not power.get("available") and not openet.get("available") and not usgs.get("available"):
        return {"earned": 0, "possible": 0, "issues": [], "evidence": [], "improvements": []}

    earned = 0.0
    possible = 0.0
    issues = []
    evidence = []
    improvements = []
    need = water_need(water_requirement)
    dryness = _dryness(
        power if power.get("available") else {},
        openet if openet.get("available") else {},
        usgs if usgs.get("available") else None,
    )
    if need and dryness:
        possible += 8
        table = {
            ("high", "dry"): 1,
            ("high", "moderate"): 6,
            ("high", "wet"): 8,
            ("moderate", "dry"): 4,
            ("moderate", "moderate"): 8,
            ("moderate", "wet"): 6,
            ("low", "dry"): 8,
            ("low", "moderate"): 6,
            ("low", "wet"): 3,
        }
        earned += table[(need, dryness)]
        if need == "high" and dryness == "dry":
            issues.append(
                "Location climate looks dry for a crop that wants consistent moisture. "
                "Check irrigation before relying on rainfall."
            )
            improvements.append(
                "Seasonal rainfall is light for this crop. Confirm root-zone moisture and irrigate from a soil check rather than a fixed calendar."
            )
        elif need == "low" and dryness == "wet":
            issues.append(
                "This place looks wetter than a drought-tolerant crop prefers. Watch drainage during the selected season."
            )
        elif need == "high" and dryness == "wet":
            evidence.append("Seasonal moisture from NASA POWER looks compatible with this crop's higher water need.")
        elif need == "low" and dryness == "dry":
            evidence.append("The drier seasonal water balance fits a lower water-need or drought-tolerant crop.")
        else:
            evidence.append("Seasonal rainfall and evapotranspiration are in a middle range for this crop's water note.")

    # Light USGS-only water fit when POWER/OpenET did not already score moisture.
    usgs_signal = _usgs_moisture_signal(usgs if usgs.get("available") else None)
    if need and usgs_signal and not (power.get("available") or openet.get("available")):
        possible += 4
        table = {
            ("high", "dry"): 1,
            ("high", "moderate"): 3,
            ("high", "wet"): 4,
            ("moderate", "dry"): 2,
            ("moderate", "moderate"): 4,
            ("moderate", "wet"): 3,
            ("low", "dry"): 4,
            ("low", "moderate"): 3,
            ("low", "wet"): 1,
        }
        earned += table[(need, usgs_signal)]
        evidence.append(
            "Nearest USGS water monitoring was used as a supporting moisture cue for this crop."
        )
    elif need and usgs_signal and (power.get("available") or openet.get("available")):
        evidence.append(
            "Nearest USGS streamflow or groundwater reading supported the seasonal moisture assessment."
        )

    preference = temperature_preference(growing_season)
    temperature = power.get("temperature_c") if power.get("available") else None
    if temperature is not None and preference != "flexible":
        possible += 7
        if preference == "warm":
            if temperature >= 18:
                earned += 7
                evidence.append(
                    f"The {power.get('season', 'selected').lower()} average of {power.get('temperature_f')}°F supports a warm-season crop."
                )
            elif temperature >= 14:
                earned += 3
                issues.append("Average temperature is cool for a warm-season crop. Confirm the frost-free window before transplanting.")
            else:
                earned += 1
                issues.append("Average temperature is well below a typical warm-season growing range for this planting season.")
        elif preference == "cool":
            if temperature <= 20:
                earned += 7
                evidence.append(
                    f"The {power.get('season', 'selected').lower()} average of {power.get('temperature_f')}°F fits a cool-season crop."
                )
            elif temperature <= 24:
                earned += 3
                issues.append("Average temperature is warm for a cool-season crop and may shorten the useful planting window.")
            else:
                earned += 1
                issues.append("Average temperature is hot for a cool-season crop in the selected season.")
    return {
        "earned": earned,
        "possible": possible,
        "issues": issues,
        "evidence": evidence,
        "improvements": improvements,
    }
