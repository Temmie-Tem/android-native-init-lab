#!/usr/bin/env python3
"""V1970 Android RIL/QMI producer-side capture handoff.

This runner reuses the proven V1521 Android/Magisk/native-rollback handoff
engine and installs one temporary post-fs-data observer.  The observer performs
only read-only live measurement during a normal Android boot:

- strace `sendmsg/recvmsg/sendto/recvfrom` on `rild`, `cnss-daemon`, and
  `pm-service`.
- unfiltered dmesg/logcat capture to anchor the normal `wlan_pd` UP edge.
- QRTR nameservice lookup enumeration, including WDS/DMS/NAS.

It does not start Wi-Fi HAL work, scan/connect, use credentials, run
DHCP/routes, ping externally, open `/dev/subsys_esoc0`, touch eSoC/PCIe/GDSC,
or write PMIC/GPIO/regulator/platform state.  The only partition writes are the
approved Android boot-image handoff and rollback to native v724.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import shutil
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, ensure_private_dir, write_private_text

import android_rc1_magisk_postfs_sampler_handoff_v1521 as v1521


DEFAULT_OUT_DIR = Path("tmp/wifi/v1970-android-ril-qmi-producer-capture-handoff")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v724.img")
DEFAULT_NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1970_ANDROID_RIL_QMI_PRODUCER_CAPTURE_HANDOFF_2026-06-04.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1970-android-ril-qmi-producer-capture-handoff.txt")

MODULE_NAME = "a90_v1970_ril_qmi"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1970-ril-qmi-producer"
REMOTE_STAGE_PREFIX = "/data/local/tmp/a90_v1970_ril_qmi"
STRACE_SOURCE = Path("external_tools/userland/bin/strace-aarch64-static")
QRTR_NS_PROBE_SOURCE = Path("stage3/linux_init/helpers/a90_qrtr_ns_probe")
QRTR_NS_PROBE_FALLBACKS = (
    QRTR_NS_PROBE_SOURCE,
    Path("tmp/wifi/v270-qrtr-ns-readback/build/a90_qrtr_ns_probe"),
)

ORIGINAL_BUILD_PLAN = v1521.build_plan

WLAN_PD_UP_RE = re.compile(
    r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\].*root_service_service_ind_cb:.*"
    r"msm/modem/wlan_pd.*state:\s*0x1fffffff",
    re.IGNORECASE,
)
PCIE_MHI_RE = re.compile(r"pcie_initialized|mhi_enable|\bMHI\b|mhi_", re.IGNORECASE)
WLFW_RE = re.compile(r"\bWLFW\b|\bwlfw\b|QMI Server Connected|service 69", re.IGNORECASE)
WLAN0_RE = re.compile(r"\bwlan0\b", re.IGNORECASE)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--native-image", type=Path, default=DEFAULT_NATIVE_IMAGE)
    parser.add_argument("--native-expect-version", default=DEFAULT_NATIVE_EXPECT_VERSION)
    parser.add_argument("--android-boot-image", action="append", type=Path, default=[])
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--boot-block", default=v1521.DEFAULT_BOOT_BLOCK)
    parser.add_argument("--remote-android-image", default=v1521.DEFAULT_REMOTE_ANDROID_IMAGE)
    parser.add_argument("--bridge-host", default=v1521.DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=v1521.DEFAULT_BRIDGE_PORT)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--recovery-timeout", type=int, default=240)
    parser.add_argument("--android-timeout", type=int, default=420)
    parser.add_argument("--sampler-samples", type=int, default=280)
    parser.add_argument("--sampler-delay-us", type=int, default=250000)
    parser.add_argument("--sampler-wait-timeout", type=int, default=180)
    parser.add_argument("--strace-binary", type=Path, default=STRACE_SOURCE)
    parser.add_argument("--qrtr-ns-probe-binary", type=Path, default=QRTR_NS_PROBE_SOURCE)
    parser.add_argument("--allow-android-boot-flash", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-native-rollback", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("dry-run")
    subparsers.add_parser("run")
    return parser.parse_args()


def remote_quote(path: str) -> str:
    if not path.startswith("/") or "\x00" in path:
        raise RuntimeError(f"remote path must be absolute: {path}")
    return shlex.quote(path)


def module_prop() -> str:
    return "\n".join(
        [
            f"id={MODULE_NAME}",
            "name=A90 V1970 RIL QMI producer observer",
            "version=1",
            "versionCode=1",
            "author=A90 native-init project",
            "description=Temporary read-only RIL/CNSS/PM QMI producer capture. Remove after capture.",
            "",
        ]
    )


def sepolicy_rule() -> str:
    return """# Temporary V1970 diagnostic policy for read-only capture.
