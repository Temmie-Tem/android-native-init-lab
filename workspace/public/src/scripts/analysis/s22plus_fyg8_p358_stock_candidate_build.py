"""P358 sealed successor binding; no device authority."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "revalidation"))
from s22plus_fyg8_p358_namespace import load
load(globals())

# The namespace loader reads these without importing them; bind their bytes too.
from s22plus_fyg8_p358_namespace import PREDECESSORS
_inherited_source_files = source_files


def source_files():
    result = _inherited_source_files()
    for relative, _ in PREDECESSORS.values():
        result[relative] = ROOT / relative
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument('--audit-only', action='store_true')
    args = parser.parse_args()
    result = build_result(args.out, audit_only=args.audit_only)
    print(json.dumps({'verdict': result['verdict'], 'ap': result['candidate']['a']['ap_tar_md5']}, sort_keys=True))
