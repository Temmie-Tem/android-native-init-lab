#!/usr/bin/env python3
"""Small fixed adapter for the A90 minimal boot-only F1 state machine.

The adapter reuses the repository-managed Native serial bridge and
``native_init_flash.py``.  It does not start ADB outside the helper's recovery
window and exposes no caller-selected command, partition, endpoint, or retry.
Live subprocess construction remains disabled pending independent review.
"""

from __future__ import annotations

import json
import importlib.util
import os
import re
import resource
import shlex
import signal
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol
from a90_boot_only_f1_minimal_v1 import (
    _MODULE_SENTINEL as MINIMAL_MODULE_SENTINEL,
    ContractError,
    EffectResult,
    FailedBootEvidenceResult,
    Snapshot,
    FAILED_BOOT_CMDLINE_MAX_BYTES,
    FAILED_BOOT_EVIDENCE_CMDLINE_SOURCE,
    FAILED_BOOT_EVIDENCE_SOURCE,
    FAILED_BOOT_RECOVERY_SETTLE_ATTEMPTS,
    FAILED_BOOT_EVIDENCE_TIMEOUT_SEC,
    FAILED_BOOT_LAST_KMSG_MAX_BYTES,
    canonical_json,
    sha256_bytes,
)
_SERIAL_REDACTION_PATH = Path(__file__).resolve().with_name("a90_serial_redaction_v1.py")
_serial_redaction = sys.modules.get("a90_serial_redaction_v1")
if _serial_redaction is None:
    _spec = importlib.util.spec_from_file_location("a90_serial_redaction_v1", _SERIAL_REDACTION_PATH)
    if _spec is None or _spec.loader is None: raise RuntimeError("serial redaction module import specification failed")
    _serial_redaction = importlib.util.module_from_spec(_spec); sys.modules["a90_serial_redaction_v1"] = _serial_redaction
    _spec.loader.exec_module(_serial_redaction)
if Path(getattr(_serial_redaction, "__file__", "")).resolve() != _SERIAL_REDACTION_PATH: raise RuntimeError("serial redaction module identity is not exact")
SerialRedactor = _serial_redaction.SerialRedactor; run_owner_process = _serial_redaction.run_owner_process
LIVE_ADAPTER_ENABLED = True
REPO_ROOT = Path(__file__).resolve().parents[5]
PYTHON = Path("/usr/bin/python3.14")
ADB = Path("/usr/bin/adb")
LSUSB = Path("/usr/bin/lsusb")
BRIDGE = REPO_ROOT / "workspace/public/src/scripts/revalidation/a90_bridge.py"
A90CTL = REPO_ROOT / "workspace/public/src/scripts/revalidation/a90ctl.py"
FLASH = REPO_ROOT / "workspace/public/src/scripts/revalidation/native_init_flash.py"
SERIAL_BRIDGE = REPO_ROOT / "workspace/public/src/scripts/revalidation/serial_tcp_bridge.py"
FIXED_SERIAL = "/dev/serial/by-id/usb-A90-LNX_A90_Linux_ARM64_A90NATIVE001-if00"
MAX_OUTPUT_BYTES = 1 << 20
MAX_CHILD_FILE_BYTES = 64 << 20
VERSION_RE = re.compile(r"^version: (?P<version>\S+) build=(?P<build>\S+)$")
SELFTEST_RE = re.compile(
    r"^selftest: pass=[0-9]+ warn=[0-9]+ fail=0 duration=[0-9]+ms entries=[1-9][0-9]*$"
)
BOOT_ID_RE = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
TTY_RE = re.compile(r"^/dev/ttyACM[0-9]+$")
LSUSB_RE = re.compile(
    rb"^Bus [0-9]{3} Device [0-9]{3}: ID "
    rb"(?P<vendor>[0-9a-f]{4}):(?P<product>[0-9a-f]{4}) .+$"
)
ADB_STATES = {"device", "recovery", "offline", "unauthorized", "no permissions"}
ADB_ROLE_NATIVE = "NATIVE_NO_RECOVERY"
ADB_ROLE_RECOVERY = "BOUND_RECOVERY_PRESENT"
ROLLBACK_REENUMERATION_TIMEOUT_SEC = 30.0
ROLLBACK_REENUMERATION_POLL_SEC = 0.25
FAILED_BOOT_CMDLINE_RAW_NAME = "failed-boot-001-cmdline.raw"
FAILED_BOOT_LAST_KMSG_RAW_NAME = "failed-boot-002-last-kmsg.raw"

@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    quiescent: bool = True
class CommandRunner(Protocol):
    def run(self, label: str, argv: tuple[str, ...], timeout_sec: int) -> CommandResult: ...

