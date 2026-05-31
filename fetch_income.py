#!/usr/bin/env python3
"""
Build a 'community wealth' heat field beneath the branches.

  - Wealth:    IRS SOI ZIP-code data (21zpallagi.csv) -> average AGI per return
               per ZIP (free, no key). A00100 = AGI [thousands], N1 = # returns.
  - Centroids: Census 2023 Gazetteer ZCTA file (GEOID + INTPTLAT/LONG)

Output: data/income.js  ->  window.INCOME_DATA = [{zip,lat,lon,income}, ...]
"""
import csv, io, json, sys, zipfile, urllib.request

UA = {"User-Agent": "branchscape/1.0"}
LAT_MIN, LAT_MAX = 32.45, 34.10
LON_MIN, LON_MAX = -113.40, -111.00

IRS_URL = "https://www.irs.gov/pub/irs-soi/21zpallagi.csv"
GAZ_URL = ("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
           "2023_Gazetteer/2023_Gaz_zcta_national.zip")


def main():
    print("-> IRS SOI ZIP AGI (Arizona) ...", file=sys.stderr)
    req = urllib.request.Request(IRS_URL, headers=UA)
    agg = {}   # zip -> [sum_returns, sum_agi_thousands]
    with urllib.request.urlopen(req, timeout=180) as r:
        reader = csv.DictReader(io.TextIOWrapper(r, encoding="latin-1"))
        for row in reader:
            if row.get("STATE") != "AZ":
                continue
            z = (row.get("zipcode") or "").strip().zfill(5)
            if z in ("00000", "99999"):
                continue
            try:
                n1 = float(row["N1"]); agi = float(row["A00100"])
            except (TypeError, ValueError, KeyError):
                continue
            a = agg.setdefault(z, [0.0, 0.0])
            a[0] += n1; a[1] += agi
    income = {z: (v[1] * 1000.0 / v[0]) for z, v in agg.items() if v[0] > 50}
    print(f"   {len(income)} AZ ZIPs with AGI", file=sys.stderr)

    print("-> Gazetteer ZCTA centroids ...", file=sys.stderr)
    zf = zipfile.ZipFile(io.BytesIO(
        urllib.request.urlopen(urllib.request.Request(GAZ_URL, headers=UA), timeout=120).read()))
    name = [n for n in zf.namelist() if n.lower().endswith(".txt")][0]
    lines = zf.read(name).decode("latin-1").splitlines()
    h = [c.strip() for c in lines[0].split("\t")]
    gi, la, lo = h.index("GEOID"), h.index("INTPTLAT"), h.index("INTPTLONG")

    out = []
    for ln in lines[1:]:
        p = ln.split("\t")
        if len(p) <= lo:
            continue
        z = p[gi].strip().zfill(5)
        if z not in income:
            continue
        try:
            lat = float(p[la]); lon = float(p[lo].strip())
        except ValueError:
            continue
        if LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
            out.append({"zip": z, "lat": round(lat, 5), "lon": round(lon, 5),
                        "income": int(round(income[z]))})

    out.sort(key=lambda r: r["income"])
    with open("data/income.js", "w") as f:
        f.write("window.INCOME_DATA = ")
        json.dump(out, f, separators=(",", ":"))
        f.write(";")
    incs = [r["income"] for r in out]
    print(f"   {len(out)} metro ZIPs | avg AGI ${min(incs):,}-${max(incs):,}"
          f" median ${incs[len(incs)//2]:,}", file=sys.stderr)
    print("WROTE data/income.js", file=sys.stderr)


if __name__ == "__main__":
    main()
