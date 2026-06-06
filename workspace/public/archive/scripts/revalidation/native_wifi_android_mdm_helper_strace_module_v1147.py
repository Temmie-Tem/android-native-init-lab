#!/usr/bin/env python3
"""V1147 host-only Magisk module scaffold for Android mdm_helper strace capture.

This script does not install a module, boot Android, contact the device, open
eSoC/subsys nodes, start Wi-Fi HAL, scan/connect, use credentials, run DHCP or
routes, external ping, or write boot/partitions. It only creates a private
host-side scaffold and verifies the wrapper contract.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_bytes, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1147-android-mdm-helper-strace-module")
LATEST_POINTER = Path("tmp/wifi/latest-v1147-android-mdm-helper-strace-module.txt")
PLAN_PATH = Path("docs/plans/NATIVE_INIT_V1146_ANDROID_MDM_HELPER_STRACE_PLAN_2026-05-27.md")

MODULE_ID = "a90_mdm_trace"
TRACE_DIR = "/data/local/tmp/a90-wifi"
MODULE_DIR = f"/data/adb/modules/{MODULE_ID}"
WRAPPER_RELATIVE_PATH = "module/system/vendor/bin/mdm_helper"
VENDOR_WRAPPER_RELATIVE_PATH = "module/vendor/bin/mdm_helper"
STRACE_RELATIVE_PATH = "module/system/vendor/bin/a90_strace"
VENDOR_STRACE_RELATIVE_PATH = "module/vendor/bin/a90_strace"
SEPOLICY_RELATIVE_PATH = "module/sepolicy.rule"
CUSTOMIZE_RELATIVE_PATH = "module/customize.sh"

REQUIRED_SYSCALLS = ("openat", "ioctl", "read", "write", "execve")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--strace-binary",
        type=Path,
        default=None,
        help="Optional static aarch64 strace binary to stage into the module.",
    )
    parser.add_argument(
        "--wrapper-binary",
        type=Path,
        default=None,
        help="Optional static aarch64 ELF mdm_helper wrapper to stage into the module.",
    )
    return parser.parse_args()


def run_host_command(command: list[str], timeout: int = 10) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return result.returncode, result.stdout


def read_text(path: Path, limit: int = 2_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def prepare_out_dir(path: Path) -> None:
    if not path.exists():
        return
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"refusing non-directory output path: {path}")
    tmp_root = repo_path("tmp").resolve()
    resolved = path.resolve()
    if tmp_root != resolved and tmp_root not in resolved.parents:
        raise RuntimeError(f"refusing to clean output outside tmp/: {path}")
    shutil.rmtree(path)


def write_exec_text(store: EvidenceStore, relative_path: str, text: str) -> Path:
    path = store.write_text(relative_path, text)
    path.chmod(0o700)
    return path


def write_module_file(store: EvidenceStore, relative_path: str, text: str, mode: int = 0o600) -> Path:
    path = store.write_text(relative_path, text)
    path.chmod(mode)
    return path


def module_prop() -> str:
    return f"""id={MODULE_ID}
name=A90 mdm_helper strace capture scaffold
version=v1159
versionCode=1159
author=Temmie/Codex
description=Temporary Android mdm_helper/ks strace capture scaffold. Remove after capture.
"""


def sepolicy_rule() -> str:
    return """# Temporary V1157 capture-only policy for Android mdm_helper strace.
# Removed with the a90_mdm_trace Magisk module after capture.
allow vendor_mdm_helper magisk_file dir { getattr open read search };
allow vendor_mdm_helper magisk_file file { execute execute_no_trans getattr map open read };
allow vendor_mdm_helper adb_data_file dir { getattr open read search };
allow vendor_mdm_helper adb_data_file file { execute execute_no_trans getattr map open read };
allow vendor_mdm_helper system_file dir { getattr open read search };
allow vendor_mdm_helper system_file file { execute execute_no_trans getattr map open read };
allow vendor_mdm_helper system_data_file dir { getattr open read search };
allow vendor_mdm_helper system_data_file file { execute execute_no_trans getattr map open read };
allow vendor_mdm_helper vendor_file dir { getattr open read search };
allow vendor_mdm_helper vendor_file file { execute execute_no_trans getattr map open read };
allow vendor_mdm_helper shell_data_file dir { add_name create getattr open read remove_name search write };
allow vendor_mdm_helper shell_data_file file { append create getattr open read setattr unlink write };
allow vendor_mdm_helper vendor_mdm_helper process ptrace;
"""


def customize_script() -> str:
    return f"""#!/system/bin/sh
MODPATH="${{MODPATH:-{MODULE_DIR}}}"

chmod 0755 "$MODPATH/vendor" "$MODPATH/vendor/bin" 2>/dev/null || true
if [ -x /vendor/bin/mdm_helper ] && [ ! -f "$MODPATH/vendor/bin/mdm_helper.real" ]; then
  cp -p /vendor/bin/mdm_helper "$MODPATH/vendor/bin/mdm_helper.real" 2>/dev/null || true
