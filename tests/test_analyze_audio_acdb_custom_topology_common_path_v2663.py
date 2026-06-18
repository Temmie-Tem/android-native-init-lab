import unittest
from pathlib import Path
import importlib.util
import sys

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "workspace/public/src/scripts/revalidation/analyze_audio_acdb_custom_topology_common_path_v2663.py"
spec = importlib.util.spec_from_file_location("v2663", MODULE)
v2663 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = v2663
spec.loader.exec_module(v2663)


class AnalyzeCommonTopologyPathV2663(unittest.TestCase):
    def sample_common_text(self):
        return """
00008cf0 acdb_loader_send_common_custom_topology:
    90ea:       movs    r0, #24
    90ec:       bl      #27732
    910a:       bl      #27310
    9154:       movw    r0, #12506
    9160:       blx     #51468
    91c8:       blx     #51716
    924a:       movs    r0, #10
    924c:       bl      #27380
    926c:       bl      #26956
    92ba:       movw    r0, #5012
    92c6:       blx     #51112
    92fc:       blx     #51408
    93f6:       movs    r0, #14
    93f8:       bl      #26952
    9416:       bl      #26530
    945e:       movw    r0, #11777
    946a:       blx     #50692
    94a0:       blx     #50988
    9524:       movs    r0, #25
    9526:       bl      #26650
    9544:       bl      #26228
    958c:       movw    r0, #12506
    959a:       blx     #50388
    95d0:       blx     #50684
"""

    def test_branch_target_parser_maps_known_calls(self):
        text = self.sample_common_text()
        self.assertEqual(v2663.parse_branch_target(text, 0x924C), 0xFD44)
        self.assertEqual(v2663.parse_branch_target(text, 0x926C), 0xFBBC)
        self.assertEqual(v2663.parse_branch_target(text, 0x92C6), 0x15A72)
        self.assertEqual(v2663.parse_branch_target(text, 0x92FC), 0x15BD0)

    def test_analyze_common_text_finds_missing_target_cals(self):
        paths = {p.cal_type: p for p in v2663.analyze_common_text(self.sample_common_text())}
        for cal_type, command_id in ((10, "0x11394"), (14, "0x12e01"), (24, "0x130da")):
            with self.subTest(cal_type=cal_type):
                self.assertIn(cal_type, paths)
                self.assertTrue(paths[cal_type].reaches_target_set_path)
                self.assertEqual(paths[cal_type].get_command_id, command_id)
                self.assertEqual(paths[cal_type].acdb_ioctl_callsite[:2], "0x")
                self.assertEqual(paths[cal_type].set_ioctl_callsite[:2], "0x")

    def test_markdown_records_next_unit_and_boundaries(self):
        analysis = v2663.Analysis(
            decision="unit-test",
            ok=True,
            lib_path="private/lib.so",
            lib_sha256="0" * 64,
            thumb_disassembly_ok=True,
            target_custom_cals_complete=True,
            common_export_contains_targets=True,
            lower_set_helper_not_required=True,
            cal_paths=v2663.analyze_common_text(self.sample_common_text()),
            next_unit="V2664 common-only capture",
        )
        report = v2663.markdown(analysis)
        self.assertIn("cal_types `24`, `10`, and `14`", report)
        self.assertIn("fake `AUDIO_SET_CALIBRATION`", report)
        self.assertIn("V2664 common-only capture", report)


if __name__ == "__main__":
    unittest.main()
