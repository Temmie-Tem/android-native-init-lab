"""Regression tests for the REPL run-timing events schema analyzer."""

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script

timing = load_script("workspace/public/src/scripts/analysis/analyze_repl_run_timing.py")


def timeline_events(base: str = "2026-07-01T10:00:00+00:00") -> dict:
    del base
    return {
        "events": [
            {"name": "candidate_flash_start", "timestamp_utc": "2026-07-01T10:00:00+00:00"},
            {"name": "candidate_flash_done", "timestamp_utc": "2026-07-01T10:01:05+00:00"},
            {"name": "candidate_boot_ready", "timestamp_utc": "2026-07-01T10:01:15+00:00"},
            {"name": "live_session_start", "timestamp_utc": "2026-07-01T10:01:20+00:00"},
            {"name": "live_session_end", "timestamp_utc": "2026-07-01T10:01:50+00:00"},
            {"name": "rollback_flash_start", "timestamp_utc": "2026-07-01T10:01:55+00:00"},
            {"name": "rollback_flash_done", "timestamp_utc": "2026-07-01T10:03:00+00:00"},
            {"name": "rollback_boot_ready", "timestamp_utc": "2026-07-01T10:03:10+00:00"},
        ]
    }


class AnalyzeReplRunTimingTests(unittest.TestCase):
    def test_events_schema_requires_only_events_top_level_and_required_phase_names(self) -> None:
        self.assertEqual(timing.validate_events_schema(timeline_events()), [])

        doc = timeline_events()
        doc["phases"] = {}
        errors = timing.validate_events_schema(doc)
        self.assertTrue(any("top-level keys must be exactly events" in item for item in errors))

        missing = {"events": timeline_events()["events"][:-1]}
        errors = timing.validate_events_schema(missing)
        self.assertTrue(any("rollback_boot_ready" in item for item in errors))

    def test_nested_timeline_shape_is_rejected(self) -> None:
        doc = {
            "timeline": {
                "candidate_flash_start": "2026-07-01T10:00:00+00:00",
                "candidate_flash_done": "2026-07-01T10:01:00+00:00",
            }
        }

        self.assertEqual(timing.extract_names(doc), {})
        self.assertTrue(timing.validate_events_schema(doc))

    def test_phase_elapsed_uses_canonical_events(self) -> None:
        names = timing.extract_names(timeline_events())

        self.assertEqual(
            timing.phase_elapsed(names, "candidate_flash_start", "candidate_flash_done"),
            65.0,
        )
        self.assertEqual(
            timing.phase_elapsed(names, "live_session_start", "live_session_end"),
            30.0,
        )

    def test_resident_session_projection_reduces_flash_count_and_cost(self) -> None:
        summary = {
            "candidate flash": {"mean": 65.0},
            "candidate boot/health": {"mean": 15.0},
            "live session (work)": {"mean": 30.0},
            "rollback flash": {"mean": 65.0},
            "rollback boot/health": {"mean": 15.0},
        }

        projection = timing.resident_session_projection(
            summary,
            batch_size=10,
            resident_batches=10,
            warm_reboot_sec=15.0,
        )

        self.assertEqual(projection["ok"], 1)
        self.assertEqual(projection["old_flashes"], 20)
        self.assertEqual(projection["resident_flashes"], 2)
        self.assertEqual(projection["old_batch_sec"], 190.0)
        self.assertEqual(projection["old_in_boot_per_target_sec"], 19.0)
        self.assertEqual(projection["resident_session_total_sec"], 610.0)
        self.assertEqual(projection["resident_per_target_sec"], 6.1)
        self.assertGreater(projection["speedup_vs_unbatched_unit"], 30.0)
        self.assertGreater(projection["speedup_vs_per_unit_in_boot_batch"], 3.0)

    def test_resident_session_projection_fails_closed_without_phase_means(self) -> None:
        projection = timing.resident_session_projection(
            {"candidate flash": {"mean": 65.0}},
            batch_size=10,
            resident_batches=10,
            warm_reboot_sec=15.0,
        )

        self.assertEqual(projection["ok"], 0)
        self.assertIn("missing phase means", projection["reason"])

    def test_cli_json_reports_invalid_noncanonical_timeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = root / "good"
            bad = root / "bad"
            good.mkdir()
            bad.mkdir()
            (good / "timeline.json").write_text(json.dumps(timeline_events()), encoding="utf-8")
            (bad / "timeline.json").write_text(
                json.dumps({"phases": {}, "events": timeline_events()["events"]}),
                encoding="utf-8",
            )

            # Exercise the core parser instead of subprocessing the CLI.
            valid = 0
            invalid = []
            for path in sorted(root.glob("*/timeline.json")):
                doc = json.loads(path.read_text(encoding="utf-8"))
                errors = timing.validate_events_schema(doc)
                if errors:
                    invalid.append(errors)
                else:
                    valid += 1

            self.assertEqual(valid, 1)
            self.assertEqual(len(invalid), 1)
            self.assertTrue(any("top-level keys" in item for item in invalid[0]))


if __name__ == "__main__":
    unittest.main()
