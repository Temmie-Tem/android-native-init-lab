"""Regression tests for a90_kernel_v2244_semantic_timeline_merger."""

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2244 = load_revalidation("a90_kernel_v2244_semantic_timeline_merger")


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def edge(event: str, ts: float = 1.0):
    return {
        "event": event,
        "group": "a90cnss",
        "surface": "uprobe",
        "first_ts": ts,
        "hit_count": 1,
    }


def semantic(event: str, confidence: str = "high", alignment: str = "aligned_entry_prologue"):
    return {
        "event": event,
        "object": "a90cnss",
        "event_role": "entry" if event == "wlfw_start" else "protocol_edge",
        "instruction_class": "frame_prologue" if event == "wlfw_start" else "load",
        "alignment": alignment,
        "confidence": confidence,
    }


class MergeHelpers(unittest.TestCase):
    def test_semantic_by_event_uses_key_events_only_and_later_rows_override(self):
        summary = {
            "key_events": [
                semantic("wlfw_start", confidence="medium"),
                semantic("wlfw_start", confidence="high"),
            ],
            "review_needed": [semantic("ignored")],
        }

        rows = v2244.semantic_by_event(summary)

        self.assertEqual(set(rows), {"wlfw_start"})
        self.assertEqual(rows["wlfw_start"]["confidence"], "high")

    def test_evidence_strength_maps_confidence_to_strength_buckets(self):
        self.assertEqual(v2244.evidence_strength(None), "missing_semantics")
        self.assertEqual(v2244.evidence_strength({"confidence": "high"}), "strong")
        self.assertEqual(v2244.evidence_strength({"confidence": "medium"}), "marker")
        self.assertEqual(v2244.evidence_strength({"confidence": "low"}), "weak")

    def test_merge_edge_preserves_timing_and_adds_public_semantic_metadata(self):
        merged = v2244.merge_edge(edge("wlfw_start", ts=3.5), semantic("wlfw_start"))

        self.assertEqual(merged["event"], "wlfw_start")
        self.assertEqual(merged["first_ts"], 3.5)
        self.assertTrue(merged["semantic_found"])
        self.assertEqual(merged["evidence_strength"], "strong")
        self.assertEqual(merged["event_role"], "entry")
        self.assertEqual(merged["object"], "a90cnss")

    def test_merge_edge_marks_missing_semantics_without_crashing(self):
        merged = v2244.merge_edge(edge("missing"), None)

        self.assertFalse(merged["semantic_found"])
        self.assertEqual(merged["evidence_strength"], "missing_semantics")
        self.assertIsNone(merged["event_role"])


class RunAndOutcomeSummaries(unittest.TestCase):
    def test_summarize_run_counts_strengths_missing_and_weak_edges(self):
        run = {
            "outcome": "observed-no-wlan0",
            "deltas_sec": {"a": 1.0},
            "edges": {
                "wlfw_start": edge("wlfw_start"),
                "wlfw_cap_qmi": edge("wlfw_cap_qmi"),
                "unknown": edge("unknown"),
            },
        }
        semantics = {
            "wlfw_start": semantic("wlfw_start", confidence="high"),
            "wlfw_cap_qmi": semantic("wlfw_cap_qmi", confidence="low", alignment="needs_manual_context"),
        }

        summary = v2244.summarize_run("v1", run, semantics)

        self.assertEqual(summary["edge_count"], 3)
        self.assertEqual(summary["strong_edge_count"], 1)
        self.assertEqual(summary["weak_edge_count"], 1)
        self.assertEqual(summary["missing_semantic_count"], 1)
        self.assertEqual(summary["missing_semantics"], ["unknown"])
        self.assertEqual(summary["weak_edges"], ["wlfw_cap_qmi"])
        self.assertEqual(summary["deltas_sec"], {"a": 1.0})

    def test_compare_outcomes_detects_edge_and_semantic_signature_differences(self):
        runs = {
            "v1": {
                "run_id": "v1",
                "outcome": "observed",
                "edges": {
                    "a": {"evidence_strength": "strong", "event_role": "entry", "alignment": "x", "confidence": "high"},
                    "b": {"evidence_strength": "marker", "event_role": "state", "alignment": "y", "confidence": "medium"},
                },
            },
            "v2": {
                "run_id": "v2",
                "outcome": "ready",
                "edges": {
                    "a": {"evidence_strength": "strong", "event_role": "entry", "alignment": "x", "confidence": "high"},
                    "c": {"evidence_strength": "strong", "event_role": "entry", "alignment": "z", "confidence": "high"},
                },
            },
        }

        comparison = v2244.compare_outcomes(runs)

        self.assertEqual(comparison["outcomes"], {"observed": ["v1"], "ready": ["v2"]})
        self.assertEqual(comparison["common_edges"], ["a"])
        self.assertEqual(comparison["union_edge_count"], 3)
        self.assertFalse(comparison["edge_sets_identical_across_runs"])
        self.assertFalse(comparison["semantic_signatures_identical_across_runs"])
        self.assertEqual(comparison["differing_semantic_edges"], ["c"])