fi
if [ -x /vendor/bin/mdm_helper ] && [ ! -f "$MODPATH/system/vendor/bin/mdm_helper.real" ]; then
  cp -p /vendor/bin/mdm_helper "$MODPATH/system/vendor/bin/mdm_helper.real" 2>/dev/null || true
fi
chmod 0755 "$MODPATH/vendor/bin/mdm_helper" 2>/dev/null || true
chmod 0755 "$MODPATH/vendor/bin/mdm_helper.real" 2>/dev/null || true
chmod 0755 "$MODPATH/vendor/bin/a90_strace" 2>/dev/null || true
chmod 0755 "$MODPATH/system" "$MODPATH/system/vendor" "$MODPATH/system/vendor/bin" 2>/dev/null || true
chmod 0755 "$MODPATH/system/vendor/bin/mdm_helper" 2>/dev/null || true
chmod 0755 "$MODPATH/system/vendor/bin/mdm_helper.real" 2>/dev/null || true
chmod 0755 "$MODPATH/system/vendor/bin/a90_strace" 2>/dev/null || true
chmod 0755 "$MODPATH/post-fs-data.sh" "$MODPATH/service.sh" 2>/dev/null || true
chmod 0644 "$MODPATH/sepolicy.rule" "$MODPATH/module.prop" 2>/dev/null || true
true
"""


def wrapper_script() -> str:
    syscall_filter = ",".join(REQUIRED_SYSCALLS)
    return f"""#!/system/bin/sh
TRACE_DIR="{TRACE_DIR}"
STRACE_BIN="/vendor/bin/a90_strace"
TRACE_OUT="$TRACE_DIR/mdm_helper.strace.txt"
WRAPPER_LOG="$TRACE_DIR/mdm_helper.wrapper.log"

umask 077
mkdir -p "$TRACE_DIR"

{{
  echo "wrapper_start=$(date '+%Y-%m-%dT%H:%M:%S%z') pid=$$ argv=$*"
  id
  cat /proc/self/attr/current 2>/dev/null || true
}} >> "$WRAPPER_LOG" 2>&1

if [ ! -x "$STRACE_BIN" ]; then
  echo "missing executable strace: $STRACE_BIN" >> "$WRAPPER_LOG"
  exit 127
fi

ORIG=""
for candidate in \\
  /sbin/.magisk/mirror/vendor/bin/mdm_helper \\
  /debug_ramdisk/.magisk/mirror/vendor/bin/mdm_helper \\
  /data/adb/modules/{MODULE_ID}/original/mdm_helper
do
  if [ "$candidate" = "/vendor/bin/mdm_helper" ]; then
    continue
  fi
  if [ "$candidate" = "/system/vendor/bin/mdm_helper" ]; then
    continue
  fi
  if [ -x "$candidate" ]; then
    ORIG="$candidate"
    break
  fi
done

if [ -z "$ORIG" ]; then
  echo "original mdm_helper not found in Magisk mirror/original fallback" >> "$WRAPPER_LOG"
  exit 126
fi

case "$ORIG" in
  /vendor/bin/mdm_helper|/system/vendor/bin/mdm_helper|"$0")
    echo "refusing recursive original path: $ORIG" >> "$WRAPPER_LOG"
    exit 126
    ;;
esac

echo "exec_strace=$STRACE_BIN original=$ORIG out=$TRACE_OUT" >> "$WRAPPER_LOG"
exec "$STRACE_BIN" -f -tt -s 256 -e trace={syscall_filter} -o "$TRACE_OUT" "$ORIG" "$@"
"""


def post_fs_data_script() -> str:
    return f"""#!/system/bin/sh
TRACE_DIR="{TRACE_DIR}"
umask 000
rm -rf "$TRACE_DIR" 2>/dev/null || true
mkdir -p "$TRACE_DIR"
chmod 1777 "$TRACE_DIR" 2>/dev/null || true

collect_task_snapshot() {{
  label="$1"
  pid="$2"
  tid="$3"
  dir="$TRACE_DIR/pm_thread_snapshots/${{label}}_${{pid}}_${{tid}}"
  mkdir -p "$dir"
  cat "/proc/$pid/cmdline" > "$dir/cmdline.bin" 2>/dev/null || true
  cat "/proc/$pid/task/$tid/comm" > "$dir/comm.txt" 2>/dev/null || true
  cat "/proc/$pid/task/$tid/status" > "$dir/status.txt" 2>/dev/null || true
  cat "/proc/$pid/task/$tid/wchan" > "$dir/wchan.txt" 2>/dev/null || true
  cat "/proc/$pid/task/$tid/syscall" > "$dir/syscall.txt" 2>/dev/null || true
  cat "/proc/$pid/task/$tid/stack" > "$dir/stack.txt" 2>/dev/null || true
  ls -l "/proc/$pid/fd" > "$dir/fd.txt" 2>&1 || true
}}

