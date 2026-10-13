"""File history, timing and physical-return facts keep separate meanings."""
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_debian_file_protocol_v1 as protocol
import s22plus_debian_file_profile_v1 as profile
import s22plus_debian_file_window_v1 as window
import s22plus_debian_file_retrieval_v1 as retrieval
import s22plus_debian_early_profile_v1 as early
import s22plus_native_records_v3 as records
import s22plus_native_root_inspect_session_v1 as scope


class FileRecords(unittest.TestCase):
    key=bytes(range(32));candidate=bytes(range(16));names=['driver_a','driver_b']
    boot=b'12345678-1234-1234-1234-123456789abc'
    expected=dict(shell_sha256='11'*32,init_sha256='22'*32,helper_sha256='33'*32)

    def fixture(self,*,origin=100,elapsed=None,error_at=None):
        boot=hashlib.sha256(self.boot).digest()
        events=[b'BEGIN run='+self.candidate.hex().encode()+b' boot='+self.boot+b' parent=1',b'TARGET_GUARD_OK']
        for ordinal,name in enumerate(self.names,1):
            events += [f'MODULE_{state} ordinal={ordinal} name={name}'.encode() for state in ('BEGIN','DONE')]
        events += [b'MODULE_SET_READY count=2',b'LOGGING_RAM_ONLY retention_after_reboot=not_available',
            b'TERMINAL result=PLATFORM_READY error=0']
        log=b''.join(f'FYG8_H0 seq={i} '.encode()+event+b'\n' for i,event in enumerate(events,1))
        proof=struct.pack('<4I',1,42,0,len(log))+boot+bytes.fromhex(self.expected['shell_sha256'])+\
            bytes.fromhex(self.expected['init_sha256'])+hashlib.sha256(log).digest()+bytes.fromhex(self.expected['helper_sha256'])
        header=b'S22FL01\0'+struct.pack('<II',1,256)+self.candidate+proof+struct.pack('<Q',origin)+bytes(8)
        signature=protocol.common.tag(self.key,self.candidate,boot,0,0,header,domain=protocol.DOMAIN)
        raw=header+signature+log;offset=len(raw)
        steps=[(1,0),*((k,p) for p in range(1,4) for k in (2,3)),(4,0)]
        for seq,(kind,phase) in enumerate(steps):
            body=b'S22FLR1\0'+struct.pack('<IIQII',seq,kind,seq if elapsed is None else elapsed,
                phase,5 if seq==error_at else 0)+bytes(32)+signature
            signature=protocol.common.tag(self.key,self.candidate,boot,kind,seq,body,domain=protocol.DOMAIN)
            raw+=body+signature
        return raw,offset

    def decode(self,raw,**kwargs):
        return protocol.decode(raw,key=self.key,run=self.candidate,expected=self.expected,module_names=self.names,**kwargs)

    def test_complete_proves_only_pre_unmount_history(self):
        value=self.decode(self.fixture()[0])
        self.assertTrue(value['debian_early_pid1']);self.assertTrue(value['pre_unmount_complete'])
        self.assertEqual(len(value['records']),8)
        for field in ('installed_debian_pid1','live_usb_proved','unmount_return_proved',
                'clean_filesystem_proved','nonexecution_proved','replay_authorized'):
            self.assertFalse(value[field],field)

    def test_aligned_and_torn_prefixes_never_become_complete(self):
        raw,start=self.fixture()
        for size,count in ((start,0),(start+256,2),(start+300,2)):
            with self.subTest(size=size):
                with self.assertRaises(ValueError):self.decode(raw[:size])
                prefix=self.decode(raw[:size],allow_prefix=True)
                self.assertFalse(prefix['pre_unmount_complete']);self.assertEqual(len(prefix['records']),count)

    def test_missing_or_modified_preparation_is_not_authenticated(self):
        raw,start=self.fixture()
        for changed in (raw[:256],raw[:300]+bytes([raw[300]^1])+raw[301:]):
            with self.assertRaises(ValueError):self.decode(changed,allow_prefix=True)

    def test_foreign_run_key_and_source_measurement_rejected(self):
        raw,_=self.fixture()
        common=dict(key=self.key,run=self.candidate,expected=self.expected,module_names=self.names)
        for changed in (dict(key=b'x'*32),dict(run=b'x'*16),
                dict(expected=dict(self.expected,helper_sha256='44'*32))):
            with self.subTest(changed=changed),self.assertRaises(ValueError):
                protocol.decode(raw,**dict(common,**changed))

    def test_absolute_deadline_is_authenticated_but_still_enforced(self):
        for origin,elapsed in ((300000,0),(299999,1),(299990,100)):
            with self.subTest(origin=origin),self.assertRaises(ValueError):
                self.decode(self.fixture(origin=origin,elapsed=elapsed)[0])

    def test_error_and_reordered_records_do_not_gain_completion(self):
        failed,start=self.fixture(error_at=3)
        with self.assertRaises(ValueError):self.decode(failed)
        self.assertEqual(len(self.decode(failed,allow_prefix=True)['records']),3)
        raw,start=self.fixture();changed=raw[:start]+raw[start+128:start+256]+raw[start:start+128]+raw[start+256:]
        with self.assertRaises(ValueError):self.decode(changed)

    def test_file_has_no_usb_protocol(self):
        with self.assertRaises(ValueError):early.wire_protocol(dict(profile=profile.PROFILE))


