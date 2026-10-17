"""H0 interpretation of two sealed automatic-boot files after healthy closure."""
import argparse
import hashlib
import hmac
import os
from pathlib import Path
import struct

import s22plus_debian_autoboot_profile_v1 as writer_profile
import s22plus_debian_evidence_v1 as durable
import s22plus_debian_file_protocol_v1 as early
import s22plus_native_evidence_profile_v1 as reader_profile
from s22plus_debian_file_retrieval_v1 import closed_operation
from s22plus_native_records_v3 import pin,private_path,publish,read,require,verify
from s22plus_native_session_v3 import operation_steps

ROOT=writer_profile.ROOT


def early_header(data,key,selected):
    """Authenticate a surviving header even when its log body is missing."""
    require(type(data) is bytes and early.HEADER<=len(data)<=early.MAXIMUM,'early file has no bounded header')
    header=data[:early.HEADER];run=bytes.fromhex(selected['run_id']);boot=header[48:80]
    require(header[:8]==b'S22FL03\0' and struct.unpack_from('<II',header,8)==(3,early.HEADER) and
        header[16:32]==run and not any(header[216:224]) and
        hmac.compare_digest(header[224:],early.common.tag(key,run,boot,0,0,header[:224],domain=writer_profile.DOMAIN)),
        'early header authentication differs')
    pid1,child,status,length=struct.unpack_from('<4I',header,32)
    origin=struct.unpack_from('<Q',header,208)[0];expected=selected['measured']
    require(pid1==1 and child>1 and status==0 and origin<300000 and 0<length<=early.MAXIMUM-early.HEADER-14*early.RECORD and
        header[80:112].hex()==expected['shell_sha256'] and header[112:144].hex()==expected['init_sha256'] and
        header[176:208].hex()==expected['helper_sha256'],'early header PID1 or source identity differs')
    return dict(authenticated=True,boot=boot.hex(),derived_nonce=hashlib.sha256(header).hexdigest(),
        preparation_bytes=length,preparation_sha256=header[144:176].hex(),progress_log_verified=False)


def runtime_prefix(data,key,selected):
    require(type(data) is bytes and durable.HEADER<=len(data)<=durable.MAXIMUM,
        'runtime file has no bounded header')
    header=data[:durable.HEADER];device=struct.unpack_from('<Q',header,192)[0]
    root_device=dict(major=os.major(device),minor=os.minor(device))
    require(os.makedev(root_device['major'],root_device['minor'])==device,'runtime local device encoding differs')
    # Boot/nonce/device are local claims. The first decode authenticates them
    # and verifies the independently sealed physical run/init/hook identities.
    expected=dict(key_sha256=hashlib.sha256(key).hexdigest(),run_id_hex=selected['run_id'],
        boot=header[32:64].hex(),nonce_sha256=hashlib.sha256(header[64:96]).hexdigest(),
        init_sha256=selected['installed_init']['sha256'],hook_sha256=selected['hook']['sha256'],
        root_device=root_device)
    durable.decode(header,key,expected,autoboot=True)
    proof=durable.decode(data,key,expected,allow_prefix=True,autoboot=True)
    return dict(proof=proof,header=dict(authenticated=True,boot=expected['boot'],
        nonce=header[64:96].hex(),root_device=root_device,
        binding='AUTHENTICATED_LOCAL_PRODUCER_OBSERVATION',external_binding_proved=False))


def project(early_bytes,runtime_bytes,*,key,selected):
    """Keep independent authenticated prefixes even if their peer is absent."""
    require(type(key) is bytes and len(key)==32,'writer authentication key differs')
    result=dict(schema='s22plus-debian-autoboot-retrieval-projection-v1',
        early=dict(status='NOT_CAPTURED'),runtime=dict(status='NOT_CAPTURED'),
        join=dict(status='UNAVAILABLE'),highest_authenticated_stage=None,
        service_observation_ms=None,boot_progress_claim_valid=False,
        ssh_access_proved=False,clean_shutdown_proved=False,
        current_filesystem_consistency_proved=False,absence_proves_nonexecution=False,replay_authorized=False)
    first=None;first_header=None;runtime=None;stage=None
    if early_bytes is not None:
        try:
            first_header=early_header(early_bytes,key,selected)
            first=early.decode(early_bytes,key=key,run=bytes.fromhex(selected['run_id']),
                expected=selected['measured'],module_names=[m['runtime_name'] for m in selected['modules']],
                allow_prefix=True,storage_first=True,diagnostic=True,autoboot=True)
            first_header['progress_log_verified']=True
            result['early']=dict(status='AUTHENTICATED',header=first_header,proof=first)
            stage='EARLY_PRE_UNMOUNT' if first['pre_unmount_complete'] else 'EARLY_PID1_STORAGE_PREPARATION'
        except (ValueError,KeyError,struct.error) as error:
            result['early']=dict(status='AUTHENTICATED_HEADER_ONLY' if first_header else 'NO_AUTHENTICATED_PROGRESS',
                error=str(error),**(dict(header=first_header) if first_header else {}))
    if runtime_bytes is not None:
        try:
            decoded=runtime_prefix(runtime_bytes,key,selected);runtime=decoded['proof']
            result['runtime']=dict(status='AUTHENTICATED',**decoded)
            if runtime['local_init_observed']:stage='INSTALLED_DEBIAN_PID1'
            if runtime['automatic_start']:stage='INSTALLED_INIT_HOOK_COMPLETE'
            if any(row['kind']==durable.PROGRESS for row in runtime['records']):stage='RCS_ENTERED'
            if runtime['rcs_completed']:stage='RCS_COMPLETED'
            if runtime['runlevel_completed']:stage='RUNLEVEL2_COMPLETED'
            samples=[row['a'] for row in runtime['records'] if row['kind']==durable.PROGRESS and row['phase'] in (3,4)]
            if samples:
                result['service_observation_ms']=max(samples);stage='SERVICES_OBSERVED'
            if runtime['local_runtime_proved']:stage='SERVICES_120S_COMPLETE'
        except (ValueError,KeyError,OverflowError,struct.error) as error:
            result['runtime']=dict(status='NO_AUTHENTICATED_PROGRESS',error=str(error))
    if first_header is not None and runtime is not None:
        header=result['runtime']['header']
        boot=header['boot']==first_header['boot']
        nonce=header['nonce']==first_header['derived_nonce']
        result['join']=dict(status='MATCH' if boot and nonce else 'CONFLICT',boot_matches=boot,nonce_matches=nonce)
    conflict=result['join']['status']=='CONFLICT'
    result.update(status='AUTHENTICATED_RECORDS_CONFLICT' if conflict else
        'PASS_AUTHENTICATED_LOCAL_PROGRESS' if stage else 'NO_AUTHENTICATED_PROGRESS',
        highest_authenticated_stage=None if conflict else stage,boot_progress_claim_valid=stage is not None and not conflict)
    return result


