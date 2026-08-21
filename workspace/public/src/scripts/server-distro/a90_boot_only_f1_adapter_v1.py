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
import shlex
import signal
import stat
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from a90_boot_only_f1_minimal_v1 import (
    _MODULE_SENTINEL as MINIMAL_MODULE_SENTINEL,
    ContractError,
    EffectResult,
    Snapshot,
    canonical_json,
    sha256_bytes,
)


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

    def __init__(self, log_directory: Path) -> None:
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
        or not value["systemReturnCommandOk"]
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
            "version": self._a90ctl(
                "version", ["version"], self._remaining(deadline, cap=15)
            ),
            "selftest": self._a90ctl(
                "selftest", ["selftest"], self._remaining(deadline, cap=15)
            ),
            "status": self._a90ctl(
                "status", ["status"], self._remaining(deadline, cap=15)
            ),
            "bootId": self._a90ctl(
                "boot-id",
                ["cat", "/proc/sys/kernel/random/boot_id"],
                self._remaining(deadline, cap=15),
            ),
        }
        version_text = _validate_command(receipts["version"], ["version"], "version")
        selftest_text = _validate_command(receipts["selftest"], ["selftest"], "selftest")
        status_text = _validate_command(receipts["status"], ["status"], "status")
        boot_text = _validate_command(
            receipts["bootId"], ["cat", "/proc/sys/kernel/random/boot_id"], "boot ID"
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
            and (state_absent or not require_fresh_state)
        )
        stable_identity = {
            "usbInventory": usb_inventory,
            "bridge": bridge,
            "bootId": boot_id,
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

    def flash(self, artifact: dict[str, Any], *, rollback: bool, timeout_sec: int) -> EffectResult:
        role = "rollback" if rollback else "candidate"
        argv = fixed_flash_argv(
            artifact,
            recovery_serial_sha256=self.recovery_serial_sha256,
            timeout_sec=timeout_sec,
            rollback=rollback,
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


def fixed_flash_argv(
    artifact: dict[str, Any],
    *,
    recovery_serial_sha256: str,
    timeout_sec: int,
    rollback: bool = False,
) -> tuple[str, ...]:
    """Return the sole reviewed helper command for receipt reconstruction."""
    if type(rollback) is not bool:
        raise ContractError("flash role is not boolean")
    helper_phase_timeout = max(1, (timeout_sec - 30) // 2)
    return (
        str(PYTHON), str(FLASH), artifact["path"],
        "--adb", str(ADB),
        *(
            ("--reuse-bound-recovery-or-from-native",)
            if rollback
            else ("--from-native", "--require-stable-adb-baseline")
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
