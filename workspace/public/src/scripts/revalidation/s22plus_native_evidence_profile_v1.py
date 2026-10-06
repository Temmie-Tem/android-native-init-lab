"""Fixed mountless native_data evidence reads; no live authority or replay."""
import hashlib
import re
import struct
from pathlib import Path
import s22plus_native_root_inspect_profile_v1 as inspection
import s22plus_root_console_v1 as wire
from s22plus_native_records_v3 import read,require,verify

ROOT=inspection.ROOT
SCHEMA='s22plus-native-root-evidence-v1'
PROFILE='thermal-v3-reconnect-ufs-drain-root-evidence-v1'
OPERATION=SELECTION='root-evidence'
MAXIMUM=65536
CHILD_MAXIMUM=24576
FILE_NOT_FOUND=2133571404
prior_inputs=inspection.prior_inputs
LIBRARIES=dict(path=str(ROOT/'workspace/private/outputs/s22plus-debian-durable-evidence-p415-h0-20261007-1/libraries/reader-libraries.json'),
    size=10637,sha256='6a06123794aeb759acd149e11a51ae9ab9792cfa3f88acd1ad783417a7e25ba4')
# path, exact mode/gid, maximum whole-file bytes, raw suffix bytes.
# Raw contents remain private. Rotated dmesg files are digest/metadata only.
FILES=(
    ('var/lib/lab/boot-count',0o100644,0,32,32),
    ('var/log/wtmp',0o100664,43,65536,1200),
    ('var/log/dmesg',0o100640,4,1048576,1024),
    ('var/log/messages',0o100644,0,133248,1024),
    *((f'var/log/messages.{i}',0o100644,0,133248,512) for i in range(3)),
    ('var/log/dmesg.0',0o100640,4,1048576,0),
    *((f'var/log/dmesg.{i}.gz',0o100640,4,1048576,0) for i in range(1,5)),
)


def paths(record_run=None):
    require(record_run is None or type(record_run) is str and re.fullmatch('[0-9a-f]{32}',record_run),
        'evidence run identity differs')
    return FILES+((('var/lib/lab/s22-evidence-'+record_run,0o100600,0,16384,16384),) if record_run else ())


def header(record_run=None):
    import json
    selected=paths(record_run)
    return ('struct ne_path { const char *path; unsigned mode,gid; uint64_t maximum; unsigned capture; };\n'
        f'#define NE_PATH_COUNT {len(selected)}U\nstatic const struct ne_path ne_paths[]={{\n'+
        ''.join('{'+json.dumps(name)+f',{mode}U,{gid}U,{maximum}ULL,{capture}U'+'},\n'
            for name,mode,gid,maximum,capture in selected)+'};\n').encode()


def library_inputs():
    value=read(verify(LIBRARIES))
    require(value['schema']=='s22plus-native-evidence-libraries-h0-v1' and
        value['upstream']['sha256']=='08242e64ca0e8194d9c1caad49762b19209a06318199b63ce74ae4ef2d74e63c',
        'evidence parser library provenance differs')
    verify(value['upstream'],maximum=16*1024*1024);verify(value['tools_result'])
    for row in value['libraries']+value['headers']:verify(row)
    return value


def image_binding(image):
    require(image['profile']==PROFILE,'unselected evidence reader image')
    root=inspection.image_binding(dict(image,profile=inspection.PROFILE))
    value=image['root_evidence'];record_run=value['record_run']
    require(set(value)=={'libraries','record_run','files','max_output','mount','journal_replay','filesystem_writes'} and
        value['libraries']==LIBRARIES and value['files']==[list(row) for row in paths(record_run)] and
        value['max_output']==MAXIMUM and value['mount'] is False and value['journal_replay'] is False and
        value['filesystem_writes'] is False,'evidence reader scope differs')
    library_inputs();return root


def decode_child(raw,record_run=None):
    require(64<=len(raw)<=CHILD_MAXIMUM and raw[:8]==b'S22NE01\0','evidence child header absent')
    selected=paths(record_run);count,state,recover,orphan=struct.unpack_from('<4I',raw,8)
    require(count==len(selected) and not any(raw[24:32]) and recover in (0,1) and state<=65535,
        'evidence child filesystem fields differ')
    pos=32;rows=[]
    for index,(name,mode,gid,maximum,capture) in enumerate(selected):
        require(pos+96<=len(raw)-32,'short evidence file header')
        row=raw[pos:pos+96];pos+=96
        ordinal,status=struct.unpack_from('<2I',row);error=struct.unpack_from('<Q',row,8)[0]
        inode,actual_mode,uid,actual_gid,links,generation=struct.unpack_from('<6I',row,16)
        size=struct.unpack_from('<Q',row,40)[0];length=struct.unpack_from('<I',row,48)[0]
        offset=struct.unpack_from('<Q',row,56)[0]
        require(ordinal==index and status in range(5) and not any(row[52:56]),'evidence file status/order differs')
        require(pos+length<=len(raw)-32 and length<=capture,'evidence suffix bound differs')
        contents=raw[pos:pos+length];pos+=length
        if status==0:
            require(not error and inode>=2 and actual_mode==mode and uid==0 and actual_gid==gid and links==1 and
                size<=maximum and length==min(size,capture) and offset==size-length,'evidence regular-file facts differ')
            if offset==0:require(hashlib.sha256(contents).digest()==row[64:96],'full evidence file hash differs')
        else:
            require(not length and not offset and not any(row[64:96]),'failed file emitted unverified contents')
            require((error>0) if status in (1,2) else error==0,'evidence file error status differs')
            if status==1:require(error==FILE_NOT_FOUND and not any(row[16:48]),'absent file status differs')
            if status==4:require(size>maximum and inode>=2 and actual_mode==mode and uid==0 and
                actual_gid==gid and links==1,'oversize result has invalid size or metadata')
        rows.append(dict(path=name,status=('READ','ABSENT_IN_HOME_VIEW','READ_ERROR','METADATA_REJECTED','OVERSIZE')[status],
            error=error,inode=inode,mode=actual_mode,uid=uid,gid=actual_gid,links=links,generation=generation,size=size,
            offset=offset,captured=length,sha256=row[64:96].hex() if status==0 else None,raw_hex=contents.hex()))
    footer=raw[pos:];require(len(footer)==32 and footer[:8]==b'S22NEND\0','evidence footer/tail differs')
    read_bytes,calls,writes,total,reserved=struct.unpack_from('<Q4I',footer,8)
    require(0<read_bytes<=64*1024*1024 and 0<calls<=16384 and writes==reserved==0 and total==len(raw),
        'evidence I/O accounting differs')
    return dict(files=rows,superblock=dict(state=state,recover=recover,orphan=orphan),read_bytes=read_bytes,read_calls=calls,
        view='CHECKPOINTED_HOME_BLOCKS_NO_JOURNAL_REPLAY',latest_state_complete=False,absence_proves_nonexecution=False)


