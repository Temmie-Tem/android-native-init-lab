#!/usr/bin/env python3
"""Attended exact-target S20+ resident Magisk boot F1.

Only the fixed reviewed boot-only candidate and stock boot rollback are in
scope.  A candidate intent is one-shot.  Successful resident health keeps the
candidate boot installed; failure permits only the fixed stock rollback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
from typing import Any, Callable

import s20plus_g986n_magisk_bootstrap_f1 as bootstrap


VERSION = "s20plus-g986n-magisk-resident-f1-v1"
RESIDENT_F1_ACTIVE = True
EXPECTED_REVIEWED_NORMALIZED_SHA256 = "d9a47bbc6627fbfc2f57ee18952c5d9524527c23978873ea541e04c7617c8fdc"
ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve()
RUN_ROOT = ROOT / "workspace/private/runs/s20plus-g986n-magisk-resident-f1"
APPROVAL_PREFIX = "S20PLUS-G986N-MAGISK-RESIDENT-F1-DATA-RESET-ACCEPTED:"
PHYSICAL_ROLLBACK_ARM = "S20PLUS-G986N-RESIDENT-PHYSICAL-STOCK-ROLLBACK-ARM"
PHYSICAL_ROLLBACK_CONFIRM = "S20PLUS-G986N-RESIDENT-PHYSICAL-STOCK-ROLLBACK-CONFIRM"
BASE_RUNNER = {
    "path": str(bootstrap.__file__),
    "size": 161_259,
    "sha256": "11ca8aaef183e76c6eeec1a43e75b00bbc14e4b51650e3122c8f4bbdfdc8799f",
    "normalized_sha256": "457c6c9c06a70b431a0c352d7707c1d421bbe89f190667eb2eab608cab49c57e",
}

Command = Callable[[list[str], float, int], tuple[int, bytes, bytes]]
PRE_CANDIDATE_FILES = {
    "initial-download-baseline.json",
    "initial-download-intent.json",
    "initial-download-observation.json",
    "initial-download-result.json",
    "prepared.json",
    "events/00-resident-prepared.json",
}


class ResidentError(RuntimeError):
    pass


def require_active() -> None:
    if not RESIDENT_F1_ACTIVE:
        raise ResidentError("S20+ resident F1 is not active")


def require_exact_run_nodes(run_dir: Path, regular_names: set[str]) -> None:
    expected = {Path(name): "regular" for name in regular_names}
    expected[Path("events")] = "directory"
    actual: dict[Path, str] = {}
    pending = [run_dir]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                relative = path.relative_to(run_dir)
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1:
                    actual[relative] = "regular"
                elif stat.S_ISDIR(metadata.st_mode) and not entry.is_symlink():
                    actual[relative] = "directory"
                    pending.append(path)
                else:
                    actual[relative] = "unexpected"
    if actual != expected:
        raise ResidentError("resident run journal contains missing, extra, or indirect nodes")


def candidate_manifest_files(run_dir: Path, *, pending: bool) -> set[str]:
    result = bootstrap.read_exact_json(run_dir / "candidate-result.json", "resident candidate result")
    files = PRE_CANDIDATE_FILES | {
        "candidate-intent.json",
        "candidate-result.json",
        "candidate-observation.json",
        "events/01-candidate-transfer-started.json",
        "events/02-resident-candidate-transfer-finished.json",
        "events/03-resident-candidate-observation-closed.json",
    }
    if result.get("schema") == "s20plus_g986n_f1_transfer_v1":
        files |= {"candidate.stdout", "candidate.stderr"}
    elif result.get("schema") != "s20plus_g986n_f1_transfer_failure_v1":
        raise ResidentError("resident candidate result has an unknown schema")
    if pending:
        files.add("resident-pending.json")
    return files


def rollback_manifest_files(run_dir: Path, *, recovery_result: bool) -> set[str]:
    result = bootstrap.read_exact_json(run_dir / "rollback-result.json", "resident rollback result")
    files = candidate_manifest_files(run_dir, pending=True) | {
        "resident-rollback-baseline.json",
        "resident-rollback-arm.json",
        "resident-rollback-confirmation.json",
        "rollback-intent.json",
        "rollback-result.json",
        "events/04-rollback-transfer-started.json",
    }
    if result.get("schema") == "s20plus_g986n_f1_transfer_v1":
        files |= {"rollback.stdout", "rollback.stderr"}
    elif result.get("schema") != "s20plus_g986n_f1_transfer_failure_v1":
        raise ResidentError("resident rollback result has an unknown schema")
    if recovery_result:
        files.add("resident-recovery-result.json")
    return files


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def normalized_self_sha256() -> str:
    payload = SCRIPT.read_bytes()
    pattern = rb'EXPECTED_REVIEWED_NORMALIZED_SHA256 = "[0-9a-f]{64}"'
    normalized, count = re.subn(
        pattern,
        b'EXPECTED_REVIEWED_NORMALIZED_SHA256 = "' + b"0" * 64 + b'"',
        payload,
    )
    if count != 1:
        raise ResidentError("resident runner normalized identity is ambiguous")
    return hashlib.sha256(normalized).hexdigest()


def self_receipt() -> dict[str, Any]:
    metadata = SCRIPT.lstat()
    normalized = normalized_self_sha256()
    if (
        SCRIPT.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or normalized != EXPECTED_REVIEWED_NORMALIZED_SHA256
    ):
        raise ResidentError("resident runner does not match its reviewed identity")
    return {
        "path": str(SCRIPT),
        "size": metadata.st_size,
        "sha256": bootstrap.sha256_file(SCRIPT),
        "normalized_sha256": normalized,
    }


def closure_receipts() -> dict[str, Any]:
    base = bootstrap.closure_receipts()
    if base["runner"] != BASE_RUNNER:
        raise ResidentError("bootstrap helper closure changed")
    return {"resident_runner": self_receipt(), "bootstrap": base}


def guard_path() -> Path:
    return bootstrap.guard_path()


def guard_value(run_dir: Path) -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_magisk_resident_guard_v1",
        "version": VERSION,
        "run_dir": str(run_dir),
        "unresolved": True,
    }


def read_guard(run_dir: Path) -> dict[str, Any]:
    value = bootstrap.read_exact_json(guard_path(), "resident shared guard")
    if value != guard_value(run_dir):
        raise ResidentError("resident shared guard does not match this run")
    return value


def release_guard(run_dir: Path) -> None:
    read_guard(run_dir)
    guard_path().unlink()
    bootstrap.fsync_dir(guard_path().parent)


def allocate_run_dir(requested: Path | None) -> Path:
    parent = RUN_ROOT.parent.resolve(strict=True)
    if RUN_ROOT.exists():
        if RUN_ROOT.is_symlink() or RUN_ROOT.resolve(strict=True) != RUN_ROOT.absolute():
            raise ResidentError("resident run root is indirect")
    else:
        if RUN_ROOT.parent.absolute() != parent:
            raise ResidentError("resident run parent is indirect")
        RUN_ROOT.mkdir(mode=0o700)
        bootstrap.fsync_dir(RUN_ROOT.parent)
    target = requested or RUN_ROOT / f"run-{time.time_ns()}"
    target = target if target.is_absolute() else ROOT / target
    if target.parent != RUN_ROOT or target.exists() or target.is_symlink():
        raise ResidentError("resident run directory is not a fresh direct child")
    target.mkdir(mode=0o700)
    bootstrap.fsync_dir(RUN_ROOT)
    return target


def validate_run_dir(run_dir: Path) -> Path:
    if RUN_ROOT.is_symlink() or RUN_ROOT.resolve(strict=True) != RUN_ROOT.absolute():
        raise ResidentError("resident run root is indirect")
    if run_dir.parent != RUN_ROOT or run_dir.is_symlink() or not run_dir.is_dir():
        raise ResidentError("resident run directory is indirect")
    if run_dir.resolve(strict=True) != run_dir.absolute():
        raise ResidentError("resident run directory escaped its root")
    return run_dir


def prepared_binding(
    run_dir: Path,
    artifacts: dict[str, Any],
    transition: dict[str, Any],
    endpoint: dict[str, Any],
    closure: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_magisk_resident_binding_v1",
        "version": VERSION,
        "run_dir": str(run_dir),
        "target": {
            "model": bootstrap.EXPECTED_MODEL,
            "device": bootstrap.EXPECTED_DEVICE,
            "product": bootstrap.EXPECTED_PRODUCT,
            "incremental": bootstrap.EXPECTED_INCREMENTAL,
            "topology_sha256": bootstrap.EXPECTED_TOPOLOGY_SHA256,
        },
        "artifacts": artifacts,
        "transition": transition,
        "endpoint": endpoint,
        "closure": closure,
        "candidate_attempts": 1,
        "rollback_attempts": 1,
        "candidate_replay": False,
        "resident_root_authorized": True,
        "factory_reset_data_loss_accepted": True,
        "rollback_role": "failure-recovery-only",
    }


def prepare(requested: Path | None, command: Command = bootstrap.bounded_command) -> Path:
    require_active()
    if os.path.lexists(guard_path()):
        raise ResidentError("another S20+ action remains unresolved")
    artifacts = bootstrap.validate_artifacts()
    closure = closure_receipts()
    run_dir = allocate_run_dir(requested)
    bootstrap.durable_create(guard_path(), guard_value(run_dir))
    try:
        adb = closure["bootstrap"]["adb"]["path"]
        transition, endpoint = bootstrap.transition_android_to_download(run_dir, command, adb)
        binding = prepared_binding(run_dir, artifacts, transition, endpoint, closure)
        binding_sha = canonical_sha(binding)
        bootstrap.durable_create(run_dir / "prepared.json", {
            "schema": "s20plus_g986n_magisk_resident_prepared_v1",
            "version": VERSION,
            "binding": binding,
            "binding_sha256": binding_sha,
            "approval_token": APPROVAL_PREFIX + binding_sha,
            "prepared_at": bootstrap.utc_now(),
        })
        bootstrap.event(run_dir, 0, "resident-prepared", {"binding_sha256": binding_sha})
        return run_dir
    except Exception:
        if not os.path.lexists(run_dir / "initial-download-intent.json"):
            release_guard(run_dir)
        raise


def read_prepared(run_dir: Path) -> dict[str, Any]:
    run_dir = validate_run_dir(run_dir)
    read_guard(run_dir)
    value = bootstrap.read_exact_json(run_dir / "prepared.json", "resident prepared binding")
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "version", "binding", "binding_sha256", "approval_token", "prepared_at"}
        or value.get("schema") != "s20plus_g986n_magisk_resident_prepared_v1"
        or value.get("version") != VERSION
        or value.get("binding_sha256") != canonical_sha(value.get("binding"))
        or value.get("approval_token") != APPROVAL_PREFIX + value["binding_sha256"]
    ):
        raise ResidentError("resident prepared binding is malformed")
    binding = value["binding"]
    if binding != prepared_binding(
        run_dir,
        bootstrap.validate_artifacts(),
        binding.get("transition", {}),
        binding.get("endpoint", {}),
        closure_receipts(),
    ):
        raise ResidentError("resident prepared binding changed")
    bootstrap.validate_live_transition_binding(run_dir, binding["transition"], binding["endpoint"])
    return value


def validated_candidate_observation(run_dir: Path, prepared: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        candidate = bootstrap.validate_candidate_for_physical_handoff(run_dir, prepared["binding_sha256"])
    except bootstrap.BootstrapError:
        bootstrap.read_transfer_intent(run_dir, "candidate", prepared["binding_sha256"])
        candidate = bootstrap.read_exact_json(run_dir / "candidate-result.json", "resident candidate failure result")
        if (
            not isinstance(candidate, dict)
            or set(candidate) != {"schema", "kind", "classification", "error_class", "possible_partition_effect"}
            or candidate.get("schema") != "s20plus_g986n_f1_transfer_failure_v1"
            or candidate.get("kind") != "candidate"
            or candidate.get("classification") != "odin_device_session_failure_or_unknown"
            or not isinstance(candidate.get("error_class"), str)
            or not candidate.get("error_class")
            or candidate.get("possible_partition_effect") is not True
            or os.path.lexists(run_dir / "candidate.stdout")
            or os.path.lexists(run_dir / "candidate.stderr")
        ):
            raise ResidentError("resident candidate failure evidence is malformed")
    observation = bootstrap.validate_candidate_observation_for_physical_handoff(run_dir, candidate)
    return candidate, observation


def validate_full_transfer_result(run_dir: Path, kind: str, binding_sha256: str) -> dict[str, Any]:
    intent = bootstrap.read_transfer_intent(run_dir, kind, binding_sha256)
    value = bootstrap.read_exact_json(run_dir / f"{kind}-result.json", f"resident {kind} result")
    receipt = value.get("receipt") if isinstance(value, dict) else None
    if not isinstance(receipt, dict):
        raise ResidentError(f"resident {kind} receipt is malformed")
    stdout = bootstrap.read_raw_evidence(
        run_dir / f"{kind}.stdout", receipt.get("stdout_bytes"), value.get("stdout_sha256")
    )
    stderr = bootstrap.read_raw_evidence(
        run_dir / f"{kind}.stderr", receipt.get("stderr_bytes"), value.get("stderr_sha256")
    )
    digest = bootstrap.CANDIDATE_SHA256 if kind == "candidate" else bootstrap.ROLLBACK_SHA256
    path = bootstrap.CANDIDATE if kind == "candidate" else bootstrap.ROLLBACK
    size = bootstrap.CANDIDATE_SIZE if kind == "candidate" else bootstrap.ROLLBACK_SIZE
    post_state = receipt.get("endpoint_post_state")
    post_identity = receipt.get("endpoint_post_identity")
    if (
        set(value) != {"schema", "version", "kind", "binding_sha256", "endpoint", "classification", "receipt", "stdout_sha256", "stderr_sha256"}
        or set(receipt) != {
            "label", "returncode", "command_shape", "regular_path_inputs",
            "anonymous_proc_fd_inputs", "odin", "ap", "endpoint_path_sha256",
            "endpoint_pre_identity", "endpoint_post_identity", "endpoint_post_state",
            "stdout_bytes", "stderr_bytes",
        }
        or value.get("schema") != "s20plus_g986n_f1_transfer_v1"
        or value.get("version") != bootstrap.VERSION
        or value.get("kind") != kind
        or value.get("binding_sha256") != binding_sha256
        or value.get("endpoint") != intent["endpoint"]
        or value.get("classification") != bootstrap.persisted_transfer_classification(receipt, stdout, stderr)
        or value.get("classification") not in {
            "odin_transfer_completed", "odin_device_session_failure_or_unknown", "odin_local_parse_failure"
        }
        or receipt.get("label") != kind
        or not isinstance(receipt.get("returncode"), int)
        or isinstance(receipt.get("returncode"), bool)
        or receipt.get("command_shape") != ["odin4", "--reboot", "-a", "AP.tar.md5", "-d", "USBFS"]
        or receipt.get("regular_path_inputs") is not True
        or receipt.get("anonymous_proc_fd_inputs") is not False
        or receipt.get("ap") != {"path": str(path), "size": size, "sha256": digest}
        or receipt.get("odin") != {
            "path": str(bootstrap.ODIN), "size": bootstrap.ODIN_SIZE, "sha256": bootstrap.ODIN_SHA256
        }
        or receipt.get("endpoint_path_sha256") != hashlib.sha256(intent["endpoint"]["device"].encode()).hexdigest()
        or receipt.get("endpoint_pre_identity") != intent["endpoint"]["identity"]
        or post_state not in {"same", "absent", "changed"}
        or (post_state == "same" and post_identity != intent["endpoint"]["identity"])
        or (post_state == "absent" and post_identity is not None)
        or (
            post_state == "changed"
            and (
                not isinstance(post_identity, list)
                or len(post_identity) != 4
                or any(not isinstance(item, int) or isinstance(item, bool) for item in post_identity)
                or post_identity == intent["endpoint"]["identity"]
            )
        )
    ):
        raise ResidentError(f"resident {kind} transfer evidence is malformed or mismatched")
    return value


def candidate_observation(run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    candidate, observation = validated_candidate_observation(run_dir, prepared)
    if candidate.get("classification") != "odin_transfer_completed":
        raise ResidentError("resident candidate transfer is uncertain; stock recovery only")
    return observation


def validate_resident_pending(run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    pending = bootstrap.read_exact_json(run_dir / "resident-pending.json", "resident pending result")
    common = {
        "schema": "s20plus_g986n_magisk_resident_pending_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
    }
    expected = (
        {
            **common,
            "verdict": "RECOVERY_PENDING_S20PLUS_G986N_RESIDENT_FACTORY_RESET_REQUIRED",
            "factory_reset_data_loss_accepted": True,
        },
        {
            **common,
            "verdict": "RECOVERY_PENDING_S20PLUS_G986N_RESIDENT_CANDIDATE_UNCERTAIN",
        },
    )
    if pending not in expected:
        raise ResidentError("resident pending state is malformed or mismatched")
    return pending


def validate_failed_stock_health(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("healthy") is not False:
        raise ResidentError("resident stock failure health is malformed")
    reason = value.get("reason")
    simple = {
        "android-not-returned",
        "root-absence-output-oversized",
        "root-absence-output-malformed",
    }
    observer = {
        "post-root-probe-identity-uncertain",
        "post-root-probe-identity-drift",
    }
    if reason in simple and set(value) == {"healthy", "reason"}:
        return value
    if reason in observer and set(value) == {"healthy", "root_absent", "reason"} and value.get("root_absent") is None:
        return value
    if reason in {"root-still-present", "root-absence-observer-uncertain"} and set(value) == {
        "healthy", "root_absent", "reason", "root_probe_rc", "root_probe_sha256"
    }:
        if (
            (reason == "root-still-present" and value.get("root_absent") is not False)
            or (reason == "root-absence-observer-uncertain" and value.get("root_absent") is not None)
            or not isinstance(value.get("root_probe_rc"), int)
            or isinstance(value.get("root_probe_rc"), bool)
            or re.fullmatch(r"[0-9a-f]{64}", str(value.get("root_probe_sha256"))) is None
        ):
            raise ResidentError("resident stock failure health is malformed")
        return value
    if set(value) == {
        "healthy", "root_absent", "boot_changed", "boot_id_sha256",
        "confirmed_boot_id_sha256", "root_probe_rc", "root_probe_sha256", "target",
    } and value.get("root_absent") is True and value.get("boot_changed") is False:
        if (
            not isinstance(value.get("root_probe_rc"), int)
            or isinstance(value.get("root_probe_rc"), bool)
            or any(re.fullmatch(r"[0-9a-f]{64}", str(value.get(key))) is None for key in (
                "boot_id_sha256", "confirmed_boot_id_sha256", "root_probe_sha256"
            ))
            or value.get("target") != {
                "model": bootstrap.EXPECTED_MODEL,
                "device": bootstrap.EXPECTED_DEVICE,
                "product": bootstrap.EXPECTED_PRODUCT,
                "incremental": bootstrap.EXPECTED_INCREMENTAL,
            }
        ):
            raise ResidentError("resident stock failure health is malformed")
        return value
    raise ResidentError("resident stock failure health is malformed")


def validate_pending_stock_recovery(run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    value = bootstrap.read_exact_json(run_dir / "resident-recovery-result.json", "resident stock recovery result")
    if (
        not isinstance(value, dict)
        or set(value) != {
            "schema", "version", "binding_sha256", "verdict", "rollback_transfer",
            "final_health", "candidate_replay_permitted", "rollback_replay_permitted",
        }
        or value.get("schema") != "s20plus_g986n_magisk_resident_recovery_v1"
        or value.get("version") != VERSION
        or value.get("binding_sha256") != prepared["binding_sha256"]
        or value.get("verdict") != "RECOVERY_PENDING_S20PLUS_G986N_RESIDENT_STOCK_FACTORY_RESET_REQUIRED"
        or value.get("rollback_transfer") != "odin_transfer_completed"
        or value.get("candidate_replay_permitted") is not False
        or value.get("rollback_replay_permitted") is not False
    ):
        raise ResidentError("resident stock recovery result is malformed or mismatched")
    validate_failed_stock_health(value.get("final_health"))
    return value


def validate_rollback_confirmation(
    run_dir: Path,
    prepared: dict[str, Any],
    expected_endpoint: dict[str, Any],
) -> dict[str, Any]:
    value = bootstrap.read_exact_json(
        run_dir / "resident-rollback-confirmation.json", "resident rollback confirmation"
    )
    endpoint = value.get("endpoint") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or set(value) != {
            "schema", "version", "binding_sha256", "endpoint",
            "operator_confirmed", "no_replay", "at",
        }
        or value.get("schema") != "s20plus_g986n_magisk_resident_rollback_confirmation_v1"
        or value.get("version") != VERSION
        or value.get("binding_sha256") != prepared["binding_sha256"]
        or value.get("operator_confirmed") is not True
        or value.get("no_replay") is not True
        or not isinstance(value.get("at"), str)
        or not value.get("at")
        or endpoint != expected_endpoint
    ):
        raise ResidentError("resident rollback confirmation is malformed or mismatched")
    bootstrap.validate_download_endpoint_record(endpoint, "resident confirmed rollback endpoint")
    return value


def write_resident_success(
    run_dir: Path,
    prepared: dict[str, Any],
    identity: dict[str, str],
    root: dict[str, Any],
    *,
    late_boot_finalization: bool,
) -> dict[str, Any]:
    require_exact_run_nodes(run_dir, candidate_manifest_files(run_dir, pending=late_boot_finalization))
    initial = prepared["binding"]["transition"]["android_identity"]
    if (
        set(identity) != {"serial_sha256", "topology_sha256", "boot_id_sha256"}
        or any(re.fullmatch(r"[0-9a-f]{64}", str(identity.get(key))) is None for key in identity)
        or identity.get("serial_sha256") != initial.get("serial_sha256")
        or identity.get("topology_sha256") != initial.get("topology_sha256")
        or identity.get("boot_id_sha256") == initial.get("boot_id_sha256")
        or root.get("root_verified") is not True
        or not isinstance(root.get("attempts"), int)
        or isinstance(root.get("attempts"), bool)
        or not 1 <= root.get("attempts") <= 30
        or re.fullmatch(r"[0-9a-f]{64}", str(root.get("output_sha256"))) is None
        or set(root) != {"root_verified", "attempts", "output_sha256"}
        or not isinstance(late_boot_finalization, bool)
    ):
        raise ResidentError("resident root health is not exact")
    result = {
        "schema": "s20plus_g986n_magisk_resident_result_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "verdict": "PASS_S20PLUS_G986N_MAGISK_RESIDENT_ROOT_HEALTHY",
        "resident_root": True,
        "late_boot_finalization": late_boot_finalization,
        "android_identity": identity,
        "root_observation": root,
        "candidate_transfer_count": 1,
        "rollback_transfer_count": 0,
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
        "other_target_command_count": 0,
        "s22plus_command_count": 0,
        "a90_command_count": 0,
        "at": bootstrap.utc_now(),
    }
    bootstrap.durable_create(run_dir / "resident-result.json", result)
    release_guard(run_dir)
    return result


def execute(run_dir: Path, approval: str, command: Command = bootstrap.bounded_command) -> dict[str, Any]:
    require_active()
    prepared = read_prepared(run_dir)
    require_exact_run_nodes(run_dir, PRE_CANDIDATE_FILES)
    if approval != prepared["approval_token"]:
        raise ResidentError("resident F1 approval token mismatch")
    if os.path.lexists(run_dir / "candidate-intent.json"):
        raise ResidentError("resident candidate attempt already exists; replay forbidden")
    endpoint = bootstrap.identify_download(command)
    if not bootstrap.endpoint_session_equivalent(endpoint, prepared["binding"]["endpoint"]):
        raise ResidentError("resident Download endpoint changed before candidate")
    classification = bootstrap.transfer_once(run_dir, "candidate", endpoint, 1, prepared["binding_sha256"])
    bootstrap.event(run_dir, 2, "resident-candidate-transfer-finished", {"classification": classification})
    android = bootstrap.wait_android(command, prepared["binding"]["closure"]["bootstrap"]["adb"]["path"], 90) if classification == "odin_transfer_completed" else None
    root = {"root_verified": False, "attempts": 0}
    if android is not None:
        root = bootstrap.root_observation(command, prepared["binding"]["closure"]["bootstrap"]["adb"]["path"], android[2])
    observation = {
        "schema": "s20plus_g986n_f1_candidate_observation_v1",
        "version": bootstrap.VERSION,
        "classification": classification,
        "android_returned": android is not None,
        "boot_id_sha256": android[2]["boot_id_sha256"] if android is not None else None,
        **root,
    }
    bootstrap.durable_create(run_dir / "candidate-observation.json", observation)
    bootstrap.event(run_dir, 3, "resident-candidate-observation-closed", {
        "classification": classification,
        "android_returned": observation["android_returned"],
        "root_verified": observation["root_verified"],
    })
    persisted_candidate, persisted_observation = validated_candidate_observation(run_dir, prepared)
    if persisted_candidate.get("classification") != classification or persisted_observation != observation:
        raise ResidentError("resident candidate journal changed before terminal decision")
    require_exact_run_nodes(run_dir, candidate_manifest_files(run_dir, pending=False))
    if classification != "odin_transfer_completed":
        result = {
            "schema": "s20plus_g986n_magisk_resident_pending_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "verdict": "RECOVERY_PENDING_S20PLUS_G986N_RESIDENT_CANDIDATE_UNCERTAIN",
            "candidate_replay_permitted": False,
            "rollback_replay_permitted": False,
        }
        bootstrap.durable_create(run_dir / "resident-pending.json", result)
        return result
    if android is not None and root.get("root_verified") is True:
        return write_resident_success(run_dir, prepared, android[2], root, late_boot_finalization=False)
    result = {
        "schema": "s20plus_g986n_magisk_resident_pending_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "verdict": "RECOVERY_PENDING_S20PLUS_G986N_RESIDENT_FACTORY_RESET_REQUIRED",
        "factory_reset_data_loss_accepted": True,
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
    }
    bootstrap.durable_create(run_dir / "resident-pending.json", result)
    return result


def finalize_resident(run_dir: Path, command: Command = bootstrap.bounded_command) -> dict[str, Any]:
    require_active()
    prepared = read_prepared(run_dir)
    if os.path.lexists(run_dir / "resident-result.json"):
        raise ResidentError("resident result already exists")
    observation = candidate_observation(run_dir, prepared)
    if observation.get("root_verified") is not False:
        raise ResidentError("resident finalizer requires an unresolved non-root observation")
    pending = validate_resident_pending(run_dir, prepared)
    if pending.get("verdict") != "RECOVERY_PENDING_S20PLUS_G986N_RESIDENT_FACTORY_RESET_REQUIRED":
        raise ResidentError("resident pending state is not finalizable")
    require_exact_run_nodes(run_dir, candidate_manifest_files(run_dir, pending=True))
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    _selected, _values, identity = bootstrap.android_health_once(command, adb)
    root = bootstrap.root_observation(command, adb, identity)
    return write_resident_success(run_dir, prepared, identity, root, late_boot_finalization=True)


def abort_pre_candidate(run_dir: Path, command: Command = bootstrap.bounded_command) -> dict[str, Any]:
    require_active()
    prepared = read_prepared(run_dir)
    require_exact_run_nodes(run_dir, PRE_CANDIDATE_FILES)
    if any(os.path.lexists(run_dir / name) for name in (
        "candidate-intent.json", "candidate-result.json", "candidate.stdout", "candidate.stderr",
        "candidate-observation.json", "rollback-intent.json", "rollback-result.json",
        "rollback.stdout", "rollback.stderr", "resident-pending.json",
        "resident-result.json", "resident-rollback-arm.json", "resident-rollback-confirmation.json",
        "resident-recovery-result.json", "resident-stock-final.json",
    )):
        raise ResidentError("resident pre-candidate abort is no longer eligible")
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    _selected, _values, identity = bootstrap.android_health_once(command, adb)
    initial = prepared["binding"]["transition"]["android_identity"]
    if (
        identity.get("serial_sha256") != initial.get("serial_sha256")
        or identity.get("topology_sha256") != initial.get("topology_sha256")
        or identity.get("boot_id_sha256") == initial.get("boot_id_sha256")
    ):
        raise ResidentError("resident pre-candidate abort lost target or boot continuity")
    root_absence = bootstrap.exact_root_absence_once(command, adb, _selected, identity)
    result = {
        "schema": "s20plus_g986n_magisk_resident_abort_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "verdict": "PASS_S20PLUS_G986N_RESIDENT_PRE_CANDIDATE_ABORTED",
        "candidate_transfer_count": 0,
        "rollback_transfer_count": 0,
        "root_absence": root_absence,
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
        "at": bootstrap.utc_now(),
    }
    bootstrap.durable_create(run_dir / "resident-abort.json", result)
    release_guard(run_dir)
    return result


def physical_stock_rollback(
    run_dir: Path,
    confirmation: str,
    command: Command = bootstrap.bounded_command,
) -> dict[str, Any]:
    require_active()
    prepared = read_prepared(run_dir)
    validated_candidate_observation(run_dir, prepared)
    validate_resident_pending(run_dir, prepared)
    candidate_files = candidate_manifest_files(run_dir, pending=True)
    if os.path.lexists(run_dir / "rollback-intent.json"):
        raise ResidentError("stock rollback attempt already exists; replay forbidden")
    arm_path = run_dir / "resident-rollback-arm.json"
    if not os.path.lexists(arm_path):
        require_exact_run_nodes(run_dir, candidate_files)
        if confirmation != PHYSICAL_ROLLBACK_ARM:
            raise ResidentError("resident physical rollback arm mismatch")
        baseline = bootstrap.download_baseline(command)
        bootstrap.durable_create(run_dir / "resident-rollback-baseline.json", baseline)
        bootstrap.durable_create(arm_path, {
            "schema": "s20plus_g986n_magisk_resident_rollback_arm_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "baseline_sha256": canonical_sha(baseline),
            "confirmation_required": PHYSICAL_ROLLBACK_CONFIRM,
            "no_replay": True,
            "at": bootstrap.utc_now(),
        })
        return {"verdict": "RECOVERY_PENDING_S20PLUS_G986N_RESIDENT_PHYSICAL_DOWNLOAD_CONFIRMATION"}
    if confirmation != PHYSICAL_ROLLBACK_CONFIRM:
        raise ResidentError("resident physical rollback confirmation mismatch")
    arm = bootstrap.read_exact_json(arm_path, "resident rollback arm")
    baseline = bootstrap.validate_download_baseline(bootstrap.read_exact_json(run_dir / "resident-rollback-baseline.json", "resident rollback baseline"))
    if arm != {
        "schema": "s20plus_g986n_magisk_resident_rollback_arm_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "baseline_sha256": canonical_sha(baseline),
        "confirmation_required": PHYSICAL_ROLLBACK_CONFIRM,
        "no_replay": True,
        "at": arm.get("at"),
    } or not isinstance(arm.get("at"), str):
        raise ResidentError("resident rollback arm is malformed")
    require_exact_run_nodes(run_dir, candidate_files | {
        "resident-rollback-baseline.json", "resident-rollback-arm.json"
    })
    endpoint = bootstrap.identify_download(command)
    bootstrap.durable_create(run_dir / "resident-rollback-confirmation.json", {
        "schema": "s20plus_g986n_magisk_resident_rollback_confirmation_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "endpoint": endpoint,
        "operator_confirmed": True,
        "no_replay": True,
        "at": bootstrap.utc_now(),
    })
    validate_rollback_confirmation(run_dir, prepared, endpoint)
    require_exact_run_nodes(run_dir, candidate_files | {
        "resident-rollback-baseline.json", "resident-rollback-arm.json",
        "resident-rollback-confirmation.json",
    })
    classification = bootstrap.transfer_once(run_dir, "rollback", endpoint, 4, prepared["binding_sha256"])
    if classification == "odin_transfer_completed":
        bootstrap.completed_transfer_result(run_dir, "rollback", prepared["binding_sha256"])
    else:
        failure = bootstrap.read_exact_json(run_dir / "rollback-result.json", "resident rollback failure result")
        if failure.get("schema") == "s20plus_g986n_f1_transfer_v1":
            validated_failure = validate_full_transfer_result(run_dir, "rollback", prepared["binding_sha256"])
            if validated_failure.get("classification") != classification:
                raise ResidentError("resident rollback classification changed")
        else:
            bootstrap.read_transfer_intent(run_dir, "rollback", prepared["binding_sha256"])
            if (
                failure != {
                "schema": "s20plus_g986n_f1_transfer_failure_v1",
                "kind": "rollback",
                "classification": "odin_device_session_failure_or_unknown",
                "error_class": failure.get("error_class"),
                "possible_partition_effect": True,
                }
                or not isinstance(failure.get("error_class"), str)
                or not failure.get("error_class")
                or os.path.lexists(run_dir / "rollback.stdout")
                or os.path.lexists(run_dir / "rollback.stderr")
            ):
                raise ResidentError("resident rollback failure evidence is malformed")
    require_exact_run_nodes(run_dir, rollback_manifest_files(run_dir, recovery_result=False))
    if classification != "odin_transfer_completed":
        result = {
            "schema": "s20plus_g986n_magisk_resident_recovery_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "verdict": "RECOVERY_PENDING_S20PLUS_G986N_RESIDENT_STOCK_ROLLBACK_UNCERTAIN",
            "rollback_transfer": classification,
            "final_health": None,
            "candidate_replay_permitted": False,
            "rollback_replay_permitted": False,
        }
        bootstrap.durable_create(run_dir / "resident-recovery-result.json", result)
        return result
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    final = bootstrap.final_stock_health(command, adb)
    result = {
        "schema": "s20plus_g986n_magisk_resident_recovery_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "verdict": "RECOVERED_S20PLUS_G986N_RESIDENT_TO_STOCK_HEALTHY" if final["healthy"] else "RECOVERY_PENDING_S20PLUS_G986N_RESIDENT_STOCK_FACTORY_RESET_REQUIRED",
        "rollback_transfer": classification,
        "final_health": final,
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
    }
    bootstrap.durable_create(run_dir / "resident-recovery-result.json", result)
    if final["healthy"]:
        release_guard(run_dir)
    return result


def finalize_stock(run_dir: Path, command: Command = bootstrap.bounded_command) -> dict[str, Any]:
    require_active()
    prepared = read_prepared(run_dir)
    validated_candidate_observation(run_dir, prepared)
    bootstrap.completed_transfer_result(run_dir, "rollback", prepared["binding_sha256"])
    validate_pending_stock_recovery(run_dir, prepared)
    require_exact_run_nodes(run_dir, rollback_manifest_files(run_dir, recovery_result=True))
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    final = bootstrap.final_stock_health(command, adb)
    if not final["healthy"]:
        raise ResidentError("stock Android is not yet healthy")
    result = {
        "schema": "s20plus_g986n_magisk_resident_stock_final_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "verdict": "RECOVERED_S20PLUS_G986N_RESIDENT_TO_STOCK_HEALTHY",
        "final_health": final,
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
        "at": bootstrap.utc_now(),
    }
    bootstrap.durable_create(run_dir / "resident-stock-final.json", result)
    release_guard(run_dir)
    return result


def render_plan() -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_magisk_resident_plan_v1",
        "version": VERSION,
        "active": RESIDENT_F1_ACTIVE,
        "target": f"{bootstrap.EXPECTED_MODEL}/{bootstrap.EXPECTED_DEVICE}/{bootstrap.EXPECTED_INCREMENTAL}",
        "candidate_sha256": bootstrap.CANDIDATE_SHA256,
        "rollback_sha256": bootstrap.ROLLBACK_SHA256,
        "candidate_attempts": 1,
        "rollback_attempts": 1,
        "resident_root_authorized": True,
        "factory_reset_data_loss_accepted_by_approval": True,
        "candidate_replay": False,
        "non_boot_partitions": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--render-plan", action="store_true")
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--finalize-resident", action="store_true")
    modes.add_argument("--abort-pre-candidate", action="store_true")
    modes.add_argument("--physical-stock-rollback", action="store_true")
    modes.add_argument("--finalize-stock", action="store_true")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--approval")
    parser.add_argument("--confirmation")
    args = parser.parse_args()
    try:
        if args.render_plan:
            print(json.dumps(render_plan(), indent=2, sort_keys=True))
            return 0
        if args.prepare:
            run_dir = prepare(args.run_dir)
            prepared = read_prepared(run_dir)
            print("PASS_S20PLUS_G986N_MAGISK_RESIDENT_PREPARED")
            print(f"run_dir={run_dir}")
            print(f"approval={prepared['approval_token']}")
            return 0
        if args.run_dir is None:
            raise ResidentError("resident run directory is required")
        run_dir = args.run_dir if args.run_dir.is_absolute() else ROOT / args.run_dir
        if args.execute:
            result = execute(run_dir, args.approval or "")
        elif args.finalize_resident:
            result = finalize_resident(run_dir)
        elif args.abort_pre_candidate:
            result = abort_pre_candidate(run_dir)
        elif args.finalize_stock:
            result = finalize_stock(run_dir)
        else:
            result = physical_stock_rollback(run_dir, args.confirmation or "")
        print(result["verdict"])
        return 0
    except Exception:
        print("FAIL_S20PLUS_G986N_MAGISK_RESIDENT_CLOSED")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
