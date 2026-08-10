from __future__ import annotations

import argparse
import copy
import unittest
from unittest import mock

from _loader import load_script


class A90H17NativeFallbackFinalizerV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_script(
            "workspace/public/src/scripts/server-distro/"
            "a90_h17_native_fallback_finalizer_v1.py"
        )

    def _terminal(self, closure_sha: str = "a" * 64) -> dict:
        def receipt(command: str, text: str) -> dict:
            return {
                "command": [command],
                "rc": 0,
                "status": "ok",
                "trust": "A90P1_V1_STRUCTURAL_ONLY",
                "begin": {},
                "end": {},
                "text": text,
            }

        version = receipt(
            "version",
            f"{self.module.H17_BOOT_DETAIL}\n"
            f"version: {self.module.f1.CANDIDATE_VERSION} "
            f"build={self.module.f1.CANDIDATE_BUILD}\n",
        )
        status = receipt(
            "status",
            "\n".join(
                (
                    "pstore=available entries=0",
                    f"init: {self.module.H17_BOOT_DETAIL}",
                    "selftest: pass=11 warn=1 fail=0",
                    "pid1guard: pass=12 warn=0 fail=0",
                    "autohud: running",
                    "transport.ncm=ready",
                    "transport.tcpctl=ready",
                    "",
                )
            ),
        )
        selftest = receipt(
            "selftest",
            "selftest: pass=11 warn=1 fail=0 duration=1ms entries=12\n",
        )
        approval_binding = self.module._approval_binding(
            {"sha256": closure_sha},
            created_utc="2026-08-10T00:00:00Z",
            expires_utc="2026-08-10T00:30:00Z",
        )
        return {
            "schema": "a90-h17-ufs-d1-result-v1",
            "status": "REFUTED_H17_PERSISTENT_SERVER_NATIVE_FALLBACK_HEALTHY",
            "incident": "H17_POST_ROOT_MOUNT_NATIVE_FALLBACK",
            "intent_sha256": self.module.INTENT_SHA256,
            "prior_current_result_sha256": (
                "7a702f27a1f68d082d117e289aaba775e57926e760f6d0359ef2b5e4b07d6b5a"
            ),
            "predecessor_execution_closure_sha256": (
                self.module.PREDECESSOR_EXECUTION_SHA256
            ),
            "finalizer_execution_closure_sha256": closure_sha,
            "read_only_approval_binding": approval_binding,
            "read_only_approval_binding_sha256": self.module.f1.json_sha256(
                approval_binding
            ),
            "device_safety_state": "RESIDENT_HEALTHY",
            "resident_healthy": True,
            "ordinal_closed": True,
            "inter_effect_health_barrier_satisfied": True,
            "new_device_effect_authority": False,
            "experiment_proof": "REFUTED",
            "automatic_native_fallback": True,
            "automatic_native_return": False,
            "operator_physical_return": False,
            "persistent_debian_reached": False,
            "switch_root_exec_proven": False,
            "persistent_server_proven": False,
            "authenticated_ssh_proven": False,
            "debian_pid1_proven": False,
            "persistent_hud_proven": False,
            "display_visible_proven": False,
            "final_wifi_proven": False,
            "candidate_replay": False,
            "arm_dispatch_count": 1,
            "reboot_dispatch_count": 1,
            "handoff_dispatch_count": 1,
            "physical_return_reboot_dispatch_count": 0,
            "payload_transfer_count": 0,
            "partition_write_count": 0,
            "flash_count": 0,
            "sd_rootfs_stage_count": 0,
            "userdata_write_count": 0,
            "native_health": {
                "exact_bridge": True,
                "selected_realpath": "/dev/ttyACM0",
                "version": version,
                "status": status,
                "selftest": selftest,
                "facts": {
                    "pass": 11,
                    "warn": 1,
                    "fail": 0,
                    "duration_ms": 1,
                    "entries": 12,
                    "pstore_entries": 0,
                },
            },
            "native_status": {
                "proof": True,
                "required_markers": [
                    f"init: {self.module.H17_BOOT_DETAIL}",
                    "selftest: pass=11 warn=1 fail=0",
                    "pid1guard: pass=12 warn=0 fail=0",
                    "autohud: running",
                    "transport.ncm=ready",
                    "transport.tcpctl=ready",
                ],
                "record": status,
            },
            "auto_handoff_status": {
                "binding": 1,
                "enable": 1,
                "latch": 1,
                "build": self.module.f1.CANDIDATE_BUILD,
            },
            "auto_handoff_status_record": {},
            "same_intent_binding": {
                "proof": True,
                "intent": self.module.INTENT_SHA256,
                "userdata_write_count": 0,
                "record": {},
            },
            "native_fallback_proof": {
                "proof": True,
                "intent_sha256": self.module.INTENT_SHA256,
                "root_mounted": True,
                "writable_set_ready": False,
                "switch_root_exec": False,
                "cleanup_clean": True,
                "recovery_required": False,
                "candidate_replay": False,
                "userdata_write_count": 0,
            },
            "post_fallback_userdata": {
                "proof": True,
                "device": "259:17",
                "identity": "sole-PARTNAME-userdata-DEVNAME-sda33-runtime-devt",
                "mount_count": 0,
                "userdata_write_count": 0,
                "record": {},
            },
            "diagnosis_binding": {
                "proof": True,
                "sha256": self.module.DIAGNOSIS_SHA256,
                "fallback": {"proof": True},
            },
            "final_bridge": {"selected_realpath": "/dev/ttyACM0"},
            "durable_log_record": {},
            "original_observation": {
                "proof": False,
                "guard_release": {"released": True},
            },
        }

    def test_execution_closure_excludes_mutable_predecessor_runner(self) -> None:
        closure = self.module.execution_closure()
        self.assertIn(self.module.ADAPTER_REL, closure["files"])
        self.assertIn(self.module.INCIDENT_REPORT_REL, closure["files"])
        self.assertIn(self.module.TARGET_CONTRACT_REL, closure["files"])
        self.assertNotIn(self.module.PREDECESSOR_D1_REL, closure["files"])
        self.assertRegex(closure["sha256"], r"^[0-9a-f]{64}$")

    def test_approval_binding_is_read_only_and_no_replay(self) -> None:
        value = self.module._approval_binding(
            {"sha256": "a" * 64},
            created_utc="2026-08-10T00:00:00Z",
            expires_utc="2026-08-10T00:30:00Z",
        )
        self.assertEqual(value["device_contact"], "bounded-read-only")
        self.assertFalse(value["device_effect"])
        self.assertFalse(value["candidate_replay"])
        for key in (
            "arm_count",
            "reboot_count",
            "handoff_count",
            "mount_count",
            "service_control_count",
            "payload_transfer_count",
            "partition_write_count",
            "userdata_write_count",
        ):
            self.assertEqual(value[key], 0)

    def test_unmounted_probe_is_read_only_and_alias_complete(self) -> None:
        script = self.module._unmounted_script()
        self.assertIn("/sys/class/block/*/uevent", script)
        self.assertIn("^PARTNAME=userdata$", script)
        self.assertIn("/proc/self/mountinfo", script)
        self.assertIn("'$3 == d", script)
        self.assertIn("userdata_write=0", script)
        for forbidden in (" rm ", "reboot", "switch_root", " dd ", "mkfs", "mount -"):
            self.assertNotIn(forbidden, script)

    def test_unmounted_probe_accepts_runtime_resolved_devt(self) -> None:
        record = {
            "command": ["run", "/bin/busybox", "sh", "-c", "fixture"],
            "text": (
                "A90H17_NATIVE_FALLBACK devt=259:42 "
                "ufs_mount_count=0 userdata_write=0\n"
            ),
        }
        with mock.patch.object(
            self.module,
            "_unmounted_script",
            return_value="fixture",
        ), mock.patch.object(
            self.module.base,
            "run_f1_cmd",
            return_value=record,
        ), mock.patch.object(
            self.module.base,
            "require_exact_f1_command_receipt",
            return_value=record,
        ):
            value = self.module._prove_userdata_unmounted(argparse.Namespace())
        self.assertEqual(value["device"], "259:42")
        self.assertEqual(
            value["identity"],
            "sole-PARTNAME-userdata-DEVNAME-sda33-runtime-devt",
        )
        self.assertEqual(value["mount_count"], 0)
        self.assertEqual(value["userdata_write_count"], 0)

    def test_state_parser_requires_exact_h17_one_one(self) -> None:
        record = {
            "command": ["auto-handoff-status"],
            "text": "A90AUTO_STATUS binding=1 enable=1 latch=1 "
            "build=phase3-minimal-h17-ufs-ro-observer-auth-persistent-hud\n",
        }
        with mock.patch.object(
            self.module.base,
            "require_exact_f1_command_receipt",
            return_value=record,
        ):
            value = self.module._parse_status(record)
        self.assertEqual((value["enable"], value["latch"]), (1, 1))

    def test_fallback_proof_uses_latest_exact_failed_h17_segment(self) -> None:
        intent = self.module.INTENT_SHA256
        markers = "\n".join(
            (
                f"auto-handoff: armed after native health intent_sha256={intent}",
                f"auto-handoff: armed reboot dispatch intent_sha256={intent}",
                f"detail={self.module.H17_BOOT_DETAIL}",
                f"ondev-evidence: run published intent_sha256={intent}",
                "server-distro: D4 handoff failure cleanup_clean=1 "
                "root_mounted=0 recovery_required=0 userdata_unchanged=1 "
                "userdata_write=0",
                "auto-handoff: handoff returned no replay rc=-1",
            )
        )
        records = [
            {"stage": stage, "boottime_ms": index * 1000}
            for index, stage in enumerate(self.module.FAILED_HANDOFF_STAGES)
        ]
        with mock.patch.object(
            self.module.base,
            "require_exact_f1_command_receipt",
            return_value={"text": markers},
        ), mock.patch.object(
            self.module.benchmark,
            "parse_runs",
            return_value=[{"records": records}],
        ):
            value = self.module._fallback_proof({"record": True})
        self.assertTrue(value["proof"])
        self.assertTrue(value["root_mounted"])
        self.assertFalse(value["writable_set_ready"])
        self.assertFalse(value["switch_root_exec"])
        self.assertEqual(value["root_mounted_to_failure_ms"], 1000)

    def test_fallback_proof_rejects_switch_root_contradiction(self) -> None:
        intent = self.module.INTENT_SHA256
        text = "\n".join(
            (
                f"auto-handoff: armed after native health intent_sha256={intent}",
                f"auto-handoff: armed reboot dispatch intent_sha256={intent}",
                f"detail={self.module.H17_BOOT_DETAIL}",
                f"ondev-evidence: run published intent_sha256={intent}",
                "server-distro: D4 handoff failure cleanup_clean=1 "
                "root_mounted=0 recovery_required=0 userdata_unchanged=1 "
                "userdata_write=0",
                "auto-handoff: handoff returned no replay rc=-1",
                "stage=switch_root_exec ",
            )
        )
        records = [
            {"stage": stage, "boottime_ms": index}
            for index, stage in enumerate(self.module.FAILED_HANDOFF_STAGES)
        ]
        with mock.patch.object(
            self.module.base,
            "require_exact_f1_command_receipt",
            return_value={"text": text},
        ), mock.patch.object(
            self.module.benchmark,
            "parse_runs",
            return_value=[{"records": records}],
        ), self.assertRaisesRegex(
            self.module.ContractError, "contradicts successful handoff"
        ):
            self.module._fallback_proof({"record": True})

    def test_fallback_proof_rejects_unaccounted_later_boot(self) -> None:
        intent = self.module.INTENT_SHA256
        text = "\n".join(
            (
                f"auto-handoff: armed after native health intent_sha256={intent}",
                f"auto-handoff: armed reboot dispatch intent_sha256={intent}",
                f"detail={self.module.H17_BOOT_DETAIL}",
                f"ondev-evidence: run published intent_sha256={intent}",
                "server-distro: D4 handoff failure cleanup_clean=1 "
                "root_mounted=0 recovery_required=0 userdata_unchanged=1 "
                "userdata_write=0",
                "auto-handoff: handoff returned no replay rc=-1",
                f"detail={self.module.H17_BOOT_DETAIL}",
            )
        )
        records = [
            {"stage": stage, "boottime_ms": index}
            for index, stage in enumerate(self.module.FAILED_HANDOFF_STAGES)
        ]
        with mock.patch.object(
            self.module.base,
            "require_exact_f1_command_receipt",
            return_value={"text": text},
        ), mock.patch.object(
            self.module.benchmark,
            "parse_runs",
            return_value=[{"records": records}],
        ), self.assertRaisesRegex(
            self.module.ContractError, "same-intent proof is not unique"
        ):
            self.module._fallback_proof({"record": True})

    def test_fallback_proof_rejects_additional_latest_segment_run(self) -> None:
        intent = self.module.INTENT_SHA256
        text = "\n".join(
            (
                f"auto-handoff: armed after native health intent_sha256={intent}",
                f"auto-handoff: armed reboot dispatch intent_sha256={intent}",
                f"detail={self.module.H17_BOOT_DETAIL}",
                f"ondev-evidence: run published intent_sha256={intent}",
                "server-distro: D4 handoff failure cleanup_clean=1 "
                "root_mounted=0 recovery_required=0 userdata_unchanged=1 "
                "userdata_write=0",
                "auto-handoff: handoff returned no replay rc=-1",
            )
        )
        exact_records = [
            {"stage": stage, "boottime_ms": index}
            for index, stage in enumerate(self.module.FAILED_HANDOFF_STAGES)
        ]
        with mock.patch.object(
            self.module.base,
            "require_exact_f1_command_receipt",
            return_value={"text": text},
        ), mock.patch.object(
            self.module.benchmark,
            "parse_runs",
            return_value=[
                {"records": exact_records},
                {"records": [{"stage": "handoff_begin", "boottime_ms": 1}]},
            ],
        ), self.assertRaisesRegex(
            self.module.ContractError, "same-intent proof is not unique"
        ):
            self.module._fallback_proof({"record": True})

    def test_terminal_restores_health_without_overclaim(self) -> None:
        result = self.module._validate_terminal(
            self._terminal(), {"sha256": "a" * 64}
        )
        self.assertTrue(result["resident_healthy"])
        self.assertEqual(result["experiment_proof"], "REFUTED")
        self.assertFalse(result["operator_physical_return"])
        self.assertFalse(result["automatic_native_return"])
        self.assertFalse(result["switch_root_exec_proven"])
        self.assertFalse(result["persistent_server_proven"])

    def test_terminal_rejects_new_pstore_entry(self) -> None:
        terminal = self._terminal()
        terminal["native_health"]["status"]["text"] = (
            "pstore=available entries=1\n"
        )
        with self.assertRaisesRegex(
            self.module.ContractError, "exact health receipts changed"
        ):
            self.module._validate_terminal(terminal, {"sha256": "a" * 64})

    def test_deep_terminal_rejects_synthetic_evidence(self) -> None:
        terminal = self._terminal()
        manifest = {"target": {"bridge_realpath": "/dev/ttyACM0"}}
        diagnosis = terminal["diagnosis_binding"]
        records = [
            {},
            {},
            {},
            {"observation": terminal["original_observation"]},
            {"result_sha256": terminal["prior_current_result_sha256"]},
        ]

        def validate(value: dict) -> dict:
            with mock.patch.object(
                self.module.base,
                "require_exact_f1_command_receipt",
                side_effect=lambda record, _command, _label: record,
            ), mock.patch.object(
                self.module,
                "_validate_native_status",
                return_value=value["native_status"],
            ), mock.patch.object(
                self.module,
                "_parse_status",
                return_value=value["auto_handoff_status"],
            ), mock.patch.object(
                self.module,
                "_parse_same_intent_record",
                return_value=value["same_intent_binding"],
            ), mock.patch.object(
                self.module,
                "_fallback_proof",
                return_value=value["native_fallback_proof"],
            ), mock.patch.object(
                self.module,
                "_parse_unmounted_record",
                return_value=value["post_fallback_userdata"],
            ):
                return self.module._deep_validate_terminal(
                    value,
                    {"sha256": "a" * 64},
                    manifest,
                    diagnosis,
                    records,
                )

        self.assertEqual(validate(terminal), terminal)

        missing_receipt = copy.deepcopy(terminal)
        missing_receipt.pop("durable_log_record")
        with self.assertRaisesRegex(self.module.ContractError, "evidence is absent"):
            validate(missing_receipt)

        changed_approval = copy.deepcopy(terminal)
        changed_approval["read_only_approval_binding"]["arm_count"] = 1
        with self.assertRaisesRegex(self.module.ContractError, "approval changed"):
            validate(changed_approval)

        changed_bridge = copy.deepcopy(terminal)
        changed_bridge["final_bridge"]["selected_realpath"] = "/dev/ttyACM9"
        with self.assertRaisesRegex(self.module.ContractError, "identity changed"):
            validate(changed_bridge)

    def test_six_record_resume_appends_closed_without_device_contact(self) -> None:
        closure = {"sha256": "a" * 64}
        result = self._terminal()
        result_sha = self.module.f1.json_sha256(result)
        records = [{}, {}, {}, {}, {}, {"result": result, "result_sha256": result_sha}]
        args = argparse.Namespace(operator_attended=True, approval=None)
        writes: list[tuple[int, str, dict]] = []
        with mock.patch.object(
            self.module,
            "_load_static_inputs",
            return_value=({}, {}, records, closure),
        ), mock.patch.object(
            self.module,
            "_deep_validate_terminal",
            return_value=result,
        ) as deep_validate, mock.patch.object(
            self.module,
            "_build_result",
            side_effect=AssertionError("must not contact device"),
        ), mock.patch.object(
            self.module,
            "_write_record",
            side_effect=lambda index, action, payload: writes.append(
                (index, action, payload)
            ),
        ):
            value = self.module.close(args)
        self.assertEqual(value, result)
        self.assertEqual([item[:2] for item in writes], [(6, "closed")])
        deep_validate.assert_called_once_with(result, closure, {}, {}, records)

    def test_five_record_close_rejects_static_drift_before_write(self) -> None:
        manifest = {"target": {"bridge_realpath": "/dev/ttyACM0"}}
        diagnosis = {"proof": True}
        records = [{"sequence": index} for index in range(5)]
        drifted = copy.deepcopy(records)
        drifted[3]["changed_during_reads"] = True
        closure = {"sha256": "a" * 64}
        result = self._terminal()
        approval = {
            "approval_binding": result["read_only_approval_binding"],
            "approval_binding_sha256": result[
                "read_only_approval_binding_sha256"
            ],
        }
        args = argparse.Namespace(operator_attended=True, approval="exact")
        with mock.patch.object(
            self.module,
            "_load_static_inputs",
            side_effect=(
                (manifest, diagnosis, records, closure),
                (manifest, diagnosis, drifted, closure),
            ),
        ), mock.patch.object(
            self.module,
            "_validate_approval",
            return_value=approval,
        ), mock.patch.object(
            self.module,
            "_build_result",
            return_value=result,
        ), mock.patch.object(
            self.module,
            "_deep_validate_terminal",
            return_value=result,
        ), mock.patch.object(
            self.module,
            "_write_record",
        ) as write_record, self.assertRaisesRegex(
            self.module.ContractError, "static inputs changed during reads"
        ):
            self.module.close(args)
        write_record.assert_not_called()

    def test_five_record_close_requires_attendance_and_fresh_approval(self) -> None:
        args = argparse.Namespace(operator_attended=False, approval=None)
        with self.assertRaisesRegex(self.module.ContractError, "attended-only"):
            self.module.close(args)

        args = argparse.Namespace(operator_attended=True, approval=None)
        with mock.patch.object(
            self.module,
            "_load_static_inputs",
            return_value=({}, {}, [{}, {}, {}, {}, {}], {"sha256": "a" * 64}),
        ), self.assertRaisesRegex(self.module.ContractError, "fresh exact approval"):
            self.module.close(args)

    def test_cli_has_no_effect_mode(self) -> None:
        options = self.module.parser()._option_string_actions
        for forbidden in (
            "--execute",
            "--reboot",
            "--arm",
            "--handoff",
            "--mount",
            "--flash",
        ):
            self.assertNotIn(forbidden, options)
        self.assertIn("--prepare-approval", options)
        self.assertIn("--close", options)


if __name__ == "__main__":
    unittest.main()
