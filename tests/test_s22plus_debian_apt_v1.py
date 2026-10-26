"""APT proof ordering, exact state selection and one-shot authenticated time handoff."""
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_debian_apt_v1 as spec
import s22plus_debian_apt_access_v1 as access
import s22plus_debian_evidence_v1 as evidence
import s22plus_debian_autoboot_profile_v1 as profile
from s22plus_native_records_v3 import clock,publish,read
from test_s22plus_debian_cron_config_v1 import DurableConfiguration


class AptChain(unittest.TestCase):
    key=b'K'*32
    def rows(self,phase):
        rows=DurableConfiguration().rows(phase)
        rows.insert(11,(15,1101,phase,1,1800000000,123,5))
        end=rows[-1][1];extra=[]
        if phase==1:extra.append((16,end,1,1,140421,20656989,57900))
        extra.extend(((13,end,phase,phase,10,64,0),(14,end,phase,phase,777,0,64)))
        rows[-1:-1]=extra
        return rows
    def consume(self,rows,phase,*,apt=True):
        chain=evidence.Chain(b'T'*32,autoboot=True,single_cpu=True,reboot=dict(phase=phase,initial_mount_count=38),
            cron_config=True,download=True,package=True,apt=apt)
        for seq,(kind,ms,p,event,a,b,c) in enumerate(rows):
            data=bytearray(128);data[:8]=b'S22DER1\0'
            struct.pack_into('<IIQIIQQQII',data,8,seq,kind,ms,p,event,a,b,c,0,0)
            data[64:96]=chain.tag
            data[96:]=evidence.tag(self.key,data[:96],autoboot=True,reboot=True,cron_config=True,download=True,package=True,apt=apt)
            chain.append(bytes(data),self.key)
        return chain
    def test_install_and_second_boot_require_clock_but_only_first_acquires(self):
        for phase in (1,2):
            rows=self.rows(phase);chain=self.consume(rows,phase)
            self.assertTrue(chain.complete);self.assertIsNotNone(chain.apt_clock)
            self.assertEqual(chain.apt_acquired is not None,phase==1)
            for kind in (15,13,14)+((16,) if phase==1 else ()):
                with self.subTest(phase=phase,kind=kind),self.assertRaises(ValueError):
                    self.consume([r for r in rows if r[0]!=kind],phase)
    def test_duplicate_clock_wrong_time_and_second_acquisition_fail(self):
        rows=self.rows(1);at=11
        cases=[rows[:at]+[rows[at]]+rows[at:]]
        for index,value in ((2,2),(4,0),(5,1000000000),(6,20001)):
            changed=list(rows);row=list(changed[at]);row[index]=value;changed[at]=tuple(row);cases.append(changed)
        for case in cases:
            with self.assertRaises(ValueError):self.consume(case,1)
        rows=self.rows(2);rows.insert(-3,(16,rows[-1][1],2,1,140421,20656989,57900))
        with self.assertRaises(ValueError):self.consume(rows,2)
        with self.assertRaises(ValueError):self.consume(self.rows(1),1,apt=False)
    def test_prior_package_state_and_variant_remain_separate(self):
        selected=dict(transition_observer=profile.APT_OBSERVER)
        self.assertEqual(profile.cron_selected(selected),'apt')
        self.assertIs(profile.package_variant(selected),spec)
        data=read(spec.FILES);old=read(spec.previous.FILES)
        self.assertEqual(len(data['rows']),64)
        for prior in old['rows']:
            row=next(r for r in data['rows'] if r['path']==prior['path'])
            self.assertTrue(row['existing']);self.assertEqual(row['before_sha256'],prior['sha256'])
        config=spec.apt_config()
        for value in (b'Dpkg::Use-Pty "false"',b'Acquire::Check-Date "true"',b'Acquire::https::Verify-Peer "true"'):
            self.assertIn(value,config)
        self.assertNotIn(b'AllowUnauthenticated',config)


