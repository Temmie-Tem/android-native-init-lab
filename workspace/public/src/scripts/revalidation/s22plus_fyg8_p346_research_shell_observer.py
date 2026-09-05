#!/usr/bin/env python3
"""P346 numeric-witness qualification using the reviewed five-session observer."""
from pathlib import Path
import hashlib

TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p345_research_shell_observer.py')
TEMPLATE_IDENTITY = {"size": 42606, "sha256": "7d24a1ae005ef07235a45a8c24256ae3fcf1ba4972620868730318b6b51a1b12"}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P346 source template identity differs")
_template = _template.replace(b'import s22plus_fyg8_p345_research_shell_runtime as runtime',
                              b'import s22plus_fyg8_p346_research_shell_runtime as runtime')
_template = _template.replace(b's22plus-fyg8-p345-research-shell-qualification',
                              b's22plus-fyg8-p346-research-shell-qualification')
# Fixed P345 canary/CANCEL markers are protocol vocabulary, not run identity.
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p346", "exec"), globals())
