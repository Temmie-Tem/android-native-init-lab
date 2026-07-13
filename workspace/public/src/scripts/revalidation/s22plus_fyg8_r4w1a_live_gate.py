#!/usr/bin/env python3
"""Guarded FYG8 R4W1-A retained PID-1 witness live gate.

The helper verifies the exact host-built boot-only candidate, records a
read-only Magisk/observer baseline, and supports a separately authorized
``bugreportz -s`` oracle rehearsal.  Candidate transfer and emergency rollback
remain independently policy-gated one-shot operations.

The repository policy is deliberately inactive by default.  Merely having
this file does not authorize device contact, a bugreport capture, or a flash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import s22plus_fyg8_r3c0_live_gate as common
import s22plus_fyg8_r4w1a_marker_oracle as oracle


SCHEMA = "s22plus_fyg8_r4w1a_live_gate_v1"
TARGET = common.TARGET
SCRIPT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1a_live_gate.py"
)
LIVE_TEST_RELATIVE = Path("tests/test_s22plus_fyg8_r4w1a_live_gate.py")
COMMON_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r3c0_live_gate.py"
)
TRANSPORT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_m3_observable_live_gate.py"
)
BUILDER_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/build_s22plus_fyg8_r4w1a_candidate.py"
)
BUILDER_TEST_RELATIVE = Path("tests/test_build_s22plus_fyg8_r4w1a_candidate.py")
CHECKER_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1a_static_checker.py"
)
CHECKER_TEST_RELATIVE = Path("tests/test_s22plus_fyg8_r4w1a_static_checker.py")
ORACLE_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1a_marker_oracle.py"
)
ORACLE_TEST_RELATIVE = Path("tests/test_s22plus_fyg8_r4w1a_marker_oracle.py")
POLICY_DRAFT = Path(
    "docs/operations/S22PLUS_FYG8_R4W1A_AGENTS_EXCEPTION_DRAFT_2026-07-13.md"
)
POLICY_MARKER = "S22+ FYG8 R4W1-A retained PID1 witness boot-only live gate"
ORACLE_POLICY_MARKER = "S22+ FYG8 R4W1-A bugreport oracle dry-run live gate"
ACTIVE_SENTINEL = "S22PLUS_FYG8_R4W1A_POLICY_STATE=ACTIVE"
ORACLE_ACTIVE_SENTINEL = "S22PLUS_FYG8_R4W1A_ORACLE_DRY_POLICY_STATE=ACTIVE"
LIVE_ACK_TOKEN = "S22PLUS-FYG8-R4W1A-RETAINED-PID1-WITNESS-LIVE"
CONNECTED_ACK_TOKEN = "S22PLUS-FYG8-R4W1A-CONNECTED-IDENTITY-DRY-RUN"
ORACLE_ACK_TOKEN = "S22PLUS-FYG8-R4W1A-BUGREPORT-ORACLE-DRY-RUN"
ROLLBACK_ACK_TOKEN = "S22PLUS-FYG8-R4W1A-MAGISK-ROLLBACK-FROM-DOWNLOAD"

EXPECTED_CANDIDATE_BOOT_SHA256 = (
    "a2bba0ef907af14e57508ca55d247d571c3f89936dd7020293e51ebfa8f8d133"
)
EXPECTED_CANDIDATE_BOOT_SIZE = 100_663_296
EXPECTED_CANDIDATE_LZ4_SHA256 = (
    "0bf83af2bb7167aae4a57be1686599aa99fe9e75ccd7aa89128da799a4c14a99"
)
EXPECTED_CANDIDATE_AP_SHA256 = (
    "cb2c078f001af6e263dc3f533a2efe3294a5c80201f50952a45bb88254e4d895"
)
EXPECTED_MANIFEST_SHA256 = (
    "3b9b5c0f0d3bac818a010cb7682e1146eaa50d5feec8a16324a039bbd5d2f85b"
)
EXPECTED_R4W1_IMAGE_SHA256 = (
    "9552653de86dbdc2f1abd919b4d7b0d3f365fc878a56ed5ae09c82d0d81d844c"
)
EXPECTED_BUILDER_SHA256 = (
    "081d608ef54ddd171aaa2013c5b06eb33b72aba760192e66ac023dc2f23e759f"
)
EXPECTED_BUILDER_TEST_SHA256 = (
    "bb0613a0546078d5c61cfb48957153772d0fd8e16ffd5fd5282ca987df4712f4"
)
EXPECTED_LIVE_TEST_SHA256 = (
    "314b3efc9fec555b31bf6b926bcdbe4b34ebe75ad17bf1172d0e3027e52bf145"
)
EXPECTED_COMMON_SHA256 = (
    "f10a30735882bbd59453471fe901b1cef11fdf42bcf3560a8ae61b4af361c4f4"
)
EXPECTED_TRANSPORT_SHA256 = (
    "1f093d78a110925440c98741399d8828201cce38265a5c941ac2f71b6c104305"
)
EXPECTED_CHECKER_SHA256 = (
    "cb2fb233370463135d6f8a26c2fbd93fb3404c973aa5b326a94c6ec149c2f711"
)
EXPECTED_CHECKER_TEST_SHA256 = (
    "be802e37fbfb1ef94599e170a2c68bd55bb6e9116612bb697f86362f32ca18bf"
)
EXPECTED_STATIC_RESULT_SHA256 = (
    "fc528ba9c8acce18a636d398a13add42a7882e7bfd505e82d63ff861e0963a0b"
)
EXPECTED_ORACLE_SHA256 = (
    "bfc7a8d76892931ff7faed25606cc7c7c92cf6ef3f67357316ee25b0fa887462"
)
EXPECTED_ORACLE_TEST_SHA256 = (
    "9006fc3579ec07ac226d082fbc99321e5309da721be805f4646858a2807235b4"
)
EXPECTED_ORACLE_AUDIT_SHA256 = (
    "f243191c985caf918a2a4504be349fdaa133c10b75caab973c71b1e31c1610dd"
)
EXPECTED_OVERWRITE_RESULT_SHA256 = (
    "ec6052c0165e17f202a103bae7ee376c873f0aefcf72f3a86370fdc821711301"
)

DEFAULT_CANDIDATE_DIR = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1a_candidate/reproduction-c"
)
DEFAULT_CANDIDATE_BOOT = DEFAULT_CANDIDATE_DIR / "boot.img"
DEFAULT_CANDIDATE_AP = DEFAULT_CANDIDATE_DIR / "odin4/AP.tar.md5"
DEFAULT_MANIFEST = DEFAULT_CANDIDATE_DIR / "manifest.json"
DEFAULT_STATIC_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1a_candidate/static-check/result.json"
)
DEFAULT_OVERWRITE_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1a_candidate/overwrite-budget/result.json"
)
DEFAULT_ORACLE_AUDIT = Path(
    "workspace/private/work/s22plus_fyg8_r4w1a_oracle/marker_oracle_audit.json"
)
RUN_ROOT = Path("workspace/private/runs")
CONSUMED_STATE = Path(
    "workspace/private/state/s22plus_fyg8_r4w1a_live_exception_consumed.json"
)
CONNECTED_PASS_STATE = Path(
    "workspace/private/state/s22plus_fyg8_r4w1a_connected_dry_run_pass_v3.json"
)
ORACLE_CONSUMED_STATE = Path(
    "workspace/private/state/s22plus_fyg8_r4w1a_oracle_dry_run_consumed.json"
)
ORACLE_PASS_STATE = Path(
    "workspace/private/state/s22plus_fyg8_r4w1a_oracle_dry_run_pass.json"
)

TIMELINE_NAMES = common.TIMELINE_NAMES
EXPECTED_BIND = (
    "/sys/bus/platform/drivers/samsung,kernel_log_buf/"
    "8.samsung,kernel_log_buf"
)
PSTORE_PATHS = (
    "/sys/fs/pstore/console-ramoops",
    "/sys/fs/pstore/console-ramoops-0",
)
MAX_SNAPSHOT_BYTES = 2_097_136
MAX_BUGREPORT_STDERR = 1024 * 1024
REMOTE_BUGREPORT_ROOT = "/bugreports"
REMOTE_PATH_RE = re.compile(r"^/bugreports/[A-Za-z0-9][A-Za-z0-9._+-]{0,191}$")
STAT_RE = re.compile(
    r"^(?P<device>[0-9]+):(?P<inode>[0-9]+):(?P<size>[0-9]+):"
    r"(?P<mtime>-?[0-9]+):(?P<mode>[0-9a-fA-F]+)$"
)

GateError = common.GateError


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def resolve(root: Path, path: Path) -> Path:
    return common.resolve(root, path)


def require_sha(path: Path, expected: str, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise GateError(f"{label} missing or not a direct regular file")
    actual = common.sha256_file(path)
    if actual != expected:
        raise GateError(f"{label} SHA mismatch: {actual}")


def read_pinned_json(path: Path, expected: str, label: str) -> dict[str, Any]:
    require_sha(path, expected, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GateError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise GateError(f"{label} top level is not an object")
    return value


def verify_manifest(path: Path) -> dict[str, Any]:
    data = read_pinned_json(path, EXPECTED_MANIFEST_SHA256, "R4W1-A manifest")
    if data.get("schema") != "s22plus_fyg8_r4w1a_candidate_build_v1":
        raise GateError("R4W1-A manifest schema mismatch")
    if data.get("target") != TARGET:
        raise GateError("R4W1-A manifest target mismatch")
    if data.get("verdict") != "PASS_R4W1A_ARTIFACT_BUILT_HOST_ONLY":
        raise GateError("R4W1-A manifest verdict mismatch")
    hashes = data.get("artifacts", {}).get("hashes", {})
    expected_hashes = {
        "boot_img": EXPECTED_CANDIDATE_BOOT_SHA256,
        "boot_img_lz4": EXPECTED_CANDIDATE_LZ4_SHA256,
        "ap_tar_md5": EXPECTED_CANDIDATE_AP_SHA256,
        "kernel": EXPECTED_R4W1_IMAGE_SHA256,
    }
    for key, expected in expected_hashes.items():
        if hashes.get(key) != expected:
            raise GateError(f"R4W1-A manifest artifact mismatch: {key}")
    construction = data.get("construction", {})
    required_true = (
        "kernel_equals_exact_r4w1_image",
        "r3c0_boot_header_preserved",
        "r3c0_post_kernel_bytes_preserved",
        "r3c0_ramdisk_preserved",
        "r3c0_signer_preserved",
        "r3c0_vbmeta_preserved",
        "r3c0_avb_footer_preserved",
        "arm64_header_exact_r3c0_match",
    )
    if any(construction.get(key) is not True for key in required_true):
        raise GateError("R4W1-A manifest construction contract mismatch")
    if construction.get("patch_vbmeta_flag") is not False:
        raise GateError("R4W1-A manifest PATCHVBMETAFLAG mismatch")
    if construction.get("r4w1_marker_count") != 1:
        raise GateError("R4W1-A manifest marker count mismatch")
    if construction.get("difference", {}).get("outside_kernel_changed_byte_count") != 0:
        raise GateError("R4W1-A manifest records an outside-kernel delta")
    safety = data.get("safety", {})
    for key in (
        "device_contact",
        "usb_enumeration",
        "odin_transfer",
        "flash",
        "live_authorized",
        "r4w1a_live_authorized",
    ):
        if safety.get(key) is not False:
            raise GateError(f"R4W1-A manifest safety mismatch: {key}")
    if safety.get("boot_only_ap") is not True:
        raise GateError("R4W1-A manifest is not boot-only")
    return data


def run_static_checker(root: Path) -> dict[str, Any]:
    checker = root / CHECKER_RELATIVE
    require_sha(checker, EXPECTED_CHECKER_SHA256, "R4W1-A static checker")
    result = common.run([sys.executable, checker], timeout=300)
    if result.returncode != 0:
        raise GateError("R4W1-A static checker failed closed")
    if sha256_bytes(result.stdout.encode("utf-8")) != EXPECTED_STATIC_RESULT_SHA256:
        raise GateError("R4W1-A static checker output SHA mismatch")
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GateError("R4W1-A static checker output is not JSON") from exc
    if report.get("verdict") != "PASS_R4W1A_THREE_REPRO_STATIC_CONTRACT":
        raise GateError("R4W1-A static checker verdict mismatch")
    return {
        "source_sha256": EXPECTED_CHECKER_SHA256,
        "result_sha256": EXPECTED_STATIC_RESULT_SHA256,
        "verdict": report["verdict"],
    }


def verify_artifacts(
    root: Path, boot: Path, ap: Path, manifest: Path, odin: Path
) -> dict[str, Any]:
    require_sha(root / COMMON_RELATIVE, EXPECTED_COMMON_SHA256, "reviewed R3 live primitives")
    require_sha(
        root / TRANSPORT_RELATIVE,
        EXPECTED_TRANSPORT_SHA256,
        "reviewed Odin transport primitives",
    )
    require_sha(root / BUILDER_RELATIVE, EXPECTED_BUILDER_SHA256, "R4W1-A builder")
    require_sha(root / LIVE_TEST_RELATIVE, EXPECTED_LIVE_TEST_SHA256, "R4W1-A live test")
    require_sha(
        root / BUILDER_TEST_RELATIVE,
        EXPECTED_BUILDER_TEST_SHA256,
        "R4W1-A builder test",
    )
    require_sha(root / CHECKER_TEST_RELATIVE, EXPECTED_CHECKER_TEST_SHA256, "checker test")
    require_sha(root / ORACLE_RELATIVE, EXPECTED_ORACLE_SHA256, "marker oracle")
    require_sha(root / ORACLE_TEST_RELATIVE, EXPECTED_ORACLE_TEST_SHA256, "oracle test")
    if boot.stat().st_size != EXPECTED_CANDIDATE_BOOT_SIZE:
        raise GateError("R4W1-A candidate boot size mismatch")
    require_sha(boot, EXPECTED_CANDIDATE_BOOT_SHA256, "R4W1-A candidate boot")
    require_sha(ap, EXPECTED_CANDIDATE_AP_SHA256, "R4W1-A candidate AP")
    if common.tar_members(ap) != [common.EXPECTED_MEMBER]:
        raise GateError("R4W1-A candidate AP is not exactly boot-only")
    manifest_data = verify_manifest(manifest)

    static_result = read_pinned_json(
        root / DEFAULT_STATIC_RESULT,
        EXPECTED_STATIC_RESULT_SHA256,
        "R4W1-A static result",
    )
    if static_result.get("verdict") != "PASS_R4W1A_THREE_REPRO_STATIC_CONTRACT":
        raise GateError("pinned R4W1-A static result verdict mismatch")
    overwrite = read_pinned_json(
        root / DEFAULT_OVERWRITE_RESULT,
        EXPECTED_OVERWRITE_RESULT_SHA256,
        "R4W1-A overwrite-budget result",
    )
    if (
        overwrite.get("verdict")
        != "PASS_R4W1A_OVERWRITE_BUDGET_MEASURED_HOST_ONLY"
        or overwrite.get("risk_verdict") != "HIGH_RISK_UNRESOLVED"
        or overwrite.get("a0_deliverable_pass") is not True
        or overwrite.get("a1_ready") is not False
    ):
        raise GateError("overwrite-budget result no longer records unresolved old oracle")
    audit = read_pinned_json(
        root / DEFAULT_ORACLE_AUDIT,
        EXPECTED_ORACLE_AUDIT_SHA256,
        "R4W1-A marker-oracle audit",
    )
    decision = audit.get("decision", {})
    if (
        audit.get("verdict") != "PASS_R4W1A_PRIMARY_ORACLE_SELECTED_HOST_ONLY"
        or decision.get("selected_primary_oracle")
        != "BUGREPORTZ_STREAM_DUMPSTATE_LAST_KMSG"
        or decision.get("a1_implementation_ready") is not True
        or decision.get("a1_live_ready") is not False
    ):
        raise GateError("R4W1-A marker-oracle decision mismatch")

    magisk = resolve(root, common.DEFAULT_MAGISK_ROLLBACK_AP)
    stock = resolve(root, common.DEFAULT_STOCK_ROLLBACK_AP)
    require_sha(magisk, common.EXPECTED_MAGISK_AP_SHA256, "Magisk rollback AP")
    require_sha(stock, common.EXPECTED_STOCK_AP_SHA256, "stock cleanup AP")
    if common.tar_members(magisk) != [common.EXPECTED_MEMBER]:
        raise GateError("Magisk rollback AP is not boot-only")
    if common.tar_members(stock) != [common.EXPECTED_MEMBER]:
        raise GateError("stock cleanup AP is not boot-only")
    return {
        "candidate_boot_sha256": EXPECTED_CANDIDATE_BOOT_SHA256,
        "candidate_ap_sha256": EXPECTED_CANDIDATE_AP_SHA256,
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "manifest_schema": manifest_data["schema"],
        "r4w1_image_sha256": EXPECTED_R4W1_IMAGE_SHA256,
        "magisk_rollback_ap_sha256": common.EXPECTED_MAGISK_AP_SHA256,
        "stock_cleanup_ap_sha256": common.EXPECTED_STOCK_AP_SHA256,
        "oracle_source_sha256": EXPECTED_ORACLE_SHA256,
        "oracle_audit_sha256": EXPECTED_ORACLE_AUDIT_SHA256,
        "live_test_sha256": EXPECTED_LIVE_TEST_SHA256,
        "common_source_sha256": EXPECTED_COMMON_SHA256,
        "transport_source_sha256": EXPECTED_TRANSPORT_SHA256,
        "static_checker": run_static_checker(root),
        "odin": common.verify_odin(odin),
    }


def helper_sha256(root: Path) -> str:
    return common.sha256_file(root / SCRIPT_RELATIVE)


def durable_create_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    if path.exists() or path.is_symlink():
        raise GateError(f"state already exists: {path}")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except FileExistsError as exc:
        raise GateError(f"state was created concurrently: {path}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def validate_pass_record(root: Path, kind: str) -> str:
    contracts = {
        "connected": (
            CONNECTED_PASS_STATE,
            "s22plus_fyg8_r4w1a_connected_pass_v3",
            "connected-dry-run",
            "PASS_R4W1A_CONNECTED_IDENTITY_DRY_RUN_READ_ONLY",
        ),
        "oracle": (
            ORACLE_PASS_STATE,
            "s22plus_fyg8_r4w1a_oracle_pass_v1",
            "oracle-dry-run",
            "PASS_R4W1A_ORACLE_DRY_RUN_EXACT_ZIP_AND_CLEANUP",
        ),
    }
    if kind not in contracts:
        raise GateError(f"unknown promotion-record kind: {kind}")
    relative, schema, mode, verdict = contracts[kind]
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise GateError(f"{kind} promotion record is missing")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GateError(f"{kind} promotion record is invalid JSON") from exc
    if (
        record.get("schema") != schema
        or record.get("target") != TARGET
        or record.get("helper_sha256") != helper_sha256(root)
        or record.get("verdict") != verdict
    ):
        raise GateError(f"{kind} promotion record contract mismatch")
    result_relative = Path(str(record.get("result_path", "")))
    if result_relative.is_absolute() or ".." in result_relative.parts:
        raise GateError(f"{kind} promotion result path is unsafe")
    result_path = (root / result_relative).resolve()
    run_root = (root / RUN_ROOT).resolve()
    if not result_path.is_relative_to(run_root):
        raise GateError(f"{kind} promotion result is outside private runs")
    require_sha(
        result_path,
        str(record.get("result_sha256", "")),
        f"{kind} promotion result",
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("schema") != SCHEMA or result.get("mode") != mode:
        raise GateError(f"{kind} promotion result schema or mode mismatch")
    if result.get("target") != TARGET or result.get("verdict") != verdict:
        raise GateError(f"{kind} promotion result target or verdict mismatch")
    if kind == "connected":
        if result.get("device_writes") is not False:
            raise GateError("connected promotion result records a device write")
    else:
        capture = result.get("capture", {})
        if (
            capture.get("success") is not True
            or capture.get("cleanup_verified") is not True
            or capture.get("parser_stream_identity_match") is not True
            or capture.get("parser", {}).get("marker", {}).get("classification")
            != "MARKER_FAMILY_ABSENT"
        ):
            raise GateError("oracle promotion result does not prove shape and cleanup")
        consumed_path = root / ORACLE_CONSUMED_STATE
        if consumed_path.is_symlink() or not consumed_path.is_file():
            raise GateError("oracle promotion has no one-shot consumed record")
        try:
            consumed = json.loads(consumed_path.read_text(encoding="utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise GateError("oracle consumed record is invalid JSON") from exc
        expected_run_dir = str(result_path.parent.relative_to(root))
        if (
            consumed.get("schema") != "s22plus_fyg8_r4w1a_oracle_consumed_v1"
            or consumed.get("target") != TARGET
            or consumed.get("helper_sha256") != helper_sha256(root)
            or consumed.get("reason") != "bugreport_capture_start"
            or consumed.get("run_dir") != expected_run_dir
        ):
            raise GateError("oracle promotion and consumed record do not name the same run")
    return common.sha256_file(path)


def create_pass_record(root: Path, kind: str, result_path: Path, verdict: str) -> str:
    contracts = {
        "connected": (CONNECTED_PASS_STATE, "s22plus_fyg8_r4w1a_connected_pass_v3"),
        "oracle": (ORACLE_PASS_STATE, "s22plus_fyg8_r4w1a_oracle_pass_v1"),
    }
    if kind not in contracts:
        raise GateError(f"unknown promotion-record kind: {kind}")
    relative, schema = contracts[kind]
    resolved = result_path.resolve()
    if not resolved.is_relative_to((root / RUN_ROOT).resolve()):
        raise GateError("promotion result is outside private runs")
    durable_create_json(
        root / relative,
        {
            "schema": schema,
            "target": TARGET,
            "created_at_utc": common.utc_now(),
            "helper_sha256": helper_sha256(root),
            "result_path": str(resolved.relative_to(root)),
            "result_sha256": common.sha256_file(resolved),
            "verdict": verdict,
        },
    )
    return validate_pass_record(root, kind)


def active_policy(root: Path, *, oracle_only: bool) -> bool:
    try:
        connected_pass_sha256 = validate_pass_record(root, "connected")
        oracle_pass_sha256 = None if oracle_only else validate_pass_record(root, "oracle")
    except (GateError, OSError, ValueError, json.JSONDecodeError):
        return False
    text = (root / "AGENTS.md").read_text(encoding="utf-8")
    sentinel = ORACLE_ACTIVE_SENTINEL if oracle_only else ACTIVE_SENTINEL
    marker = ORACLE_POLICY_MARKER if oracle_only else POLICY_MARKER
    token = ORACLE_ACK_TOKEN if oracle_only else LIVE_ACK_TOKEN
    active_line = re.compile(rf"(?m)^\s*`?{re.escape(sentinel)}`?\s*$")
    required = (
        marker,
        str(SCRIPT_RELATIVE),
        helper_sha256(root),
        token,
        EXPECTED_CANDIDATE_BOOT_SHA256,
        EXPECTED_CANDIDATE_AP_SHA256,
        EXPECTED_ORACLE_SHA256,
        common.EXPECTED_MAGISK_AP_SHA256,
        str(CONNECTED_PASS_STATE),
        connected_pass_sha256,
    )
    if not oracle_only:
        required += (
            ROLLBACK_ACK_TOKEN,
            common.EXPECTED_STOCK_AP_SHA256,
            str(ORACLE_PASS_STATE),
            str(oracle_pass_sha256),
        )
    return bool(active_line.search(text)) and all(item in text for item in required)


def verify_policy_draft(root: Path) -> dict[str, Any]:
    path = root / POLICY_DRAFT
    if not path.is_file():
        raise GateError("R4W1-A policy draft missing")
    text = path.read_text(encoding="utf-8")
    if "DRAFT_INACTIVE" not in text:
        raise GateError("R4W1-A policy draft is not explicitly inactive")
    source_sha = helper_sha256(root)
    required = (
        POLICY_MARKER,
        ORACLE_POLICY_MARKER,
        str(SCRIPT_RELATIVE),
        source_sha,
        EXPECTED_LIVE_TEST_SHA256,
        LIVE_ACK_TOKEN,
        CONNECTED_ACK_TOKEN,
        ORACLE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        EXPECTED_CANDIDATE_BOOT_SHA256,
        EXPECTED_CANDIDATE_AP_SHA256,
        EXPECTED_ORACLE_SHA256,
        common.EXPECTED_MAGISK_AP_SHA256,
        common.EXPECTED_STOCK_AP_SHA256,
        str(CONNECTED_PASS_STATE),
        str(ORACLE_CONSUMED_STATE),
        str(ORACLE_PASS_STATE),
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise GateError(f"R4W1-A policy draft missing pins: {missing}")
    return {
        "path": str(POLICY_DRAFT),
        "sha256": common.sha256_file(path),
        "current_source_sha256": source_sha,
        "oracle_policy_active": active_policy(root, oracle_only=True),
        "candidate_policy_active": active_policy(root, oracle_only=False),
    }


def consumed_state_path(root: Path) -> Path:
    return root / CONSUMED_STATE


def ensure_not_consumed(root: Path) -> None:
    path = consumed_state_path(root)
    if path.exists():
        raise GateError(f"R4W1-A one-shot exception already consumed: {path}")


def consume_exception(root: Path, run_dir: Path) -> None:
    ensure_not_consumed(root)
    common.durable_write_json(
        consumed_state_path(root),
        {
            "schema": "s22plus_fyg8_r4w1a_consumed_state_v1",
            "consumed_at_utc": common.utc_now(),
            "reason": "candidate_flash_start",
            "run_dir": str(run_dir.relative_to(root)),
            "candidate_ap_sha256": EXPECTED_CANDIDATE_AP_SHA256,
        },
    )


def ensure_oracle_not_consumed(root: Path) -> None:
    path = root / ORACLE_CONSUMED_STATE
    if path.exists() or path.is_symlink():
        raise GateError(f"R4W1-A oracle dry-run already consumed: {path}")


def consume_oracle_exception(root: Path, run_dir: Path) -> None:
    ensure_oracle_not_consumed(root)
    durable_create_json(
        root / ORACLE_CONSUMED_STATE,
        {
            "schema": "s22plus_fyg8_r4w1a_oracle_consumed_v1",
            "target": TARGET,
            "consumed_at_utc": common.utc_now(),
            "reason": "bugreport_capture_start",
            "run_dir": str(run_dir.relative_to(root)),
            "helper_sha256": helper_sha256(root),
        },
    )


def allocate_run_dir(root: Path, mode: str, requested: Path | None = None) -> Path:
    if requested is not None:
        path = resolve(root, requested)
        path.mkdir(parents=True, exist_ok=False)
        return path
    base = root / RUN_ROOT / f"s22plus_fyg8_r4w1a_{mode}_{common.utc_stamp()}"
    for suffix in range(100):
        path = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            path.mkdir(parents=True, exist_ok=False)
            return path
        except FileExistsError:
            continue
    raise GateError("could not allocate a unique R4W1-A run directory")


def write_bytes_fsync(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def remote_exec_out(
    serial: str, command: str, *, root: bool = False, timeout: float = 60.0
) -> subprocess.CompletedProcess[bytes]:
    program = "su" if root else "sh"
    remote = f"{program} -c {shlex.quote(command)}"
    return subprocess.run(
        ["adb", "-s", serial, "exec-out", remote],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def remote_bytes(
    serial: str,
    command: str,
    *,
    root: bool = False,
    timeout: float = 60.0,
    maximum: int | None = None,
) -> bytes:
    result = remote_exec_out(serial, command, root=root, timeout=timeout)
    if result.returncode != 0 or result.stderr:
        raise GateError(f"remote command failed: {command.split()[0]}")
    if maximum is not None and len(result.stdout) > maximum:
        raise GateError(f"remote output exceeds bound: {len(result.stdout)} > {maximum}")
    return result.stdout


def remote_text(
    serial: str, command: str, *, root: bool = False, timeout: float = 60.0
) -> str:
    payload = remote_bytes(serial, command, root=root, timeout=timeout, maximum=1024 * 1024)
    try:
        return payload.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise GateError("remote text output is not UTF-8") from exc


def classify_marker_absence(payload: bytes) -> dict[str, Any]:
    exact_count = payload.count(oracle.EXPECTED_MARKER)
    family_count = payload.count(oracle.MARKER_FAMILY_PREFIX)
    suspicious_tokens = {
        "short_family": payload.count(b"[[S22R4"),
        "stage_name": payload.count(b"S22R4W1"),
        "marker_id": payload.count(b"9ed5923b08c5eedbbdb0aaa6f6a5200c"),
        "phase": payload.count(b"RAMDISK_EXEC_ACCEPTED"),
    }
    minimum = len(oracle.MARKER_FAMILY_PREFIX)
    partial_tail = any(
        payload.endswith(oracle.EXPECTED_MARKER[:length])
        for length in range(minimum, len(oracle.EXPECTED_MARKER))
    )
    partial_head = any(
        payload.startswith(oracle.EXPECTED_MARKER[-length:])
        for length in range(minimum, len(oracle.EXPECTED_MARKER))
    )
    passed = (
        exact_count == 0
        and family_count == 0
        and all(count == 0 for count in suspicious_tokens.values())
        and not partial_tail
        and not partial_head
    )
    return {
        "pass": passed,
        "classification": "MARKER_FAMILY_ABSENT" if passed else "MARKER_CONTAMINATION",
        "exact_count": exact_count,
        "family_count": family_count,
        "suspicious_tokens": suspicious_tokens,
        "partial_at_head": partial_head,
        "partial_at_tail": partial_tail,
    }


def pstore_console_absent(serial: str) -> dict[str, bool]:
    result: dict[str, bool] = {}
    for path in PSTORE_PATHS:
        quoted = shlex.quote(path)
        value = remote_text(serial, f"if test -e {quoted}; then echo present; else echo absent; fi")
        if value not in {"present", "absent"}:
            raise GateError(f"ambiguous pstore existence result: {path}")
        result[path] = value == "absent"
    if not all(result.values()):
        raise GateError(f"pstore console path would shadow /proc/last_kmsg: {result}")
    return result


def connected_preflight(
    root: Path, run_dir: Path, odin: Path
) -> tuple[str, dict[str, Any]]:
    ensure_not_consumed(root)
    serial, baseline = common.current_android()
    devices = common.odin_devices(odin, run_dir / "connected.log", "r4w1a-preflight")
    if devices:
        raise GateError(f"connected preflight requires no Odin endpoint: {devices}")
    state = remote_text(
        serial,
        "printf 'osrelease='; cat /proc/sys/kernel/osrelease; "
        "grep '^sec_log_buf ' /proc/modules; "
        f"test -L {shlex.quote(EXPECTED_BIND)} && echo bind_ok=1 || echo bind_ok=0; "
        "stat -c '%n:%s:%a' /proc/ap_klog /proc/last_kmsg",
        root=True,
        timeout=45,
    )
    required = (
        f"osrelease={common.EXPECTED_RELEASE}",
        "sec_log_buf ",
        " Live ",
        "bind_ok=1",
        "/proc/ap_klog:",
        "/proc/last_kmsg:",
    )
    missing = [item for item in required if item not in state]
    if missing:
        raise GateError(f"sec_log_buf baseline mismatch: {missing}")
    ap_klog = remote_bytes(
        serial,
        "cat /proc/ap_klog",
        root=True,
        timeout=90,
        maximum=MAX_SNAPSHOT_BYTES,
    )
    last_kmsg = remote_bytes(
        serial,
        "cat /proc/last_kmsg",
        root=True,
        timeout=90,
        maximum=MAX_SNAPSHOT_BYTES,
    )
    if not ap_klog or not last_kmsg:
        raise GateError("sec_log_buf baseline snapshot is empty")
    ap_result = classify_marker_absence(ap_klog)
    last_result = classify_marker_absence(last_kmsg)
    if not ap_result["pass"] or not last_result["pass"]:
        raise GateError("R4W1 marker contamination in baseline observer snapshots")
    write_bytes_fsync(run_dir / "baseline_ap_klog.bin", ap_klog)
    write_bytes_fsync(run_dir / "baseline_last_kmsg.bin", last_kmsg)
    summary = {
        "target": TARGET,
        "android": baseline,
        "sec_log_buf_live": True,
        "bind": EXPECTED_BIND,
        "ap_klog": {
            "bytes": len(ap_klog),
            "sha256": sha256_bytes(ap_klog),
            "marker": ap_result,
            "read_to_eof": True,
        },
        "last_kmsg": {
            "bytes": len(last_kmsg),
            "sha256": sha256_bytes(last_kmsg),
            "marker": last_result,
            "read_to_eof": True,
        },
        "no_odin_endpoint": True,
        "one_shot_consumed": False,
        "device_writes": False,
    }
    common.durable_write_json(run_dir / "connected_preflight.json", summary)
    return serial, summary


def parse_inventory_paths(payload: bytes) -> list[str]:
    if not payload:
        return []
    if not payload.endswith(b"\0"):
        raise GateError("bugreport inventory is not NUL terminated")
    paths: list[str] = []
    for raw in payload[:-1].split(b"\0"):
        try:
            path = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise GateError("bugreport inventory path is not UTF-8") from exc
        if not REMOTE_PATH_RE.fullmatch(path):
            raise GateError(f"unsafe or unexpected bugreport path: {path!r}")
        if path in paths:
            raise GateError(f"duplicate bugreport inventory path: {path}")
        paths.append(path)
    return sorted(paths)


def remote_inventory(serial: str) -> dict[str, dict[str, Any]]:
    payload = remote_bytes(
        serial,
        f"test -d {REMOTE_BUGREPORT_ROOT} && "
        f"find {REMOTE_BUGREPORT_ROOT} -mindepth 1 -maxdepth 1 -print0",
        timeout=30,
        maximum=1024 * 1024,
    )
    inventory: dict[str, dict[str, Any]] = {}
    for path in parse_inventory_paths(payload):
        quoted = shlex.quote(path)
        output = remote_text(
            serial,
            f"test ! -L {quoted} && test -f {quoted} && "
            f"stat -c '%d:%i:%s:%Y:%f' {quoted}",
        )
        match = STAT_RE.fullmatch(output)
        if match is None:
            raise GateError(f"malformed bugreport stat output: {path}")
        values = match.groupdict()
        inventory[path] = {
            "device": int(values["device"]),
            "inode": int(values["inode"]),
            "size": int(values["size"]),
            "mtime": int(values["mtime"]),
            "mode": values["mode"].lower(),
        }
    return inventory


def compare_inventories(
    before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    missing = sorted(set(before) - set(after))
    added = sorted(set(after) - set(before))
    changed = sorted(path for path in set(before) & set(after) if before[path] != after[path])
    return {
        "missing_preexisting": missing,
        "changed_preexisting": changed,
        "added": added,
        "preexisting_unchanged": not missing and not changed,
    }


def remote_file_sha256(serial: str, path: str) -> str:
    quoted = shlex.quote(path)
    output = remote_text(serial, f"sha256sum {quoted}", timeout=120)
    fields = output.split()
    if not fields or not re.fullmatch(r"[0-9a-f]{64}", fields[0]):
        raise GateError("malformed remote bugreport SHA256")
    return fields[0]


def cleanup_exact_remote_file(
    serial: str, path: str, identity: dict[str, Any], sha256: str
) -> None:
    if not REMOTE_PATH_RE.fullmatch(path):
        raise GateError("cleanup path is outside the strict bugreport namespace")
    quoted = shlex.quote(path)
    expected_stat = (
        f"{identity['device']}:{identity['inode']}:{identity['size']}:"
        f"{identity['mtime']}:{identity['mode']}"
    )
    command = (
        f"test ! -L {quoted} && test -f {quoted} && "
        f"test \"$(stat -c '%d:%i:%s:%Y:%f' {quoted})\" = {shlex.quote(expected_stat)} && "
        f"test \"$(sha256sum {quoted} | cut -d' ' -f1)\" = {shlex.quote(sha256)} && "
        f"rm {quoted} && test ! -e {quoted}"
    )
    result = remote_exec_out(serial, command, timeout=120)
    if result.returncode != 0 or result.stdout or result.stderr:
        raise GateError("exact bugreport cleanup failed")


def kill_process_group(process: subprocess.Popen[Any]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def stream_bugreport(
    serial: str, output: Path, stderr_path: Path, timeout: float
) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    with output.open("xb") as stdout_stream, stderr_path.open("xb") as stderr_stream:
        process = subprocess.Popen(
            ["adb", "-s", serial, "exec-out", "bugreportz", "-s"],
            stdin=subprocess.DEVNULL,
            stdout=stdout_stream,
            stderr=stderr_stream,
            start_new_session=True,
        )
        timed_out = False
        too_large = False
        while process.poll() is None:
            stdout_stream.flush()
            stderr_stream.flush()
            if os.fstat(stdout_stream.fileno()).st_size > oracle.MAX_ARCHIVE_SIZE:
                too_large = True
                kill_process_group(process)
                break
            if os.fstat(stderr_stream.fileno()).st_size > MAX_BUGREPORT_STDERR:
                too_large = True
                kill_process_group(process)
                break
            if time.monotonic() >= deadline:
                timed_out = True
                kill_process_group(process)
                break
            time.sleep(0.1)
        try:
            returncode = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            kill_process_group(process)
            returncode = process.wait(timeout=5)
        stdout_stream.flush()
        stderr_stream.flush()
        os.fsync(stdout_stream.fileno())
        os.fsync(stderr_stream.fileno())
        output_size = os.fstat(stdout_stream.fileno()).st_size
        stderr_size = os.fstat(stderr_stream.fileno()).st_size
    directory_fd = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    if timed_out:
        raise GateError("bugreportz stream timed out")
    if too_large:
        raise GateError("bugreportz output exceeded a fixed size bound")
    if returncode != 0:
        raise GateError(f"bugreportz stream failed rc={returncode}")
    if output_size == 0 or output_size > oracle.MAX_ARCHIVE_SIZE:
        raise GateError(f"bugreportz stream size invalid: {output_size}")
    if stderr_size:
        raise GateError("bugreportz emitted unexpected stderr")
    return {
        "argv": ["adb", "-s", "<S22_SERIAL_REDACTED>", "exec-out", "bugreportz", "-s"],
        "returncode": returncode,
        "bytes": output_size,
        "sha256": common.sha256_file(output),
        "stderr_bytes": stderr_size,
        "read_to_eof": True,
    }


def capture_oracle(
    serial: str,
    run_dir: Path,
    *,
    expectation: str,
    timeout: float,
) -> dict[str, Any]:
    before = remote_inventory(serial)
    common.durable_write_json(run_dir / "bugreports_before.json", before)
    host_zip = run_dir / "bugreport.zip"
    stderr_path = run_dir / "bugreport.stderr"
    result: dict[str, Any] = {
        "expectation": expectation,
        "before": before,
        "stream": None,
        "after": None,
        "inventory_delta": None,
        "remote_created_file": None,
        "parser": None,
        "parser_stream_identity_match": False,
        "cleanup_attempted": False,
        "cleanup_verified": False,
        "success": False,
        "errors": [],
    }
    try:
        result["stream"] = stream_bugreport(serial, host_zip, stderr_path, timeout)
    except (GateError, OSError, subprocess.SubprocessError) as exc:
        result["errors"].append(str(exc))

    try:
        after = remote_inventory(serial)
        result["after"] = after
        common.durable_write_json(run_dir / "bugreports_after.json", after)
        delta = compare_inventories(before, after)
        result["inventory_delta"] = delta
        if not delta["preexisting_unchanged"]:
            result["errors"].append("preexisting /bugreports entries changed or disappeared")
        if len(delta["added"]) != 1:
            result["errors"].append(
                f"expected exactly one created bugreport file, got {delta['added']}"
            )
        else:
            path = delta["added"][0]
            identity = after[path]
            remote_sha = remote_file_sha256(serial, path)
            result["remote_created_file"] = {
                "path": path,
                "identity": identity,
                "sha256": remote_sha,
            }
            remote_matches_stream = False
            if result["stream"] is not None:
                if identity["size"] != result["stream"]["bytes"]:
                    result["errors"].append("remote and streamed bugreport sizes differ")
                elif remote_sha != result["stream"]["sha256"]:
                    result["errors"].append("remote and streamed bugreport SHA256 differ")
                else:
                    remote_matches_stream = True
            if host_zip.is_file() and result["stream"] is not None:
                try:
                    result["parser"] = oracle.parse_bugreport(host_zip, expectation)
                    parser_input = result["parser"].get("input", {})
                    result["parser_stream_identity_match"] = (
                        parser_input.get("sha256") == result["stream"]["sha256"]
                        and parser_input.get("size") == result["stream"]["bytes"]
                    )
                    if not result["parser_stream_identity_match"]:
                        result["errors"].append(
                            "parsed host ZIP identity does not match streamed bytes"
                        )
                except (oracle.OracleError, OSError) as exc:
                    result["errors"].append(f"oracle parser failed: {exc}")
            if remote_matches_stream:
                result["cleanup_attempted"] = True
                try:
                    cleanup_exact_remote_file(serial, path, identity, remote_sha)
                    final = remote_inventory(serial)
                    common.durable_write_json(run_dir / "bugreports_final.json", final)
                    result["cleanup_verified"] = final == before
                    if not result["cleanup_verified"]:
                        result["errors"].append("post-cleanup inventory does not equal baseline")
                except (GateError, OSError, subprocess.SubprocessError) as exc:
                    result["errors"].append(f"cleanup failed: {exc}")
            else:
                result["errors"].append(
                    "created file not deleted because host/remote identity was not proven"
                )
    except (GateError, OSError, subprocess.SubprocessError) as exc:
        result["errors"].append(f"post-capture inventory failed: {exc}")

    result["success"] = (
        not result["errors"]
        and result["stream"] is not None
        and result["parser"] is not None
        and result["parser_stream_identity_match"] is True
        and result["cleanup_verified"] is True
    )
    common.durable_write_json(run_dir / "oracle_capture.json", result)
    return result


def append_all_no_flash_events(
    timeline_path: Path, timeline: list[dict[str, str]], start_at: int = 0
) -> None:
    for name in TIMELINE_NAMES[start_at:]:
        common.append_event(timeline_path, timeline, name)


def connected_dry_run(
    root: Path,
    odin: Path,
    artifacts: dict[str, Any],
    requested: Path | None,
    ack: str | None,
) -> int:
    if ack != CONNECTED_ACK_TOKEN:
        raise GateError("R4W1-A connected dry-run acknowledgement mismatch")
    if (root / CONNECTED_PASS_STATE).exists():
        raise GateError("R4W1-A connected dry-run PASS already exists")
    run_dir = allocate_run_dir(root, "connected_dry_run", requested)
    timeline: list[dict[str, str]] = []
    timeline_path = run_dir / "timeline.json"
    common.append_event(timeline_path, timeline, "live_session_start")
    _, baseline = connected_preflight(root, run_dir, odin)
    append_all_no_flash_events(timeline_path, timeline, 1)
    result = {
        "schema": SCHEMA,
        "mode": "connected-dry-run",
        "target": TARGET,
        "artifacts": artifacts,
        "baseline": baseline,
        "timeline_phase_semantics": {
            "candidate_flash_start": "no-candidate-flash-read-only-dry-run",
            "candidate_flash_done": "no-candidate-flash-read-only-dry-run",
            "candidate_boot_ready": "baseline-android-remained-ready",
            "rollback_flash_start": "no-rollback-flash-read-only-dry-run",
            "rollback_flash_done": "no-rollback-flash-read-only-dry-run",
            "rollback_boot_ready": "baseline-android-remained-ready",
        },
        "device_writes": False,
        "verdict": "PASS_R4W1A_CONNECTED_IDENTITY_DRY_RUN_READ_ONLY",
    }
    result_path = run_dir / "result.json"
    common.durable_write_json(result_path, result)
    promotion_sha256 = create_pass_record(
        root, "connected", result_path, result["verdict"]
    )
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "verdict": result["verdict"],
                "promotion_record_sha256": promotion_sha256,
            },
            indent=2,
        )
    )
    return 0


def oracle_dry_run(
    root: Path, args: argparse.Namespace, artifacts: dict[str, Any]
) -> int:
    if not active_policy(root, oracle_only=True):
        raise GateError("R4W1-A oracle dry-run policy is inactive")
    if args.ack != ORACLE_ACK_TOKEN:
        raise GateError("R4W1-A oracle dry-run acknowledgement mismatch")
    ensure_oracle_not_consumed(root)
    if (root / ORACLE_PASS_STATE).exists():
        raise GateError("R4W1-A oracle dry-run PASS already exists")
    run_dir = allocate_run_dir(root, "oracle_dry_run", args.run_dir)
    timeline: list[dict[str, str]] = []
    timeline_path = run_dir / "timeline.json"
    common.append_event(timeline_path, timeline, "live_session_start")
    serial, baseline = connected_preflight(root, run_dir, resolve(root, args.odin))
    pstore = pstore_console_absent(serial)
    consume_oracle_exception(root, run_dir)
    common.append_event(timeline_path, timeline, "candidate_flash_start")
    capture = capture_oracle(
        serial,
        run_dir,
        expectation="absent",
        timeout=args.bugreport_wait_sec,
    )
    common.append_event(timeline_path, timeline, "candidate_flash_done")
    _, final = common.current_android()
    common.append_event(timeline_path, timeline, "candidate_boot_ready")
    common.append_event(timeline_path, timeline, "rollback_flash_start")
    common.append_event(timeline_path, timeline, "rollback_flash_done")
    common.append_event(timeline_path, timeline, "rollback_boot_ready")
    devices = common.odin_devices(
        resolve(root, args.odin), run_dir / "oracle.log", "r4w1a-oracle-final"
    )
    if devices:
        raise GateError(f"Odin endpoint appeared during oracle dry-run: {devices}")
    common.append_event(timeline_path, timeline, "live_session_end")
    verdict = (
        "PASS_R4W1A_ORACLE_DRY_RUN_EXACT_ZIP_AND_CLEANUP"
        if capture["success"]
        else "FAIL_R4W1A_ORACLE_DRY_RUN_CLEANUP_OR_SHAPE"
    )
    result = {
        "schema": SCHEMA,
        "mode": "oracle-dry-run",
        "target": TARGET,
        "artifacts": artifacts,
        "baseline": baseline,
        "pstore_console_absent": pstore,
        "capture": capture,
        "final": final,
        "timeline_phase_semantics": {
            "candidate_flash_start": "zero-flash-one-bugreport-capture-start",
            "candidate_flash_done": "zero-flash-one-bugreport-capture-finished",
            "candidate_boot_ready": "baseline-android-revalidated",
            "rollback_flash_start": "zero-flash-no-rollback-required",
            "rollback_flash_done": "zero-flash-no-rollback-required",
            "rollback_boot_ready": "baseline-android-revalidated",
        },
        "verdict": verdict,
    }
    result_path = run_dir / "result.json"
    common.durable_write_json(result_path, result)
    promotion_sha256 = None
    if capture["success"]:
        promotion_sha256 = create_pass_record(root, "oracle", result_path, verdict)
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "verdict": verdict,
                "promotion_record_sha256": promotion_sha256,
            },
            indent=2,
        )
    )
    return 0 if capture["success"] else 40


def candidate_observation(args: argparse.Namespace, run_dir: Path) -> dict[str, Any]:
    serial, samples, error = common.wait_candidate_android(
        args.candidate_wait_sec, args.sample_count, args.sample_interval_sec
    )
    result: dict[str, Any] = {
        "serial_present": serial is not None,
        "samples": samples,
        "observation": error,
        "pstore_console_absent": None,
        "oracle_capture": None,
    }
    if serial is not None and samples:
        try:
            result["pstore_console_absent"] = pstore_console_absent(serial)
            result["oracle_capture"] = capture_oracle(
                serial,
                run_dir,
                expectation="exact",
                timeout=args.bugreport_wait_sec,
            )
        except (GateError, OSError, subprocess.SubprocessError) as exc:
            result["oracle_capture"] = {
                "success": False,
                "errors": [str(exc)],
                "cleanup_verified": False,
            }
    return result


def classify_live_verdict(
    rollback_target: str,
    rollback_verdict: str,
    rollback_rc: int,
    candidate_transfer_ok: bool,
    samples: list[dict[str, str]],
    marker_proved: bool,
) -> tuple[str, int]:
    if rollback_target != "magisk":
        return rollback_verdict, rollback_rc
    if samples and marker_proved:
        return "PASS_R4W1A_ANDROID_INIT_EXEC_WITNESS_RETAINED_AND_ROLLED_BACK", 0
    if not samples and marker_proved:
        return "PROOF_R4W1A_INIT_EXEC_ACCEPTED_NO_ANDROID_MILESTONE", 42
    if not candidate_transfer_ok:
        return "NO_PROOF_R4W1A_CANDIDATE_TRANSFER_FAILED_MAGISK_ROLLED_BACK", 31
    if samples:
        return "NO_PROOF_R4W1A_ANDROID_VIABLE_WITNESS_NOT_RECOVERED", 41
    return "NO_PROOF_NO_R4W1A_ANDROID_OR_RETAINED_WITNESS", 32


def collect_rollback_last_kmsg(serial: str, run_dir: Path) -> dict[str, Any]:
    first = remote_bytes(
        serial, "cat /proc/last_kmsg", root=True, timeout=90, maximum=MAX_SNAPSHOT_BYTES
    )
    time.sleep(0.25)
    second = remote_bytes(
        serial, "cat /proc/last_kmsg", root=True, timeout=90, maximum=MAX_SNAPSHOT_BYTES
    )
    write_bytes_fsync(run_dir / "rollback_last_kmsg_1.bin", first)
    write_bytes_fsync(run_dir / "rollback_last_kmsg_2.bin", second)
    result = {
        "first_bytes": len(first),
        "second_bytes": len(second),
        "first_sha256": sha256_bytes(first),
        "second_sha256": sha256_bytes(second),
        "byte_identical": first == second,
        "first_read_to_eof": True,
        "second_read_to_eof": True,
        "load_bearing": False,
    }
    common.durable_write_json(run_dir / "rollback_last_kmsg.json", result)
    return result


def live_run(root: Path, args: argparse.Namespace, artifacts: dict[str, Any]) -> int:
    if not active_policy(root, oracle_only=False):
        raise GateError("R4W1-A candidate live policy is inactive")
    if args.ack != LIVE_ACK_TOKEN:
        raise GateError("R4W1-A live acknowledgement mismatch")
    ensure_not_consumed(root)
    odin = resolve(root, args.odin)
    run_dir = allocate_run_dir(root, "live", args.run_dir)
    timeline: list[dict[str, str]] = []
    timeline_path = run_dir / "timeline.json"
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "mode": "live",
        "target": TARGET,
        "artifacts": artifacts,
        "candidate_flash_attempted": False,
        "candidate_transfer_ok": False,
        "candidate_observation": None,
        "verdict": "INCOMPLETE",
    }
    common.append_event(timeline_path, timeline, "live_session_start")
    serial, baseline = connected_preflight(root, run_dir, odin)
    result["baseline"] = baseline
    common.durable_write_json(run_dir / "result.json", result)

    reboot = common.run(["adb", "-s", serial, "reboot", "download"], timeout=20)
    if reboot.returncode != 0:
        raise GateError("Android failed to request Download mode")
    device = common.wait_for_odin(
        odin, run_dir / "live.log", "r4w1a-candidate", args.download_wait_sec
    )
    if device is None:
        raise GateError("Download mode did not appear before R4W1-A candidate flash")
    common.append_event(timeline_path, timeline, "candidate_flash_start")
    consume_exception(root, run_dir)
    result["candidate_flash_attempted"] = True
    common.durable_write_json(run_dir / "result.json", result)
    try:
        common.flash_exact(
            odin,
            resolve(root, args.candidate_ap),
            device,
            run_dir / "live.log",
            "r4w1a-candidate",
        )
        result["candidate_transfer_ok"] = True
    except GateError as exc:
        result["candidate_transfer_error"] = str(exc)
    common.append_event(timeline_path, timeline, "candidate_flash_done")
    common.durable_write_json(run_dir / "result.json", result)

    observation: dict[str, Any] = {
        "serial_present": False,
        "samples": [],
        "oracle_capture": None,
        "observation": "candidate transfer failed",
    }
    if result["candidate_transfer_ok"] and common.wait_odin_absent(
        odin, run_dir / "live.log", "r4w1a-candidate-disconnect", args.disconnect_wait_sec
    ):
        observation = candidate_observation(args, run_dir)
    elif result["candidate_transfer_ok"]:
        observation["observation"] = "original Odin endpoint stayed present"
    result["candidate_observation"] = observation
    common.append_event(timeline_path, timeline, "candidate_boot_ready")
    common.durable_write_json(run_dir / "result.json", result)

    existing = common.odin_devices(odin, run_dir / "live.log", "r4w1a-pre-rollback")
    if len(existing) > 1:
        raise GateError(f"ambiguous Odin endpoints before rollback: {existing}")
    rollback_device = existing[0] if existing else None
    if rollback_device is None:
        common.request_download_if_android()
        print(
            "R4W1-A observation is complete. If Download mode does not appear "
            "automatically, enter physical Download mode for mandatory rollback.",
            flush=True,
        )
        rollback_device = common.wait_for_odin(
            odin,
            run_dir / "live.log",
            "r4w1a-mandatory-rollback",
            args.manual_wait_sec,
        )
    if rollback_device is None:
        result["verdict"] = "FAIL_R4W1A_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED"
        result["timeline_phase_semantics"] = {
            "rollback_flash_start": "bounded wait closed; no rollback flash started",
            "rollback_flash_done": "no rollback flash occurred",
            "rollback_boot_ready": "rollback Android not observed",
            "live_session_end": "recovery required through rollback-from-download mode",
        }
        append_all_no_flash_events(timeline_path, timeline, 4)
        common.durable_write_json(run_dir / "result.json", result)
        return 20

    common.append_event(timeline_path, timeline, "rollback_flash_start")
    rollback_target = common.flash_rollback(root, odin, rollback_device, run_dir / "live.log")
    common.append_event(timeline_path, timeline, "rollback_flash_done")
    final, rollback_verdict, rollback_rc = common.wait_final_android(
        rollback_target, args.android_wait_sec, odin, run_dir / "live.log"
    )
    common.append_event(timeline_path, timeline, "rollback_boot_ready")
    rollback_capture = None
    if rollback_target == "magisk":
        final_serial = common.adb_serial()
        rollback_capture = collect_rollback_last_kmsg(final_serial, run_dir)
    capture = observation.get("oracle_capture") or {}
    marker_proved = bool(capture.get("success"))
    verdict, rc = classify_live_verdict(
        rollback_target,
        rollback_verdict,
        rollback_rc,
        bool(result["candidate_transfer_ok"]),
        observation.get("samples", []),
        marker_proved,
    )
    result.update(
        {
            "rollback_target": rollback_target,
            "final": final,
            "rollback_last_kmsg": rollback_capture,
            "verdict": verdict,
        }
    )
    common.append_event(timeline_path, timeline, "live_session_end")
    common.durable_write_json(run_dir / "result.json", result)
    print(json.dumps({"run_dir": str(run_dir), "verdict": verdict}, indent=2))
    return rc


def rollback_from_download(root: Path, args: argparse.Namespace) -> int:
    if not active_policy(root, oracle_only=False):
        raise GateError("R4W1-A rollback policy is inactive")
    if args.ack != ROLLBACK_ACK_TOKEN:
        raise GateError("R4W1-A rollback acknowledgement mismatch")
    odin = resolve(root, args.odin)
    run_dir = allocate_run_dir(root, "rollback", args.run_dir)
    timeline: list[dict[str, str]] = []
    timeline_path = run_dir / "timeline.json"
    for name in TIMELINE_NAMES[:4]:
        common.append_event(timeline_path, timeline, name)
    devices = common.odin_devices(odin, run_dir / "rollback.log", "r4w1a-recovery")
    if len(devices) != 1:
        raise GateError(f"rollback requires exactly one Odin endpoint, got {devices}")
    common.append_event(timeline_path, timeline, "rollback_flash_start")
    target = common.flash_rollback(root, odin, devices[0], run_dir / "rollback.log")
    common.append_event(timeline_path, timeline, "rollback_flash_done")
    final, verdict, rc = common.wait_final_android(
        target, args.android_wait_sec, odin, run_dir / "rollback.log"
    )
    if target == "magisk":
        verdict = "PASS_R4W1A_MAGISK_ROLLBACK_FROM_DOWNLOAD"
    common.append_event(timeline_path, timeline, "rollback_boot_ready")
    common.append_event(timeline_path, timeline, "live_session_end")
    result = {
        "schema": SCHEMA,
        "mode": "rollback-from-download",
        "timeline_phase_semantics": {
            "candidate_flash_start": "recovery-only-session-no-candidate-flash",
            "candidate_flash_done": "recovery-only-session-no-candidate-flash",
            "candidate_boot_ready": "operator-entered-download-before-session",
        },
        "rollback_target": target,
        "final": final,
        "verdict": verdict,
        "exit_code": rc,
    }
    common.durable_write_json(run_dir / "result.json", result)
    print(json.dumps({"run_dir": str(run_dir), "verdict": verdict}, indent=2))
    return rc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline-check", action="store_true")
    modes.add_argument("--connected-dry-run", action="store_true")
    modes.add_argument("--oracle-dry-run", action="store_true")
    modes.add_argument("--live", action="store_true")
    modes.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--ack")
    parser.add_argument("--candidate-boot", type=Path, default=DEFAULT_CANDIDATE_BOOT)
    parser.add_argument("--candidate-ap", type=Path, default=DEFAULT_CANDIDATE_AP)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--odin", type=Path, default=common.DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--download-wait-sec", type=int, default=120)
    parser.add_argument("--disconnect-wait-sec", type=int, default=30)
    parser.add_argument("--candidate-wait-sec", type=int, default=300)
    parser.add_argument("--bugreport-wait-sec", type=int, default=600)
    parser.add_argument("--manual-wait-sec", type=int, default=300)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    parser.add_argument("--sample-count", type=int, default=3)
    parser.add_argument("--sample-interval-sec", type=float, default=5.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = common.repo_root()
    try:
        if not 1 <= args.sample_count <= 5:
            raise GateError("sample count must be between 1 and 5")
        for label, value, maximum in (
            ("download wait", args.download_wait_sec, 300),
            ("disconnect wait", args.disconnect_wait_sec, 120),
            ("candidate wait", args.candidate_wait_sec, 600),
            ("bugreport wait", args.bugreport_wait_sec, 900),
            ("manual wait", args.manual_wait_sec, 600),
            ("Android wait", args.android_wait_sec, 600),
        ):
            if value < 1 or value > maximum:
                raise GateError(f"{label} must be between 1 and {maximum} seconds")
        odin = resolve(root, args.odin)
        artifacts = verify_artifacts(
            root,
            resolve(root, args.candidate_boot),
            resolve(root, args.candidate_ap),
            resolve(root, args.manifest),
            odin,
        )
        draft = verify_policy_draft(root)
        if args.offline_check:
            print(
                json.dumps(
                    {
                        "schema": SCHEMA,
                        "artifacts": artifacts,
                        "policy": draft,
                        "device_contact": False,
                        "device_write": False,
                        "flash": False,
                        "verdict": "PASS_R4W1A_LIVE_HELPER_OFFLINE_CHECK",
                    },
                    indent=2,
                )
            )
            return 0
        if args.connected_dry_run:
            return connected_dry_run(root, odin, artifacts, args.run_dir, args.ack)
        if args.oracle_dry_run:
            return oracle_dry_run(root, args, artifacts)
        if args.rollback_from_download:
            return rollback_from_download(root, args)
        return live_run(root, args, artifacts)
    except (
        GateError,
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"R4W1-A gate error: {common.redact(str(exc))}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
