#!/usr/bin/env python3
"""Guarded S22+ O1.1 stock-first-stage control live gate.

Offline and connected dry-runs are non-destructive. Live mode additionally
requires the active SHA-pinned AGENTS.md exception and two exact ack tokens.
The candidate changes only the O1 service SELinux domain.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from s22plus_m3_observable_live_gate import (
    DEFAULT_MAGISK_ROLLBACK_AP,
    DEFAULT_ODIN,
    DEFAULT_RUN_ROOT,
    EXPECTED_MAGISK_AP_SHA256,
    ROLLBACK_MAGISK,
    append_log,
    collect_android_pstore,
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
    device_snapshot,
    run_roundtrips,
    select_host_tty,
    start_observers,
    stock_service_state,
)
import s22plus_o1_stock_first_stage_control_live_gate as o1_live


LIVE_ACK_TOKEN = "S22PLUS-O11-SECLABEL-CONTROL-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-O11-SECLABEL-CONTROL-ROLLBACK"
EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_MEMBER = "boot.img.lz4"
EXPECTED_SCHEMA = "s22plus_o11_stock_first_stage_control_live_v1"
DISPLAY_SERIAL_REDACTED = "<S22_SERIAL_REDACTED>"

EXPECTED_BASE_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_O11_BOOT_SHA256 = "1e59b172edda0d2c717a93021c9084af1393c0c4db7d28eeb10e06c0b1787b0d"
EXPECTED_O11_BOOT_LZ4_SHA256 = "afef7ff56c7efd54cbb094b1a36bc8068cb3c780ccc8e2667baee9493c6ca6e6"
EXPECTED_O11_AP_SHA256 = "c43eeb83cedb2db3e0758de71050ef2960765740face7378fcc285a5b8188730"
EXPECTED_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_INIT_SHA256 = "383670a7ba3a6a4b79e5f3467e1da4b66a5df66a9b356ab9f70916854dd6b468"
EXPECTED_RC_SHA256 = "36363a0c6aedbd901310ac5de7bcdd9b85c2a2f985f92a0d78d86daefef8503b"
EXPECTED_SERVICE_SHA256 = "3e5c000308acaa52495c1b235b9f3e777123e3ddeb1e51f01b7461a38593be93"
EXPECTED_DAEMON_SHA256 = "a82cd32f83afc20d40fc74a9402896ae07378811f259913ed6df7cbc540f858c"
EXPECTED_SECLABEL = "u:r:magisk:s0"

DEFAULT_O11_ROOT = Path("workspace/private/outputs/s22plus_native_init/o11_magisk_overlay_v0_1")
DEFAULT_O11_AP = DEFAULT_O11_ROOT / "odin4/AP.tar.md5"
DEFAULT_O11_MANIFEST = DEFAULT_O11_ROOT / "manifest.json"
ACTIVE_EXCEPTION_HEADING = (
    "**Narrow operator-authorized exception (2026-07-10, S22+ O1.1 "
    "SELinux-domain USB control boot-only live gate):**"
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
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_o11_stock_first_stage_control_live_gate_{utc_stamp()}")
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise SystemExit(f"could not allocate run directory under {base.parent}")


def policy_required_markers() -> list[str]:
    return [
        "S22+ O1.1 SELinux-domain USB control boot-only",
        "workspace/public/src/scripts/revalidation/s22plus_o11_stock_first_stage_control_live_gate.py",
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        EXPECTED_TARGET,
        EXPECTED_O11_AP_SHA256,
        EXPECTED_O11_BOOT_SHA256,
        EXPECTED_O11_BOOT_LZ4_SHA256,
        EXPECTED_BASE_BOOT_SHA256,
        EXPECTED_KERNEL_SHA256,
        EXPECTED_INIT_SHA256,
        EXPECTED_RC_SHA256,
        EXPECTED_SERVICE_SHA256,
        EXPECTED_DAEMON_SHA256,
        EXPECTED_MAGISK_AP_SHA256,
        EXPECTED_STOCK_BOOT_AP_SHA256,
        EXPECTED_STOCK_BOOT_RAW_SHA256,
        "seclabel u:r:magisk:s0",
        "bounded two-attempt ADB Download retry",
        "automatic postrollback retained-log collection",
        "128-request framed O0 protocol",
        "mandatory boot-only rollback",
        "no configfs/sysfs write",
        "no module insertion",
        "no persistent partition mount",
    ]


def active_exception_segment(text: str) -> str:
    start = text.find(ACTIVE_EXCEPTION_HEADING)
    if start < 0:
        return ""
    end = text.find("\n   **", start + len(ACTIVE_EXCEPTION_HEADING))
    return text[start:] if end < 0 else text[start:end]


def verify_agents_exception(root: Path, log_path: Path) -> None:
    segment = active_exception_segment((root / "AGENTS.md").read_text(encoding="utf-8"))
    normalized = " ".join(segment.split())
    missing = [marker for marker in policy_required_markers() if marker not in normalized]
    append_log(log_path, f"o11_agents_exception_present={int(bool(segment))}")
    append_log(log_path, f"o11_agents_exception_missing={missing}")
    if not segment or "Consumed exception" in segment or "Consumed/retired" in segment:
        raise SystemExit("active O1.1 AGENTS.md exception is absent or consumed")
    if missing:
        raise SystemExit(f"O1.1 AGENTS.md exception missing markers: {missing}")


def verify_o11_manifest(path: Path, log_path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"O1.1 manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes = data.get("hashes") or {}
    safety = data.get("safety") or {}
    delta = data.get("o11_delta") or {}
    ramdisk = data.get("ramdisk") or {}
    runtime = data.get("runtime_contract") or {}
    expected_hashes = {
        "base_boot": EXPECTED_BASE_BOOT_SHA256,
        "nochange_repack_boot": EXPECTED_BASE_BOOT_SHA256,
        "boot_img": EXPECTED_O11_BOOT_SHA256,
        "boot_img_lz4": EXPECTED_O11_BOOT_LZ4_SHA256,
        "ap_tar_md5": EXPECTED_O11_AP_SHA256,
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
            raise SystemExit(f"O1.1 manifest hash mismatch {key}: {hashes.get(key)!r}")
    required_safety = {
        "boot_only": True,
        "host_only_build": True,
        "live_flash_authorized": False,
        "base_is_known_booting_magisk_boot": True,
        "stock_first_stage_preserved": True,
        "stock_magisk_init_preserved": True,
        "kernel_preserved": True,
        "service_seclabel": EXPECTED_SECLABEL,
        "selinux_policy_file_change": False,
        "configfs_write": False,
        "sysfs_write": False,
        "active_gadget_change": False,
        "module_insertions": False,
        "reboot_request": False,
        "persistent_partition_mount": False,
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"O1.1 manifest safety mismatch {key}: {safety.get(key)!r}")
    if data.get("schema") != "s22plus_o11_magisk_overlay_build_v1" or data.get("variant") != "O1.1":
        raise SystemExit("O1.1 manifest identity mismatch")
    if data.get("tar_members") != [EXPECTED_MEMBER]:
        raise SystemExit("O1.1 manifest is not boot-only")
    intended = [
        "overlay.d/s22plus_o1_control.rc",
        "overlay.d/sbin/s22plus_o1_service.sh",
        "overlay.d/sbin/s22plus_o1_tty_echo",
    ]
    listing = ramdisk.get("listing_diff") or {}
    if ramdisk.get("added_entries") != intended or ramdisk.get("replaced_entries") != []:
        raise SystemExit("O1.1 manifest ramdisk additions mismatch")
    if listing.get("added") != sorted(intended) or listing.get("removed") != []:
        raise SystemExit("O1.1 manifest ramdisk listing delta mismatch")
    if runtime.get("service_domain") != EXPECTED_SECLABEL:
        raise SystemExit("O1.1 manifest runtime service domain mismatch")
    if delta.get("added_service_option") != "seclabel u:r:magisk:s0" or delta.get("other_behavioral_delta") is not False:
        raise SystemExit("O1.1 manifest rc delta mismatch")
    append_log(log_path, f"o11_manifest={json.dumps(data, sort_keys=True)}")
    return data


def verify_o11_artifacts(root: Path, out_root: Path, ap: Path, manifest: Path, log_path: Path) -> None:
    verify_ap(ap, EXPECTED_O11_AP_SHA256, "o11_candidate", log_path)
    verify_o11_manifest(manifest, log_path)
    files = {
        "boot_img": (out_root / "boot.img", EXPECTED_O11_BOOT_SHA256),
        "boot_img_lz4": (out_root / "odin4/boot.img.lz4", EXPECTED_O11_BOOT_LZ4_SHA256),
        "overlay_rc": (root / "workspace/public/src/android/s22plus_o11_control.rc", EXPECTED_RC_SHA256),
        "overlay_service": (
            root / "workspace/public/src/android/s22plus_o1_service.sh",
            EXPECTED_SERVICE_SHA256,
        ),
        "o0_daemon": (
            out_root / "build/daemon/bin/s22plus_o0_tty_echo_v3403",
            EXPECTED_DAEMON_SHA256,
        ),
    }
    for label, (path, expected) in files.items():
        if not path.is_file():
            raise SystemExit(f"O1.1 {label} missing: {path}")
        actual = sha256_file(path)
        append_log(log_path, f"o11_{label}_sha256={actual}")
        if actual != expected:
            raise SystemExit(f"O1.1 {label} SHA mismatch: {actual}")


def offline_contract() -> dict[str, Any]:
    return {
        "target": EXPECTED_TARGET,
        "candidate": "O1.1 SELinux-domain stock-first-stage USB control",
        "boot_only": True,
        "candidate_tar_members": [EXPECTED_MEMBER],
        "service_seclabel": EXPECTED_SECLABEL,
        "selinux_policy_file_change": False,
        "protocol_requests": 128,
        "host_tty_reopen_at": 64,
        "download_retry_max_attempts": 2,
        "automatic_retained_log_collection": True,
        "stock_first_stage_preserved": True,
        "stock_usb_gadget_preserved": True,
        "configfs_write": False,
        "sysfs_write": False,
        "module_insertion": False,
        "persistent_partition_mount": False,
        "mandatory_rollback": True,
    }


def adb_serial_ready(serial: str) -> bool:
    result = run(["adb", "devices", "-l"], timeout=10.0)
    for line in result.stdout.splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 2 and fields[0] == serial and fields[1] == "device":
            return True
    return False


def probe_transition_after_adb_error(
    odin: Path,
    serial: str,
    log_path: Path,
    timeout_sec: float,
) -> str:
    deadline = time.monotonic() + timeout_sec
    started = time.monotonic()
    saw_adb_absent = False
    while time.monotonic() < deadline:
        devices = odin_devices(odin, log_path, "adb-reboot-transition-probe")
        if len(devices) == 1:
            return "odin"
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices after adb error: {devices}")
        adb_ready = adb_serial_ready(serial)
        if not adb_ready:
            saw_adb_absent = True
        elif saw_adb_absent or time.monotonic() - started >= 2.0:
            return "adb"
        time.sleep(0.5)
    return "none"


def request_download_with_retry(
    serial: str,
    log_path: Path,
    odin: Path,
    *,
    max_attempts: int = 2,
    transition_wait_sec: float = 20.0,
    run_command: Callable[..., Any] = run,
    transition_probe: Callable[[Path, str, Path, float], str] = probe_transition_after_adb_error,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for index in range(max_attempts):
        result = run_command(["adb", "-s", serial, "reboot", "download"], timeout=20.0)
        entry = {
            "attempt": index + 1,
            "rc": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        attempts.append(entry)
        append_log(log_path, f"adb_reboot_download_attempt_{index + 1}_rc={result.returncode}")
        append_log(log_path, result.stdout + result.stderr)
        if result.returncode == 0:
            return {"success": True, "transition": "command-accepted", "attempts": attempts}
        transition = transition_probe(odin, serial, log_path, transition_wait_sec)
        entry["post_error_transition"] = transition
        if transition == "odin":
            return {"success": True, "transition": "odin-after-adb-error", "attempts": attempts}
        if transition != "adb" or index + 1 >= max_attempts:
            append_log(log_path, f"adb_reboot_download_retry_stopped transition={transition}")
            break
    return {"success": False, "transition": "not-observed", "attempts": attempts}


def candidate_snapshot_reasons(snapshot: dict[str, str]) -> list[str]:
    expected = {
        "model": "SM-S906N",
        "device": "g0q",
        "incremental": "S906NKSS7FYG8",
        "boot_completed": "1",
        "boot_recovery": "0",
        "vbstate": "orange",
        "ttyGS0_char": "1",
        "boot_sha256": EXPECTED_O11_BOOT_SHA256,
        "uid": "0",
    }
    reasons = [f"{key}-mismatch" for key, value in expected.items() if snapshot.get(key) != value]
    if not snapshot.get("udc") or snapshot.get("udc") == "__MISSING__":
        reasons.append("udc-missing")
    if "adb" not in snapshot.get("usb_config", ""):
        reasons.append("stock-adb-config-missing")
    return reasons


def readiness_reasons(evidence: dict[str, Any], stock: dict[str, Any]) -> list[str]:
    values = evidence.get("values") or {}
    expected = {"marker": "1", "phase": "daemon-running", "o1_service_state": "running"}
    reasons = [f"{key}-mismatch" for key, value in expected.items() if values.get(key, "") != value]
    if evidence.get("rc") != 0:
        reasons.append("evidence-read-failed")
    if not (
        stock.get("rc") == 0
        and stock.get("state") == "stopped"
        and not stock.get("pid_present")
        and stock.get("tty_owner_count") == 0
    ):
        reasons.append("stock-service-not-handed-off")
    return reasons


def wait_runtime_ready(serial: str, timeout_sec: int) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    deadline = time.monotonic() + timeout_sec
    evidence: dict[str, Any] = {}
    stock: dict[str, Any] = {}
    reasons = ["not-observed"]
    while time.monotonic() < deadline:
        evidence = o1_live.read_o1_evidence(serial)
        stock = stock_service_state(serial)
        reasons = readiness_reasons(evidence, stock)
        if not reasons:
            return evidence, stock, reasons
        time.sleep(0.25)
    return evidence, stock, reasons


def collect_retained_after_rollback(run_dir: Path, log_path: Path, serial: str) -> dict[str, Any]:
    marker_found = collect_android_pstore(
        run_dir,
        log_path,
        "postrollback_o11",
        serial,
        marker="s22plus_o1_control",
    )
    last_kmsg = run_dir / "android_pstore/postrollback_o11_last_kmsg.bin"
    collected = last_kmsg.is_file()
    result = {
        "last_kmsg_collected": collected,
        "last_kmsg_bytes": last_kmsg.stat().st_size if collected else 0,
        "o11_marker_found": marker_found,
    }
    append_log(log_path, f"o11_retained_collection={json.dumps(result, sort_keys=True)}")
    return result


def validate_live_authorization(args: argparse.Namespace) -> None:
    if not args.live:
        return
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")
    if args.rollback_ack != ROLLBACK_ACK_TOKEN:
        raise SystemExit(f"--live requires --rollback-ack {ROLLBACK_ACK_TOKEN}")


def write_result(run_dir: Path, payload: dict[str, Any]) -> None:
    (run_dir / "result.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def execute(args: argparse.Namespace) -> int:
    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_o11_stock_first_stage_control_live_gate.txt"
    append_log(log_path, f"target={EXPECTED_TARGET}")
    append_log(log_path, f"offline_contract={json.dumps(offline_contract(), sort_keys=True)}")

    odin = resolve(root, args.odin)
    out_root = resolve(root, args.o11_root)
    candidate_ap = resolve(root, args.o11_ap)
    manifest = resolve(root, args.o11_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_o11_artifacts(root, out_root, candidate_ap, manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)
    if args.offline_check:
        print(json.dumps({"result": "offline-pass", "run_dir": str(run_dir), **offline_contract()}, indent=2))
        return 0

    selected_serial = require_current_android(log_path, args.serial)
    verify_partition_hash(log_path, selected_serial, "boot", EXPECTED_BASE_BOOT_SHA256, "preflight")
    verify_android_stability(log_path, selected_serial, args.preflight_samples, args.sample_interval_sec)
    stock_before = stock_service_state(selected_serial)
    if not (
        stock_before.get("state") == "running"
        and stock_before.get("pid_present")
        and stock_before.get("tty_owner_count", 0) > 0
    ):
        raise SystemExit(f"preflight DR-daemon ownership mismatch: {stock_before}")
    if o1_live.wait_for_host_tty(selected_serial, args.host_tty, 5) is None:
        raise SystemExit("preflight Samsung CDC ACM tty missing")
    concurrent_odin = odin_devices(odin, log_path, "preflight")
    if concurrent_odin:
        raise SystemExit(f"refusing concurrent Android and Odin transports: {concurrent_odin}")
    host_snapshot(run_dir, log_path, "preflight", odin)

    if not args.live:
        print(
            "dry-run pass: O1.1 artifacts, rollback APs, Android, boot hash, and stock tty verified; "
            f"live policy intentionally not required; run={run_dir}"
        )
        return 0

    verify_agents_exception(root, log_path)
    validate_live_authorization(args)
    observers = start_observers(run_dir, selected_serial)
    result = "candidate-not-started"
    result_rc = 1
    candidate_error: str | None = None
    roundtrip: dict[str, Any] | None = None
    readiness: dict[str, Any] | None = None
    ready_stock: dict[str, Any] | None = None
    final_evidence: dict[str, Any] | None = None
    final_stock: dict[str, Any] | None = None
    candidate_snapshot: dict[str, str] | None = None
    download_requests: list[dict[str, Any]] = []
    rollback_target: str | None = None
    rollback_device: str | None = None
    rollback_android: str | None = None
    retained: dict[str, Any] | None = None
    candidate_flash_started = False
    record_timeline_event(run_dir, "live_session_start")
    try:
        initial_download = request_download_with_retry(selected_serial, log_path, odin)
        download_requests.append({"phase": "candidate", **initial_download})
        if not initial_download["success"]:
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
        flash_rc = flash_ap(odin, candidate_ap, odin_device, log_path, "o11_candidate")
        record_timeline_event(run_dir, "candidate_flash_done")
        if flash_rc != 0:
            raise RuntimeError(f"candidate Odin flash failed rc={flash_rc}")
        if not wait_for_odin_absent(odin, log_path, "candidate-disconnect", args.odin_disconnect_sec):
            raise RuntimeError("original Odin endpoint did not disconnect")

        tty_match = o1_live.wait_for_host_tty(selected_serial, args.host_tty, args.candidate_tty_wait_sec)
        if tty_match is None:
            raise RuntimeError("candidate stock CDC ACM tty did not appear")
        tty_path, tty_props = tty_match
        append_log(log_path, f"candidate_tty={tty_path} props={json.dumps(tty_props, sort_keys=True)}")

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
        record_timeline_event(run_dir, "candidate_boot_ready")
        readiness, ready_stock, ready_reasons = wait_runtime_ready(candidate_android, args.runtime_ready_wait_sec)
        append_log(log_path, f"o11_readiness={json.dumps(readiness, sort_keys=True)}")
        append_log(log_path, f"o11_ready_stock={json.dumps(ready_stock, sort_keys=True)}")
        if ready_reasons:
            raise RuntimeError(f"O1.1 daemon readiness mismatch: {ready_reasons}")

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
            raise RuntimeError(f"O1.1 framed protocol incomplete: {roundtrip}")
        final_evidence, final_stock, final_reasons = o1_live.wait_o1_postflight(candidate_android, 20)
        append_log(log_path, f"o11_final_evidence={json.dumps(final_evidence, sort_keys=True)}")
        append_log(log_path, f"o11_final_stock={json.dumps(final_stock, sort_keys=True)}")
        if final_reasons:
            raise RuntimeError(f"O1.1 volatile result/restore mismatch: {final_reasons}")
        result = "candidate-control-pass-rollback-pending"
    except Exception as exc:
        candidate_error = f"{type(exc).__name__}: {exc}"
        append_log(log_path, f"candidate_error={candidate_error}")
        result = "candidate-control-fail-rollback-pending"
    finally:
        if candidate_flash_started:
            try:
                rollback_download = request_download_with_retry(selected_serial, log_path, odin)
                download_requests.append({"phase": "rollback", **rollback_download})
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
                        label="o11",
                    )
                    rollback_target = rollback.rollback_target
                    rollback_device = rollback.rollback_device
                    rollback_android = rollback.android_serial
                    if rollback.rc != 0 or rollback.android_serial is None:
                        result = "rollback-failed"
                        result_rc = 6
                    else:
                        retained = collect_retained_after_rollback(
                            run_dir, log_path, rollback.android_serial
                        )
                        verify_android_stability(
                            log_path,
                            rollback.android_serial,
                            args.postflight_samples,
                            args.sample_interval_sec,
                        )
                        restored_stock = stock_service_state(rollback.android_serial)
                        if not retained.get("last_kmsg_collected"):
                            result = "rollback-retained-collection-missing"
                            result_rc = 10
                        elif not (
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
        record_timeline_event(run_dir, "live_session_end")
        if result == "pass":
            missing = o1_live.missing_complete_timeline_phases(run_dir)
            if missing:
                append_log(log_path, f"timeline_missing={missing}")
                result = "timeline-incomplete"
                result_rc = 9
        write_result(
            run_dir,
            {
                "schema": EXPECTED_SCHEMA,
                "target": EXPECTED_TARGET,
                "result": result,
                "rc": result_rc,
                "candidate_ap_sha256": EXPECTED_O11_AP_SHA256,
                "candidate_boot_sha256": EXPECTED_O11_BOOT_SHA256,
                "candidate_error": candidate_error,
                "candidate_snapshot": candidate_snapshot,
                "runtime_readiness": readiness,
                "runtime_ready_stock": ready_stock,
                "roundtrip": roundtrip,
                "final_evidence": final_evidence,
                "final_stock": final_stock,
                "download_requests": download_requests,
                "rollback_target": rollback_target,
                "rollback_device": rollback_device,
                "rollback_android_serial": DISPLAY_SERIAL_REDACTED if rollback_android else None,
                "retained": retained,
                "safety": offline_contract(),
            },
        )
    print(json.dumps({"result": result, "rc": result_rc, "run_dir": str(run_dir)}, indent=2))
    return result_rc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--o11-root", type=Path, default=DEFAULT_O11_ROOT)
    parser.add_argument("--o11-ap", type=Path, default=DEFAULT_O11_AP)
    parser.add_argument("--o11-manifest", type=Path, default=DEFAULT_O11_MANIFEST)
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
    parser.add_argument("--runtime-ready-wait-sec", type=int, default=60)
    parser.add_argument("--rollback-wait-sec", type=int, default=300)
    parser.add_argument("--rollback-android-wait-sec", type=int, default=300)
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
        "runtime_ready_wait_sec",
        "rollback_wait_sec",
        "rollback_android_wait_sec",
    ]:
        if getattr(args, name) <= 0:
            raise SystemExit(f"--{name.replace('_', '-')} must be positive")
    if args.frame_timeout_sec <= 0 or args.sample_interval_sec < 0:
        raise SystemExit("frame/sample intervals are invalid")
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
