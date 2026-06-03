#!/usr/bin/env python3
"""V1934 Android-good libqmi service-69 publication positive control.

This reuses the rollbackable V1899 Android handoff engine and adds one extra
read-only userland tracefs uprobe group for `/vendor/lib64/libqmi_cci.so`.
The goal is to capture the normal Android service-69 publication edge that
native V1930 lacked: WLFW service lookup for QMI service 0x45 followed by a
libqmi new-server event for the same service.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

import android_cnss_qrtr_stateup_handoff_v1899 as base
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


CYCLE = "V1934"
DEFAULT_OUT_DIR = Path("tmp/wifi/v1934-android-libqmi-service69-positive-control")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1934_ANDROID_LIBQMI_SERVICE69_POSITIVE_CONTROL_2026-06-04.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1934-android-libqmi-service69-positive-control.txt")
MODULE_NAME = "a90_v1934_libqmi69"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1934-libqmi69"
REMOTE_STAGE_PREFIX = "/data/local/tmp/a90_v1934_libqmi69"
TRACEFS_GROUP = "a90libqmi1934"

BASE_POST_FS_DATA_SCRIPT = base.post_fs_data_script
BASE_ANALYZE = base.analyze_pulled_evidence
BASE_PARSER_COMMANDS = base.parser_commands

LIBQMI_EVENT_NAMES = (
    "libqmi_get_service_list_entry",
    "libqmi_get_service_list_lookup_call",
    "libqmi_get_service_list_lookup_ret",
    "libqmi_client_init_instance_entry",
    "libqmi_initial_get_service_instance_ret",
    "libqmi_initial_client_init_ret",
    "libqmi_notifier_init_call",
    "libqmi_notifier_init_ret",
    "libqmi_wait_call",
    "libqmi_wait_return",
    "libqmi_loop_get_service_instance_ret",
    "libqmi_loop_client_init_ret",
    "libqmi_init_timeout_path",
    "libqmi_init_return",
    "libqmi_signal_wait_entry",
    "libqmi_signal_wait_timedwait",
    "libqmi_signal_wait_timeout_store",
    "libqmi_xport_new_server_entry",
    "libqmi_xport_new_server_service",
    "libqmi_xport_new_server_signal",
    "libqmi_xport_new_server_callback_call",
)

SERVICE_RE = re.compile(r"\bsvc_id=(0x[0-9a-fA-F]+|\d+)\b")
FOUND_RE = re.compile(r"\bfound=(0x[0-9a-fA-F]+|\d+)\b")
THREAD_RE = re.compile(r"\S+-(\d+)\s+\[\d+\]")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def module_prop() -> str:
    return "\n".join(
        [
            f"id={MODULE_NAME}",
            "name=A90 V1934 Android libqmi service69 observer",
            "version=1",
            "versionCode=1",
            "author=A90 native-init project",
            "description=Temporary Android-good libqmi service69 positive-control observer. Remove after capture.",
            "",
        ]
    )


def patch_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise RuntimeError(f"post-fs-data patch anchor not found: {old[:80]!r}")
    return text.replace(old, new, 1)


def post_fs_data_script(samples: int, delay_us: int) -> str:
    text = BASE_POST_FS_DATA_SCRIPT(samples, delay_us)
    text = patch_once(
        text,
        'QRTR_SUMMARY="$OUT/qrtr-kprobe-summary.txt"\nTRACE_EVENTS=',
        'QRTR_SUMMARY="$OUT/qrtr-kprobe-summary.txt"\n'
        'LIBQMI_UPROBE="$OUT/libqmi-uprobe-trace.txt"\n'
        'LIBQMI_UPROBE_SUMMARY="$OUT/libqmi-uprobe-summary.txt"\n'
        'TRACE_EVENTS=',
    )
    text = patch_once(
        text,
        "QRTR_KPROBE_ARMED=0\nORIG_TRACING_ON=",
        "QRTR_KPROBE_ARMED=0\nLIBQMI_UPROBE_ARMED=0\nORIG_TRACING_ON=",
    )
    text = patch_once(
        text,
        "return 1\n}\n\ndump_tracefs_catalog()",
        "return 1\n}\n\n"
        "select_libqmi_service() {\n"
        "  for p in /vendor/lib64/libqmi_cci.so /mnt/vendor/lib64/libqmi_cci.so /vendor/lib/libqmi_cci.so /mnt/vendor/lib/libqmi_cci.so; do\n"
        "    if [ -r \"$p\" ]; then\n"
        "      LIBQMI_SERVICE=\"$p\"\n"
        "      return 0\n"
        "    fi\n"
        "  done\n"
        "  return 1\n"
        "}\n\n"
        "dump_tracefs_catalog()",
    )
    text = patch_once(
        text,
        '[ "$UPROBE_ARMED" = "1" ] || [ "$CNSS_UPROBE_ARMED" = "1" ] || [ "$QRTR_KPROBE_ARMED" = "1" ] || return 0',
        '[ "$UPROBE_ARMED" = "1" ] || [ "$CNSS_UPROBE_ARMED" = "1" ] || [ "$QRTR_KPROBE_ARMED" = "1" ] || [ "$LIBQMI_UPROBE_ARMED" = "1" ] || return 0',
    )
    text = patch_once(
        text,
        "  if [ -e \"$TRACE_ROOT/kprobe_events\" ]; then\n",
        "  for label in "
        + " ".join(LIBQMI_EVENT_NAMES)
        + "; do\n"
        "    if [ -e \"$TRACE_ROOT/events/$GROUP/$label/enable\" ]; then\n"
        "      echo 0 > \"$TRACE_ROOT/events/$GROUP/$label/enable\" 2>/dev/null || true\n"
        "    fi\n"
        "  done\n"
        "  for label in "
        + " ".join(LIBQMI_EVENT_NAMES)
        + "; do\n"
        "    echo \"-:$GROUP/$label\" >> \"$TRACE_ROOT/uprobe_events\" 2>/dev/null || true\n"
        "  done\n"
        "  if [ -e \"$TRACE_ROOT/kprobe_events\" ]; then\n",
    )
    text = patch_once(
        text,
        'echo "cleanup_done=1" >> "$QRTR_SUMMARY"\n}',
        'echo "cleanup_done=1" >> "$QRTR_SUMMARY"\n'
        '  echo "cleanup_done=1" >> "$LIBQMI_UPROBE_SUMMARY"\n'
        "}",
    )
    text = patch_once(
        text,
        'register_cnss_uprobe_event() {\n  label="$1"\n  offset="$2"\n  fetch="$3"\n  register_user_uprobe_event "$label" "$CNSS_SERVICE" "$offset" "$fetch" "$CNSS_UPROBE_SUMMARY"\n}\n\nregister_kprobe_event()',
        'register_cnss_uprobe_event() {\n  label="$1"\n  offset="$2"\n  fetch="$3"\n  register_user_uprobe_event "$label" "$CNSS_SERVICE" "$offset" "$fetch" "$CNSS_UPROBE_SUMMARY"\n}\n\n'
        'register_libqmi_uprobe_event() {\n'
        '  label="$1"\n'
        '  offset="$2"\n'
        '  fetch="$3"\n'
        '  register_user_uprobe_event "$label" "$LIBQMI_SERVICE" "$offset" "$fetch" "$LIBQMI_UPROBE_SUMMARY"\n'
        '}\n\n'
        "register_kprobe_event()",
    )
    text = patch_once(
        text,
        "arm_qrtr_kprobes() {",
        "arm_libqmi_uprobes() {\n"
        "  [ \"$LIBQMI_UPROBE_ARMED\" = \"0\" ] || return 0\n"
        "  : > \"$LIBQMI_UPROBE_SUMMARY\"\n"
        "  echo \"result=libqmi_uprobe_attempted_prearmed\" >> \"$LIBQMI_UPROBE_SUMMARY\"\n"
        "  if ! select_tracefs; then\n"
        "    echo \"tracefs=missing\" >> \"$LIBQMI_UPROBE_SUMMARY\"\n"
        "    return 0\n"
        "  fi\n"
        "  if ! select_libqmi_service; then\n"
        "    echo \"libqmi_service=missing\" >> \"$LIBQMI_UPROBE_SUMMARY\"\n"
        "    return 0\n"
        "  fi\n"
        "  echo \"tracefs=$TRACE_ROOT\" >> \"$LIBQMI_UPROBE_SUMMARY\"\n"
        "  echo \"libqmi_service=$LIBQMI_SERVICE\" >> \"$LIBQMI_UPROBE_SUMMARY\"\n"
        "  if [ -r \"$TRACE_ROOT/tracing_on\" ] && [ -z \"$ORIG_TRACING_ON\" ]; then\n"
        "    ORIG_TRACING_ON=\"$(cat \"$TRACE_ROOT/tracing_on\" 2>/dev/null)\"\n"
        "  fi\n"
        "  echo 1 > \"$TRACE_ROOT/tracing_on\" 2>/dev/null || true\n"
        "  register_libqmi_uprobe_event libqmi_get_service_list_entry 5e08 'svc_obj=%x0 list=%x1 capacity=%x2 count=%x3' || true\n"
        "  register_libqmi_uprobe_event libqmi_get_service_list_lookup_call 5eec 'xport=%x0 xport_id=%x1 svc_id=%x2 idl_version=%x3 capacity_ptr=%x4 list_ptr=%x5 lookup_fn=%x8' || true\n"
        "  register_libqmi_uprobe_event libqmi_get_service_list_lookup_ret 5ef0 'found=%x0 list=%x21 capacity_ptr=%x20 count_ptr=%x19 offset=%x22 xport_index=%x26' || true\n"
        "  register_libqmi_uprobe_event libqmi_client_init_instance_entry 7824 'svc=%x0 instance=%x1 ind_cb=%x2 ind_data=%x3 os_params=%x4 timeout=%x5 handle=%x6' || true\n"
        "  register_libqmi_uprobe_event libqmi_initial_get_service_instance_ret 78a0 '' || true\n"
        "  register_libqmi_uprobe_event libqmi_initial_client_init_ret 78c0 '' || true\n"
        "  register_libqmi_uprobe_event libqmi_notifier_init_call 78ec 'svc=%x0 signal=%x1 handle_out=%x2' || true\n"
        "  register_libqmi_uprobe_event libqmi_notifier_init_ret 78f0 '' || true\n"
        "  register_libqmi_uprobe_event libqmi_wait_call 7904 'signal=%x0 timeout=%x1' || true\n"
        "  register_libqmi_uprobe_event libqmi_wait_return 7908 '' || true\n"
        "  register_libqmi_uprobe_event libqmi_loop_get_service_instance_ret 7924 '' || true\n"
        "  register_libqmi_uprobe_event libqmi_loop_client_init_ret 7944 '' || true\n"
        "  register_libqmi_uprobe_event libqmi_init_timeout_path 7954 '' || true\n"
        "  register_libqmi_uprobe_event libqmi_init_return 7970 'rc=%x26' || true\n"
        "  register_libqmi_uprobe_event libqmi_signal_wait_entry 7e74 '' || true\n"
        "  register_libqmi_uprobe_event libqmi_signal_wait_timedwait 7fb8 '' || true\n"
        "  register_libqmi_uprobe_event libqmi_signal_wait_timeout_store 7fdc '' || true\n"
        "  register_libqmi_uprobe_event libqmi_xport_new_server_entry 48e8 'xport=%x0' || true\n"
        "  register_libqmi_uprobe_event libqmi_xport_new_server_service 4910 'xport=%x19 svc_id=+0(%x19):u32 state=+264(%x19):u32 addr=+64(%x19):u64 notifier=+296(%x19):u64' || true\n"
        "  register_libqmi_uprobe_event libqmi_xport_new_server_signal 496c 'xport=%x19 svc_id=+0(%x19):u32 signal=%x0 waiter=%x22' || true\n"
        "  register_libqmi_uprobe_event libqmi_xport_new_server_callback_call 4990 'svc_id=%x0 addr=%x1 event=%x2 version=%x3 cb=%x4' || true\n"
        "  LIBQMI_UPROBE_ARMED=1\n"
        "  echo \"armed=1\" >> \"$LIBQMI_UPROBE_SUMMARY\"\n"
        "}\n\n"
        "arm_qrtr_kprobes() {",
    )
    text = patch_once(
        text,
        "  if [ -n \"$TRACE_ROOT\" ] && [ -r \"$TRACE_ROOT/trace\" ]; then\n"
        "    grep -E \"$GROUP.*(cnss_|wlfw_)|cnss_wlfw\" \"$TRACE_ROOT/trace\" > \"$CNSS_UPROBE.tmp\" 2>/dev/null || true\n"
        "    mv \"$CNSS_UPROBE.tmp\" \"$CNSS_UPROBE\" 2>/dev/null || true\n"
        "    grep -E \"$GROUP.*(qrtr_|qmi_|servnotif_)|qrtr_|qmi_|servnotif_\" \"$TRACE_ROOT/trace\" > \"$QRTR_TRACE.tmp\" 2>/dev/null || true\n"
        "    mv \"$QRTR_TRACE.tmp\" \"$QRTR_TRACE\" 2>/dev/null || true\n"
        "  else\n"
        "    : > \"$CNSS_UPROBE\"\n"
        "    : > \"$QRTR_TRACE\"\n"
        "  fi\n",
        "  if [ -n \"$TRACE_ROOT\" ] && [ -r \"$TRACE_ROOT/trace\" ]; then\n"
        "    grep -E \"$GROUP.*(cnss_|wlfw_)|cnss_wlfw\" \"$TRACE_ROOT/trace\" > \"$CNSS_UPROBE.tmp\" 2>/dev/null || true\n"
        "    mv \"$CNSS_UPROBE.tmp\" \"$CNSS_UPROBE\" 2>/dev/null || true\n"
        "    grep -E \"$GROUP.*(qrtr_|qmi_|servnotif_)|qrtr_|qmi_|servnotif_\" \"$TRACE_ROOT/trace\" > \"$QRTR_TRACE.tmp\" 2>/dev/null || true\n"
        "    mv \"$QRTR_TRACE.tmp\" \"$QRTR_TRACE\" 2>/dev/null || true\n"
        "    grep -E \"$GROUP.*libqmi_|libqmi_\" \"$TRACE_ROOT/trace\" > \"$LIBQMI_UPROBE.tmp\" 2>/dev/null || true\n"
        "    mv \"$LIBQMI_UPROBE.tmp\" \"$LIBQMI_UPROBE\" 2>/dev/null || true\n"
        "  else\n"
        "    : > \"$CNSS_UPROBE\"\n"
        "    : > \"$QRTR_TRACE\"\n"
        "    : > \"$LIBQMI_UPROBE\"\n"
        "  fi\n",
    )
    text = patch_once(
        text,
        'echo "servnotif_hit_count=${servnotif_hits:-0}" >> "$QRTR_SUMMARY"\n}',
        'echo "servnotif_hit_count=${servnotif_hits:-0}" >> "$QRTR_SUMMARY"\n'
        '  libqmi_hits="$(grep -Ec "$GROUP|libqmi_" "$LIBQMI_UPROBE" 2>/dev/null || true)"\n'
        '  libqmi_lookup69_hits="$(grep -Ec "libqmi_get_service_list_lookup_call:.*svc_id=0x45|libqmi_get_service_list_lookup_call:.*svc_id=69" "$LIBQMI_UPROBE" 2>/dev/null || true)"\n'
        '  libqmi_new69_hits="$(grep -Ec "libqmi_xport_new_server_(service|signal|callback_call):.*svc_id=0x45|libqmi_xport_new_server_(service|signal|callback_call):.*svc_id=69" "$LIBQMI_UPROBE" 2>/dev/null || true)"\n'
        '  echo "hit_count=${libqmi_hits:-0}" >> "$LIBQMI_UPROBE_SUMMARY"\n'
        '  echo "lookup69_hit_count=${libqmi_lookup69_hits:-0}" >> "$LIBQMI_UPROBE_SUMMARY"\n'
        '  echo "new69_hit_count=${libqmi_new69_hits:-0}" >> "$LIBQMI_UPROBE_SUMMARY"\n'
        "}",
    )
    text = patch_once(
        text,
        'cat "$OUT"/*.strace.txt "$DMESG" "$LOGCAT" "$UPROBE" "$CNSS_UPROBE" "$QRTR_TRACE" 2>/dev/null',
        'cat "$OUT"/*.strace.txt "$DMESG" "$LOGCAT" "$UPROBE" "$CNSS_UPROBE" "$QRTR_TRACE" "$LIBQMI_UPROBE" 2>/dev/null',
    )
    text = patch_once(
        text,
        'printf \'qrtr_kprobe_trace_lines=\'\n    count_nonempty_lines "$QRTR_TRACE"',
        'printf \'qrtr_kprobe_trace_lines=\'\n'
        '    count_nonempty_lines "$QRTR_TRACE"\n'
        '    printf \'libqmi_uprobe_trace_lines=\'\n'
        '    count_nonempty_lines "$LIBQMI_UPROBE"',
    )
    text = text.replace(
        '  : > "$QRTR_TRACE"\n  : > "$QRTR_SUMMARY"\n',
        '  : > "$QRTR_TRACE"\n  : > "$QRTR_SUMMARY"\n  : > "$LIBQMI_UPROBE"\n  : > "$LIBQMI_UPROBE_SUMMARY"\n',
        1,
    )
    text = text.replace("  arm_cnss_uprobes\n  arm_qrtr_kprobes", "  arm_cnss_uprobes\n  arm_libqmi_uprobes\n  arm_qrtr_kprobes")
    text = text.replace("      arm_cnss_uprobes\n      arm_qrtr_kprobes", "      arm_cnss_uprobes\n      arm_libqmi_uprobes\n      arm_qrtr_kprobes")
    return text


def parse_key_values(text: str) -> dict[str, str]:
    return base.parse_key_values(text)


def read_file(path: Path, limit: int = 4_000_000) -> str:
    return base.read_file(path, limit=limit)


def service_ids_from_trace(text: str, event_names: tuple[str, ...]) -> list[int]:
    values: set[int] = set()
    for line in text.splitlines():
        if not any(event in line for event in event_names):
            continue
        match = SERVICE_RE.search(line)
        if match:
            values.add(int(match.group(1), 0))
    return sorted(values)


def event_thread(line: str) -> str:
    match = THREAD_RE.search(line)
    return match.group(1) if match else ""


def service69_progress_from_trace(text: str) -> dict[str, Any]:
    threads: set[str] = set()
    pending_lookup_threads: set[str] = set()
    found_count = 0
    wait_return_count = 0
    init_return_count = 0
    first_lookup = ""
    first_found = ""
    first_wait_return = ""
    first_init_return = ""
    for line in text.splitlines():
        thread = event_thread(line)
        if "libqmi_get_service_list_lookup_call" in line:
            match = SERVICE_RE.search(line)
            if match and int(match.group(1), 0) == 0x45:
                if thread:
                    threads.add(thread)
                    pending_lookup_threads.add(thread)
                if not first_lookup:
                    first_lookup = line.strip()
            continue
        if thread not in threads:
            continue
        if "libqmi_get_service_list_lookup_ret" in line and thread in pending_lookup_threads:
            match = FOUND_RE.search(line)
            if match and int(match.group(1), 0) > 0:
                found_count += 1
                if not first_found:
                    first_found = line.strip()
            pending_lookup_threads.discard(thread)
        elif "libqmi_wait_return" in line:
            wait_return_count += 1
            if not first_wait_return:
                first_wait_return = line.strip()
        elif "libqmi_init_return" in line:
            init_return_count += 1
            if not first_init_return:
                first_init_return = line.strip()
    return {
        "service69_threads": sorted(threads),
        "service69_found_count": found_count,
        "service69_wait_return_count": wait_return_count,
        "service69_init_return_count": init_return_count,
        "first_service69_lookup": first_lookup,
        "first_service69_found": first_found,
        "first_service69_wait_return": first_wait_return,
        "first_service69_init_return": first_init_return,
    }


def format_hex(values: list[int]) -> list[str]:
    return [f"0x{value:x}" for value in values]


def analyze_pulled_evidence(store: EvidenceStore) -> dict[str, Any]:
    analysis = BASE_ANALYZE(store)
    root = base.v1521.pulled_evidence_dir(store)
    evidence_dir = base.evidence_base(store)
    libqmi_trace = read_file(evidence_dir / "libqmi-uprobe-trace.txt")
    libqmi_summary = parse_key_values(read_file(evidence_dir / "libqmi-uprobe-summary.txt"))
    lookup_ids = service_ids_from_trace(libqmi_trace, ("libqmi_get_service_list_lookup_call",))
    new_server_ids = service_ids_from_trace(
        libqmi_trace,
        (
            "libqmi_xport_new_server_service",
            "libqmi_xport_new_server_signal",
            "libqmi_xport_new_server_callback_call",
        ),
    )
    service69_progress = service69_progress_from_trace(libqmi_trace)
    analysis.setdefault("files_present", {})["libqmi_uprobe_trace"] = bool(libqmi_trace)
    analysis.setdefault("files_present", {})["libqmi_uprobe_summary"] = bool(libqmi_summary)
    analysis.setdefault("trace_lines", {})["libqmi_uprobe"] = libqmi_trace.count("\n")
    analysis["libqmi_uprobe_summary"] = libqmi_summary
    analysis["libqmi_uprobe_excerpt"] = libqmi_trace[-8000:]
    analysis["libqmi_lookup_service_ids"] = format_hex(lookup_ids)
    analysis["libqmi_new_server_service_ids"] = format_hex(new_server_ids)
    analysis["libqmi_lookup_service69_seen"] = 0x45 in lookup_ids
    analysis["libqmi_new_server_service69_seen"] = 0x45 in new_server_ids
    analysis.update({f"libqmi_{key}": value for key, value in service69_progress.items()})
    analysis["libqmi_trace_path"] = rel(root / evidence_dir.name / "libqmi-uprobe-trace.txt")
    return analysis


def classify_result(
    base_decision: str,
    base_pass: bool,
    context: dict[str, Any],
    parser_results: dict[str, Any],
    selftest_ok: bool,
) -> tuple[str, bool, str, str]:
    if not selftest_ok:
        return "v1934-rollback-selftest-failed", False, "native rollback did not prove selftest fail=0", "rollback-selftest-failed"
    if not base_pass:
        return f"v1934-base-handoff-failed-{base_decision}", False, "underlying Android handoff did not complete", "android-handoff-failed"
    analysis = context.get("analysis") or {}
    files = analysis.get("files_present") or {}
    if not files.get("request_summary"):
        return "v1934-capture-insufficient-rollback-pass", False, "rollback completed, but request-summary evidence was not captured", "capture-insufficient"
    dmesg = analysis.get("dmesg") or {}
    contaminated = (
        bool(dmesg.get("degraded_257s_like"))
        or int(dmesg.get("pcie_mhi_before_wlan0") or 0) > 0
        or int(dmesg.get("esoc_boot_failed_before_wlan0") or 0) > 0
    )
    if contaminated:
        return (
            "v1934-android-capture-rejected-degraded-or-pcie-mhi",
            False,
            "Android capture was rejected because it is degraded or has pre-wlan0 PCIe/MHI/eSoC contamination",
            "android-capture-rejected-degraded-or-pcie-mhi",
        )
    stateup = (
        int(analysis.get("pm_vote_count") or 0) > 0
        and int(analysis.get("wlfw_service_request_count") or 0) > 0
        and int(analysis.get("wlan_pd_indication_count") or 0) > 0
        and int(analysis.get("wlanmdsp_count") or 0) > 0
        and dmesg.get("wlan0_time_s") is not None
    )
    if not stateup:
        return (
            "v1934-android-normal-stateup-incomplete-rollback-pass",
            False,
            "capture does not contain the normal PM vote -> wlan_pd -> wlanmdsp -> wlan0 state-up sequence",
            "android-normal-stateup-incomplete",
        )
    parser_ok = bool((parser_results.get("v1894") or {}).get("pass")) and bool((parser_results.get("v1888") or {}).get("pass"))
    if not parser_ok:
        return "v1934-parser-chain-failed-rollback-pass", False, "Android capture succeeded but V1894/V1888 parser chain did not pass", "parser-chain-failed"
    libqmi_lines = int((analysis.get("trace_lines") or {}).get("libqmi_uprobe") or 0)
    lookup69 = bool(analysis.get("libqmi_lookup_service69_seen"))
    new69 = bool(analysis.get("libqmi_new_server_service69_seen"))
    service69_found = int(analysis.get("libqmi_service69_found_count") or 0) > 0
    service69_wait_return = int(analysis.get("libqmi_service69_wait_return_count") or 0) > 0
    service69_init_return = int(analysis.get("libqmi_service69_init_return_count") or 0) > 0
    if lookup69 and new69:
        return (
            "v1934-android-libqmi-service69-publication-positive-control-rollback-pass",
            True,
            "normal Android state-up captured libqmi lookup and new-server publication for WLFW service 0x45/69; native V1930 has lookup but no new-server69",
            "android-libqmi-service69-publication-positive-control",
        )
    if lookup69 and service69_found and service69_wait_return and service69_init_return:
        return (
            "v1934-android-libqmi-service69-wait-return-positive-control-rollback-pass",
            True,
            "normal Android state-up captured WLFW service 0x45 lookup, wait return, successful service-list lookup, and qmi_client_init_instance return; decoded new-server69 was not exposed by the transport fetch",
            "android-libqmi-service69-wait-return-positive-control",
        )
    if new69:
        return (
            "v1934-android-libqmi-service69-new-server-without-lookup-rollback-pass",
            True,
            "normal Android state-up captured libqmi new-server publication for service 0x45/69, but the lookup uprobe missed the corresponding request",
            "android-libqmi-service69-new-server-without-lookup",
        )
    if libqmi_lines > 0:
        return (
            "v1934-android-libqmi-trace-missed-service69-rollback-pass",
            False,
            "normal Android state-up completed, but libqmi uprobes did not capture service 0x45/69 publication",
            "android-libqmi-trace-missed-service69",
        )
    return (
        "v1934-android-libqmi-uprobe-incomplete-rollback-pass",
        False,
        "normal Android state-up completed, but libqmi uprobe trace was empty or missing",
        "android-libqmi-uprobe-incomplete",
    )


def parser_commands(store: EvidenceStore, android_dir: Path) -> list[tuple[str, list[str], int, Path]]:
    commands = BASE_PARSER_COMMANDS(store, android_dir)
    rewritten: list[tuple[str, list[str], int, Path]] = []
    for name, command, timeout, manifest_path in commands:
        command = list(command)
        if "--report" in command:
            index = command.index("--report") + 1
            command[index] = str(store.run_dir / f"{name}-report.md")
        rewritten.append((name, command, timeout, manifest_path))
    return rewritten


def render_summary(manifest: dict[str, Any]) -> str:
    context = manifest["context"]
    analysis = context.get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    parser_results = manifest.get("parser_results") or {}
    libqmi_summary = analysis.get("libqmi_uprobe_summary") or {}
    libqmi_summary_slim = {
        key: libqmi_summary.get(key)
        for key in ("result", "tracefs", "libqmi_service", "armed", "hit_count", "lookup69_hit_count", "new69_hit_count")
    }
    rows = [
        ["android_dir", analysis.get("android_dir")],
        [
            "recovered/sampler_done",
            f"{context.get('recovered_after_host_analyzer_crash', False)}/{context.get('sampler_done_present')}",
        ],
        [
            "PM vote/WLFW request/wlan_pd/wlanmdsp/wlan0",
            f"{analysis.get('pm_vote_count')}/{analysis.get('wlfw_service_request_count')}/{analysis.get('wlan_pd_indication_count')}/{analysis.get('wlanmdsp_count')}/{dmesg.get('wlan0_time_s')}",
        ],
        [
            "contamination pcie-mhi/esoc/degraded257",
            f"{dmesg.get('pcie_mhi_before_wlan0')}/{dmesg.get('esoc_boot_failed_before_wlan0')}/{dmesg.get('degraded_257s_like')}",
        ],
        ["libqmi trace lines", (analysis.get("trace_lines") or {}).get("libqmi_uprobe")],
        ["libqmi lookup service IDs", json.dumps(analysis.get("libqmi_lookup_service_ids") or [])],
        ["libqmi new-server service IDs", json.dumps(analysis.get("libqmi_new_server_service_ids") or [])],
        [
            "libqmi lookup69/found/wait-return/init-return/new69",
            f"{analysis.get('libqmi_lookup_service69_seen')}/{analysis.get('libqmi_service69_found_count')}/{analysis.get('libqmi_service69_wait_return_count')}/{analysis.get('libqmi_service69_init_return_count')}/{analysis.get('libqmi_new_server_service69_seen')}",
        ],
        ["first service69 lookup", analysis.get("libqmi_first_service69_lookup")],
        ["first service69 found", analysis.get("libqmi_first_service69_found")],
        ["first service69 wait return", analysis.get("libqmi_first_service69_wait_return")],
        ["first service69 init return", analysis.get("libqmi_first_service69_init_return")],
        ["libqmi summary", json.dumps(libqmi_summary_slim, sort_keys=True)],
        ["libqmi trace", analysis.get("libqmi_trace_path")],
    ]
    return "\n".join(
        [
            "# Native Init V1934 Android Libqmi Service69 Positive Control",
            "",
            "## Summary",
            "",
            f"- Cycle: `{CYCLE}`",
            f"- Decision: `{manifest['decision']}`",
            f"- Label: `{manifest['label']}`",
            f"- Pass: `{manifest['pass']}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            "",
            "## Android Normal Edge",
            "",
            markdown_table(["field", "value"], [[str(cell) for cell in row] for row in rows]),
            "",
            "## Parser Chain",
            "",
            markdown_table(
                ["parser", "decision", "label", "pass", "out_dir"],
                [
                    [
                        "V1894",
                        (parser_results.get("v1894") or {}).get("decision"),
                        (parser_results.get("v1894") or {}).get("label"),
                        (parser_results.get("v1894") or {}).get("pass"),
                        (parser_results.get("v1894") or {}).get("out_dir"),
                    ],
                    [
                        "V1888",
                        (parser_results.get("v1888") or {}).get("decision"),
                        (parser_results.get("v1888") or {}).get("label"),
                        (parser_results.get("v1888") or {}).get("pass"),
                        (parser_results.get("v1888") or {}).get("out_dir"),
                    ],
                ],
            ),
            "",
            "## Comparison Target",
            "",
            "- Native V1930 already saw WLFW lookup for QMI service `0x45` but no `new-server69`.",
            "- Android-good shows the missing positive edge as WLFW service69 wait return plus found service-list/init return; the decoded transport new-server fetch only exposed low transport IDs.",
            "- Next native unit should target why the native WLFW thread never receives this wait-return/found-service edge, still below HAL and not SDX50M/eSoC/PCIe/GDSC.",
            "",
            "## Rollback Gate",
            "",
            f"- native rollback selftest fail=0: `{manifest['rollback_selftest_fail0']}`",
            f"- base handoff decision/pass: `{manifest['base_decision']}` / `{manifest['base_pass']}`",
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
            "## Safety",
            "",
            "Rollbackable Android-handoff to native v724 only. Android-side writes are limited to the temporary Magisk module, bounded evidence directory, and bounded tracefs uprobe/kprobe controls for CNSS/WLFW/QRTR/libqmi observation. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, or partition write beyond declared boot-image handoff/rollback.",
            "",
        ]
    )


def configure_base() -> None:
    base.CYCLE = CYCLE
    base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.LATEST_POINTER = LATEST_POINTER
    base.MODULE_NAME = MODULE_NAME
    base.REMOTE_MODULE_DIR = REMOTE_MODULE_DIR
    base.REMOTE_EVIDENCE_DIR = REMOTE_EVIDENCE_DIR
    base.REMOTE_STAGE_PREFIX = REMOTE_STAGE_PREFIX
    base.TRACEFS_GROUP = TRACEFS_GROUP
    base.module_prop = module_prop
    base.post_fs_data_script = post_fs_data_script
    base.analyze_pulled_evidence = analyze_pulled_evidence
    base.classify_result = classify_result
    base.parser_commands = parser_commands
    base.render_summary = render_summary


def main() -> int:
    configure_base()
    args = base.parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    execute = args.command == "run"
    base.configure_v1521_engine()
    steps, context, base_decision, base_pass = base.v1521.execute_plan(args, store, execute=execute)
    parser_results: dict[str, Any] = {}
    if execute and base_pass:
        android_dir = base.evidence_base(store)
        for name, command, timeout, manifest_path in parser_commands(store, android_dir):
            step = base.execute_parser_step(store, name, command, timeout, execute=True)
            steps.append(step)
            key = "v1894" if "v1894" in name else "v1888"
            parser_results[key] = base.read_json(manifest_path)
    elif not execute:
        for name, command, timeout, _manifest_path in parser_commands(store, base.evidence_base(store)):
            steps.append(base.execute_parser_step(store, name, command, timeout, execute=False))

    selftest_ok = base.rollback_selftest_ok(store, steps) if execute else False
    if execute:
        decision, pass_ok, reason, label = classify_result(base_decision, base_pass, context, parser_results, selftest_ok)
    else:
        decision = (
            "v1934-android-libqmi-service69-positive-control-plan-ready"
            if args.command == "plan"
            else "v1934-android-libqmi-service69-positive-control-dryrun-ready"
        )
        pass_ok = bool(base_pass)
        reason = "plan/dry-run completed without Android-good live capture"
        label = "android-libqmi-service69-positive-control-handoff-ready"

    manifest = {
        "cycle": CYCLE,
        "generated_at": now_iso(),
        "command": args.command,
        "base_decision": base_decision,
        "base_pass": base_pass,
        "decision": decision,
        "pass": pass_ok,
        "label": label,
        "reason": reason,
        "out_dir": rel(store.run_dir),
        "host": collect_host_metadata(),
        "context": context,
        "parser_results": parser_results,
        "rollback_selftest_fail0": selftest_ok,
        "steps": [asdict(step) for step in steps],
        "device_commands_executed": execute,
        "device_mutations": execute,
        "temporary_magisk_module_executed": execute,
        "temporary_magisk_module_cleanup_requested": execute,
        "tracefs_uprobe_control_executed": execute,
        "tracefs_kprobe_control_executed": execute,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "pmic_gpio_gdsc_regulator_write_executed": False,
        "forced_rc1_case_write_executed": False,
        "subsys_esoc0_open_executed": False,
        "fake_online_executed": False,
        "blind_esoc_notify_executed": False,
        "boot_done_spoof_executed": False,
        "global_pci_rescan_executed": False,
        "platform_bind_unbind_executed": False,
        "flash_executed": execute,
        "boot_image_write_executed": execute,
        "partition_write_executed": False,
    }
    summary = render_summary(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(DEFAULT_REPORT_PATH), summary)
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"label:    {manifest['label']}")
    print(f"reason:   {manifest['reason']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
