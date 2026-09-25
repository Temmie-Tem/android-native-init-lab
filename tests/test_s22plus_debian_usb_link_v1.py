"""Real temporary sysfs trees for the shared Debian endpoint selector; H0 only."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
import s22plus_debian_first_boot_v1 as lane
import s22plus_debian_installed_boot_v1 as installed


class USBLinkTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.net = self.root / 'class/net'
        self.usb = self.root / 'bus/usb/devices'
        self.net.mkdir(parents=True)
        self.usb.mkdir(parents=True)
        self.wanted = dict(host_mac='fixture-host-mac', serial='fixture-serial')
        for name, value in [('SOURCE_TOPOLOGY', 'usb:source'),
                            ('CANDIDATE_TOPOLOGY', 'usb:candidate')]:
            self.enterContext(patch.object(lane.target.lane, name, value))
        roots = {'/sys/class/net': self.net, '/sys/bus/usb/devices': self.usb}
        # Only redirect the selector's two absolute roots. Resolve, symlink
        # traversal and bounded descriptor reads use the actual filesystem.
        self.enterContext(patch.object(lane, 'Path', side_effect=lambda p: roots[str(p)]))

    def endpoint(self, topology, name='net0', **fields):
        usb = self.usb / topology
        usb.mkdir(exist_ok=True)
        descriptors = dict(idVendor='1d6b', idProduct='0104',
            serial=self.wanted['serial'], product='S22 Debian research',
            busnum='1', devnum='2')
        descriptors.update(fields)
        for key, value in descriptors.items():
            (usb / key).write_text(value + '\n')
        interface = usb / (topology + ':1.0')
        interface.mkdir(exist_ok=True)
        node = self.net / name
        node.mkdir()
        (node / 'address').write_text(self.wanted['host_mac'] + '\n')
        (node / 'device').symlink_to(interface, target_is_directory=True)
        return node

    def select(self, owner_type=lane.Owner):
        owner = object.__new__(owner_type)
        owner.plan = dict(link=self.wanted)
        return owner.usb_link()

    def test_candidate_is_found_when_source_topology_is_absent(self):
        self.endpoint('candidate')
        for owner_type in (lane.Owner, installed.Owner):
            with self.subTest(owner=owner_type.__module__):
                self.assertEqual(self.select(owner_type)['topology'], 'usb:candidate')

    def test_source_is_found_when_candidate_topology_is_absent(self):
        self.endpoint('source')
        self.assertEqual(self.select()['topology'], 'usb:source')

    def test_unrelated_source_does_not_hide_candidate(self):
        (self.usb / 'source').mkdir()
        self.endpoint('candidate')
        self.assertEqual(self.select()['topology'], 'usb:candidate')

    def test_empty_tree_and_unrelated_topology_are_not_endpoints(self):
        self.assertIsNone(self.select())
        self.endpoint('outside')
        self.assertIsNone(self.select())

    def test_wrong_mac_is_not_an_endpoint(self):
        node = self.endpoint('candidate')
        (node / 'address').write_text('different-fixture-mac\n')
        self.assertIsNone(self.select())

    def test_descriptor_mismatch_is_rejected_on_candidate(self):
        self.endpoint('candidate', serial='wrong-fixture')
        with self.assertRaisesRegex(ValueError, 'descriptor identity differs'):
            self.select()

    def test_missing_descriptor_is_not_an_endpoint(self):
        self.endpoint('candidate')
        (self.usb / 'candidate/serial').unlink()
        self.assertIsNone(self.select())

    def test_oversized_descriptor_is_rejected(self):
        self.endpoint('candidate', product='x' * 513)
        with self.assertRaisesRegex(ValueError, 'exceeds bound'):
            self.select()

    def test_two_matching_interfaces_are_ambiguous(self):
        self.endpoint('source', 'net0')
        self.endpoint('candidate', 'net1')
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            self.select()

    def test_disappearing_interface_does_not_hide_next_interface(self):
        node = self.net / 'gone'
        node.mkdir()
        (node / 'address').write_text(self.wanted['host_mac'] + '\n')
        (node / 'device').symlink_to(self.root / 'absent')
        self.endpoint('candidate')
        self.assertEqual(self.select()['interface'], 'net0')


if __name__ == '__main__':
    unittest.main()
