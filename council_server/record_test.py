# branchscape/council_server/record_test.py
import os, tempfile, unittest
from council_server.record import Recorder, replay_events

class RecordTest(unittest.TestCase):
    def test_recorder_appends_jsonl_and_replay_reads_back(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "run.jsonl")
            rec = Recorder(path)
            rec.write({"type": "phase_change", "data": {"beat": "gather"}})
            rec.write({"type": "verdict", "data": {"zone": "x"}})
            rec.close()
            evts = list(replay_events(path, sleep=lambda s: None))
            self.assertEqual([e["type"] for e in evts], ["phase_change", "verdict"])

if __name__ == "__main__":
    unittest.main()
