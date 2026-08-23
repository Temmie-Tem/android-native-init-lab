from __future__ import annotations

import importlib.util
import json
import os
import re
import resource
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / "workspace/public/src/scripts/server-distro"
sys.path.insert(0, str(MODULE_DIR))
SOURCE = MODULE_DIR / "a90_boot_only_f1_adapter_v1.py"
SPEC = importlib.util.spec_from_file_location("a90_boot_only_f1_adapter_v1", SOURCE)
assert SPEC and SPEC.loader
A = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = A
SPEC.loader.exec_module(A)


BOOT_ID = "01234567-89ab-cdef-0123-456789abcdef"
QUALIFICATION = {
    "recovery": {
        "profile": "A90_ATTENDED_PHYSICAL_RECOVERY_V1",
        "method": "NATIVE_TO_STABLE_ADB_BASELINE_SINGLE_NEW_RECOVERY_ARRIVAL_BOOT_READBACK_V1",
        "demonstrated": True,
    },
    "recoveryIdentity": {"adbSerialSha256": "c" * 64},
    "review": {"path": "/tmp/review.json", "size": 1, "sha256": "a" * 64},
    "freshState": {
        "enablePath": "/cache/a90-auto-handoff-phase3-minimal-h27.enable",
        "latchPath": "/cache/a90-auto-handoff-phase3-minimal-h27.done",
    },
}


class FakeRunner:
    def __init__(self, results, log_directory=None):
        self.results = list(results)
        self.calls = []
        self.log_directory = log_directory

    def run(self, label, argv, timeout_sec):
        if re.fullmatch(r"[a-z0-9-]{1,40}", label) is None:
            raise A.ContractError("adapter log label is invalid")
        self.calls.append((label, argv, timeout_sec))
        return self.results.pop(0)


def result(value, *, rc=0, quiescent=True, stderr=b""):
    raw = value if isinstance(value, bytes) else json.dumps(value).encode()
    return A.CommandResult(rc, raw, stderr, quiescent)


def command(text, name):
    return {
        "begin": {"cmd": name},
        "end": {"cmd": name, "rc": "0", "status": "ok"},
        "rc": 0,
        "status": "ok",
        "trust": "A90P1_V1_STRUCTURAL_ONLY",
        "text": text,
    }


def absent_stat():
    return {
        "begin": {"cmd": "stat"},
        "end": {"cmd": "stat", "rc": "-2", "status": "error", "errno": "2"},
        "rc": -2,
        "status": "error",
        "trust": "A90P1_V1_STRUCTURAL_ONLY",
        "text": "not found",
    }


def bridge(*, ambiguous=False):
    capture_path = A.REPO_ROOT / "workspace/private/test-bridge.raw"
    command = [
        "/usr/bin/python3", str(A.SERIAL_BRIDGE),
        "--host", "127.0.0.1", "--port", "54321",
        "--device", A.FIXED_SERIAL, "--device-glob", A.FIXED_SERIAL,
        "--capture", str(capture_path), "--expect-realpath", "/dev/ttyACM0",
    ]
    return {
        "wrapper_contract": 1,
        "bridge_process": "running",
        "port_listening": True,
        "bridge_probe": "connected-no-immediate-error",
        "ambiguous": ambiguous,
        "serial_candidates": [
            {"path": A.FIXED_SERIAL, "realpath": "/dev/ttyACM0", "exists": True}
        ],
        "selected_device": A.FIXED_SERIAL,
        "selected_realpath": "/dev/ttyACM0",
        "metadata": {
            "command": command,
            "device": A.FIXED_SERIAL,
            "device_glob": A.FIXED_SERIAL,
            "effective_expect_realpath": "/dev/ttyACM0",
            "host": "127.0.0.1",
            "pid": 1234,
            "pin_selected_realpath": True,
            "port": 54321,
            "capture_path": "workspace/private/test-bridge.raw",
        },
        "listen_host": "127.0.0.1",
        "listen_port": 54321,
        "port_pids": [1234],
        "port_pid_source": "fd",
        "port_socket_inodes": ["98765"],
        "port_sockets": [{
            "address": "127.0.0.1",
            "inode": "98765",
            "port": 54321,
            "uid": 1000,
        }],
        "processes": [{
            "cmdline": " ".join(command),
            "managed": True,
            "pid": 1234,
            "port_match": True,
        }],
    }


def usb_inventory(*, duplicate=False, other_samsung=False):
    lines = [b"Bus 001 Device 002: ID 1d6b:0002 Linux Foundation 2.0 root hub",
             b"Bus 001 Device 003: ID 04e8:6861 Samsung Electronics Co., Ltd"]
    if duplicate:
        lines.append(b"Bus 001 Device 004: ID 04e8:6861 Samsung Electronics Co., Ltd")
    if other_samsung:
        lines.append(b"Bus 001 Device 005: ID 04e8:6860 Samsung Electronics Co., Ltd")
    return result(b"\n".join(lines) + b"\n")


def usb_zero_samsung():
    return result(
        b"Bus 001 Device 002: ID 1d6b:0002 Linux Foundation 2.0 root hub\n"
    )


def usb_recovery_inventory():
    return result(
        b"Bus 001 Device 002: ID 1d6b:0002 Linux Foundation 2.0 root hub\n"
        b"Bus 001 Device 003: ID 04e8:6860 Samsung Electronics Co., Ltd\n"
    )


