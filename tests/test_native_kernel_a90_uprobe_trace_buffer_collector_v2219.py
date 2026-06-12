"""Regression tests for native_kernel_a90_uprobe_trace_buffer_collector_v2219."""

import unittest

from _loader import load_revalidation

v2219 = load_revalidation("native_kernel_a90_uprobe_trace_buffer_collector_v2219")


class EventStateParsers(unittest.TestCase):
    def test_clean_cmdv1_text_removes_control_and_linker_noise(self):
        raw = (
            "a90:/# prompt\n"
            "A90P1 BEGIN\n"
            "cmdv1x run shell\n"
            "WARNING: linker: Warning: failed to find generated linker configuration\n"
            "EVENT a90cnss:wlfw_start\n"
            "\n"
            "[done]\n"
            "run: pid=99\n"
            "exists=1\n"
            "[exit 0]\n"
        )

        cleaned = v2219.clean_cmdv1_text(raw)

        self.assertEqual(cleaned, "EVENT a90cnss:wlfw_start\nexists=1\n")

    def test_parse_event_state_handles_inline_and_pending_cat_values(self):
        raw = (
            "EVENT a90cnss:wlfw_start\n"
            "exists=1\n"
            "id=123\n"
            "enable=1\n"
            "EVENT a90pmsrv:pm_service_post_ack_qmi_restart_ind_call\n"
            "exists=1\n"
            "id=\n"
            "456\n"
            "enable=\n"
            "0\n"
            "EVENT a90libqmi:missing\n"
            "exists=0\n"
        )

        states = v2219.parse_event_state(raw)

        self.assertEqual(states["a90cnss:wlfw_start"], {"exists": True, "id": 123, "enable": "1"})
        self.assertEqual(
            states["a90pmsrv:pm_service_post_ack_qmi_restart_ind_call"],
            {"exists": True, "id": 456, "enable": "0"},
        )
        self.assertEqual(states["a90libqmi:missing"], {"exists": False, "id": None, "enable": None})

    def test_event_name_map_groups_by_short_event_name(self):
        states = {
            "a90cnss:wlfw_start": {},
            "a90libqmi:libqmi_get_service_list_lookup_call": {},
            "a90pmsrv:wlfw_start": {},
        }

        mapping = v2219.event_name_map(states)

        self.assertEqual(mapping["wlfw_start"], ["a90cnss", "a90pmsrv"])
        self.assertEqual(mapping["libqmi_get_service_list_lookup_call"], ["a90libqmi"])


