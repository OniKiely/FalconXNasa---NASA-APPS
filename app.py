"""Flask routes for the falconXNasa crop planner."""
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from services.catalog import categories, varieties
from services.climate import empty_climate, fetch_climate
from services.compatibility import assess, recommend
from services.env import load_env
from services.location import geocode, geocode_place, place_query

ROOT = Path(__file__).resolve().parent
load_env(ROOT / ".env")
app = Flask(__name__, static_folder=str(ROOT / "static"), static_url_path="")
VALID_SOILS = {"loam", "clay", "sandy", "silt", "peat"}
VALID_SEASONS = {"spring", "summer", "fall", "winter"}


def optional_number(value, name, converter, minimum, maximum):
    if value in (None, ""):
        return None
    try:
        number = converter(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not minimum <= number <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return number


@app.get("/")
def home():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/index.html")
def index():
    return home()


@app.get("/about-us.html")
def about():
    return send_from_directory(app.static_folder, "about-us.html")


@app.get("/api/health")
def health():
    return jsonify(status="ok", backend="Flask")


@app.get("/api/catalog")
def catalog():
    return jsonify(
        categories=[{"slug": row["slug"], "name": row["name"]} for row in categories()],
        varieties=[
            {"slug": row["slug"], "name": row["name"], "category": row["category"]}
            for row in varieties()
        ],
    )


def clean_text(value, limit=80):
    return " ".join(str(value or "").split())[:limit]


def resolve_farm(data):
    """Geocode structured farm fields, then load climate and water context once."""
    city = clean_text(data.get("city"))
    state = clean_text(data.get("state"))
    postal_code = clean_text(data.get("postal_code") or data.get("zip"))
    country = clean_text(data.get("country"))
    query = place_query(city, state, postal_code, country)
    if not query:
        query = clean_text(data.get("location"), 180)
    if not query:
        return None, empty_climate(), ""
    resolved = geocode_place(city, state, postal_code, country) if any(
        (city, state, postal_code, country)
    ) else geocode(query)
    if resolved is None:
        return None, empty_climate(), query
    climate = fetch_climate(
        resolved["latitude"],
        resolved["longitude"],
        data.get("season") or "Summer",
        resolved.get("country_code") or "",
    )
    return resolved, climate, resolved.get("display_name") or query


@app.get("/api/location")
def location():
    city = clean_text(request.args.get("city"))
    state = clean_text(request.args.get("state"))
    postal_code = clean_text(request.args.get("postal_code") or request.args.get("zip"))
    country = clean_text(request.args.get("country"))
    if any((city, state, postal_code, country)):
        resolved = geocode_place(city, state, postal_code, country)
    else:
        resolved = geocode(clean_text(request.args.get("q"), 180))
    if resolved is None:
        return jsonify(error="Location could not be resolved. Include a city, state, and ZIP code."), 404
    return jsonify(resolved)


@app.post("/api/planner")
def planner():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Expected a JSON object"), 400

    try:
        mode = data.get("mode", "check")
        soil = str(data.get("soil") or "").strip().lower()
        season = str(data.get("season") or "Spring").strip()
        zone = optional_number(data.get("zone"), "USDA zone", int, 1, 13)
        ph = optional_number(data.get("soil_ph"), "Soil pH", float, 0, 14)
        moisture = data.get("moisture") or None
        nitrogen = data.get("nitrogen") or None

        if soil not in VALID_SOILS:
            raise ValueError("Invalid soil type")
        if season.lower() not in VALID_SEASONS:
            raise ValueError("Invalid planting season")
        if moisture not in (None, "dry", "normal", "wet"):
            raise ValueError("Invalid moisture value")
        if nitrogen not in (None, "low", "normal", "high"):
            raise ValueError("Invalid nitrogen value")

        city = clean_text(data.get("city"))
        state = clean_text(data.get("state"))
        postal_code = clean_text(data.get("postal_code") or data.get("zip"))
        if not ((city and state) or postal_code):
            raise ValueError(
                "Farm location is required: enter a city and state, or a ZIP code."
            )

        resolved, climate, place = resolve_farm(data)
        context = {
            "location": resolved,
            "query": place,
            "lines": list(climate.get("lines") or []),
        }
        if place and resolved is None:
            context["lines"] = [
                "That city, state, and ZIP could not be turned into coordinates, so climate and water data were skipped."
            ]

        if mode == "recommend":
            return jsonify(
                mode=mode,
                context=context,
                recommendations=recommend(soil, season, zone, climate=climate if resolved else None),
                disclaimer=(
                    "Ranked by soil, season, and location climate when coordinates resolve. "
                    "This is not a predicted crop yield."
                ),
            )
        if mode != "check":
            raise ValueError("Invalid mode")

        result = assess(
            str(data.get("variety") or ""), soil, season, zone, ph,
            moisture, nitrogen, place, climate if resolved else None,
        )
        return jsonify(mode=mode, context=context, result=result)
    except (ValueError, TypeError) as exc:
        return jsonify(error=str(exc)), 400


if __name__ == "__main__":
    app.run(debug=True, port=5003, use_reloader=False)
