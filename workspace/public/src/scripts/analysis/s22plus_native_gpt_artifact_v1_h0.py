"""Export exact GPT A/B image and private proposal bindings; no device effects."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
from s22plus_native_records_v3 import pin, private_path, publish, require
import s22plus_boot_only_f1_transport as transport
import s22plus_native_gpt_profile_v1 as gpt


def qualify(namespace,output,*,key_path,build_directory=None):
    import s22plus_native_baseline_v2_candidates as catalog
    require(namespace in catalog.DECLARATIONS,'GPT build declaration is absent')
    selected=catalog.DECLARATIONS[namespace]
    require(catalog.research_profile(selected)==gpt.PROFILE,'runtime is outside GPT scope')
    builder=catalog.static(namespace).builder
    if build_directory is not None:builder.DEFAULT_OUTPUT_ROOT=private_path(ROOT,build_directory)
    built=builder.audit_existing()
    require(built['verdict']=='PASS_NATIVE_THERMAL_BUILD_H0' and built['byte_identical'] is True
        and built['candidate']['a']==built['candidate']['b'],'GPT A/B producer did not qualify')
    key=pin(private_path(ROOT,key_path),maximum=32)
    require({k:key[k] for k in ('size','sha256')}==selected.artifact.auth_key_identity(),
        'GPT key does not match the audited producer')
    gpt.vectors(built['gpt'])
    ap=dict(path=str(builder.DEFAULT_OUTPUT_ROOT/'candidate-a/odin4/AP.tar.md5'),
        **built['candidate']['a']['ap_tar_md5'])
    with transport.pin_boot_only_ap(Path(ap['path']),label='GPT qualification',
            expected_size=ap['size'],expected_sha256=ap['sha256']) as bound:
        member=transport.boot_only_member_receipt(bound,label='GPT qualification')
    output=private_path(ROOT,output,exists=False);require(not output.exists(),'GPT qualification already exists')
    output.mkdir(mode=0o700)
    image=dict(schema='s22plus-native-image-v3',namespace=namespace,run_id_hex=selected.IDENTITY.run_id_hex,
        profile=gpt.PROFILE,version=selected.IDENTITY.display_version,ap=ap,member=member,key=key,
        runtime_sources=built['source_inputs'],gpt=built['gpt'])
    qualification=publish(output/'qualification.json',dict(schema='s22plus-native-artifact-qualification-v3',
        image=image,builder_result=pin(builder.DEFAULT_OUTPUT_ROOT/'result.json'),
        ab_identical=True,actual_ap_join=True,exporter=pin(Path(__file__))))
    return publish(output/'image.json',dict(image,qualification=qualification))
