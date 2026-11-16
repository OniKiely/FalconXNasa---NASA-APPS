
import re

from .catalog import variety, varieties, calendar, companions, nutrition
from .climate import describe_climate, score_climate
from .soil import soil_profile
from .improvement import plan


# Planting seasons and their corresponding months
MONTHS = {
    "spring": {3, 4, 5},
    "summer": {6, 7, 8},
    "fall": {9, 10, 11},
    "winter": {12, 1, 2}
}

MONTH_MAP = {
    month: index
    for index, month in enumerate(
        [
            "January", "February", "March", "April",
            "May", "June", "July", "August",
            "September", "October", "November", "December"
        ],
        start=1
    )
}


def ph_range(text):
    """Extract a crop's preferred soil pH range."""
    numbers = re.findall(r"\d+(?:\.\d+)?", text or "")

    if len(numbers) < 2:
        return None

    low, high = map(float, numbers[:2])

    if not 0 <= low <= high <= 14:
        return None

    return low, high


def months_between(start, end):
    """Return the months between two month names."""
    first = MONTH_MAP.get(start)
    last = MONTH_MAP.get(end)

    if not first or not last:
        return set()

    months = {first}

    while first != last:
        first = first % 12 + 1
        months.add(first)

    return months


def calculate_score(texture_match, soil_ph, ph_range, season_match, climate_part=None):
    """
    Calculate a preliminary rule-based compatibility index.

    Texture: 35 points
    Soil pH: 30 points
    Planting season: 20 points
    Location climate: up to 15 points when NASA POWER or OpenET data exists

    Missing pH, season, and climate data are excluded.
    Moisture is not scored without crop-specific requirements.
    """
    earned = 0.0
    possible = 35.0

    if texture_match:
        earned += 35

    if soil_ph is not None and ph_range is not None:
        possible += 30
        low, high = ph_range

        if low <= soil_ph <= high:
            earned += 30

    if season_match is not None:
        possible += 20

        if season_match:
            earned += 20

    if climate_part and climate_part.get("possible"):
        possible += climate_part["possible"]
        earned += climate_part["earned"]

    return round((earned / possible) * 100)


