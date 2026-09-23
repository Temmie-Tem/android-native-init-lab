#!/usr/bin/env python3
"""One installed-Debian PID 1 attempt with P399 normal return and original-A fallback.

This owner remains H0 until its separate policy, target adoption and source-bound
independent review are current. The P401 installation owner is never reopened.
"""
import argparse
import ast
from dataclasses import asdict
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

import consumed_candidate_registry_v1 as registry
import device_action_raw_capture_v1 as raw
import s22plus_boot_only_f1_transport as transport
import s22plus_debian_first_boot_v1 as old
import s22plus_native_target_io_v3 as target
import s22plus_odin_transition_core as transition
from s22plus_native_records_v3 import (clock,digest,host_boot,pin,private_path,publish,
    read,require,verify)

ROOT=Path(__file__).resolve().parents[5]
SCHEMA='s22plus-debian-installed-boot-v1'
POLICY=ROOT/'docs/operations/S22PLUS_DEBIAN_INSTALLED_BOOT_V1.md'
COMMON=ROOT/'docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md'
TARGET=ROOT/'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md'
REVIEW=ROOT/'workspace/public/src/device-action/bindings/s22plus_debian_installed_boot_v1_review.json'
P404=ROOT/'workspace/private/outputs/s22plus-debian-installed-h0-20260923-1'
ARTIFACT=dict(path=str(P404/'build-5/artifact.json'),size=4342,
    sha256='99de9421701ee202769645ab5bdb3273fc7319f36cfe7fe064fbcaca4d67cf7b')
QUALIFIED=dict(path=str(P404/'qualified-1/qualification.json'),size=6092,
    sha256='d0af6c1072b4cbc0acc3733ee0b00a95417b766d15d20d3724f3b6a4ae7fb513')
P401_PLAN=ROOT/'workspace/private/outputs/s22plus-debian-device-prep-20260921-1/p401-first-boot-run-3/plan.json'
P399=ROOT/'workspace/private/runs/s22plus-native-session-v3/p399-p400-native-ext4-20260917-1'
STEPS=('android-download','candidate-boot','debian-shutdown','native-return','android-restore')
OBSERVATIONS=('debian-health','native-health')


def producer_artifact():
    return read(verify(ARTIFACT))['p401_artifact']


def native_source_paths():
    """Bind the local import closure of P399 admission and native observation."""
    base=Path(__file__).parent
    pending=['s22plus_native_adapter_v3','s22plus_native_host_v3',
        's22plus_native_observation_v3']
    found=set()
    while pending:
        path=base/(pending.pop()+'.py')
        if not path.is_file() or path in found:continue
        found.add(path)
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node,ast.Import):names=[alias.name.split('.')[0] for alias in node.names]
            elif isinstance(node,ast.ImportFrom) and node.module:
                names=[node.module.split('.')[0]]
            else:continue
            pending.extend(name for name in names if (base/(name+'.py')).is_file())
    return found


def recovery_sources():
    return sorted(set(old.source_paths()) | {Path(__file__),POLICY,COMMON,TARGET,
        ROOT/'AGENTS.md'})


def sources():
    return sorted(set(recovery_sources()) | native_source_paths() | {
        Path(__file__), POLICY, COMMON, TARGET, ROOT/'AGENTS.md',
        ROOT/'workspace/public/src/debian/s22plus_v1/handoff.c',
        ROOT/'workspace/public/src/debian/s22plus_v1/device/target.inc.c',
        ROOT/'workspace/public/src/debian/s22plus_v1/device/installed_prepare.py',
        ROOT/'workspace/public/src/debian/s22plus_v1/device/installed_vm_test.py',
        ROOT/'workspace/public/src/scripts/revalidation/s22plus_debian_installed_artifact_v1.py',
        ROOT/'workspace/public/src/device-action/profiles/s22plus_fyg8.json',
        ROOT/'docs/operations/DEVICE_ACTION_PROCESS_V2.md',
        ROOT/'docs/operations/DEVICE_ACTION_RISK_TIERS.md'})


def capability(*,recovery=None):
    value=read(verify(recovery)) if recovery is not None else read(REVIEW)
    require(set(value)=={'schema','verdict','scope','sources','findings','reviewer'} and
        value['schema']==SCHEMA+'-review' and value['verdict']=='PASS_GO' and
        value['scope']=='REACHABLE_OWNER_AND_BOUNDARY' and value['findings']==[],
        'installed Debian owner has no current independent review')
    listed=value['sources']
    require(type(listed) is list and len({item['path'] for item in listed})==len(listed),
        'reviewed installed Debian source list is malformed')
    if recovery is not None:
        indexed={item['path']:item for item in listed}
        for path in recovery_sources():
            require(str(path) in indexed,'frozen A recovery omits a reviewed source')
            verify(indexed[str(path)],maximum=4*1024*1024)
    else:
        require(listed==[pin(p,maximum=4*1024*1024) for p in sources()],
            'prospective installed Debian source closure differs')
        require(POLICY.read_bytes().startswith(b'# S22+ installed Debian') and
            b'Status: **REVIEW_GATED_CAPABILITY**' in POLICY.read_bytes() and
            POLICY.name.encode() in COMMON.read_bytes() and
            POLICY.name.encode() in TARGET.read_bytes() and
            digest(COMMON.read_bytes()).encode() in (ROOT/'AGENTS.md').read_bytes(),
            'installed Debian scope is not common-incorporated and target-adopted')
    return recovery if recovery is not None else pin(REVIEW)


def native_close_capability(original_review,plan):
    """A healthy P399 terminal needs more than the frozen A-only closure."""
    reviewed=read(verify(original_review))
    indexed={item['path']:item for item in reviewed['sources']}
    for path in native_source_paths():
        require(str(path) in indexed,'frozen native closure omits a source')
        verify(indexed[str(path)],maximum=4*1024*1024)
    import s22plus_native_adapter_v3 as native_adapter
    task=read(verify(plan['native_task']))
    native_adapter.image_valid(plan['N'],artifact_bytes=True)
    native_adapter.Adapter(ROOT,P399/'operation-0001').admission(
        plan['admission'],plan['N'],task)
    require(task['N']==plan['N'] and task['A']==plan['A'],
        'frozen P399 normal return or original A differs')


