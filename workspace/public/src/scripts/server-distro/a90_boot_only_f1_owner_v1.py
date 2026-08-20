#!/usr/bin/env python3
"""Reusable boot-only A90 F1 transaction owner.

The current generation is H0 implementation only.  Its strict data and state
machine are executable in host tests, but the production CLI deliberately
rejects live execution until recovery/resume and runtime-closure qualification
are implemented and independently reviewed.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import resource
import signal
import stat
import subprocess
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
    validate_hazard_qualification,
    validate_recovery_qualification,
    validate_resident_qualification,
    validate_result,
    validate_terminal_payload,
)
from a90_boot_only_f1_runtime_v1 import verify_runtime_qualification_current
import a90_boot_only_f1_observer_v1 as observer_v1


IMPLEMENTATION_STATUS = (
    "H0_RUNTIME_QUALIFIED_STABLE_SOURCE_PACKAGE_BRIDGE_OBSERVATION_WORKER_"
    "CORE_PRESENT_"
    "RECOVERY_BINDING_AND_RESUME_ABSENT"
)
LIVE_EXECUTION_ENABLED = False
PYTHON_EXECUTABLE = Path("/usr/bin/python3.14")
ADB_EXECUTABLE = Path("/usr/lib/android-sdk/platform-tools/adb")
REPO_ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = REPO_ROOT / "workspace/public/src/scripts/revalidation"
FD_EXEC_PATH = REVALIDATION / "a90_boot_only_f1_fd_exec.py"
SOURCE_PACKAGE_PATH = REVALIDATION / "a90_boot_only_f1_source_package_v1.py"
HELPER_PATH = SOURCE_PACKAGE_PATH
RUNTIME_QUALIFICATION_PATH = (
    REPO_ROOT
    / "workspace/public/src/device-action/a90_boot_only_f1_runtime_qualification_v1.json"
)
FD_EXEC_SPEC = (
    3_689,
    "e35e667e4bdf6a87999d9ec7ac496d699cd8251974dfac17e71ddad6a0d66069",
)
SOURCE_PACKAGE_SPEC = (
    186_547,
    "68332b68f353c38456f81fa544f99b4c99b890feff416772d4630c174b5b4ae1",
)
HELPER_RUNTIME_CLOSURE_SHA256 = SOURCE_PACKAGE_SPEC[1]
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


@dataclass(frozen=True)
class CommandOutcome:
    command: list[str]
    rc: int
    status: str
    text: str


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
    def __init__(
        self,
        artifacts: dict[str, Any],
        qualifications: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.artifacts = artifacts
        self.qualifications = qualifications or {}

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


@dataclass
class HeldSourceArtifact:
    """One exact source capability executed only from its already-open FD.

    Repository ancestors are deliberately not treated as an execution
    boundary: neither the loader nor the package reopens this pathname.
    """

    role: str
    path: Path
    source_fd: int
    fd: int
    identity: dict[str, Any]

    @classmethod
    def open(
        cls,
        *,
        role: str,
        path: Path,
        expected_size: int,
        expected_sha256: str,
    ) -> "HeldSourceArtifact":
        if not path.is_absolute():
            raise ContractError("held source path is not absolute")
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        except OSError as exc:
            raise ContractError(f"held source cannot be opened: {role}") from exc
        sealed_fd = -1
        try:
            metadata = os.fstat(descriptor)
            path_metadata = path.lstat()
            digest = BoundArtifact._hash_fd(descriptor, expected_size)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or not stat.S_ISREG(path_metadata.st_mode)
                or metadata.st_nlink != 1
                or path_metadata.st_nlink != 1
                or metadata.st_uid != os.getuid()
                or metadata.st_gid != os.getgid()
                or path_metadata.st_uid != os.getuid()
                or path_metadata.st_gid != os.getgid()
                or (metadata.st_dev, metadata.st_ino)
                != (path_metadata.st_dev, path_metadata.st_ino)
                or metadata.st_size != expected_size
                or digest != expected_sha256
            ):
                raise ContractError(f"held source input mismatch: {role}")
            raw = os.pread(descriptor, expected_size, 0)
            if (
                len(raw) != expected_size
                or os.pread(descriptor, 1, expected_size)
                or sha256_bytes(raw) != expected_sha256
            ):
                raise ContractError(f"held source exact read mismatch: {role}")
            sealed_fd = os.memfd_create(
                f"a90-{role}", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING
            )
            offset = 0
            while offset < len(raw):
                written = os.write(sealed_fd, raw[offset:])
                if written <= 0:
                    raise ContractError(f"held source sealed copy failed: {role}")
                offset += written
            required_seals = (
                fcntl.F_SEAL_SEAL
                | fcntl.F_SEAL_SHRINK
                | fcntl.F_SEAL_GROW
                | fcntl.F_SEAL_WRITE
            )
            fcntl.fcntl(sealed_fd, fcntl.F_ADD_SEALS, required_seals)
            if fcntl.fcntl(sealed_fd, fcntl.F_GET_SEALS) != required_seals:
                raise ContractError(f"held source sealing failed: {role}")
            sealed_digest = BoundArtifact._hash_fd(sealed_fd, expected_size)
            if sealed_digest != expected_sha256:
                raise ContractError(f"held source sealed digest mismatch: {role}")
            return cls(
                role,
                path,
                descriptor,
                sealed_fd,
                {
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
                    "sealedSize": expected_size,
                    "sealedSha256": sealed_digest,
                    "sealedFlags": required_seals,
                },
            )
        except BaseException:
            os.close(descriptor)
            if sealed_fd >= 0:
                os.close(sealed_fd)
            raise

    def checkpoint(self) -> dict[str, Any]:
        metadata = os.fstat(self.source_fd)
        path_metadata = self.path.lstat()
        sealed_metadata = os.fstat(self.fd)
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
            "sha256": BoundArtifact._hash_fd(self.source_fd, metadata.st_size),
            "sealedSize": sealed_metadata.st_size,
            "sealedSha256": BoundArtifact._hash_fd(self.fd, sealed_metadata.st_size),
            "sealedFlags": fcntl.fcntl(self.fd, fcntl.F_GET_SEALS),
        }
        if (
            not stat.S_ISREG(metadata.st_mode)
            or not stat.S_ISREG(path_metadata.st_mode)
            or (metadata.st_dev, metadata.st_ino)
            != (path_metadata.st_dev, path_metadata.st_ino)
            or current != self.identity
        ):
            raise ContractError("held source identity or bytes drifted")
        return current

    def close(self) -> None:
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1
        if self.source_fd >= 0:
            os.close(self.source_fd)
            self.source_fd = -1


def bind_source_package() -> dict[str, HeldSourceArtifact]:
    artifacts: dict[str, HeldSourceArtifact] = {}
    try:
        artifacts["helper-fd-exec"] = HeldSourceArtifact.open(
            role="helper-fd-exec",
            path=FD_EXEC_PATH,
            expected_size=FD_EXEC_SPEC[0],
            expected_sha256=FD_EXEC_SPEC[1],
        )
        artifacts["helper-package"] = HeldSourceArtifact.open(
            role="helper-package",
            path=SOURCE_PACKAGE_PATH,
            expected_size=SOURCE_PACKAGE_SPEC[0],
            expected_sha256=SOURCE_PACKAGE_SPEC[1],
        )
        return artifacts
    except BaseException:
        for artifact in artifacts.values():
            artifact.close()
        raise


class OwnedBridgeLifecycle:
    """One owner-created bridge from held source bytes, with bounded teardown."""

    def __init__(
        self,
        bindings: ExecutionBindings,
        run_directory: Path,
        fd_exec: Any,
        *,
        popen_factory: Any = subprocess.Popen,
        endpoint_probe: Any = observer_v1.probe_endpoint_identity,
        listener_absence_probe: Any = observer_v1.prove_listener_absent,
        process_probe: Any = observer_v1.probe_bridge_identity,
        teardown_probe: Any = observer_v1.prove_bridge_absent,
        monotonic: Any = time.monotonic,
        sleep: Any = time.sleep,
    ) -> None:
        self.bindings = bindings
        self.run_directory = run_directory
        self.fd_exec = fd_exec
        self.popen_factory = popen_factory
        self.endpoint_probe = endpoint_probe
        self.listener_absence_probe = listener_absence_probe
        self.process_probe = process_probe
        self.teardown_probe = teardown_probe
        self.monotonic = monotonic
        self.sleep = sleep
        self.process: Any | None = None
        self.command: tuple[str, ...] | None = None
        self.endpoint: dict[str, Any] | None = None
        self.receipt: dict[str, Any] | None = None
        self.stdout_fd = -1
        self.stderr_fd = -1
        self.stdout_path = run_directory / "bridge.stdout"
        self.stderr_path = run_directory / "bridge.stderr"
        self.closed = False

    def _open_logs(self) -> None:
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
        self.stdout_fd = os.open(self.stdout_path, flags, 0o600)
        try:
            self.stderr_fd = os.open(self.stderr_path, flags, 0o600)
        except BaseException:
            os.close(self.stdout_fd)
            self.stdout_fd = -1
            raise

    def _reap(self, timeout_sec: float) -> tuple[int, bool]:
        assert self.process is not None
        forced = False
        if self.process.poll() is None:
            self.process.terminate()
        try:
            returncode = self.process.wait(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            forced = True
            self.process.kill()
            returncode = self.process.wait(timeout=timeout_sec)
        return returncode, forced

    def _close_logs(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for name, descriptor, path in (
            ("stdoutSha256", self.stdout_fd, self.stdout_path),
            ("stderrSha256", self.stderr_fd, self.stderr_path),
        ):
            if descriptor < 0:
                continue
            try:
                result[name] = _finalize_log(descriptor, path)
            finally:
                os.close(descriptor)
                if name == "stdoutSha256":
                    self.stdout_fd = -1
                else:
                    self.stderr_fd = -1
        return result

    def start(
        self,
        *,
        readiness_timeout_sec: float,
    ) -> dict[str, Any]:
        if self.process is not None or self.closed:
            raise ContractError("owned bridge lifecycle is not fresh")
        if type(readiness_timeout_sec) not in {int, float} or not (
            0 < readiness_timeout_sec <= 300
        ):
            raise ContractError("owned bridge readiness timeout is invalid")
        self.bindings.checkpoint()
        self.listener_absence_probe()
        self.endpoint = self.endpoint_probe()
        bridge = self.bindings.artifacts["helper-package"]
        arguments = (
            "bridge",
            "--host",
            "127.0.0.1",
            "--port",
            "54321",
            "--device",
            observer_v1.FIXED_BRIDGE_DEVICE,
            "--expect-realpath",
            self.endpoint["selectedRealpath"],
        )
        self.command = self.fd_exec.bootstrap_command(
            PYTHON_EXECUTABLE,
            bridge.fd,
            bridge.path,
            bridge.identity["size"],
            bridge.identity["sha256"],
            arguments,
        )
        self._open_logs()
        try:
            self.process = self.popen_factory(
                self.command,
                cwd="/",
                env={
                    "PATH": "/usr/bin:/bin",
                    "LANG": "C",
                    "LC_ALL": "C",
                    "PYTHONHASHSEED": "0",
                },
                stdin=subprocess.DEVNULL,
                stdout=self.stdout_fd,
                stderr=self.stderr_fd,
                close_fds=True,
                pass_fds=self.fd_exec.bootstrap_pass_fds(bridge.fd),
                start_new_session=True,
            )
            deadline = self.monotonic() + float(readiness_timeout_sec)
            last_error: ContractError | None = None
            while self.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise ContractError("owned bridge exited before readiness")
                try:
                    self.receipt = self.process_probe(
                        self.endpoint,
                        expected_pid=self.process.pid,
                        expected_command=self.command,
                    )
                    self.bindings.checkpoint()
                    return self.receipt
                except ContractError as exc:
                    last_error = exc
                    self.sleep(0.05)
            raise ContractError("owned bridge readiness timed out") from last_error
        except BaseException:
            try:
                if self.process is not None:
                    self._reap(2.0)
                    self.listener_absence_probe()
            finally:
                self._close_logs()
                self.closed = True
            raise

    def close(self, *, timeout_sec: float = 5.0) -> dict[str, Any]:
        if self.closed or self.process is None or self.receipt is None:
            raise ContractError("owned bridge cannot be closed from this state")
        if type(timeout_sec) not in {int, float} or not 0 < timeout_sec <= 30:
            raise ContractError("owned bridge close timeout is invalid")
        returncode: int | None = None
        forced = False
        logs: dict[str, str] = {}
        try:
            returncode, forced = self._reap(timeout_sec)
            self.teardown_probe(
                pid=self.receipt["bridgeProcessPid"],
                listener_inode=self.receipt["listenerSocketInode"],
                selected_realpath=self.receipt["selectedRealpath"],
            )
            self.bindings.checkpoint()
        finally:
            logs = self._close_logs()
            self.closed = True
        assert returncode is not None
        return {
            "bridgeReceiptSha256": self.receipt["receiptSha256"],
            "returncode": returncode,
            "forced": forced,
            **logs,
        }


OBSERVATION_COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("version", ("version",)),
    ("selftest", ("selftest",)),
    ("status", ("status",)),
    ("boot-id", ("cat", "/proc/sys/kernel/random/boot_id")),
)


class OwnedObservationWorker:
    """Run the complete fixed observation sequence in one isolated child."""

    def __init__(
        self,
        bindings: ExecutionBindings,
        run_directory: Path,
        fd_exec: Any,
        *,
        popen_factory: Any = subprocess.Popen,
        process_group_exists: Any = lambda process_group: _process_group_exists(
            process_group
        ),
        kill_group: Any = os.killpg,
    ) -> None:
        self.bindings = bindings
        self.run_directory = run_directory
        self.fd_exec = fd_exec
        self.popen_factory = popen_factory
        self.process_group_exists = process_group_exists
        self.kill_group = kill_group
        self.consumed = False

    def run(self, *, timeout_sec: int) -> dict[str, dict[str, Any]]:
        if self.consumed:
            raise ContractError("observation worker is already consumed")
        if type(timeout_sec) is not int or not 1 <= timeout_sec <= 300:
            raise ContractError("observation worker timeout is invalid")
        self.consumed = True
        self.bindings.checkpoint()
        bootstrap = self.bindings.artifacts["helper-package"]
        argv = self.fd_exec.bootstrap_command(
            PYTHON_EXECUTABLE,
            bootstrap.fd,
            bootstrap.path,
            bootstrap.identity["size"],
            bootstrap.identity["sha256"],
            ("observe", str(timeout_sec)),
        )
        stdout_path = self.run_directory / "observation-worker.stdout"
        stderr_path = self.run_directory / "observation-worker.stderr"
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
        stdout_fd = os.open(stdout_path, flags, 0o600)
        try:
            stderr_fd = os.open(stderr_path, flags, 0o600)
        except BaseException:
            os.close(stdout_fd)
            raise
        process: Any | None = None
        try:
            process = self.popen_factory(
                argv,
                cwd="/",
                env={
                    "HOME": str(REPO_ROOT),
                    "PATH": "/usr/bin:/bin",
                    "LANG": "C",
                    "LC_ALL": "C",
                    "PYTHONHASHSEED": "0",
                },
                stdin=subprocess.DEVNULL,
                stdout=stdout_fd,
                stderr=stderr_fd,
                close_fds=True,
                pass_fds=self.fd_exec.bootstrap_pass_fds(bootstrap.fd),
                start_new_session=True,
            )
            try:
                returncode = process.wait(
                    timeout=float(len(OBSERVATION_COMMANDS) * timeout_sec + 2)
                )
            except subprocess.TimeoutExpired as exc:
                try:
                    self.kill_group(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=2.0)
                raise ContractError("observation worker exceeded its bound") from exc
            if self.process_group_exists(process.pid):
                try:
                    self.kill_group(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                raise ContractError("observation worker left a surviving process group")
            self.bindings.checkpoint()
            stdout_sha256 = _finalize_log(stdout_fd, stdout_path)
            _stderr_sha256 = _finalize_log(stderr_fd, stderr_path)
            stdout_metadata = os.fstat(stdout_fd)
            raw = os.pread(stdout_fd, stdout_metadata.st_size, 0)
            if sha256_bytes(raw) != stdout_sha256:
                raise ContractError("observation worker stdout changed after fsync")
            value = parse_canonical_bytes(raw, "observation worker")
            worker = require_object(
                value,
                frozenset({"schema", "results"}),
                "observation worker",
            )
            results = worker["results"]
            if (
                worker["schema"] != "a90-boot-only-f1-observation-worker-v1"
                or type(results) is not list
                or len(results) != len(OBSERVATION_COMMANDS)
                or returncode != 0
            ):
                raise ContractError("observation worker envelope mismatch")
            receipts: dict[str, dict[str, Any]] = {}
            for index, (expected_label, command_tuple) in enumerate(
                OBSERVATION_COMMANDS
            ):
                result = require_object(
                    results[index],
                    frozenset({"label", "command", "rc", "status", "text"}),
                    f"observation worker result {index}",
                )
                expected_command = list(command_tuple)
                if (
                    result["label"] != expected_label
                    or result["command"] != expected_command
                    or type(result["rc"]) is not int
                    or result["rc"] != 0
                    or result["status"] != "ok"
                    or type(result["text"]) is not str
                    or not result["text"]
                ):
                    raise ContractError("observation worker result mismatch")
                outcome = CommandOutcome(
                    command=expected_command,
                    rc=result["rc"],
                    status=result["status"],
                    text=result["text"],
                )
                receipts[expected_label] = observer_v1.command_receipt(
                    expected_command, outcome
                )
            return receipts
        finally:
            os.close(stdout_fd)
            os.close(stderr_fd)


class OwnedObservationSession:
    """One bridge plus one fixed-order observation worker and teardown."""

    def __init__(
        self,
        bridge: OwnedBridgeLifecycle,
        worker: OwnedObservationWorker,
    ) -> None:
        self.bridge = bridge
        self.worker = worker

    def observe(
        self,
        expected: dict[str, Any],
        *,
        recovery_available: bool,
        bridge_timeout_sec: int,
        command_timeout_sec: int,
    ) -> observer_v1.ObservedHealth:
        bridge_receipt = self.bridge.start(
            readiness_timeout_sec=bridge_timeout_sec,
        )
        try:
            receipts = self.worker.run(timeout_sec=command_timeout_sec)
            value = {
                "schema": observer_v1.OBSERVER_SCHEMA,
                "bridge": bridge_receipt,
                "version": receipts["version"],
                "selftest": receipts["selftest"],
                "status": receipts["status"],
                "bootId": receipts["boot-id"],
            }
            return observer_v1.validate_observation_input(
                value,
                expected,
                recovery_available=recovery_available,
            )
        finally:
            self.bridge.close(timeout_sec=5.0)


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


def _read_bound_canonical(bound: BoundArtifact, label: str) -> tuple[bytes, Any]:
    raw = os.pread(bound.fd, bound.identity["size"], 0)
    if len(raw) != bound.identity["size"] or os.pread(
        bound.fd, 1, bound.identity["size"]
    ):
        raise ContractError(f"{label} exact read mismatch")
    return raw, parse_canonical_bytes(raw, label)


def helper_runtime_digest() -> str:
    return SOURCE_PACKAGE_SPEC[1]


def owner_source_closure() -> dict[str, dict[str, Any]]:
    members = {
        Path(__file__).resolve(),
        Path(__file__).with_name("a90_boot_only_f1_contract_v1.py").resolve(),
        Path(__file__).with_name("a90_boot_only_f1_runtime_v1.py").resolve(),
        Path(__file__).with_name("a90_boot_only_f1_observer_v1.py").resolve(),
    }
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(members):
        raw = path.read_bytes()
        result[str(path.relative_to(REPO_ROOT))] = {
            "size": len(raw),
            "sha256": sha256_bytes(raw),
        }
    for path, (size, sha256) in (
        (FD_EXEC_PATH, FD_EXEC_SPEC),
        (SOURCE_PACKAGE_PATH, SOURCE_PACKAGE_SPEC),
    ):
        result[str(path.relative_to(REPO_ROOT))] = {
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
    if manifest["flashHelper"] != {
        "path": str(HELPER_PATH),
        "size": SOURCE_PACKAGE_SPEC[0],
        "sha256": SOURCE_PACKAGE_SPEC[1],
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
    if (snapshot.version, snapshot.build) != (
        expected["version"],
        expected["build"],
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
    runtime = verify_runtime_qualification_current(
        runtime_qualification, manifest["ownerClosureSha256"]
    )
    artifacts: dict[str, BoundArtifact] = {}
    qualifications: dict[str, dict[str, Any]] = {}
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
        expected = manifest["expectedStart"]
        resident_path = Path(expected["residentQualificationPath"])
        artifacts["resident-qualification"] = BoundArtifact.open(
            role="resident-qualification",
            path=resident_path,
            expected_size=resident_path.lstat().st_size,
            expected_sha256=expected["residentQualificationSha256"],
            anchor=REPO_ROOT,
            expected_uid=invoking_uid,
            expected_gid=invoking_gid,
        )
        _resident_raw, resident_value = _read_bound_canonical(
            artifacts["resident-qualification"], "resident qualification"
        )
        validate_resident_qualification(
            resident_value, expected
        )
        qualifications["resident"] = resident_value
        recovery = manifest["recovery"]
        recovery_path = Path(recovery["qualificationPath"])
        artifacts["recovery-qualification"] = BoundArtifact.open(
            role="recovery-qualification",
            path=recovery_path,
            expected_size=recovery_path.lstat().st_size,
            expected_sha256=recovery["qualificationSha256"],
            anchor=REPO_ROOT,
            expected_uid=invoking_uid,
            expected_gid=invoking_gid,
        )
        _recovery_raw, recovery_value = _read_bound_canonical(
            artifacts["recovery-qualification"], "recovery qualification"
        )
        validate_recovery_qualification(recovery_value, manifest)
        qualifications["recovery"] = recovery_value
        for index, hazard in enumerate(manifest["hazards"]):
            hazard_path = Path(hazard["qualificationPath"])
            role = f"hazard-qualification:{hazard['id']}"
            artifacts[role] = BoundArtifact.open(
                role=role,
                path=hazard_path,
                expected_size=hazard_path.lstat().st_size,
                expected_sha256=hazard["qualificationSha256"],
                anchor=REPO_ROOT,
                expected_uid=invoking_uid,
                expected_gid=invoking_gid,
            )
            _hazard_raw, hazard_value = _read_bound_canonical(
                artifacts[role], f"hazard qualification {index}"
            )
            validate_hazard_qualification(
                hazard_value, hazard["id"]
            )
            qualifications[role] = hazard_value
        helper = manifest["flashHelper"]
        if Path(helper["path"]) != HELPER_PATH:
            raise ContractError("manifest selected another flash helper")
        artifacts.update(bind_source_package())
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
        return ExecutionBindings(artifacts, qualifications)
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
            bindings.artifacts["helper-fd-exec"],
            "a90_boot_only_f1_fd_exec_bound",
        )
        self.bridge = OwnedBridgeLifecycle(
            bindings,
            run_directory,
            self.fd_exec,
        )
        self.worker = OwnedObservationWorker(
            bindings,
            run_directory,
            self.fd_exec,
        )
        self.observation_session = OwnedObservationSession(
            self.bridge,
            self.worker,
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
        bootstrap = bindings.artifacts["helper-package"]
        stdout_path = self.run_directory / f"{role}.stdout"
        stderr_path = self.run_directory / f"{role}.stderr"
        output_flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
        stdout_fd = os.open(stdout_path, output_flags, 0o600)
        stderr_fd = os.open(stderr_path, output_flags, 0o600)
        gate_read, gate_write = os.pipe2(os.O_CLOEXEC)
        arguments = (
            "flash",
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
            SOURCE_PACKAGE_PATH,
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
            "live execution remains blocked: recovery binding and crash-prefix resume absent"
        )
    raise ContractError("unknown owner action")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"A90_BOOT_ONLY_F1_OWNER_V1 NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2)
