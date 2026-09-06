#!/usr/bin/env python3
"""P350 H0-only promotion using the ordinary no-lease preparation owner."""
from pathlib import Path
import hashlib

TEMPLATE_SOURCE=Path(__file__).with_name('prepare_s22plus_fyg8_p345_process_v2.py')
TEMPLATE_IDENTITY={'size':7412,'sha256':'9af06de6f4fed7f7a59179922becf9b1c7e27a633b2fc731bdce6ac26df38380'}
_source=TEMPLATE_SOURCE.read_bytes()
if {'size':len(_source),'sha256':hashlib.sha256(_source).hexdigest()}!=TEMPLATE_IDENTITY:
    raise ValueError('P350 preparation template identity differs')
_source=_source.replace(b'P345',b'P350').replace(b'p345',b'p350')
_source=_source.replace(b'process_v2_ready_2',b'process_v2_ready_1').replace(b'process-v2-ready-2',b'process-v2-ready-1').replace(b'p350-live-2',b'p350-live-1')
_source=_source.replace(b'evidence.p350_research_shell_observer_spec()',b'evidence._shell_observer_spec("p350")')
_source=_source.replace(b'"timeout_sec": 300',b'"timeout_sec": 150')
exec(compile(_source,str(TEMPLATE_SOURCE)+'#p350','exec'),globals())
