"""Make and parse a bounded first-return probe. This module has no device transport."""

import hashlib
import re
import shlex
from pathlib import Path

STAGES = ("fdt", "unflatten")

CAPACITY = 2097136
FILTER = Path(__file__).resolve().with_name("return-stage.awk")


def frames(nonce):
    if len(nonce) != 32 or any(c not in "0123456789abcdef" for c in nonce):
        raise ValueError("invalid witness identifier")
    records = {}
    for stage in STAGES:
        label = f"Y2QLOG1|linux-6.18|{stage}|{nonce}|".encode("ascii")
        check = hashlib.sha256(label).hexdigest().encode("ascii")
        records[stage] = (label + check).ljust(127, b".") + b"\n"
    return records


def shell(nonce, boot_digest):
    if not re.fullmatch(r"[0-9a-f]{64}", boot_digest):
        raise ValueError("invalid restored boot digest")
    expected = frames(nonce)
    return f"""set -eu
set -o pipefail
export LC_ALL=C
test "$(/system/bin/id -u)" = 0
test "$(/system/bin/getprop ro.product.model)" = SM-G986N
test "$(/system/bin/getprop ro.product.device)" = y2q
test "$(/system/bin/getprop ro.product.name)" = y2qksx
test "$(/system/bin/getprop ro.build.version.incremental)" = G986NKSS8IYC2
test "$(/system/bin/getprop sys.boot_completed)" = 1
test "$(/system/bin/getenforce)" = Enforcing
same_boot() {{
    boot=$(/system/bin/cat /proc/sys/kernel/random/boot_id) || return 1
    hash=$(/system/bin/printf '%s' "$boot" | /system/bin/sha256sum) || return 1
    test "${{hash%% *}}" = {boot_digest}
}}
same_boot || exit 4
scan() {{
node=/proc/last_kmsg
if [ ! -e "$node" ]; then echo y2q_log_missing; return 0; fi
test ! -L "$node" && test -f "$node" || exit 4
test "$(/system/bin/readlink -f "$node")" = "$node" || exit 4
test "$(/system/bin/stat -f -c %t "$node")" = 9fa0 || exit 4
if [ ! -r "$node" ]; then echo y2q_log_unreadable; return 0; fi
length=$(/system/bin/stat -c %s "$node") || exit 4
case "$length" in ''|*[!0-9]*) exit 4;; esac
test "$length" -le {CAPACITY} || exit 4
bb=/data/adb/magisk/busybox
test -x "$bb" && test -f "$bb" && test ! -L "$bb" || exit 4
test "$(/system/bin/readlink -f "$bb")" = "$bb" || exit 4
test "$(/system/bin/stat -c %s "$bb")" = 1710600 || exit 4
got=$(/system/bin/sha256sum "$bb") || exit 4
test "${{got%% *}}" = 4d60ab3f5a59ebb2ca863f2f514e6924401b581e9b64f602665c008177626651 || exit 4
/system/bin/od -An -v -tx1 -N {CAPACITY + 1} "$node" | "$bb" awk -v expected="$length" -v first={expected["fdt"].hex()} -v second={expected["unflatten"].hex()} {shlex.quote(FILTER.read_text("ascii"))}
}}
result=$(scan) || exit 4
same_boot || exit 4
/system/bin/printf '%s\\n' "$result"
"""


def parse(rc, stdout, stderr):
    if rc or stderr or len(stdout) > 96:
        raise ValueError("incomplete first-return observation")
    if stdout in (b"y2q_log_missing\n", b"y2q_log_unreadable\n"):
        return {"state": stdout.decode().strip().removeprefix("y2q_log_")}
    m = re.fullmatch(
        rb"y2q_log_v1=([0-9]{1,7}),([0-9]{1,5}),([0-9]{1,5}),([01])\n", stdout
    )
    if not m:
        raise ValueError("unexpected first-return output")
    n, first, second, paired = map(int, m.groups())
    if (
        n > CAPACITY
        or (first + second) * 128 > n
        or (paired and (first, second) != (1, 1))
    ):
        raise ValueError("inconsistent first-return output")
    if first > 1 or second > 1 or (first and second and not paired):
        state = "ambiguous"
    else:
        state = {
            (0, 0): "no_record",
            (1, 0): "fdt_only",
            (0, 1): "unflatten_only",
            (1, 1): "paired",
        }[(first, second)]
    return dict(state=state, size=n, fdt_count=first, unflatten_count=second)
