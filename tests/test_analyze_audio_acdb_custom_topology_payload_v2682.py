from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from analyze_audio_acdb_custom_topology_payload_v2682 import (
    MODULE_SLOT_U32,
    MODULE_SLOTS,
    RECORD_U32,
    load_module_names,
    parse_payload,
)


class AcdbCustomTopologyPayloadV2682Test(unittest.TestCase):
    def test_fixed_record_geometry_parses_declared_modules(self) -> None:
        words = [1]
        record = [0x1000FFFF, 2]
        record += [0x10719, 0x10000, 0, 0, 0, 0]
        record += [0x10BFE, 0x10000, 0, 0, 0, 0]
        record += [0] * ((MODULE_SLOTS - 2) * MODULE_SLOT_U32)
        self.assertEqual(len(record), RECORD_U32)
        words += record
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.bin"
            path.write_bytes(struct.pack("<" + "I" * len(words), *words))
            parsed = parse_payload(path, 14, "ASM_CUSTOM_TOPOLOGY_PAYLOAD", {0x10719: "AUDPROC_MODULE_ID_RESAMPLER"})
        self.assertTrue(parsed.grammar_ok)
        self.assertEqual(parsed.topology_count, 1)
        self.assertEqual(parsed.records[0].topology_id, 0x1000FFFF)
        self.assertEqual(parsed.records[0].declared_module_count, 2)
        self.assertEqual(len(parsed.records[0].active_modules), 2)
        self.assertTrue(parsed.records[0].module_count_matches)
        self.assertEqual(parsed.records[0].active_modules[0].name, "AUDPROC_MODULE_ID_RESAMPLER")

    def test_rejects_wrong_record_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.bin"
            path.write_bytes(struct.pack("<III", 1, 0x1000FFFF, 0))
            parsed = parse_payload(path, 14, "bad", {})
        self.assertFalse(parsed.grammar_ok)
        self.assertEqual(parsed.records, ())

    def test_module_name_loader_prefers_shorter_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            header = Path(tmp) / "apr_audio-v2.h"
            header.write_text(
                "#define VERY_LONG_MODULE_ALIAS 0x00010719\n"
                "#define AUDPROC_MODULE_ID_RESAMPLER 0x00010719\n"
            )
            names = load_module_names(header)
        self.assertEqual(names[0x10719], "AUDPROC_MODULE_ID_RESAMPLER")


if __name__ == "__main__":
    unittest.main()
