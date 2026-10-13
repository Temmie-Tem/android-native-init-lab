"""H0 join of closed writer/reader operations and the exact captured run file."""
import argparse
import os
from pathlib import Path

import consumed_candidate_registry_v1 as registry
import s22plus_debian_file_profile_v1 as profile
import s22plus_debian_file_protocol_v1 as protocol
import s22plus_debian_file_first_profile_v1 as first_profile
import s22plus_debian_file_first_protocol_v1 as first_protocol
import s22plus_native_evidence_profile_v1 as evidence
import s22plus_native_target_io_v3 as target
from s22plus_native_adapter_v3 import Adapter,image_identity
from s22plus_native_session_v3 import Session,Step,operation_steps
from s22plus_native_records_v3 import pin,private_path,publish,read,require,verify

ROOT=evidence.ROOT


def original_claim(image,operation_sha256,claim):
    identity=image_identity(image,operation_sha256)
    require(claim['candidate_key']==identity['candidate_key'] and
        all(claim['record'].get(key)==value for key,value in identity.items() if key!='schema') and
        registry.active_claim(ROOT,identity['candidate_key'])==claim['record'],
        'candidate consumption is not bound to this image and operation')


def closed_operation(directory,selected_profile):
    directory=private_path(ROOT,directory);request=read(directory/'operation.json')
    require(request['N']['profile']==selected_profile,'offline evidence operation profile differs')
    task=read(verify(request['task']));grant=read(verify(request['grant']))
    task_directory=Path(request['task']['path']).parent
    closed=read(task_directory/'closed.json');terminal=read(directory/'terminal.json')
    require(task['N']==request['N'] and request['task']==grant['task'] and
        closed['task']==request['task'] and closed['grant']==request['grant'] and
        closed['terminal_state']=='ANDROID_CLOSED_HEALTHY' and closed['consumed_operations']==1 and
        closed['current_android_terminal']==pin(directory/'terminal.json') and
        terminal['operation_record']==pin(directory/'operation.json') and
        terminal['terminal_state']=='ANDROID_CLOSED_HEALTHY' and terminal['research_closed'] is True,
        'operation lacks its closed original-A outcome')
    adapter=Adapter(ROOT,directory);session=Session(ROOT,directory,adapter)
    require(session.consumed() is not None,'offline evidence has no original operation consumption')
    transfers=[r['data'] for r in session.rows() if r['event']=='effect-intent' and r['data']['action']=='transfer']
    require([row['role'] for row in transfers]==['N','A'],'offline evidence transfer ownership differs')
    session.completed((Step('install-native-first','transfer','N'),))
    plan=(Step(transfers[-1]['step'],'transfer','A'),Step('recovery-health','health','A')) if terminal['recovered'] else operation_steps(request)
    values=session.completed(plan)
    rederived=adapter.terminal(plan,values,request,recovered=terminal['recovered'])
    require(all(terminal.get(key)==value for key,value in rederived.items()),'stored terminal differs from raw proofs')
    initial=read(directory/'io-preflight/health.json')
    require(target.health_projection(initial['captures'],task['target'],task['A'])==initial,
        'original Android start does not rederive')
    returned=read(verify(values[-1]['health']))
    require(returned['boot_id_sha256']!=initial['boot_id_sha256'],'original-A return has no changed Android boot')
    claim=read(directory/'claim-N.json')
    original_claim(request['N'],pin(directory/'operation.json')['sha256'],claim)
    return dict(request=request,task=task,terminal=terminal,closed=pin(task_directory/'closed.json'),
        terminal_receipt=pin(directory/'terminal.json'),adapter=adapter,session=session)


def recover(directory,writer_directory,reader_directory):
    """Only existing raw captures are consumed. No transition or journal edit."""
    directory=private_path(ROOT,directory,exists=False)
    require(not directory.exists(),'fresh file projection output required')
    writer_profile=read(private_path(ROOT,writer_directory)/'operation.json')['N']['profile']
    require(writer_profile in (profile.PROFILE,first_profile.PROFILE),'unselected early file writer')
    selected_profile=first_profile if writer_profile==first_profile.PROFILE else profile
    selected_protocol=first_protocol if writer_profile==first_profile.PROFILE else protocol
    writer=closed_operation(writer_directory,writer_profile)
    reader=closed_operation(reader_directory,evidence.PROFILE)
    image=writer['request']['N'];artifact=selected_profile.image_binding(image)
    require(writer['task']['target']==reader['task']['target'] and writer['task']['A']==reader['task']['A'] and
        reader['request']['N']['root_evidence']['record_run']==image['run_id_hex'] and
        reader['request']['N']['run_id_hex']!=image['run_id_hex'],
        'reader is not the separate exact-target operation for this writer')
    step=next(s for s in operation_steps(reader['request']) if s.name==evidence.SELECTION)
    acquired=reader['session'].completed((step,))[0]['proof']['root_evidence']
    name='var/lib/lab/s22-evidence-'+image['run_id_hex']
    matches=[row for row in acquired['files'] if row['path']==name]
    require(len(matches)==1,'sealed run file is absent from reader declaration')
    selected=matches[0];directory.mkdir(mode=0o700)
    context=dict(schema='s22plus-debian-file-retrieval-h0-v1',writer_closed=writer['closed'],
        reader_closed=reader['closed'],writer_terminal=writer['terminal_receipt'],reader_terminal=reader['terminal_receipt'],
        writer_artifact=image['early_boot'],reader_result=pin(reader['adapter'].directory/(step.name+'.json')),
        source=pin(Path(__file__)),device_actions=0,writer_android_healthy=True,reader_android_healthy=True,
        source_view_clean=acquired['source_view_clean'],reader_journal_replayed=False,
        absence_proves_nonexecution=False,replay_authorized=False)
    publish(directory/'acquisition.json',dict(context,file=selected))
    if selected['status']!='READ':
        return publish(directory/'result.json',dict(context,status='NO_AUTHENTICATED_FILE',file_status=selected['status']))
    data=bytes.fromhex(selected['raw_hex']);path=directory/'record.bin'
    with path.open('xb') as stream:
        require(stream.write(data)==len(data),'short offline raw copy')
        stream.flush();os.fsync(stream.fileno())
    path.chmod(0o400)
    raw=pin(path);publish(directory/'raw.json',raw)
    arguments=dict(key=verify(image['key'],maximum=32).read_bytes(),run=bytes.fromhex(image['run_id_hex']),
        expected=artifact['expected'],module_names=artifact['module_names'])
    strict_error=None
    try:proof=selected_protocol.decode(data,**arguments)
    except ValueError as error:
        strict_error=str(error)
        try:proof=selected_protocol.decode(data,**arguments,allow_prefix=True)
        except ValueError as failure:
            return publish(directory/'result.json',dict(context,status='NO_AUTHENTICATED_FILE',raw=raw,
                strict_error=strict_error,prefix_error=str(failure)))
    return publish(directory/'result.json',dict(context,raw=raw,strict_error=strict_error,proof=proof,
        status='PASS_PERSISTED_EARLY_PID1_PRE_UNMOUNT' if proof['pre_unmount_complete'] else 'PARTIAL_PERSISTED_EARLY_PID1'))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','writer','reader'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=recover(args.output,args.writer,args.reader)
    print(read(verify(result))['status'])
