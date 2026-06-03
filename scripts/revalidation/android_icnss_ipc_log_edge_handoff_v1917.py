#!/usr/bin/env python3
"""V1917 Android-good ICNSS IPC/debugfs read-only handoff."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from a90_kernel_tools import markdown_table

import android_service_notifier_symbol_owner_handoff_v1912 as base


CYCLE = "V1917"
MODULE_NAME = "a90_v1917_icnss_ipc_log_edge"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1917-icnss-ipc-log-edge"
DEFAULT_OUT_DIR = Path("tmp/wifi/v1917-android-icnss-ipc-log-edge-handoff")
DEFAULT_REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1917_ANDROID_ICNSS_IPC_LOG_EDGE_HANDOFF_2026-06-03.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1917-android-icnss-ipc-log-edge-handoff.txt")

SERVICE74_RE = re.compile(r"service_notifier_new_server: .* 74 service", re.IGNORECASE)
SERVICE180_RE = re.compile(r"service_notifier_new_server: .* 180 service", re.IGNORECASE)
WLAN_PD_RE = re.compile(r"service-notifier: .*msm/modem/wlan_pd", re.IGNORECASE)
WLFW_CONNECTED_RE = re.compile(r"WLFW service connected", re.IGNORECASE)
IPC_FOCUS_RE = re.compile(
    r"domain_name|instance_id|Get service|service location|service notify|PD notification|"
    r"service_notif|service-notifier|wlan_pd|wlan/fw|wlanmdsp|qmi_add_lookup|servreg|wlfw",
    re.IGNORECASE,
)
DOMAIN_INSTANCE_RE = re.compile(r"domain_name:\s*(?P<domain>\S+)\s*,?\s*instance_id:\s*(?P<instance>\d+)", re.IGNORECASE)
INSTANCE74_RE = re.compile(r"\b(instance_id\s*[:=]\s*74|74 service|msm/modem/wlan_pd.*\b74\b|\b74\b.*msm/modem/wlan_pd)", re.IGNORECASE)


def module_prop() -> str:
    return "\n".join(
        [
            f"id={MODULE_NAME}",
            "name=A90 V1917 ICNSS IPC log edge observer",
            "version=1",
            "versionCode=1",
            "author=A90 native-init project",
            "description=Temporary read-only Android-good ICNSS IPC/debugfs domain-instance observer. Remove after capture.",
            "",
        ]
    )


def post_fs_data_script(samples: int, delay_us: int) -> str:
    del samples, delay_us
    filter_expr = (
        "service-locator|servloc|domain|service-notifier|service_notifier|ssctl|SSCTL|"
        "wlanmdsp|wlan[_/-]?pd|wlan/fw|wlfw_service_request|WLFW|wlfw|icnss|cnss|"
        "tftp|wlan0|PCIe|pcie|MHI|mhi|pcie_initialized|mhi_enable|esoc0|boot_failed"
    )
    ipc_filter = (
        "domain_name|instance_id|Get service|service location|service notify|PD notification|"
        "service_notif|service-notifier|wlan_pd|wlan/fw|wlanmdsp|qmi_add_lookup|servreg|wlfw"
    )
    ipc_context_filter = "icnss|cnss|wlan|wlfw|qmi|serv|notif|loc|qrtr|PIL|smp2p|glink|wcnss|wcss|subsys"
    return f"""#!/system/bin/sh
OUT={REMOTE_EVIDENCE_DIR}
FILTER='{filter_expr}'
IPC_FILTER='{ipc_filter}'
IPC_CONTEXT_FILTER='{ipc_context_filter}'
mkdir -p "$OUT" 2>/dev/null
chmod 755 "$OUT" 2>/dev/null
STATUS="$OUT/status.txt"
LOG="$OUT/samples.log"
DMESG="$OUT/dmesg-filtered.txt"
LOGCAT="$OUT/logcat-filtered.txt"
PROPS="$OUT/props.txt"
DEBUG_STATUS="$OUT/debugfs-status.txt"
IPC_ROOTS="$OUT/ipc-roots.txt"
IPC_TREE="$OUT/ipc-tree.txt"
IPC_FOCUSED="$OUT/ipc-focused.txt"
IPC_FOCUSED_LATE="$OUT/ipc-focused-late.txt"
IPC_RAW_INDEX="$OUT/ipc-readable-index.txt"
ICNSS_TREE="$OUT/icnss-debugfs-tree.txt"
ICNSS_STATS="$OUT/icnss-stats.txt"
ICNSS_STATS_LATE="$OUT/icnss-stats-late.txt"
QRTR="$OUT/proc-net-qrtr.txt"

