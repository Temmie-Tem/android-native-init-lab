#!/usr/bin/env python3
"""Collect rooted Android boot-capture evidence for S22+ native-init planning.

The collector is read-only.  It verifies the SM-S906N/g0q target, requires
Magisk root, then captures the vendor Android bring-up state that a future
native PID1 must reproduce for observability: module metadata/load state, dmesg,
USB gadget/configfs state, display/DRM/KGSL state, and boot timing props.

Raw artifacts stay under workspace/private/runs because they can contain serials,
USB IDs, MACs, command lines, and other device identifiers.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_RUN_ROOT = Path("workspace/private/runs")
EXPECTED_MODEL = "SM-S906N"
EXPECTED_DEVICE = "g0q"
EXPECTED_BUILD = "S906NKSS7FYG8"

KEY_DMESG_PATTERNS = {
    "usb": re.compile(r"usb|dwc3|gadget|configfs|adbd|ffs|mtp|rndis|ncm", re.IGNORECASE),
    "display": re.compile(r"drm|dsi|panel|sde|display|kgsl|adreno|gpu|dispcc|gpucc", re.IGNORECASE),
    "module": re.compile(r"module|insmod|dlkm|firmware", re.IGNORECASE),
    "pstore": re.compile(r"pstore|ramoops|console-ramoops", re.IGNORECASE),
}


def run(argv: list[str], *, text: bool = True, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
        timeout=timeout,
    )


def adb(serial: str, *args: str, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    return run(["adb", "-s", serial, *args], timeout=timeout)


def shell(serial: str, command: str, *, timeout: float | None = 60.0) -> subprocess.CompletedProcess[str]:
    return adb(serial, "shell", command, timeout=timeout)


def su_shell(serial: str, command: str, *, timeout: float | None = 60.0) -> subprocess.CompletedProcess[str]:
    return shell(serial, f"su -c {sh_quote(command)}", timeout=timeout)


def sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def write_result(path: Path, result: subprocess.CompletedProcess[str]) -> None:
    path.write_text(result.stdout, encoding="utf-8", errors="replace")
    if result.stderr:
        path.with_suffix(path.suffix + ".stderr").write_text(result.stderr, encoding="utf-8", errors="replace")
    path.with_suffix(path.suffix + ".rc").write_text(f"{result.returncode}\n", encoding="ascii")


def parse_adb_devices(output: str) -> list[str]:
    serials: list[str] = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            serials.append(parts[0])
    return serials


def select_serial(requested: str | None) -> str:
    if requested:
        return requested
    result = run(["adb", "devices", "-l"], timeout=10.0)
    serials = parse_adb_devices(result.stdout)
    if len(serials) != 1:
        raise SystemExit(f"expected exactly one adb device or pass --serial; found {len(serials)}")
    return serials[0]


def collect(run_dir: Path, name: str, result: subprocess.CompletedProcess[str]) -> str:
    write_result(run_dir / name, result)
    return result.stdout + result.stderr


def collect_shell(serial: str, run_dir: Path, name: str, command: str, *, timeout: float | None = 60.0) -> str:
    return collect(run_dir, name, shell(serial, command, timeout=timeout))


def collect_su(serial: str, run_dir: Path, name: str, command: str, *, timeout: float | None = 60.0) -> str:
    return collect(run_dir, name, su_shell(serial, command, timeout=timeout))


def parse_props(raw: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for line in raw.splitlines():
        match = re.match(r"\[(.+?)\]: \[(.*)\]", line)
        if match:
            props[match.group(1)] = match.group(2)
    return props


def line_count(text: str) -> int:
    return len([line for line in text.splitlines() if line.strip()])


def parse_proc_modules(raw: str) -> list[str]:
    modules: list[str] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        modules.append(line.split()[0])
    return modules


def first_existing_modules_load(metadata: str) -> list[str]:
    entries: list[str] = []
    in_load = False
    for line in metadata.splitlines():
        if line.startswith("### "):
            in_load = line.endswith("modules.load")
            continue
        if in_load and line.strip() and not line.startswith("#"):
            entries.append(line.strip())
    return entries


def usb_functions_from_tree(raw: str) -> list[str]:
    functions: set[str] = set()
    for line in raw.splitlines():
        for match in re.finditer(r"/functions/([^/\s]+)", line):
            functions.add(match.group(1))
    return sorted(functions)


def grep_count(raw: str, pattern: re.Pattern[str]) -> int:
    return sum(1 for line in raw.splitlines() if pattern.search(line))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", help="adb serial to pin; required if multiple devices are connected")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--expect-model", default=EXPECTED_MODEL)
    parser.add_argument("--expect-device", default=EXPECTED_DEVICE)
    parser.add_argument("--expect-build", default=EXPECTED_BUILD)
    args = parser.parse_args(argv)

    serial = select_serial(args.serial)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.run_dir or (DEFAULT_RUN_ROOT / f"s22plus_magisk_boot_capture_{stamp}")
    run_dir.mkdir(parents=True, exist_ok=False)

    collect(run_dir, "adb_devices_l.txt", run(["adb", "devices", "-l"], timeout=10.0))
    props_raw = collect_shell(serial, run_dir, "getprop_all.txt", "getprop", timeout=30.0)
    props = parse_props(props_raw)
    model = props.get("ro.product.model", "")
    device = props.get("ro.product.device", "")
    build = props.get("ro.build.version.incremental", "")
    boot_completed = props.get("sys.boot_completed", "")
    if (model, device, build, boot_completed) != (args.expect_model, args.expect_device, args.expect_build, "1"):
        raise SystemExit(
            "target preflight mismatch: "
            f"model={model!r} device={device!r} build={build!r} boot_completed={boot_completed!r}"
        )

    root_id = collect_shell(serial, run_dir, "root_id.txt", "su -c id", timeout=30.0)
    if "uid=0(root)" not in root_id:
        raise SystemExit("Magisk root proof failed; refusing boot-capture collection")

    collect_shell(serial, run_dir, "uname.txt", "uname -a", timeout=20.0)
    collect_shell(serial, run_dir, "uptime.txt", "cat /proc/uptime; date -u '+%Y-%m-%dT%H:%M:%SZ'", timeout=20.0)
    collect_shell(serial, run_dir, "boot_props.txt", "getprop | grep -Ei 'boot|init\\.svc|usb|adb|display|graphics|gpu|hwc|surfaceflinger|zygote|vendor' | sort", timeout=40.0)
    dmesg_raw = collect_su(serial, run_dir, "dmesg_raw.txt", "dmesg", timeout=90.0)
    collect_su(serial, run_dir, "dmesg_time.txt", "dmesg -T 2>/dev/null || dmesg", timeout=90.0)
    collect_su(
        serial,
        run_dir,
        "dmesg_key_filtered.txt",
        "dmesg | grep -Ei 'usb|dwc3|gadget|configfs|adbd|ffs|mtp|rndis|ncm|drm|dsi|panel|sde|display|kgsl|adreno|gpu|dispcc|gpucc|module|insmod|dlkm|firmware|pstore|ramoops' || true",
        timeout=90.0,
    )

    proc_modules_raw = collect_shell(serial, run_dir, "proc_modules.txt", "cat /proc/modules 2>/dev/null || true", timeout=30.0)
    module_inventory = collect_su(
        serial,
        run_dir,
        "module_inventory.txt",
        "for d in /vendor/lib/modules /vendor_dlkm/lib/modules /system/lib/modules /odm/lib/modules; do "
        "[ -d \"$d\" ] && echo '###' \"$d\" && find \"$d\" -maxdepth 4 -type f 2>/dev/null | sort; "
        "done",
        timeout=60.0,
    )
    module_metadata = collect_su(
        serial,
        run_dir,
        "module_metadata.txt",
        "for f in "
        "/vendor/lib/modules/modules.load /vendor/lib/modules/modules.dep /vendor/lib/modules/modules.alias /vendor/lib/modules/modules.order "
        "/vendor_dlkm/lib/modules/modules.load /vendor_dlkm/lib/modules/modules.dep /vendor_dlkm/lib/modules/modules.alias /vendor_dlkm/lib/modules/modules.order "
        "/odm/lib/modules/modules.load /odm/lib/modules/modules.dep /odm/lib/modules/modules.alias /odm/lib/modules/modules.order; do "
        "[ -f \"$f\" ] && echo '###' \"$f\" && cat \"$f\"; "
        "done",
        timeout=90.0,
    )
    collect_shell(serial, run_dir, "sys_module_listing.txt", "ls -1 /sys/module 2>/dev/null | sort", timeout=30.0)

    usb_tree = collect_su(
        serial,
        run_dir,
        "usb_gadget_state.txt",
        "for p in /config/usb_gadget /sys/kernel/config/usb_gadget /sys/class/udc /sys/class/android_usb; do "
        "[ -e \"$p\" ] || continue; "
        "echo '###TREE' \"$p\"; find \"$p\" -maxdepth 5 2>/dev/null | sort; "
        "echo '###FILES' \"$p\"; "
        "find \"$p\" -maxdepth 5 -type f 2>/dev/null | sort | while read f; do "
        "echo '---' \"$f\"; head -c 4096 \"$f\" 2>/dev/null; echo; "
        "done; "
        "done",
        timeout=90.0,
    )
    collect_shell(serial, run_dir, "usb_props.txt", "getprop | grep -Ei 'usb|adb|mtp|rndis|ncm|configfs' | sort", timeout=30.0)
    collect_su(serial, run_dir, "net_state.txt", "ip addr; echo '###ROUTE'; ip route; echo '###SYS_NET'; ls -l /sys/class/net", timeout=60.0)

    display_state = collect_su(
        serial,
        run_dir,
        "display_gpu_state.txt",
        "for p in /sys/class/drm /sys/class/graphics /sys/class/backlight /sys/class/leds /dev/dri /dev/graphics /dev/kgsl; do "
        "[ -e \"$p\" ] || continue; echo '###' \"$p\"; ls -lR \"$p\" 2>/dev/null | head -n 800; "
        "done",
        timeout=90.0,
    )
    collect_shell(serial, run_dir, "surfaceflinger_services.txt", "service list | grep -Ei 'surface|display|graphics|gpu|hwc|drm' || true", timeout=30.0)
    collect_shell(serial, run_dir, "surfaceflinger_brief.txt", "dumpsys SurfaceFlinger --display-id 2>/dev/null | head -n 200 || true", timeout=30.0)
    collect_su(serial, run_dir, "pstore_state.txt", "mount | grep -i pstore || true; ls -la /sys/fs/pstore 2>/dev/null || true", timeout=30.0)

    loaded_modules = parse_proc_modules(proc_modules_raw)
    module_files = [line for line in module_inventory.splitlines() if line.endswith(".ko")]
    modules_load = first_existing_modules_load(module_metadata)
    usb_functions = usb_functions_from_tree(usb_tree)
    summary = {
        "timestamp_utc": stamp,
        "device": {
            "serial_redacted": True,
            "model": model,
            "device": device,
            "build": build,
            "bootloader": props.get("ro.boot.bootloader", ""),
            "verifiedbootstate": props.get("ro.boot.verifiedbootstate", ""),
            "boot_completed": boot_completed,
        },
        "root": {
            "uid0": "uid=0(root)" in root_id,
            "magisk_su": "MAGISKSU" in root_id or "magisk" in root_id.lower(),
        },
        "module": {
            "module_file_count": len(module_files),
            "loaded_module_count": len(loaded_modules),
            "modules_load_count": len(modules_load),
            "loaded_first_40": loaded_modules[:40],
            "modules_load_first_40": modules_load[:40],
        },
        "usb": {
            "functions": usb_functions,
            "ncm_present_in_configfs": any("ncm" in function for function in usb_functions),
            "adb_present_in_configfs": any("ffs.adb" in function or "adb" in function for function in usb_functions),
        },
        "display": {
            "has_dev_dri": "/dev/dri" in display_state,
            "has_dev_kgsl": "/dev/kgsl" in display_state,
        },
        "dmesg_key_counts": {
            name: grep_count(dmesg_raw, pattern) for name, pattern in KEY_DMESG_PATTERNS.items()
        },
        "raw_private": True,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(run_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
