"""Regression tests for a90_kernel_v2239_scalar_uprobe_timeline."""

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2239 = load_revalidation("a90_kernel_v2239_scalar_uprobe_timeline")


def make_timeline(base: float = 10.0, cap_gap: float = 61.0):
    offsets = {
        "wlfw_start": 0.0,
        "wlfw_service_request": 1.0,
        "libqmi_loop_client_init_ret": 1.25,
        "wlfw_cap_qmi": 1.0 + cap_gap,
        "wlfw_bdf_entry": 1.0 + cap_gap + 0.5,
        "wlfw_bdf_send_ret": 1.0 + cap_gap + 0.7,
        "wlfw_bdf_result_log": 1.0 + cap_gap + 1.0,
        "wlfw_worker_done_signal": 1.0 + cap_gap + 2.0,
        "wlfw_worker_post_done_wait": 1.0 + cap_gap + 2.1,
    }
    return [
        {
            "event": event,
            "ts": base + offset,
            "hit_count": index + 1,
            "group": "a90cnss",
            "surface": "uprobe",
        }
        for index, (event, offset) in enumerate(offsets.items())
    ]


def write_summary(path: Path, timeline, passed: bool = True):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "decision": "parser-pass" if passed else "parser-fail",
                "pass": passed,
                "total_hits": 123,
                "key_hit_event_total": len(timeline),
                "timeline": timeline,
            }
        ),
        encoding="utf-8",
    )


class TimelineEdges(unittest.TestCase):
    def test_first_edges_sorts_by_timestamp_and_defaults_hit_count_to_candidate_count(self):
        timeline = make_timeline()
        timeline.append(
            {
                "event": "wlfw_start",
                "ts": 9.0,
                "group": "a90libqmi",
                "surface": "libqmi_uprobe",
            }
        )

        edges = v2239.first_edges(timeline)

        self.assertEqual(edges["wlfw_start"].first_ts, 9.0)
        self.assertEqual(edges["wlfw_start"].hit_count, 2)
        self.assertEqual(edges["wlfw_start"].group, "a90libqmi")
        self.assertEqual(edges["wlfw_start"].surface, "libqmi_uprobe")

    def test_compute_deltas_returns_none_when_an_edge_is_missing(self):
        edges = v2239.first_edges(make_timeline())
        edges["wlfw_cap_qmi"] = v2239.Edge(
            event="wlfw_cap_qmi",
            first_ts=None,
            hit_count=0,
            group=None,
            surface=None,
        )

        deltas = v2239.compute_deltas(edges)

        self.assertEqual(deltas["service_request_after_start"], 1.0)
        self.assertIsNone(deltas["cap_qmi_after_service_request"])
        self.assertIsNone(deltas["bdf_entry_after_cap_qmi"])


class RunSummaryLoading(unittest.TestCase):
    def test_build_run_summary_requires_all_key_events_and_infers_observed_outcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary_path = Path(tmp) / "v9001-live/parser/summary.json"
            write_summary(summary_path, make_timeline(base=20.0))

            run = v2239.build_run_summary(summary_path)

        self.assertEqual(run.run_id, "v9001")
        self.assertEqual(run.parser_decision, "parser-pass")
        self.assertTrue(run.parser_pass)
        self.assertEqual(run.total_hits, 123)
        self.assertEqual(run.key_hit_event_total, len(v2239.KEY_EVENTS))
        self.assertEqual(run.deltas_sec["cap_qmi_after_service_request"], 61.0)
        self.assertEqual(run.outcome, "observed-no-wlan0")

    def test_build_run_summary_rejects_missing_key_event(self):
        timeline = [item for item in make_timeline() if item["event"] != "wlfw_bdf_entry"]
        with tempfile.TemporaryDirectory() as tmp:
            summary_path = Path(tmp) / "v9002-live/parser/summary.json"
            write_summary(summary_path, timeline)

            with self.assertRaisesRegex(ValueError, "wlfw_bdf_entry"):
                v2239.build_run_summary(summary_path)

    def test_infer_outcome_reads_helper_success_marker_and_v2233_tail_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            helper_run = Path(tmp) / "v9003-live"
            helper_device = helper_run / "device"
            helper_device.mkdir(parents=True)
            (helper_device / "helper_result.txt").write_text(
                "status: helper supervisor reached wlan0-ready\n",
                encoding="utf-8",
            )

            fwclass_run = Path(tmp) / "v2233-live-arbitrary"

            self.assertEqual(v2239.infer_outcome(helper_run, {"pass": False}), "wlan0-ready")
            self.assertEqual(
                v2239.infer_outcome(fwclass_run, {"pass": False}),
                "wlan0-ready-fwclass-tail",
            )


