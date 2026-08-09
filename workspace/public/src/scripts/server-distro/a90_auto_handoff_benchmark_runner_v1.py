#!/usr/bin/env python3
"""One-ordinal attended A90 auto-handoff benchmark runner.

The runner consumes an installed-resident D1 manifest.  It proves the H10
resident healthy and unarmed, durably binds one arm intent, arms once, proves
the exact enable state, durably binds one reboot intent, reboots once, observes
Debian PID1/display/SSH, automatic native return, the retained latch, final
resident health, and one complete benchmark boot segment.  An uncertain arm or
reboot is never resent.  ``--reconcile`` is read-only; an exact historical-
closure resume can continue only from one proved armed result or a durably
observed return.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import shlex
import shutil
import stat
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_boot_benchmark_v1 as benchmark  # noqa: E402
import a90_ondevice_evidence_v1 as ondevice_evidence  # noqa: E402
import a90_phase3_d1_observer_v1 as phase3_observer  # noqa: E402
import a90_transition_d1_session_v1 as resident  # noqa: E402
import a90_v3403_f1_orchestrator as base  # noqa: E402


SCHEMA = "a90-auto-handoff-benchmark-runner-v3"
JOURNAL_SCHEMA = "a90-auto-handoff-benchmark-journal-v3"
RESULT_SCHEMA = "a90-auto-handoff-benchmark-result-v3"
RECONCILE_SCHEMA = "a90-auto-handoff-benchmark-reconciliation-v3"
EXPECTED_VERSION = "0.11.178"
EXPECTED_BUILD = (
    "phase3-minimal-h10-fast-source-receipt-auto-benchmark"
)
EXPECTED_ROOTFS_SHA256 = (
    "38d9ce41503483996d14a18fb51275fbbe47e898ce51aee37f9f88b61295018e"
)
ARM_TOKEN = "AUTO-HANDOFF-BENCHMARK-V1-ARM"
SOURCE_RECEIPT_SCHEMA = "a90-d3-source-receipt-v1"
SOURCE_RECEIPT_PATH = "/cache/a90-source-receipt-phase3-minimal-h10"
FAST_SOURCE_STATES = {"receipt-absent", "receipt-verified"}
FAST_SOURCE_MARKER_RE = re.compile(
    r"^A90D1_FAST_SOURCE state=(?P<state>receipt-(?:absent|verified)) "
    r"work_absent=1 temp_absent=1 "
    r"dev=(?P<dev>[0-9]+) ino=(?P<ino>[0-9]+) "
    r"size=(?P<size>[0-9]+) mode=(?P<mode>[0-9]+) "
    r"uid=(?P<uid>[0-9]+) gid=(?P<gid>[0-9]+) "
    r"nlink=(?P<nlink>[0-9]+) "
    r"mtime_sec=(?P<mtime_sec>[0-9]+) "
    r"mtime_nsec=(?P<mtime_nsec>[0-9]+) "
    r"ctime_sec=(?P<ctime_sec>[0-9]+) "
    r"ctime_nsec=(?P<ctime_nsec>[0-9]+)$"
)
FAST_RECEIPT_MARKER_RE = re.compile(r"^A90D1_FAST_RECEIPT exact=1$")
FAST_SOURCE_IDENTITY_KEYS = (
    "dev", "ino", "size", "mode", "uid", "gid", "nlink",
    "mtime_sec", "mtime_nsec", "ctime_sec", "ctime_nsec",
)
CMDV1X_BUFFER_BYTES = 4096
ARMED_RESUME_PREDECESSOR_CLOSURE_SHA256 = (
    "85dc18125032f8d0cf3bcdd1117261dd5a6d0af2bf95afd56904135341aa95ce"
)
HISTORICAL_H10_TERMINAL_CLOSURE_SHA256 = (
    "1562ffe1b7a6577ee28bba5bdba21bbc6734eaa427764982c068d2ab70751919"
)
STATUS_RE = re.compile(
    r"^A90AUTO_STATUS binding=(?P<binding>[01]) "
    r"enable=(?P<enable>-?[0-9]+) latch=(?P<latch>-?[0-9]+) "
    r"build=(?P<build>[a-z0-9._-]+)\r?$",
    re.MULTILINE,
)
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
USB_TOPOLOGY_RE = re.compile(r"^[0-9]+-[0-9]+(?:\.[0-9]+)*$")
PRE_REBOOT_OBSERVER_BINDING_SCHEMA = "a90-pre-reboot-observer-binding-v1"
POST_REBOOT_NCM_IDENTITY_SCHEMA = "a90-post-reboot-ncm-identity-v1"
SYS_CLASS_TTY = Path("/sys/class/tty")
SYS_CLASS_NET = Path("/sys/class/net")
EXECUTION_SOURCES = {
    "runner": Path(__file__).resolve(),
    "benchmark_parser": SCRIPT_DIR / "a90_boot_benchmark_v1.py",
    "ondevice_evidence": SCRIPT_DIR / "a90_ondevice_evidence_v1.py",
    "resident_manifest_loader": SCRIPT_DIR / "a90_transition_d1_session_v1.py",
    "resident_f1_loader": SCRIPT_DIR / "a90_v3403_f1_orchestrator.py",
}
JOURNAL_NAMES = (
    "0000-open.json",
    "0001-arm-intent.json",
    "0002-arm-result.json",
    "0003-reboot-intent.json",
    "0004-observation.json",
    "0005-absence-intent.json",
    "0006-absence-result.json",
    "0007-final-health.json",
    "0008-result.json",
)
JOURNAL_ACTIONS = (
    "open-native-healthy-unarmed",
    "arm-intent",
    "arm-result",
    "reboot-intent",
    "observation",
    "absence-close-intent",
    "absence-close-result",
    "final-health",
    "closed",
)
COMMON_RECORD_KEYS = {"schema", "action", "timestamp_utc"}
PAYLOAD_KEYS = (
    {
        "manifest_sha256", "execution_closure", "candidate_sha256",
        "rollback_sha256", "rootfs_sha256", "opening_preflight",
        "auto_status", "auto_status_record", "first_boot_log",
        "first_boot_log_sha256", "first_boot_unarmed",
    },
    {
        "manifest_sha256", "execution_closure_sha256",
        "arm_dispatch_count_max", "reboot_dispatch_count", "candidate_replay",
    },
    {
        "intent_sha256", "arm_dispatch_count", "arm_record",
        "post_arm_status_record", "post_arm_status",
    },
    {
        "intent_sha256", "execution_closure_sha256", "armed_preflight", "pre_reboot_epoch",
        "reboot_dispatch_count_max", "candidate_replay",
    },
    {
        "intent_sha256", "arm_dispatch_count", "reboot_dispatch_count",
        "candidate_replay", "observation",
    },
    {
        "intent_sha256", "manifest_sha256", "cleanup_dispatch_count_max",
        "arm_dispatch_count", "reboot_dispatch_count", "candidate_replay",
        "returned_status", "returned_status_record",
    },
    {
        "intent_sha256", "cleanup_dispatch_count", "cleanup_record",
        "absence_preflight", "inferred_from_absence", "candidate_replay",
    },
    {"intent_sha256", "result_sha256", "result"},
    {"result_sha256", "result"},
)


class ContractError(RuntimeError):
    """Raised before widening, replaying, or misclassifying a D1 effect."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def exact_int(value: Any, expected: int) -> bool:
    return type(value) is int and value == expected


