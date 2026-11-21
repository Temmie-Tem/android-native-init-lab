"""MAX77705 Stage 1 observer against a simulated device (host build, no hardware)."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'workspace/public/src/mainline/s22plus_canary_h0'
sys.path.insert(0, str(SRC))
import max77705_record as rec


class ObserverFakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.exe = Path(cls.tmp.name) / 'fake'
        subprocess.run(['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-O1',
                        '-I', str(SRC), str(SRC / 'max77705_observe_fake.c'), '-o', str(cls.exe)],
                       check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_fake(self, scenario):
        out = subprocess.run([str(self.exe), scenario], capture_output=True, text=True, check=True).stdout
        lines = out.splitlines()
        meta = dict(kv.split('=') for kv in lines[0].split())
        return meta, rec.decode(bytes.fromhex(lines[1]))

    def test_autonomous_switch_is_seen(self):
        meta, d = self.run_fake('autonomous')
        self.assertEqual(meta['bad_writes'], '0')
        self.assertEqual(d['adapter'], 'ok')
        self.assertEqual(d['events'][0]['kind'], 'begin')
        self.assertEqual(d['events'][0]['ctrl1'], 0x3f)
        ev = [e for e in d['events'] if e['kind'] == 'on-event']
        self.assertTrue(ev and 'VBUSDetI' in ev[0]['uic_bits'] and ev[0]['ctrl1'] == 0x09)
        self.assertEqual(rec.verdict(d), 'OPEN_THEN_COM_USB_AFTER_ATTACH')

    def test_open_stays_open(self):
        _, d = self.run_fake('open_stays')
        self.assertEqual(rec.verdict(d), 'OPEN_UNCHANGED_AFTER_ATTACH')
        periodic = [e for e in d['events'] if e['kind'] == 'periodic']
        self.assertGreaterEqual(len(periodic), 10)  # ~every 10 s over 120 s

    def test_stale_latch_is_cleared_and_kept(self):
        _, d = self.run_fake('stale_latch')
        self.assertTrue(d['initial_uic_valid'])
        self.assertIn('APCmdResI', d['initial_uic_bits'])
        self.assertEqual(d['events'][0]['ctrl1'], 0x3f)  # not the stale 0x77

    def test_timeout_and_bad_echo(self):
        _, d = self.run_fake('timeout')
        self.assertEqual(d['events'][0]['ctrl1_status'], 'timeout')
        self.assertEqual(rec.verdict(d), 'NO_PROOF_NO_CONTROL1_READ')
        _, d = self.run_fake('bad_echo')
        self.assertEqual(d['events'][0]['ctrl1_status'], 'proto')

    def test_identity_mismatch_sends_no_command(self):
        meta, d = self.run_fake('no_identity')
        self.assertEqual(d['adapter'], 'identity-mismatch')
        self.assertEqual(meta['bus_writes'], '0')
        self.assertEqual(d['commands'], 0)

    def test_write_allowlist(self):
        out = subprocess.run([str(self.exe), 'write_probe'], capture_output=True, text=True,
                             check=True).stdout.strip()
        self.assertEqual(out, 'rejected=11111 bus_writes=0 writes_rejected=5')

    def test_command_budget_and_ring(self):
        meta, d = self.run_fake('flood')
        self.assertLessEqual(int(meta['commands']), 32)
        self.assertEqual(meta['bad_writes'], '0')
        self.assertGreater(d['events_total'], 48)
        times = [e['t_ms'] for e in d['events']]
        self.assertEqual(times[:24], sorted(times[:24]))
        self.assertEqual(times[24:], sorted(times[24:]))
        self.assertLess(times[23], times[24])

    def test_only_control1_read_opcode_in_source(self):
        import re
        text = (SRC / 'max77705-usb-observe.h').read_text()
        calls = re.findall(r'mx_write\(MX_USBC_ADDR, (\w+), (\w+)\)', text)
        self.assertEqual(sorted(set(calls)), [('MX_AP_DATAOUT0', 'MX_CTRL1_READ'),
                                              ('MX_AP_DATAOUT_END', '0x00')])
        self.assertEqual(text.count('mx_raw_write('), 2)  # definition + the one allowlisted call
        self.assertNotIn('CTRL1_WRITE', text)
        self.assertNotIn('I2C_SLAVE', text)


if __name__ == '__main__':
    unittest.main()
