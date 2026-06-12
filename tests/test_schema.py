"""Regression tests for a90harness.schema result dataclasses.

The current schema module exposes lightweight dataclasses, not active validators.
These tests pin their serialized contract and HarnessResult failure rollups.
"""

import unittest

from _loader import load_harness

schema = load_harness("schema")


class CheckResultSchema(unittest.TestCase):
    def test_check_result_to_dict_serializes_fields(self):
        result = schema.CheckResult(name="selftest", ok=True, detail="fail=0")

        self.assertEqual(
            result.to_dict(),
            {"name": "selftest", "ok": True, "detail": "fail=0"},
        )


class CommandRecordSchema(unittest.TestCase):
    def test_command_record_to_dict_includes_default_error(self):
        record = schema.CommandRecord(
            name="version",
            command=["a90ctl", "version"],
            ok=True,
            rc=0,
            status="ok",
            duration_sec=0.125,
            transcript="A90 Linux init",
        )

        self.assertEqual(
            record.to_dict(),
            {
                "name": "version",
                "command": ["a90ctl", "version"],
                "ok": True,
                "rc": 0,
                "status": "ok",
                "duration_sec": 0.125,
                "transcript": "A90 Linux init",
                "error": "",
            },
        )

    def test_command_record_to_dict_keeps_none_rc_and_error(self):
        record = schema.CommandRecord(
            name="bridge",
            command=["a90ctl", "status"],
            ok=False,
            rc=None,
            status="timeout",
            duration_sec=45.0,
            transcript="",
            error="timed out",
        )

        self.assertEqual(record.to_dict()["rc"], None)
        self.assertEqual(record.to_dict()["error"], "timed out")


class HarnessResultSchema(unittest.TestCase):
    def test_harness_result_to_dict_rolls_up_only_failed_items(self):
        passing_check = schema.CheckResult("version", True, "ok")
        failing_check = schema.CheckResult("selftest", False, "fail=1")
        passing_command = schema.CommandRecord(
            name="version",
            command=["a90ctl", "version"],
            ok=True,
            rc=0,
            status="ok",
            duration_sec=0.1,
            transcript="version output",
        )
        failing_command = schema.CommandRecord(
            name="status",
            command=["a90ctl", "status"],
            ok=False,
            rc=1,
            status="failed",
            duration_sec=0.2,
            transcript="status output",
            error="bad status",
        )

        result = schema.HarnessResult(
            label="smoke",
            ok=False,
            checks=[passing_check, failing_check],
            commands=[passing_command, failing_command],
        ).to_dict()

        self.assertEqual(result["label"], "smoke")
        self.assertFalse(result["ok"])
        self.assertEqual(result["checks"], [passing_check.to_dict(), failing_check.to_dict()])
        self.assertEqual(result["commands"], [passing_command.to_dict(), failing_command.to_dict()])
        self.assertEqual(result["failed_checks"], [failing_check.to_dict()])
        self.assertEqual(result["failed_commands"], [failing_command.to_dict()])

    def test_harness_result_empty_lists_are_serialized(self):
        result = schema.HarnessResult(label="empty", ok=True, checks=[], commands=[]).to_dict()

        self.assertEqual(
            result,
            {
                "label": "empty",
                "ok": True,
                "checks": [],
                "commands": [],
                "failed_checks": [],
                "failed_commands": [],
            },
        )


if __name__ == "__main__":
    unittest.main()
