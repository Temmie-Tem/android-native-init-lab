import copy
import json
import time
from types import SimpleNamespace
import unittest

import s22plus_resident_adoption_h0_support as support
import s22plus_native_resident_observer_v1 as observer


class Probe(unittest.TestCase):
    def raw(self,**change):
        values=dict(sequence=700,stamp=100000,system=701,hardware=702,gauge=703,cpu=52000,mask=8191,
            state='FRESH',valid=480,age=10,dropped=0)
        values.update(change)
        frame=('RESIDENT_FRAME seq={sequence} ms={stamp} state=0 system_seq={system} system=FRESH system_valid=3 system_age=10 '
            'hardware_seq={hardware} hardware={state} hardware_valid={valid} hardware_age={age} gauge_seq={gauge} '
            'gauge_age={age} cpu_temp_mc={cpu} cpu_mask={mask} expected=13 producer_dropped={dropped} '
            'event=matched visible=UNPROVED\n').format(**values).encode()
        return (b'S22RPROBE1\n100.10 0.00\nS22RLOG1 first=901 last=901 records=1 evicted=900 dropped=0 partial_bytes=0 exhausted=0\n'+
                frame+b'S22RLOG1 COMPLETE\nS22RPROBE1 COMPLETE\n')

    def test_current_clock_retained_window_and_cpu_coverage(self):
        value=observer.decode_probe(self.raw(dropped=4))
        self.assertTrue(value['fresh_system_and_gauge']);self.assertTrue(value['cpu_temperature_observed'])
        self.assertFalse(value['log']['complete_history']);self.assertEqual(value['latest']['producer_dropped'],4)
        stale=observer.decode_probe(self.raw(stamp=1000))
        self.assertFalse(stale['fresh_system_and_gauge'])
        combined=observer.decode_probe(self.raw(stamp=96000,age=4000))
        self.assertFalse(combined['fresh_system_and_gauge'])
        self.assertEqual(combined['current_age_upper_ms']['gauge_age_ms'],8109)
        missing=observer.decode_probe(self.raw(cpu=0,mask=0,valid=224))
        self.assertTrue(missing['fresh_system_and_gauge']);self.assertFalse(missing['cpu_temperature_observed'])
        for raw in (self.raw()[:-1],self.raw(stamp=100120),self.raw(mask=8192),self.raw(cpu=150001),
                    self.raw().replace(b'records=1',b'records=2'),self.raw().replace(b'S22RLOG1 COMPLETE\n',b'')):
            with self.subTest(raw=raw[-60:]),self.assertRaises(ValueError):observer.decode_probe(raw)

    def test_valid_to_unavailable_gauge_keeps_the_observed_failure(self):
        first=self.raw().splitlines(keepends=True)
        missing=self.raw(sequence=701,gauge=0,valid=256).splitlines(keepends=True)[3]
        raw=b''.join(first[:2])+first[2].replace(b'last=901 records=1',b'last=902 records=2')+first[3]+missing+b''.join(first[4:])
        value=observer.decode_probe(raw)
        self.assertFalse(value['fresh_system_and_gauge']);self.assertEqual(value['latest']['gauge_sequence'],0)
        regressed=self.raw(sequence=702,gauge=2).splitlines(keepends=True)[3]
        raw=raw.replace(b'last=902 records=2',b'last=903 records=3').replace(b'S22RLOG1 COMPLETE\n',regressed+b'S22RLOG1 COMPLETE\n')
        with self.assertRaises(ValueError):observer.decode_probe(raw)


