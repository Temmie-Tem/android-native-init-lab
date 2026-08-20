from __future__ import annotations

import importlib.util
import json
import sys
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
        "method": "NATIVE_TO_EMPTY_ADB_SINGLE_RECOVERY_ARRIVAL_BOOT_READBACK_V1",
        "evidence": {"path": "/tmp/recovery.json", "size": 1, "sha256": "a" * 64},
        "review": {"path": "/tmp/recovery-review.json", "size": 1, "sha256": "b" * 64},
        "demonstrated": True,
    },
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
        "end": {"cmd": "stat", "rc": "-2", "status": "unknown", "errno": "2"},
        "rc": -2,
        "status": "unknown",
        "trust": "A90P1_V1_STRUCTURAL_ONLY",
        "text": "not found",
    }


def bridge(*, ambiguous=False):
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
        "port_pids": [1234],
    }


def healthy_results(version="0.11.194", build="phase3-minimal-h27"):
    return [
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
            "bridge-preflight", "version", "selftest", "status", "boot-id",
            "fresh-enablePath", "fresh-latchPath",
        ])

    def test_bridge_ambiguity_is_rejected(self):
        runner = FakeRunner([result(bridge(ambiguous=True))])
        with self.assertRaisesRegex(A.ContractError, "bridge preflight"):
            A.FixedA90Adapter(runner, qualification=QUALIFICATION).preflight(
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
        second[2] = result(command(
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
        bad_selftest[2] = result(command(
            "selftest: pass=8 warn=0 fail=1 duration=12ms entries=9\n", "selftest"
        ))
        with self.assertRaisesRegex(A.ContractError, "selftest"):
            A.FixedA90Adapter(FakeRunner(bad_selftest), qualification=QUALIFICATION).preflight(
                {"expectedStart": self.expected, "qualification": QUALIFICATION}
            )

        bad_pstore = healthy_results()
        bad_pstore[3] = result(command("pstore=dirty entries=0 entries=1\n", "status"))
        snapshot = A.FixedA90Adapter(
            FakeRunner(bad_pstore), qualification=QUALIFICATION
        ).preflight({"expectedStart": self.expected, "qualification": QUALIFICATION})
        self.assertFalse(snapshot.healthy)

    def test_present_fresh_state_is_rejected(self):
        present = healthy_results()
        present[5] = result(command("mode=100600 size=0\n", "stat"))
        with self.assertRaisesRegex(A.ContractError, "fresh state absence"):
            A.FixedA90Adapter(
                FakeRunner(present), qualification=QUALIFICATION
            ).preflight(
                {"expectedStart": self.expected, "qualification": QUALIFICATION}
            )

    def test_recovery_qualification_is_required(self):
        with self.assertRaisesRegex(A.ContractError, "physical recovery"):
            A.FixedA90Adapter(FakeRunner([]), qualification={})

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
                FakeRunner([result(bad)]), qualification=QUALIFICATION
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
        self.assertEqual(argv[:2], (str(A.PYTHON), str(A.FLASH)))
        self.assertIn("--from-native", argv)
        self.assertIn("--require-empty-adb-baseline", argv)
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

    def test_live_host_runner_is_hard_disabled(self):
        self.assertFalse(A.LIVE_ADAPTER_ENABLED)
        with self.assertRaisesRegex(A.ContractError, "live adapter is disabled"):
            A.HostRunner(Path("/tmp/not-used"))

    def test_adapter_surface_stays_small(self):
        self.assertLessEqual(len(SOURCE.read_text().splitlines()), 500)


if __name__ == "__main__":
    unittest.main()
