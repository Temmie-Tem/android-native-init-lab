"""Stage 0 host port watch: topology mapping, transitions and labels on a fake sysfs."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/mainline/s22plus_canary_h0'))
import host_port_watch as hpw


class FakeSysfs:
    def __init__(self, root):
        self.root = Path(root)

    def port(self, topology, state):
        node = hpw.port_node(topology, self.root)
        node.mkdir(parents=True, exist_ok=True)
        (node / 'state').write_text(state + '\n')
        (node / 'connect_type').write_text('unknown\n')

    def device(self, topology, present):
        node = self.root / topology
        if present:
            node.mkdir(parents=True, exist_ok=True)
            (node / 'idVendor').write_text('04e8\n')
            (node / 'speed').write_text('480\n')
        elif node.exists():
            for f in node.iterdir():
                f.unlink()
            node.rmdir()


class HostPortWatchTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.base = Path(t.name)
        self.sys = FakeSysfs(self.base / 'sys')

    def test_port_node_mapping(self):
        r = Path('/x')
        self.assertEqual(hpw.port_node('3-1.3', r), r / '3-1:1.0/3-1-port3')
        self.assertEqual(hpw.port_node('usb:2-1.4.4', r), r / '2-1.4:1.0/2-1.4-port4')
        self.assertEqual(hpw.port_node('2-1', r), r / 'usb2/2-0:1.0/usb2-port1')
        for bad in ('3', '3-', 'a-1', '3-1.x'):
            with self.assertRaises(ValueError):
                hpw.port_node(bad, r)

    def run_script(self, script):
        """script: list of (time, callable) applied as the fake clock advances."""
        clock = {'t': 0.0}
        pending = list(script)

        def sleep(dt):
            clock['t'] += dt
            while pending and pending[0][0] <= clock['t']:
                pending.pop(0)[1]()
        return hpw.watch(('3-1.3',), 1.0, 0.1, self.base / 'out', usb_root=self.base / 'sys',
                         clock=lambda: clock['t'], sleep=sleep, wall=lambda: 0.0, monitors=False)

    def test_stays_not_attached(self):
        self.sys.port('3-1.3', 'not attached')
        s = self.run_script([])
        self.assertEqual(s['ports']['3-1.3']['label'], 'PORT_STAYED_NOT_ATTACHED')
        self.assertEqual(s['ports']['3-1.3']['transitions'], 1)
        self.assertFalse(s['device_contact'])

    def test_connect_without_enumeration(self):
        self.sys.port('3-1.3', 'not attached')
        s = self.run_script([(0.3, lambda: self.sys.port('3-1.3', 'powered')),
                             (0.6, lambda: self.sys.port('3-1.3', 'not attached'))])
        p = s['ports']['3-1.3']
        self.assertEqual(p['label'], 'PORT_LEFT_NOT_ATTACHED_WITHOUT_DEVICE')
        self.assertEqual(p['transitions'], 3)
        lines = (self.base / 'out/ports.jsonl').read_text().splitlines()
        self.assertEqual([json.loads(l)['snapshot']['port_state'] for l in lines],
                         ['not attached', 'powered', 'not attached'])

    def test_enumerated(self):
        self.sys.port('3-1.3', 'not attached')

        def attach():
            self.sys.port('3-1.3', 'configured')
            self.sys.device('3-1.3', True)
        s = self.run_script([(0.5, attach)])
        self.assertEqual(s['ports']['3-1.3']['label'], 'DEVICE_ENUMERATED')

    def test_missing_port_is_unreadable(self):
        s = self.run_script([])
        self.assertEqual(s['ports']['3-1.3']['label'], 'PORT_STATE_UNREADABLE')

    def test_refuses_existing_output(self):
        (self.base / 'out').mkdir()
        self.sys.port('3-1.3', 'not attached')
        with self.assertRaises(FileExistsError):
            self.run_script([])


if __name__ == '__main__':
    unittest.main()
