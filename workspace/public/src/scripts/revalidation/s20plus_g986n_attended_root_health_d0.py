#!/usr/bin/env python3
"""Attended root-health D0 for the exact SM-G986N/y2q target.

Live availability is controlled by the binding target contract and the
reviewed activation constant.  The command, parser, identity checks, and
private evidence owner remain fixed across that status boundary.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import stat
import sys
import time
from types import ModuleType
from typing import Any, Protocol, Sequence


VERSION = "s20plus-g986n-attended-root-health-d0-v1"
RESULT_SCHEMA = "s20plus_g986n_attended_root_health_d0_result_v1"
FAILURE_SCHEMA = "s20plus_g986n_attended_root_health_d0_failure_v1"
PLAN_SCHEMA = "s20plus_g986n_attended_root_health_d0_plan_v1"
PASS_VERDICT = "PASS_S20PLUS_G986N_ATTENDED_ROOT_HEALTH_D0"
FAIL_VERDICT = "FAIL_S20PLUS_G986N_ATTENDED_ROOT_HEALTH_D0_READ_CLOSED"
DORMANT_VERDICT = "STOP_S20PLUS_G986N_ATTENDED_ROOT_HEALTH_D0_NOT_ACTIVE"

# Review qualification must not change this value.  A later contract change,
# independent review, and identity rotation are required to activate it.
ATTENDED_ROOT_HEALTH_D0_ACTIVE = True

EXPECTED_MODEL = "SM-G986N"
EXPECTED_ADB_MODEL = "model:SM_G986N"
EXPECTED_DEVICE = "y2q"
EXPECTED_PRODUCT = "y2qksx"
EXPECTED_INCREMENTAL = "G986NKSS8IYC2"
EXPECTED_ADB_PATH = "/usr/lib/android-sdk/platform-tools/adb"
EXPECTED_ADB_SIZE = 716_968
EXPECTED_ADB_SHA256 = (
    "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
)

FIXED_PRIVATE_ROOT = Path(
    "workspace/private/runs/s20plus-g986n-attended-root-health-d0"
)
MAX_INVENTORY_BYTES = 32 * 1024
MAX_SNAPSHOT_BYTES = 8 * 1024
MAX_ROOT_TRANSCRIPT_BYTES = 4 * 1024
INVENTORY_TIMEOUT_SECONDS = 10.0
SNAPSHOT_TIMEOUT_SECONDS = 20.0
ROOT_TIMEOUT_SECONDS = 30.0

PUBLIC_SNAPSHOT_KEYS = (
    "model",
    "device",
    "product_name",
    "incremental",
    "boot_completed",
    "bootanim",
    "selinux",
    "boot_id",
)

PUBLIC_SNAPSHOT_SCRIPT = """set -eu
emit_prop() {
    printf '%s=' "$1"
    /system/bin/getprop "$2"
}
emit_prop model ro.product.model
emit_prop device ro.product.device
emit_prop product_name ro.product.name
emit_prop incremental ro.build.version.incremental
emit_prop boot_completed sys.boot_completed
emit_prop bootanim init.svc.bootanim
printf 'selinux='; /system/bin/getenforce
printf 'boot_id='; /system/bin/cat /proc/sys/kernel/random/boot_id
"""

PUBLIC_SHELL_ARGUMENT = PUBLIC_SNAPSHOT_SCRIPT

ROOT_OUTPUT_KEYS = (
    "uid",
    "gid",
    "context",
    "magisk_version",
    "magisk_version_code",
    "selinux",
    "pid1_exe",
    "pid1_context",
)

EXPECTED_ROOT_OUTPUT = {
    "uid": "0",
    "gid": "0",
    "context": "u:r:magisk:s0",
    "magisk_version": "30.7:MAGISK:R",
    "magisk_version_code": "30700",
    "selinux": "Enforcing",
    "pid1_exe": "/system/bin/init",
    "pid1_context": "u:r:init:s0",
}

ROOT_READ_SCRIPT = r"""set -eu
uid=$(/system/bin/id -u)
gid=$(/system/bin/id -g)
context=$(/system/bin/cat /proc/self/attr/current)
magisk_version=$(/data/adb/magisk/magisk -v)
magisk_version_code=$(/data/adb/magisk/magisk -V)
selinux=$(/system/bin/getenforce)
pid1_exe=$(/system/bin/readlink /proc/1/exe)
pid1_context=$(/system/bin/cat /proc/1/attr/current)
printf '%s\n' \
    "uid=$uid" \
    "gid=$gid" \
    "context=$context" \
    "magisk_version=$magisk_version" \
    "magisk_version_code=$magisk_version_code" \
    "selinux=$selinux" \
    "pid1_exe=$pid1_exe" \
    "pid1_context=$pid1_context"
