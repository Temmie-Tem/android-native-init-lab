#!/usr/bin/env python3
"""V580 read-only postflight and ICNSS blocker classifier.

This classifier consumes the V579 companion+driver-state evidence, then captures
current read-only device state. It does not start daemons, write qcwlanstate,
scan, connect, change routes, or ping externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v580-v579-postflight-icnss")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_WLANBOOTCTL = "/cache/bin/a90_wlanbootctl"
DEFAULT_V579_MANIFEST = Path("tmp/wifi/v579-v95-companion-driver-state/manifest.json")
DEFAULT_V514_MANIFEST = Path("tmp/wifi/v579-v514-current-readback/manifest.json")
SOURCE_REFERENCES = (
    "https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c",
)

KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TARGET_PROCESS_RE = re.compile(
    r"\b(servicemanager|hwservicemanager|vndservicemanager|wificond|wpa_supplicant|hostapd|"
    r"cnss-daemon|cnss_diag|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi|"
    r"qrtr-ns|rmt_storage|tftp_server|pd-mapper)\b",
    re.IGNORECASE,
)
WIFI_LINK_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wifi-aware\d*|phy\d+|wiphy\d*)\b", re.IGNORECASE)
DMESG_PATTERNS = {
    "wifi_turning_on": re.compile(r"Wifi Turning On from UI", re.IGNORECASE),
    "modules_not_initialized": re.compile(r"Modules not initialized just return", re.IGNORECASE),
    "timed_out": re.compile(r"Timed-out|Timed-out waiting", re.IGNORECASE),
    "driver_loaded": re.compile(r"wlan: driver loaded", re.IGNORECASE),
    "driver_load_failure": re.compile(r"driver load failure|wlan driver initialization failed|hdd_init failed", re.IGNORECASE),
    "cnss_netlink": re.compile(r"\b(cnss-daemon|cnss_diag)\b.*\b(cld80211|netlink_create|ctrl_getfamily)\b", re.IGNORECASE),
    "qmi_server_connected": re.compile(r"QMI Server Connected", re.IGNORECASE),
    "bdf_regdb": re.compile(r"\b(regdb\.bin|bdf_regdb)\b", re.IGNORECASE),
    "bdf_bdwlan": re.compile(r"\b(bdwlan\.bin|bdf_bdwlan)\b", re.IGNORECASE),
    "wlan_fw_ready": re.compile(r"WLAN FW is ready|FW ready event received|wma_wait_for_ready_event", re.IGNORECASE),
    "wlan0_event": re.compile(r"\bwlan0\b", re.IGNORECASE),
}


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
    parser.add_argument("--wlanbootctl", default=DEFAULT_WLANBOOTCTL)
    parser.add_argument("--v579-manifest", type=Path, default=DEFAULT_V579_MANIFEST)
    parser.add_argument("--v514-manifest", type=Path, default=DEFAULT_V514_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"))
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def load_manifest(path: Path) -> dict[str, Any]:
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


def parse_key_values(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def dmesg_summary(text: str) -> dict[str, Any]:
    lines = [strip_ansi(line).strip() for line in text.splitlines() if line.strip()]
    events: dict[str, list[str]] = {name: [] for name in DMESG_PATTERNS}
    for line in lines:
        for name, pattern in DMESG_PATTERNS.items():
            if pattern.search(line):
                events[name].append(line)
    counts = {name: len(items) for name, items in events.items()}
    return {
        "counts": counts,
        "latest": {name: items[-1] if items else "" for name, items in events.items()},
        "focus_tail": [line for items in events.values() for line in items][-120:],
    }


def v579_key(v579: dict[str, Any], name: str, default: str = "") -> str:
    live = v579.get("live_result") if isinstance(v579.get("live_result"), dict) else {}
    keys = live.get("keys") if isinstance(live.get("keys"), dict) else {}
    value = keys.get(name)
    return str(value) if value is not None else default


def v579_live(v579: dict[str, Any], name: str, default: Any = None) -> Any:
    live = v579.get("live_result") if isinstance(v579.get("live_result"), dict) else {}
    return live.get(name, default)


def v579_summary(v579: dict[str, Any]) -> dict[str, Any]:
    return {
        "exists": bool(v579.get("exists")) and not v579.get("invalid"),
        "path": v579.get("path"),
        "decision": v579.get("decision"),
        "pass": v579.get("pass"),
        "reason": v579.get("reason"),
        "all_postflight_safe": v579_live(v579, "all_postflight_safe"),
        "driver_state_on": v579_live(v579, "driver_state_on"),
        "driver_state_write_executed": v579_live(v579, "driver_state_write_executed"),
        "driver_state_write_rc": v579_live(v579, "driver_state_write_rc"),
        "driver_state_write_errno": v579_live(v579, "driver_state_write_errno"),
        "driver_state_write_duration_ms": v579_live(v579, "driver_state_write_duration_ms"),
        "iwifi_start": f"{v579_live(v579, 'iwifi_start_wifi_status_name', '')}/{v579_live(v579, 'iwifi_start_wifi_status_code', '')}",
        "qipcrtr_sockets_window": v579_live(v579, "qipcrtr_sockets_window"),
        "qrtr_readback_qmi_attempted": v579_live(v579, "qrtr_readback_qmi_attempted"),
        "qrtr_readback_service_events": v579_live(v579, "qrtr_readback_service_events"),
        "wlan_count_window": v579_live(v579, "wlan_count_window"),
        "phy_count_window": v579_live(v579, "phy_count_window"),
        "scan_connect_linkup": v579_live(v579, "scan_connect_linkup"),
        "external_ping": v579_live(v579, "external_ping"),
        "legacy_postflight_safe": v579_key(v579, "wifi_companion_hal_order.child.wifi_hal_legacy.postflight_safe"),
        "legacy_reaped": v579_key(v579, "wifi_companion_hal_order.child.wifi_hal_legacy.reaped"),
        "legacy_kill_sent": v579_key(v579, "wifi_companion_hal_order.child.wifi_hal_legacy.kill_sent"),
        "legacy_signal": v579_key(v579, "wifi_companion_hal_order.child.wifi_hal_legacy.signal"),
    }


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("native")
    return [
        run_step(args, store, "version", ["version"], 15.0),
        run_step(args, store, "status", ["status"], 25.0),
        run_step(args, store, "selftest", ["selftest"], 25.0),
        run_step(args, store, "wlanboot-status", ["run", args.wlanbootctl, "status"], 25.0),
        run_step(args, store, "ps", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 25.0),
        run_step(args, store, "sys-class-net", ["ls", "/sys/class/net"], 10.0),
        run_step(args, store, "sys-class-ieee80211", ["ls", "/sys/class/ieee80211"], 10.0),
        run_step(args, store, "proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
        run_step(args, store, "proc-net-qrtr", ["cat", "/proc/net/qrtr"], 10.0),
        run_step(args, store, "dmesg", ["run", args.toybox, "dmesg"], 60.0),
    ]


def target_process_lines(ps_text: str) -> list[str]:
    lines = []
    for line in ps_text.splitlines():
        cleaned = line.strip()
        if cleaned and TARGET_PROCESS_RE.search(cleaned):
            lines.append(cleaned)
    return lines


def wifi_link_lines(*texts: str) -> list[str]:
    lines = []
    for text in texts:
        for line in text.splitlines():
            cleaned = line.strip()
            if cleaned and WIFI_LINK_RE.search(cleaned):
                lines.append(cleaned)
    return lines


def parse_status_reaper(status_text: str) -> dict[str, str]:
    reaper = {}
    for line in status_text.splitlines():
        if not line.startswith("reaper:"):
            continue
        for token in line.split():
            if "=" in token:
                name, value = token.split("=", 1)
                reaper[name] = value
    return reaper


def current_surface(steps: list[dict[str, Any]]) -> dict[str, Any]:
    status_text = step_payload(steps, "status")
    selftest_text = step_payload(steps, "selftest")
    ps_text = step_payload(steps, "ps")
    wlan_text = step_payload(steps, "wlanboot-status")
    sys_net = step_payload(steps, "sys-class-net")
    sys_ieee = step_payload(steps, "sys-class-ieee80211")
    proc_net_dev = step_payload(steps, "proc-net-dev")
    proc_net_qrtr = step_payload(steps, "proc-net-qrtr")
    wlan_keys = parse_key_values(wlan_text)
    targets = target_process_lines(ps_text)
    links = wifi_link_lines(sys_net, sys_ieee, proc_net_dev)
    return {
        "native_healthy": "fail=0" in status_text and "fail=0" in selftest_text,
        "reaper": parse_status_reaper(status_text),
        "target_processes": targets,
        "target_process_count": len(targets),
        "wifi_links": links,
        "wifi_link_count": len(links),
        "qcwlanstate": wlan_keys.get("wlanboot.status.qcwlanstate.value", ""),
        "dev_wlan_exists": wlan_keys.get("wlanboot.status.dev_wlan.exists") == "1",
        "dev_wlan_type": wlan_keys.get("wlanboot.status.dev_wlan.type", ""),
        "dev_wlan_major_minor": f"{wlan_keys.get('wlanboot.status.dev_wlan.major', '')}:{wlan_keys.get('wlanboot.status.dev_wlan.minor', '')}",
        "wlan0_exists": wlan_keys.get("wlanboot.status.sys_class_net_wlan0.exists") == "1",
        "ieee80211_count": int(wlan_keys.get("wlanboot.status.sys_class_ieee80211.count", "0") or 0),
        "proc_net_qrtr_present": "No such file" not in proc_net_qrtr and "No such file or directory" not in proc_net_qrtr and bool(proc_net_qrtr.strip()),
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
                 v579: dict[str, Any],
                 v514: dict[str, Any],
                 surface: dict[str, Any],
                 dmesg: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run V580 read-only classifier")
        return checks

    counts = dmesg.get("counts") or {}
    reaper = surface.get("reaper") or {}
    v579_ok = v579["exists"] and v579["decision"] == "v579-driver-state-cleanup-review"
    guard_clean = not v579["scan_connect_linkup"] and not v579["external_ping"] and int(v579["qrtr_readback_qmi_attempted"] or 0) == 0
    write_einval = (
        v579["driver_state_write_executed"] is True and
        str(v579["driver_state_write_rc"]) == "1" and
        str(v579["driver_state_write_errno"]) == "22"
    )
    icnss_pattern = (
        write_einval and
        int(counts.get("modules_not_initialized", 0)) > 0 and
        int(counts.get("driver_loaded", 0)) == 0 and
        int(counts.get("qmi_server_connected", 0)) == 0 and
        int(counts.get("wlan_fw_ready", 0)) == 0
    )

    add_check(
        checks,
        "v579-evidence-ready",
        "pass" if v579_ok else "blocked",
        "blocker",
        f"decision={v579['decision']} pass={v579['pass']} reason={v579['reason']}",
        [str(v579.get("path"))],
        "run V579 before postflight classification",
    )
    add_check(
        checks,
        "v579-guard-clean",
        "pass" if guard_clean else "blocked",
        "blocker",
        f"scan_connect={v579['scan_connect_linkup']} external_ping={v579['external_ping']} qmi_attempted={v579['qrtr_readback_qmi_attempted']}",
        [],
        "stop Wi-Fi live work and inspect guard failure",
    )
    add_check(
        checks,
        "native-current-health",
        "pass" if surface["native_healthy"] else "blocked",
        "blocker",
        f"native_healthy={surface['native_healthy']}",
        [],
        "restore native baseline before more Wi-Fi work",
    )
    add_check(
        checks,
        "delayed-postflight-process-clean",
        "pass" if surface["target_process_count"] == 0 else "blocked",
        "blocker",
        f"target_process_count={surface['target_process_count']} reaper_last_pid={reaper.get('last_pid', '')} reaper_last={reaper.get('last', '')}",
        surface["target_processes"][:12],
        "cleanup residual helper-owned Wi-Fi processes before further live work",
    )
    add_check(
        checks,
        "v579-helper-cleanup-false-explained",
        "pass" if v579["all_postflight_safe"] is False and surface["target_process_count"] == 0 else "warn",
        "warning",
        f"v579_all_postflight_safe={v579['all_postflight_safe']} legacy_reaped={v579['legacy_reaped']} current_targets={surface['target_process_count']}",
        [f"legacy_postflight_safe={v579['legacy_postflight_safe']}", f"legacy_kill_sent={v579['legacy_kill_sent']}", f"legacy_signal={v579['legacy_signal']}"],
        "tighten helper delayed-reap accounting in a future helper if needed",
    )
    add_check(
        checks,
        "dev-wlan-still-materialized",
        "pass" if surface["dev_wlan_exists"] and surface["dev_wlan_type"] == "char" else "blocked",
        "blocker",
        f"dev_wlan={surface['dev_wlan_exists']} type={surface['dev_wlan_type']} rdev={surface['dev_wlan_major_minor']} qcwlanstate={surface['qcwlanstate']}",
        [],
        "re-run V509 before any future driver-state proof",
    )
    add_check(
        checks,
        "no-wifi-link-surface",
        "pass" if surface["wifi_link_count"] == 0 and not surface["wlan0_exists"] and surface["ieee80211_count"] == 0 else "blocked",
        "blocker",
        f"link_count={surface['wifi_link_count']} wlan0={surface['wlan0_exists']} ieee80211={surface['ieee80211_count']}",
        surface["wifi_links"][:12],
        "if WLAN surface appears, switch to scan-only gate",
    )
    add_check(
        checks,
        "icnss-module-init-blocker",
        "pass" if icnss_pattern else "blocked",
        "blocker",
        f"write_einval={write_einval} modules_not_initialized={counts.get('modules_not_initialized', 0)} driver_loaded={counts.get('driver_loaded', 0)} qmi={counts.get('qmi_server_connected', 0)} fw_ready={counts.get('wlan_fw_ready', 0)}",
        [dmesg.get("latest", {}).get("modules_not_initialized", ""), dmesg.get("latest", {}).get("wifi_turning_on", "")],
        "compare Android ICNSS module-init ordering before another driver-state retry",
    )
    add_check(
        checks,
        "v514-consistent",
        "pass" if v514.get("decision") == "v514-wlan-module-init-timeout-classified" else "warn",
        "warning",
        f"decision={v514.get('decision')} pass={v514.get('pass')}",
        [str(v514.get("path"))],
        "refresh V514 if this classifier disagrees",
    )
    return checks


def blocking_checks(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], v579: dict[str, Any], surface: dict[str, Any], dmesg: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return "v580-postflight-icnss-plan-ready", True, "plan-only; no device command executed", "run V580 read-only classifier"
    blockers = blocking_checks(checks)
    if blockers:
        return "v580-postflight-icnss-blocked", False, "blocked by " + ", ".join(blockers), "resolve blockers before more live Wi-Fi work"
    counts = dmesg.get("counts") or {}
    if (
        v579["all_postflight_safe"] is False and
        surface["target_process_count"] == 0 and
        str(v579["driver_state_write_errno"]) == "22" and
        int(counts.get("modules_not_initialized", 0)) > 0
    ):
        return (
            "v580-delayed-clean-icnss-module-init-blocker-confirmed",
            True,
            "V579 helper cleanup false is explained by delayed reaping; the stable blocker is qcwlanstate EINVAL with ICNSS modules-not-initialized",
            "build V581 Android-vs-native ICNSS module-init ordering comparator before any more driver-state or IWifi.start retries",
        )
    return (
        "v580-postflight-icnss-review",
        True,
        "read-only postflight captured but did not match the canonical V579 ICNSS blocker pattern",
        "inspect V580 dmesg/process evidence before deciding the next live gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    v579 = manifest.get("v579_summary") or {}
    v579_rows = [[key, value] for key, value in v579.items() if key not in {"path"}]
    surface = manifest.get("current_surface") or {}
    surface_rows = [
        ["native_healthy", surface.get("native_healthy", "")],
        ["target_process_count", surface.get("target_process_count", "")],
        ["reaper", surface.get("reaper", "")],
        ["dev_wlan", f"{surface.get('dev_wlan_type', '')} {surface.get('dev_wlan_major_minor', '')}"],
        ["qcwlanstate", surface.get("qcwlanstate", "")],
        ["wifi_link_count", surface.get("wifi_link_count", "")],
        ["proc_net_qrtr_present", surface.get("proc_net_qrtr_present", "")],
    ]
    counts = (manifest.get("dmesg_summary") or {}).get("counts") or {}
    count_rows = [[key, value] for key, value in sorted(counts.items())]
    focus = (manifest.get("dmesg_summary") or {}).get("focus_tail") or []
    return "\n".join([
        "# V580 V579 Postflight ICNSS Classifier",
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
        markdown_table(["name", "status", "severity", "detail", "next"], rows),
        "",
        "## V579 Evidence Summary",
        "",
        markdown_table(["key", "value"], v579_rows),
        "",
        "## Current Surface",
        "",
        markdown_table(["key", "value"], surface_rows),
        "",
        "## Dmesg Pattern Counts",
        "",
        markdown_table(["pattern", "count"], count_rows) if count_rows else "- none",
        "",
        "## Dmesg Focus Tail",
        "",
        "\n".join(f"- `{line[:220]}`" for line in focus[-32:]) if focus else "- none",
        "",
        "## Source References",
        "",
        *[f"- {item}" for item in manifest["source_references"]],
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v579 = v579_summary(load_manifest(args.v579_manifest))
    v514 = load_manifest(args.v514_manifest)
    steps: list[dict[str, Any]] = []
    surface: dict[str, Any] = {}
    dmesg: dict[str, Any] = dmesg_summary("")
    if args.command == "run":
        steps = collect_steps(args, store)
        surface = current_surface(steps)
        dmesg = dmesg_summary(step_payload(steps, "dmesg"))
    checks = build_checks(args, v579, v514, surface, dmesg)
    decision, pass_ok, reason, next_step = decide(args.command, checks, v579, surface, dmesg)
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
        "v579_summary": v579,
        "v514_manifest": {
            "exists": v514.get("exists"),
            "path": v514.get("path"),
            "decision": v514.get("decision"),
            "pass": v514.get("pass"),
            "reason": v514.get("reason"),
        },
        "current_surface": surface,
        "dmesg_summary": dmesg,
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
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
