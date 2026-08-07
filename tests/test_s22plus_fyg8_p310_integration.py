#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_live_v2 as live  # noqa: E402
import device_action_f1_v2 as process  # noqa: E402
import prepare_s22plus_fyg8_p310_process_v2 as process_adapter  # noqa: E402
import prepare_s22plus_fyg8_p310_ready_manifest as ready_manifest  # noqa: E402
import s22plus_fyg8_p308_telemetry_spec as spec  # noqa: E402
import s22plus_fyg8_p309_generator as p309_generator  # noqa: E402
import s22plus_fyg8_p310_candidate_contract as candidate_contract  # noqa: E402
import s22plus_fyg8_p310_candidate_intent as intent  # noqa: E402
import s22plus_fyg8_p310_build as kernel_build  # noqa: E402
import s22plus_fyg8_p310_e2_stock_closure as stock_closure  # noqa: E402
import s22plus_fyg8_p310_carrier_model as carrier  # noqa: E402
import s22plus_fyg8_p310_generator as generator  # noqa: E402
import s22plus_fyg8_p310_identity_tiers as identity  # noqa: E402
import s22plus_fyg8_p310_postbuild_linked_audit as postbuild  # noqa: E402
import s22plus_fyg8_p310_pre_lto_qualification as qualification  # noqa: E402
import s22plus_fyg8_p310_source_contract as source  # noqa: E402


