from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


wsta25 = load_script("workspace/public/src/scripts/server-distro/run_wsta25_confirmed_autoconnect_live.py")
wsta43 = load_script("workspace/public/src/scripts/server-distro/run_wsta43_orchestrated_native_uplink_dpublic.py")
RUNBOOK = Path("docs/operations/A90_WSTA_NATIVE_UPLINK_DPUBLIC_OPERATOR_RUNBOOK.md")


class ServerDistroWsta49OperatorRunbookTests(unittest.TestCase):
    def test_runbook_has_operator_publish_and_aggregate_flow(self) -> None:
        text = RUNBOOK.read_text(encoding="utf-8")

        self.assertIn("run_wsta45_appliance_operator.py", text)
        self.assertIn("--print-publish-template", text)
        self.assertIn("--mode publish", text)
        self.assertIn("--use-native-uplink-profile", text)
        self.assertIn("--allow-operator-live", text)
        self.assertIn("--allow-native-reboot", text)
        self.assertIn("--allow-public-live", text)
        self.assertIn("--ack-credentialed-wifi", text)
        self.assertIn("--ack-public-exposure", text)
        self.assertIn("run_wsta48_redacted_result_aggregate.py", text)
        self.assertIn("run_wsta88_persistent_operator_workflow.py", text)
        self.assertIn("run_wsta108_operator_server_status.py", text)
        self.assertIn("--emit-server-status", text)
        self.assertIn("SERVER_PROFILE_READY_DEFAULT_OFF", text)
        self.assertIn("redaction_guard.ok=true", text)
        self.assertIn("all_pass=true", text)

    def test_runbook_keeps_live_values_placeholder_only(self) -> None:
        text = RUNBOOK.read_text(encoding="utf-8")
        lowered = text.lower()

        self.assertIn("<native-confirm-token>", text)
        self.assertIn("<public-confirm-token>", text)
        self.assertNotIn(wsta25.NATIVE_CONFIRM_TOKEN, text)
        self.assertNotIn(wsta43.PUBLIC_CONFIRM_TOKEN, text)
        self.assertNotIn("trycloudflare.com", lowered)
        self.assertNotIn("ssid=", lowered)
        self.assertNotIn("psk=", lowered)

    def test_runbook_includes_health_checks_stop_conditions_and_non_goals(self) -> None:
        text = RUNBOOK.read_text(encoding="utf-8")

        self.assertIn("a90_bridge.py status --json", text)
        self.assertIn("a90ctl.py version", text)
        self.assertIn("a90ctl.py status", text)
        self.assertIn("a90ctl.py selftest", text)
        self.assertIn("a90ctl.py wifi status", text)
        self.assertIn("Stop Conditions", text)
        self.assertIn("redaction_guard.ok", text)
        self.assertIn("selftest fail=0", text)
        self.assertIn("No `native_init_flash.py` invocation belongs", text)
        self.assertIn("No always-on public exposure", text)
        self.assertIn("Do not commit private run JSON", text)


if __name__ == "__main__":
    unittest.main()
