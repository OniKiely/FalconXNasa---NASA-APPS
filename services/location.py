import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

def geocode(place):
    """Optional OpenStreetMap geocoding; never infer soil type from place name."""
    if not place or len(place) > 180: return None
    url="https://nominatim.openstreetmap.org/search?"+urlencode({"q":place,"format":"json","limit":1})
    try:
        with urlopen(Request(url,headers={"User-Agent":"falconXNasa-educational-demo/1.0 (contact: local-development)"}),timeout=5) as response:
            data=json.load(response)
        if data: return {"display_name":data[0]["display_name"],"latitude":float(data[0]["lat"]),"longitude":float(data[0]["lon"]),"source":"OpenStreetMap Nominatim; approximate place centroid, not a farm boundary"}
    except Exception: pass
    return None
