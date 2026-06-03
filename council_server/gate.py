# branchscape/council_server/gate.py
import threading

class RunGate:
    """Guards public exposure of the live council. A deliberation spends real API
    budget, so before a run starts we (1) optionally require a shared passcode and
    (2) cap the number of concurrent deliberations. Both are no-ops-friendly: an
    unset passcode authorizes everyone (local dev), and the cap is at least 1."""

    def __init__(self, passcode=None, max_concurrent=2):
        self.passcode = passcode or None          # None / "" => no passcode required
        self.max_concurrent = max(1, int(max_concurrent or 1))
        self._active = 0
        self._lock = threading.Lock()

    def authorized(self, supplied):
        """True if no passcode is configured, or the supplied one matches."""
        if not self.passcode:
            return True
        return supplied == self.passcode

    def try_acquire(self):
        """Reserve a run slot. Returns False (without reserving) if at capacity."""
        with self._lock:
            if self._active >= self.max_concurrent:
                return False
            self._active += 1
            return True

    def release(self):
        with self._lock:
            if self._active > 0:
                self._active -= 1

    @property
    def active(self):
        with self._lock:
            return self._active
