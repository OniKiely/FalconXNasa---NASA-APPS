import csv
from functools import lru_cache
from pathlib import Path
DATA = Path(__file__).resolve().parents[1] / "data"
@lru_cache(maxsize=12)
def rows(filename):
    with (DATA / filename).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def categories():
    return rows("categories.csv")

def varieties(category=None):
    all_rows = rows("varieties.csv")
    return [r for r in all_rows if r["category"].lower() == category.lower()] if category else all_rows

def variety(slug):
    return next((r for r in varieties() if r["slug"] == slug), None)

def calendar(slug, zone=None):
    matches = [r for r in rows("planting_calendar.csv") if r["variety_slug"] == slug]
    if zone is not None:
        matches = [r for r in matches if r["usda_zone"] == str(zone)]
    return matches[:12]

def companions(slug):
    return [dict(name=r["companion_name"], relationship=r["relationship"], reason=r["reason"]) for r in rows("companion_plants.csv") if r["variety_slug"] == slug][:12]

def nutrition(slug):
    r = next((r for r in rows("nutrition.csv") if r["variety_slug"] == slug), None)
    if not r: return None
    return {k:r.get(k) for k in ["calories","protein_g","fiber_g","vitamin_c_mg","iron_mg","potassium_mg","data_source"]}