uptime_now() {{
  cat /proc/uptime 2>/dev/null | awk '{{print $1}}'
}}

write_status() {{
  now="$(uptime_now)"
  echo "A90_V1917_STATUS $1 $now" > "$STATUS"
  echo "A90_V1521_STATUS $1 $now" >> "$STATUS"
}}

dump_logs() {{
  dmesg 2>&1 | grep -Ei "$FILTER" | tail -n 5000 > "$DMESG.tmp" || true
  mv "$DMESG.tmp" "$DMESG" 2>/dev/null || true
  logcat -d 2>/dev/null | grep -Ei "$FILTER" | tail -n 5000 > "$LOGCAT.tmp" || true
  mv "$LOGCAT.tmp" "$LOGCAT" 2>/dev/null || true
}}

dump_props() {{
  for p in sys.boot_completed dev.bootcomplete init.svc.vendor.per_mgr init.svc.vendor.pm-service init.svc.vendor.rmt_storage init.svc.vendor.tftp_server init.svc.cnss-daemon ro.boottime.vendor.per_mgr ro.boottime.vendor.pm-service ro.boottime.vendor.tftp_server ro.boottime.cnss-daemon; do
    echo "$p=$(getprop "$p" 2>/dev/null)"
  done > "$PROPS.tmp"
  mv "$PROPS.tmp" "$PROPS" 2>/dev/null || true
}}

append_readable_filtered() {{
  src="$1"
  label="$2"
  [ -r "$src" ] || return 0
  echo "$src" >> "$IPC_RAW_INDEX.tmp"
  {{
    echo "### $label $src"
    cat "$src" 2>&1 | grep -Ei "$IPC_FILTER" | tail -n 1200
  }} >> "$IPC_FOCUSED.tmp" 2>/dev/null || true
}}

append_late_filtered() {{
  src="$1"
  label="$2"
  [ -r "$src" ] || return 0
  {{
    echo "### $label $src"
    cat "$src" 2>&1 | grep -Ei "$IPC_FILTER" | tail -n 1200
  }} >> "$IPC_FOCUSED_LATE.tmp" 2>/dev/null || true
}}

dump_ipc_root() {{
  root="$1"
  [ -d "$root" ] || return 0
  echo "ROOT $root" >> "$IPC_ROOTS.tmp"
  find "$root" -maxdepth 4 2>/dev/null | head -n 1800 >> "$IPC_TREE.tmp" || true
  for dir in $(find "$root" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | head -n 260); do
    name="$(basename "$dir")"
    echo "$name" | grep -Ei "$IPC_CONTEXT_FILTER" >/dev/null 2>&1 || continue
    echo "CONTEXT $name" >> "$IPC_ROOTS.tmp"
    for leaf in log read stats; do
      file="$dir/$leaf"
      [ -r "$file" ] || continue
      append_readable_filtered "$file" "ipc:$name"
    done
  done
}}

dump_late_focused() {{
  DEBUGFS=""
  for p in /sys/kernel/debug /d; do
    [ -d "$p" ] && DEBUGFS="$p" && break
  done
  : > "$IPC_FOCUSED_LATE.tmp"
  if [ -n "$DEBUGFS" ]; then
    for ctx in icnss icnss_long qmi_txns qrtr qrtr_0_tx glink_pkt glink_probe PIL-IPC smp2p; do
      file="$DEBUGFS/ipc_logging/$ctx/log"
      [ -r "$file" ] || continue
      append_late_filtered "$file" "late:$ctx"
    done
    [ -r "$DEBUGFS/icnss/stats" ] && cat "$DEBUGFS/icnss/stats" 2>&1 > "$ICNSS_STATS_LATE.tmp" || true
    mv "$ICNSS_STATS_LATE.tmp" "$ICNSS_STATS_LATE" 2>/dev/null || true
  fi
  mv "$IPC_FOCUSED_LATE.tmp" "$IPC_FOCUSED_LATE" 2>/dev/null || true
}}

