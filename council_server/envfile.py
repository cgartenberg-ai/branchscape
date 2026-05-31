# branchscape/council_server/envfile.py
# Minimal .env support (stdlib only — no python-dotenv dependency).
import os

def parse_env(text):
    """Parse simple KEY=VALUE lines into a dict.
    Ignores blank lines and # comments; strips optional surrounding quotes;
    tolerates a leading 'export '. Does NOT touch os.environ."""
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        if key:
            out[key] = val
    return out

def load_env(path, override=False):
    """Load KEY=VALUE pairs from `path` into os.environ. Existing env vars win
    unless override=True. Returns the dict of keys applied (no-op if missing)."""
    if not os.path.exists(path):
        return {}
    applied = parse_env(open(path, encoding="utf-8").read())
    for k, v in applied.items():
        if override or k not in os.environ:
            os.environ[k] = v
    return applied
