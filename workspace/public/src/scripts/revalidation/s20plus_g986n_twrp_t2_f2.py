#!/usr/bin/env python3
"""Connected owner for the exact S20+ TWRP T2 campaign.

This is deliberately a separate owner from the boot-only B0 process.  It can
address only the SHA-pinned T2 candidate and exact-stock rollback AP archives,
each containing one ``recovery.img.lz4`` member.  The live entrypoints remain
enabled only when the common and target recovery-only exception, this source,
its hostile tests, and its activation transition are all reviewed and active.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import sys
import time
from typing import Any, Sequence


REVALIDATION = Path(__file__).resolve().parent
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s20plus_g986n_boot_recovery_canary_b0_f1 as b0  # noqa: E402
import s20plus_g986n_twrp_t2_profile_h0 as h0  # noqa: E402
import s20plus_g986n_recovery_digest_profile_h0 as recovery_digest  # noqa: E402
import s20plus_g986n_twrp_t1_f2 as t1_predecessor  # noqa: E402


VERSION = "s20plus-g986n-twrp-t2-f2-v1"
PLAN_SCHEMA = "s20plus_g986n_twrp_t2_f2_plan_v1"
T2_F2_ACTIVE = False
EXPECTED_REVIEWED_NORMALIZED_SHA256 = "51e88d8c43cd2150a472528efe7352d22f3b1bb9d43457bfe2a5ac0a779a3ae9"

ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve()
RUN_ROOT = ROOT / "workspace/private/runs/s20plus-g986n-twrp-t2-f2"
CLAIM_ROOT = RUN_ROOT / "consumed-candidates"
SHARED_GUARD = ROOT / "workspace/private/runs/s20plus-g986n-routine-actions/active-action.json"
T1_PREDECESSOR_RUN_ID = "run-1788186109945582687"
T1_PREDECESSOR_RUN = (
    ROOT / "workspace/private/runs/s20plus-g986n-twrp-t1-f2" / T1_PREDECESSOR_RUN_ID
)
T1_PREDECESSOR_TERMINAL = T1_PREDECESSOR_RUN / "terminal.json"
T1_PREDECESSOR_TERMINAL_SIZE = 2_144
T1_PREDECESSOR_TERMINAL_SHA256 = (
    "9475e2cd6f283c7390b0d4b86b5e5208f0e943b2b452439febbe1dc3ca82cd7f"
)
T1_PREDECESSOR_OBSERVATION = T1_PREDECESSOR_RUN / "candidate-observation.json"
T1_PREDECESSOR_OBSERVATION_SIZE = 336
T1_PREDECESSOR_OBSERVATION_SHA256 = (
    "c2c1d123d1f26a2416252fc5da8c576efbb0bf2bd9527c2b2fcebd3529204e74"
)
T1_PREDECESSOR_OBSERVER_CAPTURE = (
    T1_PREDECESSOR_RUN / "candidate-recovery-observer-0001.capture.json"
)
T1_PREDECESSOR_OBSERVER_CAPTURE_SIZE = 546
T1_PREDECESSOR_OBSERVER_CAPTURE_SHA256 = (
    "bbd780281ffccf7991ad4a5b10c4ba063be9bc690422699b75a9b033159d024b"
)
T1_PREDECESSOR_OBSERVER_STDOUT = (
    T1_PREDECESSOR_RUN / "candidate-recovery-observer-0001.stdout"
)
T1_PREDECESSOR_OBSERVER_STDOUT_SIZE = 271
T1_PREDECESSOR_OBSERVER_STDOUT_SHA256 = (
    "c2c8b4e7393153ff40e1ca3487b76d8c345e1c2816636a6f30913e9d27baf0cc"
)

RUN_ID_RE = re.compile(r"run-[0-9]{19}")
HEX64_RE = re.compile(r"[0-9a-f]{64}")
APPROVAL_PREFIX = "S20PLUS-G986N-TWRP-T2-F2-APPROVE:"
PHYSICAL_PREFIX = "S20PLUS-G986N-T2-PHYSICAL-ROLLBACK-CONFIRM:"
APPROVAL_LIFETIME_SECONDS = 15 * 60
PHYSICAL_LIFETIME_SECONDS = 15 * 60
RECOVERY_WAIT_SECONDS = 90
ANDROID_WAIT_SECONDS = 420
MAX_RAW_BYTES = 8 * 1024 * 1024
DIRECT_RECOVERY_INSTRUCTION = (
    "Keep USB connected. Hold Side/Power + Volume Down until the display turns "
    "fully black; keep holding Side/Power, immediately release Volume Down and "
    "press Volume Up; keep Side/Power + Volume Up held until Recovery appears. "
    "Do not allow Android to boot."
)

RUN_NODE_NAMES = frozenset(
    {
        "allocation.json",
        "failure.json",
        "candidate-download-baseline.json",
        "prepared.json",
        "prepare-recovery-read-intent.json",
        "execute-pre-download-recovery-read-intent.json",
        "pre-candidate-abort-recovery-read-intent.json",
        "final-recovery-read-intent.json",
        "approval.json",
        "candidate-download-intent.json",
        "candidate-download-result.json",
        "candidate-download-arrival.json",
        "candidate-intent.json",
        "candidate-cage-quiescent.json",
        "candidate-result.json",
        "recovery-boot-intent.json",
        "candidate-observation-intent.json",
        "candidate-observation.json",
        "rollback-download-baseline.json",
        "rollback-download-intent.json",
        "rollback-download-result.json",
        "rollback-download-arrival.json",
        "physical-rollback-arm.json",
        "physical-rollback-confirmation.json",
        "physical-observation-intent.json",
        "physical-observation-miss.json",
        "physical-resume-observation-intent.json",
        "physical-resume-observation-miss.json",
        "rollback-intent.json",
        "rollback-cage-quiescent.json",
        "rollback-result.json",
        "final-health.json",
        "terminal.json",
    }
)
PHYSICAL_ROLLBACK_NODES = frozenset(
    {
        "physical-rollback-arm.json",
        "physical-rollback-confirmation.json",
        "physical-observation-intent.json",
        "physical-observation-miss.json",
        "physical-resume-observation-intent.json",
        "physical-resume-observation-miss.json",
    }
)
RAW_NODE_RE = re.compile(
    r"(?:"
    r"(?:prepare|execute-pre-download|pre-candidate-abort|final)-health-"
    r"(?:before|after)(?:-resume-[0-9]{4})?"
    r"|(?:prepare|execute-pre-download|pre-candidate-abort|final)-recovery-digest-[0-9]{4}"
    r"|candidate-download-[0-9]{4}"
    r"|candidate-transfer-[0-9]{4}"
    r"|candidate-recovery-observer-[0-9]{4}"
    r"|rollback-download-[0-9]{4}"
    r"|rollback-transfer-[0-9]{4}"
    r")\.(?:stdout|stderr|capture\.json)"
)

DEPENDENCIES = {
    "b0_primitives": (
        ROOT / "workspace/public/src/scripts/revalidation/s20plus_g986n_boot_recovery_canary_b0_f1.py",
        224_559,
        "82ec4cee48c3a39aa8dc4de6136e8fda3fbefe88d4821a71bdb0df55d2a17c2a",
    ),
    "t0_h0_base": (
        ROOT / "workspace/public/src/scripts/revalidation/s20plus_g986n_recovery_canary_t0_runner_h0.py",
        30_909,
        "3eb7cd148477c4e28d8bf1102a22f4eeb2f7a92bc99199fdd084af1dde5cd7df",
    ),
    "t1_predecessor_owner": (
        ROOT / "workspace/public/src/scripts/revalidation/s20plus_g986n_twrp_t1_f2.py",
        161_745,
        "756289617ee4837457a5d1c0357d6a8b78d10d86f4b6822d30a86ed24a174fd0",
    ),
    "h0_closure": (
        ROOT / "workspace/public/src/scripts/revalidation/s20plus_g986n_twrp_t2_profile_h0.py",
        12_847,
        "c02b78f2a1215a1fc2104a4634264609d2060d610bc628a068b318cb1cf55fb7",
    ),
    "recovery_digest": (
        ROOT / "workspace/public/src/scripts/revalidation/s20plus_g986n_recovery_digest_profile_h0.py",
        9_509,
        "9377e58d3717e0fa96826210815b09df20bf2ba62a70c85c896f5a6fdf68fded",
    ),
    "inventory": (
        ROOT / "workspace/public/src/scripts/revalidation/s20plus_g986n_d0_inventory.py",
        21_474,
        "3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81",
    ),
    "raw_capture": (
        ROOT / "workspace/public/src/scripts/revalidation/device_action_raw_capture_v1.py",
        25_006,
        "410e260129c0c50dca29b008dc7cf1051ee007816ab18bea76aeae62505ca0e4",
    ),
}

_BOUND_APIS = {
    "durable_json": b0.durable_json,
    "read_json": b0.read_json,
    "fsync_dir": b0.fsync_dir,
    "resident_health_once": b0.resident_health_once,
    "adb_inventory": b0.adb_inventory,
    "exact_adb_row": b0.exact_adb_row,
    "target_adb_rows": b0.target_adb_rows,
    "sanitized_inventory": b0.sanitized_inventory,
    "adb_devpath": b0.adb_devpath,
    "download_baseline": b0.download_baseline,
    "validate_download_baseline": b0.validate_download_baseline,
    "enumerate_download": b0.enumerate_download,
    "wait_download": b0.wait_download,
    "identify_download": b0.identify_download,
    "same_download_session": b0.same_download_session,
    "endpoint_stat": b0.endpoint_stat,
    "prepare_process_cage": b0.prepare_process_cage,
    "quiesce_process_cage": b0.quiesce_process_cage,
    "raw_acquire": b0.raw_capture.acquire_command,
    "raw_stdout": b0.raw_capture.read_stdout,
    "raw_stderr": b0.raw_capture.read_stderr,
    "raw_load": b0.raw_capture.load_handle,
    "raw_record": b0.validated_raw_capture_record,
    "root_parse": b0.parse_root_output,
    "host_validate": h0.validate_host_closure,
    "ap_validate": h0.validate_recovery_only_ap,
    "pin_regular_file": h0.pin_regular_file,
    "file_identity": h0._identity,
    "recovery_parse": h0.parse_recovery_observation,
    "digest_parse": recovery_digest.parse_root_result,
    "t1_source_closure": t1_predecessor.source_closure,
    "t1_resolve_run": t1_predecessor.resolve_run,
    "t1_read_prepared": t1_predecessor.read_prepared,
    "t1_validate_journal": t1_predecessor.validate_journal,
    "t1_validate_terminal": t1_predecessor._validate_terminal,
}


class T2F2Error(RuntimeError):
    """The exact recovery-only execution boundary was not satisfied."""


def utc_now() -> str:
    return b0.utc_now()


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise T2F2Error("value is not canonical JSON") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise T2F2Error(f"{label} schema differs")
    return value


def _text(value: Any, label: str, maximum: int = 4096) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value.encode("utf-8")) > maximum
        or "\x00" in value
        or "\r" in value
        or "\n" in value
    ):
        raise T2F2Error(f"{label} is not bounded text")
    return value


def _hex64(value: Any, label: str) -> str:
    text = _text(value, label, 64)
    if HEX64_RE.fullmatch(text) is None:
        raise T2F2Error(f"{label} is not SHA-256")
    return text


def _integer(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise T2F2Error(f"{label} is not an integer")
    return value


def _validate_endpoint(value: Any, label: str) -> dict[str, Any]:
    item = _exact(
        value,
        {"device", "endpoint_identity", "endpoint_sha256", "topology_sha256", "usb"},
        label,
    )
    device = _text(item["device"], f"{label}.device", 64)
    identity = item["endpoint_identity"]
    if (
        h0.USBFS_RE.fullmatch(device) is None
        or item["endpoint_sha256"] != hashlib.sha256(device.encode()).hexdigest()
        or not isinstance(identity, list)
        or len(identity) != 4
        or any(type(part) is not int or part < 0 for part in identity)
        or item["topology_sha256"] not in b0.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256
        or item["usb"] != {**b0.DOWNLOAD_USB, "serial_absent": True}
    ):
        raise T2F2Error(f"{label} identity differs")
    return item


def _validate_capture_receipt(
    value: Any, run_dir: Path, label: str
) -> dict[str, Any]:
    item = _exact(value, {"path", "size", "sha256"}, label)
    path = Path(_text(item["path"], f"{label}.path"))
    if path.parent != run_dir or not path.name.endswith(".capture.json"):
        raise T2F2Error(f"{label} path escapes the run")
    size = _integer(item["size"], f"{label}.size", 1)
    sha256 = _hex64(item["sha256"], f"{label}.sha256")
    _file_receipt(path, size, sha256, label)
    handle = b0.raw_capture.load_handle(path)
    b0.validated_raw_capture_record(handle, label)
    return item


def _require_capture_name(receipt: dict[str, Any], pattern: str, label: str) -> None:
    if re.fullmatch(pattern, Path(receipt["path"]).name) is None:
        raise T2F2Error(f"{label} capture name differs")


def _validate_health(value: Any, run_dir: Path, label: str) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "target", "serial_sha256", "topology_sha256", "boot_id_sha256",
            "public_health", "root_health", "inventory_sha256",
            "root_health_capture", "recovery_digest",
        },
        label,
    )
    if item["target"] != h0.EXPECTED_TARGET:
        raise T2F2Error(f"{label} target differs")
    _hex64(item["serial_sha256"], f"{label}.serial")
    _hex64(item["boot_id_sha256"], f"{label}.boot")
    if item["topology_sha256"] != b0.EXPECTED_ANDROID_TOPOLOGY_SHA256:
        raise T2F2Error(f"{label} topology differs")
    expected_public = {
        "model": h0.EXPECTED_TARGET["model"],
        "device": h0.EXPECTED_TARGET["device"],
        "product_name": h0.EXPECTED_TARGET["product"],
        "incremental": h0.EXPECTED_TARGET["incremental"],
        "boot_completed": "1",
        "bootanim": "stopped",
        "selinux": "Enforcing",
    }
    if item["public_health"] != expected_public or item["root_health"] != b0.EXPECTED_ROOT_OUTPUT:
        raise T2F2Error(f"{label} Android/root health differs")
    _hex64(item["inventory_sha256"], f"{label}.inventory")
    root_capture = _validate_capture_receipt(
        item["root_health_capture"], run_dir, f"{label}.root_capture"
    )
    _require_capture_name(
        root_capture,
        r"(?:prepare|execute-pre-download|pre-candidate-abort|final)-health-"
        r"(?:before|after)(?:-resume-[0-9]{4})?\.capture\.json",
        label,
    )
    root_handle = b0.raw_capture.load_handle(Path(root_capture["path"]))
    root_values = b0.parse_root_output(
        (
            root_handle.returncode,
            b0.raw_capture.read_stdout(root_handle, maximum=4096),
            b0.raw_capture.read_stderr(root_handle, maximum=4096),
        )
    )
    if (
        hashlib.sha256(root_values["boot_id"].encode()).hexdigest()
        != item["boot_id_sha256"]
        or {key: value for key, value in root_values.items() if key != "boot_id"}
        != item["root_health"]
    ):
        raise T2F2Error(f"{label} root capture differs")
    recovery = _exact(item["recovery_digest"], {"size", "sha256", "capture"}, f"{label}.recovery")
    if (
        recovery["size"] != h0.ROLLBACK_RECOVERY_SIZE
        or recovery["sha256"] != h0.ROLLBACK_RECOVERY_SHA256
    ):
        raise T2F2Error(f"{label} recovery is not exact stock")
    recovery_capture = _validate_capture_receipt(
        recovery["capture"], run_dir, f"{label}.recovery.capture"
    )
    _require_capture_name(
        recovery_capture,
        r"(?:prepare|execute-pre-download|pre-candidate-abort|final)-"
        r"recovery-digest-0001\.capture\.json",
        label,
    )
    recovery_handle = b0.raw_capture.load_handle(Path(recovery_capture["path"]))
    parsed_recovery = recovery_digest.parse_root_result(
        (
            recovery_handle.returncode,
            b0.raw_capture.read_stdout(
                recovery_handle, maximum=recovery_digest.MAX_ROOT_STDOUT_BYTES
            ),
            b0.raw_capture.read_stderr(
                recovery_handle, maximum=recovery_digest.MAX_ROOT_STDERR_BYTES
            ),
        )
    )
    if (
        int(parsed_recovery["recovery_size"]) != recovery["size"]
        or parsed_recovery["recovery_sha256"] != recovery["sha256"]
    ):
        raise T2F2Error(f"{label} recovery capture differs")
    match = re.fullmatch(
        r"(prepare|execute-pre-download|pre-candidate-abort|final)-"
        r"recovery-digest-[0-9]{4}\.capture\.json",
        Path(recovery_capture["path"]).name,
    )
    if match is None:
        raise T2F2Error(f"{label} recovery capture phase differs")
    phase = match.group(1)
    intent = _exact(
        b0.read_json(
            run_dir / f"{phase}-recovery-read-intent.json",
            f"{phase} recovery read intent",
        ),
        {
            "schema", "version", "phase", "target", "serial_sha256",
            "topology_sha256", "boot_id_sha256", "expected_size",
            "expected_sha256", "attempt", "no_replay", "at",
        },
        f"{phase} recovery read intent",
    )
    if (
        intent["schema"]
        != "s20plus_g986n_twrp_t2_recovery_read_intent_v1"
        or intent["version"] != VERSION
        or intent["phase"] != phase
        or intent["target"] != h0.EXPECTED_TARGET
        or intent["serial_sha256"] != item["serial_sha256"]
        or intent["topology_sha256"] != item["topology_sha256"]
        or intent["boot_id_sha256"] != item["boot_id_sha256"]
        or intent["expected_size"] != h0.ROLLBACK_RECOVERY_SIZE
        or type(intent["expected_size"]) is not int
        or intent["expected_sha256"] != h0.ROLLBACK_RECOVERY_SHA256
        or type(intent["attempt"]) is not int
        or intent["attempt"] != 1
        or intent["no_replay"] is not True
    ):
        raise T2F2Error(f"{label} recovery read intent differs")
    _text(intent["at"], f"{phase} recovery read intent time", 128)
    return item


def _validate_baseline(value: Any, label: str) -> dict[str, Any]:
    try:
        return b0.validate_download_baseline(value, label)
    except Exception as exc:
        raise T2F2Error(f"{label} differs") from exc


def _validate_arrival(value: Any, prepared: dict[str, Any], label: str) -> dict[str, Any]:
    item = _exact(
        value,
        {"endpoint", "baseline_sha256", "arrival_listing_sha256", "at"},
        label,
    )
    _validate_endpoint(item["endpoint"], f"{label}.endpoint")
    _hex64(item["baseline_sha256"], f"{label}.baseline")
    _hex64(item["arrival_listing_sha256"], f"{label}.listing")
    _text(item["at"], f"{label}.at", 128)
    baseline = prepared["binding"]["initial_download_baseline"]
    # The arrival is emitted by b0.wait_download(), whose canonical receipt
    # includes the durable JSON trailing newline.  Keep its provenance in the
    # producer's digest domain instead of the T2 binding digest domain.
    if item["baseline_sha256"] != b0.digest(baseline):
        raise T2F2Error(f"{label} is not descended from the prepared baseline")
    return item


def _file_receipt(path: Path, size: int, sha256: str, label: str) -> dict[str, Any]:
    try:
        metadata = path.lstat()
        payload = path.read_bytes()
    except OSError as exc:
        raise T2F2Error(f"{label} is unavailable") from exc
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or path.resolve(strict=True) != path.absolute()
        or len(payload) != size
        or hashlib.sha256(payload).hexdigest() != sha256
    ):
        raise T2F2Error(f"{label} identity differs")
    return {"path": str(path), "size": size, "sha256": sha256}


def normalized_self_sha256() -> str:
    source = SCRIPT.read_bytes()
    source, active_count = re.subn(
        rb"^T2_F2_ACTIVE = (?:False|True)$",
        b"T2_F2_ACTIVE = <REVIEWED_ACTIVATION_BOOLEAN>",
        source,
        flags=re.MULTILINE,
    )
    source, hash_count = re.subn(
        rb'^EXPECTED_REVIEWED_NORMALIZED_SHA256 = "[0-9a-f]{64}"$',
        b'EXPECTED_REVIEWED_NORMALIZED_SHA256 = "' + b"0" * 64 + b'"',
        source,
        flags=re.MULTILINE,
    )
    if active_count != 1 or hash_count != 1:
        raise T2F2Error("runner normalization grammar changed")
    return hashlib.sha256(source).hexdigest()


def self_receipt(*, enforce_reviewed: bool = True) -> dict[str, Any]:
    metadata = SCRIPT.lstat()
    normalized = normalized_self_sha256()
    if (
        SCRIPT.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or SCRIPT.resolve(strict=True) != SCRIPT.absolute()
    ):
        raise T2F2Error("runner source is indirect")
    if enforce_reviewed and normalized != EXPECTED_REVIEWED_NORMALIZED_SHA256:
        raise T2F2Error("runner source is not independently reviewed")
    return {
        "path": str(SCRIPT),
        "size": metadata.st_size,
        "sha256": hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
        "normalized_sha256": normalized,
    }


def source_closure(*, enforce_self: bool = True) -> dict[str, Any]:
    current = {
        "durable_json": b0.durable_json,
        "read_json": b0.read_json,
        "fsync_dir": b0.fsync_dir,
        "resident_health_once": b0.resident_health_once,
        "adb_inventory": b0.adb_inventory,
        "exact_adb_row": b0.exact_adb_row,
        "target_adb_rows": b0.target_adb_rows,
        "sanitized_inventory": b0.sanitized_inventory,
        "adb_devpath": b0.adb_devpath,
        "download_baseline": b0.download_baseline,
        "validate_download_baseline": b0.validate_download_baseline,
        "enumerate_download": b0.enumerate_download,
        "wait_download": b0.wait_download,
        "identify_download": b0.identify_download,
        "same_download_session": b0.same_download_session,
        "endpoint_stat": b0.endpoint_stat,
        "prepare_process_cage": b0.prepare_process_cage,
        "quiesce_process_cage": b0.quiesce_process_cage,
        "raw_acquire": b0.raw_capture.acquire_command,
        "raw_stdout": b0.raw_capture.read_stdout,
        "raw_stderr": b0.raw_capture.read_stderr,
        "raw_load": b0.raw_capture.load_handle,
        "raw_record": b0.validated_raw_capture_record,
        "root_parse": b0.parse_root_output,
        "host_validate": h0.validate_host_closure,
        "ap_validate": h0.validate_recovery_only_ap,
        "pin_regular_file": h0.pin_regular_file,
        "file_identity": h0._identity,
        "recovery_parse": h0.parse_recovery_observation,
        "digest_parse": recovery_digest.parse_root_result,
        "t1_source_closure": t1_predecessor.source_closure,
        "t1_resolve_run": t1_predecessor.resolve_run,
        "t1_read_prepared": t1_predecessor.read_prepared,
        "t1_validate_journal": t1_predecessor.validate_journal,
        "t1_validate_terminal": t1_predecessor._validate_terminal,
    }
    if any(current[name] is not expected for name, expected in _BOUND_APIS.items()):
        raise T2F2Error("an imported execution API was rebound")
    receipts = {
        name: _file_receipt(path, size, sha256, name)
        for name, (path, size, sha256) in DEPENDENCIES.items()
    }
    receipts["runner"] = self_receipt(enforce_reviewed=enforce_self)
    receipts["adb"] = _file_receipt(
        b0.ADB, b0.ADB_SIZE, b0.ADB_SHA256, "ADB"
    )
    receipts["odin"] = _file_receipt(
        h0.ODIN, h0.ODIN_SIZE, h0.ODIN_SHA256, "Odin4"
    )
    receipts["cage_shell"] = _file_receipt(
        b0.DASH, b0.DASH_SIZE, b0.DASH_SHA256, "process-cage shell"
    )
    receipts["cage_watchdog"] = _file_receipt(
        b0.CAGE_SLEEP,
        b0.CAGE_SLEEP_SIZE,
        b0.CAGE_SLEEP_SHA256,
        "process-cage watchdog",
    )
    return receipts


def _parse_t1_predecessor_observation(payload: bytes) -> dict[str, str]:
    try:
        text = payload.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise T2F2Error("T1 predecessor observer output is not UTF-8") from exc
    if "\r" in text or "\x00" in text or not text.endswith("\n"):
        raise T2F2Error("T1 predecessor observer framing differs")
    lines = text.splitlines()
    if len(lines) != len(h0.RECOVERY_OUTPUT_KEYS):
        raise T2F2Error("T1 predecessor observer field count differs")
    values: dict[str, str] = {}
    for expected, line in zip(h0.RECOVERY_OUTPUT_KEYS, lines, strict=True):
        key, separator, value = line.partition("=")
        if separator != "=" or key != expected or key in values or not value:
            raise T2F2Error("T1 predecessor observer grammar differs")
        values[key] = value
    expected_fixed = {
        "uid": "0",
        "twrp_version": t1_predecessor.h0.TWRP_VERSION,
        "incremental": t1_predecessor.h0.TWRP_INCREMENTAL,
        "ro_secure": "0",
        "ro_debuggable": "1",
        "usb_config": "mtp,adb",
        "adbd_state": "running",
        "marker_sha256": t1_predecessor.h0.MARKER_SHA256,
    }
    if any(values.get(key) != expected for key, expected in expected_fixed.items()):
        raise T2F2Error("T1 predecessor observer fixed values differ")
    if h0.BOOT_ID_RE.fullmatch(values["boot_id"]) is None:
        raise T2F2Error("T1 predecessor recovery boot ID differs")
    return values


def validate_t1_predecessor(
    *, expected_serial_sha256: str | None = None
) -> dict[str, Any]:
    """Re-derive the fixed T1 rollback and discriminating observer evidence."""

    t1_predecessor.source_closure()
    terminal_receipt = _file_receipt(
        T1_PREDECESSOR_TERMINAL,
        T1_PREDECESSOR_TERMINAL_SIZE,
        T1_PREDECESSOR_TERMINAL_SHA256,
        "T1 predecessor terminal",
    )
    observation_receipt = _file_receipt(
        T1_PREDECESSOR_OBSERVATION,
        T1_PREDECESSOR_OBSERVATION_SIZE,
        T1_PREDECESSOR_OBSERVATION_SHA256,
        "T1 predecessor observation",
    )
    capture_receipt = _file_receipt(
        T1_PREDECESSOR_OBSERVER_CAPTURE,
        T1_PREDECESSOR_OBSERVER_CAPTURE_SIZE,
        T1_PREDECESSOR_OBSERVER_CAPTURE_SHA256,
        "T1 predecessor observer capture",
    )
    stdout_receipt = _file_receipt(
        T1_PREDECESSOR_OBSERVER_STDOUT,
        T1_PREDECESSOR_OBSERVER_STDOUT_SIZE,
        T1_PREDECESSOR_OBSERVER_STDOUT_SHA256,
        "T1 predecessor observer stdout",
    )
    run_dir = t1_predecessor.resolve_run(T1_PREDECESSOR_RUN_ID)
    prepared = t1_predecessor.read_prepared(
        run_dir,
        require_unexpired=False,
        require_current_guard=False,
    )
    actual = t1_predecessor.validate_journal(run_dir, prepared)
    terminal = t1_predecessor._validate_terminal(run_dir, prepared, actual)
    final_health = terminal.get("final_health")
    observation = b0.read_json(
        T1_PREDECESSOR_OBSERVATION, "T1 predecessor observation"
    )
    if (
        not isinstance(observation, dict)
        or set(observation)
        != {"schema", "version", "binding_sha256", "claim_verdict", "reason", "at"}
        or observation.get("schema") != "s20plus_g986n_twrp_t1_observation_v1"
        or observation.get("version") != t1_predecessor.VERSION
        or observation.get("binding_sha256") != prepared.get("binding_sha256")
        or observation.get("claim_verdict") != "NO_PROOF"
        or observation.get("reason")
        != "TWRPT1ProfileError:cb0d94ae158cdbc57ed857d2127ebf62bce6ebf2231af6f7d8a59c40f09d4e19"
    ):
        raise T2F2Error("T1 predecessor observation differs")
    _text(observation["at"], "T1 predecessor observation time", 128)
    handle = b0.raw_capture.load_handle(T1_PREDECESSOR_OBSERVER_CAPTURE)
    b0.validated_raw_capture_record(handle, "T1 predecessor observer capture")
    if (
        handle.stdout_path != T1_PREDECESSOR_OBSERVER_STDOUT
        or handle.returncode != 0
        or handle.stderr.get("size") != 0
    ):
        raise T2F2Error("T1 predecessor observer capture envelope differs")
    stdout = b0.raw_capture.read_stdout(handle, maximum=h0.MAX_RECOVERY_OBSERVER_BYTES)
    stderr = b0.raw_capture.read_stderr(handle, maximum=h0.MAX_RECOVERY_OBSERVER_BYTES)
    if stderr or hashlib.sha256(stdout).hexdigest() != T1_PREDECESSOR_OBSERVER_STDOUT_SHA256:
        raise T2F2Error("T1 predecessor observer streams differ")
    values = _parse_t1_predecessor_observation(stdout)
    recovery_boot_sha256 = hashlib.sha256(values["boot_id"].encode()).hexdigest()
    if (
        terminal.get("verdict")
        != "NO_PROOF_T1_RETURNED_STOCK_RECOVERY_HEALTHY"
        or terminal.get("candidate_claim") != "NO_PROOF"
        or terminal.get("candidate_transfer_proved") is not True
        or terminal.get("rollback_transfer_proved") is not True
        or terminal.get("final_stock_recovery_proved") is not True
        or terminal.get("candidate_replay_permitted") is not False
        or terminal.get("rollback_replay_permitted") is not False
        or terminal.get("candidate_attempts") != 1
        or type(terminal.get("candidate_attempts")) is not int
        or terminal.get("rollback_attempts") != 1
        or type(terminal.get("rollback_attempts")) is not int
        or terminal.get("partition_transfer_attempts") != 2
        or type(terminal.get("partition_transfer_attempts")) is not int
        or terminal.get("all_other_partition_transfers") != 0
        or type(terminal.get("all_other_partition_transfers")) is not int
        or terminal.get("s22plus_commands") != 0
        or terminal.get("a90_commands") != 0
        or terminal.get("other_target_commands") != 0
        or not isinstance(final_health, dict)
        or final_health.get("target") != h0.EXPECTED_TARGET
        or final_health.get("recovery_digest")
        != {
            "size": h0.ROLLBACK_RECOVERY_SIZE,
            "sha256": h0.ROLLBACK_RECOVERY_SHA256,
            "capture": final_health.get("recovery_digest", {}).get("capture"),
        }
        or recovery_boot_sha256 == prepared["binding"]["preflight"]["boot_id_sha256"]
        or recovery_boot_sha256 == final_health.get("boot_id_sha256")
    ):
        raise T2F2Error("T1 predecessor no longer proves observed TWRP and stock return")
    predecessor_serial = final_health.get("serial_sha256")
    _hex64(predecessor_serial, "T1 predecessor serial")
    if expected_serial_sha256 is not None:
        _hex64(expected_serial_sha256, "current T2 serial")
        if predecessor_serial != expected_serial_sha256:
            raise T2F2Error("current T2 serial is not the T1-qualified device")
    return {
        "terminal": terminal_receipt,
        "observation": observation_receipt,
        "observer_capture": capture_receipt,
        "observer_stdout": stdout_receipt,
        "verdict": terminal["verdict"],
        "candidate_transfer_proved": True,
        "rollback_transfer_proved": True,
        "final_stock_recovery_proved": True,
        "final_stock_recovery_sha256": h0.ROLLBACK_RECOVERY_SHA256,
        "observed_twrp_version": values["twrp_version"],
        "observed_usb_config": values["usb_config"],
        "all_other_partition_transfers": 0,
    }


def validate_host_closure(
    *, enforce_self: bool = True, expected_serial_sha256: str | None = None
) -> dict[str, Any]:
    sources = source_closure(enforce_self=enforce_self)
    host = h0.validate_host_closure()
    if (
        host.get("verdict") != h0.HOST_PASS_VERDICT
        or host.get("live_authorized") is not False
        or host.get("target") != h0.EXPECTED_TARGET
    ):
        raise T2F2Error("T2 H0 artifact closure differs")
    predecessor = validate_t1_predecessor(
        expected_serial_sha256=expected_serial_sha256
    )
    return {"sources": sources, "host": host, "t1_predecessor": predecessor}


def require_active() -> None:
    if not T2_F2_ACTIVE:
        raise T2F2Error("S20+ TWRP T2 F2 is not active")
    source_closure()


def _ensure_private_roots() -> None:
    parent = RUN_ROOT.parent
    if parent.resolve(strict=True) != parent.absolute() or parent.is_symlink():
        raise T2F2Error("private run parent is indirect")
    if RUN_ROOT.exists():
        if RUN_ROOT.is_symlink() or RUN_ROOT.resolve(strict=True) != RUN_ROOT.absolute():
            raise T2F2Error("T2 run root is indirect")
    else:
        RUN_ROOT.mkdir(mode=0o700)
        b0.fsync_dir(parent)
    if CLAIM_ROOT.exists():
        if CLAIM_ROOT.is_symlink() or CLAIM_ROOT.resolve(strict=True) != CLAIM_ROOT.absolute():
            raise T2F2Error("T2 claim root is indirect")
    else:
        CLAIM_ROOT.mkdir(mode=0o700)
        b0.fsync_dir(RUN_ROOT)


def _run_id(path: Path) -> str:
    if path.parent != RUN_ROOT or RUN_ID_RE.fullmatch(path.name) is None:
        raise T2F2Error("run path is outside the closed namespace")
    return path.name


def allocate_run_dir() -> Path:
    _ensure_private_roots()
    for _ in range(32):
        path = RUN_ROOT / f"run-{time.time_ns()}"
        try:
            path.mkdir(mode=0o700)
        except FileExistsError:
            continue
        b0.fsync_dir(RUN_ROOT)
        return path
    raise T2F2Error("unable to allocate a unique T2 run")


def resolve_run(run_id: str) -> Path:
    _ensure_private_roots()
    if RUN_ID_RE.fullmatch(run_id) is None:
        raise T2F2Error("run ID grammar differs")
    path = RUN_ROOT / run_id
    metadata = path.lstat()
    if (
        path.is_symlink()
        or not stat.S_ISDIR(metadata.st_mode)
        or path.resolve(strict=True) != path.absolute()
    ):
        raise T2F2Error("run directory is indirect")
    validate_namespace(path)
    return path


def validate_namespace(run_dir: Path) -> set[str]:
    before = run_dir.stat(follow_symlinks=False)
    actual: set[str] = set()
    with os.scandir(run_dir) as entries:
        for entry in entries:
            metadata = entry.stat(follow_symlinks=False)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
                or entry.is_symlink()
            ):
                raise T2F2Error("T2 journal contains an indirect node")
            actual.add(entry.name)
    unknown = {
        name
        for name in actual
        if name not in RUN_NODE_NAMES and RAW_NODE_RE.fullmatch(name) is None
    }
    if unknown:
        raise T2F2Error("T2 journal contains an unknown node")
    one_shot_prefixes = (
        "prepare-recovery-digest", "execute-pre-download-recovery-digest",
        "pre-candidate-abort-recovery-digest", "final-recovery-digest",
        "candidate-download", "candidate-transfer",
        "candidate-recovery-observer", "rollback-download", "rollback-transfer",
    )
    for prefix in one_shot_prefixes:
        ordinals = {
            match.group(1)
            for name in actual
            if (
                match := re.fullmatch(
                    rf"{re.escape(prefix)}-([0-9]{{4}})\."
                    r"(?:stdout|stderr|capture\.json)",
                    name,
                )
            )
        }
        if len(ordinals) > 1:
            raise T2F2Error(f"T2 journal reuses one-shot raw prefix {prefix}")
    after = run_dir.stat(follow_symlinks=False)
    if (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_ctime_ns,
    ):
        raise T2F2Error("T2 run directory changed during validation")
    return actual


def _guard_value(run_dir: Path) -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_twrp_t2_guard_v1",
        "version": VERSION,
        "run_id": _run_id(run_dir),
        "candidate_sha256": h0.CANDIDATE_AP_SHA256,
        "rollback_sha256": h0.ROLLBACK_AP_SHA256,
        "owner": str(SCRIPT),
    }


def acquire_guard(run_dir: Path) -> None:
    if os.path.lexists(SHARED_GUARD):
        raise T2F2Error("shared S20+ action guard is already held")
    b0.durable_json(SHARED_GUARD, _guard_value(run_dir))


def require_guard(run_dir: Path) -> None:
    if b0.read_json(SHARED_GUARD, "shared S20+ guard") != _guard_value(run_dir):
        raise T2F2Error("shared S20+ action guard differs")


def release_guard(run_dir: Path) -> None:
    require_guard(run_dir)
    SHARED_GUARD.unlink()
    b0.fsync_dir(SHARED_GUARD.parent)


def candidate_claim_path() -> Path:
    return CLAIM_ROOT / f"{h0.CANDIDATE_AP_SHA256}.json"


def validate_candidate_claim(
    value: Any, run_dir: Path, prepared: dict[str, Any]
) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "schema", "version", "run_id", "binding_sha256",
            "candidate_sha256", "candidate_replay", "at",
        },
        "global candidate claim",
    )
    if (
        item["schema"] != "s20plus_g986n_twrp_t2_global_claim_v1"
        or item["version"] != VERSION
        or item["run_id"] != _run_id(run_dir)
        or item["binding_sha256"] != prepared["binding_sha256"]
        or item["candidate_sha256"] != h0.CANDIDATE_AP_SHA256
        or item["candidate_replay"] is not False
    ):
        raise T2F2Error("global candidate claim differs")
    _text(item["at"], "global candidate claim time", 128)
    return item


def require_fresh_candidate_unclaimed() -> None:
    path = candidate_claim_path()
    if os.path.lexists(path):
        try:
            b0.read_json(path, "global candidate claim")
        except Exception as exc:
            raise T2F2Error("global candidate claim is malformed") from exc
        raise T2F2Error("this exact T2 candidate is permanently consumed")


def _next_capture_name(run_dir: Path, prefix: str) -> str:
    for ordinal in range(1, 10_000):
        name = f"{prefix}-{ordinal:04d}"
        if not any(
            os.path.lexists(run_dir / f"{name}{suffix}")
            for suffix in (".capture.json", ".stdout", ".stderr")
        ):
            return name
    raise T2F2Error("raw-capture ordinal space is exhausted")


def _capture(
    run_dir: Path,
    prefix: str,
    argv: list[str],
    *,
    timeout: float,
    maximum: int,
    env: dict[str, str] | None = None,
    start_new_session: bool = False,
) -> tuple[Any, bytes, bytes]:
    name = _next_capture_name(run_dir, prefix)
    handle = b0.raw_capture.acquire_command(
        argv,
        run_dir,
        name,
        timeout=timeout,
        stdout_maximum=maximum,
        stderr_maximum=maximum,
        env=env,
        start_new_session=start_new_session,
        stdout_name=f"{name}.stdout",
        stderr_name=f"{name}.stderr",
    )
    stdout = b0.raw_capture.read_stdout(handle, maximum=maximum)
    stderr = b0.raw_capture.read_stderr(handle, maximum=maximum)
    return handle, stdout, stderr


def _capture_receipt(handle: Any) -> dict[str, Any]:
    path = handle.receipt_path
    payload = path.read_bytes()
    return {
        "path": str(path),
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def android_stock_recovery_health(
    run_dir: Path,
    prefix: str,
    expected_serial_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    if prefix not in {
        "prepare", "execute-pre-download", "pre-candidate-abort", "final"
    }:
        raise T2F2Error("unknown fixed recovery-health phase")
    before, serial = b0.resident_health_once(
        run_dir, f"{prefix}-health-before", expected_serial_sha256
    )
    read_intent_path = run_dir / f"{prefix}-recovery-read-intent.json"
    read_intent = {
        "schema": "s20plus_g986n_twrp_t2_recovery_read_intent_v1",
        "version": VERSION,
        "phase": prefix,
        "target": dict(h0.EXPECTED_TARGET),
        "serial_sha256": before["serial_sha256"],
        "topology_sha256": before["topology_sha256"],
        "boot_id_sha256": before["boot_id_sha256"],
        "expected_size": h0.ROLLBACK_RECOVERY_SIZE,
        "expected_sha256": h0.ROLLBACK_RECOVERY_SHA256,
        "attempt": 1,
        "no_replay": True,
        "at": utc_now(),
    }
    captures = sorted(
        run_dir.glob(f"{prefix}-recovery-digest-[0-9][0-9][0-9][0-9].capture.json")
    )
    if os.path.lexists(read_intent_path):
        stored = b0.read_json(read_intent_path, f"{prefix} recovery read intent")
        if (
            {key: stored.get(key) for key in read_intent if key != "at"}
            != {key: read_intent[key] for key in read_intent if key != "at"}
            or set(stored) != set(read_intent)
            or not isinstance(stored.get("at"), str)
            or len(captures) != 1
        ):
            raise T2F2Error(f"{prefix} recovery read was consumed without a receipt")
        handle = b0.raw_capture.load_handle(captures[0])
        b0.validated_raw_capture_record(handle, f"{prefix} recovery read capture")
        stdout = b0.raw_capture.read_stdout(
            handle, maximum=recovery_digest.MAX_ROOT_STDOUT_BYTES
        )
        stderr = b0.raw_capture.read_stderr(
            handle, maximum=recovery_digest.MAX_ROOT_STDERR_BYTES
        )
    else:
        if captures or any(
            run_dir.glob(f"{prefix}-recovery-digest-[0-9][0-9][0-9][0-9].stdout")
        ) or any(
            run_dir.glob(f"{prefix}-recovery-digest-[0-9][0-9][0-9][0-9].stderr")
        ):
            raise T2F2Error(f"{prefix} recovery evidence exists without intent")
        b0.durable_json(read_intent_path, read_intent)
        handle, stdout, stderr = _capture(
            run_dir,
            f"{prefix}-recovery-digest",
            [
                str(b0.ADB),
                "-s",
                serial,
                "shell",
                "su",
                "-c",
                recovery_digest.ROOT_SHELL_ARGUMENT,
            ],
            timeout=recovery_digest.PROPOSED_ROOT_TIMEOUT_SECONDS,
            maximum=recovery_digest.MAX_ROOT_STDOUT_BYTES,
        )
    parsed = recovery_digest.parse_root_result((handle.returncode, stdout, stderr))
    after, final_serial = b0.resident_health_once(
        run_dir, f"{prefix}-health-after", before["serial_sha256"]
    )
    if (
        final_serial != serial
        or before["serial_sha256"] != after["serial_sha256"]
        or before["topology_sha256"] != after["topology_sha256"]
        or before["boot_id_sha256"] != after["boot_id_sha256"]
    ):
        raise T2F2Error("Android identity changed during recovery digest read")
    return {
        "target": dict(h0.EXPECTED_TARGET),
        "serial_sha256": before["serial_sha256"],
        "topology_sha256": before["topology_sha256"],
        "boot_id_sha256": before["boot_id_sha256"],
        "public_health": before["public_health"],
        "root_health": before["root_health"],
        "inventory_sha256": before["inventory_sha256"],
        "root_health_capture": before["root_capture"],
        "recovery_digest": {
            "size": int(parsed["recovery_size"]),
            "sha256": parsed["recovery_sha256"],
            "capture": _capture_receipt(handle),
        },
    }, serial


def _adb_reboot_download(
    run_dir: Path,
    serial: str,
    prefix: str,
    *,
    phase: str,
    binding_sha256: str,
) -> dict[str, Any]:
    handle, stdout, stderr = _capture(
        run_dir,
        prefix,
        [str(b0.ADB), "-s", serial, "reboot", "download"],
        timeout=20,
        maximum=64 * 1024,
    )
    dispatched = (
        type(handle.returncode) is int
        and handle.returncode == 0
        and not stdout
        and not stderr
        and handle.producer_error_type is None
        and not handle.timed_out
        and not handle.output_exceeded
    )
    return {
        "schema": "s20plus_g986n_twrp_t2_reboot_result_v1",
        "version": VERSION,
        "phase": phase,
        "binding_sha256": binding_sha256,
        "outcome": "dispatched" if dispatched else "uncertain",
        "returncode": handle.returncode,
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "raw_capture": _capture_receipt(handle),
        "failure_class": None,
        "replay_permitted": False,
        "at": utc_now(),
    }


def _prepared_binding(
    run_dir: Path,
    health: dict[str, Any],
    baseline: dict[str, Any],
    closure: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_twrp_t2_binding_v1",
        "version": VERSION,
        "run_id": _run_id(run_dir),
        "target": dict(h0.EXPECTED_TARGET),
        "preflight": health,
        "initial_download_baseline": baseline,
        "candidate": {
            "path": str(h0.CANDIDATE_AP),
            "size": h0.CANDIDATE_AP_SIZE,
            "sha256": h0.CANDIDATE_AP_SHA256,
            "member": h0.AP_MEMBER_NAME,
        },
        "rollback": {
            "path": str(h0.ROLLBACK_AP),
            "size": h0.ROLLBACK_AP_SIZE,
            "sha256": h0.ROLLBACK_AP_SHA256,
            "member": h0.AP_MEMBER_NAME,
        },
        "closure_sha256": digest(closure),
        "candidate_attempt_maximum": 1,
        "rollback_attempt_maximum": 1,
        "candidate_replay": False,
        "rollback_replay": False,
        "recovery_partition_only": True,
        "all_other_partition_transfers": 0,
        "expires_unix": int(time.time()) + APPROVAL_LIFETIME_SECONDS,
    }


def prepare() -> dict[str, Any]:
    require_active()
    closure = validate_host_closure()
    _ensure_private_roots()
    require_fresh_candidate_unclaimed()
    run_dir = allocate_run_dir()
    acquire_guard(run_dir)
    b0.durable_json(
        run_dir / "allocation.json",
        {
            "schema": "s20plus_g986n_twrp_t2_allocation_v1",
            "version": VERSION,
            "run_id": _run_id(run_dir),
            "guard": _guard_value(run_dir),
            "at": utc_now(),
        },
    )
    try:
        require_fresh_candidate_unclaimed()
        health, serial = android_stock_recovery_health(run_dir, "prepare")
        if validate_t1_predecessor(
            expected_serial_sha256=health["serial_sha256"]
        ) != closure["t1_predecessor"]:
            raise T2F2Error("T1 qualification changed during T2 preparation")
        baseline = b0.download_baseline()
        b0.durable_json(run_dir / "candidate-download-baseline.json", baseline)
        binding = _prepared_binding(run_dir, health, baseline, closure)
        binding_sha256 = digest(binding)
        prepared = {
            "schema": "s20plus_g986n_twrp_t2_prepared_v1",
            "version": VERSION,
            "binding": binding,
            "binding_sha256": binding_sha256,
            "approval_token": APPROVAL_PREFIX + binding_sha256,
            "at": utc_now(),
        }
        b0.durable_json(run_dir / "prepared.json", prepared)
        checked = read_prepared(run_dir, require_unexpired=True)
        validate_journal(run_dir, checked)
        return {
            "verdict": "PREPARED_S20PLUS_G986N_TWRP_T2_AWAITING_APPROVAL",
            "run_id": _run_id(run_dir),
            "approval_token": prepared["approval_token"],
            "expires_unix": binding["expires_unix"],
        }
    except Exception as exc:
        b0.durable_json(
            run_dir / "failure.json",
            {
                "schema": "s20plus_g986n_twrp_t2_failure_v1",
                "version": VERSION,
                "phase": "prepare-read-only",
                "failure_class": type(exc).__name__,
                "failure_sha256": hashlib.sha256(str(exc).encode()).hexdigest(),
                "device_effects": 0,
                "at": utc_now(),
            },
        )
        release_guard(run_dir)
        raise


def read_prepared(
    run_dir: Path,
    *,
    require_unexpired: bool,
    require_current_guard: bool = True,
) -> dict[str, Any]:
    prepared = b0.read_json(run_dir / "prepared.json", "T2 prepared binding")
    allocation = b0.read_json(run_dir / "allocation.json", "T2 allocation")
    if (
        set(prepared) != {
            "schema", "version", "binding", "binding_sha256", "approval_token", "at"
        }
        or prepared.get("schema") != "s20plus_g986n_twrp_t2_prepared_v1"
        or prepared.get("version") != VERSION
        or not isinstance(prepared.get("binding"), dict)
        or prepared.get("binding_sha256") != digest(prepared["binding"])
        or prepared.get("approval_token")
        != APPROVAL_PREFIX + prepared["binding_sha256"]
        or prepared["binding"].get("run_id") != _run_id(run_dir)
        or prepared["binding"].get("target") != h0.EXPECTED_TARGET
    ):
        raise T2F2Error("prepared T2 binding is malformed")
    binding = _exact(
        prepared["binding"],
        {
            "schema", "version", "run_id", "target", "preflight",
            "initial_download_baseline", "candidate", "rollback",
            "closure_sha256", "candidate_attempt_maximum",
            "rollback_attempt_maximum", "candidate_replay", "rollback_replay",
            "recovery_partition_only", "all_other_partition_transfers",
            "expires_unix",
        },
        "prepared T2 binding",
    )
    if (
        binding["schema"] != "s20plus_g986n_twrp_t2_binding_v1"
        or binding["version"] != VERSION
        or binding["run_id"] != _run_id(run_dir)
        or binding["target"] != h0.EXPECTED_TARGET
        or binding["candidate"]
        != {
            "path": str(h0.CANDIDATE_AP),
            "size": h0.CANDIDATE_AP_SIZE,
            "sha256": h0.CANDIDATE_AP_SHA256,
            "member": h0.AP_MEMBER_NAME,
        }
        or binding["rollback"]
        != {
            "path": str(h0.ROLLBACK_AP),
            "size": h0.ROLLBACK_AP_SIZE,
            "sha256": h0.ROLLBACK_AP_SHA256,
            "member": h0.AP_MEMBER_NAME,
        }
        or binding["candidate_attempt_maximum"] != 1
        or type(binding["candidate_attempt_maximum"]) is not int
        or binding["rollback_attempt_maximum"] != 1
        or type(binding["rollback_attempt_maximum"]) is not int
        or binding["candidate_replay"] is not False
        or binding["rollback_replay"] is not False
        or binding["recovery_partition_only"] is not True
        or binding["all_other_partition_transfers"] != 0
        or type(binding["all_other_partition_transfers"]) is not int
    ):
        raise T2F2Error("prepared T2 binding fields differ")
    _hex64(binding["closure_sha256"], "prepared closure SHA-256")
    _validate_health(binding["preflight"], run_dir, "prepared health")
    baseline = _validate_baseline(
        binding["initial_download_baseline"], "prepared Download baseline"
    )
    stored_baseline = b0.read_json(
        run_dir / "candidate-download-baseline.json", "stored Download baseline"
    )
    if stored_baseline != baseline:
        raise T2F2Error("stored Download baseline differs from preparation")
    expected_allocation = {
        "schema": "s20plus_g986n_twrp_t2_allocation_v1",
        "version": VERSION,
        "run_id": _run_id(run_dir),
        "guard": _guard_value(run_dir),
        "at": allocation.get("at"),
    }
    if allocation != expected_allocation:
        raise T2F2Error("T2 allocation differs")
    _text(allocation["at"], "allocation time", 128)
    expires = prepared["binding"].get("expires_unix")
    if type(expires) is not int or (require_unexpired and int(time.time()) > expires):
        raise T2F2Error("prepared T2 approval expired")
    if require_current_guard:
        require_guard(run_dir)
    return prepared


def _validate_cage_binding(
    value: Any, kind: str, binding_sha256: str
) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "schema", "version", "kind", "binding_sha256", "parent",
            "parent_identity", "cage", "host_boot_id_sha256",
            "cage_identity", "empty_before_backend", "at",
        },
        f"{kind} process cage",
    )
    parent = Path(_text(item["parent"], f"{kind} cage parent"))
    expected_cage = parent / f"s20plus-b0-{kind}-{binding_sha256[:20]}"
    if (
        item["schema"] != "s20plus_g986n_b0_process_cage_binding_v1"
        or item["version"] != b0.VERSION
        or item["kind"] != kind
        or item["binding_sha256"] != binding_sha256
        or not parent.is_absolute()
        or parent.parts[:4] != ("/", "sys", "fs", "cgroup")
        or ".." in parent.parts
        or item["cage"] != str(expected_cage)
        or not isinstance(item["parent_identity"], list)
        or len(item["parent_identity"]) != 5
        or any(type(part) is not int for part in item["parent_identity"])
        or not isinstance(item["cage_identity"], list)
        or len(item["cage_identity"]) != 5
        or any(type(part) is not int for part in item["cage_identity"])
        or item["empty_before_backend"] is not True
    ):
        raise T2F2Error(f"{kind} process cage differs")
    _hex64(item["host_boot_id_sha256"], f"{kind} cage host boot")
    _text(item["at"], f"{kind} cage time", 128)
    return item


def _validate_cage_quiescence(
    run_dir: Path, kind: str, binding_sha256: str, cage: dict[str, Any]
) -> dict[str, Any]:
    value = b0.read_json(
        run_dir / f"{kind}-cage-quiescent.json", f"{kind} cage quiescence"
    )
    item = _exact(
        value,
        {
            "schema", "version", "kind", "binding_sha256",
            "cage_binding_sha256", "kill_requested",
            "cage_absent_before_check", "empty_and_removed", "at",
        },
        f"{kind} cage quiescence",
    )
    if (
        item["schema"] != "s20plus_g986n_b0_process_cage_quiescent_v1"
        or item["version"] != b0.VERSION
        or item["kind"] != kind
        or item["binding_sha256"] != binding_sha256
        or item["cage_binding_sha256"] != b0.digest(cage)
        or type(item["kill_requested"]) is not bool
        or type(item["cage_absent_before_check"]) is not bool
        or item["empty_and_removed"] is not True
    ):
        raise T2F2Error(f"{kind} cage quiescence differs")
    _text(item["at"], f"{kind} cage quiescence time", 128)
    return item


def _validate_approval(value: Any, prepared: dict[str, Any]) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "schema", "version", "binding_sha256", "approval_sha256",
            "consumed", "at",
        },
        "T2 approval",
    )
    if (
        item["schema"] != "s20plus_g986n_twrp_t2_approval_v1"
        or item["version"] != VERSION
        or item["binding_sha256"] != prepared["binding_sha256"]
        or item["approval_sha256"]
        != hashlib.sha256(prepared["approval_token"].encode()).hexdigest()
        or item["consumed"] is not True
    ):
        raise T2F2Error("T2 approval differs")
    _text(item["at"], "approval time", 128)
    return item


def _validate_reboot_result(
    run_dir: Path, value: Any, phase: str, binding_sha256: str
) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "schema", "version", "phase", "binding_sha256", "outcome",
            "returncode", "stdout_sha256", "stderr_sha256", "raw_capture",
            "failure_class", "replay_permitted", "at",
        },
        f"{phase} reboot result",
    )
    if (
        item["schema"] != "s20plus_g986n_twrp_t2_reboot_result_v1"
        or item["version"] != VERSION
        or item["phase"] != phase
        or item["binding_sha256"] != binding_sha256
        or item["outcome"] not in {"dispatched", "uncertain"}
        or item["replay_permitted"] is not False
        or item["failure_class"] is not None
        and not isinstance(item["failure_class"], str)
    ):
        raise T2F2Error(f"{phase} reboot result differs")
    _hex64(item["stdout_sha256"], f"{phase} reboot stdout")
    _hex64(item["stderr_sha256"], f"{phase} reboot stderr")
    _text(item["at"], f"{phase} reboot time", 128)
    capture = item["raw_capture"]
    if capture is None:
        if (
            item["outcome"] != "uncertain"
            or item["returncode"] is not None
            or item["failure_class"] != "ReportingCut"
            or item["stdout_sha256"] != hashlib.sha256(b"").hexdigest()
            or item["stderr_sha256"] != hashlib.sha256(b"").hexdigest()
        ):
            raise T2F2Error(f"{phase} cut result differs")
        return item
    receipt = _validate_capture_receipt(capture, run_dir, f"{phase} reboot capture")
    _require_capture_name(
        receipt, rf"{re.escape(phase)}-download-0001\.capture\.json", phase
    )
    handle = b0.raw_capture.load_handle(Path(receipt["path"]))
    stdout = b0.raw_capture.read_stdout(handle, maximum=64 * 1024)
    stderr = b0.raw_capture.read_stderr(handle, maximum=64 * 1024)
    derived = (
        "dispatched"
        if type(handle.returncode) is int
        and handle.returncode == 0
        and not stdout
        and not stderr
        and handle.producer_error_type is None
        and not handle.timed_out
        and not handle.output_exceeded
        else "uncertain"
    )
    if (
        item["returncode"] != handle.returncode
        or item["stdout_sha256"] != hashlib.sha256(stdout).hexdigest()
        or item["stderr_sha256"] != hashlib.sha256(stderr).hexdigest()
        or item["outcome"] != derived
        or item["failure_class"] is not None
    ):
        raise T2F2Error(f"{phase} reboot result is not raw-derived")
    return item


def _validate_transfer_intent_record(
    run_dir: Path, value: Any, kind: str, prepared: dict[str, Any]
) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "schema", "version", "kind", "binding_sha256", "ap",
            "archive_member", "endpoint", "command_shape", "process_cage",
            "attempt", "no_replay", "at",
        },
        f"{kind} transfer intent",
    )
    expected_ap = prepared["binding"][kind]
    expected_shape = [
        "odin4", *(["--reboot"] if kind == "rollback" else []),
        "-a", "AP.tar.md5", "-d", "USBFS",
    ]
    if (
        item["schema"] != "s20plus_g986n_twrp_t2_transfer_intent_v1"
        or item["version"] != VERSION
        or item["kind"] != kind
        or item["binding_sha256"] != prepared["binding_sha256"]
        or item["ap"] != {
            "path": expected_ap["path"],
            "size": expected_ap["size"],
            "sha256": expected_ap["sha256"],
        }
        or item["archive_member"] != h0.AP_MEMBER_NAME
        or item["command_shape"] != expected_shape
        or type(item["attempt"]) is not int
        or item["attempt"] != 1
        or item["no_replay"] is not True
    ):
        raise T2F2Error(f"{kind} transfer intent differs")
    _validate_endpoint(item["endpoint"], f"{kind} intent endpoint")
    arrival_name = (
        "candidate-download-arrival.json"
        if kind == "candidate"
        else "rollback-download-arrival.json"
    )
    if os.path.lexists(run_dir / arrival_name):
        arrival = b0.read_json(
            run_dir / arrival_name,
            f"{kind} bound arrival",
        )
        if not b0.same_download_session(arrival.get("endpoint", {}), item["endpoint"]):
            raise T2F2Error(f"{kind} intent endpoint is not arrival-bound")
    _validate_cage_binding(item["process_cage"], kind, prepared["binding_sha256"])
    _text(item["at"], f"{kind} intent time", 128)
    return item


def _validate_transfer_result_record(
    run_dir: Path, value: Any, kind: str, prepared: dict[str, Any]
) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "schema", "version", "kind", "binding_sha256", "classification",
            "failure_class", "stdout_sha256", "stderr_sha256", "raw_capture",
            "endpoint_pre_identity", "endpoint_post_identity",
            "endpoint_post_state", "process_quiescence_sha256",
            "replay_permitted", "at",
        },
        f"{kind} transfer result",
    )
    intent = _validate_transfer_intent_record(
        run_dir,
        b0.read_json(run_dir / f"{kind}-intent.json", f"{kind} intent"),
        kind,
        prepared,
    )
    cage = intent["process_cage"]
    quiescence = _validate_cage_quiescence(
        run_dir, kind, prepared["binding_sha256"], cage
    )
    if (
        item["schema"] != "s20plus_g986n_twrp_t2_transfer_result_v1"
        or item["version"] != VERSION
        or item["kind"] != kind
        or item["binding_sha256"] != prepared["binding_sha256"]
        or item["classification"] not in {
            "odin_transfer_completed", "odin_local_parse_failure",
            "odin_device_session_failure_or_unknown",
        }
        or item["endpoint_pre_identity"] != intent["endpoint"]["endpoint_identity"]
        or item["endpoint_post_state"] not in {"same", "absent", "changed", "unread"}
        or item["process_quiescence_sha256"] != digest(quiescence)
        or item["replay_permitted"] is not False
    ):
        raise T2F2Error(f"{kind} transfer result differs")
    _hex64(item["stdout_sha256"], f"{kind} stdout")
    _hex64(item["stderr_sha256"], f"{kind} stderr")
    _text(item["at"], f"{kind} result time", 128)
    if item["failure_class"] is not None:
        _text(item["failure_class"], f"{kind} failure class", 256)
    if item["endpoint_post_state"] in {"same", "changed"}:
        identity = item["endpoint_post_identity"]
        if (
            not isinstance(identity, list)
            or len(identity) != 4
            or any(type(part) is not int for part in identity)
        ):
            raise T2F2Error(f"{kind} endpoint post identity differs")
    elif item["endpoint_post_identity"] is not None:
        raise T2F2Error(f"{kind} endpoint post state differs")
    capture = item["raw_capture"]
    if capture is None:
        if (
            item["classification"] != "odin_device_session_failure_or_unknown"
            or item["failure_class"] is None
            or item["stdout_sha256"] != hashlib.sha256(b"").hexdigest()
            or item["stderr_sha256"] != hashlib.sha256(b"").hexdigest()
        ):
            raise T2F2Error(f"{kind} missing capture gained a result")
        return item
    receipt = _validate_capture_receipt(capture, run_dir, f"{kind} transfer capture")
    _require_capture_name(
        receipt, rf"{re.escape(kind)}-transfer-0001\.capture\.json", kind
    )
    handle = b0.raw_capture.load_handle(Path(receipt["path"]))
    stdout = b0.raw_capture.read_stdout(handle, maximum=MAX_RAW_BYTES)
    stderr = b0.raw_capture.read_stderr(handle, maximum=MAX_RAW_BYTES)
    derived = _classify_odin(handle, stdout, stderr)
    if item["endpoint_post_state"] == "unread":
        derived = "odin_device_session_failure_or_unknown"
    if kind == "candidate" and item["endpoint_post_state"] == "absent":
        derived = "odin_device_session_failure_or_unknown"
    if item["endpoint_post_state"] == "changed" and (
        item["endpoint_post_identity"] is None
        or item["endpoint_post_identity"][:3]
        != intent["endpoint"]["endpoint_identity"][:3]
    ):
        derived = "odin_device_session_failure_or_unknown"
    if (
        item["stdout_sha256"] != hashlib.sha256(stdout).hexdigest()
        or item["stderr_sha256"] != hashlib.sha256(stderr).hexdigest()
        or item["classification"] != derived
    ):
        raise T2F2Error(f"{kind} transfer result is not raw-derived")
    return item


def _validate_observation(
    run_dir: Path, value: Any, prepared: dict[str, Any]
) -> dict[str, Any]:
    common = {"schema", "version", "binding_sha256", "claim_verdict", "at"}
    proved = common | {
        "serial_sha256", "topology_sha256", "boot_id_sha256", "values", "capture"
    }
    no_proof = common | {"reason"}
    if (
        not isinstance(value, dict)
        or frozenset(value) not in {frozenset(proved), frozenset(no_proof)}
    ):
        raise T2F2Error("candidate recovery observation schema differs")
    item = value
    if (
        item["schema"] != "s20plus_g986n_twrp_t2_observation_v1"
        or item["version"] != VERSION
        or item["binding_sha256"] != prepared["binding_sha256"]
        or item["claim_verdict"] not in {"PROVED", "NO_PROOF"}
    ):
        raise T2F2Error("candidate recovery observation differs")
    _text(item["at"], "candidate observation time", 128)
    if item["claim_verdict"] == "NO_PROOF":
        if set(item) != no_proof:
            raise T2F2Error("NO_PROOF observation gained evidence")
        _text(item["reason"], "NO_PROOF reason")
        return item
    if set(item) != proved:
        raise T2F2Error("PROVED observation lacks evidence")
    if (
        item["serial_sha256"] != prepared["binding"]["preflight"]["serial_sha256"]
        or item["topology_sha256"]
        != prepared["binding"]["preflight"]["topology_sha256"]
        or item["boot_id_sha256"]
        == prepared["binding"]["preflight"]["boot_id_sha256"]
    ):
        raise T2F2Error("PROVED recovery identity differs")
    _hex64(item["boot_id_sha256"], "recovery boot ID")
    receipt = _validate_capture_receipt(
        item["capture"], run_dir, "candidate recovery observer capture"
    )
    _require_capture_name(
        receipt,
        r"candidate-recovery-observer-0001\.capture\.json",
        "candidate recovery observer",
    )
    handle = b0.raw_capture.load_handle(Path(receipt["path"]))
    values = h0.parse_recovery_observation(
        (
            handle.returncode,
            b0.raw_capture.read_stdout(handle, maximum=h0.MAX_RECOVERY_OBSERVER_BYTES),
            b0.raw_capture.read_stderr(handle, maximum=h0.MAX_RECOVERY_OBSERVER_BYTES),
        )
    )
    if (
        hashlib.sha256(values["boot_id"].encode()).hexdigest()
        != item["boot_id_sha256"]
        or {key: field for key, field in values.items() if key != "boot_id"}
        != item["values"]
    ):
        raise T2F2Error("PROVED recovery observation is not raw-derived")
    return item


def _validate_physical_arm(value: Any, prepared: dict[str, Any]) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "schema", "version", "binding_sha256", "mode", "baseline",
            "existing_endpoint", "initial_listing_sha256", "expires_unix",
            "action", "attempt", "no_replay", "confirmation_token", "at",
        },
        "physical rollback arm",
    )
    core = {key: item[key] for key in item if key not in {"confirmation_token", "at"}}
    if (
        item["schema"] != "s20plus_g986n_twrp_t2_physical_arm_v1"
        or item["version"] != VERSION
        or item["binding_sha256"] != prepared["binding_sha256"]
        or item["mode"] not in {
            "empty-baseline-physical-entry", "already-download-bound-session"
        }
        or item["action"]
        != "attended-physical-entry-to-download-for-stock-recovery-only"
        or type(item["attempt"]) is not int
        or item["attempt"] != 1
        or item["no_replay"] is not True
        or type(item["expires_unix"]) is not int
        or item["confirmation_token"] != PHYSICAL_PREFIX + digest(core)
    ):
        raise T2F2Error("physical rollback arm differs")
    _hex64(item["initial_listing_sha256"], "physical initial listing")
    _text(item["at"], "physical arm time", 128)
    if item["mode"] == "empty-baseline-physical-entry":
        baseline_value = _validate_baseline(
            item["baseline"], "physical rollback baseline"
        )
        if (
            item["existing_endpoint"] is not None
            or item["initial_listing_sha256"] != baseline_value["listing_sha256"]
        ):
            raise T2F2Error("physical empty baseline contains an endpoint")
    else:
        if item["baseline"] is not None:
            raise T2F2Error("already-Download arm contains a baseline")
        _validate_endpoint(item["existing_endpoint"], "physical existing endpoint")
    return item


def _physical_confirmation_sha256(arm: dict[str, Any]) -> str:
    return hashlib.sha256(arm["confirmation_token"].encode()).hexdigest()


def _validate_physical_observation_record(
    run_dir: Path,
    prepared: dict[str, Any],
    arm: dict[str, Any],
    kind: str,
) -> dict[str, Any] | None:
    if kind not in {"initial", "resume"}:
        raise T2F2Error("physical observation kind differs")
    stem = "physical-observation" if kind == "initial" else "physical-resume-observation"
    intent_path = run_dir / f"{stem}-intent.json"
    miss_path = run_dir / f"{stem}-miss.json"
    if not os.path.lexists(intent_path):
        if os.path.lexists(miss_path):
            raise T2F2Error("physical observation miss lacks intent")
        return None
    intent = _exact(
        b0.read_json(intent_path, f"physical {kind} observation intent"),
        {
            "schema", "version", "binding_sha256", "kind",
            "physical_arm_sha256", "confirmation_sha256", "expires_unix",
            "attempt", "no_replay", "at",
        },
        f"physical {kind} observation intent",
    )
    if (
        intent["schema"]
        != "s20plus_g986n_twrp_t2_physical_observation_intent_v1"
        or intent["version"] != VERSION
        or intent["binding_sha256"] != prepared["binding_sha256"]
        or intent["kind"] != kind
        or intent["physical_arm_sha256"] != digest(arm)
        or intent["confirmation_sha256"] != _physical_confirmation_sha256(arm)
        or intent["expires_unix"] != arm["expires_unix"]
        or type(intent["expires_unix"]) is not int
        or type(intent["attempt"]) is not int
        or intent["attempt"] != 1
        or intent["no_replay"] is not True
    ):
        raise T2F2Error(f"physical {kind} observation intent differs")
    _text(intent["at"], f"physical {kind} observation intent time", 128)
    if not os.path.lexists(miss_path):
        return intent
    miss = _exact(
        b0.read_json(miss_path, f"physical {kind} observation miss"),
        {
            "schema", "version", "binding_sha256", "kind",
            "observation_intent_sha256", "reason", "replay_permitted", "at",
        },
        f"physical {kind} observation miss",
    )
    if (
        miss["schema"]
        != "s20plus_g986n_twrp_t2_physical_observation_miss_v1"
        or miss["version"] != VERSION
        or miss["binding_sha256"] != prepared["binding_sha256"]
        or miss["kind"] != kind
        or miss["observation_intent_sha256"] != digest(intent)
        or miss["reason"] not in {
            "bounded-observation-no-arrival", "expired-before-observation",
            "ambiguous-download-listing", "listing-identification-mismatch",
            "resume-observation-intent-consumed-result-absent",
        }
        or miss["replay_permitted"] is not False
    ):
        raise T2F2Error(f"physical {kind} observation miss differs")
    _text(miss["at"], f"physical {kind} observation miss time", 128)
    return miss


def _validate_rollback_arrival(
    value: Any, run_dir: Path, prepared: dict[str, Any]
) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "schema", "version", "binding_sha256", "branch", "endpoint",
            "arrival_listing_sha256", "baseline_sha256", "physical_arm_sha256",
            "confirmation_sha256", "at",
        },
        "rollback Download arrival",
    )
    if (
        item["schema"] != "s20plus_g986n_twrp_t2_rollback_arrival_v1"
        or item["version"] != VERSION
        or item["binding_sha256"] != prepared["binding_sha256"]
        or item["branch"] not in {
            "candidate-outcome-unproved-already-download",
            "automatic-recovery-adb",
            "empty-baseline-physical-entry",
            "already-download-bound-session",
        }
    ):
        raise T2F2Error("rollback Download arrival differs")
    _validate_endpoint(item["endpoint"], "rollback arrival endpoint")
    _hex64(item["arrival_listing_sha256"], "rollback arrival listing")
    _text(item["at"], "rollback arrival time", 128)
    if item["branch"] == "candidate-outcome-unproved-already-download":
        candidate = _validate_transfer_result_record(
            run_dir,
            b0.read_json(run_dir / "candidate-result.json", "candidate result"),
            "candidate",
            prepared,
        )
        expected_baseline = digest(prepared["binding"]["initial_download_baseline"])
        if (
            candidate["classification"] == "odin_transfer_completed"
            or not os.path.lexists(run_dir / "candidate-download-result.json")
            or item["baseline_sha256"] != expected_baseline
            or item["physical_arm_sha256"] is not None
            or item["confirmation_sha256"] is not None
        ):
            raise T2F2Error("candidate-failure rollback arrival provenance differs")
    elif item["branch"] == "automatic-recovery-adb":
        if (
            not os.path.lexists(run_dir / "rollback-download-intent.json")
            or not os.path.lexists(run_dir / "rollback-download-result.json")
        ):
            raise T2F2Error("automatic rollback arrival lacks its reboot result")
        baseline = _validate_baseline(
            b0.read_json(
                run_dir / "rollback-download-baseline.json",
                "rollback Download baseline",
            ),
            "rollback Download baseline",
        )
        if (
            item["baseline_sha256"] != digest(baseline)
            or item["physical_arm_sha256"] is not None
            or item["confirmation_sha256"] is not None
        ):
            raise T2F2Error("automatic rollback arrival provenance differs")
    else:
        arm = _validate_physical_arm(
            b0.read_json(run_dir / "physical-rollback-arm.json", "physical arm"),
            prepared,
        )
        confirmation = _exact(
            b0.read_json(
                run_dir / "physical-rollback-confirmation.json",
                "physical confirmation",
            ),
            {
                "schema", "version", "binding_sha256", "confirmation_sha256",
                "consumed", "at",
            },
            "physical confirmation",
        )
        expected_confirmation = hashlib.sha256(
            arm["confirmation_token"].encode()
        ).hexdigest()
        initial_observation = _validate_physical_observation_record(
            run_dir, prepared, arm, "initial"
        )
        resume_observation = _validate_physical_observation_record(
            run_dir, prepared, arm, "resume"
        )
        if (
            item["branch"] != arm["mode"]
            or item["baseline_sha256"]
            != (None if arm["baseline"] is None else digest(arm["baseline"]))
            or item["physical_arm_sha256"] != digest(arm)
            or item["confirmation_sha256"] != expected_confirmation
            or confirmation
            != {
                "schema": "s20plus_g986n_twrp_t2_physical_confirmation_v1",
                "version": VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "confirmation_sha256": expected_confirmation,
                "consumed": True,
                "at": confirmation.get("at"),
            }
            or initial_observation is None and resume_observation is None
            or os.path.lexists(run_dir / "physical-observation-miss.json")
            or os.path.lexists(run_dir / "physical-resume-observation-miss.json")
        ):
            raise T2F2Error("physical rollback arrival provenance differs")
        _text(confirmation["at"], "physical confirmation time", 128)
    return item


def validate_journal(run_dir: Path, prepared: dict[str, Any]) -> set[str]:
    """Validate the complete currently published graph before any continuation."""

    actual = validate_namespace(run_dir)
    dependencies = {
        "prepare-recovery-read-intent.json": {"allocation.json"},
        "execute-pre-download-recovery-read-intent.json": {"approval.json"},
        "pre-candidate-abort-recovery-read-intent.json": {"prepared.json"},
        "final-recovery-read-intent.json": {"rollback-result.json"},
        "prepared.json": {
            "allocation.json", "candidate-download-baseline.json",
            "prepare-recovery-read-intent.json",
        },
        "approval.json": {"prepared.json"},
        "candidate-download-intent.json": {
            "approval.json", "execute-pre-download-recovery-read-intent.json"
        },
        "candidate-download-result.json": {"candidate-download-intent.json"},
        "candidate-download-arrival.json": {
            "candidate-download-intent.json", "candidate-download-result.json"
        },
        "candidate-intent.json": {"candidate-download-arrival.json"},
        "candidate-cage-quiescent.json": {"candidate-intent.json"},
        "candidate-result.json": {"candidate-intent.json", "candidate-cage-quiescent.json"},
        "recovery-boot-intent.json": {"candidate-result.json"},
        "candidate-observation-intent.json": {"recovery-boot-intent.json"},
        "candidate-observation.json": {"candidate-observation-intent.json"},
        "rollback-download-baseline.json": {"candidate-observation.json"},
        "rollback-download-intent.json": {"rollback-download-baseline.json"},
        "rollback-download-result.json": {"rollback-download-intent.json"},
        "physical-rollback-arm.json": {"candidate-intent.json", "candidate-result.json"},
        "physical-rollback-confirmation.json": {"physical-rollback-arm.json"},
        "physical-observation-intent.json": {"physical-rollback-confirmation.json"},
        "physical-observation-miss.json": {"physical-observation-intent.json"},
        "physical-resume-observation-intent.json": {
            "physical-rollback-confirmation.json"
        },
        "physical-resume-observation-miss.json": {
            "physical-resume-observation-intent.json"
        },
        "rollback-download-arrival.json": {"candidate-intent.json"},
        "rollback-intent.json": {"rollback-download-arrival.json"},
        "rollback-cage-quiescent.json": {"rollback-intent.json"},
        "rollback-result.json": {"rollback-intent.json", "rollback-cage-quiescent.json"},
        "final-health.json": {"rollback-result.json", "final-recovery-read-intent.json"},
        "terminal.json": set(),
    }
    for node, required in dependencies.items():
        if node in actual and not required <= actual:
            raise T2F2Error(f"T2 journal dependency is missing for {node}")
    for phase in (
        "prepare", "execute-pre-download", "pre-candidate-abort", "final"
    ):
        name = f"{phase}-recovery-read-intent.json"
        if name not in actual:
            continue
        read_intent = _exact(
            b0.read_json(run_dir / name, f"{phase} recovery read intent"),
            {
                "schema", "version", "phase", "target", "serial_sha256",
                "topology_sha256", "boot_id_sha256", "expected_size",
                "expected_sha256", "attempt", "no_replay", "at",
            },
            f"{phase} recovery read intent",
        )
        if (
            read_intent["schema"]
            != "s20plus_g986n_twrp_t2_recovery_read_intent_v1"
            or read_intent["version"] != VERSION
            or read_intent["phase"] != phase
            or read_intent["target"] != h0.EXPECTED_TARGET
            or read_intent["topology_sha256"]
            != b0.EXPECTED_ANDROID_TOPOLOGY_SHA256
            or read_intent["expected_size"] != h0.ROLLBACK_RECOVERY_SIZE
            or type(read_intent["expected_size"]) is not int
            or read_intent["expected_sha256"] != h0.ROLLBACK_RECOVERY_SHA256
            or type(read_intent["attempt"]) is not int
            or read_intent["attempt"] != 1
            or read_intent["no_replay"] is not True
        ):
            raise T2F2Error(f"{phase} recovery read intent differs")
        _hex64(read_intent["serial_sha256"], f"{phase} recovery read serial")
        _hex64(read_intent["boot_id_sha256"], f"{phase} recovery read boot")
        _text(read_intent["at"], f"{phase} recovery read time", 128)
    if "approval.json" in actual:
        _validate_approval(b0.read_json(run_dir / "approval.json", "approval"), prepared)
    if "candidate-download-intent.json" in actual:
        item = _exact(
            b0.read_json(
                run_dir / "candidate-download-intent.json", "candidate Download intent"
            ),
            {
                "schema", "version", "phase", "binding_sha256", "source",
                "baseline_sha256", "attempt", "no_replay", "at",
            },
            "candidate Download intent",
        )
        if (
            item["schema"] != "s20plus_g986n_twrp_t2_download_intent_v1"
            or item["version"] != VERSION
            or item["phase"] != "candidate"
            or item["binding_sha256"] != prepared["binding_sha256"]
            or item["baseline_sha256"]
            != digest(prepared["binding"]["initial_download_baseline"])
            or type(item["attempt"]) is not int
            or item["attempt"] != 1
            or item["no_replay"] is not True
        ):
            raise T2F2Error("candidate Download intent differs")
        _validate_health(item["source"], run_dir, "candidate Download source")
        _text(item["at"], "candidate Download intent time", 128)
    if "candidate-download-result.json" in actual:
        _validate_reboot_result(
            run_dir,
            b0.read_json(run_dir / "candidate-download-result.json", "candidate reboot"),
            "candidate",
            prepared["binding_sha256"],
        )
    if "candidate-download-arrival.json" in actual:
        _validate_arrival(
            b0.read_json(run_dir / "candidate-download-arrival.json", "candidate arrival"),
            prepared,
            "candidate arrival",
        )
    for kind in ("candidate", "rollback"):
        if f"{kind}-intent.json" in actual:
            _validate_transfer_intent_record(
                run_dir,
                b0.read_json(run_dir / f"{kind}-intent.json", f"{kind} intent"),
                kind,
                prepared,
            )
        if f"{kind}-result.json" in actual:
            _validate_transfer_result_record(
                run_dir,
                b0.read_json(run_dir / f"{kind}-result.json", f"{kind} result"),
                kind,
                prepared,
            )
    if "recovery-boot-intent.json" in actual:
        item = _exact(
            b0.read_json(run_dir / "recovery-boot-intent.json", "recovery boot intent"),
            {
                "schema", "version", "binding_sha256", "candidate_result_sha256",
                "action", "attempt", "no_replay", "at",
            },
            "recovery boot intent",
        )
        candidate = _validate_transfer_result_record(
            run_dir,
            b0.read_json(run_dir / "candidate-result.json", "candidate result"),
            "candidate",
            prepared,
        )
        if (
            item["schema"] != "s20plus_g986n_twrp_t2_recovery_boot_intent_v1"
            or item["version"] != VERSION
            or item["binding_sha256"] != prepared["binding_sha256"]
            or candidate["classification"] != "odin_transfer_completed"
            or item["candidate_result_sha256"] != digest(candidate)
            or item["action"] != "attended-direct-recovery-key-chord-once"
            or type(item["attempt"]) is not int
            or item["attempt"] != 1
            or item["no_replay"] is not True
        ):
            raise T2F2Error("recovery boot intent differs")
        _text(item["at"], "recovery boot intent time", 128)
    if "candidate-observation-intent.json" in actual:
        item = _exact(
            b0.read_json(
                run_dir / "candidate-observation-intent.json", "observation intent"
            ),
            {
                "schema", "version", "binding_sha256", "attempt", "no_replay", "at"
            },
            "observation intent",
        )
        if (
            item["schema"] != "s20plus_g986n_twrp_t2_observation_intent_v1"
            or item["version"] != VERSION
            or item["binding_sha256"] != prepared["binding_sha256"]
            or type(item["attempt"]) is not int
            or item["attempt"] != 1
            or item["no_replay"] is not True
        ):
            raise T2F2Error("observation intent differs")
        _text(item["at"], "observation intent time", 128)
    if "candidate-observation.json" in actual:
        _validate_observation(
            run_dir,
            b0.read_json(run_dir / "candidate-observation.json", "observation"),
            prepared,
        )
    if "rollback-download-intent.json" in actual:
        item = _exact(
            b0.read_json(
                run_dir / "rollback-download-intent.json", "rollback Download intent"
            ),
            {
                "schema", "version", "binding_sha256", "source",
                "source_boot_id_sha256", "baseline_sha256", "attempt",
                "no_replay", "at",
            },
            "rollback Download intent",
        )
        observation = _validate_observation(
            run_dir,
            b0.read_json(run_dir / "candidate-observation.json", "observation"),
            prepared,
        )
        baseline = _validate_baseline(
            b0.read_json(run_dir / "rollback-download-baseline.json", "rollback baseline"),
            "rollback baseline",
        )
        if (
            item["schema"]
            != "s20plus_g986n_twrp_t2_rollback_download_intent_v1"
            or item["version"] != VERSION
            or item["binding_sha256"] != prepared["binding_sha256"]
            or item["source"] != "proved-recovery-adb"
            or observation["claim_verdict"] != "PROVED"
            or item["source_boot_id_sha256"] != observation["boot_id_sha256"]
            or item["baseline_sha256"] != digest(baseline)
            or type(item["attempt"]) is not int
            or item["attempt"] != 1
            or item["no_replay"] is not True
        ):
            raise T2F2Error("rollback Download intent differs")
        _text(item["at"], "rollback Download intent time", 128)
    if "rollback-download-result.json" in actual:
        _validate_reboot_result(
            run_dir,
            b0.read_json(run_dir / "rollback-download-result.json", "rollback reboot"),
            "rollback",
            prepared["binding_sha256"],
        )
    if "physical-rollback-arm.json" in actual:
        arm = _validate_physical_arm(
            b0.read_json(run_dir / "physical-rollback-arm.json", "physical arm"),
            prepared,
        )
        if "physical-rollback-confirmation.json" in actual:
            confirmation = _exact(
                b0.read_json(
                    run_dir / "physical-rollback-confirmation.json",
                    "physical confirmation",
                ),
                {
                    "schema", "version", "binding_sha256",
                    "confirmation_sha256", "consumed", "at",
                },
                "physical confirmation",
            )
            if (
                confirmation["schema"]
                != "s20plus_g986n_twrp_t2_physical_confirmation_v1"
                or confirmation["version"] != VERSION
                or confirmation["binding_sha256"] != prepared["binding_sha256"]
                or confirmation["confirmation_sha256"]
                != hashlib.sha256(arm["confirmation_token"].encode()).hexdigest()
                or confirmation["consumed"] is not True
            ):
                raise T2F2Error("physical confirmation differs")
            _text(confirmation["at"], "physical confirmation time", 128)
        initial_physical = _validate_physical_observation_record(
            run_dir, prepared, arm, "initial"
        )
        resumed_physical = _validate_physical_observation_record(
            run_dir, prepared, arm, "resume"
        )
        if (
            "physical-observation-miss.json" in actual
            and "rollback-download-arrival.json" in actual
        ) or (
            "physical-resume-observation-miss.json" in actual
            and "rollback-download-arrival.json" in actual
        ) or (
            "physical-observation-miss.json" in actual
            and "physical-resume-observation-intent.json" in actual
        ):
            raise T2F2Error("physical observation has both miss and arrival")
    if "rollback-download-arrival.json" in actual:
        _validate_rollback_arrival(
            b0.read_json(run_dir / "rollback-download-arrival.json", "rollback arrival"),
            run_dir,
            prepared,
        )
    if "final-health.json" in actual:
        _validate_health(
            b0.read_json(run_dir / "final-health.json", "final health"),
            run_dir,
            "final health",
        )
    claim_path = candidate_claim_path()
    if os.path.lexists(claim_path):
        claim = validate_candidate_claim(
            b0.read_json(claim_path, "global candidate claim"), run_dir, prepared
        )
        if "candidate-download-arrival.json" not in actual:
            raise T2F2Error("global candidate claim lacks candidate Download arrival")
    elif "candidate-intent.json" in actual:
        raise T2F2Error("candidate intent lacks the global no-replay claim")
    if "terminal.json" in actual:
        _validate_terminal(run_dir, prepared, actual)
    return actual


def _validate_terminal(
    run_dir: Path, prepared: dict[str, Any], actual: set[str]
) -> dict[str, Any]:
    terminal = b0.read_json(run_dir / "terminal.json", "T2 terminal")
    if terminal.get("schema") == "s20plus_g986n_twrp_t2_retained_terminal_v1":
        item = _exact(
            terminal,
            {
                "schema", "version", "binding_sha256", "verdict",
                "candidate_claim", "candidate_attempts", "rollback_attempts",
                "candidate_replay_permitted", "candidate_retained",
                "stock_rollback", "recovery_observation",
                "partition_transfer_attempts", "candidate_transfer_proved",
                "proved_recovery_partition_transfers",
                "all_other_partition_transfers", "s22plus_commands",
                "a90_commands", "other_target_commands", "at",
            },
            "retained T2 terminal",
        )
        required = {
            "candidate-intent.json", "candidate-result.json",
            "recovery-boot-intent.json", "candidate-observation-intent.json",
            "candidate-observation.json",
        }
        forbidden = {
            "rollback-download-intent.json", "rollback-download-result.json",
            "rollback-download-arrival.json", "rollback-intent.json",
            "rollback-result.json", "final-health.json",
        } | PHYSICAL_ROLLBACK_NODES
        if not required <= actual or forbidden & actual:
            raise T2F2Error("retained T2 terminal graph differs")
        candidate = _validate_transfer_result_record(
            run_dir,
            b0.read_json(run_dir / "candidate-result.json", "candidate result"),
            "candidate",
            prepared,
        )
        observation = _validate_observation(
            run_dir,
            b0.read_json(run_dir / "candidate-observation.json", "observation"),
            prepared,
        )
        if (
            item["version"] != VERSION
            or item["binding_sha256"] != prepared["binding_sha256"]
            or item["verdict"] != "PROVED_T2_RECOVERY_RETAINED"
            or item["candidate_claim"] != "PROVED"
            or candidate["classification"] != "odin_transfer_completed"
            or observation["claim_verdict"] != "PROVED"
            or item["recovery_observation"] != observation
            or item["stock_rollback"] != prepared["binding"]["rollback"]
            or type(item["candidate_attempts"]) is not int
            or item["candidate_attempts"] != 1
            or type(item["rollback_attempts"]) is not int
            or item["rollback_attempts"] != 0
            or item["candidate_replay_permitted"] is not False
            or item["candidate_retained"] is not True
            or type(item["partition_transfer_attempts"]) is not int
            or item["partition_transfer_attempts"] != 1
            or item["candidate_transfer_proved"] is not True
            or type(item["proved_recovery_partition_transfers"]) is not int
            or item["proved_recovery_partition_transfers"] != 1
            or any(
                type(item[name]) is not int or item[name] != 0
                for name in (
                    "all_other_partition_transfers", "s22plus_commands",
                    "a90_commands", "other_target_commands",
                )
            )
            or observation["boot_id_sha256"]
            == prepared["binding"]["preflight"]["boot_id_sha256"]
        ):
            raise T2F2Error("retained T2 terminal is not graph-derived")
        _text(item["at"], "retained T2 terminal time", 128)
        return item
    if terminal.get("schema") == "s20plus_g986n_twrp_t2_pre_candidate_abort_v1":
        item = _exact(
            terminal,
            {
                "schema", "version", "binding_sha256", "verdict",
                "global_candidate_claim_consumed",
                "candidate_attempts", "rollback_attempts",
                "partition_transfer_attempts", "candidate_replay_permitted",
                "final_health", "at",
            },
            "pre-candidate terminal",
        )
        if (
            item["version"] != VERSION
            or item["binding_sha256"] != prepared["binding_sha256"]
            or item["verdict"]
            != (
                "ABORTED_AFTER_CANDIDATE_CLAIM_NO_TRANSFER_STOCK_RECOVERY_HEALTHY"
                if item["global_candidate_claim_consumed"] is True
                else "ABORTED_PRE_CANDIDATE_STOCK_RECOVERY_HEALTHY"
            )
            or type(item["global_candidate_claim_consumed"]) is not bool
            or item["global_candidate_claim_consumed"]
            is not os.path.lexists(candidate_claim_path())
            or any(
                type(item[name]) is not int or item[name] != 0
                for name in (
                    "candidate_attempts", "rollback_attempts",
                    "partition_transfer_attempts",
                )
            )
            or item["candidate_replay_permitted"] is not False
            or "candidate-intent.json" in actual
            or "rollback-intent.json" in actual
            or "pre-candidate-abort-recovery-read-intent.json" not in actual
        ):
            raise T2F2Error("pre-candidate terminal differs")
        health = _validate_health(item["final_health"], run_dir, "abort final health")
        if health["boot_id_sha256"] == prepared["binding"]["preflight"]["boot_id_sha256"]:
            raise T2F2Error("pre-candidate abort did not return through a new boot")
        _text(item["at"], "pre-candidate terminal time", 128)
        return item
    item = _exact(
        terminal,
        {
            "schema", "version", "binding_sha256", "verdict", "candidate_claim",
            "candidate_attempts", "rollback_attempts", "candidate_replay_permitted",
            "rollback_replay_permitted", "final_health",
            "final_stock_recovery_proved", "partition_transfer_attempts",
            "candidate_transfer_proved", "rollback_transfer_proved",
            "proved_recovery_partition_transfers", "all_other_partition_transfers",
            "s22plus_commands", "a90_commands", "other_target_commands", "at",
        },
        "T2 terminal",
    )
    if not {
        "candidate-intent.json", "candidate-result.json", "rollback-intent.json",
        "rollback-result.json", "final-health.json",
    } <= actual:
        raise T2F2Error("T2 terminal lacks its complete result graph")
    candidate = _validate_transfer_result_record(
        run_dir,
        b0.read_json(run_dir / "candidate-result.json", "candidate result"),
        "candidate",
        prepared,
    )
    rollback = _validate_transfer_result_record(
        run_dir,
        b0.read_json(run_dir / "rollback-result.json", "rollback result"),
        "rollback",
        prepared,
    )
    final_health = _validate_health(
        b0.read_json(run_dir / "final-health.json", "final health"),
        run_dir,
        "final health",
    )
    observation = (
        _validate_observation(
            run_dir,
            b0.read_json(run_dir / "candidate-observation.json", "observation"),
            prepared,
        )
        if "candidate-observation.json" in actual
        else None
    )
    candidate_complete = candidate["classification"] == "odin_transfer_completed"
    rollback_complete = rollback["classification"] == "odin_transfer_completed"
    candidate_claim = (
        observation["claim_verdict"] if observation is not None else "NO_PROOF"
    )
    proved = (
        candidate_complete
        and rollback_complete
        and observation is not None
        and observation["claim_verdict"] == "PROVED"
        and len(
            {
                prepared["binding"]["preflight"]["boot_id_sha256"],
                observation["boot_id_sha256"],
                final_health["boot_id_sha256"],
            }
        )
        == 3
    )
    expected_verdict = (
        "PROVED_T2_RETURNED_STOCK_RECOVERY_HEALTHY"
        if proved
        else (
            "NO_PROOF_T2_RETURNED_STOCK_RECOVERY_HEALTHY"
            if rollback_complete
            else "NO_PROOF_T2_STOCK_RECOVERY_HEALTHY_TRANSFER_UNPROVED"
        )
    )
    if (
        item["schema"] != "s20plus_g986n_twrp_t2_terminal_v1"
        or item["version"] != VERSION
        or item["binding_sha256"] != prepared["binding_sha256"]
        or item["verdict"] != expected_verdict
        or item["candidate_claim"] != candidate_claim
        or type(item["candidate_attempts"]) is not int
        or item["candidate_attempts"] != 1
        or type(item["rollback_attempts"]) is not int
        or item["rollback_attempts"] != 1
        or item["candidate_replay_permitted"] is not False
        or item["rollback_replay_permitted"] is not False
        or item["final_health"] != final_health
        or item["final_stock_recovery_proved"] is not True
        or type(item["partition_transfer_attempts"]) is not int
        or item["partition_transfer_attempts"] != 2
        or item["candidate_transfer_proved"] is not candidate_complete
        or item["rollback_transfer_proved"] is not rollback_complete
        or type(item["proved_recovery_partition_transfers"]) is not int
        or item["proved_recovery_partition_transfers"]
        != int(candidate_complete) + int(rollback_complete)
        or any(
            type(item[name]) is not int or item[name] != 0
            for name in (
                "all_other_partition_transfers", "s22plus_commands",
                "a90_commands", "other_target_commands",
            )
        )
        or final_health["boot_id_sha256"]
        == prepared["binding"]["preflight"]["boot_id_sha256"]
    ):
        raise T2F2Error("T2 terminal is not graph-derived")
    _text(item["at"], "terminal time", 128)
    return item


def _same_endpoint(expected: dict[str, Any]) -> dict[str, Any]:
    current = b0.identify_download()
    if not b0.same_download_session(current, expected):
        raise T2F2Error("Download endpoint session changed")
    return current


def _classify_odin(handle: Any, stdout: bytes, stderr: bytes) -> str:
    if (
        type(handle.returncode) is not int
        or handle.producer_error_type is not None
        or handle.timed_out
        or handle.output_exceeded
        or not stdout.startswith(b0.ODIN_CAGE_ENTRY_MARKER)
    ):
        return "odin_device_session_failure_or_unknown"
    output = stdout[len(b0.ODIN_CAGE_ENTRY_MARKER) :]
    session = (
        b"Setup Connection", b"initializeConnection", b"Receive PIT Info",
        b"Upload Binaries", b"Close Connection",
    )
    if b"Fail parse" in output and not stderr and not any(
        marker in output for marker in session
    ):
        return "odin_local_parse_failure"
    lowered = output.lower() + b"\n" + stderr.lower()
    if any(token in lowered for token in (b"fail", b"error", b"exception", b"abort")):
        return "odin_device_session_failure_or_unknown"
    ordered = (
        b"Setup Connection",
        b"initializeConnection",
        b"Receive PIT Info",
        b"success getpit",
        b"Upload Binaries",
        b"recovery.img.lz4",
        b"(100%)",
        b"Close Connection",
    )
    position = 0
    for marker in ordered:
        found = output.find(marker, position)
        if found < 0:
            return "odin_device_session_failure_or_unknown"
        position = found + len(marker)
    if (
        handle.returncode == 0
        and not stderr
        and output.count(b"recovery.img.lz4") == 1
        and output.count(b"Close Connection") == 1
    ):
        return "odin_transfer_completed"
    return "odin_device_session_failure_or_unknown"


def _transfer(
    run_dir: Path,
    prepared: dict[str, Any],
    kind: str,
    endpoint: dict[str, Any],
) -> dict[str, Any]:
    if kind == "candidate":
        path, size, sha256 = h0.CANDIDATE_AP, h0.CANDIDATE_AP_SIZE, h0.CANDIDATE_AP_SHA256
        member_size, member_sha, tar_md5 = (
            h0.CANDIDATE_MEMBER_SIZE, h0.CANDIDATE_MEMBER_SHA256, h0.CANDIDATE_TAR_MD5
        )
        reboot = False
    elif kind == "rollback":
        path, size, sha256 = h0.ROLLBACK_AP, h0.ROLLBACK_AP_SIZE, h0.ROLLBACK_AP_SHA256
        member_size, member_sha, tar_md5 = (
            h0.ROLLBACK_MEMBER_SIZE, h0.ROLLBACK_MEMBER_SHA256, h0.ROLLBACK_TAR_MD5
        )
        reboot = True
    else:
        raise T2F2Error("unknown recovery transfer kind")
    intent_path = run_dir / f"{kind}-intent.json"
    result_path = run_dir / f"{kind}-result.json"
    if os.path.lexists(intent_path) or os.path.lexists(result_path):
        raise T2F2Error(f"{kind} attempt is already consumed")
    current = _same_endpoint(endpoint)
    h0.validate_recovery_only_ap(
        path,
        label=kind,
        expected_size=size,
        expected_sha256=sha256,
        expected_member_size=member_size,
        expected_member_sha256=member_sha,
        expected_tar_md5=tar_md5,
    )
    binding_sha256 = prepared["binding_sha256"]
    _cage, cage_binding = b0.prepare_process_cage(run_dir, kind, binding_sha256)
    command = [str(h0.ODIN)]
    if reboot:
        command.append("--reboot")
    command.extend(["-a", str(path), "-d", current["device"]])
    intent = {
        "schema": "s20plus_g986n_twrp_t2_transfer_intent_v1",
        "version": VERSION,
        "kind": kind,
        "binding_sha256": binding_sha256,
        "ap": {"path": str(path), "size": size, "sha256": sha256},
        "archive_member": h0.AP_MEMBER_NAME,
        "endpoint": current,
        "command_shape": ["odin4", *( ["--reboot"] if reboot else [] ), "-a", "AP.tar.md5", "-d", "USBFS"],
        "process_cage": cage_binding,
        "attempt": 1,
        "no_replay": True,
        "at": utc_now(),
    }
    b0.durable_json(intent_path, intent)
    handle = None
    stdout = b""
    stderr = b""
    failure_class: str | None = None
    post_state = "unread"
    post_identity: list[int] | None = None
    try:
        with h0.pin_regular_file(
            h0.ODIN,
            label="Odin4",
            expected_size=h0.ODIN_SIZE,
            expected_sha256=h0.ODIN_SHA256,
        ) as (odin_fd, _odin_receipt), h0.pin_regular_file(
            path,
            label=kind,
            expected_size=size,
            expected_sha256=sha256,
        ) as (ap_fd, _ap_receipt), h0.pin_regular_file(
            b0.DASH,
            label="process-cage shell",
            expected_size=b0.DASH_SIZE,
            expected_sha256=b0.DASH_SHA256,
        ) as (dash_fd, _dash_receipt):
            opened = {
                "odin": h0._identity(os.fstat(odin_fd)),
                "ap": h0._identity(os.fstat(ap_fd)),
                "dash": h0._identity(os.fstat(dash_fd)),
            }
            dispatch_endpoint = _same_endpoint(current)
            if (
                b0.endpoint_stat(dispatch_endpoint["device"])
                != tuple(dispatch_endpoint["endpoint_identity"])
            ):
                raise T2F2Error("Download endpoint changed at Odin dispatch")
            handle, stdout, stderr = _capture(
                run_dir,
                f"{kind}-transfer",
                [
                    str(b0.DASH), "-c", b0.ODIN_CAGE_ENTRY_SCRIPT,
                    "s20plus-t2-odin-cage", cage_binding["cage"], *command,
                ],
                timeout=300,
                maximum=MAX_RAW_BYTES,
                env=b0.ODIN_FIXED_ENV,
                start_new_session=True,
            )
            if (
                h0._identity(os.fstat(odin_fd)) != opened["odin"]
                or h0._identity(os.lstat(h0.ODIN)) != opened["odin"]
                or h0._identity(os.fstat(ap_fd)) != opened["ap"]
                or h0._identity(os.lstat(path)) != opened["ap"]
                or h0._identity(os.fstat(dash_fd)) != opened["dash"]
                or h0._identity(os.lstat(b0.DASH)) != opened["dash"]
            ):
                raise T2F2Error("an opened transfer input changed across Odin")
            try:
                observed = b0.endpoint_stat(current["device"])
                post_identity = list(observed)
                post_state = (
                    "same"
                    if post_identity == current["endpoint_identity"]
                    else "changed"
                )
            except FileNotFoundError:
                post_state = "absent"
    except Exception as exc:
        failure_class = type(exc).__name__
    finally:
        quiescence = b0.quiesce_process_cage(run_dir, kind, binding_sha256)
    classification = (
        _classify_odin(handle, stdout, stderr)
        if handle is not None
        else "odin_device_session_failure_or_unknown"
    )
    if post_state == "unread":
        classification = "odin_device_session_failure_or_unknown"
    if kind == "candidate" and post_state == "absent":
        classification = "odin_device_session_failure_or_unknown"
    if (
        post_state == "changed"
        and (
            post_identity is None
            or post_identity[:3] != current["endpoint_identity"][:3]
        )
    ):
        classification = "odin_device_session_failure_or_unknown"
    result = {
        "schema": "s20plus_g986n_twrp_t2_transfer_result_v1",
        "version": VERSION,
        "kind": kind,
        "binding_sha256": binding_sha256,
        "classification": classification,
        "failure_class": failure_class,
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "raw_capture": None if handle is None else _capture_receipt(handle),
        "endpoint_pre_identity": current["endpoint_identity"],
        "endpoint_post_identity": post_identity,
        "endpoint_post_state": post_state,
        "process_quiescence_sha256": None if quiescence is None else digest(quiescence),
        "replay_permitted": False,
        "at": utc_now(),
    }
    b0.durable_json(result_path, result)
    return _validate_transfer_result_record(
        run_dir, result, kind, prepared
    )


def _capture_paths(run_dir: Path, prefix: str) -> list[Path]:
    return sorted(run_dir.glob(f"{prefix}-[0-9][0-9][0-9][0-9].capture.json"))


def require_all_transfer_processes_quiescent(
    run_dir: Path, prepared: dict[str, Any]
) -> None:
    for kind in ("candidate", "rollback"):
        intent_path = run_dir / f"{kind}-intent.json"
        if not os.path.lexists(intent_path):
            continue
        intent = _validate_transfer_intent_record(
            run_dir,
            b0.read_json(intent_path, f"{kind} intent"),
            kind,
            prepared,
        )
        if not os.path.lexists(run_dir / f"{kind}-cage-quiescent.json"):
            b0.quiesce_process_cage(
                run_dir, kind, prepared["binding_sha256"]
            )
        _validate_cage_quiescence(
            run_dir,
            kind,
            prepared["binding_sha256"],
            intent["process_cage"],
        )


def recover_transfer_result(
    run_dir: Path, prepared: dict[str, Any], kind: str
) -> dict[str, Any]:
    """Publish one non-replay result after quiescing an intent-bound Odin cage."""

    require_all_transfer_processes_quiescent(run_dir, prepared)
    result_path = run_dir / f"{kind}-result.json"
    if os.path.lexists(result_path):
        return _validate_transfer_result_record(
            run_dir,
            b0.read_json(result_path, f"{kind} result"),
            kind,
            prepared,
        )
    intent = _validate_transfer_intent_record(
        run_dir,
        b0.read_json(run_dir / f"{kind}-intent.json", f"{kind} intent"),
        kind,
        prepared,
    )
    captures = _capture_paths(run_dir, f"{kind}-transfer")
    if len(captures) > 1:
        raise T2F2Error(f"{kind} transfer has multiple raw receipts")
    handle = None
    stdout = b""
    stderr = b""
    raw_receipt = None
    if captures:
        try:
            handle = b0.raw_capture.load_handle(captures[0])
            b0.validated_raw_capture_record(handle, f"{kind} recovered capture")
            stdout = b0.raw_capture.read_stdout(handle, maximum=MAX_RAW_BYTES)
            stderr = b0.raw_capture.read_stderr(handle, maximum=MAX_RAW_BYTES)
            raw_receipt = _capture_receipt(handle)
        except Exception:
            handle = None
            stdout = b""
            stderr = b""
            raw_receipt = None
    endpoint = intent["endpoint"]
    post_state = "unread"
    post_identity: list[int] | None = None
    try:
        post_identity = list(b0.endpoint_stat(endpoint["device"]))
        post_state = (
            "same"
            if post_identity == endpoint["endpoint_identity"]
            else "changed"
        )
    except FileNotFoundError:
        post_state = "absent"
    except Exception:
        post_state = "unread"
        post_identity = None
    classification = (
        _classify_odin(handle, stdout, stderr)
        if handle is not None
        else "odin_device_session_failure_or_unknown"
    )
    if post_state == "unread" or (kind == "candidate" and post_state == "absent"):
        classification = "odin_device_session_failure_or_unknown"
    if post_state == "changed" and (
        post_identity is None
        or post_identity[:3] != endpoint["endpoint_identity"][:3]
    ):
        classification = "odin_device_session_failure_or_unknown"
    quiescence = b0.read_json(
        run_dir / f"{kind}-cage-quiescent.json", f"{kind} cage quiescence"
    )
    result = {
        "schema": "s20plus_g986n_twrp_t2_transfer_result_v1",
        "version": VERSION,
        "kind": kind,
        "binding_sha256": prepared["binding_sha256"],
        "classification": classification,
        "failure_class": "ReportingCut",
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "raw_capture": raw_receipt,
        "endpoint_pre_identity": endpoint["endpoint_identity"],
        "endpoint_post_identity": post_identity,
        "endpoint_post_state": post_state,
        "process_quiescence_sha256": digest(quiescence),
        "replay_permitted": False,
        "at": utc_now(),
    }
    b0.durable_json(result_path, result)
    return _validate_transfer_result_record(
        run_dir, result, kind, prepared
    )


def recover_reboot_result(
    run_dir: Path, prepared: dict[str, Any], phase: str
) -> dict[str, Any]:
    result_path = run_dir / f"{phase}-download-result.json"
    if os.path.lexists(result_path):
        return _validate_reboot_result(
            run_dir,
            b0.read_json(result_path, f"{phase} reboot result"),
            phase,
            prepared["binding_sha256"],
        )
    captures = _capture_paths(run_dir, f"{phase}-download")
    if len(captures) > 1:
        raise T2F2Error(f"{phase} reboot has multiple raw receipts")
    handle = None
    stdout = b""
    stderr = b""
    raw_receipt = None
    if captures:
        try:
            handle = b0.raw_capture.load_handle(captures[0])
            b0.validated_raw_capture_record(handle, f"{phase} recovered reboot")
            stdout = b0.raw_capture.read_stdout(handle, maximum=64 * 1024)
            stderr = b0.raw_capture.read_stderr(handle, maximum=64 * 1024)
            raw_receipt = _capture_receipt(handle)
        except Exception:
            handle = None
            stdout = b""
            stderr = b""
            raw_receipt = None
    dispatched = (
        handle is not None
        and type(handle.returncode) is int
        and handle.returncode == 0
        and not stdout
        and not stderr
        and handle.producer_error_type is None
        and not handle.timed_out
        and not handle.output_exceeded
    )
    result = {
        "schema": "s20plus_g986n_twrp_t2_reboot_result_v1",
        "version": VERSION,
        "phase": phase,
        "binding_sha256": prepared["binding_sha256"],
        "outcome": "dispatched" if dispatched else "uncertain",
        "returncode": None if handle is None else handle.returncode,
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "raw_capture": raw_receipt,
        "failure_class": "ReportingCut" if handle is None else None,
        "replay_permitted": False,
        "at": utc_now(),
    }
    b0.durable_json(result_path, result)
    return _validate_reboot_result(
        run_dir, result, phase, prepared["binding_sha256"]
    )


def _candidate_claim(run_dir: Path, prepared: dict[str, Any]) -> None:
    path = candidate_claim_path()
    require_fresh_candidate_unclaimed()
    b0.durable_json(
        path,
        {
            "schema": "s20plus_g986n_twrp_t2_global_claim_v1",
            "version": VERSION,
            "run_id": _run_id(run_dir),
            "binding_sha256": prepared["binding_sha256"],
            "candidate_sha256": h0.CANDIDATE_AP_SHA256,
            "candidate_replay": False,
            "at": utc_now(),
        },
    )


def _rollback_from_download(
    run_dir: Path,
    prepared: dict[str, Any],
    endpoint: dict[str, Any],
    branch: str,
) -> dict[str, Any]:
    arrival_path = run_dir / "rollback-download-arrival.json"
    if not os.path.lexists(arrival_path):
        raise T2F2Error("stock rollback requires a durable bound Download arrival")
    arrival = _validate_rollback_arrival(
        b0.read_json(arrival_path, "rollback Download arrival"),
        run_dir,
        prepared,
    )
    if (
        arrival["binding_sha256"] != prepared["binding_sha256"]
        or arrival["branch"] != branch
        or not b0.same_download_session(arrival["endpoint"], endpoint)
    ):
        raise T2F2Error("rollback Download arrival differs from dispatch input")
    return _transfer(run_dir, prepared, "rollback", endpoint)


def execute(run_dir: Path, approval: str) -> dict[str, Any]:
    require_active()
    prepared = read_prepared(run_dir, require_unexpired=True)
    validate_journal(run_dir, prepared)
    require_fresh_candidate_unclaimed()
    if approval != prepared["approval_token"]:
        raise T2F2Error("approval token does not match the prepared T2 binding")
    if os.path.lexists(run_dir / "approval.json"):
        raise T2F2Error("prepared T2 approval is already consumed")
    if digest(validate_host_closure()) != prepared["binding"]["closure_sha256"]:
        raise T2F2Error("T2 execution closure changed after preparation")
    b0.durable_json(
        run_dir / "approval.json",
        {
            "schema": "s20plus_g986n_twrp_t2_approval_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "approval_sha256": hashlib.sha256(approval.encode()).hexdigest(),
            "consumed": True,
            "at": utc_now(),
        },
    )
    preflight, serial = android_stock_recovery_health(
        run_dir,
        "execute-pre-download",
        prepared["binding"]["preflight"]["serial_sha256"],
    )
    if (
        preflight["boot_id_sha256"]
        != prepared["binding"]["preflight"]["boot_id_sha256"]
        or preflight["topology_sha256"]
        != prepared["binding"]["preflight"]["topology_sha256"]
    ):
        raise T2F2Error("prepared Android boot changed before candidate Download")
    require_fresh_candidate_unclaimed()
    if digest(
        validate_host_closure(
            expected_serial_sha256=preflight["serial_sha256"]
        )
    ) != prepared["binding"]["closure_sha256"]:
        raise T2F2Error("T2 execution closure changed before candidate Download")
    baseline = prepared["binding"]["initial_download_baseline"]
    if digest(baseline) != digest(
        b0.read_json(
            run_dir / "candidate-download-baseline.json",
            "candidate Download baseline",
        )
    ):
        raise T2F2Error("candidate Download baseline changed")
    intent = {
        "schema": "s20plus_g986n_twrp_t2_download_intent_v1",
        "version": VERSION,
        "phase": "candidate",
        "binding_sha256": prepared["binding_sha256"],
        "source": preflight,
        "baseline_sha256": digest(baseline),
        "attempt": 1,
        "no_replay": True,
        "at": utc_now(),
    }
    b0.durable_json(run_dir / "candidate-download-intent.json", intent)
    transition = _adb_reboot_download(
        run_dir,
        serial,
        "candidate-download",
        phase="candidate",
        binding_sha256=prepared["binding_sha256"],
    )
    b0.durable_json(run_dir / "candidate-download-result.json", transition)
    arrival = b0.wait_download(baseline)
    if arrival is None:
        return {
            "verdict": "PRE_CANDIDATE_DOWNLOAD_RETURN_REQUIRED",
            "run_id": _run_id(run_dir),
            "candidate_attempts": 0,
            "candidate_replay": False,
            "instruction": "Return the attended S20+ to Android without a payload, then use abort-pre-candidate.",
        }
    b0.durable_json(run_dir / "candidate-download-arrival.json", arrival)
    _candidate_claim(run_dir, prepared)
    endpoint = arrival["endpoint"]
    candidate = _transfer(run_dir, prepared, "candidate", endpoint)
    if candidate["classification"] == "odin_transfer_completed":
        _publish_recovery_boot_intent(run_dir, prepared, candidate)
        return {
            "verdict": "CANDIDATE_TRANSFERRED_AWAITING_DIRECT_RECOVERY_BOOT",
            "run_id": _run_id(run_dir),
            "candidate_replay": False,
            "instruction": DIRECT_RECOVERY_INSTRUCTION,
        }
    try:
        current = b0.identify_download()
        if not b0.same_download_session(current, endpoint):
            raise T2F2Error("post-candidate Download endpoint differs from the bound session")
        devices, listing_sha256 = b0.enumerate_download()
        if devices != [current["device"]]:
            raise T2F2Error("post-candidate Download listing differs")
        b0.durable_json(
            run_dir / "rollback-download-arrival.json",
            {
                "schema": "s20plus_g986n_twrp_t2_rollback_arrival_v1",
                "version": VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "branch": "candidate-outcome-unproved-already-download",
                "endpoint": current,
                "arrival_listing_sha256": listing_sha256,
                "baseline_sha256": digest(baseline),
                "physical_arm_sha256": None,
                "confirmation_sha256": None,
                "at": utc_now(),
            },
        )
    except Exception:
        return {
            "verdict": "CANDIDATE_UNPROVED_PHYSICAL_ROLLBACK_REQUIRED",
            "run_id": _run_id(run_dir),
            "candidate_replay": False,
        }
    rollback = _rollback_from_download(
        run_dir, prepared, current, "candidate-outcome-unproved-already-download"
    )
    return {
        "verdict": "CANDIDATE_UNPROVED_STOCK_ROLLBACK_ATTEMPTED",
        "run_id": _run_id(run_dir),
        "candidate_replay": False,
        "rollback": rollback["classification"],
    }


def abort_pre_candidate(run_dir: Path) -> dict[str, Any]:
    """Close only after a prepared/approved run returned without a candidate intent."""

    require_active()
    prepared = read_prepared(run_dir, require_unexpired=False)
    actual = validate_journal(run_dir, prepared)
    require_all_transfer_processes_quiescent(run_dir, prepared)
    forbidden = (
        "candidate-intent.json",
        "candidate-result.json",
        "recovery-boot-intent.json",
        "rollback-intent.json",
        "rollback-result.json",
    )
    if any(os.path.lexists(run_dir / name) for name in forbidden):
        raise T2F2Error("pre-candidate abort is unavailable after a transfer intent")
    claim_consumed = os.path.lexists(candidate_claim_path())
    if claim_consumed:
        validate_candidate_claim(
            b0.read_json(candidate_claim_path(), "global candidate claim"),
            run_dir,
            prepared,
        )
    health, _serial = android_stock_recovery_health(
        run_dir,
        "pre-candidate-abort",
        prepared["binding"]["preflight"]["serial_sha256"],
    )
    if health["boot_id_sha256"] == prepared["binding"]["preflight"]["boot_id_sha256"]:
        raise T2F2Error("pre-candidate abort requires a later Android boot")
    terminal = {
        "schema": "s20plus_g986n_twrp_t2_pre_candidate_abort_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "verdict": (
            "ABORTED_AFTER_CANDIDATE_CLAIM_NO_TRANSFER_STOCK_RECOVERY_HEALTHY"
            if claim_consumed
            else "ABORTED_PRE_CANDIDATE_STOCK_RECOVERY_HEALTHY"
        ),
        "global_candidate_claim_consumed": claim_consumed,
        "candidate_attempts": 0,
        "rollback_attempts": 0,
        "partition_transfer_attempts": 0,
        "candidate_replay_permitted": False,
        "final_health": health,
        "at": utc_now(),
    }
    b0.durable_json(run_dir / "terminal.json", terminal)
    validate_journal(run_dir, prepared)
    release_guard(run_dir)
    return terminal


def _recovery_observation(run_dir: Path, prepared: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    if os.path.lexists(run_dir / "candidate-observation-intent.json"):
        raise T2F2Error("candidate recovery observation is already consumed")
    b0.durable_json(
        run_dir / "candidate-observation-intent.json",
        {
            "schema": "s20plus_g986n_twrp_t2_observation_intent_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "attempt": 1,
            "no_replay": True,
            "at": utc_now(),
        },
    )
    expected_serial = prepared["binding"]["preflight"]["serial_sha256"]
    deadline = time.monotonic() + RECOVERY_WAIT_SECONDS
    def no_proof(reason: str) -> tuple[dict[str, Any], None]:
        return {
            "schema": "s20plus_g986n_twrp_t2_observation_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "claim_verdict": "NO_PROOF",
            "reason": reason,
            "at": utc_now(),
        }, None

    while time.monotonic() < deadline:
        try:
            rows = b0.adb_inventory()
        except Exception as exc:
            return no_proof(
                "adb-inventory-malformed:"
                + hashlib.sha256(str(exc).encode()).hexdigest()
            )
        expected_rows = tuple(
            row
            for row in rows
            if hashlib.sha256(row["serial"].encode()).hexdigest() == expected_serial
        )
        if len(expected_rows) > 1:
            return no_proof("prepared-serial-ambiguous")
        if not expected_rows:
            time.sleep(2)
            continue
        row = expected_rows[0]
        if row["state"] != "recovery":
            return no_proof("prepared-serial-state-mismatch")
        try:
            serial = row["serial"]
            devpath = b0.adb_devpath(serial)
            if hashlib.sha256(devpath.encode()).hexdigest() != prepared["binding"]["preflight"]["topology_sha256"]:
                raise T2F2Error("recovery ADB topology differs")
            handle, stdout, stderr = _capture(
                run_dir,
                "candidate-recovery-observer",
                [str(b0.ADB), "-s", serial, "exec-out", "sh", "-c", h0.RECOVERY_SHELL_ARGUMENT],
                timeout=h0.PROPOSED_RECOVERY_OBSERVER_TIMEOUT_SECONDS,
                maximum=h0.MAX_RECOVERY_OBSERVER_BYTES,
            )
            values = h0.parse_recovery_observation((handle.returncode, stdout, stderr))
            final = b0.adb_inventory()
            final_rows = tuple(
                candidate
                for candidate in final
                if hashlib.sha256(candidate["serial"].encode()).hexdigest()
                == expected_serial
            )
            if len(final_rows) != 1 or final_rows[0]["state"] != "recovery":
                raise T2F2Error("TWRP ADB identity or state changed")
            final_row = final_rows[0]
            final_devpath = b0.adb_devpath(final_row["serial"])
            if (
                b0.sanitized_inventory(final) != b0.sanitized_inventory(rows)
                or final_devpath != devpath
            ):
                raise T2F2Error("recovery ADB inventory or topology changed")
            boot_id_sha256 = hashlib.sha256(values["boot_id"].encode()).hexdigest()
            if boot_id_sha256 == prepared["binding"]["preflight"]["boot_id_sha256"]:
                raise T2F2Error("recovery reused the prepared Android boot ID")
            return {
                "schema": "s20plus_g986n_twrp_t2_observation_v1",
                "version": VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "claim_verdict": "PROVED",
                "serial_sha256": expected_serial,
                "topology_sha256": hashlib.sha256(devpath.encode()).hexdigest(),
                "boot_id_sha256": boot_id_sha256,
                "values": {key: value for key, value in values.items() if key != "boot_id"},
                "capture": _capture_receipt(handle),
                "at": utc_now(),
            }, serial
        except Exception as exc:
            return no_proof(
                type(exc).__name__ + ":" + hashlib.sha256(str(exc).encode()).hexdigest()
            )
    return no_proof("bounded-recovery-observer-timeout")


def _automatic_rollback_download(
    run_dir: Path, prepared: dict[str, Any], serial: str, observation: dict[str, Any]
) -> dict[str, Any] | None:
    baseline_path = run_dir / "rollback-download-baseline.json"
    if os.path.lexists(baseline_path):
        baseline = _validate_baseline(
            b0.read_json(baseline_path, "rollback Download baseline"),
            "rollback Download baseline",
        )
    else:
        baseline = b0.download_baseline()
        b0.durable_json(baseline_path, baseline)
    intent = {
        "schema": "s20plus_g986n_twrp_t2_rollback_download_intent_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "source": "proved-recovery-adb",
        "source_boot_id_sha256": observation["boot_id_sha256"],
        "baseline_sha256": digest(baseline),
        "attempt": 1,
        "no_replay": True,
        "at": utc_now(),
    }
    b0.durable_json(run_dir / "rollback-download-intent.json", intent)
    result = _adb_reboot_download(
        run_dir,
        serial,
        "rollback-download",
        phase="rollback",
        binding_sha256=prepared["binding_sha256"],
    )
    b0.durable_json(run_dir / "rollback-download-result.json", result)
    arrival = b0.wait_download(baseline)
    if arrival is None:
        return None
    b0.durable_json(
        run_dir / "rollback-download-arrival.json",
        {
            "schema": "s20plus_g986n_twrp_t2_rollback_arrival_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "branch": "automatic-recovery-adb",
            "endpoint": arrival["endpoint"],
            "arrival_listing_sha256": arrival["arrival_listing_sha256"],
            "baseline_sha256": digest(baseline),
            "physical_arm_sha256": None,
            "confirmation_sha256": None,
            "at": utc_now(),
        },
    )
    return arrival["endpoint"]


def observe_recovery(run_dir: Path) -> dict[str, Any]:
    require_active()
    prepared = read_prepared(run_dir, require_unexpired=False)
    validate_journal(run_dir, prepared)
    require_all_transfer_processes_quiescent(run_dir, prepared)
    if (
        os.path.lexists(run_dir / "candidate-intent.json")
        and not os.path.lexists(run_dir / "candidate-result.json")
    ):
        recover_transfer_result(run_dir, prepared, "candidate")
    validate_journal(run_dir, prepared)
    result = _validate_transfer_result_record(
        run_dir,
        b0.read_json(run_dir / "candidate-result.json", "candidate result"),
        "candidate",
        prepared,
    )
    if result["classification"] != "odin_transfer_completed":
        raise T2F2Error("only a completed candidate may enter recovery observation")
    b0.read_json(run_dir / "recovery-boot-intent.json", "recovery boot intent")
    observation, serial = _recovery_observation(run_dir, prepared)
    _validate_observation(run_dir, observation, prepared)
    b0.durable_json(run_dir / "candidate-observation.json", observation)
    if serial is None:
        return {
            "verdict": "NO_PROOF_T2_PHYSICAL_ROLLBACK_REQUIRED",
            "run_id": _run_id(run_dir),
            "candidate_replay": False,
        }
    if validate_namespace(run_dir) & PHYSICAL_ROLLBACK_NODES:
        return _pending(
            run_dir,
            prepared,
            "PROVED_T2_PHYSICAL_ROLLBACK_ALREADY_ARMED",
        )
    return retain_proved_twrp(run_dir, prepared, observation)


def retain_proved_twrp(
    run_dir: Path, prepared: dict[str, Any], observation: dict[str, Any]
) -> dict[str, Any]:
    """Close successfully with the proved TWRP candidate intentionally retained."""

    if observation.get("claim_verdict") != "PROVED":
        raise T2F2Error("only a proved TWRP observation may be retained")
    actual = validate_namespace(run_dir)
    if actual & PHYSICAL_ROLLBACK_NODES:
        raise T2F2Error("an armed physical rollback forbids TWRP retention")
    candidate = _validate_transfer_result_record(
        run_dir,
        b0.read_json(run_dir / "candidate-result.json", "candidate result"),
        "candidate",
        prepared,
    )
    if candidate["classification"] != "odin_transfer_completed":
        raise T2F2Error("unproved candidate transfer cannot be retained")
    terminal = {
        "schema": "s20plus_g986n_twrp_t2_retained_terminal_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "verdict": "PROVED_T2_RECOVERY_RETAINED",
        "candidate_claim": "PROVED",
        "candidate_attempts": 1,
        "rollback_attempts": 0,
        "candidate_replay_permitted": False,
        "candidate_retained": True,
        "stock_rollback": dict(prepared["binding"]["rollback"]),
        "recovery_observation": observation,
        "partition_transfer_attempts": 1,
        "candidate_transfer_proved": True,
        "proved_recovery_partition_transfers": 1,
        "all_other_partition_transfers": 0,
        "s22plus_commands": 0,
        "a90_commands": 0,
        "other_target_commands": 0,
        "at": utc_now(),
    }
    b0.durable_json(run_dir / "terminal.json", terminal)
    validate_journal(run_dir, prepared)
    release_guard(run_dir)
    return terminal


def arm_physical_rollback(run_dir: Path) -> dict[str, Any]:
    require_active()
    prepared = read_prepared(run_dir, require_unexpired=False)
    validate_journal(run_dir, prepared)
    require_all_transfer_processes_quiescent(run_dir, prepared)
    if (
        os.path.lexists(run_dir / "candidate-intent.json")
        and not os.path.lexists(run_dir / "candidate-result.json")
    ):
        recover_transfer_result(run_dir, prepared, "candidate")
    validate_journal(run_dir, prepared)
    if os.path.lexists(run_dir / "candidate-observation.json"):
        observation = _validate_observation(
            run_dir,
            b0.read_json(run_dir / "candidate-observation.json", "observation"),
            prepared,
        )
        if observation["claim_verdict"] == "PROVED":
            raise T2F2Error("proved TWRP cannot arm a competing physical rollback")
    if os.path.lexists(run_dir / "rollback-intent.json"):
        raise T2F2Error("stock recovery rollback is already consumed")
    if not os.path.lexists(run_dir / "candidate-intent.json"):
        raise T2F2Error("physical stock rollback requires a consumed candidate intent")
    path = run_dir / "physical-rollback-arm.json"
    if os.path.lexists(path):
        raise T2F2Error("physical rollback arm is already consumed")
    if os.path.lexists(run_dir / "rollback-download-arrival.json"):
        raise T2F2Error("rollback Download arrival is already bound")
    devices, listing_sha256 = b0.enumerate_download()
    if len(devices) > 1:
        raise T2F2Error("physical rollback baseline is ambiguous")
    baseline: dict[str, Any] | None
    existing_endpoint: dict[str, Any] | None
    if not devices:
        baseline = b0.download_baseline()
        listing_sha256 = baseline["listing_sha256"]
        existing_endpoint = None
        mode = "empty-baseline-physical-entry"
    else:
        existing_endpoint = b0.identify_download()
        candidate_arrival = b0.read_json(
            run_dir / "candidate-download-arrival.json", "candidate Download arrival"
        )
        if (
            candidate_arrival.get("endpoint") is None
            or not b0.same_download_session(
                existing_endpoint, candidate_arrival["endpoint"]
            )
        ):
            raise T2F2Error("existing Download endpoint is not the candidate session")
        baseline = None
        mode = "already-download-bound-session"
    core = {
        "schema": "s20plus_g986n_twrp_t2_physical_arm_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "mode": mode,
        "baseline": baseline,
        "existing_endpoint": existing_endpoint,
        "initial_listing_sha256": listing_sha256,
        "expires_unix": int(time.time()) + PHYSICAL_LIFETIME_SECONDS,
        "action": "attended-physical-entry-to-download-for-stock-recovery-only",
        "attempt": 1,
        "no_replay": True,
    }
    token = PHYSICAL_PREFIX + digest(core)
    b0.durable_json(path, {**core, "confirmation_token": token, "at": utc_now()})
    return {
        "verdict": "PHYSICAL_STOCK_RECOVERY_ROLLBACK_ARMED",
        "run_id": _run_id(run_dir),
        "confirmation_token": token,
        "expires_unix": core["expires_unix"],
    }


def _publish_physical_observation_intent(
    run_dir: Path,
    prepared: dict[str, Any],
    arm: dict[str, Any],
    kind: str,
) -> dict[str, Any]:
    stem = "physical-observation" if kind == "initial" else "physical-resume-observation"
    path = run_dir / f"{stem}-intent.json"
    if os.path.lexists(path):
        record = _validate_physical_observation_record(
            run_dir, prepared, arm, kind
        )
        if record is None or record.get("schema") != (
            "s20plus_g986n_twrp_t2_physical_observation_intent_v1"
        ):
            raise T2F2Error(f"physical {kind} observation is already closed")
        return record
    value = {
        "schema": "s20plus_g986n_twrp_t2_physical_observation_intent_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "kind": kind,
        "physical_arm_sha256": digest(arm),
        "confirmation_sha256": _physical_confirmation_sha256(arm),
        "expires_unix": arm["expires_unix"],
        "attempt": 1,
        "no_replay": True,
        "at": utc_now(),
    }
    b0.durable_json(path, value)
    return value


def _publish_physical_observation_miss(
    run_dir: Path,
    prepared: dict[str, Any],
    intent: dict[str, Any],
    kind: str,
    reason: str,
) -> None:
    stem = "physical-observation" if kind == "initial" else "physical-resume-observation"
    b0.durable_json(
        run_dir / f"{stem}-miss.json",
        {
            "schema": "s20plus_g986n_twrp_t2_physical_observation_miss_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "kind": kind,
            "observation_intent_sha256": digest(intent),
            "reason": reason,
            "replay_permitted": False,
            "at": utc_now(),
        },
    )


def _physical_arrival_record(
    prepared: dict[str, Any],
    arm: dict[str, Any],
    endpoint: dict[str, Any],
    listing_sha256: str,
) -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_twrp_t2_rollback_arrival_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "branch": arm["mode"],
        "endpoint": endpoint,
        "arrival_listing_sha256": listing_sha256,
        "baseline_sha256": (
            None if arm["baseline"] is None else digest(arm["baseline"])
        ),
        "physical_arm_sha256": digest(arm),
        "confirmation_sha256": _physical_confirmation_sha256(arm),
        "at": utc_now(),
    }


def _initial_physical_observation(
    run_dir: Path, prepared: dict[str, Any], arm: dict[str, Any]
) -> dict[str, Any] | None:
    intent = _publish_physical_observation_intent(
        run_dir, prepared, arm, "initial"
    )
    remaining = arm["expires_unix"] - int(time.time())
    if remaining <= 0:
        _publish_physical_observation_miss(
            run_dir, prepared, intent, "initial", "expired-before-observation"
        )
        return None
    if arm["mode"] == "empty-baseline-physical-entry":
        try:
            arrival = b0.wait_download(
                _validate_baseline(arm["baseline"], "physical rollback baseline"),
                timeout=min(180, remaining),
            )
        except Exception:
            _publish_physical_observation_miss(
                run_dir,
                prepared,
                intent,
                "initial",
                "ambiguous-download-listing",
            )
            raise
        if arrival is None:
            _publish_physical_observation_miss(
                run_dir,
                prepared,
                intent,
                "initial",
                "bounded-observation-no-arrival",
            )
            return None
        try:
            devices, listing_sha256 = b0.enumerate_download()
            endpoint = b0.identify_download()
        except Exception:
            _publish_physical_observation_miss(
                run_dir,
                prepared,
                intent,
                "initial",
                "listing-identification-mismatch",
            )
            raise
        if devices != [endpoint["device"]]:
            _publish_physical_observation_miss(
                run_dir,
                prepared,
                intent,
                "initial",
                "listing-identification-mismatch",
            )
            return None
        if not b0.same_download_session(endpoint, arrival["endpoint"]):
            _publish_physical_observation_miss(
                run_dir,
                prepared,
                intent,
                "initial",
                "listing-identification-mismatch",
            )
            return None
    else:
        try:
            devices, listing_sha256 = b0.enumerate_download()
        except Exception:
            _publish_physical_observation_miss(
                run_dir,
                prepared,
                intent,
                "initial",
                "ambiguous-download-listing",
            )
            raise
        if len(devices) != 1:
            _publish_physical_observation_miss(
                run_dir,
                prepared,
                intent,
                "initial",
                "ambiguous-download-listing",
            )
            return None
        try:
            endpoint = b0.identify_download()
        except Exception:
            _publish_physical_observation_miss(
                run_dir,
                prepared,
                intent,
                "initial",
                "listing-identification-mismatch",
            )
            raise
        if devices != [endpoint["device"]] or not b0.same_download_session(
            endpoint, arm["existing_endpoint"]
        ):
            _publish_physical_observation_miss(
                run_dir,
                prepared,
                intent,
                "initial",
                "listing-identification-mismatch",
            )
            return None
    if int(time.time()) > arm["expires_unix"]:
        _publish_physical_observation_miss(
            run_dir, prepared, intent, "initial", "expired-before-observation"
        )
        return None
    record = _physical_arrival_record(
        prepared, arm, endpoint, listing_sha256
    )
    b0.durable_json(run_dir / "rollback-download-arrival.json", record)
    return endpoint


def confirm_physical_rollback(
    run_dir: Path, confirmation: str
) -> dict[str, Any]:
    require_active()
    prepared = read_prepared(run_dir, require_unexpired=False)
    validate_journal(run_dir, prepared)
    require_all_transfer_processes_quiescent(run_dir, prepared)
    arm = _validate_physical_arm(
        b0.read_json(run_dir / "physical-rollback-arm.json", "physical rollback arm"),
        prepared,
    )
    if (
        arm["confirmation_token"] != confirmation
        or not confirmation.startswith(PHYSICAL_PREFIX)
        or int(time.time()) > arm["expires_unix"]
    ):
        raise T2F2Error("physical rollback confirmation differs or expired")
    if os.path.lexists(run_dir / "physical-rollback-confirmation.json"):
        raise T2F2Error("physical rollback confirmation is consumed; use --resume")
    b0.durable_json(
        run_dir / "physical-rollback-confirmation.json",
        {
            "schema": "s20plus_g986n_twrp_t2_physical_confirmation_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "confirmation_sha256": hashlib.sha256(confirmation.encode()).hexdigest(),
            "consumed": True,
            "at": utc_now(),
        },
    )
    endpoint = _initial_physical_observation(run_dir, prepared, arm)
    if endpoint is None:
        return {
            "verdict": "PHYSICAL_STOCK_RECOVERY_DOWNLOAD_OBSERVATION_MISSED",
            "run_id": _run_id(run_dir),
            "rollback": "not-attempted",
        }
    rollback = _rollback_from_download(run_dir, prepared, endpoint, arm["mode"])
    return {
        "verdict": "PHYSICAL_STOCK_RECOVERY_ROLLBACK_ATTEMPTED",
        "run_id": _run_id(run_dir),
        "rollback": rollback["classification"],
    }


def _wait_android_health(
    run_dir: Path, prepared: dict[str, Any]
) -> dict[str, Any]:
    deadline = time.monotonic() + ANDROID_WAIT_SECONDS
    expected_serial = prepared["binding"]["preflight"]["serial_sha256"]
    while time.monotonic() < deadline:
        try:
            rows = b0.adb_inventory()
        except Exception as exc:
            raise T2F2Error("final ADB inventory is malformed") from exc
        matches = b0.target_adb_rows(rows)
        expected_rows = tuple(
            row
            for row in rows
            if hashlib.sha256(row["serial"].encode()).hexdigest() == expected_serial
        )
        if len(matches) > 1:
            raise T2F2Error("final exact-target ADB inventory is ambiguous")
        if not matches:
            if expected_rows:
                raise T2F2Error(
                    "final prepared serial is present without exact target metadata"
                )
            time.sleep(3)
            continue
        row = matches[0]
        if (
            hashlib.sha256(row["serial"].encode()).hexdigest() != expected_serial
            or row["state"] != "device"
            or not b0.EXPECTED_ADB_METADATA <= row["metadata"]
        ):
            raise T2F2Error("final exact target state or identity differs")
        break
    else:
        raise T2F2Error("final exact Android arrival timed out")
    health, _serial = android_stock_recovery_health(
        run_dir,
        "final",
        expected_serial,
    )
    return health


def _publish_recovery_boot_intent(
    run_dir: Path, prepared: dict[str, Any], candidate: dict[str, Any]
) -> None:
    if os.path.lexists(run_dir / "recovery-boot-intent.json"):
        return
    if candidate["classification"] != "odin_transfer_completed":
        raise T2F2Error("unproved candidate cannot gain a recovery boot intent")
    b0.durable_json(
        run_dir / "recovery-boot-intent.json",
        {
            "schema": "s20plus_g986n_twrp_t2_recovery_boot_intent_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "candidate_result_sha256": digest(candidate),
            "action": "attended-direct-recovery-key-chord-once",
            "attempt": 1,
            "no_replay": True,
            "at": utc_now(),
        },
    )


def _bind_current_candidate_download(
    run_dir: Path, prepared: dict[str, Any]
) -> dict[str, Any] | None:
    devices, listing_sha256 = b0.enumerate_download()
    if len(devices) > 1:
        raise T2F2Error("candidate Download resume state is ambiguous")
    if not devices:
        return None
    endpoint = b0.identify_download()
    if endpoint["device"] != devices[0]:
        raise T2F2Error("candidate Download listing changed")
    arrival = {
        "endpoint": endpoint,
        "baseline_sha256": b0.digest(
            prepared["binding"]["initial_download_baseline"]
        ),
        "arrival_listing_sha256": listing_sha256,
        "at": utc_now(),
    }
    _validate_arrival(arrival, prepared, "resumed candidate arrival")
    b0.durable_json(run_dir / "candidate-download-arrival.json", arrival)
    return endpoint


def _bind_current_rollback_download(
    run_dir: Path, prepared: dict[str, Any], branch: str
) -> dict[str, Any] | None:
    devices, listing_sha256 = b0.enumerate_download()
    if len(devices) > 1:
        raise T2F2Error("rollback Download resume state is ambiguous")
    if not devices:
        return None
    endpoint = b0.identify_download()
    if endpoint["device"] != devices[0]:
        raise T2F2Error("rollback Download listing changed")
    if branch == "automatic-recovery-adb":
        baseline = _validate_baseline(
            b0.read_json(run_dir / "rollback-download-baseline.json", "rollback baseline"),
            "rollback baseline",
        )
        physical_arm_sha256 = None
        confirmation_sha256 = None
    elif branch == "candidate-outcome-unproved-already-download":
        baseline = prepared["binding"]["initial_download_baseline"]
        physical_arm_sha256 = None
        confirmation_sha256 = None
    else:
        raise T2F2Error("rollback resume branch differs")
    arrival = {
        "schema": "s20plus_g986n_twrp_t2_rollback_arrival_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "branch": branch,
        "endpoint": endpoint,
        "arrival_listing_sha256": listing_sha256,
        "baseline_sha256": digest(baseline),
        "physical_arm_sha256": physical_arm_sha256,
        "confirmation_sha256": confirmation_sha256,
        "at": utc_now(),
    }
    _validate_rollback_arrival(arrival, run_dir, prepared)
    b0.durable_json(run_dir / "rollback-download-arrival.json", arrival)
    return endpoint


def _resume_physical_confirmation(
    run_dir: Path, prepared: dict[str, Any]
) -> dict[str, Any] | None:
    arm = _validate_physical_arm(
        b0.read_json(run_dir / "physical-rollback-arm.json", "physical arm"),
        prepared,
    )
    confirmation = b0.read_json(
        run_dir / "physical-rollback-confirmation.json", "physical confirmation"
    )
    expected_confirmation = hashlib.sha256(
        arm["confirmation_token"].encode()
    ).hexdigest()
    if (
        confirmation.get("schema")
        != "s20plus_g986n_twrp_t2_physical_confirmation_v1"
        or confirmation.get("version") != VERSION
        or confirmation.get("binding_sha256") != prepared["binding_sha256"]
        or confirmation.get("confirmation_sha256") != expected_confirmation
        or confirmation.get("consumed") is not True
    ):
        raise T2F2Error("physical confirmation differs")
    if os.path.lexists(run_dir / "rollback-download-arrival.json"):
        arrival = _validate_rollback_arrival(
            b0.read_json(run_dir / "rollback-download-arrival.json", "rollback arrival"),
            run_dir,
            prepared,
        )
        return arrival["endpoint"]
    initial = _validate_physical_observation_record(
        run_dir, prepared, arm, "initial"
    )
    if (
        initial is not None
        and initial.get("schema")
        == "s20plus_g986n_twrp_t2_physical_observation_miss_v1"
    ):
        return None
    resumed = _validate_physical_observation_record(
        run_dir, prepared, arm, "resume"
    )
    if resumed is not None:
        if resumed.get("schema") == (
            "s20plus_g986n_twrp_t2_physical_observation_miss_v1"
        ):
            return None
        _publish_physical_observation_miss(
            run_dir,
            prepared,
            resumed,
            "resume",
            "resume-observation-intent-consumed-result-absent",
        )
        return None
    resume_intent = _publish_physical_observation_intent(
        run_dir, prepared, arm, "resume"
    )
    if int(time.time()) > arm["expires_unix"]:
        _publish_physical_observation_miss(
            run_dir,
            prepared,
            resume_intent,
            "resume",
            "expired-before-observation",
        )
        return None
    try:
        devices, listing_sha256 = b0.enumerate_download()
    except Exception:
        _publish_physical_observation_miss(
            run_dir,
            prepared,
            resume_intent,
            "resume",
            "ambiguous-download-listing",
        )
        raise
    if len(devices) > 1:
        _publish_physical_observation_miss(
            run_dir,
            prepared,
            resume_intent,
            "resume",
            "ambiguous-download-listing",
        )
        return None
    if not devices:
        _publish_physical_observation_miss(
            run_dir,
            prepared,
            resume_intent,
            "resume",
            "bounded-observation-no-arrival",
        )
        return None
    try:
        endpoint = b0.identify_download()
    except Exception:
        _publish_physical_observation_miss(
            run_dir,
            prepared,
            resume_intent,
            "resume",
            "listing-identification-mismatch",
        )
        raise
    if devices != [endpoint["device"]] or (
        arm["mode"] == "already-download-bound-session"
        and not b0.same_download_session(endpoint, arm["existing_endpoint"])
    ):
        _publish_physical_observation_miss(
            run_dir,
            prepared,
            resume_intent,
            "resume",
            "listing-identification-mismatch",
        )
        return None
    if int(time.time()) > arm["expires_unix"]:
        _publish_physical_observation_miss(
            run_dir,
            prepared,
            resume_intent,
            "resume",
            "expired-before-observation",
        )
        return None
    arrival = _physical_arrival_record(
        prepared, arm, endpoint, listing_sha256
    )
    _validate_rollback_arrival(arrival, run_dir, prepared)
    b0.durable_json(run_dir / "rollback-download-arrival.json", arrival)
    return endpoint


def _pending(run_dir: Path, prepared: dict[str, Any], verdict: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_twrp_t2_pending_v1",
        "version": VERSION,
        "run_id": _run_id(run_dir),
        "binding_sha256": prepared["binding_sha256"],
        "verdict": verdict,
        "candidate_replay": False,
        "rollback_replay": False,
        **extra,
    }


def resume_run(run_dir: Path) -> dict[str, Any]:
    """Recover only from durable state; no candidate or rollback effect replays."""

    require_active()
    terminal_exists = os.path.lexists(run_dir / "terminal.json")
    prepared = read_prepared(
        run_dir,
        require_unexpired=False,
        require_current_guard=not terminal_exists,
    )
    actual = validate_journal(run_dir, prepared)
    if terminal_exists:
        terminal = _validate_terminal(run_dir, prepared, actual)
        if os.path.lexists(SHARED_GUARD):
            release_guard(run_dir)
        return terminal
    require_all_transfer_processes_quiescent(run_dir, prepared)
    actual = validate_journal(run_dir, prepared)
    if "approval.json" not in actual:
        return _pending(
            run_dir, prepared, "PREPARED_AWAITING_APPROVAL_OR_ABORT"
        )
    if "candidate-download-intent.json" not in actual:
        return _pending(
            run_dir,
            prepared,
            "APPROVAL_CONSUMED_PRE_EFFECT_ABORT_REQUIRED",
        )
    if "candidate-download-result.json" not in actual:
        recover_reboot_result(run_dir, prepared, "candidate")
    if "candidate-download-arrival.json" not in actual:
        endpoint = _bind_current_candidate_download(run_dir, prepared)
        if endpoint is None:
            return _pending(
                run_dir,
                prepared,
                "PRE_CANDIDATE_DOWNLOAD_UNPROVED_RETURN_ANDROID_AND_ABORT",
            )
    arrival = _validate_arrival(
        b0.read_json(run_dir / "candidate-download-arrival.json", "candidate arrival"),
        prepared,
        "candidate arrival",
    )
    claim_path = candidate_claim_path()
    if not os.path.lexists(claim_path):
        _candidate_claim(run_dir, prepared)
    else:
        validate_candidate_claim(
            b0.read_json(claim_path, "global candidate claim"), run_dir, prepared
        )
    if not os.path.lexists(run_dir / "candidate-intent.json"):
        try:
            _same_endpoint(arrival["endpoint"])
        except Exception:
            return _pending(
                run_dir,
                prepared,
                "GLOBAL_CANDIDATE_CLAIM_CONSUMED_NO_TRANSFER_RETURN_ANDROID_AND_ABORT",
            )
        candidate = _transfer(
            run_dir, prepared, "candidate", arrival["endpoint"]
        )
    elif not os.path.lexists(run_dir / "candidate-result.json"):
        candidate = recover_transfer_result(run_dir, prepared, "candidate")
    else:
        candidate = _validate_transfer_result_record(
            run_dir,
            b0.read_json(run_dir / "candidate-result.json", "candidate result"),
            "candidate",
            prepared,
        )
    if candidate["classification"] != "odin_transfer_completed":
        if (
            not os.path.lexists(run_dir / "rollback-download-arrival.json")
            and not os.path.lexists(run_dir / "physical-rollback-arm.json")
        ):
            endpoint = _bind_current_rollback_download(
                run_dir,
                prepared,
                "candidate-outcome-unproved-already-download",
            )
            if endpoint is None:
                return _pending(
                    run_dir, prepared, "CANDIDATE_UNPROVED_PHYSICAL_ROLLBACK_REQUIRED"
                )
    else:
        _publish_recovery_boot_intent(run_dir, prepared, candidate)
        if not os.path.lexists(run_dir / "candidate-observation.json"):
            if os.path.lexists(run_dir / "candidate-observation-intent.json"):
                observation = {
                    "schema": "s20plus_g986n_twrp_t2_observation_v1",
                    "version": VERSION,
                    "binding_sha256": prepared["binding_sha256"],
                    "claim_verdict": "NO_PROOF",
                    "reason": "observation-intent-consumed-result-absent",
                    "at": utc_now(),
                }
                b0.durable_json(run_dir / "candidate-observation.json", observation)
            else:
                return _pending(
                    run_dir,
                    prepared,
                    "DIRECT_RECOVERY_ACTION_AND_OBSERVATION_PENDING",
                    instruction=DIRECT_RECOVERY_INSTRUCTION,
                )
        observation = _validate_observation(
            run_dir,
            b0.read_json(run_dir / "candidate-observation.json", "observation"),
            prepared,
        )
        if observation["claim_verdict"] == "PROVED":
            if not (actual & PHYSICAL_ROLLBACK_NODES):
                return retain_proved_twrp(run_dir, prepared, observation)
        elif (
            not os.path.lexists(run_dir / "rollback-download-arrival.json")
            and not os.path.lexists(run_dir / "physical-rollback-arm.json")
        ):
            return _pending(
                run_dir, prepared, "NO_PROOF_T2_PHYSICAL_ROLLBACK_REQUIRED"
            )
    if os.path.lexists(run_dir / "physical-rollback-arm.json"):
        arm = _validate_physical_arm(
            b0.read_json(run_dir / "physical-rollback-arm.json", "physical arm"),
            prepared,
        )
        if not os.path.lexists(run_dir / "physical-rollback-confirmation.json"):
            return _pending(
                run_dir,
                prepared,
                "PHYSICAL_ROLLBACK_CONFIRMATION_PENDING",
                confirmation_token=arm["confirmation_token"],
            )
        if not os.path.lexists(run_dir / "rollback-download-arrival.json"):
            endpoint = _resume_physical_confirmation(run_dir, prepared)
            if endpoint is None:
                return _pending(
                    run_dir,
                    prepared,
                    "PHYSICAL_ROLLBACK_CONFIRMATION_CONSUMED_ARRIVAL_UNPROVED",
                )
    if not os.path.lexists(run_dir / "rollback-download-arrival.json"):
        return _pending(run_dir, prepared, "PHYSICAL_ROLLBACK_REQUIRED")
    rollback_arrival = _validate_rollback_arrival(
        b0.read_json(run_dir / "rollback-download-arrival.json", "rollback arrival"),
        run_dir,
        prepared,
    )
    if not os.path.lexists(run_dir / "rollback-intent.json"):
        rollback = _rollback_from_download(
            run_dir,
            prepared,
            rollback_arrival["endpoint"],
            rollback_arrival["branch"],
        )
    elif not os.path.lexists(run_dir / "rollback-result.json"):
        rollback = recover_transfer_result(run_dir, prepared, "rollback")
    else:
        rollback = _validate_transfer_result_record(
            run_dir,
            b0.read_json(run_dir / "rollback-result.json", "rollback result"),
            "rollback",
            prepared,
        )
    return finalize(run_dir)


def finalize(run_dir: Path) -> dict[str, Any]:
    require_active()
    terminal_exists = os.path.lexists(run_dir / "terminal.json")
    prepared = read_prepared(
        run_dir,
        require_unexpired=False,
        require_current_guard=not terminal_exists,
    )
    actual = validate_journal(run_dir, prepared)
    if terminal_exists:
        terminal = _validate_terminal(run_dir, prepared, actual)
        if os.path.lexists(SHARED_GUARD):
            release_guard(run_dir)
        return terminal
    require_all_transfer_processes_quiescent(run_dir, prepared)
    if not os.path.lexists(run_dir / "rollback-result.json"):
        recover_transfer_result(run_dir, prepared, "rollback")
    candidate = _validate_transfer_result_record(
        run_dir,
        b0.read_json(run_dir / "candidate-result.json", "candidate result"),
        "candidate",
        prepared,
    )
    rollback = _validate_transfer_result_record(
        run_dir,
        b0.read_json(run_dir / "rollback-result.json", "rollback result"),
        "rollback",
        prepared,
    )
    if os.path.lexists(run_dir / "final-health.json"):
        health = _validate_health(
            b0.read_json(run_dir / "final-health.json", "final health"),
            run_dir,
            "final health",
        )
    else:
        health = _wait_android_health(run_dir, prepared)
        _validate_health(health, run_dir, "final health")
        b0.durable_json(run_dir / "final-health.json", health)
    if health["boot_id_sha256"] == prepared["binding"]["preflight"]["boot_id_sha256"]:
        raise T2F2Error("final Android reused the prepared source boot ID")
    observation = (
        _validate_observation(
            run_dir,
            b0.read_json(run_dir / "candidate-observation.json", "candidate observation"),
            prepared,
        )
        if os.path.lexists(run_dir / "candidate-observation.json")
        else None
    )
    candidate_complete = candidate["classification"] == "odin_transfer_completed"
    rollback_complete = rollback["classification"] == "odin_transfer_completed"
    proved = (
        candidate_complete
        and rollback_complete
        and observation is not None
        and observation["claim_verdict"] == "PROVED"
        and len(
            {
                prepared["binding"]["preflight"]["boot_id_sha256"],
                observation["boot_id_sha256"],
                health["boot_id_sha256"],
            }
        )
        == 3
    )
    if proved:
        verdict = "PROVED_T2_RETURNED_STOCK_RECOVERY_HEALTHY"
    elif rollback_complete:
        verdict = "NO_PROOF_T2_RETURNED_STOCK_RECOVERY_HEALTHY"
    else:
        verdict = "NO_PROOF_T2_STOCK_RECOVERY_HEALTHY_TRANSFER_UNPROVED"
    terminal = {
        "schema": "s20plus_g986n_twrp_t2_terminal_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "verdict": verdict,
        "candidate_claim": (
            observation["claim_verdict"] if observation is not None else "NO_PROOF"
        ),
        "candidate_attempts": 1,
        "rollback_attempts": 1,
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
        "final_health": health,
        "final_stock_recovery_proved": True,
        "partition_transfer_attempts": 2,
        "candidate_transfer_proved": candidate_complete,
        "rollback_transfer_proved": rollback_complete,
        "proved_recovery_partition_transfers": (
            int(candidate_complete) + int(rollback_complete)
        ),
        "all_other_partition_transfers": 0,
        "s22plus_commands": 0,
        "a90_commands": 0,
        "other_target_commands": 0,
        "at": utc_now(),
    }
    b0.durable_json(run_dir / "terminal.json", terminal)
    validate_journal(run_dir, prepared)
    release_guard(run_dir)
    return terminal


def render_plan() -> dict[str, Any]:
    closure = validate_host_closure(enforce_self=False)
    return {
        "schema": PLAN_SCHEMA,
        "version": VERSION,
        "status": (
            "BINDING_ATTENDED_TWRP_T2_F2_ACTIVE"
            if T2_F2_ACTIVE
            else "DORMANT_REVIEW_PENDING_NOT_ACTIVE"
        ),
        "active": T2_F2_ACTIVE,
        "live_authority": T2_F2_ACTIVE,
        "target": dict(h0.EXPECTED_TARGET),
        "candidate": {
            "size": h0.CANDIDATE_AP_SIZE,
            "sha256": h0.CANDIDATE_AP_SHA256,
            "member": h0.AP_MEMBER_NAME,
        },
        "rollback": {
            "size": h0.ROLLBACK_AP_SIZE,
            "sha256": h0.ROLLBACK_AP_SHA256,
            "member": h0.AP_MEMBER_NAME,
        },
        "limits": {
            "candidate_recovery_transfer": 1,
            "stock_recovery_transfer": 1,
            "candidate_replay": False,
            "rollback_replay": False,
            "all_other_partition_transfers": 0,
            "format": False,
            "vbmeta": False,
            "misc": False,
        },
        "connected_modes": [
            "prepare", "execute", "observe-recovery",
            "abort-pre-candidate", "arm-physical-rollback",
            "confirm-physical-rollback", "resume", "finalize",
        ],
        "direct_recovery_instruction": DIRECT_RECOVERY_INSTRUCTION,
        "closure_sha256": digest(closure),
        "runner": self_receipt(enforce_reviewed=False),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Operate the exact S20+ TWRP T2 F2 owner"
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--render-plan", action="store_true")
    modes.add_argument("--validate-host", action="store_true")
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--observe-recovery", action="store_true")
    modes.add_argument("--abort-pre-candidate", action="store_true")
    modes.add_argument("--arm-physical-rollback", action="store_true")
    modes.add_argument("--confirm-physical-rollback", action="store_true")
    modes.add_argument("--resume", action="store_true")
    modes.add_argument("--finalize", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--approval")
    parser.add_argument("--confirmation")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.render_plan:
        print(json.dumps(render_plan(), sort_keys=True, indent=2))
        return 0
    if args.validate_host:
        print(json.dumps(validate_host_closure(enforce_self=False), sort_keys=True, indent=2))
        return 0
    if not T2_F2_ACTIVE:
        print("STOP_S20PLUS_G986N_TWRP_T2_F2_NOT_ACTIVE")
        return 2
    if args.prepare:
        if args.run_id or args.approval or args.confirmation:
            raise T2F2Error("prepare accepts no caller binding")
        result = prepare()
    else:
        if not args.run_id:
            raise T2F2Error("the allocated run ID is required")
        run_dir = resolve_run(args.run_id)
        if args.execute:
            if not args.approval or args.confirmation:
                raise T2F2Error("execute requires only the exact approval")
            result = execute(run_dir, args.approval)
        elif args.observe_recovery:
            if args.approval or args.confirmation:
                raise T2F2Error("observe-recovery accepts no token")
            result = observe_recovery(run_dir)
        elif args.abort_pre_candidate:
            if args.approval or args.confirmation:
                raise T2F2Error("abort-pre-candidate accepts no token")
            result = abort_pre_candidate(run_dir)
        elif args.arm_physical_rollback:
            if args.approval or args.confirmation:
                raise T2F2Error("arm accepts no token")
            result = arm_physical_rollback(run_dir)
        elif args.confirm_physical_rollback:
            if not args.confirmation or args.approval:
                raise T2F2Error("physical rollback requires only its confirmation")
            result = confirm_physical_rollback(run_dir, args.confirmation)
        elif args.finalize:
            if args.approval or args.confirmation:
                raise T2F2Error("finalize accepts no token")
            result = finalize(run_dir)
        elif args.resume:
            if args.approval or args.confirmation:
                raise T2F2Error("resume accepts no token")
            result = resume_run(run_dir)
        else:
            raise T2F2Error("unknown T2 operation")
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
