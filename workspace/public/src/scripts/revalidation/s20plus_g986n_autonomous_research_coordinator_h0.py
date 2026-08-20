#!/usr/bin/env python3
"""Dormant H0 journal/state-machine candidate for the S20+ research lane.

This file is not a mechanically activatable live coordinator.  It contains a
host-only strict journal model and no ADB, USB, Odin, shell, root, observer,
backend, or callback transport.  ``COORDINATOR_ACTIVE`` is deliberately false
and the CLI is render-only.  Effect-facing methods remain unavailable until a
separate exact live-action integration is implemented and reviewed.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
SCHEMA = "s20plus_g986n_autonomous_research_coordinator_h0_v1"
STATUS = "H0_AUTONOMOUS_RESEARCH_COORDINATOR_PASS_GO_NOT_ACTIVE"
COORDINATOR_ACTIVE = False
LIVE_AUTHORITY = False
MECHANICALLY_ACTIVATABLE = False
LIVE_ACTION_INTEGRATION = False

TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "build": "G986NKSS8IYC2",
}

LIMITS = {
    "session_duration_sec": 4 * 60 * 60,
    "read_operations_max": 64,
    "private_evidence_bytes_max": 32 * 1024 * 1024,
    "single_command_output_bytes_max": 1024 * 1024,
    "control_transactions_max": 16,
    "component_effects_max": 24,
    "normal_reboots_max": 8,
    "download_roundtrips_max": 8,
}

EXPECTED_ANDROID_TOPOLOGY_SHA256 = (
    "3279d577ef7a789f8aac93664e3b45543e10522b08d29ebabc99564ca86295f1"
)
EXPECTED_DOWNLOAD_TOPOLOGY_SHA256 = frozenset(
    {
        EXPECTED_ANDROID_TOPOLOGY_SHA256,
        "ae90de878991480bf8aafc6e131953d185245aba4fa8d9cd8d0507810d2c96e1",
    }
)
EMPTY_DOWNLOAD_LISTING_SHA256 = (
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
)
EMPTY_DOWNLOAD_LISTING_GRAMMAR = "odin4-list-v1-empty-lines"

CAMPAIGN_LIMITS = {
    "campaign_duration_sec": 24 * 60 * 60,
    "read_operations_max": 256,
    "private_evidence_bytes_max": 128 * 1024 * 1024,
    "control_transactions_max": 64,
    "component_effects_max": 96,
    "normal_reboots_max": 32,
    "download_roundtrips_max": 32,
}

# These are intentionally fixed private roots.  No public request accepts a
# replacement root, campaign id, journal filename, endpoint, or destination.
PRIVATE_RUN_ROOT = (
    ROOT / "workspace/private/runs/s20plus-g986n-autonomous-research"
)
CAMPAIGN_GUARD_PATH = PRIVATE_RUN_ROOT / "active-campaign.json"
CAMPAIGNS_ROOT = PRIVATE_RUN_ROOT / "campaigns"
MAX_JOURNAL_BYTES = 1024 * 1024
ZERO_HASH = "0" * 64

READ_ACTIONS = ("public-health",)
CONTROL_ACTIONS = ("reboot-system", "download-roundtrip")
ACTIONS = READ_ACTIONS + CONTROL_ACTIONS + ("prepare-f1-readiness",)

SOURCE_SPECS = {
    "policy_owner": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_g986n_autonomous_research_h0.py",
        "size": 14_605,
        "sha256": "64bd8ec99730f37e790cca1ca8e2ab1ea48377f5bdb08596ef23c58fe7daa2b7",
    },
    "inventory": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_g986n_d0_inventory.py",
        "size": 21_474,
        "sha256": "3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81",
    },
    "routine_d0": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_g986n_routine_d0.py",
        "size": 12_649,
        "sha256": "2377e463e1ec4869fd9ba7a5155aeb6c792bdb5b5b969c902a2b0e5a00fda77c",
    },
    "routine_actions": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_g986n_routine_actions.py",
        "size": 41_739,
        "sha256": "7b1d8989db5ffbf012cbf356e4e1411d5e487e965361b4ea61307a508b17bc72",
    },
    "download_exit": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_g986n_download_exit_d1.py",
        "size": 34_025,
        "sha256": "72411a9e7983849dca0cbb3775f4f070c9642b9c8efb929fd519826e954b336a",
    },
}

# Replaced with the final normalized source digest after this file is frozen.
EXPECTED_COORDINATOR_NORMALIZED_SHA256 = "8d28f370f16d1f0d86eaa456fae09c01160d9fd8445529184643223934f4aea1"

DEFERRED_ROOT_PROFILES = {
    "root-pid1-status": {
        "paths": {"/proc/1/status": "direct-regular-proc"},
        "status": "DEFERRED_NOT_AN_ACTION",
    },
    "root-pid1-mountinfo": {
        "paths": {"/proc/1/mountinfo": "direct-regular-proc"},
        "status": "DEFERRED_NOT_AN_ACTION",
    },
    "root-namespace-links": {
        "paths": {
            "/proc/1/ns/mnt": "direct-proc-symlink",
            "/proc/1/ns/pid": "direct-proc-symlink",
            "/proc/1/ns/uts": "direct-proc-symlink",
        },
        "status": "DEFERRED_NOT_AN_ACTION",
    },
    "root-selinux-enforce": {
        "paths": {"/sys/fs/selinux/enforce": "direct-regular-sysfs"},
        "status": "DEFERRED_NOT_AN_ACTION",
    },
    "root-magisk-metadata": {
        "paths": {
            "/data/adb/magisk/magisk": "direct-regular",
            "/data/adb/magisk/busybox": "direct-regular",
            "/data/adb/magisk/util_functions.sh": "direct-regular",
            "/data/adb/modules": "direct-directory",
            "/data/adb/modules_update": "direct-directory",
        },
        "status": "DEFERRED_NOT_AN_ACTION",
    },
}

ROOT_PROFILE_ACTIVATION_REQUIREMENTS = {
    "exact_root_launcher_and_transport_receipts": True,
    "fixed_command_timeout": True,
    "per_input_size_ceiling_before_read": True,
    "stable_no_follow_metadata_before_and_after": True,
    "directory_entry_count_and_name_grammar": True,
    "exact_parser_source_receipts": True,
    "hostile_cut_and_replacement_tests": True,
}

LIVE_COORDINATOR_REQUIREMENTS = {
    "fixed_private_campaign_guard_path": True,
    "fixed_private_campaign_run_root": True,
    "bounded_no_follow_canonical_duplicate_safe_reads": True,
    "reject_duplicate_noncanonical_nonfinite_json": True,
    "derive_campaign_session_policy_source_and_ordinal_from_current_guard": True,
    "derive_endpoint_from_current_validated_arrival": True,
    "hash_actual_validated_predecessor_bytes": True,
    "validate_full_opening_entry_arrival_return_chain": True,
    "ordinal_equals_current_campaign_roundtrip_count": True,
    "exact_child_membership_in_current_campaign": True,
    "atomic_both_scope_counters_and_intent": True,
    "debit_only_or_partial_scope_has_zero_authority": True,
    "expiry_recovery_only_from_current_guard_chain": True,
    "old_foreign_extra_and_partial_nodes_zero_authority": True,
    "terminal_and_guard_cuts_are_read_only": True,
    "pre_f1_stops_before_f1_or_odin_payload": True,
    "reboot_requires_canonical_healthy_observation": True,
    "return_requires_canonical_healthy_observation": True,
    "health_identity_serial_topology_exact_and_boot_fresh": True,
    "pending_health_blocks_next_control_and_terminal": True,
    "opening_guard_first_immutable_and_exact_reconciliation": True,
    "typed_issued_at_current_and_monotonic": True,
    "new_transaction_nodes_before_both_expiries": True,
    "post_expiry_only_prebound_continuations": True,
}

HEX64_RE = re.compile(r"[0-9a-f]{64}\Z")
ID_RE = re.compile(r"[0-9a-f]{32}\Z")
ENTRY_NAME_RE = re.compile(r"entry-([0-9]{6})\.json\Z")
BASELINE_NAME_RE = re.compile(r"baseline-([0-9]{6})\.json\Z")
ARRIVAL_NAME_RE = re.compile(r"arrival-([0-9]{6})\.json\Z")
RETURN_NAME_RE = re.compile(r"return-([0-9]{6})\.json\Z")
REBOOT_NAME_RE = re.compile(r"reboot-([0-9]{6})\.json\Z")
REBOOT_HEALTH_NAME_RE = re.compile(r"reboot-health-([0-9]{6})\.json\Z")
RETURN_HEALTH_NAME_RE = re.compile(r"return-health-([0-9]{6})\.json\Z")
MAX_ORDINAL = 999_999
COUNTER_KEYS = {
    "control_transactions",
    "component_effects_consumed",
    "component_effects_reserved",
    "normal_reboots",
    "download_roundtrips",
    "roundtrip_entries",
    "roundtrip_returns",
}

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
AT_EMPTY_PATH = 0x1000


class CoordinatorError(RuntimeError):
    """Every malformed or unavailable journal state fails closed."""


def _require_private_context() -> None:
    if COORDINATOR_ACTIVE is True and LIVE_AUTHORITY is True:
        return
    raise CoordinatorError(
        "private coordinator filesystem is dormant; use the reviewed live context"
    )


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
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CoordinatorError("value is not canonical JSON") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _reject_constant(value: str) -> Any:
    raise ValueError(f"non-finite JSON constant {value}")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


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


def _allowed_final_name(name: str) -> bool:
    """Return whether *name* is one of the closed journal final names."""
    _require_private_context()
    if type(name) is not str or name in {"", ".", ".."} or "/" in name:
        return False
    if name in {"active-campaign.json", "opening.json", "session-opening.json", "terminal.json"}:
        return True
    return any(
        regex.fullmatch(name)
        for regex in (
            ENTRY_NAME_RE,
            BASELINE_NAME_RE,
            ARRIVAL_NAME_RE,
            RETURN_NAME_RE,
            REBOOT_NAME_RE,
            REBOOT_HEALTH_NAME_RE,
            RETURN_HEALTH_NAME_RE,
        )
    )


def _managed_path(path: Path) -> str:
    """Validate the closed lexical path grammar before any filesystem access."""
    _require_private_context()
    path = Path(path)
    root = Path(PRIVATE_RUN_ROOT)
    if not path.is_absolute() or not root.is_absolute():
        raise CoordinatorError("journal path must be absolute")
    parts = path.parts
    root_parts = root.parts
    if any(part in {".", ".."} for part in parts):
        raise CoordinatorError("journal path contains traversal")
    if len(parts) < len(root_parts) or parts[: len(root_parts)] != root_parts:
        raise CoordinatorError("journal path is outside the fixed private root")
    relative = parts[len(root_parts) :]
    if not relative:
        return "run-root"
    if relative == ("active-campaign.json",):
        return "guard"
    if relative == ("campaigns",):
        return "campaigns-root"
    if len(relative) == 2 and relative[0] == "campaigns" and ID_RE.fullmatch(relative[1]):
        return "campaign"
    if (
        len(relative) == 3
        and relative[0] == "campaigns"
        and ID_RE.fullmatch(relative[1])
        and relative[2] == "session"
    ):
        return "session"
    if (
        len(relative) == 4
        and relative[0] == "campaigns"
        and ID_RE.fullmatch(relative[1])
        and relative[2] == "session"
        and relative[3] != "active-campaign.json"
        and _allowed_final_name(relative[3])
    ):
        return "journal-final"
    raise CoordinatorError("journal path is outside the closed namespace grammar")


def _directory_stat(metadata: os.stat_result, label: str, *, private: bool) -> None:
    if not stat.S_ISDIR(metadata.st_mode):
        raise CoordinatorError(f"{label} is not a directory")
    if private:
        expected_uid = getattr(os, "getuid", lambda: metadata.st_uid)()
        expected_gid = getattr(os, "getgid", lambda: metadata.st_gid)()
        if (
            stat.S_IMODE(metadata.st_mode) != 0o700
            or metadata.st_uid != expected_uid
            or metadata.st_gid != expected_gid
        ):
            raise CoordinatorError(f"{label} ownership or mode differs")


def _open_components(path: Path, *, create: bool = False) -> int:
    """Open a validated absolute path from `/` using only dirfd-relative opens."""
    _require_private_context()
    path = Path(path)
    kind = _managed_path(path)
    if kind not in {"run-root", "campaigns-root", "campaign", "session"}:
        raise CoordinatorError("managed path is not a directory")
    root_parts = Path(PRIVATE_RUN_ROOT).parts
    descriptor = -1
    try:
        descriptor = os.open(
            os.sep,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
        for index, component in enumerate(path.parts[1:], start=1):
            private = index >= len(root_parts) - 1
            try:
                next_descriptor = os.open(
                    component,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                    dir_fd=descriptor,
                )
            except FileNotFoundError:
                if not create or not private:
                    raise
                os.mkdir(component, mode=0o700, dir_fd=descriptor)
                os.fsync(descriptor)
                next_descriptor = os.open(
                    component,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                    dir_fd=descriptor,
                )
            try:
                before = os.fstat(next_descriptor)
                _directory_stat(before, "managed directory", private=private)
                after = os.fstat(next_descriptor)
                if _metadata(before) != _metadata(after):
                    raise CoordinatorError("managed directory changed during open")
            except CoordinatorError:
                os.close(next_descriptor)
                raise
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except CoordinatorError:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise
    except (OSError, TypeError) as exc:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise CoordinatorError("managed directory is unavailable or indirect") from exc


def _open_directory(path: Path) -> int:
    """Open only a closed-grammar managed directory, component by component."""
    _require_private_context()
    return _open_components(Path(path))


def _open_managed_directory(path: Path) -> int:
    """Open a fixed-root directory one component at a time with no follows."""
    _require_private_context()
    return _open_components(Path(path))


def _read_bounded_at(
    parent: int,
    name: str,
    label: str,
    mode: int = 0o400,
    *,
    allow_guard: bool = False,
) -> bytes:
    """Read one allowlisted final via a pinned parent dirfd."""
    _require_private_context()
    if name == "active-campaign.json" and not allow_guard:
        raise CoordinatorError("guard name is not valid in a session directory")
    if not _allowed_final_name(name):
        raise CoordinatorError("journal final name is outside the closed grammar")
    descriptor = -1
    try:
        parent_before = os.fstat(parent)
        _directory_stat(parent_before, "journal parent", private=True)
        parent_owner = (parent_before.st_uid, parent_before.st_gid)
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=parent,
        )
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or stat.S_IMODE(before.st_mode) != mode
            or before.st_size > MAX_JOURNAL_BYTES
            or (before.st_uid, before.st_gid) != parent_owner
        ):
            raise CoordinatorError(
                f"{label} is not a bounded direct regular file owned by its parent"
            )
        payload = bytearray()
        while True:
            chunk = os.read(
                descriptor,
                min(64 * 1024, MAX_JOURNAL_BYTES + 1 - len(payload)),
            )
            if not chunk:
                break
            payload.extend(chunk)
            if len(payload) > MAX_JOURNAL_BYTES:
                raise CoordinatorError(f"{label} is oversized")
        after = os.fstat(descriptor)
        if _metadata(before) != _metadata(after):
            raise CoordinatorError(f"{label} changed during read")
        parent_after = os.fstat(parent)
        if (
            parent_after.st_dev,
            parent_after.st_ino,
            parent_after.st_mode,
            parent_after.st_uid,
            parent_after.st_gid,
        ) != (
            parent_before.st_dev,
            parent_before.st_ino,
            parent_before.st_mode,
            parent_before.st_uid,
            parent_before.st_gid,
        ):
            raise CoordinatorError(f"{label} parent changed during read")
        if (after.st_uid, after.st_gid) != parent_owner:
            raise CoordinatorError(f"{label} owner changed during read")
        return bytes(payload)
    except (OSError, TypeError) as exc:
        raise CoordinatorError(f"{label} is missing or indirect") from exc
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError as exc:
                raise CoordinatorError(f"{label} close failed") from exc


def _read_bounded(path: Path, label: str, mode: int = 0o400) -> bytes:
    """Read a fixed final by first pinning its exact parent directory."""
    _require_private_context()
    path = Path(path)
    kind = _managed_path(path)
    if kind not in {"guard", "journal-final"}:
        raise CoordinatorError("journal path is not a fixed final")
    parent = -1
    try:
        parent = _open_managed_directory(path.parent)
        return _read_bounded_at(
            parent,
            path.name,
            label,
            mode,
            allow_guard=kind == "guard",
        )
    finally:
        if parent >= 0:
            try:
                os.close(parent)
            except OSError as exc:
                raise CoordinatorError(f"{label} parent close failed") from exc


def _parse_exact_json(payload: bytes, label: str) -> tuple[Any, bytes]:
    _require_private_context()
    try:
        value = json.loads(
            payload.decode("utf-8", "strict"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
        expected = canonical_bytes(value)
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise CoordinatorError(f"{label} is malformed JSON") from exc
    if payload != expected:
        raise CoordinatorError(f"{label} is non-canonical JSON")
    return value, payload


def _read_optional_json(path: Path, label: str) -> tuple[Any, bytes] | None:
    """Read an exact final, returning None only for an absent final/parent."""
    _require_private_context()
    kind = _managed_path(Path(path))
    if kind not in {"guard", "journal-final"}:
        raise CoordinatorError("optional JSON path is not a fixed final")
    parent = -1
    try:
        try:
            parent = _open_managed_directory(Path(path).parent)
        except CoordinatorError as exc:
            if isinstance(exc.__cause__, FileNotFoundError):
                return None
            raise
        try:
            payload = _read_bounded_at(
                parent,
                Path(path).name,
                label,
                allow_guard=kind == "guard",
            )
        except CoordinatorError as exc:
            if isinstance(exc.__cause__, FileNotFoundError):
                return None
            if "missing or indirect" in str(exc):
                # An absent final is the only missing state accepted here; a
                # present symlink/special node still fails closed.
                try:
                    os.stat(Path(path).name, dir_fd=parent, follow_symlinks=False)
                except FileNotFoundError:
                    return None
            raise
        return _parse_exact_json(payload, label)
    except FileNotFoundError:
        return None
    finally:
        if parent >= 0:
            try:
                os.close(parent)
            except OSError as exc:
                raise CoordinatorError(f"{label} parent close failed") from exc


def read_exact_json(path: Path, label: str = "journal node") -> tuple[Any, bytes]:
    _require_private_context()
    path = Path(path)
    kind = _managed_path(path)
    if kind not in {"guard", "journal-final"}:
        raise CoordinatorError("journal path is not a fixed final")
    parent = -1
    try:
        parent = _open_managed_directory(path.parent)
        return _parse_exact_json(
            _read_bounded_at(
                parent,
                path.name,
                label,
                allow_guard=kind == "guard",
            ),
            label,
        )
    finally:
        if parent >= 0:
            try:
                os.close(parent)
            except OSError as exc:
                raise CoordinatorError(f"{label} parent close failed") from exc


def read_json(path: Path, label: str = "journal node") -> Any:
    """Value-only compatibility view; callers cannot supply a raw predecessor."""
    _require_private_context()
    value, _ = read_exact_json(path, label)
    return value


def _ensure_private_dir(path: Path) -> None:
    """Create only fixed private directories through pinned dirfds."""
    _require_private_context()
    path = Path(path)
    kind = _managed_path(path)
    if kind not in {"run-root", "campaigns-root", "campaign", "session"}:
        raise CoordinatorError("private directory is outside the closed grammar")
    descriptor = _open_components(path, create=True)
    try:
        os.fsync(descriptor)
    except OSError as exc:
        raise CoordinatorError("fixed private directory fsync failed") from exc
    finally:
        os.close(descriptor)


def _link_tmpfile(descriptor: int, parent: int, name: str) -> None:
    _require_private_context()
    if not _allowed_final_name(name):
        raise CoordinatorError("journal final name is outside the closed grammar")
    if _LINKAT(
        descriptor,
        b"",
        parent,
        os.fsencode(name),
        AT_EMPTY_PATH,
    ) != 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number), name)


def atomic_publish(path: Path, payload: bytes, mode: int = 0o400) -> None:
    """Publish complete bytes under a final name, never replacing an inode."""
    _require_private_context()
    path = Path(path)
    if _managed_path(path) not in {"guard", "journal-final"}:
        raise CoordinatorError("journal publication path is not a fixed final")
    if not isinstance(payload, bytes) or len(payload) > MAX_JOURNAL_BYTES:
        raise CoordinatorError("journal payload is oversized or not bytes")
    _ensure_private_dir(path.parent)
    parent = _open_managed_directory(path.parent)
    descriptor = -1
    try:
        descriptor = os.open(
            ".",
            os.O_WRONLY | os.O_TMPFILE | os.O_CLOEXEC,
            mode,
            dir_fd=parent,
        )
        os.fchmod(descriptor, mode)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise CoordinatorError("journal write was short")
            offset += written
        os.fsync(descriptor)
        _link_tmpfile(descriptor, parent, path.name)
        os.fsync(parent)
    except FileExistsError as exc:
        raise CoordinatorError("journal final name already exists") from exc
    except OSError as exc:
        raise CoordinatorError("journal atomic publication failed") from exc
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError as exc:
                raise CoordinatorError("journal temporary close failed") from exc
        try:
            os.close(parent)
        except OSError as exc:
            raise CoordinatorError("journal parent close failed") from exc


def durable_json(path: Path, value: Any) -> None:
    _require_private_context()
    atomic_publish(Path(path), canonical_bytes(value))


def _require_hex(value: Any, label: str) -> str:
    if type(value) is not str or HEX64_RE.fullmatch(value) is None:
        raise CoordinatorError(f"{label} is not a lowercase SHA-256")
    return value


def _require_id(value: Any, label: str) -> str:
    if type(value) is not str or ID_RE.fullmatch(value) is None:
        raise CoordinatorError(f"{label} is not a fixed id")
    return value


def _require_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise CoordinatorError(f"{label} is not a bounded integer")
    return value


def _require_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise CoordinatorError(f"{label} is not a boolean")
    return value


def _exact_keys(value: Any, keys: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        raise CoordinatorError(f"{label} keys are not exact")


def _exact_equal(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and set(actual) == set(expected)
            and all(_exact_equal(actual[key], expected[key]) for key in expected)
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(_exact_equal(left, right) for left, right in zip(actual, expected))
        )
    return type(actual) is type(expected) and actual == expected


def validate_named_request(value: Any) -> str:
    _exact_keys(value, {"action"}, "research request")
    action = value["action"]
    if type(action) is not str or action not in ACTIONS:
        raise CoordinatorError("research action is not allowlisted")
    return action


def validate_identity(value: Any, label: str = "identity") -> dict[str, Any]:
    keys = {
        "target",
        "serial_sha256",
        "topology_sha256",
        "boot_id_sha256",
        "healthy_android",
        "foreign_guard_present",
    }
    _exact_keys(value, keys, label)
    if not _exact_equal(value["target"], TARGET):
        raise CoordinatorError(f"{label} target differs")
    for key in ("serial_sha256", "topology_sha256", "boot_id_sha256"):
        _require_hex(value[key], f"{label}.{key}")
    if value["healthy_android"] is not True:
        raise CoordinatorError(f"{label} is not healthy Android")
    if value["foreign_guard_present"] is not False:
        raise CoordinatorError(f"{label} has a foreign guard")
    return dict(value)


def validate_endpoint(value: Any, label: str = "endpoint") -> dict[str, str]:
    keys = {"path_sha256", "identity_sha256", "topology_sha256", "product"}
    _exact_keys(value, keys, label)
    result = {
        key: _require_hex(value[key], f"{label}.{key}")
        for key in ("path_sha256", "identity_sha256", "topology_sha256")
    }
    if type(value["product"]) is not str or value["product"] != "SM8250":
        raise CoordinatorError(f"{label}.product differs")
    if result["topology_sha256"] not in EXPECTED_DOWNLOAD_TOPOLOGY_SHA256:
        raise CoordinatorError(f"{label}.topology_sha256 is not allowlisted")
    result["product"] = value["product"]
    return result


def zero_counters() -> dict[str, int]:
    return {key: 0 for key in sorted(COUNTER_KEYS)}


def validate_counters(counters: Any, limits: dict[str, Any]) -> dict[str, int]:
    _exact_keys(counters, COUNTER_KEYS, "control counters")
    result = {
        key: _require_int(counters[key], f"counter.{key}") for key in COUNTER_KEYS
    }
    unresolved = result["roundtrip_entries"] - result["roundtrip_returns"]
    if (
        result["download_roundtrips"] != result["roundtrip_entries"]
        or unresolved not in (0, 1)
        or result["component_effects_reserved"] != unresolved
        or result["control_transactions"]
        != result["normal_reboots"] + result["download_roundtrips"]
        or result["component_effects_consumed"]
        != result["normal_reboots"]
        + result["roundtrip_entries"]
        + result["roundtrip_returns"]
    ):
        raise CoordinatorError("counter relationships are invalid")
    checks = {
        "control_transactions": "control_transactions_max",
        "normal_reboots": "normal_reboots_max",
        "download_roundtrips": "download_roundtrips_max",
    }
    total_effects = (
        result["component_effects_consumed"]
        + result["component_effects_reserved"]
    )
    if total_effects > limits["component_effects_max"] or any(
        result[key] > limits[maximum] for key, maximum in checks.items()
    ):
        raise CoordinatorError("control budget is exhausted")
    return result


def debit_before_intent(
    counters: Any, action: str, component: str, limits: dict[str, Any]
) -> dict[str, int]:
    result = validate_counters(counters, limits)
    if action == "reboot-system" and component == "reboot":
        if result["roundtrip_entries"] != result["roundtrip_returns"]:
            raise CoordinatorError("a Download roundtrip is unresolved")
        result["control_transactions"] += 1
        result["component_effects_consumed"] += 1
        result["normal_reboots"] += 1
    elif action == "download-roundtrip" and component == "entry":
        if result["roundtrip_entries"] != result["roundtrip_returns"]:
            raise CoordinatorError("a Download roundtrip is already unresolved")
        result["control_transactions"] += 1
        result["component_effects_consumed"] += 1
        result["component_effects_reserved"] += 1
        result["download_roundtrips"] += 1
        result["roundtrip_entries"] += 1
    elif action == "download-roundtrip" and component == "return":
        if (
            result["roundtrip_entries"] != result["roundtrip_returns"] + 1
            or result["component_effects_reserved"] != 1
        ):
            raise CoordinatorError("no unmatched Download entry exists")
        result["component_effects_reserved"] = 0
        result["component_effects_consumed"] += 1
        result["roundtrip_returns"] += 1
    else:
        raise CoordinatorError("control component is not allowlisted")
    return validate_counters(result, limits)


def _read_source(spec: dict[str, Any], label: str) -> bytes:
    path = Path(spec["path"])
    if type(spec["size"]) is not int or spec["size"] <= 0:
        raise CoordinatorError(f"{label} expected size is invalid")
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size != spec["size"]
        ):
            raise CoordinatorError(f"{label} source identity differs")
        data = bytearray()
        while len(data) < before.st_size:
            chunk = os.read(descriptor, min(1024 * 1024, before.st_size - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        if len(data) != before.st_size or os.read(descriptor, 1):
            raise CoordinatorError(f"{label} source length differs")
        after = os.fstat(descriptor)
        if _metadata(before) != _metadata(after):
            raise CoordinatorError(f"{label} source changed during read")
    except (OSError, TypeError) as exc:
        raise CoordinatorError(f"{label} source is unavailable") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    payload = bytes(data)
    if hashlib.sha256(payload).hexdigest() != spec["sha256"]:
        raise CoordinatorError(f"{label} source bytes changed")
    return payload


def read_exact_source(spec: dict[str, Any], label: str) -> dict[str, Any]:
    payload = _read_source(spec, label)
    return {
        "path": str(spec["path"]),
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def self_receipt() -> dict[str, Any]:
    path = Path(__file__).resolve()
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size > 2 * MAX_JOURNAL_BYTES
        ):
            raise CoordinatorError("coordinator source identity differs")
        data = bytearray()
        while len(data) < before.st_size:
            chunk = os.read(descriptor, min(1024 * 1024, before.st_size - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        if len(data) != before.st_size or os.read(descriptor, 1):
            raise CoordinatorError("coordinator source length differs")
        after = os.fstat(descriptor)
        if _metadata(before) != _metadata(after):
            raise CoordinatorError("coordinator source changed during read")
    except OSError as exc:
        raise CoordinatorError("coordinator source is unavailable") from exc
    finally:
        try:
            os.close(descriptor)
        except (UnboundLocalError, OSError):
            pass
    payload = bytes(data)
    normalized = re.sub(
        rb'EXPECTED_COORDINATOR_NORMALIZED_SHA256 = "[0-9a-f]{64}"',
        b'EXPECTED_COORDINATOR_NORMALIZED_SHA256 = "' + b"0" * 64 + b'"',
        payload,
        count=1,
    )
    normalized_sha256 = hashlib.sha256(normalized).hexdigest()
    if (
        EXPECTED_COORDINATOR_NORMALIZED_SHA256 != "0" * 64
        and normalized_sha256 != EXPECTED_COORDINATOR_NORMALIZED_SHA256
    ):
        raise CoordinatorError("coordinator normalized source identity differs")
    return {
        "path": str(path),
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "normalized_sha256": normalized_sha256,
    }


def source_receipts() -> dict[str, dict[str, Any]]:
    result = {"coordinator": self_receipt()}
    for label, spec in sorted(SOURCE_SPECS.items()):
        result[label] = read_exact_source(spec, label)
    return result


def binding_value() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "mechanically_activatable": MECHANICALLY_ACTIVATABLE,
        "live_action_integration": LIVE_ACTION_INTEGRATION,
        "live_integration_required": [
            "exact-empty-download-listing-producer",
            "exact-routine-d0-health-observer",
            "bounded-read-and-private-evidence-receipts",
            "fixed-reboot-and-return-backend",
            "child-session-lifecycle-and-reporting-cuts",
        ],
        "target": TARGET,
        "sources": source_receipts(),
        "actions": {
            "read_only": list(READ_ACTIONS),
            "control": list(CONTROL_ACTIONS),
            "pre_f1_terminal": "prepare-f1-readiness",
        },
        "limits": LIMITS,
        "campaign_limits": CAMPAIGN_LIMITS,
        "deferred_root_profiles": DEFERRED_ROOT_PROFILES,
        "root_profile_activation_requirements": ROOT_PROFILE_ACTIVATION_REQUIREMENTS,
        "live_coordinator_requirements": LIVE_COORDINATOR_REQUIREMENTS,
        "privacy": {
            "raw_output": "workspace/private/session-only",
            "public_output": "sanitized-hashes-and-conclusions-only",
            "caller_path": False,
            "caller_shell": False,
            "caller_callback": False,
        },
        "pre_f1_boundary": {
            "healthy_normal_android": True,
            "health_observation_required_after_reboot_or_return": True,
            "pending_health_blocks_control_and_terminal": True,
            "f1_intent": False,
            "download_entry_for_f1": False,
            "approval_consumed": False,
            "partition_transfer": False,
            "odin_payload": False,
        },
    }


def binding_digest() -> str:
    return digest(binding_value())


def _new_id() -> str:
    return secrets.token_hex(16)


def _now() -> int:
    return int(time.time())


def _base_node(
    *,
    kind: str,
    issued_at: int,
    campaign_id: str,
    session_id: str,
    ordinal: int,
    predecessor_sha256: str,
    source_identity: dict[str, Any],
    child_counters: dict[str, int],
    campaign_counters: dict[str, int],
    action: str,
    component: str,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "kind": kind,
        "issued_at": _require_int(issued_at, f"{kind}.issued_at"),
        "campaign_id": campaign_id,
        "session_id": session_id,
        "target": TARGET,
        "policy_binding_sha256": binding_digest(),
        "coordinator_normalized_sha256": self_receipt()["normalized_sha256"],
        "ordinal": ordinal,
        "predecessor_sha256": predecessor_sha256,
        "source_identity": validate_identity(source_identity, "source identity"),
        "child_counters": validate_counters(child_counters, LIMITS),
        "campaign_counters": validate_counters(campaign_counters, CAMPAIGN_LIMITS),
        "action": action,
        "component": component,
        "no_replay": True,
    }


def model_campaign_opening(identity: dict[str, Any], opened_at: int | None = None) -> dict[str, Any]:
    """Build a deterministic-shape opening model without publishing anything."""
    source_identity = validate_identity(identity, "opening identity")
    now = _now() if opened_at is None else _require_int(opened_at, "opened_at")
    campaign_id = _new_id()
    session_id = _new_id()
    campaign_counters = zero_counters()
    child_counters = zero_counters()
    opening = {
        "schema": SCHEMA,
        "kind": "campaign-opening",
        "campaign_id": campaign_id,
        "session_id": session_id,
        "target": TARGET,
        "policy_binding_sha256": binding_digest(),
        "coordinator_normalized_sha256": self_receipt()["normalized_sha256"],
        "source_identity": source_identity,
        "opened_at": now,
        "expires_at": now + CAMPAIGN_LIMITS["campaign_duration_sec"],
        "campaign_counters": campaign_counters,
        "child_counters": child_counters,
        "predecessor_sha256": ZERO_HASH,
        "attended_opening": True,
        "no_replay": True,
        "f1_intent": False,
        "approval_consumed": False,
        "partition_transfer": False,
    }
    opening_bytes = canonical_bytes(opening)
    session = {
        "schema": SCHEMA,
        "kind": "session-opening",
        "campaign_id": campaign_id,
        "session_id": session_id,
        "target": TARGET,
        "policy_binding_sha256": opening["policy_binding_sha256"],
        "coordinator_normalized_sha256": opening["coordinator_normalized_sha256"],
        "source_identity": source_identity,
        "opened_at": now,
        "expires_at": now + LIMITS["session_duration_sec"],
        "campaign_counters": campaign_counters,
        "child_counters": child_counters,
        "predecessor_sha256": hashlib.sha256(opening_bytes).hexdigest(),
        "no_replay": True,
    }
    session_bytes = canonical_bytes(session)
    guard = {
        "schema": SCHEMA,
        "kind": "campaign-guard",
        "phase": "allocation-claimed",
        "campaign_id": campaign_id,
        "session_id": session_id,
        "target": TARGET,
        "policy_binding_sha256": opening["policy_binding_sha256"],
        "coordinator_normalized_sha256": opening["coordinator_normalized_sha256"],
        "source_identity": source_identity,
        "opened_at": now,
        "expires_at": opening["expires_at"],
        "opening_sha256": hashlib.sha256(opening_bytes).hexdigest(),
        "session_opening_sha256": hashlib.sha256(session_bytes).hexdigest(),
        "opening": opening,
        "session": session,
        "campaign_counters": campaign_counters,
        "child_counters": child_counters,
        "no_replay": True,
        "f1_intent": False,
        "approval_consumed": False,
        "partition_transfer": False,
    }
    return {
        "campaign_id": campaign_id,
        "session_id": session_id,
        "opening": opening,
        "session": session,
        "guard": guard,
    }


def _validate_opening_model(model: Any) -> dict[str, Any]:
    if not isinstance(model, dict) or set(model) != {
        "campaign_id",
        "session_id",
        "opening",
        "session",
        "guard",
    }:
        raise CoordinatorError("campaign opening model shape differs")
    _require_id(model["campaign_id"], "model.campaign_id")
    _require_id(model["session_id"], "model.session_id")
    if model["opening"]["campaign_id"] != model["campaign_id"] or model["session"]["campaign_id"] != model["campaign_id"] or model["guard"]["campaign_id"] != model["campaign_id"]:
        raise CoordinatorError("campaign opening model campaign differs")
    if model["opening"]["session_id"] != model["session_id"] or model["session"]["session_id"] != model["session_id"] or model["guard"]["session_id"] != model["session_id"]:
        raise CoordinatorError("campaign opening model session differs")
    guard = _validate_guard(model["guard"])
    nodes = {
        "opening.json": (model["opening"], canonical_bytes(model["opening"])),
        "session-opening.json": (model["session"], canonical_bytes(model["session"])),
    }
    _validate_opening(nodes, guard)
    return model


def _directory_names(directory: Path, label: str) -> list[str]:
    """Enumerate one fixed directory through its already-pinned dirfd."""
    _require_private_context()
    descriptor = _open_managed_directory(Path(directory))
    try:
        before = os.fstat(descriptor)
        try:
            entries = list(os.scandir(descriptor))
        except OSError as exc:
            raise CoordinatorError(f"{label} namespace is unavailable") from exc
        after = os.fstat(descriptor)
        if _metadata(before) != _metadata(after):
            raise CoordinatorError(f"{label} directory changed during enumeration")
        names: list[str] = []
        for entry in entries:
            if entry.name in names:
                raise CoordinatorError(f"{label} namespace is duplicated")
            names.append(entry.name)
        return sorted(names)
    finally:
        try:
            os.close(descriptor)
        except OSError as exc:
            raise CoordinatorError(f"{label} namespace close failed") from exc


def _guard_model(guard: dict[str, Any]) -> dict[str, Any]:
    """Recover the exact allocation model embedded in an immutable guard."""
    _require_private_context()
    _validate_guard(guard)
    return {
        "campaign_id": guard["campaign_id"],
        "session_id": guard["session_id"],
        "opening": guard["opening"],
        "session": guard["session"],
        "guard": guard,
    }


def _complete_guarded_opening(model: dict[str, Any]) -> bool:
    """Complete only the exact missing nodes owned by the current guard."""
    _require_private_context()
    model = _validate_opening_model(model)
    _ensure_private_dir(PRIVATE_RUN_ROOT)
    _ensure_private_dir(CAMPAIGNS_ROOT)
    session_dir = _session_dir(model["campaign_id"])
    _require_exact_namespace(
        PRIVATE_RUN_ROOT,
        {"active-campaign.json", "campaigns"},
        "private run root",
    )
    campaign_names = _directory_names(CAMPAIGNS_ROOT, "campaign root")
    if campaign_names and campaign_names != [model["campaign_id"]]:
        raise CoordinatorError("guarded opening campaign namespace is foreign")
    if not campaign_names:
        _ensure_private_dir(_campaign_dir(model["campaign_id"]))
    _require_exact_namespace(
        CAMPAIGNS_ROOT,
        {model["campaign_id"]},
        "campaign root",
    )
    campaign_names = _directory_names(
        _campaign_dir(model["campaign_id"]), "campaign"
    )
    if campaign_names and campaign_names != ["session"]:
        raise CoordinatorError("guarded opening campaign contains a foreign entry")
    if not campaign_names:
        _ensure_private_dir(session_dir)
    _require_exact_namespace(
        _campaign_dir(model["campaign_id"]),
        {"session"},
        "campaign",
    )
    expected = {
        "opening.json": model["opening"],
        "session-opening.json": model["session"],
    }
    names = _directory_names(session_dir, "session")
    if any(name not in expected for name in names):
        raise CoordinatorError("guarded opening contains a foreign node")
    completed = True
    for name, value in expected.items():
        path = session_dir / name
        existing = _read_optional_json(path, name)
        if existing is None:
            durable_json(path, value)
            completed = False
        elif existing != (value, canonical_bytes(value)):
            raise CoordinatorError("guarded opening node differs from immutable guard")
    return completed


def reconcile_opening_cut() -> dict[str, Any]:
    """Complete an exact guard-owned opening; never delete guardless files."""
    _require_private_context()
    try:
        guard_result = _read_optional_json(CAMPAIGN_GUARD_PATH, "campaign guard")
    except CoordinatorError as exc:
        if isinstance(exc.__cause__, FileNotFoundError):
            return {
                "reconciled": False,
                "reason": "no guard; guardless files retained",
                "authority": False,
                "guard_present": False,
            }
        raise
    if guard_result is None:
        return {
            "reconciled": False,
            "reason": "no guard; guardless files retained",
            "authority": False,
            "guard_present": False,
        }
    guard, _ = guard_result
    completed = _complete_guarded_opening(_guard_model(guard))
    return {
        "reconciled": not completed,
        "authority": False,
        "guard_present": True,
        "phase": guard["phase"],
    }


def publish_campaign_opening(model: dict[str, Any]) -> dict[str, Any]:
    """Host-only guard-first opening with immutable no-clobber completion."""
    _require_private_context()
    model = _validate_opening_model(model)
    _ensure_private_dir(PRIVATE_RUN_ROOT)
    names = _directory_names(PRIVATE_RUN_ROOT, "private run root")
    if any(name not in {"active-campaign.json", "campaigns"} for name in names):
        raise CoordinatorError("private run root contains a foreign guardless entry")
    _ensure_private_dir(CAMPAIGNS_ROOT)
    existing_guard = _read_optional_json(CAMPAIGN_GUARD_PATH, "campaign guard")
    if existing_guard is not None:
        guard, _ = existing_guard
        if guard != model["guard"]:
            raise CoordinatorError("concurrent opening guard differs")
        complete = _complete_guarded_opening(_guard_model(guard))
        if complete:
            raise CoordinatorError("current immutable guard already owns opening")
        return {
            "published": True,
            "guard_present": True,
            "campaign_id": guard["campaign_id"],
            "session_id": guard["session_id"],
            "authority": False,
            "recovered": True,
        }
    _require_exact_namespace(PRIVATE_RUN_ROOT, {"campaigns"}, "private run root")
    _require_exact_namespace(CAMPAIGNS_ROOT, set(), "campaign root")
    # The immutable allocation guard is the first final publication.  Any
    # write/link/fsync cut after this point leaves the guard for exact recovery.
    durable_json(CAMPAIGN_GUARD_PATH, model["guard"])
    _complete_guarded_opening(model)
    return {
        "published": True,
        "guard_present": True,
        "campaign_id": model["campaign_id"],
        "session_id": model["session_id"],
        "authority": False,
    }


def _context_identity(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        raise CoordinatorError("current context is not an object")
    for key in (
        "campaign_id",
        "session_id",
        "source_identity",
        "predecessor_sha256",
        "child_counters",
        "campaign_counters",
        "current_time",
        "campaign_expires_at",
        "session_expires_at",
        "expired",
        "session_expired",
        "pending_intent_issued_at",
    ):
        if key not in context:
            raise CoordinatorError("current context is incomplete")
    _require_id(context["campaign_id"], "context.campaign_id")
    _require_id(context["session_id"], "context.session_id")
    validate_identity(context["source_identity"], "context.source_identity")
    _require_hex(context["predecessor_sha256"], "context.predecessor_sha256")
    validate_counters(context["child_counters"], LIMITS)
    validate_counters(context["campaign_counters"], CAMPAIGN_LIMITS)
    current_time = _require_int(context["current_time"], "context.current_time")
    campaign_expires_at = _require_int(
        context["campaign_expires_at"], "context.campaign_expires_at"
    )
    session_expires_at = _require_int(
        context["session_expires_at"], "context.session_expires_at"
    )
    if session_expires_at > campaign_expires_at:
        raise CoordinatorError("context session expiry exceeds campaign expiry")
    if context["expired"] is not (current_time >= campaign_expires_at):
        raise CoordinatorError("context campaign expiry is not current")
    if context["session_expired"] is not (current_time >= session_expires_at):
        raise CoordinatorError("context session expiry is not current")
    if context["pending_intent_issued_at"] is not None:
        _require_int(
            context["pending_intent_issued_at"],
            "context.pending_intent_issued_at",
        )
        if context["pending_intent_issued_at"] > current_time:
            raise CoordinatorError("context pending intent is from the future")
    return context["source_identity"]


_CONTEXT_BINDING_KEYS = (
    "campaign_id",
    "session_id",
    "phase",
    "expired",
    "session_expired",
    "current_time",
    "campaign_expires_at",
    "session_expires_at",
    "current_ordinal",
    "source_identity",
    "endpoint",
    "predecessor_sha256",
    "child_counters",
    "campaign_counters",
    "terminal",
    "f1_intent",
    "approval_consumed",
    "partition_transfer",
    "no_replay",
    "pending_intent_issued_at",
)


def _validated_context(context: dict[str, Any]) -> dict[str, Any]:
    """Re-derive model input from the current journal at its typed timestamp."""
    if not isinstance(context, dict) or type(context.get("current_time")) is not int:
        raise CoordinatorError("model context must carry a validated current time")
    actual_now = _require_int(_now(), "actual current time")
    fresh = validate_chain(now=actual_now)
    for key in _CONTEXT_BINDING_KEYS:
        if key not in context or key not in fresh or not _exact_equal(
            context[key], fresh[key]
        ):
            raise CoordinatorError("model context is stale or caller-derived")
    if context["current_time"] != actual_now:
        raise CoordinatorError("model context timestamp is stale or backdated")
    _context_identity(fresh)
    return fresh


def _context_issued_at(
    context: dict[str, Any], *, continuation: bool = False
) -> int:
    _context_identity(context)
    if not continuation and (
        context["expired"] or context["session_expired"]
    ):
        raise CoordinatorError("new node cannot be issued after expiry")
    pending = context["pending_intent_issued_at"]
    if continuation:
        if pending is None:
            raise CoordinatorError("continuation has no pending intent")
        if context["phase"] == "reboot-health-pending" and (
            pending >= context["campaign_expires_at"]
            or pending >= context["session_expires_at"]
        ):
            raise CoordinatorError("reboot intent was issued after expiry")
    return context["current_time"]


def model_baseline_node(context: dict[str, Any]) -> dict[str, Any]:
    """Build the exact empty Download listing receipt for the next ordinal."""
    return _model_baseline_node_validated(_validated_context(context))


def _model_baseline_node_validated(context: dict[str, Any]) -> dict[str, Any]:
    source_identity = _context_identity(context)
    issued_at = _context_issued_at(context)
    if context.get("phase") != "healthy-normal":
        raise CoordinatorError("Download baseline requires healthy normal Android")
    if context.get("endpoint") is not None:
        raise CoordinatorError("Download baseline cannot reuse an endpoint")
    ordinal = context["campaign_counters"]["download_roundtrips"] + 1
    node = _base_node(
        kind="baseline",
        issued_at=issued_at,
        campaign_id=context["campaign_id"],
        session_id=context["session_id"],
        ordinal=ordinal,
        predecessor_sha256=context["predecessor_sha256"],
        source_identity=source_identity,
        child_counters=context["child_counters"],
        campaign_counters=context["campaign_counters"],
        action="download-roundtrip",
        component="baseline",
    )
    node["baseline"] = {
        "endpoint_count": 0,
        "listing_sha256": EMPTY_DOWNLOAD_LISTING_SHA256,
        "listing_grammar": EMPTY_DOWNLOAD_LISTING_GRAMMAR,
    }
    return node


def _model_entry_node_validated(
    context: dict[str, Any], action: str = "download-roundtrip"
) -> dict[str, Any]:
    """Build one intent node from a previously validated current context.

    This is an offline fixture builder.  It does not publish a node, contact a
    device, or create authority; validation of a persisted node still derives
    all fields from the current fixed guard and predecessor chain.
    """
    source_identity = _context_identity(context)
    issued_at = _context_issued_at(context)
    if type(action) is not str or action not in CONTROL_ACTIONS:
        raise CoordinatorError("entry action is not allowlisted")
    if action == "download-roundtrip":
        if context.get("phase") != "download-baseline-ready":
            raise CoordinatorError("Download entry requires an exact fresh baseline")
        if context.get("_paired_baseline") is not True:
            raise CoordinatorError("baseline-only state cannot authorize a later entry")
        baseline_sha256 = _require_hex(
            context.get("baseline_sha256"), "baseline predecessor"
        )
        child = debit_before_intent(
            context["child_counters"], action, "entry", LIMITS
        )
        campaign = debit_before_intent(
            context["campaign_counters"], action, "entry", CAMPAIGN_LIMITS
        )
        ordinal = campaign["download_roundtrips"]
        component = "entry"
        kind = "entry"
    else:
        if context.get("phase") != "healthy-normal":
            raise CoordinatorError("reboot requires healthy normal Android")
        child = debit_before_intent(
            context["child_counters"], action, "reboot", LIMITS
        )
        campaign = debit_before_intent(
            context["campaign_counters"], action, "reboot", CAMPAIGN_LIMITS
        )
        ordinal = campaign["normal_reboots"]
        component = "reboot"
        kind = "reboot"
    node = _base_node(
        kind=kind,
        issued_at=issued_at,
        campaign_id=context["campaign_id"],
        session_id=context["session_id"],
        ordinal=ordinal,
        predecessor_sha256=context["predecessor_sha256"],
        source_identity=source_identity,
        child_counters=child,
        campaign_counters=campaign,
        action=action,
        component=component,
    )
    if action == "download-roundtrip":
        node["baseline_sha256"] = baseline_sha256
    return node


def model_entry_node(
    context: dict[str, Any], action: str = "download-roundtrip"
) -> dict[str, Any]:
    return _model_entry_node_validated(_validated_context(context), action)


def model_roundtrip_pair(context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build baseline and its immediately bound entry as one host-only pair."""
    context = _validated_context(context)
    baseline = _model_baseline_node_validated(context)
    baseline_context = dict(context)
    baseline_context["phase"] = "download-baseline-ready"
    baseline_context["_paired_baseline"] = True
    baseline_context["baseline_sha256"] = hashlib.sha256(
        canonical_bytes(baseline)
    ).hexdigest()
    baseline_context["predecessor_sha256"] = baseline_context["baseline_sha256"]
    return baseline, _model_entry_node_validated(baseline_context)


