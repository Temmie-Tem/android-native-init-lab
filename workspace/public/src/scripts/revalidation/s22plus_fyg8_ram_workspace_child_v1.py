#!/usr/bin/env python3
"""Source-bound RAM workspace child, preserving consumed read-only loaders."""
from pathlib import Path
import ast
import hashlib

CHILD_IDENTITY = {'size': 23811, 'sha256': '672e8f5dcb334527fc1083287940cfecf7c533c8ca05775f129170c973b9232d'}
TEMPLATE_SOURCE = Path(__file__).with_name("s22plus_fyg8_p345_readonly_child.py")
TEMPLATE_IDENTITY = {"size": 11111, "sha256": "a438364fdbb1259610b48ef699c837178e748175ae65124990033619729614b0"}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("RAM workspace child template differs")
_replacements = {
    b"s22plus_fyg8_p345_readonly_child.inc.c": b"s22plus_fyg8_ram_workspace_child_v1.inc.c",
    b"s22plus_fyg8_p345_readonly_child_v1": b"s22plus_fyg8_ram_workspace_child_v1",
    b"/dev/p345-root": b"/dev/p349-root",
    b"P345_O_WRITE_MASK": b"P349_WORK_DATA",
    b'    "writable-create-truncate-append-open-modes",\n': b"",
    b'    "filesystem-mutation",': b'    "filesystem-mutation-outside-work",',
    b'"write-output-pipes-only"': b'"write-output-pipes-and-ram-workspace"',
    b'"openat-readonly-flags-only"': b'"openat-fixed-view-and-ram-workspace"',
    b'    "nanosleep",': b'    "nanosleep",\n    "clock_nanosleep-realtime-relative-only",\n    "mkdirat",\n    "unlinkat",\n    "renameat",',
    b'"unsupported_syscall_policy": "fail-closed-before-ash"': b'"unsupported_syscall_policy": "deny-with-EPERM"',
    b'"new-fixed-readonly-child-boundary"': b'"bounded-current-boot-ram-workspace"',
}
for _old, _new in _replacements.items():
    if _old not in _template:
        raise ValueError("RAM workspace loader seam differs")
    _template = _template.replace(_old, _new)
_tree = ast.parse(_template)
for _node in _tree.body:
    if isinstance(_node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SOURCE_IDENTITY" for t in _node.targets):
        _node.value = ast.parse(repr(CHILD_IDENTITY), mode="eval").body
exec(compile(ast.fix_missing_locations(_tree), str(TEMPLATE_SOURCE) + "#ram-v1", "exec"), globals())
RESOURCE_BOUNDS = dict(RESOURCE_BOUNDS, workspace_bytes=8388608, workspace_inodes=256)
_base_audit = audit
def audit():
    value = _base_audit()
    value.update(workspace_path="/work", workspace_lifetime="current-boot", workspace_nosuid=True, workspace_nodev=True, parent_workspace_api="p349_prepare_workspace(void)")
    return value
