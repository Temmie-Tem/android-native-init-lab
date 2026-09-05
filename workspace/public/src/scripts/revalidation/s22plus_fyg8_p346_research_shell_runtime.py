#!/usr/bin/env python3
"""P346 fresh identity over the unchanged P345 read-only child and cancel ABI."""
from pathlib import Path
import hashlib

TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p345_research_shell_runtime.py')
TEMPLATE_IDENTITY = {"size": 40666, "sha256": "eab728141657d1d0fa11b4ce5affc7d42426927331c6bdd6500079a1842911d7"}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P346 source template identity differs")
_template = _template.replace(
    b'P345_RUN_ID_HEX = "c345f1e0a90b5e6d7c8a9b0c1d2e3f0a"',
    b'P345_RUN_ID_HEX = "c346f1e0a90b5e6d7c8a9b0c1d2e3f0a"', 1)
_template = _template.replace(b's22plus-fyg8-p345-readonly-research-shell-runtime-v1',
                              b's22plus-fyg8-p346-readonly-research-shell-runtime-v1')
# Execute before derived constants/defaults/helper construction. Parent globals
# remain untouched; P345-labelled C and CANCEL ABI are deliberately preserved.
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p346", "exec"), globals())
for _name, _value in tuple(globals().items()):
    if _name.startswith("P345_"):
        globals()[_name.replace("P345_", "P346_", 1)] = _value
validate_p346_runtime = validate_p345_runtime
P345_CONSUMED_RUN_ID_HEX = "c345f1e0a90b5e6d7c8a9b0c1d2e3f0a"
