"""P351 actual wire bytes through retained parsing and durable reopening."""
from pathlib import Path
import types
import unittest
from unittest import mock

_source = Path(__file__).with_name('test_s22plus_fyg8_p350_live.py').read_text()
_source = _source.replace('P350', 'P351').replace('p350', 'p351')
_source = _source.replace('observer.display_output(42)',
                        'observer.display_output(42, dict(mdp=-1,dsi=1,elapsed_ms=400,scans=4))')
_fixture = types.ModuleType('_p351_wire_fixture')
_fixture.__file__ = __file__
exec(compile(_source, __file__ + '#wire', 'exec'), _fixture.__dict__)


class P351LiveTests(_fixture.P351LiveTests):
    def test_failure_log_and_status_rejected_after_real_wire_parse(self):
        for kind in ('kernel-log', 'exit-failure'):
            with _fixture.tempfile.TemporaryDirectory() as directory:
                fixture = _fixture.P351ReceiptFixture(Path(directory) / 'run')
                observer = fixture.observer
                if kind == 'kernel-log':
                    old = observer.display_output
                    with mock.patch.object(observer, 'display_output', side_effect=lambda *args:
                                           b'DISPLAY_KMSG_BEGIN\n' + old(*args) + b'DISPLAY_KMSG_END\n'):
                        rx, tx = fixture._session(2)
                else:
                    old = fixture._frame
                    def frame(typ, sequence, body):
                        if typ == fixture.runtime.FRAME_EXIT and sequence == 4:
                            fields = list(fixture.codec.EXIT.unpack(body))
                            fields[1] = 1
                            body = fixture.codec.EXIT.pack(*fields)
                        return old(typ, sequence, body)
                    with mock.patch.object(fixture, '_frame', side_effect=frame):
                        rx, tx = fixture._session(2)
                shell = observer.parse_captured_session(fixture.codec, rx, tx, _fixture.KEY)
                with self.assertRaises(observer.QualificationError):
                    observer.validate_session_result(shell, observer.DISPLAY_STEP)


if __name__ == '__main__':
    unittest.main()
