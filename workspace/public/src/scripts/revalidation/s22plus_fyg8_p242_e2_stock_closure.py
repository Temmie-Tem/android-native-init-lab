#!/usr/bin/env python3
"""Shared exact stock-rootfs contract for the FYG8 E2 candidate pipeline."""

from __future__ import annotations

import hashlib
import json
import stat
from pathlib import Path
from typing import Any

import s22plus_boot_verify as boot_verify
import s22plus_fyg8_p241_e2_static_checker as p241
import s22plus_fyg8_r4w1e_e1_candidate_static_checker as e1_static
import s22plus_o2_module_plan as planner


SCHEMA = "s22plus_fyg8_p242_e2_stock_module_closure_v1"
ORDER_MODEL = "P2.41 exact E2 order from pinned FYG8 module metadata"
EXPECTED_MODULE_CLOSURE_SHA256 = (
    "a15eff75e913eb26de1932fee410cc26fd4369ada29b2ece5a534a82951ac6cc"
)
EXPECTED_ELF_ENTRYPOINTS = {"init": 4_198_636, "child": 4_194_508}
EXPECTED_GENERIC_ENTRY_COUNT = 22
DEFAULT_VENDOR_RAMDISK = p241.DEFAULT_VENDOR_RAMDISK
DEFAULT_VENDOR_BOOT = e1_static.DEFAULT_VENDOR_BOOT
DEFAULT_LZ4 = p241.DEFAULT_LZ4