def candidate_identity(plan, binding):
    image=plan['candidate']
    return registry.derive_candidate_identity({'target':dict(model='SM-S906N',device='g0q')},
        dict(manifest_id='s22plus-debian-installed-boot-v1',run_id=image['run_id'],
            candidate_ap=image['ap'],allowed_member='boot.img.lz4'),image['ap']['sha256'],
        approval_binding_sha256=binding,candidate_receipt=dict(size=image['ap']['size'],
            sha256=image['ap']['sha256'],member=image['member']))


def inspect_inputs():
    import s22plus_native_adapter_v3 as native_adapter
    artifact=read(verify(ARTIFACT));qualified=read(verify(QUALIFIED))
    require(qualified['artifact']==ARTIFACT and
        qualified['verdict']=='PASS_H0_INSTALLED_BOOT_ARTIFACT_AND_ARM64_VM'
        and qualified['device_actions']==0 and artifact['grants_device_authority'] is False,
        'P404 actual H0 qualification differs')
    prior,basis=old.retained_basis()
    # The exact P401 plan is retained by its consumed terminal, independent of
    # the moving old runner and of P404's new candidate identity.
    terminal=read(P401_PLAN.parent/'terminal.json')
    require(terminal['plan']==pin(P401_PLAN) and
        terminal['terminal_state']=='ANDROID_CLOSED_HEALTHY' and
        terminal['verdict']=='NO_PROOF_ANDROID_CLOSED_HEALTHY',
        'P401 consumed root owner differs')
    prior_plan=read(verify(terminal['plan']))
    task=read(P399/'task.json');image=task['N']
    native_adapter.image_valid(image,artifact_bytes=True)
    native_adapter.Adapter(ROOT,P399/'operation-0001').admission(
        pin(P399/'operation-0001/admission.json'),image,task)
    require(task['target']==prior['target'] and task['A']==prior['A'] and
        image['ap']['sha256']==artifact['baseline_native']['ap']['sha256'],
        'P399 selected baseline is not the same target and original A')
    return artifact,prior_plan,prior,basis,task


def plan(output):
    """Publish only a proposal after review; no grant or device contact."""
    output=private_path(ROOT,output,exists=False)
    require(not output.exists(),'installed Debian task path already exists')
    artifact,old_plan,prior,basis,native_task=inspect_inputs()
    review=capability()
    with transport.pin_boot_only_ap(Path(artifact['ap']['path']),label='P404 candidate',
            expected_size=artifact['ap']['size'],expected_sha256=artifact['ap']['sha256']) as ap:
        member=transport.boot_only_member_receipt(ap,label='P404 candidate')
    plan=dict(schema=SCHEMA,directory=str(output),seconds=3600,review=review,
        candidate=dict(ap=artifact['ap'],member=member,run_id=artifact['run_id']),
        root_run_id=old_plan['candidate']['run_id'],installed_root=producer_artifact(),
        artifact=ARTIFACT,qualification=QUALIFIED,source_terminal=old.PRIOR_CLOSED,
        target=prior['target'],lane=target.lane.capture_binding(target.lane.SOURCE_TOPOLOGY),
        A=prior['A'],N=native_task['N'],admission=pin(P399/'operation-0001/admission.json'),
        native_task=pin(P399/'task.json'),basis=old_plan['basis'],
        link=old_plan['link'],network_uuid=old_plan['network_uuid'],
        client_key=old_plan['client_key'],known_hosts=old_plan['known_hosts'],
        nmcli=old_plan['nmcli'],ssh=old_plan['ssh'],odin=old_plan['odin'],adb=old_plan['adb'],
        host_installation=native_task['host_installation'])
    validate_plan(plan)
    output.mkdir(mode=0o700)
    receipt=publish(output/'plan.json',plan)
    publish(output/'proposal.json',dict(plan=receipt,operations=1,seconds=3600,
        attended=True,grants_device_authority=False))
    return receipt


def validate_plan(plan,*,recovery=False,static_only=False):
    require(not static_only or recovery,'static-only plan check is recovery-only')
    keys={'schema','directory','seconds','review','candidate','root_run_id','installed_root',
        'artifact','qualification','source_terminal','target','lane','A','N','admission',
        'native_task','basis','link','client_key','known_hosts','nmcli','ssh','odin','adb',
        'host_installation','network_uuid'}
    require(set(plan)==keys and plan['schema']==SCHEMA and plan['seconds']==3600 and
        Path(plan['directory']).is_relative_to(ROOT/'workspace/private') and
        plan['source_terminal']==old.PRIOR_CLOSED and
        plan['review']==capability(recovery=plan['review'] if recovery else None),
        'installed Debian task identity differs')
    if recovery:
        # An intended transfer owns its recovery even if candidate-only sources,
        # qualification or P399 inputs later drift. Keep the A and owner closure.
        terminal=read(P401_PLAN.parent/'terminal.json')
        require(terminal['plan']==pin(P401_PLAN),'retained P401 plan differs')
        old_plan=read(verify(terminal['plan']))
        prior,_=old.retained_basis()
        require(plan['A']==prior['A'] and plan['target']==prior['target'] and
            plan['basis']==old_plan['basis'] and
            all(plan[key]==old_plan[key] for key in
                ('link','network_uuid','client_key','known_hosts','nmcli','ssh','odin','adb')),
            'installed Debian A recovery binding differs')
        if not static_only:
            target.lane.revalidate_binding(plan['lane'],source_topology=target.lane.SOURCE_TOPOLOGY)
        return plan
    image,old_plan,prior,basis,native_task=inspect_inputs()
    require(plan['artifact']==ARTIFACT and plan['qualification']==QUALIFIED and
        plan['candidate']==dict(ap=image['ap'],member=plan['candidate']['member'],run_id=image['run_id'])
        and plan['root_run_id']==old_plan['candidate']['run_id']
        and plan['installed_root']==producer_artifact()
        and plan['target']==prior['target'] and plan['A']==prior['A']
        and plan['N']==native_task['N'] and plan['native_task']==pin(P399/'task.json')
        and plan['admission']==pin(P399/'operation-0001/admission.json')
        and plan['basis']==old_plan['basis']
        and all(plan[key]==old_plan[key] for key in ('link','network_uuid','client_key','known_hosts','nmcli','ssh','odin','adb'))
        and plan['host_installation']==native_task['host_installation'],
        'installed root or native return artifacts differ')
    with transport.pin_boot_only_ap(Path(image['ap']['path']),label='P404 candidate',
            expected_size=image['ap']['size'],expected_sha256=image['ap']['sha256']) as ap:
        require(transport.boot_only_member_receipt(ap,label='P404 candidate')==plan['candidate']['member'],
            'P404 AP member differs')
    target.lane.revalidate_binding(plan['lane'],source_topology=target.lane.SOURCE_TOPOLOGY)
    return plan


