"""Tests for the V2599 ACDB post-preGET geometry extractor."""

from __future__ import annotations

import unittest

from _loader import load_revalidation

v2599 = load_revalidation("native_audio_acdb_post_preget_geometry_recon_v2599")


class NativeAudioAcdbPostPregetGeometryReconV2599(unittest.TestCase):
    def test_combines_movw_movt_literals(self) -> None:
        context = v2599.parse_instructions(
            """
            9e7a: 41 f2 2e 20                  movw    r0, #4654
            9e82: c0 f2 01 00                  movt    r0, #1
            """
        )
        registers = v2599.literal_registers(context)
        self.assertEqual(v2599.combined_literal(registers["r0"]), 0x1122E)

    def test_extracts_literal_acdb_call_metadata(self) -> None:
        context = v2599.parse_instructions(
            """
            9e74: 04 20                        movs    r0, #4
            9e76: 04 22                        movs    r2, #4
            9e78: 00 90                        str     r0, [sp]
            9e7a: 41 f2 2e 20                  movw    r0, #4654
            9e80: 1d ab                        add     r3, sp, #116
            9e82: c0 f2 01 00                  movt    r0, #1
            9e86: 0b f0 f4 ed                  blx     #48104
            """
        )
        registers = v2599.literal_registers(context)
        source = v2599.command_source(context, registers, "acdb_ioctl")
        self.assertEqual(source["value"], 0x1122E)
        self.assertEqual(v2599.immediate_r2(context, registers), 4)
        self.assertEqual(v2599.stack_out_len(context, registers), 4)

    def test_extracts_audio_set_ioctl_request(self) -> None:
        context = v2599.parse_instructions(
            """
            9f0a: 46 f2 cb 11                  movw    r1, #25035
            9f0e: cc f2 04 01                  movt    r1, #49156
            9f16: 0b f0 5c ee                  blx     #48312
            """
        )
        registers = v2599.literal_registers(context)
        source = v2599.command_source(context, registers, "ioctl")
        self.assertEqual(source["value"], v2599.AUDIO_SET_CALIBRATION)
        self.assertEqual(source["meaning"], "AUDIO_SET_CALIBRATION")

    def test_detects_table_backed_acdb_command(self) -> None:
        context = v2599.parse_instructions(
            """
            a352: 70 78                        ldrb    r0, [r6, #1]
            a354: 0c 22                        movs    r2, #12
            a356: 00 91                        str     r1, [sp]
            a35c: 51 f8 20 00                  ldr.w   r0, [r1, r0, lsl #2]
            a364: 0b f0 84 eb                  blx     #46856
            """
        )
        registers = v2599.literal_registers(context)
        source = v2599.command_source(context, registers, "acdb_ioctl")
        self.assertEqual(source["kind"], "table_lookup")

    def test_helper_range_names_downstream_helpers(self) -> None:
        self.assertEqual(v2599.helper_range_for(0x9E86)["name"], "send_audio_cal_v5_entry")
        self.assertEqual(v2599.helper_range_for(0xB45E)["name"], "helper_b370")


if __name__ == "__main__":
    unittest.main()
