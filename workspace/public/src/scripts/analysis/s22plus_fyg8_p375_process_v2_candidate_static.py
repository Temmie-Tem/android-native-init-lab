#!/usr/bin/env python3
"""P375 complete root-console candidate/static closure; H0 only."""
from pathlib import Path
import ast
import hashlib

TEMPLATE_SOURCE=Path(__file__).with_name('s22plus_fyg8_p345_process_v2_candidate_static.py')
TEMPLATE_IDENTITY={'size':8107,'sha256':'4537f63080f1397c2775da0557f3c2622d103fc2b284144d2a3df1623efbb3e0'}
_source=TEMPLATE_SOURCE.read_bytes()
if {'size':len(_source),'sha256':hashlib.sha256(_source).hexdigest()}!=TEMPLATE_IDENTITY:
    raise ValueError('P375 static template identity differs')
_source=_source.replace(b'P345',b'P375').replace(b'p345',b'p375')
_tree=ast.parse(_source)
_tree.body=[node for node in _tree.body
    if not (isinstance(node,ast.FunctionDef) and node.name=='build_result')
    and not (isinstance(node,ast.If) and '__name__' in ast.unparse(node.test))]
exec(compile(ast.fix_missing_locations(_tree),str(TEMPLATE_SOURCE)+'#p375','exec'),globals())

import s22plus_fyg8_p375_stock_candidate_build as candidate_build
import s22plus_fyg8_p375_console_owner as console_owner
import s22plus_fyg8_p375_research_shell_runtime as runtime

SOURCE_FILES.pop('p375_readonly_child')
SOURCE_FILES.pop('p375_readonly_child_c')
SOURCE_FILES.update({
    'p375_static_template':TEMPLATE_SOURCE,
    'p375_candidate_builder':Path(candidate_build.__file__),
    'p375_preparation':Path(__file__).with_name('prepare_s22plus_fyg8_p375_process_v2.py'),
    'p375_root_console_native':runtime.ROOT_CONSOLE_SOURCE,
    'p375_root_console_host':REVALIDATION/'s22plus_root_console_v1.py',
    'p375_root_console_owner':Path(console_owner.__file__),
    'p375_progress':REVALIDATION/'s22plus_fyg8_p375_progress.py',
    'p375_return_intent':REVALIDATION/'s22plus_fyg8_p375_return_host.py',
    'p375_return_spec':REVALIDATION/'s22plus_fyg8_p375_return_spec.py',
    'p375_live_owner':REVALIDATION/'device_action_f1_live_v2.py',
    'p375_typed_evidence':REVALIDATION/'device_action_f1_evidence_v2.py',
    'p375_native_usb_departure':REVALIDATION/'s22plus_native_usb_departure_v1.py',
    'p375_final_target_health':REVALIDATION/'s22plus_final_target_health_v1.py',
    'p375_target_contract':ROOT/'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md',
    'p375_capability_contract':ROOT/'docs/operations/S22PLUS_FYG8_ROOT_CONSOLE_V1.md',
})


def build_result():
    built=candidate_build.audit_existing()
    inventory=built['candidate']['a']['inventory']
    assets={name:value for name,value in inventory.items()
        if name=='s22-display' or name=='s22-display-modules'
        or name.startswith('s22-display-modules/')}
    candidate={'a':built['candidate']['a'],'b':built['candidate']['b'],
        'image':built['image'],'init':built['init'],'child':built['child'],
        'busybox':{key:inventory['bin/busybox'][key] for key in ('size','sha256')},
        'display_assets':assets,'boot_only':True,'byte_identical':True,
        'root_console':True,'fixed_display_once_child':False}
    artifact.validate_rollback_ap(ROLLBACK_AP,ROLLBACK_IDENTITY)
    return {'schema':SCHEMA,'verdict':VERDICT,'target':TARGET,'run_id':RUN_ID,
        'predecessor_run_id':artifact.P344_PREDECESSOR_RUN_ID_HEX,
        'source_contract_id':adapter.PARENT_SOURCE_CONTRACT_ID,
        'userspace_overlay_contract_id':adapter.OVERLAY_CONTRACT_ID,
        'profile':adapter.PROFILE,'authority_source':receipt(Path(__file__).resolve()),
        'builder_result':receipt(candidate_build.DEFAULT_OUTPUT_ROOT/'result.json'),
        'candidate':candidate,'source_closure':source_receipts(),
        'rollback_ap':{'path':str(ROLLBACK_AP.relative_to(ROOT)),**ROLLBACK_IDENTITY},
        'auth_key':artifact.auth_key_identity(),'adapter':adapter.audit(),
        'qualification':adapter.acceptance_fixture()['qualification_commands'],
        'observer_binding':observer.audit_binding(),'console_owner':console_owner.audit(),
        'safety':{'host_only':True,'device_contact':False,'live_authorized':False,
            'later_action_lease_active':False,'mandatory_rollback':True,
            'console_reentry':False,'automatic_recovery_proved':False}}


if __name__=='__main__':
    raise SystemExit(main())
