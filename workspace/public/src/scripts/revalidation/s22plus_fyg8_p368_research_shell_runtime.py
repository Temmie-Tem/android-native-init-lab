"""P368 fixed child-exit experiment; H0 only until separately approved."""
from s22plus_fyg8_p368_namespace import load
load(globals())

_exit_base_audit=audit_binding

def audit_binding(*,child=None):
    value=_exit_base_audit(child=child)
    value.update(renderer_binary_unchanged=False,
        renderer_fault='fixed-exit-7-after-third-flushed-submission')
    return value
