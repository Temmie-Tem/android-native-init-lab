"""Export freshly audited native artifacts for V3; never imported by live I/O.

The existing A/B producer remains an H0 build tool. The exported descriptor
contains actual AP/member/key identities and immutable original provenance.
It neither creates a content claim nor admits N nor opens a task grant.
"""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
from s22plus_native_records_v3 import digest, pin, private_path, publish, read, require, verify
import s22plus_boot_only_f1_transport as transport


def qualify(namespace, output, *, key_path, build_directory=None):
    # H0-only compatibility with a retained producer. No legacy module crosses
    # into the live owner process or determines live authority.
    import s22plus_native_baseline_v2_candidates as catalog
    require(namespace in catalog.DECLARATIONS,'native build declaration is absent')
    selected=catalog.DECLARATIONS[namespace]
    require(catalog.research_profile(selected)=='thermal-v3-reconnect-v1','runtime profile is outside V3 scope')
    static=catalog.static(namespace); builder=static.builder
    if build_directory is not None: builder.DEFAULT_OUTPUT_ROOT=private_path(ROOT,build_directory)
    built=builder.audit_existing()
    require(built['verdict']=='PASS_NATIVE_THERMAL_BUILD_H0' and built['byte_identical'] is True
        and built['candidate']['a']==built['candidate']['b'],'native A/B producer did not qualify')
    key=pin(private_path(ROOT,key_path),maximum=32)
    require({name:key[name] for name in ('size','sha256')}==selected.artifact.auth_key_identity(),
        'native key does not match the audited producer')
    ap_path=builder.DEFAULT_OUTPUT_ROOT/'candidate-a/odin4/AP.tar.md5'
    ap=dict(path=str(ap_path),**built['candidate']['a']['ap_tar_md5'])
    with transport.pin_boot_only_ap(ap_path,label='V3 native qualification',expected_size=ap['size'],
            expected_sha256=ap['sha256']) as bound:
        member=transport.boot_only_member_receipt(bound,label='V3 native qualification')
    output=private_path(ROOT,output,exists=False); require(not output.exists(),'qualification output already exists')
    output.mkdir(mode=0o700)
    image=dict(schema='s22plus-native-image-v3',namespace=namespace,run_id_hex=selected.IDENTITY.run_id_hex,
        profile='thermal-v3-reconnect-v1',version=selected.IDENTITY.display_version,ap=ap,member=member,key=key,
        runtime_sources=built['source_inputs'])
    qualification=publish(output/'qualification.json',dict(schema='s22plus-native-artifact-qualification-v3',
        image=image,builder_result=pin(builder.DEFAULT_OUTPUT_ROOT/'result.json'),
        ab_identical=True,actual_ap_join=True,exporter=pin(Path(__file__))))
    return publish(output/'image.json',dict(image,qualification=qualification))


def export_recovery(terminal_path, output):
    """Read the closed V2 A result once, exporting no old live authority."""
    import s22plus_native_target_io_v3 as target
    import device_action_raw_capture_v1 as raw
    from s22plus_native_task_v3 import android_artifact
    terminal_path=private_path(ROOT,terminal_path); terminal=read(terminal_path)
    require(terminal['schema']=='s22plus-native-baseline-owner-v1' and terminal['state']=='ANDROID_CLOSED'
        and terminal['android_transferred'] is True and terminal['recovery_required'] is False,
        'historical recovery is not a closed Android return')
    operation=read(verify(terminal['operation'])); grant=read(verify(operation['grant']))
    request=read(verify(grant['request'])); android=android_artifact(ROOT)
    original=dict(android['ap'],member=android['member'])
    require(terminal['android']==request['android']==original and grant['attended'] is True,
        'historical attended Android recovery identity differs')
    health=read(verify(terminal['final_health']))
    completed=read(verify(health['completed_android']))
    path=Path(health['completed_android']['path']); prefix=completed['prefix']
    start_path=path.parent/(prefix+'.start.json'); start=read(start_path)
    delivery=read(path.parent/(prefix+'.delivery.json'))
    require(start['operation']==health['operation']==terminal['operation'] and start['artifact']==original
        and delivery['intent']==pin(start_path) and completed['classification']=='odin_transfer_completed'
        and completed['transport']['ap']==android['ap'],
        'historical recovery transfer is not joined to its original A intent')
    handle=raw.load_handle(verify(completed['transport']['raw_capture_receipt']))
    target.transfer_completed(handle)
    projected=target.health_projection(health['captures'],request['target'],android)
    return publish(private_path(ROOT,output,exists=False),dict(schema='s22plus-native-recovery-evidence-v3',
        target=request['target'],A=android,transfer=dict(ap=android['ap'],raw=pin(handle.receipt_path)),
        health=projected,source_terminal=pin(terminal_path),source_health=terminal['final_health'],
        source_transfer=health['completed_android'],exporter=pin(Path(__file__))))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('namespace'); parser.add_argument('output',type=Path)
    parser.add_argument('--key',type=Path,required=True); parser.add_argument('--build-directory',type=Path)
    args=parser.parse_args()
    receipt=qualify(args.namespace,args.output,key_path=args.key,build_directory=args.build_directory)
    print('PASS_V3_ARTIFACT_H0 image_sha256='+receipt['sha256'])


if __name__=='__main__': main()
