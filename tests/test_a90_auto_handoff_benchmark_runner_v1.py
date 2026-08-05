"""Static and pure tests for the A90 H2 automatic benchmark runner."""

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
    def _status(enable: int, latch: int) -> dict:
        return {
            "text": (
                f"A90AUTO_STATUS binding=1 enable={enable} latch={latch} "
                "build=phase3-minimal-h2-two-phase-auto-benchmark\n"
            )
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

    def test_status_parser_requires_one_exact_h2_line(self) -> None:
        record = {
            "text": (
                "A90AUTO_STATUS binding=1 enable=0 latch=0 "
                "build=phase3-minimal-h2-two-phase-auto-benchmark\n"
            )
        }
        self.assertEqual(
            runner.parse_auto_status(record),
            {
                "binding": 1,
                "enable": 0,
                "latch": 0,
                "build": "phase3-minimal-h2-two-phase-auto-benchmark",
            },
        )
        with self.assertRaises(runner.ContractError):
            runner.parse_auto_status({"text": record["text"] * 2})

    def test_execution_closure_binds_runner_and_parser(self) -> None:
        closure = runner.execution_closure()
        self.assertEqual(set(closure["files"]), {"runner", "benchmark_parser"})
        self.assertRegex(closure["sha256"], r"^[0-9a-f]{64}$")

    def test_intents_precede_one_arm_and_one_reboot(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        execute = source[source.index("def execute(") : source.index("def reconcile(")]
        arm_intent = execute.index('"arm-intent"')
        arm_dispatch = execute.index('["auto-handoff-arm", ARM_TOKEN, intent_sha256]')
        arm_status = execute.index("require_auto_status(args, enable=1, latch=0)")
        reboot_intent = execute.index('"reboot-intent"')
        reboot_dispatch = execute.index("send_reboot_once(args)")
        observation = execute.index("observe_auto_cycle(spec, args, path, guard)")
        returned_status = execute.index(
            "returned_status_record, returned_status = require_auto_status("
        )
        cleanup_intent = execute.index('"cleanup-intent"')
        cleanup_dispatch = execute.index("base.run_f1_shell")
        self.assertLess(arm_intent, arm_dispatch)
        self.assertLess(arm_dispatch, arm_status)
        self.assertLess(arm_status, reboot_intent)
        self.assertLess(reboot_intent, reboot_dispatch)
        self.assertLess(reboot_dispatch, observation)
        self.assertLess(observation, returned_status)
        self.assertLess(returned_status, cleanup_intent)
        self.assertLess(cleanup_intent, cleanup_dispatch)
        self.assertEqual(execute.count("send_reboot_once(args)"), 1)
        self.assertEqual(
            execute.count(
                'arm_record = base.run_f1_cmd(\n            args,\n'
                '            ["auto-handoff-arm", ARM_TOKEN, intent_sha256],'
            ),
            1,
        )

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
        records6 = [{}, {}, {}, {}, {"observation": observation, "intent_sha256": "6" * 64}, {}]
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
