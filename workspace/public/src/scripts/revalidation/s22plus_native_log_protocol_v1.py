"""Exact native calibration frames and bounded live/retained interpretation."""
import base64
import hashlib
import hmac
import re
import struct
import uuid
from s22plus_native_records_v3 import require

DOMAIN=b'S22PLUS-FYG8-NATIVE-LOG-CAL-v1'
PREFIX=b'S22CAL1['
FRAME=153
MAXIMUM=4*1024**2
FIELDS=('stage','errno','attempted','returned','module_errno','bound','pre_written','pre_ring',
        'post_written','post_ring','backend_bytes','backend_eof','pre_count','post_count',
        'pre_offset','post_offset','cleanup_errno')


def encode(*,key,run,boot,sequence,pid,helper):
    require(sequence in (1,2) and len(key)==32 and len(run)==len(boot)==16 and len(helper)==32,'frame input differs')
    data=run+boot+struct.pack('<III',sequence,sequence,pid)+helper
    tag=hmac.new(key,DOMAIN+run+hashlib.sha256(boot).digest()+struct.pack('<IB',sequence,242)+data,hashlib.sha256).digest()
    return PREFIX+base64.b64encode(data+tag)+b']'


def decode_frame(raw,*,key,run,helper):
    require(type(raw) is bytes and len(raw)==FRAME and raw.startswith(PREFIX) and raw[-1:]==b']','frame envelope differs')
    data=base64.b64decode(raw[len(PREFIX):-1],validate=True)
    require(len(data)==108 and base64.b64encode(data)==raw[len(PREFIX):-1],'frame encoding differs')
    seq,kind,pid=struct.unpack('<III',data[32:44]);require(data[:16]==run and seq in (1,2) and kind==seq and pid>1 and data[44:76].hex()==helper,'frame identity differs')
    expected=encode(key=key,run=run,boot=data[16:32],sequence=seq,pid=pid,helper=data[44:76])
    require(hmac.compare_digest(expected,raw),'frame authentication differs')
    boot=str(uuid.UUID(bytes=data[16:32]))
    return dict(sequence=seq,name='PRE' if seq==1 else 'POST',pid=pid,boot_uuid=boot,
        helper_sha256=helper,frame_hex=raw.hex(),frame_sha256=hashlib.sha256(raw).hexdigest())


def _fields(line,prefix,names):
    require(line.startswith(prefix+' '),'record prefix differs')
    parts=line[len(prefix)+1:].split(' ');require(len(parts)==len(names),'record width differs')
    result={}
    for name,item in zip(names,parts):
        k,sep,value=item.partition('=');require(k==name and sep and value,'record field differs');result[name]=value
    return result


