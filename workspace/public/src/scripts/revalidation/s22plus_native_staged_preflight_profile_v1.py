"""Fixed streamed preparation under the already-running native owner."""
import hashlib
import re
import struct

import s22plus_native_root_inspect_profile_v1 as inspection
import s22plus_native_userspace_probe_profile_v1 as userspace
import s22plus_root_console_v1 as wire
from s22plus_native_records_v3 import read, require, verify

ROOT = inspection.ROOT
SCHEMA = 's22plus-native-staged-preflight-v1'
PROFILE = 'thermal-v3-reconnect-ufs-drain-staged-preflight-v1'
OPERATION = SELECTION = 'staged-preflight'
prior_inputs=inspection.prior_inputs
STEPS = ('setup','binding','block-ro','superblock','checker','mount','markers','inventory',
    'comparison','eligibility','loader-inputs','loader-verify','loader-list','parent-protection',
    'unmount','final-binding','cleanup')
LOADER_LINES = ('linux-vdso.so.1',
    'libselinux.so.1 => /lib/aarch64-linux-gnu/libselinux.so.1',
    'libc.so.6 => /lib/aarch64-linux-gnu/libc.so.6', '/lib/ld-linux-aarch64.so.1',
    'libpcre2-8.so.0 => /lib/aarch64-linux-gnu/libpcre2-8.so.0')


def execution_binding():
    artifact, _, _ = inspection.prior_inputs()
    filesystem = read(verify(artifact['filesystem_binding']))
    return dict(checker=filesystem['checker'], stages=list(STEPS), loader_lines=list(LOADER_LINES),
        checker_uid=0, loader_uid=65534, all_child_capabilities_zero=True, no_new_privs=True,
        inherited_command_group=True, child_seconds=30, output_maximum=4096,
        persistent_writes=False, pid1_handoff=False, raw_before_parse=True)


def image_binding(image):
    require(image['profile']==PROFILE and image['staged_preflight']==execution_binding(),
        'staged preparation selection differs')
    return inspection.image_binding(dict(image,profile=inspection.PROFILE))


def header():
    import json
    import tarfile
    artifact, _, _ = inspection.prior_inputs()
    with tarfile.open(verify(artifact['rootfs'],maximum=256*1024*1024)) as archive:
        cache=archive.extractfile('etc/ld.so.cache').read()
    return ('/* Fixed stage grammar and retained loader inputs. */\n'+
        'static const char *const sp_steps[]={'+','.join(map(json.dumps,STEPS))+'};\n'+
        'static const char *const sp_loader_lines[]={'+','.join(map(json.dumps,LOADER_LINES))+'};\n'+
        f'static const uint64_t sp_cache_size={len(cache)}ULL;\n'+
        'static const uint8_t sp_cache_sha256[]={'+','.join(map(str,hashlib.sha256(cache).digest()))+'};\n').encode()


def progress(stdout, *, complete=False):
    """Markers are evidence of an emitted stage, never a completed session."""
    require(type(stdout) is bytes and len(stdout)<=inspection.MAXIMUM, 'stage output bound exceeded')
    finished_lines=stdout.split(b'\n')[:-1]
    stages=[]; active=None; previous=-1; diagnostic_error=None
    for raw in finished_lines:
        if not raw.startswith(b'SP1_STAGE '): continue
        try:
            match=re.fullmatch(rb'SP1_STAGE seq=([1-9][0-9]*) step=([a-z-]+) phase=(begin|pass|stop|error) errno=(0|[1-9][0-9]*)',raw)
            require(match is not None,'malformed stage marker')
            sequence=int(match[1]); name=match[2].decode(); phase=match[3].decode(); error=int(match[4])
            require(sequence==len(stages)+1 and sequence<=64 and name in STEPS and error<=4095 and
                (error>0)==(phase=='error'),'stage identity, sequence or error differs')
            if phase=='begin':
                require(active is None and STEPS.index(name)>previous,'overlapping or repeated stage')
                previous=STEPS.index(name);active=name
            else:
                require(active==name,'stage end has no matching start');active=None
            stages.append(dict(sequence=sequence,step=name,phase=phase,errno=error))
        except ValueError as error:
            if complete:raise
            diagnostic_error=str(error);break
    if complete: require(stdout.endswith(b'\n') and active is None,'incomplete final stage')
    return dict(stages=stages,last_started=next((r['step'] for r in reversed(stages) if r['phase']=='begin'),None),
        last_passed=next((r['step'] for r in reversed(stages) if r['phase']=='pass'),None),
        open_stage=active,diagnostic_error=diagnostic_error,session_completion_proved=False)


