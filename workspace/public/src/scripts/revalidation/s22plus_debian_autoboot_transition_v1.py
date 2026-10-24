"""Independent bounded transition facts; missing records never locate a stall."""
import hashlib
import hmac
from pathlib import Path
import re
import struct

from s22plus_native_records_v3 import require

ROOT=Path(__file__).resolve().parents[5]
STAGES=ROOT/'workspace/public/src/native-init/s22plus_autoboot_transition_stages_v1.def'
DOMAIN=b'S22PLUS-FYG8-AUTOBOOT-TRANSITION-v1'
MAXIMUM=4*1024**2
LINE=re.compile(rb'S22AT1 run=([0-9a-f]{32}) boot=([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}) mac=([0-9a-f]{64}) data=([0-9a-f]{256})')
ACTORS={1:'file_worker',2:'automatic_entry',3:'ram_witness',4:'installed_hook',5:'file_supervisor'}
RCS_ACTORS={**ACTORS,6:'rcs_parent',7:'rcs_child'}
WATCHDOG_ACTORS={**RCS_ACTORS,8:'runlevel_parent'}
WATCHDOG_STAGES={79,80,81,82}
PHASE_STAGES=set(range(83,91))
SCRIPT_STAGES=set(range(91,96))
WATCHDOG_DUE=(0,9000,10000,11000,12000)
WATCHDOG_WCHAN=('zero_running_unavailable_or_hidden','qcom_wdt_kthread','smp_call_function_single',
    'csd_lock_wait','wait_for_completion','schedule_timeout','other')


def stages():
    text=STAGES.read_text()
    rows=re.findall(r'^AT_STAGE\((\d+), ([A-Z_]+), (\d+), ([123])\)$',text,re.M)
    result={int(number):(name,int(mask),int(convention)) for number,name,mask,convention in rows}
    require(len(result)==len(rows) and rows,'transition stage declaration differs')
    return result


def sources(selected):
    result={actor:selected[name]['sha256'] for actor,name in
        ((1,'writer'),(2,'entry'),(3,'witness'),(4,'hook'),(5,'writer'))}
    schema=selected.get('transition_observer',{}).get('schema')
    if schema in ('s22plus-autoboot-rcs-v1','s22plus-autoboot-watchdog-v1','s22plus-autoboot-phase-v1','s22plus-autoboot-singlecpu-v1','s22plus-autoboot-script-channel-v1','s22plus-autoboot-minimal-v1','s22plus-autoboot-reboot-v1'):
        result.update({6:selected['hook']['sha256'],7:selected['hook']['sha256']})
    if schema in ('s22plus-autoboot-watchdog-v1','s22plus-autoboot-phase-v1','s22plus-autoboot-singlecpu-v1','s22plus-autoboot-script-channel-v1','s22plus-autoboot-minimal-v1','s22plus-autoboot-reboot-v1'):result[8]=selected['hook']['sha256']
    return result


def phase_sample(stage,kind,value,error,a,b,c,d,ms,*,window_ms=15000,scripts=None):
    """Interpret source-bound positive observations without locating a stall."""
    import s22plus_debian_autoboot_phase_v1 as phase_spec
    scripts=phase_spec.SCRIPTS if scripts is None else scripts
    cap=2+2*len(scripts)
    if kind!=4:return None
    if stage==84:
        if value not in (1,2) or any((a,b,c,d)):return None
        return dict(type='handover',action='save' if value==1 else 'resume',error=error)
    if stage==85:
        if value or any((a,b,c,d)):return None
        return dict(type='child_channel',error=error)
    if stage==86:
        event=b&255;cpu=b>>8
        if error or not 1<=event<=12 or cpu>=8 or not 0<=value<window_ms*1000-1 or value>(ms+1)*1000 or not 0<=a<=2**31-1:return None
        declaration=phase_spec.PROBES[event-1];fields=declaration[4]
        if (not 0<=c<8 if 'cpu=' in fields else c!=2**32-1):return None
        if 'rc=' not in fields and d:return None
        return dict(type='kernel',event_id=event,event=declaration[1],trace_cpu=cpu,pid=a,
            kernel_boottime_us=value,target_cpu=c if 'cpu=' in fields else None,
            returned_register=d-2**32 if d>=2**31 else d if 'rc=' in fields else None,
            timestamp_precision='rounded_microsecond')
    if stage==87:
        if error or not 1<=a<=cap or not 0<=b<=len(scripts) or c not in map(ord,'DBEX') or d or not 0<=value<=255 or ms>=window_ms:return None
        action=chr(c)
        if action in 'DX' and (b or value) or action in 'BE' and not b or action=='B' and value:return None
        return dict(type='script',packet_sequence=a,action=action,script_id=b,
            script=scripts[b-1] if b else None,status=value)
    if stage==88:
        if not 0<=value<=2**32-1 or a&~4095 or b>65536 or c>28:return None
        if not error and (a!=4095 or value<b or c>b):return None
        return dict(type='profile',error=error,event_mask=a,decoded=b,retained=c,hits=value,missed=d)
    if stage==89:
        if not 0<=value<=2**32-1 or a&~255 or d>>8>34 or not error and a!=255:return None
        return dict(type='ring',error=error,cpu_mask=a,overruns=value,commit_overruns=b,dropped=c,flags=d&255,
            packets=d>>8)
    return None