def execution_closure() -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    digest = hashlib.sha256()
    for role, requested in sorted(EXECUTION_SOURCES.items()):
        path = requested.resolve()
        info = path.stat()
        if requested.is_symlink() or not stat.S_ISREG(info.st_mode):
            raise ContractError(f"execution source is not one regular file: {role}")
        try:
            relative = path.relative_to(REPO_ROOT).as_posix()
        except ValueError as exc:
            raise ContractError("execution source escapes repository") from exc
        file_sha256 = sha256_file(path)
        files[role] = {
            "path": relative,
            "size": info.st_size,
            "sha256": file_sha256,
        }
        digest.update(role.encode("utf-8"))
        digest.update(b"\0")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(info.st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(file_sha256.encode("ascii"))
        digest.update(b"\0")
    return {"sha256": digest.hexdigest(), "files": files}


def validate_recorded_execution_closure(
    value: Any,
    expected_sha256: str,
) -> dict[str, Any]:
    """Validate a durable historical closure without rebinding current files."""

    if HEX64_RE.fullmatch(expected_sha256 or "") is None:
        raise ContractError("historical execution closure SHA256 is not exact")
    if not isinstance(value, dict) or set(value) != {"sha256", "files"}:
        raise ContractError("historical execution closure is not exact")
    files = value.get("files")
    if not isinstance(files, dict) or set(files) != set(EXECUTION_SOURCES):
        raise ContractError("historical execution closure roles changed")
    digest = hashlib.sha256()
    for role, requested in sorted(EXECUTION_SOURCES.items()):
        record = files.get(role)
        relative = requested.resolve().relative_to(REPO_ROOT).as_posix()
        if (
            not isinstance(record, dict)
            or set(record) != {"path", "size", "sha256"}
            or record.get("path") != relative
            or type(record.get("size")) is not int
            or record.get("size") < 1
            or HEX64_RE.fullmatch(str(record.get("sha256") or "")) is None
        ):
            raise ContractError(f"historical execution closure role changed: {role}")
        digest.update(role.encode("utf-8"))
        digest.update(b"\0")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record["size"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(record["sha256"].encode("ascii"))
        digest.update(b"\0")
    if value.get("sha256") != expected_sha256 or digest.hexdigest() != expected_sha256:
        raise ContractError("historical execution closure digest changed")
    return value


def require_execution_closure(expected_sha256: str) -> dict[str, Any]:
    if HEX64_RE.fullmatch(expected_sha256 or "") is None:
        raise ContractError("expected execution closure SHA256 is not exact")
    value = execution_closure()
    if value["sha256"] != expected_sha256:
        raise ContractError(
            "execution closure changed: "
            f"got {value['sha256']} expected {expected_sha256}"
        )
    return value


def write_record(path: Path, action: str, payload: dict[str, Any]) -> None:
    if COMMON_RECORD_KEYS.intersection(payload):
        raise ContractError("journal payload attempts to replace common keys")
    resident.write_private_json_exclusive(
        path,
        {
            "schema": JOURNAL_SCHEMA,
            "action": action,
            "timestamp_utc": resident.utc_now(),
            **payload,
        },
    )


def exact_transaction_dir(spec: resident.SessionSpec, requested: Path) -> Path:
    path = requested.resolve()
    if path != spec.transaction_dir.resolve():
        raise ContractError("transaction directory differs from D1 manifest binding")
    try:
        path.relative_to(resident.PRIVATE_RUN_BASE)
    except ValueError as exc:
        raise ContractError("transaction directory escapes private A90 run root") from exc
    return path


def require_bounded_run_script(script: str) -> str:
    command = ["run", "/bin/busybox", "sh", "-c", script]
    wire = base.a90ctl.encode_cmdv1_line(command)
    if len(wire.encode("utf-8")) >= CMDV1X_BUFFER_BYTES:
        raise ContractError("H10 read-only cmdv1x script exceeds native buffer")
    return script


def fast_source_preflight_script(
    spec: resident.SessionSpec,
    *,
    expected_state: str,
) -> str:
    """Inspect the H10 source/receipt identity without hashing source data."""

    if expected_state not in FAST_SOURCE_STATES:
        raise ContractError("fast source preflight state is not exact")
    if (
        spec.candidate_version != EXPECTED_VERSION
        or spec.candidate_build != EXPECTED_BUILD
        or spec.rootfs.sha256 != EXPECTED_ROOTFS_SHA256
        or base.FAST_SOURCE_RECEIPT_PATHS.get(
            (spec.candidate_version, spec.candidate_build)
        ) != SOURCE_RECEIPT_PATH
    ):
        raise ContractError("fast source receipt binding is not exact H10")
    final = shlex.quote(spec.remote_final)
    work = shlex.quote(spec.remote_work)
    receipt = shlex.quote(SOURCE_RECEIPT_PATH)
    expected_size = shlex.quote(str(spec.rootfs.size))
    state_checks = (
        (
            '[ ! -e "$RECEIPT" ]',
            '[ ! -L "$RECEIPT" ]',
        )
        if expected_state == "receipt-absent"
        else (
            '[ -f "$RECEIPT" ]',
            '[ ! -L "$RECEIPT" ]',
        )
    )
    script = "\n".join(
        (
            "set -eu",
            f"FINAL={final}",
            f"WORK={work}",
            f"RECEIPT={receipt}",
            'RECEIPT_TMP="$RECEIPT.tmp"',
            f"EXPECTED_SIZE={expected_size}",
            '[ -f "$FINAL" ]',
            '[ ! -L "$FINAL" ]',
            '[ ! -e "$WORK" ]',
            '[ ! -L "$WORK" ]',
            '[ ! -e "$RECEIPT_TMP" ]',
            '[ ! -L "$RECEIPT_TMP" ]',
            'SOURCE_DEV=$(/bin/busybox stat -c %d "$FINAL")',
            'SOURCE_INO=$(/bin/busybox stat -c %i "$FINAL")',
            'SOURCE_SIZE=$(/bin/busybox stat -c %s "$FINAL")',
            '[ "$SOURCE_SIZE" = "$EXPECTED_SIZE" ]',
            'SOURCE_MODE_HEX=$(/bin/busybox stat -c %f "$FINAL")',
            'SOURCE_MODE=$((0x$SOURCE_MODE_HEX))',
            'SOURCE_UID=$(/bin/busybox stat -c %u "$FINAL")',
            'SOURCE_GID=$(/bin/busybox stat -c %g "$FINAL")',
            'SOURCE_NLINK=$(/bin/busybox stat -c %h "$FINAL")',
            'SOURCE_MTIME_SEC=$(/bin/busybox stat -c %Y "$FINAL")',
            'SOURCE_MTIME_TEXT=$(/bin/busybox stat -c %y "$FINAL")',
            'SOURCE_MTIME_NSEC=${SOURCE_MTIME_TEXT#*.}',
            '[ "$SOURCE_MTIME_NSEC" != "$SOURCE_MTIME_TEXT" ]',
            'SOURCE_MTIME_NSEC=${SOURCE_MTIME_NSEC%% *}',
            'SOURCE_CTIME_SEC=$(/bin/busybox stat -c %Z "$FINAL")',
            'SOURCE_CTIME_TEXT=$(/bin/busybox stat -c %z "$FINAL")',
            'SOURCE_CTIME_NSEC=${SOURCE_CTIME_TEXT#*.}',
            '[ "$SOURCE_CTIME_NSEC" != "$SOURCE_CTIME_TEXT" ]',
            'SOURCE_CTIME_NSEC=${SOURCE_CTIME_NSEC%% *}',
            'case "$SOURCE_MTIME_NSEC" in ""|*[!0-9]*) exit 1 ;; esac',
            'case "$SOURCE_CTIME_NSEC" in ""|*[!0-9]*) exit 1 ;; esac',
            'SOURCE_MTIME_NSEC=$((10#$SOURCE_MTIME_NSEC))',
            'SOURCE_CTIME_NSEC=$((10#$SOURCE_CTIME_NSEC))',
            *state_checks,
            f"echo A90D1_FAST_SOURCE state={expected_state} "
            'work_absent=1 temp_absent=1 '
            'dev=$SOURCE_DEV ino=$SOURCE_INO size=$SOURCE_SIZE '
            'mode=$SOURCE_MODE uid=$SOURCE_UID gid=$SOURCE_GID '
            'nlink=$SOURCE_NLINK mtime_sec=$SOURCE_MTIME_SEC '
            'mtime_nsec=$SOURCE_MTIME_NSEC ctime_sec=$SOURCE_CTIME_SEC '
            'ctime_nsec=$SOURCE_CTIME_NSEC',
        )
    )
    return require_bounded_run_script(script)


def fast_receipt_content_script(
    spec: resident.SessionSpec,
    source_identity: dict[str, int],
) -> str:
    """Verify the exact native receipt in a separate bounded cmdv1x call."""

    if (
        set(source_identity) != set(FAST_SOURCE_IDENTITY_KEYS)
        or any(type(source_identity[key]) is not int or source_identity[key] < 0
               for key in FAST_SOURCE_IDENTITY_KEYS)
        or source_identity["size"] != spec.rootfs.size
    ):
        raise ContractError("fast receipt source identity is not exact")
    receipt_text = "\n".join(
        (
            f"schema={SOURCE_RECEIPT_SCHEMA}",
            f"image={spec.remote_final}",
            f"sha256={spec.rootfs.sha256}",
            *(f"{key}={source_identity[key]}" for key in FAST_SOURCE_IDENTITY_KEYS),
        )
    )
    receipt = shlex.quote(SOURCE_RECEIPT_PATH)
    final = shlex.quote(spec.remote_final)
    work = shlex.quote(spec.remote_work)
    expected = shlex.quote(receipt_text)
    script = "\n".join(
        (
            "set -eu",
            f"R={receipt}",
            f"F={final}",
            f"W={work}",
            'T="$R.tmp"',
            '[ -f "$F" ]',
            '[ ! -L "$F" ]',
            '[ ! -e "$W" ]',
            '[ ! -L "$W" ]',
            f'[ "$(/bin/busybox stat -c %d "$F")" = {source_identity["dev"]} ]',
            f'[ "$(/bin/busybox stat -c %i "$F")" = {source_identity["ino"]} ]',
            f'[ "$(/bin/busybox stat -c %s "$F")" = {source_identity["size"]} ]',
            'MF=$(/bin/busybox stat -c %f "$F")',
            f'[ "$((0x$MF))" = {source_identity["mode"]} ]',
            f'[ "$(/bin/busybox stat -c %u "$F")" = {source_identity["uid"]} ]',
            f'[ "$(/bin/busybox stat -c %g "$F")" = {source_identity["gid"]} ]',
            f'[ "$(/bin/busybox stat -c %h "$F")" = {source_identity["nlink"]} ]',
            f'[ "$(/bin/busybox stat -c %Y "$F")" = {source_identity["mtime_sec"]} ]',
            'MT=$(/bin/busybox stat -c %y "$F"); MN=${MT#*.}; MN=${MN%% *}',
            'case "$MN" in ""|*[!0-9]*) exit 1 ;; esac',
            f'[ "$((10#$MN))" = {source_identity["mtime_nsec"]} ]',
            f'[ "$(/bin/busybox stat -c %Z "$F")" = {source_identity["ctime_sec"]} ]',
            'CT=$(/bin/busybox stat -c %z "$F"); CN=${CT#*.}; CN=${CN%% *}',
            'case "$CN" in ""|*[!0-9]*) exit 1 ;; esac',
            f'[ "$((10#$CN))" = {source_identity["ctime_nsec"]} ]',
            '[ -f "$R" ]',
            '[ ! -L "$R" ]',
            '[ ! -e "$T" ]',
            '[ ! -L "$T" ]',
            '[ "$(/bin/busybox stat -c %u "$R")" = 0 ]',
            '[ "$(/bin/busybox stat -c %g "$R")" = 0 ]',
            '[ "$(/bin/busybox stat -c %h "$R")" = 1 ]',
            '[ "$(/bin/busybox stat -c %a "$R")" = 600 ]',
            '[ "$(/bin/busybox wc -l < "$R")" = 14 ]',
            f"E={expected}",
            'A="$(/bin/busybox cat "$R")"',
            '[ "$A" = "$E" ]',
            "echo A90D1_FAST_RECEIPT exact=1",
        )
    )
    return require_bounded_run_script(script)


def require_fast_source_preflight_receipt(
    spec: resident.SessionSpec,
    value: Any,
    *,
    expected_state: str,
    expected_identity: dict[str, int] | None = None,
) -> dict[str, int]:
    script = fast_source_preflight_script(spec, expected_state=expected_state)
    try:
        record = resident._require_exact_run_shell_receipt(  # noqa: SLF001
            value,
            script=script,
            marker_pattern=FAST_SOURCE_MARKER_RE,
            label=f"H10 {expected_state} source preflight",
        )
    except resident.ContractError as exc:
        raise ContractError("fast source preflight receipt is not exact") from exc
    marker_lines = [
        line.strip()
        for line in str(record.get("text") or "").replace("\r", "").splitlines()
        if line.strip().startswith("A90D1_FAST_SOURCE")
    ]
    matches = [FAST_SOURCE_MARKER_RE.fullmatch(line) for line in marker_lines]
    matches = [match for match in matches if match is not None]
    if (
        len(marker_lines) != 1
        or len(matches) != 1
        or matches[0].group("state") != expected_state
    ):
        raise ContractError("fast source preflight marker is not exact")
    identity = {
        key: int(matches[0].group(key), 10)
        for key in FAST_SOURCE_IDENTITY_KEYS
    }
    if identity["size"] != spec.rootfs.size:
        raise ContractError("fast source preflight size changed")
    if expected_identity is not None and identity != expected_identity:
        raise ContractError("fast source identity changed across qualification")
    return identity


def require_fast_receipt_content_receipt(
    spec: resident.SessionSpec,
    source_identity: dict[str, int],
    value: Any,
) -> dict[str, Any]:
    script = fast_receipt_content_script(spec, source_identity)
    try:
        record = resident._require_exact_run_shell_receipt(  # noqa: SLF001
            value,
            script=script,
            marker_pattern=FAST_RECEIPT_MARKER_RE,
            label="H10 exact receipt content",
        )
    except resident.ContractError as exc:
        raise ContractError("fast receipt content record is not exact") from exc
    marker_lines = [
        line.strip()
        for line in str(record.get("text") or "").replace("\r", "").splitlines()
        if line.strip().startswith("A90D1_FAST_RECEIPT")
    ]
    if marker_lines != ["A90D1_FAST_RECEIPT exact=1"]:
        raise ContractError("fast receipt content marker is not exact")
    return record


def fast_resident_preflight(
    spec: resident.SessionSpec,
    args: argparse.Namespace,
    *,
    expected_state: str,
    expected_identity: dict[str, int] | None = None,
) -> tuple[resident.SessionPreflight, dict[str, Any], dict[str, int]]:
    f1_spec = _f1_spec(spec)
    health = resident.verify_resident_health_exact(spec, f1_spec, args)
    identity_record = base.run_f1_shell(
        args,
        fast_source_preflight_script(spec, expected_state=expected_state),
    )
    source_identity = require_fast_source_preflight_receipt(
        spec,
        identity_record,
        expected_state=expected_state,
        expected_identity=expected_identity,
    )
    receipt_record = None
    if expected_state == "receipt-verified":
        receipt_record = base.run_f1_shell(
            args,
            fast_receipt_content_script(spec, source_identity),
        )
        require_fast_receipt_content_receipt(
            spec,
            source_identity,
            receipt_record,
        )
    preflight = resident.SessionPreflight(True, True, True, True, True)
    preflight.validate()
    return (
        preflight,
        {
            "resident_health": health,
            "source_preflight": {
                "identity_record": identity_record,
                "receipt_record": receipt_record,
            },
            "rollback_sha256": spec.rollback.sha256,
            "recovery_profile": spec.recovery_profile,
        },
        source_identity,
    )


def validate_preflight_evidence(
    spec: resident.SessionSpec,
    value: Any,
    *,
    expected_state: str,
    expected_identity: dict[str, int] | None = None,
) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) != {
        "resident_health",
        "source_preflight",
        "rollback_sha256",
        "recovery_profile",
    }:
        raise ContractError("resident preflight evidence keyset is not exact")
    if (
        value.get("rollback_sha256") != spec.rollback.sha256
        or value.get("recovery_profile") != spec.recovery_profile
    ):
        raise ContractError("resident preflight artifact binding changed")
    resident._validate_resident_native_health(  # noqa: SLF001
        value.get("resident_health"),
        expected_version=spec.candidate_version,
        expected_build=spec.candidate_build,
        expected_bridge_realpath=spec.bridge_realpath,
    )
    source = value.get("source_preflight")
    if not isinstance(source, dict) or set(source) != {
        "identity_record",
        "receipt_record",
    }:
        raise ContractError("fast source preflight evidence is not exact")
    source_identity = require_fast_source_preflight_receipt(
        spec,
        source.get("identity_record"),
        expected_state=expected_state,
        expected_identity=expected_identity,
    )
    if expected_state == "receipt-absent":
        if source.get("receipt_record") is not None:
            raise ContractError("receipt-absent preflight has a receipt record")
    else:
        require_fast_receipt_content_receipt(
            spec,
            source_identity,
            source.get("receipt_record"),
        )
    return source_identity


def _read_record(path: Path) -> dict[str, Any]:
    info = path.stat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ContractError("durable journal member is not one regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("durable journal member is malformed") from exc
    if not isinstance(value, dict):
        raise ContractError("durable journal member is not an object")
    return value


def load_journal_prefix(
    spec: resident.SessionSpec,
    path: Path,
    expected_closure_sha256: str,
    *,
    journal_closure_sha256: str | None = None,
) -> list[dict[str, Any]]:
    closure = require_execution_closure(expected_closure_sha256)
    present = [name for name in JOURNAL_NAMES if (path / name).is_file()]
    if present != list(JOURNAL_NAMES[: len(present)]):
        raise ContractError("durable journal is not one contiguous prefix")
    unexpected = sorted(
        item.name
        for item in path.iterdir()
        if re.fullmatch(r"[0-9]{4}-.*\.json", item.name) is not None
        and item.name not in present
    )
    if unexpected:
        raise ContractError("durable journal has unexpected JSON members")
    records: list[dict[str, Any]] = []
    for index, name in enumerate(present):
        value = _read_record(path / name)
        if (
            set(value) != COMMON_RECORD_KEYS | PAYLOAD_KEYS[index]
            or value.get("schema") != JOURNAL_SCHEMA
            or value.get("action") != JOURNAL_ACTIONS[index]
            or not base.is_canonical_utc_timestamp(value.get("timestamp_utc"))
        ):
            raise ContractError(f"journal record {index} shape/action is not exact")
        records.append(value)
    if not records:
        return records

    opened = records[0]
    if journal_closure_sha256 is None:
        opened_closure = closure
        intent_closure_sha256 = expected_closure_sha256
    else:
        opened_closure = validate_recorded_execution_closure(
            opened.get("execution_closure"),
            journal_closure_sha256,
        )
        intent_closure_sha256 = journal_closure_sha256
    if (
        opened.get("manifest_sha256") != spec.manifest_sha256
        or opened.get("execution_closure") != opened_closure
        or opened.get("candidate_sha256") != spec.candidate.sha256
        or opened.get("rollback_sha256") != spec.rollback.sha256
        or opened.get("rootfs_sha256") != spec.rootfs.sha256
        or opened.get("first_boot_unarmed") is not True
    ):
        raise ContractError("journal opening binding changed")
    opening_source_identity = validate_preflight_evidence(
        spec,
        opened.get("opening_preflight"),
        expected_state="receipt-absent",
    )
    status_record = base.require_exact_f1_command_receipt(
        opened.get("auto_status_record"),
        ["auto-handoff-status"],
        "journal opening status",
    )
    if opened.get("auto_status") != parse_auto_status(status_record):
        raise ContractError("journal opening status record changed")
    if opened["auto_status"].get("enable") != 0 or opened["auto_status"].get("latch") != 0:
        raise ContractError("journal opening state is not unarmed")
    first_log = base.require_exact_f1_command_receipt(
        opened.get("first_boot_log"),
        ["logcat"],
        "journal first-boot log",
    )
    require_first_boot_unarmed(first_log)
    if opened.get("first_boot_log_sha256") != hashlib.sha256(
        str(first_log.get("text") or "").encode("utf-8")
    ).hexdigest():
        raise ContractError("journal first-boot log hash changed")

    if len(records) >= 2:
        intent = records[1]
        if (
            intent.get("manifest_sha256") != spec.manifest_sha256
            or intent.get("execution_closure_sha256") != intent_closure_sha256
            or not exact_int(intent.get("arm_dispatch_count_max"), 1)
            or not exact_int(intent.get("reboot_dispatch_count"), 0)
            or intent.get("candidate_replay") is not False
        ):
            raise ContractError("arm intent binding changed")
        intent_sha256 = sha256_file(path / JOURNAL_NAMES[1])
    else:
        return records

    if len(records) >= 3:
        armed = records[2]
        post_status_value = armed.get("post_arm_status_record")
        if isinstance(post_status_value, dict) and "command" in post_status_value:
            post_status_record = base.require_exact_f1_command_receipt(
                post_status_value,
                ["auto-handoff-status"],
                "journal post-arm status",
            )
            post_status: dict[str, Any] | None = parse_auto_status(post_status_record)
        elif _is_unproved_receipt(post_status_value):
            post_status = None
        else:
            raise ContractError("journal post-arm status receipt is not exact")
        if (
            armed.get("intent_sha256") != intent_sha256
            or not exact_int(armed.get("arm_dispatch_count"), 1)
            or armed.get("post_arm_status") != post_status
        ):
            raise ContractError("arm result binding changed")
        arm_record = armed.get("arm_record")
        if isinstance(arm_record, dict) and "command" in arm_record:
            _, arm_outcome = require_exact_arm_dispatch_receipt(
                arm_record,
                intent_sha256,
            )
        elif _is_unproved_receipt(arm_record):
            arm_outcome = "unproved"
        else:
            raise ContractError("journal arm dispatch record is not exact")
        state = None if post_status is None else (
            post_status.get("enable"),
            post_status.get("latch"),
        )
        if (
            (arm_outcome == "armed" and state != (1, 0))
            or (arm_outcome == "refused-unarmed" and state != (0, 0))
            or (arm_outcome == "unproved" and state not in (None, (0, 0), (1, 0)))
        ):
            raise ContractError("journal arm receipt and post-arm state disagree")
    if len(records) >= 4:
        reboot = records[3]
        if (
            arm_outcome != "armed"
            or records[2].get("post_arm_status") is None
            or records[2]["post_arm_status"].get("enable") != 1
            or records[2]["post_arm_status"].get("latch") != 0
            or (
                reboot.get("intent_sha256") != intent_sha256
                or reboot.get("execution_closure_sha256")
                != expected_closure_sha256
                or not exact_int(reboot.get("reboot_dispatch_count_max"), 1)
                or reboot.get("candidate_replay") is not False
                or not isinstance(reboot.get("pre_reboot_epoch"), dict)
            )
        ):
            raise ContractError("reboot intent binding changed")
        validate_preflight_evidence(
            spec,
            reboot.get("armed_preflight"),
            expected_state="receipt-verified",
            expected_identity=opening_source_identity,
        )
        pre_reboot_binding = reboot["pre_reboot_epoch"]
        if pre_reboot_binding.get("schema") == PRE_REBOOT_OBSERVER_BINDING_SCHEMA:
            validate_pre_reboot_observer_binding(
                pre_reboot_binding,
                expected_realpath=spec.bridge_realpath,
            )
        elif expected_closure_sha256 != HISTORICAL_H10_TERMINAL_CLOSURE_SHA256:
            raise ContractError("reboot intent lacks the exact observer binding")
    if len(records) >= 5:
        observed = records[4]
        observation = observed.get("observation")
        if (
            observed.get("intent_sha256") != intent_sha256
            or not exact_int(observed.get("arm_dispatch_count"), 1)
            or not exact_int(observed.get("reboot_dispatch_count"), 1)
            or observed.get("candidate_replay") is not False
            or not isinstance(observation, dict)
            or not isinstance(observation.get("reboot_record"), dict)
            or observation["reboot_record"].get("command") != ["reboot"]
            or not exact_int(
                observation["reboot_record"].get("dispatch_count"), 1
            )
        ):
            raise ContractError("observation journal binding changed")
    if len(records) >= 6:
        cleanup_intent = records[5]
        returned_status_record = base.require_exact_f1_command_receipt(
            cleanup_intent.get("returned_status_record"),
            ["auto-handoff-status"],
            "journal pre-absence returned status",
        )
        returned_status = parse_auto_status(returned_status_record)
        if (
            cleanup_intent.get("intent_sha256") != intent_sha256
            or cleanup_intent.get("manifest_sha256") != spec.manifest_sha256
            or not exact_int(cleanup_intent.get("cleanup_dispatch_count_max"), 0)
            or not exact_int(cleanup_intent.get("arm_dispatch_count"), 1)
            or not exact_int(cleanup_intent.get("reboot_dispatch_count"), 1)
            or cleanup_intent.get("candidate_replay") is not False
            or cleanup_intent.get("returned_status") != returned_status
            or returned_status.get("enable") != 1
            or returned_status.get("latch") != 1
        ):
            raise ContractError("absence-close intent binding changed")
    if len(records) >= 7:
        cleanup = records[6]
        if (
            cleanup.get("intent_sha256") != intent_sha256
            or cleanup.get("candidate_replay") is not False
        ):
            raise ContractError("absence-close result binding changed")
        if cleanup.get("inferred_from_absence") is not True:
            raise ContractError("absence-close result disposition is not exact")
        if (
            not exact_int(cleanup.get("cleanup_dispatch_count"), 0)
            or cleanup.get("cleanup_record") is not None
        ):
            raise ContractError("H10 absence close dispatched cleanup")
        validate_preflight_evidence(
            spec,
            cleanup.get("absence_preflight"),
            expected_state="receipt-verified",
            expected_identity=opening_source_identity,
        )
    if len(records) >= 8:
        final = records[7]
        result = validate_result(
            spec,
            final.get("result"),
            intent_sha256,
            expected_source_identity=opening_source_identity,
        )
        if (
            final.get("intent_sha256") != intent_sha256
            or final.get("result_sha256") != base.json_sha256(result)
        ):
            raise ContractError("final-health result binding changed")
    if len(records) >= 9:
        closed = records[8]
        result = validate_result(
            spec,
            closed.get("result"),
            intent_sha256,
            expected_source_identity=opening_source_identity,
        )
        if (
            closed.get("result_sha256") != base.json_sha256(result)
            or result != records[7].get("result")
        ):
            raise ContractError("closed result binding changed")
    return records


def parse_auto_status(record: dict[str, Any]) -> dict[str, Any]:
    text = str(record.get("text") or "")
    tag_lines = [
        line.strip()
        for line in text.replace("\r", "").splitlines()
        if line.strip().startswith("A90AUTO_STATUS")
    ]
    matches = [STATUS_RE.fullmatch(line) for line in tag_lines]
    if len(tag_lines) != 1 or len(matches) != 1 or matches[0] is None:
        raise ContractError("auto-handoff status response is not unique")
    match = matches[0]
    result = {
        "binding": int(match.group("binding"), 10),
        "enable": int(match.group("enable"), 10),
        "latch": int(match.group("latch"), 10),
        "build": match.group("build"),
    }
    if result["binding"] != 1 or result["build"] != EXPECTED_BUILD:
        raise ContractError("auto-handoff status binding/build is not exact H10")
    return result


def require_auto_status(
    args: argparse.Namespace,
    *,
    enable: int,
    latch: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    record, status = read_auto_status(args)
    if status["enable"] != enable or status["latch"] != latch:
        raise ContractError(
            "auto-handoff state differs: "
            f"got enable={status['enable']} latch={status['latch']} "
            f"expected enable={enable} latch={latch}"
        )
    return record, status


def read_auto_status(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, Any]]:
    record = base.require_exact_f1_command_receipt(
        base.run_f1_cmd(args, ["auto-handoff-status"]),
        ["auto-handoff-status"],
        "auto-handoff status receipt",
    )
    status = parse_auto_status(record)
    return record, status


def require_exact_arm_dispatch_receipt(
    value: Any,
    intent_sha256: str,
) -> tuple[dict[str, Any], str]:
    command = ["auto-handoff-arm", ARM_TOKEN, intent_sha256]
    if not isinstance(value, dict):
        raise ContractError("auto-handoff arm receipt is not an object")
    if value.get("rc") == 0:
        record = base.require_exact_f1_command_receipt(
            value,
            command,
            "auto-handoff arm receipt",
        )
        lines = [
            line.strip()
            for line in str(record.get("text") or "").replace("\r", "").splitlines()
            if line.strip().startswith(("A90D3H0", "A90AUTO_ARM"))
        ]
        expected_lines = [
            "A90D3H0 source_receipt=qualifying "
            f"path={SOURCE_RECEIPT_PATH} prior_rc=-2 full_sha=required",
            "A90D3H0 source_sha phase=receipt-qualification "
            f"sha={EXPECTED_ROOTFS_SHA256} expected_sha_match=1",
            "A90D3H0 source_receipt=qualified "
            f"path={SOURCE_RECEIPT_PATH} metadata=exact full_sha=verified",
            "A90AUTO_ARM armed=1 "
            f"intent_sha256={intent_sha256} build={EXPECTED_BUILD}",
        ]
        if lines != expected_lines:
            raise ContractError(
                "auto-handoff arm did not prove one fresh full-SHA qualification"
            )
        return record, "armed"

    record = value
    begin = record.get("begin")
    end = record.get("end")
    rc = record.get("rc")
    if (
        set(record) != {"command", "rc", "status", "trust", "begin", "end", "text"}
        or record.get("command") != command
        or type(rc) is not int
        or rc >= 0
        or record.get("status") != "error"
        or record.get("trust") != "A90P1_V1_STRUCTURAL_ONLY"
        or type(record.get("text")) is not str
        or not isinstance(begin, dict)
        or set(begin) != {"argc", "cmd", "flags", "seq"}
        or begin.get("cmd") != command[0]
        or begin.get("argc") != str(len(command))
        or re.fullmatch(r"0x[0-9a-f]+", str(begin.get("flags") or "")) is None
        or not str(begin.get("seq") or "").isdigit()
        or not isinstance(end, dict)
        or set(end) != {"cmd", "duration_ms", "errno", "flags", "rc", "seq", "status"}
        or end.get("cmd") != command[0]
        or end.get("seq") != begin.get("seq")
        or end.get("flags") != begin.get("flags")
        or end.get("rc") != str(rc)
        or end.get("errno") != str(-rc)
        or end.get("status") != "error"
        or not str(end.get("duration_ms") or "").isdigit()
    ):
        raise ContractError("auto-handoff arm refusal receipt is not exact")
    marker = f"A90AUTO_ARM armed=0 rc={rc}"
    tag_lines = [
        line.strip()
        for line in str(record.get("text") or "").replace("\r", "").splitlines()
        if line.strip().startswith(("A90D3H0", "A90AUTO_ARM"))
    ]
    if tag_lines != [marker]:
        raise ContractError("auto-handoff arm refusal marker is not exact")
    return record, "refused-unarmed"


def _is_unproved_receipt(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"error", "response_proof"}
        and isinstance(value.get("error"), dict)
        and value.get("response_proof") is False
    )


def require_first_boot_unarmed(log_record: dict[str, Any]) -> None:
    base.require_exact_f1_command_receipt(
        log_record,
        ["logcat"],
        "first H10 resident log receipt",
    )
    text = str(log_record.get("text") or "")
    state_lines: list[str] = []
    for line in text.replace("\r", "\n").splitlines():
        marker = line.find("A90AUTO state=")
        if marker >= 0:
            state_lines.append(line[marker:].strip())
    if not state_lines or any(
        line != "A90AUTO state=unarmed-stay-native" for line in state_lines
    ):
        raise ContractError("H10 resident log is not exclusively unarmed")


def _effect_args() -> argparse.Namespace:
    return resident._effect_args()  # noqa: SLF001 - exact reviewed D1 adapter


def _f1_spec(spec: resident.SessionSpec) -> base.F1Spec:
    return resident._f1_spec(spec)  # noqa: SLF001 - exact reviewed D1 adapter


def send_reboot_once(args: argparse.Namespace) -> dict[str, Any]:
    line = base.a90ctl.encode_cmdv1_line(["reboot"])
    record: dict[str, Any] = {
        "command": ["reboot"],
        "dispatch_count": 1,
        "accepted_transport_drop": True,
    }
    try:
        text = base.a90ctl.bridge_exchange(
            args.bridge_host,
            args.bridge_port,
            line,
            8.0,
            markers=(b"reboot: syncing and restarting", b"A90P1 END "),
            input_mode=base.F1_SERIAL_INPUT_MODE,
            input_char_delay_sec=base.F1_SERIAL_INPUT_CHAR_DELAY_SEC,
            require_prompt_after_end=False,
            post_marker_drain_sec=0.0,
        )
        record["text"] = text
        if "A90P1 END " in text and "reboot: syncing and restarting" not in text:
            raise ContractError("reboot command returned before reboot dispatch")
    except ContractError:
        raise
    except Exception as exc:  # transport loss is expected after one dispatch
        record["transport_error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
    return record


def _native_release_log(text: str) -> str:
    lines: list[str] = []
    for line in text.replace("\r", "\n").splitlines():
        index = line.find("A90D3DISPLAY ")
        if index >= 0:
            lines.append(line[index:])
    return "\n".join(lines) + ("\n" if lines else "")


def _usb_parent_snapshot(parent: Path) -> dict[str, Any]:
    topology = parent.name
    vendor = base.staging._read_sysfs_text(parent / "idVendor").lower()  # noqa: SLF001
    product = base.staging._read_sysfs_text(parent / "idProduct").lower()  # noqa: SLF001
    serial = base.staging._read_sysfs_text(parent / "serial")  # noqa: SLF001
    busnum = base.staging._read_sysfs_text(parent / "busnum")  # noqa: SLF001
    devnum = base.staging._read_sysfs_text(parent / "devnum")  # noqa: SLF001
    if (
        USB_TOPOLOGY_RE.fullmatch(topology) is None
        or vendor != base.staging.HOST_NCM_VENDOR_ID
        or product != base.staging.HOST_NCM_PRODUCT_ID
        or not serial
        or not busnum.isdecimal()
        or not devnum.isdecimal()
    ):
        raise ContractError("A90 USB parent identity is not exact")
    return {
        "usb_topology": topology,
        "usb_serial_sha256": hashlib.sha256(serial.encode("utf-8")).hexdigest(),
        "usb_vendor": vendor,
        "usb_product": product,
        "usb_busnum": int(busnum, 10),
        "usb_devnum": int(devnum, 10),
    }


def capture_pre_reboot_observer_binding(
    f1_spec: base.F1Spec,
    args: argparse.Namespace,
) -> dict[str, Any]:
    bridge = base.staging.require_exact_bridge(f1_spec.stage, args)
    selected_realpath = bridge.get("selected_realpath")
    if selected_realpath != f1_spec.stage.bridge_realpath:
        raise ContractError("pre-reboot bridge realpath is not exact")
    parent = base.staging._usb_device_parent(  # noqa: SLF001
        SYS_CLASS_TTY / Path(selected_realpath).name
    )
    if parent is None:
        raise ContractError("pre-reboot A90 USB parent is unavailable")
    interfaces = base.staging.exact_a90_ncm_interfaces(selected_realpath)
    if len(interfaces) != 1:
        raise ContractError("pre-reboot A90 USB parent lacks one exact NCM interface")
    return {
        "schema": PRE_REBOOT_OBSERVER_BINDING_SCHEMA,
        "serial_epoch": base._bound_bridge_serial_epoch(f1_spec, bridge),  # noqa: SLF001
        "usb_identity": _usb_parent_snapshot(parent),
        "pre_reboot_interface": interfaces[0],
    }


def require_pre_reboot_observer_binding_current(
    f1_spec: base.F1Spec,
    args: argparse.Namespace,
    binding: dict[str, Any],
) -> dict[str, Any]:
    """Require the captured ACM/NCM epoch to remain live before reboot."""

    binding = validate_pre_reboot_observer_binding(
        binding,
        expected_realpath=f1_spec.stage.bridge_realpath,
    )
    if capture_pre_reboot_observer_binding(f1_spec, args) != binding:
        raise ContractError("pre-reboot A90 observer binding changed")
    return binding


def validate_pre_reboot_observer_binding(
    value: Any,
    *,
    expected_realpath: str | None = None,
) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value)
        != {"schema", "serial_epoch", "usb_identity", "pre_reboot_interface"}
        or value.get("schema") != PRE_REBOOT_OBSERVER_BINDING_SCHEMA
        or not isinstance(value.get("serial_epoch"), dict)
        or not isinstance(value.get("usb_identity"), dict)
        or base.staging.HOST_IFACE_RE.fullmatch(
            str(value.get("pre_reboot_interface") or "")
        )
        is None
    ):
        raise ContractError("pre-reboot observer binding is not exact")
    serial_epoch = value["serial_epoch"]
    if (
        set(serial_epoch)
        != {
            "schema",
            "selected_realpath",
            "tty_st_dev",
            "tty_st_ino",
            "tty_st_rdev",
            "usb_busnum",
            "usb_devnum",
        }
        or serial_epoch.get("schema") != base.RETURN_EPOCH_SCHEMA
        or base.staging.BRIDGE_REALPATH_RE.fullmatch(
            str(serial_epoch.get("selected_realpath") or "")
        )
        is None
        or (
            expected_realpath is not None
            and serial_epoch.get("selected_realpath") != expected_realpath
        )
        or any(
            type(serial_epoch.get(key)) is not int or serial_epoch[key] < 0
            for key in (
                "tty_st_dev",
                "tty_st_ino",
                "tty_st_rdev",
                "usb_busnum",
                "usb_devnum",
            )
        )
        or serial_epoch["usb_busnum"] < 1
        or serial_epoch["usb_devnum"] < 1
    ):
        raise ContractError("pre-reboot serial epoch is not exact")
    identity = value["usb_identity"]
    if (
        set(identity)
        != {
            "usb_topology",
            "usb_serial_sha256",
            "usb_vendor",
            "usb_product",
            "usb_busnum",
            "usb_devnum",
        }
        or USB_TOPOLOGY_RE.fullmatch(str(identity.get("usb_topology") or ""))
        is None
        or HEX64_RE.fullmatch(str(identity.get("usb_serial_sha256") or "")) is None
        or identity.get("usb_vendor") != base.staging.HOST_NCM_VENDOR_ID
        or identity.get("usb_product") != base.staging.HOST_NCM_PRODUCT_ID
        or type(identity.get("usb_busnum")) is not int
        or identity["usb_busnum"] < 1
        or type(identity.get("usb_devnum")) is not int
        or identity["usb_devnum"] < 1
    ):
        raise ContractError("pre-reboot USB identity is not exact")
    if (
        serial_epoch["usb_busnum"],
        serial_epoch["usb_devnum"],
    ) != (identity["usb_busnum"], identity["usb_devnum"]):
        raise ContractError("pre-reboot serial and NCM USB epochs differ")
    return value


