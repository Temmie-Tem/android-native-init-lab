"""P364 diagnostic successor; source-bound H0 capability only."""
from s22plus_fyg8_p364_namespace import load
load(globals())

DIAGNOSTIC_SOURCE = ROOT / 'workspace/public/src/native-init/s22plus_native_return_diagnostics_v1.inc.c'
_p364_base_exec = _exec_function
_p364_base_console = _console_function


def _exec_function(value):
    value = _p364_base_exec(value).replace(b'p363',b'p364').replace(b'P363',b'P364')
    value = _replace_function(value,b'static long p364_insert_module(',DIAGNOSTIC_SOURCE.read_bytes())
    value = _once(value,b'        long preparation = p364_prepare_return();',
        b'        long preparation = p364_diag_start(tty_fd,nonce);\n'
        b'        if (preparation == 0) preparation = p364_prepare_return();')
    value = _once(value,b'static long p364_prepare_return(void) {',
        b'static long p364_prepare_return(void) {\n'
        b'    long entered=p364_diag_enter(1U);if(entered!=0)return entered;')
    value = _once(value,b'            rc=p364_nvmem_providers();',
        b'            rc=p364_diag_enter(30U);\n'
        b'            if(rc==0)rc=p364_diag_result(30U,p364_nvmem_providers());')
    value = _replace_function(value,b'static long p364_verify_reboot_registry(',b'''
static long p364_verify_reboot_registry(void) {
    long rc=p364_diag_enter(31U);if(rc!=0)return rc;
    rc=p364_diag_result(31U,sys_mount("debugfs","/sys/kernel/debug","debugfs",15UL,NULL));
    if(rc!=0)return rc;
    rc=p364_diag_enter(32U);if(rc!=0)return rc;
    struct timespec64 deadline={0};
    rc=p282_deadline_after(5LL,&deadline);
    if(rc!=0)return p364_diag_result(32U,rc);
    for(;;) {
        if(p282_deadline_expired(&deadline))return p364_diag_result(32U,-ETIMEDOUT);
        rc=p364_read_reboot_registry();
        if(rc==0)return p364_diag_result(32U,0);
        if(rc!=-P260_EPROTO && rc!=-ENOENT)return p364_diag_result(32U,rc);
        p282_poll_delay();
    }
}
''')
    value = _once(value,b'''    long rc=p241_newfstatat("/sys/bus/platform/drivers/samsung,qcom-qcom_reboot_reason/soc:samsung,qcom-qcom_reboot_reason",&metadata,0);
    if(rc!=0 || (metadata.st_mode&0170000U)!=0040000U) return rc?rc:-P260_EPROTO;
    return 0;''',b'''    long rc=p364_diag_enter(33U);if(rc!=0)return rc;
    rc=p241_newfstatat("/sys/bus/platform/drivers/samsung,qcom-qcom_reboot_reason/soc:samsung,qcom-qcom_reboot_reason",&metadata,0);
    if(rc==0 && (metadata.st_mode&0170000U)!=0040000U)rc=-P260_EPROTO;
    rc=p364_diag_result(33U,rc);if(rc!=0)return rc;
    return p364_diag_result(1U,0);''')
    value = _once(value,b'    long rc = sys_pipe2(pipe_fds, O_CLOEXEC | O_NONBLOCK);',
        b'    long rc = p364_display ? p364_diag_enter(40U) : 0;\n'
        b'    if(rc!=0)return rc;\n'
        b'    rc = sys_pipe2(pipe_fds, O_CLOEXEC | O_NONBLOCK);\n'
        b'    if(p364_display)rc=p364_diag_result(40U,rc);')
    value = _once(value,b'    if (rc != 0) return rc;\n    struct timespec64 started = {0};',
        b'    if (rc != 0) {\n'
        b'        if(pipe_fds[0]>=0)(void)sys_close(pipe_fds[0]);\n'
        b'        if(pipe_fds[1]>=0)(void)sys_close(pipe_fds[1]);\n'
        b'        return rc;\n    }\n'
        b'    struct timespec64 started = {0};')
    value = _once(value,b'    rc = p241_clock_gettime(&started);',
        b'    rc = p364_display ? p364_diag_enter(41U) : 0;\n'
        b'    if(rc==0) {\n'
        b'        rc=p241_clock_gettime(&started);\n'
        b'        if(p364_display)rc=p364_diag_result(41U,rc);\n'
        b'    }')
    value = _once(value,b'    long pid = sys_clone();',b'''    if(p364_display) {
        rc=p364_diag_enter(42U);
        if(rc!=0){(void)sys_close(pipe_fds[0]);(void)sys_close(pipe_fds[1]);return rc;}
    }
    long pid = sys_clone();''')
    value = _once(value,b'    if (pid < 0) {\n',
        b'    if (pid < 0) {\n        if(p364_display)(void)p364_diag_result(42U,pid);\n')
    value = _once(value,b'    (void)sys_close(pipe_fds[1]);\n\n    struct timespec64 deadline',b'''    if(p364_display) {
        rc=p364_diag_result(42U,0); /* Child created, not exec success. */
        if(rc!=0) {
            (void)sys_kill(pid,SIGKILL);
            int cleanup_status=0;
            (void)p328_reap_after_kill(pid,&cleanup_status);
            (void)sys_close(pipe_fds[0]);(void)sys_close(pipe_fds[1]);
            (void)p328_cleanup_process_group(pid);
            return rc;
        }
    }
    (void)sys_close(pipe_fds[1]);

    struct timespec64 deadline''')
    value = _once(value,b'''        if (p364_display) {
            if (!control.ready''',b'''        if (p364_display) {
            if(reaped) {rc=p364_diag_child_status(status);if(rc!=0)break;}
            if (!control.ready''')
    value = _once(value,b'    if (rc != 0 && !reaped) {',
        b'    if(p364_display && rc<0 && !p364_diagnostic.first_error)p364_diagnostic.first_error=rc;\n'
        b'    if (rc != 0 && !reaped) {')
    value = _once(value,b'    if (p364_display) return -P260_EPROTO;',
        b'    if (p364_display) return timeout_attempted ? -ETIMEDOUT : -P260_EPROTO;')
    value = _once(value,b'    state->consumed=1U; /* Before ACK and every privileged effect. Never reset. */',
        b'    state->consumed=1U; /* Before ACK and every privileged effect. Never reset. */\n'
        b'    p364_diagnostic.terminal=1; /* Progress ends before CONTROL ACK. */')
    return value


def _console_function(value):
    value = _p364_base_console(value)
    anchor=b'''                for (;;) p282_poll_delay();
            }
            if (rc != 0) return rc;'''
    return _once(value,anchor,b'''                p364_diag_finish(rc);
                for (;;) p282_poll_delay();
            }
            if (rc != 0) return rc;''')


P345_HELPER_TEMPLATE = P345_HELPER = build_helper()
P364_HELPER_TEMPLATE = P364_HELPER = P345_HELPER_TEMPLATE
_p364_base_audit = audit_binding


def audit_binding(*,child=None):
    value=_p364_base_audit(child=child)
    value.update(authenticated_progress=True,diagnostic_frame_type=return_spec.FRAME_DIAGNOSTIC,
        diagnostic_max_frames=return_spec.MAX_DIAGNOSTIC_FRAMES,
        diagnostic_stage_count=len(return_spec.STAGES),diagnostic_write_deadline_sec=60,
        preparation_error_reported_before_park=True,renderer_binary_unchanged=True)
    return value
