#!/usr/bin/env python3
"""P350 complete display assets through the existing static/promotion schema."""
from pathlib import Path
import ast
import hashlib

TEMPLATE_SOURCE=Path(__file__).with_name('s22plus_fyg8_p345_process_v2_candidate_static.py')
TEMPLATE_IDENTITY={'size':8107,'sha256':'4537f63080f1397c2775da0557f3c2622d103fc2b284144d2a3df1623efbb3e0'}
_source=TEMPLATE_SOURCE.read_bytes()
if {'size':len(_source),'sha256':hashlib.sha256(_source).hexdigest()}!=TEMPLATE_IDENTITY:
    raise ValueError('P350 static template identity differs')
_source=_source.replace(b'P345',b'P350').replace(b'p345',b'p350')
_tree=ast.parse(_source)
_tree.body=[n for n in _tree.body if not (isinstance(n,ast.FunctionDef) and n.name=='build_result') and not (isinstance(n,ast.If) and '__name__' in ast.unparse(n.test))]
exec(compile(ast.fix_missing_locations(_tree),str(TEMPLATE_SOURCE)+'#p350','exec'),globals())
import s22plus_fyg8_p350_stock_candidate_build as candidate_build

SOURCE_FILES.pop('p350_readonly_child');SOURCE_FILES.pop('p350_readonly_child_c')
SOURCE_FILES.update({
    'p350_readonly_child':REVALIDATION/'s22plus_fyg8_readonly_child_v2.py',
    'p350_readonly_child_c':ROOT/'workspace/public/src/native-init/s22plus_fyg8_readonly_child_v2.inc.c',
    'p350_renderer':ROOT/'workspace/public/src/native-init/s22plus_native_display_h0.c',
    'p350_module_loader':ROOT/'workspace/public/src/native-init/s22plus_native_display_load.inc.c',
    'p350_static_template':TEMPLATE_SOURCE,
    'p350_target_contract':ROOT/'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md',
})
for name in ('s22plus_fyg8_p345_research_shell_runtime','s22plus_fyg8_p347_research_shell_runtime',
    's22plus_fyg8_p345_research_shell_observer','s22plus_fyg8_p347_research_shell_observer',
    's22plus_fyg8_p345_artifact_identity','s22plus_fyg8_p345_stock_process_v2_adapter',
    's22plus_fyg8_p345_readonly_child'):
    SOURCE_FILES['p350_template_'+name]=REVALIDATION/(name+'.py')
_base_source_receipts=source_receipts


def source_receipts():
    values=_base_source_receipts()
    built=json.loads(candidate_build.stable(candidate_build.DEFAULT_OUTPUT_ROOT/'result.json'))
    for name,expected in built['source_inputs'].items():
        path=ROOT/name
        candidate_build.stable(path,expected)
        values['p350_build_input_'+hashlib.sha256(name.encode()).hexdigest()[:16]]=receipt(path)
    return values


def build_result():
    b=candidate_build.audit_existing()
    inventory=b['candidate']['a']['inventory']
    assets={n:v for n,v in inventory.items() if n=='s22-display' or n=='s22-display-modules' or n.startswith('s22-display-modules/')}
    candidate={'a':b['candidate']['a'],'b':b['candidate']['b'],'image':b['image'],
        'init':b['init'],'child':b['child'],
        'busybox':{k:inventory['bin/busybox'][k] for k in ('size','sha256')},
        'display_assets':assets,'boot_only':True,'byte_identical':True}
    artifact.validate_rollback_ap(ROLLBACK_AP,ROLLBACK_IDENTITY)
    return {'schema':SCHEMA,'verdict':VERDICT,'target':TARGET,'run_id':RUN_ID,
        'predecessor_run_id':artifact.P344_PREDECESSOR_RUN_ID_HEX,
        'source_contract_id':adapter.PARENT_SOURCE_CONTRACT_ID,
        'userspace_overlay_contract_id':adapter.OVERLAY_CONTRACT_ID,'profile':adapter.PROFILE,
        'authority_source':receipt(Path(__file__).resolve()),
        'builder_result':receipt(candidate_build.DEFAULT_OUTPUT_ROOT/'result.json'),
        'candidate':candidate,'source_closure':source_receipts(),
        'rollback_ap':{'path':str(ROLLBACK_AP.relative_to(ROOT)),**ROLLBACK_IDENTITY},
        'auth_key':artifact.auth_key_identity(),'adapter':adapter.audit(),
        'qualification':adapter.acceptance_fixture()['qualification_commands'],
        'observer_binding':observer.audit_binding(),
        'safety':{'host_only':True,'device_contact':False,'live_authorized':False,
            'later_action_lease_active':False,'mandatory_rollback':True}}

if __name__=='__main__':raise SystemExit(main())
