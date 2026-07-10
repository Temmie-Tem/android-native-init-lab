#!/usr/bin/env python3
"""Guarded S22+ V3428R stock-origin transition positive-control retry.

The live mode writes two bounded run-unique frames to /dev/kmsg, verifies them
through fresh /proc/ap_klog snapshots, waits for attended manual Download entry,
reflashes the already-running Magisk boot image through Odin's AP slot, and
classifies two identical first-boot /proc/last_kmsg reads. No native-init
candidate is built or flashed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import s22plus_v3426_phase_observer_design as observer
import s22plus_v3427_transition_selection as transition
from s22plus_m3_observable_live_gate import run
from s22plus_o0_stock_usb_control import start_observers


SCHEMA = "s22plus_v3428r_stock_transition_positive_control_v1"
TARGET = observer.TARGET
LIVE_ACK_TOKEN = "S22PLUS-V3428R-STOCK-TRANSITION-POSITIVE-CONTROL-LIVE-GATE"
ACTIVE_EXCEPTION_HEADING = (
    "**Narrow operator-authorized exception (2026-07-10, S22+ V3428R "
    "stock-origin transition positive-control retry):**"
)
SCRIPT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3428_stock_transition_positive_control.py"
)
RUN_ROOT = Path("workspace/private/runs")
EXPECTED_BOOT_SHA256 = transition.MAGISK_ROLLBACK_BOOT_SHA256
EXPECTED_BIND = observer.DRIVER_BIND
MIN_DWELL_SEC = 60
MAX_MANUAL_WAIT_SEC = 120
MAX_TRANSITION_SEC = 180
POST_ROLLBACK_WAIT_SEC = 240
TIMELINE_REQUIRED_NAMES = (
    "live_session_start",
    "candidate_flash_start",
    "candidate_flash_done",
    "candidate_boot_ready",
    "rollback_flash_start",
    "rollback_flash_done",
    "rollback_boot_ready",
    "live_session_end",
)
TIMELINE_SEMANTIC_NAMES = (
    "no_candidate_flash_marker_arm_start",
    "no_candidate_flash_marker_pair_verified",
    "stock_origin_quiet_transition_start",
)
TIMELINE_NAMES = TIMELINE_REQUIRED_NAMES + TIMELINE_SEMANTIC_NAMES
SERIAL_RE = re.compile(r"RFCT[0-9A-Z]+")
ODIN_DEVICE_RE = re.compile(r"/dev/bus/usb/\d+/\d+")


class PositiveControlError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def repo_root() -> Path:
    return observer.repo_root()


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def redact(text: str) -> str:
    return SERIAL_RE.sub("<S22_SERIAL_REDACTED>", text)


def append_log(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(redact(text))
        if not text.endswith("\n"):
            handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_json_fsync(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def write_bytes_fsync(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def allocate_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    base = resolve(root, RUN_ROOT / f"s22plus_v3428r_stock_transition_{utc_stamp()}")
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
            return run_dir
        except FileExistsError:
            continue
    raise PositiveControlError(f"could not allocate run directory under {base.parent}")


def record_timeline_event(path: Path, events: list[dict[str, str]], name: str) -> None:
    if name not in TIMELINE_NAMES:
        raise PositiveControlError(f"non-canonical timeline event: {name}")
    if any(event["name"] == name for event in events):
        raise PositiveControlError(f"duplicate timeline event: {name}")
    events.append({"name": name, "timestamp_utc": utc_now()})
    write_json_fsync(path, {"events": events})


def timeline_complete(events: list[dict[str, str]]) -> bool:
    return set(TIMELINE_REQUIRED_NAMES).issubset(
        {event["name"] for event in events}
    )


def _adb_rows() -> list[tuple[str, str, str]]:
    result = run(["adb", "devices", "-l"], timeout=10.0)
    if result.returncode != 0:
        raise PositiveControlError("adb devices failed")
    rows: list[tuple[str, str, str]] = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split(maxsplit=2)
        if len(parts) >= 2:
            rows.append((parts[0], parts[1], parts[2] if len(parts) > 2 else ""))
    return rows


def select_one_android() -> str:
    usable = [row for row in _adb_rows() if row[1] == "device"]
    if len(usable) != 1:
        raise PositiveControlError(f"expected exactly one usable ADB target, got {len(usable)}")
    return usable[0][0]


def odin_devices(odin: Path, log_path: Path, label: str) -> list[str]:
    result = run([odin, "-l"], timeout=10.0)
    output = result.stdout + result.stderr
    devices = sorted(
        device
        for device in set(ODIN_DEVICE_RE.findall(output))
        if Path(device).exists()
    )
    append_log(
        log_path,
        f"[{utc_now()}] {label} odin4 -l rc={result.returncode} devices={devices}",
    )
    append_log(log_path, output)
    return devices


def wait_for_odin(
    odin: Path, log_path: Path, label: str, wait_sec: int
) -> str | None:
    deadline = time.monotonic() + wait_sec
    while True:
        devices = odin_devices(odin, log_path, label)
        if len(devices) == 1:
            return devices[0]
        if len(devices) > 1:
            raise PositiveControlError(f"refusing ambiguous Odin devices: {devices}")
        if time.monotonic() >= deadline:
            return None
        time.sleep(1.0)


def flash_ap(
    odin: Path, ap: Path, device: str, log_path: Path, label: str
) -> int:
    command = [odin, "--reboot", "-a", ap, "-d", device]
    append_log(log_path, f"{label}_cmd={' '.join(str(part) for part in command)}")
    result = run(command, timeout=240.0)
    append_log(log_path, f"{label}_odin_rc={result.returncode}")
    append_log(log_path, result.stdout + result.stderr)
    return result.returncode


def marker_context(run_id: str, phase: str) -> str:
    payload = {
        "schema": SCHEMA,
        "run_id": run_id,
        "phase": phase,
        "observer_contract_sha256": observer.CONTRACT_SHA256,
        "transition_sha256": transition.TRANSITION_SHA256,
        "boot_sha256": EXPECTED_BOOT_SHA256,
    }
    return hashlib.sha256(observer.canonical_json(payload)).hexdigest()


def make_expectation(run_id: str) -> observer.MarkerExpectation:
    return observer.make_expectation(
        run_id,
        marker_context(run_id, observer.PHASE_PRECHECK),
        marker_context(run_id, observer.PHASE_FINAL),
    )


def expected_marker_record(expectation: observer.MarkerExpectation) -> dict[str, Any]:
    precheck = observer.encode_marker(expectation, observer.PHASE_PRECHECK)
    final = observer.encode_marker(expectation, observer.PHASE_FINAL)
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "run_id": expectation.run_id,
        "observer_contract_sha256": observer.CONTRACT_SHA256,
        "transition_sha256": transition.TRANSITION_SHA256,
        "module_sha256": observer.MODULE_SHA256,
        "precheck_context_sha256": expectation.precheck_context_sha256,
        "final_context_sha256": expectation.final_context_sha256,
        "precheck_frame": precheck.decode("ascii"),
        "precheck_frame_sha256": hashlib.sha256(precheck).hexdigest(),
        "final_frame": final.decode("ascii"),
        "final_frame_sha256": hashlib.sha256(final).hexdigest(),
    }


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
        "S22+ V3428R stock-origin transition positive-control retry",
        str(SCRIPT_RELATIVE),
        helper_sha256(root),
        LIVE_ACK_TOKEN,
        TARGET,
        observer.CONTRACT_SHA256,
        transition.TRANSITION_SHA256,
        transition.MAGISK_ROLLBACK_AP_SHA256,
        transition.STOCK_ROLLBACK_AP_SHA256,
        "manual RDX/Download",
        "boot partition only",
        "/dev/kmsg PRECHECK and FINAL only",
        "first-boot /proc/last_kmsg double-read",
        "no native-init candidate",
        "no non-boot partition write",
    ]


def verify_agents_exception(root: Path) -> None:
    segment = active_exception_segment((root / "AGENTS.md").read_text(encoding="utf-8"))
    normalized = " ".join(segment.split())
    missing = [marker for marker in policy_markers(root) if marker not in normalized]
    consumed = "Consumed exception" in segment or "Consumed/retired" in segment
    if not segment or consumed:
        raise PositiveControlError("active V3428R exception is absent or consumed")
    if missing:
        raise PositiveControlError(f"V3428R exception missing markers: {missing}")


def verify_host_inputs(root: Path) -> dict[str, Any]:
    selection = transition.build_selection(root)
    if selection["transition_sha256"] != transition.TRANSITION_SHA256:
        raise PositiveControlError("V3427 transition contract mismatch")
    return {
        "helper_sha256": helper_sha256(root),
        "observer_contract_sha256": observer.CONTRACT_SHA256,
        "transition_sha256": transition.TRANSITION_SHA256,
        "magisk_rollback_ap_sha256": transition.MAGISK_ROLLBACK_AP_SHA256,
        "stock_fallback_ap_sha256": transition.STOCK_ROLLBACK_AP_SHA256,
        "live_authorized_by_artifacts": False,
    }


def read_root_text(serial: str, command: str, *, timeout: float = 30.0) -> str:
    result = root_shell(serial, command, timeout=timeout)
    if result.returncode != 0:
        raise PositiveControlError(f"root command failed: {command}")
    return result.stdout + result.stderr


def read_root_bytes(serial: str, command: str, *, timeout: float = 60.0) -> bytes:
    result = root_exec_out(serial, command, timeout=timeout)
    if result.returncode != 0 or result.stderr:
        raise PositiveControlError(f"root byte command failed: {command}")
    return result.stdout


def root_shell(
    serial: str, command: str, *, timeout: float = 30.0
) -> subprocess.CompletedProcess[str]:
    return run(
        ["adb", "-s", serial, "shell", f"su -c {shlex.quote(command)}"],
        timeout=timeout,
    )


def root_exec_out(
    serial: str, command: str, *, timeout: float = 60.0
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["adb", "-s", serial, "exec-out", f"su -c {shlex.quote(command)}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def connected_preflight(
    root: Path,
    run_dir: Path,
    expectation: observer.MarkerExpectation,
) -> tuple[str, dict[str, Any]]:
    serial = select_one_android()
    result = run(
        [
            "adb",
            "-s",
            serial,
            "shell",
            "printf 'model='; getprop ro.product.model; "
            "printf 'device='; getprop ro.product.device; "
            "printf 'bootloader='; getprop ro.boot.bootloader; "
            "printf 'incremental='; getprop ro.build.version.incremental; "
            "printf 'boot_completed='; getprop sys.boot_completed; "
            "printf 'vbstate='; getprop ro.boot.verifiedbootstate",
        ],
        timeout=30.0,
    )
    props = result.stdout + result.stderr
    required = (
        "model=SM-S906N",
        "device=g0q",
        "bootloader=S906NKSS7FYG8",
        "incremental=S906NKSS7FYG8",
        "boot_completed=1",
        "vbstate=orange",
    )
    missing = [token for token in required if token not in props]
    if result.returncode != 0 or missing:
        raise PositiveControlError(f"Android identity mismatch: {missing}")
    root_state = read_root_text(
        serial,
        "id; sha256sum /dev/block/by-name/boot; "
        "grep '^sec_log_buf ' /proc/modules; "
        f"test -L {shlex.quote(EXPECTED_BIND)} "
        "&& echo bind_ok=1 || echo bind_ok=0; "
        "stat -c '%n:%s:%a' /proc/ap_klog /proc/last_kmsg",
        timeout=45.0,
    )
    root_required = (
        "uid=0(root)",
        EXPECTED_BOOT_SHA256,
        "sec_log_buf ",
        " Live ",
        "bind_ok=1",
        "/proc/ap_klog:",
        "/proc/last_kmsg:",
    )
    root_missing = [token for token in root_required if token not in root_state]
    if root_missing:
        raise PositiveControlError(f"root baseline mismatch: {root_missing}")
    baseline = read_root_bytes(serial, "cat /proc/ap_klog")
    if not baseline or len(baseline) > transition.MAX_LAST_KMSG_BYTES:
        raise PositiveControlError(f"ap_klog size invalid: {len(baseline)}")
    baseline_result = observer.classify_marker_snapshot(
        "baseline", baseline, expectation
    )
    if not baseline_result["pass"]:
        raise PositiveControlError(f"baseline negative control failed: {baseline_result['errors']}")
    write_bytes_fsync(run_dir / "baseline_ap_klog.bin", baseline)
    summary = {
        "target": TARGET,
        "boot_sha256": EXPECTED_BOOT_SHA256,
        "sec_log_buf_live": True,
        "bind": EXPECTED_BIND,
        "baseline_ap_klog_bytes": len(baseline),
        "baseline_ap_klog_sha256": hashlib.sha256(baseline).hexdigest(),
        "baseline_marker_result": baseline_result,
    }
    write_json_fsync(run_dir / "connected_preflight.json", summary)
    return serial, summary


def emit_marker(serial: str, frame: bytes) -> None:
    text = frame.decode("ascii")
    command = f"printf '%s\\n' {shlex.quote(text)} > /dev/kmsg"
    result = root_shell(serial, command, timeout=30.0)
    if result.returncode != 0:
        raise PositiveControlError("marker write failed")


def verify_current_ring(
    serial: str,
    stage: str,
    expectation: observer.MarkerExpectation,
    output: Path,
) -> dict[str, Any]:
    payload = read_root_bytes(serial, "cat /proc/ap_klog")
    write_bytes_fsync(output, payload)
    result = observer.classify_marker_snapshot(stage, payload, expectation)
    if not result["pass"]:
        raise PositiveControlError(f"{stage} current-ring verification failed: {result['errors']}")
    return result


def evaluate_postrollback_health(props: str, root_state: str) -> dict[str, bool]:
    health = {
        "model": "model=SM-S906N" in props,
        "device": "device=g0q" in props,
        "bootloader": "bootloader=S906NKSS7FYG8" in props,
        "incremental": "incremental=S906NKSS7FYG8" in props,
        "boot_completed": "boot_completed=1" in props,
        "vbstate": "vbstate=orange" in props,
        "root": "uid=0(root)" in root_state,
        "boot_sha256_match": EXPECTED_BOOT_SHA256 in root_state,
    }
    health["pass"] = all(health.values())
    return health


def read_postrollback_health(serial: str) -> dict[str, bool]:
    result = run(
        [
            "adb",
            "-s",
            serial,
            "shell",
            "printf 'model='; getprop ro.product.model; "
            "printf 'device='; getprop ro.product.device; "
            "printf 'bootloader='; getprop ro.boot.bootloader; "
            "printf 'incremental='; getprop ro.build.version.incremental; "
            "printf 'boot_completed='; getprop sys.boot_completed; "
            "printf 'vbstate='; getprop ro.boot.verifiedbootstate",
        ],
        timeout=30.0,
    )
    if result.returncode != 0:
        raise PositiveControlError("post-rollback Android identity read failed")
    root_state = read_root_text(
        serial,
        "id; sha256sum /dev/block/by-name/boot",
        timeout=45.0,
    )
    return evaluate_postrollback_health(result.stdout + result.stderr, root_state)


def wait_for_first_boot_ready(wait_sec: int) -> tuple[str, dict[str, bool]] | None:
    deadline = time.monotonic() + wait_sec
    while time.monotonic() < deadline:
        try:
            serial = select_one_android()
            health = read_postrollback_health(serial)
            if health["pass"]:
                return serial, health
        except (PositiveControlError, subprocess.TimeoutExpired):
            pass
        time.sleep(1.0)
    return None


def collect_first_boot(
    serial: str,
    run_dir: Path,
    expectation: observer.MarkerExpectation,
) -> dict[str, Any]:
    first_result = root_exec_out(serial, "cat /proc/last_kmsg", timeout=75.0)
    time.sleep(0.25)
    second_result = root_exec_out(serial, "cat /proc/last_kmsg", timeout=75.0)
    first = first_result.stdout
    second = second_result.stdout
    write_bytes_fsync(run_dir / "first_boot_last_kmsg_1.bin", first)
    write_bytes_fsync(run_dir / "first_boot_last_kmsg_2.bin", second)
    classification = transition.classify_first_boot_capture(
        first,
        second,
        expectation,
        first_eof=first_result.returncode == 0 and not first_result.stderr,
        second_eof=second_result.returncode == 0 and not second_result.stderr,
    )
    result = {
        "first_bytes": len(first),
        "second_bytes": len(second),
        "first_sha256": hashlib.sha256(first).hexdigest(),
        "second_sha256": hashlib.sha256(second).hexdigest(),
        "classification": classification,
    }
    write_json_fsync(run_dir / "first_boot_classification.json", result)
    return result


def stop_observers(observers: list[Any]) -> dict[str, dict[str, Any]]:
    stopped: dict[str, dict[str, Any]] = {}
    for item in observers:
        state = item.stop()
        stopped[state.name] = {
            "started": state.started,
            "returncode": state.returncode,
            "start_error": state.start_error,
        }
    return stopped


def live_run(
    root: Path,
    run_dir: Path,
    ack: str,
    manual_wait_sec: int,
) -> dict[str, Any]:
    if ack != LIVE_ACK_TOKEN:
        raise PositiveControlError("live acknowledgement token mismatch")
    verify_agents_exception(root)
    expectation = make_expectation(observer.generate_run_id())
    expected = expected_marker_record(expectation)
    write_json_fsync(run_dir / "expected_markers.json", expected)
    events: list[dict[str, str]] = []
    timeline_path = run_dir / "timeline.json"
    record_timeline_event(timeline_path, events, "live_session_start")
    serial, preflight = connected_preflight(root, run_dir, expectation)
    observers = start_observers(run_dir, serial)
    log_path = run_dir / "live.log"
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "target": TARGET,
        "run_id": expectation.run_id,
        "preflight": preflight,
        "candidate_flash": False,
        "timeline_semantics": {
            "candidate_flash_start": "marker_arm_start_no_candidate_flash",
            "candidate_flash_done": "marker_pair_verified_no_candidate_flash",
            "candidate_boot_ready": "stock_origin_quiet_transition_start",
        },
        "verdict": "INCOMPLETE",
    }
    try:
        record_timeline_event(timeline_path, events, "candidate_flash_start")
        record_timeline_event(
            timeline_path, events, "no_candidate_flash_marker_arm_start"
        )
        emit_marker(
            serial,
            observer.encode_marker(expectation, observer.PHASE_PRECHECK),
        )
        result["precheck_current_ring"] = verify_current_ring(
            serial,
            "precheck",
            expectation,
            run_dir / "precheck_ap_klog.bin",
        )
        emit_marker(
            serial,
            observer.encode_marker(expectation, observer.PHASE_FINAL),
        )
        result["final_current_ring"] = verify_current_ring(
            serial,
            "final",
            expectation,
            run_dir / "final_ap_klog.bin",
        )
        record_timeline_event(timeline_path, events, "candidate_flash_done")
        record_timeline_event(
            timeline_path, events, "no_candidate_flash_marker_pair_verified"
        )
        record_timeline_event(timeline_path, events, "candidate_boot_ready")
        record_timeline_event(
            timeline_path, events, "stock_origin_quiet_transition_start"
        )
        transition_started = time.monotonic()
        append_log(log_path, "compatibility_note=candidate_flash events are marker-arm events; no candidate flash")
        print(f"MARKER_PAIR_VERIFIED quiet_dwell_sec={MIN_DWELL_SEC}", flush=True)
        time.sleep(MIN_DWELL_SEC)
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
        odin_device = wait_for_odin(
            transition.ODIN4,
            log_path,
            "v3428r-manual-download",
            remaining,
        )
        if odin_device is None:
            result["verdict"] = "UNAVAILABLE_STOP_MANUAL_DOWNLOAD_TIMEOUT"
            return result
        transition_elapsed = time.monotonic() - transition_started
        result["manual_transition_elapsed_sec"] = transition_elapsed
        if transition_elapsed > MAX_TRANSITION_SEC:
            result["verdict"] = "UNAVAILABLE_STOP_TRANSITION_DEADLINE"
            return result
        verify_agents_exception(root)
        verify_host_inputs(root)
        if time.monotonic() - transition_started > MAX_TRANSITION_SEC:
            result["verdict"] = "UNAVAILABLE_STOP_TRANSITION_DEADLINE"
            return result
        record_timeline_event(timeline_path, events, "rollback_flash_start")
        primary_ap = root / transition.MAGISK_ROLLBACK_AP
        flash_rc = flash_ap(
            transition.ODIN4,
            primary_ap,
            odin_device,
            log_path,
            "v3428r_magisk_identity_rollback",
        )
        record_timeline_event(timeline_path, events, "rollback_flash_done")
        result["primary_rollback_rc"] = flash_rc
        if flash_rc != 0:
            verify_host_inputs(root)
            fallback_device = wait_for_odin(
                transition.ODIN4, log_path, "v3428r-fallback", 15
            )
            if fallback_device is not None:
                result["stock_fallback_rc"] = flash_ap(
                    transition.ODIN4,
                    root / transition.STOCK_ROLLBACK_AP,
                    fallback_device,
                    log_path,
                    "v3428r_stock_recovery_only",
                )
            result["verdict"] = "RECOVERY_ONLY_NO_PROOF_STOP"
            return result
        first_boot = wait_for_first_boot_ready(POST_ROLLBACK_WAIT_SEC)
        if first_boot is None:
            result["verdict"] = "UNAVAILABLE_STOP_FIRST_ROOT_TIMEOUT"
            return result
        first_boot_serial, health = first_boot
        result["postrollback_health"] = health
        if not health["pass"]:
            result["verdict"] = "UNAVAILABLE_STOP_POSTROLLBACK_HEALTH"
            return result
        record_timeline_event(timeline_path, events, "rollback_boot_ready")
        capture = collect_first_boot(first_boot_serial, run_dir, expectation)
        result["first_boot_capture"] = capture
        result["verdict"] = capture["classification"]["verdict"]
        return result
    finally:
        observer_rcs = stop_observers(observers)
        result["observer_rcs"] = observer_rcs
        if not any(event["name"] == "live_session_end" for event in events):
            record_timeline_event(timeline_path, events, "live_session_end")
        result["timeline_complete"] = timeline_complete(events)
        write_json_fsync(run_dir / "result.json", result)


def offline_plan(root: Path) -> dict[str, Any]:
    inputs = verify_host_inputs(root)
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "helper_sha256": inputs["helper_sha256"],
        "observer_contract_sha256": observer.CONTRACT_SHA256,
        "transition_sha256": transition.TRANSITION_SHA256,
        "live_ack_token": LIVE_ACK_TOKEN,
        "manual_transition": True,
        "candidate_flash": False,
        "boot_only_identity_rollback": True,
        "live_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--connected-dry-run", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--ack", default="")
    parser.add_argument("--manual-wait-sec", type=int, default=MAX_MANUAL_WAIT_SEC)
    parser.add_argument("--print-plan", action="store_true")
    args = parser.parse_args()
    if args.live and args.connected_dry_run:
        raise SystemExit("--live and --connected-dry-run are mutually exclusive")
    if args.manual_wait_sec < 30 or args.manual_wait_sec > MAX_MANUAL_WAIT_SEC:
        raise SystemExit(
            f"--manual-wait-sec must be between 30 and {MAX_MANUAL_WAIT_SEC}"
        )
    root = repo_root()
    plan = offline_plan(root)
    if args.print_plan:
        print(json.dumps(plan, indent=2, sort_keys=True))
    if not args.connected_dry_run and not args.live:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    run_dir = allocate_run_dir(root, args.run_dir)
    write_json_fsync(run_dir / "offline_plan.json", plan)
    if args.connected_dry_run:
        expectation = make_expectation(observer.generate_run_id())
        write_json_fsync(
            run_dir / "expected_markers.json", expected_marker_record(expectation)
        )
        _, summary = connected_preflight(root, run_dir, expectation)
        result = {
            "schema": SCHEMA,
            "mode": "connected-read-only-dry-run",
            "preflight": summary,
            "device_writes": False,
            "flash": False,
        }
        write_json_fsync(run_dir / "result.json", result)
        print(f"connected dry-run PASS; run_dir={run_dir.relative_to(root)}")
        return 0
    try:
        result = live_run(root, run_dir, args.ack, args.manual_wait_sec)
    except PositiveControlError as exc:
        write_json_fsync(
            run_dir / "fatal.json",
            {"schema": SCHEMA, "error": str(exc), "timestamp_utc": utc_now()},
        )
        print(f"V3428R FAIL: {exc}", file=sys.stderr)
        return 2
    print(f"V3428R verdict={result['verdict']} run_dir={run_dir.relative_to(root)}")
    return 0 if result["verdict"] == "PASS_STAGE_A_AND_CROSS_SESSION_RETENTION" else 3


if __name__ == "__main__":
    raise SystemExit(main())
