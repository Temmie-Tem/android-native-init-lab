"""P375 root-console source namespace over immutable reviewed predecessors.

Projection copies definition bytes, never rewrites consumed source/artifacts.
The new console runtime and observer supply the changed execution path.
"""
from pathlib import Path
import hashlib
import s22plus_display_step_v1_namespace as parent
ROOT=parent.ROOT
PREDECESSORS=dict(parent.PREDECESSORS)
# Exact deterministic identity-only Image transform, checked before READY.
PREDECESSOR_IMAGE=parent.IMAGE_HASHES['p374']
IMAGE_SHA='9bd1c7055dc1307000fb3939336e05a6eb380a673bd4539a97378c7cddf43910'
_definitions=parent._definitions


def projected(name):
    raw=parent.projected(name.replace('p375','p374'),'p374')
    raw=raw.replace(PREDECESSOR_IMAGE.encode(),IMAGE_SHA.encode())
    raw=raw.replace(b'c374f1e0a90b5e6d7c8a9b0c1d2e3f0b',b'c375f1e0a90b5e6d7c8a9b0c1d2e3f0b')
    return raw.replace(b'P374',b'P375').replace(b'p374',b'p375')


def load(namespace):
    name=Path(namespace['__file__']).name
    raw=projected(name)
    if name.endswith('_research_shell_runtime.py'):
        raw=raw.replace(b'STATUS_SOURCE.read_bytes()',b"STATUS_SOURCE.read_bytes().replace(b'p371',b'p375').replace(b'P371',b'P375')")
    exec(compile(_definitions(raw),str(namespace['__file__'])+'#sealed-predecessor','exec'),namespace)