def script_sample(stage,kind,value,error,a,b,c,d,ms,*,minimal=False):
    from s22plus_debian_autoboot_profile_v1 import script_spec
    from s22plus_debian_autoboot_phase_v1 import SCRIPT_DUE
    scripts=script_spec(minimal).SCRIPTS;cap=2+2*len(scripts)
    if kind!=4:return None
    if stage==91:
        if not 0<=value<=ms or a!=min(value+120000,300000) or any((b,c,d)):return None
        return dict(type='setup',started_ms=value,window_end_ms=a,error=error)
    if stage==92:
        if value or any((a,b,c,d)):return None
        return dict(type='child_channel',error=error)
    if stage==93:
        return phase_sample(87,kind,value,error,a,b,c,d,ms,window_ms=300000,scripts=scripts)
    if stage==94:
        if error or not 1<=a<=8 or not SCRIPT_DUE[a-1]<=value<120000 or value>ms or b>len(scripts) or c>1 or d>cap:return None
        if c and not b:return None
        return dict(type='parent',ordinal=a,elapsed_ms=value,script_id=b,script_open=bool(c),packets=d)
    if stage==95:
        if error or not 0<=value<=300000 or a>cap or b&~120 or c>1 or d>8:return None
        return dict(type='summary',used_ms=value,packets=a,flags=b,dispatcher_end=bool(c),parent_records=d)
    return None


def script_projection(records,*,minimal=False):
    from s22plus_debian_autoboot_profile_v1 import script_spec
    count=len(script_spec(minimal).SCRIPTS);cap=2+2*count
    rows=sorted((r for r in records if 'script_channel' in r),key=lambda r:(r['actor_id'],r['sequence']))
    packets=[r for r in rows if r['script_channel']['type']=='script']
    setups=[r for r in rows if r['script_channel']['type']=='setup']
    summaries=[r for r in rows if r['script_channel']['type']=='summary']
    parents=[r for r in rows if r['script_channel']['type']=='parent']
    issues=[];gap=False;previous=0;opened=0;identifier=0;ended=False
    if len(setups)>1 or len(summaries)>1 or len(parents)>8 or len(packets)>cap:issues.append('script_record_cap')
    for row in packets:
        p=row['script_channel'];seq=p['packet_sequence'];action=p['action'];current=p['script_id']
        if seq<=previous or ended:issues.append('script_packet_order')
        if seq!=previous+1:gap=True
        if action=='D':
            if seq!=1:issues.append('script_dispatcher_order')
        elif action=='B':
            if seq==previous+1 and opened or current<=identifier:issues.append('script_pair_order')
            opened=current;identifier=current
        elif action=='E':
            if seq==previous+1 and opened!=current:issues.append('script_pair_order')
            opened=0;identifier=current
        else:
            if seq==previous+1 and opened:issues.append('script_pair_order')
            ended=True
        previous=seq
    if setups:
        setup=setups[0];start=setup['script_channel']['started_ms'];end=setup['script_channel']['window_end_ms']
        for row in packets+parents:
            if row['sequence']<=setup['sequence'] or not start<=row['boottime_ms']<end:issues.append('script_window')
            if row['script_channel']['type']=='parent' and row['script_channel']['elapsed_ms']>row['boottime_ms']-start:
                issues.append('script_parent_clock')
        if setup['error'] and packets:issues.append('script_failed_setup_packets')
    for previous_parent,current_parent in zip(parents,parents[1:]):
        if current_parent['script_channel']['ordinal']<=previous_parent['script_channel']['ordinal']:
            issues.append('script_parent_order')
    if summaries:
        summary=summaries[0];stats=summary['script_channel']
        if any(r['sequence']>=summary['sequence'] for r in packets+parents):issues.append('script_after_summary')
        if stats['packets']<len(packets) or stats['parent_records']<len(parents):issues.append('script_summary_deficit')
        if ended and not stats['dispatcher_end']:issues.append('script_summary_end')
    exact=[('D',0,0)]+[(action,i,0) for i in range(1,count+1) for action in ('B','E')]+[('X',0,0)]
    # E may carry a nonzero service status; dispatcher completion is separate.
    ordered=[(r['script_channel']['action'],r['script_channel']['script_id'],
        0 if r['script_channel']['action']=='E' else r['script_channel']['status']) for r in packets]
    complete=bool(not issues and not gap and len(setups)==len(summaries)==1 and
        setups[0]['error']==0 and summaries[0]['script_channel']['flags']==0 and
        summaries[0]['script_channel']['packets']==cap and summaries[0]['script_channel']['dispatcher_end'] and
        ordered==exact and not any(r['prior_log_losses'] or r['prior_log_error'] for r in rows))
    return dict(records=rows,packets=packets,conflicts=sorted(set(issues)),packet_gap_detected=gap,
        dispatcher_exec_observed=any(r['script_channel']['action']=='D' for r in packets),
        complete_channel_observed=complete,collection_time_is_execution_time=False,
        missing_packet_proves_stall=False,watchdog_pet_proved=False,hardware_renewal_proved=False)


