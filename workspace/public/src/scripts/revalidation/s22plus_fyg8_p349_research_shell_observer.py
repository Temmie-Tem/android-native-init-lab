#!/usr/bin/env python3
"""P349 bounded RAM-workspace successor; retained P348 template is immutable."""
from pathlib import Path
import hashlib
TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p348_research_shell_observer.py')
TEMPLATE_IDENTITY = {"size": 22531, "sha256": 'e4b9d45f0050b0b97985e98ab09bc21441177b088d870f055cec2fad7ef76b42'}
_template = TEMPLATE_SOURCE.read_bytes()
if {"size": len(_template), "sha256": hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError("P349 template identity differs")
_template = _template.replace(b"P348", b"P349").replace(b"p348", b"p349")
_template = _template.replace(b"readonly_research_shell", b"ram_workspace_research_shell")
exec(compile(_template, str(TEMPLATE_SOURCE) + "#p349", "exec"), globals())

# Initial qualification retains the root-write denial canary. The bounded
# writable mount is proved separately across fresh later command children.
def _success(command, output):
    return {"command": command, "outcome": "ok", "middle": {
        "output": output, "flags": 0, "exit_code": 0, "signal_number": 0}}

_original_acceptance = LATER_ACCEPTANCE_COMMANDS
LATER_ACCEPTANCE_COMMANDS = {
    "checked-snapshot": _original_acceptance["checked-snapshot"],
    "ram-create": _success(
        b"/bin/busybox mkdir /work/research && printf 'one\\n' >/work/research/value && printf 'P349-RAM-CREATED\\n'",
        b"P349-RAM-CREATED\n"),
    "ram-modify": _success(
        b"test \"$(/bin/busybox cat /work/research/value)\" = one && printf 'two\\n' >/work/research/value && /bin/busybox mv /work/research/value /work/research/retained && printf 'P349-RAM-MODIFIED\\n'",
        b"P349-RAM-MODIFIED\n"),
    "ram-script": _success(
        b"printf 'test \"$(/bin/busybox cat /work/research/retained)\" = two || exit 81\\nprintf \"P349-RAM-SCRIPT\\\\n\"\\n' >/work/research/program.sh && /bin/busybox ash /work/research/program.sh",
        b"P349-RAM-SCRIPT\n"),
    "known-nonzero": _original_acceptance["known-nonzero"],
    "timeout": _original_acceptance["timeout"],
    "active-cancel": _original_acceptance["active-cancel"],
    "post-cancel-success": _original_acceptance["post-cancel-success"],
}
LONGEVITY_SECONDS = {"witness-20min": 1200, "witness-40min": 2400, "witness-60min": 3600}
for _role, _seconds in LONGEVITY_SECONDS.items():
    _marker = ("P349-" + _role.upper() + "\n").encode("ascii")
    LATER_ACCEPTANCE_COMMANDS[_role] = _success(
        b'test "$(/bin/busybox cat /work/research/retained)" = two && '
        + b"printf '" + _marker.rstrip(b"\n") + b"\\n'", _marker)