class HostRunner:
    """Bounded production subprocess owner for the reviewed minimal lane."""
    def __init__(self, log_directory: Path, *, redactor: SerialRedactor | None = None) -> None:
        if LIVE_ADAPTER_ENABLED is not True:
            raise ContractError("A90 minimal live adapter is disabled")
        if not log_directory.is_absolute():
            raise ContractError("adapter log directory is not absolute")
        try:
            log_directory.mkdir(mode=0o700, parents=False)
        except FileExistsError as exc:
            raise ContractError("adapter log directory already exists") from exc
        _fsync_directory(log_directory.parent)
        self.log_directory = log_directory
        try:
            self.adb_home, self.adb_android = _serial_redaction.prepare_owner_adb_home(
                log_directory
            )
        except (OSError, RuntimeError) as exc:
            raise ContractError("owner ADB home creation failed") from exc
        _fsync_directory(self.adb_home)
        _fsync_directory(self.log_directory)
        self._check_adb_home()
        self.environment = {
            "HOME": str(self.adb_home),
            **_serial_redaction.owner_adb_environment(self.adb_home),
        }
        self.sequence = 0
        self.redactor = redactor

    def _check_adb_home(self) -> None:
        try:
            _serial_redaction.validate_owner_adb_home(self.adb_home, self.adb_android)
        except (OSError, RuntimeError) as exc:
            raise ContractError(str(exc)) from exc
    def run(self, label: str, argv: tuple[str, ...], timeout_sec: int) -> CommandResult:
        if re.fullmatch(r"[a-z0-9-]{1,40}", label) is None:
            raise ContractError("adapter log label is invalid")
        self._check_adb_home()
        output_limit = {"failed-boot-cmdline": FAILED_BOOT_CMDLINE_MAX_BYTES, "failed-boot-last-kmsg": FAILED_BOOT_LAST_KMSG_MAX_BYTES}.get(label, MAX_OUTPUT_BYTES)
        self.sequence += 1
        prefix = f"{self.sequence:03d}-{label}"
        stdout_path = self.log_directory / f"{prefix}.stdout"
        stderr_path = self.log_directory / f"{prefix}.stderr"
        if self.redactor is not None:
            try:
                returncode, stdout, stderr, quiescent = run_owner_process(argv, timeout_sec, cwd=REPO_ROOT, log_directory=self.log_directory, stdout_path=stdout_path, stderr_path=stderr_path, redactor=self.redactor, max_output_bytes=output_limit, adb_inventory=label in {"adb-inventory", "failed-boot-adb-inventory"}, environment=self.environment, preexec_fn=_limit_child, process_group_exists=_process_group_exists)
            except RuntimeError as exc:
                raise ContractError(str(exc)) from exc
            self._check_adb_home()
            return CommandResult(returncode, stdout, stderr, quiescent)
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
                env=self.environment,
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
            stdout = _read_bound_log(stdout_fd, output_limit)
            stderr = _read_bound_log(stderr_fd, output_limit)
            _fsync_directory(self.log_directory)
            self._check_adb_home()
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
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    # The fixed flash helper creates one verified boot-sized sealed copy before
    # transfer.  Keep that scratch file bounded independently from the much
    # smaller stdout/stderr acceptance envelope enforced by _read_bound_log().
    resource.setrlimit(
        resource.RLIMIT_FSIZE,
        (MAX_CHILD_FILE_BYTES, MAX_CHILD_FILE_BYTES),
    )
def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
def _read_bound_log(descriptor: int, maximum: int = MAX_OUTPUT_BYTES) -> bytes:
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > maximum:
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
OWNER_RECEIPT_SCHEMA = "a90-f1-owner-effect-receipt-v1"
OWNER_RECEIPT_MODE = "A90_F1_OWNER_EFFECT_RECEIPT_V1"
OWNER_RECEIPT_OUTCOMES = {
    "PRE_WRITE_FAILURE",
    "WRITE_OR_READBACK_UNCLASSIFIED",
    "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED",
    "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN",
}
def _parse_owner_effect_receipt(raw: bytes) -> str:
    """Return a stage only for the exact fixed helper receipt.

    Missing, prose, duplicate, or malformed stdout is deliberately mapped to
    ``UNCLASSIFIED``.  It can never manufacture candidate-return pending.
    """
    if not raw:
        return "UNCLASSIFIED"
    try:
        value = _json(raw, "owner effect receipt")
    except ContractError:
        return "UNCLASSIFIED"
    if canonical_json(value) != raw:
        return "UNCLASSIFIED"
    if set(value) != {
        "schema",
        "mode",
        "outcome",
        "writeStarted",
        "bootWrittenReadbackExact",
        "systemReturnAttempted",
        "systemReturnCommandOk",
        "systemReturnConfirmed",
    }:
        return "UNCLASSIFIED"
    if (
        value["schema"] != OWNER_RECEIPT_SCHEMA
        or value["mode"] != OWNER_RECEIPT_MODE
        or type(value["outcome"]) is not str
        or value["outcome"] not in OWNER_RECEIPT_OUTCOMES
        or any(
            type(value[key]) is not bool
            for key in (
                "writeStarted",
                "bootWrittenReadbackExact",
                "systemReturnAttempted",
                "systemReturnCommandOk",
                "systemReturnConfirmed",
            )
        )
    ):
        return "UNCLASSIFIED"
    if value["outcome"] == "PRE_WRITE_FAILURE" and any(
        value[key]
        for key in (
            "writeStarted",
            "bootWrittenReadbackExact",
            "systemReturnAttempted",
            "systemReturnCommandOk",
            "systemReturnConfirmed",
        )
    ):
        return "UNCLASSIFIED"
    if value["outcome"] == "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED" and (
        not value["writeStarted"]
        or not value["bootWrittenReadbackExact"]
        or not value["systemReturnAttempted"]
        or not value["systemReturnCommandOk"]
        or not value["systemReturnConfirmed"]
    ):
        return "UNCLASSIFIED"
    if value["outcome"] == "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN" and (
        not value["writeStarted"]
        or not value["bootWrittenReadbackExact"]
        or not value["systemReturnAttempted"]
        or value["systemReturnConfirmed"]
    ):
        return "UNCLASSIFIED"
    if value["outcome"] == "WRITE_OR_READBACK_UNCLASSIFIED" and (
        not value["writeStarted"] or value["bootWrittenReadbackExact"]
    ):
        return "UNCLASSIFIED"
    return value["outcome"]
def _one_line(text: str, pattern: re.Pattern[str], label: str) -> re.Match[str]:
    matches = [pattern.fullmatch(line.strip()) for line in text.replace("\r", "").splitlines()]
    exact = [match for match in matches if match is not None]
    if len(exact) != 1:
        raise ContractError(f"{label} is not unique")
    return exact[0]
