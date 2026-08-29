#!/usr/bin/env python3
"""Dormant H0 journal fixture for the reviewed S22+ normal-reboot descriptor.

This module binds one reviewed descriptor and exercises the real coordinator
state model through a durable append-only journal.  It has no activation-file
loader, target enumerator, device transport, subprocess call, or live executor.
The CLI can only run a temporary host-only self-test.
"""

from __future__ import annotations

import argparse
from contextlib import AbstractContextManager
import ctypes
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
COORDINATOR_PATH = (
    ROOT
    / "workspace/public/src/device-action/coordinators/"
    "s22plus_fyg8_pref1_autonomous_coordinator_h0.py"
)
EXECUTOR_PATH = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_d1_fresh_baseline_v3.py"
)
BINDING_PATH = (
    ROOT
    / "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p319_d1_fresh_baseline_v3.json"
)

SCHEMA = "s22plus_fyg8_pref1_normal_reboot_journal_h0_v1"
DESCRIPTOR_SCHEMA = "s22plus_fyg8_pref1_fixed_descriptor_v1"
RECORD_SCHEMA = "s22plus_fyg8_pref1_journal_record_v1"
STATUS = "H0_FIXED_DESCRIPTOR_JOURNAL_IMPLEMENTED_NOT_ACTIVE"

COORDINATOR_ACTIVE = False
LIVE_AUTHORITY = False
ACTIVATION_MANIFEST_PRESENT = False
DEVICE_ACTION_INTEGRATION = False
LIVE_EXECUTOR_INTEGRATION = False
DURABLE_JOURNAL_FIXTURE = True

CLASS_ID = "normal_android_reboot_health"
TIER = "D1"
PROOF_MODE = "new_boot_health"
EXECUTOR_ORDINAL = "d1-fresh-baseline-3"
REVIEW_VERDICT = "PASS_GO_P319_D1_FRESH_BASELINE_CANONICAL_ARM_V3_H0_CAPABILITY_V1"

EXPECTED_FILES = {
    "coordinator": {
        "size": 23_764,
        "sha256": "c0d56417c070c5958a356110f4b1996f9c903af993d118e0f812cccdd8aea65e",
    },
    "executor": {
        "size": 73_125,
        "sha256": "cb13236e1fb10bf25ac47f7706df050abe15b2ab5a7e423bbdc7b5b31c2c491d",
    },
    "binding": {
        "size": 6_705,
        "sha256": "dcb869aeeebf877d669da0a1f45b8c1d56a65777c13c9d518c0ad2dace93fc10",
    },
}

MAX_JSON_BYTES = 128 * 1024
ZERO_HASH = "0" * 64
RECORD_NAME = re.compile(r"([0-9]{6})-([a-z-]+)\.json\Z")
KIND_TO_SLUG = {
    "CAMPAIGN_OPEN": "campaign-open",
    "EFFECT_INTENT": "effect-intent",
    "EFFECT_HEALTHY_RETURN": "effect-healthy-return",
    "EFFECT_UNCERTAIN_PARK": "effect-uncertain-park",
    "CAMPAIGN_CLOSE": "campaign-close",
}
SLUG_TO_KIND = {value: key for key, value in KIND_TO_SLUG.items()}
RECORD_KEYS = {
    "schema",
    "sequence",
    "kind",
    "recorded_at_epoch",
    "previous_record_sha256",
    "payload_sha256",
    "payload",
}

AT_EMPTY_PATH = 0x1000
_LIBC = ctypes.CDLL(None, use_errno=True)
_LINKAT = _LIBC.linkat
_LINKAT.argtypes = (
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_int,
)
_LINKAT.restype = ctypes.c_int


class JournalError(RuntimeError):
    """A descriptor, namespace, record, or transition failed closed."""