"""

ROOT_SHELL_ARGUMENT = shlex.quote(ROOT_READ_SCRIPT)
EXPECTED_ROOT_STDOUT = "".join(
    f"{key}={EXPECTED_ROOT_OUTPUT[key]}\n" for key in ROOT_OUTPUT_KEYS
).encode("utf-8")

INVENTORY_HELPER_NAME = "s20plus_g986n_d0_inventory.py"
INVENTORY_HELPER_SIZE = 21_474
INVENTORY_HELPER_SHA256 = (
    "3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81"
)

_SAFE_PUBLIC_VALUE = re.compile(r"[^\x00\r\n]{0,4096}")
_ALLOWED_EVIDENCE_NAMES = frozenset(
    {"root-stdout.bin", "root-stderr.bin", "result.json", "failure.json"}
)
_EVIDENCE_MAXIMUMS = {
    "root-stdout.bin": MAX_ROOT_TRANSCRIPT_BYTES,
    "root-stderr.bin": MAX_ROOT_TRANSCRIPT_BYTES,
    "result.json": 64 * 1024,
    "failure.json": 64 * 1024,
}


class RootHealthD0Error(RuntimeError):
    """A fail-closed validation or evidence error."""


def _identity(value: os.stat_result) -> tuple[int, ...]:
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
    """Fields that remain stable when owned children are published."""

    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_uid,
        value.st_gid,
    )


def _read_direct_regular_source(
    path: Path, *, maximum: int = 2 * 1024 * 1024
) -> tuple[bytes, dict[str, Any]]:
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or not 0 <= before.st_size <= maximum
        ):
            raise RootHealthD0Error("source is not a bounded direct link-count-one file")
        payload = bytearray()
        while len(payload) < before.st_size:
            chunk = os.read(
                descriptor, min(1024 * 1024, before.st_size - len(payload))
            )
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) != before.st_size or os.read(descriptor, 1):
            raise RootHealthD0Error("source length changed while it was read")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = os.stat(path, follow_symlinks=False)
    if _identity(before) != _identity(after) or _identity(after) != _identity(current):
        raise RootHealthD0Error("source identity changed while it was read")
    data = bytes(payload)
    return data, {
        "path": str(path.resolve(strict=True)),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def normalized_source_sha256(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise RootHealthD0Error("runner source normalization requires exact bytes")
    normalized, count = re.subn(
        rb"^ATTENDED_ROOT_HEALTH_D0_ACTIVE = (?:False|True)$",
        b"ATTENDED_ROOT_HEALTH_D0_ACTIVE = <REVIEWED_ACTIVATION_BOOLEAN>",
        payload,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise RootHealthD0Error("runner activation normalization is ambiguous")
    return hashlib.sha256(normalized).hexdigest()


def self_receipt() -> dict[str, Any]:
    payload, receipt = _read_direct_regular_source(Path(__file__).resolve(strict=True))
    return {**receipt, "normalized_sha256": normalized_source_sha256(payload)}


def _direct_regular_receipt(
    path: Path, *, expected_size: int, expected_sha256: str
) -> dict[str, Any]:
    """Read a direct regular file without following its final path component."""

    digest = hashlib.sha256()
    size = 0
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise RootHealthD0Error("bound source is not a direct link-count-one file")
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > expected_size:
                raise RootHealthD0Error("bound source exceeds its pinned size")
            digest.update(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = os.stat(path, follow_symlinks=False)
    if _identity(before) != _identity(after) or _identity(after) != _identity(current):
        raise RootHealthD0Error("bound source changed while it was read")
    receipt = {
        "path": str(path.resolve(strict=True)),
        "size": size,
        "sha256": digest.hexdigest(),
    }
    if size != expected_size or receipt["sha256"] != expected_sha256:
        raise RootHealthD0Error("bound source does not match its pinned identity")
    return receipt


def _load_inventory_helper() -> tuple[ModuleType, dict[str, Any]]:
    path = Path(__file__).resolve().with_name(INVENTORY_HELPER_NAME)
    receipt = _direct_regular_receipt(
        path,
        expected_size=INVENTORY_HELPER_SIZE,
        expected_sha256=INVENTORY_HELPER_SHA256,
    )
    spec = importlib.util.spec_from_file_location(
        "_bound_s20plus_g986n_d0_inventory_for_root_health", path
    )
    if spec is None or spec.loader is None:
        raise RootHealthD0Error("cannot load the bound inventory helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if (
        _direct_regular_receipt(
            path,
            expected_size=INVENTORY_HELPER_SIZE,
            expected_sha256=INVENTORY_HELPER_SHA256,
        )
        != receipt
    ):
        raise RootHealthD0Error("bound inventory helper changed during import")
    return module, receipt


base, INVENTORY_HELPER_RECEIPT = _load_inventory_helper()


class Backend(Protocol):
    def tool_receipt(self) -> dict[str, Any]: ...

    def run(
        self, argv: list[str], timeout: float, maximum: int
    ) -> tuple[int, bytes, bytes]: ...


class FixedBackend:
    """The only backend constructed by the connected CLI."""

    def tool_receipt(self) -> dict[str, Any]:
        if not ATTENDED_ROOT_HEALTH_D0_ACTIVE:
            raise RootHealthD0Error("fixed connected backend is dormant")
        return base.tool_receipt(base.DEFAULT_ADB)

    def run(
        self, argv: list[str], timeout: float, maximum: int
    ) -> tuple[int, bytes, bytes]:
        if not ATTENDED_ROOT_HEALTH_D0_ACTIVE:
            raise RootHealthD0Error("fixed connected backend is dormant")
        return base.bounded_command(argv, timeout, maximum)


class CommandRecorder:
    _KINDS = frozenset({"inventory", "devpath", "snapshot", "root"})

    def __init__(self, backend: Backend):
        self.backend = backend
        self.host_command_count = 0
        self.inventory_command_count = 0
        self.selected_target_command_count = 0
        self.public_snapshot_command_count = 0
        self.root_command_count = 0
        self.root_transcript_digest: dict[str, Any] | None = None

    def run(
        self,
        kind: str,
        argv: list[str],
        timeout: float,
        maximum: int,
    ) -> tuple[int, bytes, bytes]:
        if kind not in self._KINDS:
            raise RootHealthD0Error("internal command kind is outside the fixed plan")
        self.host_command_count += 1
        if kind == "inventory":
            self.inventory_command_count += 1
        else:
            self.selected_target_command_count += 1
        if kind == "snapshot":
            self.public_snapshot_command_count += 1
        if kind == "root":
            self.root_command_count += 1
        return self.backend.run(argv, timeout, maximum)

    def evidence(self) -> dict[str, int]:
        return {
            "host_command_count": self.host_command_count,
            "inventory_command_count": self.inventory_command_count,
            "selected_target_command_count": self.selected_target_command_count,
            "public_snapshot_command_count": self.public_snapshot_command_count,
            "root_command_count": self.root_command_count,
            "other_target_command_count": 0,
            "s22plus_command_count": 0,
            "a90_command_count": 0,
        }

    def observe_root_transcript(
        self, returncode: int, stdout: bytes, stderr: bytes
    ) -> None:
        self.root_transcript_digest = {
            "returncode": returncode,
            "stdout_size": len(stdout),
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_size": len(stderr),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "raw_published": False,
        }


def _validate_adb_receipt(value: dict[str, Any]) -> dict[str, Any]:
    expected_keys = {"path", "device", "inode", "mtime_ns", "size", "sha256"}
    if type(value) is not dict or set(value) != expected_keys:
        raise RootHealthD0Error("ADB receipt schema is invalid")
    for key in ("device", "inode", "mtime_ns", "size"):
        if type(value[key]) is not int or value[key] < 0:
            raise RootHealthD0Error("ADB receipt contains an invalid integer")
    if (
        value["path"] != EXPECTED_ADB_PATH
        or value["size"] != EXPECTED_ADB_SIZE
        or value["sha256"] != EXPECTED_ADB_SHA256
    ):
        raise RootHealthD0Error("ADB receipt does not match the reviewed identity")
    return dict(value)


def _command_envelope(
    result: tuple[int, bytes, bytes], *, label: str, maximum: int
) -> tuple[int, bytes, bytes]:
    if type(result) is not tuple or len(result) != 3:
        raise RootHealthD0Error(f"{label} returned an invalid command envelope")
    returncode, stdout, stderr = result
    if type(returncode) is not int or type(returncode) is bool:
        raise RootHealthD0Error(f"{label} returned an invalid return code")
    if type(stdout) is not bytes or type(stderr) is not bytes:
        raise RootHealthD0Error(f"{label} returned non-byte output")
    if len(stdout) + len(stderr) > maximum:
        raise RootHealthD0Error(f"{label} exceeded its output bound")
    return returncode, stdout, stderr


def _successful_stdout(
    result: tuple[int, bytes, bytes], *, label: str, maximum: int
) -> bytes:
    returncode, stdout, stderr = _command_envelope(
        result, label=label, maximum=maximum
    )
    if returncode != 0:
        raise RootHealthD0Error(f"{label} failed")
    if stderr:
        raise RootHealthD0Error(f"{label} produced stderr")
    return stdout


def _decode_inventory(result: tuple[int, bytes, bytes], label: str) -> str:
    stdout = _successful_stdout(result, label=label, maximum=MAX_INVENTORY_BYTES)
    try:
        return stdout.decode("utf-8", "strict").strip()
    except UnicodeDecodeError as exc:
        raise RootHealthD0Error(f"{label} is not UTF-8") from exc


def _parse_devpath(result: tuple[int, bytes, bytes]) -> str:
    stdout = _successful_stdout(
        result, label="selected target devpath", maximum=MAX_INVENTORY_BYTES
    )
    try:
        text = stdout.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise RootHealthD0Error("selected target devpath is not UTF-8") from exc
    if not text.endswith("\n") or text.count("\n") != 1 or "\r" in text or "\x00" in text:
        raise RootHealthD0Error("selected target devpath framing is invalid")
    devpath = text[:-1]
    if base.DEVPATH_RE.fullmatch(devpath) is None:
        raise RootHealthD0Error("selected target devpath is malformed")
    return devpath


def _parse_ordered_lines(
    stdout: bytes,
    *,
    keys: Sequence[str],
    label: str,
) -> dict[str, str]:
    try:
        text = stdout.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise RootHealthD0Error(f"{label} is not UTF-8") from exc
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise RootHealthD0Error(f"{label} does not use canonical line framing")
    lines = text.splitlines()
    if len(lines) != len(keys):
        raise RootHealthD0Error(f"{label} has the wrong field count")
    values: dict[str, str] = {}
    for expected_key, line in zip(keys, lines, strict=True):
        if "=" not in line:
            raise RootHealthD0Error(f"{label} contains a malformed field")
        key, value = line.split("=", 1)
        if key != expected_key or key in values:
            raise RootHealthD0Error(f"{label} field order or name is invalid")
        if _SAFE_PUBLIC_VALUE.fullmatch(value) is None:
            raise RootHealthD0Error(f"{label} contains an invalid field value")
        values[key] = value
    return values


def parse_public_snapshot(result: tuple[int, bytes, bytes]) -> dict[str, str]:
    stdout = _successful_stdout(
        result,
        label="selected target public snapshot",
        maximum=MAX_SNAPSHOT_BYTES,
    )
    values = _parse_ordered_lines(
        stdout, keys=PUBLIC_SNAPSHOT_KEYS, label="selected target public snapshot"
    )
    expected = {
        "model": EXPECTED_MODEL,
        "device": EXPECTED_DEVICE,
        "product_name": EXPECTED_PRODUCT,
        "incremental": EXPECTED_INCREMENTAL,
        "boot_completed": "1",
        "bootanim": "stopped",
        "selinux": "Enforcing",
    }
    for key, expected_value in expected.items():
        if values[key] != expected_value:
            raise RootHealthD0Error("selected target public identity or health mismatched")
    if base.BOOT_ID_RE.fullmatch(values["boot_id"]) is None:
        raise RootHealthD0Error("selected target boot ID is malformed")
    return values


def parse_root_result(result: tuple[int, bytes, bytes]) -> dict[str, str]:
    stdout = _successful_stdout(
        result,
        label="selected target fixed root read",
        maximum=MAX_ROOT_TRANSCRIPT_BYTES,
    )
    if stdout != EXPECTED_ROOT_STDOUT:
        # Parse for a field-oriented failure classification, while still
        # requiring byte-exact canonical output for acceptance.
        values = _parse_ordered_lines(
            stdout, keys=ROOT_OUTPUT_KEYS, label="selected target fixed root read"
        )
        if values != EXPECTED_ROOT_OUTPUT:
            raise RootHealthD0Error("selected target fixed root values mismatched")
        raise RootHealthD0Error("selected target fixed root output is not canonical")
    return dict(EXPECTED_ROOT_OUTPUT)


def select_exact_target(rows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    required = {
        EXPECTED_ADB_MODEL,
        f"device:{EXPECTED_DEVICE}",
        f"product:{EXPECTED_PRODUCT}",
    }
    plausible = [row for row in rows if required & row["metadata"]]
    if len(plausible) != 1:
        raise RootHealthD0Error("exactly one plausible S20+ row is required")
    selected = plausible[0]
    if selected["state"] != "device" or not required <= selected["metadata"]:
        raise RootHealthD0Error("the plausible S20+ row is not exact and healthy")
    return selected


def parse_inventory(text: str) -> tuple[dict[str, Any], ...]:
    """Use the pinned parser and additionally reject collapsed duplicate tokens."""

    for line in text.splitlines():
        if not line or line.startswith("List of devices attached"):
            continue
        fields = line.split()
        if len(fields) >= 3 and len(fields[2:]) != len(set(fields[2:])):
            raise RootHealthD0Error("ADB inventory contains duplicate metadata tokens")
    return base.parse_inventory(text)


def _validate_snapshot_binding(
    snapshot: dict[str, str], selected: dict[str, Any]
) -> None:
    base.validate_snapshot_binding(snapshot, selected)
    if (
        snapshot["device"] != EXPECTED_DEVICE
        or snapshot["product_name"] != EXPECTED_PRODUCT
        or snapshot["incremental"] != EXPECTED_INCREMENTAL
    ):
        raise RootHealthD0Error("public snapshot conflicts with the exact target binding")


def _validate_devpath_binding(selected: dict[str, Any], devpath: str) -> None:
    usb_tokens = sorted(
        value for value in selected["metadata"] if value.startswith("usb:")
    )
    if len(usb_tokens) != 1 or usb_tokens[0] != devpath:
        raise RootHealthD0Error(
            "selected target inventory USB token conflicts with get-devpath"
        )


def _privacy_tokens(
    rows: tuple[dict[str, Any], ...], devpath: str, boot_id: str
) -> tuple[bytes, ...]:
    values = [row["serial"] for row in rows]
    values.extend((devpath, boot_id))
    return tuple(value.encode("utf-8") for value in values if value)


def _assert_private_tokens_absent(
    stdout: bytes, stderr: bytes, private_tokens: tuple[bytes, ...]
) -> None:
    combined = stdout + b"\x00" + stderr
    if any(token in combined for token in private_tokens):
        raise RootHealthD0Error("root transcript contains a private target identifier")


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")
        + b"\n"
    )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _ensure_fixed_private_root(repo: Path) -> Path:
    repo = repo.resolve(strict=True)
    current = repo
    for component in FIXED_PRIVATE_ROOT.parts:
        candidate = current / component
        created = False
        try:
            os.mkdir(candidate, 0o700)
            created = True
        except FileExistsError:
            pass
        observed = os.lstat(candidate)
        if not stat.S_ISDIR(observed.st_mode) or stat.S_ISLNK(observed.st_mode):
            raise RootHealthD0Error("fixed private evidence path contains an indirect node")
        if observed.st_uid != os.geteuid():
            raise RootHealthD0Error("fixed private evidence path has a foreign owner")
        if created:
            _fsync_directory(current)
        current = candidate
    if stat.S_IMODE(os.lstat(current).st_mode) != 0o700:
        raise RootHealthD0Error("fixed private evidence root mode is not 0700")
    return current


class EvidenceOwner:
    """Atomic no-replace publications inside one newly allocated private run."""

    def __init__(self, path: Path, descriptor: int, identity: tuple[int, ...]):
        self.path = path
        self._descriptor = descriptor
        self._identity = identity
        self.receipts: dict[str, dict[str, Any]] = {}

    @classmethod
    def allocate(cls, repo: Path) -> "EvidenceOwner":
        parent = _ensure_fixed_private_root(repo)
        for _attempt in range(32):
            name = (
                "d0-"
                + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                + f"-{time.time_ns()}-{secrets.token_hex(8)}"
            )
            run = parent / name
            try:
                os.mkdir(run, 0o700)
                break
            except FileExistsError:
                continue
        else:
            raise RootHealthD0Error("could not allocate a unique private run directory")
        observed = os.lstat(run)
        if (
            not stat.S_ISDIR(observed.st_mode)
            or stat.S_ISLNK(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != 0o700
            or observed.st_uid != os.geteuid()
        ):
            raise RootHealthD0Error("new private run directory identity is invalid")
        descriptor = os.open(
            run, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
        )
        pinned = os.fstat(descriptor)
        if _directory_identity(pinned) != _directory_identity(observed):
            os.close(descriptor)
            raise RootHealthD0Error("private run directory changed during allocation")
        if os.listdir(descriptor):
            os.close(descriptor)
            raise RootHealthD0Error("new private run directory is not empty")
        _fsync_directory(parent)
        return cls(run, descriptor, _directory_identity(pinned))

    def close(self) -> None:
        if self._descriptor >= 0:
            os.close(self._descriptor)
            self._descriptor = -1

    def __enter__(self) -> "EvidenceOwner":
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _traceback: Any) -> None:
        self.close()

    def _validate_directory(self) -> None:
        if (
            self._descriptor < 0
            or _directory_identity(os.fstat(self._descriptor)) != self._identity
        ):
            raise RootHealthD0Error("private run directory identity changed")
        if set(os.listdir(self._descriptor)) != set(self.receipts):
            raise RootHealthD0Error("private run evidence namespace changed")

    def publish(self, name: str, payload: bytes) -> dict[str, Any]:
        if name not in _ALLOWED_EVIDENCE_NAMES or type(payload) is not bytes:
            raise RootHealthD0Error("evidence publication is outside the fixed namespace")
        if len(payload) > _EVIDENCE_MAXIMUMS[name]:
            raise RootHealthD0Error("private evidence exceeds its fixed file bound")
        self._validate_directory()
        temporary = f".tmp-{secrets.token_hex(16)}"
        descriptor = -1
        linked = False
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | os.O_CLOEXEC
                | os.O_NOFOLLOW,
                0o400,
                dir_fd=self._descriptor,
            )
            offset = 0
            while offset < len(payload):
                written = os.write(descriptor, payload[offset:])
                if written <= 0:
                    raise RootHealthD0Error("short private evidence write")
                offset += written
            os.fsync(descriptor)
            staged = os.fstat(descriptor)
            if (
                not stat.S_ISREG(staged.st_mode)
                or stat.S_IMODE(staged.st_mode) != 0o400
                or staged.st_nlink != 1
                or staged.st_uid != os.geteuid()
                or staged.st_size != len(payload)
            ):
                raise RootHealthD0Error("staged private evidence identity is invalid")
            os.link(
                temporary,
                name,
                src_dir_fd=self._descriptor,
                dst_dir_fd=self._descriptor,
                follow_symlinks=False,
            )
            linked = True
            os.unlink(temporary, dir_fd=self._descriptor)
            os.fsync(self._descriptor)
        except Exception:
            try:
                os.unlink(temporary, dir_fd=self._descriptor)
            except FileNotFoundError:
                pass
            raise
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        if not linked:
            raise RootHealthD0Error("private evidence was not atomically published")
        final_descriptor = os.open(
            name,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=self._descriptor,
        )
        try:
            final = os.fstat(final_descriptor)
            observed = bytearray()
            while len(observed) <= len(payload):
                chunk = os.read(final_descriptor, min(1024 * 1024, len(payload) + 1))
                if not chunk:
                    break
                observed.extend(chunk)
        finally:
            os.close(final_descriptor)
        if (
            not stat.S_ISREG(final.st_mode)
            or stat.S_IMODE(final.st_mode) != 0o400
            or final.st_nlink != 1
            or final.st_uid != os.geteuid()
            or bytes(observed) != payload
        ):
            raise RootHealthD0Error("published private evidence identity is invalid")
        if set(os.listdir(self._descriptor)) != set(self.receipts) | {name}:
            raise RootHealthD0Error("private run evidence namespace changed after publication")
        receipt = {
            "name": name,
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "mode": "0400",
            "link_count": 1,
        }
        self.receipts[name] = receipt
        return dict(receipt)

    def publish_json(self, name: str, value: dict[str, Any]) -> dict[str, Any]:
        return self.publish(name, _json_bytes(value))


def collect(recorder: CommandRecorder, evidence: EvidenceOwner | None = None) -> dict[str, Any]:
    runner_receipt = self_receipt()
    receipt = _validate_adb_receipt(recorder.backend.tool_receipt())
    adb = receipt["path"]

    first_inventory_text = _decode_inventory(
        recorder.run(
            "inventory",
            [adb, "devices", "-l"],
            INVENTORY_TIMEOUT_SECONDS,
            MAX_INVENTORY_BYTES,
        ),
        "initial ADB inventory",
    )
    first_rows = parse_inventory(first_inventory_text)
    selected = select_exact_target(first_rows)
    serial = selected["serial"]

    devpath = _parse_devpath(
        recorder.run(
            "devpath",
            [adb, "-s", serial, "get-devpath"],
            INVENTORY_TIMEOUT_SECONDS,
            MAX_INVENTORY_BYTES,
        )
    )
    _validate_devpath_binding(selected, devpath)

    pre_snapshot = parse_public_snapshot(
        recorder.run(
            "snapshot",
            [adb, "-s", serial, "exec-out", "sh", "-c", PUBLIC_SHELL_ARGUMENT],
            SNAPSHOT_TIMEOUT_SECONDS,
            MAX_SNAPSHOT_BYTES,
        )
    )
    _validate_snapshot_binding(pre_snapshot, selected)

    root_result = recorder.run(
        "root",
        [adb, "-s", serial, "shell", "su", "-c", ROOT_SHELL_ARGUMENT],
        ROOT_TIMEOUT_SECONDS,
        MAX_ROOT_TRANSCRIPT_BYTES,
    )
    root_rc, root_stdout, root_stderr = _command_envelope(
        root_result,
        label="selected target fixed root read",
        maximum=MAX_ROOT_TRANSCRIPT_BYTES,
    )
    recorder.observe_root_transcript(root_rc, root_stdout, root_stderr)
    _assert_private_tokens_absent(
        root_stdout,
        root_stderr,
        _privacy_tokens(first_rows, devpath, pre_snapshot["boot_id"]),
    )
    root_health = parse_root_result(root_result)
    if evidence is not None:
        evidence.publish("root-stdout.bin", root_stdout)
        evidence.publish("root-stderr.bin", root_stderr)
        if recorder.root_transcript_digest is not None:
            recorder.root_transcript_digest["raw_published"] = True

    post_snapshot = parse_public_snapshot(
        recorder.run(
            "snapshot",
            [adb, "-s", serial, "exec-out", "sh", "-c", PUBLIC_SHELL_ARGUMENT],
            SNAPSHOT_TIMEOUT_SECONDS,
            MAX_SNAPSHOT_BYTES,
        )
    )
    _validate_snapshot_binding(post_snapshot, selected)
    if post_snapshot != pre_snapshot:
        raise RootHealthD0Error("public target identity or boot changed across root read")

    final_inventory_text = _decode_inventory(
        recorder.run(
            "inventory",
            [adb, "devices", "-l"],
            INVENTORY_TIMEOUT_SECONDS,
            MAX_INVENTORY_BYTES,
        ),
        "final ADB inventory",
    )
    final_rows = parse_inventory(final_inventory_text)
    final_selected = select_exact_target(final_rows)
    _validate_devpath_binding(final_selected, devpath)
    if (
        final_selected["serial"] != serial
        or base.sanitized_inventory(final_rows) != base.sanitized_inventory(first_rows)
    ):
        raise RootHealthD0Error("selected target or global inventory changed during read")
    if _validate_adb_receipt(recorder.backend.tool_receipt()) != receipt:
        raise RootHealthD0Error("ADB tool changed during the fixed read")
    if self_receipt() != runner_receipt:
        raise RootHealthD0Error("runner source changed during the fixed read")

    counts = recorder.evidence()
    expected_counts = {
        "host_command_count": 6,
        "inventory_command_count": 2,
        "selected_target_command_count": 4,
        "public_snapshot_command_count": 2,
        "root_command_count": 1,
        "other_target_command_count": 0,
        "s22plus_command_count": 0,
        "a90_command_count": 0,
    }
    if counts != expected_counts:
        raise RootHealthD0Error("command counts do not match the fixed six-invocation plan")

    public_health = dict(pre_snapshot)
    boot_id = public_health.pop("boot_id")
    sanitized = base.sanitized_inventory(first_rows)
    raw_evidence = {} if evidence is None else dict(evidence.receipts)
    return {
        "schema": RESULT_SCHEMA,
        "version": VERSION,
        "mode": "connected-attended-root-read-only",
        "risk_tier": "D0-attended-root-read-only",
        "target": {
            "model": EXPECTED_MODEL,
            "device": EXPECTED_DEVICE,
            "product_name": EXPECTED_PRODUCT,
            "incremental": EXPECTED_INCREMENTAL,
            "adb_serial_sha256": base.sha256_text(serial),
            "usb_topology_sha256": base.sha256_text(devpath),
            "boot_id_sha256": base.sha256_text(boot_id),
            "other_serial_sha256": sorted(
                base.sha256_text(row["serial"])
                for row in first_rows
                if row["serial"] != serial
            ),
            "inventory_sha256": base.sha256_text(
                json.dumps(sanitized, sort_keys=True, separators=(",", ":"))
            ),
        },
        "public_health": public_health,
        "root_health": root_health,
        "host_tool": receipt,
        "dependency_closure": {
            "runner": runner_receipt,
            "inventory_helper": INVENTORY_HELPER_RECEIPT,
        },
        "private_raw_evidence": raw_evidence,
        **counts,
        "device_effect_count": 0,
        "device_writes": False,
        "root_used": True,
        "root_writes": False,
        "reboot_requested": False,
        "mode_transition_requested": False,
        "payload_transfer": False,
        "partition_access": False,
        "package_operation": False,
        "property_or_service_change": False,
        "d1_authorized": False,
        "r1_authorized": False,
        "f1_authorized": False,
        "verdict": PASS_VERDICT,
    }


def failure_result(
    recorder: CommandRecorder, exc: Exception, evidence: EvidenceOwner | None
) -> dict[str, Any]:
    signature = f"{type(exc).__name__}:{exc}".encode("utf-8", "replace")
    counts = recorder.evidence()
    return {
        "schema": FAILURE_SCHEMA,
        "version": VERSION,
        "mode": "connected-attended-root-read-only-failed",
        "failure_class": type(exc).__name__,
        "failure_signature_sha256": hashlib.sha256(signature).hexdigest(),
        "private_raw_evidence": {} if evidence is None else dict(evidence.receipts),
        "root_transcript_digest": recorder.root_transcript_digest,
        **counts,
        "device_contact_started": counts["host_command_count"] > 0,
        "device_effect_count": 0,
        "device_writes": False,
        "root_used": counts["root_command_count"] > 0,
        "root_writes": False,
        "reboot_requested": False,
        "mode_transition_requested": False,
        "payload_transfer": False,
        "partition_access": False,
        "package_operation": False,
        "property_or_service_change": False,
        "d1_authorized": False,
        "r1_authorized": False,
        "f1_authorized": False,
        "verdict": FAIL_VERDICT,
    }


def render_plan() -> dict[str, Any]:
    return {
        "schema": PLAN_SCHEMA,
        "version": VERSION,
        "status": (
            "ACTIVE_ATTENDED_ROOT_HEALTH_D0"
            if ATTENDED_ROOT_HEALTH_D0_ACTIVE
            else "DORMANT_NOT_ACTIVE"
        ),
        "mode": "render-plan-device-hidden",
        "attended_root_health_d0_active": ATTENDED_ROOT_HEALTH_D0_ACTIVE,
        "expected_target": {
            "model": EXPECTED_MODEL,
            "device": EXPECTED_DEVICE,
            "product_name": EXPECTED_PRODUCT,
            "incremental": EXPECTED_INCREMENTAL,
        },
        "fixed_private_root": str(FIXED_PRIVATE_ROOT),
        "fixed_invocation_order": [
            "global-inventory",
            "selected-get-devpath",
            "selected-public-pre-snapshot",
            "selected-fixed-su-read",
            "selected-public-post-snapshot",
            "global-final-inventory",
        ],
        "public_snapshot_keys": list(PUBLIC_SNAPSHOT_KEYS),
        "public_snapshot_script_sha256": hashlib.sha256(
            PUBLIC_SNAPSHOT_SCRIPT.encode("utf-8")
        ).hexdigest(),
        "public_snapshot_shell_argument_sha256": hashlib.sha256(
            PUBLIC_SHELL_ARGUMENT.encode("utf-8")
        ).hexdigest(),
        "public_snapshot_transport": [
            "exec-out",
            "sh",
            "-c",
            "<single-raw-fixed-script-argv-ADB-escaped-once>",
        ],
        "root_output_keys": list(ROOT_OUTPUT_KEYS),
        "expected_root_output": dict(EXPECTED_ROOT_OUTPUT),
        "root_script_sha256": hashlib.sha256(
            ROOT_READ_SCRIPT.encode("utf-8")
        ).hexdigest(),
        "root_transport": ["shell", "su", "-c", "<single-shlex-quoted-fixed-literal>"],
        "root_timeout_seconds": ROOT_TIMEOUT_SECONDS,
        "root_transcript_maximum_bytes": MAX_ROOT_TRANSCRIPT_BYTES,
        "dependency_closure": {
            "runner": self_receipt(),
            "inventory_helper": INVENTORY_HELPER_RECEIPT,
            "adb": {
                "path": EXPECTED_ADB_PATH,
                "size": EXPECTED_ADB_SIZE,
                "sha256": EXPECTED_ADB_SHA256,
            },
        },
        "planned_counts": {
            "host_command_count": 6,
            "inventory_command_count": 2,
            "selected_target_command_count": 4,
            "public_snapshot_command_count": 2,
            "root_command_count": 1,
            "other_target_command_count": 0,
            "s22plus_command_count": 0,
            "a90_command_count": 0,
            "device_effect_count": 0,
        },
        "device_writes": False,
        "root_writes": False,
        "reboot_requested": False,
        "mode_transition_requested": False,
        "payload_transfer": False,
        "partition_access": False,
        "live_authorized": ATTENDED_ROOT_HEALTH_D0_ACTIVE,
    }


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--render-plan", action="store_true")
    mode.add_argument("--connected", action="store_true")
    return parser


def _execute_connected() -> int:
    if not ATTENDED_ROOT_HEALTH_D0_ACTIVE:
        print(DORMANT_VERDICT)
        return 2
    recorder = CommandRecorder(FixedBackend())
    try:
        owner = EvidenceOwner.allocate(repo_root())
    except Exception:
        print("FAIL_S20PLUS_G986N_ATTENDED_ROOT_HEALTH_D0_EVIDENCE_ALLOCATION")
        return 1
    with owner:
        try:
            result = collect(recorder, owner)
            owner.publish_json("result.json", result)
        except Exception as exc:
            try:
                owner.publish_json("failure.json", failure_result(recorder, exc, owner))
            except Exception:
                print("FAIL_S20PLUS_G986N_ATTENDED_ROOT_HEALTH_D0_EVIDENCE_WRITE")
                return 1
            print(FAIL_VERDICT)
            print(f"failure={owner.path / 'failure.json'}")
            return 1
        print(PASS_VERDICT)
        print(f"result={owner.path / 'result.json'}")
        return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.render_plan:
        print(json.dumps(render_plan(), indent=2, sort_keys=True))
        return 0
    if not ATTENDED_ROOT_HEALTH_D0_ACTIVE:
        print(DORMANT_VERDICT)
        return 2
    return _execute_connected()


if __name__ == "__main__":
    raise SystemExit(main())
