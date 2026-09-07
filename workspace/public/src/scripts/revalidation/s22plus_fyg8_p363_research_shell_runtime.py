"""P363 sealed successor binding; no device authority."""
from s22plus_fyg8_p363_namespace import load
load(globals())

from pathlib import Path
import s22plus_fyg8_p363_return_spec as return_spec

ROOT = return_spec.ROOT
CONTROL_SOURCE = ROOT / 'workspace/public/src/native-init/s22plus_native_return_control_v1.inc.c'
MODULE_SOURCE = ROOT / 'workspace/public/src/native-init/s22plus_native_return_modules_v1.inc.c'
AUTH_DOMAIN_BOOT_ID = b'S22PLUS-FYG8-P363-AUTH-KERNEL-BOOT-ID-v2'
_return_base_exec = _exec_function


def _exec_function(value):
    value = _return_base_exec(value)
    helper = return_spec.render_module_table() + MODULE_SOURCE.read_bytes() + b'\n' + CONTROL_SOURCE.read_bytes()
    anchor = b'static unsigned int p363_display_consumed;'
    value = _once(value, anchor, helper + b'\n' + anchor)
    value = _once(value,
        b'        p363_display_consumed = 1U;\n',
        b'        p363_display_consumed = 1U;\n'
        b'        long preparation = p363_prepare_return();\n'
        b'        if (preparation != 0) return preparation;\n')
    value = _once(value, b'    uint8_t output[P328_MAX_PAYLOAD];\n',
        b'    uint8_t output[P328_MAX_PAYLOAD];\n'
        b'    struct p363_control_state control = {0};\n')
    value = _once(value, b'            uint32_t allowed = (uint32_t)amount;',
        b'            if (p363_display) {\n'
        b'                rc = p363_child_output(&control, output, (size_t)amount);\n'
        b'                if (rc != 0) break;\n'
        b'            }\n'
        b'            uint32_t allowed = (uint32_t)amount;')
    anchor = b'        if (!p363_display && sequence == P345_CANCEL_SEQUENCE\n'
    value = _once(value, anchor, b'''        if (p363_display) {
            if (!control.ready && (control.swaps == 10U || reaped)) {
                control.child_exited = reaped ? 1U : 0U;
                const uint8_t ready[4] = {P363_LIVE_MODE,(uint8_t)control.swaps,1U,
                    (uint8_t)control.child_exited};
                rc = p363_write_status(tty_fd,P363_FRAME_CONTROL_READY,
                    p363_ready_domain,nonce,ready,&deadline);
                if (rc != 0) break;
                control.ready = 1U;
            }
            rc = p363_try_control(&control,tty_fd,nonce,&deadline);
            if (rc != 0) break;
        }
''' + anchor)
    value = _once(value, b'\n        if (reaped) {\n', b'\n        if (reaped && !p363_display) {\n')
    value = _once(value, b'            timeout_attempted = 1;\n',
        b'            if (p363_display && reaped) { rc = -ETIMEDOUT; break; }\n'
        b'            timeout_attempted = 1;\n')
    old_domain = b'"S22PLUS-FYG8-P335-AUTH-BOOT-ID-v1"'
    value = _once(value, old_domain, b'"' + AUTH_DOMAIN_BOOT_ID + b'"')
    value = _replace_function(value, b'static long p335_getrandom_boot_id(', b'''
static long p335_getrandom_boot_id(uint8_t boot_id[P335_BOOT_ID_SIZE]) {
    _Static_assert(P335_BOOT_ID_SIZE == 32U, "kernel UUID SHA256 wire size");
    return p363_kernel_boot_id(boot_id);
}
''')
    return value


P345_HELPER_TEMPLATE = P345_HELPER = build_helper()
P363_HELPER_TEMPLATE = P363_HELPER = P345_HELPER_TEMPLATE
_return_base_audit = audit_binding


def audit_binding(*, child=None):
    value = _return_base_audit(child=child)
    value.update(display_post_dispatch_tty_io=True,
        display_output_capture='bounded-parent-lines-reduced-to-submitted-swap-count',
        display_machine_proof='authenticated-submission-count-and-control-acceptance',
        kernel_boot_id_semantic=return_spec.BOOT_ID_SEMANTIC,
        kernel_boot_id_auth_domain=AUTH_DOMAIN_BOOT_ID.decode(),
        control_mode='download', control_sequence=return_spec.CONTROL_SEQUENCE,
        control_owner='native-PID1-supervisor', control_ordinary_restart_live=False,
        control_replay_forbidden=True, control_syscall_maximum=1,
        control_ack_scope='acceptance-only', control_ack_write_failure='consume-without-syscall',
        return_modules=[dict(name=n,size=s,sha256=h,parameters=p) for n,s,h,p in return_spec.MODULES],
        dump_mode_initialization='NODUMP-then-Samsung-writer-FULLDUMP-window',
        return_recovery='attended-physical-Download-exact-Magisk-rollback',
        automatic_recovery_proved=False)
    return value
