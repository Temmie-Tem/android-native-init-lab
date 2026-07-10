#!/usr/bin/env python3
"""Guarded live gate for the V3429 direct-PID1 phase observer.

The candidate is boot-only and has no transport or transition path. The host
flashes it once, observes departure from the original Odin endpoint, waits a
bounded quiet dwell, requires attended manual RDX/Download entry, restores the
pinned Magisk boot image, and classifies the first rollback boot's retained
ring with the V3426/V3427 contract.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import s22plus_twrp_magisk_restore_window as stock_evidence
import s22plus_v3426_phase_observer_design as observer
import s22plus_v3427_transition_selection as transition
import s22plus_v3428_stock_transition_positive_control as control
from build_s22plus_direct_p3_boot import tar_members


SCHEMA = "s22plus_v3430_phase_observer_live_gate_v1"
TARGET = observer.TARGET
LIVE_ACK_TOKEN = "S22PLUS-V3430-V3429-PHASE-OBSERVER-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-V3430-V3429-ROLLBACK-FROM-DOWNLOAD"
ACTIVE_EXCEPTION_HEADING = (
    "**Narrow operator-authorized exception (2026-07-10, S22+ V3430 V3429 "
    "direct-PID1 phase-observer live gate):**"
)
SCRIPT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3430_phase_observer_live_gate.py"
)
RUN_ROOT = Path("workspace/private/runs")

CANDIDATE_DIR = Path(
    "workspace/private/outputs/s22plus_native_init/v3429_phase_observer_v0_1"
)
CANDIDATE_MANIFEST = CANDIDATE_DIR / "manifest.json"
CANDIDATE_EXPECTED_MARKERS = CANDIDATE_DIR / "expected_markers.json"
CANDIDATE_AP = CANDIDATE_DIR / "odin4/AP.tar.md5"
CANDIDATE_BOOT = CANDIDATE_DIR / "boot.img"
CANDIDATE_LZ4 = CANDIDATE_DIR / "odin4/boot.img.lz4"

EXPECTED_RUN_ID = "f1613e72912b63f030c25a6bd7fd072e"
EXPECTED_MANIFEST_SHA256 = (
    "3961f828b0427c70ec09bce3ffc168cfdb02132f5e5363a2767eb287d89270a1"
)
EXPECTED_MARKERS_SHA256 = (
    "b05615527be5e78b4c095153b7b104522436b91d3197c127f278867baf5acd54"
)
EXPECTED_CANDIDATE_AP_SHA256 = (
    "d6b2a430b2f5d21a7bdefe5b7db050c9e627d30ef5ecdee77ee44bd764579b4f"
)
EXPECTED_CANDIDATE_BOOT_SHA256 = (
    "93eef3b07bfbeb2154ecc9bfddfdeed682d83d950ca5e6032b7cfd75e4c9a428"
)
EXPECTED_CANDIDATE_LZ4_SHA256 = (
    "3eccf17ce7b22cb8c6f29ce31e24e33513d46d878ab0076528a91df4f4b957d8"
)
EXPECTED_INIT_SHA256 = (
    "4e58721e21efa42e7d4529d9aa3a0c60d0724b56cf8fc171fc85e82c4d3a17ea"
)
EXPECTED_SOURCE_SHA256 = (
    "311a44deecbd0d0148c7624929f173c44500cf714c4f2a8dd8b5e6acd856db59"
)

MIN_QUIET_DWELL_SEC = 60
MAX_MANUAL_WAIT_SEC = 120
MAX_TRANSITION_SEC = 180
ODIN_WAIT_SEC = 90
POST_FLASH_DISCONNECT_WAIT_SEC = 45
POST_ROLLBACK_WAIT_SEC = 240


class LiveGateError(RuntimeError):
    pass


@dataclass(frozen=True)
class FilePin:
    path: Path
    device: int
    inode: int
    size: int
    mtime_ns: int


def allocate_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = requested if requested.is_absolute() else root / requested
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    base = root / RUN_ROOT / f"s22plus_v3430_phase_observer_{control.utc_stamp()}"
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
            return run_dir
        except FileExistsError:
            continue
    raise LiveGateError(f"could not allocate V3430 run directory under {base.parent}")


def file_pin(path: Path) -> FilePin:
    stat = path.stat()
    return FilePin(path, stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def require_unchanged(pin: FilePin) -> None:
    current = file_pin(pin.path)
    if current != pin:
        raise LiveGateError(f"pinned file changed after verification: {pin.path}")


def helper_sha256(root: Path) -> str:
    return observer.sha256_file(root / SCRIPT_RELATIVE)


def active_exception_segment(text: str) -> str:
    start = text.find(ACTIVE_EXCEPTION_HEADING)
    if start < 0:
        return ""
    end = text.find("\n   **", start + len(ACTIVE_EXCEPTION_HEADING))
    return text[start:] if end < 0 else text[start:end]


def policy_markers(root: Path) -> list[str]:
    return [
        "S22+ V3430 V3429 direct-PID1 phase-observer live gate",
        str(SCRIPT_RELATIVE),
        helper_sha256(root),
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        TARGET,
        EXPECTED_RUN_ID,
        EXPECTED_MANIFEST_SHA256,
        EXPECTED_MARKERS_SHA256,
        EXPECTED_CANDIDATE_AP_SHA256,
        EXPECTED_CANDIDATE_BOOT_SHA256,
        observer.CONTRACT_SHA256,
        transition.TRANSITION_SHA256,
        transition.MAGISK_ROLLBACK_AP_SHA256,
        transition.STOCK_ROLLBACK_AP_SHA256,
        "manual RDX/Download",
        "first-rollback /proc/last_kmsg double-read",
        "boot partition only",
        "no non-boot partition write",
    ]


def validate_exception_segment(
    segment: str,
    required_markers: list[str],
    *,
    allow_consumed: bool,
) -> None:
    normalized = " ".join(segment.split())
    missing = [marker for marker in required_markers if marker not in normalized]
    consumed = "Consumed exception" in segment or "Consumed/retired" in segment
    if not segment:
        raise LiveGateError("active V3430 exception is absent")
    if consumed and not allow_consumed:
        raise LiveGateError("V3430 exception is already consumed")
    if missing:
        raise LiveGateError(f"V3430 exception missing markers: {missing}")


def verify_agents_exception(root: Path, *, allow_consumed: bool = False) -> None:
    segment = active_exception_segment((root / "AGENTS.md").read_text(encoding="utf-8"))
    validate_exception_segment(
        segment,
        policy_markers(root),
        allow_consumed=allow_consumed,
    )


def sha256_matches(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise LiveGateError(f"{label} missing: {path}")
    actual = observer.sha256_file(path)
    if actual != expected:
        raise LiveGateError(f"{label} SHA256 mismatch: {actual}")


def load_candidate(root: Path) -> tuple[observer.MarkerExpectation, dict[str, Any]]:
    manifest_path = root / CANDIDATE_MANIFEST
    markers_path = root / CANDIDATE_EXPECTED_MARKERS
    ap_path = root / CANDIDATE_AP
    boot_path = root / CANDIDATE_BOOT
    lz4_path = root / CANDIDATE_LZ4
    sha256_matches(manifest_path, EXPECTED_MANIFEST_SHA256, "candidate manifest")
    sha256_matches(markers_path, EXPECTED_MARKERS_SHA256, "expected markers")
    sha256_matches(ap_path, EXPECTED_CANDIDATE_AP_SHA256, "candidate AP")
    sha256_matches(boot_path, EXPECTED_CANDIDATE_BOOT_SHA256, "candidate boot")
    sha256_matches(lz4_path, EXPECTED_CANDIDATE_LZ4_SHA256, "candidate boot LZ4")
    if tar_members(ap_path) != ["boot.img.lz4"]:
        raise LiveGateError("candidate AP must contain exactly boot.img.lz4")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    markers = json.loads(markers_path.read_text(encoding="utf-8"))
    expected_manifest = {
        "schema": "s22plus_v3429_phase_observer_build_v1",
        "target": TARGET,
        "run_id": EXPECTED_RUN_ID,
    }
    for key, value in expected_manifest.items():
        if manifest.get(key) != value:
            raise LiveGateError(f"candidate manifest {key} mismatch")
    required_hashes = {
        "source": EXPECTED_SOURCE_SHA256,
        "init": EXPECTED_INIT_SHA256,
        "boot_img": EXPECTED_CANDIDATE_BOOT_SHA256,
        "boot_img_lz4": EXPECTED_CANDIDATE_LZ4_SHA256,
        "ap_tar_md5": EXPECTED_CANDIDATE_AP_SHA256,
        "base_boot": transition.MAGISK_ROLLBACK_BOOT_SHA256,
    }
    for key, value in required_hashes.items():
        if manifest.get("hashes", {}).get(key) != value:
            raise LiveGateError(f"candidate manifest hash {key} mismatch")
    if manifest.get("tar_members") != ["boot.img.lz4"]:
        raise LiveGateError("candidate manifest tar member mismatch")
    safety = manifest.get("safety", {})
    required_safety = {
        "host_only_build": True,
        "live_flash_authorized": False,
        "boot_only": True,
        "kernel_changed": False,
        "pid1_never_exits": True,
        "reboot_syscall": False,
        "block_device_write": False,
        "candidate_transition": False,
    }
    for key, value in required_safety.items():
        if safety.get(key) is not value:
            raise LiveGateError(f"candidate safety field {key} mismatch")
    marker_required = {
        "schema": "s22plus_v3429_expected_markers_v1",
        "target": TARGET,
        "run_id": EXPECTED_RUN_ID,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "observer_contract_sha256": observer.CONTRACT_SHA256,
        "transition_sha256": transition.TRANSITION_SHA256,
    }
    for key, value in marker_required.items():
        if markers.get(key) != value:
            raise LiveGateError(f"expected marker {key} mismatch")
    expectation = observer.make_expectation(
        markers["run_id"],
        markers["precheck_context_sha256"],
        markers["final_context_sha256"],
        module_sha256=markers["module_sha256"],
        contract_sha256=markers["observer_contract_sha256"],
    )
    precheck = observer.encode_marker(expectation, observer.PHASE_PRECHECK).decode("ascii")
    final = observer.encode_marker(expectation, observer.PHASE_FINAL).decode("ascii")
    if precheck != markers.get("precheck_frame") or final != markers.get("final_frame"):
        raise LiveGateError("expected marker frame does not round-trip")
    return expectation, markers


def verify_rollback_inputs(root: Path) -> dict[str, FilePin]:
    primary = root / transition.MAGISK_ROLLBACK_AP
    fallback = root / transition.STOCK_ROLLBACK_AP
    sha256_matches(primary, transition.MAGISK_ROLLBACK_AP_SHA256, "Magisk rollback AP")
    sha256_matches(fallback, transition.STOCK_ROLLBACK_AP_SHA256, "stock fallback AP")
    if tar_members(primary) != ["boot.img.lz4"]:
        raise LiveGateError("Magisk rollback AP member mismatch")
    if tar_members(fallback) != ["boot.img.lz4"]:
        raise LiveGateError("stock fallback AP member mismatch")
    return {"primary": file_pin(primary), "fallback": file_pin(fallback)}


def verify_full_stock_evidence(root: Path, log_path: Path) -> None:
    try:
        stock_evidence.verify_full_firmware_evidence(
            root / stock_evidence.DEFAULT_FULL_FW,
            root / stock_evidence.DEFAULT_FULL_FW_DIR,
            log_path,
        )
    except SystemExit as exc:
        raise LiveGateError(str(exc)) from exc


def verify_host_inputs(
    root: Path,
    log_path: Path,
    *,
    include_full_stock: bool,
) -> tuple[observer.MarkerExpectation, dict[str, Any], dict[str, FilePin]]:
    expectation, markers = load_candidate(root)
    try:
        selection = transition.build_selection(root)
    except Exception as exc:
        raise LiveGateError(f"transition input verification failed: {exc}") from exc
    if selection["transition_sha256"] != transition.TRANSITION_SHA256:
        raise LiveGateError("transition contract mismatch")
    rollback_pins = verify_rollback_inputs(root)
    if include_full_stock:
        verify_full_stock_evidence(root, log_path)
    pins = {
        "candidate": file_pin(root / CANDIDATE_AP),
        **rollback_pins,
    }
    return expectation, markers, pins


def wait_for_odin_absent(log_path: Path, label: str, wait_sec: int) -> bool:
    deadline = time.monotonic() + wait_sec
    while True:
        devices = control.odin_devices(transition.ODIN4, log_path, label)
        if not devices:
            control.append_log(log_path, f"{label}_odin_absent=1")
            return True
        if len(devices) > 1:
            raise LiveGateError(f"ambiguous Odin devices: {devices}")
        if time.monotonic() >= deadline:
            control.append_log(log_path, f"{label}_odin_absent=0")
            return False
        time.sleep(1.0)


def reboot_android_to_download(serial: str, log_path: Path) -> None:
    result = control.run(["adb", "-s", serial, "reboot", "download"], timeout=20.0)
    control.append_log(log_path, f"adb_reboot_download_rc={result.returncode}")
    control.append_log(log_path, result.stdout + result.stderr)
    if result.returncode != 0:
        raise LiveGateError("adb reboot download failed")


def rollback_and_collect(
    root: Path,
    run_dir: Path,
    log_path: Path,
    events: list[dict[str, str]],
    expectation: observer.MarkerExpectation,
    rollback_pins: dict[str, FilePin],
    odin_device: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    verify_agents_exception(root, allow_consumed=True)
    require_unchanged(rollback_pins["primary"])
    require_unchanged(rollback_pins["fallback"])
    timeline_path = run_dir / "timeline.json"
    control.record_timeline_event(timeline_path, events, "rollback_flash_start")
    rc = control.flash_ap(
        transition.ODIN4,
        rollback_pins["primary"].path,
        odin_device,
        log_path,
        "v3430_magisk_boot_rollback",
    )
    control.record_timeline_event(timeline_path, events, "rollback_flash_done")
    result["primary_rollback_rc"] = rc
    if rc != 0:
        fallback_device = control.wait_for_odin(
            transition.ODIN4, log_path, "v3430-stock-fallback", 20
        )
        if fallback_device is not None:
            result["stock_fallback_rc"] = control.flash_ap(
                transition.ODIN4,
                rollback_pins["fallback"].path,
                fallback_device,
                log_path,
                "v3430_stock_boot_fallback",
            )
        result["verdict"] = "RECOVERY_ONLY_NO_PROOF_STOP"
        return result
    first_boot = control.wait_for_first_boot_ready(POST_ROLLBACK_WAIT_SEC)
    if first_boot is None:
        result["verdict"] = "UNAVAILABLE_STOP_FIRST_ROOT_TIMEOUT"
        return result
    serial, health = first_boot
    result["postrollback_health"] = health
    if not health["pass"]:
        result["verdict"] = "UNAVAILABLE_STOP_POSTROLLBACK_HEALTH"
        return result
    control.record_timeline_event(timeline_path, events, "rollback_boot_ready")
    capture = control.collect_first_boot(serial, run_dir, expectation)
    result["first_boot_capture"] = capture
    result["verdict"] = capture["classification"]["verdict"]
    return result


def live_run(
    root: Path,
    run_dir: Path,
    ack: str,
    manual_wait_sec: int,
) -> dict[str, Any]:
    if ack != LIVE_ACK_TOKEN:
        raise LiveGateError("live acknowledgement token mismatch")
    verify_agents_exception(root)
    log_path = run_dir / "live.log"
    expectation, markers, pins = verify_host_inputs(
        root, log_path, include_full_stock=True
    )
    control.write_json_fsync(run_dir / "expected_markers.json", markers)
    events: list[dict[str, str]] = []
    timeline_path = run_dir / "timeline.json"
    control.record_timeline_event(timeline_path, events, "live_session_start")
    serial, preflight = control.connected_preflight(root, run_dir, expectation)
    observers = control.start_observers(run_dir, serial)
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "target": TARGET,
        "run_id": expectation.run_id,
        "preflight": preflight,
        "candidate_flash": True,
        "candidate_ap_sha256": EXPECTED_CANDIDATE_AP_SHA256,
        "candidate_boot_sha256": EXPECTED_CANDIDATE_BOOT_SHA256,
        "timeline_semantics": {
            "candidate_boot_ready": (
                "original Odin endpoint departed; observation window started; "
                "not direct PID1 execution proof"
            )
        },
        "verdict": "INCOMPLETE",
    }
    try:
        reboot_android_to_download(serial, log_path)
        odin_device = control.wait_for_odin(
            transition.ODIN4, log_path, "v3430-candidate-wait", ODIN_WAIT_SEC
        )
        if odin_device is None:
            result["verdict"] = "UNAVAILABLE_STOP_NO_ODIN_BEFORE_CANDIDATE"
            return result
        verify_agents_exception(root)
        require_unchanged(pins["candidate"])
        control.record_timeline_event(timeline_path, events, "candidate_flash_start")
        candidate_rc = control.flash_ap(
            transition.ODIN4,
            pins["candidate"].path,
            odin_device,
            log_path,
            "v3430_v3429_candidate",
        )
        control.record_timeline_event(timeline_path, events, "candidate_flash_done")
        result["candidate_flash_rc"] = candidate_rc
        if candidate_rc != 0:
            rollback_device = control.wait_for_odin(
                transition.ODIN4, log_path, "v3430-candidate-failure-rollback", 15
            )
            if rollback_device is None:
                result["verdict"] = "RECOVERY_REQUIRED_NO_ODIN_AFTER_FLASH_FAILURE"
                return result
            return rollback_and_collect(
                root,
                run_dir,
                log_path,
                events,
                expectation,
                pins,
                rollback_device,
                result,
            )
        departed = wait_for_odin_absent(
            log_path,
            "v3430-post-candidate-disconnect",
            POST_FLASH_DISCONNECT_WAIT_SEC,
        )
        if not departed:
            result["verdict"] = "NO_PROOF_ORIGINAL_ODIN_NEVER_DEPARTED"
            rollback_device = control.wait_for_odin(
                transition.ODIN4, log_path, "v3430-still-odin-rollback", 5
            )
            if rollback_device is None:
                return result
            return rollback_and_collect(
                root,
                run_dir,
                log_path,
                events,
                expectation,
                pins,
                rollback_device,
                result,
            )
        control.record_timeline_event(timeline_path, events, "candidate_boot_ready")
        transition_started = time.monotonic()
        print(
            f"CANDIDATE_TRANSFER_DEPARTED quiet_dwell_sec={MIN_QUIET_DWELL_SEC}",
            flush=True,
        )
        time.sleep(MIN_QUIET_DWELL_SEC)
        print(
            "MANUAL_ACTION_REQUIRED enter Samsung RDX/Download mode now; helper is waiting",
            flush=True,
        )
        remaining = min(
            manual_wait_sec,
            max(0, int(transition_started + MAX_TRANSITION_SEC - time.monotonic())),
        )
        if remaining <= 0:
            result["verdict"] = "UNAVAILABLE_STOP_TRANSITION_DEADLINE"
            return result
        rollback_device = control.wait_for_odin(
            transition.ODIN4, log_path, "v3430-manual-download", remaining
        )
        if rollback_device is None:
            result["verdict"] = "UNAVAILABLE_STOP_MANUAL_DOWNLOAD_TIMEOUT"
            return result
        elapsed = time.monotonic() - transition_started
        result["manual_transition_elapsed_sec"] = elapsed
        if elapsed > MAX_TRANSITION_SEC:
            result["verdict"] = "UNAVAILABLE_STOP_TRANSITION_DEADLINE"
            return result
        return rollback_and_collect(
            root,
            run_dir,
            log_path,
            events,
            expectation,
            pins,
            rollback_device,
            result,
        )
    finally:
        result["observer_rcs"] = control.stop_observers(observers)
        if not any(event["name"] == "live_session_end" for event in events):
            control.record_timeline_event(timeline_path, events, "live_session_end")
        result["timeline_complete"] = control.timeline_complete(events)
        control.write_json_fsync(run_dir / "result.json", result)


def rollback_only(root: Path, run_dir: Path, ack: str) -> dict[str, Any]:
    if ack != ROLLBACK_ACK_TOKEN:
        raise LiveGateError("rollback acknowledgement token mismatch")
    verify_agents_exception(root, allow_consumed=True)
    log_path = run_dir / "rollback.log"
    expectation, markers, pins = verify_host_inputs(
        root, log_path, include_full_stock=False
    )
    control.write_json_fsync(run_dir / "expected_markers.json", markers)
    devices = control.odin_devices(transition.ODIN4, log_path, "v3430-rollback-only")
    if len(devices) != 1:
        raise LiveGateError(f"rollback-only requires exactly one Odin device: {devices}")
    events: list[dict[str, str]] = []
    timeline_path = run_dir / "timeline.json"
    control.record_timeline_event(timeline_path, events, "live_session_start")
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "mode": "mandatory-rollback-only",
        "target": TARGET,
        "run_id": expectation.run_id,
        "verdict": "INCOMPLETE",
    }
    try:
        return rollback_and_collect(
            root,
            run_dir,
            log_path,
            events,
            expectation,
            pins,
            devices[0],
            result,
        )
    finally:
        control.record_timeline_event(timeline_path, events, "live_session_end")
        result["timeline_complete"] = control.timeline_complete(events)
        control.write_json_fsync(run_dir / "result.json", result)


def offline_plan(root: Path) -> dict[str, Any]:
    expectation, markers = load_candidate(root)
    rollback_pins = verify_rollback_inputs(root)
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "helper_sha256": helper_sha256(root),
        "run_id": expectation.run_id,
        "candidate_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "expected_markers_sha256": EXPECTED_MARKERS_SHA256,
        "candidate_ap_sha256": EXPECTED_CANDIDATE_AP_SHA256,
        "candidate_boot_sha256": EXPECTED_CANDIDATE_BOOT_SHA256,
        "observer_contract_sha256": observer.CONTRACT_SHA256,
        "transition_sha256": transition.TRANSITION_SHA256,
        "magisk_rollback_ap_sha256": transition.MAGISK_ROLLBACK_AP_SHA256,
        "stock_fallback_ap_sha256": transition.STOCK_ROLLBACK_AP_SHA256,
        "live_ack_token": LIVE_ACK_TOKEN,
        "rollback_ack_token": ROLLBACK_ACK_TOKEN,
        "candidate_flash": True,
        "manual_transition": True,
        "first_rollback_double_read": True,
        "artifact_marker_schema": markers["schema"],
        "rollback_files_pinned": sorted(rollback_pins),
        "live_authorized_by_plan": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--connected-dry-run", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--rollback-only", action="store_true")
    parser.add_argument("--ack", default="")
    parser.add_argument("--manual-wait-sec", type=int, default=MAX_MANUAL_WAIT_SEC)
    parser.add_argument("--print-plan", action="store_true")
    args = parser.parse_args()
    modes = sum((args.connected_dry_run, args.live, args.rollback_only))
    if modes > 1:
        raise SystemExit("select only one of --connected-dry-run/--live/--rollback-only")
    if args.manual_wait_sec < 30 or args.manual_wait_sec > MAX_MANUAL_WAIT_SEC:
        raise SystemExit(
            f"--manual-wait-sec must be between 30 and {MAX_MANUAL_WAIT_SEC}"
        )
    root = observer.repo_root()
    plan = offline_plan(root)
    if args.print_plan or modes == 0:
        print(json.dumps(plan, indent=2, sort_keys=True))
    if modes == 0:
        return 0
    run_dir = allocate_run_dir(root, args.run_dir)
    control.write_json_fsync(run_dir / "offline_plan.json", plan)
    try:
        if args.connected_dry_run:
            verify_agents_exception(root)
            log_path = run_dir / "dry_run.log"
            expectation, markers, _ = verify_host_inputs(
                root, log_path, include_full_stock=True
            )
            control.write_json_fsync(run_dir / "expected_markers.json", markers)
            _, summary = control.connected_preflight(root, run_dir, expectation)
            result = {
                "schema": SCHEMA,
                "mode": "connected-read-only-dry-run",
                "preflight": summary,
                "device_writes": False,
                "reboot": False,
                "flash": False,
            }
            control.write_json_fsync(run_dir / "result.json", result)
            print(f"V3430 connected dry-run PASS; run_dir={run_dir.relative_to(root)}")
            return 0
        if args.rollback_only:
            result = rollback_only(root, run_dir, args.ack)
        else:
            result = live_run(root, run_dir, args.ack, args.manual_wait_sec)
    except (LiveGateError, control.PositiveControlError, OSError) as exc:
        control.write_json_fsync(
            run_dir / "fatal.json",
            {"schema": SCHEMA, "error": str(exc), "timestamp_utc": control.utc_now()},
        )
        print(f"V3430 FAIL: {exc}", file=sys.stderr)
        return 2
    print(f"V3430 verdict={result['verdict']} run_dir={run_dir.relative_to(root)}")
    return 0 if result["verdict"] == "PASS_STAGE_A_AND_CROSS_SESSION_RETENTION" else 3


if __name__ == "__main__":
    raise SystemExit(main())
