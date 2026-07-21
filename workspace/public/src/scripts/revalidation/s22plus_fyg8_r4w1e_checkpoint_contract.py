#!/usr/bin/env python3
"""Validate and model the host-only FYG8 R4W1-E runtime checkpoint carrier."""

from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_r4w1e_checkpoint_contract_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
VERDICT = "PASS_R4W1E_CHECKPOINT_CARRIER_HOST_CONTRACT"
BLOCKED_VERDICT = "BLOCKED_R4W1E_CHECKPOINT_CARRIER_HOST_CONTRACT"
CONFIG = "CONFIG_S22PLUS_FYG8_RUNTIME_CHECKPOINT"

LOG_BASE = 0x800200000
LOG_SIZE = 0x200000
LOG_MAGIC = 0x4D474F4C
ENTRY_SIZE = 45
SLOT_SIZE = 64
SLOT_COUNT = 2
REGION_SIZE = ENTRY_SIZE + SLOT_SIZE * SLOT_COUNT
REQUEST_SIZE = 32
FORMAT_VERSION = 1
COMMIT = 0xA5

OUTCOME_PROGRESS = 0
OUTCOME_SUCCESS = 1
OUTCOME_FAILURE = 2

CARRIER_PREIMAGE = (
    "S22PLUS_FYG8_R4W1E_OBSERVABLE_RUNTIME_CHECKPOINT|SM-S906N|g0q|"
    "S906NKSS7FYG8|"
    "base-main=7d281c86ca63646083b9f489eed28281c7d2518f397f34ceccf34c223eaa663a|"
    "geometry=entry45+slot64x2-contiguous-pre-cursor|"
    "writer=sec-log-unloaded-and-idx-unchanged|"
    "target=waipio-mtp+kernel-log-dt-resource|"
    "api=pid1-only-fixed32-crc32-profile-kind-run-id|"
    "slots=ab-generation-crc-commit-last|stages=exact-successor-v1"
)
CARRIER_SHA256 = (
    "9ac60dac17baf39c32ad46a69174edc75a7481155f57df627da4a78d09909d74"
)
CARRIER_ID = bytes.fromhex(CARRIER_SHA256[:32])
ENTRY_PROOF = f"\n[[S22P1E|{CARRIER_SHA256[:32]}]]\n".encode("ascii")
ENTRY_FAMILY = b"[[S22P1E|"
ENTRY_PREFIXES = tuple(
    ENTRY_FAMILY[:length]
    for length in range(len(b"[[S22P1"), len(ENTRY_FAMILY) + 1)
)

PROFILE_DESCRIPTIONS = {
    "E1": (
        "S22PLUS_FYG8_R4W1E_E1_LOCAL_RUNTIME|"
        "mount-readback+static-child-token-exit-reap+watchdog5+quiet-park"
    ),
    "E2": (
        "S22PLUS_FYG8_R4W1E_E2_USB_BIND_UDC|"
        "e1+exact-module-closure+platform-bind+dwc3-child+udc"
    ),
    "E3": (
        "S22PLUS_FYG8_R4W1E_E3_ACM_ONE_WAY|"
        "e2+configfs-acm+peripheral+ttygs0+exact-banner"
    ),
    "E4": (
        "S22PLUS_FYG8_R4W1E_E4_FIXED_EXCHANGE|"
        "e3+one-status-nonce-request+one-bound-response"
    ),
}
PROFILE_NUMBERS = {"E1": 1, "E2": 2, "E3": 3, "E4": 4}
PROFILE_BY_NUMBER = {number: name for name, number in PROFILE_NUMBERS.items()}

STAGES = {
    "ENTRY": 0x00,
    "PROC_MOUNTED": 0x10,
    "SYS_MOUNTED": 0x11,
    "DEV_TMPFS_MOUNTED": 0x12,
    "RUN_TMPFS_MOUNTED": 0x13,
    "DEV_NODES_VERIFIED": 0x14,
    "CHILD_EXEC_STARTED": 0x20,
    "CHILD_TOKEN_VERIFIED": 0x21,
    "CHILD_REAPED": 0x22,
    "WDT_MODULE_0": 0x30,
    "WDT_MODULE_1": 0x31,
    "WDT_MODULE_2": 0x32,
    "WDT_MODULE_3": 0x33,
    "WDT_MODULE_4": 0x34,
    "WDT_MODULES_VERIFIED": 0x35,
    "E1_SUCCESS": 0x3F,
    "USB_MODULE_BASE": 0x40,
    "USB_MODULE_LAST": 0x7A,
    "USB_MODULES_VERIFIED": 0x7B,
    "USB_PLATFORM_BOUND": 0x7C,
    "USB_DWC3_CHILD_PRESENT": 0x7D,
    "USB_UDC_PRESENT": 0x7E,
    "E2_SUCCESS": 0x7F,
    "ACM_CONFIGFS_MOUNTED": 0x80,
    "ACM_GADGET_CONFIGURED": 0x81,
    "ACM_PERIPHERAL_ROLE": 0x82,
    "ACM_UDC_BOUND": 0x83,
    "ACM_TTYGS0_READY": 0x84,
    "ACM_BANNER_WRITTEN": 0x85,
    "E3_SUCCESS": 0x8F,
    "EXCHANGE_REQUEST_READ": 0x90,
    "EXCHANGE_REQUEST_VERIFIED": 0x91,
    "EXCHANGE_RESPONSE_WRITTEN": 0x92,
    "E4_SUCCESS": 0x9F,
}
PROFILE_TERMINAL_STAGE = {
    "E1": STAGES["E1_SUCCESS"],
    "E2": STAGES["E2_SUCCESS"],
    "E3": STAGES["E3_SUCCESS"],
    "E4": STAGES["E4_SUCCESS"],
}

