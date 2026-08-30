#!/usr/bin/env python3
"""Permanent-inactive exact loader for the S20+ public-health recovery core.

The loader is an independent root of trust.  It opens only three fixed private
roots, acquires the existing coordinator lock, verifies the exact private core
and manifest through held no-follow directory handles, compiles only those
verified bytes, and injects a fresh object-identity capability.  Its production
finalizer/re-emission gates are false and its CLI is render-only in this H0 unit.
"""

from __future__ import annotations

import argparse
import ast
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from types import MappingProxyType
from typing import Any, Mapping, Sequence


STATUS = "H0_PUBLIC_HEALTH_RECOVERY_LOADER_V1_PASS_GO_NOT_ACTIVE"
EXPECTED_LOADER_NORMALIZED_SHA256 = (
    "8df4dc534a1d4e9ac1a73867151e4bfcf2450a52283a281c7091d9c47e1e09cc"
)
LOADER_V1_QUALIFIED = False
FINALIZER_IDENTITY_ACTIVE = False
MANIFEST_IDENTITY_ACTIVE = False
FINALIZER_OPERATION_ACTIVE = False
REEMIT_OPERATION_ACTIVE = False
FUTURE_RUNNER_BINDING_ACTIVE = False
CONTRACT_ACTIVE = False
MECHANICAL_ACTIVATION = False
LIVE_AUTHORITY = False
PERMANENT_VERSIONED_LOADER = True

TARGET = MappingProxyType(
    {
        "model": "SM-G986N",
        "device": "y2q",
        "product": "y2qksx",
        "build": "G986NKSS8IYC2",
    }
)
PLAN_SCHEMA = "s20plus_g986n_autonomous_public_health_recovery_loader_v1_plan"
MANIFEST_SCHEMA = "s20plus_g986n_autonomous_public_health_recovery_v1_manifest"
RECOVERY_DIRECTORY = "recovery-v1"
RECOVERY_CORE_NAME = "recovery-core.py"
RECOVERY_MANIFEST_NAME = "manifest.json"
LOCK_NAME = "coordinator.lock"

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

ALLOWED_CORE_SIZE = 162_875
ALLOWED_CORE_SHA256 = "94f6022aebcdc63bcad08757f493349d2e4b198610a367e72181a65694321f0b"
ALLOWED_CORE_NORMALIZED_SHA256 = (
    "38cb154e526e8a1a3ad38f8c857f03668f92fedced786745f5e8e85d91e21dac"
)
ALLOWED_MANIFEST_SIZE = 7_669
ALLOWED_MANIFEST_SHA256 = (
    "51931dd9a084e1c7ae8d674681d34be7bd2f50b32d8c0b84b2842d51749df593"
)
RECOVERY_CORE_MAX_BYTES = 256 * 1024
RECOVERY_MANIFEST_MAX_BYTES = 32 * 1024
RECOVERY_BUNDLE_MAX_BYTES = 288 * 1024
LOADER_SOURCE_MAX_BYTES = 64 * 1024
STRUCTURAL_MAX_BYTES = 48 * 1024
EVIDENCE_PROOF_MAX_BYTES = 507_904
COMPLETED_TOTAL_MAX_BYTES = 1_441_792
COMPLETED_TOTAL_FILE_COUNT = 52
ZERO_HASH = "0" * 64

if (
    ALLOWED_CORE_SIZE > RECOVERY_CORE_MAX_BYTES
    or ALLOWED_MANIFEST_SIZE > RECOVERY_MANIFEST_MAX_BYTES
    or ALLOWED_CORE_SIZE + ALLOWED_MANIFEST_SIZE > RECOVERY_BUNDLE_MAX_BYTES
):
    raise RuntimeError("allowed recovery bundle exceeds fixed closure")


class RecoveryLoaderV1Error(RuntimeError):
    pass


def sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise RecoveryLoaderV1Error("hash input is not bytes")
    return hashlib.sha256(payload).hexdigest()


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
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise RecoveryLoaderV1Error("value is not canonical JSON") from exc


def _reject_constant(value: str) -> Any:
    raise RecoveryLoaderV1Error(f"non-finite JSON constant {value!r}")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RecoveryLoaderV1Error("duplicate JSON key")
        result[key] = value
    return result