allow magisk self capability sys_ptrace;
allow magisk rild process ptrace;
allow magisk rild process signal;
allow magisk vendor_per_mgr process ptrace;
allow magisk vendor_per_mgr process signal;
allow magisk vendor_wcnss_service process ptrace;
allow magisk vendor_wcnss_service process signal;
allow magisk kernel system syslog_read;
allow magisk proc_kmsg file { getattr open read };
allow magisk vendor_file dir { getattr open read search };
allow magisk vendor_file file { execute execute_no_trans getattr map open read };
allow magisk system_file dir { getattr open read search };
allow magisk system_file file { execute execute_no_trans getattr map open read };
allow magisk shell_data_file dir { add_name create getattr open read remove_name search write };
allow magisk shell_data_file file { append create getattr open read setattr unlink write };
allow magisk adb_data_file dir { add_name create getattr open read remove_name search write };
allow magisk adb_data_file file { append create getattr open read setattr unlink write };
"""


def post_fs_data_script(samples: int, delay_us: int) -> str:
    delay_sec = f"{delay_us / 1_000_000:.3f}"
    return f"""#!/system/bin/sh
OUT={REMOTE_EVIDENCE_DIR}
MOD={REMOTE_MODULE_DIR}
STRACE="$MOD/a90_strace"
QRTR="$MOD/a90_qrtr_ns_probe"
SAMPLES={samples}
DELAY_SEC={delay_sec}
mkdir -p "$OUT" 2>/dev/null
chmod 755 "$OUT" 2>/dev/null
STATUS="$OUT/status.txt"
EVENTS="$OUT/events.log"
PIDS="$OUT/observer-pids.txt"
QRTR_PIDS="$OUT/qrtr-pids.txt"
PROC_SNAP="$OUT/proc-snapshots.txt"
POLICY_LOG="$OUT/policy.log"
QRTR_STARTED=0
FAST_DELAY_SEC=0.020

write_status() {{
  now="$(cat /proc/uptime 2>/dev/null | cut -d' ' -f1)"
  echo "A90_V1970_STATUS $1 $now" > "$STATUS"
  echo "A90_V1521_STATUS $1 $now" >> "$STATUS"
}}

event() {{
  now="$(cat /proc/uptime 2>/dev/null | cut -d' ' -f1)"
  echo "A90_V1970_EVENT uptime=$now $*" >> "$EVENTS"
}}

find_pid_by_cmd() {{
  pattern="$1"
  for proc in /proc/[0-9]*; do
    comm="$(cat "$proc/comm" 2>/dev/null)"
    cmd="$(tr '\\0' ' ' < "$proc/cmdline" 2>/dev/null)"
    case "$comm $cmd" in
      *"$pattern"*) basename "$proc"; return 0 ;;
    esac
  done
  return 1
}}

dump_process_table() {{
  label="$1"
  {{
    echo "A90_V1970_PS label=$label uptime=$(cat /proc/uptime 2>/dev/null | cut -d' ' -f1)"
    ps -AZ 2>&1 || ps -A -o LABEL,PID,PPID,NAME,CMD 2>&1 || ps 2>&1
  }} > "$OUT/ps-az-$label.txt"
}}

policy_allow_pid() {{
  pid="$1"
  label="$2"
  ctx="$(cat "/proc/$pid/attr/current" 2>/dev/null)"
  type="$(echo "$ctx" | sed -n 's/^u:r:\\([^:]*\\):s0.*/\\1/p')"
  echo "label=$label pid=$pid ctx=$ctx type=$type static_policy=1" >> "$POLICY_LOG"
}}

snapshot_proc() {{
  label="$1"
  pid="$2"
  uptime="$(cat /proc/uptime 2>/dev/null | cut -d' ' -f1)"
  {{
    echo "A90_V1970_PROC label=$label pid=$pid uptime=$uptime"
    echo "attr=$(cat "/proc/$pid/attr/current" 2>/dev/null)"
    tr '\\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null; echo
    cat "/proc/$pid/status" 2>/dev/null | grep -E 'Name:|State:|Pid:|PPid:|Uid:|Gid:' || true
    cat "/proc/$pid/wchan" 2>/dev/null || true; echo
    ls -l "/proc/$pid/fd" 2>&1 | head -n 120 || true
  }} >> "$PROC_SNAP"
}}

attach_once() {{
  label="$1"
  pattern="$2"
  out="$OUT/$label.strace.txt"
  marker="$OUT/$label.attached"
  [ -e "$marker" ] && return 0
  pid="$(find_pid_by_cmd "$pattern" 2>/dev/null | head -n 1)"
  [ -n "$pid" ] || return 0
  policy_allow_pid "$pid" "$label"
  snapshot_proc "$label" "$pid"
  if [ -x "$STRACE" ]; then
    "$STRACE" -f -tt -s 9999 -xx -e trace=sendmsg,recvmsg,sendto,recvfrom -p "$pid" -o "$out" >> "$OUT/strace-launch.log" 2>&1 &
    spid=$!
    echo "$label $pid $spid" >> "$PIDS"
    echo "attached label=$label pid=$pid strace_pid=$spid pattern=$pattern" > "$marker"
    event "attached label=$label pid=$pid strace_pid=$spid"
    snapshot_proc "$label" "$pid" &
  else
    echo "missing strace binary: $STRACE" >> "$OUT/strace-launch.log"
  fi
}}

