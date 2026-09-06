#!/usr/bin/env python3
"""P347 exact Image/AP joins from the retained P344 construction base."""
from pathlib import Path
import hashlib

TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p345_artifact_identity.py')
TEMPLATE_IDENTITY = {"size": 4090, "sha256": "db540159a31b3f82a67c91837e814aa873c74d2b373dd6eb2291bb2c107d5402"}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P347 source template identity differs")
_template = _template.replace(b"P345", b"P347").replace(b"p345", b"p347")
_template = _template.replace(b"c345f1e0a90b5e6d7c8a9b0c1d2e3f0a",
                              b"c347f1e0a90b5e6d7c8a9b0c1d2e3f0a")
_template = _template.replace(b"b937b2aeb9d1b70a7b1a2de891412a94415960b91de7494cffd51fa1d0897ccf",
                              b"0678765bee776bcfff550e8f02985e32b8a8ee1dbcafff962b42bba33f016c19")
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p347", "exec"), globals())
# Consumed P345 is also excluded, while P344 remains the construction source.
P345_CONSUMED_AP_IDENTITY = {"size": 28631081,
    "sha256": "7ee59a134a78568e7a3d534959dbe1e010f975fa4f72b47a1dcaa60d3695f343"}
STALE_AP_IDENTITIES = _bound.STALE_AP_IDENTITIES + (P345_CONSUMED_AP_IDENTITY,)
_bound.STALE_AP_IDENTITIES = STALE_AP_IDENTITIES

_base_stale_counts = _bound._stale_counts

def _stale_counts(payload):
    counts = _base_stale_counts(payload)
    consumed = "c345f1e0a90b5e6d7c8a9b0c1d2e3f0a"
    counts[consumed] = payload.count(consumed.encode("ascii"))
    return counts

_bound._stale_counts = _stale_counts

P346_CONSUMED_AP_IDENTITY = {"size": 28631081,
    "sha256": "ad6a84efa60d81b6779f637a994a22155f60b85f6f83f6b11147a69c5de10e85"}
STALE_AP_IDENTITIES = _bound.STALE_AP_IDENTITIES + (P346_CONSUMED_AP_IDENTITY,)
_bound.STALE_AP_IDENTITIES = STALE_AP_IDENTITIES
_p345_stale_counts = _bound._stale_counts

def _stale_counts(payload):
    counts = _p345_stale_counts(payload)
    consumed = "c346f1e0a90b5e6d7c8a9b0c1d2e3f0a"
    counts[consumed] = payload.count(consumed.encode("ascii"))
    return counts

_bound._stale_counts = _stale_counts
