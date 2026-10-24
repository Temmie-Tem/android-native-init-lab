"""One fixed pre-build Android D0 read of native_data's first 4096 bytes."""
import argparse
from pathlib import Path
import re
import shlex

import consumed_candidate_registry_v1 as registry
import device_action_raw_capture_v1 as raw
import s22plus_native_android_storage_v1 as census
import s22plus_native_gpt_android_v1 as storage
import s22plus_native_gpt_profile_v1 as gpt
import s22plus_native_ext4_profile_v1 as ext4
import s22plus_native_root_inspect_profile_v1 as inspection
import s22plus_native_target_io_v3 as target
import s22plus_native_task_v3 as task_api
import s22plus_debian_reboot_v1 as spec
from s22plus_native_records_v3 import clock,digest,host_boot,pin,private_path,publish,read,require,verify

SCHEMA='s22plus-debian-reboot-baseline-v1'
PROFILE='debian-reboot-baseline-d0-v1'
# Existing node only; no mount, ioctl, chmod, mknod, helper staging or device write.
SCRIPT=r'''set -eu
B=/system/bin/toybox
u=$($B readlink -f /dev/block/by-name/userdata)
case "${u##*/}" in sd?40) ;; *) exit 1;; esac
r=$($B readlink -f "/sys/class/block/${u##*/}")
p=${r%/*}
case "$p" in /sys/devices/platform/soc*/1d84000.ufshc/host*/target*/*:0:0:0/block/sd?) ;; *) exit 1;; esac
n="$p/${p##*/}41"
d="/dev/block/${p##*/}41"
g(){
 [ -b "$d" ]
 [ "$($B readlink -f /dev/block/by-name/userdata)" = "$u" ]
 [ "$($B readlink -f "/sys/class/block/${u##*/}")" = "$r" ]
 [ "$($B readlink -f "/sys/class/block/${d##*/}")" = "$n" ]
 [ "$($B readlink -f "$d")" = "$d" ]
 [ "$($B cat "$n/partition")" = 41 ]
 [ "$($B sed -n 's/^PARTNAME=//p' "$n/uevent")" = native_data ]
 [ "$($B cat "$n/start")" = 96923648 ]
 [ "$($B cat "$n/size")" = 401516544 ]
 [ "$($B cat "$p/size")" = 498442240 ]
 [ "$($B cat "$p/queue/logical_block_size")" = 4096 ]
 IFS=: read a b <"$n/dev"
 [ "$($B stat -c %t:%T "$d")" = "$(printf '%x:%x' "$a" "$b")" ]
 printf '%s\n' "$n"
 for f in "$n"/dev "$n"/partition "$n"/start "$n"/size "$p"/dev "$p"/size "$p"/queue/logical_block_size; do $B cat "$f"; done
 $B stat -c %t:%T "$d"
}
printf 'S22_REBOOT_BASELINE_BEGIN\n'
g
$B dd if="$d" bs=4096 count=1 status=none
printf 'S22_REBOOT_BASELINE_AFTER\n'
g
printf 'S22_REBOOT_BASELINE_END\n'
'''


def filesystem():
    return read(verify(inspection.filesystem.BINDING))


def block_projection(block):
    require(type(block) is bytes and len(block)==4096,'baseline block is not exactly 4096 bytes')
    value=ext4.superblock(block[1024:2048],filesystem()['filesystem_uuid'])
    count=int.from_bytes(block[1024+0x34:1024+0x36],'little');spec.count(count)
    return dict(initial_mount_count=count,superblock=value,block=dict(size=4096,sha256=digest(block)))


def decode(output,gpt_output):
    begin=b'S22_REBOOT_BASELINE_BEGIN\n';after=b'S22_REBOOT_BASELINE_AFTER\n';end=b'S22_REBOOT_BASELINE_END\n'
    require(type(output) is bytes and len(output)<=16384 and output.startswith(begin) and output.endswith(end),
        'baseline read framing differs')
    rows=output[len(begin):].split(b'\n',9);require(len(rows)==10,'baseline geometry is incomplete')
    fields=[s.decode('ascii') for s in rows[:9]];body=rows[9]
    require(body[4096:]==after+b'\n'.join(rows[:9])+b'\n'+end,'baseline endpoint changed or output length differs')
    node,dev,part,start,size,parent_dev,total,logical,hexdev=fields
    origin=census.gpt.geometry(gpt_output[3:].split(b'\n',8)[:8])
    require(node==origin['ancestry'].rsplit('/',1)[0]+'/'+origin['parent']+'41' and
        (part,start,size,total,logical)==('41',str(ext4.FIRST_LBA*8),str(ext4.BLOCK_COUNT*8),str(62305280*8),'4096') and
        parent_dev==origin['parent_device'] and
        census.gpt.device_number(dev)==census.gpt.device_number(hexdev,hexadecimal=True),
        'native_data block identity is not on the same exact GPT LU0')
    return dict(block_projection(body[:4096]),node=node,device=dev,parent_device=parent_dev,
        partition_index=41,first_lba=ext4.FIRST_LBA,block_count=ext4.BLOCK_COUNT)


