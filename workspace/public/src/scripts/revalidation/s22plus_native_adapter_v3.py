"""Concrete fixed S22+ I/O for the V3 session owner; no legacy live owner."""
from dataclasses import asdict
from contextlib import contextmanager
import os
from pathlib import Path
import time
import uuid

import consumed_candidate_registry_v1 as registry
import device_action_raw_capture_v1 as raw
import s22plus_boot_only_f1_transport as transport
import s22plus_native_host_v3 as host_module
import s22plus_native_observation_v3 as native
import s22plus_native_target_io_v3 as target
import s22plus_odin_transition_core as transition
from s22plus_native_records_v3 import (SCHEMA, Journal, clock, digest, pin, private_path,
    publish, read, require, verify)
from s22plus_native_session_v3 import steps

AP_MAXIMUM=128*1024*1024


def image_identity(image, binding):
    """Content keys use the existing global registry, including historic claims."""
    return registry.derive_candidate_identity({'target':dict(model='SM-S906N',device='g0q')},
        dict(manifest_id='s22plus-'+image['namespace']+'-v3',run_id=image['run_id_hex'],
            candidate_ap=image['ap'],allowed_member='boot.img.lz4'),image['ap']['sha256'],
        approval_binding_sha256=binding,candidate_receipt=dict(size=image['ap']['size'],
            sha256=image['ap']['sha256'],member=image['member']))


def image_valid(image, *, artifact_bytes=False):
    require(set(image)=={'schema','namespace','run_id_hex','profile','version','ap','member','key',
        'qualification','runtime_sources'} and image['schema']=='s22plus-native-image-v3'
        and image['profile']=='thermal-v3-reconnect-v1','native image qualification schema differs')
    native.identity(image); native.key_bytes(image)
    qualification=read(verify(image['qualification']))
    require(qualification['schema']=='s22plus-native-artifact-qualification-v3'
        and qualification['image']=={key:value for key,value in image.items() if key!='qualification'}
        and qualification['ab_identical'] is True and qualification['actual_ap_join'] is True,
        'native artifact qualification differs')
    built=read(verify(qualification['builder_result']))
    verify(qualification['exporter'])
    require(qualification['exporter']['path']==str(Path(__file__).resolve().parents[1]/'analysis/s22plus_native_artifact_v3_h0.py')
        and built['schema']=='s22plus-native-thermal-build-v1' and built['verdict']=='PASS_NATIVE_THERMAL_BUILD_H0'
        and built['byte_identical'] is True and built['candidate']['a']==built['candidate']['b']
        and built['source_inputs']==image['runtime_sources'] and built['run_id_hex']==image['run_id_hex']
        and built['native_selection']['namespace']==image['namespace']
        and built['native_selection']['display_version']==image['version']
        and built['native_selection']['auth_key']=={name:image['key'][name] for name in ('size','sha256')}
        and built['candidate']['a']['ap_tar_md5']=={name:image['ap'][name] for name in ('size','sha256')}
        and built['candidate']['a']['boot_img_lz4']=={name:image['member'][name] for name in ('size','sha256')},
        'native qualification does not join its actual A/B producer')
    if artifact_bytes:
        with transport.pin_boot_only_ap(Path(image['ap']['path']),label='qualified native image',
                expected_size=image['ap']['size'],expected_sha256=image['ap']['sha256']) as ap:
            require(transport.boot_only_member_receipt(ap,label='native')==image['member'],'qualified native boot member differs')


