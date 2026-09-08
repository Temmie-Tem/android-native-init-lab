"""Source extension evaluated in each fixed variant namespace."""
_STEP_SOURCE=ROOT/'workspace/public/src/native-init/s22plus_native_display_step_v1.inc.c'
_step_base_exec=_exec_function

def _exec_function(value):
    value=_step_base_exec(value)
    prefix=_STEP_PREFIX.encode();upper=prefix.upper()
    def once(old,new):
        nonlocal value
        value=_once(value,old.replace(b'pstep',prefix).replace(b'PSTEP',upper),new.replace(b'pstep',prefix).replace(b'PSTEP',upper))
    once(b'#define PSTEP_CONTROL_SEQUENCE 10U',b'#define PSTEP_CONTROL_SEQUENCE 14U\n#define PSTEP_STEP_MAX '+str(_STEP_MAX).encode()+b'U')
    once(b'    unsigned wait_marker;',b'    unsigned wait_marker;\n    int step_fd;\n    unsigned step_requested,step_started,step_completed,step_pending,step_failed;')
    # The status domains are declared by the predecessor immediately before the extension.
    anchor=b'static long pstep_sample_wait('.replace(b'pstep',prefix)
    extension=_STEP_SOURCE.read_bytes().replace(b'pstep',prefix).replace(b'PSTEP',upper)
    value=_once(value,anchor,extension+b'\n'+anchor)
    once(b'return pstep_status_reply(state,fd,expected_sequence,deadline,pid,reaped,status);',b'return pstep_step_status(state,fd,expected_sequence,deadline,pid,reaped,status);')
    once(b'long sampled=pstep_wait_checkpoint(state,pid,reaped,status);',b'long sampled=pstep_step_checkpoint(state,pid,reaped,status);')
    once(b'rc = pstep_child_output(&control, output, (size_t)amount);',b'rc = pstep_step_output(&control, output, (size_t)amount);')
    old=b'expected_kind==10U?8U+state->status_count:10U'
    new=b'expected_kind==10U?8U+state->status_count:expected_kind==11U?11U+state->step_requested:14U'
    if value.count(old)!=2:raise ValueError('step sequence seam differs')
    value=value.replace(old,new)
    once(b'((expected_kind==10U && state->status_count<2U) || expected_kind==PSTEP_FRAME_CONTROL)',b'((expected_kind==10U && state->status_count<2U) || (expected_kind==11U && state->step_requested<PSTEP_STEP_MAX) || expected_kind==PSTEP_FRAME_CONTROL)')
    once(b'expected_kind==10U?pstep_status_request_domain:pstep_control_domain;',b'expected_kind==10U?pstep_status_request_domain:expected_kind==11U?pstep_step_domain:pstep_control_domain;')
    once(b'    if(expected_kind==10U) {',b'    if(expected_kind==11U) {\n        pstep_reset_request(state);\n        return pstep_step_request(state,fd,expected_sequence,deadline,pid,reaped,status);\n    }\n    if(expected_kind==10U) {')
    # eventfd2 is the exact ARM64 syscall 19, flags checked by target UAPI/ARM64 H0 probe.
    once(b'    long pid = sys_clone();',b'    long step_fd=pstep_display?syscall6(19,0,O_CLOEXEC|O_NONBLOCK,0,0,0,0):-1;\n    if(pstep_display && step_fd<=2){if(step_fd>=0)(void)sys_close((int)step_fd);(void)sys_close(pipe_fds[0]);(void)sys_close(pipe_fds[1]);return step_fd<0?step_fd:-P260_EPROTO;}\n    long pid = sys_clone();')
    once(b'    if (pid < 0) {',b'    if (pid < 0) {\n        if(step_fd>=0)(void)sys_close((int)step_fd);')
    old=b'''        long null_fd = sys_openat("/dev/null", O_RDONLY | O_CLOEXEC, 0);
        if (null_fd < 0 || p328_dup_to((int)null_fd, 0) != 0) sys_exit(126);
        if (null_fd != 0) (void)sys_close((int)null_fd);'''
    new=b'''        long input_fd=pstep_display?step_fd:sys_openat("/dev/null",O_RDONLY|O_CLOEXEC,0);
        if(input_fd<0 || p328_dup_to((int)input_fd,0)!=0)sys_exit(126);
        if(input_fd!=0)(void)sys_close((int)input_fd);
        /* Never F_SETFL on eventfd: O_NONBLOCK belongs to the shared description. */'''
    once(old,new)
    once(b'    control.retained_pid=pid;',b'    control.step_fd=(int)step_fd;\n    control.retained_pid=pid;')
    once(b'            (void)p328_cleanup_process_group(pid);\n            return rc;',b'            (void)p328_cleanup_process_group(pid);\n            if(step_fd>=0)(void)sys_close((int)step_fd);\n            return rc;')
    once(b'            (void)sys_close(pipe_fds[0]);(void)p328_cleanup_process_group(pid);return rc;',b'            (void)sys_close(pipe_fds[0]);(void)p328_cleanup_process_group(pid);\n            if(step_fd>=0)(void)sys_close((int)step_fd);\n            return rc;')
    once(b'    (void)sys_close(pipe_fds[0]);\n    long group_cleanup = p328_cleanup_process_group(pid);',b'    (void)sys_close(pipe_fds[0]);\n    if(step_fd>=0)(void)sys_close((int)step_fd);\n    long group_cleanup = p328_cleanup_process_group(pid);')
    for result,name in ((b'int',b'swap_line'),(b'int',b'wait_line'),(b'long',b'note_wait'),
                        (b'long',b'sample_wait'),(b'long',b'wait_checkpoint'),
                        (b'long',b'status_reply'),(b'long',b'child_output')):
        value=_replace_function(value,b'static '+result+b' '+prefix+b'_'+name+b'(',b'')
    return value

P345_HELPER_TEMPLATE=P345_HELPER=build_helper()
globals()[_STEP_PREFIX.upper()+'_HELPER_TEMPLATE']=P345_HELPER_TEMPLATE
globals()[_STEP_PREFIX.upper()+'_HELPER']=P345_HELPER_TEMPLATE
_step_audit=audit_binding

def audit_binding(*,child=None):
    value=_step_audit(child=child)
    value.pop('wait_checkpoint',None);value.pop('wait_observation_interval_sec',None)
    value.update(status_sample='requested-started-completed-failed-child-and-native-interval',
        step_checkpoint='signed-step-state-at-control')
    value.update(control_sequence=14,status_response_bytes=12,step_maximum=_STEP_MAX,
        step_exit_before_completion=_STEP_EXIT,step_sequences=list(range(11,11+_STEP_MAX)),
        step_channel='eventfd-nonblocking-one-pending',step_ack_scope='queued-only',
        step_completion='exact-child-marker',control_independent_of_step_completion=True)
    return value
