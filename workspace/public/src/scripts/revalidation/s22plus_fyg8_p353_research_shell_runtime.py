"""P353 fresh H0 namespace over the sealed P351 template; no device authority."""
from pathlib import Path
import ast
import hashlib

P351_TEMPLATE = Path(__file__).with_name('s22plus_fyg8_p351_research_shell_runtime.py')
P351_TEMPLATE_SHA = '59f333342213863f97f084f658588b40bb44060e675f09bf1c5d289367b99200'
_source = P351_TEMPLATE.read_bytes()
if hashlib.sha256(_source).hexdigest() != P351_TEMPLATE_SHA:
    raise ValueError("P353 predecessor template identity differs")
_source = _source.replace(b'P351', b'P353').replace(b'p351', b'p353')
_source = _source.replace(b'c351f1e0a90b5e6d7c8a9b0c1d2e3f0b', b'c353f1e0a90b5e6d7c8a9b0c1d2e3f0b')
_tree = ast.parse(_source)
_tree.body = [n for n in _tree.body if not (isinstance(n, ast.If) and '__name__' in ast.unparse(n.test))]
exec(compile(ast.fix_missing_locations(_tree), str(P351_TEMPLATE) + '#p353', 'exec'), globals())

# The display branch is a one-way attended action after authenticated EXEC.
# Its child lifetime must not depend on host tty closure or DATA backpressure.
_p353_inherited_exec = _exec_function


def _exec_function(value):
    value = _p353_inherited_exec(value)
    old = b'''                rc = p328_write_frame(
                    tty_fd, P328_FRAME_DATA, sequence, output,
                    (uint16_t)allowed);
                if (rc != 0) break;'''
    new = b'''                if (!p353_display) {
                    rc = p328_write_frame(
                        tty_fd, P328_FRAME_DATA, sequence, output,
                        (uint16_t)allowed);
                    if (rc != 0) break;
                } /* fixed display: bounded local drain, no post-dispatch TX */'''
    value = _once(value, old, new)
    value = _once(value,
        b'        if (sequence == P345_CANCEL_SEQUENCE\n            && !cancelled && !late_cancel)',
        b'        if (!p353_display && sequence == P345_CANCEL_SEQUENCE\n            && !cancelled && !late_cancel)')
    value = _once(value, b'    if (cancelled) flags |= P345_CANCELLED_FLAG;',
        b'''    /* No EXIT, next command or CLOSE exchange for the display action.
     * The one-shot slot stays consumed even after child failure or timeout. */
    if (p353_display) return -P260_EPROTO;
    if (cancelled) flags |= P345_CANCELLED_FLAG;''')
    return value


_p353_inherited_console = _console_function


def _console_function(value):
    value = _p353_inherited_console(value)
    anchor = b'''                nonce, &p345_cancel_status);
            if (rc != 0) return rc;'''
    return _once(value, anchor, b'''                nonce, &p345_cancel_status);
            /* The authenticated fixed action terminates this console even
             * when child setup failed. Never enter another session/listener
             * or the generic error publisher after this one-way dispatch. */
            if (sequence == P345_CANCEL_SEQUENCE
                && command_length == sizeof("P353_DISPLAY_ONCE") - 1U
                && p260_bytes_equal((const char *)command, "P353_DISPLAY_ONCE", command_length)) {
                for (;;) p282_poll_delay();
            }
            if (rc != 0) return rc;''')


P345_HELPER_TEMPLATE = P345_HELPER = build_helper()
P353_HELPER_TEMPLATE = P353_HELPER = P345_HELPER_TEMPLATE
_p353_inherited_audit = audit_binding


def audit_binding(*, child=None):
    value = _p353_inherited_audit(child=child)
    value.update(display_post_dispatch_tty_io=False,
        display_output_capture='none-local-pipe-drained',
        display_cancel_supported=False, display_timeout_seconds=60,
        display_machine_proof='authenticated-request-dispatch-only',
        display_visual_proof='operator-observation', display_cleanup_proof_required=False,
        post_display_usb_required=False)
    return value
