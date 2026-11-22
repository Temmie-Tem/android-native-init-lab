"""The fixed marker read and its host-side evidence check, without a transport."""

import hashlib
import re
import shlex


MARKER_PATH = "/sys/firmware/devicetree/base/chosen/codex,y2q-uniloader-android-v1"
ADB = "/usr/lib/android-sdk/platform-tools/adb"
READ_SECONDS = 10
STDOUT_MAXIMUM = 111  # boot_id=<UUID>\n plus at most 66 property bytes
STDERR_MAXIMUM = 1024
ABSENT_RC = 44
READ_SCRIPT = f"""set -eu
property={MARKER_PATH}
chosen=${{property%/*}}
printf 'boot_id='
/system/bin/cat /proc/sys/kernel/random/boot_id
[ -d "$chosen" ] && [ -r "$chosen" ] && [ -x "$chosen" ] || exit 45
[ ! -L "$property" ] || exit 45
[ -e "$property" ] || exit {ABSENT_RC}
[ -f "$property" ] && [ -r "$property" ] || exit 45
exec /system/bin/head -c 66 "$property"
"""
IDENTITY = ("serial_sha256", "topology_sha256", "boot_id_sha256")
HEX64 = re.compile(r"[0-9a-f]{64}")
UUID_LINE = re.compile(rb"boot_id=([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})")


def marker_argv(serial):
    """The reviewed owner must supply the serial from its exact target binding."""
    if not isinstance(serial, str) or not serial or any(c.isspace() for c in serial):
        raise ValueError("exact selected serial is required")
    return [ADB, "-s", serial, "shell", "-T", "su", "-c", shlex.quote(READ_SCRIPT)]


def marker_digest(marker):
    if not isinstance(marker, str) or HEX64.fullmatch(marker) is None:
        raise ValueError("invalid loader marker")
    return hashlib.sha256(marker.encode("ascii") + b"\0").hexdigest()


def classify_marker(returncode, stdout, stderr, *, expected_marker_sha256, expected_boot_sha256):
    """Classify bounded bytes after the owner checks the captured producer result."""
    if (type(returncode) is not int or type(stdout) is not bytes or type(stderr) is not bytes
            or len(stdout) > STDOUT_MAXIMUM or stderr):
        return "UNAVAILABLE"
    header, separator, payload = stdout.partition(b"\n")
    boot_id = UUID_LINE.fullmatch(header)
    if not separator or boot_id is None:
        return "UNAVAILABLE"
    if hashlib.sha256(boot_id[1]).hexdigest() != expected_boot_sha256:
        return "BOOT_CHANGED"
    if returncode == ABSENT_RC and not payload:
        return "ABSENT"
    if returncode != 0 or re.fullmatch(rb"[0-9a-f]{64}\x00", payload) is None:
        return "UNAVAILABLE"
    if hashlib.sha256(payload).hexdigest() == expected_marker_sha256:
        return "MATCH"
    return "DIFFERENT"


def observe_marker(before, after, result, *, expected_marker_sha256, preflight, prior_boots):
    """Bind marker data to two already validated health receipts from the same run.

    The owner validates the full Magisk health receipts and raw capture provenance.
    This function gives neither rollback authority nor transfer proof.
    """
    if any(not isinstance(before.get(key), str) or HEX64.fullmatch(before[key]) is None
           or before[key] != after.get(key) for key in IDENTITY):
        return "HEALTH_BINDING_CHANGED"
    if (any(before[key] != preflight.get(key) for key in IDENTITY[:2])
            or before["boot_id_sha256"] == preflight.get("boot_id_sha256")
            or before["boot_id_sha256"] in prior_boots):
        return "HEALTH_BINDING_CHANGED"
    return classify_marker(*result, expected_marker_sha256=expected_marker_sha256,
                           expected_boot_sha256=before["boot_id_sha256"])
