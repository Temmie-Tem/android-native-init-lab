"""Fixed foreground Android GPT census after a closed original-A return.

This D0 path uses existing Android block nodes. It neither opens a V3 grant nor
changes boot mode, creates a node, loads a module, or writes a storage byte.
"""
from pathlib import Path
import os
import shlex

import consumed_candidate_registry_v1 as registry
import device_action_raw_capture_v1 as raw
import s22plus_boot_only_f1_transport as transport
import s22plus_native_storage_census_v1 as gpt
import s22plus_native_target_io_v3 as target_io
from s22plus_native_records_v3 import (canonical, clock, digest, host_boot, pin, private_path,
    publish, read, read_bytes, require, verify)

SCHEMA = 's22plus-native-android-storage-census-v1'
POLICY = 'docs/operations/S22PLUS_ANDROID_STORAGE_CENSUS_V1.md'
SCRIPT_V1 = r'''set -eu
B=/system/bin/toybox
stage=userdata
trap 'rc=$?; [ "$rc" = 0 ] || printf "S22_GPT_STAGE=%s RC=%s\n" "$stage" "$rc" >&2' EXIT
v=$($B readlink -f /dev/block/by-name/userdata)
u=/sys/class/block/${v##*/}
r=$($B readlink -f "$u")
p=${r%/*}
stage=ancestry
case "$p" in /sys/devices/platform/soc*/1d84000.ufshc/host*/target*/*:0:0:0/block/sd?) ;; *) exit 1;; esac
d=/dev/block/${p##*/}
stage=device
[ -b "$d" ]
IFS=: read a b <"$p/dev"
[ "$($B stat -c %t:%T "$d")" = "$(printf '%x:%x' "$a" "$b")" ]
stage=geometry
[ "$($B cat "$p/queue/logical_block_size")" = 4096 ]
s=$($B cat "$p/size")
[ $((s%8)) = 0 ]
[ "$s" -gt 128 ]
g(){ printf '%s\n' "$r"; for f in "$u"/dev "$u"/start "$u"/size "$p"/dev "$p"/size "$p"/queue/logical_block_size; do $B cat "$f"; done; $B stat -c %t:%T "$d"; }
stage=primary
printf 'G0\n'
g
$B dd if="$d" bs=4096 count=6 status=none
stage=backup
$B dd if="$d" bs=4096 skip=$((s/8-5)) count=5 status=none
stage=final
printf 'G1\n'
g
printf 'END\n'
'''
LEGACY_PROFILE='lu0-tail5-v1'
CURRENT_PROFILE='lu0-tail9-v2'
require(SCRIPT_V1.count('skip=$((s/8-5)) count=5')==1,'legacy census declaration differs')
SCRIPT=SCRIPT_V1.replace('skip=$((s/8-5)) count=5','skip=$((s/8-9)) count=9')
TAIL9_GUARD=r'''us=$($B cat "$u/start")
uz=$($B cat "$u/size")
case "$us" in ''|*[!0-9]*) exit 1;; esac
case "$uz" in ''|*[!0-9]*) exit 1;; esac
[ "${#us}" -le 16 ]; [ "${#uz}" -le 16 ]; [ "$uz" -gt 0 ]
e=$((us+uz)); [ "$e" -le "$((s-72))" ]'''
require(SCRIPT.count('[ "$s" -gt 128 ]')==1,'legacy geometry guard differs')
SCRIPT=SCRIPT.replace('[ "$s" -gt 128 ]','[ "$s" -gt 128 ]\n'+TAIL9_GUARD)
PROFILES={LEGACY_PROFILE:(SCRIPT_V1,5),CURRENT_PROFILE:(SCRIPT,9)}


def command(android):
    """Preserve both bounded raw streams before interpreting the fixed read."""
    features=android.command(['-s',android.target['serial'],'features'],'shell-features',timeout=10)
    require_shell_v2(pin(features.receipt_path))
    android.guard()
    with transport.pin_regular_file(Path(android.tool['path']),label='ADB',
            expected_size=android.tool['size'],expected_sha256=android.tool['sha256']) as tool:
        android.guard()
        return raw.acquire_command([str(tool.path),'-s',android.target['serial'],
            'shell','-T','su -c '+shlex.quote(SCRIPT)],android.directory,'metadata',
            timeout=15,stdout_maximum=gpt.MAX_OUTPUT,stderr_maximum=16384)


def require_shell_v2(receipt):
    handle=raw.load_handle(verify(receipt))
    features=raw.decode_success_stdout(handle,maximum=16384).splitlines()
    require('shell_v2' in features,'Android shell-v2 transport is unavailable; no legacy fallback')


