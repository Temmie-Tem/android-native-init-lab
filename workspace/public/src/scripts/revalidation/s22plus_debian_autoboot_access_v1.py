"""Bounded read-only observation of effects already owned by the N transfer."""
import time
import re

import s22plus_debian_access_v1 as access
import s22plus_debian_autoboot_protocol_v1 as protocol
from s22plus_native_records_v3 import Journal,clock,pin,publish,read,require,verify


def singlecpu_health_sample(handle,plan,boot=None):
    output=access.raw.read_stdout(handle,maximum=65536)
    if boot is None:
        # Early shape/candidate checks are provisional. The final pair is
        # rederived against the independently authenticated runtime boot.
        boots=re.findall(rb'^boot_id=([0-9a-f-]{36})$',output,re.M)
        require(len(boots)==1,'initial single CPU health lacks one boot identity')
        boot=access.digest(boots[0])
    health=access.health_projection(handle,plan,boot_sha256=boot,autoboot=True)
    require(re.findall(rb'^S22_SINGLECPU_ONLINE (.*)$',output,re.M)==[b'0'],
        'SSH endpoint does not observe CPU0 alone')
    rows=re.findall(rb'^S22_SINGLECPU_UPTIME ([0-9]{1,3})\.([0-9]{2})$',output,re.M)
    require(len(rows)==1,'single CPU SSH uptime is missing or malformed')
    seconds,fraction=rows[0];ms=int(seconds)*1000+int(fraction)*10
    require(0<=ms<300000,'single CPU SSH uptime exceeds original device deadline')
    return dict(health=health,boottime_ms=ms,online_cpus=[0])


def singlecpu_health_pair(first,last,plan,boot):
    """Two authenticated SSH endpoints separated by >=120 device seconds."""
    values=[singlecpu_health_sample(handle,plan,boot) for handle in (first,last)]
    require(values[1]['boottime_ms']-values[0]['boottime_ms']>=120000 and
        values[0]['health']['boot_count']==values[1]['health']['boot_count'],
        'SSH endpoints do not span 120 seconds in the same installed boot')
    return dict(status='PASS_SAME_BOOT_SSH_120_SECONDS',first=values[0],last=values[1],
        continuous_connection_proved=False)


