#!/usr/bin/env python3
"""Run WSTA94: bounded D-public packet-filter loopback live gate.

This runner mounts the Debian rootfs as a chroot, stages only the loopback smoke
helpers plus the D-public packet-filter helper, then runs one SSH transaction
that proves:

  * packet-filter preflight passes;
  * current IPv4/IPv6 filter tables are saved before mutation;
  * loopback smoke works before and after the loopback-only default-drop policy;
  * INPUT/FORWARD default-drop and loopback accept are observable;
  * restore returns the exact saved IPv4/IPv6 filter tables before cleanup.

It does not start Wi-Fi association, DHCP, public tunnels, public smoke, native
reboot, switch_root, userdata formatting, or boot flashing.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = SCRIPT_DIR.parent / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_d1_chroot_mvp as d1  # noqa: E402
import run_d2_ssh_in_chroot as d2  # noqa: E402
import run_wsta19_native_owned_chroot_wifi as wsta19  # noqa: E402
import run_wsta2_native_materialization as wsta2  # noqa: E402
import run_wsta42_native_uplink_dpublic_tunnel as wsta42  # noqa: E402


REPO_ROOT = wsta2.REPO_ROOT
DEFAULT_RUN_BASE = wsta2.DEFAULT_RUN_BASE
PASS_DECISION = "wsta94-packet-filter-loopback-live-pass"
REMOTE_PACKET_FILTER = "/usr/local/bin/a90-dpublic-packet-filter"
PACKET_FILTER_SOURCE = SCRIPT_DIR / "a90_dpublic_packet_filter.sh"
RESULT_NAME = "wsta94_result.json"
WSTA94_LOOP = "/dev/loop0"
WSTA94_LOOP_MINOR = "0"
WSTA94_LOOP_STATE = "/tmp/a90_wsta94_loop_created"


def rel(path: Path) -> str:
    return wsta2.rel(path)


def write_json(path: Path, payload: Any) -> None:
    d1.write_json(path, payload)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def finish_result(out_path: Path, result: dict[str, Any]) -> dict[str, Any]:
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def sha256_file(path: Path) -> str:
    return d1.sha256_file(path)


def explicit_live_gate(args: argparse.Namespace) -> tuple[bool, str]:
    if not args.execute_loopback_default_drop_live:
        return False, "wsta94-blocked-loopback-default-drop-live-required"
    if not args.allow_packet_filter_live:
        return False, "wsta94-blocked-packet-filter-live-allow-required"
    if not args.ack_packet_filter_mutation:
        return False, "wsta94-blocked-packet-filter-mutation-ack-required"
    if not args.force_restore_proof:
        return False, "wsta94-blocked-restore-proof-required"
    return True, "ok"


def safety(gate_ok: bool) -> dict[str, Any]:
    return {
        "device_action": gate_ok,
        "boot_flash": False,
        "native_reboot": False,
        "wifi_connect": False,
        "dhcp": False,
        "public_tunnel": False,
        "public_smoke": False,
        "external_ping": False,
        "userdata_touch": False,
        "switch_root": False,
        "packet_filter_mutation": "explicit-live-gated" if gate_ok else False,
        "packet_filter_restore_required": gate_ok,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def stage_loopback_binaries(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    return {
        "smoke_httpd": ssh_write_file_atomic(
            args,
            run_dir,
            run_dir / "a90-dpublic-smoke-httpd",
            wsta42.REMOTE_SMOKE,
            timeout=args.ssh_timeout,
        ),
        "http_get": ssh_write_file_atomic(
            args,
            run_dir,
            run_dir / "a90-dpublic-http-get",
            wsta42.REMOTE_HTTP_GET,
            timeout=args.ssh_timeout,
        ),
    }


def stage_packet_filter_helper(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    return ssh_write_file_atomic(
        args,
        run_dir,
        PACKET_FILTER_SOURCE,
        REMOTE_PACKET_FILTER,
        timeout=args.ssh_timeout,
    )


def stage_ok(record: dict[str, Any]) -> bool:
    return all(bool(item.get("staged")) for item in record.values())


def native_stale_cleanup(args: argparse.Namespace) -> dict[str, Any]:
    script = f"""
set +e
echo A90WSTA94_NATIVE_STALE_CLEANUP_BEGIN
for pid in $(/bin/busybox pidof a90-dpublic-smoke-httpd 2>/dev/null); do
  /bin/busybox kill "$pid" >/dev/null 2>&1 || true
done
/bin/busybox sleep 1
for pid in $(/bin/busybox pidof a90-dpublic-smoke-httpd 2>/dev/null); do
  /bin/busybox kill -9 "$pid" >/dev/null 2>&1 || true
done
if /bin/busybox pidof a90-dpublic-smoke-httpd >/dev/null 2>&1; then echo A90WSTA94 stale_smoke_absent=0; else echo A90WSTA94 stale_smoke_absent=1; fi
for pid in $(/bin/busybox pidof dropbear 2>/dev/null); do
  /bin/busybox kill "$pid" >/dev/null 2>&1 || true
done
/bin/busybox sleep 1
for pid in $(/bin/busybox pidof dropbear 2>/dev/null); do
  /bin/busybox kill -9 "$pid" >/dev/null 2>&1 || true
