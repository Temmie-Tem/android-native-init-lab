#!/usr/bin/env python3
"""Focused tests for the P3.07 Process-v2 source and decoder binding."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPT_DIR))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as process_v2  # noqa: E402
import prepare_s22plus_fyg8_p307_process_v2 as adapter  # noqa: E402
import prepare_s22plus_fyg8_p307_ready_manifest as ready  # noqa: E402
import s22plus_fyg8_p301_overlay_contract as p301_overlay  # noqa: E402
import s22plus_fyg8_p303_overlay_contract as p303_overlay  # noqa: E402
import s22plus_fyg8_p304_overlay_contract as p304_overlay  # noqa: E402
import s22plus_fyg8_p305_overlay_contract as p305_overlay  # noqa: E402
import s22plus_fyg8_p307_overlay_contract as overlay  # noqa: E402
import s22plus_fyg8_p307_telemetry_decoder as decoder  # noqa: E402
import s22plus_fyg8_p307_telemetry_spec as spec  # noqa: E402


class P307ProcessV2OverlayTest(unittest.TestCase):
    def acceptance(self) -> dict[str, str]:
        return {
            "kind": evidence.E1_LATEST_STAGE_KIND,
            "profile": overlay.PROFILE,
            "source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": overlay.CONTRACT_ID,
        }

    def test_decoder_selection_and_deep_terminal_inheritance(self) -> None:
        selected = evidence._latest_stage_observation_decoder(  # noqa: SLF001
            overlay.PARENT_SOURCE_CONTRACT_ID,
            overlay.PROFILE,
            overlay.CONTRACT_ID,
        )
        self.assertIs(selected, decoder)
        self.assertEqual(
            evidence._latest_stage_terminal(selected, overlay.PROFILE),  # noqa: SLF001
            decoder.inherited.inherited.TERMINAL_POSITION[0],
        )

    def test_defaults_and_promoted_evidence_are_p307_bound(self) -> None:
        args = adapter.parse_args([])
        ready_args = ready.parse_args([])
        self.assertTrue(
            all(
                "s22plus_fyg8_p307" in value.as_posix()
                for value in (args.candidate_static, args.candidate_ap, args.out)
            )
        )
        self.assertTrue(
            all(
                "s22plus_fyg8_p307" in value.as_posix()
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
        for name in ("run-manifest.json", "static-check-result.json"):
            value = json.loads((output / name).read_text(encoding="ascii"))
            self.assertEqual(
                value["userspace_overlay_contract_id"], overlay.CONTRACT_ID
            )
            self.assertEqual(
                value["source_contract_id"], overlay.PARENT_SOURCE_CONTRACT_ID
            )
            self.assertEqual(value["decoder"], decoder.DECODER_ID)
            self.assertEqual(value["policy_id"], decoder.POLICY_ID)

    def test_execution_receipts_bind_exact_overlay_lineage(self) -> None:
        receipts = process_v2.execution_critical_source_receipts(self.acceptance())
        expected = (
            ("p301", p301_overlay),
            ("p303", p303_overlay),
            ("p304", p304_overlay),
            ("p305", p305_overlay),
            ("p307", overlay),
        )
        for prefix, module in expected:
            selected = {
                name: value
                for name, value in receipts.items()
                if name.startswith(f"{prefix}_overlay_source_")
            }
            self.assertEqual(len(selected), len(module.SOURCE_KEYS))
            self.assertIn(f"{prefix}_overlay_intent", receipts)
        self.assertNotIn("p306_overlay_intent", receipts)
        self.assertNotIn("p303_stock_baseline_binding", receipts)

    def test_execution_binding_rejects_any_overlay_source_drift(self) -> None:
        contract = overlay.verify_intent(ROOT, ROOT / overlay.DEFAULT_INTENT)
        p305_contract = contract["parent_overlay_contract"]
        p304_contract = p305_contract["parent_overlay_contract"]
        p303_contract = p304_contract["parent_overlay_contract"]
        verification = {
            "source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": overlay.CONTRACT_ID,
            "candidate_source_receipts": evidence.validate_candidate_source_preimage(
                contract["parent_candidate_contract"],
                overlay.PROFILE,
                contract["run_id"],
            ),
            "p301_overlay_source_receipts": p303_contract[
                "parent_overlay_contract"
            ]["source_receipts"],
            "p303_overlay_source_receipts": p303_contract["source_receipts"],
            "p304_overlay_source_receipts": p304_contract["source_receipts"],
            "p305_overlay_source_receipts": p305_contract["source_receipts"],
            "p307_overlay_source_receipts": contract["source_receipts"],
        }
        execution = process_v2.execution_critical_source_receipts(self.acceptance())
        process_v2.verify_candidate_source_binding(
            self.acceptance(), verification, execution
        )
        changed = copy.deepcopy(execution)
        first = sorted(overlay.SOURCE_KEYS)[0]
        changed[f"p307_overlay_source_{first}"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(process_v2.F1V2Error, "overlay source differs"):
            process_v2.verify_candidate_source_binding(
                self.acceptance(), verification, changed
            )

    def test_static_result_binds_eud_path_and_qscratch_callsite(self) -> None:
        result = json.loads(
            (ROOT / adapter.DEFAULT_STATIC).read_text(encoding="ascii")
        )
        observer = result["p307_observer"]
        self.assertEqual(observer["eud_cache_path"], spec.EUD_CACHE_PATH)
        self.assertEqual(observer["eud_cache_read_count"], 1)
        self.assertTrue(observer["read_only"])
        self.assertEqual(result["p303_callsite_audit"]["callsite_count"], 12)
        self.assertEqual(
            result["p307_qscratch_audit"]["probe"]["offset"],
            spec.QSCRATCH_PROBE_OFFSET,
        )
        self.assertTrue(result["p307_qscratch_audit"]["verified"])


if __name__ == "__main__":
    unittest.main()