def _validate_bridge(value: dict[str, Any]) -> dict[str, Any]:
    candidates = value.get("serial_candidates")
    pids = value.get("port_pids")
    metadata, selected_realpath = value.get("metadata"), value.get("selected_realpath")
    processes = value.get("processes")
    socket_inodes, sockets = value.get("port_socket_inodes"), value.get("port_sockets")
    candidates_valid = type(candidates) is list and all(
        type(candidate) is dict for candidate in candidates
    )
    bound_candidates = [
        candidate for candidate in candidates if candidate.get("path") == FIXED_SERIAL
    ] if candidates_valid else []
    command = metadata.get("command") if type(metadata) is dict else None
    process = processes[0] if type(processes) is list and len(processes) == 1 else None
    listener = sockets[0] if type(sockets) is list and len(sockets) == 1 else None
    process_argv = (
        shlex.split(process.get("cmdline"))
        if type(process) is dict and type(process.get("cmdline")) is str
        else None
    )
    command_options = (
        dict(zip(command[2::2], command[3::2]))
        if type(command) is list
        and len(command) == 14
        and all(type(item) is str for item in command)
        and all(item.startswith("--") for item in command[2::2])
        and len(set(command[2::2])) == 6
        else None
    )
    if (
        value.get("wrapper_contract") != 1
        or value.get("bridge_process") != "running"
        or value.get("port_listening") is not True
        or type(value.get("ambiguous")) is not bool
        or type(candidates) is not list
        or len(bound_candidates) != 1
        or bound_candidates[0].get("exists") is not True
        or bound_candidates[0].get("realpath") != selected_realpath
        or value.get("selected_device") != FIXED_SERIAL
        or type(selected_realpath) is not str
        or TTY_RE.fullmatch(selected_realpath) is None
        or type(metadata) is not dict
        or metadata.get("device") != FIXED_SERIAL
        or metadata.get("device_glob") != FIXED_SERIAL
        or metadata.get("effective_expect_realpath") != selected_realpath
        or metadata.get("pin_selected_realpath") is not True
        or metadata.get("host") != "127.0.0.1"
        or metadata.get("port") != 54321
        or value.get("listen_host") != "127.0.0.1"
        or value.get("listen_port") != 54321
        or type(pids) is not list
        or len(pids) != 1
        or type(pids[0]) is not int
        or pids[0] <= 0
        or value.get("port_pid_source") != "fd"
        or type(socket_inodes) is not list
        or len(socket_inodes) != 1
        or type(socket_inodes[0]) is not str
        or not socket_inodes[0].isdigit()
        or type(listener) is not dict
        or listener.get("address") != "127.0.0.1"
        or listener.get("port") != 54321
        or listener.get("inode") != socket_inodes[0]
        or type(process) is not dict
        or process.get("pid") != pids[0]
        or process.get("pid") != metadata.get("pid")
        or process.get("managed") is not True
        or process.get("port_match") is not True
        or process_argv != command
        or command_options is None
        or command[:2] != ["/usr/bin/python3", str(SERIAL_BRIDGE)]
        or command_options.get("--host") != "127.0.0.1"
        or command_options.get("--port") != "54321"
        or command_options.get("--device") != FIXED_SERIAL
        or command_options.get("--device-glob") != FIXED_SERIAL
        or command_options.get("--expect-realpath") != selected_realpath
        or type(command_options.get("--capture")) is not str
        or value.get("bridge_probe") not in {"connected-no-immediate-error", "data"}
    ):
        raise ContractError("A90 bridge preflight is not exact")
    return {
        "selectedDevice": FIXED_SERIAL,
        "selectedRealpath": selected_realpath,
        "bridgePid": pids[0],
    }
def _validate_usb_inventory(result: CommandResult) -> dict[str, Any]:
    if (
        type(result.returncode) is not int
        or result.returncode != 0
        or result.quiescent is not True
        or result.stderr
        or not result.stdout
    ):
        raise ContractError("USB inventory producer failed")
    lines = result.stdout.rstrip(b"\n").split(b"\n")
    matches = [LSUSB_RE.fullmatch(line) for line in lines]
    if any(match is None for match in matches):
        raise ContractError("USB inventory output is malformed")
    samsung = [
        match for match in matches
        if match is not None and match.group("vendor") == b"04e8"
    ]
    a90 = [match for match in samsung if match.group("product") == b"6861"]
    if len(a90) != 1:
        raise ContractError("USB inventory does not contain one exact A90 endpoint")
    return {
        "allEndpointCount": len(lines),
        "samsungEndpointCount": len(samsung),
        "a90EndpointCount": 1,
        "otherSamsungEndpointCount": len(samsung) - 1,
        "a90Product": "04e8:6861",
        "inventorySha256": sha256_bytes(result.stdout),
    }
def _parse_effect_inventory(result: CommandResult) -> tuple[str, str]:
    """Return the exact pre-effect USB role without opening ADB on Native."""
    if (
        type(result.returncode) is not int
        or result.returncode != 0
        or result.quiescent is not True
        or result.stderr
        or not result.stdout
    ):
        raise ContractError("pre-effect USB inventory producer failed")
    lines = result.stdout.rstrip(b"\n").split(b"\n")
    matches = [LSUSB_RE.fullmatch(line) for line in lines]
    if any(match is None for match in matches):
        raise ContractError("pre-effect USB inventory output is malformed")
    samsung = [
        match for match in matches
        if match is not None and match.group("vendor") == b"04e8"
    ]
    if len(samsung) != 1 or samsung[0] is None:
        raise ContractError("pre-effect USB inventory is not single-Samsung")
    product = samsung[0].group("product")
    if product == b"6861":
        return ADB_ROLE_NATIVE, sha256_bytes(result.stdout)
    if product == b"6860":
        return ADB_ROLE_RECOVERY, sha256_bytes(result.stdout)
    raise ContractError("pre-effect USB product is not exact A90 Native or Recovery")