sample_pm_threads() {{
  samples="$TRACE_DIR/pm_thread_samples.txt"
  interesting="$TRACE_DIR/pm_thread_interesting.txt"
  summary="$TRACE_DIR/pm_thread_summary.txt"
  mkdir -p "$TRACE_DIR/pm_thread_snapshots"
  i=0
  fw_seen=0
  fw_seen_at=-1
  while [ "$i" -lt 360 ]; do
    uptime="$(cat /proc/uptime 2>/dev/null | awk '{{print $1}}')"
    for proc in /proc/[0-9]*; do
      pid="${{proc##*/}}"
      cmdline="$(tr '\\0' ' ' < "$proc/cmdline" 2>/dev/null)"
      label=""
      case "$cmdline" in
        */vendor/bin/pm-service*|/vendor/bin/pm-service*) label="pm-service" ;;
        */vendor/bin/pm_proxy_helper*|/vendor/bin/pm_proxy_helper*) label="pm_proxy_helper" ;;
        */vendor/bin/mdm_helper.real*|/vendor/bin/mdm_helper.real*) label="mdm_helper_real" ;;
        */vendor/bin/mdm_helper*|/vendor/bin/mdm_helper*) label="mdm_helper" ;;
        */vendor/bin/cnss-daemon*|*/system/vendor/bin/cnss-daemon*) label="cnss-daemon" ;;
      esac
      [ -n "$label" ] || continue
      for task in "$proc"/task/[0-9]*; do
        [ -d "$task" ] || continue
        tid="${{task##*/}}"
        comm="$(cat "$task/comm" 2>/dev/null)"
        wchan="$(cat "$task/wchan" 2>/dev/null)"
        syscall="$(cat "$task/syscall" 2>/dev/null)"
        line="sample=$i uptime=$uptime label=$label pid=$pid tid=$tid comm=$comm wchan=$wchan syscall=$syscall"
        echo "$line" >> "$samples"
        case "$label $comm $wchan $syscall" in
          *Binder*|*binder*|*subsys*|*esoc*|*pil*|*wait*|*ioctl*|*nanosleep*)
            echo "$line" >> "$interesting"
            collect_task_snapshot "$label" "$pid" "$tid"
            ;;
        esac
      done
    done
    if [ "$fw_seen" = "0" ] && dmesg | tail -n 400 | grep -E "WLAN FW is ready|FW ready event received|dev : wlan0 : event : 16" >/dev/null 2>&1; then
      fw_seen=1
      fw_seen_at="$i"
      echo "fw_seen_at_sample=$i uptime=$uptime" >> "$summary"
    fi
    if [ "$fw_seen" = "1" ] && [ "$i" -gt "$((fw_seen_at + 30))" ]; then
      break
    fi
    i=$((i + 1))
    sleep 0.1 2>/dev/null || sleep 1
  done
  {{
    echo "samples=$i"
    echo "fw_seen=$fw_seen"
    echo "fw_seen_at=$fw_seen_at"
    echo "pm_service_pids=$(pidof pm-service 2>/dev/null)"
    echo "pm_proxy_helper_pids=$(pidof pm_proxy_helper 2>/dev/null)"
    echo "mdm_helper_pids=$(pidof mdm_helper mdm_helper.real 2>/dev/null)"
    echo "cnss_daemon_pids=$(pidof cnss-daemon 2>/dev/null)"
  }} >> "$summary"
  dmesg > "$TRACE_DIR/pm_thread_dmesg_end.txt" 2>&1 || true
}}

POLICY_TOOL=""
for candidate in /debug_ramdisk/magiskpolicy /sbin/magiskpolicy /data/adb/magisk/magiskpolicy /system/bin/magiskpolicy; do
  if [ -x "$candidate" ]; then
    POLICY_TOOL="$candidate"
    break
  fi
done

{{
  echo "post_fs_data_start=$(date '+%Y-%m-%dT%H:%M:%S%z') pid=$$"
  id
  getenforce 2>/dev/null || true
  cat /proc/self/attr/current 2>/dev/null || true
  echo "policy_tool=$POLICY_TOOL"
}} >> "$TRACE_DIR/post-fs-data.log" 2>&1

