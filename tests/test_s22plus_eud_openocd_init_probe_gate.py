import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_eud_openocd_init_probe_gate.py")
DRAFT = Path("docs/operations/S22PLUS_EUD_OPENOCD_INIT_PROBE_AGENTS_EXCEPTION_DRAFT_2026-07-08.md")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_eud_openocd_init_probe_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S22PlusEudOpenocdInitProbeGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_openocd_probe_args_include_expected_script_roots_and_cfgs(self):
        argv = self.module.openocd_probe_args(
            Path("/tmp/openocd"),
            Path("/tmp/private-scripts"),
            Path("/tmp/public-scripts"),
        )
        self.assertIn("-s", argv)
        self.assertIn("/tmp/private-scripts", argv)
        self.assertIn("/tmp/public-scripts", argv)
        self.assertIn("interface/eud.cfg", argv)
        self.assertIn("target/qualcomm/sm8450_s22plus_romtable.cfg", argv)
        self.assertEqual(argv[-6:], ["-c", "init", "-c", "targets", "-c", "shutdown"])

    def test_policy_draft_has_required_markers(self):
        text = DRAFT.read_text(encoding="utf-8")
        self.assertEqual(self.module.missing_policy_markers(text), [])

    def test_policy_marker_check_rejects_missing_ack_and_boundaries(self):
        text = "S22+ EUD OpenOCD Init Probe target/qualcomm/sm8450_s22plus_romtable.cfg"
        missing = self.module.missing_policy_markers(text)
        self.assertIn(self.module.LIVE_ACK_TOKEN, missing)
        self.assertIn("no partition write", missing)
        self.assertIn("bounded OpenOCD init", missing)

    def test_unrelated_consumed_text_does_not_poison_policy_marker_check(self):
        text = DRAFT.read_text(encoding="utf-8") + "\nConsumed/retired unrelated exception text.\n"
        self.assertEqual(self.module.missing_policy_markers(text), [])

    def test_preflight_summary_waits_for_endpoint_when_cfg_is_ready(self):
        cfg_summary = {"classification": {"result": "sm8450_cfg_draft_ready_romtable_dbgbase"}}
        host_summary = {
            "classification": {"result": "waiting_for_eud_enumeration_or_hardware"},
            "host": {"host_eud_usb_hint": False},
        }
        result = self.module.summarize_preflight(cfg_summary, host_summary)
        self.assertEqual(result["result"], "waiting_for_eud_enumeration_or_hardware")
        self.assertFalse(result["ready"])

    def test_preflight_summary_ready_only_when_host_audit_ready(self):
        cfg_summary = {"classification": {"result": "sm8450_cfg_draft_ready_romtable_dbgbase"}}
        host_summary = {
            "classification": {"result": "host_openocd_eud_ready_to_probe"},
            "host": {"host_eud_usb_hint": True},
        }
        result = self.module.summarize_preflight(cfg_summary, host_summary)
        self.assertEqual(result["result"], "ready_for_bounded_openocd_init_probe")
        self.assertTrue(result["ready"])


if __name__ == "__main__":
    unittest.main()
