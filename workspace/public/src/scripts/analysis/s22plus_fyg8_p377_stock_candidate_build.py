"""v0.1.1-rc.1 system-status HUD, fresh candidate identity."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p377_namespace import load_predecessor
load_predecessor(globals())

_status_source_files=source_files

def source_files():
    from s22plus_fyg8_p377_namespace import P376_SOURCES
    result=dict(_status_source_files())
    for name in ('s22plus_hud_renderer_v2.inc.c','s22plus_status_metrics_v1.inc.c'):
        path=ROOT/'workspace/public/src/native-init'/name
        result[str(path.relative_to(ROOT))]=path
    for relative,_ in P376_SOURCES.values():result[relative]=ROOT/relative
    return result

DEFAULT_OUTPUT_ROOT=ROOT/'workspace/private/outputs/s22plus-fyg8-v0.1.1-rc.1/candidate-build-final'
_status_build=build_result
_status_audit=audit_existing

def build_result(output_root=DEFAULT_OUTPUT_ROOT,*,audit_only=False):
    return _status_build(output_root,audit_only=audit_only)

def audit_existing(output_root=DEFAULT_OUTPUT_ROOT):
    return _status_audit(output_root)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args()
    result=build_result(args.out,audit_only=args.audit_only)
    print(json.dumps({'verdict':result['verdict'],'ap':result['candidate']['a']['ap_tar_md5']},sort_keys=True))
