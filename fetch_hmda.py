#!/usr/bin/env python3
"""
HMDA mortgage originations for Maricopa County (FIPS 04013), by bank x census
tract, for the latest available year. Source: CFPB HMDA Data Browser (no key).

  - filers endpoint -> LEI -> institution name (to match our FDIC banks)
  - loan-level CSV  -> stream-aggregate originations by (LEI, census_tract)

We keep only banks that appear in our 2024 branch set (matched by normalized
name), keyed by FDIC CERT so the app can look it up directly.

Output: data/hmda.js -> window.HMDA = {year, byCert:{cert:{n,amt,tracts:{...}}}}
"""
import csv, io, json, re, sys, urllib.request

YEAR = 2023
COUNTY = "04013"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Accept": "application/json, text/csv, */*"}
FILERS = f"https://ffiec.cfpb.gov/v2/data-browser-api/view/filers?years={YEAR}&counties={COUNTY}"
CSVURL = f"https://ffiec.cfpb.gov/v2/data-browser-api/view/csv?years={YEAR}&counties={COUNTY}&actions_taken=1"

STOP = re.compile(r'\b(NATIONAL ASSOCIATION|ASSOCIATION|NATIONAL|ASSN|NATL|NA|N A|FSB|SSB|THE|COMPANY|CO|INCORPORATED|INC|LLC|LTD|BANCORP|BANCORPORATION|FINANCIAL|GROUP|HOLDINGS)\b')
def norm(s):
    s = (s or "").upper()
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    s = STOP.sub(' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\b(\w) (?=\w\b)', r'\1', s)   # collapse single-letter runs: U S -> US
    return re.sub(r'\s+', ' ', s).strip()


def main():
    d = json.load(open("data/branches.json"))
    banks = {}  # cert -> name (institution)
    for b in d["branches"]:
        if b["year"] == 2024 and b.get("cert"):
            banks[b["cert"]] = b.get("bank") or b.get("hc")
    mybynorm = {}
    for cert, name in banks.items():
        mybynorm.setdefault(norm(name), cert)
    print(f"-> {len(banks)} 2024 banks", file=sys.stderr)

    fil = json.loads(open("data/raw/hmda_filers.json").read())
    insts = fil.get("institutions", [])
    lei2cert = {}
    for it in insts:
        c = mybynorm.get(norm(it["name"]))
        if c:
            lei2cert[it["lei"]] = c
    print(f"-> {len(insts)} HMDA filers in Maricopa; matched {len(lei2cert)} LEIs to our banks",
          file=sys.stderr)

    agg = {}
    with open("data/raw/hmda_maricopa.csv", encoding="utf-8", errors="replace") as r:
        reader = csv.reader(r)
        hdr = next(reader)
        iL, iT, iA = hdr.index("lei"), hdr.index("census_tract"), hdr.index("loan_amount")
        rows = 0
        for row in reader:
            rows += 1
            cert = lei2cert.get(row[iL] if len(row) > iL else "")
            if not cert:
                continue
            tract = row[iT]
            try:
                amt = float(row[iA])
            except (TypeError, ValueError):
                amt = 0.0
            a = agg.setdefault(cert, {"n": 0, "amt": 0.0, "tracts": {}})
            a["n"] += 1; a["amt"] += amt
            t = a["tracts"].setdefault(tract, {"n": 0, "amt": 0.0})
            t["n"] += 1; t["amt"] += amt
    print(f"-> streamed {rows} originations; {len(agg)} of our banks have HMDA lending",
          file=sys.stderr)

    out = {"year": YEAR, "byCert": agg}
    with open("data/hmda.js", "w") as f:
        f.write("window.HMDA = ")
        json.dump(out, f, separators=(",", ":"))
        f.write(";")
    print("WROTE data/hmda.js", file=sys.stderr)


if __name__ == "__main__":
    main()
