"""Bounded read-only observation of effects already owned by the N transfer."""
import time

import s22plus_debian_access_v1 as access
import s22plus_debian_autoboot_protocol_v1 as protocol
from s22plus_native_records_v3 import Journal,clock,pin,publish,read,require,verify


class Access(access.Access):
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
        folder=self.adapter.folder('debian-health');value=read(folder/'evidence.json')
        handle=access.raw.load_handle(verify(value['capture']));access.raw.require_success(handle)
        require(not access.raw.read_stderr(handle,maximum=16384),'automatic SSH evidence has diagnostics')
        proof,_=protocol.envelope(access.raw.read_stdout(handle,maximum=protocol.MAXIMUM),
            key=verify(self.request['N']['key'],maximum=32).read_bytes(),selected=self.selection())
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
        for ordinal in range(1,181):
            current();handle=self.ssh('evidence',folder,f'evidence-{ordinal:03d}',found,current,deadline_ns=deadline)
            if handle.returncode==0:
                access.raw.require_success(handle)
                require(not access.raw.read_stderr(handle,maximum=16384),'automatic evidence has diagnostics')
                proof,_=protocol.envelope(access.raw.read_stdout(handle,maximum=protocol.MAXIMUM),
                    key=verify(self.request['N']['key'],maximum=32).read_bytes(),selected=self.selection())
                current();publish(folder/'evidence.json',dict(capture=pin(handle.receipt_path),proof=proof,observed_ns=clock()))
                break
            require(not handle.output_exceeded and handle.producer_error_type is None,'automatic evidence producer failed')
            time.sleep(min(2,max(0,(deadline-clock())/1_000_000_000)))
        else:raise TimeoutError('automatic SSH evidence sample budget exhausted')
        for ordinal in range(1,31):
            current();handle=self.ssh('health',folder,f'health-{ordinal:03d}',found,current,deadline_ns=deadline)
            if handle.returncode==0:
                health=access.health_projection(handle,self.plan,boot_sha256=proof['kernel_boot_identity_sha256'],autoboot=True)
                current();require(access.endpoint(self.plan['link'])==found,'automatic NCM changed during health')
                value=dict(action='debian-health',health=health,evidence=pin(folder/'evidence.json'),
                    endpoint=pin(folder/'endpoint.json'),observed_ns=clock(),window=pin(folder/'window.json'))
                publish(folder/'result.json',value);return self.rederive_health()
            require(not handle.output_exceeded and handle.producer_error_type is None,'automatic health producer failed')
            time.sleep(min(1,max(0,(deadline-clock())/1_000_000_000)))
        raise TimeoutError('automatic health sample budget exhausted')

    def rederive_health(self):
        folder=self.adapter.folder('debian-health');value=read(folder/'result.json');evidence=self.evidence()
        require(value['action']=='debian-health' and value['evidence']==pin(folder/'evidence.json') and
            value['endpoint']==pin(folder/'endpoint.json') and value['window']==pin(folder/'window.json'),
            'automatic health receipt location differs')
        expected=access.health_projection(access.raw.load_handle(verify(value['health']['capture'])),self.plan,
            boot_sha256=evidence['proof']['kernel_boot_identity_sha256'],autoboot=True)
        require(value['health']==expected,'automatic health raw proof differs')
        window=read(verify(value['window']));found=read(verify(value['endpoint']))
        require(evidence['observed_ns']<=value['observed_ns']<window['basis']['deadline_ns'] and
            all(found['fields'][name]==v for name,v in dict(idVendor='1d6b',idProduct='0104',
                serial=self.plan['link']['serial'],product='S22 Debian research').items()) and
            found['topology'] in (access.target.lane.SOURCE_TOPOLOGY,access.target.lane.CANDIDATE_TOPOLOGY),
            'automatic health timing or endpoint differs')
        access.raw.require_success(access.raw.load_handle(folder/'network-create.capture.json'))
        access.raw.require_success(access.raw.load_handle(folder/'network-up.capture.json'))
        return value
