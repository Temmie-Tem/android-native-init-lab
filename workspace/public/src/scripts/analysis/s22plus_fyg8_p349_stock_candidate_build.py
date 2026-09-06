#!/usr/bin/env python3
"""P349 fresh H0 packaging over an immutable retained construction template."""
from pathlib import Path
import hashlib
import ast
TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p348_stock_candidate_build.py')
TEMPLATE_IDENTITY = {"size": 4087, "sha256": 'be94a5a021fd18d1d9d22dd8b7b70414f74effe990c3fae5e72bc4f38d04d350'}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P349 packaging template identity differs")
_template = _template.replace(b"P348", b"P349").replace(b"p348", b"p349")
_template = _template.replace(b"P3.48", b"P3.49")
_template = _template.replace(b"s22plus_fyg8_readonly_child_v2", b"s22plus_fyg8_ram_workspace_child_v1")
_template = _template.replace(b'_tree = ast.parse(_template)', b'_template = _template.replace(b"s22plus_fyg8_readonly_child_v2", b"s22plus_fyg8_ram_workspace_child_v1")\n_tree = ast.parse(_template)')
_tree = ast.parse(_template)
_worker_pins = {'P349_RUNTIME_IDENTITY': {'size': 1824, 'sha256': 'a2562d922d01a922c48e90957a7c06fc5bfa56131801100311c80b790851bdf9'}, 'P349_ARTIFACT_IDENTITY': {'size': 2092, 'sha256': '6e74cd0a96fd834185d2f98770a4b153bab7371227924c934a70cd586a45f31d'}, 'P349_OBSERVER_IDENTITY': {'size': 2586, 'sha256': 'f610f9c04b95997809529d0176ffece20a1da98ea7c69125ac3541d3b8a104e3'}, 'P349_ADAPTER_IDENTITY': {'size': 1297, 'sha256': 'fbdf8f938aa1fa2065c22d288d08c1f9b9222c330fe771082f9c20a4d888d5ae'}}
for _node in _tree.body:
    if isinstance(_node, ast.Assign) and len(_node.targets) == 1:
        _target = _node.targets[0]
        if isinstance(_target, ast.Name) and _target.id == "_worker_pins":
            _node.value = ast.parse(repr(_worker_pins), mode="eval").body
_tree.body = [node for node in _tree.body if not (
    isinstance(node, ast.If) and "__name__" in ast.unparse(node.test))]
exec(compile(ast.fix_missing_locations(_tree), str(TEMPLATE_SOURCE) + "#p349", "exec"), globals())

_prior_fresh_result = _fresh_result

def _fresh_result(value):
    result = _prior_fresh_result(value)
    def update(item):
        if isinstance(item, dict):
            if "read_only_child_boundary" in item:
                item["read_only_child_boundary"] = False
                item["ram_workspace_child_boundary"] = True
            for nested in item.values():
                update(nested)
        elif isinstance(item, list):
            for nested in item:
                update(nested)
    update(result)
    result["ram_workspace"] = {"path": "/work", "bytes": 8388608, "inodes": 256,
        "lifetime": "current-boot", "uid": 65534, "gid": 65534}
    return result

if __name__ == "__main__":
    _ENGINE.build_result = build_result
    raise SystemExit(_ENGINE.main())
