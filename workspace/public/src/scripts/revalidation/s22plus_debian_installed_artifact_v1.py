#!/usr/bin/env python3
"""Independent H0 readback of the installed-only P404 boot package."""
import argparse
import hashlib
from pathlib import Path
import stat
import sys

import s22plus_boot_only_f1_transport as transport
import s22plus_boot_verify as boot
import s22plus_debian_artifact_v1 as old_artifact
from s22plus_native_records_v3 import digest, pin, private_path, publish, read, require, verify

ROOT = Path(__file__).resolve().parents[5]
HERE = ROOT / 'workspace/public/src/debian/s22plus_v1/device'
sys.path.insert(0,str(HERE))
import installed_prepare as producer

SCHEMA = 's22plus-debian-installed-artifact-qualification-v1'
MAXIMUM = 128 * 1024 * 1024


def qualify(artifact_path, vm_path, output):
    artifact_path = private_path(ROOT, artifact_path, exists=True)
    vm_path = private_path(ROOT, vm_path, exists=True)
    output = private_path(ROOT, output, exists=False)
    require(not output.exists(), 'fresh private qualification output required')
    artifact_receipt = pin(artifact_path)
    artifact = read(artifact_path)
    require(artifact['schema'] == producer.SCHEMA and artifact['status'] == 'H0_BUILT_NOT_QUALIFIED'
        and artifact['namespace'] == producer.NAMESPACE and artifact['version'] == producer.VERSION
        and artifact['ab_identical'] is True and artifact['device_actions'] == 0
        and artifact['grants_device_authority'] is False
        and artifact['p401_artifact'] == producer.ARTIFACT
        and artifact['p401_qualification'] == producer.QUALIFIED
        and artifact['installed_root_proof'] == producer.TERMINAL
        and artifact['installed_root_close'] == producer.CLOSED
        and artifact['predecessor_terminal'] == producer.PREDECESSOR_TERMINAL
        and artifact['predecessor_close'] == producer.PREDECESSOR_CLOSE
        and artifact['baseline_native'] == dict(ap=producer.P399_AP,admission=producer.P399_ADMISSION)
        and artifact['removed_members'] == ['install.meta','install.sha256','rootfs.tar.xz'],
        'P404 selected build role or predecessor differs')
    producer.inputs()
    require(artifact['source_inputs'] == producer.source_inputs(),
            'P404 producer source inputs differ')
    old = read(verify(producer.ARTIFACT))
    before = verify(old['boot'],maximum=MAXIMUM).read_bytes()
    old_parsed, old_entries = producer.packaging.shared.entries(before)
    image = verify(artifact['boot'],maximum=MAXIMUM).read_bytes()
    parsed, entries = producer.packaging.shared.entries(image)
    omitted = set(artifact['removed_members'])
    added = {'p404-lab-qualify'}
    require(len(image) == len(before) == 96*1024*1024 and parsed.kernel == old_parsed.kernel
        and set(entries) == (set(old_entries)-omitted)|added
        and all(entries[name].mode == old_entries[name].mode and
                entries[name].data == old_entries[name].data
                for name in set(old_entries)-omitted-{'init'}),
        'P404 kernel/unchanged ramdisk inputs differ')
    init = verify(artifact['init']).read_bytes()
    script = verify(artifact['shutdown_overlay']).read_bytes()
    old_artifact.static_arm64(init)
    require(entries['init'].data == init and
        entries['p404-lab-qualify'].mode == stat.S_IFREG|0o500 and
        entries['p404-lab-qualify'].data == script and
        all(entries[name].uid == entries[name].gid == 0 and entries[name].nlink == 1 for name in entries)
        and b'installed-root-not-complete' in init and b'BOOTSTRAP_HANDOFF' in init
        and producer.boot_identity(artifact['run_id']).encode() in init
        and all(name not in init for name in (b'/rootfs.tar.xz',b'/install.meta',b'/install.sha256',
            b'DEBIAN_INSTALL_INTENT_DURABLE',b'DEBIAN_INSTALL_COMPLETE')),
        'P404 installed-only init or RAM command differs')
    require(script == producer.shutdown_overlay_bytes(),
            'RAM shutdown command differs from its fixed producer')
    with transport.pin_boot_only_ap(Path(artifact['ap']['path']),label='P404 H0 AP',
            expected_size=artifact['ap']['size'],expected_sha256=artifact['ap']['sha256']) as ap:
        member = transport.read_boot_only_member(ap,label='P404 H0 AP')
    require(boot.decompress_lz4_stream_python(member,maximum=MAXIMUM)==image,
        'P404 AP boot member differs')
    result = read(vm_path)
    require(result['schema'] == 's22plus-debian-installed-boot-vm-h0-v1' and
        result['verdict'] == 'PASS_H0_ARM64_INSTALLED_BOOT_AND_EMPTY_REJECTION'
        and result['device_actions'] == 0 and result['scope'] == 'VIRT_NOT_SAMSUNG',
        'P404 ARM64 virtual workload and empty-root rejection are absent')
    positive = read(verify(result['positive']))
    require(positive['status']=='PASS_INSTALLED_PID1_H0' and positive['no_install'] is True and
        positive['return_status']=='SHUTDOWN_COMPLETED' and
        positive['candidate_identity']==producer.boot_identity(positive['candidate_run_id']) and
        positive['shutdown_overlay']['sha256']==artifact['shutdown_overlay']['sha256'],
        'virtual installed root or shutdown does not join physical command bytes')
    output.mkdir(mode=0o700)
    snapshots=[]
    for receipt in artifact['source_inputs']:
        path=verify(receipt,maximum=4*1024*1024)
        saved=output/'source'/path.relative_to(ROOT)
        saved.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        saved.write_bytes(path.read_bytes())
        saved.chmod(0o400)
        snapshots.append(dict(original=receipt,saved=pin(saved)))
    return publish(output/'qualification.json',dict(schema=SCHEMA,
        verdict='PASS_H0_INSTALLED_BOOT_ARTIFACT_AND_ARM64_VM',
        artifact=artifact_receipt,vm=pin(vm_path),p401=producer.ARTIFACT,
        p403=producer.TERMINAL,p399_ap=producer.P399_AP,
        source_snapshot=snapshots,boot=artifact['boot'],ap=artifact['ap'],
        init=artifact['init'],ram_command=artifact['shutdown_overlay'],
        boot_sha256=digest(image),shutdown_command_sha256=digest(script),
        device_actions=0,grants_device_authority=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--artifact',type=Path,required=True)
    parser.add_argument('--vm',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(qualify(args.artifact,args.vm,args.output))
