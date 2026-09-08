"""P370 one planned pre-CONTROL handoff; H0 only until approved."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p370_namespace import load
load(globals())

_handoff_sources=source_files

def source_files():
    value=_handoff_sources()
    for p in (runtime.HANDOFF_SOURCE,ROOT/'workspace/public/src/scripts/revalidation/s22plus_native_planned_handoff_v1.py'):
        value[str(p.relative_to(ROOT))]=p
    return value

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--audit-only",action="store_true")
    args=parser.parse_args()
    result=build_result(args.out,audit_only=args.audit_only)
    print(json.dumps({"verdict":result["verdict"],"ap":result["candidate"]["a"]["ap_tar_md5"]},sort_keys=True))
