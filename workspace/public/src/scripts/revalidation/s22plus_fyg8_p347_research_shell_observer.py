#!/usr/bin/env python3
"""P347 numeric-witness qualification using the reviewed five-session observer."""
from pathlib import Path
import hashlib

TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p345_research_shell_observer.py')
TEMPLATE_IDENTITY = {"size": 42606, "sha256": "7d24a1ae005ef07235a45a8c24256ae3fcf1ba4972620868730318b6b51a1b12"}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P347 source template identity differs")
_template = _template.replace(b'import s22plus_fyg8_p345_research_shell_runtime as runtime',
                              b'import s22plus_fyg8_p347_research_shell_runtime as runtime')
_template = _template.replace(b's22plus-fyg8-p345-research-shell-qualification',
                              b's22plus-fyg8-p347-research-shell-qualification')
# Fixed P345 canary/CANCEL markers are protocol vocabulary, not run identity.
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p347", "exec"), globals())


# Keep five sessions and the inherited frame/marker vocabulary. Command texts
# and full output identities are fresh capability inputs, never P346 evidence.
CANARY_COMMAND = (
    b"printf 'P345-UID='; /bin/busybox id -u || exit 71; "
    b"printf 'P345-GID='; /bin/busybox id -g || exit 72; "
    b"/bin/busybox cat /proc/uptime || exit 73; "
    b"if ( : >/probe ); then printf 'P345-PROBE-CREATED\\n'; "
    b"else printf 'P345-PROBE-DENIED\\n'; fi; "
    b"if test ! -e /probe; then printf 'P345-PROBE-ABSENT\\n'; "
    b"else printf 'P345-PROBE-PRESENT\\n'; fi; "
    b"printf 'P345-CANARY\\n'"
)
PIPELINE_MARKER = b"x\n" * 60000 + b"P345-PIPE-MARKER\n"
PIPELINE_COMMAND = (
    b"v=$(/bin/busybox cat /proc/version) || exit 74; "
    b"test -n \"$v\" || exit 75; "
    b"/bin/busybox awk 'BEGIN {for(i=0;i<60000;i++) print \"x\"}' || exit 76; "
    b"printf 'P345-PIPE-%s\\n' \"$(printf marker)\" | /bin/busybox tr a-z A-Z"
)
QUALIFICATION_COMMANDS = (
    QualificationStep(1, "readonly-canary", CANARY_COMMAND, "ok"),
    QualificationStep(2, "expected-command-failure", EXIT7_COMMAND, "command-failed"),
    QualificationStep(3, "command-timeout", TIMEOUT_COMMAND, "timeout"),
    QualificationStep(4, "authenticated-cancel", CANCEL_COMMAND, "cancelled"),
    QualificationStep(5, "post-cancel-pipeline", PIPELINE_COMMAND, "ok"),
)

_base_validate_command_results = _validate_command_results

def _validate_command_results(step, session, shell_result):
    result = _base_validate_command_results(step, session, shell_result)
    if step.ordinal == 3 and session.commands[1].duration_ms < 15000:
        raise QualificationError("P347 timeout duration is shorter than its bound")
    return result

_base_validate_qualification = validate_qualification

def validate_qualification(value):
    result = _base_validate_qualification(value)
    if result["sessions"][2]["commands"][1]["duration_ms"] < 15000:
        raise QualificationError("P347 retained timeout duration is shorter than its bound")
    return result