class ClosureError(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def closure_sha256(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def derive_module_closure(
    root: Path,
    vendor_ramdisk: Path,
    lz4: Path,
    plan_header: Path | None = None,
) -> dict[str, Any]:
    header_path = plan_header or root / p241.DEFAULT_PLAN_HEADER
    header = p241.stable_read(header_path, "P2.42 E2 plan header", 1024 * 1024)
    _metadata, plan, plan_audit = p241.audit_plan(
        root / planner.DEFAULT_METADATA_DIR, header
    )
    module_audit = p241.audit_vendor_modules(root, vendor_ramdisk, lz4, plan)
    result = {
        "schema": SCHEMA,
        "files": [row["file"] for row in module_audit["modules"]],
        "runtime_names": [
            row["runtime_name"] for row in module_audit["modules"]
        ],
        "count": module_audit["module_count"],
        "modules": module_audit["modules"],
        "order_model": ORDER_MODEL,
        "constraint_count": plan_audit["constraint_count"],
        "plan_tsv_sha256": plan_audit["tsv_sha256"],
        "plan_header": plan_audit["header"],
        "foundation": plan_audit["foundation"],
        "vendor_ramdisk": module_audit["vendor_ramdisk"],
        "vendor_entry_count": module_audit["entry_count"],
        "request_firmware_string_hits": module_audit[
            "request_firmware_string_hits"
        ],
        "sec_log_buf_absent": module_audit["sec_log_buf_absent"],
        "verified": True,
    }
    validate_module_closure(result, allow_unpinned=not EXPECTED_MODULE_CLOSURE_SHA256)
    return result


def _identity(value: Any, label: str) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != {"size", "sha256"}
        or isinstance(value.get("size"), bool)
        or not isinstance(value.get("size"), int)
        or value["size"] <= 0
        or not isinstance(value.get("sha256"), str)
        or len(value["sha256"]) != 64
    ):
        raise ClosureError(f"{label} identity is malformed")
    try:
        bytes.fromhex(value["sha256"])
    except ValueError as exc:
        raise ClosureError(f"{label} digest is not hexadecimal") from exc
    return value


def validate_module_closure(
    value: Any, *, allow_unpinned: bool = False
) -> dict[str, Any]:
    expected_keys = {
        "schema",
        "files",
        "runtime_names",
        "count",
        "modules",
        "order_model",
        "constraint_count",
        "plan_tsv_sha256",
        "plan_header",
        "foundation",
        "vendor_ramdisk",
        "vendor_entry_count",
        "request_firmware_string_hits",
        "sec_log_buf_absent",
        "verified",
    }
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise ClosureError("E2 stock module closure shape mismatch")
    rows = value.get("modules")
    if not isinstance(rows, list) or len(rows) != 59:
        raise ClosureError("E2 stock module row count mismatch")
    normalized = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {
            "index",
            "file",
            "runtime_name",
            "size",
            "sha256",
        }:
            raise ClosureError(f"E2 stock module row shape mismatch: {index}")
        if (
            type(row["index"]) is not int
            or row["index"] != index
            or not isinstance(row["file"], str)
            or not row["file"].endswith(".ko")
            or not isinstance(row["runtime_name"], str)
            or row["runtime_name"] != planner.normalize_module_name(row["file"])
        ):
            raise ClosureError(f"E2 stock module row identity mismatch: {index}")
        _identity({"size": row["size"], "sha256": row["sha256"]}, "E2 module")
        normalized.append(row)
    files = [row["file"] for row in normalized]
    runtime_names = [row["runtime_name"] for row in normalized]
    if (
        value.get("schema") != SCHEMA
        or value.get("files") != files
        or value.get("runtime_names") != runtime_names
        or type(value.get("count")) is not int
        or value["count"] != 59
        or len(set(files)) != 59
        or len(set(runtime_names)) != 59
        or value.get("order_model") != ORDER_MODEL
        or type(value.get("constraint_count")) is not int
        or value["constraint_count"] != 210
        or value.get("plan_tsv_sha256")
        != planner.EXPECTED_E2_PROFILE_PLAN_TSV_SHA256
        or value.get("foundation") != list(planner.E2_PROVEN_E1B_FOUNDATION)
        or type(value.get("vendor_entry_count")) is not int
        or value["vendor_entry_count"] != p241.EXPECTED_VENDOR_ENTRY_COUNT
        or type(value.get("request_firmware_string_hits")) is not int
        or value["request_firmware_string_hits"] != 0
        or value.get("sec_log_buf_absent") is not True
        or value.get("verified") is not True
    ):
        raise ClosureError("E2 stock module closure invariant mismatch")
    _identity(value.get("plan_header"), "E2 plan header")
    _identity(value.get("vendor_ramdisk"), "E2 vendor ramdisk")
    digest = closure_sha256(value)
    if not allow_unpinned and digest != EXPECTED_MODULE_CLOSURE_SHA256:
        raise ClosureError(f"E2 stock module closure digest mismatch: {digest}")
    return value


def _validate_elf(value: Any, label: str) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "machine",
            "entrypoint",
            "interpreter",
            "dynamic",
            "executable_stack",
            "entrypoint_mapped",
            "verified",
        }
        or value.get("machine") != "AArch64"
        or type(value.get("entrypoint")) is not int
        or value["entrypoint"] != EXPECTED_ELF_ENTRYPOINTS[label]
        or value.get("interpreter") is not False
        or value.get("dynamic") is not False
        or value.get("executable_stack") is not False
        or value.get("entrypoint_mapped") is not True
        or value.get("verified") is not True
    ):
        raise ClosureError(f"effective E2 {label} ELF mismatch")
    return value


