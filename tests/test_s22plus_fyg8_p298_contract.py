#!/usr/bin/env python3
"""Focused contract tests for the P2.98 gadget-start successor."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import s22plus_fyg8_p296_candidate_intent as p296_candidate_intent
import s22plus_fyg8_p296_source_contract as p296_contract
import s22plus_fyg8_p298_build as build
import s22plus_fyg8_p298_build_repro_check as build_repro
import s22plus_fyg8_p298_candidate_contract as candidate_contract
import s22plus_fyg8_p298_candidate_intent as candidate_intent
import s22plus_fyg8_p298_candidate_static_checker as static_checker
import s22plus_fyg8_p298_e2_stock_closure as stock_closure
import s22plus_fyg8_p298_identity_tiers as identity
import s22plus_fyg8_p298_linked_audit as linked
import s22plus_fyg8_p298_postbuild_linked_audit as postbuild
import s22plus_fyg8_p298_pre_lto_qualification as qualification
import s22plus_fyg8_p298_source_contract as contract
import s22plus_fyg8_p298_telemetry_generator as generator
import s22plus_fyg8_p298_telemetry_spec as spec


ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict[str, str]:
    return {
        "__dwc3_gadget_start": """
1000: 94000000 bl 2000 <__dwc3_gadget_ep_enable>
1004: 350000e0 cbnz w0, 1020
1008: 94000000 bl 2000 <__dwc3_gadget_ep_enable>
100c: 2a0003f4 mov w20, w0
1010: 350000e0 cbnz w0, 1024
1014: d65f03c0 ret
""",
        "__dwc3_gadget_ep_enable": "2000: d65f03c0 ret\n",
        "dwc3_gadget_reset_interrupt": "3000: d65f03c0 ret\n",
        "dwc3_gadget_conndone_interrupt": "4000: d65f03c0 ret\n",
        "dwc3_gadget_pullup": """
5000: 94000000 bl 1000 <__dwc3_gadget_start>
5004: 52800021 mov w1, #0x1
5008: aa1303e0 mov x0, x19
500c: 94000000 bl 6000 <dwc3_gadget_run_stop>
5010: 2a0003f5 mov w21, w0
""",
        "dwc3_gadget_resume": """
