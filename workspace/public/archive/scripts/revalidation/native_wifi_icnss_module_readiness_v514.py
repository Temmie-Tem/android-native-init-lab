#!/usr/bin/env python3
"""V514 read-only ICNSS/WLAN module-readiness classifier.

This tool does not start daemons, write qcwlanstate, write boot_wlan, scan,
connect, request DHCP, change routes, or ping externally. It classifies the
current native-init Wi-Fi blocker from read-only device state plus the latest
V513 evidence bundle.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v514-icnss-module-readiness")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_WLANBOOTCTL = "/cache/bin/a90_wlanbootctl"
DEFAULT_V513_MANIFEST = Path("tmp/wifi/v513-dual-hal-driver-state-on/manifest.json")
SOURCE_REFERENCES = (
    "https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c",
)
KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
DMESG_TS_RE = re.compile(r"\[\s*(?P<time>[0-9]+(?:\.[0-9]+)?)\]")
WIFI_PROCESS_RE = re.compile(
    r"\b(servicemanager|hwservicemanager|vndservicemanager|wificond|supplicant|hostapd|"
    r"cnss-daemon|cnss_diag|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi)\b",
    re.IGNORECASE,
)
WIFI_LINK_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wifi-aware\d*|wiphy\d*|phy\d+)\b", re.IGNORECASE)
DMESG_PATTERNS = {
    "loading_driver": re.compile(r"wlan: Loading driver", re.IGNORECASE),
    "state_initialized": re.compile(r"wlan_hdd_state .* initialized", re.IGNORECASE),
    "driver_loaded": re.compile(r"wlan: driver loaded", re.IGNORECASE),
    "driver_load_failure": re.compile(r"driver load failure|wlan driver initialization failed|hdd_init failed", re.IGNORECASE),
    "wifi_turning_on": re.compile(r"Wifi Turning On from UI", re.IGNORECASE),
    "timed_out": re.compile(r"Timed-out!!", re.IGNORECASE),
    "modules_not_initialized": re.compile(r"Modules not initialized just return", re.IGNORECASE),
    "cnss_daemon_netlink": re.compile(r"cnss-daemon.*(ctrl_getfamily|netlink_create|cld80211)", re.IGNORECASE),
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
    parser.add_argument("--v513-manifest", type=Path, default=DEFAULT_V513_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"))
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


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


def dmesg_time(line: str) -> float | None:
    match = DMESG_TS_RE.search(line)
    if not match:
        return None
    try:
        return float(match.group("time"))
    except ValueError:
        return None


def dmesg_pattern_summary(text: str) -> dict[str, Any]:
    lines = [strip_ansi(line).strip() for line in text.splitlines() if line.strip()]
    events: dict[str, list[dict[str, Any]]] = {name: [] for name in DMESG_PATTERNS}
    focus: list[str] = []
    for index, line in enumerate(lines):
        matched = False
        for name, pattern in DMESG_PATTERNS.items():
            if pattern.search(line):
                events[name].append({"index": index, "time": dmesg_time(line), "line": line})
                matched = True
        if matched:
            focus.append(line)
    counts = {name: len(items) for name, items in events.items()}
    latest = {name: (items[-1] if items else None) for name, items in events.items()}
    return {
        "counts": counts,
        "latest": latest,
        "focus_tail": focus[-160:],
        "has_loading_driver": counts["loading_driver"] > 0,
        "has_state_initialized": counts["state_initialized"] > 0,
        "has_driver_loaded": counts["driver_loaded"] > 0,
        "has_driver_load_failure": counts["driver_load_failure"] > 0,
        "has_wifi_turning_on": counts["wifi_turning_on"] > 0,
        "has_timed_out": counts["timed_out"] > 0,
        "has_modules_not_initialized": counts["modules_not_initialized"] > 0,
        "has_cnss_daemon_netlink": counts["cnss_daemon_netlink"] > 0,
    }


def load_v513_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    live = data.get("live_result") if isinstance(data, dict) else {}
    keys = live.get("keys") if isinstance(live, dict) else {}
    return {
        "exists": True,
        "path": str(resolved),
        "decision": data.get("decision"),
        "pass": data.get("pass"),
        "reason": data.get("reason"),
        "write_executed": keys.get("wifi_hal_composite_start.wlan_driver_state_on.executed") == "1",
        "write_rc": keys.get("wifi_hal_composite_start.wlan_driver_state_on.write_rc"),
        "write_errno": keys.get("wifi_hal_composite_start.wlan_driver_state_on.write_errno"),
        "wlan_count": keys.get("wifi_surface_composite.during.wlan_count"),
        "phy_count": keys.get("wifi_surface_composite.during.phy_count"),
        "micro_result": keys.get("wifi_hal_micro_query.result"),
    }


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("native")
    return [
        run_step(args, store, "version", ["version"], 15.0),
        run_step(args, store, "status", ["status"], 25.0),
        run_step(args, store, "selftest", ["selftest"], 25.0),
        run_step(args, store, "netservice-status", ["netservice", "status"], 15.0),
        run_step(args, store, "wlanboot-status", ["run", args.wlanbootctl, "status"], 25.0),
        run_step(args, store, "ps", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 25.0),
        run_step(args, store, "sys-class-net", ["ls", "/sys/class/net"], 10.0),
        run_step(args, store, "sys-class-ieee80211", ["ls", "/sys/class/ieee80211"], 10.0),
        run_step(args, store, "proc-devices", ["cat", "/proc/devices"], 10.0),
        run_step(args, store, "proc-net-wireless", ["cat", "/proc/net/wireless"], 10.0),
        run_step(args, store, "wlan-con-mode", ["cat", "/sys/module/wlan/parameters/con_mode"], 10.0),
        run_step(args, store, "wlan-fwpath", ["cat", "/sys/module/wlan/parameters/fwpath"], 10.0),
        run_step(args, store, "firmware-class-path", ["cat", "/sys/module/firmware_class/parameters/path"], 10.0),
        run_step(args, store, "icnss-uevent", ["cat", "/sys/devices/platform/soc/18800000.qcom,icnss/uevent"], 10.0),
        run_step(args, store, "icnss-driver-dir", ["ls", "/sys/bus/platform/drivers/icnss"], 10.0),
        run_step(args, store, "icnss-power-control", ["cat", "/sys/devices/platform/soc/18800000.qcom,icnss/power/control"], 10.0),
        run_step(args, store, "icnss-runtime-status", ["cat", "/sys/devices/platform/soc/18800000.qcom,icnss/power/runtime_status"], 10.0),
        run_step(args, store, "dmesg", ["run", args.toybox, "dmesg"], 60.0),
    ]


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(args: argparse.Namespace,
                 steps: list[dict[str, Any]],
                 wlan_keys: dict[str, str],
                 dmesg: dict[str, Any],
                 v513: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run V514 read-only classifier")
        return checks

    version = step_payload(steps, "version")
    status = step_payload(steps, "status")
    selftest = step_payload(steps, "selftest")
    ps = step_payload(steps, "ps")
    sys_net = step_payload(steps, "sys-class-net")
    sys_ieee = step_payload(steps, "sys-class-ieee80211")
    processes = [line.strip() for line in ps.splitlines() if WIFI_PROCESS_RE.search(line)]
    links = [line.strip() for line in (sys_net + "\n" + sys_ieee).splitlines() if WIFI_LINK_RE.search(line)]
    qcwlanstate_ready = wlan_keys.get("wlanboot.status.qcwlanstate.exists") == "1"
    dev_wlan_ready = (
        wlan_keys.get("wlanboot.status.dev_wlan.exists") == "1" and
        wlan_keys.get("wlanboot.status.dev_wlan.type") == "char"
    )
    no_wlan_surface = (
        wlan_keys.get("wlanboot.status.sys_class_net_wlan0.exists") == "0" and
        wlan_keys.get("wlanboot.status.sys_class_ieee80211.count") == "0" and
        wlan_keys.get("wlanboot.status.proc_net_dev.wlan_present") == "0"
    )
    partial_init = dmesg["has_loading_driver"] and dmesg["has_state_initialized"]
    no_success = not dmesg["has_driver_loaded"]
    timeout_blocker = dmesg["has_wifi_turning_on"] and dmesg["has_timed_out"] and dmesg["has_modules_not_initialized"]

    add_check(checks, "native-clean", "pass" if args.expect_version in version and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker",
              f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:3], "restore native health before Wi-Fi retry")
    add_check(checks, "no-active-wifi-processes", "pass" if not processes else "warn", "warning",
              f"process_count={len(processes)}", processes[:8], "inspect residual Wi-Fi processes before any later mutation")
    add_check(checks, "no-wifi-link-surface", "pass" if no_wlan_surface and not links else "blocked", "blocker",
              f"links={len(links)} wlan0={wlan_keys.get('wlanboot.status.sys_class_net_wlan0.exists')} phy_count={wlan_keys.get('wlanboot.status.sys_class_ieee80211.count')}",
              links[:8], "if a Wi-Fi interface appears, advance to scan-only instead of readiness triage")
    add_check(checks, "qcwlanstate-devnode-ready", "pass" if qcwlanstate_ready and dev_wlan_ready else "blocked", "blocker",
              f"qcwlanstate={qcwlanstate_ready} dev_wlan={dev_wlan_ready}", [
                  f"qcwlanstate={wlan_keys.get('wlanboot.status.qcwlanstate.value')}",
                  f"dev_wlan={wlan_keys.get('wlanboot.status.dev_wlan.major')}:{wlan_keys.get('wlanboot.status.dev_wlan.minor')}",
              ], "repair qcwlanstate/devnode before retrying driver-state")
    add_check(checks, "v513-driver-state-evidence", "pass" if v513.get("exists") and v513.get("write_executed") else "blocked", "blocker",
              f"decision={v513.get('decision')} write_rc={v513.get('write_rc')} errno={v513.get('write_errno')}",
              [str(v513.get("path"))], "run V513 first to prove the private ON path")
    add_check(checks, "wlan-module-init-partial", "pass" if partial_init else "blocked", "blocker",
              f"loading={dmesg['has_loading_driver']} state_initialized={dmesg['has_state_initialized']}",
              [str((dmesg["latest"].get("loading_driver") or {}).get("line", "")),
               str((dmesg["latest"].get("state_initialized") or {}).get("line", ""))],
              "if missing, inspect boot_wlan init path before HAL work")
    add_check(checks, "wlan-module-not-loaded", "pass" if no_success and timeout_blocker else "warn", "warning",
              f"driver_loaded={dmesg['has_driver_loaded']} timeout_blocker={timeout_blocker}",
              [str((dmesg["latest"].get("wifi_turning_on") or {}).get("line", "")),
               str((dmesg["latest"].get("timed_out") or {}).get("line", "")),
               str((dmesg["latest"].get("modules_not_initialized") or {}).get("line", ""))],
              "classify corrected init order before scan/connect")
    add_check(checks, "cnss-userspace-observed", "pass" if dmesg["has_cnss_daemon_netlink"] else "warn", "warning",
              f"cnss_daemon_netlink={dmesg['has_cnss_daemon_netlink']}",
              [str((dmesg["latest"].get("cnss_daemon_netlink") or {}).get("line", ""))],
              "compare cnss-daemon timing against Android boot-complete")
    return checks


def blocking_checks(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], dmesg: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return "v514-icnss-module-readiness-plan-ready", True, "plan-only; no device command executed", "run V514 read-only classifier"
    blockers = blocking_checks(checks)
    if blockers:
        return "v514-icnss-module-readiness-blocked", False, "blocked by " + ", ".join(blockers), "resolve missing baseline evidence"
    if dmesg["has_wifi_turning_on"] and dmesg["has_timed_out"] and dmesg["has_modules_not_initialized"] and not dmesg["has_driver_loaded"]:
        return "v514-wlan-module-init-timeout-classified", True, "WLAN init starts but does not reach driver-loaded; ICNSS/modules-not-initialized timeout is the current blocker", "compare Android boot order and build corrected native init sequence"
    if dmesg["has_driver_loaded"]:
        return "v514-wlan-driver-loaded-review", True, "dmesg contains a driver-loaded marker; runtime surface still needs reconciliation", "re-run scan-only readiness check"
    return "v514-icnss-module-readiness-review", True, "read-only evidence captured but blocker pattern is not canonical", "inspect dmesg focus and add a narrower classifier"


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    dmesg = manifest.get("dmesg_summary") or {}
    counts = dmesg.get("counts") or {}
    count_rows = [[key, value] for key, value in sorted(counts.items())]
    wlan = manifest.get("wlan_status") or {}
    wlan_rows = [
        ["qcwlanstate", wlan.get("wlanboot.status.qcwlanstate.value", "")],
        ["dev_wlan", f"{wlan.get('wlanboot.status.dev_wlan.major', '')}:{wlan.get('wlanboot.status.dev_wlan.minor', '')}"],
        ["wlan0_exists", wlan.get("wlanboot.status.sys_class_net_wlan0.exists", "")],
        ["ieee80211_count", wlan.get("wlanboot.status.sys_class_ieee80211.count", "")],
        ["proc_net_dev_wlan", wlan.get("wlanboot.status.proc_net_dev.wlan_present", "")],
    ]
    focus = dmesg.get("focus_tail") or []
    return "\n".join([
        "# V514 ICNSS/WLAN Module-Readiness Classifier",
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
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## WLAN Status",
        "",
        markdown_table(["key", "value"], wlan_rows),
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
    steps: list[dict[str, Any]] = []
    if args.command == "run":
        steps = collect_steps(args, store)
    wlan_keys = parse_key_values(step_payload(steps, "wlanboot-status"))
    dmesg = dmesg_pattern_summary(step_payload(steps, "dmesg")) if steps else dmesg_pattern_summary("")
    v513 = load_v513_manifest(args.v513_manifest)
    checks = build_checks(args, steps, wlan_keys, dmesg, v513)
    decision, pass_ok, reason, next_step = decide(args.command, checks, dmesg)
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
        "wlan_status": wlan_keys,
        "dmesg_summary": dmesg,
        "v513_manifest": v513,
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
