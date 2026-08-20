#!/usr/bin/env python3
"""Host-only binding model for a future attended S20+ N3-U0 boot owner."""

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
SCHEMA = "s20plus_g986n_n3u0_attended_owner_h0_v1"
OWNER_ACTIVE = False
STATUS = "H0_DESIGN_ONLY_PASS_GO_NOT_ACTIVE"

TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "build": "G986NKSS8IYC2",
}

CANDIDATE_AP = (
    ROOT
    / "workspace/private/outputs/s20plus_g986n/"
    "n3u0_acm_overlay_v1/AP.tar.md5"
)
CANDIDATE_AP_SIZE = 26_112_041
CANDIDATE_AP_SHA256 = (
    "3aad497979cfa0f247aef68f50ea792f40127afa037c134eeb0d2e96798ca7af"
)
CANDIDATE_MEMBER_SIZE = 26_103_098
CANDIDATE_MEMBER_SHA256 = (
    "ee57ba63c557bca651fd633f77d6f006585ec0d5b22bb18418a6fade3590809d"
)
CANDIDATE_BOOT_SHA256 = (
    "7024d206453dbd82f04187b7a3ccb6042aef7e2e20ed9660a67b47ecf19206eb"
)

ROLLBACK_AP = (
    ROOT
    / "workspace/private/outputs/s20plus_g986n/"
    "magisk_boot_only_iyc2_v1/candidate/AP.tar.md5"
)
ROLLBACK_AP_SIZE = 25_835_561
ROLLBACK_AP_SHA256 = (
    "1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2"
)
ROLLBACK_MEMBER_SIZE = 25_833_304
ROLLBACK_MEMBER_SHA256 = (
    "2003a3db44c35e0a32b6b485ca0260c7feeab4d9c3031b8cf3ec64f87a8b19b5"
)
ROLLBACK_BOOT_SHA256 = (
    "d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc"
)

PUBLIC_CLOSURE = {
    "witness": {
        "path": ROOT
        / "workspace/public/src/native-init/s20plus_n3u0_acm_witness.c",
        "size": 18_286,
        "sha256": "cb6b71b08575658edc22bb00472ee13eaa8198543ad393ef6e4ad6efb22ef2f1",
    },
    "builder": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "build_s20plus_n3u0_magisk_overlay.py",
        "size": 22_454,
        "sha256": "93af2c760acd7d4f33a992fe68cb0346485aa675490aed6c43b993f1f09dcce2",
    },
    "observer": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_n3u0_usb_observer.py",
        "size": 16_713,
        "sha256": "f1c6af4123684be1122950442472de7803995345e125955322a8fd262b25e44f",
    },
    "transport": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/device_action_f1_v2.py",
        "size": 80_851,
        "sha256": "4e61a7511cc2ed103d1cac4d1afdd2c91d6edc41e30d9bc2832229286d9ee290",
    },
    "combined_review": {
        "path": ROOT
        / "docs/reports/S20PLUS_G986N_N3U0_COMBINED_H0_REVIEW_2026-08-16.md",
        "size": 4_456,
        "sha256": "f8419f86a522dae8f82bbfc46a12c11d1ef11edaaad1444d8730a272634cd520",
    },
}

AP_MEMBER = "boot.img.lz4"
AP_TRAILER_RE = re.compile(rb"([0-9a-f]{32})  AP\.tar\n")
BOOT_ID_RE = re.compile(r"[0-9a-f]{64}")
MAX_AP_SIZE = 32 * 1024 * 1024
APPROVAL_PREFIX = "S20PLUS-G986N-N3U0-ATTENDED-F1-APPROVE:"


