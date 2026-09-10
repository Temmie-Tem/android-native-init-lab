"""P384 direct artifact/static/promotion binding; no device actions."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = ROOT/'workspace/public/src/scripts/revalidation'
sys.path[:0] = [str(REVALIDATION), str(Path(__file__).parent)]
import device_action_f1_evidence_v2 as evidence
import s22plus_fyg8_p384_candidate as declaration
import s22plus_fyg8_p384_stock_candidate_build as builder
import s22plus_native_source_v1 as direct

artifact, adapter, observer = declaration.artifact, declaration.adapter, declaration.observer
SCHEMA = 's22plus_fyg8_p384_process_v2_candidate_static_v1'
VERDICT = 'PASS_P384_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY'
RUN_SCHEMA = 's22plus_fyg8_p384_process_v2_run_manifest_v1'
CHECK_SCHEMA = 's22plus_fyg8_p384_process_v2_static_result_v1'
CHECK_VERDICT = 'PASS_P384_PROCESS_V2_STATIC_RESULT_HOST_ONLY'
RUN_ID = declaration.IDENTITY.run_id_hex
TARGET = dict(builder.TARGET)
DEFAULT_OUTPUT = ROOT/'workspace/private/outputs/s22plus_fyg8_p384/candidate-static-v1.json'
ROLLBACK_AP = ROOT/'workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5'
ROLLBACK_IDENTITY = dict(size=23367721, sha256='d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56')
StaticContractError = ValueError

# Explicit reachable roots also cover dynamic source readers that AST imports
# miss. Codec runtime imports are replaced by this declaration before use.
_names = ('s22plus_fyg8_p384_candidate', 's22plus_native_console_observer_v1',
    's22plus_native_console_owner_v1', 's22plus_native_candidate_artifacts_v1',
    's22plus_native_carrier_adapter_v1', 's22plus_local_display_observer_v1',
    's22plus_native_baseline_health_v1', 's22plus_root_console_v1',
    's22plus_fyg8_p363_return_spec', 's22plus_fyg8_p320_stock_process_v2_adapter',
    's22plus_fyg8_p336_long_idle_acm_observer', 's22plus_fyg8_p335_retained_listener_acm_observer',
    's22plus_fyg8_p334_first_read_rc_acm_observer', 's22plus_fyg8_p333_open_entry_diag_acm_observer',
    's22plus_fyg8_p332_logical_resident_acm_observer', 's22plus_fyg8_p330_auth_acm_observer',
    's22plus_fyg8_p329_auth_acm_observer', 's22plus_fyg8_p328_auth_acm_observer')
_paths = {REVALIDATION/(name+'.py') for name in _names}
_paths.update(ROOT/name for name in builder.source_receipts())
_paths.update(ROOT/path for path in adapter.SOURCE_PATHS.values())
_paths.update({Path(__file__), Path(builder.__file__),
    REVALIDATION/'device_action_f1_v2.py', REVALIDATION/'device_action_f1_live_v2.py',
    REVALIDATION/'device_action_f1_evidence_v2.py', REVALIDATION/'s22plus_fyg8_p363_return_host.py',
    REVALIDATION/'s22plus_native_usb_departure_v1.py', REVALIDATION/'s22plus_odin_transition_core.py',
    REVALIDATION/'s22plus_odin_usbfs_identity.py', REVALIDATION/'device_action_raw_capture_v1.py',
    REVALIDATION/'s22plus_native_roundtrip_owner_v1.py',
    ROOT/'docs/operations/S22PLUS_NATIVE_ROUNDTRIP_FOLLOWUP_V2.md',
    ROOT/'docs/operations/S22PLUS_FYG8_LOCAL_DISPLAY_ADOPTION_V1.md',
    ROOT/'docs/operations/S22PLUS_FYG8_LOCAL_DISPLAY_LIFECYCLE_V1.md',
    ROOT/'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md'})
SOURCE_FILES = {'p384_source_'+hashlib.sha256(str(path.relative_to(ROOT)).encode()).hexdigest()[:16]: path
                for path in sorted(_paths)}


def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
def identity(raw): return dict(size=len(raw), sha256=hashlib.sha256(raw).hexdigest())
def receipt(path): return dict(path=str(path.relative_to(ROOT)), **identity(artifact.stable_bytes(path)))


def source_receipts():
    return {name: receipt(path) for name, path in SOURCE_FILES.items()}


def build_result():
    built = builder.audit_existing(); inventory = built['candidate']['a']['inventory']
    assets = {name: pin for name, pin in inventory.items() if name == 's22-display' or name == 's22-display-modules'
              or name.startswith('s22-display-modules/')}
    artifact.validate_rollback_ap(ROLLBACK_AP, ROLLBACK_IDENTITY)
    candidate = dict(a=built['candidate']['a'], b=built['candidate']['b'], image=built['image'], init=built['init'],
        child=built['child'], busybox={k: inventory['bin/busybox'][k] for k in ('size', 'sha256')},
        display_assets=assets, boot_only=True, byte_identical=True)
    return dict(schema=SCHEMA, verdict=VERDICT, target=TARGET, run_id=RUN_ID,
        predecessor_run_id=builder.REFERENCE_IDENTITY.run_id_hex, source_contract_id=adapter.PARENT_SOURCE_CONTRACT_ID,
        userspace_overlay_contract_id=adapter.OVERLAY_CONTRACT_ID, profile=adapter.PROFILE,
        authority_source=receipt(Path(__file__)), builder_result=receipt(builder.DEFAULT_OUTPUT_ROOT/'result.json'),
        candidate=candidate, source_closure=source_receipts(), rollback_ap=dict(path=str(ROLLBACK_AP.relative_to(ROOT)), **ROLLBACK_IDENTITY),
        auth_key=artifact.auth_key_identity(), adapter=adapter.audit(), qualification=adapter.acceptance_fixture()['qualification_commands'],
        observer_binding=observer.audit_binding(), safety=dict(host_only=True, device_contact=False, live_authorized=False,
            later_action_lease_active=False, mandatory_rollback=True))


def validate_result(value):
    if canonical(value) != canonical(build_result()): raise ValueError('native static binding does not regenerate')
    return value


validate_bound_result = validate_result


def promotion_payloads(static, static_receipt, *, run_id):
    common = dict(run_id=RUN_ID, target=TARGET, source_contract_id=adapter.PARENT_SOURCE_CONTRACT_ID,
        userspace_overlay_contract_id=adapter.OVERLAY_CONTRACT_ID, decoder=adapter.DECODER_ID, policy_id=adapter.POLICY_ID,
        profile=adapter.PROFILE, candidate_static=dict(static_receipt), candidate_ap=static['candidate']['a']['ap_tar_md5'],
        qualification=static['qualification'], host_only=True, device_contact=False, live_authorized=False,
        later_action_lease_active=False, mandatory_rollback=True)
    return (dict(common, schema=RUN_SCHEMA, promotion_run_id=run_id),
            dict(common, schema=CHECK_SCHEMA, verdict=CHECK_VERDICT, promotion_run_id=run_id))


def prepare_h0(output, *, roundtrip_followup=False):
    """Publish a fresh private review bundle and run the actual bundle reader.

    This does not prepare a live run, grant attendance or install a public READY
    manifest. Future activation still has the existing exact source checks.
    """
    import device_action_f1_v2 as core
    import device_action_f1_live_v2 as live
    import s22plus_native_roundtrip_owner_v1 as roundtrip
    output = Path(output).absolute()
    if output.exists() or output.is_symlink() or not output.resolve().is_relative_to((ROOT/'workspace/private').resolve()):
        raise ValueError('fresh private H0 bundle output required')
    value = build_result(); output.mkdir(mode=0o700, parents=True)
    builder.write(output/'candidate-static.json', canonical(value))
    static_pin = receipt(output/'candidate-static.json')
    run, check = promotion_payloads(value, static_pin, run_id='s22plus-fyg8-p384-h0-review')
    for name, body in (('run-manifest.json', run), ('static-check-result.json', check)):
        builder.write(output/name, canonical(body))
    acceptance = adapter.acceptance_fixture()
    acceptance['contract'] = {name: receipt(output/file) for name, file in (
        ('candidate_static', 'candidate-static.json'), ('run_manifest', 'run-manifest.json'),
        ('static_check', 'static-check-result.json'))}
    manifest = dict(schema=core.MANIFEST_SCHEMA, manifest_id='s22plus-fyg8-p384-h0-review',
        run_id='s22plus-fyg8-p384-live-review', status='ready-for-f1-approval',
        target_profile='workspace/public/src/device-action/profiles/s22plus_fyg8.json',
        candidate_ap=receipt(builder.DEFAULT_OUTPUT_ROOT/'candidate-a/odin4/AP.tar.md5'),
        rollback_ap=receipt(ROLLBACK_AP), allowed_member='boot.img.lz4',
        observation=dict(timeout_sec=60, acceptance=acceptance,
            candidate_observer=evidence._shell_observer_spec('p384'),
            **{evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY: evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE}),
        final_health_profile='s22plus-fyg8-magisk', runner_version=core.RUNNER_VERSION)
    if roundtrip_followup:
        manifest['manifest_id'] = roundtrip.FOLLOWUP_MANIFEST
        manifest['run_id'] = 's22plus-fyg8-p384-native-roundtrip-v2-live-1'
    path = output/'review-manifest.json'; builder.write(path, canonical(manifest))
    bundle = core.verify_bundle(ROOT, path)
    roles = roundtrip.prepare_plan(bundle) if roundtrip.selected(bundle) else None
    if roundtrip_followup != (roles is not None): raise ValueError('H0 roundtrip selection differs')
    closure = live._closure(ROOT, bundle)
    if source_receipts() != value['source_closure']: raise ValueError('H0 execution sources changed during verification')
    builder.write(output/'execution-closure.json', canonical(closure))
    result = dict(schema='s22plus-fyg8-p384-review-bundle-v1', verdict='PASS_P384_REVIEW_BUNDLE_H0',
        manifest=receipt(path), candidate_ap=value['candidate']['a']['ap_tar_md5'],
        execution_closure=receipt(output/'execution-closure.json'),
        source_inputs=value['source_closure'], device_contact=False, live_authorized=False,
        native_roundtrip_exception=roles is not None, native_roundtrip_plan=roles)
    builder.write(output/'result.json', canonical(result))
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--roundtrip-followup', action='store_true')
    args = parser.parse_args()
    result = prepare_h0(args.out, roundtrip_followup=args.roundtrip_followup)
    print(json.dumps(dict(verdict=result['verdict'], manifest=result['manifest']), sort_keys=True))