def canonical_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise JournalError("value is not canonical JSON") from exc
    return (text + "\n").encode("utf-8")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise JournalError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def strict_json(raw: bytes, label: str) -> Any:
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_JSON_BYTES:
        raise JournalError(f"{label} byte extent differs")
    try:
        value = json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_unique_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                JournalError(f"{label} has non-finite value {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JournalError(f"{label} is not strict JSON") from exc
    if canonical_bytes(value) != raw:
        raise JournalError(f"{label} is not canonical JSON")
    return value


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_regular(
    path: Path,
    label: str,
    *,
    maximum: int,
    mode: int | None = None,
) -> bytes:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise JournalError(f"{label} is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or not 0 < before.st_size <= maximum
            or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
        ):
            raise JournalError(f"{label} metadata differs")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 64 * 1024))
            if not chunk:
                raise JournalError(f"{label} read was short")
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_nlink,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_nlink,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise JournalError(f"{label} changed while open")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _bound_file(path: Path, key: str) -> bytes:
    expected = EXPECTED_FILES[key]
    payload = _read_regular(path, key, maximum=expected["size"])
    if len(payload) != expected["size"] or _sha256(payload) != expected["sha256"]:
        raise JournalError(f"{key} identity differs")
    return payload


def load_coordinator() -> types.ModuleType:
    source = _bound_file(COORDINATOR_PATH, "coordinator")
    module = types.ModuleType("s22plus_pref1_coordinator_bound_for_journal")
    module.__file__ = str(COORDINATOR_PATH)
    try:
        exec(compile(source, str(COORDINATOR_PATH), "exec"), module.__dict__)
    except Exception as exc:
        raise JournalError("bound coordinator does not load") from exc
    return module


def fixed_descriptor() -> dict[str, Any]:
    executor = _bound_file(EXECUTOR_PATH, "executor")
    binding_raw = _bound_file(BINDING_PATH, "binding")
    binding = strict_json(binding_raw, "V3 binding")
    if (
        binding.get("schema")
        != "s22plus_fyg8_p319_d1_fresh_baseline_execution_binding_v3"
        or binding.get("target")
        != {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
        or binding.get("run", {}).get("ordinal") != EXECUTOR_ORDINAL
        or binding.get("successor")
        != {
            "path": EXECUTOR_PATH.relative_to(ROOT).as_posix(),
            "size": len(executor),
            "sha256": _sha256(executor),
        }
        or binding.get("independent_review")
        != {"status": "pass-go", "verdict": REVIEW_VERDICT}
    ):
        raise JournalError("V3 reviewed descriptor semantics differ")
    safety = binding.get("safety")
    if type(safety) is not dict or safety != {
        "candidate_transfer": False,
        "download_transition": False,
        "f1_authorized": False,
        "odin": False,
        "other_targets_commanded": False,
        "partition_payload": False,
        "replay_authorized": False,
    }:
        raise JournalError("V3 descriptor safety boundary differs")
    authority = binding.get("authority_prefix")
    if type(authority) is not str or authority != (
        "DEVICE-ACTION-D1-P319-FRESH-BASELINE-V3-APPROVE:"
    ):
        raise JournalError("V3 authority form differs")
    authority += EXPECTED_FILES["binding"]["sha256"]
    value = {
        "schema": DESCRIPTOR_SCHEMA,
        "class_id": CLASS_ID,
        "tier": TIER,
        "proof_mode": PROOF_MODE,
        "target": {"model": "SM-S906N", "device": "g0q", "build": "S906NKSS7FYG8"},
        "executor": {
            "source": {
                "path": EXECUTOR_PATH.relative_to(ROOT).as_posix(),
                **EXPECTED_FILES["executor"],
            },
            "binding": {
                "path": BINDING_PATH.relative_to(ROOT).as_posix(),
                **EXPECTED_FILES["binding"],
            },
            "ordinal": EXECUTOR_ORDINAL,
            "review_verdict": REVIEW_VERDICT,
        },
        "authority_sha256": _sha256(authority.encode("ascii")),
        "invocation_shape": [
            "--live",
            "--approval",
            "<exact-authority-derived-only-after-campaign-activation>",
        ],
        "device_commands": [],
        "partition_transfers": [],
        "live_integration": False,
    }
    return value


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise JournalError(f"cannot fsync directory {path.name}") from exc


def _direct_directory(path: Path, label: str, *, mode: int = 0o700) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise JournalError(f"{label} is unavailable") from exc
    if (
        not stat.S_ISDIR(info.st_mode)
        or stat.S_ISLNK(info.st_mode)
        or stat.S_IMODE(info.st_mode) != mode
        or info.st_uid != os.getuid()
        or path.resolve(strict=True) != path.absolute()
    ):
        raise JournalError(f"{label} identity differs")


def _link_tmpfile(descriptor: int, parent: int, name: str) -> None:
    ctypes.set_errno(0)
    if _LINKAT(descriptor, b"", parent, os.fsencode(name), AT_EMPTY_PATH) != 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number), name)


