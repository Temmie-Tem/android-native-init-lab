"""Fixed foreground Android GPT census after a closed original-A return.

This D0 path uses existing Android block nodes. It neither opens a V3 grant nor
changes boot mode, creates a node, loads a module, or writes a storage byte.
"""
from pathlib import Path
import shlex

import consumed_candidate_registry_v1 as registry
import device_action_raw_capture_v1 as raw
import s22plus_boot_only_f1_transport as transport
import s22plus_native_storage_census_v1 as gpt
import s22plus_native_target_io_v3 as target_io
from s22plus_native_records_v3 import (canonical, clock, digest, host_boot, pin, private_path,
    publish, read, require, verify)

SCHEMA = 's22plus-native-android-storage-census-v1'
POLICY = 'docs/operations/S22PLUS_ANDROID_STORAGE_CENSUS_V1.md'
SCRIPT = r'''set -eu
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


def projection(receipt):
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
        metadata=gpt.decode(stdout)
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
        require(operation['operation']=='android-exit','normal Android close is not an Android exit')
        selected=steps('android-exit')
    session.completed(selected)
    require(terminal['terminal_result']==pin(directory/(selected[-1].name+'.json')),
        'Android terminal omits final raw health')
    require(task['A']==android_artifact(root),'closed task does not contain the exact original A')
    return task,pin(close_path)


def rederive(directory, task):
    directory=Path(directory);opened=read(directory/'open.json')
    require(opened['schema']==SCHEMA and opened['task_value_sha256']==digest(canonical(task))
        and read(verify(opened['task']))==task,'Android census task changed')
    require(read(directory/'read/intent.json')==dict(schema=SCHEMA,command_sha256=digest(SCRIPT.encode())),
        'Android census command intent differs')
    feature_receipt=pin(directory/'read/shell-features.capture.json');require_shell_v2(feature_receipt)
    before=read(directory/'before/health.json');after=read(directory/'after/health.json')
    for value in (before,after):
        require(target_io.health_projection(value['captures'],task['target'],task['A'])==value,
            'Android census health does not rederive')
    require(before['properties']==after['properties'] and before['boot_id_sha256']==after['boot_id_sha256'],
        'Android boot changed across census')
    result=dict(schema=SCHEMA,terminal_state='ANDROID_CLOSED_HEALTHY',
        metadata=projection(pin(directory/'read/metadata.capture.json')),
        initial_health=pin(directory/'before/health.json'),final_health=pin(directory/'after/health.json'),
        source_review=opened['source_review'],source_snapshot=opened['source_snapshot'],
        shell_v2_features=feature_receipt,
        task=opened['task'],boot_id_sha256=after['boot_id_sha256'],research_closed=True)
    return result


def observe(root, task_path, output):
    from s22plus_native_task_v3 import capability
    root=Path(root).resolve(strict=True);task_path=private_path(root,task_path)
    output=private_path(root,output,exists=False)
    require(not output.exists(),'Android census output already exists; no retry')
    with registry.target_session_lease(root):
        registry.require_no_f1_owner(root)
        review=capability(root);task,closed=closed_android(root,task_path)
        source_close=read(verify(closed));snapshot=source_close['source_snapshot'];manifest=read(verify(snapshot))
        require(manifest['review']==review,'Android source snapshot differs from current reviewed capability')
        require([row['original'] for row in manifest['sources']]==read(verify(review))['sources']+[review],
            'Android snapshot omits reviewed sources')
        for row in manifest['sources']:
            verify(row['snapshot'])
            require(all(row['original'][key]==row['snapshot'][key] for key in ('size','sha256')),
                'Android snapshot source content differs')
        output.mkdir(mode=0o700)
        epoch=host_boot();start=clock()
        def guard():
            require(host_boot()==epoch and clock()<start+600_000_000_000,'Android D0 host epoch or bound changed')
            require(capability(root)==review,'Android census capability changed')
            registry.require_no_f1_owner(root)
        publish(output/'open.json',dict(schema=SCHEMA,task=pin(task_path),
            task_value_sha256=digest(canonical(task)),source_review=review,source_snapshot=snapshot,
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
            result=rederive(output,task);publish(output/'terminal.json',result)
            return result
        except Exception as error:
            publish(output/'stopped.json',dict(schema=SCHEMA,error_type=type(error).__name__,
                retry_permitted=False,device_writes_permitted=False))
            raise
