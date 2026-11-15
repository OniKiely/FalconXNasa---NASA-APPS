def plan(soil, crop, soil_ph=None, ph_range=None, moisture=None, nitrogen=None):
    items=[]
    if soil == "clay":
        items += ["Avoid tilling wet clay; add mature compost over time and limit compaction.","If drainage is poor, consider raised beds or appropriate drainage improvements."]
    elif soil == "sandy":
        items += ["Use compost and surface mulch to improve water retention; irrigate in smaller, monitored applications.","Use soil tests to guide split nutrient applications and reduce leaching."]
    elif soil == "peat":
        items += ["Test pH and drainage before applying lime or fertilizer; peat soils vary substantially."]
    elif soil == "silt":
        items += ["Maintain ground cover and reduce compaction and erosion."]
    else:
        items += ["Maintain organic matter with compost and crop residues; verify drainage and nutrient levels."]
    if moisture == "dry": items.append("Check root-zone moisture regularly and consider mulch or drip irrigation.")
    if moisture == "wet": items.append("Investigate waterlogging and drainage before adding irrigation.")
    if nitrogen == "low": items.append("Confirm nitrogen deficiency with a soil test; select fertilizer or a legume rotation based on local recommendations.")
    if soil_ph is not None and ph_range:
        low, high = ph_range
        if soil_ph < low: items.append("Soil pH is below this variety's stated range. Obtain a buffer-pH soil test before considering lime.")
        if soil_ph > high: items.append("Soil pH is above this variety's stated range. Seek local extension advice before attempting pH correction.")
    items.append("Possible preceding cover crops: clover or vetch for nitrogen cycling, or cereal rye for soil cover. Choose species, planting and termination dates for your region; legume nitrogen benefits are not guaranteed.")
    return items