if [ -n "$POLICY_TOOL" ]; then
  "$POLICY_TOOL" --live "allow vendor_mdm_helper system_file dir {{ getattr open read search }}" >> "$TRACE_DIR/post-fs-data.log" 2>&1 || true
  "$POLICY_TOOL" --live "allow vendor_mdm_helper system_file file {{ execute execute_no_trans getattr map open read }}" >> "$TRACE_DIR/post-fs-data.log" 2>&1 || true
  "$POLICY_TOOL" --live "allow vendor_mdm_helper vendor_file dir {{ getattr open read search }}" >> "$TRACE_DIR/post-fs-data.log" 2>&1 || true
  "$POLICY_TOOL" --live "allow vendor_mdm_helper vendor_file file {{ execute execute_no_trans getattr map open read }}" >> "$TRACE_DIR/post-fs-data.log" 2>&1 || true
  "$POLICY_TOOL" --live "allow vendor_mdm_helper shell_data_file dir {{ add_name create getattr open read remove_name search write }}" >> "$TRACE_DIR/post-fs-data.log" 2>&1 || true
  "$POLICY_TOOL" --live "allow vendor_mdm_helper shell_data_file file {{ append create getattr open read setattr unlink write }}" >> "$TRACE_DIR/post-fs-data.log" 2>&1 || true
  "$POLICY_TOOL" --live "allow vendor_mdm_helper vendor_mdm_helper process ptrace" >> "$TRACE_DIR/post-fs-data.log" 2>&1 || true
fi

( sample_pm_threads >> "$TRACE_DIR/pm_thread_sampler.log" 2>&1 ) &
exit 0
"""


def service_script() -> str:
    return f"""#!/system/bin/sh
TRACE_DIR="{TRACE_DIR}"

collect_one_pid() {{
  name="$1"
  pid="$2"
  proc_dir="$TRACE_DIR/proc_${{name}}_${{pid}}"
  mkdir -p "$proc_dir"
  cat "/proc/$pid/cmdline" > "$proc_dir/cmdline.bin" 2>/dev/null || true
  cat "/proc/$pid/status" > "$proc_dir/status.txt" 2>/dev/null || true
  cat "/proc/$pid/wchan" > "$proc_dir/wchan.txt" 2>/dev/null || true
  cat "/proc/$pid/syscall" > "$proc_dir/syscall.txt" 2>/dev/null || true
  cat "/proc/$pid/stack" > "$proc_dir/stack.txt" 2>/dev/null || true
  cat "/proc/$pid/sched" > "$proc_dir/sched.txt" 2>/dev/null || true
  cat "/proc/$pid/attr/current" > "$proc_dir/attr_current.txt" 2>/dev/null || true
  ls -l "/proc/$pid/fd" > "$proc_dir/fd.txt" 2>&1 || true
}}

collect_cmdline_matches() {{
  tag="$1"
  needle="$2"
  for proc in /proc/[0-9]*; do
    pid="${{proc##*/}}"
    cmdline="$(tr '\\0' ' ' < "$proc/cmdline" 2>/dev/null)"
    case "$cmdline" in
      *"$needle"*)
        echo "$tag $pid $cmdline" >> "$TRACE_DIR/pids.txt"
        collect_one_pid "$tag" "$pid"
        ;;
    esac
  done
}}

wifi_ready=0
wifi_ready_reason=timeout
wait_wifi_ready() {{
  j=0
  while [ "$j" -lt 180 ]; do
    if ip link show wlan0 >/dev/null 2>&1; then
      wifi_ready=1
      wifi_ready_reason=wlan0-netdev
      break
    fi
    if dmesg | tail -n 400 | grep -E "WLAN FW is ready|FW ready event received|dev : wlan0 : event : 16|dev : swlan0 : event : 16|dev : p2p0 : event : 16|dev : wifi-aware0 : event : 16" >/dev/null 2>&1; then
      wifi_ready=1
      wifi_ready_reason=dmesg-fw-ready
      break
    fi
    j=$((j + 1))
    sleep 1
  done
  {{
    echo "wifi_ready=$wifi_ready"
    echo "wifi_ready_reason=$wifi_ready_reason"
    echo "wifi_ready_wait_sec=$j"
  }} > "$TRACE_DIR/wifi_ready_wait.txt" 2>/dev/null || true
}}

(
  umask 000
  mkdir -p "$TRACE_DIR"
  chmod 1777 "$TRACE_DIR" 2>/dev/null || true
  umask 077
  echo "service_start=$(date '+%Y-%m-%dT%H:%M:%S%z') pid=$$" >> "$TRACE_DIR/service.log"

  i=0
  while [ "$i" -lt 120 ]; do
    if [ "$(getprop sys.boot_completed 2>/dev/null)" = "1" ]; then
      break
    fi
    i=$((i + 1))
    sleep 1
  done

  wait_wifi_ready
  date '+%Y-%m-%dT%H:%M:%S%z' > "$TRACE_DIR/snapshot_time.txt" 2>/dev/null || true
  getprop > "$TRACE_DIR/getprop.txt" 2>&1 || true
  dmesg > "$TRACE_DIR/boot_dmesg.txt" 2>&1 || true
  ps -AZef > "$TRACE_DIR/ps_azef.txt" 2>&1 || ps -A -Z -f > "$TRACE_DIR/ps_azef.txt" 2>&1 || true
  cat /proc/interrupts > "$TRACE_DIR/interrupts.txt" 2>&1 || true
  cat /sys/kernel/debug/gpio > "$TRACE_DIR/gpio.txt" 2>&1 || true

  : > "$TRACE_DIR/pids.txt"
  for name in mdm_helper ks pm-service pm_proxy_helper cnss-daemon; do
    pids="$(pidof "$name" 2>/dev/null)"
    echo "$name $pids" >> "$TRACE_DIR/pids.txt"
    for pid in $pids; do
      collect_one_pid "$name" "$pid"
    done
  done
  collect_cmdline_matches a90_strace /vendor/bin/a90_strace
  collect_cmdline_matches mdm_helper_real /vendor/bin/mdm_helper.real
) &

