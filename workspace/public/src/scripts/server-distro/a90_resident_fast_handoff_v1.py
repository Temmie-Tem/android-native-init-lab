#!/usr/bin/env python3
"""Qualify the exact Debian A/B input for the A90 resident fast-handoff line.

This tool is deliberately H0-only.  It reads and hashes private host artifacts,
emits a private readiness receipt, and never opens a device, starts a bridge,
invokes a transport, or grants live authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
PRIVATE_ROOT = REPO_ROOT / "workspace/private"

AB_SCHEMA = "a90-phase2-display-v1-ab-receipt"
OUTPUT_SCHEMA = "a90-resident-fast-handoff-v1-host-receipt"
EXPECTED_PROFILE = "phase2-display-v1"
EXPECTED_IMAGE_BYTES = 2 * 1024 * 1024 * 1024
EXPECTED_IMAGE_SHA256 = "88152ef1150fc98765eed7c3f196ab9ef8a325d4cc5f74222e45949b089950c2"
EXPECTED_PRESENTER_SHA256 = "35e6a18d50c73ef14b2309124d4dbe7f1cd0607f525afd992e6a6334c55dd583"
EXPECTED_MANIFEST_SHA256 = "fead4c45c42add75331cc93738177902f21aa18ea0f7e0e53098bec7b0d46d09"
EXPECTED_BUILDER_SHA256 = "8b44e922aba9efdf8b6877c98d6d3395c4ec34a6d6d5e47247aa3c73d7b689a1"
EXPECTED_PRESENTER_SOURCE_SHA256 = "98c65eceadaa8a35b35eabdedaa9edca2c37587bd344e021b1dd6be8d4b2e871"

FROZEN_F1 = REPO_ROOT / "workspace/public/src/scripts/server-distro/a90_v3403_f1_orchestrator.py"
FLASH_HELPER = REPO_ROOT / "workspace/public/src/scripts/revalidation/native_init_flash.py"
MODEMMANAGER_GUARD = (
    REPO_ROOT
    / "workspace/public/src/scripts/revalidation/device_action_cdc_acm_observer_v1.py"
)
PROMOTION_MODEL = (
    REPO_ROOT
    / "workspace/public/src/scripts/server-distro/a90_resident_promotion_v1_model.py"
)

DAILY_STATES = (
    "PREFLIGHT",
    "APPROVED",
    "GUARD_ARMED",
    "HANDOFF_STARTED",
    "DEBIAN_OBSERVED",
    "NATIVE_RETURNED",
    "WORK_CLEANED",
    "HEALTH_VERIFIED",
    "CLOSED",
)


class ContractError(RuntimeError):
    """Raised when a host input does not match the exact v1 contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def private_regular(path: Path, label: str) -> Path:
    candidate = path if path.is_absolute() else REPO_ROOT / path
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(PRIVATE_ROOT.resolve(strict=True))
    except (FileNotFoundError, ValueError) as exc:
        raise ContractError(f"{label} must be an existing private path") from exc
    mode = resolved.lstat().st_mode
    if not stat.S_ISREG(mode):
        raise ContractError(f"{label} is not a regular file")
    return resolved


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return value


def load_json(path: Path, label: str) -> tuple[Path, dict[str, Any]]:
    resolved = private_regular(path, label)
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label} is not valid JSON") from exc
    return resolved, require_dict(value, label)


def bound_child(receipt_path: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ContractError(f"{label} must be a relative path")
    lexical = Path(value)
    if ".." in lexical.parts:
        raise ContractError(f"{label} contains parent traversal")
    return private_regular(receipt_path.parent / lexical, label)


def validate_image(
    receipt_path: Path,
    slot: str,
    value: Any,
) -> dict[str, Any]:
    item = require_dict(value, f"{slot}.image")
    path = bound_child(receipt_path, item.get("path"), f"{slot}.image.path")
    expected_size = item.get("bytes")
    expected_sha = item.get("sha256")
    if expected_size != EXPECTED_IMAGE_BYTES:
        raise ContractError(f"{slot} image size contract changed")
    if expected_sha != EXPECTED_IMAGE_SHA256:
        raise ContractError(f"{slot} image receipt SHA256 changed")
    if path.stat().st_size != expected_size:
        raise ContractError(f"{slot} image size does not match its receipt")
    actual_sha = sha256_file(path)
    if actual_sha != expected_sha:
        raise ContractError(f"{slot} image bytes do not match their receipt")
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "bytes": expected_size,
        "sha256": actual_sha,
    }


def validate_slot(receipt_path: Path, slot: str, value: Any) -> dict[str, Any]:
    item = require_dict(value, slot)
    if item.get("e2fsck_read_only_rc") != 0:
        raise ContractError(f"{slot} did not pass read-only e2fsck")
    presenter = require_dict(item.get("presenter"), f"{slot}.presenter")
    if presenter.get("sha256") != EXPECTED_PRESENTER_SHA256:
        raise ContractError(f"{slot} presenter SHA256 changed")
    if not isinstance(presenter.get("bytes"), int) or presenter["bytes"] <= 0:
        raise ContractError(f"{slot} presenter size is invalid")
    overlays = item.get("overlays")
    if not isinstance(overlays, list):
        raise ContractError(f"{slot}.overlays must be a list")
    matches = [
        overlay
        for overlay in overlays
        if isinstance(overlay, dict)
        and overlay.get("target") == "/usr/local/sbin/a90-debian-display-v1"
        and overlay.get("sha256") == EXPECTED_PRESENTER_SHA256
        and overlay.get("mode") == 0o755
        and overlay.get("uid") == 0
        and overlay.get("gid") == 0
    ]
    if len(matches) != 1:
        raise ContractError(f"{slot} lacks one exact presenter overlay")
    return {
        "image": validate_image(receipt_path, slot, item.get("image")),
        "presenter": {
            "bytes": presenter["bytes"],
            "sha256": presenter["sha256"],
            "target": "/usr/local/sbin/a90-debian-display-v1",
        },
        "e2fsck_read_only_pass": True,
    }


