"""Mainline USB producer/consumer, exact scope and owner interruption tests."""
import copy
import builtins
from contextlib import contextmanager, ExitStack
import errno
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest import mock

import test_s22plus_native_session_v3 as harness
import test_s22plus_mainline_canary_h0 as canary
import s22plus_mainline_access_v1 as access
import s22plus_mainline_auto_recovery_v1 as auto_recovery
import s22plus_mainline_download_access_v1 as download
import s22plus_mainline_profile_v1 as profile
import s22plus_mainline_session_v1 as mainline
import s22plus_mainline_task_v1 as task
import s22plus_native_session_v3 as owner
from s22plus_native_adapter_v3 import Adapter
import s22plus_native_records_v3 as records
import device_action_raw_capture_v1 as raw

ROOT = Path(__file__).resolve().parents[1]


class USBTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name);self.usb=self.base/'usb';self.usb.mkdir();self.net=self.base/'net';self.net.mkdir()
        self.out=self.base/'out';self.out.mkdir()
        self.manifest={'network':{'serial':'FIXTURE_CANARY','host_mac':'02:00:00:00:00:01'}}

    def device(self,topology=None):
        node=self.usb/(topology or access.target.lane.CANDIDATE_TOPOLOGY).removeprefix('usb:');node.mkdir()
        fields=dict(idVendor='1d6b',idProduct='0104',serial='FIXTURE_CANARY',product='G0Q RAM Canary',
            manufacturer='Native Init Lab',busnum='3',devnum='7',speed='480')
        for k,v in fields.items():(node/k).write_text(v+'\n')
        return node

    def interface(self,node,name='fixture0'):
        interface=node/(node.name+':1.0');interface.mkdir()
        driver=self.base/'cdc_ncm';driver.mkdir();(interface/'driver').symlink_to(driver)
        net=self.net/name;net.mkdir();(net/'device').symlink_to(interface)
        (net/'address').write_text('02:00:00:00:00:01\n');(net/'ifindex').write_text('12\n')
        return net

    def capture(self,name):
        return access.capture_endpoint(self.out,name,usb_root=self.usb,net_root=self.net)

    def test_absence_then_exact_usb2_and_no_source_lane_substitution(self):
        self.device(access.target.lane.SOURCE_TOPOLOGY)
        self.assertIsNone(access.endpoint(self.capture('source-only'),self.manifest))
        node=self.device();self.assertIsNone(access.endpoint(self.capture('no-interface'),self.manifest))
        self.interface(node);found=access.endpoint(self.capture('complete'),self.manifest)
        self.assertEqual(found['interface'],'fixture0');self.assertEqual(found['topology'],access.target.lane.CANDIDATE_TOPOLOGY)

    def test_wrong_descriptor_mac_driver_or_extra_interface_stops(self):
        node=self.device();net=self.interface(node)
        for field,value in [('serial','other'),('speed','5000'),('idProduct','0000')]:
            old=(node/field).read_text();(node/field).write_text(value)
            with self.assertRaises(ValueError):access.endpoint(self.capture(field.lower()),self.manifest)
            (node/field).write_text(old)
        (net/'address').write_text('02:00:00:00:00:02')
        with self.assertRaises(ValueError):access.endpoint(self.capture('badmac'),self.manifest)
        (net/'address').write_text('02:00:00:00:00:01')
        other=self.net/'fixture1';other.mkdir();(other/'device').symlink_to((net/'device').resolve())
        for field in ('address','ifindex'):(other/field).write_text((net/field).read_text())
        with self.assertRaises(ValueError):access.endpoint(self.capture('ambiguous'),self.manifest)

    def test_raw_capture_required_and_failed_producer_never_projects(self):
        with self.assertRaises(ValueError):access.endpoint({},self.manifest)
        h=raw.RawCaptureWriter(self.out,'failed',stdout_maximum=4096,stderr_maximum=0)
        h.write_stdout(b'{}\n');h=h.finalize(returncode=None,producer_error_type='OSError')
        with self.assertRaises(raw.RawCaptureError):access.endpoint(h,self.manifest)


class ConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        canary.CanaryTests.setUpClass();cls.fixture=canary.CanaryTests()
    @classmethod
    def tearDownClass(cls):canary.CanaryTests.tearDownClass()

    def capture(self,data,*,hang=False):
        tmp=tempfile.TemporaryDirectory(dir=self.fixture.base);self.addCleanup(tmp.cleanup);folder=Path(tmp.name)
        manifest=copy.deepcopy(self.fixture.manifest);manifest['network']={'host_ip':'127.0.0.1','device_ip':'127.0.0.1'}
        manifest['port']=1;found={'interface':'lo'};requests=[];errors=[]
        server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1);server.settimeout(2)
        def serve():
            try:
                with server.accept()[0] as client:
                    payload=b''
                    while len(payload)<72:
                        more=client.recv(72-len(payload))
                        if not more:break
                        payload+=more
                    requests.append(payload);client.sendall(data)
                    if hang:threading.Event().wait(.25)
            except Exception as error:errors.append(error)
            finally:server.close()
        thread=threading.Thread(target=serve);thread.start()
        deadline=records.clock()+(100_000_000 if hang else 2_000_000_000)
        try:
            with mock.patch.object(access.secrets,'token_bytes',return_value=self.fixture.nonce):
                try:handle=access.capture_connection(folder,manifest,found,deadline_ns=deadline,guard=lambda:None,
                    connect=lambda client:client.connect(server.getsockname()))
                except ValueError:handle=raw.load_handle(folder/'response.capture.json')
        finally:thread.join(3)
        self.assertFalse(thread.is_alive());self.assertFalse(errors);self.assertEqual(len(requests),1)
        self.assertEqual(requests[0],profile.codec.request(self.fixture.key,self.fixture.identity,self.fixture.nonce))
        return folder,handle,manifest

    def test_actual_arm64_response_through_one_bound_socket_and_raw_parser(self):
        folder,handle,manifest=self.capture(self.fixture.raw())
        proof=profile.codec.verify_capture(handle,manifest,self.fixture.nonce)
        self.assertEqual(proof['pid'],1);self.assertEqual(proof['status'],'AUTHENTICATED_CANARY_OBSERVATION')
        self.assertTrue(records.read(folder/'connection.json')['descriptor_closed'])
        self.assertEqual(raw.read_stdout(raw.load_handle(folder/'request.capture.json'),maximum=72),
            profile.codec.request(self.fixture.key,self.fixture.identity,self.fixture.nonce))

    def test_wrong_auth_and_partial_bytes_remain_sealed(self):
        good=self.fixture.raw()
        for data in (good[:120],good[:256]+bytes(32)+good[288:]):
            folder,handle,manifest=self.capture(data)
            self.assertEqual(raw.read_stdout(handle,maximum=access.MAX_RX),data)
            with self.assertRaises(ValueError):profile.codec.verify_capture(handle,manifest,self.fixture.nonce)

    def test_timeout_retains_partial_response_and_forbids_success_projection(self):
        folder,handle,manifest=self.capture(b'partial',hang=True)
        self.assertTrue(handle.timed_out);self.assertEqual(raw.read_stdout(handle,maximum=access.MAX_RX),b'partial')
        self.assertFalse(records.read(folder/'connection.json')['eof'])
        with self.assertRaises(raw.RawCaptureError):profile.codec.verify_capture(handle,manifest,self.fixture.nonce)

    def test_connection_failure_is_one_attempt_with_empty_failed_capture(self):
        with tempfile.TemporaryDirectory(dir=self.fixture.base) as name:
            folder=Path(name);manifest=dict(self.fixture.manifest,network={'host_ip':'127.0.0.1'})
            connect=mock.Mock(side_effect=ConnectionRefusedError(errno.ECONNREFUSED,'fixture'))
            with self.assertRaises(ConnectionRefusedError):access.capture_connection(folder,manifest,{'interface':'lo'},
                deadline_ns=records.clock()+1_000_000_000,guard=lambda:None,connect=connect)
            self.assertEqual(connect.call_count,1);h=raw.load_handle(folder/'response.capture.json')
            self.assertEqual(h.producer_error_type,'ConnectionRefusedError')
            self.assertFalse(records.read(folder/'connection.json')['sent_complete_request'])


