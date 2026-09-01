#!/usr/bin/env python3
"""Dormant H0 owner model for S20+ TWRP identical-resident Q0.

The model binds the exact metadata D0 proof, retained T2 recovery, known-good
resident boot and Download/Odin fallback, and the fixed write/readback backend.
It deliberately exposes only a render-plan entrypoint.  Journal, parser,
recovery owner, contract activation, fresh preparation, approval, and every
device action remain absent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

import build_s20plus_g986n_twrp_identical_resident_write_q0_h0 as q0_build
import s20plus_g986n_p0_twrp_boot_owner_h0 as p0
import s20plus_g986n_twrp_boot_identity_d0 as d0


ROOT = Path(__file__).resolve().parents[5]
SCHEMA = "s20plus_g986n_twrp_identical_resident_q0_owner_h0_v1"
STATUS = "H0_PASS_GO_NOT_ACTIVE"
Q0_ACTIVE = False
APPROVAL_PREFIX = "S20PLUS-G986N-TWRP-IDENTICAL-RESIDENT-Q0-F1-APPROVE:"
TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "incremental": "G986NKSS8IYC2",
}
HEX64_RE = re.compile(r"[0-9a-f]{64}")

TARGET_CONTRACT = ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
BACKEND_ROOT = ROOT / (
    "workspace/private/outputs/s20plus_g986n/"
    "twrp_identical_resident_write_q0_h0"
)
BACKEND = BACKEND_ROOT / "s20plus_twrp_boot_write_q0"
BACKEND_SIZE = 597_720
BACKEND_SHA256 = "16271fee5c31ddb34e426b29ae5032e0fe366623eb3114862aac1ea1cc1022b5"
BACKEND_MANIFEST = BACKEND_ROOT / "manifest.json"
BACKEND_MANIFEST_SIZE = 7_517
BACKEND_MANIFEST_SHA256 = (
    "e9b587c558c15cf1367e271f6b05561a40131a680bf5ee299d6e6c75a2ce9d86"
)
D0_RESULT = ROOT / (
    "workspace/private/runs/s20plus-g986n-twrp-boot-identity-d0/"
    "run-1788251361439704044/result.json"
)
D0_RESULT_SIZE = 2_812
D0_RESULT_SHA256 = "46ffd0388fdcf23b46608f1557d9523e9b338316537bc19c45015877eba5f6b7"
RESIDENT_BOOT = p0.ROLLBACK_BOOT
RESIDENT_BOOT_SIZE = 67_108_864
RESIDENT_BOOT_SHA256 = (
    "d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc"
)
T2_TERMINAL = p0.T2_TERMINAL
T2_TERMINAL_SIZE = 1_911
T2_TERMINAL_SHA256 = (
    "da24acd3b33c78f4ed41565858e5314bb2c3a1acaf020ac06fb83fd99ab84d05"
)

PUBLIC_CLOSURE = {
    "repository_contract": {
        "path": ROOT / "AGENTS.md",
        "size": 23_923,
        "sha256": "e59b3550ca226156d66bd22eb4a80735b2a88eefd594aa9b85c14e9411427ca4",
    },
    "risk_tiers": {
        "path": ROOT / "docs/operations/DEVICE_ACTION_RISK_TIERS.md",
        "size": 23_691,
        "sha256": "48e0bdc344da56d04d47f1b0e4ed56960f73d88a7dbf286f3640c459981d91af",
    },
    "process_v2": {
        "path": ROOT / "docs/operations/DEVICE_ACTION_PROCESS_V2.md",
        "size": 36_163,
        "sha256": "26d9c8110e19ca4dba09418d07350cd051167423387a684f8deebf76c0843af1",
    },
    "metadata_d0_runner": {
        "path": ROOT / (
            "workspace/public/src/scripts/revalidation/"
            "s20plus_g986n_twrp_boot_identity_d0.py"
        ),
        "size": 29_863,
        "sha256": "a71db531a25778b2dbd38c0b05b897dac33a7cc2f7eef51ba59edd899f9ecec6",
    },
    "metadata_d0_test": {
        "path": ROOT / "tests/test_s20plus_g986n_twrp_boot_identity_d0.py",
        "size": 21_208,
        "sha256": "5f895be987466257a88c59cec980a329aa1027e90b1ba018325b98fe2b6aad1d",
    },
    "metadata_d0_report": {
        "path": ROOT / (
            "docs/reports/"
            "S20PLUS_G986N_TWRP_BOOT_IDENTITY_D0_H0_2026-09-01.md"
        ),
        "size": 8_136,
        "sha256": "a1d32e1c7d8742f6652b10b350feb5dc6f156b7403adf1356f41e0d6791a34fe",
    },
    "q0_backend_source": {
        "path": q0_build.SOURCE,
        "size": 25_151,
        "sha256": "ba79e36822487fdec23909c653bb05540bdced8678fea2a20dba972096378e06",
    },
    "q0_backend_builder": {
        "path": Path(q0_build.__file__).resolve(),
        "size": 16_846,
        "sha256": "57edd59c660faef1a3c39b5fcf6e9eebb1f21d273bb39ac5e63edcf3f9b5949a",
    },
    "q0_backend_test": {
        "path": ROOT / (
            "tests/"
            "test_s20plus_g986n_twrp_identical_resident_write_q0_h0.py"
        ),
        "size": 9_923,
        "sha256": "3e33f3bc0f91c12d2e1162ef1f9ef759dd730a7733da194fea6af8b4a2839086",
    },
    "t2_owner": {
        "path": Path(d0.t2.__file__).resolve(),
        "size": 167_684,
        "sha256": "7f5519ef76091f491165a0be5ce81733f0343318057d02f7577954db1d1a0d11",
    },
    "t2_profile": {
        "path": Path(d0.t2.h0.__file__).resolve(),
        "size": 12_847,
        "sha256": "c02b78f2a1215a1fc2104a4634264609d2060d610bc628a068b318cb1cf55fb7",
    },
    "p0_owner_predecessor": {
        "path": Path(p0.__file__).resolve(),
        "size": 24_295,
        "sha256": "da063130a6a71f841e2863f5b23d5da35bb5238acb0a2ce1337db4570371c95e",
    },
}


class OwnerError(RuntimeError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise OwnerError(f"{label} has duplicate key")
            result[key] = value
        return result

    def reject_constant(_value: str) -> Any:
        raise OwnerError(f"{label} has non-finite number")

    try:
        value = json.loads(
            payload,
            object_pairs_hook=pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OwnerError(f"{label} is malformed") from exc
    if type(value) is not dict:
        raise OwnerError(f"{label} root differs")
    return value


def read_exact_regular(
    path: Path,
    *,
    expected_size: int,
    expected_sha256: str,
    maximum: int,
    label: str,
) -> bytes:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as exc:
        raise OwnerError(f"{label} is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or type(expected_size) is not int
            or expected_size < 1
            or expected_size > maximum
            or before.st_size != expected_size
        ):
            raise OwnerError(f"{label} identity differs")
        chunks: list[bytes] = []
        total = 0
        while total < expected_size:
            chunk = os.read(descriptor, min(1024 * 1024, expected_size - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
        if total != expected_size or os.read(descriptor, 1):
            raise OwnerError(f"{label} length differs")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        after.st_dev != before.st_dev
        or after.st_ino != before.st_ino
        or after.st_size != before.st_size
        or after.st_mtime_ns != before.st_mtime_ns
        or after.st_ctime_ns != before.st_ctime_ns
    ):
        raise OwnerError(f"{label} changed while read")
    payload = b"".join(chunks)
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise OwnerError(f"{label} hash differs")
    return payload


def receipt(
    path: Path,
    size: int,
    sha256: str,
    label: str,
    maximum: int = 256 * 1024,
) -> dict[str, Any]:
    read_exact_regular(
        path,
        expected_size=size,
        expected_sha256=sha256,
        maximum=maximum,
        label=label,
    )
    return {"path": str(path), "size": size, "sha256": sha256}


def exact_bool(value: Any, expected: bool, label: str) -> None:
    if type(value) is not bool or value is not expected:
        raise OwnerError(f"{label} differs")


def exact_int(value: Any, expected: int, label: str) -> None:
    if type(value) is not int or value != expected:
        raise OwnerError(f"{label} differs")


def read_bounded_regular(path: Path, label: str, maximum: int) -> bytes:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as exc:
        raise OwnerError(f"{label} is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size < 1
            or before.st_size > maximum
        ):
            raise OwnerError(f"{label} identity differs")
        chunks: list[bytes] = []
        total = 0
        while total < before.st_size:
            chunk = os.read(descriptor, min(1024 * 1024, before.st_size - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
        if total != before.st_size or os.read(descriptor, 1):
            raise OwnerError(f"{label} length differs")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        after.st_dev != before.st_dev
        or after.st_ino != before.st_ino
        or after.st_size != before.st_size
        or after.st_mtime_ns != before.st_mtime_ns
        or after.st_ctime_ns != before.st_ctime_ns
    ):
        raise OwnerError(f"{label} changed while read")
    return b"".join(chunks)


def validate_target_contract() -> dict[str, Any]:
    payload = read_bounded_regular(TARGET_CONTRACT, "target contract", 256 * 1024)
    text = payload.decode("utf-8")
    required = (
        "## TWRP boot-identity metadata D0",
        "PROVED_S20PLUS_G986N_TWRP_BOOT_IDENTITY_METADATA",
        "`PARTNAME=boot`, partition number 23",
        "## TWRP identical-resident boot-write qualification Q0",
        "Status: **DEFINED - H0 ONLY - NOT ACTIVE**",
        "H0 build success alone is never",
        "live authority.",
    )
    if any(token not in text for token in required):
        raise OwnerError("target contract Q0 semantics differ")
    return {
        "path": str(TARGET_CONTRACT),
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "q0_active": False,
    }


def validate_backend_manifest() -> dict[str, Any]:
    payload = read_exact_regular(
        BACKEND_MANIFEST,
        expected_size=BACKEND_MANIFEST_SIZE,
        expected_sha256=BACKEND_MANIFEST_SHA256,
        maximum=64 * 1024,
        label="Q0 backend manifest",
    )
    value = strict_json(payload, "Q0 backend manifest")
    runtime = value.get("runtime_binding")
    safety = value.get("safety")
    backend = value.get("backend")
    expected_runtime = {
        "stage_dir": "/tmp/s20plus-g986n-identical-resident-q0",
        "backend_name": "s20plus_twrp_boot_write_q0",
        "source_name": "resident-boot.img",
        "target_path": "/dev/block/sda23",
        "rdev": "259:7",
        "partname": "boot",
        "partition_number": 23,
        "size_bytes": RESIDENT_BOOT_SIZE,
        "resident_sha256": RESIDENT_BOOT_SHA256,
    }
    if (
        value.get("schema") != q0_build.SCHEMA
        or value.get("verdict") != q0_build.VERDICT
        or value.get("tier") != "H0"
        or value.get("target") != TARGET
        or type(runtime) is not dict
        or runtime != expected_runtime
        or type(safety) is not dict
        or type(backend) is not dict
        or backend.get("size") != BACKEND_SIZE
        or backend.get("sha256") != BACKEND_SHA256
        or value.get("reproducible_builds") != 2
        or value.get("reproducible_binary_sha256") != BACKEND_SHA256
    ):
        raise OwnerError("Q0 backend manifest identity differs")
    exact_bool(value.get("live_authority"), False, "Q0 manifest live authority")
    for key in (
        "fixed_input",
        "source_and_preimage_exact_before_write",
        "write_fd_identity_guarded",
        "write_fd_used_for_effect",
        "fsync_required",
        "fresh_odirect_readback_fd_independently_guarded",
        "signals_blocked_before_effect",
        "interrupted_write_recoverable_only_not_safe",
    ):
        exact_bool(safety.get(key), True, f"Q0 manifest safety {key}")
    for key in ("caller_arguments", "device_contact", "activation"):
        exact_bool(safety.get(key), False, f"Q0 manifest safety {key}")
    exact_int(safety.get("full_write_bytes"), RESIDENT_BOOT_SIZE, "Q0 write size")
    exact_int(safety.get("reboots"), 0, "Q0 backend reboots")
    exact_int(safety.get("other_partition_paths"), 0, "Q0 other partitions")
    return {
        "path": str(BACKEND_MANIFEST),
        "size": BACKEND_MANIFEST_SIZE,
        "sha256": BACKEND_MANIFEST_SHA256,
        "verdict": q0_build.VERDICT,
        "live_authority": False,
    }


def validate_d0_result() -> dict[str, Any]:
    payload = read_exact_regular(
        D0_RESULT,
        expected_size=D0_RESULT_SIZE,
        expected_sha256=D0_RESULT_SHA256,
        maximum=64 * 1024,
        label="TWRP boot identity D0 result",
    )
    value = strict_json(payload, "TWRP boot identity D0 result")
    boot = value.get("boot_partition")
    recovery = value.get("recovery")
    recovery_identity = (
        recovery.get("t2_identity_without_boot_id")
        if type(recovery) is dict
        else None
    )
    expected_boot = {
        "block_device_open_count": 0,
        "boot_link": "/dev/block/bootdevice/by-name/boot",
        "devname": "sda23",
        "devtype": "partition",
        "direct_path": "/dev/block/sda23",
        "node_is_block": True,
        "partition_content_bytes_read": 0,
        "partition_number": 23,
        "partname": "boot",
        "rdev_major": 259,
        "rdev_minor": 7,
        "sectors_512": 131072,
        "size_bytes": RESIDENT_BOOT_SIZE,
        "sysfs_dev": "259:7",
    }
    if (
        value.get("schema") != "s20plus_g986n_twrp_boot_identity_d0_result_v1"
        or value.get("version") != "s20plus-g986n-twrp-boot-identity-d0-v1"
        or value.get("tier") != "D0"
        or value.get("mode") != "connected-read-only"
        or value.get("verdict") != "PROVED_S20PLUS_G986N_TWRP_BOOT_IDENTITY_METADATA"
        or value.get("target") != TARGET
        or boot != expected_boot
        or type(recovery) is not dict
        or recovery.get("same_retained_recovery_boot") is not True
        or type(recovery_identity) is not dict
        or recovery_identity.get("twrp_version") != p0.T2_VERSION
        or value.get("host_closure_sha256")
        != "ac4b719e44b7650a5dce4382e17914ca1edd5c995178dc2ab087f10b8a6a7dc5"
    ):
        raise OwnerError("TWRP boot identity D0 semantics differ")
    for key, expected in (
        ("host_command_count", 7),
        ("inventory_command_count", 2),
        ("selected_target_command_count", 5),
        ("other_target_command_count", 0),
        ("s22plus_command_count", 0),
        ("a90_command_count", 0),
        ("block_device_open_count", 0),
        ("partition_content_bytes_read", 0),
        ("device_writes", 0),
        ("staged_payloads", 0),
        ("reboots", 0),
        ("mode_transitions", 0),
        ("odin_invocations", 0),
        ("partition_transfers", 0),
    ):
        exact_int(value.get(key), expected, f"D0 result {key}")
    exact_bool(value.get("f1_authorized"), False, "D0 F1 authority")
    exact_bool(
        value.get("direct_block_write_authorized"),
        False,
        "D0 direct block authority",
    )
    for key in ("serial_sha256", "topology_sha256", "current_boot_id_sha256"):
        private_hash = recovery.get(key)
        if type(private_hash) is not str or HEX64_RE.fullmatch(private_hash) is None:
            raise OwnerError(f"D0 private hash {key} differs")
    return {
        "path": str(D0_RESULT),
        "size": D0_RESULT_SIZE,
        "sha256": D0_RESULT_SHA256,
        "verdict": value["verdict"],
        "direct_path": boot["direct_path"],
        "rdev": boot["sysfs_dev"],
        "partname": boot["partname"],
        "partition_number": boot["partition_number"],
        "size_bytes": boot["size_bytes"],
        "same_retained_recovery_boot": True,
        "f1_authorized": False,
        "direct_block_write_authorized": False,
    }


def validate_t2_predecessor() -> dict[str, Any]:
    predecessor = d0.validate_t2_predecessor()
    if (
        predecessor.get("journal_node_count") != 43
        or predecessor.get("candidate_consumed") is not True
        or predecessor.get("t2_transfer_authority_inherited") is not False
        or predecessor.get("terminal", {}).get("sha256") != T2_TERMINAL_SHA256
    ):
        raise OwnerError("retained T2 predecessor differs")
    return {
        "terminal_path": str(T2_TERMINAL),
        "terminal_size": T2_TERMINAL_SIZE,
        "terminal_sha256": T2_TERMINAL_SHA256,
        "journal_node_count": 43,
        "verdict": "PROVED_T2_RECOVERY_RETAINED",
        "candidate_consumed": True,
        "candidate_replay_permitted": False,
        "new_t2_transfer_authority": False,
    }


def validate_closure() -> dict[str, Any]:
    closure: dict[str, Any] = {}
    for name, expected in PUBLIC_CLOSURE.items():
        closure[name] = receipt(
            expected["path"],
            expected["size"],
            expected["sha256"],
            f"Q0 {name}",
        )
    closure["target_contract"] = validate_target_contract()
    closure["backend_manifest"] = validate_backend_manifest()
    closure["backend"] = receipt(
        BACKEND,
        BACKEND_SIZE,
        BACKEND_SHA256,
        "Q0 backend",
        maximum=4 * 1024 * 1024,
    )
    closure["metadata_d0_result"] = validate_d0_result()
    closure["retained_t2"] = validate_t2_predecessor()
    closure["resident_boot"] = receipt(
        RESIDENT_BOOT,
        RESIDENT_BOOT_SIZE,
        RESIDENT_BOOT_SHA256,
        "Q0 resident boot",
        maximum=80 * 1024 * 1024,
    )
    closure["download_odin_fallback"] = p0.audit_rollback_ap()
    return closure


def binding_value() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "active": Q0_ACTIVE,
        "live_authority": False,
        "target": TARGET,
        "closure": validate_closure(),
        "qualification": {
            "tier_if_future_activated": "F1",
            "purpose": "resident-over-byte-identical-resident TWRP boot write/readback",
            "candidate_sha256": RESIDENT_BOOT_SHA256,
            "preimage_sha256": RESIDENT_BOOT_SHA256,
            "readback_sha256": RESIDENT_BOOT_SHA256,
            "candidate_is_p0": False,
            "retires_p0_candidate_attempt": False,
            "backend_accepts_caller_input": False,
            "torn_identical_write_safe": False,
        },
        "proposed_effect_budget": {
            "volatile_stage_files": 2,
            "boot_partition_content_reads": 2,
            "boot_partition_write_attempts": 1,
            "boot_partition_write_bytes": RESIDENT_BOOT_SIZE,
            "fsync_attempts": 1,
            "physical_system_boots": 1,
            "physical_direct_recovery_returns": 1,
            "odin_boot_fallback_attempts": 1,
            "recovery_partition_writes": 0,
            "misc_writes": 0,
            "other_partition_writes": 0,
            "replay": False,
        },
        "proposed_state_machine": [
            "future-prepare-exact-current-t2-and-empty-exclusive-tmpfs-stage",
            "future-publish-durable-stage-intent-before-two-fixed-pushes",
            "future-rehash-and-freeze-exact-backend-and-resident-source",
            "future-publish-write-intent-before-one-backend-invocation",
            "future-consume-attempt-on-any-post-intent-uncertainty",
            "future-require-exact-preimage-write-fsync-readback-result",
            "future-attended-physical-system-boot-without-twrp-hook",
            "future-prove-fresh-resident-android-magisk-health",
            "future-attended-physical-direct-recovery-return",
            "future-prove-fresh-t2-health-and-clean-owned-stage",
            "future-publish-terminal-before-guard-release",
        ],
        "failure_rules": {
            "before_write_intent": "zero boot writes; exact owned stage cleanup only",
            "after_write_intent_without_proved_result": "attempt consumed; never invoke backend again; no System boot; recovery only",
            "proved_readback_but_android_health_absent": "NO_PROOF; direct Recovery return; no backend replay",
            "recovery_uncertain": "retain guard; exact attended Download/Odin boot fallback only if separately activated",
        },
        "activation_blockers": [
            "strict backend stdout/failure parser is not implemented",
            "durable intent-before-effect journal and cut resumption are not implemented",
            "fixed staging and owned cleanup runner are not implemented",
            "physical no-hook System/direct-Recovery choreography owner is not implemented",
            "boot-only Download/Odin fallback is not freshly bound to this Q0 run",
            "target-contract Q0 status is H0 only and not active",
            "execution-critical unit lacks final independent PASS_GO",
            "no fresh attended preparation or exact approval exists",
        ],
        "forbidden": [
            "execute-backend-in-this-unit",
            "adb-or-device-command-in-this-unit",
            "twrp-system-reboot-hook",
            "misc-write",
            "recovery-partition-write",
            "caller-path-or-command",
            "backend-replay",
            "p0-candidate-write",
        ],
    }


def render_plan() -> dict[str, Any]:
    binding = binding_value()
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "active": Q0_ACTIVE,
        "live_authority": False,
        "binding_sha256": digest(binding),
        "approval_prefix_reserved_not_emitted": APPROVAL_PREFIX,
        "binding": binding,
        "device_commands": [],
        "device_writes": [],
        "partition_transfers": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-plan", action="store_true")
    args = parser.parse_args()
    if not args.render_plan:
        parser.error("only --render-plan exists in dormant H0 Q0 owner")
    print(json.dumps(render_plan(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