def _matching_bound_ncm_interfaces(
    binding: dict[str, Any],
) -> list[dict[str, Any]]:
    binding = validate_pre_reboot_observer_binding(binding)
    expected = binding["usb_identity"]
    try:
        netdevs = tuple(SYS_CLASS_NET.iterdir())
    except OSError:
        return []
    matches: list[dict[str, Any]] = []
    for netdev in netdevs:
        if base.staging.HOST_IFACE_RE.fullmatch(netdev.name) is None:
            continue
        try:
            driver = (netdev / "device" / "driver").resolve(strict=True).name
        except OSError:
            continue
        if driver != base.staging.HOST_NCM_DRIVER:
            continue
        parent = base.staging._usb_device_parent(netdev)  # noqa: SLF001
        if parent is None:
            continue
        try:
            current = _usb_parent_snapshot(parent)
        except ContractError:
            continue
        if (
            current["usb_topology"] == expected["usb_topology"]
            and current["usb_serial_sha256"] == expected["usb_serial_sha256"]
            and current["usb_vendor"] == expected["usb_vendor"]
            and current["usb_product"] == expected["usb_product"]
        ):
            matches.append({"interface": netdev.name, **current})
    return matches


def wait_for_bound_ncm_after_reboot(
    binding: dict[str, Any],
) -> dict[str, Any]:
    """Find the same A90 NCM at a new USB epoch without requiring ACM."""

    binding = validate_pre_reboot_observer_binding(binding)
    before = binding["usb_identity"]
    deadline = time.monotonic() + base.HOST_NCM_REBIND_TIMEOUT_SEC
    while True:
        matches = _matching_bound_ncm_interfaces(binding)
        if len(matches) > 1:
            raise ContractError("multiple NCM interfaces match the bound A90 identity")
        if len(matches) == 1:
            current = matches[0]
            if (
                current["usb_busnum"],
                current["usb_devnum"],
            ) != (before["usb_busnum"], before["usb_devnum"]):
                return {
                    "schema": POST_REBOOT_NCM_IDENTITY_SCHEMA,
                    **current,
                    "same_usb_topology": True,
                    "same_usb_serial_sha256": True,
                    "new_usb_epoch": True,
                }
        if time.monotonic() >= deadline:
            raise ContractError(
                "bound A90 NCM did not appear at a new USB epoch before deadline"
            )
        time.sleep(base.HOST_NCM_REBIND_POLL_SEC)


