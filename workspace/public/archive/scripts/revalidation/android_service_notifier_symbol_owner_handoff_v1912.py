#!/usr/bin/env python3
"""V1912 Android-good service-notifier symbol-owner handoff.

This runner reuses the proven V1521/V1753 rollbackable Android handoff pattern:
flash Android, install a temporary Magisk post-fs-data module, collect read-only
`/proc/kallsyms` and module ownership evidence for the service-notifier
publication edge, remove the module, and restore native v725-fasttransport.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text

import android_rc1_magisk_postfs_sampler_handoff_v1521 as v1521


CYCLE = "V1912"
DEFAULT_OUT_DIR = Path("tmp/wifi/v1912-android-service-notifier-symbol-owner-handoff")
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v725_fasttransport.img")
DEFAULT_NATIVE_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
DEFAULT_REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1912_ANDROID_SERVICE_NOTIFIER_SYMBOL_OWNER_HANDOFF_2026-06-03.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1912-android-service-notifier-symbol-owner-handoff.txt")

MODULE_NAME = "a90_v1912_servnotif_owner"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1912-servnotif-owner"

ORIGINAL_BUILD_PLAN = v1521.build_plan
DMESG_TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")
KALLSYMS_RE = re.compile(r"^\S+\s+\S\s+(?P<symbol>\S+)(?:\s+\[(?P<module>[^\]]+)\])?")
SERVICE74_RE = re.compile(r"service_notifier_new_server: .* 74 service", re.IGNORECASE)
SERVICE180_RE = re.compile(r"service_notifier_new_server: .* 180 service", re.IGNORECASE)
WLAN_PD_RE = re.compile(r"service-notifier: .*msm/modem/wlan_pd", re.IGNORECASE)
WLAN0_RE = re.compile(r"\bdev : wlan0\b|\bicnss .*wlan0|\bwlan0\b", re.IGNORECASE)
WLFW_REQUEST_RE = re.compile(r"wlfw_service_request", re.IGNORECASE)
WLANMDSP_RE = re.compile(r"wlanmdsp\.mbn", re.IGNORECASE)
PCIE_MHI_RE = re.compile(r"PCIe RC1 link initialized|mhi .*enabling device|\bMHI\b|pcie_initialized|mhi_enable", re.IGNORECASE)
ESOC_BOOT_FAILED_RE = re.compile(r"esoc0.*boot.*fail|boot_failed", re.IGNORECASE)
REDACT_CMD = "sed -E 's/t[e]mmie[[:alnum:]_@.-]*/[REDACTED]/g'"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


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
    parser.add_argument("--sampler-samples", type=int, default=2)
    parser.add_argument("--sampler-delay-us", type=int, default=0)
    parser.add_argument("--sampler-wait-timeout", type=int, default=80)
    parser.add_argument("--allow-android-boot-flash", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-native-rollback", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("dry-run")
    subparsers.add_parser("run")
    return parser.parse_args()


def module_prop() -> str:
    return "\n".join(
        [
            f"id={MODULE_NAME}",
            "name=A90 V1912 service-notifier symbol owner observer",
            "version=1",
            "versionCode=1",
            "author=A90 native-init project",
            "description=Temporary read-only Android-good kallsyms/module owner observer. Remove after capture.",
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
    related_symbols = (
        "service_notif|service_notifier|service_locator|service-locator|qmi_add_lookup|"
        "icnss_get_service_location_notify|icnss.*service|wlfw_service_request|servreg|ssctl"
    )
    return f"""#!/system/bin/sh
OUT={REMOTE_EVIDENCE_DIR}
FILTER='{filter_expr}'
RELATED_SYMBOLS='{related_symbols}'
mkdir -p "$OUT" 2>/dev/null
chmod 755 "$OUT" 2>/dev/null
STATUS="$OUT/status.txt"
LOG="$OUT/samples.log"
DMESG="$OUT/dmesg-filtered.txt"
LOGCAT="$OUT/logcat-filtered.txt"
PROPS="$OUT/props.txt"
KALL_TARGET="$OUT/kallsyms-service-notifier-target.txt"
KALL_RELATED="$OUT/kallsyms-related.txt"
MODULES="$OUT/proc-modules.txt"
SYS_MODULES="$OUT/sys-modules.txt"
OWNERS="$OUT/module-owners.txt"
SYSCTL="$OUT/sysctl-readonly.txt"

uptime_now() {{
  cat /proc/uptime 2>/dev/null | awk '{{print $1}}'
}}

write_status() {{
  now="$(uptime_now)"
  echo "A90_V1912_STATUS $1 $now" > "$STATUS"
  echo "A90_V1521_STATUS $1 $now" >> "$STATUS"
}}