def assess(
    slug,
    soil,
    season,
    zone=None,
    soil_ph=None,
    moisture=None,
    nitrogen=None,
    location="",
    climate=None,
):
    """Evaluate preliminary crop suitability."""

    # Find the selected crop variety
    selected_variety = variety(slug)

    if not selected_variety:
        raise ValueError("Unknown variety")

    season_key = season.lower()

    if season_key not in MONTHS:
        raise ValueError("Invalid season")

    # Get the farmer's soil information
    profile = soil_profile(
        soil, soil_ph, moisture, nitrogen
    )

    issues = []
    evidence = []
    unknown = []

    season_match = None

    # 1. Check soil texture
    desired = selected_variety.get("soil_type", "").lower()

    texture_match = (
        soil in desired
        or (soil == "loam" and "well-drained" in desired)
    )

    if texture_match:
        evidence.append(
            "The selected texture appears consistent with "
            "the variety's soil description."
        )
    else:
        issues.append(
            "The selected soil texture is not explicitly "
            "described as preferred by this variety. "
            "Check drainage and soil structure."
        )

    # 2. Check soil pH
    preferred_ph = ph_range(
        selected_variety.get("soil_ph", "")
    )

    if soil_ph is not None and preferred_ph:
        low, high = preferred_ph

        if low <= soil_ph <= high:
            evidence.append(
                "The entered pH falls within the listed "
                "variety range."
            )
        else:
            issues.append(
                f"Measured pH {soil_ph:g} is outside the "
                f"listed range {low:g}-{high:g}."
            )
    else:
        unknown.append(
            "Field soil pH was not evaluated."
        )

    # 3. Check planting season
    planting_records = calendar(slug, zone)

    if zone is None:
        unknown.append(
            "No USDA hardiness zone was entered; "
            "the planting calendar cannot be localized."
        )

    elif not planting_records:
        unknown.append(
            "No calendar record exists for this variety "
            "and USDA zone."
        )

    else:
        planting_months = set()

        for record in planting_records:
            for prefix in ("direct_sow", "outdoor_transplant"):
                start = record.get(f"{prefix}_start")
                end = record.get(f"{prefix}_end")

                planting_months.update(
                    months_between(start, end)
                )

        if planting_months:
            season_match = bool(
                planting_months & MONTHS[season_key]
            )

            if season_match:
                evidence.append(
                    "The selected season overlaps a recorded "
                    "outdoor planting window for this USDA zone."
                )
            else:
                issues.append(
                    "The selected season does not overlap the "
                    "recorded outdoor planting window."
                )
        else:
            unknown.append(
                "No outdoor planting window is recorded "
                "for this variety and zone."
            )

    # 4. Check missing measurements
    if moisture is None:
        unknown.append(
            "Current soil moisture was not measured."
        )

    if nitrogen is None:
        unknown.append(
            "Soil nitrogen status was not measured."
        )

    # 5. Compare the variety with location climate when coordinates resolved
    climate_part = score_climate(
        selected_variety.get("water_requirement"),
        selected_variety.get("growing_season"),
        climate,
    )
    issues.extend(climate_part["issues"])
    evidence.extend(climate_part["evidence"])
    improvements = plan(
        soil,
        selected_variety["category"],
        soil_ph,
        preferred_ph,
        moisture,
        nitrogen,
    )
    improvements.extend(climate_part["improvements"])

    # 6. Calculate compatibility percentage
    compatibility_score = calculate_score(
        texture_match=texture_match,
        soil_ph=soil_ph,
        ph_range=preferred_ph,
        season_match=season_match,
        climate_part=climate_part,
    )

    # 7. Determine preliminary status
    if issues:
        status = "Needs improvement / review"
    else:
        status = "Potentially suitable (preliminary)"

    coordinates = ""
    if climate and climate.get("latitude") is not None:
        coordinates = f"{climate['latitude']:.5f}, {climate['longitude']:.5f}"

    # 8. Return results to the frontend
    return {
        "crop": selected_variety["category"],
        "variety": selected_variety["name"],
        "slug": slug,
        "location": location,
        "coordinates": coordinates,
        "season": season,
        "soil": profile,
        "status": status,

        "compatibility_score": compatibility_score,
        "score_method": "Preliminary rule-based index using soil, season, and location climate when coordinates resolve",

        "issues": issues,
        "positive_indicators": evidence,
        "unknowns": unknown,

        "improvements": improvements,
        "field_context": describe_climate(climate, season) if climate else [],

        "variety_requirements": {
            "soil_type": selected_variety.get("soil_type"),
            "soil_ph": selected_variety.get("soil_ph"),
            "water_requirement": selected_variety.get(
                "water_requirement"
            ),
            "growing_season": selected_variety.get(
                "growing_season"
            )
        },

        "planting_calendar": planting_records[:2],
        "companion_plants": companions(slug)[:5],
        "nutrition": nutrition(slug),

        "sources": {
            "variety": "varieties.csv",
            "calendar": "planting_calendar.csv",
            "companions": "companion_plants.csv",
            "nutrition": "nutrition.csv",
            "climate": "NASA POWER agroclimatology",
            "water": "USGS Water Data API",
            "evapotranspiration": "OpenET",
        },

        "disclaimer": (
            "This percentage is a preliminary rule-based "
            "compatibility index, not a measured probability "
            "of crop success. Climate figures are grid or nearby-station "
            "values, not a reading from the field. A soil test is recommended."
        )
    }


def recommend(soil, season, zone=None, limit=5, climate=None):
    """Recommend varieties based on preliminary matching rules."""
    results = []

    for crop_variety in varieties():
        assessment = assess(
            crop_variety["slug"],
            soil,
            season,
            zone,
            climate=climate,
        )

        results.append({
            "slug": crop_variety["slug"],
            "variety": crop_variety["name"],
            "crop": crop_variety["category"],
            "status": assessment["status"],
            "compatibility_score": assessment["compatibility_score"],
            "issues": assessment["issues"]
        })

    results.sort(
        key=lambda item: (
            -item["compatibility_score"],
            len(item["issues"]),
            item["crop"],
            item["variety"]
        )
    )

    return results[:limit]
