#!/usr/bin/env python3
"""Pure host contract core for the reusable A90 boot-only F1 owner.

This module performs no device I/O.  It owns strict canonical JSON, immutable
journal publication, manifest/result validation, and held-file identities.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


CAPABILITY = "A90_BOOT_ONLY_F1_OWNER_V1"
MANIFEST_SCHEMA = "a90-boot-only-f1-manifest-v1"
REVIEW_SCHEMA = "a90-boot-only-f1-capability-review-v1"
RUNTIME_QUALIFICATION_SCHEMA = "a90-boot-only-f1-runtime-qualification-v1"
RESIDENT_QUALIFICATION_SCHEMA = "a90-boot-only-f1-resident-qualification-v2"
RECOVERY_QUALIFICATION_SCHEMA = "a90-boot-only-f1-recovery-qualification-v2"
QUALIFICATION_SCHEMA = "a90-boot-only-f1-hazard-qualification-v2"
APPROVAL_BINDING_SCHEMA = "a90-boot-only-f1-approval-binding-v1"
APPROVAL_SCHEMA = "a90-boot-only-f1-approval-v1"
JOURNAL_SCHEMA = "a90-boot-only-f1-journal-record-v1"
HEAD_SCHEMA = "a90-boot-only-f1-journal-head-v1"
SUCCESS_SCHEMA = "resident-install-terminal-v1"
RESULT_SCHEMA = "a90-boot-only-f1-result-v1"
SUCCESS_TERMINAL = "PASS_A90_RESIDENT_INSTALLED"
ROLLBACK_TERMINAL = "NO_PROOF_ROLLED_BACK"
RECOVERY_TERMINAL = "RECOVERY_REQUIRED"
APPROVAL_PREFIX = "A90-BOOT-ONLY-F1-APPROVE:"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
RUN_ID_RE = re.compile(r"^a90-boot-only-f1-[0-9]{8}-[0-9]{2}$")
JOURNAL_NAMESPACE_RE = re.compile(
    r"^boot-only-f1-v1-[0-9a-f]{64}-a90-boot-only-f1-[0-9]{8}-[0-9]{2}$"
)
HAZARD_IDS = frozenset({"RKP_CFP_DISABLED_RESIDENT"})

MANIFEST_KEYS = frozenset(
    {
        "schema",
        "capability",
        "targetProfile",
        "expectedStart",
        "candidate",
        "rollback",
        "flashHelper",
        "timeouts",
        "observation",
        "recovery",
        "hazards",
        "ownerClosureSha256",
    }
)
IMAGE_KEYS = frozenset({"path", "size", "sha256", "version", "build"})
HELPER_KEYS = frozenset({"path", "size", "sha256"})
EXPECTED_KEYS = frozenset(
    {
        "version",
        "build",
        "residentQualificationPath",
        "residentQualificationSha256",
    }
)
TIMEOUT_KEYS = frozenset({"recoverySec", "bridgeSec", "healthSec"})
OBSERVATION_KEYS = frozenset({"acceptanceRuleSha256"})
RECOVERY_KEYS = frozenset(
    {"plan", "version", "build", "qualificationPath", "qualificationSha256"}
)
HAZARD_KEYS = frozenset({"id", "qualificationPath", "qualificationSha256"})
RUNTIME_MEMBER_KEYS = frozenset(
    {
        "path",
        "size",
        "sha256",
        "versionReceipt",
        "versionReceiptSha256",
        "runtimeRoots",
        "externalFiles",
        "dynamicLibraries",
        "runtimeClosureSha256",
    }
)
RUNTIME_ROOT_KEYS = frozenset(
    {"path", "state", "fileCount", "totalBytes", "treeSha256"}
)
RUNTIME_FILE_KEYS = frozenset({"path", "size", "sha256"})

STATES = frozenset(
    {
        "PREPARED",
        "APPROVED",
        "CANDIDATE_INTENT",
        "CANDIDATE_LAUNCHED",
        "CANDIDATE_RESULT",
        "ROLLBACK_INTENT",
        "ROLLBACK_LAUNCHED",
        "ROLLBACK_RESULT",
        "ROLLBACK_RELEASE_UNCERTAIN",
        SUCCESS_TERMINAL,
        ROLLBACK_TERMINAL,
        RECOVERY_TERMINAL,
    }
)
TERMINALS = frozenset({SUCCESS_TERMINAL, ROLLBACK_TERMINAL, RECOVERY_TERMINAL})
ALLOWED_NEXT: dict[str | None, frozenset[str]] = {
    None: frozenset({"PREPARED"}),
    "PREPARED": frozenset({"APPROVED"}),
    "APPROVED": frozenset({"CANDIDATE_INTENT"}),
    "CANDIDATE_INTENT": frozenset(
        {"CANDIDATE_LAUNCHED", "ROLLBACK_INTENT", RECOVERY_TERMINAL}
    ),
    "CANDIDATE_LAUNCHED": frozenset(
        {"CANDIDATE_RESULT", "ROLLBACK_INTENT", RECOVERY_TERMINAL}
    ),
    "CANDIDATE_RESULT": frozenset({SUCCESS_TERMINAL, "ROLLBACK_INTENT"}),
    "ROLLBACK_INTENT": frozenset({"ROLLBACK_LAUNCHED"}),
    "ROLLBACK_LAUNCHED": frozenset(
        {"ROLLBACK_RESULT", "ROLLBACK_RELEASE_UNCERTAIN"}
    ),
    "ROLLBACK_RESULT": frozenset({ROLLBACK_TERMINAL, RECOVERY_TERMINAL}),
    "ROLLBACK_RELEASE_UNCERTAIN": frozenset({RECOVERY_TERMINAL}),
    SUCCESS_TERMINAL: frozenset(),
    ROLLBACK_TERMINAL: frozenset(),
    RECOVERY_TERMINAL: frozenset(),
}


class ContractError(RuntimeError):
    """One fail-closed contract mismatch."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: Any, label: str) -> dt.datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise ContractError(f"{label} is not canonical UTC")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError(f"{label} is not canonical UTC") from exc
    if parsed.tzinfo != dt.timezone.utc:
        raise ContractError(f"{label} is not UTC")
    return parsed


