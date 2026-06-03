# branchscape/council_server/gate_test.py
import unittest
from council_server.gate import RunGate

class RunGateTest(unittest.TestCase):
    def test_no_passcode_authorizes_everyone(self):
        g = RunGate(passcode=None)
        self.assertTrue(g.authorized(None))
        self.assertTrue(g.authorized("whatever"))
        g2 = RunGate(passcode="")  # empty == no passcode
        self.assertTrue(g2.authorized(None))

    def test_passcode_required_when_set(self):
        g = RunGate(passcode="hunter2")
        self.assertTrue(g.authorized("hunter2"))
        self.assertFalse(g.authorized("wrong"))
        self.assertFalse(g.authorized(None))

    def test_concurrency_cap_blocks_when_full_and_release_frees_a_slot(self):
        g = RunGate(max_concurrent=2)
        self.assertTrue(g.try_acquire())   # 1
        self.assertTrue(g.try_acquire())   # 2
        self.assertFalse(g.try_acquire())  # full
        self.assertEqual(g.active, 2)
        g.release()
        self.assertTrue(g.try_acquire())   # slot freed
        self.assertEqual(g.active, 2)

    def test_max_concurrent_is_at_least_one_and_coerces(self):
        self.assertEqual(RunGate(max_concurrent=0).max_concurrent, 1)
        self.assertEqual(RunGate(max_concurrent="3").max_concurrent, 3)

if __name__ == "__main__":
    unittest.main()