class ClockHandoff(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.directory=Path(temporary.name)
        publish(self.directory/'operation.json',dict(operation='fixture'))
        self.folder=self.directory/'health';self.folder.mkdir()
        self.client=types.SimpleNamespace(request=dict(operation='debian-autoboot',N=dict(namespace='p463')),
            reboot_phase=1,adapter=types.SimpleNamespace(directory=self.directory))
        self.commands=[];self.lost=False;self.wrong=False
        def ssh(command,folder,label,*args,**kw):
            self.commands.append(command)
            if command=='apt-time-status' and not (folder/'clock-intent.json').exists():
                values=dict(stdout=b'S22_APT_CLOCK_READY\n',returncode=75)
            elif command.startswith('apt-time '):
                values=dict(stdout=b'',stderr=b'connection lost\n',returncode=255) if self.lost else dict(stdout=b'S22_APT_CLOCK_REQUESTED\n')
            else:
                intent=read(folder/'clock-intent.json');phase,boot,sec,ns=intent['command'].split()[1:]
                if self.wrong:boot='b'*64
                values=dict(stdout=f'S22_APT_CLOCK_V1 {phase} {boot} {sec} {ns} 1000 1002 1003 {sec} {ns}\n'.encode())
            return access.raw.publish_captured_bytes(folder,label,**values)
        self.client.ssh=ssh
    def run_handoff(self):
        basis=dict(deadline_ns=clock()+360_000_000_000);self.client.basis=lambda:basis
        if not (self.folder/'window.json').exists():publish(self.folder/'window.json',dict(basis=basis,opened_ns=clock()))
        access.handoff(self.client,self.folder,{},lambda:None,basis['deadline_ns'],
            dict(health=dict(boot_id_sha256='a'*64)))
    def test_lost_response_is_resolved_only_by_status(self):
        self.lost=True;self.run_handoff();result=read(self.folder/'clock.json')
        self.assertFalse(result['acknowledged']);self.assertEqual(len([c for c in self.commands if c.startswith('apt-time ')]),1)
        request=read(self.folder/'clock-intent.json');sec,ns=divmod(request['utc_ns'],1000000000)
        proof=dict(kernel_boot_identity_sha256='a'*64,runtime=dict(apt=dict(clock=dict(a=sec,b=ns,c=3))))
        self.assertEqual(access.rederive(self.client,self.folder,proof),result)
    def test_wrong_boot_and_duplicate_intent_never_repeat_a_request(self):
        self.wrong=True
        with self.assertRaises(ValueError):self.run_handoff()
        self.assertFalse((self.folder/'clock.json').exists())
        before=len(self.commands)
        with self.assertRaises(ValueError):self.run_handoff()
        self.assertEqual(len([c for c in self.commands if c.startswith('apt-time ')]),1)
        self.assertLessEqual(len(self.commands)-before,1)
    def test_fixed_grammar_rejects_extra_commands_wrong_phase_and_wrong_namespace(self):
        request=self.client.request;valid='apt-time 1 '+'a'*64+' 1800000000 0'
        self.assertTrue(access.command_allowed(request,1,valid))
        for bad in (valid+'; reboot',valid+' extra',valid.replace(' 0',' 1000000000'),valid.replace('1800000000','0')):
            self.assertFalse(access.command_allowed(request,1,bad))
        self.assertFalse(access.command_allowed(request,2,valid))
        self.assertFalse(access.command_allowed(dict(request,N=dict(namespace='p462')),1,valid))

    def test_rederived_clock_cannot_renew_the_original_window(self):
        self.run_handoff();intent=read(self.folder/'clock-intent.json');sec,ns=divmod(intent['utc_ns'],1000000000)
        proof=dict(kernel_boot_identity_sha256='a'*64,runtime=dict(apt=dict(clock=dict(a=sec,b=ns,c=3))))
        self.client.basis=lambda:dict(deadline_ns=intent['deadline_ns']+1)
        with self.assertRaises(ValueError):access.rederive(self.client,self.folder,proof)


class SharedNetwork(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.directory=Path(temporary.name)
        self.folder=self.directory/'debian-health';self.folder.mkdir()
        self.found=dict(interface='fixture-usb');publish(self.folder/'endpoint.json',self.found)
        address=access.ipaddress.ip_interface((3221225985,24))  # Synthetic documentation subnet.
        self.client=types.SimpleNamespace(request=dict(operation='debian-autoboot',N=dict(namespace='p463')),
            reboot_phase=1,plan=dict(network_uuid='11111111-1111-4111-8111-111111111111',
                candidate=dict(run_id='a'*32),link=dict(host_mac='02:00:00:00:00:01',host_address=str(address))),
            adapter=types.SimpleNamespace(folder=lambda name:self.directory/name),
            cleanup_folder=lambda:self.folder,cleanup_interfaces=lambda value:[self.found['interface']])
        self.calls=[];self.exists=False;self.active=False;self.foreign=False;self.bad_owner=False;self.changed_dns=False
        def host(args,folder,label):
            self.calls.append((label,args));output=b''
            if label=='network-inventory':output=((self.client.plan['network_uuid']+':802-3-ethernet\n') if self.exists else '').encode()
            elif label in ('network-before','network-pre-up','network-after','before'):
                rows=access.network_rows(self.client,self.found['interface'])
                if self.bad_owner:rows[5]='manual'
                output=('\n'.join(rows)+'\n').encode()
            elif label=='network-device-before':output=b'foreign\n' if self.foreign else b'\n'
            elif label=='network-create':self.exists=True
            elif label=='network-up':self.active=True
            elif label in ('inventory-before','inventory-after'):output=(self.client.plan['network_uuid']+'\n').encode() if self.exists else b''
            elif label.startswith('active-'):output=(self.client.plan['network_uuid']+'\n').encode() if self.active else b''
            elif label=='down':self.active=False
            elif label=='delete':self.exists=False
            return access.pin(access.raw.publish_captured_bytes(folder,label,stdout=output).receipt_path)
        self.client.host=host
        def snapshot(client,folder,label):
            for kind in ('addresses','routes'):access.raw.publish_captured_bytes(folder,label+'-'+kind,stdout=b'[]')
            resolver=b'changed' if self.changed_dns and label.endswith('after') else b'original'
            access.raw.publish_captured_bytes(folder,label+'-resolver',stdout=resolver)
            value=access.decode_host_snapshot(folder,label)
            publish(folder/(label+'.json'),value);return value
        self.snapshot=mock.patch.object(access,'host_snapshot',side_effect=snapshot);self.snapshot.start();self.addCleanup(self.snapshot.stop)
        import s22plus_debian_access_v1 as base
        endpoint=mock.patch.object(base,'endpoint',return_value=self.found);endpoint.start();self.addCleanup(endpoint.stop)

    def configure(self):access.configure_network(self.client,self.folder,self.found,lambda:None)

    def test_fresh_share_exact_rebind_and_owned_retirement(self):
        self.configure();access.network_result(self.client,self.folder)
        self.assertIn('shared',next(args for label,args in self.calls if label=='network-create'))
        self.client.reboot_phase=2;self.folder=self.directory/'debian-health-second';self.folder.mkdir()
        publish(self.folder/'endpoint.json',self.found);self.configure();access.network_result(self.client,self.folder)
        self.assertEqual(sum(label=='network-create' for label,_ in self.calls),1)
        self.assertEqual(sum(label=='network-rebind' for label,_ in self.calls),1)
        result=access.cleanup_network(self.client)
        self.assertEqual(result['status'],'REMOVED');self.assertTrue(result['owned_profile_and_activation_absent'])
        self.assertFalse(result['networkmanager_managed_rules_independently_observed'])
        self.assertLess([label for label,_ in self.calls].index('down'),[label for label,_ in self.calls].index('delete'))

    def test_foreign_owner_fails_before_creation(self):
        self.foreign=True
        with self.assertRaises(ValueError):self.configure()
        self.assertFalse(self.exists);self.assertFalse((self.folder/'network-intent.json').exists())

    def test_host_resolver_change_is_rejected_and_cleanup_checks_all_fields(self):
        self.changed_dns=True
        with self.assertRaises(ValueError):self.configure()
        self.bad_owner=True;result=access.cleanup_network(self.client)
        self.assertEqual(result['status'],'HOST_CLEANUP_UNPROVED')
        self.assertFalse(result['original_A_recovery_blocked']);self.assertTrue(self.exists)
        self.assertNotIn('delete',[label for label,_ in self.calls])


if __name__=='__main__':unittest.main()
