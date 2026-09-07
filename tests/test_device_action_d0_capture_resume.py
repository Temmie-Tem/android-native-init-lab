"""Raw-first clients resume past complete and interrupted capture names."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from tests.test_device_action_d0_v2 import load_module


class CaptureResumeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.d0=load_module()

    def test_new_client_preserves_complete_and_partial_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);adb=run/'fixture-adb';adb.write_bytes(b'fixture');adb.chmod(0o700)
            first=self.d0.AdbReadOnlyClient(adb)
            first.bind_raw_capture_dir(run)
            def acquire(argv,capture_dir,name,**kwargs):
                return self.d0.raw_capture.publish_captured_bytes(capture_dir,name,stdout=b'result\n')
            with mock.patch.object(self.d0.raw_capture,'acquire_command',side_effect=acquire):
                self.assertEqual(first._run(['version'],'version'),'result')
                # Root observer receipt and partial writer ordinal both count.
                (run/'0008-observer-eof.capture.json').write_bytes(b'partial receipt')
                (run/'raw-adb/0012-adb-devices.stdout.bin').write_bytes(b'partial output')
                before={p:p.read_bytes() for directory in (run,run/'raw-adb') for p in directory.iterdir() if p.is_file()}
                resumed=self.d0.AdbReadOnlyClient(adb);resumed.bind_raw_capture_dir(run)
                self.assertEqual(resumed._run(['version'],'version'),'result')
                self.assertTrue((run/'raw-adb/0013-version.capture.json').exists())
                self.assertTrue(all(p.read_bytes()==raw for p,raw in before.items()))
                resumed.bind_raw_capture_dir(run)
                self.assertEqual(resumed._capture_name('next'),'0014-next')

    def test_rebinding_never_rewinds_or_changes_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);adb=run/'fixture-adb';adb.write_bytes(b'fixture');adb.chmod(0o700)
            client=self.d0.AdbReadOnlyClient(adb);client.bind_raw_capture_dir(run)
            self.assertEqual(client._capture_name('allocated'),'0000-allocated')
            client.bind_raw_capture_dir(run)
            self.assertEqual(client._capture_name('next'),'0001-next')
            other=run/'other';other.mkdir()
            with self.assertRaisesRegex(self.d0.D0Error,'directory changed'):
                client.bind_raw_capture_dir(other)

if __name__=='__main__':unittest.main()