def require_sha(value: Any, label: str) -> str:
    if type(value) is not str or HEX64_RE.fullmatch(value) is None:
        raise ContractError(f"{label} is not lowercase SHA256")
    return value


def require_string(value: Any, label: str, *, pattern: re.Pattern[str] | None = None) -> str:
    if type(value) is not str or not value:
        raise ContractError(f"{label} is not one nonempty string")
    if pattern is not None and pattern.fullmatch(value) is None:
        raise ContractError(f"{label} has invalid grammar")
    return value


def require_int(value: Any, label: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ContractError(f"{label} is outside its integer bound")
    return value


def require_object(value: Any, keys: frozenset[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise ContractError(f"{label} schema mismatch")
    if any(type(key) is not str for key in value):
        raise ContractError(f"{label} has a non-string key")
    return value


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ContractError("value is not canonical JSON data") from exc


def canonical_file_bytes(value: Any) -> bytes:
    return canonical_json(value) + b"\n"


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if type(key) is not str or key in result:
            raise ContractError("JSON contains duplicate or non-string key")
        result[key] = value
    return result


def parse_canonical_bytes(raw: bytes, label: str) -> Any:
    if type(raw) is not bytes or not raw.endswith(b"\n") or b"\r" in raw:
        raise ContractError(f"{label} framing is not canonical")
    try:
        value = json.loads(
            raw.decode("ascii"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ContractError(f"{label} contains non-finite {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label} is not strict JSON") from exc
    if canonical_file_bytes(value) != raw:
        raise ContractError(f"{label} bytes are not canonical")
    return value


def load_canonical(path: Path, label: str) -> tuple[bytes, Any]:
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        metadata = os.fstat(descriptor)
        path_metadata = path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or not stat.S_ISREG(path_metadata.st_mode)
            or metadata.st_nlink != 1
            or path_metadata.st_nlink != 1
            or metadata.st_uid != os.getuid()
            or metadata.st_gid != os.getgid()
            or metadata.st_mode & 0o022
            or (metadata.st_dev, metadata.st_ino)
            != (path_metadata.st_dev, path_metadata.st_ino)
            or not 1 <= metadata.st_size <= 4 * 1024 * 1024
        ):
            raise ContractError(f"{label} file identity mismatch")
        raw = bytearray()
        offset = 0
        while offset < metadata.st_size:
            chunk = os.pread(descriptor, min(1 << 20, metadata.st_size - offset), offset)
            if not chunk:
                raise ContractError(f"{label} file ended early")
            raw.extend(chunk)
            offset += len(chunk)
        if os.pread(descriptor, 1, metadata.st_size):
            raise ContractError(f"{label} file grew during read")
        final = os.fstat(descriptor)
        if (final.st_dev, final.st_ino, final.st_size) != (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_size,
        ):
            raise ContractError(f"{label} file drifted during read")
    finally:
        os.close(descriptor)
    exact = bytes(raw)
    return exact, parse_canonical_bytes(exact, label)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_absolute_path(value: Any, label: str) -> str:
    text = require_string(value, label)
    path = Path(text)
    if not path.is_absolute() or str(path) != text or ".." in path.parts:
        raise ContractError(f"{label} is not one canonical absolute path")
    return text


def _validate_image(value: Any, label: str) -> dict[str, Any]:
    item = require_object(value, IMAGE_KEYS, label)
    validate_absolute_path(item["path"], f"{label}.path")
    require_int(item["size"], f"{label}.size", minimum=1, maximum=128 * 1024 * 1024)
    require_sha(item["sha256"], f"{label}.sha256")
    require_string(item["version"], f"{label}.version")
    require_string(item["build"], f"{label}.build")
    return item


def validate_manifest(value: Any) -> dict[str, Any]:
    manifest = require_object(value, MANIFEST_KEYS, "manifest")
    if manifest["schema"] != MANIFEST_SCHEMA or manifest["capability"] != CAPABILITY:
        raise ContractError("manifest capability/schema mismatch")
    if manifest["targetProfile"] != "A90_5G_OPERATOR_OWNED":
        raise ContractError("manifest target profile mismatch")
    expected = require_object(manifest["expectedStart"], EXPECTED_KEYS, "expectedStart")
    require_string(expected["version"], "expectedStart.version")
    require_string(expected["build"], "expectedStart.build")
    validate_absolute_path(
        expected["residentQualificationPath"],
        "expectedStart.residentQualificationPath",
    )
    require_sha(
        expected["residentQualificationSha256"],
        "expectedStart.residentQualificationSha256",
    )
    candidate = _validate_image(manifest["candidate"], "candidate")
    rollback = _validate_image(manifest["rollback"], "rollback")
    if candidate["path"] == rollback["path"] or candidate["sha256"] == rollback["sha256"]:
        raise ContractError("candidate and rollback must be distinct")
    helper = require_object(manifest["flashHelper"], HELPER_KEYS, "flashHelper")
    validate_absolute_path(helper["path"], "flashHelper.path")
    require_int(helper["size"], "flashHelper.size", minimum=1, maximum=4 * 1024 * 1024)
    require_sha(helper["sha256"], "flashHelper.sha256")
    timeouts = require_object(manifest["timeouts"], TIMEOUT_KEYS, "timeouts")
    require_int(timeouts["recoverySec"], "timeouts.recoverySec", minimum=30, maximum=900)
    require_int(timeouts["bridgeSec"], "timeouts.bridgeSec", minimum=5, maximum=300)
    require_int(timeouts["healthSec"], "timeouts.healthSec", minimum=30, maximum=900)
    observation = require_object(manifest["observation"], OBSERVATION_KEYS, "observation")
    require_sha(observation["acceptanceRuleSha256"], "observation.acceptanceRuleSha256")
    recovery = require_object(manifest["recovery"], RECOVERY_KEYS, "recovery")
    if recovery["plan"] != "V2321_BOOT_ONLY":
        raise ContractError("recovery plan is not the fixed boot-only V2321 plan")
    if (recovery["version"], recovery["build"]) != (
        rollback["version"],
        rollback["build"],
    ):
        raise ContractError("rollback and recovery identities differ")
    validate_absolute_path(recovery["qualificationPath"], "recovery.qualificationPath")
    require_sha(recovery["qualificationSha256"], "recovery.qualificationSha256")
    hazards = manifest["hazards"]
    if type(hazards) is not list or not hazards:
        raise ContractError("manifest hazards are absent")
    seen: set[str] = set()
    for index, raw_hazard in enumerate(hazards):
        hazard = require_object(raw_hazard, HAZARD_KEYS, f"hazards[{index}]")
        hazard_id = require_string(hazard["id"], f"hazards[{index}].id")
        if hazard_id not in HAZARD_IDS or hazard_id in seen:
            raise ContractError("unknown or duplicate manifest hazard")
        seen.add(hazard_id)
        validate_absolute_path(
            hazard["qualificationPath"], f"hazards[{index}].qualificationPath"
        )
        require_sha(hazard["qualificationSha256"], f"hazards[{index}].qualificationSha256")
    require_sha(manifest["ownerClosureSha256"], "ownerClosureSha256")
    return manifest


def validate_resident_qualification(
    value: Any,
    expected: dict[str, Any],
) -> dict[str, Any]:
    qualification = require_object(
        value,
        frozenset(
            {
                "schema",
                "capability",
                "version",
                "build",
                "installTerminalSha256",
                "deviceSafetyState",
                "disposition",
            }
        ),
        "resident qualification",
    )
    if (
        qualification["schema"] != RESIDENT_QUALIFICATION_SCHEMA
        or qualification["capability"] != CAPABILITY
        or qualification["version"] != expected["version"]
        or qualification["build"] != expected["build"]
        or qualification["deviceSafetyState"] != "RESIDENT_HEALTHY"
        or qualification["disposition"] != "QUALIFIED_INSTALLED_RESIDENT"
    ):
        raise ContractError("resident qualification mismatch")
    require_sha(
        qualification["installTerminalSha256"],
        "resident qualification install terminal SHA256",
    )
    return qualification


def validate_recovery_qualification(
    value: Any,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    qualification = require_object(
        value,
        frozenset(
            {
                "schema",
                "capability",
                "plan",
                "rollbackSha256",
                "physicalRecoveryDemonstrated",
                "disposition",
            }
        ),
        "recovery qualification",
    )
    if (
        qualification["schema"] != RECOVERY_QUALIFICATION_SCHEMA
        or qualification["capability"] != CAPABILITY
        or qualification["plan"] != manifest["recovery"]["plan"]
        or qualification["rollbackSha256"] != manifest["rollback"]["sha256"]
        or qualification["physicalRecoveryDemonstrated"] is not True
        or qualification["disposition"] != "QUALIFIED_PHYSICAL_RECOVERY"
    ):
        raise ContractError("recovery qualification mismatch")
    return qualification


def validate_runtime_qualification(
    value: Any,
    owner_closure_sha256: str,
) -> dict[str, Any]:
    qualification = require_object(
        value,
        frozenset(
            {
                "schema",
                "capability",
                "ownerClosureSha256",
                "python",
                "adb",
            }
        ),
        "runtime qualification",
    )
    if (
        qualification["schema"] != RUNTIME_QUALIFICATION_SCHEMA
        or qualification["capability"] != CAPABILITY
        or qualification["ownerClosureSha256"] != owner_closure_sha256
    ):
        raise ContractError("runtime qualification identity mismatch")
    for role in ("python", "adb"):
        member = require_object(
            qualification[role], RUNTIME_MEMBER_KEYS, f"runtime {role}"
        )
        validate_absolute_path(member["path"], f"runtime {role}.path")
        require_int(
            member["size"], f"runtime {role}.size", minimum=1, maximum=64 * 1024 * 1024
        )
        for field in ("sha256", "versionReceiptSha256", "runtimeClosureSha256"):
            require_sha(member[field], f"runtime {role}.{field}")
        if type(member["versionReceipt"]) is not dict:
            raise ContractError(f"runtime {role} version receipt is not an object")
        if sha256_bytes(canonical_json(member["versionReceipt"])) != member["versionReceiptSha256"]:
            raise ContractError(f"runtime {role} version receipt digest mismatch")
        roots = member["runtimeRoots"]
        libraries = member["dynamicLibraries"]
        external_files = member["externalFiles"]
        if (
            type(roots) is not list
            or type(external_files) is not list
            or type(libraries) is not list
        ):
            raise ContractError(f"runtime {role} closure inventories are not lists")
        root_paths: list[str] = []
        for index, value in enumerate(roots):
            root = require_object(value, RUNTIME_ROOT_KEYS, f"runtime {role} root {index}")
            path = validate_absolute_path(root["path"], f"runtime {role} root path")
            root_paths.append(path)
            if root["state"] not in {
                "PRESENT_DIRECTORY",
                "PRESENT_REGULAR",
                "ABSENT",
            }:
                raise ContractError(f"runtime {role} root state mismatch")
            file_count = require_int(
                root["fileCount"], f"runtime {role} root fileCount", minimum=0, maximum=100_000
            )
            total_bytes = require_int(
                root["totalBytes"], f"runtime {role} root totalBytes", minimum=0, maximum=4 << 30
            )
            require_sha(root["treeSha256"], f"runtime {role} root treeSha256")
            if root["state"] == "ABSENT" and (file_count != 0 or total_bytes != 0):
                raise ContractError(f"runtime {role} absent root has content")
            if root["state"] == "PRESENT_REGULAR" and file_count != 1:
                raise ContractError(f"runtime {role} regular root count mismatch")
        for inventory_name, inventory in (
            ("external file", external_files),
            ("library", libraries),
        ):
            inventory_paths: list[str] = []
            for index, value in enumerate(inventory):
                item = require_object(
                    value, RUNTIME_FILE_KEYS, f"runtime {role} {inventory_name} {index}"
                )
                path = validate_absolute_path(
                    item["path"], f"runtime {role} {inventory_name} path"
                )
                inventory_paths.append(path)
                require_int(
                    item["size"],
                    f"runtime {role} {inventory_name} size",
                    minimum=1,
                    maximum=1 << 30,
                )
                require_sha(
                    item["sha256"], f"runtime {role} {inventory_name} sha256"
                )
            if inventory_paths != sorted(set(inventory_paths)):
                raise ContractError(
                    f"runtime {role} {inventory_name} inventory is not unique/sorted"
                )
        if root_paths != sorted(set(root_paths)):
            raise ContractError(f"runtime {role} closure inventory is not unique/sorted")
        closure = {
            "versionReceiptSha256": member["versionReceiptSha256"],
            "runtimeRoots": roots,
            "externalFiles": external_files,
            "dynamicLibraries": libraries,
        }
        if sha256_bytes(canonical_json(closure)) != member["runtimeClosureSha256"]:
            raise ContractError(f"runtime {role} closure digest mismatch")
    return qualification


def validate_review(
    value: Any,
    owner_closure_sha256: str,
    runtime_qualification_sha256: str,
) -> dict[str, Any]:
    keys = frozenset(
        {
            "schema",
            "capability",
            "ownerClosureSha256",
            "runtimeQualificationSha256",
            "verdict",
            "findings",
            "contacts",
        }
    )
    review = require_object(value, keys, "capability review")
    if review["schema"] != REVIEW_SCHEMA or review["capability"] != CAPABILITY:
        raise ContractError("capability review identity mismatch")
    if review["ownerClosureSha256"] != owner_closure_sha256:
        raise ContractError("capability review signed another closure")
    if review["runtimeQualificationSha256"] != require_sha(
        runtime_qualification_sha256, "runtime qualification SHA256"
    ):
        raise ContractError("capability review signed another runtime qualification")
    if review["verdict"] != "PASS_GO":
        raise ContractError("capability review did not grant PASS_GO")
    findings = require_object(
        review["findings"], frozenset({"high", "medium", "low"}), "review findings"
    )
    if any(type(findings[name]) is not int or findings[name] != 0 for name in findings):
        raise ContractError("capability review has findings")
    contacts = require_object(
        review["contacts"],
        frozenset({"device", "dev", "usb", "network", "workspacePrivate", "otherTarget"}),
        "review contacts",
    )
    if any(type(contacts[name]) is not int or contacts[name] != 0 for name in contacts):
        raise ContractError("capability review crossed its contact boundary")
    return review


def validate_hazard_qualification(
    value: Any,
    hazard_id: str,
) -> dict[str, Any]:
    keys = frozenset(
        {"schema", "capability", "hazardId", "disposition"}
    )
    qualification = require_object(value, keys, "hazard qualification")
    if (
        qualification["schema"] != QUALIFICATION_SCHEMA
        or qualification["capability"] != CAPABILITY
        or qualification["hazardId"] != hazard_id
        or qualification["disposition"] != "ACCEPTED_FOR_ATTENDED_F1"
    ):
        raise ContractError("hazard qualification mismatch")
    return qualification


@dataclass
class BoundArtifact:
    role: str
    path: Path
    fd: int
    identity: dict[str, Any]
    anchor: Path
    expected_uid: int
    expected_gid: int

    @staticmethod
    def _hash_fd(fd: int, size: int) -> str:
        digest = hashlib.sha256()
        offset = 0
        while offset < size:
            chunk = os.pread(fd, min(1 << 20, size - offset), offset)
            if not chunk:
                raise ContractError("artifact FD ended early")
            digest.update(chunk)
            offset += len(chunk)
        if os.pread(fd, 1, size):
            raise ContractError("artifact FD exceeds its bound size")
        return digest.hexdigest()

    @classmethod
    def open(
        cls,
        *,
        role: str,
        path: Path,
        expected_size: int,
        expected_sha256: str,
        anchor: Path,
        expected_uid: int,
        expected_gid: int,
        executable: bool = False,
    ) -> "BoundArtifact":
        if not path.is_absolute() or not anchor.is_absolute():
            raise ContractError("artifact and anchor paths must be absolute")
        if path == anchor or anchor not in path.parents:
            raise ContractError("artifact path is outside its fixed anchor")
        current = path.parent
        ancestors: list[dict[str, Any]] = []
        while True:
            metadata = current.lstat()
            if not stat.S_ISDIR(metadata.st_mode) or current.is_symlink():
                raise ContractError("artifact ancestor is indirect")
            if metadata.st_mode & 0o022:
                raise ContractError("artifact ancestor is group/world writable")
            if executable and (metadata.st_uid != 0 or metadata.st_gid != 0):
                raise ContractError("system executable ancestor is not root-owned")
            if not executable and (
                metadata.st_uid != expected_uid or metadata.st_gid != expected_gid
            ):
                raise ContractError("artifact ancestor owner mismatch")
            ancestors.append(
                {
                    "path": str(current),
                    "dev": metadata.st_dev,
                    "ino": metadata.st_ino,
                    "mode": metadata.st_mode,
                    "uid": metadata.st_uid,
                    "gid": metadata.st_gid,
                }
            )
            if current == anchor:
                break
            current = current.parent
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            metadata = os.fstat(fd)
            path_metadata = path.lstat()
            if not stat.S_ISREG(metadata.st_mode) or not stat.S_ISREG(path_metadata.st_mode):
                raise ContractError("artifact is not one direct regular file")
            if metadata.st_nlink != 1 or path_metadata.st_nlink != 1:
                raise ContractError("artifact link count is not one")
            if metadata.st_uid != expected_uid or metadata.st_gid != expected_gid:
                raise ContractError("artifact FD owner mismatch")
            if path_metadata.st_uid != expected_uid or path_metadata.st_gid != expected_gid:
                raise ContractError("artifact path owner mismatch")
            if metadata.st_mode & 0o022 or path_metadata.st_mode & 0o022:
                raise ContractError("artifact is group/world writable")
            if (metadata.st_dev, metadata.st_ino) != (
                path_metadata.st_dev,
                path_metadata.st_ino,
            ):
                raise ContractError("artifact path and FD differ")
            if metadata.st_size != expected_size:
                raise ContractError("artifact size mismatch")
            digest = cls._hash_fd(fd, expected_size)
            if digest != expected_sha256:
                raise ContractError("artifact digest mismatch")
            identity = {
                "role": role,
                "path": str(path),
                "dev": metadata.st_dev,
                "ino": metadata.st_ino,
                "mode": metadata.st_mode,
                "uid": metadata.st_uid,
                "gid": metadata.st_gid,
                "nlink": metadata.st_nlink,
                "size": metadata.st_size,
                "sha256": digest,
                "ancestors": ancestors,
            }
            return cls(role, path, fd, identity, anchor, expected_uid, expected_gid)
        except BaseException:
            os.close(fd)
            raise

    def checkpoint(self) -> dict[str, Any]:
        metadata = os.fstat(self.fd)
        path_metadata = self.path.lstat()
        ancestors: list[dict[str, Any]] = []
        current_path = self.path.parent
        while True:
            ancestor = current_path.lstat()
            if not stat.S_ISDIR(ancestor.st_mode) or current_path.is_symlink():
                raise ContractError("artifact ancestor ceased to be direct")
            ancestors.append(
                {
                    "path": str(current_path),
                    "dev": ancestor.st_dev,
                    "ino": ancestor.st_ino,
                    "mode": ancestor.st_mode,
                    "uid": ancestor.st_uid,
                    "gid": ancestor.st_gid,
                }
            )
            if current_path == self.anchor:
                break
            current_path = current_path.parent
        current = {
            "role": self.role,
            "path": str(self.path),
            "dev": metadata.st_dev,
            "ino": metadata.st_ino,
            "mode": metadata.st_mode,
            "uid": metadata.st_uid,
            "gid": metadata.st_gid,
            "nlink": metadata.st_nlink,
            "size": metadata.st_size,
            "sha256": self._hash_fd(self.fd, metadata.st_size),
            "ancestors": ancestors,
        }
        for key in ("versionReceiptSha256", "runtimeClosureSha256"):
            if key in self.identity:
                current[key] = self.identity[key]
        if not stat.S_ISREG(metadata.st_mode) or not stat.S_ISREG(path_metadata.st_mode):
            raise ContractError("artifact ceased to be direct regular")
        if (path_metadata.st_dev, path_metadata.st_ino) != (
            metadata.st_dev,
            metadata.st_ino,
        ):
            raise ContractError("artifact pathname drifted from held FD")
        if current != self.identity:
            raise ContractError("artifact identity or bytes drifted")
        return current

    def close(self) -> None:
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1

    def __enter__(self) -> "BoundArtifact":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_exclusive(path: Path, value: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.tmp.{os.getpid()}"
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o600,
    )
    try:
        try:
            data = canonical_file_bytes(value)
            offset = 0
            while offset < len(data):
                written = os.write(descriptor, data[offset:])
                if written <= 0:
                    raise ContractError("canonical publication short write")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.link(temporary, path, follow_symlinks=False)
        _fsync_dir(path.parent)
    finally:
        temporary.unlink(missing_ok=True)
        _fsync_dir(path.parent)


def _replace_head(path: Path, value: Any) -> None:
    temporary = path.parent / f".{path.name}.replace.{os.getpid()}"
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o600,
    )
    try:
        try:
            data = canonical_file_bytes(value)
            offset = 0
            while offset < len(data):
                written = os.write(descriptor, data[offset:])
                if written <= 0:
                    raise ContractError("journal head short write")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, path)
        _fsync_dir(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


class Journal:
    def __init__(self, directory: Path, run_id: str, manifest_sha256: str) -> None:
        self.directory = directory
        self.run_id = require_string(run_id, "run_id", pattern=RUN_ID_RE)
        self.manifest_sha256 = require_sha(manifest_sha256, "manifest SHA256")
        self.head_path = directory / "HEAD.json"

    def _record_paths(self) -> list[Path]:
        if not self.directory.exists():
            return []
        entries = list(self.directory.iterdir())
        record_paths = sorted(
            path
            for path in entries
            if re.fullmatch(r"[0-9]{4}-[A-Z0-9_]+\.json", path.name)
        )
        allowed = {path.name for path in record_paths} | {"HEAD.json"}
        extras = {path.name for path in entries} - allowed
        if extras:
            raise ContractError("journal contains an unexpected namespace entry")
        return record_paths

    def read(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        previous = "0" * 64
        previous_state: str | None = None
        for sequence, path in enumerate(self._record_paths()):
            expected_prefix = f"{sequence:04d}-"
            if not path.name.startswith(expected_prefix):
                raise ContractError("journal sequence filename gap")
            raw, value = load_canonical(path, f"journal record {sequence}")
            record = require_object(
                value,
                frozenset(
                    {
                        "schema",
                        "sequence",
                        "utc",
                        "state",
                        "runId",
                        "manifestSha256",
                        "previousSha256",
                        "payload",
                    }
                ),
                f"journal record {sequence}",
            )
            if record["schema"] != JOURNAL_SCHEMA:
                raise ContractError("journal schema mismatch")
            if type(record["sequence"]) is not int or record["sequence"] != sequence:
                raise ContractError("journal sequence mismatch")
            parse_utc(record["utc"], "journal UTC")
            state = require_string(record["state"], "journal state")
            if state not in STATES or state not in ALLOWED_NEXT[previous_state]:
                raise ContractError("journal state transition mismatch")
            if path.name != f"{sequence:04d}-{state}.json":
                raise ContractError("journal filename/state mismatch")
            if record["runId"] != self.run_id or record["manifestSha256"] != self.manifest_sha256:
                raise ContractError("journal run/manifest binding mismatch")
            if record["previousSha256"] != previous:
                raise ContractError("journal hash chain mismatch")
            if type(record["payload"]) is not dict:
                raise ContractError("journal payload is not an object")
            previous = sha256_bytes(raw)
            previous_state = state
            records.append(record)
        self._validate_counts(records)
        if self.head_path.exists():
            _raw, head = load_canonical(self.head_path, "journal head")
            head = require_object(
                head,
                frozenset({"schema", "sequence", "recordSha256"}),
                "journal head",
            )
            if not records:
                raise ContractError("journal head exists without records")
            if (
                head["schema"] != HEAD_SCHEMA
                or head["sequence"] != len(records) - 1
                or head["recordSha256"] != previous
            ):
                raise ContractError("journal head does not match tail")
        elif records:
            raise ContractError("journal records exist without a durable head")
        return records

    @staticmethod
    def _validate_counts(records: Iterable[dict[str, Any]]) -> None:
        states = [record["state"] for record in records]
        if states.count("CANDIDATE_INTENT") > 1 or states.count("CANDIDATE_LAUNCHED") > 1:
            raise ContractError("candidate attempt replay")
        if states.count("ROLLBACK_INTENT") > 1 or states.count("ROLLBACK_LAUNCHED") > 1:
            raise ContractError("rollback attempt replay")
        if sum(state in TERMINALS for state in states) > 1:
            raise ContractError("multiple terminal records")

    def append(self, state: str, payload: dict[str, Any]) -> dict[str, Any]:
        records = self.read()
        previous_state = records[-1]["state"] if records else None
        if state not in ALLOWED_NEXT[previous_state]:
            raise ContractError(f"journal transition {previous_state!r}->{state!r} denied")
        sequence = len(records)
        previous_sha = sha256_bytes(canonical_file_bytes(records[-1])) if records else "0" * 64
        record = {
            "schema": JOURNAL_SCHEMA,
            "sequence": sequence,
            "utc": utc_now(),
            "state": state,
            "runId": self.run_id,
            "manifestSha256": self.manifest_sha256,
            "previousSha256": previous_sha,
            "payload": payload,
        }
        path = self.directory / f"{sequence:04d}-{state}.json"
        publish_exclusive(path, record)
        record_sha = sha256_bytes(canonical_file_bytes(record))
        _replace_head(
            self.head_path,
            {"schema": HEAD_SCHEMA, "sequence": sequence, "recordSha256": record_sha},
        )
        self.read()
        return record


def approval_token(binding_sha256: str) -> str:
    return APPROVAL_PREFIX + require_sha(binding_sha256, "approval binding SHA256")


def validate_result(value: Any) -> dict[str, Any]:
    result = require_object(
        value,
        frozenset(
            {
                "schema",
                "status",
                "experimentProof",
                "deviceSafetyState",
                "candidateAttemptCount",
                "rollbackAttemptCount",
                "candidateReplay",
                "terminalPayloadSha256",
            }
        ),
        "owner result",
    )
    if result["schema"] != RESULT_SCHEMA or result["status"] not in TERMINALS:
        raise ContractError("owner result identity mismatch")
    if result["candidateReplay"] is not False:
        raise ContractError("owner result permits candidate replay")
    require_int(
        result["candidateAttemptCount"],
        "candidateAttemptCount",
        minimum=1,
        maximum=1,
    )
    require_int(
        result["rollbackAttemptCount"],
        "rollbackAttemptCount",
        minimum=0,
        maximum=1,
    )
    require_sha(result["terminalPayloadSha256"], "terminalPayloadSha256")
    expected = {
        SUCCESS_TERMINAL: ("PROVED", "RESIDENT_HEALTHY", 0),
        ROLLBACK_TERMINAL: ("NO_PROOF_OBSERVER", "RESIDENT_HEALTHY", 1),
    }
    if result["status"] in expected:
        proof, safety, rollback_count = expected[result["status"]]
        if (
            result["experimentProof"] != proof
            or result["deviceSafetyState"] != safety
            or result["rollbackAttemptCount"] != rollback_count
        ):
            raise ContractError("owner result proof/safety mapping mismatch")
    elif (
        result["experimentProof"] != "NO_PROOF_OBSERVER"
        or result["deviceSafetyState"] != "RECOVERY_REQUIRED"
    ):
        raise ContractError("recovery result proof/safety mapping mismatch")
    return result


def validate_terminal_payload(
    payload: Any,
    manifest: dict[str, Any],
    manifest_sha256: str,
    *,
    run_id: str,
    journal_namespace: str,
) -> dict[str, Any]:
    keys = frozenset(
        {
            "schema",
            "terminal",
            "targetEvidenceSha256",
            "runId",
            "journalNamespace",
            "manifestSha256",
            "candidateSha256",
            "expectedVersion",
            "expectedBuild",
            "observedVersion",
            "observedBuild",
            "ownerClosureSha256",
            "approvalBindingSha256",
            "observationResult",
            "acceptanceRuleSha256",
            "hazards",
            "finalHealth",
            "finalHealthReceiptSha256",
        }
    )
    result = require_object(payload, keys, "success terminal")
    if result["schema"] != SUCCESS_SCHEMA or result["terminal"] != SUCCESS_TERMINAL:
        raise ContractError("success terminal vocabulary mismatch")
    if result["runId"] != run_id or result["journalNamespace"] != journal_namespace:
        raise ContractError("success terminal run binding mismatch")
    if result["manifestSha256"] != manifest_sha256:
        raise ContractError("success terminal manifest mismatch")
    candidate = manifest["candidate"]
    expected = (candidate["version"], candidate["build"])
    if result["candidateSha256"] != candidate["sha256"]:
        raise ContractError("success terminal candidate mismatch")
    if (result["expectedVersion"], result["expectedBuild"]) != expected:
        raise ContractError("success terminal expected identity mismatch")
    if (result["observedVersion"], result["observedBuild"]) != expected:
        raise ContractError("success terminal observed identity mismatch")
    if result["ownerClosureSha256"] != manifest["ownerClosureSha256"]:
        raise ContractError("success terminal owner closure mismatch")
    if result["observationResult"] != "ACCEPTED":
        raise ContractError("success observation was not accepted")
    if result["acceptanceRuleSha256"] != manifest["observation"]["acceptanceRuleSha256"]:
        raise ContractError("success acceptance rule mismatch")
    expected_hazards = [
        {
            "id": hazard["id"],
            "qualificationSha256": hazard["qualificationSha256"],
            "accepted": True,
        }
        for hazard in manifest["hazards"]
    ]
    if result["hazards"] != expected_hazards:
        raise ContractError("success hazard acceptance mismatch")
    if result["finalHealth"] != "RESIDENT_HEALTHY":
        raise ContractError("success final health mismatch")
    for field in (
        "targetEvidenceSha256",
        "approvalBindingSha256",
        "finalHealthReceiptSha256",
    ):
        require_sha(result[field], f"success.{field}")
    return result