def phase_projection(records):
    rows=[r for r in records if 'phase' in r];issues=[]
    kernel=[r for r in rows if r['phase']['type']=='kernel']
    packets=[r for r in rows if r['phase']['type']=='script']
    if len(kernel)>28 or len(packets)>34:issues.append('phase_record_cap')
    # Kernel CPUs can race; text time is not a global syscall order.
    seen=set();opened=None;previous=0;ended=False
    for row in sorted(packets,key=lambda r:r['sequence']):
        p=row['phase'];seq=p['packet_sequence'];action=p['action'];identifier=p['script_id']
        if seq in seen or seq<=previous or ended:issues.append('phase_packet_order')
        if previous and seq==previous+1:
            if action=='B' and opened is not None or action=='E' and opened not in (None,identifier):
                issues.append('phase_script_pair')
        if action=='D' and seq!=1:issues.append('phase_dispatcher_order')
        if action=='B':opened=identifier
        if action=='E':opened=None
        if action=='X':ended=True
        seen.add(seq);previous=seq
    profiles=[r['phase'] for r in rows if r['phase']['type']=='profile']
    rings=[r['phase'] for r in rows if r['phase']['type']=='ring']
    if len(profiles)>1 or len(rings)>1:issues.append('phase_duplicate_metadata')
    if profiles and profiles[0]['retained']<len(kernel):issues.append('phase_retained_count')
    cleanup=[r for r in records if r['stage_id']==90 and r['kind']=='RETURN']
    setups=[r for r in records if r['stage_id']==83 and r['kind']=='RETURN']
    handovers=[r for r in rows if r['phase']['type']=='handover']
    if len(handovers)>2 or any(sum(r['phase']['action']==action for r in handovers)>1 for action in ('save','resume')):
        issues.append('phase_handover_count')
    metadata=bool(len(profiles)==len(rings)==1 and not profiles[0]['error'] and not rings[0]['error'])
    retention_gap=bool(profiles and profiles[0]['retained']!=len(kernel))
    script_gap=bool(rings and (rings[0]['packets']!=len(packets) or
        {r['phase']['packet_sequence'] for r in packets}!=set(range(1,rings[0]['packets']+1))))
    script_tail=bool(packets and not any(r['phase']['action']=='X' for r in packets))
    no_detected_loss=bool(metadata and not profiles[0]['missed'] and not rings[0]['overruns'] and
        not rings[0]['commit_overruns'] and not rings[0]['dropped'] and not rings[0]['flags']&127 and
        not retention_gap and not script_tail and not script_gap)
    return dict(observations=rows,conflicts=sorted(set(issues)),
        setup_confirmed=any(r['result']==0 for r in setups),
        cleanup_confirmed=bool(cleanup and all(r['result']==0 for r in cleanup)),
        metadata_complete=metadata,no_detected_loss=no_detected_loss,
        retained_kernel_count_gap=retention_gap,retained_script_count_gap=script_gap,script_terminal_unobserved=script_tail,
        dispatcher_exec_observed=any(r['phase']['action']=='D' for r in packets),
        window_complete=False,absence_proves_stall=False,watchdog_pet_proved=False,watchdog_cause_proved=False)


def watchdog_sample(stage,kind,value,error,child,status,properties,sample,ms):
    """Decode a separate observation payload, never a child/wait result."""
    slot=sample&7;acquired=sample>>3
    if kind!=4 or slot>=len(WATCHDOG_DUE) or not WATCHDOG_DUE[slot]<=acquired<12500 or acquired>ms:return None
    if error:
        if value or child or status or properties:return None
        return dict(slot=slot,acquired_boottime_ms=acquired,read_error=error,task=None)
    if acquired>=(WATCHDOG_DUE[slot]+250 if slot else 8500) or not 2<child<=2**31-1:return None
    result=dict(slot=slot,acquired_boottime_ms=acquired,read_error=0,
        task=dict(pid=child,starttime_ticks=status))
    if stage==79:
        state=chr(properties&255);cpu=(properties>>8)&255
        policy=(properties>>16)&255;priority=properties>>24
        if value<0 or state not in 'RSDTtXZPI' or cpu>=32 or policy>6 or priority>99:return None
        result.update(cpu_time_ticks=value,state=state,last_cpu=cpu,scheduling_policy=policy,rt_priority=priority)
    else:
        if properties or not 0<=value<len(WATCHDOG_WCHAN):return None
        result['wait_symbol_class']=WATCHDOG_WCHAN[value]
    return result


def watchdog_conflicts(rows):
    conflicts=[];pairs={};identities=set()
    for actor in (6,8):
        previous=None;failed=False;seen=set()
        for row in sorted((r for r in rows if r['actor_id']==actor),key=lambda r:r['sequence']):
            sample=row['watchdog'];slot=sample['slot'];index=(row['stage_id'],slot)
            order=(slot,row['stage_id'])
            if index in seen:conflicts.append('repeated_watchdog_slot')
            if failed or (previous and (order<=previous[0] or sample['acquired_boottime_ms']<previous[1])):
                conflicts.append('watchdog_sample_order')
            seen.add(index);previous=(order,sample['acquired_boottime_ms']);failed=bool(sample['read_error'])
            pairs.setdefault((actor,slot),[]).append(sample)
            if sample['task']:identities.add(tuple(sample['task'].values()))
    if len(identities)>1:conflicts.append('watchdog_task_identity')
    for samples in pairs.values():
        if len({r['acquired_boottime_ms'] for r in samples})>1:conflicts.append('watchdog_pair_time')
    ticks=sorted((r['watchdog']['acquired_boottime_ms'],r['watchdog']['cpu_time_ticks'])
        for r in rows if 'cpu_time_ticks' in r['watchdog'])
    if any(later[0]>earlier[0] and later[1]<earlier[1] for earlier,later in zip(ticks,ticks[1:])):
        conflicts.append('watchdog_cpu_time_reversal')
    return sorted(set(conflicts))