E1_SEQUENCE = (
    STAGES["PROC_MOUNTED"],
    STAGES["SYS_MOUNTED"],
    STAGES["DEV_TMPFS_MOUNTED"],
    STAGES["RUN_TMPFS_MOUNTED"],
    STAGES["DEV_NODES_VERIFIED"],
    STAGES["CHILD_EXEC_STARTED"],
    STAGES["CHILD_TOKEN_VERIFIED"],
    STAGES["CHILD_REAPED"],
    STAGES["WDT_MODULE_0"],
    STAGES["WDT_MODULE_1"],
    STAGES["WDT_MODULE_2"],
    STAGES["WDT_MODULE_3"],
    STAGES["WDT_MODULE_4"],
    STAGES["WDT_MODULES_VERIFIED"],
    STAGES["E1_SUCCESS"],
)
E2_EXTENSION = tuple(
    range(STAGES["USB_MODULE_BASE"], STAGES["USB_MODULE_LAST"] + 1)
) + (
    STAGES["USB_MODULES_VERIFIED"],
    STAGES["USB_PLATFORM_BOUND"],
    STAGES["USB_DWC3_CHILD_PRESENT"],
    STAGES["USB_UDC_PRESENT"],
    STAGES["E2_SUCCESS"],
)
E3_EXTENSION = (
    STAGES["ACM_CONFIGFS_MOUNTED"],
    STAGES["ACM_GADGET_CONFIGURED"],
    STAGES["ACM_PERIPHERAL_ROLE"],
    STAGES["ACM_UDC_BOUND"],
    STAGES["ACM_TTYGS0_READY"],
    STAGES["ACM_BANNER_WRITTEN"],
    STAGES["E3_SUCCESS"],
)
E4_EXTENSION = (
    STAGES["EXCHANGE_REQUEST_READ"],
    STAGES["EXCHANGE_REQUEST_VERIFIED"],
    STAGES["EXCHANGE_RESPONSE_WRITTEN"],
    STAGES["E4_SUCCESS"],
)
PROFILE_STAGE_SEQUENCES = {
    "E1": E1_SEQUENCE,
    "E2": E1_SEQUENCE + E2_EXTENSION,
    "E3": E1_SEQUENCE + E2_EXTENSION + E3_EXTENSION,
    "E4": E1_SEQUENCE + E2_EXTENSION + E3_EXTENSION + E4_EXTENSION,
}
PROFILE_SCHEMA_PREIMAGES = {
    name: (
        f"S22PLUS_FYG8_R4W1E_PROFILE_SCHEMA_V1|profile={name}|"
        f"number={PROFILE_NUMBERS[name]}|"
        f"sequence={','.join(f'{stage:02x}' for stage in sequence)}|"
        f"terminal={PROFILE_TERMINAL_STAGE[name]:02x}|request=32|slot=64"
    )
    for name, sequence in PROFILE_STAGE_SEQUENCES.items()
}
PROFILE_SCHEMA_SHA256 = {
    name: hashlib.sha256(preimage.encode("ascii")).hexdigest()
    for name, preimage in PROFILE_SCHEMA_PREIMAGES.items()
}
MODEL_RUN_IDS = {
    name: hashlib.sha256(
        (
            f"R4W1E_HOST_MODEL_ONLY|profile={name}|"
            f"schema={PROFILE_SCHEMA_SHA256[name]}"
        ).encode("ascii")
    ).digest()[:16]
    for name in PROFILE_NUMBERS
}

REQUEST_STRUCT = struct.Struct("<4s4BhBB16sI")
SLOT_STRUCT = struct.Struct("<4s6BhI16s16sIII3sB")

DEFAULT_SOURCE = Path("workspace/private/work/s22plus_fyg8_kernel_rebuild_r0")
DEFAULT_PATCH = Path(
    "workspace/public/src/patches/s22plus_fyg8_r4w1e_runtime_checkpoint.patch"
)
PATCH_SHA256 = "98bb55be7b87791d5861ebd27c2ceabc234d40ae28a2c4a936cccc728c4c2f1e"
BASE_FILES = {
    "kernel_platform/common/init/main.c": (
        "7d281c86ca63646083b9f489eed28281c7d2518f397f34ceccf34c223eaa663a"
    ),
    "kernel_platform/common/init/Kconfig": (
        "8273d233a441c21df2fcb1d5d17a590321d758205fd5babd8b8dcb4e6a334019"
    ),
    "kernel_platform/common/arch/arm64/configs/gki_defconfig": (
        "12661b7d249fb8f80135c3fdcd331733b86d5215f2f4e88e356d1516831ab493"
    ),
}
PATCHED_FILES = {
    "kernel_platform/common/init/main.c": (
        "1f695064114ed3d718e5f40a4d5ae4e90ab3dfc303bc78a2d11c8b1af021a53d"
    ),
    "kernel_platform/common/init/Kconfig": (
        "bac6b3e9b1a836f890d509721c27e1079c7556398518f1ff87eb6f7dbe66e239"
    ),
    "kernel_platform/common/arch/arm64/configs/gki_defconfig": (
        "f123c74fe27330a48e458d146ed05b5e8e1075fbf63cc74afed6e5fe7e48af60"
    ),
}


