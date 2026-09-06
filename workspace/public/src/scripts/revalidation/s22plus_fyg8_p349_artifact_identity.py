#!/usr/bin/env python3
"""P349 fresh bounded RAM workspace binding; H0 only."""
from pathlib import Path
import hashlib
TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p348_artifact_identity.py')
TEMPLATE_IDENTITY = {"size": 2219, "sha256": '22cfa034ea1277e26698f7b0496dec1f487346163b28829bfea566258ff48313'}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P349 source template identity differs")
_template = _template.replace(b"P348", b"P349").replace(b"p348", b"p349")
_template = _template.replace(b"readonly_research_shell", b"ram_workspace_research_shell")
_template = _template.replace(b"c348f1e0a90b5e6d7c8a9b0c1d2e3f0a", b"c349f1e0a90b5e6d7c8a9b0c1d2e3f0a")
_template = _template.replace(
    b"3d30a0de28abe2b77745426597f0bd10711c833d720270c37f89157bbdf704b0",
    b"de36995ad644cde3df79ea18a0ce1b0cc6ffac3aa8d0e6ec6532d5834cfe155d")
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p349", "exec"), globals())

P348_CONSUMED_AP_IDENTITY = {"size": 28631081,
    "sha256": "5dde23205b3c7bd0026aba0c2c6c2aded4645a808131ad323130976f4ca05263"}
# The exact consumed AP identity is validated against its retained result by
# the fresh source-closure preparation; run-marker rejection is independent.
STALE_AP_IDENTITIES = _bound.STALE_AP_IDENTITIES + (P348_CONSUMED_AP_IDENTITY,)
_bound.STALE_AP_IDENTITIES = STALE_AP_IDENTITIES
_prior_stale_counts = _bound._stale_counts

def _stale_counts(payload):
    value = _prior_stale_counts(payload)
    consumed = "c348f1e0a90b5e6d7c8a9b0c1d2e3f0a"
    value[consumed] = payload.count(consumed.encode("ascii"))
    return value

_bound._stale_counts = _stale_counts
_prior_identity = validate_p349_identity

def validate_p349_identity():
    value = _prior_identity()
    value.update(read_only_child_required=False, ram_workspace_child_required=True,
        workspace_path="/work", workspace_bytes=8388608, workspace_inodes=256,
        workspace_lifetime="current-boot", required_duration_seconds=3600)
    return value
