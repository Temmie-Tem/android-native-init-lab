from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
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
    @classmethod
    def setUpClass(cls) -> None:
        compiler = shutil.which("gcc")
        if compiler is None:
            raise AssertionError("host C compiler is unavailable")
        cls.tempdir = tempfile.TemporaryDirectory(prefix="p320-kmsg-envelope-")
        source = Path(cls.tempdir.name) / "fixture.c"
        source.write_text(
            "#include <stdint.h>\n"
            "#include <stddef.h>\n"
            "#include <stdio.h>\n"
            + envelope.P320_C_SOURCE
            + r'''
int main(void) {
    char record[P320_KMSG_ENVELOPE_MAX_RECORD + 1U];
    size_t length = fread(record, 1U, sizeof(record), stdin);
    if (length > P320_KMSG_ENVELOPE_MAX_RECORD) return 9;
    struct p320_kmsg_record_view view = {0};
    long rc = p320_kmsg_record_envelope(record, length, &view);
    if (rc != 0) { printf("ERR %ld\n", rc); return 2; }
    printf("OK %u %llu %llu %c %u %u %zu ", view.facility_level,
           (unsigned long long)view.sequence,
           (unsigned long long)view.timestamp_us, view.flag,
           view.extension_fields, view.dictionary_lines, view.message_length);
    for (size_t i = 0; i < view.message_length; ++i)
        printf("%02x", (unsigned char)view.message[i]);
    printf("\n");
    return 0;
}
''',
            encoding="ascii",
        )
        cls.fixture = Path(cls.tempdir.name) / "fixture"
        completed = subprocess.run(
            [
                compiler,
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-o",
                str(cls.fixture),
                str(source),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError((completed.stdout + completed.stderr).decode())

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def run_c(self, record: bytes) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [str(self.fixture)],
            input=record,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

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

    def test_compiled_c_matches_positive_envelope_shapes(self) -> None:
        records = (
            b"6,10,25,-;plain message\n",
            b"7,160,424069,-;pci root\n SUBSYSTEM=acpi\n DEVICE=+acpi:x\n",
            b"6,10,25,-,future=1,caller=T42;message\n",
            b"6,10,25,c;fragment\n",
        )
        for record in records:
            expected = envelope.parse_record(record)
            completed = self.run_c(record)
            self.assertEqual(completed.returncode, 0, completed.stdout)
            fields = completed.stdout.decode("ascii").strip().split()
            self.assertEqual(fields[0], "OK")
            self.assertEqual(int(fields[1]), expected["facility_level"])
            self.assertEqual(int(fields[2]), expected["sequence"])
            self.assertEqual(int(fields[3]), expected["timestamp_us"])
            self.assertEqual(fields[4], expected["flag"])
            self.assertEqual(int(fields[5]), len(expected["header_extensions"]))
            self.assertEqual(int(fields[6]), len(expected["dictionary"]))
            self.assertEqual(int(fields[7]), len(expected["message"]))
            self.assertEqual(bytes.fromhex(fields[8]), expected["message"])

    def test_compiled_c_rejects_the_same_body_failures(self) -> None:
        for record in (
            b"6,10,25,-;message",
            b"6,10,25,-;message\nnot-dictionary\n",
        ):
            with self.assertRaises(envelope.EnvelopeError):
                envelope.parse_record(record)
            self.assertNotEqual(self.run_c(record).returncode, 0)


if __name__ == "__main__":
    unittest.main()