class CheckError(ValueError):
    pass


@dataclass(frozen=True)
class Request:
    profile: str
    run_id: str
    stage: int
    outcome: int
    item_index: int
    detail: int


@dataclass(frozen=True)
class Slot:
    slot_id: int
    generation: int
    stage: int
    outcome: int
    item_index: int
    detail: int
    profile: str | None
    run_id: str
    seed_idx: int
    boot_cnt: int


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise CheckError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def crc32(data: bytes) -> int:
    return binascii.crc32(data) & 0xFFFFFFFF


def _profile_stages(profile: str) -> set[int]:
    if profile not in PROFILE_STAGE_SEQUENCES:
        raise CheckError(f"unknown checkpoint profile: {profile}")
    return set(PROFILE_STAGE_SEQUENCES[profile])


def _stage_generation(profile: str, stage: int) -> int:
    try:
        return PROFILE_STAGE_SEQUENCES[profile].index(stage) + 1
    except (KeyError, ValueError) as exc:
        raise CheckError(f"stage 0x{stage:02x} is not valid for {profile}") from exc


def _validate_semantics(
    profile: str, stage: int, outcome: int, item_index: int, detail: int
) -> None:
    if not 0 <= item_index <= 0xFF:
        raise CheckError("item index is outside u8")
    if not -0x8000 <= detail <= 0x7FFF:
        raise CheckError("detail is outside s16")
    if stage not in _profile_stages(profile):
        raise CheckError(f"stage 0x{stage:02x} is not valid for {profile}")
    if outcome not in {OUTCOME_PROGRESS, OUTCOME_SUCCESS, OUTCOME_FAILURE}:
        raise CheckError("unknown checkpoint outcome")
    if STAGES["USB_MODULE_BASE"] <= stage <= STAGES["USB_MODULE_LAST"]:
        if item_index != stage - STAGES["USB_MODULE_BASE"]:
            raise CheckError("USB module checkpoint item index mismatch")
    elif item_index != 0:
        raise CheckError("non-module checkpoint item index must be zero")
    terminal = PROFILE_TERMINAL_STAGE[profile]
    if outcome == OUTCOME_SUCCESS and stage != terminal:
        raise CheckError("success outcome is not on the profile terminal stage")
    if outcome == OUTCOME_PROGRESS and stage == terminal:
        raise CheckError("terminal stage cannot be progress")
    if outcome == OUTCOME_FAILURE and detail == 0:
        raise CheckError("failure outcome requires nonzero detail")
    if outcome != OUTCOME_FAILURE and detail != 0:
        raise CheckError("non-failure checkpoint detail must be zero")


def encode_request(
    profile: str,
    stage: int,
    *,
    run_id: bytes,
    outcome: int = OUTCOME_PROGRESS,
    item_index: int = 0,
    detail: int = 0,
) -> bytes:
    _validate_semantics(profile, stage, outcome, item_index, detail)
    if len(run_id) != 16 or not any(run_id):
        raise CheckError("checkpoint run manifest ID is invalid")
    prefix = REQUEST_STRUCT.pack(
        b"S22Q",
        FORMAT_VERSION,
        PROFILE_NUMBERS[profile],
        stage,
        outcome,
        detail,
        item_index,
        0,
        run_id,
        0,
    )[:-4]
    return prefix + struct.pack("<I", crc32(prefix))


def decode_request(data: bytes) -> Request:
    if len(data) != REQUEST_SIZE:
        raise CheckError("checkpoint request size mismatch")
    (
        magic,
        version,
        profile_number,
        stage,
        outcome,
        detail,
        item_index,
        reserved,
        run_id,
        recorded_crc,
    ) = REQUEST_STRUCT.unpack(data)
    if magic != b"S22Q" or version != FORMAT_VERSION or reserved != 0:
        raise CheckError("checkpoint request header mismatch")
    if crc32(data[:-4]) != recorded_crc:
        raise CheckError("checkpoint request CRC mismatch")
    profile = PROFILE_BY_NUMBER.get(profile_number)
    if profile is None:
        raise CheckError("checkpoint request profile is not allowlisted")
    if not any(run_id):
        raise CheckError("checkpoint request run manifest ID is zero")
    _validate_semantics(profile, stage, outcome, item_index, detail)
    return Request(profile, run_id.hex(), stage, outcome, item_index, detail)


