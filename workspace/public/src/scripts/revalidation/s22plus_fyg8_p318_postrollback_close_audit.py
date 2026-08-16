#!/usr/bin/env python3
"""Audit the closed P3.18 post-rollback finalizer without device contact.

The consumed finalizer source and authority remain immutable.  Its generic
``--validate`` path reaches the common final-observer validator before the
incident-specific stage-101 correlation patch is installed.  This H0-only
auditor applies that already-reviewed patch only around the CLOSED validation
seam, then validates the retained terminal, journal, arm, health and no-replay
state.  It has no ADB, USB, Odin, subprocess or device-action path.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
FINALIZER = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_postrollback_finalize.py"
)
AUTHORITY = ROOT / (
    "workspace/public/src/device-action/recovery/"
    "s22plus_fyg8_p318_postrollback_finalize_v1.json"
)
OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "postrollback-close-audit-20260817-01.json"
)
FINALIZER_SIZE = 51413
FINALIZER_SHA256 = "a23eafbd2f7be73fe2ac1ef20ed9a079683b047cd038c23749f6bf92cc3a3596"
AUTHORITY_SIZE = 12635
AUTHORITY_SHA256 = "fc8556fb61601a575b95be17a20d57f5ba5677f909280be2220e961519e257c7"
APPROVAL_BINDING = "131c6d13ee7710b22b75cfe55381a612d1403c5e0013528e0e49d5ec38633751"
SCHEMA = "s22plus_fyg8_p318_postrollback_close_audit_v1"
VERDICT = "PASS_P318_POSTROLLBACK_CLOSE_AUDIT_H0"


class AuditError(RuntimeError):
    """The exact retained P3.18 terminal closure differs."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _stable_bytes(
    path: Path,
    size: int,
    digest: str,
    label: str,
    required_mode: int | None = None,
) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(size + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AuditError(f"{label} is unavailable") from exc
    identity = lambda value: (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or (
            required_mode is not None
            and stat.S_IMODE(before.st_mode) != required_mode
        )
        or len(payload) != size
        or _sha256(payload) != digest
        or identity(before) != identity(inside)
        or identity(before) != identity(after)
    ):
        raise AuditError(f"{label} identity differs")
    return payload


def _load_finalizer() -> Any:
    _stable_bytes(FINALIZER, FINALIZER_SIZE, FINALIZER_SHA256, "frozen finalizer")
    sys.path.insert(0, str(FINALIZER.parent))
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_p318_postrollback_finalize_frozen", FINALIZER
    )
    if spec is None or spec.loader is None:
        raise AuditError("frozen finalizer loader is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _file_receipt(module: Any, path: Path, label: str, maximum: int) -> dict[str, Any]:
    payload = module._stable_read(path, label, maximum)
    metadata = path.lstat()
    return {
        "path": path.resolve(strict=True).relative_to(ROOT).as_posix(),
        "size": len(payload),
        "sha256": _sha256(payload),
        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
        "nlink": metadata.st_nlink,
    }


def _validate_terminal(result: dict[str, Any], journal: Any, prepared: Any) -> None:
    state = result.get("live_state")
    if (
        journal.state() != "CLOSED"
        or len(journal.records()) != 19
        or result.get("schema") != "device_action_f1_live_result_v2"
        or result.get("verdict") != "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
        or result.get("outcome_class") != "candidate_not_proven_rollback_verified"
        or result.get("recovery_required") is not False
        or result.get("current_state") != "CLOSED"
        or result.get("approval_binding_sha256") != prepared.binding_sha256
        or not isinstance(state, dict)
        or state.get("candidate_completed") is not True
        or state.get("rollback_completed") is not True
        or state.get("final_verified") is not True
        or state.get("candidate_observer_accepted") is not False
        or state.get("candidate_observer_classification") != "endpoint-timeout"
        or (prepared.run_dir / "candidate-attempt-02.start.json").exists()
        or (prepared.run_dir / "rollback-attempt-02.start.json").exists()
    ):
        raise AuditError("P3.18 retained terminal semantics differ")


def build_receipt() -> dict[str, Any]:
    module = _load_finalizer()
    _stable_bytes(AUTHORITY, AUTHORITY_SIZE, AUTHORITY_SHA256, "frozen authority")
    authority = module.load_authority(AUTHORITY)
    if authority.get("approval_binding_sha256") != APPROVAL_BINDING:
        raise AuditError("P3.18 finalizer approval binding differs")

    original = module._validate_resumable_state

    def validate_with_incident_patch(authority_value: Any, prepared: Any, journal: Any) -> None:
        patch = module.ProgressCorrelationPatch()
        with patch.installed():
            original(authority_value, prepared, journal)

    module._validate_resumable_state = validate_with_incident_patch
    try:
        prepared, journal, evidence = module.verify_incident(authority)
    finally:
        module._validate_resumable_state = original

    module.verify_existing_arm(authority, prepared.run_dir)
    adb = module._paths(authority)["adb"]
    module._verify_adb_execution_input(
        adb,
        authority["binding"]["immutable_inputs"]["adb"],
        "P3.18 close-audit ADB input",
    )
    result_path = prepared.run_dir / "live-result.json"
    result = module._load_json(result_path, "P3.18 closed live result")
    patch = module.ProgressCorrelationPatch()
    with patch.installed():
        module.live.validate_live_result(result, prepared)
    _validate_terminal(result, journal, prepared)

    files = {
        "arm": _file_receipt(
            module, prepared.run_dir / module.ARM_FILENAME, "finalizer arm", 512 * 1024
        ),
        "health": _file_receipt(
            module,
            prepared.run_dir / module.HEALTH_FILENAME,
            "final health",
            512 * 1024,
        ),
        "live_result": _file_receipt(
            module, result_path, "closed live result", 2 * 1024 * 1024
        ),
        "journal_head": _file_receipt(
            module,
            prepared.run_dir / "transaction/journal-head.json",
            "closed journal head",
            512 * 1024,
        ),
        "adb": _file_receipt(module, adb, "close-audit ADB", 2 * 1024 * 1024),
    }
    if any(value["nlink"] != 1 for value in files.values()):
        raise AuditError("P3.18 close-audit file link count differs")
    if any(files[name]["mode"] != "0400" for name in ("arm", "health", "live_result", "journal_head")):
        raise AuditError("P3.18 close-audit receipt mode differs")
    if files["adb"]["mode"] != "0500":
        raise AuditError("P3.18 close-audit ADB mode differs")

    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": {"model": "SM-S906N", "device": "g0q", "firmware": "S906NKSS7FYG8"},
        "finalizer": {"size": FINALIZER_SIZE, "sha256": FINALIZER_SHA256},
        "authority": {
            "size": AUTHORITY_SIZE,
            "sha256": AUTHORITY_SHA256,
            "approval_binding_sha256": APPROVAL_BINDING,
        },
        "terminal": {
            "journal_state": "CLOSED",
            "journal_record_count": 19,
            "verdict": result["verdict"],
            "outcome_class": result["outcome_class"],
            "recovery_required": False,
            "candidate_transfers": 1,
            "rollback_transfers": 1,
            "candidate_attempt_2_absent": True,
            "rollback_attempt_2_absent": True,
            "candidate_topology_record_sha256": evidence["record"]["sha256"],
        },
        "files": files,
        "scope": {
            "device_actions": False,
            "device_contact": False,
            "adb_commands": 0,
            "odin_invocations": 0,
            "candidate_replay": False,
            "rollback_replay": False,
            "live_authority_created": False,
        },
        "known_original_validate_gap": (
            "common final-observer validation precedes the incident correlation patch"
        ),
    }


def encode_receipt(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def write_receipt() -> dict[str, Any]:
    module = _load_finalizer()
    value = build_receipt()
    payload = encode_receipt(value)
    OUTPUT.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if OUTPUT.exists() or OUTPUT.is_symlink():
        _stable_bytes(
            OUTPUT,
            len(payload),
            _sha256(payload),
            "P3.18 close-audit receipt",
            required_mode=0o400,
        )
    else:
        module._write_mode0400_exclusive(OUTPUT, value, "P3.18 close-audit receipt")
    _stable_bytes(
        OUTPUT,
        len(payload),
        _sha256(payload),
        "P3.18 close-audit receipt",
        required_mode=0o400,
    )
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--audit-only", action="store_true")
    group.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    value = write_receipt() if args.write_receipt else build_receipt()
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AuditError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"P3.18 post-rollback close-audit error: {exc}", file=sys.stderr)
        raise SystemExit(2)