exit 0
"""


def scaffold_readme(strace_binary_present: bool, install_ready: bool) -> str:
    return f"""# V1147 A90 mdm_helper strace Magisk scaffold

This directory is host-generated only. It has not been installed on the device.

## State

- `strace_binary_present`: `{strace_binary_present}`
- `install_ready`: `{install_ready}`
- wrapper path: `{WRAPPER_RELATIVE_PATH}`
- vendor wrapper path: `{VENDOR_WRAPPER_RELATIVE_PATH}`
- strace path: `{STRACE_RELATIVE_PATH}`
- vendor strace path: `{VENDOR_STRACE_RELATIVE_PATH}`
- sepolicy path: `{SEPOLICY_RELATIVE_PATH}`
- customize path: `{CUSTOMIZE_RELATIVE_PATH}`
- Android output directory: `{TRACE_DIR}`

## Required live sequence

1. Place a static aarch64 `strace` at the module vendor overlay strace paths if absent.
2. Place the static ELF wrapper at both mdm_helper overlay paths; do not use the shell fallback for live.
3. Zip the contents of `module/` only after re-running the verifier.
4. Install through Magisk, not by directly mutating `/vendor`.
5. Boot Android once and collect `{TRACE_DIR}/`.
6. Disable/remove the module and roll back to native init.

## Capture contract

The wrapper executes:

```sh
strace -f -tt -s 256 -e trace=openat,ioctl,read,write,execve \\
  -o {TRACE_DIR}/mdm_helper.strace.txt <original-mdm_helper> "$@"
```

Expected evidence:

- `openat`: firmware and runtime paths used by `mdm_helper`;
- `ioctl`: `/dev/esoc-0` request sequence such as `ESOC_WAIT_FOR_REQ`;
- `execve`: `ks` spawn timing and argv, or absence;
- `read`/`write`: coarse image-link and MHI pipe activity;
- dmesg/fd/process snapshots from `service.sh`.

## Guardrails

