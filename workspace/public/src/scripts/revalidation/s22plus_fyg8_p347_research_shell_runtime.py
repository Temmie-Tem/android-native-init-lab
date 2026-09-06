#!/usr/bin/env python3
"""P347 checked output backpressure and versioned read-only child; same CANCEL ABI."""
from pathlib import Path
import hashlib

TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p345_research_shell_runtime.py')
TEMPLATE_IDENTITY = {"size": 40666, "sha256": "eab728141657d1d0fa11b4ce5affc7d42426927331c6bdd6500079a1842911d7"}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P347 source template identity differs")
_template = _template.replace(b"s22plus_fyg8_p345_readonly_child",
                              b"s22plus_fyg8_readonly_child_v2")
_template = _template.replace(
    b'P345_RUN_ID_HEX = "c345f1e0a90b5e6d7c8a9b0c1d2e3f0a"',
    b'P345_RUN_ID_HEX = "c347f1e0a90b5e6d7c8a9b0c1d2e3f0a"', 1)
_template = _template.replace(b's22plus-fyg8-p345-readonly-research-shell-runtime-v1',
                              b's22plus-fyg8-p347-readonly-research-shell-runtime-v1')
# Execute before derived constants/defaults/helper construction. Parent globals
# remain untouched; P345-labelled C and CANCEL ABI are deliberately preserved.
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p347", "exec"), globals())
for _name, _value in tuple(globals().items()):
    if _name.startswith("P345_"):
        globals()[_name.replace("P345_", "P347_", 1)] = _value
validate_p347_runtime = validate_p345_runtime
P345_CONSUMED_RUN_ID_HEX = "c345f1e0a90b5e6d7c8a9b0c1d2e3f0a"


_base_exec_function = _exec_function

def _exec_function(value):
    value = _base_exec_function(value)
    anchor = b"        if (p328_setsid() < 0) sys_exit(126);\n"
    if value.count(anchor) != 1:
        raise RuntimeIdentityError("P347 child output setup seam differs")
    # AArch64 fcntl=25, F_SETFL=4. Only the new pipe's write end changes;
    # parent reads stay nonblocking. CLOEXEC is a descriptor flag, untouched.
    replacement = anchor + (
        b"        if (syscall6(25, pipe_fds[1], 4, 0, 0, 0, 0) < 0)\n"
        b"            sys_exit(126);\n"
    )
    value = value.replace(anchor, replacement, 1)
    exec_anchor = b'        (void)sys_execve("/bin/busybox", argv, envp);'
    if value.count(exec_anchor) != 1:
        raise RuntimeIdentityError("P347 ash option seam differs")
    return value.replace(exec_anchor, (
        b'        char *const readonly_argv[] = {\n'
        b'            (char *)"/bin/busybox", (char *)"ash",\n'
        b'            (char *)"-o", (char *)"pipefail", (char *)"-c", command, NULL,\n'
        b'        };\n'
        b'        (void)sys_execve("/bin/busybox",\n'
        b'            sequence == P345_CANCEL_SEQUENCE ? readonly_argv : argv, envp);'
    ), 1)

# Recompute derived source after installing the checked transform. All callers
# materialize through build_helper and receive this exact implementation.
P345_HELPER_TEMPLATE = P345_HELPER = build_helper()
P347_HELPER_TEMPLATE = P347_HELPER = P345_HELPER_TEMPLATE
