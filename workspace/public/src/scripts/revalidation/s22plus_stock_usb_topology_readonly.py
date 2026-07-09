#!/usr/bin/env python3
"""Collect a serial-redacted S22+ stock USB topology without device writes."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_MODEL = "SM-S906N"
EXPECTED_DEVICE = "g0q"
EXPECTED_INCREMENTAL = "S906NKSS7FYG8"
EXPECTED_USB_ID = "04e8:6860"
DEFAULT_RUN_ROOT = Path("workspace/private/runs")
DEFAULT_PUBLISH = Path("docs/module-map/s22plus-fyg8/stock-usb-runtime-topology.json")

SERIAL_RE = re.compile(r"RFCT[0-9A-Z]+")
UDEV_SERIAL_RE = re.compile(r"(?m)^(?:ID_(?:USB_)?SERIAL(?:_SHORT)?=).*$")
MAC_RE = re.compile(r"(?<![0-9A-Fa-f])(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}(?![0-9A-Fa-f])")

PROPERTIES = (
    "ro.product.model",
    "ro.product.device",
    "ro.build.version.incremental",
    "sys.boot_completed",
    "init.svc.bootanim",
    "sys.usb.config",
    "sys.usb.state",
    "sys.usb.configured",
    "sys.usb.controller",
    "init.svc.DR-daemon",
    "init.svc.adbd",
)

DEVICE_COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("devnull_stat", ("stat", "-c", "%F|%a|%t:%T|%s|%C", "/dev/null")),
    ("root_id", ("su", "-c", "id")),
    ("root_boot_sha256", ("su", "-c", "sha256sum /dev/block/by-name/boot")),
    ("proc_modules", ("cat", "/proc/modules")),
    ("dumpsys_usb", ("dumpsys", "usb")),
    ("cmd_usb_functions", ("cmd", "usb", "get-functions")),
    ("udc_class", ("su", "-c", "ls -la /sys/class/udc")),
    ("typec_class", ("su", "-c", "ls -la /sys/class/typec")),
    ("extcon_class", ("su", "-c", "ls -la /sys/class/extcon")),
    ("usb_role_class", ("su", "-c", "ls -la /sys/class/usb_role")),
    ("ssusb_platform", ("ls", "-la", "/sys/devices/platform/soc/a600000.ssusb")),
    (
        "dwc3_platform",
        ("ls", "-la", "/sys/devices/platform/soc/a600000.ssusb/a600000.dwc3"),
    ),
    (
        "ssusb_driver",
        ("readlink", "-f", "/sys/devices/platform/soc/a600000.ssusb/driver"),
    ),
    (
        "dwc3_driver",
        (
            "readlink",
            "-f",
            "/sys/devices/platform/soc/a600000.ssusb/a600000.dwc3/driver",
        ),
    ),
    (
        "ssusb_of_node",
        ("su", "-c", "readlink -f /sys/devices/platform/soc/a600000.ssusb/of_node"),
    ),
    (
        "dwc3_of_node",
        (
            "su",
            "-c",
            "readlink -f /sys/devices/platform/soc/a600000.ssusb/a600000.dwc3/of_node",
        ),
    ),
    (
        "ssusb_role",
        ("su", "-c", "cat /sys/class/usb_role/a600000.ssusb-role-switch/role"),
    ),
    (
        "dwc3_role_object",
        ("su", "-c", "ls -la /sys/class/usb_role/a600000.dwc3-role-switch/"),
    ),
    ("udc_state", ("su", "-c", "cat /sys/class/udc/a600000.dwc3/state")),
    ("typec_port_path", ("su", "-c", "readlink -f /sys/class/typec/port0")),
    ("typec_driver", ("su", "-c", "readlink -f /sys/class/typec/port0/device/driver")),
    ("typec_data_role", ("su", "-c", "cat /sys/class/typec/port0/data_role")),
    ("typec_power_role", ("su", "-c", "cat /sys/class/typec/port0/power_role")),
    ("typec_port_type", ("su", "-c", "cat /sys/class/typec/port0/port_type")),
    ("gadget_udc", ("su", "-c", "cat /config/usb_gadget/g1/UDC")),
)


class TopologyError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def redact(text: str, serial: str | None = None) -> str:
    if serial:
        text = text.replace(serial, "<S22_SERIAL_REDACTED>")
    text = SERIAL_RE.sub("<S22_SERIAL_REDACTED>", text)
    text = UDEV_SERIAL_RE.sub(lambda match: match.group(0).split("=", 1)[0] + "=<S22_SERIAL_REDACTED>", text)
    return MAC_RE.sub("<REDACTED_MAC>", text)


def run(argv: list[str], *, serial: str | None = None, timeout: float = 30.0) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            argv,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "argv": [redact(value, serial) for value in argv],
            "rc": completed.returncode,
            "stdout": redact(completed.stdout, serial),
            "stderr": redact(completed.stderr, serial),
            "timeout": False,
        }
    except FileNotFoundError as exc:
        return {"argv": argv, "rc": 127, "stdout": "", "stderr": str(exc), "timeout": False}
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": [redact(value, serial) for value in argv],
            "rc": 124,
            "stdout": redact(exc.stdout or "", serial),
            "stderr": redact(exc.stderr or "", serial),
            "timeout": True,
        }


def parse_adb_devices(text: str) -> list[str]:
    devices: list[str] = []
    for line in text.splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 2 and fields[1] == "device":
            devices.append(fields[0])
    return devices


def select_serial(requested: str | None) -> str:
    try:
        completed = subprocess.run(
            ["adb", "devices"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15.0,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise TopologyError(f"adb devices failed: {exc}") from exc
    if completed.returncode != 0:
        raise TopologyError(f"adb devices failed: {completed.stderr}")
    devices = parse_adb_devices(completed.stdout)
    if requested:
        if requested not in devices:
            raise TopologyError("requested ADB serial is not connected")
        return requested
    if len(devices) != 1:
        raise TopologyError(f"expected exactly one ADB device, found {len(devices)}")
    return devices[0]


def adb_command(serial: str, argv: tuple[str, ...], *, timeout: float = 30.0) -> dict[str, Any]:
    return run(["adb", "-s", serial, "exec-out", *argv], serial=serial, timeout=timeout)


def collect_properties(serial: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for name in PROPERTIES:
        result = adb_command(serial, ("getprop", name))
        if result["rc"] != 0:
            raise TopologyError(f"getprop failed for {name}: {result['stderr']}")
        values[name] = result["stdout"].strip()
    return values


def find_host_usb() -> Path | None:
    root = Path("/sys/bus/usb/devices")
    for device in sorted(root.iterdir()) if root.is_dir() else []:
        try:
            vendor = (device / "idVendor").read_text(encoding="ascii").strip()
            product = (device / "idProduct").read_text(encoding="ascii").strip()
        except (FileNotFoundError, PermissionError, OSError):
            continue
        if f"{vendor}:{product}" == EXPECTED_USB_ID:
            return device.resolve()
    return None


def has_flag(text: str, key: str, value: str) -> bool:
    return bool(
        re.search(
            rf"(?m)^\s*{re.escape(key)}\s*(?:=|:)\s*{re.escape(value)}\s*$",
            text,
        )
    )


def symlink_target(listing: str, name: str) -> str:
    match = re.search(rf"(?m)\b{re.escape(name)} -> ([^\s]+)$", listing)
    return match.group(1) if match else "UNAVAILABLE"


def bracketed_current(text: str) -> str:
    match = re.search(r"\[([^\]]+)\]", text)
    return match.group(1) if match else "UNAVAILABLE"


def summarize(
    properties: dict[str, str],
    commands: dict[str, dict[str, Any]],
    host: dict[str, Any],
) -> dict[str, Any]:
    dumpsys = commands["dumpsys_usb"]["stdout"]
    modules = commands["proc_modules"]["stdout"]
    devnull_fields = commands["devnull_stat"]["stdout"].strip().split("|")
    devnull_ok = (
        commands["devnull_stat"]["rc"] == 0
        and len(devnull_fields) >= 4
        and devnull_fields[0] in {"character device", "character special file"}
        and devnull_fields[1] == "666"
        and devnull_fields[2] == "1:3"
        and devnull_fields[3] == "0"
    )
    role_listing = commands["usb_role_class"]["stdout"]
    denials = sorted(
        label
        for label, result in commands.items()
        if result["rc"] != 0 or "Permission denied" in result["stderr"] + result["stdout"]
    )
    identity_ok = (
        properties["ro.product.model"] == EXPECTED_MODEL
        and properties["ro.product.device"] == EXPECTED_DEVICE
        and properties["ro.build.version.incremental"] == EXPECTED_INCREMENTAL
    )
    stock_state = {
        "identity_exact": identity_ok,
        "boot_completed": properties["sys.boot_completed"] == "1",
        "bootanim_stopped": properties["init.svc.bootanim"] == "stopped",
        "devnull_char_1_3": devnull_ok,
        "magisk_root": "uid=0(root)" in commands["root_id"]["stdout"],
        "boot_sha256": (
            commands["root_boot_sha256"]["stdout"].split()[0]
            if commands["root_boot_sha256"]["rc"] == 0
            and commands["root_boot_sha256"]["stdout"].split()
            else "READ_DENIED"
        ),
    }
    usb_manager = {
        "connected": has_flag(dumpsys, "connected", "true"),
        "configured": has_flag(dumpsys, "configured", "true"),
        "current_mode_ufp": has_flag(dumpsys, "current_mode", "ufp"),
        "power_role_sink": has_flag(dumpsys, "power_role", "sink"),
        "data_role_device": has_flag(dumpsys, "data_role", "device"),
        "supported_modes_dual": has_flag(dumpsys, "supported_modes", "dual"),
        "device_connected": has_flag(dumpsys, "IsDeviceConnected", "true"),
    }
    ssusb_of_node = commands["ssusb_of_node"]["stdout"].strip() or symlink_target(
        commands["ssusb_platform"]["stdout"], "of_node"
    )
    dwc3_of_node = commands["dwc3_of_node"]["stdout"].strip() or symlink_target(
        commands["dwc3_platform"]["stdout"], "of_node"
    )
    sysfs = {
        "ssusb_driver": commands["ssusb_driver"]["stdout"].strip(),
        "dwc3_driver": commands["dwc3_driver"]["stdout"].strip(),
        "ssusb_of_node": ssusb_of_node,
        "dwc3_of_node": dwc3_of_node,
        "ssusb_role_switch_present": "a600000.ssusb-role-switch" in role_listing,
        "dwc3_role_switch_present": "a600000.dwc3-role-switch" in role_listing,
        "ssusb_role": commands["ssusb_role"]["stdout"].strip(),
        "udc_state": commands["udc_state"]["stdout"].strip(),
        "gadget_udc": commands["gadget_udc"]["stdout"].strip(),
        "ssusb_suppliers": sorted(set(re.findall(r"supplier:[^\s]+", commands["ssusb_platform"]["stdout"]))),
        "dwc3_suppliers": sorted(set(re.findall(r"supplier:[^\s]+", commands["dwc3_platform"]["stdout"]))),
        "read_denials": denials,
    }
    typec_path = commands["typec_port_path"]["stdout"].strip()
    typec_driver = commands["typec_driver"]["stdout"].strip()
    typec_state = {
        "port_path": typec_path,
        "driver": typec_driver,
        "data_role": bracketed_current(commands["typec_data_role"]["stdout"]),
        "power_role": bracketed_current(commands["typec_power_role"]["stdout"]),
        "port_type": bracketed_current(commands["typec_port_type"]["stdout"]),
        "max77705_usbc_provider": (
            "max77705-usbc" in typec_path and typec_driver.endswith("/max77705-usbc")
        ),
    }
    extcon_entries = sorted(
        set(re.findall(r"extcon\d+ -> ([^\s]+)", commands["extcon_class"]["stdout"]))
    )
    modules_state = {
        "dwc3_msm_loaded": bool(re.search(r"(?m)^dwc3_msm\s", modules)),
        "sec_log_buf_loaded": bool(re.search(r"(?m)^sec_log_buf\s", modules)),
        "sec_debug_loaded": bool(re.search(r"(?m)^sec_debug\s", modules)),
    }
    required = [
        stock_state["identity_exact"],
        stock_state["boot_completed"],
        stock_state["bootanim_stopped"],
        stock_state["devnull_char_1_3"],
        stock_state["magisk_root"],
        usb_manager["connected"],
        usb_manager["configured"],
        usb_manager["current_mode_ufp"],
        usb_manager["power_role_sink"],
        usb_manager["data_role_device"],
        sysfs["ssusb_driver"].endswith("/msm-dwc3"),
        sysfs["dwc3_driver"].endswith("/dwc3"),
        sysfs["ssusb_role_switch_present"],
        sysfs["dwc3_role_switch_present"],
        sysfs["ssusb_role"] == "device",
        sysfs["udc_state"] == "configured",
        sysfs["gadget_udc"] == "a600000.dwc3",
        typec_state["data_role"] == "device",
        typec_state["power_role"] == "sink",
        typec_state["port_type"] == "dual",
        typec_state["max77705_usbc_provider"],
        host.get("usb_id") == EXPECTED_USB_ID,
    ]
    return {
        "result": "pass-stock-topology-partial" if all(required) else "fail",
        "target": TARGET,
        "stock_state": stock_state,
        "usb_manager": usb_manager,
        "sysfs": sysfs,
        "typec": typec_state,
        "extcon_entries": extcon_entries,
        "modules": modules_state,
        "host": host,
        "conclusions": {
            "stock_dwc3_device_path": "LIVE_BOUND" if all(required) else "UNVERIFIABLE",
            "role_switch_objects": "LIVE_OBSERVED" if sysfs["ssusb_role_switch_present"] else "UNVERIFIABLE",
            "max77705_typec_port": "LIVE_BOUND" if typec_state["max77705_usbc_provider"] else "UNVERIFIABLE",
            "max77705_to_dwc3_role_propagation": "UNVERIFIABLE",
            "extcon_attachment": "UNVERIFIABLE",
            "direct_pid1_path": "UNVERIFIABLE",
        },
    }


def collect(serial: str) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    properties = collect_properties(serial)
    commands = {
        label: adb_command(serial, argv, timeout=60.0 if label == "dumpsys_usb" else 30.0)
        for label, argv in DEVICE_COMMANDS
    }
    host_usb = find_host_usb()
    host: dict[str, Any] = {"usb_id": "", "sysfs_path": "", "udev": {}}
    if host_usb is not None:
        vendor = (host_usb / "idVendor").read_text(encoding="ascii").strip()
        product = (host_usb / "idProduct").read_text(encoding="ascii").strip()
        udev = run(["udevadm", "info", "--query=property", f"--path={host_usb}"])
        host = {
            "usb_id": f"{vendor}:{product}",
            "sysfs_path": str(host_usb),
            "udev": {
                line.split("=", 1)[0]: line.split("=", 1)[1]
                for line in udev["stdout"].splitlines()
                if "=" in line and line.split("=", 1)[0] in {"ID_USB_INTERFACES", "ID_USB_DRIVER", "DEVTYPE"}
            },
        }
    return summarize(properties, commands, host), commands


def allocate_run_dir(base: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = base / f"s22plus_stock_usb_topology_readonly_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def offline_check() -> dict[str, Any]:
    command_text = "\n".join(" ".join(argv) for _label, argv in DEVICE_COMMANDS)
    forbidden = (
        "adb reboot",
        "finit_module",
        "insmod",
        "rmmod",
        "ctl.stop",
        "ctl.start",
        "tee /sys",
        "> /sys",
        "> /config",
    )
    root_read_programs = {"cat", "id", "ls", "readlink", "sha256sum"}
    direct_read_programs = {"cat", "cmd", "dumpsys", "ls", "readlink", "stat"}
    fixed_read_commands: dict[str, bool] = {}
    for label, argv in DEVICE_COMMANDS:
        safe = bool(argv) and argv[0] in direct_read_programs
        if argv and argv[0] == "su":
            try:
                shell_argv = shlex.split(argv[2]) if len(argv) == 3 and argv[1] == "-c" else []
            except ValueError:
                shell_argv = []
            safe = bool(shell_argv) and shell_argv[0] in root_read_programs
            safe = safe and not any(token in argv[2] for token in (";", "|", "&", ">", "<", "`", "$("))
        fixed_read_commands[label] = safe
    contract_pass = not any(token in command_text for token in forbidden) and all(
        fixed_read_commands.values()
    )
    return {
        "result": "pass" if contract_pass else "fail",
        "target": TARGET,
        "device_command_count": len(DEVICE_COMMANDS),
        "fixed_read_commands": fixed_read_commands,
        "forbidden_tokens_absent": {token: token not in command_text for token in forbidden},
        "safety": {
            "device_read_only": True,
            "flash": False,
            "reboot": False,
            "module_insertion": False,
            "service_control": False,
            "sysfs_write": False,
            "configfs_write": False,
            "partition_write": False,
            "serial_redacted": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--serial")
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--publish", type=Path, default=DEFAULT_PUBLISH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    contract = offline_check()
    if contract["result"] != "pass":
        print(json.dumps(contract, indent=2, sort_keys=True))
        return 1
    if not args.collect:
        print(json.dumps(contract, indent=2, sort_keys=True))
        return 0
    serial = select_serial(args.serial)
    run_dir = allocate_run_dir(resolve(args.run_root))
    summary, commands = collect(serial)
    summary.update(
        {
            "schema": "s22plus_stock_usb_topology_readonly_v1",
            "captured_at_utc": utc_now(),
            "serial": "<S22_SERIAL_REDACTED>",
            "private_run": rel(run_dir),
            "safety": contract["safety"],
        }
    )
    write_json(run_dir / "summary.json", summary)
    write_json(run_dir / "commands.json", commands)
    write_json(resolve(args.publish), summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["result"].startswith("pass") else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TopologyError as exc:
        print(f"topology collection failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
