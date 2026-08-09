"""Static and pure tests for the A90 H4 automatic benchmark runner."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "workspace/public/src/scripts/server-distro"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a90_auto_handoff_benchmark_runner_v1 as runner  # noqa: E402


class A90AutoHandoffBenchmarkRunnerV1Tests(unittest.TestCase):
    def test_current_runner_is_exact_h13_wifi_identity(self) -> None:
        self.assertEqual(runner.EXPECTED_VERSION, "0.11.181")
        self.assertEqual(
            runner.EXPECTED_BUILD,
            "phase3-minimal-h13-direct-min-network-wifi-auto-benchmark",
        )
        self.assertEqual(
            runner.EXPECTED_ROOTFS_SHA256,
            "8a87cd547cfd7cfee7ec4af7ee266fd4da0b91e508099950df50a272ab19952e",
        )
        self.assertEqual(
            runner.SOURCE_RECEIPT_PATH,
            "/cache/a90-source-receipt-phase3-minimal-h13",
        )

    @staticmethod
    def _benchmark_marker(stage: str, boottime_ms: int) -> str:
        values = {
            "schema": runner.benchmark.SCHEMA,
            "stage": stage,
            "boottime_ms": str(boottime_ms),
            "clock_ok": "1",
            "telemetry_sampled": "1",
            "sample_duration_ms": "5",
            "prior_emit_duration_ms": "5",
            "cpu_temp_c": "41.2C",
            "gpu_temp_c": "39.0C",
            "battery_temp_c": "31.5C",
            "cpu_usage_pct": "12%",
            "gpu_usage_pct": "0%",
            "memory_mb": "512/6144MB",
            "load1": "0.25",
            "cpu0_khz": "1000000",
            "cpu4_khz": "1800000",
            "cpu7_khz": "2400000",
            "gpu_hz": "257000000",
            "battery_current_ua": "-450000",
            "battery_voltage_uv": "4000000",
            "power_now_raw": "na",
            "power_avg_raw": "na",
            "calculated_power_uw": "-1800000",
            "mmc_read_sectors": "100",
            "mmc_write_sectors": "200",
        }
        return runner.benchmark.MARKER + " ".join(
            f"{key}={values[key]}" for key in runner.benchmark.FIELDS
        )

    @classmethod
    def _complete_benchmark_segment(cls, start_ms: int) -> str:
        return "\n".join(
            cls._benchmark_marker(stage, start_ms + index * 10)
            for index, stage in enumerate(runner.benchmark.COMPLETE_STAGES)
        )

    @staticmethod
    def _with_direct_stage(stages: tuple[str, ...]) -> tuple[str, ...]:
        values = list(stages)
        values.insert(
            values.index("native_runtime_ready") + 1,
            runner.DIRECT_HANDOFF_STAGE,
        )
        return tuple(values)

    @staticmethod
    def _with_h12_direct_stages(
        stages: tuple[str, ...],
        *,
        autoconnect: str = "native_wifi_autoconnect_dispatched",
    ) -> tuple[str, ...]:
        values = list(stages)
        index = values.index("native_runtime_ready") + 1
        values[index:index] = [
            runner.H12_WIFI_COMPANION_STAGE,
            autoconnect,
            runner.H12_NCM_HANDOFF_STAGE,
            runner.DIRECT_HANDOFF_STAGE,
        ]
        return tuple(values)

    @classmethod
    def _direct_complete_benchmark_segment(cls, start_ms: int) -> str:
        return "\n".join(
            cls._benchmark_marker(stage, start_ms + index * 10)
            for index, stage in enumerate(
                cls._with_direct_stage(runner.benchmark.COMPLETE_STAGES)
            )
        )

    @classmethod
    def _failed_benchmark_segment(cls, start_ms: int) -> str:
        stages = runner.benchmark.COMPLETE_STAGES[:-2] + (
            "handoff_failed_native",
            "auto_handoff_returned_native",
            "native_fallback_ready",
        )
        return "\n".join(
            cls._benchmark_marker(stage, start_ms + index * 10)
            for index, stage in enumerate(stages)
        )

    @staticmethod
    def _ondevice_record(phase: str, uptime_ms: int, run: str) -> str:
        return (
            f"{runner.ondevice_evidence.MARKER}"
            f"schema={runner.ondevice_evidence.SCHEMA} "
            f"phase={phase} uptime_ms={uptime_ms} run={run} "
            "pid1_comm=init proc1_exe=/usr/sbin/init drm_card0=char "
            "drm_master=1 dropbear=1 display_ready=1 display_failure=0 "
            "wifi_ready=1 wifi_failure=0 wifi_companion=1"
        )

    @staticmethod
    def _status(enable: int, latch: int) -> dict:
        command = ["auto-handoff-status"]
        return {
            "command": command,
            "rc": 0,
            "status": "ok",
            "trust": "A90P1_V1_STRUCTURAL_ONLY",
            "begin": {"argc": "1", "cmd": command[0], "flags": "0x0", "seq": "35"},
            "end": {
                "cmd": command[0],
                "duration_ms": "1",
                "errno": "0",
                "flags": "0x0",
                "rc": "0",
                "seq": "35",
                "status": "ok",
            },
            "text": (
                f"A90AUTO_STATUS binding=1 enable={enable} latch={latch} "
                f"build={runner.EXPECTED_BUILD}\n"
            )
        }

    @staticmethod
    def _arm_receipt(intent_sha256: str, rc: int) -> dict:
        command = ["auto-handoff-arm", runner.ARM_TOKEN, intent_sha256]
        status = "ok" if rc == 0 else "error"
        marker = (
            "\n".join(
                (
                    "A90D3H0 source_receipt=qualifying "
                    f"path={runner.SOURCE_RECEIPT_PATH} prior_rc=-2 "
                    "full_sha=required",
                    "A90D3H0 source_sha phase=receipt-qualification "
                    f"sha={runner.EXPECTED_ROOTFS_SHA256} "
                    "expected_sha_match=1",
                    "A90D3H0 source_receipt=qualified "
                    f"path={runner.SOURCE_RECEIPT_PATH} metadata=exact "
                    "full_sha=verified",
                    "A90AUTO_ARM armed=1 "
                    f"intent_sha256={intent_sha256} build={runner.EXPECTED_BUILD}",
                )
            )
            if rc == 0
            else f"A90AUTO_ARM armed=0 rc={rc}"
        )
        return {
            "command": command,
            "rc": rc,
            "status": status,
            "trust": "A90P1_V1_STRUCTURAL_ONLY",
            "begin": {"argc": "3", "cmd": command[0], "flags": "0x4", "seq": "34"},
            "end": {
                "cmd": command[0],
                "duration_ms": "6",
                "errno": str(-rc if rc < 0 else 0),
                "flags": "0x4",
                "rc": str(rc),
                "seq": "34",
                "status": status,
            },
            "text": marker + "\n",
        }

    @staticmethod
    def _shell_receipt(script: str, text: str) -> dict:
        command = ["run", "/bin/busybox", "sh", "-c", script]
        return {
            "command": command,
            "rc": 0,
            "status": "ok",
            "trust": "A90P1_V1_STRUCTURAL_ONLY",
            "begin": {"argc": "5", "cmd": "run", "flags": "0x4", "seq": "41"},
            "end": {
                "cmd": "run",
                "duration_ms": "5",
                "errno": "0",
                "flags": "0x4",
                "rc": "0",
                "seq": "41",
                "status": "ok",
            },
            "text": text,
        }

    @staticmethod
    def _spec() -> SimpleNamespace:
        return SimpleNamespace(
            manifest_sha256="1" * 64,
            candidate=SimpleNamespace(sha256="2" * 64),
            rollback=SimpleNamespace(sha256="3" * 64),
            rootfs=SimpleNamespace(
                sha256=runner.EXPECTED_ROOTFS_SHA256,
                size=2 * 1024 * 1024 * 1024,
            ),
            remote_final=(
                "/mnt/sdext/a90/runtime/"
                "debian-bookworm-arm64-phase2-display-v3406-keyed-20260810-08.img"
            ),
            remote_work="/mnt/sdext/a90/runtime/d3-handoff-work.img",
            recovery_profile="A90_ATTENDED_PHYSICAL_RECOVERY_V1",
            bridge_device="/dev/a90-test",
            bridge_realpath="/dev/ttyACM0",
            observer_host_ncm_profile="a90-test-ncm",
            candidate_version=runner.EXPECTED_VERSION,
            candidate_build=runner.EXPECTED_BUILD,
        )

    @classmethod
    def _host_link(cls) -> dict:
        spec = cls._spec()
        return {
            "proof": True,
            "pre_reboot_binding": cls._pre_reboot_binding(),
            "debian_ncm_identity": {
                "schema": runner.POST_REBOOT_NCM_IDENTITY_SCHEMA,
                "interface": "enx001122334455",
                "usb_topology": "2-2",
                "usb_serial_sha256": "9" * 64,
                "usb_vendor": runner.base.staging.HOST_NCM_VENDOR_ID,
                "usb_product": runner.base.staging.HOST_NCM_PRODUCT_ID,
                "usb_busnum": 2,
                "usb_devnum": 9,
                "same_usb_topology": True,
                "same_usb_serial_sha256": True,
                "new_usb_epoch": True,
            },
            "host_ncm_rebind": {
                "same_bound_usb_identity": True,
                "acm_required": False,
                "exact_interface_count": 1,
                "profile_bound": True,
                "mutated": False,
                "profile_check": {
                    "command": [
                        "nmcli", "-g", "connection.type", "connection",
                        "show", spec.observer_host_ncm_profile,
                    ],
                    "returncode": 0,
                    "stdout": runner.base.HOST_NCM_CONNECTION_TYPE + "\n",
                },
                "ready": {
                    "verified_a90_ncm": True,
                    "direct_route": True,
                    "host_cidr_present": True,
                    "device_ping": True,
                },
            },
            "debian_ncm_continuity": {
                "before_ssh": True,
                "after_ssh": True,
                "after_service": True,
            },
            "ssh": {"proof": True},
            "phase3_service": {"proof": True},
            "candidate_return": {
                "exact_bridge": True,
                "native_epoch_version_proven": True,
                "device_command_sequences": 1,
                "return_epoch": {
                    "before_ncm": {"usb_busnum": 2, "usb_devnum": 9},
                    "returned": {
                        "schema": runner.base.RETURN_EPOCH_SCHEMA,
                        "selected_realpath": spec.bridge_realpath,
                        "tty_st_dev": 7,
                        "tty_st_ino": 101,
                        "tty_st_rdev": 42496,
                        "usb_busnum": 2,
                        "usb_devnum": 10,
                    },
                    "returned_usb_identity": {
                        "usb_topology": "2-2",
                        "usb_serial_sha256": "9" * 64,
                        "usb_vendor": runner.base.staging.HOST_NCM_VENDOR_ID,
                        "usb_product": runner.base.staging.HOST_NCM_PRODUCT_ID,
                        "usb_busnum": 2,
                        "usb_devnum": 10,
                    },
                    "changed": True,
                },
            },
        }

    @staticmethod
    def _pre_reboot_binding() -> dict:
        return {
            "schema": runner.PRE_REBOOT_OBSERVER_BINDING_SCHEMA,
            "serial_epoch": {
                "schema": runner.base.RETURN_EPOCH_SCHEMA,
                "selected_realpath": "/dev/ttyACM0",
                "tty_st_dev": 7,
                "tty_st_ino": 100,
                "tty_st_rdev": 42496,
                "usb_busnum": 2,
                "usb_devnum": 8,
            },
            "usb_identity": {
                "usb_topology": "2-2",
                "usb_serial_sha256": "9" * 64,
                "usb_vendor": runner.base.staging.HOST_NCM_VENDOR_ID,
                "usb_product": runner.base.staging.HOST_NCM_PRODUCT_ID,
                "usb_busnum": 2,
                "usb_devnum": 8,
            },
            "pre_reboot_interface": "enx001122334455",
        }

    @classmethod
    def _post_reboot_ncm(cls, *, devnum: int = 9) -> dict:
        value = dict(cls._host_link()["debian_ncm_identity"])
        value["usb_devnum"] = devnum
        return value

    def _write_semantic_prefix(
        self,
        path: Path,
        count: int,
        closure: dict,
        intent_closure_sha256: str = "0" * 64,
        reboot_closure_sha256: str = "0" * 64,
    ) -> None:
        spec = self._spec()
        opened = {
            "manifest_sha256": spec.manifest_sha256,
            "execution_closure": closure,
            "candidate_sha256": spec.candidate.sha256,
            "rollback_sha256": spec.rollback.sha256,
            "rootfs_sha256": spec.rootfs.sha256,
            "opening_preflight": {},
            "auto_status": runner.parse_auto_status(self._status(0, 0)),
            "auto_status_record": self._status(0, 0),
            "first_boot_log": {"text": "A90AUTO state=unarmed-stay-native\n"},
            "first_boot_log_sha256": runner.hashlib.sha256(
                b"A90AUTO state=unarmed-stay-native\n"
            ).hexdigest(),
            "first_boot_unarmed": True,
        }
        payloads = [opened]
        if count >= 2:
            payloads.append(
                {
                    "manifest_sha256": spec.manifest_sha256,
                    "execution_closure_sha256": intent_closure_sha256,
                    "arm_dispatch_count_max": 1,
                    "reboot_dispatch_count": 0,
                    "candidate_replay": False,
                }
            )
        if count >= 2:
            runner.write_record(path / runner.JOURNAL_NAMES[0], runner.JOURNAL_ACTIONS[0], payloads[0])
            runner.write_record(path / runner.JOURNAL_NAMES[1], runner.JOURNAL_ACTIONS[1], payloads[1])
        elif count == 1:
            runner.write_record(path / runner.JOURNAL_NAMES[0], runner.JOURNAL_ACTIONS[0], payloads[0])
        if count < 3:
            return
        intent_sha256 = runner.sha256_file(path / runner.JOURNAL_NAMES[1])
        remaining = (
            {
                "intent_sha256": intent_sha256,
                "arm_dispatch_count": 1,
                "arm_record": self._arm_receipt(intent_sha256, 0),
                "post_arm_status_record": self._status(1, 0),
                "post_arm_status": runner.parse_auto_status(self._status(1, 0)),
            },
            {
                "intent_sha256": intent_sha256,
                "execution_closure_sha256": reboot_closure_sha256,
                "armed_preflight": {},
                "pre_reboot_epoch": self._pre_reboot_binding(),
                "reboot_dispatch_count_max": 1,
                "candidate_replay": False,
            },
            {
                "intent_sha256": intent_sha256,
                "arm_dispatch_count": 1,
                "reboot_dispatch_count": 1,
                "candidate_replay": False,
                "observation": {
                    "reboot_record": {"command": ["reboot"], "dispatch_count": 1}
                },
            },
            {
                "intent_sha256": intent_sha256,
                "manifest_sha256": spec.manifest_sha256,
                "cleanup_dispatch_count_max": 0,
                "arm_dispatch_count": 1,
                "reboot_dispatch_count": 1,
                "candidate_replay": False,
                "returned_status": runner.parse_auto_status(self._status(1, 1)),
                "returned_status_record": self._status(1, 1),
            },
            {
                "intent_sha256": intent_sha256,
                "cleanup_dispatch_count": 0,
                "cleanup_record": None,
                "absence_preflight": {},
                "inferred_from_absence": True,
                "candidate_replay": False,
            },
            {"intent_sha256": intent_sha256, "result_sha256": "5" * 64, "result": {}},
            {"result_sha256": "5" * 64, "result": {}},
        )
        for index, payload in enumerate(remaining, start=2):
            if index >= count:
                break
            runner.write_record(
                path / runner.JOURNAL_NAMES[index],
                runner.JOURNAL_ACTIONS[index],
                payload,
            )

    def test_status_parser_requires_one_exact_h3_line(self) -> None:
        record = {
            "text": (
                "A90AUTO_STATUS binding=1 enable=0 latch=0 "
                f"build={runner.EXPECTED_BUILD}\r\n"
            )
        }
        self.assertEqual(
            runner.parse_auto_status(record),
            {
                "binding": 1,
                "enable": 0,
                "latch": 0,
                "build": runner.EXPECTED_BUILD,
            },
        )
        with self.assertRaises(runner.ContractError):
            runner.parse_auto_status({"text": record["text"] * 2})
        framed = {
            "text": (
                "cmdv1 auto-handoff-status\nA90P1 BEGIN\n"
                + record["text"]
                + "[done]\nA90P1 END\na90:/#\n"
            )
        }
        self.assertEqual(
            runner.parse_auto_status(framed),
            runner.parse_auto_status(record),
        )
        for malformed in (
            "A90AUTO_STATUS\n",
            "A90AUTO_STATUS\tmalformed=1\n",
            "A90AUTO_STATUS binding=1 enable=1 latch=1 "
            f"build={runner.EXPECTED_BUILD} extra=1\n",
            "A90AUTO_STATUS_UNRECOGNIZED=1\n",
        ):
            with self.subTest(malformed=malformed), self.assertRaises(
                runner.ContractError
            ):
                runner.parse_auto_status({"text": record["text"] + malformed})

    def test_fast_source_preflights_never_hash_or_remove_work(self) -> None:
        spec = self._spec()
        identity = {
            "dev": 2049,
            "ino": 77,
            "size": spec.rootfs.size,
            "mode": 33188,
            "uid": 0,
            "gid": 0,
            "nlink": 1,
            "mtime_sec": 1_700_000_000,
            "mtime_nsec": 1_104_086,
            "ctime_sec": 1_700_000_001,
            "ctime_nsec": 456,
        }
        absent = runner.fast_source_preflight_script(
            spec,
            expected_state="receipt-absent",
        )
        verified = runner.fast_source_preflight_script(
            spec,
            expected_state="receipt-verified",
        )
        receipt = runner.fast_receipt_content_script(spec, identity)
        for script in (absent, verified, receipt):
            self.assertNotIn("sha256sum", script)
            self.assertNotIn("/bin/busybox rm", script)
            wire = runner.base.a90ctl.encode_cmdv1_line(
                ["run", "/bin/busybox", "sh", "-c", script]
            )
            self.assertLess(len(wire.encode("utf-8")), runner.CMDV1X_BUFFER_BYTES)
        for script in (absent, verified):
            self.assertIn('[ ! -e "$WORK" ]', script)
            self.assertIn('[ ! -e "$RECEIPT_TMP" ]', script)
        self.assertIn('[ ! -e "$RECEIPT" ]', absent)
        self.assertNotIn("ACTUAL_RECEIPT=", absent)
        self.assertIn('[ -f "$RECEIPT" ]', verified)
        self.assertNotIn("/bin/busybox cat", verified)
        self.assertIn('A="$(/bin/busybox cat "$R")"', receipt)
        self.assertIn(f"ctime_nsec={identity['ctime_nsec']}", receipt)
        self.assertIn('SOURCE_MTIME_NSEC=$((10#$SOURCE_MTIME_NSEC))', verified)
        self.assertIn('SOURCE_CTIME_NSEC=$((10#$SOURCE_CTIME_NSEC))', verified)

    def test_busybox_nsec_normalization_matches_native_decimal_receipt(self) -> None:
        busybox = shutil.which("busybox")
        if busybox is None:
            self.skipTest("BusyBox shell is unavailable")
        command = (
            "for x in 001104086 000000000 123456789; do "
            "printf '%s\\n' $((10#$x)); done"
        )
        completed = subprocess.run(
            [busybox, "sh", "-c", command],
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.stdout.splitlines(), ["1104086", "0", "123456789"])

    def test_fast_source_receipt_binds_exact_identity_across_phases(self) -> None:
        spec = self._spec()
        identity = {
            "dev": 2049,
            "ino": 77,
            "size": spec.rootfs.size,
            "mode": 33188,
            "uid": 0,
            "gid": 0,
            "nlink": 1,
            "mtime_sec": 1_700_000_000,
            "mtime_nsec": 123,
            "ctime_sec": 1_700_000_001,
            "ctime_nsec": 456,
        }
        marker = (
            "A90D1_FAST_SOURCE state=receipt-verified "
            "work_absent=1 temp_absent=1 "
            + " ".join(f"{key}={identity[key]}" for key in runner.FAST_SOURCE_IDENTITY_KEYS)
            + "\n"
        )
        script = runner.fast_source_preflight_script(
            spec,
            expected_state="receipt-verified",
        )
        record = self._shell_receipt(script, marker)
        self.assertEqual(
            runner.require_fast_source_preflight_receipt(
                spec,
                record,
                expected_state="receipt-verified",
                expected_identity=identity,
            ),
            identity,
        )
        framed = self._shell_receipt(
            script,
            "cmdv1x accepted\nA90P1 BEGIN\nrun: started\n"
            + marker
            + "[exit 0]\n[done]\nA90P1 END\na90:/#\n",
        )
        self.assertEqual(
            runner.require_fast_source_preflight_receipt(
                spec,
                framed,
                expected_state="receipt-verified",
                expected_identity=identity,
            ),
            identity,
        )
        for malformed in (
            "A90D1_FAST_SOURCE malformed=1\n",
            "A90D1_FAST_SOURCE\n",
            "A90D1_FAST_SOURCE\tmalformed=1\n",
            "A90D1_FAST_SOURCE_UNRECOGNIZED=1\n",
        ):
            with self.subTest(malformed=malformed):
                foreign_marker = self._shell_receipt(script, marker + malformed)
                with self.assertRaisesRegex(runner.ContractError, "not exact"):
                    runner.require_fast_source_preflight_receipt(
                        spec,
                        foreign_marker,
                        expected_state="receipt-verified",
                    )
        changed = dict(identity)
        changed["ctime_nsec"] += 1
        with self.assertRaisesRegex(runner.ContractError, "identity changed"):
            runner.require_fast_source_preflight_receipt(
                spec,
                record,
                expected_state="receipt-verified",
                expected_identity=changed,
            )
        duplicated = self._shell_receipt(script, marker + marker)
        with self.assertRaisesRegex(runner.ContractError, "not exact"):
            runner.require_fast_source_preflight_receipt(
                spec,
                duplicated,
                expected_state="receipt-verified",
            )
        receipt_script = runner.fast_receipt_content_script(spec, identity)
        receipt_record = self._shell_receipt(
            receipt_script,
            "A90D1_FAST_RECEIPT exact=1\n",
        )
        self.assertEqual(
            runner.require_fast_receipt_content_receipt(
                spec,
                identity,
                receipt_record,
            ),
            receipt_record,
        )
        framed_receipt = self._shell_receipt(
            receipt_script,
            "cmdv1x accepted\nA90P1 BEGIN\nrun: started\n"
            "A90D1_FAST_RECEIPT exact=1\n"
            "[exit 0]\n[done]\nA90P1 END\na90:/#\n",
        )
        self.assertEqual(
            runner.require_fast_receipt_content_receipt(
                spec,
                identity,
                framed_receipt,
            ),
            framed_receipt,
        )
        for malformed in (
            "A90D1_FAST_RECEIPT malformed=1\n",
            "A90D1_FAST_RECEIPT\n",
            "A90D1_FAST_RECEIPT\tmalformed=1\n",
            "A90D1_FAST_RECEIPT_UNRECOGNIZED=1\n",
        ):
            with self.subTest(malformed=malformed):
                malformed_receipt = self._shell_receipt(
                    receipt_script,
                    "A90D1_FAST_RECEIPT exact=1\n" + malformed,
                )
                with self.assertRaisesRegex(runner.ContractError, "not exact"):
                    runner.require_fast_receipt_content_receipt(
                        spec,
                        identity,
                        malformed_receipt,
                    )

    def test_arm_success_requires_fresh_single_full_sha_qualification(self) -> None:
        intent_sha256 = "a" * 64
        record = self._arm_receipt(intent_sha256, 0)
        self.assertEqual(
            runner.require_exact_arm_dispatch_receipt(record, intent_sha256)[1],
            "armed",
        )
        framed = json.loads(json.dumps(record))
        framed["text"] = (
            "cmdv1x accepted\nA90P1 BEGIN\nrun: started\n"
            + record["text"]
            + "[exit 0]\n[done]\nA90P1 END\na90:/#\n"
        )
        self.assertEqual(
            runner.require_exact_arm_dispatch_receipt(framed, intent_sha256)[1],
            "armed",
        )
        for replacement in (
            "source_receipt=retained",
            "full_sha=skipped",
            "expected_sha_match=0",
        ):
            changed = json.loads(json.dumps(record))
            if replacement.startswith("source_receipt"):
                changed["text"] = changed["text"].replace(
                    "source_receipt=qualified",
                    replacement,
                )
            elif replacement.startswith("full_sha"):
                changed["text"] = changed["text"].replace(
                    "full_sha=verified",
                    replacement,
                )
            else:
                changed["text"] = changed["text"].replace(
                    "expected_sha_match=1",
                    replacement,
                )
            with self.subTest(replacement=replacement), self.assertRaisesRegex(
                runner.ContractError,
                "one fresh full-SHA qualification",
            ):
                runner.require_exact_arm_dispatch_receipt(changed, intent_sha256)
        duplicated = json.loads(json.dumps(record))
        duplicated["text"] += record["text"]
        with self.assertRaisesRegex(
            runner.ContractError,
            "one fresh full-SHA qualification",
        ):
            runner.require_exact_arm_dispatch_receipt(duplicated, intent_sha256)
        for malformed in (
            "A90D3H0\n",
            "A90D3H0\tmalformed=1\n",
            "A90D3H0_UNRECOGNIZED=1\n",
            "A90AUTO_ARM\n",
            "A90AUTO_ARM\tmalformed=1\n",
            "A90AUTO_ARM_UNRECOGNIZED=1\n",
        ):
            with self.subTest(malformed=malformed):
                changed = json.loads(json.dumps(record))
                changed["text"] += malformed
                with self.assertRaisesRegex(
                    runner.ContractError,
                    "one fresh full-SHA qualification",
                ):
                    runner.require_exact_arm_dispatch_receipt(
                        changed,
                        intent_sha256,
                    )

    def test_appended_benchmark_selects_current_complete_suffix(self) -> None:
        opening = self._complete_benchmark_segment(1_000)
        current = self._complete_benchmark_segment(100)
        returned = "\n".join(
            self._benchmark_marker(stage, 50 + index * 10)
            for index, stage in enumerate(
                (
                    "native_runtime_ready",
                    "native_services_ready",
                    "auto_handoff_check",
                    "auto_handoff_latched_native",
                )
            )
        )
        with mock.patch.object(
            runner.base,
            "require_exact_f1_command_receipt",
            side_effect=lambda value, _command, _label: value,
        ):
            parsed = runner.parse_appended_benchmark(
                {"text": opening},
                {"text": "\n".join((opening, current, returned))},
            )

        self.assertEqual(parsed["status"], "complete")
        self.assertEqual(parsed["boot_segments_total"], 2)
        self.assertEqual(parsed["selected_segment_index"], 0)
        self.assertEqual(parsed["selection"]["opening_marker_count"], 15)
        self.assertEqual(parsed["selection"]["appended_marker_count"], 19)
        self.assertEqual(
            parsed["selection"]["log_relation"],
            "opening-prefix-appended-suffix",
        )

    def test_appended_benchmark_accepts_disjoint_current_boot_window(self) -> None:
        opening = self._complete_benchmark_segment(1_000)
        current = self._complete_benchmark_segment(100)
        returned = "\n".join(
            self._benchmark_marker(stage, 50 + index * 10)
            for index, stage in enumerate(runner.RETURNED_NATIVE_TAIL)
        )
        with mock.patch.object(
            runner.base,
            "require_exact_f1_command_receipt",
            side_effect=lambda value, _command, _label: value,
        ):
            parsed = runner.parse_appended_benchmark(
                {"text": opening},
                {"text": "\n".join((current, returned))},
            )

        self.assertEqual(parsed["status"], "complete")
        self.assertEqual(parsed["boot_segments_total"], 2)
        self.assertEqual(parsed["selected_segment_index"], 0)
        self.assertEqual(parsed["selection"]["opening_marker_count"], 15)
        self.assertEqual(parsed["selection"]["appended_marker_count"], 19)
        self.assertEqual(
            parsed["selection"]["log_relation"],
            "disjoint-current-window",
        )
        runner.validate_benchmark_selection(parsed)
        for field, replacement in (
            ("contract", "opening-marker-prefix-appended-suffix-v1"),
            ("log_relation", "other"),
            ("appended_marker_count", 18),
        ):
            changed = json.loads(json.dumps(parsed))
            changed["selection"][field] = replacement
            with self.subTest(field=field), self.assertRaisesRegex(
                runner.ContractError,
                "benchmark appended-marker selection changed",
            ):
                runner.validate_benchmark_selection(changed)
        for label, field, replacement in (
            ("segment-count", "boot_segments_total", 1),
            ("segment-count-bool", "boot_segments_total", True),
            ("selected-index", "selected_segment_index", 1),
            ("selected-index-bool", "selected_segment_index", False),
        ):
            changed = json.loads(json.dumps(parsed))
            changed[field] = replacement
            with self.subTest(label=label), self.assertRaisesRegex(
                runner.ContractError,
                "benchmark appended-marker selection changed",
            ):
                runner.validate_benchmark_selection(changed)

    def test_appended_benchmark_accepts_exact_h11_direct_segments(self) -> None:
        opening = self._complete_benchmark_segment(1_000)
        current = self._direct_complete_benchmark_segment(100)
        returned = "\n".join(
            self._benchmark_marker(stage, 50 + index * 10)
            for index, stage in enumerate(
                self._with_direct_stage(runner.RETURNED_NATIVE_TAIL)
            )
        )
        with mock.patch.object(
            runner.base,
            "require_exact_f1_command_receipt",
            side_effect=lambda value, _command, _label: value,
        ):
            parsed = runner.parse_appended_benchmark(
                {"text": opening},
                {"text": "\n".join((current, returned))},
            )

        self.assertEqual(parsed["status"], "complete")
        self.assertEqual(parsed["boot_segments_total"], 2)
        self.assertEqual(parsed["selection"]["appended_marker_count"], 21)
        self.assertEqual(
            parsed["selection"]["segment_stages"],
            [
                list(self._with_direct_stage(runner.benchmark.COMPLETE_STAGES)),
                list(self._with_direct_stage(runner.RETURNED_NATIVE_TAIL)),
            ],
        )
        runner.validate_benchmark_selection(parsed)

        changed = json.loads(json.dumps(parsed))
        changed["selection"]["segment_stages"][1].remove(
            runner.DIRECT_HANDOFF_STAGE
        )
        with self.assertRaisesRegex(
            runner.ContractError,
            "benchmark appended-marker selection changed",
        ):
            runner.validate_benchmark_selection(changed)

    def test_appended_benchmark_rejects_misplaced_or_duplicate_direct_stage(self) -> None:
        opening = self._complete_benchmark_segment(1_000)
        returned = "\n".join(
            self._benchmark_marker(stage, 50 + index * 10)
            for index, stage in enumerate(
                self._with_direct_stage(runner.RETURNED_NATIVE_TAIL)
            )
        )
        complete = list(runner.benchmark.COMPLETE_STAGES)
        malformed_variants = []
        misplaced = list(complete)
        misplaced.insert(0, runner.DIRECT_HANDOFF_STAGE)
        malformed_variants.append(misplaced)
        duplicated = list(self._with_direct_stage(runner.benchmark.COMPLETE_STAGES))
        duplicated.insert(
            duplicated.index("native_services_ready"),
            runner.DIRECT_HANDOFF_STAGE,
        )
        malformed_variants.append(duplicated)

        for stages in malformed_variants:
            current = "\n".join(
                self._benchmark_marker(stage, 100 + index * 10)
                for index, stage in enumerate(stages)
            )
            with self.subTest(stages=stages), mock.patch.object(
                runner.base,
                "require_exact_f1_command_receipt",
                side_effect=lambda value, _command, _label: value,
            ), self.assertRaisesRegex(
                runner.benchmark.BenchmarkError,
                "exactly one terminal handoff segment",
            ):
                runner.parse_appended_benchmark(
                    {"text": opening},
                    {"text": "\n".join((current, returned))},
                )

    def test_prefix_window_keeps_optional_returned_native_early_stage(self) -> None:
        opening = self._complete_benchmark_segment(1_000)
        current = self._complete_benchmark_segment(100)
        returned = "\n".join(
            self._benchmark_marker(stage, 50 + index * 10)
            for index, stage in enumerate(
                runner.benchmark.OPTIONAL_EARLY_STAGES
                + runner.RETURNED_NATIVE_TAIL
            )
        )
        with mock.patch.object(
            runner.base,
            "require_exact_f1_command_receipt",
            side_effect=lambda value, _command, _label: value,
        ):
            parsed = runner.parse_appended_benchmark(
                {"text": opening},
                {"text": "\n".join((opening, current, returned))},
            )
        self.assertEqual(parsed["selection"]["appended_marker_count"], 20)
        self.assertEqual(
            parsed["selection"]["log_relation"],
            "opening-prefix-appended-suffix",
        )
        runner.validate_benchmark_selection(parsed)

    def test_disjoint_window_rejects_optional_returned_native_early_stage(self) -> None:
        opening = self._complete_benchmark_segment(1_000)
        current = self._complete_benchmark_segment(100)
        returned = "\n".join(
            self._benchmark_marker(stage, 50 + index * 10)
            for index, stage in enumerate(
                runner.benchmark.OPTIONAL_EARLY_STAGES
                + runner.RETURNED_NATIVE_TAIL
            )
        )
        with mock.patch.object(
            runner.base,
            "require_exact_f1_command_receipt",
            side_effect=lambda value, _command, _label: value,
        ), self.assertRaisesRegex(
            runner.benchmark.BenchmarkError,
            "noncanonical returned-native boot tail",
        ):
            runner.parse_appended_benchmark(
                {"text": opening},
                {"text": "\n".join((current, returned))},
            )

    def test_appended_benchmark_rejects_unchanged_or_incomplete_fresh_log(self) -> None:
        opening = self._complete_benchmark_segment(1_000)
        current = self._complete_benchmark_segment(100)
        with mock.patch.object(
            runner.base,
            "require_exact_f1_command_receipt",
            side_effect=lambda value, _command, _label: value,
        ):
            with self.assertRaisesRegex(
                runner.ContractError,
                "exact appended marker suffix",
            ):
                runner.parse_appended_benchmark(
                    {"text": opening},
                    {"text": opening},
                )
            with self.assertRaisesRegex(
                runner.benchmark.BenchmarkError,
                "lacks the exact returned-native boot tail",
            ):
                runner.parse_appended_benchmark(
                    {"text": opening},
                    {"text": current},
                )

    def test_h12_direct_prelude_is_exact_for_handoff_and_return(self) -> None:
        for autoconnect in runner.H12_WIFI_AUTOCONNECT_STAGES:
            with self.subTest(autoconnect=autoconnect):
                complete = list(
                    self._with_h12_direct_stages(
                        runner.benchmark.COMPLETE_STAGES,
                        autoconnect=autoconnect,
                    )
                )
                returned = list(
                    self._with_h12_direct_stages(
                        runner.RETURNED_NATIVE_TAIL,
                        autoconnect=autoconnect,
                    )
                )
                self.assertTrue(runner.complete_handoff_stages_exact(complete))
                self.assertTrue(runner.returned_native_stages_exact(returned))
                self.assertEqual(
                    runner.normalize_direct_handoff_stage(complete),
                    list(runner.benchmark.COMPLETE_STAGES),
                )

    def test_h12_direct_prelude_parses_as_one_terminal_and_one_return(self) -> None:
        opening = self._complete_benchmark_segment(1_000)
        current = "\n".join(
            self._benchmark_marker(stage, 100 + index * 10)
            for index, stage in enumerate(
                self._with_h12_direct_stages(runner.benchmark.COMPLETE_STAGES)
            )
        )
        returned = "\n".join(
            self._benchmark_marker(stage, 50 + index * 10)
            for index, stage in enumerate(
                self._with_h12_direct_stages(runner.RETURNED_NATIVE_TAIL)
            )
        )
        with mock.patch.object(
            runner.base,
            "require_exact_f1_command_receipt",
            side_effect=lambda value, _command, _label: value,
        ):
            parsed = runner.parse_appended_benchmark(
                {"text": opening},
                {"text": "\n".join((opening, current, returned))},
            )
        self.assertEqual(parsed["status"], "complete")
        self.assertEqual(parsed["boot_segments_total"], 2)
        self.assertEqual(parsed["selection"]["appended_marker_count"], 27)
        self.assertEqual(
            parsed["selection"]["contract"],
            runner.BENCHMARK_SELECTION_CONTRACT,
        )
        runner.validate_benchmark_selection(parsed)

    def test_h12_direct_prelude_rejects_partial_duplicate_or_reordered(self) -> None:
        exact = list(
            self._with_h12_direct_stages(runner.benchmark.COMPLETE_STAGES)
        )
        malformed = []
        missing = list(exact)
        missing.remove(runner.H12_NCM_HANDOFF_STAGE)
        malformed.append(missing)
        duplicate = list(exact)
        duplicate.insert(
            duplicate.index(runner.H12_NCM_HANDOFF_STAGE),
            runner.H12_WIFI_COMPANION_STAGE,
        )
        malformed.append(duplicate)
        reordered = list(exact)
        left = reordered.index(runner.H12_WIFI_COMPANION_STAGE)
        right = reordered.index(runner.H12_NCM_HANDOFF_STAGE)
        reordered[left], reordered[right] = reordered[right], reordered[left]
        malformed.append(reordered)
        both = list(exact)
        both.insert(
            both.index(runner.H12_NCM_HANDOFF_STAGE),
            "native_wifi_autoconnect_inactive",
        )
        malformed.append(both)
        for stages in malformed:
            with self.subTest(stages=stages):
                self.assertIsNone(runner.normalize_direct_handoff_stage(stages))
                self.assertFalse(runner.complete_handoff_stages_exact(stages))

    def test_appended_benchmark_rejects_mixed_rotated_window(self) -> None:
        opening = self._complete_benchmark_segment(1_000)
        current = self._complete_benchmark_segment(100)
        returned = "\n".join(
            self._benchmark_marker(stage, 50 + index * 10)
            for index, stage in enumerate(runner.RETURNED_NATIVE_TAIL)
        )
        opening_first = next(runner.benchmark.marker_lines([opening]))
        mixed = "\n".join(
            (
                f"{runner.benchmark.MARKER}{opening_first}",
                current,
                returned,
            )
        )
        with mock.patch.object(
            runner.base,
            "require_exact_f1_command_receipt",
            side_effect=lambda value, _command, _label: value,
        ), self.assertRaisesRegex(
            runner.ContractError,
            "exact appended marker suffix",
        ):
            runner.parse_appended_benchmark(
                {"text": opening},
                {"text": mixed},
            )

    def test_appended_benchmark_rejects_two_new_handoff_segments(self) -> None:
        opening = self._complete_benchmark_segment(1_000)
        first = self._complete_benchmark_segment(100)
        second = self._complete_benchmark_segment(50)
        with mock.patch.object(
            runner.base,
            "require_exact_f1_command_receipt",
            side_effect=lambda value, _command, _label: value,
        ), self.assertRaisesRegex(
            runner.benchmark.BenchmarkError,
            "exactly one terminal handoff segment",
        ):
            runner.parse_appended_benchmark(
                {"text": opening},
                {"text": "\n".join((opening, first, second))},
            )

    def test_appended_benchmark_rejects_complete_then_failed_segments(self) -> None:
        opening = self._complete_benchmark_segment(1_000)
        complete = self._complete_benchmark_segment(100)
        failed = self._failed_benchmark_segment(50)
        with mock.patch.object(
            runner.base,
            "require_exact_f1_command_receipt",
            side_effect=lambda value, _command, _label: value,
        ), self.assertRaisesRegex(
            runner.benchmark.BenchmarkError,
            "exactly one terminal handoff segment",
        ):
            runner.parse_appended_benchmark(
                {"text": opening},
                {"text": "\n".join((opening, complete, failed))},
            )

    def test_appended_benchmark_rejects_failed_then_complete_segments(self) -> None:
        opening = self._complete_benchmark_segment(1_000)
        failed = self._failed_benchmark_segment(100)
        complete = self._complete_benchmark_segment(50)
        with mock.patch.object(
            runner.base,
            "require_exact_f1_command_receipt",
            side_effect=lambda value, _command, _label: value,
        ), self.assertRaisesRegex(
            runner.benchmark.BenchmarkError,
            "exactly one terminal handoff segment",
        ):
            runner.parse_appended_benchmark(
                {"text": opening},
                {"text": "\n".join((opening, failed, complete))},
            )

    def test_appended_benchmark_accepts_exact_returned_native_failure(self) -> None:
        opening = self._complete_benchmark_segment(1_000)
        failed = self._failed_benchmark_segment(100)
        with mock.patch.object(
            runner.base,
            "require_exact_f1_command_receipt",
            side_effect=lambda value, _command, _label: value,
        ):
            parsed = runner.parse_appended_benchmark(
                {"text": opening},
                {"text": "\n".join((opening, failed))},
            )

        self.assertEqual(parsed["status"], "partial")
        self.assertTrue(parsed["native_handoff_failed"])
        self.assertEqual(
            parsed["missing_complete_stages"],
            ["mount_moves_done", "switch_root_exec"],
        )

    def test_appended_benchmark_rejects_nonprefix_failed_handoff(self) -> None:
        opening = self._complete_benchmark_segment(1_000)
        stages = (
            "native_runtime_ready",
            "native_services_ready",
            "auto_handoff_check",
            "auto_handoff_dispatched",
            "handoff_begin",
            "root_mounted",
            *runner.FAILED_HANDOFF_TAIL,
        )
        malformed = "\n".join(
            self._benchmark_marker(stage, 100 + index * 10)
            for index, stage in enumerate(stages)
        )
        with mock.patch.object(
            runner.base,
            "require_exact_f1_command_receipt",
            side_effect=lambda value, _command, _label: value,
        ), self.assertRaisesRegex(
            runner.benchmark.BenchmarkError,
            "failed-handoff benchmark segment is not exact",
        ):
            runner.parse_appended_benchmark(
                {"text": opening},
                {"text": "\n".join((opening, malformed))},
            )

    def test_first_boot_log_allows_only_repeated_exact_unarmed_states(self) -> None:
        record = {
            "command": ["logcat"],
            "rc": 0,
            "status": "ok",
            "trust": "A90P1_V1_STRUCTURAL_ONLY",
            "begin": {"argc": "1", "cmd": "logcat", "flags": "0x0", "seq": "9"},
            "end": {
                "cmd": "logcat",
                "duration_ms": "1",
                "errno": "0",
                "flags": "0x0",
                "rc": "0",
                "seq": "9",
                "status": "ok",
            },
            "text": (
                "[5185ms] auto-handoff: A90AUTO state=unarmed-stay-native\r\n"
                "[5144ms] auto-handoff: A90AUTO state=unarmed-stay-native\r\n"
            ),
        }
        runner.require_first_boot_unarmed(record)

        for bad_line in (
            "A90AUTO state=dispatch-once",
            "A90AUTO state=armed-waiting-reboot",
            "",
        ):
            bad = dict(record)
            bad["text"] = bad_line
            with self.subTest(bad_line=bad_line), self.assertRaises(runner.ContractError):
                runner.require_first_boot_unarmed(bad)

    def test_execution_closure_binds_runner_parser_and_binding_loaders(self) -> None:
        closure = runner.execution_closure()
        self.assertEqual(
            set(closure["files"]),
            {
                "runner",
                "benchmark_parser",
                "ondevice_evidence",
                "resident_manifest_loader",
                "resident_f1_loader",
            },
        )
        self.assertRegex(closure["sha256"], r"^[0-9a-f]{64}$")

    def test_durable_same_ordinal_and_live_host_evidence_drive_pass(self) -> None:
        intent_sha256 = "a" * 64
        opening = self._complete_benchmark_segment(1_000)
        current = self._complete_benchmark_segment(100)
        durable = "\n".join(
            (
                self._ondevice_record("debian_pid1", 1_000, intent_sha256),
                self._ondevice_record("debian_sshd", 2_000, intent_sha256),
                self._ondevice_record("debian_drm_master", 3_000, intent_sha256),
                self._ondevice_record("debian_wifi", 4_000, intent_sha256),
            )
        )
        log_record = {"command": ["logcat"], "text": "\n".join((opening, current, durable))}
        status_record = self._status(1, 1)
        preflight = SimpleNamespace(validate=lambda: None)
        observation = {
            "proof": False,
            "guard_release": {"released": True},
            **self._host_link(),
        }
        with (
            mock.patch.object(
                runner,
                "require_auto_status",
                return_value=(status_record, runner.parse_auto_status(status_record)),
            ),
            mock.patch.object(
                runner,
                "fast_resident_preflight",
                return_value=(preflight, {"resident_healthy": True}, {"size": 1}),
            ),
            mock.patch.object(runner.base, "run_f1_cmd", return_value=log_record),
            mock.patch.object(
                runner.base,
                "require_exact_f1_command_receipt",
                side_effect=lambda value, _command, _label: value,
            ),
        ):
            result = runner.finalize_cycle(
                self._spec(),
                SimpleNamespace(),
                observation,
                intent_sha256=intent_sha256,
                opening_log_record={"command": ["logcat"], "text": opening},
                visible_confirmed="yes",
                cleanup_evidence={"proof": True},
                source_identity={"size": 1},
            )

        self.assertEqual(result["terminal"], "PASS_AUTO_HANDOFF_BENCHMARK_VISIBLE")
        self.assertTrue(result["ondevice_evidence"]["proof"])
        self.assertTrue(runner.h12_wifi_proven(result["ondevice_evidence"]))
        self.assertIn("candidate_return", observation)

    def test_historical_evidence_without_wifi_cannot_pass_h12(self) -> None:
        intent_sha256 = "d" * 64
        durable = "\n".join(
            self._ondevice_record(phase, stamp, intent_sha256)
            for phase, stamp in (
                ("debian_pid1", 1_000),
                ("debian_sshd", 2_000),
                ("debian_drm_master", 3_000),
            )
        )
        evaluated = runner.ondevice_evidence.evaluate(durable, intent_sha256)
        self.assertTrue(evaluated["proof"], evaluated["reason"])
        self.assertFalse(runner.h12_wifi_proven(evaluated))

    def test_native_failed_handoff_is_refuted_not_observer_no_proof(self) -> None:
        intent_sha256 = "c" * 64
        opening = self._complete_benchmark_segment(1_000)
        failed = self._failed_benchmark_segment(100)
        log_record = {"command": ["logcat"], "text": "\n".join((opening, failed))}
        status_record = self._status(1, 1)
        preflight = SimpleNamespace(validate=lambda: None)
        observation = {
            "proof": False,
            "observer_error": {"type": "RuntimeError", "message": "SSH absent"},
            "guard_release": {"released": True},
        }
        with (
            mock.patch.object(
                runner,
                "require_auto_status",
                return_value=(status_record, runner.parse_auto_status(status_record)),
            ),
            mock.patch.object(
                runner,
                "fast_resident_preflight",
                return_value=(preflight, {"resident_healthy": True}, {"size": 1}),
            ),
            mock.patch.object(runner.base, "run_f1_cmd", return_value=log_record),
            mock.patch.object(
                runner.base,
                "require_exact_f1_command_receipt",
                side_effect=lambda value, _command, _label: value,
            ),
        ):
            result = runner.finalize_cycle(
                self._spec(),
                SimpleNamespace(),
                observation,
                intent_sha256=intent_sha256,
                opening_log_record={"command": ["logcat"], "text": opening},
                visible_confirmed="unavailable",
                cleanup_evidence={"proof": True},
                source_identity={"size": 1},
            )

        self.assertEqual(
            result["terminal"],
            "REFUTED_AUTO_HANDOFF_NATIVE_HANDOFF_RESIDENT_HEALTHY",
        )
        self.assertTrue(result["benchmark"]["native_handoff_failed"])
        self.assertFalse(result["ondevice_evidence"]["proof"])

    def test_durable_evidence_cannot_replace_exact_host_link_facts(self) -> None:
        observation = self._host_link()
        self.assertTrue(runner.host_link_proven(self._spec(), observation))
        observation["debian_ncm_continuity"] = dict(
            observation["debian_ncm_continuity"]
        )
        observation["debian_ncm_continuity"]["after_service"] = False
        self.assertFalse(runner.host_link_proven(self._spec(), observation))
        observation["debian_ncm_continuity"]["after_service"] = 1
        self.assertFalse(runner.host_link_proven(self._spec(), observation))
        observation["debian_ncm_continuity"]["after_service"] = True
        observation["candidate_return"]["return_epoch"]["returned"][
            "usb_devnum"
        ] = 1
        observation["candidate_return"]["return_epoch"][
            "returned_usb_identity"
        ]["usb_devnum"] = True
        self.assertFalse(runner.host_link_proven(self._spec(), observation))
        observation = self._host_link()
        observation["host_ncm_rebind"] = dict(observation["host_ncm_rebind"])
        observation["host_ncm_rebind"]["exact_interface_count"] = 0
        self.assertFalse(runner.host_link_proven(self._spec(), observation))

    def test_durable_evidence_result_is_recomputed_from_bound_log(self) -> None:
        intent_sha256 = "b" * 64
        opening = self._complete_benchmark_segment(1_000)
        current = self._complete_benchmark_segment(100)
        durable = "\n".join(
            self._ondevice_record(phase, stamp, intent_sha256)
            for phase, stamp in (
                ("debian_pid1", 1_000),
                ("debian_sshd", 2_000),
                ("debian_drm_master", 3_000),
                ("debian_wifi", 4_000),
            )
        )
        log_record = {"command": ["logcat"], "text": "\n".join((opening, current, durable))}
        status_record = self._status(1, 1)
        preflight = SimpleNamespace(validate=lambda: None)
        observation = {
            "guard_release": {"released": True},
            **self._host_link(),
        }
        with (
            mock.patch.object(
                runner,
                "require_auto_status",
                return_value=(status_record, runner.parse_auto_status(status_record)),
            ),
            mock.patch.object(
                runner,
                "fast_resident_preflight",
                return_value=(preflight, {}, {"size": 1}),
            ),
            mock.patch.object(runner.base, "run_f1_cmd", return_value=log_record),
            mock.patch.object(
                runner.base,
                "require_exact_f1_command_receipt",
                side_effect=lambda value, _command, _label: value,
            ),
        ):
            result = runner.finalize_cycle(
                self._spec(),
                SimpleNamespace(),
                observation,
                intent_sha256=intent_sha256,
                opening_log_record={"command": ["logcat"], "text": opening},
                visible_confirmed="unavailable",
                cleanup_evidence={"proof": True},
                source_identity={"size": 1},
            )
            result["ondevice_evidence"] = dict(result["ondevice_evidence"])
            result["ondevice_evidence"]["proof"] = False
            with self.assertRaisesRegex(runner.ContractError, "durable evidence changed"):
                runner.validate_result(
                    self._spec(),
                    result,
                    intent_sha256,
                    opening_log_record={"command": ["logcat"], "text": opening},
                )

    def test_persisted_benchmark_is_reparsed_from_exact_raw_logs(self) -> None:
        intent_sha256 = "c" * 64
        opening = self._complete_benchmark_segment(1_000)
        current = self._direct_complete_benchmark_segment(100)
        returned = "\n".join(
            self._benchmark_marker(stage, 50 + index * 10)
            for index, stage in enumerate(
                self._with_direct_stage(runner.RETURNED_NATIVE_TAIL)
            )
        )
        durable = "\n".join(
            self._ondevice_record(phase, stamp, intent_sha256)
            for phase, stamp in (
                ("debian_pid1", 1_000),
                ("debian_sshd", 2_000),
                ("debian_drm_master", 3_000),
                ("debian_wifi", 4_000),
            )
        )
        opening_record = {"command": ["logcat"], "text": opening}
        log_record = {
            "command": ["logcat"],
            "text": "\n".join((opening, current, returned, durable)),
        }
        status_record = self._status(1, 1)
        preflight = SimpleNamespace(validate=lambda: None)
        cleanup = {
            "dispatch_count": 0,
            "inferred_from_absence": True,
            "receipt": None,
            "absence_preflight": {},
        }
        observation = {"guard_release": {"released": True}, **self._host_link()}
        with (
            mock.patch.object(
                runner,
                "require_auto_status",
                return_value=(status_record, runner.parse_auto_status(status_record)),
            ),
            mock.patch.object(
                runner,
                "fast_resident_preflight",
                return_value=(preflight, {}, {"size": 1}),
            ),
            mock.patch.object(runner.base, "run_f1_cmd", return_value=log_record),
            mock.patch.object(
                runner.base,
                "require_exact_f1_command_receipt",
                side_effect=lambda value, _command, _label: value,
            ),
            mock.patch.object(runner, "validate_preflight_evidence", return_value={}),
        ):
            result = runner.finalize_cycle(
                self._spec(),
                SimpleNamespace(),
                observation,
                intent_sha256=intent_sha256,
                opening_log_record=opening_record,
                visible_confirmed="yes",
                cleanup_evidence=cleanup,
                source_identity={"size": 1},
            )
            runner.validate_result(
                self._spec(),
                result,
                intent_sha256,
                opening_log_record=opening_record,
                expected_source_identity={"size": 1},
            )

            tampered = []
            changed = json.loads(json.dumps(result))
            changed["benchmark"]["selection"]["segment_stages"][1].remove(
                runner.DIRECT_HANDOFF_STAGE
            )
            changed["benchmark"]["selection"]["appended_marker_count"] -= 1
            tampered.append(changed)
            changed = json.loads(json.dumps(result))
            changed["benchmark"]["selection"]["opening_marker_count"] = 999
            changed["benchmark"]["selection"]["opening_markers_sha256"] = "f" * 64
            tampered.append(changed)
            changed = json.loads(json.dumps(result))
            direct = next(
                record
                for record in changed["benchmark"]["records"]
                if record["stage"] == runner.DIRECT_HANDOFF_STAGE
            )
            changed["benchmark"]["records"].insert(2, dict(direct))
            changed["benchmark"]["selection"]["segment_stages"][0].insert(
                2,
                runner.DIRECT_HANDOFF_STAGE,
            )
            changed["benchmark"]["selection"]["appended_marker_count"] += 1
            tampered.append(changed)
            changed = json.loads(json.dumps(result))
            changed["benchmark"]["records"][0]["clock_ok"] = True
            changed["benchmark"]["records"][0]["telemetry_sampled"] = True
            tampered.append(changed)

            for value in tampered:
                with self.subTest(value=value), self.assertRaisesRegex(
                    runner.ContractError,
                    "does not match its exact raw logs",
                ):
                    runner.validate_result(
                        self._spec(),
                        value,
                        intent_sha256,
                        opening_log_record=opening_record,
                        expected_source_identity={"size": 1},
                    )

    def test_recorded_historical_closure_is_digest_and_role_bound(self) -> None:
        closure = runner.execution_closure()
        self.assertEqual(
            runner.validate_recorded_execution_closure(
                closure,
                closure["sha256"],
            ),
            closure,
        )
        changed = json.loads(json.dumps(closure))
        changed["files"]["runner"]["size"] += 1
        with self.assertRaisesRegex(runner.ContractError, "digest changed"):
            runner.validate_recorded_execution_closure(
                changed,
                closure["sha256"],
            )

    def test_auto_observer_rebinds_exact_ncm_before_ssh(self) -> None:
        order: list[str] = []
        binding = self._pre_reboot_binding()
        post_ncm = self._post_reboot_ncm()
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            mock.patch.object(
                runner,
                "_f1_spec",
                return_value=SimpleNamespace(
                    stage=SimpleNamespace(bridge_realpath="/dev/ttyACM0")
                ),
            ),
            mock.patch.object(
                runner,
                "wait_for_bound_ncm_after_reboot",
                side_effect=lambda *_a: order.append("identity") or post_ncm,
            ),
            mock.patch.object(
                runner,
                "rebind_host_ncm_for_bound_identity",
                side_effect=lambda *_a: order.append("ncm") or {"ready": True},
            ),
            mock.patch.object(
                runner,
                "validate_post_reboot_ncm_identity",
                side_effect=lambda *_a, **_k: order.append("live") or post_ncm,
            ),
            mock.patch.object(
                runner.base,
                "observe_ssh",
                side_effect=lambda *_a: order.append("ssh") or {"proof": True},
            ),
            mock.patch.object(
                runner.phase3_observer,
                "observe_phase3_service",
                side_effect=lambda *_a: order.append("service") or {"proof": True},
            ),
            mock.patch.object(
                runner,
                "wait_for_native_return_after_bound_ncm",
                side_effect=lambda *_a, **_k: order.append("return") or {},
            ),
            mock.patch.object(
                runner.base,
                "release_candidate_return_modemmanager_guard",
                side_effect=lambda *_a: order.append("release") or {"released": True},
            ),
            mock.patch.object(
                runner.base,
                "collect_and_clear_retained_pmsg",
                side_effect=lambda *_a: order.append("pmsg") or {},
            ),
        ):
            result = runner.observe_auto_cycle(
                self._spec(),
                SimpleNamespace(),
                Path(temp_dir),
                object(),
                binding,
            )
        self.assertEqual(
            order,
            [
                "identity", "ncm", "live", "ssh", "live", "service",
                "live", "return", "release", "pmsg",
            ],
        )
        self.assertEqual(result["debian_ncm_identity"], post_ncm)
        self.assertEqual(result["host_ncm_rebind"], {"ready": True})
        self.assertEqual(
            result["debian_ncm_continuity"],
            {"before_ssh": True, "after_ssh": True, "after_service": True},
        )

    def test_pre_reboot_binding_current_rejects_epoch_change(self) -> None:
        binding = self._pre_reboot_binding()
        changed = json.loads(json.dumps(binding))
        changed["usb_identity"]["usb_devnum"] = 9
        changed["serial_epoch"]["usb_devnum"] = 9
        with (
            mock.patch.object(
                runner,
                "capture_pre_reboot_observer_binding",
                return_value=changed,
            ),
            self.assertRaisesRegex(runner.ContractError, "binding changed"),
        ):
            runner.require_pre_reboot_observer_binding_current(
                SimpleNamespace(
                    stage=SimpleNamespace(bridge_realpath="/dev/ttyACM0")
                ),
                SimpleNamespace(),
                binding,
            )

    def test_post_reboot_ncm_wait_requires_a_new_usb_epoch(self) -> None:
        binding = self._pre_reboot_binding()
        old = {
            key: value
            for key, value in self._post_reboot_ncm(devnum=8).items()
            if key
            in {
                "interface",
                "usb_topology",
                "usb_serial_sha256",
                "usb_vendor",
                "usb_product",
                "usb_busnum",
                "usb_devnum",
            }
        }
        new = dict(old, usb_devnum=9)
        with (
            mock.patch.object(
                runner,
                "_matching_bound_ncm_interfaces",
                side_effect=[[old], [new]],
            ),
            mock.patch.object(runner.time, "sleep") as sleep,
        ):
            result = runner.wait_for_bound_ncm_after_reboot(binding)
        self.assertEqual(result, self._post_reboot_ncm())
        sleep.assert_called_once_with(runner.base.HOST_NCM_REBIND_POLL_SEC)

    def test_post_reboot_ncm_wait_rejects_ambiguous_match(self) -> None:
        match = {
            key: value
            for key, value in self._post_reboot_ncm().items()
            if key
            in {
                "interface",
                "usb_topology",
                "usb_serial_sha256",
                "usb_vendor",
                "usb_product",
                "usb_busnum",
                "usb_devnum",
            }
        }
        with (
            mock.patch.object(
                runner,
                "_matching_bound_ncm_interfaces",
                return_value=[match, dict(match, interface="enx667788990011")],
            ),
            self.assertRaisesRegex(runner.ContractError, "multiple NCM interfaces"),
        ):
            runner.wait_for_bound_ncm_after_reboot(self._pre_reboot_binding())

    def test_post_reboot_ncm_wait_is_bounded_when_absent(self) -> None:
        with (
            mock.patch.object(
                runner,
                "_matching_bound_ncm_interfaces",
                return_value=[],
            ),
            mock.patch.object(runner.time, "monotonic", side_effect=[0.0, 31.0]),
            mock.patch.object(runner.time, "sleep") as sleep,
            self.assertRaisesRegex(runner.ContractError, "did not appear"),
        ):
            runner.wait_for_bound_ncm_after_reboot(self._pre_reboot_binding())
        sleep.assert_not_called()

    def test_post_reboot_ncm_live_validation_rejects_identity_loss(self) -> None:
        with (
            mock.patch.object(
                runner,
                "_matching_bound_ncm_interfaces",
                return_value=[],
            ),
            self.assertRaisesRegex(runner.ContractError, "no longer current"),
        ):
            runner.validate_post_reboot_ncm_identity(
                self._pre_reboot_binding(),
                self._post_reboot_ncm(),
                require_live=True,
            )

    def test_bound_ncm_ready_requires_exact_interface_route_and_cidr(self) -> None:
        spec = SimpleNamespace(observer_device="192.168.7.2")
        commands = [
            {
                "returncode": 0,
                "stdout": (
                    "192.168.7.2 dev enx001122334455 src 192.168.7.1 uid 1000\n"
                    "    cache\n"
                ),
            },
            {"returncode": 0, "stdout": "2: x inet 192.168.7.1/24 scope global\n"},
            {"returncode": 0, "stdout": "1 packets transmitted, 1 received\n"},
        ]
        with (
            mock.patch.object(
                runner,
                "validate_post_reboot_ncm_identity",
                side_effect=lambda _binding, value, **_kwargs: value,
            ) as validate,
            mock.patch.object(
                runner.base,
                "_host_command",
                side_effect=commands,
            ) as host,
        ):
            result = runner._require_bound_host_ncm_ready(
                spec,
                self._pre_reboot_binding(),
                self._post_reboot_ncm(),
            )
        self.assertEqual(
            result,
            {
                "verified_a90_ncm": True,
                "direct_route": True,
                "host_cidr_present": True,
                "device_ping": True,
            },
        )
        self.assertEqual(validate.call_count, 2)
        self.assertEqual(host.call_count, 3)

    def test_bound_ncm_ready_rejects_route_on_other_interface(self) -> None:
        with (
            mock.patch.object(
                runner,
                "validate_post_reboot_ncm_identity",
                side_effect=lambda _binding, value, **_kwargs: value,
            ),
            mock.patch.object(
                runner.base,
                "_host_command",
                return_value={
                    "returncode": 0,
                    "stdout": (
                        "192.168.7.2 dev enx667788990011 src 192.168.7.1\n"
                        "    cache\n"
                    ),
                },
            ),
            self.assertRaisesRegex(runner.ContractError, "bound A90 NCM"),
        ):
            runner._require_bound_host_ncm_ready(
                SimpleNamespace(observer_device="192.168.7.2"),
                self._pre_reboot_binding(),
                self._post_reboot_ncm(),
            )

    def test_native_return_wait_rejects_debian_epoch_then_accepts_later_acm(self) -> None:
        binding = self._pre_reboot_binding()
        ncm = self._post_reboot_ncm(devnum=9)
        spec = SimpleNamespace(
            stage=SimpleNamespace(bridge_device="/dev/a90-test"),
            candidate_return_timeout=180,
            candidate_version=runner.EXPECTED_VERSION,
            candidate_build=runner.EXPECTED_BUILD,
        )
        bridge = {"selected_realpath": "/dev/ttyACM0"}
        same_epoch = {
            "selected_realpath": "/dev/ttyACM0",
            "usb_busnum": 2,
            "usb_devnum": 9,
        }
        returned_epoch = dict(same_epoch, usb_devnum=10)
        guard = mock.Mock()
        guard.healthy.side_effect = [True, True]
        version = {
            "text": (
                f"version: {runner.EXPECTED_VERSION} "
                f"build={runner.EXPECTED_BUILD}\n"
            )
        }
        selftest = {"text": "selftest: pass=11 warn=1 fail=0 duration=35ms entries=12\n"}
        with (
            mock.patch.object(runner.time, "monotonic", return_value=0.0),
            mock.patch.object(runner.time, "sleep") as sleep,
            mock.patch.object(
                runner.base.staging,
                "require_exact_bridge",
                side_effect=[bridge, bridge],
            ) as exact,
            mock.patch.object(
                runner.base,
                "_bound_bridge_serial_epoch",
                side_effect=[same_epoch, returned_epoch],
            ),
            mock.patch.object(
                runner.base.staging,
                "_usb_device_parent",
                return_value=Path("/sys/devices/2-2"),
            ),
            mock.patch.object(
                runner,
                "_usb_parent_snapshot",
                return_value={**binding["usb_identity"], "usb_devnum": 10},
            ),
            mock.patch.object(
                runner.base,
                "require_returned_modemmanager_guard",
                return_value={"guard": True},
            ) as returned_guard,
            mock.patch.object(
                runner.base,
                "run_f1_cmd",
                side_effect=[version, selftest],
            ) as command,
            mock.patch.object(
                runner.base,
                "settle_observation_channel",
                return_value={"settled": True},
            ),
        ):
            result = runner.wait_for_native_return_after_bound_ncm(
                spec,
                SimpleNamespace(),
                binding,
                ncm,
                guard,
            )
        self.assertTrue(result["native_epoch_version_proven"])
        self.assertEqual(result["return_epoch"]["returned"], returned_epoch)
        self.assertEqual(exact.call_count, 2)
        sleep.assert_called_once_with(runner.base.HOST_NCM_REBIND_POLL_SEC)
        self.assertEqual(
            returned_guard.call_args.args[1]["returned"],
            returned_epoch,
        )
        self.assertEqual(
            [call.args[1] for call in command.call_args_list],
            [["version"], ["selftest"]],
        )

    def test_intents_precede_one_arm_and_one_reboot(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        execute = source[source.index("def execute(") : source.index("def reconcile(")]
        arm_helper = source[
            source.index("def dispatch_arm_once_and_publish(")
            : source.index("def _continue_after_proved_arm(")
        ]
        reboot_helper = source[
            source.index("def _continue_after_proved_arm(")
            : source.index("def execute(")
        ]
        arm_intent = execute.index('"arm-intent"')
        arm_dispatch = execute.index("dispatch_arm_once_and_publish(")
        continuation = execute.index("_continue_after_proved_arm(")
        reboot_intent = reboot_helper.index('"reboot-intent"')
        reboot_dispatch = reboot_helper.index("send_reboot_once(args)")
        observation = reboot_helper.index(
            "observe_auto_cycle(spec, args, path, guard, pre_reboot_epoch)"
        )
        returned_status = reboot_helper.index(
            "returned_status_record, returned_status = require_auto_status("
        )
        absence_intent = reboot_helper.index('"absence-close-intent"')
        absence_check = reboot_helper.index("fast_resident_preflight(", absence_intent)
        self.assertLess(arm_intent, arm_dispatch)
        self.assertLess(arm_dispatch, continuation)
        self.assertLess(reboot_intent, reboot_dispatch)
        self.assertLess(reboot_dispatch, observation)
        self.assertLess(observation, returned_status)
        self.assertLess(returned_status, absence_intent)
        self.assertLess(absence_intent, absence_check)
        self.assertEqual(reboot_helper.count("send_reboot_once(args)"), 1)
        self.assertNotIn("dispatch_arm_once_and_publish", reboot_helper)
        self.assertNotIn("resident._cleanup_script", reboot_helper)
        self.assertNotIn("resident.resident_d0_preflight", reboot_helper)
        self.assertEqual(arm_helper.count("base.run_f1_cmd("), 1)
        self.assertIn("allow_error=True", arm_helper)
        self.assertLess(
            arm_helper.index('"arm-result"'),
            arm_helper.index("auto-handoff arm was explicitly refused with no effect"),
        )

    def test_armed_resume_uses_exact_prefix_without_rearming(self) -> None:
        intent_sha256 = "a" * 64
        records = [
            {"opening_preflight": {}, "first_boot_log": {}},
            {},
            {
                "arm_record": self._arm_receipt(intent_sha256, 0),
                "post_arm_status": {
                    "binding": 1,
                    "enable": 1,
                    "latch": 0,
                    "build": runner.EXPECTED_BUILD,
                },
            },
        ]
        identity = {
            "dev": 1,
            "ino": 2,
            "size": self._spec().rootfs.size,
            "mode": 33152,
            "uid": 0,
            "gid": 0,
            "nlink": 1,
            "mtime_sec": 3,
            "mtime_nsec": 4,
            "ctime_sec": 5,
            "ctime_nsec": 6,
        }
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            mock.patch.object(
                runner,
                "exact_transaction_dir",
                return_value=Path(temp_dir),
            ),
            mock.patch.object(runner, "load_journal_prefix", return_value=records),
            mock.patch.object(
                runner,
                "validate_preflight_evidence",
                return_value=identity,
            ),
            mock.patch.object(runner, "sha256_file", return_value=intent_sha256),
            mock.patch.object(runner, "_effect_args", return_value=SimpleNamespace()),
            mock.patch.object(
                runner,
                "_continue_after_proved_arm",
                return_value={"terminal": "continued"},
            ) as continuation,
            mock.patch.object(
                runner,
                "dispatch_arm_once_and_publish",
                side_effect=AssertionError("armed resume must never re-arm"),
            ),
        ):
            result = runner.resume_after_proved_arm(
                self._spec(),
                transaction_dir=Path(temp_dir),
                expected_closure_sha256="1" * 64,
                expected_journal_closure_sha256=(
                    runner.ARMED_RESUME_PREDECESSOR_CLOSURE_SHA256
                ),
                operator_attended=True,
                visible_confirmed="unavailable",
            )
        self.assertEqual(result, {"terminal": "continued"})
        continuation.assert_called_once()
        self.assertEqual(continuation.call_args.kwargs["intent_sha256"], intent_sha256)

    def test_armed_resume_rejects_other_predecessor_before_path_or_device(self) -> None:
        with (
            mock.patch.object(
                runner,
                "exact_transaction_dir",
                side_effect=AssertionError("mismatch must stop before path access"),
            ),
            mock.patch.object(
                runner,
                "_effect_args",
                side_effect=AssertionError("mismatch must stop before device access"),
            ),
            self.assertRaisesRegex(
                runner.ContractError,
                "predecessor closure is not exact",
            ),
        ):
            runner.resume_after_proved_arm(
                self._spec(),
                transaction_dir=Path("/not/reached"),
                expected_closure_sha256="1" * 64,
                expected_journal_closure_sha256="2" * 64,
                operator_attended=True,
                visible_confirmed="unavailable",
            )

    def test_armed_resume_source_contains_no_arm_dispatch(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        resume = source[
            source.index("def resume_after_proved_arm(")
            : source.index("def resume_after_return(")
        ]
        self.assertNotIn("dispatch_arm_once_and_publish", resume)
        self.assertNotIn("auto-handoff-arm", resume)
        self.assertIn("if len(records) != 3:", resume)
        self.assertIn("_continue_after_proved_arm(", resume)

    def test_proved_arm_continuation_rechecks_guard_and_status_before_reboot(
        self,
    ) -> None:
        preflight = SimpleNamespace(validate=lambda: None)
        for healthy, expected_intent_writes in (([False], 0), ([True, False], 1)):
            guard = mock.Mock()
            guard.healthy.side_effect = healthy
            with (
                self.subTest(healthy=healthy),
                tempfile.TemporaryDirectory() as temp_dir,
                mock.patch.object(runner, "require_execution_closure", return_value={}),
                mock.patch.object(runner, "require_auto_status") as status,
                mock.patch.object(
                    runner,
                    "fast_resident_preflight",
                    return_value=(preflight, {}, {}),
                ),
                mock.patch.object(runner, "_f1_spec", return_value=SimpleNamespace()),
                mock.patch.object(
                    runner.base,
                    "arm_candidate_return_modemmanager_guard",
                    return_value=guard,
                ),
                mock.patch.object(
                    runner,
                    "capture_pre_reboot_observer_binding",
                    return_value=self._pre_reboot_binding(),
                ),
                mock.patch.object(
                    runner,
                    "require_pre_reboot_observer_binding_current",
                ) as binding_current,
                mock.patch.object(runner, "write_record") as write,
                mock.patch.object(
                    runner.base,
                    "release_candidate_return_modemmanager_guard",
                ) as release,
                mock.patch.object(
                    runner,
                    "send_reboot_once",
                    side_effect=AssertionError("guard failure must stop before reboot"),
                ) as reboot,
                self.assertRaisesRegex(runner.ContractError, "guard was lost"),
            ):
                runner._continue_after_proved_arm(
                    self._spec(),
                    SimpleNamespace(),
                    Path(temp_dir),
                    expected_closure_sha256="1" * 64,
                    source_identity={"size": self._spec().rootfs.size},
                    intent_sha256="2" * 64,
                    opening_log_record={},
                    visible_confirmed="unavailable",
                )
            self.assertEqual(
                sum(
                    call.args[1] == "reboot-intent"
                    for call in write.call_args_list
                ),
                expected_intent_writes,
            )
            self.assertEqual(status.call_count, 2 + expected_intent_writes)
            self.assertEqual(guard.healthy.call_count, len(healthy))
            self.assertEqual(binding_current.call_count, expected_intent_writes)
            release.assert_called_once_with(guard, Path(temp_dir))
            reboot.assert_not_called()

    def test_exact_reboot_nondispatch_releases_guard_without_observation(self) -> None:
        guard = mock.Mock()
        guard.healthy.side_effect = [True, True]
        preflight = SimpleNamespace(validate=lambda: None)
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            mock.patch.object(runner, "require_execution_closure", return_value={}),
            mock.patch.object(runner, "require_auto_status") as status,
            mock.patch.object(
                runner,
                "fast_resident_preflight",
                return_value=(preflight, {}, {}),
            ),
            mock.patch.object(runner, "_f1_spec", return_value=SimpleNamespace()),
            mock.patch.object(
                runner.base,
                "arm_candidate_return_modemmanager_guard",
                return_value=guard,
            ),
            mock.patch.object(
                runner,
                "capture_pre_reboot_observer_binding",
                return_value=self._pre_reboot_binding(),
            ),
            mock.patch.object(
                runner,
                "require_pre_reboot_observer_binding_current",
            ) as binding_current,
            mock.patch.object(runner, "write_record"),
            mock.patch.object(
                runner.base,
                "release_candidate_return_modemmanager_guard",
            ) as release,
            mock.patch.object(
                runner,
                "send_reboot_once",
                side_effect=runner.ContractError("exact reboot non-dispatch"),
            ) as reboot,
            mock.patch.object(runner, "observe_auto_cycle") as observe,
            self.assertRaisesRegex(runner.ContractError, "exact reboot non-dispatch"),
        ):
            runner._continue_after_proved_arm(
                self._spec(),
                SimpleNamespace(),
                Path(temp_dir),
                expected_closure_sha256="1" * 64,
                source_identity={"size": self._spec().rootfs.size},
                intent_sha256="2" * 64,
                opening_log_record={},
                visible_confirmed="unavailable",
            )
        self.assertEqual(status.call_count, 3)
        self.assertEqual(guard.healthy.call_count, 2)
        self.assertEqual(binding_current.call_count, 2)
        reboot.assert_called_once()
        release.assert_called_once_with(guard, Path(temp_dir))
        observe.assert_not_called()

    def test_enospc_arm_refusal_is_published_before_stop(self) -> None:
        intent_sha256 = "a" * 64
        refusal = self._arm_receipt(intent_sha256, -28)
        status_record = self._status(0, 0)
        status = runner.parse_auto_status(status_record)
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / runner.JOURNAL_NAMES[2]
            with (
                mock.patch.object(runner.base, "run_f1_cmd", return_value=refusal) as arm,
                mock.patch.object(
                    runner,
                    "read_auto_status",
                    return_value=(status_record, status),
                ),
                self.assertRaisesRegex(runner.ContractError, "explicitly refused"),
            ):
                runner.dispatch_arm_once_and_publish(
                    SimpleNamespace(),
                    journal_path=journal_path,
                    intent_sha256=intent_sha256,
                )
            arm.assert_called_once_with(
                mock.ANY,
                ["auto-handoff-arm", runner.ARM_TOKEN, intent_sha256],
                allow_error=True,
            )
            published = json.loads(journal_path.read_text(encoding="utf-8"))
        self.assertEqual(published["action"], "arm-result")
        self.assertEqual(published["arm_dispatch_count"], 1)
        self.assertEqual(published["arm_record"]["rc"], -28)
        self.assertEqual(published["post_arm_status"], status)

    def test_unproved_arm_never_advances_from_armed_status(self) -> None:
        intent_sha256 = "d" * 64
        status_record = self._status(1, 0)
        status = runner.parse_auto_status(status_record)
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / runner.JOURNAL_NAMES[2]
            with (
                mock.patch.object(
                    runner.base,
                    "run_f1_cmd",
                    side_effect=RuntimeError("response lost"),
                ),
                mock.patch.object(
                    runner,
                    "read_auto_status",
                    return_value=(status_record, status),
                ),
                self.assertRaisesRegex(runner.ContractError, "outcome is unproved"),
            ):
                runner.dispatch_arm_once_and_publish(
                    SimpleNamespace(),
                    journal_path=journal_path,
                    intent_sha256=intent_sha256,
                )
            published = json.loads(journal_path.read_text(encoding="utf-8"))
        self.assertFalse(published["arm_record"]["response_proof"])
        self.assertEqual(published["post_arm_status"], status)

    def test_reconcile_classifies_published_refusal_as_exact_no_effect(self) -> None:
        intent_sha256 = "b" * 64
        status_record = self._status(0, 0)
        status = runner.parse_auto_status(status_record)
        records = [
            {},
            {},
            {
                "intent_sha256": intent_sha256,
                "arm_record": self._arm_receipt(intent_sha256, -28),
                "post_arm_status": status,
            },
        ]
        preflight = SimpleNamespace(validate=lambda: None)
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            mock.patch.object(runner, "require_execution_closure", return_value={}),
            mock.patch.object(runner, "exact_transaction_dir", return_value=Path(temp_dir)),
            mock.patch.object(runner, "load_journal_prefix", return_value=records),
            mock.patch.object(runner.base, "run_f1_cmd", return_value=status_record),
            mock.patch.object(
                runner.base,
                "require_exact_f1_command_receipt",
                side_effect=lambda value, *_: value,
            ),
            mock.patch.object(
                runner.resident,
                "verify_resident_health_exact",
                return_value={},
            ),
        ):
            result = runner.reconcile(
                self._spec(),
                transaction_dir=Path(temp_dir),
                expected_closure_sha256="0" * 64,
            )
        self.assertEqual(result["terminal"], "ARM_REFUSED_EXACT_NO_EFFECT_NO_REPLAY")
        self.assertEqual(result["arm_dispatch_count"], 1)
        self.assertEqual(result["reboot_dispatch_count"], 0)
        self.assertFalse(result["device_effect"])

    def test_reconciliation_is_read_only_and_no_replay(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        reconcile = source[source.index("def reconcile(") : source.index("def build_parser(")]
        self.assertNotIn("send_reboot_once", reconcile)
        self.assertNotIn("auto-handoff-arm", reconcile)
        self.assertNotIn("run_f1_shell", reconcile)
        self.assertIn('"device_effect": False', reconcile)
        self.assertIn('"candidate_replay": False', reconcile)

    def test_reconcile_forwards_historical_opening_closure(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            mock.patch.object(runner, "require_execution_closure", return_value={}),
            mock.patch.object(
                runner,
                "exact_transaction_dir",
                return_value=Path(temp_dir),
            ),
            mock.patch.object(runner, "load_journal_prefix", return_value=[]) as load,
        ):
            result = runner.reconcile(
                self._spec(),
                transaction_dir=Path(temp_dir),
                expected_closure_sha256="1" * 64,
                expected_journal_closure_sha256="2" * 64,
            )
        self.assertEqual(result["terminal"], "NO_DURABLE_EFFECT_EVIDENCE")
        self.assertEqual(
            load.call_args.kwargs["journal_closure_sha256"],
            "2" * 64,
        )

    def test_reconcile_empty_journal_never_claims_returned(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            with (
                mock.patch.object(runner, "require_execution_closure", return_value={}),
                mock.patch.object(runner, "exact_transaction_dir", return_value=path),
                mock.patch.object(
                    runner.base,
                    "run_f1_cmd",
                    side_effect=AssertionError("empty journal must not contact device"),
                ),
            ):
                result = runner.reconcile(
                    SimpleNamespace(),
                    transaction_dir=path,
                    expected_closure_sha256="0" * 64,
                )
        self.assertEqual(result["terminal"], "NO_DURABLE_EFFECT_EVIDENCE")
        self.assertFalse(result["device_effect"])

    def test_reconcile_forged_actions_stop_before_device_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            for index, name in enumerate(runner.JOURNAL_NAMES[:5]):
                (path / name).write_text(
                    json.dumps(
                        {
                            "schema": runner.JOURNAL_SCHEMA,
                            "action": "FORGED_WRONG_ACTION",
                            "timestamp_utc": "2026-08-05T00:00:00Z",
                            **{key: None for key in runner.PAYLOAD_KEYS[index]},
                        }
                    ),
                    encoding="utf-8",
                )
            with (
                mock.patch.object(runner, "require_execution_closure", return_value={}),
                mock.patch.object(runner, "exact_transaction_dir", return_value=path),
                mock.patch.object(
                    runner.base,
                    "run_f1_cmd",
                    side_effect=AssertionError("forged journal must not contact device"),
                ),
            ):
                result = runner.reconcile(
                    SimpleNamespace(),
                    transaction_dir=path,
                    expected_closure_sha256="0" * 64,
                )
        self.assertEqual(result["terminal"], "JOURNAL_INCONSISTENT_STOP")
        self.assertIn("shape/action", result["journal_error"]["message"])

    def test_resume_only_allows_post_observation_finalization(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        resume = source[
            source.index("def resume_after_return(") : source.index("def reconcile(")
        ]
        self.assertNotIn("auto-handoff-arm", resume)
        self.assertNotIn("send_reboot_once", resume)
        self.assertIn('if len(records) < 5:', resume)
        self.assertIn('path / JOURNAL_NAMES[5]', resume)
        self.assertIn('path / JOURNAL_NAMES[7]', resume)
        self.assertIn('path / JOURNAL_NAMES[8]', resume)

    def test_historical_closure_tail_repair_rejects_pre_absence_prefix(self) -> None:
        records6 = [{}, {}, {}, {}, {}, {}]
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            mock.patch.object(
                runner,
                "exact_transaction_dir",
                return_value=Path(temp_dir),
            ),
            mock.patch.object(
                runner,
                "load_journal_prefix",
                return_value=records6,
            ),
            mock.patch.object(
                runner,
                "_effect_args",
                side_effect=AssertionError("tail repair must stop before device access"),
            ),
            self.assertRaisesRegex(
                runner.ContractError,
                "exact post-absence prefix",
            ),
        ):
            runner.resume_after_return(
                self._spec(),
                transaction_dir=Path(temp_dir),
                expected_closure_sha256="1" * 64,
                expected_journal_closure_sha256="2" * 64,
                operator_attended=True,
                visible_confirmed="yes",
            )

    def test_armed_successor_historical_tail_accepts_prefixes_five_through_nine(
        self,
    ) -> None:
        for count in range(5, 10):
            records = [{} for _ in range(count)]
            records[0] = {"first_boot_log": {}, "opening_preflight": {}}
            records[4] = {"observation": {}, "intent_sha256": "6" * 64}
            if count >= 8:
                records[7] = {"result": {}, "result_sha256": "7" * 64}
            if count == 9:
                records[8] = {"result": {}, "result_sha256": "7" * 64}
            with self.subTest(count=count), tempfile.TemporaryDirectory() as temp_dir:
                patches = (
                    mock.patch.object(
                        runner,
                        "exact_transaction_dir",
                        return_value=Path(temp_dir),
                    ),
                    mock.patch.object(
                        runner,
                        "load_journal_prefix",
                        return_value=records,
                    ),
                    mock.patch.object(runner, "validate_result", return_value={}),
                    mock.patch.object(runner, "write_record"),
                )
                with patches[0], patches[1], patches[2], patches[3]:
                    if count <= 7:
                        with mock.patch.object(
                            runner,
                            "_effect_args",
                            side_effect=RuntimeError("TAIL_REACHED"),
                        ), self.assertRaisesRegex(RuntimeError, "TAIL_REACHED"):
                            runner.resume_after_return(
                                self._spec(),
                                transaction_dir=Path(temp_dir),
                                expected_closure_sha256="2" * 64,
                                expected_journal_closure_sha256=(
                                    runner.ARMED_RESUME_PREDECESSOR_CLOSURE_SHA256
                                ),
                                operator_attended=True,
                                visible_confirmed="unavailable",
                            )
                    else:
                        result = runner.resume_after_return(
                            self._spec(),
                            transaction_dir=Path(temp_dir),
                            expected_closure_sha256="2" * 64,
                            expected_journal_closure_sha256=(
                                runner.ARMED_RESUME_PREDECESSOR_CLOSURE_SHA256
                            ),
                            operator_attended=True,
                            visible_confirmed="unavailable",
                        )
                        self.assertEqual(result, {})

    def test_historical_closure_tail_repair_never_repeats_absence_close(self) -> None:
        observation = {"reboot_record": {"command": ["reboot"], "dispatch_count": 1}}
        cleanup = {
            "cleanup_dispatch_count": 0,
            "inferred_from_absence": True,
            "cleanup_record": None,
            "absence_preflight": {},
        }
        records7 = [
            {"first_boot_log": {}, "opening_preflight": {}}, {}, {}, {},
            {"observation": observation, "intent_sha256": "6" * 64},
            {},
            cleanup,
        ]
        records8 = [*records7, {"result": {}, "result_sha256": "7" * 64}]
        records9 = [*records8, {"result": {}, "result_sha256": "7" * 64}]
        writes: list[str] = []
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            mock.patch.object(
                runner,
                "exact_transaction_dir",
                return_value=Path(temp_dir),
            ),
            mock.patch.object(
                runner,
                "load_journal_prefix",
                side_effect=[records7, records7, records8, records9],
            ) as load,
            mock.patch.object(runner, "_effect_args", return_value=SimpleNamespace()),
            mock.patch.object(runner, "validate_preflight_evidence", return_value={}),
            mock.patch.object(runner, "finalize_cycle", return_value={}),
            mock.patch.object(runner, "validate_result", return_value={}),
            mock.patch.object(runner.base, "json_sha256", return_value="7" * 64),
            mock.patch.object(
                runner,
                "write_record",
                side_effect=lambda _path, action, _payload: writes.append(action),
            ),
            mock.patch.object(
                runner.base,
                "run_f1_shell",
                side_effect=AssertionError("absence close must never dispatch cleanup"),
            ),
        ):
            result = runner.resume_after_return(
                self._spec(),
                transaction_dir=Path(temp_dir),
                expected_closure_sha256="1" * 64,
                expected_journal_closure_sha256="2" * 64,
                operator_attended=True,
                visible_confirmed="yes",
            )
        self.assertEqual(result, {})
        self.assertEqual(writes, ["final-health", "closed"])
        self.assertTrue(
            all(
                call.kwargs.get("journal_closure_sha256") == "2" * 64
                for call in load.call_args_list
            )
        )

    def test_journal_payload_cannot_replace_schema_or_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(runner.ContractError, "common keys"):
                runner.write_record(
                    Path(temp_dir) / "bad.json",
                    "closed",
                    {"schema": "forged"},
                )

    def test_every_semantic_journal_prefix_is_validated_in_order(self) -> None:
        closure = {"sha256": "0" * 64, "files": {}}
        spec = self._spec()
        for count in range(1, len(runner.JOURNAL_NAMES) + 1):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir)
                self._write_semantic_prefix(path, count, closure)
                with (
                    mock.patch.object(runner, "require_execution_closure", return_value=closure),
                    mock.patch.object(runner, "validate_preflight_evidence", return_value={}),
                    mock.patch.object(runner.base, "require_exact_f1_command_receipt", side_effect=lambda value, *_: value),
                    mock.patch.object(runner, "require_first_boot_unarmed"),
                    mock.patch.object(runner.resident, "require_exact_cleanup_receipt"),
                    mock.patch.object(runner, "validate_result", return_value={}),
                    mock.patch.object(runner.base, "json_sha256", return_value="5" * 64),
                ):
                    records = runner.load_journal_prefix(spec, path, "0" * 64)
                self.assertEqual(len(records), count)

    def test_historical_closure_loads_armed_reboot_intent_and_closed_prefixes(self) -> None:
        closure = {"sha256": "1" * 64, "files": {}}
        spec = self._spec()
        for count in (3, 4, 9):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir)
                self._write_semantic_prefix(
                    path,
                    count,
                    closure,
                    intent_closure_sha256="1" * 64,
                    reboot_closure_sha256="2" * 64,
                )
                with (
                    mock.patch.object(
                        runner,
                        "require_execution_closure",
                        return_value={"sha256": "2" * 64, "files": {}},
                    ),
                    mock.patch.object(
                        runner,
                        "validate_recorded_execution_closure",
                        return_value=closure,
                    ) as historical,
                    mock.patch.object(
                        runner,
                        "validate_preflight_evidence",
                        return_value={},
                    ),
                    mock.patch.object(
                        runner.base,
                        "require_exact_f1_command_receipt",
                        side_effect=lambda value, *_: value,
                    ),
                    mock.patch.object(runner, "require_first_boot_unarmed"),
                    mock.patch.object(runner, "validate_result", return_value={}),
                    mock.patch.object(
                        runner.base,
                        "json_sha256",
                        return_value="5" * 64,
                    ),
                ):
                    records = runner.load_journal_prefix(
                        spec,
                        path,
                        "2" * 64,
                        journal_closure_sha256="1" * 64,
                    )
                self.assertEqual(len(records), count)
                historical.assert_called_once_with(closure, "1" * 64)

    def test_historical_parser_tail_keeps_recorded_reboot_closure(self) -> None:
        closure = {"sha256": "1" * 64, "files": {}}
        spec = self._spec()
        for count in (7, 8, 9):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir)
                self._write_semantic_prefix(
                    path,
                    count,
                    closure,
                    intent_closure_sha256="1" * 64,
                    reboot_closure_sha256="1" * 64,
                )
                with (
                    mock.patch.object(
                        runner,
                        "require_execution_closure",
                        return_value={"sha256": "2" * 64, "files": {}},
                    ),
                    mock.patch.object(
                        runner,
                        "validate_recorded_execution_closure",
                        return_value=closure,
                    ),
                    mock.patch.object(
                        runner,
                        "validate_preflight_evidence",
                        return_value={},
                    ),
                    mock.patch.object(
                        runner.base,
                        "require_exact_f1_command_receipt",
                        side_effect=lambda value, *_: value,
                    ),
                    mock.patch.object(runner, "require_first_boot_unarmed"),
                    mock.patch.object(runner, "validate_result", return_value={}),
                    mock.patch.object(
                        runner.base,
                        "json_sha256",
                        return_value="5" * 64,
                    ),
                ):
                    records = runner.load_journal_prefix(
                        spec,
                        path,
                        "2" * 64,
                        journal_closure_sha256="1" * 64,
                    )
                self.assertEqual(len(records), count)

    def test_historical_parser_tail_rejects_old_reboot_before_post_absence(self) -> None:
        closure = {"sha256": "1" * 64, "files": {}}
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            self._write_semantic_prefix(
                path,
                6,
                closure,
                intent_closure_sha256="1" * 64,
                reboot_closure_sha256="1" * 64,
            )
            with (
                mock.patch.object(
                    runner,
                    "require_execution_closure",
                    return_value={"sha256": "2" * 64, "files": {}},
                ),
                mock.patch.object(
                    runner,
                    "validate_recorded_execution_closure",
                    return_value=closure,
                ),
                mock.patch.object(
                    runner,
                    "validate_preflight_evidence",
                    return_value={},
                ),
                mock.patch.object(
                    runner.base,
                    "require_exact_f1_command_receipt",
                    side_effect=lambda value, *_: value,
                ),
                mock.patch.object(runner, "require_first_boot_unarmed"),
                self.assertRaisesRegex(
                    runner.ContractError,
                    "reboot intent binding changed",
                ),
            ):
                runner.load_journal_prefix(
                    self._spec(),
                    path,
                    "2" * 64,
                    journal_closure_sha256="1" * 64,
                )

    def test_exact_h10_terminal_closure_alone_accepts_legacy_serial_epoch(self) -> None:
        closure = {"sha256": "1" * 64, "files": {}}
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            self._write_semantic_prefix(
                path,
                4,
                closure,
                intent_closure_sha256="1" * 64,
                reboot_closure_sha256=(
                    runner.HISTORICAL_H10_TERMINAL_CLOSURE_SHA256
                ),
            )
            reboot_path = path / runner.JOURNAL_NAMES[3]
            reboot = json.loads(reboot_path.read_text(encoding="utf-8"))
            reboot["pre_reboot_epoch"] = self._pre_reboot_binding()["serial_epoch"]
            reboot_path.write_text(json.dumps(reboot), encoding="utf-8")
            with (
                mock.patch.object(
                    runner,
                    "require_execution_closure",
                    return_value={
                        "sha256": runner.HISTORICAL_H10_TERMINAL_CLOSURE_SHA256,
                        "files": {},
                    },
                ),
                mock.patch.object(
                    runner,
                    "validate_recorded_execution_closure",
                    return_value=closure,
                ),
                mock.patch.object(
                    runner,
                    "validate_preflight_evidence",
                    return_value={},
                ),
                mock.patch.object(
                    runner.base,
                    "require_exact_f1_command_receipt",
                    side_effect=lambda value, *_: value,
                ),
                mock.patch.object(runner, "require_first_boot_unarmed"),
            ):
                records = runner.load_journal_prefix(
                    self._spec(),
                    path,
                    runner.HISTORICAL_H10_TERMINAL_CLOSURE_SHA256,
                    journal_closure_sha256="1" * 64,
                )
        self.assertEqual(len(records), 4)

    def test_journal_dispatch_counts_reject_booleans(self) -> None:
        cases = (
            (1, ("arm_dispatch_count_max",), True),
            (1, ("reboot_dispatch_count",), False),
            (2, ("arm_dispatch_count",), True),
            (3, ("reboot_dispatch_count_max",), True),
            (4, ("arm_dispatch_count",), True),
            (4, ("reboot_dispatch_count",), True),
            (4, ("observation", "reboot_record", "dispatch_count"), True),
            (5, ("cleanup_dispatch_count_max",), False),
            (5, ("arm_dispatch_count",), True),
            (5, ("reboot_dispatch_count",), True),
            (6, ("cleanup_dispatch_count",), False),
        )
        closure = {"sha256": "0" * 64, "files": {}}
        for index, keys, value in cases:
            with self.subTest(index=index, keys=keys), tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir)
                self._write_semantic_prefix(path, index + 1, closure)
                record_path = path / runner.JOURNAL_NAMES[index]
                record = json.loads(record_path.read_text(encoding="utf-8"))
                selected = record
                for key in keys[:-1]:
                    selected = selected[key]
                selected[keys[-1]] = value
                record_path.write_text(
                    json.dumps(record, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with (
                    mock.patch.object(
                        runner,
                        "require_execution_closure",
                        return_value=closure,
                    ),
                    mock.patch.object(
                        runner,
                        "validate_preflight_evidence",
                        return_value={},
                    ),
                    mock.patch.object(
                        runner.base,
                        "require_exact_f1_command_receipt",
                        side_effect=lambda item, *_: item,
                    ),
                    mock.patch.object(runner, "require_first_boot_unarmed"),
                    self.assertRaises(runner.ContractError),
                ):
                    runner.load_journal_prefix(
                        spec=self._spec(),
                        path=path,
                        expected_closure_sha256="0" * 64,
                    )

    def test_zero_dispatch_absence_intent_resumes_with_read_only_check(self) -> None:
        spec = self._spec()
        observation = {"reboot_record": {"command": ["reboot"], "dispatch_count": 1}}
        records6 = [
            {"first_boot_log": {}, "opening_preflight": {}},
            {},
            {},
            {},
            {"observation": observation, "intent_sha256": "6" * 64},
            {},
        ]
        cleanup = {
            "cleanup_dispatch_count": 0,
            "inferred_from_absence": True,
            "cleanup_record": None,
            "absence_preflight": {},
        }
        records7 = [*records6, cleanup]
        records8 = [*records7, {"result": {}, "result_sha256": "7" * 64}]
        records9 = [*records8, {"result": {}, "result_sha256": "7" * 64}]
        preflight = SimpleNamespace(validate=lambda: None)
        writes: list[str] = []
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            mock.patch.object(runner, "exact_transaction_dir", return_value=Path(temp_dir)),
            mock.patch.object(
                runner,
                "load_journal_prefix",
                side_effect=[records6, records7, records8, records9],
            ),
            mock.patch.object(
                runner,
                "require_auto_status",
                return_value=(self._status(1, 1), runner.parse_auto_status(self._status(1, 1))),
            ),
            mock.patch.object(
                runner,
                "fast_resident_preflight",
                return_value=(preflight, {}, {}),
            ),
            mock.patch.object(runner, "validate_preflight_evidence", return_value={}),
            mock.patch.object(
                runner.base,
                "run_f1_shell",
                side_effect=AssertionError("absence close must not dispatch cleanup"),
            ),
            mock.patch.object(runner, "finalize_cycle", return_value={}),
            mock.patch.object(runner, "validate_result", return_value={}),
            mock.patch.object(runner.base, "json_sha256", return_value="7" * 64),
            mock.patch.object(
                runner,
                "write_record",
                side_effect=lambda _path, action, _payload: writes.append(action),
            ),
        ):
            result = runner.resume_after_return(
                spec,
                transaction_dir=Path(temp_dir),
                expected_closure_sha256="0" * 64,
                operator_attended=True,
                visible_confirmed="unavailable",
            )
        self.assertEqual(result, {})
        self.assertEqual(writes, ["absence-close-result", "final-health", "closed"])

    def test_result_publication_only_resume_never_contacts_device(self) -> None:
        spec = self._spec()
        result = {"terminal": "PASS_AUTO_HANDOFF_BENCHMARK_VISIBLE"}
        records8 = [
            {"first_boot_log": {}}, {}, {}, {},
            {"observation": {}, "intent_sha256": "6" * 64},
            {}, {},
            {"result": result, "result_sha256": "7" * 64},
        ]
        records9 = [
            *records8,
            {"result": result, "result_sha256": "7" * 64},
        ]
        writes: list[str] = []
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            mock.patch.object(runner, "exact_transaction_dir", return_value=Path(temp_dir)),
            mock.patch.object(
                runner,
                "load_journal_prefix",
                side_effect=[records8, records9],
            ),
            mock.patch.object(runner, "validate_result", return_value=result),
            mock.patch.object(
                runner,
                "write_record",
                side_effect=lambda _path, action, _payload: writes.append(action),
            ),
            mock.patch.object(
                runner,
                "_effect_args",
                side_effect=AssertionError("publication repair must stay host-only"),
            ),
            mock.patch.object(
                runner,
                "require_auto_status",
                side_effect=AssertionError("publication repair must not read status"),
            ),
            mock.patch.object(
                runner.resident,
                "resident_d0_preflight",
                side_effect=AssertionError("publication repair must not read health"),
            ),
            mock.patch.object(
                runner.base,
                "run_f1_shell",
                side_effect=AssertionError("publication repair must not dispatch cleanup"),
            ),
        ):
            actual = runner.resume_after_return(
                spec,
                transaction_dir=Path(temp_dir),
                expected_closure_sha256="0" * 64,
                operator_attended=True,
                visible_confirmed="unavailable",
            )
        self.assertEqual(actual, result)
        self.assertEqual(writes, ["closed"])


if __name__ == "__main__":
    unittest.main()