dump_debug_ro() {{
  DEBUGFS=""
  for p in /sys/kernel/debug /d; do
    [ -d "$p" ] && DEBUGFS="$p" && break
  done
  {{
    echo "debugfs=$DEBUGFS"
    [ -n "$DEBUGFS" ] && [ -d "$DEBUGFS/ipc_logging" ] && echo "debugfs_ipc_logging=1" || echo "debugfs_ipc_logging=0"
    [ -d /proc/ipc_logging ] && echo "proc_ipc_logging=1" || echo "proc_ipc_logging=0"
    [ -n "$DEBUGFS" ] && [ -d "$DEBUGFS/icnss" ] && echo "debugfs_icnss=1" || echo "debugfs_icnss=0"
  }} > "$DEBUG_STATUS.tmp"
  mv "$DEBUG_STATUS.tmp" "$DEBUG_STATUS" 2>/dev/null || true

  if [ -n "$DEBUGFS" ] && [ -d "$DEBUGFS/icnss" ]; then
    find "$DEBUGFS/icnss" -maxdepth 3 2>/dev/null | head -n 500 > "$ICNSS_TREE.tmp" || true
    mv "$ICNSS_TREE.tmp" "$ICNSS_TREE" 2>/dev/null || true
    [ -r "$DEBUGFS/icnss/stats" ] && cat "$DEBUGFS/icnss/stats" 2>&1 > "$ICNSS_STATS.tmp" || true
    mv "$ICNSS_STATS.tmp" "$ICNSS_STATS" 2>/dev/null || true
  fi

  : > "$IPC_ROOTS.tmp"
  : > "$IPC_TREE.tmp"
  : > "$IPC_FOCUSED.tmp"
  : > "$IPC_RAW_INDEX.tmp"
  [ -n "$DEBUGFS" ] && dump_ipc_root "$DEBUGFS/ipc_logging"
  dump_ipc_root /proc/ipc_logging
  mv "$IPC_ROOTS.tmp" "$IPC_ROOTS" 2>/dev/null || true
  mv "$IPC_TREE.tmp" "$IPC_TREE" 2>/dev/null || true
  mv "$IPC_FOCUSED.tmp" "$IPC_FOCUSED" 2>/dev/null || true
  mv "$IPC_RAW_INDEX.tmp" "$IPC_RAW_INDEX" 2>/dev/null || true
}}

dump_qrtr() {{
  cat /proc/net/qrtr 2>&1 > "$QRTR.tmp" || true
  mv "$QRTR.tmp" "$QRTR" 2>/dev/null || true
}}