class SummaryBuilder(unittest.TestCase):
    def make_args(self, root: Path, timeline_payload, semantic_payload):
        v2239_summary = root / "v2239-summary.json"
        v2239_timeline = root / "v2239-timeline.json"
        v2243_summary = root / "v2243-summary.json"
        write_json(v2239_summary, {"decision": "v2239-pass"})
        write_json(v2239_timeline, timeline_payload)
        write_json(v2243_summary, semantic_payload)
        return argparse.Namespace(
            label="unit",
            v2239_summary=v2239_summary,
            v2239_timeline=v2239_timeline,
            v2243_summary=v2243_summary,
        )

    def test_build_summary_passes_when_all_edges_have_non_weak_semantics(self):
        timeline = {
            "v1": {
                "outcome": "observed-no-wlan0",
                "deltas_sec": {},
                "edges": {
                    "wlfw_start": edge("wlfw_start"),
                    "wlfw_cap_qmi": edge("wlfw_cap_qmi"),
                },
            },
            "v2": {
                "outcome": "wlan0-ready",
                "deltas_sec": {},
                "edges": {
                    "wlfw_start": edge("wlfw_start"),
                    "wlfw_cap_qmi": edge("wlfw_cap_qmi"),
                },
            },
        }
        semantics = {
            "decision": "v2243-pass",
            "key_events": [
                semantic("wlfw_start", confidence="high"),
                semantic("wlfw_cap_qmi", confidence="medium", alignment="marker_edge"),
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir = root / "out"
            out_dir.mkdir()
            summary = v2244.build_summary(self.make_args(root, timeline, semantics), out_dir)
            merged_path = root / summary["semantic_timeline"]["path"]
            merged = json.loads(merged_path.read_text(encoding="utf-8"))

        self.assertTrue(summary["pass"])
        self.assertEqual(summary["decision"], "v2244-semantic-timeline-merge-pass")
        self.assertEqual(summary["run_count"], 2)
        self.assertEqual(summary["semantic_coverage_count"], 4)
        self.assertEqual(summary["strength_counts"], {"marker": 2, "strong": 2})
        self.assertTrue(summary["comparison"]["edge_sets_identical_across_runs"])
        self.assertFalse(summary["semantic_timeline"]["raw_disassembly_published"])
        self.assertIn("runs", merged)

    def test_build_summary_requests_review_for_missing_or_weak_semantics(self):
        timeline = {
            "v1": {
                "outcome": "observed-no-wlan0",
                "deltas_sec": {},
                "edges": {
                    "wlfw_start": edge("wlfw_start"),
                    "wlfw_cap_qmi": edge("wlfw_cap_qmi"),
                    "unknown": edge("unknown"),
                },
            }
        }
        semantics = {
            "decision": "v2243-review",
            "key_events": [
                semantic("wlfw_start", confidence="high"),
                semantic("wlfw_cap_qmi", confidence="low", alignment="needs_manual_context"),
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir = root / "out"
            out_dir.mkdir()
            summary = v2244.build_summary(self.make_args(root, timeline, semantics), out_dir)

        self.assertFalse(summary["pass"])
        self.assertEqual(summary["decision"], "v2244-semantic-timeline-merge-review-needed")
        self.assertEqual(summary["missing_semantic_edges"], ["unknown"])
        self.assertEqual(summary["weak_edges"], ["wlfw_cap_qmi"])
        self.assertEqual(summary["low_confidence_key_edges"], ["wlfw_cap_qmi"])
        self.assertEqual(summary["role_counts"]["none"], 1)


if __name__ == "__main__":
    unittest.main()
