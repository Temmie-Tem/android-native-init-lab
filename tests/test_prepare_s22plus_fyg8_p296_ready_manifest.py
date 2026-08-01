#!/usr/bin/env python3
"""Focused tests for the P2.96 Process-v2 ready-manifest adapter."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPT_DIR))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as core  # noqa: E402
import prepare_s22plus_fyg8_p296_ready_manifest as builder  # noqa: E402
import s22plus_fyg8_p296_telemetry_decoder as decoder  # noqa: E402
import s22plus_fyg8_p296_telemetry_model as model  # noqa: E402


class P296ReadyManifestBuilderTest(unittest.TestCase):
    def fixture(self):
        builder._configure()
        run_id = "12" * 16
        run_manifest = {
            "profile": "E2",
            "run_id": run_id,
            "source_contract_id": builder.SOURCE_CONTRACT_ID,
            "decoder": decoder.DECODER_ID,
            "policy_id": decoder.POLICY_ID,
            "records": {
                "long_family_hex": model.LONG_FAMILY.hex(),
                "unsat_family_hex": model.UNSAT_FAMILY.hex(),
                "terminal_stage": evidence._latest_stage_terminal(decoder, "E2"),
            },
            "observation_contract": {
                "minimum_success_count": 1,
                "clean_baseline_required": True,
            },
        }
        paths = {
            "candidate_static": ROOT / "workspace/private/a.json",
            "run_manifest": ROOT / "workspace/private/b.json",
            "static_check": ROOT / "workspace/private/c.json",
        }
        receipts = {
            name: {"size": index + 1, "sha256": f"{index + 1:064x}"}
            for index, name in enumerate(paths)
        }
        artifact = {
            "path": "workspace/private/example/AP.tar.md5",
            "size": 10,
            "sha256": "a" * 64,
        }
        return run_manifest, paths, receipts, artifact

    def test_derives_exact_p296_acceptance_and_observer(self) -> None:
        run_manifest, paths, receipts, artifact = self.fixture()
        manifest = builder.derive_manifest(
            root=ROOT,
            run_manifest=run_manifest,
            evidence_paths=paths,
            evidence_receipts=receipts,
            candidate_ap=artifact,
            rollback_ap={**artifact, "sha256": "b" * 64},
            target_profile=ROOT / builder.DEFAULT_TARGET_PROFILE,
            manifest_id=builder.DEFAULT_MANIFEST_ID,
            live_run_id=builder.DEFAULT_LIVE_RUN_ID,
            timeout_sec=builder.DEFAULT_TIMEOUT_SEC,
        )
        self.assertEqual(manifest["schema"], core.MANIFEST_SCHEMA)
        self.assertEqual(manifest["status"], "ready-for-f1-approval")
        acceptance = manifest["observation"]["acceptance"]
        self.assertEqual(acceptance["source_contract_id"], builder.SOURCE_CONTRACT_ID)
        self.assertEqual(acceptance["decoder"], decoder.DECODER_ID)
        evidence.validate_acceptance(acceptance)
        core.verify_candidate_observer_binding(
            acceptance, manifest["observation"]["candidate_observer"]
        )

    def test_defaults_are_p296_scoped_and_verify_only_is_preserved(self) -> None:
        args = builder.parse_args([])
        self.assertIn("P2.96", builder.base.__doc__)
        for value in (
            args.candidate_static,
            args.run_manifest,
            args.static_check,
            args.candidate_ap,
            args.out,
        ):
            self.assertIn("p296", value.as_posix())
        self.assertFalse(args.verify_only)
        self.assertTrue(builder.parse_args(["--verify-only"]).verify_only)

    def test_wrong_source_contract_is_rejected(self) -> None:
        run_manifest, paths, receipts, artifact = self.fixture()
        run_manifest["source_contract_id"] = "wrong"
        with self.assertRaisesRegex(builder.ManifestError, "identity mismatch"):
            builder.derive_manifest(
                root=ROOT,
                run_manifest=run_manifest,
                evidence_paths=paths,
                evidence_receipts=receipts,
                candidate_ap=artifact,
                rollback_ap={**artifact, "sha256": "b" * 64},
                target_profile=ROOT / builder.DEFAULT_TARGET_PROFILE,
                manifest_id=builder.DEFAULT_MANIFEST_ID,
                live_run_id=builder.DEFAULT_LIVE_RUN_ID,
                timeout_sec=builder.DEFAULT_TIMEOUT_SEC,
            )


if __name__ == "__main__":
    unittest.main()
