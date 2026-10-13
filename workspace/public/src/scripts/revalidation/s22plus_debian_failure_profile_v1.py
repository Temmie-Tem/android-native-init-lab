"""Fixed supervised file variant; reuse the existing attended file owner."""
from pathlib import Path

import s22plus_debian_file_first_plan_v1 as plan
import s22plus_debian_file_profile_v1 as retained
import s22plus_debian_failure_protocol_v1 as protocol
import s22plus_debian_usb_protocol_v1 as primary
from s22plus_native_records_v3 import read,read_bytes,require,verify

PROFILE='debian-failure-observer-v1'
SCHEMA='s22plus-debian-failure-observer-v1'
POLICY='docs/operations/S22PLUS_DEBIAN_FILE_FIRST_V1.md'
WINDOW_SECONDS,TRANSFER_SECONDS,RETURN_SECONDS=retained.WINDOW_SECONDS,retained.TRANSFER_SECONDS,retained.RETURN_SECONDS
PENDING=retained.PENDING
FAULT_CASES=('begin-log','done-log','ram-sync','kernel-readback','worker-exit','worker-signal',
    'pending','late-return','parent-death','lost-diagnostic','unstable','interrupted')
CASES=('normal','insert-error',*FAULT_CASES,'short-write','file-sync-error','parent-sync-error','unmount-error',
    'dirty','wrong-uuid','existing-record','ram-log-missing','late-ro-clear','checker-timeout','readback-error','module-error')
PARTIAL_WRITES=retained.PARTIAL_WRITES+('readback-error',)
before_transfer=retained.before_transfer


def validate_adoption(root,details):
    from s22plus_debian_file_first_profile_v1 import validate_adoption as base_adoption
    base_adoption(root,details)
    for raw in (details,read_bytes(Path(root)/POLICY),
            read_bytes(Path(root)/'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md')):
        require(PROFILE.encode() in raw,'fixed supervised variant adoption absent')


