"""Cross-phase evidence and real provider binding failure boundaries."""
import errno
import hashlib
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_debian_integrated_protocol_v1 as wire

KEY=b'k'*32;RUN=b'r'*16;NONCE=b'n'*32
BOOT_TEXT=b'01234567-1234-1234-1234-0123456789ab';BOOT=hashlib.sha256(BOOT_TEXT).digest()
EXPECTED=dict(shell_sha256='11'*32,init_sha256='22'*32,helper_sha256='33'*32)
NAMES=['sec_log_buf']+[f'platform_{i}' for i in range(1,74)]+[f'ufs_{i}' for i in range(8)]
NAMES[67]='qcom_spmi_pmic'
SELECTION=dict(witness=dict(sha256='44'*32),installed_init=dict(sha256='55'*32),
    assets=dict(hook=dict(sha256='66'*32)),observer_revision=2)


def initial_log():
    events=[b'BEGIN run='+RUN.hex().encode()+b' boot='+BOOT_TEXT+b' parent=1',b'TARGET_GUARD_OK']
    for ordinal,name in enumerate(NAMES[:74],1):
        events.append(f'MODULE_BEGIN ordinal={ordinal} name={name}'.encode())
        if name=='sec_log_buf':events.append(b'LOGGER_BIND phase=0 error=0')
        events.append(f'MODULE_DONE ordinal={ordinal} name={name}'.encode())
        if name=='qcom_spmi_pmic':events.extend((b'PROVIDERS_BEGIN',b'PROVIDERS_READY mask=7'))
    events.append(b'TERMINAL result=PLATFORM_READY error=0')
    return b''.join(f'FYG8_H0 seq={seq} '.encode()+event+b'\n' for seq,event in enumerate(events,1))


def frame(kind,seq,body):
    return wire.frames.encode_frame(kind,seq,body+wire.early.tag(KEY,RUN,NONCE,kind,seq,body,domain=wire.DOMAIN))


def prefix(*,log=None,parent=1,status=0):
    log=initial_log() if log is None else log
    data=struct.pack('<4I',parent,90,status,len(log))+BOOT+bytes.fromhex(EXPECTED['shell_sha256'])+\
        bytes.fromhex(EXPECTED['init_sha256'])+hashlib.sha256(log).digest()+bytes.fromhex(EXPECTED['helper_sha256'])
    rows=[frame(wire.early.PROOF,2,data)];seq=3
    for offset in range(0,len(log),768):rows.append(frame(wire.early.LOG,seq,log[offset:offset+768]));seq+=1
    rows.append(frame(wire.early.END,seq,hashlib.sha256(log).digest()));seq+=1
    events=[b'BEGIN run='+RUN.hex().encode()+b' boot='+BOOT_TEXT+b' parent=1',b'TARGET_GUARD_OK']
    for ordinal,name in enumerate(NAMES[74:],75):
        events.extend(f'MODULE_{phase} ordinal={ordinal} name={name}'.encode() for phase in ('BEGIN','DONE'))
    events.append(b'TERMINAL result=UFS_MODULES_READY error=0')
    ufs=b''.join(f'FYG8_H0 seq={seq} '.encode()+event+b'\n' for seq,event in enumerate(events,220))
    for offset in range(0,len(ufs),768):rows.append(frame(wire.UFS_LOG,seq,ufs[offset:offset+768]));seq+=1
    rows.append(frame(wire.UFS_END,seq,hashlib.sha256(ufs).digest()))
    return rows


def root_rows(*,settlement=b'early-children-settled',boot=BOOT):
    rows=[]
    for stage in range(1,9):
        data=settlement if stage==2 else wire.handoff.base.LABELS.get(stage)
        if stage==8:data=struct.pack('<4I',1,8,41,7)+boot+bytes.fromhex('44'*32)+b'm'*32+bytes(8)
        rows.append(wire.handoff.encode(KEY,RUN,NONCE,wire.handoff.base.RECORD,1023+stage,struct.pack('<2I',stage,0)+data))
    return rows


