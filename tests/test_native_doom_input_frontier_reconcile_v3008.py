"""Static checks for V3008 DOOM input frontier reconciliation."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
RUNNER = SCRIPTS / "native_doom_input_frontier_reconcile_v3008.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import native_doom_input_frontier_reconcile_v3008 as runner  # noqa: E402


def complete_texts() -> dict[str, str]:
    return {
        "v2984": "\n".join([
            "v2984-inputcaps-live-pass-before-rollback",
            "`event6` | `0` | `1` | `1` | `1` | `1` | `1` | `unsupported`",
            "`event8` | `0` | `1` | `1` | `1` | `1` | `1` | `unsupported`",
            "runtime PM reports `unsupported` rather than `suspended`",
        ]),
        "v2990": "\n".join([
            "v2990-doominput-state-touch-state-not-proven",
            "DOOM input events: `0` states=`0` touch_states=`0`",
        ]),
        "v2991": "\n".join([
            "v2991-doominput-dual-touch-touch-state-not-proven",
            "`event6` selected_touch=`1` caps_ok=`1` doominput_rc=`-110` events=`0` states=`0`",
            "`event8` selected_touch=`1` caps_ok=`1` doominput_rc=`-110` events=`0` states=`0`",
        ]),
        "v3002": "\n".join([
            "v3002-doominput-mux-state-not-proven",
            "button_candidates=`2`",
            "Mux events: `0` states=`0` active_states=`0` proxy_states=`0`",
            "Rollback health: version_ok=`1` selftest_fail0=`1`",
        ]),
        "v3004": "\n".join([
            "v3004-doominput-keyboard-dry-run",
            "Preflight ok: `1`",
            "USB keyboard/OTG attached and DOOM keys pressed",
            "Live execution: `0`",
        ]),
        "v3006": "\n".join([
            "v3006-doom-keyboard-gate-status-status-surface-pass-before-rollback",
            "video.demo.input.hardware_gate=usb-keyboard-otg",
            "video.demo.input.keyboard_gate=v3004-doominput-keyboard-live-gate",
            "video.demo.input.physical_button_mux=v3002-zero-event-do-not-repeat",
            "video.demo.input.touch=event6,event8-zero-events",
        ]),
        "v3007": "\n".join([
            "v3007-doom-keyboard-gate-hardware-stimulus-required",
            "A90 OTG keyboard evdev evidence: `0`",
            "V3004 live actionable now: `0`",
        ]),
    }


class TestNativeDoomInputFrontierReconcileV3008(unittest.TestCase):
    def test_runner_is_host_only_reconciliation(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('RUN_ID = "V3008"', text)
        self.assertIn("V2984..V3007 evidence", text)
        self.assertIn("Host-only metadata reconciliation", text)
        self.assertNotIn("native_init_flash.py", text)
        self.assertNotIn("EVIOCGRAB", text)
        self.assertNotIn("O_WRONLY", text)
        self.assertNotIn("sendevent", text)

    def test_analyze_reports_classifies_complete_frontier(self) -> None:
        flags = runner.analyze_reports(complete_texts())
        self.assertEqual(flags["decision"], runner.DECISION)
        self.assertTrue(flags["touch_caps_proven"])
        self.assertTrue(flags["touch_events_not_proven"])
        self.assertTrue(flags["button_mux_not_proven"])
        self.assertTrue(flags["keyboard_gate_staged"])
        self.assertTrue(flags["status_surface_points_to_keyboard"])
        self.assertTrue(flags["current_gate_not_actionable"])
        self.assertTrue(flags["saturated_without_external_stimulus"])
        self.assertIn("native_doominput_keyboard_live_gate_v3004.py --live", flags["next_live_command"])

    def test_analyze_reports_rejects_missing_current_gate(self) -> None:
        texts = complete_texts()
        texts["v3007"] = "v3007-doom-keyboard-gate-live-ready\nV3004 live actionable now: `1`"
        flags = runner.analyze_reports(texts)
        self.assertEqual(flags["decision"], "v3008-doom-input-frontier-evidence-incomplete")
        self.assertFalse(flags["current_gate_not_actionable"])
        self.assertFalse(flags["saturated_without_external_stimulus"])

    def test_render_report_records_next_live_action_and_safety(self) -> None:
        payload = {
            "flags": runner.analyze_reports(complete_texts()),
            "reports": {key: f"docs/reports/{key}.md" for key in runner.REPORTS},
        }
        report = runner.render_report(payload)
        self.assertIn("Native Init V3008 DOOM Input Frontier Reconciliation", report)
        self.assertIn("Active tier saturated without external stimulus: `1`", report)
        self.assertIn("USB keyboard/OTG attached to the A90", report)
        self.assertIn("Host-only metadata reconciliation", report)
        self.assertIn("no flash", report)


if __name__ == "__main__":
    unittest.main()
