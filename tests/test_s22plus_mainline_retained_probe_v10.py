import copy
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1] / 'workspace/public/src/mainline/s22plus_canary_h0'
sys.path.insert(0, str(HERE))
import retained_marker as marker
import retained_probe as old
import retained_probe_v10 as probe


class PriorityProbeRecords(unittest.TestCase):
    def setUp(self):
        self.candidate = 'ab' * 32
        self.key = bytes(range(32))
        self.paths = ['/', '/soc@0', probe.TLMM_PATH]
        self.cfg = probe.configuration(self.candidate, self.key, 5, [0, 3, 4], self.paths)

    def decode(self, data, config=None):
        return marker.decode(data, self.candidate, self.key, version=10, config=config or self.cfg)

    def test_rotated_duplicate_positive_records_never_imply_pairing_or_causality(self):
        events = [0, 1, 2, len(probe.FIXED),
                  len(probe.FIXED) + probe.TLMM_POINTS.index('probe-return-zero')]
        data = b'noise' + b''.join(bytes.fromhex(self.cfg['frames'][str(e)]) for e in events)
        data += bytes.fromhex(self.cfg['frames']['0'])
        result = self.decode(b'prefix' + data + b'suffix')
        self.assertEqual(result['record_count'], len(events) + 1)
        self.assertEqual(len(result['events']), len(events))
        self.assertIn('tlmm-pre-deferred-arm:probe-return-zero', result['observed_stages'])
        for key in ('same_boot_pair_proved', 'same_callback_pair_proved',
                    'callback_success_proved', 'gpio_reservation_causality_proved',
                    'physical_retention_coverage_proved', 'complete_retry_history',
                    'stopped_at_last_record', 'reset_cause_proved'):
            self.assertIs(result[key], False)

    def test_frame_authentication_and_declaration_shape_validation(self):
        frame = bytes.fromhex(self.cfg['frames']['0'])
        for offset in (0, 7, 8, 12, 48, 52, 56, 60, 95, 96, 127):
            bad = bytearray(frame); bad[offset] ^= 1
            self.assertEqual(self.decode(bytes(bad))['record_count'], 0)
        self.assertEqual(self.decode(frame[:110])['record_count'], 0)
        other = probe.configuration(self.candidate, b'x' * 32, 5, [0, 3, 4], self.paths)
        self.assertEqual(self.decode(bytes.fromhex(other['frames']['0']))['record_count'], 0)
        for field, value in [('span', self.cfg['span'] - 128), ('initcall_ordinals', [3, 0, 4])]:
            bad = copy.deepcopy(self.cfg); bad[field] = value
            with self.assertRaises(ValueError):
                self.decode(frame, bad)

    def test_v9_and_v10_cannot_substitute_for_each_other(self):
        historical = old.configuration(self.candidate, self.key, 5, [0, 3, 4], self.paths)
        data = b''.join(bytes.fromhex(f) for f in historical['frames'].values())
        self.assertEqual(self.decode(data)['record_count'], 0)
        fresh = b''.join(bytes.fromhex(f) for f in self.cfg['frames'].values())
        self.assertEqual(old.decode(fresh, self.candidate, self.key, historical)['record_count'], 0)
        self.assertEqual(old.decode(data, self.candidate, self.key, historical)['record_count'],
                         len(historical['frames']))

    def test_exact_node_and_capacity_are_required(self):
        with self.assertRaises(ValueError):
            probe.configuration(self.candidate, self.key, 5, [0], ['/', '/soc@0'])
        paths = sorted(self.paths + [f'/extra@{i}' for i in range(410)])
        with self.assertRaises(ValueError):
            probe.configuration(self.candidate, self.key, 5, [0], paths)

    def test_maximum_capture_grouping_preserves_durable_bound(self):
        frame = bytes.fromhex(self.cfg['frames']['0'])
        result = self.decode(frame * (4 * 1024 * 1024 // len(frame)))
        self.assertEqual(result['record_count'], 32768)
        self.assertLess(len(json.dumps(result, indent=2).encode()), 2 * 1024 * 1024)


if __name__ == '__main__':
    unittest.main()
