"""Resident artifact and ordinary-owner H0 review bundle; no live preparation."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[5]
REVALIDATION=ROOT/'workspace/public/src/scripts/revalidation'
sys.path[:0]=[str(REVALIDATION),str(Path(__file__).parent)]
import device_action_f1_evidence_v2 as evidence
import s22plus_fyg8_p386_candidate as declaration
import s22plus_fyg8_p386_stock_candidate_build as builder
from s22plus_native_candidate_static_v1 import CandidateStatic

artifact,adapter,observer=declaration.artifact,declaration.adapter,declaration.observer
StaticContractError=ValueError

# Explicit roots include the codec's dynamically loaded reader chain.
_modules=(
    's22plus_native_console_observer_v1','s22plus_native_console_owner_v1',
    's22plus_native_candidate_artifacts_v1','s22plus_native_carrier_adapter_v1',
    's22plus_local_display_observer_v1','s22plus_native_baseline_health_v1','s22plus_root_console_v1',
    's22plus_fyg8_p363_return_spec','s22plus_fyg8_p320_stock_process_v2_adapter',
    's22plus_fyg8_p336_long_idle_acm_observer','s22plus_fyg8_p335_retained_listener_acm_observer',
    's22plus_fyg8_p334_first_read_rc_acm_observer','s22plus_fyg8_p333_open_entry_diag_acm_observer',
    's22plus_fyg8_p332_logical_resident_acm_observer','s22plus_fyg8_p330_auth_acm_observer',
    's22plus_fyg8_p329_auth_acm_observer','s22plus_fyg8_p328_auth_acm_observer',
    'device_action_f1_v2','device_action_f1_live_v2','device_action_f1_evidence_v2',
    's22plus_native_resident_backend_v1','s22plus_native_resident_observer_v1',
    's22plus_native_resident_protocol_v1','s22plus_native_baseline_protocol_v1',
    's22plus_native_candidate_definition_v1','s22plus_fyg8_p363_return_host',
    's22plus_native_usb_departure_v1','s22plus_odin_transition_core','s22plus_odin_usbfs_identity',
    'device_action_raw_capture_v1','s22plus_fyg8_p313_guard_lifetime')
_extra=['workspace/public/src/scripts/revalidation/'+name+'.py' for name in _modules]
_extra+=['docs/operations/S22PLUS_NATIVE_RESIDENT_ADOPTION_V1.md',
    'docs/operations/S22PLUS_NATIVE_RESIDENT_H0_V1.md',
    'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md']
_static=CandidateStatic(declaration,builder,__file__,extra_sources=_extra)
SOURCE_FILES=_static.SOURCE_FILES
SCHEMA,VERDICT,RUN_SCHEMA=_static.SCHEMA,_static.VERDICT,_static.RUN_SCHEMA
CHECK_SCHEMA,CHECK_VERDICT=_static.CHECK_SCHEMA,_static.CHECK_VERDICT
RUN_ID,TARGET,DEFAULT_OUTPUT=_static.RUN_ID,_static.TARGET,_static.DEFAULT_OUTPUT
ROLLBACK_AP,ROLLBACK_IDENTITY=_static.ROLLBACK_AP,_static.ROLLBACK_IDENTITY
canonical,receipt,source_receipts=_static.canonical,_static.receipt,_static.source_receipts
build_result,validate_result=_static.build_result,_static.validate_result
validate_bound_result=validate_result
promotion_payloads=_static.promotion_payloads


def prepare_h0(output):
    import device_action_f1_v2 as core
    import device_action_f1_live_v2 as live
    output=Path(output).absolute()
    if output.exists() or output.is_symlink() or not output.resolve().is_relative_to((ROOT/'workspace/private').resolve()):
        raise ValueError('fresh private resident H0 bundle required')
    value=build_result();output.mkdir(mode=0o700,parents=True)
    builder.write(output/'candidate-static.json',canonical(value));static_pin=receipt(output/'candidate-static.json')
    run,check=promotion_payloads(value,static_pin,run_id='s22plus-fyg8-p386-h0-review')
    for name,body in (('run-manifest.json',run),('static-check-result.json',check)):builder.write(output/name,canonical(body))
    acceptance=adapter.acceptance_fixture()
    acceptance['contract']={name:receipt(output/file) for name,file in (
        ('candidate_static','candidate-static.json'),('run_manifest','run-manifest.json'),('static_check','static-check-result.json'))}
    manifest=dict(schema=core.MANIFEST_SCHEMA,manifest_id='s22plus-fyg8-p386-h0-review',run_id='s22plus-fyg8-p386-live-review',
        status='draft-host-only',target_profile='workspace/public/src/device-action/profiles/s22plus_fyg8.json',
        candidate_ap=receipt(builder.DEFAULT_OUTPUT_ROOT/'candidate-a/odin4/AP.tar.md5'),rollback_ap=receipt(ROLLBACK_AP),
        allowed_member='boot.img.lz4',observation=dict(timeout_sec=observer.QUALIFICATION_TIMEOUT_SEC,acceptance=acceptance,
            candidate_observer=evidence._shell_observer_spec('p386'),
            **{evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY:evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE}),
        final_health_profile='s22plus-fyg8-magisk',runner_version=core.RUNNER_VERSION)
    path=output/'review-manifest.json';builder.write(path,canonical(manifest))
    bundle=core.verify_bundle(ROOT,path);closure=live._closure(ROOT,bundle)
    if live.native_roundtrip.selected(bundle) or live._shell_definition(bundle).native_baseline:
        raise ValueError('resident candidate selected a native-restoration exception')
    if source_receipts()!=value['source_closure']:raise ValueError('resident H0 sources changed')
    builder.write(output/'execution-closure.json',canonical(closure))
    result=dict(schema='s22plus-fyg8-p386-review-bundle-v1',verdict='PASS_P386_REVIEW_BUNDLE_H0',
        manifest=receipt(path),candidate_ap=value['candidate']['a']['ap_tar_md5'],execution_closure=receipt(output/'execution-closure.json'),
        source_inputs=value['source_closure'],guard_derivation=live.native_resident.guard_derivation(live,bundle),
        ordinary_roles=['candidate','rollback'],device_contact=False,live_authorized=False,public_ready_created=False)
    builder.write(output/'result.json',canonical(result));return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=prepare_h0(args.out)
    print(json.dumps(dict(verdict=result['verdict'],manifest=result['manifest']),sort_keys=True))
