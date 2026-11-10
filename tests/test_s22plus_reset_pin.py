"""Dedicated-pad guard and actual GCC/reset-pulse order, host and ARM64."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_s22plus_stage2_diagnostics import SOURCE, ROOT, function


class ResetPinTests(unittest.TestCase):
    def exercise(self, compiler, runner):
        with tempfile.TemporaryDirectory(prefix='s22-reset-pin-') as tmp:
            folder = Path(tmp)
            (folder/'reset.inc').write_text(function((SOURCE/'g0q_stage.c').read_text(),
                                                    'static int reset_host_and_device('))
            exe = folder/'reset'
            flags = ['-static'] if runner else []
            subprocess.run([compiler, '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror',
                '-DG0Q_RESET_CONFIG', '-DG0Q_HCE_HANDOFF', '-DG0Q_PRE_EFFECT_RETURN',
                *flags, '-I', SOURCE, '-I', folder,
                ROOT/'tests/s22plus_reset_pin_fixture.c', '-o', exe], check=True)
            if runner:
                self.assertIn('ARM aarch64', subprocess.check_output(['file',exe], text=True))

            def run(ctl=0xb, io=1, scenario=0, expiry=0):
                out = subprocess.check_output([*runner, exe, *map(str,(ctl,io,scenario,expiry))],
                                               text=True, timeout=5).splitlines()
                return list(map(int, out[-1].split()[1:])), out[:-1]

            for ctl in (0, 3, 0xa, 0x8000000b, 0xffffffff):
                facts, trace = run(ctl=ctl)
                self.assertEqual(facts[:4], [-16,0,0,0])
                self.assertEqual(trace, ['budget 1','read IO 1',f'read CTL {ctl}'])
            facts, trace = run(io=0)
            self.assertEqual(facts[:4], [-16,0,0,0])
            for io in (1,3,0x80000001,0xffffffff):
                facts, trace = run(io=io)
                self.assertEqual(facts, [0,2,1,1,io])
                self.assertEqual([x for x in trace if x.startswith('write')],
                                 [f'write IO {io & ~1}', f'write IO {io}'])
                self.assertEqual([x for x in trace if x.startswith('sleep')],
                                 ['sleep 200 210','sleep 1000 1100','sleep 10 15','sleep 10 15'])
                self.assertEqual(sum(x.startswith('read CTL') for x in trace), 2)
                self.assertLess(trace.index('GCC deassert'), next(i for i,x in enumerate(trace) if x.startswith('write')))
            for scenario in (3,4):
                facts, trace = run(scenario=scenario)
                self.assertEqual(facts[:4], [-16,0,1,1])
                self.assertFalse(any(x.startswith('write') for x in trace))
            for scenario in (5,6):
                facts, trace = run(io=0x80000001, scenario=scenario)
                self.assertEqual(facts[:4], [-5,2,1,1])
                self.assertEqual([x for x in trace if x.startswith('write')],
                                 ['write IO 2147483648','write IO 2147483649'])
            for expiry, counts in ((1,[0,0,0]),(2,[0,1,1]),(3,[2,1,1])):
                facts, trace = run(expiry=expiry)
                self.assertEqual(facts[:4], [-110,*counts])
                if expiry == 1: self.assertEqual(trace, ['budget 1'])
            for scenario, counts in ((7,[0,1,0]),(8,[0,1,1])):
                facts, trace = run(scenario=scenario)
                self.assertEqual(facts[:4], [-5,*counts])

    def test_host_actual_reset_function(self): self.exercise('cc', ())
    def test_arm64_actual_reset_function(self): self.exercise('aarch64-linux-gnu-gcc', ('qemu-aarch64',))


if __name__ == '__main__': unittest.main()
