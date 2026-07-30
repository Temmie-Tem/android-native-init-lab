#!/usr/bin/env python3
"""Close an already-rolled-back A90 F1 journal after ttyACM number drift.

This helper has no transfer, reboot, recovery, payload, or partition-write
primitive.  It is usable only after the manifest-bound rollback helper has
returned zero, its exact raw log proves boot write/readback and V2321 health,
and the durable journal contains exactly one ``rollback-flashed`` record.

The original runner pins a transient ``/dev/ttyACM*`` realpath.  A later USB
enumeration can preserve the exact manifest by-id target while assigning a new
tty number.  In that narrow state this helper rebinds read-only health to the
same USB serial digest, appends the missing health/closure records, and never
reinvokes rollback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_v3403_absent_only_staging as staging  # noqa: E402
import a90_v3403_f1_orchestrator as orch  # noqa: E402
import run_d1_chroot_mvp as d1  # noqa: E402


CLOSURE_SCHEMA = "a90_f1_postrollback_realpath_closure_v1"
TTY_REALPATH_RE = re.compile(r"^/dev/ttyACM[0-9]+$")
LOOPBACK_HOST = "127.0.0.1"
MANAGED_BRIDGE_PORT = 54321
MANAGED_BRIDGE_METADATA = (
    REPO_ROOT / "workspace" / "private" / "run" / "a90_bridge.json"
).resolve()
MANAGED_BRIDGE_SCRIPT = (REVAL_DIR / "serial_tcp_bridge.py").resolve()
MANAGED_BRIDGE_VALUE_OPTIONS = (
    "--host",
    "--port",
    "--device",
    "--device-glob",
    "--capture",
    "--expect-realpath",
)
OPEN_ACTIONS = (
    "preflight",
    "approved",
    "staging-started",
    "rootfs-staged",
    "rootfs-candidate-preflight",
    "candidate-transfer-started",
    "candidate-flashed",
    "attended-window-open",
    "attended-pre-handoff-attempt",
    "candidate-boot-ready",
    "attended-pre-handoff-ready",
    "attended-handoff-started",
    "observation-no-proof",
    "rollback-transfer-started",
    "rollback-flashed",
)
ROLLBACK_PHASE_KEYS = {
    "local_image_validated",
    "native_recovery_requested",
    "recovery_endpoint_selected",
    "payload_transfer_started",
    "boot_write_started",
    "boot_write_completed",
    "readback_completed",
}
EXPECTED_ROLLBACK_PHASES = {
    "local_image_validated": True,
    "native_recovery_requested": False,
    "recovery_endpoint_selected": True,
    "payload_transfer_started": True,
    "boot_write_started": True,
    "boot_write_completed": True,
    "readback_completed": True,
}


class ClosureError(RuntimeError):
    """Raised when the no-transfer closure contract does not validate."""


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ClosureError(f"{label} must be an object")
    return value


def _helper_sha256() -> str:
    return orch.sha256_file(Path(__file__).resolve())


def require_reviewed_helper_sha256(expected: Any) -> str:
    if (
        not isinstance(expected, str)
        or staging.HEX64_RE.fullmatch(expected) is None
        or _helper_sha256() != expected
    ):
        raise ClosureError("closure helper does not match the reviewed SHA256")
    return expected


def _require_private_regular(
    path: Path,
    *,
    one_link: bool = True,
    exact_mode: int | None = None,
) -> os.stat_result:
    try:
        info = os.lstat(path)
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ClosureError(f"private evidence is unavailable: {path}") from exc
    staging.require_below(resolved, staging.PRIVATE_ROOT, "private evidence")
    if (
        not stat.S_ISREG(info.st_mode)
        or path.is_symlink()
        or resolved != path
        or info.st_mode & 0o077
        or (one_link and info.st_nlink != 1)
        or (
            exact_mode is not None
            and stat.S_IMODE(info.st_mode) != exact_mode
        )
    ):
        raise ClosureError(f"private evidence is not exact: {path}")
    return info


def _record_payload(record: dict[str, Any]) -> dict[str, Any]:
    common = {
        "schema",
        "sequence",
        "timestamp_utc",
        "run_id",
        "manifest_sha256",
        "state",
        "action",
    }
    return {key: value for key, value in record.items() if key not in common}


def validate_open_history(
    spec: orch.F1Spec,
    approval: dict[str, Any],
    transaction_dir: Path,
    records: list[dict[str, Any]],
    reviewed_helper_sha256: str,
) -> None:
    actions = tuple(orch.action_names(records))
    allowed_suffixes = (
        (),
        ("rollback-boot-ready",),
        ("rollback-boot-ready", "health-verified"),
        ("rollback-boot-ready", "health-verified", "closed"),
    )
    if not any(actions == OPEN_ACTIONS + suffix for suffix in allowed_suffixes):
        raise ClosureError("journal is not the exact post-rollback closure state")
    orch.require_consumed_approval(records, approval)
    orch.validate_attended_candidate_closure(
        spec,
        approval,
        transaction_dir,
        records,
    )

    attempt = records[8]
    candidate_ready = records[9]
    ready = records[10]
    handoff = records[11]
    observation = records[12]
    if (
        attempt.get("state") != "CANDIDATE_FLASHED"
        or attempt.get("attempt") != 1
        or attempt.get("attempt_limit") != spec.pre_handoff_attempt_limit
        or attempt.get("handoff_intent") is not False
        or attempt.get("handoff_sent") is not False
        or attempt.get("candidate_replay") is not False
        or attempt.get("rollback_required") is not True
        or candidate_ready.get("state") != "CANDIDATE_FLASHED"
        or candidate_ready.get("candidate_version") != spec.candidate_version
        or candidate_ready.get("candidate_build") != spec.candidate_build
        or candidate_ready.get("selftest_fail_zero") is not True
        or candidate_ready.get("attended_attempt") != 1
        or ready.get("state") != "CANDIDATE_FLASHED"
        or ready.get("attempt") != 1
        or ready.get("handoff_intent") is not False
        or ready.get("handoff_sent") is not False
        or ready.get("source_exact") is not True
        or ready.get("candidate_health_exact") is not True
        or handoff.get("state") != "CANDIDATE_FLASHED"
        or handoff.get("handoff_attempt") != 1
        or handoff.get("handoff_attempt_limit") != 1
        or handoff.get("handoff_argv_sha256")
        != orch.json_sha256(list(spec.handoff_command))
        or handoff.get("journal_fsync_completed_before_dispatch") is not True
        or handoff.get("candidate_replay") is not False
        or handoff.get("rollback_required") is not True
        or observation.get("state") != "OBSERVED"
        or observation.get("debian_pid1_proven") is not False
        or observation.get("candidate_replay") is not False
        or observation.get("rollback_required") is not True
        or observation.get("candidate_returned") is not False
        or observation.get("handoff_attempt_count") != 1
    ):
        raise ClosureError("attended no-proof suffix is not exact")

    observation_path = transaction_dir / "observation.json"
    _require_private_regular(observation_path)
    observed = _dict(
        json.loads(observation_path.read_text(encoding="utf-8")),
        "observation",
    )
    handoff_result = _dict(observed.get("handoff"), "observation.handoff")
    error = _dict(observed.get("error"), "observation.error")
    handoff_text = handoff_result.get("text")
    if (
        observed.get("proof") is not False
        or "candidate_return" in observed
        or handoff_result.get("proof") is not True
        or not isinstance(handoff_text, str)
        or any(marker not in handoff_text for marker in orch.OBSERVATION_OUTPUT_MARKERS)
        or error.get("type") != "RuntimeError"
        or "Debian PID1 marker timeout" not in str(error.get("message"))
    ):
        raise ClosureError("observation does not prove the exact SSH no-proof boundary")
    validate_resume_artifacts(
        spec,
        transaction_dir,
        records,
        reviewed_helper_sha256,
    )


def validate_completed_rollback(
    spec: orch.F1Spec,
    transaction_dir: Path,
    records: list[dict[str, Any]],
) -> None:
    intent = records[13]
    flashed = records[14]
    intent_keys = {
        "schema",
        "sequence",
        "timestamp_utc",
        "run_id",
        "manifest_sha256",
        "state",
        "action",
        "rollback_sha256",
        "rollback_attempt_limit",
        "rollback_process_started",
        "candidate_replay",
        "recovery_mode",
        "prior_pre_spawn_rejections",
    }
    flashed_keys = {
        "schema",
        "sequence",
        "timestamp_utc",
        "run_id",
        "manifest_sha256",
        "state",
        "action",
        "rollback_sha256",
        "rollback_transfer_count",
        "candidate_replay",
        "record",
    }
    if (
        set(intent) != intent_keys
        or intent.get("state") != "RECOVERY_ROLLBACK"
        or intent.get("rollback_sha256") != spec.rollback.sha256
        or type(intent.get("rollback_attempt_limit")) is not int
        or intent.get("rollback_attempt_limit") != 1
        or intent.get("rollback_process_started") is not None
        or intent.get("candidate_replay") is not False
        or intent.get("recovery_mode") != "adb-recovery"
        or type(intent.get("prior_pre_spawn_rejections")) is not int
        or intent.get("prior_pre_spawn_rejections") != 0
        or set(flashed) != flashed_keys
        or flashed.get("state") != "ROLLBACK_FLASHED"
        or flashed.get("rollback_sha256") != spec.rollback.sha256
        or type(flashed.get("rollback_transfer_count")) is not int
        or flashed.get("rollback_transfer_count") != 1
        or flashed.get("candidate_replay") is not False
    ):
        raise ClosureError("completed rollback journal pair is not exact")

    execution = _dict(flashed.get("record"), "rollback execution")
    execution_keys = {
        "returncode",
        "raw_log",
        "raw_log_size",
        "raw_log_sha256",
        "process_started",
        "phase_classification",
    }
    raw_log = transaction_dir / "rollback-flash.raw.log"
    info = _require_private_regular(raw_log)
    phases = _dict(execution.get("phase_classification"), "rollback phases")
    if (
        set(execution) != execution_keys
        or type(execution.get("returncode")) is not int
        or execution.get("returncode") != 0
        or execution.get("process_started") is not True
        or set(phases) != ROLLBACK_PHASE_KEYS
        or phases != EXPECTED_ROLLBACK_PHASES
        or execution.get("raw_log") != str(raw_log)
        or type(execution.get("raw_log_size")) is not int
        or execution.get("raw_log_size") != info.st_size
        or execution.get("raw_log_sha256") != orch.sha256_file(raw_log)
        or orch.classify_flash_log(raw_log) != phases
    ):
        raise ClosureError("rollback execution record lost its exact binding")
    raw_text = raw_log.read_text(encoding="utf-8", errors="strict")
    required = (
        f"local image sha256: {spec.rollback.sha256}",
        f"remote image sha256: {spec.rollback.sha256}",
        f"boot block prefix sha256: {spec.rollback.sha256}",
        "phase.native_init_flash.boot_dd_write.elapsed_sec=",
        "phase.native_init_flash.boot_readback_sha256.elapsed_sec=",
        f"version: {spec.rollback_version} build={spec.rollback_build}",
        "selftest rc=0 status=ok fail=0",
    )
    if any(token not in raw_text for token in required):
        raise ClosureError("rollback raw log lacks exact V2321 completion evidence")


def _connected_serial_digest(spec: orch.F1Spec) -> str:
    connected = orch.bound_by_label(spec.stage, "target.connected_d0_result")
    value = staging.load_bound_json(connected)
    target = _dict(value.get("target"), "connected D0 target")
    digest = target.get("usb_serial_sha256")
    staging.validate_sha256(digest, "connected D0 usb serial sha256")
    return str(digest)


def _command_option_values(argv: list[str], option: str) -> list[str]:
    values: list[str] = []
    for index, value in enumerate(argv):
        if value == option and index + 1 < len(argv):
            values.append(argv[index + 1])
        elif value.startswith(option + "="):
            values.append(value.split("=", 1)[1])
    return values


def _metadata_private_path(metadata: dict[str, Any], key: str) -> Path:
    value = metadata.get(key)
    if not isinstance(value, str) or not value:
        raise ClosureError(f"managed bridge {key} is missing")
    path = Path(value)
    if not path.is_absolute():
        path = REPO_ROOT / path
    resolved = path.resolve()
    try:
        staging.require_below(resolved, staging.PRIVATE_ROOT, f"bridge {key}")
    except staging.ContractError as exc:
        raise ClosureError(f"managed bridge {key} is outside private storage") from exc
    return resolved


def validate_exact_bridge_binding(
    bridge: dict[str, Any],
    metadata: dict[str, Any],
    process_argv: list[str],
    spec: orch.F1Spec,
    current_realpath: str,
) -> None:
    metadata_pid = metadata.get("pid")
    processes = bridge.get("processes")
    port_processes = (
        [
            process
            for process in processes
            if isinstance(process, dict) and process.get("port_match") is True
        ]
        if isinstance(processes, list)
        else []
    )
    sockets = bridge.get("port_sockets")
    metadata_command = metadata.get("command")
    option_names = process_argv[2::2]
    capture_values = _command_option_values(process_argv, "--capture")
    capture_path = (
        Path(capture_values[0]).resolve()
        if len(capture_values) == 1
        else Path("/")
    )
    metadata_capture = _metadata_private_path(metadata, "capture_path")
    if (
        bridge.get("wrapper_contract") != 1
        or bridge.get("listen_host") != LOOPBACK_HOST
        or bridge.get("listen_port") != MANAGED_BRIDGE_PORT
        or bridge.get("ambiguous") is not False
        or bridge.get("selected_device") != spec.stage.bridge_device
        or bridge.get("selected_realpath") != current_realpath
        or bridge.get("bridge_process") != "running"
        or bridge.get("port_listening") is not True
        or bridge.get("port_pid_source") != "fd"
        or type(metadata_pid) is not int
        or metadata_pid <= 0
        or bridge.get("port_pids") != [metadata_pid]
        or not isinstance(sockets, list)
        or len(sockets) != 1
        or not isinstance(sockets[0], dict)
        or sockets[0].get("address") != LOOPBACK_HOST
        or sockets[0].get("port") != MANAGED_BRIDGE_PORT
        or len(port_processes) != 1
        or port_processes[0].get("pid") != metadata_pid
        or port_processes[0].get("managed") is not True
        or metadata.get("wrapper_contract") != 1
        or metadata.get("host") != LOOPBACK_HOST
        or metadata.get("port") != MANAGED_BRIDGE_PORT
        or metadata.get("device") != spec.stage.bridge_device
        or metadata.get("pin_selected_realpath") is not False
        or metadata.get("effective_expect_realpath") != current_realpath
        or not isinstance(metadata_command, list)
        or not all(isinstance(value, str) for value in metadata_command)
        or process_argv != metadata_command
        or len(process_argv) != 2 + 2 * len(MANAGED_BRIDGE_VALUE_OPTIONS)
        or tuple(option_names) != MANAGED_BRIDGE_VALUE_OPTIONS
        or Path(process_argv[0]).resolve() != Path(sys.executable).resolve()
        or Path(process_argv[1]).resolve() != MANAGED_BRIDGE_SCRIPT
        or _command_option_values(process_argv, "--host") != [LOOPBACK_HOST]
        or _command_option_values(process_argv, "--port")
        != [str(MANAGED_BRIDGE_PORT)]
        or _command_option_values(process_argv, "--device")
        != [spec.stage.bridge_device]
        or _command_option_values(process_argv, "--expect-realpath")
        != [current_realpath]
        or capture_path != metadata_capture
    ):
        raise ClosureError(
            "listener is not the exact managed bridge for the drifted A90 tty"
        )


def validate_current_target(spec: orch.F1Spec) -> dict[str, Any]:
    current_realpath = os.path.realpath(spec.stage.bridge_device)
    if (
        TTY_REALPATH_RE.fullmatch(current_realpath) is None
        or current_realpath == spec.stage.bridge_realpath
    ):
        raise ClosureError("closure requires exact by-id continuity with tty realpath drift")
    parent = staging._usb_device_parent(  # noqa: SLF001 - same reviewed target logic
        staging.SYS_CLASS_TTY / Path(current_realpath).name
    )
    if parent is None:
        raise ClosureError("current tty has no USB device parent")
    vendor = staging._read_sysfs_text(parent / "idVendor").lower()  # noqa: SLF001
    product = staging._read_sysfs_text(parent / "idProduct").lower()  # noqa: SLF001
    serial = staging._read_sysfs_text(parent / "serial")  # noqa: SLF001
    if (
        vendor != staging.HOST_NCM_VENDOR_ID
        or product != staging.HOST_NCM_PRODUCT_ID
        or not serial
        or hashlib.sha256(serial.encode("utf-8")).hexdigest()
        != _connected_serial_digest(spec)
    ):
        raise ClosureError("current tty is not the manifest-bound A90 USB identity")

    command = [
        sys.executable,
        str(REVAL_DIR / "a90_bridge.py"),
        "preflight",
        "--host",
        LOOPBACK_HOST,
        "--port",
        str(MANAGED_BRIDGE_PORT),
        "--device",
        spec.stage.bridge_device,
        "--expect-realpath",
        current_realpath,
        "--no-client-probe",
        "--json",
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30.0,
        check=False,
    )
    if completed.returncode != 0:
        raise ClosureError("current exact bridge preflight failed")
    try:
        bridge = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ClosureError("current bridge preflight returned invalid JSON") from exc
    _require_private_regular(MANAGED_BRIDGE_METADATA, exact_mode=0o600)
    try:
        metadata = _dict(
            json.loads(MANAGED_BRIDGE_METADATA.read_text(encoding="utf-8")),
            "managed bridge metadata",
        )
    except json.JSONDecodeError as exc:
        raise ClosureError("managed bridge metadata is invalid") from exc
    if bridge.get("metadata") != metadata:
        raise ClosureError("bridge preflight metadata changed during validation")
    metadata_pid = metadata.get("pid")
    if type(metadata_pid) is not int:
        raise ClosureError("managed bridge metadata PID is invalid")
    try:
        raw_cmdline = (Path("/proc") / str(metadata_pid) / "cmdline").read_bytes()
    except OSError as exc:
        raise ClosureError("managed bridge process is unavailable") from exc
    process_argv = [
        part.decode("utf-8", errors="strict")
        for part in raw_cmdline.split(b"\0")
        if part
    ]
    validate_exact_bridge_binding(
        bridge,
        metadata,
        process_argv,
        spec,
        current_realpath,
    )
    _require_private_regular(
        _metadata_private_path(metadata, "capture_path"),
        exact_mode=0o600,
    )
    _require_private_regular(
        _metadata_private_path(metadata, "stderr_log"),
        exact_mode=0o600,
    )
    return {
        "exact_bridge_device": spec.stage.bridge_device,
        "manifest_realpath": spec.stage.bridge_realpath,
        "current_realpath": current_realpath,
        "usb_serial_sha256": hashlib.sha256(serial.encode("utf-8")).hexdigest(),
        "realpath_drift_only": True,
    }


def read_exact_v2321_health(
    spec: orch.F1Spec,
    target: dict[str, Any],
    *,
    timeout: float,
    reviewed_helper_sha256: str,
) -> dict[str, Any]:
    results: dict[str, dict[str, Any]] = {}
    for label, argv in (
        ("version", ["version"]),
        ("status", ["status"]),
        ("selftest", ["selftest"]),
    ):
        result = d1.run_cmd(
            LOOPBACK_HOST,
            MANAGED_BRIDGE_PORT,
            timeout,
            argv,
            input_mode=orch.F1_SERIAL_INPUT_MODE,
            input_char_delay_sec=orch.F1_SERIAL_INPUT_CHAR_DELAY_SEC,
        )
        if result.get("rc") != 0 or result.get("status") != "ok":
            raise ClosureError(f"{label} is not an exact successful framed read")
        results[label] = result
    version_text = str(results["version"].get("text") or "")
    status_text = str(results["status"].get("text") or "")
    selftest_text = str(results["selftest"].get("text") or "")
    if (
        f"version: {spec.rollback_version} build={spec.rollback_build}"
        not in version_text
        or orch.PSTORE_ZERO_RE.search(status_text) is None
        or "fail=0" not in selftest_text
    ):
        raise ClosureError("current A90 health is not exact V2321 fail=0 pstore=0")
    return {
        **target,
        "version": spec.rollback_version,
        "build": spec.rollback_build,
        "selftest_fail_zero": True,
        "pstore_entries_zero": True,
        "framed_response_sha256": {
            label: hashlib.sha256(
                str(result.get("text") or "").encode("utf-8")
            ).hexdigest()
            for label, result in results.items()
        },
        "device_write": False,
        "flash": False,
        "payload_sent": False,
        "reboot_requested": False,
        "rollback_reinvoked": False,
        "candidate_replay": False,
        "closure_helper_sha256": reviewed_helper_sha256,
    }


def _rollback_ready_payload(spec: orch.F1Spec, health: dict[str, Any]) -> dict[str, Any]:
    return {
        "rollback_version": spec.rollback_version,
        "rollback_build": spec.rollback_build,
        "selftest_fail_zero": True,
        "pstore_entries_zero": True,
        "recovered_from_dynamic_realpath": True,
        "rollback_reinvoked": False,
        "candidate_replay": False,
        "manifest_realpath": health["manifest_realpath"],
        "current_realpath": health["current_realpath"],
        "closure_helper_sha256": health["closure_helper_sha256"],
    }


def validate_health_payload(
    spec: orch.F1Spec,
    health: dict[str, Any],
    reviewed_helper_sha256: str,
) -> None:
    expected_keys = {
        "exact_bridge_device",
        "manifest_realpath",
        "current_realpath",
        "usb_serial_sha256",
        "realpath_drift_only",
        "version",
        "build",
        "selftest_fail_zero",
        "pstore_entries_zero",
        "framed_response_sha256",
        "device_write",
        "flash",
        "payload_sent",
        "reboot_requested",
        "rollback_reinvoked",
        "candidate_replay",
        "closure_helper_sha256",
    }
    framed = health.get("framed_response_sha256")
    if (
        set(health) != expected_keys
        or health.get("exact_bridge_device") != spec.stage.bridge_device
        or health.get("manifest_realpath") != spec.stage.bridge_realpath
        or TTY_REALPATH_RE.fullmatch(str(health.get("current_realpath"))) is None
        or health.get("current_realpath") == spec.stage.bridge_realpath
        or not isinstance(health.get("usb_serial_sha256"), str)
        or health.get("usb_serial_sha256") != _connected_serial_digest(spec)
        or health.get("realpath_drift_only") is not True
        or health.get("version") != spec.rollback_version
        or health.get("build") != spec.rollback_build
        or health.get("selftest_fail_zero") is not True
        or health.get("pstore_entries_zero") is not True
        or not isinstance(framed, dict)
        or set(framed) != {"version", "status", "selftest"}
        or any(
            not isinstance(value, str)
            or staging.HEX64_RE.fullmatch(value) is None
            for value in framed.values()
        )
        or any(
            health.get(name) is not False
            for name in (
                "device_write",
                "flash",
                "payload_sent",
                "reboot_requested",
                "rollback_reinvoked",
                "candidate_replay",
            )
        )
        or health.get("closure_helper_sha256") != reviewed_helper_sha256
    ):
        raise ClosureError("health-verified payload is not exact")


def validate_rollback_ready_payload(
    spec: orch.F1Spec,
    payload: dict[str, Any],
    reviewed_helper_sha256: str,
) -> None:
    expected_keys = {
        "rollback_version",
        "rollback_build",
        "selftest_fail_zero",
        "pstore_entries_zero",
        "recovered_from_dynamic_realpath",
        "rollback_reinvoked",
        "candidate_replay",
        "manifest_realpath",
        "current_realpath",
        "closure_helper_sha256",
    }
    if (
        set(payload) != expected_keys
        or payload.get("rollback_version") != spec.rollback_version
        or payload.get("rollback_build") != spec.rollback_build
        or payload.get("selftest_fail_zero") is not True
        or payload.get("pstore_entries_zero") is not True
        or payload.get("recovered_from_dynamic_realpath") is not True
        or payload.get("rollback_reinvoked") is not False
        or payload.get("candidate_replay") is not False
        or payload.get("manifest_realpath") != spec.stage.bridge_realpath
        or TTY_REALPATH_RE.fullmatch(str(payload.get("current_realpath"))) is None
        or payload.get("current_realpath") == spec.stage.bridge_realpath
        or payload.get("closure_helper_sha256") != reviewed_helper_sha256
    ):
        raise ClosureError("rollback-boot-ready payload is not exact")


def _result(spec: orch.F1Spec) -> dict[str, Any]:
    return {
        "schema": orch.ORCHESTRATOR_SCHEMA,
        "run_id": spec.stage.run_id,
        "status": "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK",
        "manifest_sha256": spec.stage.manifest_sha256,
        "candidate_transfer_count": 1,
        "candidate_transfer_uncertain": False,
        "candidate_replay": False,
        "debian_pid1_proven": False,
        "rollback_transfer_count": 1,
        "final_health_restored": True,
        "timeline_events": list(orch.CANONICAL_EVENTS),
    }


def _validate_existing_payload(
    records: list[dict[str, Any]],
    action: str,
    expected: dict[str, Any],
) -> bool:
    matches = [record for record in records if record.get("action") == action]
    if not matches:
        return False
    if len(matches) != 1 or _record_payload(matches[0]) != expected:
        raise ClosureError(f"existing {action} record is not exact")
    return True


def validate_resume_artifacts(
    spec: orch.F1Spec,
    transaction_dir: Path,
    records: list[dict[str, Any]],
    reviewed_helper_sha256: str,
) -> None:
    actions = tuple(orch.action_names(records))
    suffix = actions[len(OPEN_ACTIONS):]
    rollback_ready_records = [
        record for record in records if record.get("action") == "rollback-boot-ready"
    ]
    health_records = [
        record for record in records if record.get("action") == "health-verified"
    ]
    closed_records = [
        record for record in records if record.get("action") == "closed"
    ]
    if len(rollback_ready_records) > 1 or len(health_records) > 1 or len(closed_records) > 1:
        raise ClosureError("post-rollback resume records are duplicated")

    rollback_ready: dict[str, Any] | None = None
    health: dict[str, Any] | None = None
    if rollback_ready_records:
        rollback_ready = _record_payload(rollback_ready_records[0])
        validate_rollback_ready_payload(
            spec,
            rollback_ready,
            reviewed_helper_sha256,
        )
    if health_records:
        health = _record_payload(health_records[0])
        validate_health_payload(spec, health, reviewed_helper_sha256)
        if rollback_ready != _rollback_ready_payload(spec, health):
            raise ClosureError("resume health does not match rollback-boot-ready")
    if closed_records and _record_payload(closed_records[0]) != _result(spec):
        raise ClosureError("existing closed record is not exact")

    result_path = transaction_dir / "result.json"
    if result_path.is_symlink():
        raise ClosureError("existing result.json is a symlink")
    result_exists = result_path.exists()
    if result_exists:
        _require_private_regular(result_path)
        if health is None:
            raise ClosureError("result.json exists before health verification")
        try:
            result_value = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ClosureError("existing result.json is invalid") from exc
        if result_value != _result(spec):
            raise ClosureError("existing result.json is not exact")
    if suffix == ("rollback-boot-ready", "health-verified", "closed") and not result_exists:
        raise ClosureError("closed journal lacks exact result.json")

    timeline_path = transaction_dir / "timeline.json"
    _require_private_regular(timeline_path)
    try:
        events = orch.load_timeline(transaction_dir)
    except (orch.ContractError, json.JSONDecodeError) as exc:
        raise ClosureError("existing timeline is invalid") from exc
    names = [event["name"] for event in events]
    timestamps = [event["timestamp_utc"] for event in events]
    if (
        any(not orch.is_canonical_utc_timestamp(value) for value in timestamps)
        or timestamps != sorted(timestamps)
    ):
        raise ClosureError("existing timeline timestamps are not exact")
    if suffix in ((), ("rollback-boot-ready",)):
        allowed_lengths = (6,)
    elif suffix == ("rollback-boot-ready", "health-verified"):
        allowed_lengths = (6, 7)
    else:
        allowed_lengths = (7, 8)
    if not any(
        names == list(orch.CANONICAL_EVENTS[:length])
        for length in allowed_lengths
    ):
        raise ClosureError("existing timeline is not an exact resumable prefix")
    for event in events:
        event_name = event["name"]
        source_actions = orch.JOURNAL_EVENT_ACTIONS[event_name]
        source = next(
            (
                record
                for record in records
                if record.get("action") in source_actions
            ),
            None,
        )
        if source is None:
            if event_name == "live_session_end" and not closed_records:
                continue
            raise ClosureError("timeline event lacks its journal source")
        if event["timestamp_utc"] != source.get("timestamp_utc"):
            raise ClosureError("timeline timestamp does not match its journal source")
    if result_exists and names != list(orch.CANONICAL_EVENTS[:7]):
        if not (
            suffix == ("rollback-boot-ready", "health-verified", "closed")
            and names == list(orch.CANONICAL_EVENTS)
        ):
            raise ClosureError("result.json exists before the resumable timeline")


def close_without_transfer(
    spec: orch.F1Spec,
    transaction_dir: Path,
    records: list[dict[str, Any]],
    health: dict[str, Any],
    reviewed_helper_sha256: str,
) -> dict[str, Any]:
    require_reviewed_helper_sha256(reviewed_helper_sha256)
    journal_dir = transaction_dir / "journal"
    rollback_ready = _rollback_ready_payload(spec, health)
    if not _validate_existing_payload(records, "rollback-boot-ready", rollback_ready):
        require_reviewed_helper_sha256(reviewed_helper_sha256)
        orch.append_record(
            journal_dir,
            "ROLLBACK_FLASHED",
            "rollback-boot-ready",
            rollback_ready,
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        records = orch.read_journal(spec, transaction_dir)
    if not _validate_existing_payload(records, "health-verified", health):
        require_reviewed_helper_sha256(reviewed_helper_sha256)
        orch.append_record(
            journal_dir,
            "HEALTH_VERIFIED",
            "health-verified",
            health,
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        records = orch.read_journal(spec, transaction_dir)

    require_reviewed_helper_sha256(reviewed_helper_sha256)
    events = orch.repair_timeline_from_journal(transaction_dir, records)
    has_closed = any(record.get("action") == "closed" for record in records)
    expected_names = (
        list(orch.CANONICAL_EVENTS)
        if has_closed
        else list(orch.CANONICAL_EVENTS[:7])
    )
    if [event.get("name") for event in events] != expected_names:
        raise ClosureError("closure cannot produce the canonical seven-event prefix")

    result = _result(spec)
    result_path = transaction_dir / "result.json"
    if result_path.exists():
        _require_private_regular(result_path)
        if json.loads(result_path.read_text(encoding="utf-8")) != result:
            raise ClosureError("existing result.json is not exact")
    else:
        require_reviewed_helper_sha256(reviewed_helper_sha256)
        orch.write_private_json_exclusive(result_path, result)

    records = orch.read_journal(spec, transaction_dir)
    closed = [record for record in records if record.get("action") == "closed"]
    if not closed:
        require_reviewed_helper_sha256(reviewed_helper_sha256)
        orch.append_record(
            journal_dir,
            "CLOSED",
            "closed",
            result,
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
    elif len(closed) != 1 or _record_payload(closed[0]) != result:
        raise ClosureError("existing closed record is not exact")
    records = orch.read_journal(spec, transaction_dir)
    require_reviewed_helper_sha256(reviewed_helper_sha256)
    events = orch.repair_timeline_from_journal(transaction_dir, records)
    if [event.get("name") for event in events] != list(orch.CANONICAL_EVENTS):
        raise ClosureError("closure cannot produce the canonical eight-event timeline")
    return result


def load_exact_state(
    manifest_path: Path,
    manifest_sha256: str,
    transaction_dir: Path,
    reviewed_helper_sha256: str,
) -> tuple[orch.F1Spec, dict[str, Any], list[dict[str, Any]]]:
    spec, issues = orch.load_spec(
        manifest_path,
        manifest_sha256,
        allow_draft=False,
    )
    if issues:
        raise ClosureError(f"manifest has {len(issues)} contract issues")
    orch.verify_local_closure(spec)
    exact_transaction = orch.exact_transaction_dir(spec, transaction_dir)
    approval = orch.load_approval_prepared(spec)
    records = orch.read_journal(spec, exact_transaction)
    validate_open_history(
        spec,
        approval,
        exact_transaction,
        records,
        reviewed_helper_sha256,
    )
    validate_completed_rollback(spec, exact_transaction, records)
    return spec, approval, records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expect-manifest-sha256", required=True)
    parser.add_argument("--expect-reviewed-helper-sha256", required=True)
    parser.add_argument("--transaction-dir", type=Path, required=True)
    parser.add_argument("--execute-closure", action="store_true")
    parser.add_argument("--read-timeout", type=float, default=30.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    reviewed_helper_sha256 = require_reviewed_helper_sha256(
        args.expect_reviewed_helper_sha256
    )
    spec, _, records = load_exact_state(
        args.manifest,
        args.expect_manifest_sha256,
        args.transaction_dir,
        reviewed_helper_sha256,
    )
    transaction_dir = orch.exact_transaction_dir(spec, args.transaction_dir)
    if not args.execute_closure:
        result = {
            "schema": CLOSURE_SCHEMA,
            "mode": "host-only-offline-inspection",
            "run_id": spec.stage.run_id,
            "manifest_sha256": spec.stage.manifest_sha256,
            "closure_helper_sha256": reviewed_helper_sha256,
            "journal_actions": orch.action_names(records),
            "rollback_transfer_count": 1,
            "rollback_reinvoked": False,
            "candidate_replay": False,
            "device_contact": False,
            "device_write": False,
            "ready_for_exact_d0_closure": True,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    actions = orch.action_names(records)
    existing_health = [
        record for record in records if record.get("action") == "health-verified"
    ]
    if existing_health:
        health = _record_payload(existing_health[0])
    else:
        require_reviewed_helper_sha256(reviewed_helper_sha256)
        target = validate_current_target(spec)
        health = read_exact_v2321_health(
            spec,
            target,
            timeout=args.read_timeout,
            reviewed_helper_sha256=reviewed_helper_sha256,
        )
    validate_health_payload(spec, health, reviewed_helper_sha256)
    require_reviewed_helper_sha256(reviewed_helper_sha256)
    result = close_without_transfer(
        spec,
        transaction_dir,
        records,
        health,
        reviewed_helper_sha256,
    )
    output = {
        **result,
        "closure_helper_sha256": reviewed_helper_sha256,
        "rollback_reinvoked": False,
        "device_write": False,
        "starting_actions": actions,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - concise fail-closed CLI
        print(f"a90-postrollback-closure: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