def rcs_conflicts(parents,children,extra_children=()):
    """Reject co-present impossibilities without requiring lost observations."""
    conflicts=[]
    def found(rows,stage,kind='RETURN'):
        return [r for r in rows if r['stage_id']==stage and r['kind']==kind]
    # The parent records the fork after the child may already have run. Only
    # each actor's own sequence orders its work; cross-actor clocks do not.
    ranks={60:0,61:1,62:2,63:3,64:4,75:6,76:7,77:8,78:9,
        66:11,67:12,68:12,69:13,70:14}
    for rows in (parents,children):
        previous=-1;stopped=False
        for row in sorted(rows,key=lambda r:r['sequence']):
            if row['kind']=='STOP':stopped=True;continue
            stage=row['stage_id']
            rank=(5 if row['kind']=='BEGIN' else 10) if stage==65 else ranks.get(stage,stage-71)
            if stopped or rank<previous:conflicts.append('rcs_stage_order')
            previous=rank
    # Optional child observations still join the actual fork and parent, but
    # do not acquire a position in the mandatory stage ranking above.
    children=[*children,*extra_children]
    forks=found(parents,64);waits=found(parents,66)
    reaped=found(parents,69,'POINT');complete=found(parents,70,'POINT')
    # BOOTTIME is shared by the authenticated boot. These causal bounds do
    # not order the child's work against the parent's delayed fork RETURN.
    fork_begin=found(parents,64,'BEGIN')
    if any(child['boottime_ms']<begin['boottime_ms'] for child in children for begin in fork_begin) or any(
        child['boottime_ms']>end['boottime_ms'] for child in children for end in reaped+complete):
        conflicts.append('rcs_child_causal_time')
    child_ids={r['pid'] for r in children}
    child_ids.update(r['result'] for r in forks+waits if r['result']>1)
    child_ids.update(r['child_pid'] for r in reaped)
    if len(child_ids)>1:conflicts.append('rcs_wait_join')
    if parents and any(r['ppid']!=parents[0]['pid'] for r in children):
        conflicts.append('rcs_parent_join')
    if any(r['result']==-1 for r in forks) and (children or any(
        r['kind']!='STOP' and r['stage_id'] not in (60,61,62,63,64) for r in parents)):
        conflicts.append('rcs_failed_fork_progress')
    for stage in (61,62,63):
        if any(r['result']!=0 for r in found(parents,stage)) and (children or any(
            r['kind']!='STOP' and r['stage_id']>stage for r in parents)):
            conflicts.append('rcs_failed_admission_progress')
    # A failed record still owns its close. It cannot subsequently verify the
    # failed write/sync or complete the enclosing record and enter the wait.
    for stage,success in ((75,128),(76,0),(77,0),(78,0),(65,0)):
        if any(r['result']!=success for r in found(parents,stage)):
            forbidden=({76,77} if stage==75 else {77} if stage==76 else set())|{66,67,68,69,70}
            if any(r['kind']!='STOP' and (r['stage_id'] in forbidden or
                (r['stage_id']==65 and r['kind']=='RETURN' and r['result']==0)) for r in parents):
                conflicts.append('rcs_failed_record_progress')
    for stage in (66,67):
        for failed in found(parents,stage):
            fatal=failed['result']==-1 and failed['errno_snapshot']!=4
            if fatal and any(r['kind']!='STOP' and r['sequence']>failed['sequence'] for r in parents):
                conflicts.append('rcs_failed_wait_progress')
    if any(r['result']>1 for r in waits) and any(
        r['stage_id'] in (67,68) and r['kind']!='STOP' for r in parents):
        conflicts.append('rcs_reaped_wait_progress')
    if any(r['result']!=0 for r in found(parents,68)) and (reaped or complete):
        conflicts.append('rcs_failed_heartbeat_progress')
    child_failures=[]
    for stage in (72,73,74):
        for row in found(children,stage):
            failed=(row['result']!=0 if stage==72 else
                (row['result']!=-1 or row['errno_snapshot']!=9) if stage==73 else True)
            if failed:
                child_failures.append(row)
                if any(r['kind']!='STOP' and r['sequence']>row['sequence'] for r in children):
                    conflicts.append('rcs_failed_child_progress')
    if child_failures and (complete or any(r['wait_status']==0 for r in reaped)):
        conflicts.append('rcs_failed_child_success')
    if complete and any(r['wait_status']!=0 for r in reaped):
        conflicts.append('rcs_failed_reap_completion')
    return conflicts


