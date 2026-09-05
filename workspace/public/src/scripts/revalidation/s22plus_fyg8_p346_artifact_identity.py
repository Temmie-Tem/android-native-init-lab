#!/usr/bin/env python3
"""P346 exact Image/AP joins from the retained P344 construction base."""
from pathlib import Path
import hashlib

TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p345_artifact_identity.py')
TEMPLATE_IDENTITY = {"size": 4090, "sha256": "db540159a31b3f82a67c91837e814aa873c74d2b373dd6eb2291bb2c107d5402"}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P346 source template identity differs")
_template = _template.replace(b"P345", b"P346").replace(b"p345", b"p346")
_template = _template.replace(b"c345f1e0a90b5e6d7c8a9b0c1d2e3f0a",
                              b"c346f1e0a90b5e6d7c8a9b0c1d2e3f0a")
_template = _template.replace(b"b937b2aeb9d1b70a7b1a2de891412a94415960b91de7494cffd51fa1d0897ccf",
                              b"2529892a8ef9d9f9786037a81d02418883568aff2cf72d4c0d953668f0ac9c36")
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p346", "exec"), globals())
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