def model_arrival_node(
    context: dict[str, Any], endpoint: dict[str, Any]
) -> dict[str, Any]:
    context = _validated_context(context)
    source_identity = _context_identity(context)
    issued_at = _context_issued_at(context, continuation=True)
    if context.get("phase") != "download-entry-pending":
        raise CoordinatorError("arrival requires one unmatched entry")
    validated_endpoint = validate_endpoint(endpoint, "arrival endpoint")
    ordinal = context["campaign_counters"]["download_roundtrips"]
    node = _base_node(
        kind="arrival",
        issued_at=issued_at,
        campaign_id=context["campaign_id"],
        session_id=context["session_id"],
        ordinal=ordinal,
        predecessor_sha256=context["predecessor_sha256"],
        source_identity=source_identity,
        child_counters=context["child_counters"],
        campaign_counters=context["campaign_counters"],
        action="download-roundtrip",
        component="arrival",
    )
    node["endpoint"] = validated_endpoint
    return node


def model_return_node(context: dict[str, Any]) -> dict[str, Any]:
    context = _validated_context(context)
    source_identity = _context_identity(context)
    issued_at = _context_issued_at(context, continuation=True)
    if context.get("phase") != "download-return-ready":
        raise CoordinatorError("return requires one validated arrival")
    endpoint = context.get("endpoint")
    validated_endpoint = validate_endpoint(endpoint, "validated arrival endpoint")
    child = debit_before_intent(
        context["child_counters"], "download-roundtrip", "return", LIMITS
    )
    campaign = debit_before_intent(
        context["campaign_counters"], "download-roundtrip", "return", CAMPAIGN_LIMITS
    )
    node = _base_node(
        kind="return",
        issued_at=issued_at,
        campaign_id=context["campaign_id"],
        session_id=context["session_id"],
        ordinal=campaign["download_roundtrips"],
        predecessor_sha256=context["predecessor_sha256"],
        source_identity=source_identity,
        child_counters=child,
        campaign_counters=campaign,
        action="download-roundtrip",
        component="return",
    )
    node["endpoint"] = validated_endpoint
    return node