def _atomic_publish(path: Path, payload: bytes) -> None:
    if type(payload) is not bytes or not 0 < len(payload) <= MAX_JSON_BYTES:
        raise JournalError("journal payload extent differs")
    parent = -1
    temporary = -1
    try:
        parent = os.open(
            path.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
        temporary = os.open(
            ".",
            os.O_WRONLY | os.O_TMPFILE | os.O_CLOEXEC,
            0o400,
            dir_fd=parent,
        )
        offset = 0
        while offset < len(payload):
            written = os.write(temporary, payload[offset:])
            if written <= 0:
                raise JournalError("journal write did not progress")
            offset += written
        os.fchmod(temporary, 0o400)
        os.fsync(temporary)
        metadata = os.fstat(temporary)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_size != len(payload)
        ):
            raise JournalError("journal temporary metadata differs")
        _link_tmpfile(temporary, parent, path.name)
        os.fsync(parent)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            raise JournalError("journal final already exists") from exc
        raise JournalError("journal atomic publication failed") from exc
    finally:
        if temporary >= 0:
            os.close(temporary)
        if parent >= 0:
            os.close(parent)
    if _read_regular(path, "published journal record", maximum=MAX_JSON_BYTES, mode=0o400) != payload:
        raise JournalError("published journal record differs")