def retained(data,*,key,run,expected,boot=None,phase=False,phase_window_ms=15000,script_channel=False,minimal=False):
    require(isinstance(data,bytes) and len(data)<=MAXIMUM and len(key)==32 and len(run)==16 and
        set(expected) in (set(ACTORS),set(RCS_ACTORS),set(WATCHDOG_ACTORS)),'transition input scope differs')
    watchdog=set(expected)==set(WATCHDOG_ACTORS)
    require(not phase or watchdog,'phase selection requires eight measured actors')
    require(not minimal or script_channel,'minimal workload requires selected channel semantics')
    require(not script_channel or watchdog and not phase,'script channel requires its distinct eight-actor selection')
    require(phase_window_ms in (15000,65000) and (phase or phase_window_ms==15000),
        'unselected phase timing window')
    rcs=watchdog or set(expected)==set(RCS_ACTORS)
    actors=WATCHDOG_ACTORS if watchdog else RCS_ACTORS if rcs else ACTORS
    if rcs:require(expected[4]==expected[6]==expected[7],'rcS fork executable identity differs')
    if watchdog:require(expected[8]==expected[4],'watchdog owner executable identity differs')
    declared=stages();records=[];rejected={};conflicts=[];seen={};identities={}
    def reject(reason):rejected[reason]=rejected.get(reason,0)+1
    for candidate in re.finditer(rb'S22AT1[^\r\n]*',data):
        line=candidate.group();match=LINE.fullmatch(line)
        if match is None:reject('malformed');continue
        run_hex,boot_text,tag_hex,body_hex=match.groups()
        if bytes.fromhex(run_hex.decode())!=run:reject('other_run');continue
        body=bytes.fromhex(body_hex.decode());boot_hash=hashlib.sha256(boot_text).digest()
        tag=hmac.digest(key,DOMAIN+run+boot_hash+body,'sha256')
        if not hmac.compare_digest(tag,bytes.fromhex(tag_hex.decode())):reject('authentication');continue
        actor,seq,kind,stage,convention,error=struct.unpack_from('<6I',body,8)
        value,ms,pid,ppid,lost,log_error,spent,child,status,done,worker_result=struct.unpack_from('<qQIIIIQIIII',body,32)
        digest=body[88:120].hex()
        if actor not in actors or digest!=expected.get(actor):reject('producer');continue
        if boot is not None and boot_hash.hex()!=boot:reject('other_boot');continue
        if (body[:8]!=b'S22AT01\0' or any(body[120:]) or not 1<=seq<=96 or
            kind not in (1,2,3,4) or error>4095 or log_error>4095 or lost>=seq or spent>=2000 or
            ms>=300000 or pid<1 or (actor in (2,3) and pid!=1) or
            (actor in (1,4,5) and pid<=1) or (actor==5 and ppid!=1) or
            (actor==4 and ppid<1) or
            (actor==1 and ppid<=1) or (actor==6 and (pid<=1 or ppid<1)) or
            (actor==7 and (pid<=1 or ppid<=1)) or (actor==8 and (pid<=1 or ppid<1))):
            reject('shape');continue
        if stage in WATCHDOG_STAGES and not watchdog:reject('unselected_watchdog');continue
        if stage in PHASE_STAGES and not phase:
            reject('unselected_phase')
            if script_channel:conflicts.append('unselected_phase')
            continue
        if stage in SCRIPT_STAGES and not script_channel:reject('unselected_script_channel');continue
        if (phase or script_channel) and stage in (79,80):
            reject('unselected_proc_watchdog')
            if script_channel:conflicts.append('unselected_proc_watchdog')
            continue
        if kind==3:
            valid=convention==3 and value==0 and error>0 and (stage==0 or stage in declared)
        else:
            valid=stage in declared and bool(declared[stage][1]&(1<<(actor-1))) and convention==declared[stage][2]
            valid=valid and ((kind in (1,2) and convention in (1,2)) or (kind==4 and convention==3))
            if kind==1:valid=valid and value==error==0
            if kind==2 and convention==2:valid=valid and 0<=value<=4095 and error==value
            if kind==2 and convention==1:
                if stage==64:valid=valid and (value==-1 or 1<value<=2**31-1)
                elif stage==66:valid=valid and (value in (-1,0) or 1<value<=2**31-1)
                elif stage==73:valid=valid and -1<=value<=2**31-1
                elif stage==75:valid=valid and -1<=value<=128
                else:valid=valid and value in (0,-1) and (stage not in (50,55,74) or value==-1)
        observation=None
        phase_observation=None
        script_observation=None
        if stage in SCRIPT_STAGES:
            script_observation=script_sample(stage,kind,value,error,child,status,done,worker_result,ms,minimal=minimal)
            valid=valid and script_observation is not None
        elif stage in PHASE_STAGES-{83,90}:
            phase_observation=phase_sample(stage,kind,value,error,child,status,done,worker_result,ms,
                window_ms=phase_window_ms)
            valid=valid and phase_observation is not None
        elif stage in (79,80):
            observation=watchdog_sample(stage,kind,value,error,child,status,done,worker_result,ms)
            valid=valid and observation is not None
        elif actor==5:
            valid=valid and child>1 and done in (0,1) and status<=65535
            if stage==17 and value==0:valid=valid and error==status==worker_result==0 and done==1
        elif actor==6 and stage==69 and kind==4:
            valid=valid and value==error==worker_result==0 and child>1 and status<=65535 and done==1
        else:valid=valid and child==status==done==worker_result==0
        if kind==4 and stage in (60,70,71,81):valid=valid and value==error==0
        if not valid:reject('semantics');continue
        identity=(boot_hash.hex(),pid,ppid,digest)
        if actor in identities and identities[actor]!=identity:conflicts.append('actor_identity')
        identities[actor]=identity
        record=dict(actor=actors[actor],actor_id=actor,sequence=seq,kind={1:'BEGIN',2:'RETURN',3:'STOP',4:'POINT'}[kind],
            stage=declared[stage][0] if stage else 'UNOBSERVED',stage_id=stage,
            convention={1:'syscall',2:'checked_result',3:'observation'}[convention],result=value,
            errno_snapshot=error if convention==1 else None,error=error if convention!=1 else None,
            boottime_ms=ms,pid=pid,ppid=ppid,source_sha256=digest,boot_sha256=boot_hash.hex(),
            prior_log_losses=lost,prior_log_error=log_error,prior_log_elapsed_ms=spent,
            child_pid=child,wait_status=status,worker_done=done,worker_result=worker_result)
        if observation is not None:
            for name in ('child_pid','wait_status','worker_done','worker_result'):record.pop(name)
            record['watchdog']=observation
        if phase_observation is not None:
            for name in ('child_pid','wait_status','worker_done','worker_result'):record.pop(name)
            record['phase']=phase_observation
        if script_observation is not None:
            for name in ('child_pid','wait_status','worker_done','worker_result'):record.pop(name)
            record['script_channel']=script_observation
        index=(actor,seq)
        if index in seen:
            conflicts.append('duplicate_sequence' if seen[index]==body else 'contradictory_sequence');continue
        seen[index]=body;records.append(record)
        require(len(records)<=len(actors)*96,'transition authenticated record budget exceeded')
    boots={record['boot_sha256'] for record in records}
    if len(boots)>1:conflicts.append('kernel_boot')
    unpaired_begin=[];isolated_return=[]
    for actor in actors:
        rows=sorted((r for r in records if r['actor_id']==actor),key=lambda r:r['sequence'])
        previous=None;pending={};begun=set();completed=set()
        for row in rows:
            if previous and (row['boottime_ms']<previous['boottime_ms'] or
                row['prior_log_losses']<previous['prior_log_losses'] or
                row['prior_log_elapsed_ms']<previous['prior_log_elapsed_ms']):conflicts.append('actor_order')
            previous=row;stage=row['stage_id']
            if row['kind']=='BEGIN':
                if stage in begun or stage in completed:conflicts.append('repeated_stage_begin')
                begun.add(stage)
                pending[stage]=row
            elif row['kind']=='RETURN':
                if stage in completed:conflicts.append('repeated_stage_return')
                completed.add(stage)
                if stage in pending:pending.pop(stage)
                else:isolated_return.append(row)
            elif row['kind']=='POINT':
                if 'watchdog' not in row and 'phase' not in row and 'script_channel' not in row:
                    if stage in completed:conflicts.append('repeated_stage_point')
                    completed.add(stage)
        unpaired_begin.extend(pending.values())
    workers=[r for r in records if r['actor_id']==1]
    for row in (r for r in records if r['actor_id']==5):
        if workers and any(r['pid']!=row['child_pid'] or r['ppid']!=row['pid'] for r in workers):
            conflicts.append('supervisor_child_join')
    parents=[r for r in records if r['actor_id']==6 and 'watchdog' not in r and r['stage_id'] not in PHASE_STAGES|SCRIPT_STAGES]
    children=[r for r in records if r['actor_id']==7 and r['stage_id'] not in PHASE_STAGES|SCRIPT_STAGES]
    forks=[r['result'] for r in parents if r['stage_id']==64 and r['kind']=='RETURN' and r['result']>1]
    if rcs:conflicts.extend(rcs_conflicts(parents,children,
        [r for r in records if script_channel and r['actor_id']==7 and r['stage_id']==92]))
    valid=not conflicts
    installed=valid and any(r['actor_id']==4 and r['stage_id']==58 and r['kind']=='RETURN' and r['result']==0 for r in records)
    observed=[r for r in records if r['kind'] in ('RETURN','POINT') and r['stage_id'] not in WATCHDOG_STAGES|PHASE_STAGES|SCRIPT_STAGES]
    highest=max(observed,key=lambda r:(r['boottime_ms'],r['actor_id'],r['sequence']) if rcs else r['stage_id'])['stage'] if observed and valid else None
    complete=valid and any(r['stage_id']==70 and r['kind']=='POINT' for r in parents)
    if complete:highest='RCS_COMPLETE'
    result=dict(schema='s22plus-autoboot-transition-projection-v1',
        status='AUTHENTICATED_TRANSITION_FACTS' if records and valid else 'CONFLICTING_TRANSITION_FACTS' if conflicts else 'NO_AUTHENTICATED_TRANSITION_FACTS',
        records=records,rejected=rejected,conflicts=sorted(set(conflicts)),progress_claim_valid=valid,
        highest_authenticated_stage=highest,installed_debian_pid1=installed,
        begin_without_return=unpaired_begin,return_without_begin=isolated_return,
        boot_sha256=next(iter(boots)) if len(boots)==1 else None,retained_any_stage=bool(records),
        logging_complete=False,absence_proves_nonexecution=False,stopped_at_last_record=False,
        pending_call_proves_stall=False,ssh_access_proved=False,clean_shutdown_proved=False,replay_authorized=False)
    if rcs:
        result.update(rcs_child_fork_proved=valid and bool(forks),rcs_completed=complete,
            rcs_child_exec_proved=complete,
            rcs_fork_record_completed=valid and any(r['stage_id']==65 and r['kind']=='RETURN' and r['result']==0 for r in parents))
    if watchdog and not phase and not script_channel:
        samples=[r for r in records if 'watchdog' in r];issues=watchdog_conflicts(samples)
        result.update(watchdog_observations=samples,watchdog_conflicts=issues,
            watchdog_observations_consistent=valid and not issues,watchdog_phase_proved=False,
            watchdog_pet_proved=False,watchdog_cause_proved=False,watchdog_samples_atomic=False)
    if phase:
        result['phase']=phase_projection(records)
        result['phase']['consistent']=valid and not result['phase']['conflicts']
        result['phase']['dispatcher_exec_proved']=bool(valid and forks and
            result['phase']['consistent'] and result['phase']['dispatcher_exec_observed'] and
            any(r['stage_id']==85 and r['error']==0 for r in records))
    if script_channel:
        result['script_channel']=script_projection(records,minimal=minimal)
        facts=result['script_channel'];facts['consistent']=valid and not facts['conflicts']
        facts['dispatcher_exec_proved']=bool(facts['consistent'] and forks and
            facts['dispatcher_exec_observed'] and any(r['stage_id']==92 and r['error']==0 for r in records))
        facts['complete_channel_proved']=bool(facts['consistent'] and facts['complete_channel_observed'] and
            facts['dispatcher_exec_proved'])
    return result


