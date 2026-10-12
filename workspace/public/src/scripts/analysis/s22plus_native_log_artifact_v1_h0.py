"""Qualify actual A/B native calibration bytes and their real ARM64 VM proof."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_native_log_profile_v1 as profile
import s22plus_native_root_inspect_profile_v1 as retained
import s22plus_boot_only_f1_transport as transport
from s22plus_native_records_v3 import pin,private_path,publish,read,require,verify


def qualify(namespace,output,*,key_path,vm_result,build_directory=None):
    import s22plus_native_baseline_v2_candidates as catalog
    import s22plus_debian_first_boot_v1 as prior_owner
    selected=catalog.DECLARATIONS[namespace]
    require(catalog.research_profile(selected)==profile.PROFILE,'unselected native calibration composition')
    builder=catalog.static(namespace).builder
    if build_directory is not None:builder.DEFAULT_OUTPUT_ROOT=private_path(ROOT,build_directory)
    built=builder.audit_existing()
    require(built['byte_identical'] is True and built['candidate']['a']==built['candidate']['b'],'calibration actual A/B differs')
    _,terminal,plan=retained.prior_inputs();final=verify(terminal['final_health'])
    require(read(final)==prior_owner.android_projection(final.parent,plan),'retained Android32 return does not rederive')
    key=pin(private_path(ROOT,key_path),maximum=32)
    require({k:key[k] for k in ('size','sha256')}==selected.artifact.auth_key_identity(),'calibration native key differs')
    vm=pin(private_path(ROOT,vm_result));profile.vm_results(vm,built['log_calibration'],selected.IDENTITY.run_id_hex,key)
    ap=dict(path=str(builder.DEFAULT_OUTPUT_ROOT/'candidate-a/odin4/AP.tar.md5'),**built['candidate']['a']['ap_tar_md5'])
    with transport.pin_boot_only_ap(Path(ap['path']),label='native log qualification',
            expected_size=ap['size'],expected_sha256=ap['sha256']) as bound:
        member=transport.boot_only_member_receipt(bound,label='native log qualification')
    basis=dict(source_terminal=retained.TERMINAL,target=plan['target'],A=plan['A'],layout='proposed',
        geometry=plan['basis']['geometry'],total_bytes=34357624832)
    image=dict(schema='s22plus-native-image-v3',namespace=namespace,run_id_hex=selected.IDENTITY.run_id_hex,
        profile=profile.PROFILE,version=selected.IDENTITY.display_version,ap=ap,member=member,key=key,
        runtime_sources=built['source_inputs'],gpt=plan['basis']['gpt'],android_return=basis,
        log_calibration=built['log_calibration'])
    output=private_path(ROOT,output,exists=False);require(not output.exists(),'fresh log qualification required')
    output.mkdir(mode=0o700)
    import s22plus_fyg8_p319_stock_candidate_build as linkage
    kernel=builder.DEFAULT_OUTPUT_ROOT/'inputs/fixed-Image'
    kernel_pin=pin(kernel,maximum=128*1024**2)
    providers=linkage._image_provider_map(verify(kernel_pin,maximum=128*1024**2).read_bytes(),linkage.IMAGE_SECTION_LAYOUT)
    imports=subprocess.check_output(['modprobe','--dump-modversions',verify(built['log_calibration']['module'])])
    (output/'logger-imports.txt').write_bytes(imports)
    required={symbol:linkage._norm_crc(crc) for crc,symbol in (line.split() for line in imports.decode().splitlines())}
    require(len(required)==71 and all(providers.get(symbol)==crc for symbol,crc in required.items()),
        'stock logger imports do not match the actual candidate kernel')
    abi=dict(kernel=kernel_pin,module=built['log_calibration']['module'],imports=pin(output/'logger-imports.txt'),
        providers={symbol:providers[symbol] for symbol in sorted(required)},matched=True)
    qualification=publish(output/'qualification.json',dict(schema='s22plus-native-artifact-qualification-v3',
        image=image,builder_result=pin(builder.DEFAULT_OUTPUT_ROOT/'result.json'),ab_identical=True,
        actual_ap_join=True,exporter=pin(Path(__file__)),vm=vm,logger_abi=abi))
    image=dict(image,qualification=qualification);profile.image_binding(image)
    return publish(output/'image.json',image)
