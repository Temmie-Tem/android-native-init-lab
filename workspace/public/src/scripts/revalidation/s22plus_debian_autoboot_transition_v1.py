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


def stages():
    text=STAGES.read_text()
    rows=re.findall(r'^AT_STAGE\((\d+), ([A-Z_]+), (\d+), ([123])\)$',text,re.M)
    result={int(number):(name,int(mask),int(convention)) for number,name,mask,convention in rows}
    require(len(result)==len(rows) and rows,'transition stage declaration differs')
    return result


def sources(selected):
    return {actor:selected[name]['sha256'] for actor,name in
        ((1,'writer'),(2,'entry'),(3,'witness'),(4,'hook'),(5,'writer'))}


def retained(data,*,key,run,expected,boot=None):
    require(isinstance(data,bytes) and len(data)<=MAXIMUM and len(key)==32 and len(run)==16 and
        set(expected)==set(ACTORS),'transition input scope differs')
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
        if actor not in ACTORS or digest!=expected.get(actor):reject('producer');continue
        if boot is not None and boot_hash.hex()!=boot:reject('other_boot');continue
        if (body[:8]!=b'S22AT01\0' or any(body[120:]) or not 1<=seq<=96 or
            kind not in (1,2,3,4) or error>4095 or log_error>4095 or lost>=seq or spent>=2000 or
            ms>=300000 or pid<1 or (actor in (2,3) and pid!=1) or
            (actor in (1,4,5) and pid<=1) or (actor==5 and ppid!=1) or
            (actor==4 and ppid<1) or
            (actor==1 and ppid<=1)):
            reject('shape');continue
        if kind==3:
            valid=convention==3 and value==0 and error>0 and (stage==0 or stage in declared)
        else:
            valid=stage in declared and bool(declared[stage][1]&(1<<(actor-1))) and convention==declared[stage][2]
            valid=valid and ((kind in (1,2) and convention in (1,2)) or (kind==4 and convention==3))
            if kind==1:valid=valid and value==error==0
            if kind==2 and convention==2:valid=valid and 0<=value<=4095 and error==value
            if kind==2 and convention==1:
                valid=valid and value in (0,-1) and (stage not in (50,55) or value==-1)
        if actor==5:
            valid=valid and child>1 and done in (0,1) and status<=65535
            if stage==17 and value==0:valid=valid and error==status==worker_result==0 and done==1
        else:valid=valid and child==status==done==worker_result==0
        if not valid:reject('semantics');continue
        identity=(boot_hash.hex(),pid,ppid,digest)
        if actor in identities and identities[actor]!=identity:conflicts.append('actor_identity')
        identities[actor]=identity
        record=dict(actor=ACTORS[actor],actor_id=actor,sequence=seq,kind={1:'BEGIN',2:'RETURN',3:'STOP',4:'POINT'}[kind],
            stage=declared[stage][0] if stage else 'UNOBSERVED',stage_id=stage,
            convention={1:'syscall',2:'checked_result',3:'observation'}[convention],result=value,
            errno_snapshot=error if convention==1 else None,error=error if convention!=1 else None,
            boottime_ms=ms,pid=pid,ppid=ppid,source_sha256=digest,boot_sha256=boot_hash.hex(),
            prior_log_losses=lost,prior_log_error=log_error,prior_log_elapsed_ms=spent,
            child_pid=child,wait_status=status,worker_done=done,worker_result=worker_result)
        index=(actor,seq)
        if index in seen:
            conflicts.append('duplicate_sequence' if seen[index]==body else 'contradictory_sequence');continue
        seen[index]=body;records.append(record)
        require(len(records)<=5*96,'transition authenticated record budget exceeded')
    boots={record['boot_sha256'] for record in records}
    if len(boots)>1:conflicts.append('kernel_boot')
    unpaired_begin=[];isolated_return=[]
    for actor in ACTORS:
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
                if stage in completed:conflicts.append('repeated_stage_point')
                completed.add(stage)
        unpaired_begin.extend(pending.values())
    workers=[r for r in records if r['actor_id']==1]
    for row in (r for r in records if r['actor_id']==5):
        if workers and any(r['pid']!=row['child_pid'] or r['ppid']!=row['pid'] for r in workers):
            conflicts.append('supervisor_child_join')
    valid=not conflicts
    installed=valid and any(r['actor_id']==4 and r['stage_id']==58 and r['kind']=='RETURN' and r['result']==0 for r in records)
    observed=[r for r in records if r['kind'] in ('RETURN','POINT')]
    highest=max(observed,key=lambda r:r['stage_id'])['stage'] if observed and valid else None
    return dict(schema='s22plus-autoboot-transition-projection-v1',
        status='AUTHENTICATED_TRANSITION_FACTS' if records and valid else 'CONFLICTING_TRANSITION_FACTS' if conflicts else 'NO_AUTHENTICATED_TRANSITION_FACTS',
        records=records,rejected=rejected,conflicts=sorted(set(conflicts)),progress_claim_valid=valid,
        highest_authenticated_stage=highest,installed_debian_pid1=installed,
        begin_without_return=unpaired_begin,return_without_begin=isolated_return,
        boot_sha256=next(iter(boots)) if len(boots)==1 else None,retained_any_stage=bool(records),
        logging_complete=False,absence_proves_nonexecution=False,stopped_at_last_record=False,
        pending_call_proves_stall=False,ssh_access_proved=False,clean_shutdown_proved=False,replay_authorized=False)


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
    if case=='trace-logger-loss':
        require(not rows and not proof['installed_debian_pid1'],'lost logger invented retained evidence')
    elif case in ('normal','network-absent'):
        require(proof['installed_debian_pid1'] and {r['actor_id'] for r in rows}==set(ACTORS),
            'successful VM lacks all measured transition actors')
        for stage in ('FILE_CLOSE','PARENT_CLOSE','ROOT_CLOSE','FILE_UNMOUNT','RESTORE_RO',
            'SUPER_CLEAN','GPT_CHECK','RECEIPT','WAIT_RESULT','ROOT_ELIGIBLE','WRITABLE_MOUNT',
            'MOVE_DEV','MOVE_PROC','WORK_UNMOUNT','WITNESS_CHECK','ACTUAL_INIT_CHECK','RUNTIME_FILE_BEGIN'):
            require(found(stage,'POINT' if stage=='WAIT_RESULT' else 'RETURN',0),
                'successful VM lacks actual transition return: '+stage)
        require(found('SWITCH_ROOT_EXEC','BEGIN') and found('INSTALLED_INIT_EXEC','BEGIN') and
            not found('SWITCH_ROOT_EXEC','RETURN') and not found('INSTALLED_INIT_EXEC','RETURN'),
            'successful exec claims a returning syscall')
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
