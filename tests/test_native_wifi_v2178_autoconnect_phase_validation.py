from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation


autoconnect = load_revalidation("native_wifi_v2178_autoconnect_phase_validation.py")


def base_manifest(**overrides):
    manifest = {
        "version": {"expected": True},
        "connect": {
            "decision": "wifi-autoconnect-pass",
            "secret_values_logged": "0",
            "credentials_logged": "0",
        },
        "autoconnect_status": {"secret_values_logged": "0"},
        "scope": {"credentials_logged": 0},
        "cleanup": {"decision": "wifi-cleanup-done"},
        "autoconnect_disable_restore": {"decision": "wifi-autoconnect-disabled"},
        "final_selftest": {"fail0": True},
    }
    manifest.update(overrides)
    return manifest


class PureHelpers(unittest.TestCase):
    def test_classify_accepts_clean_autoconnect_cleanup_and_selftest(self) -> None:
        result = autoconnect.classify(base_manifest())

        self.assertTrue(result["pass"])
        self.assertEqual(result["decision"], "v2180-wifi-phase-validation-pass")
        self.assertIn("cleanup completed", result["reason"])

    def test_classify_prioritizes_baseline_connect_cleanup_disable_and_selftest(self) -> None:
        cases = [
            (
                {"version": {"expected": False}},
                "v2180-wifi-phase-wrong-baseline",
                "baseline",
            ),
            (
                {"connect": {"decision": "wifi-autoconnect-failed"}},
                "v2180-wifi-phase-connect-failed",
                "autoconnect once",
            ),
            (
                {"cleanup": {"decision": "wifi-cleanup-failed"}},
                "v2180-wifi-phase-cleanup-failed",
                "cleanup",
            ),
            (
                {"autoconnect_disable_restore": {"decision": "wifi-autoconnect-enabled"}},
                "v2180-wifi-phase-disable-restore-failed",
                "disable restore",
            ),
            (
                {"final_selftest": {"fail0": False}},
                "v2180-wifi-phase-selftest-failed",
                "selftest",
            ),
        ]

        for override, decision, reason_fragment in cases:
            with self.subTest(decision=decision):
                result = autoconnect.classify(base_manifest(**override))
                self.assertFalse(result["pass"])
                self.assertEqual(result["decision"], decision)
                self.assertIn(reason_fragment, result["reason"])

    def test_classify_rejects_any_nonzero_or_missing_secret_hygiene_flag(self) -> None:
        cases = [
            {"autoconnect_status": {"secret_values_logged": "1"}},
            {"connect": {"decision": "wifi-autoconnect-pass", "secret_values_logged": "1", "credentials_logged": "0"}},
            {"connect": {"decision": "wifi-autoconnect-pass", "secret_values_logged": "0", "credentials_logged": "1"}},
            {"scope": {"credentials_logged": 1}},
            {"connect": {"decision": "wifi-autoconnect-pass", "secret_values_logged": "0"}},
        ]

        for override in cases:
            with self.subTest(override=override):
                result = autoconnect.classify(base_manifest(**override))
                self.assertFalse(result["pass"])
                self.assertEqual(result["decision"], "v2180-wifi-phase-secret-hygiene-failed")
                self.assertIn("credential/secret hygiene", result["reason"])

    def test_step_helpers_read_recent_step_outputs_and_ignore_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            (run_dir / "stdout.txt").write_text("alpha=1\n", encoding="utf-8")
            (run_dir / "stderr.txt").write_text("beta=2\n", encoding="utf-8")
            store = type("Store", (), {"run_dir": run_dir})()
            steps = [
                {"name": "wifi-autoconnect-once", "stdout_file": "old.txt"},
                {
                    "name": "wifi-autoconnect-once",
                    "stdout_file": "stdout.txt",
                    "stderr_file": "stderr.txt",
                    "extra_missing_file": "ignored.txt",
                },
            ]

            step = autoconnect.find_step(steps, "wifi-autoconnect-once")
            text = autoconnect.step_text(store, step)

        self.assertIs(step, steps[1])
        self.assertEqual(text, "alpha=1\nbeta=2\n")
        self.assertIsNone(autoconnect.find_step(steps, "not-present"))
        self.assertEqual(autoconnect.step_text(store, None), "")

    def test_zero_flag_and_rel_are_strict_and_repo_relative(self) -> None:
        self.assertTrue(autoconnect.zero_flag("0"))
        self.assertTrue(autoconnect.zero_flag(0))
        self.assertFalse(autoconnect.zero_flag(False))
        self.assertFalse(autoconnect.zero_flag(None))

        self.assertEqual(autoconnect.rel(autoconnect.REPO_ROOT / "tests"), "tests")
        self.assertEqual(autoconnect.rel(Path("/tmp/a90-outside")), "/tmp/a90-outside")


if __name__ == "__main__":
    unittest.main()
