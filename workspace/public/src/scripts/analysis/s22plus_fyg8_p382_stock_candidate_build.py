"""v0.1.2-rc.5 qualification with compact host observation journal."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p382_namespace import load_predecessor
load_predecessor(globals())

DEFAULT_OUTPUT_ROOT=ROOT/"workspace/private/outputs/s22plus-fyg8-v0.1.2-rc.5/candidate-build-final"
_rc5_build=build_result
_rc5_audit=audit_existing
_rc5_sources=source_files

def build_result(output_root=DEFAULT_OUTPUT_ROOT,*,audit_only=False):
    return _rc5_build(output_root,audit_only=audit_only)

def audit_existing(output_root=DEFAULT_OUTPUT_ROOT):
    return _rc5_audit(output_root)

def source_files():
    from s22plus_fyg8_p382_namespace import P381_SOURCES
    result=dict(_rc5_sources())
    for relative,_ in P381_SOURCES.values():result[relative]=ROOT/relative
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--audit-only",action="store_true")
    args=parser.parse_args()
    result=build_result(args.out,audit_only=args.audit_only)
    print(json.dumps({"verdict":result["verdict"],"ap":result["candidate"]["a"]["ap_tar_md5"]},sort_keys=True))
