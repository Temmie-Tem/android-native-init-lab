#!/usr/bin/env python3
"""P349 current-boot RAM workspace over the reviewed P347 command owner."""
from pathlib import Path
import hashlib

TEMPLATE_SOURCE = Path(__file__).with_name("s22plus_fyg8_p347_research_shell_runtime.py")
TEMPLATE_IDENTITY = {"size": 2996, "sha256": "6323898af8af5a5eb26776e38682f9851b5e9af505ef11b5c5b1b7938baaef69"}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P349 runtime template identity differs")
_template = _template.replace(b"P347", b"P349").replace(b"p347", b"p349")
_template = _template.replace(b"c347f1e0a90b5e6d7c8a9b0c1d2e3f0a", b"c349f1e0a90b5e6d7c8a9b0c1d2e3f0a")
_template = _template.replace(b"s22plus_fyg8_readonly_child_v2", b"s22plus_fyg8_ram_workspace_child_v1")
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p349", "exec"), globals())

# The parent creates the fixed bounded RAM mount once before any listener.
# Later commands never cause parent-side traversal or processing of its files.
P345_ENTRY = (
    b"    if (p349_prepare_workspace() != 0)\n"
    b"        p290_fail_next(P335_DETAIL_INITIAL_SESSION);\n"
) + P345_ENTRY
P349_ENTRY = P345_ENTRY
P349_CONSUMED_RUN_ID_HEX = "c348f1e0a90b5e6d7c8a9b0c1d2e3f0a"
if P349_RUN_ID_HEX != "c349f1e0a90b5e6d7c8a9b0c1d2e3f0a":
    raise RuntimeIdentityError("P349 run identity differs")

_base_audit_binding = audit_binding

def audit_binding(*, child=None):
    value = _base_audit_binding(child=child)
    value["sequence_4_readonly_child"] = False
    value["sequence_4_ram_workspace_child"] = True
    value.update(workspace_path="/work", workspace_bytes=8388608,
                 workspace_inodes=256, workspace_lifetime="current-boot",
                 unrestricted_root_shell=False)
    return value
