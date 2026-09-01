from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import stat
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "prepare_s22plus_fyg8_p324_process_v2.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p324_ready", SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("P324 ready builder cannot load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P324ReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.manifest, cls.payloads, cls.verification = cls.module.build()

    def test_exact_p324_defaults_and_acm_primary_banner(self) -> None:
        module = self.module
        observation = self.manifest["observation"]
        self.assertEqual(self.manifest["manifest_id"], module.DEFAULT_MANIFEST_ID)
        self.assertEqual(self.manifest["run_id"], module.DEFAULT_LIVE_RUN_ID)
        self.assertEqual(
            observation[module.current_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY],
            module.current_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE,
        )
        run_id = module.p324_adapter.P324_RUN_ID_HEX
        self.assertEqual(observation["candidate_observer"]["usb_serial"], "S22E3" + run_id)
        expected_banner = ("S22PLUS-FYG8-E3:" + run_id + "\n").encode("ascii")
        self.assertEqual(
            bytes.fromhex(observation["candidate_observer"]["banner_hex"]),
            expected_banner,
        )
        self.assertNotIn(
            "prepare_s22plus_fyg8_p323_bound_for_p324", sys.modules
        )
        self.assertEqual(module.P323_PREPARE_IDENTITY["size"], 13_020)

    def test_rehearsal_is_verified_and_non_authorizing(self) -> None:
        module = self.module
        run_manifest = json.loads(self.payloads["run_manifest"])
        self.assertEqual(
            run_manifest["schema"], module.current_evidence.P324_RUN_MANIFEST_SCHEMA
        )
        self.assertEqual(
            run_manifest["observation_contract"]["accepted_identity"],
            "P324_STOCK_OBSERVER_V4_RETAINED",
        )
        self.assertEqual(run_manifest["run_id"], module.p324_adapter.P324_RUN_ID_HEX)
        self.assertTrue(self.verification["verified"])
        self.assertFalse(self.verification["candidate_success"])
        for old in ("P321_STOCK_OBSERVER_V4_RETAINED", "P323_STOCK_OBSERVER_V4_RETAINED"):
            self.assertNotEqual(run_manifest["observation_contract"]["accepted_identity"], old)

    def test_manifest_reopens_and_publication_modes_are_bounded(self) -> None:
        module = self.module
        payload = module.manifest_bytes(self.manifest)
        module.verify_manifest(self.manifest, payload)
        module.core.verify_bundle(ROOT, module.DEFAULT_MANIFEST)
        self.assertEqual(module.DEFAULT_MANIFEST.read_bytes(), payload)
        self.assertIn(stat.S_IMODE(module.DEFAULT_MANIFEST.stat().st_mode), {0o644, 0o664})
        self.assertEqual(stat.S_IMODE(module.DEFAULT_PROMOTION.stat().st_mode), 0o700)
        for name in ("candidate-static.json", "run-manifest.json", "static-check-result.json"):
            item = module.DEFAULT_PROMOTION / name
            self.assertEqual(stat.S_IMODE(item.stat().st_mode), 0o400)
            self.assertEqual(item.stat().st_nlink, 1)

    def test_p324_output_namespaces_and_exact_candidate_binding(self) -> None:
        module = self.module
        self.assertIn("p324", str(module.DEFAULT_BUILDER_OUTPUT))
        self.assertIn("p324", str(module.DEFAULT_STATIC_OUTPUT))
        self.assertIn("p324", str(module.DEFAULT_PROMOTION))
        self.assertIn("p324", str(module.DEFAULT_MANIFEST))
        self.assertEqual(
            self.manifest["candidate_ap"]["sha256"],
            module.p324_static.build_result()["candidate"]["a"]["ap_tar_md5"]["sha256"],
        )
        self.assertEqual(
            self.manifest["rollback_ap"],
            {"path": module.relative(module.DEFAULT_ROLLBACK_AP), **module.ROLLBACK_IDENTITY},
        )


if __name__ == "__main__":
    unittest.main()
