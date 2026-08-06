#!/usr/bin/env python3
"""Focused tests for P3.08 Process-v2 and retained-record binding."""

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
import prepare_s22plus_fyg8_p308_process_v2 as adapter  # noqa: E402
import prepare_s22plus_fyg8_p308_ready_manifest as ready  # noqa: E402
import s22plus_fyg8_p301_overlay_contract as p301_overlay  # noqa: E402
import s22plus_fyg8_p303_overlay_contract as p303_overlay  # noqa: E402
import s22plus_fyg8_p304_overlay_contract as p304_overlay  # noqa: E402
import s22plus_fyg8_p305_overlay_contract as p305_overlay  # noqa: E402
import s22plus_fyg8_p307_overlay_contract as p307_overlay  # noqa: E402
import s22plus_fyg8_p308_overlay_contract as overlay  # noqa: E402
import s22plus_fyg8_p308_telemetry_decoder as decoder  # noqa: E402
import s22plus_fyg8_p308_telemetry_model as model  # noqa: E402
import s22plus_fyg8_p308_telemetry_spec as spec  # noqa: E402


class P308ProcessV2OverlayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = overlay.verify_intent(ROOT, ROOT / overlay.DEFAULT_INTENT)
        cls.run_id = bytes.fromhex(cls.contract["run_id"])

    def acceptance(self) -> dict[str, object]:
        artifact = {"path": "fixture", "size": 1, "sha256": "0" * 64}
        return {
            "kind": evidence.E1_LATEST_STAGE_KIND,
            "source": evidence.CHECKPOINT_SOURCE,
            "decoder": decoder.DECODER_ID,
            "policy_id": decoder.POLICY_ID,
            "profile": overlay.PROFILE,
            "run_id": self.contract["run_id"],
            "source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": overlay.CONTRACT_ID,
            "long_family_hex": model.LONG_FAMILY.hex(),
            "unsat_family_hex": model.UNSAT_FAMILY.hex(),
            "terminal_stage": evidence._latest_stage_terminal(  # noqa: SLF001
                decoder, overlay.PROFILE
            ),
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "contract": {
                "candidate_static": artifact,
                "run_manifest": artifact,
                "static_check": artifact,
            },
        }

    def _record(self, first: int, terminal: int) -> bytes:
        record = model.initialize_record(overlay.PROFILE, self.run_id)
        for generation, position in enumerate(spec.POSITIONS, 1):
            if generation == spec.ATTR_ORDINAL + 1:
                outcome, detail = spec.OUTCOME_PROGRESS, first
            elif generation == spec.SUMMARY_ORDINAL + 1:
                outcome, detail = spec.OUTCOME_FAILURE, terminal
            else:
                outcome, detail = model.OUTCOME_PROGRESS, 0
            record = model.apply_request(
                record,
                model.encode_request(
                    overlay.PROFILE,
                    position.stage,
                    run_id=self.run_id,
                    outcome=outcome,
                    item_index=position.item_index,
                    detail=detail,
                ),
            )
            if generation == spec.SUMMARY_ORDINAL + 1:
                break
        return record

    def test_decoder_selection_and_defaults_are_p308_bound(self) -> None:
        self.assertIs(
            evidence._latest_stage_observation_decoder(  # noqa: SLF001
                overlay.PARENT_SOURCE_CONTRACT_ID,
                overlay.PROFILE,
                overlay.CONTRACT_ID,
            ),
            decoder,
        )
        args = adapter.parse_args([])
        ready_args = ready.parse_args([])
        self.assertTrue(
            all(
                "s22plus_fyg8_p308" in value.as_posix()
                for value in (args.candidate_static, args.candidate_ap, args.out)
            )
        )
        self.assertTrue(
            all(
                "s22plus_fyg8_p308" in value.as_posix()
                for value in (
                    ready_args.candidate_static,
                    ready_args.run_manifest,
                    ready_args.static_check,
                    ready_args.candidate_ap,
                    ready_args.out,
                )
            )
        )

    def test_execution_receipts_bind_exact_overlay_lineage(self) -> None:
        minimal = {
            "kind": evidence.E1_LATEST_STAGE_KIND,
            "profile": overlay.PROFILE,
            "source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": overlay.CONTRACT_ID,
        }
        receipts = process_v2.execution_critical_source_receipts(minimal)
        expected = (
            ("p301", p301_overlay),
            ("p303", p303_overlay),
            ("p304", p304_overlay),
            ("p305", p305_overlay),
            ("p307", p307_overlay),
            ("p308", overlay),
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

    def test_execution_binding_rejects_p308_source_drift(self) -> None:
        p307_contract = self.contract["parent_overlay_contract"]
        p305_contract = p307_contract["parent_overlay_contract"]
        p304_contract = p305_contract["parent_overlay_contract"]
        p303_contract = p304_contract["parent_overlay_contract"]
        verification = {
            "source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": overlay.CONTRACT_ID,
            "candidate_source_receipts": evidence.validate_candidate_source_preimage(
                self.contract["parent_candidate_contract"],
                overlay.PROFILE,
                self.contract["run_id"],
            ),
            "p301_overlay_source_receipts": p303_contract[
                "parent_overlay_contract"
            ]["source_receipts"],
            "p303_overlay_source_receipts": p303_contract["source_receipts"],
            "p304_overlay_source_receipts": p304_contract["source_receipts"],
            "p305_overlay_source_receipts": p305_contract["source_receipts"],
            "p307_overlay_source_receipts": p307_contract["source_receipts"],
            "p308_overlay_source_receipts": self.contract["source_receipts"],
        }
        minimal = {
            "kind": evidence.E1_LATEST_STAGE_KIND,
            "profile": overlay.PROFILE,
            "source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": overlay.CONTRACT_ID,
        }
        execution = process_v2.execution_critical_source_receipts(minimal)
        process_v2.verify_candidate_source_binding(minimal, verification, execution)
        changed = copy.deepcopy(execution)
        first = sorted(overlay.SOURCE_KEYS)[0]
        changed[f"p308_overlay_source_{first}"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(process_v2.F1V2Error, "overlay source differs"):
            process_v2.verify_candidate_source_binding(
                minimal, verification, changed
            )

    def test_normal_retained_record_round_trips_through_evidence_adapter(self) -> None:
        classified = evidence.classify_e1_latest_stage(
            self._record(0xD00, 0x4FC1), self.acceptance()
        )
        self.assertTrue(classified["accepted"])
        self.assertEqual(classified["telemetry_count"], 1)
        self.assertEqual(classified["foreign_count"], 0)
        self.assertEqual(classified["records"][0]["p308_pair"]["kind"], "normal")

    def test_degraded_retained_record_survives_as_evidence_bearing_failure(self) -> None:
        classified = evidence.classify_e1_latest_stage(
            self._record(0xD00, 0x6100), self.acceptance()
        )
        self.assertFalse(classified["accepted"])
        self.assertEqual(classified["degraded_count"], 1)
        self.assertEqual(classified["contradiction_count"], 1)
        self.assertEqual(classified["foreign_count"], 0)
        pair = classified["records"][0]["p308_pair"]
        self.assertEqual(pair["kind"], "degraded")
        self.assertTrue(pair["evidence_bearing_observer_contradiction"])

    def test_materialized_process_output_is_p308_bound(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
