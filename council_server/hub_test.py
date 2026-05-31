# branchscape/council_server/hub_test.py
import unittest
from council_server.hub import EventHub

class HubTest(unittest.TestCase):
    def test_subscriber_receives_published_events(self):
        hub = EventHub()
        q = hub.subscribe()
        hub.publish({"type": "phase_change", "data": {"beat": "gather"}})
        evt = q.get(timeout=1)
        self.assertEqual(evt["type"], "phase_change")
        self.assertIn("ts", evt)  # hub stamps ts

    def test_multiple_subscribers_all_receive(self):
        hub = EventHub()
        a, b = hub.subscribe(), hub.subscribe()
        hub.publish({"type": "error", "data": {}})
        self.assertEqual(a.get(timeout=1)["type"], "error")
        self.assertEqual(b.get(timeout=1)["type"], "error")

    def test_unsubscribe_stops_delivery(self):
        hub = EventHub()
        q = hub.subscribe()
        hub.unsubscribe(q)
        hub.publish({"type": "error", "data": {}})
        self.assertTrue(q.empty())

if __name__ == "__main__":
    unittest.main()
