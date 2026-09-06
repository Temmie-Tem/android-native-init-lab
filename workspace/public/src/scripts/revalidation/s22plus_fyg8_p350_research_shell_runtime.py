#!/usr/bin/env python3
"""Fresh P350 fixed display child over the retained P347 protocol implementation.

The ordinary command path remains the read-only P347 child. Only one exact
sequence-4 literal selects the fixed display executable. Its boot-local slot is
consumed before pipe/fork; no arbitrary command text reaches that executable.
"""
from pathlib import Path
import hashlib

TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p347_research_shell_runtime.py')
TEMPLATE_IDENTITY = {'size': 2996, 'sha256': '6323898af8af5a5eb26776e38682f9851b5e9af505ef11b5c5b1b7938baaef69'}
_template = TEMPLATE_SOURCE.read_bytes()
if {'size': len(_template), 'sha256': hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError('P350 protocol template identity differs')
_template = _template.replace(b'P347', b'P350').replace(b'p347', b'p350')
_template = _template.replace(b'c347f1e0a90b5e6d7c8a9b0c1d2e3f0a', b'c350f1e0a90b5e6d7c8a9b0c1d2e3f0a')
exec(compile(_template, str(TEMPLATE_SOURCE) + '#p350', 'exec'), globals())

DISPLAY_COMMAND = b'P350_DISPLAY_ONCE'
DISPLAY_TIMEOUT_SECONDS = 60
_base_display_exec = _exec_function


def _once(value, old, new):
    if value.count(old) != 1:
        raise RuntimeIdentityError('P350 fixed display transform seam differs')
    return value.replace(old, new, 1)


def _exec_function(value):
    value = _base_display_exec(value)
    value = _once(value, b'static long p345_exec_command(',
        b'static unsigned int p350_display_consumed;\n\nstatic long p345_exec_command(')
    anchor = b'    command[input_length] = \'\\0\';\n'
    value = _once(value, anchor, anchor + b'''
    int p350_display = sequence == P345_CANCEL_SEQUENCE
        && input_length == sizeof("P350_DISPLAY_ONCE") - 1U
        && p260_bytes_equal(command, "P350_DISPLAY_ONCE", input_length);
    if (p350_display) {
        if (p350_display_consumed) return -P260_EPROTO;
        p350_display_consumed = 1U;
    }
''')
    anchor = b'        (void)sys_close(tty_fd);\n        if (sequence == P345_CANCEL_SEQUENCE) {'
    replacement = b'''        (void)sys_close(tty_fd);
        if (p350_display) {
            if (p345_close_extra_fds() != 0 || p345_apply_limits() != 0)
                sys_exit(126);
            char display_id[33];
            static const char hex[] = "0123456789abcdef";
            for (unsigned int i = 0U; i < 16U; ++i) {
                display_id[2U * i] = hex[p328_run_id_bytes[i] >> 4];
                display_id[2U * i + 1U] = hex[p328_run_id_bytes[i] & 15U];
            }
            display_id[32] = 0;
            char *const display_argv[] = {
                (char *)"/s22-display", (char *)"--supervised-drm",
                display_id, NULL,
            };
            char *const display_env[] = {(char *)"PATH=/bin", NULL};
            (void)sys_execve("/s22-display", display_argv, display_env);
            sys_exit(127);
        }
        if (sequence == P345_CANCEL_SEQUENCE) {'''
    value = _once(value, anchor, replacement)
    value = _once(value, b'    deadline.tv_sec += P328_COMMAND_TIMEOUT_SEC;',
        b'    deadline.tv_sec += p350_display ? 60LL : P328_COMMAND_TIMEOUT_SEC;')
    return value


P345_HELPER_TEMPLATE = P345_HELPER = build_helper()
P350_HELPER_TEMPLATE = P350_HELPER = P345_HELPER_TEMPLATE
CONTRACT_ID = 's22plus-fyg8-p350-display-once-runtime-v1'
_base_audit = audit_binding


def audit_binding(*, child=None):
    result = _base_audit(child=child)
    result.update(display_command=DISPLAY_COMMAND.decode(),
        display_timeout_seconds=DISPLAY_TIMEOUT_SECONDS,
        display_slot='boot-local-one-shot-consumed-before-fork',
        display_executable='/s22-display',
        display_child_privilege='fixed-module-load-and-drm-open-then-uid65534-no-caps',
        display_initial_inputs='current-boot-primary-panel-parameters',
        normal_middle_command_readonly=True, sequence_4_readonly_child=False,
        arbitrary_root_shell=False,
        runtime_behavior_unchanged=False, device_contact=False)
    return result
