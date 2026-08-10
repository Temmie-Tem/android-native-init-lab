from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


class A90H15ArmedRecoveryV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_script(
            "workspace/public/src/scripts/server-distro/"
            "a90_h15_armed_recovery_v1.py"
        )

    def test_expected_enable_binds_exact_incident_and_ufs_identity(self) -> None:
        intent = "a" * 64
        body = self.module._expected_enable(intent)
        self.assertIn(b"schema=a90-auto-handoff-userdata-ro-v1\n", body)
        self.assertIn(b"build=phase3-minimal-h15-direct-ufs-ro-async-wifi-auto-benchmark\n", body)
        self.assertIn(b"userdata_dev=259:17\n", body)
        self.assertIn(f"intent_sha256={intent}\n".encode(), body)
        self.assertTrue(body.endswith(b"state=armed-after-native-health\n"))

    def test_cleanup_script_is_one_exact_unlink_and_sync_without_reboot(self) -> None:
        body = self.module._expected_enable("b" * 64)
        script = self.module._cleanup_script(
            hashlib.sha256(body).hexdigest(),
            len(body),
        )
        self.assertEqual(script.count('/bin/busybox rm -- "$P"'), 1)
        self.assertEqual(script.count("/bin/busybox sync"), 1)
        self.assertEqual(script.count(self.module.ENABLE_PATH), 1)
        self.assertEqual(script.count(self.module.LATCH_PATH), 1)
        self.assertNotIn('/bin/busybox rm -- "$L"', script)
        self.assertGreaterEqual(script.count('[ ! -e "$L" ]'), 2)
        self.assertIn(f'regular file|{len(body)}|600|1', script)
        for forbidden in ("reboot", "switch_root", "mount", "dd ", "flash"):
            self.assertNotIn(forbidden, script)

    def test_execution_closure_binds_contract_incident_and_transport(self) -> None:
        closure = self.module.execution_closure()
        self.assertEqual(len(closure["files"]), len(self.module.EXECUTION_RELS))
        self.assertIn(self.module.TARGET_CONTRACT_REL, closure["files"])
        self.assertIn(self.module.INCIDENT_REPORT_REL, closure["files"])
        self.assertRegex(closure["sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(
            set(self.module.f1.EXECUTION_SOURCE_RELS).issubset(closure["files"])
        )

    def test_capability_is_incident_specific_and_replay_free(self) -> None:
        self.assertEqual(self.module.RUN_ID, "a90-h15-ufs-f1-20260810-01")
        self.assertEqual(
            self.module.PREDECESSOR_EXECUTION_SHA256,
            "1f4f5332e687ad783c9cf072ed3779918781c31079012565e61bb243c4e8dba4",
        )
        source = (
            self.module.REPO_ROOT
            / "workspace/public/src/scripts/server-distro/"
            "a90_h15_armed_recovery_v1.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"unlink_replay": False', source)
        self.assertIn('"reboot_count": 0', source)
        self.assertIn('"handoff_count": 0', source)

    def test_manifest_validator_uses_the_actual_h15_ready_status(self) -> None:
        source = (
            self.module.REPO_ROOT
            / "workspace/public/src/scripts/server-distro/"
            "a90_h15_armed_recovery_v1.py"
        ).read_text(encoding="utf-8")
        self.assertIn('value.get("status") != "ready-for-attended-f1"', source)
        self.assertNotIn('value.get("status") != "READY_FOR_F1_APPROVAL"', source)

    def test_preserved_enable_is_exact_private_single_link_bytes(self) -> None:
        expected = self.module._expected_enable("c" * 64)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            preserved = self.module._write_preserved(
                directory / "enable-before.bin",
                expected,
            )
            self.assertEqual(
                self.module._validate_preserved(directory, preserved, expected),
                preserved,
            )
            (directory / "enable-before.bin").chmod(0o644)
            with self.assertRaisesRegex(
                self.module.ContractError,
                "preserved enable file shape changed",
            ):
                self.module._validate_preserved(directory, preserved, expected)

    def test_preserved_writer_publishes_only_complete_temp_and_repairs_alias(self) -> None:
        expected = self.module._expected_enable("f" * 64)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            final = directory / "enable-before.bin"
            preserved = self.module._write_preserved(final, expected)
            alias = directory / f".{final.name}.tmp-123-456"
            alias.hardlink_to(final)
            self.assertEqual(final.stat().st_nlink, 2)
            self.module._validate_preserved(directory, preserved, expected)
            self.assertFalse(alias.exists())
            self.assertEqual(final.stat().st_nlink, 1)
        source = (
            self.module.REPO_ROOT
            / "workspace/public/src/scripts/server-distro/"
            "a90_h15_armed_recovery_v1.py"
        ).read_text(encoding="utf-8")
        writer = source[source.index("def _write_preserved(") : source.index("def _fsync_directory(")]
        self.assertIn("os.open(\n        temporary,", writer)
        self.assertIn("os.link(temporary, path", writer)

    def test_intent_only_reconciliation_can_close_without_claiming_dispatch(self) -> None:
        written: list[tuple[int, str, dict]] = []
        intent = "d" * 64
        expected = self.module._expected_enable(intent)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            preserved = self.module._write_preserved(
                directory / "enable-before.bin",
                expected,
            )
            with mock.patch.object(
                self.module,
                "_status_and_health",
                return_value=(
                    {"record": "status"},
                    {"binding": 1, "enable": 0, "latch": 0},
                    {"resident_healthy": True},
                ),
            ), mock.patch.object(
                self.module,
                "_write_record",
                side_effect=lambda _directory, index, action, payload: written.append(
                    (index, action, payload)
                ),
            ):
                result = self.module._close_from_absence(
                    directory,
                    object(),
                    intent,
                    preserved,
                    command_result={
                        "response_proof": False,
                        "reconciled_after_intent_only": True,
                    },
                    unlink_dispatch_count=None,
                )
        self.assertEqual(result["terminal"], "PASS_H15_ARMED_STATE_RECOVERED")
        self.assertIsNone(result["unlink_dispatch_count"])
        self.assertEqual(result["unlink_dispatch_count_max"], 1)
        self.assertFalse(result["unlink_dispatch_count_exact"])
        self.assertEqual([item[:2] for item in written], [(3, "final-health"), (4, "closed")])

    def test_reconcile_reuses_the_durable_unknown_dispatch_count(self) -> None:
        source = (
            self.module.REPO_ROOT
            / "workspace/public/src/scripts/server-distro/"
            "a90_h15_armed_recovery_v1.py"
        ).read_text(encoding="utf-8")
        reconcile = source[source.index("def reconcile(") : source.index("def parser(")]
        self.assertIn(
            'unlink_dispatch_count=records[2].get("unlink_dispatch_count")',
            reconcile,
        )
        self.assertNotIn("unlink_dispatch_count=1,\n    )", reconcile)

    def test_cleanup_transport_is_exactly_once_and_retry_unsafe_false(self) -> None:
        effect_args = self.module._effect_args()
        with mock.patch.object(
            self.module.transport,
            "run_cmd",
            return_value={"rc": 0, "text": "ok"},
        ) as run_cmd:
            result = self.module._run_cleanup_once(effect_args, "echo fixed")
        self.assertEqual(result, {"rc": 0, "text": "ok"})
        run_cmd.assert_called_once()
        self.assertFalse(run_cmd.call_args.kwargs["retry_unsafe"])
        self.assertEqual(
            run_cmd.call_args.args[3],
            ["run", "/bin/busybox", "sh", "-c", "echo fixed"],
        )
        source = (
            self.module.REPO_ROOT
            / "workspace/public/src/scripts/server-distro/"
            "a90_h15_armed_recovery_v1.py"
        ).read_text(encoding="utf-8")
        execute = source[source.index("def execute(") : source.index("def reconcile(")]
        self.assertNotIn("run_f1_shell", execute)

    def test_broken_journal_symlink_is_corruption_not_absence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / self.module.JOURNAL_NAMES[0]).symlink_to("missing-target")
            with self.assertRaisesRegex(
                self.module.ContractError,
                "recovery journal file shape changed",
            ):
                self.module._read_records(directory)

    def test_exact_writer_temp_hardlink_is_retired_before_journal_read(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            final = directory / self.module.JOURNAL_NAMES[0]
            value = {
                "schema": self.module.SCHEMA,
                "sequence": 0,
                "action": self.module.JOURNAL_ACTIONS[0],
            }
            self.module.f1.write_json_exclusive(final, value)
            alias = directory / f".{final.name}.tmp-123-456"
            alias.hardlink_to(final)
            self.assertEqual(final.stat().st_nlink, 2)
            self.assertEqual(self.module._read_records(directory), [value])
            self.assertFalse(alias.exists())
            self.assertEqual(final.stat().st_nlink, 1)

    def test_pre_intent_prefixes_report_contact_and_can_resume_execute(self) -> None:
        source = (
            self.module.REPO_ROOT
            / "workspace/public/src/scripts/server-distro/"
            "a90_h15_armed_recovery_v1.py"
        ).read_text(encoding="utf-8")
        execute = source[source.index("def execute(") : source.index("def reconcile(")]
        reconcile = source[source.index("def reconcile(") : source.index("def parser(")]
        self.assertIn("execute continuation is limited to a pre-intent journal prefix", execute)
        self.assertIn('"PRE_OPEN_READY_FOR_EXECUTE_CONTINUATION"', reconcile)
        self.assertIn('"PRE_INTENT_READY_FOR_EXECUTE_CONTINUATION"', reconcile)
        self.assertNotIn('"device_contact": False', reconcile)


if __name__ == "__main__":
    unittest.main()
