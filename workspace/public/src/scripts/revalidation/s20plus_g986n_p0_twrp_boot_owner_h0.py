#!/usr/bin/env python3
"""Dormant H0 owner model for a future S20+ TWRP boot-only P0 trial.

The model binds the already retained T2 recovery, the exact P0 raw boot image,
and the known resident-Magisk rollback.  It deliberately exposes no connected
command: the boot block identity, fixed TWRP sink/readback backend, journal,
target-contract activation, independent review, and fresh attended approval
remain explicit blockers.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import tarfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
SCHEMA = "s20plus_g986n_p0_twrp_boot_owner_h0_v1"
OWNER_ACTIVE = False
STATUS = "H0_DESIGN_PASS_GO_NOT_ACTIVE"

TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "build": "G986NKSS8IYC2",
}

P0_OUTPUT = ROOT / "workspace/private/outputs/s20plus_g986n/p0_pid1_acm_v1"
CANDIDATE_BOOT = P0_OUTPUT / "boot.img"
CANDIDATE_BOOT_SIZE = 67_108_864
CANDIDATE_BOOT_SHA256 = (
    "de889ff6256950b98ad8898f4d646f2229cb41a3d1a42d22af608e72161cbf01"
)
CANDIDATE_MANIFEST = P0_OUTPUT / "manifest.json"
CANDIDATE_MANIFEST_SIZE = 14_574
CANDIDATE_MANIFEST_SHA256 = (
    "2b8dc91ac01ba374e18c80127b588255efb2eb97ce40d9f22a489ee8798caf0a"
)

ROLLBACK_ROOT = (
    ROOT / "workspace/private/outputs/s20plus_g986n/magisk_boot_only_iyc2_v1/candidate"
)
ROLLBACK_BOOT = ROLLBACK_ROOT / "boot.img"
ROLLBACK_BOOT_SIZE = 67_108_864
ROLLBACK_BOOT_SHA256 = (
    "d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc"
)
ROLLBACK_AP = ROLLBACK_ROOT / "AP.tar.md5"
ROLLBACK_AP_SIZE = 25_835_561
ROLLBACK_AP_SHA256 = (
    "1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2"
)
ROLLBACK_MEMBER_SIZE = 25_833_304
ROLLBACK_MEMBER_SHA256 = (
    "2003a3db44c35e0a32b6b485ca0260c7feeab4d9c3031b8cf3ec64f87a8b19b5"
)

T2_TERMINAL = ROOT / (
    "workspace/private/runs/s20plus-g986n-twrp-t2-f2/"
    "run-1788244623738402681/terminal.json"
)
T2_TERMINAL_SIZE = 1_911
T2_TERMINAL_SHA256 = (
    "da24acd3b33c78f4ed41565858e5314bb2c3a1acaf020ac06fb83fd99ab84d05"
)
T2_VERSION = "3.7.1_12-AstroForge_v2"
T2_INCREMENTAL = "eng.codeby.20260803.123008"
T2_MARKER_SHA256 = (
    "19a1a617fd2e97feda6362a2435e3d2bcce600fb37f983dd131e21c5ecf9c246"
)

PUBLIC_CLOSURE = {
    "repository_contract": {
        "path": ROOT / "AGENTS.md",
        "size": 23_923,
        "sha256": "e59b3550ca226156d66bd22eb4a80735b2a88eefd594aa9b85c14e9411427ca4",
    },
    "target_contract": {
        "path": ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md",
        "size": 123_058,
        "sha256": "b9f1d37f54adc76896d5b30226c6c48024eafb0f2995460f160c49f4e6bc6abc",
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
    "p0_init_source": {
        "path": ROOT / "workspace/public/src/native-init/s20plus_p0_pid1_acm_init.c",
        "size": 15_549,
        "sha256": "33fd27b2216a870947ccb88da18d0d6aada76f1de9e5f9f4aab7a17a02d2bdd9",
    },
    "p0_builder": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "build_s20plus_g986n_p0_pid1_acm_h0.py",
        "size": 23_173,
        "sha256": "464878e79347fb82de019ff3297c41c048f75b090f393ca16762beab7d3e46b3",
    },
    "p0_observer": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_g986n_p0_pid1_usb_observer.py",
        "size": 16_366,
        "sha256": "7343a97da5b54fa30922210e1afb00f0c4699985b6636fe5dd9c553f3fcee8fc",
    },
    "p0_build_test": {
        "path": ROOT / "tests/test_s20plus_g986n_p0_pid1_acm_h0.py",
        "size": 13_633,
        "sha256": "34f577a071a9e6a78ddd131fe4d4b2c397ca56b24462e143b42ca2479ed56674",
    },
    "p0_observer_test": {
        "path": ROOT / "tests/test_s20plus_g986n_p0_pid1_usb_observer.py",
        "size": 12_197,
        "sha256": "524e13a601c0be00fd93935f0c3ea3cccac75559c75e47c11e9cd0dbed9ea2e8",
    },
}

AP_MEMBER = "boot.img.lz4"
AP_TRAILER_RE = re.compile(rb"([0-9a-f]{32})  AP\.tar\n")
MAX_PUBLIC_SIZE = 256 * 1024
MAX_BOOT_SIZE = 80 * 1024 * 1024
MAX_AP_SIZE = 32 * 1024 * 1024
APPROVAL_PREFIX = "S20PLUS-G986N-P0-TWRP-BOOT-F1-APPROVE:"


class OwnerDesignError(RuntimeError):
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
                raise OwnerDesignError(f"{label} has a duplicate key")
            result[key] = value
        return result

    def reject_constant(_value: str) -> Any:
        raise OwnerDesignError(f"{label} has a non-finite number")

    try:
        value = json.loads(
            payload,
            object_pairs_hook=pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OwnerDesignError(f"{label} is malformed") from exc
    if type(value) is not dict:
        raise OwnerDesignError(f"{label} root differs")
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
        raise OwnerDesignError(f"{label} is unavailable") from exc
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or type(expected_size) is not int
            or expected_size < 1
            or expected_size > maximum
            or info.st_size != expected_size
        ):
            raise OwnerDesignError(f"{label} identity differs")
        payload = bytearray()
        while len(payload) < expected_size:
            chunk = os.read(descriptor, min(1024 * 1024, expected_size - len(payload)))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) != expected_size or os.read(descriptor, 1):
            raise OwnerDesignError(f"{label} length differs")
    finally:
        os.close(descriptor)
    data = bytes(payload)
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise OwnerDesignError(f"{label} hash differs")
    return data


def receipt(
    path: Path,
    size: int,
    sha256: str,
    label: str,
    *,
    maximum: int = MAX_PUBLIC_SIZE,
) -> dict[str, Any]:
    read_exact_regular(
        path,
        expected_size=size,
        expected_sha256=sha256,
        maximum=maximum,
        label=label,
    )
    return {"path": str(path), "size": size, "sha256": sha256}


def validate_candidate_manifest() -> dict[str, Any]:
    payload = read_exact_regular(
        CANDIDATE_MANIFEST,
        expected_size=CANDIDATE_MANIFEST_SIZE,
        expected_sha256=CANDIDATE_MANIFEST_SHA256,
        maximum=MAX_PUBLIC_SIZE,
        label="P0 candidate manifest",
    )
    value = strict_json(payload, "P0 candidate manifest")
    expected = {
        "schema": "s20plus_g986n_p0_pid1_acm_build_v1",
        "tier": "H0",
        "review_state": "REVIEW_PENDING",
        "live_authority": False,
        "target": {
            "model": "SM-G986N",
            "device": "y2q",
            "product": "y2qksx",
            "incremental": "G986NKSS8IYC2",
        },
    }
    for key, item in expected.items():
        if value.get(key) != item or (
            isinstance(item, bool) and type(value.get(key)) is not bool
        ):
            raise OwnerDesignError(f"P0 candidate manifest {key} differs")
    outputs = value.get("outputs")
    safety = value.get("safety")
    ramdisk = value.get("ramdisk")
    if (
        type(outputs) is not dict
        or outputs.get("boot.img")
        != {"size": CANDIDATE_BOOT_SIZE, "sha256": CANDIDATE_BOOT_SHA256}
        or type(safety) is not dict
        or safety.get("boot_only_output") is not True
        or safety.get("global_pid1_candidate") is not True
        or safety.get("persistent_write") is not False
        or safety.get("block_device_access") is not False
        or safety.get("android_started") is not False
        or safety.get("magisk_started") is not False
        or safety.get("tar_members") != [AP_MEMBER]
        or type(ramdisk) is not dict
        or ramdisk.get("logical_regular_entries_exact") is not True
        or ramdisk.get("replaced_entries") != ["init"]
        or ramdisk.get("added_entries") != []
        or ramdisk.get("removed_entries") != []
    ):
        raise OwnerDesignError("P0 candidate manifest semantics differ")
    return {
        "path": str(CANDIDATE_MANIFEST),
        "size": CANDIDATE_MANIFEST_SIZE,
        "sha256": CANDIDATE_MANIFEST_SHA256,
        "review_state": "REVIEW_PENDING",
        "live_authority": False,
    }


def validate_t2_terminal() -> dict[str, Any]:
    payload = read_exact_regular(
        T2_TERMINAL,
        expected_size=T2_TERMINAL_SIZE,
        expected_sha256=T2_TERMINAL_SHA256,
        maximum=MAX_PUBLIC_SIZE,
        label="T2 retained terminal",
    )
    value = strict_json(payload, "T2 retained terminal")
    observation = value.get("recovery_observation")
    values = observation.get("values") if type(observation) is dict else None
    expected = {
        "schema": "s20plus_g986n_twrp_t2_retained_terminal_v1",
        "version": "s20plus-g986n-twrp-t2-f2-v1",
        "verdict": "PROVED_T2_RECOVERY_RETAINED",
        "candidate_attempts": 1,
        "rollback_attempts": 0,
        "partition_transfer_attempts": 1,
        "candidate_replay_permitted": False,
        "candidate_retained": True,
        "candidate_transfer_proved": True,
        "proved_recovery_partition_transfers": 1,
        "all_other_partition_transfers": 0,
        "a90_commands": 0,
        "s22plus_commands": 0,
        "other_target_commands": 0,
        "candidate_claim": "PROVED",
    }
    for key, item in expected.items():
        actual = value.get(key)
        if actual != item or (
            isinstance(item, bool) and type(actual) is not bool
        ) or (
            isinstance(item, int) and not isinstance(item, bool) and type(actual) is not int
        ):
            raise OwnerDesignError(f"T2 retained terminal {key} differs")
    expected_values = {
        "uid": "0",
        "twrp_version": T2_VERSION,
        "incremental": T2_INCREMENTAL,
        "ro_secure": "0",
        "ro_debuggable": "1",
        "usb_config": "mtp,adb",
        "adbd_state": "running",
        "marker_sha256": T2_MARKER_SHA256,
    }
    if (
        type(observation) is not dict
        or observation.get("claim_verdict") != "PROVED"
        or values != expected_values
    ):
        raise OwnerDesignError("T2 retained recovery observation differs")
    return {
        "path": str(T2_TERMINAL),
        "size": T2_TERMINAL_SIZE,
        "sha256": T2_TERMINAL_SHA256,
        "verdict": "PROVED_T2_RECOVERY_RETAINED",
        "candidate_consumed": True,
        "twrp_version": T2_VERSION,
        "incremental": T2_INCREMENTAL,
        "marker_sha256": T2_MARKER_SHA256,
        "usb_config": "mtp,adb",
    }


def audit_rollback_ap() -> dict[str, Any]:
    payload = read_exact_regular(
        ROLLBACK_AP,
        expected_size=ROLLBACK_AP_SIZE,
        expected_sha256=ROLLBACK_AP_SHA256,
        maximum=MAX_AP_SIZE,
        label="resident rollback AP",
    )
    trailer_size = len(b"0" * 32 + b"  AP.tar\n")
    tar_bytes = payload[:-trailer_size]
    trailer = payload[-trailer_size:]
    match = AP_TRAILER_RE.fullmatch(trailer)
    if match is None or hashlib.md5(tar_bytes).hexdigest().encode() != match.group(1):
        raise OwnerDesignError("resident rollback AP MD5 trailer differs")
    try:
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:") as archive:
            members = archive.getmembers()
            if len(members) != 1:
                raise OwnerDesignError("resident rollback AP member count differs")
            member = members[0]
            if (
                member.name != AP_MEMBER
                or not member.isreg()
                or member.mode != 0o644
                or member.uid != 0
                or member.gid != 0
                or member.mtime != 0
                or member.uname != ""
                or member.gname != ""
                or member.pax_headers
                or member.size != ROLLBACK_MEMBER_SIZE
            ):
                raise OwnerDesignError("resident rollback AP member metadata differs")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise OwnerDesignError("resident rollback AP member is unreadable")
            member_bytes = extracted.read(ROLLBACK_MEMBER_SIZE + 1)
    except (tarfile.TarError, OSError) as exc:
        raise OwnerDesignError("resident rollback AP is invalid") from exc
    if (
        len(member_bytes) != ROLLBACK_MEMBER_SIZE
        or hashlib.sha256(member_bytes).hexdigest() != ROLLBACK_MEMBER_SHA256
    ):
        raise OwnerDesignError("resident rollback AP member differs")
    return {
        "path": str(ROLLBACK_AP),
        "size": ROLLBACK_AP_SIZE,
        "sha256": ROLLBACK_AP_SHA256,
        "member": {
            "name": AP_MEMBER,
            "size": ROLLBACK_MEMBER_SIZE,
            "sha256": ROLLBACK_MEMBER_SHA256,
        },
    }


def validate_closure() -> dict[str, Any]:
    closure: dict[str, Any] = {}
    for name, expected in PUBLIC_CLOSURE.items():
        closure[name] = receipt(
            expected["path"],
            expected["size"],
            expected["sha256"],
            f"P0 {name}",
        )
    closure["candidate_manifest"] = validate_candidate_manifest()
    closure["candidate_boot"] = receipt(
        CANDIDATE_BOOT,
        CANDIDATE_BOOT_SIZE,
        CANDIDATE_BOOT_SHA256,
        "P0 raw candidate boot",
        maximum=MAX_BOOT_SIZE,
    )
    closure["resident_rollback_boot"] = receipt(
        ROLLBACK_BOOT,
        ROLLBACK_BOOT_SIZE,
        ROLLBACK_BOOT_SHA256,
        "resident raw rollback boot",
        maximum=MAX_BOOT_SIZE,
    )
    closure["resident_rollback_ap"] = audit_rollback_ap()
    closure["t2_retained_terminal"] = validate_t2_terminal()
    return closure


def binding_value() -> dict[str, Any]:
    closure = validate_closure()
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "target": dict(TARGET),
        "closure": closure,
        "starting_recovery": {
            "proof": "PROVED_T2_RECOVERY_RETAINED",
            "candidate_consumed": True,
            "new_t2_transfer_permitted": False,
            "exact_revalidation_required_before_future_prepare": True,
            "ui_mount_format_install_backup_restore_terminal_authority": False,
        },
        "prior_transfer_qualification": {
            "required": True,
            "method": "separate resident-over-identical-resident TWRP boot write",
            "exact_readback_required": True,
            "demonstrated_download_odin_recovery_required": True,
            "physical_no_hook_system_and_direct_recovery_required": True,
            "proved": False,
            "part_of_p0_candidate_attempt": False,
        },
        "candidate": {
            "role": "global direct-PID1 ACM P0 canary",
            "boot_size": CANDIDATE_BOOT_SIZE,
            "boot_sha256": CANDIDATE_BOOT_SHA256,
            "first_runtime_syscall": "getpid",
            "accepted_pid": 1,
            "proof_banner_sha256": hashlib.sha256(
                b"S20PLUS_P0_PID1_ACM_V1;pid=00000001;stage=ACM_READY\n"
            ).hexdigest(),
            "attempts": 1,
            "replay_permitted": False,
        },
        "rollback": {
            "role": "known-good resident Magisk boot",
            "boot_size": ROLLBACK_BOOT_SIZE,
            "boot_sha256": ROLLBACK_BOOT_SHA256,
            "twrp_boot_write_attempts": 1,
            "mandatory_after_candidate_intent": True,
            "replay_permitted": False,
            "demonstrated_download_odin_fallback_ap_sha256": ROLLBACK_AP_SHA256,
        },
        "observer": {
            "schema": "s20plus_g986n_p0_pid1_usb_observer_v1",
            "active_in_this_unit": False,
            "arrival_timeout_sec": 180,
            "banner_timeout_sec": 12,
            "same_prepared_physical_topology_required": True,
            "stable_tty_number_required": False,
            "banner_is_pid1_proof_only_not_terminal_health": True,
        },
        "terminal": {
            "physical_return_to_same_t2_recovery_required": True,
            "resident_boot_readback_required": True,
            "t2_root_adb_health_reproved": True,
            "exact_fresh_recovery_boot_id_required": True,
            "candidate_banner_alone_is_not_terminal": True,
            "shared_guard_released_last": True,
        },
    }


def render_plan() -> dict[str, Any]:
    binding = binding_value()
    return {
        "schema": SCHEMA,
        "active": OWNER_ACTIVE,
        "live_authority": False,
        "status": STATUS,
        "binding_sha256": digest(binding),
        "approval_prefix_reserved_not_emitted": APPROVAL_PREFIX,
        "binding": binding,
        "state_machine": [
            "validate-exact-public-and-private-h0-closure",
            "future-fresh-attended-t2-recovery-identity-and-topology-preflight",
            "future-resolve-and-bind-exact-boot-block-identity-read-only",
            "future-stage-exact-candidate-in-twrp-volatile-tmpfs-no-clobber",
            "future-candidate-intent-before-one-fixed-boot-write-and-readback",
            "future-attended-physical-system-boot-without-twrp-system-hook",
            "future-bounded-p0-acm-observation",
            "future-attended-physical-return-to-t2-recovery",
            "future-rollback-intent-before-one-fixed-resident-boot-write-and-readback",
            "future-fresh-t2-recovery-health-and-terminal-before-guard-release",
        ],
        "effect_budget": {
            "candidate_boot_partition_writes": 1,
            "candidate_readbacks": 1,
            "rollback_boot_partition_writes": 1,
            "rollback_readbacks": 1,
            "physical_system_boots_max": 1,
            "physical_recovery_returns_max": 1,
            "candidate_replay": False,
            "rollback_replay": False,
            "recovery_partition_writes": 0,
            "misc_writes": 0,
            "userdata_formats": 0,
            "other_partition_writes": 0,
        },
        "failure_rules": {
            "candidate_pre_write_rejection": "zero candidate writes; close only through reviewed pre-write abort",
            "candidate_write_or_readback_uncertainty": "candidate consumed; no system boot; recovery observation and rollback only",
            "absent_or_malformed_banner": "candidate outcome unproved; rollback remains mandatory",
            "rollback_write_or_readback_uncertainty": "no rollback replay; retain guard and use separately reviewed physical recovery",
            "foreign_or_ambiguous_endpoint": "stop before a partition effect",
        },
        "activation_blockers": [
            {
                "id": "s20plus-p0-exact-boot-identity",
                "hazard": "wrong-block or alias write",
                "scope": "future S20+ TWRP boot-only lane",
                "retire_when": "bounded read-only audit binds direct path, rdev, PARTNAME=boot, and exact size with independent review",
                "review_trigger": "target build, recovery, topology, block map, or audit closure drift",
            },
            {
                "id": "s20plus-p0-fixed-twrp-backend",
                "hazard": "TOCTOU, mixed image, partial write, or cache-served readback",
                "scope": "future staged candidate and resident rollback writes",
                "retire_when": "fixed no-input device-side backend enforces opened-fd identity, exact staged bytes, fsync, and independently guarded readback under hostile tests",
                "review_trigger": "backend, command, staging, artifact, block identity, or toolchain drift",
            },
            {
                "id": "s20plus-p0-identical-write-qualification",
                "hazard": "unproved S20+ TWRP boot-write and readback mechanism",
                "scope": "before the first P0 candidate attempt",
                "retire_when": "a separate reviewed resident-over-identical-resident one-shot proves exact write/readback, no-hook physical System boot, direct Recovery return, and Download/Odin recovery",
                "review_trigger": "recovery kernel, TWRP hook, key choreography, backend, resident boot, block identity, or recovery-path drift",
            },
            {
                "id": "s20plus-p0-durable-journal",
                "hazard": "effect replay or false attribution after a host/device cut",
                "scope": "all future P0 staging, write, boot, observation, and rollback effects",
                "retire_when": "strict typed intent-before-effect journal and cut-resume hostile tests receive independent PASS_GO",
                "review_trigger": "schema, parser, writer, effect ordering, recovery graph, or evidence closure drift",
            },
            {
                "id": "s20plus-p0-contract-activation",
                "hazard": "using retained T2 evidence as unauthorized direct-block authority",
                "scope": "S20+ P0 TWRP boot-only F1 lane only",
                "retire_when": "reviewed target-contract and risk-tier amendment is mechanically activated in one scoped commit",
                "review_trigger": "common contract, target contract, risk tiers, process, or retained-T2 closure drift",
            },
            {
                "id": "s20plus-p0-independent-review",
                "hazard": "unreviewed execution-critical transfer or recovery machinery",
                "scope": "exact backend, journal, observer, owner, tests, artifacts, and policy diff",
                "retire_when": "independent review returns PASS_GO with exact final identities and no unresolved finding",
                "review_trigger": "any execution-critical byte or named hazard changes",
            },
            {
                "id": "s20plus-p0-fresh-run-binding",
                "hazard": "stale target, recovery, artifact, topology, or operator intent",
                "scope": "one future attended P0 candidate run",
                "retire_when": "fresh preparation emits and the attending operator returns the exact short-lived approval",
                "review_trigger": "15-minute expiry, disconnect, reboot, identity drift, guard conflict, or approval consumption",
            },
        ],
        "forbidden_even_after_future_activation": [
            "twrp-rebootsystem-hook",
            "misc-bcb-write",
            "recovery-partition-write",
            "twrp-ui-mount-format-install-backup-restore-terminal",
            "candidate-replay",
            "rollback-replay",
            "other-device-command",
        ],
        "device_commands": [],
        "device_writes": [],
        "partition_transfers": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-plan", action="store_true")
    args = parser.parse_args()
    if not args.render_plan:
        parser.error("only --render-plan exists in the dormant H0 owner")
    print(json.dumps(render_plan(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