class IntegratedProtocol(unittest.TestCase):
    def reader(self):return wire.Records(KEY,RUN,NONCE,EXPECTED,NAMES,SELECTION)
    def accept(self,state,rows):
        for raw in rows:state.accept(wire.frames.decode_frame(raw))

    def test_parent_platform_ufs_and_root_are_separate(self):
        state=self.reader();self.accept(state,prefix())
        result=state.projection()
        self.assertTrue(result['initial_parent']['debian_early_pid1'])
        self.assertFalse(result['initial_parent']['root_admitted'])
        self.assertFalse(result['ufs']['storage_admitted']);self.assertIsNone(state.handoff.proof)
        self.accept(state,root_rows());self.assertIsNotNone(state.handoff.proof)
        self.assertIsNone(state.handoff.init_proof);self.assertFalse(state.projection()['ssh_access_proved'])

    def test_wrong_parent_status_and_missing_provider_barrier_reject(self):
        for rows in (prefix(parent=2),prefix(status=1),prefix(log=initial_log().replace(b'PROVIDERS_READY mask=7',b'PROVIDERS_READY mask=3'))):
            state=self.reader()
            with self.assertRaises(ValueError):self.accept(state,rows)
            self.assertIsNone(state.handoff)

    def test_old_native_worker_claim_and_foreign_boot_do_not_transfer(self):
        for rows in (root_rows(settlement=b'three-workers-reaped'),root_rows(boot=b'x'*32)):
            state=self.reader();self.accept(state,prefix())
            with self.assertRaises(ValueError):self.accept(state,rows)
            self.assertIsNone(state.handoff.proof)

    def test_root_proof_cannot_skip_ufs_completion(self):
        state=self.reader();self.accept(state,prefix()[:-1])
        with self.assertRaises(ValueError):self.accept(state,root_rows())
        self.assertIsNone(state.handoff)

    def test_old_read_only_start_domain_is_rejected(self):
        tx=wire.early.request(KEY,RUN,NONCE)
        with self.assertRaises(ValueError):wire.replay(b''.join(prefix()),tx,key=KEY,run=RUN,expected=EXPECTED,
            module_names=NAMES,selection=SELECTION,complete=False)

    def test_retained_preparation_uses_distinct_domain_and_only_partial_meaning(self):
        import s22plus_debian_usb_protocol_v1 as retained
        event=b'TARGET_GUARD_OK';tag=wire.early.tag(KEY,RUN,BOOT,240,2,event,domain=wire.DOMAIN)
        raw=b'S22USB1 run='+RUN.hex().encode()+b' boot='+BOOT_TEXT+b' seq=2 mac='+tag.hex().encode()+b' '+event+b'\n'
        value=retained.retained(raw,key=KEY,run=RUN,domain=wire.DOMAIN)
        self.assertEqual(value['status'],'AUTHENTICATED_PARTIAL_RECORDS');self.assertFalse(value['nonexecution_proved'])
        with self.assertRaises(ValueError):retained.retained(raw,key=KEY,run=RUN)
        self.assertEqual(retained.retained(b'',key=KEY,run=RUN,domain=wire.DOMAIN)['records'],[])

    def test_partial_raw_prefix_preserves_parent_without_service_or_replay_proof(self):
        result=wire.replay(b''.join(prefix())+root_rows()[0][:-1],wire.request(KEY,RUN,NONCE),key=KEY,run=RUN,
            expected=EXPECTED,module_names=NAMES,selection=SELECTION,complete=False)
        self.assertTrue(result['initial_parent']['debian_early_pid1'])
        self.assertIsNotNone(result['diagnostic_error']);self.assertFalse(result['replay_authorized'])
        self.assertIsNone(result['debian_handoff']['init_proof'])


class ProviderBinding(unittest.TestCase):
    def test_actual_provider_scan_on_host_and_arm64(self):
        with tempfile.TemporaryDirectory(prefix='s22-di-providers-') as tmp:
            base=Path(tmp);binaries=[]
            for compiler,runner in (('gcc',[]),('aarch64-linux-gnu-gcc',['qemu-aarch64'])):
                binary=base/compiler
                subprocess.run([compiler,'-static','-Wall','-Wextra','-Werror','-Wno-unused-function',
                    '-I',str(ROOT/'workspace/public/src/debian/s22plus_initramfs_h0'),
                    str(ROOT/'tests/s22plus_debian_provider_harness.c'),'-o',str(binary)],check=True)
                binaries.append((binary,runner))
            for case,expected in (('ready',0),('missing',errno.EAGAIN),('unbound',errno.EAGAIN),
                                  ('wrong-driver',errno.EXDEV),('duplicate',errno.EEXIST),('driver-file',errno.EPROTO)):
                folder=base/case;devices=folder/'devices';drivers=folder/'drivers'
                devices.mkdir(parents=True);drivers.mkdir()
                if case!='missing':
                    for i in range(2 if case=='duplicate' else 1):
                        device=devices/f'device-{i}';device.mkdir()
                        (device/'of_node').symlink_to('../../../firmware/devicetree/base/soc/qcom,spmi@c42d000')
                        if case=='driver-file':(device/'driver').write_text('wrong type')
                        elif case!='unbound':
                            target=drivers/('foreign' if case=='wrong-driver' else 'spmi_pmic_arb');target.mkdir(exist_ok=True)
                            (device/'driver').symlink_to(target)
                for binary,runner in binaries:
                    with self.subTest(case=case,architecture=binary.name):
                        result=subprocess.check_output(['unshare','--user','--map-root-user',*runner,str(binary),str(devices)+'/'],text=True)
                        self.assertEqual(int(result),expected)


if __name__=='__main__':unittest.main()
