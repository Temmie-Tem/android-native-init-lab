#!/usr/bin/env python3
"""P349 fresh bounded RAM workspace binding; H0 only."""
from pathlib import Path
import hashlib
TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p348_stock_process_v2_adapter.py')
TEMPLATE_IDENTITY = {"size": 4894, "sha256": 'a46fa7c7bbf80d1c84698aacbb66ec756960fc3ae69d33dd4f2b8e2494eaf059'}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P349 source template identity differs")
_template = _template.replace(b"P348", b"P349").replace(b"p348", b"p349")
_template = _template.replace(b"readonly_research_shell", b"ram_workspace_research_shell")
_template = _template.replace(b"LEASE_DURATION_SEC = 3600", b"LEASE_DURATION_SEC = 3900")
_template = _template.replace(b"|readonly-child|", b"|ram-workspace-8MiB-256-inodes|actual-3600-seconds|")
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p349", "exec"), globals())

_prior_contract = _contract

def _contract():
    value = _prior_contract()
    value.update(read_only_child_required=False, ram_workspace_child_required=True,
        workspace_path="/work", workspace_bytes=8388608, workspace_inodes=256,
        workspace_lifetime="current-boot", required_duration_seconds=3600)
    return value