def authorization(root):
    review=task_api.capability(root,profile='debian-autoboot-v1')
    details=(root/task_api.DETAILS).read_bytes();contract=(root/'AGENTS.md').read_bytes()
    require(digest(details).encode() in contract and Path(spec.POLICY).name.encode() in details and
        Path(spec.POLICY).name.encode() in (root/task_api.TARGET_CONTRACT).read_bytes() and
        b'Status: **REVIEW_GATED_CAPABILITY**' in (root/spec.POLICY).read_bytes() and
        PROFILE.encode() in (root/spec.POLICY).read_bytes(),'reboot baseline D0 lacks reviewed common/target adoption')
    return review


def storage_admission(folder,prior):
    captures={name:raw.load_handle(folder/(name+'.capture.json')) for name in ('metadata','stat')}
    for handle in captures.values():
        raw.require_success(handle);require(not raw.read_stderr(handle,maximum=16384),'baseline storage admission has diagnostics')
    sealed=gpt.vectors(prior['basis']['gpt']);metadata=raw.read_stdout(captures['metadata'],maximum=65536)
    current_gpt=storage.metadata(metadata,sealed,'proposed')
    capacity=storage.storage_stat(raw.decode_success_stdout(captures['stat'],maximum=16384),
        dict(layout='proposed',geometry=prior['basis']['geometry']),sealed)
    require(capacity['total_bytes']==34357624832,'baseline Android32 capacity differs')
    return current_gpt,capacity,metadata


def projection(directory):
    opened=read(directory/'open.json');task=read(verify(opened['task']))
    require(opened['schema']==SCHEMA and opened['profile']==PROFILE,'baseline opening scope differs')
    census.verify_snapshot(inspection.ROOT,opened['source_snapshot'],opened['source_review'])
    # Historical closure is rederived from raw A/health, without changing its old pins.
    historical,closed=census.closed_android(inspection.ROOT,verify(opened['task']))
    require(task==historical and closed==opened['closed_android'],'baseline closed return differs')
    _,_,prior=inspection.prior_inputs()
    require(task['target']==prior['target'] and task['A']==prior['A'],'baseline uses another target or original A')
    before=read(directory/'before/health.json');after=read(directory/'after/health.json')
    for value in (before,after):
        require(target.health_projection(value['captures'],task['target'],task['A'])==value,
            'baseline health does not rederive')
    require(before['properties']==after['properties'] and before['boot_id_sha256']==after['boot_id_sha256'],
        'Android boot changed across baseline read')
    census.require_shell_v2(pin(directory/'read/shell-features.capture.json'))
    require(read(directory/'read/baseline-intent.json')==dict(schema=SCHEMA,command_sha256=digest(SCRIPT.encode())),
        'baseline fixed command differs')
    captures={name:raw.load_handle(directory/'read'/(name+'.capture.json')) for name in ('metadata','stat','baseline')}
    for handle in captures.values():
        raw.require_success(handle);require(not raw.read_stderr(handle,maximum=16384),'baseline read has diagnostics')
    current_gpt,capacity,metadata=storage_admission(directory/'read',prior)
    baseline=decode(raw.read_stdout(captures['baseline'],maximum=16384),metadata)
    return dict(schema=SCHEMA,kind='ANDROID_FIXED_D0',status='PASS_BASELINE_SUPERBLOCK_ONLY',
        initial_mount_count=baseline['initial_mount_count'],baseline=baseline,metadata=current_gpt,capacity=capacity,
        opening=pin(directory/'open.json'),initial_health=pin(directory/'before/health.json'),
        final_health=pin(directory/'after/health.json'),captures={k:pin(v.receipt_path) for k,v in captures.items()},
        filesystem_binding=inspection.filesystem.BINDING,full_root_admitted=False,
        grants_device_authority=False,persistent_writes=False,grant_opened=False)


