#!/usr/bin/env python3
"""P349 bounded RAM-workspace successor; retained P348 template is immutable."""
from pathlib import Path
import hashlib
TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p348_shell_action.py')
TEMPLATE_IDENTITY = {"size": 36519, "sha256": 'e921080a85b21be4614a68f420249c2c2669296633ed85dceb1ce188d9ca13fb'}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P349 template identity differs")
_template = _template.replace(b"P348", b"P349").replace(b"p348", b"p349")
_template = _template.replace(b"readonly_research_shell", b"ram_workspace_research_shell")
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p349", "exec"), globals())
