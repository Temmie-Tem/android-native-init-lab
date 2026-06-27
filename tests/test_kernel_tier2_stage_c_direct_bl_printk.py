from __future__ import annotations

import hashlib
import struct
import unittest

from _loader import load_script


runner = load_script(
    "workspace/public/src/scripts/revalidation/build_kernel_tier2_stage_c_direct_bl_printk.py"
)


class KernelTier2StageCDirectBlPrintkTests(unittest.TestCase):
    def test_pc_relative_encoders_round_trip(self) -> None:
        site = runner.kernel_vaddr(runner.KGSL_EXPECTED_ENTRY_OFF) + 16
        target = runner.kernel_vaddr(runner.PRINTK_EXPECTED_ENTRY_OFF)
        word = runner.encode_bl(site, target)

        self.assertEqual(runner.decode_bl_target(site, word), target)

        adr_site = runner.kernel_vaddr(runner.KGSL_EXPECTED_ENTRY_OFF) + 12
        marker = runner.kernel_vaddr(runner.KGSL_EXPECTED_ENTRY_OFF + 36)
        adr = runner.encode_adr_x0(adr_site, marker)
        self.assertEqual(adr & 0x1F, 0)

    def test_injection_contract_preserves_ropp_shape(self) -> None:
        payload, marker_off = runner.build_injection(
            runner.KGSL_EXPECTED_ENTRY_OFF,
            runner.KGSL_EXPECTED_NEXT_MAGIC_OFF,
            runner.PRINTK_EXPECTED_ENTRY_OFF,
        )

        words = [struct.unpack_from("<I", payload, index)[0] for index in range(0, 36, 4)]
        self.assertEqual(words[0], runner.U32_EOR_PROLOGUE)
        self.assertEqual(words[1], 0xA9BF43FD)
        self.assertEqual(words[2], 0x910003FD)
        self.assertEqual(words[5], 0xA8C143FD)
        self.assertEqual(words[6], runner.U32_EOR_EPILOGUE)
        self.assertEqual(words[7], 0x528000A0)
        self.assertEqual(words[8], runner.U32_RET)
        self.assertIn(runner.MARKER, payload)
        self.assertEqual(marker_off, runner.KGSL_EXPECTED_ENTRY_OFF + 36)
        self.assertEqual(
            len(payload),
            runner.KGSL_EXPECTED_NEXT_MAGIC_OFF - runner.KGSL_EXPECTED_ENTRY_OFF,
        )
        self.assertNotIn(0xD63F0000, words)  # no blr x0

    def test_private_v2321_image_signatures_when_available(self) -> None:
        if not runner.BASE_BOOT.exists():
            self.skipTest("private v2321 boot image unavailable")

        image = runner.BASE_BOOT.read_bytes()
        self.assertEqual(hashlib.sha256(image).hexdigest(), runner.BASE_BOOT_SHA256)
        layout = runner.parse_boot_layout(image)
        kernel = image[layout.kernel_off : layout.kernel_off + layout.kernel_size]

        self.assertEqual(
            runner.locate_kgsl_num_pwrlevels(kernel),
            (
                runner.KGSL_EXPECTED_MAGIC_OFF,
                runner.KGSL_EXPECTED_ENTRY_OFF,
                runner.KGSL_EXPECTED_NEXT_MAGIC_OFF,
            ),
        )
        self.assertEqual(
            runner.locate_printk_variadic_wrapper(kernel),
            (
                runner.PRINTK_EXPECTED_ENTRY_OFF - 4,
                runner.PRINTK_EXPECTED_ENTRY_OFF,
                runner.PRINTK_EXPECTED_VA_HELPER_OFF,
                runner.PRINTK_EXPECTED_EMIT_CORE_OFF,
            ),
        )

    def test_boot_id_recompute_matches_clean_v2321_when_available(self) -> None:
        if not runner.BASE_BOOT.exists():
            self.skipTest("private v2321 boot image unavailable")

        image = bytearray(runner.BASE_BOOT.read_bytes())
        layout = runner.parse_boot_layout(bytes(image))
        original_id = bytes(image[runner.BOOT_ID_OFFSET : runner.BOOT_ID_OFFSET + runner.BOOT_ID_SIZE])
        recomputed = runner.recompute_boot_id(image, layout)

        self.assertEqual(recomputed, original_id)


if __name__ == "__main__":
    unittest.main()