def save_raw(path,data):
    """Empty captured files are preserved too; emptiness is not non-execution."""
    with path.open('xb') as stream:
        require(stream.write(data)==len(data),'short raw file copy')
        stream.flush();os.fsync(stream.fileno())
    path.chmod(0o400)
    require(path.read_bytes()==data and path.stat().st_nlink==1,'raw file changed after copy')
    return dict(path=str(path),size=len(data),sha256=hashlib.sha256(data).hexdigest())


def recover(directory,writer_directory,reader_directory):
    directory=private_path(ROOT,directory,exists=False)
    require(not directory.exists(),'fresh pair projection directory required')
    writer=closed_operation(writer_directory,writer_profile.PROFILE)
    reader=closed_operation(reader_directory,reader_profile.PROFILE)
    image=writer['request']['N'];binding=reader['request']['N']['root_evidence']
    require(writer['task']['target']==reader['task']['target'] and writer['task']['A']==reader['task']['A'] and
        binding==reader_profile.binding(image['run_id_hex'],reader_profile.AUTOBOOT_PAIR) and
        reader['request']['N']['run_id_hex']!=image['run_id_hex'],'reader does not select this closed writer pair')
    artifact=read(verify(image['autoboot_boot']));selected=read(verify(artifact['build']))
    require(selected['profile']==writer_profile.PROFILE and selected['run_id']==image['run_id_hex'] and
        selected['namespace']==image['namespace'] and selected['version']==image['version'] and
        selected['virtual'] is False,'writer is not the selected physical build')
    verify(selected['hook'])
    init=selected['installed_init']
    require(set(init)=={'size','sha256'} and type(init['size']) is int and init['size']>0 and
        type(init['sha256']) is str and len(init['sha256'])==64 and
        all(c in '0123456789abcdef' for c in init['sha256']),'installed init build identity differs')
    key=verify(image['key'],maximum=32).read_bytes()
    step=next(s for s in operation_steps(reader['request']) if s.name==reader_profile.SELECTION)
    acquired=reader['session'].completed((step,))[0]['proof']['root_evidence']
    rules=reader_profile.paths(image['run_id_hex'],reader_profile.AUTOBOOT_PAIR)
    require([row['path'] for row in acquired['files']]==[row[0] for row in rules],
        'reader returned a different file selection')
    directory.mkdir(mode=0o700)
    context=dict(schema='s22plus-debian-autoboot-retrieval-h0-v1',source=pin(Path(__file__)),
        writer_closed=writer['closed'],reader_closed=reader['closed'],writer_terminal=writer['terminal_receipt'],
        reader_terminal=reader['terminal_receipt'],writer_artifact=image['autoboot_boot'],
        writer_build=artifact['build'],reader_result=pin(reader['adapter'].directory/(step.name+'.json')),
        source_view_clean=acquired['source_view_clean'],reader_journal_replayed=False,
        writer_android_healthy=True,reader_android_healthy=True,device_actions=0,
        absence_proves_nonexecution=False,replay_authorized=False)
    # Preserve the complete acquisition and every captured file before either
    # parser runs. One malformed file cannot discard its peer's raw bytes.
    publish(directory/'acquisition.json',dict(context,files=acquired['files']))
    raw_files={};values=[]
    for name,row in zip(('early','runtime'),acquired['files']):
        data=bytes.fromhex(row['raw_hex']) if row['status']=='READ' else None
        if data is not None:
            require(len(data)==row['size']==row['captured'] and row['offset']==0 and
                hashlib.sha256(data).hexdigest()==row['sha256'],'captured pair file differs')
            raw_files[name]=save_raw(directory/(name+'.bin'),data)
        values.append(data)
    publish(directory/'raw.json',dict(files=raw_files))
    proof=project(*values,key=key,selected=selected)
    return publish(directory/'result.json',dict(context,raw=raw_files,proof=proof,status=proof['status']))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','writer','reader'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=recover(args.output,args.writer,args.reader)
    print(read(verify(result))['status'])