def recovery_binding_receipt(*, request_outcome="CONFIRMED"):
    return result(
        json.dumps(
            {
                "schema": A.RECOVERY_BINDING_RECEIPT_SCHEMA,
                "mode": A.RECOVERY_BINDING_RECEIPT_MODE,
                "role": A.ADB_ROLE_RECOVERY,
                "usbProduct": "04e8:6860",
                "adbState": "recovery",
                "usbInventorySha256": A.sha256_bytes(usb_recovery_inventory().stdout),
                "adbInventorySha256": "e" * 64,
                "adbSerialSha256": "c" * 64,
                "requestOutcome": request_outcome,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )


def healthy_results(version="0.11.194", build="phase3-minimal-h27"):
    return [
        usb_inventory(),
        result(bridge()),
        result(command(BOOT_ID + "\n", "cat")),
        result(command(f"version: {version} build={build}\n", "version")),
        result(command("selftest: pass=9 warn=0 fail=0 duration=12ms entries=9\n", "selftest")),
        result(command("pstore=clean entries=0\n", "status")),
        result(command(BOOT_ID + "\n", "cat")),
        result(absent_stat()),
        result(absent_stat()),
    ]


class FixedAdapterTest(unittest.TestCase):
    def setUp(self):
        self._managed_root = tempfile.TemporaryDirectory()
        managed_root = Path(self._managed_root.name)
        capture_dir = managed_root / "workspace/private"
        capture_dir.mkdir(parents=True, mode=0o700)
        capture_path = capture_dir / "test-bridge.raw"
        capture_path.write_bytes(b"")
        capture_path.chmod(0o600)
        self._repo_root_patch = mock.patch.object(A, "REPO_ROOT", managed_root)
        self._repo_root_patch.start()
        self.addCleanup(self._repo_root_patch.stop)
        self.addCleanup(self._managed_root.cleanup)
        self.expected = {"version": "0.11.194", "build": "phase3-minimal-h27"}
        self.artifact = {
            "path": "/tmp/candidate.img",
            "sha256": "a" * 64,
            "version": "0.11.194",
            "build": "phase3-minimal-h27",
        }
        self.recovery_binding = A.RecoveryBinding(
            A.sha256_bytes(usb_recovery_inventory().stdout),
            "e" * 64,
            "c" * 64,
        )

    def test_preflight_produces_exact_healthy_snapshot(self):
        runner = FakeRunner(healthy_results())
        adapter = A.FixedA90Adapter(runner, qualification=QUALIFICATION)
        snapshot = adapter.preflight(
            {"expectedStart": self.expected, "qualification": QUALIFICATION}
        )
        snapshot.validate()
        self.assertTrue(snapshot.healthy)
        self.assertEqual(snapshot.boot_id, BOOT_ID)
        self.assertEqual((snapshot.version, snapshot.build), tuple(self.expected.values()))
        self.assertEqual([call[0] for call in runner.calls], [
            "usb-inventory", "bridge-preflight", "boot-id-start", "version", "selftest", "status", "boot-id-final",
            "fresh-enable-path", "fresh-latch-path",
        ])
        bridge_argv = runner.calls[1][1]
        self.assertEqual(bridge_argv.count(A.FIXED_SERIAL), 2)
        self.assertIn("--pin-selected-realpath", bridge_argv)

    def test_failed_boot_capture_requires_recovery_and_reads_fixed_pair_once(self):
        with tempfile.TemporaryDirectory() as temp:
            log_directory = Path(temp)
            serial = "A90-RECOVERY"
            adb = b"List of devices attached\n" + serial.encode() + b" recovery product:r3q\n"
            runner = FakeRunner([
                usb_recovery_inventory(),
                result(adb),
                result(b"sec_log=1\n"),
                result(b"Kernel panic\n"),
            ], log_directory)
            adapter = A.FixedA90Adapter(runner, qualification=QUALIFICATION)
            adapter.recovery_serial_sha256 = A.sha256_bytes(serial.encode())
            evidence = adapter._capture_failed_boot_evidence(timeout_sec=20, lease_check=lambda: None)
            self.assertEqual(evidence.outcome, "CAPTURED")
            self.assertEqual([call[0] for call in runner.calls], [
                "failed-boot-usb-inventory", "failed-boot-adb-inventory",
                "failed-boot-cmdline", "failed-boot-last-kmsg",
            ])
            self.assertEqual(runner.calls[2][1], (
                str(A.ADB), "-s", serial, "exec-out", "cat", "/proc/cmdline"
            ))
            self.assertEqual(runner.calls[3][1], (
                str(A.ADB), "-s", serial, "exec-out", "cat", "/proc/last_kmsg"
            ))
            for name, expected in ((A.FAILED_BOOT_CMDLINE_RAW_NAME, b"sec_log=1\n"), (A.FAILED_BOOT_LAST_KMSG_RAW_NAME, b"Kernel panic\n")):
                path = log_directory / name
                self.assertEqual(path.read_bytes(), expected)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            receipt = evidence.payload()
            self.assertNotIn(serial, json.dumps(receipt))
            self.assertEqual(receipt["lastKmsg"]["byteCount"], len(b"Kernel panic\n"))

    def test_pre_candidate_transition_accepts_missing_native_response_after_exact_recovery(self):
        runner = FakeRunner([usb_inventory(), recovery_binding_receipt(request_outcome="UNCERTAIN_RESPONSE")])
        adapter = A.FixedA90Adapter(runner, qualification=QUALIFICATION)
        binding = adapter.prepare_candidate_recovery(timeout_sec=90)
        self.assertEqual(binding.adb_serial_sha256, "c" * 64)
        self.assertEqual(binding.request_outcome, "UNCERTAIN_RESPONSE")
        self.assertEqual([call[0] for call in runner.calls], ["effect-usb-inventory", "native-to-recovery"])
        transition_argv = runner.calls[1][1]
        self.assertIn("--recovery-only", transition_argv)
        self.assertIn("--from-native", transition_argv)
        self.assertNotIn("--require-empty-adb-baseline", transition_argv)

    def test_pre_candidate_transition_rejects_recovery_receipt_drift(self):
        drift = recovery_binding_receipt()
        value = json.loads(drift.stdout.decode())
        value["adbSerialSha256"] = "f" * 64
        drift = result(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())
        runner = FakeRunner([usb_inventory(), drift])
        with self.assertRaisesRegex(A.ContractError, "Recovery serial"):
            A.FixedA90Adapter(runner, qualification=QUALIFICATION).prepare_candidate_recovery(timeout_sec=90)

    def test_pre_candidate_transition_rejects_nonzero_valid_receipt(self):
        valid = recovery_binding_receipt()
        runner = FakeRunner([usb_inventory(), result(valid.stdout, rc=1)])
        with self.assertRaisesRegex(A.ContractError, "failed or survived"):
            A.FixedA90Adapter(runner, qualification=QUALIFICATION).prepare_candidate_recovery(timeout_sec=90)

    def test_failed_boot_capture_tolerates_bounded_zero_native_recovery_churn(self):
        with tempfile.TemporaryDirectory() as temp:
            serial = "A90-RECOVERY"
            adb = b"List of devices attached\n" + serial.encode() + b" recovery\n"
            runner = FakeRunner([
                usb_zero_samsung(), usb_inventory(), usb_zero_samsung(), usb_recovery_inventory(),
                result(b"List of devices attached\n" + serial.encode() + b" offline\n"),
                usb_recovery_inventory(), result(adb), result(b"sec_log=1\n"), result(b"kmsg"),
            ], Path(temp))
            adapter = A.FixedA90Adapter(runner, qualification=QUALIFICATION)
            adapter.recovery_serial_sha256 = A.sha256_bytes(serial.encode())
            with mock.patch.object(A.time, "sleep", return_value=None):
                evidence = adapter._capture_failed_boot_evidence(
                    timeout_sec=60, lease_check=lambda: None
                )
            self.assertEqual(evidence.outcome, "CAPTURED")
            self.assertEqual([call[0] for call in runner.calls[:4]], [
                "failed-boot-usb-inventory", "failed-boot-usb-settle", "failed-boot-usb-settle", "failed-boot-usb-settle"
            ])

    def test_failed_boot_capture_never_reads_cat_without_one_recovery_role(self):
        with tempfile.TemporaryDirectory() as temp:
            runner = FakeRunner([usb_inventory()], Path(temp))
            adapter = A.FixedA90Adapter(runner, qualification=QUALIFICATION)
            with mock.patch.object(A.time, "sleep", return_value=None):
                evidence = adapter._capture_failed_boot_evidence(
                    timeout_sec=20, lease_check=lambda: None
                )
            self.assertEqual(evidence.outcome, "NO_PROOF_OBSERVER")
            self.assertLessEqual(len(runner.calls), A.FAILED_BOOT_RECOVERY_SETTLE_ATTEMPTS)
            self.assertFalse(any("cat" in call[0] for call in runner.calls))

    def test_failed_boot_capture_rejects_foreign_or_multiple_samsung_immediately(self):
        foreign = result(b"Bus 001 Device 003: ID 04e8:1234 Samsung Electronics Co., Ltd\n")
        multiple = result(
            b"Bus 001 Device 003: ID 04e8:6860 Samsung Electronics Co., Ltd\n"
            b"Bus 001 Device 004: ID 04e8:6860 Samsung Electronics Co., Ltd\n"
        )
        for inventory in (foreign, multiple):
            with self.subTest(inventory=inventory.stdout), tempfile.TemporaryDirectory() as temp:
                runner = FakeRunner([inventory], Path(temp))
                adapter = A.FixedA90Adapter(runner, qualification=QUALIFICATION)
                evidence = adapter._capture_failed_boot_evidence(timeout_sec=60, lease_check=lambda: None)
                self.assertEqual(evidence.outcome, "NO_PROOF_OBSERVER")
                self.assertEqual(len(runner.calls), 1)

    def test_failed_boot_capture_empty_last_kmsg_is_no_proof_without_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            serial = "A90-RECOVERY"
            adb = b"List of devices attached\n" + serial.encode() + b" recovery\n"
            runner = FakeRunner([
                usb_recovery_inventory(), result(adb), result(b"sec_log=1\n"), result(b"")
            ], Path(temp))
            adapter = A.FixedA90Adapter(runner, qualification=QUALIFICATION)
            adapter.recovery_serial_sha256 = A.sha256_bytes(serial.encode())
            evidence = adapter._capture_failed_boot_evidence(timeout_sec=20, lease_check=lambda: None)
            self.assertEqual(evidence.outcome, "NO_PROOF_OBSERVER")
            self.assertEqual(evidence.reason, "EMPTY_LAST_KMSG")
            self.assertEqual(len(runner.calls), 4)

    def test_failed_boot_capture_failures_are_no_proof_without_retry(self):
        serial = "A90-RECOVERY"
        adb = b"List of devices attached\n" + serial.encode() + b" recovery\n"
        cases = (
            ("oversize", b"x" * (A.FAILED_BOOT_CMDLINE_MAX_BYTES + 1), {}, 4),
            ("nonzero", b"failed", {"rc": 1}, 4),
            ("stderr", b"bad", {"stderr": b"error"}, 4),
            ("nonquiescent", b"partial", {"quiescent": False}, 3),
            ("malformed-returncode", A.CommandResult(True, b"bad", b"", True), None, 3),
        )
        for label, cmdline, kwargs, expected_calls in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp:
                cmdline_result = cmdline if isinstance(cmdline, A.CommandResult) else result(cmdline, **(kwargs or {}))
                runner = FakeRunner([usb_recovery_inventory(), result(adb), cmdline_result, result(b"kmsg")], Path(temp))
                adapter = A.FixedA90Adapter(runner, qualification=QUALIFICATION)
                adapter.recovery_serial_sha256 = A.sha256_bytes(serial.encode())
                evidence = adapter._capture_failed_boot_evidence(timeout_sec=20, lease_check=lambda: None)
                self.assertEqual(evidence.outcome, "NO_PROOF_OBSERVER")
                self.assertEqual(len(runner.calls), expected_calls)

    def test_failed_boot_adb_inventory_stream_is_redacted(self):
        serial = "A90-RECOVERY"
        with tempfile.TemporaryDirectory() as temp:
            log_directory = Path(temp) / "logs"
            redactor = A.SerialRedactor(hashes=(A.sha256_bytes(serial.encode()),))
            runner = A.HostRunner(log_directory, redactor=redactor)
            runner.run("failed-boot-adb-inventory", (sys.executable, "-c", f"print('List of devices attached\\n{serial} recovery')"), 10)
            logged = (log_directory / "001-failed-boot-adb-inventory.stdout").read_bytes()
            raw = f"List of devices attached\n{serial} recovery\n".encode()
            expected = f"{A._serial_redaction.ADB_STDOUT_DIGEST_PREFIX}{A.sha256_bytes(raw)}> len={len(raw)} status=valid\n".encode()
            self.assertEqual(logged, expected)
            self.assertNotIn(serial.encode(), logged)

    def test_recovery_adb_inventory_accepts_only_authoritative_startup_banner(self):
        serial = "A90-RECOVERY"
        raw = b"List of devices attached\n" + serial.encode() + b" recovery\n"
        expected = A.sha256_bytes(serial.encode())
        banner = next(iter(A._serial_redaction.ADB_STARTUP_BANNERS))
        accepted = A._parse_recovery_adb_inventory(
            result(raw, stderr=banner), expected_serial_sha256=expected
        )
        self.assertEqual(accepted, (A.sha256_bytes(raw), serial))
        with self.assertRaises(A.ContractError):
            A._parse_recovery_adb_inventory(
                result(raw, stderr=banner + b"near-miss\n"),
                expected_serial_sha256=expected,
            )

    def test_other_serial_candidate_is_allowed_but_fixed_a90_stays_selected(self):
        value = bridge(ambiguous=True)
        value["serial_candidates"].append(
            {"path": "/dev/serial/by-id/other", "realpath": "/dev/ttyACM1", "exists": True}
        )
        snapshot = A.FixedA90Adapter(
            FakeRunner([usb_inventory(), result(value), *healthy_results()[2:]]),
            qualification=QUALIFICATION,
        ).preflight(
            {"expectedStart": self.expected, "qualification": QUALIFICATION}
        )
        snapshot.validate()

    def test_bridge_rejects_wrong_selected_device(self):
        value = bridge(ambiguous=True)
        value["selected_device"] = "/dev/serial/by-id/other"
        runner = FakeRunner([usb_inventory(), result(value)])
        with self.assertRaisesRegex(A.ContractError, "bridge preflight"):
            A.FixedA90Adapter(runner, qualification=QUALIFICATION).preflight(
                {"expectedStart": self.expected, "qualification": QUALIFICATION}
            )

    def test_bridge_rejects_listener_process_or_command_mismatch(self):
        for mutate in (
            lambda value: value["processes"][0].update(pid=9999),
            lambda value: value["processes"][0].update(port_match=False),
            lambda value: value["metadata"]["command"].__setitem__(
                value["metadata"]["command"].index(A.FIXED_SERIAL),
                "/dev/serial/by-id/other",
            ),
        ):
            value = bridge()
            mutate(value)
            with self.subTest(value=value), self.assertRaisesRegex(
                A.ContractError, "bridge preflight"
            ):
                A.FixedA90Adapter(
                    FakeRunner([usb_inventory(), result(value)]),
                    qualification=QUALIFICATION,
                ).preflight(
                    {"expectedStart": self.expected, "qualification": QUALIFICATION}
                )

    def test_bridge_capture_is_bound_to_private_metadata_and_regular_identity(self):
        for mutate in (
            lambda value: value["metadata"].__setitem__("capture_path", "/tmp/raw"),
            lambda value: value["metadata"].__setitem__(
                "capture_path", "workspace/private/other.raw"
            ),
            lambda value: value["metadata"]["command"].__setitem__(
                value["metadata"]["command"].index("--capture") + 1, "/tmp/raw"
            ),
        ):
            value = bridge()
            mutate(value)
            with self.subTest(value=value), self.assertRaisesRegex(
                A.ContractError, "bridge preflight"
            ):
                A.FixedA90Adapter(
                    FakeRunner([usb_inventory(), result(value)]),
                    qualification=QUALIFICATION,
                ).preflight(
                    {"expectedStart": self.expected, "qualification": QUALIFICATION}
                )

    def test_bridge_rejects_cmdline_fallback_listener_ownership(self):
        value = bridge()
        value["port_pid_source"] = "cmdline-fallback"
        value["port_socket_inodes"] = []
        value["port_sockets"] = []
        with self.assertRaisesRegex(A.ContractError, "bridge preflight"):
            A.FixedA90Adapter(
                FakeRunner([usb_inventory(), result(value)]),
                qualification=QUALIFICATION,
            ).preflight(
                {"expectedStart": self.expected, "qualification": QUALIFICATION}
            )

    def test_wrong_version_is_unhealthy_not_pass(self):
        runner = FakeRunner(healthy_results(version="other"))
        snapshot = A.FixedA90Adapter(runner, qualification=QUALIFICATION).preflight(
            {"expectedStart": self.expected, "qualification": QUALIFICATION}
        )
        self.assertFalse(snapshot.healthy)

    def test_rollback_observation_marks_fresh_state_unobserved(self):
        runner = FakeRunner(healthy_results()[:7])
        snapshot = A.FixedA90Adapter(
            runner, qualification=QUALIFICATION
        ).observe(
            self.expected,
            QUALIFICATION["freshState"],
            require_fresh_state=False,
            timeout_sec=30,
        )
        self.assertTrue(snapshot.healthy)
        self.assertFalse(snapshot.fresh_state_observed)
        self.assertFalse(snapshot.fresh_state_absent)
        self.assertNotIn("fresh-enable-path", [call[0] for call in runner.calls])

    def test_observation_rejects_boot_epoch_change(self):
        values = healthy_results()
        values[6] = result(command(
            "fedcba98-7654-3210-fedc-ba9876543210\n", "cat"
        ))
        snapshot = A.FixedA90Adapter(
            FakeRunner(values), qualification=QUALIFICATION
        ).preflight(
            {"expectedStart": self.expected, "qualification": QUALIFICATION}
        )
        self.assertFalse(snapshot.healthy)

    def test_stable_target_binding_ignores_variable_selftest_duration(self):
        first = healthy_results()
        second = healthy_results()
        second[4] = result(command(
            "selftest: pass=9 warn=0 fail=0 duration=99ms entries=9\n", "selftest"
        ))
        one = A.FixedA90Adapter(FakeRunner(first), qualification=QUALIFICATION).preflight(
            {"expectedStart": self.expected, "qualification": QUALIFICATION}
        )
        two = A.FixedA90Adapter(FakeRunner(second), qualification=QUALIFICATION).preflight(
            {"expectedStart": self.expected, "qualification": QUALIFICATION}
        )
        self.assertEqual(one.target_evidence_sha256, two.target_evidence_sha256)
        self.assertNotEqual(one.receipt_sha256, two.receipt_sha256)

    def test_selftest_drift_is_rejected_but_pstore_count_is_diagnostic_only(self):
        bad_selftest = healthy_results()
        bad_selftest[4] = result(command(
            "selftest: pass=8 warn=0 fail=1 duration=12ms entries=9\n", "selftest"
        ))
        with self.assertRaisesRegex(A.ContractError, "selftest"):
            A.FixedA90Adapter(FakeRunner(bad_selftest), qualification=QUALIFICATION).preflight(
                {"expectedStart": self.expected, "qualification": QUALIFICATION}
            )

        bad_pstore = healthy_results()
        bad_pstore[5] = result(command("pstore=dirty entries=0 entries=1\n", "status"))
        snapshot = A.FixedA90Adapter(
            FakeRunner(bad_pstore), qualification=QUALIFICATION
        ).preflight({"expectedStart": self.expected, "qualification": QUALIFICATION})
        self.assertTrue(snapshot.healthy)

    def test_present_fresh_state_is_rejected(self):
        present = healthy_results()
        present[7] = result(command("mode=100600 size=0\n", "stat"))
        with self.assertRaisesRegex(A.ContractError, "fresh state absence"):
            A.FixedA90Adapter(
                FakeRunner(present), qualification=QUALIFICATION
            ).preflight(
                {"expectedStart": self.expected, "qualification": QUALIFICATION}
            )

    def test_absent_stat_receipt_is_bound_to_exact_requested_path(self):
        wrong = {
            "request": ["stat", "/cache/wrong.done"],
            "response": absent_stat(),
        }
        with self.assertRaisesRegex(A.ContractError, "request binding"):
            A._validate_absent_stat(
                wrong, QUALIFICATION["freshState"]["latchPath"]
            )

    def test_absent_stat_rejects_nonprotocol_unknown_status(self):
        stale = absent_stat()
        stale["status"] = "unknown"
        stale["end"]["status"] = "unknown"
        with self.assertRaisesRegex(A.ContractError, "fresh state absence"):
            A._validate_absent_stat(
                {
                    "request": ["stat", QUALIFICATION["freshState"]["latchPath"]],
                    "response": stale,
                },
                QUALIFICATION["freshState"]["latchPath"],
            )

    def test_recovery_qualification_is_required(self):
        with self.assertRaisesRegex(A.ContractError, "physical recovery"):
            A.FixedA90Adapter(FakeRunner([]), qualification={})

    def test_duplicate_samsung_usb_endpoint_is_rejected(self):
        with self.assertRaisesRegex(A.ContractError, "one exact A90 endpoint"):
            A.FixedA90Adapter(
                FakeRunner([usb_inventory(duplicate=True)]),
                qualification=QUALIFICATION,
            ).preflight(
                {"expectedStart": self.expected, "qualification": QUALIFICATION}
            )

    def test_other_samsung_endpoint_is_not_untouched(self):
        results = healthy_results()
        results[0] = usb_inventory(other_samsung=True)
        snapshot = A.FixedA90Adapter(
            FakeRunner(results), qualification=QUALIFICATION
        ).preflight(
            {"expectedStart": self.expected, "qualification": QUALIFICATION}
        )
        snapshot.validate()
        self.assertFalse(snapshot.other_targets_untouched)

    def test_observation_budget_is_total_not_per_command(self):
        adapter = A.FixedA90Adapter(FakeRunner([]), qualification=QUALIFICATION)
        with mock.patch.object(A.time, "monotonic", side_effect=[0.0, 31.0]):
            with self.assertRaisesRegex(A.ContractError, "total timeout"):
                adapter.observe(
                    self.expected,
                    QUALIFICATION["freshState"],
                    require_fresh_state=True,
                    timeout_sec=30,
                )

    def test_bridge_realpath_mismatch_is_rejected(self):
        bad = bridge()
        bad["serial_candidates"][0]["realpath"] = "/dev/ttyACM1"
        with self.assertRaisesRegex(A.ContractError, "bridge preflight"):
            A.FixedA90Adapter(
                FakeRunner([usb_inventory(), result(bad)]), qualification=QUALIFICATION
            ).preflight(
                {"expectedStart": self.expected, "qualification": QUALIFICATION}
            )

    def test_flash_uses_only_fixed_helper_arguments(self):
        runner = FakeRunner([result(b"ok")])
        adapter = A.FixedA90Adapter(runner, qualification=QUALIFICATION)
        effect = adapter.flash(
            self.artifact, rollback=False, timeout_sec=90,
            recovery_binding=self.recovery_binding,
        )
        effect.validate()
        self.assertTrue(effect.completed)
        self.assertNotIn("adb-inventory", [call[0] for call in runner.calls])
        label, argv, timeout = runner.calls[0]
        self.assertEqual(label, "flash-candidate")
        self.assertEqual(
            argv,
            A.fixed_flash_argv(
                self.artifact,
                recovery_serial_sha256="c" * 64,
                timeout_sec=90,
                recovery_binding=self.recovery_binding,
                owner_usb_inventory_sha256=self.recovery_binding.usb_inventory_sha256,
                owner_adb_inventory_sha256=self.recovery_binding.adb_inventory_sha256,
                owner_adb_role="BOUND_RECOVERY_PRESENT",
            ),
        )
        self.assertEqual(argv[:2], (str(A.PYTHON), str(A.FLASH)))
        self.assertIn("--reuse-bound-recovery-only", argv)
        self.assertNotIn("--from-native", argv)
        self.assertIn("--owner-expect-adb-role", argv)
        self.assertEqual(
            argv[argv.index("--owner-expect-adb-role") + 1],
            "BOUND_RECOVERY_PRESENT",
        )
        self.assertIn("--owner-expect-adb-inventory-sha256", argv)
        self.assertEqual(
            argv[argv.index("--expect-recovery-serial-sha256") + 1],
            "c" * 64,
        )
        self.assertNotIn("--serial", argv)
        self.assertEqual(argv.count(self.artifact["sha256"]), 2)
        self.assertEqual(timeout, 90)
        self.assertEqual(argv[argv.index("--recovery-timeout") + 1], "30")
        self.assertEqual(argv[argv.index("--bridge-timeout") + 1], "30")

    def test_flash_failure_is_a_result_and_never_a_retry(self):
        runner = FakeRunner([usb_inventory(), result(b"failed", rc=1)])
        effect = A.FixedA90Adapter(runner, qualification=QUALIFICATION).flash(
            self.artifact, rollback=True, timeout_sec=60
        )
        self.assertFalse(effect.completed)
        self.assertEqual(effect.returncode, 1)
        self.assertEqual(len(runner.calls), 2)
        self.assertEqual(runner.calls[1][0], "flash-rollback")
        rollback_argv = runner.calls[1][1]
        self.assertIn("--reuse-bound-recovery-or-from-native", rollback_argv)
        self.assertNotIn("--from-native", rollback_argv)
        self.assertNotIn("--require-stable-adb-baseline", rollback_argv)

    def test_candidate_zero_samsung_is_immediate_and_has_no_helper_effect(self):
        runner = FakeRunner([usb_zero_samsung()])
        with self.assertRaisesRegex(A.ContractError, "candidate pre-effect"):
            A.FixedA90Adapter(runner, qualification=QUALIFICATION).prepare_candidate_recovery(
                timeout_sec=60
            )
        self.assertEqual([call[0] for call in runner.calls], ["effect-usb-inventory"])

    def test_rollback_zero_then_exact_recovery_is_bounded_and_dispatches_once(self):
        runner = FakeRunner(
            [usb_zero_samsung(), usb_recovery_inventory(), result(b"adb"), result(b"ok")]
        )
        with (
            mock.patch.object(A, "_validate_effect_adb_inventory", return_value="d" * 64),
            mock.patch.object(A.time, "sleep"),
        ):
            effect = A.FixedA90Adapter(runner, qualification=QUALIFICATION).flash(
                self.artifact, rollback=True, timeout_sec=60
            )
        self.assertTrue(effect.completed)
        self.assertEqual(
            [call[0] for call in runner.calls],
            [
                "effect-usb-inventory",
                "rollback-effect-usb-inventory",
                "adb-inventory",
                "flash-rollback",
            ],
        )

    def test_rollback_zero_timeout_stops_before_helper(self):
        runner = FakeRunner([usb_zero_samsung(), usb_zero_samsung()])
        with (
            mock.patch.object(A.time, "monotonic", side_effect=[0.0, 0.0, 31.0]),
            mock.patch.object(A.time, "sleep"),
            self.assertRaisesRegex(A.ContractError, "re-enumeration timed out"),
        ):
            A.FixedA90Adapter(runner, qualification=QUALIFICATION).flash(
                self.artifact, rollback=True, timeout_sec=60
            )
        self.assertEqual(
            [call[0] for call in runner.calls],
            ["effect-usb-inventory", "rollback-effect-usb-inventory"],
        )

    def test_rollback_exact_arrival_after_deadline_stops_before_helper(self):
        runner = FakeRunner([usb_zero_samsung(), usb_recovery_inventory()])
        with (
            mock.patch.object(A.time, "monotonic", side_effect=[0.0, 0.0, 31.0]),
            mock.patch.object(A.time, "sleep"),
            self.assertRaisesRegex(A.ContractError, "re-enumeration timed out"),
        ):
            A.FixedA90Adapter(runner, qualification=QUALIFICATION).flash(
                self.artifact, rollback=True, timeout_sec=60
            )
        self.assertEqual(
            [call[0] for call in runner.calls],
            ["effect-usb-inventory", "rollback-effect-usb-inventory"],
        )

    def test_rollback_zero_then_extra_samsung_stops_before_helper(self):
        runner = FakeRunner([usb_zero_samsung(), usb_inventory(duplicate=True)])
        with (
            mock.patch.object(A.time, "sleep"),
            self.assertRaisesRegex(A.ContractError, "single-Samsung"),
        ):
            A.FixedA90Adapter(runner, qualification=QUALIFICATION).flash(
                self.artifact, rollback=True, timeout_sec=60
            )
        self.assertEqual(
            [call[0] for call in runner.calls],
            ["effect-usb-inventory", "rollback-effect-usb-inventory"],
        )

    def test_rollback_zero_then_wrong_samsung_stops_before_helper(self):
        wrong = result(
            b"Bus 001 Device 002: ID 1d6b:0002 Linux Foundation 2.0 root hub\n"
            b"Bus 001 Device 003: ID 04e8:1234 Samsung Electronics Co., Ltd\n"
        )
        runner = FakeRunner([usb_zero_samsung(), wrong])
        with (
            mock.patch.object(A.time, "sleep"),
            self.assertRaisesRegex(A.ContractError, "not exact A90"),
        ):
            A.FixedA90Adapter(runner, qualification=QUALIFICATION).flash(
                self.artifact, rollback=True, timeout_sec=60
            )
        self.assertEqual(
            [call[0] for call in runner.calls],
            ["effect-usb-inventory", "rollback-effect-usb-inventory"],
        )

    def test_nonzero_system_return_after_exact_write_readback_is_pending_shape(self):
        receipt = A.canonical_json({
            "schema": A.OWNER_RECEIPT_SCHEMA,
            "mode": A.OWNER_RECEIPT_MODE,
            "outcome": "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN",
            "writeStarted": True,
            "bootWrittenReadbackExact": True,
            "systemReturnAttempted": True,
            "systemReturnCommandOk": False,
            "systemReturnConfirmed": False,
        })
        effect = A.FixedA90Adapter(
            FakeRunner([result(receipt, rc=1)]), qualification=QUALIFICATION
        ).flash(self.artifact, rollback=False, timeout_sec=60, recovery_binding=self.recovery_binding)
        self.assertEqual(
            effect.outcome,
            "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN",
        )
        self.assertEqual(effect.returncode, 1)
        self.assertFalse(effect.completed)

    def test_owner_usb_inventory_binding_is_role_scoped_and_fixed(self):
        digest = "d" * 64
        argv = A.fixed_flash_argv(
            self.artifact,
            recovery_serial_sha256="c" * 64,
            timeout_sec=60,
            rollback=True,
            owner_usb_inventory_sha256=digest,
            owner_adb_role="NATIVE_NO_RECOVERY",
        )
        self.assertIn("--owner-fixed-bridge-preflight", argv)
        self.assertEqual(
            argv[argv.index("--owner-expect-usb-inventory-sha256") + 1], digest
        )
        self.assertEqual(
            argv[argv.index("--owner-expect-adb-role") + 1], "NATIVE_NO_RECOVERY"
        )
        self.assertNotIn("--owner-expect-adb-inventory-sha256", argv)
        self.assertNotIn("--owner-expect-foreign-usb-sha256", argv)
        self.assertNotIn("--owner-expect-foreign-adb-sha256", argv)
        self.assertNotIn("--owner-expect-recovery-usb-product", argv)
        self.assertNotIn("--owner-expect-recovery-usb-count", argv)
        candidate_argv = A.fixed_flash_argv(
            self.artifact,
            recovery_serial_sha256="c" * 64,
            timeout_sec=60,
            rollback=False,
            recovery_binding=self.recovery_binding,
            owner_usb_inventory_sha256=self.recovery_binding.usb_inventory_sha256,
            owner_adb_inventory_sha256=self.recovery_binding.adb_inventory_sha256,
            owner_adb_role="BOUND_RECOVERY_PRESENT",
        )
        self.assertIn("--reuse-bound-recovery-only", candidate_argv)
        self.assertNotIn("--from-native", candidate_argv)

    def test_live_host_runner_creates_one_private_log_directory(self):
        self.assertTrue(A.LIVE_ADAPTER_ENABLED)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "logs"
            A.HostRunner(path)
            self.assertTrue(path.is_dir())
            self.assertEqual(path.stat().st_mode & 0o777, 0o700)
            with self.assertRaisesRegex(A.ContractError, "already exists"):
                A.HostRunner(path)

    def test_live_host_runner_binds_private_adb_home_and_no_ambient_home(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner = A.HostRunner(root / "logs")
            self.assertEqual(runner.environment["HOME"], str(runner.adb_home))
            self.assertNotIn("ADB_SERVER_SOCKET", runner.environment)
            result = runner.run(
                "environment-check",
                (
                    sys.executable,
                    "-c",
                    (
                        "import os; assert os.environ['HOME'].endswith('/.adb-home'); "
                        "assert os.environ['A90_F1_OWNER_ADB_HOME']==os.environ['HOME']; "
                        "assert 'USER' not in os.environ; print('ok')"
                    ),
                ),
                10,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b"ok\n")
            self.assertEqual(runner.adb_home.stat().st_mode & 0o777, 0o700)
            self.assertEqual(runner.adb_android.stat().st_mode & 0o777, 0o700)

    def test_live_host_runner_rejects_adb_home_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner = A.HostRunner(root / "logs")
            (runner.adb_home / "unexpected").write_bytes(b"x")
            with self.assertRaisesRegex(A.ContractError, "unexpected entries"):
                runner.run("drift-check", (sys.executable, "-c", "pass"), 10)
            (runner.adb_home / "unexpected").unlink()
            runner.adb_home.chmod(0o755)
            with self.assertRaisesRegex(A.ContractError, "mode 0700"):
                runner.run("mode-check", (sys.executable, "-c", "pass"), 10)

    def test_live_host_runner_rejects_adb_android_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner = A.HostRunner(root / "logs")
            android = runner.adb_android
            android.rmdir()
            android.symlink_to(root / "outside", target_is_directory=True)
            (root / "outside").mkdir(mode=0o700)
            with self.assertRaisesRegex(A.ContractError, r"ADB \.android directory identity"):
                runner.run("symlink-check", (sys.executable, "-c", "pass"), 10)

    def test_live_host_runner_accepts_only_default_adb_state_file(self):
        with tempfile.TemporaryDirectory() as temp:
            runner = A.HostRunner(Path(temp) / "logs")
            state = runner.adb_android / "adb.5037"
            state.write_bytes(b"state")
            state.chmod(0o600)
            self.assertEqual(
                runner.run("state-file", (sys.executable, "-c", "pass"), 10).returncode,
                0,
            )
            bad = runner.adb_android / "adb.5038"
            bad.write_bytes(b"state")
            bad.chmod(0o600)
            with self.assertRaisesRegex(A.ContractError, "unexpected entries"):
                runner.run("wrong-port", (sys.executable, "-c", "pass"), 10)

    def test_live_host_runner_rejects_non_private_adb_state_modes(self):
        for mode in (0o644, 0o664):
            with self.subTest(mode=oct(mode)), tempfile.TemporaryDirectory() as temp:
                runner = A.HostRunner(Path(temp) / "logs")
                state = runner.adb_android / "adb.5037"
                state.write_bytes(b"state")
                state.chmod(mode)
                with self.assertRaisesRegex(A.ContractError, "key entry identity"):
                    runner.run("state-mode", (sys.executable, "-c", "pass"), 10)

    def test_owner_child_preexec_sets_private_umask(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "umask-probe"
            runner = A.HostRunner(root / "logs")
            before = {
                resource.RLIMIT_CORE: resource.getrlimit(resource.RLIMIT_CORE),
                resource.RLIMIT_FSIZE: resource.getrlimit(resource.RLIMIT_FSIZE),
            }
            result = runner.run(
                "umask-probe",
                (
                    sys.executable,
                    "-c",
                    f"from pathlib import Path; Path({str(target)!r}).write_bytes(b'x')",
                ),
                10,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                before[resource.RLIMIT_CORE],
                resource.getrlimit(resource.RLIMIT_CORE),
            )
            self.assertEqual(
                before[resource.RLIMIT_FSIZE],
                resource.getrlimit(resource.RLIMIT_FSIZE),
            )

    def test_rollback_reenumeration_bound_is_thirty_seconds(self):
        self.assertEqual(A.ROLLBACK_REENUMERATION_TIMEOUT_SEC, 30.0)

    def test_live_host_runner_separates_boot_scratch_and_log_bounds(self):
        self.assertEqual(A.MAX_CHILD_FILE_BYTES, 64 << 20)
        self.assertEqual(A.MAX_OUTPUT_BYTES, 1 << 20)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scratch = root / "sealed-boot.img"
            runner = A.HostRunner(root / "logs")
            result = runner.run(
                "bounded-boot-scratch",
                (
                    sys.executable,
                    "-c",
                    (
                        "from pathlib import Path; "
                        f"p=Path({str(scratch)!r}); "
                        f"p.write_bytes(b'\\0' * {58_368_000})"
                    ),
                ),
                10,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(scratch.stat().st_size, 58_368_000)
            self.assertEqual(result.stdout, b"")
            self.assertEqual(result.stderr, b"")

    def test_live_host_runner_still_rejects_oversized_stdout(self):
        with tempfile.TemporaryDirectory() as temp:
            runner = A.HostRunner(Path(temp) / "logs")
            with self.assertRaisesRegex(A.ContractError, "output exceeds"):
                runner.run(
                    "oversized-stdout",
                    (
                        sys.executable,
                        "-c",
                        f"import os; os.write(1, b'x' * {A.MAX_OUTPUT_BYTES + 1})",
                    ),
                    10,
                )

    def test_adapter_surface_stays_bounded(self):
        self.assertLessEqual(len(SOURCE.read_text().splitlines()), 1300)


if __name__ == "__main__":
    unittest.main()