def journal_state(journal):
    effects,completed,observed={}, {}, {}
    stopped=False;armed=False;terminal=False;opened=False
    native_auth=False;native_detach=False;statements=set()
    for row in journal.rows():
        event,data=row['event'],row['data']
        require(not terminal,'installed Debian journal continues after terminal')
        if event=='owner-opened':
            require(not opened and not effects and not completed and not observed,
                'installed Debian owner opening is duplicated or late')
            opened=True
            continue
        if event=='effect-intent':
            step=data['step']
            require(set(data)=={'step','detail'} and step in STEPS and step not in effects,
                'unknown or repeated installed Debian effect')
            prerequisites={'android-download':(), 'candidate-boot':('android-download',),
                'debian-shutdown':('candidate-boot',),'native-return':('debian-shutdown',),
                'android-restore':()}
            require(opened and all(name in completed for name in prerequisites[step]) and
                (step=='android-restore' or not stopped and 'android-restore' not in effects) and
                (step not in ('debian-shutdown','native-return') or 'debian-health' in observed) and
                (step!='native-return' or armed and 'P399' in statements) and
                (step!='android-restore' or 'A' in statements),
                'installed Debian effect is out of order')
            effects[step]=row
        elif event=='effect-result':
            step=data['step']
            require(set(data)=={'step','receipt'} and step in effects and step not in completed,
                'result lacks a unique original intent')
            completed[step]=data['receipt']
        elif event=='observation':
            step=data['step']
            require(set(data)=={'step','receipt'} and step in OBSERVATIONS and step not in observed and
                (step!='debian-health' or 'candidate-boot' in completed) and
                (step!='native-health' or 'native-return' in completed and
                    native_auth and native_detach),
                'observation lacks its exact predecessor')
            observed[step]=data['receipt']
        elif event=='research-stopped':
            require(opened and not stopped,'research stop is duplicate or ownerless')
            stopped=True
        elif event=='native-return-armed':
            require(not armed and 'debian-shutdown' in completed and not stopped,
                'normal native return is not ready')
            armed=True
        elif event=='physical-statement':
            role=data.get('role')
            require(opened and role in ('P399','A') and role not in statements and
                type(data.get('statement')) is str and data['statement'].strip() and
                (role!='P399' or armed and not stopped),
                'physical return statement differs')
            statements.add(role)
        elif event=='physical-reaffirmed':
            require(opened and data.get('role')=='A' and 'A' in statements and
                'android-restore' not in effects and
                type(data.get('statement')) is str and data['statement'].strip(),
                'pre-intent A attendance reaffirmation differs')
        elif event=='native-auth-intent':
            require('native-return' in completed and not native_auth and not stopped,
                'native authentication may not replay')
            native_auth=True
        elif event=='native-detach-intent':
            require(native_auth and not native_detach and not stopped,
                'native DETACH is out of order')
            native_detach=True
        elif event=='terminal':
            require(opened and not terminal and
                ('native-health' in observed or 'android-restore' in completed or
                    not effects and stopped),
                'terminal has no return path')
            terminal=True
        else:require(False,'unknown installed Debian journal event')
    return effects,completed,observed,stopped,armed


def open_grant(directory,*,operator_statement):
    directory=private_path(ROOT,directory,exists=True)
    plan_value=read(directory/'plan.json')
    validate_plan(plan_value)
    require(type(operator_statement) is str and operator_statement.strip(),
        'actual attended operator grant is absent')
    grant=dict(schema=SCHEMA+'-grant',plan=pin(directory/'plan.json'),
        operator_statement=operator_statement,attended=True,host_boot=host_boot(),
        opened_ns=clock(),deadline_ns=0)
    grant['deadline_ns']=grant['opened_ns']+plan_value['seconds']*1_000_000_000
    return publish(directory/'grant.json',grant)


def validate_grant(grant,plan_receipt,*,current):
    require(set(grant)=={'schema','plan','operator_statement','attended','host_boot',
        'opened_ns','deadline_ns'} and grant['schema']==SCHEMA+'-grant' and
        grant['plan']==plan_receipt and grant['attended'] is True and
        type(grant['operator_statement']) is str and grant['operator_statement'].strip() and
        type(grant['opened_ns']) is int and type(grant['deadline_ns']) is int and
        grant['deadline_ns']==grant['opened_ns']+3600_000_000_000,
        'installed Debian finite grant differs')
    if current:
        require(grant['host_boot']==host_boot() and grant['opened_ns']<=clock()<grant['deadline_ns'],
            'original installed Debian task window expired')