dump_logs() {{
  dmesg 2>&1 | grep -Ei "$FILTER" | tail -n 3000 > "$DMESG.tmp" || true
  mv "$DMESG.tmp" "$DMESG" 2>/dev/null || true
  logcat -d 2>/dev/null | grep -Ei "$FILTER" | tail -n 3000 > "$LOGCAT.tmp" || true
  mv "$LOGCAT.tmp" "$LOGCAT" 2>/dev/null || true
}}

dump_props() {{
  for p in sys.boot_completed dev.bootcomplete init.svc.vendor.per_mgr init.svc.vendor.pm-service init.svc.vendor.rmt_storage init.svc.vendor.tftp_server init.svc.cnss-daemon ro.boottime.vendor.per_mgr ro.boottime.vendor.pm-service ro.boottime.vendor.tftp_server ro.boottime.cnss-daemon; do
    echo "$p=$(getprop "$p" 2>/dev/null)"
  done > "$PROPS.tmp"
  mv "$PROPS.tmp" "$PROPS" 2>/dev/null || true
}}

dump_symbols() {{
  cat /proc/kallsyms 2>&1 | grep -E '(^|[[:space:]])(__ksymtab_|__kstrtab_|__kcrctab_)?service_notif_register_notifier([[:space:]]|$)' > "$KALL_TARGET.tmp" || true
  mv "$KALL_TARGET.tmp" "$KALL_TARGET" 2>/dev/null || true
  cat /proc/kallsyms 2>&1 | grep -Ei "$RELATED_SYMBOLS" | head -n 1200 > "$KALL_RELATED.tmp" || true
  mv "$KALL_RELATED.tmp" "$KALL_RELATED" 2>/dev/null || true
  cat /proc/modules 2>&1 > "$MODULES.tmp" || true
  mv "$MODULES.tmp" "$MODULES" 2>/dev/null || true
  ls -1 /sys/module 2>/dev/null | grep -Ei 'service|notif|locator|qmi|qrtr|ipc_router|icnss|cnss|wlan|wcnss|ssr|subsys' > "$SYS_MODULES.tmp" || true
  mv "$SYS_MODULES.tmp" "$SYS_MODULES" 2>/dev/null || true
  {{
    echo "A90_V1912_KPTR_RESTRICT $(cat /proc/sys/kernel/kptr_restrict 2>/dev/null)"
    echo "A90_V1912_PERF_PARANOID $(cat /proc/sys/kernel/perf_event_paranoid 2>/dev/null)"
  }} > "$SYSCTL.tmp"
  mv "$SYSCTL.tmp" "$SYSCTL" 2>/dev/null || true
  {{
    echo "A90_V1912_MODULE_OWNER_BEGIN"
    awk 'NF >= 3 {{ mod="builtin"; if ($NF ~ /^\\[.*\\]$/) mod=$NF; print $3 " " mod; }}' "$KALL_TARGET" 2>/dev/null || true
    echo "A90_V1912_MODULE_OWNER_END"
    for m in service_notifier service-locator service_locator qmi_helpers qmi_encdec qrtr ipc_router icnss cnss2 cnss_wlan; do
      [ -d "/sys/module/$m" ] || continue
      echo "MODULE $m"
      [ -r "/sys/module/$m/refcnt" ] && printf 'refcnt=' && cat "/sys/module/$m/refcnt"
      [ -d "/sys/module/$m/holders" ] && {{ printf 'holders='; ls -1 "/sys/module/$m/holders" 2>/dev/null | tr '\\n' ' '; printf '\\n'; }}
    done
  }} > "$OWNERS.tmp"
  mv "$OWNERS.tmp" "$OWNERS" 2>/dev/null || true
}}

