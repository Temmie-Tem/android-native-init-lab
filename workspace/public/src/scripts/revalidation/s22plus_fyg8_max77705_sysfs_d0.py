#!/usr/bin/env python3
"""Collect the exact read-only S22+ Max77705 substrate sysfs inventory."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
from typing import Any

import device_action_d0_v2 as d0
import device_action_f1_v2 as f1


VERSION = "s22plus-fyg8-max77705-sysfs-d0-v1"
SCHEMA = "s22plus_fyg8_max77705_sysfs_d0_v1"
VERDICT = "PASS_S22PLUS_FYG8_MAX77705_SYSFS_D0_READ_ONLY"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_MODEL = "SM-S906N"
EXPECTED_DEVICE = "g0q"
EXPECTED_INCREMENTAL = "S906NKSS7FYG8"
EXPECTED_ANDROID_USB_ID = ("04e8", "6860")
DEFAULT_ADB = Path("/usr/bin/adb")
DEFAULT_PROFILE = Path(
    "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
)
DEFAULT_RUN_ROOT = Path(
    "workspace/private/runs/s22plus-fyg8-max77705-sysfs-d0"
)
MAX_SNAPSHOT_BYTES = 512 * 1024
MAX_RECORDS = 64

COMPATIBLE_CLASSES = {
    "qcom,qupv3-geni-se": ("qupv3", 3, "qupv3_geni_se"),
    "qcom,gpi-dma": ("gpi", 3, "gpi_dma"),
    "qcom,i2c-geni": ("i2c", 9, "i2c_geni"),
}
TARGET_ADDRESS_BY_CLASS = {
    "qupv3": "9c0000",
    "gpi": "900000",
    "i2c": "994000",
}
TARGET_I2C_NAME = "994000.i2c"
MODULE_RUNTIME_NAMES = {
    "substrate": ("msm_geni_se", "gpi", "i2c_msm_geni"),
    "excluded": ("mfd_max77705", "pdic_max77705", "spu_verify"),
}
SAFE_NAME_RE = re.compile(r"[A-Za-z0-9,._:+-]{1,160}")
HEX_RE = re.compile(r"(?:[0-9a-f]{2})*")


class InventoryError(RuntimeError):
    pass


@dataclass(frozen=True)
class AdbRow:
    serial: str
    state: str
    metadata: frozenset[str]


@dataclass(frozen=True)
class Selection:
    serial: str
    serial_sha256: str
    rows: tuple[AdbRow, ...]
    other_serial_sha256: tuple[str, ...]


@dataclass(frozen=True)
class _ProfileView:
    profile: dict[str, Any]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def resolve(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_adb_inventory(text: str) -> tuple[AdbRow, ...]:
    rows: list[AdbRow] = []
    for line in text.splitlines():
        if not line or line.startswith("List of devices attached"):
            continue
        fields = line.split()
        if len(fields) < 2:
            raise InventoryError("ADB inventory contains a malformed row")
        serial, state = fields[:2]
        if d0.SERIAL_RE.fullmatch(serial) is None:
            raise InventoryError("ADB inventory contains an unsafe serial shape")
        rows.append(AdbRow(serial, state, frozenset(fields[2:])))
    return tuple(rows)


def select_exact_s22(text: str) -> Selection:
    rows = parse_adb_inventory(text)
    matches = [
        row
        for row in rows
        if row.state == "device"
        and "model:SM_S906N" in row.metadata
        and "device:g0q" in row.metadata
    ]
    if len(matches) != 1:
        raise InventoryError(
            f"expected exactly one connected FYG8 S22+, found {len(matches)}"
        )
    selected = matches[0]
    return Selection(
        serial=selected.serial,
        serial_sha256=sha256_text(selected.serial),
        rows=rows,
        other_serial_sha256=tuple(
            sorted(sha256_text(row.serial) for row in rows if row is not selected)
        ),
    )


def read_adb_inventory(adb: Path) -> tuple[str, Selection]:
    result = d0.bounded_command(
        [str(adb), "devices", "-l"], timeout=10, maximum=d0.MAX_TEXT_OUTPUT
    )
    if result.returncode != 0 or result.stderr:
        raise InventoryError("ADB inventory failed or produced stderr")
    try:
        text = result.stdout.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise InventoryError("ADB inventory is not UTF-8") from exc
    return text, select_exact_s22(text)


def _safe_fixture_path(value: str) -> str:
    if not value.startswith("/") or any(
        token in value for token in ("\n", "\r", "\t", "'", '"', "`", "$", ";")
    ):
        raise InventoryError("snapshot root has an unsafe shape")
    return value.rstrip("/") or "/"


def build_snapshot_script(
    *,
    platform_root: str = "/sys/bus/platform/devices",
    i2c_root: str = "/sys/bus/i2c/devices",
    proc_modules: str = "/proc/modules",
) -> str:
    platform_root = _safe_fixture_path(platform_root)
    i2c_root = _safe_fixture_path(i2c_root)
    proc_modules = _safe_fixture_path(proc_modules)
    # Every redirection below is an input read. The only output is stdout.
    return f"""set -eu