class Adapter:
    def __init__(self, root, directory, *, experiment=None):
        self.root=Path(root).resolve(strict=True)
        self.directory=private_path(self.root,directory)
        self.host=None
        self.selected_experiment=experiment

    def configuration(self, request):
        return read(verify(request['task']))

    def check(self, request, *, recovery=False):
        from s22plus_native_task_v3 import validate_task, validate_grant
        task=self.configuration(request)
        android_completed=self.android_transfer_completed(request)
        validate_task(self.root,task,live=True,recovery=recovery or android_completed,
            require_android=not android_completed)
        grant_path=verify(request['grant']); grant=read(grant_path)
        validate_grant(task,grant,grant_path)
        require(set(request)=={'schema','operation','reentry','hud','grant','task','N','E','A',
            'admission','prior_terminal','usb_reconnect'}
            and request['schema']==SCHEMA and request['task']==grant['task'],
            'operation uses a different task')
        require(request['operation'] in task['operations']
            and (not request['reentry'] or task['reentry']) and (not request['hud'] or task['hud']),
            'operation options exceed the original task')
        require(request['N']==task['N'] and request['A']==task['A'],
            'operation artifact selection differs from original task')
        if request['operation']=='experiment':
            if not recovery and not android_completed: image_valid(request['E'])
            require(request['E']['runtime_sources']==task['runtime_scope']
                and request['E']['run_id_hex']!=task['N']['run_id_hex']
                and request['E']['ap']['sha256']!=task['N']['ap']['sha256'],
                'selected E is outside the original reviewed runtime scope')
        else: require(request['E'] is None,'non-experiment operation contains an E')
        require(not request['usb_reconnect'] or request['reentry'] and request['operation']=='experiment',
            'USB reconnect is not a selected E reentry')

    def folder(self, name, *, create=False):
        path=self.directory/('io-'+name)
        if create: path.mkdir(mode=0o700)
        return path

    def native_host(self, request):
        if self.host is None:
            installation=read(verify(self.configuration(request)['host_installation']))
            # A new evidence directory is used for each process, including
            # original recovery. This cannot collide with retained raw names.
            folder=self.directory/('host-'+uuid.uuid4().hex)
            self.host=host_module.NativeHost(installation,folder)
        return self.host

    def prepare(self, operation, grant, *, reentry=False, hud=False):
        task=read(verify(grant['task']))
        require(operation in task['operations'],'operation is outside the task scope')
        require(not reentry or task['reentry'],'E reentry was not selected by the task')
        require(not hud or task['hud'],'optional HUD was not selected by the task')
        experiment=None
        if operation=='experiment':
            experiment=read(verify(self.selected_experiment)) if self.selected_experiment else task['E']
            image_valid(experiment,artifact_bytes=True)
            require(experiment['runtime_sources']==task['runtime_scope']
                and experiment['run_id_hex']!=task['N']['run_id_hex']
                and experiment['ap']['sha256']!=task['N']['ap']['sha256'],
                'prepared E is outside the original runtime scope')
        prior=None; admission=None
        if operation!='bootstrap':
            admission=task['admission']
            prior=task['prior_terminal']
            for path in sorted(Path(grant['directory']).glob('operation-*/terminal.json')):
                closed=read(path)
                require(closed['terminal_state']=='NATIVE_CLOSED_HEALTHY',
                    'task already returned to Android or requires recovery')
                prior=pin(path)
                candidate=path.parent/'admission.json'
                if candidate.exists(): admission=pin(candidate)
            require(prior is not None and admission is not None,'native origin has no V3 admission and closed tail')
            self.admission(admission,task['N'],task)
            self.tail(prior,task['N'],task)
            require(not self.tail_claim_path(prior).exists(),'prior native tail already has an authentication attempt')
        return dict(task=grant['task'],N=task['N'],E=experiment,A=task['A'],
            admission=admission,prior_terminal=prior,usb_reconnect=bool(task['usb_reconnect'] and reentry))

    def preflight(self, request, *, guard):
        guard(); task=self.configuration(request)
        for image in (request['N'],request['E']):
            if image is not None: image_valid(image,artifact_bytes=True)
        with self.original_android(request): pass
        for role in (('N',) if request['operation']=='bootstrap' else ('E',) if request['operation']=='experiment' else ()):
            registry.preflight_candidate(self.root,image_identity(request[role],pin(self.directory/'operation.json')['sha256']))
        target.lane.revalidate_binding(task['lane'],source_topology=target.lane.SOURCE_TOPOLOGY)
        self.native_host(request).holders(expected_run=None if request['operation']=='bootstrap' else request['N']['run_id_hex'])
        folder=self.folder('preflight',create=True)
        if request['operation']=='bootstrap':
            self.android(request,folder,guard).health()
        else:
            self.admission(request['admission'],request['N'],task); self.tail(request['prior_terminal'],request['N'],task)
        publish(folder/'complete.json',dict(task=request['task'],host_configuration_verified=True,
            health=pin(folder/'health.json') if request['operation']=='bootstrap' else request['prior_terminal']))

    def android(self, request, folder, guard):
        task=self.configuration(request)
        return target.Android(task['adb'],task['target'],request['A'],folder,guard=guard)

    @contextmanager
    def original_android(self, request):
        artifact=request['A']
        with transport.pin_boot_only_ap(Path(artifact['ap']['path']),label='original Android A',
                expected_size=artifact['ap']['size'],expected_sha256=artifact['ap']['sha256'],
                require_deterministic_metadata=False) as ap:
            require(transport.boot_only_member_receipt(ap,label='Android',require_deterministic_metadata=False)==artifact['member'],
                'original Android member differs')
            yield ap

    def android_download(self, step, request, *, guard, before_dispatch):
        folder=self.folder(step.name,create=True)
        before=target.usb_snapshot(target.lane.SOURCE_TOPOLOGY,folder)
        publish(folder/'departure-before.json',before)
        deadline=None
        def dispatch():
            nonlocal deadline
            deadline=clock()+30_000_000_000
            before_dispatch(dict(departure=pin(folder/'departure-before.json'),departure_deadline_ns=deadline))
        result=self.android(request,folder,guard).download(before_dispatch=dispatch)
        result['departure']=target.wait_departure(before,folder,deadline_ns=deadline,guard=guard)
        publish(folder/'result.json',result)
        return dict(action='download',result=pin(folder/'result.json'))

    def claim(self, step, request, binding):
        if step.role=='A': return
        image=request[step.role]; identity=image_identity(image,binding)
        if step.name in ('install-native-first','install-experiment'):
            claim=registry.claim(self.root,identity)
            publish(self.directory/('claim-'+step.role+'.json'),claim)
        elif step.name=='install-native-second':
            claim=read(self.directory/'claim-N.json')
            require(registry.active_claim(self.root,identity['candidate_key'])==claim['record'],
                'bootstrap second installation has no original native claim')
            self.validate_result(steps('bootstrap')[3],read(self.directory/'native-first-2.json'),request)
        elif step.name=='restore-native':
            self.admission(request['admission'],image,self.configuration(request))
            selected=steps('experiment',reentry=request['reentry'],hud=request['hud'])[-3]
            self.validate_result(selected,read(self.directory/(selected.name+'.json')),request)
        else: require(False,'unselected native restoration')

    def transfer(self, step, request, *, guard, before_launch):
        task=self.configuration(request); artifact=request[step.role]['ap']
        base=self.folder(step.name); base.mkdir(mode=0o700,exist_ok=True)
        folder=base/('attempt-'+uuid.uuid4().hex); folder.mkdir(mode=0o700)
        endpoints=folder/'endpoints'; endpoints.mkdir(mode=0o700)
        guard()
        if step.name=='recover-android':
            arrival_deadline=clock()+90_000_000_000
        else:
            intents=[row for row in Journal(self.directory/'journal').rows() if row['event']=='effect-intent']
            require(intents and intents[-1]['data']['action'] in ('download','observe'),
                'normal transfer has no preceding Download intent')
            # Thirty seconds for departure and ninety for Download arrival,
            # both measured from the original mode-changing intent.
            arrival_deadline=intents[-1]['data']['detail']['departure_deadline_ns']+60_000_000_000
        require(clock()<arrival_deadline,'original Download arrival window expired')
        with transport.pin_regular_file(Path(task['odin']['path']),label='Odin enumeration',
                expected_size=task['odin']['size'],expected_sha256=task['odin']['sha256']) as odin, \
                self.original_android(request) as android, \
                transition.transaction_session(endpoints) as lease:
            def observer():
                guard(); transport.revalidate_pinned_path(odin)
                # Keep the primitive's default raw-first command producer.
                return transition.measured_usbfs_observer(endpoints)
            found=transition.wait_for_single_live_endpoint(odin.path,endpoints,timeout_sec=(arrival_deadline-clock())/1e9,
                lease=lease,endpoint_observer_factory=observer,
                monotonic=lambda:clock()/1e9)
            require(found.ticket is not None and not found.timed_out,'exact Download arrival is unproved')
            ticket=found.ticket
            identity=target.download_identity(ticket.device)
            def launch():
                guard()
                self.native_host(request).holders()
                target.lane.revalidate_binding(task['lane'],source_topology=target.lane.SOURCE_TOPOLOGY)
                checked=transition.revalidate_endpoint_ticket(odin.path,endpoints,ticket,
                    sequence=found.next_sequence,lease=lease,timeout_sec=10,
                    endpoint_observer_factory=observer,monotonic=lambda:clock()/1e9)
                require(target.download_identity(ticket.device)==identity,'Download target changed before launch')
                require(clock()<arrival_deadline,'original Download arrival window expired before dispatch')
                transport.revalidate_pinned_path(android)
                detail=dict(step=step.name,role=step.role,ap=artifact,member=request[step.role]['member'],
                    ticket=asdict(ticket),target=identity,revalidation=checked,boottime_ns=clock(),
                    arrival_deadline_ns=arrival_deadline)
                launch_receipt=publish(folder/'launch.json',detail)
                before_launch(dict(launch=launch_receipt))
                guard()
                transport.revalidate_pinned_path(android)
                require(clock()<arrival_deadline,'original Download deadline expired during intent publication')
            receipt,handle=transport.execute_odin_boot_only(odin.path,Path(artifact['path']),ticket.device,
                odin_size=task['odin']['size'],odin_sha256=task['odin']['sha256'],
                ap_size=artifact['size'],ap_sha256=artifact['sha256'],label=step.role,
                require_deterministic_metadata=step.role!='A',capture_dir=folder,capture_name='odin',
                stdout_name='stdout.bin',stderr_name='stderr.bin',before_launch=launch)
        target.transfer_completed(handle)
        publish(folder/'transport.json',receipt)
        return self.recover_transfer_result(step,request)

    def recover_transfer_result(self, step, request):
        intents=[row for row in Journal(self.directory/'journal').rows() if row['event']=='effect-intent'
            and row['data']['step']==step.name]
        require(len(intents)==1,'transfer has no original unique durable intent')
        path=verify(intents[0]['data']['detail']['launch']); folder=path.parent
        require(path.name=='launch.json' and folder.parent==self.folder(step.name)
            and folder.name.startswith('attempt-'),
            'transfer launch has no original unique durable intent')
        launch=read(path)
        require(launch['step']==step.name and launch['role']==step.role
            and launch['ap']==request[step.role]['ap'] and launch['member']==request[step.role]['member']
            and launch['boottime_ns']<launch['arrival_deadline_ns'],
            'retained transfer launch differs')
        handle=raw.load_handle(folder/'odin.capture.json'); target.transfer_completed(handle)
        return dict(action='transfer',role=step.role,launch=pin(folder/'launch.json'),raw=pin(handle.receipt_path),
            completed=True)

    def context(self, step, request):
        plan=steps(request['operation'],reentry=request['reentry'],hud=request['hud'])
        index=plan.index(step); prior=[]
        if request['prior_terminal'] is not None:
            prior.append(self.tail(request['prior_terminal'],request['N'],self.configuration(request)))
        for previous_step in plan[:index]:
            if previous_step.action=='observe':
                prior.append(self.recover_step_result(previous_step,request)['proof'])
        first=index>0 and plan[index-1].action=='transfer'
        return dict(previous=None if first else prior[-1] if prior else None,first_boot=first,
            seen_nonces=[proof['nonce_sha256'] for proof in prior],
            seen_boots=[proof['kernel_boot_identity_sha256'] for proof in prior])

    def wait_native(self, image, request, guard):
        host=self.native_host(request); deadline=clock()+90_000_000_000
        while clock()<deadline:
            guard(); endpoint=host_module.census.endpoint(host.config)
            if endpoint is not None:
                host.holders(expected_run=image['run_id_hex']); return
            time.sleep(.2)
        raise TimeoutError('selected native endpoint did not arrive')

    def observe(self, step, request, *, guard, before_terminal, consume_observation=None):
        image=request[step.role]; self.wait_native(image,request,guard)
        context=self.context(step,request)
        if step.name=='experiment-final' and request['usb_reconnect']:
            self.reconnect(request,guard)
        if step.name=='experiment-first' and request['usb_reconnect']:
            before=target.usb_snapshot(target.lane.CANDIDATE_TOPOLOGY,self.directory)
            publish(self.directory/'usb-reconnect-before.json',before)
        def begin_attempt():
            if consume_observation is not None: consume_observation()
            self.claim_tail(request)
        return native.observe(self.folder(step.name),image,self.native_host(request),ending=step.ending,
            hud=step.hud,guard=guard,before_terminal=before_terminal,
            before_auth=begin_attempt if step.name in ('native-start','native-storage') else None,
            profile='storage-census' if step.name=='native-storage' else 'health',**context)

    def tail_claim_path(self, receipt):
        verify(receipt)
        return self.root/'workspace/private/runs/s22plus-native-session-v3/tail-claims'/(receipt['sha256']+'.json')

    def claim_tail(self, request):
        path=self.tail_claim_path(request['prior_terminal'])
        path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        value=dict(schema='s22plus-native-tail-attempt-v3',prior=request['prior_terminal'],
            operation=pin(self.directory/'operation.json'),boottime_ns=clock())
        if (self.root/registry.F1_OWNER).exists():
            registry.require_f1_owner(self.root,self.directory,value['operation']['sha256'])
        else:
            registry.begin_f1_owner(self.root,self.directory,value['operation']['sha256'])
        receipt=publish(path,value)
        publish(self.directory/'tail-attempt.json',receipt)

    def native_attempt_started(self, request):
        prior=request.get('prior_terminal')
        if prior is None: return False
        path=self.tail_claim_path(prior)
        if not path.exists(): return False
        value=read(path)
        return value.get('schema')=='s22plus-native-tail-attempt-v3' and value.get('prior')==prior \
            and value.get('operation')==pin(self.directory/'operation.json')

    def android_transfer_completed(self, request):
        journal=self.directory/'journal'
        if not journal.exists(): return False
        intents=[row for row in Journal(journal).rows() if row['event']=='effect-intent']
        if not intents or intents[-1]['data']['role']!='A' or intents[-1]['data']['action']!='transfer': return False
        from s22plus_native_session_v3 import Step
        try:
            return self.recover_transfer_result(Step(intents[-1]['data']['step'],'transfer','A'),request)['completed'] is True
        except (OSError,ValueError,raw.RawCaptureError): return False

    def reconnect(self, request, guard):
        before=read(self.directory/'usb-reconnect-before.json')
        deadline=clock()+120_000_000_000
        publish(self.directory/'usb-reconnect-window.json',dict(before=pin(self.directory/'usb-reconnect-before.json'),
            opened_ns=clock(),deadline_ns=deadline))
        print('S22+ E health and DETACH are complete. Disconnect and reconnect only the bound S22+ USB cable now.',flush=True)
        departure=target.wait_departure(before,self.directory,deadline_ns=deadline,guard=guard)
        publish(self.directory/'usb-reconnect-departure.json',departure)
        host=self.native_host(request)
        while clock()<deadline:
            guard(); endpoint=host_module.census.endpoint(host.config)
            if endpoint is None: time.sleep(.1); continue
            host.holders(expected_run=request['E']['run_id_hex'])
            after=target.usb_snapshot(target.lane.CANDIDATE_TOPOLOGY,self.directory)
            require(clock()<deadline and after['identity']!=before['identity'],
                'USB reconnect did not prove a new generation within the original window')
            publish(self.directory/'usb-reconnect-after.json',after); return
        raise TimeoutError('selected USB reconnect did not complete')

    def android_health(self, step, request, *, guard):
        # A later attended recovery may take a fresh D0 health attempt. Every
        # attempt retains its raw bytes, and no A transfer is repeated.
        base=self.folder(step.name)
        base.mkdir(mode=0o700,exist_ok=True)
        if (base/'result.json').exists() or any(base.glob('attempt-*/health.json')):
            return self.recover_step_result(step,request)
        folder=base/('attempt-'+uuid.uuid4().hex); folder.mkdir(mode=0o700)
        client=self.android(request,folder,guard)
        client.wait_ready(deadline_ns=clock()+180_000_000_000)
        client.health()
        value=dict(action='health',health=pin(folder/'health.json'))
        publish(base/'result.json',value)
        return value

    def recover_step_result(self, step, request):
        if step.action=='transfer': return self.recover_transfer_result(step,request)
        if step.action=='observe':
            value=native.rederive(self.folder(step.name),request[step.role],ending=step.ending,hud=step.hud,
                profile='storage-census' if step.name=='native-storage' else 'health',**self.context(step,request))
            if step.ending=='download': value['departure']=pin(self.folder(step.name)/'departure.json')
            return value
        if step.action=='health':
            base=self.folder(step.name); path=base/'result.json'
            if path.exists(): return read(path)
            measured=list(base.glob('attempt-*/health.json'))
            require(len(measured)==1,'no unique completed Android health proof')
            return dict(action='health',health=pin(measured[0]))
        if step.action=='download': return dict(action='download',result=pin(self.folder(step.name)/'result.json'))
        require(False,'unknown retained step')

    def final_protocol_completed(self, step, request):
        folder=self.folder(step.name)
        if step.action=='health':
            return (folder/'result.json').exists() or any(folder.glob('attempt-*/health.json'))
        path=folder/'session.capture.json'
        if not path.exists(): return False
        # This is only a negative guard against another A after completed
        # protocol. Missing close evidence cannot become a terminal verdict.
        try:
            handle=raw.load_handle(path)
            return handle.returncode==0 and not handle.timed_out and not handle.output_exceeded and handle.producer_error_type is None
        except (OSError,ValueError,raw.RawCaptureError): return True

    def validate_result(self, step, value, request):
        require(value==self.recover_step_result(step,request),'step result differs from original raw evidence')
        if step.name in ('native-start','native-storage'):
            claim=read(self.tail_claim_path(request['prior_terminal']))
            require(claim['schema']=='s22plus-native-tail-attempt-v3'
                and claim['prior']==request['prior_terminal'] and claim['operation']==pin(self.directory/'operation.json'),
                'native-start proof has no unique original tail attempt')
        if step.action=='health':
            health=read(verify(value['health'])); task=self.configuration(request)
            require(target.health_projection(health['captures'],task['target'],request['A'])==health,
                'final Android health does not rederive')
            preflight=self.folder('preflight')/'health.json'
            if preflight.exists():
                require(health['boot_id_sha256']!=read(preflight)['boot_id_sha256'],
                    'final Android health reused the initial boot')
        if step.action=='download':
            result=read(verify(value['result']))
            raw.require_success(raw.load_handle(verify(result['capture'])))
            require(result['accepted'] is True,'Android Download request is unproved')
            departure=result['departure']
        elif step.action=='observe' and step.ending=='download': departure=read(verify(value['departure']))
        else: return
        require(departure['departed'] is True and departure['observed_ns']<departure['deadline_ns'],
            'timely measured departure is unproved')
        intents=[row for row in Journal(self.directory/'journal').rows() if row['event']=='effect-intent'
            and row['data']['step']==step.name]
        require(len(intents)==1 and intents[0]['data']['detail']['departure_deadline_ns']==departure['deadline_ns']
            and read(verify(intents[0]['data']['detail']['departure']))==departure['before'],
            'departure is not bound to the original transition intent')

    def validate_sequence(self, selected, values, request):
        require(len(values)==len(selected),'native sequence incomplete')
        for step,value in zip(selected,values): self.validate_result(step,value,request)
        if request['usb_reconnect'] and selected[-1].role=='N':
            window=read(self.directory/'usb-reconnect-window.json')
            departure=read(self.directory/'usb-reconnect-departure.json')
            before=read(verify(window['before'])); after=read(self.directory/'usb-reconnect-after.json')
            require(departure['before']==before and departure['departed'] is True
                and departure['deadline_ns']==window['deadline_ns']
                and window['opened_ns']<=departure['observed_ns']<after['boottime_ns']<window['deadline_ns']
                and before['identity']!=after['identity'],'physical USB reconnect proof differs')

    def terminal(self, selected, values, request, *, recovered):
        healthy_native=selected[-1].action=='observe' and selected[-1].role=='N'
        result=dict(terminal_state='NATIVE_CLOSED_HEALTHY' if healthy_native else 'ANDROID_CLOSED_HEALTHY',
            terminal_step=selected[-1].name,terminal_result=pin(self.directory/(selected[-1].name+'.json')),
            operation=request['operation'],operation_record=pin(self.directory/'operation.json'),
            native_admitted=request['operation']=='bootstrap' and not recovered,
            usb_reconnect_proved=bool(request['usb_reconnect'] and healthy_native),
            host_configuration='VERIFIED_INSTALLED_EXTERNAL_CONFIGURATION')
        if request['operation']=='storage-census':
            result['storage_census_status']=values[-1]['proof']['storage_census']['status'] if healthy_native else 'NOT_COMPLETED'
        return result

    def tail(self, receipt, image, task):
        terminal=read(verify(receipt))
        require(terminal['schema']==SCHEMA and terminal['terminal_state']=='NATIVE_CLOSED_HEALTHY'
            and terminal['recovered'] is False and terminal['research_closed'] is True,'native tail is not healthy and closed')
        operation=read(verify(terminal['operation_record']))
        require(operation['N']==image,'closed tail belongs to a different N')
        original=self.configuration(operation)
        require(original['target']==task['target'] and original['A']==task['A'],
            'closed native tail belongs to a different physical target or Android A')
        other=Adapter(self.root,Path(terminal['operation_record']['path']).parent)
        selected=steps(operation['operation'],reentry=operation['reentry'],hud=operation['hud'])[-1]
        result=read(verify(terminal['terminal_result']))
        require(terminal['terminal_step']==selected.name,'native terminal step differs')
        other.validate_result(selected,result,operation)
        return result['proof']

    def admission(self, receipt, image, task):
        admission=read(verify(receipt))
        require(admission['schema']=='s22plus-native-admission-v3' and admission['N']==image,
            'V3 admission image differs')
        terminal=read(verify(admission['terminal']))
        operation=read(verify(terminal['operation_record']))
        original=self.configuration(operation)
        require(original['target']==task['target'] and original['A']==task['A'],
            'native admission belongs to a different physical target or Android A')
        require(operation['operation']=='bootstrap' and terminal['native_admitted'] is True
            and terminal['recovered'] is False,'N was not admitted by a completed V3 bootstrap')
        other=Adapter(self.root,Path(terminal['operation_record']['path']).parent)
        from s22plus_native_session_v3 import Session
        session=Session(self.root,other.directory,other)
        session.completed(steps('bootstrap'))
        claim=read(other.directory/'claim-N.json')
        identity=image_identity(image,pin(other.directory/'operation.json')['sha256'])
        require(registry.active_claim(self.root,identity['candidate_key'])==claim['record'],
            'N admission has no original global content claim')
        return admission

    def admit(self, request, terminal):
        value=dict(schema='s22plus-native-admission-v3',N=request['N'],terminal=terminal)
        path=self.directory/'admission.json'
        if path.exists(): require(read(path)==value,'existing native admission differs')
        else: publish(path,value)
