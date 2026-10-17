"""One strict native_data replay and a separate protected post-replay admission."""
import hashlib
import re
import struct
from pathlib import Path

import s22plus_native_root_inspect_profile_v1 as inspection
import s22plus_native_staged_preflight_profile_v1 as staged
import s22plus_native_userspace_probe_profile_v1 as userspace
import s22plus_debian_handoff_profile_v1 as handoff
import s22plus_root_console_v1 as wire
from s22plus_native_records_v3 import pin, read, require, verify

ROOT=inspection.ROOT
SCHEMA='s22plus-native-journal-recovery-v1'
PROFILE='thermal-v3-reconnect-ufs-drain-journal-recovery-v1'
OPERATION=SELECTION='journal-recovery'
REPLAYER_BUILD=dict(path=str(ROOT/'workspace/private/outputs/s22plus-journal-recovery-p412-h0-20261003-1/replayer-target-2/result.json'),
    size=1374,sha256='e46466bfe31138e2e7eb7ad803e6ab450ff76b451e29a64ad6268abad08a4736')
PREDECESSOR=dict(path=str(ROOT/'workspace/private/outputs/s22plus-debian-handoff-p411-live-20261001-1/connected-preparation-1/task/closed.json'),
    size=4132,sha256='af659ad9fe0ec25b7a8e93c249db3768dcac99f406bddd8b200583f5a46833cc')
REPLAY=re.compile(rb'S22_JOURNAL_REPLAY_V1 stage=(\d+) writes=(\d+) bytes=(\d+) error=(\d+) io_error=(\d+) complete=([01])\n')


def prior_inputs():
    verify(PREDECESSOR)
    return inspection.prior_inputs()


def tool_inputs():
    import sys
    sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/analysis'))
    import s22plus_journal_replay_tool_h0 as producer
    value=read(verify(REPLAYER_BUILD));request=read(verify(value['request']))
    fs=read(verify(inspection.filesystem.BINDING))
    require(value['schema']=='s22plus-strict-journal-replay-tool-h0-v1' and
        value['fixture_only'] is False and value['live_authorized'] is False and
        request['upstream']['sha256']==producer.base.UPSTREAM_SHA256 and request['fixture_only'] is False,
        'strict replay tool role or source differs')
    require(verify(request['seal']).read_bytes()==producer.seal(fs['filesystem_uuid']),
        'replayer is not sealed to the exact native filesystem')
    for row in request['sources']: verify(row,maximum=4*1024*1024)
    for path in (producer.STRICT,producer.CORE):
        row=next(r for r in request['sources'] if r['path']==str(path))
        require(pin(path)==row and
            (Path(request['seal']['path']).parent/path.name).read_bytes()==path.read_bytes(),
            'replayer compiled inputs differ from reviewed sources')
    verify(value['replayer'],maximum=2*1024*1024)
    require(producer.base.tool_identity(value['replayer']['path'])==value['replayer'],'replayer ELF differs')
    return value,fs


def execution_binding(selection=None):
    value,fs=tool_inputs();prior_inputs()
    result=dict(replayer_build=REPLAYER_BUILD,replayer=value['replayer'],checker=fs['checker'],
        predecessor=PREDECESSOR,write_scope='internal-jbd2-replay-and-exact-finalization',
        child_uid=0,all_child_capabilities_zero=True,no_new_privs=True,inherited_command_group=True,
        child_seconds=150,output_maximum=4096,persistent_writes=True,pid1_handoff=False,
        mutable=[list(row) for row in handoff.MUTABLE])
    if selection is not None:
        import s22plus_debian_autoboot_profile_v1 as automatic
        require(selection==automatic.HISTORY_SELECTION,'unselected journal admission successor')
        table,count,boot=automatic.retained_comparison(True)
        result.update(history_selection=selection,historical_files=automatic.histories(True),
            history_retrieval=automatic.AUTO_RETRIEVAL,
            predecessor=read(verify(automatic.AUTO_RETRIEVAL))['reader_closed'],
            table_sha256=hashlib.sha256(table).hexdigest(),table_count=count,boot_count=boot,
            boot_count_encoding='canonical-ascii-1-through-99999-newline')
        for row in result['mutable']:
            if row[0]=='var/lib/lab/boot-count':row[4]=6
    return result