def validate_post_reboot_ncm_identity(
    binding: dict[str, Any],
    value: Any,
    *,
    require_live: bool,
) -> dict[str, Any]:
    binding = validate_pre_reboot_observer_binding(binding)
    keys = {
        "schema",
        "interface",
        "usb_topology",
        "usb_serial_sha256",
        "usb_vendor",
        "usb_product",
        "usb_busnum",
        "usb_devnum",
        "same_usb_topology",
        "same_usb_serial_sha256",
        "new_usb_epoch",
    }
    if (
        not isinstance(value, dict)
        or set(value) != keys
        or value.get("schema") != POST_REBOOT_NCM_IDENTITY_SCHEMA
        or base.staging.HOST_IFACE_RE.fullmatch(str(value.get("interface") or ""))
        is None
        or value.get("same_usb_topology") is not True
        or value.get("same_usb_serial_sha256") is not True
        or value.get("new_usb_epoch") is not True
    ):
        raise ContractError("post-reboot NCM identity is not exact")
    expected = binding["usb_identity"]
    if (
        value.get("usb_topology") != expected["usb_topology"]
        or value.get("usb_serial_sha256") != expected["usb_serial_sha256"]
        or value.get("usb_vendor") != expected["usb_vendor"]
        or value.get("usb_product") != expected["usb_product"]
        or type(value.get("usb_busnum")) is not int
        or value["usb_busnum"] < 1
        or type(value.get("usb_devnum")) is not int
        or value["usb_devnum"] < 1
        or (value["usb_busnum"], value["usb_devnum"])
        == (expected["usb_busnum"], expected["usb_devnum"])
    ):
        raise ContractError("post-reboot NCM does not match the bound A90")
    if require_live:
        matches = _matching_bound_ncm_interfaces(binding)
        if matches != [
            {
                key: value[key]
                for key in (
                    "interface",
                    "usb_topology",
                    "usb_serial_sha256",
                    "usb_vendor",
                    "usb_product",
                    "usb_busnum",
                    "usb_devnum",
                )
            }
        ]:
            raise ContractError("bound A90 NCM identity is no longer current")
    return value


def _require_bound_host_ncm_ready(
    spec: base.F1Spec,
    binding: dict[str, Any],
    ncm_identity: dict[str, Any],
) -> dict[str, bool]:
    ncm_identity = validate_post_reboot_ncm_identity(
        binding,
        ncm_identity,
        require_live=True,
    )
    interface = ncm_identity["interface"]
    device = ipaddress.IPv4Address(
        base.staging.validate_observer_device(spec.observer_device)
    )
    host_cidr = base._host_ncm_peer_cidr(spec.observer_device)  # noqa: SLF001
    host = host_cidr.split("/", 1)[0]
    route = base._host_command(  # noqa: SLF001
        ["ip", "-4", "route", "get", str(device)],
        timeout=5.0,
    )
    route_lines = [line for line in str(route["stdout"]).splitlines() if line.strip()]
    if (
        route["returncode"] != 0
        or not route_lines
        or any(line.strip() != "cache" for line in route_lines[1:])
    ):
        raise ContractError("bound A90 NCM direct route is unavailable")
    tokens = route_lines[0].split()
    if (
        not tokens
        or tokens[0] != str(device)
        or "via" in tokens
        or base.staging._route_token(tokens, "dev") != interface  # noqa: SLF001
        or base.staging._route_token(tokens, "src") != host  # noqa: SLF001
    ):
        raise ContractError("observer route is not on the bound A90 NCM")
    address = base._host_command(  # noqa: SLF001
        ["ip", "-4", "-o", "addr", "show", "dev", interface],
        timeout=5.0,
    )
    ping = base._host_command(  # noqa: SLF001
        ["ping", "-n", "-c", "1", "-W", "2", str(device)],
        timeout=5.0,
    )
    if address["returncode"] != 0 or host_cidr not in str(address["stdout"]).split():
        raise ContractError("bound A90 NCM lacks the expected host CIDR")
    if ping["returncode"] != 0:
        raise ContractError("Debian is not reachable on the bound A90 NCM")
    validate_post_reboot_ncm_identity(binding, ncm_identity, require_live=True)
    return {
        "verified_a90_ncm": True,
        "direct_route": True,
        "host_cidr_present": True,
        "device_ping": True,
    }


def rebind_host_ncm_for_bound_identity(
    spec: base.F1Spec,
    binding: dict[str, Any],
    ncm_identity: dict[str, Any],
) -> dict[str, Any]:
    if shutil.which("nmcli") is None:
        raise ContractError("nmcli is unavailable for bound A90 NCM rebind")
    ncm_identity = validate_post_reboot_ncm_identity(
        binding,
        ncm_identity,
        require_live=True,
    )
    interface = ncm_identity["interface"]
    profile = base._host_command(  # noqa: SLF001
        [
            "nmcli",
            "-g",
            "connection.type",
            "connection",
            "show",
            spec.observer_host_ncm_profile,
        ],
        timeout=10.0,
    )
    if (
        profile["returncode"] != 0
        or str(profile["stdout"]).strip() != base.HOST_NCM_CONNECTION_TYPE
    ):
        raise ContractError("manifest-bound host NCM profile is absent or not Ethernet")
    active_before, active_before_receipt = base._nmcli_active_connection(  # noqa: SLF001
        interface
    )
    try:
        ready_before = _require_bound_host_ncm_ready(spec, binding, ncm_identity)
    except ContractError:
        ready_before = None
    if ready_before is not None and active_before == spec.observer_host_ncm_profile:
        return {
            "same_bound_usb_identity": True,
            "acm_required": False,
            "exact_interface_count": 1,
            "profile_bound": True,
            "mutated": False,
            "profile_check": profile,
            "active_before": active_before_receipt,
            "ready": ready_before,
        }
    validate_post_reboot_ncm_identity(binding, ncm_identity, require_live=True)
    host_cidr = base._host_ncm_peer_cidr(spec.observer_device)  # noqa: SLF001
    modify = base._host_command(  # noqa: SLF001
        [
            "nmcli",
            "--wait",
            "10",
            "connection",
            "modify",
            spec.observer_host_ncm_profile,
            "connection.interface-name",
            interface,
            "ipv4.method",
            "manual",
            "ipv4.addresses",
            host_cidr,
            "ipv4.gateway",
            "",
            "ipv4.never-default",
            "yes",
            "ipv4.dns",
            "",
            "ipv6.method",
            "disabled",
            "connection.autoconnect",
            "no",
        ],
        timeout=15.0,
    )
    if modify["returncode"] != 0:
        raise ContractError("manifest-bound host NCM profile modification failed")
    validate_post_reboot_ncm_identity(binding, ncm_identity, require_live=True)
    activate = base._host_command(  # noqa: SLF001
        [
            "nmcli",
            "--wait",
            "15",
            "connection",
            "up",
            spec.observer_host_ncm_profile,
            "ifname",
            interface,
        ],
        timeout=20.0,
    )
    if activate["returncode"] != 0:
        raise ContractError("manifest-bound host NCM profile activation failed")
    active_after, active_after_receipt = base._nmcli_active_connection(  # noqa: SLF001
        interface
    )
    if active_after != spec.observer_host_ncm_profile:
        raise ContractError("bound A90 NCM did not select the manifest profile")
    ready: dict[str, bool] | None = None
    deadline = time.monotonic() + base.HOST_NCM_REBIND_TIMEOUT_SEC
    while time.monotonic() < deadline:
        try:
            ready = _require_bound_host_ncm_ready(spec, binding, ncm_identity)
            break
        except ContractError:
            validate_post_reboot_ncm_identity(
                binding,
                ncm_identity,
                require_live=True,
            )
            time.sleep(base.HOST_NCM_REBIND_POLL_SEC)
    if ready is None:
        raise ContractError("rebound A90 NCM did not become USB-local ready")
    return {
        "same_bound_usb_identity": True,
        "acm_required": False,
        "exact_interface_count": 1,
        "profile_bound": True,
        "mutated": True,
        "profile_check": profile,
        "active_before": active_before_receipt,
        "modify": modify,
        "activate": activate,
        "active_after": active_after_receipt,
        "ready": ready,
    }


