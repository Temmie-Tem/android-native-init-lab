#!/usr/bin/env python3
"""Focused contract tests for P3.00 event-ingress/IRQ attribution."""

from __future__ import annotations

from pathlib import Path
import contextlib
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock

from tests.test_device_action_f1_live_v2 import FakeBackend

import device_action_f1_evidence_v2 as evidence
import device_action_f1_live_v2 as live
import device_action_f1_v2 as process_v2
import device_action_usb_trace_sidecar_v1 as sidecar
import prepare_s22plus_fyg8_p300_process_v2 as process_adapter
import prepare_s22plus_fyg8_p300_ready_manifest as ready_manifest
import s22plus_fyg8_p300_build as build
import s22plus_fyg8_p300_build_repro_check as build_repro
import s22plus_fyg8_p300_candidate_intent as candidate_intent
import s22plus_fyg8_p300_e2_stock_closure as stock_closure
import s22plus_fyg8_p298_source_contract as p298
import s22plus_fyg8_p300_identity_tiers as identity
import s22plus_fyg8_p300_linked_audit as linked
import s22plus_fyg8_p300_postbuild_linked_audit as postbuild
import s22plus_fyg8_p300_pre_lto_qualification as qualification
import s22plus_fyg8_p300_source_contract as contract
import s22plus_fyg8_p300_telemetry_decoder as decoder
import s22plus_fyg8_p300_telemetry_generator as generator
import s22plus_fyg8_p300_telemetry_spec as spec
import s22plus_fyg8_p300_usb_trace_binding as usb_binding


ROOT = Path(__file__).resolve().parents[1]


def _linked_fixture() -> dict[str, str]:
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
        "s22_p300_dwc3_event_config_snapshot": "3000: d65f03c0 ret\n",
        "dwc3_interrupt": "4000: d65f03c0 ret\n",
        "dwc3_thread_interrupt": "5000: d65f03c0 ret\n",
        "dwc3_process_event_entry": "6000: d65f03c0 ret\n",
        "dwc3_gadget_pullup": """
7000: 94000000 bl 1000 <__dwc3_gadget_start>
7004: 52800021 mov w1, #0x1
7008: aa1303e0 mov x0, x19
700c: 94000000 bl 8000 <dwc3_gadget_run_stop>
7010: 2a0003f5 mov w21, w0
""",
        "dwc3_gadget_resume": """
9000: 94000000 bl 1000 <__dwc3_gadget_start>
9004: 37f80160 tbnz w0, #31, 9010
9008: d65f03c0 ret
""",
    }


