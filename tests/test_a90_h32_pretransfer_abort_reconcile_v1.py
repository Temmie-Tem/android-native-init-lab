"""Host-only H32 pre-write park and no-replay checks."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / "workspace/public/src/scripts/server-distro"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))


def load(name: str):
    source = MODULE_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class H32PretransferAbortTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.R = load("a90_h32_pretransfer_abort_reconcile_v1")
        cls.O = cls.R._owner
        cls.A = cls.R._adapter
        cls.H31 = load("a90_h31_pretransfer_abort_reconcile_v1")

    def test_exact_h32_identity_and_no_dispatch_log(self):
        self.assertEqual(self.H31.RUN_ID, "a90-h31-f1-20260822-01")
        self.assertEqual(self.H31.CAPABILITY, "A90_H31_PRETRANSFER_ABORT_RECONCILE_V1")
        self.assertEqual(self.R.RUN_ID, "a90-h32-f1-20260822-01")
        self.assertEqual(self.R.CANDIDATE["version"], "0.11.199")
        self.assertEqual(
            self.R.CANDIDATE["sha256"],
            "e56cb1201d63e26f275de10d6a4eb6a1686f6021b6613aa4dde1374930dd299d",
        )
        self.assertEqual(
            tuple(self.R.RECORD_HASHES),
            (
                "00-prepared.json",
                "10-approved.json",
                "20-candidate-intent.json",
                "21-candidate-launched.json",
                "22-candidate-result.json",
                "30-rollback-intent.json",
                "31-rollback-launched.json",
            ),
        )
        self.assertNotIn("flash-rollback.stdout", self.R.LOG_HASHES)
        self.assertNotIn("flash-rollback.stderr", self.R.LOG_HASHES)
        self.assertEqual(
            tuple(self.R.BUSY_OBSERVATION_LOG_HASHES),
            (
                "001-usb-inventory.stdout", "001-usb-inventory.stderr",
                "002-bridge-preflight.stdout", "002-bridge-preflight.stderr",
                "003-boot-id-start.stdout", "003-boot-id-start.stderr",
            ),
        )
        self.assertEqual(
            self.R.BUSY_OBSERVATION_LOG_SET_SHA256,
            "d5a0f200c928d88630eb2056f57e9f7964a8706ae3da70819cf8b16a6f3b7d81",
        )

    def test_candidate_receipt_is_pre_write_failure(self):
        if not self.R.LOG_DIRECTORY.is_dir():
            self.skipTest("private H32 execute logs are not present")
        stdout, _stderr = self.R._engine._require_logs()
        self.assertEqual(self.A._parse_owner_effect_receipt(stdout), "PRE_WRITE_FAILURE")

    def test_reconciliation_payload_cannot_claim_rollback_dispatch(self):
        manifest = {
            "rollback": self.R.ROLLBACK,
            "qualification": {"review": {"sha256": "b" * 64}},
        }
        snapshot = self.O.Snapshot(
            target_evidence_sha256="a" * 64,
            boot_id="01234567-89ab-cdef-0123-456789abcdef",
            version=self.R.ROLLBACK["version"],
            build=self.R.ROLLBACK["build"],
            healthy=True,
            recovery_available=True,
            recovery_evidence_sha256="b" * 64,
            fresh_state_observed=False,
            fresh_state_absent=False,
            other_targets_untouched=True,
            receipt_sha256="c" * 64,
        )
        payload = {
            "schema": self.R.SCHEMA,
            "decision": self.R.DECISION,
            "candidateReplay": False,
            "rollbackReplay": False,
            "candidateRetryPermitted": False,
            "currentReviewSha256": "d" * 64,
            "candidate": {
                "receiptSha256": self.R.CANDIDATE_RECEIPT_SHA256,
                "outcome": "PRE_WRITE_FAILURE",
                "transferStarted": False,
                "bootWriteStarted": False,
            },
            "rollback": {
                "intentRecorded": True,
                "launchedRecorded": True,
                "helperDispatched": False,
                "helperLogPresent": False,
                "transferStarted": False,
                "bootWriteStarted": False,
            },
            "recoveredSnapshot": snapshot.payload(),
        }
        self.R._engine._validate_payload(payload, manifest, "d" * 64)
        payload["rollback"] = dict(payload["rollback"])
        payload["rollback"]["helperDispatched"] = True
        with self.assertRaisesRegex(self.R.ContractError, "rollback reconciliation"):
            self.R._engine._validate_payload(payload, manifest, "d" * 64)

    def test_reconciler_source_has_no_effect_primitive(self):
        source = Path(self.R.__file__).read_text()
        for forbidden in ("adb push", "boot_dd_write", "twrp reboot", "flash-rollback"):
            self.assertNotIn(forbidden, source)

    def test_h32_closure_is_not_owner_only(self):
        current = self.R.execution_closure_sha256()
        with mock.patch.object(self.R._owner, "execution_closure_sha256", return_value="a" * 64):
            self.assertNotEqual(self.R.execution_closure_sha256(), current)

    def test_h32_closure_includes_same_length_h31_engine_bytes(self):
        original = Path.read_bytes
        current = self.R.execution_closure_sha256()

        def altered(path: Path) -> bytes:
            raw = original(path)
            if path == self.R._ENGINE_PATH:
                return b"X" + raw[1:]
            return raw

        with mock.patch.object(Path, "read_bytes", new=altered):
            self.assertNotEqual(self.R.execution_closure_sha256(), current)

    def test_h32_closure_includes_h28_hide_engine(self):
        original = Path.read_bytes
        current = self.R.execution_closure_sha256()

        def altered(path: Path) -> bytes:
            raw = original(path)
            return b"X" + raw[1:] if path == self.R._H28_PATH else raw

        with mock.patch.object(Path, "read_bytes", new=altered):
            self.assertNotEqual(self.R.execution_closure_sha256(), current)

    def test_h32_closure_includes_h28_transitive_inputs(self):
        original = Path.read_bytes
        paths = (
            self.R._owner.REPO_ROOT / "workspace/public/src/scripts/server-distro/a90_h28_physical_system_return_reconcile_v1.py",
            self.R._owner.REPO_ROOT / "docs/plans/A90_H28_MENU_HIDE_HEALTH_RECONCILIATION_DESIGN_2026-08-21.md",
            self.R._owner.REPO_ROOT / "AGENTS.md",
            self.R._owner.REPO_ROOT / "GOAL_A90.md",
        )
        for target in paths:
            with self.subTest(target=target):
                current = self.R.execution_closure_sha256()

                def altered(path: Path, target=target) -> bytes:
                    raw = original(path)
                    return b"X" + raw[1:] if path == target else raw

                with mock.patch.object(Path, "read_bytes", new=altered):
                    self.assertNotEqual(self.R.execution_closure_sha256(), current)

    def test_exact_busy_boot_id_receipt_and_adversarial_rejections(self):
        raw = self.O.canonical_json({
            "begin": {"seq": "1", "cmd": "cat", "argc": "2", "flags": "0x0"},
            "end": {"seq": "1", "cmd": "cat", "rc": "-16", "errno": "16", "duration_ms": "0", "flags": "0x0", "status": "busy"},
            "rc": -16,
            "status": "busy",
            "trust": "A90P1_V1_STRUCTURAL_ONLY",
            "text": "[busy] auto menu active; send hide/q before command\n",
        })
        self.R._validate_busy_boot_receipt(raw)
        for mutate in (
            lambda value: value.update(status="ok"),
            lambda value: value["begin"].update(seq="2"),
            lambda value: value["end"].update(errno="0"),
        ):
            value = self.O.parse_canonical(raw, "busy receipt")
            mutate(value)
            with self.assertRaises(self.R.ContractError):
                self.R._validate_busy_boot_receipt(self.O.canonical_json(value))

    def test_menu_hide_intent_is_one_shot_and_receipt_is_durable(self):
        with tempfile.TemporaryDirectory() as temporary:
            old_root = self.R.MENU_HIDE_SIDE_ROOT
            self.R.MENU_HIDE_SIDE_ROOT = Path(temporary) / "sidecar"
            try:
                intent = self.R._publish_menu_hide_intent()
                self.assertRegex(intent, r"^[0-9a-f]{64}$")
                with self.assertRaisesRegex(self.R.ContractError, "must not replay"):
                    self.R._publish_menu_hide_intent()
                self.R._publish_menu_hide_receipt(intent, "e" * 64)
                self.assertEqual(
                    set(path.name for path in self.R.MENU_HIDE_SIDE_ROOT.iterdir()),
                    {self.R.MENU_HIDE_INTENT_NAME, self.R.MENU_HIDE_RECEIPT_NAME},
                )
            finally:
                self.R.MENU_HIDE_SIDE_ROOT = old_root

    def test_menu_hide_sidecar_parent_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old_root = self.R.MENU_HIDE_SIDE_ROOT
            try:
                for label in ("symlink", "mode", "foreign"):
                    with self.subTest(label=label):
                        parent = root / label
                        if label == "symlink":
                            target = root / "symlink-target"
                            target.mkdir(mode=0o700)
                            parent.symlink_to(target, target_is_directory=True)
                        elif label == "mode":
                            parent.mkdir(mode=0o700)
                            parent.chmod(0o755)
                        else:
                            parent.write_bytes(b"not-a-directory")
                        self.R.MENU_HIDE_SIDE_ROOT = parent / "sidecar"
                        with self.assertRaisesRegex(self.R.ContractError, "parent identity"):
                            self.R._publish_menu_hide_intent()
            finally:
                self.R.MENU_HIDE_SIDE_ROOT = old_root

    def test_fresh_observation_uses_one_h28_hide_observer(self):
        snapshot = self.O.Snapshot(
            target_evidence_sha256="a" * 64,
            boot_id="01234567-89ab-cdef-0123-456789abcdef",
            version=self.R.ROLLBACK["version"],
            build=self.R.ROLLBACK["build"],
            healthy=True,
            recovery_available=True,
            recovery_evidence_sha256="d" * 64,
            fresh_state_observed=False,
            fresh_state_absent=False,
            other_targets_untouched=True,
            receipt_sha256="b" * 64,
        )
        observation = types.SimpleNamespace(
            snapshot=snapshot, hide_receipt_sha256="e" * 64
        )
        manifest = {
            "rollback": self.R.ROLLBACK,
            "timeouts": {"healthSec": 7},
            "qualification": {
                "recoveryIdentity": {"adbSerialSha256": "c" * 64},
                "review": {"sha256": "d" * 64},
            },
        }
        fake_observer = mock.Mock()
        fake_observer.observe.return_value = observation
        with (
            mock.patch.object(self.R, "_require_busy_observation_logs"),
            mock.patch.object(self.R, "_publish_menu_hide_intent", return_value="f" * 64),
            mock.patch.object(self.R._h28.adapter, "HostRunner", return_value=object()),
            mock.patch.object(self.R._h28, "MenuHideObserver", return_value=fake_observer),
            mock.patch.object(self.R._h28, "_validate_observation"),
            mock.patch.object(self.R, "_publish_menu_hide_receipt") as publish_receipt,
        ):
            self.assertIs(self.R._h32_fresh_v2321_observation(manifest), snapshot)
        fake_observer.observe.assert_called_once_with(self.R.ROLLBACK, timeout_sec=7)
        publish_receipt.assert_called_once_with("f" * 64, "e" * 64)

    def test_h32_wrapper_has_no_public_engine_forwarding_or_h31_mutation(self):
        self.assertFalse(hasattr(self.R, "owner"))
        self.assertFalse(hasattr(self.R, "adapter"))
        self.assertFalse(hasattr(self.R, "_fresh_v2321_observation"))
        self.assertEqual(self.H31.RUN_ID, "a90-h31-f1-20260822-01")
        self.assertEqual(self.H31.CAPABILITY, "A90_H31_PRETRANSFER_ABORT_RECONCILE_V1")


if __name__ == "__main__":
    unittest.main()
