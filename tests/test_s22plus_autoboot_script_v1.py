"""Selected history and authenticated channel facts; no device actions."""
import copy
import struct
import unittest
from unittest import mock

import test_s22plus_autoboot_watchdog_v1 as wire
from test_s22plus_autoboot_watchdog_selection import ClosedPair
import s22plus_debian_autoboot_profile_v1 as profile
import s22plus_debian_usb_retention_v1 as retention


class P451Pair(ClosedPair):
    receipt_name='P451_RETRIEVAL'
    select_pair=staticmethod(profile.p448_history)

    def setUp(self):
        super().setUp()
        self.writer=dict(virtual=False,namespace=profile.SINGLECPU_P447_NAMESPACE,
            transition_observer=profile.SINGLECPU_P447_OBSERVER,run_id=self.run)
        build=self.save('writer.json',self.writer)
        self.result.update(writer_build=build,writer_artifact=self.save('artifact.json',dict(build=build)),
            source_view_clean=True)

    def test_source_and_exact_physical_producer_reject(self):
        value=copy.deepcopy(self.result);value['source_view_clean']=False
        with self.assertRaises(ValueError):self.select(result=value)
        for key,value in (('virtual',True),('namespace','p446'),('run_id','0'*32),
                          ('transition_observer',profile.SINGLECPU_OBSERVER)):
            writer=dict(self.writer,**{key:value});build=self.save('wrong-writer.json',writer)
            result=dict(self.result,writer_build=build,
                writer_artifact=self.save('wrong-artifact.json',dict(build=build)))
            with self.assertRaises(ValueError):self.select(result=result)


class ScriptFacts(unittest.TestCase):
    def frame(self,stage=91,seq=1,value=20000,a=140000,b=0,c=0,d=0,ms=20000,**kw):
        return wire.record(stage=stage,seq=seq,value=value,task=a,start=b,properties=c,sample=d,ms=ms,**kw)

    def project(self,frames,selected=True):
        return wire.project(b''.join(frames),script_channel=selected)

    def complete(self):
        result=[self.frame()];packet=1
        entries=[('D',0,0)]+[(action,i,23 if action=='E' and i==8 else 0)
            for i in range(1,17) for action in ('B','E')]+[('X',0,0)]
        for action,identifier,status in entries:
            result.append(self.frame(93,packet+1,status,packet,identifier,ord(action),0,ms=20020+packet))
            packet+=1
        result.append(self.frame(95,36,50,34,0,1,0,ms=20100))
        return result

    def test_late_window_complete_channel_is_not_functional_proof(self):
        result=self.project(self.complete());facts=result['script_channel']
        self.assertFalse(result['rejected']);self.assertFalse(result['conflicts'])
        self.assertTrue(facts['complete_channel_observed'])
        self.assertFalse(facts['complete_channel_proved'])  # no fork/child join in this fixture
        self.assertFalse(facts['watchdog_pet_proved']);self.assertFalse(result['rcs_completed'])
        self.assertEqual(facts['packets'][16]['script_channel']['status'],23)

    def test_loss_gap_missing_setup_summary_and_duplicate_do_not_complete(self):
        full=self.complete()
        for frames in (full[1:],full[:-1],full[:9]+full[10:],full+full[-1:]):
            with self.subTest(length=len(frames)):
                facts=self.project(frames)['script_channel']
                self.assertFalse(facts['complete_channel_proved'])
                if len(frames)!=len(full)+1:self.assertFalse(facts['complete_channel_observed'])
        lost=full[:-1]+[self.frame(95,36,50,34,64,1,0,ms=20100)]
        self.assertFalse(self.project(lost)['script_channel']['complete_channel_observed'])

    def test_window_shape_and_wrong_selection_reject(self):
        self.assertEqual(self.project([self.frame()],selected=False)['rejected'],{'unselected_script_channel':1})
        for frame in (self.frame(a=140001),self.frame(value=20001),
                      self.frame(94,value=20,a=1,b=0,c=0,d=0),
                      self.frame(95,value=1,a=35,b=0,c=0,d=0)):
            self.assertEqual(self.project([frame])['rejected'],{'semantics':1})
        expired=[self.frame(),self.frame(93,2,0,1,0,ord('D'),0,ms=140000)]
        self.assertIn('script_window',self.project(expired)['script_channel']['conflicts'])
        self.assertEqual(self.project([wire.record()])['rejected'],{'unselected_proc_watchdog':1})
        wrong=self.project([wire.record()])
        self.assertIn('unselected_proc_watchdog',wrong['conflicts'])
        self.assertFalse(wrong['progress_claim_valid'])
        phase=self.project([self.frame(stage=85)])
        self.assertIn('unselected_phase',phase['conflicts'])

    def test_exact_selection_keeps_single_cpu_and_retention_requirements(self):
        selected=dict(transition_observer=profile.SCRIPT_OBSERVER,cpu_policy=profile.SINGLECPU_POLICY,
            idle_policy='cpuidle-off')
        retention.require_automatic_transition(selected)
        self.assertTrue(profile.script_channel_selected(selected))
        self.assertFalse(profile.phase_selected(selected))
        with self.assertRaises(ValueError):profile.script_channel_selected(dict(selected,idle_policy='retained-default'))
        with self.assertRaises(ValueError):profile.histories(True,True,True,False,True,False,True)
        with mock.patch.object(profile,'phase_history',return_value=['old-pair']), \
             mock.patch.object(profile,'p445_history',return_value='old-early'), \
             mock.patch.object(profile,'p448_history',return_value=['new-early','new-runtime']):
            self.assertEqual(profile.singlecpu_history(True),['old-pair','old-early'])
            self.assertEqual(profile.singlecpu_history(True,True),['old-pair','old-early','new-early','new-runtime'])

    def test_optional_child_channel_must_join_fork_parent_and_causal_time(self):
        fork=self.frame(64,seq=1,kind=2,convention=1,value=22,a=0,ms=20000)
        channel=self.frame(92,seq=1,actor=7,pid=999,value=0,a=0,ms=20001)
        raw=bytearray.fromhex(wire.trace.LINE.fullmatch(channel.rstrip()).group(4).decode())
        struct.pack_into('<I',raw,52,888)
        channel=wire.authenticated(raw)
        packet=self.frame(93,seq=2,value=0,a=1,b=0,c=ord('D'),ms=20002)
        result=self.project([fork,channel,packet])
        self.assertIn('rcs_wait_join',result['conflicts'])
        self.assertFalse(result['script_channel']['dispatcher_exec_proved'])
        struct.pack_into('<II',raw,48,22,21)
        joined=wire.authenticated(raw)
        self.assertTrue(self.project([fork,joined,packet])['script_channel']['dispatcher_exec_proved'])
        struct.pack_into('<I',raw,52,888)
        result=self.project([fork,wire.authenticated(raw),packet])
        self.assertIn('rcs_parent_join',result['conflicts'])
        self.assertFalse(result['script_channel']['dispatcher_exec_proved'])


if __name__=='__main__':unittest.main()