def encode_slot(
    *,
    slot_id: int,
    generation: int,
    profile: str | None,
    stage: int,
    outcome: int,
    item_index: int,
    detail: int,
    run_id: bytes,
    seed_idx: int,
    boot_cnt: int,
    committed: bool = True,
) -> bytes:
    if slot_id not in {0, 1} or not 0 <= generation <= 0xFFFFFFFF:
        raise CheckError("invalid checkpoint slot identity")
    profile_number = 0 if profile is None else PROFILE_NUMBERS.get(profile, -1)
    if profile_number < 0 or len(run_id) != 16:
        raise CheckError("checkpoint slot profile or run ID size mismatch")
    if generation == 0:
        if profile is not None or any(run_id):
            raise CheckError("initial checkpoint slot identity mismatch")
    else:
        if profile is None or not any(run_id):
            raise CheckError("checkpoint slot run identity is missing")
        _validate_semantics(profile, stage, outcome, item_index, detail)
        if generation != _stage_generation(profile, stage):
            raise CheckError("checkpoint slot generation does not match stage")
    prefix = SLOT_STRUCT.pack(
        b"S22C",
        FORMAT_VERSION,
        slot_id,
        profile_number,
        stage,
        outcome,
        item_index,
        detail,
        generation,
        CARRIER_ID,
        run_id,
        seed_idx,
        boot_cnt,
        0,
        b"\0\0\0",
        COMMIT if committed else 0,
    )
    body = prefix[:56]
    return body + struct.pack("<I", crc32(body)) + prefix[60:]


def decode_slot(data: bytes, expected_slot: int) -> Slot:
    if len(data) != SLOT_SIZE:
        raise CheckError("checkpoint slot size mismatch")
    (
        magic,
        version,
        slot_id,
        profile_number,
        stage,
        outcome,
        item_index,
        detail,
        generation,
        carrier_id,
        run_id,
        seed_idx,
        boot_cnt,
        recorded_crc,
        reserved1,
        commit,
    ) = SLOT_STRUCT.unpack(data)
    if commit != COMMIT:
        raise CheckError("checkpoint slot is not committed")
    if magic != b"S22C" or version != FORMAT_VERSION or slot_id != expected_slot:
        raise CheckError("checkpoint slot header mismatch")
    if reserved1 != b"\0\0\0":
        raise CheckError("checkpoint slot reserved bytes are nonzero")
    if carrier_id != CARRIER_ID:
        raise CheckError("checkpoint slot carrier ID mismatch")
    if crc32(data[:56]) != recorded_crc:
        raise CheckError("checkpoint slot CRC mismatch")
    if (generation & 1) != slot_id:
        raise CheckError("checkpoint slot generation parity mismatch")
    if generation == 0:
        if (
            profile_number != 0
            or run_id != bytes(16)
            or stage != STAGES["ENTRY"]
            or outcome != OUTCOME_PROGRESS
            or item_index != 0
            or detail != 0
        ):
            raise CheckError("initial checkpoint slot semantics mismatch")
        profile = None
    else:
        profile = PROFILE_BY_NUMBER.get(profile_number)
        if profile is None:
            raise CheckError("checkpoint slot profile is not allowlisted")
        if not any(run_id):
            raise CheckError("checkpoint slot run manifest ID is zero")
        _validate_semantics(profile, stage, outcome, item_index, detail)
        if generation != _stage_generation(profile, stage):
            raise CheckError("checkpoint slot generation does not match stage")
    return Slot(
        slot_id=slot_id,
        generation=generation,
        stage=stage,
        outcome=outcome,
        item_index=item_index,
        detail=detail,
        profile=profile,
        run_id=run_id.hex(),
        seed_idx=seed_idx,
        boot_cnt=boot_cnt,
    )


def initial_region(seed_idx: int, boot_cnt: int) -> bytes:
    if seed_idx < LOG_SIZE - 16 or seed_idx > 0xFFFFFFFF:
        raise CheckError("initial checkpoint seed index is not saturated")
    initial = encode_slot(
        slot_id=0,
        generation=0,
        profile=None,
        stage=STAGES["ENTRY"],
        outcome=OUTCOME_PROGRESS,
        item_index=0,
        detail=0,
        run_id=bytes(16),
        seed_idx=seed_idx,
        boot_cnt=boot_cnt,
    )
    return ENTRY_PROOF + initial + bytes(SLOT_SIZE)


def decode_region(
    region: bytes,
    expected_profile: str | None = None,
    *,
    expected_run_id: bytes | None = None,
    expected_seed_idx: int | None = None,
    expected_boot_cnt: int | None = None,
) -> dict[str, Any]:
    if len(region) != REGION_SIZE or region[:ENTRY_SIZE] != ENTRY_PROOF:
        raise CheckError("checkpoint region entry or size mismatch")
    valid: list[Slot] = []
    uncommitted: list[int] = []
    invalid_committed: list[int] = []
    for slot_id in range(SLOT_COUNT):
        start = ENTRY_SIZE + slot_id * SLOT_SIZE
        raw = region[start : start + SLOT_SIZE]
        if raw[-1] != COMMIT:
            uncommitted.append(slot_id)
            continue
        try:
            valid.append(decode_slot(raw, slot_id))
        except CheckError:
            invalid_committed.append(slot_id)
    if not valid:
        raise CheckError("checkpoint region has no valid committed slot")
    valid.sort(key=lambda slot: slot.generation)
    if len(valid) == 2:
        older, newer = valid
        if newer.generation != older.generation + 1:
            raise CheckError("checkpoint A/B generations are not adjacent")
        if newer.seed_idx != older.seed_idx or newer.boot_cnt != older.boot_cnt:
            raise CheckError("checkpoint A/B boot identity mismatch")
        if older.outcome != OUTCOME_PROGRESS:
            raise CheckError("checkpoint advanced after a terminal slot")
        if newer.stage <= older.stage:
            raise CheckError("checkpoint A/B stage is not monotonic")
        if older.profile is not None and newer.profile != older.profile:
            raise CheckError("checkpoint A/B profile changed")
        if older.profile is not None and newer.run_id != older.run_id:
            raise CheckError("checkpoint A/B run manifest ID changed")
    active = valid[-1]
    if active.seed_idx < LOG_SIZE - 16:
        raise CheckError("checkpoint active seed index is not saturated")
    if expected_profile is not None and active.profile != expected_profile:
        raise CheckError("checkpoint active profile mismatch")
    if expected_run_id is not None:
        if len(expected_run_id) != 16 or active.run_id != expected_run_id.hex():
            raise CheckError("checkpoint active run manifest ID mismatch")
    if expected_seed_idx is not None and active.seed_idx != expected_seed_idx:
        raise CheckError("checkpoint active seed index mismatch")
    if expected_boot_cnt is not None and active.boot_cnt != expected_boot_cnt:
        raise CheckError("checkpoint active boot count mismatch")
    identity_bound = all(
        value is not None
        for value in (
            expected_profile,
            expected_run_id,
            expected_seed_idx,
            expected_boot_cnt,
        )
    )
    return {
        "entry": ENTRY_PROOF.decode("ascii").strip(),
        "active": asdict(active),
        "valid_slots": [asdict(slot) for slot in valid],
        "uncommitted_slots": uncommitted,
        "invalid_committed_slots": invalid_committed,
        "terminal": active.outcome in {OUTCOME_SUCCESS, OUTCOME_FAILURE},
        "structurally_valid": True,
        "identity_bound": identity_bound,
    }