def header():
    row=execution_binding()['replayer']
    return (f'static const uint64_t rj_replayer_size={row["size"]}ULL;\n'+
        'static const uint8_t rj_replayer_sha256[32]={'+','.join(map(str,bytes.fromhex(row['sha256'])))+'};\n').encode()


def image_binding(image):
    selected=image['journal_recovery'];selection=selected.get('history_selection')
    require(image['profile']==PROFILE and selected==execution_binding(selection),
        'journal recovery image scope differs')
    # This binding describes only the subsequent protected inspection segment.
    bound=inspection.image_binding(dict(image,profile=inspection.PROFILE))
    if selection is not None:
        require(bound['table']['sha256']==selected['table_sha256'] and
            bound['table_count']==selected['table_count'] and bound['boot_count']==selected['boot_count'],
            'journal successor comparison table differs')
    return bound


def _writer(lines):
    require(len(lines)==4,'writer output framing differs')
    out=userspace._output(lines[0],'stdout');err=userspace._output(lines[1],'stderr')
    setup=userspace._output(lines[2],'setup')
    child=inspection._row(lines[3],'UP1_CHILD',('attempted','reaped','adopted','settled','status',
        'setup_stage','setup_errno','error','proved'))
    require(not err and setup==struct.pack('<II',100,0) and
        all(child[k]==v for k,v in dict(attempted=1,reaped=1,adopted=0,settled=1,
            setup_stage=100,setup_errno=0,error=0).items()),'writer did not conclusively settle')
    match=REPLAY.fullmatch(out);require(match is not None,'writer strict result absent')
    result=dict(zip(('stage','writes','bytes','error','io_error','complete'),map(int,match.groups())))
    require(result['stage']<=5 and result['writes']<=262146 and result['bytes']<=result['writes']*4096 and
        result['complete']==int(result['stage']==5 and result['error']==result['io_error']==0) and
        child['status']==(0 if result['complete'] else 8<<8) and child['proved']==result['complete'] and
        result['io_error']==0,'writer result or I/O settlement differs')
    if result['complete']:
        require(result['writes']>=2 and result['bytes']==(result['writes']-1)*4096+1024,
            'complete replay lacks its exact finalization writes')
    else:
        require(result['error']>0 and result['stage']<=3 and result['bytes']==result['writes']*4096 and
            (result['stage']>=2 or result['writes']==0),'negative replay write accounting differs')
    return dict(result,child=child)