def _validate_generic_rootfs(
    value: Any,
    *,
    expected_init: dict[str, Any],
    expected_child: dict[str, Any],
    init_elf: dict[str, Any],
    child_elf: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "entry_count",
        "no_duplicate_or_alias",
        "init",
        "child",
        "rdinit_override_absent",
        "verified",
    }:
        raise ClosureError("generic E2 rootfs shape mismatch")
    init = value.get("init")
    child = value.get("child")
    if not isinstance(init, dict) or set(init) != {
        "size",
        "sha256",
        "uid",
        "gid",
        "mode",
        "nlink",
        "elf",
        "run_id_count",
        "required_strings_complete",
        "forbidden_authority_absent",
    }:
        raise ClosureError("generic E2 init shape mismatch")
    if not isinstance(child, dict) or set(child) != {
        "size",
        "sha256",
        "uid",
        "gid",
        "mode",
        "nlink",
        "elf",
        "token_count",
    }:
        raise ClosureError("generic E2 child shape mismatch")
    init_identity = _identity(
        {name: init.get(name) for name in ("size", "sha256")},
        "generic E2 init",
    )
    child_identity = _identity(
        {name: child.get(name) for name in ("size", "sha256")},
        "generic E2 child",
    )
    integer_fields = (
        ("init uid", init.get("uid"), 0),
        ("init gid", init.get("gid"), 0),
        ("init mode", init.get("mode"), 0o750),
        ("init nlink", init.get("nlink"), 1),
        ("init run ID count", init.get("run_id_count"), 1),
        ("child uid", child.get("uid"), 0),
        ("child gid", child.get("gid"), 0),
        ("child mode", child.get("mode"), 0o750),
        ("child nlink", child.get("nlink"), 1),
        ("child token count", child.get("token_count"), 1),
    )
    if any(type(actual) is not int or actual != expected for _name, actual, expected in integer_fields):
        raise ClosureError("generic E2 executable numeric field mismatch")
    if (
        type(value.get("entry_count")) is not int
        or value["entry_count"] != EXPECTED_GENERIC_ENTRY_COUNT
        or value.get("no_duplicate_or_alias") is not True
        or init_identity != expected_init
        or child_identity != expected_child
        or canonical(_validate_elf(init.get("elf"), "init")) != canonical(init_elf)
        or canonical(_validate_elf(child.get("elf"), "child")) != canonical(child_elf)
        or init.get("required_strings_complete") is not True
        or init.get("forbidden_authority_absent") is not True
        or value.get("rdinit_override_absent") is not True
        or value.get("verified") is not True
    ):
        raise ClosureError("generic E2 rootfs invariant mismatch")
    return value


def _exact_executable(
    seen: dict[str, tuple[str, boot_verify.CpioEntry]],
    name: str,
    expected: dict[str, Any],
) -> boot_verify.CpioEntry:
    value = seen.get(name)
    if value is None:
        raise ClosureError(f"effective E2 rootfs missing {name}")
    label, entry = value
    actual = receipt(entry.data)
    if (
        label != "generic"
        or entry.file_type != "regular"
        or entry.uid != 0
        or entry.gid != 0
        or entry.nlink != 1
        or stat.S_IMODE(entry.mode) != 0o750
        or actual != expected
    ):
        raise ClosureError(f"effective E2 {name} identity mismatch")
    return entry


