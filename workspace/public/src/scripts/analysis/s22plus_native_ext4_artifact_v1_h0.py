"""Export joined filesystem A/B artifacts and the retained Android32 return basis."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
import s22plus_native_ext4_profile_v1 as profile
import s22plus_native_ext4_h0 as producer
import s22plus_boot_only_f1_transport as transport
from s22plus_native_records_v3 import pin, private_path, publish, read, require, verify

RETURN_TERMINAL = ROOT / ('workspace/private/runs/s22plus-native-session-v3/'
    'p398-native-android32-20260916-1/operation-0002/terminal.json')


def qualify(namespace, output, *, key_path, build_directory=None):
    import s22plus_native_baseline_v2_candidates as catalog
    from s22plus_native_adapter_v3 import Adapter
    from s22plus_native_session_v3 import operation_steps
    selected = catalog.DECLARATIONS[namespace]
    role = catalog.research_profile(selected)
    require(role in profile.PROFILES, 'runtime is outside fixed filesystem scope')
    builder = catalog.static(namespace).builder
    if build_directory is not None: builder.DEFAULT_OUTPUT_ROOT = private_path(ROOT, build_directory)
    built = builder.audit_existing()
    require(built['byte_identical'] is True and built['candidate']['a'] == built['candidate']['b'],
            'filesystem A/B artifacts differ')
    binding = read(verify(built['filesystem']['binding']))
    producer.seal(built['filesystem']['binding'], selected.IDENTITY.run_id_hex,
                  initialize=role == profile.INITIALIZER_PROFILE)
    layout = read(verify(binding['layout_proposal']))
    sealed = dict(proposal=binding['layout_proposal'], regions=layout['regions'], layout=layout['layout'])
    terminal = read(RETURN_TERMINAL); original = read(verify(terminal['operation_record']))
    adapter = Adapter(ROOT, RETURN_TERMINAL.parent)
    final = read(verify(terminal['terminal_result']))
    adapter.validate_result(operation_steps(original)[-1], final, original)
    require(terminal['terminal_state'] == 'ANDROID_CLOSED_HEALTHY' and
            terminal['gpt']['status'] == 'RESERVED_ANDROID_REBOOT_VERIFIED' and
            original['N']['gpt'] == sealed and final['gpt_android']['metadata']['layout'] == 'proposed',
            'filesystem return basis is not the closed initialized Android32 layout')
    return_basis = dict(source_terminal=pin(RETURN_TERMINAL), target=adapter.configuration(original)['target'],
                        A=original['A'], layout='proposed', geometry=terminal['gpt']['geometry'],
                        total_bytes=final['gpt_android']['storage']['total_bytes'])
    key = pin(private_path(ROOT, key_path), maximum=32)
    require({k:key[k] for k in ('size','sha256')} == selected.artifact.auth_key_identity(),
            'filesystem key differs from its producer')
    ap = dict(path=str(builder.DEFAULT_OUTPUT_ROOT / 'candidate-a/odin4/AP.tar.md5'),
              **built['candidate']['a']['ap_tar_md5'])
    with transport.pin_boot_only_ap(Path(ap['path']), label='filesystem qualification',
            expected_size=ap['size'], expected_sha256=ap['sha256']) as bound:
        member = transport.boot_only_member_receipt(bound, label='filesystem qualification')
    output = private_path(ROOT, output, exists=False)
    require(not output.exists(), 'filesystem qualification already exists'); output.mkdir(mode=0o700)
    image = dict(schema='s22plus-native-image-v3', namespace=namespace, run_id_hex=selected.IDENTITY.run_id_hex,
                 profile=role, version=selected.IDENTITY.display_version, ap=ap, member=member, key=key,
                 runtime_sources=built['source_inputs'], filesystem=built['filesystem'],
                 gpt=sealed, android_return=return_basis)
    qualification = publish(output / 'qualification.json', dict(schema='s22plus-native-artifact-qualification-v3',
        image=image, builder_result=pin(builder.DEFAULT_OUTPUT_ROOT / 'result.json'),
        ab_identical=True, actual_ap_join=True, exporter=pin(Path(__file__))))
    return publish(output / 'image.json', dict(image, qualification=qualification))
