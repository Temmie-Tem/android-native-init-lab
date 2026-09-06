#!/usr/bin/env python3
"""Versioned read-only child: relative CLOCK_REALTIME delay, no other new call.

Preserve the consumed P345/P346 fragment and loader. This source-bound loader
reuses their fixed view/limits/privilege implementation for future candidates.
"""
from pathlib import Path
import hashlib
import ast

TEMPLATE_SOURCE = Path(__file__).with_name("s22plus_fyg8_p345_readonly_child.py")
TEMPLATE_IDENTITY = {'size': 11111, 'sha256': 'a438364fdbb1259610b48ef699c837178e748175ae65124990033619729614b0'}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("read-only child v2 template differs")
_template = _template.replace(b"s22plus_fyg8_p345_readonly_child.inc.c",
                              b"s22plus_fyg8_readonly_child_v2.inc.c")
_template = _template.replace(b's22plus_fyg8_p345_readonly_child_v1',
                              b's22plus_fyg8_readonly_child_v2')
_template = _template.replace(b'    "nanosleep",',
    b'    "nanosleep",\n    "clock_nanosleep-realtime-relative-only",')
_template = _template.replace(b'"unsupported_syscall_policy": "fail-closed-before-ash"',
                              b'"unsupported_syscall_policy": "deny-with-EPERM"')
_tree = ast.parse(_template)
for _node in _tree.body:
    if isinstance(_node, ast.Assign) and any(isinstance(t, ast.Name) and
            t.id == "SOURCE_IDENTITY" for t in _node.targets):
        _node.value = ast.parse("{'size': 22388, 'sha256': '31b5d23a8b72816bdc299d41180d5aef33d9157accbd2bb7d482d555fa6e48f0'}", mode="eval").body
exec(compile(ast.fix_missing_locations(_tree), str(TEMPLATE_SOURCE)+"#v2", "exec"), globals())
