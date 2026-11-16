# falconXNasa Project

This version reorganizes the uploaded Flask routes and JavaScript while keeping the existing API response structure. It adds a searchable crop picker and retains the original frontend styling and images.

## Start on macOS

```bash
cd /path/to/falconxnasa_cleaned
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5002 . Change the port in `app.py` if needed.
We also hosting the server using vercel : https://falcon-x-nasa-nasa-apps.vercel.app

## Files

- `app.py`: Flask routes and request validation.
- `services/`: CSV access, suitability rules, improvement advice, and optional location geocoding.
- `data/`: six supplied CSV datasets.
- `static/`: HTML, CSS, JS, and five images.

## Location climate

The planner requires a city and state, or a ZIP code. That place is geocoded to latitude and longitude, then used when scoring a crop.

- NASA POWER (no key): seasonal temperature, rainfall, humidity, sunlight, and root-zone wetness — https://power.larc.nasa.gov/api/pages/
- USGS Water Data API: nearest streamflow and groundwater depth, also used as a light moisture cue in scoring — https://api.waterdata.usgs.gov
- OpenET (etdata.org): monthly evapotranspiration for western U.S. points — https://etdata.org

**Full write-up of how each API is called and scored:** see [API_USAGE.md](API_USAGE.md).

### API keys (`.env`, not `.venv`)

Copy `.env.example` to a file named `.env` **next to `app.py`**. Do **not** put keys inside `.venv` (that is only the Python virtualenv).

```bash
cp .env.example .env
# then edit .env and paste:
# OPENET_API_KEY=...   # required for OpenET
# USGS_API_KEY=...     # optional; higher USGS rate limit
```

`.env` is gitignored and loaded when the app starts.

## Important limits

- USDA soil survey data is **not** automatically fetched. Soil properties are farmer-entered.
- Coordinates are a town or ZIP centroid from OpenStreetMap, not a surveyed farm boundary.
- NASA POWER values are long-term grid climatology. USGS values are the nearest monitoring site. OpenET is a satellite grid, and only for its western U.S. coverage.
- Results are qualitative demonstration guidance, not measured yield predictions.
- Companion plants are not the same as preceding cover crops.
- Keep the `data/` folder alongside `app.py`.

## Tests

Run `python -m unittest discover -s tests -v` after installing Flask.
