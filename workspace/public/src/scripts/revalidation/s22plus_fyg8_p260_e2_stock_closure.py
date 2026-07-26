#!/usr/bin/env python3
"""P2.60 proof-bound stock closure over the unchanged 60-module plan."""

from __future__ import annotations

import importlib.util
import stat
import sys
from pathlib import Path
from types import ModuleType

import s22plus_fyg8_p242_e2_stock_closure as legacy
import s22plus_fyg8_p253_e2_stock_closure as p253
import s22plus_fyg8_p257_e2_stock_closure as p257
import s22plus_fyg8_p260_source_contract as source_contract


ClosureError = p257.ClosureError
SCHEMA = "s22plus_fyg8_p260_stock_closure_h0_v1"
VERDICT = "PASS_P260_STOCK_CLOSURE_HOST_ONLY"
ORDER_MODEL = p257.ORDER_MODEL
EXPECTED_ELF_ENTRYPOINTS = {"init": 0x401A9C, "child": 0x4000CC}
EXPECTED_GENERIC_ENTRY_COUNT = p257.EXPECTED_GENERIC_ENTRY_COUNT
DEFAULT_VENDOR_RAMDISK = p257.DEFAULT_VENDOR_RAMDISK
DEFAULT_VENDOR_BOOT = p257.DEFAULT_VENDOR_BOOT
DEFAULT_LZ4 = p257.DEFAULT_LZ4
EXPECTED_MODULE_COUNT = p257.EXPECTED_MODULE_COUNT
EXPECTED_PLAN_TSV_SHA256 = p257.EXPECTED_PLAN_TSV_SHA256
EXPECTED_MODULE_CLOSURE_SHA256 = p257.EXPECTED_MODULE_CLOSURE_SHA256
EXPECTED_DISPCC = p257.EXPECTED_DISPCC
boot_verify = p257.boot_verify
receipt = p257.receipt
closure_sha256 = p257.closure_sha256
_ISOLATED_MODULE_NAME = "_s22plus_fyg8_p260_isolated_p242_stock_closure"


