"""P363 sealed successor binding; no device authority."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "revalidation"))
from s22plus_fyg8_p363_namespace import load
load(globals())

# The namespace loader reads these without importing them; bind their bytes too.
from s22plus_fyg8_p363_namespace import PREDECESSORS
_inherited_source_files = source_files


def source_files():
    result = _inherited_source_files()
    for relative, _ in PREDECESSORS.values():
        result[relative] = ROOT / relative
    return result


import s22plus_fyg8_p363_return_spec as return_spec
DEFAULT_OUTPUT_ROOT = ROOT / 'workspace/private/outputs/s22plus_fyg8_p363/stock-candidate-build-v1-20260908-02'
MODULE_NAMES = artifact.DISPLAY_MODULE_NAMES + tuple(n for n, _, _, _ in return_spec.MODULES)
_RETURN_BASE_SOURCES = source_files

def source_files():
    result = _RETURN_BASE_SOURCES()
    for path in (runtime.CONTROL_SOURCE, runtime.MODULE_SOURCE):
        result[str(path.relative_to(ROOT))] = path
    return result

def display_modules(graph):
    display = {name: stable(provider_path(name), ADDITIONS[name]) if name in ADDITIONS else
        stable(DISPLAY / 'union-modules-final' / name,
            {k: graph['results'][name][k] for k in ('size', 'sha256')})
        for name in artifact.DISPLAY_MODULE_NAMES}
    return display | return_spec.module_bytes()

# Resolve fresh defaults in this namespace, including library callers. Sealed
# function defaults were captured before the P363 output directory override.
_return_inherited_audit = audit_existing
_return_inherited_build = build_result


def audit_existing(output_root=DEFAULT_OUTPUT_ROOT):
    return _return_inherited_audit(output_root)


def build_result(output_root=DEFAULT_OUTPUT_ROOT, *, audit_only=False):
    return _return_inherited_build(output_root,audit_only=audit_only)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument('--audit-only', action='store_true')
    args = parser.parse_args()
    result = build_result(args.out, audit_only=args.audit_only)
    print(json.dumps({'verdict': result['verdict'], 'ap': result['candidate']['a']['ap_tar_md5']}, sort_keys=True))
