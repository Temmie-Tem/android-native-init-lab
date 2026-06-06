#!/usr/bin/env python3
"""V1858 host/device availability preflight for a future SDX50M bridge gate."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1858"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1858-sdx50m-bridge-host-preflight"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1858_SDX50M_BRIDGE_HOST_PREFLIGHT_2026-06-03.md"
)
V1857_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1857-sdx50m-bridge-artifact-plumbing"
    / "manifest.json"
)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_host(name: str, command: list[str], timeout: float = 3.0) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if not executable:
        return {
            "name": name,
            "command": command,
            "available": False,
            "rc": 127,
            "stdout": "",
            "stderr": f"{command[0]} not found",
        }
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "name": name,
            "command": command,
            "available": True,
            "rc": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "timeout",
        }
    return {
        "name": name,
        "command": command,
        "available": True,
        "rc": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def clean_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def parse_adb_devices(stdout: str) -> list[str]:
    devices: list[str] = []
    for line in clean_lines(stdout):
        if line.startswith("List of devices"):
            continue
        if "\t" in line or " device" in line:
            devices.append(line)
    return devices


def parse_ncm(addrs: str) -> dict[str, Any]:
    matching = [
        line
        for line in clean_lines(addrs)
        if ("enx" in line or "usb" in line or "rndis" in line or "ncm" in line)
    ]
    return {
        "matching_lines": matching,
        "up": any("UP" in line for line in matching),
        "has_ipv4": any("/" in line and any(char.isdigit() for char in line) for line in matching),
    }


def collect_preflight(v1857: dict[str, Any]) -> dict[str, Any]:
    commands = {
        "git_status": run_host("git_status", ["git", "status", "--short"]),
        "ip_addr": run_host("ip_addr", ["ip", "-br", "addr"]),
        "ip_route_default": run_host("ip_route_default", ["ip", "route", "show", "default"]),
        "adb_devices": run_host("adb_devices", ["adb", "devices", "-l"]),
        "lsusb": run_host("lsusb", ["lsusb"]),
        "a90ctl_path": {
            "name": "a90ctl_path",
            "command": ["command", "-v", "a90ctl"],
            "available": shutil.which("a90ctl") is not None,
            "rc": 0 if shutil.which("a90ctl") else 127,
            "stdout": shutil.which("a90ctl") or "",
            "stderr": "",
        },
    }
    ncm = parse_ncm(commands["ip_addr"]["stdout"])
    adb_lines = parse_adb_devices(commands["adb_devices"]["stdout"])
    usb_lines = [
        line
        for line in clean_lines(commands["lsusb"]["stdout"])
        if any(token in line.lower() for token in ("samsung", "android", "qualcomm", "qcom"))
    ]
    return {
        "v1857": {
            "path": rel(V1857_MANIFEST),
            "decision": v1857.get("decision", ""),
            "label": v1857.get("label", ""),
            "pass": bool(v1857.get("pass")),
        },
        "commands": {
            key: {
                "available": value.get("available"),
                "rc": value.get("rc"),
                "stdout_lines": clean_lines(value.get("stdout", ""))[:20],
                "stderr_lines": clean_lines(value.get("stderr", ""))[:20],
            }
            for key, value in commands.items()
        },
        "summary": {
            "git_clean": commands["git_status"]["rc"] == 0 and commands["git_status"]["stdout"] == "",
            "ncm_up": ncm["up"],
            "ncm_has_ipv4": ncm["has_ipv4"],
            "ncm_lines": ncm["matching_lines"],
            "default_route_present": commands["ip_route_default"]["rc"] == 0 and bool(clean_lines(commands["ip_route_default"]["stdout"])),
            "adb_available": bool(commands["adb_devices"]["available"]),
            "adb_device_count": len(adb_lines),
            "adb_device_lines": adb_lines,
            "usb_android_present": bool(usb_lines),
            "usb_android_lines": usb_lines,
            "a90ctl_available": bool(commands["a90ctl_path"]["available"]),
        },
        "safety": {
            "device_command_executed": False,
            "flash_executed": False,
            "reboot_executed": False,
            "stage_properties_executed": False,
            "start_actors_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "direct_subsys_esoc0_open_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
            "esoc_ioctl_notify_executed": False,
            "forced_rc1_or_pci_rescan_executed": False,
        },
    }


def classify(details: dict[str, Any]) -> tuple[str, str, str, bool]:
    summary = details["summary"]
    safety_clean = not any(details["safety"].values())
    input_ready = (
        details["v1857"]["pass"]
        and details["v1857"]["label"] == "artifact-plumbing-dry-run-ready"
    )
    host_ready = (
        summary["ncm_up"]
        and summary["ncm_has_ipv4"]
        and summary["default_route_present"]
        and summary["usb_android_present"]
    )
    device_command_ready = summary["a90ctl_available"] and summary["adb_device_count"] > 0
    if not input_ready:
        return "input-review", "v1858-input-review", "V1857 artifact plumbing input is missing or not passing", False
    if not safety_clean:
        return "safety-review", "v1858-safety-review", "Preflight claims a forbidden device or Wi-Fi action", False
    if host_ready and device_command_ready:
        return (
            "host-device-preflight-ready",
            "v1858-host-device-preflight-ready-host-pass",
            "Host/NCM/USB and device command surfaces are available for a future reviewed bridge gate",
            True,
        )
    if host_ready:
        return (
            "host-ready-device-command-missing",
            "v1858-host-ready-device-command-missing-host-pass",
            "Host/NCM/USB surfaces are present, but adb has no listed device and a90ctl is unavailable, so a future live bridge gate cannot be attempted from this shell yet",
            True,
        )
    return (
        "host-preflight-incomplete",
        "v1858-host-preflight-incomplete",
        "Host/NCM/USB preflight is incomplete for a future bridge gate",
        False,
    )


def render_report(result: dict[str, Any]) -> str:
    details = result["details"]
    summary = details["summary"]
    return "\n".join([
        "# Native Init V1858 SDX50M Bridge Host Preflight",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: host-only availability preflight for a future one-run SDX50M bridge gate",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Host State",
        "",
        f"- git clean: `{summary['git_clean']}`",
        f"- NCM up/IPv4/default route: `{summary['ncm_up']}` / `{summary['ncm_has_ipv4']}` / `{summary['default_route_present']}`",
        f"- NCM lines: `{summary['ncm_lines']}`",
        f"- USB Android present: `{summary['usb_android_present']}` lines `{summary['usb_android_lines']}`",
        f"- adb available/device count: `{summary['adb_available']}` / `{summary['adb_device_count']}`",
        f"- a90ctl available: `{summary['a90ctl_available']}`",
        "",
        "## Input",
        "",
        f"- V1857: `{details['v1857']['decision']}` / `{details['v1857']['label']}` / pass `{details['v1857']['pass']}`",
        "",
        "## Safety Scope",
        "",
        "Host-only. This preflight did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "- Before any future live bridge gate, restore a usable device command surface from this shell: `a90ctl` path or another reviewed transport plus a visible target device.",
        "",
    ])


def main() -> int:
    details = collect_preflight(load_json(V1857_MANIFEST))
    label, decision, reason, passed = classify(details)
    result = {
        "cycle": CYCLE,
        "decision": decision,
        "label": label,
        "pass": passed,
        "reason": reason,
        "out_dir": rel(OUT_DIR),
        "report": rel(REPORT_PATH),
        "details": details,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("decision", "label", "pass", "reason", "out_dir", "report")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