class TraceLineParsers(unittest.TestCase):
    def test_parse_args_text_handles_quoted_and_unquoted_values(self):
        parsed = v2219.parse_args_text('svc=69 rc=-11 name="wlfw service" ptr=0xffffff8008123456')

        self.assertEqual(parsed, {
            "svc": "69",
            "rc": "-11",
            "name": "wlfw service",
            "ptr": "0xffffff8008123456",
        })

    def test_parse_trace_lines_infers_unique_group_and_marks_kernel_ips(self):
        states = {
            "a90cnss:wlfw_start": {"exists": True, "id": 1, "enable": "1"},
            "a90pmsrv:pm_service_post_ack_qmi_restart_ind_call": {"exists": True, "id": 2, "enable": "1"},
        }
        text = (
            "cnss-daemon-123 [001] .... 12.345678: a90cnss:wlfw_start: "
            '(0xffffff8008123456) svc=69 name="wlfw"\n'
            "pm-service-77 [003] d... 13.000000: pm_service_post_ack_qmi_restart_ind_call: "
            "(0x0000007f12345678) rc=-1\n"
            "not a trace line\n"
        )

        rows = v2219.parse_trace_lines(text, states)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["group"], "a90cnss")
        self.assertEqual(rows[0]["full_name"], "a90cnss:wlfw_start")
        self.assertEqual(rows[0]["task"], "cnss-daemon")
        self.assertEqual(rows[0]["pid"], 123)
        self.assertEqual(rows[0]["cpu"], 1)
        self.assertEqual(rows[0]["timestamp"], 12.345678)
        self.assertEqual(rows[0]["probe_ip"], "0xffffff8008123456")
        self.assertTrue(rows[0]["probe_ip_kernel_va"])
        self.assertEqual(rows[0]["args"], {"svc": "69", "name": "wlfw"})
        self.assertEqual(rows[1]["group"], "a90pmsrv")
        self.assertEqual(rows[1]["full_name"], "a90pmsrv:pm_service_post_ack_qmi_restart_ind_call")
        self.assertFalse(rows[1]["probe_ip_kernel_va"])
        self.assertEqual(rows[1]["args"], {"rc": "-1"})

    def test_parse_trace_lines_marks_ambiguous_unqualified_event_unknown(self):
        states = {
            "a90cnss:shared_event": {"exists": True},
            "a90pmsrv:shared_event": {"exists": True},
        }
        text = "task-1 [000] .... 1.000000: shared_event: (0xffffff8008000000) key=value\n"

        rows = v2219.parse_trace_lines(text, states)

        self.assertEqual(rows[0]["group"], "unknown")
        self.assertEqual(rows[0]["full_name"], "shared_event")
        self.assertEqual(rows[0]["args"], {"key": "value"})

    def test_summarize_hits_counts_first_last_and_ip_classes(self):
        rows = [
            {"full_name": "a90cnss:wlfw_start", "line": "first", "probe_ip_kernel_va": True},
            {"full_name": "a90pmsrv:pm_ack", "line": "only", "probe_ip_kernel_va": False},
            {"full_name": "a90cnss:wlfw_start", "line": "last", "probe_ip_kernel_va": True},
        ]

        summary = v2219.summarize_hits(rows)

        self.assertEqual(summary["total_hits"], 3)
        self.assertEqual(summary["event_counts"], {"a90cnss:wlfw_start": 2, "a90pmsrv:pm_ack": 1})
        self.assertEqual(summary["first_hits"], {"a90cnss:wlfw_start": "first", "a90pmsrv:pm_ack": "only"})
        self.assertEqual(summary["last_hits"], {"a90cnss:wlfw_start": "last", "a90pmsrv:pm_ack": "only"})
        self.assertEqual(summary["kernel_probe_ip_count"], 2)
        self.assertEqual(summary["user_probe_ip_count"], 1)


class SafetyStateHelpers(unittest.TestCase):
    def test_residual_state_is_fail_closed_on_missing_selftest_after_device_touch(self):
        untouched = v2219.residual_state({"steps": [], "selftest_fail0": False})
        touched_ok = v2219.residual_state({"steps": [{"name": "post-selftest"}], "selftest_fail0": True})
        touched_bad = v2219.residual_state({"steps": [{"name": "post-selftest"}], "selftest_fail0": False})

        self.assertFalse(untouched["device_touched"])
        self.assertFalse(untouched["cleanup_required"])
        self.assertTrue(touched_ok["device_touched"])
        self.assertTrue(touched_ok["selftest_ok"])
        self.assertFalse(touched_ok["cleanup_required"])
        self.assertTrue(touched_bad["cleanup_required"])
        self.assertEqual(touched_bad["residual_risk"], "post-selftest-incomplete")
        self.assertFalse(touched_bad["tracefs_control_write"])
        self.assertFalse(touched_bad["bpf_attach"])
        self.assertFalse(touched_bad["probe_write_user_executed"])
        self.assertFalse(touched_bad["wifi_scan_connect"])

    def test_step_result_ok_property(self):
        ok = v2219.StepResult("ok", ["true"], 0, 0.01, "stdout", "stderr")
        bad = v2219.StepResult("bad", ["false"], 2, 0.01, "stdout", "stderr")

        self.assertTrue(ok.ok)
        self.assertFalse(bad.ok)

    def test_is_kernel_va_threshold(self):
        self.assertFalse(v2219.is_kernel_va(0xFFFFFF7FFFFFFFFF))
        self.assertTrue(v2219.is_kernel_va(0xFFFFFF8000000000))


if __name__ == "__main__":
    unittest.main()
