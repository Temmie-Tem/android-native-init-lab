import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1a_overwrite_budget.py"


def load():
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_r4w1a_overwrite_budget_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R4W1AOverwriteBudgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analyzer = load()

    def test_capture_reports_oldest_latest_and_span(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = bytearray(b"\0" * 128)
            payload[:45] = b"[    3.500000] first\n[   33.250000] last\n"
            path = root / "capture.bin"
            path.write_bytes(payload)
            old_size = self.analyzer.SNAPSHOT_SIZE
            try:
                self.analyzer.SNAPSHOT_SIZE = len(payload)
                result = self.analyzer.inspect_capture(
                    root, "test", Path("capture.bin"), hashlib.sha256(payload).hexdigest()
                )
            finally:
                self.analyzer.SNAPSHOT_SIZE = old_size
            self.assertEqual(result["oldest_timestamp_sec"], 3.5)
            self.assertEqual(result["latest_timestamp_sec"], 33.25)
            self.assertEqual(result["visible_span_sec"], 29.75)

    def test_capture_fails_closed_without_timestamps(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = b"x" * 64
            path = root / "capture.bin"
            path.write_bytes(payload)
            old_size = self.analyzer.SNAPSHOT_SIZE
            try:
                self.analyzer.SNAPSHOT_SIZE = len(payload)
                with self.assertRaises(self.analyzer.AnalysisError):
                    self.analyzer.inspect_capture(
                        root, "test", Path("capture.bin"), hashlib.sha256(payload).hexdigest()
                    )
            finally:
                self.analyzer.SNAPSHOT_SIZE = old_size

    def test_analyzer_keeps_a1_blocked(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"risk_verdict": "HIGH_RISK_UNRESOLVED"', source)
        self.assertIn('"a1_ready": False', source)
        self.assertIn('"live_authorized": False', source)
        self.assertNotIn('"adb"', source.lower())


if __name__ == "__main__":
    unittest.main()
