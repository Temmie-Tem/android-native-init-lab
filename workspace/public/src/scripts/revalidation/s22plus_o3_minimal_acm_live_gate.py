#!/usr/bin/env python3
"""Guarded S22+ O3 direct-PID1 minimal generic-ACM live gate."""

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
    collect_android_pstore,
    flash_ap,
    host_snapshot,
    odin_devices,
    require_current_android,
    repo_root,
    resolve,
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
    HostTTY,
    REQUEST,
    RESPONSE,
    decode_frame,
    encode_frame,
    parse_key_values,
    read_frame,
    run_roundtrips,
    select_host_tty,
    start_observers,
    write_all,
)
from s22plus_o11_stock_first_stage_control_live_gate import request_download_with_retry


LIVE_ACK_TOKEN = "S22PLUS-O3-MINIMAL-ACM-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-O3-MINIMAL-ACM-ROLLBACK-FROM-DOWNLOAD"
ACTIVE_EXCEPTION_HEADING = (
    "**Narrow operator-authorized exception (2026-07-10, S22+ O3 direct-PID1 "
    "minimal generic-ACM boot-only live gate):**"
)

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_SCHEMA = "s22plus_o3_minimal_acm_live_v1"
EXPECTED_MEMBER = "boot.img.lz4"
EXPECTED_BASE_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_PLAN_COUNT = 59
EXPECTED_GATE_COUNT = 8
EXPECTED_PLAN_TSV_SHA256 = "a34ebbad3b5d770f133e37a450cc3007e4a84ab831788484680e88aad6b3d534"
EXPECTED_PLAN_HEADER_SHA256 = "45727cff30952096d9604682a3ba3d284807a75e6622ed4c8ae57bc153d5b863"
EXPECTED_INIT_SHA256 = "7b2785687482971e4358575d555e49af402ceac2ee72136afdfeff3ece4b95cc"
EXPECTED_CONTROL_SHA256 = "2cb881f420dccd909610c4e3822adf6439fbe443460ee61644178f38509e5570"
EXPECTED_BOOT_SHA256 = "4f4a073f79b47c0a6a3924fabf09b2389c62bb731ed3355ebb83e48c53868609"
EXPECTED_BOOT_LZ4_SHA256 = "5421281a463cbca00a2a1fcec00af96f21f827af30f3b107ae326c364d9264fb"
EXPECTED_AP_SHA256 = "41b7e32424a809cec6ac7bded281b9ac355a9f3d2d0a3727f8b02de6d1e757f7"
EXPECTED_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_USB_SERIAL = "S22O3ACM01"
EXPECTED_MARKER = "S22_NATIVE_INIT_O3_MINIMAL_ACM"