done
if /bin/busybox pidof dropbear >/dev/null 2>&1; then echo A90WSTA94 stale_dropbear_absent=0; else echo A90WSTA94 stale_dropbear_absent=1; fi
MNT={d2.shell_quote(args.mountpoint)}
if /bin/busybox grep -q " $MNT " /proc/mounts; then /bin/busybox umount "$MNT" || /bin/busybox umount -l "$MNT"; fi
LOOP={WSTA94_LOOP}
STATE={WSTA94_LOOP_STATE}
LOOP_MAJOR=$(/bin/busybox awk '$2=="loop" {{print $1; exit}}' /proc/devices)
CREATED=0
if [ ! -e "$LOOP" ] && [ -n "$LOOP_MAJOR" ]; then
  /bin/busybox mknod "$LOOP" b "$LOOP_MAJOR" {WSTA94_LOOP_MINOR}
  CREATED=1
fi
for i in 1 2 3; do
  /bin/busybox losetup -d "$LOOP" >/dev/null 2>&1 || true
  /bin/busybox sleep 1
  /bin/busybox losetup "$LOOP" >/dev/null 2>&1 || break
done
LOOP_INFO=$(/bin/busybox losetup "$LOOP" 2>&1)
LOOP_INFO_RC=$?
echo A90WSTA94 loop_info_rc=$LOOP_INFO_RC
echo A90WSTA94 loop_info="$LOOP_INFO"
if [ "$CREATED" = "1" ] && [ "$LOOP_INFO_RC" != "0" ]; then /bin/busybox rm -f "$LOOP"; fi
/bin/busybox rm -f "$STATE"
echo A90WSTA94_NATIVE_STALE_CLEANUP_DONE
""".strip()
    record = wsta19.bridge_shell(args, script, timeout=args.cleanup_timeout, allow_error=True)
    text = str(record.get("text") or "")
    record["stale_smoke_absent"] = "A90WSTA94 stale_smoke_absent=1" in text
    record["stale_dropbear_absent"] = "A90WSTA94 stale_dropbear_absent=1" in text
    record["loop_unbound"] = "A90WSTA94 loop_info_rc=1" in text
    record["cleaned"] = (
        record.get("rc") == 0
        and "A90WSTA94_NATIVE_STALE_CLEANUP_DONE" in text
        and record["stale_smoke_absent"]
        and record["stale_dropbear_absent"]
        and record["loop_unbound"]
    )
    return record


def ssh_write_file_atomic(args: argparse.Namespace,
                          run_dir: Path,
                          local_path: Path,
                          remote_path: str,
                          *,
                          timeout: float) -> dict[str, Any]:
    command = [
        *wsta42.ssh_command(args, run_dir),
        (
            "set -eu; "
            f"TARGET={wsta42.shlex.quote(remote_path)}; "
            "TMP=\"${TARGET}.wsta94-tmp.$$\"; "
            f"/bin/mkdir -p {wsta42.shlex.quote(str(Path(remote_path).parent))}; "
            "/bin/rm -f \"$TMP\"; "
            "/bin/cat > \"$TMP\"; "
            "/bin/chmod 755 \"$TMP\"; "
            "/bin/mv -f \"$TMP\" \"$TARGET\"; "
            "/usr/bin/test -x \"$TARGET\"; "
            "echo A90WSTA94_FILE_STAGED"
        ),
    ]
    data = local_path.read_bytes()
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace")
    return {
        "command": command,
        "input_bytes": len(data),
        "input_sha256": sha256_file(local_path),
        "input_redacted": False,
        "returncode": completed.returncode,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "stdout": stdout,
        "stderr": stderr,
        "staged": completed.returncode == 0 and "A90WSTA94_FILE_STAGED" in stdout,
        "remote_path": remote_path,
        "atomic_replace": True,
    }


def wsta94_mount_script(remote_image: str, mountpoint: str, port: int) -> str:
    script = d2.d2_mount_script(remote_image, mountpoint, port)
    script = script.replace("LOOP=/dev/loop0", f"LOOP={WSTA94_LOOP}")
    script = script.replace("STATE=/tmp/a90_d2_loop_created", f"STATE={WSTA94_LOOP_STATE}")
    script = script.replace('mknod "$LOOP" b "$LOOP_MAJOR" 0', f'mknod "$LOOP" b "$LOOP_MAJOR" {WSTA94_LOOP_MINOR}')
    ensure_node = 'echo A90D2 loop_node_created=$(/bin/busybox cat "$STATE")'
    detach_stale = """echo A90D2 loop_node_created=$(/bin/busybox cat "$STATE")
/bin/busybox losetup -d "$LOOP" >/dev/null 2>&1 || true
echo A90D2 stale_loop_detach_attempted=1"""
    old = '/bin/busybox losetup "$LOOP" "$IMG"'
    new = """LOSETUP_RC=0
/bin/busybox losetup "$LOOP" "$IMG" || LOSETUP_RC=$?
echo A90D2 losetup_rc=$LOSETUP_RC
if [ "$LOSETUP_RC" != "0" ]; then
  LOOP_INFO=$(/bin/busybox losetup "$LOOP" 2>&1)
  LOOP_INFO_RC=$?
  echo A90D2 losetup_info_rc=$LOOP_INFO_RC
  echo A90D2 losetup_info="$LOOP_INFO"
  if [ "$LOOP_INFO_RC" != "0" ]; then exit 32; fi