def apply_request(region: bytes, request_data: bytes) -> bytes:
    decoded = decode_region(region)
    active = Slot(**decoded["active"])
    request = decode_request(request_data)
    if decoded["terminal"]:
        raise CheckError("checkpoint region is already terminal")
    if active.profile is not None and request.profile != active.profile:
        raise CheckError("checkpoint request changes profile")
    if active.profile is not None and request.run_id != active.run_id:
        raise CheckError("checkpoint request changes run manifest ID")
    sequence = PROFILE_STAGE_SEQUENCES[request.profile]
    if active.generation >= len(sequence) or request.stage != sequence[active.generation]:
        raise CheckError("checkpoint request is not the exact next stage")
    generation = active.generation + 1
    if generation > 0xFFFFFFFF:
        raise CheckError("checkpoint generation overflow")
    next_slot = active.slot_id ^ 1
    encoded = encode_slot(
        slot_id=next_slot,
        generation=generation,
        profile=request.profile,
        stage=request.stage,
        outcome=request.outcome,
        item_index=request.item_index,
        detail=request.detail,
        run_id=bytes.fromhex(request.run_id),
        seed_idx=active.seed_idx,
        boot_cnt=active.boot_cnt,
    )
    updated = bytearray(region)
    start = ENTRY_SIZE + next_slot * SLOT_SIZE
    updated[start + SLOT_SIZE - 1] = 0
    updated[start : start + SLOT_SIZE - 1] = encoded[:-1]
    updated[start + SLOT_SIZE - 1] = encoded[-1]
    return bytes(updated)


def place_initial_region(
    payload: bytes, index: int, boot_cnt: int
) -> tuple[bytes, int]:
    if not payload or index < len(payload) or index > 0xFFFFFFFF:
        raise CheckError("invalid saturated ring geometry")
    if REGION_SIZE > len(payload):
        raise CheckError("checkpoint region exceeds ring payload")
    cursor = index % len(payload)
    position = cursor - REGION_SIZE if cursor >= REGION_SIZE else len(payload) - REGION_SIZE
    updated = bytearray(payload)
    updated[position : position + REGION_SIZE] = initial_region(index, boot_cnt)
    return bytes(updated), position


def decode_observer(
    data: bytes,
    *,
    expected_profile: str,
    expected_run_id: bytes,
    expected_seed_idx: int,
    expected_boot_cnt: int,
) -> dict[str, Any]:
    if (
        any(data.count(prefix) != 1 for prefix in ENTRY_PREFIXES)
        or data.count(ENTRY_PROOF) != 1
    ):
        raise CheckError("observer entry marker cardinality mismatch")
    position = data.index(ENTRY_PROOF)
    end = position + REGION_SIZE
    if end > len(data):
        raise CheckError("observer checkpoint region is truncated")
    result = decode_region(
        data[position:end],
        expected_profile,
        expected_run_id=expected_run_id,
        expected_seed_idx=expected_seed_idx,
        expected_boot_cnt=expected_boot_cnt,
    )
    if not result["identity_bound"]:
        raise CheckError("observer checkpoint identity is not fully bound")
    result["observer_offset"] = position
    result["evidence_verified"] = True
    return result