def wait_for_native_return_after_bound_ncm(
    spec: base.F1Spec,
    args: argparse.Namespace,
    binding: dict[str, Any],
    ncm_identity: dict[str, Any],
    guard: Any,
) -> dict[str, Any]:
    """Prove a later native ACM epoch, then perform the existing health reads."""

    binding = validate_pre_reboot_observer_binding(binding)
    ncm_identity = validate_post_reboot_ncm_identity(
        binding,
        ncm_identity,
        require_live=False,
    )
    deadline = time.monotonic() + spec.candidate_return_timeout
    returned_epoch: dict[str, Any] | None = None
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            bridge = base.staging.require_exact_bridge(spec.stage, args)
            epoch = base._bound_bridge_serial_epoch(spec, bridge)  # noqa: SLF001
        except (base.ContractError, base.staging.ContractError) as exc:
            last_error = exc
            if Path(spec.stage.bridge_device).exists():
                raise ContractError(
                    "present native-return bridge failed exact continuity"
                ) from exc
            time.sleep(base.HOST_NCM_REBIND_POLL_SEC)
            continue
        if (epoch["usb_busnum"], epoch["usb_devnum"]) == (
            ncm_identity["usb_busnum"],
            ncm_identity["usb_devnum"],
        ):
            time.sleep(base.HOST_NCM_REBIND_POLL_SEC)
            continue
        parent = base.staging._usb_device_parent(  # noqa: SLF001
            SYS_CLASS_TTY / Path(epoch["selected_realpath"]).name
        )
        if parent is None:
            raise ContractError("native-return USB parent is unavailable")
        returned_identity = _usb_parent_snapshot(parent)
        before = binding["usb_identity"]
        if (
            returned_identity["usb_topology"] != before["usb_topology"]
            or returned_identity["usb_serial_sha256"]
            != before["usb_serial_sha256"]
            or returned_identity["usb_vendor"] != before["usb_vendor"]
            or returned_identity["usb_product"] != before["usb_product"]
            or (
                returned_identity["usb_busnum"],
                returned_identity["usb_devnum"],
            )
            != (epoch["usb_busnum"], epoch["usb_devnum"])
            or (epoch["usb_busnum"], epoch["usb_devnum"])
            == (before["usb_busnum"], before["usb_devnum"])
        ):
            raise ContractError("native-return USB identity changed")
        returned_epoch = epoch
        break
    if returned_epoch is None:
        raise ContractError("native return did not reach a later exact ACM epoch") from last_error
    return_epoch = {
        "before_ncm": {
            "usb_busnum": ncm_identity["usb_busnum"],
            "usb_devnum": ncm_identity["usb_devnum"],
        },
        "returned": returned_epoch,
        "returned_usb_identity": returned_identity,
        "changed": True,
    }
    if not guard.healthy(recheck=True):
        raise ContractError("candidate-return ModemManager guard was lost")
    guard_evidence = base.require_returned_modemmanager_guard(
        spec,
        return_epoch,
        guard,
    )
    if not guard.healthy(recheck=True):
        raise ContractError("candidate-return guard was lost before command")
    version = base.run_f1_cmd(args, ["version"])
    version_text = str(version.get("text") or "")
    expected_version_line = (
        f"version: {spec.candidate_version} build={spec.candidate_build}"
    )
    version_lines = [
        line for line in version_text.splitlines() if line.startswith("version: ")
    ]
    if version_lines != [expected_version_line]:
        raise ContractError("candidate return native identity is not exact")
    channel = base.settle_observation_channel(args, phase="attended-candidate-return")
    selftest = base.run_f1_cmd(args, ["selftest"])
    selftest_lines = [
        line
        for line in str(selftest.get("text") or "").splitlines()
        if line.startswith("selftest: ")
    ]
    if (
        len(selftest_lines) != 1
        or re.fullmatch(
            r"selftest: pass=[0-9]+ warn=[0-9]+ fail=0 "
            r"duration=[0-9]+ms entries=[1-9][0-9]*",
            selftest_lines[0],
        )
        is None
    ):
        raise ContractError("candidate return selftest is not fail=0")
    return {
        "exact_bridge": True,
        "selected_realpath": returned_epoch["selected_realpath"],
        "return_epoch": return_epoch,
        "native_epoch_version_proven": True,
        "channel": channel,
        "version": version,
        "selftest": selftest,
        "device_command_sequences": 1,
        "candidate_return_modemmanager_guard": guard_evidence,
    }