fi"""
    if ensure_node not in script or old not in script:
        raise RuntimeError("D2 mount script shape changed; WSTA94 losetup guard needs review")
    return script.replace(ensure_node, detach_stale).replace(old, new)


def wsta94_cleanup_script(mountpoint: str) -> str:
    return f"""
set +e
M={d2.shell_quote(mountpoint)}
L={WSTA94_LOOP}
S={WSTA94_LOOP_STATE}
echo A90D2_CLEANUP_BEGIN
if [ -f $M/tmp/a90_d2_dropbear.pid ]; then echo A90D2 cleanup_pid=$(/bin/busybox cat $M/tmp/a90_d2_dropbear.pid); else echo A90D2 cleanup_pid=missing; fi
for pid in $(/bin/busybox pidof dropbear 2>/dev/null); do
  /bin/busybox kill $pid >/dev/null 2>&1 || true
done
/bin/busybox sleep 1
for pid in $(/bin/busybox pidof dropbear 2>/dev/null); do
  /bin/busybox kill -9 $pid >/dev/null 2>&1 || true
done
/bin/busybox sleep 1
for pid in $(/bin/busybox pidof a90-dpublic-smoke-httpd 2>/dev/null); do
  /bin/busybox kill -9 $pid >/dev/null 2>&1 || true
done
if [ -f $M/tmp/a90_d2_shadow.bak ]; then
  /bin/busybox cp $M/tmp/a90_d2_shadow.bak $M/etc/shadow
  /bin/busybox chmod 600 $M/etc/shadow
  echo A90D2 shadow_restored=1
else
  echo A90D2 shadow_restored=0
fi
/bin/busybox rm -f $M/root/.ssh/authorized_keys $M/tmp/a90_d2_dropbear_hostkey $M/tmp/a90_d2_dropbear.pid $M/tmp/a90_d2_shadow.bak $M/tmp/a90_d2_shadow.new
/bin/busybox grep -q " $M " /proc/mounts && (/bin/busybox umount $M || /bin/busybox umount -l $M)
for i in 1 2 3; do
  [ -e $L ] && /bin/busybox losetup -d $L >/dev/null 2>&1 || true
  /bin/busybox sleep 1
  /bin/busybox losetup $L >/dev/null 2>&1 || break
done
[ -f $S ] && /bin/busybox grep -q '^1$' $S && /bin/busybox rm -f $L
/bin/busybox rm -f $S
/bin/busybox rmdir $M >/dev/null 2>&1
if /bin/busybox grep -q " $M " /proc/mounts; then echo A90D2 cleanup_mount_absent=0; else echo A90D2 cleanup_mount_absent=1; fi
if [ -e $L ] && /bin/busybox losetup $L >/dev/null 2>&1; then echo A90D2 cleanup_loop_node_absent=0; else echo A90D2 cleanup_loop_node_absent=1; fi
if /bin/busybox pidof dropbear >/dev/null 2>&1; then echo A90D2 cleanup_dropbear_absent=0; else echo A90D2 cleanup_dropbear_absent=1; fi
echo A90D2_CLEANUP_DONE
""".strip()


def wsta94_postcheck_script(mountpoint: str) -> str:
    return f"""
set -eu
MNT={d2.shell_quote(mountpoint)}
LOOP={WSTA94_LOOP}
/bin/busybox sleep 2
echo A90D2_POSTCHECK_BEGIN
if /bin/busybox grep -q " $MNT " /proc/mounts; then echo A90D2 post_mount_absent=0; exit 51; else echo A90D2 post_mount_absent=1; fi
if [ -e "$LOOP" ] && /bin/busybox losetup "$LOOP" >/dev/null 2>&1; then echo A90D2 post_loop_node_absent=0; exit 52; else echo A90D2 post_loop_node_absent=1; fi
if /bin/busybox pidof dropbear >/dev/null 2>&1; then echo A90D2 post_dropbear_absent=0; exit 53; else echo A90D2 post_dropbear_absent=1; fi
echo A90D2_POSTCHECK_DONE
""".strip()


def wsta94_start_dropbear_script(mountpoint: str, public_key: str, bind_ip: str, port: int) -> str:
    return f"""
