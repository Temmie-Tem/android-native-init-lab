"""v0.1.2-rc.4 output backpressure and bounded memory observations."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p381_namespace import load_predecessor
load_predecessor(globals())

DEFAULT_OUTPUT_ROOT=ROOT/'workspace/private/outputs/s22plus-fyg8-v0.1.2-rc.4/candidate-build-final'
_rc4_build=build_result
_rc4_existing=audit_existing
_rc4_sources=source_files


def build_result(output_root=DEFAULT_OUTPUT_ROOT,*,audit_only=False):
    return _rc4_build(output_root,audit_only=audit_only)


def audit_existing(output_root=DEFAULT_OUTPUT_ROOT):
    return _rc4_existing(output_root)


def source_files():
    from s22plus_fyg8_p381_namespace import P380_SOURCES
    result=dict(_rc4_sources())
    paths=[ROOT/relative for relative,_ in P380_SOURCES.values()]
    paths+=[runtime.OUTPUT_SOURCE,
        ROOT/'workspace/public/src/native-init/s22plus_memory_snapshot_v1.inc.c',
        ROOT/'workspace/public/src/native-init/s22plus_hud_memory_v1.inc.c',
        ROOT/'workspace/public/src/scripts/analysis/s22plus_memory_manifest_v1.py',
        ROOT/'workspace/public/src/scripts/revalidation/s22plus_memory_snapshot_v1.py']
    for path in paths:result[str(path.relative_to(ROOT))]=path
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args()
    result=build_result(args.out,audit_only=args.audit_only)
    print(json.dumps({'verdict':result['verdict'],'ap':result['candidate']['a']['ap_tar_md5']},sort_keys=True))
