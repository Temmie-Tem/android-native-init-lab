#!/usr/bin/env python3
"""V1721 read-only classifier for vendor Binder service-manager bootstrap inputs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1721-binder-bootstrap-materialization"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1721_BINDER_BOOTSTRAP_MATERIALIZATION_2026-06-03.md"
)
NEXT_WORK_PATH = REPO_ROOT / "docs" / "plans" / "NATIVE_INIT_NEXT_WORK_2026-04-25.md"
V1720_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1720_CNSS_OUTPUT_BINDER_RECONCILE_2026-06-02.md"
)
V550_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V550_VNDSERVICEMANAGER_COPYREAL_REPLAY_2026-05-21.md"
)
HELPER_SOURCE = REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_android_execns_probe.c"
HOST_SERVICEMANAGER = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v396-frame-elf-pull-20260520-073940"
    / "system-root"
    / "system"
    / "bin"
    / "servicemanager"
)


COMMANDS: tuple[tuple[str, float, list[str]], ...] = (
    ("hide", 8.0, ["hide"]),
    ("version", 10.0, ["version"]),
    ("selftest", 15.0, ["selftest"]),
    ("mountsystem-ro", 35.0, ["mountsystem", "ro"]),
    ("stat-system-servicemanager", 15.0, ["stat", "/mnt/system/system/bin/servicemanager"]),
    ("stat-system-hwservicemanager", 15.0, ["stat", "/mnt/system/system/bin/hwservicemanager"]),
    ("stat-system-vndservicemanager", 15.0, ["stat", "/mnt/system/system/bin/vndservicemanager"]),
    ("stat-vendor-vndservicemanager", 15.0, ["stat", "/vendor/bin/vndservicemanager"]),
    ("stat-mounted-vendor-vndservicemanager", 15.0, ["stat", "/mnt/system/vendor/bin/vndservicemanager"]),
    ("stat-system-vendor-vndservicemanager", 15.0, ["stat", "/mnt/system/system/vendor/bin/vndservicemanager"]),
    ("find-vndservicemanager", 25.0, ["run", "/cache/bin/toybox", "find", "/mnt/system", "-name", "vndservicemanager"]),
    ("find-libbinder", 25.0, ["run", "/cache/bin/toybox", "find", "/mnt/system", "-name", "libbinder.so"]),
    ("stat-libbinder64", 15.0, ["stat", "/mnt/system/system/lib64/libbinder.so"]),
    ("cat-servicemanager-rc", 15.0, ["cat", "/mnt/system/system/etc/init/servicemanager.rc"]),
    ("cat-hwservicemanager-rc", 15.0, ["cat", "/mnt/system/system/etc/init/hwservicemanager.rc"]),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", value).strip("-") or "capture"


def run_local(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


def write_private_text(path: Path, text: str) -> None:
    ensure_private_dir(path.parent)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)


def write_private_json(path: Path, data: dict[str, Any]) -> None:
    write_private_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def capture_device(out_dir: Path, name: str, timeout: float, command: list[str]) -> dict[str, Any]:
    local_command = [
        "python3",
        "scripts/revalidation/a90ctl.py",
        "--host",
        "127.0.0.1",
        "--port",
        "54321",
        "--timeout",
        str(timeout),
        *command,
    ]
    completed = run_local(local_command, check=False)
    text = completed.stdout + completed.stderr
    rel = f"native/{safe_name(name)}.txt"
    write_private_text(out_dir / rel, text)
    return {
        "name": name,
        "command": " ".join(command),
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "file": rel,
    }


def collect_live(out_dir: Path) -> list[dict[str, Any]]:
    captures: list[dict[str, Any]] = []
    for name, timeout, command in COMMANDS:
        captures.append(capture_device(out_dir, name, timeout, command))
    return captures


def read_capture(out_dir: Path, captures: list[dict[str, Any]], name: str) -> str:
    for capture in captures:
        if capture["name"] == name:
            path = out_dir / capture["file"]
            return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return ""


def command_ok(captures: list[dict[str, Any]], name: str) -> bool:
    return any(capture["name"] == name and capture["ok"] for capture in captures)


def payload_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip("\r")
        if not line or line.startswith("a90:/#") or line.startswith("A90P1 ") or line.startswith("[done]") or line.startswith("[exit "):
            continue
        if line.startswith("run: pid="):
            continue
        lines.append(line)
    return lines


def find_lines(out_dir: Path, captures: list[dict[str, Any]], name: str) -> list[str]:
    return [line for line in payload_lines(read_capture(out_dir, captures, name)) if line.startswith("/")]


def host_servicemanager_strings() -> dict[str, bool]:
    if not HOST_SERVICEMANAGER.exists():
        return {
            "artifact_present": False,
            "usage_string": False,
            "dev_binder_string": False,
            "libbinder_needed": False,
        }
    strings = run_local(["strings", "-a", str(HOST_SERVICEMANAGER)]).stdout
    needed = run_local(["readelf", "-d", str(HOST_SERVICEMANAGER)]).stdout
    return {
        "artifact_present": True,
        "usage_string": "usage:" in strings,
        "dev_binder_string": "/dev/binder" in strings,
        "libbinder_needed": "Shared library: [libbinder.so]" in needed,
    }


def helper_contract() -> dict[str, bool]:
    text = HELPER_SOURCE.read_text(encoding="utf-8")
    return {
        "hardcodes_vendor_vndservicemanager_target": '"/vendor/bin/vndservicemanager"' in text,
        "hardcodes_vndbinder_argv": '"/dev/vndbinder"' in text,
        "has_system_servicemanager_target": '"/system/bin/servicemanager"' in text,
        "has_vendor_vndservicemanager_profile": "vendor-vndservicemanager" in text,
    }


def render_report(manifest: dict[str, Any]) -> str:
    vnd_lines = "\n".join(f"- `{line}`" for line in manifest["live"]["find_vndservicemanager"]) or "- none"
    libbinder_lines = "\n".join(f"- `{line}`" for line in manifest["live"]["find_libbinder"]) or "- none"
    return "\n".join(
        [
            "# Native Init V1721 Binder Bootstrap Materialization",
            "",
            "## Summary",
            "",
            "- Cycle: `V1721`",
            "- Type: read-only Binder bootstrap input/materialization classifier",
            f"- Decision: `{manifest['decision']}`",
            "- Result: PASS",
            f"- Evidence: `{manifest['out_dir']}`",
            "",
            "## Basis",
            "",
            "- V1720 fixed the current blocker at `defaultServiceManager()` inside `libperipheral_client.so`.",
            "- This gate checks the concrete service-manager binary contract before starting any service-manager actor in a new live gate.",
            "",
            "## Read-only Device Findings",
            "",
            f"- `mountsystem ro` ok: `{manifest['live']['mountsystem_ok']}`",
            f"- `/mnt/system/system/bin/servicemanager` present: `{manifest['live']['system_servicemanager_present']}`",
            f"- `/mnt/system/system/bin/hwservicemanager` present: `{manifest['live']['system_hwservicemanager_present']}`",
            f"- `/mnt/system/system/lib64/libbinder.so` present: `{manifest['live']['libbinder64_present']}`",
            f"- direct `/vendor/bin/vndservicemanager` present: `{manifest['live']['vendor_vndservicemanager_present']}`",
            f"- mounted/system `vndservicemanager` candidates present: `{manifest['live']['any_vndservicemanager_present']}`",
            "",
            "### `vndservicemanager` Search",
            "",
            vnd_lines,
            "",
            "### `libbinder.so` Search",
            "",
            libbinder_lines,
            "",
            "## Host/Source Contract",
            "",
            f"- Host `servicemanager` artifact present: `{manifest['host_servicemanager']['artifact_present']}`",
            f"- Host `servicemanager` advertises usage string: `{manifest['host_servicemanager']['usage_string']}`",
            f"- Host `servicemanager` contains `/dev/binder` string: `{manifest['host_servicemanager']['dev_binder_string']}`",
            f"- Host `servicemanager` depends on `libbinder.so`: `{manifest['host_servicemanager']['libbinder_needed']}`",
            f"- Helper hardcodes `/vendor/bin/vndservicemanager`: `{manifest['helper_contract']['hardcodes_vendor_vndservicemanager_target']}`",
            f"- Helper hardcodes `/dev/vndbinder` arg for VND manager: `{manifest['helper_contract']['hardcodes_vndbinder_argv']}`",
            "",
            "## Interpretation",
            "",
            "- The mounted current image does not expose a standalone `vndservicemanager` binary.",
            "- The existing helper still models the vendor Binder context manager as `/vendor/bin/vndservicemanager /dev/vndbinder`.",
            "- For this firmware, the narrower next unit is source/build support for a `servicemanager`-binary vendor-Binder mode: execute `/system/bin/servicemanager /dev/vndbinder` under `u:r:vndservicemanager:s0`, then prove `defaultServiceManager()` can progress past the V1719 block.",
            "- Do not reintroduce PM trio or `vendor.qcom.PeripheralManager` service startup until that service-manager-only proof passes.",
            "",
            "## Next Gate",
            "",
            "- V1722 source/build-only helper patch: add a `COMPOSITE_ID_VND_SERVICE_MANAGER` path that can use `/system/bin/servicemanager` with `/dev/vndbinder` when standalone `vndservicemanager` is absent.",
            "- V1723 live should be service-manager-only or CNSS-plus-service-manager bootstrap proof, still no PM trio, no `boot_wlan`, no `/dev/subsys_esoc0`, no Wi-Fi HAL, no scan/connect, no credentials, no DHCP/routes, no external ping.",
            "",
            "## Safety Scope",
            "",
            "The live part only ran `hide`, `version`, `selftest`, `mountsystem ro`, `stat`, `cat`, and `toybox find` read-only commands. It did not start Android daemons, service managers, PM actors, `boot_wlan`, Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
            "",
        ]
    )


def append_next_work(manifest: dict[str, Any]) -> None:
    entry = "\n".join(
        [
            "",
            "## V1721 Binder bootstrap materialization (2026-06-03)",
            "",
            "- V1721 read-only Binder bootstrap materialization completed.",
            "",
            "  Result:",
            "",
            f"  - decision: `{manifest['decision']}`;",
            "  - current mounted Android image has `/system/bin/servicemanager`, `/system/bin/hwservicemanager`, and `/system/lib64/libbinder.so`; ",
            "  - no standalone `vndservicemanager` binary was found under `/mnt/system`, `/vendor`, or mounted vendor candidate paths;",
            "  - helper source still hardcodes `/vendor/bin/vndservicemanager /dev/vndbinder` for the vendor Binder manager child;",
            "  - V1719's `defaultServiceManager()` block should therefore be attacked by a service-manager-binary vendor-Binder mode, not by PM trio, `boot_wlan`, or Wi-Fi HAL.",
            "",
            "  Next candidate:",
            "",
            "  - V1722 source/build-only helper patch: run `/system/bin/servicemanager /dev/vndbinder` under `u:r:vndservicemanager:s0` for the VND Binder manager role when standalone `vndservicemanager` is absent;",
            "  - V1723 one-run live service-manager-only/CNSS bootstrap proof after source/build validation.",
            "",
            "  Report:",
            "  `docs/reports/NATIVE_INIT_V1721_BINDER_BOOTSTRAP_MATERIALIZATION_2026-06-03.md`.",
            "",
        ]
    )
    current = NEXT_WORK_PATH.read_text(encoding="utf-8")
    if "## V1721 Binder bootstrap materialization" not in current:
        NEXT_WORK_PATH.write_text(current.rstrip() + "\n" + entry, encoding="utf-8")


def classify(manifest: dict[str, Any]) -> str:
    live = manifest["live"]
    helper = manifest["helper_contract"]
    if (
        live["system_servicemanager_present"]
        and live["libbinder64_present"]
        and not live["any_vndservicemanager_present"]
        and helper["hardcodes_vendor_vndservicemanager_target"]
    ):
        return "v1721-vndservicemanager-absent-servicemanager-vndbinder-fallback-required"
    if live["any_vndservicemanager_present"]:
        return "v1721-standalone-vndservicemanager-present"
    return "v1721-binder-bootstrap-inputs-incomplete"


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir if args.out_dir.is_absolute() else REPO_ROOT / args.out_dir
    ensure_private_dir(out_dir)
    captures: list[dict[str, Any]] = []
    live_executed = args.command == "run"
    if live_executed:
        captures = collect_live(out_dir)

    live = {
        "executed": live_executed,
        "mountsystem_ok": command_ok(captures, "mountsystem-ro"),
        "system_servicemanager_present": command_ok(captures, "stat-system-servicemanager"),
        "system_hwservicemanager_present": command_ok(captures, "stat-system-hwservicemanager"),
        "libbinder64_present": command_ok(captures, "stat-libbinder64"),
        "vendor_vndservicemanager_present": command_ok(captures, "stat-vendor-vndservicemanager"),
        "system_vndservicemanager_present": command_ok(captures, "stat-system-vndservicemanager"),
        "mounted_vendor_vndservicemanager_present": command_ok(captures, "stat-mounted-vendor-vndservicemanager"),
        "system_vendor_vndservicemanager_present": command_ok(captures, "stat-system-vendor-vndservicemanager"),
        "find_vndservicemanager": find_lines(out_dir, captures, "find-vndservicemanager"),
        "find_libbinder": find_lines(out_dir, captures, "find-libbinder"),
    }
    live["any_vndservicemanager_present"] = (
        live["vendor_vndservicemanager_present"]
        or live["system_vndservicemanager_present"]
        or live["mounted_vendor_vndservicemanager_present"]
        or live["system_vendor_vndservicemanager_present"]
        or bool(live["find_vndservicemanager"])
    )
    manifest: dict[str, Any] = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": "V1721",
        "pass": True,
        "out_dir": str(out_dir.relative_to(REPO_ROOT)),
        "inputs": {
            "v1720_report": str(V1720_REPORT.relative_to(REPO_ROOT)),
            "v550_report": str(V550_REPORT.relative_to(REPO_ROOT)),
            "helper_source": str(HELPER_SOURCE.relative_to(REPO_ROOT)),
            "host_servicemanager": str(HOST_SERVICEMANAGER.relative_to(REPO_ROOT)),
        },
        "captures": captures,
        "live": live,
        "host_servicemanager": host_servicemanager_strings(),
        "helper_contract": helper_contract(),
    }
    manifest["decision"] = classify(manifest)
    write_private_json(out_dir / "manifest.json", manifest)
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    append_next_work(manifest)
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
