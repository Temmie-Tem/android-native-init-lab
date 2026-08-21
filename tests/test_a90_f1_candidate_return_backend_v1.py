"""Host-only hostile corpus for the single-Samsung A90 backend boundary."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from tests.test_a90_boot_only_f1_minimal_v1 import M as OWNER


ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / "workspace/public/src/scripts/server-distro"
sys.path.insert(0, str(MODULE_DIR))


def load(name: str):
    source = MODULE_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ADAPTER = load("a90_boot_only_f1_adapter_v1")
BACKEND = load("a90_f1_candidate_return_backend_v1")


class FakeRunner:
    def __init__(self, usb: bytes, adb: bytes, bridge: dict | None = None):
        self.usb = usb
        self.adb = adb
        self.bridge = bridge
        self.calls: list[tuple[str, tuple[str, ...], int]] = []

    def run(self, label, argv, timeout_sec):
        self.calls.append((label, tuple(argv), timeout_sec))
        if label == "usb-inventory":
            return ADAPTER.CommandResult(0, self.usb, b"", True)
        if label == "adb-inventory":
            return ADAPTER.CommandResult(0, self.adb, b"", True)
        if label == "bridge-preflight":
            if self.bridge is None:
                raise AssertionError("unexpected bridge preflight")
            return ADAPTER.CommandResult(0, json.dumps(self.bridge).encode(), b"", True)
        if label == "twrp-identity":
            return ADAPTER.CommandResult(0, b"", b"", True)
        if label == "flash-rollback":
            return ADAPTER.CommandResult(1, b"", b"", True)
        raise AssertionError(f"unexpected command: {label}")


class BackendTest(unittest.TestCase):
    serial = "A90-RECOVERY-SERIAL"

    def setUp(self):
        self.serial_sha = OWNER.sha256_bytes(self.serial.encode())
        self.manifest = {
            "runId": "a90-test-run",
            "candidate": {
                "path": "/tmp/candidate.img", "size": 1, "sha256": "a" * 64,
                "version": "new", "build": "new-build",
            },
            "rollback": {
                "path": "/tmp/rollback.img", "size": 1, "sha256": "b" * 64,
                "version": "old", "build": "old-build",
            },
            "qualification": {
                "recoveryIdentity": {"adbSerialSha256": self.serial_sha},
            },
            "timeouts": {"flashSec": 30, "healthSec": 30},
        }
        self.native_usb = (
            b"Bus 001 Device 001: ID 1d6b:0002 Linux Foundation root hub\n"
            b"Bus 001 Device 002: ID 04e8:6861 A90 Native\n"
        )
        self.empty_adb = b"List of devices attached\n"
        self.recovery_usb = b"Bus 001 Device 002: ID 04e8:6860 A90 Recovery\n"
        self.recovery_adb = (
            b"List of devices attached\n"
            + self.serial.encode()
            + b"\trecovery usb:1-2 product:a90\n"
        )

    def _activation(self, *, phase="resume", checks=None):
        checks = checks or {}
        manifest_sha = OWNER.sha256_bytes(OWNER.canonical_json(self.manifest))

        def manifest_check(value):
            if OWNER.sha256_bytes(OWNER.canonical_json(value)) != manifest_sha:
                raise BACKEND.ActivationError("manifest drift")

        return BACKEND._issue_activation(
            sentinel=BACKEND._ACTIVATION_SENTINEL,
            phase=phase,
            manifest_sha256=manifest_sha,
            run_id=self.manifest["runId"],
            pending_receipt_sha256="d" * 64,
            approval_sha256="e" * 64,
            single_samsung_inventory_sha256=None,
            lease_check=checks.get("lease", lambda: None),
            guard_check=checks.get("guard", lambda: None),
            intent_check=checks.get("intent", lambda: None),
            manifest_check=manifest_check,
            inventory_check=checks.get("inventory", lambda _value: None),
        )

    def _backend(self, runner, *, phase="resume", checks=None):
        backend = BACKEND.CandidateReturnBackend(
            activation=self._activation(phase=phase, checks=checks),
            runner=runner,
        )
        backend.bind_manifest(self.manifest)
        return backend

    @staticmethod
    def _snapshot():
        return OWNER.Snapshot(
            target_evidence_sha256="d" * 64,
            boot_id="01234567-89ab-cdef-0123-456789abcdef",
            version="new",
            build="new-build",
            healthy=True,
            recovery_available=True,
            recovery_evidence_sha256="c" * 64,
            fresh_state_observed=True,
            fresh_state_absent=True,
            other_targets_untouched=False,
            receipt_sha256="e" * 64,
        )

    def test_activation_is_required_before_contact(self):
        runner = FakeRunner(self.native_usb, self.empty_adb)
        with self.assertRaises((TypeError, BACKEND.BackendError)):
            BACKEND.CandidateReturnBackend(runner=runner)
        with self.assertRaises((TypeError, BACKEND.BackendError)):
            BACKEND.create()
        with self.assertRaises(BACKEND.ActivationError):
            BACKEND.create(activation=object())
        self.assertEqual(runner.calls, [])

    def test_stale_activation_fails_before_inventory(self):
        runner = FakeRunner(self.native_usb, self.empty_adb)
        with self.assertRaises(BACKEND.ActivationError):
            self._backend(
                runner,
                checks={"lease": mock.Mock(side_effect=BACKEND.ActivationError("stale"))},
            )
        self.assertEqual(runner.calls, [])

    def test_native_is_exactly_one_samsung_and_zero_adb(self):
        backend = self._backend(FakeRunner(self.native_usb, self.empty_adb))
        inventory = backend._inventory(self.manifest)
        self.assertEqual(inventory.a90_native_count, 1)
        self.assertEqual(inventory.a90_recovery_count, 0)
        self.assertEqual(inventory.adb_role, BACKEND.ADB_ROLE_NATIVE)
        self.assertRegex(inventory.single_samsung_inventory_sha256, r"^[0-9a-f]{64}$")

    def test_recovery_is_exactly_one_samsung_and_one_bound_adb(self):
        backend = self._backend(FakeRunner(self.recovery_usb, self.recovery_adb))
        inventory = backend._inventory(self.manifest)
        self.assertEqual(inventory.a90_recovery_serial, self.serial)
        self.assertEqual(inventory.adb_role, BACKEND.ADB_ROLE_RECOVERY)
        result = backend._classify(self.manifest, inventory, after_physical=False)
        self.assertEqual(result["state"], BACKEND.STATE_TWRP_PRESENT)

    def test_extra_samsung_or_adb_endpoint_is_ambiguous_before_twrp_probe(self):
        cases = (
            (
                self.native_usb + b"Bus 001 Device 003: ID 04e8:6860 Other Samsung\n",
                self.empty_adb,
            ),
            (
                self.native_usb,
                self.empty_adb + b"other device usb:1-3 product:other\n",
            ),
            (
                self.recovery_usb,
                self.recovery_adb + b"other\trecovery usb:1-3 product:other\n",
            ),
        )
        for usb, adb in cases:
            with self.subTest(usb=usb, adb=adb):
                runner = FakeRunner(usb, adb)
                backend = self._backend(runner)
                inventory = backend._inventory(self.manifest)
                result = backend._classify(self.manifest, inventory, after_physical=False)
                self.assertEqual(result["state"], BACKEND.STATE_AMBIGUOUS)
                self.assertNotIn("twrp-identity", [label for label, *_ in runner.calls])

    def test_ambiguous_native_role_cannot_promote_a_valid_snapshot(self):
        ambiguous_usb = self.native_usb + b"Bus 001 Device 003: ID 04e8:6860 Other Samsung\n"
        backend = self._backend(FakeRunner(ambiguous_usb, self.empty_adb))
        inventory = backend._inventory(self.manifest)
        with mock.patch.object(
            backend, "_candidate_snapshot", return_value=self._snapshot()
        ) as observe:
            result = backend._classify(self.manifest, inventory, after_physical=False)
        self.assertEqual(result["state"], BACKEND.STATE_AMBIGUOUS)
        self.assertFalse(result["otherTargetsUntouched"])
        self.assertIsNone(result["candidateSnapshot"])
        observe.assert_not_called()

    def test_wrong_product_or_adb_state_is_ambiguous(self):
        wrong_usb = b"Bus 001 Device 002: ID 04e8:1234 Wrong Samsung\n"
        wrong_adb = (
            b"List of devices attached\n"
            + self.serial.encode()
            + b"\toffline usb:1-2 product:a90\n"
        )
        for usb, adb in ((wrong_usb, self.recovery_adb), (self.recovery_usb, wrong_adb)):
            with self.subTest(usb=usb, adb=adb):
                backend = self._backend(FakeRunner(usb, adb))
                inventory = backend._inventory(self.manifest)
                self.assertEqual(inventory.adb_role, BACKEND.ADB_ROLE_AMBIGUOUS)
                self.assertEqual(
                    backend._classify(self.manifest, inventory, after_physical=False)["state"],
                    BACKEND.STATE_AMBIGUOUS,
                )

    def test_raw_inventory_binding_changes_on_addition_or_reordering(self):
        first = self._backend(FakeRunner(self.native_usb, self.empty_adb))._inventory(self.manifest)
        added = self._backend(
            FakeRunner(
                self.native_usb + b"Bus 001 Device 003: ID 1234:5678 Host device\n",
                self.empty_adb,
            )
        )._inventory(self.manifest)
        reordered = self._backend(
            FakeRunner(b"".join(reversed(self.native_usb.splitlines(keepends=True))), self.empty_adb)
        )._inventory(self.manifest)
        self.assertNotEqual(first.single_samsung_inventory_sha256, added.single_samsung_inventory_sha256)
        self.assertNotEqual(first.single_samsung_inventory_sha256, reordered.single_samsung_inventory_sha256)

    def test_native_snapshot_is_passed_only_after_stable_exact_role(self):
        runner = FakeRunner(self.native_usb, self.empty_adb)
        backend = self._backend(runner)
        inventory = backend._inventory(self.manifest)
        with mock.patch.object(
            backend,
            "_candidate_snapshot",
            return_value=replace(self._snapshot(), other_targets_untouched=True),
        ):
            result = backend._classify(self.manifest, inventory, after_physical=False)
        self.assertEqual(result["state"], BACKEND.STATE_NATIVE_VISIBLE)
        self.assertTrue(result["otherTargetsUntouched"])

    def test_native_snapshot_false_is_never_promoted(self):
        runner = FakeRunner(self.native_usb, self.empty_adb)
        backend = self._backend(runner)
        inventory = backend._inventory(self.manifest)
        snapshot = replace(self._snapshot(), other_targets_untouched=False)
        with mock.patch.object(backend, "_candidate_snapshot", return_value=snapshot):
            result = backend._classify(self.manifest, inventory, after_physical=False)
        self.assertEqual(result["state"], BACKEND.STATE_NATIVE_VISIBLE)
        self.assertFalse(result["otherTargetsUntouched"])
        self.assertFalse(result["candidateSnapshot"]["otherTargetsUntouched"])

    def test_twrp_probe_targets_only_the_bound_serial(self):
        runner = FakeRunner(self.recovery_usb, self.recovery_adb)
        backend = self._backend(runner)
        self.assertEqual(backend._twrp_identity(self.manifest, self.serial), BACKEND.TWRP_IDENTITY)
        command = runner.calls[-1][1]
        self.assertEqual(command[:3], (str(BACKEND.ADB), "-s", self.serial))
        self.assertNotIn("other-serial", command)

    def test_digest_drift_stops_before_rollback_effect(self):
        runner = FakeRunner(self.native_usb, self.empty_adb)
        backend = self._backend(runner)
        native = backend._inventory(self.manifest)
        runner.calls.clear()
        with mock.patch.object(backend, "_observed_single_samsung_inventory_sha256", return_value="f" * 64), mock.patch.object(
            backend, "_inventory", return_value=native
        ):
            with self.assertRaises(BACKEND.BackendError):
                backend.flash(self.manifest["rollback"], rollback=True, timeout_sec=30)
        self.assertEqual(runner.calls, [])

    def test_native_to_recovery_raw_change_is_role_gated_not_digest_compared(self):
        native = self._backend(FakeRunner(self.native_usb, self.empty_adb))._inventory(
            self.manifest
        )
        changed_recovery_usb = (
            b"Bus 007 Device 019: ID 04e8:6860 A90 Recovery after transition\n"
        )
        recovery = self._backend(
            FakeRunner(changed_recovery_usb, self.recovery_adb)
        )._inventory(self.manifest)
        backend = self._backend(FakeRunner(b"unused\n", b"unused\n"))
        backend_inventory = mock.patch.object(
            backend, "_inventory", side_effect=[native, native, recovery]
        )
        bridge = {"generationSha256": "g" * 64, "selectedRealpath": "/dev/ttyACM0", "bridgePid": 1}
        effect_adapter = mock.Mock()
        effect_adapter.flash.return_value = "effect"
        with backend_inventory, mock.patch.object(
            backend, "_observed_single_samsung_inventory_sha256",
            return_value=native.single_samsung_inventory_sha256,
        ), mock.patch.object(backend, "_bridge_preflight", side_effect=[bridge, bridge]), mock.patch.object(
            backend, "_publish_bridge_binding"
        ), mock.patch.object(backend, "_open_rollback_artifact", return_value=mock.Mock(checkpoint=mock.Mock(), close=mock.Mock())), mock.patch.object(
            ADAPTER, "FixedA90Adapter", return_value=effect_adapter
        ):
            self.assertEqual(
                backend.flash(self.manifest["rollback"], rollback=True, timeout_sec=30),
                "effect",
            )
        effect_adapter.flash.assert_called_once()

    def test_wrong_or_multiple_role_blocks_before_rollback_effect(self):
        ambiguous_usb = self.native_usb + b"Bus 001 Device 003: ID 04e8:6860 Extra Samsung\n"
        ambiguous = self._backend(
            FakeRunner(ambiguous_usb, self.empty_adb)
        )._inventory(self.manifest)
        backend = self._backend(FakeRunner(ambiguous_usb, self.empty_adb))
        with mock.patch.object(
            backend, "_observed_single_samsung_inventory_sha256",
            return_value=ambiguous.single_samsung_inventory_sha256,
        ), mock.patch.object(backend, "_inventory", return_value=ambiguous), mock.patch.object(
            ADAPTER.FixedA90Adapter, "flash"
        ) as effect:
            with self.assertRaises(BACKEND.BackendError):
                backend.flash(self.manifest["rollback"], rollback=True, timeout_sec=30)
        effect.assert_not_called()

    def test_already_recovery_raw_drift_blocks_before_effect(self):
        recovery = self._backend(
            FakeRunner(self.recovery_usb, self.recovery_adb)
        )._inventory(self.manifest)
        drift = self._backend(
            FakeRunner(
                b"Bus 001 Device 009: ID 04e8:6860 A90 Recovery drift\n",
                self.recovery_adb,
            )
        )._inventory(self.manifest)
        backend = self._backend(FakeRunner(b"unused\n", b"unused\n"))
        with mock.patch.object(
            backend, "_observed_single_samsung_inventory_sha256",
            return_value=recovery.single_samsung_inventory_sha256,
        ), mock.patch.object(backend, "_inventory", side_effect=[recovery, drift]), mock.patch.object(
            ADAPTER.FixedA90Adapter, "flash"
        ) as effect:
            with self.assertRaises(BACKEND.BackendError):
                backend.flash(self.manifest["rollback"], rollback=True, timeout_sec=30)
        effect.assert_not_called()

    def test_unbound_artifact_shapes_are_rejected_without_runner_effect(self):
        runner = FakeRunner(self.native_usb, self.empty_adb)
        backend = self._backend(runner)
        for artifact in (
            self.manifest["candidate"],
            {**self.manifest["rollback"], "path": "/tmp/other.img"},
            {**self.manifest["rollback"], "size": True},
            {**self.manifest["rollback"], "extra": 1},
        ):
            with self.subTest(artifact=artifact):
                with self.assertRaises(BACKEND.BackendError):
                    backend.flash(artifact, rollback=True, timeout_sec=30)
        self.assertEqual(runner.calls, [])


if __name__ == "__main__":
    unittest.main()
