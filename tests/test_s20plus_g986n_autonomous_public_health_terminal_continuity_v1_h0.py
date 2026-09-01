from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path
import re
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_terminal_continuity_v1_h0.py"
)
PHASE_A_SOURCE = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_campaign_v1.py"
)
RUNTIME_SOURCE = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_runtime_v1_h0.py"
)
LOADER_SOURCE = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_recovery_loader_v1_h0.py"
)
CORE_SOURCE = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_autonomous_public_health_recovery_v1_finalizer_h0.py"
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load test module {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CONTINUITY = load_module(SOURCE, "_s20plus_terminal_continuity_v1_test")
PHASE_A = CONTINUITY._load_phase_a()


def fixture_tool(phase):
    return {
        "path": phase.ADB_PATH,
        "device": 41,
        "inode": 42,
        "mtime_ns": 43,
        "size": phase.ADB_SIZE,
        "sha256": phase.ADB_SHA256,
    }


def fixture_server(phase, tool, *, socket_inode=51, pid_start_ticks=53):
    return {
        "schema": phase.ADB_SERVER_RECEIPT_SCHEMA,
        "socket_spec": phase.ADB_SERVER_SOCKET,
        "socket_inode": socket_inode,
        "pid": 52,
        "pid_start_ticks": pid_start_ticks,
        "uid": os.getuid(),
        "pidfd_held": True,
        "continuous_identity_checks": True,
        "executable": tool,
        "provenance_proven": True,
    }


def fixture_recovery_binding(phase):
    return {
        "schema": "s20plus_g986n_autonomous_public_health_recovery_precursors_v1",
        "status": "PHASE_A_QUALIFIED_PRECURSORS_NOT_OPERATIONAL",
        "binding_complete": False,
        "phase_b_exact_binding_required": True,
        "loader": {
            "name": phase.EXPECTED_LOADER_NAME,
            "size": phase.EXPECTED_LOADER_SIZE,
            "sha256": phase.EXPECTED_LOADER_SHA256,
            "normalized_sha256": phase.EXPECTED_LOADER_NORMALIZED_SHA256,
        },
        "core": {
            "name": phase.EXPECTED_CORE_NAME,
            "size": phase.EXPECTED_CORE_SIZE,
            "sha256": phase.EXPECTED_CORE_SHA256,
            "normalized_sha256": phase.EXPECTED_CORE_NORMALIZED_SHA256,
        },
        "manifest": {
            "name": phase.EXPECTED_MANIFEST_NAME,
            "size": phase.EXPECTED_MANIFEST_SIZE,
            "sha256": phase.EXPECTED_MANIFEST_SHA256,
        },
    }


def fixture_clock(phase):
    return {
        "schema": phase.CLOCK_BINDING_SCHEMA,
        "host_boot_id_sha256": "8" * 64,
        "realtime_origin_ns": 1_700_000_000_000_000_000,
        "boottime_origin_ns": 10_000_000_000,
        "monotonic_origin_ns": 9_000_000_000,
        "logical_origin_sec": 1_700_000_000,
        "caller_supplied_time": False,
    }


def fixture_clock_sample(phase, clock, delta_seconds=6):
    delta = delta_seconds * 1_000_000_000
    return {
        "schema": phase.CLOCK_SAMPLE_SCHEMA,
        "host_boot_id_sha256": clock["host_boot_id_sha256"],
        "realtime_ns": clock["realtime_origin_ns"] + delta,
        "boottime_ns": clock["boottime_origin_ns"] + delta,
        "monotonic_ns": clock["monotonic_origin_ns"] + delta,
        "logical_sec": clock["logical_origin_sec"] + delta_seconds,
        "projection_skew_ns": 0,
        "reversed": False,
    }


def fixture_properties(phase):
    properties = {key: "observed" for key in phase.PROPERTY_KEYS}
    properties.update(
        {
            "model": phase.TARGET["model"],
            "device": phase.TARGET["device"],
            "product_name": phase.TARGET["product"],
            "build_product": phase.TARGET["device"],
            "incremental": phase.TARGET["build"],
            "fingerprint": (
                "samsung/y2qksx/y2q:13/TP1A.220624.014/"
                "G986NKSS8IYC2:user/release-keys"
            ),
            "boot_completed": "1",
            "bootanim": "stopped",
            "selinux": "Enforcing",
            "shell_identity": (
                "uid=2000(shell) gid=2000(shell) groups=2000(shell),1003(graphics)"
            ),
            "boot_id": "12345678-1234-1234-1234-123456789abc",
        }
    )
    return properties


def complete_base_model(*, socket_inode=51, pid_start_ticks=53):
    phase = PHASE_A
    serial = "RFCM0000000"
    devpath = "usb:1-2.3"
    tool = fixture_tool(phase)
    server = fixture_server(
        phase,
        tool,
        socket_inode=socket_inode,
        pid_start_ticks=pid_start_ticks,
    )
    clock = fixture_clock(phase)
    intent = phase.model_opening_intent(
        campaign_id="a" * 32,
        session_id="b" * 32,
        created_at=clock["logical_origin_sec"],
        activation_binding_candidate_sha256="c" * 64,
        producer_binding={
            "schema": (
                "s20plus_g986n_autonomous_public_health_campaign_v1_runner_binding"
            ),
            "status": "BOUND",
            "normalized_sha256": phase.EXPECTED_SELF_NORMALIZED_SHA256,
            "binding_complete": True,
        },
        recovery_binding=fixture_recovery_binding(phase),
        clock_binding=clock,
        adb_client=tool,
        adb_server=server,
    )
    intent_raw = phase.canonical_bytes(intent)
    snapshot_values = fixture_properties(phase)
    snapshot = (
        "\n".join(f"{key}={snapshot_values[key]}" for key in phase.PROPERTY_KEYS)
        + "\n"
    ).encode()
    inventory = (
        b"List of devices attached\n"
        + serial.encode()
        + b" device usb:1-2.3 product:y2qksx model:SM_G986N device:y2q\n"
    )
    outputs = (
        b"adb-version\n",
        inventory,
        devpath.encode() + b"\n",
        snapshot,
        snapshot,
        inventory,
    )
    evidence = {}
    receipts = []
    predecessor = phase.sha256_bytes(intent_raw)
    for ordinal, stdout in enumerate(outputs, 1):
        receipt = phase.model_opening_command_receipt(
            intent=intent,
            ordinal=ordinal,
            serial=serial,
            predecessor_sha256=predecessor,
            stdout=stdout,
            stderr=b"",
            started_at=clock["logical_origin_sec"] + ordinal,
            completed_at=clock["logical_origin_sec"] + ordinal,
            retained_at=clock["logical_origin_sec"] + ordinal,
            published_at=clock["logical_origin_sec"] + ordinal,
        )
        receipt_raw = phase.canonical_bytes(receipt)
        evidence[f"cmd-{ordinal:02d}.stdout.bin"] = stdout
        evidence[f"cmd-{ordinal:02d}.stderr.bin"] = b""
        evidence[f"cmd-{ordinal:02d}.receipt.json"] = receipt_raw
        receipts.append(receipt)
        predecessor = phase.sha256_bytes(receipt_raw)
    health = phase._derive_health_from_validated_returns(evidence, receipts, serial)
    evidence["health.json"] = phase.canonical_bytes(health)
    derived_identity = {
        "target": dict(phase.TARGET),
        "serial_sha256": phase.sha256_bytes(serial.encode()),
        "topology_sha256": phase.sha256_bytes(devpath.encode()),
        "boot_id_sha256": health["boot_id_sha256"],
        "health_verdict": phase.HEALTH_VERDICT,
    }
    usb = {
        "schema": phase.USB_GENERATION_SCHEMA,
        "topology_sha256": derived_identity["topology_sha256"],
        "sysfs_device": 60,
        "sysfs_inode": 61,
        "busnum": 1,
        "devnum": 2,
        "usbfs_device": 62,
        "usbfs_inode": 63,
        "usbfs_rdev": 48_385,
        "held_descriptors": True,
        "event_monitor_overflow": False,
        "generation_continuous": True,
    }
    return {
        "serial": serial,
        "devpath": devpath,
        "boot_id": snapshot_values["boot_id"],
        "intent": intent,
        "intent_raw": intent_raw,
        "base_evidence": evidence,
        "clock_sample": fixture_clock_sample(phase, clock),
        "server": server,
        "usb": usb,
        "derived_identity": derived_identity,
    }


def adapt(model):
    evidence = CONTINUITY.model_terminal_continuity_evidence(
        intent_raw=model["intent_raw"],
        base_evidence=model["base_evidence"],
        clock_sample=model["clock_sample"],
        adb_server_after=model["server"],
        usb_generation=model["usb"],
    )
    return {**model, "evidence": evidence}


def mutate_receipt(model, ordinal, mutation):
    forged = dict(model["evidence"])
    name = f"cmd-{ordinal:02d}.receipt.json"
    receipt = json.loads(forged[name])
    mutation(receipt)
    forged[name] = CONTINUITY.canonical_bytes(receipt)
    return forged


def rechain_after(evidence, ordinal):
    forged = dict(evidence)
    predecessor = hashlib.sha256(
        forged[f"cmd-{ordinal:02d}.receipt.json"]
    ).hexdigest()
    for successor_ordinal in range(ordinal + 1, 7):
        name = f"cmd-{successor_ordinal:02d}.receipt.json"
        receipt = json.loads(forged[name])
        receipt["predecessor_sha256"] = predecessor
        forged[name] = CONTINUITY.canonical_bytes(receipt)
        predecessor = hashlib.sha256(forged[name]).hexdigest()
    return forged


class TerminalContinuityV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = adapt(complete_base_model())

    def derive(self, evidence=None, intent_raw=None):
        return CONTINUITY.model_recovery_input_envelope(
            intent_raw=self.model["intent_raw"] if intent_raw is None else intent_raw,
            evidence=self.model["evidence"] if evidence is None else evidence,
        )

    def assert_rejected(self, evidence, pattern=None):
        context = (
            self.assertRaises(CONTINUITY.TerminalContinuityV1Error)
            if pattern is None
            else self.assertRaisesRegex(CONTINUITY.TerminalContinuityV1Error, pattern)
        )
        with context:
            self.derive(evidence=evidence)

    def test_render_only_status_and_all_gates_false(self):
        plan = CONTINUITY.render_plan()
        self.assertEqual(
            plan["status"],
            "H0_AUTONOMOUS_PUBLIC_HEALTH_TERMINAL_CONTINUITY_V1_MODEL_PASS_GO_NOT_ACTIVE",
        )
        self.assertEqual(plan["cli"], ["--render-plan"])
        self.assertFalse(any(plan["gates"].values()))
        self.assertEqual(plan["device_commands"], [])
        self.assertEqual(plan["subprocesses"], [])
        self.assertEqual(plan["sockets"], [])
        self.assertEqual(
            plan["pin_verification_boundary"][
                "actual_source_hash_and_normalized_load_on_model_call"
            ],
            ["phase_a", "runtime"],
        )
        self.assertEqual(
            plan["pin_verification_boundary"]["declarative_only_not_opened_by_adapter"],
            ["recovery_loader", "recovery_core", "recovery_manifest"],
        )
        with self.assertRaisesRegex(CONTINUITY.TerminalContinuityV1Error, "inactive"):
            CONTINUITY.run_terminal_continuity_adapter()

    def test_cli_renders_and_rejects_every_other_surface(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.assertEqual(CONTINUITY.main(["--render-plan"]), 0)
        self.assertEqual(json.loads(stream.getvalue())["status"], CONTINUITY.STATUS)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            CONTINUITY.main([])

    def test_even_all_true_gates_reach_only_unimplemented_stub(self):
        patches = [mock.patch.object(CONTINUITY, name, True) for name in CONTINUITY.GATE_NAMES]
        for patcher in patches:
            patcher.start()
        try:
            with self.assertRaisesRegex(
                CONTINUITY.TerminalContinuityV1Error, "not implemented"
            ):
                CONTINUITY.run_terminal_continuity_adapter()
        finally:
            for patcher in reversed(patches):
                patcher.stop()

    def test_exact_pinned_raw_identities(self):
        paths = {
            "phase_a": PHASE_A_SOURCE,
            "runtime": RUNTIME_SOURCE,
            "recovery_loader": LOADER_SOURCE,
            "recovery_core": CORE_SOURCE,
        }
        for name, path in paths.items():
            with self.subTest(name=name):
                raw = path.read_bytes()
                pin = CONTINUITY.PINNED_IDENTITIES[name]
                self.assertEqual(len(raw), pin["size"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), pin["sha256"])
        self.assertEqual(
            PHASE_A.normalized_source_sha256(PHASE_A_SOURCE.read_bytes()),
            CONTINUITY.PINNED_IDENTITIES["phase_a"]["normalized_sha256"],
        )
        runtime = load_module(RUNTIME_SOURCE, "_s20plus_runtime_pin_test")
        loader = load_module(LOADER_SOURCE, "_s20plus_recovery_loader_pin_test")
        self.assertEqual(
            runtime.normalized_source_sha256(RUNTIME_SOURCE.read_bytes()),
            CONTINUITY.PINNED_IDENTITIES["runtime"]["normalized_sha256"],
        )
        self.assertEqual(
            loader.normalized_self_sha256(LOADER_SOURCE.read_bytes()),
            CONTINUITY.PINNED_IDENTITIES["recovery_loader"]["normalized_sha256"],
        )

    def test_recovery_manifest_pin_is_exact_phase_a_pin(self):
        pin = CONTINUITY.PINNED_IDENTITIES["recovery_manifest"]
        self.assertEqual(pin["name"], PHASE_A.EXPECTED_MANIFEST_NAME)
        self.assertEqual(pin["size"], PHASE_A.EXPECTED_MANIFEST_SIZE)
        self.assertEqual(pin["sha256"], PHASE_A.EXPECTED_MANIFEST_SHA256)

    def test_public_derivation_signatures_accept_no_caller_identity(self):
        signature = inspect.signature(CONTINUITY.model_recovery_input_envelope)
        self.assertEqual(tuple(signature.parameters), ("intent_raw", "evidence"))
        self.assertTrue(
            all(
                item.kind is inspect.Parameter.KEYWORD_ONLY
                for item in signature.parameters.values()
            )
        )
        validation = inspect.signature(CONTINUITY.validate_terminal_continuity_evidence)
        self.assertEqual(tuple(validation.parameters), ("intent_raw", "evidence"))
        for forbidden in ("serial", "clock", "usb", "time", "path"):
            self.assertNotIn(forbidden, tuple(signature.parameters))

    def test_ordinals_one_through_five_are_explicit_null_and_six_is_exact_object(self):
        for ordinal in range(1, 7):
            receipt = json.loads(self.model["evidence"][f"cmd-{ordinal:02d}.receipt.json"])
            self.assertIn("terminal_continuity", receipt)
            if ordinal < 6:
                self.assertIsNone(receipt["terminal_continuity"])
            else:
                self.assertEqual(
                    set(receipt["terminal_continuity"]),
                    CONTINUITY.TERMINAL_CONTINUITY_KEYS,
                )
                self.assertIs(
                    receipt["terminal_continuity"]["observed_after_return_retained"],
                    True,
                )
                self.assertEqual(
                    receipt["terminal_continuity"]["schema"],
                    CONTINUITY.TERMINAL_CONTINUITY_SCHEMA,
                )

    def test_terminal_object_retains_every_clock_server_and_usb_field(self):
        receipt = json.loads(self.model["evidence"]["cmd-06.receipt.json"])
        terminal = receipt["terminal_continuity"]
        self.assertEqual(terminal["clock_sample"], self.model["clock_sample"])
        self.assertEqual(terminal["adb_server_after"], self.model["server"])
        self.assertEqual(terminal["usb_generation"], self.model["usb"])
        self.assertEqual(
            set(terminal["clock_sample"]), set(self.model["clock_sample"])
        )
        self.assertEqual(
            set(terminal["adb_server_after"]), set(self.model["server"])
        )
        self.assertEqual(set(terminal["usb_generation"]), set(self.model["usb"]))
        self.assertEqual(terminal["usb_generation"]["usbfs_rdev"], 48_385)
        self.assertEqual(48_385, os.makedev(189, (1 - 1) * 128 + (2 - 1)))

    def test_every_stripped_receipt_passes_exact_phase_a_validator(self):
        serial = self.model["serial"]
        argvs = PHASE_A.expected_actual_argvs(serial)
        for ordinal, (template, argv) in enumerate(
            zip(PHASE_A.FIXED_TRANSCRIPT, argvs, strict=True), 1
        ):
            receipt = json.loads(
                self.model["evidence"][f"cmd-{ordinal:02d}.receipt.json"]
            )
            receipt.pop("terminal_continuity")
            PHASE_A.validate_opening_command_receipt(
                receipt, PHASE_A.canonical_bytes(receipt), template, argv
            )

    def test_predecessor_chain_hashes_extended_raw_bytes(self):
        predecessor = hashlib.sha256(self.model["intent_raw"]).hexdigest()
        base_predecessor = predecessor
        divergence_seen = False
        for ordinal in range(1, 7):
            raw = self.model["evidence"][f"cmd-{ordinal:02d}.receipt.json"]
            receipt = json.loads(raw)
            self.assertEqual(receipt["predecessor_sha256"], predecessor)
            base = dict(receipt)
            base.pop("terminal_continuity")
            predecessor = hashlib.sha256(raw).hexdigest()
            base_predecessor = hashlib.sha256(PHASE_A.canonical_bytes(base)).hexdigest()
            if ordinal < 6:
                next_receipt = json.loads(
                    self.model["evidence"][f"cmd-{ordinal + 1:02d}.receipt.json"]
                )
                divergence_seen |= next_receipt["predecessor_sha256"] != base_predecessor
        self.assertTrue(divergence_seen)

    def test_recovery_envelope_contains_only_hashed_device_identity(self):
        envelope = self.derive()
        raw = CONTINUITY.canonical_bytes(envelope)
        self.assertNotIn(self.model["serial"].encode(), raw)
        self.assertNotIn(self.model["devpath"].encode(), raw)
        self.assertNotIn(self.model["boot_id"].encode(), raw)
        self.assertEqual(
            envelope["selected_serial_sha256"],
            hashlib.sha256(self.model["serial"].encode()).hexdigest(),
        )
        self.assertEqual(
            envelope["derived_health_identity"], self.model["derived_identity"]
        )
        self.assertNotIn("foreign_guard_present", envelope["derived_health_identity"])
        self.assertIs(envelope["foreign_guard_absence_authenticated"], False)
        self.assertIs(envelope["source_identity_usable"], False)
        self.assertIs(envelope["runtime_owner_observation_verified"], False)

    def test_public_validation_exports_guardless_derived_identity_only(self):
        validated = CONTINUITY.validate_terminal_continuity_evidence(
            intent_raw=self.model["intent_raw"], evidence=self.model["evidence"]
        )
        self.assertEqual(
            validated["derived_health_identity"], self.model["derived_identity"]
        )
        self.assertNotIn("source_identity", validated)
        self.assertNotIn("foreign_guard_present", validated["derived_health_identity"])
        self.assertIs(validated["foreign_guard_absence_authenticated"], False)
        self.assertIs(validated["source_identity_usable"], False)
        self.assertIs(validated["runtime_owner_observation_verified"], False)

    def test_recovery_envelope_contains_exact_retained_proofs_and_hashes(self):
        envelope = self.derive()
        terminal = envelope["retained_terminal_continuity"]
        expected = {
            "clock_sample": self.model["clock_sample"],
            "adb_server_after": self.model["server"],
            "usb_generation": self.model["usb"],
        }
        for name, value in expected.items():
            with self.subTest(name=name):
                self.assertEqual(terminal[name], value)
                self.assertEqual(
                    terminal[f"{name}_sha256"],
                    hashlib.sha256(CONTINUITY.canonical_bytes(value)).hexdigest(),
                )
        self.assertIs(terminal["observed_after_return_retained"], True)

    def test_envelope_marks_every_missing_integration_and_authority_false(self):
        envelope = self.derive()
        for name in (
            "opening_result_integration",
            "campaign_binding_integration",
            "recovery_loader_integration",
            "caller_serial_accepted",
            "caller_clock_accepted",
            "caller_usb_accepted",
            "caller_time_accepted",
            "caller_path_accepted",
            "foreign_guard_absence_authenticated",
            "source_identity_usable",
            "runtime_owner_observation_verified",
            "device_commands_authorized",
            "live_authority",
        ):
            self.assertIs(envelope[name], False, name)

    def test_deterministic_envelope_and_exact_result_byte_identity(self):
        first = self.derive()
        second = self.derive()
        self.assertEqual(CONTINUITY.canonical_bytes(first), CONTINUITY.canonical_bytes(second))
        raw = CONTINUITY.canonical_bytes(first)
        self.assertEqual(
            CONTINUITY.validate_recovery_input_envelope(
                first,
                raw,
                intent_raw=self.model["intent_raw"],
                evidence=self.model["evidence"],
            ),
            first,
        )
        pretty = (json.dumps(first, sort_keys=True) + "\n").encode()
        with self.assertRaisesRegex(CONTINUITY.TerminalContinuityV1Error, "bytes differ"):
            CONTINUITY.validate_recovery_input_envelope(
                first,
                pretty,
                intent_raw=self.model["intent_raw"],
                evidence=self.model["evidence"],
            )
        with self.assertRaisesRegex(
            CONTINUITY.TerminalContinuityV1Error, "raw is not bytes"
        ):
            CONTINUITY.validate_recovery_input_envelope(
                first,
                bytearray(raw),
                intent_raw=self.model["intent_raw"],
                evidence=self.model["evidence"],
            )
        forged = dict(first)
        forged["live_authority"] = True
        with self.assertRaisesRegex(CONTINUITY.TerminalContinuityV1Error, "bytes differ"):
            CONTINUITY.validate_recovery_input_envelope(
                forged,
                CONTINUITY.canonical_bytes(forged),
                intent_raw=self.model["intent_raw"],
                evidence=self.model["evidence"],
            )

    def test_each_missing_evidence_node_and_extra_node_fail_closed(self):
        for name in PHASE_A.OPENING_EVIDENCE_NAMES:
            with self.subTest(missing=name):
                forged = dict(self.model["evidence"])
                forged.pop(name)
                self.assert_rejected(forged, "19-file")
        forged = dict(self.model["evidence"])
        forged["extra.json"] = b"{}\n"
        self.assert_rejected(forged, "19-file")

    def test_nonbytes_evidence_fails_closed(self):
        forged = dict(self.model["evidence"])
        forged["cmd-01.stdout.bin"] = "adb-version\n"
        self.assert_rejected(forged, "not bytes")

    def test_serial_is_rederived_only_from_cmd02(self):
        forged = dict(self.model["evidence"])
        forged["cmd-02.stdout.bin"] = forged["cmd-02.stdout.bin"].replace(
            b"RFCM0000000", b"RFCT0000000"
        )
        receipt = json.loads(forged["cmd-02.receipt.json"])
        receipt["stdout_size"] = len(forged["cmd-02.stdout.bin"])
        receipt["stdout_sha256"] = hashlib.sha256(
            forged["cmd-02.stdout.bin"]
        ).hexdigest()
        forged["cmd-02.receipt.json"] = CONTINUITY.canonical_bytes(receipt)
        forged = rechain_after(forged, 2)
        self.assert_rejected(forged)

    def test_each_raw_stream_hash_is_authenticated(self):
        for ordinal in range(1, 7):
            for stream in ("stdout", "stderr"):
                with self.subTest(ordinal=ordinal, stream=stream):
                    forged = dict(self.model["evidence"])
                    name = f"cmd-{ordinal:02d}.{stream}.bin"
                    forged[name] += b"x"
                    self.assert_rejected(forged)

    def test_cmd06_inventory_drift_fails_closed(self):
        forged = dict(self.model["evidence"])
        forged["cmd-06.stdout.bin"] = forged["cmd-06.stdout.bin"].replace(
            b"usb:1-2.3", b"usb:1-2.4"
        )
        receipt = json.loads(forged["cmd-06.receipt.json"])
        receipt["stdout_size"] = len(forged["cmd-06.stdout.bin"])
        receipt["stdout_sha256"] = hashlib.sha256(forged["cmd-06.stdout.bin"]).hexdigest()
        forged["cmd-06.receipt.json"] = CONTINUITY.canonical_bytes(receipt)
        self.assert_rejected(forged)

    def test_cmd03_devpath_is_authenticated(self):
        forged = dict(self.model["evidence"])
        forged["cmd-03.stdout.bin"] = b"usb:1-2.4\n"
        receipt = json.loads(forged["cmd-03.receipt.json"])
        receipt["stdout_size"] = len(forged["cmd-03.stdout.bin"])
        receipt["stdout_sha256"] = hashlib.sha256(forged["cmd-03.stdout.bin"]).hexdigest()
        forged["cmd-03.receipt.json"] = CONTINUITY.canonical_bytes(receipt)
        forged = rechain_after(forged, 3)
        self.assert_rejected(forged, "raw returns or health")

    def test_both_snapshot_returns_are_authenticated(self):
        for ordinal in (4, 5):
            with self.subTest(ordinal=ordinal):
                forged = dict(self.model["evidence"])
                name = f"cmd-{ordinal:02d}.stdout.bin"
                forged[name] = forged[name].replace(b"sdk=observed", b"sdk=35")
                receipt_name = f"cmd-{ordinal:02d}.receipt.json"
                receipt = json.loads(forged[receipt_name])
                receipt["stdout_size"] = len(forged[name])
                receipt["stdout_sha256"] = hashlib.sha256(forged[name]).hexdigest()
                forged[receipt_name] = CONTINUITY.canonical_bytes(receipt)
                forged = rechain_after(forged, ordinal)
                self.assert_rejected(forged, "raw returns or health")

    def test_health_bytes_are_authenticated(self):
        forged = dict(self.model["evidence"])
        health = json.loads(forged["health.json"])
        health["properties"]["sdk"] = "35"
        forged["health.json"] = CONTINUITY.canonical_bytes(health)
        self.assert_rejected(forged, "health")

    def test_predecessor_forgery_fails_closed(self):
        forged = mutate_receipt(
            self.model, 4, lambda receipt: receipt.__setitem__("predecessor_sha256", "f" * 64)
        )
        self.assert_rejected(forged, "predecessor")

    def test_stripped_base_receipt_must_pass_exact_phase_a_validator(self):
        forged = mutate_receipt(
            self.model, 3, lambda receipt: receipt.__setitem__("returncode", 1)
        )
        self.assert_rejected(forged, "stripped Phase-A")

    def test_continuity_presence_rules_fail_closed(self):
        forged = mutate_receipt(
            self.model,
            2,
            lambda receipt: receipt.__setitem__(
                "terminal_continuity",
                json.loads(self.model["evidence"]["cmd-06.receipt.json"])[
                    "terminal_continuity"
                ],
            ),
        )
        self.assert_rejected(forged, "1-5")
        forged = mutate_receipt(
            self.model, 6, lambda receipt: receipt.__setitem__("terminal_continuity", None)
        )
        self.assert_rejected(forged, "object is absent")

    def test_missing_or_extra_terminal_field_fails_closed(self):
        for field in CONTINUITY.TERMINAL_CONTINUITY_KEYS:
            with self.subTest(missing=field):
                forged = mutate_receipt(
                    self.model,
                    6,
                    lambda receipt, field=field: receipt["terminal_continuity"].pop(field),
                )
                self.assert_rejected(forged, "keys differ")
        forged = mutate_receipt(
            self.model,
            6,
            lambda receipt: receipt["terminal_continuity"].__setitem__("extra", False),
        )
        self.assert_rejected(forged, "keys differ")

    def test_terminal_schema_literal_is_required(self):
        forged = mutate_receipt(
            self.model,
            6,
            lambda receipt: receipt["terminal_continuity"].__setitem__(
                "schema", "wrong-terminal-continuity-schema"
            ),
        )
        self.assert_rejected(forged, "schema differs")

    def test_every_nested_proof_field_is_required(self):
        keys = {
            "clock_sample": self.model["clock_sample"],
            "adb_server_after": self.model["server"],
            "usb_generation": self.model["usb"],
        }
        for group, value in keys.items():
            for field in value:
                with self.subTest(group=group, missing=field):
                    forged = mutate_receipt(
                        self.model,
                        6,
                        lambda receipt, group=group, field=field: receipt[
                            "terminal_continuity"
                        ][group].pop(field),
                    )
                    self.assert_rejected(forged)

    def test_server_after_must_equal_intent_server(self):
        forged = mutate_receipt(
            self.model,
            6,
            lambda receipt: receipt["terminal_continuity"]["adb_server_after"].__setitem__(
                "pid_start_ticks", 54
            ),
        )
        self.assert_rejected(forged, "exact post-return")

    def test_clock_sample_must_equal_terminal_publication_time(self):
        forged = mutate_receipt(
            self.model,
            6,
            lambda receipt: (
                receipt["terminal_continuity"]["clock_sample"].__setitem__(
                    "logical_sec", receipt["receipt_published_at"] - 1
                ),
                receipt["terminal_continuity"]["clock_sample"].__setitem__(
                    "realtime_ns",
                    receipt["terminal_continuity"]["clock_sample"]["realtime_ns"]
                    - 1_000_000_000,
                ),
                receipt["terminal_continuity"]["clock_sample"].__setitem__(
                    "boottime_ns",
                    receipt["terminal_continuity"]["clock_sample"]["boottime_ns"]
                    - 1_000_000_000,
                ),
                receipt["terminal_continuity"]["clock_sample"].__setitem__(
                    "monotonic_ns",
                    receipt["terminal_continuity"]["clock_sample"]["monotonic_ns"]
                    - 1_000_000_000,
                ),
            ),
        )
        self.assert_rejected(forged, "exact post-return")

    def test_usb_generation_topology_must_equal_derived_source(self):
        forged = mutate_receipt(
            self.model,
            6,
            lambda receipt: receipt["terminal_continuity"]["usb_generation"].__setitem__(
                "topology_sha256", "f" * 64
            ),
        )
        self.assert_rejected(forged, "runtime-mapped")

    def test_usbfs_rdev_must_match_exact_runtime_mapping(self):
        forged = mutate_receipt(
            self.model,
            6,
            lambda receipt: receipt["terminal_continuity"]["usb_generation"].__setitem__(
                "usbfs_rdev", 48_386
            ),
        )
        self.assert_rejected(forged, "runtime-mapped")

    def test_usb_bus_and_device_bounds_are_exact(self):
        for field, value in (
            ("busnum", 0),
            ("busnum", 1_000),
            ("devnum", 0),
            ("devnum", 128),
        ):
            with self.subTest(field=field, value=value):
                forged = mutate_receipt(
                    self.model,
                    6,
                    lambda receipt, field=field, value=value: receipt[
                        "terminal_continuity"
                    ]["usb_generation"].__setitem__(field, value),
                )
                self.assert_rejected(forged, "outside reviewed mapping")

    def test_observed_after_return_retained_must_be_literal_true(self):
        forged = mutate_receipt(
            self.model,
            6,
            lambda receipt: receipt["terminal_continuity"].__setitem__(
                "observed_after_return_retained", False
            ),
        )
        self.assert_rejected(forged, "not retained after return")

    def test_receipt_exact_8k_boundary_accepts_and_one_byte_over_rejects(self):
        normal = complete_base_model(socket_inode=5, pid_start_ticks=5)
        normal_adapted = adapt(normal)
        normal_size = len(normal_adapted["evidence"]["cmd-06.receipt.json"])
        increase = CONTINUITY.EXTENDED_RECEIPT_MAX_BYTES - normal_size
        self.assertGreater(increase, 0)
        first_digits = min(4_000, 1 + increase)
        second_digits = 1 + increase - (first_digits - 1)
        self.assertLessEqual(second_digits, 4_000)
        exact = adapt(
            complete_base_model(
                socket_inode=int("9" * first_digits),
                pid_start_ticks=int("8" * second_digits),
            )
        )
        self.assertEqual(
            len(exact["evidence"]["cmd-06.receipt.json"]),
            CONTINUITY.EXTENDED_RECEIPT_MAX_BYTES,
        )
        over = complete_base_model(
            socket_inode=int("9" * first_digits),
            pid_start_ticks=int("8" * (second_digits + 1)),
        )
        with self.assertRaisesRegex(
            CONTINUITY.TerminalContinuityV1Error, "exceeds 8 KiB"
        ):
            adapt(over)

    def test_exact_phase_a_path_or_raw_identity_drift_fails_closed(self):
        with mock.patch.object(CONTINUITY, "PHASE_A_PATH", RUNTIME_SOURCE):
            with self.assertRaisesRegex(
                CONTINUITY.TerminalContinuityV1Error, "metadata differs"
            ):
                CONTINUITY._load_phase_a()

    def test_exact_runtime_path_or_raw_identity_drift_fails_closed(self):
        with mock.patch.object(CONTINUITY, "RUNTIME_PATH", PHASE_A_SOURCE):
            with self.assertRaisesRegex(
                CONTINUITY.TerminalContinuityV1Error, "metadata differs"
            ):
                CONTINUITY._load_runtime()

    def test_every_model_derivation_exact_loads_runtime(self):
        with mock.patch.object(
            CONTINUITY, "_load_runtime", wraps=CONTINUITY._load_runtime
        ) as load_runtime:
            self.derive()
        load_runtime.assert_called_once_with()

    def test_source_imports_no_subprocess_or_socket_and_names_no_device_backend(self):
        source = SOURCE.read_text()
        self.assertNotRegex(source, r"(?m)^import (?:subprocess|socket)$")
        self.assertNotRegex(source, r"(?m)^from (?:subprocess|socket) import")
        self.assertNotIn("validate_source_identity", source)
        plan = CONTINUITY.render_plan()
        for key in ("device_commands", "subprocesses", "sockets", "root_commands"):
            self.assertEqual(plan[key], [])

    def test_normalized_anchor_is_self_consistent_and_transition_stable(self):
        raw = SOURCE.read_bytes()
        self.assertEqual(
            CONTINUITY.normalized_source_sha256(raw),
            CONTINUITY.EXPECTED_SELF_NORMALIZED_SHA256,
        )
        transitioned, status_count = re.subn(
            rb'^STATUS = "H0_AUTONOMOUS_PUBLIC_HEALTH_TERMINAL_CONTINUITY_V1_MODEL_PASS_GO_NOT_ACTIVE"$',
            b'STATUS = "REVIEWED_NOT_ACTIVE"',
            raw,
            count=1,
            flags=re.MULTILINE,
        )
        self.assertEqual(status_count, 1)
        for name in CONTINUITY.GATE_NAMES:
            transitioned = re.sub(
                rf"^{name} = False$".encode(),
                f"{name} = True".encode(),
                transitioned,
                count=1,
                flags=re.MULTILINE,
            )
        self.assertEqual(
            CONTINUITY.normalized_source_sha256(transitioned),
            CONTINUITY.EXPECTED_SELF_NORMALIZED_SHA256,
        )


if __name__ == "__main__":
    unittest.main()
