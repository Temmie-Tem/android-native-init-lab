#!/usr/bin/env python3
"""Focused tests for the P3.01 Process-v2 userspace overlay binding."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPT_DIR))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as process_v2  # noqa: E402
import prepare_s22plus_fyg8_p301_process_v2 as adapter  # noqa: E402
import prepare_s22plus_fyg8_p301_ready_manifest as ready  # noqa: E402
import s22plus_fyg8_p300_telemetry_decoder as p300_decoder  # noqa: E402
import s22plus_fyg8_p301_candidate_static_checker as checker  # noqa: E402
import s22plus_fyg8_p301_overlay_contract as overlay  # noqa: E402
import s22plus_fyg8_p301_telemetry_decoder as p301_decoder  # noqa: E402


class P301ProcessV2OverlayTest(unittest.TestCase):
    def acceptance(self) -> dict[str, str]:
        return {
            "kind": evidence.E1_LATEST_STAGE_KIND,
            "profile": overlay.PROFILE,
            "source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": overlay.CONTRACT_ID,
        }

    def test_decoder_selection_is_overlay_opt_in(self) -> None:
        inherited = evidence._latest_stage_observation_decoder(
            overlay.PARENT_SOURCE_CONTRACT_ID,
            overlay.PROFILE,
        )
        selected = evidence._latest_stage_observation_decoder(
            overlay.PARENT_SOURCE_CONTRACT_ID,
            overlay.PROFILE,
            overlay.CONTRACT_ID,
        )
        self.assertIs(inherited, p300_decoder)
        self.assertIs(selected, p301_decoder)
        with self.assertRaisesRegex(evidence.EvidenceError, "unsupported"):
            evidence._latest_stage_observation_decoder(
                None,
                overlay.PROFILE,
                overlay.CONTRACT_ID,
            )

    def test_defaults_and_promoted_evidence_are_p301_bound(self) -> None:
        args = adapter.parse_args([])
        ready_args = ready.parse_args([])
        self.assertTrue(
            all(
                "s22plus_fyg8_p301" in value.as_posix()
                for value in (args.candidate_static, args.candidate_ap, args.out)
            )
        )
        self.assertTrue(
            all(
                "s22plus_fyg8_p301" in value.as_posix()
                for value in (
                    ready_args.candidate_static,
                    ready_args.run_manifest,
                    ready_args.static_check,
                    ready_args.candidate_ap,
                    ready_args.out,
                )
            )
        )
        output = ROOT / adapter.DEFAULT_OUT
        run_manifest = json.loads((output / "run-manifest.json").read_text())
        static_result = json.loads((output / "static-check-result.json").read_text())
        for value in (run_manifest, static_result):
            self.assertEqual(
                value["userspace_overlay_contract_id"], overlay.CONTRACT_ID
            )
            self.assertEqual(value["source_contract_id"], overlay.PARENT_SOURCE_CONTRACT_ID)
            self.assertEqual(value["decoder"], p301_decoder.DECODER_ID)
            self.assertEqual(value["policy_id"], p301_decoder.POLICY_ID)

    def test_execution_receipts_bind_all_nine_overlay_sources(self) -> None:
        receipts = process_v2.execution_critical_source_receipts(self.acceptance())
        overlay_receipts = {
            name: value
            for name, value in receipts.items()
            if name.startswith("p301_overlay_source_")
        }
        self.assertEqual(len(overlay_receipts), len(overlay.SOURCE_KEYS))
        self.assertIn("p301_overlay_intent", receipts)

    def test_promotion_context_restores_inherited_modules(self) -> None:
        before = adapter._snapshot_indirect_modules()
        adapter.parse_args([])
        after = adapter._snapshot_indirect_modules()
        self.assertEqual(set(after), set(before))
        for module, values in before.items():
            self.assertEqual(set(after[module]), set(values))
            self.assertTrue(
                all(after[module][name] is value for name, value in values.items())
            )

    def test_execution_binding_rejects_overlay_source_drift(self) -> None:
        contract = overlay.verify_intent(ROOT, ROOT / overlay.DEFAULT_INTENT)
        verification = {
            "source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": overlay.CONTRACT_ID,
            "candidate_source_receipts": evidence.validate_candidate_source_preimage(
                contract["parent_candidate_contract"],
                overlay.PROFILE,
                contract["run_id"],
            ),
            "p301_overlay_source_receipts": contract["source_receipts"],
        }
        execution = process_v2.execution_critical_source_receipts(self.acceptance())
        process_v2.verify_candidate_source_binding(
            self.acceptance(), verification, execution
        )
        changed = copy.deepcopy(execution)
        first = sorted(overlay.SOURCE_KEYS)[0]
        changed[f"p301_overlay_source_{first}"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(process_v2.F1V2Error, "overlay source differs"):
            process_v2.verify_candidate_source_binding(
                self.acceptance(), verification, changed
            )

    def test_static_checker_pins_frozen_parent_result_and_build_paths(self) -> None:
        contract = overlay.verify_intent(ROOT, ROOT / overlay.DEFAULT_INTENT)
        exact_args = SimpleNamespace(
            repro_result=overlay.PARENT_REPRO_RESULT,
            build_a=checker.DEFAULT_BUILD_A,
            build_b=checker.DEFAULT_BUILD_A,
            nm=checker.DEFAULT_NM,
            objdump=checker.DEFAULT_OBJDUMP,
        )
        with self.assertRaisesRegex(checker.CheckError, "build B path differs"):
            checker.verify_repro(ROOT, exact_args, contract)

        parent = ROOT / overlay.PARENT_REPRO_RESULT
        with tempfile.TemporaryDirectory(prefix="s22-p301-result-negative-") as name:
            replacement = Path(name) / "postbuild-repro-check-fresh.json"
            replacement.write_bytes(parent.read_bytes())
            exact_args.repro_result = replacement
            exact_args.build_b = checker.DEFAULT_BUILD_B
            with self.assertRaisesRegex(
                checker.CheckError, "reproducibility result path differs"
            ):
                checker.verify_repro(ROOT, exact_args, contract)

    def test_static_checker_rejects_changed_pinned_parent_result_bytes(self) -> None:
        contract = overlay.verify_intent(ROOT, ROOT / overlay.DEFAULT_INTENT)
        parent = ROOT / overlay.PARENT_REPRO_RESULT
        with tempfile.TemporaryDirectory(prefix="s22-p301-result-tamper-") as name:
            replacement = Path(name) / "postbuild-repro-check-fresh.json"
            replacement.write_bytes(parent.read_bytes() + b" ")
            args = SimpleNamespace(
                repro_result=replacement,
                build_a=checker.DEFAULT_BUILD_A,
                build_b=checker.DEFAULT_BUILD_B,
                nm=checker.DEFAULT_NM,
                objdump=checker.DEFAULT_OBJDUMP,
            )
            with mock.patch.object(
                checker.overlay, "PARENT_REPRO_RESULT", replacement
            ):
                with self.assertRaisesRegex(
                    checker.CheckError, "reproducibility result bytes differ"
                ):
                    checker.verify_repro(ROOT, args, contract)

    def test_static_checker_rejects_shared_parent_artifact_inode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s22-p301-inode-negative-") as name:
            build_a = Path(name) / "a"
            build_b = Path(name) / "b"
            build_a.mkdir()
            build_b.mkdir()
            artifact_a = build_a / "Image"
            artifact_b = build_b / "Image"
            artifact_a.write_bytes(b"fixed-image")
            artifact_b.hardlink_to(artifact_a)
            with self.assertRaisesRegex(checker.CheckError, "share one inode"):
                checker._require_distinct_artifact_inodes(  # noqa: SLF001
                    {"build_a": build_a, "build_b": build_b}, {"Image"}
                )

    def test_static_checker_parent_qualification_receipt_is_exact(self) -> None:
        payload = (ROOT / checker.PARENT_QUALIFICATION).read_bytes()
        self.assertEqual(
            checker.base.receipt(payload), checker.PARENT_QUALIFICATION_RECEIPT
        )


if __name__ == "__main__":
    unittest.main()