def _payload(kind, out, err):
    if kind=='checker': return all(f'Pass {i}:'.encode() in out for i in range(1,6)) and b'e2fsck ' in err
    if kind=='loader-verify': return not out and not err
    if err or not out.endswith(b'\n'): return False
    found=[]
    for line in out.decode('ascii').splitlines():
        match=re.fullmatch(r'\s*([^\r\n]+) \(0x[0-9a-f]{1,16}\)',line)
        if match is None: return False
        found.append(match[1])
    return len(found)==len(LOADER_LINES) and set(found)==set(LOADER_LINES)


def _child(kind, rows):
    require(len(rows)==4,'child evidence width differs')
    out=userspace._output(rows[0],'stdout');err=userspace._output(rows[1],'stderr')
    setup=userspace._output(rows[2],'setup')
    child=inspection._row(rows[3],'UP1_CHILD',('attempted','reaped','adopted','settled','status',
        'setup_stage','setup_errno','error','proved'))
    require(child['attempted']==child['reaped']==child['settled']==1 and child['error']==0 and
        child['status']<=65535 and child['adopted']<=16 and child['proved'] in (0,1),
        'child did not settle with an actual wait result')
    require(len(setup) in (8,16),'child setup evidence incomplete')
    packets=[struct.unpack('<II',setup[i:i+8]) for i in range(0,len(setup),8)]
    require(packets[-1]==(child['setup_stage'],child['setup_errno']) and
        ((len(packets)==1 and (packets[0]==(100,0) or
            1<=packets[0][0]<=7 and 0<packets[0][1]<=4095)) or
         (len(packets)==2 and packets[0]==(100,0) and packets[1][0]==101 and 0<packets[1][1]<=4095)),
        'child setup/exec framing differs')
    proved=packets==[(100,0)] and child['status']==child['adopted']==0 and _payload(kind,out,err)
    require(child['proved']==int(proved),'child result does not match raw workload evidence')
    return dict(child,kind=kind,outputs={name:dict(size=len(value),sha256=hashlib.sha256(value).hexdigest())
        for name,value in (('stdout',out),('stderr',err),('setup',setup))})


def _premount_root(lines):
    require(len(lines)==6 and lines[:3]==['RI1_BEGIN version=1','RI1_BIND exact=1','RI1_BLOCK_RO partition=1'] and
        lines[4]=='RI1_FINAL super_unchanged=1 gpt_unchanged=1 partition_ro=1',
        'checker stop lacks unchanged protected binding')
    superblock=inspection._row(lines[3],'RI1_SUPER',('clean','state','recover','orphan'))
    final=inspection._row(lines[5],'RI1_RESULT',('complete','stage','errno','cleanup_errno','partition_ro','clean','mounted','unmounted'))
    require(superblock==dict(clean=1,state=1,recover=0,orphan=0) and
        final==dict(complete=1,stage=10,errno=0,cleanup_errno=0,partition_ro=1,clean=1,mounted=0,unmounted=0),
        'checker stop has an invalid mount or cleanup state')
    return dict(superblock=superblock,mounted=False,unmounted=False,partition_ro=True,comparison=None,markers=None,tree=None)