def decode(stdout,stderr,*,key,run,helper):
    require(not stderr and 0<len(stdout)<=8192 and stdout.endswith(b'\n'),'calibration output incomplete')
    lines=stdout.decode('ascii').splitlines();require(8<=len(lines)<=17,'calibration line count differs')
    head=_fields(lines[0],'LC1_BEGIN',('version','run','boot','pid','helper'))
    require(head['version']=='1' and head['run']==run.hex() and head['helper']==helper and
        re.fullmatch('[1-9][0-9]{0,9}',head['pid']) and int(head['pid'])>1 and str(uuid.UUID(head['boot']))==head['boot'],'live helper identity differs')
    fields=_fields(lines[-6],'LC1_RESULT',FIELDS)
    require(all(re.fullmatch('0|[1-9][0-9]{0,9}',x) for x in fields.values()),'result integer differs')
    result={k:int(v) for k,v in fields.items()}
    require(1<=result['stage']<=7 and all(result[k] in (0,1) for k in ('attempted','returned','bound','pre_written','pre_ring','post_written','post_ring','backend_eof')) and
        all(result[k]<=4095 for k in ('errno','module_errno','cleanup_errno')) and result['backend_bytes']<=MAXIMUM+1 and
        all(result[k]<=MAXIMUM for k in ('pre_count','post_count','pre_offset','post_offset')),'result bound differs')
    middle=lines[1:-6];steps=[int(x.removeprefix('LC1_STEP stage=')) for x in middle if re.fullmatch(r'LC1_STEP stage=[1-7]',x)]
    returns=[x for x in middle if x.startswith('LC1_RETURN ')]
    require(steps==list(range(1,result['stage']+1)) and len(middle)==len(steps)+len(returns) and
        len(returns)==result['returned'] and (not returns or returns==['LC1_RETURN errno='+str(result['module_errno'])]),'live stage sequence differs')
    if returns:require(middle.index(returns[0])==3,'module return appears outside its invocation stage')
    require(result['returned']==result['attempted'] and (not result['attempted'] or result['stage']>=3 and result['pre_ring']) and
        (not result['bound'] or result['returned'] and not result['module_errno'] and result['stage']>=4) and
        (not result['post_written'] or result['bound']) and (not result['backend_eof'] or result['stage']>=6 and result['post_ring']),
        'calibration causal fields contradict each other')
    frames={};backend={};zero=bytes(FRAME)
    for offset,name in enumerate(('PRE','POST','BACKEND_PRE','BACKEND_POST')):
        value=_fields(lines[-5+offset],'LC1_'+name,('frame',))['frame'];require(re.fullmatch('[0-9a-f]{306}',value),'raw frame encoding differs')
        raw=bytes.fromhex(value)
        if raw==zero:entry=None
        else:
            entry=decode_frame(raw,key=key,run=run,helper=helper)
            require(entry['sequence']==(1 if name.endswith('PRE') else 2) and entry['boot_uuid']==head['boot'] and entry['pid']==int(head['pid']),'live frame joins another helper or boot')
        (backend if name.startswith('BACKEND_') else frames)[name.removeprefix('BACKEND_')]=entry
    backend_sha=_fields(lines[-1],'LC1_BACKEND',('sha256',))['sha256'];require(re.fullmatch('[0-9a-f]{64}',backend_sha),'backend digest differs')
    for name in ('PRE','POST'):
        prefix=name.lower();require(not result[prefix+'_ring'] or result[prefix+'_written'] and frames[name] is not None,'ring success has no written frame')
        require(bool(result[prefix+'_count'])==(backend[name] is not None),'backend count has no raw frame')
        if backend[name]:require(backend[name]==frames[name] and result[prefix+'_offset']+FRAME<=result['backend_bytes'],'backend frame differs from live producer')
    if result['stage']>=3:require(result['pre_ring']==1,'later stage has no pre readback')
    if result['stage']>=5:require(result['bound']==1,'post stage has no binding')
    if result['stage']>=6:require(result['post_ring']==1,'backend stage has no post readback')
    positive=not result['errno'] and not result['cleanup_errno']
    if positive:require(result['stage']==7 and all(result[k]==1 for k in ('attempted','returned','bound','pre_written','pre_ring','post_written','post_ring','backend_eof','pre_count','post_count')) and
        not result['module_errno'] and result['pre_offset']+FRAME<=result['post_offset'],'positive calibration is incomplete')
    return dict(status='PASS_LOG_CALIBRATION_OBSERVED',scientific_status='LIVE_RETAINED_PAIR_PROVED' if positive else 'CALIBRATION_NEGATIVE',
        helper_entry_proved=True,helper_settled=True,live_pair_proved=positive,run_id_hex=run.hex(),boot_uuid=head['boot'],
        kernel_boot_identity_sha256=hashlib.sha256(hashlib.sha256(head['boot'].encode()).digest()).hexdigest(),
        helper_sha256=helper,measurements=result,frames=frames,backend_frames=backend,backend_sha256=backend_sha,
        post_return_retention_proved=False,debian_early_pid1=False,installed_debian_pid1=False,replay_authorized=False)


def retained(raw,*,key,run,helper,live):
    require(type(raw) is bytes and len(raw)<=MAXIMUM,'retained input exceeds bound')
    records=[];errors=[];foreign=0
    starts=[m.start() for m in re.finditer(re.escape(PREFIX),raw)];require(len(starts)<=512,'retained candidate count exceeds bound')
    for offset in starts:
        frame=raw[offset:offset+FRAME]
        try:
            # Foreign frames are not evidence for this run, even if well formed.
            data=base64.b64decode(frame[len(PREFIX):-1],validate=True) if len(frame)==FRAME and frame[-1:]==b']' else b''
            if len(data)==108 and data[:16]!=run:foreign+=1;continue
            value=decode_frame(frame,key=key,run=run,helper=helper)
            require(value['boot_uuid']==live['boot_uuid'] and value==live['frames'][value['name']],'retained frame has no same-boot live producer')
            records.append(dict(value,offset=offset))
        except (ValueError,UnicodeError) as error:
            errors.append(dict(offset=offset,raw_sha256=hashlib.sha256(frame).hexdigest(),reason=str(error)))
    seq=[x['sequence'] for x in records];require(seq==sorted(set(seq)),'duplicate/reversed retained calibration frames')
    complete=live['live_pair_proved'] and seq==[1,2] and not errors
    return dict(status='PASS_NATIVE_LOG_RETENTION' if complete else 'PARTIAL_NATIVE_LOG_RETENTION' if records else 'NO_AUTHENTICATED_CALIBRATION_RECORD',
        records=records,damaged_candidates=errors,foreign_frames=foreign,live_pair_proved=live['live_pair_proved'],
        post_return_retention_proved=complete,debian_early_pid1=False,installed_debian_pid1=False,
        absence_proves_nonexecution=False,stopped_at_last_record=False,replay_authorized=False)