def audit_candidate_generic_rootfs(
    boot: boot_verify.BootImageV4,
    entries: tuple[boot_verify.CpioEntry, ...],
    *,
    expected_init: dict[str, Any],
    expected_child: dict[str, Any],
    run_id: bytes,
    module_closure: dict[str, Any],
) -> dict[str, Any]:
    """Derive the executable semantics directly from the candidate boot ramdisk."""
    closure = validate_module_closure(module_closure)
    if len(run_id) != 16:
        raise ClosureError("E2 candidate run ID length mismatch")
    seen: dict[str, tuple[str, boot_verify.CpioEntry]] = {}
    for entry in entries:
        if entry.name in seen:
            raise ClosureError(f"candidate generic rootfs duplicate: {entry.name}")
        if entry.file_type == "symlink" or entry.nlink != 1:
            raise ClosureError(f"candidate generic rootfs alias: {entry.name}")
        seen[entry.name] = ("generic", entry)
    init = _exact_executable(seen, "init", expected_init)
    child = _exact_executable(seen, "s22-e1-child", expected_child)
    try:
        init_elf = e1_static.inspect_static_elf(init.data, "E2 /init")
        child_elf = e1_static.inspect_static_elf(child.data, "E2 child")
    except e1_static.CheckError as exc:
        raise ClosureError("E2 candidate executable ELF contract mismatch") from exc
    if (
        init_elf.get("entrypoint") != EXPECTED_ELF_ENTRYPOINTS["init"]
        or child_elf.get("entrypoint") != EXPECTED_ELF_ENTRYPOINTS["child"]
    ):
        raise ClosureError("E2 candidate executable entrypoint mismatch")
    if init.data.count(run_id) != 1:
        raise ClosureError("E2 candidate /init run ID cardinality mismatch")
    required = (
        b"/proc/s22_checkpoint",
        b"/proc/modules",
        b"/sys/class/udc",
        b"a600000.dwc3",
        b"/s22-e1-child",
        *(row["file"].encode("ascii") for row in closure["modules"]),
    )
    if any(value not in init.data for value in required):
        raise ClosureError("E2 candidate /init runtime strings are incomplete")
    forbidden = (
        b"/dev/block",
        b"/config/usb_gadget",
        b"ttyGS",
        b"/bin/sh",
        b"sec_log_buf.ko",
    )
    if any(value in init.data for value in forbidden):
        raise ClosureError("E2 candidate /init contains forbidden authority")
    child_token = p241.p233.legacy_e1.CHILD_TOKEN
    if child.data.count(child_token) != 1:
        raise ClosureError("E2 candidate child token cardinality mismatch")
    if b"rdinit=" in boot.header["cmdline"].encode("ascii"):
        raise ClosureError("E2 candidate boot cmdline has an rdinit override")

    def executable_record(
        entry: boot_verify.CpioEntry, identity: dict[str, Any], elf: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            **identity,
            "uid": entry.uid,
            "gid": entry.gid,
            "mode": stat.S_IMODE(entry.mode),
            "nlink": entry.nlink,
            "elf": elf,
        }

    return {
        "entry_count": len(entries),
        "no_duplicate_or_alias": True,
        "init": {
            **executable_record(init, expected_init, init_elf),
            "run_id_count": 1,
            "required_strings_complete": True,
            "forbidden_authority_absent": True,
        },
        "child": {
            **executable_record(child, expected_child, child_elf),
            "token_count": 1,
        },
        "rdinit_override_absent": True,
        "verified": True,
    }


def rootfs_audit(
    candidate: bytes,
    vendor_boot: bytes,
    lz4_tool: Path,
    *,
    expected_init: dict[str, Any],
    expected_child: dict[str, Any],
    run_id: bytes,
    module_closure: dict[str, Any],
) -> dict[str, Any]:
    closure = validate_module_closure(module_closure)
    boot = boot_verify.parse_boot_v4(candidate)
    vendor = boot_verify.parse_vendor_boot_v4(vendor_boot)
    generic_entries = boot_verify.parse_newc(
        boot_verify.decompress_lz4(lz4_tool, boot.ramdisk)
    )
    generic_rootfs = audit_candidate_generic_rootfs(
        boot,
        generic_entries,
        expected_init=expected_init,
        expected_child=expected_child,
        run_id=run_id,
        module_closure=closure,
    )
    layers: list[tuple[str, tuple[boot_verify.CpioEntry, ...]]] = [
        ("generic", generic_entries)
    ]
    for index, fragment in enumerate(vendor.fragments):
        layers.append(
            (
                f"vendor[{index}]/{fragment.name}",
                boot_verify.parse_newc(
                    boot_verify.decompress_lz4(lz4_tool, fragment.data)
                ),
            )
        )
    seen: dict[str, tuple[str, boot_verify.CpioEntry]] = {}
    for label, entries in layers:
        for entry in entries:
            if entry.name in seen:
                raise ClosureError(f"effective E2 rootfs duplicate: {entry.name}")
            if entry.file_type == "symlink" or entry.nlink != 1:
                raise ClosureError(f"effective E2 rootfs alias: {label}:{entry.name}")
            seen[entry.name] = (label, entry)
    module_rows = []
    for row in closure["modules"]:
        value = seen.get(f"lib/modules/{row['file']}")
        if value is None:
            raise ClosureError(f"effective E2 module missing: {row['file']}")
        label, entry = value
        if (
            not label.startswith("vendor[")
            or entry.file_type != "regular"
            or receipt(entry.data)
            != {"size": row["size"], "sha256": row["sha256"]}
        ):
            raise ClosureError(f"effective E2 module mismatch: {row['file']}")
        module_rows.append(
            {"file": row["file"], "runtime": row["runtime_name"], "layer": label}
        )
    if any(
        b"rdinit=" in value
        for value in (
            boot.header["cmdline"].encode("ascii"),
            vendor.cmdline.encode("ascii"),
            vendor.bootconfig,
        )
    ):
        raise ClosureError("effective E2 rootfs has an rdinit override")
    return {
        "composition_order": [label for label, _entries in layers],
        "entry_count": len(seen),
        "generic_rootfs": generic_rootfs,
        "no_duplicate_override_or_alias": True,
        "init": {
            **expected_init,
            "elf": generic_rootfs["init"]["elf"],
            "run_id_count": 1,
        },
        "child": {**expected_child, "elf": generic_rootfs["child"]["elf"]},
        "modules": module_rows,
        "module_count": len(module_rows),
        "module_closure_sha256": closure_sha256(closure),
        "rdinit_override_absent": True,
        "verified": True,
    }


