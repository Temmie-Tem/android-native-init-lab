"""Stage 2 MAX77705 route profile: real producer on a simulated device, staging, wire and decoder."""
import hashlib
import importlib.util
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'workspace/public/src/mainline/s22plus_canary_h0'
sys.path.insert(0, str(SOURCE))
from max77705_route_h0 import stage_sources, BODY  # noqa: E402
import max77705_route_record as rec  # noqa: E402

SEAL = ('#define CANARY_PORT 47649\n'
        'static const unsigned char canary_key[32]={0},canary_id[32]={0};\n'
        'static const char canary_device_ip[]="192.0.2.2";\n'
        'static const char canary_host_ip[]="192.0.2.1";\n'
        'static const char canary_netmask[]="255.255.255.0";\n'
        'static const char canary_serial[]="fixture";\n'
        'static const char canary_udc[]="dummy_udc.0";\n'
        'static const char canary_device_mac[]="02:00:00:00:00:02";\n'
        'static const char canary_host_mac[]="02:00:00:00:00:01";\n')

EXPECTED = {
    'pass': ('ROUTE_CONFIGURED_WITHOUT_REPLUG', 'written', 1),
    'nofix': ('ROUTE_CONFIGURED_AFTER_REPLUG', 'written', 1),
    'not_held': ('ROUTE_WRITE_NOT_HELD', 'written', 1),
    'write_timeout': ('ROUTE_WRITE_FAILED', 'written', 1),
    'initial_usb': ('SKIP_INITIAL_COM_USB', 'not-open', 0),
    'initial_zero': ('SKIP_PREWRITE_NOT_OPEN', 'not-open', 0),
    'dcp': ('SKIP_CHGTYP', 'chgtyp', 0),
    'no_vbus': ('SKIP_VBUS', 'vbus', 0),
    'cc_source': ('SKIP_CC', 'cc', 0),
    'early_enum': ('ENUMERATED_BEFORE_WRITE', 'udc-left', 0),
    'dwell_change': ('SKIP_STATUS_CHANGED', 'status-changed', 0),
    'no_identity': ('NO_PROOF_IDENTITY_MISMATCH', 'pending', 0),
    'fast_replug': ('ROUTE_CONFIGURED_AFTER_REPLUG', 'written', 1),
    'gap_replug': ('ROUTE_COVERAGE_GAP', 'written', 1),
    'preread_change': ('SKIP_STATUS_CHANGED', 'status-changed', 0),
    'deferred': ('ROUTE_CONFIGURED_AFTER_REPLUG', 'written', 1),
    'revert': ('ROUTE_WRITE_NOT_HELD', 'written', 1),
    'gap_departure': ('ENUMERATED_BEFORE_WRITE', 'udc-left', 0),
    'latched_replug': ('ROUTE_AMBIGUOUS_ORDER', 'written', 1),
    'udc_during_gate': ('ENUMERATED_BEFORE_WRITE', 'udc-left', 0),
    'slow_gate': ('SKIP_STALE', 'stale', 0),
    'status1_only': ('ROUTE_AMBIGUOUS_ORDER', 'written', 1),
    'begin_edge': ('SKIP_STATUS_CHANGED', 'status-changed', 0),
    'gap_status': ('SKIP_STATUS_CHANGED', 'status-changed', 0),
    'blind_gap': ('SKIP_STATUS_CHANGED', 'status-changed', 0),
    'skip_then_edge': ('SKIP_INITIAL_COM_USB', 'not-open', 0),
    'split_session': ('ROUTE_NO_READBACK', 'written', 1),
    'late_default': ('ROUTE_NO_ENUMERATION', 'written', 1),
}