class OwnerDesignError(RuntimeError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def validate_boot_attribution(
    *,
    prepared_boot_id_sha256: str,
    candidate_boot_id_sha256: str | None,
    rollback_mode_boot_id_sha256: str | None,
    final_resident_boot_id_sha256: str,
    rollback_transfer_completed: bool,
) -> dict[str, Any]:
    for label, value in (
        ("prepared", prepared_boot_id_sha256),
        ("final_resident", final_resident_boot_id_sha256),
    ):
        if not isinstance(value, str) or BOOT_ID_RE.fullmatch(value) is None:
            raise OwnerDesignError(f"{label} boot ID is required")
    observed = {
        "prepared": prepared_boot_id_sha256,
        "candidate": candidate_boot_id_sha256,
        "rollback_mode": rollback_mode_boot_id_sha256,
        "final_resident": final_resident_boot_id_sha256,
    }
    for label, value in observed.items():
        if value is not None and (
            not isinstance(value, str) or BOOT_ID_RE.fullmatch(value) is None
        ):
            raise OwnerDesignError(f"{label} boot ID is invalid")
    if rollback_transfer_completed is not True:
        raise OwnerDesignError("resident rollback completion is absent")
    durable_ids = [value for value in observed.values() if value is not None]
    if len(durable_ids) != len(set(durable_ids)):
        raise OwnerDesignError("a durable boot ID was reused")
    return {
        "prepared_boot_id_sha256": prepared_boot_id_sha256,
        "candidate_boot_id_sha256": candidate_boot_id_sha256,
        "rollback_mode_boot_id_sha256": rollback_mode_boot_id_sha256,
        "final_resident_boot_id_sha256": final_resident_boot_id_sha256,
        "rollback_transfer_completed": True,
    }


def read_exact_regular(
    path: Path,
    *,
    expected_size: int,
    expected_sha256: str,
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
            or info.st_size != expected_size
            or expected_size < 0
            or expected_size > MAX_AP_SIZE
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


def receipt(path: Path, size: int, sha256: str, label: str) -> dict[str, Any]:
    read_exact_regular(
        path,
        expected_size=size,
        expected_sha256=sha256,
        label=label,
    )
    return {"path": str(path), "size": size, "sha256": sha256}


def audit_boot_only_ap(
    path: Path,
    *,
    expected_size: int,
    expected_sha256: str,
    expected_member_size: int,
    expected_member_sha256: str,
    label: str,
) -> dict[str, Any]:
    payload = read_exact_regular(
        path,
        expected_size=expected_size,
        expected_sha256=expected_sha256,
        label=label,
    )
    trailer_size = len(b"0" * 32 + b"  AP.tar\n")
    if len(payload) <= trailer_size:
        raise OwnerDesignError(f"{label} MD5 trailer is absent")
    tar_bytes = payload[:-trailer_size]
    trailer = payload[-trailer_size:]
    match = AP_TRAILER_RE.fullmatch(trailer)
    if match is None or hashlib.md5(tar_bytes).hexdigest().encode() != match.group(1):
        raise OwnerDesignError(f"{label} MD5 trailer differs")
    try:
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:") as archive:
            members = archive.getmembers()
            if len(members) != 1:
                raise OwnerDesignError(f"{label} member count differs")
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
                or member.size != expected_member_size
            ):
                raise OwnerDesignError(f"{label} member metadata differs")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise OwnerDesignError(f"{label} member is unreadable")
            member_bytes = extracted.read(expected_member_size + 1)
    except (tarfile.TarError, OSError) as exc:
        raise OwnerDesignError(f"{label} TAR is invalid") from exc
    if (
        len(member_bytes) != expected_member_size
        or hashlib.sha256(member_bytes).hexdigest() != expected_member_sha256
    ):
        raise OwnerDesignError(f"{label} boot member differs")
    return {
        "path": str(path),
        "size": expected_size,
        "sha256": expected_sha256,
        "member": {
            "name": AP_MEMBER,
            "size": expected_member_size,
            "sha256": expected_member_sha256,
            "mode": "0644",
            "uid": 0,
            "gid": 0,
            "mtime": 0,
        },
    }


def validate_closure() -> dict[str, Any]:
    closure: dict[str, Any] = {}
    for name, expected in PUBLIC_CLOSURE.items():
        closure[name] = receipt(
            expected["path"],
            expected["size"],
            expected["sha256"],
            f"N3-U0 {name}",
        )
    closure["candidate"] = audit_boot_only_ap(
        CANDIDATE_AP,
        expected_size=CANDIDATE_AP_SIZE,
        expected_sha256=CANDIDATE_AP_SHA256,
        expected_member_size=CANDIDATE_MEMBER_SIZE,
        expected_member_sha256=CANDIDATE_MEMBER_SHA256,
        label="N3-U0 candidate AP",
    )
    closure["rollback"] = audit_boot_only_ap(
        ROLLBACK_AP,
        expected_size=ROLLBACK_AP_SIZE,
        expected_sha256=ROLLBACK_AP_SHA256,
        expected_member_size=ROLLBACK_MEMBER_SIZE,
        expected_member_sha256=ROLLBACK_MEMBER_SHA256,
        label="N3-U0 resident rollback AP",
    )
    return closure


def binding_value() -> dict[str, Any]:
    closure = validate_closure()
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "target": dict(TARGET),
        "closure": closure,
        "candidate": {
            "ap_sha256": CANDIDATE_AP_SHA256,
            "boot_sha256": CANDIDATE_BOOT_SHA256,
            "attempts": 1,
            "replay_permitted": False,
        },
        "rollback": {
            "role": "known-good resident Magisk boot",
            "ap_sha256": ROLLBACK_AP_SHA256,
            "boot_sha256": ROLLBACK_BOOT_SHA256,
            "attempts": 1,
            "mandatory_after_candidate_intent": True,
            "replay_permitted": False,
        },
        "boot_attribution": {
            "fresh_approval_binds_prepared_boot_id": True,
            "candidate_android_boot_id_recorded_when_observed": True,
            "rollback_mode_boot_id_recorded_when_observed": True,
            "final_resident_boot_observed_after_rollback_completion": True,
            "all_durable_boot_ids_pairwise_distinct": True,
        },
        "observer": {
            "schema": "s20plus_g986n_n3u0_usb_observer_v1",
            "active_in_this_unit": False,
            "arrival_timeout_sec": 180,
            "banner_timeout_sec": 12,
            "expected_banner_sha256": hashlib.sha256(
                b"S20PLUS_N3U0_ACM_V1\n"
            ).hexdigest(),
            "same_prepared_physical_topology_required": True,
            "stable_tty_number_required": False,
        },
        "terminal": {
            "candidate_banner_is_not_terminal": True,
            "resident_rollback_completed": True,
            "final_boot_id_changed_after_rollback": True,
            "final_boot_id_reuses_no_prior_durable_boot": True,
            "exact_target_android_healthy": True,
            "resident_magisk_root_proved": True,
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
            "exact-rooted-android-preflight-and-prepared-boot-binding",
            "empty-download-baseline",
            "download-transition-intent-before-one-reboot",
            "exact-download-arrival",
            "candidate-intent-before-one-boot-transfer",
            "candidate-transfer-consumed-no-replay",
            "bounded-n3u0-usb-or-distinct-candidate-android-observation",
            "automated-or-attended-physical-rollback-handoff",
            "rollback-intent-before-one-resident-boot-transfer",
            "rollback-transfer-consumed-no-replay",
            "post-rollback-distinct-resident-boot-attribution-and-rooted-health",
            "terminal-before-shared-guard-release",
        ],
        "effect_budget": {
            "candidate_download_reboots": 1,
            "candidate_boot_transfers": 1,
            "rollback_mode_reboots_max": 1,
            "attended_physical_rollback_entries_max": 1,
            "rollback_boot_transfers": 1,
            "candidate_replay": False,
            "rollback_replay": False,
        },
        "failure_rules": {
            "absent_or_malformed_banner": "candidate-outcome-unproved; rollback still mandatory",
            "candidate_result_missing_or_uncertain": "candidate consumed; observation/recovery only",
            "rollback_mode_result_missing_or_uncertain": "no reboot replay; attended recovery only",
            "rollback_result_missing_or_uncertain": "no Odin replay; retain guard",
            "foreign_or_ambiguous_endpoint": "stop without transfer",
        },
        "device_commands": [],
        "device_writes": [],
        "partition_transfers": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-plan", action="store_true")
    args = parser.parse_args()
    if not args.render_plan:
        parser.error("only --render-plan exists in the H0 design owner")
    print(json.dumps(render_plan(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