def model_health_node(
    context: dict[str, Any], observation: dict[str, Any]
) -> dict[str, Any]:
    """Build one strict post-effect healthy-Android observation node."""
    context = _validated_context(context)
    intent_source = _context_identity(context)
    issued_at = _context_issued_at(context, continuation=True)
    if context.get("phase") == "reboot-health-pending":
        action = "reboot-system"
        ordinal = context["campaign_counters"]["normal_reboots"]
        expected_observation = "reboot"
    elif context.get("phase") == "return-health-pending":
        action = "download-roundtrip"
        ordinal = context["campaign_counters"]["download_roundtrips"]
        expected_observation = "return"
    else:
        raise CoordinatorError("health observation has no pending effect")
    observed = validate_identity(observation, "health observation")
    if observed["target"] != intent_source["target"]:
        raise CoordinatorError("health observation target differs from intent")
    if (
        observed["serial_sha256"] != intent_source["serial_sha256"]
        or observed["topology_sha256"] != intent_source["topology_sha256"]
    ):
        raise CoordinatorError("health observation endpoint differs from intent")
    if observed["boot_id_sha256"] == intent_source["boot_id_sha256"]:
        raise CoordinatorError("health observation reused the effect source boot")
    node = _base_node(
        kind="health",
        issued_at=issued_at,
        campaign_id=context["campaign_id"],
        session_id=context["session_id"],
        ordinal=ordinal,
        predecessor_sha256=context["predecessor_sha256"],
        source_identity=observed,
        child_counters=context["child_counters"],
        campaign_counters=context["campaign_counters"],
        action=action,
        component="health",
    )
    node.update(
        {
            "intent_source_identity": intent_source,
            "observation_for": expected_observation,
            "healthy_android": True,
        }
    )
    return node


