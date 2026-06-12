"""Regression tests for a90_kernel_v2243_user_uprobe_semantic_classifier."""

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2243 = load_revalidation("a90_kernel_v2243_user_uprobe_semantic_classifier")


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def instruction_lines():
    return [
        "    0ffc: d503201f \tnop",
        "    1000: a9bf7bfd \tstp x29, x30, [sp, #-16]!",
        "    1004: 94000001 \tbl 0x2000",
        "    1008: b4000040 \tcbz x0, 0x1010",
        "    100c: d65f03c0 \tret",
    ]


def context_entry(event: str, offset: str, stdout=None, key_event=True):
    return {
        "group": "a90cnss",
        "object": "a90cnss",
        "event": event,
        "offset": offset,
        "observed": True,
        "key_event": key_event,
        "disassembly": {"stdout": stdout if stdout is not None else instruction_lines()},
    }


class InstructionParsing(unittest.TestCase):
    def test_parse_instructions_ignores_non_instruction_lines_and_normalizes_mnemonic(self):
        instructions = v2243.parse_instructions([
            "not an instruction",
            "    1000: A9BF7BFD \tSTP x29, x30, [sp, #-16]!",
            "    1004: 94000001 \tbl 0x2000",
        ])

        self.assertEqual([item.address for item in instructions], [0x1000, 0x1004])
        self.assertEqual(instructions[0].mnemonic, "stp")
        self.assertIn("x29", instructions[0].operands)

    def test_find_target_returns_neighboring_instructions_or_missing(self):
        instructions = v2243.parse_instructions(instruction_lines())

        previous, current, next_instruction = v2243.find_target(instructions, 0x1004)
        missing = v2243.find_target(instructions, 0x2000)

        self.assertEqual(previous.address, 0x1000)
        self.assertEqual(current.mnemonic, "bl")
        self.assertEqual(next_instruction.address, 0x1008)
        self.assertEqual(missing, (None, None, None))

    def test_instruction_class_covers_common_aarch64_shapes(self):
        samples = {
            "frame_prologue": "1000: a9bf7bfd \tstp x29, x30, [sp, #-16]!",
            "return": "1000: d65f03c0 \tret",
            "call": "1000: 94000001 \tbl 0x2000",
            "branch": "1000: 14000001 \tb 0x2000",
            "conditional_branch": "1000: b4000040 \tcbz x0, 0x1010",
            "compare": "1000: eb01001f \tcmp x0, x1",
            "load": "1000: f9400000 \tldr x0, [x0]",
            "store": "1000: f9000000 \tstr x0, [x0]",
            "address_or_alu": "1000: aa0103e0 \tmov x0, x1",
            "syscall": "1000: d4000001 \tsvc #0",
        }
        for expected, line in samples.items():
            with self.subTest(expected=expected):
                instruction = v2243.parse_instructions([line])[0]
                self.assertEqual(v2243.instruction_class(instruction), expected)
        self.assertIsNone(v2243.instruction_class(None))


class RoleAndClassification(unittest.TestCase):
    def test_event_role_and_role_alignment_cover_high_medium_low_paths(self):
        self.assertEqual(v2243.event_role("wlfw_start"), "entry")
        self.assertEqual(v2243.event_role("bdf_send_ret"), "return_or_result")
        self.assertEqual(v2243.event_role("worker_wait"), "wait_edge")
        self.assertEqual(v2243.event_role("qmi_capability"), "protocol_edge")
        self.assertEqual(v2243.event_role("plain_marker"), "state_edge")

        self.assertEqual(
            v2243.role_alignment("entry", "frame_prologue", None, "load"),
            ("aligned_entry_prologue", "high"),
        )
        self.assertEqual(
            v2243.role_alignment("return_or_result", "address_or_alu", "call", "compare"),
            ("aligned_post_call", "high"),
        )
        self.assertEqual(
            v2243.role_alignment("protocol_edge", "load", None, "call"),
            ("marker_edge", "medium"),
        )
        self.assertEqual(
            v2243.role_alignment("entry", "other", None, None),
            ("needs_manual_context", "low"),
        )
        self.assertEqual(
            v2243.role_alignment("entry", None, None, None),
            ("missing_target", "none"),
        )

    def test_classify_context_builds_public_rows_and_private_neighbor_lines(self):
        context = {
            "entries": [
                context_entry("wlfw_start", "0x1000"),
                context_entry("wlfw_bdf_send_ret", "0x1008"),
                context_entry("unmapped", "0x9999", key_event=False),
            ]
        }

        rows, private_rows = v2243.classify_context(context)

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0].alignment, "aligned_entry_prologue")
        self.assertEqual(rows[1].event_role, "return_or_result")
        self.assertEqual(rows[1].alignment, "aligned_post_call")
        self.assertEqual(rows[1].confidence, "high")
        self.assertFalse(rows[2].target_found)
        self.assertIn("current", private_rows[0]["private_instruction_lines"])
        self.assertEqual(v2243.public_row(rows[0])["event"], "wlfw_start")

    def test_counter_dict_counts_named_dataclass_field(self):
        rows, _ = v2243.classify_context({"entries": [context_entry("wlfw_start", "0x1000")]})

        self.assertEqual(v2243.counter_dict(rows, "confidence"), {"high": 1})


class SummaryBuilder(unittest.TestCase):
    def make_args(self, root: Path, context_payload):
        summary = root / "v2242-summary.json"
        context = root / "private-context.json"
        write_json(summary, {"decision": "v2242-user-elf-offset-context-pass"})
        write_json(context, context_payload)
        return argparse.Namespace(
            label="unit",
            v2242_summary=summary,
            v2242_context=context,
        )

    def test_build_summary_passes_and_writes_private_semantic_file_for_non_low_key_rows(self):
        context = {
            "entries": [
                context_entry("wlfw_start", "0x1000"),
                context_entry("wlfw_cap_qmi", "0x1008"),
            ]
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir = root / "out"
            out_dir.mkdir()
            summary = v2243.build_summary(self.make_args(root, context), out_dir)
            private_path = root / summary["private_semantic_instruction_lines"]["path"]

        self.assertTrue(summary["pass"])
        self.assertEqual(summary["decision"], "v2243-user-uprobe-semantic-classifier-pass")
        self.assertEqual(summary["confidence_counts"], {"high": 1, "medium": 1})
        self.assertEqual(summary["missing_target_count"], 0)
        self.assertFalse(summary["public_policy"]["raw_disassembly_published"])
        self.assertTrue(private_path.name.endswith("private_semantic_instruction_lines.json"))

    def test_build_summary_requests_review_for_missing_target_or_low_key_confidence(self):
        context = {
            "entries": [
                context_entry("wlfw_start", "0x0", stdout=["0: d503201f \tnop"]),
                context_entry("wlfw_cap_qmi", "0x9999"),
            ]
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir = root / "out"
            out_dir.mkdir()
            summary = v2243.build_summary(self.make_args(root, context), out_dir)

        self.assertFalse(summary["pass"])
        self.assertEqual(summary["decision"], "v2243-user-uprobe-semantic-classifier-review-needed")
        self.assertEqual(summary["missing_target_count"], 1)
        self.assertEqual(summary["key_low_confidence_count"], 1)
        self.assertEqual(summary["review_needed"][0]["alignment"], "needs_manual_context")


if __name__ == "__main__":
    unittest.main()