set -eu
M={d2.shell_quote(mountpoint)}
B={d2.shell_quote(f"{bind_ip}:{port}")}
K=/tmp/a90_d2_dropbear_hostkey
P=/tmp/a90_d2_dropbear.pid
L=/tmp/a90_d2_dropbear.log
SB=/tmp/a90_d2_shadow.bak
SN=/tmp/a90_d2_shadow.new
echo A90D2_START_BEGIN
echo A90D2 port=$B
/bin/busybox grep -q " $M " /proc/mounts
/bin/busybox mkdir -p "$M/root/.ssh" "$M/tmp"
/bin/busybox chmod 700 "$M/root/.ssh"
/bin/busybox printf '%s\\n' {d2.shell_quote(public_key)} > "$M/root/.ssh/authorized_keys"
/bin/busybox chmod 600 "$M/root/.ssh/authorized_keys"
/bin/busybox chown 0:0 "$M/root" "$M/root/.ssh" "$M/root/.ssh/authorized_keys"
/bin/busybox cp "$M/etc/shadow" "$M$SB"
/bin/busybox sed 's/^root:![^:]*:/root:*:/' "$M/etc/shadow" > "$M$SN"
/bin/busybox cp "$M$SN" "$M/etc/shadow"
/bin/busybox chmod 600 "$M/etc/shadow"
echo A90D2 authorized_keys=1
echo A90D2 shadow_temp_key_only=1
/bin/busybox rm -f "$M$K" "$M$P" "$M$L"
if /bin/busybox chroot "$M" /usr/bin/dropbearkey -t ed25519 -f "$K" >/tmp/a90_d2_dropbearkey.log 2>&1; then echo A90D2 hostkey_type=ed25519; else /bin/busybox chroot "$M" /usr/bin/dropbearkey -t rsa -s 2048 -f "$K" >/tmp/a90_d2_dropbearkey.log 2>&1; echo A90D2 hostkey_type=rsa; fi
/bin/busybox chroot "$M" /usr/sbin/dropbear -F -E -r "$K" -p "$B" -P "$P" -s -j -k </dev/null >"$M$L" 2>&1 &
PID=$!
echo "$PID" > "$M$P"
/bin/busybox sleep 1
/bin/busybox kill -0 "$PID" >/dev/null 2>&1 || {{ [ -s "$M$L" ] && /bin/busybox tail -n 4 "$M$L"; exit 35; }}
echo A90D2 dropbear_pid=$(/bin/busybox cat "$M$P")
if /bin/busybox netstat -ltn 2>/dev/null | /bin/busybox grep -q ":{port} "; then echo A90D2 dropbear_listen=1; else echo A90D2 dropbear_listen=0; [ -s "$M$L" ] && /bin/busybox tail -n 4 "$M$L"; exit 35; fi
echo A90D2_DROPBEAR_STARTED
""".strip()


def packet_filter_probe_script() -> str:
    run_dir = wsta42.REMOTE_RUN_DIR + "/wsta94-packet-filter"
    smoke_pid = run_dir + "/smoke.pid"
    smoke_log = run_dir + "/smoke.log"
    return f"""
set +e
RUN_DIR={wsta42.shlex.quote(run_dir)}
PF={wsta42.shlex.quote(REMOTE_PACKET_FILTER)}
SMOKE={wsta42.shlex.quote(wsta42.REMOTE_SMOKE)}
HTTP_GET={wsta42.shlex.quote(wsta42.REMOTE_HTTP_GET)}
SMOKE_PID={wsta42.shlex.quote(smoke_pid)}
SMOKE_LOG={wsta42.shlex.quote(smoke_log)}
IPT4=/usr/sbin/iptables-legacy
	IPT6=/usr/sbin/ip6tables-legacy
	RESTORE4=/usr/sbin/iptables-legacy-restore
	RESTORE6=/usr/sbin/ip6tables-legacy-restore
	APPLIED=0
	RESTORED=0
	rules_to_restore() {{
	  src=$1
	  dst=$2
	  {{
	    /bin/printf '*filter\\n'
	    while IFS= read -r line; do
	      set -- $line
	      case "${{1:-}}" in
	        -P)
	          [ "$#" -ge 3 ] || return 1
	          /bin/printf ':%s %s [0:0]\\n' "$2" "$3"
	          ;;
	        -N)
	          [ "$#" -ge 2 ] || return 1
	          /bin/printf ':%s - [0:0]\\n' "$2"
	          ;;
	        -A)
	          /bin/printf '%s\\n' "$line"
	          ;;
	      esac
	    done < "$src"
	    /bin/printf 'COMMIT\\n'
	  }} > "$dst"
	}}
	restore_probe_rules() {{
	  [ -s "$RUN_DIR/before.probe.restore.v4" ] || return 1
	  [ -s "$RUN_DIR/before.probe.restore.v6" ] || return 1
	  "$RESTORE4" < "$RUN_DIR/before.probe.restore.v4" || return 1
	  "$RESTORE6" < "$RUN_DIR/before.probe.restore.v6" || return 1
	  return 0
	}}
	cleanup() {{
	  if [ -s "$SMOKE_PID" ]; then /bin/kill "$(/bin/cat "$SMOKE_PID")" >/dev/null 2>&1 || true; fi
	  /usr/bin/pkill -f '[a]90-dpublic-smoke-httpd' >/dev/null 2>&1 || true
	  if [ "$APPLIED" = "1" ] && [ "$RESTORED" != "1" ]; then
	    restore_probe_rules >/dev/null 2>&1 || true
	  fi
	}}
fail() {{
  echo "A90WSTA94_FAIL reason=$1 rc=$2"
  exit "$2"
}}
trap cleanup EXIT INT TERM
/bin/mkdir -p "$RUN_DIR" {wsta42.shlex.quote(wsta42.REMOTE_RUN_DIR)}
	/bin/rm -f "$SMOKE_PID" "$SMOKE_LOG" "$RUN_DIR"/before.probe.v4 "$RUN_DIR"/before.probe.v6 "$RUN_DIR"/before.probe.restore.v4 "$RUN_DIR"/before.probe.restore.v6 "$RUN_DIR"/after.probe.v4 "$RUN_DIR"/after.probe.v6
