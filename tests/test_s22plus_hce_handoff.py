"""Actual stage/reader/guest/authenticated consumer for the opt-in HCE stop."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_s22plus_stage2_diagnostics import compile_stage_fixture
from test_s22plus_pre_effect_return import compile_pre_effect, module_report
from test_s22plus_ml030_wire import KEY, ID, WIT, GOOD, record, w


def decode(data):
    return w.result(record(raw_bytes=data), WIT, KEY, ID, report_version=6)


def line(values):
    return (' '.join(map(str, values)) + '\n').encode()


class HceHandoffTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='s22-hce-handoff-')
        cls.out = Path(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def exercise(self, compiler, runner=()):
        folder = self.out/compiler
        exe = compile_stage_fixture(folder/'stage', compiler, handoff=True)
        guest = compile_pre_effect(folder/'guest', compiler=compiler, guest=True, handoff=True)
        module = compile_pre_effect(folder/'module', compiler=compiler, handoff=True)
        if runner:
            for path in (exe, guest, module):
                self.assertIn('ARM aarch64', subprocess.check_output(['file', path], text=True))

        def run(case=1, guard=0, expiry=None, hcs=1):
            args = [0, guard, -16, hcs, 0, case]
            if expiry is not None:
                args.append(expiry)
            p = subprocess.run([*runner, exe, *map(str, args)], check=True,
                               capture_output=True, timeout=5)
            facts = decode(p.stdout)
            rows = p.stderr.decode().splitlines()
            first, later = rows[:rows.index('REPORT_DONE')], rows[rows.index('REPORT_DONE')+1:]
            self.assertFalse(any(' write ' in row for row in later))
            self.assertFalse(facts['normal_return'])  # Downstream reset is a failing fixture stub.
            self.assertLessEqual(len(p.stdout), 256)
            return p.stdout, facts, first, later

        def accepted(data):
            return int(subprocess.check_output([*runner, guest], input=data, timeout=5)) == 0

        for case in (1, 18, 19):
            data, facts, trace, later = run(case)
            h = facts['hce_handoff']
            self.assertEqual(h['status'], 'STOP_COMPLETE')
            self.assertEqual(h['flags'], 8191)
            self.assertEqual(h['poll_reads'], 1)
            self.assertLess(h['elapsed_us'], 1000)
            self.assertEqual(h['pre_hce'], 1)
            self.assertEqual(h['last_hce'], 0)
            self.assertEqual(facts['stage2_observed'], 0x7ff)
            self.assertEqual(facts['stage2_failed'], 0)
            writes = [i for i, row in enumerate(trace) if ' write ' in row]
            self.assertEqual(len(writes), 1)
            before = [row.split()[-1] for row in trace[:writes[0]] if ' read ' in row]
            self.assertEqual(before, ['hci:8','hci:e4','hci:34','hci:30','hci:58',
                                     'hci:78','hci:24','hci:20','pin:0','pin:1','hci:34'])
            after = [row.split()[-1] for row in trace[writes[0]+1:] if ' read ' in row]
            self.assertEqual(after, ['hci:34','hci:30','hci:58','hci:78','hci:60',
                                    'hci:80','hci:24','hci:20','hci:18','pin:0','pin:1'])
            self.assertEqual([row.split()[-1] for row in later if ' read ' in row],
                             ['hci:8','hci:e4','hci:34'])
            self.assertFalse(accepted(data))

        # Cold entry has no stop and the original register-read order.
        _, facts, trace, _ = run(0)
        self.assertEqual(facts['hce_handoff']['status'], 'COLD_ENTRY')
        self.assertFalse(any(' write ' in row for row in trace))
        self.assertEqual(facts['stage2_observed'], 0x7ff)
        self.assertEqual(sum(' read ' in row for row in trace), 13)

        expected = {2:('HCE',1), 3:('HCS',3), 4:('TRANSFER_DOORBELL',7),
                    5:('TASK_DOORBELL',15), 6:('IRQ_ENABLE',31), 7:('IRQ_STATUS',63),
                    8:('RESET_OUTPUT',127), 9:('RESET_HIGH',255),
                    16:('HCE',1), 17:('HCS',3), 20:('HCE',1), 21:('HCE',1)}
        for case, (condition, flags) in expected.items():
            with self.subTest(case=case):
                _, facts, trace, _ = run(case)
                h = facts['hce_handoff']
                self.assertEqual((h['status'], h['refusal_phase'], h['refusal_condition']),
                                 ('REFUSED', 'PRE_ADMISSION', condition))
                self.assertEqual(h['flags'], flags)
                self.assertEqual(facts['stage2_observed'], 0)
                self.assertFalse(any(' write ' in row or ' open rails' in row for row in trace))

        for guard in range(2,12):
            with self.subTest(post_guard=guard):
                _, facts, trace, _ = run(1, guard, hcs=0xffffffff)
                h = facts['hce_handoff']
                self.assertEqual(h['status'], 'STOP_COMPLETE')
                self.assertEqual(h['refusal_phase'], 'POST_CHECKS')
                self.assertEqual(h['refusal_condition'], w.STAGE2_CHECKS[guard-1])
                self.assertEqual(facts['stage2_observed'], (1 << guard)-1)
                self.assertEqual(facts['stage2_failed'], 1 << (guard-1))
                self.assertEqual(sum(' write ' in row for row in trace), 1)
                self.assertEqual(sum(' read ' in row for row in trace), 11+guard)
                self.assertFalse(any(' open rails' in row for row in trace))
                if guard == 2:
                    self.assertEqual(h['refusal_raw'], 0xffffffff)

        for expiry in range(2,12):
            _, facts, trace, _ = run(1, expiry=expiry)
            self.assertEqual(facts['hce_handoff']['status'], 'PRE_WRITE_DEADLINE')
            self.assertEqual(facts['hce_handoff']['flags'], (1 << (expiry-2))-1)
            self.assertFalse(any(' write ' in row for row in trace))
            self.assertEqual(facts['stage2_observed'], 0)

        _, facts, trace, _ = run(10)
        self.assertEqual(facts['hce_handoff']['status'], 'ENTRY_DRIFT')
        self.assertEqual(facts['hce_handoff']['last_hce'], 0)
        self.assertFalse(any(' write ' in row for row in trace))

        for case, expected_status in ((11,'STOP_TIMEOUT'), (12,'STOP_UNEXPECTED_STATE'),
                                      (14,'STOP_TIMEOUT'), (15,'STOP_TIMEOUT')):
            _, facts, trace, _ = run(case)
            h = facts['hce_handoff']
            self.assertEqual(h['status'], expected_status)
            self.assertTrue(h['stop_issued'])
            self.assertFalse(h['stop_completed_in_time'])
            self.assertEqual(facts['stage2_observed'], 0)
            self.assertEqual(sum(' write ' in row for row in trace), 1)
            self.assertFalse(any(' open rails' in row for row in trace))
            if case == 11:
                self.assertGreater(h['poll_reads'], 1)
                self.assertGreaterEqual(h['elapsed_us'], 1000)
            elif case == 14:
                self.assertEqual(h['poll_reads'], 0)
            elif case == 15:
                self.assertTrue(h['stop_zero_observed'])
                self.assertEqual(h['poll_reads'], 1)

        certificate = module_report(module, 'refuse', runner)
        self.assertTrue(decode(certificate)['normal_return'])
        self.assertTrue(accepted(certificate))
        for index in range(23,30):
            values = list(map(int, certificate.split())); values[index] = 1
            self.assertFalse(accepted(line(values)))
            with self.assertRaises(ValueError):
                decode(line(values))

        # Exercise the real guest return gate with complete synthetic link records.
        for extra in ([1,0,0,0,0,0,0], [8191 | (1 << 13) | (2 << 20),1,0x10f,0x400,0,0,0]):
            good = GOOD + [1 << 16,0,0x60000000,0x7ff] + extra
            self.assertTrue(decode(line(good))['normal_return'])
            self.assertTrue(accepted(line(good)))
            for index, value in ((23,0),(23,4095 | (1 << 13)),(24,3),(27,1),(28,2),(29,1)):
                bad = good.copy(); bad[index] = value
                self.assertFalse(accepted(line(bad)))
                with self.assertRaises(ValueError):
                    decode(line(bad))

        # High preHCS must coexist with the largest reached power/link fields.
        worst = GOOD + [1 << 16,0,0x60000000,0x7ff] + [8191 | (100 << 13) | (999 << 20),1,0xffffffcf,0x400,0,0,0]
        for index, value in {2:0x4fffffff,6:0xffffffc8,7:0x500,9:0xffffffcf,
                             11:32,12:0xffffffff,13:0xffffffff,14:0xffffffff}.items():
            worst[index] = value
        self.assertTrue(decode(line(worst))['normal_return'])
        self.assertTrue(accepted(line(worst)))
        self.assertLessEqual(len(line(worst)),256)

    def test_actual_host_chain(self):
        self.exercise('cc')

    def test_actual_arm64_chain(self):
        self.exercise('aarch64-linux-gnu-gcc', ('qemu-aarch64',))

    def test_malformed_transition_history(self):
        base = [-16,2,0x40040000] + [0]*14 + [1,1,1 << 16,0,0x60000115,0] + [3,1,0x11f,0,0,2,0x11f]
        self.assertEqual(decode(line(base))['hce_handoff']['status'],'REFUSED')
        for index, value in ((23,2),(24,0),(24,3),(25,0x10f),(26,0x400),
                             (27,1),(28,3),(29,0x10f),(22,1),(21,0x60000118)):
            bad=base.copy();bad[index]=value
            with self.subTest(index=index,value=value), self.assertRaises(ValueError):
                decode(line(bad))
        for version in (1,2,3,4,5):
            with self.assertRaises(ValueError):
                w.result(record(base),WIT,KEY,ID,report_version=version)


if __name__ == '__main__':
    unittest.main()
