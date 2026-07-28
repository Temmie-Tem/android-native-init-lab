import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
READY_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p280_process_v2_ready_1.json"
)
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class S22PlusFyg8P280ProcessV2ReadyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = importlib.import_module("device_action_f1_v2")

    def test_consumed_ready1_rejects_execution_source_drift(self):
        with self.assertRaisesRegex(
            self.core.F1V2Error,
            "candidate source preimage differs from execution-critical sources",
        ):
            self.core.verify_bundle(ROOT, READY_MANIFEST)


if __name__ == "__main__":
    unittest.main()
