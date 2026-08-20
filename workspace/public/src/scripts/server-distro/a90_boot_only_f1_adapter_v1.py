#!/usr/bin/env python3
"""Small fixed adapter for the A90 minimal boot-only F1 state machine.

The adapter reuses the repository-managed Native serial bridge and
``native_init_flash.py``.  It does not start ADB outside the helper's recovery
window and exposes no caller-selected command, partition, endpoint, or retry.
Live subprocess construction remains disabled pending independent review.
"""

from __future__ import annotations

import json
import os
import re
import resource
import signal
import stat
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from a90_boot_only_f1_minimal_v1 import (
    ContractError,
    EffectResult,
    Snapshot,
    canonical_json,
    sha256_bytes,
)


LIVE_ADAPTER_ENABLED = False
REPO_ROOT = Path(__file__).resolve().parents[5]
PYTHON = Path("/usr/bin/python3.14")
ADB = Path("/usr/bin/adb")
BRIDGE = REPO_ROOT / "workspace/public/src/scripts/revalidation/a90_bridge.py"
A90CTL = REPO_ROOT / "workspace/public/src/scripts/revalidation/a90ctl.py"
FLASH = REPO_ROOT / "workspace/public/src/scripts/revalidation/native_init_flash.py"
FIXED_SERIAL = "/dev/serial/by-id/usb-A90-LNX_A90_Linux_ARM64_A90NATIVE001-if00"
MAX_OUTPUT_BYTES = 1 << 20
VERSION_RE = re.compile(r"^version: (?P<version>\S+) build=(?P<build>\S+)$")
SELFTEST_RE = re.compile(
    r"^selftest: pass=[0-9]+ warn=[0-9]+ fail=0 duration=[0-9]+ms entries=[1-9][0-9]*$"
)
BOOT_ID_RE = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
TTY_RE = re.compile(r"^/dev/ttyACM[0-9]+$")


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    quiescent: bool = True


class CommandRunner(Protocol):
    def run(self, label: str, argv: tuple[str, ...], timeout_sec: int) -> CommandResult: ...


