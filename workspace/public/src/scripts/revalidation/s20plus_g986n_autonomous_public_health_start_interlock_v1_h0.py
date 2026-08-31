#!/usr/bin/env python3
"""Inactive H0 model for the S20+ cross-code new-start interlock.

The future interlock must serialize a campaign opening against every new
connected S20+ action without delaying an already-owned recovery.  This file
models that split but deliberately provides no operational root opener,
recovery scanner, runner integration, guard publisher, or live authority.

The public CLI is render-only.  The held-dirfd and ``flock`` helpers are
fixture-only protocol models used by the focused tests with temporary
directories.  A sealed fixture scan is not an operational recovery proof.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from types import MappingProxyType
from typing import Any, Iterator, Mapping, Sequence


STATUS = "H0_AUTONOMOUS_PUBLIC_HEALTH_START_INTERLOCK_V1_MODEL_PASS_GO_NOT_ACTIVE"
EXPECTED_SELF_NORMALIZED_SHA256 = "52e7ad159f6875f2367f0eeeaf6a05024c36bb0e3a7c76745defde79852d1e5d"

# Every operational/integration atom is false.  The descriptive fixture model
# below is not a replacement for a Phase-B exact recovery scanner.
START_INTERLOCK_V1_QUALIFIED = False
FIXED_ROOT_OPENER_ACTIVE = False
EXACT_RECOVERY_SCANNER_ACTIVE = False
LEAF_DIRECTORY_FLOCK_ACTIVE = False
SHARED_ACTION_GUARD_CHECK_ACTIVE = False
NEW_START_INTEGRATION_ACTIVE = False
OBSERVER_INTEGRATION_ACTIVE = False
OWNED_RECOVERY_BYPASS_INTEGRATED = False
CONTRACT_ACTIVE = False
MECHANICAL_ACTIVATION = False
LIVE_AUTHORITY = False

FIXTURE_PROTOCOL_MODEL_IMPLEMENTED = True
COORDINATOR_LOCK_IS_RECOVERY_ONLY = True
PRODUCTION_SCANNER_IMPLEMENTED = False
PRODUCTION_GUARD_PUBLISHER_IMPLEMENTED = False

TARGET = MappingProxyType(
    {
        "model": "SM-G986N",
        "device": "y2q",
        "product": "y2qksx",
        "build": "G986NKSS8IYC2",
    }
)

PLAN_SCHEMA = "s20plus_g986n_autonomous_public_health_start_interlock_v1_plan"
SCAN_SCHEMA = "s20plus_g986n_autonomous_public_health_start_interlock_v1_scan"
DECISION_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_start_interlock_v1_decision"
)
BYPASS_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_owned_recovery_bypass_v1"
)

FIXED_ROOTS = MappingProxyType(
    {
        "base": Path(
            "/home/temmie/dev/android-native-init-lab/workspace/private/runs/"
            "s20plus-g986n-autonomous-research"
        ),
        "evidence": Path(
            "/home/temmie/dev/android-native-init-lab/workspace/private/runs/"
            "s20plus-g986n-autonomous-public-health-evidence"
        ),
        "leaf": Path(
            "/home/temmie/dev/android-native-init-lab/workspace/private/runs/"
            "s20plus-g986n-autonomous-public-health-read-leaf"
        ),
    }
)
SHARED_ACTION_GUARD_PARENT = Path(
    "/home/temmie/dev/android-native-init-lab/workspace/private/runs/"
    "s20plus-g986n-routine-actions"
)
SHARED_ACTION_GUARD_NAME = "active-action.json"
SHARED_ACTION_GUARD = SHARED_ACTION_GUARD_PARENT / SHARED_ACTION_GUARD_NAME
SHARED_ACTION_GUARD_PARENT_MODE = 0o775
RECOVERY_COORDINATOR_LOCK_NAME = "coordinator.lock"

# These are data receipts for the exact H0 closure reviewed before this unit.
# The fixture model requires the complete mapping byte-for-byte.  Operational
# Phase B must additionally verify and load the exact scanner; that gate is
# intentionally false here.
PINNED_IDENTITIES = MappingProxyType(
    {
        "campaign_model": MappingProxyType(
            {
                "name": "s20plus_g986n_autonomous_public_health_campaign_v1.py",
                "size": 92_607,
                "sha256": (
                    "43edcfc5bf2c69f96bcef015f305d38be9c310dd92371a2a942e075261dfa8e2"
                ),
                "normalized_sha256": (
                    "be1f73de763b7fcce8e1b74da23cb662244b7b1de9bcbb862ffa59c5c296e773"
                ),
            }
        ),
        "recovery_store_scanner": MappingProxyType(
            {
                "name": "s20plus_g986n_autonomous_public_health_recovery_v1.py",
                "size": 133_053,
                "sha256": (
                    "6186221593b3778475bf3b1ac4bd28bfe013534793eca4ce5fbe0007be8eb0c3"
                ),
                "normalized_sha256": (
                    "1b769167018a2a08e71e67adc00c20148eb4e0a11a6c428bf8fc82b517533b5d"
                ),
            }
        ),
        "recovery_loader": MappingProxyType(
            {
                "name": (
                    "s20plus_g986n_autonomous_public_health_"
                    "recovery_loader_v1_h0.py"
                ),
                "size": 35_315,
                "sha256": (
                    "a210944447dc33b7593b42ba5c46cde9561c9449e8981523b468a4121c4284cc"
                ),
                "normalized_sha256": (
                    "8df4dc534a1d4e9ac1a73867151e4bfcf2450a52283a281c7091d9c47e1e09cc"
                ),
            }
        ),
        "recovery_finalizer": MappingProxyType(
            {
                "name": (
                    "s20plus_g986n_autonomous_public_health_"
                    "recovery_v1_finalizer_h0.py"
                ),
                "size": 162_875,
                "sha256": (
                    "94f6022aebcdc63bcad08757f493349d2e4b198610a367e72181a65694321f0b"
                ),
                "normalized_sha256": (
                    "38cb154e526e8a1a3ad38f8c857f03668f92fedced786745f5e8e85d91e21dac"
                ),
            }
        ),
        "read_leaf_model": MappingProxyType(
            {
                "name": (
                    "s20plus_g986n_autonomous_public_health_coordinator_h0.py"
                ),
                "size": 53_200,
                "sha256": (
                    "e2952245bf4433044fae12ff8114ee9ff4239cbacd173a83cdc5a3dfcfa3d2c6"
                ),
            }
        ),
        "evidence_model": MappingProxyType(
            {
                "name": "s20plus_g986n_autonomous_public_health_evidence_h0.py",
                "size": 96_626,
                "sha256": (
                    "1f737347330b5a2ed1c85e51cca852309ba25e15e7a68d59f6bd6bb4961ba0c4"
                ),
                "normalized_sha256": (
                    "79d2fb339ce6c972790e28675ec407d2dbbd2f8e6f1b1e87008f332cbb708db1"
                ),
            }
        ),
        "base_coordinator_model": MappingProxyType(
            {
                "name": "s20plus_g986n_autonomous_research_coordinator_h0.py",
                "size": 105_904,
                "sha256": (
                    "87ad2dcdcf28d33192ca85bca3f440c87fb7609272dadab297f5b3c6397866dd"
                ),
            }
        ),
        "health_model": MappingProxyType(
            {
                "name": "s20plus_g986n_autonomous_health_h0.py",
                "size": 13_908,
                "sha256": (
                    "03abc4fe5cbe258c0f8eafce27f1230960dc448af616a8f8a14b0e1809baaa4b"
                ),
            }
        ),
        "inventory_model": MappingProxyType(
            {
                "name": "s20plus_g986n_d0_inventory.py",
                "size": 21_474,
                "sha256": (
                    "3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81"
                ),
            }
        ),
    }
)

ZERO_HASH = "0" * 64
HEX64_RE = re.compile(r"[0-9a-f]{64}\Z")
ALLOWED_START_STATES = frozenset({"EMPTY", "PARKED_COMPLETE"})
BLOCKED_STATES = frozenset(
    {
        "ACTIVE",
        "INCOMPLETE",
        "EXPIRED",
        "MALFORMED",
        "UNKNOWN",
    }
)


class StartInterlockV1Error(RuntimeError):
    """An inactive gate, ambiguous state, or contended start always stops."""


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def canonical_bytes(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise StartInterlockV1Error("value is not canonical JSON") from exc


def sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise StartInterlockV1Error("digest input is not bytes")
    return hashlib.sha256(payload).hexdigest()


def _exact_keys(value: Any, expected: set[str], label: str) -> None:
    if type(value) is not dict or set(value) != expected:
        raise StartInterlockV1Error(f"{label} keys differ")


def _require_hex(value: Any, label: str) -> str:
    if type(value) is not str or HEX64_RE.fullmatch(value) is None:
        raise StartInterlockV1Error(f"{label} is not lowercase SHA-256")
    return value


def _metadata(value: os.stat_result) -> tuple[int, ...]:
    return (
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


def _directory_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_uid,
        value.st_gid,
    )


def _validate_owned_directory(
    descriptor: int,
    label: str,
    expected_mode: int,
) -> os.stat_result:
    if type(descriptor) is not int or type(descriptor) is bool or descriptor < 0:
        raise StartInterlockV1Error(f"{label} descriptor differs")
    if type(expected_mode) is not int or type(expected_mode) is bool:
        raise StartInterlockV1Error(f"{label} mode contract differs")
    try:
        metadata = os.fstat(descriptor)
    except OSError as exc:
        raise StartInterlockV1Error(f"{label} descriptor is unavailable") from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != expected_mode
        or metadata.st_uid != os.geteuid()
        or metadata.st_gid != os.getegid()
    ):
        raise StartInterlockV1Error(f"{label} identity differs")
    return metadata


def _validate_held_directory(descriptor: int, label: str) -> os.stat_result:
    return _validate_owned_directory(descriptor, label, 0o700)


def _validate_shared_parent(descriptor: int) -> os.stat_result:
    return _validate_owned_directory(
        descriptor,
        "shared action guard parent",
        SHARED_ACTION_GUARD_PARENT_MODE,
    )


def validate_held_roots(descriptors: Mapping[str, int]) -> dict[str, os.stat_result]:
    if type(descriptors) is not dict or set(descriptors) != {"base", "evidence", "leaf"}:
        raise StartInterlockV1Error("held root descriptor set differs")
    metadata = {
        label: _validate_held_directory(descriptors[label], f"held {label} root")
        for label in ("base", "evidence", "leaf")
    }
    identities = {
        (value.st_dev, value.st_ino)
        for value in metadata.values()
    }
    if len(identities) != 3:
        raise StartInterlockV1Error("held roots are not three distinct directories")
    return metadata


def _open_absolute_directory(
    path: Path,
    label: str,
    *,
    expected_mode: int,
) -> int:
    path = Path(path)
    if not path.is_absolute() or any(
        component in ("", ".", "..") for component in path.parts[1:]
    ):
        raise StartInterlockV1Error(f"{label} path is not fixed absolute")
    descriptor = os.open(
        "/",
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
    )
    try:
        for component in path.parts[1:]:
            child = os.open(
                component,
                os.O_RDONLY
                | os.O_DIRECTORY
                | os.O_CLOEXEC
                | os.O_NOFOLLOW
                | os.O_NONBLOCK,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = child
        _validate_owned_directory(descriptor, label, expected_mode)
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _open_exact_fixed_roots() -> tuple[dict[str, int], int]:
    """Future read-only opener; the public H0 entrypoint never calls it."""

    held: dict[str, int] = {}
    shared_parent = -1
    try:
        for label in ("base", "evidence", "leaf"):
            held[label] = _open_absolute_directory(
                FIXED_ROOTS[label],
                label,
                expected_mode=0o700,
            )
        validate_held_roots(held)
        shared_parent = _open_absolute_directory(
            SHARED_ACTION_GUARD_PARENT,
            "shared action guard parent",
            expected_mode=SHARED_ACTION_GUARD_PARENT_MODE,
        )
        _validate_shared_parent(shared_parent)
        return held, shared_parent
    except Exception:
        for descriptor in held.values():
            os.close(descriptor)
        if shared_parent >= 0:
            os.close(shared_parent)
        raise


def close_held_roots(descriptors: Mapping[str, int], shared_parent: int) -> None:
    for descriptor in descriptors.values():
        try:
            os.close(descriptor)
        except OSError:
            pass
    try:
        os.close(shared_parent)
    except OSError:
        pass


SCAN_KEYS = {
    "schema",
    "status",
    "target",
    "source_identities",
    "durable_content_validated",
    "campaign_present",
    "completion_present",
    "campaign_parked",
    "complete_chain_validated",
    "expired",
    "incomplete",
    "malformed",
    "state_sha256",
    "device_commands_authorized",
    "replay_authorized",
    "finalizer_resume_authorized",
}


def validate_scan_payload(value: Any) -> dict[str, Any]:
    _exact_keys(value, SCAN_KEYS, "interlock scan")
    if value["target"] != dict(TARGET):
        raise StartInterlockV1Error("interlock scan target differs")
    if value["source_identities"] != _plain(PINNED_IDENTITIES):
        raise StartInterlockV1Error("interlock scan source identities differ")
    status_value = value["status"]
    if type(status_value) is not str or status_value not in (
        ALLOWED_START_STATES | BLOCKED_STATES
    ):
        raise StartInterlockV1Error("interlock scan status differs")
    for key in (
        "durable_content_validated",
        "campaign_present",
        "completion_present",
        "campaign_parked",
        "complete_chain_validated",
        "expired",
        "incomplete",
        "malformed",
        "device_commands_authorized",
        "replay_authorized",
        "finalizer_resume_authorized",
    ):
        if type(value[key]) is not bool:
            raise StartInterlockV1Error(f"interlock scan {key} is not strict bool")
    _require_hex(value["state_sha256"], "interlock state digest")
    common_no_authority = (
        value["device_commands_authorized"] is False
        and value["replay_authorized"] is False
        and value["finalizer_resume_authorized"] is False
    )
    empty_exact = (
        status_value == "EMPTY"
        and value["durable_content_validated"] is True
        and value["campaign_present"] is False
        and value["completion_present"] is False
        and value["campaign_parked"] is False
        and value["complete_chain_validated"] is True
        and value["expired"] is False
        and value["incomplete"] is False
        and value["malformed"] is False
        and value["state_sha256"] == ZERO_HASH
        and common_no_authority
    )
    parked_exact = (
        status_value == "PARKED_COMPLETE"
        and value["durable_content_validated"] is True
        and value["campaign_present"] is True
        and value["completion_present"] is True
        and value["campaign_parked"] is True
        and value["complete_chain_validated"] is True
        and value["expired"] is False
        and value["incomplete"] is False
        and value["malformed"] is False
        and value["state_sha256"] != ZERO_HASH
        and common_no_authority
    )
    if status_value in ALLOWED_START_STATES and not (empty_exact or parked_exact):
        raise StartInterlockV1Error("allowlisted interlock state is not exact")
    if status_value in BLOCKED_STATES and common_no_authority is not True:
        raise StartInterlockV1Error("blocked interlock state unexpectedly grants authority")
    if value["schema"] != SCAN_SCHEMA:
        raise StartInterlockV1Error("interlock scan schema differs")
    return dict(value)


def model_scan_payload(status_value: str) -> dict[str, Any]:
    """Build a strict fixture receipt; it is not an operational scan."""

    if type(status_value) is not str or status_value not in (
        ALLOWED_START_STATES | BLOCKED_STATES
    ):
        raise StartInterlockV1Error("fixture state is outside the closed model")
    if status_value == "EMPTY":
        flags = {
            "durable_content_validated": True,
            "campaign_present": False,
            "completion_present": False,
            "campaign_parked": False,
            "complete_chain_validated": True,
            "expired": False,
            "incomplete": False,
            "malformed": False,
            "state_sha256": ZERO_HASH,
        }
    elif status_value == "PARKED_COMPLETE":
        flags = {
            "durable_content_validated": True,
            "campaign_present": True,
            "completion_present": True,
            "campaign_parked": True,
            "complete_chain_validated": True,
            "expired": False,
            "incomplete": False,
            "malformed": False,
            "state_sha256": "1" * 64,
        }
    else:
        flags = {
            "durable_content_validated": status_value not in {"MALFORMED", "UNKNOWN"},
            "campaign_present": status_value != "UNKNOWN",
            "completion_present": False,
            "campaign_parked": status_value in {"INCOMPLETE", "EXPIRED", "MALFORMED"},
            "complete_chain_validated": False,
            "expired": status_value == "EXPIRED",
            "incomplete": status_value == "INCOMPLETE",
            "malformed": status_value == "MALFORMED",
            "state_sha256": "2" * 64,
        }
    value = {
        "schema": SCAN_SCHEMA,
        "status": status_value,
        "target": dict(TARGET),
        "source_identities": _plain(PINNED_IDENTITIES),
        **flags,
        "device_commands_authorized": False,
        "replay_authorized": False,
        "finalizer_resume_authorized": False,
    }
    validate_scan_payload(value)
    return value


_SCAN_SEAL = object()


class _FixtureVerifiedScan:
    """Sealed test receipt standing in for a future exact scanner result."""

    __slots__ = ("_seal", "payload", "raw")

    def __init__(self, payload: Mapping[str, Any], seal: object) -> None:
        if seal is not _SCAN_SEAL:
            raise StartInterlockV1Error("fixture scan seal differs")
        plain = validate_scan_payload(dict(payload))
        self._seal = seal
        self.payload = plain
        self.raw = canonical_bytes(plain)

    def __reduce__(self) -> Any:
        raise TypeError("fixture verified scan is not serializable")


def model_verified_scan(status_value: str) -> _FixtureVerifiedScan:
    """Test-only constructor; public operational code never accepts it."""

    return _FixtureVerifiedScan(model_scan_payload(status_value), _SCAN_SEAL)


def _require_fixture_scan(scan: _FixtureVerifiedScan) -> dict[str, Any]:
    if type(scan) is not _FixtureVerifiedScan or scan._seal is not _SCAN_SEAL:
        raise StartInterlockV1Error("fixture scan was not produced by the model verifier")
    payload = validate_scan_payload(dict(scan.payload))
    if canonical_bytes(payload) != scan.raw:
        raise StartInterlockV1Error("fixture scan bytes changed")
    return payload


def _require_shared_guard_absent_at(shared_parent: int) -> None:
    _validate_shared_parent(shared_parent)
    try:
        os.stat(
            SHARED_ACTION_GUARD_NAME,
            dir_fd=shared_parent,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return
    except OSError as exc:
        if exc.errno == errno.ENOENT:
            return
        raise StartInterlockV1Error("shared action guard state is unreadable") from exc
    raise StartInterlockV1Error("a shared S20+ action guard is already present")


class _FixtureStartLease:
    """A non-authorizing marker that exists only while the leaf flock is held."""

    __slots__ = ("_active", "_leaf_descriptor", "scan_sha256", "state")

    def __init__(self, leaf_descriptor: int, scan: _FixtureVerifiedScan) -> None:
        payload = _require_fixture_scan(scan)
        self._active = True
        self._leaf_descriptor = leaf_descriptor
        self.scan_sha256 = sha256_bytes(scan.raw)
        self.state = payload["status"]

    def decision(self) -> dict[str, Any]:
        if self._active is not True:
            raise StartInterlockV1Error("fixture start lease is no longer held")
        return {
            "schema": DECISION_SCHEMA,
            "status": "FIXTURE_GUARD_CLAIM_WINDOW_MODELED",
            "target": dict(TARGET),
            "campaign_state": self.state,
            "scan_sha256": self.scan_sha256,
            "leaf_directory_flock_held": True,
            "shared_action_guard_absent_under_lock": True,
            "future_runner_must_publish_own_guard_before_unlock": True,
            "new_start_authorized_by_live_contract": False,
            "device_commands_authorized": False,
            "replay_authorized": False,
            "finalizer_resume_authorized": False,
            "live_authority": False,
        }

    def __reduce__(self) -> Any:
        raise TypeError("fixture start lease is not serializable")

    def _deactivate(self) -> None:
        self._active = False


@contextmanager
def _fixture_new_start_slot(
    held_roots: Mapping[str, int],
    shared_parent: int,
    scan: _FixtureVerifiedScan,
) -> Iterator[_FixtureStartLease]:
    """Exercise the future lock order against temporary fixture descriptors.

    This function is intentionally test-only and does not open a path, publish
    a guard, execute a command, or authorize a caller.  Phase B must replace
    the sealed fixture scan with the exact recovery scanner integration.
    """

    metadata = validate_held_roots(held_roots)
    _validate_shared_parent(shared_parent)
    leaf_descriptor = held_roots["leaf"]
    try:
        fcntl.flock(leaf_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise StartInterlockV1Error("leaf-directory start interlock is busy") from exc
    except OSError as exc:
        if exc.errno in (errno.EACCES, errno.EAGAIN):
            raise StartInterlockV1Error(
                "leaf-directory start interlock is busy"
            ) from exc
        raise StartInterlockV1Error(
            "leaf-directory start interlock could not be acquired"
        ) from exc
    try:
        payload = _require_fixture_scan(scan)
        if payload["status"] not in ALLOWED_START_STATES:
            raise StartInterlockV1Error(
                "campaign state blocks every new connected start"
            )
        _require_shared_guard_absent_at(shared_parent)
        if _directory_identity(os.fstat(leaf_descriptor)) != _directory_identity(
            metadata["leaf"]
        ):
            raise StartInterlockV1Error("held leaf root changed under interlock")
        lease = _FixtureStartLease(leaf_descriptor, scan)
        try:
            yield lease
        finally:
            lease._deactivate()
        _require_shared_guard_absent_at(shared_parent)
        if _directory_identity(os.fstat(leaf_descriptor)) != _directory_identity(
            metadata["leaf"]
        ):
            raise StartInterlockV1Error("held leaf root changed before unlock")
    finally:
        try:
            fcntl.flock(leaf_descriptor, fcntl.LOCK_UN)
        except OSError as exc:
            raise StartInterlockV1Error(
                "leaf-directory start interlock release failed"
            ) from exc


def model_owned_recovery_bypass() -> dict[str, Any]:
    """Describe priority only; it grants no recovery command or new start."""

    return {
        "schema": BYPASS_SCHEMA,
        "status": "OWNED_CONTINUATION_RECOVERY_BYPASSES_NEW_START_INTERLOCK",
        "target": dict(TARGET),
        "acquires_leaf_directory_flock": False,
        "scans_campaign_for_new_start": False,
        "requires_exact_preexisting_owned_shared_guard": True,
        "requires_exact_owned_journal": True,
        "creates_shared_action_guard": False,
        "new_start_authorized": False,
        "device_commands_authorized_by_interlock": False,
        "replay_authorized_by_interlock": False,
        "recovery_authorized_by_interlock": False,
        "live_authority": False,
    }


def normalized_source_sha256(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise StartInterlockV1Error("source normalization requires bytes")
    normalized = payload
    normalized, status_count = re.subn(
        rb'^STATUS = "[A-Z0-9_]+"$',
        b'STATUS = "<REVIEWED_STATUS>"',
        normalized,
        flags=re.MULTILINE,
    )
    normalized, anchor_count = re.subn(
        rb'^EXPECTED_SELF_NORMALIZED_SHA256 = "[0-9a-f]{64}"$',
        b'EXPECTED_SELF_NORMALIZED_SHA256 = "<REVIEWED_SELF_ANCHOR>"',
        normalized,
        flags=re.MULTILINE,
    )
    if (status_count, anchor_count) != (1, 1):
        raise StartInterlockV1Error("source identity normalization is ambiguous")
    for name in (
        "START_INTERLOCK_V1_QUALIFIED",
        "FIXED_ROOT_OPENER_ACTIVE",
        "EXACT_RECOVERY_SCANNER_ACTIVE",
        "LEAF_DIRECTORY_FLOCK_ACTIVE",
        "SHARED_ACTION_GUARD_CHECK_ACTIVE",
        "NEW_START_INTEGRATION_ACTIVE",
        "OBSERVER_INTEGRATION_ACTIVE",
        "OWNED_RECOVERY_BYPASS_INTEGRATED",
        "CONTRACT_ACTIVE",
        "MECHANICAL_ACTIVATION",
        "LIVE_AUTHORITY",
    ):
        normalized, count = re.subn(
            rf"^{name} = (?:False|True)$".encode(),
            f"{name} = <REVIEWED_BOOLEAN>".encode(),
            normalized,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise StartInterlockV1Error("source gate normalization is ambiguous")
    return sha256_bytes(normalized)


def _read_self_bytes() -> bytes:
    path = Path(__file__)
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > 128 * 1024
        ):
            raise StartInterlockV1Error("interlock source identity differs")
        payload = bytearray()
        while len(payload) < before.st_size:
            chunk = os.read(descriptor, before.st_size - len(payload))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) != before.st_size or os.read(descriptor, 1):
            raise StartInterlockV1Error("interlock source length differs")
        if _metadata(before) != _metadata(os.fstat(descriptor)):
            raise StartInterlockV1Error("interlock source changed while read")
        return bytes(payload)
    finally:
        os.close(descriptor)


def _require_operational_gate() -> None:
    if not all(
        value is True
        for value in (
            START_INTERLOCK_V1_QUALIFIED,
            FIXED_ROOT_OPENER_ACTIVE,
            EXACT_RECOVERY_SCANNER_ACTIVE,
            LEAF_DIRECTORY_FLOCK_ACTIVE,
            SHARED_ACTION_GUARD_CHECK_ACTIVE,
            NEW_START_INTEGRATION_ACTIVE,
            OBSERVER_INTEGRATION_ACTIVE,
            OWNED_RECOVERY_BYPASS_INTEGRATED,
            CONTRACT_ACTIVE,
            MECHANICAL_ACTIVATION,
            LIVE_AUTHORITY,
        )
    ):
        raise StartInterlockV1Error("start interlock operational owner is inactive")


def acquire_new_start_interlock() -> None:
    """Future no-input entrypoint; H0 stops before any fixed-root access."""

    _require_operational_gate()
    raise StartInterlockV1Error("operational start interlock is not implemented")


def render_plan() -> dict[str, Any]:
    source = _read_self_bytes()
    normalized_sha256 = normalized_source_sha256(source)
    if normalized_sha256 != EXPECTED_SELF_NORMALIZED_SHA256:
        raise StartInterlockV1Error(
            "start interlock normalized source identity differs"
        )
    gates = {
        "start_interlock_v1_qualified": START_INTERLOCK_V1_QUALIFIED,
        "fixed_root_opener_active": FIXED_ROOT_OPENER_ACTIVE,
        "exact_recovery_scanner_active": EXACT_RECOVERY_SCANNER_ACTIVE,
        "leaf_directory_flock_active": LEAF_DIRECTORY_FLOCK_ACTIVE,
        "shared_action_guard_check_active": SHARED_ACTION_GUARD_CHECK_ACTIVE,
        "new_start_integration_active": NEW_START_INTEGRATION_ACTIVE,
        "observer_integration_active": OBSERVER_INTEGRATION_ACTIVE,
        "owned_recovery_bypass_integrated": OWNED_RECOVERY_BYPASS_INTEGRATED,
        "contract_active": CONTRACT_ACTIVE,
        "mechanical_activation": MECHANICAL_ACTIVATION,
        "live_authority": LIVE_AUTHORITY,
    }
    if any(gates.values()):
        raise StartInterlockV1Error("H0 render found an active gate")
    return {
        "schema": PLAN_SCHEMA,
        "status": STATUS,
        "target": dict(TARGET),
        "gates": gates,
        "fixture_protocol_model_implemented": FIXTURE_PROTOCOL_MODEL_IMPLEMENTED,
        "production_scanner_implemented": PRODUCTION_SCANNER_IMPLEMENTED,
        "production_guard_publisher_implemented": (
            PRODUCTION_GUARD_PUBLISHER_IMPLEMENTED
        ),
        "cli": ["--render-plan"],
        "self": {
            "size": len(source),
            "sha256": sha256_bytes(source),
            "normalized_sha256": normalized_sha256,
            "normalized_sha256_expected": EXPECTED_SELF_NORMALIZED_SHA256,
        },
        "fixed_roots": {key: str(value) for key, value in FIXED_ROOTS.items()},
        "cross_code_lock": {
            "object": "held-leaf-root-directory-fd",
            "operation": "flock-LOCK_EX-LOCK_NB",
            "wait_or_retry": False,
            "held_during_scan_and-runner-owned-guard-publication": True,
        },
        "shared_action_guard": {
            "path": str(SHARED_ACTION_GUARD),
            "parent_mode": "0775",
            "required_absent_under_lock": True,
            "created_or_deleted_by_this_h0_source": False,
        },
        "state_admission": {
            "allow": sorted(ALLOWED_START_STATES),
            "block": sorted(BLOCKED_STATES),
            "content_validation_required": True,
            "expired_blocks": True,
            "incomplete_blocks": True,
            "malformed_blocks": True,
            "fixture_scan_is_operational_proof": False,
        },
        "coordinator_lock": {
            "name": RECOVERY_COORDINATOR_LOCK_NAME,
            "recovery_only": COORDINATOR_LOCK_IS_RECOVERY_ONLY,
            "used_for_new_start": False,
            "used_by_fixture_flock": False,
        },
        "owned_recovery_priority": model_owned_recovery_bypass(),
        "pinned_identities": _plain(PINNED_IDENTITIES),
        "production_entrypoint": "inactive-unimplemented",
        "caller_inputs": [],
        "callbacks": [],
        "backends": [],
        "device_commands": [],
        "device_effects": [],
        "root_commands": [],
        "odin_commands": [],
        "partition_transfers": [],
        "private_writes": [],
        "runner_integrations": [],
        "unresolved_gates": [
            "exact-recovery-content-scanner-adapter",
            "fixed-root-and-shared-parent-opener",
            "runner-owned-guard-publication-under-held-flock",
            "routine-d0-and-root-health-observer-integration",
            "routine-d1-download-f1-resident-f1-r1-start-integration",
            "owned-continuation-recovery-bypass-review",
            "target-contract-and-mechanical-activation",
            "combined-independent-review",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--render-plan", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.render_plan:
        build_parser().error("only --render-plan exists in start-interlock H0")
    print(json.dumps(render_plan(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
