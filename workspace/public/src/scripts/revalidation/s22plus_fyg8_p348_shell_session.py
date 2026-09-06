"""Host-only retained read-only shell lease for the S22+ P348 successor.

The module owns the durable lease and action journal only.  It does not select
an endpoint, open a tty, invoke a shell, or grant device authority.  P348 is a
new namespace: consumed P335/P343/P344 journals and source identities are not
reopened or projected into this lease.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import time
from typing import Any, Mapping


SCHEMA = "s22plus_fyg8_p348_shell_lease_v1"
LEASE_SCHEMA = SCHEMA
ACTION_RESULT_SCHEMA = "s22plus_fyg8_p348_shell_action_result_v1"
SUMMARY_SCHEMA = "s22plus_fyg8_p348_shell_summary_v1"
ACTIVE_RESULT_SCHEMA = "device_action_f1_p348_shell_active_v1"
VERSION = 1
MAX_LEASE_SECONDS = 3_600
MAX_ACTIONS = 16
SESSION_WINDOW_SECONDS = 30
SESSION_WINDOW_NS = SESSION_WINDOW_SECONDS * 1_000_000_000
MAX_COMMAND_BYTES = 1_023
MAX_OUTPUT_BYTES = 128 * 1024
MAX_RECEIPT_BYTES = 256 * 1024
MAX_FILE_BYTES = 2 * 1024 * 1024
ACTION_NAME = "shell-command"
ACTION_NAMES = (ACTION_NAME,)
DIRECTORY = "p348-shell-session"
LEASE_DIRECTORY = DIRECTORY
EVIDENCE_DIRECTORY = "p348-shell-actions"
OWNER = "s22plus-fyg8-p348"
PROOF_KEY = "p348_readonly_research_shell_qualification"
CLOCK_KIND = "CLOCK_BOOTTIME"
SUSPEND_TOLERANCE_NS = 1_000_000
HOST_EPOCH_PATH = Path("/proc/sys/kernel/random/boot_id")
TARGET = {
    "model": "SM-S906N",
    "device": "g0q",
    "firmware_incremental": "S906NKSS7FYG8",
}
ZERO = "0" * 64
HEX64 = re.compile(r"^[0-9a-f]{64}$")
RUN_ID = re.compile(r"^[0-9a-f]{32}$")
RELATIVE_PATH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$")


class LeaseError(ValueError):
    """The P348 lease namespace or a caller value is invalid."""


class RollbackRequired(LeaseError):
    """Only the already-bound rollback owner may continue."""


def canonical_bytes(value: Any) -> bytes:
    """Return the only JSON representation accepted by this journal."""

    def check(item: Any) -> None:
        if isinstance(item, float):
            raise LeaseError("floating-point JSON is not permitted")
        if isinstance(item, Mapping):
            for key, child in item.items():
                if type(key) is not str:
                    raise LeaseError("JSON object keys must be strings")
                check(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                check(child)
        elif item is not None and type(item) not in (str, int, bool):
            raise LeaseError("unsupported JSON value")

    check(value)
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise LeaseError("value is not canonical JSON") from exc


def parse_canonical(payload: bytes | bytearray, label: str = "JSON") -> dict[str, Any]:
    """Parse canonical JSON, rejecting duplicate keys and non-finite values."""

    if not isinstance(payload, (bytes, bytearray)):
        raise LeaseError(f"{label} is not bytes")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise LeaseError(f"{label} contains duplicate keys")
            result[key] = value
        return result

    def constant(value: str) -> None:
        raise LeaseError(f"{label} contains non-finite JSON: {value}")

    raw = bytes(payload)
    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant
        )
    except (UnicodeDecodeError, json.JSONDecodeError, LeaseError) as exc:
        raise LeaseError(f"{label} is not valid canonical JSON") from exc
    if type(value) is not dict or canonical_bytes(value) != raw:
        raise LeaseError(f"{label} is not canonical")
    return value


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def identity(payload: bytes) -> dict[str, Any]:
    if type(payload) is not bytes:
        raise LeaseError("identity payload is not bytes")
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        raise LeaseError(f"{label} has an unexpected schema")
    return value


def _hex(value: Any, label: str) -> str:
    if type(value) is not str or HEX64.fullmatch(value) is None or value == ZERO:
        raise LeaseError(f"{label} must be nonzero lowercase hexadecimal")
    return value


def _integer(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise LeaseError(f"{label} must be an integer >= {minimum}")
    return value


def _signed_integer(value: Any, label: str) -> int:
    if type(value) is not int or not -(1 << 62) <= value <= (1 << 62):
        raise LeaseError(f"{label} is not a bounded integer")
    return value


def _run_id(value: Any, label: str = "run_id") -> str:
    if type(value) is not str or RUN_ID.fullmatch(value) is None:
        raise LeaseError(f"{label} is not a 16-byte lowercase hexadecimal value")
    return value


def _command_identity(value: Any, label: str = "command") -> dict[str, Any]:
    command = _keys(value, {"size", "sha256"}, label)
    if type(command["size"]) is not int or not 1 <= command["size"] <= MAX_COMMAND_BYTES:
        raise LeaseError(f"{label}.size is outside the command bound")
    _hex(command["sha256"], f"{label}.sha256")
    return command


def _validate_path(value: Any, label: str) -> str:
    if type(value) is not str or RELATIVE_PATH.fullmatch(value) is None:
        raise LeaseError(f"{label} is not a safe relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.parts[:1] == (".",):
        raise LeaseError(f"{label} escapes the private namespace")
    return value


def clock_now_ns() -> int:
    """Return suspend-aware elapsed time used by every live lease decision."""

    clock = getattr(time, "CLOCK_BOOTTIME", None)
    if clock is None or not hasattr(time, "clock_gettime_ns"):
        raise LeaseError("CLOCK_BOOTTIME is unavailable")
    return time.clock_gettime_ns(clock)


def monotonic_now_ns() -> int:
    try:
        return time.monotonic_ns()
    except AttributeError as exc:
        raise LeaseError("CLOCK_MONOTONIC is unavailable") from exc


def suspend_delta_ns() -> int:
    """Return the host BOOTTIME minus MONOTONIC suspend accumulator."""

    return clock_now_ns() - monotonic_now_ns()


def host_epoch() -> str:
    """Return the current host boot epoch as a private digest."""

    try:
        value = HOST_EPOCH_PATH.read_bytes().strip()
    except OSError as exc:
        raise LeaseError("host boot epoch is unavailable") from exc
    if not value:
        raise LeaseError("host boot epoch is empty")
    return hashlib.sha256(value).hexdigest()


def _stat(path: Path, *, directory: bool = False, writable: bool = False) -> os.stat_result:
    try:
        value = path.lstat()
    except OSError as exc:
        raise LeaseError(f"missing {path.name}") from exc
    mode = value.st_mode
    if directory:
        good = stat.S_ISDIR(mode) and stat.S_IMODE(mode) == 0o700
    else:
        required_mode = 0o600 if writable else 0o400
        good = stat.S_ISREG(mode) and value.st_nlink == 1 and stat.S_IMODE(mode) == required_mode
    if not good or path.resolve() != path.absolute():
        raise LeaseError(f"unsafe namespace entry: {path.name}")
    return value


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_once(path: Path, payload: bytes, *, mode: int = 0o400) -> dict[str, Any]:
    if type(payload) is not bytes or len(payload) > MAX_FILE_BYTES:
        raise LeaseError("journal payload exceeds the bound")
    _stat(path.parent, directory=True)
    if path.exists() or path.is_symlink():
        raise LeaseError(f"refusing to replace {path.name}")
    temporary = path.with_name("." + path.name + ".tmp")
    if temporary.exists() or temporary.is_symlink():
        raise LeaseError(f"temporary publication already exists: {path.name}")
    descriptor = -1
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            mode,
        )
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise LeaseError("journal write made no progress")
            offset += written
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        if stat.S_IMODE(metadata.st_mode) != mode or metadata.st_nlink != 1 or metadata.st_size != len(payload):
            raise LeaseError(f"new journal record identity differs: {path.name}")
        os.close(descriptor)
        descriptor = -1
        os.link(temporary, path, follow_symlinks=False)
        _fsync_dir(path.parent)
        os.unlink(temporary)
        _fsync_dir(path.parent)
    except OSError as exc:
        raise RollbackRequired(f"uncertain publication of {path.name}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    return identity(payload)


def write_bytes_once(path: Path, payload: bytes) -> dict[str, Any]:
    """Durably create a private 0400 evidence file without replacing it."""

    return _write_once(path, payload)


def _read_bytes(path: Path, maximum: int = MAX_FILE_BYTES) -> tuple[bytes, os.stat_result]:
    before = _stat(path)
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, maximum + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > maximum:
                raise RollbackRequired(f"record exceeds bound: {path.name}")
        inside = os.fstat(descriptor)
    except OSError as exc:
        raise RollbackRequired(f"uncertain read of {path.name}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    after = _stat(path)
    fields = lambda item: (
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_nlink,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    if fields(before) != fields(inside) or fields(before) != fields(after):
        raise RollbackRequired(f"record changed while reading: {path.name}")
    return b"".join(chunks), after


def read_json(path: Path, label: str = "JSON") -> dict[str, Any]:
    payload, _ = _read_bytes(path)
    return parse_canonical(payload, label)


def _root(path: str | os.PathLike[str]) -> Path:
    value = Path(path).absolute()
    _stat(value, directory=True)
    return value


def _mkdir(path: Path) -> None:
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        _stat(path, directory=True)
    _fsync_dir(path.parent)


def _validate_shell(value: Any) -> dict[str, Any]:
    shell = _keys(
        value,
        {
            "capability",
            "command_encoding",
            "max_command_bytes",
            "max_output_bytes",
            "observer_contract",
            "runtime_contract",
            "run_id",
            "session_seconds",
        },
        "shell",
    )
    if shell["capability"] != "read-only-shell" or shell["command_encoding"] != "utf-8":
        raise LeaseError("shell capability differs")
    if shell["max_command_bytes"] != MAX_COMMAND_BYTES or shell["max_output_bytes"] != MAX_OUTPUT_BYTES:
        raise LeaseError("shell byte bounds differ")
    if shell["session_seconds"] != SESSION_WINDOW_SECONDS:
        raise LeaseError("shell session bound differs")
    _run_id(shell["run_id"], "shell.run_id")
    for key in ("observer_contract", "runtime_contract"):
        if type(shell[key]) is not str or not 1 <= len(shell[key]) <= 160:
            raise LeaseError(f"shell.{key} differs")
    return shell


def validate_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate exact target, shell capability, candidate and recovery identity."""

    binding = _keys(
        value,
        {"target", "topology", "candidate", "key", "shell", "recovery", "per_boot_id"},
        "binding",
    )
    target = _keys(binding["target"], set(TARGET), "target")
    if target != TARGET:
        raise LeaseError("target binding differs")
    topology = _keys(binding["topology"], {"sha256"}, "topology")
    _hex(topology["sha256"], "topology.sha256")
    candidate = _keys(binding["candidate"], {"run_id", "boot_sha256", "ap_sha256"}, "candidate")
    _run_id(candidate["run_id"], "candidate.run_id")
    _hex(candidate["boot_sha256"], "candidate.boot_sha256")
    _hex(candidate["ap_sha256"], "candidate.ap_sha256")
    key = _keys(binding["key"], {"size", "sha256"}, "key")
    if type(key["size"]) is not int or key["size"] != 32:
        raise LeaseError("private key size differs")
    _hex(key["sha256"], "key.sha256")
    shell = _validate_shell(binding["shell"])
    if shell["run_id"] != candidate["run_id"]:
        raise LeaseError("shell and candidate run IDs differ")
    recovery = _keys(binding["recovery"], {"kind", "owner", "rollback_ap_sha256"}, "recovery")
    if recovery["kind"] != "magisk_boot_only" or recovery["owner"] != OWNER:
        raise LeaseError("recovery owner differs")
    _hex(recovery["rollback_ap_sha256"], "recovery.rollback_ap_sha256")
    _hex(binding["per_boot_id"], "per_boot_id")
    return binding


