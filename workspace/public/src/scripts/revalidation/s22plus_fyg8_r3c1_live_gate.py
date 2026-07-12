#!/usr/bin/env python3
"""Guarded FYG8 R3C1 unpatched rebuilt-kernel boot-only live gate.

This helper verifies the exact R3C1 artifact/static contract, performs one
bounded candidate boot observation, and restores the pinned Magisk boot. It
reuses the already-reviewed R3C0 transport, Android identity, rollback, and
timeline primitives while maintaining separate R3C1 policy and one-shot state.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import s22plus_fyg8_r3c0_live_gate as common


SCHEMA = "s22plus_fyg8_r3c1_live_gate_v1"
TARGET = common.TARGET
SCRIPT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r3c1_live_gate.py"
)
CHECKER_RELATIVE = common.CHECKER_RELATIVE
BUILDER_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/build_s22plus_fyg8_r3c1_candidate.py"
)
BUILDER_TEST_RELATIVE = Path("tests/test_build_s22plus_fyg8_r3c1_candidate.py")
POLICY_DRAFT = Path(
    "docs/operations/S22PLUS_FYG8_R3C1_AGENTS_EXCEPTION_DRAFT_2026-07-12.md"
)
POLICY_MARKER = "S22+ FYG8 R3C1 unpatched rebuilt-kernel boot-only live gate"
ACTIVE_SENTINEL = "S22PLUS_FYG8_R3C1_POLICY_STATE=ACTIVE"
PENDING_SENTINEL = "S22PLUS_FYG8_R3C1_POLICY_STATE=PENDING_OPERATOR_APPROVAL"
LIVE_ACK_TOKEN = "S22PLUS-FYG8-R3C1-UNPATCHED-KERNEL-LIVE"
ROLLBACK_ACK_TOKEN = "S22PLUS-FYG8-R3C1-MAGISK-ROLLBACK-FROM-DOWNLOAD"

EXPECTED_CANDIDATE_BOOT_SHA256 = (
    "e1f0be9933e9c76d881a2cc39c0431bf54930ee0f216f55de4d7a166a60d120c"
)
EXPECTED_CANDIDATE_BOOT_SIZE = 100_663_296
EXPECTED_CANDIDATE_LZ4_SHA256 = (
    "d00e12c6d9c2d1f4100d454ba9789dcb1d782da1d72a62caf9a7664402da9efd"
)
EXPECTED_CANDIDATE_AP_SHA256 = (
    "023d7780e11363bd152900e28279233a0fd66ce8dd8902417d23eb781f613fb4"
)
EXPECTED_MANIFEST_SHA256 = (
    "2596b5f1c6a8fa88d8ee75224c8a039764c67453875789744a7087db2fb97bb0"
)
EXPECTED_BUILDER_SHA256 = (
    "11f6e270ba5c63b498b2072573bb8a870f6dd031b5fb407268b6d39c55577596"
)
EXPECTED_BUILDER_TEST_SHA256 = (
    "229ce3766d898cc5b93448be84dbc18ab798fac0724969dc030992caa5edda5d"
)
EXPECTED_CHECKER_SHA256 = common.EXPECTED_CHECKER_SHA256
EXPECTED_R3C0_BOOT_SHA256 = common.EXPECTED_CANDIDATE_BOOT_SHA256
EXPECTED_R3C0_AP_SHA256 = common.EXPECTED_CANDIDATE_AP_SHA256
EXPECTED_R2_IMAGE_SHA256 = (
    "9110a7722f28f075c5cb09789710341b44956147fa05867d05e5b3e7d024770d"
)

DEFAULT_CANDIDATE_DIR = Path(
    "workspace/private/outputs/s22plus_fyg8_r3c1_candidate/reproduction-c"
)
DEFAULT_CANDIDATE_BOOT = DEFAULT_CANDIDATE_DIR / "boot.img"
DEFAULT_CANDIDATE_AP = DEFAULT_CANDIDATE_DIR / "odin4/AP.tar.md5"
DEFAULT_MANIFEST = DEFAULT_CANDIDATE_DIR / "manifest.json"
DEFAULT_R3C0_BOOT = Path(
    "workspace/private/outputs/s22plus_fyg8_r3c0_control/reproduction-a/boot.img"
)
DEFAULT_R3C0_AP = Path(
    "workspace/private/outputs/s22plus_fyg8_r3c0_control/reproduction-a/odin4/AP.tar.md5"
)
CONSUMED_STATE = Path(
    "workspace/private/state/s22plus_fyg8_r3c1_live_exception_consumed.json"
)
RUN_ROOT = common.RUN_ROOT
TIMELINE_NAMES = common.TIMELINE_NAMES
GateError = common.GateError
append_event = common.append_event
durable_write_json = common.durable_write_json
utc_stamp = common.utc_stamp


def verify_manifest(path: Path) -> dict[str, Any]:
    if common.sha256_file(path) != EXPECTED_MANIFEST_SHA256:
        raise GateError("R3C1 manifest SHA mismatch")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "s22plus_fyg8_r3c1_candidate_build_v1":
        raise GateError("R3C1 manifest schema mismatch")
    if data.get("target") != TARGET:
        raise GateError("R3C1 manifest target mismatch")
    if data.get("verdict") != "PASS_R3C1_ARTIFACT_BUILT_HOST_ONLY":
        raise GateError("R3C1 manifest verdict mismatch")
    inputs = data.get("inputs", {})
    expected_inputs = {
        "r3c0_boot": EXPECTED_R3C0_BOOT_SHA256,
        "r2_image": EXPECTED_R2_IMAGE_SHA256,
    }
    for key, expected in expected_inputs.items():
        if inputs.get(key, {}).get("sha256") != expected:
            raise GateError(f"R3C1 manifest input mismatch: {key}")
    hashes = data.get("artifacts", {}).get("hashes", {})
    expected_hashes = {
        "boot_img": EXPECTED_CANDIDATE_BOOT_SHA256,
        "boot_img_lz4": EXPECTED_CANDIDATE_LZ4_SHA256,
        "ap_tar_md5": EXPECTED_CANDIDATE_AP_SHA256,
        "kernel": EXPECTED_R2_IMAGE_SHA256,
    }
    for key, expected in expected_hashes.items():
        if hashes.get(key) != expected:
            raise GateError(f"R3C1 manifest artifact mismatch: {key}")
    construction = data.get("construction", {})
    required_construction = {
        "patch_vbmeta_flag": False,
        "kernel_equals_exact_r2_image": True,
        "r3c0_boot_header_preserved": True,
        "r3c0_post_kernel_bytes_preserved": True,
        "r3c0_ramdisk_preserved": True,
        "r3c0_signer_preserved": True,
        "r3c0_vbmeta_preserved": True,
        "r3c0_avb_footer_preserved": True,
        "arm64_header_exact_r3c0_match": True,
    }
    for key, expected in required_construction.items():
        if construction.get(key) != expected:
            raise GateError(f"R3C1 manifest construction mismatch: {key}")
    difference = construction.get("difference", {})
    if difference.get("outside_kernel_changed_byte_count") != 0:
        raise GateError("R3C1 manifest records outside-kernel changes")
    if difference.get("changed_byte_count") != 9_098_520:
        raise GateError("R3C1 manifest changed-byte count mismatch")
    safety = data.get("safety", {})
    required_safety = {
        "host_only": True,
        "boot_only_ap": True,
        "device_contact": False,
        "usb_enumeration": False,
        "odin_transfer": False,
        "flash": False,
        "live_authorized": False,
        "r3c1_live_authorized": False,
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise GateError(f"R3C1 manifest safety mismatch: {key}")
    return data


def run_static_checker(root: Path, boot: Path, ap: Path) -> dict[str, Any]:
    checker = root / CHECKER_RELATIVE
    if common.sha256_file(checker) != EXPECTED_CHECKER_SHA256:
        raise GateError("R3 static checker SHA mismatch")
    result = common.run(
        [
            sys.executable,
            checker,
            "--stage",
            "r3c1",
            "--r3c0-boot",
            root / DEFAULT_R3C0_BOOT,
            "--r3c0-ap",
            root / DEFAULT_R3C0_AP,
            "--r3c0-boot-sha256",
            EXPECTED_R3C0_BOOT_SHA256,
            "--r3c0-ap-sha256",
            EXPECTED_R3C0_AP_SHA256,
            "--r3c1-boot",
            boot,
            "--r3c1-ap",
            ap,
            "--r3c1-boot-sha256",
            EXPECTED_CANDIDATE_BOOT_SHA256,
            "--r3c1-ap-sha256",
            EXPECTED_CANDIDATE_AP_SHA256,
        ],
        timeout=180,
    )
    if result.returncode != 0:
        raise GateError("R3C1 static checker failed closed")
    report = json.loads(result.stdout)
    if report.get("verdict") != "PASS_R3C1_STATIC_CONTRACT":
        raise GateError("R3C1 static checker verdict mismatch")
    return {
        "source_sha256": EXPECTED_CHECKER_SHA256,
        "verdict": report["verdict"],
        "scope": report.get("scope", {}),
    }


def verify_artifacts(
    root: Path, boot: Path, ap: Path, manifest: Path, odin: Path
) -> dict[str, Any]:
    if common.sha256_file(root / BUILDER_RELATIVE) != EXPECTED_BUILDER_SHA256:
        raise GateError("R3C1 builder SHA mismatch")
    if common.sha256_file(root / BUILDER_TEST_RELATIVE) != EXPECTED_BUILDER_TEST_SHA256:
        raise GateError("R3C1 builder test SHA mismatch")
    if boot.stat().st_size != EXPECTED_CANDIDATE_BOOT_SIZE:
        raise GateError("R3C1 boot size mismatch")
    if common.sha256_file(boot) != EXPECTED_CANDIDATE_BOOT_SHA256:
        raise GateError("R3C1 boot SHA mismatch")
    if common.sha256_file(ap) != EXPECTED_CANDIDATE_AP_SHA256:
        raise GateError("R3C1 AP SHA mismatch")
    if common.tar_members(ap) != [common.EXPECTED_MEMBER]:
        raise GateError("R3C1 AP is not exactly boot-only")
    manifest_data = verify_manifest(manifest)
    magisk = common.resolve(root, common.DEFAULT_MAGISK_ROLLBACK_AP)
    stock = common.resolve(root, common.DEFAULT_STOCK_ROLLBACK_AP)
    if common.sha256_file(magisk) != common.EXPECTED_MAGISK_AP_SHA256:
        raise GateError("Magisk rollback AP SHA mismatch")
    if common.tar_members(magisk) != [common.EXPECTED_MEMBER]:
        raise GateError("Magisk rollback AP is not boot-only")
    if common.sha256_file(stock) != common.EXPECTED_STOCK_AP_SHA256:
        raise GateError("stock cleanup AP SHA mismatch")
    if common.tar_members(stock) != [common.EXPECTED_MEMBER]:
        raise GateError("stock cleanup AP is not boot-only")
    return {
        "candidate_boot_sha256": EXPECTED_CANDIDATE_BOOT_SHA256,
        "candidate_ap_sha256": EXPECTED_CANDIDATE_AP_SHA256,
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "manifest_schema": manifest_data["schema"],
        "builder_sha256": EXPECTED_BUILDER_SHA256,
        "magisk_rollback_ap_sha256": common.EXPECTED_MAGISK_AP_SHA256,
        "stock_cleanup_ap_sha256": common.EXPECTED_STOCK_AP_SHA256,
        "checker": run_static_checker(root, boot, ap),
        "odin": common.verify_odin(odin),
    }


def policy_active(root: Path) -> bool:
    text = (root / "AGENTS.md").read_text(encoding="utf-8")
    source_sha = common.sha256_file(root / SCRIPT_RELATIVE)
    active_line = re.compile(rf"(?m)^\s*`?{re.escape(ACTIVE_SENTINEL)}`?\s*$")
    required = (
        POLICY_MARKER,
        str(SCRIPT_RELATIVE),
        source_sha,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        EXPECTED_CANDIDATE_BOOT_SHA256,
        EXPECTED_CANDIDATE_AP_SHA256,
        common.EXPECTED_MAGISK_AP_SHA256,
        common.EXPECTED_STOCK_AP_SHA256,
    )
    return bool(active_line.search(text)) and all(item in text for item in required)


def verify_policy_draft(root: Path) -> dict[str, Any]:
    path = root / POLICY_DRAFT
    if not path.is_file():
        raise GateError("R3C1 policy draft missing")
    text = path.read_text(encoding="utf-8")
    source_sha = common.sha256_file(root / SCRIPT_RELATIVE)
    required = (
        "DRAFT_INACTIVE",
        POLICY_MARKER,
        str(SCRIPT_RELATIVE),
        source_sha,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        EXPECTED_CANDIDATE_BOOT_SHA256,
        EXPECTED_CANDIDATE_AP_SHA256,
        common.EXPECTED_MAGISK_AP_SHA256,
        common.EXPECTED_STOCK_AP_SHA256,
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise GateError(f"R3C1 policy draft missing pins: {missing}")
    return {
        "path": str(POLICY_DRAFT),
        "sha256": common.sha256_file(path),
        "active": policy_active(root),
    }


def consumed_state_path(root: Path) -> Path:
    return root / CONSUMED_STATE


def ensure_not_consumed(root: Path) -> None:
    path = consumed_state_path(root)
    if path.exists():
        raise GateError(f"R3C1 one-shot exception already consumed: {path}")


def consume_exception(root: Path, run_dir: Path) -> None:
    path = consumed_state_path(root)
    if path.exists():
        raise GateError(f"R3C1 one-shot exception already consumed: {path}")
    durable_write_json(
        path,
        {
            "schema": "s22plus_fyg8_r3c1_consumed_state_v1",
            "consumed_at_utc": common.utc_now(),
            "reason": "candidate_flash_start",
            "run_dir": str(run_dir.relative_to(root)),
            "candidate_ap_sha256": EXPECTED_CANDIDATE_AP_SHA256,
        },
    )


def classify_live_verdict(
    rollback_target: str,
    rollback_verdict: str,
    rollback_rc: int,
    candidate_transfer_ok: bool,
    samples: list[dict[str, str]],
) -> tuple[str, int]:
    if rollback_target != "magisk":
        return rollback_verdict, rollback_rc
    if samples:
        return "PASS_R3C1_UNPATCHED_REBUILT_KERNEL_VIABLE_AND_ROLLED_BACK", 0
    if not candidate_transfer_ok:
        return "NO_PROOF_R3C1_CANDIDATE_TRANSFER_FAILED_MAGISK_ROLLED_BACK", 31
    return "NO_PROOF_NO_R3C1_CANDIDATE_ANDROID_MILESTONE_MAGISK_ROLLED_BACK", 32


def rollback_from_download(root: Path, odin: Path, run_dir: Path) -> dict[str, Any]:
    timeline: list[dict[str, str]] = []
    timeline_path = run_dir / "timeline.json"
    log_path = run_dir / "rollback.log"
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "mode": "rollback-from-download",
        "timeline_phase_semantics": {
            "candidate_flash_start": "recovery-only-session-no-candidate-flash",
            "candidate_flash_done": "recovery-only-session-no-candidate-flash",
            "candidate_boot_ready": "operator-entered-download-before-session",
        },
        "verdict": "INCOMPLETE",
    }
    for name in TIMELINE_NAMES[:4]:
        append_event(timeline_path, timeline, name)
    durable_write_json(run_dir / "result.json", result)
    devices = common.odin_devices(odin, log_path, "r3c1-recovery")
    if len(devices) != 1:
        raise GateError(f"rollback requires exactly one Odin device, got {len(devices)}")
    append_event(timeline_path, timeline, "rollback_flash_start")
    target = common.flash_rollback(root, odin, devices[0], log_path)
    append_event(timeline_path, timeline, "rollback_flash_done")
    final, verdict, rc = common.wait_final_android(target, 300, odin, log_path)
    if target == "magisk":
        verdict = "PASS_R3C1_MAGISK_ROLLBACK_FROM_DOWNLOAD"
    append_event(timeline_path, timeline, "rollback_boot_ready")
    append_event(timeline_path, timeline, "live_session_end")
    result.update(
        {
            "rollback_target": target,
            "final": final,
            "verdict": verdict,
            "exit_code": rc,
        }
    )
    durable_write_json(run_dir / "result.json", result)
    return result


def live_run(root: Path, args: argparse.Namespace, artifacts: dict[str, Any]) -> int:
    if not policy_active(root):
        raise GateError("R3C1 live policy is inactive")
    if args.ack != LIVE_ACK_TOKEN:
        raise GateError("R3C1 live acknowledgement mismatch")
    ensure_not_consumed(root)
    serial, baseline = common.current_android()
    odin = common.resolve(root, args.odin)
    run_dir = root / RUN_ROOT / f"s22plus_fyg8_r3c1_live_{utc_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    timeline: list[dict[str, str]] = []
    timeline_path = run_dir / "timeline.json"
    log_path = run_dir / "live.log"
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "target": TARGET,
        "baseline": baseline,
        "artifacts": artifacts,
        "candidate_flash_attempted": False,
        "candidate_milestone_reached": False,
        "verdict": "INCOMPLETE",
    }
    append_event(timeline_path, timeline, "live_session_start")
    durable_write_json(run_dir / "result.json", result)

    reboot = common.run(["adb", "-s", serial, "reboot", "download"], timeout=20)
    if reboot.returncode != 0:
        raise GateError("Android failed to request Download mode")
    candidate_device = common.wait_for_odin(
        odin, log_path, "r3c1-candidate", args.download_wait_sec
    )
    if candidate_device is None:
        raise GateError("Download mode did not appear before R3C1 candidate flash")
    append_event(timeline_path, timeline, "candidate_flash_start")
    consume_exception(root, run_dir)
    result["candidate_flash_attempted"] = True
    durable_write_json(run_dir / "result.json", result)
    candidate_transfer_ok = False
    try:
        common.flash_exact(
            odin,
            common.resolve(root, args.candidate_ap),
            candidate_device,
            log_path,
            "r3c1-candidate",
        )
        candidate_transfer_ok = True
    except GateError as error:
        result["candidate_flash_error"] = str(error)
    append_event(timeline_path, timeline, "candidate_flash_done")
    durable_write_json(run_dir / "result.json", result)

    samples: list[dict[str, str]] = []
    candidate_error = "candidate transfer failed"
    if candidate_transfer_ok and common.wait_odin_absent(
        odin, log_path, "r3c1-candidate-disconnect", args.disconnect_wait_sec
    ):
        _, samples, candidate_error = common.wait_candidate_android(
            args.candidate_wait_sec, args.sample_count, args.sample_interval_sec
        )
        result["candidate_samples"] = samples
        result["candidate_milestone_reached"] = bool(samples)
        result["candidate_observation"] = candidate_error
    elif candidate_transfer_ok:
        candidate_error = "original Odin endpoint stayed; candidate boot not proven"
        result["candidate_observation"] = candidate_error
    else:
        result["candidate_observation"] = candidate_error
    result["candidate_boot_ready_semantics"] = (
        "R3C1 candidate Android milestone reached"
        if samples
        else f"bounded observation closed without milestone: {candidate_error}"
    )
    append_event(timeline_path, timeline, "candidate_boot_ready")
    durable_write_json(run_dir / "result.json", result)

    rollback_device: str | None = None
    existing = common.odin_devices(odin, log_path, "r3c1-pre-rollback")
    if len(existing) > 1:
        raise GateError(f"ambiguous Odin endpoints before rollback: {existing}")
    if existing:
        rollback_device = existing[0]
    else:
        common.request_download_if_android()
        print(
            "R3C1 observation complete. If Download mode does not appear "
            "automatically, enter physical Download mode for mandatory rollback.",
            flush=True,
        )
        rollback_device = common.wait_for_odin(
            odin, log_path, "r3c1-mandatory-rollback", args.manual_wait_sec
        )
    if rollback_device is None:
        result.update(
            {
                "verdict": "FAIL_R3C1_ROLLBACK_NOT_VERIFIED_MANUAL_DOWNLOAD_REQUIRED",
                "timeline_phase_semantics": {
                    "rollback_flash_start": "bounded wait closed; no rollback flash started",
                    "rollback_flash_done": "no rollback flash occurred",
                    "rollback_boot_ready": "rollback Android not observed",
                    "live_session_end": "recovery required through rollback-from-download mode",
                },
            }
        )
        for name in TIMELINE_NAMES[4:]:
            append_event(timeline_path, timeline, name)
        durable_write_json(run_dir / "result.json", result)
        return 20

    append_event(timeline_path, timeline, "rollback_flash_start")
    rollback_target = common.flash_rollback(root, odin, rollback_device, log_path)
    append_event(timeline_path, timeline, "rollback_flash_done")
    final, rollback_verdict, rollback_rc = common.wait_final_android(
        rollback_target, args.android_wait_sec, odin, log_path
    )
    append_event(timeline_path, timeline, "rollback_boot_ready")
    verdict, rollback_rc = classify_live_verdict(
        rollback_target,
        rollback_verdict,
        rollback_rc,
        candidate_transfer_ok,
        samples,
    )
    result.update(
        {
            "rollback_target": rollback_target,
            "final": final,
            "verdict": verdict,
        }
    )
    append_event(timeline_path, timeline, "live_session_end")
    durable_write_json(run_dir / "result.json", result)
    print(json.dumps({"run_dir": str(run_dir), "verdict": verdict}, indent=2))
    return rollback_rc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline-check", action="store_true")
    modes.add_argument("--connected-dry-run", action="store_true")
    modes.add_argument("--live", action="store_true")
    modes.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--ack")
    parser.add_argument("--candidate-boot", type=Path, default=DEFAULT_CANDIDATE_BOOT)
    parser.add_argument("--candidate-ap", type=Path, default=DEFAULT_CANDIDATE_AP)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--odin", type=Path, default=common.DEFAULT_ODIN)
    parser.add_argument("--download-wait-sec", type=int, default=120)
    parser.add_argument("--disconnect-wait-sec", type=int, default=30)
    parser.add_argument("--candidate-wait-sec", type=int, default=300)
    parser.add_argument("--manual-wait-sec", type=int, default=300)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    parser.add_argument("--sample-count", type=int, default=3)
    parser.add_argument("--sample-interval-sec", type=float, default=5.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = common.repo_root()
    try:
        if args.sample_count < 1 or args.sample_count > 5:
            raise GateError("sample count must be between 1 and 5")
        odin = common.resolve(root, args.odin)
        artifacts = verify_artifacts(
            root,
            common.resolve(root, args.candidate_boot),
            common.resolve(root, args.candidate_ap),
            common.resolve(root, args.manifest),
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
                    },
                    indent=2,
                )
            )
            return 0
        if args.connected_dry_run:
            _, baseline = common.current_android()
            devices = common.odin_devices(
                odin, Path(os.devnull), "r3c1-connected-dry-run"
            )
            if devices:
                raise GateError(f"connected dry-run requires no Odin endpoint: {devices}")
            print(
                json.dumps(
                    {
                        "schema": SCHEMA,
                        "artifacts": artifacts,
                        "baseline": baseline,
                        "policy_active": draft["active"],
                        "one_shot_consumed": consumed_state_path(root).exists(),
                        "device_writes": False,
                    },
                    indent=2,
                )
            )
            return 0
        if not policy_active(root):
            raise GateError("R3C1 live policy is inactive")
        if args.rollback_from_download:
            if args.ack != ROLLBACK_ACK_TOKEN:
                raise GateError("R3C1 rollback acknowledgement mismatch")
            run_dir = root / RUN_ROOT / f"s22plus_fyg8_r3c1_rollback_{utc_stamp()}"
            run_dir.mkdir(parents=True, exist_ok=False)
            recovery = rollback_from_download(root, odin, run_dir)
            print(json.dumps(recovery, indent=2))
            return int(recovery["exit_code"])
        return live_run(root, args, artifacts)
    except (
        GateError,
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as error:
        print(f"R3C1 gate error: {common.redact(str(error))}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
