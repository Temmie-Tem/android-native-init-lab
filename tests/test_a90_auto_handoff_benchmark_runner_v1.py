"""Static and pure tests for the A90 H4 automatic benchmark runner."""

from __future__ import annotations

import json
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
            "drm_master=1 dropbear=1 display_ready=1 display_failure=0"
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
            f"A90AUTO_ARM armed=1 intent_sha256={intent_sha256}"
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
    def _spec() -> SimpleNamespace:
        return SimpleNamespace(
            manifest_sha256="1" * 64,
            candidate=SimpleNamespace(sha256="2" * 64),
            rollback=SimpleNamespace(sha256="3" * 64),
            rootfs=SimpleNamespace(sha256="4" * 64),
            recovery_profile="A90_ATTENDED_PHYSICAL_RECOVERY_V1",
            bridge_device="/dev/a90-test",
            bridge_realpath="/dev/ttyACM-test",
            observer_host_ncm_profile="a90-test-ncm",
            candidate_version=runner.EXPECTED_VERSION,
            candidate_build=runner.EXPECTED_BUILD,
        )

    @classmethod
    def _host_link(cls) -> dict:
        spec = cls._spec()
        return {
            "bridge_reenumeration": {
                "ok": True,
                "selected_device": spec.bridge_device,
                "selected_realpath": spec.bridge_realpath,
                "metadata": {"effective_expect_realpath": spec.bridge_realpath},
                "bridge_process": "running",
                "port_listening": True,
            },
            "host_ncm_rebind": {
                "same_current_acm_usb_parent": True,
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
        }

    def _write_semantic_prefix(
        self,
        path: Path,
        count: int,
        closure: dict,
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
                    "execution_closure_sha256": "0" * 64,
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
                "arm_record": {"error": {}, "response_proof": False},
                "post_arm_status_record": self._status(1, 0),
                "post_arm_status": runner.parse_auto_status(self._status(1, 0)),
            },
            {
                "intent_sha256": intent_sha256,
                "armed_preflight": {},
                "pre_reboot_epoch": {},
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
                "cleanup_dispatch_count_max": 1,
                "arm_dispatch_count": 1,
                "reboot_dispatch_count": 1,
                "candidate_replay": False,
                "returned_status": runner.parse_auto_status(self._status(1, 1)),
                "returned_status_record": self._status(1, 1),
            },
            {
                "intent_sha256": intent_sha256,
                "cleanup_dispatch_count": 1,
                "cleanup_record": {},
                "absence_preflight": None,
                "inferred_from_absence": False,
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

    def test_durable_same_ordinal_evidence_drives_terminal_without_live_ssh(self) -> None:
        intent_sha256 = "a" * 64
        opening = self._complete_benchmark_segment(1_000)
        current = self._complete_benchmark_segment(100)
        durable = "\n".join(
            (
                self._ondevice_record("debian_pid1", 1_000, intent_sha256),
                self._ondevice_record("debian_sshd", 2_000, intent_sha256),
                self._ondevice_record("debian_drm_master", 3_000, intent_sha256),
            )
        )
        log_record = {"command": ["logcat"], "text": "\n".join((opening, current, durable))}
        status_record = self._status(1, 1)
        preflight = SimpleNamespace(validate=lambda: None)
        observation = {
            "proof": False,
            "observer_error": {"type": "RuntimeError", "message": "live SSH missed"},
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
                runner.resident,
                "resident_d0_preflight",
                return_value=(preflight, {"resident_healthy": True}),
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
            )

        self.assertEqual(result["terminal"], "PASS_AUTO_HANDOFF_BENCHMARK_VISIBLE")
        self.assertTrue(result["ondevice_evidence"]["proof"])
        self.assertNotIn("candidate_return", observation)

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
                runner.resident,
                "resident_d0_preflight",
                return_value=(preflight, {"resident_healthy": True}),
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
                runner.resident,
                "resident_d0_preflight",
                return_value=(preflight, {}),
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
            )
            result["ondevice_evidence"] = dict(result["ondevice_evidence"])
            result["ondevice_evidence"]["proof"] = False
            with self.assertRaisesRegex(runner.ContractError, "durable evidence changed"):
                runner.validate_result(self._spec(), result, intent_sha256)

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
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            mock.patch.object(runner, "_f1_spec", return_value=SimpleNamespace()),
            mock.patch.object(
                runner,
                "wait_for_bound_bridge_after_reboot",
                side_effect=lambda *_a: order.append("bridge") or {"ok": True},
            ),
            mock.patch.object(
                runner.base,
                "rebind_host_ncm_after_reenumeration",
                side_effect=lambda *_a: order.append("ncm") or {"ready": True},
            ),
            mock.patch.object(
                runner.base,
                "observe_ssh",
                side_effect=lambda *_a: order.append("ssh") or {"proof": True},
            ),
            mock.patch.object(
                runner.base,
                "capture_bridge_serial_epoch",
                side_effect=lambda *_a: order.append("epoch") or {"epoch": 1},
            ),
            mock.patch.object(
                runner.phase3_observer,
                "observe_phase3_service",
                side_effect=lambda *_a: order.append("service") or {"proof": True},
            ),
            mock.patch.object(
                runner.base,
                "wait_for_candidate_return_attended_once",
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
            )
        self.assertEqual(order[:3], ["bridge", "ncm", "ssh"])
        self.assertEqual(result["bridge_reenumeration"], {"ok": True})
        self.assertEqual(result["host_ncm_rebind"], {"ready": True})

    def test_post_reboot_bridge_wait_accepts_only_temporary_bound_absence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            device = Path(temp_dir) / "a90-by-id"
            f1_spec = SimpleNamespace(
                stage=SimpleNamespace(bridge_device=str(device)),
            )
            expected = {
                "selected_realpath": "/dev/ttyACM-test",
                "serial_candidates": [
                    {"path": str(device), "exists": True},
                ],
            }
            with (
                mock.patch.object(
                    runner.base.staging,
                    "require_exact_bridge",
                    return_value=expected,
                ) as exact,
                mock.patch.object(
                    runner.time,
                    "sleep",
                    side_effect=lambda _seconds: device.write_bytes(b"returned"),
                ) as sleep,
            ):
                result = runner.wait_for_bound_bridge_after_reboot(
                    f1_spec,
                    SimpleNamespace(),
            )
            self.assertEqual(result, expected)
            exact.assert_called_once()
            sleep.assert_called_once_with(runner.base.HOST_NCM_REBIND_POLL_SEC)

    def test_post_reboot_bridge_wait_observes_disconnect_before_return(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            device = Path(temp_dir) / "a90-by-id"
            device.write_bytes(b"present")
            f1_spec = SimpleNamespace(
                stage=SimpleNamespace(bridge_device=str(device)),
            )
            expected = {
                "selected_realpath": "/dev/ttyACM-test",
                "serial_candidates": [
                    {"path": str(device), "exists": True},
                ],
            }
            sleeps = 0

            def transition(_seconds: float) -> None:
                nonlocal sleeps
                sleeps += 1
                if sleeps == 1:
                    device.unlink()
                elif sleeps == 2:
                    device.write_bytes(b"returned")

            with (
                mock.patch.object(
                    runner.base.staging,
                    "require_exact_bridge",
                    return_value=expected,
                ) as exact,
                mock.patch.object(runner.time, "sleep", side_effect=transition) as sleep,
            ):
                result = runner.wait_for_bound_bridge_after_reboot(
                    f1_spec,
                    SimpleNamespace(),
                )
            self.assertEqual(result, expected)
            exact.assert_called_once()
            self.assertEqual(sleep.call_count, 2)

    def test_post_reboot_bridge_wait_retries_absent_preflight_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            device = Path(temp_dir) / "a90-by-id"
            f1_spec = SimpleNamespace(
                stage=SimpleNamespace(bridge_device=str(device)),
            )
            stale = {
                "selected_realpath": "/dev/ttyACM-test",
                "serial_candidates": [
                    {"path": str(device), "exists": False},
                ],
            }
            expected = {
                "selected_realpath": "/dev/ttyACM-test",
                "serial_candidates": [
                    {"path": str(device), "exists": True},
                ],
            }
            with (
                mock.patch.object(
                    runner.base.staging,
                    "require_exact_bridge",
                    side_effect=[stale, expected],
                ) as exact,
                mock.patch.object(
                    runner.time,
                    "sleep",
                    side_effect=lambda _seconds: device.write_bytes(b"returned"),
                ) as sleep,
            ):
                result = runner.wait_for_bound_bridge_after_reboot(
                    f1_spec,
                    SimpleNamespace(),
                )
            self.assertEqual(result, expected)
            self.assertEqual(exact.call_count, 2)
            self.assertEqual(sleep.call_count, 2)

    def test_post_reboot_bridge_wait_rejects_returned_mismatch_without_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            device = Path(temp_dir) / "a90-by-id"
            f1_spec = SimpleNamespace(
                stage=SimpleNamespace(bridge_device=str(device)),
            )
            with (
                mock.patch.object(
                    runner.base.staging,
                    "require_exact_bridge",
                    side_effect=runner.base.staging.ContractError("wrong realpath"),
                ) as exact,
                mock.patch.object(
                    runner.time,
                    "sleep",
                    side_effect=lambda _seconds: device.write_bytes(b"returned"),
                ) as sleep,
                self.assertRaisesRegex(
                    runner.ContractError,
                    "present but exact post-reboot continuity failed",
                ),
            ):
                runner.wait_for_bound_bridge_after_reboot(
                    f1_spec,
                    SimpleNamespace(),
                )
            exact.assert_called_once()
            sleep.assert_called_once_with(runner.base.HOST_NCM_REBIND_POLL_SEC)

    def test_intents_precede_one_arm_and_one_reboot(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        execute = source[source.index("def execute(") : source.index("def reconcile(")]
        arm_helper = source[
            source.index("def dispatch_arm_once_and_publish(") : source.index("def execute(")
        ]
        arm_intent = execute.index('"arm-intent"')
        arm_dispatch = execute.index("dispatch_arm_once_and_publish(")
        reboot_intent = execute.index('"reboot-intent"')
        reboot_dispatch = execute.index("send_reboot_once(args)")
        observation = execute.index("observe_auto_cycle(spec, args, path, guard)")
        returned_status = execute.index(
            "returned_status_record, returned_status = require_auto_status("
        )
        cleanup_intent = execute.index('"cleanup-intent"')
        cleanup_dispatch = execute.index("base.run_f1_shell")
        self.assertLess(arm_intent, arm_dispatch)
        self.assertLess(arm_dispatch, reboot_intent)
        self.assertLess(reboot_intent, reboot_dispatch)
        self.assertLess(reboot_dispatch, observation)
        self.assertLess(observation, returned_status)
        self.assertLess(returned_status, cleanup_intent)
        self.assertLess(cleanup_intent, cleanup_dispatch)
        self.assertEqual(execute.count("send_reboot_once(args)"), 1)
        self.assertEqual(arm_helper.count("base.run_f1_cmd("), 1)
        self.assertIn("allow_error=True", arm_helper)
        self.assertLess(
            arm_helper.index('"arm-result"'),
            arm_helper.index("auto-handoff arm was explicitly refused with no effect"),
        )

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
                "resident_d0_preflight",
                return_value=(preflight, {}),
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

    def test_historical_closure_tail_repair_rejects_pre_cleanup_prefix(self) -> None:
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
                "exact post-cleanup prefix",
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

    def test_historical_closure_tail_repair_never_repeats_cleanup(self) -> None:
        observation = {"reboot_record": {"command": ["reboot"], "dispatch_count": 1}}
        cleanup = {
            "cleanup_dispatch_count": 1,
            "inferred_from_absence": False,
            "cleanup_record": {},
            "absence_preflight": None,
        }
        records7 = [
            {"first_boot_log": {}}, {}, {}, {},
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
                side_effect=AssertionError("completed cleanup must never replay"),
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

    def test_uncertain_cleanup_intent_is_never_replayed_by_resume(self) -> None:
        spec = self._spec()
        observation = {"reboot_record": {"command": ["reboot"], "dispatch_count": 1}}
        records6 = [
            {"first_boot_log": {}},
            {},
            {},
            {},
            {"observation": observation, "intent_sha256": "6" * 64},
            {},
        ]
        cleanup = {
            "cleanup_dispatch_count": None,
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
                runner.resident,
                "resident_d0_preflight",
                return_value=(preflight, {}),
            ),
            mock.patch.object(
                runner.base,
                "run_f1_shell",
                side_effect=AssertionError("uncertain cleanup must not replay"),
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
        self.assertEqual(writes, ["cleanup-result", "final-health", "closed"])

    def test_result_publication_only_resume_never_contacts_device(self) -> None:
        spec = self._spec()
        result = {"terminal": "PASS_AUTO_HANDOFF_BENCHMARK_VISIBLE"}
        records8 = [
            {}, {}, {}, {},
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