def _is_empty_effect_inventory(result: CommandResult) -> bool:
    """Accept only a well-formed, successful zero-Samsung re-enumeration."""
    if (
        type(result.returncode) is not int
        or result.returncode != 0
        or result.quiescent is not True
        or result.stderr
        or not result.stdout
    ):
        return False
    lines = result.stdout.rstrip(b"\n").split(b"\n")
    matches = [LSUSB_RE.fullmatch(line) for line in lines]
    if not lines or any(match is None for match in matches):
        return False
    return not any(
        match is not None and match.group("vendor") == b"04e8"
        for match in matches
    )


def _validate_effect_inventory(result: CommandResult) -> tuple[str, str]:
    return _parse_effect_inventory(result)


def _parse_recovery_adb_inventory(
    result: CommandResult, *, expected_serial_sha256: str
) -> tuple[str, str]:
    """Validate one recovery ADB row and return digest plus bound serial."""
    if (
        type(result.returncode) is not int
        or result.returncode != 0
        or result.quiescent is not True
        or result.stderr
        or not result.stdout
    ):
        raise ContractError("recovery ADB inventory producer failed")
    try:
        lines = result.stdout.decode("ascii").replace("\r", "").splitlines()
    except UnicodeDecodeError as exc:
        raise ContractError("recovery ADB inventory is not ASCII") from exc
    if not lines or lines[0] != "List of devices attached":
        raise ContractError("recovery ADB inventory header is not exact")
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line in lines[1:]:
        if not line:
            continue
        fields = line.split(None, 2)
        if len(fields) < 2 or not re.fullmatch(r"[!-~]{1,256}", fields[0]):
            raise ContractError("recovery ADB inventory row is malformed")
        serial, state = fields[0], fields[1]
        if state == "no" and len(fields) == 3 and fields[2].startswith("permissions"):
            state = "no permissions"
        if serial in seen or state not in ADB_STATES:
            raise ContractError("recovery ADB inventory role is ambiguous")
        seen.add(serial)
        rows.append((serial, state))
    if (
        len(rows) != 1
        or rows[0][1] != "recovery"
        or sha256_bytes(rows[0][0].encode("utf-8")) != expected_serial_sha256
    ):
        raise ContractError("recovery ADB inventory is not the bound A90")
    return sha256_bytes(result.stdout), rows[0][0]


def _validate_effect_adb_inventory(
    result: CommandResult, *, expected_serial_sha256: str
) -> str:
    """Validate the recovery-only ADB role and return its raw-stream digest."""
    digest, _serial = _parse_recovery_adb_inventory(
        result, expected_serial_sha256=expected_serial_sha256
    )
    return digest


def _adb_recovery_settle_transient(result: CommandResult, expected_serial_sha256: str) -> bool:
    if type(result.returncode) is not int or result.returncode != 0 or result.quiescent is not True or type(result.stdout) is not bytes or type(result.stderr) is not bytes or result.stderr:
        return False
    try:
        lines = result.stdout.decode("ascii").replace("\r", "").splitlines()
    except UnicodeDecodeError:
        return False
    if not lines or lines[0] != "List of devices attached":
        return False
    rows = []
    for line in lines[1:]:
        if not line:
            continue
        fields = line.split(None, 2)
        if len(fields) < 2 or not re.fullmatch(r"[!-~]{1,256}", fields[0]):
            return False
        state = fields[1]
        if state == "no" and len(fields) == 3 and fields[2].startswith("permissions"):
            state = "no permissions"
        rows.append((fields[0], state))
    return not rows or (len(rows) == 1 and rows[0][1] == "offline" and sha256_bytes(rows[0][0].encode("utf-8")) == expected_serial_sha256)


def _bound_response(
    value: dict[str, Any], command: list[str], label: str
) -> dict[str, Any]:
    if (
        set(value) != {"request", "response"}
        or value.get("request") != command
        or type(value.get("response")) is not dict
    ):
        raise ContractError(f"{label} request binding is invalid")
    return value["response"]


def _validate_command(value: dict[str, Any], command: list[str], label: str) -> str:
    value = _bound_response(value, command, label)
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


def _validate_absent_stat(value: dict[str, Any], path: str) -> bool:
    value = _bound_response(value, ["stat", path], "fresh state stat")
    end = value.get("end")
    if (
        set(value) != {"begin", "end", "rc", "status", "trust", "text"}
        or type(value.get("rc")) is not int
        or value["rc"] != -2
        or value.get("status") != "error"
        or value.get("trust") != "A90P1_V1_STRUCTURAL_ONLY"
        or type(end) is not dict
        or end.get("cmd") not in {None, "stat"}
        or end.get("rc") != "-2"
        or end.get("status") != "error"
        or end.get("errno") != "2"
    ):
        raise ContractError("fresh state absence receipt is invalid")
    return True