def _added_patch_lines(text: str) -> list[str]:
    return [
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def check_patch_policy(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise CheckError("R4W1-E patch is missing or indirect")
    actual_sha = sha256_file(path)
    if actual_sha != PATCH_SHA256:
        raise CheckError(f"R4W1-E patch SHA256 mismatch: {actual_sha}")
    text = path.read_text(encoding="ascii")
    targets = re.findall(r"^\+\+\+ b/(.+)$", text, flags=re.MULTILINE)
    if set(targets) != set(BASE_FILES) or len(targets) != len(BASE_FILES):
        raise CheckError(f"unexpected R4W1-E patch targets: {targets}")
    added = _added_patch_lines(text)
    added_text = "\n".join(added)
    symbols = {
        symbol
        for line in added
        for symbol in re.findall(r"CONFIG_[A-Z0-9_]+", line)
    }
    if symbols != {CONFIG}:
        raise CheckError(f"unexpected R4W1-E config symbols: {sorted(symbols)}")
    forbidden = (
        "panic(",
        "emergency_restart",
        "kernel_restart",
        "reboot(",
        "filp_open",
        "kernel_write",
        "blkdev_get",
        "submit_bio",
        "ioremap(",
        "sec_log_buf.ko",
    )
    hits = [token for token in forbidden if token in added_text]
    if hits:
        raise CheckError(f"forbidden R4W1-E operations: {hits}")
    required = (
        ENTRY_PROOF.decode("ascii").strip(),
        CONFIG,
        'proc_create("s22_checkpoint", 0200',
        "task_pid_nr(current) != 1",
        "s22plus_fyg8_cp_header_unchanged(head)",
        "s22plus_fyg8_cp_target_allowed()",
        'of_machine_is_compatible("qcom,waipio-mtp")',
        'of_find_compatible_node(NULL, NULL,\n\t\t\t"samsung,kernel_log_buf")',
        'of_parse_phandle(log_node, "memory-region", 0)',
        "WRITE_ONCE(target->commit, 0)",
        "WRITE_ONCE(target->commit, S22PLUS_FYG8_CP_COMMIT)",
        "request->stage != expected",
        "request->stage == terminal && detail == 0",
        "request.profile == s22plus_fyg8_cp_state.profile",
        "request.run_id, s22plus_fyg8_cp_state.run_id",
        "request.outcome != S22PLUS_FYG8_CP_OUTCOME_PROGRESS",
    )
    missing = [token for token in required if token not in added_text]
    if missing:
        raise CheckError(f"R4W1-E patch tokens missing: {missing}")
    return {
        "path": str(path),
        "sha256": actual_sha,
        "targets": targets,
        "added_config_symbols": sorted(symbols),
        "forbidden_hits": hits,
        "verified": True,
    }


def check_base_files(source: Path) -> dict[str, Any]:
    checked = []
    for relative, expected in BASE_FILES.items():
        path = source / relative
        if path.is_symlink() or not path.is_file():
            raise CheckError(f"base file missing or indirect: {relative}")
        actual = sha256_file(path)
        if actual != expected:
            raise CheckError(f"base SHA256 mismatch for {relative}: {actual}")
        checked.append({"path": relative, "sha256": actual})
    return {"files": checked, "verified": True}


def apply_patch_to_minimal_tree(source: Path, patch: Path) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="s22plus-r4w1e-check-") as temporary:
        root = Path(temporary)
        for relative in BASE_FILES:
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, destination)
            os.chmod(destination, 0o644)
        completed = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(patch)],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if completed.returncode != 0:
            raise CheckError(f"R4W1-E patch application failed: {completed.stdout[-2000:]}")
        actual = {relative: sha256_file(root / relative) for relative in BASE_FILES}
        if actual != PATCHED_FILES:
            raise CheckError(f"R4W1-E patched SHA256 mismatch: {actual}")
        return {
            relative: (root / relative).read_text(encoding="utf-8")
            for relative in BASE_FILES
        }