def parse_canonical_json(payload: bytes, label: str, maximum: int) -> Any:
    if (
        type(payload) is not bytes
        or not payload
        or type(maximum) is not int
        or type(maximum) is bool
        or maximum <= 0
        or len(payload) > maximum
    ):
        raise RecoveryLoaderV1Error(f"{label} bytes exceed fixed bound")
    try:
        value = json.loads(
            payload.decode("utf-8", "strict"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryLoaderV1Error(f"{label} is not strict JSON") from exc
    if canonical_bytes(value) != payload:
        raise RecoveryLoaderV1Error(f"{label} is not canonical JSON")
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


def _validate_directory(value: os.stat_result, label: str) -> None:
    if (
        not stat.S_ISDIR(value.st_mode)
        or stat.S_IMODE(value.st_mode) != 0o700
        or value.st_uid != os.geteuid()
        or value.st_gid != os.getegid()
    ):
        raise RecoveryLoaderV1Error(f"{label} directory identity differs")


def _safe_component(name: str, label: str) -> str:
    if (
        type(name) is not str
        or not name
        or name in (".", "..")
        or "/" in name
        or "\x00" in name
    ):
        raise RecoveryLoaderV1Error(f"{label} component differs")
    return name


def _open_absolute_directory(path: Path, label: str) -> int:
    path = Path(path)
    if not path.is_absolute() or any(
        component in ("", ".", "..") for component in path.parts[1:]
    ):
        raise RecoveryLoaderV1Error(f"{label} path is not fixed absolute")
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
        _validate_directory(os.fstat(descriptor), label)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _open_fixed_root(label: str) -> int:
    if label not in FIXED_ROOTS:
        raise RecoveryLoaderV1Error("root label is outside fixed closure")
    try:
        return _open_absolute_directory(FIXED_ROOTS[label], f"{label} root")
    except OSError as exc:
        raise RecoveryLoaderV1Error(f"{label} root is unavailable") from exc


def _open_child_directory(parent: int, name: str, label: str) -> int:
    _safe_component(name, label)
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY
            | os.O_DIRECTORY
            | os.O_CLOEXEC
            | os.O_NOFOLLOW
            | os.O_NONBLOCK,
            dir_fd=parent,
        )
    except OSError as exc:
        raise RecoveryLoaderV1Error(f"{label} is unavailable") from exc
    try:
        _validate_directory(os.fstat(descriptor), label)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _directory_names(descriptor: int, label: str, maximum: int) -> tuple[str, ...]:
    if type(maximum) is not int or type(maximum) is bool or maximum < 0:
        raise RecoveryLoaderV1Error(f"{label} entry cap differs")
    before = os.fstat(descriptor)
    try:
        collected: list[str] = []
        with os.scandir(descriptor) as entries:
            for entry in entries:
                if len(collected) >= maximum:
                    raise RecoveryLoaderV1Error(f"{label} exceeds entry cap")
                collected.append(entry.name)
    except OSError as exc:
        raise RecoveryLoaderV1Error(f"{label} enumeration failed") from exc
    after = os.fstat(descriptor)
    names = tuple(sorted(collected))
    if _metadata(before) != _metadata(after) or len(names) != len(set(names)):
        raise RecoveryLoaderV1Error(f"{label} changed while enumerated")
    return names


def _read_regular_exact(
    parent: int,
    name: str,
    label: str,
    expected_size: int,
    mode: int,
) -> bytes:
    _safe_component(name, label)
    if type(expected_size) is not int or type(expected_size) is bool or expected_size <= 0:
        raise RecoveryLoaderV1Error(f"{label} size binding differs")
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=parent,
        )
    except OSError as exc:
        raise RecoveryLoaderV1Error(f"{label} is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != mode
            or before.st_nlink != 1
            or before.st_uid != os.geteuid()
            or before.st_gid != os.getegid()
            or before.st_size != expected_size
        ):
            raise RecoveryLoaderV1Error(f"{label} file identity differs")
        payload = bytearray()
        while len(payload) < expected_size:
            chunk = os.read(descriptor, min(65_536, expected_size - len(payload)))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) != expected_size or os.read(descriptor, 1):
            raise RecoveryLoaderV1Error(f"{label} length differs")
        after = os.fstat(descriptor)
        if _metadata(before) != _metadata(after):
            raise RecoveryLoaderV1Error(f"{label} changed while read")
        return bytes(payload)
    finally:
        os.close(descriptor)