def decode(stdout,stderr,binding):
    require(not stderr and 0<len(stdout)<=inspection.MAXIMUM and stdout.endswith(b'\n'),'recovery output incomplete')
    lines=stdout.decode('ascii').splitlines();require(len(lines)>=8,'recovery output too short')
    require(lines[:3]==['RI1_BEGIN version=1','RI1_BIND exact=1','RI1_BLOCK_RO partition=1'],
        'initial target or protection missing')
    initial=inspection._row(lines[3],'RI1_SUPER',('clean','state','recover','orphan'))
    require(initial['clean'] in (0,1) and initial['recover'] in (0,1) and
        initial['clean']==int(initial['state']==1 and initial['recover']==initial['orphan']==0),
        'initial filesystem state contradicts cleanliness')
    before=inspection._row(lines[4],'JR1_BEFORE',('sha256',));pos=5
    writer=None;checker=None;after=initial;root_lines=lines[:4];root_match=None
    if lines[pos].startswith('JR1_SKIP '):
        skip=inspection._row(lines[pos],'JR1_SKIP',('clean',));pos+=1
        require(skip['clean']==initial['clean'] and (initial['clean'] or initial['state']!=1 or initial['orphan']),
            'eligible dirty root skipped without its writer')
    else:
        require(initial==dict(clean=0,state=1,recover=1,orphan=0) and
            lines[pos]=='JR1_BLOCK_RW partition=1','replay lacks its eligible root/RO clear')
        pos+=1;writer=_writer(lines[pos:pos+4]);pos+=4
        require(lines[pos]=='JR1_BLOCK_RO partition=1 settled=1','writer RO restoration missing');pos+=1
        after=inspection._row(lines[pos],'JR1_AFTER',('clean','state','recover','orphan'));pos+=1
        require(after['clean']==int(after['state']==1 and after['recover']==after['orphan']==0),
            'post-replay state contradicts cleanliness')
        if writer['complete']:require(after==dict(clean=1,state=1,recover=0,orphan=0),'completed writer left dirty root')
        root_lines[3]='RI1_SUPER '+ ' '.join(f'{key}={after[key]}' for key in ('clean','state','recover','orphan'))
    may_check=bool(after['clean'] and (writer is None or writer['complete']))
    if may_check:
        require(lines[pos]=='JR1_CHECKER begin=1','protected checker absent');pos+=1
        checker=staged._child('checker',lines[pos:pos+4]);pos+=4
        require(checker['adopted']==0 and checker['setup_stage']==100 and checker['setup_errno']==0 and
            checker['status']&127==0,'checker settlement differs')
    for line in lines[pos:-1]:
        if line.startswith('JR1_ROOT '):
            require(root_match is None and root_lines[-1].startswith('RI1_COMPARE '),'root result misplaced')
            root_match=inspection._row(line,'JR1_ROOT',('exact','extra'))
            require(root_match['exact'] in (0,1) and root_match['extra']<=len(handoff.MUTABLE),'root result invalid')
        else:
            require(line.startswith('RI1_'),'unknown recovery record');root_lines.append(line)
    final=inspection._row(lines[-1],'JR1_RESULT',('complete','attempted','writer_complete','checker_complete',
        'root_match','stopped','io_error'))
    checker_ok=bool(checker and checker['proved'])
    require(final['complete']==1 and final['attempted']==int(writer is not None) and
        final['writer_complete']==int(bool(writer and writer['complete'])) and
        final['checker_complete']==int(checker_ok) and final['io_error']==0,'recovery aggregate differs')
    require((root_match is not None)==checker_ok,'mounted root lacks protected checker')
    base=staged._premount_root(root_lines) if after['clean'] and not checker_ok else \
        inspection.decode(('\n'.join(root_lines)+'\n').encode(),b'',binding)
    exact=bool(root_match and root_match['exact'])
    require(final['root_match']==int(exact) and final['stopped']==int(not exact),'root aggregate differs')
    if exact:
        require(base['markers']==dict(start=1,complete=1,witness=1) and
            base['comparison']['matched']==base['comparison']['expected'] and
            base['tree']['entries']==binding['table_count']+4+root_match['extra'] and not base['tree']['other'],
            'exact root lacks immutable comparison or finite mutable accounting')
    return dict(status='PASS_JOURNAL_RECOVERY_OBSERVED',verdict='PROVED_CLEAN_ROOT' if exact else 'RECOVERY_NOT_PROVED',
        recovery_proved=exact,initial=initial,post_replay=after,pre_superblock=before,writer=writer,
        checker=checker,root_inspection=base,root_match=root_match,persistent_write_attempted=bool(writer),
        persistent_writes=bool(writer and writer['writes']),pid1_handoff=False,debian_boot_proved=False)


class Profile:
    RESULT_KEY='journal_recovery'
    MUTATES=True
    SETTLE_SECONDS=0
    OBSERVATION_SECONDS=300
    ADMISSION_SECONDS=245

    def __init__(self,image):
        self.binding=image_binding(image)
        require(re.fullmatch('[0-9a-f]{32}',image['run_id_hex']),'invalid journal recovery run')
        self.BODY=wire.command(('exec /s22-journal-recovery recover-journal '+image['run_id_hex']).encode(),
            cwd=b'/s22-root-work',timeout_ms=240000)

    def project(self,stdout,stderr,terminal,*,requested):
        result=dict(schema=SCHEMA,status='NO_PROOF',requested=requested)
        if not requested:return dict(result,reason='ORIGINAL_OBSERVATION_BUDGET_INSUFFICIENT')
        if terminal is None or terminal[:4]!=(5,0,0,0) or terminal[4]!=len(stdout)+len(stderr) or terminal[5]:
            return dict(result,reason='JOURNAL_RECOVERY_COMMAND_INCOMPLETE')
        try:proof=decode(stdout,stderr,self.binding)
        except (ValueError,UnicodeError,IndexError,KeyError) as error:return dict(result,reason=str(error))
        return dict(result,**proof)
