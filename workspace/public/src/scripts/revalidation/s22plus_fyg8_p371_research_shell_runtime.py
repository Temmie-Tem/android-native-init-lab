"""P371 fixed STATUS observations; H0 only until separately approved."""
from s22plus_fyg8_p371_namespace import load
load(globals())

STATUS_SOURCE=ROOT/'workspace/public/src/native-init/s22plus_native_status_v1.inc.c'
_status_exec=_exec_function

def _exec_function(value):
    value=_status_exec(value)
    value=_once(value,b'    unsigned handoff_used,handoff_phase;\n',b'    unsigned handoff_used,handoff_phase,status_count;\n    struct timespec64 first_status_time;\n')
    value=_once(value,b'#define P371_CONTROL_SEQUENCE 8U',b'#define P371_CONTROL_SEQUENCE 10U')
    value=_replace_function(value,b'static long p371_wait_checkpoint(',STATUS_SOURCE.read_bytes())
    value=_once(value,b'phase==2U?9U:P371_FRAME_CONTROL;',b'phase==2U?9U:state->header[5];')
    value=_once(value,b'uint32_t expected_sequence=5U+phase;',b'uint32_t expected_sequence=phase<3U?5U+phase:expected_kind==10U?8U+state->status_count:10U;')
    value=_once(value,b'const uint8_t *h=state->header;\n',b'const uint8_t *h=state->header;\n        if(phase==3U) {\n            expected_kind=h[5];expected_sequence=expected_kind==10U?8U+state->status_count:10U;\n            if(!((expected_kind==10U && state->status_count<2U) || expected_kind==P371_FRAME_CONTROL))return -P260_EPROTO;\n        }\n')
    value=_once(value,b'phase==2U?p371_resume_auth_domain:p371_control_domain;',b'phase==2U?p371_resume_auth_domain:expected_kind==10U?p371_status_request_domain:p371_control_domain;')
    value=_once(value,b'    state->consumed=1U;\n',b'    if(expected_kind==10U) {\n        p371_reset_request(state);\n        return p371_status_reply(state,fd,expected_sequence,deadline,pid,reaped,status);\n    }\n    state->consumed=1U;\n')
    return value

P345_HELPER_TEMPLATE=P345_HELPER=build_helper()
P371_HELPER_TEMPLATE=P371_HELPER=P345_HELPER_TEMPLATE
_status_audit=audit_binding

def audit_binding(*,child=None):
    value=_status_audit(child=child)
    value.update(control_sequence=10,status_maximum=2,status_sequences=[8,9],
        control_independent_of_status_count=True,status_sample='fixed-wait-facts-and-native-interval')
    return value