def qualify_case(proof,case):
    """Assertions over independently authenticated actual VM output."""
    require(not proof['conflicts'] and all(proof[name] is False for name in
        ('logging_complete','absence_proves_nonexecution','stopped_at_last_record',
         'pending_call_proves_stall','ssh_access_proved','clean_shutdown_proved','replay_authorized')),
        'transition facts were promoted beyond their observation')
    rows=proof['records']
    def found(stage,kind,result=None):
        return [r for r in rows if r['stage']==stage and r['kind']==kind and
            (result is None or r['result']==result)]
    rcs='rcs_completed' in proof
    watchdog='watchdog_observations' in proof
    phase='phase' in proof
    script_channel='script_channel' in proof
    if case=='trace-logger-loss':
        require(not rows and not proof['installed_debian_pid1'],'lost logger invented retained evidence')
    elif case in ('normal','network-absent','script-channel-setup','script-channel-gap'):
        require(proof['installed_debian_pid1'] and
            {r['actor_id'] for r in rows}==set(WATCHDOG_ACTORS if watchdog or phase or script_channel else RCS_ACTORS if rcs else ACTORS),
            'successful VM lacks all measured transition actors')
        for stage in ('FILE_CLOSE','PARENT_CLOSE','ROOT_CLOSE','FILE_UNMOUNT','RESTORE_RO',
            'SUPER_CLEAN','GPT_CHECK','RECEIPT','WAIT_RESULT','ROOT_ELIGIBLE','WRITABLE_MOUNT',
            'MOVE_DEV','MOVE_PROC','WORK_UNMOUNT','WITNESS_CHECK','ACTUAL_INIT_CHECK','RUNTIME_FILE_BEGIN'):
            require(found(stage,'POINT' if stage=='WAIT_RESULT' else 'RETURN',0),
                'successful VM lacks actual transition return: '+stage)
        require(found('SWITCH_ROOT_EXEC','BEGIN') and found('INSTALLED_INIT_EXEC','BEGIN') and
            not found('SWITCH_ROOT_EXEC','RETURN') and not found('INSTALLED_INIT_EXEC','RETURN'),
            'successful exec claims a returning syscall')
        if rcs:
            require(proof['rcs_completed'] and proof['rcs_child_fork_proved'] and proof['rcs_fork_record_completed'] and
                found('RCS_RECORD_WRITE','RETURN',128) and found('RCS_RECORD_FSYNC','RETURN',0) and
                found('RCS_RECORD_VERIFY','RETURN',0) and found('RCS_RECORD_CLOSE','RETURN',0) and
                found('RCS_CHILD_CLOSE_FDS','RETURN',0) and
                (bool(found('SCRIPT_CHILD_CHANNEL','POINT',0)) if script_channel and case!='script-channel-setup' else
                 bool(found('PHASE_CHILD_CHANNEL','POINT',0)) if phase else
                 any(r['errno_snapshot']==9 for r in found('RCS_CHILD_FD_PROBE','RETURN',-1))) and
                found('RCS_CHILD_EXEC','BEGIN') and not found('RCS_CHILD_EXEC','RETURN') and
                any(r['wait_status']==0 for r in found('RCS_CHILD_REAPED','POINT')),
                'successful rcS VM lacks its actual parent/child/record completion')
        if script_channel:
            facts=proof['script_channel']
            if case in ('script-channel-setup','script-channel-gap'):
                require(not facts['complete_channel_proved'] and facts['consistent'],
                    'optional failure was promoted to complete channel')
                if case=='script-channel-setup':
                    require(any(r['error']==28 for r in found('SCRIPT_SETUP','POINT')) and
                        not facts['packets'],'setup failure did not exercise fallback')
                else:
                    require(facts['dispatcher_exec_proved'] and
                        any(r['script_channel']['flags']&64 for r in facts['records']
                            if r['script_channel']['type']=='summary'),
                        'packet loss did not close the optional channel')
            else:require(facts['complete_channel_proved'],
                'successful script VM lacks its complete authenticated dispatcher channel')
        if phase:
            require(proof['phase']['dispatcher_exec_proved'] and not proof['phase']['conflicts'],
                'successful phase VM lacks authenticated RAM dispatcher execution')
    elif case.startswith('minimal-'):
        require(rcs and script_channel and proof['installed_debian_pid1'] and
            not proof['rcs_completed'] and not proof['script_channel']['complete_channel_proved'],
            'minimal required-input failure advanced to completion')
        require(proof['rcs_child_fork_proved']==(case in ('minimal-missing-dependency','minimal-script-error')),
            'minimal required program was not checked before child fork')
        if case in ('minimal-missing-dependency','minimal-script-error'):
            wanted=21 if case=='minimal-missing-dependency' else 37
            require(any(r['wait_status']==wanted<<8 for r in found('RCS_CHILD_REAPED','POINT')),
                'minimal dispatcher failed to preserve required failure status')
    elif case.startswith('rcs-'):
        require(rcs and proof['installed_debian_pid1'] and proof['rcs_child_fork_proved'] and
            not proof['rcs_completed'] and not proof['rcs_child_exec_proved'],'rcS negative promoted to completion')
        if case=='rcs-pending-record':
            require(found('RCS_RECORD_FSYNC','BEGIN') and not found('RCS_RECORD_FSYNC','RETURN') and
                not proof['rcs_fork_record_completed'] and not found('RCS_WAIT_FIRST','BEGIN'),
                'pending record produced a fabricated completion')
        elif case=='rcs-pending-child':
            require(proof['rcs_fork_record_completed'] and found('RCS_WAIT_FIRST','RETURN',0) and
                found('RCS_SLEEP_FIRST','RETURN',0) and found('RCS_HEARTBEAT','RETURN',0) and
                not found('RCS_CHILD_EXEC','BEGIN') and not found('RCS_CHILD_REAPED','POINT'),
                'pending child lost wait progress or fabricated completion')
        else:
            stage,number={'rcs-record-fsync':('RCS_RECORD_FSYNC',9),
                'rcs-close-range':('RCS_CHILD_CLOSE_FDS',22),'rcs-exec':('RCS_CHILD_EXEC',2),
                'rcs-wait':('RCS_WAIT_FIRST',22),'rcs-sleep':('RCS_SLEEP_FIRST',22)}[case]
            require(any(r['errno_snapshot']==number for r in found(stage,'RETURN',-1)),
                'rcS failure lacks its actual syscall errno')
            if case in ('rcs-close-range','rcs-exec'):
                expected_status=(125 if case=='rcs-close-range' else 126)<<8
                require(any(r['wait_status']==expected_status for r in found('RCS_CHILD_REAPED','POINT')),
                    'rcS child failure lacks its actual reaped status')
    elif case=='trace-pending':
        require(found('FILE_CLOSE','BEGIN') and not found('FILE_CLOSE','RETURN') and
            not proof['installed_debian_pid1'],'pending VM fabricated a return')
    elif case.startswith('trace-'):
        stage={'trace-file-close':'FILE_CLOSE','trace-parent-close':'PARENT_CLOSE','trace-root-close':'ROOT_CLOSE',
            'trace-unmount':'FILE_UNMOUNT','trace-ro':'RESTORE_RO','trace-post-super':'SUPER_READ',
            'trace-receipt':'RECEIPT','trace-second-admission':'SECOND_ADMISSION',
            'trace-root-activate':'WRITABLE_MOUNT','trace-move-dev':'MOVE_DEV','trace-switch-exec':'SWITCH_ROOT_EXEC',
            'trace-witness':'WITNESS_CHECK','trace-init-exec':'INSTALLED_INIT_EXEC',
            'trace-init-identity':'ACTUAL_INIT_CHECK'}[case]
        failed=[r for r in found(stage,'RETURN') if r['result']!=0]
        require(failed and not proof['installed_debian_pid1'],'injected failure lacks its real negative return')
        require(all(r['errno_snapshot']>0 if r['convention']=='syscall' else r['error']>0 for r in failed),
            'failure lost its immediate errno/result')
        if failed[0]['actor_id']==1:
            original=failed[0]['errno_snapshot'] if failed[0]['convention']=='syscall' else failed[0]['error']
            require(any(r['error']==original for r in found('FILE_RESULT','POINT')) and
                found('WAIT_RESULT','POINT',1),'worker error or supervisor settlement differs')
    else:require(not proof['installed_debian_pid1'],'negative VM reached installed init')
    return True
