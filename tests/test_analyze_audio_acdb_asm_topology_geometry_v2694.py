import struct
import tempfile
import unittest
from pathlib import Path

import analyze_audio_acdb_asm_topology_geometry_v2694 as v2694
import analyze_audio_acdb_core_topology_bridge_v2683 as v2683


class TestV2694AsmTopologyGeometry(unittest.TestCase):
    def test_decode_audio_cal_basic(self):
        data = struct.pack("<8i", 32, 0, 14, 16, 0, 2, 2356, 37)
        decoded = v2694.decode_audio_cal_basic(data)
        self.assertEqual(decoded["data_size"], 32)
        self.assertEqual(decoded["cal_type"], 14)
        self.assertEqual(decoded["cal_type_size"], 16)
        self.assertEqual(decoded["cal_size"], 2356)
        self.assertEqual(decoded["mem_handle"], 37)
        self.assertEqual(decoded["arg_len"], 32)

    def test_parse_fixed_payload_summary(self):
        record = v2683.CoreRecord(
            index=0,
            word_offset=0,
            domain=0,
            topology_id=0x10005000,
            version=0,
            modules=((0x10912, 0x10000), (0x10BFE, 0x10000)),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.bin"
            path.write_bytes(v2683.fixed_payload_from_core([record]))
            summary = v2694.parse_fixed_payload_summary(path)
        self.assertTrue(summary["exists"])
        self.assertTrue(summary["parse_ok"])
        self.assertEqual(summary["topology_count"], 1)
        self.assertEqual(summary["topologies"][0]["topology_hex"], "0x10005000")
        self.assertEqual(summary["topologies"][0]["module_count"], 2)

    def test_classify_ok(self):
        summary = {
            "source": {"markers": {
                "q6asm_uses_get_only_cal_block": True,
                "q6asm_sets_payload_size_from_cal_data_size": True,
                "q6asm_sets_payload_addr_from_cal_data_paddr": True,
                "q6asm_sends_asm_cmd_add_topologies": True,
                "q6asm_sets_custom_topology_dirty_on_set_cal": True,
                "cal_utils_create_block_imports_dma_buf_from_mem_handle": True,
            }},
            "manifests": {
                "v2679": {"entries": {"14": {"arg": {
                    "data_size": 32,
                    "cal_type": 14,
                    "cal_type_size": 16,
                    "cal_size": 2356,
                    "mem_handle": 37,
                }, "payload": {"size": 2356, "parse_ok": True, "sha256": "a"}}}},
                "v2688": {"entries": {"14": {"payload": {"sha256": "b"}}}},
            },
            "reports": {
                "v2680": {"asm_ebadparam": True},
                "v2689": {"asm_ebadparam": True},
            },
        }
        result = v2694.classify(summary)
        self.assertEqual(result["decision"], "v2694-asm-ebadparam-classified-as-dsp-payload-semantics")
        self.assertTrue(result["defined_payload_differs_from_exact_capture"])


if __name__ == "__main__":
    unittest.main()