def validate_ab_receipt(path: Path) -> dict[str, Any]:
    receipt_path, receipt = load_json(path, "A/B receipt")
    exact_flags = {
        "schema": AB_SCHEMA,
        "profile": EXPECTED_PROFILE,
        "host_only": True,
        "device_action": False,
        "flash": False,
        "candidate_authority": False,
        "image_byte_identical": True,
        "presenter_byte_identical": True,
        "source_unchanged": True,
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
    }
    for key, expected in exact_flags.items():
        if receipt.get(key) != expected:
            raise ContractError(f"A/B receipt {key} does not match v1")
    source_sha = require_dict(receipt.get("source_sha256"), "source_sha256")
    if source_sha.get("builder") != EXPECTED_BUILDER_SHA256:
        raise ContractError("A/B builder source SHA256 changed")
    if source_sha.get("presenter") != EXPECTED_PRESENTER_SOURCE_SHA256:
        raise ContractError("presenter source SHA256 changed")
    base = require_dict(receipt.get("base"), "base")
    if base.get("unchanged") is not True:
        raise ContractError("base image was not preserved")

    slots = {
        slot: validate_slot(receipt_path, slot, receipt.get(slot))
        for slot in ("A", "B")
    }
    if slots["A"]["image"]["sha256"] != slots["B"]["image"]["sha256"]:
        raise ContractError("A/B image bytes diverged")
    return {
        "receipt_path": str(receipt_path.relative_to(REPO_ROOT)),
        "receipt_sha256": sha256_file(receipt_path),
        "profile": receipt["profile"],
        "manifest_sha256": receipt["manifest_sha256"],
        "builder_sha256": source_sha["builder"],
        "presenter_source_sha256": source_sha["presenter"],
        "slots": slots,
        "image_byte_identical": True,
        "presenter_byte_identical": True,
        "source_unchanged": True,
        "base_unchanged": True,
    }


def current_host_closure() -> dict[str, dict[str, Any]]:
    closure: dict[str, dict[str, Any]] = {}
    for label, path in (
        ("frozen_f1_orchestrator", FROZEN_F1),
        ("boot_only_flash_helper", FLASH_HELPER),
        ("modemmanager_guard", MODEMMANAGER_GUARD),
        ("resident_promotion_model", PROMOTION_MODEL),
    ):
        if not path.is_file():
            raise ContractError(f"host closure file missing: {label}")
        closure[label] = {
            "path": str(path.relative_to(REPO_ROOT)),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    return closure


def build_host_receipt(ab_receipt: Path) -> dict[str, Any]:
    return {
        "schema": OUTPUT_SCHEMA,
        "status": "HOST_AB_QUALIFIED_PROMOTION_NOT_AUTHORIZED",
        "host_only": True,
        "device_action": False,
        "flash": False,
        "candidate_authority": False,
        "live_ready": False,
        "debian_ab": validate_ab_receipt(ab_receipt),
        "host_closure": current_host_closure(),
        "roles": {
            "frozen_f1": "one-time-resident-promotion-and-exact-recovery-only",
            "daily_d1": "resident-no-flash-one-handoff-one-return-one-cleanup",
        },
        "daily_d1_state_machine": list(DAILY_STATES),
        "daily_d1_invariants": {
            "exact_a90_target": True,
            "fresh_approval_per_run": True,
            "candidate_or_rollback_flash": False,
            "one_handoff": True,
            "usb_local_ncm_only": True,
            "exact_transient_modemmanager_guard": True,
            "changed_usb_epoch_required": True,
            "exact_returned_native_health_required": True,
            "work_copy_must_start_absent": True,
            "same_run_exact_work_cleanup_required": True,
            "candidate_replay": False,
        },
        "blockers": [
            "resident-promotion-live-runner-not-yet-implemented",
            "exact-resident-promotion-packet-not-yet-prepared",
            "fresh-resident-promotion-authority-not-granted",
            "resident-native-baseline-not-yet-observed",
            "daily-d1-live-runner-not-yet-activated",
        ],
    }


def write_private_exclusive(path: Path, value: dict[str, Any]) -> None:
    candidate = path if path.is_absolute() else REPO_ROOT / path
    resolved_parent = candidate.parent.resolve(strict=True)
    try:
        resolved_parent.relative_to(PRIVATE_ROOT.resolve(strict=True))
    except ValueError as exc:
        raise ContractError("output must stay under workspace/private") from exc
    descriptor = os.open(
        candidate,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise OSError("short write while creating private receipt")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(resolved_parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ab-receipt", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = build_host_receipt(args.ab_receipt)
        if args.output is not None:
            write_private_exclusive(args.output, result)
    except (ContractError, OSError) as exc:
        print(json.dumps({"schema": OUTPUT_SCHEMA, "status": "BLOCKED", "error": str(exc)}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
