#!/usr/bin/env python3
"""P348 promotion and ready-manifest preparation; no connected action."""

from pathlib import Path
import hashlib


TEMPLATE_SOURCE = Path(__file__).with_name(
    "prepare_s22plus_fyg8_p347_process_v2.py"
)
TEMPLATE_IDENTITY = {
    "size": 1027,
    "sha256": "207006abe9a3fe91a527b0e09334391e5bd60a48c674708066e91ed1f0febf2c",
}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P348 source template identity differs")
_template = _template.replace(b"P347", b"P348").replace(b"p347", b"p348")
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p348", "exec"), globals())

