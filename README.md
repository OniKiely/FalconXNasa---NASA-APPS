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

## Files

- `app.py`: Flask routes and request validation.
- `services/`: CSV access, suitability rules, improvement advice, and optional location geocoding.
- `data/`: six supplied CSV datasets.
- `static/`: HTML, CSS, JS, and five images.

## Important limits

- USDA soil survey data is **not** automatically fetched. Soil properties are farmer-entered.
- Location is displayed in the result but does **not** influence suitability.
- Results are qualitative demonstration guidance, not measured yield predictions.
- Companion plants are not the same as preceding cover crops.
- Keep the `data/` folder alongside `app.py`.

## Tests

Run `python -m unittest discover -s tests -v` after installing Flask.
