import unittest

import analyze_audio_libaudcal_command_handlers_v2701 as v2701


class LibaudcalCommandHandlersV2701Test(unittest.TestCase):
    def test_branch_target_uses_thumb_pc_bias_for_operand(self) -> None:
        ins = v2701.Instruction(addr=0xD4DC, mnemonic="b.w", operands="#99752 <x>", text="")

        self.assertEqual(v2701.branch_target(ins), 0x25A88)

    def test_parse_relplt_maps_first_plt_slots(self) -> None:
        rel = """
00027f3c  00000016 R_ARM_JUMP_SLOT 00000000  first_func
00027f40  00000016 R_ARM_JUMP_SLOT 00000000  second_func
"""

        symbols = v2701.parse_relplt(rel)

        self.assertEqual(symbols[0].plt_addr, 0x25C90)
        self.assertEqual(symbols[1].plt_addr, 0x25CA0)
        self.assertEqual(symbols[1].name, "second_func")

    def test_thumb_veneer_resolves_to_plt(self) -> None:
        disasm = "\n".join(
            [
                "   25a88: 40 f2 1c 4c                   \tmovw\tr12, #1052",
                "   25a8c: c0 f2 00 0c                   \tmovt\tr12, #0",
                "   25a90: fc 44                         \tadd\tr12, pc",
                "   25a92: 60 47                         \tbx\tr12",
            ]
        )

        self.assertEqual(v2701.parse_thumb_veneer(disasm, 0x25A88), 0x25EB0)

    def test_parse_validator_detects_word1_only_shape(self) -> None:
        instructions = v2701.parse_instructions(
            "\n".join(
                [
                    "   d4b8: 08 2a                         \tcmp\tr2, #8",
                    "   d4c4: bc f1 04 0f                   \tcmp.w\tr12, #4",
                    "   d4cc: 48 68                         \tldr\tr0, [r1, #4]",
                ]
            )
        )

        validator = v2701.parse_validator(instructions)

        self.assertEqual(validator["in_len"], 8)
        self.assertEqual(validator["out_len"], 4)
        self.assertEqual(validator["key_offset"], 4)
        self.assertFalse(validator["checks_word0"])

    def test_parse_validator_accepts_top_level_afe_register_allocation(self) -> None:
        instructions = v2701.parse_instructions(
            "\n".join(
                [
                    "   e692: 08 2e                         \tcmp\tr6, #8",
                    "   e69e: b9 f1 04 0f                   \tcmp.w\tr9, #4",
                    "   e6a4: 78 68                         \tldr\tr0, [r7, #4]",
                ]
            )
        )

        validator = v2701.parse_validator(instructions)

        self.assertEqual(validator["in_len"], 8)
        self.assertEqual(validator["out_len"], 4)
        self.assertEqual(validator["key_offset"], 4)
        self.assertFalse(validator["checks_word0"])

    def test_classification_requires_resolved_word1_paths(self) -> None:
        paths = [
            v2701.HandlerPath(
                cal_type=10,
                role="ADM_CUST_TOPOLOGY",
                cmd=0x11394,
                dispatcher="acdb_ioctl_audio",
                dispatch_block=0xD4B2,
                call_addr=0xD4DC,
                tail_target=0x25A88,
                tail_target_kind="thumb-veneer",
                plt_addr=0x25EB0,
                plt_symbol="AcdbCmdGetAudioCOPPTopologyData",
                validator_in_len=8,
                validator_out_len=4,
                validator_key_word="word1",
                validator_key_offset=4,
                validator_checks_word0=False,
                observed_v2700_ret=-12,
                observed_v2700_state="absent-ret-minus-12",
                interpretation="",
            )
        ]

        classification = v2701.classify_handlers(paths)

        self.assertEqual(classification["decision"], "v2701-libaudcal-topology-handlers-share-word1-key")
        self.assertTrue(classification["shared_word1_only_validator"])
        self.assertEqual(classification["recommended_next"], "v2702-acdb-command-handler-table-lookup-instrumentation")


if __name__ == "__main__":
    unittest.main()
