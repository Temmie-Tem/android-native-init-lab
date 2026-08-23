#!/usr/bin/env python3
"""Reconstruct how the pinned g0q TWRP image can expose a USB gadget.

Host-only.  The audit unpacks the exact retained TWRP recovery image in
memory, binds its kernel, DT/DTBO, ramdisk, module list and relevant ELF call
paths, and compares that older control with the current P3.19 module plan.
It never contacts a device and does not make TWRP evidence candidate-exact.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import tarfile
import tempfile
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVALIDATION = SCRIPT_DIR.parent / "revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_boot_verify as boot_verify  # noqa: E402
import s22plus_fyg8_p241_dtbo_role_contract as fdt_contract  # noqa: E402
import s22plus_fyg8_usb_role_static_re as static_re  # noqa: E402


SCHEMA = "s22plus-fyg8-p319-twrp-usb-role-control-v1"
VERDICT = "PASS_P319_TWRP_USB_ROLE_CONTROL_H0"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}

TWRP_TAR = ROOT / (
    "workspace/private/inputs/s22plus_twrp/g0q/"
    "twrp-3.7.0_12-1_afaneh92-g0q.tar"
)
HISTORICAL_LIVE_REPORT = ROOT / (
    "docs/reports/S22PLUS_TWRP_RECOVERY_INFRA_LIVE_2026-07-06.md"
)
PHASE = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "stock-witness-runtime-v1-20260821-50"
)
PHASE_RESULT = PHASE / "result.json"
ROLE_SOURCE = PHASE / "stock-sources/s22plus_fyg8_p260_e3_runtime.inc.c"
MODULE_DIR = PHASE / "module-bytes"
OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "twrp-usb-role-control-v1-20260824-01/result.json"
)

EXPECTED_INPUTS = {
    "twrp_tar": (
        55_437_312,
        "0914c68a5353c367216805a3a2fdeb4982c6629368dc021c7fefc10d3d3bd034",
    ),
    "historical_live_report": (
        4_480,
        "0ec2a8e2582bbfecf11de8aadf504ae8b2d48ceac88257a46a82b05b5b8fb427",
    ),
    "phase_result": (
        382_264,
        "982f903f7685f63e5b2fbadebc5a3bbef5d98f009207ac352bda80777b09e886",
    ),
    "role_source": (
        20_665,
        "767bd359de56cb24be84c4479cd01d4f710a676490c23f966617b996fe5cc612",
    ),
}

EXPECTED_BOOT_PARTS = {
    "recovery_img": (
        55_435_280,
        "e4e1861760298da756d1d649029c33b4c953f12272ebda1705214da56245e036",
    ),
    "kernel_gzip": (
        18_881_335,
        "7273b7497dff650b8fb0192c0c2e7bac2cb237409a1e0448162d410cdb41be63",
    ),
    "kernel_image": (
        41_488_896,
        "6beb83aa231749d503e101e0d3bbcb9512a2da9a629d10bc220a5e842e48af68",
    ),
    "ramdisk_gzip": (
        31_358_693,
        "1b1555163106adf128724bfa27444f64518b81bcd44f248ae54fbac8b9d9b354",
    ),
    "ramdisk_cpio": (
        111_237_120,
        "d196983473bf0f24fbe94c3cb8db5c02bd31887ff27b517ce557b24aa2e9182c",
    ),
    "dtb": (
        1_717_704,
        "3a4b3cc7ab17617434775dea33fb9d0979bb763e20857c88647441aab84a0092",
    ),
    "recovery_dtbo": (
        3_465_249,
        "daaa8789fe64a91d59068ecae259adbfd0f9d92e2a3a29abf24503fbcf10adca",
    ),
    "ikconfig": (
        184_059,
        "2224da95de717a31bb3d1d1ccd2fdd3aa7f1b4c54d7d4d918773b01e465872d5",
    ),
}

EXPECTED_BASE_DTBS = (
    (0, 429_426, "eb61036216278cd45cd5d92b9a8b52f5e580258099f0b67fa8fe063eca775a21"),
    (429_426, 429_406, "e7c5d9b6fdb7ef6a9d5ff1aa749c128a816703916069c9b45314aaeda85b2f7d"),
    (858_832, 429_438, "d8d4af27ec3a27085271ab7ef6400ba533b3b6cf32fac730315a218f0f0d645c"),
    (1_288_270, 429_434, "773b69673a8741479063f5b0d8811d3950fc1e91959f28c6ef8d05594150a71c"),
)

EXPECTED_OVERLAYS = (
    (192, 692_681, "44a84009b41c78d0fb4a159e075599b514ad78b68dfff7bb002461ca7bec2e1c"),
    (692_873, 692_881, "0f1cdd3b2c50d82d19898b73c6cec1c06b0bae26744fb2fbd0f4d005c7686b23"),
    (1_385_754, 692_965, "eaf837e6a7d0b1c62c963ca2455ccc5b0da420a457d974fb79c4416a5f4e6082"),
    (2_078_719, 693_225, "61d8bc4996131df86fa043608489ce3d0ad7b8b38095ef93bfcb35239a2912f5"),
    (2_771_944, 693_305, "4fa75341696267940a2aea818bb235404ef9d8e427df4498969642770416815c"),
)

RELEVANT_MODULES = {
    "eud.ko": (45_384, "39fcbb84858cd40582173fc3dfa1269ae6f87e880d489e910e2efa0f57284c2c"),
    "pmic_glink.ko": (36_352, "8b858b34cff4ac01a69256852614d9ae7ee9fe3f8ce0f63c2112ebdde376f762"),
    "usb_typec_manager.ko": (73_056, "5614fbad900701c3b131507243b4f84cec8f6e93e4f60b51ac6be5c19c71dfec"),
    "dwc3-msm.ko": (281_352, "34c5bf46a1b121f5856188bc8c281260d92255031e1e02ec818e9e4409426dec"),
    "usb_notifier_qcom.ko": (26_336, "02b4233d72277e708c7ddfed6d18c600366c31b95aafeb78e173369240bdb8c6"),
    "ucsi_glink.ko": (35_760, "489f85cdd3db1187a428cc45746c1eb480663ecb941235593094f1fda370c70b"),
    "qcom_q6v5.ko": (24_560, "9ab7cbaa8e5834d12d0da0db6d292834cb52e3285a1a07cb71bd921ca6d854e5"),
    "qcom_q6v5_pas.ko": (86_328, "6c893f4b685e972f9165bf044ed5de44b2d830f7a92e24b441a5f4a6a16a5b32"),
    "mfd_max77705.ko": (125_088, "b0471ab20b6c5b949758e38ad5de9c17662277044c0294a574c7f9a7a1fbf9f2"),
    "pdic_max77705.ko": (412_688, "fd034e6a8e1c4914dda75ac790be2d6ec1f93e9acc60c20165b1252924d16870"),
}

CURRENT_COMPARISON_MODULES = (
    "eud.ko",
    "pmic_glink.ko",
    "usb_typec_manager.ko",
    "dwc3-msm.ko",
    "usb_notifier_qcom.ko",
    "ucsi_glink.ko",
    "mfd_max77705.ko",
    "pdic_max77705.ko",
)

HELPERS = {
    "cpio": REVALIDATION / "s22plus_boot_verify.py",
    "fdt": REVALIDATION / "s22plus_fyg8_p241_dtbo_role_contract.py",
    "elf": REVALIDATION / "s22plus_fyg8_usb_role_static_re.py",
}


class AuditError(RuntimeError):
    """An exact artifact, parser, topology, or evidence boundary differs."""


_BOUND_AUDITOR_SOURCE = globals().get("_P319_TWRP_ROLE_BOUND_SOURCE")


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": sha256(payload)}


def _stat_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def stable_bytes(
    path: Path,
    label: str,
    maximum: int,
    expected: tuple[int, str] | None = None,
) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AuditError(f"{label} is unavailable") from exc
    if (
        resolved.name != direct.name
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink < 1
        or len(payload) != before.st_size
        or len(payload) > maximum
        or _stat_identity(before) != _stat_identity(inside)
        or _stat_identity(before) != _stat_identity(after)
        or expected is not None
        and identity(payload) != {"size": expected[0], "sha256": expected[1]}
    ):
        raise AuditError(f"{label} identity differs")
    return payload


def load_bound_auditor() -> types.ModuleType:
    source = stable_bytes(Path(__file__), "auditor", 1024 * 1024)
    module = types.ModuleType("p319_twrp_usb_role_control_bound")
    module.__dict__["__file__"] = str(Path(__file__).resolve())
    module.__dict__["_P319_TWRP_ROLE_BOUND_SOURCE"] = source
    exec(compile(source, str(Path(__file__).resolve()), "exec"), module.__dict__)
    return module


def _expect(payload: bytes, expected: tuple[int, str], label: str) -> bytes:
    if identity(payload) != {"size": expected[0], "sha256": expected[1]}:
        raise AuditError(f"{label} identity differs")
    return payload


def _ascii(payload: bytes, label: str) -> str:
    try:
        return payload.decode("ascii")
    except UnicodeDecodeError as exc:
        raise AuditError(f"{label} is not ASCII") from exc


def _json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not JSON") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} root is not an object")
    return value


def _align(value: int, boundary: int) -> int:
    return (value + boundary - 1) // boundary * boundary


def extract_recovery_image(tar_payload: bytes) -> tuple[bytes, dict[str, Any]]:
    try:
        with tarfile.open(fileobj=io.BytesIO(tar_payload), mode="r:") as archive:
            members = archive.getmembers()
            if (
                len(members) != 1
                or members[0].name != "recovery.img"
                or not members[0].isreg()
                or members[0].size != EXPECTED_BOOT_PARTS["recovery_img"][0]
            ):
                raise AuditError("TWRP tar membership differs")
            stream = archive.extractfile(members[0])
            if stream is None:
                raise AuditError("TWRP recovery member is unreadable")
            recovery = stream.read()
            metadata = {
                "name": members[0].name,
                "size": members[0].size,
                "mode": members[0].mode,
                "mtime": members[0].mtime,
                "uid": members[0].uid,
                "gid": members[0].gid,
            }
    except (tarfile.TarError, OSError) as exc:
        raise AuditError("TWRP tar is not a bounded single-member archive") from exc
    _expect(recovery, EXPECTED_BOOT_PARTS["recovery_img"], "TWRP recovery image")
    return recovery, metadata


def parse_boot_image(recovery: bytes) -> tuple[dict[str, Any], dict[str, bytes]]:
    if len(recovery) < 4096 or recovery[:8] != b"ANDROID!":
        raise AuditError("TWRP recovery boot magic differs")
    values = struct.unpack_from("<9I", recovery, 8)
    (
        kernel_size,
        kernel_addr,
        ramdisk_size,
        ramdisk_addr,
        second_size,
        second_addr,
        tags_addr,
        page_size,
        header_version,
    ) = values
    os_version = struct.unpack_from("<I", recovery, 44)[0]
    product = recovery[48:64].split(b"\0", 1)[0].decode("ascii")
    cmdline = (
        recovery[64:576] + recovery[608:1632]
    ).split(b"\0", 1)[0].decode("ascii")
    recovery_dtbo_size = struct.unpack_from("<I", recovery, 1632)[0]
    recovery_dtbo_offset = struct.unpack_from("<Q", recovery, 1636)[0]
    header_size = struct.unpack_from("<I", recovery, 1644)[0]
    dtb_size = struct.unpack_from("<I", recovery, 1648)[0]
    dtb_addr = struct.unpack_from("<Q", recovery, 1652)[0]
    expected_header = {
        "header_version": 2,
        "header_size": 1660,
        "page_size": 4096,
        "kernel_size": EXPECTED_BOOT_PARTS["kernel_gzip"][0],
        "ramdisk_size": EXPECTED_BOOT_PARTS["ramdisk_gzip"][0],
        "second_size": 0,
        "recovery_dtbo_size": EXPECTED_BOOT_PARTS["recovery_dtbo"][0],
        "dtb_size": EXPECTED_BOOT_PARTS["dtb"][0],
        "recovery_dtbo_offset": 0x2FEB000,
        "product": "SRPUI14B002",
    }
    actual_header = {
        "header_version": header_version,
        "header_size": header_size,
        "page_size": page_size,
        "kernel_size": kernel_size,
        "ramdisk_size": ramdisk_size,
        "second_size": second_size,
        "recovery_dtbo_size": recovery_dtbo_size,
        "dtb_size": dtb_size,
        "recovery_dtbo_offset": recovery_dtbo_offset,
        "product": product,
    }
    if actual_header != expected_header or second_addr != 0:
        raise AuditError("TWRP recovery header differs")
    kernel_offset = page_size
    ramdisk_offset = _align(kernel_offset + kernel_size, page_size)
    dtb_offset = _align(recovery_dtbo_offset + recovery_dtbo_size, page_size)
    intervals = (
        ("kernel_gzip", kernel_offset, kernel_size),
        ("ramdisk_gzip", ramdisk_offset, ramdisk_size),
        ("recovery_dtbo", recovery_dtbo_offset, recovery_dtbo_size),
        ("dtb", dtb_offset, dtb_size),
    )
    parts: dict[str, bytes] = {}
    prior_end = page_size
    for name, offset, size in intervals:
        if offset < prior_end or offset + size > len(recovery):
            raise AuditError(f"TWRP {name} bounds differ")
        if any(recovery[prior_end:offset]):
            raise AuditError(f"TWRP {name} leading padding is nonzero")
        parts[name] = _expect(
            recovery[offset : offset + size], EXPECTED_BOOT_PARTS[name], name
        )
        prior_end = offset + size
    footer = b"SEANDROIDENFORCE"
    footer_offset = len(recovery) - len(footer)
    if footer_offset < prior_end or any(recovery[prior_end:footer_offset]) or recovery[footer_offset:] != footer:
        raise AuditError("TWRP recovery footer or trailing padding differs")
    header = {
        **actual_header,
        "kernel_load_address": f"0x{kernel_addr:08x}",
        "ramdisk_load_address": f"0x{ramdisk_addr:08x}",
        "second_load_address": f"0x{second_addr:08x}",
        "tags_load_address": f"0x{tags_addr:08x}",
        "dtb_load_address": f"0x{dtb_addr:016x}",
        "os_version_patch_raw": os_version,
        "cmdline": cmdline,
        "offsets": {name: offset for name, offset, _size in intervals},
        "all_inter_part_padding_zero": True,
        "samsung_footer": footer.decode("ascii"),
        "samsung_footer_offset": footer_offset,
        "pre_footer_padding_zero": True,
    }
    return header, parts


def extract_ikconfig(image: bytes) -> tuple[bytes, dict[str, str]]:
    if image.count(b"IKCFG_ST") != 1 or image.count(b"IKCFG_ED") != 1:
        raise AuditError("TWRP IKCONFIG marker count differs")
    start = image.index(b"IKCFG_ST") + 8
    end = image.index(b"IKCFG_ED", start)
    try:
        config = gzip.decompress(image[start:end])
    except (OSError, EOFError) as exc:
        raise AuditError("TWRP IKCONFIG is not gzip") from exc
    _expect(config, EXPECTED_BOOT_PARTS["ikconfig"], "TWRP IKCONFIG")
    values: dict[str, str] = {}
    for line in _ascii(config, "TWRP IKCONFIG").splitlines():
        if line.startswith("CONFIG_") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            values[line[2 : line.index(" is not set")]] = "n"
    required = {
        "CONFIG_MODULES": "y",
        "CONFIG_USB": "y",
        "CONFIG_USB_GADGET": "y",
        "CONFIG_USB_DWC3": "y",
        "CONFIG_USB_DWC3_DUAL_ROLE": "y",
        "CONFIG_USB_ROLE_SWITCH": "y",
        "CONFIG_TYPEC": "y",
        "CONFIG_TYPEC_UCSI": "y",
        "CONFIG_EXTCON": "y",
        "CONFIG_USB_CONFIGFS": "y",
        "CONFIG_USB_CONFIGFS_F_FS": "y",
    }
    if any(values.get(key) != value for key, value in required.items()):
        raise AuditError("TWRP kernel USB configuration differs")
    banner_match = re.search(
        rb"Linux version 5\.10\.81-afaneh92-g0418bf01a3e2[^\0]+", image
    )
    if banner_match is None:
        raise AuditError("TWRP kernel banner differs")
    return config, {**required, "kernel_banner": banner_match.group().decode("ascii")}


def split_base_dtbs(data: bytes) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while offset < len(data):
        if offset + 8 > len(data):
            raise AuditError("TWRP base DTB stream is truncated")
        magic, size = struct.unpack_from(">2I", data, offset)
        if magic != fdt_contract.FDT_MAGIC or size < 40 or offset + size > len(data):
            raise AuditError("TWRP base DTB boundary differs")
        blob = data[offset : offset + size]
        nodes = fdt_contract.parse_fdt(blob)
        by_path = {node.path: node for node in nodes}
        parent = by_path.get("/soc/ssusb@a600000")
        child = by_path.get("/soc/ssusb@a600000/dwc3@a600000")
        ucsi = by_path.get("/soc/qcom,pmic_glink/qcom,ucsi")
        root = by_path.get("/")
        if None in (parent, child, ucsi, root):
            raise AuditError("TWRP base DTB USB nodes are absent")
        assert parent is not None and child is not None and ucsi is not None and root is not None
        phandles = {
            struct.unpack(">I", node.properties["phandle"])[0]: node.path
            for node in nodes
            if len(node.properties.get("phandle", b"")) == 4
        }
        extcon = parent.properties.get("extcon", b"")
        if (
            fdt_contract.string_list(parent.properties.get("compatible", b""))
            != ("qcom,dwc-usb3-msm",)
            or fdt_contract.string_list(child.properties.get("dr_mode", b""))
            != ("otg",)
            or child.properties.get("usb-role-switch") != b""
            or len(extcon) != 4
            or phandles.get(struct.unpack(">I", extcon)[0])
            != "/soc/qcom,msm-eud@88e0000"
            or fdt_contract.string_list(ucsi.properties.get("compatible", b""))
            != ("qcom,ucsi-glink",)
        ):
            raise AuditError("TWRP base DTB USB topology differs")
        rows.append(
            {
                "index": len(rows),
                "offset": offset,
                "size": size,
                "sha256": sha256(blob),
                "node_count": len(nodes),
                "model": fdt_contract.string_list(root.properties["model"])[0],
                "parent_compatible": "qcom,dwc-usb3-msm",
                "child_dr_mode": "otg",
                "child_role_switch": True,
                "parent_extcon_provider": "/soc/qcom,msm-eud@88e0000",
                "ucsi_compatible": "qcom,ucsi-glink",
            }
        )
        offset += size
    observed = tuple((row["offset"], row["size"], row["sha256"]) for row in rows)
    if observed != EXPECTED_BASE_DTBS:
        raise AuditError("TWRP base DTB manifest differs")
    return rows


def parse_recovery_dtbo(data: bytes) -> list[dict[str, Any]]:
    if len(data) < 32:
        raise AuditError("TWRP recovery DTBO is truncated")
    magic, total, header, entry_size, count, entries, page, version = struct.unpack_from(
        ">8I", data, 0
    )
    if (
        magic != fdt_contract.DT_TABLE_MAGIC
        or total != len(data)
        or header != 32
        or entry_size != 32
        or count != 5
        or entries != 32
        or page != 4096
        or version != 0
    ):
        raise AuditError("TWRP recovery DTBO table header differs")
    rows: list[dict[str, Any]] = []
    expected_start = header + count * entry_size
    for index in range(count):
        size, offset, entry_id, revision, *custom = struct.unpack_from(
            ">8I", data, entries + index * entry_size
        )
        if offset != expected_start or offset + size > len(data):
            raise AuditError("TWRP recovery DTBO entry geometry differs")
        blob = data[offset : offset + size]
        nodes = fdt_contract.parse_fdt(blob)
        row = {
            "index": index,
            "offset": offset,
            "size": size,
            "id": entry_id,
            "revision": revision,
            "custom": custom,
            "sha256": sha256(blob),
            "nodes": nodes,
        }
        inspected = fdt_contract.inspect_entry(row)
        rows.append(inspected)
        expected_start = offset + size
    if expected_start != len(data):
        raise AuditError("TWRP recovery DTBO has trailing bytes")
    observed = tuple((row["offset"], row["size"], row["sha256"]) for row in rows)
    if observed != EXPECTED_OVERLAYS:
        raise AuditError("TWRP recovery DTBO manifest differs")
    return rows


def cpio_map(ramdisk_gzip: bytes) -> tuple[bytes, dict[str, boot_verify.CpioEntry]]:
    try:
        cpio = gzip.decompress(ramdisk_gzip)
    except (OSError, EOFError) as exc:
        raise AuditError("TWRP ramdisk is not gzip") from exc
    _expect(cpio, EXPECTED_BOOT_PARTS["ramdisk_cpio"], "TWRP ramdisk CPIO")
    try:
        entries = boot_verify.parse_newc(cpio)
    except boot_verify.BootVerifyError as exc:
        raise AuditError("TWRP ramdisk CPIO is invalid") from exc
    if len(entries) != 3965 or len({entry.name for entry in entries}) != 3965:
        raise AuditError("TWRP ramdisk population differs")
    return cpio, {entry.name: entry for entry in entries}


def audit_userspace(entries: dict[str, boot_verify.CpioEntry]) -> dict[str, Any]:
    required = (
        "init.recovery.usb.rc",
        "system/etc/init/hw/init.rc",
        "prop.default",
        "system/bin/init",
        "lib/modules/modules.load.recovery",
        "lib/modules/modules.dep",
    )
    if any(name not in entries or entries[name].file_type != "regular" for name in required):
        raise AuditError("TWRP userspace authority files are absent")
    default_link = entries.get("default.prop")
    if (
        default_link is None
        or default_link.file_type != "symlink"
        or default_link.data != b"prop.default"
    ):
        raise AuditError("TWRP default.prop symlink differs")
    usb_rc = _ascii(entries["init.recovery.usb.rc"].data, "TWRP USB rc")
    default_prop = _ascii(entries["prop.default"].data, "TWRP default.prop")
    direct_role_tokens = (b"a600000.ssusb", b"ssusb/mode")
    hidden: dict[str, list[str]] = {}
    for token in direct_role_tokens:
        hidden[token.decode("ascii")] = sorted(
            entry.name
            for entry in entries.values()
            if entry.file_type == "regular"
            and not entry.name.startswith("lib/modules/")
            and token in entry.data
        )
    if any(hidden.values()):
        raise AuditError("TWRP userspace contains an unregistered SSUSB role write")
    bind_line = "write /config/usb_gadget/g1/UDC ${sys.usb.controller}"
    if (
        usb_rc.count(bind_line) != 4
        or usb_rc.count('write /config/usb_gadget/g1/UDC "none"') != 1
        or "wait /sys/class/udc" in usb_rc
        or "sys.usb.controller=a600000.dwc3" not in default_prop
    ):
        raise AuditError("TWRP configfs/UDC recipe differs")
    init_strings = entries["system/bin/init"].data
    for token in (
        b"modules.load.recovery",
        b"system/core/init/first_stage_init.cpp",
        b"system/core/libmodprobe/libmodprobe.cpp",
    ):
        if token not in init_strings:
            raise AuditError("TWRP first-stage module-loader identity differs")
    return {
        "ramdisk_entry_count": len(entries),
        "regular_file_count": sum(entry.file_type == "regular" for entry in entries.values()),
        "symlink_count": sum(entry.file_type == "symlink" for entry in entries.values()),
        "directory_count": sum(entry.file_type == "directory" for entry in entries.values()),
        "usb_rc": identity(entries["init.recovery.usb.rc"].data),
        "default_prop": identity(entries["prop.default"].data),
        "default_prop_symlink": {
            **identity(default_link.data),
            "target": "prop.default",
        },
        "first_stage_init": identity(entries["system/bin/init"].data),
        "controller_property": "a600000.dwc3",
        "configfs_udc_bind_count": 4,
        "configfs_udc_unbind_count": 1,
        "explicit_udc_wait": False,
        "explicit_ssusb_mode_write": False,
        "hidden_role_write_scan": hidden,
        "first_stage_module_loader_strings_present": True,
    }


def _parse_modules_dep(payload: bytes) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for line in _ascii(payload, "TWRP modules.dep").splitlines():
        if ":" not in line:
            raise AuditError("TWRP modules.dep grammar differs")
        left, right = line.split(":", 1)
        name = Path(left).name
        if name in values:
            raise AuditError("TWRP modules.dep has duplicate providers")
        values[name] = [Path(item).name for item in right.split()]
    return values


def _dependency_closure(dependencies: dict[str, list[str]], root: str) -> set[str]:
    pending = [root]
    found: set[str] = set()
    while pending:
        current = pending.pop()
        if current not in dependencies:
            raise AuditError(f"TWRP dependency provider is absent: {current}")
        for dependency in dependencies[current]:
            if dependency not in found:
                found.add(dependency)
                pending.append(dependency)
    return found


DWC3_REQUIRED_EDGES = {
    ("dwc3_msm_probe", "usb_role_switch_register"),
    ("dwc3_msm_probe", "queue_delayed_work_on"),
    ("dwc3_otg_sm_work", "dwc3_msm_core_init"),
    ("dwc3_msm_core_init", "of_platform_populate"),
    ("dwc3_msm_usb_role_switch_set_role", "dwc3_msm_set_role"),
    ("dwc3_msm_set_role", "dwc3_ext_event_notify"),
    ("dwc3_ext_event_notify", "queue_delayed_work_on"),
    ("dwc3_otg_sm_work", "dwc3_otg_start_peripheral"),
    ("mode_store", "dwc3_msm_set_role"),
}

DWC3_EXPECTED_SYMBOLS = {
    "dwc3_msm_probe": (0x5D38, 0xFFC),
    "dwc3_ext_event_notify": (0x4838, 0x3D0),
    "mode_store": (0x9E3C, 0xA8),
    "dwc3_msm_set_role": (0x9EE4, 0x1A0),
    "dwc3_otg_sm_work": (0xA4D4, 0x5CC),
    "dwc3_msm_usb_role_switch_set_role": (0xACC4, 0x38),
    "dwc3_msm_core_init": (0xAF9C, 0x57C),
    "dwc3_otg_start_peripheral": (0xC404, 0xC0C),
}

NOTIFIER_REQUIRED_EDGES = {
    ("usb_notifier_probe", "manager_notifier_register"),
    ("usb_notifier_probe", "muic_notifier_register"),
    ("usb_notifier_probe", "vbus_notifier_register"),
    ("ccic_usb_handle_notification", "send_otg_notify"),
    ("muic_usb_handle_notification", "send_otg_notify"),
    ("qcom_set_peripheral", "dwc_msm_vbus_event"),
}

PDIC_REQUIRED_EDGES = {
    ("max77705_usbc_probe", "max77705_muic_probe"),
    ("max77705_muic_probe", "max77705_muic_detect_dev"),
    ("max77705_ccic_event_notifier", "pdic_notifier_notify"),
}

UCSI_REQUIRED_EDGES = {
    ("ucsi_probe", "pmic_glink_register_client"),
    ("ucsi_probe", "ucsi_setup"),
    ("ucsi_qti_state_cb", "queue_work_on"),
    ("ucsi_qti_setup_work", "ucsi_setup"),
}


def _edges_for(payload: bytes, name: str, directory: Path) -> tuple[Path, set[tuple[str, str]]]:
    path = directory / name
    path.write_bytes(payload)
    symbols, by_address = static_re.parse_symbols(path)
    if not symbols:
        raise AuditError(f"TWRP {name} has no symbols")
    return path, static_re.parse_call_edges(path, by_address)


def audit_elf_modules(
    modules: dict[str, bytes], *, enforce_identities: bool = True
) -> dict[str, Any]:
    if enforce_identities:
        for name, expected in RELEVANT_MODULES.items():
            if name not in modules:
                raise AuditError(f"TWRP module is absent: {name}")
            _expect(modules[name], expected, f"TWRP module {name}")
    with tempfile.TemporaryDirectory(prefix="p319-twrp-role-elf-") as temporary:
        directory = Path(temporary)
        dwc3_path, dwc3_edges = _edges_for(modules["dwc3-msm.ko"], "dwc3-msm.ko", directory)
        notifier_path, notifier_edges = _edges_for(
            modules["usb_notifier_qcom.ko"], "usb_notifier_qcom.ko", directory
        )
        _pdic_path, pdic_edges = _edges_for(
            modules["pdic_max77705.ko"], "pdic_max77705.ko", directory
        )
        _ucsi_path, ucsi_edges = _edges_for(
            modules["ucsi_glink.ko"], "ucsi_glink.ko", directory
        )
        missing = {
            "dwc3": sorted(DWC3_REQUIRED_EDGES - dwc3_edges),
            "notifier": sorted(NOTIFIER_REQUIRED_EDGES - notifier_edges),
            "pdic": sorted(PDIC_REQUIRED_EDGES - pdic_edges),
            "ucsi": sorted(UCSI_REQUIRED_EDGES - ucsi_edges),
        }
        if any(missing.values()):
            raise AuditError(f"TWRP automatic role ELF edges differ: {missing}")
        dwc3_symbols, _dwc3_by_address = static_re.parse_symbols(dwc3_path)
        symbol_layout = {
            name: (dwc3_symbols.get(name, {}).get("address"), dwc3_symbols.get(name, {}).get("size"))
            for name in DWC3_EXPECTED_SYMBOLS
        }
        if symbol_layout != DWC3_EXPECTED_SYMBOLS:
            raise AuditError(f"TWRP DWC3 symbol layout differs: {symbol_layout}")
        blocks = static_re.parse_function_blocks(dwc3_path)
        probe = static_re.normalized_instructions(blocks.get("dwc3_msm_probe", ""))
        state_machine = static_re.normalized_instructions(
            blocks.get("dwc3_otg_sm_work", "")
        )
        instruction_checks = {
            "probe_allocates_zero_initialized_state": all(
                token in probe
                for token in (
                    "movw1,#0x8c0",
                    "movw2,#0xdc0",
                    "r_aarch64_call26devm_kmalloc",
                )
            ),
            "probe_queues_otg_state_machine": (
                "r_aarch64_call26queue_delayed_work_on" in probe
            ),
            "zero_state_calls_core_init_then_records_state_one": bool(
                re.search(
                    r"ldrw8,\[x19,#792\].*cmpw8,#0x4.*"
                    r"r_aarch64_call26\.text\+0xaf9c.*cbzw0,.*"
                    r"movw8,#0x1.*strw8,\[x19,#792\]",
                    state_machine,
                )
            ),
        }
        if not all(instruction_checks.values()):
            raise AuditError(
                f"TWRP DWC3 bootstrap instructions differ: {instruction_checks}"
            )
        relocations = static_re.run_tool(
            ["aarch64-linux-gnu-readelf", "-rW", str(notifier_path)]
        )
        callback_binding = bool(
            re.search(
                r"^0000000000000140\s+.*R_AARCH64_ABS64\s+.*\.text \+ b98$",
                relocations,
                re.MULTILINE,
            )
        )
        symbols, _by_address = static_re.parse_symbols(notifier_path)
        if (
            not callback_binding
            or symbols.get("qcom_set_peripheral.cfi_jt", {}).get("address") != 0xB98
        ):
            raise AuditError("TWRP set_peripheral callback binding differs")
        dwc3_info = static_re.run_tool(["modinfo", str(dwc3_path)])
        if (
            "5.10.81-android12-9-gki-24339823-abS906EXXU2AVF9" not in dwc3_info
            or "DesignWare USB3 MSM Glue Layer" not in dwc3_info
        ):
            raise AuditError("TWRP DWC3 module provenance differs")
    format_edges = lambda values: [f"{caller}->{callee}" for caller, callee in sorted(values)]
    return {
        "dwc3_bootstrap_edges": format_edges(DWC3_REQUIRED_EDGES),
        "dwc3_symbol_layout": {
            name: {"address": hex(address), "size": size}
            for name, (address, size) in sorted(DWC3_EXPECTED_SYMBOLS.items())
        },
        "udc_bootstrap_instruction_checks": instruction_checks,
        "samsung_notifier_edges": format_edges(NOTIFIER_REQUIRED_EDGES),
        "pdic_edges": format_edges(PDIC_REQUIRED_EDGES),
        "ucsi_transport_edges": format_edges(UCSI_REQUIRED_EDGES),
        "set_peripheral_callback": {
            "relocation_offset": "0x140",
            "cfi_target": "qcom_set_peripheral.cfi_jt",
            "target_address": "0xb98",
            "bound": True,
        },
        "dwc3_module_vermagic": (
            "5.10.81-android12-9-gki-24339823-abS906EXXU2AVF9 "
            "SMP preempt mod_unload modversions aarch64"
        ),
    }


def audit_module_population(
    entries: dict[str, boot_verify.CpioEntry], phase: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, bytes]]:
    load_entry = entries["lib/modules/modules.load.recovery"]
    dep_entry = entries["lib/modules/modules.dep"]
    if identity(load_entry.data) != {
        "size": 7_116,
        "sha256": "99d53b684fea37ba51852f3709a4ad0e48df2564632b8f8badcbe54f86959be1",
    } or identity(dep_entry.data) != {
        "size": 73_437,
        "sha256": "69949e96a2e34b6fd84732e2b6939c429369813c99979a24b645cc0b11d1f3cf",
    }:
        raise AuditError("TWRP module metadata identity differs")
    load = [line for line in _ascii(load_entry.data, "TWRP module list").splitlines() if line]
    if len(load) != 440 or len(set(load)) != 438:
        raise AuditError("TWRP recovery module list cardinality differs")
    positions = {name: index + 1 for index, name in enumerate(load)}
    modules: dict[str, bytes] = {}
    for name, expected in RELEVANT_MODULES.items():
        entry = entries.get(f"lib/modules/{name}")
        if entry is None or entry.file_type != "regular":
            raise AuditError(f"TWRP module payload is absent: {name}")
        modules[name] = _expect(entry.data, expected, f"TWRP module {name}")
        if name not in positions:
            raise AuditError(f"TWRP module is not load-listed: {name}")
    dependencies = _parse_modules_dep(dep_entry.data)
    closure = _dependency_closure(dependencies, "dwc3-msm.ko")
    if len(closure) != 28 or not {
        "ucsi_glink.ko",
        "pmic_glink.ko",
        "usb_typec_manager.ko",
        "ssusb-redriver-nb7vpq904m.ko",
    }.issubset(closure):
        raise AuditError("TWRP DWC3 dependency closure differs")
    if (
        phase.get("schema") != "s22plus-fyg8-p319-stock-witness-runtime-v1"
        or phase.get("verdict") != "PASS_P319_STOCK_WITNESS_RUNTIME_H0"
        or phase.get("plan", {}).get("module_count") != 73
        or phase.get("plan", {}).get("eud_index") != 38
    ):
        raise AuditError("current P3.19 phase authority differs")
    current_rows = {
        row["file"]: row for row in phase.get("module_crc_closure", {}).get("modules", [])
    }
    current_plan_names = {row.get("file") for row in phase.get("plan", {}).get("rows", [])}
    current_identities: dict[str, dict[str, Any]] = {}
    identical: list[str] = []
    for name in CURRENT_COMPARISON_MODULES:
        row = current_rows.get(name)
        if row is None:
            raise AuditError(f"current P3.19 module receipt is absent: {name}")
        payload = stable_bytes(
            MODULE_DIR / name,
            f"current P3.19 module {name}",
            2 * 1024 * 1024,
            (row["size"], row["sha256"]),
        )
        current_identities[name] = identity(payload)
        if payload == modules[name]:
            identical.append(name)
    if identical or "qcom_q6v5.ko" in current_plan_names or "qcom_q6v5_pas.ko" in current_plan_names:
        raise AuditError("TWRP/current P3.19 comparison differs")
    return (
        {
            "modules_load_recovery": {**identity(load_entry.data), "line_count": 440, "unique_count": 438},
            "modules_dep": identity(dep_entry.data),
            "load_positions_one_based": {name: positions[name] for name in sorted(RELEVANT_MODULES)},
            "relevant_module_identities": {name: identity(data) for name, data in sorted(modules.items())},
            "dwc3_transitive_dependency_count": len(closure),
            "dwc3_transitive_dependencies": sorted(closure),
            "qcom_q6v5_load_listed": True,
            "qcom_q6v5_pas_load_listed": True,
            "current_p319": {
                "module_count": 73,
                "eud_index": 38,
                "comparison_module_count": len(CURRENT_COMPARISON_MODULES),
                "byte_identical_to_twrp": identical,
                "byte_different_from_twrp_count": len(CURRENT_COMPARISON_MODULES),
                "module_identities": current_identities,
                "qcom_q6v5_present": False,
                "qcom_q6v5_pas_present": False,
            },
        },
        modules,
    )


def audit_historical_live_report(payload: bytes) -> dict[str, Any]:
    text = _ascii(payload, "historical TWRP live report")
    required = (
        "Recovery ADB came up as TWRP",
        "5.10.81-afaneh92-g0418bf01a3e2",
        "local_recovery_sha=e4e1861760298da756d1d649029c33b4c953f12272ebda1705214da56245e036",
        "device_recovery_prefix_sha=e4e1861760298da756d1d649029c33b4c953f12272ebda1705214da56245e036",
    )
    if any(token not in text for token in required):
        raise AuditError("historical TWRP live report differs")
    return {
        "report": identity(payload),
        "exact_recovery_prefix_match_recorded": True,
        "recovery_adb_success_recorded": True,
        "runtime_role_producer_retained": False,
        "evidence_boundary": (
            "tracked historical report; this H0 unit did not repeat the device action "
            "and no retained role-transition log identifies the winning producer"
        ),
    }


def build_result() -> dict[str, Any]:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        raise AuditError("auditor is not bound to its source bytes")
    inputs = {
        "twrp_tar": stable_bytes(TWRP_TAR, "TWRP tar", 64 * 1024 * 1024, EXPECTED_INPUTS["twrp_tar"]),
        "historical_live_report": stable_bytes(
            HISTORICAL_LIVE_REPORT,
            "historical TWRP live report",
            64 * 1024,
            EXPECTED_INPUTS["historical_live_report"],
        ),
        "phase_result": stable_bytes(
            PHASE_RESULT, "current P3.19 phase result", 2 * 1024 * 1024, EXPECTED_INPUTS["phase_result"]
        ),
        "role_source": stable_bytes(
            ROLE_SOURCE, "current P3.19 role source", 128 * 1024, EXPECTED_INPUTS["role_source"]
        ),
    }
    helper_data = {
        name: stable_bytes(path, f"helper {name}", 2 * 1024 * 1024)
        for name, path in HELPERS.items()
    }
    recovery, tar_member = extract_recovery_image(inputs["twrp_tar"])
    header, boot_parts = parse_boot_image(recovery)
    image = _expect(
        gzip.decompress(boot_parts["kernel_gzip"]),
        EXPECTED_BOOT_PARTS["kernel_image"],
        "TWRP kernel Image",
    )
    config, kernel = extract_ikconfig(image)
    cpio, entries = cpio_map(boot_parts["ramdisk_gzip"])
    userspace = audit_userspace(entries)
    base_dtbs = split_base_dtbs(boot_parts["dtb"])
    overlays = parse_recovery_dtbo(boot_parts["recovery_dtbo"])
    phase = _json(inputs["phase_result"], "current P3.19 phase result")
    module_population, modules = audit_module_population(entries, phase)
    elf = audit_elf_modules(modules)
    role_source = _ascii(inputs["role_source"], "current P3.19 role source")
    for token in (
        '"/sys/devices/platform/soc/a600000.ssusb/mode";',
        'p260_write_value(p260_role_path, "peripheral")',
        '"/config/usb_gadget/g1/UDC",',
    ):
        if token not in role_source:
            raise AuditError("current P3.19 direct-role path differs")
    historical = audit_historical_live_report(inputs["historical_live_report"])

    for name, path in HELPERS.items():
        if stable_bytes(path, f"post-run helper {name}", 2 * 1024 * 1024) != helper_data[name]:
            raise AuditError(f"helper changed during execution: {name}")
    if stable_bytes(Path(__file__), "post-run auditor", 1024 * 1024) != _BOUND_AUDITOR_SOURCE:
        raise AuditError("auditor changed during execution")

    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "status": "IMPLEMENTED_REVIEW_PENDING",
        "target": TARGET,
        "scope": {
            "tier": "H0",
            "host_only": True,
            "device_contact": False,
            "adb_commands": 0,
            "usb_actions": 0,
            "odin_invocations": 0,
            "partition_writes": 0,
            "twrp_installation": False,
            "candidate_bytes_changed": False,
            "live_authority_created": False,
        },
        "implementation": {"auditor": identity(_BOUND_AUDITOR_SOURCE)},
        "inputs": {
            **{name: identity(data) for name, data in sorted(inputs.items())},
            "helpers": {name: identity(data) for name, data in sorted(helper_data.items())},
        },
        "twrp_archive": {"tar": identity(inputs["twrp_tar"]), "member": tar_member},
        "boot_image": {
            "recovery": identity(recovery),
            "header": header,
            "parts": {name: identity(data) for name, data in sorted(boot_parts.items())},
        },
        "kernel": {
            "image": identity(image),
            "ikconfig": identity(config),
            "required_config": kernel,
            "different_from_stock_fyg8_and_current_candidate": True,
        },
        "ramdisk": {
            "cpio": identity(cpio),
            "userspace": userspace,
        },
        "device_tree": {
            "base_dtb_count": len(base_dtbs),
            "base_dtbs": base_dtbs,
            "recovery_dtbo_entry_count": len(overlays),
            "recovery_dtbo_entries": overlays,
            "common_role_topology": {
                "dr_mode": "otg",
                "usb_role_switch": True,
                "eud_extcon": True,
                "ucsi_connector_fixup": True,
                "samsung_usb_notifier": True,
                "max77705_pdic": True,
                "explicit_role_switch_default_mode": False,
            },
        },
        "modules": module_population,
        "automatic_role_paths": {
            **elf,
            "udc_bootstrap_static_path": (
                "dwc3_msm_probe queues the OTG state machine; its undefined state "
                "calls dwc3_msm_core_init and of_platform_populate before a cable "
                "role is required, initiating DWC3 child/UDC materialization; "
                "successful runtime child or UDC registration remains unproved"
            ),
            "samsung_notifier_path": (
                "PDIC/MUIC attach notification -> usb_notifier_qcom -> "
                "qcom_set_peripheral -> dwc_msm_vbus_event -> DWC3 state machine"
            ),
            "ucsi_path_present": True,
            "ucsi_path_execution_proved": False,
            "unique_winning_role_producer_proved": False,
        },
        "historical_control": historical,
        "candidate_comparison": {
            "current_p319_plan": module_population["current_p319"],
            "current_p319_direct_mode_write": True,
            "twrp_selected_module_bytes_transferable": False,
            "twrp_kernel_or_dt_transferable": False,
            "automatic_samsung_path_structurally_shared": True,
            "automatic_ucsi_path_fully_closed_in_current_plan": False,
        },
        "conclusion": {
            "twrp_usb_success_has_a_static_explanation": True,
            "twrp_is_fixed_peripheral_kernel": False,
            "twrp_relies_on_explicit_userspace_ssusb_mode_write": False,
            "twrp_has_pre_role_udc_materialization_path": True,
            "twrp_runtime_udc_creation_proved": False,
            "twrp_contains_two_automatic_normal_role_candidates": [
                "samsung-pdic-muic-notifier",
                "pmic-glink-ucsi-role-switch",
            ],
            "historical_twrp_adb_selects_unique_candidate": False,
            "current_p319_direct_mode_path_should_be_removed": False,
            "current_p319_module_growth_justified": False,
            "next_live_discriminator_unchanged": (
                "retain current ssusb/dwc3/UDC bind gates and provider diagnostics; "
                "TWRP comparison does not replace candidate-side evidence"
            ),
        },
    }


def encode(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("ascii")


def run() -> tuple[dict[str, Any], bytes]:
    result = build_result()
    return result, encode(result)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish(payload: bytes) -> None:
    parent = OUTPUT.parent
    if parent.exists() or parent.is_symlink():
        raise AuditError("output directory already exists")
    parent.mkdir(mode=0o700, parents=True)
    parent.chmod(0o700)
    descriptor = os.open(
        OUTPUT,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o400,
    )
    try:
        os.fchmod(descriptor, 0o400)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise AuditError("short result write")
            offset += written
        os.fsync(descriptor)
        state = os.fstat(descriptor)
        if (
            not stat.S_ISREG(state.st_mode)
            or stat.S_IMODE(state.st_mode) != 0o400
            or state.st_nlink != 1
            or state.st_size != len(payload)
        ):
            raise AuditError("result metadata differs")
    finally:
        os.close(descriptor)
    _fsync_directory(parent)


def main() -> int:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        return load_bound_auditor().main()
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    _result, payload = run()
    if args.write:
        publish(payload)
    else:
        existing = stable_bytes(
            OUTPUT,
            "private TWRP role-control receipt",
            2 * 1024 * 1024,
            (len(payload), sha256(payload)),
        )
        if existing != payload:
            raise AuditError("private TWRP role-control receipt differs")
    print(f"{VERDICT} {len(payload)} {sha256(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
