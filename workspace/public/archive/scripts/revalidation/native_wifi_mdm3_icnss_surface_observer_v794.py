#!/usr/bin/env python3
"""V794 read-only mdm3 + ICNSS/WLFW surface observer.

V793 routed away from unchanged service-manager/binder-only/boot_wlan retries and
selected the mdm3 + ICNSS/WLFW continuation gap.  V794 only reads the current
native boot surface: msm_subsys, esoc, ICNSS, wlan/qcwlanstate, QRTR/netlink,
procfs, and dmesg focus.  It does not write sysfs, start daemons, start Wi-Fi
HAL, scan/connect, run DHCP, ping externally, or modify boot/partitions.
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
from a90ctl import bridge_exchange
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v794-mdm3-icnss-surface-observer")
LATEST_POINTER = Path("tmp/wifi/latest-v794-mdm3-icnss-surface-observer.txt")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 60.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_V793_MANIFEST = Path("tmp/wifi/v793-cnss-icnss-route-classifier/manifest.json")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
SECRET_RE = re.compile(r"(made by|creator: made by) [^\r\n]+", re.IGNORECASE)

FORBIDDEN_ACTIONS = (
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "boot_wlan/qcwlanstate write",
    "scan/connect/link-up",
    "Wi-Fi credential use",
    "DHCP/routing/external ping",
    "sysfs/debugfs/control write",
    "esoc0 open/hold",
    "module load/unload or bind/unbind",
    "boot image or partition write",
    "custom kernel flash",
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--v793-manifest", type=Path, default=DEFAULT_V793_MANIFEST)
    parser.add_argument("--allow-live-readonly", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def redact(text: str) -> str:
    return SECRET_RE.sub(r"\1 [redacted]", text)


def clean_text(text: str) -> str:
    return redact(ANSI_RE.sub("", text))


def shell_cmd(args: argparse.Namespace, script: str) -> list[str]:
    return ["run", args.busybox, "sh", "-c", script]


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{name}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             name: str,
             command: list[str],
             timeout: float | None = None) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    if "[busy]" in text and args.hide_on_busy:
        send_hide(args)
        capture = run_capture(args, name, command, timeout=timeout)
        text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    text = clean_text(text)
    item = capture_to_manifest(capture)
    item["file"] = write_capture(store, name, text)
    item["payload"] = text
    item["ok"] = capture.ok
    return item


def send_hide(args: argparse.Namespace) -> None:
    bridge_exchange(
        args.host,
        args.port,
        "hide",
        min(args.timeout, 8.0),
        markers=(b"[busy]", b"[done]", b"[err]"),
    )


def required_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    if not args.assume_yes:
        missing.append("--assume-yes")
    if not args.allow_live_readonly:
        missing.append("--allow-live-readonly")
    return missing


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("native")
    bb = args.busybox
    toybox = args.toybox
    subsys_script = (
        f"BB={bb}; "
        "for d in /sys/bus/msm_subsys/devices/*; do "
        "[ -e \"$d\" ] || continue; "
        "printf '== %s ==\\n' \"$d\"; "
        "\"$BB\" ls -ld \"$d\" 2>&1 || true; "
        "\"$BB\" readlink \"$d\" 2>/dev/null || true; "
        "for f in name state crash_count restart_level fw_name; do "
        "printf '%s=' \"$f\"; \"$BB\" cat \"$d/$f\" 2>&1 || true; "
        "done; "
        "done"
    )
    esoc_script = (
        f"BB={bb}; "
        "for p in /sys/bus/esoc/devices /sys/bus/esoc/devices/* /sys/kernel/debug/esoc /sys/kernel/debug/esoc/*; do "
        "printf '== %s ==\\n' \"$p\"; "
        "\"$BB\" ls -ld \"$p\" 2>&1 || true; "
        "if [ -f \"$p\" ]; then \"$BB\" cat \"$p\" 2>&1 || true; fi; "
        "if [ -d \"$p\" ]; then \"$BB\" ls -la \"$p\" 2>&1 | \"$BB\" head -80; fi; "
        "done"
    )
    icnss_script = (
        f"BB={bb}; "
        "for p in "
        "/sys/bus/platform/drivers/icnss "
        "/sys/bus/platform/devices/18800000.qcom,icnss "
        "/sys/bus/platform/devices/18800000.qcom,icnss/driver "
        "/sys/bus/platform/devices/18800000.qcom,icnss/power "
        "/sys/module/icnss "
        "/sys/module/icnss/parameters "
        "/sys/module/wlan "
        "/sys/module/wlan/parameters "
        "/sys/kernel/debug/icnss "
        "/sys/kernel/boot_wlan "
        "/sys/kernel/shutdown_wlan "
        "/dev/qcwlanstate "
        "/dev/wlan "
        "; do "
        "printf '== %s ==\\n' \"$p\"; "
        "\"$BB\" ls -ld \"$p\" 2>&1 || true; "
        "\"$BB\" readlink \"$p\" 2>/dev/null || true; "
        "if [ -d \"$p\" ]; then \"$BB\" ls -la \"$p\" 2>&1 | \"$BB\" head -100; fi; "
        "done"
    )
    icnss_values_script = (
        f"BB={bb}; "
        "for p in "
        "/sys/bus/platform/devices/18800000.qcom,icnss/uevent "
        "/sys/bus/platform/devices/18800000.qcom,icnss/modalias "
        "/sys/bus/platform/devices/18800000.qcom,icnss/power/control "
        "/sys/bus/platform/devices/18800000.qcom,icnss/power/runtime_status "
        "/sys/module/wlan/parameters/fwpath "
        "/sys/module/wlan/parameters/con_mode "
        "/sys/module/wlan/parameters/country_code "
        "; do "
        "printf '== %s ==\\n' \"$p\"; \"$BB\" cat \"$p\" 2>&1 || true; "
        "done"
    )
    binder_script = (
        f"BB={bb}; "
        "for p in /dev/binder /dev/hwbinder /dev/vndbinder /sys/kernel/debug/binder /sys/kernel/debug/binder/*; do "
        "printf '== %s ==\\n' \"$p\"; "
        "\"$BB\" ls -ld \"$p\" 2>&1 || true; "
        "if [ -f \"$p\" ]; then \"$BB\" cat \"$p\" 2>&1 | \"$BB\" head -120 || true; fi; "
        "if [ -d \"$p\" ]; then \"$BB\" ls -la \"$p\" 2>&1 | \"$BB\" head -80; fi; "
        "done"
    )
    dmesg_script = (
        f"BB={bb}; "
        f"{toybox} dmesg | \"$BB\" grep -i -E "
        "'mdm3|mss|subsys|esoc|icnss|wlan|wlfw|qcwlan|hdd|pld|cnss|binder|service-notifier|servloc|sysmon-qmi|qrtr|qmi|memshare|cma|bdf|regdb|bdwlan' "
        "| \"$BB\" tail -360"
    )
    commands: list[tuple[str, list[str], float]] = [
        ("status", ["status"], 20.0),
        ("selftest", ["selftest"], 25.0),
        ("msm-subsys", shell_cmd(args, subsys_script), 25.0),
        ("esoc-surface", shell_cmd(args, esoc_script), 20.0),
        ("icnss-wlan-surface", shell_cmd(args, icnss_script), 25.0),
        ("icnss-wlan-values", shell_cmd(args, icnss_values_script), 20.0),
        ("binder-surface", shell_cmd(args, binder_script), 20.0),
        ("proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
        ("proc-net-qrtr", ["cat", "/proc/net/qrtr"], 10.0),
        ("proc-net-netlink", ["cat", "/proc/net/netlink"], 10.0),
        ("proc-modules", ["cat", "/proc/modules"], 10.0),
        ("dmesg-focus-tail", shell_cmd(args, dmesg_script), args.timeout),
    ]
    return [run_step(args, store, name, command, timeout) for name, command, timeout in commands]


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def value_block(text: str, marker: str) -> str:
    lines = text.splitlines()
    target = f"== {marker} =="
    for index, line in enumerate(lines):
        if line.strip() != target:
            continue
        values: list[str] = []
        for next_line in lines[index + 1:]:
            if next_line.startswith("== ") and next_line.endswith(" =="):
                break
            if next_line.strip():
                values.append(next_line.rstrip())
        return "\n".join(values)
    return ""


def present(block: str) -> bool:
    return bool(block.strip()) and "No such file or directory" not in block


def parse_subsys(text: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    current_path = ""
    current: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("== ") and line.endswith(" =="):
            if current_path:
                key = current.get("name") or Path(current_path).name
                result[key] = dict(current, path=current_path)
            current_path = line[3:-3].strip()
            current = {}
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            if key in {"name", "state", "crash_count", "restart_level", "fw_name"}:
                current[key] = value.strip()
    if current_path:
        key = current.get("name") or Path(current_path).name
        result[key] = dict(current, path=current_path)
    return result


def dmesg_count(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.IGNORECASE))


def build_surface(args: argparse.Namespace, steps: list[dict[str, Any]]) -> dict[str, Any]:
    subsys_text = step_payload(steps, "msm-subsys")
    esoc_text = step_payload(steps, "esoc-surface")
    icnss_text = step_payload(steps, "icnss-wlan-surface")
    value_text = step_payload(steps, "icnss-wlan-values")
    binder_text = step_payload(steps, "binder-surface")
    netdev_text = step_payload(steps, "proc-net-dev")
    qrtr_text = step_payload(steps, "proc-net-qrtr")
    modules_text = step_payload(steps, "proc-modules")
    dmesg_text = step_payload(steps, "dmesg-focus-tail")
    subsys = parse_subsys(subsys_text)
    lower_subsys = {key.lower(): value for key, value in subsys.items()}
    mdm3 = lower_subsys.get("mdm3", {})
    esoc0 = lower_subsys.get("esoc0", {})
    modem = lower_subsys.get("modem", {}) or lower_subsys.get("mss", {})
    return {
        "v793_reference": str(repo_path(args.v793_manifest)),
        "subsys": subsys,
        "modem_state": modem.get("state", ""),
        "mdm3_state": mdm3.get("state", ""),
        "mdm3_present": bool(mdm3),
        "esoc0_subsys_state": esoc0.get("state", ""),
        "esoc_devices_present": "/sys/bus/esoc/devices" in esoc_text and "No such file" not in value_block(esoc_text, "/sys/bus/esoc/devices"),
        "esoc0_present": "esoc0" in esoc_text,
        "icnss_device_present": present(value_block(icnss_text, "/sys/bus/platform/devices/18800000.qcom,icnss")),
        "icnss_driver_link_present": present(value_block(icnss_text, "/sys/bus/platform/devices/18800000.qcom,icnss/driver")),
        "wlan_module_present": present(value_block(icnss_text, "/sys/module/wlan")),
        "wlan_parameters_present": present(value_block(icnss_text, "/sys/module/wlan/parameters")),
        "qcwlanstate_present": present(value_block(icnss_text, "/dev/qcwlanstate")),
        "dev_wlan_present": present(value_block(icnss_text, "/dev/wlan")),
        "boot_wlan_node_present": present(value_block(icnss_text, "/sys/kernel/boot_wlan")),
        "wlan_fwpath": value_block(value_text, "/sys/module/wlan/parameters/fwpath"),
        "wlan_con_mode": value_block(value_text, "/sys/module/wlan/parameters/con_mode"),
        "wlan_country_code": value_block(value_text, "/sys/module/wlan/parameters/country_code"),
        "wlan0_visible": bool(re.search(r"\bwlan0\b", netdev_text)),
        "wlan_like_netdevs": sorted(set(re.findall(r"\b(?:wlan|swlan|p2p|wifi-aware)[A-Za-z0-9_-]*\b", netdev_text))),
        "qrtr_table_available": "No such file or directory" not in qrtr_text,
        "wlan_module_loaded": any(line.split()[:1] == ["wlan"] for line in modules_text.splitlines()),
        "binder_devnodes_present": all(marker in binder_text and "No such file" not in value_block(binder_text, marker) for marker in ("/dev/binder", "/dev/hwbinder", "/dev/vndbinder")),
        "dmesg_counts": {
            "mdm3": dmesg_count(dmesg_text, r"mdm3"),
            "mss_modem": dmesg_count(dmesg_text, r"\bmss\b|modem"),
            "service_notifier": dmesg_count(dmesg_text, r"service-notifier"),
            "sysmon_qmi": dmesg_count(dmesg_text, r"sysmon-qmi"),
            "qrtr": dmesg_count(dmesg_text, r"qrtr"),
            "icnss": dmesg_count(dmesg_text, r"icnss"),
            "icnss_qmi": dmesg_count(dmesg_text, r"icnss.*qmi|QMI Server Connected"),
            "wlfw": dmesg_count(dmesg_text, r"wlfw|WLFW|WLAN FW"),
            "bdf": dmesg_count(dmesg_text, r"\bBDF\b|bdwlan|regdb"),
            "wlan0": dmesg_count(dmesg_text, r"\bwlan0\b"),
            "binder_minus22": dmesg_count(dmesg_text, r"binder: .* -22|binder: .*returned -22"),
            "qcwlanstate": dmesg_count(dmesg_text, r"qcwlanstate|wlan_hdd_state"),
            "boot_wlan": dmesg_count(dmesg_text, r"boot_wlan|Modules not initialized"),
            "memshare_cma": dmesg_count(dmesg_text, r"memshare|cma_alloc|CMA"),
        },
    }


def build_checks(args: argparse.Namespace,
                 flags_missing: list[str],
                 v793: dict[str, Any],
                 surface: dict[str, Any] | None) -> list[Check]:
    checks: list[Check] = []
    checks.append(Check(
        "v793-reference",
        "pass" if v793.get("decision") == "v793-route-mdm3-icnss-wlfw-continuation" and v793.get("pass") is True else "blocked",
        "blocker",
        f"decision={v793.get('decision')} pass={v793.get('pass')}",
        "complete V793 before V794",
    ))
    if args.command == "plan":
        checks.append(Check("plan-only", "pass", "info", "no device command executed", "run V794 with explicit read-only live flags"))
        return checks
    checks.append(Check("explicit-readonly-flags", "pass" if not flags_missing else "blocked", "blocker", "missing=" + ",".join(flags_missing), "pass --assume-yes --allow-live-readonly"))
    if surface is None:
        checks.append(Check("surface-collected", "blocked", "blocker", "surface missing", "inspect capture failures"))
        return checks
    checks.extend([
        Check("surface-collected", "pass", "blocker", "read-only captures completed", "classify current surface"),
        Check("idle-modem-state", "pass" if surface.get("modem_state") == "OFFLINING" else "review", "warn", f"modem_state={surface.get('modem_state')}", "if modem is ONLINE at idle, reroute to ICNSS-QMI/WLFW trigger"),
        Check("idle-esoc-mdm3-state", "pass" if surface.get("esoc0_subsys_state") == "OFFLINING" or surface.get("mdm3_state") == "OFFLINING" else "review", "warn", f"mdm3_present={surface.get('mdm3_present')} mdm3_state={surface.get('mdm3_state')} esoc0_state={surface.get('esoc0_subsys_state')}", "if mdm3/esoc0 is ONLINE, reroute to ICNSS-QMI/WLFW trigger"),
        Check("icnss-bound", "pass" if surface.get("icnss_device_present") and surface.get("icnss_driver_link_present") else "blocked", "blocker", f"icnss_device={surface.get('icnss_device_present')} driver={surface.get('icnss_driver_link_present')}", "do not proceed without ICNSS platform binding evidence"),
        Check("wlan-control-surface", "pass" if surface.get("wlan_module_present") and surface.get("qcwlanstate_present") else "review", "warn", f"wlan_module={surface.get('wlan_module_present')} qcwlanstate={surface.get('qcwlanstate_present')} boot_wlan={surface.get('boot_wlan_node_present')}", "if absent, compare against V750/V752 control surface"),
        Check("no-wlan0", "pass" if not surface.get("wlan0_visible") else "advanced", "info", f"wlan0={surface.get('wlan0_visible')} netdevs={surface.get('wlan_like_netdevs')}", "if wlan0 appears, stop before credentials and capture link state"),
        Check("readonly-safety", "pass", "blocker", "no write/start/connect command is generated by V794", "preserve read-only behavior"),
    ])
    return checks


def decide(args: argparse.Namespace, checks: list[Check], surface: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v794-mdm3-icnss-surface-observer-plan-ready", True, "plan-only; no device command executed", "run bounded read-only V794 live observer"
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return "v794-mdm3-icnss-surface-observer-blocked", False, "blocked by " + ", ".join(blockers), "repair capture prerequisites before next route"
    if surface and surface.get("wlan0_visible"):
        return "v794-wlan0-visible-stop-before-connect", True, "read-only capture sees wlan0 or WLAN-like netdev", "capture link state before credentials, DHCP, or external ping"
    if surface and surface.get("modem_state") == "OFFLINING" and surface.get("esoc0_subsys_state") == "OFFLINING" and surface.get("icnss_device_present"):
        return "v794-idle-modem-esoc-offlining-icnss-bound-captured", True, "current idle read-only surface confirms modem/esoc0 OFFLINING, ICNSS bound, WLAN control nodes present, and no WLFW/BDF/wlan0", "plan V795 as a lower-window mdm3/esoc observer: firmware mounts plus subsys_modem holder, then read mdm3/esoc/ICNSS/WLFW surfaces without service-manager, boot_wlan, HAL, scan/connect, DHCP, or external ping"
    return "v794-current-icnss-surface-captured", True, "current read-only mdm3/ICNSS surface captured", "review surface before choosing next live action"


def render_summary(manifest: dict[str, Any]) -> str:
    surface = manifest.get("surface") or {}
    return "\n".join([
        "# V794 mdm3/ICNSS Surface Observer",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Surface",
        "",
        markdown_table(["signal", "value"], [
            ["modem_state", surface.get("modem_state")],
            ["mdm3_state", surface.get("mdm3_state")],
            ["esoc0_subsys_state", surface.get("esoc0_subsys_state")],
            ["esoc0_present", surface.get("esoc0_present")],
            ["icnss_device/driver", f"{surface.get('icnss_device_present')} / {surface.get('icnss_driver_link_present')}"],
            ["wlan_module/qcwlanstate/boot_wlan", f"{surface.get('wlan_module_present')} / {surface.get('qcwlanstate_present')} / {surface.get('boot_wlan_node_present')}"],
            ["wlan0/netdevs", f"{surface.get('wlan0_visible')} / {surface.get('wlan_like_netdevs')}"],
            ["qrtr_table_available", surface.get("qrtr_table_available")],
            ["binder_devnodes_present", surface.get("binder_devnodes_present")],
        ]) if surface else "- not collected",
        "",
        "## Dmesg Counts",
        "",
        markdown_table(["marker", "count"], [[key, value] for key, value in sorted((surface.get("dmesg_counts") or {}).items())]) if surface else "- not collected",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Safety",
        "",
        "- Read-only live observer.",
        "- No daemon start, service-manager start, Wi-Fi HAL start, boot_wlan/qcwlanstate write, scan/connect, credential use, DHCP/routes, external ping, esoc0 open, module bind/unbind, boot image write, partition write, or custom kernel flash.",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v793 = read_json(args.v793_manifest)
    flags_missing = required_flags(args)
    steps: list[dict[str, Any]] = []
    surface: dict[str, Any] | None = None
    if args.command == "run" and not flags_missing:
        steps = collect_steps(args, store)
        surface = build_surface(args, steps)
    checks = build_checks(args, flags_missing, v793, surface)
    decision, passed, reason, next_step = decide(args, checks, surface)
    manifest = {
        "cycle": "v794",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "v793_reference": {"decision": v793.get("decision"), "pass": v793.get("pass"), "path": str(repo_path(args.v793_manifest))},
        "surface": surface or {},
        "checks": [asdict(check) for check in checks],
        "steps": [{key: value for key, value in step.items() if key != "payload"} for step in steps],
        "device_commands_executed": args.command == "run" and not flags_missing,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "boot_wlan_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "custom_kernel_flash_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"boot_wlan_executed: {manifest['boot_wlan_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
