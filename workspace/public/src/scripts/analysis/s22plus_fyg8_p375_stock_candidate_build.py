"""P375 root-console A/B build using the existing exact boot-only packager."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'revalidation'))
from s22plus_fyg8_p375_namespace import load
load(globals())

_root_sources=source_files
_root_source_files=dict(_root_sources())

def source_files():
    # Some sealed predecessor builders return their module-owned mapping.
    # Freeze and copy it once so repeated static-module loads cannot remove a
    # source from another load's closure through an inherited pop().
    result=dict(_root_source_files)
    result.pop("workspace/public/src/scripts/revalidation/s22plus_fyg8_p375_planned_handoff.py",None)
    for path in (runtime.ROOT_CONSOLE_SOURCE,
                 ROOT/'workspace/public/src/scripts/revalidation/s22plus_root_console_v1.py'):
        result[str(path.relative_to(ROOT))]=path
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args()
    result=build_result(args.out,audit_only=args.audit_only)
    print(json.dumps({'verdict':result['verdict'],'ap':result['candidate']['a']['ap_tar_md5']},sort_keys=True))
