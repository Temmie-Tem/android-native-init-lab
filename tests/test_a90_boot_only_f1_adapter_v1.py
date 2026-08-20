from __future__ import annotations

import importlib.util
import json
import re
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
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def run(self, label, argv, timeout_sec):
        if re.fullmatch(r"[a-z0-9-]{1,40}", label) is None:
            raise A.ContractError("adapter log label is invalid")
        self.calls.append((label, argv, timeout_sec))
        return self.results.pop(0)


def result(value, *, rc=0, quiescent=True):
    raw = value if isinstance(value, bytes) else json.dumps(value).encode()
    return A.CommandResult(rc, raw, b"", quiescent)


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
    command = [
        "/usr/bin/python3", str(A.SERIAL_BRIDGE),
        "--host", "127.0.0.1", "--port", "54321",
        "--device", A.FIXED_SERIAL, "--device-glob", A.FIXED_SERIAL,
        "--capture", "/tmp/a90.raw", "--expect-realpath", "/dev/ttyACM0",
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


def healthy_results(version="0.11.194", build="phase3-minimal-h27"):
    return [
        usb_inventory(),
        result(bridge()),
        result(command(f"version: {version} build={build}\n", "version")),
        result(command("selftest: pass=9 warn=0 fail=0 duration=12ms entries=9\n", "selftest")),
        result(command("pstore=clean entries=0\n", "status")),
        result(command(BOOT_ID + "\n", "cat")),
        result(absent_stat()),
        result(absent_stat()),
    ]


class FixedAdapterTest(unittest.TestCase):
    def setUp(self):
        self.expected = {"version": "0.11.194", "build": "phase3-minimal-h27"}
        self.artifact = {
            "path": "/tmp/candidate.img",
            "sha256": "a" * 64,
            "version": "0.11.194",
            "build": "phase3-minimal-h27",
        }

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
            "usb-inventory", "bridge-preflight", "version", "selftest", "status", "boot-id",
            "fresh-enable-path", "fresh-latch-path",
        ])
        bridge_argv = runner.calls[1][1]
        self.assertEqual(bridge_argv.count(A.FIXED_SERIAL), 2)
        self.assertIn("--pin-selected-realpath", bridge_argv)

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

    def test_stable_target_binding_ignores_variable_selftest_duration(self):
        first = healthy_results()
        second = healthy_results()
        second[3] = result(command(
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

    def test_selftest_or_pstore_drift_is_rejected_or_unhealthy(self):
        bad_selftest = healthy_results()
        bad_selftest[3] = result(command(
            "selftest: pass=8 warn=0 fail=1 duration=12ms entries=9\n", "selftest"
        ))
        with self.assertRaisesRegex(A.ContractError, "selftest"):
            A.FixedA90Adapter(FakeRunner(bad_selftest), qualification=QUALIFICATION).preflight(
                {"expectedStart": self.expected, "qualification": QUALIFICATION}
            )

        bad_pstore = healthy_results()
        bad_pstore[4] = result(command("pstore=dirty entries=0 entries=1\n", "status"))
        snapshot = A.FixedA90Adapter(
            FakeRunner(bad_pstore), qualification=QUALIFICATION
        ).preflight({"expectedStart": self.expected, "qualification": QUALIFICATION})
        self.assertFalse(snapshot.healthy)

    def test_present_fresh_state_is_rejected(self):
        present = healthy_results()
        present[6] = result(command("mode=100600 size=0\n", "stat"))
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

    def test_other_samsung_endpoint_is_allowed_but_never_selected(self):
        results = healthy_results()
        results[0] = usb_inventory(other_samsung=True)
        snapshot = A.FixedA90Adapter(
            FakeRunner(results), qualification=QUALIFICATION
        ).preflight(
            {"expectedStart": self.expected, "qualification": QUALIFICATION}
        )
        snapshot.validate()
        self.assertTrue(snapshot.other_targets_untouched)

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
        effect = adapter.flash(self.artifact, rollback=False, timeout_sec=90)
        effect.validate()
        self.assertTrue(effect.completed)
        label, argv, timeout = runner.calls[0]
        self.assertEqual(label, "flash-candidate")
        self.assertEqual(
            argv,
            A.fixed_flash_argv(
                self.artifact,
                recovery_serial_sha256="c" * 64,
                timeout_sec=90,
            ),
        )
        self.assertEqual(argv[:2], (str(A.PYTHON), str(A.FLASH)))
        self.assertIn("--from-native", argv)
        self.assertIn("--require-stable-adb-baseline", argv)
        self.assertNotIn("--require-empty-adb-baseline", argv)
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
        runner = FakeRunner([result(b"failed", rc=1)])
        effect = A.FixedA90Adapter(runner, qualification=QUALIFICATION).flash(
            self.artifact, rollback=True, timeout_sec=60
        )
        self.assertFalse(effect.completed)
        self.assertEqual(effect.returncode, 1)
        self.assertEqual(len(runner.calls), 1)
        self.assertEqual(runner.calls[0][0], "flash-rollback")

    def test_live_host_runner_creates_one_private_log_directory(self):
        self.assertTrue(A.LIVE_ADAPTER_ENABLED)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "logs"
            A.HostRunner(path)
            self.assertTrue(path.is_dir())
            self.assertEqual(path.stat().st_mode & 0o777, 0o700)
            with self.assertRaisesRegex(A.ContractError, "already exists"):
                A.HostRunner(path)

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

    def test_adapter_surface_stays_small(self):
        self.assertLessEqual(len(SOURCE.read_text().splitlines()), 620)


if __name__ == "__main__":
    unittest.main()
