"""Regression tests for a90_kernel_v2220_helper_summary_trace_parser.

Pins deterministic parser helpers and aggregation behavior without reading real
artifacts or touching a device.
"""

import unittest

from _loader import load_revalidation

parser = load_revalidation("a90_kernel_v2220_helper_summary_trace_parser")


class ScalarHelpers(unittest.TestCase):
    def test_as_int_accepts_bool_int_decimal_and_hex(self):
        cases = [
            (True, 1),
            (False, 0),
            (7, 7),
            (" 11 ", 11),
            ("0x10", 16),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(parser.as_int(value, default=-9), expected)

    def test_as_int_uses_default_for_invalid_values(self):
        for value in ("bad", None, object()):
            with self.subTest(value=repr(value)):
                self.assertEqual(parser.as_int(value, default=-9), -9)

    def test_extract_ts_reads_trace_style_timestamp(self):
        line = "task-1 [000] .... 12.345: a90cnss:wlfw_start: (0x1) args"
        self.assertEqual(parser.extract_ts(line), 12.345)
        self.assertIsNone(parser.extract_ts("no timestamp here"))


class JsonAndNameHelpers(unittest.TestCase):
    def test_flatten_json_yields_dotted_paths_for_dicts_and_lists(self):
        value = {"a": [1, {"b": False}], "c": "x"}
        self.assertEqual(
            list(parser.flatten_json(value)),
            [("a.0", 1), ("a.1.b", False), ("c", "x")],
        )

    def test_parse_legacy_nonlog_key_extracts_event_and_suffix(self):
        self.assertEqual(
            parser.parse_legacy_nonlog_key("root.nonlog_wlfw_start_hit_count"),
            ("wlfw_start", "hit_count"),
        )
        self.assertEqual(
            parser.parse_legacy_nonlog_key("nonlog_uprobe_first_hit_line"),
            ("uprobe", "first_hit_line"),
        )
        self.assertIsNone(parser.parse_legacy_nonlog_key("nonlog_wlfw_start_unknown"))
        self.assertIsNone(parser.parse_legacy_nonlog_key("other_key"))

    def test_split_group_event_and_surface_mapping(self):
        self.assertEqual(parser.split_group_event("a90libqmi:event"), ("a90libqmi", "event"))
        self.assertEqual(parser.split_group_event("bare_event"), ("a90cnss", "bare_event"))

        self.assertEqual(parser.group_to_surface("a90cnss"), "uprobe")
        self.assertEqual(parser.group_to_surface("a90libqmi"), "libqmi_uprobe")
        self.assertEqual(parser.group_to_surface("a90pmsrv"), "pm_server_uprobe")
        self.assertEqual(parser.group_to_surface("custom"), "custom")

        self.assertEqual(parser.event_group("uprobe"), "a90cnss")
        self.assertEqual(parser.event_group("libqmi_uprobe"), "a90libqmi")
        self.assertEqual(parser.event_group("pm_server_uprobe"), "a90pmsrv")
        self.assertEqual(parser.event_group("custom"), "custom")


class Aggregate(unittest.TestCase):
    def test_aggregate_rolls_up_hits_timeline_key_events_and_nohit_sources(self):
        events = [
            parser.ParsedEvent(
                source_path="p1",
                source_kind="helper_summary_text",
                surface="uprobe",
                group="a90cnss",
                event="wlfw_start",
                fields={
                    "hit_count": "2",
                    "first_hit_line": "task-1 [000] .... 2.000: a90cnss:wlfw_start: (0x1)",
                },
            ),
            parser.ParsedEvent(
                source_path="p2",
                source_kind="json_embedded_trace_line",
                surface="uprobe",
                group="a90cnss",
                event="wlfw_start",
                fields={
                    "hit_count": 3,
                    "first_hit_line": "task-1 [000] .... 1.000: a90cnss:wlfw_start: (0x1)",
                },
            ),
            parser.ParsedEvent(
                source_path="p1",
                source_kind="legacy_manifest_nonlog",
                surface="nonlog",
                group="a90cnss",
                event="_surface_nonlog",
                fields={"hit_count": "4"},
            ),
            parser.ParsedEvent(
                source_path="p3",
                source_kind="v2219_summary",
                surface="pm_server_uprobe",
                group="a90pmsrv",
                event="pm_service_post_ack_qmi_restart_ind_call",
                fields={"hit_count": 0},
            ),
        ]

        result = parser.aggregate(events)

        self.assertEqual(result["event_total"], 3)
        self.assertEqual(result["surface_rollup_total"], 1)
        self.assertEqual(result["surface_rollup_hits"], 4)
        self.assertEqual(result["hit_event_total"], 1)
        self.assertEqual(result["key_hit_event_total"], 1)
        self.assertEqual(result["total_hits"], 5)
        self.assertEqual(result["sources_total"], 3)
        self.assertEqual(result["v2219_nohit_sources"], ["p3"])

        wlfw = result["events_by_key"]["uprobe:wlfw_start"]
        self.assertEqual(wlfw["total_hit_count"], 5)
        self.assertEqual(wlfw["first_ts"], 1.0)
        self.assertEqual(wlfw["first_hit_line"], "task-1 [000] .... 1.000: a90cnss:wlfw_start: (0x1)")
        self.assertTrue(wlfw["key_event"])

        self.assertEqual([item["ts"] for item in result["timeline"]], [1.0, 2.0])
        self.assertEqual(result["top_hit_events"][0]["event"], "wlfw_start")


if __name__ == "__main__":
    unittest.main()
