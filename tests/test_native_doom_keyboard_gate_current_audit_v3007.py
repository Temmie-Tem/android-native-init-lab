"""Static checks for V3007 current DOOM keyboard-gate audit."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
RUNNER = SCRIPTS / "native_doom_keyboard_gate_current_audit_v3007.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import native_doom_keyboard_gate_current_audit_v3007 as runner  # noqa: E402


class TestNativeDoomKeyboardGateCurrentAuditV3007(unittest.TestCase):
    def test_runner_is_read_only_current_gate_audit(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('RUN_ID = "V3007"', text)
        self.assertIn("v3007-doom-keyboard-gate-hardware-stimulus-required", text)
        self.assertIn("Read-only audit; no flash", text)
        self.assertIn("V3004_REPORT", text)
        self.assertIn("V3006_REPORT", text)
        self.assertNotIn("native_init_flash.py", text)
        self.assertNotIn("EVIOCGRAB", text)
        self.assertNotIn("O_WRONLY", text)
        self.assertNotIn("sendevent", text)

    def test_parse_health_and_usb_surfaces(self) -> None:
        version = runner.parse_version("A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)")
        self.assertTrue(version["version_ok"])
        self.assertTrue(version["resident_v2321"])
        self.assertEqual(version["build_tag"], "v2321-usb-clean-identity-rodata")

        selftest = runner.parse_selftest("selftest: pass=11 warn=1 fail=0\n08 PASS input event0=ok event3=ok")
        self.assertTrue(selftest["selftest_ok"])
        self.assertTrue(selftest["builtin_buttons_ok"])

        status = runner.parse_status("transport.bridge_endpoint=127.0.0.1:54321\ntransport.ncm=ready\nstorage: sd present=yes mounted=yes rw=yes")
        self.assertTrue(status["transport_ready"])
        self.assertTrue(status["ncm_ready"])
        self.assertTrue(status["storage_ready"])

        usb = runner.parse_lsusb_tree("""
/:  Bus 003.Port 001: Dev 001, Class=root_hub, Driver=xhci_hcd/12p, 480M
    |__ Port 003: Dev 003, If 0, Class=Human Interface Device, Driver=usbhid, 12M
    |__ Port 004: Dev 004, If 0, Class=Communications, Driver=cdc_acm, 480M
""")
        self.assertTrue(usb["host_hid_present"])
        self.assertTrue(usb["a90_control_present"])
        self.assertIn("not proof", usb["host_hid_note"])

    def test_evaluate_gate_requires_hardware_stimulus_even_with_good_reports(self) -> None:
        payload = {
            "reports": {
                "v3004_preflight_ok": True,
                "v3004_requires_usb_keyboard": True,
                "v3006_live_pass": True,
                "v3006_status_points_to_v3004": True,
            },
            "device_health": {
                "version": {"version_ok": True},
                "selftest": {"selftest_ok": True},
            },
            "host_usb_topology": {
                "host_hid_present": True,
                "a90_control_present": True,
            },
            "a90_otg_keyboard_evidence": False,
        }
        gate = runner.evaluate_gate(payload)
        self.assertEqual(gate["decision"], runner.DECISION_NOT_ACTIONABLE)
        self.assertFalse(gate["v3004_live_actionable_now"])
        self.assertIn("No current evidence shows an attached A90 USB keyboard/OTG path", "\n".join(gate["reasons"]))

    def test_render_report_records_current_v3004_v3006_gate(self) -> None:
        payload = {
            "out_dir": "workspace/private/runs/input/example",
            "inputs": {"v3004_report": "v3004.md", "v3006_report": "v3006.md"},
            "reports": {
                "v3004_preflight_ok": True,
                "v3004_live_execution": False,
                "v3006_live_pass": True,
                "v3006_status_points_to_v3004": True,
            },
            "device_health": {
                "version": {"build_tag": "v2321-usb-clean-identity-rodata"},
                "selftest": {"selftest_ok": True},
            },
            "host_usb_topology": {
                "host_hid_interface_count": 2,
                "a90_control_present": True,
            },
            "a90_otg_keyboard_evidence": False,
            "gate": {
                "decision": runner.DECISION_NOT_ACTIONABLE,
                "v3004_live_actionable_now": False,
                "reasons": ["No current evidence shows an attached A90 USB keyboard/OTG path."],
                "next_action": "Run V3004 live only when USB keyboard/OTG is attached.",
            },
        }
        report = runner.render_report(payload)
        self.assertIn("Native Init V3007 DOOM Keyboard Gate Current Audit", report)
        self.assertIn("V3004 live actionable now: `0`", report)
        self.assertIn("V3006 status surface live pass: `1`", report)
        self.assertIn("A90 OTG keyboard evdev evidence: `0`", report)
        self.assertIn("## Safety", report)


if __name__ == "__main__":
    unittest.main()
