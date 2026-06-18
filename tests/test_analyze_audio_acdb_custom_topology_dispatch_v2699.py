import unittest

import analyze_audio_acdb_custom_topology_dispatch_v2699 as v2699


class TestAnalyzeAudioAcdbCustomTopologyDispatchV2699(unittest.TestCase):
    def test_parse_movw_movt_pairs_combines_same_register(self):
        disasm = """
            9154: 43 f2 da 00    movw    r0, #12506
            9158: 00 bf          nop
            915c: c0 f2 01 00    movt    r0, #1
            9160: 0c f0 86 ec    blx     #51468
            92ba: 41 f2 94 30    movw    r0, #5012
            92c2: c0 f2 01 00    movt    r0, #1
        """
        pairs = v2699.parse_movw_movt_pairs(disasm)
        self.assertEqual([pair.value for pair in pairs], [0x130DA, 0x11394])
        self.assertEqual(pairs[0].addr, 0x9154)

    def test_extract_block_commands_maps_to_cal_type_ranges(self):
        disasm = """
            9154: 43 f2 da 00    movw    r0, #12506
            915c: c0 f2 01 00    movt    r0, #1
            92ba: 41 f2 94 30    movw    r0, #5012
            92c2: c0 f2 01 00    movt    r0, #1
            945e: 42 f6 01 60    movw    r0, #11777
            9466: c0 f2 01 00    movt    r0, #1
        """
        commands = v2699.extract_block_commands(disasm)
        by_cal = {command.cal_type: command for command in commands}
        self.assertEqual(by_cal[24].cmd, 0x130DA)
        self.assertEqual(by_cal[10].cmd, 0x11394)
        self.assertEqual(by_cal[14].cmd, 0x12E01)
        self.assertEqual(by_cal[14].selected_topology, 0x10005000)

    def test_classify_dispatch_requires_target_coverage(self):
        commands = [
            v2699.BlockCommand(24, "AFE", 0x9154, 0x130DA, "AFE", 0x1001025D, "aligned"),
            v2699.BlockCommand(10, "ADM", 0x92BA, 0x11394, "ADM", 0x10004000, "absent"),
            v2699.BlockCommand(14, "ASM", 0x945E, 0x12E01, "ASM", 0x10005000, "stale"),
        ]
        result = v2699.classify_dispatch(commands)
        self.assertEqual(result["decision"], "v2699-custom-topology-dispatch-present-selector-state-missing")
        self.assertTrue(result["ok"])
        self.assertEqual(result["recommended_next"], "v2700-lower-selector-state-re")

    def test_classify_dispatch_reports_incomplete_when_missing_asm(self):
        commands = [
            v2699.BlockCommand(24, "AFE", 0x9154, 0x130DA, "AFE", 0x1001025D, "aligned"),
            v2699.BlockCommand(10, "ADM", 0x92BA, 0x11394, "ADM", 0x10004000, "absent"),
        ]
        result = v2699.classify_dispatch(commands)
        self.assertEqual(result["decision"], "v2699-custom-topology-dispatch-incomplete")
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
