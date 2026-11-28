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


class StorageHeaderStageTest(unittest.TestCase):
    """V15: the same stage with the response-header word and an unparsed-sense repeat."""
    UNPARSED, REPEAT = 1 << 13, 1 << 14
    DEFINES = ('-DG0Q_STORAGE_HEADER',)
    DECODE = dict(header=True)

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        out = Path(cls.tmp.name)
        for header in HEADERS:
            (out / header).parent.mkdir(parents=True, exist_ok=True)
            (out / header).touch()
        (out / 'linux/errno.h').write_text('#include_next <linux/errno.h>\n')
        cls.table, cls.block = out / 'gpt.bin', out / 'zero.bin'
        cls.table.write_bytes(gpt())
        cls.block.write_bytes(bytes(4096))
        (out / 'gpt.h').write_text(f'#define G0Q_GPT_SHA256 {c_digest(gpt())}\n')
        cls.exe = out / 'fixture-v15'
        subprocess.run(['cc', '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                        *cls.DEFINES, '-include', str(out / 'gpt.h'), '-I', str(out), '-I', str(SOURCE),
                        str(ROOT / 'tests/s22plus_ufs_storage_fixture.c'), '-o', str(cls.exe)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_case(self, case):
        done = subprocess.run([str(self.exe), case, str(self.table), str(self.block)],
                              check=True, capture_output=True, text=True)
        fields, _, trace = done.stdout.splitlines()
        values = [int(v) for v in fields.split()]
        self.assertEqual(len(values), 17)
        return values, trace

    def decode(self, values):
        word = int.from_bytes(hashlib.sha256(gpt()).digest()[:4], 'big')
        with mock.patch.object(wire, 'STORAGE_GPT_WORD', word):
            return wire.storage_read([0] * 38 + values, link_completed=True, **self.DECODE)['storage']

    def test_parsed_unit_attention_is_repeated_and_the_header_word_reported(self):
        values, trace = self.run_case('ok')
        self.assertEqual((values[0], values[1], trace.count('TUR')), (0, 10, 2))
        self.assertEqual(values[2], DONE_FLAGS | 1 << 4 | 1 << 11 | self.REPEAT)
        facts = self.decode(values)
        self.assertEqual(facts['response_header'], dict(raw=0, ehs_length=0, device_information=0,
                                                        data_segment_length=0))
        self.assertEqual(facts['sense'], dict(key=6, asc=0x29, ascq=0))

    def test_check_condition_with_an_extra_header_is_repeated_unparsed(self):
        # ML057's device answer: CHECK CONDITION with a nonzero Total EHS Length.
        values, trace = self.run_case('ehs')
        self.assertEqual((values[0], values[1], values[4], trace.count('TUR')), (0, 10, 0, 2))
        self.assertEqual(values[2], DONE_FLAGS | 1 << 11 | self.UNPARSED | self.REPEAT)
        facts = self.decode(values)
        self.assertTrue(facts['completed'])
        self.assertIn('SENSE_UNPARSED', facts['flags'])
        self.assertNotIn('UNIT_ATTENTION', facts['flags'])

    def test_a_second_check_condition_stops_with_the_header_word(self):
        values, trace = self.run_case('ehs-twice')
        self.assertEqual((values[0], values[1], values[4], trace.count('TUR')), (-11, STEP['TUR'], 0, 2))
        self.assertNotIn('CAPACITY', trace)
        self.assertEqual(values[16], 1 << 24 | 20)        # EHS 1, data segment 2 + 18 bytes
        facts = self.decode(values)
        self.assertEqual((facts['response_header']['ehs_length'],
                          facts['response_header']['data_segment_length']), (1, 20))

    def test_extra_header_on_good_responses_is_accepted(self):
        # Header fields keep their offsets; the data moves through the PRDT.
        values, trace = self.run_case('ehs-all')
        self.assertEqual((values[0], values[1]), (0, 10))
        self.assertEqual(values[16], 1 << 24)
        self.assertIn('READ 62305152+1', trace)
        self.assertIn('SENSE_UNPARSED', self.decode(values)['flags'])

    def test_a_parsed_other_sense_key_is_not_repeated(self):
        values, trace = self.run_case('tur-not-ready')
        self.assertEqual((values[0], values[1], trace.count('TUR')), (-11, STEP['TUR'], 1))
        self.assertFalse(values[2] & (self.UNPARSED | self.REPEAT))
        self.assertEqual(self.decode(values)['sense'], dict(key=2, asc=4, ascq=0))

    def test_extra_header_bytes_are_never_read_as_sense(self):
        # The legacy sense place holds 0xff (EHS bytes); the outcome equals the clean case.
        garbage, trace = self.run_case('ehs-garbage')
        clean, _ = self.run_case('ehs')
        self.assertEqual(garbage, clean)
        self.assertEqual(trace.count('TUR'), 2)

    def test_a_malformed_reply_keeps_its_header_word(self):
        # ring() records both words before the type check; -EPROTO, status 0, header set.
        values, trace = self.run_case('nop-bad-ehs')
        self.assertEqual((values[0], values[1], values[5], values[16]), (-71, STEP['NOP'], 0, 1 << 24))
        self.assertEqual(trace, 'NOP;')
        self.assertEqual(self.decode(values)['response_header']['ehs_length'], 1)

    def test_an_unparsed_stop_after_a_parsed_unit_attention(self):
        values, trace = self.run_case('ehs-capacity')
        self.assertEqual((values[0], values[1], values[4]), (-11, STEP['CAPACITY'], 0))
        self.assertEqual(values[2] & (1 << 4 | self.UNPARSED | self.REPEAT), 1 << 4 | self.UNPARSED | self.REPEAT)
        self.assertEqual(values[16] >> 24, 1)
        self.assertNotIn('READ 1+3', trace)
        self.decode(values)

    def test_decoder_binds_the_v15_flags(self):
        ok, _ = self.run_case('ok')
        unparsed, _ = self.run_case('ehs')
        stop, _ = self.run_case('ehs-twice')
        capacity, _ = self.run_case('ehs-capacity')
        good = 0x21 << 24
        for values, message in (
                (ok[:2] + [ok[2] & ~self.REPEAT] + ok[3:], 'unit attention without the repeat'),
                (unparsed[:2] + [unparsed[2] & ~self.UNPARSED] + unparsed[3:], 'repeat without its CHECK CONDITION'),
                # A completed stage cannot carry a parsed UNIT ATTENTION and an unparsed CHECK CONDITION.
                (ok[:2] + [ok[2] | self.UNPARSED] + ok[3:], 'unparsed sense without its stop'),
                # A first unparsed TUR always repeats.
                (stop[:2] + [stop[2] & ~self.REPEAT] + stop[3:], 'unparsed TUR without the repeat'),
                # The terminal unparsed CHECK CONDITION needs its status, extra header and zero sense.
                (capacity[:5] + [good] + capacity[6:], 'CHECK CONDITION stop with another status'),
                (capacity[:16] + [20], 'unparsed flag with a parsed stop'),
                (stop[:4] + [6 << 16] + stop[5:], 'unparsed stop with a parsed sense'),
                ([-110, 2, 0] + [0] * 13 + [5], 'response header before the first command'),
                # Round 2: stops bound to SCSI steps and to their own CHECK CONDITION.
                ([-71] + unparsed[1:2] + [unparsed[2] & ~(self.UNPARSED | self.REPEAT | 1 << 5 | 1 << 6 | 1 << 7 |
                  1 << 8 | 1 << 9 | 1 << 10 | 1 << 11)] + [3, 0, 0x21020000, 0, 0] + [0] * 8 + [1 << 24 | 20],
                 'storage step and rc disagree|protocol refusal of a well-formed reply'),
                ([-11, STEP['NOP'], 1, 0, 0, 0x21020000, 0, 0] + [0] * 8 + [20],
                 'CHECK CONDITION stop outside a SCSI step|storage flags'),
                (stop[:2] + [stop[2] & ~(self.UNPARSED | self.REPEAT)] + stop[3:4] + [6 << 16 | 0x2900] + stop[5:16] + [20],
                 'unit attention stop without the repeat'),
                (stop[:4] + [2 << 16] + stop[5:16] + [0], 'parsed sense without its data segment|unparsed flag'),
                # Round 2: a refused or uncertain command keeps the previous exchange's sample.
                ([-110, STEP['NOP'], 1 | 1 << 12, 0, 0, 0, 0, 0] + [0] * 8 + [1 << 24],
                 'response sample before NOP OUT completed'),
                ([-110, STEP['TUR'], 0b1111 | 1 << 12 | self.UNPARSED | self.REPEAT, 3, 0, 0x21000000, 0, 0] + [0] * 8 + [1 << 24 | 20],
                 'repeat sample is not the first CHECK CONDITION'),
                ([-110, STEP['TUR'], 0b1111 | 1 << 12 | self.UNPARSED | self.REPEAT, 3, 0, 0x21020000, 0, 0] + [0] * 8 + [20],
                 'repeat sample disagrees with its reason'),
                ([-16, STEP['TUR'], 0b1111 | 1 << 4 | self.REPEAT, 3, 6 << 16, 0x21020000, 0, 0] + [0] * 8 + [0],
                 'parsed unit attention without its data segment'),
                ([-110, STEP['CAPACITY'], 0b101111 | 1 << 5, 3, 0, 0x36000000, 0, 0] + [0] * 8 + [0],
                 'sample is not the previous GOOD response')):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.decode(values)
        with self.assertRaisesRegex(ValueError, 'storage field range'):
            wire.storage_read([0] * 38 + ok, link_completed=True)   # V15 flags in a V14 report
        with self.assertRaisesRegex(ValueError, 'storage stage without a completed link'):
            wire.storage_read([0] * 54 + [1], link_completed=False, header=True)

    def test_every_producer_scenario_decodes(self):
        # Completeness: each report the V15 producer emits in the device model is accepted.
        for case in ('ok', 'no-ua', 'capacity', 'timeout-nop', 'init-stuck', 'ocs', 'tur-not-ready',
                     'short-read', 'underflow', 'descriptor-ua', 'ua-no-segment', 'ehs', 'short-additional',
                     'ehs-twice', 'ehs-all', 'ehs-garbage', 'nop-bad-ehs', 'ehs-capacity', 'no-iommu',
                     'short-budget', 'host-error', 'list-running'):
            with self.subTest(case=case):
                values, _ = self.run_case(case)
                self.decode(values)

    def test_v15_envelope_and_fields(self):
        self.assertEqual(report_modes.FIELDS[15], 55)
        self.assertGreaterEqual(report_modes.LATEST, 15)
        self.assertEqual(wire.result_size(15), wire.result_size(14))
        self.assertEqual(report_modes.defines(15)[-2:], ['G0Q_STORAGE_READ', 'G0Q_STORAGE_HEADER'])


class StorageResponseStageTest(StorageHeaderStageTest):
    """V16: V15 plus response Target Failure accepted only with CHECK CONDITION."""
    DEFINES = ('-DG0Q_STORAGE_HEADER', '-DG0Q_STORAGE_RESPONSE')
    DECODE = dict(target_failure=True)
    TF = 1 << 15

    def test_target_failure_check_condition_is_parsed_and_repeated(self):
        # ML058's device answer: CHECK CONDITION, response 0x01, 18-byte UNIT ATTENTION sense.
        values, trace = self.run_case('target-failure')
        self.assertEqual((values[0], values[1], trace.count('TUR')), (0, 10, 2))
        self.assertEqual(values[2], DONE_FLAGS | 1 << 4 | 1 << 11 | self.REPEAT | self.TF)
        facts = self.decode(values)
        self.assertTrue(facts['completed'] and facts['gpt_match'] and facts['range_ok'])
        self.assertEqual(facts['sense'], dict(key=6, asc=0x29, ascq=0))
        self.assertIn('TARGET_FAILURE', facts['flags'])
        self.assertIn('READ 62305152+1', trace)

    def test_a_second_target_failure_check_condition_stops(self):
        values, trace = self.run_case('target-failure-twice')
        self.assertEqual((values[0], values[1], values[5], trace.count('TUR')),
                         (-11, STEP['TUR'], 0x21020100, 2))
        self.assertNotIn('CAPACITY', trace)
        self.decode(values)

    def test_target_failure_with_good_status_is_refused(self):
        values, trace = self.run_case('target-failure-good')
        self.assertEqual((values[0], values[1], values[5]), (-71, STEP['CAPACITY'], 0x21000100))
        self.assertFalse(values[2] & self.TF)
        self.assertNotIn('READ 1+3', trace)
        self.decode(values)

    def test_target_failure_with_an_extra_header_is_repeated_unparsed(self):
        values, trace = self.run_case('target-failure-ehs')
        self.assertEqual((values[0], values[1], values[4], trace.count('TUR')), (0, 10, 0, 2))
        self.assertEqual(values[2], DONE_FLAGS | 1 << 11 | self.UNPARSED | self.REPEAT | self.TF)

    def test_an_unanswered_repeat_after_target_failure_is_uncertain(self):
        values, trace = self.run_case('target-failure-timeout')
        self.assertEqual((values[0], values[1], values[5], trace.count('TUR')), (-110, STEP['TUR'], 0x21020100, 2))
        self.assertTrue(values[2] & 1 << 12 and values[2] & self.TF)

    def test_another_response_value_is_refused(self):
        values, trace = self.run_case('response-two')
        self.assertEqual((values[0], values[1], values[5], trace.count('TUR')), (-71, STEP['TUR'], 0x21020200, 1))
        self.assertFalse(values[2] & self.TF)

    def test_every_target_failure_scenario_decodes(self):
        for case in ('target-failure', 'target-failure-twice', 'target-failure-good', 'target-failure-ehs',
                     'target-failure-timeout', 'response-two'):
            with self.subTest(case=case):
                self.decode(self.run_case(case)[0])

    def test_decoder_binds_the_target_failure_flag(self):
        ok, _ = self.run_case('target-failure')
        stop, _ = self.run_case('target-failure-twice')
        good, _ = self.run_case('target-failure-good')
        for values, message in (
                ([0, 10, DONE_FLAGS | 1 << 11 | self.TF] + ok[3:4] + [0] + ok[5:], 'target failure without a CHECK CONDITION'),
                (stop[:2] + [stop[2] & ~self.TF] + stop[3:], 'target failure stop without its flag'),
                (good[:5] + [0x21000000] + good[6:], 'protocol refusal of a well-formed reply'),
                # Round 1: the flag follows the visible response; a pinned GPT match passes its range.
                ([-11, STEP['TUR'], 0b1111 | self.TF, 1, 2 << 16 | 0x0400, 0x21020000, 0, 0] + [0] * 8 + [20],
                 'target failure flag disagrees with the stop'),
                ([-110, STEP['TUR'], 0b1111 | 1 << 4 | 1 << 12 | self.REPEAT | self.TF, 1, 6 << 16, 0x21020000, 0, 0]
                 + [0] * 8 + [20], 'target failure flag disagrees with the repeat sample'),
                ([-6, STEP['GPT'], 0b1111111 | 1 << 4 | 1 << 7 | 1 << 8 | self.REPEAT, 1, 6 << 16 | 0x2900,
                  0x21000000, LAST_LBA, int.from_bytes(hashlib.sha256(gpt()).digest()[:4], 'big')] + [0] * 8 + [0],
                 'pinned GPT match without its range')):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.decode(values)
        with self.assertRaisesRegex(ValueError, 'storage field range'):
            wire.storage_read([0] * 38 + ok, link_completed=True, header=True)   # V16 flag in a V15 report

    def test_v16_envelope_and_fields(self):
        self.assertEqual(report_modes.FIELDS[16], 55)
        self.assertGreaterEqual(report_modes.LATEST, 16)
        self.assertEqual(wire.result_size(16), wire.result_size(15))
        self.assertEqual(report_modes.defines(16)[-3:], ['G0Q_STORAGE_READ', 'G0Q_STORAGE_HEADER', 'G0Q_STORAGE_RESPONSE'])
        self.assertEqual([report_modes.tag(v) for v in (4, 15, 16)], [0x40000000, 0xf0000000, 0xf0100000])



class StorageWriteStageTest(unittest.TestCase):
    """V17: the V16 stage, then one FUA write of the fixed pattern over zeros and its readback."""
    DEFINES = ('-DG0Q_STORAGE_HEADER', '-DG0Q_STORAGE_RESPONSE', '-DG0Q_STORAGE_WRITE')
    PRESENT, WRITTEN, MATCH = 1 << 16, 1 << 17, 1 << 18
    UA, ZERO, UNCERTAIN, REPEAT, TF = 1 << 4, 1 << 11, 1 << 12, 1 << 14, 1 << 15
    PATTERN_WORD = 0x1155097a

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        out = cls.out = Path(cls.tmp.name)
        for header in HEADERS:
            (out / header).parent.mkdir(parents=True, exist_ok=True)
            (out / header).touch()
        (out / 'linux/errno.h').write_text('#include_next <linux/errno.h>\n')
        cls.table = out / 'gpt.bin'
        cls.table.write_bytes(gpt())
        cls.blocks = {}
        for name, data in (('zero', bytes(4096)), ('pattern', wire.STORAGE_PATTERN),
                           ('foreign', bytes(range(256)) * 16), ('near', wire.STORAGE_PATTERN[:4000] + b'X' + wire.STORAGE_PATTERN[4001:])):
            cls.blocks[name] = out / f'{name}.bin'
            cls.blocks[name].write_bytes(data)
        (out / 'gpt.h').write_text(f'#define G0Q_GPT_SHA256 {c_digest(gpt())}\n')
        cls.exe = out / 'fixture-v17'
        subprocess.run(['cc', '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                        *cls.DEFINES, '-include', str(out / 'gpt.h'), '-I', str(out), '-I', str(SOURCE),
                        str(ROOT / 'tests/s22plus_ufs_storage_fixture.c'), '-o', str(cls.exe)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_case(self, case, block='zero'):
        done = subprocess.run([str(self.exe), case, str(self.table), str(self.blocks[block])],
                              check=True, capture_output=True, text=True)
        fields, _, trace, medium = done.stdout.splitlines()
        values = [int(v) for v in fields.split()]
        self.assertEqual(len(values), 19)
        writes, word = map(int, medium.split())
        return values, trace, writes, word

    def decode(self, values):
        word = int.from_bytes(hashlib.sha256(gpt()).digest()[:4], 'big')
        with mock.patch.object(wire, 'STORAGE_GPT_WORD', word):
            return wire.storage_write([0] * 38 + values, link_completed=True)['storage']

    def test_pattern_constant(self):
        self.assertEqual(hashlib.sha256(wire.STORAGE_PATTERN).hexdigest(), wire.STORAGE_PATTERN_SHA256)
        self.assertEqual(wire.STORAGE_PATTERN[:16], b'S22UFS2B' + struct.pack('<II', TEST_LBA, 0))
        self.assertNotEqual(wire.STORAGE_PATTERN[:8], b'EFI PART')
        header = (SOURCE / 'ufs_storage.h').read_text()
        self.assertIn('"S22UFS2B"', header)
        self.assertIn('1155097a', header)

    def test_zero_block_is_written_once_and_read_back(self):
        values, trace, writes, medium = self.run_case('ok')
        self.assertEqual((values[0], values[1]), (0, 10))
        self.assertEqual(values[2], DONE_FLAGS | self.UA | self.ZERO | self.REPEAT | self.WRITTEN | self.MATCH)
        self.assertEqual((values[17], values[18]), (0x21000000, self.PATTERN_WORD))
        self.assertEqual((writes, medium), (1, self.PATTERN_WORD))
        self.assertTrue(trace.endswith('READ 62305152+1;WRITE 62305152+1;READ 62305152+1;'))
        facts = self.decode(values)
        self.assertEqual(facts['write']['outcome'], 'WRITTEN')
        self.assertTrue(facts['completed'] and facts['block_zero'])

    def test_a_block_holding_the_pattern_is_not_written_again(self):
        values, trace, writes, medium = self.run_case('ok', block='pattern')
        self.assertEqual((values[0], values[1], writes), (0, 10, 0))
        self.assertTrue(values[2] & self.PRESENT and not values[2] & (self.WRITTEN | self.MATCH | self.ZERO))
        self.assertNotIn('WRITE', trace)
        self.assertEqual((values[17], values[18]), (0, 0))
        self.assertEqual(self.decode(values)['write']['outcome'], 'ALREADY_PRESENT')
        self.assertEqual(self.decode(values)['block_sha256'], wire.STORAGE_PATTERN_SHA256)

    def test_foreign_content_is_never_written(self):
        for block in ('foreign', 'near'):
            with self.subTest(block=block):
                values, trace, writes, _ = self.run_case('ok', block=block)
                self.assertEqual((values[0], values[1], writes), (-17, 11, 0))
                self.assertNotIn('WRITE', trace)
                self.assertEqual(values[5], 0x21000000)
                self.assertEqual(self.decode(values)['write']['outcome'], 'FOREIGN_CONTENT')

    def test_too_little_budget_sends_no_write(self):
        values, trace, writes, _ = self.run_case('write-budget')
        self.assertEqual((values[0], values[1], writes), (-110, 11, 0))
        self.assertIn('READ 62305152+1', trace)
        self.assertEqual(self.decode(values)['write']['outcome'], 'WRITE_BUDGET')

    def test_a_stall_before_the_doorbell_sends_no_write(self):
        # The reserve is the last check after the barrier: a CPU stall after the
        # earlier checks still refuses the doorbell (-EBUSY), so nothing is sent.
        values, trace, writes, medium = self.run_case('write-ring-late')
        self.assertEqual((values[0], values[1], writes, values[5], values[17]), (-16, 11, 0, 0, 0))
        self.assertNotIn('WRITE', trace)
        self.assertEqual(medium, int.from_bytes(hashlib.sha256(bytes(4096)).digest()[:4], 'big'))
        self.assertEqual(self.decode(values)['write']['outcome'], 'WRITE_REFUSED')

    def test_an_unanswered_write_is_uncertain_and_never_retried(self):
        values, trace, writes, medium = self.run_case('write-timeout')
        self.assertEqual((values[0], values[1], writes, values[5], values[17]), (-110, 11, 1, 0, 0))
        self.assertTrue(values[2] & self.UNCERTAIN)
        self.assertEqual(trace.count('WRITE'), 1)
        self.assertTrue(trace.endswith('WRITE 62305152+1;'))
        facts = self.decode(values)
        self.assertEqual(facts['write']['outcome'], 'WRITE_UNCERTAIN')
        self.assertTrue(facts['write']['uncertain'])

    def test_a_failed_write_stops_without_readback(self):
        for case, rc, status in (('write-check', -11, 0x21020000), ('write-residual', -61, 0x21000000)):
            with self.subTest(case=case):
                values, trace, writes, _ = self.run_case(case)
                self.assertEqual((values[0], values[1], writes, values[5], values[17]), (rc, 11, 1, status, status))
                self.assertTrue(trace.endswith('WRITE 62305152+1;'))
                facts = self.decode(values)
                self.assertEqual(facts['write']['outcome'], 'WRITE_FAILED')
                if rc == -11:
                    self.assertEqual(facts['sense']['key'], 3)

    def test_a_readback_mismatch_is_reported(self):
        values, trace, writes, medium = self.run_case('write-drop')
        self.assertEqual((values[0], values[1], writes), (-84, 12, 1))
        self.assertTrue(values[2] & self.WRITTEN and not values[2] & self.MATCH)
        self.assertEqual(values[18], int.from_bytes(hashlib.sha256(bytes(4096)).digest()[:4], 'big'))
        self.assertEqual(self.decode(values)['write']['outcome'], 'READBACK_MISMATCH')

    def test_an_unanswered_readback_is_uncertain_after_the_write(self):
        values, trace, writes, medium = self.run_case('readback-timeout')
        self.assertEqual((values[0], values[1], writes, medium), (-110, 12, 1, self.PATTERN_WORD))
        self.assertTrue(values[2] & self.UNCERTAIN and values[2] & self.WRITTEN)
        self.assertEqual(self.decode(values)['write']['outcome'], 'READBACK_FAILED')

    def test_every_producer_scenario_decodes(self):
        for case, block in (('ok', 'zero'), ('ok', 'pattern'), ('ok', 'foreign'), ('write-budget', 'zero'), ('write-ring-late', 'zero'),
                            ('write-timeout', 'zero'), ('write-check', 'zero'), ('write-residual', 'zero'),
                            ('write-drop', 'zero'), ('readback-timeout', 'zero'), ('target-failure', 'zero'),
                            ('target-failure-twice', 'zero'), ('capacity', 'zero'), ('timeout-nop', 'zero'),
                            ('ocs', 'zero'), ('short-read', 'zero'), ('ehs', 'zero'), ('no-iommu', 'zero'),
                            ('short-budget', 'zero')):
            with self.subTest(case=case, block=block):
                self.decode(self.run_case(case, block)[0])

    def test_the_write_follows_only_a_completed_read_stage(self):
        # Any earlier stop sends no write: the fixture asserts at most one write and
        # the trace shows none.
        for case in ('capacity', 'target-failure-twice', 'short-read', 'ocs'):
            with self.subTest(case=case):
                values, trace, writes, _ = self.run_case(case)
                self.assertEqual(writes, 0)
                self.assertNotIn('WRITE', trace)
                self.assertEqual(values[2] >> 16, 0)

    def test_decoder_refuses_inconsistent_write_outcomes(self):
        ok = self.run_case('ok')[0]
        present = self.run_case('ok', block='pattern')[0]
        foreign = self.run_case('ok', block='foreign')[0]
        drop = self.run_case('write-drop')[0]
        for values, message in (
                (ok[:17] + [0x21000000, 0], 'written outcome differs'),
                (ok[:2] + [ok[2] & ~self.MATCH] + ok[3:], 'written outcome differs'),
                (ok[:17] + [0, self.PATTERN_WORD], 'written outcome differs'),
                (present[:2] + [present[2] | self.WRITTEN] + present[3:], 'pattern-present outcome differs'),
                (present[:17] + [0, self.PATTERN_WORD], 'pattern-present outcome differs'),
                (ok[:2] + [ok[2] | self.PRESENT] + ok[3:], 'pattern-present outcome differs'),
                (foreign[:17] + [0x21000000, 0], 'foreign-content stop differs'),
                (drop[:2] + [drop[2] | self.MATCH] + drop[3:], 'readback stop differs'),
                (drop[:17] + [0, drop[18]], 'readback stop differs'),
                ([-17, 9] + foreign[2:], 'storage flags and step disagree'),
                (ok[:2] + [ok[2] | 1 << 19] + ok[3:], 'storage write field range'),
                ([-6, 8] + ok[2:3] + ok[3:17] + [0x21000000, 0], 'write evidence before the write step')):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.decode(values)
        # A completed V16 report is not a V17 completion: no write fields.
        with self.assertRaises(ValueError):
            self.decode(ok[:17] + [0, 0])

    def test_late_stops_follow_the_exchange_that_produced_them(self):
        """Steps 11-12 decode exactly the stops ring() and scsi_until() can emit."""
        check = self.run_case('write-check')[0]
        drop = self.run_case('write-drop')[0]
        late = self.run_case('readback-timeout')[0]

        ua_sense = self.run_case('ok')[0][4]

        def write(rc, status, flags=None, sense=None, header=None):
            v = list(check)
            # Only a CHECK CONDITION stop replaces the stage's UNIT ATTENTION sense.
            v[0], v[4], v[5], v[17] = rc, check[4] if rc == -11 else ua_sense, status, status
            if flags is not None:
                v[2] = flags
            if sense is not None:
                v[4] = sense
            if header is not None:
                v[16] = header
            return v
        no_ua = check[2] & ~(self.UA | self.REPEAT)
        accepted = (
            write(-71, 0),                       # OCS 0, a zero reply: not a RESPONSE
            write(-71, 0x20000000),              # another UPIU type
            write(-71, 0x21000100),              # response 1 without CHECK CONDITION
            write(-5, 0x00000007),               # OCS failure, any reply bytes
            write(-5, 0x21040000),               # RESPONSE with another SCSI status
            write(-11, 0x21020100, flags=no_ua | self.TF, sense=0),       # its own target failure
            write(-11, 0x21020000, flags=check[2] | 1 << 13, sense=0, header=1 << 24),  # unparsed: EHS
            drop[:18] + [0],                     # a mismatch may hash to any first word
            late[:5] + [0x21000000] + late[6:],  # a late readback keeps the write's sample
            check[:3] + [1499] + check[4:],      # the last poll the window admits
            # A first TUR left unparsed, then a write CHECK CONDITION with an extra header.
            write(-11, 0x21020000, flags=no_ua | 1 << 13 | self.REPEAT, sense=0, header=0x01000014))
        for values in accepted:
            with self.subTest(values=values[:6]):
                self.decode(values)
        refused = (
            (write(-71, 0x21020100), 'protocol refusal'),
            (write(-71, 0x21000000), 'protocol refusal'),
            (write(-5, 0x21000000), 'transfer error'),
            (write(-5, 0x21010400), 'transfer error'),
            (write(-61, 0x21020000), 'residual refusal'),
            (write(-11, 0x21000000), 'CHECK CONDITION with another status'),
            (write(-11, 0x21020000, flags=no_ua | self.TF, sense=0), 'target failure without a CHECK CONDITION'),
            (write(-11, 0x21020000, sense=0x30000, header=1 << 24), 'unparsed'),
            (write(-11, 0x21020000, sense=0x30000, header=9), 'data segment'),
            (write(-11, 0x21020000, flags=check[2] | 1 << 13, sense=0, header=18), 'unparsed sense without its stop'),
            (write(-34, 0x21000000), 'another rc'),
            (late[:5] + [0] + late[6:], 'write sample'),
            (drop[:5] + [0x21020000] + drop[6:], 'mismatch without a GOOD read'),
            (late[:18] + [5], 'readback digest'),
            (check[:3] + [1500] + check[4:], 'beyond the poll window'))
        for values, message in refused:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.decode(values)

    def test_v17_envelope_tag_and_fields(self):
        self.assertEqual(report_modes.FIELDS[17], 57)
        self.assertGreaterEqual(report_modes.LATEST, 17)
        self.assertEqual(report_modes.ENVELOPE[17], 512)
        self.assertEqual(report_modes.tag(17), 0xf0200000)
        self.assertEqual(report_modes.defines(17)[-1], 'G0Q_STORAGE_WRITE')


if __name__ == '__main__':
    unittest.main()
