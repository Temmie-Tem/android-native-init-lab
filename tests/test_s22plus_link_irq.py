"""Terminal link interrupt samples from the real command and report functions."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_s22plus_cfg1_selection import V11, decode, success
from test_s22plus_hce_handoff import line
from test_s22plus_stage2_diagnostics import HEADERS, ROOT, SOURCE, compile_stage_fixture, function


def compile_link_fixture(out, compiler, version, *, extra=(), report=True):
    out.mkdir(parents=True)
    for header in HEADERS:
        path = out/header
        path.parent.mkdir(exist_ok=True)
        path.touch()
    (out/'linux/errno.h').write_text('#include_next <linux/errno.h>\n')
    fixture = """
static struct { struct g0q_link link; struct g0q_stage2_diag stage2; } board;
static struct { u32 records, claimed, triggered, acknowledged, reclaimed; int error; }
    power = {11, 2047, 2047, 2047, 0, 0};
static int operation_rc;
static unsigned stage = 6, usb_reason = 132352, usb_detail;
static bool usb_covered = true, usb_released = true;
#define G0Q_REPORT_SITE (G0Q_REPORT_TAG | board.stage2.site)
"""
    (out/'fixture-report.inc').write_text(fixture + function((SOURCE/'g0q_stage.c').read_text(),
                                                            'static int report('))
    flags = ['-DG0Q_PRE_EFFECT_RETURN', '-DG0Q_HCE_HANDOFF', '-DG0Q_RESET_CONFIG',
             '-DG0Q_DISABLED_UCRDY', '-DG0Q_STALE_UCCS_ACK', '-DG0Q_CFG1_DIAGNOSTICS',
             '-DG0Q_CFG1_ORDERED_SELECTION', *(['-DLINK_IRQ_FIXTURE_REPORT'] if report else [])]
    if version == 12:
        flags.append('-DG0Q_LINK_IRQ_DIAGNOSTICS')
    flags += list(extra)
    if compiler != 'cc':
        flags.append('-static')
    exe = out/'link'
    subprocess.run([compiler, '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-parameter', *flags, '-I', out, '-I', SOURCE,
                    ROOT/'tests/s22plus_ml030_hci_fixture.c', '-o', exe], check=True)
    return exe


class LinkIrqTests(unittest.TestCase):
    def test_physical_command_code_and_report(self):
        unexpected = {'link-lost': 0x480, 'irq-only': 4, 'mixed-irq': 0x80000584,
                      'full-irq': 0xffffffff}
        with tempfile.TemporaryDirectory() as tmp:
            for compiler, runner in (('cc', []), ('aarch64-linux-gnu-gcc', ['qemu-aarch64'])):
                paths = [compile_link_fixture(Path(tmp)/compiler/str(v), compiler, v) for v in (11, 12)]
                if runner:
                    self.assertIn('ARM aarch64', subprocess.check_output(['file', paths[1]], text=True))
                for case in (*unexpected, 'positive', 'no-uccs', 'no-device', 'bad-code', 'local-irq'):
                    with self.subTest(compiler=compiler, case=case):
                        old, new = [subprocess.run([*runner, exe, case, 'cfg1-clear'], check=True,
                                                   capture_output=True, timeout=5) for exe in paths]
                        self.assertEqual(old.stderr, new.stderr)
                        x, y = [list(map(int, run.stdout.split())) for run in (old, new)]
                        self.assertEqual(len(y), 33)
                        self.assertLessEqual(len(new.stdout), 256)
                        self.assertEqual(y[21], 12 << 28)
                        x[21] = y[21]
                        facts = decode(new.stdout, 12)
                        self.assertNotIn('link_irq', decode(old.stdout, 11))
                        with self.assertRaises(ValueError):
                            decode(old.stdout, 12)
                        if case in unexpected:
                            self.assertEqual(x[7], 0)
                            x[7] = unexpected[case]
                            self.assertEqual(new.stderr.splitlines(), [f'R:20={x[7]:x}'.encode()])
                            self.assertEqual(facts['link_irq'], dict(branch='UNEXPECTED_STATUS',
                                             raw=x[7], unexpected_bits=x[7] & ~0x500))
                            self.assertEqual((facts['operation_errno'], facts['status']), (5, 'NO_PROOF'))
                        elif case in ('local-irq', 'no-uccs'):
                            self.assertIsNone(facts['link_irq'])
                        else:
                            self.assertEqual(facts['link_irq']['branch'], 'COMPLETION')
                        self.assertEqual(x, y)

    def test_wide_arm_report_and_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = compile_stage_fixture(Path(tmp), 'aarch64-linux-gnu-gcc', **V11, link_irq_diagnostics=True)
            data = subprocess.check_output(['qemu-aarch64', exe, '0', '0', '-16', '1', '0', '24'],
                                           stderr=subprocess.DEVNULL)
            self.assertEqual(len(data.split()), 33)
            self.assertLessEqual(len(data), 256)
            self.assertEqual(decode(data, 12)['link_irq']['raw'], 0xffffffff)

    def test_module_error_after_link_completion(self):
        values = success(0)
        values[21] = 12 << 28
        values[0] = values[16] = -1
        facts = decode(line(values), 12)
        self.assertEqual(facts['link_irq']['branch'], 'COMPLETION')
        self.assertEqual(facts['status'], 'NO_PROOF')
        self.assertTrue(facts['recovery_return'])

    def test_impossible_terminal_words(self):
        valid = success(0)
        valid[21] = 12 << 28
        valid[0] = -5
        valid[7:10] = [0x504, 0, 0]
        self.assertEqual(decode(line(valid), 12)['link_irq']['unexpected_bits'], 4)
        for index, value in ((0, 0), (0, -110), (1, 5), (3, 0), (4, 5), (5, 0), (6, 9),
                             (7, 0), (7, 0x100), (7, 1 << 32), (8, 1), (9, 9), (30, 2)):
            with self.subTest(index=index, value=value):
                bad = valid.copy()
                bad[index] = value
                with self.assertRaises(ValueError):
                    decode(line(bad), 12)
