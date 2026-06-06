#!/usr/bin/env python3
"""V1916 Android-good broad kallsyms/tracefs read-only handoff."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from a90_kernel_tools import markdown_table

import android_service_notifier_symbol_owner_handoff_v1912 as base


CYCLE = "V1916"
MODULE_NAME = "a90_v1916_broad_kernel_edge"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1916-broad-kernel-edge"
DEFAULT_OUT_DIR = Path("tmp/wifi/v1916-android-broad-kallsyms-tracefs-handoff")
DEFAULT_REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1916_ANDROID_BROAD_KALLSYMS_TRACEFS_HANDOFF_2026-06-03.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1916-android-broad-kallsyms-tracefs-handoff.txt")

SERVICE74_RE = re.compile(r"service_notifier_new_server: .* 74 service", re.IGNORECASE)
SERVICE180_RE = re.compile(r"service_notifier_new_server: .* 180 service", re.IGNORECASE)
WLAN_PD_RE = re.compile(r"service-notifier: .*msm/modem/wlan_pd", re.IGNORECASE)
SYMBOL_PATTERNS = {
    "service_notif_register_notifier": re.compile(r"\bservice_notif_register_notifier\b"),
    "service_notifier_new_server": re.compile(r"\bservice_notifier_new_server\b"),
    "service_locator_new_server": re.compile(r"\bservice_locator_new_server\b"),
    "qmi_add_lookup": re.compile(r"\bqmi_add_lookup\b"),
    "icnss_get_service_location_notify": re.compile(r"\bicnss_get_service_location_notify\b"),
    "icnss_service_notifier_notify": re.compile(r"\bicnss_service_notifier_notify\b"),
    "qmi_servreg_notif": re.compile(r"\bqmi_servreg_notif", re.IGNORECASE),
    "qmi_servreg_loc": re.compile(r"\bqmi_servreg_loc", re.IGNORECASE),
    "ssctl": re.compile(r"\bssctl", re.IGNORECASE),
}


def module_prop() -> str:
    return "\n".join(
        [
            f"id={MODULE_NAME}",
            "name=A90 V1916 broad kernel edge observer",
            "version=1",
            "versionCode=1",
            "author=A90 native-init project",
            "description=Temporary read-only Android-good broad kallsyms/tracefs availability observer. Remove after capture.",
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
    broad_symbols = (
        "service_notif|service_notifier|service_locator|qmi_add_lookup|qmi_handle|qmi_txn|"
        "qmi_servreg|servreg|icnss_get_service|icnss_service|icnss_qmi|wlfw|ssctl|"
        "subsys_notif|subsystem_restart|qrtr|ipc_router"
    )
    return f"""#!/system/bin/sh
OUT={REMOTE_EVIDENCE_DIR}
FILTER='{filter_expr}'
BROAD_SYMBOLS='{broad_symbols}'
mkdir -p "$OUT" 2>/dev/null
chmod 755 "$OUT" 2>/dev/null
STATUS="$OUT/status.txt"
LOG="$OUT/samples.log"
DMESG="$OUT/dmesg-filtered.txt"
LOGCAT="$OUT/logcat-filtered.txt"
PROPS="$OUT/props.txt"
KALL_TARGETS="$OUT/kallsyms-targets.txt"
KALL_BROAD="$OUT/kallsyms-broad.txt"
TRACE_STATUS="$OUT/tracefs-status.txt"
TRACE_EVENTS="$OUT/tracefs-events-focused.txt"
TRACE_FILTERS="$OUT/tracefs-filter-functions-focused.txt"
TRACE_META="$OUT/tracefs-meta.txt"
QRTR="$OUT/proc-net-qrtr.txt"
SYS_MODULES="$OUT/sys-modules.txt"
MODULE_SECTIONS="$OUT/module-sections.txt"

uptime_now() {{
  cat /proc/uptime 2>/dev/null | awk '{{print $1}}'
}}

write_status() {{
  now="$(uptime_now)"
  echo "A90_V1916_STATUS $1 $now" > "$STATUS"
  echo "A90_V1521_STATUS $1 $now" >> "$STATUS"
}}

