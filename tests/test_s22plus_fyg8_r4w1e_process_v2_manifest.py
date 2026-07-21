import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
DRAFT_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_r4w1e_e1_process_v2_draft.json"
)
READY_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_r4w1e_e1_process_v2_ready_1.json"
)


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R4W1EProcessV2ManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        cls.core = load("r4w1e_process_core_tested", "device_action_f1_v2.py")
        cls.live = load("r4w1e_process_live_tested", "device_action_f1_live_v2.py")

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(SCRIPTS))

    def test_exact_draft_bundle_pins_offline_checkpoint_contract(self):
        bundle = self.core.verify_bundle(ROOT, DRAFT_MANIFEST)
        self.assertEqual(bundle.manifest["status"], "draft-host-only")
        self.assertEqual(
            bundle.receipt["candidate_ap"]["sha256"],
            "ff4e1766b82306005bfa3cbb6280347ad6133bb60801c9d6236d7eaf044bd421",
        )
        contract = bundle.receipt["observation_contract"]
        self.assertTrue(contract["verification"]["verified"])
        self.assertEqual(
            contract["verification"]["run_id"],
            "395f27c3ac34ebe61395d7efd5a058e8",
        )
        self.assertEqual(
            bundle.sha256,
            "d83dcc6415dad1c4efcf54409df6128cfac938998f384c3754e7b9b6ca3d0484",
        )

    def test_draft_remains_rejected_before_connected_prepare(self):
        bundle = self.core.verify_bundle(ROOT, DRAFT_MANIFEST)
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "must-not-exist"
            with self.assertRaisesRegex(
                self.live.F1LiveError, "manifest is not ready for F1 approval"
            ):
                self.live.prepare_connected(ROOT, bundle, run_dir, object())
            self.assertFalse(run_dir.exists())

    def test_live_adapter_dispatches_exact_terminal_checkpoint(self):
        bundle = self.core.verify_bundle(ROOT, DRAFT_MANIFEST)
        acceptance = bundle.manifest["observation"]["acceptance"]
        checkpoint = self.live.typed_evidence.checkpoint
        run_id = bytes.fromhex(acceptance["run_id"])
        region = checkpoint.initial_region(0x300000, 9)
        for stage in checkpoint.PROFILE_STAGE_SEQUENCES["E1"]:
            outcome = (
                checkpoint.OUTCOME_SUCCESS
                if stage == checkpoint.PROFILE_TERMINAL_STAGE["E1"]
                else checkpoint.OUTCOME_PROGRESS
            )
            region = checkpoint.apply_request(
                region,
                checkpoint.encode_request(
                    "E1", stage, run_id=run_id, outcome=outcome
                ),
            )
        result = self.live.classify_acceptance(
            b"prefix" + region + b"suffix", acceptance
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(result["classification"], "CHECKPOINT_TERMINAL_SUCCESS")

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
            ready.manifest["observation"]["acceptance"]["kind"],
            "retained_checkpoint_after_rollback",
        )
        self.assertEqual(
            ready.sha256,
            "c5b5cab64eb92fc9826884470c719f342c8893b49fa90f20e831b0cf9ff78f0d",
        )


if __name__ == "__main__":
    unittest.main()
