"""Static checks for V2994 DOOM input live-gate audit."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
RUNNER = SCRIPTS / "native_doom_input_live_gate_v2994.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import native_doom_input_live_gate_v2994 as runner  # noqa: E402


class TestNativeDoomInputLiveGateV2994(unittest.TestCase):
    def test_runner_is_host_only_no_flash_gate(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('RUN_ID = "V2994"', text)
        self.assertIn("v2994-doom-input-live-gate-not-actionable", text)
        self.assertIn("Host-only/read-only audit; no flash", text)
        self.assertIn("Host-side HID devices are not A90 /dev/input keyboard candidates", text)
        self.assertNotIn("native_init_flash.py", text)
        self.assertNotIn("--live", text)
        self.assertNotIn("EVIOCGRAB", text)
        self.assertNotIn("O_WRONLY", text)
        self.assertNotIn("sendevent", text)

    def test_parse_health_surfaces(self) -> None:
        version = runner.parse_version("A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)")
        self.assertTrue(version["version_ok"])
        self.assertTrue(version["resident_v2321"])
        self.assertEqual(version["build_tag"], "v2321-usb-clean-identity-rodata")

        status = runner.parse_status("transport.bridge_endpoint=127.0.0.1:54321\ntransport.ncm=ready\nusb=yes\nstorage: sd present=yes mounted=yes rw=yes")
        self.assertTrue(status["control_bridge_ready"])
        self.assertTrue(status["ncm_ready"])
        self.assertTrue(status["storage_sd_rw"])

        selftest = runner.parse_selftest("selftest: pass=11 warn=1 fail=0\n08 PASS      input    rc=0 errno=0 0ms event0=ok event3=ok")
        self.assertTrue(selftest["selftest_ok"])
        self.assertTrue(selftest["input_event0_event3_ok"])
        self.assertEqual(selftest["fail"], 0)

    def test_parse_lsusb_tree_separates_host_hid_from_a90_peripheral(self) -> None:
        tree = """
/:  Bus 002.Port 001: Dev 001, Class=root_hub, Driver=xhci_hcd/4p, 20000M/x2
    |__ Port 003: Dev 013, If 0, Class=Communications, Driver=cdc_acm, 5000M
    |__ Port 003: Dev 013, If 2, Class=Communications, Driver=cdc_ncm, 5000M
/:  Bus 003.Port 001: Dev 001, Class=root_hub, Driver=xhci_hcd/12p, 480M
    |__ Port 003: Dev 003, If 0, Class=Human Interface Device, Driver=usbhid, 12M
"""
        parsed = runner.parse_lsusb_tree(tree)
        self.assertTrue(parsed["host_hid_present"])
        self.assertEqual(parsed["host_hid_interface_count"], 1)
        self.assertTrue(parsed["a90_usb_peripheral_present"])
        self.assertIn("cdc_acm", parsed["a90_usb_control_classes"])
        self.assertIn("not A90", parsed["host_hid_note"])

    def test_evaluate_gate_blocks_without_a90_keyboard_candidate(self) -> None:
        payload = {
            "prior_evidence": {
                "v2992_keyboard_fallback_staged": True,
                "v2992_operator_prerequisite": True,
                "v2991_keyboard_candidates": 0,
            },
            "device_health": {
                "version": {"version_ok": True},
                "selftest": {"selftest_ok": True},
            },
            "host_usb_topology": {
                "host_hid_present": True,
                "a90_usb_peripheral_present": True,
            },
        }
        gate = runner.evaluate_gate(payload)
        self.assertFalse(gate["v2992_live_ready_now"])
        self.assertEqual(gate["decision"], runner.DECISION_NOT_ACTIONABLE)
        self.assertIn("Host USB HID devices are present", "\n".join(gate["reasons"]))

        payload["prior_evidence"]["v2991_keyboard_candidates"] = 1
        gate = runner.evaluate_gate(payload)
        self.assertTrue(gate["v2992_live_ready_now"])
        self.assertEqual(gate["decision"], runner.DECISION_READY)

    def test_render_report_records_live_gate_decision(self) -> None:
        payload = {
            "out_dir": "workspace/private/runs/input/example",
            "inputs": {"v2991_result": "v2991.json", "v2992_report": "v2992.md", "v2993_report": "v2993.md"},
            "prior_evidence": {
                "v2992_keyboard_fallback_staged": True,
                "v2991_keyboard_candidates": 0,
            },
            "device_health": {
                "version": {"build_tag": "v2321-usb-clean-identity-rodata"},
                "selftest": {"selftest_ok": True},
            },
            "host_usb_topology": {
                "host_hid_interface_count": 2,
                "a90_usb_peripheral_present": True,
            },
            "gate": {
                "decision": runner.DECISION_NOT_ACTIONABLE,
                "v2992_live_ready_now": False,
                "reasons": ["No keyboard-class event has been observed on A90 inputscan evidence."],
                "next_action": "Run V2992 live only after A90 inputscan evidence can show a keyboard-class event.",
            },
        }
        report = runner.render_report(payload)
        self.assertIn("Native Init V2994 DOOM Input Live Gate Audit", report)
        self.assertIn("V2992 live ready now: `0`", report)
        self.assertIn("Host USB HID interfaces visible: `2`", report)
        self.assertIn("## Host Validation", report)


if __name__ == "__main__":
    unittest.main()
