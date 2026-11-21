"""Regression checks for the VM-only SCM observation schema."""
import hashlib
import importlib.util
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'workspace/public/src/mainline/s22plus_canary_h0'
sys.path.insert(0, str(SOURCE))
from scm_usb_h0 import stage_sources


class ScmUsbTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.key = bytes(range(32))
        self.identity = bytes(range(32, 64))
        self.nonce = bytes(range(64, 96))
        self.keyfile = self.base / 'key'
        self.keyfile.write_bytes(self.key)
        self.raw = self.base / 'response'
        self.fdt = subprocess.run(
            ['dtc', '-I', 'dts', '-O', 'dtb'],
            input=b'/dts-v1/; / { compatible = "linux,dummy-virt"; };',
            capture_output=True, check=True).stdout

    def profile(self, subject):
        directory = self.base / subject
        schema = stage_sources(directory, lifecycle_model=subject == 'platform-model',
                               board=subject == 'board')
        spec = importlib.util.spec_from_file_location('scm_verify', directory / 'scm_verify.py')
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        manifest = {
            'vm': subject != 'board', 'key_path': str(self.keyfile), 'candidate_id': self.identity.hex(),
            'kernel_release': 'fixture', 'init': {'sha256': '11' * 32},
            'debian_ram': {'schema': schema, 'observer': {'sha256': '22' * 32},
                           'inittab_sha256': '33' * 32},
        }
        return verifier, manifest

    def response(self, verifier, manifest, readout):
        body = bytearray(356)
        body[:8] = verifier.protocol(manifest)[2]
        body[8:40] = self.identity
        body[40:72] = self.nonce
        body[72] = 1
        body[88:120] = hashlib.sha256(self.fdt).digest()
        body[120:152] = bytes.fromhex(manifest['init']['sha256'])
        body[152:159] = b'fixture'
        struct.pack_into('<QIIIIQII', body, 216, 1000, 1, 1, 0, 1, 20, len(self.fdt), int(manifest['vm']))
        struct.pack_into('<IIIII', body, 256, 2, 1, 1, ord('2'), ord('N'))
        runtime = manifest['debian_ram']
        body[288:320] = bytes.fromhex(runtime['observer']['sha256'])
        body[320:352] = bytes.fromhex(runtime['inittab_sha256'])
        struct.pack_into('<I', body, 352, readout)
        tag = verifier.tag(self.key, self.identity, 1, body, manifest=manifest)
        return body + tag + self.fdt

    def test_signed_readout_and_unknown_value(self):
        verifier, manifest = self.profile('scm')
        for value, expected in enumerate(('indeterminate', 'unbound', 'bound')):
            with self.subTest(value=value):
                self.raw.write_bytes(self.response(verifier, manifest, value))
                result = verifier.verify(self.raw, manifest, self.nonce, vm=True)
                self.assertEqual((result['subject'], result['scm_binding']), ('scm', expected))
        changed = self.response(verifier, manifest, 1)
        changed[352] = 2
        self.raw.write_bytes(changed)
        with self.assertRaisesRegex(ValueError, 'response HMAC'):
            verifier.verify(self.raw, manifest, self.nonce, vm=True)
        self.raw.write_bytes(self.response(verifier, manifest, 3))
        with self.assertRaisesRegex(ValueError, 'unknown SCM binding value'):
            verifier.verify(self.raw, manifest, self.nonce, vm=True)

    def test_model_and_vm_boundaries(self):
        scm, scm_manifest = self.profile('scm')
        model, model_manifest = self.profile('platform-model')
        self.raw.write_bytes(self.response(model, model_manifest, 2))
        with self.assertRaisesRegex(ValueError, 'response HMAC'):
            scm.verify(self.raw, scm_manifest, self.nonce, vm=True)
        with self.assertRaisesRegex(ValueError, 'incorrect SCM observation schema'):
            scm.verify(self.raw, model_manifest, self.nonce, vm=True)
        with self.assertRaisesRegex(ValueError, 'qualified only for H0'):
            model.verify(self.raw, dict(model_manifest, vm=False), self.nonce, vm=False)

    def test_board_domain_and_capture_entry(self):
        board, manifest = self.profile('board')
        vm, vm_manifest = self.profile('scm')
        self.assertFalse(hasattr(board, 'verify'))
        for index in (0, 1, 2):
            self.assertNotEqual(board.protocol(manifest)[index], vm.protocol(vm_manifest)[index])
        self.assertNotEqual(board.request(self.key, self.identity, self.nonce, manifest=manifest),
                            vm.request(self.key, self.identity, self.nonce, manifest=vm_manifest))
        sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
        self.addCleanup(sys.path.pop, 0)
        with self.assertRaisesRegex(ValueError, 'immutable capture handle'):
            board.verify_capture(self.raw, manifest, self.nonce, expected_loader_fdt_sha256='00' * 32)
        with self.assertRaisesRegex(ValueError, 'VM-only'):
            stage_sources(self.base / 'wrong', lifecycle_model=True, board=True)

    def test_board_capture_rejects_an_extra_empty_node(self):
        board, manifest = self.profile('board')
        sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
        self.addCleanup(sys.path.pop, 0)
        import device_action_raw_capture_v1 as capture

        def compile_dt(source):
            return subprocess.run(['dtc', '-I', 'dts', '-O', 'dtb', '-S', '1024'],
                                  input=source.encode(), capture_output=True, check=True).stdout

        source = '/dts-v1/; / { compatible = "samsung,g0q", "qcom,sm8450"; chosen { bootargs = "fixture"; }; };'
        target = self.base / 'expected.dtb'
        target.write_bytes(compile_dt(source))
        manifest.update(dtb={'path': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()},
                        initrd_address=4096, initramfs={'size': 128})
        rewritten = source.replace('chosen {', 'chosen { linux,initrd-start = /bits/ 64 <4096>; '
                                   'linux,initrd-end = /bits/ 64 <4224>;')
        self.fdt = compile_dt(rewritten)
        expected_digest = hashlib.sha256(self.fdt).hexdigest()
        raw_dir = capture.prepare_capture_dir(self.base)

        def parse(name):
            payload = bytes(self.response(board, manifest, 1))
            handle = capture.publish_captured_bytes(raw_dir, name, stdout=payload)
            return board.verify_capture(handle, manifest, self.nonce, expected_loader_fdt_sha256=expected_digest)

        self.assertEqual(parse('baseline')['scm_binding'], 'unbound')
        self.fdt = compile_dt(rewritten.replace('chosen {', 'extra-node {}; chosen {'))
        self.assertEqual(len(self.fdt), 1024)
        with self.assertRaisesRegex(ValueError, 'live FDT differs from qualified loader output'):
            parse('extra-node')
