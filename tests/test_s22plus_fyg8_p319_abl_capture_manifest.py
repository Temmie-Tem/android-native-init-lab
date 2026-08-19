"""The ABL census must be recomputable, not merely quoted.

An independent review found the census unbounded and its supporting test
string-pinned: the report stated 80/77/3 and the test only checked that those
characters appeared in the report.  These tests recompute the classification
from real capture bytes and require the report to agree with what was computed.
"""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REPORT = REPO / "docs" / "reports" / "S22PLUS_FYG8_P319_STOCK_USERSPACE_CHOREOGRAPHY_H0_2026-08-19.md"
MANIFEST = REPO / "workspace" / "private" / "outputs" / "s22plus_fyg8_p319" / "abl-capture-manifest.json"
SCRIPT = REPO / "workspace" / "public" / "src" / "scripts" / "analysis" / "s22plus_fyg8_p319_abl_log_census.py"
PRIVATE = REPO / "workspace" / "private"
LAST_KMSG_SIZE = 2097136


class AblCaptureManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = REPORT.read_text(encoding="utf-8")
        # Numeric agreement must not depend on where markdown happens to wrap.
        cls.flat = re.sub(r"\s+", " ", cls.report)
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else None

    def test_the_generator_is_committed_and_states_its_criterion(self):
        self.assertTrue(SCRIPT.exists())
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("deduplicated by SHA-256 before any counting", text)
        self.assertIn("contacts no device", text)

    def _manifest(self):
        if self.manifest is None:
            self.skipTest("manifest not built on this host; run the generator first")
        return self.manifest

    def test_manifest_counts_are_internally_consistent(self):
        m = self._manifest()
        caps = m["captures"]
        self.assertEqual(len(caps), m["distinct_captures"])
        self.assertEqual(m["matching_files"] - m["distinct_captures"], m["duplicate_files_collapsed"])
        self.assertEqual(sum(len(c["paths"]) for c in caps), m["matching_files"])
        self.assertEqual(len({c["sha256"] for c in caps}), len(caps))
        abl = [c for c in caps if c["has_abl_stage"]]
        counts = m["counts"]
        self.assertEqual(len(abl), counts["abl_stages"])
        self.assertEqual(sum(1 for c in abl if c["download_mode"]), counts["download_mode"])
        self.assertEqual(sum(1 for c in abl if not c["download_mode"]), counts["normal_handoff"])

    def test_classification_is_reproduced_from_real_bytes(self):
        # Not a tautology: re-read a sample of the actual captures, redo the
        # classification from scratch, and require the manifest to match.
        m = self._manifest()
        sample = [c for c in m["captures"] if c["has_abl_stage"]][:6]
        self.assertTrue(sample, "no ABL-bearing captures to sample")
        for cap in sample:
            path = REPO / cap["paths"][0]
            with self.subTest(path=cap["paths"][0]):
                blob = path.read_bytes()
                self.assertEqual(len(blob), LAST_KMSG_SIZE)
                self.assertEqual(hashlib.sha256(blob).hexdigest(), cap["sha256"])
                self.assertEqual(b"Launching odin" in blob, cap["download_mode"])
                self.assertEqual(
                    sorted({x.group(1).decode() for x in re.finditer(rb"SetPath: (\d+)", blob)}),
                    cap["setpath_values"],
                )

    def test_the_population_is_closed_against_the_live_tree(self):
        # The criterion is mechanical, so the file count must still hold.
        m = self._manifest()
        live = sum(
            1
            for p in PRIVATE.rglob("*")
            if p.is_file() and not p.is_symlink() and p.stat().st_size == LAST_KMSG_SIZE
        )
        self.assertEqual(live, m["matching_files"])

    def test_the_central_negative_holds_across_the_whole_population(self):
        m = self._manifest()
        self.assertEqual(m["counts"]["any_capture_with_setpath_0"], 0)
        self.assertEqual(m["setpath_values_observed"], ["1"])
        self.assertEqual(m["counts"]["normal_with_any_setpath"], 0)
        self.assertEqual(m["counts"]["download_without_setpath"], 0)
        self.assertEqual(m["counts"]["normal_with_mission_mode"], m["counts"]["normal_handoff"])

    def test_report_states_the_numbers_that_were_computed(self):
        m = self._manifest()
        c = m["counts"]
        for token in (
            f"**{m['matching_files']} matching files**",
            f"**{m['duplicate_files_collapsed']} of those files are byte-identical copies of another**",
            f"| → Odin (download mode) | **{c['download_mode']}** | `SetPath: 1` in **{c['download_mode']} of {c['download_mode']}**, none without |",
            f"| → normal handoff to Linux | **{c['normal_handoff']}** | **none at all, in all {c['normal_handoff']}** |",
            f"| any | {c['abl_stages']} |",
            f"All **{c['normal_handoff']}** normal-handoff captures carry `Booting Into Mission Mode`",
        ):
            with self.subTest(token=token):
                self.assertIn(re.sub(r"\s+", " ", token), self.flat)

    def test_report_records_that_the_earlier_census_was_replaced(self):
        self.assertIn("**The numbers below replace an earlier `80 / 77 / 3` table.**", self.report)
        self.assertIn("it undercounted the corpus and it counted files rather than captures", self.flat)
        self.assertNotIn("across all 80\nABL stages", self.report)


if __name__ == "__main__":
    unittest.main()
