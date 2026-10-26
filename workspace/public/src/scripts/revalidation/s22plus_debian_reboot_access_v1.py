"""Two finite boot observations under one owner; control intents never replay."""
import re

import s22plus_debian_access_v1 as base
import s22plus_debian_autoboot_protocol_v1 as protocol
import s22plus_debian_reboot_v1 as spec
import s22plus_debian_cron_v1 as cron_spec
import s22plus_debian_cron_config_v1 as cron_config_spec
import s22plus_debian_download_v1 as download_spec
import s22plus_debian_package_v1 as package_spec
import s22plus_debian_apt_v1 as apt_spec
from s22plus_debian_autoboot_access_v1 import Access as AutomaticAccess
from s22plus_native_records_v3 import Journal,clock,pin,publish,read,require,verify


def selected(request):
    image=request.get('N') or {}
    return request.get('operation')=='debian-autoboot' and image.get('namespace') in (spec.NAMESPACE,cron_spec.NAMESPACE,cron_config_spec.NAMESPACE,download_spec.NAMESPACE,package_spec.NAMESPACE,apt_spec.NAMESPACE)


def download_selected(request):
    return selected(request) and request['N'].get('namespace') in (download_spec.NAMESPACE,package_spec.NAMESPACE,apt_spec.NAMESPACE)


def control_step(command):return 'debian-shutdown' if command=='download' else 'debian-'+command


def return_request(adapter,request,*,create=False):
    require(download_selected(request),'unselected automatic Download return')
    selected=Access(adapter,request,phase=2)
    control=selected.rederive_control('download');folder=adapter.folder('debian-shutdown')
    intent=read(folder/'intent.json')
    rows=[r for r in Journal(adapter.directory/'journal').rows() if r['event']=='effect-intent' and
        r['data']['step']=='debian-shutdown']
    require(len(rows)==1 and rows[0]['data']['action']=='debian-shutdown' and
        rows[0]['data']['role']=='N' and rows[0]['data']['detail']==intent and
        read(adapter.directory/'debian-shutdown.json')==control,'Download return lacks original completed control')
    expected=dict(operation=pin(adapter.directory/'operation.json'),
        shutdown=pin(adapter.directory/'debian-shutdown.json'),intent=pin(folder/'intent.json'),
        mode='AUTOMATIC_DOWNLOAD',requested_ns=intent['dispatch_ns'],deadline_ns=intent['deadline_ns'])
    path=adapter.directory/'debian-return-ready.json'
    if create and not path.exists():publish(path,expected)
    require(read(path)==expected,'Download return deadline or original intent differs')
    return expected


def normal_steps():
    from s22plus_native_session_v3 import Step
    return (Step('android-download','download','A'),Step('install-native-first','transfer','N'),
        Step('debian-health','debian-health','N'),Step('debian-reboot','debian-reboot','N'),
        Step('debian-health-second','debian-health','N'),Step('debian-shutdown','debian-shutdown','N'),
        Step('install-android','transfer','A'),Step('android-final','health','A'))


def capture_body(handle,address,command):
    require(command in ('reboot','shutdown','download') and not handle.timed_out and not handle.output_exceeded and
        handle.producer_error_type is None,'reboot control producer failed')
    stdout=base.raw.read_stdout(handle,maximum=spec.EVIDENCE_MAXIMUM)
    stderr=base.raw.read_stderr(handle,maximum=16384)
    marker=f'DEBIAN_{command.upper()}_REQUEST_ACCEPTED\n'.encode()
    require(stdout.endswith(marker) and ((handle.returncode==0 and not stderr) or
        (handle.returncode==255 and stderr==('Connection to '+address+' closed by remote host.\r\n').encode())),
        'fixed reboot control was not acknowledged')
    return stdout[:-len(marker)]


