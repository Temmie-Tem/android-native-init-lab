"""Persistent configuration proof semantics; real ARM64 producers run separately."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_debian_cron_config_v1 as config
import s22plus_debian_cron_v1 as old
import s22plus_debian_evidence_v1 as evidence
import s22plus_debian_autoboot_profile_v1 as profile
from test_s22plus_debian_evidence_v1 import events


class ConfigurationProof(unittest.TestCase):
    def setUp(self):
        self.key=b'K'*32;self.run='01'*16;self.boot='02'*32;self.first='03'*32
        self.nonce=b'N'*32;self.first_nonce=b'F'*32;self.hook='04'*32
        self.programs={name:dict(size=100+i,sha256=hashlib.sha256(name.encode()).hexdigest())
            for i,name in enumerate(('cron','sshd'))}
        self.mock=patch.object(config,'programs',return_value=self.programs);self.mock.start();self.addCleanup(self.mock.stop)
        self.created=dict(config_inode=321,config_size=len(config.schedule(self.run)),config_created_ms=1102,
            config_mtime_sec=100,config_mtime_nsec=23,config_ctime_sec=101,config_ctime_nsec=24)

    def sign(self,data,domain=None):
        value=bytearray(data);value[480:]=hmac.digest(self.key,(domain or config.DOMAIN)+b'\x01'+value[:480],'sha256')
        return bytes(value)

    def record(self,**changes):
        data=bytearray(512);data[:8]=b'S22CC01\0';struct.pack_into('<II',data,8,1,512)
        data[16:32]=bytes.fromhex(self.run);data[32:64]=bytes.fromhex(self.boot);data[64:96]=self.nonce
        values=dict(root_device=os.makedev(8,41),phase=2,baseline=26,installed_count=30,
            armed_ms=1200,job_ms=60000,hash_completed_ms=60001,daemon_pid=20,job_pid=42,parent_pid=41,
            daemon_ticks=1000,cron_size=100,sshd_size=101,ancestor_count=2,**self.created)
        values.update(changes)
        for name,offset,kind in config.FIELDS:struct.pack_into('<'+kind,data,offset,values[name])
        for name,offset in (('cron',192),('sshd',224)):data[offset:offset+32]=bytes.fromhex(self.programs[name]['sha256'])
        data[256:288]=bytes.fromhex(self.hook);data[352:384]=hashlib.sha256(config.schedule(self.run)).digest()
        data[416:448]=bytes.fromhex(self.first);data[448:480]=self.first_nonce
        return self.sign(data)

    def decode(self,data,**changes):
        args=dict(key=self.key,run=self.run,boot=self.boot,nonce=self.nonce,root_device=dict(major=8,minor=41),
            hook_sha256=self.hook,baseline=26,first_boot=self.first,first_nonce=self.first_nonce,created=self.created)
        args.update(changes);return config.decode(data,**args)

    def test_consumption_joins_two_boots_and_does_not_alone_prove_retirement(self):
        result=self.decode(self.record());self.assertTrue(result['configuration_consumed'])
        self.assertFalse(result['configuration_retired']);self.assertFalse(result['package_installation_proved'])
        for changes in ({'first_boot':self.boot},{'first_nonce':self.nonce},{'nonce':self.first_nonce},
                {'created':dict(self.created,config_inode=322)}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.decode(self.record(),**changes)

    def test_valid_authentication_cannot_promote_wrong_phase_or_changed_identity(self):
        for changes in ({'phase':1},{'installed_count':28},{'baseline':22},{'daemon_ticks':0},{'job_pid':20},
                {'ancestor_count':0},{'ancestor_count':7},{'config_inode':322},{'config_mtime_nsec':25},
                {'config_ctime_sec':102},{'config_created_ms':300000},{'hash_completed_ms':300000},{'armed_ms':60002}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.decode(self.record(**changes))

    def test_domain_framing_and_reserved_bytes_are_exact(self):
        data=self.record()
        for bad in (data[:-1],data+b'X',self.sign(data,old.DOMAIN)):
            with self.assertRaises(ValueError):self.decode(bad)
        for index in (116,144,159,332,351,352,383,416,479):
            changed=bytearray(data);changed[index]^=1
            with self.subTest(index=index),self.assertRaises(ValueError):self.decode(self.sign(changed))

    def test_selection_keeps_consumed_predecessors_distinct(self):
        for observer,wanted in ((profile.REBOOT_OBSERVER,False),(profile.CRON_OBSERVER,True),
                (profile.CRON_CONFIG_OBSERVER,'config')):
            self.assertEqual(profile.cron_selected(dict(transition_observer=observer)),wanted)
        for bad in (1,None,'yes',{},[]):
            with self.assertRaises(ValueError):profile.cron_variant(bad)
        self.assertIs(profile.cron_variant('config'),config)
        self.assertNotIn(b'%',config.schedule(self.run))
        self.assertNotIn('.',config.config_path(self.run).rsplit('/',1)[1])


class DurableConfiguration(unittest.TestCase):
    key=b'K'*32

    def rows(self,phase):
        rows=[tuple((*row[:6],257 if row[0]==evidence.PROGRESS else row[6])) for row in events()[:-1]]
        if phase==1:
            rows[11:11]=[(11,1101,1,1,321,100,23),(11,1102,1,2,101,24,len(config.schedule('01'*16)))]
        else:rows.insert(-1,(12,121200,2,1,321,60,2000))
        return rows

    def consume(self,rows,phase,*,selected=True):
        first=b'T'*32;chain=evidence.Chain(first,autoboot=True,single_cpu=True,
            reboot=dict(phase=phase,initial_mount_count=26),cron_config=selected)
        for seq,(kind,ms,p,event,a,b,c) in enumerate(rows):
            row=bytearray(128);row[:8]=b'S22DER1\0';struct.pack_into('<IIQIIQQQII',row,8,seq,kind,ms,p,event,a,b,c,0,0)
            row[64:96]=chain.tag;row[96:]=evidence.tag(self.key,row[:96],autoboot=True,reboot=True,cron_config=selected)
            chain.append(bytes(row),self.key)
        return chain

    def test_phase_specific_lifecycle_is_required_for_complete(self):
        for phase in (1,2):
            chain=self.consume(self.rows(phase),phase);self.assertTrue(chain.complete)
            self.assertEqual(len(chain.config_created),2 if phase==1 else 0)
            self.assertEqual(chain.config_retired is not None,phase==2)
            with self.assertRaises(ValueError):self.consume(self.rows(phase),3-phase)
            with self.assertRaises(ValueError):self.consume([r for r in self.rows(phase) if r[0] not in (11,12)],phase)

    def test_reordered_duplicate_or_partial_creation_never_completes(self):
        rows=self.rows(1)
        cases=[rows[:12]+rows[13:],rows[:12]+[rows[11]]+rows[12:],rows[:11]+list(reversed(rows[11:13]))+rows[13:]]
        for changed in cases:
            with self.assertRaises(ValueError):self.consume(changed,1)
        with self.assertRaises(ValueError):self.consume(rows,1,selected=False)
        late=self.rows(2);late[-2]=(12,300000,2,1,321,60,2000)
        with self.assertRaises(ValueError):self.consume(late,2)


class TerminalJoins(unittest.TestCase):
    def terminal(self,change=None):
        import s22plus_debian_autoboot_session_v1 as session
        import s22plus_debian_reboot_access_v1 as access
        created=dict(config_inode=321,config_size=177,config_created_ms=1000,
            config_mtime_sec=100,config_mtime_nsec=1,config_ctime_sec=100,config_ctime_nsec=2)
        first=dict(created=created,configuration_sha256='a'*64,configuration_consumed=False,configuration_retired=False)
        second=dict(created=created,configuration_sha256='a'*64,configuration_consumed=True,configuration_retired=True)
        if change:second.update(change)
        class Selected:
            def __init__(self,adapter,request,phase):self.phase=phase
            def evidence(self):return dict(proof=dict(cron_configuration=first if self.phase==1 else second))
            def rederive_health(self):return dict(health=dict(boot_count=100+self.phase))
            def basis(self):return None
        with patch.object(access,'Access',Selected):return session.reboot_terminal(None,{},recovered=False)

    def test_saved_terminal_distinguishes_consumption_retirement_and_installation(self):
        result=json.loads(json.dumps(self.terminal()))
        for key in ('ordinary_reboot_proved','cron_workload_proved','cron_configuration_preserved',
                'cron_configuration_consumed','cron_configuration_retired'):self.assertIs(result[key],True)
        self.assertIs(result['configuration_retained_after_experiment'],False)
        self.assertIs(result['package_installation_proved'],False)
        self.assertIs(result['replay_authorized'],False)

    def test_unjoined_or_incomplete_configuration_never_gets_terminal_success_flags(self):
        for changes in ({'created':{'config_inode':999}},{'configuration_sha256':'b'*64},
                {'configuration_consumed':False},{'configuration_retired':False}):
            with self.subTest(changes=changes):
                result=self.terminal(changes);self.assertIn('evidence_error',result)
                self.assertIsNot(result.get('cron_configuration_retired'),True)


if __name__=='__main__':unittest.main()
