"""P385 static declaration; source-qualified H0 preparation only."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path[:0] = [str(ROOT/'workspace/public/src/scripts/revalidation'), str(Path(__file__).parent)]
import s22plus_fyg8_p385_candidate as declaration
import s22plus_fyg8_p385_stock_candidate_build as builder
from s22plus_native_candidate_static_v1 import CandidateStatic

_modules = ('device_action_f1_v2', 'device_action_f1_live_v2', 'device_action_f1_evidence_v2',
    'device_action_d0_v2', 'device_action_raw_capture_v1', 'consumed_candidate_registry_v1',
    's22plus_boot_only_f1_transport',
    's22plus_native_baseline_owner_v1', 's22plus_native_baseline_backend_v1',
    's22plus_native_baseline_guard_v1', 'device_action_cdc_acm_observer_v1',
    's22plus_fyg8_p324_cdc_acm_observer',
    's22plus_native_baseline_protocol_v1', 's22plus_native_baseline_observer_v1',
    's22plus_native_console_observer_v1', 's22plus_native_console_owner_v1',
    's22plus_native_candidate_artifacts_v1', 's22plus_native_carrier_adapter_v1',
    's22plus_native_baseline_health_v1', 's22plus_local_display_observer_v1', 's22plus_root_console_v1',
    's22plus_fyg8_p363_return_host', 's22plus_fyg8_p336_long_idle_acm_observer',
    's22plus_fyg8_p335_retained_listener_acm_observer', 's22plus_fyg8_p334_first_read_rc_acm_observer',
    's22plus_fyg8_p333_open_entry_diag_acm_observer', 's22plus_fyg8_p332_logical_resident_acm_observer',
    's22plus_fyg8_p330_auth_acm_observer', 's22plus_fyg8_p329_auth_acm_observer', 's22plus_fyg8_p328_auth_acm_observer',
    's22plus_fyg8_p363_return_spec', 's22plus_native_usb_departure_v1', 's22plus_native_roundtrip_owner_v1',
    's22plus_odin_transition_core', 's22plus_odin_usbfs_identity', 's22plus_fyg8_p324_typec_lane_binding',
    's22plus_fyg8_p325_cdc_acm_guard_adapter', 's22plus_attended_f1_session_v1')
_extra = ['workspace/public/src/scripts/revalidation/'+name+'.py' for name in _modules]
_extra += ['AGENTS.md', 'docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md',
    'docs/operations/DEVICE_ACTION_PROCESS_V2.md', 'docs/operations/DEVICE_ACTION_RISK_TIERS.md',
    'docs/operations/S22PLUS_NATIVE_BASELINE_V1.md', 'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md',
    'workspace/public/src/device-action/profiles/s22plus_fyg8.json']
_static = CandidateStatic(declaration, builder, __file__, extra_sources=_extra)
SOURCE_FILES, SOURCE_CONTRACT_ID = _static.SOURCE_FILES, declaration.adapter.PARENT_SOURCE_CONTRACT_ID
SCHEMA, VERDICT, RUN_SCHEMA = _static.SCHEMA, _static.VERDICT, _static.RUN_SCHEMA
CHECK_SCHEMA, CHECK_VERDICT = _static.CHECK_SCHEMA, _static.CHECK_VERDICT
RUN_ID, TARGET, DEFAULT_OUTPUT = _static.RUN_ID, _static.TARGET, _static.DEFAULT_OUTPUT
ROLLBACK_AP, ROLLBACK_IDENTITY = _static.ROLLBACK_AP, _static.ROLLBACK_IDENTITY
StaticContractError = ValueError
source_receipts, build_result = _static.source_receipts, _static.build_result
validate_result = validate_bound_result = _static.validate_result
promotion_payloads, prepare_h0 = _static.promotion_payloads, _static.prepare_h0

if __name__ == '__main__':
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    result = prepare_h0(parser.parse_args().out)
    print(json.dumps(dict(verdict=result['verdict'], manifest=result['manifest']), sort_keys=True))
