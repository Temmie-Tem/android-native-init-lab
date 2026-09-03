#!/usr/bin/env python3
"""Host-only durable core for the S22+ P3.35 resident-session lease.

This module only validates and journals the attended, current-boot lease.  It
does not import or invoke ADB, USB, Odin, a shell, or a device runner.
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
SCHEMA = "s22plus_fyg8_p335_resident_lease_v1"
VERSION = 1
MAX_LEASE_SECONDS = 3_600
MAX_ACTIONS = 16
MAX_RECEIPT_BYTES = 256 * 1024
ACTION_NAMES = ("identity", "kernel", "session-nonce")
TARGET = {"model": "SM-S906N", "device": "g0q", "firmware_incremental": "S906NKSS7FYG8"}
ZERO = "0" * 64
_HEX = re.compile(r"^[0-9a-f]{64}$")
_RUN = re.compile(r"^[0-9a-f]{32}$")
_NS = 1_000_000_000
_MAX_FILE_BYTES = 2 * 1024 * 1024
class LeaseError(ValueError):
    """The lease namespace or a caller-provided value is invalid."""


class RollbackRequired(LeaseError):
    """The only permitted continuation is the prebound rollback owner."""
def canonical_bytes(value: Any) -> bytes:
    """Return the one JSON representation accepted by this journal."""
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
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise LeaseError("value is not canonical JSON") from exc
def parse_canonical(payload: bytes | bytearray, label: str = "JSON") -> dict[str, Any]:
    """Parse bytes strictly, rejecting duplicate keys and non-canonical text."""
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
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeDecodeError, json.JSONDecodeError, LeaseError) as exc:
        raise LeaseError(f"{label} is not valid canonical JSON") from exc
    if type(value) is not dict or canonical_bytes(value) != raw:
        raise LeaseError(f"{label} is not canonical")
    return value
def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()
def _keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        raise LeaseError(f"{label} has an unexpected schema")
    return value
def _hex(value: Any, label: str, pattern: re.Pattern[str] = _HEX) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None or value == ZERO:
        raise LeaseError(f"{label} must be a nonzero lowercase hexadecimal value")
    return value
def _integer(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise LeaseError(f"{label} must be an integer >= {minimum}")
    return value
def catalog_for(run_id: str) -> dict[str, dict[str, list[str]]]:
    """The complete first catalog; callers can select a name, never a command."""
    if _RUN.fullmatch(run_id if type(run_id) is str else "") is None:
        raise LeaseError("run_id is not 16-byte lowercase hexadecimal")
    return {
        "identity": {"argv": ["/bin/busybox", "id"]},
        "kernel": {"argv": ["/bin/busybox", "uname", "-a"]},
        "session-nonce": {
            "argv": ["/bin/busybox", "echo", "P328-NONCE", run_id]
        },
    }
def validate_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the exact immutable target, topology, and recovery binding."""
    binding = _keys(value, {"target", "topology", "candidate", "key", "catalog", "recovery", "per_boot_id"}, "binding")
    target = _keys(binding["target"], set(TARGET), "target")
    if target != TARGET:
        raise LeaseError("target binding differs")
    topology = _keys(binding["topology"], {"sha256"}, "topology")
    _hex(topology["sha256"], "topology.sha256")
    candidate = _keys(binding["candidate"], {"run_id", "boot_sha256", "ap_sha256"}, "candidate")
    run_id = candidate["run_id"]
    if type(run_id) is not str or _RUN.fullmatch(run_id) is None:
        raise LeaseError("candidate.run_id is invalid")
    _hex(candidate["boot_sha256"], "candidate.boot_sha256")
    _hex(candidate["ap_sha256"], "candidate.ap_sha256")
    key = _keys(binding["key"], {"size", "sha256"}, "key")
    if type(key["size"]) is not int or key["size"] != 32:
        raise LeaseError("private key size differs")
    _hex(key["sha256"], "key.sha256")
    if binding["catalog"] != catalog_for(run_id):
        raise LeaseError("command catalog differs")
    recovery = _keys(binding["recovery"], {"kind", "owner", "rollback_ap_sha256"}, "recovery")
    if recovery["kind"] != "magisk_boot_only" or recovery["owner"] != "s22plus-fyg8-p335":
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
def _stat(path: Path, directory: bool = False) -> os.stat_result:
    try:
        value = path.lstat()
    except OSError as exc:
        raise LeaseError(f"missing {path.name}") from exc
    mode = value.st_mode
    if directory:
        good = stat.S_ISDIR(mode) and stat.S_IMODE(mode) == 0o700
    else:
        good = stat.S_ISREG(mode) and value.st_nlink == 1 and stat.S_IMODE(mode) == 0o400
    if not good:
        raise LeaseError(f"unsafe namespace entry: {path.name}")
    return value