dump_logs() {{
  dmesg 2>&1 | grep -Ei "$FILTER" | tail -n 4000 > "$DMESG.tmp" || true
  mv "$DMESG.tmp" "$DMESG" 2>/dev/null || true
  logcat -d 2>/dev/null | grep -Ei "$FILTER" | tail -n 4000 > "$LOGCAT.tmp" || true
  mv "$LOGCAT.tmp" "$LOGCAT" 2>/dev/null || true
}}

dump_props() {{
  for p in sys.boot_completed dev.bootcomplete init.svc.vendor.per_mgr init.svc.vendor.pm-service init.svc.vendor.rmt_storage init.svc.vendor.tftp_server init.svc.cnss-daemon ro.boottime.vendor.per_mgr ro.boottime.vendor.pm-service ro.boottime.vendor.tftp_server ro.boottime.cnss-daemon; do
    echo "$p=$(getprop "$p" 2>/dev/null)"
  done > "$PROPS.tmp"
  mv "$PROPS.tmp" "$PROPS" 2>/dev/null || true
}}

dump_symbols() {{
  cat /proc/kallsyms 2>&1 | grep -Ei 'service_notif_register_notifier|service_notifier_new_server|service_locator_new_server|qmi_add_lookup|icnss_get_service_location_notify|icnss_service_notifier_notify|qmi_servreg_notif|qmi_servreg_loc|ssctl' | head -n 400 > "$KALL_TARGETS.tmp" || true
  mv "$KALL_TARGETS.tmp" "$KALL_TARGETS" 2>/dev/null || true
  cat /proc/kallsyms 2>&1 | grep -Ei "$BROAD_SYMBOLS" | head -n 2500 > "$KALL_BROAD.tmp" || true
  mv "$KALL_BROAD.tmp" "$KALL_BROAD" 2>/dev/null || true
  ls -1 /sys/module 2>/dev/null | grep -Ei 'service|notif|locator|qmi|qrtr|ipc_router|icnss|cnss|wlan|wcnss|ssr|subsys' > "$SYS_MODULES.tmp" || true
  mv "$SYS_MODULES.tmp" "$SYS_MODULES" 2>/dev/null || true
  {{
    for m in service_locator icnss wlan qmi_helpers qmi_encdec qrtr ipc_router subsystem_restart; do
      [ -d "/sys/module/$m" ] || continue
      echo "MODULE $m"
      [ -d "/sys/module/$m/sections" ] && ls -1 "/sys/module/$m/sections" 2>/dev/null | sed "s#^#section $m/#"
      [ -d "/sys/module/$m/parameters" ] && ls -1 "/sys/module/$m/parameters" 2>/dev/null | sed "s#^#parameter $m/#"
    done
  }} > "$MODULE_SECTIONS.tmp"
  mv "$MODULE_SECTIONS.tmp" "$MODULE_SECTIONS" 2>/dev/null || true
}}