- No native `/dev/subsys_esoc0` retry.
- No native eSoC ioctl.
- No Wi-Fi credentials, scan/connect, DHCP/routes, or external ping.
- No direct vendor partition mutation.
- Do not keep this module installed after capture.
"""


def verify_strace_binary(path: Path | None, store: EvidenceStore) -> dict[str, Any]:
    if path is None:
        return {
            "provided": False,
            "present": False,
            "copied": False,
            "aarch64": False,
            "static_or_no_interp": False,
            "ok": False,
            "reason": "no --strace-binary provided",
        }

    resolved = repo_path(path)
    if not resolved.exists():
        return {
            "provided": True,
            "present": False,
            "copied": False,
            "aarch64": False,
            "static_or_no_interp": False,
            "ok": False,
            "reason": f"missing source binary: {resolved}",
        }

    mode = resolved.stat().st_mode
    if not stat.S_ISREG(mode):
        return {
            "provided": True,
            "present": True,
            "copied": False,
            "aarch64": False,
            "static_or_no_interp": False,
            "ok": False,
            "reason": f"not a regular file: {resolved}",
        }

    file_rc, file_out = run_host_command(["file", str(resolved)], timeout=5)
    readelf_h_rc, readelf_h = run_host_command(["readelf", "-h", str(resolved)], timeout=5)
    readelf_l_rc, readelf_l = run_host_command(["readelf", "-l", str(resolved)], timeout=5)
    readelf_d_rc, readelf_d = run_host_command(["readelf", "-d", str(resolved)], timeout=5)

    aarch64 = "AArch64" in readelf_h or "ARM aarch64" in file_out
    has_interp = "INTERP" in readelf_l
    has_dynamic = "There is no dynamic section" not in readelf_d if readelf_d_rc == 0 else False
    static_or_no_interp = readelf_l_rc == 0 and not has_interp
    ok = aarch64 and static_or_no_interp

    store.write_text("strace-file.txt", file_out if file_rc == 0 else file_out)
    store.write_text("strace-readelf-h.txt", readelf_h)
    store.write_text("strace-readelf-l.txt", readelf_l)
    store.write_text("strace-readelf-d.txt", readelf_d)

    if ok:
        payload = resolved.read_bytes()
        for relative_path in (STRACE_RELATIVE_PATH, VENDOR_STRACE_RELATIVE_PATH):
            target = store.path(relative_path)
            write_private_bytes(target, payload)
            target.chmod(0o700)

    return {
        "provided": True,
        "present": True,
        "copied": ok,
        "aarch64": aarch64,
        "static_or_no_interp": static_or_no_interp,
        "has_interp": has_interp,
        "has_dynamic": has_dynamic,
        "ok": ok,
        "reason": "ok" if ok else "binary is not verified as static/no-interp aarch64",
        "source": str(resolved),
    }


def verify_wrapper_binary(path: Path | None, store: EvidenceStore) -> dict[str, Any]:
    if path is None:
        return {
            "mode": "shell-fallback",
            "provided": False,
            "present": False,
            "copied": False,
            "aarch64": False,
            "static_or_no_interp": False,
            "has_required_markers": False,
            "ok": False,
            "reason": "no --wrapper-binary provided; shell wrapper is scaffold-only after V1149 load_script crash",
        }

    resolved = repo_path(path)
    if not resolved.exists():
        return {
            "mode": "elf",
            "provided": True,
            "present": False,
            "copied": False,
            "aarch64": False,
            "static_or_no_interp": False,
            "has_required_markers": False,
            "ok": False,
            "reason": f"missing source binary: {resolved}",
        }

    mode = resolved.stat().st_mode
    if not stat.S_ISREG(mode):
        return {
            "mode": "elf",
            "provided": True,
            "present": True,
            "copied": False,
            "aarch64": False,
            "static_or_no_interp": False,
            "has_required_markers": False,
            "ok": False,
            "reason": f"not a regular file: {resolved}",
        }

    file_rc, file_out = run_host_command(["file", str(resolved)], timeout=5)
    readelf_h_rc, readelf_h = run_host_command(["readelf", "-h", str(resolved)], timeout=5)
    readelf_l_rc, readelf_l = run_host_command(["readelf", "-l", str(resolved)], timeout=5)
    readelf_d_rc, readelf_d = run_host_command(["readelf", "-d", str(resolved)], timeout=5)
    strings_rc, strings_out = run_host_command(["strings", "-a", str(resolved)], timeout=5)

    aarch64 = "AArch64" in readelf_h or "ARM aarch64" in file_out
    has_interp = "INTERP" in readelf_l
    has_dynamic = "There is no dynamic section" not in readelf_d if readelf_d_rc == 0 else False
    static_or_no_interp = readelf_l_rc == 0 and not has_interp
    markers = {
        "version": "a90_mdm_helper_strace_wrapper v1157" in strings_out,
        "strace_path": "/vendor/bin/a90_strace" in strings_out,
        "trace_out": f"{TRACE_DIR}/mdm_helper.strace.txt" in strings_out,
        "syscall_filter": f"trace={','.join(REQUIRED_SYSCALLS)}" in strings_out,
        "mirror_search": "/sbin/.magisk/mirror/vendor/bin/mdm_helper" in strings_out,
        "original_fallback": f"/data/adb/modules/{MODULE_ID}/original/mdm_helper" in strings_out,
        "recursive_guard": "refusing recursive original path" in strings_out,
    }
    has_required_markers = all(markers.values())
    ok = aarch64 and static_or_no_interp and has_required_markers

    store.write_text("wrapper-file.txt", file_out if file_rc == 0 else file_out)
    store.write_text("wrapper-readelf-h.txt", readelf_h if readelf_h_rc == 0 else readelf_h)
    store.write_text("wrapper-readelf-l.txt", readelf_l)
    store.write_text("wrapper-readelf-d.txt", readelf_d)
    store.write_text(
        "wrapper-strings-grep.txt",
        "\n".join(
            line
            for line in strings_out.splitlines()
            if "mdm_helper" in line or "strace" in line or "trace=" in line or "recursive" in line
        )
        + "\n",
    )

    if ok:
        for relative_path in (WRAPPER_RELATIVE_PATH, VENDOR_WRAPPER_RELATIVE_PATH):
            target = store.path(relative_path)
            write_private_bytes(target, resolved.read_bytes())
            target.chmod(0o700)

    return {
        "mode": "elf",
        "provided": True,
        "present": True,
        "copied": ok,
        "aarch64": aarch64,
        "static_or_no_interp": static_or_no_interp,
        "has_interp": has_interp,
        "has_dynamic": has_dynamic,
        "markers": markers,
        "has_required_markers": has_required_markers,
        "ok": ok,
        "reason": "ok" if ok else "wrapper binary is not verified as static/no-interp aarch64 with required contract markers",
        "source": str(resolved),
        "strings_rc": strings_rc,
    }


def verify_wrapper(text: str) -> dict[str, Any]:
    syscall_filter = ",".join(REQUIRED_SYSCALLS)
    has_syscalls = all(syscall in text for syscall in REQUIRED_SYSCALLS)
    forbidden_exec = any(
        line.strip().startswith("exec /vendor/bin/mdm_helper")
        or line.strip().startswith("exec /system/vendor/bin/mdm_helper")
        for line in text.splitlines()
    )
    return {
        "mode": "shell-fallback",
        "has_f_flag": " -f " in text,
        "has_tt_flag": " -tt " in text,
        "has_s_256": " -s 256 " in text,
        "has_required_syscalls": has_syscalls,
        "syscall_filter": syscall_filter,
        "uses_strace_variable": 'exec "$STRACE_BIN"' in text,
        "uses_original_variable": '"$ORIG" "$@"' in text,
        "has_mirror_search": "/sbin/.magisk/mirror/vendor/bin/mdm_helper" in text,
        "has_original_fallback": f"/data/adb/modules/{MODULE_ID}/original/mdm_helper" in text,
        "has_recursive_guard": "refusing recursive original path" in text,
        "forbidden_direct_exec": forbidden_exec,
        "ok": False,
        "reason": "shell wrapper is scaffold-only after Android vendor init load_script crash",
    }


def verify_sepolicy_rule(text: str) -> dict[str, Any]:
    required_markers = {
        "vendor_mdm_helper": "vendor_mdm_helper" in text,
        "magisk_file_exec": "magisk_file file" in text and "execute_no_trans" in text,
        "adb_data_file_exec": "adb_data_file file" in text and "execute_no_trans" in text,
        "system_file_exec": "system_file file" in text and "execute_no_trans" in text,
        "system_data_file_exec": "system_data_file file" in text and "execute_no_trans" in text,
        "vendor_file_exec": "vendor_file file" in text and "execute_no_trans" in text,
        "shell_data_file_write": "shell_data_file file" in text and "write" in text,
        "self_ptrace": "vendor_mdm_helper process ptrace" in text,
    }
    forbidden_markers = {
        "setenforce": "setenforce" in text,
        "permissive": "permissive" in text.lower(),
        "wifi_credentials": "ssid=" in text.lower() or "psk=" in text.lower() or "passphrase" in text.lower(),
    }
    return {
        "required_markers": required_markers,
        "forbidden_markers": forbidden_markers,
        "ok": all(required_markers.values()) and not any(forbidden_markers.values()),
        "reason": "ok" if all(required_markers.values()) and not any(forbidden_markers.values()) else "sepolicy rule missing required scoped markers or contains forbidden marker",
    }


def verify_customize_script(text: str) -> dict[str, Any]:
    required_markers = {
        "chmod_strace_exec": "vendor/bin/a90_strace" in text and "system/vendor/bin/a90_strace" in text,
        "chmod_wrappers_exec": "vendor/bin/mdm_helper" in text and "system/vendor/bin/mdm_helper" in text,
        "no_permissive": "setenforce" not in text and "permissive" not in text.lower(),
        "no_exit": "exit " not in text,
    }
    return {
        "required_markers": required_markers,
        "ok": all(required_markers.values()),
        "reason": "ok" if all(required_markers.values()) else "customize script missing scoped chmod markers",
    }


def generated_files(root: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        files.append(
            {
                "path": rel,
                "mode": oct(path.stat().st_mode & 0o777),
                "size": path.stat().st_size,
            }
        )
    return files


def build_summary(manifest: dict[str, Any]) -> str:
    rows = [
        ["decision", f"`{manifest['decision']}`"],
        ["pass", f"`{manifest['pass']}`"],
        ["scaffold_ready", f"`{manifest['classification']['scaffold_ready']}`"],
        ["install_ready", f"`{manifest['classification']['install_ready']}`"],
        ["strace_binary_present", f"`{manifest['classification']['strace_binary']['present']}`"],
        ["wrapper_mode", f"`{manifest['classification']['wrapper']['mode']}`"],
        ["wrapper_binary_present", f"`{manifest['classification']['wrapper_binary']['present']}`"],
        ["wrapper_nonrecursive", f"`{manifest['classification']['wrapper']['has_recursive_guard']}`"],
        ["sepolicy_rule_ok", f"`{manifest['classification']['sepolicy_rule']['ok']}`"],
        ["customize_script_ok", f"`{manifest['classification']['customize_script']['ok']}`"],
        ["module_root", f"`{manifest['module_root']}`"],
    ]
    return "\n".join(
        [
            "# V1147 Android mdm_helper strace scaffold summary",
            "",
            markdown_table(["item", "value"], rows),
            "",
            "Generated files:",
            "",
            markdown_table(
                ["path", "mode", "size"],
                [[item["path"], item["mode"], str(item["size"])] for item in manifest["generated_files"]],
            ),
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    out_dir = repo_path(args.out_dir)
    prepare_out_dir(out_dir)
    store = EvidenceStore(out_dir)
    module_root = store.mkdir("module")
    store.mkdir("module/bin")
    store.mkdir("module/system/vendor/bin")
    store.mkdir("module/vendor/bin")
    store.mkdir("module/original")

    write_module_file(store, "module/module.prop", module_prop())
    sepolicy_text = sepolicy_rule()
    write_module_file(store, SEPOLICY_RELATIVE_PATH, sepolicy_text)
    customize_text = customize_script()
    write_exec_text(store, CUSTOMIZE_RELATIVE_PATH, customize_text)
    write_exec_text(store, "module/post-fs-data.sh", post_fs_data_script())
    write_exec_text(store, "module/service.sh", service_script())
    wrapper_text = wrapper_script()
    write_exec_text(store, WRAPPER_RELATIVE_PATH, wrapper_text)
    write_exec_text(store, VENDOR_WRAPPER_RELATIVE_PATH, wrapper_text)
    write_module_file(store, "module/original/README.md", "Optional fallback location for copied original mdm_helper.\n")

    wrapper_info = verify_wrapper(wrapper_text)
    wrapper_binary_info = verify_wrapper_binary(args.wrapper_binary, store)
    sepolicy_info = verify_sepolicy_rule(sepolicy_text)
    customize_info = verify_customize_script(customize_text)
    wrapper_ready = all(
        bool(wrapper_info[key])
        for key in (
            "has_f_flag",
            "has_tt_flag",
            "has_s_256",
            "has_required_syscalls",
            "uses_strace_variable",
            "uses_original_variable",
            "has_mirror_search",
            "has_original_fallback",
            "has_recursive_guard",
        )
    ) and not bool(wrapper_info["forbidden_direct_exec"])
    if wrapper_binary_info["ok"]:
        wrapper_info = {
            "mode": "elf",
            "has_f_flag": True,
            "has_tt_flag": True,
            "has_s_256": True,
            "has_required_syscalls": True,
            "syscall_filter": ",".join(REQUIRED_SYSCALLS),
            "uses_strace_variable": True,
            "uses_original_variable": True,
            "has_mirror_search": bool(wrapper_binary_info["markers"]["mirror_search"]),
            "has_original_fallback": bool(wrapper_binary_info["markers"]["original_fallback"]),
            "has_recursive_guard": bool(wrapper_binary_info["markers"]["recursive_guard"]),
            "forbidden_direct_exec": False,
            "ok": True,
            "reason": "static ELF wrapper verified",
        }
        wrapper_ready = True

    strace_info = verify_strace_binary(args.strace_binary, store)
    install_ready = (
        bool(strace_info["ok"])
        and bool(wrapper_binary_info["ok"])
        and bool(sepolicy_info["ok"])
        and bool(customize_info["ok"])
    )
    scaffold_ready = wrapper_ready and bool(sepolicy_info["ok"]) and bool(customize_info["ok"])

    readme_text = scaffold_readme(strace_binary_present=bool(strace_info["present"]), install_ready=install_ready)
    write_module_file(store, "README.md", readme_text)

    decision = (
        "v1159-magisk-strace-module-vendor-original-strace-wrapper-install-ready"
        if scaffold_ready and install_ready
        else "v1157-magisk-strace-module-scaffold-ready-vendor-original-strace-or-wrapper-required"
    )
    if not scaffold_ready:
        decision = "v1147-magisk-strace-module-scaffold-invalid"

    manifest: dict[str, Any] = {
        "version": "v1159",
        "created_at": now_iso(),
        "decision": decision,
        "pass": scaffold_ready,
        "runner": "scripts/revalidation/native_wifi_android_mdm_helper_strace_module_v1147.py",
        "module_root": str(module_root),
        "readme": str(store.path("README.md")),
        "summary": str(store.path("summary.md")),
        "plan": str(repo_path(PLAN_PATH)),
        "host": collect_host_metadata(),
        "classification": {
            "scaffold_ready": scaffold_ready,
            "install_ready": install_ready,
            "wrapper": wrapper_info,
            "wrapper_binary": wrapper_binary_info,
            "sepolicy_rule": sepolicy_info,
            "customize_script": customize_info,
            "strace_binary": strace_info,
            "android_trace_dir": TRACE_DIR,
            "module_id": MODULE_ID,
        },
        "guardrails": {
            "device_contact_executed": False,
            "android_boot_executed": False,
            "module_install_executed": False,
            "native_subsys_esoc0_retry_executed": False,
            "native_esoc_ioctl_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "boot_partition_write_executed": False,
            "flash_executed": False,
        },
        "generated_files": generated_files(out_dir),
        "source_notes": {
            "strace_filter": f"-f -tt -s 256 -e trace={','.join(REQUIRED_SYSCALLS)}",
            "wrapper_mode_preferred_over_attach": True,
            "selinux_live_check_required": "verify wrapper/original executes under vendor_mdm_helper domain during Android capture",
        },
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_summary(manifest))

    pointer = repo_path(LATEST_POINTER)
    write_private_text(pointer, str(store.path("manifest.json")) + "\n")

    print(json.dumps({"decision": decision, "pass": scaffold_ready, "install_ready": install_ready, "manifest": str(store.path("manifest.json"))}, ensure_ascii=False, sort_keys=True))
    return 0 if scaffold_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