def check_patched_sources(patched: dict[str, str]) -> dict[str, Any]:
    main = patched["kernel_platform/common/init/main.c"]
    kconfig = patched["kernel_platform/common/init/Kconfig"]
    defconfig = patched[
        "kernel_platform/common/arch/arm64/configs/gki_defconfig"
    ]
    exact_counts = {
        "entry_marker": main.count(ENTRY_PROOF.decode("ascii").strip()),
        "proc_node": main.count('proc_create("s22_checkpoint", 0200'),
        "exec_definition": main.count(
            "static void s22plus_fyg8_checkpoint_init_exec(const char *init_filename)"
        ),
        "exec_call": main.count(
            "s22plus_fyg8_checkpoint_init_exec(ramdisk_execute_command);"
        ),
        "proc_write_definition": main.count(
            "static ssize_t s22plus_fyg8_checkpoint_write(struct file *file,"
        ),
        "target_guard_definition": main.count(
            "static bool s22plus_fyg8_cp_target_allowed(void)"
        ),
        "stage_guard_definition": main.count(
            "static bool s22plus_fyg8_cp_request_allowed("
        ),
        "pid1_guard": main.count("task_pid_nr(current) != 1"),
        "index_publish": main.count("WRITE_ONCE(head->idx"),
        "commit_clear": main.count("WRITE_ONCE(target->commit, 0);"),
        "commit_publish": main.count(
            "WRITE_ONCE(target->commit, S22PLUS_FYG8_CP_COMMIT);"
        ),
    }
    expected = {
        "entry_marker": 1,
        "proc_node": 1,
        "exec_definition": 1,
        "exec_call": 1,
        "proc_write_definition": 1,
        "target_guard_definition": 1,
        "stage_guard_definition": 1,
        "pid1_guard": 2,
        "index_publish": 0,
        "commit_clear": 1,
        "commit_publish": 1,
    }
    if exact_counts != expected:
        raise CheckError(f"R4W1-E source cardinality mismatch: {exact_counts}")
    required = (
        f"0x{LOG_BASE:x}ULL",
        f"0x{LOG_SIZE:x}U",
        f"0x{LOG_MAGIC:08x}U",
        f"#define S22PLUS_FYG8_CP_REQUEST_SIZE\t{REQUEST_SIZE}U",
        f"#define S22PLUS_FYG8_CP_SLOT_SIZE\t{SLOT_SIZE}U",
        f"#define S22PLUS_FYG8_CP_ENTRY_SIZE\t{ENTRY_SIZE}U",
        "seed_idx < payload_size",
        "cursor >= sizeof(*region) ? cursor - sizeof(*region) :",
        "payload_size - sizeof(*region);",
        "READ_ONCE(head->idx) == s22plus_fyg8_cp_state.seed_idx",
        "READ_ONCE(head->boot_cnt) == s22plus_fyg8_cp_state.seed_boot_cnt",
        "s22plus_fyg8_cp_target_allowed()",
        "of_address_to_resource(log_node, 0, &log_resource)",
        "of_address_to_resource(memory_node, 0, &memory_resource)",
        'of_property_read_bool(memory_node, "no-map")',
        "request->stage != expected",
        "request->stage == terminal && detail == 0",
        "request.profile == s22plus_fyg8_cp_state.profile",
        "request.run_id, s22plus_fyg8_cp_state.run_id",
        "s22plus_fyg8_cp_state.active_slot ^ 1U",
        "late_initcall(s22plus_fyg8_checkpoint_proc_init);",
        "offsetof(struct s22plus_fyg8_cp_request, detail) != 8",
        "offsetof(struct s22plus_fyg8_cp_request, run_id) != 12",
        "offsetof(struct s22plus_fyg8_cp_request, crc32) != 28",
        "offsetof(struct s22plus_fyg8_cp_slot, detail) != 10",
        "offsetof(struct s22plus_fyg8_cp_slot, generation) != 12",
        "offsetof(struct s22plus_fyg8_cp_slot, run_id) != 32",
        "offsetof(struct s22plus_fyg8_cp_slot, crc32) != 56",
        "offsetof(struct s22plus_fyg8_cp_slot, commit) != 63",
    )
    missing = [token for token in required if token not in main]
    if missing:
        raise CheckError(f"R4W1-E source tokens missing: {missing}")
    transition_start = main.index("static u8 s22plus_fyg8_cp_next_stage(u8 stage)")
    transition_end = main.index(
        "static bool s22plus_fyg8_cp_request_allowed", transition_start
    )
    transition_body = main[transition_start:transition_end]
    transition_pairs = re.findall(
        r"case 0x([0-9a-f]{2}): return 0x([0-9a-f]{2});",
        transition_body,
    )
    transition_predecessors = [previous for previous, _ in transition_pairs]
    if len(transition_predecessors) != len(set(transition_predecessors)):
        raise CheckError("R4W1-E duplicate C transition case")
    explicit_transitions = {
        int(previous, 16): int(following, 16)
        for previous, following in transition_pairs
    }

    def source_next_stage(stage: int) -> int | None:
        if STAGES["USB_MODULE_BASE"] <= stage < STAGES["USB_MODULE_LAST"]:
            return stage + 1
        return explicit_transitions.get(stage)

    for profile, sequence in PROFILE_STAGE_SEQUENCES.items():
        previous = STAGES["ENTRY"]
        for expected_stage in sequence:
            if source_next_stage(previous) != expected_stage:
                raise CheckError(
                    f"R4W1-E C/Python transition mismatch for {profile}: "
                    f"0x{previous:02x} -> 0x{expected_stage:02x}"
                )
            previous = expected_stage
    terminal_tokens = {
        name: (
            f"case S22PLUS_FYG8_CP_PROFILE_{name}:\n"
            f"\t\treturn 0x{PROFILE_TERMINAL_STAGE[name]:02x};"
        )
        for name in PROFILE_NUMBERS
    }
    missing_terminals = [
        name for name, token in terminal_tokens.items() if token not in main
    ]
    if missing_terminals:
        raise CheckError(f"R4W1-E terminal table mismatch: {missing_terminals}")
    run_copy = (
        "memcpy(s22plus_fyg8_cp_state.run_id, request.run_id,\n"
        "\t\t       sizeof(s22plus_fyg8_cp_state.run_id));"
    )
    if main.count(run_copy) != 1 or "run_id = s22plus_fyg8_cp_state.run_id" in main:
        raise CheckError("R4W1-E run ID copy aliases persistent state")
    init_start = main.index(
        "static void s22plus_fyg8_checkpoint_init_exec(const char *init_filename)"
    )
    init_end = main.index("static ssize_t s22plus_fyg8_checkpoint_write", init_start)
    init_body = main[init_start:init_end]
    if init_body.index("if (!s22plus_fyg8_cp_target_allowed())") > init_body.index(
        "head = s22plus_fyg8_cp_head();"
    ):
        raise CheckError("R4W1-E target guard follows physical mapping")
    success_edge = (
        "\tif (ramdisk_execute_command) {\n"
        "\t\tret = run_init_process(ramdisk_execute_command);\n"
        "\t\tif (!ret) {\n"
        "\t\t\ts22plus_fyg8_checkpoint_init_exec(ramdisk_execute_command);\n"
        "#ifdef CONFIG_RKP\n"
    )
    if main.count(success_edge) != 1:
        raise CheckError("R4W1-E entry is not on the unique exec-success edge")
    if kconfig.count("config S22PLUS_FYG8_RUNTIME_CHECKPOINT") != 1:
        raise CheckError("R4W1-E Kconfig definition mismatch")
    if kconfig.count("depends on OF && OF_ADDRESS") != 1:
        raise CheckError("R4W1-E OF dependency mismatch")
    if kconfig.count("select CRC32") != 1:
        raise CheckError("R4W1-E CRC32 dependency mismatch")
    if defconfig.count(f"{CONFIG}=y") != 1:
        raise CheckError("R4W1-E defconfig enable mismatch")
    return {
        "entry_proof": ENTRY_PROOF.decode("ascii").strip(),
        "entry_size": ENTRY_SIZE,
        "slot_size": SLOT_SIZE,
        "slot_count": SLOT_COUNT,
        "region_size": REGION_SIZE,
        "request_size": REQUEST_SIZE,
        "exact_counts": exact_counts,
        "index_mutated": False,
        "target_guarded_before_physical_dereference": True,
        "exact_stage_successor_enforced": True,
        "run_manifest_id_dynamic": True,
        "profile_transition_lengths": {
            name: len(sequence)
            for name, sequence in PROFILE_STAGE_SEQUENCES.items()
        },
        "abi_offsets": {
            "request_detail": 8,
            "request_run_id": 12,
            "request_crc32": 28,
            "slot_detail": 10,
            "slot_generation": 12,
            "slot_run_id": 32,
            "slot_crc32": 56,
            "slot_commit": 63,
        },
        "sec_log_buf_module_must_remain_unloaded": True,
        "patched_files": PATCHED_FILES,
        "verified": True,
    }


