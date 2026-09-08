"""P369 fixed display-wait experiment; no device authority."""
from s22plus_fyg8_p369_namespace import load
load(globals())

WAIT_SOURCE=ROOT/'workspace/public/src/native-init/s22plus_native_wait_checkpoint_v1.inc.c'
_wait_base_exec=_exec_function


def _exec_function(value):
    value=_wait_base_exec(value)
    value=_once(value,b'    uint32_t child_bytes;\n',
        b'    uint32_t child_bytes;\n    unsigned wait_marker;\n    struct timespec64 wait_started;\n')
    value=_once(value,b'static long p369_child_output(',WAIT_SOURCE.read_bytes()+b'\nstatic long p369_child_output(')
    value=_once(value,b'    if(state->ready) return 0; /* Freeze the signed readiness milestone. */\n',b'')
    value=_once(value,b'            state->line_used=state->line_overflow=0U;',
        b'            if(!state->line_overflow && p369_wait_line(state->line,state->line_used)) {\n'
        b'                long rc=p369_note_wait(state);if(rc!=0)return rc;\n'
        b'            }\n            state->line_used=state->line_overflow=0U;')
    value=_once(value,b'''static long p369_try_control(struct p369_control_state *state,int fd,
    const uint8_t *nonce,const struct timespec64 *deadline) {''',b'''static long p369_try_control(struct p369_control_state *state,int fd,
    const uint8_t *nonce,const struct timespec64 *deadline,long pid,int *reaped,int *status) {''')
    value=_once(value,b'    p369_diagnostic.terminal=1; /* Progress ends before CONTROL ACK. */',
        b'    long sampled=p369_wait_checkpoint(state,pid,reaped,status);\n'
        b'    if(sampled!=0)return sampled;\n'
        b'    p369_diagnostic.terminal=1; /* Progress ends before CONTROL ACK. */')
    value=_once(value,b'    const uint8_t accepted[4]={P369_LIVE_MODE,0U,(uint8_t)state->swaps,(uint8_t)state->child_exited};',
        b'    const uint8_t accepted[4]={P369_LIVE_MODE,0U,0U,0U};')
    value=_once(value,b'''    struct p369_control_state control = {0};
    for (;;) {''',b'''    struct p369_control_state control = {0};
    if(p369_display) {
        const uint8_t ready[4]={P369_LIVE_MODE,0U,1U,0U};
        rc=p369_write_status(tty_fd,P369_FRAME_CONTROL_READY,p369_ready_domain,nonce,ready,&deadline);
        if(rc!=0) {
            (void)sys_kill(pid,SIGKILL);(void)p328_reap_after_kill(pid,&status);
            (void)sys_close(pipe_fds[0]);(void)p328_cleanup_process_group(pid);return rc;
        }
        control.ready=1U;
    }
    for (;;) {''')
    old=b'''            if (!control.ready && (control.swaps == 10U || reaped)) {
                control.child_exited = reaped ? 1U : 0U;
                const uint8_t ready[4] = {P369_LIVE_MODE,(uint8_t)control.swaps,1U,
                    (uint8_t)control.child_exited};
                rc = p369_write_status(tty_fd,P369_FRAME_CONTROL_READY,
                    p369_ready_domain,nonce,ready,&deadline);
                if (rc != 0) break;
                control.ready = 1U;
            }
'''
    value=_once(value,old,b'')
    value=_once(value,b'p369_try_control(&control,tty_fd,nonce,&deadline);',
        b'p369_try_control(&control,tty_fd,nonce,&deadline,pid,&reaped,&status);')
    value=_once(value,b'#define P369_DIAG_MAX_FRAMES 48U',b'#define P369_DIAG_MAX_FRAMES 49U')
    return value

P345_HELPER_TEMPLATE=P345_HELPER=build_helper()
P369_HELPER_TEMPLATE=P369_HELPER=P345_HELPER_TEMPLATE
_wait_base_audit=audit_binding


def audit_binding(*,child=None):
    value=_wait_base_audit(child=child)
    value.update(renderer_fault='fixed-userspace-wait-after-third-submission',
        control_readiness='after-preparation-and-clone-independent-of-display',
        diagnostic_max_frames=return_spec.MAX_DIAGNOSTIC_FRAMES,
        wait_checkpoint='signed-marker-age-and-unreaped-child-at-control',
        wait_observation_interval_sec=return_spec.OBSERVATION_INTERVAL_SEC)
    return value