def validate_case(row,built):
    """Actual stored C records are authoritative; metadata alone is insufficient."""
    case=row['case'];require(case in CASES,'unselected diagnostic case')
    raw=verify(row['raw'],maximum=16*1024**2).read_bytes().replace(b'\r',b'')
    require(b'FILE_VM_TERMINAL' not in raw and b'FILE_VM_RO' not in raw,'VM-only semantic footer is present')
    key=verify(built['key'],maximum=32).read_bytes();run=bytes.fromhex(built['run_id'])
    actual=protocol.decode(verify(row['raw'],maximum=16*1024**2).read_bytes(),key=key,run=run)
    require(actual==row['proof'],'diagnostic result does not rederive from raw')
    events=primary.retained(raw,key=key,run=run,domain=protocol.DOMAIN)
    require(events==row['primary'],'primary result does not rederive from raw')
    boots={value.get('kernel_boot_identity_sha256') for value in (actual,events)}-{None}
    require(len(boots)<=1,'VM channels belong to different authenticated boots')
    require(row['status']=='PASS' and row['device_actions']==0 and row['run_id']==built['run_id'] and
        row['outside_before']==row['outside_after'],'diagnostic confinement or identity differs')
    terminal={r['helper']:r for r in actual['records'] if r['sequence']==2}
    prep=terminal.get(1);writer=terminal.get(2)
    if case in ('lost-diagnostic','parent-death'):
        require(prep is None,'missing parent diagnostic was synthesized')
        if case=='parent-death':require(writer is None and row['disk_before']==row['disk_after'],'dead parent advanced writer')
        return
    require(prep is not None,'preparation terminal missing')
    fields=prep['fields']
    if case in ('normal','interrupted',*PARTIAL_WRITES,'dirty','wrong-uuid','existing-record',
            'ram-log-missing','late-ro-clear','checker-timeout','module-error'):
        require(prep['semantic_success'] and writer is not None,'preparation did not reach fixed writer')
        if case in ('normal','interrupted'):require(writer['semantic_success'],'normal writer did not complete')
        else:
            require(not writer['semantic_success'],'negative writer was successful')
            if case in ('dirty','wrong-uuid','existing-record','ram-log-missing','late-ro-clear','checker-timeout'):
                require(row['disk_before']==row['disk_after'],'rejected writer changed native_data')
            if case in ('dirty','wrong-uuid','existing-record','checker-timeout'):require(writer['fields']['result']==103,'admission failure lost')
            elif case=='ram-log-missing':require(writer['fields']['result']==102,'measurement failure lost')
            else:require(writer['fields']['result']==1,'writer failure lost')
            if case=='parent-sync-error':require(writer['fields']['first_log_failure_stage']==7 and
                writer['fields']['first_log_failure_errno']==5,'parent sync failure lost')
            if case in ('short-write','file-sync-error','parent-sync-error','readback-error'):
                stage={'short-write':4,'file-sync-error':5,'parent-sync-error':7,'readback-error':6}[case]
                require(writer['fields']['call_returns']==0 and writer['fields']['first_log_failure_stage']==stage and
                    writer['fields']['first_log_failure_errno']==5,'failed file evidence advanced clients or lost error')
            elif case=='unmount-error':require(writer['fields']['call_returns']==6 and
                writer['fields']['first_failure_phase']==11 and writer['fields']['first_failure_errno']==16,
                'unmount failure lost its cleanup boundary')
            elif case=='module-error':require(writer['fields']['call_returns']==3 and writer['fields']['call_rc']==-1 and
                writer['fields']['call_errno']==5,'client failure advanced later clients')
            if case=='checker-timeout':require(b'FILE_CHECKER_SETTLED owner_reaped=1 children=0\n' in raw,
                'checker timeout lacks actual child-settlement output')
    else:
        require(writer is None and row['disk_before']==row['disk_after'] and not prep['semantic_success'],
            'failed preparation advanced writable lifetime')
        if case=='insert-error':require(fields['call_returned']==1 and fields['call_rc']==-1 and
            fields['call_errno']==5 and fields['call_returns']==1,'module errno lost')
        elif case in ('begin-log','ram-sync'):require(fields['call_returns']==0 and
            fields['first_log_failure_errno']==5,'failed BEGIN evidence reached insertion')
        elif case in ('done-log','kernel-readback'):require(fields['call_returns']==1 and
            fields['call_returned']==1 and fields['call_rc']==0 and fields['call_errno']==0 and
            fields['first_log_failure_errno'] in (5,110),'log failure became module failure')
        elif case=='worker-exit':require(prep['exit_code']==77 and not fields['semantic_done'],'unexpected exit became completion')
        elif case=='worker-signal':require(prep['signal']==15,'signal outcome lost')
        elif case=='unstable':require(not prep['stable'] and fields is None and prep['signal']==15,'torn state asserted')
        elif case in ('pending','late-return'):
            require(prep['observation']=='WORKER_NOT_COLLECTED_AT_DEADLINE' and fields['phase']==3 and
                fields['call_returned']==0,'pending call gained return/cancellation proof')
    if case=='late-return':
        text=[r['event'].split(' ',2)[2] for r in events['records']]
        require(sum(e.startswith('MODULE_BEGIN ') for e in text)==1 and sum(e.startswith('MODULE_DONE ') for e in text)==1 and
            text[-1]=='TERMINAL result=REJECTED error=110','late return performed subsequent modules')


