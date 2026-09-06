#!/usr/bin/env python3
"""P347 raw Carrier binding and fixed read-only-shell acceptance; no lease."""
from pathlib import Path
import hashlib

TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p345_stock_process_v2_adapter.py')
TEMPLATE_IDENTITY = {"size": 7753, "sha256": "f9934c7d274a93ee079ee15e5f7daca089326d8da075086f03eaf77acf7bae40"}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P347 source template identity differs")
_template = _template.replace(b"P345", b"P347").replace(b"p345", b"p347")
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p347", "exec"), globals())
