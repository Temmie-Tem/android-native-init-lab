#!/usr/bin/env python3
"""One-shot no-AP reboot recovery for the consumed R4W1-C2 parse failure."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import re
import selectors
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

import s22plus_fyg8_r4w1c2_measured_live_gate as measured
import s22plus_fyg8_r4w1c_connected_gate as connected
import s22plus_odin_transition_core as odin_core
import s22plus_boot_only_live_core as core


TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
SCRIPT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1c2_noap_reboot_recovery.py"
)
TEST_RELATIVE = Path("tests/test_s22plus_fyg8_r4w1c2_noap_reboot_recovery.py")
POLICY_DRAFT_RELATIVE = Path(
    "docs/operations/S22PLUS_FYG8_R4W1C2_NOAP_REBOOT_RECOVERY_EXCEPTION_DRAFT_2026-07-21.md"
)
POLICY_BEGIN = "BEGIN_S22PLUS_FYG8_R4W1C2_NOAP_REBOOT_RECOVERY_POLICY_V1"
POLICY_END = "END_S22PLUS_FYG8_R4W1C2_NOAP_REBOOT_RECOVERY_POLICY_V1"
POLICY_STATE = "S22PLUS_FYG8_R4W1C2_NOAP_REBOOT_RECOVERY_POLICY_STATE=ACTIVE"
OLD_POLICY_BEGIN = "BEGIN_S22PLUS_FYG8_R4W1C2_MEASURED_LIVE_POLICY_V1"
OLD_POLICY_END = "END_S22PLUS_FYG8_R4W1C2_MEASURED_LIVE_POLICY_V1"
OLD_POLICY_ACTIVE = "S22PLUS_FYG8_R4W1C2_MEASURED_LIVE_POLICY_STATE=ACTIVE"
OLD_POLICY_RETIRED = "S22PLUS_FYG8_R4W1C2_MEASURED_LIVE_POLICY_STATE=RETIRED"
EXPECTED_POLICY_TEMPLATE_SHA256 = (
    "9eab648aec876d5e229e35926927dcf06cea8d1ab70c034df312b7e1a064d7f9"
)
LIVE_ACK = "S22PLUS-FYG8-R4W1C2-NOAP-REBOOT-RECOVERY-LIVE"
PASS_VERDICT = "PASS_R4W1C2_NOAP_REBOOT_RECOVERY_EXACT_MAGISK_ANDROID"
FAIL_VERDICT = "FAIL_R4W1C2_NOAP_REBOOT_RECOVERY_REQUIRED"

INCIDENT_RUN = Path(
    "workspace/private/runs/s22plus-r4w1c2-measured-live-20260720T164444Z"
)
RECOVERY_RUN_ROOT = Path("workspace/private/runs")
RECOVERY_STATE = Path(
    "workspace/private/state/"
    "s22plus_fyg8_r4w1c2_noap_reboot_recovery_consumed.json"
)

EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
PARSE_FAILURE_STDOUT = b"Reboot into normal mode\nFail parse /proc/self/fd/7\n"
PARSE_FAILURE_SHA256 = hashlib.sha256(PARSE_FAILURE_STDOUT).hexdigest()
ODIN_SUCCESS_LINES = (
    "Reboot into normal mode",
    "Setup Connection",
    "initializeConnection",
    "Receive PIT Info",
    "success getpit",
    "Upload Binaries",
    "Close Connection",
)
MAX_ODIN_OUTPUT = 1024 * 1024
PHYSICAL_CONTINUITY_BASIS = (
    "operator-attested-original-r4w1c2-handset;same-cable-hub-host-port;"
    "screen-normal-samsung-download-at-live-ack;download-serial-absent;"
    "not-host-intrinsically-verifiable"
)
UTC_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z"
)

PINNED_FILES: dict[str, tuple[Path, int, str]] = {
    "consumed": (
        measured.CONSUMED_STATE,
        2680,
        "64d15cb2fab8dc7ea5ca0b569832cc15c32c7623e05cfbe6a60924cbf02ec477",
    ),
    "live_result": (
        INCIDENT_RUN / "result-live.json",
        108695,
        "74aa8f0a03b033299b2af5a6c97d9cba819ce671b04666549be3da45b38d9728",
    ),
    "recovery_result": (
        INCIDENT_RUN / "result-recovery-attempt-01.json",
        190297,
        "aabf8323dd4d78451c3378f968a2bb1900625a6705cba2122cb261b9aaab5456",
    ),
    "stock_intent": (
        INCIDENT_RUN / measured.STOCK_CLEANUP_INTENT_NAME,
        1290,
        "50d48adc1ad9710628d5282978ca8f984e2d1478192ccec2b75185628363f23c",
    ),
    "candidate_log": (
        INCIDENT_RUN / "odin-candidate.json",
        462,
        "84523c1d488f51c936a1d62fa832b0640e30f92d8544cb5c41e1dc70cfbc4757",
    ),
    "magisk_log": (
        INCIDENT_RUN / "odin-magisk-attempt-01.json",
        468,
        "12eef1ec931c2052196ca64d5930a23fc25cbfceb19530565b36eefadeadcc1d",
    ),
    "stock_log": (
        INCIDENT_RUN / "odin-stock-attempt-01.json",
        466,
        "175794cbe076165a41e171e6c5af8defb4c36158e651926af1871c44f810585d",
    ),
    "transaction": (
        INCIDENT_RUN / "transaction.jsonl",
        6971,
        "2811364fada46d840e8787f8947491688df1f3065d6be75e670b0a923561e97b",
    ),
    "recovery_timeline": (
        INCIDENT_RUN / "recovery-attempt-01-timeline.json",
        536,
        "48226674518c975f3d9d866834222e6f4217593cffb25b0e6700d6308c7df239",
    ),
}

DEPENDENCY_FILES: dict[str, tuple[Path, int, str]] = {
    "measured_helper": (
        measured.SCRIPT_RELATIVE,
        111396,
        "22cba55a924e9c56e5d245114357921ebefc73460a673e40e22c7ecf2e145172",
    ),
    "connected_helper": (
        connected.SCRIPT_RELATIVE,
        54734,
        "fa4e9b0a77032fbb8b17affb2ae985b80c990b6e4b07c0ee095328cfd80516b9",
    ),
    "odin_core": (
        connected.ODIN_CORE_RELATIVE,
        58423,
        "c9abb179158bb45039574465e743f1f5bee18f993cbddd2f0b40e9048d1ca6b3",
    ),
    "live_core": (
        connected.LIVE_CORE_RELATIVE,
        12524,
        "9bcade2532e77d538112836ebe9903bab832c1f2250151d3635260b6fd013725",
    ),
    "usbfs_identity": (
        measured.USBFS_IDENTITY_RELATIVE,
        18998,
        "2d1310e129670e89862826bcacc3886820c60f2691f342720927e8e13bddfe10",
    ),
    "transport": (
        connected.TRANSPORT_RELATIVE,
        35401,
        "f10a30735882bbd59453471fe901b1cef11fdf42bcf3560a8ae61b4af361c4f4",
    ),
    "m3_observable": (
        Path(
            "workspace/public/src/scripts/revalidation/"
            "s22plus_m3_observable_live_gate.py"
        ),
        24686,
        "1f093d78a110925440c98741399d8828201cce38265a5c941ac2f71b6c104305",
    ),
}

ABSOLUTE_DEPENDENCIES: dict[str, tuple[Path, int, str]] = {
    "birth_time_stat": (
        measured.STAT_BINARY,
        11352352,
        "48893b0fb21436b54619db80486e83ef39dfccaf1aefe83dfa00c02d6146e8c0",
    ),
    "odin": (
        connected.DEFAULT_ODIN,
        connected.EXPECTED_ODIN_SIZE,
        connected.EXPECTED_ODIN_SHA256,
    ),
}

FAILED_LOGS = {
    "candidate_log": ("r4w1c-candidate", connected.EXPECTED_CANDIDATE_AP_SHA256),
    "magisk_log": (
        "r4w1c-magisk-rollback",
        connected.EXPECTED_MAGISK_AP_SHA256,
    ),
    "stock_log": ("r4w1c-stock-cleanup", connected.EXPECTED_STOCK_AP_SHA256),
}


class RecoveryError(RuntimeError):
    pass


class BoundedOdinError(RecoveryError):
    def __init__(
        self,
        message: str,
        stdout: bytes,
        stderr: bytes,
        *,
        timed_out: bool = False,
        output_overflow: bool = False,
    ):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.timed_out = timed_out
        self.output_overflow = output_overflow


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def stable_bytes(path: Path, *, maximum: int = 4 * 1024 * 1024) -> bytes:
    try:
        return core.read_stable_file(path, maximum=maximum)
    except (OSError, core.LiveCoreError) as exc:
        raise RecoveryError(f"pinned file is unavailable: {path}") from exc


def durable_create_bytes(path: Path, payload: bytes) -> dict[str, Any]:
    require_direct_directory(path.parent)
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise RecoveryError(f"evidence already exists: {path}") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise RecoveryError(
                f"evidence target is not a private regular file: {path}"
            )
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise RecoveryError(f"evidence write stalled: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    fsync_directory(path.parent)
    return {
        "path": str(path),
        "size": len(payload),
        "sha256": sha256_bytes(payload),
    }


def require_direct_directory(path: Path) -> os.stat_result:
    try:
        metadata = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise RecoveryError(f"direct directory is unavailable: {path}") from exc
    if not stat.S_ISDIR(metadata.st_mode) or path.is_symlink():
        raise RecoveryError(f"path is not a direct directory: {path}")
    return metadata


def require_direct_directory_chain(root: Path, path: Path) -> None:
    direct_root = Path(os.path.abspath(root))
    direct_path = Path(os.path.abspath(path))
    try:
        relative = direct_path.relative_to(direct_root)
    except ValueError as exc:
        raise RecoveryError(f"path escapes repository root: {path}") from exc
    require_direct_directory(direct_root)
    current = direct_root
    for part in relative.parts:
        current /= part
        require_direct_directory(current)


def fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def allocate_recovery_run_dir(root: Path) -> Path:
    base = Path(os.path.abspath(root / RECOVERY_RUN_ROOT))
    require_direct_directory_chain(root, base)
    run_dir = base / (
        "s22plus-r4w1c2-noap-reboot-recovery-"
        + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    )
    if run_dir.parent != base:
        raise RecoveryError("recovery run directory is not a direct run-root child")
    try:
        run_dir.mkdir(mode=0o700, parents=False, exist_ok=False)
    except FileExistsError as exc:
        raise RecoveryError(f"recovery run directory already exists: {run_dir}") from exc
    fsync_directory(base)
    require_direct_directory(run_dir)
    return run_dir


def pinned_file(root: Path, key: str) -> tuple[Path, bytes]:
    relative, size, digest = PINNED_FILES[key]
    path = root / relative
    if path.is_symlink() or not path.is_file() or path.resolve() != path.absolute():
        raise RecoveryError(f"pinned incident file is missing or indirect: {relative}")
    payload = stable_bytes(path, maximum=max(size + 1, 4 * 1024 * 1024))
    if len(payload) != size or sha256_bytes(payload) != digest:
        raise RecoveryError(f"pinned incident file identity changed: {relative}")
    return path, payload


def parse_json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RecoveryError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise RecoveryError(f"{label} is not a JSON object")
    return value


def helper_identity(root: Path) -> dict[str, Any]:
    path = root / SCRIPT_RELATIVE
    return {"path": str(SCRIPT_RELATIVE), **core.hash_stable_file(path)}


def test_identity(root: Path) -> dict[str, Any]:
    path = root / TEST_RELATIVE
    return {"path": str(TEST_RELATIVE), **core.hash_stable_file(path)}


def exact_file_identity(path: Path, *, size: int, digest: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.resolve() != path.absolute():
        raise RecoveryError(f"runtime dependency is missing or indirect: {path}")
    payload = stable_bytes(path, maximum=size + 1)
    if len(payload) != size or sha256_bytes(payload) != digest:
        raise RecoveryError(f"runtime dependency identity changed: {path}")
    return {"path": str(path), "size": size, "sha256": digest}


def dependency_identities(root: Path) -> dict[str, dict[str, Any]]:
    identities: dict[str, dict[str, Any]] = {}
    for name, (relative, size, digest) in DEPENDENCY_FILES.items():
        identities[name] = exact_file_identity(
            root / relative, size=size, digest=digest
        )
        identities[name]["path"] = str(relative)
    for name, (path, size, digest) in ABSOLUTE_DEPENDENCIES.items():
        identities[name] = exact_file_identity(path, size=size, digest=digest)
    validate_runtime_dependency_graph(root)
    return identities


def validate_runtime_dependency_graph(root: Path) -> None:
    source_root = SCRIPT_RELATIVE.parent
    expected = {relative for relative, _size, _digest in DEPENDENCY_FILES.values()}
    discovered: set[Path] = set()
    pending = [SCRIPT_RELATIVE]
    visited: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in visited:
            continue
        visited.add(relative)
        payload = stable_bytes(root / relative, maximum=2 * 1024 * 1024)
        try:
            tree = ast.parse(payload, filename=str(relative))
        except SyntaxError as exc:
            raise RecoveryError(f"runtime dependency is not valid Python: {relative}") from exc
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.add(node.module.split(".", 1)[0])
        for module_name in modules:
            candidate = source_root / f"{module_name}.py"
            if (root / candidate).is_file():
                discovered.add(candidate)
                pending.append(candidate)
    if discovered != expected:
        missing = sorted(str(path) for path in discovered - expected)
        surplus = sorted(str(path) for path in expected - discovered)
        raise RecoveryError(
            f"runtime dependency graph changed: unpinned={missing}, unused={surplus}"
        )


def policy_draft_identity(root: Path) -> tuple[dict[str, Any], bytes]:
    path = root / POLICY_DRAFT_RELATIVE
    payload = stable_bytes(path, maximum=256 * 1024)
    if not payload.endswith(b"\n"):
        raise RecoveryError("no-AP recovery policy draft lacks its exact newline")
    return (
        {
            "path": str(POLICY_DRAFT_RELATIVE),
            "size": len(payload),
            "sha256": sha256_bytes(payload),
        },
        payload,
    )


def canonical_policy_template(
    payload: bytes,
    *,
    helper: dict[str, Any],
    test: dict[str, Any],
) -> bytes:
    canonical = payload
    replacements = (
        (str(helper["size"]).encode("ascii"), b"<HELPER_SIZE>"),
        (str(helper["sha256"]).encode("ascii"), b"<HELPER_SHA256>"),
        (str(test["size"]).encode("ascii"), b"<TEST_SIZE>"),
        (str(test["sha256"]).encode("ascii"), b"<TEST_SHA256>"),
    )
    for exact, placeholder in replacements:
        if canonical.count(exact) != 1:
            raise RecoveryError("policy draft dynamic identity is not unique and exact")
        canonical = canonical.replace(exact, placeholder)
    return canonical


def extract_policy(text: str) -> str | None:
    start = text.find(POLICY_BEGIN)
    end = text.find(POLICY_END)
    if start < 0 and end < 0:
        return None
    if start < 0 or end < start or text.find(POLICY_BEGIN, start + 1) >= 0:
        raise RecoveryError("no-AP recovery policy markers are malformed")
    end += len(POLICY_END)
    if text.find(POLICY_END, end) >= 0:
        raise RecoveryError("duplicate no-AP recovery policy marker")
    return text[start:end]


def require_old_policy_retired(text: str) -> None:
    start = text.find(OLD_POLICY_BEGIN)
    end = text.find(OLD_POLICY_END)
    if (
        start < 0
        or end < start
        or text.find(OLD_POLICY_BEGIN, start + 1) >= 0
    ):
        raise RecoveryError("consumed R4W1-C2 measured policy markers are malformed")
    end += len(OLD_POLICY_END)
    if text.find(OLD_POLICY_END, end) >= 0:
        raise RecoveryError("consumed R4W1-C2 measured policy marker is duplicated")
    old_clause = text[start:end]
    if OLD_POLICY_ACTIVE in old_clause or old_clause.count(OLD_POLICY_RETIRED) != 1:
        raise RecoveryError("consumed R4W1-C2 measured policy is not exactly retired")


def policy_status(root: Path) -> dict[str, Any]:
    text = stable_bytes(root / "AGENTS.md", maximum=2 * 1024 * 1024).decode("utf-8")
    clause = extract_policy(text)
    if clause is None:
        return {"active": False, "clause": None, "sha256": None}
    helper = helper_identity(root)
    test = test_identity(root)
    dependencies = dependency_identities(root)
    draft, draft_payload = policy_draft_identity(root)
    if clause.encode("utf-8") + b"\n" != draft_payload:
        raise RecoveryError("active no-AP recovery policy is not the exact reviewed draft")
    require_old_policy_retired(text)
    template_sha256 = sha256_bytes(
        canonical_policy_template(draft_payload, helper=helper, test=test)
    )
    if template_sha256 != EXPECTED_POLICY_TEMPLATE_SHA256:
        raise RecoveryError("no-AP recovery policy template identity changed")
    required = (
        POLICY_STATE,
        LIVE_ACK,
        helper["sha256"],
        test["sha256"],
        PINNED_FILES["consumed"][2],
        PINNED_FILES["stock_intent"][2],
        PARSE_FAILURE_SHA256,
        connected.EXPECTED_ODIN_SHA256,
        *(identity["sha256"] for identity in dependencies.values()),
    )
    if any(value not in clause for value in required):
        raise RecoveryError("active no-AP recovery policy does not bind exact inputs")
    return {
        "active": True,
        "clause": clause,
        "sha256": sha256_bytes(clause.encode("utf-8")),
        "draft": draft,
        "template_sha256": template_sha256,
        "dependencies": dependencies,
    }


def validate_failed_log(value: dict[str, Any], *, label: str, ap_sha256: str) -> None:
    expected = {
        "label": label,
        "returncode": 1,
        "stdout_bytes": len(PARSE_FAILURE_STDOUT),
        "stderr_bytes": 0,
        "stdout_sha256": PARSE_FAILURE_SHA256,
        "stderr_sha256": EMPTY_SHA256,
        "odin_sha256": connected.EXPECTED_ODIN_SHA256,
        "ap_sha256": ap_sha256,
        "sealed_inputs": True,
    }
    if value != expected:
        raise RecoveryError(f"{label} is not the exact sealed-path parse failure")


def validate_incident(root: Path) -> dict[str, Any]:
    opened: dict[str, dict[str, Any]] = {}
    bindings: dict[str, dict[str, Any]] = {}
    payloads: dict[str, bytes] = {}
    for key, (relative, size, digest) in PINNED_FILES.items():
        path, payload = pinned_file(root, key)
        payloads[key] = payload
        bindings[key] = {"path": str(relative), "size": size, "sha256": digest}
        if path.suffix == ".json":
            opened[key] = parse_json(payload, key)

    consumed = opened["consumed"]
    if (
        consumed.get("schema") != "s22plus_fyg8_r4w1c2_measured_consumed_v1"
        or consumed.get("target") != TARGET
        or consumed.get("run_dir") != str(INCIDENT_RUN)
        or consumed.get("usb_binding")
        != {
            "topology": "2-1.3",
            "serial_sha256": measured.android_serial_sha256("RFCT519XWGK"),
            "download_serial_state": measured.DOWNLOAD_USB_SERIAL_STATE,
        }
        or consumed.get("android_serial") != "RFCT519XWGK"
    ):
        raise RecoveryError("consumed incident binding is not exact")

    live_result = opened["live_result"]
    recovery_result = opened["recovery_result"]
    if (
        live_result.get("verdict")
        != "FAIL_R4W1C2_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED"
        or live_result.get("candidate_transfer_ok") is not False
        or live_result.get("candidate_transfer_error")
        != "r4w1c-candidate Odin flash failed rc=1"
        or recovery_result.get("verdict")
        != "FAIL_R4W1C2_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED"
        or recovery_result.get("error")
        != "r4w1c-stock-cleanup Odin flash failed rc=1"
        or recovery_result.get("rollback_ok") is not False
        or recovery_result.get("final_android") is not None
    ):
        raise RecoveryError("incident result contract does not describe failed rollback")

    for key, (label, ap_sha256) in FAILED_LOGS.items():
        validate_failed_log(opened[key], label=label, ap_sha256=ap_sha256)

    intent = opened["stock_intent"]
    if (
        intent.get("schema") != "s22plus_fyg8_r4w1c_stock_cleanup_intent_v1"
        or intent.get("target") != "stock"
        or intent.get("magisk_failure") != "definite-nonzero"
        or intent.get("stock_ap_sha256") != connected.EXPECTED_STOCK_AP_SHA256
        or intent.get("usb_binding", {}).get("topology") != "2-1.3"
        or intent.get("usb_binding", {}).get("serial_state") != "absent"
        or intent.get("ticket", {}).get("device_identity")
        != intent.get("usb_binding", {}).get("device_identity")
    ):
        raise RecoveryError("stock cleanup intent binding is not exact")

    transaction = payloads["transaction"]
    if b'"phase":"rollback_transfer_finished"' in transaction:
        raise RecoveryError("incident unexpectedly contains a completed rollback transfer")
    if PARSE_FAILURE_SHA256 != "7f6162459d49213e9d36485eaa1e7748492b484f4538db45ef50ab4d9f31adb4":
        raise RecoveryError("parse-failure preimage is not exact")

    return {
        "target": TARGET,
        "run_dir": str(INCIDENT_RUN),
        "android_serial": consumed["android_serial"],
        "usb_binding": consumed["usb_binding"],
        "parse_failure_stdout": {
            "bytes": len(PARSE_FAILURE_STDOUT),
            "sha256": PARSE_FAILURE_SHA256,
            "text": PARSE_FAILURE_STDOUT.decode("ascii").splitlines(),
            "meaning": "AP parse stopped before Setup Connection",
        },
        "files": bindings,
        "no_completed_transfer_receipt": True,
    }


def offline_check(root: Path) -> dict[str, Any]:
    incident = validate_incident(root)
    dependencies = dependency_identities(root)
    helper = helper_identity(root)
    test = test_identity(root)
    draft, draft_payload = policy_draft_identity(root)
    template_sha256 = sha256_bytes(
        canonical_policy_template(draft_payload, helper=helper, test=test)
    )
    if template_sha256 != EXPECTED_POLICY_TEMPLATE_SHA256:
        raise RecoveryError("no-AP recovery policy template identity changed")
    draft["template_sha256"] = template_sha256
    policy = policy_status(root)
    state_path = root / RECOVERY_STATE
    return {
        "schema": "s22plus_fyg8_r4w1c2_noap_reboot_recovery_offline_v1",
        "verdict": "PASS_R4W1C2_NOAP_REBOOT_RECOVERY_SOURCE_HOST_ONLY",
        "target": TARGET,
        "helper": helper,
        "test": test,
        "policy_draft": draft,
        "dependencies": dependencies,
        "incident": incident,
        "policy": {key: value for key, value in policy.items() if key != "clause"},
        "recovery_consumed": state_path.exists() or state_path.is_symlink(),
        "device_contact": False,
        "device_writes": False,
        "reboot": False,
        "odin_transfer": False,
        "flash": False,
    }


def exact_timeline(
    started: str,
    reboot_start: str,
    reboot_done: str,
    ready: str,
    ended: str | None = None,
) -> list[dict[str, str]]:
    ended = ready if ended is None else ended
    return [
        {"name": "live_session_start", "timestamp_utc": started},
        {"name": "candidate_flash_start", "timestamp_utc": started},
        {"name": "candidate_flash_done", "timestamp_utc": started},
        {"name": "candidate_boot_ready", "timestamp_utc": started},
        {"name": "rollback_flash_start", "timestamp_utc": reboot_start},
        {"name": "rollback_flash_done", "timestamp_utc": reboot_done},
        {"name": "rollback_boot_ready", "timestamp_utc": ready},
        {"name": "live_session_end", "timestamp_utc": ended},
    ]


def validate_reboot_stdout(stdout: bytes, stderr: bytes, device: str) -> list[str]:
    if stderr:
        raise RecoveryError("no-AP Odin reboot produced stderr")
    try:
        text = stdout.decode("utf-8")
    except UnicodeError as exc:
        raise RecoveryError("no-AP Odin reboot stdout is not UTF-8") from exc
    lines = text.splitlines()
    if (
        not stdout
        or len(stdout) > MAX_ODIN_OUTPUT
        or device not in lines
        or any(required not in lines for required in ODIN_SUCCESS_LINES)
        or any("fail" in line.lower() for line in lines)
    ):
        raise RecoveryError("no-AP Odin reboot output lacks the exact success shape")
    positions = [lines.index(value) for value in ODIN_SUCCESS_LINES]
    if positions != sorted(positions):
        raise RecoveryError("no-AP Odin reboot success lines are out of order")
    return lines


def bounded_odin_runner(
    command: list[str],
    *,
    stdout: int,
    stderr: int,
    stdin: int,
    pass_fds: tuple[int, ...],
    timeout: float,
    check: bool,
) -> subprocess.CompletedProcess[bytes]:
    if (
        stdout != subprocess.PIPE
        or stderr != subprocess.PIPE
        or stdin != subprocess.DEVNULL
        or check
    ):
        raise RecoveryError("bounded Odin runner contract is invalid")
    if not math.isfinite(timeout) or timeout <= 0:
        raise RecoveryError("bounded Odin timeout is invalid")
    process: subprocess.Popen[bytes] | None = None
    selector: selectors.BaseSelector | None = None
    streams: dict[str, list[bytes]] = {"stdout": [], "stderr": []}
    total = 0
    deadline = time.monotonic() + timeout
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            pass_fds=pass_fds,
        )
        selector = selectors.DefaultSelector()
        assert process.stdout is not None
        assert process.stderr is not None
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise BoundedOdinError(
                    "no-AP Odin reboot timed out",
                    b"".join(streams["stdout"]),
                    b"".join(streams["stderr"]),
                    timed_out=True,
                )
            events = selector.select(remaining)
            if not events:
                raise BoundedOdinError(
                    "no-AP Odin reboot timed out",
                    b"".join(streams["stdout"]),
                    b"".join(streams["stderr"]),
                    timed_out=True,
                )
            for key, _mask in events:
                chunk = os.read(key.fd, 8192)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                remaining_capacity = MAX_ODIN_OUTPUT - total
                if len(chunk) > remaining_capacity:
                    streams[str(key.data)].append(chunk[:remaining_capacity])
                    raise BoundedOdinError(
                        "no-AP Odin reboot output exceeded its bound",
                        b"".join(streams["stdout"]),
                        b"".join(streams["stderr"]),
                        output_overflow=True,
                    )
                total += len(chunk)
                streams[str(key.data)].append(chunk)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BoundedOdinError(
                "no-AP Odin reboot timed out",
                b"".join(streams["stdout"]),
                b"".join(streams["stderr"]),
                timed_out=True,
            )
        returncode = process.wait(timeout=remaining)
        return subprocess.CompletedProcess(
            command,
            returncode,
            stdout=b"".join(streams["stdout"]),
            stderr=b"".join(streams["stderr"]),
        )
    except subprocess.TimeoutExpired as exc:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        raise BoundedOdinError(
            "no-AP Odin reboot timed out",
            b"".join(streams["stdout"]),
            b"".join(streams["stderr"]),
            timed_out=True,
        ) from exc
    except BaseException:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        raise
    finally:
        if selector is not None:
            selector.close()
        if process is not None:
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()


def run_noap_odin(
    odin_fd: int,
    device: str,
    *,
    stdout_path: Path,
    stderr_path: Path,
    outcome_path: Path,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = bounded_odin_runner,
) -> tuple[subprocess.CompletedProcess[bytes], list[str], list[str]]:
    command = [f"/proc/self/fd/{odin_fd}", "--reboot", "-d", device]
    forbidden = {"-a", "-b", "-c", "-s", "-u", "-e", "-V", "--redownload"}
    if any(argument in forbidden for argument in command):
        raise RecoveryError("no-AP reboot command contains a transfer option")
    try:
        completed = runner(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            pass_fds=(odin_fd,),
            timeout=60,
            check=False,
        )
        stdout = completed.stdout or b""
        stderr = completed.stderr or b""
    except (subprocess.TimeoutExpired, BoundedOdinError) as exc:
        stdout, stderr, overflow = cap_output_pair(
            exc.stdout or b"", exc.stderr or b""
        )
        stdout_record = durable_create_bytes(stdout_path, stdout)
        stderr_record = durable_create_bytes(stderr_path, stderr)
        core.durable_create_json(
            outcome_path,
            {
                "schema": "s22plus_fyg8_r4w1c2_noap_reboot_outcome_v1",
                "created_at_utc": core.utc_now(),
                "attempted": True,
                "returned": False,
                "timed_out": bool(getattr(exc, "timed_out", True)),
                "output_overflow": bool(
                    getattr(exc, "output_overflow", False) or overflow
                ),
                "returncode": None,
                "stdout": stdout_record,
                "stderr": stderr_record,
            },
        )
        raise RecoveryError(str(exc)) from exc
    except OSError as exc:
        stdout_record = durable_create_bytes(stdout_path, b"")
        stderr_record = durable_create_bytes(stderr_path, b"")
        core.durable_create_json(
            outcome_path,
            {
                "schema": "s22plus_fyg8_r4w1c2_noap_reboot_outcome_v1",
                "created_at_utc": core.utc_now(),
                "attempted": True,
                "returned": False,
                "timed_out": False,
                "output_overflow": False,
                "returncode": None,
                "spawn_error": str(exc),
                "stdout": stdout_record,
                "stderr": stderr_record,
            },
        )
        raise RecoveryError("no-AP Odin reboot process could not start") from exc
    stdout, stderr, overflow = cap_output_pair(stdout, stderr)
    if overflow:
        stdout_record = durable_create_bytes(stdout_path, stdout)
        stderr_record = durable_create_bytes(stderr_path, stderr)
        core.durable_create_json(
            outcome_path,
            {
                "schema": "s22plus_fyg8_r4w1c2_noap_reboot_outcome_v1",
                "created_at_utc": core.utc_now(),
                "attempted": True,
                "returned": True,
                "timed_out": False,
                "output_overflow": True,
                "returncode": completed.returncode,
                "stdout": stdout_record,
                "stderr": stderr_record,
            },
        )
        raise RecoveryError("no-AP Odin reboot output exceeded its bound")
    stdout_record = durable_create_bytes(stdout_path, stdout)
    stderr_record = durable_create_bytes(stderr_path, stderr)
    core.durable_create_json(
        outcome_path,
        {
            "schema": "s22plus_fyg8_r4w1c2_noap_reboot_outcome_v1",
            "created_at_utc": core.utc_now(),
            "attempted": True,
            "returned": True,
            "timed_out": False,
            "output_overflow": False,
            "returncode": completed.returncode,
            "stdout": stdout_record,
            "stderr": stderr_record,
        },
    )
    if completed.returncode != 0:
        raise RecoveryError(f"no-AP Odin reboot failed rc={completed.returncode}")
    lines = validate_reboot_stdout(stdout, stderr, device)
    return completed, command, lines


def cap_output_pair(stdout: bytes, stderr: bytes) -> tuple[bytes, bytes, bool]:
    bounded_stdout = stdout[:MAX_ODIN_OUTPUT]
    bounded_stderr = stderr[: MAX_ODIN_OUTPUT - len(bounded_stdout)]
    overflow = len(stdout) + len(stderr) > MAX_ODIN_OUTPUT
    return bounded_stdout, bounded_stderr, overflow


def create_recovery_state(
    root: Path,
    *,
    policy: dict[str, Any],
    incident: dict[str, Any],
    run_dir: Path,
    helper: dict[str, Any],
    test: dict[str, Any],
    dependencies: dict[str, dict[str, Any]],
    policy_draft: dict[str, Any],
) -> dict[str, Any]:
    path = root / RECOVERY_STATE
    require_direct_directory_chain(root, run_dir)
    expected_run_root = Path(os.path.abspath(root / RECOVERY_RUN_ROOT))
    if Path(os.path.abspath(run_dir)).parent != expected_run_root:
        raise RecoveryError(
            "recovery state run directory is outside the direct run root"
        )
    require_direct_directory_chain(root, path.parent)
    if path.exists() or path.is_symlink():
        raise RecoveryError("no-AP reboot recovery was already consumed")
    record = {
        "schema": "s22plus_fyg8_r4w1c2_noap_reboot_recovery_consumed_v1",
        "created_at_utc": core.utc_now(),
        "target": TARGET,
        "ack": LIVE_ACK,
        "operator_attestation_ack": LIVE_ACK,
        "physical_continuity_basis": PHYSICAL_CONTINUITY_BASIS,
        "helper_sha256": helper["sha256"],
        "test_sha256": test["sha256"],
        "policy_clause_sha256": policy["sha256"],
        "policy_draft": policy_draft,
        "runtime_dependencies": dependencies,
        "incident_consumed_sha256": incident["files"]["consumed"]["sha256"],
        "stock_intent_sha256": incident["files"]["stock_intent"]["sha256"],
        "run_dir": str(run_dir.relative_to(root)),
        "expected_usb_binding": incident["usb_binding"],
        "consumption_timing": "before any device or USB observation",
        "action": "odin4 --reboot only; no AP and no partition payload",
    }
    payload = (
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    durable_create_bytes(path, payload)
    return record


def live_run(root: Path, args: argparse.Namespace) -> int:
    offline = offline_check(root)
    policy = policy_status(root)
    if not policy["active"] or args.ack != LIVE_ACK:
        raise RecoveryError("no-AP reboot recovery policy or acknowledgement is inactive")
    if offline["recovery_consumed"]:
        raise RecoveryError("no-AP reboot recovery one-shot is already consumed")

    started = core.utc_now()
    run_dir = allocate_recovery_run_dir(root)
    result_path = run_dir / "result.json"
    timeline_path = run_dir / "timeline.json"
    stdout_path = run_dir / "odin-reboot.stdout"
    stderr_path = run_dir / "odin-reboot.stderr"
    attempt_path = run_dir / "odin-reboot-attempt.json"
    outcome_path = run_dir / "odin-reboot-outcome.json"
    result: dict[str, Any] = {
        "schema": "s22plus_fyg8_r4w1c2_noap_reboot_recovery_live_v1",
        "target": TARGET,
        "mode": "no-ap-reboot-only",
        "verdict": "INCOMPLETE",
        "incident": offline["incident"],
        "device_writes": False,
        "partition_write": False,
        "odin_transfer": False,
        "flash": False,
        "reboot": None,
        "reboot_attempted": False,
        "reboot_command_returned": False,
        "physical_continuity_basis": PHYSICAL_CONTINUITY_BASIS,
    }

    odin = (root / args.odin).resolve() if not args.odin.is_absolute() else args.odin
    reboot_start: str | None = None
    reboot_done: str | None = None
    ready: str | None = None
    try:
        if odin != connected.DEFAULT_ODIN:
            raise RecoveryError("no-AP recovery requires the exact default Odin path")
        if offline_check(root) != offline:
            raise RecoveryError("host evidence changed before recovery consumption")
        state = create_recovery_state(
            root,
            policy=policy,
            incident=offline["incident"],
            run_dir=run_dir,
            helper=offline["helper"],
            test=offline["test"],
            dependencies=offline["dependencies"],
            policy_draft=offline["policy_draft"],
        )
        result["recovery_state"] = state
        with measured.pinned_odin_session(odin) as (odin_fd, external_odin):
            with odin_core.transaction_session(run_dir) as lease:
                ticket, sequence = measured.wait_for_endpoint(
                    external_odin,
                    run_dir,
                    timeout_sec=args.endpoint_wait_sec,
                    sequence=0,
                    lease=lease,
                    expected_usb_binding=dict(offline["incident"]["usb_binding"]),
                )
                usb = measured.require_ticket_usb_binding(
                    ticket, dict(offline["incident"]["usb_binding"])
                )
                device, sequence, revalidation = measured.revalidate_ticket(
                    external_odin,
                    run_dir,
                    ticket,
                    sequence=sequence,
                    lease=lease,
                )
                if measured.require_ticket_usb_binding(
                    ticket, dict(offline["incident"]["usb_binding"])
                ) != usb:
                    raise RecoveryError("Download USB binding changed before reboot")
                reboot_start = core.utc_now()
                command_shape = ["<sealed-odin-fd>", "--reboot", "-d", device]
                core.durable_create_json(
                    attempt_path,
                    {
                        "schema": "s22plus_fyg8_r4w1c2_noap_reboot_attempt_v1",
                        "created_at_utc": reboot_start,
                        "attempted": True,
                        "operator_attestation_ack": LIVE_ACK,
                        "physical_continuity_basis": PHYSICAL_CONTINUITY_BASIS,
                        "command_shape": command_shape,
                        "ticket": measured._ticket_payload(ticket),
                        "usb_binding": usb,
                        "device_writes": False,
                        "partition_write": False,
                        "odin_transfer": False,
                        "flash": False,
                    },
                )
                result["reboot_attempted"] = True
                completed, command, lines = run_noap_odin(
                    odin_fd,
                    device,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                    outcome_path=outcome_path,
                )
                reboot_done = core.utc_now()
                result["reboot_command_returned"] = True
                serial, android = measured.wait_magisk_android(
                    args.android_wait_sec,
                    expected_serial=str(offline["incident"]["android_serial"]),
                    expected_usb_binding=dict(offline["incident"]["usb_binding"]),
                )
                absence = odin_core.wait_for_no_live_endpoint(
                    external_odin,
                    run_dir,
                    timeout_sec=args.odin_absence_wait_sec,
                    sequence_start=sequence,
                    poll_sec=0.1,
                    lease=lease,
                    endpoint_observer_factory=odin_core.measured_usbfs_observer,
                )
                if not absence.absent or absence.timed_out:
                    raise RecoveryError("exact Android return retained an Odin endpoint")
                ready = core.utc_now()
                timeline = exact_timeline(started, reboot_start, reboot_done, ready)
                result.update(
                    {
                        "verdict": PASS_VERDICT,
                        "device_writes": False,
                        "partition_write": False,
                        "odin_transfer": False,
                        "flash": False,
                        "reboot": True,
                        "ticket": measured._ticket_payload(ticket),
                        "usb_binding": usb,
                        "endpoint_revalidation": revalidation,
                        "command_shape": command_shape,
                        "command_argument_count": len(command),
                        "ap_argument_present": False,
                        "odin": {
                            "returncode": completed.returncode,
                            "attempt": {
                                "path": str(attempt_path.relative_to(root)),
                                **core.hash_stable_file(attempt_path),
                            },
                            "outcome": {
                                "path": str(outcome_path.relative_to(root)),
                                **core.hash_stable_file(outcome_path),
                            },
                            "stdout": {"path": str(stdout_path.relative_to(root)), **core.hash_stable_file(stdout_path)},
                            "stderr": {"path": str(stderr_path.relative_to(root)), **core.hash_stable_file(stderr_path)},
                            "lines": lines,
                        },
                        "android_serial": serial,
                        "final_android": android,
                        "no_odin_endpoint": True,
                        "timeline_phase_semantics": {
                            "candidate_flash_start": "zero-action recovery placeholder",
                            "candidate_flash_done": "zero-action recovery placeholder",
                            "candidate_boot_ready": "zero-action recovery placeholder",
                            "rollback_flash_start": "no-AP reboot command start; no flash",
                            "rollback_flash_done": "no-AP reboot command return; no flash",
                        },
                    }
                )
                core.durable_create_json(timeline_path, {"events": timeline})
                result["timeline"] = {
                    "path": str(timeline_path.relative_to(root)),
                    "events": timeline,
                }
                core.durable_create_json(result_path, result)
                print(json.dumps({"run_dir": str(run_dir), "verdict": PASS_VERDICT}, indent=2))
                return 0
    except (
        RecoveryError,
        measured.GateError,
        connected.GateError,
        odin_core.OdinTransitionError,
        core.LiveCoreError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        ended = core.utc_now()
        attempt: dict[str, Any] | None = None
        outcome: dict[str, Any] | None = None
        if attempt_path.is_file() and not attempt_path.is_symlink():
            attempt = parse_json(stable_bytes(attempt_path), "reboot attempt")
        if outcome_path.is_file() and not outcome_path.is_symlink():
            outcome = parse_json(stable_bytes(outcome_path), "reboot outcome")
        if attempt is not None:
            reboot_start = str(attempt.get("created_at_utc") or reboot_start or ended)
            result["reboot_attempted"] = attempt.get("attempted") is True
        if outcome is not None:
            reboot_done = str(outcome.get("created_at_utc") or reboot_done or ended)
            result["reboot_command_returned"] = outcome.get("returned") is True
        timeline = exact_timeline(
            started,
            reboot_start or ended,
            reboot_done or ended,
            ready or ended,
            ended,
        )
        result["verdict"] = FAIL_VERDICT
        result["error"] = str(exc)
        result["recovery_consumed"] = (root / RECOVERY_STATE).exists()
        result["reboot"] = True if ready is not None else None
        result["odin_attempt"] = attempt
        result["odin_outcome"] = outcome
        result["timeline_phase_semantics"] = {
            "candidate_flash_start": "zero-action recovery placeholder",
            "candidate_flash_done": "zero-action recovery placeholder",
            "candidate_boot_ready": "zero-action recovery placeholder",
            "rollback_flash_start": (
                "no-AP reboot attempted; no flash"
                if result["reboot_attempted"]
                else "no reboot attempt; no flash"
            ),
            "rollback_flash_done": (
                "no-AP reboot command returned; no flash"
                if result["reboot_command_returned"]
                else "no command return observed; no flash"
            ),
            "rollback_boot_ready": (
                "exact Android ready"
                if ready is not None
                else "exact Android readiness not proven"
            ),
        }
        core.durable_create_json(timeline_path, {"events": timeline})
        result["timeline"] = {
            "path": str(timeline_path.relative_to(root)),
            "events": timeline,
        }
        core.durable_create_json(result_path, result)
        print(json.dumps({"run_dir": str(run_dir), "verdict": FAIL_VERDICT}, indent=2))
        return 20


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline-check", action="store_true")
    modes.add_argument("--live", action="store_true")
    parser.add_argument("--ack")
    parser.add_argument("--odin", type=Path, default=connected.DEFAULT_ODIN)
    parser.add_argument("--endpoint-wait-sec", type=float, default=120.0)
    parser.add_argument("--android-wait-sec", type=float, default=300.0)
    parser.add_argument("--odin-absence-wait-sec", type=float, default=15.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    try:
        if args.offline_check:
            print(json.dumps(offline_check(root), indent=2, sort_keys=True))
            return 0
        return live_run(root, args)
    except (RecoveryError, measured.GateError, connected.GateError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
