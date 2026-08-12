#!/usr/bin/env python3
"""Exact-target routine setup and mode-control actions for SM-G986N/y2q."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import time
from typing import Any, Callable

import s20plus_g986n_d0_inventory as base
import s20plus_g986n_routine_d0 as routine


VERSION = "s20plus-g986n-routine-actions-v1"
EXPECTED_MODEL = "SM-G986N"
EXPECTED_DEVICE = "y2q"
EXPECTED_PRODUCT = "y2qksx"
EXPECTED_INCREMENTAL = "G986NKSS8IYC2"
DEFAULT_RUN_ROOT = Path("workspace/private/runs/s20plus-g986n-routine-actions")
ACTIVE_GUARD_NAME = "active-action.json"
MAX_OUTPUT_BYTES = 64 * 1024
MAX_COMMAND_TIMEOUT = 4 * 60 * 60
MIN_STAGE_FREE_BYTES = 20 * 1024 * 1024 * 1024

MAGISK_PACKAGE = "com.topjohnwu.magisk"
MAGISK_APK_REL = Path("workspace/private/tools/magisk/v30.7/Magisk-v30.7.apk")
MAGISK_APK_SIZE = 11_613_864
MAGISK_APK_SHA256 = "e0d32d2123532860f97123d927b1bb86c4e08e6fd8a48bfc6b5bee0afae9ebd5"

AP_NAME = (
    "AP_G986NKSS8IYC2_G986NKSS8IYC2_MQB93855401_REV00_"
    "user_low_ship_MULTI_CERT_meta_OS13.tar.md5"
)
AP_REL = Path(
    "workspace/private/inputs/s20plus_g986n/G986NKSS8IYC2_KTC/extracted"
) / AP_NAME
AP_SIZE = 8_799_989_882
AP_SHA256 = "460a414ca8ba0d9fb64aa53de0fc1c1cc87ae75f0d79a1a1496e478bafa08753"
AP_STAGE_DIR_NAME = f"Codex-S20Plus-IYC2-{AP_SHA256[:12]}"
AP_STAGE_DIR = f"/sdcard/Download/{AP_STAGE_DIR_NAME}"
AP_REMOTE = f"{AP_STAGE_DIR}/{AP_NAME}"

ACTIONS = (
    "install-magisk",
    "stage-ap",
    "reboot-system",
    "enter-download",
    "enter-recovery",
)
CONTROL_ACTIONS = frozenset(("reboot-system", "enter-download", "enter-recovery"))
CONTROL_RESOLUTIONS = {
    "reboot-system-returned-normal": "reboot-system",
    "download-observed": "enter-download",
    "download-returned-normal": "enter-download",
    "recovery-observed": "enter-recovery",
    "recovery-returned-normal": "enter-recovery",
}
CONTROL_VERDICTS = {
    "reboot-system": "DISPATCHED_S20PLUS_G986N_REBOOT_HEALTH_PENDING",
    "enter-download": "DISPATCHED_S20PLUS_G986N_DOWNLOAD_ENTRY_PENDING",
    "enter-recovery": "DISPATCHED_S20PLUS_G986N_RECOVERY_ENTRY_PENDING",
}


class RoutineActionError(RuntimeError):
    pass


Command = Callable[[list[str], float, int], tuple[int, bytes, bytes]]


class Recorder:
    def __init__(self, command: Command, before_effect: Callable[[str, int], None] | None = None):
        self.command = command
        self.before_effect = before_effect
        self.host_command_count = 0
        self.inventory_command_count = 0
        self.selected_target_command_count = 0
        self.effect_command_count = 0
        self.labels: list[str] = []

    def run(
        self,
        argv: list[str],
        timeout: float,
        maximum: int,
        *,
        label: str,
        effect: bool = False,
    ) -> tuple[int, bytes, bytes]:
        self.host_command_count += 1
        self.labels.append(label)
        if argv[-2:] == ["devices", "-l"]:
            self.inventory_command_count += 1
        if "-s" in argv:
            self.selected_target_command_count += 1
        if effect:
            if self.before_effect is not None:
                self.before_effect(label, self.effect_command_count + 1)
            self.effect_command_count += 1
        return self.command(argv, timeout, maximum)

    def evidence(self) -> dict[str, Any]:
        return {
            "host_command_count": self.host_command_count,
            "inventory_command_count": self.inventory_command_count,
            "selected_target_command_count": self.selected_target_command_count,
            "effect_command_count": self.effect_command_count,
            "command_labels": list(self.labels),
            "other_target_command_count": 0,
            "s22plus_command_count": 0,
            "a90_command_count": 0,
        }


def bounded_command(
    argv: list[str], timeout: float, maximum: int
) -> tuple[int, bytes, bytes]:
    if (
        not argv
        or not 0.1 <= timeout <= MAX_COMMAND_TIMEOUT
        or not 1 <= maximum <= MAX_OUTPUT_BYTES
    ):
        raise RoutineActionError("invalid command bound")
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as error:
        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=error,
            close_fds=True,
        )
        deadline = time.monotonic() + timeout
        while process.poll() is None:
            if output.tell() + error.tell() > maximum:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
                raise RoutineActionError("command output exceeded its bound")
            if time.monotonic() >= deadline:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
                raise RoutineActionError("command timed out")
            time.sleep(0.05)
        output.seek(0)
        error.seek(0)
        stdout = output.read(maximum + 1)
        stderr = error.read(maximum + 1)
    if len(stdout) + len(stderr) > maximum:
        raise RoutineActionError("command output exceeded its bound")
    return process.returncode, stdout, stderr


def decode(
    result: tuple[int, bytes, bytes], label: str, *, permit_stderr: bool = False
) -> tuple[str, str]:
    returncode, stdout, stderr = result
    if returncode != 0:
        raise RoutineActionError(f"{label} failed with rc={returncode}")
    if stderr and not permit_stderr:
        raise RoutineActionError(f"{label} produced stderr")
    try:
        return stdout.decode("utf-8", "strict").strip(), stderr.decode(
            "utf-8", "strict"
        ).strip()
    except UnicodeDecodeError as exc:
        raise RoutineActionError(f"{label} output is not UTF-8") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_artifact(
    root: Path, relative: Path, expected_size: int, expected_sha256: str
) -> dict[str, Any]:
    expected_path = (root / relative).absolute()
    try:
        metadata = expected_path.lstat()
    except OSError as exc:
        raise RoutineActionError("bound artifact is unavailable") from exc
    if not stat.S_ISREG(metadata.st_mode) or expected_path.is_symlink():
        raise RoutineActionError("bound artifact is not a regular non-symlink file")
    if metadata.st_size != expected_size:
        raise RoutineActionError("bound artifact size mismatch")
    resolved = expected_path.resolve(strict=True)
    if resolved != expected_path:
        raise RoutineActionError("bound artifact path changed through resolution")
    actual_sha256 = sha256_file(resolved)
    if actual_sha256 != expected_sha256:
        raise RoutineActionError("bound artifact SHA-256 mismatch")
    return {
        "path": str(resolved),
        "size": expected_size,
        "sha256": expected_sha256,
    }


def action_artifact(action: str, root: Path) -> dict[str, Any] | None:
    if action == "install-magisk":
        return require_artifact(
            root, MAGISK_APK_REL, MAGISK_APK_SIZE, MAGISK_APK_SHA256
        )
    if action == "stage-ap":
        return require_artifact(root, AP_REL, AP_SIZE, AP_SHA256)
    return None


def preflight(recorder: Recorder, exact_adb: str) -> dict[str, Any]:
    inventory, _ = decode(
        recorder.run(
            [exact_adb, "devices", "-l"],
            10,
            MAX_OUTPUT_BYTES,
            label="initial-inventory",
        ),
        "initial inventory",
    )
    try:
        rows = base.parse_inventory(inventory)
        selected = routine.select_exact_target(rows)
    except (base.InventoryError, routine.RoutineD0Error) as exc:
        raise RoutineActionError("initial target identity is not exact") from exc
    serial = selected["serial"]
    devpath, _ = decode(
        recorder.run(
            [exact_adb, "-s", serial, "get-devpath"],
            10,
            MAX_OUTPUT_BYTES,
            label="target-devpath",
        ),
        "target devpath",
    )
    if base.DEVPATH_RE.fullmatch(devpath) is None:
        raise RoutineActionError("selected target USB topology is malformed")
    snapshot_text, _ = decode(
        recorder.run(
            [exact_adb, "-s", serial, "exec-out", "sh", "-c", base.REMOTE_SNAPSHOT],
            20,
            MAX_OUTPUT_BYTES,
            label="target-health",
        ),
        "target health",
    )
    try:
        values = base.parse_snapshot(snapshot_text)
        base.validate_snapshot_binding(values, selected)
    except base.InventoryError as exc:
        raise RoutineActionError("preflight snapshot is not exact") from exc
    expected = {
        "model": EXPECTED_MODEL,
        "device": EXPECTED_DEVICE,
        "product_name": EXPECTED_PRODUCT,
        "incremental": EXPECTED_INCREMENTAL,
        "boot_completed": "1",
        "bootanim": "stopped",
        "selinux": "Enforcing",
    }
    for key, value in expected.items():
        if values.get(key) != value:
            raise RoutineActionError(f"preflight health mismatch: {key}")
    return {
        "serial": serial,
        "serial_sha256": base.sha256_text(serial),
        "devpath": devpath,
        "usb_topology_sha256": base.sha256_text(devpath),
        "boot_id_sha256": base.sha256_text(values["boot_id"]),
        "inventory": routine.sanitized_inventory(rows),
    }


def final_normal_check(
    recorder: Recorder, exact_adb: str, target: dict[str, Any]
) -> None:
    inventory, _ = decode(
        recorder.run(
            [exact_adb, "devices", "-l"],
            10,
            MAX_OUTPUT_BYTES,
            label="final-inventory",
        ),
        "final inventory",
    )
    rows = base.parse_inventory(inventory)
    selected = routine.select_exact_target(rows)
    if (
        selected["serial"] != target["serial"]
        or routine.sanitized_inventory(rows) != target["inventory"]
    ):
        raise RoutineActionError("target or inventory changed during action")


def parse_available_bytes(output: str) -> int:
    lines = [line.split() for line in output.splitlines() if line.strip()]
    if len(lines) < 2 or len(lines[-1]) < 5:
        raise RoutineActionError("df output is malformed")
    try:
        available_kib = int(lines[-1][-3])
    except ValueError as exc:
        raise RoutineActionError("df available space is not numeric") from exc
    if available_kib < 0:
        raise RoutineActionError("df available space is negative")
    return available_kib * 1024


def parse_remote_sha256(output: str, expected_path: str) -> str:
    fields = output.split()
    if len(fields) != 2 or fields[1] != expected_path:
        raise RoutineActionError("remote SHA-256 output is malformed")
    value = fields[0].lower()
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise RoutineActionError("remote SHA-256 value is malformed")
    return value


def run_action(
    action: str,
    *,
    root: Path,
    command: Command = bounded_command,
    recorder: Recorder | None = None,
    artifact: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Recorder]:
    if action not in ACTIONS:
        raise RoutineActionError("action is not allowlisted")
    receipt = base.tool_receipt(base.DEFAULT_ADB)
    exact_adb = receipt["path"]
    expected_artifact = action_artifact(action, root) if artifact is None else artifact
    expected_binding = {
        "install-magisk": (MAGISK_APK_SIZE, MAGISK_APK_SHA256),
        "stage-ap": (AP_SIZE, AP_SHA256),
    }.get(action)
    if expected_binding is None:
        if expected_artifact is not None:
            raise RoutineActionError("control action unexpectedly has an artifact")
    elif (
        expected_artifact is None
        or expected_artifact.get("size") != expected_binding[0]
        or expected_artifact.get("sha256") != expected_binding[1]
        or not isinstance(expected_artifact.get("path"), str)
    ):
        raise RoutineActionError("prepared artifact binding is invalid")
    artifact = expected_artifact

    recorder = recorder or Recorder(command)
    target = preflight(recorder, exact_adb)
    serial = target["serial"]
    effect = {
        "device_write": False,
        "package_install": False,
        "user_storage_stage": False,
        "reboot_requested": False,
        "mode_transition_requested": False,
        "partition_access": False,
        "flash_requested": False,
    }
    verification: dict[str, Any] = {}

    if action == "install-magisk":
        assert artifact is not None
        stdout, stderr = decode(
            recorder.run(
                [
                    exact_adb,
                    "-s",
                    serial,
                    "install",
                    "--no-streaming",
                    "-r",
                    artifact["path"],
                ],
                300,
                MAX_OUTPUT_BYTES,
                label="install-magisk",
                effect=True,
            ),
            "Magisk install",
            permit_stderr=True,
        )
        if "Success" not in (stdout + "\n" + stderr).splitlines():
            raise RoutineActionError("package manager did not report exact success")
        package_path, _ = decode(
            recorder.run(
                [exact_adb, "-s", serial, "shell", "pm", "path", MAGISK_PACKAGE],
                20,
                MAX_OUTPUT_BYTES,
                label="verify-magisk-package",
            ),
            "Magisk package verification",
        )
        if not package_path.startswith(f"package:/data/app/") or not package_path.endswith(
            ".apk"
        ):
            raise RoutineActionError("installed package path is unexpected")
        effect.update(device_write=True, package_install=True)
        verification = {"package": MAGISK_PACKAGE, "installed": True}
        final_normal_check(recorder, exact_adb, target)
        verdict = "PASS_S20PLUS_G986N_MAGISK_APK_INSTALLED"
    elif action == "stage-ap":
        assert artifact is not None
        df_text, _ = decode(
            recorder.run(
                [
                    exact_adb,
                    "-s",
                    serial,
                    "shell",
                    "toybox",
                    "df",
                    "-k",
                    "/sdcard/Download",
                ],
                20,
                MAX_OUTPUT_BYTES,
                label="stage-free-space",
            ),
            "stage free-space check",
        )
        available_bytes = parse_available_bytes(df_text)
        if available_bytes < MIN_STAGE_FREE_BYTES:
            raise RoutineActionError("insufficient shared-storage space")
        decode(
            recorder.run(
                [exact_adb, "-s", serial, "shell", "mkdir", AP_STAGE_DIR],
                20,
                MAX_OUTPUT_BYTES,
                label="claim-stage-directory",
                effect=True,
            ),
            "atomic stage-directory claim",
        )
        decode(
            recorder.run(
                [
                    exact_adb,
                    "-s",
                    serial,
                    "push",
                    "-Z",
                    artifact["path"],
                    AP_REMOTE,
                ],
                MAX_COMMAND_TIMEOUT,
                MAX_OUTPUT_BYTES,
                label="stage-ap-bytes",
                effect=True,
            ),
            "AP staging transfer",
            permit_stderr=True,
        )
        final_hash_text, _ = decode(
            recorder.run(
                [
                    exact_adb,
                    "-s",
                    serial,
                    "shell",
                    "toybox",
                    "sha256sum",
                    AP_REMOTE,
                ],
                MAX_COMMAND_TIMEOUT,
                MAX_OUTPUT_BYTES,
                label="verify-staged-ap",
            ),
            "staged AP verification",
        )
        if parse_remote_sha256(final_hash_text, AP_REMOTE) != AP_SHA256:
            raise RoutineActionError("staged AP SHA-256 mismatch")
        effect.update(device_write=True, user_storage_stage=True)
        verification = {
            "remote_name": AP_NAME,
            "remote_directory": AP_STAGE_DIR_NAME,
            "size": AP_SIZE,
            "sha256": AP_SHA256,
            "available_bytes_before": available_bytes,
            "inactive_shared_storage_only": True,
        }
        final_normal_check(recorder, exact_adb, target)
        verdict = "PASS_S20PLUS_G986N_AP_STAGED_VERIFIED"
    else:
        reboot_argument = {
            "reboot-system": None,
            "enter-download": "download",
            "enter-recovery": "recovery",
        }[action]
        argv = [exact_adb, "-s", serial, "reboot"]
        if reboot_argument is not None:
            argv.append(reboot_argument)
        decode(
            recorder.run(
                argv,
                20,
                MAX_OUTPUT_BYTES,
                label=action,
                effect=True,
            ),
            action,
        )
        effect["reboot_requested"] = True
        effect["mode_transition_requested"] = action != "reboot-system"
        verification = {
            "dispatch_confirmed": True,
            "terminal_health_pending": True,
            "replay_permitted": False,
            "operator_attendance_required": True,
        }
        verdict = CONTROL_VERDICTS[action]

    if base.tool_receipt(Path(exact_adb)) != receipt:
        raise RoutineActionError("ADB tool changed during action")
    if action in ("install-magisk", "stage-ap"):
        post_artifact = action_artifact(action, root)
        if post_artifact != artifact:
            raise RoutineActionError("bound artifact changed during action")
    public_target = {
        "model": EXPECTED_MODEL,
        "device": EXPECTED_DEVICE,
        "product": EXPECTED_PRODUCT,
        "incremental": EXPECTED_INCREMENTAL,
        "adb_serial_sha256": target["serial_sha256"],
        "usb_topology_sha256": target["usb_topology_sha256"],
        "pre_action_boot_id_sha256": target["boot_id_sha256"],
    }
    return (
        {
            "schema": "s20plus_g986n_routine_action_result_v1",
            "version": VERSION,
            "action": action,
            "target": public_target,
            "artifact": None
            if artifact is None
            else {"size": artifact["size"], "sha256": artifact["sha256"]},
            "verification": verification,
            "effect": effect,
            "host_tool": receipt,
            **recorder.evidence(),
            "d1_authorized": True,
            "f1_authorized": False,
            "verdict": verdict,
        },
        recorder,
    )


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def allocate_run_dir(root: Path, action: str, requested: Path | None) -> Path:
    base_dir = (root / DEFAULT_RUN_ROOT).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    candidate = requested or base_dir / (
        action
        + "-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + f"-{time.time_ns()}"
    )
    candidate = candidate if candidate.is_absolute() else root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base_dir)
    except ValueError as exc:
        raise RoutineActionError("run directory is outside the private action root") from exc
    resolved.mkdir(mode=0o700)
    _fsync_dir(resolved.parent)
    return resolved


def guard_path(root: Path) -> Path:
    return (root / DEFAULT_RUN_ROOT / ACTIVE_GUARD_NAME).resolve()


def acquire_guard(
    root: Path,
    run_dir: Path,
    action: str,
    artifact: dict[str, Any] | None,
) -> Path:
    path = guard_path(root)
    payload = {
        "schema": "s20plus_g986n_active_routine_action_v1",
        "version": VERSION,
        "action": action,
        "run_dir": str(run_dir.resolve()),
        "expected_target": {
            "model": EXPECTED_MODEL,
            "device": EXPECTED_DEVICE,
            "product": EXPECTED_PRODUCT,
            "incremental": EXPECTED_INCREMENTAL,
        },
        "artifact": None
        if artifact is None
        else {"size": artifact["size"], "sha256": artifact["sha256"]},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "unresolved": True,
    }
    try:
        base.durable_write(path, payload)
    except FileExistsError as exc:
        raise RoutineActionError("an unresolved routine action already exists") from exc
    return path


def read_guard(root: Path) -> dict[str, Any]:
    path = guard_path(root)
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
            raise RoutineActionError("active action guard is not a regular file")
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RoutineActionError("active action guard is unreadable") from exc
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != "s20plus_g986n_active_routine_action_v1"
        or payload.get("version") != VERSION
        or payload.get("action") not in ACTIONS
        or payload.get("unresolved") is not True
        or not isinstance(payload.get("run_dir"), str)
    ):
        raise RoutineActionError("active action guard is malformed")
    run_dir = Path(payload["run_dir"]).resolve()
    try:
        run_dir.relative_to((root / DEFAULT_RUN_ROOT).resolve())
    except ValueError as exc:
        raise RoutineActionError("active action run directory is outside its root") from exc
    if not run_dir.is_dir():
        raise RoutineActionError("active action run directory is unavailable")
    return payload


def release_guard(root: Path, *, expected_run_dir: Path, expected_action: str) -> None:
    payload = read_guard(root)
    if (
        payload["action"] != expected_action
        or Path(payload["run_dir"]).resolve() != expected_run_dir.resolve()
    ):
        raise RoutineActionError("active action guard binding changed")
    path = guard_path(root)
    path.unlink()
    _fsync_dir(path.parent)


def resolve_control(root: Path, resolution: str) -> Path:
    expected_action = CONTROL_RESOLUTIONS.get(resolution)
    if expected_action is None:
        raise RoutineActionError("control resolution is not allowlisted")
    payload = read_guard(root)
    if payload["action"] != expected_action:
        raise RoutineActionError("control resolution does not match the active action")
    run_dir = Path(payload["run_dir"]).resolve()
    effect_events = sorted(run_dir.glob("effect-*.json"))
    result_path = run_dir / "result.json"
    if effect_events != [run_dir / "effect-01.json"] or not result_path.is_file():
        raise RoutineActionError("active control has no durable dispatch evidence")
    try:
        effect = json.loads(effect_events[0].read_text(encoding="utf-8"))
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RoutineActionError("active control evidence is unreadable") from exc
    if (
        not isinstance(effect, dict)
        or effect.get("schema") != "s20plus_g986n_routine_effect_intent_v1"
        or effect.get("version") != VERSION
        or effect.get("action") != expected_action
        or effect.get("label") != expected_action
        or effect.get("ordinal") != 1
    ):
        raise RoutineActionError("active control effect evidence is not exact")
    if (
        not isinstance(result, dict)
        or result.get("schema") != "s20plus_g986n_routine_action_result_v1"
        or result.get("version") != VERSION
        or result.get("action") != expected_action
        or result.get("verdict") != CONTROL_VERDICTS[expected_action]
        or result.get("effect_command_count") != 1
        or result.get("verification", {}).get("terminal_health_pending") is not True
        or result.get("verification", {}).get("replay_permitted") is not False
    ):
        raise RoutineActionError("active control result is not resolvable")
    resolution_path = run_dir / "resolution.json"
    base.durable_write(
        resolution_path,
        {
            "schema": "s20plus_g986n_control_resolution_v1",
            "version": VERSION,
            "action": expected_action,
            "resolution": resolution,
            "operator_observation_required": True,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    release_guard(root, expected_run_dir=run_dir, expected_action=expected_action)
    return resolution_path


def close_guard_after_result(
    root: Path, *, run_dir: Path, action: str
) -> bool:
    if action in CONTROL_ACTIONS:
        return False
    release_guard(root, expected_run_dir=run_dir, expected_action=action)
    return True


def close_guard_after_failure(
    root: Path, *, run_dir: Path, action: str, effect_command_count: int
) -> bool:
    if effect_command_count != 0:
        return False
    release_guard(root, expected_run_dir=run_dir, expected_action=action)
    return True


def failure_result(action: str, recorder: Recorder, exc: Exception) -> dict[str, Any]:
    signature = f"{type(exc).__name__}:{exc}"
    possible_effect = recorder.effect_command_count > 0
    return {
        "schema": "s20plus_g986n_routine_action_failure_v1",
        "version": VERSION,
        "action": action,
        "failure_class": type(exc).__name__,
        "failure_signature_sha256": hashlib.sha256(signature.encode()).hexdigest(),
        **recorder.evidence(),
        "possible_effect": possible_effect,
        "possible_package_install": possible_effect and action == "install-magisk",
        "possible_user_storage_stage": possible_effect and action == "stage-ap",
        "possible_reboot_or_mode_dispatch": possible_effect and action in CONTROL_ACTIONS,
        "automatic_retry_permitted": False,
        "f1_authorized": False,
        "verdict": "FAIL_S20PLUS_G986N_ROUTINE_ACTION_CLOSED",
    }


def dry_run_plan(action: str) -> dict[str, Any]:
    if action not in ACTIONS:
        raise RoutineActionError("action is not allowlisted")
    artifact = None
    if action == "install-magisk":
        artifact = {"size": MAGISK_APK_SIZE, "sha256": MAGISK_APK_SHA256}
    elif action == "stage-ap":
        artifact = {"size": AP_SIZE, "sha256": AP_SHA256, "remote_name": AP_NAME}
    return {
        "schema": "s20plus_g986n_routine_action_plan_v1",
        "version": VERSION,
        "mode": "dry-run-device-hidden",
        "action": action,
        "expected_target": f"{EXPECTED_MODEL}/{EXPECTED_DEVICE}/{EXPECTED_INCREMENTAL}",
        "artifact": artifact,
        "partition_access": False,
        "flash_requested": False,
        "root_used": False,
        "other_target_command_count": 0,
        "live_authorized": False,
    }


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--action", choices=ACTIONS)
    mode.add_argument("--resolve-control", choices=tuple(CONTROL_RESOLUTIONS))
    parser.add_argument("--connected", action="store_true")
    parser.add_argument("--apply-resolution", action="store_true")
    parser.add_argument("--run-dir", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.resolve_control is not None:
        if args.connected or args.run_dir is not None:
            print("FAIL_S20PLUS_G986N_CONTROL_RESOLUTION_ARGUMENTS")
            return 1
        if not args.apply_resolution:
            print(
                json.dumps(
                    {
                        "schema": "s20plus_g986n_control_resolution_plan_v1",
                        "version": VERSION,
                        "mode": "host-only-dry-run",
                        "resolution": args.resolve_control,
                        "operator_observation_required": True,
                        "will_contact_device": False,
                        "live_authorized": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        try:
            path = resolve_control(repo_root(), args.resolve_control)
        except Exception:
            print("FAIL_S20PLUS_G986N_CONTROL_RESOLUTION_CLOSED")
            return 1
        print("PASS_S20PLUS_G986N_CONTROL_RESOLVED")
        print(f"resolution={path}")
        return 0
    if args.apply_resolution:
        print("FAIL_S20PLUS_G986N_ROUTINE_ACTION_ARGUMENTS")
        return 1
    assert args.action is not None
    if not args.connected:
        print(json.dumps(dry_run_plan(args.action), indent=2, sort_keys=True))
        return 0
    try:
        artifact = action_artifact(args.action, repo_root())
    except Exception:
        print("FAIL_S20PLUS_G986N_ROUTINE_ACTION_HOST_PREFLIGHT")
        return 1
    run_dir = allocate_run_dir(repo_root(), args.action, args.run_dir)
    try:
        acquire_guard(repo_root(), run_dir, args.action, artifact)
    except Exception:
        print("FAIL_S20PLUS_G986N_ROUTINE_ACTION_UNRESOLVED_GUARD")
        return 1
    base.durable_write(
        run_dir / "intent.json",
        {
            "schema": "s20plus_g986n_routine_action_intent_v1",
            "version": VERSION,
            "action": args.action,
            "expected_target": {
                "model": EXPECTED_MODEL,
                "device": EXPECTED_DEVICE,
                "product": EXPECTED_PRODUCT,
                "incremental": EXPECTED_INCREMENTAL,
            },
            "artifact": None
            if artifact is None
            else {"size": artifact["size"], "sha256": artifact["sha256"]},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "no_automatic_retry": True,
        },
    )
    def before_effect(label: str, ordinal: int) -> None:
        base.durable_write(
            run_dir / f"effect-{ordinal:02d}.json",
            {
                "schema": "s20plus_g986n_routine_effect_intent_v1",
                "version": VERSION,
                "action": args.action,
                "label": label,
                "ordinal": ordinal,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    recorder = Recorder(bounded_command, before_effect=before_effect)
    try:
        result, recorder = run_action(
            args.action,
            root=repo_root(),
            command=recorder.command,
            recorder=recorder,
            artifact=artifact,
        )
        base.durable_write(run_dir / "result.json", result)
        close_guard_after_result(
            repo_root(), run_dir=run_dir, action=args.action
        )
    except Exception as exc:
        base.durable_write(run_dir / "failure.json", failure_result(args.action, recorder, exc))
        close_guard_after_failure(
            repo_root(),
            run_dir=run_dir,
            action=args.action,
            effect_command_count=recorder.effect_command_count,
        )
        print("FAIL_S20PLUS_G986N_ROUTINE_ACTION_CLOSED")
        print(f"failure={run_dir / 'failure.json'}")
        return 1
    print(result["verdict"])
    print(f"result={run_dir / 'result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
