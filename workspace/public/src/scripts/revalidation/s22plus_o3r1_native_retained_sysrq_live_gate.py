#!/usr/bin/env python3
"""Guarded S22+ O3R1 direct-PID1 retained SysRq live gate."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import s22plus_o3_minimal_acm_live_gate as base
from s22plus_m34_s10c0_direct_finit_loader_audit_live_gate import wait_for_odin_absent
from s22plus_o11_stock_first_stage_control_live_gate import request_download_with_retry
from s22plus_o0_stock_usb_control import start_observers
from s22plus_sec_debug_mid_sysrq_gate import (
    DEBUG_LEVEL_CONFIRM_TOKEN,
    assert_sec_debug_mid_state,
    collect_sec_debug_state,
)


LIVE_ACK_TOKEN = "S22PLUS-O3R1-NATIVE-RETAINED-SYSRQ-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-O3R1-NATIVE-RETAINED-SYSRQ-ROLLBACK-FROM-DOWNLOAD"
ACTIVE_EXCEPTION_HEADING = (
    "**Narrow operator-authorized exception (2026-07-10, S22+ O3R1 native "
    "retained-SysRq boot-only live gate):**"
)

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_SCHEMA = "s22plus_o3r1_native_retained_sysrq_live_v1"
EXPECTED_BUILD_SCHEMA = "s22plus_o3r1_native_retained_sysrq_build_v1"
EXPECTED_MEMBER = "boot.img.lz4"
EXPECTED_MARKER = "S22_NATIVE_INIT_O3R1_RETAINED_SYSRQ"
EXPECTED_BASE_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_SOURCE_SHA256 = "a51fd1d87732bbcc3fa4b6ea2c9ede7ff78d423736ce3e168c059cef50626968"
EXPECTED_INIT_SHA256 = "44d70f3d7ee534b6701a5a912e07febdaf21b0b4d7fabf0368c4a6f942499fdc"
EXPECTED_RAMDISK_SHA256 = "bc40ff00d156ce27c0dba6453f426b42cda3438aadde26908cee0b78b2441d38"
EXPECTED_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_BOOT_SHA256 = "fc0dce090f454b621ed90e63dd11cfe29dad8de0fe04d3c1f138a004d9d2f6aa"
EXPECTED_BOOT_LZ4_SHA256 = "3af2ec28c2048aee8aac632c815581ded688dae256e3522eb002464514ae84a9"
EXPECTED_AP_TAR_SHA256 = "eb3819730944e68cab7355d72f2372c2dc47e88de6cb5670e94c43fe1593cbb8"
EXPECTED_AP_SHA256 = "2a92008b4632a8907fec96f0d8194a8461c16060cb1d919aeba7446020c4beda"

EXPECTED_MAGISK_AP_SHA256 = base.EXPECTED_MAGISK_AP_SHA256
EXPECTED_STOCK_BOOT_AP_SHA256 = base.EXPECTED_STOCK_BOOT_AP_SHA256
EXPECTED_STOCK_BOOT_RAW_SHA256 = base.EXPECTED_STOCK_BOOT_RAW_SHA256

DEFAULT_O3R1_ROOT = Path(
    "workspace/private/outputs/s22plus_native_init/o3r1_native_retained_sysrq_v0_1"
)
DEFAULT_O3R1_AP = DEFAULT_O3R1_ROOT / "odin4/AP.tar.md5"
DEFAULT_O3R1_MANIFEST = DEFAULT_O3R1_ROOT / "manifest.json"
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
        run_dir = base.resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    parent = base.resolve(root, base.DEFAULT_RUN_ROOT)
    candidate = parent / f"s22plus_o3r1_native_retained_sysrq_live_gate_{utc_stamp()}"
    for suffix in range(100):
        run_dir = candidate if suffix == 0 else Path(f"{candidate}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise SystemExit(f"could not allocate run directory under {parent}")


def active_exception_segment(text: str) -> str:
    start = text.find(ACTIVE_EXCEPTION_HEADING)
    if start < 0:
        return ""
    end = text.find("\n   **", start + len(ACTIVE_EXCEPTION_HEADING))
    return text[start:] if end < 0 else text[start:end]


def policy_markers() -> list[str]:
    return [
        "S22+ O3R1 native retained-SysRq boot-only",
        "workspace/public/src/scripts/revalidation/s22plus_o3r1_native_retained_sysrq_live_gate.py",
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        DEBUG_LEVEL_CONFIRM_TOKEN,
        EXPECTED_TARGET,
        EXPECTED_AP_SHA256,
        EXPECTED_BOOT_SHA256,
        EXPECTED_BOOT_LZ4_SHA256,
        EXPECTED_INIT_SHA256,
        EXPECTED_SOURCE_SHA256,
        EXPECTED_MARKER,
        EXPECTED_BASE_BOOT_SHA256,
        EXPECTED_MAGISK_AP_SHA256,
        EXPECTED_STOCK_BOOT_AP_SHA256,
        EXPECTED_STOCK_BOOT_RAW_SHA256,
        "debug_level=MID",
        "sec_debug enable=1",
        "/proc/sysrq-trigger",
        "/proc/last_kmsg",
        "intentional kernel crash",
        "global PID1 exit_group panic fallback",
        "mandatory boot-only rollback",
        "manual Download-mode entry",
        "no non-boot partition write",
    ]


def verify_agents_exception(root: Path, log_path: Path, *, allow_consumed: bool = False) -> None:
    segment = active_exception_segment((root / "AGENTS.md").read_text(encoding="utf-8"))
    normalized = " ".join(segment.split())
    missing = [marker for marker in policy_markers() if marker not in normalized]
    consumed = "Consumed exception" in segment or "Consumed/retired" in segment
    base.append_log(log_path, f"o3r1_agents_exception_present={int(bool(segment))}")
    base.append_log(log_path, f"o3r1_agents_exception_consumed={int(consumed)}")
    base.append_log(log_path, f"o3r1_agents_exception_missing={missing}")
    if not segment or (consumed and not allow_consumed):
        raise SystemExit("active O3R1 AGENTS.md exception is absent or consumed")
    if missing:
        raise SystemExit(f"O3R1 AGENTS.md exception missing markers: {missing}")


def verify_manifest(path: Path, log_path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"O3R1 manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes = data.get("hashes") or {}
    safety = data.get("safety") or {}
    ramdisk = data.get("ramdisk") or {}
    init = data.get("init") or {}
    expected_hashes = {
        "source": EXPECTED_SOURCE_SHA256,
        "base_boot": EXPECTED_BASE_BOOT_SHA256,
        "nochange_repack_boot": EXPECTED_BASE_BOOT_SHA256,
        "init": EXPECTED_INIT_SHA256,
        "ramdisk_after": EXPECTED_RAMDISK_SHA256,
        "kernel": EXPECTED_KERNEL_SHA256,
        "boot_img": EXPECTED_BOOT_SHA256,
        "boot_img_lz4": EXPECTED_BOOT_LZ4_SHA256,
        "ap_tar": EXPECTED_AP_TAR_SHA256,
        "ap_tar_md5": EXPECTED_AP_SHA256,
    }
    for key, expected in expected_hashes.items():
        if hashes.get(key) != expected:
            raise SystemExit(f"O3R1 manifest hash mismatch {key}: {hashes.get(key)!r}")
    required_safety = {
        "boot_only": True,
        "host_only_build": True,
        "live_flash_authorized": False,
        "requires_new_sha_pinned_agents_exception_before_flash": True,
        "kernel_changed": False,
        "runtime": "freestanding-raw-syscall",
        "intentional_kernel_crash": "sysrq-trigger-c",
        "failure_fallback": "global PID1 exit_group panic",
        "kernel_sysrq_sysctl_write": False,
        "procfs_mount": True,
        "procfs_write_allowlist": ["/proc/sysrq-trigger=c"],
        "pmsg_write": False,
        "sysfs_write": False,
        "configfs_write": False,
        "module_insertion": False,
        "usb_setup": False,
        "persistent_partition_mount": False,
        "block_device_write": False,
        "reboot_syscall": False,
        "no_android_or_magisk_handoff": True,
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"O3R1 manifest safety mismatch {key}: {safety.get(key)!r}")
    if data.get("schema") != EXPECTED_BUILD_SCHEMA or data.get("target") != EXPECTED_TARGET:
        raise SystemExit("O3R1 manifest schema/target mismatch")
    if data.get("tar_members") != [EXPECTED_MEMBER]:
        raise SystemExit("O3R1 manifest is not a single-member boot AP")
    if ramdisk.get("replaced_entry") != "init" or ramdisk.get("added_entries") != []:
        raise SystemExit("O3R1 manifest ramdisk delta mismatch")
    if init.get("undefined_symbols") != [] or init.get("no_interp") is not True:
        raise SystemExit("O3R1 init is not closed freestanding ELF")
    base.append_log(log_path, f"o3r1_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
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
    base.verify_ap(candidate_ap, EXPECTED_AP_SHA256, "o3r1_candidate", log_path)
    manifest = verify_manifest(manifest_path, log_path)
    base.verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    base.verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)
    files = {
        "boot_img": (out_root / "boot.img", EXPECTED_BOOT_SHA256),
        "boot_img_lz4": (out_root / "odin4/boot.img.lz4", EXPECTED_BOOT_LZ4_SHA256),
        "ap_tar": (out_root / "odin4/AP.tar", EXPECTED_AP_TAR_SHA256),
        "init": (out_root / "build/init", EXPECTED_INIT_SHA256),
        "source": (
            root / "workspace/public/src/native-init/s22plus_init_o3r1_native_retained_sysrq.c",
            EXPECTED_SOURCE_SHA256,
        ),
    }
    for label, (artifact, expected) in files.items():
        if not artifact.is_file() or base.sha256_file(artifact) != expected:
            raise SystemExit(f"O3R1 artifact mismatch {label}: {artifact}")
    return manifest


def classify_retained(payloads: dict[str, bytes]) -> dict[str, Any]:
    decoded = {
        name: payload.decode("utf-8", errors="replace")
        for name, payload in payloads.items()
    }
    combined = "\n".join(decoded.values())
    lower = combined.lower()
    marker_pattern = re.compile(
        rf"{re.escape(EXPECTED_MARKER)}[^\r\n]*phase=([^\s]+)\s+rc=(-?[0-9]+)\s+action=([^\s]+)"
    )
    records = [
        {"phase": match.group(1), "rc": int(match.group(2)), "action": match.group(3)}
        for match in marker_pattern.finditer(combined)
    ]
    marker_found = EXPECTED_MARKER in combined
    before_sysrq_found = any(record["phase"] == "before-sysrq-c" for record in records)
    sysrq_trigger_line = "sysrq: trigger a crash" in lower
    sysrq_panic_line = "kernel panic - not syncing: sysrq triggered crash" in lower
    init_death_panic = "attempted to kill init" in lower
    kernel_panic = "kernel panic" in lower

    if marker_found and before_sysrq_found and sysrq_trigger_line and sysrq_panic_line:
        verdict = "pass-marker-and-sysrq-panic"
        channel_proven = True
        exact_pass = True
    elif marker_found and init_death_panic:
        verdict = "marker-retained-sysrq-failed-init-death-panic"
        channel_proven = True
        exact_pass = False
    elif init_death_panic:
        verdict = "init-death-panic-without-marker"
        channel_proven = False
        exact_pass = False
    elif marker_found and kernel_panic:
        verdict = "marker-retained-unclassified-panic"
        channel_proven = True
        exact_pass = False
    elif marker_found:
        verdict = "marker-retained-without-classified-panic"
        channel_proven = True
        exact_pass = False
    elif kernel_panic:
        verdict = "panic-without-o3r1-marker"
        channel_proven = False
        exact_pass = False
    else:
        verdict = "no-retained-o3r1-proof"
        channel_proven = False
        exact_pass = False

    return {
        "verdict": verdict,
        "exact_pass": exact_pass,
        "channel_proven": channel_proven,
        "marker_found": marker_found,
        "before_sysrq_found": before_sysrq_found,
        "sysrq_trigger_line": sysrq_trigger_line,
        "sysrq_panic_line": sysrq_panic_line,
        "init_death_panic": init_death_panic,
        "kernel_panic": kernel_panic,
        "marker_records": records,
        "sources": {name: len(payload) for name, payload in payloads.items()},
    }


def collect_retained(run_dir: Path, log_path: Path, serial: str) -> dict[str, Any]:
    label = "postrollback_o3r1"
    base.collect_android_pstore(run_dir, log_path, label, serial, marker=EXPECTED_MARKER)
    retained_dir = run_dir / "android_pstore"
    payloads = {
        path.name: path.read_bytes()
        for path in sorted(retained_dir.glob(f"{label}_*.bin"))
        if path.is_file()
    }
    classification = classify_retained(payloads)
    (retained_dir / f"{label}_classification.json").write_text(
        json.dumps(classification, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    base.append_log(log_path, f"o3r1_retained={json.dumps(classification, sort_keys=True)}")
    return classification


def validate_live_tokens(args: argparse.Namespace) -> None:
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")
    if args.rollback_ack != ROLLBACK_ACK_TOKEN:
        raise SystemExit(f"--live requires --rollback-ack {ROLLBACK_ACK_TOKEN}")
    if args.confirm_debug_level_mid != DEBUG_LEVEL_CONFIRM_TOKEN:
        raise SystemExit(f"--live requires --confirm-debug-level-mid {DEBUG_LEVEL_CONFIRM_TOKEN}")


def write_result(run_dir: Path, payload: dict[str, Any]) -> None:
    (run_dir / "result.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def execute(args: argparse.Namespace) -> int:
    root = base.repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_o3r1_native_retained_sysrq_live_gate.txt"
    odin = base.resolve(root, args.odin)
    out_root = base.resolve(root, args.o3r1_root)
    candidate_ap = base.resolve(root, args.o3r1_ap)
    manifest_path = base.resolve(root, args.o3r1_manifest)
    magisk_rollback_ap = base.resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = base.resolve(root, args.stock_rollback_ap)
    base.append_log(log_path, f"target={EXPECTED_TARGET}")
    base.append_log(log_path, f"candidate_ap_sha256={EXPECTED_AP_SHA256}")
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
            raise SystemExit(
                f"--rollback-from-download requires --rollback-ack {ROLLBACK_ACK_TOKEN}"
            )
        verify_agents_exception(root, log_path, allow_consumed=True)
        device = base.wait_for_odin(odin, log_path, "o3r1-emergency-rollback-wait", args.odin_wait_sec)
        if device is None:
            raise SystemExit("no single Odin device available for O3R1 rollback")
        base.record_timeline_event(run_dir, "live_session_start")
        rollback = base.perform_rollback(
            odin=odin,
            rollback_ap=magisk_rollback_ap,
            stock_ap=stock_rollback_ap,
            device=device,
            run_dir=run_dir,
            log_path=log_path,
            android_wait_sec=args.android_wait_sec,
            label="o3r1_emergency",
        )
        retained = None
        if rollback.rc == 0 and rollback.android_serial:
            base.verify_partition_hash(
                log_path,
                rollback.android_serial,
                "boot",
                EXPECTED_BASE_BOOT_SHA256,
                "o3r1_emergency_postrollback",
            )
            retained = collect_retained(run_dir, log_path, rollback.android_serial)
        base.record_timeline_event(run_dir, "live_session_end")
        write_result(
            run_dir,
            {
                "schema": EXPECTED_SCHEMA,
                "mode": "emergency-rollback",
                "rc": rollback.rc,
                "retained": retained,
            },
        )
        return int(rollback.rc)

    selected_serial = base.require_current_android(log_path, args.serial)
    base.verify_partition_hash(log_path, selected_serial, "boot", EXPECTED_BASE_BOOT_SHA256, "preflight")
    base.verify_android_stability(
        log_path, selected_serial, args.preflight_samples, args.sample_interval_sec
    )
    sec_debug_state = collect_sec_debug_state(run_dir, log_path, selected_serial, "pre_o3r1")
    assert_sec_debug_mid_state(sec_debug_state, "pre_o3r1")
    concurrent_odin = base.odin_devices(odin, log_path, "preflight")
    if concurrent_odin:
        raise SystemExit(f"refusing concurrent Android and Odin transports: {concurrent_odin}")
    base.host_snapshot(run_dir, log_path, "preflight", odin)
    if not args.live:
        print(
            "dry-run pass: exact O3R1/rollback artifacts, Android baseline, "
            f"and sec_debug MID verified; run={run_dir}"
        )
        return 0

    verify_agents_exception(root, log_path)
    validate_live_tokens(args)
    observers = start_observers(run_dir, selected_serial)
    result = "candidate-not-started"
    error: str | None = None
    rc = 1
    candidate_flash_attempted = False
    candidate_left_odin = False
    rollback_result: Any = None
    retained: dict[str, Any] | None = None
    rollback_entry = "none"
    base.record_timeline_event(run_dir, "live_session_start")
    try:
        transition = request_download_with_retry(selected_serial, log_path, odin)
        if not transition.get("success"):
            result = "pre-candidate-download-failed"
            rc = 2
            return rc
        odin_device = base.wait_for_odin(odin, log_path, "o3r1-candidate-wait", args.odin_wait_sec)
        if odin_device is None:
            result = "pre-candidate-odin-missing"
            rc = 2
            return rc

        base.record_timeline_event(run_dir, "candidate_flash_start")
        candidate_flash_attempted = True
        flash_rc = base.flash_ap(odin, candidate_ap, odin_device, log_path, "o3r1_candidate")
        base.record_timeline_event(run_dir, "candidate_flash_done")
        if flash_rc != 0:
            result = "candidate-flash-failed"
            error = f"candidate Odin flash rc={flash_rc}"
        else:
            candidate_left_odin = wait_for_odin_absent(
                odin, log_path, "o3r1-candidate-disconnect", args.odin_disconnect_sec
            )
            if not candidate_left_odin:
                result = "candidate-never-left-download"
                error = "original Odin endpoint remained present"
            else:
                # This canonical event records the kernel boot-attempt boundary only;
                # retained evidence, not this event, decides whether PID1 executed.
                base.record_timeline_event(run_dir, "candidate_boot_ready")
                base.append_log(
                    log_path,
                    "candidate_boot_ready_semantics=original-odin-disconnected-not-pid1-proof",
                )
                result = "candidate-panic-observation-pending"

        rollback_device = base.wait_for_odin(
            odin,
            log_path,
            "o3r1-automatic-download-wait",
            args.automatic_download_wait_sec,
        )
        if rollback_device is not None:
            rollback_entry = "automatic-host-observed"
        else:
            print(
                "O3R1 panic observation window ended. Enter Download mode manually now for "
                f"the mandatory boot-only rollback; waiting {args.manual_download_wait_sec}s.",
                flush=True,
            )
            rollback_device = base.wait_for_odin(
                odin,
                log_path,
                "o3r1-manual-rollback-wait",
                args.manual_download_wait_sec,
            )
            if rollback_device is not None:
                rollback_entry = "attended-manual"
        if rollback_device is None:
            error = (error + "; " if error else "") + "mandatory rollback endpoint missing"
            rc = 4
            return rc

        rollback_result = base.perform_rollback(
            odin=odin,
            rollback_ap=magisk_rollback_ap,
            stock_ap=stock_rollback_ap,
            device=rollback_device,
            run_dir=run_dir,
            log_path=log_path,
            android_wait_sec=args.android_wait_sec,
            label="o3r1",
        )
        if rollback_result.rc != 0 or rollback_result.android_serial is None:
            rc = int(rollback_result.rc or 5)
            result = "rollback-failed"
            return rc
        base.verify_partition_hash(
            log_path,
            rollback_result.android_serial,
            "boot",
            EXPECTED_BASE_BOOT_SHA256,
            "postrollback",
        )
        base.verify_android_stability(
            log_path,
            rollback_result.android_serial,
            args.postrollback_samples,
            args.sample_interval_sec,
        )
        post_state = collect_sec_debug_state(
            run_dir, log_path, rollback_result.android_serial, "post_o3r1_rollback"
        )
        assert_sec_debug_mid_state(post_state, "post_o3r1_rollback")
        retained = collect_retained(run_dir, log_path, rollback_result.android_serial)
        result = retained["verdict"]
        rc = 0 if retained["exact_pass"] else 9
        return rc
    finally:
        observer_states = base.stop_observers(observers)
        base.record_timeline_event(run_dir, "live_session_end")
        timeline_path = run_dir / "timeline.json"
        timeline_events = []
        if timeline_path.is_file():
            timeline_events = json.loads(timeline_path.read_text(encoding="utf-8")).get("events", [])
        event_names = [event.get("name") for event in timeline_events]
        payload = {
            "schema": EXPECTED_SCHEMA,
            "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "target": EXPECTED_TARGET,
            "result": result,
            "rc": rc,
            "error": error,
            "candidate_flash_attempted": candidate_flash_attempted,
            "candidate_left_odin": candidate_left_odin,
            "candidate_ap_sha256": EXPECTED_AP_SHA256,
            "candidate_boot_sha256": EXPECTED_BOOT_SHA256,
            "base_boot_sha256": EXPECTED_BASE_BOOT_SHA256,
            "rollback_entry": rollback_entry,
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
        base.append_log(log_path, f"o3r1_result={json.dumps(payload, sort_keys=True)}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--o3r1-root", type=Path, default=DEFAULT_O3R1_ROOT)
    parser.add_argument("--o3r1-ap", type=Path, default=DEFAULT_O3R1_AP)
    parser.add_argument("--o3r1-manifest", type=Path, default=DEFAULT_O3R1_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=base.DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=base.DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=base.DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial")
    parser.add_argument("--offline-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--ack")
    parser.add_argument("--rollback-ack")
    parser.add_argument("--confirm-debug-level-mid")
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--odin-disconnect-sec", type=int, default=30)
    parser.add_argument("--automatic-download-wait-sec", type=int, default=45)
    parser.add_argument("--manual-download-wait-sec", type=int, default=600)
    parser.add_argument("--android-wait-sec", type=int, default=300)
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