class Access(access.Access):
    health_step='debian-health'

    def decode_evidence(self,output):
        return protocol.envelope(output,key=verify(self.request['N']['key'],maximum=32).read_bytes(),
            selected=self.selection())

    def check_health_phase(self,handle):
        pass

    def network_result(self,folder):
        access.raw.require_success(access.raw.load_handle(folder/'network-create.capture.json'))
        access.raw.require_success(access.raw.load_handle(folder/'network-up.capture.json'))

    def basis(self):
        rows=Journal(self.adapter.directory/'journal').rows()
        intents=[r for r in rows if r['event']=='effect-intent' and r['data']['step']=='install-native-first']
        completed=[r for r in rows if r['event']=='step-complete' and r['data']['step']=='install-native-first']
        require(len(intents)==len(completed)==1 and intents[0]['data']['action']=='transfer' and
            intents[0]['data']['role']=='N','automatic boot lacks unique transfer ownership')
        from s22plus_native_session_v3 import Step
        result=self.adapter.recover_transfer_result(Step('install-native-first','transfer','N'),self.request)
        require(result==read(verify(completed[0]['data']['result'])),'automatic transfer does not rederive')
        end=completed[0]['boottime_ns']+360_000_000_000
        require(end<self.grant['deadline_ns'],'original grant lacks automatic observation window')
        return dict(operation=pin(self.adapter.directory/'operation.json'),grant=self.request['grant'],
            transfer=completed[0]['data']['result'],transfer_completed_ns=completed[0]['boottime_ns'],
            host_boot=self.grant['host_boot'],deadline_ns=end)

    def selection(self):
        artifact=read(verify(self.request['N']['autoboot_boot']))
        return read(verify(artifact['build']))

    def evidence(self):
        folder=self.adapter.folder(self.health_step);value=read(folder/'evidence.json')
        handle=access.raw.load_handle(verify(value['capture']));access.raw.require_success(handle)
        require(not access.raw.read_stderr(handle,maximum=16384),'automatic SSH evidence has diagnostics')
        proof,_=self.decode_evidence(access.raw.read_stdout(handle,maximum=protocol.MAXIMUM))
        require(value['proof']==proof,'automatic evidence differs from its raw capture')
        window=read(folder/'window.json')
        require(window['basis']==self.basis() and window['opened_ns']<=value['observed_ns']<window['basis']['deadline_ns'],
            'automatic evidence did not finish in its original transfer window')
        return value

    def health(self,step,guard):
        folder=self.adapter.folder(step.name,create=True);basis=self.basis();deadline=basis['deadline_ns']
        def current():
            guard();require(clock()<deadline,'automatic observation window expired')
        current();publish(folder/'window.json',dict(basis=basis,opened_ns=clock()))
        found=None
        for ordinal in range(1,181):
            current();access.usb.capture(folder,ordinal,self.plan['link'])
            found=access.endpoint(self.plan['link'])
            if found:break
            time.sleep(min(2,max(0,(deadline-clock())/1_000_000_000)))
        require(found is not None,'automatic Debian NCM did not arrive')
        publish(folder/'endpoint.json',found);self.configure_link(folder,found,current)
        from s22plus_debian_autoboot_profile_v1 import singlecpu_selected
        single_cpu=singlecpu_selected(self.selection());first_health=None;health_ordinal=0
        if single_cpu:
            for health_ordinal in range(1,30):
                current();handle=self.ssh('health',folder,f'health-{health_ordinal:03d}',found,current,deadline_ns=deadline)
                if handle.returncode==0:
                    self.check_health_phase(handle);singlecpu_health_sample(handle,self.plan)
                    first_health=handle;first_finished=clock();break
                require(not handle.output_exceeded and handle.producer_error_type is None,'initial health producer failed')
                time.sleep(min(3,max(0,(deadline-clock())/1_000_000_000)))
            require(first_health is not None,'initial single CPU SSH health budget exhausted')
        from s22plus_debian_apt_access_v1 import selected as apt_selected,handoff as clock_handoff
        if apt_selected(self.request):
            require(first_health is not None,'APT clock handoff needs same-boot SSH identity')
            clock_handoff(self,folder,found,current,deadline,singlecpu_health_sample(first_health,self.plan))
        for ordinal in range(1,181):
            current();handle=self.ssh('evidence',folder,f'evidence-{ordinal:03d}',found,current,deadline_ns=deadline)
            if handle.returncode==0:
                access.raw.require_success(handle)
                require(not access.raw.read_stderr(handle,maximum=16384),'automatic evidence has diagnostics')
                proof,_=self.decode_evidence(access.raw.read_stdout(handle,maximum=protocol.MAXIMUM))
                current();publish(folder/'evidence.json',dict(capture=pin(handle.receipt_path),proof=proof,observed_ns=clock()))
                break
            require(not handle.output_exceeded and handle.producer_error_type is None,'automatic evidence producer failed')
            time.sleep(min(2,max(0,(deadline-clock())/1_000_000_000)))
        else:raise TimeoutError('automatic SSH evidence sample budget exhausted')
        if single_cpu:
            # This wait consumes the original window. It creates no new
            # lifetime, command, grant or device deadline.
            while clock()-first_finished<120_100_000_000:
                current();time.sleep(min(1,max(0,(deadline-clock())/1_000_000_000)))
        for ordinal in range(health_ordinal+1,31):
            current();handle=self.ssh('health',folder,f'health-{ordinal:03d}',found,current,deadline_ns=deadline)
            if handle.returncode==0:
                self.check_health_phase(handle)
                health=access.health_projection(handle,self.plan,boot_sha256=proof['kernel_boot_identity_sha256'],autoboot=True)
                current();require(access.endpoint(self.plan['link'])==found,'automatic NCM changed during health')
                value=dict(action='debian-health',health=health,evidence=pin(folder/'evidence.json'),
                    endpoint=pin(folder/'endpoint.json'),observed_ns=clock(),window=pin(folder/'window.json'))
                if single_cpu:
                    value['ssh_120_seconds']=singlecpu_health_pair(first_health,handle,self.plan,
                        proof['kernel_boot_identity_sha256'])
                publish(folder/'result.json',value);return self.rederive_health()
            require(not handle.output_exceeded and handle.producer_error_type is None,'automatic health producer failed')
            time.sleep(min(1,max(0,(deadline-clock())/1_000_000_000)))
        raise TimeoutError('automatic health sample budget exhausted')

    def rederive_health(self):
        folder=self.adapter.folder(self.health_step);value=read(folder/'result.json');evidence=self.evidence()
        require(value['action']=='debian-health' and value['evidence']==pin(folder/'evidence.json') and
            value['endpoint']==pin(folder/'endpoint.json') and value['window']==pin(folder/'window.json'),
            'automatic health receipt location differs')
        self.check_health_phase(access.raw.load_handle(verify(value['health']['capture'])))
        expected=access.health_projection(access.raw.load_handle(verify(value['health']['capture'])),self.plan,
            boot_sha256=evidence['proof']['kernel_boot_identity_sha256'],autoboot=True)
        require(value['health']==expected,'automatic health raw proof differs')
        from s22plus_debian_autoboot_profile_v1 import singlecpu_selected
        if singlecpu_selected(self.selection()):
            pair=value['ssh_120_seconds']
            self.check_health_phase(access.raw.load_handle(verify(pair['first']['health']['capture'])))
            require(pair==singlecpu_health_pair(
                access.raw.load_handle(verify(pair['first']['health']['capture'])),
                access.raw.load_handle(verify(value['health']['capture'])),self.plan,
                evidence['proof']['kernel_boot_identity_sha256']),'single CPU SSH interval does not rederive')
        else:require('ssh_120_seconds' not in value,'legacy health cannot claim a sampled SSH interval')
        window=read(verify(value['window']));found=read(verify(value['endpoint']))
        require(evidence['observed_ns']<=value['observed_ns']<window['basis']['deadline_ns'] and
            all(found['fields'][name]==v for name,v in dict(idVendor='1d6b',idProduct='0104',
                serial=self.plan['link']['serial'],product='S22 Debian research').items()) and
            found['topology'] in (access.target.lane.SOURCE_TOPOLOGY,access.target.lane.CANDIDATE_TOPOLOGY),
            'automatic health timing or endpoint differs')
        self.network_result(folder)
        from s22plus_debian_apt_access_v1 import selected as apt_selected,rederive as clock_rederive
        if apt_selected(self.request):clock_rederive(self,folder,evidence['proof'])
        return value