class OwnerTests(unittest.TestCase):
    setUp=harness.OwnerTests.setUp
    def operation(self, *, ufs=False, stop=False):
        device=harness.DeviceFixture()
        image = {'ufs_link': True, 'download_return': {}} if ufs else {'fixture': True}
        with mock.patch.object(device, 'prepare', return_value={'target': 'fixture', 'N': image}):
            directory=owner.prepare_operation(self.root,self.grant,operation=profile.OPERATION,adapter=device)
        def observe(adapter,request,guard):
            guard();adapter.assert_mode('N');adapter.actions.append('mainline-request-once')
            if adapter.fail_after=='observation':raise OSError('partial response')
            return adapter.proof(mainline.normal_steps()[2])
        patch=mock.patch.object(access,'observe',observe);patch.start();self.addCleanup(patch.stop)
        if ufs:
            def download_observe(adapter, request, guard, before_control):
                guard()
                before_control(lambda: {'fixed': 'fixture permit'})
                device.actions.append('download-control-once')
                device.mode = 'Download'
                if stop:
                    raise OSError('fixture stopped after control')
                return device.proof(mainline.normal_steps(request)[2])

            for module, name, replacement in (
                (download, 'observe', download_observe),
                (download, 'return_request', lambda *a, **k: {}),
                (auto_recovery, 'attempt', lambda *_: None),
            ):
                patch = mock.patch.object(module, name, replacement)
                patch.start()
                self.addCleanup(patch.stop)
        device.directory = directory
        device.folder=lambda name:directory/('io-'+name)
        return owner.Session(self.root,directory,device),device

    def test_normal_single_n_observation_physical_a_and_h0_close(self):
        session,device=self.operation();self.assertEqual(session.execute(attended=True)['state'],'AWAITING_PHYSICAL_DOWNLOAD')
        self.assertEqual(device.installed,['N']);device.mode='Download';session.resume(attended=True)
        self.assertEqual(device.installed,['N','A']);self.assertEqual(device.actions.count('mainline-request-once'),1)
        before=list(device.actions);session.repair_close();self.assertEqual(device.actions,before)
        with self.assertRaises(ValueError):session.execute(attended=True)

    @contextmanager
    def malformed_observation(self, device, session):
        folder = device.folder(profile.SELECTION)
        folder.mkdir()
        is_download = download.selected(session.request)
        window = {'opened_ns': 1, 'deadline_ns': 4, 'host_boot': 'fixture',
                  'operation': records.pin(session.directory/'operation.json')}
        records.publish(folder/'window.json', window)
        endpoint = {'interface': 'fixture'}
        records.publish(folder/'endpoint.json', endpoint)
        attempt = records.publish(folder/'attempt.json', {
            'opened_ns': 2, 'deadline_ns': 4, 'nonce': '00'*32,
            'host_boot': 'fixture', 'endpoint': endpoint,
            'request': {'path': None, 'size': 1, 'sha256': '0'*64},
        })
        for label in ('usb-before-connect', 'usb-after-connect', 'usb-after-response',
                      'network-create', 'network-up', 'response', 'prefix'):
            raw.publish_captured_bytes(folder, label, stdout=b'fixture')
        complete = {'attempt': attempt, 'response': records.pin(folder/'response.capture.json'),
                    'finished_ns': 3, 'sent_complete_request': True}
        if is_download:
            records.publish(folder/'base-complete.json', dict(
                complete, prefix=records.pin(folder/'prefix.capture.json'),
                framing='length', descriptor_open=True))
        else:
            records.publish(folder/'connection.json', dict(complete, eof=True, descriptor_closed=True))
        original = device.recover_step_result

        def recover_step(step, request):
            if step.name == profile.SELECTION:
                return Adapter.recover_step_result(device, step, request) if is_download else access.rederive_base(device, request)
            return original(step, request)

        with mock.patch.object(device, 'recover_step_result', side_effect=recover_step), \
             mock.patch.object(profile, 'image_binding', return_value={}), \
             mock.patch.object(profile.codec, 'has_download', return_value=is_download), \
             mock.patch.object(access, 'window_for', return_value=window), \
             mock.patch.object(access, 'endpoint', return_value=endpoint):
            yield

    def test_malformed_observation_allows_only_original_a_recovery(self):
        session, device = self.operation()
        session.execute(attended=True)
        device.mode = 'Download'
        with self.malformed_observation(device, session):
            result = session.recover(attended=True)
        self.assertTrue(result['recovered'])
        self.assertEqual(device.installed, ['N', 'A'])
        self.assertEqual(device.actions.count('mainline-request-once'), 1)

    def test_malformed_ufs_request_allows_only_original_a_recovery(self):
        session, device = self.operation(ufs=True, stop=True)
        self.assertEqual(session.execute(attended=True)['state'], 'AWAITING_ATTENDED_RECOVERY')
        with self.malformed_observation(device, session):
            self.assertTrue(session.recover(attended=True)['recovered'])
        self.assertEqual(device.installed, ['N', 'A'])
        self.assertEqual(device.actions.count('download-control-once'), 1)

    def test_missing_or_broken_marker_codec_cannot_block_a_after_complete_usb(self):
        original_import=builtins.__import__
        for error in (ImportError('missing marker codec'),SyntaxError('broken marker codec')):
            self.setUp();session,device=self.operation()
            self.assertEqual(session.execute(attended=True)['state'],'AWAITING_PHYSICAL_DOWNLOAD')
            self.assertIn(profile.SELECTION,device.proofs);device.mode='Download'
            recover=device.recover_step_result;failed_imports=[]
            def missing(name,globals=None,locals=None,fromlist=(),level=0):
                if name=='mainline.s22plus_canary_h0' and 'retained_marker' in fromlist:
                    failed_imports.append(name);raise error
                return original_import(name,globals,locals,fromlist,level)
            def recover_proof(step,request):
                # The real adapter rederives USB evidence while reconstructing
                # this step, before the remaining normal A steps are probed.
                if step.name==profile.SELECTION:profile.marker_codec()
                return recover(step,request)
            with mock.patch.object(task,'capability',return_value={'fixture':True}),\
                 mock.patch('builtins.__import__',side_effect=missing),\
                 mock.patch.object(device,'recover_step_result',side_effect=recover_proof):
                result=session.recover(attended=True)
                self.assertEqual(result['state'],'ANDROID_CLOSED')
                self.assertEqual(device.installed,['N','A'])
                self.assertEqual(len(failed_imports),1)
                with mock.patch.object(access,'rederive',side_effect=lambda *_:profile.marker_codec()):
                    terminal=mainline.terminal(device,session.request,recovered=True)
                    self.assertEqual(terminal['status'],'NO_PROOF')
                    self.assertTrue(terminal['original_a_return_proved'])

    def test_repair_uses_normal_final_health_when_request_receipt_is_malformed(self):
        session, device = self.operation()
        session.execute(attended=True)
        device.mode = 'Download'
        with mock.patch.object(session, 'close', side_effect=OSError('terminal publication interrupted')):
            with self.assertRaises(OSError):
                session.resume(attended=True)
        previous = list(device.actions)
        with self.malformed_observation(device, session):
            with self.assertRaisesRegex(ValueError, 'needs H0 repair'):
                session.recover(attended=True)
            result = session.repair_close()
        self.assertTrue(result['recovered'])
        self.assertEqual(result['state'], 'ANDROID_CLOSED')
        self.assertEqual(device.actions, previous)
        self.assertEqual(device.installed, ['N', 'A'])
        self.assertFalse((session.directory/'recovery-health.json').exists())
        self.assertIsNone(self.f1)

    def test_repair_uses_final_health_after_malformed_ufs_request(self):
        session, device = self.operation(ufs=True)
        with mock.patch.object(session, 'close', side_effect=OSError('terminal publication interrupted')):
            with self.assertRaisesRegex(OSError, 'terminal publication interrupted'):
                session.execute(attended=True)
        before = list(device.actions)
        with self.malformed_observation(device, session):
            with self.assertRaisesRegex(ValueError, 'needs H0 repair'):
                session.recover(attended=True)
            self.assertTrue(session.repair_close()['recovered'])
        self.assertEqual(device.actions, before)
        self.assertEqual(device.installed, ['N', 'A'])
        self.assertFalse((session.directory/'recovery-health.json').exists())

    def test_interrupted_owner_requires_cue_resolution_before_original_a(self):
        session, device = self.operation()
        session.execute(attended=True)
        original = access.attach
        operation = session.directory
        now = records.clock()
        folder = device.folder(profile.SELECTION)
        folder.mkdir()
        window = records.publish(folder/'window.json', dict(
            operation=records.pin(operation/'operation.json'), host_boot=records.host_boot(),
            opened_ns=now - 1, deadline_ns=now + 60_000_000_000))
        cue = original.issue(operation, window, evidence={}, check=lambda: None)
        with self.assertRaisesRegex(ValueError, 'resolve the issued attach cue'):
            session.recover(attended=True)
        self.assertEqual(device.installed, ['N'])
        self.assertIsNotNone(self.f1)
        original.resolve(operation, window, cue=cue, resolution='cancelled', operator_statement='Cancelled.')
        self.assertEqual(session.recover(attended=True)['state'], 'ANDROID_CLOSED')
        self.assertEqual(device.installed, ['N', 'A'])

    def test_unreviewed_marker_code_is_rejected_before_import(self):
        with mock.patch.object(task,'capability',side_effect=ValueError('source changed')),\
             mock.patch('builtins.__import__',wraps=builtins.__import__) as imports:
            with self.assertRaisesRegex(ValueError,'source changed'):profile.marker_codec()
            self.assertFalse(any(c.args[0]=='mainline.s22plus_canary_h0' for c in imports.call_args_list))

    def test_n_intent_cut_and_partial_observation_only_recover_a(self):
        for fault in ('install-native-first','observation'):
            self.setUp();session,device=self.operation();device.fail_after=fault
            self.assertEqual(session.execute(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
            before=device.actions.count('mainline-request-once');session.recover(attended=True)
            self.assertEqual(device.installed,['N','A']);self.assertEqual(device.actions.count('mainline-request-once'),before)

    def test_missing_observation_publication_rederived_without_request_replay(self):
        session,device=self.operation();original=records.publish
        def fail(path,value):
            if path.name==profile.SELECTION+'.json':raise OSError('publication fixture')
            return original(path,value)
        with mock.patch.object(owner,'publish',fail),self.assertRaises(owner.ResultPublicationError):session.execute(attended=True)
        # A normal resume needs the physical-return request. Recovery reconstructs
        # existing evidence then performs only A; it never contacts the canary.
        session.recover(attended=True);self.assertEqual(device.installed,['N','A'])
        self.assertEqual(device.actions.count('mainline-request-once'),1)

    def test_host_cut_before_observation_cannot_start_observation_on_resume(self):
        session,device=self.operation();step=mainline.normal_steps()[0];session.perform(step)
        session.perform(mainline.normal_steps()[1]);device.mode='Download'
        with self.assertRaises(OSError):session.resume(attended=True)
        session.recover(attended=True);self.assertNotIn('mainline-request-once',device.actions)
        self.assertEqual(device.installed,['N','A'])

    def test_uncertain_a_never_retransfers_and_completed_a_only_rechecks_health(self):
        session,device=self.operation();session.execute(attended=True);device.mode='Download';device.fail_after='install-android'
        session.resume(attended=True)
        with self.assertRaises((ValueError,KeyError)):session.recover(attended=True)
        self.assertEqual(device.installed,['N','A'])
        self.setUp();session,device=self.operation();session.execute(attended=True);device.mode='Download';device.health_failure=True
        session.resume(attended=True);device.health_failure=False;session.recover(attended=True)
        self.assertEqual(device.installed,['N','A'])

    def test_expiry_only_allows_original_recovery_and_cleanup_cannot_block_it(self):
        session,device=self.operation();session.execute(attended=True)
        with mock.patch.object(owner,'clock',return_value=session.grant['deadline_ns']+1):
            with self.assertRaises(ValueError):session.resume(attended=True)
            with mock.patch.object(access,'_cleanup',side_effect=OSError('host only')):
                session.recover(attended=True)
        self.assertEqual(device.installed,['N','A']);self.assertIsNone(self.f1)


class ObserverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        canary.CanaryTests.setUpClass();cls.fixture=canary.CanaryTests()
    @classmethod
    def tearDownClass(cls):canary.CanaryTests.tearDownClass()

    def test_complete_observer_rederives_from_original_raw_without_socket_or_command(self):
        self.complete_observer()

    def test_name_refresh_before_profile_reaches_one_real_socket_and_offline_proof(self):
        self.complete_observer(rename_at_next_census=True)

    def test_ordinary_scm_observer_closes_cue_and_rederives_without_replay(self):
        self.complete_observer(ordinary=True)

    def complete_observer(self,*,rename_at_next_census=False,ordinary=False):
        usb=USBTests();usb.setUp();self.addCleanup(usb.doCleanups)
        initial_name='fixture-pending' if rename_at_next_census else 'lo'
        usb.interface(usb.device(),name=initial_name)
        manifest=copy.deepcopy(self.fixture.manifest)
        manifest['network']=dict(usb.manifest['network'],host_ip='127.0.0.1',device_ip='127.0.0.2',netmask='255.255.255.0')
        manifest['port']=1
        directory=usb.base/'operation';directory.mkdir()
        now=records.clock();launch=records.publish(directory/'launch.json',dict(boottime_ns=now))
        grant=records.publish(directory/'grant.json',dict(host_boot=records.host_boot(),deadline_ns=now+60_000_000_000))
        image = {'schema': profile.SCM_SCHEMA} if ordinary else {'fixture': True}
        request=dict(N=image,grant=grant);records.publish(directory/'operation.json',request)
        class Adapter:
            def __init__(self):self.directory=directory;self.root=ROOT
            def folder(self,name,create=False):
                folder=directory/('io-'+name)
                if create:folder.mkdir()
                return folder
            def recover_transfer_result(self,*_):return {'launch':launch}
            def configuration(self,*_):
                return {'mainline_access':{'uuid':'fixture','name':'fixture'},
                        'review': {'path': str(ROOT/profile.SCM_CUE_REVIEW if ordinary else ROOT/profile.SCM_REVIEW)}}
        adapter=Adapter();created=False
        def command(plan,tool,args,folder,label,**_):
            nonlocal created
            code=0;data=b''
            if label=='addresses-before':data=b'[]'
            elif label=='profile-before':code=10
            elif label=='network-create':created=True
            elif label=='profile-after':
                self.assertTrue(created);data=b'fixture\nfixture\n02:00:00:00:00:01\nlo\n'
            elif label=='route':data=json.dumps([dict(dev='lo',**{'from':'127.0.0.1'})]).encode()
            writer=raw.RawCaptureWriter(folder,label,stdout_maximum=262144,stderr_maximum=16384)
            writer.write_stdout(data);return writer.finalize(returncode=code)
        capture=access.capture_endpoint
        def census(folder,label):
            if rename_at_next_census and label in ('usb-before-configure','usb-before-up') and (usb.net/initial_name).exists():
                (usb.net/initial_name).rename(usb.net/'lo')
            return capture(folder,label,usb_root=usb.usb,net_root=usb.net)
        server=socket.socket();server.bind(('127.0.0.2',0));server.listen(1);server.settimeout(2)
        packet=self.fixture.raw();requests=[]
        def serve():
            try:
                with server.accept()[0] as client:
                    data=b''
                    while len(data)<72:data+=client.recv(72-len(data))
                    requests.append(data);client.sendall(packet)
            finally:server.close()
        thread=threading.Thread(target=serve);thread.start()
        connect=access.capture_connection
        def connection(folder,manifest,found,**options):
            return connect(folder,manifest,found,connect=lambda client:client.connect(server.getsockname()),**options)
        with mock.patch.object(profile,'image_binding',return_value=manifest),\
             mock.patch.object(task,'capability'),\
             mock.patch.object(access,'host_command',side_effect=command),\
             mock.patch.object(access,'capture_endpoint',side_effect=census),\
             mock.patch.object(access,'capture_connection',side_effect=connection),\
             mock.patch.object(access.secrets,'token_bytes',return_value=self.fixture.nonce):
            value=access.observe(adapter,request,lambda:None);thread.join(3)
            self.assertEqual(value['proof']['status'],'AUTHENTICATED_CANARY_OBSERVATION')
            self.assertEqual(len(requests),1)
            if ordinary:
                closure = directory/'mainline-attach-closed.json'
                self.assertEqual(value['attach'], records.pin(closure))
                self.assertIsNone(records.read(closure)['cue'])
            with mock.patch.object(access.socket,'socket',side_effect=AssertionError('replay')),\
                 mock.patch.object(access,'host_command',side_effect=AssertionError('new command')):
                self.assertEqual(access.rederive(adapter,request),value)
                with mock.patch.object(access,'host_boot',return_value='different-host-boot'):
                    self.assertEqual(access.rederive(adapter,request),value)
                folder = adapter.folder(profile.SELECTION)
                attempt = folder/'attempt.json'
                connection = folder/'connection.json'
                original_attempt = records.read(attempt)
                original_connection = records.read(connection)
                damaged = records.read(attempt)
                damaged['request']['path'] = None
                attempt.unlink()
                records.publish(attempt, damaged)
                joined = dict(records.read(connection), attempt=records.pin(attempt))
                connection.unlink()
                records.publish(connection, joined)
                try:
                    with self.assertRaisesRegex(ValueError, 'request receipt path'):
                        access.rederive_base(adapter,request)
                finally:
                    attempt.unlink()
                    connection.unlink()
                    records.publish(attempt, original_attempt)
                    records.publish(connection, original_connection)
                if ordinary:
                    damaged = dict(records.read(closure), closed_ns=None)
                    closure.unlink()
                    records.publish(closure, damaged)
                    with self.assertRaisesRegex(ValueError, 'closure timestamps'):
                        access.rederive(adapter, request)
                    closure.unlink()
                    with self.assertRaises(FileNotFoundError):
                        access.rederive(adapter,request)
                (adapter.folder(profile.SELECTION)/'usb-after-response.capture.json').unlink()
                with self.assertRaises((ValueError,OSError,raw.RawCaptureError)):access.rederive(adapter,request)


class ScopeTests(unittest.TestCase):
    def test_live_grant_still_rejects_host_reboot(self):
        grant=dict(schema=owner.SCHEMA,host_boot='original',opened_ns=1,deadline_ns=100)
        with mock.patch.object(owner,'host_boot',return_value='new'),mock.patch.object(owner,'clock',return_value=2):
            with self.assertRaises(ValueError):owner.live_grant(grant)

    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);(self.root/'workspace/private').mkdir(parents=True)
        self.fixed={'transport':{'odin':{'path':'fixture-odin'}},'rollback':{'ap':{'path':'workspace/private/a','size':1,'sha256':'a'*64}},
            'start_health':{'boot_sha256':'b'*64,'supporting_partition_sha256':{}}}
        self.install=records.publish(self.root/'workspace/private/install.json',dict(uid=task.os.getuid(),
            topology=access.target.lane.CANDIDATE_TOPOLOGY.removeprefix('usb:')))
        self.value=dict(schema='s22plus-mainline-task-v1',target=dict(serial='FIXTURE',topology=access.target.lane.SOURCE_TOPOLOGY),
            lane={},N=dict(profile=profile.PROFILE,runtime_sources={'fixture':'runtime'}),E=None,
            A=dict(ap=dict(self.fixed['rollback']['ap'],path=str(self.root/'workspace/private/a')),partition_sha256={'boot':'b'*64}),
            adb=dict(path=str(Path('/usr/bin/adb').resolve())),odin=self.fixed['transport']['odin'],host_installation=self.install,
            review={'fixture':'review'},recovery_evidence={},operations=[profile.OPERATION],seconds=1800,operation_budget=1,
            recovery_mode='attended',reentry=False,hud=False,usb_reconnect=False,admission=None,prior_terminal=None,
            runtime_scope={'fixture':'runtime'},mainline_access={})
        stack=ExitStack();self.addCleanup(stack.close)
        original=task.read
        stack.enter_context(mock.patch.object(task,'read',side_effect=lambda p:self.fixed if Path(p)==self.root/task.tasks.PROFILE else original(p)))
        for obj,name,value in [(task,'capability',self.value['review']),(task,'validate_access',None),
            (profile,'image_binding',{}),(task.target.lane,'validate_binding',None),(task.tasks,'unchanged',None),
            (task.tasks,'validate_recovery',None)]:stack.enter_context(mock.patch.object(obj,name,return_value=value))

    def test_scope_changes_reject_and_recovery_does_not_need_candidate_or_network_tools(self):
        task.validate_task(self.root,self.value)
        for key,value in [('seconds',1801),('operation_budget',2),('recovery_mode','deferred'),('hud',True),
                          ('E',{}),('operations',['mainline-ram','bootstrap']),('admission',{}),('extra',1)]:
            invalid=copy.deepcopy(self.value);invalid[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):task.validate_task(self.root,invalid)
        with mock.patch.object(profile,'image_binding',side_effect=FileNotFoundError),\
             mock.patch.object(task,'validate_access',side_effect=FileNotFoundError):
            task.validate_task(self.root,self.value,recovery=True)
            with self.assertRaises(FileNotFoundError):task.validate_task(self.root,self.value)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name);self.task=records.publish(self.base/'task.json',dict(fixture=True))
        self.folder=self.base/'ready-fixture';self.folder.mkdir();self.now=records.clock()
        self.health=records.publish(self.folder/'health.json',dict(captures={'fixture':True}))
        writer=raw.RawCaptureWriter(self.folder,'permissions',stdout_maximum=100,stderr_maximum=0)
        writer.write_stdout(b'fixture');self.network=records.pin(writer.finalize(returncode=0).receipt_path)
        self.value=dict(schema='s22plus-mainline-ready-v1',task=self.task,host_boot=records.host_boot(),observed_ns=self.now,
            health=self.health,network_permissions=self.network,device_controls=0,partition_transfers=0)
        self.ready=records.publish(self.folder/'ready.json',self.value)
        self.journal=records.Journal(self.base/'journal');self.journal.append('readiness-complete',result=self.ready)
        self.input={'target':{},'A':{},'N':{'profile':profile.PROFILE}}
        patch=mock.patch.object(task.target,'health_projection',return_value={'captures':{'fixture':True}})
        patch.start();self.addCleanup(patch.stop)

    def test_current_same_host_readiness_requires_actual_preapproval_journal(self):
        task.validate_readiness(self.input,self.ready,self.task,fresh=True)
        with mock.patch.object(task,'clock',return_value=self.now+300_000_000_001):
            with self.assertRaises(ValueError):task.validate_readiness(self.input,self.ready,self.task,fresh=True)
            task.validate_readiness(self.input,self.ready,self.task,fresh=False)
        with mock.patch.object(task,'host_boot',return_value='different'):
            with self.assertRaises(ValueError):task.validate_readiness(self.input,self.ready,self.task,fresh=True)
            task.validate_readiness(self.input,self.ready,self.task,fresh=False)
        (self.base/'journal/0000.json').unlink()
        with self.assertRaises(ValueError):task.validate_readiness(self.input,self.ready,self.task,fresh=True)

    def test_success_label_does_not_replace_raw_health(self):
        with mock.patch.object(task.target,'health_projection',side_effect=ValueError('raw invalid')):
            with self.assertRaises(ValueError):task.validate_readiness(self.input,self.ready,self.task,fresh=True)


if __name__=='__main__':unittest.main()