class FixedA90Adapter:
    def __init__(self, runner: CommandRunner, *, qualification: dict[str, Any]) -> None:
        recovery = qualification.get("recovery")
        recovery_identity = qualification.get("recoveryIdentity")
        fresh_state = qualification.get("freshState")
        review = qualification.get("review")
        if (
            type(recovery) is not dict
            or set(recovery) != {"profile", "method", "demonstrated"}
            or recovery.get("profile") != "A90_ATTENDED_PHYSICAL_RECOVERY_V1"
            or recovery.get("method")
            != "NATIVE_TO_STABLE_ADB_BASELINE_SINGLE_NEW_RECOVERY_ARRIVAL_BOOT_READBACK_V1"
            or recovery.get("demonstrated") is not True
            or type(recovery_identity) is not dict
            or set(recovery_identity) != {"adbSerialSha256"}
            or type(recovery_identity.get("adbSerialSha256")) is not str
            or re.fullmatch(
                r"[0-9a-f]{64}", recovery_identity["adbSerialSha256"]
            ) is None
            or type(review) is not dict
            or set(review) != {"path", "size", "sha256"}
            or type(review.get("sha256")) is not str
            or re.fullmatch(r"[0-9a-f]{64}", review["sha256"]) is None
            or type(fresh_state) is not dict
            or set(fresh_state) != {"enablePath", "latchPath"}
        ):
            raise ContractError("A90 physical recovery qualification is not exact")
        self.runner = runner
        self.recovery_evidence_sha256 = review["sha256"]
        self.recovery_serial_sha256 = recovery_identity["adbSerialSha256"]

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

    def _a90ctl(
        self,
        label: str,
        command: list[str],
        timeout_sec: int = 15,
        *,
        allow_error: bool = False,
    ) -> dict[str, Any]:
        prefix = (
            str(PYTHON),
            str(A90CTL),
            "--json",
            "--timeout",
            str(timeout_sec),
        )
        argv = (*prefix, *(("--allow-error",) if allow_error else ()), "--", *command)
        return {
            "request": list(command),
            "response": self._json_command(label, argv, timeout_sec),
        }

    @staticmethod
    def _remaining(deadline: float, *, cap: int) -> int:
        remaining = int(deadline - time.monotonic())
        if remaining < 1:
            raise ContractError("A90 observation exhausted its total timeout")
        return min(cap, remaining)

    def _effect_inventory(self, *, rollback: bool) -> tuple[str, str, str | None]:
        """Bind USB/ACM Native or Recovery before invoking the flash helper."""
        first = self.runner.run("effect-usb-inventory", (str(LSUSB),), 10)
        if _is_empty_effect_inventory(first):
            if not rollback:
                raise ContractError("candidate pre-effect USB inventory has no A90 endpoint")
            deadline = time.monotonic() + ROLLBACK_REENUMERATION_TIMEOUT_SEC
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ContractError("rollback pre-effect A90 re-enumeration timed out")
                time.sleep(min(ROLLBACK_REENUMERATION_POLL_SEC, remaining))
                retry = self.runner.run(
                    "rollback-effect-usb-inventory",
                    (str(LSUSB),),
                    max(1, min(10, int(remaining + 0.999))),
                )
                if time.monotonic() > deadline:
                    raise ContractError(
                        "rollback pre-effect A90 re-enumeration timed out"
                    )
                if _is_empty_effect_inventory(retry):
                    continue
                role, usb_digest = _validate_effect_inventory(retry)
                break
        else:
            role, usb_digest = _validate_effect_inventory(first)
        if role == ADB_ROLE_NATIVE:
            # No ADB process is created while Native is the selected role.
            return role, usb_digest, None
        adb_digest = _validate_effect_adb_inventory(
            self.runner.run("adb-inventory", (str(ADB), "devices", "-l"), 10),
            expected_serial_sha256=self.recovery_serial_sha256,
        )
        return role, usb_digest, adb_digest

    def _failed_boot_log_directory(self) -> Path:
        directory = getattr(self.runner, "log_directory", None)
        if not isinstance(directory, Path) or not directory.is_absolute():
            raise ContractError("failed-boot owner log directory is unavailable")
        metadata = directory.lstat()
        if not (stat.S_ISDIR(metadata.st_mode) and metadata.st_uid == os.getuid() and metadata.st_gid == os.getgid() and stat.S_IMODE(metadata.st_mode) == 0o700):
            raise ContractError("failed-boot owner log directory is not private")
        return directory

    def _write_failed_boot_raw(self, name: str, raw: bytes, lease_check: Callable[[], None]) -> None:
        lease_check()
        directory = self._failed_boot_log_directory()
        descriptor = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
        try:
            offset = 0
            while offset < len(raw):
                written = os.write(descriptor, raw[offset:])
                if written <= 0:
                    raise ContractError("failed-boot raw evidence short write")
                offset += written
            metadata = os.fstat(descriptor)
            if not (stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1 and metadata.st_size == len(raw) and stat.S_IMODE(metadata.st_mode) == 0o600 and metadata.st_uid == os.getuid() and metadata.st_gid == os.getgid()):
                raise ContractError("failed-boot raw evidence file identity changed")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        _fsync_directory(directory)

    @staticmethod
    def _failed_boot_command_result(
        result: CommandResult | None,
        *,
        source: str,
        maximum: int,
    ) -> tuple[bytes, str | None, bool]:
        if result is None:
            return b"", "COMMAND_NONQUIESCENT", False
        if type(result.returncode) is not int or type(result.quiescent) is not bool or type(result.stdout) is not bytes or type(result.stderr) is not bytes:
            return b"", "COMMAND_NONQUIESCENT", False
        if result.quiescent is not True:
            return b"", "COMMAND_NONQUIESCENT", False
        if result.returncode == 124:
            return b"", "COMMAND_TIMEOUT", True
        if result.stderr:
            return b"", "COMMAND_STDERR", True
        if result.returncode != 0:
            return b"", "COMMAND_NONZERO", True
        if type(result.stdout) is not bytes or len(result.stdout) > maximum:
            return b"", "COMMAND_OUTPUT_INVALID", True
        if source == FAILED_BOOT_EVIDENCE_CMDLINE_SOURCE:
            if not result.stdout:
                return b"", "COMMAND_OUTPUT_INVALID", True
            try:
                result.stdout.decode("ascii")
            except UnicodeDecodeError:
                return b"", "COMMAND_OUTPUT_INVALID", True
        elif not result.stdout:
            return b"", "EMPTY_LAST_KMSG", True
        return result.stdout, None, True

    def _capture_failed_boot_evidence(
        self, *, timeout_sec: int, lease_check: Callable[[], None]
    ) -> FailedBootEvidenceResult:
        try:
            if type(timeout_sec) is not int or timeout_sec < 1 or timeout_sec > FAILED_BOOT_EVIDENCE_TIMEOUT_SEC:
                return FailedBootEvidenceResult.no_proof("COMMAND_TIMEOUT")
            deadline = time.monotonic() + timeout_sec
            def remaining() -> int | None:
                budget = deadline - time.monotonic()
                return None if budget < 1 else max(1, min(FAILED_BOOT_EVIDENCE_TIMEOUT_SEC, int(budget)))
            def run(label: str, argv: tuple[str, ...]) -> tuple[CommandResult | None, str | None]:
                budget = remaining()
                if budget is None:
                    return None, "COMMAND_TIMEOUT"
                try:
                    result = self.runner.run(label, argv, budget)
                    if time.monotonic() > deadline:
                        return result, "COMMAND_TIMEOUT"
                    return result, None
                except Exception:
                    return None, "COMMAND_NONQUIESCENT"
            settle_deadline = min(deadline, time.monotonic() + 30)
            def await_final_recovery() -> tuple[CommandResult | None, str | None, str | None, str | None, str | None]:
                for ordinal in range(FAILED_BOOT_RECOVERY_SETTLE_ATTEMPTS * 4):
                    if time.monotonic() >= settle_deadline:
                        return None, "NO_RECOVERY_ENDPOINT", None, None, None
                    label = "failed-boot-usb-inventory" if ordinal == 0 else "failed-boot-usb-settle"
                    result, error = run(label, (str(LSUSB),))
                    if error is not None or result is None:
                        return result, error or "COMMAND_FAILED", None, None, None
                    if type(result.returncode) is not int or type(result.quiescent) is not bool or type(result.stdout) is not bytes or type(result.stderr) is not bytes:
                        return result, "COMMAND_NONQUIESCENT", None, None, None
                    if result.quiescent is not True:
                        return result, "COMMAND_NONQUIESCENT", None, None, None
                    if _is_empty_effect_inventory(result):
                        time.sleep(min(1.0, max(0.0, settle_deadline - time.monotonic())))
                        continue
                    try:
                        role, usb_digest = _validate_effect_inventory(result)
                    except ContractError:
                        return result, "USB_INVENTORY_FAILED", None, None, None
                    if role == ADB_ROLE_NATIVE:
                        time.sleep(min(1.0, max(0.0, settle_deadline - time.monotonic())))
                        continue
                    adb_result, adb_error = run("failed-boot-adb-inventory", (str(ADB), "devices", "-l"))
                    if adb_error is not None or adb_result is None:
                        return adb_result, adb_error or "COMMAND_FAILED", usb_digest, None, None
                    if type(adb_result.returncode) is not int or type(adb_result.quiescent) is not bool or type(adb_result.stdout) is not bytes or type(adb_result.stderr) is not bytes:
                        return adb_result, "COMMAND_NONQUIESCENT", usb_digest, None, None
                    if adb_result.quiescent is not True:
                        return adb_result, "COMMAND_NONQUIESCENT", usb_digest, None, None
                    try:
                        adb_digest, serial = _parse_recovery_adb_inventory(adb_result, expected_serial_sha256=self.recovery_serial_sha256)
                    except ContractError:
                        if _adb_recovery_settle_transient(adb_result, self.recovery_serial_sha256):
                            time.sleep(min(1.0, max(0.0, settle_deadline - time.monotonic())))
                            continue
                        return adb_result, "ADB_INVENTORY_FAILED", usb_digest, None, None
                    return result, None, usb_digest, adb_digest, serial
                return None, "NO_RECOVERY_ENDPOINT", None, None, None
            directory = self._failed_boot_log_directory()
            for name in (FAILED_BOOT_CMDLINE_RAW_NAME, FAILED_BOOT_LAST_KMSG_RAW_NAME):
                if (directory / name).exists() or (directory / name).is_symlink():
                    return FailedBootEvidenceResult.no_proof("RAW_PUBLICATION_FAILED")
            lease_check()
            usb_result, usb_error, usb_digest, adb_digest, serial = await_final_recovery()
            if usb_error is not None or usb_result is None or usb_digest is None or adb_digest is None or serial is None:
                return FailedBootEvidenceResult.no_proof(usb_error or "COMMAND_FAILED", usb_inventory_sha256=usb_digest or "0" * 64, adb_inventory_sha256=adb_digest or "0" * 64, quiescent=usb_error != "COMMAND_NONQUIESCENT" and (usb_result is None or usb_result.quiescent is True))
            cmdline_argv = (str(ADB), "-s", serial, "exec-out", "cat", FAILED_BOOT_EVIDENCE_CMDLINE_SOURCE)
            last_kmsg_argv = (str(ADB), "-s", serial, "exec-out", "cat", FAILED_BOOT_EVIDENCE_SOURCE)
            lease_check()
            cmdline_result, cmdline_error = run("failed-boot-cmdline", cmdline_argv)
            cmdline, cmdline_reason, cmdline_quiescent = self._failed_boot_command_result(cmdline_result, source=FAILED_BOOT_EVIDENCE_CMDLINE_SOURCE, maximum=FAILED_BOOT_CMDLINE_MAX_BYTES)
            if cmdline_error is not None or cmdline_result is None or cmdline_result.quiescent is not True or cmdline_result.returncode == 124 or cmdline_reason == "COMMAND_NONQUIESCENT":
                return FailedBootEvidenceResult.no_proof(cmdline_error or cmdline_reason or "COMMAND_FAILED", cmdline=cmdline, usb_inventory_sha256=usb_digest, adb_inventory_sha256=adb_digest, quiescent=cmdline_quiescent)
            if remaining() is None:
                return FailedBootEvidenceResult.no_proof("COMMAND_TIMEOUT", cmdline=cmdline, usb_inventory_sha256=usb_digest, adb_inventory_sha256=adb_digest, quiescent=cmdline_quiescent)
            lease_check()
            last_kmsg_result, last_kmsg_error = run("failed-boot-last-kmsg", last_kmsg_argv)
            last_kmsg, last_kmsg_reason, last_kmsg_quiescent = self._failed_boot_command_result(last_kmsg_result, source=FAILED_BOOT_EVIDENCE_SOURCE, maximum=FAILED_BOOT_LAST_KMSG_MAX_BYTES)
            if last_kmsg_error is not None and last_kmsg_result is None:
                last_kmsg_reason = last_kmsg_error
            raw_durable = False
            raw_reason: str | None = None
            if cmdline_reason is None:
                try:
                    self._write_failed_boot_raw(FAILED_BOOT_CMDLINE_RAW_NAME, cmdline, lease_check)
                except Exception:
                    raw_reason = "RAW_PUBLICATION_FAILED"
            if last_kmsg_reason is None and raw_reason is None:
                try:
                    self._write_failed_boot_raw(FAILED_BOOT_LAST_KMSG_RAW_NAME, last_kmsg, lease_check)
                except Exception:
                    raw_reason = "RAW_PUBLICATION_FAILED"
            if cmdline_reason is None and last_kmsg_reason is None and raw_reason is None:
                raw_durable = True
                return FailedBootEvidenceResult("CAPTURED", "BOTH_READS_DURABLE", len(cmdline), sha256_bytes(cmdline), len(last_kmsg), sha256_bytes(last_kmsg), usb_digest, adb_digest, cmdline_quiescent and last_kmsg_quiescent, raw_durable)
            reason = raw_reason or cmdline_reason or last_kmsg_reason or "OBSERVER_EXCEPTION"
            return FailedBootEvidenceResult.no_proof(reason, cmdline=cmdline, last_kmsg=last_kmsg, usb_inventory_sha256=usb_digest, adb_inventory_sha256=adb_digest, quiescent=cmdline_quiescent and last_kmsg_quiescent, raw_durable=raw_durable)
        except Exception:
            return FailedBootEvidenceResult.no_proof("OBSERVER_EXCEPTION")

    def preflight(self, manifest: dict[str, Any]) -> Snapshot:
        return self._snapshot(
            manifest["expectedStart"],
            manifest["qualification"]["freshState"],
            require_fresh_state=True,
        )

    def observe(
        self,
        expected: dict[str, Any],
        fresh_state: dict[str, Any],
        *,
        require_fresh_state: bool,
        timeout_sec: int,
    ) -> Snapshot:
        return self._snapshot(
            expected,
            fresh_state,
            require_fresh_state=require_fresh_state,
            timeout_sec=timeout_sec,
        )

    def _snapshot(
        self,
        expected: dict[str, Any],
        fresh_state: dict[str, Any],
        *,
        require_fresh_state: bool,
        timeout_sec: int = 30,
    ) -> Snapshot:
        deadline = time.monotonic() + timeout_sec
        usb_inventory = _validate_usb_inventory(
            self.runner.run(
                "usb-inventory",
                (str(LSUSB),),
                self._remaining(deadline, cap=10),
            )
        )
        bridge = _validate_bridge(
            self._json_command(
                "bridge-preflight",
                (
                    str(PYTHON), str(BRIDGE), "preflight",
                    "--device", FIXED_SERIAL,
                    "--device-glob", FIXED_SERIAL,
                    "--pin-selected-realpath", "--json",
                ),
                self._remaining(deadline, cap=10),
            )
        )
        receipts = {
            "bootIdStart": self._a90ctl(
                "boot-id-start",
                ["cat", "/proc/sys/kernel/random/boot_id"],
                self._remaining(deadline, cap=15),
            ),
            "version": self._a90ctl(
                "version", ["version"], self._remaining(deadline, cap=15)
            ),
            "selftest": self._a90ctl(
                "selftest", ["selftest"], self._remaining(deadline, cap=15)
            ),
            "status": self._a90ctl(
                "status", ["status"], self._remaining(deadline, cap=15)
            ),
            "bootIdFinal": self._a90ctl(
                "boot-id-final",
                ["cat", "/proc/sys/kernel/random/boot_id"],
                self._remaining(deadline, cap=15),
            ),
        }
        boot_start_text = _validate_command(
            receipts["bootIdStart"],
            ["cat", "/proc/sys/kernel/random/boot_id"],
            "initial boot ID",
        )
        version_text = _validate_command(receipts["version"], ["version"], "version")
        selftest_text = _validate_command(receipts["selftest"], ["selftest"], "selftest")
        status_text = _validate_command(receipts["status"], ["status"], "status")
        boot_final_text = _validate_command(
            receipts["bootIdFinal"],
            ["cat", "/proc/sys/kernel/random/boot_id"],
            "final boot ID",
        )
        state_observed = require_fresh_state
        state_absent = False
        if require_fresh_state:
            state_absent = True
            fresh_labels = {
                "enablePath": "fresh-enable-path",
                "latchPath": "fresh-latch-path",
            }
            for name, path in sorted(fresh_state.items()):
                receipt = self._a90ctl(
                    fresh_labels[name],
                    ["stat", path],
                    self._remaining(deadline, cap=15),
                    allow_error=True,
                )
                receipts[f"fresh-{name}"] = receipt
                state_absent = state_absent and _validate_absent_stat(receipt, path)
        version = _one_line(version_text, VERSION_RE, "resident version")
        _one_line(selftest_text, SELFTEST_RE, "resident selftest")
        boot_id = _one_line(
            boot_start_text, BOOT_ID_RE, "initial resident boot ID"
        ).group(0)
        final_boot_id = _one_line(
            boot_final_text, BOOT_ID_RE, "final resident boot ID"
        ).group(0)
        healthy = (
            (version.group("version"), version.group("build"))
            == (expected["version"], expected["build"])
            and boot_id == final_boot_id
            and (state_absent or not require_fresh_state)
        )
        stable_identity = {
            "usbInventory": usb_inventory,
            "bridge": bridge,
            "bootId": boot_id,
            "finalBootId": final_boot_id,
            "version": version.group("version"),
            "build": version.group("build"),
            "recoveryEvidenceSha256": self.recovery_evidence_sha256,
            "freshStateObserved": state_observed,
            "freshStateAbsent": state_absent,
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
            recovery_evidence_sha256=self.recovery_evidence_sha256,
            fresh_state_observed=state_observed,
            fresh_state_absent=state_absent,
            other_targets_untouched=usb_inventory["a90EndpointCount"] == 1 and usb_inventory["otherSamsungEndpointCount"] == 0,
            receipt_sha256=sha256_bytes(
                canonical_json({"evidence": evidence, "healthy": healthy})
            ),
        )
    def flash(self, artifact: dict[str, Any], *, rollback: bool, timeout_sec: int, owner_usb_inventory_sha256: str | None = None, owner_adb_inventory_sha256: str | None = None, owner_adb_role: str | None = None) -> EffectResult:
        if owner_usb_inventory_sha256 is None:
            owner_adb_role, owner_usb_inventory_sha256, owner_adb_inventory_sha256 = (
                self._effect_inventory(rollback=rollback)
            )
            if not rollback and owner_adb_role != ADB_ROLE_NATIVE:
                raise ContractError("candidate effect requires the exact Native role")
        role = "rollback" if rollback else "candidate"
        argv = fixed_flash_argv(
            artifact,
            recovery_serial_sha256=self.recovery_serial_sha256,
            timeout_sec=timeout_sec,
            rollback=rollback, owner_usb_inventory_sha256=owner_usb_inventory_sha256,
            owner_adb_inventory_sha256=owner_adb_inventory_sha256, owner_adb_role=owner_adb_role,
        )
        started = time.monotonic()
        result = self.runner.run(f"flash-{role}", argv, timeout_sec)
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
            outcome=_parse_owner_effect_receipt(result.stdout),
        )
