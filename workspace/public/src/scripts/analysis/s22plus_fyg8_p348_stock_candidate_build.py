#!/usr/bin/env python3
"""P348 deterministic A/B build wrapper; no device contact."""

from pathlib import Path
import hashlib


TEMPLATE_SOURCE = Path(__file__).with_name(
    "s22plus_fyg8_p347_stock_candidate_build.py"
)
TEMPLATE_IDENTITY = {
    "size": 4247,
    "sha256": "54375480de547b4b06804e35d3cd53ae2e45add7ce2a58482016988561f6d5c1",
}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P348 source template identity differs")
import ast

_template = _template.replace(b"P347", b"P348").replace(b"p347", b"p348")
_template = _template.replace(b"P3.47", b"P3.48")
_template = _template.replace(
    b"stock-candidate-build-v1-20260906-01",
    b"stock-candidate-build-v1-20260906-01",
)

_tree = ast.parse(_template)
_worker_pins = {
    "P348_RUNTIME_IDENTITY": {
        "size": 1916,
        "sha256": "adbe6fe1891bdaa80c49087a7aa87b3f1f93d5da9ac5ce459671aa30f9f65885",
    },
    "P348_ARTIFACT_IDENTITY": {
        "size": 2219,
        "sha256": "22cfa034ea1277e26698f7b0496dec1f487346163b28829bfea566258ff48313",
    },
    "P348_OBSERVER_IDENTITY": {
        "size": 22531,
        "sha256": "e4b9d45f0050b0b97985e98ab09bc21441177b088d870f055cec2fad7ef76b42",
    },
    "P348_ADAPTER_IDENTITY": {
        "size": 4894,
        "sha256": "a46fa7c7bbf80d1c84698aacbb66ec756960fc3ae69d33dd4f2b8e2494eaf059",
    },
}
for _node in _tree.body:
    if isinstance(_node, ast.Assign) and len(_node.targets) == 1:
        _target = _node.targets[0]
        if isinstance(_target, ast.Name) and _target.id == "_worker_pins":
            _node.value = ast.parse(repr(_worker_pins), mode="eval").body
        elif isinstance(_target, ast.Name) and _target.id in _worker_pins:
            _node.value = ast.parse(repr(_worker_pins[_target.id]), mode="eval").body
_tree.body = [
    _node
    for _node in _tree.body
    if not (
        isinstance(_node, ast.FunctionDef)
        and _node.name in {"_rewrite_result", "audit_existing", "build_result"}
    )
    and not (
        isinstance(_node, ast.If) and "__name__" in ast.unparse(_node.test)
    )
]
exec(compile(ast.fix_missing_locations(_tree), str(TEMPLATE_SOURCE) + "#p348", "exec"), globals())


def _complete_build_result(value):
    result = _fresh_result(value)
    result["p348_ap_identity"] = dict(result["phase2"]["candidate"]["a"]["ap_tar_md5"])
    return result


_build_tree = ast.parse(_ENGINE_SOURCE)
_build_node = next(
    node
    for node in _build_tree.body
    if isinstance(node, ast.FunctionDef) and node.name == "_build_once"
)
_build_text = ast.unparse(_build_node)
_publication = "_write_exclusive(output_root / 'result.json', _json_bytes(result))"
if _build_text.count(_publication) != 1:
    raise AuditError("P348 final publication seam differs")
_build_text = _build_text.replace(
    _publication,
    "result = _complete_build_result(result)\n    " + _publication,
    1,
)
_ENGINE._complete_build_result = _complete_build_result
exec(compile(_build_text, str(SELF_SOURCE) + "#create", "exec"), _ENGINE.__dict__)


def audit_existing(output_root=DEFAULT_OUTPUT_ROOT):
    output_root = Path(output_root).absolute()
    if output_root != DEFAULT_OUTPUT_ROOT:
        raise AuditError("P348 audit requires its exact fresh output namespace")
    result = _ENGINE.audit_existing(output_root)
    _stable_worker_sources(result)
    expected = _complete_build_result(result)
    if _ENGINE._json_bytes(result) != _ENGINE._json_bytes(expected):
        raise AuditError("P348 stored final build metadata differs")
    return result


def build_result(output_root=DEFAULT_OUTPUT_ROOT, *, audit_only=False):
    output_root = Path(output_root).absolute()
    if output_root != DEFAULT_OUTPUT_ROOT:
        raise AuditError("P348 build requires its exact fresh output namespace")
    if not audit_only:
        _ENGINE._build_once(output_root)
    return audit_existing(output_root)


if __name__ == "__main__":
    _ENGINE.build_result = build_result
    raise SystemExit(_ENGINE.main())