class Access(AutomaticAccess):
    def __init__(self,adapter,request,*,phase):
        super().__init__(adapter,request)
        require(selected(request) and type(phase) is int and phase in spec.PHASES,'unselected reboot owner phase')
        protocol.reboot_binding(self.selection(),phase)
        self.reboot_phase=phase
        self.health_step='debian-health' if phase==1 else 'debian-health-second'

    def final_command(self):return 'download' if download_selected(self.request) else 'shutdown'

    def basis(self):
        if self.reboot_phase==1:return super().basis()
        first=Access(self.adapter,self.request,phase=1);reboot=first.rederive_control('reboot')
        rows=Journal(self.adapter.directory/'journal').rows()
        intents=[r for r in rows if r['event']=='effect-intent' and r['data']['step']=='debian-reboot']
        completed=[r for r in rows if r['event']=='step-complete' and r['data']['step']=='debian-reboot']
        require(len(intents)==len(completed)==1 and intents[0]['data']['action']=='debian-reboot' and
            intents[0]['data']['role']=='N' and intents[0]['data']['detail']==
            read(self.adapter.folder('debian-reboot')/'intent.json') and
            read(verify(completed[0]['data']['result']))==reboot,'second boot lacks unique original reboot ownership')
        end=min(intents[0]['boottime_ns']+360_000_000_000,self.grant['deadline_ns'])
        return dict(operation=pin(self.adapter.directory/'operation.json'),grant=self.request['grant'],
            reboot=completed[0]['data']['result'],reboot_intended_ns=intents[0]['boottime_ns'],
            host_boot=self.grant['host_boot'],deadline_ns=end)

    def check_health_phase(self,handle):
        require(re.findall(rb'^S22_REBOOT_PHASE (.*)$',base.raw.read_stdout(handle,maximum=65536),re.M)==
            [str(self.reboot_phase).encode()],'SSH health belongs to another reboot phase')

    def decode_evidence(self,output):
        proof,values=protocol.envelope(output,key=verify(self.request['N']['key'],maximum=32).read_bytes(),
            selected=self.selection(),phase=self.reboot_phase)
        require(not proof['runtime']['reboot_intent'] and not proof['runtime']['shutdown_intent'],
            'health evidence follows a consumed control')
        if self.reboot_phase==2:
            first=Access(self.adapter,self.request,phase=1)
            _,prior=first.control_evidence('reboot')
            require(values[3:5]==prior[:2],'first boot files changed across the ordinary reboot')
            if protocol.profile.cron_config_selected(self.selection()):
                require(values[-2]==prior[-1],'configuration snapshot changed across the ordinary reboot')
            elif protocol.profile.cron_selected(self.selection()):
                require(values[-1]==prior[-1],'cron output changed across the ordinary reboot')
        return proof,values

    def rederive_health(self):
        value=super().rederive_health()
        if self.reboot_phase==2:
            first=Access(self.adapter,self.request,phase=1).rederive_health()
            require(value['health']['boot_count']==first['health']['boot_count']+1,
                'installed boot count did not advance exactly once')
        return value

    def network_expected(self,found):
        return ['s22-debian-'+self.plan['candidate']['run_id'],self.plan['network_uuid'],
            self.plan['link']['host_mac'],found['interface']]

    def network_inspection(self,handle,found):
        base.raw.require_success(handle)
        require(not base.raw.read_stderr(handle,maximum=16384),'owned network inspection has diagnostics')
        rows=base.raw.read_stdout(handle,maximum=16384).decode('ascii').splitlines()
        if len(rows)==4:rows[2]=rows[2].lower()
        require(rows==self.network_expected(found),'reboot connection is not the original owned UUID/name/MAC/interface')

    def configure_link(self,folder,found,guard):
        from s22plus_debian_apt_access_v1 import selected as apt_selected,configure_network
        if apt_selected(self.request):return configure_network(self,folder,found,guard)
        if self.reboot_phase==1:return super().configure_link(folder,found,guard)
        first=self.adapter.folder('debian-health');original=read(first/'network-intent.json')
        previous=read(first/'endpoint.json')
        require(original==dict(uuid=self.plan['network_uuid'],endpoint=previous),'original network ownership differs')
        receipt=self.host(['--escape','no','-g',
            'connection.id,connection.uuid,802-3-ethernet.mac-address,connection.interface-name',
            'connection','show','uuid',self.plan['network_uuid']],folder,'network-before')
        self.network_inspection(base.raw.load_handle(verify(receipt)),previous)
        guard();require(base.endpoint(self.plan['link'])==found,'second NCM changed before rebind')
        publish(folder/'network-intent.json',dict(uuid=self.plan['network_uuid'],endpoint=found))
        self.host(['connection','modify','--temporary','uuid',self.plan['network_uuid'],
            'connection.interface-name',found['interface']],folder,'network-rebind')
        guard();require(base.endpoint(self.plan['link'])==found,'second NCM changed before activation')
        self.host(['connection','up','uuid',self.plan['network_uuid'],'ifname',found['interface']],folder,'network-up')
        require(base.endpoint(self.plan['link'])==found,'second NCM changed during activation')

    def network_result(self,folder):
        from s22plus_debian_apt_access_v1 import selected as apt_selected,network_result
        if apt_selected(self.request):return network_result(self,folder)
        if self.reboot_phase==1:return super().network_result(folder)
        self.network_inspection(base.raw.load_handle(folder/'network-before.capture.json'),
            read(self.adapter.folder('debian-health')/'endpoint.json'))
        for name in ('network-rebind','network-up'):
            base.raw.require_success(base.raw.load_handle(folder/(name+'.capture.json')))

    def cleanup_folder(self):
        second=self.adapter.folder('debian-health-second')
        return second if (second/'network-intent.json').exists() else self.adapter.folder('debian-health')

    def cleanup_interfaces(self,selected):
        # An interrupted rebind may leave either of these two owned interfaces.
        first=read(self.adapter.folder('debian-health')/'network-intent.json')
        require(first['uuid']==self.plan['network_uuid'],'original cleanup UUID differs')
        return [first['endpoint']['interface'],selected['endpoint']['interface']]

    def control_evidence(self,command):
        require((self.reboot_phase,command) in ((1,'reboot'),(2,self.final_command())),'control phase differs')
        folder=self.adapter.folder(control_step(command))
        handle=base.raw.load_handle(folder/(command+'.capture.json'))
        proof,values=protocol.envelope(capture_body(handle,self.plan['link']['ssh_address'],command),
            key=verify(self.request['N']['key'],maximum=32).read_bytes(),selected=self.selection(),phase=self.reboot_phase)
        require(proof['runtime'][command+'_intent'],'completed runtime lacks the requested control tail')
        health=self.evidence()
        previous=base.raw.load_handle(verify(health['capture']))
        _,before=self.decode_evidence(base.raw.read_stdout(previous,maximum=protocol.MAXIMUM))
        require(values[0]==before[0] and values[2:]==before[2:] and values[1][:-128]==before[1] and
            len(values[1])==len(before[1])+128,'control snapshot is not exactly the observed chain plus one intent')
        return proof,values

    def rederive_control(self,command):
        health=self.rederive_health();folder=self.adapter.folder(control_step(command))
        intent=read(folder/'intent.json');proof,_=self.control_evidence(command)
        require(intent['endpoint']==health['endpoint'] and intent['phase']==self.reboot_phase and
            intent['command']==command and intent['health']==pin(self.adapter.folder(self.health_step)/'result.json') and
            intent['dispatch_ns']<intent['deadline_ns']<=self.grant['deadline_ns'] and
            intent['deadline_ns']-intent['dispatch_ns']<=90_000_000_000,
            'control does not join phase, original health or bounded dispatch')
        departure=read(folder/'departure.json')
        require(departure['departed'] is True and departure['before']==read(verify(intent['before'])) and
            departure['deadline_ns']==intent['deadline_ns'] and
            intent['dispatch_ns']<=departure['observed_ns']<intent['deadline_ns'],
            'control departure does not join original dispatch')
        result=dict(action=control_step(command),phase=self.reboot_phase,
            accepted=dict(dispatch_capture=pin(folder/(command+'.capture.json')),request_accepted=True,
                clean_shutdown_proved=False,proof=proof),departure=pin(folder/'departure.json'),
            clean_shutdown_proved=False)
        if command=='download':result['command']=command
        return result

    def control(self,command,step,guard,before):
        require((self.reboot_phase,command,step.name,step.action) in (
            (1,'reboot','debian-reboot','debian-reboot'),(2,self.final_command(),'debian-shutdown','debian-shutdown')),
            'unselected reboot control step')
        health=self.rederive_health();found=read(verify(health['endpoint']))
        folder=self.adapter.folder(step.name,create=True)
        snapshot=base.target.usb_snapshot(found['topology'],folder);publish(folder/'before.json',snapshot)
        def dispatch():
            guard();require(base.endpoint(self.plan['link'])==found,'NCM changed at reboot control dispatch')
            now=clock();detail=dict(endpoint=health['endpoint'],before=pin(folder/'before.json'),
                phase=self.reboot_phase,command=command,health=pin(self.adapter.folder(self.health_step)/'result.json'),
                dispatch_ns=now,deadline_ns=min(self.grant['deadline_ns'],now+90_000_000_000))
            publish(folder/'intent.json',detail);before(detail)
        handle=self.ssh(command,folder,command,found,guard,before=dispatch,deadline_ns=self.grant['deadline_ns'])
        self.control_evidence(command)
        detail=read(folder/'intent.json')
        departed=base.target.wait_departure(snapshot,folder,deadline_ns=detail['deadline_ns'],guard=guard)
        publish(folder/'departure.json',departed)
        value=self.rederive_control(command);publish(folder/'result.json',value)
        # P463 sharing cleanup follows the owner completion/failure path. It
        # must not consume the Download-to-A window before the A transfer.
        from s22plus_debian_apt_access_v1 import selected as apt_selected
        if command in ('shutdown','download') and not apt_selected(self.request):base.cleanup(self.adapter,self.request)
        return value

    def reboot(self,step,guard,before):return self.control('reboot',step,guard,before)
    def shutdown(self,step,guard,before):return self.control(self.final_command(),step,guard,before)
    def rederive_shutdown(self):return self.rederive_control(self.final_command())
