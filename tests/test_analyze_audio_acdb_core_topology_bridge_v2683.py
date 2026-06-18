import struct
import unittest

import analyze_audio_acdb_core_topology_bridge_v2683 as v2683


class CoreTopologyBridgeV2683Test(unittest.TestCase):
    def test_parse_core_payload_variable_records(self):
        payload = struct.pack(
            "<" + "I" * 13,
            2,
            2, 0x10004000, 1, 2, 0x10719, 0x10000, 0x10C2A, 0x10000,
            2, 0x10005000, 1, 0,
        )
        records = v2683.parse_core_payload(payload)
        self.assertEqual([record.topology_id for record in records], [0x10004000, 0x10005000])
        self.assertEqual(records[0].modules, ((0x10719, 0x10000), (0x10C2A, 0x10000)))
        self.assertEqual(records[1].modules, ())

    def test_fixed_payload_from_core_uses_six_word_slots(self):
        record = v2683.CoreRecord(
            index=0,
            word_offset=1,
            domain=2,
            topology_id=0x10005000,
            version=1,
            modules=((0x10912, 0x10000), (0x10BFE, 0x10000)),
        )
        payload = v2683.fixed_payload_from_core([record])
        words = struct.unpack("<" + "I" * (len(payload) // 4), payload)
        self.assertEqual(len(payload), 4 + 98 * 4)
        self.assertEqual(words[0], 1)
        self.assertEqual(words[1], 0x10005000)
        self.assertEqual(words[2], 2)
        self.assertEqual(words[3:9], (0x10912, 0x10000, 0, 0, 0, 0))
        self.assertEqual(words[9:15], (0x10BFE, 0x10000, 0, 0, 0, 0))
        self.assertTrue(all(word == 0 for word in words[15:]))
        parsed = v2683.parse_fixed_payload(payload)
        self.assertEqual(parsed[0].modules, record.modules)

    def test_parse_fixed_payload_rejects_nonzero_reserved_words(self):
        words = [1] + [0] * 98
        words[1] = 0x10005000
        words[2] = 1
        words[3] = 0x10912
        words[4] = 0x10000
        words[5] = 1
        payload = struct.pack("<" + "I" * len(words), *words)
        with self.assertRaisesRegex(ValueError, "reserved"):
            v2683.parse_fixed_payload(payload)


if __name__ == "__main__":
    unittest.main()
