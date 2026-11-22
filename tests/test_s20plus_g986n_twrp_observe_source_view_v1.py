import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
import s20plus_g986n_twrp_observe_source_view_v1 as view


class TwrpObserveSourceViewTests(unittest.TestCase):
    def test_live_command_has_one_read_only_baseline_mode(self):
        argv = view.command(observe=True)
        self.assertEqual(argv[-2:], [str(view.BASELINE), "--observe"])
        self.assertEqual(argv.count("--bind"), 1)
        index = argv.index("--bind")
        self.assertEqual(argv[index + 1:index + 3], [str(view.RUN_ROOT)] * 2)
        for source, destination in (*view.SOURCE_BINDS, *view.QUALIFICATION_BINDS):
            index = argv.index(str(source))
            self.assertEqual(argv[index - 1:index + 2],
                             ["--ro-bind", str(source), str(destination)])
        self.assertNotIn("--enter", argv)
        self.assertNotIn("--resume", argv)
        self.assertIn("pycache_prefix=/dev/null", argv)

    def test_h0_command_has_no_run_directory_or_qualification_mount(self):
        argv = view.command(observe=False)
        self.assertEqual(argv[-2:], ["-c", view.FINGERPRINT_SCRIPT])
        self.assertIn("validate_host_closure(enforce_self=True)", argv[-1])
        self.assertIn("baseline.routine.bounded_command", argv[-1])
        self.assertNotIn("--bind", argv)
        self.assertNotIn(str(view.QUALIFICATION), argv)

    def test_capture_uses_private_temporary_storage_and_standard_devices(self):
        for observe in (False, True):
            argv = view.command(observe=observe)
            index = argv.index("--tmpfs")
            self.assertEqual(argv[index:index + 4], ["--tmpfs", "/tmp", "--dev", "/dev"])
        self.assertEqual(view.clean_environment()["TMPDIR"], "/tmp")

    def test_review_binds_the_exact_view_and_test_log(self):
        with tempfile.TemporaryDirectory() as temporary:
            qualification = Path(temporary) / "qualification.json"
            log = Path(temporary) / "tests.log"
            log.write_bytes(b"OK\n")
            log.chmod(0o400)
            expected_view = {"mode": "observe-only", "files": {"example": "original"}}
            qualification.write_text(json.dumps({
                "schema": view.REVIEW_SCHEMA,
                "review": view.REVIEW_PASS,
                "observation_view": expected_view,
                "tests": {"path": str(view.BASELINE_TEST_LOG), **view.file_receipt(log.read_bytes())},
            }, indent=2, sort_keys=True) + "\n")
            qualification.chmod(0o400)
            with mock.patch.multiple(view, QUALIFICATION=qualification, TEST_LOG=log):
                view.require_review(expected_view)
                with self.assertRaisesRegex(ValueError, "review differs"):
                    view.require_review({"mode": "observe-only", "files": {"example": "changed"}})
                log.chmod(0o600)
                log.write_bytes(b"updated\nOK\n")
                log.chmod(0o400)
                with self.assertRaisesRegex(ValueError, "review differs"):
                    view.require_review(expected_view)

    def test_existing_guard_stops_before_bwrap_or_adb(self):
        with (mock.patch.object(sys, "argv", ["view", "--observe"]),
              mock.patch.object(view, "view_receipt", return_value={}),
              mock.patch.object(view, "require_review"),
              mock.patch.object(view.os.path, "lexists", return_value=True),
              mock.patch.object(view.subprocess, "run") as run):
            with self.assertRaisesRegex(ValueError, "already holds a guard"):
                view.main()
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
