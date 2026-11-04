"""Name selection before the first profile effect; later identity stays exact."""
import copy
import json
from types import SimpleNamespace
import unittest
from unittest import mock

import device_action_raw_capture_v1 as raw
import s22plus_mainline_access_v1 as access
import s22plus_native_records_v3 as records
from test_s22plus_mainline_live_v1 import USBTests


class ConfigurationTests(unittest.TestCase):
    def setUp(self):self.fresh()

    def fresh(self):
        self.usb=USBTests();self.usb.setUp();self.addCleanup(self.usb.doCleanups)
        self.node=self.usb.device();self.net=self.usb.interface(self.node)
        self.folder=self.usb.out;self.manifest=copy.deepcopy(self.usb.manifest)
        self.manifest['network'].update(host_ip='127.0.0.1',device_ip='127.0.0.2',netmask='255.255.255.0')
        self.anchor=access.endpoint(self.usb.capture('initial'),self.manifest)
        self.plan=dict(name='fixture',uuid='fixture');self.profile=None
        self.commands=[];self.captures=[];self.addresses=[];self.guards=0
        self.deadline=records.clock()+30_000_000_000
        self.before_capture=lambda label:None

    def captured(self,folder,label,data=b'',code=0):
        writer=raw.RawCaptureWriter(folder,label,stdout_maximum=16384,stderr_maximum=16384)
        writer.write_stdout(data);return writer.finalize(returncode=code)

    def host(self,plan,tool,args,folder,label,**kwargs):
        self.commands.append((label,args));data=b'';code=0
        if label=='addresses-before':data=json.dumps(self.addresses).encode()
        elif label=='network-create':
            self.assertIsNone(self.profile)
            self.profile=dict(name=args[args.index('con-name')+1],uuid=args[args.index('connection.uuid')+1],
                mac=args[args.index('802-3-ethernet.mac-address')+1],interface=args[args.index('ifname')+1])
        elif label=='network-up':self.assertEqual(args[-1],self.profile['interface'])
        elif label in ('profile-before','profile-after','before','after'):
            if self.profile is None:code=10
            else:data=('\n'.join(self.profile[k] for k in ('name','uuid','mac','interface'))+'\n').encode()
        elif label=='route':data=json.dumps([dict(dev=self.profile['interface'],**{'from':'127.0.0.1'})]).encode()
        elif label=='delete':self.assertIsNotNone(self.profile);self.profile=None
        else:raise AssertionError('unexpected host command '+label)
        return self.captured(folder,label,data,code)

    def census(self,folder,label):
        self.captures.append(label);self.before_capture(label)
        return self.original_capture(folder,label,usb_root=self.usb.usb,net_root=self.usb.net)

    def guard(self):self.guards+=1

    def patches(self):
        from contextlib import ExitStack
        stack=ExitStack()
        self.original_capture=access.capture_endpoint
        stack.enter_context(mock.patch.object(access,'capture_endpoint',side_effect=self.census))
        stack.enter_context(mock.patch.object(access,'host_command',side_effect=self.host))
        for target in ('subprocess.Popen','socket.socket'):
            stack.enter_context(mock.patch(target,side_effect=AssertionError('fixture attempted external effect')))
        stack.enter_context(mock.patch.object(raw,'acquire_command',side_effect=AssertionError('fixture attempted acquisition')))
        return stack

    def rename(self,name):
        renamed=self.net.parent/name;self.net.rename(renamed);self.net=renamed

    def test_name_changes_at_next_census_before_binding_and_all_commands_use_final_name(self):
        def rename_at_next_census(label):
            if self.net.name=='fixture0':self.rename('fixture-final')
        self.before_capture=rename_at_next_census
        with self.patches():final=access.configure(self.plan,self.manifest,self.anchor,self.folder,self.guard,deadline_ns=self.deadline)
        self.assertEqual(final['interface'],'fixture-final')
        self.assertEqual({k:v for k,v in final.items() if k!='interface'},
                         {k:v for k,v in self.anchor.items() if k!='interface'})
        self.assertEqual(records.read(self.folder/'endpoint.json'),final)
        self.assertEqual(records.read(self.folder/'network-intent.json'),dict(plan=self.plan,endpoint=final))
        self.assertEqual(self.profile['interface'],'fixture-final')
        self.assertEqual(sum(label=='network-create' for label,_ in self.commands),1)
        self.assertEqual(self.guards,2)  # Existing create/up guards; no extra settling guard.

    def test_other_identity_changes_absence_or_ambiguity_stop_before_any_intent(self):
        for case in ('ifindex','busnum','devnum','speed','mac','driver','device-path','absent','ambiguous'):
            with self.subTest(case=case):
                self.fresh()
                if case=='ifindex':(self.net/'ifindex').write_text('13\n')
                elif case in ('busnum','devnum','speed'):
                    (self.node/case).write_text({'busnum':'4','devnum':'8','speed':'12'}[case]+'\n')
                elif case=='mac':(self.net/'address').write_text('02:00:00:00:00:02\n')
                elif case=='driver':
                    path=(self.net/'device').resolve()/'driver';path.unlink();other=self.usb.base/'other-driver';other.mkdir();path.symlink_to(other)
                elif case=='device-path':
                    other=self.node/(self.node.name+':1.1');other.mkdir();(other/'driver').symlink_to(self.usb.base/'cdc_ncm')
                    (self.net/'device').unlink();(self.net/'device').symlink_to(other)
                elif case=='absent':self.node.rename(self.node.parent/'absent-fixture')
                else:
                    other=self.net.parent/'fixture-extra';other.mkdir();(other/'device').symlink_to((self.net/'device').resolve())
                    for field in ('address','ifindex'):(other/field).write_text((self.net/field).read_text())
                with self.patches(),self.assertRaises(ValueError):
                    access.configure(self.plan,self.manifest,self.anchor,self.folder,self.guard,deadline_ns=self.deadline)
                self.assertIsNone(self.profile)
                self.assertFalse((self.folder/'endpoint.json').exists())
                self.assertFalse((self.folder/'network-intent.json').exists())
                self.assertFalse(any(label=='network-create' for label,_ in self.commands))

    def test_guard_failure_before_binding_does_not_publish_or_create(self):
        def expired():raise ValueError('original window expired')
        with self.patches(),self.assertRaisesRegex(ValueError,'original window expired'):
            access.configure(self.plan,self.manifest,self.anchor,self.folder,expired,deadline_ns=self.deadline)
        self.assertFalse(self.captures);self.assertIsNone(self.profile)
        self.assertFalse((self.folder/'endpoint.json').exists())
        self.assertFalse((self.folder/'network-intent.json').exists())

    def test_name_change_after_creation_still_stops_and_cleanup_deletes_owned_profile_once(self):
        self.before_capture=lambda label:self.rename('fixture-late') if label=='usb-before-up' else None
        with self.patches():
            with self.assertRaisesRegex(ValueError,'NCM changed before activation'):
                access.configure(self.plan,self.manifest,self.anchor,self.folder,self.guard,deadline_ns=self.deadline)
            self.assertFalse(any(label=='network-up' for label,_ in self.commands))
            adapter=SimpleNamespace(folder=lambda name:self.folder,configuration=lambda request:dict(mainline_access=self.plan))
            self.assertEqual(access.cleanup(adapter,{}),dict(status='REMOVED',device_recovery_blocked=False))
            self.assertEqual(access.cleanup(adapter,{}),dict(status='ALREADY_ABSENT',device_recovery_blocked=False))
        self.assertEqual(sum(label=='delete' for label,_ in self.commands),1)

    def test_deadline_expiring_during_publication_never_creates_profile(self):
        now=1;publish=access.publish
        def delayed_publish(path,value):
            nonlocal now
            receipt=publish(path,value)
            if path.name=='network-intent.json':now=10
            return receipt
        with self.patches(),mock.patch.object(access,'clock',side_effect=lambda:now),\
             mock.patch.object(access,'publish',side_effect=delayed_publish),\
             self.assertRaisesRegex(ValueError,'expired before profile creation'):
            access.configure(self.plan,self.manifest,self.anchor,self.folder,self.guard,deadline_ns=10)
        self.assertIsNone(self.profile)
        self.assertTrue((self.folder/'network-intent.json').exists())
        self.assertFalse(any(label=='network-create' for label,_ in self.commands))

    def test_address_conflict_excludes_own_index_not_another_interface_with_old_name(self):
        own=dict(ifname='fixture-final',ifindex=self.anchor['ifindex'],addr_info=[dict(family='inet',local='127.0.0.1',prefixlen=24)])
        same=raw.publish_captured_bytes(self.folder,'same-index',stdout=json.dumps([own]).encode(),stderr=b'')
        self.assertTrue(access.network_conflicts(same,self.manifest,own_ifindex=self.anchor['ifindex']))
        foreign=dict(own,ifname=self.anchor['interface'],ifindex=self.anchor['ifindex']+1)
        conflict=raw.publish_captured_bytes(self.folder,'foreign-old-name',stdout=json.dumps([own,foreign]).encode(),stderr=b'')
        with self.assertRaisesRegex(ValueError,'conflicts'):
            access.network_conflicts(conflict,self.manifest,own_ifindex=self.anchor['ifindex'])
        with self.assertRaisesRegex(ValueError,'conflicts'):access.network_conflicts(same,self.manifest)
        boolean=dict(own,ifindex=True)
        invalid=raw.publish_captured_bytes(self.folder,'boolean-index',stdout=json.dumps([boolean]).encode(),stderr=b'')
        with self.assertRaisesRegex(ValueError,'conflicts'):access.network_conflicts(invalid,self.manifest,own_ifindex=1)


if __name__=='__main__':unittest.main()