run_qrtr_one() {{
  qlabel="$1"
  service="$2"
  instance="$3"
  out="$4"
  if [ -x "$QRTR" ]; then
    "$QRTR" --service "$service" --instance "$instance" --allow-qrtr-ns-transmit --allow-wildcard-lookup --readback-ms 5000 --max-events 64 > "$out" 2>&1
  else
    echo "missing qrtr ns probe: $QRTR" > "$out"
  fi
  event "qrtr_done label=$qlabel service=$service instance=$instance out=$out"
}}

run_qrtr_matrix() {{
  label="$1"
  event "qrtr_matrix_start label=$label"
  run_qrtr_one "$label-wildcard-all" 0 0 "$OUT/qrtr-$label-wildcard-all.txt"
  run_qrtr_one "$label-wds" 1 4294967295 "$OUT/qrtr-$label-wds-service1.txt"
  run_qrtr_one "$label-dms" 2 4294967295 "$OUT/qrtr-$label-dms-service2.txt"
  run_qrtr_one "$label-nas" 3 4294967295 "$OUT/qrtr-$label-nas-service3.txt"
  event "qrtr_matrix_end label=$label"
}}

all_required_attached() {{
  [ -e "$OUT/rild.attached" ] && [ -e "$OUT/cnss_daemon.attached" ] && [ -e "$OUT/pm_service.attached" ]
}}

maybe_start_qrtr_matrix() {{
  label="$1"
  [ "$QRTR_STARTED" = "0" ] || return 0
  QRTR_STARTED=1
  run_qrtr_matrix "$label" &
  echo "qrtr_matrix_$label 0 $!" >> "$QRTR_PIDS"
  event "qrtr_matrix_background_started label=$label pid=$!"
}}

dump_props() {{
  for p in sys.boot_completed dev.bootcomplete init.svc.ril-daemon init.svc.vendor.ril-daemon init.svc.vendor.ril-daemon1 init.svc.vendor.ril-daemon2 init.svc.vendor.per_mgr init.svc.vendor.pm-service init.svc.cnss-daemon init.svc.vendor.rmt_storage init.svc.vendor.tftp_server ro.boottime.ril-daemon ro.boottime.vendor.ril-daemon ro.boottime.vendor.per_mgr ro.boottime.vendor.pm-service ro.boottime.cnss-daemon ro.boottime.vendor.rmt_storage ro.boottime.vendor.tftp_server; do
    echo "$p=$(getprop "$p" 2>/dev/null)"
  done > "$OUT/props.txt"
}}

start_live_logs() {{
  ( dmesg -w > "$OUT/dmesg-live.txt" 2>&1 ) &
  echo "dmesg_live 0 $!" >> "$PIDS"
  ( logcat -b all -v threadtime > "$OUT/logcat-live.txt" 2>&1 ) &
  echo "logcat_live 0 $!" >> "$PIDS"
}}

stop_live_observers() {{
  if [ -r "$PIDS" ]; then
    while read label pid spid rest; do
      case "$label" in
        rild|cnss_daemon|pm_service|dmesg_live|logcat_live)
          kill -INT "$spid" 2>/dev/null || true
          ;;
      esac
    done < "$PIDS"
    sleep 1
    while read label pid spid rest; do
      case "$label" in
        rild|cnss_daemon|pm_service|dmesg_live|logcat_live)
          kill -TERM "$spid" 2>/dev/null || true
          ;;
      esac
    done < "$PIDS"
  fi
}}

write_status start
event "start samples=$SAMPLES delay_sec=$DELAY_SEC"
dump_process_table early
start_live_logs

i=0
while [ "$i" -lt "$SAMPLES" ]; do
  write_status "sample-$i"
  attach_once rild rild
  attach_once cnss_daemon cnss-daemon
  attach_once pm_service pm-service
  if all_required_attached; then
    maybe_start_qrtr_matrix "post-attach-$i"
  fi
  case "$i" in
    160)
      maybe_start_qrtr_matrix "fallback-$i"
      ;;
  esac
  i=$((i + 1))
  if all_required_attached; then
    sleep "$DELAY_SEC" 2>/dev/null || sleep 1
  else
    sleep "$FAST_DELAY_SEC" 2>/dev/null || sleep 1
  fi
done

write_status finalizing
dump_process_table late
dump_props
if [ -r "$QRTR_PIDS" ]; then
  while read label pid spid rest; do
    wait "$spid" 2>/dev/null || true
  done < "$QRTR_PIDS"