def projection(receipt, *, profile=LEGACY_PROFILE):
    require(profile in PROFILES,'unknown Android metadata profile')
    handle=raw.load_handle(verify(receipt))
    stdout=raw.read_stdout(handle,maximum=gpt.MAX_OUTPUT)
    stderr=raw.read_stderr(handle,maximum=16384)
    result=dict(schema=SCHEMA,status='NO_PROOF',capture=receipt,
        stdout=dict(size=len(stdout),sha256=digest(stdout)),
        stderr=dict(size=len(stderr),sha256=digest(stderr)),
        grants_partition_write_authority=False,node_creation=False)
    if (handle.returncode!=0 or handle.timed_out or handle.output_exceeded
            or handle.producer_error_type is not None or stderr):
        return dict(result,reason='ANDROID_CENSUS_COMMAND_DID_NOT_COMPLETE_SUCCESSFULLY')
    try:
        metadata=gpt.decode(stdout,backup_blocks=PROFILES[profile][1])
    except gpt.CensusError as error:
        return dict(result,reason=str(error))
    # The shared decoder also projects native alias cleanup from its END marker.
    # Android has no alias or cleanup operation; retain only its GPT semantics.
    metadata.pop('ram_block_alias_removed')
    return dict(result,status='PASS_METADATA_ONLY',uses_existing_android_block_node=True,**metadata)


def closed_android(root, task_path):
    """The old close is provenance, while fresh D0 health supplies live identity."""
    from s22plus_native_adapter_v3 import Adapter
    from s22plus_native_session_v3 import Session, steps
    from s22plus_native_task_v3 import android_artifact
    task_path=private_path(root,task_path);task=read(task_path)
    close_path=task_path.parent/'closed.json';close=read(close_path)
    require(close['schema']=='s22plus-native-session-v3-task-close-v1'
        and close['task']==pin(task_path) and close['terminal_state']=='ANDROID_CLOSED_HEALTHY'
        and close['operations'],'D0 requires a closed original-A Android return')
    terminal_receipt=close['operations'][-1]['terminal'];terminal=read(verify(terminal_receipt))
    require(terminal['terminal_state']=='ANDROID_CLOSED_HEALTHY' and terminal['research_closed'] is True,
        'original Android terminal is not closed healthy')
    operation=read(verify(terminal['operation_record']));directory=Path(terminal['operation_record']['path']).parent
    require(operation['task']==pin(task_path),'Android terminal belongs to another task')
    adapter=Adapter(root,directory);session=Session(root,directory,adapter)
    if terminal['recovered']:
        from s22plus_native_session_v3 import Step
        effects=[row['data'] for row in session.rows() if row['event']=='effect-intent'
            and row['data']['action']=='transfer' and row['data']['role']=='A']
        require(len(effects)==1,'Android recovery has no unique original-A transfer')
        selected=(Step(effects[0]['step'],'transfer','A'),Step('recovery-health','health','A'))
    else:
        require(operation['operation'] in ('android-exit','gpt-reserve'),
            'normal Android close is not an Android exit or completed GPT operation')
        selected=steps(operation['operation'])
    values=session.completed(selected)
    require(terminal['terminal_result']==pin(directory/(selected[-1].name+'.json')),
        'Android terminal omits final raw health')
    if operation['operation']=='gpt-reserve':
        derived=adapter.terminal(selected,values,operation,recovered=terminal['recovered'])['gpt']
        require(terminal['gpt']==derived and close['gpt']==derived,
            'closed GPT feature does not rederive from its raw operation proof')
    require(task['A']==android_artifact(root),'closed task does not contain the exact original A')
    return task,pin(close_path)


def verify_snapshot(root, receipt, review):
    """Read historical CAP bytes from their saved copy, never its moving path."""
    base=private_path(root,verify(receipt)).parent
    manifest=read(verify(receipt));rows=manifest['sources']
    require(manifest['schema']=='s22plus-native-v3-source-snapshot-v1' and manifest['review']==review,
        'source snapshot review differs')
    caps=[row for row in rows if row['original']==review]
    require(len(caps)==1,'source snapshot has no unique saved capability')
    for row in rows:
        path=private_path(root,Path(row['snapshot']['path']))
        require(path.is_relative_to(base),'saved source is outside its snapshot')
        verify(row['snapshot'])
        require(all(row['original'][key]==row['snapshot'][key] for key in ('size','sha256')),
            'source snapshot content differs')
    saved_review=read(verify(caps[0]['snapshot']))
    require(saved_review['schema']=='s22plus-native-session-v3-review'
        and saved_review['scope']=='V3_REACHABLE_CAPABILITY'
        and saved_review['verdict']=='PASS_GO' and saved_review['findings']==[]
        and [row['original'] for row in rows]==saved_review['sources']+[review],
        'source snapshot omits reviewed sources')
    return manifest


