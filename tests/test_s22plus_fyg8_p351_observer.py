"""Reuse fixed-session fixtures; add P351 readiness/raw failure negatives."""
from pathlib import Path
import types
import unittest

_source = Path(__file__).with_name('test_s22plus_fyg8_p350_observer.py').read_text()
_source = _source.replace('P350', 'P351').replace('p350', 'p351')
_source = _source.replace('o.display_output(42)', "o.display_output(42, dict(mdp=-1,dsi=1,elapsed_ms=400,scans=4))")
_fixture = types.ModuleType('_p351_fixed_sessions')
_fixture.__file__ = __file__
exec(compile(_source, __file__ + '#fixed-sessions', 'exec'), _fixture.__dict__)
o = _fixture.o


class P351ObserverTests(_fixture.P351ObserverTests):
    def test_readiness_corruption_stops_before_usb_after(self):
        changes = [(b'complete=1', b'complete=0'), (b'bus=1', b'bus=0'),
                   (b'pmic=1', b'pmic=0'), (b'rails=15', b'rails=7'),
                   (b'drm=1', b'drm=0'), (b'elapsed_ms=400', b'elapsed_ms=15001'),
                   (b'scans=4', b'scans=1'), (b'mdp=-1', b'mdp=2'),
                   (b'index=11', b'index=10')]
        for before, after in changes:
            def corrupt(i, r):
                if i == 2:
                    r.session.commands[1].output = r.session.commands[1].output.replace(before, after)
            result, calls = self.run_sequence(corrupt)
            self.assertIsInstance(result, o.QualificationError, (before, result))
            self.assertEqual(len(calls), 2)

    def test_kernel_log_cannot_supply_success_witness(self):
        def corrupt(i, r):
            if i == 2:
                command = r.session.commands[1]
                command.output = b'DISPLAY_KMSG_BEGIN\n' + command.output + b'DISPLAY_KMSG_END\n'
        result, calls = self.run_sequence(corrupt)
        self.assertIsInstance(result, o.QualificationError)
        self.assertEqual(len(calls), 2)

    def test_failed_exit_rejects_even_complete_looking_output(self):
        def corrupt(i, r):
            if i == 2:
                r.session.commands[1].exit_code = 1
        result, calls = self.run_sequence(corrupt)
        self.assertIsInstance(result, o.QualificationError)
        self.assertEqual(len(calls), 2)

    def test_receipt_readiness_is_typed_and_bound_to_output(self):
        result, _ = self.run_sequence()
        if isinstance(result, Exception):
            raise result
        for value in (True, -1, 15001, '400'):
            changed = _fixture.copy.deepcopy(result.receipt)
            changed['sessions'][1]['semantic']['readiness']['elapsed_ms'] = value
            with self.assertRaises(o.QualificationError):
                o.validate_qualification(changed)


if __name__ == '__main__':
    unittest.main()
