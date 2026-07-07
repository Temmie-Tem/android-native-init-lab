#!/usr/bin/env python3
"""Read-only S22+ active DTB provenance audit.

This helper does not flash, reboot, write sysfs, write partitions, install
modules, or stage files on the device. It compares the live Android
`/proc/device-tree` ramoops node against the stock vendor_boot DTB blobs and the
stock DTBO ramoops overlay targets.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_s22plus_ramoops_dtbo_enable import decode_string_list, iter_fdt_blobs, parse_fdt_props
from build_s22plus_ramoops_vendor_boot_enable import STATUS_NAME, TARGET_NODE
from s22plus_ramoops_android_baseline_preflight import (
    EXPECTED_BOOT_SHA256,
    EXPECTED_BUILD,
    EXPECTED_DEVICE,
    EXPECTED_DTBO_SHA256,
    EXPECTED_MODEL,
    get_props,
    read_partition_hash,
    select_device,
)
from s22plus_ramoops_vendor_boot_m13_capture_live_gate import EXPECTED_STOCK_VENDOR_BOOT_SHA256


DEFAULT_RUN_ROOT = Path("workspace/private/runs")
DEFAULT_VENDOR_DTB = Path("workspace/private/outputs/s22plus_ramoops_vendor_boot_direct_enable_v0_1/build/dtb.source")
DEFAULT_PATCHED_VENDOR_DTB = Path(
    "workspace/private/outputs/s22plus_ramoops_vendor_boot_direct_enable_v0_1/build/dtb.ramoops_status_okay.direct"
)
DEFAULT_STOCK_DTBO = Path("workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/raw/dtbo.img")
DEFAULT_PATCHED_DTBO = Path("workspace/private/outputs/s22plus_ramoops_dtbo_enable_v0_1/build/dtbo.img")

RAMOOPS_SYMBOL = "ramoops_mem"
TARGET_OVERLAY_STATUS_PATH = "/fragment@116/__overlay__"
SENSITIVE_KEY_RE = re.compile(r"(serial|bootargs|cmdline|rng-seed|kaslr-seed|androidboot|uuid|partuuid)", re.IGNORECASE)
COMPARE_PREFIXES = (
    "/model",
    "/compatible",
    "/interrupt-parent",
    "/#address-cells",
    "/#size-cells",
    f"{TARGET_NODE}/",
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").is_dir():
            return parent
    raise RuntimeError(f"could not locate repo root from {current}")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def display_value(value: bytes) -> dict[str, Any]:
    item: dict[str, Any] = {
        "length": len(value),
        "sha256": sha256_bytes(value),
        "hex": value.hex(),
    }
    strings: list[str] = []
    try:
        strings = decode_string_list(value)
    except UnicodeDecodeError:
        strings = []
    if (
        value.endswith(b"\0")
        and strings
        and all(part and all(32 <= ord(ch) < 127 for ch in part) for part in strings)
        and any(re.search(r"[A-Za-z]", part) for part in strings)
    ):
        item["strings"] = strings
    if len(value) in (4, 8, 16):
        cells = [int.from_bytes(value[index : index + 4], "big") for index in range(0, len(value), 4)]
        item["u32_cells_be"] = cells
    return item


def prop_key(node_path: str, name: str) -> str:
    if node_path == "/":
        return f"/{name}"
    return f"{node_path.rstrip('/')}/{name}"


def is_sensitive_key(key: str) -> bool:
    return bool(SENSITIVE_KEY_RE.search(key))


def is_compare_key(key: str) -> bool:
    if is_sensitive_key(key):
        return False
    return any(key == prefix or key.startswith(prefix) for prefix in COMPARE_PREFIXES)


def parse_fdt_prop_map(blob_data: bytes) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for blob in iter_fdt_blobs(blob_data):
        props = parse_fdt_props(blob)
        prop_map = {prop_key(prop.path, prop.name): prop.value for prop in props}
        ramoops_props = {
            prop.name: display_value(prop.value)
            for prop in props
            if prop.path == TARGET_NODE and not is_sensitive_key(prop.name)
        }
        ramoops_symbol = [
            value
            for prop in props
            if prop.path == "/__symbols__" and prop.name == RAMOOPS_SYMBOL
            for value in decode_string_list(prop.value)
        ]
        summaries.append(
            {
                "blob_index": blob.index,
                "blob_offset_hex": f"0x{blob.offset:x}",
                "totalsize": blob.totalsize,
                "sha256": sha256_bytes(blob.data),
                "prop_count": len(prop_map),
                "ramoops_symbol": ramoops_symbol,
                "ramoops_props": ramoops_props,
                "_props": prop_map,
            }
        )
    return summaries


def public_blob_summary(blob: dict[str, Any]) -> dict[str, Any]:
    return {
        "blob_index": blob["blob_index"],
        "blob_offset_hex": blob["blob_offset_hex"],
        "totalsize": blob["totalsize"],
        "sha256": blob["sha256"],
        "prop_count": blob["prop_count"],
        "ramoops_symbol": blob["ramoops_symbol"],
        "ramoops_props": blob["ramoops_props"],
    }


def summarize_dtbo_ramoops_overlays(image: bytes) -> list[dict[str, Any]]:
    overlays: list[dict[str, Any]] = []
    for blob in iter_fdt_blobs(image):
        props = parse_fdt_props(blob)
        fixups = [
            value
            for prop in props
            if prop.path == "/__fixups__" and prop.name == RAMOOPS_SYMBOL
            for value in decode_string_list(prop.value)
        ]
        statuses = [
            display_value(prop.value)
            for prop in props
            if prop.path == TARGET_OVERLAY_STATUS_PATH and prop.name == STATUS_NAME
        ]
        if fixups or statuses:
            overlays.append(
                {
                    "blob_index": blob.index,
                    "blob_offset_hex": f"0x{blob.offset:x}",
                    "totalsize": blob.totalsize,
                    "sha256": sha256_bytes(blob.data),
                    "ramoops_fixups": fixups,
                    "fragment116_status_values": statuses,
                    "has_ramoops_mem_fragment116_fixup": any("/fragment@116:target:0" in item for item in fixups),
                }
            )
    return overlays


def adb_exec_out(serial: str, command: str, timeout: float = 60.0) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["adb", "-s", serial, "exec-out", "su", "-c", command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def collect_live_device_tree(serial: str) -> dict[str, bytes]:
    result = adb_exec_out(serial, "cd /proc/device-tree && tar -cf - . 2>/dev/null", timeout=90.0)
    if result.returncode != 0 or not result.stdout:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise SystemExit(f"failed to read live /proc/device-tree tar rc={result.returncode}: {stderr}")
    props: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
            for member in archive:
                if not member.isfile():
                    continue
                handle = archive.extractfile(member)
                if handle is None:
                    continue
                name = "/" + member.name.lstrip("./")
                props[name] = handle.read()
    except tarfile.TarError as exc:
        raise SystemExit(f"failed to parse live /proc/device-tree tar: {exc}") from exc
    return props


def compare_blob_to_live(blob: dict[str, Any], live_props: dict[str, bytes]) -> dict[str, Any]:
    props: dict[str, bytes] = blob["_props"]
    keys = sorted(key for key in props.keys() & live_props.keys() if is_compare_key(key))
    exact = [key for key in keys if props[key] == live_props[key]]
    mismatch = [key for key in keys if props[key] != live_props[key]]
    live_ramoops_keys = sorted(key for key in live_props if key.startswith(f"{TARGET_NODE}/") and is_compare_key(key))
    blob_ramoops_keys = sorted(key for key in props if key.startswith(f"{TARGET_NODE}/") and is_compare_key(key))
    missing_ramoops_in_blob = sorted(set(live_ramoops_keys) - set(blob_ramoops_keys))
    missing_ramoops_live = sorted(set(blob_ramoops_keys) - set(live_ramoops_keys))
    return {
        "blob_index": blob["blob_index"],
        "comparable_key_count": len(keys),
        "exact_match_count": len(exact),
        "mismatch_count": len(mismatch),
        "exact_match_ratio": round(len(exact) / len(keys), 4) if keys else 0.0,
        "exact_keys": exact,
        "mismatch_keys": mismatch,
        "live_ramoops_keys": live_ramoops_keys,
        "blob_ramoops_keys": blob_ramoops_keys,
        "missing_ramoops_in_blob": missing_ramoops_in_blob,
        "missing_ramoops_live": missing_ramoops_live,
    }


def node_props(props: dict[str, bytes], node: str) -> dict[str, Any]:
    prefix = node.rstrip("/") + "/"
    result: dict[str, Any] = {}
    for key, value in sorted(props.items()):
        if key.startswith(prefix):
            name = key[len(prefix) :]
            if "/" not in name and not is_sensitive_key(name):
                result[name] = display_value(value)
    return result


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    vendor_dtb = resolve(root, args.vendor_dtb)
    patched_vendor_dtb = resolve(root, args.patched_vendor_dtb)
    stock_dtbo = resolve(root, args.stock_dtbo)
    patched_dtbo = resolve(root, args.patched_dtbo)

    for label, path in (
        ("vendor_dtb", vendor_dtb),
        ("patched_vendor_dtb", patched_vendor_dtb),
        ("stock_dtbo", stock_dtbo),
    ):
        if not path.is_file():
            raise SystemExit(f"{label} missing: {path}")

    serial = select_device(args.serial)
    props = get_props(serial)
    boot_hash = read_partition_hash(serial, "boot")
    vendor_boot_hash = read_partition_hash(serial, "vendor_boot")
    dtbo_hash = read_partition_hash(serial, "dtbo")
    live_tree = collect_live_device_tree(serial)

    vendor_blobs = parse_fdt_prop_map(vendor_dtb.read_bytes())
    patched_vendor_blobs = parse_fdt_prop_map(patched_vendor_dtb.read_bytes())
    stock_dtbo_overlays = summarize_dtbo_ramoops_overlays(stock_dtbo.read_bytes())
    patched_dtbo_overlays = summarize_dtbo_ramoops_overlays(patched_dtbo.read_bytes()) if patched_dtbo.is_file() else []

    comparisons = [compare_blob_to_live(blob, live_tree) for blob in vendor_blobs]
    best = max(comparisons, key=lambda item: (item["exact_match_count"], item["exact_match_ratio"]), default=None)

    live_ramoops = node_props(live_tree, TARGET_NODE)
    vendor_base_matches_live = bool(best) and TARGET_NODE.strip("/") and best["exact_match_count"] >= 5
    vendor_symbols_target_ramoops = all(blob["ramoops_symbol"] == [TARGET_NODE] for blob in vendor_blobs)
    stock_dtbo_disables_ramoops = any(
        item["has_ramoops_mem_fragment116_fixup"]
        and any("disabled" in value.get("strings", []) for value in item["fragment116_status_values"])
        for item in stock_dtbo_overlays
    )
    patched_dtbo_enables_ramoops = any(
        item["has_ramoops_mem_fragment116_fixup"]
        and any("okay" in value.get("strings", []) for value in item["fragment116_status_values"])
        for item in patched_dtbo_overlays
    )
    live_status_disabled = "disabled" in live_ramoops.get("status", {}).get("strings", [])

    checks = {
        "model": props.get("model") == EXPECTED_MODEL,
        "device": props.get("device") == EXPECTED_DEVICE,
        "bootloader": props.get("bootloader") == EXPECTED_BUILD,
        "incremental": props.get("incremental") == EXPECTED_BUILD,
        "vbstate_orange": props.get("vbstate") == "orange",
        "boot_recovery_zero": props.get("boot_recovery") == "0",
        "boot_completed": props.get("boot_completed") == "1",
        "root_available": "uid=0(root)" in props.get("su_id", ""),
        "boot_sha_matches_magisk_baseline": boot_hash["sha256"] == EXPECTED_BOOT_SHA256,
        "vendor_boot_sha_matches_stock": vendor_boot_hash["sha256"] == EXPECTED_STOCK_VENDOR_BOOT_SHA256,
        "dtbo_sha_matches_stock": dtbo_hash["sha256"] == EXPECTED_DTBO_SHA256,
        "live_ramoops_status_disabled": live_status_disabled,
        "vendor_boot_symbols_target_ramoops": vendor_symbols_target_ramoops,
        "stock_dtbo_overlay_disables_ramoops": stock_dtbo_disables_ramoops,
        "patched_dtbo_overlay_enables_ramoops": patched_dtbo_enables_ramoops,
    }
    conclusion = (
        "stock-dtbo-overlay-overrides-ramoops-status"
        if checks["live_ramoops_status_disabled"]
        and checks["vendor_boot_symbols_target_ramoops"]
        and checks["stock_dtbo_overlay_disables_ramoops"]
        else "inconclusive"
    )

    return {
        "generated_at_utc": utc_now(),
        "purpose": "read-only active DTB provenance audit for S22+ ramoops status",
        "device_action": "read-only-adb",
        "writes_performed": False,
        "serial_redacted": True,
        "paths": {
            "vendor_dtb": str(args.vendor_dtb),
            "patched_vendor_dtb": str(args.patched_vendor_dtb),
            "stock_dtbo": str(args.stock_dtbo),
            "patched_dtbo": str(args.patched_dtbo) if patched_dtbo.is_file() else "",
        },
        "hashes": {
            "vendor_dtb": sha256_file(vendor_dtb),
            "patched_vendor_dtb": sha256_file(patched_vendor_dtb),
            "stock_dtbo": sha256_file(stock_dtbo),
            "patched_dtbo": sha256_file(patched_dtbo) if patched_dtbo.is_file() else "",
        },
        "props": {
            "model": props.get("model", ""),
            "device": props.get("device", ""),
            "bootloader": props.get("bootloader", ""),
            "incremental": props.get("incremental", ""),
            "vbstate": props.get("vbstate", ""),
            "boot_recovery": props.get("boot_recovery", ""),
            "boot_completed": props.get("boot_completed", ""),
            "bootanim": props.get("bootanim", ""),
            "su_id_root": "uid=0(root)" in props.get("su_id", ""),
        },
        "partition_hashes": {
            "boot": boot_hash,
            "vendor_boot": vendor_boot_hash,
            "dtbo": dtbo_hash,
            "expected_boot_sha256": EXPECTED_BOOT_SHA256,
            "expected_vendor_boot_sha256": EXPECTED_STOCK_VENDOR_BOOT_SHA256,
            "expected_dtbo_sha256": EXPECTED_DTBO_SHA256,
        },
        "live": {
            "property_count": len(live_tree),
            "ramoops_props": live_ramoops,
        },
        "vendor_boot_dtb": {
            "blob_count": len(vendor_blobs),
            "blobs": [public_blob_summary(blob) for blob in vendor_blobs],
            "comparisons_to_live": comparisons,
            "best_blob_index": best["blob_index"] if best else None,
        },
        "patched_vendor_boot_dtb": {
            "blob_count": len(patched_vendor_blobs),
            "blobs": [public_blob_summary(blob) for blob in patched_vendor_blobs],
        },
        "stock_dtbo": {
            "ramoops_overlays": stock_dtbo_overlays,
        },
        "patched_dtbo": {
            "ramoops_overlays": patched_dtbo_overlays,
        },
        "checks": checks,
        "conclusion": conclusion,
        "result": "pass" if all(checks.values()) and conclusion != "inconclusive" else "fail",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", help="optional ADB serial to pin")
    parser.add_argument("--vendor-dtb", type=Path, default=DEFAULT_VENDOR_DTB)
    parser.add_argument("--patched-vendor-dtb", type=Path, default=DEFAULT_PATCHED_VENDOR_DTB)
    parser.add_argument("--stock-dtbo", type=Path, default=DEFAULT_STOCK_DTBO)
    parser.add_argument("--patched-dtbo", type=Path, default=DEFAULT_PATCHED_DTBO)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    report = build_report(args)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        root = repo_root()
        out = resolve(root, args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