def snapshot_current(root, directory, review):
    """H0 source preservation precedes the first fresh Android command."""
    directory=private_path(root,directory,exists=False);directory.mkdir(mode=0o700)
    saved=[]
    for original in read(verify(review))['sources']+[review]:
        source=verify(original);data=read_bytes(source)
        require(digest(data)==original['sha256'],'source changed before snapshot')
        destination=directory/source.relative_to(root)
        destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        private_path(root,destination,exists=False)
        fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400)
        with os.fdopen(fd,'wb') as stream:
            require(stream.write(data)==len(data),'source snapshot write was short')
            stream.flush();os.fsync(stream.fileno())
        saved.append(dict(original=original,snapshot=pin(destination)))
    return publish(directory/'manifest.json',dict(schema='s22plus-native-v3-source-snapshot-v1',
        review=review,sources=saved))


def rederive(directory, task, *, root=None):
    directory=Path(directory);opened=read(directory/'open.json')
    root=Path(root) if root is not None else Path(__file__).resolve().parents[5]
    profile=opened.get('profile',LEGACY_PROFILE)
    require(profile in PROFILES,'unknown Android metadata profile')
    require(opened['schema']==SCHEMA and opened['task_value_sha256']==digest(canonical(task))
        and read(verify(opened['task']))==task,'Android census task changed')
    verify_snapshot(root,opened['source_snapshot'],opened['source_review'])
    if 'android_return_source_snapshot' in opened:
        verify_snapshot(root,opened['android_return_source_snapshot'],task['review'])
    require(read(directory/'read/intent.json')==dict(schema=SCHEMA,command_sha256=digest(PROFILES[profile][0].encode())),
        'Android census command intent differs')
    feature_receipt=pin(directory/'read/shell-features.capture.json');require_shell_v2(feature_receipt)
    before=read(directory/'before/health.json');after=read(directory/'after/health.json')
    for value in (before,after):
        require(target_io.health_projection(value['captures'],task['target'],task['A'])==value,
            'Android census health does not rederive')
    require(before['properties']==after['properties'] and before['boot_id_sha256']==after['boot_id_sha256'],
        'Android boot changed across census')
    result=dict(schema=SCHEMA,terminal_state='ANDROID_CLOSED_HEALTHY',
        metadata=projection(pin(directory/'read/metadata.capture.json'),profile=profile),
        initial_health=pin(directory/'before/health.json'),final_health=pin(directory/'after/health.json'),
        source_review=opened['source_review'],source_snapshot=opened['source_snapshot'],
        shell_v2_features=feature_receipt,
        task=opened['task'],boot_id_sha256=after['boot_id_sha256'],research_closed=True)
    if 'profile' in opened:result['profile']=profile
    return result


def observe(root, task_path, output):
    from s22plus_native_task_v3 import capability
    root=Path(root).resolve(strict=True);task_path=private_path(root,task_path)
    output=private_path(root,output,exists=False)
    require(not output.exists(),'Android census output already exists; no retry')
    with registry.target_session_lease(root):
        registry.require_no_f1_owner(root)
        review=capability(root);task,closed=closed_android(root,task_path)
        return_snapshot=read(verify(closed))['source_snapshot']
        verify_snapshot(root,return_snapshot,task['review'])
        output.mkdir(mode=0o700)
        snapshot=snapshot_current(root,output/'source-snapshot',review)
        epoch=host_boot();start=clock()
        def guard():
            require(host_boot()==epoch and clock()<start+600_000_000_000,'Android D0 host epoch or bound changed')
            require(capability(root)==review,'Android census capability changed')
            registry.require_no_f1_owner(root)
        publish(output/'open.json',dict(schema=SCHEMA,profile=CURRENT_PROFILE,task=pin(task_path),
            task_value_sha256=digest(canonical(task)),source_review=review,source_snapshot=snapshot,
            android_return_source_snapshot=return_snapshot,
            closed_android=closed,host_boot=epoch,started_ns=start))
        try:
            before=target_io.Android(task['adb'],task['target'],task['A'],output/'before',guard=guard)
            before.health()
            reader=target_io.Android(task['adb'],task['target'],task['A'],output/'read',guard=guard)
            publish(output/'read/intent.json',dict(schema=SCHEMA,command_sha256=digest(SCRIPT.encode())))
            command(reader)
            # This single post-read health bracket is allowed even for a failed
            # metadata command. It never repeats metadata or changes boot mode.
            after=target_io.Android(task['adb'],task['target'],task['A'],output/'after',guard=guard)
            after.health();guard()
            result=rederive(output,task,root=root);publish(output/'terminal.json',result)
            return result
        except Exception as error:
            publish(output/'stopped.json',dict(schema=SCHEMA,error_type=type(error).__name__,
                retry_permitted=False,device_writes_permitted=False))
            raise
