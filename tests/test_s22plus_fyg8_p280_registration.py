#!/usr/bin/env python3
"""Focused tests for bounded P2.80 registration and adapters."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p280_contract_spec as p280_spec  # noqa: E402, F401
import s22plus_fyg8_p280_trace_contract as p280_trace  # noqa: E402, F401
import s22plus_fyg8_p280_e1_decoder as p280_decoder  # noqa: E402, F401
import s22plus_fyg8_p280_source_contract as p280  # noqa: E402
import build_s22plus_fyg8_p234_candidate as candidate  # noqa: E402
import device_action_f1_evidence_v2 as evidence  # noqa: E402
import s22plus_fyg8_p253_e2_stock_closure as closure_selector  # noqa: E402
import s22plus_fyg8_p260_e2_stock_closure as p260_closure  # noqa: E402
import s22plus_fyg8_p260_source_contract as p260  # noqa: E402
import s22plus_fyg8_p280_e2_stock_closure as p280_closure  # noqa: E402
import s22plus_fyg8_p280_linked_audit as linked  # noqa: E402
import s22plus_fyg8_source_contracts as contracts  # noqa: E402


EXPECTED_P260_SAFETY = {
    "host_only": True,
    "device_contact": False,
    "device_write": False,
    "odin_invoked": False,
    "flash": False,
    "partition_write": False,
    "live_authorized": False,
    "boot_only_ap": True,
    "ap_members": ["boot.img.lz4"],
    "no_shell": True,
    "no_block_write": True,
    "no_reboot_syscall": True,
    "userspace_sysfs_configfs_write_scope": (
        "source-contract-bound-p260-e3-acm-and-peripheral-role"
    ),
    "usb_scope": "bounded-configfs-cdc-acm-banner-and-peripheral-role",
    "module_init_probe_authority": "active-live-unproved",
}
EXPECTED_P280_TRACE_AUTHORITY = {
    "userspace_tracefs_mount_scope": (
        "source-contract-bound-p280-mount-if-absent-owned-unmount-only"
    ),
    "userspace_tracefs_global_event_scope": (
        "source-contract-bound-p280-exact-group-event-register-readback-and-remove"
    ),
    "userspace_tracefs_instance_control_scope": (
        "source-contract-bound-p280-isolated-instance-create-remove-filter-"
        "enable-clock-buffer-trace-and-tracing-on"
    ),
    "dynamic_kernel_text_instrumentation_scope": (
        "standard-tracefs-kprobe-events-at-exact-source-bound-sites"
    ),
    "no_global_tracer_or_global_buffer_reset": True,
}
EXPECTED_P280_SAFETY = {
    **EXPECTED_P260_SAFETY,
    **EXPECTED_P280_TRACE_AUTHORITY,
}


class P280RegistrationTests(unittest.TestCase):
    def test_source_contract_and_decoder_are_selected(self):
        selected = contracts.select(p280.CONTRACT_ID, "E2")
        self.assertIs(selected.module, p280)
        self.assertIs(selected.decoder, p280.decoder)
        self.assertEqual(selected.contract_id, p280.CONTRACT_ID)
        self.assertIn(p280.CONTRACT_ID, contracts.contract_ids())
        self.assertIs(
            evidence._latest_stage_decoder(p280.CONTRACT_ID, "E2"),
            p280.decoder,
        )

    def test_source_selector_keeps_p260_unchanged(self):
        selected = contracts.select(p260.CONTRACT_ID, "E2")
        self.assertIs(selected.module, p260)
        self.assertIs(selected.decoder, p260.decoder)
        self.assertEqual(selected.contract_id, p260.CONTRACT_ID)

    def test_source_selector_rejects_wrong_profile(self):
        with self.assertRaises(contracts.SourceContractSelectionError):
            contracts.select(p280.CONTRACT_ID, "E1")

    def test_artifact_safety_selects_exact_p280_authority(self):
        safety = candidate.artifact_safety(
            {"profile": "E2", "source_contract_id": p280.CONTRACT_ID}
        )
        historical = candidate.artifact_safety(
            {"profile": "E2", "source_contract_id": p260.CONTRACT_ID}
        )
        self.assertEqual(p280.spec.RUNTIME_AUTHORITY, EXPECTED_P280_TRACE_AUTHORITY)
        self.assertEqual(safety, EXPECTED_P280_SAFETY)
        self.assertEqual(
            {
                name: safety[name]
                for name in p280.spec.RUNTIME_AUTHORITY
            },
            p280.spec.RUNTIME_AUTHORITY,
        )
        self.assertEqual(
            {
                name: value
                for name, value in safety.items()
                if name not in p280.spec.RUNTIME_AUTHORITY
            },
            historical,
        )
        self.assertNotIn("no_userspace_sysfs_or_configfs_write", safety)
        self.assertEqual(
            set(safety) - set(historical),
            set(p280.spec.RUNTIME_AUTHORITY),
        )

    def test_artifact_safety_keeps_p260_unchanged(self):
        safety = candidate.artifact_safety(
            {"profile": "E2", "source_contract_id": p260.CONTRACT_ID}
        )
        self.assertEqual(safety, EXPECTED_P260_SAFETY)
        self.assertEqual(
            safety["userspace_sysfs_configfs_write_scope"],
            "source-contract-bound-p260-e3-acm-and-peripheral-role",
        )
        self.assertEqual(
            safety["usb_scope"],
            "bounded-configfs-cdc-acm-banner-and-peripheral-role",
        )
        for name in p280.spec.RUNTIME_AUTHORITY:
            self.assertNotIn(name, safety)

    def test_stock_closure_selector_is_versioned(self):
        self.assertIs(
            closure_selector.select(p280.CONTRACT_ID), p280_closure
        )
        self.assertIs(
            closure_selector.select(p260.CONTRACT_ID), p260_closure
        )
        self.assertIs(p280_closure.select(p280.CONTRACT_ID), p280_closure)
        with self.assertRaises(p280_closure.ClosureError):
            p280_closure.select(p260.CONTRACT_ID)

    def test_stock_closure_scoped_overrides_restore_historical_state(self):
        adapter_entrypoints = (
            p280_closure.isolated_p260.EXPECTED_ELF_ENTRYPOINTS
        )
        legacy_entrypoints = (
            p280_closure.isolated_p260.isolated_legacy.EXPECTED_ELF_ENTRYPOINTS
        )
        audit = (
            p280_closure.isolated_p260._p260_audit_candidate_generic_rootfs
        )
        with p280_closure._expected_entrypoints(
            {"init": 0x410000, "child": 0x400000}
        ):
            self.assertEqual(
                p280_closure.isolated_p260.EXPECTED_ELF_ENTRYPOINTS["init"],
                0x410000,
            )
        self.assertIs(
            p280_closure.isolated_p260.EXPECTED_ELF_ENTRYPOINTS,
            adapter_entrypoints,
        )
        self.assertIs(
            p280_closure.isolated_p260.isolated_legacy.EXPECTED_ELF_ENTRYPOINTS,
            legacy_entrypoints,
        )
        with p280_closure._p280_audit_override():
            self.assertIs(
                p280_closure.isolated_p260._p260_audit_candidate_generic_rootfs,
                p280_closure._p280_audit_candidate_generic_rootfs,
            )
        self.assertIs(
            p280_closure.isolated_p260._p260_audit_candidate_generic_rootfs,
            audit,
        )

    def test_stock_closure_accepts_only_p280_trace_path_extension(self):
        historical = p260.spec
        strings = frozenset(
            (
                *p280_closure.REQUIRED_ABSOLUTE_PATH_STRINGS,
                *historical.E3_REQUIRED_CONTROL_STRINGS,
            )
        )
        data = b"\0".join(
            value.encode("ascii") for value in sorted(strings)
        ) + b"\0"
        p280_closure._validate_p280_authority_strings(data)
        p280_closure._validate_p280_authority_strings(
            data + b"/enable\0/filter\0"
        )
        missing = p280.spec.TRACEFS_ABSOLUTE_PATHS[0].encode("ascii") + b"\0"
        with self.assertRaisesRegex(
            p280_closure.ClosureError, "required absolute path is missing"
        ):
            p280_closure._validate_p280_authority_strings(
                data.replace(missing, b"", 1)
            )

        with self.assertRaises(p260_closure.ClosureError):
            p260_closure._validate_p260_authority_strings(data)
        with self.assertRaisesRegex(
            p280_closure.ClosureError, "absolute-path authority mismatch"
        ):
            p280_closure._validate_p280_authority_strings(
                data + b"/sys/kernel/debug/tracing\0"
            )

    def test_linked_audit_dispatch_and_adapter_are_exact(self):
        self.assertEqual(
            linked.EXPECTED_SOURCE_CONTRACT_ID, p280.CONTRACT_ID
        )
        self.assertEqual(
            linked.ADAPTER_ID, "s22plus-fyg8-p280-linked-audit-v1"
        )
        self.assertEqual(
            linked.repro.LINKED_VALIDATOR_ADAPTERS[p280.CONTRACT_ID],
            "s22plus_fyg8_p280_linked_audit",
        )
        self.assertEqual(
            linked.repro.LINKED_VALIDATOR_ADAPTERS[p260.CONTRACT_ID],
            "s22plus_fyg8_p260_linked_audit",
        )
        self.assertEqual(
            linked.LINKED_VALIDATOR_SYMBOLS,
            ("s22_fyg8_p280_detail_allowed",),
        )

    def test_linked_validator_delegates_with_p280_contract(self):
        expected = {"verified": True}
        with mock.patch.object(
            linked.p253,
            "audit_linked_validator",
            return_value=expected,
        ) as audit, mock.patch.object(
            linked.p253,
            "_table_loads",
            return_value=[{"table_offset": 0}],
        ) as table_loads:
            result = linked.audit_linked_validator(
                {
                    "s22_fyg8_p280_detail_allowed": "disassembly",
                },
                {
                    "s22_fyg8_e1_detail_allowed": [
                        "s22_fyg8_p280_detail_allowed"
                    ]
                },
                {"s22_fyg8_p280_details": 0x1000},
            )
        self.assertTrue(result["verified"])
        self.assertTrue(result["p280_detail_validator_called"])
        self.assertTrue(result["p280_detail_validator_loads_exact_table"])
        audit.assert_called_once_with(
            {"s22_fyg8_p280_detail_allowed": "disassembly"},
            {
                "s22_fyg8_e1_detail_allowed": [
                    "s22_fyg8_p280_detail_allowed"
                ]
            },
            {"s22_fyg8_p280_details": 0x1000},
            source_contract_module=p280,
            adapter_id=linked.ADAPTER_ID,
        )
        table_loads.assert_called_once_with(
            "disassembly",
            0x1000,
            len(
                linked.linked_table_storage_bytes(
                    p280.linked_table_bytes()
                )["s22_fyg8_p280_details"]
            ),
            "halfword",
        )

    def test_linked_detail_storage_normalizes_exact_abi_padding(self):
        logical = p280.linked_table_bytes()
        physical = linked.linked_table_storage_bytes(logical)
        detail = physical[linked.P280_DETAIL_TABLE]
        self.assertEqual(
            len(detail),
            len(p280.spec.DIAGNOSTIC_DETAILS)
            * linked.P280_DETAIL_STORAGE_STRIDE,
        )
        self.assertEqual(
            detail[linked.P280_DETAIL_LOGICAL_STRIDE :: linked.P280_DETAIL_STORAGE_STRIDE],
            b"\0" * len(p280.spec.DIAGNOSTIC_DETAILS),
        )
        normalized, evidence = linked.normalize_linked_table_storage(
            physical, logical
        )
        self.assertEqual(normalized, logical)
        self.assertTrue(evidence["zero_tail_padding_verified"])
        self.assertTrue(evidence["verified"])

    def test_linked_detail_storage_rejects_nonzero_padding(self):
        logical = p280.linked_table_bytes()
        physical = linked.linked_table_storage_bytes(logical)
        changed = bytearray(physical[linked.P280_DETAIL_TABLE])
        changed[linked.P280_DETAIL_LOGICAL_STRIDE] = 1
        with self.assertRaisesRegex(linked.AuditError, "padding is nonzero"):
            linked.normalize_linked_table_storage(
                {**physical, linked.P280_DETAIL_TABLE: bytes(changed)},
                logical,
            )

    def test_linked_detail_storage_rejects_packed_or_mutated_bytes(self):
        logical = p280.linked_table_bytes()
        physical = linked.linked_table_storage_bytes(logical)
        with self.assertRaisesRegex(linked.AuditError, "size differs"):
            linked.normalize_linked_table_storage(logical, logical)
        changed = bytearray(physical[linked.P280_DETAIL_TABLE])
        changed[0] ^= 1
        with self.assertRaisesRegex(linked.AuditError, "bytes differ"):
            linked.normalize_linked_table_storage(
                {**physical, linked.P280_DETAIL_TABLE: bytes(changed)},
                logical,
            )

    def test_central_auditor_owns_one_physical_storage_transform(self):
        logical, physical = linked.repro._linked_table_storage_bytes(
            linked.p280, linked
        )
        self.assertEqual(
            len(logical[linked.P280_DETAIL_TABLE]),
            len(p280.spec.DIAGNOSTIC_DETAILS)
            * linked.P280_DETAIL_LOGICAL_STRIDE,
        )
        self.assertEqual(
            len(physical[linked.P280_DETAIL_TABLE]),
            len(p280.spec.DIAGNOSTIC_DETAILS)
            * linked.P280_DETAIL_STORAGE_STRIDE,
        )

    def test_linked_adapter_does_not_mutate_central_auditor(self):
        common_audit = linked.repro.audit_linked
        with mock.patch.object(
            linked.repro,
            "check",
            side_effect=RuntimeError("injected common failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "injected common failure"):
                linked.check(object())
        self.assertIs(linked.repro.audit_linked, common_audit)

    def test_candidate_repro_requires_p280_linked_adapter(self):
        exact_contract = {
            "profile": "E2",
            "source_contract_id": p280.CONTRACT_ID,
            "run_id": "ab" * 16,
        }
        image = {"size": 123, "sha256": "a" * 64}
        value = {
            "schema": candidate.repro.SCHEMA,
            "target": candidate.TARGET,
            "verdict": candidate.repro.VERDICT,
            "candidate_contract": exact_contract,
            "linked_audit": {
                "verified": True,
                "audit_adapter": linked.ADAPTER_ID,
                "source_contract_validator": {
                    "writer_guard": {
                        "guard_dominates_retained_stores": True
                    }
                },
            },
            "byte_identical_artifacts": {
                name: True
                for name in candidate.repro.ARTIFACT_LIMITS
                if name != "build-result.json"
            },
            "build_a": {"artifacts": {"Image": image}},
            "pre_lto_qualification": {
                "schema": candidate.repro.P280_QUALIFICATION_SCHEMA,
                "verdict": candidate.repro.P280_QUALIFICATION_VERDICT,
                "build_allowed": True,
                "run_id": exact_contract["run_id"],
                "source_contract_id": p280.CONTRACT_ID,
                "qualification_repo_path": (
                    "workspace/private/qualification.json"
                ),
                "intent_repo_path": "workspace/private/intent.json",
                "patch_repo_path": "workspace/private/candidate.patch",
                "qualification": {"size": 10, "sha256": "1" * 64},
                "gate_result_receipts": {
                    name: {"size": 11, "sha256": str(index) * 64}
                    for index, name in enumerate(
                        sorted(candidate.repro.P280_GATE_RESULTS), start=2
                    )
                },
                "verified": True,
            },
        }
        normalized = candidate.repro.p280_qualification_identity(
            value["pre_lto_qualification"], exact_contract
        )
        with mock.patch.object(
            candidate,
            "_read_json",
            return_value=(value, {"size": 1, "sha256": "b" * 64}),
        ), mock.patch.object(
            candidate.repro,
            "verify_p280_qualification_file",
            return_value=normalized,
        ):
            result = candidate.verify_repro_result(
                Path("unused"),
                image,
                exact_contract,
                intent_path=ROOT / "workspace/private/intent.json",
                patch_path=ROOT / "workspace/private/candidate.patch",
            )
        self.assertTrue(result["linked_audit_verified"])

        value["linked_audit"]["audit_adapter"] = (
            "s22plus-fyg8-p260-linked-audit-v1"
        )
        with (
            mock.patch.object(
                candidate,
                "_read_json",
                return_value=(value, {"size": 1, "sha256": "b" * 64}),
            ),
            self.assertRaisesRegex(
                candidate.BuildError, "P2.80 linked audit adapter mismatch"
            ),
        ):
                candidate.verify_repro_result(
                    Path("unused"),
                    image,
                    exact_contract,
                    intent_path=ROOT / "workspace/private/intent.json",
                    patch_path=ROOT / "workspace/private/candidate.patch",
                )


if __name__ == "__main__":
    unittest.main()