def model_reboot_health_node(
    context: dict[str, Any], observation: dict[str, Any]
) -> dict[str, Any]:
    if context.get("phase") != "reboot-health-pending":
        raise CoordinatorError("reboot health has no pending reboot")
    return model_health_node(context, observation)


def model_return_health_node(
    context: dict[str, Any], observation: dict[str, Any]
) -> dict[str, Any]:
    if context.get("phase") != "return-health-pending":
        raise CoordinatorError("return health has no pending return")
    return model_health_node(context, observation)


def model_terminal_node(context: dict[str, Any]) -> dict[str, Any]:
    context = _validated_context(context)
    source_identity = _context_identity(context)
    issued_at = _context_issued_at(context)
    if context.get("phase") != "healthy-normal" or context.get("endpoint") is not None:
        raise CoordinatorError("pre-F1 readiness requires resolved healthy Android")
    node = _base_node(
        kind="terminal",
        issued_at=issued_at,
        campaign_id=context["campaign_id"],
        session_id=context["session_id"],
        ordinal=context["campaign_counters"]["download_roundtrips"],
        predecessor_sha256=context["predecessor_sha256"],
        source_identity=source_identity,
        child_counters=context["child_counters"],
        campaign_counters=context["campaign_counters"],
        action="prepare-f1-readiness",
        component="terminal",
    )
    node.update(
        {
            "verdict": "READY_FOR_ATTENDED_F1",
            "healthy_normal_android": True,
            "f1_intent": False,
            "approval_consumed": False,
            "partition_transfer": False,
            "odin_payload": False,
        }
    )
    return node


