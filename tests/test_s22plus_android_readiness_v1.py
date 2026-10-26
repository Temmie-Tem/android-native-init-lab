"""Actual immutable raw captures through the fixed readiness observation loop."""
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_native_target_io_v3 as target
from s22plus_native_records_v3 import pin


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.directory=Path(temporary.name)
        self.binding=dict(serial='RFCT0000000',topology=target.lane.SOURCE_TOPOLOGY)
        self.inventory=b'List of devices attached\nRFCT0000000 device model:SM_S906N device:g0q transport_id:1\n'
        self.missing=b"adb: device 'RFCT0000000' not found\n"

    def fixture(self,values,*,after=None):
        directory=self.directory/str(len(list(self.directory.iterdir())))
        client=target.Android(dict(path='/fixture'),self.binding,{},directory,guard=lambda:None)
        calls=[];handles=[];values=iter(values)
        def command(arguments,name,*,timeout,before_launch=None):
            client.guard()
            if before_launch:before_launch()
            calls.append(dict(arguments=arguments,name=name,timeout=timeout))
            value=next(values)
            if isinstance(value,Exception):raise value
            if isinstance(value,bytes):value=dict(stdout=value)
            value=dict(value)
            writer=target.raw.RawCaptureWriter(directory,name,stdout_maximum=16384,
                stderr_maximum=16384,argv0_name='fixture-adb')
            writer.write_stdout(value.pop('stdout',b''))
            writer.write_stderr(value.pop('stderr',b''))
            handle=writer.finalize(returncode=value.pop('returncode',0),**value)
            handles.append(handle)
            if after:handle=after(handle,len(calls))
            return handle
        return client,calls,handles,command

    def test_exact_disappearance_gets_new_inventory_and_keeps_raw_failure(self):
        client,calls,handles,command=self.fixture([
            self.inventory,dict(returncode=1,stderr=self.missing),self.inventory,b'1'])
        with mock.patch.object(client,'command',side_effect=command),\
             mock.patch.object(client,'health') as health,mock.patch.object(target.time,'sleep'):
            client.wait_ready(deadline_ns=target.clock()+10_000_000_000)
        self.assertEqual([x['name'] for x in calls],[
            'wait-000-inventory','wait-000-boot','wait-001-inventory','wait-001-boot'])
        self.assertEqual([x['arguments'] for x in calls],
            [['devices','-l'],['-s','RFCT0000000','shell','getprop sys.boot_completed']]*2)
        health.assert_not_called()
        before=pin(handles[1].receipt_path)
        self.assertEqual(target.raw.load_handle(handles[1].receipt_path),handles[1])
        self.assertEqual(target.raw.read_stderr(handles[1],maximum=16384),self.missing)
        self.assertEqual(pin(handles[1].receipt_path),before)
        self.assertEqual(handles[1].stdout_path.stat().st_mode&0o777,0o400)

    def test_other_diagnostics_status_and_incomplete_producers_stop(self):
        failures=[
            dict(returncode=1,stderr=value) for value in (
                self.missing.replace(b'RFCT0000000',b'RFCS0000000'),self.missing.rstrip(b'\n'),
                self.missing+b'\n',self.missing+b'additional\n',
                b'adb: device offline\n',b'adb: device unauthorized\n',
                b'adb: no devices/emulators found\n',b'adb: more than one device/emulator\n')]
        failures += [
            dict(returncode=1,stderr=self.missing,stdout=b'0'),
            dict(returncode=2,stderr=self.missing),dict(returncode=0,stderr=self.missing,stdout=b'1'),
            dict(returncode=1,stderr=self.missing,timed_out=True),
            dict(returncode=1,stderr=self.missing,output_exceeded=True),
            dict(returncode=1,stderr=self.missing,producer_error_type='OSError'),
            dict(returncode=None,stderr=self.missing)]
        for value in failures:
            with self.subTest(value=value):
                client,calls,_,command=self.fixture([self.inventory,value])
                with mock.patch.object(client,'command',side_effect=command),self.assertRaises((ValueError,target.raw.RawCaptureError)):
                    client.wait_ready(deadline_ns=target.clock()+10_000_000_000)
                self.assertEqual(len(calls),2)

    def test_malformed_success_and_inventory_diagnostics_stop(self):
        for output in (b'2',b'1\n1',b'\xff',b'X'*17):
            with self.subTest(output=output):
                client,calls,_,command=self.fixture([self.inventory,output])
                with mock.patch.object(client,'command',side_effect=command),self.assertRaises((ValueError,target.raw.RawCaptureError)):
                    client.wait_ready(deadline_ns=target.clock()+10_000_000_000)
                self.assertEqual(len(calls),2)
        client,calls,_,command=self.fixture([dict(stdout=self.inventory,stderr=b'diagnostic')])
        with mock.patch.object(client,'command',side_effect=command),self.assertRaises((ValueError,target.raw.RawCaptureError)):
            client.wait_ready(deadline_ns=target.clock()+10_000_000_000)
        self.assertEqual(len(calls),1)

    def test_next_inventory_must_select_the_same_unambiguous_target(self):
        for inventory in (
                self.inventory+self.inventory.splitlines(keepends=True)[1],
                self.inventory+b'RFCS0000000 device model:SM_S906N device:g0q\n',
                self.inventory.replace(b'RFCT0000000',b'RFCS0000000'),
                b'bad header\n',b'List of devices attached\nmalformed\n'):
            with self.subTest(inventory=inventory):
                client,calls,_,command=self.fixture([
                    self.inventory,dict(returncode=1,stderr=self.missing),inventory])
                with mock.patch.object(client,'command',side_effect=command),\
                     mock.patch.object(target.time,'sleep'),self.assertRaises((ValueError,target.raw.RawCaptureError)):
                    client.wait_ready(deadline_ns=target.clock()+10_000_000_000)
                self.assertEqual(len(calls),3)

    def test_capture_integrity_and_handle_identity_are_not_transient(self):
        def corrupt(handle,index):
            if index==2:
                handle.stderr_path.chmod(0o600);handle.stderr_path.write_bytes(self.missing+b'x')
                handle.stderr_path.chmod(0o400)
            return handle
        def forged(handle,index):
            return replace(handle,returncode=0) if index==2 else handle
        for alter in (corrupt,forged):
            client,calls,_,command=self.fixture([self.inventory,dict(returncode=1,stderr=self.missing)],after=alter)
            with mock.patch.object(client,'command',side_effect=command),self.assertRaises((ValueError,target.raw.RawCaptureError)):
                client.wait_ready(deadline_ns=target.clock()+10_000_000_000)
            self.assertEqual(len(calls),2)

    def test_expiry_after_inventory_blocks_the_property_launch(self):
        now=[0]
        def expire(handle,index):
            now[0]=1_000_000_000
            return handle
        client,calls,_,command=self.fixture([self.inventory],after=expire)
        with mock.patch.object(client,'command',side_effect=command),\
             mock.patch.object(target,'clock',side_effect=lambda:now[0]),self.assertRaises(TimeoutError):
            client.wait_ready(deadline_ns=1_000_000_000)
        self.assertEqual(len(calls),1)
        self.assertLessEqual(calls[0]['timeout'],1)

    def test_initial_expiry_and_too_short_acquisition_budget_do_not_read(self):
        for deadline in (0,50_000_000):
            client,calls,_,command=self.fixture([])
            with mock.patch.object(client,'command',side_effect=command),\
                 mock.patch.object(target,'clock',return_value=0),self.assertRaises(TimeoutError):
                client.wait_ready(deadline_ns=deadline)
            self.assertEqual(calls,[])

    def test_transients_consume_original_deadline_without_renewal(self):
        now=[0];values=[self.inventory,dict(returncode=1,stderr=self.missing)]*4
        client,calls,_,command=self.fixture(values)
        def sleep(seconds):now[0]+=round(seconds*1e9)
        with mock.patch.object(client,'command',side_effect=command),\
             mock.patch.object(target,'clock',side_effect=lambda:now[0]),\
             mock.patch.object(target.time,'sleep',side_effect=sleep),self.assertRaises(TimeoutError):
            client.wait_ready(deadline_ns=1_100_000_000)
        self.assertEqual(len(calls),6)
        self.assertTrue(all(x['timeout']<=1.1 for x in calls))

    def test_inventory_count_remains_bounded_when_clock_does_not_advance(self):
        client,calls,_,command=self.fixture([self.inventory,dict(returncode=1,stderr=self.missing)]*256)
        with mock.patch.object(client,'command',side_effect=command),\
             mock.patch.object(target,'clock',return_value=0),mock.patch.object(target.time,'sleep'),\
             self.assertRaisesRegex(ValueError,'exceeds bound'):
            client.wait_ready(deadline_ns=20_000_000_000)
        self.assertEqual(len(calls),512)

    def test_next_guard_failure_and_late_success_still_stop(self):
        client,calls,_,command=self.fixture([
            self.inventory,dict(returncode=1,stderr=self.missing),ValueError('scope guard rejected')])
        with mock.patch.object(client,'command',side_effect=command),\
             mock.patch.object(target.time,'sleep'),self.assertRaisesRegex(ValueError,'scope guard rejected'):
            client.wait_ready(deadline_ns=target.clock()+10_000_000_000)
        self.assertEqual(len(calls),3)
        now=[0]
        def late(handle,index):
            if index==2:now[0]=1_000_000_000
            return handle
        client,calls,_,command=self.fixture([self.inventory,b'1'],after=late)
        with mock.patch.object(client,'command',side_effect=command),\
             mock.patch.object(target,'clock',side_effect=lambda:now[0]),\
             self.assertRaisesRegex(ValueError,'original deadline'):
            client.wait_ready(deadline_ns=1_000_000_000)
        self.assertEqual(len(calls),2)


if __name__=='__main__':unittest.main()