def observe_auto_cycle(
    spec: resident.SessionSpec,
    args: argparse.Namespace,
    transaction_dir: Path,
    guard: Any,
    pre_reboot_binding: dict[str, Any],
) -> dict[str, Any]:
    f1_spec = _f1_spec(spec)
    result: dict[str, Any] = {"proof": False}
    try:
        pre_reboot_binding = validate_pre_reboot_observer_binding(
            pre_reboot_binding,
            expected_realpath=f1_spec.stage.bridge_realpath,
        )
        result["pre_reboot_binding"] = pre_reboot_binding
        result["debian_ncm_identity"] = wait_for_bound_ncm_after_reboot(
            pre_reboot_binding
        )
        result["host_ncm_rebind"] = rebind_host_ncm_for_bound_identity(
            f1_spec,
            pre_reboot_binding,
            result["debian_ncm_identity"],
        )
        result["debian_ncm_continuity"] = {}
        validate_post_reboot_ncm_identity(
            pre_reboot_binding,
            result["debian_ncm_identity"],
            require_live=True,
        )
        result["debian_ncm_continuity"]["before_ssh"] = True
        result["ssh"] = base.observe_ssh(f1_spec, args)
        validate_post_reboot_ncm_identity(
            pre_reboot_binding,
            result["debian_ncm_identity"],
            require_live=True,
        )
        result["debian_ncm_continuity"]["after_ssh"] = True
        result["phase3_service"] = phase3_observer.observe_phase3_service(
            f1_spec,
            args,
        )
        validate_post_reboot_ncm_identity(
            pre_reboot_binding,
            result["debian_ncm_identity"],
            require_live=True,
        )
        result["debian_ncm_continuity"]["after_service"] = True
        result["candidate_return"] = wait_for_native_return_after_bound_ncm(
            f1_spec,
            args,
            pre_reboot_binding,
            result["debian_ncm_identity"],
            guard,
        )
        result["proof"] = True
    except Exception as exc:  # effect is never replayed; final D0 decides health
        result["observer_error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
    finally:
        try:
            result["guard_release"] = base.release_candidate_return_modemmanager_guard(
                guard,
                transaction_dir,
            )
        except Exception as exc:  # preserve primary observation
            result["guard_release"] = {
                "released": False,
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
    if "candidate_return" in result:
        try:
            result["retained_pmsg"] = base.collect_and_clear_retained_pmsg(
                f1_spec,
                args,
                transaction_dir,
            )
        except Exception as exc:  # final health is independently established
            result["retained_pmsg_error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
            }
    return result


FAILED_HANDOFF_TAIL = (
    "handoff_failed_native",
    "auto_handoff_returned_native",
    "native_fallback_ready",
)
RETURNED_NATIVE_TAIL = (
    "native_runtime_ready",
    "native_services_ready",
    "auto_handoff_check",
    "auto_handoff_latched_native",
)


def failed_handoff_stages_exact(stages: list[Any]) -> bool:
    """Accept one ordered complete-stage prefix followed by the native failure tail."""

    if len(stages) < len(FAILED_HANDOFF_TAIL) or tuple(
        stages[-len(FAILED_HANDOFF_TAIL) :]
    ) != FAILED_HANDOFF_TAIL:
        return False
    prefix = stages[: -len(FAILED_HANDOFF_TAIL)]
    optional = list(benchmark.OPTIONAL_EARLY_STAGES)
    if prefix[: len(optional)] == optional:
        complete_prefix = prefix[len(optional) :]
    else:
        complete_prefix = prefix
    if complete_prefix != list(benchmark.COMPLETE_STAGES[: len(complete_prefix)]):
        return False
    return {"auto_handoff_dispatched", "handoff_begin"}.issubset(complete_prefix)


def complete_handoff_stages_exact(stages: list[Any]) -> bool:
    return stages in (
        list(benchmark.COMPLETE_STAGES),
        list(benchmark.OPTIONAL_EARLY_STAGES + benchmark.COMPLETE_STAGES),
    )


def returned_native_stages_exact(stages: list[Any]) -> bool:
    return stages in (
        list(RETURNED_NATIVE_TAIL),
        list(benchmark.OPTIONAL_EARLY_STAGES + RETURNED_NATIVE_TAIL),
    )


def parse_appended_benchmark(
    opening_log_record: dict[str, Any],
    final_log_record: dict[str, Any],
) -> dict[str, Any]:
    """Select only markers appended after the hash-bound pre-arm log."""

    opening = base.require_exact_f1_command_receipt(
        opening_log_record,
        ["logcat"],
        "benchmark opening log",
    )
    final = base.require_exact_f1_command_receipt(
        final_log_record,
        ["logcat"],
        "benchmark final log",
    )
    before = list(benchmark.marker_lines([str(opening.get("text") or "")]))
    after = list(benchmark.marker_lines([str(final.get("text") or "")]))
    if not before or not after or after == before:
        raise ContractError("benchmark log is not an exact appended marker suffix")
    if len(after) > len(before) and after[: len(before)] == before:
        appended = after[len(before) :]
        log_relation = "opening-prefix-appended-suffix"
    elif set(before).isdisjoint(after):
        # A reboot may replace the bounded pmsg window instead of retaining
        # its pre-arm prefix. Accept only a wholly disjoint current window;
        # the exact one-terminal-segment and returned-native checks below
        # still reject a partial, mixed, duplicated, or stale-prefix tail.
        appended = after
        log_relation = "disjoint-current-window"
    else:
        raise ContractError("benchmark log is not an exact appended marker suffix")
    canonical = "".join(f"{benchmark.MARKER}{line}\n" for line in appended)
    segments = benchmark.parse_runs([canonical])
    segment_stages = [
        [record.get("stage") for record in segment.get("records", [])]
        for segment in segments
    ]
    for stages in segment_stages:
        if (
            any(stage in stages for stage in FAILED_HANDOFF_TAIL)
            and not failed_handoff_stages_exact(stages)
        ):
            raise benchmark.BenchmarkError(
                "native failed-handoff benchmark segment is not exact"
            )
    eligible = [
        (index, failed_handoff_stages_exact(stages))
        for index, stages in enumerate(segment_stages)
        if complete_handoff_stages_exact(stages)
        or failed_handoff_stages_exact(stages)
    ]
    if len(eligible) != 1:
        raise benchmark.BenchmarkError(
            "appended log does not contain exactly one terminal handoff segment"
        )
    selected_index, native_handoff_failed = eligible[0]
    if selected_index != 0:
        raise benchmark.BenchmarkError(
            "terminal handoff segment is not the first appended boot segment"
        )
    trailing_stages = segment_stages[1:]
    if native_handoff_failed:
        if trailing_stages:
            raise benchmark.BenchmarkError(
                "native failed-handoff segment has an unexpected boot tail"
            )
    elif len(trailing_stages) > 1 or (
        trailing_stages and not returned_native_stages_exact(trailing_stages[0])
    ):
        raise benchmark.BenchmarkError(
            "complete handoff has an unexpected returned-native boot tail"
        )
    elif log_relation == "disjoint-current-window" and not trailing_stages:
        raise benchmark.BenchmarkError(
            "fresh benchmark window lacks the exact returned-native boot tail"
        )
    elif (
        log_relation == "disjoint-current-window"
        and trailing_stages[0] != list(RETURNED_NATIVE_TAIL)
    ):
        raise benchmark.BenchmarkError(
            "fresh benchmark window has a noncanonical returned-native boot tail"
        )
    parsed = segments[selected_index]
    parsed["boot_segments_total"] = len(segments)
    parsed["selected_segment_index"] = selected_index
    parsed["native_handoff_failed"] = native_handoff_failed
    parsed["selection"] = {
        "contract": "opening-prefix-or-disjoint-current-window-v2",
        "log_relation": log_relation,
        "opening_marker_count": len(before),
        "appended_marker_count": len(appended),
        "opening_markers_sha256": hashlib.sha256(
            "".join(f"{line}\n" for line in before).encode("utf-8")
        ).hexdigest(),
        "appended_markers_sha256": hashlib.sha256(
            "".join(f"{line}\n" for line in appended).encode("utf-8")
        ).hexdigest(),
    }
    return parsed


def host_link_proven(spec: resident.SessionSpec, observation: Any) -> bool:
    """Keep USB identity and NCM reachability as host-observed facts."""

    if not isinstance(observation, dict):
        return False
    binding = observation.get("pre_reboot_binding")
    ncm_identity = observation.get("debian_ncm_identity")
    try:
        binding = validate_pre_reboot_observer_binding(
            binding,
            expected_realpath=spec.bridge_realpath,
        )
        ncm_identity = validate_post_reboot_ncm_identity(
            binding,
            ncm_identity,
            require_live=False,
        )
    except ContractError:
        return False
    ncm = observation.get("host_ncm_rebind")
    continuity = observation.get("debian_ncm_continuity")
    ready = ncm.get("ready") if isinstance(ncm, dict) else None
    profile = ncm.get("profile_check") if isinstance(ncm, dict) else None
    ssh = observation.get("ssh")
    service = observation.get("phase3_service")
    returned = observation.get("candidate_return")
    return_epoch = returned.get("return_epoch") if isinstance(returned, dict) else None
    returned_serial = (
        return_epoch.get("returned") if isinstance(return_epoch, dict) else None
    )
    returned_usb_identity = (
        return_epoch.get("returned_usb_identity")
        if isinstance(return_epoch, dict)
        else None
    )
    before_ncm = (
        return_epoch.get("before_ncm") if isinstance(return_epoch, dict) else None
    )
    returned_epoch_exact = (
        isinstance(return_epoch, dict)
        and set(return_epoch)
        == {"before_ncm", "returned", "returned_usb_identity", "changed"}
        and return_epoch.get("changed") is True
        and isinstance(before_ncm, dict)
        and set(before_ncm) == {"usb_busnum", "usb_devnum"}
        and exact_int(before_ncm.get("usb_busnum"), ncm_identity["usb_busnum"])
        and exact_int(before_ncm.get("usb_devnum"), ncm_identity["usb_devnum"])
        and isinstance(returned_serial, dict)
        and set(returned_serial)
        == {
            "schema",
            "selected_realpath",
            "tty_st_dev",
            "tty_st_ino",
            "tty_st_rdev",
            "usb_busnum",
            "usb_devnum",
        }
        and returned_serial.get("schema") == base.RETURN_EPOCH_SCHEMA
        and returned_serial.get("selected_realpath") == spec.bridge_realpath
        and all(
            type(returned_serial.get(key)) is int and returned_serial[key] >= 0
            for key in (
                "tty_st_dev",
                "tty_st_ino",
                "tty_st_rdev",
                "usb_busnum",
                "usb_devnum",
            )
        )
        and returned_serial.get("usb_busnum", 0) >= 1
        and returned_serial.get("usb_devnum", 0) >= 1
        and isinstance(returned_usb_identity, dict)
        and set(returned_usb_identity)
        == {
            "usb_topology",
            "usb_serial_sha256",
            "usb_vendor",
            "usb_product",
            "usb_busnum",
            "usb_devnum",
        }
        and returned_usb_identity.get("usb_topology")
        == binding["usb_identity"]["usb_topology"]
        and returned_usb_identity.get("usb_serial_sha256")
        == binding["usb_identity"]["usb_serial_sha256"]
        and returned_usb_identity.get("usb_vendor")
        == binding["usb_identity"]["usb_vendor"]
        and returned_usb_identity.get("usb_product")
        == binding["usb_identity"]["usb_product"]
        and exact_int(
            returned_usb_identity.get("usb_busnum"),
            returned_serial["usb_busnum"],
        )
        and exact_int(
            returned_usb_identity.get("usb_devnum"),
            returned_serial["usb_devnum"],
        )
        and (
            returned_serial["usb_busnum"],
            returned_serial["usb_devnum"],
        )
        not in {
            (
                binding["usb_identity"]["usb_busnum"],
                binding["usb_identity"]["usb_devnum"],
            ),
            (ncm_identity["usb_busnum"], ncm_identity["usb_devnum"]),
        }
    )
    return (
        observation.get("proof") is True
        and isinstance(ncm, dict)
        and ncm.get("same_bound_usb_identity") is True
        and ncm.get("acm_required") is False
        and exact_int(ncm.get("exact_interface_count"), 1)
        and ncm.get("profile_bound") is True
        and type(ncm.get("mutated")) is bool
        and isinstance(continuity, dict)
        and set(continuity) == {"before_ssh", "after_ssh", "after_service"}
        and all(value is True for value in continuity.values())
        and isinstance(ready, dict)
        and set(ready)
        == {
            "verified_a90_ncm",
            "direct_route",
            "host_cidr_present",
            "device_ping",
        }
        and all(value is True for value in ready.values())
        and isinstance(profile, dict)
        and profile.get("command")
        == [
            "nmcli",
            "-g",
            "connection.type",
            "connection",
            "show",
            spec.observer_host_ncm_profile,
        ]
        and exact_int(profile.get("returncode"), 0)
        and str(profile.get("stdout") or "").strip()
        == base.HOST_NCM_CONNECTION_TYPE
        and isinstance(ssh, dict)
        and ssh.get("proof") is True
        and isinstance(service, dict)
        and service.get("proof") is True
        and isinstance(returned, dict)
        and returned.get("exact_bridge") is True
        and returned.get("native_epoch_version_proven") is True
        and exact_int(returned.get("device_command_sequences"), 1)
        and returned_epoch_exact
    )


def validate_benchmark_selection(parsed: dict[str, Any]) -> None:
    selection = parsed.get("selection")
    if (
        not isinstance(selection, dict)
        or set(selection)
        != {
            "contract",
            "log_relation",
            "opening_marker_count",
            "appended_marker_count",
            "opening_markers_sha256",
            "appended_markers_sha256",
        }
        or selection.get("contract")
        != "opening-prefix-or-disjoint-current-window-v2"
        or selection.get("log_relation")
        not in {
            "opening-prefix-appended-suffix",
            "disjoint-current-window",
        }
        or type(selection.get("opening_marker_count")) is not int
        or selection.get("opening_marker_count") <= 0
        or type(selection.get("appended_marker_count")) is not int
        or selection.get("appended_marker_count") <= 0
        or HEX64_RE.fullmatch(str(selection.get("opening_markers_sha256") or ""))
        is None
        or HEX64_RE.fullmatch(str(selection.get("appended_markers_sha256") or ""))
        is None
        or type(parsed.get("selected_segment_index")) is not int
        or parsed.get("selected_segment_index") != 0
    ):
        raise ContractError("benchmark appended-marker selection changed")
    records = parsed.get("records")
    if not isinstance(records, list) or not records:
        raise ContractError("benchmark appended-marker selection changed")
    native_failed = parsed.get("native_handoff_failed")
    boot_segments_total = parsed.get("boot_segments_total")
    if type(boot_segments_total) is not int:
        raise ContractError("benchmark appended-marker selection changed")
    if native_failed is True:
        expected_segments = 1
        expected_marker_counts = {len(records)}
    elif native_failed is False:
        if selection["log_relation"] == "disjoint-current-window":
            expected_segments = 2
            expected_marker_counts = {len(records) + len(RETURNED_NATIVE_TAIL)}
        elif boot_segments_total in {1, 2}:
            expected_segments = boot_segments_total
            expected_marker_counts = {len(records)}
            if expected_segments == 2:
                expected_marker_counts = {
                    len(records) + len(RETURNED_NATIVE_TAIL),
                    len(records)
                    + len(benchmark.OPTIONAL_EARLY_STAGES)
                    + len(RETURNED_NATIVE_TAIL),
                }
        else:
            raise ContractError("benchmark appended-marker selection changed")
    else:
        raise ContractError("benchmark appended-marker selection changed")
    if (
        boot_segments_total != expected_segments
        or selection.get("appended_marker_count") not in expected_marker_counts
    ):
        raise ContractError("benchmark appended-marker selection changed")


def finalize_cycle(
    spec: resident.SessionSpec,
    args: argparse.Namespace,
    observation: dict[str, Any],
    *,
    intent_sha256: str,
    opening_log_record: dict[str, Any],
    visible_confirmed: str,
    cleanup_evidence: dict[str, Any],
    source_identity: dict[str, int],
) -> dict[str, Any]:
    status_record, status = require_auto_status(args, enable=1, latch=1)
    final_preflight, final_evidence, _ = fast_resident_preflight(
        spec,
        args,
        expected_state="receipt-verified",
        expected_identity=source_identity,
    )
    final_preflight.validate()
    log_record = base.run_f1_cmd(args, ["logcat"])
    log_text = str(log_record.get("text") or "")
    parsed_benchmark = parse_appended_benchmark(opening_log_record, log_record)
    ssh = observation.get("ssh")
    service = observation.get("phase3_service")
    facts: dict[str, Any] = {}
    if isinstance(ssh, dict) and isinstance(service, dict):
        classified = base.display.classify_phase2_display_facts(
            handoff_log=_native_release_log(log_text),
            native_release_marker=str(ssh.get("native_release_marker_text") or ""),
            pid1_comm_init=ssh.get("pid1_comm_init"),
            proc1_exe_init=ssh.get("proc1_exe_init"),
            dropbear_started=service.get("proof") is True,
            display_status=str(ssh.get("display_status")),
        )
        facts = base.display.facts_to_dict(classified)
    durable_evidence = ondevice_evidence.evaluate(log_text, intent_sha256)
    mechanical = durable_evidence["proof"] is True
    # Exact returned enable/latch and final resident D0 were proved above.
    # The returned latch and final resident D0 remain authoritative for health;
    # the later exact ACM epoch is independently retained in host_link proof.
    returned = status.get("enable") == 1 and status.get("latch") == 1
    guard_released = observation.get("guard_release", {}).get("released") is True
    host_link = host_link_proven(spec, observation)
    native_handoff_failed = parsed_benchmark.get("native_handoff_failed") is True
    if returned and native_handoff_failed:
        terminal = "REFUTED_AUTO_HANDOFF_NATIVE_HANDOFF_RESIDENT_HEALTHY"
    elif returned and mechanical and host_link and guard_released:
        terminal = (
            "PASS_AUTO_HANDOFF_BENCHMARK_VISIBLE"
            if visible_confirmed == "yes"
            else "REFUTED_AUTO_HANDOFF_DISPLAY_VISIBILITY"
            if visible_confirmed == "no"
            else "PASS_AUTO_HANDOFF_BENCHMARK_NO_PROOF_VISIBILITY"
        )
    else:
        terminal = "NO_PROOF_OBSERVER_RESIDENT_HEALTHY"
    return {
        "schema": RESULT_SCHEMA,
        "intent_sha256": intent_sha256,
        "terminal": terminal,
        "resident_healthy": True,
        "candidate_replay": False,
        "arm_dispatch_count": 1,
        "reboot_dispatch_count": 1,
        "auto_handoff_status": status,
        "auto_handoff_status_record": status_record,
        "final_preflight": final_evidence,
        "work_cleanup": cleanup_evidence,
        "observation": observation,
        "display_facts": facts,
        "ondevice_evidence": durable_evidence,
        "durable_evidence_log_record": log_record,
        "visible_confirmed": visible_confirmed,
        "benchmark": parsed_benchmark,
        "telemetry_scope": (
            "temperature-clock-power-memory-load and absolute mmc counters; "
            "mmc counters are observer-inclusive, not isolated workload writes"
        ),
        "payload_transfer": False,
        "partition_write": False,
        "flash": False,
    }


def validate_result(
    spec: resident.SessionSpec,
    value: Any,
    intent_sha256: str,
    *,
    expected_source_identity: dict[str, int] | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("benchmark result is not an object")
    expected_keys = {
        "schema", "intent_sha256", "terminal", "resident_healthy", "candidate_replay",
        "arm_dispatch_count", "reboot_dispatch_count", "auto_handoff_status",
        "auto_handoff_status_record", "final_preflight", "work_cleanup",
        "observation", "display_facts", "ondevice_evidence",
        "durable_evidence_log_record", "visible_confirmed", "benchmark",
        "telemetry_scope", "payload_transfer", "partition_write", "flash",
    }
    allowed_terminal = {
        "PASS_AUTO_HANDOFF_BENCHMARK_VISIBLE",
        "REFUTED_AUTO_HANDOFF_DISPLAY_VISIBILITY",
        "REFUTED_AUTO_HANDOFF_NATIVE_HANDOFF_RESIDENT_HEALTHY",
        "PASS_AUTO_HANDOFF_BENCHMARK_NO_PROOF_VISIBILITY",
        "NO_PROOF_OBSERVER_RESIDENT_HEALTHY",
    }
    if (
        set(value) != expected_keys
        or value.get("schema") != RESULT_SCHEMA
        or value.get("intent_sha256") != intent_sha256
        or value.get("terminal") not in allowed_terminal
        or value.get("resident_healthy") is not True
        or value.get("candidate_replay") is not False
        or not exact_int(value.get("arm_dispatch_count"), 1)
        or not exact_int(value.get("reboot_dispatch_count"), 1)
        or value.get("visible_confirmed") not in {"yes", "no", "unavailable"}
        or value.get("telemetry_scope")
        != (
            "temperature-clock-power-memory-load and absolute mmc counters; "
            "mmc counters are observer-inclusive, not isolated workload writes"
        )
        or value.get("payload_transfer") is not False
        or value.get("partition_write") is not False
        or value.get("flash") is not False
        or not isinstance(value.get("observation"), dict)
        or not isinstance(value.get("display_facts"), dict)
    ):
        raise ContractError("benchmark result terminal contract changed")
    durable_log = base.require_exact_f1_command_receipt(
        value.get("durable_evidence_log_record"),
        ["logcat"],
        "result durable evidence log",
    )
    durable_evidence = ondevice_evidence.evaluate(
        str(durable_log.get("text") or ""),
        intent_sha256,
    )
    if value.get("ondevice_evidence") != durable_evidence:
        raise ContractError("benchmark result durable evidence changed")
    guard_released = value["observation"].get("guard_release", {}).get(
        "released"
    ) is True
    host_link = host_link_proven(spec, value["observation"])
    parsed = value.get("benchmark")
    native_handoff_failed = (
        isinstance(parsed, dict)
        and parsed.get("native_handoff_failed") is True
    )
    if native_handoff_failed:
        expected_terminal = "REFUTED_AUTO_HANDOFF_NATIVE_HANDOFF_RESIDENT_HEALTHY"
    elif durable_evidence["proof"] is True and host_link and guard_released:
        expected_terminal = (
            "PASS_AUTO_HANDOFF_BENCHMARK_VISIBLE"
            if value.get("visible_confirmed") == "yes"
            else "REFUTED_AUTO_HANDOFF_DISPLAY_VISIBILITY"
            if value.get("visible_confirmed") == "no"
            else "PASS_AUTO_HANDOFF_BENCHMARK_NO_PROOF_VISIBILITY"
        )
    else:
        expected_terminal = "NO_PROOF_OBSERVER_RESIDENT_HEALTHY"
    if value.get("terminal") != expected_terminal:
        raise ContractError("benchmark result durable terminal changed")
    status_record = base.require_exact_f1_command_receipt(
        value.get("auto_handoff_status_record"),
        ["auto-handoff-status"],
        "result auto-handoff status",
    )
    status = parse_auto_status(status_record)
    if (
        value.get("auto_handoff_status") != status
        or status.get("enable") != 1
        or status.get("latch") != 1
    ):
        raise ContractError("benchmark result does not prove returned H10 latch")
    validate_preflight_evidence(
        spec,
        value.get("final_preflight"),
        expected_state="receipt-verified",
        expected_identity=expected_source_identity,
    )
    cleanup = value.get("work_cleanup")
    if not isinstance(cleanup, dict) or set(cleanup) != {
        "dispatch_count", "inferred_from_absence", "receipt", "absence_preflight"
    }:
        raise ContractError("benchmark result cleanup evidence changed")
    if cleanup.get("inferred_from_absence") is not True:
        raise ContractError("benchmark result cleanup disposition changed")
    if (
        not exact_int(cleanup.get("dispatch_count"), 0)
        or cleanup.get("receipt") is not None
    ):
        raise ContractError("benchmark result H10 absence close dispatched cleanup")
    validate_preflight_evidence(
        spec,
        cleanup.get("absence_preflight"),
        expected_state="receipt-verified",
        expected_identity=expected_source_identity,
    )
    if not isinstance(parsed, dict):
        raise ContractError("benchmark result is not an object")
    parsed_stages = [record.get("stage") for record in parsed.get("records", [])]
    if parsed.get("native_handoff_failed") is True:
        expected_missing = [
            stage for stage in benchmark.COMPLETE_STAGES
            if stage not in parsed_stages
        ]
        benchmark_shape_ok = (
            len(parsed_stages) == len(set(parsed_stages))
            and failed_handoff_stages_exact(parsed_stages)
            and parsed.get("missing_complete_stages") == expected_missing
            and parsed.get("status")
            == ("partial" if expected_missing else "complete")
        )
    elif parsed.get("native_handoff_failed") is False:
        benchmark_shape_ok = (
            parsed.get("status") == "complete"
            and parsed.get("missing_complete_stages") == []
            and parsed_stages
            in (
                list(benchmark.COMPLETE_STAGES),
                list(benchmark.OPTIONAL_EARLY_STAGES + benchmark.COMPLETE_STAGES),
            )
        )
    else:
        benchmark_shape_ok = False
    if (
        parsed.get("schema") != benchmark.RESULT_SCHEMA
        or not benchmark_shape_ok
        or parsed.get("boot_segments_total") is None
        or type(parsed.get("selected_segment_index")) is not int
    ):
        raise ContractError("benchmark result is not one exact terminal segment")
    validate_benchmark_selection(parsed)
    return value


def dispatch_arm_once_and_publish(
    args: argparse.Namespace,
    *,
    journal_path: Path,
    intent_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Dispatch once, publish every outcome, and continue only from exact armed state."""

    command = ["auto-handoff-arm", ARM_TOKEN, intent_sha256]
    try:
        arm_record: dict[str, Any] = base.run_f1_cmd(
            args,
            command,
            allow_error=True,
        )
    except Exception as exc:  # durable unknown; never replay
        arm_record = {
            "error": {"type": type(exc).__name__, "message": str(exc)},
            "response_proof": False,
        }
    try:
        post_arm_record, post_arm_status = read_auto_status(args)
    except Exception as exc:  # preserve the arm receipt before stopping observation
        post_arm_record = {
            "error": {"type": type(exc).__name__, "message": str(exc)},
            "response_proof": False,
        }
        post_arm_status = None
    write_record(
        journal_path,
        "arm-result",
        {
            "intent_sha256": intent_sha256,
            "arm_dispatch_count": 1,
            "arm_record": arm_record,
            "post_arm_status_record": post_arm_record,
            "post_arm_status": post_arm_status,
        },
    )

    if "command" in arm_record:
        _, arm_outcome = require_exact_arm_dispatch_receipt(
            arm_record,
            intent_sha256,
        )
    elif _is_unproved_receipt(arm_record):
        arm_outcome = "unproved"
    else:
        raise ContractError("published arm dispatch record is not exact")

    state = None if post_arm_status is None else (
        post_arm_status.get("enable"),
        post_arm_status.get("latch"),
    )
    if arm_outcome == "refused-unarmed":
        if state == (0, 0):
            raise ContractError("auto-handoff arm was explicitly refused with no effect")
        raise ContractError("auto-handoff arm refusal contradicts post-arm state")
    if arm_outcome != "armed":
        raise ContractError("auto-handoff arm outcome is unproved; no replay or reboot")
    if state != (1, 0):
        raise ContractError("auto-handoff arm outcome is not exact armed state")
    return arm_record, post_arm_status


def _continue_after_proved_arm(
    spec: resident.SessionSpec,
    args: argparse.Namespace,
    path: Path,
    *,
    expected_closure_sha256: str,
    source_identity: dict[str, int],
    intent_sha256: str,
    opening_log_record: dict[str, Any],
    visible_confirmed: str,
) -> dict[str, Any]:
    """Continue one journal-bound ordinal without ever dispatching arm again."""

    require_execution_closure(expected_closure_sha256)
    require_auto_status(args, enable=1, latch=0)
    armed_preflight, armed_evidence, _ = fast_resident_preflight(
        spec,
        args,
        expected_state="receipt-verified",
        expected_identity=source_identity,
    )
    armed_preflight.validate()
    f1_spec = _f1_spec(spec)
    guard = base.arm_candidate_return_modemmanager_guard(f1_spec, args, path)
    try:
        pre_reboot_epoch = capture_pre_reboot_observer_binding(f1_spec, args)
        require_auto_status(args, enable=1, latch=0)
        if not guard.healthy(recheck=True):
            raise ContractError("candidate-return guard was lost before reboot intent")
        require_pre_reboot_observer_binding_current(
            f1_spec,
            args,
            pre_reboot_epoch,
        )
        write_record(
            path / JOURNAL_NAMES[3],
            "reboot-intent",
            {
                "intent_sha256": intent_sha256,
                "execution_closure_sha256": expected_closure_sha256,
                "armed_preflight": armed_evidence,
                "pre_reboot_epoch": pre_reboot_epoch,
                "reboot_dispatch_count_max": 1,
                "candidate_replay": False,
            },
        )
        require_execution_closure(expected_closure_sha256)
        require_auto_status(args, enable=1, latch=0)
        if not guard.healthy(recheck=True):
            raise ContractError("candidate-return guard was lost before reboot dispatch")
        require_pre_reboot_observer_binding_current(
            f1_spec,
            args,
            pre_reboot_epoch,
        )
        reboot_record = send_reboot_once(args)
    except Exception:
        try:
            base.release_candidate_return_modemmanager_guard(guard, path)
        except Exception:  # preserve the pre-dispatch failure
            pass
        raise
    observation = observe_auto_cycle(spec, args, path, guard, pre_reboot_epoch)
    observation["reboot_record"] = reboot_record
    write_record(
        path / JOURNAL_NAMES[4],
        "observation",
        {
            "intent_sha256": intent_sha256,
            "arm_dispatch_count": 1,
            "reboot_dispatch_count": 1,
            "candidate_replay": False,
            "observation": observation,
        },
    )
    returned_status_record, returned_status = require_auto_status(
        args,
        enable=1,
        latch=1,
    )
    write_record(
        path / JOURNAL_NAMES[5],
        "absence-close-intent",
        {
            "intent_sha256": intent_sha256,
            "manifest_sha256": spec.manifest_sha256,
            "cleanup_dispatch_count_max": 0,
            "arm_dispatch_count": 1,
            "reboot_dispatch_count": 1,
            "candidate_replay": False,
            "returned_status": returned_status,
            "returned_status_record": returned_status_record,
        },
    )
    absence_preflight, absence_evidence, _ = fast_resident_preflight(
        spec,
        args,
        expected_state="receipt-verified",
        expected_identity=source_identity,
    )
    absence_preflight.validate()
    cleanup_evidence = {
        "dispatch_count": 0,
        "inferred_from_absence": True,
        "receipt": None,
        "absence_preflight": absence_evidence,
    }
    write_record(
        path / JOURNAL_NAMES[6],
        "absence-close-result",
        {
            "intent_sha256": intent_sha256,
            "cleanup_dispatch_count": 0,
            "cleanup_record": None,
            "absence_preflight": absence_evidence,
            "inferred_from_absence": True,
            "candidate_replay": False,
        },
    )
    result = finalize_cycle(
        spec,
        args,
        observation,
        intent_sha256=intent_sha256,
        opening_log_record=opening_log_record,
        visible_confirmed=visible_confirmed,
        cleanup_evidence=cleanup_evidence,
        source_identity=source_identity,
    )
    result = validate_result(
        spec,
        result,
        intent_sha256,
        expected_source_identity=source_identity,
    )
    result_sha256 = base.json_sha256(result)
    write_record(
        path / JOURNAL_NAMES[7],
        "final-health",
        {
            "intent_sha256": intent_sha256,
            "result_sha256": result_sha256,
            "result": result,
        },
    )
    write_record(
        path / JOURNAL_NAMES[8],
        "closed",
        {"result_sha256": result_sha256, "result": result},
    )
    return result


def execute(
    spec: resident.SessionSpec,
    *,
    transaction_dir: Path,
    expected_closure_sha256: str,
    operator_attended: bool,
    visible_confirmed: str,
) -> dict[str, Any]:
    if operator_attended is not True:
        raise ContractError("operator attendance is required for this D1 ordinal")
    if spec.candidate_version != EXPECTED_VERSION or spec.candidate_build != EXPECTED_BUILD:
        raise ContractError("installed resident is not the exact H10 benchmark candidate")
    closure = require_execution_closure(expected_closure_sha256)
    path = exact_transaction_dir(spec, transaction_dir)
    if path.exists() or path.is_symlink():
        raise ContractError("transaction directory already exists; use --reconcile")
    path.mkdir(parents=True, mode=0o700)
    os.chmod(path, 0o700)
    args = _effect_args()
    opening_preflight, opening_evidence, source_identity = fast_resident_preflight(
        spec,
        args,
        expected_state="receipt-absent",
    )
    opening_preflight.validate()
    status_record, status = require_auto_status(args, enable=0, latch=0)
    first_log = base.run_f1_cmd(args, ["logcat"])
    require_first_boot_unarmed(first_log)
    write_record(
        path / JOURNAL_NAMES[0],
        "open-native-healthy-unarmed",
        {
            "manifest_sha256": spec.manifest_sha256,
            "execution_closure": closure,
            "candidate_sha256": spec.candidate.sha256,
            "rollback_sha256": spec.rollback.sha256,
            "rootfs_sha256": spec.rootfs.sha256,
            "opening_preflight": opening_evidence,
            "auto_status": status,
            "auto_status_record": status_record,
            "first_boot_log": first_log,
            "first_boot_log_sha256": hashlib.sha256(
                str(first_log.get("text") or "").encode("utf-8")
            ).hexdigest(),
            "first_boot_unarmed": True,
        },
    )
    require_execution_closure(expected_closure_sha256)
    arm_intent_path = path / JOURNAL_NAMES[1]
    write_record(
        arm_intent_path,
        "arm-intent",
        {
            "manifest_sha256": spec.manifest_sha256,
            "execution_closure_sha256": expected_closure_sha256,
            "arm_dispatch_count_max": 1,
            "reboot_dispatch_count": 0,
            "candidate_replay": False,
        },
    )
    intent_sha256 = sha256_file(arm_intent_path)
    dispatch_arm_once_and_publish(
        args,
        journal_path=path / JOURNAL_NAMES[2],
        intent_sha256=intent_sha256,
    )
    return _continue_after_proved_arm(
        spec,
        args,
        path,
        expected_closure_sha256=expected_closure_sha256,
        source_identity=source_identity,
        intent_sha256=intent_sha256,
        opening_log_record=first_log,
        visible_confirmed=visible_confirmed,
    )


def resume_after_proved_arm(
    spec: resident.SessionSpec,
    *,
    transaction_dir: Path,
    expected_closure_sha256: str,
    expected_journal_closure_sha256: str,
    operator_attended: bool,
    visible_confirmed: str,
) -> dict[str, Any]:
    """Resume at reboot intent from exactly one durable, proved arm result."""

    if operator_attended is not True:
        raise ContractError("operator attendance is required for armed D1 resume")
    if (
        expected_journal_closure_sha256
        != ARMED_RESUME_PREDECESSOR_CLOSURE_SHA256
    ):
        raise ContractError("armed resume predecessor closure is not exact")
    if spec.candidate_version != EXPECTED_VERSION or spec.candidate_build != EXPECTED_BUILD:
        raise ContractError("installed resident is not the exact H10 benchmark candidate")
    path = exact_transaction_dir(spec, transaction_dir)
    if not path.is_dir() or path.is_symlink():
        raise ContractError("armed-resume transaction directory is not exact")
    records = load_journal_prefix(
        spec,
        path,
        expected_closure_sha256,
        journal_closure_sha256=expected_journal_closure_sha256,
    )
    if len(records) != 3:
        raise ContractError("armed resume requires the exact three-record prefix")
    source_identity = validate_preflight_evidence(
        spec,
        records[0]["opening_preflight"],
        expected_state="receipt-absent",
    )
    intent_sha256 = sha256_file(path / JOURNAL_NAMES[1])
    _, arm_outcome = require_exact_arm_dispatch_receipt(
        records[2]["arm_record"],
        intent_sha256,
    )
    post_status = records[2]["post_arm_status"]
    if (
        arm_outcome != "armed"
        or not isinstance(post_status, dict)
        or post_status.get("enable") != 1
        or post_status.get("latch") != 0
    ):
        raise ContractError("armed resume lacks one exact durable armed result")
    args = _effect_args()
    return _continue_after_proved_arm(
        spec,
        args,
        path,
        expected_closure_sha256=expected_closure_sha256,
        source_identity=source_identity,
        intent_sha256=intent_sha256,
        opening_log_record=records[0]["first_boot_log"],
        visible_confirmed=visible_confirmed,
    )


def resume_after_return(
    spec: resident.SessionSpec,
    *,
    transaction_dir: Path,
    expected_closure_sha256: str,
    expected_journal_closure_sha256: str | None = None,
    operator_attended: bool,
    visible_confirmed: str,
) -> dict[str, Any]:
    """Finish only absence/final health after a durably observed return."""

    if operator_attended is not True:
        raise ContractError("operator attendance is required for D1 finalization")
    if spec.candidate_version != EXPECTED_VERSION or spec.candidate_build != EXPECTED_BUILD:
        raise ContractError("installed resident is not the exact H10 benchmark candidate")
    path = exact_transaction_dir(spec, transaction_dir)
    if not path.is_dir() or path.is_symlink():
        raise ContractError("resume transaction directory is not exact")
    records = load_journal_prefix(
        spec,
        path,
        expected_closure_sha256,
        journal_closure_sha256=expected_journal_closure_sha256,
    )
    if len(records) < 5:
        raise ContractError("resume lacks one durable automatic-cycle observation")
    if expected_journal_closure_sha256 is not None:
        if (
            expected_journal_closure_sha256
            == ARMED_RESUME_PREDECESSOR_CLOSURE_SHA256
        ):
            if not 5 <= len(records) <= len(JOURNAL_NAMES):
                raise ContractError(
                    "armed-successor historical tail requires prefix 5 through 9"
                )
        elif len(records) != 7:
            raise ContractError(
                "historical-closure tail repair requires the exact post-absence prefix"
            )
    if len(records) == len(JOURNAL_NAMES):
        return validate_result(
            spec,
            records[-1]["result"],
            records[4]["intent_sha256"],
        )
    if len(records) == 8:
        # Only the host-side publication record is absent.  Never turn this
        # append-only repair into a new device observation or D1 effect.
        result = validate_result(
            spec,
            records[7]["result"],
            records[4]["intent_sha256"],
        )
        result_sha256 = records[7]["result_sha256"]
        write_record(
            path / JOURNAL_NAMES[8],
            "closed",
            {"result_sha256": result_sha256, "result": result},
        )
        load_journal_prefix(
            spec,
            path,
            expected_closure_sha256,
            journal_closure_sha256=expected_journal_closure_sha256,
        )
        return result

    args = _effect_args()
    observation = records[4]["observation"]
    intent_sha256 = records[4]["intent_sha256"]
    source_identity = validate_preflight_evidence(
        spec,
        records[0]["opening_preflight"],
        expected_state="receipt-absent",
    )

    if len(records) == 5:
        returned_status_record, returned_status = require_auto_status(
            args,
            enable=1,
            latch=1,
        )
        write_record(
            path / JOURNAL_NAMES[5],
            "absence-close-intent",
            {
                "intent_sha256": intent_sha256,
                "manifest_sha256": spec.manifest_sha256,
                "cleanup_dispatch_count_max": 0,
                "arm_dispatch_count": 1,
                "reboot_dispatch_count": 1,
                "candidate_replay": False,
                "returned_status": returned_status,
                "returned_status_record": returned_status_record,
            },
        )
        absence_preflight, absence_evidence, _ = fast_resident_preflight(
            spec,
            args,
            expected_state="receipt-verified",
            expected_identity=source_identity,
        )
        absence_preflight.validate()
        write_record(
            path / JOURNAL_NAMES[6],
            "absence-close-result",
            {
                "intent_sha256": intent_sha256,
                "cleanup_dispatch_count": 0,
                "cleanup_record": None,
                "absence_preflight": absence_evidence,
                "inferred_from_absence": True,
                "candidate_replay": False,
            },
        )
        cleanup_evidence = {
            "dispatch_count": 0,
            "inferred_from_absence": True,
            "receipt": None,
            "absence_preflight": absence_evidence,
        }
    elif len(records) == 6:
        # The zero-dispatch close intent is durable. Re-read exact absence and
        # receipt metadata; never create or remove a work file.
        preflight, absence_evidence, _ = fast_resident_preflight(
            spec,
            args,
            expected_state="receipt-verified",
            expected_identity=source_identity,
        )
        preflight.validate()
        write_record(
            path / JOURNAL_NAMES[6],
            "absence-close-result",
            {
                "intent_sha256": intent_sha256,
                "cleanup_dispatch_count": 0,
                "cleanup_record": None,
                "absence_preflight": absence_evidence,
                "inferred_from_absence": True,
                "candidate_replay": False,
            },
        )
        cleanup_evidence = {
            "dispatch_count": 0,
            "inferred_from_absence": True,
            "receipt": None,
            "absence_preflight": absence_evidence,
        }
    else:
        cleanup_record = records[6]
        cleanup_evidence = {
            "dispatch_count": cleanup_record["cleanup_dispatch_count"],
            "inferred_from_absence": cleanup_record["inferred_from_absence"],
            "receipt": cleanup_record["cleanup_record"],
            "absence_preflight": cleanup_record["absence_preflight"],
        }

    records = load_journal_prefix(
        spec,
        path,
        expected_closure_sha256,
        journal_closure_sha256=expected_journal_closure_sha256,
    )
    if len(records) == 7:
        result = finalize_cycle(
            spec,
            args,
            observation,
            intent_sha256=intent_sha256,
            opening_log_record=records[0]["first_boot_log"],
            visible_confirmed=visible_confirmed,
            cleanup_evidence=cleanup_evidence,
            source_identity=source_identity,
        )
        result = validate_result(
            spec,
            result,
            intent_sha256,
            expected_source_identity=source_identity,
        )
        result_sha256 = base.json_sha256(result)
        write_record(
            path / JOURNAL_NAMES[7],
            "final-health",
            {
                "intent_sha256": intent_sha256,
                "result_sha256": result_sha256,
                "result": result,
            },
        )
    else:
        result = validate_result(
            spec,
            records[7]["result"],
            intent_sha256,
            expected_source_identity=source_identity,
        )
        result_sha256 = records[7]["result_sha256"]
    records = load_journal_prefix(
        spec,
        path,
        expected_closure_sha256,
        journal_closure_sha256=expected_journal_closure_sha256,
    )
    if len(records) == 8:
        write_record(
            path / JOURNAL_NAMES[8],
            "closed",
            {"result_sha256": result_sha256, "result": result},
        )
    load_journal_prefix(
        spec,
        path,
        expected_closure_sha256,
        journal_closure_sha256=expected_journal_closure_sha256,
    )
    return result


def reconcile(
    spec: resident.SessionSpec,
    *,
    transaction_dir: Path,
    expected_closure_sha256: str,
    expected_journal_closure_sha256: str | None = None,
) -> dict[str, Any]:
    """Read-only device reconciliation; never arm, reboot, hand off, or replay."""

    require_execution_closure(expected_closure_sha256)
    path = exact_transaction_dir(spec, transaction_dir)
    if not path.is_dir() or path.is_symlink():
        raise ContractError("reconciliation transaction directory is not exact")
    try:
        records = load_journal_prefix(
            spec,
            path,
            expected_closure_sha256,
            journal_closure_sha256=expected_journal_closure_sha256,
        )
    except Exception as exc:
        return {
            "schema": RECONCILE_SCHEMA,
            "terminal": "JOURNAL_INCONSISTENT_STOP",
            "journal_error": {"type": type(exc).__name__, "message": str(exc)},
            "arm_dispatch_count": None,
            "reboot_dispatch_count": None,
            "candidate_replay": False,
            "device_effect": None,
        }
    present = list(JOURNAL_NAMES[: len(records)])
    if not records:
        return {
            "schema": RECONCILE_SCHEMA,
            "terminal": "NO_DURABLE_EFFECT_EVIDENCE",
            "journal_records_present": [],
            "arm_dispatch_count": 0,
            "reboot_dispatch_count": 0,
            "candidate_replay": False,
            "device_effect": False,
        }
    if len(records) == len(JOURNAL_NAMES):
        return {
            "schema": RECONCILE_SCHEMA,
            "terminal": "CLOSED_EXACT_NO_REPLAY",
            "journal_records_present": present,
            "result": records[-1]["result"],
            "arm_dispatch_count": 1,
            "reboot_dispatch_count": 1,
            "candidate_replay": False,
            "device_effect": True,
        }
    args = _effect_args()
    status_record: dict[str, Any] | None = None
    status: dict[str, Any] | None = None
    status_error: dict[str, str] | None = None
    try:
        status_record = base.require_exact_f1_command_receipt(
            base.run_f1_cmd(args, ["auto-handoff-status"]),
            ["auto-handoff-status"],
            "reconciliation auto-handoff status",
        )
        status = parse_auto_status(status_record)
    except Exception as exc:  # endpoint absence is HEALTH_PENDING, never replay
        status_error = {"type": type(exc).__name__, "message": str(exc)}
    health: dict[str, Any] | None = None
    health_error: dict[str, str] | None = None
    try:
        health = resident.verify_resident_health_exact(spec, _f1_spec(spec), args)
    except Exception as exc:  # HEALTH_PENDING, never a reason to replay
        health_error = {"type": type(exc).__name__, "message": str(exc)}
    arm_dispatch_count: int | None = 1 if len(records) >= 3 else (
        None if len(records) >= 2 else 0
    )
    reboot_dispatch_count: int | None = 1 if len(records) >= 5 else (
        None if len(records) >= 4 else 0
    )
    device_effect: bool | None = None
    if len(records) >= 8:
        terminal = "RESULT_PUBLICATION_PENDING_NO_REPLAY"
        device_effect = True
    elif (
        len(records) >= 5
        and health is not None
        and status is not None
        and status["enable"] == 1
        and status["latch"] == 1
    ):
        terminal = "RETURNED_NATIVE_FINALIZATION_PENDING_NO_REPLAY"
        device_effect = True
    elif len(records) >= 4:
        terminal = "RECOVERY_PENDING_PARKED_NO_REPLAY"
        device_effect = True
    elif len(records) == 3:
        journal_status = records[2].get("post_arm_status")
        journal_arm = records[2].get("arm_record")
        if isinstance(journal_arm, dict) and "command" in journal_arm:
            _, journal_outcome = require_exact_arm_dispatch_receipt(
                journal_arm,
                records[2]["intent_sha256"],
            )
        else:
            journal_outcome = "unproved"
        if (
            journal_outcome == "refused-unarmed"
            and isinstance(journal_status, dict)
            and journal_status.get("enable") == 0
            and journal_status.get("latch") == 0
        ):
            terminal = "ARM_REFUSED_EXACT_NO_EFFECT_NO_REPLAY"
            device_effect = False
        elif (
            isinstance(journal_status, dict)
            and journal_status.get("enable") == 1
            and journal_status.get("latch") == 0
        ):
            terminal = "ARMED_REBOOT_NOT_DURABLY_INTENDED_NO_REPLAY"
            device_effect = True
        else:
            terminal = "ARM_OUTCOME_PENDING_NO_REPLAY"
    elif len(records) == 2:
        if status is not None and status["enable"] == 0 and status["latch"] == 0:
            terminal = "ARM_RESULT_PUBLICATION_MISSING_CURRENTLY_UNARMED_NO_REPLAY"
            device_effect = False
        else:
            terminal = "ARM_RESULT_PUBLICATION_MISSING_NO_REPLAY"
    else:
        terminal = "OPENED_NO_D1_INTENT"
        device_effect = False
    return {
        "schema": RECONCILE_SCHEMA,
        "terminal": terminal,
        "journal_records_present": present,
        "auto_handoff_status": status,
        "auto_handoff_status_record": status_record,
        "auto_handoff_status_error": status_error,
        "resident_health": health,
        "resident_health_error": health_error,
        "arm_dispatch_count": arm_dispatch_count,
        "reboot_dispatch_count": reboot_dispatch_count,
        "candidate_replay": False,
        "device_effect": device_effect,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-execution-closure", action="store_true")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--expect-manifest-sha256")
    parser.add_argument("--expect-execution-closure-sha256")
    parser.add_argument("--expect-journal-execution-closure-sha256")
    parser.add_argument("--transaction-dir", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--resume-after-proved-arm", action="store_true")
    modes.add_argument("--resume-after-return", action="store_true")
    modes.add_argument("--reconcile", action="store_true")
    parser.add_argument("--operator-attended", action="store_true")
    parser.add_argument(
        "--visible-confirmed",
        choices=("yes", "no", "unavailable"),
        default="unavailable",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.print_execution_closure:
        print(json.dumps(execution_closure(), indent=2, sort_keys=True))
        return 0
    required = (
        args.manifest,
        args.expect_manifest_sha256,
        args.expect_execution_closure_sha256,
        args.transaction_dir,
    )
    if any(value is None for value in required):
        raise ContractError("manifest, closure, and transaction arguments are required")
    spec = resident.load_spec(args.manifest, args.expect_manifest_sha256)
    if (
        args.expect_journal_execution_closure_sha256 is not None
        and not (
            args.resume_after_proved_arm
            or args.resume_after_return
            or args.reconcile
        )
    ):
        raise ContractError(
            "historical journal closure is valid only for exact no-replay resume"
        )
    if args.execute:
        result = execute(
            spec,
            transaction_dir=args.transaction_dir,
            expected_closure_sha256=args.expect_execution_closure_sha256,
            operator_attended=args.operator_attended,
            visible_confirmed=args.visible_confirmed,
        )
    elif args.resume_after_proved_arm:
        if args.expect_journal_execution_closure_sha256 is None:
            raise ContractError("armed resume requires the exact journal closure")
        result = resume_after_proved_arm(
            spec,
            transaction_dir=args.transaction_dir,
            expected_closure_sha256=args.expect_execution_closure_sha256,
            expected_journal_closure_sha256=(
                args.expect_journal_execution_closure_sha256
            ),
            operator_attended=args.operator_attended,
            visible_confirmed=args.visible_confirmed,
        )
    elif args.resume_after_return:
        result = resume_after_return(
            spec,
            transaction_dir=args.transaction_dir,
            expected_closure_sha256=args.expect_execution_closure_sha256,
            expected_journal_closure_sha256=(
                args.expect_journal_execution_closure_sha256
            ),
            operator_attended=args.operator_attended,
            visible_confirmed=args.visible_confirmed,
        )
    elif args.reconcile:
        result = reconcile(
            spec,
            transaction_dir=args.transaction_dir,
            expected_closure_sha256=args.expect_execution_closure_sha256,
            expected_journal_closure_sha256=(
                args.expect_journal_execution_closure_sha256
            ),
        )
    else:
        result = {
            "schema": SCHEMA,
            "host_only": True,
            "manifest_sha256": spec.manifest_sha256,
            "execution_closure": require_execution_closure(
                args.expect_execution_closure_sha256
            ),
            "transaction_dir": str(spec.transaction_dir),
            "live_authority": False,
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, resident.ContractError, base.ContractError) as exc:
        print(f"a90-auto-handoff-benchmark-runner-v1: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
