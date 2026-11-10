"""Offline attribution checks. Device-side production is exercised separately in QEMU."""
import hmac
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from decode import DUE_MS, MAGIC, project

KEY = bytes(range(32))
CANDIDATE = bytes(range(16))


def signed(samples, *, tag=b'A', bind=(2000, 3000, 11), count=1):
    body = bytearray(96)
    body[:40] = MAGIC + CANDIDATE + tag * 16
    struct.pack_into('<IIi', body, 40, *bind)
    mask = 0
    for i, ms, state in samples:
        struct.pack_into('<Ih', body, 52 + 6 * i, ms, state)
        mask |= 1 << i
    struct.pack_into('<II', body, 88, mask, count)
    return body + hmac.digest(KEY, body, 'sha256')


class Observation(unittest.TestCase):
    def test_ties_missing_times_and_state_changes(self):
        rows = [(0, 7000, 0), (2, 27001, 0), (5, 119001, 7)]
        raw = signed(rows, bind=(6000, 7000, 11))
        frame, = project(raw, CANDIDATE, KEY)['frames']
        self.assertEqual(frame['bind'], 'bound')
        self.assertEqual([s['after_successful_bind'] for s in frame['samples']], [False, True, True])
        self.assertEqual([s['state'] for s in frame['samples']], ['not attached', 'not attached', 'configured'])

    def test_no_frame_and_failed_observations(self):
        self.assertEqual(project(b'', CANDIDATE, KEY)['frames'], [])
        for bind, count, expected in [
            ((0, 0, 0), 0, 'no callback observed'), ((1, 0, 0), 1, 'callback entered'),
            ((1, 2, -16), 1, 'callback failed'), ((1, 2, 11), 2, 'repeated'),
        ]:
            raw = signed([(0, DUE_MS[0], -19), (1, DUE_MS[1], -16)], bind=bind, count=count)
            frame, = project(raw, CANDIDATE, KEY)['frames']
            self.assertEqual(frame['bind'], expected)
            self.assertEqual([s['state'] for s in frame['samples']], ['UDC absent', 'UDC list busy'])
            self.assertFalse(any(s['after_successful_bind'] for s in frame['samples']))

    def test_damaged_foreign_and_wrong_key(self):
        frame = signed([(0, 7000, 0)])
        damaged = frame.copy()
        damaged[53] ^= 1
        foreign = frame.copy()
        foreign[8] ^= 1
        result = project(b'prefix' + damaged + foreign + frame + frame[:6] + frame[:40], CANDIDATE, KEY)
        self.assertEqual((len(result['frames']), result['damaged'], result['foreign']), (1, 2, 1))
        self.assertEqual(project(frame, CANDIDATE, b'k' * 32)['frames'], [])

    def test_no_cross_frame_join_even_if_boot_tag_matches(self):
        raw = signed([(0, 7001, 0)]) + signed([(3, 61000, 7)])
        frames = project(raw, CANDIDATE, KEY)['frames']
        self.assertEqual([len(f['samples']) for f in frames], [1, 1])
        self.assertEqual(frames[0]['boot_tag'], frames[1]['boot_tag'])

    def test_authenticated_invalid_chronology(self):
        for times in [[(0, 120000, 0)], [(0, 7000, 0), (1, 6999, 7)], [(0, 7000, 42)]]:
            self.assertEqual(project(signed(times), CANDIDATE, KEY)['damaged'], 1)


if __name__ == '__main__':
    unittest.main()
