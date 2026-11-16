"""Turn a farm address into a latitude and longitude."""
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USER_AGENT = "falconXNasa-educational-demo/1.0 (contact: local-development)"


def place_query(city="", state="", postal_code="", country=""):
    """Join the address parts the farmer actually entered."""
    parts = []
    for value in (city, state, postal_code, country):
        text = " ".join(str(value or "").split())
        if text:
            parts.append(text[:80])
    return ", ".join(parts)[:180]


def geocode(place):
    """Resolve a place string with OpenStreetMap Nominatim."""
    query = " ".join(str(place or "").split())
    if not query or len(query) > 180:
        return None
    url = "https://nominatim.openstreetmap.org/search?" + urlencode({
        "q": query,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    })
    try:
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        with urlopen(request, timeout=8) as response:
            data = json.load(response)
    except Exception:
        return None
    if not data:
        return None
    hit = data[0]
    address = hit.get("address") or {}
    try:
        latitude = float(hit["lat"])
        longitude = float(hit["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    return {
        "display_name": hit.get("display_name") or query,
        "latitude": round(latitude, 5),
        "longitude": round(longitude, 5),
        "city": address.get("city") or address.get("town") or address.get("village") or "",
        "state": address.get("state") or "",
        "postal_code": address.get("postcode") or "",
        "country_code": (address.get("country_code") or "").lower(),
        "source": "OpenStreetMap Nominatim; approximate place centroid, not a farm boundary",
    }


def geocode_place(city="", state="", postal_code="", country=""):
    return geocode(place_query(city, state, postal_code, country))
