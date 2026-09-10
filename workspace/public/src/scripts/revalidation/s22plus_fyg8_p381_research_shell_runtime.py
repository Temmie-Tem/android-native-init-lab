"""v0.1.2-rc.4 output backpressure and bounded memory observations."""
from s22plus_fyg8_p381_namespace import load_predecessor
load_predecessor(globals())

OUTPUT_SOURCE=ROOT/'workspace/public/src/native-init/s22plus_root_console_output_v2.inc.c'
_backpressure_build=build_helper


def apply_backpressure(value):
    value=_once(value,
        b'unsigned cancel_phase,terminal_sent,rx_used,rx_size,qhead,qcount,fault_sent;',
        b'unsigned cancel_phase,terminal_sent,rx_used,rx_size,qhead,qcount,fault_sent,output_turn;')
    anchor=b'static long rc1_child_tick('
    value=_once(value,anchor,OUTPUT_SOURCE.read_bytes()+b'\n'+anchor)
    start=value.index(b'    for(unsigned i=0;i<2;i++)if(s->pipe[i]>=0) {',value.index(anchor))
    end=value.index(b'    if(s->pipe[2]>=0) {',start)
    old=ROOT_CONSOLE_SOURCE.read_bytes()
    a=old.index(b'    for(unsigned i=0;i<2;i++)if(s->pipe[i]>=0) {',old.index(anchor))
    b=old.index(b'    if(s->pipe[2]>=0) {',a)
    if value[start:end]!=old[a:b]:raise ValueError('sealed output loop differs')
    return value[:start]+b'    long output_rc=rc1_output_tick(s);if(output_rc)return output_rc;\n'+value[end:]


def build_helper(child=None):
    return apply_backpressure(_backpressure_build(child))


P345_HELPER_TEMPLATE=P345_HELPER=build_helper()
P381_HELPER_TEMPLATE=P381_HELPER=P345_HELPER
_backpressure_audit=audit_binding


def audit_binding(*,child=None):
    value=_backpressure_audit(child=child)
    value.update(output_source=identity(OUTPUT_SOURCE.read_bytes()),
        pipe_admission='credit-before-read',output_stream_fairness='rotate-after-forward',
        output_queue_entries=8,output_response_reserve=3,
        budget_exhaustion='bounded-discard-with-explicit-truncation',
        control_and_deadlines_unchanged=True)
    return value
