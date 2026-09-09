"""P376 boot HUD with the reviewed root console; fresh identity."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p376_namespace import load_template
load_template(globals())

_hud_source_files=source_files

def source_files():
    from s22plus_fyg8_p376_namespace import P375_SOURCES
    result=dict(_hud_source_files())
    for path in (runtime.HUD_SOURCE,ROOT/'workspace/public/src/native-init/s22plus_hud_renderer_v1.inc.c'):
        result[str(path.relative_to(ROOT))]=path
    # Sealed template bytes are build inputs even when their Python wrappers
    # are loaded by projection instead of normal import discovery.
    for relative,_ in P375_SOURCES.values():result[relative]=ROOT/relative
    for folder in ('analysis','revalidation'):
        for path in (ROOT/'workspace/public/src/scripts'/folder).glob('*s22plus_fyg8_p376*.py'):
            result[str(path.relative_to(ROOT))]=path
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args()
    result=build_result(args.out,audit_only=args.audit_only)
    print(json.dumps({'verdict':result['verdict'],'ap':result['candidate']['a']['ap_tar_md5']},sort_keys=True))
