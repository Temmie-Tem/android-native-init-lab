"""Real C coverage/unwind/deadlines joined to the explicitly selected wire schema."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from test_s22plus_ml030_transport import compile_fixture
from test_s22plus_ml030_wire import KEY, ID, WIT, GOOD, record, w


class UsbAdmissionTest(unittest.TestCase):
    def test_reason_numbers_match_actual_kernel_header(self):
        header = Path(w.__file__).parent/'transport/g0q_rpmh.h'
        enum = header.read_text().split('enum g0q_usb_reason {', 1)[1].split('};', 1)[0]
        names = re.findall(r'G0Q_([A-Z_]+)', enum)
        aliases = {'USB_OK':'OK', 'USB_RUN_STATE':'RUN_STATE', 'USB_CEILING':'COVER_CEILING'}
        self.assertEqual(tuple(aliases.get(name, name) for name in names), w.USB_REASONS)

    def test_actual_leaf_and_retry_reports_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            exe = compile_fixture(Path(temp), 'cc', ['-Wno-sign-compare'], 's22plus_ml034_usb_fixture.c')
            lines = subprocess.check_output([exe], text=True, timeout=5).splitlines()
        self.assertTrue(lines[-1].startswith('PASS actual'))
        self.assertGreater(len(lines), 50)
        for line in lines[:-1]:
            with self.subTest(line=line):
                facts = w.result(record(raw_bytes=(line+'\n').encode()), WIT, KEY, ID, report_version=2)
                self.assertFalse(facts['normal_return'])
                self.assertNotIn('control_nonce', facts)

    def test_explicit_schema_and_success_conditions(self):
        for values, version in ((GOOD, 2), (GOOD+[1<<16, 0], 1)):
            with self.assertRaisesRegex(ValueError, 'status line'):
                w.result(record(values), WIT, KEY, ID, report_version=version)
        for attempts, first in ((1, 0), (2, 5), (25, 16)):
            self.assertTrue(w.result(record(GOOD+[(attempts<<16)|(first<<8), 0]),
                                     WIT, KEY, ID, report_version=2)['normal_return'])
        for bad in (GOOD+[0, 0], GOOD+[1<<24, 0], GOOD+[(2<<16), 0],
                    GOOD+[(1<<16)|(5<<8), 0], GOOD+[1<<16, 1]):
            with self.assertRaises(ValueError):
                w.result(record(bad), WIT, KEY, ID, report_version=2)

    def test_malformed_failure_does_not_claim_a_branch(self):
        cases = [(-19, 5|(5<<8)|(25<<16), 0), (-19, 20, 0),
                 (-5, 10|(1<<16), 0), (-16, 19|(1<<16), 0x444),
                 (-16, 19|(1<<16), 0x10455), (-16, 13|(1<<16), 4<<16),
                 (-16, 18|(1<<16), 2), (-16, 17|(1<<16), 0),
                 (-16, 18, 0), (-16, 18|(2<<16), 0)]
        for rc, word, detail in cases:
            with self.subTest(word=word), self.assertRaises(ValueError):
                w.result(record([rc]+[0]*18+[word, detail]), WIT, KEY, ID, report_version=2)

    def test_worst_case_line_and_load_error_preserve_original_transport(self):
        maxima = [-(1<<31) if i in (0, 16) else (1<<32)-1 for i in range(21)]
        line = (' '.join(map(str, maxima))+'\n').encode()
        self.assertEqual(len(line), 233)
        self.assertLess(len(line), 256)
        for version in (1, 2):
            facts = w.result(record(load=19), WIT, KEY, ID, report_version=version)
            self.assertEqual(facts['load_errno'], 19)
            self.assertNotIn('usb_reason', facts)


if __name__ == '__main__':
    unittest.main()
