"""H0 raw-first USB diagnostics on temporary filesystem fixtures."""
import errno
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
import s22plus_debian_usb_observation_v1 as observation


class ObservationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.usb = self.root / 'usb'
        self.net = self.root / 'net'
        self.output = self.root / 'output'
        for path in (self.usb, self.net, self.output): path.mkdir()
        self.wanted = dict(serial='fixture-serial', host_mac='fixture-mac')
        self.enterContext(patch.object(observation.target.lane, 'SOURCE_TOPOLOGY', 'usb:source'))
        self.enterContext(patch.object(observation.target.lane, 'CANDIDATE_TOPOLOGY', 'usb:candidate'))

    def endpoint(self, *, interface=True, **fields):
        path = self.usb / 'candidate'
        path.mkdir()
        values = dict(idVendor='1d6b', idProduct='0104', serial=self.wanted['serial'],
                      product='S22 Debian research', busnum='1', devnum='2')
        values.update(fields)
        for key, value in values.items(): (path / key).write_bytes(value.encode() + b'\n')
        if interface: self.interface('net0', path, self.wanted['host_mac'])
        return path

    def interface(self, name, path, address):
        node = self.net / name
        node.mkdir()
        (node / 'device').symlink_to(path, target_is_directory=True)
        (node / 'address').write_text(address + '\n')
        return node

    def sample(self):
        receipt = observation.capture(self.output, 1, self.wanted,
                                      usb_root=self.usb, net_root=self.net)
        from s22plus_native_records_v3 import read
        result = read(Path(receipt['path']))
        self.assertTrue(result['diagnostic_only'])
        self.assertFalse(result['endpoint_acceptance'])
        return result['paths']

    def test_absent_source_does_not_hide_matching_candidate(self):
        self.endpoint()
        self.assertEqual([row['state'] for row in self.sample()],
                         ['ABSENT_USB', 'MATCHING_ENDPOINT_OBSERVED'])

    def test_both_absent(self):
        self.assertEqual([row['state'] for row in self.sample()], ['ABSENT_USB'] * 2)

    def test_usb_without_network_interface(self):
        self.endpoint(interface=False)
        self.assertEqual(self.sample()[1]['state'], 'USB_WITHOUT_NETWORK_INTERFACE')

    def test_descriptor_mismatch(self):
        self.endpoint(serial='different-fixture')
        self.assertEqual(self.sample()[1]['state'], 'USB_IDENTITY_MISMATCH')

    def test_mac_mismatch(self):
        self.endpoint()
        (self.net / 'net0/address').write_text('different-fixture\n')
        self.assertEqual(self.sample()[1]['state'], 'MAC_MISMATCH')

    def test_disappeared_field_is_retained(self):
        path = self.endpoint()
        (path / 'serial').unlink()
        self.assertEqual(self.sample()[1]['state'], 'USB_FIELD_UNAVAILABLE')
        self.assertIn(str(errno.ENOENT).encode(), (self.output / 'usb-001.stdout.bin').read_bytes())

    def test_duplicate_interfaces_are_not_diagnostic_success(self):
        path = self.endpoint()
        self.interface('net1', path, self.wanted['host_mac'])
        self.assertEqual(self.sample()[1]['state'], 'AMBIGUOUS_INTERFACES')

    def test_unrelated_identity_is_not_collected(self):
        path = self.root / 'unrelated'; path.mkdir()
        self.interface('unrelated', path, 'must-not-be-collected')
        self.sample()
        self.assertNotIn(b'must-not-be-collected', (self.output / 'usb-001.stdout.bin').read_bytes())
        self.assertNotIn(b'unrelated', (self.output / 'usb-001.stdout.bin').read_bytes())

    def test_raw_is_durable_before_malformed_field_rejection(self):
        self.endpoint(product='bad\x00product')
        with self.assertRaises(ValueError): self.sample()
        handle = observation.raw.load_handle(self.output / 'usb-001.capture.json')
        self.assertIn(b'6261640070726f647563740a', observation.raw.read_stdout(handle, maximum=32768))
        self.assertFalse((self.output / 'usb-001.json').exists())

    def test_oversized_field_retains_bounded_prefix_before_rejection(self):
        self.endpoint(product='x' * 1000)
        with self.assertRaisesRegex(ValueError, 'field exceeds bound'): self.sample()
        handle = observation.raw.load_handle(self.output / 'usb-001.capture.json')
        self.assertLess(handle.stdout['size'], observation.MAX_CAPTURE)

    def test_sample_budget_does_not_create_streams(self):
        with self.assertRaisesRegex(ValueError, 'budget'):
            observation.capture(self.output, 181, self.wanted, usb_root=self.usb, net_root=self.net)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_inventory_overflow_preserves_incomplete_raw_failure(self):
        for i in range(observation.MAX_INTERFACES + 1): (self.net / str(i)).mkdir()
        with self.assertRaisesRegex(ValueError, 'inventory exceeds'): self.sample()
        handle = observation.raw.load_handle(self.output / 'usb-001.capture.json')
        self.assertIsNotNone(handle.producer_error_type)
        self.assertIsNone(handle.returncode)
        self.assertFalse((self.output / 'usb-001.json').exists())


if __name__ == '__main__': unittest.main()
