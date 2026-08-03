#!/usr/bin/env python3
"""One-ordinal unattended A90 resident switch-root transaction runner.

Manifest construction and inspection are H0.  Live execution performs one
fresh exact-target D0 followed by at most one already-qualified, no-payload
``SWITCHROOT_EXPERIMENT`` dispatch.  It has no operator-attendance flag, no
approval token, no session window, no campaign loop, and no replay path.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_transition_d1_session_v1 as attended  # noqa: E402
import a90_transition_engine_v2 as engine  # noqa: E402
from a90_transition_contract_v2 import SessionAction, SessionPreflight  # noqa: E402


SCHEMA = "a90_unattended_resident_d1_manifest_v1"
STATUS = "ready-for-reviewed-unattended-resident-d1"
WORKFLOW = "A90_UNATTENDED_RESIDENT_D1_V1"
RISK_TIER = "TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL"
REVIEW_SCHEMA = "a90_unattended_resident_d1_independent_review_v1"
REVIEW_STATUS = "PASS_GO"
REVIEW_RECEIPT_PATH = (
    REPO_ROOT
    / "docs/reports/A90_UNATTENDED_RESIDENT_D1_RUNNER_INDEPENDENT_REVIEW_2026-08-03.json"
).resolve()
QUALIFICATION_SCHEMA = "a90_unattended_resident_d1_qualification_v1"
JOURNAL_SCHEMA = "a90_unattended_resident_d1_journal_v1"
RESULT_SCHEMA = "a90_unattended_resident_d1_result_v1"
RUN_ID_RE = re.compile(r"^a90-d1-unattended-[0-9]{8}-[0-9]{2}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
TRANSACTION_DIR_NAME = "d1-unattended"
LOCK_NAME = "d1-unattended.lock"
PRIVATE_ROOT = (REPO_ROOT / "workspace/private").resolve()
PRIVATE_RUN_BASE = (PRIVATE_ROOT / "runs/server-distro").resolve()

SOURCE_PATHS = {
    "runner": Path(__file__).resolve(),
    "attended_transaction": SCRIPT_DIR / "a90_transition_d1_session_v1.py",
    "transition_contract": REVAL_DIR / "a90_transition_contract_v2.py",
    "transition_engine": SCRIPT_DIR / "a90_transition_engine_v2.py",
    "common_contract": REPO_ROOT / "AGENTS.md",
    "target_contract": REPO_ROOT
    / "docs/operations/targets/A90_TARGET_CONTRACT.md",
    "policy_review": REPO_ROOT
    / "docs/reports/A90_UNATTENDED_RESIDENT_D1_POLICY_H0_2026-08-03.md",
}
ATTENDED_SOURCE_ROLE_MAP = {
    "runner": "attended_transaction",
    "transition_contract": "transition_contract",
    "transition_engine": "transition_engine",
    **{
        role: f"attended_{role}"
        for role in attended.SOURCE_PATHS
        if role not in {"runner", "transition_contract", "transition_engine"}
    },
}
if set(ATTENDED_SOURCE_ROLE_MAP) != set(attended.SOURCE_PATHS):
    raise RuntimeError("attended transitive source role map is incomplete")
for _attended_role, _capability_role in ATTENDED_SOURCE_ROLE_MAP.items():
    _attended_path = attended.SOURCE_PATHS[_attended_role]
    _existing_path = SOURCE_PATHS.get(_capability_role)
    if _existing_path is not None and _existing_path != _attended_path:
        raise RuntimeError("attended capability source path differs")
    SOURCE_PATHS[_capability_role] = _attended_path


class ContractError(RuntimeError):
    """Raised before widening or replaying an unattended A90 D1 effect."""


@dataclass(frozen=True)
class Qualification:
    transaction_dir: Path
    evidence: dict[str, attended.BoundFile]
    binding_sha256: str


@dataclass(frozen=True)
class UnattendedBinding:
    run_id: str
    workflow: str
    manifest_sha256: str
    resident_boot_sha256: str
    rollback_boot_sha256: str
    rootfs_sha256: str
    observer_sha256: str
    qualification_sha256: str

    def validate(self) -> None:
        if RUN_ID_RE.fullmatch(self.run_id) is None or self.workflow != WORKFLOW:
            raise ContractError("unattended D1 binding identity is not exact")
        for value in (
            self.manifest_sha256,
            self.resident_boot_sha256,
            self.rollback_boot_sha256,
            self.rootfs_sha256,
            self.observer_sha256,
            self.qualification_sha256,
        ):
            if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
                raise ContractError("unattended D1 binding SHA256 is not exact")


@dataclass(frozen=True)
class UnattendedSpec:
    manifest_path: Path
    manifest_sha256: str
    run_id: str
    base_manifest: attended.BoundFile
    base: attended.SessionSpec
    qualification: Qualification
    review_receipt: attended.BoundFile
    source_closure: dict[str, attended.BoundFile]
    transaction_dir: Path
    lock_path: Path

    @property
    def binding(self) -> UnattendedBinding:
        value = UnattendedBinding(
            run_id=self.run_id,
            workflow=WORKFLOW,
            manifest_sha256=self.manifest_sha256,
            resident_boot_sha256=self.base.candidate.sha256,
            rollback_boot_sha256=self.base.rollback.sha256,
            rootfs_sha256=self.base.rootfs.sha256,
            observer_sha256=self.base.source_closure[
                "observation_pipeline"
            ].sha256,
            qualification_sha256=self.qualification.binding_sha256,
        )
        value.validate()
        return value


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _require_private_regular(path: Path) -> os.stat_result:
    try:
        resolved = path.resolve(strict=True)
        info = path.lstat()
    except OSError as exc:
        raise ContractError(f"private file is unavailable: {path}") from exc
    if (
        not resolved.is_relative_to(PRIVATE_ROOT)
        or not stat.S_ISREG(info.st_mode)
        or path.is_symlink()
        or info.st_nlink != 1
        or stat.S_IMODE(info.st_mode) != 0o600
    ):
        raise ContractError(f"private file identity is not exact: {path}")
    return info


def _bound_file(path: Path, *, private: bool) -> attended.BoundFile:
    if not path.is_absolute():
        path = (Path.cwd() / path).absolute()
    if private:
        info = _require_private_regular(path)
    else:
        try:
            info = path.lstat()
        except OSError as exc:
            raise ContractError(f"source file is unavailable: {path}") from exc
        if not stat.S_ISREG(info.st_mode) or path.is_symlink():
            raise ContractError(f"source is not a regular file: {path}")
    return attended.BoundFile(
        path.resolve(strict=True),
        info.st_size,
        sha256_file(path),
    )


def _bound_dict(value: Any, label: str, *, private: bool) -> attended.BoundFile:
    if not isinstance(value, dict) or set(value) != {"path", "size", "sha256"}:
        raise ContractError(f"{label} binding is not exact")
    path = value.get("path")
    size = value.get("size")
    digest = value.get("sha256")
    if (
        not isinstance(path, str)
        or not path
        or type(size) is not int
        or size <= 0
        or not isinstance(digest, str)
        or HEX64_RE.fullmatch(digest) is None
    ):
        raise ContractError(f"{label} binding value is not exact")
    actual = _bound_file(Path(path), private=private)
    if actual.size != size or actual.sha256 != digest:
        raise ContractError(f"{label} changed")
    return actual


def _as_dict(value: attended.BoundFile) -> dict[str, Any]:
    return {"path": str(value.path), "size": value.size, "sha256": value.sha256}


def _read_private_json(path: Path) -> dict[str, Any]:
    _require_private_regular(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"private JSON is invalid: {path}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"private JSON is not an object: {path}")
    return value


def _read_public_json(path: Path) -> dict[str, Any]:
    _bound_file(path, private=False)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"review JSON is invalid: {path}") from exc
    if not isinstance(value, dict):
        raise ContractError("review JSON is not an object")
    return value


def _source_closure() -> dict[str, attended.BoundFile]:
    return {
        role: _bound_file(path, private=False)
        for role, path in SOURCE_PATHS.items()
    }


def _validate_attended_base_source_closure(
    base: attended.SessionSpec,
    capability_sources: dict[str, attended.BoundFile],
) -> None:
    if set(base.source_closure) != set(ATTENDED_SOURCE_ROLE_MAP):
        raise ContractError("base attended source role set differs")
    for attended_role, capability_role in ATTENDED_SOURCE_ROLE_MAP.items():
        actual = base.source_closure.get(attended_role)
        expected = capability_sources.get(capability_role)
        if actual != expected:
            raise ContractError(
                "base attended source closure differs: " + attended_role
            )


def _qualification_value(value: Qualification) -> dict[str, Any]:
    return {
        "schema": QUALIFICATION_SCHEMA,
        "transaction_dir": str(value.transaction_dir),
        "binding_sha256": value.binding_sha256,
        "automatic_native_return_proved": True,
        "debian_pid1_proved": True,
        "dropbear_ssh_proved": True,
        "display_mechanical_proved": True,
        "operator_visibility_proved": True,
        "resident_healthy_proved": True,
        "handoff_dispatch_count": 1,
        "payload_transfer": False,
        "partition_write": False,
        "flash": False,
        "action_replay": False,
        "evidence": {
            role: _as_dict(item)
            for role, item in sorted(value.evidence.items())
        },
    }


def _validate_qualification(
    base_spec: attended.SessionSpec,
    transaction_dir: Path,
) -> Qualification:
    transaction_dir = transaction_dir.resolve(strict=True)
    if transaction_dir.name != attended.SESSION_DIR_NAME:
        raise ContractError("qualification transaction directory is not exact")
    old_manifest_path = transaction_dir.parent / "manifest.json"
    paths = {
        "manifest": old_manifest_path,
        "handoff_intent": transaction_dir / "action-001/handoff-intent.json",
        "observation": transaction_dir / "action-001/observation.json",
        "action_result": transaction_dir / "action-001/result.json",
        "engine_outcome": transaction_dir / "action-001/engine-outcome.json",
        "journal_result": transaction_dir
        / "journal/0002-action-001-result.json",
        "operator_visibility": transaction_dir
        / "action-001/operator-display-observation.json",
    }
    evidence = {
        role: _bound_file(path, private=True) for role, path in paths.items()
    }
    old_manifest = _read_private_json(paths["manifest"])
    resident = old_manifest.get("resident")
    target = old_manifest.get("target")
    candidate = resident.get("candidate") if isinstance(resident, dict) else None
    rollback = resident.get("rollback") if isinstance(resident, dict) else None
    rootfs = resident.get("rootfs") if isinstance(resident, dict) else None
    if (
        old_manifest.get("schema") != attended.SCHEMA
        or not isinstance(resident, dict)
        or not isinstance(target, dict)
        or not isinstance(candidate, dict)
        or candidate.get("sha256") != base_spec.candidate.sha256
        or not isinstance(rollback, dict)
        or rollback.get("sha256") != base_spec.rollback.sha256
        or not isinstance(rootfs, dict)
        or rootfs.get("sha256") != base_spec.rootfs.sha256
        or target.get("profile") != attended.staging.TARGET_PROFILE
    ):
        raise ContractError("qualification resident binding differs")

    intent = _read_private_json(paths["handoff_intent"])
    observation = _read_private_json(paths["observation"])
    result = _read_private_json(paths["action_result"])
    outcome = _read_private_json(paths["engine_outcome"])
    journal = _read_private_json(paths["journal_result"])
    visible = _read_private_json(paths["operator_visibility"])
    if (
        intent.get("schema") != attended.RESULT_SCHEMA
        or intent.get("ordinal") != 1
        or intent.get("handoff_dispatch_count_max") != 1
        or intent.get("journal_fsync_completed_before_dispatch") is not True
        or result.get("schema") != attended.RESULT_SCHEMA
        or result.get("ordinal") != 1
        or result.get("handoff_dispatch_count") != 1
        or result.get("resident_healthy") is not True
        or result.get("observation") != observation
        or any(
            result.get(key) is not False
            for key in ("payload_transfer", "partition_write", "flash")
        )
        or observation.get("native_release_proven") is not True
        or observation.get("debian_pid1_proven") is not True
        or observation.get("dropbear_proven") is not True
        or observation.get("display_mechanical_proof") is not True
        or observation.get("bounded_display_failure") is not False
        or not isinstance(observation.get("ssh"), dict)
        or observation["ssh"].get("proof") is not True
    ):
        raise ContractError("qualification switch-root proof is not exact")
    returned, errors = attended._classify_return_observation(
        attended._f1_spec(base_spec),
        observation,
    )
    if returned is not True or set(errors) - {"retained_pmsg"}:
        raise ContractError("qualification automatic native return is not exact")
    cleanup = result.get("cleanup")
    final_health = result.get("final_health")
    final_source = result.get("final_source")
    selftest = (
        final_health.get("selftest")
        if isinstance(final_health, dict)
        else None
    )
    version = (
        final_health.get("version")
        if isinstance(final_health, dict)
        else None
    )
    if (
        not isinstance(cleanup, dict)
        or cleanup.get("rc") != 0
        or "A90D1_WORK_CLEANUP exact=1 work_absent=1"
        not in str(cleanup.get("text") or "")
        or not isinstance(final_health, dict)
        or final_health.get("exact_bridge") is not True
        or final_health.get("selected_realpath") != base_spec.bridge_realpath
        or not isinstance(selftest, dict)
        or "fail=0" not in str(selftest.get("text") or "")
        or not isinstance(version, dict)
        or base_spec.candidate_version
        not in str(version.get("text") or "")
        or base_spec.candidate_build
        not in str(version.get("text") or "")
        or not isinstance(final_source, dict)
        or final_source.get("rc") != 0
        or "A90F1_SOURCE_PRECHECK exact=1 work_absent=1"
        not in str(final_source.get("text") or "")
    ):
        raise ContractError("qualification final resident health is not exact")
    compact_outcome = {
        "ordinal": outcome.get("ordinal"),
        "action": outcome.get("action"),
        "status": outcome.get("status"),
        "failure_class": outcome.get("failure_class"),
    }
    bound_outcome = journal.get("outcome_evidence")
    snapshot = journal.get("snapshot")
    if (
        outcome.get("schema") != attended.OUTCOME_SCHEMA
        or outcome.get("ordinal") != 1
        or outcome.get("action") != SessionAction.SWITCHROOT_EXPERIMENT.value
        or outcome.get("action_started") is not True
        or journal.get("schema") != attended.JOURNAL_SCHEMA
        or journal.get("sequence") != 2
        or journal.get("action") != "action-001-result"
        or journal.get("manifest_sha256") != evidence["manifest"].sha256
        or journal.get("outcome") != compact_outcome
        or not isinstance(bound_outcome, dict)
        or bound_outcome.get("path") != str(evidence["engine_outcome"].path)
        or bound_outcome.get("size") != evidence["engine_outcome"].size
        or bound_outcome.get("sha256") != evidence["engine_outcome"].sha256
        or not isinstance(snapshot, dict)
        or snapshot.get("device_safety_state") != "RESIDENT_HEALTHY"
    ):
        raise ContractError("qualification durable result binding is not exact")
    if (
        visible.get("schema") != "a90_operator_display_observation_v1"
        or visible.get("ordinal") != 1
        or visible.get("action") != SessionAction.SWITCHROOT_EXPERIMENT.value
        or visible.get("source") != "attended-operator-chat"
        or visible.get("display_visible") is not True
        or visible.get("display_owner_text_observed") != "DISPLAY OWNER DEBIAN"
        or visible.get("handoff_intent_sha256")
        != evidence["handoff_intent"].sha256
        or visible.get("observation_sha256") != evidence["observation"].sha256
    ):
        raise ContractError("qualification operator visibility is not exact")

    binding_value = {
        "workflow": WORKFLOW,
        "qualified_action": SessionAction.SWITCHROOT_EXPERIMENT.value,
        "resident_boot_sha256": base_spec.candidate.sha256,
        "rollback_boot_sha256": base_spec.rollback.sha256,
        "rootfs_sha256": base_spec.rootfs.sha256,
        "evidence_sha256": {
            role: item.sha256 for role, item in sorted(evidence.items())
        },
        "automatic_native_return_proved": True,
        "resident_healthy_proved": True,
        "handoff_dispatch_count": 1,
        "action_replay": False,
    }
    return Qualification(
        transaction_dir=transaction_dir,
        evidence=evidence,
        binding_sha256=json_sha256(binding_value),
    )


def _validate_review_receipt(
    path: Path,
    source_closure: dict[str, attended.BoundFile],
) -> attended.BoundFile:
    receipt = _bound_file(path, private=False)
    if receipt.path != REVIEW_RECEIPT_PATH:
        raise ContractError("unattended D1 review receipt path is not canonical")
    value = _read_public_json(receipt.path)
    expected_sources = {
        role: _as_dict(item) for role, item in sorted(source_closure.items())
    }
    if (
        set(value)
        != {
            "schema",
            "status",
            "reviewed_source_closure",
            "independent_review_completed",
            "unresolved_findings",
            "permanent_boundaries_unchanged",
            "device_contact",
        }
        or value.get("schema") != REVIEW_SCHEMA
        or value.get("status") != REVIEW_STATUS
        or value.get("reviewed_source_closure") != expected_sources
        or value.get("independent_review_completed") is not True
        or value.get("unresolved_findings") != []
        or value.get("permanent_boundaries_unchanged") is not True
        or value.get("device_contact") is not False
    ):
        raise ContractError("unattended D1 independent review is not exact")
    return receipt


def build_manifest(
    *,
    base_manifest_path: Path,
    base_manifest_sha256: str,
    qualification_transaction_dir: Path,
    review_receipt_path: Path,
    run_id: str,
) -> dict[str, Any]:
    if RUN_ID_RE.fullmatch(run_id) is None:
        raise ContractError("unattended D1 run_id is not exact")
    base_manifest = _bound_file(base_manifest_path, private=True)
    if base_manifest.sha256 != base_manifest_sha256:
        raise ContractError("base attended manifest SHA256 mismatch")
    try:
        base = attended.load_spec(base_manifest.path, base_manifest.sha256)
    except attended.ContractError as exc:
        raise ContractError("base attended manifest is not current") from exc
    sources = _source_closure()
    _validate_attended_base_source_closure(base, sources)
    qualification = _validate_qualification(base, qualification_transaction_dir)
    review = _validate_review_receipt(review_receipt_path, sources)
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "created_utc": utc_now(),
        "run_id": run_id,
        "workflow": WORKFLOW,
        "risk_tier": RISK_TIER,
        "target_profile": attended.staging.TARGET_PROFILE,
        "base_attended_manifest": _as_dict(base_manifest),
        "qualification": _qualification_value(qualification),
        "review_receipt": _as_dict(review),
        "source_closure": {
            role: _as_dict(item) for role, item in sorted(sources.items())
        },
        "action": {
            "ordinal": 1,
            "allowlist": [SessionAction.SWITCHROOT_EXPERIMENT.value],
            "fresh_exact_d0_before_dispatch": True,
            "expected_terminal": "AUTOMATIC_NATIVE_RETURN",
            "operator_visible_confirmation": "unavailable",
            "one_durable_intent": True,
            "handoff_dispatch_count_max": 1,
            "automatic_replay": False,
        },
        "transaction": {
            "directory": str(
                PRIVATE_RUN_BASE / run_id / TRANSACTION_DIR_NAME
            ),
            "lock_path": str(PRIVATE_RUN_BASE / run_id / LOCK_NAME),
        },
        "safety": {
            "payload_transfer": False,
            "partition_write": False,
            "flash": False,
            "persistent_setting": False,
            "credential_or_security_change": False,
            "package_or_immutable_rootfs_change": False,
            "transient_bound_work_copy": True,
            "exact_work_cleanup_required": True,
            "recovery_mutation": False,
            "other_targets_untouched": True,
        },
        "authority": {
            "manifest_grants_live_authority": False,
            "operator_approval_required": False,
            "operator_attendance_required": False,
            "active_contract_presence_mode_required": WORKFLOW,
            "fresh_d0_required": True,
            "one_ordinal_only": True,
        },
    }


def load_spec(path: Path, expected_sha256: str) -> UnattendedSpec:
    manifest = _bound_file(path, private=True)
    if manifest.sha256 != expected_sha256:
        raise ContractError("unattended D1 manifest SHA256 mismatch")
    value = _read_private_json(manifest.path)
    expected_keys = {
        "schema",
        "status",
        "created_utc",
        "run_id",
        "workflow",
        "risk_tier",
        "target_profile",
        "base_attended_manifest",
        "qualification",
        "review_receipt",
        "source_closure",
        "action",
        "transaction",
        "safety",
        "authority",
    }
    run_id = value.get("run_id")
    if (
        set(value) != expected_keys
        or value.get("schema") != SCHEMA
        or value.get("status") != STATUS
        or not isinstance(run_id, str)
        or RUN_ID_RE.fullmatch(run_id) is None
        or manifest.path.parent != PRIVATE_RUN_BASE / run_id
        or value.get("workflow") != WORKFLOW
        or value.get("risk_tier") != RISK_TIER
        or value.get("target_profile") != attended.staging.TARGET_PROFILE
    ):
        raise ContractError("unattended D1 manifest identity is not exact")
    base_manifest = _bound_dict(
        value.get("base_attended_manifest"),
        "base attended manifest",
        private=True,
    )
    try:
        base = attended.load_spec(base_manifest.path, base_manifest.sha256)
    except attended.ContractError as exc:
        raise ContractError("base attended manifest is not current") from exc
    sources_raw = value.get("source_closure")
    if not isinstance(sources_raw, dict) or set(sources_raw) != set(SOURCE_PATHS):
        raise ContractError("unattended D1 source closure is not exact")
    sources: dict[str, attended.BoundFile] = {}
    for role, expected_path in SOURCE_PATHS.items():
        item = _bound_dict(sources_raw.get(role), role, private=False)
        if item.path != expected_path.resolve(strict=True):
            raise ContractError(f"unattended D1 source path changed: {role}")
        sources[role] = item
    _validate_attended_base_source_closure(base, sources)
    qualification_value = value.get("qualification")
    if not isinstance(qualification_value, dict):
        raise ContractError("unattended D1 qualification is absent")
    transaction_raw = qualification_value.get("transaction_dir")
    if not isinstance(transaction_raw, str) or not transaction_raw:
        raise ContractError("qualification transaction path is absent")
    qualification = _validate_qualification(base, Path(transaction_raw))
    if qualification_value != _qualification_value(qualification):
        raise ContractError("unattended D1 qualification binding changed")
    review = _bound_dict(
        value.get("review_receipt"),
        "review receipt",
        private=False,
    )
    if review != _validate_review_receipt(review.path, sources):
        raise ContractError("unattended D1 review receipt changed")
    action = value.get("action")
    transaction = value.get("transaction")
    safety = value.get("safety")
    authority = value.get("authority")
    expected_transaction = PRIVATE_RUN_BASE / run_id / TRANSACTION_DIR_NAME
    expected_lock = PRIVATE_RUN_BASE / run_id / LOCK_NAME
    if (
        action
        != {
            "ordinal": 1,
            "allowlist": [SessionAction.SWITCHROOT_EXPERIMENT.value],
            "fresh_exact_d0_before_dispatch": True,
            "expected_terminal": "AUTOMATIC_NATIVE_RETURN",
            "operator_visible_confirmation": "unavailable",
            "one_durable_intent": True,
            "handoff_dispatch_count_max": 1,
            "automatic_replay": False,
        }
        or transaction
        != {"directory": str(expected_transaction), "lock_path": str(expected_lock)}
        or safety
        != {
            "payload_transfer": False,
            "partition_write": False,
            "flash": False,
            "persistent_setting": False,
            "credential_or_security_change": False,
            "package_or_immutable_rootfs_change": False,
            "transient_bound_work_copy": True,
            "exact_work_cleanup_required": True,
            "recovery_mutation": False,
            "other_targets_untouched": True,
        }
        or authority
        != {
            "manifest_grants_live_authority": False,
            "operator_approval_required": False,
            "operator_attendance_required": False,
            "active_contract_presence_mode_required": WORKFLOW,
            "fresh_d0_required": True,
            "one_ordinal_only": True,
        }
    ):
        raise ContractError("unattended D1 action or safety contract changed")
    spec = UnattendedSpec(
        manifest_path=manifest.path,
        manifest_sha256=manifest.sha256,
        run_id=run_id,
        base_manifest=base_manifest,
        base=base,
        qualification=qualification,
        review_receipt=review,
        source_closure=sources,
        transaction_dir=expected_transaction,
        lock_path=expected_lock,
    )
    spec.binding.validate()
    return spec


def _binding_value(value: UnattendedBinding) -> dict[str, Any]:
    value.validate()
    return {
        "run_id": value.run_id,
        "workflow": value.workflow,
        "manifest_sha256": value.manifest_sha256,
        "resident_boot_sha256": value.resident_boot_sha256,
        "rollback_boot_sha256": value.rollback_boot_sha256,
        "rootfs_sha256": value.rootfs_sha256,
        "observer_sha256": value.observer_sha256,
        "qualification_sha256": value.qualification_sha256,
        "action_allowlist": [SessionAction.SWITCHROOT_EXPERIMENT.value],
        "ordinal": 1,
        "payload_transfer": False,
        "partition_write": False,
        "flash": False,
        "action_replay": False,
    }


def _append_journal(
    spec: UnattendedSpec,
    action: str,
    payload: dict[str, Any],
    *,
    expected_sequence: int,
) -> Path:
    bound = {"schema", "sequence", "action", "run_id", "manifest_sha256"}
    if bound.intersection(payload):
        raise ContractError("unattended D1 journal payload overrides binding")
    journal = spec.transaction_dir / "journal"
    existing = tuple(sorted(journal.glob("*.json"))) if journal.exists() else ()
    if len(existing) != expected_sequence:
        raise ContractError("unattended D1 journal sequence changed")
    path = journal / f"{expected_sequence:04d}-{action}.json"
    attended.write_private_json_exclusive(
        path,
        {
            "schema": JOURNAL_SCHEMA,
            "sequence": expected_sequence,
            "timestamp_utc": utc_now(),
            "action": action,
            "run_id": spec.run_id,
            "manifest_sha256": spec.manifest_sha256,
            **payload,
        },
    )
    return path


def _healthy_unattended_postflight(value: SessionPreflight | None) -> bool:
    if not isinstance(value, SessionPreflight):
        return False
    try:
        value.validate()
    except Exception:  # noqa: BLE001 - result cannot claim durable health
        return False
    return (
        value.operator_attended is False
        and value.unattended_resident_d1_qualified is True
        and value.target_identity_matches is True
        and value.resident_identity_matches is True
        and value.rollback_ready is True
        and value.recovery_available is True
    )


def _revalidate_execution_closure(spec: UnattendedSpec) -> None:
    current = load_spec(spec.manifest_path, spec.manifest_sha256)
    if current != spec:
        raise ContractError("unattended D1 execution closure changed")


def _validate_persisted_action_evidence(
    action_dir: Path,
    outcome: engine.SessionActionResult,
) -> tuple[
    attended.BoundFile,
    attended.BoundFile | None,
    dict[str, Any],
    int | None,
]:
    outcome_path = action_dir / "engine-outcome.json"
    outcome_evidence = _bound_file(outcome_path, private=True)
    persisted_outcome = _read_private_json(outcome_path)
    if persisted_outcome != attended._action_outcome_value(1, outcome):
        raise ContractError("durable engine outcome differs from returned outcome")

    result_path = action_dir / "result.json"
    if not result_path.is_file():
        if (
            outcome.status is engine.SessionActionStatus.EXPERIMENT_BLOCKED
            and outcome.failure_class
            in {
                "PRE_HANDOFF_EXPERIMENT_BLOCKED",
                "PRE_DISPATCH_INTEGRITY_BLOCKED",
            }
        ):
            return outcome_evidence, None, {}, 0
        if outcome.status in {
            engine.SessionActionStatus.DEVICE_SAFETY_FAILURE,
            engine.SessionActionStatus.CONTROL_AMBIGUOUS,
        }:
            return outcome_evidence, None, {}, None
        raise ContractError("durable action result is absent for completed effect")

    result_evidence = _bound_file(result_path, private=True)
    result = _read_private_json(result_path)
    expected_terminal = {
        (engine.SessionActionStatus.PROVED, None): (
            "PASS_SWITCHROOT_RETURN_NO_PROOF_DISPLAY_VISIBILITY"
        ),
        (
            engine.SessionActionStatus.REFUTED,
            "DISPLAY_ACQUISITION_REFUTED",
        ): "REFUTED_DISPLAY_ACQUISITION",
        (
            engine.SessionActionStatus.REFUTED,
            "DISPLAY_VISIBILITY_REFUTED",
        ): "REFUTED_DISPLAY_VISIBILITY",
        (
            engine.SessionActionStatus.NO_PROOF_OBSERVER,
            "RETURN_CHANNEL_OBSERVER",
        ): "NO_PROOF_RETURN_OBSERVER",
        (
            engine.SessionActionStatus.NO_PROOF_OBSERVER,
            "DISPLAY_EVIDENCE_OBSERVER",
        ): "NO_PROOF_DISPLAY_OBSERVER",
        (
            engine.SessionActionStatus.EXPERIMENT_BLOCKED,
            "POSTFLIGHT_EXPERIMENT_BLOCKED",
        ): "SESSION_BLOCKED_RESIDENT_HEALTHY",
    }.get((outcome.status, outcome.failure_class))
    detailed_status = outcome.status in {
        engine.SessionActionStatus.PROVED,
        engine.SessionActionStatus.REFUTED,
        engine.SessionActionStatus.NO_PROOF_OBSERVER,
    } or (
        outcome.status is engine.SessionActionStatus.EXPERIMENT_BLOCKED
        and outcome.failure_class == "POSTFLIGHT_EXPERIMENT_BLOCKED"
    )
    if (
        not detailed_status
        or result.get("schema") != attended.RESULT_SCHEMA
        or result.get("ordinal") != 1
        or result.get("handoff_dispatch_count") != 1
        or result.get("resident_healthy") is not True
        or any(
            result.get(key) is not False
            for key in ("payload_transfer", "partition_write", "flash")
        )
        or expected_terminal is None
        or result.get("proof_terminal") != expected_terminal
        or not isinstance(result.get("observation"), dict)
        or not isinstance(result.get("final_health"), dict)
    ):
        raise ContractError("durable action result is not exact")
    observation = result["observation"]
    if outcome.status is engine.SessionActionStatus.PROVED and (
        result.get("candidate_return_observed") is not True
        or observation.get("display_mechanical_proof") is not True
        or observation.get("bounded_display_failure") is not False
    ):
        raise ContractError("durable proved result lacks switch-root proof")
    if outcome.failure_class == "DISPLAY_ACQUISITION_REFUTED" and (
        result.get("candidate_return_observed") is not True
        or observation.get("bounded_display_failure") is not True
    ):
        raise ContractError("durable display refutation is not exact")
    if outcome.failure_class == "DISPLAY_VISIBILITY_REFUTED" and (
        result.get("candidate_return_observed") is not True
        or observation.get("display_mechanical_proof") is not True
    ):
        raise ContractError("durable visibility refutation is not exact")
    if outcome.failure_class == "RETURN_CHANNEL_OBSERVER" and (
        result.get("candidate_return_observed") is not False
    ):
        raise ContractError("durable return no-proof is not exact")
    if outcome.failure_class == "DISPLAY_EVIDENCE_OBSERVER" and (
        result.get("candidate_return_observed") is not True
        or observation.get("display_mechanical_proof") is True
        or observation.get("bounded_display_failure") is not False
    ):
        raise ContractError("durable display no-proof is not exact")
    return outcome_evidence, result_evidence, result, 1


def _execute_locked(spec: UnattendedSpec) -> dict[str, Any]:
    if spec.transaction_dir.exists():
        raise ContractError("unattended D1 transaction already exists; replay forbidden")
    try:
        preflight, preflight_evidence = attended.resident_d0_preflight(
            spec.base,
            unattended_qualified=True,
        )
    except Exception as exc:  # noqa: BLE001 - no effect or durable intent yet
        raise ContractError("fresh exact unattended D0 failed") from exc
    if (
        not isinstance(preflight, SessionPreflight)
        or not isinstance(preflight_evidence, dict)
        or set(preflight_evidence)
        != {
            "resident_health",
            "source_preflight",
            "rollback_sha256",
            "recovery_profile",
        }
        or preflight.operator_attended is not False
        or preflight.unattended_resident_d1_qualified is not True
    ):
        raise ContractError("unattended D1 preflight falsely claims attendance")
    preflight.validate()
    _revalidate_execution_closure(spec)
    spec.transaction_dir.mkdir(parents=True, mode=0o700)
    preflight_path = spec.transaction_dir / "fresh-d0-preflight.json"
    attended.write_private_json_exclusive(preflight_path, preflight_evidence)
    preflight_bound = _bound_file(preflight_path, private=True)
    binding = spec.binding
    intent_path = _append_journal(
        spec,
        "ordinal-001-intent",
        {
            "binding": _binding_value(binding),
            "binding_sha256": json_sha256(_binding_value(binding)),
            "fresh_d0_evidence": _as_dict(preflight_bound),
            "presence_mode": WORKFLOW,
            "operator_attended": False,
            "session_window": False,
            "approval_token": False,
            "handoff_dispatch_count_max": 1,
            "action_replay": False,
        },
        expected_sequence=0,
    )
    effects = attended.LiveSessionEffects(
        spec.base,
        spec.transaction_dir,
        binding=binding,  # type: ignore[arg-type]
        opening_preflight_evidence=preflight_evidence,
        visible_confirmed="unavailable",
        presence_mode=WORKFLOW,
        enforce_session_window=False,
        pre_dispatch_revalidate=lambda: _revalidate_execution_closure(spec),
    )
    try:
        outcome = effects.invoke_action(
            binding,  # type: ignore[arg-type]
            1,
            SessionAction.SWITCHROOT_EXPERIMENT,
            binding.observer_sha256,
        )
    except Exception as exc:  # noqa: BLE001 - durable intent forbids retry
        handoff_intent = spec.transaction_dir / "action-001/handoff-intent.json"
        parked = {
            "schema": RESULT_SCHEMA,
            "terminal": "RECOVERY_PENDING_PARKED",
            "device_safety_state": "HEALTH_PENDING",
            "effect_result_available": False,
            "handoff_intent_present": handoff_intent.is_file(),
            "handoff_dispatch_count": None,
            "handoff_dispatch_count_max": 1,
            "exception_type": type(exc).__name__,
            "action_replay": False,
            "next_ordinal_permitted": False,
        }
        _append_journal(
            spec,
            "ordinal-001-result",
            {
                "result": parked,
                "intent_evidence": _as_dict(
                    _bound_file(intent_path, private=True)
                ),
            },
            expected_sequence=1,
        )
        return parked
    action_dir = spec.transaction_dir / "action-001"
    try:
        outcome.validate()
        (
            outcome_evidence,
            action_result_bound,
            action_result_value,
            handoff_dispatch_count,
        ) = _validate_persisted_action_evidence(
            action_dir,
            outcome,
        )
        action_result = (
            _as_dict(action_result_bound)
            if action_result_bound is not None
            else None
        )
    except Exception as exc:  # noqa: BLE001 - never repeat after durable intent
        parked = {
            "schema": RESULT_SCHEMA,
            "terminal": "RECOVERY_PENDING_PARKED",
            "device_safety_state": "HEALTH_PENDING",
            "effect_result_available": True,
            "evidence_packaging_complete": False,
            "handoff_dispatch_count": None,
            "handoff_dispatch_count_max": 1,
            "exception_type": type(exc).__name__,
            "action_replay": False,
            "next_ordinal_permitted": False,
        }
        _append_journal(
            spec,
            "ordinal-001-result",
            {
                "result": parked,
                "intent_evidence": _as_dict(
                    _bound_file(intent_path, private=True)
                ),
            },
            expected_sequence=1,
        )
        return parked
    healthy = _healthy_unattended_postflight(outcome.postflight)
    parked = outcome.status in {
        engine.SessionActionStatus.DEVICE_SAFETY_FAILURE,
        engine.SessionActionStatus.CONTROL_AMBIGUOUS,
    }
    if parked or not healthy:
        terminal = "RECOVERY_PENDING_PARKED"
        device_safety_state = "HEALTH_PENDING"
    else:
        terminal = "ORDINAL_CLOSED_RESIDENT_HEALTHY"
        device_safety_state = "RESIDENT_HEALTHY"
    result = {
        "schema": RESULT_SCHEMA,
        "terminal": terminal,
        "device_safety_state": device_safety_state,
        "experiment_status": outcome.status.value,
        "proof_terminal": action_result_value.get("proof_terminal"),
        "failure_class": outcome.failure_class,
        "action_started": outcome.action_started,
        "operator_attended": False,
        "unattended_resident_d1_qualified": True,
        "handoff_dispatch_count": handoff_dispatch_count,
        "handoff_dispatch_count_max": 1,
        "durable_engine_outcome_validated": True,
        "durable_action_result_validated": action_result is not None,
        "payload_transfer": False,
        "partition_write": False,
        "flash": False,
        "action_replay": False,
        "next_ordinal_permitted": healthy and not parked,
        "fresh_d0_required_before_next_ordinal": True,
    }
    _append_journal(
        spec,
        "ordinal-001-result",
        {
            "result": result,
            "intent_evidence": _as_dict(_bound_file(intent_path, private=True)),
            "engine_outcome_evidence": _as_dict(outcome_evidence),
            "action_result_evidence": action_result,
        },
        expected_sequence=1,
    )
    return result


def execute(spec: UnattendedSpec) -> dict[str, Any]:
    descriptor = os.open(
        spec.lock_path,
        os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
        0o600,
    )
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1
        ):
            raise ContractError("unattended D1 lock identity is not exact")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ContractError("unattended D1 transaction is already owned") from exc
        return _execute_locked(spec)
    finally:
        os.close(descriptor)


def inspect(spec: UnattendedSpec) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "mode": "host-only-inspection",
        "run_id": spec.run_id,
        "workflow": WORKFLOW,
        "manifest_sha256": spec.manifest_sha256,
        "qualification_sha256": spec.qualification.binding_sha256,
        "review_receipt_sha256": spec.review_receipt.sha256,
        "ready_for_fresh_exact_d0": True,
        "operator_attendance_required": False,
        "operator_attended_asserted": False,
        "approval_required": False,
        "session_window": False,
        "action_budget": False,
        "one_ordinal_only": True,
        "device_contact": False,
        "device_effect": False,
        "payload_transfer": False,
        "partition_write": False,
        "flash": False,
        "live_authority": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--expect-manifest-sha256")
    parser.add_argument("--build-manifest", action="store_true")
    parser.add_argument("--base-attended-manifest", type=Path)
    parser.add_argument("--expect-base-attended-manifest-sha256")
    parser.add_argument("--qualification-transaction-dir", type=Path)
    parser.add_argument("--review-receipt", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--execute-switchroot", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.build_manifest:
        required = (
            args.base_attended_manifest,
            args.expect_base_attended_manifest_sha256,
            args.qualification_transaction_dir,
            args.review_receipt,
            args.run_id,
            args.output,
        )
        if any(item is None for item in required):
            raise ContractError("unattended manifest-build arguments are incomplete")
        value = build_manifest(
            base_manifest_path=args.base_attended_manifest,
            base_manifest_sha256=args.expect_base_attended_manifest_sha256,
            qualification_transaction_dir=args.qualification_transaction_dir,
            review_receipt_path=args.review_receipt,
            run_id=args.run_id,
        )
        attended.write_private_json_exclusive(args.output, value)
        print(
            json.dumps(
                {"manifest_sha256": sha256_file(args.output), "host_only": True},
                sort_keys=True,
            )
        )
        return 0
    if args.manifest is None or args.expect_manifest_sha256 is None:
        raise ContractError("manifest and expected SHA256 are required")
    spec = load_spec(args.manifest, args.expect_manifest_sha256)
    result = execute(spec) if args.execute_switchroot else inspect(spec)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, attended.ContractError) as exc:
        print(f"a90-unattended-resident-d1-v1: ContractError: {exc}", file=sys.stderr)
        raise SystemExit(1)
