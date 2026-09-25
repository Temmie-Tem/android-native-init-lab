"""Join actual A/B inspector bytes to the consumed P401 comparison and return."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
import s22plus_native_root_inspect_profile_v1 as profile
import s22plus_boot_only_f1_transport as transport
from s22plus_native_records_v3 import pin, private_path, publish, read, require, verify


def qualify(namespace, output, *, key_path, build_directory=None, userspace=False, preflight=False):
    import s22plus_native_baseline_v2_candidates as catalog
    import s22plus_debian_first_boot_v1 as prior_owner
    selected = catalog.DECLARATIONS[namespace]
    chosen = profile
    require(not (userspace and preflight), 'select one diagnostic role')
    if userspace: import s22plus_native_userspace_probe_profile_v1 as chosen
    if preflight: import s22plus_native_preflight_profile_v1 as chosen
    require(catalog.research_profile(selected) == chosen.PROFILE, 'unselected protected-root composition')
    builder = catalog.static(namespace).builder
    if build_directory is not None: builder.DEFAULT_OUTPUT_ROOT = private_path(ROOT, build_directory)
    built = builder.audit_existing()
    require(built['byte_identical'] is True and built['candidate']['a'] == built['candidate']['b'],
        'inspector actual A/B bytes differ')
    _, terminal, plan = profile.prior_inputs()
    final = verify(terminal['final_health'])
    require(read(final) == prior_owner.android_projection(final.parent, plan),
        'retained P401 Android32 closure does not rederive from its raw evidence')
    if userspace:
        from s22plus_native_adapter_v3 import Adapter
        from s22plus_native_session_v3 import Session, Step
        _, recent, _ = chosen.prior_inputs()
        folder = Path(chosen.TERMINAL['path']).parent
        adapter = Adapter(ROOT, folder); retained = Session(ROOT, folder, adapter)
        retained.completed((Step('root-inspection', 'observe', 'N', 'detach'),))
        retained.completed((Step('install-android', 'transfer', 'A'), Step('recovery-health', 'health', 'A')))
        require(recent['operation_record'] == pin(folder / 'operation.json'), 'P402 operation receipt differs')
    key = pin(private_path(ROOT, key_path), maximum=32)
    require({k:key[k] for k in ('size', 'sha256')} == selected.artifact.auth_key_identity(),
        'inspector authentication key differs from its producer')
    ap = dict(path=str(builder.DEFAULT_OUTPUT_ROOT / 'candidate-a/odin4/AP.tar.md5'),
        **built['candidate']['a']['ap_tar_md5'])
    with transport.pin_boot_only_ap(Path(ap['path']), label='root inspection qualification',
            expected_size=ap['size'], expected_sha256=ap['sha256']) as bound:
        member = transport.boot_only_member_receipt(bound, label='root inspection qualification')
    basis = dict(source_terminal=profile.TERMINAL, target=plan['target'], A=plan['A'], layout='proposed',
        geometry=plan['basis']['geometry'], total_bytes=34357624832)
    image = dict(schema='s22plus-native-image-v3', namespace=namespace, run_id_hex=selected.IDENTITY.run_id_hex,
        profile=chosen.PROFILE, version=selected.IDENTITY.display_version, ap=ap, member=member, key=key,
        runtime_sources=built['source_inputs'],
        gpt=plan['basis']['gpt'], android_return=basis)
    if preflight:image['preflight']=built['preflight']
    else:image['root_inspection']=built['root_inspection']
    if userspace: image['userspace_probe'] = built['userspace_probe']
    chosen.image_binding(image)
    output = private_path(ROOT, output, exists=False)
    require(not output.exists(), 'inspector qualification output already exists'); output.mkdir(mode=0o700)
    qualification = publish(output / 'qualification.json', dict(schema='s22plus-native-artifact-qualification-v3',
        image=image, builder_result=pin(builder.DEFAULT_OUTPUT_ROOT / 'result.json'),
        ab_identical=True, actual_ap_join=True, exporter=pin(Path(__file__).with_name(
            's22plus_native_preflight_artifact_v1_h0.py') if preflight else Path(__file__).with_name(
            's22plus_native_userspace_probe_artifact_v1_h0.py') if userspace else Path(__file__))))
    return publish(output / 'image.json', dict(image, qualification=qualification))
