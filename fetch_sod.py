#!/usr/bin/env python3
"""
Pull FDIC Summary of Deposits (SOD) branch-level data for Maricopa County, AZ
across multiple years. SOD is the only public dataset with per-branch lat/long
and per-branch deposits. Free, no API key.

API: https://banks.data.fdic.gov/api/sod
Rate limit: ~2 req/sec with a cooldown window -> we pace + back off on 429.
"""
import json
import time
import urllib.parse
import urllib.request
import sys

API = "https://banks.data.fdic.gov/api/sod"

# Years to pull (for the cold-open slice we only need the latest; the rest
# set up the 30-year time-lapse for free).
YEARS = [1994, 2000, 2005, 2010, 2015, 2020, 2024]

FIELDS = ",".join([
    "YEAR", "NAMEBR", "NAMEFULL", "ADDRESBR", "CITYBR", "CNTYNAMB", "ZIPBR",
    "DEPSUMBR", "SIMS_LATITUDE", "SIMS_LONGITUDE", "NAMEHCR", "STNAMEBR", "STALPBR",
    "CERT",
])

# Generous Maricopa County / Phoenix-metro bounding box (fallback filter)
LAT_MIN, LAT_MAX = 32.45, 34.10
LON_MIN, LON_MAX = -113.40, -111.00

LIMIT = 1000
PACE = 1.6          # seconds between calls
MAX_RETRIES = 6


def fetch(params):
    qs = urllib.parse.urlencode(params)
    url = f"{API}?{qs}"
    delay = PACE
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "branchscape/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read().decode("utf-8")
            if body.strip().startswith("{"):
                return json.loads(body)
            # rate-limit text body
            raise ValueError(body[:120])
        except Exception as e:
            wait = delay * (attempt + 1)
            print(f"   retry {attempt+1}/{MAX_RETRIES} after {wait:.1f}s ({str(e)[:80]})",
                  file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"failed after {MAX_RETRIES} retries: {url}")


def in_maricopa(rec):
    cnty = (rec.get("CNTYNAMB") or "").strip().lower()
    if cnty == "maricopa":
        return True
    lat = rec.get("SIMS_LATITUDE")
    lon = rec.get("SIMS_LONGITUDE")
    if lat is None or lon is None:
        return False
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX


def pull_year(year):
    out = []
    offset = 0
    while True:
        params = {
            "filters": f"STALPBR:AZ AND YEAR:{year}",
            "fields": FIELDS,
            "limit": LIMIT,
            "offset": offset,
            "format": "json",
        }
        time.sleep(PACE)
        payload = fetch(params)
        rows = payload.get("data", [])
        if not rows:
            break
        for row in rows:
            rec = row.get("data", row)
            if not in_maricopa(rec):
                continue
            lat = rec.get("SIMS_LATITUDE")
            lon = rec.get("SIMS_LONGITUDE")
            dep = rec.get("DEPSUMBR")
            if lat in (None, "") or lon in (None, ""):
                continue
            try:
                out.append({
                    "year": int(rec.get("YEAR", year)),
                    "name": (rec.get("NAMEBR") or rec.get("NAMEFULL") or "").strip(),
                    "hc": (rec.get("NAMEHCR") or rec.get("NAMEFULL") or "").strip(),
                    "bank": (rec.get("NAMEFULL") or "").strip(),
                    "cert": str(rec.get("CERT") or "").strip(),
                    "city": (rec.get("CITYBR") or "").strip(),
                    "lat": float(lat),
                    "lon": float(lon),
                    "dep": float(dep) if dep not in (None, "") else 0.0,  # $ thousands
                })
            except (TypeError, ValueError):
                continue
        if len(rows) < LIMIT:
            break
        offset += LIMIT
    return out


def main():
    all_branches = []
    summary = {}
    for y in YEARS:
        print(f"-> {y} ...", file=sys.stderr)
        try:
            recs = pull_year(y)
        except Exception as e:
            print(f"   SKIP {y}: {e}", file=sys.stderr)
            continue
        all_branches.extend(recs)
        total_dep = sum(r["dep"] for r in recs) / 1e6  # $B
        summary[y] = {"branches": len(recs), "deposits_billions": round(total_dep, 2)}
        print(f"   {y}: {len(recs)} branches, ${total_dep:,.1f}B deposits", file=sys.stderr)

    out = {
        "region": "Maricopa County, AZ (Phoenix metro)",
        "source": "FDIC Summary of Deposits (banks.data.fdic.gov/api/sod)",
        "deposit_units": "USD thousands (DEPSUMBR)",
        "years": sorted(summary.keys()),
        "summary": summary,
        "branches": all_branches,
    }
    with open("data/branches.json", "w") as f:
        json.dump(out, f)
    print(f"\nWROTE data/branches.json — {len(all_branches)} branch-years across "
          f"{len(summary)} years", file=sys.stderr)


if __name__ == "__main__":
    main()
