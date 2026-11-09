"""Actual C stage/report -> bounded reader -> authenticated v3 decoder, H0 only."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from test_s22plus_ml030_wire import KEY, ID, WIT, GOOD, record, w

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'workspace/public/src/mainline/s22plus_ufs_link_h0'
HEADERS = ('linux/types.h', 'linux/bitfield.h', 'linux/delay.h', 'linux/io.h',
           'linux/ktime.h', 'ufs/ufshci.h', 'ufs/unipro.h')


def function(text, signature):
    start = text.index(signature)
    return text[start:text.index('\n}\n', start)+3]


def compile_stage_fixture(out, compiler='cc', *, source=SOURCE, legacy=False):
    """Extract byte-identical production functions; substitute kernel APIs only."""
    out.mkdir(parents=True, exist_ok=True)
    for header in HEADERS:
        path = out/header
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    (out/'linux/errno.h').write_text('#include_next <linux/errno.h>\n')
    stage = (source/'g0q_stage.c').read_text()
    (out/'board.inc').write_text(stage[stage.index('struct board {'):stage.index('static int remaining(')])
    signatures = ('static int remaining(', 'static int report(', 'static int supply(',
                  'static int rate(', 'static int host_supplies(', 'static int run(')
    (out/'stage.inc').write_text('\n'.join(function(stage, s) for s in signatures))
    (out/'reader.inc').write_text(function((source/'link-runtime.h').read_text(), 'static int ml030_read_result('))
    exe = out/'stage2'
    flags = ['-static'] if compiler != 'cc' else []
    if legacy:
        flags.append('-DLEGACY_STAGE2')
    subprocess.run([compiler, '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-parameter', '-Wno-unused-variable', *flags,
                    '-I', out, '-I', source, ROOT/'tests/s22plus_stage2_fixture.c', '-o', exe], check=True)
    return exe


def execute(exe, *, runner=(), fault=0, guard=0, error=-16, hcs=1, early=0):
    result = subprocess.run([*runner, exe, *map(str, (fault, guard, error, hcs, early))],
                            check=True, capture_output=True, timeout=5)
    values = list(map(int, result.stdout.split()))
    facts = w.result(record(raw_bytes=result.stdout), WIT, KEY, ID, report_version=3)
    return values, facts, result.stderr.decode().splitlines()


class StageTwoDiagnosticsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='s22-stage2-')
        cls.exe = compile_stage_fixture(Path(cls.temp.name)/'host')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def exercise(self, exe, runner=()):
        values, facts, trace = execute(exe, runner=runner)
        self.assertEqual((values[0], values[1]), (-5, 3))
        self.assertEqual(facts['stage2_observed'], 0x7ff)
        self.assertIsNone(facts['stage2_failure'])
        self.assertFalse(facts['normal_return'])
        # The observed region ends at the intentionally failed stage-three stub.
        boundary = next(i for i, row in enumerate(trace) if row.endswith('later reset'))
        trace = trace[:boundary]
        expected_sites = {(1,1), (1,2), (1,3), (1,4), (2,5)}
        for component in (3,4):
            expected_sites |= {(component, op) for op in (1,6,7)}
        for component in (5,6,7):
            expected_sites |= {(component, op) for op in (8,9,10,11,12,13,14,15,20)}
        expected_sites |= {(8,op) for op in (8,9,10,13,14,16,17,18,19,20)}
        seen = set()
        for guard in range(1,12):
            with self.subTest(guard=guard):
                values, facts, rows = execute(exe, runner=runner, guard=guard)
                self.assertEqual((values[0],values[1]), (-16,2))
                self.assertEqual(facts['stage2_observed'], (1 << guard)-1)
                self.assertEqual(facts['stage2_failed'], 1 << (guard-1))
                self.assertEqual(list(facts['stage2_conditions'].values()),
                                 ['PASS']*(guard-1)+['FAIL']+['UNOBSERVED']*(11-guard))
                # Two version reads followed by exactly the evaluated predicates.
                first_reads = rows[:rows.index('REPORT_DONE')]
                self.assertEqual(sum(' read ' in row for row in first_reads), 2+guard)
                self.assertNotIn(' open rails', '\n'.join(rows))
                seen.add((values[21] >> 8, values[21] & 255))
        for early, op, error in ((1,2,19),(2,3,19),(3,1,110)):
            values, facts, _ = execute(exe, runner=runner, early=early)
            self.assertEqual(facts['operation_errno'],error)
            self.assertEqual((facts['stage2_observed'],facts['stage2_failed']),(0,0))
            self.assertIsNone(facts['stage2_hcs_masked'])
            self.assertEqual(values[21], (1 << 8)|op)
            seen.add((1,op))
        for hcs in (1,8,16,32,0x39):
            _, facts, _ = execute(exe, runner=runner, guard=2, hcs=hcs)
            self.assertEqual(facts['stage2_hcs_masked'], hcs)
        # Fault every external rate/supply call and every reached budget check.
        for row in trace:
            number, kind, name = row.split()
            if kind in ('clock','read','open'):
                continue
            for error in (-16,-5):
                with self.subTest(event=row, error=error):
                    values, facts, _ = execute(exe, runner=runner, fault=int(number), error=error)
                    self.assertEqual(values[1],2)
                    self.assertEqual(facts['stage2_observed'],0x7ff)
                    self.assertEqual(facts['stage2_failed'],0)
                    self.assertFalse(facts['normal_return'])
                    self.assertNotIn('control_nonce',facts)
                    seen.add((values[21] >> 8, values[21] & 255))
        self.assertEqual(seen, expected_sites)

    def test_actual_host_producer_reader_and_consumer(self):
        self.exercise(self.exe)

    @unittest.skipUnless(shutil.which('aarch64-linux-gnu-gcc') and shutil.which('qemu-aarch64'),
                         'ARM64 toolchain and user emulation required')
    def test_actual_arm64_producer_reader_and_consumer(self):
        exe = compile_stage_fixture(Path(self.temp.name)/'arm64', 'aarch64-linux-gnu-gcc')
        self.assertIn('ARM aarch64',subprocess.check_output(['file',exe],text=True))
        self.exercise(exe, ('qemu-aarch64',))

    def test_declarations_match_c(self):
        header = (SOURCE/'waipio_hci.h').read_text()
        for enum, names in (('component',w.STAGE2_COMPONENTS[1:]),
                            ('operation',w.STAGE2_OPERATIONS[1:]), ('check',w.STAGE2_CHECKS)):
            text = header.split('enum g0q_stage2_'+enum+' {',1)[1].split('};',1)[0]
            self.assertEqual(tuple(re.findall(r'G0Q_S2_([A-Z_]+)',text)),names)

    def test_legacy_schema_and_return_rules_unchanged(self):
        for values, version in ((GOOD,1),(GOOD+[1<<16,0],2),(GOOD+[1<<16,0,0,0x7ff],3)):
            self.assertTrue(w.result(record(values),WIT,KEY,ID,report_version=version)['normal_return'])
            for other in ({1,2,3}-{version}):
                with self.assertRaises(ValueError):
                    w.result(record(values),WIT,KEY,ID,report_version=other)
        # Known pre-hardware USB failure remains a failure even under v3.
        values = [-16]+[0]*18+[19|(1<<16),0,0,0]
        facts = w.result(record(values),WIT,KEY,ID,report_version=3)
        self.assertFalse(facts['normal_return'])
        self.assertEqual(set(facts['stage2_conditions'].values()),{'UNOBSERVED'})
        for version in (1,2,3):
            facts = w.result(record(load=19),WIT,KEY,ID,report_version=version)
            self.assertNotIn('stage2_failure',facts)
            self.assertFalse(facts['normal_return'])

    def test_inconsistent_diagnostics_rejected(self):
        values, _, _ = execute(self.exe,guard=2)
        cases = []
        for index, replacement in ((21,0),(21,0xffff),(21,0x301),(22,0),(22,1<<28),
                                   (22,3|(3<<11)),(22,3|(2<<11)),(22,3|(2<<11)|(4<<22)),
                                   (22,7|(2<<11)|(1<<22)),(0,-5),(1,3),(5,1)):
            changed=values.copy();changed[index]=replacement;cases.append(changed)
        for changed in cases:
            with self.subTest(values=changed),self.assertRaises(ValueError):
                w.result(record(changed),WIT,KEY,ID,report_version=3)
        with self.assertRaises(ValueError):
            w.result(record(values),WIT,KEY,ID,report_version=4)
        raw=record(values)
        with self.assertRaises(ValueError):
            w.result(raw[:-1]+bytes([raw[-1]^1]),WIT,KEY,ID,report_version=3)

    def test_report_capacity(self):
        maxima = [-(1<<31) if i in (0,16) else (1<<32)-1 for i in range(23)]
        self.assertEqual(len((' '.join(map(str,maxima))+'\n').encode()),255)


if __name__=='__main__':
    unittest.main()
