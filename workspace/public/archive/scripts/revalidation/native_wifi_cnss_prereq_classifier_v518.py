#!/usr/bin/env python3
"""V518 read-only classifier for remaining CNSS readiness prerequisites."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v518-cnss-prereq-classifier")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_V517_MANIFEST = Path("tmp/wifi/v517-cnss-userspace-private-data-wifi/manifest.json")
DEFAULT_CNSS_DAEMON = Path("tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon")
TOYBOX = "/cache/bin/toybox"
PROCESS_RE = re.compile(r"\b(cnss-daemon|cnss_diag|wificond|supplicant|hostapd|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi)\b", re.IGNORECASE)
WIFI_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wifi-aware\d*|wiphy\d*|phy\d+)\b", re.IGNORECASE)

READ_ONLY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 15.0),
    ("status", ["status"], 20.0),
    ("selftest", ["selftest"], 20.0),
    ("ps", ["run", TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
    ("proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
    ("sys-class-net", ["ls", "/sys/class/net"], 10.0),
    ("proc-net-protocols", ["cat", "/proc/net/protocols"], 10.0),
    ("proc-net-qrtr", ["cat", "/proc/net/qrtr"], 10.0),
    ("stat-dev-qrtr", ["stat", "/dev/qrtr"], 10.0),
    ("stat-dev-diag", ["stat", "/dev/diag"], 10.0),
    ("stat-dev-wlan", ["stat", "/dev/wlan"], 10.0),
    ("stat-property-socket", ["stat", "/dev/socket/property_service"], 10.0),
    ("stat-property-area", ["stat", "/dev/__properties__"], 10.0),
    ("stat-perfd-socket", ["stat", "/dev/socket/perfd"], 10.0),
    ("stat-vendor-perfd", ["stat", "/mnt/system/vendor/bin/perfd"], 10.0),
    ("stat-system-vendor-perfd", ["stat", "/mnt/system/system/vendor/bin/perfd"], 10.0),
    ("find-perfd", ["run", TOYBOX, "find", "/mnt/system", "-maxdepth", "8", "-name", "*perfd*"], 30.0),
    ("find-qmi", ["run", TOYBOX, "find", "/mnt/system", "-maxdepth", "8", "-name", "*qmi*"], 30.0),
    ("find-qrtr", ["run", TOYBOX, "find", "/mnt/system", "-maxdepth", "8", "-name", "*qrtr*"], 30.0),
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
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v517-manifest", type=Path, default=DEFAULT_V517_MANIFEST)
    parser.add_argument("--cnss-daemon", type=Path, default=DEFAULT_CNSS_DAEMON)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {"exists": True, "path": str(resolved), "invalid": True}


def run_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    records = []
    store.mkdir("native")
    for name, command, timeout in READ_ONLY_COMMANDS:
        capture = run_capture(args, name, command, timeout=timeout)
        text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
        rel = f"native/{safe_name(name)}.txt"
        store.write_text(rel, text)
        item = capture_to_manifest(capture)
        item["file"] = rel
        item["payload"] = text
        records.append(item)
    return records


def by_name(steps: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(step.get("name")): step for step in steps}


def payload(steps: dict[str, dict[str, Any]], name: str) -> str:
    return str(steps.get(name, {}).get("payload") or "")


def ok(steps: dict[str, dict[str, Any]], name: str) -> bool:
    item = steps.get(name, {})
    return item.get("rc") == 0 and item.get("status") == "ok"


def host_strings(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    info: dict[str, Any] = {
        "path": str(resolved),
        "exists": resolved.exists(),
        "perfd_refs": [],
        "property_refs": [],
        "socket_refs": [],
        "qmi_wlfw_refs": [],
    }
    if not resolved.exists():
        return info
    result = subprocess.run(
        ["strings", "-a", str(resolved)],
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=20,
    )
    lines = result.stdout.splitlines()
    info["perfd_refs"] = [line for line in lines if "perfd" in line.lower() or "perf" in line.lower()][:80]
    info["property_refs"] = [line for line in lines if "property" in line.lower() or line.startswith(("ro.", "persist.", "vendor."))][:80]
    info["socket_refs"] = [line for line in lines if "socket" in line.lower() or "/data/vendor/wifi" in line][:80]
    info["qmi_wlfw_refs"] = [line for line in lines if "qmi" in line.lower() or "wlfw" in line.lower()][:120]
    return info


def v517_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    live = manifest.get("live_result") if isinstance(manifest.get("live_result"), dict) else {}
    keys = live.get("keys") if isinstance(live.get("keys"), dict) else {}
    dmesg = manifest.get("dmesg_summary") if isinstance(manifest.get("dmesg_summary"), dict) else {}
    return {
        "exists": bool(manifest) and not manifest.get("invalid") and manifest.get("path") is None,
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "reason": manifest.get("reason"),
        "helper_result": live.get("helper_result"),
        "all_postflight_safe": live.get("all_postflight_safe"),
        "data_wifi_mode_private": "private /data/vendor/wifi/sockets was present" in str(manifest.get("reason")),
        "no_fail_bind_user_socket": "Fail to bind user socket" not in json.dumps(live, ensure_ascii=False),
        "perfd_warning": "Failed to become a perfd client" in json.dumps(live, ensure_ascii=False),
        "readiness_markers": dmesg.get("readiness_markers") or [],
        "qcwlanstate_write": keys.get("cnss_userspace_readiness.qcwlanstate_write"),
        "scan_connect_linkup": keys.get("cnss_userspace_readiness.scan_connect_linkup"),
        "external_ping": keys.get("cnss_userspace_readiness.external_ping"),
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_runtime_surface(steps: dict[str, dict[str, Any]]) -> dict[str, Any]:
    protocols = payload(steps, "proc-net-protocols")
    ps = payload(steps, "ps")
    netdev = payload(steps, "proc-net-dev") + "\n" + payload(steps, "sys-class-net")
    find_perfd = payload(steps, "find-perfd")
    find_qmi = payload(steps, "find-qmi")
    find_qrtr = payload(steps, "find-qrtr")
    return {
        "qipcrtr_protocol_present": bool(re.search(r"^QIPCRTR\s", protocols, re.MULTILINE)),
        "proc_net_qrtr_present": ok(steps, "proc-net-qrtr"),
        "dev_qrtr_present": ok(steps, "stat-dev-qrtr"),
        "dev_diag_present": ok(steps, "stat-dev-diag"),
        "dev_wlan_present": ok(steps, "stat-dev-wlan"),
        "property_socket_present": ok(steps, "stat-property-socket"),
        "property_area_present": ok(steps, "stat-property-area"),
        "perfd_socket_present": ok(steps, "stat-perfd-socket"),
        "perfd_binary_present": ok(steps, "stat-vendor-perfd") or ok(steps, "stat-system-vendor-perfd"),
        "perfd_paths": [line for line in find_perfd.splitlines() if line.startswith("/mnt/system/")][:80],
        "qmi_paths": [line for line in find_qmi.splitlines() if line.startswith("/mnt/system/")][:80],
        "qrtr_paths": [line for line in find_qrtr.splitlines() if line.startswith("/mnt/system/")][:80],
        "process_hits": [line.strip() for line in ps.splitlines() if PROCESS_RE.search(line)],
        "wifi_hits": [line.strip() for line in netdev.splitlines() if WIFI_RE.search(line)],
    }


def build_checks(args: argparse.Namespace,
                 steps: dict[str, dict[str, Any]],
                 surface: dict[str, Any],
                 v517: dict[str, Any],
                 strings_info: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    status = payload(steps, "status")
    selftest = payload(steps, "selftest")
    version = payload(steps, "version")
    add_check(checks, "native-clean", "pass" if args.expect_version in version and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker", f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:2], "restore native baseline")
    add_check(checks, "v517-gap-current", "pass" if v517.get("decision") == "v517-cnss-userspace-readiness-no-fw-marker" and v517.get("pass") is True else "blocked", "blocker", f"decision={v517.get('decision')} pass={v517.get('pass')}", [str(args.v517_manifest)], "run V517 first")
    add_check(checks, "data-wifi-user-socket-gap-closed", "pass" if v517.get("data_wifi_mode_private") and v517.get("no_fail_bind_user_socket") else "blocked", "blocker", f"private_data={v517.get('data_wifi_mode_private')} fail_bind_absent={v517.get('no_fail_bind_user_socket')}", [], "fix private data Wi-Fi namespace before retry")
    add_check(checks, "no-active-wifi-processes", "pass" if not surface["process_hits"] else "blocked", "blocker", f"process_hits={len(surface['process_hits'])}", surface["process_hits"][:8], "cleanup residual process before next live action")
    add_check(checks, "no-wifi-link-surface", "pass" if not surface["wifi_hits"] else "blocked", "blocker", f"wifi_hits={len(surface['wifi_hits'])}", surface["wifi_hits"][:8], "if wlan exists, move to scan-only gate")
    add_check(checks, "qipcrtr-surface", "pass" if surface["qipcrtr_protocol_present"] else "warn", "warning", f"protocol={surface['qipcrtr_protocol_present']} proc_net_qrtr={surface['proc_net_qrtr_present']} dev_qrtr={surface['dev_qrtr_present']}", [], "classify QRTR before QMI/WLFW retry if missing")
    add_check(checks, "perfd-warning-classified", "pass", "warning", f"v517_perfd_warning={v517.get('perfd_warning')} binary={surface['perfd_binary_present']} socket={surface['perfd_socket_present']} paths={len(surface['perfd_paths'])}", surface["perfd_paths"][:6], "treat as nonfatal unless next evidence contradicts it")
    add_check(checks, "property-runtime-classified", "pass", "warning", f"socket={surface['property_socket_present']} area={surface['property_area_present']} string_refs={len(strings_info.get('property_refs') or [])}", (strings_info.get("property_refs") or [])[:6], "use private property root only when a property-dependent blocker is proven")
    add_check(checks, "cnss-daemon-strings-visible", "pass" if strings_info["exists"] else "warn", "warning", f"path={strings_info['path']} qmi_wlfw_refs={len(strings_info.get('qmi_wlfw_refs') or [])}", (strings_info.get("qmi_wlfw_refs") or [])[:8], "refresh vendor export if missing")
    return checks


def classify(checks: list[Check], surface: dict[str, Any], v517: dict[str, Any]) -> tuple[str, bool, str, str]:
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return "v518-cnss-prereq-blocked", False, "blocked by " + ", ".join(blockers), "resolve blockers before another live action"
    if not surface["qipcrtr_protocol_present"]:
        return "v518-cnss-prereq-qrtr-missing", True, "data Wi-Fi gap is closed, but QIPCRTR protocol surface is not visible", "restore QRTR/modem surface before qcwlanstate retry"
    if v517.get("readiness_markers"):
        return "v518-cnss-prereq-stale", False, "V517 already has readiness markers; this classifier is stale", "move directly to scan-only gate"
    return "v518-cnss-prereq-classified", True, "data Wi-Fi user socket gap closed; QMI/WLFW still absent, so the next gate is read-only QRTR/modem/perfd/property delta", "compare Android/native QRTR modem, perfd, and property runtime before any qcwlanstate retry"


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"], item["next_step"]] for item in manifest["checks"]]
    surface_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)] for key, value in manifest["runtime_surface"].items()]
    return "\n".join([
        "# V518 CNSS Prerequisite Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "- daemon_start_executed: `False`",
        "- wifi_bringup_executed: `False`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Runtime Surface",
        "",
        markdown_table(["key", "value"], surface_rows),
        "",
        "## Evidence",
        "",
        f"- `{manifest['out_dir']}`",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps = [] if args.command == "plan" else run_steps(args, store)
    step_map = by_name(steps)
    v517 = v517_summary(load_json(args.v517_manifest))
    strings_info = host_strings(args.cnss_daemon)
    surface = build_runtime_surface(step_map) if steps else {
        "qipcrtr_protocol_present": False,
        "proc_net_qrtr_present": False,
        "dev_qrtr_present": False,
        "dev_diag_present": False,
        "dev_wlan_present": False,
        "property_socket_present": False,
        "property_area_present": False,
        "perfd_socket_present": False,
        "perfd_binary_present": False,
        "perfd_paths": [],
        "qmi_paths": [],
        "qrtr_paths": [],
        "process_hits": [],
        "wifi_hits": [],
    }
    checks = [Check("plan-only", "pass", "info", "no device command executed", [], "run V518 read-only classifier")] if args.command == "plan" else build_checks(args, step_map, surface, v517, strings_info)
    decision, pass_ok, reason, next_step = ("v518-cnss-prereq-plan-ready", True, "plan-only; no device command executed", "run V518 read-only classifier") if args.command == "plan" else classify(checks, surface, v517)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "steps": steps,
        "checks": [asdict(check) for check in checks],
        "runtime_surface": surface,
        "v517_summary": v517,
        "cnss_daemon_strings": strings_info,
        "device_commands_executed": args.command != "plan",
        "device_mutations": False,
        "daemon_start_executed": False,
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
