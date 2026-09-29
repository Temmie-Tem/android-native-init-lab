"""Exact NCM identity, pinned SSH health and one fixed shutdown for V3.

Pure proof parsing is separated from the bounded I/O. No first-boot installer,
legacy owner, arbitrary SSH command, package operation or reboot is imported.
"""
import os
from pathlib import Path
import re
import time
import uuid
import device_action_raw_capture_v1 as raw
import s22plus_native_target_io_v3 as target
import s22plus_debian_usb_observation_v1 as usb
from s22plus_native_records_v3 import clock,digest,pin,publish,read,require,verify


def inputs(run):
    from s22plus_native_root_inspect_profile_v1 import prior_inputs
    artifact,_,previous=prior_inputs()
    value={name:previous[name] for name in ('link','client_key','known_hosts','ssh')}
    for name in ('client_key','known_hosts','ssh'):verify(value[name],maximum=32*1024*1024)
    # nmcli belongs to this host preparation, not the historical rootfs. Pin
    # its current fixed path now; a later change rejects the immutable task.
    value['nmcli']=pin(Path('/usr/bin/nmcli').resolve(strict=True),maximum=32*1024*1024)
    return dict(value,root_run_id=artifact['run_id'],
        network_uuid=str(uuid.uuid5(uuid.UUID(hex=run),'s22-debian-handoff-v1')))


def health_projection(handle,plan,*,boot_sha256):
    raw.require_success(handle)
    require(not raw.read_stderr(handle,maximum=16384),'Debian health has diagnostics')
    output=raw.read_stdout(handle,maximum=65536);candidate=plan['candidate']
    marker=('BOOTSTRAP_CANDIDATE '+candidate['namespace']+' '+candidate['version']+' '+candidate['run_id']+'\n').encode()
    require(output.startswith(('S22PLUS_FYG8_DEBIAN_V1 '+plan['root_run_id']+'\n').encode()) and
        output.endswith(b'DEBIAN_HEALTH_PASS\n') and output.count(marker)==output.count(b'BOOTSTRAP_CANDIDATE ')==1 and
        output.count(b'pid1_exe=/usr/sbin/init\n')==output.count(b'pid1_root=/\n')==1 and
        output.count(b'BOOTSTRAP_HANDOFF pid=1 children=0 backend=s22plus-fyg8\n')==1 and
        b'DEBIAN_INSTALL_INTENT_DURABLE' not in output and b'DEBIAN_INSTALL_COMPLETE' not in output,
        'Debian SSH root/PID1/candidate identity differs')
    boots=re.findall(rb'^boot_id=([0-9a-f-]{36})$',output,re.M)
    counts=re.findall(rb'^boot_count=([1-9][0-9]*)$',output,re.M)
    require(len(boots)==len(counts)==1 and target.UUID.fullmatch(boots[0].decode()) and int(counts[0])<=100000 and
        digest(boots[0])==boot_sha256,'SSH does not join the authenticated native kernel boot')
    return dict(status='PASS_INSTALLED_DEBIAN_SSH',boot_id_sha256=digest(boots[0]),boot_count=int(counts[0]),
        capture=pin(handle.receipt_path),root_run_id=plan['root_run_id'])


def shutdown_projection(handle,address):
    require(not handle.timed_out and not handle.output_exceeded and handle.producer_error_type is None,
        'Debian shutdown producer failed')
    stdout,stderr=raw.read_stdout(handle,maximum=65536),raw.read_stderr(handle,maximum=16384)
    require(stdout==b'DEBIAN_SHUTDOWN_REQUEST_ACCEPTED\n' and
        ((handle.returncode==0 and not stderr) or (handle.returncode==255 and
        stderr==('Connection to '+address+' closed by remote host.\r\n').encode())),
        'fixed Debian shutdown was not acknowledged')
    return dict(dispatch_capture=pin(handle.receipt_path),request_accepted=True,clean_shutdown_proved=False)


def endpoint(wanted):
    matches=[]
    for ordinal,interface in enumerate(Path('/sys/class/net').iterdir(),1):
        require(ordinal<=128,'network interface inventory exceeds bound')
        try:
            if (interface/'address').read_text().strip()!=wanted['host_mac']:continue
            device=(interface/'device').resolve(strict=True)
            for topology in (target.lane.SOURCE_TOPOLOGY,target.lane.CANDIDATE_TOPOLOGY):
                node=Path('/sys/bus/usb/devices')/topology.removeprefix('usb:')
                try:parent=node.resolve(strict=True)
                except FileNotFoundError:continue
                if not device.is_relative_to(parent):continue
                fields={name:target.sysfs_field(node,name) for name in usb.FIELDS}
                require(all(fields[name]==value for name,value in dict(idVendor='1d6b',idProduct='0104',
                    serial=wanted['serial'],product='S22 Debian research').items()),'Debian NCM descriptor differs')
                matches.append(dict(interface=interface.name,topology=topology,fields=fields))
        except FileNotFoundError:continue
    require(len(matches)<=1,'Debian NCM endpoint ambiguous')
    return matches[0] if matches else None