(
  umask 022
  : > "$LOG"
  echo "A90_V1917_POSTFS_BEGIN uptime=$(uptime_now)" >> "$LOG"
  write_status start
  echo "A90_V1917_SAMPLE_BEGIN label=early uptime=$(uptime_now)" >> "$LOG"
  dump_debug_ro
  dump_qrtr
  dump_logs
  dump_props
  echo "SRC debugfs_status" >> "$LOG"
  cat "$DEBUG_STATUS" >> "$LOG" 2>/dev/null || true
  echo "SRC ipc_roots" >> "$LOG"
  cat "$IPC_ROOTS" >> "$LOG" 2>/dev/null || true
  echo "SRC ipc_focused_excerpt" >> "$LOG"
  cat "$IPC_FOCUSED" | tail -n 120 >> "$LOG" 2>/dev/null || true
  echo "A90_V1917_SAMPLE_END label=early uptime=$(uptime_now)" >> "$LOG"
  echo "A90_V1917_SAMPLE_BEGIN label=late uptime=$(uptime_now)" >> "$LOG"
  dump_late_focused
  dump_logs
  dump_props
  echo "SRC ipc_focused_late_excerpt" >> "$LOG"
  cat "$IPC_FOCUSED_LATE" | tail -n 120 >> "$LOG" 2>/dev/null || true
  echo "A90_V1917_SAMPLE_END label=late uptime=$(uptime_now)" >> "$LOG"
  echo "A90_V1917_POSTFS_END uptime=$(uptime_now)" >> "$LOG"
  write_status done
  touch "$OUT/done"
  chmod 755 "$OUT" 2>/dev/null
  chmod 644 "$OUT"/* 2>/dev/null
) >/dev/null 2>&1 &
exit 0
"""


def read_pulled(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def count_regex(text: str, regex: re.Pattern[str]) -> int:
    return sum(1 for line in text.splitlines() if regex.search(line))


def first_line(text: str, regex: re.Pattern[str]) -> str:
    for line in text.splitlines():
        if regex.search(line):
            return line.strip()
    return ""


def parse_status_map(text: str) -> dict[str, str]:
    status: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        status[key.strip()] = value.strip()
    return status


def domain_instances(text: str) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        match = DOMAIN_INSTANCE_RE.search(line)
        if not match:
            continue
        item = (match.group("domain"), match.group("instance"))
        if item in seen:
            continue
        seen.add(item)
        rows.append({"domain": item[0], "instance": item[1], "line": line.strip()})
    return rows


def focused_excerpt(text: str, limit: int = 24) -> list[str]:
    excerpt: list[str] = []
    for line in text.splitlines():
        clean = line.strip()
        if clean and IPC_FOCUS_RE.search(clean):
            excerpt.append(clean)
        if len(excerpt) >= limit:
            break
    return excerpt


def analyze_pulled_evidence(store: base.EvidenceStore) -> dict[str, Any]:
    root = base.v1521.pulled_evidence_dir(store)
    evidence = root / Path(REMOTE_EVIDENCE_DIR).name
    base_dir = evidence if evidence.is_dir() else root
    samples = read_pulled(base_dir / "samples.log")
    dmesg = read_pulled(base_dir / "dmesg-filtered.txt") + "\n" + read_pulled(root / "host-dmesg-filtered.txt")
    logcat = read_pulled(base_dir / "logcat-filtered.txt")
    props = read_pulled(base_dir / "props.txt")
    status = read_pulled(base_dir / "status.txt")
    debug_status_text = read_pulled(base_dir / "debugfs-status.txt")
    ipc_roots = read_pulled(base_dir / "ipc-roots.txt")
    ipc_tree = read_pulled(base_dir / "ipc-tree.txt")
    ipc_focused = read_pulled(base_dir / "ipc-focused.txt")
    ipc_focused_late = read_pulled(base_dir / "ipc-focused-late.txt")
    ipc_index = read_pulled(base_dir / "ipc-readable-index.txt")
    icnss_tree = read_pulled(base_dir / "icnss-debugfs-tree.txt")
    icnss_stats = read_pulled(base_dir / "icnss-stats.txt")
    icnss_stats_late = read_pulled(base_dir / "icnss-stats-late.txt")
    qrtr = read_pulled(base_dir / "proc-net-qrtr.txt")
    all_lower = dmesg + "\n" + logcat
    all_focus = ipc_focused + "\n" + ipc_focused_late + "\n" + samples + "\n" + dmesg + "\n" + logcat
    dmesg_lines = dmesg.splitlines()
    wlan0_time = base.first_dmesg_time(dmesg_lines, base.WLAN0_RE)
    debug_status = parse_status_map(debug_status_text)
    domains = domain_instances(all_focus)
    instance74_lines = [line.strip() for line in all_focus.splitlines() if INSTANCE74_RE.search(line)][:32]
    wlan_pd_domain_lines = [line.strip() for line in all_focus.splitlines() if "wlan_pd" in line.lower()][:32]
    return {
        "base": base.rel(base_dir),
        "files_present": {
            "samples": bool(samples.strip()),
            "dmesg": bool(dmesg.strip()),
            "logcat": bool(logcat.strip()),
            "props": bool(props.strip()),
            "status": bool(status.strip()),
            "done": (base_dir / "done").exists(),
            "debugfs_status": bool(debug_status_text.strip()),
            "ipc_roots": bool(ipc_roots.strip()),
            "ipc_tree": bool(ipc_tree.strip()),
            "ipc_focused": bool(ipc_focused.strip()),
            "ipc_focused_late": bool(ipc_focused_late.strip()),
            "ipc_readable_index": bool(ipc_index.strip()),
            "icnss_tree": bool(icnss_tree.strip()),
            "icnss_stats": bool(icnss_stats.strip()),
            "icnss_stats_late": bool(icnss_stats_late.strip()),
            "qrtr": bool(qrtr.strip()),
        },
        "status_text": status.strip(),
        "sample_count": samples.count("A90_V1917_SAMPLE_BEGIN"),
        "service74_count": base.count_lines(dmesg_lines, SERVICE74_RE),
        "service180_count": base.count_lines(dmesg_lines, SERVICE180_RE),
        "wlan_pd_indication_count": base.count_lines(dmesg_lines, WLAN_PD_RE),
        "wlfw_service_request_count": base.count_lines(all_lower, base.WLFW_REQUEST_RE),
        "wlfw_service_connected_count": base.count_lines(all_lower, WLFW_CONNECTED_RE),
        "wlanmdsp_count": base.count_lines(all_lower, base.WLANMDSP_RE),
        "first_service74_line": first_line(dmesg, SERVICE74_RE),
        "first_service180_line": first_line(dmesg, SERVICE180_RE),
        "first_wlan_pd_line": first_line(dmesg, WLAN_PD_RE),
        "first_wlanmdsp_line": first_line(all_lower, base.WLANMDSP_RE),
        "dmesg": {
            "wlan0_time_s": wlan0_time,
            "pcie_mhi_before_wlan0": base.count_dmesg_before(dmesg_lines, base.PCIE_MHI_RE, wlan0_time),
            "esoc_boot_failed_before_wlan0": base.count_dmesg_before(dmesg_lines, base.ESOC_BOOT_FAILED_RE, wlan0_time),
            "degraded_257s_like": wlan0_time is not None and wlan0_time > 120.0,
            "wlan0_lines": base.count_lines(all_lower, re.compile(r"\bwlan0\b", re.IGNORECASE)),
        },
        "debugfs_status": debug_status,
        "debugfs_status_text": debug_status_text.strip(),
        "ipc_root_count": len([line for line in ipc_roots.splitlines() if line.startswith("ROOT ")]),
        "ipc_tree_line_count": len(ipc_tree.splitlines()) if ipc_tree else 0,
        "ipc_readable_file_count": len([line for line in ipc_index.splitlines() if line.strip()]),
        "ipc_focused_line_count": len([line for line in ipc_focused.splitlines() if line.strip()]),
        "ipc_focused_late_line_count": len([line for line in ipc_focused_late.splitlines() if line.strip()]),
        "ipc_focus_match_count": count_regex(ipc_focused + "\n" + ipc_focused_late, IPC_FOCUS_RE),
        "domain_instances": domains[:48],
        "domain_instance_count": len(domains),
        "instance74_lines": instance74_lines,
        "wlan_pd_domain_lines": wlan_pd_domain_lines,
        "focused_excerpt": focused_excerpt(all_focus),
        "icnss_tree_line_count": len(icnss_tree.splitlines()) if icnss_tree else 0,
        "icnss_stats_line_count": len(icnss_stats.splitlines()) if icnss_stats else 0,
        "icnss_stats_late_line_count": len(icnss_stats_late.splitlines()) if icnss_stats_late else 0,
        "icnss_stats_excerpt": [line.strip() for line in (icnss_stats + "\n" + icnss_stats_late).splitlines() if line.strip()][:24],
        "android_internal_stateup": (
            base.count_lines(all_lower, base.WLFW_REQUEST_RE) > 0
            and base.count_lines(all_lower, base.WLANMDSP_RE) > 0
            and wlan0_time is not None
        ),
        "android_service_notifier_stateup": (
            base.count_lines(dmesg_lines, SERVICE74_RE) > 0
            and base.count_lines(dmesg_lines, SERVICE180_RE) > 0
            and base.count_lines(dmesg_lines, WLAN_PD_RE) > 0
            and base.count_lines(all_lower, base.WLANMDSP_RE) > 0
            and wlan0_time is not None
        ),
        "qrtr_line_count": len(qrtr.splitlines()) if qrtr else 0,
        "props_text": props.strip(),
    }


def classify_result(base_decision: str, base_pass: bool, analysis: dict[str, Any], selftest_ok: bool) -> tuple[str, bool, str, str]:
    if not selftest_ok:
        return ("v1917-rollback-selftest-failed", False, "native rollback did not prove selftest fail=0", "rollback-selftest-failed")
    if not base_pass:
        return (f"v1917-base-handoff-failed-{base_decision}", False, "underlying Android handoff did not complete", "android-handoff-failed")
    files = analysis.get("files_present") or {}
    dmesg = analysis.get("dmesg") or {}
    contaminated = (
        base.boolish(dmesg.get("degraded_257s_like"))
        or base.intish(dmesg.get("pcie_mhi_before_wlan0")) > 0
        or base.intish(dmesg.get("esoc_boot_failed_before_wlan0")) > 0
    )
    if contaminated:
        return ("v1917-android-capture-rejected-degraded-or-pcie-mhi", False, "Android capture was degraded or had pre-wlan0 PCIe/MHI/eSoC contamination", "android-capture-rejected-degraded-or-pcie-mhi")
    stateup = base.boolish(analysis.get("android_internal_stateup"))
    if not stateup:
        return ("v1917-android-normal-stateup-incomplete-rollback-pass", False, "Android capture did not prove normal WLFW + wlanmdsp + wlan0 internal-modem state-up", "android-normal-stateup-incomplete")
    if not files.get("debugfs_status"):
        return ("v1917-android-debugfs-status-missing-rollback-pass", False, "Android state-up succeeded but read-only debugfs status was missing", "android-debugfs-status-missing")
    if analysis.get("instance74_lines"):
        return (
            "v1917-android-icnss-ipc-domain-instance74-edge-captured-rollback-pass",
            True,
            "normal Android internal-modem state-up captured an instance74/wlan_pd IPC or kernel-log edge, then rolled back to native v724",
            "android-icnss-ipc-domain-instance74-edge",
        )
    if (
        base.intish(analysis.get("ipc_focused_line_count")) > 0
        or base.intish(analysis.get("ipc_focused_late_line_count")) > 0
        or base.intish(analysis.get("icnss_stats_line_count")) > 0
        or base.intish(analysis.get("icnss_stats_late_line_count")) > 0
    ):
        return (
            "v1917-android-ipc-debugfs-surface-no-instance74-rollback-pass",
            True,
            "normal Android internal-modem state-up captured IPC/debugfs surfaces but no instance74 line, then rolled back to native v724",
            "android-ipc-debugfs-surface-no-instance74",
        )
    return (
        "v1917-android-ipc-debugfs-surface-absent-rollback-pass",
        True,
        "normal Android internal-modem state-up completed, but read-only IPC/debugfs surfaces were absent or unreadable; native rollback passed",
        "android-ipc-debugfs-surface-absent-readonly",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = (manifest.get("context") or {}).get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    return "\n".join([
        "# Native Init V1917 Android ICNSS IPC Log Edge Handoff",
        "",
        f"- Cycle: `{manifest['cycle']}`",
        "- Type: rollbackable Android-good read-only ICNSS IPC/debugfs domain-instance capture",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Android-good State-up",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["service74/service180/wlan_pd/wlanmdsp/wlan0", f"{analysis.get('service74_count')}/{analysis.get('service180_count')}/{analysis.get('wlan_pd_indication_count')}/{analysis.get('wlanmdsp_count')}/{dmesg.get('wlan0_time_s')}"],
                ["wlfw service request", analysis.get("wlfw_service_request_count")],
                ["wlfw service connected", analysis.get("wlfw_service_connected_count")],
                ["state-up gates internal/notifier", f"{analysis.get('android_internal_stateup')}/{analysis.get('android_service_notifier_stateup')}"],
                ["contamination pcie-mhi/esoc/degraded257", f"{dmesg.get('pcie_mhi_before_wlan0')}/{dmesg.get('esoc_boot_failed_before_wlan0')}/{dmesg.get('degraded_257s_like')}"],
                ["first service74", analysis.get("first_service74_line", "")],
                ["first wlan_pd", analysis.get("first_wlan_pd_line", "")],
            ],
        ),
        "",
        "## IPC / Debugfs Surface",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["debugfs status", json.dumps(analysis.get("debugfs_status") or {}, sort_keys=True)],
                ["ipc roots/tree/readable/focused/late", f"{analysis.get('ipc_root_count')}/{analysis.get('ipc_tree_line_count')}/{analysis.get('ipc_readable_file_count')}/{analysis.get('ipc_focused_line_count')}/{analysis.get('ipc_focused_late_line_count')}"],
                ["domain instances", json.dumps(analysis.get("domain_instances") or [])],
                ["instance74 lines", json.dumps(analysis.get("instance74_lines") or [])],
                ["wlan_pd domain lines", json.dumps(analysis.get("wlan_pd_domain_lines") or [])],
                ["focused excerpt", json.dumps(analysis.get("focused_excerpt") or [])],
            ],
        ),
        "",
        "## ICNSS / QRTR",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["icnss tree/stats/late lines", f"{analysis.get('icnss_tree_line_count')}/{analysis.get('icnss_stats_line_count')}/{analysis.get('icnss_stats_late_line_count')}"],
                ["icnss stats excerpt", json.dumps(analysis.get("icnss_stats_excerpt") or [])],
                ["qrtr lines", analysis.get("qrtr_line_count")],
            ],
        ),
        "",
        "## Files",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["base", analysis.get("base")],
                ["files", json.dumps(analysis.get("files_present") or {}, sort_keys=True)],
                ["sample_count", analysis.get("sample_count")],
                ["status", analysis.get("status_text")],
                ["rollback selftest fail=0", manifest.get("rollback_selftest_fail0")],
            ],
        ),
        "",
        "## Safety Scope",
        "",
        "Rollbackable Android-handoff to native v724 only. Android-side writes are limited to the temporary Magisk module and bounded evidence directory. The module reads debugfs/proc IPC logging surfaces, `/sys/kernel/debug/icnss/stats`, `/proc/net/qrtr`, dmesg, logcat, and properties. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, restart-PD request, tracefs write, debugfs write, or partition write beyond the declared boot-image handoff/rollback.",
        "",
        "## Next",
        "",
        "- If instance74/wlan_pd appears in IPC logging, compare that ICNSS domain-list path against native service-locator instance180-only behavior.",
        "- Do not attempt Wi-Fi credentials/connect/ping until native proves WLFW service69 and `wlan0`.",
        "",
    ])


def configure_engine() -> None:
    base.CYCLE = CYCLE
    base.MODULE_NAME = MODULE_NAME
    base.REMOTE_MODULE_DIR = REMOTE_MODULE_DIR
    base.REMOTE_EVIDENCE_DIR = REMOTE_EVIDENCE_DIR
    base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.LATEST_POINTER = LATEST_POINTER
    base.module_prop = module_prop
    base.post_fs_data_script = post_fs_data_script
    base.analyze_pulled_evidence = analyze_pulled_evidence
    base.classify_result = classify_result
    base.render_summary = render_summary
    base.configure_engine()


def main() -> int:
    configure_engine()
    args = base.parse_args()
    store = base.EvidenceStore(base.repo_path(args.out_dir))
    execute = args.command == "run"
    steps, context, base_decision, base_pass = base.v1521.execute_plan(args, store, execute=execute)
    analysis = context.get("analysis") or {}
    selftest_ok = base.rollback_selftest_ok(store, steps) if execute else False
    if execute:
        decision, pass_ok, reason, label = classify_result(base_decision, base_pass, analysis, selftest_ok)
    else:
        decision = (
            "v1917-android-icnss-ipc-log-edge-plan-ready"
            if args.command == "plan"
            else "v1917-android-icnss-ipc-log-edge-dryrun-ready"
        )
        pass_ok = bool(base_pass)
        reason = "plan/dry-run completed without Android-good live capture"
        label = "android-icnss-ipc-log-edge-handoff-ready"
    manifest = {
        "cycle": CYCLE,
        "generated_at": base.now_iso(),
        "command": args.command,
        "base_decision": base_decision,
        "base_pass": base_pass,
        "decision": decision,
        "pass": pass_ok,
        "label": label,
        "reason": reason,
        "out_dir": base.rel(store.run_dir),
        "host": base.collect_host_metadata(),
        "context": context,
        "rollback_selftest_fail0": selftest_ok,
        "steps": [base.asdict(step) for step in steps],
        "device_commands_executed": execute,
        "device_mutations": execute,
        "temporary_magisk_module_executed": execute,
        "temporary_magisk_module_cleanup_requested": execute,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "restart_pd_request_executed": False,
        "tracefs_write_executed": False,
        "debugfs_write_executed": False,
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
    base.write_private_text(base.repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        base.write_private_text(base.repo_path(DEFAULT_REPORT_PATH), summary)
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"label:    {manifest['label']}")
    print(f"reason:   {manifest['reason']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
