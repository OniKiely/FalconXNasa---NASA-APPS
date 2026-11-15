SOILS = {"loam":"Balanced texture; confirm drainage and soil test results.","clay":"Can retain water and compact; check infiltration and root-zone aeration.","sandy":"Drains rapidly; check water-holding capacity and nutrient leaching.","silt":"Often fertile but susceptible to compaction and erosion.","peat":"Organic-rich soil; pH and drainage can vary greatly."}
def soil_profile(soil, ph=None, moisture=None, nitrogen=None):
    if soil not in SOILS: raise ValueError("Choose a valid soil type")
    return {"texture":soil,"description":SOILS[soil],"ph":ph,"moisture":moisture,"nitrogen":nitrogen,"source":"Farmer-entered soil texture and optional field measurements; not USDA measurements"}