class FileWindow(unittest.TestCase):
    def test_consumption_is_bound_to_the_writer_and_operation(self):
        image=dict(namespace='p999',run_id_hex='12'*16,
            ap=dict(size=123,sha256='34'*32),member=dict(name='boot.img.lz4',size=100,sha256='56'*32))
        identity=retrieval.image_identity(image,'78'*32)
        claim=dict(candidate_key=identity['candidate_key'],record={k:v for k,v in identity.items() if k!='schema'})
        with mock.patch.object(retrieval.registry,'active_claim',return_value=claim['record']):
            retrieval.original_claim(image,'78'*32,claim)
            with self.assertRaises(ValueError):retrieval.original_claim(image,'90'*32,claim)
            other=dict(image,ap=dict(size=123,sha256='ab'*32))
            with self.assertRaises(ValueError):retrieval.original_claim(other,'78'*32,claim)

    def test_actual_common_and_target_adoption(self):
        details=(ROOT/'docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md').read_bytes()
        profile.validate_adoption(ROOT,details)
        with self.assertRaises(ValueError):
            profile.validate_adoption(ROOT,details.replace(Path(profile.POLICY).name.encode(),b'UNADOPTED'))

    def test_exact_task_duration_is_required_before_device_work(self):
        task=dict(N=dict(profile=profile.PROFILE),operations=['debian-early'],E=None,admission=None,
            prior_terminal=None,recovery_mode='attended',operation_budget=1,seconds=60,
            reentry=False,hud=False,usb_reconnect=False,target={},A={})
        with mock.patch.object(early,'image_binding'),mock.patch.object(scope,'android_basis_for_image'):
            with self.assertRaises(ValueError):scope.validate_task(task)
            task['seconds']=1800;scope.validate_task(task)

    def test_remaining_budget_does_not_renew_grant(self):
        grant=dict(opened_ns=1,deadline_ns=1800*10**9)
        profile.before_transfer(grant,2)
        for now in (0,600*10**9,1799*10**9):
            with self.assertRaises(ValueError):profile.before_transfer(grant,now)

    def test_window_is_original_transfer_time_only_and_cannot_reopen(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary).resolve()
            grant=records.publish(directory/'grant.json',dict(host_boot='fixed-host-boot',opened_ns=10**9,
                deadline_ns=1800*10**9))
            request=dict(N=dict(profile=profile.PROFILE),grant=grant)
            records.publish(directory/'operation.json',request)
            transfer=dict(action='transfer',fixed_fixture=True)
            receipt=records.publish(directory/'install-native-first.json',transfer)
            with mock.patch.object(records,'clock',side_effect=[100*10**9,101*10**9]):
                journal=records.Journal(directory/'journal')
                journal.append('effect-intent',step='install-native-first',action='transfer',role='N')
                journal.append('step-complete',step='install-native-first',result=receipt)
            class Adapter:
                def folder(self,name):return self.directory/('io-'+name)
                def recover_transfer_result(self,step,operation):return transfer
            adapter=Adapter();adapter.directory=directory
            before={p.name:p.read_bytes() for p in (directory/'journal').iterdir() if p.is_file()}
            ticks=[101*10**9,101*10**9,281*10**9,461*10**9,461*10**9]
            with mock.patch.object(profile,'image_binding'),mock.patch.object(window,'clock',side_effect=ticks),\
                    mock.patch.object(window.time,'sleep'):
                value=window.observe(adapter,request,guard=lambda:None)
                with self.assertRaises(FileExistsError):window.observe(adapter,request,guard=lambda:None)
            self.assertEqual(value,window.rederive(adapter,request))
            self.assertEqual(value['proof']['status'],'AWAITING_OFFLINE_FILE_RECORD')
            self.assertEqual(value['proof']['device_activity'],'UNKNOWN')
            for key in ('debian_early_pid1','file_write_proved','live_usb_proved','replay_authorized'):
                self.assertFalse(value['proof'][key])
            self.assertEqual({p.name:p.read_bytes() for p in (directory/'journal').iterdir() if p.is_file()},before)
            opened=records.read(adapter.folder('debian-early-evidence')/'open.json')
            self.assertEqual(opened['basis']['window_end_ns'],461*10**9)