dump_tracefs() {{
  TRACEFS=""
  for p in /sys/kernel/tracing /sys/kernel/debug/tracing; do
    [ -d "$p" ] && TRACEFS="$p" && break
  done
  {{
    echo "tracefs=$TRACEFS"
    [ -n "$TRACEFS" ] && [ -r "$TRACEFS/current_tracer" ] && echo "current_tracer=$(cat "$TRACEFS/current_tracer" 2>/dev/null)"
    [ -n "$TRACEFS" ] && [ -r "$TRACEFS/tracing_on" ] && echo "tracing_on=$(cat "$TRACEFS/tracing_on" 2>/dev/null)"
    [ -n "$TRACEFS" ] && [ -e "$TRACEFS/kprobe_events" ] && echo "kprobe_events_exists=1" || echo "kprobe_events_exists=0"
    [ -n "$TRACEFS" ] && [ -e "$TRACEFS/uprobe_events" ] && echo "uprobe_events_exists=1" || echo "uprobe_events_exists=0"
    [ -n "$TRACEFS" ] && [ -e "$TRACEFS/available_filter_functions" ] && echo "available_filter_functions_exists=1" || echo "available_filter_functions_exists=0"
  }} > "$TRACE_STATUS.tmp"
  mv "$TRACE_STATUS.tmp" "$TRACE_STATUS" 2>/dev/null || true
  if [ -n "$TRACEFS" ]; then
    [ -r "$TRACEFS/available_events" ] && grep -Ei 'qmi|qrtr|ipc|service|servreg|icnss|wlan|subsys|ssr' "$TRACEFS/available_events" | head -n 500 > "$TRACE_EVENTS.tmp" || true
    mv "$TRACE_EVENTS.tmp" "$TRACE_EVENTS" 2>/dev/null || true
    [ -r "$TRACEFS/available_filter_functions" ] && grep -Ei 'service_notif|service_notifier|service_locator|qmi_add_lookup|icnss|get_service_location|ssctl|subsys_notif|wlfw' "$TRACEFS/available_filter_functions" | head -n 500 > "$TRACE_FILTERS.tmp" || true
    mv "$TRACE_FILTERS.tmp" "$TRACE_FILTERS" 2>/dev/null || true
    {{
      [ -d "$TRACEFS/events" ] && find "$TRACEFS/events" -maxdepth 2 -type d 2>/dev/null | grep -Ei 'qmi|qrtr|ipc|service|servreg|icnss|wlan|subsys|ssr' | head -n 500
    }} > "$TRACE_META.tmp"
    mv "$TRACE_META.tmp" "$TRACE_META" 2>/dev/null || true
  fi
}}

dump_qrtr() {{
  cat /proc/net/qrtr 2>&1 > "$QRTR.tmp" || true
  mv "$QRTR.tmp" "$QRTR" 2>/dev/null || true
}}

