#!/usr/bin/env python3
"""Read-only S22+ retained-evidence channel probe.

This helper does not reboot, flash, write partitions, install modules, or write
remote files.  It records the current rooted-Android evidence that determines
whether early native-init kmsg/pmsg markers can be trusted after recovery.
Private raw captures are written under workspace/private/runs by default.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_MODEL = "SM-S906N"
EXPECTED_DEVICE = "g0q"
EXPECTED_BOOTLOADER = "S906NKSS7FYG8"
DEFAULT_RUN_ROOT = Path("workspace/private/runs")
DEFAULT_MARKERS = (
    "S22_NATIVE_INIT",
    "S22_NATIVE_INIT_INSTANT_DOWNLOAD_M4T0",
    "S22_NATIVE_INIT_FAST_DWELL_M4A",
    "S22_NATIVE_INIT_MARKER_ONLY_M32",
    "S22_NATIVE_INIT_OBSERVABLE_M3",
    "S22_NATIVE_INIT_DIRECT_P3",
    "S22_NATIVE_INIT_MAGISK_CHAINLOAD",
)

DT_PROPS = {
    "ramoops_status": "/proc/device-tree/reserved-memory/ramoops_region/status",
    "ramoops_compatible": "/proc/device-tree/reserved-memory/ramoops_region/compatible",
    "ramoops_size": "/proc/device-tree/reserved-memory/ramoops_region/size",
    "ramoops_pmsg_size": "/proc/device-tree/reserved-memory/ramoops_region/pmsg-size",
    "ramoops_alloc_ranges": "/proc/device-tree/reserved-memory/ramoops_region/alloc-ranges",
    "sec_debug_log_reg": "/proc/device-tree/reserved-memory/sec_debug_region_log@8001FF000/reg",
    "sec_debug_pool_reg": "/proc/device-tree/reserved-memory/sec_debug_region_pool@800100000/reg",
    "google_debug_kinfo_reg": "/proc/device-tree/reserved-memory/google_debug_kinfo_region@800B00000/reg",
}


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").is_dir():
            return parent
    raise RuntimeError(f"could not locate repo root from {current}")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run(argv: list[str], *, timeout: float = 30.0) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)


def adb(serial: str | None, args: list[str], *, timeout: float = 30.0) -> subprocess.CompletedProcess[bytes]:
    argv = ["adb"]
    if serial:
        argv.extend(["-s", serial])
    argv.extend(args)
    return run(argv, timeout=timeout)


def adb_text(serial: str | None, args: list[str], *, timeout: float = 30.0) -> str:
    result = adb(serial, args, timeout=timeout)
    return (result.stdout + result.stderr).decode("utf-8", errors="replace")


def adb_exec(serial: str | None, command: str, *, timeout: float = 30.0) -> subprocess.CompletedProcess[bytes]:
    return adb(serial, ["exec-out", "sh", "-c", command], timeout=timeout)


def adb_su_exec(serial: str | None, command: str, *, timeout: float = 30.0) -> subprocess.CompletedProcess[bytes]:
    return adb(serial, ["exec-out", "su", "-c", command], timeout=timeout)


def write_capture(run_dir: Path, name: str, payload: bytes) -> Path:
    path = run_dir / name
    path.write_bytes(payload)
    return path


def clean_dt_string(payload: bytes) -> str:
    return payload.split(b"\0", 1)[0].decode("utf-8", errors="replace")


def be_int(payload: bytes) -> int | None:
    if len(payload) not in (4, 8, 16):
        return None
    if len(payload) == 16:
        return None
    return int.from_bytes(payload, byteorder="big", signed=False)


def be_cells(payload: bytes) -> list[str]:
    if len(payload) % 4 != 0:
        return []
    return [f"0x{int.from_bytes(payload[idx:idx + 4], 'big'):08x}" for idx in range(0, len(payload), 4)]


def parse_adb_devices(output: str) -> list[str]:
    serials: list[str] = []
    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            serials.append(parts[0])
    return serials


def choose_serial(requested: str | None) -> str:
    output = adb_text(None, ["devices", "-l"])
    devices = parse_adb_devices(output)
    if requested:
        if requested not in devices:
            raise SystemExit(f"requested serial {requested!r} is not an adb device; devices={devices!r}")
        return requested
    if len(devices) != 1:
        raise SystemExit(f"expected exactly one adb device or pass --serial; devices={devices!r}")
    return devices[0]


def extract_prop(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}=(.*)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", help="target adb serial; required when multiple adb devices are present")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--marker", action="append", default=[], help="marker string to search in retained logs")
    args = parser.parse_args(argv)

    root = repo_root()
    serial = choose_serial(args.serial)
    run_dir = args.run_dir or (DEFAULT_RUN_ROOT / f"s22plus_retained_evidence_probe_{utc_stamp()}")
    run_dir = run_dir if run_dir.is_absolute() else root / run_dir
    run_dir.mkdir(parents=True, exist_ok=False)

    markers = list(DEFAULT_MARKERS)
    markers.extend(args.marker)

    devices_text = adb_text(None, ["devices", "-l"])
    write_capture(run_dir, "adb_devices.txt", devices_text.encode())

    identity_cmd = (
        "printf 'model='; getprop ro.product.model; "
        "printf 'device='; getprop ro.product.device; "
        "printf 'bootloader='; getprop ro.boot.bootloader; "
        "printf 'boot_completed='; getprop sys.boot_completed; "
        "printf 'boot_recovery='; getprop ro.boot.boot_recovery; "
        "printf 'verifiedbootstate='; getprop ro.boot.verifiedbootstate; "
        "printf 'root_id='; su -c id 2>/dev/null || true; "
        "printf 'getenforce='; getenforce 2>/dev/null || true"
    )
    identity = adb_text(serial, ["shell", identity_cmd])
    write_capture(run_dir, "identity.txt", identity.encode())
    model = extract_prop(identity, "model")
    device = extract_prop(identity, "device")
    bootloader = extract_prop(identity, "bootloader")
    if model != EXPECTED_MODEL or device != EXPECTED_DEVICE or bootloader != EXPECTED_BOOTLOADER:
        raise SystemExit(f"target identity mismatch: model={model!r} device={device!r} bootloader={bootloader!r}")

    config_gz = adb_exec(serial, "cat /proc/config.gz 2>/dev/null", timeout=30.0)
    write_capture(run_dir, "proc_config.gz.raw", config_gz.stdout + config_gz.stderr)
    config_text = ""
    try:
        config_text = gzip.decompress(config_gz.stdout).decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001 - report exact capture failure in summary.
        config_text = f"CONFIG_READ_DECODE_FAILED: {exc}\n"
    write_capture(run_dir, "proc_config.txt", config_text.encode())
    config_lines = [
        line
        for line in config_text.splitlines()
        if line.startswith("CONFIG_PSTORE") or line.startswith("CONFIG_RAMOOPS") or "PSTORE" in line
    ]

    dt_summary: dict[str, Any] = {}
    for name, remote_path in DT_PROPS.items():
        result = adb_su_exec(serial, f"cat {remote_path} 2>/dev/null", timeout=20.0)
        payload = result.stdout
        write_capture(run_dir, f"dt_{name}.bin", payload + result.stderr)
        item: dict[str, Any] = {
            "path": remote_path,
            "rc": result.returncode,
            "bytes": len(payload),
            "hex": payload.hex(),
        }
        if name.endswith(("status", "compatible")):
            item["text"] = clean_dt_string(payload)
        intval = be_int(payload)
        if intval is not None:
            item["be_int"] = intval
            item["be_hex"] = f"0x{intval:x}"
        cells = be_cells(payload)
        if cells:
            item["be_cells"] = cells
        dt_summary[name] = item

    dt_find = adb_su_exec(
        serial,
        "find /proc/device-tree/reserved-memory -maxdepth 2 -type d -print 2>/dev/null "
        "| grep -Ei 'ramoops|debug|pmsg|sec|log|kmsg' || true",
        timeout=20.0,
    )
    write_capture(run_dir, "device_tree_reserved_memory_matches.txt", dt_find.stdout + dt_find.stderr)

    devices = adb_su_exec(serial, "cat /proc/devices 2>/dev/null | grep -E 'pmsg|pstore|ramoops|rpmsg' || true")
    write_capture(run_dir, "proc_devices_filtered.txt", devices.stdout + devices.stderr)
    pstore = adb_su_exec(serial, "ls -la /sys/fs/pstore 2>&1 || true", timeout=20.0)
    write_capture(run_dir, "pstore_listing.txt", pstore.stdout + pstore.stderr)
    last_kmsg = adb_su_exec(serial, "cat /proc/last_kmsg 2>&1 || true", timeout=45.0)
    last_payload = last_kmsg.stdout + last_kmsg.stderr
    write_capture(run_dir, "last_kmsg.txt", last_payload)
    dmesg = adb_su_exec(serial, "dmesg 2>&1 | tail -n 120 || true", timeout=20.0)
    write_capture(run_dir, "dmesg_tail.txt", dmesg.stdout + dmesg.stderr)

    marker_hits = {
        marker: marker.encode("utf-8") in last_payload or marker.encode("utf-8") in dmesg.stdout
        for marker in markers
    }

    last_kmsg_text_prefix = last_payload[:512].decode("utf-8", errors="replace")
    last_kmsg_read_denied = last_payload.strip() in (
        b"cat: /proc/last_kmsg: Permission denied",
        b"/proc/last_kmsg: Permission denied",
        b"Permission denied",
    )
    dmesg_payload = dmesg.stdout + dmesg.stderr
    dmesg_read_denied = dmesg_payload.strip() in (
        b"dmesg: klogctl: Permission denied",
        b"Permission denied",
    )

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "serial_redacted": True,
        "target": f"{EXPECTED_MODEL}/{EXPECTED_DEVICE}/{EXPECTED_BOOTLOADER}",
        "identity": {
            "model": model,
            "device": device,
            "bootloader": bootloader,
            "boot_completed": extract_prop(identity, "boot_completed"),
            "boot_recovery": extract_prop(identity, "boot_recovery"),
            "verifiedbootstate": extract_prop(identity, "verifiedbootstate"),
            "root_id_contains_uid0": "uid=0(root)" in identity,
            "getenforce": extract_prop(identity, "getenforce"),
        },
        "kernel_config_pstore_lines": config_lines,
        "kernel_config_pstore_ok": all(
            needle in config_text
            for needle in (
                "CONFIG_PSTORE=y",
                "CONFIG_PSTORE_RAM=y",
                "CONFIG_PSTORE_PMSG=y",
                "CONFIG_PSTORE_CONSOLE=y",
            )
        ),
        "device_tree": dt_summary,
        "ramoops_region_present": dt_summary.get("ramoops_compatible", {}).get("text") == "ramoops",
        "ramoops_region_status": dt_summary.get("ramoops_status", {}).get("text", ""),
        "ramoops_pmsg_size": dt_summary.get("ramoops_pmsg_size", {}).get("be_int"),
        "pstore_listing_bytes": len(pstore.stdout + pstore.stderr),
        "pstore_listing_text": (pstore.stdout + pstore.stderr).decode("utf-8", errors="replace"),
        "last_kmsg_bytes": len(last_payload),
        "last_kmsg_read_denied": last_kmsg_read_denied,
        "last_kmsg_prefix": last_kmsg_text_prefix,
        "dmesg_read_denied": dmesg_read_denied,
        "marker_hits": marker_hits,
        "interpretation": (
            "pstore kernel support and a DT ramoops node exist, but this boot reports "
            "ramoops_region/status=disabled and /sys/fs/pstore may be empty or SELinux-gated; "
            "future native-init negative results must not rely on empty pstore alone."
        ),
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