if [ -x /sbin/ip ]; then /sbin/ip link set lo up >/dev/null 2>&1; fi
if [ -x /usr/sbin/ip ]; then /usr/sbin/ip link set lo up >/dev/null 2>&1; fi
if [ -x /bin/busybox ]; then /bin/busybox ip link set lo up >/dev/null 2>&1; fi
echo A90WSTA94_BEGIN
PF_PRE=$("$PF" preflight 2>&1)
PF_PRE_RC=$?
/bin/printf '%s\\n' "$PF_PRE"
[ "$PF_PRE_RC" -eq 0 ] || fail preflight "$PF_PRE_RC"
"$SMOKE" 127.0.0.1 8080 </dev/null >"$SMOKE_LOG" 2>&1 &
echo $! > "$SMOKE_PID"
/bin/sleep 1
if /bin/kill -0 "$(/bin/cat "$SMOKE_PID")" 2>/dev/null; then echo A90WSTA94_SMOKE_STARTED=1; else fail smoke-start 21; fi
HTTP_BEFORE=$(/usr/bin/timeout 10s "$HTTP_GET" 127.0.0.1 8080 2>&1)
HTTP_BEFORE_RC=$?
/bin/printf '%s\\n' "$HTTP_BEFORE"
if /bin/printf '%s\\n' "$HTTP_BEFORE" | /bin/grep -q 'A90_DPUBLIC_SMOKE_OK'; then
  echo A90WSTA94_LOOPBACK_BEFORE_OK=1
else
  echo A90WSTA94_LOOPBACK_BEFORE_OK=0 rc=$HTTP_BEFORE_RC
  fail loopback-before 22
fi
	"$IPT4" -S > "$RUN_DIR/before.probe.v4" || fail save-before-v4 23
	"$IPT6" -S > "$RUN_DIR/before.probe.v6" || fail save-before-v6 24
	[ -s "$RUN_DIR/before.probe.v4" ] || fail save-before-v4-empty 25
	[ -s "$RUN_DIR/before.probe.v6" ] || fail save-before-v6-empty 26
	rules_to_restore "$RUN_DIR/before.probe.v4" "$RUN_DIR/before.probe.restore.v4" || fail save-before-v4-restore 27
	rules_to_restore "$RUN_DIR/before.probe.v6" "$RUN_DIR/before.probe.restore.v6" || fail save-before-v6-restore 28
PF_APPLY=$("$PF" apply-loopback-default-drop 2>&1)
PF_APPLY_RC=$?
/bin/printf '%s\\n' "$PF_APPLY"
[ "$PF_APPLY_RC" -eq 0 ] || fail apply "$PF_APPLY_RC"
APPLIED=1
RULES4=$("$IPT4" -S 2>&1)
RULES6=$("$IPT6" -S 2>&1)
/bin/printf '%s\\n' "$RULES4"
/bin/printf '%s\\n' "$RULES6"
case "$RULES4" in *"-P INPUT DROP"*) echo A90WSTA94_POLICY_V4_INPUT_DROP=1;; *) echo A90WSTA94_POLICY_V4_INPUT_DROP=0; fail policy-v4-input 31;; esac
case "$RULES4" in *"-P FORWARD DROP"*) echo A90WSTA94_POLICY_V4_FORWARD_DROP=1;; *) echo A90WSTA94_POLICY_V4_FORWARD_DROP=0; fail policy-v4-forward 32;; esac
case "$RULES4" in *"-P OUTPUT ACCEPT"*) echo A90WSTA94_POLICY_V4_OUTPUT_ACCEPT=1;; *) echo A90WSTA94_POLICY_V4_OUTPUT_ACCEPT=0; fail policy-v4-output 33;; esac
case "$RULES4" in *"-A INPUT -i lo -j ACCEPT"*) echo A90WSTA94_RULE_V4_LOOPBACK_ACCEPT=1;; *) echo A90WSTA94_RULE_V4_LOOPBACK_ACCEPT=0; fail rule-v4-loopback 34;; esac
case "$RULES6" in *"-P INPUT DROP"*) echo A90WSTA94_POLICY_V6_INPUT_DROP=1;; *) echo A90WSTA94_POLICY_V6_INPUT_DROP=0; fail policy-v6-input 35;; esac
case "$RULES6" in *"-A INPUT -i lo -j ACCEPT"*) echo A90WSTA94_RULE_V6_LOOPBACK_ACCEPT=1;; *) echo A90WSTA94_RULE_V6_LOOPBACK_ACCEPT=0; fail rule-v6-loopback 36;; esac
HTTP_AFTER=$(/usr/bin/timeout 10s "$HTTP_GET" 127.0.0.1 8080 2>&1)
HTTP_AFTER_RC=$?
/bin/printf '%s\\n' "$HTTP_AFTER"
if /bin/printf '%s\\n' "$HTTP_AFTER" | /bin/grep -q 'A90_DPUBLIC_SMOKE_OK'; then
  echo A90WSTA94_LOOPBACK_AFTER_OK=1
else
  echo A90WSTA94_LOOPBACK_AFTER_OK=0 rc=$HTTP_AFTER_RC
  fail loopback-after 37
fi
	restore_probe_rules || fail restore 78
	echo packet_filter_decision=packet-filter-restored
	RESTORED=1
	"$IPT4" -S > "$RUN_DIR/after.probe.v4" || fail save-after-v4 41
	"$IPT6" -S > "$RUN_DIR/after.probe.v6" || fail save-after-v6 42
