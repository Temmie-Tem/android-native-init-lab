from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


class A90H17UfsExecutionV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.f1 = load_script(
            "workspace/public/src/scripts/server-distro/a90_h17_ufs_f1_runner_v1.py"
        )
        cls.d1 = load_script(
            "workspace/public/src/scripts/server-distro/a90_h17_ufs_d1_runner_v1.py"
        )

    def _baseline(self) -> tuple[dict, dict]:
        f1 = self.f1
        native = {
            "exact_bridge": True,
            "version": {
                "command": ["version"],
                "rc": 0,
                "text": f"{f1.CURRENT_VERSION} {f1.CURRENT_BUILD}",
            },
            "selftest": {
                "command": ["selftest"],
                "rc": 0,
                "text": "pass=11 warn=1 fail=0",
            },
        }
        first_boot = {
            "proof": True,
            "enable": 0,
            "latch": 0,
            "status": {
                "command": ["auto-handoff-status"],
                "rc": 0,
                "text": "binding=1 enable=0 latch=0",
            },
        }
        manifest = {
            "schema": "a90-h16-ufs-f1-manifest-v1",
            "capability": "A90_DIRECT_UFS_READONLY_ROOT_V2",
            "execution_closure": {
                "sha256": f1.CURRENT_INSTALL_EXECUTION_CLOSURE_SHA256
            },
            "candidate_boot": {
                "expected_version": f1.CURRENT_VERSION,
                "expected_build": f1.CURRENT_BUILD,
                "size": f1.CURRENT_BOOT_SIZE,
                "sha256": f1.CURRENT_BOOT_SHA256,
            },
            "rollback_boot": {
                "expected_version": f1.ROLLBACK_VERSION,
                "expected_build": f1.ROLLBACK_BUILD,
                "size": f1.ROLLBACK_SIZE,
                "sha256": f1.ROLLBACK_SHA256,
            },
        }
        result = {
            "schema": "a90-h16-ufs-f1-result-v1",
            "status": "PASS_A90_H16_UFS_RESIDENT_INSTALLED",
            "device_safety_state": "RESIDENT_HEALTHY",
            "candidate_attempt_count": 1,
            "candidate_transfer_count": 1,
            "rollback_transfer_count": 0,
            "candidate_replay": False,
            "rootfs_payload_count": 0,
            "sd_stage_count": 0,
            "userdata_write_count": 0,
            "final_health": {"native": native, "first_boot": first_boot},
        }
        return manifest, result

    def _receipt(self, candidate: Path, observer_sha: str) -> dict:
        f1 = self.f1
        resolution = f1.flat_buildlib.resolve_manifest(
            f1.REPO_ROOT / f1.VERSION_MANIFEST_REL
        )
        source_keys = {}
        for role, relative in (
            (
                "flat_builder",
                "workspace/public/src/scripts/revalidation/a90_flat_builder/build.py",
            ),
            (
                "flat_builder_library",
                "workspace/public/src/scripts/revalidation/a90_flat_builder/buildlib.py",
            ),
        ):
            bound = f1.bound_file(f1.REPO_ROOT / relative)
            source_keys[role] = {
                "path": relative,
                "size": bound["size"],
                "sha256": bound["sha256"],
            }
        return {
            "schema": "a90-flat-builder-v1-ab-receipt",
            "profile": f1.CANDIDATE_BUILD,
            "byte_identical": True,
            "candidate_authority": False,
            "accepted_boot_unchanged": True,
            "manifest_sha256": f1.sha256_file(
                f1.REPO_ROOT / f1.VERSION_MANIFEST_REL
            ),
            "manifest_lineage": [
                {
                    "path": path.relative_to(f1.REPO_ROOT).as_posix(),
                    "sha256": f1.sha256_file(path),
                }
                for path in resolution.lineage
            ],
            "input_pins": {
                "init_closure_sha256": f1.NATIVE_CLOSURE_SHA256,
                "observer_authorized_key_sha256": observer_sha,
                "h17_firstboot_sha256": f1.sha256_file(
                    f1.REPO_ROOT / f1.FIRSTBOOT_REL
                ),
            },
            "source_keys": source_keys,
            "artifacts": {
                "boot": {
                    "path": "boot.img",
                    "bytes": candidate.stat().st_size,
                    "sha256": f1.sha256_file(candidate),
                }
            },
            "auto_handoff_binding": f1.expected_compiled_binding(),
        }

    def test_f1_identity_is_h17_only(self) -> None:
        self.assertEqual(self.f1.CAPABILITY, "A90_H17_PERSISTENT_UFS_SERVER_V1")
        self.assertEqual(self.f1.CURRENT_VERSION, "0.11.184")
        self.assertEqual(self.f1.CANDIDATE_VERSION, "0.11.185")
        self.assertIn("persistent-hud", self.f1.CANDIDATE_BUILD)

    def test_compiled_binding_is_v5_auth_and_hud(self) -> None:
        binding = self.f1.expected_compiled_binding()
        self.assertEqual(binding["schema"], "a90-compiled-auto-handoff-binding-v5")
        self.assertEqual(binding["observer_auth"], "boot-private-tmpfs-v1")
        self.assertEqual(binding["display_owner"], "native-handoff-hud-v1")
        content = {key: value for key, value in binding.items() if key != "binding_sha256"}
        self.assertEqual(binding["binding_sha256"], self.f1.json_sha256(content))

    def test_ab_receipt_binds_private_observer_identity_without_public_literal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary) / "boot.img"
            candidate.write_bytes(b"boot")
            observer_sha = "a" * 64
            value = self._receipt(candidate, observer_sha)
            self.assertEqual(
                self.f1.validate_ab_receipt(value, candidate, observer_sha),
                self.f1.expected_compiled_binding(),
            )

    def test_ab_receipt_rejects_observer_key_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary) / "boot.img"
            candidate.write_bytes(b"boot")
            value = self._receipt(candidate, "a" * 64)
            with self.assertRaisesRegex(self.f1.ContractError, "receipt"):
                self.f1.validate_ab_receipt(value, candidate, "b" * 64)

    def test_ab_receipt_rejects_firstboot_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary) / "boot.img"
            candidate.write_bytes(b"boot")
            value = self._receipt(candidate, "a" * 64)
            value["input_pins"]["h17_firstboot_sha256"] = "b" * 64
            with self.assertRaisesRegex(self.f1.ContractError, "receipt"):
                self.f1.validate_ab_receipt(value, candidate, "a" * 64)

    def test_h16_predecessor_requires_exact_installed_boot(self) -> None:
        manifest, result = self._baseline()
        self.f1._baseline_inputs(manifest, result)
        manifest["candidate_boot"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(self.f1.ContractError, "H16 resident"):
            self.f1._baseline_inputs(manifest, result)

    def test_host_capability_qualification_remains_exact(self) -> None:
        value = self.f1.validate_host_capability_qualification()
        self.assertEqual(value["verdict"], "PASS_GO")
        self.assertFalse(value["f1_runner_qualified"])
        self.assertFalse(value["d1_runner_qualified"])

    def test_execution_qualification_requires_both_runners(self) -> None:
        closure = self.f1.execution_closure()
        value = {
            "schema": self.f1.QUALIFICATION_SCHEMA,
            "capability": self.f1.CAPABILITY,
            "verdict": "PASS_GO",
            "predecessor_capability_closure_sha256": (
                self.f1.HOST_CAPABILITY_CLOSURE_SHA256
            ),
            "execution_closure_sha256": closure["sha256"],
            "execution_hashes": closure["files"],
            "review_scope": (
                "h17-boot-only-f1-and-persistent-ufs-d1-execution-critical-closure"
            ),
            "new_hazard_or_incident": True,
            "ordinal_requalification_required": False,
            "f1_runner_qualified": True,
            "d1_runner_qualified": True,
            "live_authority": False,
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "qualification.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            binding = self.f1.bound_file(path)
            self.f1.validate_qualification(binding, closure)
            value["d1_runner_qualified"] = False
            path.unlink()
            path.write_text(json.dumps(value), encoding="utf-8")
            binding = self.f1.bound_file(path)
            with self.assertRaisesRegex(self.f1.ContractError, "qualification"):
                self.f1.validate_qualification(binding, closure)

    def test_d1_journal_has_pending_then_physical_return_close(self) -> None:
        self.assertEqual(self.d1.JOURNAL_ACTIONS[4:], (
            "current-state",
            "final-health",
            "closed",
        ))
        self.assertEqual(len(self.d1.JOURNAL_NAMES), 7)

    def test_approval_binds_persistent_mode_and_observer(self) -> None:
        manifest = {
            "run_id": "a90-h17-ufs-f1-20260810-01",
            "target": {
                "profile": "galaxy-a90-5g-native-init",
                "bridge_device": "bridge",
                "bridge_realpath": "/dev/ttyACM0",
                "recovery_adb_identity_evidence": {"proof": True},
            },
            "observer": {
                "private_key": {"sha256": "a" * 64},
                "public_key_sha256": "b" * 64,
            },
        }
        args = argparse.Namespace(
            expect_manifest_sha256="c" * 64,
            expect_install_result_sha256="d" * 64,
            expect_execution_closure_sha256="e" * 64,
        )
        value = self.d1.approval_binding(
            manifest,
            args,
            Path("/private/run01"),
            created_utc="2026-08-10T00:00:00Z",
            expires_utc="2026-08-10T00:30:00Z",
        )
        self.assertTrue(value["persistent_debian_expected"])
        self.assertFalse(value["automatic_native_return_expected"])
        self.assertFalse(value["physical_return_dispatched_by_runner"])
        self.assertEqual(value["observer_public_key_sha256"], "b" * 64)

    def test_live_result_pass_stays_health_pending_and_open(self) -> None:
        result = self.d1._live_result(
            {"server": {"proof": True}, "guard_release": {"released": True}},
            "a" * 64,
            "yes",
        )
        self.assertEqual(result["status"], "PASS_A90_H17_PERSISTENT_SERVER_LIVE")
        self.assertEqual(
            result["device_safety_state"], "HEALTH_PENDING_PERSISTENT_DEBIAN"
        )
        self.assertFalse(result["resident_healthy"])
        self.assertFalse(result["ordinal_closed"])
        self.assertFalse(result["inter_effect_health_barrier_satisfied"])
        self.assertFalse(result["new_device_effect_authority"])

    def test_live_result_refuses_unconfirmed_visibility(self) -> None:
        result = self.d1._live_result(
            {"server": {"proof": True}, "guard_release": {"released": True}},
            "a" * 64,
            "unavailable",
        )
        self.assertEqual(result["status"], "NO_PROOF_A90_H17_PERSISTENT_SERVER_LIVE")

    def test_persistent_observation_never_waits_for_native_return(self) -> None:
        guard = mock.Mock()
        with mock.patch.object(
            self.d1.legacy, "wait_for_bound_ncm_after_reboot", return_value={"ncm": True}
        ), mock.patch.object(
            self.d1.legacy, "rebind_host_ncm_for_bound_identity", return_value={"ok": True}
        ), mock.patch.object(
            self.d1.legacy, "validate_post_reboot_ncm_identity"
        ), mock.patch.object(
            self.d1.persistent_observer,
            "observe",
            return_value={"proof": True},
        ), mock.patch.object(
            self.d1.base,
            "release_candidate_return_modemmanager_guard",
            return_value={"released": True},
        ), mock.patch.object(
            self.d1.legacy,
            "wait_for_native_return_after_bound_ncm",
        ) as native_return:
            result = self.d1._observe(
                SimpleNamespace(observer_key=Path("key")),
                argparse.Namespace(visible_confirmed="yes"),
                Path("transaction"),
                guard,
                {"binding": True},
                "yes",
            )
        self.assertTrue(result["proof"])
        native_return.assert_not_called()

    def test_dispatch_writes_no_closed_record(self) -> None:
        writes: list[tuple[int, str]] = []
        with mock.patch.object(
            self.d1.legacy, "require_pre_reboot_observer_binding_current"
        ), mock.patch.object(
            self.d1, "require_status"
        ), mock.patch.object(
            self.d1, "_arm_reboot_once", return_value={"dispatch": True}
        ), mock.patch.object(
            self.d1,
            "_observe",
            return_value={
                "server": {"proof": True},
                "guard_release": {"released": True},
            },
        ), mock.patch.object(
            self.d1,
            "_write_record",
            side_effect=lambda _directory, index, action, _payload: writes.append(
                (index, action)
            ),
        ):
            guard = mock.Mock()
            guard.healthy.return_value = True
            self.d1._dispatch_and_observe(
                object(),
                argparse.Namespace(visible_confirmed="yes"),
                Path("transaction"),
                guard,
                {"binding": True},
                "a" * 64,
                "yes",
            )
        self.assertEqual(
            writes,
            [(2, "dispatch-result"), (3, "persistent-observation"), (4, "current-state")],
        )

    def test_userdata_probe_is_read_only_and_runtime_devt(self) -> None:
        script = self.d1._unmounted_script()
        self.assertIn("^PARTNAME=userdata$", script)
        self.assertIn("runtime", self.d1.f1.UFS_IDENTITY["devt_policy"])
        for forbidden in (" rm ", "reboot", "switch_root", " dd ", "mkfs", "mount -"):
            self.assertNotIn(forbidden, script)

    def test_userdata_probe_accepts_dynamic_exact_devt(self) -> None:
        record = {
            "command": ["placeholder"],
            "text": "A90H17_POST_PHYSICAL_RETURN devt=260:9 "
            "ufs_mount_count=0 userdata_write=0\n",
        }
        with mock.patch.object(self.d1.base, "run_f1_cmd", return_value=record), mock.patch.object(
            self.d1.base, "require_exact_f1_command_receipt", return_value=record
        ):
            value = self.d1._prove_userdata_unmounted(argparse.Namespace())
        self.assertEqual(value["device"], "260:9")
        self.assertEqual(value["devt_policy"], "runtime-resolved-same-session")

    def test_same_intent_probe_requires_exact_enable_latch_and_evidence_bytes(self) -> None:
        intent = "a" * 64
        enable = self.d1.hashlib.sha256(
            self.d1._expected_h17_state(intent, "armed-after-native-health")
        ).hexdigest()
        latch = self.d1.hashlib.sha256(
            self.d1._expected_h17_state(
                intent,
                "automatic-handoff-dispatched-no-replay",
            )
        ).hexdigest()
        evidence = self.d1.hashlib.sha256((intent + "\n").encode()).hexdigest()
        record = {
            "text": "A90H17_INTENT_BINDING "
            f"intent={intent} enable_sha256={enable} "
            f"latch_sha256={latch} evidence_sha256={evidence}\n"
        }
        with mock.patch.object(self.d1.base, "run_f1_cmd", return_value=record), mock.patch.object(
            self.d1.base, "require_exact_f1_command_receipt", return_value=record
        ):
            value = self.d1.require_same_intent_state(argparse.Namespace(), intent)
        self.assertTrue(value["proof"])
        self.assertEqual(value["intent_sha256"], intent)

    def test_same_intent_probe_rejects_foreign_latched_intent(self) -> None:
        current = "a" * 64
        foreign = "b" * 64
        record = {
            "text": "A90H17_INTENT_BINDING "
            f"intent={foreign} enable_sha256={'c' * 64} "
            f"latch_sha256={'d' * 64} evidence_sha256={'e' * 64}\n"
        }
        with mock.patch.object(self.d1.base, "run_f1_cmd", return_value=record), mock.patch.object(
            self.d1.base, "require_exact_f1_command_receipt", return_value=record
        ), self.assertRaisesRegex(self.d1.ContractError, "intent binding"):
            self.d1.require_same_intent_state(argparse.Namespace(), current)

    def test_physical_return_confirmation_is_mandatory(self) -> None:
        for attended, confirmed in ((False, False), (True, False), (False, True)):
            args = argparse.Namespace(
                operator_attended=attended,
                physical_return_confirmed=confirmed,
            )
            with self.assertRaisesRegex(self.d1.ContractError, "attended confirmation"):
                self.d1.finalize_physical_return(args)

    def test_physical_return_from_intent_prefix_fills_evidence_without_replay(self) -> None:
        records: list[dict] = [
            {"opening": True},
            {"pre_reboot_binding": {"bound": True}},
        ]
        writes: list[tuple[int, str]] = []

        def write(_directory: Path, index: int, action: str, payload: dict) -> None:
            self.assertEqual(index, len(records))
            writes.append((index, action))
            records.append({"action": action, **payload})

        args = argparse.Namespace(
            operator_attended=True,
            physical_return_confirmed=True,
            transaction_dir=Path("transaction"),
        )
        with mock.patch.object(
            self.d1, "load_inputs", return_value=({}, mock.Mock(stage=object()), {})
        ), mock.patch.object(
            self.d1, "_require_transaction_dir", return_value=Path("transaction")
        ), mock.patch.object(
            self.d1, "_read_records", side_effect=lambda _directory: list(records)
        ), mock.patch.object(
            self.d1, "_validate_records", return_value="a" * 64
        ), mock.patch.object(
            self.d1.base.staging, "require_exact_bridge"
        ), mock.patch.object(
            self.d1,
            "require_status",
            return_value=({"record": True}, {"binding": 1, "enable": 1, "latch": 1}),
        ), mock.patch.object(
            self.d1.base, "verify_candidate_health", return_value={"healthy": True}
        ), mock.patch.object(
            self.d1, "_prove_userdata_unmounted", return_value={"proof": True}
        ), mock.patch.object(
            self.d1,
            "require_same_intent_state",
            return_value={"proof": True, "intent_sha256": "a" * 64},
        ), mock.patch.object(
            self.d1, "_write_record", side_effect=write
        ), mock.patch.object(
            self.d1, "_arm_reboot_once"
        ) as replay:
            result = self.d1.finalize_physical_return(args)
        replay.assert_not_called()
        self.assertEqual(
            writes,
            [
                (2, "dispatch-result"),
                (3, "persistent-observation"),
                (4, "current-state"),
                (5, "final-health"),
                (6, "closed"),
            ],
        )
        self.assertEqual(result["device_safety_state"], "RESIDENT_HEALTHY")
        self.assertFalse(result["live_server_proven"])
        self.assertEqual(result["physical_return_reboot_dispatch_count"], 0)
        self.assertTrue(result["inter_effect_health_barrier_satisfied"])
        self.assertFalse(result["new_device_effect_authority"])

    def test_six_record_physical_return_resume_only_appends_close(self) -> None:
        current = {"device_safety_state": "HEALTH_PENDING_PERSISTENT_DEBIAN"}
        final = {"status": "healthy"}
        records = [{}, {}, {}, {}, {"result": current}, {"result": final, "result_sha256": "a" * 64}]
        writes: list[tuple[int, str]] = []
        args = argparse.Namespace(
            operator_attended=True,
            physical_return_confirmed=True,
            transaction_dir=Path("transaction"),
        )
        with mock.patch.object(
            self.d1, "load_inputs", return_value=({}, object(), {})
        ), mock.patch.object(
            self.d1, "_require_transaction_dir", return_value=Path("transaction")
        ), mock.patch.object(
            self.d1, "_read_records", return_value=records
        ), mock.patch.object(
            self.d1, "_validate_records", return_value="b" * 64
        ), mock.patch.object(
            self.d1,
            "_write_record",
            side_effect=lambda _directory, index, action, _payload: writes.append(
                (index, action)
            ),
        ), mock.patch.object(
            self.d1.base, "verify_candidate_health"
        ) as device_contact:
            result = self.d1.finalize_physical_return(args)
        self.assertEqual(result, final)
        self.assertEqual(writes, [(6, "closed")])
        device_contact.assert_not_called()

    def test_reconcile_live_pending_uses_durable_state_without_native_contact(self) -> None:
        current = {
            "device_safety_state": "HEALTH_PENDING_PERSISTENT_DEBIAN",
            "ordinal_closed": False,
        }
        records = [{}, {}, {}, {}, {"result": current}]
        args = argparse.Namespace(transaction_dir=Path("transaction"))
        with mock.patch.object(
            self.d1, "load_inputs", return_value=({}, object(), {})
        ), mock.patch.object(
            self.d1, "_require_transaction_dir", return_value=Path("transaction")
        ), mock.patch.object(
            self.d1, "_read_records", return_value=records
        ), mock.patch.object(
            self.d1, "_validate_records"
        ), mock.patch.object(
            self.d1.base, "run_f1_cmd"
        ) as device_contact:
            value = self.d1.reconcile(args)
        self.assertEqual(
            value["terminal"], "PERSISTENT_DEBIAN_LIVE_HEALTH_PENDING_NO_REPLAY"
        )
        device_contact.assert_not_called()

    def test_cli_exposes_physical_return_not_automatic_return(self) -> None:
        options = self.d1.parser()._option_string_actions
        self.assertIn("--finalize-physical-return", options)
        self.assertIn("--physical-return-confirmed", options)
        self.assertNotIn("--finalize-return", options)


if __name__ == "__main__":
    unittest.main()