def observe(directory,closed_task):
    root=inspection.ROOT;directory=private_path(root,directory,exists=False)
    require(not directory.exists(),'baseline output already exists')
    with registry.target_session_lease(root):
        registry.require_no_f1_owner(root);review=authorization(root)
        task,closed=census.closed_android(root,private_path(root,closed_task))
        _,_,prior=inspection.prior_inputs()
        require(task['target']==prior['target'] and task['A']==prior['A'],'baseline target differs')
        directory.mkdir(mode=0o700);snapshot=census.snapshot_current(root,directory/'source-snapshot',review)
        epoch=host_boot();start=clock()
        lane=target.lane.capture_binding(target.lane.SOURCE_TOPOLOGY)
        def guard():
            require(host_boot()==epoch and clock()<start+600_000_000_000,'baseline host epoch or read window expired')
            require(authorization(root)==review,'baseline capability changed')
            registry.require_no_f1_owner(root)
            target.lane.revalidate_binding(lane,source_topology=target.lane.SOURCE_TOPOLOGY)
        publish(directory/'open.json',dict(schema=SCHEMA,profile=PROFILE,task=pin(closed_task),closed_android=closed,
            source_review=review,source_snapshot=snapshot,host_boot=epoch,started_ns=start))
        try:
            target.Android(task['adb'],task['target'],task['A'],directory/'before',guard=guard).health()
            reader=target.Android(task['adb'],task['target'],task['A'],directory/'read',guard=guard)
            failure=None;after_failure=None
            try:
                census.command(reader)
                reader.command(['-s',task['target']['serial'],'shell','-T','su -c '+shlex.quote(storage.STAT_SCRIPT)],'stat',timeout=15)
                storage_admission(directory/'read',prior)
                publish(directory/'read/baseline-intent.json',dict(schema=SCHEMA,command_sha256=digest(SCRIPT.encode())))
                reader.command(['-s',task['target']['serial'],'shell','-T','su -c '+shlex.quote(SCRIPT)],'baseline',timeout=15)
            except Exception as error:failure=error
            try:target.Android(task['adb'],task['target'],task['A'],directory/'after',guard=guard).health()
            except Exception as error:after_failure=error
            if failure is not None:
                if after_failure is not None:
                    publish(directory/'post-read-health-error.json',dict(error_type=type(after_failure).__name__))
                raise failure
            if after_failure is not None:raise after_failure
            guard()
            return publish(directory/'result.json',projection(directory))
        except Exception as error:
            publish(directory/'stopped.json',dict(schema=SCHEMA,error_type=type(error).__name__,
                repeat_authorized=False,device_writes_authorized=False));raise


def fixture(directory,block):
    directory=private_path(inspection.ROOT,directory,exists=False)
    require(not directory.exists(),'fresh baseline fixture output required');directory.mkdir(mode=0o700)
    value=block_projection(block);(directory/'block.bin').write_bytes(block)
    return publish(directory/'result.json',dict(schema=SCHEMA,kind='H0_SYNTHETIC',
        initial_mount_count=value['initial_mount_count'],baseline=value,block=pin(directory/'block.bin'),
        device_actions=0,physical_readiness=False))


def binding(receipt,*,physical=False):
    value=read(verify(receipt));require(value['schema']==SCHEMA,'baseline schema differs')
    if value['kind']=='ANDROID_FIXED_D0':
        require(value==projection(verify(receipt).parent),'baseline raw projection differs')
    else:
        require(value['kind']=='H0_SYNTHETIC' and not physical and value['device_actions']==0 and
            value['physical_readiness'] is False and value['baseline']==block_projection(verify(value['block']).read_bytes()) and
            value['initial_mount_count']==value['baseline']['initial_mount_count'],'synthetic baseline cannot qualify device use')
    spec.count(value['initial_mount_count'])
    return dict(initial_mount_count=value['initial_mount_count'],receipt=receipt,kind=value['kind'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--closed-task',type=Path,required=True)
    args=parser.parse_args();result=observe(args.directory,args.closed_task)
    print('PASS_BASELINE_SUPERBLOCK_ONLY '+result['sha256'])
