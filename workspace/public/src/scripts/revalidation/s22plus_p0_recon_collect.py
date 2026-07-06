#!/usr/bin/env python3
"""Collect read-only S22+ P0 native-init recon artifacts.

This helper intentionally performs no partition writes, no reboot, and no device
state mutation.  It pins a single adb target, verifies the expected SM-S906N/g0q
identity, then captures the shipped kernel config, module inventory, and current
boot-related partition hashes into a private run directory.
"""

from __future__ import annotations

import argparse
import gzip
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_RUN_ROOT = Path("workspace/private/runs")
EXPECTED_MODEL = "SM-S906N"
EXPECTED_DEVICE = "g0q"

CONFIG_KEYS = [
    "CONFIG_NET_NS",
    "CONFIG_OVERLAY_FS",
    "CONFIG_VETH",
    "CONFIG_BRIDGE",
    "CONFIG_TUN",
    "CONFIG_WIREGUARD",
    "CONFIG_CGROUPS",
    "CONFIG_NAMESPACES",
    "CONFIG_USER_NS",
    "CONFIG_SECCOMP",
    "CONFIG_SECCOMP_FILTER",
    "CONFIG_PID_NS",
    "CONFIG_UTS_NS",
    "CONFIG_IPC_NS",
    "CONFIG_SECURITY_SELINUX",
    "CONFIG_SECURITY_APPARMOR",
    "CONFIG_MODULES",
    "CONFIG_MODULE_UNLOAD",
    "CONFIG_DEVTMPFS",
    "CONFIG_TMPFS",
]

SAMSUNG_SECURITY_PATTERNS = (
    "RKP",
    "KDP",
    "PROCA",
    "FIVE",
    "DEFEX",
    "KNOX",
    "UH",
)


def run(
    argv: list[str],
    *,
    text: bool = True,
    check: bool = False,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        argv,
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
    )


def adb(serial: str, *args: str, text: bool = True) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    return run(["adb", "-s", serial, *args], text=text)


def shell(serial: str, command: str) -> subprocess.CompletedProcess[str]:
    return adb(serial, "shell", command, text=True)  # type: ignore[return-value]


def write_result(path: Path, result: subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]) -> None:
    if isinstance(result.stdout, bytes):
        path.write_bytes(result.stdout)
        if result.stderr:
            path.with_suffix(path.suffix + ".stderr").write_bytes(result.stderr)
    else:
        path.write_text(result.stdout, encoding="utf-8", errors="replace")
        if result.stderr:
            path.with_suffix(path.suffix + ".stderr").write_text(
                result.stderr, encoding="utf-8", errors="replace"
            )
    path.with_suffix(path.suffix + ".rc").write_text(f"{result.returncode}\n", encoding="ascii")


def parse_adb_devices(output: str) -> list[str]:
    serials: list[str] = []
    for line in output.splitlines():
        if "\tdevice" in line or " device " in line:
            serials.append(line.split()[0])
    return serials


def select_serial(requested: str | None) -> str:
    if requested:
        return requested
    result = run(["adb", "devices", "-l"], text=True, check=True)
    serials = parse_adb_devices(result.stdout)  # type: ignore[arg-type]
    if len(serials) != 1:
        raise SystemExit(
            f"expected exactly one adb device or pass --serial; found {len(serials)}"
        )
    return serials[0]


def props_map(raw: str) -> dict[str, str]:
    keys = [
        "ro.product.model",
        "ro.product.device",
        "ro.product.name",
        "ro.boot.bootloader",
        "ro.boot.verifiedbootstate",
        "ro.boot.vbmeta.device_state",
        "ro.boot.flash.locked",
        "ro.boot.warranty_bit",
        "sys.boot_completed",
        "persist.sys.safemode",
    ]
    values = raw.splitlines()
    return {key: values[idx] if idx < len(values) else "" for idx, key in enumerate(keys)}


def parse_config(text: str) -> dict[str, str]:
    config: dict[str, str] = {}
    for line in text.splitlines():
        if not line:
            continue
        if line.startswith("# CONFIG_") and line.endswith(" is not set"):
            key = line.split()[1]
            config[key] = "not set"
        elif line.startswith("CONFIG_") and "=" in line:
            key, value = line.split("=", 1)
            config[key] = value
    return config


def collect_proc_config(serial: str, run_dir: Path) -> tuple[str, dict[str, str], list[str]]:
    raw = adb(serial, "exec-out", "cat", "/proc/config.gz", text=False)  # type: ignore[assignment]
    write_result(run_dir / "proc_config.gz", raw)
    config_text = ""
    if raw.returncode == 0 and raw.stdout:
        try:
            config_text = gzip.decompress(raw.stdout).decode("utf-8", errors="replace")  # type: ignore[arg-type]
        except OSError:
            config_text = raw.stdout.decode("utf-8", errors="replace")  # type: ignore[union-attr]
    (run_dir / "proc_config.txt").write_text(config_text, encoding="utf-8", errors="replace")
    config = parse_config(config_text)
    samsung_hits = sorted(
        key
        for key in config
        if any(pattern in key for pattern in SAMSUNG_SECURITY_PATTERNS)
    )
    return config_text, config, samsung_hits


