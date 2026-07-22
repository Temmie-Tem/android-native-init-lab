import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
DRAFT_MANIFEST = (
    ROOT
    / "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_r4w1d_process_v2_draft.json"
)
READY_MANIFEST = (
    ROOT
    / "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_r4w1d_process_v2_ready_1.json"
)


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R4W1DProcessV2ManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        cls.core = load("r4w1d_process_core_tested", "device_action_f1_v2.py")
        cls.live = load("r4w1d_process_live_tested", "device_action_f1_live_v2.py")

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(SCRIPTS))

    def test_exact_draft_bundle_passes_host_validation(self):
        bundle = self.core.verify_bundle(ROOT, DRAFT_MANIFEST)
        self.assertEqual(bundle.manifest["status"], "draft-host-only")
        self.assertEqual(
            bundle.receipt["candidate_ap"]["sha256"],
            "e35cee4c81966f7b3955af60dfb4921edbb9a07f7a10336d6cc9fddfa915d649",
        )
        self.assertEqual(
            bundle.sha256,
            "e40cd63f3675ad763af3ac325a06318850095e422e8790bea139a0c63fbf558a",
        )

    def test_acceptance_is_exact_compact_d_marker(self):
        bundle = self.core.verify_bundle(ROOT, DRAFT_MANIFEST)
        acceptance = bundle.manifest["observation"]["acceptance"]
        marker = acceptance["marker"].encode()
        record = b"\n" + marker + b"\n"
        self.assertTrue(self.live.classify_acceptance(record, acceptance)["accepted"])
        self.assertFalse(
            self.live.classify_acceptance(record + record, acceptance)["accepted"]
        )

    def test_draft_is_rejected_before_connected_prepare_allocation(self):
        bundle = self.core.verify_bundle(ROOT, DRAFT_MANIFEST)
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "must-not-exist"
            with self.assertRaisesRegex(
                self.live.F1LiveError, "manifest is not ready for F1 approval"
            ):
                self.live.prepare_connected(ROOT, bundle, run_dir, object())
            self.assertFalse(run_dir.exists())

    def test_ready_manifest_is_data_only_promotion(self):
        draft = self.core.verify_bundle(ROOT, DRAFT_MANIFEST)
        ready = self.core.verify_bundle(ROOT, READY_MANIFEST)
        mutable = {"manifest_id", "run_id", "status"}
        self.assertEqual(
            {
                key
                for key in draft.manifest
                if draft.manifest[key] != ready.manifest[key]
            },
            mutable,
        )
        self.assertEqual(ready.manifest["status"], "ready-for-f1-approval")
        self.assertEqual(
            ready.sha256,
            "babc51704eb918679fb72a0d0c4c20cc41d4e54e3aed1e6190580fa8c02cf1b9",
        )


if __name__ == "__main__":
    unittest.main()