class Access:
    def __init__(self,adapter,request):
        self.adapter,self.request=adapter,request
        self.task=adapter.configuration(request);self.plan=dict(self.task['debian_access'])
        image=request['N'];self.plan['candidate']=dict(namespace=image['namespace'],version=image['version'],run_id=image['run_id_hex'])
        self.grant=read(verify(request['grant']))

    def host(self,args,folder,label):
        tool=self.plan['nmcli'];verify(tool,maximum=32*1024*1024)
        handle=raw.acquire_command([tool['path'],*args],folder,label,timeout=30,
            stdout_maximum=16384,stderr_maximum=16384,env=dict(os.environ,LC_ALL='C',LANG='C'))
        raw.require_success(handle);return pin(handle.receipt_path)

    def ssh(self,command,folder,label,found,guard,*,before=None):
        require(command in ('health','shutdown'),'SSH command outside fixed handoff scope')
        guard();require(endpoint(self.plan['link'])==found,'SSH endpoint changed')
        for name in ('ssh','client_key','known_hosts'):verify(self.plan[name],maximum=32*1024*1024)
        args=[self.plan['ssh']['path'],'-F','/dev/null','-i',self.plan['client_key']['path'],
            '-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes',
            '-o','UserKnownHostsFile='+self.plan['known_hosts']['path'],'-o','GlobalKnownHostsFile=/dev/null',
            '-o','LogLevel=ERROR','-o','ConnectTimeout=3','-o','ConnectionAttempts=1',
            '-o','ServerAliveInterval=5','-o','ServerAliveCountMax=1',
            '-b',self.plan['link']['host_address'].split('/')[0],'root@'+self.plan['link']['ssh_address'],command]
        if before is not None:before()
        return raw.acquire_command(args,folder,label,timeout=20,stdout_maximum=65536,stderr_maximum=16384)

    def handoff(self):
        from s22plus_native_observation_v3 import rederive
        return rederive(self.adapter.folder('debian-handoff'),self.request['N'],ending='handoff',hud=False,
            first_boot=True,profile='debian-handoff')['proof']

    def health(self,step,guard):
        proof=self.handoff();folder=self.adapter.folder(step.name,create=True)
        deadline=min(self.grant['deadline_ns'],clock()+180_000_000_000)
        publish(folder/'window.json',dict(opened_ns=clock(),deadline_ns=deadline,handoff=pin(self.adapter.folder('debian-handoff')/'attempt.json')))
        found=None
        for ordinal in range(1,181):
            guard();require(clock()<deadline,'Debian NCM arrival expired')
            usb.capture(folder,ordinal,self.plan['link']);found=endpoint(self.plan['link'])
            if found:break
            time.sleep(1)
        require(found is not None,'Debian NCM did not arrive')
        publish(folder/'endpoint.json',found)
        connection=self.plan['network_uuid']
        publish(folder/'network-intent.json',dict(uuid=connection,endpoint=found))
        self.host(['connection','add','save','no','type','ethernet','con-name','s22-debian-'+self.plan['candidate']['run_id'],
            'ifname',found['interface'],'connection.uuid',connection,'connection.autoconnect','no',
            '802-3-ethernet.mac-address',self.plan['link']['host_mac'],'ipv4.method','manual',
            'ipv4.addresses',self.plan['link']['host_address'],'ipv4.never-default','yes','ipv6.method','disabled'],folder,'network-create')
        guard();require(endpoint(self.plan['link'])==found,'NCM changed before activation')
        self.host(['connection','up','uuid',connection,'ifname',found['interface']],folder,'network-up')
        require(endpoint(self.plan['link'])==found,'NCM changed during activation')
        for ordinal in range(1,181):
            guard();require(clock()<deadline,'Debian SSH health expired')
            handle=self.ssh('health',folder,f'health-{ordinal:03d}',found,guard)
            if handle.returncode==0 and not handle.timed_out and not handle.output_exceeded and handle.producer_error_type is None:
                health=health_projection(handle,self.plan,boot_sha256=proof['kernel_boot_proof'])
                require(endpoint(self.plan['link'])==found,'NCM changed during authenticated health')
                result=dict(action='debian-health',health=health,endpoint=pin(folder/'endpoint.json'),
                    observed_ns=clock(),window=pin(folder/'window.json'))
                publish(folder/'result.json',result);return result
            time.sleep(1)
        raise TimeoutError('Debian health sample bound exhausted')

    def shutdown(self,step,guard,before):
        health=self.rederive_health();found=read(verify(health['endpoint']));folder=self.adapter.folder(step.name,create=True)
        snapshot=target.usb_snapshot(found['topology'],folder);publish(folder/'before.json',snapshot)
        detail=dict(endpoint=health['endpoint'],before=pin(folder/'before.json'),deadline_ns=clock()+90_000_000_000)
        def dispatch():
            guard();require(endpoint(self.plan['link'])==found,'NCM changed at shutdown dispatch')
            publish(folder/'intent.json',detail);before(detail)
        handle=self.ssh('shutdown',folder,'shutdown',found,guard,before=dispatch)
        accepted=shutdown_projection(handle,self.plan['link']['ssh_address'])
        departed=target.wait_departure(snapshot,folder,deadline_ns=detail['deadline_ns'],guard=guard)
        publish(folder/'departure.json',departed)
        value=dict(action='debian-shutdown',accepted=accepted,departure=pin(folder/'departure.json'),
            clean_shutdown_proved=False)
        publish(folder/'result.json',value);cleanup(self.adapter,self.request);return value

    def cleanup(self):
        """Only our recorded UUID/name/MAC/interface; host failure never gates A."""
        folder=self.adapter.folder('debian-health');intent=folder/'network-intent.json'
        if not intent.exists():return dict(status='NOT_CREATED')
        output=folder/('cleanup-'+uuid.uuid4().hex);output.mkdir(mode=0o700)
        try:
            selected=read(intent);connection=self.plan['network_uuid']
            require(selected['uuid']==connection and selected['endpoint']==read(folder/'endpoint.json'),
                'host cleanup has no original exact network intent')
            tool=self.plan['nmcli'];verify(tool,maximum=32*1024*1024)
            command=[tool['path'],'--escape','no','-g',
                'connection.id,connection.uuid,802-3-ethernet.mac-address,connection.interface-name',
                'connection','show','uuid',connection]
            def inspect(label):
                handle=raw.acquire_command(command,output,label,timeout=15,stdout_maximum=16384,stderr_maximum=16384,
                    env=dict(os.environ,LC_ALL='C',LANG='C'))
                require(not handle.timed_out and not handle.output_exceeded and handle.producer_error_type is None,
                    'host cleanup inspection incomplete')
                stdout=raw.read_stdout(handle,maximum=16384)
                if handle.returncode==10 and not stdout:return False
                raw.require_success(handle);rows=stdout.decode('ascii').splitlines()
                require(len(rows)==4 and rows[:2]==['s22-debian-'+self.plan['candidate']['run_id'],connection] and
                    rows[2].lower()==self.plan['link']['host_mac'] and rows[3]==selected['endpoint']['interface'],
                    'cleanup UUID now belongs to another host connection')
                return True
            existed=inspect('before')
            if existed:
                self.host(['connection','delete','uuid',connection],output,'delete')
                require(not inspect('after'),'owned host connection still exists')
            result=dict(status='REMOVED' if existed else 'ALREADY_ABSENT',intent=pin(intent),device_actions=0)
        except (ValueError,OSError,KeyError,TypeError,raw.RawCaptureError) as error:
            result=dict(status='HOST_CLEANUP_UNPROVED',error_type=type(error).__name__,message=str(error)[:256],
                original_A_recovery_blocked=False,device_actions=0)
        publish(output/'result.json',result);return result


    def rederive_health(self):
        folder=self.adapter.folder('debian-health');value=read(folder/'result.json');proof=self.handoff()
        require(value['action']=='debian-health' and value['endpoint']==pin(folder/'endpoint.json') and
            value['window']==pin(folder/'window.json'),'Debian health receipt location differs')
        require(health_projection(raw.load_handle(verify(value['health']['capture'])),self.plan,
            boot_sha256=proof['kernel_boot_proof'])==value['health'],'Debian health raw proof differs')
        window=read(verify(value['window']))
        require(window['opened_ns']<value['observed_ns']<window['deadline_ns'] and
            window['deadline_ns']<=self.grant['deadline_ns'],'Debian health did not finish in its original window')
        found=read(verify(value['endpoint']))
        require(all(found['fields'][name]==v for name,v in dict(idVendor='1d6b',idProduct='0104',
            serial=self.plan['link']['serial'],product='S22 Debian research').items()) and
            found['topology'] in (target.lane.SOURCE_TOPOLOGY,target.lane.CANDIDATE_TOPOLOGY),'retained NCM identity differs')
        raw.require_success(raw.load_handle(folder/'network-create.capture.json'))
        raw.require_success(raw.load_handle(folder/'network-up.capture.json'))
        return value

    def rederive_shutdown(self):
        folder=self.adapter.folder('debian-shutdown');health=self.rederive_health();intent=read(folder/'intent.json')
        require(intent['endpoint']==health['endpoint'],'shutdown does not join original SSH health')
        value=dict(action='debian-shutdown',accepted=shutdown_projection(raw.load_handle(folder/'shutdown.capture.json'),
            self.plan['link']['ssh_address']),departure=pin(folder/'departure.json'),clean_shutdown_proved=False)
        departure=read(verify(value['departure']))
        require(departure['departed'] is True and departure['before']==read(verify(intent['before'])) and
            departure['deadline_ns']==intent['deadline_ns'] and departure['observed_ns']<intent['deadline_ns'],
            'shutdown departure does not join original dispatch')
        return value

def cleanup(adapter,request):
    # A reporting/disk error here must not turn a local cleanup into another
    # device-health prerequisite or reopen a closed operation.
    try:return Access(adapter,request).cleanup()
    except (ValueError,OSError,KeyError,TypeError,raw.RawCaptureError) as error:
        return dict(status='HOST_CLEANUP_UNPROVED',error_type=type(error).__name__,original_A_recovery_blocked=False)
