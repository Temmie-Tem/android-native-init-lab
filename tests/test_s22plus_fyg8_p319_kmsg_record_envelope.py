from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p319_kmsg_record_envelope.py"
)
SPEC = importlib.util.spec_from_file_location("p319_kmsg_record_envelope", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
envelope = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(envelope)


class P319KmsgRecordEnvelopeTests(unittest.TestCase):
    def test_plain_record(self) -> None:
        value = envelope.parse_record(b"6,10,25,-;plain message\n")
        self.assertEqual(value["facility_level"], 6)
        self.assertEqual(value["sequence"], 10)
        self.assertEqual(value["timestamp_us"], 25)
        self.assertEqual(value["flag"], "-")
        self.assertEqual(value["message"], b"plain message")
        self.assertEqual(value["dictionary"], [])

    def test_official_dictionary_shape_is_separate_from_message(self) -> None:
        value = envelope.parse_record(
            b"7,160,424069,-;pci_root PNP0A03:00: host bridge\n"
            b" SUBSYSTEM=acpi\n"
            b" DEVICE=+acpi:PNP0A03:00\n"
        )
        self.assertEqual(value["message"], b"pci_root PNP0A03:00: host bridge")
        self.assertEqual(
            value["dictionary"],
            [b" SUBSYSTEM=acpi", b" DEVICE=+acpi:PNP0A03:00"],
        )

    def test_unknown_header_extensions_are_preserved(self) -> None:
        value = envelope.parse_record(
            b"6,10,25,-,future=1,caller=T42;message\n"
        )
        self.assertEqual(
            value["header_extensions"], ["future=1", "caller=T42"]
        )

    def test_fragment_flag_is_accepted_without_merging_records(self) -> None:
        value = envelope.parse_record(b"6,10,25,c;fragment\n")
        self.assertEqual(value["flag"], "c")
        self.assertEqual(value["message"], b"fragment")

    def test_noncontinuation_second_line_is_rejected(self) -> None:
        with self.assertRaisesRegex(envelope.EnvelopeError, "leading space"):
            envelope.parse_record(b"6,10,25,-;message\nnot-dictionary\n")

    def test_terminal_newline_and_bounds_remain_strict(self) -> None:
        with self.assertRaisesRegex(envelope.EnvelopeError, "terminal newline"):
            envelope.parse_record(b"6,10,25,-;message")
        with self.assertRaisesRegex(envelope.EnvelopeError, "record length"):
            envelope.parse_record(b"6,10,25,-;" + b"x" * 4090 + b"\n")


if __name__ == "__main__":
    unittest.main()
