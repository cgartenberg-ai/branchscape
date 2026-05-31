#!/usr/bin/env python3
"""
All-lender CRA small-business lending by census tract for Maricopa, from the
CRA AGGREGATE file (A1-1), which — unlike the per-lender disclosure file — DOES
report at the individual census-tract level (summed across all reporters).

A1-1 layout (1-based): state 12-13, county 14-16, census tract 22-28 (e.g.
"0301.01"), report level 34-36 (blank = individual tract, not a total), then
size-bucket count/amount pairs ($thousands):
  $<=100k 47-56, $100-250k 67-76, $250k-1M 87-96.

Output: data/cra_tract.js -> window.CRA_TRACT = {year, tracts:{geoid:{amt,n}}}
"""
import json, sys

SRC = "data/raw/cra2023_Aggr_A11.dat"

def i(s):
    s = s.strip()
    return int(s) if s.isdigit() else 0


def main():
    tracts = {}
    rows = 0
    with open(SRC, encoding="latin-1") as f:
        for ln in f:
            if ln[11:13] != "04" or ln[13:16] != "013":
                continue
            ct = ln[21:28].strip()
            if not ct:                         # blank tract = a total row, skip
                continue
            if ln[33:36].strip() != "":        # report level blank = individual tract
                continue
            geoid = "04013" + ct.replace(".", "")
            n = i(ln[36:46]) + i(ln[56:66]) + i(ln[76:86])
            amt = i(ln[46:56]) + i(ln[66:76]) + i(ln[86:96])   # $thousands
            if amt <= 0 and n <= 0:
                continue
            t = tracts.setdefault(geoid, {"amt": 0, "n": 0})
            t["amt"] += amt; t["n"] += n
            rows += 1

    out = {"year": 2023, "tracts": tracts}
    with open("data/cra_tract.js", "w") as f:
        f.write("window.CRA_TRACT = ")
        json.dump(out, f, separators=(",", ":"))
        f.write(";")
    tot = sum(t["amt"] for t in tracts.values()) / 1e6
    print(f"-> {len(tracts)} Maricopa tracts with small-biz lending; "
          f"${tot:.2f}B total ({rows} rows)", file=sys.stderr)
    print("WROTE data/cra_tract.js", file=sys.stderr)


if __name__ == "__main__":
    main()
