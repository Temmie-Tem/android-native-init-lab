"""Exact new history and selected packet semantics; no device actions."""
import copy
import unittest
from unittest import mock

import test_s22plus_autoboot_script_v1 as previous
from test_s22plus_autoboot_watchdog_selection import ClosedPair
import s22plus_debian_autoboot_profile_v1 as profile
import s22plus_debian_usb_retention_v1 as retention


class P455Pair(ClosedPair):
    receipt_name='P455_RETRIEVAL'
    select_pair=staticmethod(profile.p452_history)

    def setUp(self):
        super().setUp()
        self.writer=dict(virtual=False,namespace=profile.SCRIPT_NAMESPACE,
            version=profile.SCRIPT_VERSION,transition_observer=profile.SCRIPT_OBSERVER,run_id=self.run)
        build=self.save('writer.json',self.writer)
        self.result.update(writer_build=build,writer_artifact=self.save('artifact.json',dict(build=build)),
            source_view_clean=True,reader_journal_replayed=False)
        self.acquired.update(source_view_clean=True,superblock=dict(state=1,recover=0,orphan=0))

    def test_replay_dirty_view_or_other_physical_producer_rejects(self):
        for key,value in (('source_view_clean',False),('reader_journal_replayed',True)):
            with self.assertRaises(ValueError):self.select(result=dict(self.result,**{key:value}))
        acquired=copy.deepcopy(self.acquired);acquired['superblock']['recover']=1
        with self.assertRaises(ValueError):self.select(acquired=acquired)
        for key,value in (('virtual',True),('version','unreviewed'),('run_id','0'*32),
                          ('transition_observer',profile.MINIMAL_OBSERVER)):
            writer=dict(self.writer,**{key:value});build=self.save('other.json',writer)
            result=dict(self.result,writer_build=build,
                writer_artifact=self.save('other-artifact.json',dict(build=build)))
            with self.assertRaises(ValueError):self.select(result=result)


class MinimalPackets(unittest.TestCase):
    frame=previous.ScriptFacts.frame

    def project(self,frames,*,minimal=True):
        return previous.wire.project(b''.join(frames),script_channel=True,minimal=minimal)

    def complete(self):
        rows=[self.frame()]
        entries=[('D',0,0)]+[(action,i,0) for i in range(1,6) for action in ('B','E')]+[('X',0,0)]
        for sequence,(action,identifier,status) in enumerate(entries,1):
            rows.append(self.frame(93,sequence+1,status,sequence,identifier,ord(action),0,ms=20020+sequence))
        rows.append(self.frame(95,14,50,12,0,1,0,ms=20100))
        return rows

    def test_minimal_completeness_does_not_claim_full_rcs_or_service_proof(self):
        rows=self.complete();new=self.project(rows)
        self.assertFalse(new['rejected']);self.assertFalse(new['conflicts'])
        self.assertTrue(new['script_channel']['complete_channel_observed'])
        self.assertFalse(new['script_channel']['complete_channel_proved'])
        self.assertFalse(new['rcs_completed'])
        names=[p['script_channel']['script'] for p in new['script_channel']['packets']
            if p['script_channel']['action']=='B']
        self.assertEqual(names,list(profile.minimal_spec.SCRIPTS))
        self.assertFalse(self.project(rows,minimal=False)['script_channel']['complete_channel_observed'])

    def test_old_ids_excess_packets_and_missing_pair_do_not_complete(self):
        for frame in (self.frame(93,2,0,1,6,ord('B'),0),self.frame(95,14,50,13,0,1,0)):
            self.assertEqual(self.project([frame])['rejected'],{'semantics':1})
        rows=self.complete()
        self.assertFalse(self.project(rows[:4]+rows[5:])['script_channel']['complete_channel_observed'])
        self.assertFalse(self.project(previous.ScriptFacts.complete(self))['script_channel']['complete_channel_observed'])

    def test_exact_selection_preserves_prior_history_and_cpu_requirements(self):
        selected=dict(transition_observer=profile.MINIMAL_OBSERVER,cpu_policy=profile.SINGLECPU_POLICY,
            idle_policy='cpuidle-off')
        retention.require_automatic_transition(selected)
        self.assertTrue(profile.minimal_selected(selected))
        self.assertTrue(profile.script_channel_selected(selected))
        producers=dict(selected,**{name:dict(sha256=str(i)*64)
            for i,name in enumerate(('writer','entry','witness','hook'),1)})
        self.assertEqual(set(previous.wire.trace.sources(producers)),set(range(1,9)))
        with self.assertRaises(ValueError):profile.minimal_selected(dict(selected,idle_policy='retained-default'))
        with self.assertRaises(ValueError):profile.histories(True,True,True,False,True,True,False,True)
        with mock.patch.object(profile,'phase_history',return_value=['phase']), \
             mock.patch.object(profile,'p445_history',return_value='early'), \
             mock.patch.object(profile,'p448_history',return_value=['old-pair']), \
             mock.patch.object(profile,'p452_history',return_value=['new-pair']):
            self.assertEqual(profile.singlecpu_history(True,True),['phase','early','old-pair'])
            self.assertEqual(profile.singlecpu_history(True,True,True),['phase','early','old-pair','new-pair'])


if __name__=='__main__':unittest.main()