7000: 94000000 bl 1000 <__dwc3_gadget_start>
7004: 37f80160 tbnz w0, #31, 7010
7008: d65f03c0 ret
""",
    }


def _authority_data() -> bytes:
    values = set(stock_closure.REQUIRED_ABSOLUTE_PATH_STRINGS)
    values.update(
        stock_closure.p286.p282._HISTORICAL_SPEC.E3_REQUIRED_CONTROL_STRINGS
    )
    return b"\0".join(value.encode("ascii") for value in sorted(values)) + b"\0"


class P298ContractTests(unittest.TestCase):
    def _validate_synthetic_incidental_path(self, suffix: bytes = b"") -> bytes:
        window = stock_closure.INCIDENTAL_INSTRUCTION_WINDOW
        data = _authority_data() + window + suffix
        offset = len(_authority_data()) + 1
        with (
            mock.patch.object(stock_closure, "INCIDENTAL_INIT_SIZE", len(data)),
            mock.patch.object(
                stock_closure,
                "INCIDENTAL_INIT_SHA256",
                hashlib.sha256(data).hexdigest(),
            ),
            mock.patch.object(stock_closure, "INCIDENTAL_PATH_OFFSET", offset),
            mock.patch.object(
                stock_closure,
                "INCIDENTAL_TEXT_OFFSET",
                offset - 1,
            ),
            mock.patch.object(
                stock_closure,
                "INCIDENTAL_TEXT_END",
                offset - 1 + len(window),
            ),
            mock.patch.object(
                stock_closure,
                "INCIDENTAL_INSTRUCTION_WINDOW_OFFSET",
                offset - 1,
            ),
        ):
            stock_closure._validate_p298_authority_strings(data)
        return data

    def test_stock_closure_accepts_only_exact_opcode_path_receipt(self) -> None:
        data = self._validate_synthetic_incidental_path()
        with self.assertRaisesRegex(
            stock_closure.ClosureError,
            "absolute-path authority mismatch",
        ):
            stock_closure._validate_p298_authority_strings(data)

    def test_stock_closure_incidental_path_mutations_fail_closed(self) -> None:
        unauthorized = (
            b"\0/tmp\0",
            b"\0/data/local/tmp/unauthorized\0",
        )
        for suffix in unauthorized:
            with self.subTest(suffix=suffix), self.assertRaisesRegex(
                stock_closure.ClosureError,
                "absolute-path authority mismatch",
            ):
                self._validate_synthetic_incidental_path(suffix)

        data = _authority_data() + stock_closure.INCIDENTAL_INSTRUCTION_WINDOW
        offset = len(_authority_data()) + 1
        with (
            mock.patch.object(stock_closure, "INCIDENTAL_INIT_SIZE", len(data)),
            mock.patch.object(
                stock_closure,
                "INCIDENTAL_INIT_SHA256",
                hashlib.sha256(data).hexdigest(),
            ),
            mock.patch.object(stock_closure, "INCIDENTAL_PATH_OFFSET", offset),
            mock.patch.object(
                stock_closure,
                "INCIDENTAL_TEXT_OFFSET",
                offset - 1,
            ),
            mock.patch.object(
                stock_closure,
                "INCIDENTAL_TEXT_END",
                offset - 1 + len(stock_closure.INCIDENTAL_INSTRUCTION_WINDOW),
            ),
            mock.patch.object(
                stock_closure,
                "INCIDENTAL_INSTRUCTION_WINDOW_OFFSET",
                offset - 1,
            ),
        ):
            mutated = data[:offset] + b"/tmp" + data[offset + 4:]
            with self.assertRaisesRegex(
                stock_closure.ClosureError,
                "absolute-path authority mismatch",
            ):
                stock_closure._validate_p298_authority_strings(mutated)

    def test_stock_closure_routes_generic_rootfs_validator_and_restores(self) -> None:
        window = stock_closure.INCIDENTAL_INSTRUCTION_WINDOW
        data = _authority_data() + window
        offset = len(_authority_data()) + 1
        inherited_validator = (
            stock_closure.p286.p282._validate_p282_authority_strings
        )
        with (
            mock.patch.object(stock_closure, "INCIDENTAL_INIT_SIZE", len(data)),
            mock.patch.object(
                stock_closure,
                "INCIDENTAL_INIT_SHA256",
                hashlib.sha256(data).hexdigest(),
            ),
            mock.patch.object(stock_closure, "INCIDENTAL_PATH_OFFSET", offset),
            mock.patch.object(
                stock_closure,
                "INCIDENTAL_TEXT_OFFSET",
                offset - 1,
            ),
            mock.patch.object(
                stock_closure,
                "INCIDENTAL_TEXT_END",
                offset - 1 + len(window),
            ),
            mock.patch.object(
                stock_closure,
                "INCIDENTAL_INSTRUCTION_WINDOW_OFFSET",
                offset - 1,
            ),
        ):
            with stock_closure._p298_authority_paths():
                self.assertIs(
                    stock_closure.p286.p282._validate_p282_authority_strings,
                    stock_closure._validate_p298_authority_strings,
                )
                stock_closure.p286.p282._validate_p282_authority_strings(data)
                with self.assertRaisesRegex(
                    stock_closure.ClosureError,
                    "absolute-path authority mismatch",
                ):
                    stock_closure.p286.p282._validate_p282_authority_strings(
                        data + b"\0/tmp\0"
                    )
        self.assertIs(
            stock_closure.p286.p282._validate_p282_authority_strings,
            inherited_validator,
        )
        with self.assertRaises(RuntimeError):
            with stock_closure._p298_authority_paths():
                raise RuntimeError("forced context exit")
        self.assertIs(
            stock_closure.p286.p282._validate_p282_authority_strings,
            inherited_validator,
        )

    def test_postbuild_tier2_repair_is_exact_and_non_payload(self) -> None:
        static_checker._configure()
        self.assertIs(static_checker.base.audit, static_checker.audit)
        self.assertEqual(
            static_checker.HISTORICAL_POSTBUILD_RESULT,
            {
                "sha256": (
                    "a7bfff7bdc82683999ef0d91349f20560b659ea703cb0542eeb37ca36a3ff997"
                ),
                "size": 71342,
            },
        )
        tiers = identity.path_tiers()
        for path in static_checker.TIER2_REPAIR_PATHS:
            with self.subTest(path=path):
                self.assertIn(path.as_posix(), tiers["tier2_qualification"])
                self.assertNotIn(path.as_posix(), tiers["tier1_payload"])

    def test_postbuild_tier2_repair_receipt_and_a_b_mutations_fail_closed(self) -> None:
        payload = b"exact historical postbuild fixture"
        with mock.patch.object(
            static_checker,
            "HISTORICAL_POSTBUILD_RESULT",
            static_checker.base.receipt(payload),
        ):
            self.assertTrue(static_checker._is_historical_postbuild_result(payload))
            self.assertFalse(
                static_checker._is_historical_postbuild_result(payload + b"x")
            )

        private = ROOT / "workspace/private"
        private.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private) as name:
            temporary = Path(name)
            build_a = temporary / "a"
            build_b = temporary / "b"
            build_a.mkdir()
            build_b.mkdir()
            args = SimpleNamespace(build_a=build_a, build_b=build_b)
            directories = static_checker._distinct_build_directories(ROOT, args)
            self.assertEqual(set(directories), {"build_a", "build_b"})
            with self.assertRaisesRegex(
                static_checker.CheckError, "not distinct"
            ):
                static_checker._distinct_build_directories(
                    ROOT, SimpleNamespace(build_a=build_a, build_b=build_a)
                )
            alias = temporary / "alias"
            alias.symlink_to(build_a, target_is_directory=True)
            with self.assertRaisesRegex(
                static_checker.CheckError, "indirect or missing|not distinct"
            ):
                static_checker._distinct_build_directories(
                    ROOT, SimpleNamespace(build_a=build_a, build_b=alias)
                )

            limits = {"Image": 1024, "build-result.json": 1024}
            exact_contract = {"source_contract_id": contract.CONTRACT_ID}
            artifacts = {}
            for key, directory in directories.items():
                artifacts[key] = {}
                for artifact in limits:
                    data = (
                        artifact.encode("ascii")
                        if artifact == "Image"
                        else f"{key}:{artifact}".encode("ascii")
                    )
                    (directory / artifact).write_bytes(data)
                    artifacts[key][artifact] = static_checker.base.receipt(data)
            result = {
                "schema": static_checker.repro.SCHEMA,
                "verdict": static_checker.repro.VERDICT,
                "candidate_contract": exact_contract,
                "pre_lto_qualification": {
                    "qualification": {
                        **static_checker.HISTORICAL_QUALIFICATION,
                        "path": "/private/historical/qualification-v3.json",
                    },
                    "qualification_repo_path": (
                        "workspace/private/outputs/s22plus_fyg8_p298_pre_lto/"
                        "qualification-v3.json"
                    ),
                },
                "linked_audit": {
                    "verified": True,
                    "postbuild_audit": {"verified": True},
                },
                "byte_identical_artifacts": {"Image": True},
                "build_a": {"artifacts": artifacts["build_a"]},
                "build_b": {"artifacts": artifacts["build_b"]},
            }
            with mock.patch.object(
                static_checker.repro, "ARTIFACT_LIMITS", limits
            ):
                proof = static_checker._verify_historical_postbuild_repair(
                    ROOT, args, result, exact_contract
                )
                self.assertTrue(proof["verified"])
                self.assertTrue(proof["a_b_artifact_inodes_distinct"])
                self.assertEqual(
                    proof["byte_identical_artifacts_reverified"], ["Image"]
                )
                result["pre_lto_qualification"]["qualification"]["size"] += 1
                with self.assertRaisesRegex(
                    static_checker.CheckError, "header mismatch"
                ):
                    static_checker._verify_historical_postbuild_repair(
                        ROOT, args, result, exact_contract
                    )
                result["pre_lto_qualification"]["qualification"]["size"] -= 1
                result["pre_lto_qualification"]["qualification_repo_path"] += ".x"
                with self.assertRaisesRegex(
                    static_checker.CheckError, "header mismatch"
                ):
                    static_checker._verify_historical_postbuild_repair(
                        ROOT, args, result, exact_contract
                    )
                result["pre_lto_qualification"]["qualification_repo_path"] = (
                    "workspace/private/outputs/s22plus_fyg8_p298_pre_lto/"
                    "qualification-v3.json"
                )
                (build_b / "Image").write_bytes(b"mutated")
                with self.assertRaisesRegex(
                    static_checker.CheckError, "artifact receipt mismatch"
                ):
                    static_checker._verify_historical_postbuild_repair(
                        ROOT, args, result, exact_contract
                    )
                different = b"different but self-consistent B Image"
                (build_b / "Image").write_bytes(different)
                artifacts["build_b"]["Image"] = static_checker.base.receipt(
                    different
                )
                with self.assertRaisesRegex(
                    static_checker.CheckError, "bytes are not identical"
                ):
                    static_checker._verify_historical_postbuild_repair(
                        ROOT, args, result, exact_contract
                    )
                (build_b / "Image").write_bytes((build_a / "Image").read_bytes())
                artifacts["build_b"]["Image"] = static_checker.base.receipt(
                    (build_b / "Image").read_bytes()
                )
                (build_b / "Image").unlink()
                os.link(build_a / "Image", build_b / "Image")
                with self.assertRaisesRegex(
                    static_checker.CheckError, "share one inode"
                ):
                    static_checker._verify_historical_postbuild_repair(
                        ROOT, args, result, exact_contract
                    )

    def test_postbuild_tier2_repair_emits_honest_audit_state(self) -> None:
        repair = {"verified": True}

        def fake_base_audit(_args):
            static_checker._ACTIVE_TIER2_REPAIR.set(repair)
            return {"build_repro": {"fresh_reverification": True}}

        with mock.patch.object(static_checker, "_BASE_AUDIT", fake_base_audit):
            result = static_checker.audit(SimpleNamespace())
        self.assertFalse(result["build_repro"]["fresh_reverification"])
        self.assertTrue(
            result["build_repro"]["immutable_build_time_proof_revalidated"]
        )
        self.assertEqual(result["build_repro"]["tier2_repair"], repair)

    def test_identity_and_generated_patch(self) -> None:
        result = identity.validate()
        self.assertEqual(result["tier1_source_key_count"], len(contract.SOURCE_KEYS))
        self.assertEqual(result["generated_payload_count"], 13)
        source = generator.generate_bytes(
            ROOT,
            run_id=identity.SOURCE_CHECK_RUN_ID,
            unsat_tag=identity.SOURCE_CHECK_UNSAT_TAG,
            profile=contract.PROFILE,
        )
        self.assertIn(b"{105, 0, 0xd00}", source["candidate_patch"])
        self.assertIn(b"P282_BIND_EVENT_COUNT 12U", source["trace_descriptor_header"])

    def test_linked_detail_table_uses_current_sot(self) -> None:
        tables = contract.linked_table_bytes()
        rules = tables["s22_fyg8_p290_detail_rules"]
        self.assertEqual(len(rules), len(spec.exact_detail_rules()) * 4)
        self.assertTrue(linked.normalize_linked_table_storage(tables, tables)[1])

    def test_full_lto_callsite_contract_accepts_exact_shape(self) -> None:
        proof = linked.audit_gadget_start_callsite_pair(_fixture(), _fixture())
        self.assertTrue(proof["a_b_disassembly_identical"])
        self.assertTrue(
            proof["build_a"]["ep0_enable_chain"]["hit_one_is_ep0_out"]
        )
        self.assertFalse(
            proof["build_a"]["pullup_discard"][
                "return_consumed_before_overwrite"
            ]
        )

    def test_full_lto_callsite_mutations_fail_closed(self) -> None:
        mutations = {
            "inline-or-missing": (
                "dwc3_gadget_pullup",
                "94000000 bl 1000 <__dwc3_gadget_start>",
                "d503201f nop",
            ),
            "clone": (
                "dwc3_gadget_pullup",
                "<__dwc3_gadget_start>",
                "<__dwc3_gadget_start.llvm.1>",
            ),
            "tail-call": (
                "dwc3_gadget_pullup",
                "94000000 bl 1000 <__dwc3_gadget_start>",
                "14000000 b 1000 <__dwc3_gadget_start>",
            ),
            "return-consuming": (
                "dwc3_gadget_pullup",
                "5004: 52800021 mov w1, #0x1",
                "5004: 35000060 cbnz w0, 5010",
            ),
            "one-ep-enable-call": (
                "__dwc3_gadget_start",
                "1008: 94000000 bl 2000 <__dwc3_gadget_ep_enable>",
                "1008: d503201f nop",
            ),
        }
        for name, (symbol, old, new) in mutations.items():
            with self.subTest(name=name):
                candidate = _fixture()
                candidate[symbol] = candidate[symbol].replace(old, new)
                with self.assertRaises(linked.AuditError):
                    linked.audit_gadget_start_callsites(candidate)

    def test_full_lto_a_b_callsite_divergence_fails_closed(self) -> None:
        build_b = _fixture()
        build_b["dwc3_gadget_resume"] = build_b[
            "dwc3_gadget_resume"
        ].replace("7008: d65f03c0 ret", "7008: d503201f nop")
        with self.assertRaises(linked.AuditError):
            linked.audit_gadget_start_callsite_pair(_fixture(), build_b)

    def test_reachable_records_cover_new_families(self) -> None:
        result = contract.validate_reachable_records(
            bytes.fromhex("1234567890abcdef1234567890abcdef")
        )
        self.assertEqual(
            result["telemetry_reachable_variants"],
            contract.TELEMETRY_REACHABLE_VARIANTS,
        )
        self.assertTrue(result["verified"])

    def test_qualification_selects_exact_p298_adapters(self) -> None:
        exact_contract = {
            "profile": contract.PROFILE,
            "source_contract_id": contract.CONTRACT_ID,
        }
        safety = qualification._expected_safety(exact_contract)
        audit_module = qualification._load_linked_audit_module()
        self.assertEqual(
            audit_module.EXPECTED_SOURCE_CONTRACT_ID,
            contract.CONTRACT_ID,
        )
        self.assertEqual(audit_module.ADAPTER_ID, linked.ADAPTER_ID)
        self.assertEqual(safety["candidate_module_binaries_injected"], 0)
        self.assertTrue(safety["built_in_telemetry_only"])
        self.assertEqual(
            safety["dynamic_kernel_text_instrumentation_scope"],
            spec.RUNTIME_AUTHORITY[
                "dynamic_kernel_text_instrumentation_scope"
            ],
        )

    def test_build_and_postbuild_registration_is_exact(self) -> None:
        build._configure()
        self.assertEqual(
            build.base.QUALIFICATION_MODULES,
            {
                contract.CONTRACT_ID: (
                    "s22plus_fyg8_p298_pre_lto_qualification",
                    "p298_pre_lto_qualification",
                    "P2.98",
                )
            },
        )
        build_repro._configure()
        self.assertEqual(
            build_repro.base.LINKED_VALIDATOR_ADAPTERS[
                contract.CONTRACT_ID
            ],
            "s22plus_fyg8_p298_postbuild_linked_audit",
        )
        postbuild._configure()
        self.assertEqual(postbuild.base.ADAPTER_ID, linked.ADAPTER_ID)
        self.assertEqual(
            postbuild.base.EXPECTED_SOURCE_CONTRACT_ID,
            contract.CONTRACT_ID,
        )

    def test_complete_implementation_closure(self) -> None:
        result = contract.implementation_result(ROOT)
        self.assertEqual(result["verdict"], contract.IMPLEMENTATION_VERDICT)
        self.assertTrue(result["patch"]["driver_clean_apply"])
        self.assertTrue(result["telemetry_closure"]["result_contract"]["verified"])
        self.assertTrue(result["linked_userspace"]["static_aarch64"])

    def test_candidate_intent_uses_p298_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p298-intent-") as temporary:
            output = Path(temporary) / "p298-intent"
            p296_output = Path(temporary) / "p296-intent"
            p296_args = p296_candidate_intent.parse_args(
                [
                    "--source-contract-id",
                    p296_contract.CONTRACT_ID,
                    "--profile",
                    p296_contract.PROFILE,
                    "--out",
                    str(p296_output),
                ]
            )
            p296_result = p296_candidate_intent.create(p296_args)
            args = candidate_intent.parse_args(
                [
                    "--source-contract-id",
                    contract.CONTRACT_ID,
                    "--profile",
                    contract.PROFILE,
                    "--out",
                    str(output),
                ]
            )
            result = candidate_intent.create(args)
            p296_patch = (p296_output / "candidate.patch").read_bytes()
            p298_patch = (output / "candidate.patch").read_bytes()
        self.assertEqual(result["verdict"], contract.INTENT_VERDICT)
        self.assertEqual(result["source_contract_id"], contract.CONTRACT_ID)
        self.assertNotEqual(result["run_id"], p296_result["run_id"])
        self.assertNotEqual(p298_patch, p296_patch)

    def test_candidate_reopen_selector_uses_p298_contract(self) -> None:
        candidate_contract._configure()
        selected = candidate_contract.intent.selected_source_contract(
            contract.CONTRACT_ID,
            contract.PROFILE,
        )
        self.assertIs(selected.module, contract)
        self.assertEqual(selected.contract_id, contract.CONTRACT_ID)


if __name__ == "__main__":
    unittest.main()