hex_file() {{
    if [ -r \"$1\" ]; then
        od -An -v -tx1 \"$1\" | tr -d ' \\n'
    fi
}}
hex_text() {{
    printf '%s' \"$1\" | od -An -v -tx1 | tr -d ' \\n'
}}
platform_root='{platform_root}'
i2c_root='{i2c_root}'
for d in \"$platform_root\"/*; do
    [ -e \"$d\" ] || continue
    [ -r \"$d/of_node/compatible\" ] || continue
    compat=$(tr '\\000' '\\n' < \"$d/of_node/compatible\")
    case \"$compat\" in
        *qcom,qupv3-geni-se*|*qcom,gpi-dma*|*qcom,i2c-geni*) ;;
        *) continue ;;
    esac
    name=${{d##*/}}
    device_path=$(readlink -f \"$d\")
    driver_present=0
    driver_path=''
    if [ -L \"$d/driver\" ]; then
        driver_present=1
        driver_path=$(readlink -f \"$d/driver\")
    fi
    override_present=0
    if [ -r \"$d/driver_override\" ]; then
        override_present=1
    fi
    printf 'P\\t'; hex_text \"$name\"; printf '\\t'; hex_text \"$device_path\"
    printf '\\t'; hex_file \"$d/of_node/compatible\"
    printf '\\t'; hex_file \"$d/modalias\"
    printf '\\t%s\\t' \"$override_present\"; hex_file \"$d/driver_override\"
    printf '\\t%s\\t' \"$driver_present\"; hex_text \"$driver_path\"; printf '\\n'
done
target=$(readlink -f \"$platform_root/{TARGET_I2C_NAME}\" 2>/dev/null || true)
printf 'T\\t'; hex_text \"$target\"; printf '\\n'
if [ -n \"$target\" ]; then
    for d in \"$i2c_root\"/*; do
        [ -e \"$d\" ] || continue
        device_path=$(readlink -f \"$d\")
        case \"$device_path\" in
            \"$target\"|\"$target\"/*) ;;
            *) continue ;;
        esac
        name=${{d##*/}}
        driver_present=0
        driver_path=''
        if [ -L \"$d/driver\" ]; then
            driver_present=1
            driver_path=$(readlink -f \"$d/driver\")
        fi
        printf 'I\\t'; hex_text \"$name\"; printf '\\t'; hex_text \"$device_path\"
        printf '\\t'; hex_file \"$d/of_node/compatible\"
        printf '\\t'; hex_file \"$d/modalias\"
        printf '\\t'; hex_file \"$d/name\"
        printf '\\t%s\\t' \"$driver_present\"; hex_text \"$driver_path\"; printf '\\n'
    done
fi
printf 'M\\t'; hex_file '{proc_modules}'; printf '\\n'
"""


SNAPSHOT_SCRIPT = build_snapshot_script()


def _decode_hex(value: str, label: str, maximum: int = 128 * 1024) -> bytes:
    if len(value) > maximum * 2 or HEX_RE.fullmatch(value) is None:
        raise InventoryError(f"{label} has malformed or oversized hex")
    return bytes.fromhex(value)


def _decode_text(value: str, label: str, maximum: int = 4096) -> str:
    payload = _decode_hex(value, label, maximum)
    if b"\x00" in payload:
        raise InventoryError(f"{label} contains an unexpected NUL")
    try:
        return payload.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise InventoryError(f"{label} is not UTF-8") from exc


def _decode_compatibles(value: str, label: str) -> tuple[str, ...]:
    payload = _decode_hex(value, label, 4096)
    if not payload or not payload.endswith(b"\x00"):
        raise InventoryError(f"{label} is not a NUL-terminated compatible list")
    try:
        values = tuple(
            item.decode("ascii", "strict") for item in payload.rstrip(b"\x00").split(b"\x00")
        )
    except UnicodeDecodeError as exc:
        raise InventoryError(f"{label} is not ASCII") from exc
    if not values or any(not item or len(item) > 160 for item in values):
        raise InventoryError(f"{label} contains an invalid compatible")
    return values


def _flag(value: str, label: str) -> bool:
    if value not in {"0", "1"}:
        raise InventoryError(f"{label} is not a binary flag")
    return value == "1"


def _name(value: str, label: str) -> str:
    name = _decode_text(value, label)
    if SAFE_NAME_RE.fullmatch(name) is None:
        raise InventoryError(f"{label} has an unsafe name")
    return name


def _path(value: str, label: str, *, allow_empty: bool = False) -> str:
    path = _decode_text(value, label)
    if allow_empty and not path:
        return path
    if (
        not path.startswith("/")
        or len(path) > 4096
        or any(ord(char) < 0x20 for char in path)
        or ".." in Path(path).parts
    ):
        raise InventoryError(f"{label} has an unsafe path")
    return path


def _single_class(compatibles: tuple[str, ...], label: str) -> tuple[str, str, str]:
    matches = [
        COMPATIBLE_CLASSES[value]
        for value in compatibles
        if value in COMPATIBLE_CLASSES
    ]
    if len(matches) != 1:
        raise InventoryError(f"{label} does not have exactly one target compatible")
    return matches[0]


def _parse_modules(payload: bytes) -> dict[str, Any]:
    try:
        text = payload.decode("ascii", "strict")
    except UnicodeDecodeError as exc:
        raise InventoryError("/proc/modules is not ASCII") from exc
    loaded: set[str] = set()
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 6 or SAFE_NAME_RE.fullmatch(fields[0]) is None:
            raise InventoryError("/proc/modules contains a malformed row")
        if fields[0] in loaded:
            raise InventoryError("/proc/modules contains a duplicate module")
        loaded.add(fields[0])
    return {
        group: {name: name in loaded for name in names}
        for group, names in MODULE_RUNTIME_NAMES.items()
    }


def parse_snapshot(payload: bytes) -> dict[str, Any]:
    if not payload or len(payload) > MAX_SNAPSHOT_BYTES:
        raise InventoryError("sysfs snapshot is empty or oversized")
    try:
        text = payload.decode("ascii", "strict")
    except UnicodeDecodeError as exc:
        raise InventoryError("sysfs snapshot is not ASCII") from exc
    lines = text.splitlines()
    if not lines or len(lines) > MAX_RECORDS:
        raise InventoryError("sysfs snapshot record count is invalid")

    platforms: list[dict[str, Any]] = []
    i2c_devices: list[dict[str, Any]] = []
    target_paths: list[str] = []
    module_payloads: list[bytes] = []
    for index, line in enumerate(lines):
        fields = line.split("\t")
        if fields[0] == "P" and len(fields) == 9:
            name = _name(fields[1], f"platform[{index}].name")
            path = _path(fields[2], f"platform[{index}].path")
            compatibles = _decode_compatibles(
                fields[3], f"platform[{index}].compatible"
            )
            class_name, _expected_count, expected_driver = _single_class(
                compatibles, f"platform[{index}]"
            )
            modalias = _decode_text(fields[4], f"platform[{index}].modalias").rstrip("\n")
            override_present = _flag(fields[5], f"platform[{index}].override")
            override_raw = _decode_hex(fields[6], f"platform[{index}].override_raw", 4096)
            try:
                override_text = override_raw.decode("utf-8", "strict").rstrip("\n")
            except UnicodeDecodeError as exc:
                raise InventoryError("driver_override is not UTF-8") from exc
            driver_present = _flag(fields[7], f"platform[{index}].driver")
            driver_path = _path(
                fields[8], f"platform[{index}].driver_path", allow_empty=True
            )
            if driver_present != bool(driver_path):
                raise InventoryError("platform driver flag/path disagree")
            if Path(path).name != name:
                raise InventoryError("platform name and resolved path disagree")
            platforms.append(
                {
                    "name": name,
                    "path": path,
                    "class": class_name,
                    "compatibles": list(compatibles),
                    "modalias": modalias,
                    "driver_override_present": override_present,
                    "driver_override_hex": override_raw.hex(),
                    "driver_override_text": override_text,
                    "driver_present": driver_present,
                    "driver_path": driver_path,
                    "driver_name": Path(driver_path).name if driver_path else "",
                    "expected_stock_driver": expected_driver,
                }
            )
        elif fields[0] == "T" and len(fields) == 2:
            target_paths.append(_path(fields[1], "target_i2c_path", allow_empty=True))
        elif fields[0] == "I" and len(fields) == 8:
            name = _name(fields[1], f"i2c[{index}].name")
            path = _path(fields[2], f"i2c[{index}].path")
            compatible = (
                list(_decode_compatibles(fields[3], f"i2c[{index}].compatible"))
                if fields[3]
                else []
            )
            modalias = _decode_text(fields[4], f"i2c[{index}].modalias").rstrip("\n")
            device_name = _decode_text(fields[5], f"i2c[{index}].device_name").rstrip("\n")
            driver_present = _flag(fields[6], f"i2c[{index}].driver")
            driver_path = _path(
                fields[7], f"i2c[{index}].driver_path", allow_empty=True
            )
            if driver_present != bool(driver_path):
                raise InventoryError("I2C driver flag/path disagree")
            i2c_devices.append(
                {
                    "name": name,
                    "path": path,
                    "compatibles": compatible,
                    "modalias": modalias,
                    "device_name": device_name,
                    "driver_present": driver_present,
                    "driver_path": driver_path,
                    "driver_name": Path(driver_path).name if driver_path else "",
                }
            )
        elif fields[0] == "M" and len(fields) == 2:
            module_payloads.append(_decode_hex(fields[1], "proc_modules"))
        else:
            raise InventoryError(f"sysfs snapshot record {index} is malformed")

    if len(target_paths) != 1 or not target_paths[0]:
        raise InventoryError("target 994000.i2c path is missing or duplicated")
    if len(module_payloads) != 1:
        raise InventoryError("/proc/modules snapshot is missing or duplicated")
    if len(platforms) != sum(value[1] for value in COMPATIBLE_CLASSES.values()):
        raise InventoryError("platform target-family total is not exactly 15")
    if len({item["name"] for item in platforms}) != len(platforms):
        raise InventoryError("platform inventory contains duplicate names")

    by_class: dict[str, list[dict[str, Any]]] = {}
    target_devices: dict[str, str] = {}
    for compatible, (class_name, expected_count, expected_driver) in COMPATIBLE_CLASSES.items():
        values = sorted(
            (item for item in platforms if item["class"] == class_name),
            key=lambda item: item["name"],
        )
        if len(values) != expected_count:
            raise InventoryError(f"{class_name} count is not {expected_count}")
        if any(item["expected_stock_driver"] != expected_driver for item in values):
            raise InventoryError(f"{class_name} driver authority drifted")
        target_address = TARGET_ADDRESS_BY_CLASS[class_name]
        targets = [item for item in values if item["name"].split(".", 1)[0] == target_address]
        if len(targets) != 1:
            raise InventoryError(f"{class_name} target address is ambiguous")
        target_devices[class_name] = targets[0]["name"]
        by_class[class_name] = values

    if target_devices["i2c"] != TARGET_I2C_NAME:
        raise InventoryError("target I2C sysfs name differs")
    target_path = target_paths[0]
    target_platform = next(item for item in platforms if item["name"] == TARGET_I2C_NAME)
    if target_platform["path"] != target_path:
        raise InventoryError("target I2C platform and topology paths disagree")

    target_names = set(target_devices.values())
    non_target = [item for item in platforms if item["name"] not in target_names]
    if len(non_target) != 12:
        raise InventoryError("non-target override set is not exactly 12")
    if any(not item["driver_override_present"] for item in non_target):
        raise InventoryError("a required non-target driver_override is absent")
    if any(item["driver_override_text"] not in {"", "(null)"} for item in platforms):
        raise InventoryError("a stock platform driver_override is non-default")
    if any(
        not item["driver_present"]
        or item["driver_name"] != item["expected_stock_driver"]
        for item in platforms
    ):
        raise InventoryError("a stock platform device has an unexpected binding")

    for item in i2c_devices:
        if not (item["path"] == target_path or item["path"].startswith(target_path + "/")):
            raise InventoryError("I2C topology escaped the target controller")
    max77705 = [item for item in i2c_devices if re.fullmatch(r"\d+-0066", item["name"])]
    if len(max77705) != 1:
        raise InventoryError("target adapter does not contain exactly one *-0066 client")
    if "maxim,max77705" not in max77705[0]["compatibles"]:
        raise InventoryError("the *-0066 client is not the Max77705 parent")

    return {
        "platform": {
            "counts": {name: len(values) for name, values in by_class.items()},
            "total": len(platforms),
            "target_devices": target_devices,
            "non_target_override_names": sorted(item["name"] for item in non_target),
            "devices": sorted(platforms, key=lambda item: item["name"]),
        },
        "target_i2c": {
            "platform_path": target_path,
            "max77705_client": max77705[0],
            "devices": sorted(i2c_devices, key=lambda item: item["name"]),
        },
        "modules": _parse_modules(module_payloads[0]),
    }


def snapshot_safety_contract(script: str = SNAPSHOT_SCRIPT) -> dict[str, Any]:
    forbidden = (
        "driver_override=",
        "/bind",
        "/unbind",
        " insmod",
        " modprobe",
        " rmmod",
        " setprop",
        " reboot",
        " stop ",
        " start ",
        " svc ",
        " tee ",
        "> /sys",
        ">/sys",
        "> /proc",
        ">/proc",
        "finit_module",
    )
    required = (
        "/sys/bus/platform/devices",
        "/sys/bus/i2c/devices",
        "/proc/modules",
        "driver_override",
        "readlink -f",
    )
    result = not any(token in script for token in forbidden) and all(
        token in script for token in required
    )
    return {
        "result": "pass" if result else "fail",
        "script_sha256": sha256_text(script),
        "forbidden_tokens_absent": {token: token not in script for token in forbidden},
        "required_reads_present": {token: token in script for token in required},
        "device_read_only": True,
        "sysfs_write": False,
        "module_action": False,
        "service_action": False,
        "reboot": False,
        "partition_write": False,
    }


def _root_snapshot(adb: Path, serial: str) -> bytes:
    result = d0.bounded_command(
        [str(adb), "-s", serial, "exec-out", "su", "-c", SNAPSHOT_SCRIPT],
        timeout=45,
        maximum=MAX_SNAPSHOT_BYTES,
    )
    if result.returncode != 0 or result.stderr:
        raise InventoryError("read-only sysfs snapshot failed or produced stderr")
    return result.stdout


def _host_android_usb_count(root: Path = d0.DEFAULT_USB_ROOT) -> int:
    if not root.is_dir():
        raise InventoryError("host USB sysfs is unavailable")
    count = 0
    for child in root.iterdir():
        vendor = d0._read_small(child / "idVendor")
        product = d0._read_small(child / "idProduct")
        if (vendor, product) == EXPECTED_ANDROID_USB_ID:
            count += 1
    return count


def _exact_identity(properties: dict[str, str]) -> None:
    expected = {
        "model": EXPECTED_MODEL,
        "device": EXPECTED_DEVICE,
        "incremental": EXPECTED_INCREMENTAL,
        "boot_completed": "1",
        "bootanim": "stopped",
    }
    if any(properties.get(name) != value for name, value in expected.items()):
        raise InventoryError("selected target is not healthy exact FYG8 Android")


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def durable_create(path: Path, payload: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o400,
    )
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise InventoryError("short private evidence write")
            offset += written
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != len(payload):
            raise InventoryError("private evidence identity differs")
    finally:
        os.close(descriptor)
    _fsync_dir(path.parent)


def allocate_run_dir(root: Path, requested: Path | None) -> Path:
    base = (root / DEFAULT_RUN_ROOT).resolve()
    base.mkdir(parents=True, exist_ok=True)
    _fsync_dir(base.parent)
    candidate = requested or base / (
        "d0-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + f"-{time.time_ns()}"
    )
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise InventoryError("D0 run directory escaped the private root") from exc
    resolved.mkdir(mode=0o700)
    _fsync_dir(resolved.parent)
    return resolved


def collect(
    root: Path,
    profile_path: Path,
    adb_path: Path,
    run_dir: Path,
) -> dict[str, Any]:
    safety = snapshot_safety_contract()
    if safety["result"] != "pass":
        raise InventoryError("read-only snapshot contract failed")
    profile, _payload = f1.load_json(profile_path, "S22+ FYG8 target profile")
    f1.validate_profile(profile)
    if profile.get("profile_id") != "s22plus-fyg8":
        raise InventoryError("D0 requires the exact S22+ FYG8 profile")

    adb = adb_path.resolve(strict=True)
    client = d0.AdbReadOnlyClient(
        adb, expected_model=EXPECTED_MODEL, expected_device=EXPECTED_DEVICE
    )
    host_tool = client.receipt()
    initial_usb = d0.usb_snapshot(d0.DEFAULT_USB_ROOT, profile["target"]["download"])
    if (
        not initial_usb["enumerated_devices"]
        or initial_usb["download_endpoint_count"]
        or _host_android_usb_count() != 1
    ):
        raise InventoryError("initial host USB state is not one exact Android endpoint")

    initial_text, selection = read_adb_inventory(adb)
    topology = client.topology(selection.serial)
    properties = client.properties(selection.serial)
    _exact_identity(properties)
    root_health = client.root_health(selection.serial)
    health = d0.validate_health(_ProfileView(profile), properties, root_health, True)
    raw = _root_snapshot(adb, selection.serial)
    inventory = parse_snapshot(raw)

    final_text, final_selection = read_adb_inventory(adb)
    final_topology = client.topology(final_selection.serial)
    final_properties = client.properties(final_selection.serial)
    final_usb = d0.usb_snapshot(d0.DEFAULT_USB_ROOT, profile["target"]["download"])
    if (
        final_selection.serial_sha256 != selection.serial_sha256
        or final_selection.other_serial_sha256 != selection.other_serial_sha256
        or final_text != initial_text
        or final_topology != topology
        or final_properties != properties
        or not final_usb["enumerated_devices"]
        or final_usb["download_endpoint_count"]
        or _host_android_usb_count() != 1
    ):
        raise InventoryError("exact target, inventory, health, or USB state changed during D0")

    raw_path = run_dir / "sysfs-snapshot.tsv"
    durable_create(raw_path, raw)
    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "verdict": VERDICT,
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "target": TARGET,
        "target_evidence": {
            "adb_serial_sha256": selection.serial_sha256,
            "adb_topology_sha256": sha256_text(topology),
            "inventory_row_count": len(selection.rows),
            "other_target_count": len(selection.other_serial_sha256),
            "other_serial_sha256": list(selection.other_serial_sha256),
            "other_target_command_count": 0,
            "identity": {
                "model": properties["model"],
                "device": properties["device"],
                "incremental": properties["incremental"],
            },
        },
        "health": health,
        "usb": {
            "initial": initial_usb,
            "final": final_usb,
            "android_endpoint_id": ":".join(EXPECTED_ANDROID_USB_ID),
            "android_endpoint_count": 1,
        },
        "inventory": inventory,
        "raw_evidence": {
            "path": raw_path.relative_to(root).as_posix(),
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
        "host_tool": host_tool,
        "safety": safety,
        "device_contact": True,
        "device_writes": False,
        "reboot_requested": False,
        "module_action": False,
        "service_action": False,
        "partition_transfer": False,
        "a90_command_count": 0,
        "f1_authorized": False,
    }
    encoded = json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n"
    durable_create(run_dir / "result.json", encoded)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--adb", type=Path, default=DEFAULT_ADB)
    parser.add_argument("--run-dir", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    safety = snapshot_safety_contract()
    if not args.collect:
        print(json.dumps(safety, indent=2, sort_keys=True))
        return 0 if safety["result"] == "pass" else 2
    root = repo_root()
    try:
        result = collect(
            root,
            resolve(root, args.profile),
            resolve(root, args.adb),
            allocate_run_dir(root, args.run_dir),
        )
    except (InventoryError, d0.D0Error, f1.F1V2Error, OSError) as exc:
        print(f"Max77705 sysfs D0 error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