class _ExistingCoordinatorLock:
    def __init__(self, leaf_fd: int):
        self.leaf_fd = leaf_fd
        self.descriptor = -1
        self.identity: tuple[int, ...] | None = None

    def __enter__(self) -> int:
        try:
            self.descriptor = os.open(
                LOCK_NAME,
                os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
                dir_fd=self.leaf_fd,
            )
            before = os.fstat(self.descriptor)
            named = os.stat(
                LOCK_NAME, dir_fd=self.leaf_fd, follow_symlinks=False
            )
            if (
                not stat.S_ISREG(before.st_mode)
                or stat.S_IMODE(before.st_mode) != 0o600
                or before.st_nlink != 1
                or before.st_uid != os.geteuid()
                or before.st_gid != os.getegid()
                or before.st_size != 0
                or _metadata(before) != _metadata(named)
            ):
                raise RecoveryLoaderV1Error("coordinator lock identity differs")
            fcntl.flock(self.descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            after = os.fstat(self.descriptor)
            if _metadata(before) != _metadata(after):
                raise RecoveryLoaderV1Error("coordinator lock changed on acquisition")
            self.identity = _metadata(after)
            return self.descriptor
        except BlockingIOError as exc:
            self._close()
            raise RecoveryLoaderV1Error("coordinator lock is already held") from exc
        except OSError as exc:
            self._close()
            raise RecoveryLoaderV1Error("coordinator lock open failed") from exc
        except BaseException:
            self._close()
            raise

    def _close(self) -> None:
        if self.descriptor >= 0:
            os.close(self.descriptor)
            self.descriptor = -1
        self.identity = None

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.descriptor >= 0:
            try:
                after = os.fstat(self.descriptor)
                named = os.stat(
                    LOCK_NAME, dir_fd=self.leaf_fd, follow_symlinks=False
                )
                if (
                    self.identity is None
                    or _metadata(after) != self.identity
                    or _metadata(named) != self.identity
                ):
                    raise RecoveryLoaderV1Error(
                        "coordinator lock changed while operation was held"
                    )
            finally:
                try:
                    fcntl.flock(self.descriptor, fcntl.LOCK_UN)
                finally:
                    self._close()


def normalized_core_sha256(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise RecoveryLoaderV1Error("core normalization requires bytes")
    normalized = payload
    normalized, status_count = re.subn(
        rb'^STATUS = "[A-Z0-9_]+"$',
        b'STATUS = "<REVIEWED_STATUS>"',
        normalized,
        flags=re.MULTILINE,
    )
    normalized, anchor_count = re.subn(
        rb'^EXPECTED_RECOVERY_NORMALIZED_SHA256 = "[0-9a-f]{64}"$',
        b'EXPECTED_RECOVERY_NORMALIZED_SHA256 = "<REVIEWED_RECOVERY_ANCHOR>"',
        normalized,
        flags=re.MULTILINE,
    )
    normalized, runner_count = re.subn(
        rb"^FUTURE_RUNNER_BINDING_JSON = b'[^\r\n]*\\n'$",
        b"FUTURE_RUNNER_BINDING_JSON = b'<REVIEWED_FUTURE_RUNNER_BINDING>\\\\n'",
        normalized,
        flags=re.MULTILINE,
    )
    if (status_count, anchor_count, runner_count) != (1, 1, 1):
        raise RecoveryLoaderV1Error("core identity normalization is ambiguous")
    for name in (
        "RECOVERY_V1_QUALIFIED",
        "RECOVERY_SCANNER_ACTIVE",
        "RECOVERY_WRITER_ACTIVE",
        "RECOVERY_FINALIZER_PUBLICATION_ACTIVE",
        "RECOVERY_FINALIZER_ACTIVE",
        "RECOVERY_REEMIT_ACTIVE",
        "RECOVERY_MANIFEST_ACTIVE",
        "RECOVERY_CONTRACT_ACTIVE",
        "LIVE_AUTHORITY",
    ):
        normalized, count = re.subn(
            rf"^{name} = (?:False|True)$".encode(),
            f"{name} = <REVIEWED_BOOLEAN>".encode(),
            normalized,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise RecoveryLoaderV1Error("core activation normalization is ambiguous")
    return sha256_bytes(normalized)


def normalized_self_sha256(payload: bytes) -> str:
    """Stable loader identity that breaks the loader/core binding cycle."""
    if type(payload) is not bytes:
        raise RecoveryLoaderV1Error("loader normalization requires bytes")
    normalized = payload
    replacements = (
        (
            rb'^STATUS = "[A-Z0-9_]+"$',
            b'STATUS = "<REVIEWED_STATUS>"',
        ),
        (
            rb'^EXPECTED_LOADER_NORMALIZED_SHA256 = \($\n^    "[0-9a-f]{64}"$\n^\)$',
            b'EXPECTED_LOADER_NORMALIZED_SHA256 = (\n'
            b'    "<REVIEWED_LOADER_ANCHOR>"\n'
            b')',
        ),
        (
            rb'^ALLOWED_CORE_SIZE = [0-9_]+$',
            b'ALLOWED_CORE_SIZE = <REVIEWED_CORE_SIZE>',
        ),
        (
            rb'^ALLOWED_CORE_SHA256 = "[0-9a-f]{64}"$',
            b'ALLOWED_CORE_SHA256 = "<REVIEWED_CORE_SHA256>"',
        ),
        (
            rb'^ALLOWED_CORE_NORMALIZED_SHA256 = \($\n^    "[0-9a-f]{64}"$\n^\)$',
            b'ALLOWED_CORE_NORMALIZED_SHA256 = (\n'
            b'    "<REVIEWED_CORE_NORMALIZED_SHA256>"\n'
            b')',
        ),
        (
            rb'^ALLOWED_MANIFEST_SIZE = [0-9_]+$',
            b'ALLOWED_MANIFEST_SIZE = <REVIEWED_MANIFEST_SIZE>',
        ),
        (
            rb'^ALLOWED_MANIFEST_SHA256 = \($\n^    "[0-9a-f]{64}"$\n^\)$',
            b'ALLOWED_MANIFEST_SHA256 = (\n'
            b'    "<REVIEWED_MANIFEST_SHA256>"\n'
            b')',
        ),
    )
    for pattern, replacement in replacements:
        normalized, count = re.subn(
            pattern, replacement, normalized, flags=re.MULTILINE
        )
        if count != 1:
            raise RecoveryLoaderV1Error("loader identity normalization is ambiguous")
    for name in (
        "LOADER_V1_QUALIFIED",
        "FINALIZER_IDENTITY_ACTIVE",
        "MANIFEST_IDENTITY_ACTIVE",
        "FINALIZER_OPERATION_ACTIVE",
        "REEMIT_OPERATION_ACTIVE",
        "FUTURE_RUNNER_BINDING_ACTIVE",
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
            raise RecoveryLoaderV1Error("loader activation normalization is ambiguous")
    return sha256_bytes(normalized)


def _require_manifest_semantics(manifest: Any, raw: bytes) -> dict[str, Any]:
    if type(manifest) is not dict or canonical_bytes(manifest) != raw:
        raise RecoveryLoaderV1Error("manifest object/bytes differ")
    required = {
        "schema",
        "status",
        "target",
        "core",
        "future_runner_binding",
        "fixed_roots",
        "caps",
        "entrypoints",
        "manifest_published_last",
        "direct_path_execution_authoritative",
        "private_core_requires_nofollow_manifest_verified_loader",
        "independent_loader_runner_identity_cross_check_implemented",
        "replay_authorized",
        "refund_authorized",
        "next_action_authorized",
        "live_authority",
    }
    if not required <= set(manifest):
        raise RecoveryLoaderV1Error("manifest required model fields are absent")
    expected_core = {
        "name": RECOVERY_CORE_NAME,
        "size": ALLOWED_CORE_SIZE,
        "sha256": ALLOWED_CORE_SHA256,
        "normalized_sha256": ALLOWED_CORE_NORMALIZED_SHA256,
        "normalized_sha256_expected": ALLOWED_CORE_NORMALIZED_SHA256,
        "runner_binding_is_activation_normalized": True,
        "mode": "0400",
    }
    if (
        manifest["schema"] != MANIFEST_SCHEMA
        or manifest["status"] != "H0_PRIVATE_RECOVERY_FINALIZER_COPY_NOT_ACTIVE"
        or manifest["target"] != dict(TARGET)
        or manifest["core"] != expected_core
        or manifest["fixed_roots"]
        != {key: str(value) for key, value in FIXED_ROOTS.items()}
        or manifest["manifest_published_last"] is not True
        or manifest["direct_path_execution_authoritative"] is not False
        or manifest["private_core_requires_nofollow_manifest_verified_loader"]
        is not True
        or manifest["independent_loader_runner_identity_cross_check_implemented"]
        is not False
        or manifest["replay_authorized"] is not False
        or manifest["refund_authorized"] is not False
        or manifest["next_action_authorized"] is not False
        or manifest["live_authority"] is not False
    ):
        raise RecoveryLoaderV1Error("manifest exact identity model differs")
    binding = manifest["future_runner_binding"]
    if type(binding) is not dict:
        raise RecoveryLoaderV1Error("manifest future runner binding differs")
    if FUTURE_RUNNER_BINDING_ACTIVE is True:
        if (
            binding.get("status") != "BOUND"
            or binding.get("binding_complete") is not True
            or binding.get("normalized_sha256")
            != EXPECTED_LOADER_NORMALIZED_SHA256
        ):
            raise RecoveryLoaderV1Error("manifest future runner binding differs")
    elif (
        binding.get("status") != "UNBOUND_PLACEHOLDER"
        or binding.get("binding_complete") is not False
        or binding.get("normalized_sha256") != ZERO_HASH
    ):
        raise RecoveryLoaderV1Error("manifest future runner is not dormant")
    caps = manifest["caps"]
    expected_caps = {
        "core_max_bytes": RECOVERY_CORE_MAX_BYTES,
        "manifest_max_bytes": RECOVERY_MANIFEST_MAX_BYTES,
        "recovery_bundle_max_bytes": RECOVERY_BUNDLE_MAX_BYTES,
        "structural_max_bytes": STRUCTURAL_MAX_BYTES,
        "evidence_proof_max_bytes": EVIDENCE_PROOF_MAX_BYTES,
        "completed_total_max_bytes": COMPLETED_TOTAL_MAX_BYTES,
        "completed_total_file_count": COMPLETED_TOTAL_FILE_COUNT,
    }
    if any(caps.get(key) != value for key, value in expected_caps.items()):
        raise RecoveryLoaderV1Error("manifest closure caps differ")
    expected_entries = {
        "finalize_zero_command": (
            "implemented-held-dirfd-loader-capability-gated-inactive"
        ),
        "reemit_terminal": (
            "implemented-full-ancestry-sanitized-repeatable-gated-inactive"
        ),
    }
    if any(
        manifest["entrypoints"].get(key) != value
        for key, value in expected_entries.items()
    ):
        raise RecoveryLoaderV1Error("manifest finalizer entrypoint model differs")
    return dict(manifest)


def _verify_bundle_at(recovery_fd: int) -> tuple[bytes, bytes, dict[str, Any]]:
    if set(_directory_names(recovery_fd, "recovery bundle", 2)) != {
        RECOVERY_CORE_NAME,
        RECOVERY_MANIFEST_NAME,
    }:
        raise RecoveryLoaderV1Error("recovery bundle namespace differs")
    core = _read_regular_exact(
        recovery_fd,
        RECOVERY_CORE_NAME,
        "recovery core",
        ALLOWED_CORE_SIZE,
        0o400,
    )
    manifest_raw = _read_regular_exact(
        recovery_fd,
        RECOVERY_MANIFEST_NAME,
        "recovery manifest",
        ALLOWED_MANIFEST_SIZE,
        0o400,
    )
    if (
        sha256_bytes(core) != ALLOWED_CORE_SHA256
        or normalized_core_sha256(core) != ALLOWED_CORE_NORMALIZED_SHA256
        or sha256_bytes(manifest_raw) != ALLOWED_MANIFEST_SHA256
    ):
        raise RecoveryLoaderV1Error("recovery core or manifest identity differs")
    manifest = parse_canonical_json(
        manifest_raw, "recovery manifest", RECOVERY_MANIFEST_MAX_BYTES
    )
    return core, manifest_raw, _require_manifest_semantics(manifest, manifest_raw)


def _load_verified_namespace_at(
    recovery_fd: int,
) -> tuple[dict[str, Any], object, bytes]:
    core, manifest_raw, manifest = _verify_bundle_at(recovery_fd)
    try:
        source = core.decode("utf-8", "strict")
        tree = ast.parse(source, filename="<verified-recovery-core>")
        code = compile(
            tree,
            filename="<verified-recovery-core>",
            mode="exec",
            dont_inherit=True,
            optimize=0,
        )
    except (UnicodeDecodeError, SyntaxError, ValueError) as exc:
        raise RecoveryLoaderV1Error("verified recovery core is not exact Python") from exc
    capability = object()
    namespace: dict[str, Any] = {
        "__name__": "_s20plus_verified_private_recovery_core",
        "__file__": "<verified-recovery-core>",
        "__builtins__": __builtins__,
        "__recovery_loader_capability__": capability,
        "__recovery_verified_core_bytes__": core,
        "__recovery_verified_manifest_bytes__": manifest_raw,
    }
    exec(code, namespace, namespace)
    if (
        namespace.get("_LOADER_CAPABILITY") is not capability
        or namespace.get("_VERIFIED_CORE_BYTES") != core
        or namespace.get("_VERIFIED_MANIFEST_BYTES") != manifest_raw
        or namespace.get("TARGET") != dict(TARGET)
        or namespace.get("EXPECTED_RECOVERY_NORMALIZED_SHA256")
        != ALLOWED_CORE_NORMALIZED_SHA256
        or not callable(namespace.get("loader_finalize_zero_command"))
        or not callable(namespace.get("loader_reemit_terminal"))
    ):
        raise RecoveryLoaderV1Error("compiled recovery namespace differs")
    for injected in (
        "__recovery_loader_capability__",
        "__recovery_verified_core_bytes__",
        "__recovery_verified_manifest_bytes__",
    ):
        if injected in namespace:
            raise RecoveryLoaderV1Error("loader injection remained publicly named")
    if manifest["core"]["sha256"] != sha256_bytes(core):
        raise RecoveryLoaderV1Error("compiled core differs from manifest")
    return namespace, capability, manifest_raw


def _require_reopened_fixed_root(label: str, held: int) -> None:
    reopened = _open_fixed_root(label)
    try:
        if (os.fstat(reopened).st_dev, os.fstat(reopened).st_ino) != (
            os.fstat(held).st_dev,
            os.fstat(held).st_ino,
        ):
            raise RecoveryLoaderV1Error(f"{label} fixed path changed")
    finally:
        os.close(reopened)


def _require_reopened_roots(held: Mapping[str, int], recovery_fd: int) -> None:
    if type(held) is not dict or set(held) != {"base", "evidence", "leaf"}:
        raise RecoveryLoaderV1Error("held root set differs")
    for label in ("base", "evidence", "leaf"):
        _require_reopened_fixed_root(label, held[label])
    reopened_leaf = _open_fixed_root("leaf")
    try:
        reopened_recovery = _open_child_directory(
            reopened_leaf, RECOVERY_DIRECTORY, "reopened recovery-v1"
        )
        try:
            if (os.fstat(reopened_recovery).st_dev, os.fstat(reopened_recovery).st_ino) != (
                os.fstat(recovery_fd).st_dev,
                os.fstat(recovery_fd).st_ino,
            ):
                raise RecoveryLoaderV1Error("recovery-v1 fixed path changed")
        finally:
            os.close(reopened_recovery)
    finally:
        os.close(reopened_leaf)


def _require_operational_gate(operation: str) -> None:
    selected = {
        "finalize": FINALIZER_OPERATION_ACTIVE,
        "reemit": REEMIT_OPERATION_ACTIVE,
    }
    if (
        operation not in selected
        or LOADER_V1_QUALIFIED is not True
        or FINALIZER_IDENTITY_ACTIVE is not True
        or MANIFEST_IDENTITY_ACTIVE is not True
        or FUTURE_RUNNER_BINDING_ACTIVE is not True
        or CONTRACT_ACTIVE is not True
        or MECHANICAL_ACTIVATION is not True
        or selected[operation] is not True
        or LIVE_AUTHORITY is not False
    ):
        raise RecoveryLoaderV1Error(f"{operation} loader operation is inactive")
    source = _read_self_bytes()
    if normalized_self_sha256(source) != EXPECTED_LOADER_NORMALIZED_SHA256:
        raise RecoveryLoaderV1Error("executing loader normalized identity differs")


def _require_bound_loader_manifest(manifest: Mapping[str, Any]) -> None:
    binding = manifest.get("future_runner_binding")
    if (
        type(binding) is not dict
        or binding.get("status") != "BOUND"
        or binding.get("binding_complete") is not True
        or binding.get("normalized_sha256") != EXPECTED_LOADER_NORMALIZED_SHA256
    ):
        raise RecoveryLoaderV1Error("recovery core is not bound to this loader")


def _write_stdout_exact(payload: bytes) -> None:
    if type(payload) is not bytes or not payload:
        raise RecoveryLoaderV1Error("terminal stdout payload differs")
    offset = 0
    while offset < len(payload):
        count = os.write(1, payload[offset:])
        if type(count) is not int or type(count) is bool or count <= 0:
            raise RecoveryLoaderV1Error("terminal stdout write did not progress")
        offset += count


def _run_fixed_operation(operation: str) -> dict[str, Any] | None:
    _require_operational_gate(operation)
    held: dict[str, int] = {}
    recovery_fd = -1
    try:
        for label in ("base", "evidence", "leaf"):
            held[label] = _open_fixed_root(label)
        identities = {
            (os.fstat(descriptor).st_dev, os.fstat(descriptor).st_ino)
            for descriptor in held.values()
        }
        if len(identities) != 3:
            raise RecoveryLoaderV1Error("fixed roots are not distinct")
        with _ExistingCoordinatorLock(held["leaf"]):
            recovery_fd = _open_child_directory(
                held["leaf"], RECOVERY_DIRECTORY, "recovery-v1"
            )
            namespace, capability, manifest_raw = _load_verified_namespace_at(
                recovery_fd
            )
            manifest = parse_canonical_json(
                manifest_raw, "recovery manifest", RECOVERY_MANIFEST_MAX_BYTES
            )
            _require_bound_loader_manifest(manifest)
            if operation == "finalize":
                result = namespace["loader_finalize_zero_command"](
                    capability,
                    held["base"],
                    held["evidence"],
                    held["leaf"],
                    manifest_raw,
                )
                _verify_bundle_at(recovery_fd)
                _require_reopened_roots(held, recovery_fd)
                return result
            payload = namespace["loader_reemit_terminal"](
                capability,
                held["base"],
                held["evidence"],
                held["leaf"],
                manifest_raw,
            )
            _verify_bundle_at(recovery_fd)
            _require_reopened_roots(held, recovery_fd)
            _write_stdout_exact(payload)
            return None
    finally:
        if recovery_fd >= 0:
            os.close(recovery_fd)
        for descriptor in held.values():
            try:
                os.close(descriptor)
            except OSError:
                pass


def finalize_zero_command() -> dict[str, Any]:
    result = _run_fixed_operation("finalize")
    if type(result) is not dict:
        raise RecoveryLoaderV1Error("finalizer result differs")
    return result


def reemit_terminal() -> None:
    _run_fixed_operation("reemit")


def _read_self_bytes() -> bytes:
    path = Path(__file__)
    if not path.is_absolute():
        raise RecoveryLoaderV1Error("loader source path is not absolute")
    descriptor = os.open(
        path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_uid != os.geteuid()
            or before.st_gid != os.getegid()
            or before.st_size <= 0
            or before.st_size > LOADER_SOURCE_MAX_BYTES
        ):
            raise RecoveryLoaderV1Error("loader source identity differs")
        payload = bytearray()
        while len(payload) < before.st_size:
            chunk = os.read(descriptor, min(65_536, before.st_size - len(payload)))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) != before.st_size or os.read(descriptor, 1):
            raise RecoveryLoaderV1Error("loader source length differs")
        if _metadata(before) != _metadata(os.fstat(descriptor)):
            raise RecoveryLoaderV1Error("loader source changed while read")
        return bytes(payload)
    finally:
        os.close(descriptor)


def render_plan() -> dict[str, Any]:
    source = _read_self_bytes()
    return {
        "schema": PLAN_SCHEMA,
        "status": STATUS,
        "target": dict(TARGET),
        "loader_v1_qualified": LOADER_V1_QUALIFIED,
        "finalizer_identity_active": FINALIZER_IDENTITY_ACTIVE,
        "manifest_identity_active": MANIFEST_IDENTITY_ACTIVE,
        "finalizer_operation_active": FINALIZER_OPERATION_ACTIVE,
        "reemit_operation_active": REEMIT_OPERATION_ACTIVE,
        "future_runner_binding_active": FUTURE_RUNNER_BINDING_ACTIVE,
        "contract_active": CONTRACT_ACTIVE,
        "mechanical_activation": MECHANICAL_ACTIVATION,
        "live_authority": LIVE_AUTHORITY,
        "permanent_versioned_loader": PERMANENT_VERSIONED_LOADER,
        "cli": ["--render-plan"],
        "self": {
            "size": len(source),
            "sha256": sha256_bytes(source),
            "normalized_sha256": normalized_self_sha256(source),
            "normalized_sha256_expected": EXPECTED_LOADER_NORMALIZED_SHA256,
        },
        "allowed_core": {
            "name": RECOVERY_CORE_NAME,
            "size": ALLOWED_CORE_SIZE,
            "sha256": ALLOWED_CORE_SHA256,
            "normalized_sha256": ALLOWED_CORE_NORMALIZED_SHA256,
            "mode": "0400",
        },
        "allowed_manifest": {
            "name": RECOVERY_MANIFEST_NAME,
            "size": ALLOWED_MANIFEST_SIZE,
            "sha256": ALLOWED_MANIFEST_SHA256,
            "mode": "0400",
        },
        "fixed_roots": {key: str(value) for key, value in FIXED_ROOTS.items()},
        "loader_protocol": [
            "open-three-fixed-roots-componentwise-nofollow",
            "acquire-existing-mode-0600-zero-byte-coordinator-lock",
            "verify-exact-two-file-recovery-bundle",
            "verify-core-full-and-normalized-identities",
            "verify-canonical-manifest-full-identity-and-critical-model",
            "compile-only-verified-held-bytes",
            "inject-fresh-object-identity-capability",
            "pass-held-base-evidence-leaf-dirfds-and-manifest-bytes",
            "reopen-all-fixed-roots-and-recovery-directory-after-operation",
        ],
        "future_noncircular_binding_order": [
            "freeze-finalizer-normalized-identity",
            "freeze-loader-normalized-identity-with-core-manifest-literals-masked",
            "bind-loader-normalized-identity-into-finalizer-runner-binding",
            "freeze-bound-finalizer-full-identity-and-manifest-full-identity",
            "rotate-loader-exact-core-and-manifest-literals",
            "independent-review-before-any-gate-activation",
        ],
        "future_reserved_completed_closure": {
            "bundle_max_bytes": RECOVERY_BUNDLE_MAX_BYTES,
            "structural_max_bytes": STRUCTURAL_MAX_BYTES,
            "evidence_proof_max_bytes": EVIDENCE_PROOF_MAX_BYTES,
            "total_max_bytes": COMPLETED_TOTAL_MAX_BYTES,
            "total_file_count": COMPLETED_TOTAL_FILE_COUNT,
            "current_scanner_accepts_future_opening_and_binding": False,
        },
        "loader_source_max_bytes": LOADER_SOURCE_MAX_BYTES,
        "production_entrypoints": {
            "finalize_zero_command": "inactive",
            "reemit_terminal": "inactive",
        },
        "caller_inputs": [],
        "device_commands": [],
        "device_effects": [],
        "root_commands": [],
        "subprocesses": [],
        "sockets": [],
        "writes_before_activation": [],
        "unresolved_gates": [
            "exact-independent-review",
            "future-runner-binding",
            "private-bundle-install",
            "attended-opening-and-fixed-producer",
            "contract-and-mechanical-activation",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--render-plan", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.render_plan:
        parser.error("only --render-plan exists in recovery loader H0")
    print(json.dumps(render_plan(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