def decode(stdout,stderr,binding):
    require(not stderr and 0<len(stdout)<=MAXIMUM and stdout.endswith(b'\n'),'incomplete evidence acquisition')
    lines=stdout.decode('ascii').splitlines()
    require(len(lines)==11 and lines[:3]==['RI1_BEGIN version=1','RI1_BIND exact=1','RI1_BLOCK_RO partition=1'] and
        lines[4]=='NE1_READ mount=0 replay=0 output_max=24576','evidence binding or non-mount scope differs')
    superblock=inspection._row(lines[3],'RI1_SUPER',('clean','state','recover','orphan'))
    streams={}
    for line,name in zip(lines[5:8],('stdout','stderr','setup')):
        match=re.fullmatch(r'UP1_OUTPUT stream='+name+r' bytes=(0|[1-9][0-9]*) hex=([0-9a-f]+|-)',line)
        require(match is not None,'raw evidence child output framing differs')
        n=int(match[1]);body=b'' if match[2]=='-' else bytes.fromhex(match[2])
        require(n==len(body)<=CHILD_MAXIMUM and (bool(n)==(match[2]!='-')),'raw child output accounting differs')
        streams[name]=body
    require(streams['setup']==struct.pack('<2I',100,0) and not streams['stderr'],'evidence reader setup failed')
    child=inspection._row(lines[8],'UP1_CHILD',('attempted','reaped','adopted','settled','status','setup_stage','setup_errno','error','proved'))
    require(child==dict(attempted=1,reaped=1,adopted=0,settled=1,status=0,setup_stage=100,setup_errno=0,error=0,proved=1),
        'evidence reader process did not settle successfully')
    require(lines[9]=='RI1_FINAL super_unchanged=1 gpt_unchanged=1 partition_ro=1','final protected identity absent')
    final=inspection._row(lines[10],'RI1_RESULT',('complete','stage','errno','cleanup_errno','partition_ro','clean','mounted','unmounted'))
    clean=int(superblock['state']==1 and superblock['recover']==0 and superblock['orphan']==0)
    require(superblock['clean']==clean and final==dict(complete=1,stage=10,errno=0,cleanup_errno=0,
        partition_ro=1,clean=clean,mounted=0,unmounted=0),'evidence final cleanup differs')
    data=decode_child(streams['stdout'],binding['record_run'])
    require(data['superblock']=={k:superblock[k] for k in ('state','recover','orphan')},'child/parent filesystem fields differ')
    return dict(data,status='PASS_ROOT_EVIDENCE_OBSERVED',partition_readonly=True,mounted=False,persistent_writes=False,
        debian_boot_proved=False,source_view_clean=bool(clean),reader_child=child)


class Profile:
    RESULT_KEY='root_evidence'
    MUTATES=True  # Exact partition-only RAM RO control.
    SETTLE_SECONDS=0
    OBSERVATION_SECONDS=300
    ADMISSION_SECONDS=245

    def __init__(self,image):
        image_binding(image);self.binding=image['root_evidence']
        require(re.fullmatch('[0-9a-f]{32}',image['run_id_hex']),'evidence command run differs')
        self.BODY=wire.command(('exec /s22-root-evidence evidence '+image['run_id_hex']).encode(),
            cwd=b'/s22-root-work',timeout_ms=240000)

    def project(self,stdout,stderr,terminal,*,requested):
        result=dict(schema=SCHEMA,status='NO_PROOF',requested=requested,
            stdout=dict(size=len(stdout),sha256=hashlib.sha256(stdout).hexdigest()),
            stderr=dict(size=len(stderr),sha256=hashlib.sha256(stderr).hexdigest()))
        if not requested:return dict(result,reason='ORIGINAL_OBSERVATION_BUDGET_INSUFFICIENT')
        if terminal is None or terminal[:4]!=(5,0,0,0) or terminal[4]!=len(stdout)+len(stderr) or terminal[5]!=0:
            return dict(result,reason='EVIDENCE_COMMAND_INCOMPLETE')
        try:proof=decode(stdout,stderr,self.binding)
        except (ValueError,UnicodeError,IndexError,KeyError,struct.error) as error:return dict(result,reason=str(error))
        return dict(result,**proof)
