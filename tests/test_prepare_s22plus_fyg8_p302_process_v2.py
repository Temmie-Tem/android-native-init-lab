#!/usr/bin/env python3
"""Focused tests for the P3.02-M0 Process-v2 source binding."""

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
import prepare_s22plus_fyg8_p301_process_v2 as p301_adapter  # noqa: E402
import prepare_s22plus_fyg8_p302_process_v2 as adapter  # noqa: E402
import prepare_s22plus_fyg8_p302_ready_manifest as ready  # noqa: E402
import s22plus_fyg8_p301_overlay_contract as parent_overlay  # noqa: E402
import s22plus_fyg8_p301_telemetry_decoder as p301_decoder  # noqa: E402
import s22plus_fyg8_p302_binary_carrier as carrier  # noqa: E402
import s22plus_fyg8_p302_overlay_contract as overlay  # noqa: E402


class P302ProcessV2OverlayTest(unittest.TestCase):
    def acceptance(self) -> dict[str, str]:
        return {
            "kind": evidence.E1_LATEST_STAGE_KIND,
            "profile": overlay.PROFILE,
            "source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": overlay.CONTRACT_ID,
        }

    def test_decoder_selection_reuses_exact_p301_policy(self) -> None:
        selected = evidence._latest_stage_observation_decoder(
            overlay.PARENT_SOURCE_CONTRACT_ID,
            overlay.PROFILE,
            overlay.CONTRACT_ID,
        )
        self.assertIs(selected, p301_decoder)

    def test_defaults_and_promoted_evidence_are_p302_bound(self) -> None:
        args = adapter.parse_args([])
        ready_args = ready.parse_args([])
        self.assertTrue(
            all(
                "s22plus_fyg8_p302" in value.as_posix()
                for value in (args.candidate_static, args.candidate_ap, args.out)
            )
        )
        self.assertTrue(
            all(
                "s22plus_fyg8_p302" in value.as_posix()
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
            self.assertEqual(
                value["source_contract_id"], overlay.PARENT_SOURCE_CONTRACT_ID
            )
            self.assertEqual(value["decoder"], p301_decoder.DECODER_ID)
            self.assertEqual(value["policy_id"], p301_decoder.POLICY_ID)

    def test_execution_receipts_bind_parent_and_carrier_sources(self) -> None:
        receipts = process_v2.execution_critical_source_receipts(self.acceptance())
        p301 = {
            name: value
            for name, value in receipts.items()
            if name.startswith("p301_overlay_source_")
        }
        p302 = {
            name: value
            for name, value in receipts.items()
            if name.startswith("p302_overlay_source_")
        }
        self.assertEqual(len(p301), len(parent_overlay.SOURCE_KEYS))
        self.assertEqual(len(p302), len(overlay.SOURCE_KEYS))
        self.assertIn("p301_overlay_intent", receipts)
        self.assertIn("p302_overlay_intent", receipts)

    def test_execution_binding_rejects_parent_or_carrier_source_drift(self) -> None:
        contract = overlay.verify_intent(ROOT, ROOT / overlay.DEFAULT_INTENT)
        verification = {
            "source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": overlay.CONTRACT_ID,
            "candidate_source_receipts": evidence.validate_candidate_source_preimage(
                contract["parent_candidate_contract"],
                overlay.PROFILE,
                contract["run_id"],
            ),
            "p301_overlay_source_receipts": contract["parent_overlay_contract"][
                "source_receipts"
            ],
            "p302_overlay_source_receipts": contract["source_receipts"],
        }
        execution = process_v2.execution_critical_source_receipts(self.acceptance())
        process_v2.verify_candidate_source_binding(
            self.acceptance(), verification, execution
        )
        for prefix, keys in (
            ("p301", parent_overlay.SOURCE_KEYS),
            ("p302", overlay.SOURCE_KEYS),
        ):
            changed = copy.deepcopy(execution)
            first = sorted(keys)[0]
            changed[f"{prefix}_overlay_source_{first}"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(
                process_v2.F1V2Error, "overlay source differs"
            ):
                process_v2.verify_candidate_source_binding(
                    self.acceptance(), verification, changed
                )

    def test_static_result_proves_nonalloc_carrier_only(self) -> None:
        result = json.loads(
            (ROOT / adapter.DEFAULT_STATIC).read_text(encoding="ascii")
        )
        identity = result["carrier_identity"]
        self.assertEqual(identity["carrier_id"], carrier.CARRIER_ID)
        self.assertEqual(identity["section"], carrier.SECTION)
        self.assertFalse(identity["section_allocatable"])
        self.assertEqual(
            identity["alloc_sections_byte_identical"], list(carrier.ALLOC_SECTIONS)
        )
        self.assertTrue(identity["elf_header_execution_fields_identical"])
        self.assertTrue(identity["program_headers_byte_identical"])
        self.assertTrue(
            identity["program_segment_bytes_identical_except_section_table_fields"]
        )
        self.assertTrue(
            identity[
                "file_prefix_and_padding_identical_except_section_table_fields"
            ]
        )
        self.assertTrue(identity["identity_section_exact"])
        self.assertFalse(identity["identity_in_program_segment"])
        self.assertFalse(identity["kernel_rebuilt"])
        self.assertEqual(identity["module_binaries_injected"], 0)

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

    def test_p302_then_actual_p301_r1_validation_has_no_global_leak(self) -> None:
        adapter.parse_args([])
        static_path = (
            ROOT
            / "workspace/private/outputs/s22plus_fyg8_p301_r1/"
            "static-check-result.json"
        )
        ap_path = (
            ROOT
            / "workspace/private/outputs/s22plus_fyg8_p301_r1/"
            "candidate-a/odin4/AP.tar.md5"
        )
        static_payload = static_path.read_bytes()
        static_result = json.loads(static_payload.decode("ascii"))
        ap_payload = ap_path.read_bytes()
        ap_info, frame = p301_adapter.boot_verify.parse_ap_tar_md5(ap_payload)
        self.assertEqual(ap_info["member"]["name"], "boot.img.lz4")
        candidate_contract, identities = p301_adapter.validate_static(
            static_result,
            p301_adapter.receipt(static_payload),
            {
                **p301_adapter.receipt(ap_payload),
                "member": {
                    "name": "boot.img.lz4",
                    **p301_adapter.receipt(frame),
                },
            },
        )
        self.assertEqual(
            candidate_contract["userspace_overlay_contract_id"],
            parent_overlay.CONTRACT_ID,
        )
        self.assertEqual(
            identities["init"]["sha256"],
            "17eae28ae1e8fa0abcd47b05c3b57cfa5c54124db0192137b208a3f85978ee35",
        )


if __name__ == "__main__":
    unittest.main()