class P310IntegrationTests(unittest.TestCase):
    def test_postbuild_host_validator_accepts_parent_pre_and_post_configure_shapes(self) -> None:
        patch = generator.generate_bytes(
            ROOT,
            run_id=source.SOURCE_CHECK_RUN_ID,
            unsat_tag=source.SOURCE_CHECK_UNSAT_TAG,
            profile=source.PROFILE,
        )["candidate_patch"]
        previous = postbuild.base.p290
        try:
            for active_contract in (postbuild.parent.p300, source):
                postbuild.base.p290 = active_contract
                translation_unit = postbuild.host_validator_tu(patch)
                self.assertEqual(
                    translation_unit.count(b"#define S22_FYG8_E1_HEADER_SIZE 32\n"),
                    1,
                )
                self.assertNotIn(
                    b"#define S22_FYG8_E1_HEADER_SIZE 25\n",
                    translation_unit,
                )
                self.assertEqual(
                    translation_unit.count(b"#define S22_FYG8_E1_HEADER_SIZE "),
                    1,
                )
                self.assertEqual(
                    translation_unit.count(
                        b"#define S22_FYG8_E1_SLOT_PAYLOAD_SIZE 67\n"
                    ),
                    1,
                )
                self.assertEqual(
                    translation_unit.count(
                        b"#define S22_FYG8_E1_REQUEST_PAYLOAD_SIZE 64\n"
                    ),
                    1,
                )
                self.assertEqual(
                    translation_unit.count(
                        b"#define S22_FYG8_E1_SLOT_PAYLOAD_SIZE "
                    ),
                    1,
                )
                self.assertEqual(
                    translation_unit.count(
                        b"#define S22_FYG8_E1_REQUEST_PAYLOAD_SIZE "
                    ),
                    1,
                )
        finally:
            postbuild.base.p290 = previous

    def test_postbuild_host_validator_rejects_conflicting_carrier_defines(self) -> None:
        invalid_sources = (
            (
                b"#define S22_FYG8_E1_HEADER_SIZE 25\n"
                b"#define S22_FYG8_E1_HEADER_SIZE 32\n"
            ),
            (
                b"#define S22_FYG8_E1_HEADER_SIZE 25\n"
                b"#define S22_FYG8_E1_HEADER_SIZE 32\n"
                b"#define S22_FYG8_E1_HEADER_SIZE 32\n"
            ),
            b"#define S22_FYG8_E1_HEADER_SIZE 31\n",
            (
                b"#define S22_FYG8_E1_HEADER_SIZE 25\n"
                b"#define S22_FYG8_E1_SLOT_PAYLOAD_SIZE 67\n"
            ),
            (
                b"#define S22_FYG8_E1_HEADER_SIZE 32\n"
                b"#define S22_FYG8_E1_REQUEST_PAYLOAD_SIZE 64\n"
            ),
        )
        for invalid_source in invalid_sources:
            with self.subTest(invalid_source=invalid_source):
                with mock.patch.object(
                    postbuild.parent,
                    "host_validator_tu",
                    return_value=invalid_source,
                ):
                    with self.assertRaises(postbuild.AuditError):
                        postbuild.host_validator_tu(b"unused")

    def test_source_contract_delegates_linked_table_audit(self) -> None:
        expected = source.linked_table_bytes()
        result = source.audit_linked_tables(expected)
        self.assertTrue(result["verified"])

        corrupted = dict(expected)
        name = next(iter(corrupted))
        corrupted[name] = corrupted[name] + b"\x00"
        with self.assertRaises(source.SourceContractError):
            source.audit_linked_tables(corrupted)

    def test_stock_closure_carries_current_runtime_delta(self) -> None:
        self.assertEqual(
            stock_closure.ADDITIONAL_ABSOLUTE_PATH_STRINGS,
            {"/dev/kmsg", "/sys/module/eud/parameters/enable"},
        )
        self.assertEqual(stock_closure.module_parent.EXPECTED_MODULE_COUNT, 61)
        self.assertIs(
            stock_closure.rootfs_audit,
            stock_closure.module_parent.rootfs_audit,
        )
        self.assertEqual(stock_closure.INCIDENTAL_INIT_SIZE, 66416)
        self.assertEqual(stock_closure.INCIDENTAL_PATH_OFFSET, 0x41C1)
        self.assertEqual(stock_closure.INCIDENTAL_TEXT_OFFSET, 0x120)
        self.assertEqual(stock_closure.INCIDENTAL_TEXT_END, 0x8FB0)
        self.assertEqual(
            stock_closure.INCIDENTAL_INSTRUCTION_WINDOW,
            bytes.fromhex("e02f453922000090"),
        )

    def test_transitive_decoder_semantics_are_bound_and_drift_changes_identity(self) -> None:
        materials = identity.tier1_materials(ROOT)
        semantic_keys = set(identity.SEMANTIC_DEPENDENCY_PATHS)
        self.assertTrue(semantic_keys)
        self.assertTrue(semantic_keys <= set(materials))
        self.assertIn(
            "p310_semantic__s22plus_fyg8_p308_telemetry_decoder",
            semantic_keys,
        )
        before = identity.payload_identity(materials)
        changed = dict(materials)
        key = sorted(semantic_keys)[0]
        changed[key] += b"\n# semantic-drift-negative-test\n"
        self.assertNotEqual(identity.payload_identity(changed), before)

        receipts = process.execution_critical_source_receipts(
            {
                "kind": evidence.E1_LATEST_STAGE_KIND,
                "profile": source.PROFILE,
                "source_contract_id": source.CONTRACT_ID,
                "decoder": source.decoder.DECODER_ID,
                "policy_id": source.decoder.POLICY_ID,
            }
        )
        self.assertEqual(
            {
                f"candidate_source_{semantic_key}"
                for semantic_key in semantic_keys
            }
            & set(receipts),
            {
                f"candidate_source_{semantic_key}"
                for semantic_key in semantic_keys
            },
        )

    def test_reachable_count_is_the_unique_encoder_output_count(self) -> None:
        result = source.validate_reachable_records(bytes.fromhex("43" * 16))
        self.assertEqual(source.TELEMETRY_REACHABLE_VARIANTS, 5838)
        self.assertEqual(result["checked"], source.TELEMETRY_REACHABLE_VARIANTS)
        self.assertEqual(
            source.P310.reachable_variants,
            source.inherited.REACHABLE_VARIANTS + result["checked"],
        )
        self.assertEqual(source.MODULE_PLAN_COUNT, 61)

    def test_pre_lto_reuses_exact_sealed_p300_linked_capability(self) -> None:
        known_good = qualification._inherited_known_good_linked_binding(ROOT)  # noqa: SLF001
        self.assertEqual(
            known_good["linked_adapter"],
            "s22plus-fyg8-p280-linked-audit-v1",
        )
        self.assertTrue(known_good["verified"])

    def test_kernel_output_gate_is_bound_to_carrier_v2_families(self) -> None:
        kernel_build._configure()  # noqa: SLF001
        self.assertEqual(kernel_build.base.LONG_FAMILY, carrier.LONG_FAMILY)
        self.assertEqual(kernel_build.base.UNSAT_FAMILY, carrier.UNSAT_FAMILY)

    def test_pre_lto_private_stock_closure_entrypoints_are_explicit(self) -> None:
        self.assertIs(stock_closure._entrypoints, stock_closure.parent._entrypoints)  # noqa: SLF001
        self.assertIs(
            stock_closure._validate_p282_authority_strings,  # noqa: SLF001
            stock_closure._validate_p310_authority_strings,  # noqa: SLF001
        )
        self.assertIsNot(
            stock_closure._validate_p282_authority_strings,  # noqa: SLF001
            stock_closure.parent._validate_p282_authority_strings,  # noqa: SLF001
        )

    def test_generated_delta_is_carrier_only_and_keeps_corrected_descriptor(self) -> None:
        baseline = p309_generator.generate_bytes(
            ROOT,
            run_id=source.SOURCE_CHECK_RUN_ID,
            unsat_tag=source.SOURCE_CHECK_UNSAT_TAG,
            profile=source.PROFILE,
        )
        generated = generator.generate_bytes(
            ROOT,
            run_id=source.SOURCE_CHECK_RUN_ID,
            unsat_tag=source.SOURCE_CHECK_UNSAT_TAG,
            profile=source.PROFILE,
        )
        self.assertEqual(
            {key for key in generated if generated[key] != baseline[key]},
            {"candidate_patch"},
        )
        self.assertEqual(generated["trace_descriptor_header"].count(b"rc=%x21:s32"), 1)
        self.assertNotIn(b"rc=%w21:s32", generated["trace_descriptor_header"])
        self.assertIn(b"S22E1L2|", generated["candidate_patch"])
        self.assertEqual(
            generated["candidate_patch"].count(
                b"static noinline __used bool "
                b"s22_fyg8_e1_record_families_allowed"
            ),
            1,
        )

    def test_intent_uses_new_layout_and_distinct_run_identity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p310-intent-") as temporary:
            output = Path(temporary) / "intent"
            args = intent.parse_args(
                [
                    "--source-contract-id",
                    source.CONTRACT_ID,
                    "--nonce",
                    "31" * 16,
                    "--out",
                    str(output),
                ]
            )
            value = intent.create(args)
            exact = candidate_contract.verify(
                ROOT,
                ROOT / candidate_contract.DEFAULT_SOURCE,
                output / "candidate-intent.json",
                output / "candidate.patch",
            )
        self.assertEqual(
            value["identity_preimage"]["record_layout"],
            "S22E1L2-192-ab-header-slot-crc-payload64",
        )
        self.assertEqual(value["source_contract_id"], source.CONTRACT_ID)
        self.assertEqual(value["verdict"], source.INTENT_VERDICT)
        self.assertEqual(exact["run_id"], value["run_id"])

    def test_process_and_live_runner_select_p310_and_keep_usb_sidecar(self) -> None:
        selected = process._selected_candidate_source_contract(  # noqa: SLF001
            source.CONTRACT_ID, source.PROFILE
        )
        self.assertEqual(selected.contract_id, source.CONTRACT_ID)
        bundle = SimpleNamespace(
            manifest={
                "observation": {
                    "acceptance": {"source_contract_id": source.CONTRACT_ID}
                }
            }
        )
        self.assertTrue(live._p300_bundle(bundle))  # noqa: SLF001
        process_args = process_adapter.parse_args([])
        ready_args = ready_manifest.parse_args([])
        self.assertTrue(
            all(
                "s22plus_fyg8_p310" in value.as_posix()
                for value in (
                    process_args.candidate_static,
                    process_args.candidate_ap,
                    process_args.out,
                    ready_args.candidate_static,
                    ready_args.run_manifest,
                    ready_args.static_check,
                    ready_args.candidate_ap,
                    ready_args.out,
                )
            )
        )

    def test_evidence_adapter_round_trips_normal_pair_and_embedded_family(self) -> None:
        run_id = bytes.fromhex("42" * 16)
        record = source._prefix(run_id, spec.ATTR_ORDINAL)  # noqa: SLF001
        a = spec.POSITIONS[spec.ATTR_ORDINAL]
        record = carrier.apply_request(
            record,
            carrier.encode_request(
                spec.PROFILE,
                a.stage,
                run_id=run_id,
                outcome=carrier.OUTCOME_PROGRESS,
                item_index=a.item_index,
                detail=0xD00,
                payload_kind=carrier.PAYLOAD_RAW_EXCERPT,
                payload=b"raw:" + carrier.LONG_FAMILY + carrier.LEGACY_FAMILIES[0],
                version=carrier.REQUEST_VERSION_V3,
            ),
        )
        b = spec.POSITIONS[spec.SUMMARY_ORDINAL]
        record = carrier.apply_request(
            record,
            carrier.encode_request(
                spec.PROFILE,
                b.stage,
                run_id=run_id,
                outcome=carrier.OUTCOME_FAILURE,
                item_index=b.item_index,
                detail=spec.SUMMARY_DETAIL_BASE,
            ),
        )
        artifact = {"path": "private", "size": 1, "sha256": "00" * 32}
        acceptance = {
            "kind": evidence.E1_LATEST_STAGE_KIND,
            "source": evidence.CHECKPOINT_SOURCE,
            "decoder": source.decoder.DECODER_ID,
            "policy_id": source.decoder.POLICY_ID,
            "profile": source.PROFILE,
            "run_id": run_id.hex(),
            "long_family_hex": carrier.LONG_FAMILY.hex(),
            "unsat_family_hex": carrier.UNSAT_FAMILY.hex(),
            "terminal_stage": spec.TERMINAL_STAGE,
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "source_contract_id": source.CONTRACT_ID,
            "contract": {
                "candidate_static": artifact,
                "run_manifest": artifact,
                "static_check": artifact,
            },
        }
        result = evidence.classify_e1_latest_stage(record, acceptance)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["classification"], "P310_TELEMETRY_ONE_OR_MORE_BOOTS")
        self.assertEqual(result["foreign_count"], 0)
        self.assertGreaterEqual(result["records"][0]["active"]["generation"], 107)
        clean = evidence.classify_clean_baseline(b"clean", acceptance)
        self.assertTrue(clean["baseline_clean"])


if __name__ == "__main__":
    unittest.main()
