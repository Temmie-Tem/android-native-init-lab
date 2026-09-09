#!/usr/bin/env python3
"""P375 root-console H0 promotion; publication still requires review."""
from pathlib import Path
import ast
import hashlib

TEMPLATE_SOURCE=Path(__file__).with_name('prepare_s22plus_fyg8_p345_process_v2.py')
TEMPLATE_IDENTITY={'size':7412,'sha256':'9af06de6f4fed7f7a59179922becf9b1c7e27a633b2fc731bdce6ac26df38380'}
_source=TEMPLATE_SOURCE.read_bytes()
if {'size':len(_source),'sha256':hashlib.sha256(_source).hexdigest()}!=TEMPLATE_IDENTITY:
    raise ValueError('P375 preparation template identity differs')
_source=_source.replace(b'P345',b'P375').replace(b'p345',b'p375')
_source=_source.replace(b'evidence.p375_research_shell_observer_spec()',
    b'evidence._shell_observer_spec("p375")')
_tree=ast.parse(_source)
_tree.body=[node for node in _tree.body
    if not (isinstance(node,ast.If) and '__name__' in ast.unparse(node.test))]
exec(compile(ast.fix_missing_locations(_tree),str(TEMPLATE_SOURCE)+'#p375','exec'),globals())

DEFAULT_PROMOTION=ROOT/'workspace/private/outputs/s22plus_fyg8_p375/process-v2-promotion-20260909-01'
DEFAULT_MANIFEST=ROOT/'workspace/public/src/device-action/manifests/s22plus_fyg8_p375_process_v2_ready_1.json'
DEFAULT_MANIFEST_ID='s22plus-fyg8-p375-process-v2-ready-1'
DEFAULT_LIVE_RUN_ID='s22plus-fyg8-p375-live-1'
_p375_manifest=_manifest


def _manifest(static,pins):
    value=_p375_manifest(static,pins)
    value['observation']['timeout_sec']=600
    value['observation']['candidate_observer']=evidence._shell_observer_spec('p375')
    return value


if __name__=='__main__':
    raise SystemExit(main())
