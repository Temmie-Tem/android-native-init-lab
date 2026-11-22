"""Render the fixed first-return pstore reader and decode its bounded result."""

import hashlib
import re
import shlex

ADB = "/usr/lib/android-sdk/platform-tools/adb"
HEX = re.compile(r"[0-9a-f]{64}")
STAGES = ("guard-passed", "fdt-marked", "handoff-ready")
SECONDS = 12
STDOUT = 192
STDERR = 1024
PMSG = 1024
CONSOLE = 0x40000


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def script(tag, boot):
    if HEX.fullmatch(tag) is None or HEX.fullmatch(boot) is None:
        raise ValueError("pstore marker or boot identity differs")
    records = [f"Y2Q-STAGE-V1 {tag} {stage}\n".encode() for stage in STAGES]
    cases = "\n".join(
        f"          {len(prefix)}:{sha256(prefix)}) answer=MATCH_{index} ;;"
        for index in range(1, len(records) + 1)
        for prefix in (b"".join(records[:index]),)
    )
    pattern = (r"^(<[0-9]+>)?(\[ *[0-9]+\.[0-9]+\] *)?"
               r"([ I]\[[0-9]:[^]:]{15}: *[0-9]{1,5}\] )?"
               r"Kernel command line: codex\.y2q_trace=" + tag + r"( |$)")
    return f"""set -eu
set -o pipefail
export LC_ALL=C
boot_hash() {{
  boot=$(/system/bin/cat /proc/sys/kernel/random/boot_id) || return 1
  hash=$(/system/bin/printf '%s' "$boot" | /system/bin/sha256sum) || return 1
  /system/bin/printf '%s' "${{hash%% *}}"
}}
[ "$(/system/bin/id -u)" = 0 ] && [ "$(boot_hash)" = {boot} ] || exit 64
chosen=/sys/firmware/devicetree/base/chosen
property=$chosen/codex,y2q-uniloader-android-v1
[ -d "$chosen" ] && [ -r "$chosen" ] && [ -x "$chosen" ] || exit 64
[ ! -L "$property" ] && [ ! -e "$property" ] || exit 64
directory=/sys/fs/pstore
mount_view=$(/system/bin/head -c 65537 /proc/self/mounts && /system/bin/printf .) || exit 65
mount_view=${{mount_view%.}}
[ "${{#mount_view}}" -le 65536 ] || exit 65
mounts=$(/system/bin/printf '%s' "$mount_view" | (
  count=0
  correct=0
  while IFS=' ' read -r source target kind remainder; do
    if [ "$target" = "$directory" ]; then
      count=$((count+1))
      if [ "$kind" = pstore ]; then correct=$((correct+1)); fi
    fi
  done
  if [ "$count:$correct" = 1:1 ]; then /system/bin/printf 1; else /system/bin/printf 0; fi
)) || exit 65

record() (
  node=$directory/$1
  limit=$2
  [ "$mounts" = 1 ] && [ ! -L "$directory" ] && [ -d "$directory" ] || exit 65
  [ ! -L "$node" ] || exit 65
  if [ ! -e "$node" ]; then
    [ -r "$directory" ] && [ -x "$directory" ] || exit 65
    /system/bin/printf MISSING
    exit 0
  fi
  [ -f "$node" ] && [ -r "$node" ] || exit 65
  metadata='%d:%i:%f:%s:%h'
  before=$(/system/bin/stat -c "$metadata" "$node") || exit 65
  size=$(/system/bin/stat -c '%s' "$node") || exit 65
  case "$size" in ''|*[!0-9]*) exit 65 ;; esac
  [ "$size" -le "$limit" ] && [ "${{before##*:}}" = 1 ] || exit 65
  exec 3< "$node"
  # FD 0 survives mksh's close-on-exec treatment of FD 3.
  [ -f /proc/self/fd/0 ] <&3 || exit 65
  [ "$(/system/bin/stat -Lc "$metadata" /proc/self/fd/0 <&3)" = "$before" ] || exit 65
  answer=UNMATCHED
  case "$1" in
    pmsg-ramoops-0)
      hash=$(/system/bin/head -c "$((limit+1))" <&3 | /system/bin/sha256sum) || exit 65
      case "$size:${{hash%% *}}" in
{cases}
      esac ;;
    console-ramoops-0)
      count=$(/system/bin/head -c "$((limit+1))" <&3 |
        {{ /system/bin/grep -aEc -- {shlex.quote(pattern)} || [ "$?" = 1 ]; }}) || exit 65
      [ "$count" != 1 ] || answer=MATCH ;;
    *) exit 65 ;;
  esac
  after=$(/system/bin/stat -Lc "$metadata" /proc/self/fd/0 <&3) || exit 65
  exec 3<&-
  [ "$after" = "$before" ] && [ "$(/system/bin/stat -c "$metadata" "$node")" = "$before" ] || exit 65
  /system/bin/printf '%s' "$answer"
)
pmsg=$(record pmsg-ramoops-0 {PMSG}) || pmsg=UNAVAILABLE
console=$(record console-ramoops-0 {CONSOLE}) || console=UNAVAILABLE
[ "$(boot_hash)" = {boot} ] || exit 64
/system/bin/printf 'Y2Q_PSTORE_RETURN_V1\nboot_sha256=%s\npmsg=%s\nconsole=%s\n' {boot} "$pmsg" "$console"
"""


def argv(serial, tag, boot):
    return [ADB, "-s", serial, "shell", "-T", "su", "-c", shlex.quote(script(tag, boot))]


def decode(returncode, stdout, stderr, boot):
    row = re.fullmatch(rb"Y2Q_PSTORE_RETURN_V1\nboot_sha256=([a-f0-9]{64})\n"
                       rb"pmsg=(MISSING|UNAVAILABLE|UNMATCHED|MATCH_[123])\n"
                       rb"console=(MISSING|UNAVAILABLE|UNMATCHED|MATCH)\n", stdout)
    if returncode != 0 or stderr or len(stdout) > STDOUT or row is None:
        return {"pmsg": "UNAVAILABLE", "console": "UNAVAILABLE",
                "loader_stages": [], "vendor_kernel_command_line": False}
    if row[1].decode() != boot:
        return {"pmsg": "BOOT_CHANGED", "console": "BOOT_CHANGED",
                "loader_stages": [], "vendor_kernel_command_line": False}
    pmsg, console = (item.decode() for item in row.groups()[1:])
    count = int(pmsg[-1]) if pmsg.startswith("MATCH_") else 0
    return {"pmsg": pmsg, "console": console, "loader_stages": list(STAGES[:count]),
            "vendor_kernel_command_line": console == "MATCH"}