class Producer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.exe = Path(cls.tmp.name) / 'fake'
        subprocess.run(['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-O1', '-I', str(SOURCE),
                        str(SOURCE / 'max77705_route_fake.c'), '-o', str(cls.exe)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def run_fake(cls, scenario):
        out = subprocess.run([str(cls.exe), scenario], capture_output=True, text=True, check=True).stdout
        lines = out.splitlines()
        return dict(kv.split('=') for kv in lines[0].split()), bytes.fromhex(lines[1])


class ProducerTests(Producer):
    def test_every_scenario_verdict_and_write_count(self):
        for scenario, (verdict, gate, writes) in EXPECTED.items():
            with self.subTest(scenario=scenario):
                meta, raw = self.run_fake(scenario)
                d = rec.decode(raw)
                self.assertEqual(meta['bad_writes'], '0')
                self.assertEqual(int(meta['route_bus_writes']), writes)
                self.assertEqual(d['route_writes'], writes)
                self.assertEqual(d['gate'], gate)
                self.assertEqual(rec.verdict(d), verdict)

    def test_pass_timeline(self):
        _, raw = self.run_fake('pass')
        d = rec.decode(raw)
        kinds = [e['kind'] for e in d['events']]
        self.assertEqual(kinds, ['begin', 'udc', 'prewrite', 'write', 'udc', 'udc', 'readback', 'request'])
        self.assertGreaterEqual(d['write_ms'] - d['dwell_start_ms'], 3000)
        self.assertEqual(d['write_echo'], 0x06)
        write = d['events'][3]
        self.assertEqual((write['written'], write['udc']), (0x09, 'not attached'))
        self.assertEqual(d['events'][-1]['udc'], 'configured')
        self.assertEqual(d['events'][-1]['ctrl1'], 0x09)

    def test_failed_write_is_never_retried(self):
        meta, raw = self.run_fake('write_timeout')
        d = rec.decode(raw)
        self.assertEqual(meta['route_bus_writes'], '1')
        self.assertEqual(sum(e['kind'] == 'write' for e in d['events']), 1)
        self.assertEqual(d['write_status'], 'timeout')

    def test_deferred_read_follows_a_skipped_event(self):
        # Cable out and back in 400 ms apart: the second change falls inside the
        # command spacing, so it is recorded unread and a deferred read follows.
        _, raw = self.run_fake('deferred')
        d = rec.decode(raw)
        after = [e['kind'] for e in d['events'] if e['t_ms'] >= 45000]
        self.assertEqual(after[:2], ['on-event', 'status'])
        self.assertIn('deferred', after[2:4])

    def test_preread_change_blocks_the_write(self):
        meta, raw = self.run_fake('preread_change')
        d = rec.decode(raw)
        self.assertEqual(meta['route_bus_writes'], '0')
        self.assertEqual(d['prewrite_ctrl1'], 0x3f)

    def test_failed_status_read_keeps_flags_and_is_not_a_pass(self):
        _, raw = self.run_fake('gap_replug')
        d = rec.decode(raw)
        gaps = [e for e in d['events'] if e['kind'] == 'gap']
        self.assertTrue(gaps and any('VBUSDetI' in e['uic_bits'] for e in gaps))

    def test_write_allowlist(self):
        out = subprocess.run([str(self.exe), 'write_probe'], capture_output=True, text=True,
                             check=True).stdout.strip()
        # 5 disallowed single writes + an ungated route write rejected; one gated write; a repeat rejected.
        self.assertEqual(out, 'rejected=11111101 bus_writes=1 writes_rejected=7 route_writes=1')

    def test_command_budget_and_ring(self):
        meta, raw = self.run_fake('flood')
        d = rec.decode(raw)
        self.assertLessEqual(int(meta['commands']), 32)
        self.assertEqual(meta['route_bus_writes'], '0')
        self.assertGreater(d['events_total'], 48)
        times = [e['t_ms'] for e in d['events']]
        self.assertEqual(times, sorted(times))

    def test_source_write_sites(self):
        text = (SOURCE / 'max77705-usb-route.h').read_text()
        calls = re.findall(r'mx_write\(MX_USBC_ADDR, (\w+), (\w+)\)', text)
        self.assertEqual(sorted(set(calls)), [('MX_AP_DATAOUT0', 'MX_CTRL1_READ'),
                                              ('MX_AP_DATAOUT_END', '0x00')])
        # definition + the single-byte allowlisted call + the one route write
        self.assertEqual(text.count('mx_raw_write('), 3)
        self.assertEqual(text.count('mx_write_route()'), 2)  # definition + one call in mx_route()
        self.assertIn('{ MX_AP_DATAOUT0, MX_CTRL1_WRITE, MX_COM_USB }', text)
        self.assertNotIn('I2C_SLAVE', text)
        self.assertNotRegex(text, r'mx_raw_write\(MX_(PMIC|FSA)_ADDR')


class RequestOrderTests(Producer):
    def test_request_must_be_final(self):
        # Codex review r2: relabel a pre-replug periodic event as a configured
        # request and the real request as periodic; the decoder must refuse.
        _, raw = self.run_fake('nofix')
        d = rec.decode(raw)
        kinds = [e['kind'] for e in d['events']]
        last_periodic = max(i for i, k in enumerate(kinds) if k == 'periodic')
        request = kinds.index('request')
        out = bytearray(raw)
        out[rec.HEADER + last_periodic * rec.EVENT + 4] = rec.KIND.index('request')
        out[rec.HEADER + last_periodic * rec.EVENT + 12] = 8
        out[rec.HEADER + request * rec.EVENT + 4] = rec.KIND.index('periodic')
        with self.assertRaises(ValueError):
            rec.decode(bytes(out))


class WriteUdcTests(Producer):
    def test_write_events_require_not_attached(self):
        # Codex review r3: mark the pre-replug samples, including the write,
        # "configured"; the decoder must refuse rather than return PASS.
        _, raw = self.run_fake('nofix')
        d = rec.decode(raw)
        out = bytearray(raw)
        for i, e in enumerate(d['events']):
            if 0 < i and e['t_ms'] < 45000:
                out[rec.HEADER + i * rec.EVENT + 12] = 8
        with self.assertRaises(ValueError):
            rec.decode(bytes(out))
        write = next(i for i, e in enumerate(d['events']) if e['kind'] == 'write')
        out = bytearray(raw)
        for i in range(write - 1, len(d['events'])):
            if d['events'][i]['t_ms'] < 45000:
                out[rec.HEADER + i * rec.EVENT + 12] = 8
        with self.assertRaisesRegex(ValueError, 'not-attached|without its udc event'):
            rec.decode(bytes(out))


class ChangeEventTests(Producer):
    def test_change_event_needs_a_change(self):
        # Codex review r4: zero the flags of the post-write status event of
        # latched_replug; with unchanged status the producer cannot emit it.
        _, raw = self.run_fake('latched_replug')
        d = rec.decode(raw)
        slot = next(i for i, e in enumerate(d['events'])
                    if e['kind'] in ('on-event', 'status') and e['t_ms'] > d['write_ms'])
        out = bytearray(raw)
        out[rec.HEADER + slot * rec.EVENT + 5] = 0
        out[rec.HEADER + slot * rec.EVENT + 6] = 0
        with self.assertRaisesRegex(ValueError, 'change event without a change'):
            rec.decode(bytes(out))
        # Codex review r5: instead fake a status change on that event; the next
        # unchanged-sample event still shows the old status, so it must fail.
        out[rec.HEADER + slot * rec.EVENT + 9] = 0x10
        with self.assertRaisesRegex(ValueError, 'status changed without a change event'):
            rec.decode(bytes(out))


class GrammarTests(Producer):
    """Codex review r7: forged transcripts in each family must be refused."""

    def slot(self, raw, pick):
        d = rec.decode(raw)
        return next(i for i, e in enumerate(d['events']) if pick(e)), d

    def test_forgeries_are_refused(self):
        _, nofix = self.run_fake('nofix')
        _, revert = self.run_fake('revert')
        _, latched = self.run_fake('latched_replug')
        cases = []
        # mailbox encoding: an answered read without APCmdResI
        i, _ = self.slot(nofix, lambda e: e['kind'] == 'on-event')
        cases.append(('response flag', edit(nofix, rec.HEADER + i * rec.EVENT + 5,
                                            rec.decode(nofix)['events'][i]['uic'] & 0x7f)))
        # failed read hiding its value: request result -> io, value kept
        i, _ = self.slot(revert, lambda e: e['kind'] == 'request')
        cases.append(('failed read carries a value', edit(revert, rec.HEADER + i * rec.EVENT + 11, 3)))
        # orphan deferred after relabelling the physical event as udc
        i, d = self.slot(latched, lambda e: e['kind'] in ('on-event', 'status') and e['t_ms'] > 0)
        forged = bytearray(latched)
        forged[rec.HEADER + i * rec.EVENT + 4] = rec.KIND.index('udc')
        forged[rec.HEADER + i * rec.EVENT + 5] = 0
        forged[rec.HEADER + i * rec.EVENT + 6] = 0
        forged[rec.HEADER + i * rec.EVENT + 11] = 4
        cases.append(('', bytes(forged)))
        # terminal closure: hide the final request by decrementing the counts
        d = rec.decode(revert)
        hidden = bytearray(revert)
        hidden[28] = d['events_total'] - 1
        hidden[32] = d['commands'] - 1
        cases.append(('', bytes(hidden)))
        # write admission: prewrite turned into a periodic read of 0x09
        i, _ = self.slot(nofix, lambda e: e['kind'] == 'prewrite')
        cases.append(('', edit(nofix, rec.HEADER + i * rec.EVENT + 4, rec.KIND.index('periodic'))))
        for want, raw in cases:
            with self.subTest(want=want), self.assertRaisesRegex(ValueError, want):
                rec.decode(raw)


class WireTests(Producer):
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
        spec = importlib.util.spec_from_file_location('mxr_' + d.name, d / 'max77705_verify.py')
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
        self.assertEqual(BODY, 352 + 832)
        for board in (False, True):
            _, _, d = self.profile(board)
            (d / 'seal.h').write_text(SEAL)
            flags = ['-DCANARY_DEBIAN_RAM'] + ([] if board else ['-DCANARY_H0_VM'])
            r = subprocess.run(['aarch64-linux-gnu-gcc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                                '-Wno-unused-function', '-Wno-unused-const-variable', '-fsyntax-only', *flags,
                                '-I', str(d), '-I', str(ROOT / 'workspace/public/src/native-init'), str(d / 'init.c')],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])
            wrong = ['-DCANARY_DEBIAN_RAM'] + (['-DCANARY_H0_VM'] if board else [])
            r = subprocess.run(['aarch64-linux-gnu-gcc', '-fsyntax-only', *wrong, '-I', str(d),
                                '-I', str(ROOT / 'workspace/public/src/native-init'), str(d / 'init.c')],
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            init = (d / 'init.c').read_text()
            self.assertEqual(init.count('mx_final();'), 1)
            self.assertIn('mx_final();\n    mx_fill(response+352);', init)

    def test_producer_records_verify_signed(self):
        v, manifest, d = self.profile()
        source = (d / 'max77705_verify.py').read_bytes()
        (d / 'max77705_route_record.py').unlink()    # the decoder is embedded in the verifier
        namespace = {'__name__': 'pinned_route_decoder'}
        exec(compile(source, '<pinned>', 'exec'), namespace)
        for scenario in ('pass', 'nofix', 'initial_usb', 'no_identity'):
            with self.subTest(scenario=scenario):
                _, raw = self.run_fake(scenario)
                self.raw.write_bytes(self.response(v, manifest, raw))
                result = namespace['verify'](self.raw, manifest, self.nonce, vm=True)
                self.assertEqual(result['status'], 'AUTHENTICATED_H0_MAX77705_ROUTE_OBSERVATION')
                self.assertEqual(result['subject'], 'max77705-route')
                self.assertEqual(result['max77705_verdict'], EXPECTED[scenario][0])

    def test_tamper_is_rejected(self):
        v, manifest, _ = self.profile()
        _, raw = self.run_fake('nofix')
        resp = self.response(v, manifest, raw)
        resp[352 + 40] = 2                       # gate: written -> udc-left
        self.raw.write_bytes(resp)
        with self.assertRaisesRegex(ValueError, 'response HMAC'):
            v.verify(self.raw, manifest, self.nonce, vm=True)


def edit(raw, offset, value):
    out = bytearray(raw)
    out[offset] = value
    return bytes(out)


class DecoderTests(Producer):
    def test_impossible_records_are_rejected(self):
        _, ok = self.run_fake('pass')
        events = rec.decode(ok)['events']
        write_slot = next(i for i, e in enumerate(events) if e['kind'] == 'write')
        base = rec.HEADER + write_slot * rec.EVENT
        cases = {
            'disallowed write': edit(ok, 34, 1),
            'more than one route write': edit(ok, 35, 2),
            'gate and route write count disagree': edit(edit(ok, 40, 4), 35, 1),
            'route write value differs': edit(ok, base + 10, 0x3f),
            'without its preconditions': edit(ok, 41, 0x09),
            'without its echo': edit(ok, 43, 0),
            'route record header': edit(ok, 40, 12),
            'reserved bytes': edit(ok, 60, 1),
            'route event field': edit(ok, base + 14, 1),
        }
        for want, raw in cases.items():
            with self.subTest(want=want), self.assertRaisesRegex(ValueError, want):
                rec.decode(raw)

    def test_write_fields_without_write_are_rejected(self):
        _, skipped = self.run_fake('initial_usb')
        for offset, value in ((43, 0x06), (44, 0x09), (48, 1)):
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, 'without a written gate'):
                rec.decode(edit(skipped, offset, value))

    def test_udc_state_cannot_change_without_its_event(self):
        # Codex review r1: flipping only the readback's UDC byte must not turn
        # NO_FIX into PASS; the producer always emits a udc event first.
        _, raw = self.run_fake('nofix')
        d = rec.decode(raw)
        slot = next(i for i, e in enumerate(d['events']) if e['kind'] == 'readback')
        with self.assertRaisesRegex(ValueError, 'without its udc event'):
            rec.decode(edit(raw, rec.HEADER + slot * rec.EVENT + 12, 8))
        _, raw = self.run_fake('pass')
        d = rec.decode(raw)
        slot = next(i for i, e in enumerate(d['events']) if e['kind'] == 'udc' and e['udc'] == 'default')
        with self.assertRaisesRegex(ValueError, 'carries interrupt flags'):
            rec.decode(edit(raw, rec.HEADER + slot * rec.EVENT + 5, 0x20))


if __name__ == '__main__':
    unittest.main()
