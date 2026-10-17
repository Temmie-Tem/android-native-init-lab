"""Independent authenticated prefixes, physical-source binding and boot joins."""
import hashlib
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

from test_s22plus_debian_file_first_v1 import Fixture
from test_s22plus_debian_evidence_v1 import events
import s22plus_debian_autoboot_profile_v1 as profile
import s22plus_debian_autoboot_retrieval_v1 as collector
import s22plus_debian_evidence_v1 as durable
import s22plus_debian_file_protocol_v1 as early
import s22plus_native_evidence_profile_v1 as evidence
from s22plus_native_records_v3 import pin,publish,read,verify
from s22plus_native_session_v3 import Step


def early_file():
    f=Fixture();old,start=f.make();log=old[256:start].replace(b'parent=1',b'parent=supervised')
    header=bytearray(old[:224]);header[:8]=b'S22FL03\0';struct.pack_into('<I',header,8,3)
    struct.pack_into('<I',header,44,len(log));header[144:176]=hashlib.sha256(log).digest()
    boot=hashlib.sha256(f.boot).digest()
    tag=early.common.tag(f.key,f.candidate,boot,0,0,header,domain=profile.DOMAIN)
    raw=bytes(header)+tag+log;boundary=len(raw)
    for pos in range(start,len(old),128):
        record=bytearray(old[pos:pos+96]);record[:8]=b'S22FLR3\0';record[64:96]=tag
        seq,kind=struct.unpack_from('<II',record,8)
        tag=early.common.tag(f.key,f.candidate,boot,kind,seq,record,domain=profile.DOMAIN)
        raw+=bytes(record)+tag
    return raw,boundary


def selected():
    f=Fixture()
    return dict(run_id=f.candidate.hex(),measured=f.expected,modules=[dict(runtime_name=n) for n in f.names],
        installed_init=dict(sha256=(b'i'*32).hex()),hook=dict(sha256=(b'h'*32).hex()))


def runtime_file(first,*,boot=None,nonce=None,hook=b'h'*32,rows=None):
    f=Fixture();header=bytearray(256);header[:8]=b'S22DE01\0';struct.pack_into('<II',header,8,1,256)
    header[16:32]=f.candidate;header[32:64]=boot or hashlib.sha256(f.boot).digest()
    header[64:96]=nonce or hashlib.sha256(first[:256]).digest()
    struct.pack_into('<QQ4I',header,96,0,300000,5,128,120,15616)
    header[128:160]=b'i'*32;header[160:192]=hook;struct.pack_into('<Q',header,192,os.makedev(8,41))
    header[224:]=durable.tag(f.key,header[:224],autoboot=True);raw=bytes(header);tag=raw[224:]
    for seq,values in enumerate(events()[:-1] if rows is None else rows):
        kind,elapsed,phase,event,a,b,c=values;record=bytearray(128);record[:8]=b'S22DER1\0'
        struct.pack_into('<IIQIIQQQII',record,8,seq,kind,elapsed,phase,event,a,b,c,0,0)
        record[64:96]=tag;record[96:]=durable.tag(f.key,record[:96],autoboot=True)
        tag=bytes(record[96:]);raw+=record
    return raw


