# How external APIs are used in falconXNasa

This app turns a farm address into coordinates, then pulls climate and water
context from three public data services. Those values help score crop
compatibility and show plain-language field context in the planner results.

## End-to-end flow

1. The farmer enters **city + state**, or a **ZIP code** (country optional).
2. `services/location.py` geocodes that place with **OpenStreetMap Nominatim**
   and returns latitude / longitude (a place centroid, not a surveyed field).
3. `services/climate.py` calls the three climate/water APIs **in parallel**.
4. `services/compatibility.py` uses that climate object when scoring a crop
   (check mode) or ranking recommendations (recommend mode).
5. The UI shows resolved place, coordinates, and the climate/water lines.

```text
City / State / ZIP
        │
        ▼
  Nominatim geocode  →  latitude, longitude
        │
        ├──────────────┬────────────────┐
        ▼              ▼                ▼
  NASA POWER      USGS Water         OpenET
  (climatology)   (nearby gages)     (ET, western U.S.)
        │              │                │
        └──────────────┴────────────────┘
                       │
                       ▼
           crop score + result panel
```

Main code paths:

| Step | File | Function |
|------|------|----------|
| Geocode | `services/location.py` | `geocode_place`, `geocode` |
| Fetch climate | `services/climate.py` | `fetch_climate` |
| Score crop | `services/compatibility.py` | `assess`, `recommend`, via `score_climate` |
| HTTP entry | `app.py` | `resolve_farm`, `/api/planner` |

---

## 1. OpenStreetMap Nominatim (geocoding)

**Purpose:** Convert city / state / ZIP into latitude and longitude so the other
APIs can be queried for that point.

| | |
|---|---|
| Docs / service | https://nominatim.openstreetmap.org |
| Used in | `services/location.py` |
| API key | None (send a descriptive `User-Agent`) |

**What we send:** a joined query such as `Boise, ID, 83702, US`.

**What we keep:** display name, lat, lon, city, state, postal code, country code.

**Limits:** This is a town or ZIP **centroid**, not a farm boundary. Soil texture
and pH are still entered by the farmer; they are not looked up from a soil map.

---

## 2. NASA POWER

**Docs:** https://power.larc.nasa.gov/api/pages/

**Purpose:** Long-term agroclimatology for the farm point — temperature,
rainfall, humidity, sunlight, and root-zone wetness for the selected planting
season.

| | |
|---|---|
| Endpoint used | `https://power.larc.nasa.gov/api/temporal/climatology/point` |
| Used in | `services/climate.py` → `fetch_power` |
| API key | **None** |
| Community | `AG` (agriculture) |

**Parameters requested:**

| POWER code | Meaning in the app |
|---|---|
| `T2M` | Average 2 m air temperature |
| `T2M_MAX` / `T2M_MIN` | Typical daily max / min |
| `PRECTOTCORR` | Corrected precipitation |
| `RH2M` | Relative humidity |
| `ALLSKY_SFC_SW_DWN` | Solar radiation |
| `GWETROOT` | Root-zone soil wetness (0–1) |

**How seasons map:** Spring = Mar–May, Summer = Jun–Aug, Fall = Sep–Nov,
Winter = Dec–Feb. Monthly climatology values are averaged for those months.

**How it improves recommendations:**

- Temperature is compared to whether the crop is warm-season or cool-season.
- Rainfall, root-zone wetness, and (with OpenET) water balance help decide if
  the location looks dry, moderate, or wet for the crop’s water need.
- Summary lines appear under **Location, climate, and water** in the results.

---

## 3. USGS Water Data API

**Docs / base:** https://api.waterdata.usgs.gov  
**OGC API docs:** https://api.waterdata.usgs.gov/docs/ogcapi/

**Purpose:** Find nearby United States monitoring sites and report recent
streamflow and groundwater depth as local water context.

| | |
|---|---|
| Endpoint pattern | `https://api.waterdata.usgs.gov/ogcapi/v1/collections/{collection}/items` |
| Used in | `services/climate.py` → `fetch_usgs` |
| API key | **Optional** — set `USGS_API_KEY` in `.env` for a higher rate limit |

**Collections / parameters used:**

| Collection | Parameter | Meaning |
|---|---|---|
| `latest-continuous`, then `latest-daily` | `00060` | Streamflow |
| `latest-continuous`, then `latest-daily` | `72019` | Groundwater depth |
| `monitoring-locations` | site id | Human-readable site name |

**Search behavior:** Build a bounding box around the farm (~25 km, then ~60 km).
Prefer recent readings (within about 45 days), then nearer sites.

**How it improves recommendations:**

- Shown in the result panel (gage name, distance, value, date).
- Recent nearby readings can lightly nudge the dry / wet moisture signal used
  in `score_climate` (supporting cue only; missing USGS data is not a penalty).
- Stale records are still shown with a note that they may be inactive, and they
  are **not** used for scoring.

**Coverage:** United States monitoring footprint. Points outside that area skip
the USGS query with an explanatory note.

---

## 4. OpenET (etdata.org)

**Product site:** https://etdata.org  
**API used by the app:** `https://openet-api.org/raster/timeseries/point`  
(Create a key at https://etdata.org/api/)

**Purpose:** Satellite-based **evapotranspiration (ET)** — how much water the
landscape is using — for western U.S. fields. Combined with NASA POWER rainfall
to estimate a simple seasonal water balance (rain minus ET).

| | |
|---|---|
| Used in | `services/climate.py` → `fetch_openet` |
| API key | **Required** — `OPENET_API_KEY` in `.env` next to `app.py` |
| Model | Ensemble |
| Variable | `ET` (mm), monthly, prior calendar year |
| Reference ET | gridMET |

**Coverage:** Approximate western United States. Points outside that footprint
are skipped with a note (NASA POWER and USGS can still run).

**How it improves recommendations:**

- Annual and seasonal ET totals are shown in the result panel.
- Seasonal rain − ET becomes a water-balance cue (irrigation likely if strongly
  negative).
- That balance feeds the same dry / moderate / wet scoring used with POWER.

**Setup:**

```bash
cp .env.example .env
# edit .env:
OPENET_API_KEY=your_key_here
# optional:
USGS_API_KEY=your_usgs_key_here
```

Do **not** put keys in `.venv`. Restart `python app.py` after changing `.env`.

---

## How the three APIs affect the crop score

Scoring lives in `score_climate` inside `services/climate.py` and is folded into
the overall compatibility percentage in `services/compatibility.py`.

| Signal | Source | Effect |
|---|---|---|
| Seasonal temperature | NASA POWER | Points for warm- vs cool-season crop fit |
| Rain / wetness / ET deficit | POWER + OpenET | Dry / moderate / wet vs crop water need |
| Nearby gage moisture cue | USGS (recent only) | Small supporting nudge; optional alone if POWER/OpenET missing |

Missing data from any one API does **not** fail the planner. Failed or
unavailable sources are skipped; the others still run.

---

## What these APIs do *not* do

- They do not replace a field soil test (pH, texture, nitrogen stay farmer-entered).
- They do not return a predicted yield.
- Coordinates are a place centroid, not a parcel survey.
- POWER is long-term climatology, not yesterday’s weather station reading.
- USGS values are the nearest monitor, which can be kilometers away.
- OpenET is a satellite grid for its western coverage only.

Results remain preliminary educational guidance for crop compatibility planning.
