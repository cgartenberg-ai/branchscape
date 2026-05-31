# branchscape/council_server/record.py
import json, time

class Recorder:
    """Appends every emitted event as one JSON line."""
    def __init__(self, path):
        self.path = path
        self._f = open(path, "a", encoding="utf-8")
    def write(self, event):
        self._f.write(json.dumps(event) + "\n"); self._f.flush()
    def close(self):
        try: self._f.close()
        except Exception: pass

def replay_events(path, sleep=time.sleep, speed=1.0):
    """Yield events from a JSONL run log, pausing by the original inter-event gaps."""
    prev = None
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        evt = json.loads(line)
        ts = evt.get("ts")
        if prev is not None and ts is not None:
            gap = max(0.0, (ts - prev) / speed)
            if gap:
                sleep(min(gap, 3.0))  # cap any pause at 3s
        prev = ts
        yield evt