def validate_effective_rootfs(
    value: Any,
    *,
    expected_init: dict[str, Any],
    expected_child: dict[str, Any],
    module_closure: dict[str, Any],
) -> dict[str, Any]:
    closure = validate_module_closure(module_closure)
    normalized_init = _identity(expected_init, "expected E2 init")
    normalized_child = _identity(expected_child, "expected E2 child")
    if not isinstance(value, dict) or set(value) != {
        "composition_order",
        "entry_count",
        "generic_rootfs",
        "no_duplicate_override_or_alias",
        "init",
        "child",
        "modules",
        "module_count",
        "module_closure_sha256",
        "rdinit_override_absent",
        "verified",
    }:
        raise ClosureError("effective E2 rootfs shape mismatch")
    expected_modules = [
        {"file": row["file"], "runtime": row["runtime_name"], "layer": "vendor[0]/"}
        for row in closure["modules"]
    ]
    init = value.get("init")
    child = value.get("child")
    if not isinstance(init, dict) or set(init) != {
        "size",
        "sha256",
        "elf",
        "run_id_count",
    }:
        raise ClosureError("effective E2 init shape mismatch")
    if not isinstance(child, dict) or set(child) != {"size", "sha256", "elf"}:
        raise ClosureError("effective E2 child shape mismatch")
    init_elf = _validate_elf(init.get("elf"), "init")
    child_elf = _validate_elf(child.get("elf"), "child")
    _validate_generic_rootfs(
        value.get("generic_rootfs"),
        expected_init=normalized_init,
        expected_child=normalized_child,
        init_elf=init_elf,
        child_elf=child_elf,
    )
    if (
        value.get("composition_order") != ["generic", "vendor[0]/"]
        or type(value.get("entry_count")) is not int
        or value["entry_count"] != 474
        or value.get("no_duplicate_override_or_alias") is not True
        or _identity(
            {name: init.get(name) for name in ("size", "sha256")},
            "effective E2 init",
        )
        != normalized_init
        or type(init.get("run_id_count")) is not int
        or init["run_id_count"] != 1
        or _identity(
            {name: child.get(name) for name in ("size", "sha256")},
            "effective E2 child",
        )
        != normalized_child
        or value.get("modules") != expected_modules
        or type(value.get("module_count")) is not int
        or value["module_count"] != 59
        or value.get("module_closure_sha256") != closure_sha256(closure)
        or value.get("rdinit_override_absent") is not True
        or value.get("verified") is not True
    ):
        raise ClosureError("effective E2 rootfs invariant mismatch")
    return value
