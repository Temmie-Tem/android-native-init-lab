#!/usr/bin/env python3
"""Reusable boot-only A90 F1 transaction owner.

The current generation is H0 implementation only.  Its strict data and state
machine are executable in host tests, but the production CLI deliberately
rejects live execution until recovery/resume and runtime-closure qualification
are implemented and independently reviewed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import signal
import stat
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from a90_boot_only_f1_contract_v1 import (
    APPROVAL_BINDING_SCHEMA,
    APPROVAL_SCHEMA,
    CAPABILITY,
    RECOVERY_TERMINAL,
    RESULT_SCHEMA,
    ROLLBACK_TERMINAL,
    SUCCESS_TERMINAL,
    BoundArtifact,
    ContractError,
    Journal,
    approval_token,
    canonical_json,
    load_canonical,
    parse_canonical_bytes,
    parse_utc,
    publish_exclusive,
    require_object,
    require_sha,
    require_string,
    sha256_bytes,
    utc_now,
    validate_manifest,
    validate_runtime_qualification,
    validate_result,
    validate_terminal_payload,
)


IMPLEMENTATION_STATUS = "H0_RECOVERY_RESUME_AND_RUNTIME_QUALIFICATION_ABSENT"
LIVE_EXECUTION_ENABLED = False
PYTHON_EXECUTABLE = Path("/usr/bin/python3.14")
ADB_EXECUTABLE = Path("/usr/lib/android-sdk/platform-tools/adb")
REPO_ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = REPO_ROOT / "workspace/public/src/scripts/revalidation"
FD_EXEC_PATH = REVALIDATION / "a90_boot_only_f1_fd_exec.py"
BOOTSTRAP_PATH = REVALIDATION / "a90_boot_only_f1_helper_bootstrap.py"
HELPER_PATH = REVALIDATION / "native_init_flash.py"
HELPER_RUNTIME_CLOSURE_SHA256 = (
    "9907a2864988817a41f5133dd390a387c362fa81c1fff4dd81f4f100ca229f10"
)
HELPER_SPECS = {
    "_workspace_bootstrap.py": (
        1_255,
        "7a8322f9760c8aa3672e094b01df0231fb5b0a85ceaeb5ad73042fcd3f3a6ffe",
    ),
    "a90_boot_only_f1_fd_exec.py": (
        3_493,
        "b55959a4362d459df0058a7b6bca7630a27978e0b1246868cb993ef1380abf57",
    ),
    "a90_boot_only_f1_helper_bootstrap.py": (
        4_767,
        "26b98c3714ea5f8865cb552abb191fbbb6cb5eb3472ddfbb6a03bc308d8e9233",
    ),
    "a90_observation_pipeline.py": (
        24_478,
        "6fa353b4e28ad26e76ec98d0e2c30089b493356fb314b36b962ce97e34a00adb",
    ),
    "a90_serial_lock.py": (
        2_860,
        "663dd16f5121e35fc1047d563bdbe55148695224cf0c6ca5ab59c0433b6191c7",
    ),
    "a90_transition_contract_v2.py": (
        13_734,
        "64e640dfb54d016f8e5548aea0da167e7f6917bf40c02fbc971773ef181b1c7e",
    ),
    "a90ctl.py": (
        16_380,
        "4d72b87b42ef49c5997ddcd24d0c6bb4fe94766c2c7fddaa21b07ff218009f8c",
    ),
    "native_init_flash.py": (
        43_118,
        "366dd38304625d37607916e92ea98a95271bbc4d9dfdc7eea106a5437b6dfe53",
    ),
}
MAX_LOG_BYTES = 16 * 1024 * 1024


@dataclass(frozen=True)
class LiveSnapshot:
    target_evidence_sha256: str
    boot_id: str
    version: str
    build: str
    boot_identity_sha256: str
    device_safety_state: str
    recovery_available: bool
    other_targets_untouched: bool
    receipt_sha256: str


@dataclass(frozen=True)
class EffectResult:
    returncode: int
    released: bool
    quiescent: bool
    pid: int
    process_group: int
    stdout_sha256: str
    stderr_sha256: str
    duration_ms: int

    def payload(self) -> dict[str, Any]:
        return {
            "returncode": self.returncode,
            "released": self.released,
            "quiescent": self.quiescent,
            "pid": self.pid,
            "processGroup": self.process_group,
            "stdoutSha256": self.stdout_sha256,
            "stderrSha256": self.stderr_sha256,
            "durationMs": self.duration_ms,
        }


class Backend(Protocol):
    def preflight(self, manifest: dict[str, Any]) -> LiveSnapshot: ...

    def run_candidate(
        self,
        manifest: dict[str, Any],
        journal: Journal,
        bindings: "ExecutionBindings",
        approval_binding_sha256: str,
    ) -> EffectResult: ...

    def run_rollback(
        self,
        manifest: dict[str, Any],
        journal: Journal,
        bindings: "ExecutionBindings",
        approval_binding_sha256: str,
    ) -> EffectResult: ...

    def observe(self, expected: dict[str, Any]) -> LiveSnapshot: ...


class ExecutionBindings:
    def __init__(self, artifacts: dict[str, BoundArtifact]) -> None:
        self.artifacts = artifacts

    def checkpoint(self) -> dict[str, Any]:
        return {
            name: self.artifacts[name].checkpoint()
            for name in sorted(self.artifacts)
        }

    def close(self) -> None:
        for artifact in self.artifacts.values():
            artifact.close()

    def __enter__(self) -> "ExecutionBindings":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


def _load_exact_python_module(bound: BoundArtifact, module_name: str) -> Any:
    source = os.pread(bound.fd, bound.identity["size"], 0)
    if len(source) != bound.identity["size"]:
        raise ContractError("exact module source read is incomplete")
    namespace: dict[str, Any] = {
        "__name__": module_name,
        "__file__": str(bound.path),
        "__package__": "",
        "__cached__": None,
    }
    exec(compile(source, str(bound.path), "exec", dont_inherit=True), namespace)
    return type("ExactModule", (), namespace)


def helper_runtime_digest() -> str:
    digest = hashlib.sha256()
    for name in sorted(HELPER_SPECS):
        size, sha256 = HELPER_SPECS[name]
        digest.update(f"{name}\0{size}\0{sha256}\n".encode("ascii"))
    return digest.hexdigest()


def owner_source_closure() -> dict[str, dict[str, Any]]:
    members = {
        Path(__file__).resolve(),
        Path(__file__).with_name("a90_boot_only_f1_contract_v1.py").resolve(),
        REPO_ROOT / "tests/test_a90_boot_only_f1_owner_v1.py",
    }
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(members):
        raw = path.read_bytes()
        result[str(path.relative_to(REPO_ROOT))] = {
            "size": len(raw),
            "sha256": sha256_bytes(raw),
        }
    for name, (size, sha256) in sorted(HELPER_SPECS.items()):
        result[f"workspace/public/src/scripts/revalidation/{name}"] = {
            "size": size,
            "sha256": sha256,
        }
    return result


def owner_closure_sha256() -> str:
    closure = owner_source_closure()
    digest = hashlib.sha256()
    for path in sorted(closure):
        item = closure[path]
        digest.update(f"{path}\0{item['size']}\0{item['sha256']}\n".encode("ascii"))
    return digest.hexdigest()


def validate_local_manifest_bindings(manifest: dict[str, Any]) -> None:
    if manifest["ownerClosureSha256"] != owner_closure_sha256():
        raise ContractError("manifest selected another owner closure")
    helper_size, helper_sha256 = HELPER_SPECS["native_init_flash.py"]
    if manifest["flashHelper"] != {
        "path": str(HELPER_PATH),
        "size": helper_size,
        "sha256": helper_sha256,
    }:
        raise ContractError("manifest selected another flash helper")


def validate_snapshot(
    snapshot: LiveSnapshot,
    expected: dict[str, Any],
    *,
    require_healthy: bool = True,
) -> None:
    for value, label in (
        (snapshot.target_evidence_sha256, "target evidence"),
        (snapshot.boot_identity_sha256, "boot identity"),
        (snapshot.receipt_sha256, "health receipt"),
    ):
        require_sha(value, label)
    require_string(snapshot.boot_id, "boot ID")
    if (snapshot.version, snapshot.build, snapshot.boot_identity_sha256) != (
        expected["version"],
        expected["build"],
        expected.get("bootIdentitySha256", snapshot.boot_identity_sha256),
    ):
        raise ContractError("live resident does not equal the expected identity")
    if require_healthy and snapshot.device_safety_state != "RESIDENT_HEALTHY":
        raise ContractError("live resident is not healthy")
    if snapshot.recovery_available is not True:
        raise ContractError("physical recovery is not available")
    if snapshot.other_targets_untouched is not True:
        raise ContractError("other-target isolation is not proved")


def _bound_artifacts(
    manifest: dict[str, Any],
    runtime_qualification: dict[str, Any],
) -> ExecutionBindings:
    invoking_uid = os.getuid()
    invoking_gid = os.getgid()
    runtime = validate_runtime_qualification(
        runtime_qualification, manifest["ownerClosureSha256"]
    )
    artifacts: dict[str, BoundArtifact] = {}
    try:
        for role in ("candidate", "rollback"):
            item = manifest[role]
            path = Path(item["path"])
            artifacts[role] = BoundArtifact.open(
                role=role,
                path=path,
                expected_size=item["size"],
                expected_sha256=item["sha256"],
                anchor=REPO_ROOT,
                expected_uid=invoking_uid,
                expected_gid=invoking_gid,
            )
        helper = manifest["flashHelper"]
        if Path(helper["path"]) != HELPER_PATH:
            raise ContractError("manifest selected another flash helper")
        for name, (size, sha256) in sorted(HELPER_SPECS.items()):
            artifacts[f"helper:{name}"] = BoundArtifact.open(
                role=f"helper:{name}",
                path=REVALIDATION / name,
                expected_size=size,
                expected_sha256=sha256,
                anchor=REPO_ROOT,
                expected_uid=invoking_uid,
                expected_gid=invoking_gid,
            )
        for role, path, qualified in (
            ("python-interpreter", PYTHON_EXECUTABLE, runtime["python"]),
            ("adb-transport", ADB_EXECUTABLE, runtime["adb"]),
        ):
            if qualified["path"] != str(path):
                raise ContractError(f"{role} runtime qualification path mismatch")
            artifacts[role] = BoundArtifact.open(
                role=role,
                path=path,
                expected_size=qualified["size"],
                expected_sha256=qualified["sha256"],
                anchor=Path("/"),
                expected_uid=0,
                expected_gid=0,
                executable=True,
            )
            artifacts[role].identity.update(
                {
                    "versionReceiptSha256": qualified["versionReceiptSha256"],
                    "runtimeClosureSha256": qualified["runtimeClosureSha256"],
                }
            )
        return ExecutionBindings(artifacts)
    except BaseException:
        for artifact in artifacts.values():
            artifact.close()
        raise


def _approval_binding(
    manifest: dict[str, Any],
    manifest_sha256: str,
    run_id: str,
    journal_namespace: str,
    snapshot: LiveSnapshot,
    nonce: str,
    expires_at: str,
    bindings: ExecutionBindings,
) -> dict[str, Any]:
    require_string(run_id, "run ID")
    require_string(journal_namespace, "journal namespace")
    require_string(nonce, "approval nonce")
    parse_utc(expires_at, "approval expiry")
    checkpoint = bindings.checkpoint()
    return {
        "schema": APPROVAL_BINDING_SCHEMA,
        "capability": CAPABILITY,
        "targetProfile": manifest["targetProfile"],
        "targetEvidenceSha256": snapshot.target_evidence_sha256,
        "bootId": snapshot.boot_id,
        "runId": run_id,
        "journalNamespace": journal_namespace,
        "manifestSha256": manifest_sha256,
        "candidateSha256": manifest["candidate"]["sha256"],
        "rollbackSha256": manifest["rollback"]["sha256"],
        "flashHelperSha256": manifest["flashHelper"]["sha256"],
        "ownerClosureSha256": manifest["ownerClosureSha256"],
        "helperRuntimeClosureSha256": HELPER_RUNTIME_CLOSURE_SHA256,
        "pythonExecutableIdentity": checkpoint["python-interpreter"],
        "adbExecutableIdentity": checkpoint["adb-transport"],
        "acceptanceRuleSha256": manifest["observation"]["acceptanceRuleSha256"],
        "observationTimeoutSec": manifest["timeouts"]["healthSec"],
        "recoveryPlan": manifest["recovery"]["plan"],
        "hazards": [
            {
                "id": hazard["id"],
                "qualificationSha256": hazard["qualificationSha256"],
            }
            for hazard in manifest["hazards"]
        ],
        "nonce": nonce,
        "expiresAt": expires_at,
    }


def validate_approval(
    value: Any,
    expected_binding: dict[str, Any],
    supplied_token: str,
    *,
    now: str | None = None,
) -> str:
    approval = require_object(
        value,
        frozenset({"schema", "binding", "bindingSha256", "token", "consumed"}),
        "approval",
    )
    if approval["schema"] != APPROVAL_SCHEMA or approval["binding"] != expected_binding:
        raise ContractError("approval binding mismatch")
    binding_sha = sha256_bytes(canonical_json(expected_binding))
    if approval["bindingSha256"] != binding_sha:
        raise ContractError("approval binding SHA256 mismatch")
    expected_token = approval_token(binding_sha)
    if approval["token"] != expected_token or supplied_token != expected_token:
        raise ContractError("approval token mismatch")
    if approval["consumed"] is not False:
        raise ContractError("approval is already consumed")
    current = parse_utc(now or utc_now(), "approval current time")
    if current >= parse_utc(expected_binding["expiresAt"], "approval expiry"):
        raise ContractError("approval expired")
    return binding_sha


def build_success_payload(
    manifest: dict[str, Any],
    manifest_sha256: str,
    run_id: str,
    journal_namespace: str,
    approval_binding_sha256: str,
    snapshot: LiveSnapshot,
) -> dict[str, Any]:
    payload = {
        "schema": "resident-install-terminal-v1",
        "terminal": SUCCESS_TERMINAL,
        "targetEvidenceSha256": snapshot.target_evidence_sha256,
        "runId": run_id,
        "journalNamespace": journal_namespace,
        "manifestSha256": manifest_sha256,
        "candidateSha256": manifest["candidate"]["sha256"],
        "expectedVersion": manifest["candidate"]["version"],
        "expectedBuild": manifest["candidate"]["build"],
        "observedVersion": snapshot.version,
        "observedBuild": snapshot.build,
        "ownerClosureSha256": manifest["ownerClosureSha256"],
        "approvalBindingSha256": approval_binding_sha256,
        "observationResult": "ACCEPTED",
        "acceptanceRuleSha256": manifest["observation"]["acceptanceRuleSha256"],
        "hazards": [
            {
                "id": hazard["id"],
                "qualificationSha256": hazard["qualificationSha256"],
                "accepted": True,
            }
            for hazard in manifest["hazards"]
        ],
        "finalHealth": "RESIDENT_HEALTHY",
        "finalHealthReceiptSha256": snapshot.receipt_sha256,
    }
    validate_terminal_payload(
        payload,
        manifest,
        manifest_sha256,
        run_id=run_id,
        journal_namespace=journal_namespace,
    )
    return payload


class OwnerEngine:
    def __init__(
        self,
        *,
        manifest_raw: bytes,
        manifest: dict[str, Any],
        run_id: str,
        journal_namespace: str,
        run_directory: Path,
        backend: Backend,
        bindings: ExecutionBindings,
    ) -> None:
        self.manifest_raw = manifest_raw
        self.manifest = validate_manifest(manifest)
        if parse_canonical_bytes(manifest_raw, "manifest") != self.manifest:
            raise ContractError("manifest bytes and parsed object differ")
        self.manifest_sha256 = sha256_bytes(manifest_raw)
        validate_local_manifest_bindings(self.manifest)
        self.run_id = run_id
        self.journal_namespace = journal_namespace
        expected_namespace = f"boot-only-f1-v1-{self.manifest_sha256}-{self.run_id}"
        if self.journal_namespace != expected_namespace:
            raise ContractError("journal namespace is not derived from manifest and run")
        self.run_directory = run_directory
        _prepare_fresh_run_directory(run_directory)
        self.backend = backend
        self.bindings = bindings
        self.journal = Journal(run_directory / "journal", run_id, self.manifest_sha256)

    def execute(
        self,
        approval: dict[str, Any],
        supplied_token: str,
        *,
        nonce: str,
        expires_at: str,
        now: str | None = None,
    ) -> dict[str, Any]:
        if self.journal.read():
            raise ContractError("fresh execution requires an empty journal")
        start = self.backend.preflight(self.manifest)
        validate_snapshot(start, self.manifest["expectedStart"])
        expected_binding = _approval_binding(
            self.manifest,
            self.manifest_sha256,
            self.run_id,
            self.journal_namespace,
            start,
            nonce,
            expires_at,
            self.bindings,
        )
        binding_sha = validate_approval(
            approval,
            expected_binding,
            supplied_token,
            now=now,
        )
        self.journal.append(
            "PREPARED",
            {
                "implementationStatus": IMPLEMENTATION_STATUS,
                "ownerClosureSha256": self.manifest["ownerClosureSha256"],
                "artifactCheckpoint": self.bindings.checkpoint(),
                "targetEvidenceSha256": start.target_evidence_sha256,
            },
        )
        self.journal.append(
            "APPROVED",
            {
                "approvalBindingSha256": binding_sha,
                "approvalTokenSha256": sha256_bytes(supplied_token.encode("ascii")),
                "approvalConsumed": True,
            },
        )
        pre_intent = self.backend.preflight(self.manifest)
        validate_snapshot(pre_intent, self.manifest["expectedStart"])
        if (
            pre_intent.target_evidence_sha256 != start.target_evidence_sha256
            or pre_intent.boot_id != start.boot_id
            or _approval_binding(
                self.manifest,
                self.manifest_sha256,
                self.run_id,
                self.journal_namespace,
                pre_intent,
                nonce,
                expires_at,
                self.bindings,
            )
            != expected_binding
        ):
            raise ContractError("live approval binding drifted before candidate intent")
        self.bindings.checkpoint()
        self.journal.append(
            "CANDIDATE_INTENT",
            {
                "approvalBindingSha256": binding_sha,
                "candidateSha256": self.manifest["candidate"]["sha256"],
                "partition": "boot",
                "attempt": 1,
                "candidateReplay": False,
                "rollbackPreauthorized": True,
            },
        )
        candidate = self.backend.run_candidate(
            self.manifest, self.journal, self.bindings, binding_sha
        )
        if not candidate.quiescent:
            return self._recovery_required(
                "CANDIDATE_PROCESS_GROUP_NOT_QUIESCENT", binding_sha
            )
        if not candidate.released:
            return self._rollback(binding_sha, "CANDIDATE_RETURN_UNCERTAIN")
        self.journal.append(
            "CANDIDATE_RESULT",
            {"approvalBindingSha256": binding_sha, "result": candidate.payload()},
        )
        self.bindings.checkpoint()
        if candidate.returncode == 0:
            try:
                final = self.backend.observe(self.manifest["candidate"])
                validate_snapshot(final, self.manifest["candidate"])
            except Exception:
                return self._rollback(binding_sha, "CANDIDATE_HEALTH_UNPROVED")
            payload = build_success_payload(
                self.manifest,
                self.manifest_sha256,
                self.run_id,
                self.journal_namespace,
                binding_sha,
                final,
            )
            self.journal.append(SUCCESS_TERMINAL, payload)
            result = {
                "schema": RESULT_SCHEMA,
                "status": SUCCESS_TERMINAL,
                "experimentProof": "PROVED",
                "deviceSafetyState": "RESIDENT_HEALTHY",
                "candidateAttemptCount": 1,
                "rollbackAttemptCount": 0,
                "candidateReplay": False,
                "terminalPayloadSha256": sha256_bytes(canonical_json(payload)),
            }
            validate_result(result)
            publish_exclusive(self.run_directory / "result.json", result)
            return result
        return self._rollback(binding_sha, "CANDIDATE_HELPER_FAILED")

    def _rollback(self, binding_sha: str, reason: str) -> dict[str, Any]:
        self.bindings.checkpoint()
        self.journal.append(
            "ROLLBACK_INTENT",
            {
                "approvalBindingSha256": binding_sha,
                "rollbackSha256": self.manifest["rollback"]["sha256"],
                "attempt": 1,
                "reason": reason,
                "rollbackReplay": False,
            },
        )
        rollback = self.backend.run_rollback(
            self.manifest, self.journal, self.bindings, binding_sha
        )
        if not rollback.released or not rollback.quiescent:
            self.journal.append(
                "ROLLBACK_RELEASE_UNCERTAIN",
                {
                    "approvalBindingSha256": binding_sha,
                    "reason": "ROLLBACK_RETURN_UNCERTAIN",
                    "result": rollback.payload(),
                },
            )
            return self._recovery_required("ROLLBACK_RETURN_UNCERTAIN", binding_sha)
        self.journal.append(
            "ROLLBACK_RESULT",
            {"approvalBindingSha256": binding_sha, "result": rollback.payload()},
        )
        self.bindings.checkpoint()
        if rollback.returncode == 0:
            try:
                final = self.backend.observe(self.manifest["rollback"])
                validate_snapshot(final, self.manifest["rollback"])
            except Exception:
                return self._recovery_required("ROLLBACK_HEALTH_UNPROVED", binding_sha)
            payload = {
                "approvalBindingSha256": binding_sha,
                "reason": reason,
                "deviceSafetyState": "RESIDENT_HEALTHY",
                "experimentProof": "NO_PROOF_OBSERVER",
                "finalHealthReceiptSha256": final.receipt_sha256,
                "candidateReplay": False,
                "rollbackReplay": False,
            }
            self.journal.append(ROLLBACK_TERMINAL, payload)
            result = {
                "schema": RESULT_SCHEMA,
                "status": ROLLBACK_TERMINAL,
                "experimentProof": "NO_PROOF_OBSERVER",
                "deviceSafetyState": "RESIDENT_HEALTHY",
                "candidateAttemptCount": 1,
                "rollbackAttemptCount": 1,
                "candidateReplay": False,
                "terminalPayloadSha256": sha256_bytes(canonical_json(payload)),
            }
            validate_result(result)
            publish_exclusive(self.run_directory / "result.json", result)
            return result
        return self._recovery_required("ROLLBACK_HELPER_FAILED", binding_sha)

    def _recovery_required(
        self, reason: str, approval_binding_sha256: str
    ) -> dict[str, Any]:
        records = self.journal.read()
        rollback_attempts = sum(
            record["state"] == "ROLLBACK_LAUNCHED" for record in records
        )
        payload = {
            "approvalBindingSha256": approval_binding_sha256,
            "reason": reason,
            "deviceSafetyState": "RECOVERY_REQUIRED",
            "experimentProof": "NO_PROOF_OBSERVER",
            "candidateReplay": False,
            "rollbackReplay": False,
        }
        self.journal.append(RECOVERY_TERMINAL, payload)
        result = {
            "schema": RESULT_SCHEMA,
            "status": RECOVERY_TERMINAL,
            "experimentProof": "NO_PROOF_OBSERVER",
            "deviceSafetyState": "RECOVERY_REQUIRED",
            "candidateAttemptCount": 1,
            "rollbackAttemptCount": rollback_attempts,
            "candidateReplay": False,
            "terminalPayloadSha256": sha256_bytes(canonical_json(payload)),
        }
        validate_result(result)
        publish_exclusive(self.run_directory / "result.json", result)
        return result


class SubprocessBackend:
    """Production backend shape; live construction remains activation-blocked."""

    def __init__(self, bindings: ExecutionBindings, run_directory: Path) -> None:
        if LIVE_EXECUTION_ENABLED is not True:
            raise ContractError("subprocess backend is H0-disabled")
        self.bindings = bindings
        self.run_directory = run_directory
        self.fd_exec = _load_exact_python_module(
            bindings.artifacts["helper:a90_boot_only_f1_fd_exec.py"],
            "a90_boot_only_f1_fd_exec_bound",
        )

    def preflight(self, manifest: dict[str, Any]) -> LiveSnapshot:
        raise ContractError("production target preflight is not implemented")

    def observe(self, expected: dict[str, Any]) -> LiveSnapshot:
        raise ContractError("production final-health observer is not implemented")

    def run_candidate(
        self,
        manifest: dict[str, Any],
        journal: Journal,
        bindings: ExecutionBindings,
        approval_binding_sha256: str,
    ) -> EffectResult:
        return self._run_helper(
            manifest["candidate"],
            manifest,
            journal,
            bindings,
            approval_binding_sha256,
            False,
        )

    def run_rollback(
        self,
        manifest: dict[str, Any],
        journal: Journal,
        bindings: ExecutionBindings,
        approval_binding_sha256: str,
    ) -> EffectResult:
        return self._run_helper(
            manifest["rollback"],
            manifest,
            journal,
            bindings,
            approval_binding_sha256,
            True,
        )

    def _run_helper(
        self,
        image: dict[str, Any],
        manifest: dict[str, Any],
        journal: Journal,
        bindings: ExecutionBindings,
        approval_binding_sha256: str,
        rollback: bool,
    ) -> EffectResult:
        role = "rollback" if rollback else "candidate"
        bindings.checkpoint()
        bootstrap = bindings.artifacts["helper:a90_boot_only_f1_helper_bootstrap.py"]
        stdout_path = self.run_directory / f"{role}.stdout"
        stderr_path = self.run_directory / f"{role}.stderr"
        output_flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
        stdout_fd = os.open(stdout_path, output_flags, 0o600)
        stderr_fd = os.open(stderr_path, output_flags, 0o600)
        gate_read, gate_write = os.pipe2(os.O_CLOEXEC)
        arguments = (
            image["path"],
            "--adb",
            str(ADB_EXECUTABLE),
            "--from-native",
            "--expect-version",
            image["version"],
            "--expect-sha256",
            image["sha256"],
            "--expect-readback-sha256",
            image["sha256"],
            "--verify-protocol",
            "selftest",
            "--recovery-timeout",
            str(manifest["timeouts"]["recoverySec"]),
            "--bridge-timeout",
            str(manifest["timeouts"]["bridgeSec"]),
        )
        command = self.fd_exec.bootstrap_command(
            PYTHON_EXECUTABLE,
            bootstrap.fd,
            BOOTSTRAP_PATH,
            bootstrap.identity["size"],
            bootstrap.identity["sha256"],
            arguments,
        )
        started = time.monotonic()
        pid = os.fork()
        if pid == 0:
            try:
                os.setpgid(0, 0)
                os.close(gate_write)
                token = os.read(gate_read, 2)
                os.close(gate_read)
                if token != b"R":
                    os._exit(125)
                os.dup2(stdout_fd, 1)
                os.dup2(stderr_fd, 2)
                resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_LOG_BYTES, MAX_LOG_BYTES))
                os.set_inheritable(bootstrap.fd, True)
                keep = {0, 1, 2, bootstrap.fd}
                upper = min(resource.getrlimit(resource.RLIMIT_NOFILE)[0], 1 << 20)
                for descriptor in range(3, int(upper)):
                    if descriptor not in keep:
                        try:
                            os.close(descriptor)
                        except OSError:
                            pass
                environment = {
                    "HOME": "/nonexistent",
                    "LANG": "C",
                    "LC_ALL": "C",
                    "PATH": "/usr/bin:/bin",
                    "PYTHONHASHSEED": "0",
                }
                os.execve(PYTHON_EXECUTABLE, command, environment)
            except BaseException:
                os._exit(126)
        os.close(gate_read)
        launch_state = "ROLLBACK_LAUNCHED" if rollback else "CANDIDATE_LAUNCHED"
        try:
            journal.append(
                launch_state,
                {
                    "approvalBindingSha256": approval_binding_sha256,
                    "pid": pid,
                    "processGroup": pid,
                    "releaseGateWriteFd": gate_write,
                    "stdoutPath": str(stdout_path),
                    "stderrPath": str(stderr_path),
                    "artifactCheckpoint": bindings.checkpoint(),
                },
            )
        except BaseException:
            os.close(gate_write)
            _reap_unreleased_child(pid)
            os.close(stdout_fd)
            os.close(stderr_fd)
            raise
        try:
            released = os.write(gate_write, b"R") == 1
        except OSError:
            released = False
        finally:
            os.close(gate_write)
        deadline = time.monotonic() + manifest["timeouts"]["recoverySec"]
        status: int | None = None
        while time.monotonic() < deadline:
            waited, current = os.waitpid(pid, os.WNOHANG)
            if waited == pid:
                status = current
                break
            time.sleep(0.05)
        if status is None:
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            _waited, status = os.waitpid(pid, 0)
        returncode = os.waitstatus_to_exitcode(status)
        quiescent = not _process_group_exists(pid)
        duration_ms = int((time.monotonic() - started) * 1000)
        try:
            stdout_sha256 = _finalize_log(stdout_fd, stdout_path)
            stderr_sha256 = _finalize_log(stderr_fd, stderr_path)
            return EffectResult(
                returncode=returncode,
                released=released,
                quiescent=quiescent,
                pid=pid,
                process_group=pid,
                stdout_sha256=stdout_sha256,
                stderr_sha256=stderr_sha256,
                duration_ms=duration_ms,
            )
        finally:
            os.close(stdout_fd)
            os.close(stderr_fd)


def _prepare_fresh_run_directory(path: Path) -> None:
    if not path.is_absolute():
        raise ContractError("run directory is not absolute")
    try:
        os.mkdir(path, 0o700)
    except FileExistsError as exc:
        raise ContractError("fresh run directory already exists") from exc
    metadata = path.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or path.is_symlink()
        or metadata.st_uid != os.getuid()
        or metadata.st_gid != os.getgid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise ContractError("fresh run directory identity mismatch")
    parent_fd = os.open(path.parent, os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def _reap_unreleased_child(pid: int) -> None:
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        waited, _status = os.waitpid(pid, os.WNOHANG)
        if waited == pid:
            return
        time.sleep(0.01)
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    os.waitpid(pid, 0)


def _finalize_log(fd: int, path: Path) -> str:
    os.fsync(fd)
    metadata = os.fstat(fd)
    path_metadata = path.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or not stat.S_ISREG(path_metadata.st_mode)
        or (metadata.st_dev, metadata.st_ino)
        != (path_metadata.st_dev, path_metadata.st_ino)
        or metadata.st_nlink != 1
        or path_metadata.st_nlink != 1
        or metadata.st_uid != os.getuid()
        or metadata.st_gid != os.getgid()
        or metadata.st_size > MAX_LOG_BYTES
    ):
        raise ContractError("helper log identity mismatch")
    return BoundArtifact._hash_fd(fd, metadata.st_size)


def _process_group_exists(process_group: int) -> bool:
    for entry in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = entry.read_text(encoding="ascii").split()
            if len(fields) > 4 and int(fields[4], 10) == process_group:
                return True
        except (OSError, UnicodeError, ValueError):
            continue
    return False


def audit(manifest_path: Path, run_directory: Path) -> dict[str, Any]:
    raw, value = load_canonical(manifest_path, "manifest")
    validate_manifest(value)
    manifest_sha = sha256_bytes(raw)
    run_id = run_directory.name
    journal = Journal(run_directory / "journal", run_id, manifest_sha)
    records = journal.read()
    last = records[-1]["state"] if records else None
    if last in {SUCCESS_TERMINAL, ROLLBACK_TERMINAL, RECOVERY_TERMINAL}:
        disposition = "TERMINAL"
    elif last in {"CANDIDATE_INTENT", "CANDIDATE_LAUNCHED", "CANDIDATE_RESULT"}:
        disposition = "CANDIDATE_CONSUMED_ROLLBACK_ONLY"
    elif last == "ROLLBACK_INTENT":
        disposition = "SAME_BOUND_ROLLBACK_MAY_LAUNCH"
    elif last in {"ROLLBACK_LAUNCHED", "ROLLBACK_RELEASE_UNCERTAIN"}:
        disposition = "ROLLBACK_CONSUMED_OBSERVE_ONLY"
    else:
        disposition = "NO_EFFECT_OR_EMPTY"
    return {
        "schema": "a90-boot-only-f1-audit-v1",
        "implementationStatus": IMPLEMENTATION_STATUS,
        "recordCount": len(records),
        "lastState": last,
        "disposition": disposition,
        "candidateReplayAllowed": False,
        "liveExecutionEnabled": LIVE_EXECUTION_ENABLED,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="A90 reusable boot-only F1 owner")
    subparsers = result.add_subparsers(dest="action", required=True)
    validate = subparsers.add_parser("validate-manifest")
    validate.add_argument("manifest", type=Path)
    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("manifest", type=Path)
    audit_parser.add_argument("run_directory", type=Path)
    execute = subparsers.add_parser("execute")
    execute.add_argument("manifest", type=Path)
    execute.add_argument("--operator-attended", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.action == "validate-manifest":
        raw, value = load_canonical(args.manifest, "manifest")
        validate_manifest(value)
        validate_local_manifest_bindings(value)
        print(
            json.dumps(
                {
                    "status": "VALID_H0_MANIFEST",
                    "manifestSha256": sha256_bytes(raw),
                    "ownerClosureSha256": owner_closure_sha256(),
                    "liveExecutionEnabled": LIVE_EXECUTION_ENABLED,
                },
                sort_keys=True,
            )
        )
        return 0
    if args.action == "audit":
        print(json.dumps(audit(args.manifest, args.run_directory), sort_keys=True))
        return 0
    if args.action == "execute":
        if args.operator_attended is not True:
            raise ContractError("A90 F1 is attended-only")
        raise ContractError(
            "live execution remains blocked: recovery/resume and runtime qualification absent"
        )
    raise ContractError("unknown owner action")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"A90_BOOT_ONLY_F1_OWNER_V1 NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2)
