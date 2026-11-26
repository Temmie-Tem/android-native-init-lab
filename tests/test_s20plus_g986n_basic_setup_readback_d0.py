"""Host-only checks for current-restored basic-setup readback separation."""

from contextlib import ExitStack, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
RETAINED = ROOT / "workspace/private/runs/s20plus-g986n-basic-setup-f1/run-1795726991377518240"
sys.path.insert(0, str(SCRIPTS))


@unittest.skipUnless((RETAINED / "terminal.json").is_file(), "requires the retained basic-setup closure")
class CurrentRestoredReadback(unittest.TestCase):
    def setUp(self):
        import s20plus_g986n_basic_setup_readback_d0 as profile

        self.m = profile
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.parent = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.patch(profile, "PARENT", self.parent)

    def patch(self, obj, name, *args, **kwargs):
        return self.stack.enter_context(patch.object(obj, name, *args, **kwargs))

    def test_pinned_current_boot_and_original_observation_gap(self):
        m = self.m
        expected, probe = m.closure()
        self.assertIn(expected["boot_id_sha256"], probe)
        self.assertIn("y2q_basic_v1=", probe)
        self.assertIn("/proc/last_kmsg", probe)
        self.assertEqual(m.SCOPE, "CURRENT_RESTORED_BOOT_ONLY")
        original = m.checked

        def changed(path, pin):
            raw = original(path, pin)
            if path == m.RUN / "mainline-return-evidence.json":
                data = json.loads(raw)
                data["state"] = "no_record"
                return json.dumps(data).encode()
            return raw

        self.patch(m, "checked", side_effect=changed)
        with self.assertRaisesRegex(ValueError, "first-return gap"):
            m.closure()

    def fixture(self, after):
        m = self.m
        identity = {"shell": "0" * 64}
        expected = {k: str(i + 1) * 64 for i, k in enumerate(m.IDENTITY)}
        script = "fixed bounded fixture"
        before = ("fixture-serial", "fixture-port", {"boot": "expected"})
        admit = self.patch(m.stock, "admit")
        bracket = self.patch(m.stock, "bracket", side_effect=[before, before if after else None])
        self.patch(m.health.base, "tool_receipt", return_value={})
        self.patch(m.health, "_validate_adb_receipt", return_value={"path": "/fixture/adb"})
        self.patch(m, "closure", return_value=(expected, script))
        self.patch(m, "subject", return_value=identity)
        self.patch(m.health, "_ALLOWED_EVIDENCE_NAMES", m.health._ALLOWED_EVIDENCE_NAMES | {"intent.json"})
        self.patch(m.health, "_EVIDENCE_MAXIMUMS", {**m.health._EVIDENCE_MAXIMUMS, "intent.json": 16384})

        def bounded(command, timeout, maximum):
            saved = json.loads((self.parent / "observation/intent.json").read_bytes())
            self.assertEqual(saved["binding"], expected)
            self.assertEqual((timeout, maximum), (120, 96))
            self.assertEqual(command, ["/fixture/adb", "-s", "fixture-serial", "shell", "-T", "su", "-c",
                                       "'fixed bounded fixture'"])
            self.assertEqual(admit.call_count, 2)
            return "completed", 0, b"y2q_basic_v1=160,1,1,0,1,0,0\n", b""

        capture = self.patch(m.io, "root_capture", side_effect=bounded)
        return (identity, expected, script), bracket, capture

    def test_post_twrp_counts_are_separate_and_no_raw_log_is_published(self):
        m = self.m
        args, bracket, capture = self.fixture(after=True)
        with redirect_stdout(io.StringIO()) as output:
            m.observe(*args)
        node = self.parent / "observation"
        data = json.loads((node / "result.json").read_bytes())
        receipt = json.loads((node / "root-receipt.json").read_bytes())
        self.assertEqual(set(p.name for p in node.iterdir()), {"intent.json", "root-receipt.json", "result.json"})
        self.assertEqual(data["scope"], m.SCOPE)
        self.assertIs(data["first_return_attributed"], False)
        self.assertIs(data["operator_reported_intervening_twrp"], True)
        self.assertEqual(data["facts"]["dt_enter_pair_count"], 1)
        self.assertEqual(json.loads(output.getvalue()), dict(scope=m.SCOPE, facts=data["facts"]))
        self.assertIn("stdout_sha256", receipt)
        self.assertNotIn("stdout", receipt)
        self.assertEqual(bracket.call_count, 2)
        capture.assert_called_once()

    def test_changed_current_boot_preserves_failure_and_consumed_intent(self):
        m = self.m
        args, _, capture = self.fixture(after=False)
        with self.assertRaisesRegex(ValueError, "incomplete current restored boot bracket"):
            m.observe(*args)
        node = self.parent / "observation"
        self.assertTrue((node / "failure.json").exists())
        self.assertTrue((node / "intent.json").exists())
        self.assertFalse((node / "result.json").exists())
        with self.assertRaises(FileExistsError):
            m.observe(*args)
        capture.assert_called_once()

    def test_transient_initial_bracket_failure_does_not_reserve_observation(self):
        m = self.m
        args, bracket, capture = self.fixture(after=True)
        bracket.side_effect = ValueError("transient ADB bracket failure")
        with self.assertRaisesRegex(ValueError, "transient ADB bracket failure"):
            m.observe(*args)
        self.assertFalse((self.parent / "observation").exists())
        capture.assert_not_called()


if __name__ == "__main__":
    unittest.main()
