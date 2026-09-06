#!/usr/bin/env python3
"""P347 fresh A/B build with read-only revalidation; retained inputs never rewritten."""
from pathlib import Path
import hashlib

TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p345_stock_candidate_build.py')
TEMPLATE_IDENTITY = {'size': 19988, 'sha256': '5f30eca14784c1801a83584eba2e50168e061da0207103c72a9b10b08e76b32a'}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P347 source template identity differs")
import ast
_template = _template.replace(b"P345", b"P347").replace(b"p345", b"p347")
_template = _template.replace(b"P3.45", b"P3.47")
_template = _template.replace(b"s22plus_fyg8_p347_readonly_child as child",
                              b"s22plus_fyg8_readonly_child_v2 as child")
_template = _template.replace(b"stock-candidate-build-v1-20260906-02",
                              b"stock-candidate-build-v1-20260906-01")
_tree = ast.parse(_template)
# Freeze all changed wrapper source inputs before candidate derivation.
_worker_pins = {'P347_RUNTIME_IDENTITY': {'size': 2996, 'sha256': '6323898af8af5a5eb26776e38682f9851b5e9af505ef11b5c5b1b7938baaef69'}, 'P347_ARTIFACT_IDENTITY': {'size': 2178, 'sha256': 'e0a45f6beb220b3be2a23d89471bb27c437b41e83ca0a3dcc326f9c165987d85'}, 'P347_OBSERVER_IDENTITY': {'size': 3084, 'sha256': 'a3fd9c964f3a9d40892c73c65b162340f9373c755c772957d71b66d0fe1bac0a'}, 'P347_ADAPTER_IDENTITY': {'size': 700, 'sha256': '4164a62c11f419e2675bb2a65eed8a7b0b4b2f6a2d67a4ac54a4cca97397a5e0'}}
for _node in _tree.body:
    if isinstance(_node, ast.Assign) and len(_node.targets) == 1:
        _target = _node.targets[0]
        if isinstance(_target, ast.Name) and _target.id in _worker_pins:
            _node.value = ast.parse(repr(_worker_pins[_target.id]), mode="eval").body
# The old mutating audit and truncating publisher are never compiled here.
_tree.body = [_node for _node in _tree.body if not (
    isinstance(_node, ast.FunctionDef) and _node.name in
    {"_rewrite_result", "audit_existing", "build_result"}) and not (
    isinstance(_node, ast.If) and "__name__" in ast.unparse(_node.test))]
exec(compile(ast.fix_missing_locations(_tree), str(TEMPLATE_SOURCE) + "#p347", "exec"), globals())


def _complete_build_result(value):
    result = _fresh_result(value)
    result["p347_ap_identity"] = dict(result["phase2"]["candidate"]["a"]["ap_tar_md5"])
    return result


# Rebind just the fresh-creation function so its one exclusive result write
# already carries final metadata. Reopening invokes no writer or chmod.
_build_tree = ast.parse(_ENGINE_SOURCE)
_build_node = next(node for node in _build_tree.body
                   if isinstance(node, ast.FunctionDef) and node.name == "_build_once")
_build_text = ast.unparse(_build_node)
_publication = "_write_exclusive(output_root / 'result.json', _json_bytes(result))"
if _build_text.count(_publication) != 1:
    raise AuditError("P347 final publication seam differs")
_build_text = _build_text.replace(_publication,
    "result = _complete_build_result(result)\n    " + _publication, 1)
_ENGINE._complete_build_result = _complete_build_result
exec(compile(_build_text, str(SELF_SOURCE) + "#create", "exec"), _ENGINE.__dict__)


def audit_existing(output_root=DEFAULT_OUTPUT_ROOT):
    output_root = Path(output_root).absolute()
    if output_root != DEFAULT_OUTPUT_ROOT:
        raise AuditError("P347 audit requires its exact fresh output namespace")
    result = _ENGINE.audit_existing(output_root)
    _stable_worker_sources(result)
    expected = _complete_build_result(result)
    if _ENGINE._json_bytes(result) != _ENGINE._json_bytes(expected):
        raise AuditError("P347 stored final build metadata differs")
    return result


def build_result(output_root=DEFAULT_OUTPUT_ROOT, *, audit_only=False):
    output_root = Path(output_root).absolute()
    if output_root != DEFAULT_OUTPUT_ROOT:
        raise AuditError("P347 build requires its exact fresh output namespace")
    if not audit_only:
        _ENGINE._build_once(output_root)
    return audit_existing(output_root)


if __name__ == "__main__":
    _ENGINE.build_result = build_result
    raise SystemExit(_ENGINE.main())