class HostRunner:
    """Future production runner; construction is currently impossible."""

    def __init__(self, log_directory: Path) -> None:
        if LIVE_ADAPTER_ENABLED is not True:
            raise ContractError("A90 minimal live adapter is disabled")
        if not log_directory.is_absolute():
            raise ContractError("adapter log directory is not absolute")
        self.log_directory = log_directory
        self.sequence = 0

    def run(self, label: str, argv: tuple[str, ...], timeout_sec: int) -> CommandResult:
        if re.fullmatch(r"[a-z0-9-]{1,40}", label) is None:
            raise ContractError("adapter log label is invalid")
        self.sequence += 1
        prefix = f"{self.sequence:03d}-{label}"
        stdout_path = self.log_directory / f"{prefix}.stdout"
        stderr_path = self.log_directory / f"{prefix}.stderr"
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
        stdout_fd = os.open(stdout_path, flags, 0o600)
        stderr_fd = os.open(stderr_path, flags, 0o600)
        process: subprocess.Popen[bytes] | None = None
        timed_out = False
        try:
            process = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=stdout_fd,
                stderr=stderr_fd,
                cwd=REPO_ROOT,
                env={"HOME": "/nonexistent", "LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
                start_new_session=True,
                preexec_fn=_limit_child,
            )
            try:
                process.wait(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            os.fsync(stdout_fd)
            os.fsync(stderr_fd)
            stdout = _read_bound_log(stdout_fd)
            stderr = _read_bound_log(stderr_fd)
            _fsync_directory(self.log_directory)
            quiescent = not _process_group_exists(process.pid)
            return CommandResult(
                returncode=124 if timed_out else process.returncode,
                stdout=stdout,
                stderr=stderr,
                quiescent=quiescent,
            )
        finally:
            os.close(stdout_fd)
            os.close(stderr_fd)


def _limit_child() -> None:
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _read_bound_log(descriptor: int) -> bytes:
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_OUTPUT_BYTES:
        raise ContractError("adapter output exceeds its fixed bound")
    return os.pread(descriptor, metadata.st_size, 0)


def _process_group_exists(process_group: int) -> bool:
    try:
        os.killpg(process_group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ContractError("adapter JSON has a duplicate key")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise ContractError(f"adapter JSON contains non-finite number {value}")


def _json(raw: bytes, label: str) -> dict[str, Any]:
    if not raw or len(raw) > MAX_OUTPUT_BYTES:
        raise ContractError(f"{label} output envelope is invalid")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label} output is not JSON") from exc
    if type(value) is not dict:
        raise ContractError(f"{label} output is not an object")
    return value


def _one_line(text: str, pattern: re.Pattern[str], label: str) -> re.Match[str]:
    matches = [pattern.fullmatch(line.strip()) for line in text.replace("\r", "").splitlines()]
    exact = [match for match in matches if match is not None]
    if len(exact) != 1:
        raise ContractError(f"{label} is not unique")
    return exact[0]


def _validate_bridge(value: dict[str, Any]) -> dict[str, Any]:
    candidates = value.get("serial_candidates")
    pids = value.get("port_pids")
    if (
        value.get("wrapper_contract") != 1
        or value.get("bridge_process") != "running"
        or value.get("port_listening") is not True
        or value.get("ambiguous") is not False
        or type(candidates) is not list
        or len(candidates) != 1
        or type(candidates[0]) is not dict
        or candidates[0].get("path") != FIXED_SERIAL
        or candidates[0].get("exists") is not True
        or candidates[0].get("realpath") != value.get("selected_realpath")
        or value.get("selected_device") != FIXED_SERIAL
        or type(value.get("selected_realpath")) is not str
        or TTY_RE.fullmatch(value["selected_realpath"]) is None
        or type(pids) is not list
        or len(pids) != 1
        or type(pids[0]) is not int
        or pids[0] <= 0
        or value.get("bridge_probe") not in {"connected-no-immediate-error", "data"}
    ):
        raise ContractError("A90 bridge preflight is not exact")
    return {
        "selectedDevice": FIXED_SERIAL,
        "selectedRealpath": value["selected_realpath"],
        "bridgePid": pids[0],
    }


def _validate_command(value: dict[str, Any], command: list[str], label: str) -> str:
    if (
        set(value) != {"begin", "end", "rc", "status", "trust", "text"}
        or value.get("rc") != 0
        or type(value.get("rc")) is not int
        or value.get("status") != "ok"
        or value.get("trust") != "A90P1_V1_STRUCTURAL_ONLY"
        or type(value.get("text")) is not str
        or not value["text"]
        or type(value.get("end")) is not dict
        or value["end"].get("cmd") not in {None, command[0]}
    ):
        raise ContractError(f"{label} command receipt is invalid")
    return value["text"]


class FixedA90Adapter:
    def __init__(self, runner: CommandRunner, *, recovery_qualified: bool) -> None:
        if recovery_qualified is not True:
            raise ContractError("A90 physical recovery is not qualified")
        self.runner = runner

    def _json_command(self, label: str, argv: tuple[str, ...], timeout_sec: int) -> dict[str, Any]:
        result = self.runner.run(label, argv, timeout_sec)
        if (
            type(result.returncode) is not int
            or type(result.quiescent) is not bool
            or result.returncode != 0
            or not result.quiescent
        ):
            raise ContractError(f"{label} producer failed or survived")
        return _json(result.stdout, label)

    def _a90ctl(self, label: str, command: list[str], timeout_sec: int = 15) -> dict[str, Any]:
        argv = (
            str(PYTHON),
            str(A90CTL),
            "--json",
            "--timeout",
            str(timeout_sec),
            "--",
            *command,
        )
        return self._json_command(label, argv, timeout_sec + 5)

    def preflight(self, manifest: dict[str, Any]) -> Snapshot:
        return self._snapshot(manifest["expectedStart"])

    def observe(self, expected: dict[str, Any], *, timeout_sec: int) -> Snapshot:
        return self._snapshot(expected, timeout_sec=timeout_sec)

    def _snapshot(self, expected: dict[str, Any], *, timeout_sec: int = 30) -> Snapshot:
        bridge = _validate_bridge(
            self._json_command(
                "bridge-preflight",
                (str(PYTHON), str(BRIDGE), "preflight", "--json"),
                10,
            )
        )
        receipts = {
            "version": self._a90ctl("version", ["version"], timeout_sec),
            "selftest": self._a90ctl("selftest", ["selftest"], timeout_sec),
            "status": self._a90ctl("status", ["status"], timeout_sec),
            "bootId": self._a90ctl(
                "boot-id", ["cat", "/proc/sys/kernel/random/boot_id"], timeout_sec
            ),
        }
        version_text = _validate_command(receipts["version"], ["version"], "version")
        selftest_text = _validate_command(receipts["selftest"], ["selftest"], "selftest")
        status_text = _validate_command(receipts["status"], ["status"], "status")
        boot_text = _validate_command(
            receipts["bootId"], ["cat", "/proc/sys/kernel/random/boot_id"], "boot ID"
        )
        version = _one_line(version_text, VERSION_RE, "resident version")
        _one_line(selftest_text, SELFTEST_RE, "resident selftest")
        boot_id = _one_line(boot_text, BOOT_ID_RE, "resident boot ID").group(0)
        pstore = [line.strip() for line in status_text.replace("\r", "").splitlines() if line.strip().startswith("pstore=")]
        healthy = (
            len(pstore) == 1
            and pstore[0].split().count("entries=0") == 1
            and not any(
                token.startswith("entries=") and token != "entries=0"
                for token in pstore[0].split()
            )
            and (version.group("version"), version.group("build"))
            == (expected["version"], expected["build"])
        )
        stable_identity = {
            "bridge": bridge,
            "bootId": boot_id,
            "version": version.group("version"),
            "build": version.group("build"),
        }
        evidence = {
            "stableIdentity": stable_identity,
            "commands": {
                key: sha256_bytes(canonical_json(receipts[key])) for key in sorted(receipts)
            },
        }
        return Snapshot(
            target_evidence_sha256=sha256_bytes(canonical_json(stable_identity)),
            boot_id=boot_id,
            version=version.group("version"),
            build=version.group("build"),
            healthy=healthy,
            recovery_available=True,
            other_targets_untouched=True,
            receipt_sha256=sha256_bytes(
                canonical_json({"evidence": evidence, "healthy": healthy})
            ),
        )

    def flash(self, artifact: dict[str, Any], *, rollback: bool, timeout_sec: int) -> EffectResult:
        role = "rollback" if rollback else "candidate"
        argv = (
            str(PYTHON),
            str(FLASH),
            artifact["path"],
            "--adb",
            str(ADB),
            "--from-native",
            "--require-empty-adb-baseline",
            "--expect-version",
            artifact["version"],
            "--expect-sha256",
            artifact["sha256"],
            "--expect-readback-sha256",
            artifact["sha256"],
            "--verify-protocol",
            "selftest",
            "--recovery-timeout",
            str(timeout_sec),
            "--bridge-timeout",
            str(timeout_sec),
        )
        started = time.monotonic()
        result = self.runner.run(f"flash-{role}", argv, min(1900, timeout_sec * 2 + 60))
        receipt = {
            "argv": list(argv),
            "returncode": result.returncode,
            "quiescent": result.quiescent,
            "stdoutSha256": sha256_bytes(result.stdout),
            "stderrSha256": sha256_bytes(result.stderr),
            "durationMs": int((time.monotonic() - started) * 1000),
        }
        return EffectResult(
            returncode=result.returncode,
            completed=result.returncode == 0,
            quiescent=result.quiescent,
            receipt_sha256=sha256_bytes(canonical_json(receipt)),
        )
