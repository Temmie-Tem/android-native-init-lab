from __future__ import annotations

import struct
import unittest

from _loader import load_script


runner = load_script(
    "workspace/public/src/scripts/revalidation/build_kernel_tier2_repl_v1_call_pair.py"
)
v1 = runner.v1repl


class KernelTier2ReplV1CallPairTests(unittest.TestCase):
    def test_call_pair_injection_contract(self) -> None:
        payload = runner.build_call_pair_injection(
            v1.ENTRY_OFF,
            v1.NEXT_MAGIC_OFF,
            v1.stage_c.PRINTK_EXPECTED_ENTRY_OFF,
        )
        words = [
            struct.unpack_from("<I", payload, index)[0]
            for index in range(0, v1.CODE_WORD_COUNT * 4, 4)
        ]

        self.assertEqual(len(payload), v1.EXPECTED_PATCH_LEN)
        self.assertEqual(words[39], v1.encode_blr(9))
        self.assertEqual(words[40], v1.encode_mov_x(2, 1))
        self.assertEqual(words[41], v1.encode_mov_x(1, 0))
        self.assertEqual(
            payload[v1.FORMAT_WORD_INDEX * 4:],
            runner.FORMAT,
        )
        self.assertEqual(
            v1.stage_c.decode_bl_target(
                v1.stage_c.kernel_vaddr(v1.ENTRY_OFF + 43 * 4),
                words[43],
            ),
            v1.PRINTK_ENTRY_VADDR,
        )


if __name__ == "__main__":
    unittest.main()