def installed_health_projection(handle,plan):
    require(handle.returncode==0 and not handle.timed_out and
        not handle.output_exceeded and handle.producer_error_type is None and
        not raw.read_stderr(handle,maximum=16384),
        'installed Debian health producer failed')
    output=raw.read_stdout(handle,maximum=65536)
    wanted=('S22PLUS_FYG8_DEBIAN_V1 '+plan['root_run_id']+'\n').encode()
    require(output.startswith(wanted) and output.endswith(b'DEBIAN_HEALTH_PASS\n') and
        output.count(b'pid1_exe=/usr/sbin/init\n')==1 and
        output.count(b'pid1_root=/\n')==1 and
        output.count(b'BOOTSTRAP_HANDOFF pid=1 children=0 backend=s22plus-fyg8\n')==1 and
        b'DEBIAN_INSTALL_INTENT_DURABLE' not in output and
        b'DEBIAN_INSTALL_COMPLETE' not in output,
        'installed root handoff or authenticated Debian PID 1 differs')
    boot=re.findall(rb'^boot_id=([0-9a-f-]{36})$',output,re.M)
    count=re.findall(rb'^boot_count=([1-9][0-9]*)$',output,re.M)
    require(len(boot)==len(count)==1 and target.UUID.fullmatch(boot[0].decode())
        and int(count[0])<=100000,'Debian boot identity or count differs')
    return dict(status='PASS_INSTALLED_DEBIAN_PID1',boot_id_sha256=digest(boot[0]),
        boot_count=int(count[0]),root_run_id=plan['root_run_id'],
        capture=pin(handle.receipt_path))


