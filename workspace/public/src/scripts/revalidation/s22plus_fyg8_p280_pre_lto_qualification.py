#!/usr/bin/env python3
"""Assemble and verify the exact P2.80 pre-Full-LTO gate receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import math
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p234_candidate_contract as candidate_contract  # noqa: E402
import s22plus_fyg8_p234_userspace_build as userspace  # noqa: E402
import s22plus_fyg8_p260_qemu_harness as p260_qemu  # noqa: E402
import s22plus_fyg8_p280_e2_stock_closure as p280_closure  # noqa: E402
import s22plus_fyg8_p280_kprobe_qemu_control as kprobe_qemu  # noqa: E402
import s22plus_fyg8_p280_source_contract as p280  # noqa: E402
import s22plus_fyg8_p280_trace_lifecycle_qemu as lifecycle_qemu  # noqa: E402


SCHEMA = "s22plus_fyg8_p280_pre_lto_qualification_v1"
VERDICT = "PASS_P280_PRE_FULL_LTO_QUALIFICATION_HOST_ONLY"
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p280_v5/"
    "pre-lto-qualification.json"
)
DEFAULT_USERSPACE_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p280_v5/"
    "userspace/userspace-result.json"
)
DEFAULT_P260_QEMU_RESULT = Path(
    "workspace/private/outputs/"
    "s22plus_fyg8_p280_p260_qemu_regression/result.json"
)
DEFAULT_KPROBE_RESULT = Path(
    "workspace/private/outputs/"
    "s22plus_fyg8_p280_kprobe_qemu_control/result.json"
)
DEFAULT_LIFECYCLE_RESULT = Path(
    "workspace/private/outputs/"
    "s22plus_fyg8_p280_trace_lifecycle_qemu_v5/result.json"
)
MAX_FILE_SIZE = 512 * 1024 * 1024
PINNED_QEMU_REPO_PATH = Path(
    "workspace/private/tools/qemu-arm64-10.2.1/root/"
    "usr/bin/qemu-system-aarch64"
)
QUALIFICATION_SOURCE = Path(__file__).resolve()
BUILD_WRAPPER_SOURCE = SCRIPT_DIR / "s22plus_fyg8_p234_build.py"
GATE_IMPLEMENTATION_SOURCES = {
    "qualification": QUALIFICATION_SOURCE,
    "build_wrapper": BUILD_WRAPPER_SOURCE,
    "userspace_builder": SCRIPT_DIR / "s22plus_fyg8_p234_userspace_build.py",
    "candidate_safety_builder": (
        SCRIPT_DIR / "build_s22plus_fyg8_p234_candidate.py"
    ),
    "entrypoint_closure": SCRIPT_DIR / "s22plus_fyg8_p280_e2_stock_closure.py",
    "p260_qemu_executor": SCRIPT_DIR / "s22plus_fyg8_p260_qemu_harness.py",
    "kprobe_qemu_executor": (
        SCRIPT_DIR / "s22plus_fyg8_p280_kprobe_qemu_control.py"
    ),
    "lifecycle_qemu_executor": (
        SCRIPT_DIR / "s22plus_fyg8_p280_trace_lifecycle_qemu.py"
    ),
}
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
QEMU_APPEND = "console=ttyAMA0 rdinit=/init panic=-1 loglevel=6"
P260_VALIDATED_SCOPE = [
    "generic configfs mount and statfs",
    "generic ACM gadget construction",
    "ttyGS0 materialization and raw mode",
    "pre-bind banner queue",
    "dummy_hcd UDC bind and configured state",
    "exact banner arrival through ttyACM0",
]
P260_NOT_VALIDATED_SCOPE = [
    "Qualcomm DWC3-MSM and peripheral role",
    "S22+ PHY, VBUS, Type-C, and Samsung notifier behavior",
    "physical host enumeration",
]
KPROBE_VALIDATED_SCOPE = [
    "tracefs mount and exact filesystem type",
    "isolated tracing instance and group ownership",
    "entry and return Kprobe-event registration",
    "PID1 filter and counter trace clock readback",
    "one entry and one exact signed s32 negative return value",
    "zero missed entry and return probes",
    "event, instance, and tracefs cleanup",
]
KPROBE_NOT_VALIDATED_SCOPE = [
    "S22+ Shadow Call Stack and pointer-authentication behavior",
    "S22+ DWC3-MSM target symbols and instruction sites",
    "Qualcomm USB runtime behavior",
    "physical USB enumeration",
]
LIFECYCLE_VALIDATED_SCOPE = [
    "shared P2.80 trace setup, exact readback, finish, and cleanup",
    "four-event then six-event isolated lifecycle",
    "runtime C parser malformed and nesting fixtures",
    "zero missed probes and one trace record per owned event",
    "each phase below the five-second control sanity threshold",
]
LIFECYCLE_NOT_VALIDATED_SCOPE = [
    "Qualcomm DWC3-MSM targets or USB behavior",
    "S22+ SCS/PAC behavior",
    "physical enumeration",
]
PINNED_P260_MODULES = {
    "cdc-acm": (
        "c659494fbd03a20580e584df2bb78e70224dbf86c653400f37df12cfa532d0aa",
        "7f076cf4004f355b9b9953ef8d71fada691a665a0b7229cb685e19ac4e1b027e",
    ),
    "configfs": (
        "2787f75954571bd91b82127b65460457b7aa9ab9d07edf8e29d15f6b9465de52",
        "88902c62533c9270b51b623fc9f53febd43ac91c51a64114b209a1f13360d6d8",
    ),
    "dummy_hcd": (
        "914528c45313c90a908dce135a8411f6d16862f2e7044e7b1e01577f436cfee5",
        "bf79de0ae52f0df07af88530d5c09bf8e0e3831b370e9f6b332708fed3d8b057",
    ),
    "libcomposite": (
        "a720a157e5a4afb253eb89c83081e56a123bc3d87a36bd2b4c73d9639673f8bd",
        "b84cee71a91bfec949d42d4b584595818b4e0253c4edc39c4b5d32a891822ce5",
    ),
    "u_serial": (
        "3404b2775b227860312f01d68da06c0982baad6cc525c3455c7216d311237c1c",
        "109f62dfc2d5caad6238fcd14a6a6ef01a571fa2f337242bcfd0a581dd290b25",
    ),
    "udc-core": (
        "d79a67aff601ffe772658b7aae13230c4dd22214b8dc84920e141c2ed97a1a84",
        "22ffb43967f4de912ce693c5d6653f1ec380ed5474e0099fa6d7a06b39a88790",
    ),
    "usb-common": (
        "160d74999d6f22d8ed951d6519b84f0875d55dfda0f1d754d1e94c9e345d9d28",
        "4dccd6b0e441beba62aa84aedbf40fbb67eedd01587e85637c2d4c77c1b37ce0",
    ),
    "usb_f_acm": (
        "4578e3a4cf9f45cd762c9e644d97f7d6fc926b478b5f169498cf25eecf9c3b1b",
        "3860a9021d4da6811a1c5f9a4ac08953aa59622d76bb1e4d712e26a8e3687755",
    ),
    "usbcore": (
        "8d73ad01f8646f5ec37063d97c7d1577492093b4446bd75c2e5dc5893cb2d352",
        "666df6120bb5acfe4343c432bc606cfae628011356fa69ecd6c3fb1ecf9d4016",
    ),
}


class QualificationError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _receipt_bytes(data: bytes) -> dict[str, Any]:
    return {
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _receipt_identity(row: Any, label: str) -> dict[str, Any]:
    if (
        not isinstance(row, dict)
        or type(row.get("size")) is not int
        or row["size"] <= 0
        or not isinstance(row.get("sha256"), str)
        or HEX64_RE.fullmatch(row["sha256"]) is None
    ):
        raise QualificationError(f"{label} receipt identity is invalid")
    return {"size": row["size"], "sha256": row["sha256"]}


def _repo_relative(root: Path, path: Path, label: str) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError as exc:
        raise QualificationError(f"{label} is outside the repository") from exc


def _repo_result_binding(
    root: Path, path: Path, receipt: dict[str, Any], label: str
) -> dict[str, Any]:
    return {
        "result": _receipt_identity(receipt, label),
        "result_repo_path": _repo_relative(root, path, label),
    }


def _result_path(root: Path, row: Any, label: str) -> Path:
    if not isinstance(row, dict):
        raise QualificationError(f"{label} gate row is invalid")
    relative = row.get("result_repo_path")
    if (
        not isinstance(relative, str)
        or not relative
        or Path(relative).is_absolute()
    ):
        raise QualificationError(f"{label} result path is invalid")
    path = (root / relative).resolve()
    _repo_relative(root, path, label)
    return path


def _elapsed(value: Any, label: str, maximum: float) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
        or value > maximum
    ):
        raise QualificationError(f"{label} elapsed time is invalid")
    return float(value)


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise QualificationError(f"{label} digest is invalid")
    return value


def _qemu_command_semantics(
    command: Any, build: dict[str, Any], label: str
) -> list[str]:
    if (
        not isinstance(command, list)
        or len(command) != 21
        or any(not isinstance(item, str) or not item for item in command)
    ):
        raise QualificationError(f"{label} command shape is invalid")
    binary = Path(command[0])
    if binary.name != "qemu-system-aarch64":
        raise QualificationError(f"{label} binary name is invalid")
    try:
        qemu_root = binary.parents[2]
    except IndexError as exc:
        raise QualificationError(f"{label} binary path is invalid") from exc
    expected = [
        str(binary),
        "-L",
        str(qemu_root / "usr/share/qemu"),
        "-M",
        "virt",
        "-cpu",
        "cortex-a57",
        "-smp",
        "2",
        "-m",
        "512M",
        "-nographic",
        "-no-reboot",
        "-nic",
        "none",
        "-kernel",
        build["kernel"],
        "-initrd",
        (
            build["initramfs"]["path"]
            if isinstance(build.get("initramfs"), dict)
            else build["initramfs"]
        ),
        "-append",
        QEMU_APPEND,
    ]
    if command != expected:
        raise QualificationError(f"{label} command is not exact")
    return command


def _require_command_identity(
    command: list[str], identity: dict[str, Any], label: str
) -> None:
    if command[0] != identity.get("binary"):
        raise QualificationError(
            f"{label} command and pinned binary identity differ"
        )


def _verify_current_qemu_binary(
    command: list[str], root: Path, label: str
) -> dict[str, Any]:
    reported = Path(command[0])
    suffix = PINNED_QEMU_REPO_PATH.parts
    if (
        not reported.is_absolute()
        or len(reported.parts) < len(suffix)
        or reported.parts[-len(suffix) :] != suffix
    ):
        raise QualificationError(f"{label} binary path is not pinned")
    current = _material(root / PINNED_QEMU_REPO_PATH, f"{label} binary")
    if current["sha256"] != kprobe_qemu.PINNED_QEMU_SHA256:
        raise QualificationError(f"{label} binary is not pinned")
    return {
        "repo_path": str(PINNED_QEMU_REPO_PATH),
        "sha256": current["sha256"],
        "size": current["size"],
    }


def _stable_read(path: Path, label: str, maximum: int = MAX_FILE_SIZE) -> bytes:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise QualificationError(f"{label} cannot be opened: {path}") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size <= 0
            or before.st_size > maximum
        ):
            raise QualificationError(f"{label} is not a bounded regular file")
        digest = hashlib.sha256()
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise QualificationError(f"{label} read was short")
            digest.update(chunk)
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        current = os.lstat(path)
    except OSError as exc:
        raise QualificationError(f"{label} disappeared after read") from exc
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(
        getattr(before, name) != getattr(after, name)
        or getattr(after, name) != getattr(current, name)
        for name in fields
    ):
        raise QualificationError(f"{label} changed while reading")
    data = b"".join(chunks)
    if digest.hexdigest() != hashlib.sha256(data).hexdigest():
        raise QualificationError(f"{label} streaming digest mismatch")
    return data


def _material(path: Path, label: str) -> dict[str, Any]:
    data = _stable_read(path, label)
    return {"path": str(path.resolve()), **_receipt_bytes(data)}


def _load_json(path: Path, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    data = _stable_read(path, label, 32 * 1024 * 1024)
    try:
        value = json.loads(data.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise QualificationError(f"{label} is not valid ASCII JSON") from exc
    if not isinstance(value, dict):
        raise QualificationError(f"{label} root is not an object")
    return value, {"path": str(path.resolve()), **_receipt_bytes(data)}


def _require_material(row: Any, label: str) -> dict[str, Any]:
    if not isinstance(row, dict) or set(row) != {"path", "size", "sha256"}:
        raise QualificationError(f"{label} material receipt shape mismatch")
    path = Path(row["path"])
    actual = _material(path, label)
    if actual != row:
        raise QualificationError(f"{label} material changed")
    return actual


def _expected_safety(exact_contract: dict[str, Any]) -> dict[str, Any]:
    import build_s22plus_fyg8_p234_candidate as candidate_builder

    if (
        exact_contract.get("profile") != "E2"
        or exact_contract.get("source_contract_id") != p280.CONTRACT_ID
    ):
        raise QualificationError("P2.80 safety requires the exact E2 contract")
    expected = {
        "host_only": True,
        "device_contact": False,
        "device_write": False,
        "odin_invoked": False,
        "flash": False,
        "partition_write": False,
        "live_authorized": False,
        "boot_only_ap": True,
        "ap_members": ["boot.img.lz4"],
        "no_shell": True,
        "no_block_write": True,
        "no_reboot_syscall": True,
        "userspace_sysfs_configfs_write_scope": (
            "source-contract-bound-p260-e3-acm-and-peripheral-role"
        ),
        "usb_scope": "bounded-configfs-cdc-acm-banner-and-peripheral-role",
        "module_init_probe_authority": "active-live-unproved",
        **p280.spec.RUNTIME_AUTHORITY,
    }
    actual = candidate_builder.artifact_safety(exact_contract)
    if actual != expected:
        raise QualificationError("P2.80 safety dictionary is not exact")
    return actual


def _gate_implementation() -> dict[str, Any]:
    result = {
        name: _material(path, f"P2.80 gate implementation {name}")
        for name, path in GATE_IMPLEMENTATION_SOURCES.items()
    }
    result["verified"] = True
    return result


def _verify_userspace(
    path: Path, exact_contract: dict[str, Any]
) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    value, result_receipt = _load_json(path, "P2.80 userspace result")
    if (
        set(value)
        != {
            "candidate_contract",
            "compile_flags",
            "outputs",
            "profile",
            "run_id",
            "safety",
            "schema",
            "source_contract",
            "target",
            "two_build_byte_identical",
            "verdict",
        }
        or value.get("schema") != userspace.SCHEMA
        or value.get("verdict") != p280.USERSPACE_VERDICT
        or value.get("candidate_contract") != exact_contract
        or value.get("run_id") != exact_contract["run_id"]
        or value.get("profile") != "E2"
        or value.get("two_build_byte_identical") is not True
        or value.get("source_contract", {}).get("verified") is not True
    ):
        raise QualificationError("P2.80 userspace result is not current")
    output = path.resolve().parent
    init = _stable_read(output / "init", "P2.80 userspace init", 16 * 1024 * 1024)
    child = _stable_read(
        output / "s22-e1-child", "P2.80 userspace child", 16 * 1024 * 1024
    )
    outputs = value.get("outputs")
    if (
        not isinstance(outputs, dict)
        or set(outputs) != {"init", "child"}
    ):
        raise QualificationError("P2.80 userspace output inventory mismatch")
    for name, data in (("init", init), ("child", child)):
        expected = _receipt_bytes(data)
        row = outputs.get(name)
        if not isinstance(row, dict) or any(
            row.get(key) != expected[key] for key in expected
        ):
            raise QualificationError(f"P2.80 userspace {name} receipt mismatch")
    entries = [
        SimpleNamespace(name="init", data=init),
        SimpleNamespace(name="s22-e1-child", data=child),
    ]
    entrypoints = p280_closure._entrypoints(entries)
    return {
        **_repo_result_binding(
            root, path, result_receipt, "P2.80 userspace result"
        ),
        "semantics": {
            "init": {
                "repo_path": _repo_relative(
                    root, output / "init", "P2.80 userspace init"
                ),
                **_receipt_bytes(init),
            },
            "child": {
                "repo_path": _repo_relative(
                    root,
                    output / "s22-e1-child",
                    "P2.80 userspace child",
                ),
                **_receipt_bytes(child),
            },
            "entrypoints": entrypoints,
        },
        "verified": True,
    }


def _verify_p260_qemu(
    path: Path, *, verify_materials: bool = True
) -> dict[str, Any]:
    value, result_receipt = _load_json(path, "P2.60 generic QEMU result")
    build = value.get("build")
    scope = value.get("scope")
    if (
        set(value)
        != {
            "build",
            "command",
            "elapsed_sec",
            "qemu_output_sha256",
            "schema",
            "scope",
            "verdict",
        }
        or value.get("schema")
        != "s22plus_fyg8_p260_generic_qemu_harness_v1"
        or value.get("verdict") != p260_qemu.VERDICT
        or not isinstance(build, dict)
        or set(build)
        != {
            "compile_output",
            "harness_sha256",
            "init",
            "init_file",
            "init_sha256",
            "initramfs",
            "initramfs_sha256",
            "kernel",
            "kernel_sha256",
            "modules",
            "runtime_sha256",
        }
        or build.get("kernel_sha256") != kprobe_qemu.PINNED_KERNEL_SHA256
        or set(build.get("modules", {})) != set(PINNED_P260_MODULES)
        or set(PINNED_P260_MODULES) != set(p260_qemu.MODULES)
        or not isinstance(scope, dict)
        or scope
        != {
            "validated": P260_VALIDATED_SCOPE,
            "intended_validation": P260_VALIDATED_SCOPE,
            "not_validated": P260_NOT_VALIDATED_SCOPE,
        }
    ):
        raise QualificationError("P2.60 generic QEMU result is not accepted")

    root = candidate_contract.intent.repo_root()
    runtime = _material(root / p260_qemu.RUNTIME_RELATIVE, "P2.60 QEMU runtime")
    harness = _material(root / p260_qemu.HARNESS_RELATIVE, "P2.60 QEMU harness")
    if (
        build.get("runtime_sha256") != runtime["sha256"]
        or build.get("harness_sha256") != harness["sha256"]
    ):
        raise QualificationError("P2.60 QEMU source binding changed")

    module_pins = {}
    for name in p260_qemu.MODULES:
        row = build["modules"].get(name)
        if (
            not isinstance(row, dict)
            or set(row)
            != {"source", "source_sha256", "decompressed_sha256"}
        ):
            raise QualificationError(f"P2.60 QEMU module missing: {name}")
        source_sha256, decompressed_sha256 = PINNED_P260_MODULES[name]
        if (
            row.get("source_sha256") != source_sha256
            or row.get("decompressed_sha256") != decompressed_sha256
        ):
            raise QualificationError(f"P2.60 QEMU module pin drifted: {name}")
        module_pins[name] = {
            "source_sha256": source_sha256,
            "decompressed_sha256": decompressed_sha256,
        }
    command = _qemu_command_semantics(
        value.get("command"), build, "P2.60 QEMU"
    )
    qemu_binary = _verify_current_qemu_binary(
        command, root, "P2.60 QEMU"
    )
    semantics = {
        "elapsed_sec": _elapsed(
            value.get("elapsed_sec"), "P2.60 QEMU", 620.0
        ),
        "qemu_output_sha256": _digest(
            value.get("qemu_output_sha256"), "P2.60 QEMU output"
        ),
        "command": command,
        "qemu_binary": qemu_binary,
        "kernel_sha256": build["kernel_sha256"],
        "runtime_sha256": runtime["sha256"],
        "harness_sha256": harness["sha256"],
        "init_sha256": _digest(
            build.get("init_sha256"), "P2.60 QEMU init"
        ),
        "initramfs_sha256": _digest(
            build.get("initramfs_sha256"), "P2.60 QEMU initramfs"
        ),
        "module_pins": module_pins,
        "scope": scope,
    }
    result = {
        **_repo_result_binding(
            root, path, result_receipt, "P2.60 generic QEMU result"
        ),
        "semantics": semantics,
        "verified": True,
    }
    if not verify_materials:
        return result
    materials = [runtime, harness]
    kernel = _material(Path(build["kernel"]), "P2.60 QEMU kernel")
    if kernel["sha256"] != kprobe_qemu.PINNED_KERNEL_SHA256:
        raise QualificationError("P2.60 QEMU kernel is not pinned")
    materials.append(kernel)
    for name in p260_qemu.MODULES:
        row = build["modules"][name]
        source = _material(Path(row["source"]), f"P2.60 QEMU module {name}")
        if source["sha256"] != row["source_sha256"]:
            raise QualificationError(f"P2.60 QEMU module source drifted: {name}")
        try:
            decompressed = lzma.decompress(
                _stable_read(Path(row["source"]), name)
            )
        except lzma.LZMAError as exc:
            raise QualificationError(
                f"P2.60 QEMU module cannot be decompressed: {name}"
            ) from exc
        if (
            hashlib.sha256(decompressed).hexdigest()
            != row["decompressed_sha256"]
        ):
            raise QualificationError(f"P2.60 QEMU module bytes drifted: {name}")
        materials.append(source)
    for key in ("init", "initramfs"):
        material = _material(Path(build[key]), f"P2.60 QEMU {key}")
        if material["sha256"] != build[f"{key}_sha256"]:
            raise QualificationError(f"P2.60 QEMU {key} drifted")
        materials.append(material)
    return result


def _verify_kprobe_qemu(
    path: Path, *, verify_materials: bool = True
) -> dict[str, Any]:
    value, result_receipt = _load_json(path, "P2.80 Kprobe QEMU result")
    build = value.get("build")
    identity = value.get("qemu_identity")
    scope = value.get("scope")
    if (
        set(value)
        != {
            "build",
            "command",
            "elapsed_sec",
            "qemu_identity",
            "qemu_output_sha256",
            "schema",
            "scope",
            "verdict",
        }
        or value.get("schema")
        != "s22plus_fyg8_p280_kprobe_qemu_control_v1"
        or value.get("verdict") != kprobe_qemu.VERDICT
        or not isinstance(build, dict)
        or set(build)
        != {
            "compile_output",
            "guest_config",
            "guest_config_sha256",
            "init",
            "init_file",
            "init_sha256",
            "initramfs",
            "initramfs_sha256",
            "kernel",
            "kernel_sha256",
            "source",
            "source_sha256",
        }
        or not isinstance(identity, dict)
        or set(identity) != {"binary", "binary_sha256", "version"}
        or build.get("kernel_sha256") != kprobe_qemu.PINNED_KERNEL_SHA256
        or build.get("guest_config_sha256")
        != kprobe_qemu.PINNED_CONFIG_SHA256
        or identity.get("binary_sha256") != kprobe_qemu.PINNED_QEMU_SHA256
        or identity.get("version") != kprobe_qemu.PINNED_QEMU_VERSION
        or scope
        != {
            "validated": KPROBE_VALIDATED_SCOPE,
            "not_validated": KPROBE_NOT_VALIDATED_SCOPE,
        }
    ):
        raise QualificationError("P2.80 Kprobe QEMU result is not accepted")
    root = candidate_contract.intent.repo_root()
    source = _material(
        root / kprobe_qemu.SOURCE_RELATIVE, "P2.80 Kprobe QEMU source"
    )
    if source["sha256"] != build.get("source_sha256"):
        raise QualificationError("P2.80 Kprobe QEMU source drifted")
    command = _qemu_command_semantics(
        value.get("command"), build, "P2.80 Kprobe QEMU"
    )
    _require_command_identity(command, identity, "P2.80 Kprobe QEMU")
    qemu_binary = _verify_current_qemu_binary(
        command, root, "P2.80 Kprobe QEMU"
    )
    semantics = {
        "elapsed_sec": _elapsed(
            value.get("elapsed_sec"), "P2.80 Kprobe QEMU", 80.0
        ),
        "qemu_output_sha256": _digest(
            value.get("qemu_output_sha256"), "P2.80 Kprobe QEMU output"
        ),
        "command": command,
        "qemu_identity": identity,
        "qemu_binary": qemu_binary,
        "kernel_sha256": build["kernel_sha256"],
        "guest_config_sha256": build["guest_config_sha256"],
        "source_sha256": source["sha256"],
        "init_sha256": _digest(
            build.get("init_sha256"), "P2.80 Kprobe QEMU init"
        ),
        "initramfs_sha256": _digest(
            build.get("initramfs_sha256"), "P2.80 Kprobe QEMU initramfs"
        ),
        "scope": scope,
    }
    result = {
        **_repo_result_binding(
            root, path, result_receipt, "P2.80 Kprobe QEMU result"
        ),
        "semantics": semantics,
        "verified": True,
    }
    if not verify_materials:
        return result
    materials = [source]
    path_fields = (
        ("kernel", "kernel_sha256"),
        ("guest_config", "guest_config_sha256"),
        ("init", "init_sha256"),
        ("initramfs", "initramfs_sha256"),
    )
    for path_key, sha_key in path_fields:
        material = _material(
            Path(build[path_key]), f"P2.80 Kprobe QEMU {path_key}"
        )
        if material["sha256"] != build[sha_key]:
            raise QualificationError(
                f"P2.80 Kprobe QEMU {path_key} drifted"
            )
        materials.append(material)
    return result


def _verify_lifecycle_qemu(
    path: Path, *, verify_materials: bool = True
) -> dict[str, Any]:
    value, result_receipt = _load_json(path, "P2.80 lifecycle QEMU result")
    identity = value.get("qemu_identity")
    build = value.get("build")
    scope = value.get("scope")
    _source_data, current_sources = p280.source_receipts(
        candidate_contract.intent.repo_root()
    )
    samples = value.get("samples")
    if (
        set(value)
        != {
            "build",
            "cold_sample_count",
            "command",
            "qemu_identity",
            "samples",
            "schema",
            "scope",
            "source_contract_id",
            "source_receipts",
            "verdict",
        }
        or value.get("schema") != lifecycle_qemu.SCHEMA
        or value.get("verdict") != lifecycle_qemu.VERDICT
        or value.get("source_contract_id") != p280.CONTRACT_ID
        or value.get("source_receipts") != current_sources
        or value.get("cold_sample_count") not in range(5, 11)
        or not isinstance(samples, list)
        or len(samples) != value["cold_sample_count"]
        or any(sample.get("verified") is not True for sample in samples)
        or not isinstance(identity, dict)
        or set(identity) != {"binary", "binary_sha256", "version"}
        or identity.get("binary_sha256") != kprobe_qemu.PINNED_QEMU_SHA256
        or identity.get("version") != kprobe_qemu.PINNED_QEMU_VERSION
        or not isinstance(build, dict)
        or set(build)
        != {
            "checkpoint",
            "compile_output",
            "guest_config",
            "guest_config_sha256",
            "harness",
            "init",
            "init_file",
            "initramfs",
            "kernel",
            "kernel_sha256",
            "runtime",
        }
        or build.get("kernel_sha256") != kprobe_qemu.PINNED_KERNEL_SHA256
        or build.get("guest_config_sha256")
        != kprobe_qemu.PINNED_CONFIG_SHA256
        or scope
        != {
            "validated": LIFECYCLE_VALIDATED_SCOPE,
            "not_validated": LIFECYCLE_NOT_VALIDATED_SCOPE,
        }
    ):
        raise QualificationError("P2.80 lifecycle QEMU result is not current")
    material_receipts = {
        key: _receipt_identity(
            build.get(key), f"P2.80 lifecycle {key}"
        )
        for key in ("runtime", "checkpoint", "harness", "init", "initramfs")
    }
    normalized_samples = []
    for index, sample in enumerate(samples):
        if (
            not isinstance(sample, dict)
            or set(sample)
            != {
                "elapsed_sec",
                "role_ns",
                "bind_ns",
                "console_sha256",
                "verified",
            }
            or type(sample.get("role_ns")) is not int
            or type(sample.get("bind_ns")) is not int
            or sample["role_ns"] <= 0
            or sample["bind_ns"] <= 0
            or sample["role_ns"] >= lifecycle_qemu.SANITY_NS
            or sample["bind_ns"] >= lifecycle_qemu.SANITY_NS
        ):
            raise QualificationError(
                f"P2.80 lifecycle sample {index} is invalid"
            )
        elapsed = _elapsed(
            sample["elapsed_sec"], f"P2.80 lifecycle sample {index}", 80.0
        )
        if max(sample["role_ns"], sample["bind_ns"]) >= elapsed * 1e9:
            raise QualificationError(
                f"P2.80 lifecycle sample {index} timing is impossible"
            )
        normalized_samples.append(
            {
                "elapsed_sec": elapsed,
                "role_ns": sample["role_ns"],
                "bind_ns": sample["bind_ns"],
                "console_sha256": _digest(
                    sample["console_sha256"],
                    f"P2.80 lifecycle sample {index} console",
                ),
                "verified": True,
            }
        )
    command = _qemu_command_semantics(
        value.get("command"), build, "P2.80 lifecycle QEMU"
    )
    _require_command_identity(command, identity, "P2.80 lifecycle QEMU")
    root = candidate_contract.intent.repo_root()
    qemu_binary = _verify_current_qemu_binary(
        command, root, "P2.80 lifecycle QEMU"
    )
    semantics = {
        "command": command,
        "qemu_identity": identity,
        "qemu_binary": qemu_binary,
        "kernel_sha256": build["kernel_sha256"],
        "guest_config_sha256": build["guest_config_sha256"],
        "material_receipts": material_receipts,
        "source_receipts": current_sources,
        "cold_sample_count": value["cold_sample_count"],
        "samples": normalized_samples,
        "scope": scope,
    }
    result = {
        **_repo_result_binding(
            root, path, result_receipt, "P2.80 lifecycle QEMU result"
        ),
        "semantics": semantics,
        "verified": True,
    }
    if not verify_materials:
        return result
    materials = [
        _require_material(build[key], f"P2.80 lifecycle {key}")
        for key in ("runtime", "checkpoint", "harness", "init", "initramfs")
    ]
    for path_key, sha_key in (
        ("kernel", "kernel_sha256"),
        ("guest_config", "guest_config_sha256"),
    ):
        material = _material(
            Path(build[path_key]), f"P2.80 lifecycle {path_key}"
        )
        if material["sha256"] != build[sha_key]:
            raise QualificationError(f"P2.80 lifecycle {path_key} drifted")
        materials.append(material)
    return result


def _candidate_binding(
    exact_contract: dict[str, Any], intent_path: Path, patch_path: Path
) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    intent = _material(intent_path, "P2.80 candidate intent")
    patch = _material(patch_path, "P2.80 candidate patch")
    if patch["sha256"] != exact_contract.get("patch", {}).get("sha256"):
        raise QualificationError("P2.80 patch receipt is not current")
    return {
        "run_id": exact_contract["run_id"],
        "profile": exact_contract["profile"],
        "source_contract_id": exact_contract["source_contract_id"],
        "candidate_contract_sha256": hashlib.sha256(
            _canonical(exact_contract)
        ).hexdigest(),
        "intent": intent,
        "intent_repo_path": _repo_relative(
            root, intent_path, "P2.80 candidate intent"
        ),
        "patch": patch,
        "patch_repo_path": _repo_relative(
            root, patch_path, "P2.80 candidate patch"
        ),
    }


def _same_gate(
    stored: Any, current: dict[str, Any], label: str
) -> None:
    if (
        not isinstance(stored, dict)
        or set(stored)
        != {"result", "result_repo_path", "semantics", "verified"}
    ):
        raise QualificationError(f"{label} stored gate is invalid")
    if (
        stored.get("verified") is not True
        or stored.get("result_repo_path") != current["result_repo_path"]
        or _receipt_identity(stored.get("result"), f"{label} stored result")
        != current["result"]
        or stored.get("semantics") != current["semantics"]
    ):
        raise QualificationError(f"{label} gate receipt or semantics changed")


def create(
    *,
    source: Path,
    intent_path: Path,
    patch_path: Path,
    userspace_result: Path,
    p260_qemu_result: Path,
    kprobe_result: Path,
    lifecycle_result: Path,
) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    exact_contract = candidate_contract.verify(
        root, source, intent_path, patch_path
    )
    if exact_contract.get("source_contract_id") != p280.CONTRACT_ID:
        raise QualificationError("qualification is only valid for P2.80")
    implementation = p280.implementation_result(root)
    if implementation.get("verdict") != p280.IMPLEMENTATION_VERDICT:
        raise QualificationError("P2.80 implementation gate did not pass")
    _source_data, source_receipts = p280.source_receipts(root)
    gates = {
        "userspace": _verify_userspace(userspace_result, exact_contract),
        "safety": {
            "dictionary": _expected_safety(exact_contract),
            "verified": True,
        },
        "p260_generic_qemu": _verify_p260_qemu(p260_qemu_result),
        "kprobe_control_qemu": _verify_kprobe_qemu(kprobe_result),
        "trace_lifecycle_qemu": _verify_lifecycle_qemu(lifecycle_result),
    }
    if any(row.get("verified") is not True for row in gates.values()):
        raise QualificationError("P2.80 pre-LTO gate did not verify")
    payload = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "build_allowed": True,
        "candidate": _candidate_binding(
            exact_contract, intent_path, patch_path
        ),
        "implementation": {
            "schema": implementation["schema"],
            "verdict": implementation["verdict"],
            "generated": implementation["generated"],
            "source_receipts": source_receipts,
            "verified": True,
        },
        "gate_implementation": _gate_implementation(),
        "gates": gates,
        "safety": {
            "host_only": True,
            "kernel_built": False,
            "full_lto_started": False,
            "candidate_created": False,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        },
    }
    return {
        **payload,
        "payload_sha256": hashlib.sha256(_canonical(payload)).hexdigest(),
    }


def verify_receipt(
    path: Path,
    exact_contract: dict[str, Any],
    *,
    intent_path: Path,
    patch_path: Path,
) -> dict[str, Any]:
    value, qualification_receipt = _load_json(
        path, "P2.80 pre-LTO qualification"
    )
    if set(value) != {
        "build_allowed",
        "candidate",
        "gate_implementation",
        "gates",
        "implementation",
        "payload_sha256",
        "safety",
        "schema",
        "verdict",
    }:
        raise QualificationError("P2.80 qualification schema is not exact")
    payload = dict(value)
    payload_sha256 = payload.pop("payload_sha256", None)
    if (
        not isinstance(payload_sha256, str)
        or payload_sha256 != hashlib.sha256(_canonical(payload)).hexdigest()
    ):
        raise QualificationError("P2.80 qualification payload digest mismatch")
    candidate = value.get("candidate")
    implementation = value.get("implementation")
    gate_implementation = value.get("gate_implementation")
    gates = value.get("gates")
    safety = value.get("safety")
    if (
        value.get("schema") != SCHEMA
        or value.get("verdict") != VERDICT
        or value.get("build_allowed") is not True
        or not isinstance(candidate, dict)
        or candidate.get("run_id") != exact_contract.get("run_id")
        or candidate.get("profile") != exact_contract.get("profile")
        or candidate.get("source_contract_id")
        != exact_contract.get("source_contract_id")
        or candidate.get("candidate_contract_sha256")
        != hashlib.sha256(_canonical(exact_contract)).hexdigest()
        or not isinstance(implementation, dict)
        or not isinstance(gate_implementation, dict)
        or not isinstance(gates, dict)
        or set(gates)
        != {
            "userspace",
            "safety",
            "p260_generic_qemu",
            "kprobe_control_qemu",
            "trace_lifecycle_qemu",
        }
        or not isinstance(candidate, dict)
        or set(candidate)
        != {
            "candidate_contract_sha256",
            "intent",
            "intent_repo_path",
            "patch",
            "patch_repo_path",
            "profile",
            "run_id",
            "source_contract_id",
        }
        or not isinstance(implementation, dict)
        or set(implementation)
        != {
            "generated",
            "schema",
            "source_receipts",
            "verdict",
            "verified",
        }
        or not isinstance(safety, dict)
        or safety
        != {
            "host_only": True,
            "kernel_built": False,
            "full_lto_started": False,
            "candidate_created": False,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        }
    ):
        raise QualificationError("P2.80 qualification identity mismatch")
    intent = _receipt_identity(
        candidate.get("intent"), "P2.80 qualification intent"
    )
    patch = _receipt_identity(
        candidate.get("patch"), "P2.80 qualification patch"
    )
    root = candidate_contract.intent.repo_root()
    selected_intent = _material(intent_path, "P2.80 selected build intent")
    selected_patch = _material(patch_path, "P2.80 selected build patch")
    if (
        intent != _receipt_identity(selected_intent, "selected intent")
        or patch != _receipt_identity(selected_patch, "selected patch")
        or candidate.get("intent_repo_path")
        != _repo_relative(root, intent_path, "P2.80 selected build intent")
        or candidate.get("patch_repo_path")
        != _repo_relative(root, patch_path, "P2.80 selected build patch")
    ):
        raise QualificationError(
            "P2.80 qualification is bound to different build inputs"
        )
    if patch["sha256"] != exact_contract.get("patch", {}).get("sha256"):
        raise QualificationError("P2.80 qualification patch is stale")
    current_implementation = p280.implementation_result(root)
    _source_data, source_receipts = p280.source_receipts(root)
    if (
        implementation.get("verdict") != p280.IMPLEMENTATION_VERDICT
        or implementation.get("schema")
        != current_implementation.get("schema")
        or implementation.get("generated")
        != current_implementation.get("generated")
        or implementation.get("source_receipts") != source_receipts
        or implementation.get("verified") is not True
    ):
        raise QualificationError("P2.80 qualification source binding is stale")
    current_gate_implementation = _gate_implementation()
    if (
        not isinstance(gate_implementation, dict)
        or gate_implementation.get("verified") is not True
        or set(gate_implementation)
        != set(GATE_IMPLEMENTATION_SOURCES) | {"verified"}
        or any(
            _receipt_identity(
                gate_implementation.get(name),
                f"P2.80 qualification {name}",
            )
            != _receipt_identity(
                current_gate_implementation[name],
                f"P2.80 current {name}",
            )
            for name in GATE_IMPLEMENTATION_SOURCES
        )
    ):
        raise QualificationError(
            "P2.80 qualification implementation binding is stale"
        )
    if (
        not isinstance(gates["safety"], dict)
        or set(gates["safety"]) != {"dictionary", "verified"}
        or gates["safety"].get("verified") is not True
        or gates["safety"].get("dictionary")
        != _expected_safety(exact_contract)
    ):
        raise QualificationError("P2.80 qualification safety is stale")
    userspace_gate = _verify_userspace(
        _result_path(root, gates["userspace"], "P2.80 userspace"),
        exact_contract,
    )
    p260_gate = _verify_p260_qemu(
        _result_path(
            root, gates["p260_generic_qemu"], "P2.60 generic QEMU"
        ),
        verify_materials=False,
    )
    kprobe_gate = _verify_kprobe_qemu(
        _result_path(
            root, gates["kprobe_control_qemu"], "P2.80 Kprobe QEMU"
        ),
        verify_materials=False,
    )
    lifecycle_gate = _verify_lifecycle_qemu(
        _result_path(
            root, gates["trace_lifecycle_qemu"], "P2.80 lifecycle QEMU"
        ),
        verify_materials=False,
    )
    for name, current in (
        ("userspace", userspace_gate),
        ("p260_generic_qemu", p260_gate),
        ("kprobe_control_qemu", kprobe_gate),
        ("trace_lifecycle_qemu", lifecycle_gate),
    ):
        _same_gate(gates[name], current, f"P2.80 {name}")
    if set(PINNED_P260_MODULES) != set(p260_qemu.MODULES):
        raise QualificationError("P2.80 qualification module pins are stale")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "build_allowed": True,
        "run_id": exact_contract["run_id"],
        "source_contract_id": p280.CONTRACT_ID,
        "qualification": qualification_receipt,
        "qualification_repo_path": _repo_relative(
            root, path, "P2.80 pre-LTO qualification"
        ),
        "intent_repo_path": candidate["intent_repo_path"],
        "patch_repo_path": candidate["patch_repo_path"],
        "gate_result_receipts": {
            name: row["result"]
            for name, row in gates.items()
            if name != "safety"
        },
        "verified": True,
    }


def _resolve(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def _write_exclusive(path: Path, value: dict[str, Any]) -> None:
    data = json.dumps(
        value, indent=2, sort_keys=True, allow_nan=False
    ).encode("ascii") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o400)
    try:
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                raise QualificationError("qualification receipt write was short")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=candidate_contract.DEFAULT_SOURCE)
    parser.add_argument("--intent", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument(
        "--userspace-result", type=Path, default=DEFAULT_USERSPACE_RESULT
    )
    parser.add_argument(
        "--p260-qemu-result", type=Path, default=DEFAULT_P260_QEMU_RESULT
    )
    parser.add_argument(
        "--kprobe-result", type=Path, default=DEFAULT_KPROBE_RESULT
    )
    parser.add_argument(
        "--lifecycle-result", type=Path, default=DEFAULT_LIFECYCLE_RESULT
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = candidate_contract.intent.repo_root()
    try:
        result = create(
            source=_resolve(root, args.source),
            intent_path=_resolve(root, args.intent),
            patch_path=_resolve(root, args.patch),
            userspace_result=_resolve(root, args.userspace_result),
            p260_qemu_result=_resolve(root, args.p260_qemu_result),
            kprobe_result=_resolve(root, args.kprobe_result),
            lifecycle_result=_resolve(root, args.lifecycle_result),
        )
        out = _resolve(root, args.out)
        _write_exclusive(out, result)
    except (
        QualificationError,
        candidate_contract.ContractError,
        candidate_contract.intent.IntentError,
        p280.SourceContractError,
        p280_closure.ClosureError,
        OSError,
        subprocess.TimeoutExpired,
    ) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}
            )
        )
        return 1
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "verdict": VERDICT,
                "run_id": result["candidate"]["run_id"],
                "out": str(out),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
