#!/usr/bin/env python3
"""P348 fresh runtime identity over the consumed P347 child/filter/pipe.

P347 remains a consumed source closure.  This module executes a pinned copy of
that wrapper and changes only the successor namespace and run identity.  The
generated child source, including its syscall filter, blocking output pipe and
sequence-4 ``ash -o pipefail`` path, must stay byte-for-byte equal to P347.
"""

from pathlib import Path
import hashlib


TEMPLATE_SOURCE = Path(__file__).with_name(
    "s22plus_fyg8_p347_research_shell_runtime.py"
)
TEMPLATE_IDENTITY = {
    "size": 2996,
    "sha256": "6323898af8af5a5eb26776e38682f9851b5e9af505ef11b5c5b1b7938baaef69",
}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P348 source template identity differs")

# P347 deliberately retained P345-labelled protocol vocabulary.  Keep that
# ABI and its child/filter/pipe implementation unchanged; only the wrapper's
# public successor namespace and fresh run marker are projected here.
_template = _template.replace(b"P347", b"P348").replace(b"p347", b"p348")
_template = _template.replace(
    b"c347f1e0a90b5e6d7c8a9b0c1d2e3f0a",
    b"c348f1e0a90b5e6d7c8a9b0c1d2e3f0a",
)
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p348", "exec"), globals())


P348_CONSUMED_RUN_ID_HEX = "c347f1e0a90b5e6d7c8a9b0c1d2e3f0a"

# The transformed P347 wrapper creates P348_* aliases from the inherited
# P345-labelled implementation.  Assert the identity that matters to callers
# at import time so stale wrapper projections cannot silently become inputs.
if P348_RUN_ID_HEX != "c348f1e0a90b5e6d7c8a9b0c1d2e3f0a":
    raise RuntimeError("P348 run identity was not projected")
if DEVICE_BANNER != f"S22PLUS-FYG8-E3:{P348_RUN_ID_HEX}\n".encode("ascii"):
    raise RuntimeError("P348 device banner identity differs")