DEFAULT_O3_ROOT = Path("workspace/private/outputs/s22plus_native_init/o3_minimal_acm_v0_1")
DEFAULT_O3_AP = DEFAULT_O3_ROOT / "odin4/AP.tar.md5"
DEFAULT_O3_MANIFEST = DEFAULT_O3_ROOT / "manifest.json"
REQUIRED_TIMELINE_PHASES = [
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
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_o3_minimal_acm_live_gate_{utc_stamp()}")
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise SystemExit(f"could not allocate run directory under {base.parent}")


def active_exception_segment(text: str) -> str:
    start = text.find(ACTIVE_EXCEPTION_HEADING)
    if start < 0:
        return ""
    end = text.find("\n   **", start + len(ACTIVE_EXCEPTION_HEADING))
    return text[start:] if end < 0 else text[start:end]


def policy_markers() -> list[str]:
    return [
        "S22+ O3 direct-PID1 minimal generic-ACM boot-only",
        "workspace/public/src/scripts/revalidation/s22plus_o3_minimal_acm_live_gate.py",
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        EXPECTED_TARGET,
        EXPECTED_AP_SHA256,
        EXPECTED_BOOT_SHA256,
        EXPECTED_INIT_SHA256,
        EXPECTED_CONTROL_SHA256,
        EXPECTED_PLAN_TSV_SHA256,
        EXPECTED_BASE_BOOT_SHA256,
        EXPECTED_MAGISK_AP_SHA256,
        EXPECTED_STOCK_BOOT_AP_SHA256,
        EXPECTED_STOCK_BOOT_RAW_SHA256,
        "128-request framed O0 protocol",
        "O3 STATUS",
        "mandatory boot-only rollback",
        "manual Download-mode entry",
        "a600000.ssusb/mode=peripheral",
        "a600000.dwc3",
        "no non-boot partition write",
    ]


def verify_agents_exception(root: Path, log_path: Path, *, allow_consumed: bool = False) -> None:
    segment = active_exception_segment((root / "AGENTS.md").read_text(encoding="utf-8"))
    normalized = " ".join(segment.split())
    missing = [marker for marker in policy_markers() if marker not in normalized]
    consumed = "Consumed exception" in segment or "Consumed/retired" in segment
    append_log(log_path, f"o3_agents_exception_present={int(bool(segment))}")
    append_log(log_path, f"o3_agents_exception_consumed={int(consumed)}")
    append_log(log_path, f"o3_agents_exception_missing={missing}")
    if not segment or (consumed and not allow_consumed):
        raise SystemExit("active O3 AGENTS.md exception is absent or consumed")
    if missing:
        raise SystemExit(f"O3 AGENTS.md exception missing markers: {missing}")


def verify_manifest(path: Path, log_path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"O3 manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes = data.get("hashes") or {}
    safety = data.get("safety") or {}
    plan = data.get("plan") or {}
    ramdisk = data.get("ramdisk") or {}
    expected_hashes = {
        "base_boot": EXPECTED_BASE_BOOT_SHA256,
        "nochange_repack_boot": EXPECTED_BASE_BOOT_SHA256,
        "plan_tsv": EXPECTED_PLAN_TSV_SHA256,
        "plan_header": EXPECTED_PLAN_HEADER_SHA256,
        "o3_init": EXPECTED_INIT_SHA256,
        "o3_control": EXPECTED_CONTROL_SHA256,
        "kernel": EXPECTED_KERNEL_SHA256,
        "boot_img": EXPECTED_BOOT_SHA256,
        "boot_img_lz4": EXPECTED_BOOT_LZ4_SHA256,
        "ap_tar_md5": EXPECTED_AP_SHA256,
    }
    for key, expected in expected_hashes.items():
        if hashes.get(key) != expected:
            raise SystemExit(f"O3 manifest hash mismatch {key}: {hashes.get(key)!r}")
    required_safety = {
        "boot_only": True,
        "host_only_build": True,
        "live_flash_authorized": False,
        "requires_new_sha_pinned_agents_exception_before_flash": True,
        "base_is_known_booting_magisk_boot": True,
        "kernel_changed": False,
        "mkbootimg_from_scratch": False,
        "no_android_or_magisk_handoff": True,
        "auto_reboot": False,
        "reboot_syscall": False,
        "persistent_partition_mount": False,
        "block_device_writes": False,
        "module_binary_injection": False,
        "module_source": "stock vendor_boot /lib/modules",
        "configfs_runtime_gadget": "one generic acm.usb0 function",
        "udc_binding": "a600000.dwc3 only",
        "eud_enable": False,
        "sec_debug_trigger": False,
        "pmic_typec_power_write": False,
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"O3 manifest safety mismatch {key}: {safety.get(key)!r}")
    if data.get("schema") != "s22plus_o3_minimal_acm_build_v1" or data.get("target") != EXPECTED_TARGET:
        raise SystemExit("O3 manifest schema/target mismatch")
    if data.get("tar_members") != [EXPECTED_MEMBER]:
        raise SystemExit("O3 manifest is not a single-member boot AP")
    if plan.get("module_count") != EXPECTED_PLAN_COUNT or plan.get("tsv_sha256") != EXPECTED_PLAN_TSV_SHA256:
        raise SystemExit("O3 manifest module plan mismatch")
    if ramdisk.get("replaced_entry") != "init" or ramdisk.get("added_entry") != "s22plus_o3_tty_control":
        raise SystemExit("O3 manifest ramdisk delta mismatch")
    if ramdisk.get("module_files_injected") != 0:
        raise SystemExit("O3 manifest unexpectedly injects module binaries")
    append_log(log_path, f"o3_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    return data


def verify_artifacts(
    *,
    root: Path,
    out_root: Path,
    candidate_ap: Path,
    manifest_path: Path,
    magisk_rollback_ap: Path,
    stock_rollback_ap: Path,
    log_path: Path,
) -> dict[str, Any]:
    verify_ap(candidate_ap, EXPECTED_AP_SHA256, "o3_candidate", log_path)
    manifest = verify_manifest(manifest_path, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)
    files = {
        "boot_img": (out_root / "boot.img", EXPECTED_BOOT_SHA256),
        "boot_img_lz4": (out_root / "odin4/boot.img.lz4", EXPECTED_BOOT_LZ4_SHA256),
        "o3_init": (out_root / "build/init", EXPECTED_INIT_SHA256),
        "o3_control": (out_root / "build/s22plus_o3_tty_control", EXPECTED_CONTROL_SHA256),
        "plan_tsv": (out_root / "build/plan/module-plan.tsv", EXPECTED_PLAN_TSV_SHA256),
        "plan_header": (out_root / "build/plan/module-plan.generated.h", EXPECTED_PLAN_HEADER_SHA256),
    }
    for label, (path, expected) in files.items():
        if not path.is_file() or sha256_file(path) != expected:
            raise SystemExit(f"O3 artifact mismatch {label}: {path}")
    if not (root / "workspace/public/src/native-init/s22plus_init_o3_minimal_acm.c").is_file():
        raise SystemExit("O3 public init source missing")
    return manifest


def status_reasons(values: dict[str, str]) -> list[str]:
    expected = {
        "marker": EXPECTED_MARKER,
        "version": "0.1",
        "phase": "control-ready",
        "result": "ready",
        "rc": "0",
        "plan_count": str(EXPECTED_PLAN_COUNT),
        "module_attempted": str(EXPECTED_PLAN_COUNT),
        "module_failed": "0",
        "proc_registration_rc": "0",
        "proc_eof": "1",
        "proc_found": str(EXPECTED_PLAN_COUNT),
        "gate_mask": "0xff",
        "gate_count": str(EXPECTED_GATE_COUNT),
        "configfs_rc": "0",
        "ssusb_mode_write_rc": "0",
        "ssusb_mode_readback_ok": "1",
        "udc_bind_rc": "0",
        "udc_readback_ok": "1",
        "ttyGS0_ready": "1",
        "gadget_function": "acm.usb0",
        "udc": "a600000.dwc3",
        "protocol_result": "pass",
        "protocol_handled": "128",
        "protocol_invalid": "0",
        "protocol_crc_errors": "0",
        "protocol_seq_errors": "0",
    }
    reasons = [f"{key}-mismatch:{values.get(key)!r}" for key, expected_value in expected.items() if values.get(key) != expected_value]
    loaded = values.get("module_loaded")
    existing = values.get("module_eexist")
    try:
        if int(loaded or "-1") + int(existing or "-1") != EXPECTED_PLAN_COUNT:
            reasons.append("module-loaded-plus-eexist-mismatch")
    except ValueError:
        reasons.append("module-loaded-or-eexist-not-integer")
    return reasons


def wait_for_o3_tty(requested: Path | None, timeout_sec: int) -> tuple[Path, dict[str, str]] | None:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            path, props = select_host_tty(requested)
        except (RuntimeError, OSError):
            time.sleep(0.25)
            continue
        if props.get("ID_SERIAL_SHORT") == EXPECTED_USB_SERIAL:
            return path, props
        time.sleep(0.25)
    return None


def query_o3_status(tty_path: Path, frame_timeout_sec: float) -> tuple[dict[str, str], str]:
    handle = HostTTY(tty_path)
    try:
        time.sleep(0.2)
        fd = handle.open(flush=True)
        write_all(fd, encode_frame(REQUEST, 128, b"O3 STATUS"), frame_timeout_sec)
        frame = read_frame(fd, frame_timeout_sec)
        _, seq, payload = decode_frame(frame, RESPONSE)
        if seq != 128:
            raise RuntimeError(f"O3 STATUS response sequence mismatch: {seq}")
        text = payload.decode("utf-8", errors="strict")
        return parse_key_values(text), text
    finally:
        handle.close()


def collect_retained(run_dir: Path, log_path: Path, serial: str) -> dict[str, Any]:
    marker_found = collect_android_pstore(
        run_dir,
        log_path,
        "postrollback_o3",
        serial,
        marker=EXPECTED_MARKER,
    )
    last_kmsg = run_dir / "android_pstore/postrollback_o3_last_kmsg.bin"
    return {
        "marker_found": marker_found,
        "last_kmsg_collected": last_kmsg.is_file(),
        "last_kmsg_bytes": last_kmsg.stat().st_size if last_kmsg.is_file() else 0,
    }


def stop_observers(observers: list[Any]) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    for observer in observers:
        state = observer.stop()
        states.append(vars(state))
    return states


def write_result(run_dir: Path, payload: dict[str, Any]) -> None:
    (run_dir / "result.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def validate_live_tokens(args: argparse.Namespace) -> None:
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")
    if args.rollback_ack != ROLLBACK_ACK_TOKEN:
        raise SystemExit(f"--live requires --rollback-ack {ROLLBACK_ACK_TOKEN}")


def perform_rollback(
    *,
    odin: Path,
    rollback_ap: Path,
    stock_ap: Path,
    device: str,
    run_dir: Path,
    log_path: Path,
    android_wait_sec: int,
    label: str,
) -> Any:
    return rollback_boot_only_from_download(
        odin=odin,
        rollback_ap=rollback_ap,
        stock_boot_fallback_ap=stock_ap,
        odin_device=device,
        run_dir=run_dir,
        log_path=log_path,
        rollback_target=ROLLBACK_MAGISK,
        android_wait_sec=android_wait_sec,
        label=label,
    )


def execute(args: argparse.Namespace) -> int:
    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_o3_minimal_acm_live_gate.txt"
    odin = resolve(root, args.odin)
    out_root = resolve(root, args.o3_root)
    candidate_ap = resolve(root, args.o3_ap)
    manifest_path = resolve(root, args.o3_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    append_log(log_path, f"target={EXPECTED_TARGET}")
    append_log(log_path, f"candidate_ap_sha256={EXPECTED_AP_SHA256}")
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")
    verify_artifacts(
        root=root,
        out_root=out_root,
        candidate_ap=candidate_ap,
        manifest_path=manifest_path,
        magisk_rollback_ap=magisk_rollback_ap,
        stock_rollback_ap=stock_rollback_ap,
        log_path=log_path,
    )

    if args.offline_check:
        print(json.dumps({"result": "offline-pass", "run_dir": str(run_dir)}, indent=2))
        return 0

    if args.rollback_from_download:
        if args.rollback_ack != ROLLBACK_ACK_TOKEN:
            raise SystemExit(f"--rollback-from-download requires --rollback-ack {ROLLBACK_ACK_TOKEN}")
        verify_agents_exception(root, log_path, allow_consumed=True)
        device = wait_for_odin(odin, log_path, "emergency-rollback-wait", args.odin_wait_sec)
        if device is None:
            raise SystemExit("no single Odin device available for O3 rollback")
        record_timeline_event(run_dir, "live_session_start")
        rollback = perform_rollback(
            odin=odin,
            rollback_ap=magisk_rollback_ap,
            stock_ap=stock_rollback_ap,
            device=device,
            run_dir=run_dir,
            log_path=log_path,
            android_wait_sec=args.android_wait_sec,
            label="emergency",
        )
        record_timeline_event(run_dir, "live_session_end")
        return int(rollback.rc)

    selected_serial = require_current_android(log_path, args.serial)
    verify_partition_hash(log_path, selected_serial, "boot", EXPECTED_BASE_BOOT_SHA256, "preflight")
    verify_android_stability(log_path, selected_serial, args.preflight_samples, args.sample_interval_sec)
    concurrent_odin = odin_devices(odin, log_path, "preflight")
    if concurrent_odin:
        raise SystemExit(f"refusing concurrent Android and Odin transports: {concurrent_odin}")
    host_snapshot(run_dir, log_path, "preflight", odin)
    if not args.live:
        print(f"dry-run pass: exact O3/rollback artifacts and Android baseline verified; run={run_dir}")
        return 0

    verify_agents_exception(root, log_path)
    validate_live_tokens(args)
    observers = start_observers(run_dir, selected_serial)
    proof_result = "candidate-not-started"
    proof_error: str | None = None
    roundtrip: dict[str, Any] | None = None
    status_values: dict[str, str] | None = None
    status_text: str | None = None
    tty_path: str | None = None
    rollback_result: Any = None
    retained: dict[str, Any] | None = None
    rc = 1
    candidate_flash_attempted = False
    record_timeline_event(run_dir, "live_session_start")
    try:
        transition = request_download_with_retry(selected_serial, log_path, odin)
        if not transition.get("success"):
            proof_result = "pre-candidate-download-failed"
            rc = 2
            return rc
        odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
        if odin_device is None:
            proof_result = "pre-candidate-odin-missing"
            rc = 2
            return rc

        record_timeline_event(run_dir, "candidate_flash_start")
        candidate_flash_attempted = True
        flash_rc = flash_ap(odin, candidate_ap, odin_device, log_path, "o3_candidate")
        record_timeline_event(run_dir, "candidate_flash_done")
        if flash_rc != 0:
            proof_result = "candidate-flash-failed"
            proof_error = f"candidate Odin flash rc={flash_rc}"
        elif not wait_for_odin_absent(odin, log_path, "candidate-disconnect", args.odin_disconnect_sec):
            proof_result = "candidate-never-left-download"
            proof_error = "original Odin endpoint remained present"
        else:
            try:
                tty_match = wait_for_o3_tty(args.host_tty, args.candidate_tty_wait_sec)
                if tty_match is None:
                    raise RuntimeError("O3 ACM tty with exact serial did not appear")
                selected_tty, tty_props = tty_match
                tty_path = str(selected_tty)
                append_log(log_path, f"o3_tty={selected_tty} props={json.dumps(tty_props, sort_keys=True)}")
                record_timeline_event(run_dir, "candidate_boot_ready")
                roundtrip_events: list[dict[str, str]] = []
                roundtrip = run_roundtrips(
                    selected_tty,
                    count=128,
                    payload_size=256,
                    reopen_at=64,
                    frame_timeout=args.frame_timeout_sec,
                    events=roundtrip_events,
                )
                if not (
                    roundtrip.get("completed") == 128
                    and roundtrip.get("sequence_continuity") is True
                    and roundtrip.get("payload_equality") is True
                    and roundtrip.get("host_reopen_completed") is True
                ):
                    raise RuntimeError(f"O3 roundtrip contract failed: {roundtrip}")
                status_values, status_text = query_o3_status(selected_tty, args.frame_timeout_sec)
                append_log(log_path, "o3_status_begin")
                append_log(log_path, status_text)
                append_log(log_path, "o3_status_end")
                reasons = status_reasons(status_values)
                if reasons:
                    raise RuntimeError(f"O3 STATUS contract failed: {reasons}")
                proof_result = "pass"
            except Exception as exc:
                proof_result = "candidate-proof-failed"
                proof_error = str(exc)
                append_log(log_path, f"candidate_proof_error={proof_error}")

        rollback_device = wait_for_odin(odin, log_path, "rollback-immediate-probe", 3)
        if rollback_device is None:
            print(
                "O3 candidate observation is complete. Enter Download mode manually now for the "
                f"mandatory boot-only rollback; waiting {args.manual_download_wait_sec}s.",
                flush=True,
            )
            rollback_device = wait_for_odin(
                odin,
                log_path,
                "manual-rollback-wait",
                args.manual_download_wait_sec,
            )
        if rollback_device is None:
            rc = 4
            proof_error = (proof_error + "; " if proof_error else "") + "manual Download rollback endpoint missing"
            return rc

        rollback_result = perform_rollback(
            odin=odin,
            rollback_ap=magisk_rollback_ap,
            stock_ap=stock_rollback_ap,
            device=rollback_device,
            run_dir=run_dir,
            log_path=log_path,
            android_wait_sec=args.android_wait_sec,
            label="o3",
        )
        if rollback_result.rc != 0 or rollback_result.android_serial is None:
            rc = int(rollback_result.rc or 5)
            return rc
        verify_partition_hash(
            log_path,
            rollback_result.android_serial,
            "boot",
            EXPECTED_BASE_BOOT_SHA256,
            "postrollback",
        )
        verify_android_stability(
            log_path,
            rollback_result.android_serial,
            args.postrollback_samples,
            args.sample_interval_sec,
        )
        retained = collect_retained(run_dir, log_path, rollback_result.android_serial)
        rc = 0 if proof_result == "pass" else 9
        return rc
    finally:
        observer_states = stop_observers(observers)
        record_timeline_event(run_dir, "live_session_end")
        timeline_path = run_dir / "timeline.json"
        timeline_events = []
        if timeline_path.is_file():
            timeline_events = json.loads(timeline_path.read_text(encoding="utf-8")).get("events", [])
        event_names = [event.get("name") for event in timeline_events]
        payload = {
            "schema": EXPECTED_SCHEMA,
            "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "target": EXPECTED_TARGET,
            "result": proof_result,
            "rc": rc,
            "error": proof_error,
            "candidate_flash_attempted": candidate_flash_attempted,
            "candidate_ap_sha256": EXPECTED_AP_SHA256,
            "candidate_boot_sha256": EXPECTED_BOOT_SHA256,
            "base_boot_sha256": EXPECTED_BASE_BOOT_SHA256,
            "tty_path": tty_path,
            "roundtrip": roundtrip,
            "status": status_values,
            "status_text": status_text,
            "rollback": None
            if rollback_result is None
            else {
                "rc": rollback_result.rc,
                "target": rollback_result.rollback_target,
                "android_restored": rollback_result.android_serial is not None,
            },
            "retained": retained,
            "timeline_required_phases": REQUIRED_TIMELINE_PHASES,
            "timeline_present_phases": event_names,
            "timeline_complete": all(name in event_names for name in REQUIRED_TIMELINE_PHASES),
            "observers": observer_states,
        }
        write_result(run_dir, payload)
        append_log(log_path, f"o3_result={json.dumps(payload, sort_keys=True)}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--o3-root", type=Path, default=DEFAULT_O3_ROOT)
    parser.add_argument("--o3-ap", type=Path, default=DEFAULT_O3_AP)
    parser.add_argument("--o3-manifest", type=Path, default=DEFAULT_O3_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial")
    parser.add_argument("--host-tty", type=Path)
    parser.add_argument("--offline-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--ack")
    parser.add_argument("--rollback-ack")
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--odin-disconnect-sec", type=int, default=30)
    parser.add_argument("--candidate-tty-wait-sec", type=int, default=120)
    parser.add_argument("--manual-download-wait-sec", type=int, default=600)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    parser.add_argument("--frame-timeout-sec", type=float, default=3.0)
    parser.add_argument("--preflight-samples", type=int, default=4)
    parser.add_argument("--postrollback-samples", type=int, default=4)
    parser.add_argument("--sample-interval-sec", type=float, default=3.0)
    args = parser.parse_args(argv)
    modes = sum(1 for value in (args.offline_check, args.live, args.rollback_from_download) if value)
    if modes > 1:
        raise SystemExit("--offline-check, --live, and --rollback-from-download are mutually exclusive")
    if args.manual_download_wait_sec < 60:
        raise SystemExit("--manual-download-wait-sec must be at least 60")
    return execute(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
