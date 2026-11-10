"""V5 actual module/reader/guest and authenticated host checks, host and ARM64."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_s22plus_stage2_diagnostics import compile_stage_fixture
from test_s22plus_pre_effect_return import compile_pre_effect, module_report
from test_s22plus_ml030_wire import KEY, ID, WIT, GOOD, record, w


def decode(data):
    return w.result(record(raw_bytes=data), WIT, KEY, ID, report_version=5)


class HciSnapshotTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='s22-hci-snapshot-')
        cls.out = Path(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def exercise(self, compiler, runner=()):
        folder = self.out/compiler
        exe = compile_stage_fixture(folder/'stage', compiler, snapshot=True)
        old = compile_stage_fixture(folder/'old', compiler)
        guest = compile_pre_effect(folder/'guest', compiler=compiler, guest=True, snapshot=True)
        module = compile_pre_effect(folder/'entry', compiler=compiler, snapshot=True)
        if runner:
            for file in (exe, old, guest, module):
                self.assertIn('ARM aarch64', subprocess.check_output(['file', file], text=True))

        def run(binary, args):
            p = subprocess.run([*runner, binary, *map(str, args)], capture_output=True, check=True, timeout=5)
            return p.stdout, p.stderr.decode().splitlines()

        def accepted(data):
            return int(subprocess.check_output([*runner, guest], input=data, timeout=5)) == 0

        # HCE rejection always retains the first predicate failure and cannot return.
        for hce in (1, 2, 3, 4, 0x80000000, 0xffffffff):
            data, trace = run(exe, (0, 1, -16, 1, 0, hce, 0, 0xffffffff))
            facts = decode(data)
            self.assertEqual(facts['hci_snapshot']['HCE'], hce)
            self.assertEqual(facts['stage2_observed'], 1)
            self.assertEqual(facts['stage2_failed'], 1)
            self.assertEqual(set(list(facts['stage2_conditions'].values())[1:]), {'UNOBSERVED'})
            self.assertFalse(facts['normal_return'])
            self.assertFalse(accepted(data))
            reads = [x.split()[-1] for x in trace[:trace.index('REPORT_DONE')] if ' read ' in x]
            expected = ['hci:8', 'hci:e4', 'hci:34']
            if hce in (1, 2, 3):
                expected += ['hci:30', 'hci:58', 'hci:78', 'hci:24', 'hci:20']
            self.assertEqual(reads, expected)
            self.assertNotIn('open rails', '\n'.join(trace))
            self.assertLess(len(data), 256)
            # The later non-observing call has the original three reads only.
            later = [x.split()[-1] for x in trace[trace.index('REPORT_DONE')+1:] if ' read ' in x]
            self.assertEqual(later, ['hci:8', 'hci:e4', 'hci:34'])

        # Stop before each extra read at the unchanged absolute deadline.
        for expiry in range(2, 8):
            data, trace = run(exe, (0, 1, -16, 1, 0, 1, expiry, 0xffffffff))
            facts = decode(data)
            expected = (1 << min(expiry - 1, 6)) - 1
            self.assertEqual(facts['hci_snapshot_captured'], expected)
            self.assertEqual(facts['operation_errno'], 16)
            self.assertFalse(accepted(data))

        # No added MMIO or changed decisions for HCE==0 and early refusals.
        for guard, early in [(g, 0) for g in range(2, 12)] + [(0, e) for e in range(4)]:
            args = (0, guard, -16, 1, early)
            data, trace = run(exe, args)
            previous, prior_trace = run(old, args)
            values, old_values = list(map(int, data.split())), list(map(int, previous.split()))
            self.assertEqual(values[:21], old_values[:21])
            self.assertEqual(values[21] & 0xffff, old_values[21])
            self.assertEqual(values[22], old_values[22])
            self.assertEqual(trace, prior_trace)
            facts = decode(data)
            if early in (1, 3):
                self.assertIsNone(facts['hci_hw_version'])
            else:
                self.assertEqual(facts['hci_hw_version'], values[2])
            if early == 2:
                # A HW_VERSION failure really read this register, even if 0.
                values[2] = 0
                self.assertEqual(decode((' '.join(map(str, values))+'\n').encode())['hci_hw_version'], 0)

        refused = module_report(module, 'refuse', runner)
        self.assertTrue(accepted(refused))
        self.assertEqual(decode(refused)['return_reason'], 'PRE_EFFECT_REJECTION')
        for scenario in ('refuse-held', 'refuse-pending', 'refuse-power-error', 'refuse-run-state',
                         'post-cover-expired', 'overlay-failed', 'rails-failed', 'probe-failed', 'stage2'):
            self.assertFalse(accepted(module_report(module, scenario, runner)))
        success = GOOD + [1 << 16, 0, 0x50000000, 0x7ff, 1] + [0]*6
        line = (' '.join(map(str, success))+'\n').encode()
        self.assertTrue(accepted(line))
        self.assertEqual(decode(line)['status'], 'UFS_LINK_COMPLETED')

        # New raw words cannot forge the certificate; schemas cannot mix.
        values = list(map(int, refused.split()))
        for index in range(23, 30):
            bad = values.copy(); bad[index] = 1
            line = (' '.join(map(str, bad))+'\n').encode()
            self.assertFalse(accepted(line))
            with self.assertRaises(ValueError): decode(line)
        for version in (1, 2, 3, 4):
            with self.assertRaises(ValueError):
                w.result(record(raw_bytes=refused), WIT, KEY, ID, report_version=version)

    def test_host_producer_reader_and_consumers(self):
        self.exercise('cc')

    def test_arm64_producer_reader_and_consumers(self):
        self.exercise('aarch64-linux-gnu-gcc', ('qemu-aarch64',))

    def test_impossible_capture_histories_rejected(self):
        base = [-16, 2, 0x40040000] + [0]*14 + [1, 1, 1 << 16, 0, 0x50000104, 2049, 63, 1] + [0]*5
        self.assertEqual(len(base), 30)
        decode((' '.join(map(str, base))+'\n').encode())
        for index, value in ((23, 0), (23, 2), (23, 64), (24, 0), (24, 4), (24, 1 << 32),
                             (1, 3), (22, 3 | (2 << 11) | (1 << 22)), (21, 0x40000104)):
            bad = base.copy(); bad[index] = value
            with self.subTest(index=index, value=value), self.assertRaises(ValueError):
                decode((' '.join(map(str, bad))+'\n').encode())
        bad = base.copy(); bad[23] = 1; bad[25] = 1
        with self.assertRaises(ValueError): decode((' '.join(map(str, bad))+'\n').encode())
        early = [-16, 1, 0] + [0]*14 + [1, 1, 1 << 16, 0, 0x50000000, 0] + [0]*7
        self.assertIsNone(decode((' '.join(map(str, early))+'\n').encode())['hci_hw_version'])

    def test_reachable_report_capacity(self):
        # Extra raw maxima occur only before all later UFS/power fields.
        refusal = [-16, 2, 0x4fffffff] + [0]*14 + [1, 1, (25 << 16) | (16 << 8),
                   0, 0x50000104, 2049, 63, 3] + [0xffffffff]*5
        # Later hardware may expose large status words but has no extra reads.
        later = [-4095, 6, 0x4fffffff, 1, 6, 1, 0xffffffff, 0xffffffff, 255,
                 0xffffffff, 1, 32, 0xffffffff, 0xffffffff, 0xffffffff, 0, -4095,
                 1, 1, (25 << 16) | (16 << 8), 0, 0x50000000, 0x7ff, 1] + [0]*6
        for values in (refusal, later):
            line = (' '.join(map(str, values))+'\n').encode()
            self.assertLess(len(line), 256)
            self.assertFalse(decode(line)['normal_return'])


if __name__ == '__main__':
    unittest.main()
