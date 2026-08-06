#!/usr/bin/env python3
"""P3.10 stock closure with the exact P3.08 userspace/module delta."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
from pathlib import Path
from typing import Iterator

from s22plus_fyg8_p300_e2_stock_closure import *  # noqa: F403
import s22plus_fyg8_p300_e2_stock_closure as parent
import s22plus_fyg8_p304_e2_stock_closure as module_parent
import s22plus_fyg8_p310_candidate_contract as candidate_contract
import s22plus_fyg8_p310_source_contract as source_contract


SCHEMA = "s22plus_fyg8_p310_stock_closure_h0_v1"
VERDICT = "PASS_P310_STOCK_CLOSURE_HOST_ONLY"
ClosureError = parent.ClosureError
_entrypoints = parent._entrypoints  # noqa: SLF001
ADDITIONAL_ABSOLUTE_PATH_STRINGS = frozenset(
    {"/dev/kmsg", "/sys/module/eud/parameters/enable"}
)
REQUIRED_ABSOLUTE_PATH_STRINGS = frozenset(
    {*parent.REQUIRED_ABSOLUTE_PATH_STRINGS, *ADDITIONAL_ABSOLUTE_PATH_STRINGS}
)
ALLOWED_ABSOLUTE_PATH_STRINGS = frozenset(
    {*parent.ALLOWED_ABSOLUTE_PATH_STRINGS, *ADDITIONAL_ABSOLUTE_PATH_STRINGS}
)
INCIDENTAL_INIT_SIZE = 66416
INCIDENTAL_PATH = b'/E9"'
INCIDENTAL_PATH_OFFSET = 0x41C1
INCIDENTAL_TEXT_OFFSET = 0x120
INCIDENTAL_TEXT_END = 0x8FB0
INCIDENTAL_TEXT_SHA256 = (
    "2ddc6da0fcab05f89984dbdba79ef1fdeef4a0678cef077bdebf8fd1d74dac6b"
)
INCIDENTAL_INSTRUCTION_WINDOW_OFFSET = 0x41C0
INCIDENTAL_INSTRUCTION_WINDOW = bytes.fromhex("e02f453922000090")


@contextmanager
def _context() -> Iterator[None]:
    previous = {
        "source_contract": parent.source_contract,
        "SCHEMA": parent.SCHEMA,
        "VERDICT": parent.VERDICT,
    }
    parent.source_contract = source_contract
    parent.SCHEMA = SCHEMA
    parent.VERDICT = VERDICT
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(parent, name, value)


def select(source_contract_id: str | None):
    source_contract.require(source_contract_id, source_contract.PROFILE)
    return __import__(__name__)


def _scrub_exact_incidental_opcode_path(data: bytes) -> bytes:
    text = data[INCIDENTAL_TEXT_OFFSET:INCIDENTAL_TEXT_END]
    if (
        len(data) != INCIDENTAL_INIT_SIZE
        or hashlib.sha256(text).hexdigest() != INCIDENTAL_TEXT_SHA256
        or data.count(INCIDENTAL_PATH) != 1
        or data.find(INCIDENTAL_PATH) != INCIDENTAL_PATH_OFFSET
        or INCIDENTAL_PATH_OFFSET != INCIDENTAL_INSTRUCTION_WINDOW_OFFSET + 1
        or INCIDENTAL_INSTRUCTION_WINDOW_OFFSET < INCIDENTAL_TEXT_OFFSET
        or (
            INCIDENTAL_INSTRUCTION_WINDOW_OFFSET
            + len(INCIDENTAL_INSTRUCTION_WINDOW)
            > INCIDENTAL_TEXT_END
        )
        or (INCIDENTAL_INSTRUCTION_WINDOW_OFFSET - INCIDENTAL_TEXT_OFFSET) % 4
        != 0
        or data[
            INCIDENTAL_INSTRUCTION_WINDOW_OFFSET:
            INCIDENTAL_INSTRUCTION_WINDOW_OFFSET
            + len(INCIDENTAL_INSTRUCTION_WINDOW)
        ]
        != INCIDENTAL_INSTRUCTION_WINDOW
    ):
        raise ClosureError("P3.10 incidental opcode-path receipt mismatch")
    return (
        data[:INCIDENTAL_PATH_OFFSET]
        + (b"\0" * len(INCIDENTAL_PATH))
        + data[INCIDENTAL_PATH_OFFSET + len(INCIDENTAL_PATH):]
    )


def _validate_p310_authority_strings(data: bytes) -> None:
    printable = parent.p286.p282.p280.isolated_p260._printable_strings(data)  # noqa: SLF001
    paths = parent.p286.p282._absolute_path_candidates(printable)  # noqa: SLF001
    incidental = paths - ALLOWED_ABSOLUTE_PATH_STRINGS
    if (
        REQUIRED_ABSOLUTE_PATH_STRINGS - paths
        or incidental != {INCIDENTAL_PATH.decode("ascii")}
        or any(
            data.count(value.encode("ascii")) != 1
            for value in ADDITIONAL_ABSOLUTE_PATH_STRINGS
        )
    ):
        raise ClosureError("P3.10 candidate absolute-path authority mismatch")
    scrubbed = _scrub_exact_incidental_opcode_path(data)
    previous_required = parent.REQUIRED_ABSOLUTE_PATH_STRINGS
    previous_allowed = parent.ALLOWED_ABSOLUTE_PATH_STRINGS
    parent.REQUIRED_ABSOLUTE_PATH_STRINGS = REQUIRED_ABSOLUTE_PATH_STRINGS
    parent.ALLOWED_ABSOLUTE_PATH_STRINGS = ALLOWED_ABSOLUTE_PATH_STRINGS
    try:
        with parent._p300_authority_globals():  # noqa: SLF001
            parent._P282_VALIDATE_AUTHORITY_STRINGS(scrubbed)  # noqa: SLF001
    finally:
        parent.REQUIRED_ABSOLUTE_PATH_STRINGS = previous_required
        parent.ALLOWED_ABSOLUTE_PATH_STRINGS = previous_allowed


_validate_p282_authority_strings = _validate_p310_authority_strings


@contextmanager
def exact_init_authority(expected: bytes) -> Iterator[None]:
    def validate(data: bytes) -> None:
        if data != expected:
            raise ClosureError(
                "P3.10 effective init differs from source-bound userspace"
            )
        _validate_p310_authority_strings(data)

    previous = parent.p286.p282._validate_p282_authority_strings  # noqa: SLF001
    parent.p286.p282._validate_p282_authority_strings = validate  # noqa: SLF001
    try:
        yield
    finally:
        parent.p286.p282._validate_p282_authority_strings = previous  # noqa: SLF001


def derive_module_closure(
    root: Path,
    vendor_ramdisk: Path,
    lz4: Path,
    plan_header: Path | None = None,
):
    if plan_header is None:
        raise ClosureError("P3.10 exact materialized plan is missing")
    intent_path = plan_header.parent.parent / "candidate-intent.json"
    patch_path = intent_path.parent / "candidate.patch"
    exact = candidate_contract.verify(
        root,
        root / candidate_contract.DEFAULT_SOURCE,
        intent_path,
        patch_path,
    )
    supplied = module_parent.p241.stable_read(
        plan_header, "P3.10 materialized plan", 1024 * 1024
    )
    if module_parent.receipt(supplied) != exact["materialized_sources"]["plan_header"]:
        raise ClosureError("P3.10 supplied plan identity differs")
    names = module_parent.plan_spec.module_names(supplied)
    _metadata, expanded, insertion = module_parent._expanded_plan(root)  # noqa: SLF001
    if names != expanded.modules:
        raise ClosureError("P3.10 supplied 61-module plan order differs")
    parent_closure = parent.derive_module_closure(
        root, vendor_ramdisk, lz4, plan_header=None
    )
    audit = module_parent.p241.audit_vendor_modules(
        root, vendor_ramdisk, lz4, expanded
    )
    notifier = audit["modules"][insertion]
    if (
        notifier.get("file") != module_parent.plan_spec.MODULE_NAME
        or notifier.get("runtime_name") != module_parent.plan_spec.MODULE_RUNTIME
        or {key: notifier.get(key) for key in ("size", "sha256")}
        != {
            "size": module_parent.overlay.MODULE_SIZE,
            "sha256": module_parent.overlay.MODULE_SHA256,
        }
    ):
        raise ClosureError("P3.10 effective stock notifier identity differs")
    result = {
        "schema": module_parent.SCHEMA,
        "verdict": module_parent.VERDICT,
        "files": [row["file"] for row in audit["modules"]],
        "runtime_names": [row["runtime_name"] for row in audit["modules"]],
        "count": audit["module_count"],
        "modules": audit["modules"],
        "insertion_index": insertion,
        "plan_header": module_parent.receipt(supplied),
        "parent_closure": parent_closure,
        "parent_closure_sha256": parent.closure_sha256(parent_closure),
        "vendor_ramdisk": audit["vendor_ramdisk"],
        "vendor_entry_count": audit["entry_count"],
        "request_firmware_string_hits": audit["request_firmware_string_hits"],
        "sec_log_buf_absent": audit["sec_log_buf_absent"],
        "verified": True,
    }
    result["closure_sha256"] = module_parent.closure_sha256(result)
    return module_parent.validate_module_closure(result)


validate_module_closure = module_parent.validate_module_closure
audit_candidate_generic_rootfs = module_parent.audit_candidate_generic_rootfs
rootfs_audit = module_parent.rootfs_audit
validate_effective_rootfs = module_parent.validate_effective_rootfs


def build_result(root=None):  # noqa: ANN001, ANN201
    with _context():
        return parent.build_result(root)
