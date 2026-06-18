import tempfile
import unittest
from pathlib import Path

from workspace.public.src.scripts.revalidation import analyze_audio_acdb_pointer_target_capture_design_v2691 as v2691


class AnalyzeAudioAcdbPointerTargetCaptureDesignV2691Test(unittest.TestCase):
    def test_parse_tuple_evidence_detects_pointer_words(self):
        report = """
| cal_type | role | GET cmd | create | allocate | request words | ret | size |
| 24 | `AFE_CUSTOM_TOPOLOGY` | `0x000130da` | `True` | `True` | `0x00001000, 0xe9383000` | `0` | `1180` |
| 10 | `ADM_CUSTOM_TOPOLOGY` | `0x00011394` | `True` | `True` | `0x00001000, 0xe9382000` | `-12` | `0` |
| 14 | `ASM_CUSTOM_TOPOLOGY` | `0x00012e01` | `True` | `True` | `0x00001000, 0xe9381000` | `0` | `2356` |
"""
        rows = v2691.parse_tuple_evidence(report)

        self.assertEqual([row.cal_type for row in rows], [24, 10, 14])
        self.assertTrue(all(row.word1_pointer_like for row in rows))
        self.assertEqual(rows[1].ret, -12)
        self.assertEqual(rows[2].expected_topology_hex, "0x10005000")

    def test_inspect_sources_marks_existing_gap(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: self.remove_tree(root))
        lower = root / "lower.c"
        tap = root / "tap.c"
        indirect = root / "indirect.c"
        lower.write_text(
            "struct a90_cal_block { unsigned get_arg0; unsigned get_arg1; int mem_handle; };\n"
            "get_in[0] = block->get_arg0; get_in[1] = block->get_arg1;\n",
            encoding="utf-8",
        )
        tap.write_text("a90_log_generic_indirect_capture\n", encoding="utf-8")
        indirect.write_text("a90_log_indirect_candidate_captures\n", encoding="utf-8")

        evidence = v2691.inspect_sources(lower, tap, indirect)

        self.assertTrue(evidence.lower_builds_get_from_block)
        self.assertTrue(evidence.tap_has_generic_indirect_capture)
        self.assertTrue(evidence.indirect_tap_has_generic_indirect_capture)
        self.assertFalse(evidence.indirect_tap_has_maps_verified_pointer_target_capture)

    def test_analysis_requires_pointer_target_capture(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: self.remove_tree(root))
        run = root / "run"
        tap_dir = run / "ownget-device-artifacts" / "acdbtap"
        tap_dir.mkdir(parents=True)
        (tap_dir / "acdbtap-events.jsonl").write_text(
            "{\"event\":\"acdb_ioctl_call\",\"in_word1\":\"0xe9383000\"}\n",
            encoding="utf-8",
        )
        for name in (
            "acdbtap-00000001-cmd-000130da-in-len-00000008.bin",
            "acdbtap-00000001-cmd-000130da-len-00000004.bin",
            "acdbtap-00000002-cmd-00011394-in-len-00000008.bin",
            "acdbtap-00000002-cmd-00011394-len-00000004.bin",
            "acdbtap-00000003-cmd-00012e01-in-len-00000008.bin",
            "acdbtap-00000003-cmd-00012e01-len-00000004.bin",
        ):
            (tap_dir / name).write_bytes(b"\0" * 4)
        report = root / "v2690.md"
        report.write_text(
            "| 24 | `AFE_CUSTOM_TOPOLOGY` | `0x000130da` | `True` | `True` | `0x00001000, 0xe9383000` | `0` | `1180` |\n"
            "| 10 | `ADM_CUSTOM_TOPOLOGY` | `0x00011394` | `True` | `True` | `0x00001000, 0xe9382000` | `-12` | `0` |\n"
            "| 14 | `ASM_CUSTOM_TOPOLOGY` | `0x00012e01` | `True` | `True` | `0x00001000, 0xe9381000` | `0` | `2356` |\n",
            encoding="utf-8",
        )
        lower = root / "lower.c"
        tap = root / "tap.c"
        indirect = root / "indirect.c"
        lower.write_text(
            "struct a90_cal_block { unsigned get_arg0; unsigned get_arg1; int mem_handle; };\n"
            "get_in[0] = block->get_arg0; get_in[1] = block->get_arg1;\n",
            encoding="utf-8",
        )
        tap.write_text("a90_log_generic_indirect_capture\n", encoding="utf-8")
        indirect.write_text("a90_log_indirect_candidate_captures\n", encoding="utf-8")

        analysis = v2691.analyze(run, report, lower, tap, indirect)

        self.assertTrue(analysis.ok)
        self.assertEqual(analysis.decision, "v2691-same-process-pointer-target-capture-required")
        self.assertTrue(analysis.same_process_pointer_capture_required)
        self.assertTrue(analysis.native_replay_parked)
        rendered = v2691.render_report(analysis)
        self.assertIn("V2692 Build Requirements", rendered)
        self.assertIn("in_word1", rendered)

    def remove_tree(self, path: Path):
        import shutil

        shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
