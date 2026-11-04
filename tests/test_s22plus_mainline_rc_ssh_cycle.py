"""One rc2 SSH operation on a held base socket; no host network configuration."""
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import socket
import struct
import sys
import threading
import unittest
from unittest import mock

import test_s22plus_mainline_debian_ram as base_tests
from mainline.s22plus_canary_h0 import service_ram as wire,ssh_ram
import device_action_raw_capture_v1 as raw
import s22plus_mainline_access_v1 as access
import s22plus_mainline_download_access_v1 as download
import s22plus_mainline_profile_v1 as profile
import s22plus_mainline_session_v1 as session
import s22plus_native_records_v3 as rec

class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper=base_tests.DebianWireTests();cls.helper.setUpClass();cls.f=cls.helper.fixture
    @classmethod
    def tearDownClass(cls):cls.helper.tearDownClass()

    def run_cycle(self,name):
        f=self.f;operation=f.base/name;operation.mkdir();folder=operation/'io';folder.mkdir()
        found={'interface':'lo'};manifest=self.helper.manifest();manifest.update(network={'host_ip':'127.0.0.1','device_ip':'127.0.0.1'})
        manifest['debian_ram'].update(schema=wire.SCHEMA,keys={})
        body=self.helper.body();body[:8]=b'G0QCRS1\0';struct.pack_into('<III',body,276,3,44,72)
        frame=body+profile.codec.tag(f.key,f.identity,1,body,manifest=manifest)+f.live.read_bytes()
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(5)
        manifest['port']=listener.getsockname()[1];controls=[];errors=[]
        def guest():
            try:
                with listener.accept()[0] as peer:
                    peer.settimeout(5);query=peer.recv(72,socket.MSG_WAITALL)
                    self.assertEqual(query,profile.codec.request(f.key,f.identity,f.nonce,manifest=manifest))
                    peer.sendall(frame);cmd=peer.recv(88,socket.MSG_WAITALL);controls.append(cmd)
                    if cmd:
                        self.assertTrue((folder/'ssh-complete.json').is_file())
                        self.assertTrue((folder/'control-intent.json').is_file())
                        ack=wire.ACK_MAGIC+f.identity+f.nonce+body[72:88]+wire.ACK_FIELDS.pack(
                            99 if name=='other-master' else 44,72,2,6,0,0,0,52,1300,1400)
                        peer.sendall(ack+wire.tag(f.key,f.identity,3,ack));peer.shutdown(socket.SHUT_WR);peer.recv(1)
            except Exception as e:errors.append(repr(e))
            finally:listener.close()
        th=threading.Thread(target=guest);th.start()
        start=rec.clock();deadline=start+12_000_000_000;boot=rec.host_boot()
        grant=rec.publish(operation/'grant.json',dict(host_boot=boot,deadline_ns=deadline+100_000_000))
        request=dict(operation='mainline-ram',N={'debian_ram':{},'download_return':{}},grant=grant)
        op=rec.publish(operation/'operation.json',request);window=dict(operation=op,opened_ns=start,deadline_ns=deadline,host_boot=boot)
        executable=rec.pin(Path(sys.executable).resolve(),maximum=32*1024*1024);plan=dict(ssh=executable)
        adapter=mock.Mock();adapter.directory=operation;adapter.folder.return_value=folder
        adapter.configuration.return_value={'mainline_access':plan}
        journal=rec.Journal(operation/'journal')
        def endpoint(folder,label):return raw.publish_captured_bytes(folder,label,stdout=b'loopback')
        def configure(plan,manifest,found,folder,guard,*,deadline_ns):
            guard();rec.publish(folder/'endpoint.json',found)
            for label in ('network-create','network-up'):endpoint(folder,label)
            return found
        guest_boot='01020304-0506-0708-090a-0b0c0d0e0f10'
        lines=('G0Q_SSH_RAM_V1\nboot_id='+guest_boot+'\nUid: 1000 1000 1000 1000\nGid: 1000 1000 1000 1000\nGroups: 1000\nCapEff: 0000000000000000\n')
        cmd=[executable['path'],'-c','raise SystemExit(9)' if name=='failed-ssh' else 'print('+repr(lines)+',end="")']
        def before_control(detail):journal.append('effect-intent',step=profile.SELECTION,action=download.ACTION,role='N',ending=None,recovery=False,detail=detail())
        with ExitStack() as patches:
            for module,attr,value in ((profile,'image_binding',manifest),(access,'window_for',window),(access,'endpoint',found),
                    (ssh_ram,'known_hosts',b'fixture\n'),(ssh_ram,'command',cmd),(download.secrets,'token_bytes',f.nonce)):
                patches.enter_context(mock.patch.object(module,attr,return_value=value))
            for module,attr,fn in ((access,'configure',configure),(access,'capture_endpoint',endpoint),
                    (access,'host_command',lambda plan,tool,args,folder,label:raw.publish_captured_bytes(folder,label,stdout=json.dumps([{'dev':'lo','from':'127.0.0.1'}]).encode()))):
                patches.enter_context(mock.patch.object(module,attr,side_effect=fn))
            try:
                if name=='complete':
                    value=download.observe(adapter,request,lambda:None,before_control)
                    rec.publish(operation/(profile.SELECTION+'.json'),value);ready=download.return_request(adapter,request,create=True)
                    launch=rec.publish(operation/'launch.json',dict(arrival_deadline_ns=ready['deadline_ns'],boottime_ns=rec.clock(),ticket={'bound':True},revalidation={'A':True}))
                    adapter.recover_transfer_result.return_value=dict(launch=launch,completed=True)
                    terminal=session.terminal(adapter,request,recovered=False)
                    self.assertEqual(terminal['status'],'PASS_DEBIAN_RC_SSH_CYCLE_RAM')
                    self.assertEqual(value['ssh']['uid'],1000);self.assertEqual(value['accepted']['master_pid'],44)
                    adapter.recover_transfer_result.side_effect=OSError('no normal A')
                    self.assertEqual(session.terminal(adapter,request,recovered=True)['status'],'NO_PROOF')
                else:
                    with self.assertRaises((ValueError,raw.RawCaptureError)):
                        download.observe(adapter,request,lambda:None,before_control)
                    result=session.terminal(adapter,request,recovered=True)
                    self.assertEqual(result['status'],'NO_PROOF');self.assertTrue(result['mainline_pid1'])
                    self.assertEqual(bool(result.get('ssh_proved')),name=='other-master')
            finally:th.join(6)
        self.assertFalse(th.is_alive());self.assertFalse(errors,errors)
        self.assertEqual([len(v) for v in controls],[0 if name=='failed-ssh' else 88])
        self.assertEqual(sum(row['event']=='effect-intent' for row in journal.rows()),int(name!='failed-ssh'))

    def test_physical_host_success_and_original_a_required(self):self.run_cycle('complete')
    def test_uncertain_ssh_stops_before_control(self):self.run_cycle('failed-ssh')
    def test_wrong_authenticated_master_keeps_ssh_only(self):self.run_cycle('other-master')

    def test_type_aliases_cannot_select_service_effects(self):
        for key,v in (('control_requests',True),('restart2_calls',1.0),('linux_storage',0),('runlevels',[2.0,6])):
            scope=dict(wire.scope());scope[key]=v
            decl=dict(schema=wire.SCHEMA,package_lock={},observer={},inittab_sha256=hashlib.sha256(wire.INITTAB).hexdigest(),
                members=dict.fromkeys(wire.MEMBERS),keys=dict.fromkeys(ssh_ram.KEY_NAMES),service_cycle=scope)
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'service-cycle scope differs'):
                ssh_ram.validate({'debian_ram':decl,'vm':True},recipe=wire)
