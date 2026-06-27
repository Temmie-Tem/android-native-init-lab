from __future__ import annotations

import hashlib
import struct
import unittest

from _loader import load_script


runner = load_script(
    "workspace/public/src/scripts/revalidation/build_kernel_tier2_kasan_lite_reclaim_dump.py"
)


class KernelTier2KasanLiteReclaimDumpTests(unittest.TestCase):
    def test_dump_injection_contract(self) -> None:
        payload, format_off = runner.build_dump_injection(
            runner.PROC_RESET_EXPECTED_ENTRY_OFF,
            runner.PROC_RESET_EXPECTED_NEXT_MAGIC_OFF,
            runner.stage_c.PRINTK_EXPECTED_ENTRY_OFF,
        )

        words = [struct.unpack_from("<I", payload, index)[0] for index in range(0, 120, 4)]
        self.assertEqual(words[0], runner.stage_c.U32_EOR_PROLOGUE)
        self.assertEqual(words[1], 0xA9BE43FD)
        self.assertEqual(words[2], 0xF9000BF3)
        self.assertEqual(words[3], 0x910003FD)
        self.assertEqual(words[4], runner.encode_ldr_x_imm(19, 3, 0xB40))

        for call_base, line_index, offset in ((5, 0, 0x00), (11, 1, 0x20), (17, 2, 0x40)):
            self.assertEqual(words[call_base] & 0x1F, 0)  # adr x0, format
            self.assertEqual(words[call_base + 1], runner.encode_mov_w_imm(1, line_index))
            self.assertEqual(words[call_base + 2], runner.encode_mov_x(2, 19))
            self.assertEqual(words[call_base + 3], runner.encode_ldp_x(3, 4, 19, offset))
            self.assertEqual(words[call_base + 4], runner.encode_ldp_x(5, 6, 19, offset + 0x10))
            self.assertEqual(words[call_base + 5] & 0xFC000000, 0x94000000)

        self.assertEqual(words[23], 0x2A1F03E0)
        self.assertEqual(words[24], 0xF9400BF3)
        self.assertEqual(words[25], 0xA8C243FD)
        self.assertEqual(words[26], runner.stage_c.U32_EOR_EPILOGUE)
        self.assertEqual(words[27], runner.stage_c.U32_RET)
        self.assertIn(runner.FORMAT, payload)
        self.assertEqual(format_off, runner.PROC_RESET_EXPECTED_ENTRY_OFF + 28 * 4)
        self.assertEqual(
            len(payload),
            runner.PROC_RESET_EXPECTED_NEXT_MAGIC_OFF - runner.PROC_RESET_EXPECTED_ENTRY_OFF,
        )
        self.assertNotIn(0xD63F0000, words)  # no blr x0

    def test_private_v2321_image_signatures_when_available(self) -> None:
        if not runner.BASE_BOOT.exists():
            self.skipTest("private v2321 boot image unavailable")

        image = runner.BASE_BOOT.read_bytes()
        self.assertEqual(hashlib.sha256(image).hexdigest(), runner.BASE_BOOT_SHA256)
        layout = runner.stage_c.parse_boot_layout(image)
        kernel = image[layout.kernel_off : layout.kernel_off + layout.kernel_size]

        self.assertEqual(
            runner.find_proc_integrity_reset_file(kernel),
            (
                runner.PROC_RESET_EXPECTED_MAGIC_OFF,
                runner.PROC_RESET_EXPECTED_ENTRY_OFF,
                runner.PROC_RESET_EXPECTED_NEXT_MAGIC_OFF,
            ),
        )
        self.assertEqual(
            runner.stage_c.locate_printk_variadic_wrapper(kernel),
            (
                runner.stage_c.PRINTK_EXPECTED_ENTRY_OFF - 4,
                runner.stage_c.PRINTK_EXPECTED_ENTRY_OFF,
                runner.stage_c.PRINTK_EXPECTED_VA_HELPER_OFF,
                runner.stage_c.PRINTK_EXPECTED_EMIT_CORE_OFF,
            ),
        )


if __name__ == "__main__":
    unittest.main()