class FileRetrieval(unittest.TestCase):
    def project(self,data,*,wrong_run=False,fixture=None,storage_first=False):
        fixture=fixture or FileRecords();temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        root=Path(temporary.name);output=root/'projection';reader_path=root/'reader';reader_path.mkdir()
        key=root/'key';key.write_bytes(fixture.key)
        writer_path=root/'writer';writer_path.mkdir()
        selected_profile=retrieval.first_profile if storage_first else retrieval.profile
        records.publish(writer_path/'operation.json',dict(N=dict(profile=selected_profile.PROFILE)))
        records.publish(reader_path/(retrieval.evidence.SELECTION+'.json'),dict(fixed_reader_result=True))
        selected=dict(path='var/lib/lab/s22-evidence-'+fixture.candidate.hex(),status='READ',raw_hex=data.hex())
        acquired=dict(files=[selected],source_view_clean=True)
        task=dict(target=dict(fixed_target=True),A=dict(fixed_original=True))
        common=dict(task=task,closed=dict(fixed_closed=True),terminal_receipt=dict(fixed_terminal=True))
        writer=dict(common,request=dict(N=dict(run_id_hex=fixture.candidate.hex(),key=records.pin(key),
            early_boot=dict(fixed_artifact=True))))
        reader=dict(common,request=dict(N=dict(run_id_hex='ff'*16,
            root_evidence=dict(record_run='aa'*16 if wrong_run else fixture.candidate.hex()))),
            adapter=SimpleNamespace(directory=reader_path),
            session=SimpleNamespace(completed=lambda plan:[dict(proof=dict(root_evidence=acquired))]))
        artifact=dict(expected=fixture.expected,module_names=fixture.names)
        step=retrieval.Step(retrieval.evidence.SELECTION,'observe','N')
        with mock.patch.object(retrieval,'private_path',side_effect=lambda base,p,**kw:Path(p)),\
                mock.patch.object(retrieval,'closed_operation',side_effect=[writer,reader]),\
                mock.patch.object(selected_profile,'image_binding',return_value=artifact),\
                mock.patch.object(retrieval,'operation_steps',return_value=(step,)):
            if wrong_run:
                with self.assertRaises(ValueError):retrieval.recover(output,root/'writer',reader_path)
                self.assertFalse(output.exists());return None
            receipt=retrieval.recover(output,root/'writer',reader_path)
        self.assertEqual((output/'record.bin').read_bytes(),data)
        self.assertEqual(records.read(output/'acquisition.json')['file']['raw_hex'],data.hex())
        return records.read(records.verify(receipt))

    def test_complete_offline_projection_keeps_unmount_separate(self):
        result=self.project(FileRecords().fixture()[0])
        self.assertEqual(result['status'],'PASS_PERSISTED_EARLY_PID1_PRE_UNMOUNT')
        self.assertTrue(result['writer_android_healthy']);self.assertTrue(result['source_view_clean'])
        self.assertFalse(result['proof']['unmount_return_proved'])

    def test_failed_decoder_keeps_raw_and_partial_status(self):
        result=self.project(b'invalid raw file')
        self.assertEqual(result['status'],'NO_AUTHENTICATED_FILE');self.assertIn('strict_error',result)
        raw,start=FileRecords().fixture();result=self.project(raw[:start+140])
        self.assertEqual(result['status'],'PARTIAL_PERSISTED_EARLY_PID1')
        self.assertFalse(result['proof']['pre_unmount_complete'])

    def test_other_writer_selection_cannot_create_projection(self):
        self.project(FileRecords().fixture()[0],wrong_run=True)


if __name__=='__main__':unittest.main()
