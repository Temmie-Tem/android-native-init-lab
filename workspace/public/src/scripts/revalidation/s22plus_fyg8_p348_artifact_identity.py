#!/usr/bin/env python3
"""P348 exact Image/AP identity over the retained P344 construction base."""

from pathlib import Path
import hashlib


TEMPLATE_SOURCE = Path(__file__).with_name(
    "s22plus_fyg8_p347_artifact_identity.py"
)
TEMPLATE_IDENTITY = {
    "size": 2178,
    "sha256": "e0a45f6beb220b3be2a23d89471bb27c437b41e83ca0a3dcc326f9c165987d85",
}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P348 source template identity differs")
_template = _template.replace(b"P347", b"P348").replace(b"p347", b"p348")
_template = _template.replace(
    b"c347f1e0a90b5e6d7c8a9b0c1d2e3f0a",
    b"c348f1e0a90b5e6d7c8a9b0c1d2e3f0a",
)
_template = _template.replace(
    b"0678765bee776bcfff550e8f02985e32b8a8ee1dbcafff962b42bba33f016c19",
    b"3d30a0de28abe2b77745426597f0bd10711c833d720270c37f89157bbdf704b0",
)
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p348", "exec"), globals())


P347_CONSUMED_AP_IDENTITY = {
    "size": 28631081,
    "sha256": "02c5d905c823f03f560f30c2cc5a734c5c113930b6f9ad15f09c2130245803b0",
}
STALE_AP_IDENTITIES = _bound.STALE_AP_IDENTITIES + (P347_CONSUMED_AP_IDENTITY,)
_bound.STALE_AP_IDENTITIES = STALE_AP_IDENTITIES
_p347_stale_counts = _bound._stale_counts


def _stale_counts(payload):
    counts = _p347_stale_counts(payload)
    consumed = "c347f1e0a90b5e6d7c8a9b0c1d2e3f0a"
    counts[consumed] = payload.count(consumed.encode("ascii"))
    return counts


_bound._stale_counts = _stale_counts

_base_validate_p348_identity = validate_p348_identity


def validate_p348_identity():
    value = _base_validate_p348_identity()
    value.update(
        {
            "initial_session_count": 6,
            "same_fd_session_count": 5,
            "initial_reconnect_count": 1,
            "idle_seconds": 120,
            "total_session_count": 6,
            "total_command_count": 18,
            "physical_reopen_count": 1,
            "initial_observation": "p348_readonly_research_shell_qualification",
            "initial_observation_field": "p348_readonly_research_shell",
            "later_action_lease_active": False,
        }
    )
    return value
