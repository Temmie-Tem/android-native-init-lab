"""Fixed H0 wire, memory-coverage and DT-identity regression cases."""
import contextlib
import copy
import hashlib
import importlib
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'workspace/public/src/mainline/s22plus_canary_h0'
sys.path.insert(0,str(HERE))
import prepare
import verify
import vm_evidence


class CanaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='mainline-h0-',dir=ROOT/'workspace/private/tmp')
        cls.base=Path(cls.tmp.name);cls.key=bytes(range(32));cls.identity=bytes(range(32,64));cls.nonce=bytes(range(64,96))
        cls.codec=cls.base/'codec'
        subprocess.run(['aarch64-linux-gnu-gcc','-std=c11','-static','-Os','-Wall','-Wextra','-Werror',
                        '-Wno-unused-function',ROOT/'tests/s22plus_mainline_protocol_fixture.c','-o',cls.codec],check=True)
        source='/dts-v1/; / { model="fixture"; compatible="samsung,g0q"; #address-cells=<2>; #size-cells=<2>; chosen { bootargs="fixture"; }; };'
        cls.dtb=cls.base/'expected.dtb';cls.compile_dts(source,cls.dtb)
        source=source.replace('chosen {','chosen { linux,initrd-start=/bits/ 64 <0x100000>; linux,initrd-end=/bits/ 64 <0x101000>;')
        cls.live=cls.base/'live.dtb';cls.compile_dts(source,cls.live)
        reserved=cls.base/'reserved.dtb';cls.compile_dts(source.replace('/dts-v1/;','/dts-v1/; /memreserve/ 0x200000 0x1000;'),reserved)
        cls.reserved=reserved.read_bytes()
        (cls.base/'key.bin').write_bytes(cls.key)
        cls.manifest={'vm':False,'key_path':str(cls.base/'key.bin'),'candidate_id':cls.identity.hex(),
                      'init':{'sha256':hashlib.sha256(b'fixture-init').hexdigest()},
                      'kernel_release':'fixture-release','initrd_address':0x100000,'initramfs':{'size':0x1000},
                      'dtb':{'path':str(cls.dtb),'sha256':prepare.digest(cls.dtb)}}

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    @classmethod
    def compile_dts(cls,source,path):
        subprocess.run(['dtc','-I','dts','-O','dtb','-o',path],input=source.encode(),check=True,capture_output=True)

    def body(self,fdt=None):
        fdt=self.live.read_bytes() if fdt is None else fdt
        b=bytearray(256);b[:8]=b'G0QRSP1\0';b[8:40]=self.identity;b[40:72]=self.nonce
        b[72:88]=bytes(range(1,17));b[88:120]=hashlib.sha256(fdt).digest()
        b[120:152]=bytes.fromhex(self.manifest['init']['sha256']);b[152:167]=b'fixture-release'
        struct.pack_into('<QIIIIQII',b,216,1000,1,1,0,1,20,len(fdt),0)
        return b

    def raw(self,body=None,fdt=None):
        fdt=self.live.read_bytes() if fdt is None else fdt
        body=self.body(fdt) if body is None else body
        result=subprocess.run(['qemu-aarch64',self.codec,'response'],input=body,capture_output=True,check=True)
        self.assertEqual(result.stdout[-32:],verify.tag(self.key,self.identity,1,body))
        return result.stdout+fdt

    def check(self,raw,manifest=None,nonce=None):
        path=self.base/'response.raw';path.write_bytes(raw)
        return verify.verify(path,self.manifest if manifest is None else manifest,
                             self.nonce if nonce is None else nonce)

    def test_real_arm64_request_and_response(self):
        request=verify.request(self.key,self.identity,self.nonce)
        self.assertEqual(subprocess.run(['qemu-aarch64',self.codec,'request'],input=request).returncode,0)
        bad=bytearray(request);bad[-1]^=1
        self.assertEqual(subprocess.run(['qemu-aarch64',self.codec,'request'],input=bad).returncode,1)
        self.assertEqual(self.check(self.raw())['status'],'AUTHENTICATED_CANARY_OBSERVATION')

    def test_truncation_tamper_nonce_and_duplicate(self):
        raw=self.raw()
        variants=[raw[:200],raw[:-1],raw+raw,bytes([raw[0]^1])+raw[1:],raw[:-1]+bytes([raw[-1]^1])]
        for value in variants:
            with self.subTest(size=len(value)),self.assertRaises(ValueError):self.check(value)
        with self.assertRaises(ValueError):self.check(raw,nonce=bytes(32))

    def test_authenticated_wrong_health_fields_rejected(self):
        for offset,fmt,value in [(216,'Q',0),(216,'Q',120000),(224,'I',2),(228,'I',2),(232,'I',1),
                                  (236,'I',0),(240,'Q',19),(240,'Q',5001),(252,'I',1)]:
            with self.subTest(offset=offset,value=value):
                body=self.body();struct.pack_into('<'+fmt,body,offset,value)
                with self.assertRaises(ValueError):self.check(self.raw(body))

    def test_measured_identity_and_vm_separation(self):
        for offset in [8,72,120,152]:
            body=self.body()
            if offset==72:body[72:88]=bytes(16)
            else:body[offset]^=1
            with self.subTest(offset=offset),self.assertRaises(ValueError):self.check(self.raw(body))
        m=copy.deepcopy(self.manifest);m['vm']=True
        with self.assertRaises(ValueError):self.check(self.raw(),manifest=m)

    def test_header_reservation_and_boot_cpu_rejected(self):
        with self.assertRaises(ValueError):self.check(self.raw(fdt=self.reserved))
        data=bytearray(self.live.read_bytes());struct.pack_into('>I',data,28,1)
        with self.assertRaises(ValueError):self.check(self.raw(fdt=data))
        data=bytearray(self.live.read_bytes());struct.pack_into('>I',data,16,len(data)-8)
        with self.assertRaises(ValueError):self.check(self.raw(fdt=data))

    def test_interval_coverage_handles_overlaps_and_holes(self):
        self.assertEqual(prepare.uncovered([(10,30),(20,40)],[(0,15),(17,25),(25,35)]),[(15,17),(35,40)])
        self.assertEqual(prepare.uncovered([(10,20)],[(10,20)]),[])
        self.assertEqual(prepare.uncovered([(10,20)],[(20,30)]),[(10,20)])
        with self.assertRaises(ValueError):prepare.merged([(20,10)])

    def test_only_effective_nomap_reservations_cover_live_ranges(self):
        props={'reg':struct.pack('>QQ',0x1000,0x2000),'no-map':b''}
        for change,covered in [({},True),({'status':b'ok\0'},True),({'status':b'disabled\0'},False),
                                ({'reusable':b''},False),({'no-map':None},False)]:
            row=dict(props);row.update(change)
            row={k:v for k,v in row.items() if v is not None}
            tree={'/reserved-memory/fixture':row}
            self.assertEqual(prepare.fixed_reservations(tree),[(0x1000,0x3000)])
            self.assertEqual(prepare.fixed_reservations(tree,coverage=True),[(0x1000,0x3000)] if covered else [])

    def vm_capture(self, root):
        init=root/'init';init.mkdir();prepared=root/'prepared';prepared.mkdir();run=root/'run';run.mkdir()
        manifest=copy.deepcopy(self.manifest);manifest['vm']=True
        for name,data in [('init',b'fixture-init'),('initramfs',b'fixture-archive')]:
            path=init/name;path.write_bytes(data)
            manifest[name]={'path':str(path),'sha256':prepare.digest(path),'size':len(data)}
        key=init/'key.bin';key.write_bytes(self.key);manifest['key_path']=str(key)
        (init/'result.json').write_text(json.dumps(manifest))
        kernel=prepared/'Image';kernel.write_bytes(b'fixture-kernel')
        (prepared/'kernel-1-result.json').write_text(json.dumps({'image':str(kernel),'sha256':prepare.digest(kernel)}))
        fdt=run/'vm.dtb';self.compile_dts('/dts-v1/; / { compatible="linux,dummy-virt"; };',fdt)
        body=self.body(fdt.read_bytes());struct.pack_into('<I',body,252,1)
        (run/'response.raw').write_bytes(self.raw(body,fdt.read_bytes()))
        (run/'nonce.bin').write_bytes(self.nonce)
        (run/'request.raw').write_bytes(verify.request(self.key,self.identity,self.nonce))
        (run/'command.json').write_text('{}')
        (run/'serial.log').write_text('G0Q_RAM_OBSERVER_READY\n')
        (run/'qemu.stderr').write_text('')
        vm_evidence.capture(run,vm_evidence.inputs(prepared,init,'kernel-1'),vm_evidence.snapshot(run),
                            bad_key=False,elapsed=10.0,returncode=-15)
        return prepared,init,run

    def replay(self, prepared, init, run, output):
        # A recheck cannot quietly turn a missing/invalid capture into a new VM run.
        with (patch('subprocess.Popen',side_effect=AssertionError('unexpected process')),
              patch('socket.socket',side_effect=AssertionError('unexpected network')),
              contextlib.redirect_stdout(io.StringIO())):
            return vm_evidence.recheck(prepared,init,run,output)

    def test_vm_recheck_preserves_original_and_accepts_checker_only_change(self):
        with tempfile.TemporaryDirectory(dir=self.base) as name:
            root=Path(name);prepared,init,run=self.vm_capture(root)
            before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            first=self.replay(prepared,init,run,root/'recheck-1')
            self.assertEqual(first['status'],'PASS_H0_VM_EVIDENCE_RECHECK')
            self.assertEqual(first['vm_executions'],0)
            self.assertEqual(first['observation_status'],'PASS_H0_VM_PID1_OBSERVER')
            changed=root/'changed';changed.mkdir()
            for p in (run/'source').iterdir():shutil.copyfile(p,changed/p.name)
            with (changed/'verify.py').open('a') as stream:stream.write('\n# checker-only revision\n')
            with patch.object(vm_evidence,'HERE',changed):
                second=self.replay(prepared,init,run,root/'recheck-2')
            self.assertNotEqual(first['validator_source']['verify.py'],second['validator_source']['verify.py'])
            self.assertEqual(first['capture'],second['capture'])
            self.assertEqual(before,{p:Path(p).read_bytes() for p in before})
            # No old result.json is necessary: complete raw capture survives a parser failure.
            self.assertFalse((run/'result.json').exists())

    def test_vm_recheck_rejects_changed_or_missing_inputs_and_evidence(self):
        cases=['kernel','initramfs','key','nonce.bin','request.raw','response.raw','serial.log',
               'command.json','source/verify.py','missing-capture','missing-response','bad-key','partial-evidence']
        for case in cases:
            with self.subTest(case=case),tempfile.TemporaryDirectory(dir=self.base) as name:
                root=Path(name);prepared,init,run=self.vm_capture(root)
                target={'kernel':prepared/'Image','initramfs':init/'initramfs','key':init/'key.bin'}.get(case,run/case)
                if case.startswith('missing-'):
                    (run/('capture.json' if case=='missing-capture' else 'response.raw')).unlink()
                elif case in ('bad-key','partial-evidence'):
                    receipt=json.loads((run/'capture.json').read_text())
                    if case=='bad-key':receipt['bad_key']=True
                    else:del receipt['evidence']['serial.log']
                    (run/'capture.json').write_text(json.dumps(receipt))
                else:target.write_bytes(target.read_bytes()+b'changed')
                with self.assertRaises((ValueError,FileNotFoundError)):
                    self.replay(prepared,init,run,root/'recheck')

    def test_vm_recheck_reparses_instead_of_trusting_capture_label(self):
        with tempfile.TemporaryDirectory(dir=self.base) as name:
            root=Path(name);prepared,init,run=self.vm_capture(root)
            raw=bytearray((run/'response.raw').read_bytes());raw[236]=0
            # Even matching receipt hashes cannot turn an invalid authenticated response into PASS.
            raw[256:288]=verify.tag(self.key,self.identity,1,raw[:256])
            (run/'response.raw').write_bytes(raw)
            receipt=json.loads((run/'capture.json').read_text())
            receipt['evidence']['response.raw']=prepare.digest(run/'response.raw')
            (run/'capture.json').write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError,'health fields'):
                self.replay(prepared,init,run,root/'recheck')
            with self.assertRaisesRegex(ValueError,'outside original run'):
                self.replay(prepared,init,run,run/'recheck')


if __name__=='__main__':unittest.main()
