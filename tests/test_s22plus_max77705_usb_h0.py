"""Regression checks for the MAX77705 USB observation profile (staging, wire, decoder)."""
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
from max77705_usb_h0 import stage_sources, BODY  # noqa: E402
import max77705_record as rec  # noqa: E402

SEAL = ('#define CANARY_PORT 47649\n'
        'static const unsigned char canary_key[32]={0},canary_id[32]={0};\n'
        'static const char canary_device_ip[]="192.0.2.2";\n'
        'static const char canary_host_ip[]="192.0.2.1";\n'
        'static const char canary_netmask[]="255.255.255.0";\n'
        'static const char canary_serial[]="fixture";\n'
        'static const char canary_udc[]="dummy_udc.0";\n'
        'static const char canary_device_mac[]="02:00:00:00:00:02";\n'
        'static const char canary_host_mac[]="02:00:00:00:00:01";\n')


def record(adapter=0, events=(), total=None, rejected=0):
    out = bytearray(rec.SIZE)
    struct.pack_into('<IIII', out, 0, 1, adapter, 0, 3)
    out[16:20] = bytes([0x15, 0x02, 0x1a, 0x6e])
    out[20], out[21] = 0x80, 1
    struct.pack_into('<I', out, 28, len(events) if total is None else total)
    out[32] = sum(1 for e in events if e[-1] != 4)
    out[34] = rejected
    struct.pack_into('<I', out, 36, max([e[0] for e in events], default=0) + 1)
    for i, (t, kind, uic, ctrl1, status) in enumerate(events):
        struct.pack_into('<IBBBBBBBB', out, rec.HEADER + i * rec.EVENT, t, kind, uic, 0, 0x81, 0, 0, ctrl1, status)
    return bytes(out)


class StagingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.key, self.identity, self.nonce = bytes(range(32)), bytes(range(32, 64)), bytes(range(64, 96))
        (self.base / 'key').write_bytes(self.key)
        self.raw = self.base / 'response'
        self.fdt = subprocess.run(['dtc', '-I', 'dts', '-O', 'dtb'],
                                  input=b'/dts-v1/; / { compatible = "linux,dummy-virt"; };',
                                  capture_output=True, check=True).stdout

    def profile(self, board=False):
        d = self.base / ('board' if board else 'vm')
        schema = stage_sources(d, board=board)
        spec = importlib.util.spec_from_file_location('mxv_' + d.name, d / 'max77705_verify.py')
        v = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(v)
        manifest = {'vm': not board, 'key_path': str(self.base / 'key'), 'candidate_id': self.identity.hex(),
                    'kernel_release': 'fixture', 'init': {'sha256': '11' * 32},
                    'debian_ram': {'schema': schema, 'observer': {'sha256': '22' * 32}, 'inittab_sha256': '33' * 32}}
        return v, manifest, d

    def response(self, v, manifest, rec_bytes):
        body = bytearray(BODY)
        body[:8] = v.protocol(manifest)[2]
        body[8:40], body[40:72], body[72] = self.identity, self.nonce, 1
        body[88:120] = hashlib.sha256(self.fdt).digest()
        body[120:152] = bytes.fromhex(manifest['init']['sha256'])
        body[152:159] = b'fixture'
        struct.pack_into('<QIIIIQII', body, 216, 1000, 1, 1, 0, 1, 20, len(self.fdt), int(manifest['vm']))
        struct.pack_into('<IIIII', body, 256, 2, 1, 1, ord('2'), ord('N'))
        body[288:320] = bytes.fromhex('22' * 32)
        body[320:352] = bytes.fromhex('33' * 32)
        body[352:] = rec_bytes
        return body + v.tag(self.key, self.identity, 1, bytes(body), manifest=manifest) + self.fdt

    def test_body_size_and_sources_compile_for_aarch64(self):
        self.assertEqual(BODY, 968)
        for board in (False, True):
            _, _, d = self.profile(board)
            (d / 'seal.h').write_text(SEAL)
            flags = ['-DCANARY_DEBIAN_RAM'] + ([] if board else ['-DCANARY_H0_VM'])
            r = subprocess.run(['aarch64-linux-gnu-gcc', '-fsyntax-only', *flags, '-I', str(d),
                                '-I', str(ROOT / 'workspace/public/src/native-init'), str(d / 'init.c')],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])
            wrong = ['-DCANARY_DEBIAN_RAM'] + (['-DCANARY_H0_VM'] if board else [])
            r = subprocess.run(['aarch64-linux-gnu-gcc', '-fsyntax-only', *wrong, '-I', str(d),
                                '-I', str(ROOT / 'workspace/public/src/native-init'), str(d / 'init.c')],
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)

    def test_signed_record_decodes(self):
        v, manifest, _ = self.profile()
        events = [(5, 0, 0x80, 0x3f, 0), (60000, 3, 0xa2, 0x09, 0)]
        self.raw.write_bytes(self.response(v, manifest, record(events=events)))
        result = v.verify(self.raw, manifest, self.nonce, vm=True)
        self.assertEqual(result['status'], 'AUTHENTICATED_H0_MAX77705_USB_OBSERVATION')
        self.assertEqual(result['max77705_verdict'], 'OPEN_THEN_COM_USB_AFTER_ATTACH')
        self.assertEqual([e['ctrl1'] for e in result['max77705']['events']], [0x3f, 0x09])
        self.assertEqual(result['subject'], 'max77705')

    def test_decoder_runs_from_pinned_bytes_without_sibling_file(self):
        # The attended session execs the decoder from checked bytes, with no __file__.
        v, manifest, d = self.profile()
        events = [(5, 0, 0x80, 0x3f, 0), (60000, 3, 0xa2, 0x09, 0)]
        self.raw.write_bytes(self.response(v, manifest, record(events=events)))
        source = (d / 'max77705_verify.py').read_bytes()
        (d / 'max77705_record.py').unlink()
        namespace = {'__name__': 'pinned_max77705_decoder'}
        exec(compile(source, '<pinned>', 'exec'), namespace)
        result = namespace['verify'](self.raw, manifest, self.nonce, vm=True)
        self.assertEqual(result['max77705_verdict'], 'OPEN_THEN_COM_USB_AFTER_ATTACH')

    def test_tamper_and_rejected_write(self):
        v, manifest, _ = self.profile()
        resp = self.response(v, manifest, record(events=[(5, 0, 0, 0x3f, 0)]))
        resp[352 + rec.HEADER + 10] = 0x09
        self.raw.write_bytes(resp)
        with self.assertRaisesRegex(ValueError, 'response HMAC'):
            v.verify(self.raw, manifest, self.nonce, vm=True)
        self.raw.write_bytes(self.response(v, manifest, record(events=[(5, 0, 0, 0x3f, 0)], rejected=1)))
        with self.assertRaisesRegex(ValueError, 'disallowed write'):
            v.verify(self.raw, manifest, self.nonce, vm=True)

    def test_verdicts(self):
        cases = {
            'INITIAL_COM_USB': [(5, 0, 0, 0x09, 0)],
            'OPEN_UNCHANGED_AFTER_ATTACH': [(5, 0, 0, 0x3f, 0), (9000, 3, 0x22, 0x3f, 0)],
            'OPEN_NO_ATTACH_SEEN': [(5, 0, 0, 0x3f, 0), (10000, 2, 0, 0x3f, 0)],
            'NO_PROOF_NO_CONTROL1_READ': [(5, 0, 0, 0, 1)],
        }
        for want, events in cases.items():
            with self.subTest(want=want):
                self.assertEqual(rec.verdict(rec.decode(record(events=events))), want)
        self.assertEqual(rec.verdict(rec.decode(record(adapter=1))), 'NO_PROOF_ADAPTER_ABSENT')

    def test_ring_order(self):
        # Simulate the C writer: slot = n-1 for the first 48, then a ring over the second half.
        total, slots = 60, [None] * rec.EVENTS
        for n in range(1, total + 1):
            slot = n - 1 if n <= rec.EVENTS else rec.EVENTS // 2 + (n - 1 - rec.EVENTS // 2) % (rec.EVENTS // 2)
            slots[slot] = (n * 100, 0, 0, 0x3f, 0) if n == 1 else (n * 100, 1, 0, 0, 4)
        d = rec.decode(record(events=slots, total=total))
        self.assertEqual(len(d['events']), 48)
        times = [e['t_ms'] for e in d['events']]
        self.assertEqual(times, sorted(times))
        self.assertEqual(times[24], (total - 24 + 1) * 100)

    def test_impossible_records_are_rejected(self):
        ok = [(5, 0, 0, 0x3f, 0), (9000, 3, 0x22, 0x3f, 0)]
        cases = {
            'command count exceeds': record(events=ok, total=None),
            'out of order': record(events=[(9000, 0, 0, 0x3f, 0), (5, 3, 0x22, 0x3f, 0)]),
            'leading begin': record(events=[(5, 2, 0, 0x3f, 0)]),
            'events without an identified adapter': record(adapter=1, events=ok),
            'kind and read status disagree': record(events=[(5, 0, 0, 0, 4), (9000, 3, 0x22, 0x09, 0)]),
            'limit status before the command limit': record(events=[(5, 0, 0, 0x3f, 0), (9000, 2, 0, 0, 5)]),
        }
        big = bytearray(cases['command count exceeds'])
        big[32] = 255
        cases['command count exceeds'] = bytes(big)
        for want, raw in cases.items():
            with self.subTest(want=want), self.assertRaisesRegex(ValueError, want):
                rec.decode(raw)

    def test_split_verdicts(self):
        cases = {
            'OTHER_INITIAL_CONTROL1': [(5, 0, 0, 0x12, 0)],
            'OPEN_THEN_OTHER_AFTER_ATTACH': [(5, 0, 0, 0x3f, 0), (9000, 3, 0x22, 0x34, 0)],
            'OPEN_NO_READ_AFTER_ATTACH': [(5, 0, 0, 0x3f, 0), (9000, 1, 0x22, 0, 4)],
        }
        for want, events in cases.items():
            with self.subTest(want=want):
                self.assertEqual(rec.verdict(rec.decode(record(events=events))), want)


if __name__ == '__main__':
    unittest.main()
