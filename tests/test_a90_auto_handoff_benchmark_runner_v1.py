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
            bridge_realpath="/dev/ttyACM-test",
            candidate_version=runner.EXPECTED_VERSION,
            candidate_build=runner.EXPECTED_BUILD,
        )

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

    def test_appended_benchmark_rejects_nonprefix_or_unchanged_log(self) -> None:
        opening = self._complete_benchmark_segment(1_000)
        current = self._complete_benchmark_segment(100)
        with mock.patch.object(
            runner.base,
            "require_exact_f1_command_receipt",
            side_effect=lambda value, _command, _label: value,
        ):
            for final in (opening, current):
                with self.subTest(final=final[:40]), self.assertRaisesRegex(
                    runner.ContractError,
                    "exact appended marker suffix",
                ):
                    runner.parse_appended_benchmark(
                        {"text": opening},
                        {"text": final},
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
            "multiple handoff boot segments",
        ):
            runner.parse_appended_benchmark(
                {"text": opening},
                {"text": "\n".join((opening, first, second))},
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
                "resident_manifest_loader",
                "resident_f1_loader",
            },
        )
        self.assertRegex(closure["sha256"], r"^[0-9a-f]{64}$")

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
        self.assertEqual(order[:2], ["ncm", "ssh"])
        self.assertEqual(result["host_ncm_rebind"], {"ready": True})

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
