"""P366 exact native departure successor; no device authority."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p366_namespace import load
load(globals())

_departure_sources=source_files

def source_files():
    value=_departure_sources()
    path=ROOT/'workspace/public/src/scripts/revalidation/s22plus_native_usb_departure_v1.py'
    value[str(path.relative_to(ROOT))]=path
    return value

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args()
    result=build_result(args.out,audit_only=args.audit_only)
    print(json.dumps({'verdict':result['verdict'],'ap':result['candidate']['a']['ap_tar_md5']},sort_keys=True))
