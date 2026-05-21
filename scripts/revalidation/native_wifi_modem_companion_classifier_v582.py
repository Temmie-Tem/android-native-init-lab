#!/usr/bin/env python3
"""V582 read-only modem companion readiness classifier.

This tool classifies the missing V581 QRTR modem/service-notifier/sysmon gap as
userland-service, kernel-readiness, or evidence-stale. It uses Android evidence,
local extracted roots, and current native read-only state only. It does not
start daemons, write sysfs/qcwlanstate, scan, connect, route, or ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v582-modem-companion-classifier")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_ANDROID_DMESG = Path("tmp/wifi/v206-android-icnss-cnss-map/android/commands/dmesg-wifi-cnss-tail.txt")
DEFAULT_ANDROID_PROCESSES = Path("tmp/wifi/v206-android-icnss-cnss-map/android/commands/processes-wifi.txt")
DEFAULT_ANDROID_INITRC_FILES = Path("tmp/wifi/v206-android-icnss-cnss-map/android/commands/initrc-wifi-files.txt")
DEFAULT_ANDROID_INITRC_GREP = Path("tmp/wifi/v206-android-icnss-cnss-map/android/commands/initrc-wifi-grep.txt")
DEFAULT_ANDROID_LOGCAT = Path("tmp/wifi/v206-android-icnss-cnss-map/android/commands/logcat-wifi-cnss-tail.txt")
DEFAULT_V581_MANIFEST = Path("tmp/wifi/v581-icnss-order-gap/manifest.json")
DEFAULT_BINARY_ROOTS = (
    Path("tmp/wifi/v226-vendor-root-live-export/vendor-source"),
    Path("tmp/wifi/v222-vendor-root-evidence-export/vendor-root"),
    Path("tmp/wifi/v227-android-core-system-library-evidence/system-root"),
    Path("tmp/wifi/v396-frame-elf-pull-20260520-073940/system-root"),
)
SOURCE_REFERENCES = (
    "https://android.googlesource.com/kernel/msm/+/refs/heads/android-msm-crosshatch-4.9-s-preview-1/drivers/soc/qcom/service-notifier.c",
    "https://android.googlesource.com/kernel/msm/+/refs/heads/android-msm-crosshatch-4.9-s-preview-1/drivers/soc/qcom/sysmon-qmi.c",
    "https://android.googlesource.com/kernel/msm/+/refs/heads/android-msm-crosshatch-4.9-s-preview-1/net/qrtr/qrtr.c",
)

SERVICE_NAMES = (
    "sysmon-qmi",
    "service-notifier",
    "service_notifier",
    "qrtr-ns",
    "pd-mapper",
    "rmt_storage",
    "tftp_server",
    "cnss-daemon",
    "cnss_diag",
    "tqftpserv",
    "rmtfs",
    "qmiproxy",
    "ssgqmigd",
)
USERLAND_EXPECTED = {"qrtr-ns", "pd-mapper", "rmt_storage", "tftp_server", "cnss-daemon", "cnss_diag"}
KERNEL_EXPECTED = {"sysmon-qmi", "service-notifier", "service_notifier"}

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--android-processes", type=Path, default=DEFAULT_ANDROID_PROCESSES)
    parser.add_argument("--android-initrc-files", type=Path, default=DEFAULT_ANDROID_INITRC_FILES)
    parser.add_argument("--android-initrc-grep", type=Path, default=DEFAULT_ANDROID_INITRC_GREP)
    parser.add_argument("--android-logcat", type=Path, default=DEFAULT_ANDROID_LOGCAT)
    parser.add_argument("--v581-manifest", type=Path, default=DEFAULT_V581_MANIFEST)
    parser.add_argument("--binary-root", action="append", type=Path, default=None)
    parser.add_argument("command", choices=("plan", "run"))
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def read_text_if_exists(path: Path) -> tuple[bool, str, str]:
    resolved = repo_path(path)
    if not resolved.exists():
        return False, str(resolved), ""
    return True, str(resolved), resolved.read_text(encoding="utf-8", errors="replace")


def load_json_if_exists(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "invalid": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "invalid": "not-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             name: str,
             command: list[str],
             timeout: float | None = None) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["file"] = write_capture(store, name, text)
    item["payload"] = text
    return item


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("native")
    return [
        run_step(args, store, "version", ["version"], 15.0),
        run_step(args, store, "status", ["status"], 25.0),
        run_step(args, store, "selftest", ["selftest"], 25.0),
        run_step(args, store, "sys-module-list", ["run", args.toybox, "find", "/sys/module", "-maxdepth", "1"], 30.0),
        run_step(args, store, "proc-modules", ["run", args.toybox, "cat", "/proc/modules"], 20.0),
        run_step(args, store, "debug-kernel-list", ["run", args.toybox, "find", "/sys/kernel/debug", "-maxdepth", "2"], 20.0),
        run_step(args, store, "proc-net-protocols", ["run", args.toybox, "cat", "/proc/net/protocols"], 20.0),
        run_step(args, store, "proc-net-qrtr", ["cat", "/proc/net/qrtr"], 10.0),
    ]


def count_hits(text: str, patterns: dict[str, re.Pattern[str]]) -> dict[str, int]:
    counts = {name: 0 for name in patterns}
    for line in strip_ansi(text).splitlines():
        for name, pattern in patterns.items():
            if pattern.search(line):
                counts[name] += 1
    return counts


def lines_matching(text: str, pattern: re.Pattern[str], limit: int = 20) -> list[str]:
    lines = []
    for raw_line in strip_ansi(text).splitlines():
        line = raw_line.strip()
        if line and pattern.search(line):
            lines.append(line)
            if len(lines) >= limit:
                break
    return lines


def service_patterns() -> dict[str, re.Pattern[str]]:
    return {
        "sysmon-qmi": re.compile(r"\bsysmon-qmi\b|sysmon_qmi", re.I),
        "service-notifier": re.compile(r"\bservice-notifier\b|service_notifier", re.I),
        "wlan_pd": re.compile(r"wlan_pd|msm/modem/wlan_pd", re.I),
        "qrtr_modem_readiness": re.compile(r"qrtr: Modem QMI Readiness", re.I),
        "tftp_server": re.compile(r"\btftp_server\b|tftp-server", re.I),
        "rmt_storage": re.compile(r"\brmt_storage\b", re.I),
        "pd-mapper": re.compile(r"\bpd-mapper\b|pd_mapper", re.I),
        "qrtr-ns": re.compile(r"\bqrtr-ns\b", re.I),
        "cnss-daemon": re.compile(r"\bcnss-daemon\b", re.I),
        "cnss_diag": re.compile(r"\bcnss_diag\b", re.I),
    }


def android_evidence(args: argparse.Namespace) -> dict[str, Any]:
    dmesg_exists, dmesg_path, dmesg = read_text_if_exists(args.android_dmesg)
    proc_exists, proc_path, processes = read_text_if_exists(args.android_processes)
    init_files_exists, init_files_path, init_files = read_text_if_exists(args.android_initrc_files)
    init_grep_exists, init_grep_path, init_grep = read_text_if_exists(args.android_initrc_grep)
    logcat_exists, logcat_path, logcat = read_text_if_exists(args.android_logcat)
    patterns = service_patterns()
    sysmon_process_lines = lines_matching(processes, patterns["sysmon-qmi"])
    notifier_process_lines = lines_matching(processes, patterns["service-notifier"])
    sysmon_init_lines = lines_matching(init_files + "\n" + init_grep, patterns["sysmon-qmi"])
    notifier_init_lines = lines_matching(init_files + "\n" + init_grep, patterns["service-notifier"])
    service_init_lines = {
        name: lines_matching(init_files + "\n" + init_grep, pattern, limit=8)
        for name, pattern in patterns.items()
        if name not in {"sysmon-qmi", "service-notifier", "wlan_pd", "qrtr_modem_readiness"}
    }
    return {
        "paths": {
            "dmesg": dmesg_path,
            "processes": proc_path,
            "initrc_files": init_files_path,
            "initrc_grep": init_grep_path,
            "logcat": logcat_path,
        },
        "exists": dmesg_exists and proc_exists and init_files_exists and init_grep_exists,
        "logcat_exists": logcat_exists,
        "dmesg_counts": count_hits(dmesg, patterns),
        "process_counts": count_hits(processes, patterns),
        "init_counts": count_hits(init_files + "\n" + init_grep, patterns),
        "logcat_counts": count_hits(logcat, patterns),
        "sysmon_process_lines": sysmon_process_lines,
        "service_notifier_process_lines": notifier_process_lines,
        "sysmon_init_lines": sysmon_init_lines,
        "service_notifier_init_lines": notifier_init_lines,
        "service_init_lines": service_init_lines,
        "wlan_pd_lines": lines_matching(dmesg, patterns["wlan_pd"], limit=8),
        "sysmon_lines": lines_matching(dmesg, patterns["sysmon-qmi"], limit=8),
        "service_notifier_lines": lines_matching(dmesg, patterns["service-notifier"], limit=8),
        "tftp_logcat_lines": lines_matching(logcat, patterns["tftp_server"], limit=8),
    }


def binary_roots(args: argparse.Namespace) -> list[Path]:
    roots = list(args.binary_root or [])
    roots.extend(DEFAULT_BINARY_ROOTS)
    seen: set[Path] = set()
    result: list[Path] = []
    for root in roots:
        resolved = repo_path(root)
        if resolved in seen:
            continue
        seen.add(resolved)
        result.append(resolved)
    return result


def scan_binaries(args: argparse.Namespace) -> dict[str, Any]:
    hits = {name: [] for name in SERVICE_NAMES}
    roots = binary_roots(args)
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            name = path.name
            if name in hits:
                hits[name].append(str(path))
    return {
        "roots": [str(root) for root in roots],
        "hits": hits,
        "present": {name: bool(paths) for name, paths in hits.items()},
    }


def native_surface(steps: list[dict[str, Any]]) -> dict[str, Any]:
    status_text = step_payload(steps, "status")
    selftest_text = step_payload(steps, "selftest")
    module_list = step_payload(steps, "sys-module-list")
    proc_modules = step_payload(steps, "proc-modules")
    debug_list = step_payload(steps, "debug-kernel-list")
    protocols = step_payload(steps, "proc-net-protocols")
    proc_net_qrtr = step_payload(steps, "proc-net-qrtr")
    patterns = service_patterns()
    combined_modules = module_list + "\n" + proc_modules
    return {
        "native_healthy": "fail=0" in status_text and "fail=0" in selftest_text,
        "module_counts": count_hits(combined_modules, patterns),
        "debug_counts": count_hits(debug_list, patterns),
        "qipcrtr_protocol_present": "QIPCRTR" in protocols,
        "proc_net_qrtr_present": "No such file" not in proc_net_qrtr and "No such file or directory" not in proc_net_qrtr and bool(proc_net_qrtr.strip()),
        "sysmon_module_lines": lines_matching(combined_modules, patterns["sysmon-qmi"], limit=8),
        "service_notifier_module_lines": lines_matching(combined_modules, patterns["service-notifier"], limit=8),
        "debug_lines": lines_matching(debug_list, re.compile(r"sysmon|service|qrtr|qmi|wlan|cnss", re.I), limit=16),
    }


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(args: argparse.Namespace,
                 android: dict[str, Any],
                 binaries: dict[str, Any],
                 native: dict[str, Any],
                 v581: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run V582 classifier")
        return checks

    dmesg_counts = android["dmesg_counts"]
    process_counts = android["process_counts"]
    init_counts = android["init_counts"]
    present = binaries["present"]
    add_check(
        checks,
        "v581-reference-ready",
        "pass" if v581.get("decision") == "v581-native-missing-modem-qrtr-readiness-before-qcwlanstate" else "blocked",
        "blocker",
        f"decision={v581.get('decision')} pass={v581.get('pass')}",
        [str(v581.get("path"))],
        "run V581 before classifying modem companion source",
    )
    add_check(
        checks,
        "android-modem-companion-markers-present",
        "pass" if dmesg_counts.get("sysmon-qmi", 0) and dmesg_counts.get("service-notifier", 0) and dmesg_counts.get("wlan_pd", 0) else "blocked",
        "blocker",
        f"sysmon={dmesg_counts.get('sysmon-qmi', 0)} service_notifier={dmesg_counts.get('service-notifier', 0)} wlan_pd={dmesg_counts.get('wlan_pd', 0)}",
        android["sysmon_lines"][:2] + android["service_notifier_lines"][:2] + android["wlan_pd_lines"][:2],
        "refresh Android modem companion evidence",
    )
    add_check(
        checks,
        "sysmon-service-notifier-not-userspace-daemons",
        "pass" if process_counts.get("sysmon-qmi", 0) == 0 and process_counts.get("service-notifier", 0) == 0 and init_counts.get("sysmon-qmi", 0) == 0 and init_counts.get("service-notifier", 0) == 0 else "blocked",
        "blocker",
        f"process_sysmon={process_counts.get('sysmon-qmi', 0)} process_notifier={process_counts.get('service-notifier', 0)} init_sysmon={init_counts.get('sysmon-qmi', 0)} init_notifier={init_counts.get('service-notifier', 0)}",
        android["sysmon_process_lines"][:4] + android["service_notifier_process_lines"][:4] + android["sysmon_init_lines"][:4] + android["service_notifier_init_lines"][:4],
        "if userspace services exist, model and start them before qcwlanstate retry",
    )
    add_check(
        checks,
        "extracted-roots-lack-sysmon-notifier-binaries",
        "pass" if not present.get("sysmon-qmi") and not present.get("service-notifier") and not present.get("service_notifier") else "blocked",
        "blocker",
        f"sysmon_binary={present.get('sysmon-qmi')} notifier_binary={present.get('service-notifier') or present.get('service_notifier')}",
        (binaries["hits"].get("sysmon-qmi") or [])[:4] + (binaries["hits"].get("service-notifier") or [])[:4] + (binaries["hits"].get("service_notifier") or [])[:4],
        "locate userspace binary if present before live retry",
    )
    add_check(
        checks,
        "known-userland-companions-accounted",
        "pass",
        "info",
        "qrtr-ns/pd-mapper/rmt_storage/tftp_server/cnss-daemon/cnss_diag were already modeled in V579",
        [],
        "do not duplicate V579 companion replay unless lower readiness changes",
    )
    add_check(
        checks,
        "native-readonly-surface-clean",
        "pass" if native["native_healthy"] and native["qipcrtr_protocol_present"] and not native["proc_net_qrtr_present"] else "blocked",
        "blocker",
        f"native_healthy={native['native_healthy']} qipcrtr={native['qipcrtr_protocol_present']} proc_net_qrtr={native['proc_net_qrtr_present']}",
        native["debug_lines"][:8],
        "restore native baseline before more Wi-Fi work",
    )
    add_check(
        checks,
        "kernel-source-classification",
        "pass",
        "info",
        "service-notifier and sysmon-qmi are kernel QMI components in Qualcomm kernel sources; not Android init services in local evidence",
        list(SOURCE_REFERENCES),
        "next classify what triggers the kernel QRTR readiness path",
    )
    return checks


def blocking_checks(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return "v582-modem-companion-classifier-plan-ready", True, "plan-only; read-only classifier is ready", "run V582 classifier"
    blockers = blocking_checks(checks)
    if blockers:
        return "v582-modem-companion-classifier-blocked", False, "blocked by " + ", ".join(blockers), "refresh missing evidence before next Wi-Fi gate"
    return (
        "v582-kernel-modem-companion-readiness-gap-classified",
        True,
        "sysmon-qmi/service-notifier/WLAN-PD are kernel/QMI readiness evidence, not missing startable userspace daemons; native must trigger the modem QRTR readiness path before qcwlanstate/IWifi retry",
        "plan V583 around firmware/modem mounts, QRTR modem readiness trigger, and service-notifier/sysmon kernel surface; keep scan/connect blocked",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    android = manifest.get("android_evidence") or {}
    native = manifest.get("native_surface") or {}
    binaries = manifest.get("binary_scan") or {}
    android_rows = [
        ["dmesg_counts", android.get("dmesg_counts", {})],
        ["process_counts", android.get("process_counts", {})],
        ["init_counts", android.get("init_counts", {})],
        ["logcat_counts", android.get("logcat_counts", {})],
    ]
    binary_rows = [[name, str(value), ", ".join((binaries.get("hits") or {}).get(name, [])[:2])] for name, value in sorted((binaries.get("present") or {}).items())]
    native_rows = [
        ["native_healthy", native.get("native_healthy", "")],
        ["module_counts", native.get("module_counts", {})],
        ["debug_counts", native.get("debug_counts", {})],
        ["qipcrtr_protocol_present", native.get("qipcrtr_protocol_present", "")],
        ["proc_net_qrtr_present", native.get("proc_net_qrtr_present", "")],
    ]
    return "\n".join([
        "# V582 Modem Companion Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], checks),
        "",
        "## Android Evidence",
        "",
        markdown_table(["key", "value"], android_rows),
        "",
        "## Binary Scan",
        "",
        markdown_table(["name", "present", "sample paths"], binary_rows),
        "",
        "## Native Read-Only Surface",
        "",
        markdown_table(["key", "value"], native_rows),
        "",
        "## Source References",
        "",
        *[f"- {item}" for item in manifest["source_references"]],
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v581 = load_json_if_exists(args.v581_manifest)
    android = android_evidence(args)
    binaries = scan_binaries(args)
    steps: list[dict[str, Any]] = []
    native = {
        "native_healthy": False,
        "module_counts": {},
        "debug_counts": {},
        "qipcrtr_protocol_present": False,
        "proc_net_qrtr_present": False,
    }
    if args.command == "run":
        steps = collect_steps(args, store)
        native = native_surface(steps)
    checks = build_checks(args, android, binaries, native, v581)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "steps": steps,
        "checks": [asdict(check) for check in checks],
        "v581_manifest": {
            "exists": v581.get("exists"),
            "path": v581.get("path"),
            "decision": v581.get("decision"),
            "pass": v581.get("pass"),
            "reason": v581.get("reason"),
        },
        "android_evidence": android,
        "binary_scan": binaries,
        "native_surface": native,
        "source_references": list(SOURCE_REFERENCES),
        "device_commands_executed": args.command == "run",
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
