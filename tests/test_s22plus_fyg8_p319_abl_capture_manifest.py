"""The ABL census must be recomputable, not merely quoted.

An independent review found the census unbounded and its supporting test
string-pinned: the report stated 80/77/3 and the test only checked that those
characters appeared in the report.  These tests recompute the classification
from real capture bytes and require the report to agree with what was computed.

A later review found three more holes and they are closed here.  The manifest is
gitignored, so `MANIFEST.exists()` was false on a clean checkout and every
substantive test skipped silently; the manifest is now *built* when absent, so
the suite either checks the corpus or fails, and never quietly passes.  The
recomputation covered only the first six entries; it now covers every
ABL-bearing capture.  And SHA-256 identity is file identity rather than boot
identity, so the boot-segment count is recomputed independently as well.
"""

from __future__ import annotations

import hashlib
import importlib.util
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

SEGMENT_RE = re.compile(rb"MUIC Device : Max77705! count: 0")
BC_CTRL1_RE = re.compile(rb"BC_CTRL1_READ\s*:\s*(0x[0-9A-Fa-f]+)")
OPCODE_RE = re.compile(rb"muic_command_polling: OP (0x[0-9A-Fa-f]{2})")
SETPATH_RE = re.compile(rb"SetPath: (\d+)")


def _load_generator():
    spec = importlib.util.spec_from_file_location("p319_abl_log_census", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AblCaptureManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = REPORT.read_text(encoding="utf-8")
        # Numeric agreement must not depend on where markdown happens to wrap.
        cls.flat = re.sub(r"\s+", " ", cls.report)
        if MANIFEST.exists():
            cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        else:
            # Build rather than skip.  The manifest is a gitignored output, and
            # skipping on its absence made every check below vacuous on a clean
            # checkout.
            cls.manifest = _load_generator().build()

    def test_the_generator_is_committed_and_states_its_criterion(self):
        self.assertTrue(SCRIPT.exists())
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("deduplicated by SHA-256 before any counting", text)
        self.assertIn("contacts no device", text)
        self.assertIn("SHA-256 identity is *file* identity, not *boot* identity", text)

    def _manifest(self):
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
        self.assertEqual(sum(c["boot_segments"] for c in abl), counts["abl_boot_segments"])

    def test_classification_is_reproduced_from_every_abl_capture(self):
        # Not a tautology and no longer a sample: re-read every ABL-bearing
        # capture, redo the classification from scratch, and require the
        # manifest to match byte for byte and count for count.
        m = self._manifest()
        abl = [c for c in m["captures"] if c["has_abl_stage"]]
        self.assertEqual(len(abl), m["counts"]["abl_stages"])
        self.assertTrue(abl, "no ABL-bearing captures to check")
        for cap in abl:
            path = REPO / cap["paths"][0]
            with self.subTest(path=cap["paths"][0]):
                blob = path.read_bytes()
                self.assertEqual(len(blob), LAST_KMSG_SIZE)
                self.assertEqual(hashlib.sha256(blob).hexdigest(), cap["sha256"])
                self.assertEqual(b"Launching odin" in blob, cap["download_mode"])
                self.assertEqual(
                    sorted({x.group(1).decode() for x in SETPATH_RE.finditer(blob)}),
                    cap["setpath_values"],
                )
                self.assertEqual(len(SETPATH_RE.findall(blob)), cap["setpath_occurrences"])
                self.assertEqual(len(SEGMENT_RE.findall(blob)), cap["boot_segments"])
                self.assertEqual(
                    [x.group(1).decode() for x in BC_CTRL1_RE.finditer(blob)],
                    cap["bc_ctrl1_reads"],
                )

    def test_every_manifest_path_still_exists_with_the_right_bytes(self):
        m = self._manifest()
        for cap in m["captures"]:
            for rel in cap["paths"]:
                p = REPO / rel
                with self.subTest(path=rel):
                    self.assertTrue(p.is_file(), f"manifest path vanished: {rel}")
                    self.assertEqual(p.stat().st_size, LAST_KMSG_SIZE)

    def test_the_population_is_closed_against_the_live_tree(self):
        # The criterion is mechanical, so the file count must still hold.
        m = self._manifest()
        live = sum(
            1
            for p in PRIVATE.rglob("*")
            if p.is_file() and not p.is_symlink() and p.stat().st_size == LAST_KMSG_SIZE
        )
        self.assertEqual(live, m["matching_files"] + m["unreadable_or_short_files"])

    def test_the_central_negative_holds_across_the_whole_population(self):
        m = self._manifest()
        self.assertEqual(m["counts"]["any_capture_with_setpath_0"], 0)
        self.assertEqual(m["setpath_values_observed"], ["1"])
        self.assertEqual(m["counts"]["normal_with_any_setpath"], 0)
        self.assertEqual(m["counts"]["download_without_setpath"], 0)
        self.assertEqual(m["counts"]["normal_with_mission_mode"], m["counts"]["normal_handoff"])

    def test_one_file_is_not_one_boot(self):
        # The correction the sixth review forced: the download captures hold
        # several boot rings each, so the file count is not a boot count.
        m = self._manifest()
        c = m["counts"]
        self.assertEqual(c["normal_boot_segments"], c["normal_handoff"])
        self.assertGreater(c["download_boot_segments"], c["download_mode"])
        self.assertEqual(
            c["download_boot_segments"] + c["normal_boot_segments"], c["abl_boot_segments"]
        )

    def test_the_hidden_register_value_is_carried_uncollapsed(self):
        # 0x00C5 vs 0x00E5 differ in BC_CTRL1 bit 5, NoAutoIBUS.  Normalising
        # the digits is what hid it, so the manifest must keep both.
        m = self._manifest()
        self.assertEqual(set(m["bc_ctrl1_value_counts_normal"]), {"0x00C5"})
        self.assertEqual(set(m["bc_ctrl1_value_counts_download"]), {"0x00C5", "0x00E5"})
        # Exactly one 0x00C5 per download capture, and it is the first read.
        download = [c for c in m["captures"] if c["has_abl_stage"] and c["download_mode"]]
        for cap in download:
            with self.subTest(sha=cap["sha256"][:12]):
                reads = cap["bc_ctrl1_reads"]
                self.assertEqual(reads.count("0x00C5"), 1)
                self.assertEqual(reads[0], "0x00C5")
                self.assertEqual(set(reads[1:]), {"0x00E5"})

    def test_no_capture_writes_bcctrl1_and_the_control1_accounting_closes(self):
        m = self._manifest()
        ops = m["muic_opcode_counts"]
        c = m["counts"]
        # 0x02 is OPCODE_BCCTRL1_W, issued only by path ids 5 and 6.
        self.assertNotIn("0x02", ops)
        # One BCCTRL1 read per boot segment.
        self.assertEqual(ops["0x01"], c["abl_boot_segments"])
        # Every CONTROL1 access is muic_init's or a SetPath, with no residual.
        self.assertEqual(ops["0x05"], ops["0x06"])
        self.assertEqual(ops["0x06"], c["abl_boot_segments"] + c["setpath_occurrences_total"])

    def test_report_states_the_numbers_that_were_computed(self):
        m = self._manifest()
        c = m["counts"]
        for token in (
            f"**{m['matching_files']} matching files**",
            f"**{m['duplicate_files_collapsed']} of those files are byte-identical copies of another**",
            f"| → Odin (download mode) | **{c['download_mode']}** | **{c['download_boot_segments']}** | `SetPath: 1` in **{c['download_mode']} of {c['download_mode']}** files, **{c['setpath_occurrences_total']}** occurrences |",
            f"| → normal handoff to Linux | **{c['normal_handoff']}** | **{c['normal_boot_segments']}** | **none at all, in all {c['normal_handoff']}** |",
            f"| any | {c['abl_stages']} | {c['abl_boot_segments']} |",
            f"All **{c['normal_handoff']}** normal-handoff captures carry `Booting Into Mission Mode`",
            f"the corpus is **{c['abl_boot_segments']} boot segments in {c['abl_stages']} files**",
        ):
            with self.subTest(token=token):
                self.assertIn(re.sub(r"\s+", " ", token), self.flat)

    def test_report_records_that_the_earlier_census_was_replaced(self):
        self.assertIn("**The numbers below replace an earlier `80 / 77 / 3` table.**", self.report)
        self.assertIn("it undercounted the corpus and it counted files rather than captures", self.flat)
        self.assertNotIn("across all 80\nABL stages", self.report)

    def test_report_withdraws_the_distinct_boots_framing(self):
        self.assertIn('The census called its 121 deduplicated files "distinct boots"', self.flat)
        self.assertIn("**That is withdrawn.**", self.flat)


if __name__ == "__main__":
    unittest.main()
