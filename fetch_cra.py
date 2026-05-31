#!/usr/bin/env python3
"""
CRA small-business lending for Maricopa County, by reporting institution.
Per-bank CRA is COUNTY-level only (tract-level CRA exists only as all-lender
aggregates), so this is each reporter's total Maricopa small-business
originations: loan count + $ volume.

Inputs (already downloaded under data/raw/, via Wayback mirror of FFIEC):
  - CRA2023_Transmittal.dat  : respondent ID (+agency) -> bank name
  - cra2023_Discl_D11.dat     : Small Business Loans by County (Originations)

D1-1 layout (1-based): state 23-24, county 25-27, income-group 40-42,
report-level 43-45 (40 = County Total), then size-bucket count/amount pairs:
  #<=100k 46-55, $<=100k 56-65, #100-250k 66-75, $ 76-85, #250k-1M 86-95, $ 96-105
Amounts are in $thousands. We take the row with Report Level 40 and blank
income group (the county grand total across income categories).

Output: data/cra.js -> window.CRA = {year, byCert:{cert:{n,amt}}}
"""
import json, re, sys

STOP = re.compile(r'\b(NATIONAL ASSOCIATION|ASSOCIATION|NATIONAL|ASSN|NATL|NA|N A|FSB|SSB|THE|COMPANY|CO|INCORPORATED|INC|LLC|LTD|BANCORP|BANCORPORATION|FINANCIAL|GROUP|HOLDINGS)\b')
def norm(s):
    s = (s or "").upper()
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    s = STOP.sub(' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\b(\w) (?=\w\b)', r'\1', s)   # collapse single-letter runs: U S -> US
    return re.sub(r'\s+', ' ', s).strip()

def i(s):
    s = s.strip()
    return int(s) if s.isdigit() else 0


def main():
    # respondent (id+agency) -> name
    respname = {}
    with open("data/raw/CRA2023_Transmittal.dat", encoding="latin-1") as f:
        for ln in f:
            if len(ln) < 45:
                continue
            key = ln[0:11]            # respid(10) + agency(1)
            respname[key] = ln[15:45].strip()
    print(f"-> {len(respname)} CRA reporters in transmittal", file=sys.stderr)

    # our banks (2024): normalized name -> cert
    d = json.load(open("data/branches.json"))
    mybynorm = {}
    for b in d["branches"]:
        if b["year"] == 2024 and b.get("cert"):
            nm = b.get("bank") or b.get("hc")
            # transmittal names are truncated to 30 chars, so index both forms
            mybynorm.setdefault(norm(nm), b["cert"])
            mybynorm.setdefault(norm(nm[:30]), b["cert"])

    # scan D1-1 for Maricopa county totals
    byCert = {}
    matched_reporters = 0
    seen = set()
    with open("data/raw/cra2023_Discl_D11.dat", encoding="latin-1") as f:
        for ln in f:
            if ln[22:24] != "04" or ln[24:27] != "013":
                continue
            rl = ln[42:45].strip()                  # Report Level (e.g. "040")
            if not rl.isdigit() or int(rl) != 40:   # 40 = County Total
                continue
            if ln[39:42].strip() != "":            # blank income group = grand total
                continue
            key = ln[5:16]                          # respid(10)+agency(1)
            name = respname.get(key)
            if not name:
                continue
            cert = mybynorm.get(norm(name))
            if not cert:
                continue
            n = i(ln[45:55]) + i(ln[65:75]) + i(ln[85:95])
            amt = i(ln[55:65]) + i(ln[75:85]) + i(ln[95:105])   # $thousands
            if key not in seen:
                seen.add(key); matched_reporters += 1
            c = byCert.setdefault(cert, {"n": 0, "amt": 0})
            c["n"] += n; c["amt"] += amt

    print(f"-> matched {matched_reporters} Maricopa CRA reporters to our banks; "
          f"{len(byCert)} certs", file=sys.stderr)

    out = {"year": 2023, "byCert": byCert}
    with open("data/cra.js", "w") as f:
        f.write("window.CRA = ")
        json.dump(out, f, separators=(",", ":"))
        f.write(";")
    # show top
    rows = sorted(byCert.items(), key=lambda kv: -kv[1]["amt"])[:6]
    for cert, v in rows:
        print(f"   cert {cert}: {v['n']} loans  ${v['amt']/1e6:.2f}B small-biz", file=sys.stderr)
    print("WROTE data/cra.js", file=sys.stderr)


if __name__ == "__main__":
    main()
