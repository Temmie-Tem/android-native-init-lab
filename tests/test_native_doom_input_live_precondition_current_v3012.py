"""Static checks for V3012 current DOOM input live-precondition audit."""

from __future__ import annotations

from pathlib import Path
import unittest

from _loader import load_script


runner = load_script("workspace/public/src/scripts/revalidation/native_doom_input_live_precondition_current_v3012.py")


def complete_payload() -> dict:
    return {
        "run_id": runner.RUN_ID,
        "build_tag": runner.BUILD_TAG,
        "out_dir": "workspace/private/runs/input/example",
        "inputs": {
            "v3008_report": "docs/reports/v3008.md",
            "v3010_report": "docs/reports/v3010.md",
            "v3011_report": "docs/reports/v3011.md",
        },
        "bridge": {
            "control_path_ready": True,
            "bridge_probe_ok": True,
        },
        "device_health": {
            "version": {"build_tag": "v2321-usb-clean-identity-rodata", "resident_v2321": True},
            "status": {"transport_ready": True},
            "selftest": {"selftest_ok": True},
        },
        "host_usb_topology": {
            "host_hid_interface_count": 3,
            "host_hid_present": True,
            "host_cdc_interface_count": 4,
            "host_cdc_present": True,
            "a90_otg_keyboard_evidence": False,
        },
        "selector": {
            "decision": "frontier-selector-no-automatic-safe-unit",
            "first_track": "VIDEO",
            "first_status": "external-hardware-stimulus-required",
            "selector_external_stimulus_required": True,
            "v3010_flash_gate_assets_ready": True,
            "v3010_flash_gate_reports_ok": True,
            "v3010_external_hardware_wait_retained": True,
        },
        "reports": {
            "v3008_external_gate": True,
            "v3010_assets_ready": True,
            "v3010_reports_ok": True,
            "v3010_external_hardware_wait": True,
            "v3011_selector_external_gate": True,
            "v3011_selector_pass": True,
        },
    }


class NativeDoomInputLivePreconditionCurrentV3012Tests(unittest.TestCase):
    def test_runner_is_read_only_precondition_audit(self) -> None:
        script = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn('RUN_ID = "V3012"', script)
        self.assertIn("read-only current precondition audit", script)
        self.assertIn(runner.DECISION_WAIT, script)
        self.assertNotIn("native_init_flash.py", script)
        self.assertNotIn("EVIOCGRAB", script)
        self.assertNotIn("O_WRONLY", script)
        self.assertNotIn("sendevent", script)

    def test_parse_bridge_status_json_accepts_running_control_path(self) -> None:
        parsed = runner.parse_bridge_status_json("""{
          "bridge_process": "running",
          "bridge_probe": "connected-no-immediate-error",
          "port_listening": true,
          "selected_device": "/dev/serial/by-id/redacted",
          "serial_candidates": [{"exists": true}]
        }""")

        self.assertTrue(parsed["json_ok"])
        self.assertTrue(parsed["bridge_running"])
        self.assertTrue(parsed["port_listening"])
        self.assertTrue(parsed["bridge_probe_ok"])
        self.assertTrue(parsed["control_path_ready"])
        self.assertEqual(parsed["serial_candidate_count"], 1)

    def test_parse_health_usb_and_selector(self) -> None:
        version = runner.parse_version("A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)")
        self.assertTrue(version["resident_v2321"])

        selftest = runner.parse_selftest("selftest: pass=11 warn=1 fail=0\n08 PASS input event0=ok event3=ok\n11 PASS usb acm=yes")
        self.assertTrue(selftest["selftest_ok"])
        self.assertTrue(selftest["input_builtin_ok"])
        self.assertTrue(selftest["usb_acm_ok"])

        usb = runner.parse_lsusb_tree("""
/:  Bus 002.Port 001: Dev 001, Class=root_hub, Driver=xhci_hcd/4p, 20000M/x2
    |__ Port 003: Dev 019, If 0, Class=Communications, Driver=cdc_acm, 5000M
/:  Bus 003.Port 001: Dev 001, Class=root_hub, Driver=xhci_hcd/12p, 480M
    |__ Port 003: Dev 003, If 0, Class=Human Interface Device, Driver=usbhid, 12M
""")
        self.assertTrue(usb["host_hid_present"])
        self.assertTrue(usb["host_cdc_present"])
        self.assertFalse(usb["a90_otg_keyboard_evidence"])
        self.assertIn("not proof", usb["note"])

        selector = runner.parse_selector_json("""{
          "decision": "frontier-selector-no-automatic-safe-unit",
          "track_evaluations": [{
            "track": "VIDEO",
            "name": "doom-input",
            "status": "external-hardware-stimulus-required",
            "safe_actionable_now": false,
            "evidence": {
              "v3010_flash_gate_assets_ready": true,
              "v3010_flash_gate_reports_ok": true,
              "v3010_external_hardware_wait_retained": true,
              "v3010_v3004_live_actionable_now": false,
              "next_live_command": "run-v3004"
            }
          }]
        }""")
        self.assertTrue(selector["selector_external_stimulus_required"])
        self.assertTrue(selector["v3010_flash_gate_assets_ready"])
        self.assertFalse(selector["v3010_v3004_live_actionable_now"])

    def test_evaluate_keeps_gate_waiting_without_a90_otg_keyboard(self) -> None:
        payload = complete_payload()

        gate = runner.evaluate(payload)

        self.assertEqual(gate["decision"], runner.DECISION_WAIT)
        self.assertTrue(gate["resident_health_ok"])
        self.assertTrue(gate["gate_assets_ready"])
        self.assertTrue(gate["external_gate_retained"])
        self.assertFalse(gate["a90_otg_keyboard_evidence"])
        self.assertFalse(gate["v3004_live_actionable_now"])
        self.assertIn("No current evidence shows an A90-side OTG keyboard", "\n".join(gate["reasons"]))

    def test_evaluate_blocks_when_resident_health_is_bad(self) -> None:
        payload = complete_payload()
        payload["device_health"]["selftest"]["selftest_ok"] = False

        gate = runner.evaluate(payload)

        self.assertEqual(gate["decision"], runner.DECISION_BLOCKED)
        self.assertFalse(gate["resident_health_ok"])

    def test_render_report_records_current_precondition_and_safety(self) -> None:
        payload = complete_payload()
        payload["gate"] = runner.evaluate(payload)

        report = runner.render_report(payload)

        self.assertIn("Native Init V3012 DOOM Input Live Precondition Current Audit", report)
        self.assertIn(runner.DECISION_WAIT, report)
        self.assertIn("Bridge/control path ready: `1`", report)
        self.assertIn("V3010 flash-gate assets ready: `1`", report)
        self.assertIn("A90 OTG keyboard evdev evidence: `0`", report)
        self.assertIn("no flash", report)
        self.assertIn("host HID devices are not treated as A90 input evidence", report)


if __name__ == "__main__":
    unittest.main()
