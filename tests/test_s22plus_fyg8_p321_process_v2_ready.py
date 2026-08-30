from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "prepare_s22plus_fyg8_p321_process_v2.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p321_process_v2_ready", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("P3.21 Process-v2 preparation source cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P321ProcessV2ReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.manifest, cls.payloads, cls.verification = cls.module.build()

    def test_single_ready_rehearsal_binds_exact_boot_only_candidate(self) -> None:
        manifest = self.manifest
        self.assertEqual(manifest["status"], "ready-for-f1-approval")
        self.assertEqual(manifest["allowed_member"], "boot.img.lz4")
        self.assertEqual(
            manifest["candidate_ap"]["sha256"],
            "770694d16123ea9a0ce28aded393fbf44e280794e5a94107c47952e904586514",
        )
        self.assertEqual(
            manifest["rollback_ap"]["sha256"],
            "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
        )
        acceptance = manifest["observation"]["acceptance"]
        self.assertEqual(
            acceptance["userspace_overlay_contract_id"],
            self.module.adapter.P321_OVERLAY_CONTRACT_ID,
        )
        self.assertTrue(self.verification["verified"])
        self.assertFalse(self.verification["causal_result_allowed"])
        self.assertFalse(self.verification["candidate_success"])

    def test_promotion_is_canonical_and_uses_one_p321_run_id(self) -> None:
        self.assertEqual(
            set(self.payloads),
            {"candidate_static", "run_manifest", "static_check"},
        )
        run_manifest = json.loads(self.payloads["run_manifest"])
        static_result = json.loads(self.payloads["static_check"])
        self.assertEqual(
            self.payloads["run_manifest"], self.module.canonical(run_manifest)
        )
        self.assertEqual(
            self.payloads["static_check"], self.module.canonical(static_result)
        )
        self.assertEqual(run_manifest["run_id"], self.module.adapter.P321_RUN_ID_HEX)
        self.assertEqual(static_result["run_id"], self.module.adapter.P321_RUN_ID_HEX)
        closure = self.verification["ap_payload_closure"]
        self.assertEqual(closure["run_id"], self.module.adapter.P321_RUN_ID_HEX)
        self.assertEqual(
            closure["image"]["sha256"],
            "f3b18031ffc6548d619f3c35e92b6f8b72a1fc1f7863c36a3b5b14cbe09c2810",
        )
        self.assertEqual(
            closure["init"]["sha256"],
            "2d260502fe55ed001532fc9fb8ca9bf2fed29f2722ce20d324df03aadd245bc5",
        )

    def test_p321_runtime_projection_stays_noncausal(self) -> None:
        import device_action_f1_live_v2 as live

        raw = self.module.adapter._full_fixture(  # noqa: SLF001
            state="COMPLETE", observer_error=False
        )
        classified = self.module.evidence.classify_e1_latest_stage(
            raw, self.module.adapter.acceptance_fixture()
        )
        self.assertEqual(
            classified["overlay_contract_id"],
            self.module.adapter.P321_OVERLAY_CONTRACT_ID,
        )
        self.assertEqual(classified["proof_class"], "NONCAUSAL_SUCCESS_PATH")
        self.assertEqual(len(classified["p321_stock"]), 1)
        projection = live._p320_terminal_projection(classified)  # noqa: SLF001
        self.assertFalse(projection["causal_result_allowed"])
        self.assertFalse(projection["candidate_success"])


if __name__ == "__main__":
    unittest.main()