def _load_isolated_legacy() -> ModuleType:
    path = Path(legacy.__file__).resolve()
    spec = importlib.util.spec_from_file_location(_ISOLATED_MODULE_NAME, path)
    if spec is None or spec.loader is None:
        raise ClosureError("cannot create isolated P2.60 stock-closure module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_ISOLATED_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(_ISOLATED_MODULE_NAME, None)
        raise
    module.EXPECTED_ELF_ENTRYPOINTS = dict(EXPECTED_ELF_ENTRYPOINTS)
    return module


isolated_legacy = _load_isolated_legacy()


def _printable_strings(data: bytes) -> frozenset[str]:
    result = set()
    start = None
    for index, value in enumerate(data + b"\0"):
        if 0x20 <= value <= 0x7E:
            if start is None:
                start = index
            continue
        if start is not None and index - start >= 1:
            result.add(data[start:index].decode("ascii"))
        start = None
    return frozenset(result)


def _validate_p260_authority_strings(data: bytes) -> None:
    strings = _printable_strings(data)
    absolute_paths = frozenset(
        value for value in strings if value.startswith("/")
    )
    if not absolute_paths.issubset(
        source_contract.spec.ALLOWED_ABSOLUTE_PATH_STRINGS
    ):
        raise ClosureError("P2.60 candidate absolute-path authority mismatch")
    if not source_contract.spec.REQUIRED_ABSOLUTE_PATH_STRINGS.issubset(
        absolute_paths
    ):
        raise ClosureError("P2.60 candidate required absolute path is missing")
    if not source_contract.spec.E3_REQUIRED_CONTROL_STRINGS.issubset(strings):
        raise ClosureError("P2.60 candidate E3 control strings are incomplete")

    hex_controls = frozenset(
        value
        for value in strings
        if value[:2].lower() == "0x"
        and len(value) > 2
        and all(character in "0123456789abcdefABCDEF" for character in value[2:])
    )
    function_targets = frozenset(
        value for value in strings if "functions/" in value
    )
    speed_controls = frozenset(
        value for value in strings if value.endswith("-speed")
    )
    role_controls = frozenset(
        value
        for value in strings
        if value in {"device", "host", "none", "otg", "peripheral"}
    )
    udc_names = frozenset(
        value
        for value in strings
        if "/" not in value and value.endswith(".dwc3")
    )
    expected = (
        (
            hex_controls,
            source_contract.spec.E3_HEX_CONTROL_STRINGS,
            "hex control",
        ),
        (
            function_targets,
            source_contract.spec.E3_FUNCTION_TARGET_STRINGS,
            "function target",
        ),
        (
            speed_controls,
            source_contract.spec.E3_SPEED_CONTROL_STRINGS,
            "speed control",
        ),
        (
            role_controls,
            source_contract.spec.E3_ROLE_CONTROL_STRINGS,
            "role control",
        ),
        (
            udc_names,
            source_contract.spec.E3_UDC_NAME_STRINGS,
            "UDC name",
        ),
    )
    for actual, allowed, label in expected:
        if actual != allowed:
            raise ClosureError(f"P2.60 candidate {label} authority mismatch")


def _p260_audit_candidate_generic_rootfs(
    boot,
    entries,
    *,
    expected_init,
    expected_child,
    run_id,
    module_closure,
):
    closure = isolated_legacy.validate_module_closure(module_closure)
    if len(run_id) != 16:
        raise ClosureError("P2.60 candidate run ID length mismatch")
    seen = {}
    for entry in entries:
        if entry.name in seen:
            raise ClosureError(f"P2.60 candidate rootfs duplicate: {entry.name}")
        if entry.file_type == "symlink" or entry.nlink != 1:
            raise ClosureError(f"P2.60 candidate rootfs alias: {entry.name}")
        seen[entry.name] = ("generic", entry)
    init = isolated_legacy._exact_executable(seen, "init", expected_init)
    child = isolated_legacy._exact_executable(
        seen, "s22-e1-child", expected_child
    )
    try:
        init_elf = isolated_legacy.e1_static.inspect_static_elf(
            init.data, "P2.60 /init"
        )
        child_elf = isolated_legacy.e1_static.inspect_static_elf(
            child.data, "P2.60 child"
        )
    except isolated_legacy.e1_static.CheckError as exc:
        raise ClosureError(
            "P2.60 candidate executable ELF contract mismatch"
        ) from exc
    if (
        init_elf.get("entrypoint") != EXPECTED_ELF_ENTRYPOINTS["init"]
        or child_elf.get("entrypoint") != EXPECTED_ELF_ENTRYPOINTS["child"]
    ):
        raise ClosureError("P2.60 candidate executable entrypoint mismatch")
    if init.data.count(run_id) != 1:
        raise ClosureError("P2.60 candidate /init run ID cardinality mismatch")
    required = (
        b"/proc/s22_checkpoint",
        b"/proc/modules",
        b"/sys/class/udc",
        b"a600000.dwc3",
        b"/s22-e1-child",
        *(
            value.encode("ascii")
            for value in source_contract.spec.E3_AUTHORITY_STRINGS
        ),
        *(row["file"].encode("ascii") for row in closure["modules"]),
    )
    if any(value not in init.data for value in required):
        raise ClosureError(
            "P2.60 candidate /init runtime or E3 authority is incomplete"
        )
    _validate_p260_authority_strings(init.data)
    forbidden = (b"/dev/block", b"/bin/sh", b"sec_log_buf.ko")
    if any(value in init.data for value in forbidden):
        raise ClosureError("P2.60 candidate /init contains forbidden authority")
    child_token = isolated_legacy.p241.p233.legacy_e1.CHILD_TOKEN
    if child.data.count(child_token) != 1:
        raise ClosureError("P2.60 candidate child token cardinality mismatch")
    if b"rdinit=" in boot.header["cmdline"].encode("ascii"):
        raise ClosureError("P2.60 candidate boot cmdline has an rdinit override")

    def executable_record(entry, identity, elf):
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


def _call_with_p260_entrypoints(function, *args, **kwargs):
    previous = p253.isolated_legacy
    previous_audit = isolated_legacy.audit_candidate_generic_rootfs
    p253.isolated_legacy = isolated_legacy
    isolated_legacy.audit_candidate_generic_rootfs = (
        _p260_audit_candidate_generic_rootfs
    )
    try:
        return function(*args, **kwargs)
    finally:
        isolated_legacy.audit_candidate_generic_rootfs = previous_audit
        p253.isolated_legacy = previous


def select(source_contract_id: str | None):
    source_contract.require(source_contract_id, "E2")
    return sys.modules[__name__]


def validate_module_closure(value, *, allow_unpinned: bool = False):
    return p257.validate_module_closure(
        value, allow_unpinned=allow_unpinned
    )


def derive_module_closure(root, vendor_ramdisk, lz4, plan_header=None):
    result = p257.derive_module_closure(
        root,
        vendor_ramdisk,
        lz4,
        plan_header=plan_header,
    )
    return validate_module_closure(result)


def audit_candidate_generic_rootfs(
    boot,
    entries,
    *,
    expected_init,
    expected_child,
    run_id,
    module_closure,
):
    return _call_with_p260_entrypoints(
        p257.audit_candidate_generic_rootfs,
        boot,
        entries,
        expected_init=expected_init,
        expected_child=expected_child,
        run_id=run_id,
        module_closure=module_closure,
    )


def rootfs_audit(
    candidate,
    vendor_boot,
    lz4_tool,
    *,
    expected_init,
    expected_child,
    run_id,
    module_closure,
):
    return _call_with_p260_entrypoints(
        p257.rootfs_audit,
        candidate,
        vendor_boot,
        lz4_tool,
        expected_init=expected_init,
        expected_child=expected_child,
        run_id=run_id,
        module_closure=module_closure,
    )


def validate_effective_rootfs(
    value,
    *,
    expected_init,
    expected_child,
    module_closure,
):
    return _call_with_p260_entrypoints(
        p257.validate_effective_rootfs,
        value,
        expected_init=expected_init,
        expected_child=expected_child,
        module_closure=module_closure,
    )


def build_result(root=None):
    result = dict(p257.build_result(root))
    result.update(
        {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "contract_id": source_contract.CONTRACT_ID,
        }
    )
    return result