def fixed_flash_argv(artifact: dict[str, Any], *, recovery_serial_sha256: str, timeout_sec: int, rollback: bool = False, owner_usb_inventory_sha256: str | None = None, owner_adb_inventory_sha256: str | None = None, owner_adb_role: str | None = None) -> tuple[str, ...]:
    """Return the sole reviewed helper command for receipt reconstruction."""
    if type(rollback) is not bool:
        raise ContractError("flash role is not boolean")
    if owner_usb_inventory_sha256 is not None and (type(owner_usb_inventory_sha256) is not str or re.fullmatch(r"[0-9a-f]{64}", owner_usb_inventory_sha256) is None):
        raise ContractError("owner USB inventory binding is not exact")
    if owner_adb_role is not None and owner_adb_role not in {ADB_ROLE_NATIVE, ADB_ROLE_RECOVERY}:
        raise ContractError("owner endpoint role binding is not exact")
    if owner_usb_inventory_sha256 is not None and owner_adb_role is None:
        raise ContractError("owner endpoint role binding is missing")
    if owner_adb_inventory_sha256 is not None and (type(owner_adb_inventory_sha256) is not str or re.fullmatch(r"[0-9a-f]{64}", owner_adb_inventory_sha256) is None or owner_adb_role != ADB_ROLE_RECOVERY or owner_usb_inventory_sha256 is None):
        raise ContractError("owner ADB inventory binding is not exact")
    if owner_adb_role == ADB_ROLE_RECOVERY and owner_adb_inventory_sha256 is None:
        raise ContractError("recovery ADB inventory binding is missing")
    if owner_adb_role == ADB_ROLE_NATIVE and owner_adb_inventory_sha256 is not None:
        raise ContractError("Native owner binding must not carry an ADB digest")
    helper_phase_timeout = max(1, (timeout_sec - 30) // 2)
    return (
        str(PYTHON), str(FLASH), artifact["path"],
        "--adb", str(ADB),
        *(
            ("--reuse-bound-recovery-or-from-native",)
            if rollback
            else ("--from-native", "--require-stable-adb-baseline")
        ),
        *(
            (
                "--owner-fixed-bridge-preflight",
                "--owner-expect-usb-inventory-sha256",
                owner_usb_inventory_sha256,
                *(
                    (
                        "--owner-expect-adb-inventory-sha256",
                        owner_adb_inventory_sha256,
                    )
                    if owner_adb_inventory_sha256 is not None
                    else ()
                ),
                "--owner-expect-adb-role",
                owner_adb_role,
            )
            if owner_usb_inventory_sha256 is not None
            else ()
        ),
        "--expect-recovery-serial-sha256", recovery_serial_sha256,
        "--expect-version", artifact["version"],
        "--expect-sha256", artifact["sha256"],
        "--expect-readback-sha256", artifact["sha256"],
        "--verify-protocol", "selftest",
        "--owner-receipt-mode", OWNER_RECEIPT_MODE,
        "--recovery-timeout", str(helper_phase_timeout),
        "--bridge-timeout", str(helper_phase_timeout),
    )
