from __future__ import annotations

import argparse
import unittest
from unittest import mock

from _loader import load_script


class A90H16PersistentPhysicalReturnV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_script(
            "workspace/public/src/scripts/server-distro/"
            "a90_h16_persistent_physical_return_v1.py"
        )

    def _terminal(self, closure_sha: str = "a" * 64) -> dict:
        return {
            "schema": self.module.d1.RESULT_SCHEMA,
            "terminal": "NO_PROOF_H16_PERSISTENT_DEBIAN_PHYSICAL_RETURN_HEALTHY",
            "incident": "PERSISTENT_DEBIAN_RETURN_AND_OBSERVER_BINDING_MISMATCH",
            "intent_sha256": self.module.INTENT_SHA256,
            "physical_return_execution_closure_sha256": closure_sha,
            "resident_healthy": True,
            "operator_physical_return": True,
            "automatic_native_return": False,
            "switch_root_exec_proven": True,
            "persistent_server_proven": False,
            "authenticated_ssh_proven": False,
            "debian_pid1_proven": False,
            "drm_master_proven": False,
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
            "auto_handoff_status": {"binding": 1, "enable": 1, "latch": 1},
            "handoff_benchmark": {"proof": True, "switch_root_exec": True},
            "post_physical_return_userdata": {
                "proof": True,
                "device": "259:17",
                "mount_count": 0,
                "userdata_write_count": 0,
            },
            "original_observation": {
                "proof": False,
                "guard_release": {"released": True},
            },
        }

    def test_execution_closure_binds_incident_contract_and_predecessor_sources(self) -> None:
        closure = self.module.execution_closure()
        self.assertEqual(len(closure["files"]), len(self.module.EXECUTION_RELS))
        self.assertIn(self.module.TARGET_CONTRACT_REL, closure["files"])
        self.assertIn(self.module.INCIDENT_REPORT_REL, closure["files"])
        self.assertIn(self.module.ADAPTER_REL, closure["files"])
        self.assertTrue(
            set(self.module.f1.EXECUTION_SOURCE_RELS).issubset(closure["files"])
        )
        self.assertRegex(closure["sha256"], r"^[0-9a-f]{64}$")

    def test_unmounted_probe_is_read_only_and_exactly_bounded(self) -> None:
        script = self.module._unmounted_script()
        self.assertIn("/sys/class/block/*/uevent", script)
        self.assertIn("^PARTNAME=userdata$", script)
        self.assertIn('[ "$DEVNAME" = sda33 ]', script)
        self.assertIn("/proc/self/mountinfo", script)
        self.assertIn("'$3 == d", script)
        self.assertIn("userdata_write=0", script)
        for forbidden in (" rm ", "reboot", "switch_root", " dd ", "mkfs", "mount -"):
            self.assertNotIn(forbidden, script)

    def test_unmounted_probe_requires_exact_device_and_zero_mounts(self) -> None:
        record = {
            "command": ["placeholder"],
            "text": "A90H16_POST_PHYSICAL_RETURN devt=259:17 "
            "ufs_mount_count=0 userdata_write=0\n",
        }
        with mock.patch.object(
            self.module.base,
            "run_f1_cmd",
            return_value=record,
        ), mock.patch.object(
            self.module.base,
            "require_exact_f1_command_receipt",
            return_value=record,
        ):
            value = self.module._prove_userdata_unmounted(argparse.Namespace())
        self.assertTrue(value["proof"])
        self.assertEqual(value["device"], "259:17")
        self.assertEqual(value["mount_count"], 0)
        self.assertEqual(value["userdata_write_count"], 0)

    def test_benchmark_proof_requires_unique_h16_handoff_and_return(self) -> None:
        intent = self.module.INTENT_SHA256
        text = "\n".join(
            (
                f"auto-handoff: armed after native health intent_sha256={intent}",
                f"auto-handoff: armed reboot dispatch intent_sha256={intent}",
                f"ondev-evidence: run published intent_sha256={intent}",
                "server-distro: D4 read-only switch_root exec "
                "source=/dev/block/a90-userdata "
                "root=/mnt/sdext/a90/runtime/distro-root writable_set=4 "
                "evidence_bound=1 wifi_handoff_bound=1",
            )
        )
        handoff_records = [
            {"stage": stage, "boottime_ms": index * 10}
            for index, stage in enumerate(self.module.H16_UFS_STAGES)
        ]
        return_records = [
            {"stage": stage, "boottime_ms": index * 10}
            for index, stage in enumerate(self.module.RETURN_STAGES)
        ]
        with mock.patch.object(
            self.module.base,
            "require_exact_f1_command_receipt",
            return_value={"text": text},
        ), mock.patch.object(
            self.module.benchmark,
            "parse_runs",
            return_value=[
                {"records": handoff_records},
                {"records": return_records},
            ],
        ):
            value = self.module._benchmark_proof({"record": True}, intent)
        self.assertTrue(value["switch_root_exec"])
        self.assertEqual(value["boot_to_switch_root_ms"], 170)
        self.assertEqual(value["handoff_begin_to_switch_root_ms"], 90)

    def test_result_refuses_to_promote_missing_server_evidence(self) -> None:
        closure = {"sha256": "b" * 64}
        records = [{}, {}, {}, {"observation": {"proof": False}}]
        with mock.patch.object(
            self.module.base.staging,
            "require_exact_bridge",
        ), mock.patch.object(
            self.module.d1,
            "require_status",
            return_value=({"status": True}, {"binding": 1, "enable": 1, "latch": 1}),
        ), mock.patch.object(
            self.module.base,
            "verify_candidate_health",
            return_value={"resident_healthy": True},
        ), mock.patch.object(
            self.module.base,
            "run_f1_cmd",
            return_value={"log": True},
        ), mock.patch.object(
            self.module,
            "_benchmark_proof",
            return_value={"proof": True, "switch_root_exec": True},
        ), mock.patch.object(
            self.module,
            "_prove_userdata_unmounted",
            return_value={"proof": True, "mount_count": 0},
        ):
            result = self.module._build_result(
                mock.Mock(stage=object()), records, closure
            )
        self.assertTrue(result["resident_healthy"])
        self.assertTrue(result["switch_root_exec_proven"])
        self.assertFalse(result["automatic_native_return"])
        self.assertFalse(result["persistent_server_proven"])
        self.assertFalse(result["authenticated_ssh_proven"])
        self.assertFalse(result["debian_pid1_proven"])
        self.assertFalse(result["drm_master_proven"])
        self.assertFalse(result["display_visible_proven"])
        self.assertFalse(result["final_wifi_proven"])

    def test_five_record_crash_resume_only_appends_closed_record(self) -> None:
        closure = {"sha256": "a" * 64}
        result = self._terminal()
        result_sha = self.module.f1.json_sha256(result)
        records = [{}, {}, {}, {}, {"result": result, "result_sha256": result_sha}]
        args = argparse.Namespace(
            operator_attended=True,
            physical_return_confirmed=True,
        )
        written: list[tuple[int, str, dict]] = []
        with mock.patch.object(
            self.module,
            "_load_inputs",
            return_value=({}, object(), records, closure),
        ), mock.patch.object(
            self.module,
            "_build_result",
            side_effect=AssertionError("must not contact the device again"),
        ), mock.patch.object(
            self.module.d1,
            "_write_record",
            side_effect=lambda _directory, index, action, payload: written.append(
                (index, action, payload)
            ),
        ):
            value = self.module.close(args)
        self.assertEqual(value, result)
        self.assertEqual([item[:2] for item in written], [(5, "closed")])

    def test_exact_writer_temp_hardlink_is_retired_for_crash_resume(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            final = directory / "0004-final-health.json"
            final.write_text("{}", encoding="utf-8")
            final.chmod(0o600)
            alias = directory / f".{final.name}.tmp-123-456"
            alias.hardlink_to(final)
            info = self.module._canonicalize_exact_writer_temp(final, final.lstat())
            self.assertEqual(info.st_nlink, 1)
            self.assertFalse(alias.exists())

    def test_attendance_and_physical_return_confirmation_are_both_required(self) -> None:
        for attended, confirmed in ((False, False), (True, False), (False, True)):
            args = argparse.Namespace(
                operator_attended=attended,
                physical_return_confirmed=confirmed,
            )
            with self.assertRaisesRegex(
                self.module.ContractError,
                "requires attended confirmation",
            ):
                self.module.close(args)

    def test_cli_has_no_approval_or_effect_mode(self) -> None:
        options = self.module.parser()._option_string_actions
        self.assertNotIn("--approval", options)
        self.assertNotIn("--execute", options)
        self.assertNotIn("--reboot", options)
        self.assertNotIn("--arm", options)
        self.assertEqual(options["--close"].const, True)


if __name__ == "__main__":
    unittest.main()