def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
def _write_once(path: Path, payload: bytes) -> None:
    if len(payload) > _MAX_FILE_BYTES:
        raise LeaseError("journal record is too large")
    _stat(path.parent, directory=True)
    temp = path.with_name("." + path.name + ".tmp")
    if temp.exists() or path.exists():
        raise LeaseError(f"refusing to replace {path.name}")
    fd = -1
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
        written = 0
        while written < len(payload):
            written += os.write(fd, payload[written:])
        os.fsync(fd)
        os.close(fd)
        fd = -1
        os.link(temp, path, follow_symlinks=False)
        _fsync_dir(path.parent)
        os.unlink(temp)
        _fsync_dir(path.parent)
    except OSError as exc:
        if fd >= 0:
            os.close(fd)
        raise RollbackRequired(f"uncertain publication of {path.name}") from exc
def _read(path: Path) -> dict[str, Any]:
    before = _stat(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb", closefd=True) as stream:
            raw = stream.read(_MAX_FILE_BYTES + 1)
            inside = os.fstat(stream.fileno())
    except OSError as exc:
        raise RollbackRequired(f"uncertain read of {path.name}") from exc
    after = _stat(path)
    identity = lambda item: (item.st_dev, item.st_ino, item.st_mode, item.st_nlink, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
    if len(raw) > _MAX_FILE_BYTES or identity(before) != identity(inside) or identity(before) != identity(after):
        raise RollbackRequired(f"changed journal record: {path.name}")
    return parse_canonical(raw, path.name)
def _root(path: str | os.PathLike[str]) -> Path:
    value = Path(path)
    _stat(value, directory=True)
    return value
def _mkdir(path: Path) -> None:
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        _stat(path, directory=True)
    _fsync_dir(path.parent)
class ResidentLease:
    """A strict, no-clobber lease and one-shot action journal."""

    def __init__(self, run_dir: Path, lease: dict[str, Any], guard: dict[str, Any], actions: list[tuple[dict[str, Any], dict[str, Any] | None]], terminal: dict[str, Any] | None) -> None:
        self.run_dir, self.lease, self.guard = run_dir, lease, guard
        self.actions, self.terminal = actions, terminal
        self.binding = validate_binding(lease["binding"])

    @classmethod
    def publish(
        cls, run_dir: str | os.PathLike[str], binding: Mapping[str, Any], observation: Mapping[str, Any],
        *, now_ns: int | None = None, duration_seconds: int = MAX_LEASE_SECONDS, lease_id: str | None = None,
    ) -> "ResidentLease":
        root = _root(run_dir)
        if any(root.iterdir()):
            raise LeaseError("resident namespace is not fresh")
        binding = validate_binding(dict(binding))
        observation = _validate_observation(dict(observation))
        now = time.monotonic_ns() if now_ns is None else _integer(now_ns, "opened_monotonic_ns")
        if type(duration_seconds) is not int or not 0 < duration_seconds <= MAX_LEASE_SECONDS:
            raise LeaseError("lease duration exceeds one-hour bound")
        lease_id = secrets.token_hex(16) if lease_id is None else lease_id
        if _RUN.fullmatch(lease_id) is None:
            raise LeaseError("lease_id is invalid")
        _mkdir(root / "events")
        _mkdir(root / "actions")
        lease = {
            "binding": binding, "binding_sha256": digest(binding), "candidate_boot_ready": True,
            "expires_monotonic_ns": now + duration_seconds * _NS, "kind": "resident-lease",
            "lease_id": lease_id, "max_actions": MAX_ACTIONS, "max_sessions_per_action": 1,
            "no_replay": True, "observed_monotonic_ns": now, "observation": observation,
            "schema": SCHEMA, "state": "RESIDENT_SESSION_ACTIVE", "ordinary_state": "OBSERVED", "version": VERSION,
        }
        lease_raw = canonical_bytes(lease)
        _write_once(root / "lease.json", lease_raw)
        guard = {
            "binding_sha256": lease["binding_sha256"], "kind": "resident-lease-guard", "lease_id": lease_id,
            "lease_sha256": hashlib.sha256(lease_raw).hexdigest(), "no_replay": True, "schema": SCHEMA,
            "state": "ACTIVE", "version": VERSION,
        }
        _write_once(root / "lease.guard.json", canonical_bytes(guard))
        return cls.open(root)

    create = publish

    @classmethod
    def open(cls, run_dir: str | os.PathLike[str]) -> "ResidentLease":
        root = _root(run_dir)
        entries = {entry.name for entry in os.scandir(root)}
        expected = {"lease.json", "lease.guard.json", "events", "actions"}
        if entries - expected:
            raise LeaseError("foreign resident namespace entry")
        present = entries & {"lease.json", "lease.guard.json"}
        if len(present) == 1:
            raise RollbackRequired("partial lease/guard publication")
        if present != {"lease.json", "lease.guard.json"}:
            raise LeaseError("resident lease is absent")
        _stat(root / "events", directory=True)
        _stat(root / "actions", directory=True)
        lease = _keys(_read(root / "lease.json"), {
            "binding", "binding_sha256", "candidate_boot_ready", "expires_monotonic_ns", "kind", "lease_id",
            "max_actions", "max_sessions_per_action", "no_replay", "observed_monotonic_ns", "observation",
            "schema", "state", "ordinary_state", "version",
        }, "lease")
        if lease["schema"] != SCHEMA or type(lease["version"]) is not int or lease["version"] != VERSION or lease["kind"] != "resident-lease":
            raise LeaseError("lease schema differs")
        if lease["state"] != "RESIDENT_SESSION_ACTIVE" or lease["ordinary_state"] != "OBSERVED" or lease["candidate_boot_ready"] is not True:
            raise RollbackRequired("lease is not the observed current-boot state")
        if type(lease["max_actions"]) is not int or type(lease["max_sessions_per_action"]) is not int or lease["max_actions"] != MAX_ACTIONS or lease["max_sessions_per_action"] != 1 or lease["no_replay"] is not True:
            raise LeaseError("lease bounds differ")
        if _RUN.fullmatch(lease["lease_id"] if type(lease["lease_id"]) is str else "") is None:
            raise LeaseError("lease_id differs")
        _integer(lease["observed_monotonic_ns"], "observed_monotonic_ns")
        expires = _integer(lease["expires_monotonic_ns"], "expires_monotonic_ns")
        if expires <= lease["observed_monotonic_ns"] or expires - lease["observed_monotonic_ns"] > MAX_LEASE_SECONDS * _NS:
            raise LeaseError("lease deadline is invalid")
        binding = validate_binding(lease["binding"])
        if lease["binding_sha256"] != digest(binding):
            raise LeaseError("binding digest differs")
        _validate_observation(lease["observation"])
        guard = _keys(_read(root / "lease.guard.json"), {
            "binding_sha256", "kind", "lease_id", "lease_sha256", "no_replay", "schema", "state", "version",
        }, "guard")
        if guard["schema"] != SCHEMA or type(guard["version"]) is not int or guard["version"] != VERSION or guard["kind"] != "resident-lease-guard" or guard["state"] != "ACTIVE" or guard["no_replay"] is not True:
            raise RollbackRequired("resident guard differs")
        if guard["lease_id"] != lease["lease_id"] or guard["binding_sha256"] != lease["binding_sha256"]:
            raise RollbackRequired("resident guard binding differs")
        if guard["lease_sha256"] != digest(lease):
            raise RollbackRequired("resident guard lease digest differs")
        actions = cls._load_actions(root / "actions", lease["lease_id"], lease["binding_sha256"])
        terminal = cls._load_terminal(root / "events", lease["lease_id"], lease["binding_sha256"])
        return cls(root, lease, guard, actions, terminal)

    @staticmethod
    def _load_actions(directory: Path, lease_id: str, binding_sha256: str) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
        files = {entry.name for entry in os.scandir(directory)}
        pattern = re.compile(r"^([0-9]{2})-(intent|result)\.json$")
        parsed: dict[int, dict[str, Path]] = {}
        for name in files:
            match = pattern.fullmatch(name)
            if match is None:
                raise RollbackRequired("foreign or partial action journal entry")
            ordinal, kind = int(match.group(1)), match.group(2)
            if not 1 <= ordinal <= MAX_ACTIONS or kind in parsed.setdefault(ordinal, {}):
                raise RollbackRequired("action ordinal is invalid or duplicated")
            parsed[ordinal][kind] = directory / name
        actions: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
        for ordinal in range(1, (max(parsed) if parsed else 0) + 1):
            row = parsed.get(ordinal)
            if row is None or "intent" not in row:
                raise RollbackRequired("action journal has a gap")
            intent = _keys(_read(row["intent"]), {
                "action", "binding_sha256", "issued_monotonic_ns", "kind", "lease_id", "no_replay", "ordinal", "schema", "version",
            }, "action intent")
            if intent["schema"] != SCHEMA or type(intent["version"]) is not int or intent["version"] != VERSION or intent["kind"] != "action-intent" or intent["lease_id"] != lease_id or intent["binding_sha256"] != binding_sha256 or type(intent["ordinal"]) is not int or intent["ordinal"] != ordinal or intent["action"] not in ACTION_NAMES or intent["no_replay"] is not True:
                raise RollbackRequired("action intent binding differs")
            _integer(intent["issued_monotonic_ns"], "action intent time")
            result = None
            if "result" in row:
                result = _keys(_read(row["result"]), {
                    "action", "binding_sha256", "intent_sha256", "issued_monotonic_ns", "kind", "lease_id", "no_replay", "ordinal", "receipt_bytes", "receipt_sha256", "schema", "status", "version",
                }, "action result")
                if result["schema"] != SCHEMA or type(result["version"]) is not int or result["version"] != VERSION or result["kind"] != "action-result" or result["lease_id"] != lease_id or result["binding_sha256"] != binding_sha256 or type(result["ordinal"]) is not int or result["ordinal"] != ordinal or result["action"] != intent["action"] or result["intent_sha256"] != digest(intent) or result["no_replay"] is not True or result["status"] not in ("ok", "failed", "uncertain"):
                    raise RollbackRequired("action result binding differs")
                _integer(result["issued_monotonic_ns"], "action result time")
                if _integer(result["receipt_bytes"], "receipt_bytes") > MAX_RECEIPT_BYTES:
                    raise RollbackRequired("action receipt is too large")
                _hex(result["receipt_sha256"], "receipt_sha256")
            actions.append((intent, result))
        return actions

    @staticmethod
    def _load_terminal(directory: Path, lease_id: str, binding_sha256: str) -> dict[str, Any] | None:
        files = {entry.name for entry in os.scandir(directory)}
        if not files:
            return None
        if files != {"0000-rollback-required.json"}:
            raise RollbackRequired("foreign or duplicate terminal event")
        event = _keys(_read(directory / "0000-rollback-required.json"), {
            "binding_sha256", "issued_monotonic_ns", "kind", "lease_id", "no_replay", "previous_sha256", "reason", "schema", "sequence", "trigger", "version",
        }, "terminal event")
        if event["schema"] != SCHEMA or type(event["version"]) is not int or event["version"] != VERSION or event["kind"] != "lease-event" or event["lease_id"] != lease_id or event["binding_sha256"] != binding_sha256 or type(event["sequence"]) is not int or event["sequence"] != 0 or event["trigger"] not in ("STOP", "EXPIRY", "DRIFT", "ACTION_RESULT", "ACTION_BUDGET") or event["previous_sha256"] != ZERO or event["no_replay"] is not True:
            raise RollbackRequired("terminal event binding differs")
        _integer(event["issued_monotonic_ns"], "terminal event time")
        reason = event["reason"]
        if type(reason) is not str or not 1 <= len(reason) <= 160 or any(ord(char) < 0x20 or ord(char) > 0x7E for char in reason):
            raise RollbackRequired("terminal event reason is invalid")
        return event

    def _refresh(self) -> None:
        fresh = type(self).open(self.run_dir)
        self.__dict__.update(fresh.__dict__)

    def _terminal(self, trigger: str, reason: str, now_ns: int | None = None) -> None:
        if self.terminal is not None:
            return
        if trigger not in ("STOP", "EXPIRY", "DRIFT", "ACTION_RESULT", "ACTION_BUDGET"):
            raise LeaseError("unknown rollback trigger")
        if type(reason) is not str or not 1 <= len(reason) <= 160 or any(ord(char) < 0x20 or ord(char) > 0x7E for char in reason):
            raise LeaseError("rollback reason is invalid")
        issued = time.monotonic_ns() if now_ns is None else _integer(now_ns, "event time")
        event = {
            "binding_sha256": self.lease["binding_sha256"], "issued_monotonic_ns": issued, "kind": "lease-event",
            "lease_id": self.lease["lease_id"], "no_replay": True, "previous_sha256": ZERO, "reason": reason,
            "schema": SCHEMA, "sequence": 0, "trigger": trigger, "version": VERSION,
        }
        _write_once(self.run_dir / "events" / "0000-rollback-required.json", canonical_bytes(event))
        self.terminal = event

    def _require_binding(self, binding: Mapping[str, Any]) -> None:
        try:
            current = validate_binding(dict(binding))
        except LeaseError as exc:
            self._terminal("DRIFT", "current binding is invalid")
            raise RollbackRequired("current binding is invalid") from exc
        if canonical_bytes(current) != canonical_bytes(self.binding):
            self._terminal("DRIFT", "exact target or session binding drifted")
            raise RollbackRequired("exact target or session binding drifted")

    def snapshot(self, *, now_ns: int | None = None) -> dict[str, Any]:
        now = time.monotonic_ns() if now_ns is None else _integer(now_ns, "snapshot time")
        pending = next((intent for intent, result in self.actions if result is None), None)
        rollback = self.terminal is not None or pending is not None or now >= self.lease["expires_monotonic_ns"] or any(result and result["status"] != "ok" for _, result in self.actions)
        reason = self.terminal["reason"] if self.terminal else ("active intent unresolved" if pending else ("lease expired" if now >= self.lease["expires_monotonic_ns"] else ""))
        return {
            "schema": SCHEMA, "lease_id": self.lease["lease_id"], "state": "ROLLBACK_REQUIRED" if rollback else "ACTIVE",
            "rollback_required": rollback, "reason": reason, "binding_sha256": self.lease["binding_sha256"],
            "per_boot_id": self.binding["per_boot_id"], "opened_monotonic_ns": self.lease["observed_monotonic_ns"],
            "expires_monotonic_ns": self.lease["expires_monotonic_ns"], "actions_started": len(self.actions),
            "actions_completed": sum(result is not None for _, result in self.actions), "actions_remaining": MAX_ACTIONS - len(self.actions),
            "active_intent": pending["action"] if pending else None, "terminal_event": self.terminal["trigger"] if self.terminal else None,
        }

    def begin_action(self, action: str, current_binding: Mapping[str, Any], *, now_ns: int | None = None) -> dict[str, Any]:
        self._refresh()
        self._require_binding(current_binding)
        now = time.monotonic_ns() if now_ns is None else _integer(now_ns, "action time")
        if type(action) is not str or action not in ACTION_NAMES:
            raise LeaseError("caller may select only a named action")
        if self.terminal is not None:
            raise RollbackRequired("lease is rollback-required")
        if any(result is None for _, result in self.actions):
            raise RollbackRequired("active action intent blocks new commands")
        if now >= self.lease["expires_monotonic_ns"]:
            self._terminal("EXPIRY", "resident lease deadline expired", now)
            raise RollbackRequired("resident lease expired")
        if len(self.actions) >= MAX_ACTIONS:
            self._terminal("ACTION_BUDGET", "resident action budget exhausted", now)
            raise RollbackRequired("resident action budget exhausted")
        ordinal = len(self.actions) + 1
        intent = {
            "action": action, "binding_sha256": self.lease["binding_sha256"], "issued_monotonic_ns": now,
            "kind": "action-intent", "lease_id": self.lease["lease_id"], "no_replay": True,
            "ordinal": ordinal, "schema": SCHEMA, "version": VERSION,
        }
        _write_once(self.run_dir / "actions" / f"{ordinal:02d}-intent.json", canonical_bytes(intent))
        self.actions.append((intent, None))
        return intent

    def record_action_result(
        self, ordinal_or_intent: int | Mapping[str, Any], result: Mapping[str, Any], current_binding: Mapping[str, Any], *, now_ns: int | None = None,
    ) -> dict[str, Any]:
        self._refresh()
        self._require_binding(current_binding)
        if self.terminal is not None:
            raise RollbackRequired("lease is rollback-required")
        pending = [(index, pair) for index, pair in enumerate(self.actions) if pair[1] is None]
        if len(pending) != 1 or (type(ordinal_or_intent) is int and ordinal_or_intent != pending[0][0] + 1) or (type(ordinal_or_intent) is not int and not isinstance(ordinal_or_intent, Mapping)):
            raise RollbackRequired("there is no matching active action intent")
        ordinal, (intent, _) = pending[0][0] + 1, pending[0][1]
        if isinstance(ordinal_or_intent, Mapping) and canonical_bytes(dict(ordinal_or_intent)) != canonical_bytes(intent):
            raise RollbackRequired("action intent differs")
        values = _keys(dict(result), {"status", "receipt_bytes", "receipt_sha256"}, "result")
        if values["status"] not in ("ok", "failed", "uncertain"):
            raise LeaseError("action result status differs")
        receipt_bytes = _integer(values["receipt_bytes"], "receipt_bytes")
        if receipt_bytes > MAX_RECEIPT_BYTES:
            raise LeaseError("action receipt is too large")
        receipt_sha256 = _hex(values["receipt_sha256"], "receipt_sha256")
        now = time.monotonic_ns() if now_ns is None else _integer(now_ns, "result time")
        if now >= self.lease["expires_monotonic_ns"]:
            self._terminal("EXPIRY", "resident lease deadline expired", now)
            raise RollbackRequired("resident lease expired")
        row = {
            "action": intent["action"], "binding_sha256": self.lease["binding_sha256"], "intent_sha256": digest(intent),
            "issued_monotonic_ns": now, "kind": "action-result", "lease_id": self.lease["lease_id"], "no_replay": True,
            "ordinal": ordinal, "receipt_bytes": receipt_bytes, "receipt_sha256": receipt_sha256, "schema": SCHEMA,
            "status": values["status"], "version": VERSION,
        }
        _write_once(self.run_dir / "actions" / f"{ordinal:02d}-result.json", canonical_bytes(row))
        self.actions[pending[0][0]] = (intent, row)
        if row["status"] != "ok":
            self._terminal("ACTION_RESULT", "action result is not successful", now)
        elif ordinal == MAX_ACTIONS:
            self._terminal("ACTION_BUDGET", "resident action budget exhausted", now)
        return row

    def stop(self, reason: str = "operator stop") -> None:
        self._refresh()
        self._terminal("STOP", reason)

    def expire(self, *, now_ns: int | None = None) -> None:
        self._refresh()
        now = time.monotonic_ns() if now_ns is None else _integer(now_ns, "expiry time")
        self._terminal("EXPIRY", "resident lease deadline expired", now)

    def mark_drift(self, reason: str = "exact binding drifted") -> None:
        self._refresh()
        self._terminal("DRIFT", reason)


publish_lease = ResidentLease.publish
open_lease = ResidentLease.open
