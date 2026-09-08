"""P370 one planned pre-CONTROL handoff; H0 only until approved."""
from s22plus_fyg8_p370_namespace import load
load(globals())

HANDOFF_SOURCE=ROOT/'workspace/public/src/native-init/s22plus_native_handoff_v1.inc.c'
_handoff_base_exec=_exec_function

def _exec_function(value):
    value=_handoff_base_exec(value)
    value=_once(value,b'    unsigned wait_marker;\n',b'''    unsigned wait_marker;
    unsigned handoff_used,handoff_phase;
    long retained_pid;
    uint8_t active_nonce[32],resume_nonce[32],resume_boot[32];
    struct timespec64 quiet_until;
''')
    value=_once(value,b'#define P370_CONTROL_SEQUENCE 5U',b'#define P370_CONTROL_SEQUENCE 8U')
    value=_replace_function(value,b'static long p370_try_control(',HANDOFF_SOURCE.read_bytes())
    value=_once(value,b'    struct p370_control_state control = {0};\n',
        b'    struct p370_control_state control = {0};\n'
        b'    control.retained_pid=pid;memcpy(control.active_nonce,nonce,32U);\n')
    value=_once(value,b'            if(reaped) {rc=p370_diag_child_status(status);if(rc!=0)break;}',
        b'            if(reaped && control.handoff_phase!=1U && control.handoff_phase!=2U) {rc=p370_diag_child_status(status);if(rc!=0)break;}')
    return value

P345_HELPER_TEMPLATE=P345_HELPER=build_helper()
P370_HELPER_TEMPLATE=P370_HELPER=P345_HELPER_TEMPLATE
_handoff_audit=audit_binding

def audit_binding(*,child=None):
    value=_handoff_audit(child=child)
    value.update(control_sequence=8,planned_handoff_maximum=1,authenticated_transport_legs=2,
        native_tty_reopened=False,host_tty_reopened=True,child_relaunched=False,
        handoff_quiet_sec=2,deadline_renewed=False)
    return value