class Integration(support.Fixture,unittest.TestCase):
    @classmethod
    def setUpClass(cls):support.compile_components(cls)

    def exercise(self,case='normal'):
        with self.running(case) as ctx:
            intents=[];raw=bytearray();reopens=[]
            def reopen(row,deadline,index):
                self.reopen(ctx);reopens.append(index)
                self.advance(ctx,(observer.CHECKPOINT_SECONDS[index-1]-observer.CHECKPOINT_SECONDS[index-2])*1000)
                return ctx.fd
            try:
                result=support.candidate.observer.qualify(self.codec,ctx.fd,b'k'*32,None,set(),
                    SimpleNamespace(write_stdout=raw.extend),deadline=time.monotonic()+60,
                    before_control=intents.append,evidence=ctx.folder/'auth',before_detach=intents.append,
                    reopen=reopen,before_auth=lambda index:None,before_write=lambda:None)
            except observer.console.QualificationError as exc:
                raise AssertionError({'cause':repr(exc.__cause__),
                    'probes':[r['probe'] for r in exc.partial_receipt['sessions']],
                    'log':(ctx.folder/'hud.log').read_text()[-3000:]}) from exc
            rx=b''.join(bytes(s.session.audit.rx) for s in result.sessions)
            tx=b''.join(bytes(s.session.audit.tx) for s in result.sessions)
            self.assertEqual(bytes(raw),rx);self.assertEqual(reopens,[2,3,4])
            marks=(ctx.folder/'marks').read_text()
            self.assertEqual(marks.count('baseline-boot-prepare'),1);self.assertEqual(marks.count('download 0'),1)
            self.assertEqual(marks.count('metrics-child'),2);self.assertEqual(marks.count('hud-child'),1)
            return result,rx,tx,intents

    def test_actual_c_four_checkpoints_probe_and_raw_reopen(self):
        result,rx,tx,intents=self.exercise()
        self.assertTrue(result.receipt['proved']);self.assertTrue(result.receipt['past_sample_limit'])
        self.assertGreaterEqual(result.receipt['signed_checkpoint_elapsed_ms'][-1],1800000)
        self.assertEqual([r['mode'] for r in intents],['detach']*3+['download'])
        self.assertEqual(result.receipt,support.candidate.observer.replay_session(self.codec,rx,tx,b'k'*32))
        for r,t in ((rx[:-1],tx),(rx+rx,tx),(rx,tx[:-1]),(rx,tx+tx)):
            with self.subTest(r=len(r),t=len(t)),self.assertRaises((ValueError,EOFError)):
                support.candidate.observer.replay_session(self.codec,r,t,b'k'*32)
        changed=copy.deepcopy(result.receipt);changed['sessions'][3]['resident_info']['elapsed_ms']=100
        with self.assertRaises(ValueError):support.candidate.observer.validate_qualification(changed)
        # Public metadata includes no raw command output. This is deliberately a
        # serialization check on the complete actual proof used by the journal.
        self.assertLess(len(json.dumps(result.receipt)),32768)

    def test_fixed_health_failure_preserves_raw_and_does_not_retry(self):
        with self.running('bad-health') as ctx:
            raw=bytearray();auth=[];ends=[]
            with self.assertRaises(observer.console.QualificationError) as caught:
                support.candidate.observer.qualify(self.codec,ctx.fd,b'k'*32,None,set(),SimpleNamespace(write_stdout=raw.extend),
                    deadline=time.monotonic()+10,before_control=ends.append,evidence=ctx.folder/'auth',
                    before_detach=ends.append,reopen=lambda *_:self.fail('replay'),before_auth=auth.append,before_write=lambda:None)
            self.assertEqual(auth,[1]);self.assertEqual(ends,[])
            self.assertEqual(bytes(raw),bytes(caught.exception.failed_audit.rx));self.assertTrue(raw)

    def test_complete_control_survives_a_short_signed_observation_span(self):
        with self.running() as ctx:
            raw=bytearray();intents=[]
            def reopen(row,deadline,index):
                self.reopen(ctx);self.advance(ctx,300000 if index<4 else 800000);return ctx.fd
            with self.assertRaises(observer.console.QualificationError) as caught:
                support.candidate.observer.qualify(self.codec,ctx.fd,b'k'*32,None,set(),SimpleNamespace(write_stdout=raw.extend),
                    deadline=time.monotonic()+60,before_control=intents.append,evidence=ctx.folder/'auth',
                    before_detach=intents.append,reopen=reopen,before_auth=lambda _:None,before_write=lambda:None)
            error=caught.exception;proof=error.partial_receipt
            self.assertEqual(len(error.completed_sessions),4);self.assertIsNone(error.failed_audit)
            self.assertFalse(proof['proved']);self.assertFalse(proof['signed_span_valid'])
            self.assertTrue(proof['control_acceptance_observed']);self.assertEqual(intents[-1]['mode'],'download')
            tx=b''.join(bytes(s.session.audit.tx) for s in error.completed_sessions)
            self.assertEqual(proof,support.candidate.observer.replay_session(self.codec,bytes(raw),tx,b'k'*32,partial=True))


if __name__=='__main__':unittest.main()
