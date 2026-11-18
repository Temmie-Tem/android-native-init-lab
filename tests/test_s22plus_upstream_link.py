"""V13 upstream link tolerance from the real command, selection and report code."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_s22plus_cfg1_selection import V11, decode, success
from test_s22plus_hce_handoff import line
from test_s22plus_link_irq import compile_link_fixture
from test_s22plus_pre_effect_return import compile_pre_effect
from test_s22plus_stage2_diagnostics import compile_stage_fixture

V12_FLAGS = ['-DG0Q_LINK_IRQ_DIAGNOSTICS']
V13_FLAGS = ['-DG0Q_LINK_IRQ_DIAGNOSTICS', '-DG0Q_UPSTREAM_LINK']
# Cases that never observe UIC_ERROR: V13 must reproduce V12 exactly.
NO_UIC_ERROR = ('positive', 'no-uccs', 'no-device', 'bad-code', 'link-lost', 'local-irq')


def build(tmp, compiler, version, *, report=True):
    out = Path(tmp)/compiler/f'{version}-{int(report)}'
    return compile_link_fixture(out, compiler, 12, extra=V13_FLAGS[1:] if version == 13 else [],
                                report=report)


class UpstreamLinkTests(unittest.TestCase):
    def test_register_model_cases(self):
        """The fixture's own assertions encode each V13 branch."""
        cases = ('positive', 'irq-only', 'ue-then-complete', 'ue-then-fatal', 'ue-then-bad-code',
                 'ue-budget', 'mixed-irq', 'full-irq', 'link-lost', 'no-device', 'bad-code',
                 'no-uccs', 'local-irq', 'expired-cfg1', 'no-calibration', 'pre-command-irq',
                 'bit31-clear', 'active', 'old-completion', 'timer-disagreement')
        with tempfile.TemporaryDirectory() as tmp:
            for compiler, runner in (('cc', []), ('aarch64-linux-gnu-gcc', ['qemu-aarch64'])):
                exe = build(tmp, compiler, 13, report=False)
                if runner:
                    self.assertIn('ARM aarch64', subprocess.check_output(['file', exe], text=True))
                for case in cases:
                    for clear in ([], ['cfg1-clear']):
                        with self.subTest(compiler=compiler, case=case, clear=clear):
                            subprocess.run([*runner, exe, case, *clear], check=True,
                                           capture_output=True, timeout=5)

    def test_v12_parity_without_uic_error(self):
        """Without UIC_ERROR the link-phase MMIO trace and first 33 fields match V12."""
        with tempfile.TemporaryDirectory() as tmp:
            for compiler, runner in (('cc', []), ('aarch64-linux-gnu-gcc', ['qemu-aarch64'])):
                old, new = build(tmp, compiler, 12), build(tmp, compiler, 13)
                for case in NO_UIC_ERROR:
                    with self.subTest(compiler=compiler, case=case):
                        a, b = [subprocess.run([*runner, exe, case, 'cfg1-clear'], check=True,
                                               capture_output=True, timeout=5) for exe in (old, new)]
                        self.assertEqual(a.stderr, b.stderr)
                        x, y = [list(map(int, run.stdout.split())) for run in (a, b)]
                        self.assertEqual((len(x), len(y)), (33, 38))
                        self.assertLessEqual(len(b.stdout), 256)
                        self.assertEqual((x[21], y[21]), (12 << 28, 13 << 28))
                        x[21] = y[21]
                        self.assertEqual(x, y[:33])
                        self.assertEqual(y[34:], [0] * 4)
                        facts = decode(b.stdout, 13)
                        self.assertEqual(decode(a.stdout, 12)['link_irq'], facts['link_irq'])
                        if facts['link_poll']:
                            self.assertFalse(facts['link_poll']['uic_error_seen'])

    def test_uic_error_outcomes_and_decoder(self):
        expected = {
            'ue-then-complete': (0, 'COMPLETION', 0x504, 31, True),
            'irq-only': (-110, None, 0x4, 31, False),
            'ue-then-fatal': (-5, 'UNEXPECTED_STATUS', 0x84, 31, True),
            'ue-then-bad-code': (-5, 'COMPLETION', 0x404, 31, True),
            'ue-budget': (-110, None, 0x4, 3, True),
        }
        with tempfile.TemporaryDirectory() as tmp:
            for compiler, runner in (('cc', []), ('aarch64-linux-gnu-gcc', ['qemu-aarch64'])):
                exe = build(tmp, compiler, 13)
                for case, (rc, branch, seen, mask, line_reset) in expected.items():
                    with self.subTest(compiler=compiler, case=case):
                        run = subprocess.run([*runner, exe, case], check=True,
                                             capture_output=True, timeout=5)
                        self.assertLessEqual(len(run.stdout), 256)
                        values = list(map(int, run.stdout.split()))
                        self.assertEqual(len(values), 38)
                        facts = decode(run.stdout, 13)
                        self.assertEqual(facts['operation_errno'], -rc)
                        self.assertEqual((facts['link_irq'] or {}).get('branch'), branch)
                        poll = facts['link_poll']
                        self.assertEqual((poll['seen'], poll['uec_read_mask']), (seen, mask))
                        self.assertTrue(poll['uic_error_seen'])
                        if case != 'irq-only':
                            self.assertEqual(poll['uec']['PA'], dict(raw=0x80000010, error=True, code=0x10,
                                                                     reserved_set=False))
                            self.assertTrue(poll['pa_line_reset'])
                        if case == 'ue-then-complete':
                            self.assertEqual(poll['uec']['DL']['code'], 0x2000)
                            self.assertEqual(facts['status'], 'UFS_LINK_COMPLETED')
                            self.assertTrue(facts['normal_return'])
                        else:
                            self.assertEqual(facts['status'], 'NO_PROOF')
                            self.assertTrue(facts['recovery_return'])
                        with self.assertRaises(ValueError):
                            decode(run.stdout, 12)

    def test_wide_arm_report_fits_envelope(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = compile_stage_fixture(Path(tmp), 'aarch64-linux-gnu-gcc', **V11,
                                        link_irq_diagnostics=True, upstream_link=True)
            data = subprocess.check_output(['qemu-aarch64', exe, '0', '0', '-16', '1', '0', '24'],
                                           stderr=subprocess.DEVNULL)
            self.assertEqual(len(data.split()), 38)
            self.assertLessEqual(len(data), 256)
            self.assertEqual(list(map(int, data.split()))[33:37], [2**32 - 1, 31, 2**32 - 1, 2**32 - 1])

    def test_full_width_link_path_fits_envelope(self):
        """Every raw hardware word at full width on the issued-link path."""
        with tempfile.TemporaryDirectory() as tmp:
            exe = build(tmp, 'aarch64-linux-gnu-gcc', 13)
            run = subprocess.run(['qemu-aarch64', exe, 'full-irq'], check=True,
                                 capture_output=True, timeout=5)
            values = list(map(int, run.stdout.split()))
            self.assertEqual(values[33:37], [2**32 - 1, 31, 2**32 - 1, 2**32 - 1])
            self.assertEqual(values[37], 0x70707ff)
            self.assertLessEqual(len(run.stdout), 256)
        # Synthetic bound: every unconstrained u32 at 10 digits, bounded fields
        # at their reachable maxima (11 fixed RPMh records, errno, flags).
        wide = 2**32 - 1
        worst = [-110, 6, wide, 1, 6, 1, wide, wide, 255, wide, 1, 11, 2047, 2047, 2047,
                 2047, -110, 1, 1, wide, wide, wide, wide, wide, 1, wide, 1024, 1, 11, wide,
                 3, wide, wide, wide, 31, wide, wide, 0x70707ff]
        self.assertEqual(len(worst), 38)
        self.assertLessEqual(len(line(worst)), 256)

    def test_guest_and_host_agree_on_success_lines(self):
        """The guest's pre-return check and the host decoder accept the same V13 lines."""
        valid = success(0)
        valid[21] = 13 << 28
        valid[7] = 0x504
        valid += [0x504, 31, 0x80000010, 0x80002000, 0x10000]
        variants = [valid]
        for index, value in ((33, 0x500), (33, 0x400), (34, 3), (34, 32), (35, 0), (37, 1 << 30),
                             (37, 0x70707ff), (7, 0x400), (33, 0x584)):
            bad = valid.copy()
            bad[index] = value
            variants.append(bad)
        no_error = success(0)
        no_error[21] = 13 << 28
        no_error += [0x400, 0, 0, 0, 0]
        variants.append(no_error)
        with tempfile.TemporaryDirectory() as tmp:
            for compiler, runner in (('cc', ()), ('aarch64-linux-gnu-gcc', ('qemu-aarch64',))):
                guest = compile_pre_effect(Path(tmp)/compiler, compiler=compiler, guest=True, **V11,
                                           link_irq_diagnostics=True, upstream_link=True)
                for values in variants:
                    with self.subTest(compiler=compiler, values=values[33:]):
                        try:
                            host = decode(line(values), 13)['status'] == 'UFS_LINK_COMPLETED'
                        except ValueError:
                            host = False
                        guest_ok = int(subprocess.check_output([*runner, guest], input=line(values),
                                                               timeout=5)) == 0
                        self.assertEqual(guest_ok, host)
                self.assertTrue(int(subprocess.check_output([*runner, guest], input=line(valid))) == 0)

    def test_selection_sits_between_calibration_and_lane_clocks(self):
        """V13 places QUNIPRO_SEL where ufs_qcom_power_up_sequence does."""
        from test_s22plus_stage2_diagnostics import SOURCE, function
        stage = (SOURCE/'g0q_stage.c').read_text()
        phy_on, run = function(stage, 'static int phy_on('), function(stage, 'static int run(')
        calibrate = phy_on.index('g0q_phy_calibrate(')
        select = phy_on.index('g0q_hci_select_unipro(')
        self.assertLess(calibrate, select)
        self.assertLess(run.index('rc = phy_on();'), run.index('rc = symbol_lanes();'))
        self.assertLess(run.index('rc = symbol_lanes();'), run.index('g0q_hci_link_once('))
        hci = (SOURCE/'waipio_hci.c').read_text()
        link = function(hci, 'int g0q_hci_link_once(')
        self.assertIn('#ifdef G0Q_UPSTREAM_LINK\n\t/* QUNIPRO_SEL was written', link)

    def test_selection_and_lane_failures_from_the_real_formatter(self):
        """Stage four/five/six outcomes after the moved selection decode as reachable."""
        import os
        with tempfile.TemporaryDirectory() as tmp:
            for compiler, runner in (('cc', ()), ('aarch64-linux-gnu-gcc', ('qemu-aarch64',))):
                exe = compile_stage_fixture(Path(tmp)/compiler, compiler, **V11,
                                            link_irq_diagnostics=True, upstream_link=True)
                def run(case, fault=0):
                    env = dict(os.environ, V13_CASE=str(case))
                    return subprocess.run([*runner, exe, str(fault), '0', '-16', '1', '0'], env=env,
                                          check=True, capture_output=True, timeout=5)
                expected = {1: (4, 5, 'BUDGET_EXPIRED'), 2: (5, 19, 'BIT_SET_BUDGET_PASS'),
                            3: (6, 16, 'BIT_SET_BUDGET_PASS')}
                for case, (stage, errno, outcome) in expected.items():
                    with self.subTest(compiler=compiler, case=case):
                        out = run(case)
                        facts = decode(out.stdout, 13)
                        self.assertEqual((facts['stage'], facts['operation_errno']), (stage, errno))
                        self.assertEqual(facts['cfg1']['outcome'], outcome)
                        self.assertFalse(facts['link_issued'])
                        self.assertIsNone(facts['link_poll'])
                # The stage-six core-rate refusal (-ERANGE) after selection.
                events = run(3).stderr.decode().splitlines()
                rate = [int(e.split()[0]) for e in events if e.split()[1:] == ['rate-get', 'core']][-1]
                facts = decode(run(3, rate).stdout, 13)
                self.assertEqual((facts['stage'], facts['operation_errno']), (6, 34))
                self.assertEqual(facts['cfg1']['outcome'], 'BIT_SET_BUDGET_PASS')

    def test_impossible_v13_words(self):
        valid = success(0)
        valid[21] = 13 << 28
        valid += [0x504, 31, 0x80000010, 0, 0]
        valid[7] = 0x504
        facts = decode(line(valid), 13)
        self.assertEqual(facts['status'], 'UFS_LINK_COMPLETED')
        self.assertTrue(facts['link_poll']['pa_line_reset'])
        for index, value in ((33, 0x400), (33, 0x80), (34, 2), (34, 32), (37, 1 << 30),
                             (7, 0x484), (34, 0), (34, 1)):
            with self.subTest(index=index, value=value):
                bad = valid.copy()
                bad[index] = value
                if index == 34 and value == 1:
                    bad[37] = 0
                    self.assertEqual(set(decode(line(bad), 13)['link_poll']['uec']), {'PA'})
                    bad[37] = 1
                    with self.assertRaises(ValueError):
                        decode(line(bad), 13)
                    continue
                if index == 34 and value == 0:
                    bad[35] = 0
                    bad[33] = 0x400
                    bad[7] = 0x400
                    self.assertEqual(decode(line(bad), 13)['link_poll']['uec_read_mask'], 0)
                    continue
                with self.assertRaises(ValueError):
                    decode(line(bad), 13)


if __name__ == '__main__':
    unittest.main()
