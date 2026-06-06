#!/usr/bin/env python3
"""V1859 host-only transport locator for the native-init bridge path."""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1859"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1859-bridge-transport-locator"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1859_BRIDGE_TRANSPORT_LOCATOR_2026-06-03.md"
)
V1858_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1858-sdx50m-bridge-host-preflight"
    / "manifest.json"
)
A90CTL = REPO_ROOT / "scripts" / "revalidation" / "a90ctl.py"
SERIAL_BRIDGE = REPO_ROOT / "scripts" / "revalidation" / "serial_tcp_bridge.py"
README = REPO_ROOT / "README.md"
BRIDGE_GUIDE = REPO_ROOT / "docs" / "operations" / "NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md"
SUDO_MATRIX = REPO_ROOT / "docs" / "operations" / "WIFI_V317_APPROVAL_AND_SUDO_MATRIX.md"
BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 54321


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def clean_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


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


def file_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def inspect_docs() -> dict[str, Any]:
    readme = file_text(README)
    bridge_guide = file_text(BRIDGE_GUIDE)
    sudo_matrix = file_text(SUDO_MATRIX)
    return {
        "readme": {
            "path": rel(README),
            "exists": README.exists(),
            "mentions_tty_acm0": "/dev/ttyACM0" in readme,
            "mentions_bridge_port": "54321" in readme,
            "mentions_bridge_script": "serial_tcp_bridge.py" in readme,
        },
        "bridge_guide": {
            "path": rel(BRIDGE_GUIDE),
            "exists": BRIDGE_GUIDE.exists(),
            "mentions_local_endpoint": "127.0.0.1:54321" in bridge_guide,
            "mentions_a90ctl": "a90ctl.py" in bridge_guide,
            "mentions_tty_acm0": "/dev/ttyACM0" in bridge_guide,
        },
        "sudo_matrix": {
            "path": rel(SUDO_MATRIX),
            "exists": SUDO_MATRIX.exists(),
            "mentions_explicit_device": "--device /dev/ttyACM0" in sudo_matrix,
            "mentions_read_only_bridge": "Device read-only via bridge" in sudo_matrix,
        },
    }


def inspect_scripts() -> dict[str, Any]:
    a90ctl_help = run_host("a90ctl_help", ["python3", str(A90CTL), "--help"])
    bridge_help = run_host("serial_bridge_help", ["python3", str(SERIAL_BRIDGE), "--help"])
    return {
        "a90ctl_path": {
            "path_lookup": shutil.which("a90ctl") or "",
            "path_available": shutil.which("a90ctl") is not None,
            "repo_path": rel(A90CTL),
            "repo_exists": A90CTL.exists(),
            "help_rc": a90ctl_help["rc"],
            "help_has_cmdv1": "cmdv1" in a90ctl_help["stdout"],
            "help_first_lines": clean_lines(a90ctl_help["stdout"])[:8],
        },
        "serial_bridge": {
            "repo_path": rel(SERIAL_BRIDGE),
            "repo_exists": SERIAL_BRIDGE.exists(),
            "help_rc": bridge_help["rc"],
            "help_mentions_tty": "--device" in bridge_help["stdout"],
            "help_mentions_port": "--port" in bridge_help["stdout"],
            "help_first_lines": clean_lines(bridge_help["stdout"])[:8],
        },
        "commands": {
            "a90ctl_help": {
                "available": a90ctl_help["available"],
                "rc": a90ctl_help["rc"],
                "stderr_lines": clean_lines(a90ctl_help["stderr"])[:8],
            },
            "serial_bridge_help": {
                "available": bridge_help["available"],
                "rc": bridge_help["rc"],
                "stderr_lines": clean_lines(bridge_help["stderr"])[:8],
            },
        },
    }


def inspect_tty() -> dict[str, Any]:
    tty_acm = sorted(glob.glob("/dev/ttyACM*"))
    tty_usb = sorted(glob.glob("/dev/ttyUSB*"))
    by_id = sorted(glob.glob("/dev/serial/by-id/*Samsung*"))
    return {
        "tty_acm": [{"path": path, "realpath": os.path.realpath(path)} for path in tty_acm],
        "tty_usb": [{"path": path, "realpath": os.path.realpath(path)} for path in tty_usb],
        "samsung_by_id": [{"path": path, "realpath": os.path.realpath(path)} for path in by_id],
        "tty_acm0_present": "/dev/ttyACM0" in tty_acm,
        "any_acm_present": bool(tty_acm),
    }


