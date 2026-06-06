#!/usr/bin/env python3
"""V520 host-only companion-service availability planner.

This tool does not talk to the device. It reduces V519, Android reference
captures, local extracted roots, and prior QRTR evidence into the next safe
availability proof before any qcwlanstate retry, CNSS daemon retry, Wi-Fi HAL
start, scan/connect, link-up, DHCP, route change, or external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v520-companion-service-availability-plan")
DEFAULT_V519_MANIFEST = Path("tmp/wifi/v519-android-native-qrtr-modem-delta/manifest.json")
DEFAULT_ANDROID_V206_DIR = Path("tmp/wifi/v206-android-icnss-cnss-map/android/commands")
DEFAULT_ANDROID_V425_DIR = Path("tmp/wifi/v425-settled-handoff-live-20260520-134752/v423-android-hwservice-bootcomplete-run/commands")
DEFAULT_V250_MANIFEST = Path("tmp/wifi/v250-qrtr-socket-probe/manifest.json")
DEFAULT_V270_LONG_MANIFEST = Path("tmp/wifi/v270-qrtr-ns-readback-live-long-20260519-103732/manifest.json")
DEFAULT_V276_MANIFEST = Path("tmp/wifi/v276-qrtr-cnss-registration-correlation/manifest.json")
DEFAULT_BINARY_ROOTS = (
    Path("tmp/wifi/v226-vendor-root-live-export/vendor-source"),
    Path("tmp/wifi/v222-vendor-root-evidence-export/vendor-root"),
    Path("tmp/wifi/v227-android-core-system-library-evidence/system-root"),
    Path("tmp/wifi/v396-frame-elf-pull-20260520-073940/system-root"),
)

COMPANION_NAMES = (
    "qrtr-ns",
    "qmiproxy",
    "sysmon-qmi",
    "service-notifier",
    "rmtfs",
    "pd-mapper",
    "tqftpserv",
)
LOCAL_BINARY_NAMES = set(COMPANION_NAMES) | {"cnss-daemon", "cnss_diag"}
COMPANION_RE = re.compile(r"qrtr-ns|qmiproxy|sysmon-qmi|service-notifier|rmtfs|pd-mapper|tqftpserv", re.IGNORECASE)
QMI_SEQUENCE_RE = re.compile(r"Modem QMI Readiness|sysmon-qmi|service-notifier|wlan_pd|QMI Server Connected|BDF file|WLAN FW is ready", re.IGNORECASE)
SOURCE_REFERENCES = (
    "https://wiki.postmarketos.org/wiki/SDM845_Mainlining",
    "https://wiki.postmarketos.org/wiki/Qualcomm_Snapdragon_845/850_(SDM845/SDM850)#WiFi",
    "https://gitlab.com/postmarketOS/pmaports/-/issues/863",
    "https://packages.debian.org/sid/protection-domain-mapper",
    "https://packages.debian.org/source/bookworm/tqftpserv",
)

ANDROID_RECAPTURE_COMMANDS = (
    (
        "companion-processes",
        "adb shell su -c 'ps -AZ 2>/dev/null | grep -Ei "
        "\"qrtr|qmi|qmiproxy|sysmon|service-notifier|rmtfs|pd-mapper|tqftp|cnss|wlan|wifi|servicemanager|perfd\" || true'",
    ),
    (
        "companion-props",
        "adb shell su -c 'getprop | grep -Ei "
        "\"init\\.svc\\..*(qrtr|qmi|qmiproxy|sysmon|service|rmtfs|pd|tqftp|cnss|wifi|wlan)|"
        "ro\\.boottime\\..*(qrtr|qmi|qmiproxy|sysmon|service|rmtfs|pd|tqftp|cnss|wifi|wlan)|"
        "qrtr|qmi|qmiproxy|sysmon|service-notifier|rmtfs|pd-mapper|tqftp|wlan_pd|firmware\" || true'",
    ),
    (
        "companion-initrc",
        "adb shell su -c 'grep -RHiE "
        "\"service .*(qrtr|qmi|qmiproxy|sysmon|service-notifier|rmtfs|pd-mapper|tqftp|cnss|wifi|wlan)|"
        "on property:.*(qrtr|qmi|qmiproxy|sysmon|rmtfs|pd-mapper|tqftp|cnss|wifi|wlan)|wlan_pd|pdr\" "
        "/system/etc/init /system_ext/etc/init /vendor/etc/init /odm/etc/init /product/etc/init 2>/dev/null || true'",
    ),
    (
        "companion-binaries",
        "adb shell su -c 'find /system /system_ext /vendor /odm /product -type f "
        "\\( -name qrtr-ns -o -name qmiproxy -o -name sysmon-qmi -o -name service-notifier "
        "-o -name rmtfs -o -name pd-mapper -o -name tqftpserv -o -name cnss-daemon -o -name cnss_diag \\) "
        "2>/dev/null | sort || true'",
    ),
    (
        "companion-dmesg",
        "adb shell su -c 'dmesg 2>/dev/null | grep -Ei "
        "\"qrtr|qmi|qmiproxy|sysmon|service-notifier|wlan_pd|rmtfs|pd-mapper|tqftp|cnss|icnss|bdf|bdwlan|regdb|firmware\" "
        "| tail -n 1000 || true'",
    ),
)


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
    parser.add_argument("--v519-manifest", type=Path, default=DEFAULT_V519_MANIFEST)
    parser.add_argument("--android-v206-dir", type=Path, default=DEFAULT_ANDROID_V206_DIR)
    parser.add_argument("--android-v425-dir", type=Path, default=DEFAULT_ANDROID_V425_DIR)
    parser.add_argument("--v250-manifest", type=Path, default=DEFAULT_V250_MANIFEST)
    parser.add_argument("--v270-long-manifest", type=Path, default=DEFAULT_V270_LONG_MANIFEST)
    parser.add_argument("--v276-manifest", type=Path, default=DEFAULT_V276_MANIFEST)
    parser.add_argument("--binary-root", action="append", type=Path, default=None)
    parser.add_argument("command", choices=("plan", "run"))
    return parser.parse_args()


def read_text(path: Path) -> tuple[bool, str, str]:
    resolved = repo_path(path)
    if not resolved.exists():
        return False, str(resolved), ""
    return True, str(resolved), resolved.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "invalid": True}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def unique_focus_lines(texts: list[str], pattern: re.Pattern[str], limit: int = 120) -> list[str]:
    seen: set[str] = set()
    lines: list[str] = []
    for text in texts:
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("$"):
                continue
            if not pattern.search(line):
                continue
            if line in seen:
                continue
            seen.add(line)
            lines.append(line)
            if len(lines) >= limit:
                return lines
    return lines


def roots(args: argparse.Namespace) -> list[Path]:
    items = list(DEFAULT_BINARY_ROOTS)
    if args.binary_root:
        items.extend(args.binary_root)
    return items


def binary_inventory(root_paths: list[Path]) -> dict[str, Any]:
    found: dict[str, list[dict[str, Any]]] = {name: [] for name in sorted(LOCAL_BINARY_NAMES)}
    scanned: list[dict[str, Any]] = []
    for root in root_paths:
        resolved = repo_path(root)
        scanned.append({"path": str(resolved), "exists": resolved.exists()})
        if not resolved.exists() or not resolved.is_dir():
            continue
        for path in resolved.rglob("*"):
            if not path.is_file() or path.name not in LOCAL_BINARY_NAMES:
                continue
            try:
                stat_info = path.stat()
                mode = stat_info.st_mode & 0o7777
                rel = path.relative_to(resolved)
            except OSError:
                continue
            found[path.name].append({
                "root": str(resolved),
                "relative_path": str(rel),
                "size": stat_info.st_size,
                "mode": oct(mode),
                "executable": bool(mode & 0o111),
            })
    return {
        "roots": scanned,
        "summary": {name: {"count": len(paths), "paths": paths} for name, paths in found.items()},
        "has_android_vendor_equivalent": bool(found["qrtr-ns"] or found["qmiproxy"] or found["sysmon-qmi"] or found["service-notifier"]),
        "has_mainline_set": bool(found["rmtfs"] and found["pd-mapper"] and found["tqftpserv"]),
        "has_cnss_set": bool(found["cnss-daemon"] and found["cnss_diag"]),
    }


def android_surface(args: argparse.Namespace, store: EvidenceStore, command: str) -> dict[str, Any]:
    files = {
        "v206_processes": args.android_v206_dir / "processes-wifi.txt",
        "v206_props": args.android_v206_dir / "wifi-props-init-state.txt",
        "v206_initrc": args.android_v206_dir / "initrc-wifi-grep.txt",
        "v206_dmesg": args.android_v206_dir / "dmesg-wifi-cnss-tail.txt",
        "v206_devnodes": args.android_v206_dir / "devnodes-sockets-wifi.txt",
        "v425_processes": args.android_v425_dir / "service-processes.txt",
        "v425_props": args.android_v425_dir / "identity-props.txt",
    }
    records: dict[str, Any] = {}
    texts: list[str] = []
    texts_by_name: dict[str, str] = {}
    for name, path in files.items():
        exists, resolved, text = read_text(path)
        records[name] = {"exists": exists, "path": resolved}
        if exists:
            texts.append(text)
            texts_by_name[name] = text
            if command == "run":
                store.write_text(f"inputs/{name}.txt", text.rstrip() + "\n")

    companion_lines = unique_focus_lines(texts, COMPANION_RE)
    qmi_lines = unique_focus_lines(texts, QMI_SEQUENCE_RE)
    all_text = "\n".join(texts)
    process_text = "\n".join(text for name, text in texts_by_name.items() if "process" in name)
    return {
        "inputs": records,
        "companion_lines": companion_lines,
        "qmi_sequence_lines": qmi_lines,
        "has_qrtr_ns_process": bool(re.search(r"\bqrtr-ns\b", all_text)),
        "has_qmiproxy_initrc": bool(re.search(r"service\s+qmiproxy\b", all_text)),
        "has_sysmon_qmi_dmesg": bool(re.search(r"sysmon-qmi", all_text, re.IGNORECASE)),
        "has_service_notifier_dmesg": bool(re.search(r"service-notifier", all_text, re.IGNORECASE)),
        "has_wlan_pd_indication": bool(re.search(r"wlan_pd", all_text, re.IGNORECASE)),
        "has_qmi_server_connected": bool(re.search(r"QMI Server Connected", all_text, re.IGNORECASE)),
        "has_bdf_regdb": bool(re.search(r"regdb\.bin", all_text, re.IGNORECASE)),
        "has_bdf_bdwlan": bool(re.search(r"bdwlan\.bin", all_text, re.IGNORECASE)),
        "has_fw_ready": bool(re.search(r"WLAN FW is ready", all_text, re.IGNORECASE)),
        "process_capture_has_sysmon": bool(re.search(r"\bsysmon-qmi\b", process_text, re.IGNORECASE)),
        "process_capture_has_service_notifier": bool(re.search(r"\bservice-notifier\b", process_text, re.IGNORECASE)),
        "process_capture_has_qmiproxy": bool(re.search(r"\bqmiproxy\b", process_text, re.IGNORECASE)),
        "process_capture_has_mainline": bool(re.search(r"\b(rmtfs|pd-mapper|tqftpserv)\b", process_text, re.IGNORECASE)),
    }


def prior_qrtr_summary(v250: dict[str, Any], v270: dict[str, Any], v276: dict[str, Any]) -> dict[str, Any]:
    return {
        "v250": {
            "exists": v250.get("exists") is True and not v250.get("invalid"),
            "path": v250.get("path"),
            "decision": v250.get("decision"),
            "pass": v250.get("pass"),
        },
        "v270": {
            "exists": v270.get("exists") is True and not v270.get("invalid"),
            "path": v270.get("path"),
            "decision": v270.get("decision"),
            "pass": v270.get("pass"),
            "reason": v270.get("reason"),
        },
        "v276": {
            "exists": v276.get("exists") is True and not v276.get("invalid"),
            "path": v276.get("path"),
            "decision": v276.get("decision"),
            "pass": v276.get("pass"),
            "reason": v276.get("reason"),
        },
    }


def build_checks(command: str,
                 v519: dict[str, Any],
                 android: dict[str, Any],
                 inventory: dict[str, Any],
                 qrtr: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    if command == "plan":
        add_check(checks, "plan-only", "pass", "info", "host-only planner; no device command executed", [], "run V520 planner")
        return checks

    add_check(checks, "v519-ready", "pass" if v519.get("decision") == "v519-qrtr-companion-service-gap-classified" and v519.get("pass") is True else "blocked", "blocker",
              f"decision={v519.get('decision')} pass={v519.get('pass')}", [str(v519.get("path"))],
              "run V519 before selecting companion-service path")
    android_sequence = android["has_qrtr_ns_process"] and android["has_sysmon_qmi_dmesg"] and android["has_service_notifier_dmesg"] and android["has_wlan_pd_indication"] and android["has_qmi_server_connected"] and android["has_bdf_bdwlan"] and android["has_fw_ready"]
    add_check(checks, "android-qmi-sequence-present", "pass" if android_sequence else "blocked", "blocker",
              f"qrtr_ns={android['has_qrtr_ns_process']} sysmon={android['has_sysmon_qmi_dmesg']} service_notifier={android['has_service_notifier_dmesg']} wlan_pd={android['has_wlan_pd_indication']} qmi={android['has_qmi_server_connected']} bdf={android['has_bdf_bdwlan']} fw={android['has_fw_ready']}",
              android["qmi_sequence_lines"][:8], "recapture Android boot-complete Wi-Fi/CNSS lifecycle")
    process_gap = not (android["process_capture_has_sysmon"] or android["process_capture_has_service_notifier"] or android["process_capture_has_qmiproxy"] or android["process_capture_has_mainline"])
    add_check(checks, "android-companion-process-coverage", "review" if process_gap else "pass", "warning",
              f"sysmon_proc={android['process_capture_has_sysmon']} service_notifier_proc={android['process_capture_has_service_notifier']} qmiproxy_proc={android['process_capture_has_qmiproxy']} mainline_proc={android['process_capture_has_mainline']}",
              android["companion_lines"][:10], "run widened Android companion recapture before choosing deploy/build path")
    add_check(checks, "local-direct-start-binaries", "pass" if inventory["has_android_vendor_equivalent"] or inventory["has_mainline_set"] else "review", "warning",
              f"vendor_equivalent={inventory['has_android_vendor_equivalent']} mainline_set={inventory['has_mainline_set']} cnss_set={inventory['has_cnss_set']}",
              [json.dumps(root, sort_keys=True) for root in inventory["roots"]],
              "if absent locally, export Android binaries or prepare static companion builds")
    add_check(checks, "prior-qrtr-baseline", "pass" if qrtr["v250"]["decision"] == "qrtr-socket-local-bind-pass" and qrtr["v270"]["decision"] == "qrtr-ns-readback-timeout" and qrtr["v276"]["decision"] == "qrtr-cnss-platform-surface-visible" else "review", "warning",
              f"v250={qrtr['v250']['decision']} v270={qrtr['v270']['decision']} v276={qrtr['v276']['decision']}",
              [str(qrtr["v250"].get("path")), str(qrtr["v270"].get("path")), str(qrtr["v276"].get("path"))],
              "do not send QMI payload until companion surface changes QRTR readback")
    add_check(checks, "qcwlanstate-still-blocked", "pass", "blocker",
              "V519 has no native WLFW/QMI/BDF/FW-ready marker; retry would likely reproduce timeout", [],
              "allow qcwlanstate only after companion-service proof produces WLFW/QMI marker")
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], android: dict[str, Any], inventory: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return "v520-companion-availability-plan-ready", True, "host-only plan; no device command executed", "run V520 planner"
    blockers = blocking(checks)
    if blockers:
        return "v520-companion-availability-blocked", False, "blocked by " + ", ".join(blockers), "refresh required evidence"
    process_gap = not (android["process_capture_has_sysmon"] or android["process_capture_has_service_notifier"] or android["process_capture_has_qmiproxy"] or android["process_capture_has_mainline"])
    if process_gap:
        return (
            "v520-companion-android-recapture-needed",
            True,
            "Android dmesg proves QRTR/QMI/service-notifier/WLAN-PD sequence, but current process/binary captures do not identify the exact companion services or startable paths",
            "boot Android and run widened companion-service recapture; then export or build the proven service set",
        )
    if inventory["has_android_vendor_equivalent"] or inventory["has_mainline_set"]:
        return (
            "v520-companion-startonly-plan-ready",
            True,
            "a startable companion-service candidate set is locally available",
            "design bounded no-scan companion start-only proof before cnss-daemon retry",
        )
    return (
        "v520-companion-build-or-export-needed",
        True,
        "companion model is supported but no local startable binaries are available",
        "export Android binaries if present or build static rmtfs/pd-mapper/tqftpserv candidates",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"], item["next_step"]] for item in checks]
    inv_rows = []
    for name, item in (manifest.get("local_binary_inventory", {}).get("summary") or {}).items():
        inv_rows.append([name, item.get("count"), json.dumps(item.get("paths") or [], ensure_ascii=False, sort_keys=True)])
    cmd_rows = [[item["name"], item["command"]] for item in manifest.get("android_recapture_commands") or []]
    return "\n".join([
        "# V520 Companion-Service Availability Plan",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Android Evidence",
        "",
        markdown_table(["field", "value"], [[key, value] for key, value in manifest["android_surface"].items() if key not in {"inputs", "companion_lines", "qmi_sequence_lines"}]),
        "",
        "## Companion Lines",
        "",
        "\n".join(f"- {line[:260]}" for line in manifest["android_surface"]["companion_lines"][:40]) or "- none",
        "",
        "## QMI Sequence Lines",
        "",
        "\n".join(f"- {line[:260]}" for line in manifest["android_surface"]["qmi_sequence_lines"][:40]) or "- none",
        "",
        "## Local Binary Inventory",
        "",
        markdown_table(["name", "count", "paths"], inv_rows),
        "",
        "## Android Recapture Commands",
        "",
        markdown_table(["name", "command"], cmd_rows),
        "",
        "## Source References",
        "",
        *[f"- {item}" for item in manifest["source_references"]],
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    if args.command == "run":
        store.mkdir("inputs")
    v519 = load_json(args.v519_manifest)
    v250 = load_json(args.v250_manifest)
    v270 = load_json(args.v270_long_manifest)
    v276 = load_json(args.v276_manifest)
    android = android_surface(args, store, args.command)
    inventory = binary_inventory(roots(args))
    qrtr = prior_qrtr_summary(v250, v270, v276)
    checks = build_checks(args.command, v519, android, inventory, qrtr)
    decision, pass_ok, reason, next_step = decide(args.command, checks, android, inventory)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "v519": {
            "exists": v519.get("exists"),
            "path": v519.get("path"),
            "decision": v519.get("decision"),
            "pass": v519.get("pass"),
            "reason": v519.get("reason"),
        },
        "android_surface": android,
        "local_binary_inventory": inventory,
        "prior_qrtr": qrtr,
        "checks": [asdict(check) for check in checks],
        "android_recapture_commands": [
            {"name": name, "command": command}
            for name, command in ANDROID_RECAPTURE_COMMANDS
        ],
        "source_references": list(SOURCE_REFERENCES),
        "device_commands_executed": False,
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
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