def _campaign_dir(campaign_id: str) -> Path:
    _require_private_context()
    _require_id(campaign_id, "campaign id")
    return CAMPAIGNS_ROOT / campaign_id


def _session_dir(campaign_id: str) -> Path:
    _require_private_context()
    return _campaign_dir(campaign_id) / "session"


def _assert_dormant() -> None:
    if (
        COORDINATOR_ACTIVE is not True
        or LIVE_AUTHORITY is not True
        or MECHANICALLY_ACTIVATABLE is not True
        or LIVE_ACTION_INTEGRATION is not True
    ):
        raise CoordinatorError(
            "autonomous journal candidate is dormant; live action integration is absent"
        )


class Coordinator:
    """Fixed-root journal surface; no live action integration is exposed."""

    def open_campaign(self, identity: Any = None) -> None:
        _assert_dormant()
        # This line is unreachable while the candidate is H0.  Keeping the
        # implementation absent is intentional: no live opening CLI exists.
        raise CoordinatorError("campaign opening is not exposed by this candidate")

    def begin_named_action(self, request: Any = None) -> None:
        _assert_dormant()
        raise CoordinatorError("named action dispatch is not exposed by this candidate")

    def begin_entry(self, request: Any = None) -> None:
        _assert_dormant()
        raise CoordinatorError("entry dispatch is not exposed by this candidate")

    def record_arrival(self, observation: Any = None) -> None:
        _assert_dormant()
        raise CoordinatorError("arrival dispatch is not exposed by this candidate")

    def begin_return(self, request: Any = None) -> None:
        _assert_dormant()
        raise CoordinatorError("return dispatch is not exposed by this candidate")

    def prepare_f1_readiness(self, request: Any = None) -> None:
        _assert_dormant()
        raise CoordinatorError("pre-F1 readiness is not exposed by this candidate")