def decode(stdout,stderr,binding):
    require(not stderr and 0<len(stdout)<=inspection.MAXIMUM and stdout.endswith(b'\n'),'staged output incomplete')
    marks=progress(stdout,complete=True);lines=stdout.decode('ascii').splitlines()
    require(lines[-1].startswith('SP1_RESULT '),'staged result absent')
    final=inspection._row(lines[-1],'SP1_RESULT',('complete','children','passed','stopped'))
    require(final['complete']==1 and final['children']<=3 and final['passed']<=final['children'] and final['stopped'] in (0,1),
        'preparation or cleanup did not complete')
    active=None;blocks={};eligibility=None;root_lines=[]
    for line in lines[:-1]:
        if line.startswith('SP1_STAGE '):
            row=next(r for r in marks['stages'] if r['sequence']==int(line.split('seq=')[1].split()[0]))
            active=row['step'] if row['phase']=='begin' else None
        elif line.startswith('UP1_'):
            require(active in ('checker','loader-verify','loader-list'),'child evidence outside its stage')
            blocks.setdefault(active,[]).append(line)
        elif line.startswith('SP1_ELIGIBLE '):
            require(active=='eligibility' and eligibility is None,'eligibility is repeated or misplaced')
            eligibility=inspection._row(line,'SP1_ELIGIBLE',('exact',))['exact']
            require(eligibility in (0,1),'invalid eligibility')
        elif line.startswith('RI1_'):
            stage={'RI1_BEGIN':None,'RI1_BIND':'binding','RI1_BLOCK_RO':'block-ro','RI1_SUPER':'superblock',
                'RI1_MOUNT':'mount','RI1_MARKERS':'markers','RI1_TREE':'inventory','RI1_COMPARE':'comparison',
                'RI1_FINDING':'comparison','RI1_UNMOUNT':'unmount','RI1_FINAL':'final-binding','RI1_RESULT':None}
            tag=line.split()[0]
            require(tag in stage and active==stage[tag],'root evidence outside its stage')
            root_lines.append(line)
        else:raise ValueError('unknown preparation record')
    children=[_child(kind,rows) for kind,rows in blocks.items()]
    require(len(children)==final['children'] and sum(r['proved'] for r in children)==final['passed'],
        'child aggregate differs')
    ends={r['step']:r['phase'] for r in marks['stages'] if r['phase']!='begin'}
    require(all(phase in ('pass','stop') for phase in ends.values()),'an errored stage cannot complete')
    for child in children:
        require(ends[child['kind']]==('pass' if child['proved'] else 'stop'),'child stage result differs')
    checker_stop=ends.get('checker')=='stop'
    base=_premount_root(root_lines) if checker_stop else inspection.decode(('\n'.join(root_lines)+'\n').encode(),b'',binding)
    expected=list(STEPS)
    if not base['superblock']['clean']:
        expected=list(STEPS[:4])+list(STEPS[-2:]);verdict='SKIPPED_UNCLEAN_ROOT'
        require(not children and eligibility is None and not final['stopped'],'unclean root reached a child')
    elif checker_stop:
        expected=list(STEPS[:5])+list(STEPS[-2:]);verdict='CHECKER_NOT_PROVED'
        require(len(children)==1 and eligibility is None and final['stopped']==1,'checker stop continued preparation')
    else:
        require(children and children[0]['kind']=='checker' and children[0]['proved']==1 and eligibility in (0,1),
            'mounted preparation lacks checker and eligibility evidence')
        if not eligibility:
            expected=list(STEPS[:10])+list(STEPS[-3:]);verdict='SKIPPED_ROOT_NOT_EXACT'
            require(len(children)==1 and ends['eligibility']=='stop' and final['stopped']==1,'ineligible root reached a loader')
        else:
            comparison,tree=base['comparison'],base['tree']
            require(base['markers']==dict(start=1,complete=1,witness=1) and
                comparison['expected']==comparison['matched'] and tree['entries']==comparison['expected']+4 and tree['other']==0,
                'loader lacks exact root closure')
            if ends.get('loader-verify')=='stop':expected.remove('loader-list')
            verdict='PROVED_PROTECTED_PREPARATION' if final['passed']==3 else 'LOADER_NOT_PROVED'
            require(final['stopped']==int(final['passed']!=3),'loader stop aggregate differs')
    require([r['step'] for r in marks['stages'] if r['phase']=='begin']==expected and
        len(marks['stages'])==len(expected)*2,'stage path differs from its observed branch')
    require(list(blocks)==[s for s in expected if s in ('checker','loader-verify','loader-list')],
        'stage lacks its unique child evidence')
    for step in expected:
        if step not in blocks and step!='eligibility':require(ends[step]=='pass','non-workload stage did not pass')
    if eligibility is not None:require(ends['eligibility']==('pass' if eligibility else 'stop'),'eligibility stage differs')
    return dict(status='PASS_STAGED_PREFLIGHT_OBSERVED',verdict=verdict,
        preparation_proved=verdict=='PROVED_PROTECTED_PREPARATION',stages=marks['stages'],
        root_inspection=base,children=children,persistent_writes=False,pid1_handoff=False,
        chroot_proved=False,debian_boot_proved=False)


class Profile:
    RESULT_KEY='staged_preflight'
    MUTATES=True
    SETTLE_SECONDS=0
    OBSERVATION_SECONDS=300
    ADMISSION_SECONDS=245

    def __init__(self,image):
        self.binding=image_binding(image)
        require(re.fullmatch('[0-9a-f]{32}',image['run_id_hex']),'invalid staged command run')
        self.BODY=wire.command(('exec /s22-staged-preflight staged '+image['run_id_hex']).encode(),
            cwd=b'/s22-root-work',timeout_ms=240000)

    def project(self,stdout,stderr,terminal,*,requested):
        result=dict(schema=SCHEMA,status='NO_PROOF',requested=requested)
        if not requested:return dict(result,reason='ORIGINAL_OBSERVATION_BUDGET_INSUFFICIENT')
        try:result['progress']=progress(stdout)
        except ValueError as error:result['progress_error']=str(error)
        if terminal is None or terminal[:4]!=(5,0,0,0) or terminal[4]!=len(stdout)+len(stderr) or terminal[5]:
            return dict(result,reason='STAGED_COMMAND_INCOMPLETE')
        try:proof=decode(stdout,stderr,self.binding)
        except (ValueError,UnicodeError,IndexError,KeyError) as error:return dict(result,reason=str(error))
        return dict(result,**proof)
