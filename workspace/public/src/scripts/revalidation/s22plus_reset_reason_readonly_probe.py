#!/usr/bin/env python3
"""Read-only S22+ reset/PON reason probe.

This helper does not flash, reboot, write partitions, write sysfs, install
modules, or stage files on the device. It records a redacted, repeatable snapshot
of the current Android reset-reason surfaces before the ramoops live gate.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_MODEL = "SM-S906N"
EXPECTED_DEVICE = "g0q"
EXPECTED_BUILD = "S906NKSS7FYG8"
EXPECTED_MAGISK_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_STOCK_VENDOR_BOOT_SHA256 = "096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7"

DEFAULT_RUN_ROOT = Path("workspace/private/runs")

RESET_FILES = (
    "/proc/reset_reason",
    "/proc/reset_summary",
    "/proc/reset_history",
    "/proc/reset_klog",
    "/proc/reset_tzlog",
    "/proc/reset_rwc",
    "/proc/store_lastkmsg",
    "/proc/boot_stat",
    "/proc/enhanced_boot_stat",
    "/proc/cmdline",
    "/proc/bootconfig",
    "/sys/module/qcom_dload_mode/parameters/download_mode",
    "/sys/module/ramoops/parameters/max_reason",
    "/sys/module/kernel/parameters/panic",
    "/sys/module/kernel/parameters/panic_on_warn",
    "/sys/kernel/wakeup_reasons/last_resume_reason",
)

LAST_KMSG_PATTERNS = (
    "S22_NATIVE_INIT",
    "panic",
    "oops",
    "SError",
    "watchdog",
    "download",
    "reboot_reason",
    "restart_reason",
    "reset",
    "pon",
)


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").is_dir():
            return parent
    raise RuntimeError(f"could not locate repo root from {current}")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def adb_su(serial: str, command: str, *, timeout: float = 30.0) -> subprocess.CompletedProcess[bytes]:
    return adb(serial, ["exec-out", "su", "-c", command], timeout=timeout)


def parse_adb_devices(text: str) -> list[str]:
    devices: list[str] = []
    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices


def choose_serial(requested: str | None) -> str:
    devices = parse_adb_devices(adb_text(None, ["devices", "-l"], timeout=10.0))
    if requested:
        if requested not in devices:
            raise SystemExit("requested ADB serial is not currently connected as a device")
        return requested
    if len(devices) != 1:
        raise SystemExit("expected exactly one ADB device or pass --serial")
    return devices[0]


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def redact(text: str) -> str:
    text = re.sub(r"RFCT[0-9A-Z]+", "<REDACTED_SERIAL>", text)
    text = re.sub(r'(sec_debug\.ap_serial=)"[^"]+"', r'\1"<REDACTED_AP_SERIAL>"', text)
    text = re.sub(r'(kernel\.sec_debug\.ap_serial = )"[^"]+"', r'\1"<REDACTED_AP_SERIAL>"', text)
    sensitive_boot_keys = (
        "androidboot.ap_serial",
        "androidboot.serialno",
        "androidboot.kg.ap",
        "androidboot.em.did",
    )
    for key in sensitive_boot_keys:
        text = re.sub(rf'({re.escape(key)} = )"[^"]+"', rf'\1"<REDACTED_{key.split(".")[-1].upper()}>"', text)
    return text


def safe_name(path: str) -> str:
    cleaned = path.strip("/").replace("/", "__").replace("*", "glob")
    return re.sub(r"[^A-Za-z0-9_.+-]", "_", cleaned) or "root"


def remote_file_payload(text: str) -> str:
    lines = text.splitlines()
    if lines and re.match(r"^[bcdlps-][rwxStTs-]{9}\s+", lines[0]):
        return "\n".join(lines[1:]).strip()
    return text.strip()


def first_payload_line(text: str) -> str:
    for line in remote_file_payload(text).splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def parse_reset_context(
    *,
    reset_reason_text: str,
    reset_rwc_text: str,
    store_lastkmsg_text: str,
    reset_history_text: str,
    reset_summary_text: str,
) -> dict[str, Any]:
    reset_reason_value = first_payload_line(reset_reason_text)
    reset_rwc_value = first_payload_line(reset_rwc_text)
    store_lastkmsg_value = first_payload_line(store_lastkmsg_text)
    history_payload = remote_file_payload(reset_history_text)
    summary_payload = remote_file_payload(reset_summary_text)
    upload_causes = re.findall(r"@ Upload Cause = ([^\r\n<]+)", history_payload)
    oem_reset_magic_values = re.findall(r"OEM_RESET_REASON:.*?magic_val:(0x[0-9a-fA-F]+)", history_payload)
    return {
        "proc_reset_reason_value": reset_reason_value,
        "proc_reset_rwc_value": reset_rwc_value,
        "proc_store_lastkmsg_value": store_lastkmsg_value,
        "reset_history_upload_causes": upload_causes[:16],
        "reset_history_upload_cause_count": len(upload_causes),
        "reset_history_pmic_abnormal_count": history_payload.count("PMIC abnormal reset"),
        "reset_summary_pmic_abnormal_count": summary_payload.count("PMIC abnormal reset"),
        "reset_history_oem_reset_magic_values": oem_reset_magic_values[:16],
        "reset_history_oem_reset_magic_count": len(oem_reset_magic_values),
    }


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def su_text(serial: str, command: str, *, timeout: float = 30.0) -> tuple[int, str]:
    result = adb_su(serial, command, timeout=timeout)
    text = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    return result.returncode, redact(text)


def read_remote_file(serial: str, path: str, *, timeout: float = 15.0, head_bytes: int = 131072) -> dict[str, Any]:
    command = (
        f"if [ -e '{path}' ]; then "
        f"ls -l '{path}' 2>/dev/null; "
        f"cat '{path}' 2>&1 | head -c {head_bytes}; "
        "else echo __MISSING__; fi"
    )
    rc, text = su_text(serial, command, timeout=timeout)
    missing = "__MISSING__" in text
    return {
        "path": path,
        "rc": rc,
        "missing": missing,
        "bytes": len(text.encode("utf-8", errors="replace")),
        "text": text,
    }


def grep_remote(serial: str, path: str, patterns: tuple[str, ...], *, timeout: float = 20.0) -> dict[str, Any]:
    pattern = "|".join(re.escape(item) for item in patterns)
    command = f"cat '{path}' 2>/dev/null | grep -Eai '{pattern}' | head -200 || true"
    rc, text = su_text(serial, command, timeout=timeout)
    return {
        "path": path,
        "rc": rc,
        "bytes": len(text.encode("utf-8", errors="replace")),
        "text": text,
        "hit_count": len([line for line in text.splitlines() if line.strip()]),
    }


def sha256_block(serial: str, by_name: str, *, timeout: float = 90.0) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9._+-]+", by_name):
        raise ValueError(f"unsafe partition name: {by_name!r}")
    command = f"dd if=/dev/block/by-name/{by_name} bs=4096 2>/dev/null | sha256sum"
    rc, text = su_text(serial, command, timeout=timeout)
    match = re.search(r"\b([0-9a-fA-F]{64})\b", text)
    return {
        "partition": by_name,
        "rc": rc,
        "sha256": match.group(1).lower() if match else "",
        "bytes": len(text.encode("utf-8", errors="replace")),
    }


def collect_props(serial: str) -> dict[str, str]:
    keys = (
        "ro.product.model",
        "ro.product.device",
        "ro.build.version.incremental",
        "ro.boot.bootloader",
        "ro.boot.verifiedbootstate",
        "ro.boot.boot_recovery",
        "ro.boot.bootreason",
        "sys.boot.reason",
        "sys.boot.reason.last",
        "persist.sys.boot.reason.history",
        "sys.boot_completed",
        "init.svc.bootanim",
        "sys.reset_reason",
        "persist.radio.silent-reset",
    )
    command = "; ".join(f"printf '{key}='; getprop {key}" for key in keys)
    rc, text = su_text(serial, command, timeout=15.0)
    values = parse_key_values(text)
    values["_rc"] = str(rc)
    values["su_root"] = "false"
    id_rc, id_text = su_text(serial, "id", timeout=10.0)
    if id_rc == 0 and "uid=0(root)" in id_text:
        values["su_root"] = "true"
    return values


def collect_pstore(serial: str) -> dict[str, Any]:
    rc, text = su_text(serial, "ls -la /sys/fs/pstore 2>&1 || true", timeout=15.0)
    entries = [
        line
        for line in text.splitlines()
        if line.strip()
        and not line.startswith("total ")
        and "Permission denied" not in line
        and not re.search(r"\s\.$", line)
        and not re.search(r"\s\.\.$", line)
    ]
    return {
        "rc": rc,
        "listing": text,
        "entry_count_estimate": max(0, len(entries)),
        "permission_denied": "Permission denied" in text,
    }


def collect(run_dir: Path, serial: str) -> dict[str, Any]:
    props = collect_props(serial)
    reset_files: dict[str, Any] = {}
    for path in RESET_FILES:
        item = read_remote_file(serial, path)
        reset_files[path] = {key: value for key, value in item.items() if key != "text"}
        write_text(run_dir / "reset_files" / f"{safe_name(path)}.txt", item["text"])

    last_kmsg_meta = read_remote_file(serial, "/proc/last_kmsg", timeout=45.0, head_bytes=262144)
    write_text(run_dir / "last_kmsg_head.txt", last_kmsg_meta["text"])
    last_kmsg_grep = grep_remote(serial, "/proc/last_kmsg", LAST_KMSG_PATTERNS, timeout=45.0)
    write_text(run_dir / "last_kmsg_grep.txt", last_kmsg_grep["text"])
    dmesg_grep = {
        "rc": 0,
        "text": "",
        "hit_count": 0,
    }
    rc, dmesg_text = su_text(
        serial,
        "dmesg -T 2>/dev/null | grep -Eai 'reboot|bootreason|reset|watchdog|wdog|panic|oops|download|pon|pstore|ramoops|sec_debug|qcom.*reason' | tail -300 || true",
        timeout=30.0,
    )
    dmesg_grep = {
        "rc": rc,
        "bytes": len(dmesg_text.encode("utf-8", errors="replace")),
        "text": dmesg_text,
        "hit_count": len([line for line in dmesg_text.splitlines() if line.strip()]),
    }
    write_text(run_dir / "dmesg_reset_reason_grep.txt", dmesg_text)

    pstore = collect_pstore(serial)
    write_text(run_dir / "pstore_listing.txt", pstore["listing"])

    boot_hash = sha256_block(serial, "boot")
    vendor_boot_hash = sha256_block(serial, "vendor_boot")

    reset_reason = (run_dir / "reset_files" / f"{safe_name('/proc/reset_reason')}.txt").read_text(encoding="utf-8")
    reset_rwc = (run_dir / "reset_files" / f"{safe_name('/proc/reset_rwc')}.txt").read_text(encoding="utf-8")
    store_lastkmsg = (run_dir / "reset_files" / f"{safe_name('/proc/store_lastkmsg')}.txt").read_text(encoding="utf-8")
    reset_history = (run_dir / "reset_files" / f"{safe_name('/proc/reset_history')}.txt").read_text(encoding="utf-8")
    reset_summary = (run_dir / "reset_files" / f"{safe_name('/proc/reset_summary')}.txt").read_text(encoding="utf-8")

    summary: dict[str, Any] = {
        "generated_at_utc": utc_now(),
        "device_action": "read-only-adb-root",
        "writes_performed": False,
        "reboots_performed": False,
        "flashes_performed": False,
        "serial_redacted": True,
        "props": props,
        "reset_reason": {
            "proc_reset_reason_contains_NPON": "NPON" in reset_reason,
            "proc_reset_rwc_value_0": reset_rwc.rstrip().endswith("0"),
            "proc_store_lastkmsg_value_0": store_lastkmsg.rstrip().endswith("0"),
            **parse_reset_context(
                reset_reason_text=reset_reason,
                reset_rwc_text=reset_rwc,
                store_lastkmsg_text=store_lastkmsg,
                reset_history_text=reset_history,
                reset_summary_text=reset_summary,
            ),
        },
        "partition_hashes": {
            "boot": boot_hash,
            "vendor_boot": vendor_boot_hash,
            "boot_matches_magisk_baseline": boot_hash["sha256"] == EXPECTED_MAGISK_BOOT_SHA256,
            "vendor_boot_matches_stock": vendor_boot_hash["sha256"] == EXPECTED_STOCK_VENDOR_BOOT_SHA256,
        },
        "pstore": {key: value for key, value in pstore.items() if key != "listing"},
        "last_kmsg": {
            "head_bytes": last_kmsg_meta["bytes"],
            "grep_hit_count": last_kmsg_grep["hit_count"],
            "grep_path": "last_kmsg_grep.txt",
        },
        "dmesg": {
            "grep_hit_count": dmesg_grep["hit_count"],
            "grep_path": "dmesg_reset_reason_grep.txt",
        },
        "reset_files": reset_files,
    }
    summary["checks"] = {
        "target_model": props.get("ro.product.model") == EXPECTED_MODEL,
        "target_device": props.get("ro.product.device") == EXPECTED_DEVICE,
        "target_build": props.get("ro.boot.bootloader") == EXPECTED_BUILD
        and props.get("ro.build.version.incremental") == EXPECTED_BUILD,
        "android_booted": props.get("sys.boot_completed") == "1",
        "normal_boot": props.get("ro.boot.boot_recovery") == "0",
        "root_available": props.get("su_root") == "true",
        "boot_hash_baseline": summary["partition_hashes"]["boot_matches_magisk_baseline"],
        "vendor_boot_hash_stock": summary["partition_hashes"]["vendor_boot_matches_stock"],
    }
    summary["result"] = "pass" if all(summary["checks"].values()) else "fail"
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", help="optional ADB serial when more than one device is connected")
    parser.add_argument("--run-dir", type=Path, help="optional private run directory")
    args = parser.parse_args(argv)

    root = repo_root()
    run_dir = args.run_dir or (DEFAULT_RUN_ROOT / f"s22plus_reset_reason_readonly_{utc_stamp()}")
    run_dir = run_dir if run_dir.is_absolute() else root / run_dir
    run_dir.mkdir(parents=True, exist_ok=False)
    serial = choose_serial(args.serial)
    summary = collect(run_dir, serial)
    summary["run_dir"] = str(run_dir.relative_to(root) if run_dir.is_relative_to(root) else run_dir)
    payload = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    write_text(run_dir / "summary.json", payload)
    print(payload, end="")
    return 0 if summary["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
