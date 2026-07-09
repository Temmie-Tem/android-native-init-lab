#!/usr/bin/env python3
"""Guarded S22+ O1 stock-first-stage control live gate.

Dry-run is the default. Live mode flashes one exact boot-only Magisk overlay
candidate, proves the O0 framed protocol over the stock Android USB gadget,
checks the volatile O1 result and DR-daemon restoration, then restores the
known-good Magisk boot. It never configures USB or loads modules itself.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from s22plus_m3_observable_live_gate import (
    DEFAULT_MAGISK_ROLLBACK_AP,
    DEFAULT_ODIN,
    DEFAULT_RUN_ROOT,
    EXPECTED_MAGISK_AP_SHA256,
    ROLLBACK_MAGISK,
    append_log,
    flash_ap,
    host_snapshot,
    odin_devices,
    poll_android,
    repo_root,
    require_current_android,
    resolve,
    run,
    sha256_file,
    verify_ap,
    wait_for_odin,
)
from s22plus_m25_hs_only_usb2_acm_live_gate import (
    record_timeline_event,
    verify_partition_hash,
)
from s22plus_m34_s10c0_direct_finit_loader_audit_live_gate import (
    DEFAULT_STOCK_ROLLBACK_AP,
    EXPECTED_STOCK_BOOT_AP_SHA256,
    EXPECTED_STOCK_BOOT_RAW_SHA256,
    rollback_boot_only_from_download,
    wait_for_odin_absent,
)
from s22plus_m5_usb_acm_live_gate import verify_android_stability
from s22plus_o0_stock_usb_control import (
    adb_text,
    device_snapshot,
    parse_key_values,
    run_roundtrips,
    select_host_tty,
    start_observers,
    stock_service_state,
)


LIVE_ACK_TOKEN = "S22PLUS-O1-STOCK-FIRST-STAGE-CONTROL-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-O1-STOCK-FIRST-STAGE-CONTROL-ROLLBACK"
EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_MEMBER = "boot.img.lz4"
EXPECTED_SCHEMA = "s22plus_o1_stock_first_stage_control_live_v1"
DISPLAY_SERIAL_REDACTED = "<S22_SERIAL_REDACTED>"

EXPECTED_BASE_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_O1_BOOT_SHA256 = "df7a166752f78aa07bea10aef53de1ba2737abf43bb041fe01738cce36113070"
EXPECTED_O1_BOOT_LZ4_SHA256 = "26af084cca0cf23525e8786a50a49b270d60ae7b2fa7f4ed8d652bc9e102bb21"
EXPECTED_O1_AP_SHA256 = "388d35c12e9f5024f053837444da46254db6a6177c046400549148e24eaeec29"
EXPECTED_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_INIT_SHA256 = "383670a7ba3a6a4b79e5f3467e1da4b66a5df66a9b356ab9f70916854dd6b468"
EXPECTED_RC_SHA256 = "9bd6732aacd55e2eb929bd0eb52fdbdff33613e5ac0931c1ea1ca67ad7cf32fe"
EXPECTED_SERVICE_SHA256 = "3e5c000308acaa52495c1b235b9f3e777123e3ddeb1e51f01b7461a38593be93"
EXPECTED_DAEMON_SHA256 = "a82cd32f83afc20d40fc74a9402896ae07378811f259913ed6df7cbc540f858c"

DEFAULT_O1_ROOT = Path("workspace/private/outputs/s22plus_native_init/o1_magisk_overlay_v0_1")
DEFAULT_O1_AP = DEFAULT_O1_ROOT / "odin4/AP.tar.md5"
DEFAULT_O1_MANIFEST = DEFAULT_O1_ROOT / "manifest.json"
ACTIVE_EXCEPTION_HEADING = (
    "**Narrow operator-authorized exception (2026-07-10, S22+ O1 "
    "stock-first-stage USB control boot-only live gate):**"
)
REQUIRED_LIVE_TIMELINE_PHASES = [
    "live_session_start",
    "candidate_flash_start",
    "candidate_flash_done",
    "candidate_boot_ready",
    "rollback_flash_start",
    "rollback_flash_done",
    "rollback_boot_ready",
    "live_session_end",
]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_o1_stock_first_stage_control_live_gate_{utc_stamp()}")
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise SystemExit(f"could not allocate unique run directory under {base.parent}")


def policy_required_markers() -> list[str]:
    return [
        "S22+ O1 stock-first-stage USB control boot-only",
        "workspace/public/src/scripts/revalidation/s22plus_o1_stock_first_stage_control_live_gate.py",
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        EXPECTED_TARGET,
        EXPECTED_O1_AP_SHA256,
        EXPECTED_O1_BOOT_SHA256,
        EXPECTED_O1_BOOT_LZ4_SHA256,
        EXPECTED_BASE_BOOT_SHA256,
        EXPECTED_KERNEL_SHA256,
        EXPECTED_INIT_SHA256,
        EXPECTED_RC_SHA256,
        EXPECTED_SERVICE_SHA256,
        EXPECTED_DAEMON_SHA256,
        EXPECTED_MAGISK_AP_SHA256,
        EXPECTED_STOCK_BOOT_AP_SHA256,
        EXPECTED_STOCK_BOOT_RAW_SHA256,
        "overlay.d/s22plus_o1_control.rc",
        "overlay.d/sbin/s22plus_o1_service.sh",
        "overlay.d/sbin/s22plus_o1_tty_echo",
        "/dev/.s22plus_o1_status",
        "128-request framed O0 protocol",
        "mandatory boot-only rollback",
        "no configfs/sysfs write",
        "no module insertion",
        "no persistent partition mount",
    ]


def active_exception_segment(agents_text: str) -> str:
    start = agents_text.find(ACTIVE_EXCEPTION_HEADING)
    if start < 0:
        return ""
    next_heading = agents_text.find("\n   **", start + len(ACTIVE_EXCEPTION_HEADING))
    return agents_text[start:] if next_heading < 0 else agents_text[start:next_heading]


def verify_agents_exception(root: Path, log_path: Path) -> None:
    segment = active_exception_segment((root / "AGENTS.md").read_text(encoding="utf-8"))
    normalized = " ".join(segment.split())
    missing = [marker for marker in policy_required_markers() if marker not in normalized]
    append_log(log_path, f"o1_agents_exception_present={int(bool(segment))}")
    append_log(log_path, f"o1_agents_exception_missing={missing}")
    if not segment or "Consumed exception" in segment or "Consumed/retired" in segment:
        raise SystemExit("active O1 AGENTS.md exception is absent or consumed")
    if missing:
        raise SystemExit(f"O1 AGENTS.md exception missing markers: {missing}")


def verify_o1_manifest(path: Path, log_path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"O1 manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes = data.get("hashes") or {}
    safety = data.get("safety") or {}
    ramdisk = data.get("ramdisk") or {}
    expected_hashes = {
        "base_boot": EXPECTED_BASE_BOOT_SHA256,
        "nochange_repack_boot": EXPECTED_BASE_BOOT_SHA256,
        "boot_img": EXPECTED_O1_BOOT_SHA256,
        "boot_img_lz4": EXPECTED_O1_BOOT_LZ4_SHA256,
        "ap_tar_md5": EXPECTED_O1_AP_SHA256,
        "kernel_before": EXPECTED_KERNEL_SHA256,
        "kernel_after": EXPECTED_KERNEL_SHA256,
        "original_magisk_init_before": EXPECTED_INIT_SHA256,
        "original_magisk_init_after": EXPECTED_INIT_SHA256,
        "overlay_rc": EXPECTED_RC_SHA256,
        "overlay_service": EXPECTED_SERVICE_SHA256,
        "o0_daemon": EXPECTED_DAEMON_SHA256,
    }
    for key, expected in expected_hashes.items():
        if hashes.get(key) != expected:
            raise SystemExit(f"O1 manifest hash mismatch {key}: {hashes.get(key)!r}")
    expected_safety = {
        "boot_only": True,
        "host_only_build": True,
        "live_flash_authorized": False,
        "base_is_known_booting_magisk_boot": True,
        "stock_first_stage_preserved": True,
        "stock_magisk_init_preserved": True,
        "kernel_preserved": True,
        "configfs_write": False,
        "sysfs_write": False,
        "active_gadget_change": False,
        "module_insertions": False,
        "reboot_request": False,
        "persistent_partition_mount": False,
    }
    for key, expected in expected_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"O1 manifest safety mismatch {key}: {safety.get(key)!r}")
    intended = [
        "overlay.d/s22plus_o1_control.rc",
        "overlay.d/sbin/s22plus_o1_service.sh",
        "overlay.d/sbin/s22plus_o1_tty_echo",
    ]
    listing = ramdisk.get("listing_diff") or {}
    if data.get("tar_members") != [EXPECTED_MEMBER]:
        raise SystemExit("O1 manifest is not boot-only")
    if ramdisk.get("added_entries") != intended or ramdisk.get("replaced_entries") != []:
        raise SystemExit("O1 manifest ramdisk additions mismatch")
    if listing.get("added") != sorted(intended) or listing.get("removed") != []:
        raise SystemExit("O1 manifest ramdisk listing delta mismatch")
    append_log(log_path, f"o1_manifest={json.dumps(data, sort_keys=True)}")
    return data


def verify_o1_artifacts(root: Path, o1_root: Path, ap: Path, manifest: Path, log_path: Path) -> None:
    verify_ap(ap, EXPECTED_O1_AP_SHA256, "o1_candidate", log_path)
    verify_o1_manifest(manifest, log_path)
    files = {
        "boot_img": (o1_root / "boot.img", EXPECTED_O1_BOOT_SHA256),
        "boot_img_lz4": (o1_root / "odin4/boot.img.lz4", EXPECTED_O1_BOOT_LZ4_SHA256),
        "overlay_rc": (root / "workspace/public/src/android/s22plus_o1_control.rc", EXPECTED_RC_SHA256),
        "overlay_service": (root / "workspace/public/src/android/s22plus_o1_service.sh", EXPECTED_SERVICE_SHA256),
        "o0_daemon": (
            o1_root / "build/daemon/bin/s22plus_o0_tty_echo_v3403",
            EXPECTED_DAEMON_SHA256,
        ),
    }
    for label, (path, expected) in files.items():
        if not path.is_file():
            raise SystemExit(f"O1 {label} missing: {path}")
        actual = sha256_file(path)
        append_log(log_path, f"o1_{label}_sha256={actual}")
        if actual != expected:
            raise SystemExit(f"O1 {label} SHA mismatch: {actual}")


def offline_contract() -> dict[str, Any]:
    return {
        "target": EXPECTED_TARGET,
        "candidate": "O1 stock-first-stage USB control",
        "boot_only": True,
        "candidate_tar_members": [EXPECTED_MEMBER],
        "protocol_requests": 128,
        "host_tty_reopen_at": 64,
        "stock_first_stage_preserved": True,
        "stock_usb_gadget_preserved": True,
        "configfs_write": False,
        "sysfs_write": False,
        "module_insertion": False,
        "persistent_partition_mount": False,
        "volatile_status_only": True,
        "mandatory_rollback": True,
    }


def wait_for_host_tty(serial: str, requested: Path | None, timeout_sec: int) -> tuple[Path, dict[str, str]] | None:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            return select_host_tty(requested, serial)
        except RuntimeError:
            time.sleep(0.25)
    return None


def candidate_snapshot_reasons(snapshot: dict[str, str]) -> list[str]:
    expected = {
        "model": "SM-S906N",
        "device": "g0q",
        "incremental": "S906NKSS7FYG8",
        "boot_completed": "1",
        "boot_recovery": "0",
        "vbstate": "orange",
        "ttyGS0_char": "1",
        "boot_sha256": EXPECTED_O1_BOOT_SHA256,
        "uid": "0",
    }
    reasons = [f"{key}-mismatch" for key, value in expected.items() if snapshot.get(key) != value]
    if not snapshot.get("udc") or snapshot.get("udc") == "__MISSING__":
        reasons.append("udc-missing")
    if "adb" not in snapshot.get("usb_config", ""):
        reasons.append("stock-adb-config-missing")
    return reasons


def read_o1_evidence(serial: str) -> dict[str, Any]:
    command = "; ".join(
        [
            "printf 'marker='; if test -e /dev/.s22plus_o1_control_once; then echo 1; else echo 0; fi",
            "cat /dev/.s22plus_o1_status 2>/dev/null || true",
            "printf 'o1_service_state='; getprop init.svc.s22plus_o1_control",
            "printf 'o1_daemon_pid='; pidof s22plus_o1_tty_echo 2>/dev/null || true; echo",
        ]
    )
    result = adb_text(serial, command, root=True, timeout=20.0)
    return {"rc": result["rc"], "values": parse_key_values(result["stdout"]), "stderr": result["stderr"]}


def o1_evidence_reasons(evidence: dict[str, Any], stock: dict[str, Any]) -> list[str]:
    values = evidence.get("values") or {}
    expected = {
        "marker": "1",
        "result": "pass",
        "daemon_rc": "0",
        "restore_rc": "0",
        "o1_service_state": "stopped",
        "o1_daemon_pid": "",
    }
    reasons = [f"{key}-mismatch" for key, value in expected.items() if values.get(key, "") != value]
    if evidence.get("rc") != 0:
        reasons.append("evidence-read-failed")
    if not (
        stock.get("rc") == 0
        and stock.get("state") == "running"
        and stock.get("pid_present")
        and stock.get("tty_owner_count", 0) > 0
    ):
        reasons.append("stock-service-not-restored")
    return reasons


def wait_o1_postflight(serial: str, timeout_sec: int) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    deadline = time.monotonic() + timeout_sec
    evidence: dict[str, Any] = {}
    stock: dict[str, Any] = {}
    reasons = ["not-observed"]
    while time.monotonic() < deadline:
        evidence = read_o1_evidence(serial)
        stock = stock_service_state(serial)
        reasons = o1_evidence_reasons(evidence, stock)
        if not reasons:
            return evidence, stock, reasons
        time.sleep(0.25)
    return evidence, stock, reasons


def request_candidate_download(serial: str, log_path: Path) -> bool:
    result = run(["adb", "-s", serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"candidate_adb_reboot_download_rc={result.returncode}")
    append_log(log_path, result.stdout + result.stderr)
    return result.returncode == 0


def write_result(run_dir: Path, payload: dict[str, Any]) -> None:
    (run_dir / "result.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def missing_complete_timeline_phases(run_dir: Path) -> list[str]:
    path = run_dir / "timeline.json"
    if not path.is_file():
        return list(REQUIRED_LIVE_TIMELINE_PHASES)
    data = json.loads(path.read_text(encoding="utf-8"))
    if sorted(data.keys()) != ["events"] or not isinstance(data["events"], list):
        raise SystemExit("refusing non-canonical O1 timeline shape")
    names: list[str] = []
    for event in data["events"]:
        if not isinstance(event, dict) or sorted(event.keys()) != ["name", "timestamp_utc"]:
            raise SystemExit("refusing non-canonical O1 timeline event")
        names.append(event["name"])
    return [name for name in REQUIRED_LIVE_TIMELINE_PHASES if name not in names]


def validate_live_authorization(args: argparse.Namespace) -> None:
    if not args.live:
        return
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")
    if args.rollback_ack != ROLLBACK_ACK_TOKEN:
        raise SystemExit(f"--live requires --rollback-ack {ROLLBACK_ACK_TOKEN}")


def execute(args: argparse.Namespace) -> int:
    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_o1_stock_first_stage_control_live_gate.txt"
    append_log(log_path, f"target={EXPECTED_TARGET}")
    append_log(log_path, f"offline_contract={json.dumps(offline_contract(), sort_keys=True)}")

    odin = resolve(root, args.odin)
    o1_root = resolve(root, args.o1_root)
    o1_ap = resolve(root, args.o1_ap)
    o1_manifest = resolve(root, args.o1_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_agents_exception(root, log_path)
    verify_o1_artifacts(root, o1_root, o1_ap, o1_manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)
    if args.offline_check:
        print(json.dumps({"result": "offline-pass", "run_dir": str(run_dir), **offline_contract()}, indent=2))
        return 0

    selected_serial = require_current_android(log_path, args.serial)
    verify_partition_hash(log_path, selected_serial, "boot", EXPECTED_BASE_BOOT_SHA256, "preflight")
    verify_android_stability(log_path, selected_serial, args.preflight_samples, args.sample_interval_sec)
    preflight_stock = stock_service_state(selected_serial)
    if not (
        preflight_stock.get("state") == "running"
        and preflight_stock.get("pid_present")
        and preflight_stock.get("tty_owner_count", 0) > 0
    ):
        raise SystemExit(f"preflight DR-daemon ownership mismatch: {preflight_stock}")
    preflight_tty = wait_for_host_tty(selected_serial, args.host_tty, 5)
    if preflight_tty is None:
        raise SystemExit("preflight Samsung CDC ACM tty missing")
    concurrent_odin = odin_devices(odin, log_path, "preflight")
    if concurrent_odin:
        raise SystemExit(f"refusing concurrent Android and Odin transports: {concurrent_odin}")
    host_snapshot(run_dir, log_path, "preflight", odin)

    if not args.live:
        print(f"dry-run pass: O1 artifacts, rollback APs, policy, Android, boot hash, and stock tty verified; run={run_dir}")
        return 0
    validate_live_authorization(args)

    observers = start_observers(run_dir, selected_serial)
    result = "candidate-not-started"
    result_rc = 1
    candidate_error: str | None = None
    roundtrip: dict[str, Any] | None = None
    o1_evidence: dict[str, Any] | None = None
    stock_after: dict[str, Any] | None = None
    candidate_snapshot: dict[str, str] | None = None
    rollback_target: str | None = None
    rollback_device: str | None = None
    rollback_android: str | None = None
    candidate_flash_started = False
    session_started = True
    record_timeline_event(run_dir, "live_session_start")
    try:
        if not request_candidate_download(selected_serial, log_path):
            result = "pre-candidate-download-request-failed"
            result_rc = 2
            return result_rc
        odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
        if odin_device is None:
            result = "pre-candidate-download-missing"
            result_rc = 2
            return result_rc

        record_timeline_event(run_dir, "candidate_flash_start")
        candidate_flash_started = True
        flash_rc = flash_ap(odin, o1_ap, odin_device, log_path, "o1_candidate")
        record_timeline_event(run_dir, "candidate_flash_done")
        if flash_rc != 0:
            raise RuntimeError(f"candidate Odin flash failed rc={flash_rc}")
        if not wait_for_odin_absent(odin, log_path, "candidate-disconnect", args.odin_disconnect_sec):
            raise RuntimeError("original Odin endpoint did not disconnect")

        tty_match = wait_for_host_tty(selected_serial, args.host_tty, args.candidate_tty_wait_sec)
        if tty_match is None:
            raise RuntimeError("candidate stock CDC ACM tty did not appear")
        tty_path, tty_props = tty_match
        append_log(log_path, f"candidate_tty={tty_path} props={json.dumps(tty_props, sort_keys=True)}")
        record_timeline_event(run_dir, "candidate_boot_ready")
        time.sleep(args.daemon_settle_sec)

        roundtrip_events: list[dict[str, str]] = []
        record_timeline_event(run_dir, "candidate_protocol_start")
        roundtrip = run_roundtrips(
            tty_path,
            count=128,
            payload_size=256,
            reopen_at=64,
            frame_timeout=args.frame_timeout_sec,
            events=roundtrip_events,
        )
        record_timeline_event(run_dir, "candidate_protocol_done")
        if not (
            roundtrip.get("completed") == 128
            and roundtrip.get("sequence_continuity") is True
            and roundtrip.get("payload_equality") is True
            and roundtrip.get("host_reopen_completed") is True
        ):
            raise RuntimeError(f"O1 framed protocol incomplete: {roundtrip}")

        candidate_android = poll_android(
            log_path,
            args.candidate_android_wait_sec,
            expect_root=True,
            serial=selected_serial,
        )
        if candidate_android is None:
            raise RuntimeError("candidate Android/Magisk did not become ready")
        candidate_snapshot = device_snapshot(candidate_android)
        snapshot_reasons = candidate_snapshot_reasons(candidate_snapshot)
        if snapshot_reasons:
            raise RuntimeError(f"candidate snapshot mismatch: {snapshot_reasons}")
        o1_evidence, stock_after, evidence_reasons = wait_o1_postflight(candidate_android, 20)
        append_log(log_path, f"o1_evidence={json.dumps(o1_evidence, sort_keys=True)}")
        append_log(log_path, f"stock_after={json.dumps(stock_after, sort_keys=True)}")
        if evidence_reasons:
            raise RuntimeError(f"O1 volatile result/restore mismatch: {evidence_reasons}")
        result = "candidate-control-pass-rollback-pending"
    except Exception as exc:
        candidate_error = f"{type(exc).__name__}: {exc}"
        append_log(log_path, f"candidate_error={candidate_error}")
        result = "candidate-control-fail-rollback-pending"
    finally:
        if candidate_flash_started:
            try:
                request_candidate_download(selected_serial, log_path)
                rollback_odin = wait_for_odin(odin, log_path, "rollback-wait", args.rollback_wait_sec)
                if rollback_odin is None:
                    result = "rollback-download-missing-manual-recovery-required"
                    result_rc = 5
                else:
                    rollback = rollback_boot_only_from_download(
                        odin=odin,
                        rollback_ap=magisk_rollback_ap,
                        stock_boot_fallback_ap=stock_rollback_ap,
                        odin_device=rollback_odin,
                        run_dir=run_dir,
                        log_path=log_path,
                        rollback_target=ROLLBACK_MAGISK,
                        android_wait_sec=args.rollback_android_wait_sec,
                        label="o1",
                    )
                    rollback_target = rollback.rollback_target
                    rollback_device = rollback.rollback_device
                    rollback_android = rollback.android_serial
                    if rollback.rc != 0 or rollback.android_serial is None:
                        result = "rollback-failed"
                        result_rc = 6
                    else:
                        verify_android_stability(
                            log_path,
                            rollback.android_serial,
                            args.postflight_samples,
                            args.sample_interval_sec,
                        )
                        restored_stock = stock_service_state(rollback.android_serial)
                        if not (
                            restored_stock.get("state") == "running"
                            and restored_stock.get("pid_present")
                            and restored_stock.get("tty_owner_count", 0) > 0
                        ):
                            result = "rollback-android-stock-tty-mismatch"
                            result_rc = 7
                        elif candidate_error is None and roundtrip is not None:
                            result = "pass"
                            result_rc = 0
                        else:
                            result = "candidate-fail-rollback-pass"
                            result_rc = 1
            except (Exception, SystemExit) as exc:
                append_log(log_path, f"rollback_exception={type(exc).__name__}: {exc}")
                result = "rollback-exception-manual-recovery-required"
                result_rc = 8
        for observer in observers:
            observer.stop()
        if session_started:
            record_timeline_event(run_dir, "live_session_end")
        if result == "pass":
            timeline_missing = missing_complete_timeline_phases(run_dir)
            if timeline_missing:
                append_log(log_path, f"timeline_missing={timeline_missing}")
                result = "timeline-incomplete"
                result_rc = 9
        write_result(
            run_dir,
            {
                "schema": EXPECTED_SCHEMA,
                "target": EXPECTED_TARGET,
                "result": result,
                "rc": result_rc,
                "candidate_ap_sha256": EXPECTED_O1_AP_SHA256,
                "candidate_boot_sha256": EXPECTED_O1_BOOT_SHA256,
                "candidate_error": candidate_error,
                "roundtrip": roundtrip,
                "o1_evidence": o1_evidence,
                "stock_service_after": stock_after,
                "candidate_snapshot": candidate_snapshot,
                "rollback_target": rollback_target,
                "rollback_device": rollback_device,
                "rollback_android_serial": DISPLAY_SERIAL_REDACTED if rollback_android else None,
                "safety": offline_contract(),
            },
        )
    print(json.dumps({"result": result, "rc": result_rc, "run_dir": str(run_dir)}, indent=2))
    return result_rc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--o1-root", type=Path, default=DEFAULT_O1_ROOT)
    parser.add_argument("--o1-ap", type=Path, default=DEFAULT_O1_AP)
    parser.add_argument("--o1-manifest", type=Path, default=DEFAULT_O1_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial")
    parser.add_argument("--host-tty", type=Path)
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--odin-disconnect-sec", type=int, default=30)
    parser.add_argument("--candidate-tty-wait-sec", type=int, default=150)
    parser.add_argument("--candidate-android-wait-sec", type=int, default=180)
    parser.add_argument("--rollback-wait-sec", type=int, default=300)
    parser.add_argument("--rollback-android-wait-sec", type=int, default=300)
    parser.add_argument("--daemon-settle-sec", type=float, default=1.0)
    parser.add_argument("--frame-timeout-sec", type=float, default=3.0)
    parser.add_argument("--preflight-samples", type=int, default=2)
    parser.add_argument("--postflight-samples", type=int, default=3)
    parser.add_argument("--sample-interval-sec", type=float, default=2.0)
    parser.add_argument("--offline-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--ack")
    parser.add_argument("--rollback-ack")
    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    for name in [
        "odin_wait_sec",
        "odin_disconnect_sec",
        "candidate_tty_wait_sec",
        "candidate_android_wait_sec",
        "rollback_wait_sec",
        "rollback_android_wait_sec",
    ]:
        if getattr(args, name) <= 0:
            raise SystemExit(f"--{name.replace('_', '-')} must be positive")
    if args.daemon_settle_sec < 0 or args.frame_timeout_sec <= 0 or args.sample_interval_sec < 0:
        raise SystemExit("settle/frame/sample intervals are invalid")
    if args.preflight_samples < 1 or args.postflight_samples < 1:
        raise SystemExit("preflight/postflight samples must be positive")
    if args.offline_check and args.live:
        raise SystemExit("--offline-check and --live are mutually exclusive")
    validate_live_authorization(args)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    validate_args(args)
    return execute(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
