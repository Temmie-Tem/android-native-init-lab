#!/usr/bin/env python3
"""V711 read-only ICNSS/QCA/WLFW edge classifier.

The runner collects current read-only ICNSS/QCA/WLAN surfaces and combines them
with V710/V703 evidence. It does not start daemons, write sysfs, start Wi-Fi
HAL, scan/connect, run DHCP, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    capture_to_manifest,
    collect_host_metadata,
    markdown_table,
    repo_path,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v711-icnss-edge-readonly")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_SHELL = "/cache/bin/busybox"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_V710_MANIFEST = Path("tmp/wifi/v710-kernel-event-source-classifier-rerun/manifest.json")
DEFAULT_ANDROID_MANIFEST = Path("tmp/wifi/v703-android-native-binding-compare/manifest.json")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

FORBIDDEN_ACTIONS = (
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "Wi-Fi credential use",
    "DHCP/routing/external ping",
    "sysfs/debugfs/control write",
    "ICNSS bind/unbind/driver_override/recovery/ramdump/assert",
    "boot image or partition write",
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
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
    parser.add_argument("--shell", default=DEFAULT_SHELL)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--v710-manifest", type=Path, default=DEFAULT_V710_MANIFEST)
    parser.add_argument("--android-manifest", type=Path, default=DEFAULT_ANDROID_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path | str) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path | str) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def clean_text(text: str) -> str:
    return ANSI_RE.sub("", text)


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
    text = clean_text(text)
    item = capture_to_manifest(capture)
    item["file"] = write_capture(store, name, text)
    item["payload"] = text
    return item


def sh_cmd(args: argparse.Namespace, script: str) -> list[str]:
    return ["run", args.shell, "sh", "-c", script]


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("native")
    shell = args.shell
    focus_script = (
        f"BB={shell}; "
        "for p in "
        "/sys/bus/platform/drivers/icnss "
        "/sys/bus/platform/devices/18800000.qcom,icnss "
        "/sys/bus/platform/devices/18800000.qcom,icnss/driver "
        "/sys/bus/platform/devices/18800000.qcom,icnss/power "
        "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390 "
        "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390/driver "
        "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390/power "
        "/sys/module/icnss "
        "/sys/module/icnss/parameters "
        "/sys/module/wlan "
        "/sys/module/wlan/parameters "
        "/sys/kernel/shutdown_wlan "
        "/sys/class/net "
        "/sys/bus/mhi/devices "
        "/sys/bus/mhi/drivers "
        "/sys/bus/pci/devices "
        "/sys/bus/pci/drivers "
        "/sys/bus/rpmsg/devices "
        "/sys/bus/rpmsg/drivers "
        "; do "
        "printf '== %s ==\\n' \"$p\"; "
        "\"$BB\" ls -ld \"$p\" 2>&1 || true; "
        "\"$BB\" readlink \"$p\" 2>/dev/null || true; "
        "if [ -d \"$p\" ]; then \"$BB\" ls -la \"$p\" 2>&1 | \"$BB\" head -80; fi; "
        "done"
    )
    value_script = (
        f"BB={shell}; "
        "for p in "
        "/sys/bus/platform/devices/18800000.qcom,icnss/uevent "
        "/sys/bus/platform/devices/18800000.qcom,icnss/modalias "
        "/sys/bus/platform/devices/18800000.qcom,icnss/power/control "
        "/sys/bus/platform/devices/18800000.qcom,icnss/power/runtime_status "
        "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390/uevent "
        "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390/modalias "
        "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390/power/control "
        "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390/power/runtime_status "
        "/sys/module/icnss/parameters/quirks "
        "/sys/module/icnss/parameters/dynamic_feature_mask "
        "/sys/module/wlan/parameters/fwpath "
        "/sys/module/wlan/parameters/con_mode "
        "/sys/module/wlan/parameters/country_code "
        "/sys/module/wlan/parameters/prealloc_disabled "
        "; do "
        "printf '== %s ==\\n' \"$p\"; "
        "\"$BB\" cat \"$p\" 2>&1 || true; "
        "done"
    )
    dmesg_script = (
        f"BB={shell}; "
        f"{args.toybox} dmesg | \"$BB\" grep -i -E "
        "'icnss|wlan|wlfw|qca6390|service-notifier|sysmon-qmi|qrtr|mhi|pcie|cnss' "
        "| \"$BB\" tail -260"
    )
    interrupts_script = (
        f"BB={shell}; "
        "\"$BB\" cat /proc/interrupts 2>/dev/null | \"$BB\" grep -i -E "
        "'wlan|icnss|cnss|qca|mhi|pcie' || true"
    )
    commands: list[tuple[str, list[str], float]] = [
        ("status", ["status"], 20.0),
        ("selftest", ["selftest"], 25.0),
        ("focus-sysfs", sh_cmd(args, focus_script), 25.0),
        ("focus-values", sh_cmd(args, value_script), 20.0),
        ("proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
        ("proc-net-qrtr", ["cat", "/proc/net/qrtr"], 10.0),
        ("proc-net-netlink", ["cat", "/proc/net/netlink"], 10.0),
        ("proc-interrupts-wifi", sh_cmd(args, interrupts_script), 15.0),
        ("dmesg-focus-tail", sh_cmd(args, dmesg_script), args.timeout),
    ]
    return [run_step(args, store, name, command, timeout) for name, command, timeout in commands]


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def value_block(text: str, path: str) -> str:
    marker = f"== {path} =="
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != marker:
            continue
        values: list[str] = []
        for next_line in lines[index + 1:]:
            if next_line.startswith("== ") and next_line.endswith(" =="):
                break
            if next_line.strip():
                values.append(next_line.strip())
        return "\n".join(values)
    return ""


def focus_dir_block(text: str, path: str) -> str:
    return value_block(text, path)


def present(block: str) -> bool:
    return bool(block) and "No such file or directory" not in block


def list_entries(block: str) -> list[str]:
    entries: list[str] = []
    for line in block.splitlines():
        parts = line.split()
        if not parts:
            continue
        name = parts[-1]
        if name in {".", ".."} or name.startswith("=="):
            continue
        if name not in entries:
            entries.append(name)
    return entries


def dmesg_count(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.I))


def build_surface(args: argparse.Namespace, steps: list[dict[str, Any]]) -> dict[str, Any]:
    focus = step_payload(steps, "focus-sysfs")
    values = step_payload(steps, "focus-values")
    dmesg = step_payload(steps, "dmesg-focus-tail")
    netdev = step_payload(steps, "proc-net-dev")
    v710 = load_json(args.v710_manifest)
    android = load_json(args.android_manifest)
    icnss_dir = focus_dir_block(focus, "/sys/bus/platform/devices/18800000.qcom,icnss")
    qca_dir = focus_dir_block(focus, "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390")
    wlan_params = focus_dir_block(focus, "/sys/module/wlan/parameters")
    icnss_params = focus_dir_block(focus, "/sys/module/icnss/parameters")
    qca_driver = focus_dir_block(focus, "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390/driver")
    icnss_driver = focus_dir_block(focus, "/sys/bus/platform/devices/18800000.qcom,icnss/driver")
    wlan_param_fwpath = value_block(values, "/sys/module/wlan/parameters/fwpath")
    wlan_param_con_mode = value_block(values, "/sys/module/wlan/parameters/con_mode")
    wlan_param_country = value_block(values, "/sys/module/wlan/parameters/country_code")
    return {
        "inputs": {
            "v710_manifest": str(repo_path(args.v710_manifest)),
            "android_manifest": str(repo_path(args.android_manifest)),
        },
        "v710_decision": v710.get("decision", ""),
        "v710_pass": v710.get("pass"),
        "android_decision": android.get("decision", ""),
        "android_pass": android.get("pass"),
        "android_wlfw_progression_positive": bool((android.get("android_surface") or {}).get("wlfw_progression_positive")),
        "icnss_device_present": present(icnss_dir),
        "icnss_driver_link_present": present(icnss_driver),
        "icnss_entries": list_entries(icnss_dir),
        "qca6390_device_present": present(qca_dir),
        "qca6390_driver_link_present": present(qca_driver),
        "qca6390_entries": list_entries(qca_dir),
        "wlan_module_params_present": present(wlan_params),
        "icnss_module_params_present": present(icnss_params),
        "wlan_fwpath": wlan_param_fwpath,
        "wlan_con_mode": wlan_param_con_mode,
        "wlan_country_code": wlan_param_country,
        "wlan0_visible": bool(re.search(r"\bwlan0\b", netdev)),
        "wlan_like_netdevs": sorted(set(re.findall(r"\b(?:wlan|swlan|p2p|wifi-aware)[A-Za-z0-9_-]*\b", netdev))),
        "qrtr_table_available": "No such file or directory" not in step_payload(steps, "proc-net-qrtr"),
        "dmesg_counts": {
            "service_notifier": dmesg_count(dmesg, r"service-notifier"),
            "service_notifier_wlan_pd": dmesg_count(dmesg, r"wlan[_/-]?pd|msm/modem/wlan_pd"),
            "icnss_qmi_connected": dmesg_count(dmesg, r"icnss_qmi: QMI Server Connected"),
            "wlfw": dmesg_count(dmesg, r"\bWLFW\b|wlfw_"),
            "bdf": dmesg_count(dmesg, r"\bBDF\b|bdwlan|regdb"),
            "wlan_fw_ready": dmesg_count(dmesg, r"WLAN FW is ready|fw_ready"),
            "wlan0": dmesg_count(dmesg, r"\bwlan0\b"),
            "qca6390": dmesg_count(dmesg, r"qca6390"),
            "mhi_pcie": dmesg_count(dmesg, r"\bmhi\b|\bpcie\b"),
        },
    }


def build_checks(surface: dict[str, Any] | None) -> list[Check]:
    checks = [
        Check(
            "scope-read-only",
            "pass",
            "runner captures explicit sysfs/procfs/dmesg surfaces only",
            "keep write/start/connect actions blocked until readiness advances",
        )
    ]
    if surface is None:
        return checks
    checks.extend([
        Check(
            "v710-input",
            "pass" if surface.get("v710_decision") == "v710-missing-qca6390-wlfw-kernel-event-source" else "warn",
            f"v710_decision={surface.get('v710_decision')}",
            "refresh V710 if input changed",
        ),
        Check(
            "icnss-model",
            "pass" if surface.get("icnss_device_present") and surface.get("icnss_driver_link_present") else "warn",
            f"icnss_present={surface.get('icnss_device_present')} driver_link={surface.get('icnss_driver_link_present')}",
            "if ICNSS is not bound, return to kernel platform probe",
        ),
        Check(
            "qca-node-context",
            "pass" if surface.get("qca6390_device_present") else "warn",
            f"qca6390_present={surface.get('qca6390_device_present')} driver_link={surface.get('qca6390_driver_link_present')}",
            "do not write qca bind/driver_override; use as context only",
        ),
        Check(
            "wlan-readiness",
            "pass" if not surface.get("wlan0_visible") else "advanced",
            f"wlan0_visible={surface.get('wlan0_visible')} netdevs={surface.get('wlan_like_netdevs')}",
            "if wlan0 appears, move to no-credential netdev state gate before connect",
        ),
    ])
    return checks


def decide(command: str, surface: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if command == "plan":
        return (
            "v711-icnss-edge-readonly-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V711 current read-only ICNSS edge capture",
            False,
        )
    if surface is None:
        return "v711-icnss-edge-readonly-missing-surface", False, "surface collection failed", "inspect captures", True
    if surface.get("wlan0_visible"):
        return (
            "v711-wlan0-visible-review-next",
            True,
            "current read-only capture sees wlan0 or WLAN-like netdev",
            "classify link state before credentials, DHCP, or external ping",
            True,
        )
    if surface.get("icnss_device_present") and surface.get("icnss_driver_link_present") and surface.get("qca6390_device_present"):
        return (
            "v711-icnss-qmi-wlfw-edge-targeted",
            True,
            "current boot confirms ICNSS core is bound and QCA6390 context is visible, but WLAN readiness is absent; combine with V710 to target ICNSS-QMI/WLFW readiness rather than qca bind writes",
            "implement V712 helper/window capture for ICNSS-QMI/WLFW event source with bind/unbind and Wi-Fi connect still blocked",
            True,
        )
    return (
        "v711-current-icnss-surface-review",
        True,
        "current read-only capture completed but ICNSS/QCA context is incomplete",
        "review current sysfs before another live start-only run",
        True,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    surface = manifest.get("surface") or {}
    checks = manifest.get("checks") or []
    sysfs_rows = [
        ["icnss_device_present", str(surface.get("icnss_device_present", ""))],
        ["icnss_driver_link_present", str(surface.get("icnss_driver_link_present", ""))],
        ["qca6390_device_present", str(surface.get("qca6390_device_present", ""))],
        ["qca6390_driver_link_present", str(surface.get("qca6390_driver_link_present", ""))],
        ["wlan_module_params_present", str(surface.get("wlan_module_params_present", ""))],
        ["icnss_module_params_present", str(surface.get("icnss_module_params_present", ""))],
        ["wlan_fwpath", str(surface.get("wlan_fwpath", ""))],
        ["wlan_con_mode", str(surface.get("wlan_con_mode", ""))],
        ["wlan_country_code", str(surface.get("wlan_country_code", ""))],
        ["wlan0_visible", str(surface.get("wlan0_visible", ""))],
        ["wlan_like_netdevs", ", ".join(surface.get("wlan_like_netdevs") or [])],
        ["qrtr_table_available", str(surface.get("qrtr_table_available", ""))],
    ]
    return "\n".join([
        "# V711 ICNSS Edge Read-Only Summary",
        "",
        f"- decision: `{manifest.get('decision')}`",
        f"- pass: `{manifest.get('pass')}`",
        f"- reason: {manifest.get('reason')}",
        f"- next: {manifest.get('next')}",
        f"- live_executed: `{manifest.get('live_executed')}`",
        f"- evidence: `{manifest.get('evidence_dir')}`",
        "",
        "## Scope",
        "",
        "- Read-only current-state capture plus V710/V703 evidence comparison.",
        "- No daemon/service-manager/HAL start, scan/connect, credentials, DHCP, external ping, sysfs writes, or boot image writes.",
        "",
        "## Checks",
        "",
        markdown_table(
            ["name", "status", "detail", "next"],
            [[check["name"], check["status"], check["detail"], check["next_step"]] for check in checks],
        ),
        "",
        "## Current Surface",
        "",
        markdown_table(["item", "value"], sysfs_rows),
        "",
        "## Dmesg Counts",
        "",
        markdown_table(["marker", "count"], [[key, str(value)] for key, value in sorted((surface.get("dmesg_counts") or {}).items())])
        if surface.get("dmesg_counts") else "- not collected",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    surface: dict[str, Any] | None = None
    if args.command == "run":
        steps = collect_steps(args, store)
        surface = build_surface(args, steps)
    checks = build_checks(surface)
    decision, pass_ok, reason, next_step, live_executed = decide(args.command, surface)
    return {
        "cycle": "v711",
        "created_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next": next_step,
        "live_executed": live_executed,
        "evidence_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "surface": surface or {},
        "checks": [asdict(check) for check in checks],
        "steps": [{key: value for key, value in step.items() if key != "payload"} for step in steps],
        "device_commands_executed": live_executed,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "dhcp_or_external_ping_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
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
    print(f"next: {manifest['next']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"dhcp_or_external_ping_executed: {manifest['dhcp_or_external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