(
  umask 022
  : > "$LOG"
  echo "A90_V1912_POSTFS_BEGIN uptime=$(uptime_now)" >> "$LOG"
  write_status start
  echo "A90_V1912_SAMPLE_BEGIN label=early uptime=$(uptime_now)" >> "$LOG"
  dump_symbols
  dump_logs
  dump_props
  echo "A90_V1912_SAMPLE_END label=early uptime=$(uptime_now)" >> "$LOG"
  write_status early
  sleep 18
  echo "A90_V1912_SAMPLE_BEGIN label=late uptime=$(uptime_now)" >> "$LOG"
  dump_symbols
  dump_logs
  dump_props
  echo "SRC kallsyms_service_notifier_target" >> "$LOG"
  cat "$KALL_TARGET" >> "$LOG" 2>/dev/null || true
  echo "SRC module_owners" >> "$LOG"
  cat "$OWNERS" >> "$LOG" 2>/dev/null || true
  echo "A90_V1912_SAMPLE_END label=late uptime=$(uptime_now)" >> "$LOG"
  echo "A90_V1912_POSTFS_END uptime=$(uptime_now)" >> "$LOG"
  write_status done
  touch "$OUT/done"
  chmod 755 "$OUT" 2>/dev/null
  chmod 644 "$OUT"/* 2>/dev/null
) >/dev/null 2>&1 &
exit 0
"""


def redacted_a90ctl_command(kind: str) -> list[str]:
    if kind == "version":
        inner = f"python3 scripts/revalidation/a90ctl.py --json version | {REDACT_CMD}"
    elif kind == "status":
        inner = f"python3 scripts/revalidation/a90ctl.py status | {REDACT_CMD}"
    else:
        raise ValueError(kind)
    return ["bash", "-lc", inner]


def redacted_shell_pipeline(command: list[str]) -> list[str]:
    return ["bash", "-lc", f"set -o pipefail; {shlex.join(command)} | {REDACT_CMD}"]


def build_plan_v1912(args: argparse.Namespace, store: EvidenceStore, android_image: Any, native_image: Any) -> list[tuple[str, list[str] | str, int]]:
    plan = ORIGINAL_BUILD_PLAN(args, store, android_image, native_image)
    updated: list[tuple[str, list[str] | str, int]] = []
    for name, command, timeout in plan:
        if name == "native-version":
            updated.append(("native-version-redacted", redacted_a90ctl_command("version"), timeout))
        elif name == "native-status":
            updated.append(("native-status-redacted", redacted_a90ctl_command("status"), timeout))
        elif name == "restore-native" and isinstance(command, list):
            updated.append((name, redacted_shell_pipeline(command), timeout))
        else:
            updated.append((name, command, timeout))
    updated.append(("post-rollback-native-status-redacted", redacted_a90ctl_command("status"), args.timeout))
    return updated


def evidence_base(store: EvidenceStore) -> Path:
    root = v1521.pulled_evidence_dir(store)
    candidate = root / Path(REMOTE_EVIDENCE_DIR).name
    return candidate if candidate.is_dir() else root


def read_pulled(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def first_dmesg_time(lines: list[str], regex: re.Pattern[str]) -> float | None:
    for line in lines:
        if not regex.search(line):
            continue
        match = DMESG_TIME_RE.search(line)
        if match:
            return float(match.group("time"))
    return None


def count_lines(lines: list[str] | str, regex: re.Pattern[str]) -> int:
    iterable = lines.splitlines() if isinstance(lines, str) else lines
    return sum(1 for line in iterable if regex.search(line))


def first_line(lines: list[str] | str, regex: re.Pattern[str]) -> str:
    iterable = lines.splitlines() if isinstance(lines, str) else lines
    for line in iterable:
        if regex.search(line):
            return line.strip()
    return ""


def count_dmesg_before(lines: list[str], regex: re.Pattern[str], before_time: float | None) -> int:
    count = 0
    for line in lines:
        match = DMESG_TIME_RE.search(line)
        if not match:
            continue
        if before_time is not None and float(match.group("time")) > before_time:
            continue
        if regex.search(line):
            count += 1
    return count


def parse_kallsyms_targets(text: str) -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []
    for line in text.splitlines():
        match = KALLSYMS_RE.match(line.strip())
        if not match:
            continue
        symbol = match.group("symbol")
        module = match.group("module") or "builtin"
        targets.append({"symbol": symbol, "module": module, "line": line.strip()})
    return targets


def analyze_pulled_evidence(store: EvidenceStore) -> dict[str, Any]:
    root = v1521.pulled_evidence_dir(store)
    base = evidence_base(store)
    samples = read_pulled(base / "samples.log")
    dmesg = read_pulled(base / "dmesg-filtered.txt") + "\n" + read_pulled(root / "host-dmesg-filtered.txt")
    logcat = read_pulled(base / "logcat-filtered.txt")
    props = read_pulled(base / "props.txt")
    status = read_pulled(base / "status.txt")
    kall_target = read_pulled(base / "kallsyms-service-notifier-target.txt")
    kall_related = read_pulled(base / "kallsyms-related.txt")
    modules = read_pulled(base / "proc-modules.txt")
    sys_modules = read_pulled(base / "sys-modules.txt")
    owners = read_pulled(base / "module-owners.txt")
    sysctl = read_pulled(base / "sysctl-readonly.txt")
    targets = parse_kallsyms_targets(kall_target)
    exact_targets = [item for item in targets if item["symbol"] == "service_notif_register_notifier"]
    owner_set = sorted({item["module"] for item in exact_targets})
    dmesg_lines = dmesg.splitlines()
    logcat_lines = logcat.splitlines()
    all_lines = dmesg_lines + logcat_lines
    wlan0_time = first_dmesg_time(dmesg_lines, WLAN0_RE)
    pcie_mhi_before = count_dmesg_before(dmesg_lines, PCIE_MHI_RE, wlan0_time)
    esoc_failed_before = count_dmesg_before(dmesg_lines, ESOC_BOOT_FAILED_RE, wlan0_time)
    return {
        "base": rel(base),
        "files_present": {
            "samples": bool(samples),
            "dmesg": bool(dmesg.strip()),
            "props": bool(props),
            "status": bool(status),
            "done": (base / "done").exists(),
            "kallsyms_target": bool(kall_target.strip()),
            "kallsyms_related": bool(kall_related.strip()),
            "modules": bool(modules.strip()),
            "sys_modules": bool(sys_modules.strip()),
            "owners": bool(owners.strip()),
        },
        "status_text": status.strip(),
        "sample_count": samples.count("A90_V1912_SAMPLE_BEGIN"),
        "kallsyms_target_lines": targets,
        "service_notif_register_notifier_lines": exact_targets,
        "service_notif_register_notifier_count": len(exact_targets),
        "service_notif_register_notifier_owners": owner_set,
        "kallsyms_related_line_count": len(kall_related.splitlines()) if kall_related else 0,
        "proc_modules_line_count": len(modules.splitlines()) if modules else 0,
        "sys_modules": [line.strip() for line in sys_modules.splitlines() if line.strip()],
        "module_owners_text": owners.strip(),
        "sysctl_text": sysctl.strip(),
        "dmesg": {
            "wlfw_lines": count_lines(all_lines, re.compile(r"\bwlfw\b|WLFW", re.IGNORECASE)),
            "bdf_lines": count_lines(all_lines, re.compile(r"BDF file|regdb\.bin|bdwlan\.bin", re.IGNORECASE)),
            "wlan0_lines": count_lines(all_lines, re.compile(r"\bwlan0\b", re.IGNORECASE)),
            "wlan0_time_s": wlan0_time,
            "pcie_mhi_before_wlan0": pcie_mhi_before,
            "esoc_boot_failed_before_wlan0": esoc_failed_before,
            "degraded_257s_like": wlan0_time is not None and wlan0_time > 120.0,
        },
        "service74_count": count_lines(dmesg_lines, SERVICE74_RE),
        "service180_count": count_lines(dmesg_lines, SERVICE180_RE),
        "wlan_pd_indication_count": count_lines(dmesg_lines, WLAN_PD_RE),
        "wlfw_service_request_count": count_lines(all_lines, WLFW_REQUEST_RE),
        "wlanmdsp_count": count_lines(all_lines, WLANMDSP_RE),
        "first_service74_line": first_line(dmesg_lines, SERVICE74_RE),
        "first_service180_line": first_line(dmesg_lines, SERVICE180_RE),
        "first_wlan_pd_line": first_line(dmesg_lines, WLAN_PD_RE),
        "first_wlanmdsp_line": first_line(all_lines, WLANMDSP_RE),
        "props_text": props.strip(),
        "matched_window": {"first_lower_time": wlan0_time},
    }


def step_text(store: EvidenceStore, step: Any) -> str:
    return (store.run_dir / step.file).read_text(encoding="utf-8", errors="replace") if step.file else ""


def rollback_selftest_ok(store: EvidenceStore, steps: list[Any]) -> bool:
    for step in reversed(steps):
        if step.name == "post-rollback-native-status-redacted":
            return bool(re.search(r"selftest:\s+pass=\d+\s+warn=\d+\s+fail=0\b", step_text(store, step)))
    return False


def classify_result(base_decision: str, base_pass: bool, analysis: dict[str, Any], selftest_ok: bool) -> tuple[str, bool, str, str]:
    if not selftest_ok:
        return ("v1912-rollback-selftest-failed", False, "native rollback did not prove selftest fail=0", "rollback-selftest-failed")
    if not base_pass:
        return (f"v1912-base-handoff-failed-{base_decision}", False, "underlying Android handoff did not complete", "android-handoff-failed")
    files = analysis.get("files_present") or {}
    if not files.get("kallsyms_target"):
        return ("v1912-android-kallsyms-target-missing-rollback-pass", False, "Android handoff completed but target kallsyms lines were missing", "android-kallsyms-target-missing")
    owners = analysis.get("service_notif_register_notifier_owners") or []
    if not owners:
        return ("v1912-android-service-notifier-register-symbol-unparsed", False, "target kallsyms output did not parse service_notif_register_notifier", "android-service-notifier-register-symbol-unparsed")
    dmesg = analysis.get("dmesg") or {}
    contaminated = boolish(dmesg.get("degraded_257s_like")) or intish(dmesg.get("pcie_mhi_before_wlan0")) > 0 or intish(dmesg.get("esoc_boot_failed_before_wlan0")) > 0
    if contaminated:
        return ("v1912-android-capture-rejected-degraded-or-pcie-mhi", False, "Android capture was degraded or had pre-wlan0 PCIe/MHI/eSoC contamination", "android-capture-rejected-degraded-or-pcie-mhi")
    stateup = (
        intish(analysis.get("service74_count")) > 0
        and intish(analysis.get("service180_count")) > 0
        and intish(analysis.get("wlan_pd_indication_count")) > 0
        and intish(analysis.get("wlanmdsp_count")) > 0
        and dmesg.get("wlan0_time_s") is not None
    )
    if not stateup:
        return ("v1912-android-normal-stateup-incomplete-rollback-pass", False, "Android capture did not prove normal service74/180 -> wlan_pd -> wlan0 state-up", "android-normal-stateup-incomplete")
    owner_label = "-".join(str(owner).replace("_", "-").replace(".", "-") for owner in owners)
    if owners == ["builtin"]:
        return (
            "v1912-android-service-notifier-register-builtin-normal-stateup-pass",
            True,
            "normal Android state-up captured and service_notif_register_notifier is built into the kernel, not owned by a loadable module",
            "android-service-notifier-register-builtin-normal-stateup",
        )
    return (
        f"v1912-android-service-notifier-register-owner-{owner_label}-normal-stateup-pass",
        True,
        f"normal Android state-up captured and service_notif_register_notifier owner is {owners}",
        f"android-service-notifier-register-owner-{owner_label}-normal-stateup",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = (manifest.get("context") or {}).get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    return "\n".join(
        [
            "# Native Init V1912 Android Service-notifier Symbol-owner Handoff",
            "",
            f"- Cycle: `{manifest['cycle']}`",
            f"- Type: rollbackable Android-good read-only kallsyms/module-owner capture",
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
            "## Symbol Ownership",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["service_notif_register_notifier count", analysis.get("service_notif_register_notifier_count")],
                    ["owners", json.dumps(analysis.get("service_notif_register_notifier_owners") or [])],
                    ["target lines", json.dumps(analysis.get("service_notif_register_notifier_lines") or [])],
                    ["related kallsyms lines", analysis.get("kallsyms_related_line_count")],
                    ["sys_modules", json.dumps(analysis.get("sys_modules") or [])],
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
            "Rollbackable Android-handoff to native v724 only. Android-side writes are limited to the temporary Magisk module and bounded evidence directory. The module reads `/proc/kallsyms`, `/proc/modules`, `/sys/module`, dmesg, logcat, and properties. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, restart-PD request, tracefs write, or partition write beyond the declared boot-image handoff/rollback.",
            "",
            "## Next",
            "",
            "- If the owner is `builtin`, keep the trigger search on the internal-modem kernel/servreg publication edge and do not pivot to SDX50M/PCIe/GDSC.",
            "- Do not attempt Wi-Fi credentials/connect/ping until native proves WLFW service69 and `wlan0`.",
            "",
        ]
    )


def configure_engine() -> None:
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
    v1521.analyze_pulled_evidence = analyze_pulled_evidence
    v1521.build_plan = build_plan_v1912


def main() -> int:
    configure_engine()
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    execute = args.command == "run"
    steps, context, base_decision, base_pass = v1521.execute_plan(args, store, execute=execute)
    analysis = context.get("analysis") or {}
    selftest_ok = rollback_selftest_ok(store, steps) if execute else False
    if execute:
        decision, pass_ok, reason, label = classify_result(base_decision, base_pass, analysis, selftest_ok)
    else:
        decision = "v1912-android-service-notifier-symbol-owner-plan-ready" if args.command == "plan" else "v1912-android-service-notifier-symbol-owner-dryrun-ready"
        pass_ok = bool(base_pass)
        reason = "plan/dry-run completed without Android-good live capture"
        label = "android-service-notifier-symbol-owner-handoff-ready"
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
        "rollback_selftest_fail0": selftest_ok,
        "steps": [asdict(step) for step in steps],
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
    sys.exit(main())