class P300ContractTests(unittest.TestCase):
    def test_identity_extends_p298_without_mutating_inherited_bytes(self) -> None:
        inherited = p298.source_bytes(ROOT)
        current = identity.tier1_materials(ROOT)
        for new_key, old_key in identity.INHERITED_PAYLOAD_SOURCE_KEYS.items():
            self.assertEqual(current[new_key], inherited[old_key])
        self.assertEqual(set(current), contract.SOURCE_KEYS)
        self.assertIn(
            "workspace/public/src/scripts/revalidation/"
            "device_action_usb_trace_sidecar_v1.py",
            identity.path_tiers()["tier3_live"],
        )
        all_paths = {
            path
            for paths in identity.path_tiers().values()
            for path in paths
        }
        tier1 = set(identity.path_tiers()["tier1_payload"])
        for filename in (
            "s22plus_fyg8_p300_candidate_intent.py",
            "s22plus_fyg8_p300_userspace_build.py",
            "s22plus_fyg8_p300_build.py",
            "build_s22plus_fyg8_p300_candidate.py",
            "s22plus_fyg8_p300_boot_only_packager.py",
        ):
            self.assertTrue(any(path.endswith(filename) for path in tier1))
        descriptor = identity.descriptor()
        self.assertTrue(
            descriptor["tier2"]["candidate_qualification_adapter_complete"]
        )
        self.assertFalse(descriptor["tier2"]["approval_bundle_bound"])
        self.assertTrue(
            descriptor["tier3"]["same_f1_binding_adapter_complete"]
        )
        self.assertFalse(
            descriptor["tier3"]["same_f1_runtime_binding_complete"]
        )
        self.assertIn(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p300_usb_trace_binding.py",
            all_paths,
        )

    def test_contract_reachable_routes_include_position_duplicates(self) -> None:
        result = contract.validate_reachable_records(
            bytes.fromhex("1234567890abcdef1234567890abcdef")
        )
        self.assertEqual(
            result["telemetry_reachable_variants"],
            contract.TELEMETRY_REACHABLE_VARIANTS,
        )
        self.assertEqual(result["telemetry_reachable_variants"], 358)

    def test_source_check_patch_is_generator_exact(self) -> None:
        source = contract.source_bytes(ROOT)
        generated = generator.generate_bytes(
            ROOT,
            run_id=contract.SOURCE_CHECK_RUN_ID,
            unsat_tag=contract.SOURCE_CHECK_UNSAT_TAG,
            profile=contract.PROFILE,
        )
        self.assertEqual(source["base_patch"], generated["candidate_patch"])
        self.assertNotIn(b"dwc3-msm-core.c", source["base_patch"])

    def test_all_final_ingress_families_imply_probe_success(self) -> None:
        for detail in range(0xD00, 0xDB0):
            telemetry = decoder.decode_detail(detail)["telemetry"]
            self.assertTrue(telemetry["probe_armed"])
            self.assertEqual(telemetry["gadget_start_rc"], 0)
            self.assertEqual(telemetry["ep_enable_hit_count"], 2)
            self.assertTrue(telemetry["streaming_trace_verified"])
            self.assertTrue(telemetry["ring_loss_zero"])
            self.assertTrue(telemetry["kretprobe_nmissed_zero"])

    def test_full_host_implementation_closes(self) -> None:
        result = contract.implementation_result(ROOT)
        self.assertEqual(result["verdict"], contract.IMPLEMENTATION_VERDICT)
        self.assertTrue(result["patch"]["driver_clean_apply"])
        self.assertEqual(result["patch"]["external_module_patch_count"], 0)
        self.assertTrue(result["linked_userspace"]["two_link_reproducible"])
        self.assertEqual(result["descriptor"]["bind_event_count"], 15)
        self.assertEqual(result["descriptor"]["irq_return_maxactive"], 32)
        self.assertEqual(result["descriptor"]["ingress_class_count"], 11)
        self.assertFalse(
            result["descriptor"]["same_f1_host_sidecar"]["binding_complete"]
        )
        self.assertTrue(result["safety"]["candidate_adapters_present"])

    def test_candidate_intent_and_qualification_registration_are_exact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p300-intent-") as temporary:
            output = Path(temporary) / "intent"
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
        self.assertEqual(result["source_contract_id"], contract.CONTRACT_ID)
        self.assertEqual(result["verdict"], contract.INTENT_VERDICT)
        build._configure()
        self.assertEqual(
            build.base.QUALIFICATION_MODULES,
            {
                contract.CONTRACT_ID: (
                    "s22plus_fyg8_p300_pre_lto_qualification",
                    "p300_pre_lto_qualification",
                    "P3.00",
                )
            },
        )
        self.assertEqual(
            qualification._load_linked_audit_module().ADAPTER_ID,
            linked.ADAPTER_ID,
        )
        safety = qualification._expected_safety(
            {
                "profile": contract.PROFILE,
                "source_contract_id": contract.CONTRACT_ID,
            }
        )
        self.assertEqual(safety["candidate_module_binaries_injected"], 0)
        self.assertTrue(safety["built_in_telemetry_only"])
        build_repro._configure()
        self.assertEqual(
            build_repro.base.LINKED_VALIDATOR_ADAPTERS[contract.CONTRACT_ID],
            "s22plus_fyg8_p300_postbuild_linked_audit",
        )
        postbuild._configure()
        self.assertEqual(postbuild.base.ADAPTER_ID, linked.ADAPTER_ID)
        qualification._validate_reused_s22_process_capability()
        self.assertTrue(qualification.INHERITED_P280_LIFECYCLE_RESULT)
        self.assertIn(
            "s22plus_fyg8_p298_pre_lto",
            qualification.DEFAULT_LIFECYCLE_RESULT.as_posix(),
        )
        self.assertNotIn(
            Path("tests/test_device_action_process_v2_docs.py"),
            qualification.PROCESS_V2_TESTS,
        )
        for relative, expected in qualification.REUSED_S22_POLICY_RECEIPTS.items():
            self.assertEqual(
                hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(),
                expected,
            )

    def test_full_lto_probe_target_contract_accepts_exact_shape(self) -> None:
        proof = linked.audit_gadget_start_callsite_pair(
            _linked_fixture(), _linked_fixture()
        )
        self.assertTrue(proof["a_b_disassembly_identical"])
        self.assertTrue(proof["build_a"]["probe_targets_out_of_line"])
        self.assertTrue(
            proof["build_a"]["ep0_enable_chain"]["hit_one_is_ep0_out"]
        )
        mutated = _linked_fixture()
        del mutated["dwc3_interrupt"]
        with self.assertRaises(linked.AuditError):
            linked.audit_gadget_start_callsites(mutated)

    def test_stock_closure_pins_only_declared_trace_paths_and_opcode(self) -> None:
        self.assertEqual(len(stock_closure.TRACE_STAT_PATHS), 32)
        self.assertTrue(
            stock_closure.P300_TRACE_PATHS
            <= stock_closure.REQUIRED_ABSOLUTE_PATH_STRINGS
        )
        self.assertEqual(stock_closure.INCIDENTAL_PATH_OFFSET, 0x3929)
        self.assertEqual(
            stock_closure.INCIDENTAL_INSTRUCTION_WINDOW,
            bytes.fromhex("e02f4539220000b0"),
        )
        first = (
            ROOT
            / "workspace/private/outputs/"
            "s22plus_fyg8_p300_preintent_Rz55EP/userspace/init"
        )
        if first.is_file():
            scrubbed = stock_closure._scrub_exact_incidental_opcode_path(
                first.read_bytes()
            )
            stock_closure._validate_p300_authority_strings(scrubbed)

    def test_same_attempt_sidecar_binding_is_exact_and_fail_closed(self) -> None:
        digest = "1" * 64
        binding = usb_binding.create_binding(
            campaign_id="p300-campaign-1",
            attempt_id="attempt-1",
            candidate_ap={"sha256": "2" * 64, "size": 4096},
            approval_binding_sha256=digest,
            transaction_path="workspace/private/runs/p300/transaction",
            sidecar_result_path=(
                "workspace/private/runs/p300/host-usb-trace/result.json"
            ),
            observation_witness_path=(
                "workspace/private/runs/p300/observation-durable.json"
            ),
        )
        records = []
        for kind, action, timestamp in (
            ("event", "live_session_start", "2026-08-04T00:00:00Z"),
            ("event", "candidate_flash_start", "2026-08-04T00:00:02Z"),
            ("event", "candidate_flash_done", "2026-08-04T00:00:04Z"),
            ("event", "candidate_boot_ready", "2026-08-04T00:00:08Z"),
        ):
            records.append(
                {
                    "sequence": len(records),
                    "binding_sha256": digest,
                    "kind": kind,
                    "action": action,
                    "timestamp_utc": timestamp,
                    "details": {"attempt": 1}
                    if action == "candidate_flash_start"
                    else {},
                }
            )
        source_result = {
            "returncode": -15,
            "alive_at_arm": True,
            "alive_before_stop": True,
            "stop_requested_utc": "2026-08-04T00:00:05.500000Z",
            "ended_utc": "2026-08-04T00:00:05.600000Z",
        }
        sidecar_result = {
            "schema": "device_action_usb_trace_sidecar_v1",
            "phase": "complete",
            "started_utc": "2026-08-04T00:00:01Z",
            "ended_utc": "2026-08-04T00:00:06Z",
            "stop_reason": "signal:SIGTERM",
            "owner_token_sha256": usb_binding.owner_token_sha256(binding),
            "non_authoritative": True,
            "device_actions": False,
            "opens_candidate_acm": False,
            "sources": {
                name: dict(source_result) for name in sidecar.SOURCE_COMMANDS
            },
        }
        observation_witness = {
            "schema": usb_binding.OBSERVATION_WITNESS_SCHEMA,
            "binding_sha256": binding["binding_sha256"],
            "approval_binding_sha256": digest,
            "candidate_ap": binding["candidate_ap"],
            "timestamp_utc": "2026-08-04T00:00:05Z",
            "live_state_sha256": "3" * 64,
            "durable": True,
            "device_actions": False,
        }
        self.assertTrue(
            usb_binding.verify_same_attempt(
                binding, sidecar_result, records, observation_witness
            )["same_attempt_verified"]
        )
        sidecar_result["ended_utc"] = "2026-08-04T00:00:03Z"
        with self.assertRaises(usb_binding.BindingError):
            usb_binding.verify_same_attempt(
                binding, sidecar_result, records, observation_witness
            )
        sidecar_result["ended_utc"] = "2026-08-04T00:00:06Z"
        sidecar_result["stop_reason"] = "duration-expired"
        with self.assertRaises(usb_binding.BindingError):
            usb_binding.verify_same_attempt(
                binding, sidecar_result, records, observation_witness
            )
        sidecar_result["stop_reason"] = "signal:SIGTERM"
        sidecar_result["sources"]["kernel"]["returncode"] = 0
        with self.assertRaises(usb_binding.BindingError):
            usb_binding.verify_same_attempt(
                binding, sidecar_result, records, observation_witness
            )

    def test_process_v2_registers_p300_and_binds_all_three_tiers(self) -> None:
        decoder_module = evidence._latest_stage_decoder(contract.CONTRACT_ID, "E2")
        closure = evidence._select_e2_closure(contract.CONTRACT_ID)
        self.assertEqual(decoder_module.DECODER_ID, decoder.DECODER_ID)
        self.assertEqual(closure.source_contract.CONTRACT_ID, contract.CONTRACT_ID)
        self.assertEqual(
            evidence.P300_CANDIDATE_STATIC_SCHEMA,
            "s22plus_fyg8_p300_candidate_static_checker_v1",
        )
        receipts = process_v2.execution_critical_source_receipts(
            {
                "kind": evidence.E1_LATEST_STAGE_KIND,
                "profile": "E2",
                "source_contract_id": contract.CONTRACT_ID,
            }
        )
        self.assertEqual(
            len([key for key in receipts if key.startswith("candidate_source_")]),
            len(contract.SOURCE_KEYS),
        )
        self.assertEqual(
            len([key for key in receipts if key.startswith("p300_tier2_")]),
            len(identity.tier2_materials(ROOT)),
        )
        self.assertEqual(
            len([key for key in receipts if key.startswith("p300_tier3_")]),
            len(identity.tier3_materials(ROOT)),
        )
        args = process_adapter.parse_args([])
        self.assertTrue(
            all(
                "s22plus_fyg8_p300" in value.as_posix()
                for value in (args.candidate_static, args.candidate_ap, args.out)
            )
        )

    def test_ready_manifest_uses_campaign_and_attempt_as_sidecar_ids(self) -> None:
        run_id = "12" * 16
        run_manifest = {
            "profile": "E2",
            "run_id": run_id,
            "source_contract_id": contract.CONTRACT_ID,
            "decoder": decoder.DECODER_ID,
            "policy_id": decoder.POLICY_ID,
            "records": {
                "long_family_hex": decoder.model.LONG_FAMILY.hex(),
                "unsat_family_hex": decoder.model.UNSAT_FAMILY.hex(),
                "terminal_stage": evidence._latest_stage_terminal(decoder, "E2"),
            },
            "observation_contract": {
                "minimum_success_count": 1,
                "clean_baseline_required": True,
            },
        }
        paths = {
            name: ROOT / f"workspace/private/p300-{name}.json"
            for name in ("candidate_static", "run_manifest", "static_check")
        }
        receipts = {
            name: {"size": index + 1, "sha256": f"{index + 1:064x}"}
            for index, name in enumerate(paths)
        }
        candidate = {
            "path": "workspace/private/p300/AP.tar.md5",
            "size": 10,
            "sha256": "a" * 64,
        }
        manifest = ready_manifest.derive_manifest(
            root=ROOT,
            run_manifest=run_manifest,
            evidence_paths=paths,
            evidence_receipts=receipts,
            candidate_ap=candidate,
            rollback_ap={**candidate, "sha256": "b" * 64},
            target_profile=ROOT / ready_manifest.DEFAULT_TARGET_PROFILE,
            manifest_id=ready_manifest.DEFAULT_MANIFEST_ID,
            live_run_id=ready_manifest.DEFAULT_LIVE_RUN_ID,
            timeout_sec=ready_manifest.DEFAULT_TIMEOUT_SEC,
        )
        bundle = process_v2.Bundle({}, manifest, {}, "c" * 64)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "workspace/private/runs/p300"
            run_dir.mkdir(parents=True)
            binding = live._p300_usb_binding_value(  # noqa: SLF001
                root, bundle, run_dir, "d" * 64
            )
        self.assertEqual(binding["campaign_id"], manifest["manifest_id"])
        self.assertEqual(binding["attempt_id"], manifest["run_id"])
        self.assertEqual(binding["candidate_ap"], {"size": 10, "sha256": "a" * 64})

    def test_sidecar_capture_directory_is_receipt_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "workspace/private/runs/p300/host-usb-trace"
            output.mkdir(parents=True)

            def write(name: str, payload: bytes) -> dict[str, object]:
                path = output / name
                path.write_bytes(payload)
                return {
                    "name": name,
                    "size": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }

            binding = usb_binding.create_binding(
                campaign_id="p300-campaign-1",
                attempt_id="attempt-1",
                candidate_ap={"sha256": "2" * 64, "size": 4096},
                approval_binding_sha256="1" * 64,
                transaction_path="workspace/private/runs/p300/transaction",
                sidecar_result_path=(
                    "workspace/private/runs/p300/host-usb-trace/result.json"
                ),
                observation_witness_path=(
                    "workspace/private/runs/p300/observation-durable.json"
                ),
            )
            owner_sha256 = usb_binding.owner_token_sha256(binding)
            started = "2026-08-04T00:00:01Z"
            start = {
                "schema": sidecar.SCHEMA,
                "phase": "start",
                "started_utc": started,
                "non_authoritative": True,
                "device_actions": False,
                "opens_candidate_acm": False,
                "owner_token_sha256": owner_sha256,
            }
            armed = {
                "schema": sidecar.SCHEMA,
                "phase": "armed",
                "armed_utc": "2026-08-04T00:00:01.100000Z",
                "owner_token_sha256": owner_sha256,
                "process_group_id": 9001,
                "session_id": 9001,
                "non_authoritative": True,
                "device_actions": False,
                "opens_candidate_acm": False,
                "sources": {
                    name: {
                        "pid": 9100 + index,
                        "process_group_id": 9001,
                        "session_id": 9001,
                        "alive": True,
                        "started_utc": started,
                    }
                    for index, name in enumerate(sidecar.SOURCE_COMMANDS)
                },
            }
            supporting = {
                "start": write("start.json", json.dumps(start).encode()),
                "armed": write("armed.json", json.dumps(armed).encode()),
                "lsusb_start": write("lsusb-start.json", b"{}\n"),
                "lsusb_end": write("lsusb-end.json", b"{}\n"),
            }
            sources = {}
            for name, command in sidecar.SOURCE_COMMANDS.items():
                payload = f"source={name}\n".encode()
                receipt = write(f"{name}.log", payload)
                sources[name] = {
                    "command": list(command),
                    "returncode": -15,
                    "bytes": receipt["size"],
                    "sha256": receipt["sha256"],
                    "truncated": False,
                    "error_type": None,
                    "started_utc": started,
                    "ended_utc": "2026-08-04T00:00:05.600000Z",
                    "alive_at_arm": True,
                    "alive_before_stop": True,
                    "stop_requested_utc": "2026-08-04T00:00:05.500000Z",
                }
            result = {
                "schema": sidecar.SCHEMA,
                "phase": "complete",
                "started_utc": started,
                "ended_utc": "2026-08-04T00:00:06Z",
                "elapsed_sec": 5.0,
                "requested_duration_sec": 900,
                "stop_reason": "signal:SIGTERM",
                "non_authoritative": True,
                "device_actions": False,
                "opens_candidate_acm": False,
                "contains_private_usb_identifiers": True,
                "public_raw_export_forbidden": True,
                "owner_token_sha256": owner_sha256,
                "process_group_id": 9001,
                "session_id": 9001,
                "supporting": supporting,
                "sources": sources,
            }
            (output / "result.json").write_text(json.dumps(result))
            proof = usb_binding.verify_capture_directory(
                binding, result, root=root, output_dir=output
            )
            self.assertTrue(proof["integrity_clean"])
            (output / "kernel.log").write_bytes(b"changed")
            with self.assertRaises(usb_binding.BindingError):
                usb_binding.verify_capture_directory(
                    binding, result, root=root, output_dir=output
                )

    def test_live_sidecar_session_covers_the_candidate_window(self) -> None:
        script_source = textwrap.dedent(
            """
            import argparse, hashlib, json, os, signal, time
            from datetime import datetime, timezone
            from pathlib import Path

            def now():
                return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")

            parser = argparse.ArgumentParser()
            parser.add_argument("--output-dir", type=Path, required=True)
            parser.add_argument("--duration-sec")
            args = parser.parse_args()
            args.output_dir.mkdir()

            def write(name, payload):
                path = args.output_dir / name
                path.write_bytes(payload)
                return {"name": name, "size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}

            started = now()
            owner = os.environ["S22PLUS_P300_USB_TRACE_OWNER"]
            owner_sha256 = hashlib.sha256(owner.encode()).hexdigest()
            group = os.getpgrp()
            session = os.getsid(0)
            start = {"schema": "device_action_usb_trace_sidecar_v1", "phase": "start", "started_utc": started, "owner_token_sha256": owner_sha256, "non_authoritative": True, "device_actions": False, "opens_candidate_acm": False}
            source_arms = {
                name: {"pid": os.getpid(), "process_group_id": group, "session_id": session, "alive": True, "started_utc": started}
                for name in ("kernel", "udev")
            }
            armed = {"schema": "device_action_usb_trace_sidecar_v1", "phase": "armed", "armed_utc": now(), "owner_token_sha256": owner_sha256, "process_group_id": group, "session_id": session, "non_authoritative": True, "device_actions": False, "opens_candidate_acm": False, "sources": source_arms}
            supporting = {
                "start": write("start.json", json.dumps(start).encode()),
                "armed": write("armed.json", json.dumps(armed).encode()),
                "lsusb_start": write("lsusb-start.json", b"{}\\n"),
            }
            logs = {
                "kernel": write("kernel.log", b"synthetic kernel usb\\n"),
                "udev": write("udev.log", b"synthetic udev usb\\n"),
            }
            stopped = False
            def stop(_signum, _frame):
                global stopped
                stopped = True
            signal.signal(signal.SIGTERM, stop)
            while not stopped:
                time.sleep(0.01)
            stop_requested = now()
            supporting["lsusb_end"] = write("lsusb-end.json", b"{}\\n")
            source_ended = now()
            sources = {
                name: {"command": [f"/synthetic/{name}"], "returncode": -15, "bytes": item["size"], "sha256": item["sha256"], "truncated": False, "error_type": None, "started_utc": started, "ended_utc": source_ended, "alive_at_arm": True, "alive_before_stop": True, "stop_requested_utc": stop_requested}
                for name, item in logs.items()
            }
            result = {
                "schema": "device_action_usb_trace_sidecar_v1",
                "phase": "complete",
                "started_utc": started,
                "ended_utc": now(),
                "elapsed_sec": 0.1,
                "requested_duration_sec": 900,
                "stop_reason": "signal:SIGTERM",
                "non_authoritative": True,
                "device_actions": False,
                "opens_candidate_acm": False,
                "contains_private_usb_identifiers": True,
                "public_raw_export_forbidden": True,
                "owner_token_sha256": owner_sha256,
                "process_group_id": group,
                "session_id": session,
                "supporting": supporting,
                "sources": sources,
            }
            write("result.json", json.dumps(result).encode())
            """
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "workspace/private/runs/p300"
            run_dir.mkdir(parents=True)
            fake = root / "fake-sidecar.py"
            fake.write_text(script_source)
            original_file = sidecar.__file__
            original_commands = sidecar.SOURCE_COMMANDS
            sidecar.__file__ = str(fake)
            sidecar.SOURCE_COMMANDS = {
                "kernel": ("/synthetic/kernel",),
                "udev": ("/synthetic/udev",),
            }
            try:
                manifest = {
                    "manifest_id": "p300-campaign-1",
                    "run_id": "p300-attempt-1",
                    "candidate_ap": {"size": 4096, "sha256": "2" * 64},
                    "observation": {
                        "timeout_sec": 300,
                        "acceptance": {
                            "source_contract_id": contract.CONTRACT_ID
                        },
                    },
                }
                bundle = process_v2.Bundle({}, manifest, {}, "3" * 64)
                approval = "1" * 64
                binding = live._p300_usb_binding_value(  # noqa: SLF001
                    root, bundle, run_dir, approval
                )
                binding_path = run_dir / "p300-usb-trace-binding.json"
                binding_payload = json.dumps(binding).encode()
                binding_path.write_bytes(binding_payload)
                binding_receipt = {
                    "path": str(binding_path),
                    "size": len(binding_payload),
                    "sha256": hashlib.sha256(binding_payload).hexdigest(),
                }
                prepared = live.PreparedRun(
                    root,
                    run_dir,
                    bundle,
                    {
                        "approval_binding_sha256": approval,
                        "p300_usb_trace_binding": binding_receipt,
                    },
                    {},
                )
                journal = process_v2.Journal.create(
                    run_dir / "transaction", approval
                )
                journal.event("live_session_start")
                journal.transition("APPROVED", "test", {})
                session = live._P300UsbTraceSession(  # noqa: SLF001
                    prepared, journal
                )
                session.start()
                journal.transition("DOWNLOAD_IDENTIFIED", "test", {})
                journal.event("candidate_flash_start", {"attempt": 1})
                journal.transition("CANDIDATE_FLASHED", "test", {})
                journal.event("candidate_flash_done")
                current = live._state(prepared)  # noqa: SLF001
                live._save_state(prepared, current)  # noqa: SLF001
                live._write_p300_observation_witness(  # noqa: SLF001
                    prepared, current
                )
                journal.transition("OBSERVED", "test", {})
                session.close()
                journal.event("candidate_boot_ready")
                session.finalize()
                state = live._state(prepared)  # noqa: SLF001
                self.assertEqual(
                    state["p300_usb_trace"]["status"], "verified"
                )
                live._validate_p300_usb_trace_state(  # noqa: SLF001
                    prepared, state, journal.records()
                )
            finally:
                sidecar.__file__ = original_file
                sidecar.SOURCE_COMMANDS = original_commands

    def test_interrupted_sidecar_process_group_is_reaped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "workspace/private/runs/p300"
            run_dir.mkdir(parents=True)
            approval = "1" * 64
            binding = usb_binding.create_binding(
                campaign_id="p300-campaign-1",
                attempt_id="attempt-1",
                candidate_ap={"sha256": "2" * 64, "size": 4096},
                approval_binding_sha256=approval,
                transaction_path="workspace/private/runs/p300/transaction",
                sidecar_result_path=(
                    "workspace/private/runs/p300/host-usb-trace/result.json"
                ),
                observation_witness_path=(
                    "workspace/private/runs/p300/observation-durable.json"
                ),
            )
            (run_dir / "p300-usb-trace-binding.json").write_text(
                json.dumps(binding)
            )
            bundle = process_v2.Bundle({}, {"observation": {}}, {}, "3" * 64)
            prepared = live.PreparedRun(
                root,
                run_dir,
                bundle,
                {"approval_binding_sha256": approval},
                {},
            )
            owner_path = live._p300_process_owner_path(prepared)  # noqa: SLF001
            owner_path.write_text(
                json.dumps(
                    live._p300_process_owner_value(  # noqa: SLF001
                        prepared, binding
                    )
                )
            )
            token = live._p300_owner_token(binding)  # noqa: SLF001
            script = (
                "import os,subprocess,sys,time; "
                "subprocess.Popen([sys.executable,'-c',"
                "'import time;time.sleep(60)'],env=os.environ.copy()); "
                "time.sleep(60)"
            )
            process = subprocess.Popen(
                [sys.executable, "-c", script],
                env={
                    "LC_ALL": "C",
                    "PATH": "/usr/bin:/bin",
                    sidecar.OWNER_ENV: token,
                },
                start_new_session=True,
            )
            try:
                identity = live._proc_identity(process.pid)  # noqa: SLF001
                self.assertIsNotNone(identity)
                owner_path.write_text(
                    json.dumps(
                        live._p300_process_owner_value(  # noqa: SLF001
                            prepared, binding, identity
                        )
                    )
                )
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    if len(live._p300_owned_processes(token)) >= 2:  # noqa: SLF001
                        break
                    time.sleep(0.05)
                self.assertGreaterEqual(
                    len(live._p300_owned_processes(token)),  # noqa: SLF001
                    2,
                )
                owner_receipt, cleanup = (
                    live._p300_recovery_process_cleanup(  # noqa: SLF001
                        prepared
                    )
                )
                process.wait(timeout=5)
                self.assertIsNotNone(owner_receipt)
                self.assertTrue(cleanup["verified"])
                self.assertEqual(cleanup["matching_processes_after"], 0)
                self.assertFalse(
                    live._p300_owned_processes(token)  # noqa: SLF001
                )
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, 9)
                    process.wait(timeout=5)

    def test_sidecar_faults_do_not_block_mandatory_rollback(self) -> None:
        for fault in ("witness", "close"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                run_dir = root / "workspace/private/runs/p300"
                run_dir.mkdir(parents=True)
                health = {
                    "android_boot_completed": True,
                    "boot_animation_stopped": True,
                    "verified_boot_state": "orange",
                    "root_required": True,
                    "boot_sha256": "a" * 64,
                    "supporting_partition_sha256": {
                        "vendor_boot": "b" * 64,
                        "dtbo": "c" * 64,
                        "recovery": "d" * 64,
                    },
                    "odin_endpoint_absent": True,
                }
                profile = {
                    "profile_id": "fixture-profile",
                    "target": {
                        "model": "SM-S906N",
                        "device": "g0q",
                        "firmware_incremental": "S906NKSS7FYG8",
                    },
                    "start_health": health,
                    "final_health": health,
                }
                manifest = {
                    "manifest_id": "p300-campaign-1",
                    "run_id": f"p300-{fault}-attempt",
                    "status": "ready-for-f1-approval",
                    "candidate_ap": {"sha256": "9" * 64, "size": 4096},
                    "observation": {
                        "timeout_sec": 1,
                        "acceptance": {
                            "source_contract_id": contract.CONTRACT_ID,
                            "source": "/proc/last_kmsg",
                            "marker": "[[FIXTURE|phase=PID1]]",
                            "family": "[[FIXTURE|",
                            "exact_count": 1,
                        },
                    },
                }
                bundle = process_v2.Bundle(profile, manifest, {}, "e" * 64)
                approval = "f" * 64
                binding = live._p300_usb_binding_value(  # noqa: SLF001
                    root, bundle, run_dir, approval
                )
                binding_path = run_dir / "p300-usb-trace-binding.json"
                binding_path.write_text(json.dumps(binding))
                prepared = live.PreparedRun(
                    root,
                    run_dir,
                    bundle,
                    {
                        "approval_binding_sha256": approval,
                        "p300_usb_trace_binding": live._receipt(  # noqa: SLF001
                            binding_path, "fixture binding"
                        ),
                    },
                    {
                        "schema": live.PRIVATE_TARGET_SCHEMA,
                        "serial": "s",
                        "topology": "usb:1-1",
                    },
                )
                backend = FakeBackend(live)

                def start_without_process(session):
                    session.binding = usb_binding.verify_binding(binding)
                    session.owner_token = live._p300_owner_token(  # noqa: SLF001
                        session.binding
                    )

                def injected_failure(*_args, **_kwargs):
                    raise process_v2.F1V2Error("injected sidecar receipt failure")

                with contextlib.ExitStack() as stack:
                    stack.enter_context(
                        mock.patch.object(
                            live._P300UsbTraceSession,  # noqa: SLF001
                            "start",
                            new=start_without_process,
                        )
                    )
                    if fault == "witness":
                        stack.enter_context(
                            mock.patch.object(
                                live,
                                "_write_p300_observation_witness",
                                new=injected_failure,
                            )
                        )
                    else:
                        stack.enter_context(
                            mock.patch.object(
                                live._P300UsbTraceSession,  # noqa: SLF001
                                "_close_impl",
                                new=injected_failure,
                            )
                        )
                    result = live.execute_prepared(
                        prepared, prepared.approval_token, backend
                    )
                self.assertEqual(result["current_state"], "CLOSED")
                self.assertEqual(
                    result["live_state"]["p300_usb_trace"]["status"],
                    "unknown",
                )
                self.assertTrue(
                    result["live_state"]["p300_usb_trace"][
                        "device_result_authoritative"
                    ]
                )
                self.assertEqual(
                    [
                        call
                        for call in backend.calls
                        if call.startswith("transfer-")
                    ],
                    ["transfer-candidate", "transfer-rollback"],
                )

    def test_failure_allocation_is_exact_and_disjoint(self) -> None:
        self.assertEqual(set(spec.NEW_FAILURE_DETAIL_NAMES), set(range(0xF73, 0xF80)))
        self.assertTrue(
            set(spec.NEW_FAILURE_DETAIL_NAMES).isdisjoint(range(0xF80, 0x1000))
        )


if __name__ == "__main__":
    unittest.main()
