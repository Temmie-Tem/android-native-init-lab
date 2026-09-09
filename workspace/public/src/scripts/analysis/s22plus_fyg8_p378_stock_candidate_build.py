"""v0.1.2-rc.1 gauge telemetry HUD, prospective fresh candidate."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p378_namespace import load_predecessor
load_predecessor(globals())

DEFAULT_OUTPUT_ROOT=ROOT/'workspace/private/outputs/s22plus-fyg8-v0.1.2-rc.1/candidate-build-final2'
_gauge_build=build_result
_gauge_audit=audit_existing

def build_result(output_root=DEFAULT_OUTPUT_ROOT,*,audit_only=False):
    return _gauge_build(output_root,audit_only=audit_only)

def audit_existing(output_root=DEFAULT_OUTPUT_ROOT):
    return _gauge_audit(output_root)

# The inherited module graph remains the sealed display/return graph. Append
# the fixed reader only after that graph is validated; it has Image exports only.
import types
TELEMETRY_NAME='s22plus_max77705_telemetry.ko'
TELEMETRY_ROOT=ROOT/'workspace/private/outputs/s22plus-telemetry-provider-qualified-v3'
TELEMETRY_IDENTITY={'size':294480,'sha256':'a0a78e0831fed6cf11a64bdf8583851ed8bad4b29cb33e3a84c1161ab8043eda'}
_gauge_old_modules=types.FunctionType(display_modules.__code__,dict(display_modules.__globals__,MODULE_NAMES=tuple(name for name in MODULE_NAMES if name!=TELEMETRY_NAME)),display_modules.__name__)
_gauge_old_plan=module_plan
MODULE_NAMES=tuple(dict.fromkeys((*MODULE_NAMES,TELEMETRY_NAME)))

def telemetry_qualification():
    receipt=json.loads(stable(TELEMETRY_ROOT/'result.json',{'size':3690,'sha256':'6baa82d9f4da660832936836aea3395818f0163c72a8e22f2f1822bd0facb50d'}))
    if receipt['module']!=TELEMETRY_IDENTITY or not receipt['ab_identical']:
        raise AuditError('telemetry qualification differs')
    for relative,pin in receipt['source_inputs'].items():stable(ROOT/relative,pin)
    return receipt

def display_modules(graph):
    telemetry_qualification()
    result=_gauge_old_modules(graph)
    result[TELEMETRY_NAME]=stable(TELEMETRY_ROOT/'module-a.ko',TELEMETRY_IDENTITY)
    return result

def module_plan(graph):
    plan=_gauge_old_plan(graph)
    if plan.count(b'#define P350_DISPLAY_MODULE_COUNT 12U')!=1 or not plan.endswith(b'};\n'):
        raise AuditError('fixed display plan differs')
    row=('    {"/s22-display-modules/%s", %dULL, 0},\n'%(TELEMETRY_NAME,TELEMETRY_IDENTITY['size'])).encode()
    return plan.replace(b'P350_DISPLAY_MODULE_COUNT 12U',b'P350_DISPLAY_MODULE_COUNT 13U')[:-3]+row+b'};\n'

_gauge_sources=source_files

def source_files():
    from s22plus_fyg8_p378_namespace import P377_SOURCES
    result=dict(_gauge_sources())
    paths=[ROOT/relative for relative,_ in P377_SOURCES.values()]
    paths += [ROOT/'workspace/public/src/native-init'/name for name in
        ('s22plus_gauge_sample_v1.inc.c','s22plus_status_metrics_v2.inc.c','s22plus_hud_renderer_v3.inc.c')]
    paths += list((ROOT/'workspace/public/src/kernel-modules/s22plus_max77705_telemetry').iterdir())
    paths += [ROOT/'workspace/public/src/scripts/analysis/s22plus_fyg8_telemetry_provider_h0.py']
    for path in paths:
        if path.is_file():result[str(path.relative_to(ROOT))]=path
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args()
    result=build_result(args.out,audit_only=args.audit_only)
    print(json.dumps({'verdict':result['verdict'],'ap':result['candidate']['a']['ap_tar_md5']},sort_keys=True))