def profile_contract() -> dict[str, Any]:
    return {
        name: {
            "number": PROFILE_NUMBERS[name],
            "description": PROFILE_DESCRIPTIONS[name],
            "schema_preimage": PROFILE_SCHEMA_PREIMAGES[name],
            "schema_sha256": PROFILE_SCHEMA_SHA256[name],
            "terminal_stage": PROFILE_TERMINAL_STAGE[name],
            "stage_sequence": list(PROFILE_STAGE_SEQUENCES[name]),
            "run_manifest_id_required": True,
            "host_model_run_id_not_live": MODEL_RUN_IDS[name].hex(),
        }
        for name in ("E1", "E2", "E3", "E4")
    }


def run_check(source: Path, patch: Path) -> dict[str, Any]:
    if REQUEST_STRUCT.size != REQUEST_SIZE or SLOT_STRUCT.size != SLOT_SIZE:
        raise CheckError("Python checkpoint ABI struct size mismatch")
    derived = hashlib.sha256(CARRIER_PREIMAGE.encode("ascii")).hexdigest()
    if derived != CARRIER_SHA256 or len(ENTRY_PROOF) != ENTRY_SIZE:
        raise CheckError("R4W1-E carrier derivation mismatch")
    base = check_base_files(source)
    patch_result = check_patch_policy(patch)
    patched = apply_patch_to_minimal_tree(source, patch)
    source_contract = check_patched_sources(patched)
    model = initial_region(0x300000, 7)
    model = apply_request(
        model,
        encode_request(
            "E1", STAGES["PROC_MOUNTED"], run_id=MODEL_RUN_IDS["E1"]
        ),
    )
    model_result = decode_region(
        model,
        "E1",
        expected_run_id=MODEL_RUN_IDS["E1"],
        expected_seed_idx=0x300000,
        expected_boot_cnt=7,
    )
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": VERDICT,
        "base": base,
        "patch": patch_result,
        "source_contract": source_contract,
        "geometry": {
            "log_base": f"0x{LOG_BASE:x}",
            "log_size": LOG_SIZE,
            "entry_size": ENTRY_SIZE,
            "slot_size": SLOT_SIZE,
            "slot_count": SLOT_COUNT,
            "region_size": REGION_SIZE,
            "request_size": REQUEST_SIZE,
            "contiguous_pre_cursor": True,
            "ring_index_mutated": False,
            "cursor_must_remain_unchanged": True,
            "runtime_dt_target_guard": True,
            "sec_log_buf_module_must_remain_unloaded": True,
        },
        "carrier": {
            "preimage": CARRIER_PREIMAGE,
            "sha256": CARRIER_SHA256,
            "id": CARRIER_ID.hex(),
            "entry_proof": ENTRY_PROOF.decode("ascii").strip(),
        },
        "profiles": profile_contract(),
        "run_manifest_binding": {
            "required_for_live_evidence": True,
            "kernel_accepts_dynamic_nonzero_id": True,
            "host_requires_exact_expected_id": True,
            "p2_7_model_ids_are_not_live": True,
        },
        "model_selfcheck": model_result,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "kernel_build": False,
            "image_created": False,
            "candidate_packaged": False,
            "flash": False,
            "live_authorized": False,
            "partition_write": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    result = run_check(resolve(root, args.source), resolve(root, args.patch))
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        output = resolve(root, args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="ascii")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CheckError as exc:
        print(json.dumps({"verdict": BLOCKED_VERDICT, "error": str(exc)}))
        raise SystemExit(2) from exc