class Owner(old.Owner):
    def __init__(self,directory,*,recovery=False):
        self.directory=private_path(ROOT,directory,exists=True)
        self.plan_receipt=pin(self.directory/'plan.json')
        self.plan=read(self.directory/'plan.json')
        require(self.plan['directory']==str(self.directory),
            'installed Debian plan belongs to another task directory')
        self.recovery=recovery
        self.journal=old.Journal(self.directory/'journal',schema=SCHEMA)
        self.grant=read(self.directory/'grant.json') if (self.directory/'grant.json').exists() else None

    def guard(self,*,owned=True):
        validate_plan(self.plan,recovery=self.recovery)
        if self.grant is not None:
            validate_grant(self.grant,self.plan_receipt,current=not self.recovery)
        if owned:
            require(self.grant is not None,'installed Debian grant is absent')
            registry.require_f1_owner(ROOT,self.directory,self.plan_receipt['sha256'])
            opening=[row for row in self.journal.rows() if row['event']=='owner-opened']
            require(len(opening)==1 and opening[0]['data']==dict(
                plan=self.plan_receipt,grant=pin(self.directory/'grant.json')),
                'installed Debian owner opening differs')
        target.lane.revalidate_binding(self.plan['lane'],source_topology=target.lane.SOURCE_TOPOLOGY)
        journal_state(self.journal)

    def intent(self,step,detail):
        self.guard()
        require(step not in journal_state(self.journal)[0],'installed Debian effect was already intended')
        self.journal.append('effect-intent',step=step,detail=detail)

    def observed_debian(self,endpoint):
        folder=self.folder('debian-health-reads')
        deadline=min(self.grant['deadline_ns'],clock()+180_000_000_000)
        ordinal=0
        while clock()<deadline:
            ordinal+=1
            handle=self.ssh('health',folder,f'health-{ordinal:03d}',endpoint=endpoint)
            output=raw.read_stdout(handle,maximum=65536)
            wanted=('S22PLUS_FYG8_DEBIAN_V1 '+self.plan['root_run_id']+'\n').encode()
            if output.startswith(b'S22PLUS_FYG8_DEBIAN_V1 '):
                require(output.startswith(wanted),'installed root reports another identity')
            if handle.returncode!=0 or handle.timed_out or handle.output_exceeded or handle.producer_error_type:
                time.sleep(1);continue
            value=installed_health_projection(handle,self.plan)
            require(self.usb_link()==endpoint,
                'Debian physical endpoint continuity differs')
            value['endpoint']=endpoint
            self.result('debian-health',value,observation=True)
            return value
        raise TimeoutError('installed Debian health did not complete within the original deadline')

    def artifact_for(self,step):
        return (self.plan['candidate']['ap'] if step=='candidate-boot' else
            self.plan['N']['ap'] if step=='native-return' else self.plan['A']['ap'])

    def transfer(self,step):
        require(step in ('candidate-boot','native-return','android-restore'),
            'unselected installed Debian transfer')
        artifact=self.artifact_for(step)
        base=self.folder(step+'-transfer')
        require(step not in journal_state(self.journal)[0],'boot transfer intent already exists')
        folder=base/('attempt-'+uuid.uuid4().hex)
        folder.mkdir(mode=0o700)
        endpoints=folder/'endpoints';endpoints.mkdir(mode=0o700)
        deadline=clock()+90_000_000_000
        if step!='android-restore':deadline=min(deadline,self.grant['deadline_ns'])
        with transport.pin_regular_file(Path(self.plan['odin']['path']),label='Odin',
                expected_size=self.plan['odin']['size'],expected_sha256=self.plan['odin']['sha256']) as odin, \
             transport.pin_boot_only_ap(Path(self.plan['A']['ap']['path']),label='original Android A',
                expected_size=self.plan['A']['ap']['size'],expected_sha256=self.plan['A']['ap']['sha256'],
                require_deterministic_metadata=False) as recovery, \
             transition.transaction_session(endpoints) as lease:
            def observer():
                self.guard();transport.revalidate_pinned_path(odin)
                return transition.measured_usbfs_observer(endpoints)
            found=transition.wait_for_single_live_endpoint(odin.path,endpoints,
                timeout_sec=max(0,(deadline-clock())/1e9),lease=lease,
                endpoint_observer_factory=observer,monotonic=lambda:clock()/1e9)
            require(found.ticket is not None and not found.timed_out,
                'exact attended Download endpoint did not arrive')
            ticket=found.ticket;identity=target.download_identity(ticket.device)
            def before_launch():
                self.guard()
                checked=transition.revalidate_endpoint_ticket(odin.path,endpoints,ticket,
                    sequence=found.next_sequence,lease=lease,timeout_sec=10,
                    endpoint_observer_factory=observer,monotonic=lambda:clock()/1e9)
                require(target.download_identity(ticket.device)==identity and clock()<deadline,
                    'Download identity or original arrival deadline changed')
                transport.revalidate_pinned_path(recovery)
                if step=='candidate-boot':
                    claim=registry.claim(ROOT,candidate_identity(self.plan,self.plan_receipt['sha256']))
                    publish(self.directory/'candidate-claim.json',claim)
                elif step=='native-return':
                    import s22plus_native_adapter_v3 as native_adapter
                    original=read(verify(self.plan['native_task']))
                    native_adapter.Adapter(ROOT,P399/'operation-0001').admission(
                        self.plan['admission'],self.plan['N'],original)
                invocation=publish(folder/'invocation.json',dict(
                    command=transport.build_odin_boot_only_command(
                        odin.path,Path(artifact['path']),ticket.device),
                    odin=self.plan['odin'],ap=artifact,ticket=asdict(ticket)))
                detail=dict(ap=artifact,ticket=asdict(ticket),endpoint=identity,
                    endpoint_revalidation=checked,capture_directory=str(folder),
                    invocation=invocation,
                    p399_admission=self.plan['admission'] if step=='native-return' else None)
                self.intent(step,detail)
            receipt,handle=transport.execute_odin_boot_only(odin.path,Path(artifact['path']),ticket.device,
                odin_size=self.plan['odin']['size'],odin_sha256=self.plan['odin']['sha256'],
                ap_size=artifact['size'],ap_sha256=artifact['sha256'],label=step,
                require_deterministic_metadata=step!='android-restore',capture_dir=folder,
                capture_name='odin',stdout_name='stdout.bin',stderr_name='stderr.bin',
                before_launch=before_launch)
        publish(folder/'transport.json',receipt)
        target.transfer_completed(handle)
        return self.result(step,dict(transport=pin(folder/'transport.json'),raw=pin(handle.receipt_path)))

    def transfer_proved(self,step):
        effects,_,_,_,_=journal_state(self.journal)
        if step not in effects:return False
        detail=effects[step]['data']['detail'];folder=Path(detail['capture_directory'])
        require(folder.parent==self.directory/(step+'-transfer') and
            re.fullmatch(r'attempt-[0-9a-f]{32}',folder.name) and
            detail['ap']==self.artifact_for(step),
            'retained transfer path or image differs')
        invocation_path=verify(detail['invocation'])
        require(invocation_path==folder/'invocation.json' and
            read(invocation_path)==dict(command=transport.build_odin_boot_only_command(
                Path(self.plan['odin']['path']),Path(detail['ap']['path']),
                detail['ticket']['device']),odin=self.plan['odin'],
                ap=detail['ap'],ticket=detail['ticket']),
            'prelaunch Odin invocation is not bound to the original intent')
        path=folder/'odin.capture.json'
        if not path.exists():return False
        try:
            capture=read(path)
            require(capture['argv0_name']==Path(self.plan['odin']['path']).name and
                capture['name']=='odin','raw producer identity differs')
            target.transfer_completed(raw.load_handle(path))
            transport_path=folder/'transport.json'
            if transport_path.exists():
                saved=read(transport_path)
                require(saved['odin']==self.plan['odin'] and saved['ap']==detail['ap'] and
                    saved['raw_capture_receipt']==pin(path) and saved['label']==step and
                    saved['command_shape']==['odin4','--reboot','-a','AP.tar.md5','-d','USBFS'],
                    'published transport differs from intent and raw producer')
            return True
        except (ValueError,OSError,raw.RawCaptureError):return False

    def transfer_result(self,step):
        effects,completed,_,_,_=journal_state(self.journal)
        require(step in completed and self.transfer_proved(step),
            'retained transfer is not completed and proved')
        folder=Path(effects[step]['data']['detail']['capture_directory'])
        path=verify(completed[step])
        require(path==self.directory/(step+'.json'),
            'effect result is not the original transfer result')
        value=read(path)
        expected=dict(raw=pin(folder/'odin.capture.json'),
            transport=pin(folder/'transport.json') if (folder/'transport.json').exists() else None)
        if value.get('resumed_from_original_raw') is True:
            expected['resumed_from_original_raw']=True
        require(value==expected,'stored transfer result differs from original raw/transport')
        return value

    def finish_proved_transfer(self,step):
        require(step in ('candidate-boot','native-return','android-restore'),
            'unselected transfer reconciliation')
        effects,completed,_,_,_=journal_state(self.journal)
        require(step in effects and self.transfer_proved(step),
            'original transfer dispatch is not proved; it cannot be replayed')
        if step in completed:
            self.transfer_result(step)
            return completed[step]
        folder=Path(effects[step]['data']['detail']['capture_directory'])
        raw_receipt=pin(folder/'odin.capture.json')
        transport_path=folder/'transport.json'
        transport_receipt=pin(transport_path) if transport_path.exists() else None
        result_path=self.directory/(step+'.json')
        if result_path.exists():
            stored=read(result_path)
            require(stored['raw']==raw_receipt and stored['transport']==transport_receipt,
                'published result differs from the proved original transfer')
            receipt=pin(result_path)
        else:
            receipt=publish(result_path,dict(raw=raw_receipt,transport=transport_receipt,
                resumed_from_original_raw=True))
        self.journal.append('effect-result',step=step,receipt=receipt)
        self.transfer_result(step)
        return receipt

    def finish_proved_a_transfer(self):
        return self.finish_proved_transfer('android-restore')

    def shutdown_projection(self):
        effects,_,observed,_,_=journal_state(self.journal)
        require('debian-shutdown' in effects and 'debian-health' in observed,
            'shutdown has no original intent and Debian health')
        folder=self.directory/'debian-shutdown-io'
        handle=raw.load_handle(folder/'command.capture.json')
        value=old.control_projection(handle,'shutdown',self.plan['link']['ssh_address'])
        departure=pin(folder/'departure.json')
        detail=read(verify(departure))
        health=read(verify(observed['debian-health']))
        require(set(detail)=={'endpoint','observed_boottime_ns','method'} and
            detail['endpoint']==health['endpoint'] and
            detail['method']=='NCM_ENDPOINT_ABSENT' and
            type(detail['observed_boottime_ns']) is int and
            detail['observed_boottime_ns']>0,
            'shutdown departure does not match the authenticated Debian endpoint')
        value['departure']=departure
        return value

    def finish_proved_shutdown(self):
        _,completed,_,_,_=journal_state(self.journal)
        value=self.shutdown_projection()
        path=self.directory/'debian-shutdown.json'
        if 'debian-shutdown' in completed:
            require(verify(completed['debian-shutdown'])==path and read(path)==value,
                'completed shutdown result differs from original raw/departure')
            return completed['debian-shutdown']
        if path.exists():
            require(read(path)==value,'published shutdown result differs')
            receipt=pin(path)
        else:receipt=publish(path,value)
        self.journal.append('effect-result',step='debian-shutdown',receipt=receipt)
        return receipt

    def research_proof(self):
        effects,completed,observed,_,_=journal_state(self.journal)
        verify(self.plan['candidate']['ap'],maximum=128*1024*1024)
        require('candidate-boot' in completed and self.transfer_proved('candidate-boot') and
            'debian-health' in observed and 'debian-shutdown' in completed,
            'installed Debian research predecessor is incomplete')
        self.transfer_result('candidate-boot')
        health=read(verify(observed['debian-health']))
        require(health==dict(installed_health_projection(
            raw.load_handle(verify(health['capture'])),self.plan),endpoint=health['endpoint']) and
            health['root_run_id']==self.plan['root_run_id'],
            'original installed Debian PID 1 raw health does not rederive')
        require(verify(completed['debian-shutdown'])==self.directory/'debian-shutdown.json' and
            read(self.directory/'debian-shutdown.json')==self.shutdown_projection(),
            'original orderly shutdown and USB departure do not rederive')
        claim=read(self.directory/'candidate-claim.json')
        identity=candidate_identity(self.plan,self.plan_receipt['sha256'])
        require(registry.active_claim(ROOT,identity['candidate_key'])==claim['record'],
            'new P404 boot candidate claim differs')
        return health

    def returned_native_health(self):
        import s22plus_native_host_v3 as native_host
        import s22plus_native_observation_v3 as native
        require(self.transfer_proved('native-return'),
            'native restoration has no complete original transfer')
        import s22plus_native_ext4_profile_v1 as fs
        folder=self.folder('native-health-io')
        installation=read(verify(self.plan['host_installation']))
        host=native_host.NativeHost(installation,folder/'host')
        host.holders(expected_run=self.plan['N']['run_id_hex'])
        self.journal.append('native-auth-intent',image=self.plan['N']['ap'])
        debian=read(self.directory/'debian-health.json')
        value=native.observe(folder,self.plan['N'],host,ending='detach',hud=False,
            guard=self.guard,before_terminal=lambda:self.journal.append('native-detach-intent',
                image=self.plan['N']['ap']),first_boot=True,
            seen_boots=(debian['boot_id_sha256'],),profile='filesystem-verify')
        require(value['proof']['filesystem']['status']=='PASS_READONLY_WITNESS_CLEAN_UNMOUNT',
            'P399 returned without its clean read-only witness')
        self.result('native-health',value,observation=True)
        return value

    def finish_proved_native_health(self,health):
        import s22plus_native_observation_v3 as native
        effects,completed,observed,_,_=journal_state(self.journal)
        events=[row['event'] for row in self.journal.rows()]
        require('native-return' in completed and
            events.count('native-auth-intent')==1 and
            events.count('native-detach-intent')==1,
            'native result lacks unique authentication and DETACH intents')
        value=native.rederive(self.directory/'native-health-io',self.plan['N'],
            ending='detach',hud=False,first_boot=True,
            seen_boots=(health['boot_id_sha256'],),profile='filesystem-verify')
        require(value['proof']['filesystem']['status']==
            'PASS_READONLY_WITNESS_CLEAN_UNMOUNT',
            'retained native observation lacks its clean witness')
        path=self.directory/'native-health.json'
        if path.exists():
            require(read(path)==value,'published native health differs from raw proof')
            receipt=pin(path)
        else:receipt=publish(path,value)
        if 'native-health' in observed:
            require(observed['native-health']==receipt,
                'journaled native health points to another result')
        else:self.journal.append('observation',step='native-health',receipt=receipt)
        return receipt

    def execute(self):
        require(not self.journal.rows(),'started installed-Debian owner may not replay')
        with registry.target_session_lease(ROOT):
            registry.require_no_f1_owner(ROOT)
            self.guard(owned=False)
            require(self.grant is not None,'attended grant is absent')
            registry.preflight_candidate(ROOT,candidate_identity(self.plan,self.plan_receipt['sha256']))
            self.android_health('fresh-start',prepared=True)
            registry.begin_f1_owner(ROOT,self.directory,self.plan_receipt['sha256'])
            self.journal.append('owner-opened',plan=self.plan_receipt,grant=pin(self.directory/'grant.json'))
            try:
                folder=self.folder('android-download-io')
                before=target.usb_snapshot(target.lane.SOURCE_TOPOLOGY,folder)
                client=target.Android(self.plan['adb'],self.plan['target'],self.plan['A'],folder,guard=self.guard)
                deadline=clock()+30_000_000_000
                value=client.download(before_dispatch=lambda:self.intent('android-download',
                    dict(source=before,departure_deadline_ns=deadline)))
                value['departure']=target.wait_departure(before,folder,deadline_ns=deadline,guard=self.guard)
                self.result('android-download',value)
                self.transfer('candidate-boot')
                endpoint=self.network('network-first',create=True)
                health=self.observed_debian(endpoint)
                folder=self.folder('debian-shutdown-io')
                handle=self.ssh('shutdown',folder,'command',endpoint=endpoint,
                    before=lambda:self.intent('debian-shutdown',dict(health=pin(self.directory/'debian-health.json'))))
                accepted=old.control_projection(handle,'shutdown',self.plan['link']['ssh_address'])
                deadline=min(self.grant['deadline_ns'],clock()+60_000_000_000)
                while clock()<deadline and self.usb_link()==endpoint:
                    time.sleep(1)
                require(self.usb_link() is None,'Debian NCM did not depart after shutdown')
                accepted['departure']=publish(folder/'departure.json',dict(endpoint=endpoint,
                    observed_boottime_ns=clock(),method='NCM_ENDPOINT_ABSENT'))
                self.result('debian-shutdown',accepted)
                self.journal.append('native-return-armed',health=pin(self.directory/'debian-health.json'),
                    shutdown=pin(self.directory/'debian-shutdown.json'))
                print('WAIT_ATTENDED_PHYSICAL_DOWNLOAD_FOR_P399',flush=True)
            except BaseException as error:
                self.journal.append('research-stopped',error_type=type(error).__name__,message=str(error)[:512])
                if not journal_state(self.journal)[0]:
                    self._close_no_effect_held()
                raise

    def _close_no_effect_held(self):
        effects,_,_,stopped,_=journal_state(self.journal)
        require(not effects and stopped,'a device effect remains or research did not stop')
        validate_plan(self.plan,recovery=True,static_only=True)
        validate_grant(self.grant,self.plan_receipt,current=False)
        registry.require_f1_owner(ROOT,self.directory,self.plan_receipt['sha256'])
        opening=[row for row in self.journal.rows() if row['event']=='owner-opened']
        require(len(opening)==1 and opening[0]['data']==dict(
            plan=self.plan_receipt,grant=pin(self.directory/'grant.json')),
            'no-effect owner opening differs')
        expected=dict(schema=SCHEMA+'-terminal',
            terminal_state='NO_EFFECT_CLOSED',verdict='NO_DEVICE_EFFECT_CLOSED',
            plan=self.plan_receipt,grant=pin(self.directory/'grant.json'),
            research_closed=True,device_effects=0)
        path=self.directory/'terminal.json'
        if path.exists():
            require(read(path)==expected,'zero-effect terminal differs')
            terminal=pin(path)
        else:terminal=publish(path,expected)
        terminal_rows=[row for row in self.journal.rows() if row['event']=='terminal']
        require(len(terminal_rows)<=1 and
            (not terminal_rows or terminal_rows[0]['data']==dict(receipt=terminal)),
            'zero-effect terminal journal differs')
        if not terminal_rows:self.journal.append('terminal',receipt=terminal)
        registry.retire_f1_owner(ROOT,self.directory,self.plan_receipt['sha256'])
        return terminal

    def close_no_effect(self):
        require(self.recovery is True,'no-effect close needs retained recovery mode')
        with registry.target_session_lease(ROOT):
            effects,_,_,stopped,_=journal_state(self.journal)
            require(not effects,'no-effect close encountered a durable effect')
            if not self.journal.rows():
                validate_plan(self.plan,recovery=True,static_only=True)
                validate_grant(self.grant,self.plan_receipt,current=False)
                registry.require_f1_owner(ROOT,self.directory,self.plan_receipt['sha256'])
                require(not (self.directory/'candidate-claim.json').exists() and
                    not any((self.directory/(step+'-transfer')).exists() for step in
                        ('candidate-boot','native-return','android-restore')),
                    'zero-effect owner has later-stage artifacts')
                first=self.directory/'fresh-start/result.json'
                require(first.exists() and
                    read(first)==old.android_projection(self.directory/'fresh-start',self.plan),
                    'zero-effect owner lacks its completed initial health')
                self.journal.append('owner-opened',plan=self.plan_receipt,
                    grant=pin(self.directory/'grant.json'))
            if not stopped:
                validate_plan(self.plan,recovery=True,static_only=True)
                validate_grant(self.grant,self.plan_receipt,current=False)
                registry.require_f1_owner(ROOT,self.directory,self.plan_receipt['sha256'])
                require(not (self.directory/'candidate-claim.json').exists() and
                    not any((self.directory/(step+'-transfer')).exists() for step in
                        ('candidate-boot','native-return','android-restore')),
                    'zero-effect owner has later-stage artifacts')
                self.journal.append('research-stopped',error_type='HostCutBeforeFirstEffect',
                    message='durable owner with no device effect')
            return self._close_no_effect_held()

    def return_native(self,*,physical_statement):
        require(type(physical_statement) is str and physical_statement.strip(),
            'current physical Download attendance is absent')
        with registry.target_session_lease(ROOT):
            self.guard()
            effects,completed,observed,stopped,armed=journal_state(self.journal)
            require(armed and not stopped and 'native-return' not in effects and
                'debian-health' in observed and 'debian-shutdown' in completed,
                'normal P399 return is not eligible')
            self.research_proof()
            self.journal.append('physical-statement',role='P399',statement=physical_statement)
            try:
                self.transfer('native-return')
                self.returned_native_health()
                return self._close_native_held()
            except BaseException as error:
                if not any(row['event']=='terminal' for row in self.journal.rows()):
                    self.journal.append('research-stopped',error_type=type(error).__name__,message=str(error)[:512])
                raise

    def _close_native_held(self):
        self.guard()
        native_close_capability(self.plan['review'],self.plan)
        effects,completed,observed,stopped,_=journal_state(self.journal)
        require('android-restore' not in effects and 'native-return' in effects,
            'normal native closure lacks its one-shot return intent')
        self.finish_proved_transfer('candidate-boot')
        self.finish_proved_shutdown()
        self.finish_proved_transfer('native-return')
        health=self.research_proof()
        self.finish_proved_native_health(health)
        effects,completed,observed,stopped,_=journal_state(self.journal)
        value=read(verify(observed['native-health']))
        require(value['proof']['filesystem']['status']=='PASS_READONLY_WITNESS_CLEAN_UNMOUNT',
            'normal P399 health does not rederive from original raw evidence')
        expected=dict(schema=SCHEMA+'-terminal',
            terminal_state='NATIVE_CLOSED_HEALTHY',verdict='PASS_INSTALLED_DEBIAN_PID1_RETURNED_P399',
            plan=self.plan_receipt,grant=pin(self.directory/'grant.json'),
            debian_health=observed['debian-health'],native_health=observed['native-health'],
            candidate_transfer=completed['candidate-boot'],native_transfer=completed['native-return'],
            original_A_transfer=None,research_closed=True,normal_return=True)
        path=self.directory/'terminal.json'
        if path.exists():
            require(read(path)==expected,'published native terminal differs')
            terminal=pin(path)
        else:terminal=publish(path,expected)
        if not any(row['event']=='terminal' for row in self.journal.rows()):
            self.journal.append('terminal',receipt=terminal)
        registry.retire_f1_owner(ROOT,self.directory,self.plan_receipt['sha256'])
        self.cleanup_network()
        return terminal

    def close_native(self):
        require(self.recovery is True,'native close continuation needs retained recovery mode')
        with registry.target_session_lease(ROOT):
            return self._close_native_held()

    def reconcile(self,step):
        require(self.recovery is True and step in
            ('candidate-boot','native-return','debian-shutdown'),
            'read-only reconciliation step is unselected')
        with registry.target_session_lease(ROOT):
            self.guard()
            if step=='debian-shutdown':return self.finish_proved_shutdown()
            return self.finish_proved_transfer(step)

    def recover_android(self,*,physical_statement=None):
        require(self.recovery is True,'original-A recovery needs retained recovery mode')
        with registry.target_session_lease(ROOT):
            self.guard()
            effects,completed,observed,stopped,_=journal_state(self.journal)
            require(effects,
                'no unresolved installed-Debian effect remains')
            if 'android-restore' not in effects:
                require(type(physical_statement) is str and physical_statement.strip(),
                    'new original-A transfer requires current physical attendance')
                prior=any(row['event']=='physical-statement' and
                    row['data'].get('role')=='A' for row in self.journal.rows())
                self.journal.append('physical-reaffirmed' if prior else 'physical-statement',
                    role='A',statement=physical_statement)
                self.transfer('android-restore')
            self.finish_proved_a_transfer()
            if not (self.directory/'android-final.json').exists():
                final=self.android_health('android-final-'+uuid.uuid4().hex)
                publish(self.directory/'android-final.json',final)
            final=read(self.directory/'android-final.json')
            require(final==old.android_projection(Path(final['final_health']['path']).parents[1],self.plan),
                'final original-A health does not rederive')
            initial=read(self.directory/'fresh-start/result.json')
            require(initial==old.android_projection(self.directory/'fresh-start',self.plan) and
                final['boot_id_sha256']!=initial['boot_id_sha256'],
                'original-A restoration lacks a distinct healthy Android boot')
            self.cleanup_network()
            expected=dict(schema=SCHEMA+'-terminal',
                terminal_state='ANDROID_CLOSED_HEALTHY',verdict='NO_PROOF_ANDROID_CLOSED_HEALTHY',
                plan=self.plan_receipt,grant=pin(self.directory/'grant.json'),
                original_A_transfer_proved=True,final_health=pin(self.directory/'android-final.json'),
                research_closed=True,normal_return=False)
            path=self.directory/'terminal.json'
            if path.exists():
                require(read(path)==expected,'published Android terminal differs')
                terminal=pin(path)
            else:terminal=publish(path,expected)
            if not any(row['event']=='terminal' for row in self.journal.rows()):
                self.journal.append('terminal',receipt=terminal)
            registry.retire_f1_owner(ROOT,self.directory,self.plan_receipt['sha256'])
            return terminal


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='phase',required=True)
    item=sub.add_parser('prepare');item.add_argument('directory',type=Path)
    item=sub.add_parser('execute');item.add_argument('directory',type=Path);item.add_argument('--attended',action='store_true')
    item=sub.add_parser('native-return');item.add_argument('directory',type=Path)
    item.add_argument('--physical-statement',required=True)
    item=sub.add_parser('recover-android');item.add_argument('directory',type=Path)
    item.add_argument('--physical-statement')
    item=sub.add_parser('close-native');item.add_argument('directory',type=Path)
    item=sub.add_parser('close-no-effect');item.add_argument('directory',type=Path)
    item=sub.add_parser('reconcile');item.add_argument('directory',type=Path)
    item.add_argument('--step',required=True,
        choices=('candidate-boot','native-return','debian-shutdown'))
    args=parser.parse_args()
    if args.phase=='prepare': value=plan(args.directory)
    elif args.phase=='execute':
        require(args.attended is True,'installed Debian transfer needs actual attendance')
        value=Owner(args.directory).execute()
    elif args.phase=='native-return':value=Owner(args.directory).return_native(
        physical_statement=args.physical_statement)
    elif args.phase=='recover-android':value=Owner(args.directory,recovery=True).recover_android(
        physical_statement=args.physical_statement)
    elif args.phase=='close-native':value=Owner(args.directory,recovery=True).close_native()
    elif args.phase=='reconcile':value=Owner(args.directory,recovery=True).reconcile(args.step)
    else:value=Owner(args.directory,recovery=True).close_no_effect()
    if value is not None:print(value,flush=True)


if __name__=='__main__':main()
