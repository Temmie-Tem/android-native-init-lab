from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from _loader import load_revalidation


screenapp = load_revalidation("native_ui_screenapp_validation_v2187.py")


def base_manifest(**overrides):
    manifest = {
        "classification": {
            "decision": "v2187-screenapp-ui-validation-pass",
            "pass": True,
            "reason": "ok",
        },
        "flash_v2187": {"ok": True},
        "screenapp_status": {
            "pass": True,
            "title": "WIFI STATUS",
            "presented": "1",
        },
        "screenapp_ping": {
            "pass": True,
            "title": "WIFI PING RESULTS",
            "presented": "1",
        },
        "rollback": {
            "ok": True,
            "attempt": "from-native",
            "status_ok": True,
            "selftest_ok": True,
        },
        "out_dir": "workspace/private/runs/wifi/example",
    }
    manifest.update(overrides)
    return manifest


class PureHelpers(unittest.TestCase):
    def test_screenapp_pass_requires_valid_presented_rc_and_exact_title(self) -> None:
        valid = {
            "screenapp.valid": "1",
            "screenapp.presented": "1",
            "screenapp.rc": "0",
            "screenapp.title": "WIFI STATUS",
        }
        self.assertTrue(screenapp.screenapp_pass(valid, "WIFI STATUS"))

        for key, value in (
            ("screenapp.valid", "0"),
            ("screenapp.presented", "0"),
            ("screenapp.rc", "1"),
            ("screenapp.title", "OTHER"),
        ):
            with self.subTest(key=key):
                fields = dict(valid)
                fields[key] = value
                self.assertFalse(screenapp.screenapp_pass(fields, "WIFI STATUS"))

    def test_classify_prioritizes_flash_status_ping_and_rollback_failures(self) -> None:
        cases = [
            (
                {"flash_v2187": {"ok": False}},
                "v2187-screenapp-flash-failed",
                "flash",
            ),
            (
                {"screenapp_status": {"pass": False}},
                "v2187-screenapp-wifi-status-failed",
                "WIFI STATUS",
            ),
            (
                {"screenapp_ping": {"pass": False}},
                "v2187-screenapp-wifi-ping-failed",
                "WIFI PING",
            ),
            (
                {"rollback": {"selftest_ok": False}},
                "v2187-screenapp-rollback-selftest-failed",
                "rollback",
            ),
        ]

        for override, decision, reason_fragment in cases:
            with self.subTest(decision=decision):
                result = screenapp.classify(base_manifest(**override))
                self.assertFalse(result["pass"])
                self.assertEqual(result["decision"], decision)
                self.assertIn(reason_fragment, result["reason"])

        passed = screenapp.classify(base_manifest())
        self.assertTrue(passed["pass"])
        self.assertEqual(passed["decision"], "v2187-screenapp-ui-validation-pass")

    def test_render_report_includes_decision_evidence_and_safety_scope(self) -> None:
        manifest = base_manifest()

        report = screenapp.render_report(manifest)

        self.assertIn("# Native Init V2187 Screenapp UI Validation Live", report)
        self.assertIn("- Decision: `v2187-screenapp-ui-validation-pass`.", report)
        self.assertIn("- Result: PASS.", report)
        self.assertIn("`screenapp wifi-status`: pass `True`, title `WIFI STATUS`, presented `1`.", report)
        self.assertIn("`screenapp wifi-ping`: pass `True`, title `WIFI PING RESULTS`, presented `1`.", report)
        self.assertIn("No credentials, raw SSID, BSSID, private IP, gateway, or peer MAC details", report)

    def test_rel_prefers_repo_relative_paths_and_keeps_external_paths_absolute(self) -> None:
        inside = screenapp.REPO_ROOT / "docs" / "reports"
        external = Path("/tmp/a90-external-path")

        self.assertEqual(screenapp.rel(inside), "docs/reports")
        self.assertEqual(screenapp.rel(external), str(external))

    def test_fields_for_parses_key_values_from_matching_step_output(self) -> None:
        steps = [{"name": "screenapp-wifi-status"}]
        with (
            mock.patch.object(screenapp, "find_step", return_value=steps[0]) as find_step,
            mock.patch.object(screenapp, "step_text", return_value="screenapp.valid=1\nscreenapp.title=WIFI_STATUS\n") as step_text,
        ):
            fields = screenapp.fields_for(object(), steps, "screenapp-wifi-status")

        self.assertEqual(fields["screenapp.valid"], "1")
        self.assertEqual(fields["screenapp.title"], "WIFI_STATUS")
        find_step.assert_called_once_with(steps, "screenapp-wifi-status")
        step_text.assert_called_once_with(mock.ANY, steps[0])


if __name__ == "__main__":
    unittest.main()
