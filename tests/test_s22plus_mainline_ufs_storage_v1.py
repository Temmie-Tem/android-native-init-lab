"""Phase 2a: the actual read-only UTP storage stage against a host device model."""
from pathlib import Path
from unittest import mock
import hashlib
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'workspace/public/src/mainline/s22plus_ufs_link_h0'
sys.path.insert(0, str(SOURCE))
import link_wire as wire  # noqa: E402
import report_modes  # noqa: E402

TEST_LBA, NATIVE_LAST, LAST_USABLE, LAST_LBA = 62305152, 62305023, 62305270, 62305279
RETAINED = ROOT / ('workspace/private/outputs/s22plus-native-android32-gpt-proposal-h0-20260916-1/'
                   'primary-six-proposed.bin')
HEADERS = ('linux/types.h', 'linux/delay.h', 'linux/device.h', 'linux/dma-mapping.h', 'linux/io.h',
           'linux/kernel.h', 'linux/minmax.h', 'linux/ktime.h', 'linux/string.h', 'linux/unaligned.h',
           'linux/iommu.h', 'linux/reset.h', 'crypto/sha2.h', 'ufs/ufshci.h')
DONE_FLAGS = 0b11111101111
STEP = {name: i for i, name in enumerate(wire.STORAGE_STEPS)}


def gpt(cover_test_lba=False):
    """LBAs 1-3 with the live Android32 geometry: header, then 44 entries."""
    header = bytearray(4096)
    header[:8] = b'EFI PART'
    struct.pack_into('<QQQQ', header, 24, 1, LAST_LBA, 6, LAST_USABLE)
    struct.pack_into('<QII', header, 72, 2, 44, 128)
    entries = bytearray(8192)
    extents = [(264 + 8 * i, 271 + 8 * i) for i in range(39)] + [(3726848, 12115455),
                                                                   (12115456, NATIVE_LAST)]
    if cover_test_lba:
        extents[-1] = (12115456, TEST_LBA)
    for i, (first, last) in enumerate(extents):
        entry = struct.pack('<16s16sQQ', bytes([i + 1]) * 16, bytes([0x80 | i]) * 16, first, last)
        entries[i * 128:i * 128 + len(entry)] = entry
    return bytes(header + entries)


def values_word(values):
    return values[7]


def c_digest(data):
    return '"' + ''.join(f'\\x{b:02x}' for b in hashlib.sha256(data).digest()) + '"'


class StorageStageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        out = Path(cls.tmp.name)
        for header in HEADERS:
            (out / header).parent.mkdir(parents=True, exist_ok=True)
            (out / header).touch()
        (out / 'linux/errno.h').write_text('#include_next <linux/errno.h>\n')
        cls.files = {}
        for name, data in (('gpt', gpt()), ('covered', gpt(cover_test_lba=True)),
                           ('zero', bytes(4096)), ('pattern', bytes(range(256)) * 16)):
            cls.files[name] = out / f'{name}.bin'
            cls.files[name].write_bytes(data)
        cls.exe = {}
        for name, table in (('gpt', gpt()), ('covered', gpt(cover_test_lba=True))):
            (out / f'{name}.h').write_text(f'#define G0Q_GPT_SHA256 {c_digest(table)}\n')
            cls.exe[name] = out / f'fixture-{name}'
            subprocess.run(['cc', '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-Wno-unused-function', '-include', str(out / f'{name}.h'),
                            '-I', str(out), '-I', str(SOURCE), str(ROOT / 'tests/s22plus_ufs_storage_fixture.c'),
                            '-o', str(cls.exe[name])], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_case(self, case, *, table='gpt', block='zero', exe='gpt'):
        done = subprocess.run([str(self.exe[exe]), case, str(self.files[table]), str(self.files[block])],
                              check=True, capture_output=True, text=True)
        fields, counts, trace = done.stdout.splitlines()
        values = [int(v) for v in fields.split()]
        commands, allocations, doorbell, started = map(int, counts.split())
        self.started = bool(started)
        return values, commands, allocations, doorbell, trace

    def decode(self, values, table=None):
        # The fixture's synthetic table stands in for the pinned live GPT.
        word = int.from_bytes(hashlib.sha256(table or gpt()).digest()[:4], 'big')
        with mock.patch.object(wire, 'STORAGE_GPT_WORD', word):
            return wire.storage_read([0] * 38 + values, link_completed=True)['storage']

    def test_complete_read_only_sequence_of_a_zero_block(self):
        values, commands, allocations, doorbell, trace = self.run_case('ok')
        self.assertEqual(trace, 'NOP;SETFLAG;READFLAG;READFLAG;READFLAG;TUR;TUR;CAPACITY;'
                                'READ 1+3;READ 62305152+1;')
        rc, step, flags, polls = values[:4]
        self.assertEqual((rc, step, polls, doorbell, allocations), (0, 10, 3, 0, 3))
        self.assertEqual(flags, DONE_FLAGS | 1 << 4 | 1 << 11)
        self.assertEqual(values[6], LAST_LBA)
        self.assertEqual(values[7], int.from_bytes(hashlib.sha256(gpt()).digest()[:4], 'big'))
        facts = self.decode(values)
        self.assertTrue(facts['completed'] and facts['block_zero'] and facts['gpt_match'] and facts['range_ok'])
        self.assertEqual(facts['block_sha256'], hashlib.sha256(bytes(4096)).hexdigest())
        self.assertEqual(facts['sense'], dict(key=6, asc=0x29, ascq=0))

    def test_block_digest_is_the_full_sha256(self):
        values, *_ = self.run_case('no-ua', block='pattern')
        facts = self.decode(values)
        self.assertEqual(facts['block_sha256'], hashlib.sha256(bytes(range(256)) * 16).hexdigest())
        self.assertFalse(facts['block_zero'])
        self.assertNotIn('UNIT_ATTENTION', facts['flags'])

    def test_gpt_mismatch_stops_before_the_test_block(self):
        values, _, _, _, trace = self.run_case('ok', table='covered')
        self.assertEqual((values[0], values[1]), (-6, STEP['GPT']))     # -ENXIO
        self.assertNotIn('READ 62305152', trace)
        facts = self.decode(values)
        self.assertFalse(facts['gpt_match'] or facts['range_ok'])
        self.assertIsNone(facts['block_sha256'])

    def test_an_entry_covering_the_test_block_fails_the_range_check(self):
        # The table digest matches here, so only the parsed range can refuse.
        values, _, _, _, trace = self.run_case('ok', table='covered', exe='covered')
        facts = self.decode(values, gpt(cover_test_lba=True))
        self.assertTrue(facts['gpt_match'])
        self.assertFalse(facts['range_ok'])
        self.assertEqual(values[0], -6)
        self.assertNotIn('READ 62305152', trace)

    def test_wrong_capacity_stops(self):
        values, _, _, _, trace = self.run_case('capacity')
        self.assertEqual((values[0], values[1]), (-34, STEP['CAPACITY']))  # -ERANGE
        self.assertNotIn('READ 1+3', trace)

    def test_unanswered_command_is_uncertain_and_never_reused(self):
        values, commands, _, doorbell, trace = self.run_case('timeout-nop')
        self.assertEqual((values[0], values[1], commands, doorbell, trace), (-110, STEP['NOP'], 1, 1, 'NOP;'))
        self.assertIn('UNCERTAIN', self.decode(values)['flags'])

    def test_device_init_that_never_clears_times_out_without_an_uncertain_slot(self):
        values, _, _, doorbell, trace = self.run_case('init-stuck')
        self.assertEqual((values[0], values[1], doorbell), (-110, STEP['INIT_POLL'], 0))
        self.assertNotIn('UNCERTAIN', self.decode(values)['flags'])
        self.assertNotIn('TUR', trace)

    def test_transfer_error_status_stops(self):
        values, *_ = self.run_case('ocs')
        self.assertEqual((values[0], values[1]), (-5, STEP['GPT']))        # -EIO
        self.assertEqual(self.decode(values)['last_status']['ocs'], 2)

    def test_only_one_unit_attention_is_repeated(self):
        values, _, _, _, trace = self.run_case('tur-not-ready')
        self.assertEqual((values[0], values[1]), (-11, STEP['TUR']))      # -EAGAIN
        self.assertEqual(trace.count('TUR'), 1)
        self.assertEqual(self.decode(values)['sense'], dict(key=2, asc=4, ascq=0))

    def test_good_status_without_every_byte_is_refused(self):
        for case in ('short-read', 'underflow'):
            with self.subTest(case=case):
                values, *_ = self.run_case(case)
                self.assertEqual((values[0], values[1]), (-61, STEP['BLOCK']))   # -ENODATA
                facts = self.decode(values)
                self.assertIsNone(facts['block_sha256'])
                self.assertFalse(facts['block_zero'])

    def test_sense_outside_the_declared_segment_is_not_a_unit_attention(self):
        values, _, _, _, trace = self.run_case('ua-no-segment')
        self.assertEqual((values[0], values[1], values[4]), (-11, STEP['TUR'], 0))   # -EAGAIN, no sense
        self.assertEqual(trace.count('TUR'), 1)

    def test_a_response_with_an_extra_header_is_refused(self):
        values, _, _, _, trace = self.run_case('ehs')
        self.assertEqual((values[0], values[1], values[4]), (-71, STEP['TUR'], 0))   # -EPROTO
        self.assertEqual(trace.count('TUR'), 1)

    def test_fixed_sense_asc_needs_its_additional_length(self):
        # Key 6 is inside the 8-byte record; ASC/ASCQ beyond it are not reported.
        values, _, _, _, trace = self.run_case('short-additional')
        self.assertEqual(values[0], 0)
        self.assertEqual(trace.count('TUR'), 2)
        self.assertEqual(self.decode(values)['sense'], dict(key=6, asc=0, ascq=0))

    def test_descriptor_format_unit_attention_is_repeated_once(self):
        values, _, _, _, trace = self.run_case('descriptor-ua')
        self.assertEqual(values[0], 0)
        self.assertEqual(trace.count('TUR'), 2)
        self.assertEqual(self.decode(values)['sense'], dict(key=6, asc=0x29, ascq=0))

    def test_the_list_is_stopped_and_the_host_reset_on_shutdown(self):
        for case in ('ok', 'timeout-nop'):   # the fixture asserts the list stop and HCE rule
            with self.subTest(case=case):
                self.run_case(case)
                self.assertTrue(self.started)

    def test_an_unstoppable_slot_parks_shutdown(self):
        # An outstanding slot with HCE never clearing parks with the reset held (status 77).
        done = subprocess.run([str(self.exe['gpt']), 'hce-stuck-timeout', str(self.files['gpt']),
                               str(self.files['zero'])], capture_output=True)
        self.assertEqual(done.returncode, 77)

    def test_the_decoder_binds_gpt_and_zero_flags_to_their_digests(self):
        good, *_ = self.run_case('ok')
        self.decode(good)
        with self.assertRaisesRegex(ValueError, 'GPT match with another table digest'):
            wire.storage_read([0] * 38 + good, link_completed=True)   # real pin, synthetic table
        pattern, *_ = self.run_case('ok', block='pattern')
        forged = list(pattern)
        forged[2] |= 1 << 11
        with self.assertRaisesRegex(ValueError, 'zero flag and block digest disagree'):
            self.decode(forged)
        unflagged = list(good)
        unflagged[2] &= ~(1 << 11)
        with self.assertRaisesRegex(ValueError, 'zero flag and block digest disagree'):
            self.decode(unflagged)
        uncertain = list(good)
        uncertain[0], uncertain[1], uncertain[2] = -110, 9, uncertain[2] | 1 << 12
        with self.assertRaisesRegex(ValueError, 'uncertain slot with the current step completed|storage flags and step disagree'):
            self.decode(uncertain)
        early = [-110, 2, 1 << 12] + [0] * 13
        with self.assertRaisesRegex(ValueError, 'uncertain slot without a command step|storage flags and step disagree'):
            self.decode(early)
        ran_gpt = DONE_FLAGS & ~(1 << 10)
        for case, message in (
                ([-6, 8, ran_gpt, 3, 0, 0x21 << 24, LAST_LBA, values_word(good)] + [0] * 8,
                 'storage flags and step disagree'),
                ([-110, 9, ran_gpt, 3, 0, 0x21 << 24, LAST_LBA - 1, values_word(good)] + [0] * 8,
                 'capacity outside its step'),
                ([-110, 5, 7 | 1 << 12, 0, 0, 0x36 << 24, 0, 0] + [0] * 8, 'uncertain poll without a poll'),
                ([-6, 8, ran_gpt & ~(1 << 9), 3, 0, 0x21000002, LAST_LBA, values_word(good)] + [0] * 8,
                 'GPT read evidence without a GOOD read'),
                ([-5, 7, 0b101111, 3, 0, 0x21000002, LAST_LBA, 0] + [0] * 8,
                 'capacity value without a GOOD capacity read'),
                (good[:4] + [2 << 16 | 0x0400] + good[5:],
                 'unit attention with another sense key|unit attention sense replaced')):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.decode(case)
        # A later CHECK CONDITION may overwrite the initial UNIT ATTENTION's sense.
        with self.assertRaisesRegex(ValueError, 'sense without a CHECK CONDITION'):
            self.decode([-5, 8, 0b1101111, 3, 6 << 16 | 0x2900, 0x21000002, LAST_LBA, 0] + [0] * 8)
        later = [-11, 7, 0b111111, 3, 2 << 16 | 0x0400, 0x21020000, 0, 0] + [0] * 8
        self.assertEqual(self.decode(later)['sense']['key'], 2)
        stale = list(good)
        stale[0], stale[1] = -110, 9
        stale[2] &= ~(1 << 12)
        with self.assertRaisesRegex(ValueError, 'block evidence before the stage ended|storage flags and step disagree'):
            self.decode(stale)

    def test_no_dma_without_the_device_smmu_mapping(self):
        values, commands, allocations, _, _ = self.run_case('no-iommu')
        self.assertEqual((values[0], values[1], commands, allocations, self.started),
                         (-19, STEP['ADMIT'], 0, 0, False))                    # -ENODEV

    def test_a_budget_too_short_for_the_stage_touches_nothing(self):
        values, commands, allocations, _, _ = self.run_case('short-budget')
        self.assertEqual((values[0], commands, allocations, self.started), (-110, 0, 0, False))

    def test_admission_refusals_touch_nothing(self):
        for case in ('link-failed', 'list-running', 'host-error'):
            with self.subTest(case=case):
                values, commands, allocations, _, trace = self.run_case(case)
                self.assertEqual((values[0], values[1], commands, allocations, trace),
                                 (-16, STEP['ADMIT'], 0, 0, ''))           # -EBUSY

    def test_wire_rejects_storage_fields_without_a_completed_link(self):
        self.assertEqual(wire.storage_read([0] * 54, link_completed=False), dict(storage=None))
        with self.assertRaisesRegex(ValueError, 'storage stage without a completed link'):
            wire.storage_read([0] * 38 + [0, 1] + [0] * 14, link_completed=False)

    def test_wire_rejects_inconsistent_storage_fields(self):
        good, *_ = self.run_case('ok')
        bad = [list(good) for _ in range(7)]
        bad[0][1] = 9                         # rc 0 but not done
        bad[1][2] &= ~(1 << 5)                # a skipped step flag
        bad[2][2] |= 1 << 12                  # uncertain without a timeout
        bad[3][6] = LAST_LBA - 1              # wrong capacity on success
        bad[4][5] = 0x0f                      # success with an invalid terminal OCS
        bad[5][3] = 0                         # device init cleared without a poll
        bad[6][8:16] = [0] * 8                # success without a block digest
        for values in bad:
            with self.subTest(values=values[:8]), self.assertRaises(ValueError):
                self.decode(values)

    def test_v14_envelope_and_fields(self):
        self.assertEqual(report_modes.FIELDS[14], 54)
        self.assertEqual(wire.result_size(14) - wire.result_size(13), 256)

    @unittest.skipUnless(RETAINED.exists(), 'retained live GPT not present')
    def test_compiled_digest_is_the_retained_live_gpt(self):
        header = (SOURCE / 'ufs_storage.h').read_text()
        expected = hashlib.sha256(RETAINED.read_bytes()[4096:4 * 4096]).digest()
        self.assertIn(''.join(f'\\x{b:02x}' for b in expected[:16]), header)
        self.assertIn(''.join(f'\\x{b:02x}' for b in expected[16:]), header)


if __name__ == '__main__':
    unittest.main()