(
  umask 022
  : > "$LOG"
  echo "A90_V1916_POSTFS_BEGIN uptime=$(uptime_now)" >> "$LOG"
  write_status start
  echo "A90_V1916_SAMPLE_BEGIN label=early uptime=$(uptime_now)" >> "$LOG"
  dump_symbols
  dump_tracefs
  dump_qrtr
  dump_logs
  dump_props
  echo "SRC kallsyms_targets" >> "$LOG"
  cat "$KALL_TARGETS" >> "$LOG" 2>/dev/null || true
  echo "SRC tracefs_status" >> "$LOG"
  cat "$TRACE_STATUS" >> "$LOG" 2>/dev/null || true
  echo "A90_V1916_SAMPLE_END label=early uptime=$(uptime_now)" >> "$LOG"
  echo "A90_V1916_POSTFS_END uptime=$(uptime_now)" >> "$LOG"
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


def trace_status_map(text: str) -> dict[str, str]:
    status: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        status[key.strip()] = value.strip()
    return status


def analyze_pulled_evidence(store: base.EvidenceStore) -> dict[str, Any]:
    root = base.v1521.pulled_evidence_dir(store)
    evidence = root / Path(REMOTE_EVIDENCE_DIR).name
    base_dir = evidence if evidence.is_dir() else root
    samples = read_pulled(base_dir / "samples.log")
    dmesg = read_pulled(base_dir / "dmesg-filtered.txt") + "\n" + read_pulled(root / "host-dmesg-filtered.txt")
    logcat = read_pulled(base_dir / "logcat-filtered.txt")
    props = read_pulled(base_dir / "props.txt")
    status = read_pulled(base_dir / "status.txt")
    kall_targets = read_pulled(base_dir / "kallsyms-targets.txt")
    kall_broad = read_pulled(base_dir / "kallsyms-broad.txt")
    trace_status_text = read_pulled(base_dir / "tracefs-status.txt")
    trace_events = read_pulled(base_dir / "tracefs-events-focused.txt")
    trace_filters = read_pulled(base_dir / "tracefs-filter-functions-focused.txt")
    trace_meta = read_pulled(base_dir / "tracefs-meta.txt")
    qrtr = read_pulled(base_dir / "proc-net-qrtr.txt")
    sys_modules = read_pulled(base_dir / "sys-modules.txt")
    module_sections = read_pulled(base_dir / "module-sections.txt")
    all_lower = dmesg + "\n" + logcat
    dmesg_lines = dmesg.splitlines()
    wlan0_time = base.first_dmesg_time(dmesg_lines, base.WLAN0_RE)
    trace_status = trace_status_map(trace_status_text)
    symbol_counts = {name: count_regex(kall_targets + "\n" + kall_broad, regex) for name, regex in SYMBOL_PATTERNS.items()}
    filter_counts = {name: count_regex(trace_filters, regex) for name, regex in SYMBOL_PATTERNS.items()}
    event_counts = {
        "focused_event_lines": len([line for line in trace_events.splitlines() if line.strip()]),
        "focused_event_dirs": len([line for line in trace_meta.splitlines() if line.strip()]),
    }
    return {
        "base": base.rel(base_dir),
        "files_present": {
            "samples": bool(samples.strip()),
            "dmesg": bool(dmesg.strip()),
            "logcat": bool(logcat.strip()),
            "props": bool(props.strip()),
            "status": bool(status.strip()),
            "done": (base_dir / "done").exists(),
            "kallsyms_targets": bool(kall_targets.strip()),
            "kallsyms_broad": bool(kall_broad.strip()),
            "tracefs_status": bool(trace_status_text.strip()),
            "tracefs_events": bool(trace_events.strip()),
            "tracefs_filter_functions": bool(trace_filters.strip()),
            "qrtr": bool(qrtr.strip()),
            "sys_modules": bool(sys_modules.strip()),
            "module_sections": bool(module_sections.strip()),
        },
        "status_text": status.strip(),
        "sample_count": samples.count("A90_V1916_SAMPLE_BEGIN"),
        "service74_count": base.count_lines(dmesg_lines, SERVICE74_RE),
        "service180_count": base.count_lines(dmesg_lines, SERVICE180_RE),
        "wlan_pd_indication_count": base.count_lines(dmesg_lines, WLAN_PD_RE),
        "wlfw_service_request_count": base.count_lines(all_lower, base.WLFW_REQUEST_RE),
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
        "kallsyms_target_line_count": len(kall_targets.splitlines()) if kall_targets else 0,
        "kallsyms_broad_line_count": len(kall_broad.splitlines()) if kall_broad else 0,
        "symbol_counts": symbol_counts,
        "tracefs_status": trace_status,
        "tracefs_status_text": trace_status_text.strip(),
        "tracefs_filter_line_count": len(trace_filters.splitlines()) if trace_filters else 0,
        "tracefs_filter_symbol_counts": filter_counts,
        "tracefs_event_counts": event_counts,
        "tracefs_event_excerpt": [line.strip() for line in trace_events.splitlines() if line.strip()][:24],
        "qrtr_line_count": len(qrtr.splitlines()) if qrtr else 0,
        "sys_modules": [line.strip() for line in sys_modules.splitlines() if line.strip()],
        "module_sections_line_count": len(module_sections.splitlines()) if module_sections else 0,
        "props_text": props.strip(),
    }


def classify_result(base_decision: str, base_pass: bool, analysis: dict[str, Any], selftest_ok: bool) -> tuple[str, bool, str, str]:
    if not selftest_ok:
        return ("v1916-rollback-selftest-failed", False, "native rollback did not prove selftest fail=0", "rollback-selftest-failed")
    if not base_pass:
        return (f"v1916-base-handoff-failed-{base_decision}", False, "underlying Android handoff did not complete", "android-handoff-failed")
    files = analysis.get("files_present") or {}
    dmesg = analysis.get("dmesg") or {}
    contaminated = (
        base.boolish(dmesg.get("degraded_257s_like"))
        or base.intish(dmesg.get("pcie_mhi_before_wlan0")) > 0
        or base.intish(dmesg.get("esoc_boot_failed_before_wlan0")) > 0
    )
    if contaminated:
        return ("v1916-android-capture-rejected-degraded-or-pcie-mhi", False, "Android capture was degraded or had pre-wlan0 PCIe/MHI/eSoC contamination", "android-capture-rejected-degraded-or-pcie-mhi")
    stateup = (
        base.intish(analysis.get("service74_count")) > 0
        and base.intish(analysis.get("service180_count")) > 0
        and base.intish(analysis.get("wlan_pd_indication_count")) > 0
        and base.intish(analysis.get("wlanmdsp_count")) > 0
        and dmesg.get("wlan0_time_s") is not None
    )
    symbols = analysis.get("symbol_counts") or {}
    required_symbols = all(base.intish(symbols.get(name)) > 0 for name in [
        "service_notif_register_notifier",
        "service_notifier_new_server",
        "qmi_add_lookup",
        "qmi_servreg_notif",
        "qmi_servreg_loc",
    ])
    if not stateup:
        return ("v1916-android-normal-stateup-incomplete-rollback-pass", False, "Android capture did not prove normal service74/180 -> wlan_pd -> wlan0 state-up", "android-normal-stateup-incomplete")
    if not files.get("kallsyms_targets") or not files.get("kallsyms_broad") or not required_symbols:
        return ("v1916-android-broad-kallsyms-incomplete-rollback-pass", False, "Android state-up succeeded but broad kallsyms target symbols were incomplete", "android-broad-kallsyms-incomplete")
    if not files.get("tracefs_status"):
        return ("v1916-android-tracefs-status-missing-rollback-pass", False, "Android state-up succeeded but tracefs status was missing", "android-tracefs-status-missing")
    return (
        "v1916-android-broad-kallsyms-tracefs-internal-edge-captured-rollback-pass",
        True,
        "normal Android internal-modem state-up captured with broad service-notifier/servreg kallsyms and read-only tracefs availability, then rolled back to native v724",
        "android-broad-kallsyms-tracefs-internal-edge-captured",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = (manifest.get("context") or {}).get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    return "\n".join([
        "# Native Init V1916 Android Broad Kallsyms Tracefs Handoff",
        "",
        f"- Cycle: `{manifest['cycle']}`",
        "- Type: rollbackable Android-good broad read-only kallsyms/tracefs availability capture",
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
                ["contamination pcie-mhi/esoc/degraded257", f"{dmesg.get('pcie_mhi_before_wlan0')}/{dmesg.get('esoc_boot_failed_before_wlan0')}/{dmesg.get('degraded_257s_like')}"],
                ["first service74", analysis.get("first_service74_line", "")],
                ["first wlan_pd", analysis.get("first_wlan_pd_line", "")],
            ],
        ),
        "",
        "## Broad Kallsyms",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["target/broad lines", f"{analysis.get('kallsyms_target_line_count')}/{analysis.get('kallsyms_broad_line_count')}"],
                ["symbol counts", json.dumps(analysis.get("symbol_counts") or {}, sort_keys=True)],
                ["sys modules", json.dumps(analysis.get("sys_modules") or [])],
                ["module section/parameter lines", analysis.get("module_sections_line_count")],
            ],
        ),
        "",
        "## Tracefs Read-only Availability",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["status", json.dumps(analysis.get("tracefs_status") or {}, sort_keys=True)],
                ["filter lines", analysis.get("tracefs_filter_line_count")],
                ["filter symbol counts", json.dumps(analysis.get("tracefs_filter_symbol_counts") or {}, sort_keys=True)],
                ["event counts", json.dumps(analysis.get("tracefs_event_counts") or {}, sort_keys=True)],
                ["event excerpt", json.dumps(analysis.get("tracefs_event_excerpt") or [])],
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
        "Rollbackable Android-handoff to native v724 only. Android-side writes are limited to the temporary Magisk module and bounded evidence directory. The module reads `/proc/kallsyms`, `/proc/net/qrtr`, `/sys/module`, tracefs availability files, dmesg, logcat, and properties. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, restart-PD request, tracefs write, or partition write beyond the declared boot-image handoff/rollback.",
        "",
        "## Next",
        "",
        "- Use the captured broad symbol/tracefs availability to choose the next internal-modem service74 observer; do not pivot to SDX50M/PCIe/GDSC.",
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
            "v1916-android-broad-kallsyms-tracefs-plan-ready"
            if args.command == "plan"
            else "v1916-android-broad-kallsyms-tracefs-dryrun-ready"
        )
        pass_ok = bool(base_pass)
        reason = "plan/dry-run completed without Android-good live capture"
        label = "android-broad-kallsyms-tracefs-handoff-ready"
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