def _validate_common_node(node: Any, kind: str) -> None:
    required = {
        "schema",
        "kind",
        "issued_at",
        "campaign_id",
        "session_id",
        "target",
        "policy_binding_sha256",
        "coordinator_normalized_sha256",
        "ordinal",
        "predecessor_sha256",
        "source_identity",
        "child_counters",
        "campaign_counters",
        "action",
        "component",
        "no_replay",
    }
    _exact_keys(node, required, kind)
    if node["schema"] != SCHEMA or node["kind"] != kind:
        raise CoordinatorError(f"{kind} schema differs")
    _require_id(node["campaign_id"], f"{kind}.campaign_id")
    _require_id(node["session_id"], f"{kind}.session_id")
    _require_int(node["issued_at"], f"{kind}.issued_at")
    if not _exact_equal(node["target"], TARGET):
        raise CoordinatorError(f"{kind}.target differs")
    _require_hex(node["policy_binding_sha256"], f"{kind}.policy_binding_sha256")
    _require_hex(
        node["coordinator_normalized_sha256"],
        f"{kind}.coordinator_normalized_sha256",
    )
    ordinal = _require_int(node["ordinal"], f"{kind}.ordinal")
    if ordinal > MAX_ORDINAL:
        raise CoordinatorError(f"{kind}.ordinal exceeds bound")
    _require_hex(node["predecessor_sha256"], f"{kind}.predecessor_sha256")
    validate_identity(node["source_identity"], f"{kind}.source_identity")
    validate_counters(node["child_counters"], LIMITS)
    validate_counters(node["campaign_counters"], CAMPAIGN_LIMITS)
    if type(node["action"]) is not str or node["action"] not in ACTIONS:
        raise CoordinatorError(f"{kind}.action is not allowlisted")
    if type(node["component"]) is not str:
        raise CoordinatorError(f"{kind}.component is malformed")
    if node["no_replay"] is not True:
        raise CoordinatorError(f"{kind} permits replay")


def _validate_guard(guard: Any) -> dict[str, Any]:
    keys = {
        "schema",
        "kind",
        "phase",
        "campaign_id",
        "session_id",
        "target",
        "policy_binding_sha256",
        "coordinator_normalized_sha256",
        "source_identity",
        "opened_at",
        "expires_at",
        "opening_sha256",
        "session_opening_sha256",
        "opening",
        "session",
        "campaign_counters",
        "child_counters",
        "no_replay",
        "f1_intent",
        "approval_consumed",
        "partition_transfer",
    }
    _exact_keys(guard, keys, "campaign guard")
    if (
        guard["schema"] != SCHEMA
        or guard["kind"] != "campaign-guard"
        or guard["phase"] != "allocation-claimed"
    ):
        raise CoordinatorError("campaign guard schema differs")
    _require_id(guard["campaign_id"], "guard.campaign_id")
    _require_id(guard["session_id"], "guard.session_id")
    if not _exact_equal(guard["target"], TARGET):
        raise CoordinatorError("guard target differs")
    _require_hex(guard["policy_binding_sha256"], "guard.policy_binding_sha256")
    _require_hex(
        guard["coordinator_normalized_sha256"],
        "guard.coordinator_normalized_sha256",
    )
    validate_identity(guard["source_identity"], "guard.source_identity")
    if guard["policy_binding_sha256"] != binding_digest():
        raise CoordinatorError("guard policy/source binding is stale or foreign")
    if guard["coordinator_normalized_sha256"] != self_receipt()["normalized_sha256"]:
        raise CoordinatorError("guard coordinator source binding is stale or foreign")
    opened = _require_int(guard["opened_at"], "guard.opened_at")
    expires = _require_int(guard["expires_at"], "guard.expires_at")
    if expires <= opened:
        raise CoordinatorError("guard expiry is not after opening")
    _require_hex(guard["opening_sha256"], "guard.opening_sha256")
    _require_hex(guard["session_opening_sha256"], "guard.session_opening_sha256")
    if not isinstance(guard["opening"], dict) or not isinstance(guard["session"], dict):
        raise CoordinatorError("guard allocation values are not objects")
    opening = guard["opening"]
    session = guard["session"]
    if (
        opening.get("campaign_id") != guard["campaign_id"]
        or opening.get("session_id") != guard["session_id"]
        or session.get("campaign_id") != guard["campaign_id"]
        or session.get("session_id") != guard["session_id"]
    ):
        raise CoordinatorError("guard allocation identity differs")
    opening_bytes = canonical_bytes(opening)
    session_bytes = canonical_bytes(session)
    if (
        _hash_payload(opening_bytes) != guard["opening_sha256"]
        or _hash_payload(session_bytes) != guard["session_opening_sha256"]
    ):
        raise CoordinatorError("guard allocation digests differ")
    validate_counters(guard["campaign_counters"], CAMPAIGN_LIMITS)
    validate_counters(guard["child_counters"], LIMITS)
    if guard["campaign_counters"] != zero_counters() or guard["child_counters"] != zero_counters():
        raise CoordinatorError("guard counters are not fresh")
    if guard["no_replay"] is not True:
        raise CoordinatorError("guard permits replay")
    for key in ("f1_intent", "approval_consumed", "partition_transfer"):
        if guard[key] is not False:
            raise CoordinatorError("guard crosses the pre-F1 boundary")
    _validate_opening(
        {
            "opening.json": (opening, opening_bytes),
            "session-opening.json": (session, session_bytes),
        },
        guard,
    )
    return guard


def _allowed_node_names() -> set[str]:
    _require_private_context()
    return {"opening.json", "session-opening.json", "terminal.json"}


def _scan_nodes(directory: Path) -> dict[str, tuple[Any, bytes]]:
    _require_private_context()
    directory = Path(directory)
    if _managed_path(directory) != "session":
        raise CoordinatorError("journal scan requires a fixed session directory")
    descriptor = -1
    try:
        descriptor = _open_managed_directory(directory)
        before_directory = os.fstat(descriptor)
        entries = list(os.scandir(descriptor))
        after_directory = os.fstat(descriptor)
        if _metadata(before_directory) != _metadata(after_directory):
            raise CoordinatorError("journal directory changed during enumeration")
    except OSError as exc:
        raise CoordinatorError("campaign run root is unavailable") from exc
    try:
        result: dict[str, tuple[Any, bytes]] = {}
        for entry in entries:
            name = entry.name
            if not _allowed_final_name(name):
                raise CoordinatorError(
                    "journal namespace contains an unknown or partial node"
                )
            if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                raise CoordinatorError("journal namespace contains an indirect node")
            result[name] = _parse_exact_json(
                _read_bounded_at(descriptor, name, name),
                name,
            )
        return result
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError as exc:
                raise CoordinatorError("journal directory close failed") from exc


def _require_exact_namespace(
    directory: Path, allowed_names: set[str], label: str
) -> None:
    """Reject foreign guards/campaigns and any unowned namespace entry."""
    _require_private_context()
    directory = Path(directory)
    kind = _managed_path(directory)
    if kind not in {"run-root", "campaigns-root", "campaign", "session"}:
        raise CoordinatorError(f"{label} is not a fixed directory")
    checked = _open_managed_directory(directory)
    try:
        before_directory = os.fstat(checked)
        try:
            entries = list(os.scandir(checked))
        except OSError as exc:
            raise CoordinatorError(f"{label} namespace is unavailable") from exc
        after_directory = os.fstat(checked)
        if _metadata(before_directory) != _metadata(after_directory):
            raise CoordinatorError(f"{label} directory changed during enumeration")
        names: set[str] = set()
        for entry in entries:
            if entry.is_symlink() or entry.name in names:
                raise CoordinatorError(f"{label} namespace is indirect or duplicated")
            names.add(entry.name)
            if entry.name not in allowed_names:
                raise CoordinatorError(f"{label} namespace contains a foreign entry")
        if names != allowed_names:
            raise CoordinatorError(f"{label} namespace is incomplete")
    finally:
        try:
            os.close(checked)
        except OSError as exc:
            raise CoordinatorError(f"{label} namespace close failed") from exc