def vm_results(tested,built):
    from s22plus_debian_file_first_profile_v1 import virtual_artifact
    from s22plus_debian_file_protocol_v1 import decode
    sources={r['path']:r['sha256'] for r in tested['source_inputs']}
    require(tested['status']=='PASS' and tested['device_actions']==0 and
        [r['case'] for r in tested['cases']]==list(CASES),'diagnostic suite differs')
    for row in tested['cases']:
        virtual_artifact(row,built,sources,diagnostic=True);validate_case(row,built)
        if row['case'] in ('normal',*PARTIAL_WRITES,'module-error'):
            retrieved=row['file_retrieval'];reader=read(verify(retrieved['retrieval']))
            require(reader['disk_unchanged'] and reader['proof']['source_view_clean'] and not reader['proof']['mounted'],
                'later protected reader qualification absent')
            raw=bytes.fromhex(reader['proof']['files'][-1]['raw_hex'])
            arguments=dict(key=verify(built['key'],maximum=32).read_bytes(),run=bytes.fromhex(built['run_id']),
                expected=row['expected'],module_names=[m['runtime_name'] for m in built['modules']],
                storage_first=True,diagnostic=True,allow_prefix=row['case']!='normal')
            try:proof=decode(raw,**arguments)
            except ValueError as error:
                require(row['case']=='parent-sync-error','unexpected undecodable file');proof=dict(status='NO_AUTHENTICATED_FILE_PREFIX',error=str(error))
            require(proof==retrieved['proof'],'recovered file does not rederive')
            if proof['status']!='NO_AUTHENTICATED_FILE_PREFIX':
                require(proof['kernel_boot_identity_sha256']==row['proof']['kernel_boot_identity_sha256'],
                    'recovered VM file belongs to another authenticated boot')
            if row['case']=='normal':require(proof['pre_unmount_complete'] and proof['debian_early_pid1'] and
                not proof['unmount_return_proved'] and not proof['live_usb_proved'],'file proof scope differs')
            elif row['case']=='module-error':require(proof['client_return_records']==2 and
                proof['client_error']==dict(name='i2c_msm_geni',error=5) and not proof['pre_unmount_complete'],
                'client error file differs')
            elif row['case']=='parent-sync-error':require(proof['status']=='NO_AUTHENTICATED_FILE_PREFIX',
                'parent sync failure gained a file prefix')
            elif row['case']=='unmount-error':require(proof['pre_unmount_complete'] and not proof['unmount_return_proved'],
                'pre-unmount file became cleanup proof')
            else:require(not proof['pre_unmount_complete'] and proof['client_return_records']==0 and
                proof['client_attempt_records']==(0 if row['case']=='short-write' else 1),
                'failed file record advanced persisted clients')


def image_binding(image):return retained.image_binding(image,storage_first=True,diagnostic=True)


def decode(data,**kwargs):
    from s22plus_debian_file_protocol_v1 import decode as file_decode
    return file_decode(data,**kwargs,storage_first=True,diagnostic=True)


def decode_retained(raw,*,key,run):
    """Preserve two independent channel results even when either parser fails."""
    channels={};errors={}
    for name,decoder in (('diagnostic',protocol.decode),('primary',primary.retained)):
        try:
            channels[name]=decoder(raw if name=='diagnostic' else raw.replace(b'\r',b''),key=key,run=run,
                **(dict(domain=protocol.DOMAIN) if name=='primary' else {}))
        except ValueError as error:
            errors[name]=str(error)
            channels[name]=dict(status='MALFORMED_EVIDENCE',records=[],nonexecution_proved=False)
    boots={v.get('kernel_boot_identity_sha256') for v in channels.values()}-{None}
    consistent=len(boots)<=1
    have_diagnostic=channels['diagnostic'].get('status')=='AUTHENTICATED_DIAGNOSTICS'
    have_primary=bool(channels['primary']['records'])
    return dict(schema='s22plus-debian-failure-retained-v1',
        status='MIXED_AUTHENTICATED_BOOTS' if not consistent else 'AUTHENTICATED_FAILURE_DIAGNOSTICS' if have_diagnostic else
            'AUTHENTICATED_PRIMARY_PREFIX_ONLY' if have_primary else 'NO_AUTHENTICATED_OUTCOME',
        channels=channels,parse_errors=errors,authenticated_boot_consistent=consistent,
        retained_any_stage=bool(channels['diagnostic']['records']) or have_primary,
        initial_debian_pid1_measured=consistent and any(r.get('fields',{}).get('initial_pid1_measured')==1
            for r in channels['diagnostic']['records'] if r.get('fields')),
        installed_debian_pid1=False,stopped_at_last_record=False,nonexecution_proved=False,
        unmount_proved=False,descendant_settlement_proved=False,replay_authorized=False)
