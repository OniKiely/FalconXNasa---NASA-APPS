"""Flask routes for the falconXNasa crop planner."""
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from services.catalog import categories, varieties
from services.compatibility import assess, recommend
from services.location import geocode

ROOT = Path(__file__).resolve().parent
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


@app.get("/api/location")
def location():
    place = request.args.get("q", "").strip()
    if not place:
        return jsonify(error="Provide q"), 400
    resolved = geocode(place)
    if resolved is None:
        return jsonify(error="Location could not be resolved."), 404
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

        if mode == "recommend":
            return jsonify(
                mode=mode,
                recommendations=recommend(soil, season, zone),
                disclaimer="Ranked by simple dataset matches, not predicted crop yield.",
            )
        if mode != "check":
            raise ValueError("Invalid mode")

        result = assess(
            str(data.get("variety") or ""), soil, season, zone, ph,
            moisture, nitrogen, str(data.get("location") or "")[:180],
        )
        return jsonify(mode=mode, result=result)
    except (ValueError, TypeError) as exc:
        return jsonify(error=str(exc)), 400


if __name__ == "__main__":
    app.run(debug=True, port=5003, use_reloader=False)
