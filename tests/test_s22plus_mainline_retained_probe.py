import copy
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1] / 'workspace/public/src/mainline/s22plus_canary_h0'
sys.path.insert(0, str(HERE))
import retained_marker as marker
import retained_probe as probe


class ProbeRecords(unittest.TestCase):
    def setUp(self):
        self.candidate = 'ab' * 32
        self.key = bytes(range(32))
        self.cfg = probe.configuration(self.candidate, self.key, 5, [0, 3, 4],
                                       ['/', '/soc', '/soc/device@1'])

    def decode(self, raw, cfg=None):
        return marker.decode(raw, self.candidate, self.key, version=9, config=cfg or self.cfg)

    def test_complete_records_and_positive_only_interpretation(self):
        raw = b''.join(bytes.fromhex(v) for v in self.cfg['frames'].values())
        result = self.decode(raw + raw)
        self.assertEqual(result['record_count'], 2 * len(self.cfg['frames']))
        self.assertEqual(len(result['events']), len(self.cfg['frames']))
        self.assertTrue(all(len(r['offsets']) == 2 for r in result['events']))
        for key in ('same_boot_pair_proved', 'same_callback_pair_proved',
                    'unique_device_or_driver_proved', 'complete_retry_history',
                    'callback_success_proved', 'reset_cause_proved'):
            self.assertIs(result[key], False)

    def test_torn_wrong_version_and_wrong_key_are_rejected(self):
        original = bytes.fromhex(self.cfg['frames']['0'])
        for offset in (0, 7, 8, 12, 48, 52, 56, 60, 95, 96, 127):
            broken = bytearray(original); broken[offset] ^= 1
            self.assertEqual(self.decode(bytes(broken))['record_count'], 0)
        self.assertEqual(self.decode(original[:110])['record_count'], 0)
        other = probe.configuration(self.candidate, b'x' * 32, 5, [0, 3, 4], self.cfg['node_paths'])
        self.assertEqual(self.decode(bytes.fromhex(other['frames']['0']))['record_count'], 0)

    def test_declaration_shape_and_frame_substitution_are_rejected(self):
        changed = copy.deepcopy(self.cfg)
        changed['span'] -= 128
        with self.assertRaises(ValueError):
            self.decode(b'', changed)
        changed = copy.deepcopy(self.cfg); changed['initcall_ordinals'] = [0, 2, 4]
        changed['frames']['0'] = changed['frames']['1']
        with self.assertRaises(ValueError):
            self.decode(b'', changed)

    def test_capacity_is_closed(self):
        paths = ['/'] + ['/node@' + str(i) for i in range(410)]
        with self.assertRaises(ValueError):
            probe.configuration(self.candidate, self.key, 5, [0, 3, 4], sorted(paths))
        for paths in (['/bad:path'], ['/bad"path'], ['/same', '/same']):
            with self.assertRaises(ValueError):
                probe.configuration(self.candidate, self.key, 5, [0], paths)

    def test_catalog_keeps_disabled_nodes_and_propertyless_ancestors(self):
        nodes = {'/soc/device@1': {'compatible': b'x\0', 'status': b'disabled\0'},
                 '/soc/device@1/sub@0': {'reg': b'x'}, '/pins/no-device': {'pins': b'x'}}
        self.assertEqual(probe.catalog(nodes), ['/', '/soc', '/soc/device@1', '/soc/device@1/sub@0'])

    def test_historical_magic_is_not_accepted(self):
        v8 = marker.configuration(self.candidate, self.key, version=8, initcall_count=5)
        old = b''.join(bytes.fromhex(v) for v in v8['frames'].values())
        self.assertEqual(self.decode(old)['record_count'], 0)
        fresh = b''.join(bytes.fromhex(v) for v in self.cfg['frames'].values())
        self.assertEqual(marker.decode(fresh, self.candidate, self.key, version=8,
                                       config=v8)['record_count'], 0)

    def test_max_capture_grouping_fits_durable_limit(self):
        frame = bytes.fromhex(self.cfg['frames']['0'])
        result = self.decode(frame * (4 * 1024 * 1024 // len(frame)))
        self.assertEqual(result['record_count'], 32768)
        self.assertLess(len(json.dumps(result, indent=2).encode()), 2 * 1024 * 1024)


if __name__ == '__main__':
    unittest.main()
