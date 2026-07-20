#!/usr/bin/env python3
"""Inactive-until-bound R4W1-C3 regular-path boot-only F1 gate.

This successor keeps the qualified R4W1-C candidate unchanged and replaces
only the Odin AP transport that previously used an anonymous proc-fd pathname.
Offline modes never contact the device.  Connected and live modes remain
separately acknowledgement- and policy-gated.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import s22plus_boot_only_f1_transport as f1
import s22plus_boot_only_live_core as core
import s22plus_fyg8_r3c0_live_gate as legacy_transport
import s22plus_fyg8_r4w1c_connected_gate as connected
import s22plus_fyg8_r4w1c_live_gate as legacy_r4w1c


SCHEMA = "s22plus_fyg8_r4w1c3_regular_ap_live_gate_v1"
TARGET = connected.TARGET
SCRIPT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1c3_regular_ap_live_gate.py"
)
TEST_RELATIVE = Path("tests/test_s22plus_fyg8_r4w1c3_regular_ap_live_gate.py")
F1_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_boot_only_f1_transport.py"
)
F1_TEST_RELATIVE = Path("tests/test_s22plus_boot_only_f1_transport.py")
CONNECTED_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1c_connected_gate.py"
)
LEGACY_R4W1C_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1c_live_gate.py"
)
POLICY_DRAFT = Path(
    "docs/operations/S22PLUS_FYG8_R4W1C3_REGULAR_AP_F1_EXCEPTION_DRAFT_2026-07-21.md"
)
POLICY_MARKER = "S22+ FYG8 R4W1-C3 regular-path direct-PID1 boot-only F1 gate"
POLICY_BEGIN = "BEGIN_S22PLUS_FYG8_R4W1C3_REGULAR_AP_F1_POLICY_V1"
POLICY_END = "END_S22PLUS_FYG8_R4W1C3_REGULAR_AP_F1_POLICY_V1"
ACTIVE_SENTINEL = "S22PLUS_FYG8_R4W1C3_REGULAR_AP_F1_POLICY_STATE=ACTIVE"
LIVE_ACK_TOKEN = "S22PLUS-FYG8-R4W1C3-REGULAR-AP-DIRECT-PID1-LIVE"
CONNECTED_ACK_TOKEN = "S22PLUS-FYG8-R4W1C3-CONNECTED-READ-ONLY-DRY-RUN"
ROLLBACK_ACK_TOKEN = "S22PLUS-FYG8-R4W1C3-MAGISK-ROLLBACK-FROM-DOWNLOAD"
PASS_VERDICT = "PASS_R4W1C3_DIRECT_PID1_EXEC_ACCEPTED_AND_ROLLED_BACK"
NO_PROOF_VERDICT = "NO_PROOF_R4W1C3_MARKER_ABSENT_MAGISK_ROLLED_BACK"

RUN_ROOT = Path("workspace/private/runs")
CONSUMED_STATE = Path(
    "workspace/private/state/"
    "s22plus_fyg8_r4w1c3_regular_ap_live_exception_consumed.json"
)
MAX_TRANSFER_OUTPUT = 8 * 1024 * 1024
DEFAULT_PARK_WAIT_SEC = 120.0
DEFAULT_DOWNLOAD_WAIT_SEC = 180
DEFAULT_ANDROID_WAIT_SEC = 300.0
STABLE_DOWNLOAD_SAMPLES = 3


class GateError(RuntimeError):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def resolve(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else (root / value).resolve()


def source_identity(root: Path, relative: Path) -> dict[str, Any]:
    path = root / relative
    identity = core.hash_stable_file(path)
    return {"path": str(relative), **identity}


def verify_regular_inputs(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    paths = {
        "candidate": (
            resolve(root, args.candidate_ap),
            connected.EXPECTED_CANDIDATE_AP_SIZE,
            connected.EXPECTED_CANDIDATE_AP_SHA256,
        ),
        "magisk": (
            resolve(root, args.magisk_ap),
            connected.EXPECTED_MAGISK_AP_SIZE,
            connected.EXPECTED_MAGISK_AP_SHA256,
        ),
        "stock": (
            resolve(root, args.stock_ap),
            connected.EXPECTED_STOCK_AP_SIZE,
            connected.EXPECTED_STOCK_AP_SHA256,
        ),
    }
    result: dict[str, Any] = {}
    for label, (path, size, digest) in paths.items():
        with f1.pin_boot_only_ap(
            path,
            label=f"{label} AP",
            expected_size=size,
            expected_sha256=digest,
        ) as pinned:
            result[label] = pinned.receipt()
    odin_path = resolve(root, args.odin)
    with f1.pin_regular_file(
        odin_path,
        label="Odin4",
        expected_size=connected.EXPECTED_ODIN_SIZE,
        expected_sha256=connected.EXPECTED_ODIN_SHA256,
    ) as pinned_odin:
        if not os.access(pinned_odin.path, os.X_OK):
            raise GateError("pinned Odin4 is not executable")
        result["odin"] = pinned_odin.receipt()
    return result


def verify_artifacts(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    identities = {
        "candidate_boot": connected.require_identity(
            resolve(root, args.candidate_boot),
            connected.EXPECTED_CANDIDATE_BOOT_SIZE,
            connected.EXPECTED_CANDIDATE_BOOT_SHA256,
            "candidate boot",
        ),
        "candidate_lz4": connected.require_identity(
            resolve(root, args.candidate_lz4),
            connected.EXPECTED_CANDIDATE_LZ4_SIZE,
            connected.EXPECTED_CANDIDATE_LZ4_SHA256,
            "candidate LZ4",
        ),
        "candidate_ap": connected.require_identity(
            resolve(root, args.candidate_ap),
            connected.EXPECTED_CANDIDATE_AP_SIZE,
            connected.EXPECTED_CANDIDATE_AP_SHA256,
            "candidate AP",
        ),
        "manifest": connected.require_identity(
            resolve(root, args.manifest),
            connected.EXPECTED_MANIFEST_SIZE,
            connected.EXPECTED_MANIFEST_SHA256,
            "candidate manifest",
        ),
        "static_result": connected.require_identity(
            resolve(root, args.static_result),
            connected.EXPECTED_STATIC_RESULT_SIZE,
            connected.EXPECTED_STATIC_RESULT_SHA256,
            "static result",
        ),
        "magisk_rollback_ap": connected.require_identity(
            resolve(root, args.magisk_ap),
            connected.EXPECTED_MAGISK_AP_SIZE,
            connected.EXPECTED_MAGISK_AP_SHA256,
            "Magisk rollback AP",
        ),
        "stock_cleanup_ap": connected.require_identity(
            resolve(root, args.stock_ap),
            connected.EXPECTED_STOCK_AP_SIZE,
            connected.EXPECTED_STOCK_AP_SHA256,
            "stock cleanup AP",
        ),
        "full_firmware": connected.require_identity(
            resolve(root, args.full_firmware),
            connected.EXPECTED_FULL_FIRMWARE_SIZE,
            connected.EXPECTED_FULL_FIRMWARE_SHA256,
            "full FYG8 firmware",
        ),
        "odin": connected.require_identity(
            resolve(root, args.odin),
            connected.EXPECTED_ODIN_SIZE,
            connected.EXPECTED_ODIN_SHA256,
            "Odin4",
        ),
    }
    for label, path in (
        ("candidate AP", resolve(root, args.candidate_ap)),
        ("Magisk rollback AP", resolve(root, args.magisk_ap)),
        ("stock cleanup AP", resolve(root, args.stock_ap)),
    ):
        if connected.tar_members(path) != [f1.BOOT_MEMBER]:
            raise GateError(f"{label} is not exactly boot-only")
    construction_sources = {
        "static_checker": (
            connected.STATIC_CHECKER_RELATIVE,
            connected.EXPECTED_STATIC_CHECKER_SIZE,
            connected.EXPECTED_STATIC_CHECKER_SHA256,
        ),
        "static_checker_test": (
            connected.STATIC_CHECKER_TEST_RELATIVE,
            connected.EXPECTED_STATIC_CHECKER_TEST_SIZE,
            connected.EXPECTED_STATIC_CHECKER_TEST_SHA256,
        ),
        "builder": (
            connected.BUILDER_RELATIVE,
            connected.EXPECTED_BUILDER_SIZE,
            connected.EXPECTED_BUILDER_SHA256,
        ),
        "builder_test": (
            connected.BUILDER_TEST_RELATIVE,
            connected.EXPECTED_BUILDER_TEST_SIZE,
            connected.EXPECTED_BUILDER_TEST_SHA256,
        ),
        "live_core": (
            connected.LIVE_CORE_RELATIVE,
            connected.EXPECTED_LIVE_CORE_SIZE,
            connected.EXPECTED_LIVE_CORE_SHA256,
        ),
        "live_core_test": (
            connected.LIVE_CORE_TEST_RELATIVE,
            connected.EXPECTED_LIVE_CORE_TEST_SIZE,
            connected.EXPECTED_LIVE_CORE_TEST_SHA256,
        ),
        "legacy_transport": (
            connected.TRANSPORT_RELATIVE,
            connected.EXPECTED_TRANSPORT_SIZE,
            connected.EXPECTED_TRANSPORT_SHA256,
        ),
    }
    fixed_sources = {
        label: connected.require_identity(root / path, size, digest, label)
        for label, (path, size, digest) in construction_sources.items()
    }
    return {
        "identities": identities,
        "fixed_sources": fixed_sources,
        "fresh_static_checker": connected.run_fresh_static_checker(root),
        "ap_members": [f1.BOOT_MEMBER],
        "regular_path_inputs": verify_regular_inputs(root, args),
        "sources": {
            "helper": source_identity(root, SCRIPT_RELATIVE),
            "test": source_identity(root, TEST_RELATIVE),
            "f1_transport": source_identity(root, F1_RELATIVE),
            "f1_transport_test": source_identity(root, F1_TEST_RELATIVE),
            "connected_gate": source_identity(root, CONNECTED_RELATIVE),
            "legacy_r4w1c_helpers": source_identity(root, LEGACY_R4W1C_RELATIVE),
        },
    }


def required_policy_values(root: Path) -> tuple[str, ...]:
    return (
        POLICY_BEGIN,
        POLICY_END,
        POLICY_MARKER,
        ACTIVE_SENTINEL,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        str(SCRIPT_RELATIVE),
        core.sha256_file(root / SCRIPT_RELATIVE),
        str(TEST_RELATIVE),
        core.sha256_file(root / TEST_RELATIVE),
        str(F1_RELATIVE),
        core.sha256_file(root / F1_RELATIVE),
        str(F1_TEST_RELATIVE),
        core.sha256_file(root / F1_TEST_RELATIVE),
        str(CONNECTED_RELATIVE),
        core.sha256_file(root / CONNECTED_RELATIVE),
        str(LEGACY_R4W1C_RELATIVE),
        core.sha256_file(root / LEGACY_R4W1C_RELATIVE),
        connected.EXPECTED_CANDIDATE_AP_SHA256,
        connected.EXPECTED_MAGISK_AP_SHA256,
        connected.EXPECTED_STOCK_AP_SHA256,
        connected.EXPECTED_FULL_FIRMWARE_SHA256,
        connected.EXPECTED_ODIN_SHA256,
    )


def verify_policy_draft(root: Path) -> dict[str, Any]:
    path = root / POLICY_DRAFT
    if path.is_symlink() or not path.is_file():
        raise GateError("R4W1-C3 policy draft is missing or indirect")
    text = path.read_text(encoding="utf-8")
    if "DRAFT_INACTIVE" not in text:
        raise GateError("R4W1-C3 policy draft is not inactive")
    missing = [value for value in required_policy_values(root) if value not in text]
    if missing:
        raise GateError(f"R4W1-C3 policy draft is missing pins: {missing}")
    return {
        "path": str(POLICY_DRAFT),
        "size": path.stat().st_size,
        "sha256": core.sha256_file(path),
        "active": policy_active(root),
    }


def policy_active(root: Path) -> bool:
    text = (root / "AGENTS.md").read_text(encoding="utf-8")
    if text.count(POLICY_BEGIN) != 1 or text.count(POLICY_END) != 1:
        return False
    start = text.index(POLICY_BEGIN)
    end = text.index(POLICY_END, start)
    if end <= start:
        return False
    clause = text[start : end + len(POLICY_END)]
    active = re.findall(
        rf"(?m)^\s*`?{re.escape(ACTIVE_SENTINEL)}`?\s*$", clause
    )
    return len(active) == 1 and all(
        value in clause for value in required_policy_values(root)
    )


def consumed_path(root: Path) -> Path:
    return root / CONSUMED_STATE


def consume_exception(
    root: Path,
    run_dir: Path,
    artifacts: dict[str, Any],
    baseline: dict[str, str],
    usb_binding: dict[str, str],
) -> dict[str, Any]:
    value = {
        "schema": "s22plus_fyg8_r4w1c3_regular_ap_consumed_v1",
        "consumed_at_utc": core.utc_now(),
        "reason": "candidate_flash_start",
        "run_dir": str(run_dir.relative_to(root)),
        "target": TARGET,
        "candidate_ap_sha256": connected.EXPECTED_CANDIDATE_AP_SHA256,
        "magisk_ap_sha256": connected.EXPECTED_MAGISK_AP_SHA256,
        "helper_sha256": artifacts["sources"]["helper"]["sha256"],
        "baseline": baseline,
        "usb_binding": usb_binding,
    }
    core.durable_create_json(consumed_path(root), value)
    return value


def load_consumed(root: Path) -> dict[str, Any]:
    path = consumed_path(root)
    try:
        value = json.loads(core.read_stable_file(path, maximum=1024 * 1024))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GateError("R4W1-C3 consumed state is unavailable") from exc
    if (
        value.get("schema") != "s22plus_fyg8_r4w1c3_regular_ap_consumed_v1"
        or value.get("target") != TARGET
        or value.get("candidate_ap_sha256") != connected.EXPECTED_CANDIDATE_AP_SHA256
        or value.get("magisk_ap_sha256") != connected.EXPECTED_MAGISK_AP_SHA256
    ):
        raise GateError("R4W1-C3 consumed state contract mismatch")
    return value


def no_odin_endpoint(odin: Path, log_path: Path, label: str) -> None:
    devices = legacy_transport.odin_devices(odin, log_path, label)
    if devices:
        raise GateError(f"{label} requires no Odin endpoint: {devices}")


def wait_bound_download(
    odin: Path,
    log_path: Path,
    expected_topology: str,
    wait_sec: int,
    label: str,
) -> tuple[str, dict[str, str]]:
    deadline = time.monotonic() + wait_sec
    prior: tuple[str, dict[str, str]] | None = None
    stable = 0
    while time.monotonic() < deadline:
        devices = legacy_transport.odin_devices(odin, log_path, label)
        if len(devices) > 1:
            raise GateError(f"ambiguous Odin endpoints: {devices}")
        if len(devices) == 1:
            device = devices[0]
            identity = legacy_r4w1c.endpoint_usb_identity(device)
            if identity.get("topology") != expected_topology:
                raise GateError("Download endpoint changed USB topology")
            sample = (device, identity)
            stable = stable + 1 if sample == prior else 1
            prior = sample
            if stable >= STABLE_DOWNLOAD_SAMPLES:
                return sample
        time.sleep(0.25)
    raise GateError(f"bounded wait for {label} Download endpoint expired")


def create_bytes(path: Path, payload: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return {"path": str(path), **core.hash_stable_file(path)}


def transfer_ap(
    root: Path,
    args: argparse.Namespace,
    device: str,
    ap: Path,
    size: int,
    digest: str,
    label: str,
    run_dir: Path,
) -> dict[str, Any]:
    receipt, stdout, stderr = f1.execute_odin_boot_only(
        resolve(root, args.odin),
        resolve(root, ap),
        device,
        odin_size=connected.EXPECTED_ODIN_SIZE,
        odin_sha256=connected.EXPECTED_ODIN_SHA256,
        ap_size=size,
        ap_sha256=digest,
        label=label,
        timeout=240,
        maximum_output=MAX_TRANSFER_OUTPUT,
    )
    receipt["stdout"] = create_bytes(run_dir / f"{label}.stdout", stdout)
    receipt["stderr"] = create_bytes(run_dir / f"{label}.stderr", stderr)
    core.durable_create_json(run_dir / f"{label}.json", receipt)
    return receipt


def wait_magisk_android(
    seconds: float,
    expected_serial: str,
    usb_binding: dict[str, str],
) -> tuple[str, dict[str, str]]:
    return legacy_r4w1c.wait_magisk_android(
        seconds,
        expected_serial=expected_serial,
        expected_usb_binding=usb_binding,
    )


def wait_stock_android(seconds: float) -> dict[str, str]:
    deadline = time.monotonic() + seconds
    last_error = "no stock Android observation"
    while time.monotonic() < deadline:
        try:
            return legacy_transport.current_stock_android()
        except (legacy_transport.GateError, OSError, subprocess.SubprocessError) as exc:
            last_error = str(exc)
            time.sleep(2)
    raise GateError(f"stock cleanup Android did not return: {last_error}")


def rollback_transfer(
    root: Path,
    args: argparse.Namespace,
    device: str,
    run_dir: Path,
) -> tuple[str, dict[str, Any]]:
    magisk = transfer_ap(
        root,
        args,
        device,
        args.magisk_ap,
        connected.EXPECTED_MAGISK_AP_SIZE,
        connected.EXPECTED_MAGISK_AP_SHA256,
        "magisk-rollback",
        run_dir,
    )
    if magisk["returncode"] == 0:
        return "magisk", magisk
    odin = resolve(root, args.odin)
    devices = legacy_transport.odin_devices(odin, run_dir / "live.log", "stock-cleanup")
    if devices != [device]:
        raise GateError("Magisk transfer failed without the same rollback endpoint")
    stock = transfer_ap(
        root,
        args,
        device,
        args.stock_ap,
        connected.EXPECTED_STOCK_AP_SIZE,
        connected.EXPECTED_STOCK_AP_SHA256,
        "stock-cleanup",
        run_dir,
    )
    if stock["returncode"] != 0:
        raise GateError("both Magisk rollback and stock cleanup transfers failed")
    return "stock", stock


def passive_observation(seconds: float) -> dict[str, Any]:
    if not math.isfinite(seconds) or not 0 <= seconds <= 180:
        raise GateError("candidate observation bound is invalid")
    started = time.monotonic()
    time.sleep(seconds)
    return {
        "bounded": True,
        "requested_sec": seconds,
        "elapsed_sec": round(time.monotonic() - started, 6),
        "candidate_adb_required": False,
        "load_bearing": False,
    }


def classify_verdict(
    candidate_rc: int,
    rollback_target: str,
    marker: dict[str, Any] | None,
) -> tuple[str, int]:
    if rollback_target != "magisk":
        return "STOCK_CLEANUP_MAGISK_BASELINE_NOT_RESTORED", 30
    if candidate_rc != 0:
        return "NO_PROOF_R4W1C3_CANDIDATE_TRANSFER_FAILED_MAGISK_ROLLED_BACK", 31
    if marker is not None and marker.get("acceptance_present") is True:
        return PASS_VERDICT, 0
    return NO_PROOF_VERDICT, 32


def wait_recovery_magisk_android(
    seconds: float, usb_binding: dict[str, str]
) -> tuple[str, dict[str, str]]:
    deadline = time.monotonic() + seconds
    last_error = "no exact Magisk Android observation"
    while time.monotonic() < deadline:
        try:
            serial, final = connected.current_android_exact()
            if core.sha256_bytes(serial.encode("ascii")) != usb_binding.get(
                "serial_sha256"
            ):
                raise GateError("recovery Android serial binding changed")
            if legacy_r4w1c.adb_usb_binding(serial) != usb_binding:
                raise GateError("recovery Android USB binding changed")
            return serial, final
        except (
            GateError,
            connected.GateError,
            legacy_transport.GateError,
            OSError,
            UnicodeError,
            subprocess.SubprocessError,
        ) as exc:
            last_error = str(exc)
            time.sleep(2)
    raise GateError(f"exact Magisk Android did not return: {last_error}")


def wait_rollback_endpoint(
    root: Path,
    args: argparse.Namespace,
    run_dir: Path,
    usb_binding: dict[str, str],
) -> tuple[str, dict[str, str]]:
    odin = resolve(root, args.odin)
    return wait_bound_download(
        odin,
        run_dir / "live.log",
        usb_binding["topology"],
        args.manual_download_wait_sec,
        "mandatory-rollback",
    )


def finish_rollback(
    root: Path,
    args: argparse.Namespace,
    run_dir: Path,
    expected_serial: str,
    usb_binding: dict[str, str],
    candidate_rc: int,
    rollback: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    odin = resolve(root, args.odin)
    rollback_target = str(rollback["target"])
    if rollback_target == "magisk":
        serial, final = wait_magisk_android(
            args.android_wait_sec, expected_serial, usb_binding
        )
        observer = legacy_r4w1c.collect_rollback_observer(root, serial, run_dir, 0)
        marker = observer["marker"]
    else:
        final = wait_stock_android(args.android_wait_sec)
        observer = None
        marker = None
    no_odin_endpoint(odin, run_dir / "live.log", "final")
    verdict, rc = classify_verdict(candidate_rc, rollback_target, marker)
    rollback.update({"final": final, "observer": observer, "verdict": verdict})
    return rollback, rc


def live_run(
    root: Path,
    args: argparse.Namespace,
    artifacts: dict[str, Any],
) -> int:
    if not policy_active(root):
        raise GateError("R4W1-C3 F1 policy is inactive")
    if args.ack != LIVE_ACK_TOKEN:
        raise GateError("R4W1-C3 live acknowledgement mismatch")
    if consumed_path(root).exists() or consumed_path(root).is_symlink():
        raise GateError("R4W1-C3 one-shot state is already consumed")
    serial, baseline = connected.current_android_exact()
    usb_binding = legacy_r4w1c.adb_usb_binding(serial)
    odin = resolve(root, args.odin)
    no_odin_endpoint(odin, Path(os.devnull), "baseline")
    run_dir = core.allocate_run_dir(root, RUN_ROOT, "s22plus-r4w1c3-live", args.run_dir)
    timeline: list[dict[str, str]] = []
    timeline_path = run_dir / "timeline.json"
    result_path = run_dir / "result.json"
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "mode": "live",
        "target": TARGET,
        "artifacts": artifacts,
        "baseline": baseline,
        "usb_binding": usb_binding,
        "candidate_transfer_attempted": False,
        "verdict": "INCOMPLETE",
    }
    core.append_event(timeline_path, timeline, "live_session_start")
    core.durable_write_json(result_path, result)

    reboot = legacy_transport.run(["adb", "-s", serial, "reboot", "download"], timeout=20)
    if reboot.returncode != 0:
        raise GateError("Android failed to request Download mode")
    device, endpoint = wait_bound_download(
        odin,
        run_dir / "live.log",
        usb_binding["topology"],
        args.download_wait_sec,
        "candidate",
    )
    consumed = consume_exception(root, run_dir, artifacts, baseline, usb_binding)
    core.append_event(timeline_path, timeline, "candidate_flash_start")
    result["candidate_transfer_attempted"] = True
    result["consumed_state"] = consumed
    result["candidate_endpoint"] = endpoint
    core.durable_write_json(result_path, result)

    try:
        candidate = transfer_ap(
            root,
            args,
            device,
            args.candidate_ap,
            connected.EXPECTED_CANDIDATE_AP_SIZE,
            connected.EXPECTED_CANDIDATE_AP_SHA256,
            "candidate",
            run_dir,
        )
        candidate_rc = int(candidate["returncode"])
        result["candidate_transfer"] = candidate
    except (
        GateError,
        f1.F1TransportError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        candidate_rc = 255
        result["candidate_transfer_error"] = str(exc)
    core.append_event(timeline_path, timeline, "candidate_flash_done")
    if candidate_rc == 0:
        try:
            disconnected = legacy_transport.wait_odin_absent(
                odin,
                run_dir / "live.log",
                "candidate-disconnect",
                args.disconnect_wait_sec,
            )
            result["candidate_observation"] = (
                passive_observation(args.park_wait_sec)
                if disconnected
                else {"bounded": True, "error": "Odin endpoint did not disconnect"}
            )
        except (legacy_transport.GateError, OSError, subprocess.SubprocessError) as exc:
            result["candidate_observation"] = {"bounded": True, "error": str(exc)}
    else:
        result["candidate_observation"] = {
            "bounded": True,
            "error": "candidate Odin command did not complete successfully",
        }
    core.append_event(timeline_path, timeline, "candidate_boot_ready")
    core.durable_write_json(result_path, result)
    print(
        "Candidate observation is closed. Enter physical Download mode now "
        "for mandatory Magisk rollback.",
        flush=True,
    )
    if candidate_rc != 0:
        legacy_transport.request_download_if_android()
    try:
        rollback_device, rollback_endpoint = wait_rollback_endpoint(
            root, args, run_dir, usb_binding
        )
    except (
        GateError,
        f1.F1TransportError,
        legacy_transport.GateError,
        legacy_r4w1c.GateError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        result["rollback_error"] = str(exc)
        result["verdict"] = "FAIL_R4W1C3_MANUAL_DOWNLOAD_OR_ROLLBACK_REQUIRED"
        result["timeline_phase_semantics"] = {
            "rollback_flash_start": "no rollback transfer started",
            "rollback_flash_done": "no rollback transfer completed",
            "rollback_boot_ready": "rollback Android not observed",
            "live_session_end": "recovery requires rollback-from-download mode",
        }
        core.append_remaining_events(timeline_path, timeline)
        core.durable_write_json(result_path, result)
        return 20
    core.append_event(timeline_path, timeline, "rollback_flash_start")
    try:
        rollback_target, rollback_transfer_receipt = rollback_transfer(
            root, args, rollback_device, run_dir
        )
        rollback = {
            "endpoint": rollback_endpoint,
            "target": rollback_target,
            "transfer": rollback_transfer_receipt,
        }
    except (
        GateError,
        f1.F1TransportError,
        legacy_transport.GateError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        result["rollback_transfer_error"] = str(exc)
        result["verdict"] = "FAIL_R4W1C3_ROLLBACK_TRANSFER_NOT_VERIFIED"
        core.append_event(timeline_path, timeline, "rollback_flash_done")
        core.append_event(timeline_path, timeline, "rollback_boot_ready")
        core.append_event(timeline_path, timeline, "live_session_end")
        core.durable_write_json(result_path, result)
        return 21
    core.append_event(timeline_path, timeline, "rollback_flash_done")
    try:
        rollback, rc = finish_rollback(
            root, args, run_dir, serial, usb_binding, candidate_rc, rollback
        )
    except (
        GateError,
        legacy_transport.GateError,
        legacy_r4w1c.GateError,
        connected.GateError,
        core.LiveCoreError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        result["rollback"] = rollback
        result["rollback_boot_error"] = str(exc)
        result["verdict"] = "FAIL_R4W1C3_ROLLBACK_BOOT_NOT_VERIFIED"
        core.append_event(timeline_path, timeline, "rollback_boot_ready")
        core.append_event(timeline_path, timeline, "live_session_end")
        core.durable_write_json(result_path, result)
        return 21
    result["rollback"] = rollback
    result["verdict"] = rollback["verdict"]
    core.append_event(timeline_path, timeline, "rollback_boot_ready")
    core.append_event(timeline_path, timeline, "live_session_end")
    core.durable_write_json(result_path, result)
    print(json.dumps({"run_dir": str(run_dir), "verdict": result["verdict"]}, indent=2))
    return rc


def rollback_from_download(
    root: Path,
    args: argparse.Namespace,
    artifacts: dict[str, Any],
) -> int:
    if not policy_active(root) or args.ack != ROLLBACK_ACK_TOKEN:
        raise GateError("R4W1-C3 rollback authority is inactive or unacknowledged")
    consumed = load_consumed(root)
    usb_binding = consumed.get("usb_binding")
    if not isinstance(usb_binding, dict) or not usb_binding.get("topology"):
        raise GateError("consumed state lacks USB binding")
    # The serial itself is intentionally not persisted; recovery binds the same
    # Android return by its SHA and then supplies the live serial to final checks.
    run_dir = core.allocate_run_dir(root, RUN_ROOT, "s22plus-r4w1c3-rollback", args.run_dir)
    timeline: list[dict[str, str]] = []
    timeline_path = run_dir / "timeline.json"
    result_path = run_dir / "result.json"
    core.append_event(timeline_path, timeline, "live_session_start")
    core.append_event(timeline_path, timeline, "candidate_flash_start")
    core.append_event(timeline_path, timeline, "candidate_flash_done")
    core.append_event(timeline_path, timeline, "candidate_boot_ready")
    odin = resolve(root, args.odin)
    device, endpoint = wait_bound_download(
        odin,
        run_dir / "live.log",
        str(usb_binding["topology"]),
        args.download_wait_sec,
        "recovery",
    )
    core.append_event(timeline_path, timeline, "rollback_flash_start")
    target, transfer = rollback_transfer(root, args, device, run_dir)
    core.append_event(timeline_path, timeline, "rollback_flash_done")
    if target == "magisk":
        serial, final = wait_recovery_magisk_android(args.android_wait_sec, usb_binding)
        observer = legacy_r4w1c.collect_rollback_observer(root, serial, run_dir, 1)
        verdict = "PASS_R4W1C3_MAGISK_ROLLBACK_FROM_DOWNLOAD"
        rc = 0
    else:
        final = wait_stock_android(args.android_wait_sec)
        observer = None
        verdict = "STOCK_CLEANUP_MAGISK_BASELINE_NOT_RESTORED"
        rc = 30
    no_odin_endpoint(odin, run_dir / "live.log", "recovery-final")
    core.append_event(timeline_path, timeline, "rollback_boot_ready")
    core.append_event(timeline_path, timeline, "live_session_end")
    result = {
        "schema": SCHEMA,
        "mode": "rollback-from-download",
        "target": TARGET,
        "artifacts": artifacts,
        "endpoint": endpoint,
        "rollback_target": target,
        "transfer": transfer,
        "final": final,
        "observer": observer,
        "verdict": verdict,
    }
    core.durable_write_json(result_path, result)
    print(json.dumps({"run_dir": str(run_dir), "verdict": verdict}, indent=2))
    return rc


def connected_dry_run(root: Path, args: argparse.Namespace) -> int:
    if args.ack != CONNECTED_ACK_TOKEN:
        raise GateError("R4W1-C3 connected acknowledgement mismatch")
    serial, baseline = connected.current_android_exact()
    usb_binding = legacy_r4w1c.adb_usb_binding(serial)
    no_odin_endpoint(resolve(root, args.odin), Path(os.devnull), "connected")
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "mode": "connected-read-only-dry-run",
                "target": TARGET,
                "baseline": baseline,
                "usb_binding": usb_binding,
                "device_contact": True,
                "device_writes": False,
                "reboot": False,
                "download_transition": False,
                "odin_transfer": False,
                "flash": False,
                "verdict": "PASS_R4W1C3_CONNECTED_READ_ONLY",
            },
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline-check", action="store_true")
    modes.add_argument("--render-live-plan", action="store_true")
    modes.add_argument("--connected-read-only-dry-run", action="store_true")
    modes.add_argument("--live", action="store_true")
    modes.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--ack")
    parser.add_argument("--candidate-boot", type=Path, default=connected.DEFAULT_CANDIDATE_BOOT)
    parser.add_argument("--candidate-lz4", type=Path, default=connected.DEFAULT_CANDIDATE_LZ4)
    parser.add_argument("--candidate-ap", type=Path, default=connected.DEFAULT_CANDIDATE_AP)
    parser.add_argument("--manifest", type=Path, default=connected.DEFAULT_MANIFEST)
    parser.add_argument("--static-result", type=Path, default=connected.DEFAULT_STATIC_RESULT)
    parser.add_argument("--magisk-ap", type=Path, default=connected.DEFAULT_MAGISK_AP)
    parser.add_argument("--stock-ap", type=Path, default=connected.DEFAULT_STOCK_AP)
    parser.add_argument("--full-firmware", type=Path, default=connected.DEFAULT_FULL_FIRMWARE)
    parser.add_argument("--odin", type=Path, default=connected.DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--download-wait-sec", type=int, default=DEFAULT_DOWNLOAD_WAIT_SEC)
    parser.add_argument("--disconnect-wait-sec", type=int, default=30)
    parser.add_argument("--manual-download-wait-sec", type=int, default=300)
    parser.add_argument("--android-wait-sec", type=float, default=DEFAULT_ANDROID_WAIT_SEC)
    parser.add_argument("--park-wait-sec", type=float, default=DEFAULT_PARK_WAIT_SEC)
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if not 1 <= args.download_wait_sec <= 600:
        raise GateError("Download wait must be between 1 and 600 seconds")
    if not 1 <= args.disconnect_wait_sec <= 120:
        raise GateError("disconnect wait must be between 1 and 120 seconds")
    if not 1 <= args.manual_download_wait_sec <= 900:
        raise GateError("manual Download wait must be between 1 and 900 seconds")
    if not 30 <= args.android_wait_sec <= 600:
        raise GateError("Android wait must be between 30 and 600 seconds")
    if not math.isfinite(args.park_wait_sec) or not 0 <= args.park_wait_sec <= 180:
        raise GateError("park wait must be between 0 and 180 seconds")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    try:
        validate_args(args)
        artifacts = verify_artifacts(root, args)
        policy = verify_policy_draft(root)
        if args.offline_check or args.render_live_plan:
            output = {
                "schema": SCHEMA,
                "mode": "render-live-plan" if args.render_live_plan else "offline-check",
                "target": TARGET,
                "artifacts": artifacts,
                "policy": policy,
                "transfer_command_shape": [
                    "odin4",
                    "--reboot",
                    "-a",
                    "/absolute/path/AP.tar.md5",
                    "-d",
                    "/dev/bus/usb/DDD/DDD",
                ],
                "anonymous_proc_fd_inputs": False,
                "device_contact": False,
                "device_writes": False,
                "reboot": False,
                "download_transition": False,
                "odin_transfer": False,
                "flash": False,
                "live_authorized": policy["active"],
                "verdict": "PASS_R4W1C3_REGULAR_AP_F1_HOST_ONLY",
            }
            print(json.dumps(output, indent=2))
            return 0
        if args.connected_read_only_dry_run:
            return connected_dry_run(root, args)
        if args.rollback_from_download:
            return rollback_from_download(root, args, artifacts)
        return live_run(root, args, artifacts)
    except (
        GateError,
        f1.F1TransportError,
        core.LiveCoreError,
        connected.GateError,
        legacy_transport.GateError,
        legacy_r4w1c.GateError,
        OSError,
        UnicodeError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"R4W1-C3 gate error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