fi
dmesg > "$OUT/dmesg-full-final.txt" 2>&1 || true
logcat -d -b all -v threadtime > "$OUT/logcat-dump-final.txt" 2>&1 || true
stop_live_observers
sync
touch "$OUT/done"
write_status done
event done
exit 0
"""


def module_stage_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "magisk-module"


def prepare_module(store: EvidenceStore, args: argparse.Namespace, execute: bool) -> v1521.StepResult:
    started = time.monotonic()
    if not execute:
        return v1521.write_step(
            store,
            "prepare-v1970-magisk-module",
            "host:prepare temporary RIL QMI producer Magisk module",
            "[dry-run] not executed\n",
            "",
            0,
            0.0,
            skipped=True,
            ok_override=True,
        )

    stage = module_stage_dir(store)
    ensure_private_dir(stage)
    strace_path = repo_path(args.strace_binary)
    qrtr_candidates = [repo_path(args.qrtr_ns_probe_binary)]
    qrtr_candidates.extend(repo_path(path) for path in QRTR_NS_PROBE_FALLBACKS if repo_path(path) not in qrtr_candidates)
    qrtr_path = next((path for path in qrtr_candidates if path.exists()), qrtr_candidates[0])
    if not strace_path.exists():
        raise RuntimeError(f"missing static strace binary: {strace_path}")
    if not qrtr_path.exists():
        raise RuntimeError(
            "missing QRTR NS probe binary; checked "
            + ", ".join(str(path) for path in qrtr_candidates)
        )

    write_private_text(stage / "module.prop", module_prop())
    write_private_text(stage / "post-fs-data.sh", post_fs_data_script(args.sampler_samples, args.sampler_delay_us))
    write_private_text(stage / "sepolicy.rule", sepolicy_rule())
    shutil.copy2(strace_path, stage / "a90_strace")
    shutil.copy2(qrtr_path, stage / "a90_qrtr_ns_probe")
    (stage / "post-fs-data.sh").chmod(0o700)
    (stage / "a90_strace").chmod(0o700)
    (stage / "a90_qrtr_ns_probe").chmod(0o700)
    (stage / "sepolicy.rule").chmod(0o600)

    text = "\n".join(
        [
            f"module_dir={stage}",
            f"strace_binary={strace_path}",
            f"qrtr_ns_probe_binary={qrtr_path}",
            f"samples={args.sampler_samples}",
            f"delay_us={args.sampler_delay_us}",
            "files=module.prop post-fs-data.sh sepolicy.rule a90_strace a90_qrtr_ns_probe",
            "",
        ]
    )
    return v1521.write_step(
        store,
        "prepare-v1970-magisk-module",
        "host:prepare temporary RIL QMI producer Magisk module",
        text,
        "",
        0,
        time.monotonic() - started,
    )


def install_module_android_steps(args: argparse.Namespace, store: EvidenceStore) -> list[tuple[str, list[str], int]]:
    stage = module_stage_dir(store)
    remote_prop = f"{REMOTE_STAGE_PREFIX}_module.prop"
    remote_postfs = f"{REMOTE_STAGE_PREFIX}_post-fs-data.sh"
    remote_policy = f"{REMOTE_STAGE_PREFIX}_sepolicy.rule"
    remote_strace = f"{REMOTE_STAGE_PREFIX}_a90_strace"
    remote_qrtr = f"{REMOTE_STAGE_PREFIX}_a90_qrtr_ns_probe"
    install_shell = (
        f"rm -rf {remote_quote(REMOTE_MODULE_DIR)} {remote_quote(REMOTE_EVIDENCE_DIR)}; "
        f"mkdir -p {remote_quote(REMOTE_MODULE_DIR)}; "
        f"cp {remote_quote(remote_prop)} {remote_quote(REMOTE_MODULE_DIR)}/module.prop; "
        f"cp {remote_quote(remote_postfs)} {remote_quote(REMOTE_MODULE_DIR)}/post-fs-data.sh; "
        f"cp {remote_quote(remote_policy)} {remote_quote(REMOTE_MODULE_DIR)}/sepolicy.rule; "
        f"cp {remote_quote(remote_strace)} {remote_quote(REMOTE_MODULE_DIR)}/a90_strace; "
        f"cp {remote_quote(remote_qrtr)} {remote_quote(REMOTE_MODULE_DIR)}/a90_qrtr_ns_probe; "
        f"chmod 600 {remote_quote(REMOTE_MODULE_DIR)}/module.prop {remote_quote(REMOTE_MODULE_DIR)}/sepolicy.rule; "
        f"chmod 700 {remote_quote(REMOTE_MODULE_DIR)}/post-fs-data.sh "
        f"{remote_quote(REMOTE_MODULE_DIR)}/a90_strace {remote_quote(REMOTE_MODULE_DIR)}/a90_qrtr_ns_probe; "
        f"rm -f {remote_quote(remote_prop)} {remote_quote(remote_postfs)} {remote_quote(remote_policy)} "
        f"{remote_quote(remote_strace)} {remote_quote(remote_qrtr)}; "
        "sync"
    )
    return [
        ("push-v1970-module-prop-android", [*v1521.adb_base(args), "push", str(stage / "module.prop"), remote_prop], args.timeout),
        ("push-v1970-post-fs-data-android", [*v1521.adb_base(args), "push", str(stage / "post-fs-data.sh"), remote_postfs], args.timeout),
        ("push-v1970-sepolicy-android", [*v1521.adb_base(args), "push", str(stage / "sepolicy.rule"), remote_policy], args.timeout),
        ("push-v1970-strace-android", [*v1521.adb_base(args), "push", str(stage / "a90_strace"), remote_strace], args.timeout * 2),
        ("push-v1970-qrtr-ns-probe-android", [*v1521.adb_base(args), "push", str(stage / "a90_qrtr_ns_probe"), remote_qrtr], args.timeout * 2),
        ("install-v1970-module-android-su", [*v1521.adb_base(args), "shell", "su", "-c", shlex.quote(install_shell)], args.timeout),
    ]


def cleanup_module_android_command(args: argparse.Namespace) -> list[str]:
    shell = (
        f"rm -rf {remote_quote(REMOTE_MODULE_DIR)} {remote_quote(REMOTE_EVIDENCE_DIR)} "
        f"{remote_quote(REMOTE_STAGE_PREFIX)}_*; sync"
    )
    return [*v1521.adb_base(args), "shell", "su", "-c", shlex.quote(shell)]


def cleanup_module_recovery_best_effort_command(args: argparse.Namespace) -> list[str]:
    return [
        *v1521.adb_base(args),
        "shell",
        (
            f"rm -rf {remote_quote(REMOTE_MODULE_DIR)} {remote_quote(REMOTE_EVIDENCE_DIR)} "
            f"{remote_quote(REMOTE_STAGE_PREFIX)}_* 2>/dev/null || true; sync"
        ),
    ]


def build_plan_v1970(args: argparse.Namespace,
                     store: EvidenceStore,
                     android_image: Any,
                     native_image: Any) -> list[tuple[str, list[str] | str, int]]:
    plan = ORIGINAL_BUILD_PLAN(args, store, android_image, native_image)
    plan.append(("post-rollback-native-selftest", ["python3", "scripts/revalidation/a90ctl.py", "selftest"], args.timeout))
    return plan


def read_file(path: Path, limit: int = 15_000_000) -> str:
    if not path.exists():
        return ""
    return path.read_bytes()[:limit].decode("utf-8", errors="replace")


def evidence_base(store: EvidenceStore) -> Path:
    root = v1521.pulled_evidence_dir(store)
    candidate = root / "a90-v1970-ril-qmi-producer"
    return candidate if candidate.is_dir() else root


def first_dmesg_time(text: str, pattern: re.Pattern[str]) -> float | None:
    for line in text.splitlines():
        match = pattern.search(line)
        if not match:
            continue
        if "ts" in match.groupdict():
            return float(match.group("ts"))
        prefix = re.match(r"^\[\s*([0-9]+(?:\.[0-9]+)?)\]", line.strip())
        if prefix:
            return float(prefix.group(1))
    return None


def count_lines(text: str, pattern: str | re.Pattern[str]) -> int:
    regex = re.compile(pattern, re.IGNORECASE) if isinstance(pattern, str) else pattern
    return sum(1 for line in text.splitlines() if regex.search(line))


def parse_attach_times(events: str) -> dict[str, float]:
    attach_times: dict[str, float] = {}
    regex = re.compile(r"A90_V1970_EVENT uptime=([0-9.]+) attached label=(\S+)")
    for line in events.splitlines():
        match = regex.search(line)
        if match:
            attach_times[match.group(2)] = float(match.group(1))
    return attach_times


def parse_qrtr_file(path: Path) -> dict[str, Any]:
    text = read_file(path, limit=1_000_000)
    values: dict[str, str] = {}
    events: list[dict[str, str]] = []
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
        match = re.match(r"qrtr_ns\.event\.(\d+)\.(service|instance|node|port|type|empty)$", key.strip())
        if match:
            index = int(match.group(1))
            while len(events) <= index:
                events.append({})
            events[index][match.group(2)] = value.strip()
    service_events = int(values.get("qrtr_ns.readback.service_events", "0") or 0)
    present_services = sorted({event.get("service", "") for event in events if event.get("service", "") not in {"", "0"}})
    return {
        "file": str(path),
        "status": values.get("qrtr_ns.status", ""),
        "service": values.get("qrtr_ns.service", ""),
        "instance": values.get("qrtr_ns.instance", ""),
        "service_events": service_events,
        "present_services": present_services,
        "events": [event for event in events if event][:32],
    }


def analyze_pulled_evidence(store: EvidenceStore) -> dict[str, Any]:
    root = v1521.pulled_evidence_dir(store)
    base = evidence_base(store)
    dmesg_full = read_file(base / "dmesg-full-final.txt")
    dmesg_live = read_file(base / "dmesg-live.txt")
    logcat_dump = read_file(base / "logcat-dump-final.txt")
    events = read_file(base / "events.log")
    status = read_file(base / "status.txt")
    props = read_file(base / "props.txt")
    policy = read_file(base / "policy.log")
    launch = read_file(base / "strace-launch.log")
    attach_times = parse_attach_times(events)
    combined_dmesg = "\n".join(part for part in (dmesg_full, dmesg_live, read_file(root / "host-dmesg-filtered.txt")) if part)
    wlanpd_up_time = first_dmesg_time(combined_dmesg, WLAN_PD_UP_RE)
    pcie_mhi_time = first_dmesg_time(combined_dmesg, PCIE_MHI_RE)
    normal_android_window = wlanpd_up_time is not None and wlanpd_up_time <= 90.0 and (
        pcie_mhi_time is None or pcie_mhi_time > wlanpd_up_time
    )
    required_labels = ("rild", "cnss_daemon", "pm_service")
    producer_window_strace = bool(
        wlanpd_up_time is not None
        and all((attach_times.get(label) is not None and attach_times[label] <= wlanpd_up_time) for label in required_labels)
    )
    strace: dict[str, dict[str, Any]] = {}
    for label in ("rild", "cnss_daemon", "pm_service"):
        text = read_file(base / f"{label}.strace.txt")
        strace[label] = {
            "present": bool(text),
            "lines": text.count("\n"),
            "send_lines": count_lines(text, r"\bsendmsg\(|\bsendto\("),
            "recv_lines": count_lines(text, r"\brecvmsg\(|\brecvfrom\("),
            "qipcrtr_lines": count_lines(text, r"AF_QIPCRTR|sockaddr_qrtr|sq_node|sq_port"),
            "excerpt": "\n".join(text.splitlines()[:8] + text.splitlines()[-8:]) if text else "",
        }
    qrtr_files = sorted(base.glob("qrtr-*.txt"))
    qrtr = [parse_qrtr_file(path) for path in qrtr_files]
    wildcard_services = {
        service
        for item in qrtr
        if "wildcard-all" in item["file"]
        for service in item.get("present_services", [])
    }
    targeted = {
        "wds": sum(item["service_events"] for item in qrtr if "wds-service1" in item["file"]) + (1 if "1" in wildcard_services else 0),
        "dms": sum(item["service_events"] for item in qrtr if "dms-service2" in item["file"]) + (1 if "2" in wildcard_services else 0),
        "nas": sum(item["service_events"] for item in qrtr if "nas-service3" in item["file"]) + (1 if "3" in wildcard_services else 0),
        "wildcard": sum(item["service_events"] for item in qrtr if "wildcard-all" in item["file"]),
    }
    files_present = {
        "samples": bool(events),
        "dmesg": bool(dmesg_full or dmesg_live),
        "done": (base / "done").exists(),
        "status": bool(status),
        "events": bool(events),
        "dmesg_full": bool(dmesg_full),
        "logcat_dump": bool(logcat_dump),
        "props": bool(props),
        "policy": bool(policy),
        "strace_launch": bool(launch),
        "rild_strace": strace["rild"]["present"],
        "cnss_daemon_strace": strace["cnss_daemon"]["present"],
        "pm_service_strace": strace["pm_service"]["present"],
        "qrtr_files": bool(qrtr_files),
    }
    return {
        "base": str(base),
        "files_present": files_present,
        "status_text": status.strip(),
        "events_excerpt": events[-8000:],
        "props_text": props.strip(),
        "policy_excerpt": policy[-8000:],
        "strace_launch_excerpt": launch[-8000:],
        "attach_times": attach_times,
        "dmesg": {
            "wlanpd_up_time": wlanpd_up_time,
            "first_pcie_mhi_time": pcie_mhi_time,
            "normal_android_window": normal_android_window,
            "producer_window_strace": producer_window_strace,
            "wlanpd_up_lines": count_lines(combined_dmesg, WLAN_PD_UP_RE),
            "wlfw_lines": count_lines(combined_dmesg + "\n" + logcat_dump, WLFW_RE),
            "bdf_lines": count_lines(combined_dmesg + "\n" + logcat_dump, r"BDF file|regdb\.bin|bdwlan\.bin"),
            "wlan0_lines": count_lines(combined_dmesg + "\n" + logcat_dump, WLAN0_RE),
            "pcie_mhi_lines": count_lines(combined_dmesg, PCIE_MHI_RE),
        },
        "strace": strace,
        "qrtr": {
            "file_count": len(qrtr_files),
            "targeted_service_events": targeted,
            "files": qrtr[:20],
        },
        "sample_count": events.count("A90_V1970_EVENT"),
        "matched_window": {
            "first_lower_time": wlanpd_up_time,
            "has_pre_lower_sample": bool(events),
            "has_post_lower_sample": bool(status and "done" in status),
            "has_pre_l0_sample": False,
            "has_post_l0_sample": False,
        },
    }


def rollback_selftest_ok(store: EvidenceStore, steps: list[v1521.StepResult]) -> bool:
    for step in steps:
        if step.name == "post-rollback-native-selftest":
            return bool(re.search(r"selftest:\s+pass=\d+\s+warn=\d+\s+fail=0\b", v1521.step_text(store, step)))
    return False


def classify_result(base_decision: str,
                    base_pass: bool,
                    analysis: dict[str, Any],
                    selftest_ok: bool) -> tuple[str, bool, str, str]:
    if not selftest_ok:
        return (
            "v1970-rollback-selftest-failed",
            False,
            "native rollback did not prove selftest fail=0",
            "rollback-selftest-failed",
        )
    if not base_pass:
        return (
            f"v1970-base-handoff-failed-{base_decision}",
            False,
            "underlying Android handoff did not complete cleanly",
            "base-handoff-failed",
        )
    dmesg = analysis.get("dmesg") or {}
    if not dmesg.get("normal_android_window"):
        return (
            "v1970-reject-degraded-or-unanchoored-android-window",
            False,
            "capture did not prove normal early wlan_pd UP before any PCIe/MHI path",
            "reject-degraded-window",
        )
    if not dmesg.get("producer_window_strace"):
        return (
            "v1970-strace-attached-after-wlanpd-up-rollback-pass",
            False,
            "normal Android wlan_pd UP was anchored, but required straces attached after the producer window",
            "producer-window-missed",
        )
    strace = analysis.get("strace") or {}
    strace_complete = all((strace.get(label) or {}).get("present") for label in ("rild", "cnss_daemon", "pm_service"))
    qrtr_targeted = ((analysis.get("qrtr") or {}).get("targeted_service_events") or {})
    qrtr_complete = all(int(qrtr_targeted.get(label) or 0) > 0 for label in ("wds", "dms", "nas"))
    if strace_complete and qrtr_complete:
        return (
            "v1970-android-ril-qmi-producer-capture-complete-rollback-pass",
            True,
            "normal Android wlan_pd UP anchored; rild/cnss/pm-service strace and WDS/DMS/NAS QRTR enumeration captured; native rollback selftest fail=0",
            "android-ril-qmi-producer-capture-complete",
        )
    if strace_complete:
        return (
            "v1970-android-ril-qmi-strace-complete-qrtr-partial-rollback-pass",
            False,
            "normal Android strace captured, but WDS/DMS/NAS QRTR enumeration was incomplete",
            "qrtr-enumeration-partial",
        )
    return (
        "v1970-android-ril-qmi-producer-capture-partial-rollback-pass",
        False,
        "normal Android window captured, but one or more required process straces are missing",
        "strace-capture-partial",
    )


def configure_v1521_engine() -> None:
    v1521.MODULE_NAME = MODULE_NAME
    v1521.REMOTE_MODULE_DIR = REMOTE_MODULE_DIR
    v1521.REMOTE_EVIDENCE_DIR = REMOTE_EVIDENCE_DIR
    v1521.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1521.DEFAULT_NATIVE_IMAGE = DEFAULT_NATIVE_IMAGE
    v1521.DEFAULT_NATIVE_EXPECT_VERSION = DEFAULT_NATIVE_EXPECT_VERSION
    v1521.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    v1521.LATEST_POINTER = LATEST_POINTER
    v1521.module_prop = module_prop
    v1521.post_fs_data_script = post_fs_data_script
    v1521.prepare_module = prepare_module
    v1521.install_module_android_steps = install_module_android_steps
    v1521.cleanup_module_android_command = cleanup_module_android_command
    v1521.cleanup_module_recovery_best_effort_command = cleanup_module_recovery_best_effort_command
    v1521.analyze_pulled_evidence = analyze_pulled_evidence
    v1521.build_plan = build_plan_v1970


def render_summary(manifest: dict[str, Any]) -> str:
    context = manifest["context"]
    analysis = context.get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    strace = analysis.get("strace") or {}
    qrtr = analysis.get("qrtr") or {}
    attach_times = analysis.get("attach_times") or {}
    strace_stats = {
        label: {
            key: value
            for key, value in (strace.get(label) or {}).items()
            if key in {"present", "lines", "send_lines", "recv_lines", "qipcrtr_lines"}
        }
        for label in ("rild", "cnss_daemon", "pm_service")
    }
    return "\n".join(
        [
            "# V1970 Android RIL/QMI Producer Capture Handoff",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- label: `{manifest['label']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- evidence: `{manifest['out_dir']}`",
            f"- native rollback selftest fail=0: `{manifest['rollback_selftest_fail0']}`",
            f"- base decision: `{manifest.get('base_decision')}`",
            f"- original base decision: `{manifest.get('base_decision_original', manifest.get('base_decision'))}`",
            "",
            "## Capture Result",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["wlan_pd UP time", dmesg.get("wlanpd_up_time")],
                    ["attach times", json.dumps(attach_times, sort_keys=True)],
                    ["first PCIe/MHI time", dmesg.get("first_pcie_mhi_time")],
                    ["normal Android window", dmesg.get("normal_android_window")],
                    ["producer-window strace", dmesg.get("producer_window_strace")],
                    ["wlan_pd/WLFW/wlan0 lines", f"{dmesg.get('wlanpd_up_lines')}/{dmesg.get('wlfw_lines')}/{dmesg.get('wlan0_lines')}"],
                    ["strace rild", json.dumps(strace_stats.get("rild") or {}, sort_keys=True)],
                    ["strace cnss-daemon", json.dumps(strace_stats.get("cnss_daemon") or {}, sort_keys=True)],
                    ["strace pm-service", json.dumps(strace_stats.get("pm_service") or {}, sort_keys=True)],
                    ["QRTR targeted events", json.dumps(qrtr.get("targeted_service_events") or {}, sort_keys=True)],
                    ["files", json.dumps(analysis.get("files_present") or {}, sort_keys=True)],
                ],
            ),
            "",
            "## Scope",
            "",
            "One rollbackable Android handoff. The module writes only to `/data/local/tmp/a90-v1970-ril-qmi-producer` and `/data/adb/modules/a90_v1970_ril_qmi`, removes both before native restore, and appends `a90ctl selftest` after rollback. It captures live strace, dmesg/logcat, process tables, and QRTR nameservice lookup output only.",
            "",
            "## Safety",
            "",
            "No Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, PMIC/GPIO/GDSC/regulator writes, fake ONLINE state, or sda29 remount-write is performed. The only partition writes are the declared Android boot handoff and rollback to `stage3/boot_linux_v724.img`.",
            "",
            "## Next",
            "",
            "- Use V1971 for the decoded post-UP RIL DMS/NAS payloads from this capture.",
            "- For a decisive producer-side trace, rerun with strace attached before the QRTR matrix so `rild`, `cnss-daemon`, and `pm-service` are attached before `wlan_pd` UP.",
            "",
            "## Steps",
            "",
            markdown_table(
                ["step", "status", "rc", "duration", "file"],
                [
                    [
                        item["name"],
                        "skip" if item["skipped"] else ("ok" if item["ok"] else "fail"),
                        item["rc"],
                        f"{item['duration_sec']:.3f}s",
                        item["file"],
                    ]
                    for item in manifest["steps"]
                ],
            ),
            "",
        ]
    )


def main() -> int:
    configure_v1521_engine()
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    execute = args.command == "run"
    steps, context, base_decision, base_pass = v1521.execute_plan(args, store, execute=execute)
    selftest_ok = rollback_selftest_ok(store, steps) if execute else False
    if execute:
        analysis = context.get("analysis") or {}
        decision, pass_ok, reason, label = classify_result(base_decision, base_pass, analysis, selftest_ok)
    else:
        label = "plan-ready" if args.command == "plan" else "dryrun-ready"
        decision = "v1970-android-ril-qmi-producer-capture-plan-ready" if args.command == "plan" else "v1970-android-ril-qmi-producer-capture-dryrun-ready"
        pass_ok = bool(base_pass)
        reason = "plan/dry-run completed without Android live capture"

    manifest = {
        "cycle": "V1970",
        "generated_at": now_iso(),
        "command": args.command,
        "base_decision": base_decision,
        "base_pass": base_pass,
        "decision": decision,
        "label": label,
        "pass": pass_ok,
        "reason": reason,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "context": context,
        "steps": [asdict(step) for step in steps],
        "rollback_selftest_fail0": selftest_ok,
        "device_commands_executed": execute,
        "device_mutations": execute,
        "temporary_magisk_module_executed": execute,
        "temporary_magisk_module_cleanup_requested": execute,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "pmic_gpio_gdsc_write_executed": False,
        "blind_esoc_notify_executed": False,
        "boot_done_spoof_executed": False,
        "global_pci_rescan_executed": False,
        "platform_bind_unbind_executed": False,
        "subsys_esoc0_open_executed": False,
        "flash_executed": execute,
        "boot_image_write_executed": execute,
        "partition_write_executed": False,
    }
    summary = render_summary(manifest)
    leaks = v1521.check_forbidden_output(manifest, summary)
    manifest["forbidden_output_env_hits"] = leaks
    if leaks:
        manifest["decision"] = "v1970-forbidden-output-hit"
        manifest["label"] = "forbidden-output-hit"
        manifest["pass"] = False
        manifest["reason"] = "forbidden environment-backed output string detected"
        summary = render_summary(manifest)

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(DEFAULT_REPORT_PATH), summary)
    print(f"decision: {manifest['decision']}")
    print(f"label:    {manifest['label']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
