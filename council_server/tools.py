# branchscape/council_server/tools.py
import math

def schemas():
    """Anthropic tool schemas exposed to every agent."""
    return [
        {
            "name": "query_data",
            "description": "Query the Maricopa County banking dataset (FDIC deposits, "
                           "CRA small-business lending, IRS income by ZIP, census tracts).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": [
                        "total_deposits", "branch_count", "underserved_tracts",
                        "high_income_tracts", "tract_detail"]},
                    "geoid": {"type": "string", "description": "tract id, for tract_detail"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["metric"],
            },
        },
        {
            "name": "cast_vote",
            "description": "Record your vote for where to open the branch.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "zone": {"type": "string", "description": "census tract geoid"},
                    "stance": {"type": "string", "enum": ["support", "conditional", "oppose"]},
                    "rationale": {"type": "string"},
                },
                "required": ["zone", "stance", "rationale"],
            },
        },
    ]

def _haversine_km(a_lat, a_lon, b_lat, b_lon):
    R = 6371.0
    dlat = math.radians(b_lat - a_lat); dlon = math.radians(b_lon - a_lon)
    s = (math.sin(dlat/2)**2 + math.cos(math.radians(a_lat))*math.cos(math.radians(b_lat))*math.sin(dlon/2)**2)
    return 2*R*math.asin(min(1, math.sqrt(s)))

def _nearest_income(ds, lon, lat):
    best, val = 1e9, 0
    for p in ds.income:
        d = _haversine_km(lat, lon, p["lat"], p["lon"])
        if d < best: best, val = d, p["income"]
    return val

def _tract_rows(ds):
    """Build a per-tract summary used by the ranking metrics (skips 98xx special tracts)."""
    rows = []
    for geoid, (lon, lat) in ds.tracts.items():
        if int(str(geoid)[-6:]) >= 980000:
            continue
        cra = ds.cra["tracts"].get(geoid, {})
        rows.append({
            "geoid": geoid, "lon": lon, "lat": lat,
            "income": _nearest_income(ds, lon, lat),
            "cra_amt": cra.get("amt", 0),
        })
    return rows

def dispatch(ds, name, args):
    if name == "query_data":
        return _query_data(ds, args)
    if name == "cast_vote":
        return {"zone": args["zone"], "stance": args["stance"], "rationale": args.get("rationale", "")}
    raise KeyError(name)

def _query_data(ds, args):
    metric = args["metric"]; limit = int(args.get("limit", 5))
    if metric == "total_deposits":
        total = sum((b["dep"].get("2024", 0) for b in ds.branches))
        return {"metric": metric, "value": total, "units": "USD thousands"}
    if metric == "branch_count":
        return {"metric": metric, "value": len(ds.branches)}
    if metric == "underserved_tracts":
        rows = sorted(_tract_rows(ds), key=lambda r: (r["cra_amt"], r["income"]))[:limit]
        return {"metric": metric, "rows": rows}
    if metric == "high_income_tracts":
        rows = sorted(_tract_rows(ds), key=lambda r: -r["income"])[:limit]
        return {"metric": metric, "rows": rows}
    if metric == "tract_detail":
        g = args.get("geoid"); lonlat = ds.tracts.get(g)
        if not lonlat: return {"metric": metric, "error": "unknown geoid"}
        lon, lat = lonlat; cra = ds.cra["tracts"].get(g, {})
        return {"metric": metric, "geoid": g, "income": _nearest_income(ds, lon, lat),
                "cra_amt": cra.get("amt", 0)}
    return {"metric": metric, "error": "unknown metric"}
