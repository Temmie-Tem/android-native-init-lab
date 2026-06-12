"""Regression tests for native_kernel_wlan_tracepoint_catalog_v2218."""

import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2218 = load_revalidation("native_kernel_wlan_tracepoint_catalog_v2218")

BASE = 0xFFFFFF8008000000


class TracepointCatalogParsers(unittest.TestCase):
    def test_clean_cmdv1_text_removes_control_and_linker_noise(self):
        raw = (
            "a90:/# prompt\n"
            "A90P1 BEGIN\n"
            "cmdv1x shell stuff\n"
            "WARNING: linker: Warning: failed to find generated linker configuration\n"
            "real:line\n"
            "\n"
            "[done]\n"
            "run: pid=123\n"
            "next=line\n"
            "[exit 0]\n"
        )

        cleaned = v2218.clean_cmdv1_text(raw)

        self.assertEqual(cleaned, "real:line\nnext=line\n")

    def test_parse_events_filters_invalid_lines_and_preserves_group_event(self):
        text = "a90cnss:wlfw_start\ninvalid\n:missing_group\ngroup:\ncfg80211:rdev_return_int\n"

        self.assertEqual(v2218.parse_events(text), ["a90cnss:wlfw_start", "cfg80211:rdev_return_int"])

    def test_category_for_classifies_frontier_groups(self):
        cases = {
            "a90cnss:wlfw_start": "a90cnss_wlfw",
            "a90libqmi:libqmi_client_init_instance_entry": "a90_qmi_pm",
            "a90pmsrv:pm_service_post_ack_qmi_restart_ind_call": "a90_qmi_pm",
            "cfg80211:rdev_scan": "wifi_kernel",
            "msm_pil_event:pil_notif": "pil_subsys",
            "dfc:dfc_qmi_tc": "qmi_transport",
            "net:net_dev_queue": "net_stack",
            "timer:timer_start": "scheduler_context",
            "clk:clk_enable": "power_clock",
            "misc:unrelated": None,
        }

        for event, expected in cases.items():
            with self.subTest(event=event):
                self.assertEqual(v2218.category_for(event), expected)

    def test_parse_format_extracts_event_fields_probe_ip_and_arrays(self):
        fmt = (
            "name: wlfw_bdf_entry\n"
            "ID: 1331\n"
            "format:\n"
            "\tfield:unsigned short common_type;\toffset:0;\tsize:2;\tsigned:0;\n"
            "\tfield:unsigned long __probe_ip;\toffset:8;\tsize:8;\tsigned:0;\n"
            "\tfield:int bdf_type;\toffset:16;\tsize:4;\tsigned:1;\n"
            "\tfield:char fw_name[32];\toffset:20;\tsize:32;\tsigned:1;\n"
        )

        parsed = v2218.parse_format(fmt)

        self.assertTrue(parsed["has_probe_ip"])
        self.assertEqual(parsed["field_names"], ["common_type", "__probe_ip", "bdf_type", "fw_name"])
        self.assertEqual(parsed["event_fields"], [
            {"type": "unsigned long", "name": "__probe_ip", "offset": 8, "size": 8, "signed": False},
            {"type": "int", "name": "bdf_type", "offset": 16, "size": 4, "signed": True},
            {"type": "char", "name": "fw_name", "offset": 20, "size": 32, "signed": True},
        ])


class SymbolAndExtractHelpers(unittest.TestCase):
    def test_load_system_map_skips_absolute_symbols_and_symbolize_with_slide(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "System.map"
            path.write_text(
                "nothex T ignored\n"
                f"{BASE + 0x1000:016x} T alpha\n"
                f"{BASE + 0x1800:016x} A absolute_ignored\n"
                f"{BASE + 0x2000:016x} W beta\n",
                encoding="utf-8",
            )
            symbols = v2218.load_system_map(path)

        self.assertEqual([symbol["name"] for symbol in symbols], ["alpha", "beta"])
        hit = v2218.symbolize(BASE + 0x1010 + 0x84EF4, symbols, 0x84EF4)
        self.assertEqual(hit, {
            "runtime": f"0x{BASE + 0x1010 + 0x84EF4:016x}",
            "static": f"0x{BASE + 0x1010:016x}",
            "symbol": "alpha",
            "offset": 0x10,
        })
        self.assertIsNone(v2218.symbolize(BASE + 0x0FFF, symbols, 0))

    def test_parse_extract_output_cleans_counts_last_result_and_symbolizes(self):
        symbols = [
            {"address": BASE + 0x1000, "type": "T", "name": "alpha"},
            {"address": BASE + 0x2000, "type": "T", "name": "beta"},
        ]
        last_runtime = BASE + 0x1010 + v2218.EXACT_SLIDE
        text = (
            "a90:/# prompt\n"
            "result=extract-pass\n"
            "attach_attempted=1\n"
            "count=23\n"
            f"last={last_runtime}\n"
        )

        parsed = v2218.parse_extract_output(text, symbols, v2218.EXACT_SLIDE)

        self.assertEqual(parsed["count"], 23)
        self.assertEqual(parsed["last"], f"0x{last_runtime:016x}")
        self.assertEqual(parsed["result"], "extract-pass")
        self.assertTrue(parsed["attach_attempted"])
        self.assertEqual(parsed["symbolized_last"]["symbol"], "alpha")
        self.assertEqual(parsed["symbolized_last"]["offset"], 0x10)
        self.assertIn("count=23", parsed["cleaned_stdout"])

    def test_parse_extract_output_defaults_missing_count_and_last(self):
        parsed = v2218.parse_extract_output("result=attach-failed errno=4\n", [], v2218.EXACT_SLIDE)

        self.assertEqual(parsed["count"], 0)
        self.assertEqual(parsed["last"], "0x0000000000000000")
        self.assertEqual(parsed["result"], "attach-failed errno=4")
        self.assertFalse(parsed["attach_attempted"])
        self.assertIsNone(parsed["symbolized_last"])

    def test_residual_state_reflects_device_touch_selftest_and_bpf_attach(self):
        untouched = v2218.residual_state({"steps": [], "selftest_fail0": False, "safety": {"bpf_tracepoint_attach": False}})
        touched_ok = v2218.residual_state({"steps": [{"name": "sample"}], "selftest_fail0": True, "safety": {"bpf_tracepoint_attach": True}})
        touched_bad = v2218.residual_state({"steps": [{"name": "sample"}], "selftest_fail0": False, "safety": {"bpf_tracepoint_attach": True}})

        self.assertFalse(untouched["device_touched"])
        self.assertFalse(untouched["cleanup_required"])
        self.assertTrue(touched_ok["device_touched"])
        self.assertTrue(touched_ok["selftest_ok"])
        self.assertTrue(touched_ok["bpf_attach"])
        self.assertFalse(touched_ok["cleanup_required"])
        self.assertTrue(touched_bad["cleanup_required"])
        self.assertEqual(touched_bad["residual_risk"], "post-selftest-incomplete")
        self.assertFalse(touched_bad["flash_reboot"])
        self.assertFalse(touched_bad["probe_write_user_executed"])


class DataclassHelpers(unittest.TestCase):
    def test_step_result_ok_property(self):
        ok = v2218.StepResult("ok", ["true"], 0, 0.1, "stdout", "stderr")
        bad = v2218.StepResult("bad", ["false"], 1, 0.1, "stdout", "stderr")

        self.assertTrue(ok.ok)
        self.assertFalse(bad.ok)


if __name__ == "__main__":
    unittest.main()