class ContractBuilder(unittest.TestCase):
    def make_run(self, run_id: str, cap_gap: float, outcome: str):
        edges = v2239.first_edges(make_timeline(cap_gap=cap_gap))
        return v2239.RunSummary(
            run_id=run_id,
            input_path=f"input/{run_id}.json",
            parser_decision="parser-pass",
            parser_pass=True,
            total_hits=99,
            key_hit_event_total=len(v2239.KEY_EVENTS),
            source_run_dir=f"runs/{run_id}",
            edge_coverage=edges,
            deltas_sec=v2239.compute_deltas(edges),
            outcome=outcome,
        )

    def test_summarize_delta_stats_counts_only_present_values(self):
        ok = self.make_run("v1", 61.0, "observed-no-wlan0")
        missing = self.make_run("v2", 62.0, "observed-no-wlan0")
        missing.deltas_sec["cap_qmi_after_service_request"] = None

        stats = v2239.summarize_delta_stats([ok, missing])

        self.assertEqual(stats["cap_qmi_after_service_request"], {
            "count": 1,
            "min": 61.0,
            "max": 61.0,
            "mean": 61.0,
            "spread": 0.0,
        })

    def test_build_contract_marks_stable_long_gap_and_wlan0_success_runs(self):
        runs = [
            self.make_run("v2229", 61.0, "observed-no-wlan0"),
            self.make_run("v2231", 61.1, "wlan0-ready"),
            self.make_run("v2233", 61.05, "wlan0-ready-fwclass-tail"),
        ]
        static_audit = {
            "decision": "static-pass",
            "classification_counts": {"record-pointer-chain-possible": 0},
            "qrtr_trace_defs": ["qrtr:qrtr_send"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            contract = v2239.build_contract(runs, static_audit, Path(tmp), "unit")

        self.assertTrue(contract["pass"])
        self.assertTrue(contract["safety"]["host_only"])
        self.assertFalse(contract["safety"]["device_io"])
        self.assertTrue(contract["interpretation"]["stable_wlfw_qmi_sequence"])
        self.assertTrue(contract["interpretation"]["stable_service_request_to_cap_qmi_gap"])
        self.assertEqual(contract["interpretation"]["wlan0_success_runs"], ["v2231", "v2233"])
        self.assertEqual(
            contract["contract"]["static_tracepoint_role"],
            "scalar lifecycle correlation only",
        )
        self.assertEqual(
            contract["interpretation"]["v2233_distinguishing_tail"],
            "post-FW_READY boot_wlan + firmware_class tail, not a different WLFW/QMI edge order",
        )

    def test_build_contract_fails_when_any_parser_failed(self):
        runs = [
            self.make_run("v1", 61.0, "observed-no-wlan0"),
            self.make_run("v2", 61.0, "observed-no-wlan0"),
        ]
        runs[1] = v2239.RunSummary(
            **{**runs[1].__dict__, "parser_pass": False}
        )

        with tempfile.TemporaryDirectory() as tmp:
            contract = v2239.build_contract(
                runs,
                {"classification_counts": {}},
                Path(tmp),
                "unit",
            )

        self.assertFalse(contract["pass"])
        self.assertEqual(
            contract["decision"],
            "v2239-scalar-uprobe-timeline-contract-incomplete",
        )


if __name__ == "__main__":
    unittest.main()