def _hash_payload(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _same_identity(left: Any, right: Any) -> bool:
    return _exact_equal(left, right)


_UNSET_SOURCE = object()


def _check_binding(
    node: Any,
    guard: dict[str, Any],
    kind: str,
    expected_source: dict[str, Any] | None | object = _UNSET_SOURCE,
) -> None:
    common_keys = {
        "schema",
        "kind",
        "issued_at",
        "campaign_id",
        "session_id",
        "target",
        "policy_binding_sha256",
        "coordinator_normalized_sha256",
        "ordinal",
        "predecessor_sha256",
        "source_identity",
        "child_counters",
        "campaign_counters",
        "action",
        "component",
        "no_replay",
    }
    if not common_keys.issubset(node):
        _validate_common_node(node, kind)
    else:
        _validate_common_node({key: node[key] for key in common_keys}, kind)
    _check_binding_identity(node, guard, kind, expected_source)


def _check_binding_identity(
    node: Any,
    guard: dict[str, Any],
    kind: str,
    expected_source: dict[str, Any] | None | object = _UNSET_SOURCE,
) -> None:
    if node.get("schema") != SCHEMA:
        raise CoordinatorError(f"{kind} schema differs")
    if node.get("target") != TARGET:
        raise CoordinatorError(f"{kind} target differs")
    _require_id(node.get("campaign_id"), f"{kind}.campaign_id")
    _require_id(node.get("session_id"), f"{kind}.session_id")
    for key in ("campaign_id", "session_id", "policy_binding_sha256", "coordinator_normalized_sha256"):
        expected = {
            "campaign_id": guard["campaign_id"],
            "session_id": guard["session_id"],
            "policy_binding_sha256": guard["policy_binding_sha256"],
            "coordinator_normalized_sha256": guard["coordinator_normalized_sha256"],
        }[key]
        if node.get(key) != expected:
            raise CoordinatorError(f"{kind} is foreign to the current guard")
    _require_hex(node.get("policy_binding_sha256"), f"{kind}.policy_binding_sha256")
    _require_hex(node.get("coordinator_normalized_sha256"), f"{kind}.coordinator_normalized_sha256")
    if expected_source is _UNSET_SOURCE:
        expected_source = guard["source_identity"]
    if expected_source is not None and not _same_identity(
        node.get("source_identity"), expected_source
    ):
        raise CoordinatorError(f"{kind} source identity differs")


def _validate_opening(nodes: dict[str, tuple[Any, bytes]], guard: dict[str, Any]) -> str:
    if "opening.json" not in nodes or "session-opening.json" not in nodes:
        raise CoordinatorError("opening chain is incomplete")
    opening, opening_bytes = nodes["opening.json"]
    session, session_bytes = nodes["session-opening.json"]
    if _hash_payload(opening_bytes) != guard["opening_sha256"]:
        raise CoordinatorError("opening predecessor bytes differ")
    if _hash_payload(session_bytes) != guard["session_opening_sha256"]:
        raise CoordinatorError("session predecessor bytes differ")
    _exact_keys(
        opening,
        {
            "schema",
            "kind",
            "campaign_id",
            "session_id",
            "target",
            "policy_binding_sha256",
            "coordinator_normalized_sha256",
            "source_identity",
            "opened_at",
            "expires_at",
            "campaign_counters",
            "child_counters",
            "predecessor_sha256",
            "attended_opening",
            "no_replay",
            "f1_intent",
            "approval_consumed",
            "partition_transfer",
        },
        "campaign opening",
    )
    if opening["schema"] != SCHEMA or opening["kind"] != "campaign-opening":
        raise CoordinatorError("campaign opening schema differs")
    _check_binding_identity(opening, guard, "campaign opening")
    if opening["predecessor_sha256"] != ZERO_HASH or opening["attended_opening"] is not True:
        raise CoordinatorError("opening is not fresh attended allocation")
    if opening["expires_at"] != guard["expires_at"] or opening["opened_at"] != guard["opened_at"]:
        raise CoordinatorError("opening time differs from current guard")
    if opening["campaign_counters"] != zero_counters() or opening["child_counters"] != zero_counters():
        raise CoordinatorError("opening counters are not zero")
    for key in ("f1_intent", "approval_consumed", "partition_transfer"):
        if opening[key] is not False:
            raise CoordinatorError("opening crosses the pre-F1 boundary")
    _exact_keys(
        session,
        {
            "schema",
            "kind",
            "campaign_id",
            "session_id",
            "target",
            "policy_binding_sha256",
            "coordinator_normalized_sha256",
            "source_identity",
            "opened_at",
            "expires_at",
            "campaign_counters",
            "child_counters",
            "predecessor_sha256",
            "no_replay",
        },
        "session opening",
    )
    _check_binding_identity(session, guard, "session opening")
    if session["kind"] != "session-opening" or session["predecessor_sha256"] != guard["opening_sha256"]:
        raise CoordinatorError("session does not immediately follow opening")
    if session["campaign_counters"] != zero_counters() or session["child_counters"] != zero_counters():
        raise CoordinatorError("session opening counters are not zero")
    if session["expires_at"] > guard["expires_at"]:
        raise CoordinatorError("session expiry exceeds campaign expiry")
    return _hash_payload(session_bytes)


def _validate_node_time(
    node: dict[str, Any],
    kind: str,
    *,
    current_time: int,
    campaign_expires_at: int,
    session_expires_at: int,
    predecessor_issued_at: int,
    preexpiry_required: bool,
) -> int:
    issued_at = _require_int(node["issued_at"], f"{kind}.issued_at")
    if issued_at < predecessor_issued_at:
        raise CoordinatorError(f"{kind}.issued_at is not monotonic")
    if issued_at > current_time:
        raise CoordinatorError(f"{kind}.issued_at is from the future")
    if preexpiry_required and (
        issued_at >= campaign_expires_at or issued_at >= session_expires_at
    ):
        raise CoordinatorError(f"{kind} was issued after expiry")
    return issued_at


def validate_chain(now: int | None = None) -> dict[str, Any]:
    """Read and validate the complete current fixed-root chain.

    This is intentionally read-only.  It derives the current ordinal, source,
    endpoint and predecessor from the current guard and actual validated node
    bytes; callers cannot provide any of those values.
    """
    _require_private_context()
    current_time = _now() if now is None else _require_int(now, "current time")
    guard, _ = read_exact_json(CAMPAIGN_GUARD_PATH, "campaign guard")
    guard = _validate_guard(guard)
    _require_exact_namespace(
        PRIVATE_RUN_ROOT,
        {"active-campaign.json", "campaigns"},
        "private run root",
    )
    _require_exact_namespace(CAMPAIGNS_ROOT, {guard["campaign_id"]}, "campaign root")
    campaign_dir = _campaign_dir(guard["campaign_id"])
    session_dir = _session_dir(guard["campaign_id"])
    _require_exact_namespace(campaign_dir, {"session"}, "campaign")
    session_descriptor = _open_managed_directory(session_dir)
    os.close(session_descriptor)
    nodes = _scan_nodes(session_dir)
    head = _validate_opening(nodes, guard)
    session_expires_at = _require_int(
        nodes["session-opening.json"][0]["expires_at"],
        "session opening expiry",
    )
    previous_issued_at = _require_int(
        nodes["session-opening.json"][0]["opened_at"],
        "session opening timestamp",
    )
    current_child = zero_counters()
    current_campaign = zero_counters()
    current_source = guard["source_identity"]
    seen_boot_ids = {current_source["boot_id_sha256"]}
    previous_hash = head
    unresolved: dict[str, Any] | None = None
    arrival: dict[str, Any] | None = None
    baseline: dict[str, Any] | None = None
    pending_health: str | None = None
    pending_intent_issued_at: int | None = None
    pending_return_endpoint: dict[str, Any] | None = None
    consumed: set[str] = {"opening.json", "session-opening.json"}
    phase = "healthy-normal"
    terminal = None
    action_names = {
        name
        for name in nodes
        if name not in {"opening.json", "session-opening.json"}
    }
    common_node_keys = {
        "schema",
        "kind",
        "issued_at",
        "campaign_id",
        "session_id",
        "target",
        "policy_binding_sha256",
        "coordinator_normalized_sha256",
        "ordinal",
        "predecessor_sha256",
        "source_identity",
        "child_counters",
        "campaign_counters",
        "action",
        "component",
        "no_replay",
    }
    health_keys = common_node_keys | {
        "intent_source_identity",
        "observation_for",
        "healthy_android",
    }
    while True:
        candidates: list[tuple[str, Any, bytes]] = []
        for name in action_names - consumed:
            node, raw = nodes[name]
            if isinstance(node, dict) and node.get("predecessor_sha256") == previous_hash:
                candidates.append((name, node, raw))
        if not candidates:
            break
        if len(candidates) != 1:
            raise CoordinatorError("journal chain has duplicate predecessor successors")
        name, node, raw = candidates[0]
        if name == "terminal.json":
            if pending_health is not None or unresolved is not None or arrival is not None or baseline is not None:
                raise CoordinatorError("terminal precedes healthy normal Android")
            _validate_node_time(
                node,
                "terminal",
                current_time=current_time,
                campaign_expires_at=guard["expires_at"],
                session_expires_at=session_expires_at,
                predecessor_issued_at=previous_issued_at,
                preexpiry_required=True,
            )
            _validate_terminal(
                node,
                guard,
                previous_hash,
                current_child,
                current_campaign,
                current_source,
            )
            terminal = node
            consumed.add(name)
            previous_hash = _hash_payload(raw)
            previous_issued_at = node["issued_at"]
            phase = "READY_FOR_ATTENDED_F1"
            break
        if REBOOT_HEALTH_NAME_RE.fullmatch(name) or RETURN_HEALTH_NAME_RE.fullmatch(name):
            kind = "health"
            _exact_keys(node, health_keys, kind)
            _check_binding(node, guard, kind, None)
            _validate_node_time(
                node,
                kind,
                current_time=current_time,
                campaign_expires_at=guard["expires_at"],
                session_expires_at=session_expires_at,
                predecessor_issued_at=previous_issued_at,
                preexpiry_required=False,
            )
            expected_health = (
                "reboot" if REBOOT_HEALTH_NAME_RE.fullmatch(name) else "return"
            )
            if pending_health != expected_health:
                raise CoordinatorError("health node has no matching pending intent")
            name_match = (
                REBOOT_HEALTH_NAME_RE.fullmatch(name)
                if expected_health == "reboot"
                else RETURN_HEALTH_NAME_RE.fullmatch(name)
            )
            assert name_match is not None
            if node["ordinal"] != int(name_match.group(1)):
                raise CoordinatorError("health filename ordinal differs from node")
            intent_source = validate_identity(
                node["intent_source_identity"], "health intent source"
            )
            if not _same_identity(intent_source, current_source):
                raise CoordinatorError("health intent source is not current")
            observed = validate_identity(node["source_identity"], "health source")
            if observed["serial_sha256"] != current_source["serial_sha256"] or observed["topology_sha256"] != current_source["topology_sha256"]:
                raise CoordinatorError("health source endpoint differs")
            if observed["boot_id_sha256"] in seen_boot_ids:
                raise CoordinatorError("health source boot was reused")
            if node["observation_for"] != expected_health or node["healthy_android"] is not True:
                raise CoordinatorError("health observation grammar differs")
            expected_ordinal = (
                current_campaign["normal_reboots"]
                if expected_health == "reboot"
                else current_campaign["download_roundtrips"]
            )
            if node["ordinal"] != expected_ordinal or node["child_counters"] != current_child or node["campaign_counters"] != current_campaign:
                raise CoordinatorError("health counter snapshot differs")
            current_source = observed
            seen_boot_ids.add(observed["boot_id_sha256"])
            pending_health = None
            pending_intent_issued_at = None
            if expected_health == "return":
                pending_return_endpoint = None
            phase = "healthy-normal"
            consumed.add(name)
            previous_hash = _hash_payload(raw)
            previous_issued_at = node["issued_at"]
            continue
        if BASELINE_NAME_RE.fullmatch(name):
            kind = "baseline"
            expected_node_keys = common_node_keys | {"baseline"}
        elif ENTRY_NAME_RE.fullmatch(name):
            kind = "entry"
            expected_node_keys = common_node_keys | {"baseline_sha256"}
        elif ARRIVAL_NAME_RE.fullmatch(name):
            kind = "arrival"
            expected_node_keys = common_node_keys | {"endpoint"}
        elif RETURN_NAME_RE.fullmatch(name):
            kind = "return"
            expected_node_keys = common_node_keys | {"endpoint"}
        elif REBOOT_NAME_RE.fullmatch(name):
            kind = "reboot"
            expected_node_keys = common_node_keys
        else:
            raise CoordinatorError("journal chain contains an unknown node")
        _exact_keys(node, expected_node_keys, kind)
        _check_binding(node, guard, kind, current_source)
        _validate_node_time(
            node,
            kind,
            current_time=current_time,
            campaign_expires_at=guard["expires_at"],
            session_expires_at=session_expires_at,
            predecessor_issued_at=previous_issued_at,
            preexpiry_required=kind in {"baseline", "entry", "reboot"},
        )
        name_match = {
            "entry": ENTRY_NAME_RE,
            "baseline": BASELINE_NAME_RE,
            "arrival": ARRIVAL_NAME_RE,
            "return": RETURN_NAME_RE,
            "reboot": REBOOT_NAME_RE,
        }[kind].fullmatch(name)
        assert name_match is not None
        if node["ordinal"] != int(name_match.group(1)):
            raise CoordinatorError("journal filename ordinal differs from node ordinal")
        if kind == "baseline":
            if phase != "healthy-normal" or unresolved is not None or arrival is not None or pending_health is not None or baseline is not None:
                raise CoordinatorError("baseline requires healthy normal Android")
            expected_ordinal = current_campaign["download_roundtrips"] + 1
            if node["action"] != "download-roundtrip" or node["component"] != "baseline" or node["ordinal"] != expected_ordinal:
                raise CoordinatorError("baseline ordinal or action differs")
            if node["child_counters"] != current_child or node["campaign_counters"] != current_campaign:
                raise CoordinatorError("baseline counter snapshot differs")
            _exact_keys(
                node["baseline"],
                {"endpoint_count", "listing_sha256", "listing_grammar"},
                "Download baseline",
            )
            if (
                node["baseline"]["endpoint_count"] != 0
                or node["baseline"]["listing_sha256"] != EMPTY_DOWNLOAD_LISTING_SHA256
                or node["baseline"]["listing_grammar"] != EMPTY_DOWNLOAD_LISTING_GRAMMAR
            ):
                raise CoordinatorError("Download baseline is nonempty or noncanonical")
            baseline = node
            phase = "download-baseline-ready"
        elif kind == "entry":
            if phase != "download-baseline-ready" or baseline is None or unresolved is not None or arrival is not None or pending_health is not None:
                raise CoordinatorError("entry requires an immediately preceding Download baseline")
            expected_ordinal = baseline["ordinal"]
            if node["action"] != "download-roundtrip" or node["component"] != "entry" or node["ordinal"] != expected_ordinal:
                raise CoordinatorError("entry ordinal or action differs")
            if node["baseline_sha256"] != _hash_payload(canonical_bytes(baseline)):
                raise CoordinatorError("entry baseline predecessor hash differs")
            next_child = debit_before_intent(current_child, "download-roundtrip", "entry", LIMITS)
            next_campaign = debit_before_intent(current_campaign, "download-roundtrip", "entry", CAMPAIGN_LIMITS)
            if node["child_counters"] != next_child or node["campaign_counters"] != next_campaign:
                raise CoordinatorError("entry is not an atomic two-scope debit")
            unresolved = node
            pending_intent_issued_at = node["issued_at"]
            baseline = None
            phase = "download-entry-pending"
            current_child, current_campaign = next_child, next_campaign
        elif kind == "arrival":
            if phase != "download-entry-pending" or unresolved is None or arrival is not None:
                raise CoordinatorError("arrival does not follow one unmatched entry")
            if node["ordinal"] != unresolved["ordinal"] or node["action"] != "download-roundtrip" or node["component"] != "arrival":
                raise CoordinatorError("arrival ordinal or action differs")
            if node["child_counters"] != current_child or node["campaign_counters"] != current_campaign:
                raise CoordinatorError("arrival counter snapshot differs")
            validate_endpoint(node.get("endpoint"), "arrival.endpoint")
            arrival = node
            phase = "download-return-ready"
        elif kind == "return":
            if phase != "download-return-ready" or unresolved is None or arrival is None:
                raise CoordinatorError("return lacks validated arrival")
            if node["ordinal"] != unresolved["ordinal"] or node["action"] != "download-roundtrip" or node["component"] != "return":
                raise CoordinatorError("return ordinal or action differs")
            if not _exact_equal(node.get("endpoint"), arrival["endpoint"]):
                raise CoordinatorError("return endpoint differs from validated arrival")
            next_child = debit_before_intent(current_child, "download-roundtrip", "return", LIMITS)
            next_campaign = debit_before_intent(current_campaign, "download-roundtrip", "return", CAMPAIGN_LIMITS)
            if node["child_counters"] != next_child or node["campaign_counters"] != next_campaign:
                raise CoordinatorError("return is not an atomic two-scope conversion")
            unresolved = None
            pending_return_endpoint = dict(arrival["endpoint"])
            arrival = None
            current_child, current_campaign = next_child, next_campaign
            pending_health = "return"
            pending_intent_issued_at = node["issued_at"]
            phase = "return-health-pending"
        else:
            if phase != "healthy-normal" or unresolved is not None or arrival is not None or pending_health is not None:
                raise CoordinatorError("reboot requires healthy normal Android")
            if node["action"] != "reboot-system" or node["component"] != "reboot":
                raise CoordinatorError("reboot node action differs")
            next_child = debit_before_intent(current_child, "reboot-system", "reboot", LIMITS)
            next_campaign = debit_before_intent(current_campaign, "reboot-system", "reboot", CAMPAIGN_LIMITS)
            if node["ordinal"] != next_campaign["normal_reboots"] or node["child_counters"] != next_child or node["campaign_counters"] != next_campaign:
                raise CoordinatorError("reboot counter snapshot differs")
            current_child, current_campaign = next_child, next_campaign
            pending_health = "reboot"
            pending_intent_issued_at = node["issued_at"]
            phase = "reboot-health-pending"
        consumed.add(name)
        previous_hash = _hash_payload(raw)
        previous_issued_at = node["issued_at"]
    if consumed != set(nodes):
        raise CoordinatorError("old, foreign, partial, or unreachable node exists")
    expired = current_time >= guard["expires_at"]
    session_expired = current_time >= session_expires_at
    return {
        "campaign_id": guard["campaign_id"],
        "session_id": guard["session_id"],
        "phase": phase,
        "expired": expired,
        "session_expired": session_expired,
        "current_time": current_time,
        "campaign_expires_at": guard["expires_at"],
        "session_expires_at": session_expires_at,
        "current_ordinal": current_campaign["download_roundtrips"],
        "source_identity": current_source,
        "endpoint": (
            arrival["endpoint"]
            if arrival is not None
            else pending_return_endpoint
        ),
        "predecessor_sha256": previous_hash,
        "child_counters": current_child,
        "campaign_counters": current_campaign,
        "terminal": terminal,
        "f1_intent": False,
        "approval_consumed": False,
        "partition_transfer": False,
        "no_replay": True,
        "pending_intent_issued_at": pending_intent_issued_at,
    }


def _validate_terminal(
    node: Any,
    guard: dict[str, Any],
    predecessor: str,
    child_counters: dict[str, int],
    campaign_counters: dict[str, int],
    expected_source: dict[str, Any],
) -> None:
    keys = {
        "schema",
        "kind",
        "issued_at",
        "campaign_id",
        "session_id",
        "target",
        "policy_binding_sha256",
        "coordinator_normalized_sha256",
        "ordinal",
        "predecessor_sha256",
        "source_identity",
        "child_counters",
        "campaign_counters",
        "action",
        "component",
        "no_replay",
        "verdict",
        "healthy_normal_android",
        "f1_intent",
        "approval_consumed",
        "partition_transfer",
        "odin_payload",
    }
    _exact_keys(node, keys, "terminal")
    _check_binding(
        {
            key: node[key]
            for key in {
                "schema",
                "kind",
                "issued_at",
                "campaign_id",
                "session_id",
                "target",
                "policy_binding_sha256",
                "coordinator_normalized_sha256",
                "ordinal",
                "predecessor_sha256",
                "source_identity",
                "child_counters",
                "campaign_counters",
                "action",
                "component",
                "no_replay",
            }
        },
        guard,
        "terminal",
        expected_source,
    )
    if node["predecessor_sha256"] != predecessor or node["action"] != "prepare-f1-readiness" or node["component"] != "terminal":
        raise CoordinatorError("terminal predecessor or action differs")
    if node["ordinal"] != campaign_counters["download_roundtrips"]:
        raise CoordinatorError("terminal ordinal differs")
    if node["child_counters"] != child_counters or node["campaign_counters"] != campaign_counters:
        raise CoordinatorError("terminal counters differ")
    if node["verdict"] != "READY_FOR_ATTENDED_F1" or node["healthy_normal_android"] is not True:
        raise CoordinatorError("terminal is not healthy pre-F1 readiness")
    for key in ("f1_intent", "approval_consumed", "partition_transfer", "odin_payload"):
        if node[key] is not False:
            raise CoordinatorError("terminal crosses F1 boundary")


def current_context() -> dict[str, Any]:
    _require_private_context()
    return validate_chain()


def validate_current_guard() -> dict[str, Any]:
    _require_private_context()
    guard, _ = read_exact_json(CAMPAIGN_GUARD_PATH, "campaign guard")
    guard = _validate_guard(guard)
    _require_exact_namespace(
        PRIVATE_RUN_ROOT,
        {"active-campaign.json", "campaigns"},
        "private run root",
    )
    _require_exact_namespace(CAMPAIGNS_ROOT, {guard["campaign_id"]}, "campaign root")
    return guard


def validate_full_chain(now: int | None = None) -> dict[str, Any]:
    _require_private_context()
    return validate_chain(now)


def terminal_guard_state() -> dict[str, Any]:
    """Classify terminal/guard reporting cuts without issuing any effect."""
    _require_private_context()
    try:
        context = validate_chain()
    except CoordinatorError as validation_error:
        guard_result = _read_optional_json(CAMPAIGN_GUARD_PATH, "campaign guard")
        if guard_result is not None:
            raise validation_error
        # A missing guard is never authority.  A terminal without its guard is
        # deliberately not self-certifying: report only presence and do not
        # read or certify a standalone terminal value.
        try:
            campaign_names = _directory_names(CAMPAIGNS_ROOT, "campaign root")
        except CoordinatorError:
            return {
                "terminal_present": False,
                "guard_present": False,
                "authority": False,
                "terminal_certified": False,
                "no_device_commands": True,
            }
        if len(campaign_names) != 1 or ID_RE.fullmatch(campaign_names[0]) is None:
            return {
                "terminal_present": False,
                "guard_present": False,
                "authority": False,
                "terminal_certified": False,
                "no_device_commands": True,
            }
        session_dir = _session_dir(campaign_names[0])
        session_descriptor = -1
        try:
            session_descriptor = _open_managed_directory(session_dir)
            try:
                metadata = os.stat(
                    "terminal.json",
                    dir_fd=session_descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                return {
                    "terminal_present": False,
                    "guard_present": False,
                    "authority": False,
                    "terminal_certified": False,
                    "no_device_commands": True,
                }
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                return {
                    "terminal_present": False,
                    "guard_present": False,
                    "authority": False,
                    "terminal_certified": False,
                    "no_device_commands": True,
                }
        except CoordinatorError:
            return {
                "terminal_present": False,
                "guard_present": False,
                "authority": False,
                "terminal_certified": False,
                "no_device_commands": True,
            }
        finally:
            if session_descriptor >= 0:
                os.close(session_descriptor)
        return {
            "terminal_present": True,
            "guard_present": False,
            "authority": False,
            "terminal_certified": False,
            "no_device_commands": True,
            "reason": "guard missing; standalone terminal is uncertified",
        }


def recovery_authority(now: int | None = None) -> dict[str, Any]:
    """Return only the reserved-return recovery surface after expiry.

    The result is derived from the current fixed guard and full chain.  It is
    descriptive H0 evidence; it does not send a command or publish a node.
    """
    _require_private_context()
    context = validate_chain(now)
    expired = context["expired"] or context["session_expired"]
    if not expired:
        return {
            "authority": False,
            "reason": "current campaign/session has not expired",
            "campaign_id": context["campaign_id"],
            "session_id": context["session_id"],
            "current_ordinal": context["current_ordinal"],
            "no_replay": True,
        }
    if context["phase"] not in {
        "download-entry-pending",
        "download-return-ready",
        "return-health-pending",
        "reboot-health-pending",
    }:
        return {
            "authority": False,
            "reason": "no unmatched reserved return",
            "campaign_id": context["campaign_id"],
            "session_id": context["session_id"],
            "current_ordinal": context["current_ordinal"],
            "no_replay": True,
        }
    actions = {
        "download-entry-pending": ("observe-bound-arrival",),
        "download-return-ready": ("payload-free-return",),
        "return-health-pending": ("observe-return-health", "final-health"),
        "reboot-health-pending": ("observe-reboot-health",),
    }[context["phase"]]
    return {
        "authority": True,
        "recovery_only": True,
        "expired": expired,
        "allowed_actions": list(actions),
        "campaign_id": context["campaign_id"],
        "session_id": context["session_id"],
        "current_ordinal": context["current_ordinal"],
        "source_identity": context["source_identity"],
        "endpoint": context["endpoint"],
        "predecessor_sha256": context["predecessor_sha256"],
        "no_new_baseline": True,
        "no_new_entry": True,
        "no_new_transaction": True,
        "no_replay": True,
    }


def render_plan() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "active": False,
        "live_authority": False,
        "mechanically_activatable": False,
        "live_action_integration": False,
        "journal_candidate_only": True,
        "cli": ["--render-plan"],
        "policy_owner_permanently_render_only": True,
        "binding_sha256": binding_digest(),
        "binding": binding_value(),
        "fixed_private_campaign_guard_path": str(CAMPAIGN_GUARD_PATH),
        "fixed_private_campaign_run_root": str(CAMPAIGNS_ROOT),
        "device_commands": [],
        "root_commands": [],
        "device_effects": [],
        "partition_transfers": [],
        "odin_payloads": [],
        "pre_f1_terminal": {
            "verdict": "READY_FOR_ATTENDED_F1",
            "f1_intent": False,
            "approval_consumed": False,
            "partition_transfer": False,
            "odin_payload": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-plan", action="store_true")
    args = parser.parse_args()
    if not args.render_plan:
        parser.error("only --render-plan exists while the coordinator is dormant")
    print(json.dumps(render_plan(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
