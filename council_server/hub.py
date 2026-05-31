# branchscape/council_server/hub.py
import queue, threading, time

class EventHub:
    """Thread-safe fan-out of event dicts to all current subscribers."""
    def __init__(self):
        self._subs = set()
        self._lock = threading.Lock()

    def subscribe(self):
        q = queue.Queue()
        with self._lock:
            self._subs.add(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            self._subs.discard(q)

    def publish(self, event):
        if "ts" not in event:
            event["ts"] = time.time()
        event.setdefault("agent", None)
        event.setdefault("data", {})
        with self._lock:
            subs = list(self._subs)
        for q in subs:
            q.put(event)
        return event
