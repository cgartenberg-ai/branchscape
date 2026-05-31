#!/usr/bin/env python3
"""
Pull latest institution-level financials for every bank (CERT) present in the
2024 branch set, to enrich the drill-down card. These are PARENT-INSTITUTION
figures (the whole bank) — branch-level lending/mortgages are not reported in
public data; only branch deposits are (FDIC SOD).

Source: https://api.fdic.gov/banks/financials  (free, no key)
Fields: ASSET, DEP, NETINC, LNLSGR (gross loans), LNCI (C&I / business loans),
        LNRERES (1-4 family residential mortgages), ROA.
Output: data/financials.js -> window.FINANCIALS = {cert: {...}}
"""
import json, sys, time, urllib.parse, urllib.request

API = "https://api.fdic.gov/banks/financials"
FIELDS = "CERT,REPDTE,ASSET,DEP,NETINC,LNLSGR,LNCI,LNRERES,ROA"
PACE, MAX_RETRIES = 1.4, 6


def fetch(cert):
    qs = urllib.parse.urlencode({
        "filters": f"CERT:{cert}", "fields": FIELDS,
        "sort_by": "REPDTE", "sort_order": "DESC", "limit": 1, "format": "json",
    })
    url = f"{API}?{qs}"
    delay = PACE
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "branchscape/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read().decode("utf-8")
            if body.strip().startswith("{"):
                data = json.loads(body).get("data", [])
                return data[0]["data"] if data else None
            raise ValueError(body[:80])
        except Exception as e:
            time.sleep(delay * (attempt + 1))
            if attempt == MAX_RETRIES - 1:
                print(f"   FAIL cert {cert}: {str(e)[:70]}", file=sys.stderr)
    return None


def main():
    d = json.load(open("data/branches.json"))
    certs = sorted({b["cert"] for b in d["branches"]
                    if b["year"] == 2024 and b.get("cert")})
    print(f"-> {len(certs)} unique 2024 CERTs", file=sys.stderr)

    out = {}
    for i, cert in enumerate(certs):
        time.sleep(PACE)
        rec = fetch(cert)
        if not rec:
            continue
        out[str(cert)] = {
            "repdte": rec.get("REPDTE"),
            "asset": rec.get("ASSET"),       # $ thousands
            "dep": rec.get("DEP"),
            "netinc": rec.get("NETINC"),
            "loans": rec.get("LNLSGR"),
            "ci": rec.get("LNCI"),           # C&I / business loans
            "mortg": rec.get("LNRERES"),     # 1-4 family residential
            "roa": rec.get("ROA"),
        }
        if (i + 1) % 10 == 0:
            print(f"   {i+1}/{len(certs)} ...", file=sys.stderr)

    with open("data/financials.js", "w") as f:
        f.write("window.FINANCIALS = ")
        json.dump(out, f, separators=(",", ":"))
        f.write(";")
    print(f"WROTE data/financials.js — {len(out)}/{len(certs)} institutions", file=sys.stderr)


if __name__ == "__main__":
    main()