def parse_listener_lines(stdout: str) -> list[str]:
    return [
        line
        for line in clean_lines(stdout)
        if f":{BRIDGE_PORT}" in line and "LISTEN" in line
    ]


def inspect_listener() -> dict[str, Any]:
    ss = run_host("ss_ltnp", ["ss", "-ltnp"])
    lines = parse_listener_lines(ss["stdout"])
    localhost_lines = [
        line
        for line in lines
        if f"{BRIDGE_HOST}:{BRIDGE_PORT}" in line
        or f"[::1]:{BRIDGE_PORT}" in line
        or f"localhost:{BRIDGE_PORT}" in line
    ]
    return {
        "command": {
            "available": ss["available"],
            "rc": ss["rc"],
            "stderr_lines": clean_lines(ss["stderr"])[:8],
        },
        "bridge_port": BRIDGE_PORT,
        "bridge_host": BRIDGE_HOST,
        "listener_lines": lines,
        "localhost_listener_lines": localhost_lines,
        "bridge_listener_present": bool(lines),
        "localhost_bridge_listener_present": bool(localhost_lines),
    }


def collect_locator(v1858: dict[str, Any]) -> dict[str, Any]:
    git_status = run_host("git_status", ["git", "status", "--short"])
    docs = inspect_docs()
    scripts = inspect_scripts()
    tty = inspect_tty()
    listener = inspect_listener()
    return {
        "v1858": {
            "path": rel(V1858_MANIFEST),
            "decision": v1858.get("decision", ""),
            "label": v1858.get("label", ""),
            "pass": bool(v1858.get("pass")),
        },
        "host": {
            "git_clean": git_status["rc"] == 0 and git_status["stdout"] == "",
            "git_status_lines": clean_lines(git_status["stdout"])[:20],
        },
        "docs": docs,
        "scripts": scripts,
        "tty": tty,
        "listener": listener,
        "safety": {
            "a90ctl_runtime_command_executed": False,
            "serial_bridge_started": False,
            "serial_bridge_tcp_connect_probe_executed": False,
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


def docs_ready(details: dict[str, Any]) -> bool:
    docs = details["docs"]
    return (
        docs["readme"]["mentions_tty_acm0"]
        and docs["readme"]["mentions_bridge_port"]
        and docs["readme"]["mentions_bridge_script"]
        and docs["bridge_guide"]["mentions_local_endpoint"]
        and docs["bridge_guide"]["mentions_a90ctl"]
        and docs["sudo_matrix"]["mentions_explicit_device"]
        and docs["sudo_matrix"]["mentions_read_only_bridge"]
    )


def scripts_ready(details: dict[str, Any]) -> bool:
    scripts = details["scripts"]
    return (
        scripts["a90ctl_path"]["repo_exists"]
        and scripts["a90ctl_path"]["help_rc"] == 0
        and scripts["serial_bridge"]["repo_exists"]
        and scripts["serial_bridge"]["help_rc"] == 0
        and scripts["serial_bridge"]["help_mentions_port"]
    )


def classify(details: dict[str, Any]) -> tuple[str, str, str, bool]:
    safety_clean = not any(details["safety"].values())
    input_ready = details["v1858"]["pass"] and details["v1858"]["label"] in {
        "host-ready-device-command-missing",
        "host-device-preflight-ready",
    }
    repo_scripts_ready = scripts_ready(details)
    docs_match = docs_ready(details)
    tty_ready = details["tty"]["tty_acm0_present"] or details["tty"]["any_acm_present"]
    bridge_ready = details["listener"]["localhost_bridge_listener_present"]

    if not input_ready:
        return "input-review", "v1859-input-review", "V1858 host preflight input is missing or not passing", False
    if not safety_clean:
        return "safety-review", "v1859-safety-review", "Transport locator claims a forbidden live action", False
    if not repo_scripts_ready or not docs_match:
        return (
            "transport-tooling-review",
            "v1859-transport-tooling-review",
            "Repo-local bridge tooling or documented endpoint expectations are incomplete",
            False,
        )
    if tty_ready and bridge_ready:
        return (
            "transport-locator-repo-bridge-ready",
            "v1859-transport-locator-repo-bridge-ready-host-pass",
            "Repo-local a90ctl/serial bridge tooling exists, an ACM tty is present, and localhost bridge port 54321 is already listening; V1858's PATH issue is narrowed to command invocation, not missing repo tooling",
            True,
        )
    if tty_ready:
        return (
            "transport-locator-start-bridge-needed",
            "v1859-transport-locator-start-bridge-needed-host-pass",
            "Repo-local tooling and ACM tty are present, but localhost bridge port 54321 is not listening",
            True,
        )
    return (
        "transport-locator-tty-missing",
        "v1859-transport-locator-tty-missing",
        "Repo-local tooling exists, but no ACM tty is visible from this host shell",
        False,
    )


def render_report(result: dict[str, Any]) -> str:
    details = result["details"]
    scripts = details["scripts"]
    tty = details["tty"]
    listener = details["listener"]
    docs = details["docs"]
    return "\n".join([
        "# Native Init V1859 Bridge Transport Locator",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: host-only locator for repo-local native-init bridge transport",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Input",
        "",
        f"- V1858: `{details['v1858']['decision']}` / `{details['v1858']['label']}` / pass `{details['v1858']['pass']}`",
        "",
        "## Tooling",
        "",
        f"- PATH `a90ctl`: `{scripts['a90ctl_path']['path_available']}` path `{scripts['a90ctl_path']['path_lookup']}`",
        f"- Repo `a90ctl.py`: `{scripts['a90ctl_path']['repo_exists']}` at `{scripts['a90ctl_path']['repo_path']}`, help rc `{scripts['a90ctl_path']['help_rc']}`",
        f"- Repo `serial_tcp_bridge.py`: `{scripts['serial_bridge']['repo_exists']}` at `{scripts['serial_bridge']['repo_path']}`, help rc `{scripts['serial_bridge']['help_rc']}`",
        "",
        "## Host Transport",
        "",
        f"- git clean: `{details['host']['git_clean']}`",
        f"- ACM tty present: `{tty['any_acm_present']}` entries `{tty['tty_acm']}`",
        f"- `/dev/ttyACM0` present: `{tty['tty_acm0_present']}`",
        f"- Samsung by-id entries: `{tty['samsung_by_id']}`",
        f"- localhost `{listener['bridge_host']}:{listener['bridge_port']}` listener: `{listener['localhost_bridge_listener_present']}`",
        f"- listener lines: `{listener['localhost_listener_lines'] or listener['listener_lines']}`",
        "",
        "## Documentation Cross-Check",
        "",
        f"- README bridge reference: tty `{docs['readme']['mentions_tty_acm0']}`, port `{docs['readme']['mentions_bridge_port']}`, script `{docs['readme']['mentions_bridge_script']}`",
        f"- Flash/bridge guide reference: endpoint `{docs['bridge_guide']['mentions_local_endpoint']}`, a90ctl `{docs['bridge_guide']['mentions_a90ctl']}`, tty `{docs['bridge_guide']['mentions_tty_acm0']}`",
        f"- Approval matrix reference: explicit tty command `{docs['sudo_matrix']['mentions_explicit_device']}`, read-only bridge row `{docs['sudo_matrix']['mentions_read_only_bridge']}`",
        "",
        "## Safety Scope",
        "",
        "Host-only. This locator did not run an `a90ctl` device command, start a serial bridge, open a TCP bridge client probe, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "- Use repo-local `python3 scripts/revalidation/a90ctl.py` instead of relying on PATH `a90ctl`.",
        "- Next useful live-adjacent unit is a read-only bridge identity/status smoke that redacts version creator text and checks only prerequisites such as WLFW service 69 and `wlan0` presence.",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "",
    ])


def main() -> int:
    details = collect_locator(load_json(V1858_MANIFEST))
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