def collect_text(serial: str, run_dir: Path, name: str, command: str) -> str:
    result = shell(serial, command)
    write_result(run_dir / name, result)
    return result.stdout


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", help="adb serial to pin; required if multiple devices are connected")
    parser.add_argument("--run-dir", type=Path, help="private output directory")
    parser.add_argument("--expect-model", default=EXPECTED_MODEL)
    parser.add_argument("--expect-device", default=EXPECTED_DEVICE)
    args = parser.parse_args(argv)

    serial = select_serial(args.serial)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.run_dir or (DEFAULT_RUN_ROOT / f"s22plus_p0_recon_{timestamp}")
    run_dir.mkdir(parents=True, exist_ok=False)

    devices = run(["adb", "devices", "-l"], text=True, check=True)
    write_result(run_dir / "adb_devices.txt", devices)

    prop_command = (
        "getprop ro.product.model; "
        "getprop ro.product.device; "
        "getprop ro.product.name; "
        "getprop ro.boot.bootloader; "
        "getprop ro.boot.verifiedbootstate; "
        "getprop ro.boot.vbmeta.device_state; "
        "getprop ro.boot.flash.locked; "
        "getprop ro.boot.warranty_bit; "
        "getprop sys.boot_completed; "
        "getprop persist.sys.safemode"
    )
    props_raw = collect_text(serial, run_dir, "props.txt", prop_command)
    props = props_map(props_raw)
    if props.get("ro.product.model") != args.expect_model or props.get("ro.product.device") != args.expect_device:
        raise SystemExit(
            "target identity mismatch: "
            f"model={props.get('ro.product.model')!r} device={props.get('ro.product.device')!r}"
        )

    collect_text(serial, run_dir, "root_id.txt", "su -c id")
    collect_text(serial, run_dir, "uname.txt", "uname -a")
    collect_text(serial, run_dir, "cmdline.txt", "su -c 'cat /proc/cmdline 2>/dev/null || true'")
    collect_text(
        serial,
        run_dir,
        "partition_sha256.txt",
        "su -c 'sha256sum /dev/block/by-name/boot /dev/block/by-name/vendor_boot "
        "/dev/block/by-name/recovery /dev/block/by-name/vbmeta /dev/block/by-name/vbmeta_system 2>/dev/null'",
    )
    collect_text(serial, run_dir, "proc_modules.txt", "cat /proc/modules 2>/dev/null || true")
    collect_text(
        serial,
        run_dir,
        "module_inventory.txt",
        "for d in /vendor/lib/modules /vendor_dlkm/lib/modules /system/lib/modules /odm/lib/modules; do "
        "[ -d \"$d\" ] && find \"$d\" -maxdepth 3 -type f | sort; "
        "done",
    )
    collect_text(
        serial,
        run_dir,
        "module_metadata.txt",
        "for f in "
        "/vendor/lib/modules/modules.load /vendor/lib/modules/modules.dep /vendor/lib/modules/modules.order "
        "/vendor_dlkm/lib/modules/modules.load /vendor_dlkm/lib/modules/modules.dep /vendor_dlkm/lib/modules/modules.order "
        "/odm/lib/modules/modules.load /odm/lib/modules/modules.dep /odm/lib/modules/modules.order; do "
        "[ -f \"$f\" ] && echo '###' \"$f\" && su -c \"cat $f\"; "
        "done",
    )
    collect_text(
        serial,
        run_dir,
        "container_readiness_probe.txt",
        "printf 'dev_net_tun='; [ -e /dev/net/tun ] && echo yes || echo no; "
        "printf 'proc_filesystems\\n'; cat /proc/filesystems; "
        "printf 'proc_self_ns\\n'; ls -l /proc/self/ns 2>/dev/null || true; "
        "printf 'cgroups\\n'; cat /proc/cgroups 2>/dev/null || true",
    )

    _, config, samsung_hits = collect_proc_config(serial, run_dir)
    module_inventory = (run_dir / "module_inventory.txt").read_text(
        encoding="utf-8", errors="replace"
    )
    module_files = [line for line in module_inventory.splitlines() if line.endswith(".ko")]
    loaded_modules = [
        line.split()[0]
        for line in (run_dir / "proc_modules.txt").read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip()
    ]
    selected_config = {key: config.get(key, "missing") for key in CONFIG_KEYS}
    summary = {
        "timestamp_utc": timestamp,
        "device": {
            "serial_redacted": True,
            "model": props.get("ro.product.model", ""),
            "device": props.get("ro.product.device", ""),
            "name": props.get("ro.product.name", ""),
            "bootloader": props.get("ro.boot.bootloader", ""),
            "verifiedbootstate": props.get("ro.boot.verifiedbootstate", ""),
            "vbmeta_device_state": props.get("ro.boot.vbmeta.device_state", ""),
            "flash_locked": props.get("ro.boot.flash.locked", ""),
            "warranty_bit": props.get("ro.boot.warranty_bit", ""),
            "boot_completed": props.get("sys.boot_completed", ""),
            "safemode": props.get("persist.sys.safemode", ""),
        },
        "selected_config": selected_config,
        "samsung_security_config_hits": samsung_hits,
        "module_file_count": len(module_files),
        "loaded_module_count": len(loaded_modules),
        "loaded_modules": loaded_modules,
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(run_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
