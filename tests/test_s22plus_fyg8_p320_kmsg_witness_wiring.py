from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p320_kmsg_witness_wiring.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p320_kmsg_witness_wiring", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load P3.20 wiring")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P320KmsgWitnessWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        compiler = shutil.which("gcc")
        if compiler is None:
            raise AssertionError("host C compiler is unavailable")
        cls.tempdir = tempfile.TemporaryDirectory(prefix="p320-kmsg-wiring-")
        directory = Path(cls.tempdir.name)
        source = directory / "fixture.c"
        source.write_bytes(
            cls.module.build_fixture_source()
            + rb'''
#include <stdio.h>

int main(int argc, char **argv) {
    for (int index = 1; index < argc; ++index) {
        long rc = p320_kmsg_witness_observe_v2(argv[index], strlen(argv[index]));
        if (rc != 0) {
            printf("ERR %ld\n", rc);
            return 2;
        }
    }
    printf("OK %u %u %u %u %u %u %u %u\n",
        g_p319_witness.witness_mask,
        g_p319_witness.probe_count,
        g_p319_witness.irq_count,
        g_p319_witness.initial_status_count,
        g_p319_witness.classification_form1_count,
        g_p319_witness.classification_form2_count,
        g_p319_witness.deferred_status_count,
        g_p319_witness.malformed_count);
    return 0;
}
'''
        )
        cls.fixture = directory / "fixture"
        completed = subprocess.run(
            [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", "-o", str(cls.fixture), str(source)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError((completed.stdout + completed.stderr).decode("ascii", "replace"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def run_c(self, *records: bytes) -> list[str]:
        completed = subprocess.run(
            [str(self.fixture), *(record.decode("ascii") for record in records)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            self.fail(f"C wiring rejected fixture: {completed.stdout}{completed.stderr}")
        return completed.stdout.strip().split()

    def test_python_transform_returns_only_human_message_and_preserves_source(self) -> None:
        record = (
            b"6,10,25,-,future=1,caller=T42;"
            b"pdic_max77705: max77705_muic_detect_dev USBC1:0x27, USBC2:0x05, BC:0x82\n"
            b" pdic_max77705: max77705_muic_detect_dev USBC1:0x00, USBC2:0x00, BC:0x00\n"
        )
        original = bytes(record)
        expected = b"pdic_max77705: max77705_muic_detect_dev USBC1:0x27, USBC2:0x05, BC:0x82"
        self.assertEqual(self.module.human_message(record), expected)
        self.assertEqual(self.module.record_to_witness_message(record), expected)
        self.assertEqual(self.module.transform_record(record), expected)
        self.assertEqual(record, original)

    def test_dictionary_lines_are_excluded_from_stateless_transform(self) -> None:
        records = (
            b"6,11,26,-;not-a-witness\n"
            b" pdic_max77705: max77705_muic_check_new_dev vps table match found at i(9), CDP\n",
            b"6,12,27,-;still-not-a-witness\n"
            b" max77705: max77705_usbc_probe: probing Complete..\n",
        )
        self.assertEqual(self.module.transform_records(records), [
            b"not-a-witness",
            b"still-not-a-witness",
        ])

    def test_unknown_extensions_and_c_flag_do_not_create_fragment_state(self) -> None:
        first = b"6,20,30,c,unknown=1,caller=C7;fragment-one\n"
        second = b"6,21,31,c,unknown=2;fragment-two\n"
        self.assertEqual(self.module.transform_records((first, second)), [
            b"fragment-one",
            b"fragment-two",
        ])
        self.assertEqual(self.run_c(first, second)[0], "OK")
        # The two records remain two independent messages; no witness is
        # synthesized from their concatenation.
        self.assertEqual(self.run_c(first, second)[1:7], ["0", "0", "0", "0", "0", "0"])

    def test_retained_runtime_and_parser_are_byte_bound(self) -> None:
        runtime = self.module.load_retained_runtime()
        self.assertEqual(len(runtime), self.module.RETAINED_RUNTIME_SIZE)
        parser = self.module.extract_retained_parser(runtime)
        self.assertIn(b"#define P319_WITNESS_ABI_VERSION 2U", parser)
        self.assertIn(b"static long p319_witness_observe_v2", parser)
        self.assertLess(parser.find(b"p319_witness_observe_v2"), len(parser))
        with self.assertRaises(self.module.WiringError):
            self.module.extract_retained_parser(runtime.replace(
                b"#define P319_WITNESS_ABI_VERSION 2U",
                b"#define P319_WITNESS_ABI_VERSION 1U",
                1,
            ))

    def test_c_wiring_passes_human_message_to_existing_parser(self) -> None:
        record = (
            b"6,30,40,-,future=1;"
            b"pdic_max77705: max77705_muic_check_new_dev vps table match found at i(9), CDP\n"
            b" pdic_max77705: max77705_muic_detect_dev USBC1:0x27, USBC2:0x05, BC:0x82\n"
        )
        fields = self.run_c(record)
        self.assertEqual(fields, ["OK", "8", "0", "0", "0", "1", "0", "0", "0"])

    def test_c_wiring_accepts_fragment_flag_without_reassembly(self) -> None:
        record = (
            b"6,31,41,c,extension=yes;"
            b"max77705: max77705_usbc_probe: probing Complete..\n"
            b" pdic_max77705: max77705_muic_detect_dev USBC1:0x00, USBC2:0x00, BC:0x00\n"
        )
        fields = self.run_c(record)
        self.assertEqual(fields[0:3], ["OK", "1", "1"])
        self.assertEqual(fields[3:], ["0", "0", "0", "0", "0", "0"])

    def test_c_wiring_source_has_one_way_message_seam(self) -> None:
        source = self.module.P320_C_WIRING_SOURCE
        self.assertEqual(source.count("p320_kmsg_record_envelope"), 1)
        self.assertEqual(source.count("p319_witness_observe_v2"), 1)
        self.assertIn("view.message, view.message_length", source)
        self.assertNotIn("view.dictionary", source)
        self.assertNotIn("dictionary_lines", source)
        self.assertNotIn("fragment_", source.lower())


if __name__ == "__main__":
    unittest.main()