if /usr/bin/cmp -s "$RUN_DIR/before.probe.v4" "$RUN_DIR/after.probe.v4"; then echo A90WSTA94_RESTORE_EXACT_V4=1; else echo A90WSTA94_RESTORE_EXACT_V4=0; fail restore-v4-mismatch 43; fi
if /usr/bin/cmp -s "$RUN_DIR/before.probe.v6" "$RUN_DIR/after.probe.v6"; then echo A90WSTA94_RESTORE_EXACT_V6=1; else echo A90WSTA94_RESTORE_EXACT_V6=0; fail restore-v6-mismatch 44; fi
echo A90WSTA94_PACKET_FILTER_PROBE_PASS
exit 0
""".strip()


def parse_packet_filter_probe(record: dict[str, Any]) -> dict[str, Any]:
    stdout = str(record.get("stdout") or "")
    return {
        "preflight_pass": "packet_filter_decision=packet-filter-preflight-pass" in stdout,
        "apply_pass": "packet_filter_decision=packet-filter-loopback-default-drop-applied" in stdout,
        "restore_pass": "packet_filter_decision=packet-filter-restored" in stdout,
        "smoke_started": "A90WSTA94_SMOKE_STARTED=1" in stdout,
        "loopback_before_ok": "A90WSTA94_LOOPBACK_BEFORE_OK=1" in stdout,
        "loopback_after_ok": "A90WSTA94_LOOPBACK_AFTER_OK=1" in stdout,
        "v4_input_drop": "A90WSTA94_POLICY_V4_INPUT_DROP=1" in stdout,
        "v4_forward_drop": "A90WSTA94_POLICY_V4_FORWARD_DROP=1" in stdout,
        "v4_output_accept": "A90WSTA94_POLICY_V4_OUTPUT_ACCEPT=1" in stdout,
        "v4_loopback_accept": "A90WSTA94_RULE_V4_LOOPBACK_ACCEPT=1" in stdout,
        "v6_input_drop": "A90WSTA94_POLICY_V6_INPUT_DROP=1" in stdout,
        "v6_loopback_accept": "A90WSTA94_RULE_V6_LOOPBACK_ACCEPT=1" in stdout,
        "restore_exact_v4": "A90WSTA94_RESTORE_EXACT_V4=1" in stdout,
        "restore_exact_v6": "A90WSTA94_RESTORE_EXACT_V6=1" in stdout,
        "probe_pass": record.get("returncode") == 0 and "A90WSTA94_PACKET_FILTER_PROBE_PASS" in stdout,
        "secret_values_logged": 0,
    }


def run_packet_filter_probe(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    record = wsta42.ssh_exec(args, run_dir, packet_filter_probe_script(), timeout=args.packet_filter_timeout)
    record["parsed"] = parse_packet_filter_probe(record)
    return record


def chroot_cleanup_ok(result: dict[str, Any]) -> bool:
    cleanup = result.get("cleanup_parse", {})
    postcheck = result.get("postcheck_parse", {})
    return bool(
        cleanup.get("done")
        and cleanup.get("shadow_restored")
        and postcheck.get("mount_absent")
        and postcheck.get("loop_node_absent")
        and postcheck.get("dropbear_absent")
    )


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_live_gate", "wsta94-blocked-explicit-live-gate"),
        ("local_image_present", "wsta94-blocked-local-image-missing"),
        ("helpers_built", "wsta94-blocked-helper-build"),
        ("baseline_selftest_fail_zero", "wsta94-blocked-baseline-selftest"),
        ("native_stale_cleanup_ok", "wsta94-blocked-native-stale-cleanup"),
        ("remote_image_ready", "wsta94-blocked-remote-image"),
        ("chroot_mount_ready", "wsta94-blocked-chroot-mount"),
        ("dropbear_started", "wsta94-blocked-dropbear-start"),
        ("debian_ssh_marker", "wsta94-blocked-debian-ssh"),
        ("loopback_binaries_staged", "wsta94-blocked-loopback-binary-stage"),
        ("packet_filter_helper_staged", "wsta94-blocked-packet-filter-helper-stage"),
        ("packet_filter_preflight_pass", "wsta94-blocked-packet-filter-preflight"),
        ("loopback_before_ok", "wsta94-blocked-loopback-before"),
        ("packet_filter_apply_pass", "wsta94-blocked-packet-filter-apply"),
        ("packet_filter_default_drop_observed", "wsta94-blocked-default-drop-observe"),
        ("loopback_after_ok", "wsta94-blocked-loopback-after-default-drop"),
        ("packet_filter_restore_pass", "wsta94-blocked-packet-filter-restore"),
        ("packet_filter_restore_exact", "wsta94-blocked-packet-filter-restore-mismatch"),
        ("dpublic_cleanup_ok", "wsta94-blocked-dpublic-cleanup"),
        ("chroot_cleanup_ok", "wsta94-blocked-chroot-cleanup"),
        ("final_selftest_fail_zero", "wsta94-blocked-final-selftest"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return decision
    return PASS_DECISION


def translate_wsta42_decision(result: dict[str, Any]) -> None:
    decision = result.get("decision")
    if isinstance(decision, str) and decision.startswith("wsta42-"):
        result["decision"] = decision.replace("wsta42-", "wsta94-inherited-image-", 1)


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta94-packet-filter-live-gate-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / RESULT_NAME

    gate_ok, gate_decision = explicit_live_gate(args)
    result: dict[str, Any] = {
        "scope": "WSTA94 bounded D-public packet-filter loopback live gate",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "gate_decision": gate_decision,
        "remote_image": args.remote_image,
        "remote_clean_image": args.remote_clean_image if wsta42.remote_clean_image_enabled(args) else None,
        "mountpoint": args.mountpoint,
        "safety": safety(gate_ok),
        "checks": {
            "explicit_live_gate": gate_ok,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
    }
    write_json(out_path, result)
    if not gate_ok:
        result["decision"] = gate_decision
        return finish_result(out_path, result)

    local_image = args.local_image
    if not local_image.is_file():
        result["checks"]["local_image_present"] = False
        result["decision"] = classify(result)
        return finish_result(out_path, result)

    local_sha = sha256_file(local_image)
    result["local_image"] = rel(local_image)
    result["local_image_sha256"] = local_sha
    result["checks"]["local_image_present"] = True
    if args.local_image_sha256 and args.local_image_sha256 != local_sha:
        result["local_image_expected_sha256"] = args.local_image_sha256
        result["checks"]["remote_image_ready"] = False
        result["decision"] = "wsta94-blocked-local-image-sha"
        return finish_result(out_path, result)

    result["helper_build"] = wsta42.build_dpublic_helpers(run_dir)
    result["checks"]["helpers_built"] = bool(result["helper_build"].get("ok"))
    write_json(out_path, result)
    if not result["checks"]["helpers_built"]:
        result["decision"] = classify(result)
        return finish_result(out_path, result)

    mounted = False
    try:
        result["bridge_status"] = wsta2.run_host([sys.executable, str(wsta2.BRIDGE), "status", "--json"], timeout=10.0)
        result["version"] = wsta19.try_cmdv1_retry(args, ["version"], timeout=args.timeout)
        result["status"] = wsta19.try_cmdv1_retry(args, ["status"], timeout=args.timeout)
        result["baseline_selftest"] = wsta19.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
        result["checks"]["baseline_selftest_fail_zero"] = wsta2.selftest_passed(result["baseline_selftest"].get("text", ""))
        result["native_stale_cleanup"] = native_stale_cleanup(args)
        result["checks"]["native_stale_cleanup_ok"] = bool(result["native_stale_cleanup"].get("cleaned"))
        write_json(out_path, result)
        if not result["checks"]["native_stale_cleanup_ok"]:
            result["decision"] = "wsta94-blocked-native-stale-cleanup"
            return finish_result(out_path, result)

        image_ready = wsta42.prepare_remote_work_image(args, result, out_path, run_dir, local_sha=local_sha)
        translate_wsta42_decision(result)
        result["checks"]["remote_image_ready"] = bool(image_ready)
        write_json(out_path, result)
        if not image_ready:
            return finish_result(out_path, result)

        result["keygen"] = d2.generate_ssh_key(run_dir, run_id)
        public_key = d2.read_public_key(run_dir)
        write_json(out_path, result)

        mount_record = wsta19.bridge_shell(
            args,
            wsta94_mount_script(args.remote_image, args.mountpoint, args.ssh_port),
            timeout=args.setup_timeout,
        )
        mounted = True
        result["mount"] = mount_record
        result["mount_parse"] = d2.parse_setup(str(mount_record.get("text") or ""))
        result["checks"]["chroot_mount_ready"] = bool(
            result["mount_parse"].get("mount_ready") and result["mount_parse"].get("mounted")
        )
        write_json(out_path, result)
        if not result["checks"]["chroot_mount_ready"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        start_record = wsta19.bridge_shell(
            args,
            wsta94_start_dropbear_script(args.mountpoint, public_key, args.device_ip, args.ssh_port),
            timeout=args.setup_timeout,
            allow_error=True,
        )
        result["dropbear_start"] = start_record
        result["dropbear_parse"] = d2.parse_setup(str(start_record.get("text") or ""))
        result["checks"]["dropbear_started"] = bool(
            result["dropbear_parse"].get("started")
            and result["dropbear_parse"].get("authorized_keys")
            and result["dropbear_parse"].get("shadow_temp_key_only")
        )
        write_json(out_path, result)
        if not result["checks"]["dropbear_started"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["ssh"] = wsta19.ssh_chroot_marker(args, run_dir)
        result["ssh_parse"] = result["ssh"].get("marker", {})
        result["checks"]["debian_ssh_marker"] = bool(result["ssh_parse"].get("marker"))
        write_json(out_path, result)
        if not result["checks"]["debian_ssh_marker"]:
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["loopback_stage"] = stage_loopback_binaries(args, run_dir)
        result["packet_filter_stage"] = stage_packet_filter_helper(args, run_dir)
        result["checks"]["loopback_binaries_staged"] = stage_ok(result["loopback_stage"])
        result["checks"]["packet_filter_helper_staged"] = bool(result["packet_filter_stage"].get("staged"))
        write_json(out_path, result)
        if not (result["checks"]["loopback_binaries_staged"] and result["checks"]["packet_filter_helper_staged"]):
            result["decision"] = classify(result)
            return finish_result(out_path, result)

        result["packet_filter_probe"] = run_packet_filter_probe(args, run_dir)
        parsed = result["packet_filter_probe"].get("parsed", {})
        result["checks"].update({
            "packet_filter_preflight_pass": bool(parsed.get("preflight_pass")),
            "loopback_before_ok": bool(parsed.get("loopback_before_ok")),
            "packet_filter_apply_pass": bool(parsed.get("apply_pass")),
            "packet_filter_default_drop_observed": bool(
                parsed.get("v4_input_drop")
                and parsed.get("v4_forward_drop")
                and parsed.get("v4_output_accept")
                and parsed.get("v4_loopback_accept")
                and parsed.get("v6_input_drop")
                and parsed.get("v6_loopback_accept")
            ),
            "loopback_after_ok": bool(parsed.get("loopback_after_ok")),
            "packet_filter_restore_pass": bool(parsed.get("restore_pass")),
            "packet_filter_restore_exact": bool(parsed.get("restore_exact_v4") and parsed.get("restore_exact_v6")),
        })
        write_json(out_path, result)
    finally:
        if mounted:
            if result.get("checks", {}).get("dropbear_started"):
                try:
                    result["dpublic_cleanup"] = wsta42.cleanup_dpublic(args, run_dir)
                except Exception as exc:  # noqa: BLE001
                    result["dpublic_cleanup"] = {"error": str(exc), "cleaned": False}
            else:
                result["dpublic_cleanup"] = {
                    "skipped": True,
                    "reason": "dropbear-not-started",
                    "cleaned": True,
                }
            result["cleanup"] = wsta19.bridge_shell(
                args,
                wsta94_cleanup_script(args.mountpoint),
                timeout=args.cleanup_timeout,
                allow_error=True,
            )
            result["cleanup_parse"] = d2.parse_cleanup(str(result["cleanup"].get("text") or ""))
            result["postcheck"] = wsta19.bridge_shell(
                args,
                wsta94_postcheck_script(args.mountpoint),
                timeout=args.cleanup_timeout,
                allow_error=True,
            )
            result["postcheck_parse"] = d2.parse_postcheck(str(result["postcheck"].get("text") or ""))
        else:
            result["dpublic_cleanup"] = {"skipped": True, "reason": "chroot-not-mounted"}
            result["cleanup"] = {"skipped": True, "reason": "chroot-not-mounted"}
            result["cleanup_parse"] = {}
            result["postcheck"] = {"skipped": True, "reason": "chroot-not-mounted"}
            result["postcheck_parse"] = {}

        result["final_version"] = wsta19.try_cmdv1_retry(args, ["version"], timeout=args.timeout)
        result["final_selftest"] = wsta19.try_cmdv1_retry(args, ["selftest"], timeout=args.timeout)
        result["checks"]["dpublic_cleanup_ok"] = bool(
            not mounted or result.get("dpublic_cleanup", {}).get("cleaned")
        )
        result["checks"]["chroot_cleanup_ok"] = bool(not mounted or chroot_cleanup_ok(result))
        result["checks"]["final_selftest_fail_zero"] = wsta2.selftest_passed(result["final_selftest"].get("text", ""))
        write_json(out_path, result)

    result["decision"] = classify(result)
    return finish_result(out_path, result)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--ssh-port", type=int, default=2222)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--sha-timeout", type=float, default=180.0)
    parser.add_argument("--setup-timeout", type=float, default=180.0)
    parser.add_argument("--cleanup-timeout", type=float, default=120.0)
    parser.add_argument("--ssh-timeout", type=float, default=45.0)
    parser.add_argument("--packet-filter-timeout", type=float, default=90.0)
    parser.add_argument("--ssh-connect-timeout", type=int, default=8)
    parser.add_argument("--bridge-timeout", type=float, default=60.0)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--transfer-timeout", type=float, default=900.0)
    parser.add_argument("--transfer-delay", type=float, default=2.0)
    parser.add_argument("--toybox", default="/bin/toybox")
    parser.add_argument("--local-image", type=Path, default=d1.DEFAULT_LOCAL_IMAGE)
    parser.add_argument("--local-image-sha256", default="")
    parser.add_argument("--remote-image", default=d1.DEFAULT_REMOTE_IMAGE)
    parser.add_argument("--remote-clean-image", default=wsta42.DEFAULT_REMOTE_CLEAN_IMAGE)
    parser.add_argument("--mountpoint", default=d1.DEFAULT_MOUNTPOINT)
    parser.add_argument("--execute-loopback-default-drop-live", action="store_true")
    parser.add_argument("--allow-packet-filter-live", action="store_true")
    parser.add_argument("--ack-packet-filter-mutation", action="store_true")
    parser.add_argument("--force-restore-proof", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        ts = utc_stamp()
        run_dir = args.run_dir or (DEFAULT_RUN_BASE / (args.run_id or f"wsta94-packet-filter-live-gate-{ts}"))
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        out_path = run_dir / RESULT_NAME
        if out_path.is_file():
            try:
                result = json.loads(out_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                result = {
                    "scope": "WSTA94 bounded D-public packet-filter loopback live gate",
                    "run_dir": rel(run_dir),
                }
        else:
            result = {
                "scope": "WSTA94 bounded D-public packet-filter loopback live gate",
                "run_dir": rel(run_dir),
            }
        result["decision"] = "wsta94-runner-error"
        result["error"] = str(exc)
        finish_result(out_path, result)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
