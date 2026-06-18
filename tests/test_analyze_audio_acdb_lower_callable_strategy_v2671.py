import importlib.util
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "workspace/public/src/scripts/revalidation/analyze_audio_acdb_lower_callable_strategy_v2671.py"
spec = importlib.util.spec_from_file_location("v2671", MODULE)
v2671 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = v2671
spec.loader.exec_module(v2671)


class AnalyzeAcdbLowerCallableStrategyV2671(unittest.TestCase):
    def dynsym_text(self):
        return """
    86: 0000e2d5   360 FUNC    GLOBAL DEFAULT   14 acdb_loader_store_set_audio_cal
   110: 0000e68d   136 FUNC    GLOBAL DEFAULT   14 acdb_loader_set_audio_cal_v2
   141: 00008cf1  2620 FUNC    GLOBAL DEFAULT   14 acdb_loader_send_common_custom_topology
   170: 0000e43d   592 FUNC    GLOBAL DEFAULT   14 acdb_loader_adsp_set_audio_cal
"""

    def common_text(self):
        return """
    8cfe:       add.w   r11, sp, #24
    8d3a:       movw    r8, #25035
    8d3e:       movt    r8, #49156
    8d12:       str     r0, [sp, #92]
    90ea:       movs    r0, #24
    90ec:       bl      #27732
    910a:       bl      #27310
    9160:       blx     #51468
    91c8:       blx     #51716
    924a:       movs    r0, #10
    924c:       bl      #27380
    926c:       bl      #26956
    92c6:       blx     #51112
    92fc:       blx     #51408
    93f6:       movs    r0, #14
    93f8:       bl      #26952
    9416:       bl      #26530
    946a:       blx     #50692
    94a0:       blx     #50988
    9524:       movs    r0, #25
    9526:       bl      #26650
    9544:       bl      #26228
    959a:       blx     #50388
    95d0:       blx     #50684
"""

    def set_v2_text(self):
        return """
    e692:       mov     r6, r0
    e696:       mov     r8, r2
    e698:       mov     r5, r1
    e6c0:       b.w     #29328
    e6f2:       b.w     #29290
"""

    def store_text(self):
        return """
    e2da:       cmp     r0, #0
    e2e6:       cmpne   r1, #0
    e30a:       ldr     r3, [r0, #28]
"""

    def adsp_text(self):
        return """
    e442:       mov     r7, r0
    e44e:       mov     r9, r1
    e450:       mov     r10, r2
    e496:       ldr     r0, [r7, #28]
"""

    def test_common_blocks_are_pinned_but_not_direct_callable(self):
        blocks = {row.cal_type: row for row in v2671.analyze_common_blocks(self.common_text())}
        for cal_type in (10, 14, 24):
            self.assertTrue(blocks[cal_type].path_pinned)
            self.assertFalse(blocks[cal_type].direct_entry_callable)
            self.assertIn("interior block", blocks[cal_type].direct_entry_rejection_reason)

    def test_helper_abi_requires_created_cal_node(self):
        symbols = v2671.parse_dynamic_symbols(self.dynsym_text(), v2671.EXPORTED_HELPERS)
        abi = v2671.analyze_helper_abi(symbols, self.set_v2_text(), self.store_text(), self.adsp_text())
        self.assertTrue(abi.set_audio_cal_v2_three_arg_wrapper)
        self.assertTrue(abi.store_set_audio_cal_expects_node_and_payload)
        self.assertTrue(abi.adsp_set_audio_cal_expects_node_payload_len)
        self.assertTrue(abi.standalone_helper_requires_cal_node_pointer)

    def test_analysis_selects_hidden_node_sequence_next(self):
        analysis = v2671.analyze(
            dynsym_text=self.dynsym_text(),
            common_text=self.common_text(),
            set_v2_text=self.set_v2_text(),
            store_text=self.store_text(),
            adsp_text=self.adsp_text(),
        )
        self.assertTrue(analysis.ok)
        self.assertFalse(analysis.direct_hidden_blocks_callable)
        self.assertTrue(analysis.hidden_node_sequence_ready)
        self.assertFalse(analysis.exported_lower_helper_standalone_ready)
        self.assertIn("base+0xfd45", analysis.next_unit)

    def test_markdown_records_do_not_jump_boundary(self):
        analysis = v2671.analyze(
            dynsym_text=self.dynsym_text(),
            common_text=self.common_text(),
            set_v2_text=self.set_v2_text(),
            store_text=self.store_text(),
            adsp_text=self.adsp_text(),
        )
        report = v2671.markdown(analysis)
        self.assertIn("do **not** call", report)
        self.assertIn("create the cal node", report)
        self.assertIn("fake-success", report)


if __name__ == "__main__":
    unittest.main()