class Journal(AbstractContextManager["Journal"]):
    """Single-writer append-only store used only by the H0 fixture."""

    def __init__(self, root: Path, coordinator: types.ModuleType | None = None):
        self.root = Path(root).absolute()
        self.records = self.root / "journal"
        self.lock = self.root / "coordinator.lock"
        self.coordinator = coordinator or load_coordinator()
        self.descriptor = fixed_descriptor()
        self.descriptor_digest = _sha256(canonical_bytes(self.descriptor))
        self._lock_fd = -1

    @classmethod
    def create(cls, root: Path) -> "Journal":
        path = Path(root).absolute()
        if path.exists() or path.is_symlink():
            raise JournalError("campaign journal root already exists")
        try:
            os.mkdir(path, 0o700)
            _fsync_directory(path.parent)
            os.mkdir(path / "journal", 0o700)
            _fsync_directory(path)
        except OSError as exc:
            raise JournalError("cannot initialize campaign journal") from exc
        return cls(path)

    def _validate_namespace(self, *, lock_may_be_absent: bool) -> None:
        _direct_directory(self.root, "campaign journal root")
        _direct_directory(self.records, "campaign record directory")
        allowed = {"journal", "coordinator.lock"}
        names = {entry.name for entry in self.root.iterdir()}
        if not names <= allowed or "journal" not in names:
            raise JournalError("campaign journal namespace differs")
        if "coordinator.lock" not in names:
            if lock_may_be_absent:
                return
            raise JournalError("coordinator lock is absent")
        info = self.lock.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_ISLNK(info.st_mode)
            or info.st_nlink != 1
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_uid != os.getuid()
        ):
            raise JournalError("coordinator lock identity differs")

    def __enter__(self) -> "Journal":
        self._validate_namespace(lock_may_be_absent=True)
        flags = os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW
        try:
            descriptor = os.open(self.lock, flags, 0o600)
            os.fchmod(descriptor, 0o600)
            os.fsync(descriptor)
            _fsync_directory(self.root)
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            if "descriptor" in locals():
                os.close(descriptor)
            raise JournalError("exclusive coordinator lease is unavailable") from exc
        self._lock_fd = descriptor
        try:
            self._validate_namespace(lock_may_be_absent=False)
            self.history()
        except BaseException:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(self._lock_fd)
                self._lock_fd = -1
            raise
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._lock_fd >= 0:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(self._lock_fd)
                self._lock_fd = -1

    def _require_lease(self) -> None:
        if self._lock_fd < 0:
            raise JournalError("coordinator lease is not held")

    def _read_entries(self) -> list[tuple[dict[str, Any], bytes, Path]]:
        self._require_lease()
        entries: list[tuple[dict[str, Any], bytes, Path]] = []
        for expected_sequence, path in enumerate(sorted(self.records.iterdir())):
            match = RECORD_NAME.fullmatch(path.name)
            if match is None or int(match.group(1)) != expected_sequence:
                raise JournalError("journal filename sequence differs")
            kind = SLUG_TO_KIND.get(match.group(2))
            if kind is None:
                raise JournalError("journal filename kind differs")
            raw = _read_regular(
                path,
                f"journal record {expected_sequence}",
                maximum=MAX_JSON_BYTES,
                mode=0o400,
            )
            value = strict_json(raw, f"journal record {expected_sequence}")
            if type(value) is not dict or set(value) != RECORD_KEYS:
                raise JournalError("journal record shape differs")
            if value["sequence"] != expected_sequence or value["kind"] != kind:
                raise JournalError("journal record identity differs")
            entries.append((value, raw, path))
        return entries

    def _validate_entries(
        self, entries: list[tuple[dict[str, Any], bytes, Path | None]]
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        previous = ZERO_HASH
        state: dict[str, Any] | None = None
        intent: dict[str, Any] | None = None
        terminal = False
        last_recorded_at = -1
        for sequence, (record, raw, _path) in enumerate(entries):
            if (
                type(record) is not dict
                or set(record) != RECORD_KEYS
                or record["schema"] != RECORD_SCHEMA
                or type(record["sequence"]) is not int
                or record["sequence"] != sequence
                or type(record["recorded_at_epoch"]) is not int
                or record["recorded_at_epoch"] < 0
                or record["recorded_at_epoch"] < last_recorded_at
                or record["previous_record_sha256"] != previous
                or record["kind"] not in KIND_TO_SLUG
                or type(record["payload"]) is not dict
                or record["payload_sha256"]
                != _sha256(canonical_bytes(record["payload"]))
            ):
                raise JournalError("journal record chain differs")
            if terminal:
                raise JournalError("journal continues after terminal state")
            payload = record["payload"]
            kind = record["kind"]
            now = record["recorded_at_epoch"]
            if kind == "CAMPAIGN_OPEN":
                if sequence != 0 or set(payload) != {"activation", "state"}:
                    raise JournalError("campaign-open record differs")
                activation = self.coordinator.canonical_bytes(payload["activation"])
                candidate = self.coordinator.model_campaign_open(activation, now=now)
                if (
                    candidate["phase"] != "OPEN_HEALTHY"
                    or candidate["effect_core_sha256"] != self.descriptor_digest
                    or canonical_bytes(candidate) != canonical_bytes(payload["state"])
                ):
                    raise JournalError("campaign did not open healthy")
                state = candidate
            elif kind == "EFFECT_INTENT":
                if state is None or intent is not None or set(payload) != {
                    "descriptor_sha256",
                    "intent",
                    "state",
                }:
                    raise JournalError("effect-intent record differs")
                if payload["descriptor_sha256"] != self.descriptor_digest:
                    raise JournalError("effect descriptor identity differs")
                observed = {
                    "target": dict(self.coordinator.TARGET),
                    "topology_sha256": state["topology_sha256"],
                    "boot_id_sha256": state["boot_id_sha256"],
                    "healthy_android": True,
                }
                expected_state, expected_intent = self.coordinator.model_effect_intent(
                    state,
                    class_id=CLASS_ID,
                    proof_mode=PROOF_MODE,
                    observed=observed,
                    now=now,
                )
                if (
                    canonical_bytes(payload["state"]) != canonical_bytes(expected_state)
                    or canonical_bytes(payload["intent"])
                    != canonical_bytes(expected_intent)
                ):
                    raise JournalError("effect-intent transition differs")
                state = expected_state
                intent = expected_intent
            elif kind == "EFFECT_HEALTHY_RETURN":
                if state is None or intent is None or set(payload) != {"result", "state"}:
                    raise JournalError("healthy-return record differs")
                result = payload["result"]
                if type(result) is not dict or type(result.get("boot_id_sha256")) is not str:
                    raise JournalError("healthy-return result differs")
                observed = {
                    "target": dict(self.coordinator.TARGET),
                    "topology_sha256": state["topology_sha256"],
                    "boot_id_sha256": result["boot_id_sha256"],
                    "healthy_android": True,
                }
                expected_state, expected_result = self.coordinator.model_healthy_return(
                    state,
                    intent=intent,
                    observed=observed,
                    now=now,
                )
                if (
                    canonical_bytes(payload["state"]) != canonical_bytes(expected_state)
                    or canonical_bytes(result) != canonical_bytes(expected_result)
                ):
                    raise JournalError("healthy-return transition differs")
                state = expected_state
                intent = None
            elif kind == "EFFECT_UNCERTAIN_PARK":
                if state is None or intent is None or set(payload) != {"result", "state"}:
                    raise JournalError("uncertain-park record differs")
                result = payload["result"]
                if type(result) is not dict or type(result.get("reason")) is not str:
                    raise JournalError("uncertain-park result differs")
                expected_state, expected_result = self.coordinator.model_uncertain_cut(
                    state,
                    intent=intent,
                    reason=result["reason"],
                )
                if (
                    canonical_bytes(payload["state"]) != canonical_bytes(expected_state)
                    or canonical_bytes(result) != canonical_bytes(expected_result)
                ):
                    raise JournalError("uncertain-park transition differs")
                state = expected_state
                terminal = True
            elif kind == "CAMPAIGN_CLOSE":
                if state is None or intent is not None or set(payload) != {"state"}:
                    raise JournalError("campaign-close record differs")
                expected_state = self.coordinator.model_close(state)
                if canonical_bytes(payload["state"]) != canonical_bytes(expected_state):
                    raise JournalError("campaign-close transition differs")
                state = expected_state
                terminal = True
            previous = _sha256(raw)
            last_recorded_at = now
        return state, intent

    def history(self) -> list[dict[str, Any]]:
        entries = self._read_entries()
        self._validate_entries(entries)
        return [
            {
                "record": record,
                "receipt": {
                    "path": path.name,
                    "size": len(raw),
                    "sha256": _sha256(raw),
                    "mode": "0400",
                    "nlink": 1,
                },
            }
            for record, raw, path in entries
        ]

    def _tail(self) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        entries = self._read_entries()
        return self._validate_entries(entries)

    def _append(self, kind: str, payload: Mapping[str, Any], *, now: int) -> dict[str, Any]:
        self._require_lease()
        if kind not in KIND_TO_SLUG or type(now) is not int or now < 0:
            raise JournalError("journal append request differs")
        entries = self._read_entries()
        sequence = len(entries)
        previous = _sha256(entries[-1][1]) if entries else ZERO_HASH
        value = {
            "schema": RECORD_SCHEMA,
            "sequence": sequence,
            "kind": kind,
            "recorded_at_epoch": now,
            "previous_record_sha256": previous,
            "payload_sha256": _sha256(canonical_bytes(dict(payload))),
            "payload": dict(payload),
        }
        raw = canonical_bytes(value)
        self._validate_entries(entries + [(value, raw, None)])
        path = self.records / f"{sequence:06d}-{KIND_TO_SLUG[kind]}.json"
        _atomic_publish(path, raw)
        result = self.history()
        if len(result) != sequence + 1:
            raise JournalError("journal append did not become visible")
        return result[-1]

    def record_open(self, activation_raw: bytes, *, now: int) -> dict[str, Any]:
        if self.history():
            raise JournalError("campaign journal is already open")
        state = self.coordinator.model_campaign_open(activation_raw, now=now)
        activation = self.coordinator.strict_json_bytes(activation_raw)
        return self._append(
            "CAMPAIGN_OPEN",
            {"activation": activation, "state": state},
            now=now,
        )

    def record_intent(self, observed: Mapping[str, Any], *, now: int) -> dict[str, Any]:
        state, intent = self._tail()
        if state is None or intent is not None:
            raise JournalError("normal-reboot intent is unavailable")
        next_state, next_intent = self.coordinator.model_effect_intent(
            state,
            class_id=CLASS_ID,
            proof_mode=PROOF_MODE,
            observed=observed,
            now=now,
        )
        return self._append(
            "EFFECT_INTENT",
            {
                "descriptor_sha256": self.descriptor_digest,
                "intent": next_intent,
                "state": next_state,
            },
            now=now,
        )

    def record_healthy_return(
        self, observed: Mapping[str, Any], *, now: int
    ) -> dict[str, Any]:
        state, intent = self._tail()
        if state is None or intent is None:
            raise JournalError("normal-reboot result is unavailable")
        next_state, result = self.coordinator.model_healthy_return(
            state,
            intent=intent,
            observed=observed,
            now=now,
        )
        return self._append(
            "EFFECT_HEALTHY_RETURN",
            {"result": result, "state": next_state},
            now=now,
        )

    def record_uncertain(self, *, reason: str, now: int) -> dict[str, Any]:
        state, intent = self._tail()
        if state is None or intent is None:
            raise JournalError("normal-reboot park is unavailable")
        next_state, result = self.coordinator.model_uncertain_cut(
            state,
            intent=intent,
            reason=reason,
        )
        return self._append(
            "EFFECT_UNCERTAIN_PARK",
            {"result": result, "state": next_state},
            now=now,
        )

    def record_close(self, *, now: int) -> dict[str, Any]:
        state, intent = self._tail()
        if state is None or intent is not None:
            raise JournalError("campaign close is unavailable")
        next_state = self.coordinator.model_close(state)
        return self._append("CAMPAIGN_CLOSE", {"state": next_state}, now=now)


def _fixture_activation(coordinator: types.ModuleType, descriptor_digest: str) -> bytes:
    binding = coordinator.current_binding()
    value = {
        "schema": coordinator.ACTIVATION_SCHEMA,
        "campaign_id": "1" * 32,
        "target": dict(coordinator.TARGET),
        "policy_sha256": binding["policy"]["sha256"],
        "coordinator_sha256": binding["coordinator"]["sha256"],
        "catalog_sha256": binding["catalog_sha256"],
        "effect_core_sha256": descriptor_digest,
        "topology_sha256": "2" * 64,
        "boot_id_sha256": "3" * 64,
        "opened_at_epoch": 100,
        "expires_at_epoch": 100 + coordinator.CAMPAIGN_DURATION_SECONDS,
        "d1_effect_max": coordinator.D1_EFFECT_MAX,
        "d0_command_group_max": coordinator.D0_COMMAND_GROUP_MAX,
        "independent_pass_go_sha256": "4" * 64,
        "live_session_approval_sha256": "5" * 64,
        "operator_attended_opening": True,
    }
    return coordinator.canonical_bytes(value)


def _observed(coordinator: types.ModuleType, state: Mapping[str, Any], boot: str) -> dict[str, Any]:
    return {
        "target": dict(coordinator.TARGET),
        "topology_sha256": state["topology_sha256"],
        "boot_id_sha256": boot,
        "healthy_android": True,
    }


def self_test() -> dict[str, Any]:
    coordinator = load_coordinator()
    descriptor = fixed_descriptor()
    digest = _sha256(canonical_bytes(descriptor))
    with tempfile.TemporaryDirectory(prefix="s22-pref1-reboot-journal-") as temporary:
        root = Path(temporary).resolve() / "campaign"
        Journal.create(root)
        activation = _fixture_activation(coordinator, digest)
        with Journal(root, coordinator) as journal:
            journal.record_open(activation, now=100)
        with Journal(root, coordinator) as journal:
            state, _ = journal._tail()
            assert state is not None
            journal.record_intent(
                _observed(coordinator, state, state["boot_id_sha256"]),
                now=101,
            )
        with Journal(root, coordinator) as journal:
            state, _ = journal._tail()
            assert state is not None
            returned_boot = hashlib.sha256(b"fixture-returned-boot").hexdigest()
            journal.record_healthy_return(
                _observed(coordinator, state, returned_boot),
                now=102,
            )
        with Journal(root, coordinator) as journal:
            journal.record_close(now=103)
            history = journal.history()
            state, intent = journal._tail()
        if state is None or state["phase"] != "CLOSED" or intent is not None:
            raise JournalError("journal fixture did not close")
        return {
            "schema": SCHEMA,
            "status": STATUS,
            "descriptor_sha256": digest,
            "descriptor": descriptor,
            "journal_record_count": len(history),
            "journal_kinds": [item["record"]["kind"] for item in history],
            "journal_tail_sha256": history[-1]["receipt"]["sha256"],
            "restart_reopens": 4,
            "final_phase": state["phase"],
            "durable_journal_fixture": DURABLE_JOURNAL_FIXTURE,
            "coordinator_active": COORDINATOR_ACTIVE,
            "activation_manifest_present": ACTIVATION_MANIFEST_PRESENT,
            "device_action_integration": DEVICE_ACTION_INTEGRATION,
            "live_executor_integration": LIVE_EXECUTOR_INTEGRATION,
            "live_authority": LIVE_AUTHORITY,
            "device_contact": False,
            "approval_created": False,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.error("only --self-test is available")
    print(json.dumps(self_test(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
