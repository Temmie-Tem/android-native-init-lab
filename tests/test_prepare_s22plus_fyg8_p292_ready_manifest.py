#!/usr/bin/env python3
"""Focused tests for the P2.92 Process-v2 ready-manifest builder."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPT_DIR))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as core  # noqa: E402
import prepare_s22plus_fyg8_p292_ready_manifest as builder  # noqa: E402
import s22plus_fyg8_p292_repair_decoder as decoder  # noqa: E402
import s22plus_fyg8_p292_repair_model as model  # noqa: E402


class P292ReadyManifestBuilderTest(unittest.TestCase):
    def fixture(self):
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

    def test_derives_exact_p292_acceptance_and_observer(self) -> None:
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
        self.assertEqual(
            acceptance["terminal_stage"],
            evidence._latest_stage_terminal(decoder, "E2"),
        )
        evidence.validate_acceptance(acceptance)
        core.verify_candidate_observer_binding(
            acceptance, manifest["observation"]["candidate_observer"]
        )

    def test_rejects_wrong_source_contract(self) -> None:
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

    def test_defaults_are_p292_scoped_and_no_live_transport(self) -> None:
        args = builder.parse_args([])
        self.assertEqual(args.out, builder.DEFAULT_OUT)
        self.assertEqual(args.timeout_sec, 300)
        self.assertFalse(args.verify_only)
        self.assertTrue(builder.parse_args(["--verify-only"]).verify_only)
        source = (SCRIPT_DIR / "prepare_s22plus_fyg8_p292_ready_manifest.py").read_text()
        for forbidden in ("device_action_f1_live_v2", "subprocess", "adb ", "Odin4"):
            self.assertNotIn(forbidden, source)

    def test_verify_only_runs_full_bundle_check_without_creating_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "manifests"
            canonical.mkdir()
            output = canonical / "candidate.json"
            seen = []
            with mock.patch.object(
                builder.core,
                "verify_bundle",
                side_effect=lambda _root, proposal: seen.append(proposal.read_bytes()),
            ) as verify:
                created = builder.verify_and_finalize(
                    root=root,
                    output=output,
                    canonical_directory=canonical,
                    payload=b"proposal\n",
                    verify_only=True,
                )
            self.assertFalse(created)
            self.assertFalse(output.exists())
            verify.assert_called_once()
            self.assertEqual(seen, [b"proposal\n"])

    def test_verify_only_rejects_preexisting_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "manifests"
            canonical.mkdir()
            output = canonical / "candidate.json"
            output.write_bytes(b"old\n")
            with self.assertRaisesRegex(builder.ManifestError, "already exists"):
                builder.verify_and_finalize(
                    root=root,
                    output=output,
                    canonical_directory=canonical,
                    payload=b"proposal\n",
                    verify_only=True,
                )

    def test_manifest_creation_is_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            builder.durable_create(path, b"first\n")
            self.assertEqual(path.read_bytes(), b"first\n")
            with self.assertRaises(FileExistsError):
                builder.durable_create(path, b"second\n")
            self.assertEqual(path.read_bytes(), b"first\n")


if __name__ == "__main__":
    unittest.main()
