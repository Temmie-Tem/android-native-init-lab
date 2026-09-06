#!/usr/bin/env python3
"""P349 H0 promotion through the retained, source-bound preparation engine."""
from pathlib import Path
import hashlib

TEMPLATE_SOURCE = Path(__file__).with_name("prepare_s22plus_fyg8_p345_process_v2.py")
TEMPLATE_IDENTITY = {"size": 7412, "sha256": "9af06de6f4fed7f7a59179922becf9b1c7e27a633b2fc731bdce6ac26df38380"}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P349 preparation template identity differs")
_template = _template.replace(b"P345", b"P349").replace(b"p345", b"p349")
_template = _template.replace(b"process-v2-promotion-20260906-02", b"process-v2-promotion-20260906-01")
_template = _template.replace(b"p349_process_v2_ready_2", b"p349_process_v2_ready_1")
_template = _template.replace(b"p349-process-v2-ready-2", b"p349-process-v2-ready-1")
_template = _template.replace(b"p349-live-2", b"p349-live-1")
_template = _template.replace(b"evidence.p349_research_shell_observer_spec()", b'evidence._shell_observer_spec("p349")')
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p349", "exec"), globals())
