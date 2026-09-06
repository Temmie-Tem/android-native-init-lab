"""P350 fixed display sequence, same-boot proof and failure stops; host only."""
import copy
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'workspace/public/src/scripts/revalidation'))
import s22plus_fyg8_p350_research_shell_observer as o
import s22plus_fyg8_research_shell_exchange as exchange


def command(seq, text, output, flags=0, code=0, signal=0, duration=1):
    return SimpleNamespace(sequence=seq, command=text, output=output, flags=flags,
        exit_code=code, term_signal=signal, duration_ms=duration)


def result(index, text):
    outputs = [o.PRE_MARKER, o.display_output(42), o.POST_MARKER]
    middle=command(4,text,outputs[index-1],duration=10000 if index==2 else 1)
    outcome='ok'
    audit=SimpleNamespace(nonce=bytes([index])*32,boot_id=b'b'*32,
        rx=bytearray(b'rx'+bytes([index])),tx=bytearray(b'tx'+bytes([index])),
        banner_seen=True,challenge_seen=True,ready_seen=True,authenticated=True,done_seen=True)
    commands=(command(3,o.runtime.DEFAULT_COMMANDS[0],b'uid=0 gid=0\n'),middle,
        command(5,o.runtime.DEFAULT_COMMANDS[2],b'P328-NONCE '+o.RUN_ID_HEX.encode()+b'\n'))
    return exchange.ShellExchange(SimpleNamespace(audit=audit,commands=commands),outcome,False,None)


class P350ObserverTests(unittest.TestCase):
    def run_sequence(self, corrupt=None):
        calls=[];clock=[0.0]
        def fake(*args,**kwargs):
            calls.append((args[1],args[3]));r=result(len(calls),args[3])
            if corrupt:corrupt(len(calls),r)
            args[5].add(hashlib.sha256(r.session.audit.nonce).hexdigest())
            return r
        writer=SimpleNamespace(current_sizes=lambda:(0,0))
        with mock.patch.object(o._base.shell_exchange,'exchange',side_effect=fake), mock.patch.object(o._display_exchange,'exchange',side_effect=fake), mock.patch.object(o.time,'monotonic',side_effect=lambda:clock[0]):
            try:r=o.qualify(object(),23,b'k'*32,None,set(),writer,deadline=150)
            except Exception as e:return e,calls
        return r,calls

    def test_fixed_once_and_same_boot_usb_return(self):
        r,calls=self.run_sequence()
        if isinstance(r,Exception):raise r
        self.assertEqual([x[0] for x in calls],[23]*3)
        self.assertEqual([x[1] for x in calls].count(o.runtime.DISPLAY_COMMAND),1)
        self.assertEqual(r.receipt['session_count'],3)
        self.assertTrue(r.receipt['display_consumed'])
        self.assertEqual(r.receipt['visible_panel_output'],'UNPROVED')
        self.assertEqual(o.validate_qualification(r.receipt),r.receipt)

    def test_missing_flip_stops_before_next_command(self):
        def corrupt(i,r):
            if i==2:r.session.commands[1].output=r.session.commands[1].output.replace(b'counter=4',b'counter=3')
        r,calls=self.run_sequence(corrupt)
        self.assertIsInstance(r,o.QualificationError)
        self.assertEqual(len(calls),2)
        self.assertTrue(r.partial_receipt['display_replay_forbidden'])
        self.assertTrue(r.partial_receipt['recovery_required'])

    def test_changed_boot_stops(self):
        def corrupt(i,r):
            if i==2:r.session.audit.boot_id=b'c'*32
        r,calls=self.run_sequence(corrupt)
        self.assertIsInstance(r,o.QualificationError)
        self.assertEqual(len(calls),2)

    def test_receipt_mutations_rejected(self):
        r,_=self.run_sequence()
        if isinstance(r,Exception):raise r
        mutations=[lambda x:x.update(display_consumed=False),
            lambda x:x['sessions'][1]['semantic'].update(completed_frames=9),
            lambda x:x['sessions'][1]['commands'][1].update(duration_ms=9999),
            lambda x:x['sessions'][2].update(nonce_sha256=x['sessions'][1]['nonce_sha256']),
            lambda x:x['sessions'][1]['commands'][1].update(flags=True)]
        for mutate in mutations:
            bad=copy.deepcopy(r.receipt);mutate(bad)
            with self.assertRaises(o.QualificationError):o.validate_qualification(bad)


if __name__=='__main__':unittest.main()