class RetrievalTests(unittest.TestCase):
    def project(self,first,second,**kwargs):
        return collector.project(first,second,key=kwargs.pop('key',Fixture.key),selected=kwargs.pop('selected',selected()))

    def test_complete_files_join_without_ssh_or_cleanup_claims(self):
        first,_=early_file();value=self.project(first,runtime_file(first))
        self.assertEqual(value['join']['status'],'MATCH')
        self.assertEqual(value['highest_authenticated_stage'],'SERVICES_120S_COMPLETE')
        self.assertEqual(value['service_observation_ms'],120000)
        for name in ('ssh_access_proved','clean_shutdown_proved','current_filesystem_consistency_proved',
                     'absence_proves_nonexecution','replay_authorized'):self.assertFalse(value[name])

    def test_missing_or_corrupt_peer_preserves_independent_progress(self):
        first,_=early_file();second=runtime_file(first)
        for missing in (None,b'',b'bad'):
            value=self.project(missing,second)
            self.assertEqual(value['highest_authenticated_stage'],'SERVICES_120S_COMPLETE')
            self.assertEqual(value['join']['status'],'UNAVAILABLE')
            self.assertFalse(value['runtime']['header']['external_binding_proved'])
            value=self.project(first,missing)
            self.assertEqual(value['highest_authenticated_stage'],'EARLY_PRE_UNMOUNT')

    def test_partial_records_report_only_completed_local_stages(self):
        first,start=early_file();second=runtime_file(first)
        value=self.project(first[:start+256],None)
        self.assertFalse(value['early']['proof']['pre_unmount_complete'])
        self.assertEqual(value['early']['proof']['client_attempt_records'],1)
        value=self.project(None,second[:384+17])
        self.assertEqual(value['highest_authenticated_stage'],'INSTALLED_DEBIAN_PID1')
        self.assertFalse(value['runtime']['proof']['rcs_completed'])
        value=self.project(None,second[:256])
        self.assertFalse(value['boot_progress_claim_valid'])
        self.assertTrue(value['runtime']['header']['authenticated'])

    def test_physical_hook_run_init_key_and_header_authentication_are_required(self):
        first,_=early_file();second=runtime_file(first)
        for changes in ({'hook':dict(sha256='00'*32)},{'installed_init':dict(sha256='00'*32)},
                        {'run_id':'00'*16}):
            value=self.project(None,second,selected=dict(selected(),**changes))
            self.assertEqual(value['runtime']['status'],'NO_AUTHENTICATED_PROGRESS')
        self.assertEqual(self.project(None,second,key=b'x'*32)['runtime']['status'],'NO_AUTHENTICATED_PROGRESS')
        bad=bytearray(second);bad[32]^=1
        self.assertEqual(self.project(None,bytes(bad))['runtime']['status'],'NO_AUTHENTICATED_PROGRESS')
        self.assertEqual(self.project(None,runtime_file(first,hook=b'v'*32))['runtime']['status'],'NO_AUTHENTICATED_PROGRESS')

    def test_authenticated_cross_boot_or_nonce_conflict_is_not_one_boot(self):
        first,_=early_file()
        for kwargs in (dict(boot=b'B'*32),dict(nonce=b'N'*32)):
            value=self.project(first,runtime_file(first,**kwargs))
            self.assertEqual(value['status'],'AUTHENTICATED_RECORDS_CONFLICT')
            self.assertFalse(value['boot_progress_claim_valid']);self.assertIsNone(value['highest_authenticated_stage'])
            self.assertEqual(value['early']['status'],value['runtime']['status'])

    def test_header_only_early_peer_still_blocks_conflicting_runtime(self):
        first,_=early_file()
        for partial in (first[:256],first[:400]):
            for kwargs in (dict(boot=b'B'*32),dict(nonce=b'N'*32)):
                value=self.project(partial,runtime_file(first,**kwargs))
                self.assertEqual(value['early']['status'],'AUTHENTICATED_HEADER_ONLY')
                self.assertEqual(value['join']['status'],'CONFLICT')
                self.assertFalse(value['boot_progress_claim_valid'])
        value=self.project(first[:256],runtime_file(first))
        self.assertEqual(value['join']['status'],'MATCH')
        self.assertEqual(value['highest_authenticated_stage'],'SERVICES_120S_COMPLETE')

    def test_stop_and_torn_tail_do_not_erase_the_prior_prefix(self):
        first,_=early_file();rows=events()[:2]+[(durable.STOP,201,0,0,5,8,0)]
        value=self.project(None,runtime_file(first,rows=rows)+b'torn')
        self.assertTrue(value['runtime']['proof']['required_check_stopped'])
        self.assertEqual(value['highest_authenticated_stage'],'INSTALLED_INIT_HOOK_COMPLETE')
        self.assertFalse(value['runtime']['proof']['local_runtime_proved'])

    def test_empty_raw_capture_is_saved_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'empty.bin';receipt=collector.save_raw(path,b'')
            self.assertEqual(receipt['size'],0);self.assertEqual(path.read_bytes(),b'')
            with self.assertRaises(FileExistsError):collector.save_raw(path,b'other')

    def test_recover_preserves_both_files_with_metadata_only_installed_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);base=root/'workspace/private';base.mkdir(parents=True)
            first,_=early_file();hook=base/'hook';hook.write_bytes(b'fixture physical hook')
            key=base/'key';key.write_bytes(Fixture.key)
            selection=dict(selected(),profile=profile.PROFILE,namespace='p432',version='v0.8.0-rc.1',virtual=False,
                hook=pin(hook),installed_init=dict(size=69504,sha256=(b'i'*32).hex()))
            second=runtime_file(first,hook=bytes.fromhex(selection['hook']['sha256']))
            build=publish(base/'build.json',selection);artifact=publish(base/'artifact.json',dict(build=build))
            writer_image=dict(profile=profile.PROFILE,namespace='p432',version='v0.8.0-rc.1',
                run_id_hex=selection['run_id'],key=pin(key),autoboot_boot=artifact)
            operation=base/'reader';operation.mkdir();publish(operation/'root-evidence.json',{'fixture':True})
            files=[]
            for rule,data in zip(evidence.paths(selection['run_id'],evidence.AUTOBOOT_PAIR),(first,second)):
                files.append(dict(path=rule[0],status='READ',size=len(data),captured=len(data),offset=0,
                    sha256=hashlib.sha256(data).hexdigest(),raw_hex=data.hex()))
            proof=dict(source_view_clean=True,files=files)
            session=SimpleNamespace(completed=lambda steps:[dict(proof=dict(root_evidence=proof))])
            shared=dict(task=dict(target={'fixture':'target'},A={'fixture':'rollback'}),closed=build,terminal_receipt=build)
            writer=dict(shared,request=dict(N=writer_image))
            reader=dict(shared,request=dict(N=dict(run_id_hex='f'*32,
                root_evidence=evidence.binding(selection['run_id'],evidence.AUTOBOOT_PAIR))),
                session=session,adapter=SimpleNamespace(directory=operation))
            out=base/'retrieval';real_project=collector.project
            def after_preservation(*args,**kwargs):
                self.assertEqual((out/'early.bin').read_bytes(),first)
                self.assertEqual((out/'runtime.bin').read_bytes(),second)
                self.assertTrue((out/'raw.json').exists())
                return real_project(*args,**kwargs)
            with mock.patch.object(collector,'ROOT',root), \
                    mock.patch.object(collector,'closed_operation',side_effect=[writer,reader]), \
                    mock.patch.object(collector,'operation_steps',return_value=[Step('root-evidence','observe','N','detach')]), \
                    mock.patch.object(collector,'project',side_effect=after_preservation):
                result=read(verify(collector.recover(out,base/'writer',operation)))
            self.assertEqual(result['proof']['highest_authenticated_stage'],'SERVICES_120S_COMPLETE')


if __name__=='__main__':unittest.main()