def _validate_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    observation = _keys(value, {"state", "candidate_boot_ready", "journal_sha256"}, "observation")
    if observation["state"] != "OBSERVED" or observation["candidate_boot_ready"] is not True:
        raise LeaseError("observation is not OBSERVED and candidate_boot_ready")
    _hex(observation["journal_sha256"], "observation.journal_sha256")
    return observation


def _proof(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LeaseError("P348 observation is not an object")
    candidate = value.get(PROOF_KEY)
    if candidate is None:
        candidate = value.get("p348_readonly_research_shell")
    if not isinstance(candidate, Mapping):
        raise LeaseError("P348 qualification proof is absent")
    return candidate


class ShellLease:
    """Strict no-clobber P348 lease and one-shot action journal."""

    def __init__(
        self,
        run_dir: Path,
        lease: dict[str, Any],
        guard: dict[str, Any],
        actions: list[tuple[dict[str, Any], dict[str, Any] | None]],
        terminal: dict[str, Any] | None,
    ) -> None:
        self.run_dir = run_dir
        self.lease = lease
        self.guard = guard
        self.actions = actions
        self.terminal = terminal
        self.binding = validate_binding(lease["binding"])

    @classmethod
    def publish(
        cls,
        run_dir: str | os.PathLike[str],
        binding: Mapping[str, Any],
        observation: Mapping[str, Any],
        *,
        now_ns: int | None = None,
        duration_seconds: int = MAX_LEASE_SECONDS,
        lease_id: str | None = None,
        host_epoch_value: str | None = None,
    ) -> "ShellLease":
        root = _root(run_dir)
        if any(root.iterdir()):
            raise LeaseError("P348 lease namespace is not fresh")
        binding_value = validate_binding(dict(binding))
        observation_value = _validate_observation(dict(observation))
        now = clock_now_ns() if now_ns is None else _integer(now_ns, "opened elapsed time")
        if type(duration_seconds) is not int or not 0 < duration_seconds <= MAX_LEASE_SECONDS:
            raise LeaseError("lease duration exceeds one-hour bound")
        epoch = host_epoch() if host_epoch_value is None else host_epoch_value
        _hex(epoch, "host_epoch")
        lease_id = secrets.token_hex(16) if lease_id is None else lease_id
        _run_id(lease_id, "lease_id")
        _mkdir(root / "events")
        _mkdir(root / "actions")
        lease = {
            "binding": binding_value,
            "binding_sha256": digest(binding_value),
            "candidate_boot_ready": True,
        "clock_kind": CLOCK_KIND,
        "expires_elapsed_ns": now + duration_seconds * 1_000_000_000,
        "host_epoch": epoch,
            "kind": "p348-shell-lease",
            "lease_id": lease_id,
            "max_actions": MAX_ACTIONS,
            "max_sessions_per_action": 1,
        "no_replay": True,
        "observation": observation_value,
        "opened_monotonic_ns": monotonic_now_ns(),
        "opened_elapsed_ns": now,
        "opened_suspend_delta_ns": suspend_delta_ns(),
            "ordinary_state": "OBSERVED",
            "schema": SCHEMA,
            "shell_capability": binding_value["shell"],
            "state": "P348_SHELL_ACTIVE",
            "version": VERSION,
        }
        lease_raw = canonical_bytes(lease)
        _write_once(root / "lease.json", lease_raw)
        guard = {
            "binding_sha256": lease["binding_sha256"],
            "clock_kind": CLOCK_KIND,
            "expires_elapsed_ns": lease["expires_elapsed_ns"],
            "host_epoch": epoch,
            "kind": "p348-shell-lease-guard",
            "lease_id": lease_id,
            "lease_sha256": hashlib.sha256(lease_raw).hexdigest(),
            "no_replay": True,
            "opened_monotonic_ns": lease["opened_monotonic_ns"],
            "opened_suspend_delta_ns": lease["opened_suspend_delta_ns"],
            "schema": SCHEMA,
            "state": "ACTIVE",
            "version": VERSION,
        }
        _write_once(root / "lease.guard.json", canonical_bytes(guard))
        return cls.open(root)

    create = publish

    @classmethod
    def open(
        cls,
        run_dir: str | os.PathLike[str],
        *,
        validate_clock: bool = True,
    ) -> "ShellLease":
        root = _root(run_dir)
        entries = {entry.name for entry in os.scandir(root)}
        expected = {"lease.json", "lease.guard.json", "events", "actions"}
        if entries - expected:
            raise LeaseError("foreign P348 lease namespace entry")
        present = entries & {"lease.json", "lease.guard.json"}
        if len(present) == 1:
            raise RollbackRequired("partial P348 lease/guard publication")
        if present != {"lease.json", "lease.guard.json"}:
            raise LeaseError("P348 lease is absent")
        _stat(root / "events", directory=True)
        _stat(root / "actions", directory=True)
        lease = _keys(
            read_json(root / "lease.json", "P348 lease"),
            {
                "binding", "binding_sha256", "candidate_boot_ready", "clock_kind",
                "expires_elapsed_ns", "host_epoch", "kind", "lease_id", "max_actions",
                "max_sessions_per_action", "no_replay", "observation", "opened_elapsed_ns",
                "opened_monotonic_ns", "opened_suspend_delta_ns", "ordinary_state", "schema",
                "shell_capability", "state", "version",
            },
            "lease",
        )
        if (
            lease["schema"] != SCHEMA
            or lease["version"] != VERSION
            or lease["kind"] != "p348-shell-lease"
            or lease["state"] != "P348_SHELL_ACTIVE"
            or lease["ordinary_state"] != "OBSERVED"
            or lease["candidate_boot_ready"] is not True
            or lease["clock_kind"] != CLOCK_KIND
            or lease["max_actions"] != MAX_ACTIONS
            or lease["max_sessions_per_action"] != 1
            or lease["no_replay"] is not True
        ):
            raise RollbackRequired("P348 lease identity or bounds differ")
        _run_id(lease["lease_id"], "lease_id")
        _hex(lease["host_epoch"], "host_epoch")
        opened = _integer(lease["opened_elapsed_ns"], "opened elapsed time")
        _integer(lease["opened_monotonic_ns"], "opened monotonic time")
        opened_delta = _signed_integer(lease["opened_suspend_delta_ns"], "opened suspend delta")
        expires = _integer(lease["expires_elapsed_ns"], "expires elapsed time")
        if expires <= opened or expires - opened > MAX_LEASE_SECONDS * 1_000_000_000:
            raise LeaseError("P348 lease deadline is invalid")
        binding = validate_binding(lease["binding"])
        if lease["shell_capability"] != binding["shell"]:
            raise RollbackRequired("P348 shell capability binding differs")
        if lease["binding_sha256"] != digest(binding):
            raise RollbackRequired("P348 binding digest differs")
        _validate_observation(lease["observation"])
        guard = _keys(
            read_json(root / "lease.guard.json", "P348 lease guard"),
            {
                "binding_sha256", "clock_kind", "expires_elapsed_ns", "host_epoch",
                "kind", "lease_id", "lease_sha256", "no_replay", "schema", "state", "version",
                "opened_monotonic_ns", "opened_suspend_delta_ns",
            },
            "guard",
        )
        if (
            guard["schema"] != SCHEMA
            or guard["version"] != VERSION
            or guard["kind"] != "p348-shell-lease-guard"
            or guard["state"] != "ACTIVE"
            or guard["no_replay"] is not True
            or guard["clock_kind"] != CLOCK_KIND
            or guard["opened_monotonic_ns"] != lease["opened_monotonic_ns"]
            or guard["opened_suspend_delta_ns"] != lease["opened_suspend_delta_ns"]
        ):
            raise RollbackRequired("P348 lease guard differs")
        if (
            guard["lease_id"] != lease["lease_id"]
            or guard["binding_sha256"] != lease["binding_sha256"]
            or guard["host_epoch"] != lease["host_epoch"]
            or guard["expires_elapsed_ns"] != lease["expires_elapsed_ns"]
            or guard["lease_sha256"] != digest(lease)
        ):
            raise RollbackRequired("P348 guard binding differs")
        actions = cls._load_actions(root / "actions", lease["lease_id"], lease["binding_sha256"])
        terminal = cls._load_terminal(root / "events", lease["lease_id"], lease["binding_sha256"], lease["host_epoch"])
        instance = cls(root, lease, guard, actions, terminal)
        if validate_clock:
            try:
                current_epoch = host_epoch()
            except LeaseError:
                raise RollbackRequired("host boot epoch cannot be revalidated")
            if current_epoch != lease["host_epoch"]:
                instance._terminal("DRIFT", "host boot epoch changed")
                raise RollbackRequired("host boot epoch changed")
            if clock_now_ns() < opened:
                instance._terminal("DRIFT", "host elapsed clock moved backwards")
                raise RollbackRequired("host elapsed clock moved backwards")
            try:
                delta = suspend_delta_ns()
            except LeaseError as exc:
                instance._terminal("DRIFT", "suspend-aware clock cannot be revalidated")
                raise RollbackRequired("suspend-aware clock cannot be revalidated") from exc
            if delta - opened_delta > SUSPEND_TOLERANCE_NS:
                instance._terminal("DRIFT", "host suspend detected")
                raise RollbackRequired("host suspend detected")
        return instance

    @staticmethod
    def _load_actions(
        directory: Path, lease_id: str, binding_sha256: str
    ) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
        files = {entry.name for entry in os.scandir(directory)}
        pattern = re.compile(r"^([0-9]{2})-(intent|result)\.json$")
        parsed: dict[int, dict[str, Path]] = {}
        for name in files:
            match = pattern.fullmatch(name)
            if match is None:
                raise RollbackRequired("foreign or partial P348 action journal entry")
            ordinal, kind = int(match.group(1)), match.group(2)
            if not 1 <= ordinal <= MAX_ACTIONS or kind in parsed.setdefault(ordinal, {}):
                raise RollbackRequired("P348 action ordinal is invalid or duplicated")
            parsed[ordinal][kind] = directory / name
        actions: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
        for ordinal in range(1, (max(parsed) if parsed else 0) + 1):
            row = parsed.get(ordinal)
            if row is None or "intent" not in row:
                raise RollbackRequired("P348 action journal has a gap")
            intent = _keys(
                read_json(row["intent"], "P348 action intent"),
                {
                    "action", "binding_sha256", "command", "command_path", "host_epoch",
                    "issued_elapsed_ns", "kind", "lease_id", "no_replay", "ordinal", "schema", "version",
                },
                "action intent",
            )
            if (
                intent["schema"] != SCHEMA
                or intent["version"] != VERSION
                or intent["kind"] != "action-intent"
                or intent["lease_id"] != lease_id
                or intent["binding_sha256"] != binding_sha256
                or intent["ordinal"] != ordinal
                or intent["action"] != ACTION_NAME
                or intent["host_epoch"] == ZERO
                or intent["no_replay"] is not True
            ):
                raise RollbackRequired("P348 action intent binding differs")
            _command_identity(intent["command"], "action intent command")
            _validate_path(intent["command_path"], "action intent command_path")
            _hex(intent["host_epoch"], "action intent host_epoch")
            _integer(intent["issued_elapsed_ns"], "action intent time")
            result: dict[str, Any] | None = None
            if "result" in row:
                result = _keys(
                    read_json(row["result"], "P348 action result journal"),
                    {
                        "action", "binding_sha256", "command", "command_outcome", "continuation_allowed",
                        "intent_sha256", "issued_elapsed_ns", "kind", "lease_id", "no_replay", "ordinal",
                        "receipt_bytes", "receipt_sha256", "schema", "session_complete", "status", "version",
                    },
                    "action result",
                )
                if (
                    result["schema"] != SCHEMA
                    or result["version"] != VERSION
                    or result["kind"] != "action-result"
                    or result["lease_id"] != lease_id
                    or result["binding_sha256"] != binding_sha256
                    or result["ordinal"] != ordinal
                    or result["action"] != intent["action"]
                    or result["intent_sha256"] != digest(intent)
                    or result["no_replay"] is not True
                    or result["status"] not in ("completed", "failed", "uncertain")
                    or type(result["session_complete"]) is not bool
                    or type(result["continuation_allowed"]) is not bool
                    or type(result["command_outcome"]) is not str
                ):
                    raise RollbackRequired("P348 action result binding differs")
                _command_identity(result["command"], "action result command")
                _integer(result["issued_elapsed_ns"], "action result time")
                if result["command"] != intent["command"]:
                    raise RollbackRequired("P348 action result command differs")
                receipt_bytes = _integer(result["receipt_bytes"], "receipt_bytes")
                if receipt_bytes > MAX_RECEIPT_BYTES:
                    raise RollbackRequired("P348 action receipt is too large")
                _hex(result["receipt_sha256"], "receipt_sha256")
            actions.append((intent, result))
        return actions

    @staticmethod
    def _load_terminal(
        directory: Path, lease_id: str, binding_sha256: str, host_epoch_value: str
    ) -> dict[str, Any] | None:
        files = {entry.name for entry in os.scandir(directory)}
        if not files:
            return None
        if files != {"0000-rollback-required.json"}:
            raise RollbackRequired("foreign or duplicate P348 terminal event")
        event = _keys(
            read_json(directory / "0000-rollback-required.json", "P348 terminal event"),
            {
                "binding_sha256", "host_epoch", "issued_elapsed_ns", "kind", "lease_id", "no_replay",
                "previous_sha256", "reason", "schema", "sequence", "trigger", "version",
            },
            "terminal event",
        )
        if (
            event["schema"] != SCHEMA
            or event["version"] != VERSION
            or event["kind"] != "lease-event"
            or event["lease_id"] != lease_id
            or event["binding_sha256"] != binding_sha256
            or event["host_epoch"] != host_epoch_value
            or event["sequence"] != 0
            or event["trigger"] not in ("STOP", "EXPIRY", "DRIFT", "ACTION_RESULT", "ACTION_BUDGET")
            or event["previous_sha256"] != ZERO
            or event["no_replay"] is not True
        ):
            raise RollbackRequired("P348 terminal event binding differs")
        _integer(event["issued_elapsed_ns"], "terminal event time")
        reason = event["reason"]
        if type(reason) is not str or not 1 <= len(reason) <= 160 or any(ord(c) < 0x20 or ord(c) > 0x7E for c in reason):
            raise RollbackRequired("P348 terminal event reason is invalid")
        return event

    def _refresh(self) -> None:
        fresh = type(self).open(self.run_dir)
        self.__dict__.update(fresh.__dict__)

    def _check_clock(self, now: int) -> None:
        if now < self.lease["opened_elapsed_ns"]:
            self._terminal("DRIFT", "host elapsed clock moved backwards", now)
            raise RollbackRequired("host elapsed clock moved backwards")
        try:
            current_epoch = host_epoch()
        except LeaseError as exc:
            self._terminal("DRIFT", "host boot epoch cannot be revalidated", now)
            raise RollbackRequired("host boot epoch cannot be revalidated") from exc
        if current_epoch != self.lease["host_epoch"]:
            self._terminal("DRIFT", "host boot epoch changed", now)
            raise RollbackRequired("host boot epoch changed")
        try:
            delta = suspend_delta_ns()
        except LeaseError as exc:
            self._terminal("DRIFT", "suspend-aware clock cannot be revalidated", now)
            raise RollbackRequired("suspend-aware clock cannot be revalidated") from exc
        if delta - self.lease["opened_suspend_delta_ns"] > SUSPEND_TOLERANCE_NS:
            self._terminal("DRIFT", "host suspend detected", now)
            raise RollbackRequired("host suspend detected")

    def _terminal(self, trigger: str, reason: str, now_ns: int | None = None) -> None:
        if self.terminal is not None:
            return
        if trigger not in ("STOP", "EXPIRY", "DRIFT", "ACTION_RESULT", "ACTION_BUDGET"):
            raise LeaseError("unknown P348 rollback trigger")
        if type(reason) is not str or not 1 <= len(reason) <= 160 or any(ord(c) < 0x20 or ord(c) > 0x7E for c in reason):
            raise LeaseError("P348 rollback reason is invalid")
        issued = clock_now_ns() if now_ns is None else _integer(now_ns, "terminal event time")
        event = {
            "binding_sha256": self.lease["binding_sha256"],
            "host_epoch": self.lease["host_epoch"],
            "issued_elapsed_ns": issued,
            "kind": "lease-event",
            "lease_id": self.lease["lease_id"],
            "no_replay": True,
            "previous_sha256": ZERO,
            "reason": reason,
            "schema": SCHEMA,
            "sequence": 0,
            "trigger": trigger,
            "version": VERSION,
        }
        _write_once(self.run_dir / "events" / "0000-rollback-required.json", canonical_bytes(event))
        self.terminal = event

    def _require_binding(self, binding: Mapping[str, Any]) -> None:
        try:
            current = validate_binding(dict(binding))
        except LeaseError as exc:
            self._terminal("DRIFT", "current P348 binding is invalid")
            raise RollbackRequired("current P348 binding is invalid") from exc
        if canonical_bytes(current) != canonical_bytes(self.binding):
            self._terminal("DRIFT", "exact P348 binding drifted")
            raise RollbackRequired("exact P348 binding drifted")

    def snapshot(self, *, now_ns: int | None = None) -> dict[str, Any]:
        now = clock_now_ns() if now_ns is None else _integer(now_ns, "snapshot elapsed time")
        pending = next((intent for intent, result in self.actions if result is None), None)
        expired = now >= self.lease["expires_elapsed_ns"]
        failed = any(result is not None and result["status"] != "completed" for _, result in self.actions)
        rollback = self.terminal is not None or pending is not None or expired or failed
        reason = (
            self.terminal["reason"]
            if self.terminal
            else "active action intent unresolved"
            if pending
            else "P348 lease expired"
            if expired
            else "P348 action did not permit continuation"
            if failed
            else ""
        )
        return {
            "schema": SCHEMA,
            "lease_id": self.lease["lease_id"],
            "state": "ROLLBACK_REQUIRED" if rollback else "ACTIVE",
            "rollback_required": rollback,
            "reason": reason,
            "binding_sha256": self.lease["binding_sha256"],
            "per_boot_id": self.binding["per_boot_id"],
            "host_epoch": self.lease["host_epoch"],
            "clock_kind": self.lease["clock_kind"],
            "opened_elapsed_ns": self.lease["opened_elapsed_ns"],
            "opened_monotonic_ns": self.lease["opened_monotonic_ns"],
            "opened_suspend_delta_ns": self.lease["opened_suspend_delta_ns"],
            "expires_elapsed_ns": self.lease["expires_elapsed_ns"],
            "actions_started": len(self.actions),
            "actions_completed": sum(result is not None and result["status"] == "completed" for _, result in self.actions),
            "actions_remaining": max(0, MAX_ACTIONS - len(self.actions)),
            "active_intent": pending["ordinal"] if pending else None,
            "terminal_event": self.terminal["trigger"] if self.terminal else None,
        }

    def begin_action(
        self,
        command: bytes | Mapping[str, Any],
        current_binding: Mapping[str, Any],
        *,
        command_path: str = "p348-shell-actions/action-01/command.bin",
        now_ns: int | None = None,
    ) -> dict[str, Any]:
        self._refresh()
        now = clock_now_ns() if now_ns is None else _integer(now_ns, "action elapsed time")
        self._check_clock(now)
        self._require_binding(current_binding)
        if isinstance(command, (bytes, bytearray)):
            command_value = identity(bytes(command))
        else:
            command_value = _command_identity(dict(command), "action command")
        if self.terminal is not None:
            raise RollbackRequired("P348 lease is rollback-required")
        if any(result is None for _, result in self.actions):
            raise RollbackRequired("active P348 action intent blocks new commands")
        if now >= self.lease["expires_elapsed_ns"]:
            self._terminal("EXPIRY", "P348 lease deadline expired", now)
            raise RollbackRequired("P348 lease expired")
        if self.lease["expires_elapsed_ns"] - now < SESSION_WINDOW_NS:
            self._terminal("EXPIRY", "less than one P348 session window remains", now)
            raise RollbackRequired("less than one P348 session window remains")
        if len(self.actions) >= MAX_ACTIONS:
            self._terminal("ACTION_BUDGET", "P348 action budget exhausted", now)
            raise RollbackRequired("P348 action budget exhausted")
        command_path = _validate_path(command_path, "action command_path")
        ordinal = len(self.actions) + 1
        intent = {
            "action": ACTION_NAME,
            "binding_sha256": self.lease["binding_sha256"],
            "command": command_value,
            "command_path": command_path.replace("action-01", f"action-{ordinal:02d}"),
            "host_epoch": self.lease["host_epoch"],
            "issued_elapsed_ns": now,
            "kind": "action-intent",
            "lease_id": self.lease["lease_id"],
            "no_replay": True,
            "ordinal": ordinal,
            "schema": SCHEMA,
            "version": VERSION,
        }
        _write_once(self.run_dir / "actions" / f"{ordinal:02d}-intent.json", canonical_bytes(intent))
        self.actions.append((intent, None))
        return intent

    def record_action_result(
        self,
        ordinal_or_intent: int | Mapping[str, Any],
        result: Mapping[str, Any],
        current_binding: Mapping[str, Any],
        *,
        now_ns: int | None = None,
    ) -> dict[str, Any]:
        self._refresh()
        now = clock_now_ns() if now_ns is None else _integer(now_ns, "result elapsed time")
        self._check_clock(now)
        self._require_binding(current_binding)
        if self.terminal is not None:
            raise RollbackRequired("P348 lease is rollback-required")
        pending = [(index, pair) for index, pair in enumerate(self.actions) if pair[1] is None]
        if len(pending) != 1:
            raise RollbackRequired("there is no matching P348 active action intent")
        index, (intent, _) = pending[0]
        if isinstance(ordinal_or_intent, int):
            if ordinal_or_intent != index + 1:
                raise RollbackRequired("P348 action ordinal differs")
        elif canonical_bytes(dict(ordinal_or_intent)) != canonical_bytes(intent):
            raise RollbackRequired("P348 action intent differs")
        values = _keys(
            dict(result),
            {"status", "command", "session_complete", "command_outcome", "continuation_allowed", "receipt_bytes", "receipt_sha256"},
            "P348 action result",
        )
        if values["status"] not in ("completed", "failed", "uncertain"):
            raise LeaseError("P348 action result status differs")
        _command_identity(values["command"], "P348 result command")
        if values["command"] != intent["command"]:
            self._terminal("DRIFT", "P348 action result command differs", now)
            raise RollbackRequired("P348 action result command differs")
        if type(values["session_complete"]) is not bool or type(values["continuation_allowed"]) is not bool:
            raise LeaseError("P348 action completion flags differ")
        if type(values["command_outcome"]) is not str or not values["command_outcome"]:
            raise LeaseError("P348 command outcome differs")
        receipt_bytes = _integer(values["receipt_bytes"], "receipt_bytes")
        if receipt_bytes > MAX_RECEIPT_BYTES:
            raise LeaseError("P348 action receipt is too large")
        receipt_sha256 = _hex(values["receipt_sha256"], "receipt_sha256")
        if now >= self.lease["expires_elapsed_ns"]:
            self._terminal("EXPIRY", "P348 lease deadline expired", now)
            raise RollbackRequired("P348 lease expired while publishing result")
        row = {
            "action": intent["action"],
            "binding_sha256": self.lease["binding_sha256"],
            "command": values["command"],
            "command_outcome": values["command_outcome"],
            "continuation_allowed": values["continuation_allowed"],
            "intent_sha256": digest(intent),
            "issued_elapsed_ns": now,
            "kind": "action-result",
            "lease_id": self.lease["lease_id"],
            "no_replay": True,
            "ordinal": index + 1,
            "receipt_bytes": receipt_bytes,
            "receipt_sha256": receipt_sha256,
            "schema": SCHEMA,
            "session_complete": values["session_complete"],
            "status": values["status"],
            "version": VERSION,
        }
        _write_once(self.run_dir / "actions" / f"{index + 1:02d}-result.json", canonical_bytes(row))
        self.actions[index] = (intent, row)
        if row["status"] != "completed" or row["continuation_allowed"] is not True:
            self._terminal("ACTION_RESULT", "P348 action does not permit continuation", now)
        elif index + 1 == MAX_ACTIONS:
            self._terminal("ACTION_BUDGET", "P348 action budget exhausted", now)
        return row

    def stop(self, reason: str = "operator stop") -> None:
        self._refresh()
        self._terminal("STOP", reason)

    def expire(self, *, now_ns: int | None = None) -> None:
        self._refresh()
        now = clock_now_ns() if now_ns is None else _integer(now_ns, "expiry elapsed time")
        self._terminal("EXPIRY", "P348 lease deadline expired", now)

    def mark_drift(self, reason: str = "exact P348 binding drifted") -> None:
        self._refresh()
        self._terminal("DRIFT", reason)


ResidentLease = ShellLease
publish_lease = ShellLease.publish
open_lease = ShellLease.open


def _variant(live: Any) -> Any:
    variants = getattr(getattr(live, "typed_evidence", None), "SHELL_VARIANTS", {})
    value = variants.get("p348") if hasattr(variants, "get") else None
    if value is None:
        raise live.F1LiveError("P348 shell variant is unavailable")
    return value


def _runtime_identity(variant: Any) -> tuple[str, str, str]:
    runtime = variant.runtime
    observer = variant.observer
    run_id = getattr(runtime, "P348_RUN_ID_HEX", None) or getattr(runtime, "P347_RUN_ID_HEX", None) or getattr(runtime, "P345_RUN_ID_HEX", None)
    if run_id is None:
        run_id_value = getattr(variant, "run_id", None)
        run_id = run_id_value.hex() if isinstance(run_id_value, bytes) else run_id_value
    run_id = _run_id(run_id, "P348 run_id")
    runtime_contract = str(getattr(runtime, "SCHEMA", getattr(runtime, "CONTRACT_ID", "p348-runtime")))
    observer_contract = str(getattr(observer, "CONTRACT_ID", getattr(observer, "SCHEMA", "p348-observer")))
    return run_id, runtime_contract, observer_contract


def _proof_value(observation: Mapping[str, Any]) -> Mapping[str, Any]:
    try:
        return _proof(observation)
    except LeaseError:
        return {}


def _first_hash(value: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        item = value.get(key)
        if isinstance(item, str) and HEX64.fullmatch(item) and item != ZERO:
            return item
    return None


def binding_for(live: Any, prepared: Any, observation: Mapping[str, Any]) -> dict[str, Any]:
    """Derive a fresh P348 binding from the exact prepared run and proof."""

    if not live._p348_bundle(prepared.bundle) or not live._p348_proof_ok(observation):
        raise live.F1LiveError("P348 initial proof differs")
    variant = _variant(live)
    run_id, runtime_contract, observer_contract = _runtime_identity(variant)
    proof = _proof_value(observation)
    sessions = proof.get("sessions") if isinstance(proof, Mapping) else None
    if not isinstance(sessions, list) or len(sessions) != 6:
        raise live.F1LiveError("P348 proof session count differs")
    per_boot_id = _first_hash(proof, "expected_boot_sha256")
    if per_boot_id is None:
        for row in sessions:
            if isinstance(row, Mapping):
                per_boot_id = _first_hash(row, "boot_id_sha256")
                if per_boot_id:
                    break
    if per_boot_id is None:
        raise live.F1LiveError("P348 proof boot identity is absent")
    topology_sha = _first_hash(observation, "candidate_topology_sha256", "topology_sha256")
    if topology_sha is None:
        raise live.F1LiveError("P348 candidate topology identity is absent")
    closure = {}
    try:
        closure = prepared.bundle.receipt["observation_contract"]["verification"]["ap_payload_closure"]
    except (AttributeError, KeyError, TypeError):
        pass
    boot_sha = _first_hash(closure.get("boot_image", {}) if isinstance(closure, Mapping) else {}, "sha256") or per_boot_id
    manifest = getattr(prepared.bundle, "manifest", {})
    candidate_ap = manifest.get("candidate_ap", {}) if isinstance(manifest, Mapping) else {}
    rollback_ap = manifest.get("rollback_ap", {}) if isinstance(manifest, Mapping) else {}
    ap_sha = _first_hash(candidate_ap, "sha256") or _first_hash(manifest, "candidate_ap_sha256")
    rollback_sha = _first_hash(rollback_ap, "sha256") or _first_hash(manifest, "rollback_ap_sha256")
    if ap_sha is None or rollback_sha is None:
        raise live.F1LiveError("P348 AP identities are absent")
    key = getattr(variant, "auth_key", None) or getattr(live, "P348_AUTH_KEY_IDENTITY", None)
    if not isinstance(key, Mapping):
        raise live.F1LiveError("P348 authentication key identity is absent")
    key = {"size": key.get("size"), "sha256": key.get("sha256")}
    runtime_target = getattr(variant.runtime, "TARGET", None)
    target = dict(runtime_target) if isinstance(runtime_target, Mapping) else dict(TARGET)
    binding = {
        "target": target,
        "topology": {"sha256": topology_sha},
        "candidate": {"run_id": run_id, "boot_sha256": boot_sha, "ap_sha256": ap_sha},
        "key": key,
        "shell": {
            "capability": "read-only-shell",
            "command_encoding": "utf-8",
            "max_command_bytes": MAX_COMMAND_BYTES,
            "max_output_bytes": MAX_OUTPUT_BYTES,
            "observer_contract": observer_contract,
            "runtime_contract": runtime_contract,
            "run_id": run_id,
            "session_seconds": SESSION_WINDOW_SECONDS,
        },
        "recovery": {
            "kind": "magisk_boot_only",
            "owner": OWNER,
            "rollback_ap_sha256": rollback_sha,
        },
        "per_boot_id": per_boot_id,
    }
    try:
        return validate_binding(binding)
    except LeaseError as exc:
        raise live.F1LiveError("P348 binding is invalid") from exc


def _state(live: Any, prepared: Any) -> dict[str, Any]:
    return live._state(prepared)


def before_guard_release(
    live: Any, prepared: Any, journal: Any, candidate: Any, observation: Mapping[str, Any], trace: Any
) -> dict[str, Any]:
    journal.transition("OBSERVED", "bounded_p348_candidate_observation_closed", observation)
    durable = live._reopen_candidate_observation(prepared)
    proof = bool(
        getattr(candidate, "completed", False)
        and durable.get("download_endpoint_absent") is True
        and durable.get("accepted") is True
        and live._p348_proof_ok(durable)
    )
    live._seal_p300_before_candidate_boot_ready(trace, journal, proof)
    if not proof:
        return {"proof": False, "shell_session_active": False}
    root = prepared.run_dir / DIRECTORY
    try:
        root.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise live.F1LiveError("P348 lease namespace already exists") from exc
    live.core._fsync_dir(prepared.run_dir)
    lease = ShellLease.publish(
        root,
        binding_for(live, prepared, durable),
        {"state": "OBSERVED", "candidate_boot_ready": True, "journal_sha256": journal.records()[-1]["record_sha256"]},
    )
    snapshot = lease.snapshot()
    current = _state(live, prepared)
    current.update(
        {
            "p348_shell_session_state": snapshot["state"],
            "p348_shell_session_active": True,
            "p348_shell_lease_id": snapshot["lease_id"],
            "p348_shell_lease_receipt": live._receipt(root / "lease.json", "P348 shell lease"),
            "p348_shell_guard_receipt": live._receipt(root / "lease.guard.json", "P348 shell guard"),
            "p348_shell_rollback_required": snapshot["rollback_required"],
            "p348_shell_host_epoch": snapshot["host_epoch"],
        }
    )
    live._save_state(prepared, current)
    return {"proof": True, "shell_session_active": True, "snapshot": snapshot}


def mark_rollback_required(live: Any, prepared: Any) -> None:
    root = prepared.run_dir / DIRECTORY
    if not root.exists() or root.is_symlink():
        return
    try:
        lease = ShellLease.open(root)
        if not lease.snapshot()["rollback_required"]:
            lease.stop("P348 F1 recovery requested")
    except (LeaseError, OSError):
        pass
    current = _state(live, prepared)
    current["p348_shell_session_active"] = False
    current["p348_shell_rollback_required"] = True
    live._save_state(prepared, current)


def after_guard_release(
    live: Any,
    prepared: Any,
    backend: Any,
    journal: Any,
    endpoint_dir: Path,
    endpoint_lease: Any,
    pending: Mapping[str, Any],
) -> dict[str, Any]:
    release = live._reopen_candidate_guard_release(prepared)
    current = _state(live, prepared)
    current.update(
        {
            "candidate_observer_guard_release_status": release["status"],
            "candidate_observer_guard_released": release["released"],
            "candidate_observer_guard_warning": release.get("warning"),
            "candidate_observer_guard_release_receipt_sha256": release.get("receipt_sha256"),
        }
    )
    supported = (
        pending["proof"]
        and release.get("released") is True
        and release.get("status") == "released"
    )
    live._save_state(prepared, current)
    if not pending["proof"] or not supported:
        mark_rollback_required(live, prepared)
        return live._finish_rollback(prepared, backend, journal, endpoint_dir, endpoint_lease)
    snapshot = ShellLease.open(prepared.run_dir / DIRECTORY).snapshot()
    if snapshot["rollback_required"]:
        mark_rollback_required(live, prepared)
        return live._finish_rollback(prepared, backend, journal, endpoint_dir, endpoint_lease)
    return {
        "schema": ACTIVE_RESULT_SCHEMA,
        "verdict": "P348_RETAINED_SHELL_SESSION_ACTIVE",
        "outcome_class": "p348_readonly_research_shell_active",
        "manifest_id": prepared.bundle.manifest["manifest_id"],
        "run_id": prepared.bundle.manifest["run_id"],
        "ordinary_f1_state": "OBSERVED",
        "candidate_boot_ready": True,
        "shell_session": snapshot,
        "f1_closed": False,
        "rollback_completed": False,
        "recovery_required": False,
    }


def _raw_identity(path: Path) -> dict[str, Any]:
    payload, metadata = _read_bytes(path, MAX_RECEIPT_BYTES)
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest(), "nlink": metadata.st_nlink, "mode": "0400"}


def _read_action_receipt(path: Path) -> dict[str, Any]:
    value = read_json(path, "P348 action receipt")
    if value.get("schema") != ACTION_RESULT_SCHEMA:
        raise LeaseError("P348 action receipt schema differs")
    return value


def _validate_retained_frames(
    live: Any,
    prepared: Any,
    value: Mapping[str, Any],
    action_dir: Path,
    command: bytes,
    binding: Mapping[str, Any],
    intent: Mapping[str, Any],
) -> None:
    """Reopen and parse the actual retained TX/RX frame streams when available."""

    raw_tx = value.get("raw_tx")
    raw_rx = value.get("raw_rx")
    if not isinstance(raw_tx, Mapping) or not isinstance(raw_rx, Mapping):
        raise LeaseError("P348 retained wire identities are absent")
    tx_path = action_dir / "session.tx.bin"
    rx_path = action_dir / "session.rx.bin"
    tx, _ = _read_bytes(tx_path, MAX_OUTPUT_BYTES * 2)
    rx, _ = _read_bytes(rx_path, MAX_OUTPUT_BYTES * 2)
    if raw_tx != identity(tx) or raw_rx != identity(rx):
        raise LeaseError("P348 retained wire identity differs")
    import device_action_raw_capture_v1 as raw_capture  # noqa: PLC0415

    capture_path = action_dir / "session-rx.capture.json"
    capture = raw_capture.load_handle(capture_path)
    if (
        capture.returncode != 0
        or capture.timed_out
        or capture.output_exceeded
        or capture.producer_error_type is not None
        or capture.stdout_path != action_dir / "session-rx.stdout.bin"
        or capture.stderr_path != action_dir / "session-rx.stderr.bin"
        or raw_capture.read_stdout(capture, maximum=512 * 1024) != rx
        or raw_capture.read_stderr(capture, maximum=1) != b""
    ):
        raise LeaseError("P348 raw-first capture receipt differs")
    raw_capture_value = value.get("raw_capture")
    if (
        not isinstance(raw_capture_value, Mapping)
        or raw_capture_value.get("receipt") != str(capture.receipt_path)
        or raw_capture_value.get("stdout") != dict(capture.stdout)
        or raw_capture_value.get("stderr") != dict(capture.stderr)
    ):
        raise LeaseError("P348 raw-first capture identity differs")
    variant = _variant(live)
    observer = variant.observer
    parser = getattr(observer, "parse_captured_session", None)
    if parser is None:
        raise LeaseError("P348 retained frame parser is unavailable")
    key_reader = getattr(live, "_p328_read_auth_key", None)
    opener = getattr(live, "_open_header_initial_observer_module", None)
    if not callable(key_reader) or not callable(opener):
        raise LeaseError("P348 retained frame codec is unavailable")
    key, key_sha = key_reader(prepared)
    if key_sha != binding["key"]["sha256"]:
        raise LeaseError("P348 retained frame key differs")
    codec = opener(variant.runtime, observer, "p348-shell-close")
    parsed = parser(codec, rx, tx, key)
    parsed_session = getattr(parsed, "session", parsed)
    commands = getattr(parsed_session, "commands", None)
    if not isinstance(commands, (tuple, list)) or len(commands) != 3:
        raise LeaseError("P348 retained frame command tuple differs")
    if commands[1].command != command:
        raise LeaseError("P348 retained frame command differs")
    audit = getattr(parsed_session, "audit", None)
    if audit is None or getattr(audit, "done_seen", False) is not True:
        raise LeaseError("P348 retained frame close witness is absent")

    # Rebuild the public receipt from the parsed frame object.  This makes the
    # wire parser, rather than caller JSON, authoritative for every outcome
    # and witness field.  Import lazily to keep the session core transport-free.
    import s22plus_fyg8_p348_shell_action as action  # noqa: PLC0415

    expected = action._session_receipt(  # noqa: SLF001
        live,
        variant,
        command,
        binding,
        intent,
        parsed,
        raw_tx,
        raw_rx,
        type("Capture", (), {"receipt_path": Path("capture.json"), "stdout": {}, "stderr": {}})(),
    )
    fields = (
        "action", "binding_sha256", "command", "session_complete", "command_outcome",
        "continuation_allowed", "commands", "boot_id_sha256", "challenge_nonce_sha256",
        "cancel_sent", "cancel_ack", "session_result", "acceptance_role", "ordinal", "intent_sha256",
    )
    for field in fields:
        if expected.get(field) != value.get(field):
            raise LeaseError(f"P348 retained frame semantic field differs: {field}")
    if expected["selected_output"] != value.get("selected_output"):
        raise LeaseError("P348 retained selected output differs")


def _validate_action_receipt(
    live: Any, prepared: Any, lease: ShellLease, intent: Mapping[str, Any], result: Mapping[str, Any]
) -> dict[str, Any]:
    if result.get("schema") != ACTION_RESULT_SCHEMA:
        raise LeaseError("P348 action receipt schema differs")
    required = {
        "action", "binding_sha256", "command", "command_outcome", "continuation_allowed", "intent_sha256",
        "ordinal", "session_complete", "commands", "selected_output", "selected_output_path",
        "raw_tx", "raw_rx", "raw_capture", "session_result",
    }
    # Diagnostic fields (cancel metadata and raw-capture paths) may be added,
    # but the protocol, command and retained-wire fields are mandatory.
    if not required <= set(result):
        raise LeaseError("P348 action receipt fields are incomplete")
    if (
        result.get("action") != ACTION_NAME
        or result.get("binding_sha256") != lease.lease["binding_sha256"]
        or result.get("intent_sha256") != digest(intent)
        or result.get("ordinal") != intent["ordinal"]
        or type(result.get("session_complete")) is not bool
        or type(result.get("continuation_allowed")) is not bool
        or type(result.get("command_outcome")) is not str
    ):
        raise LeaseError("P348 action receipt intent binding differs")
    command_identity = _command_identity(result.get("command"), "P348 receipt command")
    if command_identity != intent["command"]:
        raise LeaseError("P348 action receipt command identity differs")
    command_path = intent["command_path"]
    command_file = prepared.run_dir / command_path
    command_bytes, _ = _read_bytes(command_file, MAX_COMMAND_BYTES)
    if identity(command_bytes) != command_identity:
        raise LeaseError("P348 retained command bytes differ")
    selected_path = prepared.run_dir / _validate_path(result["selected_output_path"], "P348 selected output path")
    selected_bytes, _ = _read_bytes(selected_path, MAX_OUTPUT_BYTES)
    if result["selected_output"] != identity(selected_bytes):
        raise LeaseError("P348 selected output identity differs")
    if result["session_complete"] is not True:
        raise LeaseError("P348 action protocol is incomplete")
    if result["continuation_allowed"] is not True:
        raise LeaseError("P348 action does not permit continuation")
    _validate_retained_frames(
        live,
        prepared,
        result,
        prepared.run_dir / EVIDENCE_DIRECTORY / f"action-{intent['ordinal']:02d}",
        command_bytes,
        lease.binding,
        intent,
    )
    return dict(result)


def validate_previous_actions(
    live: Any,
    prepared: Any,
    lease: ShellLease,
    initial_nonces: set[str],
) -> set[str]:
    """Validate every prior completed action before a new OPEN is possible.

    This is the shared retained-evidence consumer used by the live dispatcher.
    It reparses each framed receipt, rechecks the command copy, raw-capture
    handle, selected output, outcome and exact intent binding, and returns the
    nonce set that the next exchange must reject.  A pending, failed, malformed
    or repeated action is terminal evidence; callers must not select an
    endpoint or publish another intent after this function fails.
    """

    if type(initial_nonces) is not set:
        raise LeaseError("P348 initial nonce set is not mutable")
    seen = set(initial_nonces)
    if any(type(item) is not str or HEX64.fullmatch(item) is None or item == ZERO for item in seen):
        raise RollbackRequired("P348 initial nonce history is malformed")
    for ordinal, (intent, journal_result) in enumerate(lease.actions, 1):
        if journal_result is None or journal_result["status"] != "completed":
            raise RollbackRequired("P348 prior action is unresolved")
        receipt_path = prepared.run_dir / EVIDENCE_DIRECTORY / f"action-{ordinal:02d}" / "result.json"
        raw, _ = _read_bytes(receipt_path, MAX_RECEIPT_BYTES)
        if (
            len(raw) != journal_result["receipt_bytes"]
            or hashlib.sha256(raw).hexdigest() != journal_result["receipt_sha256"]
        ):
            raise RollbackRequired("P348 prior action receipt digest differs")
        value = parse_canonical(raw, "P348 prior action receipt")
        if (
            journal_result["command"] != value.get("command")
            or journal_result["command_outcome"] != value.get("command_outcome")
            or journal_result["session_complete"] != value.get("session_complete")
            or journal_result["continuation_allowed"] != value.get("continuation_allowed")
        ):
            raise RollbackRequired("P348 prior action journal/result differs")
        checked = _validate_action_receipt(live, prepared, lease, intent, value)
        nonce = checked.get("challenge_nonce_sha256")
        if type(nonce) is not str or HEX64.fullmatch(nonce) is None or nonce == ZERO or nonce in seen:
            raise RollbackRequired("P348 prior action challenge nonce was replayed")
        seen.add(nonce)
    return seen


def action_summary(live: Any, prepared: Any) -> dict[str, Any]:
    """Reopen close evidence; never blocks the already-bound rollback owner."""

    rows: list[dict[str, Any]] = []
    try:
        # Close validation is a durable-evidence read.  A host reboot or a
        # later elapsed-clock value must not turn an already retained action
        # into a different summary or block the prebound rollback owner.
        lease = ShellLease.open(prepared.run_dir / DIRECTORY, validate_clock=False)
        expected = binding_for(live, prepared, live._reopen_candidate_observation(prepared))
        if canonical_bytes(expected) != canonical_bytes(lease.binding):
            raise LeaseError("P348 close lease binding differs")
        durable_proof = _proof_value(live._reopen_candidate_observation(prepared))
        initial_nonces = {
            row.get("nonce_sha256")
            for row in durable_proof.get("sessions", [])
            if isinstance(row, Mapping) and isinstance(row.get("nonce_sha256"), str)
        }
        later_nonces: set[str] = set()
        for ordinal, (intent, journal_result) in enumerate(lease.actions, 1):
            row = {
                "ordinal": ordinal,
                "action": intent["action"],
                "command": dict(intent["command"]),
                "status": "pending" if journal_result is None else journal_result["status"],
                "session_complete": False,
                "command_outcome": None,
                "continuation_allowed": False,
                "receipt_sha256": None,
            }
            if journal_result is not None:
                name = "result.json" if journal_result["status"] in ("completed", "failed") else "failure.json"
                receipt_path = prepared.run_dir / EVIDENCE_DIRECTORY / f"action-{ordinal:02d}" / name
                raw, _ = _read_bytes(receipt_path, MAX_RECEIPT_BYTES)
                if len(raw) != journal_result["receipt_bytes"] or hashlib.sha256(raw).hexdigest() != journal_result["receipt_sha256"]:
                    raise LeaseError("P348 action receipt digest differs")
                value = parse_canonical(raw, "P348 close action receipt")
                if (
                    journal_result["command"] != value.get("command")
                    or journal_result["command_outcome"] != value.get("command_outcome")
                    or journal_result["session_complete"] != value.get("session_complete")
                    or journal_result["continuation_allowed"] != value.get("continuation_allowed")
                ):
                    raise LeaseError("P348 journal/result outcome binding differs")
                if journal_result["status"] == "completed":
                    checked = _validate_action_receipt(live, prepared, lease, intent, value)
                    nonce = checked.get("challenge_nonce_sha256")
                    if type(nonce) is not str or HEX64.fullmatch(nonce) is None or nonce == ZERO or nonce in initial_nonces or nonce in later_nonces:
                        raise LeaseError("P348 retained challenge nonce was replayed")
                    later_nonces.add(nonce)
                    row.update(
                        session_complete=checked["session_complete"],
                        command_outcome=checked["command_outcome"],
                        continuation_allowed=checked["continuation_allowed"],
                        acceptance_role=checked.get("acceptance_role"),
                        receipt_sha256=journal_result["receipt_sha256"],
                    )
                else:
                    row.update(
                        session_complete=value.get("session_complete") is True,
                        command_outcome=value.get("command_outcome"),
                        continuation_allowed=False,
                        acceptance_role=value.get("acceptance_role"),
                        receipt_sha256=journal_result["receipt_sha256"],
                    )
            rows.append(row)
        completed = sum(row["status"] == "completed" and row["continuation_allowed"] is True for row in rows)
        integrity_proved = bool(rows) and completed == len(rows)
        acceptance = _acceptance_summary(live, prepared, rows)
        return {
            "schema": SUMMARY_SCHEMA,
            "proved": integrity_proved and acceptance["proved"],
            "integrity_proved": integrity_proved,
            "acceptance": acceptance,
            "actions": rows,
            "completed_actions": completed,
            "protocol_completed_actions": sum(row["session_complete"] is True for row in rows),
            "reason": None if integrity_proved and acceptance["proved"] else "retained-lease-or-action-evidence-unproved",
            "lease": lease.snapshot(now_ns=lease.lease["opened_elapsed_ns"]),
        }
    except Exception:
        return {
            "schema": SUMMARY_SCHEMA,
            "proved": False,
            "integrity_proved": False,
            "acceptance": {"proved": False, "roles": [], "missing": ["all"]},
            "actions": rows,
            "completed_actions": 0,
            "protocol_completed_actions": 0,
            "reason": "retained-lease-or-action-evidence-unproved",
        }


def _acceptance_summary(live: Any, prepared: Any, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Require the finite checked later-use sequence for capability PASS."""

    required = (
        "checked-snapshot",
        "known-nonzero",
        "timeout",
        "active-cancel",
        "post-cancel-success",
    )
    roles: list[str] = []
    for row in rows:
        role = row.get("acceptance_role")
        if isinstance(role, str):
            roles.append(role)
    cursor = 0
    out_of_order = False
    for role in roles:
        if cursor < len(required) and role == required[cursor]:
            cursor += 1
        elif role in required[:cursor + 1]:
            # A repeated checked witness is allowed within the remaining
            # action budget and cannot erase an already established role.
            continue
        elif role in required:
            out_of_order = True
    missing = list(required[cursor:])
    ordered = cursor == len(required) and not out_of_order
    if out_of_order:
        missing.append("ordered-acceptance-sequence")
    return {
        "proved": not missing and ordered,
        "roles": roles,
        "missing": missing,
        "required": list(required),
    }


__all__ = [
    "ACTION_NAME", "ACTION_NAMES", "ACTION_RESULT_SCHEMA", "CLOCK_KIND", "DIRECTORY", "LEASE_DIRECTORY", "LEASE_SCHEMA",
    "EVIDENCE_DIRECTORY", "LeaseError", "MAX_ACTIONS", "MAX_COMMAND_BYTES", "MAX_LEASE_SECONDS",
    "MAX_OUTPUT_BYTES", "OWNER", "PROOF_KEY", "RollbackRequired", "SCHEMA", "SESSION_WINDOW_NS",
    "SESSION_WINDOW_SECONDS", "SUMMARY_SCHEMA", "SUSPEND_TOLERANCE_NS", "ShellLease", "ResidentLease", "TARGET",
    "action_summary", "after_guard_release", "before_guard_release", "binding_for", "canonical_bytes",
    "clock_now_ns", "digest", "host_epoch", "identity", "mark_rollback_required", "monotonic_now_ns", "open_lease",
    "parse_canonical", "publish_lease", "read_json", "suspend_delta_ns", "validate_binding", "validate_previous_actions", "write_bytes_once",
]
