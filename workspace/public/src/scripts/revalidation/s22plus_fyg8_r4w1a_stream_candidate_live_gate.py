#!/usr/bin/env python3
"""Inactive successor gate for the FYG8 R4W1-A stream-only candidate proof.

This helper consumes the independently qualified A4 baseline evidence and uses
the host ``bugreportz -s`` byte stream as the only marker-oracle artifact.  It
does not promote or modify the consumed v1 oracle run.  Candidate transfer and
rollback remain unavailable until a separate binding AGENTS clause is active
and the operator supplies the exact fresh acknowledgement.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import s22plus_fyg8_r4w1a_live_gate as historical
import s22plus_fyg8_r4w1a_marker_oracle as oracle
import s22plus_fyg8_r4w1a_stream_oracle_qualification as qualification


SCHEMA = "s22plus_fyg8_r4w1a_stream_candidate_live_gate_v2"
TARGET = historical.TARGET
SCRIPT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1a_stream_candidate_live_gate.py"
)
TEST_RELATIVE = Path("tests/test_s22plus_fyg8_r4w1a_stream_candidate_live_gate.py")
POLICY_DRAFT = Path(
    "docs/operations/"
    "S22PLUS_FYG8_R4W1A_STREAM_CANDIDATE_AGENTS_EXCEPTION_DRAFT_2026-07-13.md"
)
POLICY_MARKER = (
    "S22+ FYG8 R4W1-A stream-only retained PID1 witness boot-only live gate"
)
ACTIVE_SENTINEL = "S22PLUS_FYG8_R4W1A_STREAM_CANDIDATE_POLICY_STATE=ACTIVE"
LIVE_ACK_TOKEN = "S22PLUS-FYG8-R4W1A-STREAM-CANDIDATE-LIVE"
ROLLBACK_ACK_TOKEN = "S22PLUS-FYG8-R4W1A-STREAM-MAGISK-ROLLBACK-FROM-DOWNLOAD"

HISTORICAL_HELPER_RELATIVE = historical.SCRIPT_RELATIVE
HISTORICAL_HELPER_SHA256 = (
    "d541397c823b7c6311dbec950dd3a82dc6a5881984b45838c99ffedebc2d3d14"
)
HISTORICAL_TEST_RELATIVE = historical.LIVE_TEST_RELATIVE
HISTORICAL_TEST_SHA256 = (
    "314b3efc9fec555b31bf6b926bcdbe4b34ebe75ad17bf1172d0e3027e52bf145"
)
QUALIFICATION_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1a_stream_oracle_qualification.py"
)
QUALIFICATION_SHA256 = (
    "fa940a5ff225d0d42c7d31214458ebc4625b33be7eb0f5b32ec543342b5bcf3c"
)
QUALIFICATION_TEST_RELATIVE = Path(
    "tests/test_s22plus_fyg8_r4w1a_stream_oracle_qualification.py"
)
QUALIFICATION_TEST_SHA256 = (
    "592e982d70a808e3f6f68429d4b8fb8891e78b2dd476b656c958d208b0e9cbb3"
)
QUALIFICATION_RESULT_RELATIVE = Path(
    "workspace/private/work/s22plus_fyg8_r4w1a_a4/"
    "stream_oracle_qualification.json"
)
QUALIFICATION_RESULT_SHA256 = (
    "077885c4f785760720463763905e4db3453c6e262021524e6fff97700bf6b12a"
)
QUALIFICATION_SCHEMA = "s22plus_fyg8_r4w1a_stream_oracle_qualification_v1"
QUALIFICATION_VERDICT = "PASS_R4W1A_STREAM_ORACLE_EVIDENCE_QUALIFIED_HOST_ONLY"

EXPECTED_CANDIDATE_BOOT_SHA256 = historical.EXPECTED_CANDIDATE_BOOT_SHA256
EXPECTED_CANDIDATE_BOOT_SIZE = historical.EXPECTED_CANDIDATE_BOOT_SIZE
EXPECTED_CANDIDATE_AP_SHA256 = historical.EXPECTED_CANDIDATE_AP_SHA256
EXPECTED_MARKER_ORACLE_SHA256 = historical.EXPECTED_ORACLE_SHA256
EXPECTED_MAGISK_ROLLBACK_AP_SHA256 = historical.common.EXPECTED_MAGISK_AP_SHA256
EXPECTED_STOCK_CLEANUP_AP_SHA256 = historical.common.EXPECTED_STOCK_AP_SHA256

DEFAULT_CANDIDATE_BOOT = historical.DEFAULT_CANDIDATE_BOOT
DEFAULT_CANDIDATE_AP = historical.DEFAULT_CANDIDATE_AP
DEFAULT_MANIFEST = historical.DEFAULT_MANIFEST
CONSUMED_STATE = historical.CONSUMED_STATE
RUN_ROOT = historical.RUN_ROOT
TIMELINE_NAMES = historical.TIMELINE_NAMES

GateError = historical.GateError
common = historical.common


def require_sha(path: Path, expected: str, label: str) -> None:
    historical.require_sha(path, expected, label)


def read_pinned_json(path: Path, expected: str, label: str) -> dict[str, Any]:
    return historical.read_pinned_json(path, expected, label)


def helper_sha256(root: Path) -> str:
    return common.sha256_file(root / SCRIPT_RELATIVE)


def test_sha256(root: Path) -> str:
    return common.sha256_file(root / TEST_RELATIVE)


def verify_a4_qualification(root: Path) -> dict[str, Any]:
    require_sha(
        root / HISTORICAL_HELPER_RELATIVE,
        HISTORICAL_HELPER_SHA256,
        "retired v1 helper",
    )
    require_sha(
        root / HISTORICAL_TEST_RELATIVE,
        HISTORICAL_TEST_SHA256,
        "retired v1 helper tests",
    )
    require_sha(
        root / QUALIFICATION_RELATIVE,
        QUALIFICATION_SHA256,
        "A4 qualification validator",
    )
    require_sha(
        root / QUALIFICATION_TEST_RELATIVE,
        QUALIFICATION_TEST_SHA256,
        "A4 qualification tests",
    )
    pinned = read_pinned_json(
        root / QUALIFICATION_RESULT_RELATIVE,
        QUALIFICATION_RESULT_SHA256,
        "A4 qualification result",
    )
    fresh = qualification.qualify(root)
    if fresh != pinned:
        raise GateError("fresh A4 qualification does not equal the pinned result")
    decision = pinned.get("decision", {})
    safety = pinned.get("safety", {})
    contract = pinned.get("contract", {})
    required = (
        pinned.get("schema") == QUALIFICATION_SCHEMA,
        pinned.get("verdict") == QUALIFICATION_VERDICT,
        pinned.get("target") == TARGET,
        decision.get("baseline_observer_qualified") is True,
        decision.get("second_live_baseline_required") is False,
        decision.get("candidate_clause_design_ready") is True,
        decision.get("candidate_live_authorized") is False,
        decision.get("old_oracle_pass_record_created") is False,
        decision.get("qualification_is_not_retroactive_old_policy_pass") is True,
        contract.get("inventory_unchanged") is True,
        contract.get("remote_cleanup_required") is False,
        contract.get("fresh_parser", {}).get("marker", {}).get("classification")
        == "MARKER_FAMILY_ABSENT",
        safety
        == {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "flash": False,
            "policy_activation": False,
            "promotion_record_created": False,
        },
    )
    if not all(required):
        raise GateError("A4 qualification contract mismatch")
    if (root / historical.ORACLE_PASS_STATE).exists():
        raise GateError("retired v1 oracle PASS must remain absent")
    return {
        "source_sha256": QUALIFICATION_SHA256,
        "test_sha256": QUALIFICATION_TEST_SHA256,
        "result_sha256": QUALIFICATION_RESULT_SHA256,
        "schema": QUALIFICATION_SCHEMA,
        "verdict": QUALIFICATION_VERDICT,
        "second_live_baseline_required": False,
    }


def verify_artifacts(
    root: Path, boot: Path, ap: Path, manifest: Path, odin: Path
) -> dict[str, Any]:
    artifacts = historical.verify_artifacts(root, boot, ap, manifest, odin)
    artifacts["a4_qualification"] = verify_a4_qualification(root)
    artifacts["successor_helper_sha256"] = helper_sha256(root)
    artifacts["successor_test_sha256"] = test_sha256(root)
    return artifacts


def policy_active(root: Path) -> bool:
    try:
        source_sha = helper_sha256(root)
        focused_test_sha = test_sha256(root)
        text = (root / "AGENTS.md").read_text(encoding="utf-8")
    except OSError:
        return False
    active_line = re.compile(rf"(?m)^\s*`?{re.escape(ACTIVE_SENTINEL)}`?\s*$")
    required = (
        POLICY_MARKER,
        str(SCRIPT_RELATIVE),
        source_sha,
        focused_test_sha,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        EXPECTED_CANDIDATE_BOOT_SHA256,
        EXPECTED_CANDIDATE_AP_SHA256,
        EXPECTED_MARKER_ORACLE_SHA256,
        EXPECTED_MAGISK_ROLLBACK_AP_SHA256,
        EXPECTED_STOCK_CLEANUP_AP_SHA256,
        QUALIFICATION_SHA256,
        QUALIFICATION_TEST_SHA256,
        QUALIFICATION_RESULT_SHA256,
        QUALIFICATION_VERDICT,
    )
    return bool(active_line.search(text)) and all(value in text for value in required)


def verify_policy_draft(root: Path) -> dict[str, Any]:
    path = root / POLICY_DRAFT
    if path.is_symlink() or not path.is_file():
        raise GateError("stream-candidate policy draft missing")
    text = path.read_text(encoding="utf-8")
    source_sha = helper_sha256(root)
    focused_test_sha = test_sha256(root)
    required = (
        "DRAFT_INACTIVE",
        POLICY_MARKER,
        ACTIVE_SENTINEL,
        str(SCRIPT_RELATIVE),
        source_sha,
        focused_test_sha,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        EXPECTED_CANDIDATE_BOOT_SHA256,
        EXPECTED_CANDIDATE_AP_SHA256,
        EXPECTED_MARKER_ORACLE_SHA256,
        EXPECTED_MAGISK_ROLLBACK_AP_SHA256,
        EXPECTED_STOCK_CLEANUP_AP_SHA256,
        QUALIFICATION_SHA256,
        QUALIFICATION_TEST_SHA256,
        QUALIFICATION_RESULT_SHA256,
        QUALIFICATION_VERDICT,
    )
    missing = [value for value in required if value not in text]
    if missing:
        raise GateError(f"stream-candidate policy draft missing pins: {missing}")
    return {
        "path": str(POLICY_DRAFT),
        "sha256": common.sha256_file(path),
        "helper_sha256": source_sha,
        "test_sha256": focused_test_sha,
        "active": policy_active(root),
        "state": "DRAFT_INACTIVE",
    }


def ensure_not_consumed(root: Path) -> None:
    path = root / CONSUMED_STATE
    if path.exists() or path.is_symlink():
        raise GateError(f"R4W1-A candidate exception already consumed: {path}")


def consume_exception(root: Path, run_dir: Path) -> None:
    ensure_not_consumed(root)
    historical.durable_create_json(
        root / CONSUMED_STATE,
        {
            "schema": "s22plus_fyg8_r4w1a_stream_candidate_consumed_v2",
            "target": TARGET,
            "consumed_at_utc": common.utc_now(),
            "reason": "candidate_flash_start",
            "run_dir": str(run_dir.relative_to(root)),
            "helper_sha256": helper_sha256(root),
            "candidate_ap_sha256": EXPECTED_CANDIDATE_AP_SHA256,
            "a4_qualification_result_sha256": QUALIFICATION_RESULT_SHA256,
        },
    )


def require_consumed_for_rollback(root: Path) -> dict[str, Any]:
    path = root / CONSUMED_STATE
    if path.is_symlink() or not path.is_file():
        raise GateError("rollback requires an already-consumed stream-candidate run")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GateError("candidate consumed state is invalid") from exc
    required = (
        state.get("schema") == "s22plus_fyg8_r4w1a_stream_candidate_consumed_v2",
        state.get("target") == TARGET,
        state.get("reason") == "candidate_flash_start",
        state.get("helper_sha256") == helper_sha256(root),
        state.get("candidate_ap_sha256") == EXPECTED_CANDIDATE_AP_SHA256,
        state.get("a4_qualification_result_sha256") == QUALIFICATION_RESULT_SHA256,
    )
    if not all(required):
        raise GateError("candidate consumed state contract mismatch")
    return state


def allocate_run_dir(root: Path, mode: str, requested: Path | None) -> Path:
    return historical.allocate_run_dir(root, f"stream_candidate_{mode}", requested)


def capture_stream_oracle(
    serial: str,
    run_dir: Path,
    *,
    expectation: str,
    timeout: float,
) -> dict[str, Any]:
    before = historical.remote_inventory(serial)
    common.durable_write_json(run_dir / "bugreports_before.json", before)
    host_zip = run_dir / "bugreport.zip"
    stderr_path = run_dir / "bugreport.stderr"
    result: dict[str, Any] = {
        "contract": "host-stream-canonical-no-remote-cleanup-v2",
        "expectation": expectation,
        "before": before,
        "stream": None,
        "after": None,
        "inventory_delta": None,
        "inventory_unchanged": False,
        "parser": None,
        "parser_stream_identity_match": False,
        "remote_cleanup_allowed": False,
        "cleanup_attempted": False,
        "success": False,
        "errors": [],
    }
    try:
        result["stream"] = historical.stream_bugreport(
            serial, host_zip, stderr_path, timeout
        )
    except (GateError, OSError, subprocess.SubprocessError) as exc:
        result["errors"].append(str(exc))

    try:
        after = historical.remote_inventory(serial)
        result["after"] = after
        common.durable_write_json(run_dir / "bugreports_after.json", after)
        delta = historical.compare_inventories(before, after)
        result["inventory_delta"] = delta
        result["inventory_unchanged"] = after == before
        if not result["inventory_unchanged"]:
            result["errors"].append(
                "direct /bugreports inventory changed; remote cleanup is forbidden"
            )
    except (GateError, OSError, subprocess.SubprocessError) as exc:
        result["errors"].append(f"post-capture inventory failed: {exc}")

    if result["stream"] is not None and host_zip.is_file():
        try:
            parsed = oracle.parse_bugreport(host_zip, expectation)
            result["parser"] = parsed
            parser_input = parsed.get("input", {})
            result["parser_stream_identity_match"] = (
                parser_input.get("sha256") == result["stream"].get("sha256")
                and parser_input.get("size") == result["stream"].get("bytes")
                and parser_input.get("same_fd_pre_post_sha256") is True
            )
            if not result["parser_stream_identity_match"]:
                result["errors"].append(
                    "parsed ZIP identity does not match the canonical stream"
                )
        except (oracle.OracleError, OSError) as exc:
            result["errors"].append(f"oracle parser failed: {exc}")

    result["success"] = (
        not result["errors"]
        and result["stream"] is not None
        and result["inventory_unchanged"] is True
        and result["parser"] is not None
        and result["parser_stream_identity_match"] is True
        and result["cleanup_attempted"] is False
    )
    common.durable_write_json(run_dir / "oracle_capture.json", result)
    return result


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
            result["pstore_console_absent"] = historical.pstore_console_absent(serial)
            result["oracle_capture"] = capture_stream_oracle(
                serial,
                run_dir,
                expectation="exact",
                timeout=args.bugreport_wait_sec,
            )
        except (GateError, OSError, subprocess.SubprocessError) as exc:
            result["oracle_capture"] = {
                "success": False,
                "errors": [str(exc)],
                "cleanup_attempted": False,
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
    if not candidate_transfer_ok:
        return "NO_PROOF_R4W1A_CANDIDATE_TRANSFER_FAILED_MAGISK_ROLLED_BACK", 31
    if samples:
        return "NO_PROOF_R4W1A_ANDROID_VIABLE_STREAM_WITNESS_NOT_RECOVERED", 41
    return "NO_PROOF_NO_R4W1A_ANDROID_OR_STREAM_WITNESS", 32


def append_remaining_events(
    timeline_path: Path, timeline: list[dict[str, str]], start_at: int
) -> None:
    for name in TIMELINE_NAMES[start_at:]:
        common.append_event(timeline_path, timeline, name)


def collect_rollback_corroboration(serial: str, run_dir: Path) -> dict[str, Any]:
    try:
        return historical.collect_rollback_last_kmsg(serial, run_dir)
    except (GateError, OSError, subprocess.SubprocessError) as exc:
        result = {"load_bearing": False, "error": str(exc)}
        common.durable_write_json(run_dir / "rollback_last_kmsg.json", result)
        return result


def live_run(root: Path, args: argparse.Namespace, artifacts: dict[str, Any]) -> int:
    if not policy_active(root):
        raise GateError("R4W1-A stream-candidate policy is inactive")
    if args.ack != LIVE_ACK_TOKEN:
        raise GateError("R4W1-A stream-candidate acknowledgement mismatch")
    ensure_not_consumed(root)
    odin = common.resolve(root, args.odin)
    run_dir = allocate_run_dir(root, "live", args.run_dir)
    timeline: list[dict[str, str]] = []
    timeline_path = run_dir / "timeline.json"
    log_path = run_dir / "live.log"
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
    serial, baseline = historical.connected_preflight(root, run_dir, odin)
    result["baseline"] = baseline
    result["baseline_pstore_console_absent"] = historical.pstore_console_absent(serial)
    common.durable_write_json(run_dir / "result.json", result)

    reboot = common.run(["adb", "-s", serial, "reboot", "download"], timeout=20)
    if reboot.returncode != 0:
        raise GateError("Android failed to request Download mode")
    device = common.wait_for_odin(
        odin, log_path, "r4w1a-stream-candidate", args.download_wait_sec
    )
    if device is None:
        raise GateError("Download mode did not appear before candidate flash")
    common.append_event(timeline_path, timeline, "candidate_flash_start")
    consume_exception(root, run_dir)
    result["candidate_flash_attempted"] = True
    common.durable_write_json(run_dir / "result.json", result)
    try:
        common.flash_exact(
            odin,
            common.resolve(root, args.candidate_ap),
            device,
            log_path,
            "r4w1a-stream-candidate",
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
    try:
        if result["candidate_transfer_ok"] and common.wait_odin_absent(
            odin,
            log_path,
            "r4w1a-stream-candidate-disconnect",
            args.disconnect_wait_sec,
        ):
            observation = candidate_observation(args, run_dir)
        elif result["candidate_transfer_ok"]:
            observation["observation"] = "original Odin endpoint stayed present"
    except (GateError, OSError, subprocess.SubprocessError) as exc:
        observation["observation"] = f"candidate observation failed closed: {exc}"
    result["candidate_observation"] = observation
    common.append_event(timeline_path, timeline, "candidate_boot_ready")
    common.durable_write_json(run_dir / "result.json", result)

    try:
        existing = common.odin_devices(odin, log_path, "r4w1a-stream-pre-rollback")
    except (GateError, OSError, subprocess.SubprocessError) as exc:
        existing = []
        result["pre_rollback_endpoint_error"] = str(exc)
    if len(existing) > 1:
        result["verdict"] = "FAIL_R4W1A_AMBIGUOUS_ROLLBACK_TARGET_RECOVERY_REQUIRED"
        result["timeline_phase_semantics"] = {
            "rollback_flash_start": (
                "multiple Odin endpoints observed; no rollback flash started"
            ),
            "rollback_flash_done": "no rollback flash occurred",
            "rollback_boot_ready": "rollback Android not observed",
            "live_session_end": "recovery required because rollback target was ambiguous",
        }
        append_remaining_events(timeline_path, timeline, 4)
        common.durable_write_json(run_dir / "result.json", result)
        return 20
    rollback_device = existing[0] if existing else None
    if rollback_device is None:
        common.request_download_if_android()
        print(
            "R4W1-A observation is complete. If Download mode does not appear "
            "automatically, enter physical Download mode for mandatory rollback.",
            flush=True,
        )
        try:
            rollback_device = common.wait_for_odin(
                odin,
                log_path,
                "r4w1a-stream-mandatory-rollback",
                args.manual_wait_sec,
            )
        except (GateError, OSError, subprocess.SubprocessError) as exc:
            result["rollback_endpoint_wait_error"] = str(exc)
            rollback_device = None
    if rollback_device is None:
        result["verdict"] = "FAIL_R4W1A_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED"
        result["timeline_phase_semantics"] = {
            "rollback_flash_start": "bounded wait closed; no rollback flash started",
            "rollback_flash_done": "no rollback flash occurred",
            "rollback_boot_ready": "rollback Android not observed",
            "live_session_end": "recovery requires rollback-from-download mode",
        }
        append_remaining_events(timeline_path, timeline, 4)
        common.durable_write_json(run_dir / "result.json", result)
        return 20

    common.append_event(timeline_path, timeline, "rollback_flash_start")
    try:
        rollback_target = common.flash_rollback(root, odin, rollback_device, log_path)
    except (GateError, OSError, subprocess.SubprocessError) as exc:
        result["rollback_error"] = str(exc)
        result["verdict"] = "FAIL_R4W1A_ROLLBACK_TRANSFER_RECOVERY_REQUIRED"
        append_remaining_events(timeline_path, timeline, 5)
        common.durable_write_json(run_dir / "result.json", result)
        return 20
    common.append_event(timeline_path, timeline, "rollback_flash_done")
    try:
        final, rollback_verdict, rollback_rc = common.wait_final_android(
            rollback_target, args.android_wait_sec, odin, log_path
        )
    except (GateError, OSError, subprocess.SubprocessError) as exc:
        result["rollback_target"] = rollback_target
        result["rollback_health_error"] = str(exc)
        result["verdict"] = "FAIL_R4W1A_ROLLBACK_HEALTH_RECOVERY_REQUIRED"
        append_remaining_events(timeline_path, timeline, 6)
        common.durable_write_json(run_dir / "result.json", result)
        return 20
    common.append_event(timeline_path, timeline, "rollback_boot_ready")
    rollback_capture = None
    if rollback_target == "magisk":
        try:
            rollback_capture = collect_rollback_corroboration(
                common.adb_serial(), run_dir
            )
        except (GateError, OSError, subprocess.SubprocessError) as exc:
            rollback_capture = {"load_bearing": False, "error": str(exc)}
            common.durable_write_json(
                run_dir / "rollback_last_kmsg.json", rollback_capture
            )
    capture = observation.get("oracle_capture") or {}
    verdict, rc = classify_live_verdict(
        rollback_target,
        rollback_verdict,
        rollback_rc,
        bool(result["candidate_transfer_ok"]),
        observation.get("samples", []),
        bool(capture.get("success")),
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
    if not policy_active(root):
        raise GateError("R4W1-A stream-candidate rollback policy is inactive")
    if args.ack != ROLLBACK_ACK_TOKEN:
        raise GateError("R4W1-A stream rollback acknowledgement mismatch")
    require_consumed_for_rollback(root)
    odin = common.resolve(root, args.odin)
    run_dir = allocate_run_dir(root, "rollback", args.run_dir)
    timeline: list[dict[str, str]] = []
    timeline_path = run_dir / "timeline.json"
    log_path = run_dir / "rollback.log"
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "mode": "rollback-from-download",
        "target": TARGET,
        "verdict": "INCOMPLETE",
        "timeline_phase_semantics": {
            "candidate_flash_start": "recovery-only-no-candidate-flash",
            "candidate_flash_done": "recovery-only-no-candidate-flash",
            "candidate_boot_ready": "operator-entered-download-before-session",
        },
    }
    for name in TIMELINE_NAMES[:4]:
        common.append_event(timeline_path, timeline, name)
    common.durable_write_json(run_dir / "result.json", result)
    devices = common.odin_devices(odin, log_path, "r4w1a-stream-recovery")
    if len(devices) != 1:
        raise GateError(f"rollback requires exactly one Odin endpoint, got {devices}")
    common.append_event(timeline_path, timeline, "rollback_flash_start")
    target = common.flash_rollback(root, odin, devices[0], log_path)
    common.append_event(timeline_path, timeline, "rollback_flash_done")
    final, verdict, rc = common.wait_final_android(
        target, args.android_wait_sec, odin, log_path
    )
    common.append_event(timeline_path, timeline, "rollback_boot_ready")
    common.append_event(timeline_path, timeline, "live_session_end")
    if target == "magisk":
        verdict = "PASS_R4W1A_STREAM_CANDIDATE_MAGISK_ROLLBACK_FROM_DOWNLOAD"
    result.update({"rollback_target": target, "final": final, "verdict": verdict})
    common.durable_write_json(run_dir / "result.json", result)
    print(json.dumps({"run_dir": str(run_dir), "verdict": verdict}, indent=2))
    return rc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline-check", action="store_true")
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
    parser.add_argument("--manual-wait-sec", type=int, default=300)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    parser.add_argument("--bugreport-wait-sec", type=int, default=600)
    parser.add_argument("--sample-count", type=int, default=3)
    parser.add_argument("--sample-interval-sec", type=float, default=5.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = common.repo_root()
    try:
        if args.sample_count < 1 or args.sample_count > 5:
            raise GateError("sample count must be between 1 and 5")
        for label, value, maximum in (
            ("download wait", args.download_wait_sec, 300),
            ("disconnect wait", args.disconnect_wait_sec, 120),
            ("candidate wait", args.candidate_wait_sec, 600),
            ("manual wait", args.manual_wait_sec, 600),
            ("Android wait", args.android_wait_sec, 600),
            ("bugreport wait", args.bugreport_wait_sec, 900),
        ):
            if value < 1 or value > maximum:
                raise GateError(f"{label} must be between 1 and {maximum} seconds")
        if args.sample_interval_sec <= 0 or args.sample_interval_sec > 30:
            raise GateError("sample interval must be in (0, 30] seconds")
        odin = common.resolve(root, args.odin)
        artifacts = verify_artifacts(
            root,
            common.resolve(root, args.candidate_boot),
            common.resolve(root, args.candidate_ap),
            common.resolve(root, args.manifest),
            odin,
        )
        policy = verify_policy_draft(root)
        if args.offline_check:
            print(
                json.dumps(
                    {
                        "schema": SCHEMA,
                        "verdict": "PASS_R4W1A_STREAM_CANDIDATE_OFFLINE_CHECK",
                        "artifacts": artifacts,
                        "policy": policy,
                        "candidate_consumed": (root / CONSUMED_STATE).exists(),
                        "device_contact": False,
                        "device_write": False,
                        "flash": False,
                    },
                    indent=2,
                )
            )
            return 0
        if args.live:
            return live_run(root, args, artifacts)
        if args.rollback_from_download:
            return rollback_from_download(root, args)
        raise GateError("no mode selected")
    except (
        GateError,
        qualification.QualificationError,
        oracle.OracleError,
        OSError,
        subprocess.SubprocessError,
        json.JSONDecodeError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
