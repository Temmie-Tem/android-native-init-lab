#!/usr/bin/env python3
"""One-use attended S20+ fastboot-boot support probe with a known-good boot."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
from typing import Any, Callable

import s20plus_g986n_fastboot_getvar_census as census


VERSION = "s20plus-g986n-fastboot-boot-support-f1-v1"
LIVE_ACTIVE = True
APPROVAL_PREFIX = "S20PLUS-G986N-FASTBOOT-BOOT-SUPPORT-F1-APPROVE:"

ROOT = Path(__file__).resolve().parents[5]
RUN_ROOT = ROOT / "workspace/private/runs/s20plus-g986n-fastboot-boot-support-f1"
SHARED_GUARD = (
    ROOT / "workspace/private/runs/s20plus-g986n-routine-actions/active-action.json"
)
CONSUMED = RUN_ROOT / "consumed-boot-intent.json"

CENSUS_SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_fastboot_getvar_census.py"
)
CENSUS_SOURCE_SIZE = 38_587
CENSUS_SOURCE_SHA256 = (
    "80ab93f7e2091a5db0cedfd8d46fb2df9afaf36ceab9ca70bca6b762f535d39e"
)
RAW_CAPTURE_SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/device_action_raw_capture_v1.py"
)
RAW_CAPTURE_SOURCE_SIZE = 25_006
RAW_CAPTURE_SOURCE_SHA256 = (
    "410e260129c0c50dca29b008dc7cf1051ee007816ab18bea76aeae62505ca0e4"
)
D0_INVENTORY_SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/s20plus_g986n_d0_inventory.py"
)
D0_INVENTORY_SOURCE_SIZE = 21_474
D0_INVENTORY_SOURCE_SHA256 = (
    "3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81"
)
ROUTINE_D0_SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/s20plus_g986n_routine_d0.py"
)
ROUTINE_D0_SOURCE_SIZE = 12_649
ROUTINE_D0_SOURCE_SHA256 = (
    "2377e463e1ec4869fd9ba7a5155aeb6c792bdb5b5b969c902a2b0e5a00fda77c"
)

BOOT_IMAGE = ROOT / (
    "workspace/private/outputs/s20plus_g986n/"
    "boot_recovery_canary_b0_v1/rollback/boot.img"
)
BOOT_IMAGE_SIZE = 67_108_864
BOOT_IMAGE_SHA256 = (
    "d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc"
)

P0_RUN = ROOT / (
    "workspace/private/runs/s20plus-g986n-p0-pid1-odin-f1/"
    "run-1788344115316596479"
)
P0_TERMINAL = P0_RUN / "terminal.json"
P0_TERMINAL_SIZE = 607
P0_TERMINAL_SHA256 = (
    "67a291732731e244a942b376779f4c493a8f8e61ccbee764bb84625994362005"
)
P0_FINAL_HEALTH = P0_RUN / "final-health.json"
P0_FINAL_HEALTH_SIZE = 1_384
P0_FINAL_HEALTH_SHA256 = (
    "797d02ac2513720648cbf3e6663bc5a615ad575ef832e4b914bbc782d3d273aa"
)
P0_ROLLBACK_RESULT = P0_RUN / "rollback-result.json"
P0_ROLLBACK_RESULT_SIZE = 1_910
P0_ROLLBACK_RESULT_SHA256 = (
    "42fa97fa826b3170c710550c610fd857ff6db9acb3c4306748ceb7e6249b8b40"
)

CENSUS_RUN = ROOT / (
    "workspace/private/runs/s20plus-g986n-fastboot-getvar-census/"
    "census-20260902T151105Z-1788361865846027780"
)
CENSUS_PROBE = CENSUS_RUN / "probe-result.json"
CENSUS_PROBE_SIZE = 3_907
CENSUS_PROBE_SHA256 = (
    "1369b7a29b2ba7c5589be0cee89a1f09a865c344d0a6dce9c99967f5e2177ba8"
)
CENSUS_FINAL = CENSUS_RUN / "final-result.json"
CENSUS_FINAL_SIZE = 1_538
CENSUS_FINAL_SHA256 = (
    "d9a0d858ee8030274f91deba3fbb2a5bedc667b93732dc43cafa451fb5a6184a"
)

PASS_SUPPORTED = "PASS_S20PLUS_G986N_FASTBOOT_BOOT_SUPPORTED_RETURN_HEALTHY"
PASS_UNSUPPORTED = "PASS_S20PLUS_G986N_FASTBOOT_BOOT_UNSUPPORTED_RETURN_HEALTHY"
NO_PROOF = "NO_PROOF_S20PLUS_G986N_FASTBOOT_BOOT_RETURNED_HEALTHY"
MAX_OUTPUT = 32 * 1024


class SupportProbeError(RuntimeError):
    pass


class ReturnRequiredError(SupportProbeError):
    pass


Command = Callable[[list[str], float, int], tuple[int, bytes, bytes]]
UsbInventory = Callable[[], tuple[dict[str, Any], ...]]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _lexists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _local_sha256(path: Path) -> str:
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise SupportProbeError("hashed input is not a direct regular file")
        digest = hashlib.sha256()
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = os.lstat(path)
    identity = lambda value: (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )
    if identity(before) != identity(after) or identity(after) != identity(current):
        raise SupportProbeError("hashed input changed while reading")
    return digest.hexdigest()


def _exact_file(
    path: Path,
    size: int,
    digest: str,
    label: str,
    *,
    private_mode: bool,
) -> dict[str, Any]:
    try:
        before = path.lstat()
    except OSError as exc:
        raise SupportProbeError(f"{label} is unavailable") from exc
    if (
        path.is_symlink()
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or path.resolve(strict=True) != path
        or before.st_size != size
        or (private_mode and stat.S_IMODE(before.st_mode) != 0o400)
        or _local_sha256(path) != digest
    ):
        raise SupportProbeError(f"{label} identity differs")
    after = path.lstat()
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise SupportProbeError(f"{label} changed while reading")
    return {"path": str(path), "size": size, "sha256": digest}


def static_closure(root: Path = ROOT) -> dict[str, Any]:
    if root != ROOT:
        raise SupportProbeError("support probe root differs")
    if Path(census.__file__).resolve(strict=True) != CENSUS_SOURCE:
        raise SupportProbeError("census resolved module path differs")
    source = _exact_file(
        CENSUS_SOURCE,
        CENSUS_SOURCE_SIZE,
        CENSUS_SOURCE_SHA256,
        "census source",
        private_mode=False,
    )
    dependency_specs = (
        (
            "raw_capture_source",
            RAW_CAPTURE_SOURCE,
            RAW_CAPTURE_SOURCE_SIZE,
            RAW_CAPTURE_SOURCE_SHA256,
            census.raw_capture,
        ),
        (
            "d0_inventory_source",
            D0_INVENTORY_SOURCE,
            D0_INVENTORY_SOURCE_SIZE,
            D0_INVENTORY_SOURCE_SHA256,
            census.base,
        ),
        (
            "routine_d0_source",
            ROUTINE_D0_SOURCE,
            ROUTINE_D0_SOURCE_SIZE,
            ROUTINE_D0_SOURCE_SHA256,
            census.routine,
        ),
    )
    dependencies: dict[str, dict[str, Any]] = {}
    for name, path, size, digest, module in dependency_specs:
        if Path(module.__file__).resolve(strict=True) != path:
            raise SupportProbeError(f"{name} resolved module path differs")
        dependencies[name] = _exact_file(
            path, size, digest, name, private_mode=False
        )
    boot = _exact_file(
        BOOT_IMAGE,
        BOOT_IMAGE_SIZE,
        BOOT_IMAGE_SHA256,
        "resident boot image",
        private_mode=True,
    )
    p0_terminal_receipt = _exact_file(
        P0_TERMINAL,
        P0_TERMINAL_SIZE,
        P0_TERMINAL_SHA256,
        "P0 terminal",
        private_mode=True,
    )
    p0_health_receipt = _exact_file(
        P0_FINAL_HEALTH,
        P0_FINAL_HEALTH_SIZE,
        P0_FINAL_HEALTH_SHA256,
        "P0 final health",
        private_mode=True,
    )
    p0_rollback_receipt = _exact_file(
        P0_ROLLBACK_RESULT,
        P0_ROLLBACK_RESULT_SIZE,
        P0_ROLLBACK_RESULT_SHA256,
        "P0 rollback result",
        private_mode=True,
    )
    census_probe_receipt = _exact_file(
        CENSUS_PROBE,
        CENSUS_PROBE_SIZE,
        CENSUS_PROBE_SHA256,
        "fastboot census probe",
        private_mode=True,
    )
    census_final_receipt = _exact_file(
        CENSUS_FINAL,
        CENSUS_FINAL_SIZE,
        CENSUS_FINAL_SHA256,
        "fastboot census terminal",
        private_mode=True,
    )

    p0_terminal = census.load_json(P0_TERMINAL, "P0 terminal")
    p0_health = census.load_json(P0_FINAL_HEALTH, "P0 final health")
    p0_rollback = census.load_json(P0_ROLLBACK_RESULT, "P0 rollback result")
    prior_probe = census.load_json(CENSUS_PROBE, "fastboot census probe")
    prior_final = census.load_json(CENSUS_FINAL, "fastboot census terminal")
    expected_target = {
        "model": census.EXPECTED_MODEL,
        "device": census.EXPECTED_DEVICE,
        "product_name": census.EXPECTED_PRODUCT,
        "incremental": census.EXPECTED_INCREMENTAL,
    }
    if (
        p0_terminal.get("verdict") != "NO_PROOF_P0_RETURNED_RESIDENT_HEALTHY"
        or p0_terminal.get("candidate_attempts") != 1
        or p0_terminal.get("rollback_attempts") != 1
        or p0_terminal.get("rollback_transfer_completed") is not True
        or p0_terminal.get("rollback_replay_permitted") is not False
        or p0_health.get("resident_boot_healthy") is not True
        or p0_health.get("rollback_outcome_proved") is not True
        or p0_health.get("health", {}).get("target") != {
            "model": census.EXPECTED_MODEL,
            "device": census.EXPECTED_DEVICE,
            "product": census.EXPECTED_PRODUCT,
            "incremental": census.EXPECTED_INCREMENTAL,
        }
        or p0_rollback.get("kind") != "rollback"
        or p0_rollback.get("classification") != "odin_transfer_completed"
        or p0_rollback.get("receipt", {}).get("ap", {}).get("sha256")
        != "1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2"
        or prior_probe.get("verdict")
        != census.RETURN_PENDING
        or prior_probe.get("fastboot_command_count") != 4
        or prior_probe.get("getvar_order") != list(census.GETVARS)
        or prior_final.get("verdict") != census.FINAL_PASS
        or prior_final.get("fastboot_query_intent_count") != 4
        or prior_final.get("all_four_queries_completed") is not True
        or prior_final.get("fastboot_endpoint_absent_before_health") is not True
        or prior_final.get("target", {}).get("model") != expected_target["model"]
    ):
        raise SupportProbeError("support-probe predecessor evidence differs")
    values = {
        item.get("variable"): item.get("value")
        for item in prior_probe.get("getvars", [])
    }
    if values.get("product") != "kona" or values.get("is-userspace") != "no":
        raise SupportProbeError("classic-fastboot census values differ")
    return {
        "census_source": source,
        **dependencies,
        "boot_image": boot,
        "p0_terminal": p0_terminal_receipt,
        "p0_final_health": p0_health_receipt,
        "p0_rollback_result": p0_rollback_receipt,
        "fastboot_census_probe": census_probe_receipt,
        "fastboot_census_terminal": census_final_receipt,
    }


def validate_runtime_sources(prepared: dict[str, Any]) -> None:
    specs = (
        (
            "census_source",
            CENSUS_SOURCE,
            CENSUS_SOURCE_SIZE,
            CENSUS_SOURCE_SHA256,
            census,
        ),
        (
            "raw_capture_source",
            RAW_CAPTURE_SOURCE,
            RAW_CAPTURE_SOURCE_SIZE,
            RAW_CAPTURE_SOURCE_SHA256,
            census.raw_capture,
        ),
        (
            "d0_inventory_source",
            D0_INVENTORY_SOURCE,
            D0_INVENTORY_SOURCE_SIZE,
            D0_INVENTORY_SOURCE_SHA256,
            census.base,
        ),
        (
            "routine_d0_source",
            ROUTINE_D0_SOURCE,
            ROUTINE_D0_SOURCE_SIZE,
            ROUTINE_D0_SOURCE_SHA256,
            census.routine,
        ),
    )
    expected = prepared.get("binding", {}).get("predecessors", {})
    for name, path, size, digest, module in specs:
        if Path(module.__file__).resolve(strict=True) != path:
            raise SupportProbeError(f"{name} finalizer module path differs")
        current = _exact_file(path, size, digest, name, private_mode=False)
        if expected.get(name) != current:
            raise SupportProbeError(f"{name} finalizer receipt differs")


def allocate_run_dir() -> Path:
    RUN_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    run_dir = RUN_ROOT / (
        "probe-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + f"-{time.time_ns()}"
    )
    run_dir.mkdir(mode=0o700)
    _fsync_dir(RUN_ROOT)
    return run_dir


def _bound_run(value: dict[str, Any]) -> Path:
    raw = value.get("run_dir")
    if not isinstance(raw, str):
        raise SupportProbeError("journal has no run directory")
    path = Path(raw)
    try:
        path.relative_to(RUN_ROOT)
    except ValueError as exc:
        raise SupportProbeError("run directory is outside support-probe root") from exc
    if not path.is_absolute() or path.is_symlink() or not path.is_dir() or path.resolve() != path:
        raise SupportProbeError("run directory is unavailable or indirect")
    return path


def acquire_guard(run_dir: Path) -> None:
    SHARED_GUARD.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        census.base.durable_write(
            SHARED_GUARD,
            {
                "schema": "s20plus_g986n_fastboot_boot_support_guard_v1",
                "version": VERSION,
                "run_dir": str(run_dir),
                "unresolved": True,
                "at": now(),
            },
        )
    except FileExistsError as exc:
        raise SupportProbeError("an unresolved shared S20+ action exists") from exc


def read_guard() -> tuple[dict[str, Any], Path]:
    value = census.load_json(SHARED_GUARD, "support-probe guard")
    run_dir = _bound_run(value)
    if (
        value.get("schema") != "s20plus_g986n_fastboot_boot_support_guard_v1"
        or value.get("version") != VERSION
        or value.get("unresolved") is not True
    ):
        raise SupportProbeError("support-probe guard differs")
    return value, run_dir


def release_guard(run_dir: Path) -> None:
    _value, bound = read_guard()
    if bound != run_dir:
        raise SupportProbeError("support-probe guard run differs")
    SHARED_GUARD.unlink()
    _fsync_dir(SHARED_GUARD.parent)


def prepared_binding(
    run_dir: Path,
    health: dict[str, Any],
    closure: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_fastboot_boot_support_binding_v1",
        "version": VERSION,
        "run_dir_sha256": census.base.sha256_text(str(run_dir)),
        "target": {
            "model": census.EXPECTED_MODEL,
            "device": census.EXPECTED_DEVICE,
            "product": census.EXPECTED_PRODUCT,
            "incremental": census.EXPECTED_INCREMENTAL,
            "serial_sha256": health["serial_sha256"],
            "topology_sha256": health["topology_sha256"],
            "boot_id_sha256": health["boot_id_sha256"],
            "other_serial_sha256": health["other_serial_sha256"],
        },
        "boot_image": closure["boot_image"],
        "adb": health["adb"],
        "fastboot": census.require_fastboot(ROOT),
        "predecessors": closure,
        "command_shape": ["fastboot", "-s", "BOUND_SERIAL", "boot", "BOUND_BOOT_IMAGE"],
        "physical_recovery": "power-cycle-or-START-to-persistent-resident-boot",
        "attempt": 1,
        "no_replay": True,
    }


def prepare() -> tuple[Path, str]:
    if not LIVE_ACTIVE:
        raise SupportProbeError("live support probe is not active")
    if CONSUMED.exists() or CONSUMED.is_symlink():
        raise SupportProbeError("fastboot-boot support probe is already consumed")
    closure = static_closure()
    run_dir = allocate_run_dir()
    acquire_guard(run_dir)
    try:
        command = census.RawCommand(run_dir, "prepare")
        health = census.collect_android_health(command, census.real_usb_inventory)
        if static_closure() != closure:
            raise SupportProbeError("static closure changed during prepare")
        binding = prepared_binding(run_dir, health, closure)
        approval = APPROVAL_PREFIX + census.object_sha256(binding)
        prepared = {
            "schema": "s20plus_g986n_fastboot_boot_support_prepared_v1",
            "version": VERSION,
            "binding": binding,
            "binding_sha256": census.object_sha256(binding),
            "approval": approval,
            "health": health["health"],
            "persistent_device_writes": False,
            "partition_writes": 0,
            "persistent_mutation": False,
            "partition_access": False,
            "at": now(),
        }
        census.base.durable_write(run_dir / "prepared.json", prepared)
        return run_dir, approval
    except Exception:
        if _lexists(SHARED_GUARD):
            release_guard(run_dir)
        raise


def validate_prepared_at(run_dir: Path) -> dict[str, Any]:
    prepared = census.load_json(run_dir / "prepared.json", "prepared support probe")
    binding = prepared.get("binding")
    if (
        set(prepared)
        != {
            "schema",
            "version",
            "binding",
            "binding_sha256",
            "approval",
            "health",
            "persistent_device_writes",
            "partition_writes",
            "persistent_mutation",
            "partition_access",
            "at",
        }
        or prepared.get("schema")
        != "s20plus_g986n_fastboot_boot_support_prepared_v1"
        or prepared.get("version") != VERSION
        or not isinstance(binding, dict)
        or set(binding)
        != {
            "schema",
            "version",
            "run_dir_sha256",
            "target",
            "boot_image",
            "adb",
            "fastboot",
            "predecessors",
            "command_shape",
            "physical_recovery",
            "attempt",
            "no_replay",
        }
        or prepared.get("binding_sha256") != census.object_sha256(binding)
        or prepared.get("approval") != APPROVAL_PREFIX + census.object_sha256(binding)
        or binding.get("schema")
        != "s20plus_g986n_fastboot_boot_support_binding_v1"
        or binding.get("version") != VERSION
        or binding.get("run_dir_sha256")
        != census.base.sha256_text(str(run_dir))
        or binding.get("boot_image", {}).get("sha256") != BOOT_IMAGE_SHA256
        or not isinstance(binding.get("adb"), dict)
        or binding.get("command_shape")
        != ["fastboot", "-s", "BOUND_SERIAL", "boot", "BOUND_BOOT_IMAGE"]
        or binding.get("attempt") != 1
        or binding.get("no_replay") is not True
        or prepared.get("persistent_device_writes") is not False
        or prepared.get("partition_writes") != 0
        or prepared.get("persistent_mutation") is not False
        or prepared.get("partition_access") is not False
        or not isinstance(prepared.get("at"), str)
    ):
        raise SupportProbeError("prepared support-probe binding differs")
    return prepared


def load_prepared() -> tuple[Path, dict[str, Any]]:
    _guard, run_dir = read_guard()
    prepared = validate_prepared_at(run_dir)
    return run_dir, prepared


def abort_pre_entry() -> Path:
    _guard, run_dir = read_guard()
    if CONSUMED.exists() or CONSUMED.is_symlink():
        raise SupportProbeError("support probe is already consumed")
    if any(
        _lexists(run_dir / name)
        for name in (
            "entry-observed.json",
            "boot-intent.json",
            "boot-result.json",
            "final-result.json",
        )
    ):
        raise SupportProbeError("pre-entry abort found possible effect evidence")
    prepared_path = run_dir / "prepared.json"
    prepared_present = _lexists(prepared_path)
    prepared = validate_prepared_at(run_dir) if prepared_present else None
    binding_sha256 = None if prepared is None else prepared["binding_sha256"]
    path = run_dir / "pre-entry-abort.json"
    if _lexists(path):
        value = census.load_json(path, "pre-entry abort")
        if (
            set(value)
            != {
                "schema",
                "version",
                "binding_sha256",
                "prepared_present",
                "entry_intent_absent",
                "boot_intent_absent",
                "fastboot_boot_attempts",
                "device_effects",
                "at",
            }
            or value.get("schema")
            != "s20plus_g986n_fastboot_boot_support_pre_entry_abort_v1"
            or value.get("version") != VERSION
            or value.get("binding_sha256") != binding_sha256
            or value.get("prepared_present") is not prepared_present
            or value.get("entry_intent_absent") is not True
            or value.get("boot_intent_absent") is not True
            or type(value.get("fastboot_boot_attempts")) is not int
            or value.get("fastboot_boot_attempts") != 0
            or type(value.get("device_effects")) is not int
            or value.get("device_effects") != 0
            or not isinstance(value.get("at"), str)
            or not value["at"]
        ):
            raise SupportProbeError("pre-entry abort receipt differs")
    else:
        census.base.durable_write(
            path,
            {
                "schema": "s20plus_g986n_fastboot_boot_support_pre_entry_abort_v1",
                "version": VERSION,
                "binding_sha256": binding_sha256,
                "prepared_present": prepared_present,
                "entry_intent_absent": True,
                "boot_intent_absent": True,
                "fastboot_boot_attempts": 0,
                "device_effects": 0,
                "at": now(),
            },
        )
    release_guard(run_dir)
    return path


def create_entry_intent(run_dir: Path, prepared: dict[str, Any]) -> None:
    census.base.durable_write(
        CONSUMED,
        {
            "schema": "s20plus_g986n_fastboot_boot_support_entry_intent_v1",
            "version": VERSION,
            "run_dir": str(run_dir),
            "binding_sha256": prepared["binding_sha256"],
            "operator_action": "select Magisk bootloader reboot",
            "host_transition_command": None,
            "attempt": 1,
            "no_replay": True,
            "at": now(),
        },
    )


def classify_boot(
    result: tuple[int, bytes, bytes],
    private_values: tuple[str, ...],
) -> dict[str, Any]:
    returncode, stdout, stderr = result
    try:
        output = (stdout + stderr).decode("utf-8", "strict")
    except UnicodeError as exc:
        raise SupportProbeError("fastboot boot output is not UTF-8") from exc
    if len(stdout) + len(stderr) > MAX_OUTPUT:
        raise SupportProbeError("fastboot boot output exceeds its combined bound")
    for value in private_values:
        output = output.replace(value, "<PRIVATE_REDACTED>")
    output = output.strip()
    if len(output.encode()) > MAX_OUTPUT:
        raise SupportProbeError("redacted fastboot boot output exceeds its bound")
    lowered = output.lower()
    booting_okay = re.search(r"(?im)^Booting\s+OKAY\b", output) is not None
    contradictory = (
        "fastboot: error" in lowered
        or re.search(r"(?i)\bfailed\b", output) is not None
        or re.search(r"(?im)^error(?:\s|:)", output) is not None
    )
    remote_failure_lines = [
        line.lower()
        for line in output.splitlines()
        if re.fullmatch(
            r"(?:booting\s+)?failed \(remote:.*\)",
            line.lower(),
        )
    ]
    if (
        returncode == 0
        and booting_okay
        and not contradictory
    ):
        status = "COMMAND_ACCEPTED"
    elif (
        returncode != 0
        and not booting_okay
        and len(remote_failure_lines) == 1
        and any(
            marker in line
            for line in remote_failure_lines
            for marker in (
                "unknown command",
                "not supported",
                "unrecognized command",
                "not implemented",
            )
        )
    ):
        status = "UNSUPPORTED"
    else:
        status = "UNCERTAIN"
    return {
        "schema": "s20plus_g986n_fastboot_boot_support_command_result_v1",
        "version": VERSION,
        "status": status,
        "returncode": returncode,
        "output": output,
        "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
        "replay_permitted": False,
        "at": now(),
    }


def execute(
    approval: str,
    *,
    ready: Callable[[], None] | None = None,
    usb_inventory: UsbInventory = census.real_usb_inventory,
) -> dict[str, Any]:
    if not LIVE_ACTIVE:
        raise SupportProbeError("live support probe is not active")
    if CONSUMED.exists() or CONSUMED.is_symlink():
        raise SupportProbeError("fastboot-boot support probe is already consumed")
    run_dir, prepared = load_prepared()
    if approval != prepared["approval"]:
        raise SupportProbeError("support-probe approval differs")
    closure = static_closure()
    if closure != prepared["binding"]["predecessors"]:
        raise SupportProbeError("support-probe closure changed after approval")
    command = census.RawCommand(run_dir, "execute")
    health = census.collect_android_health(command, usb_inventory)
    target = prepared["binding"]["target"]
    if (
        health["serial_sha256"] != target["serial_sha256"]
        or health["topology_sha256"] != target["topology_sha256"]
        or health["boot_id_sha256"] != target["boot_id_sha256"]
        or health["other_serial_sha256"] != target["other_serial_sha256"]
        or health["adb"] != prepared["binding"]["adb"]
    ):
        raise SupportProbeError("prepared target or boot changed before entry")
    create_entry_intent(run_dir, prepared)
    if ready is not None:
        ready()
    endpoint = census.wait_for_fastboot(
        usb_inventory,
        health["node"],
        health["serial"],
        timeout=census.MAX_WAIT_SECONDS,
    )
    census.base.durable_write(
        run_dir / "entry-observed.json",
        {
            "schema": "s20plus_g986n_fastboot_boot_support_entry_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "serial_sha256": census.base.sha256_text(endpoint["serial"]),
            "topology_sha256": health["topology_sha256"],
            "at": now(),
        },
    )
    post_rows = census.base.parse_inventory(
        census.base.decode_command(
            command([health["adb"]["path"], "devices", "-l"], 10, MAX_OUTPUT),
            "post-entry ADB inventory",
        )
    )
    if any(row["serial"] == health["serial"] for row in post_rows):
        raise ReturnRequiredError("prepared target remains in ADB after fastboot arrival")
    if sorted(census.base.sha256_text(row["serial"]) for row in post_rows) != health[
        "other_serial_sha256"
    ]:
        raise ReturnRequiredError("other ADB inventory changed during fastboot entry")
    if static_closure() != closure:
        raise ReturnRequiredError("support-probe closure changed before boot intent")
    fastboot = census.require_fastboot(ROOT)
    if fastboot != prepared["binding"]["fastboot"]:
        raise ReturnRequiredError("fastboot tool changed before boot intent")
    if census.validate_fastboot_usb(
        usb_inventory(), health["node"], health["serial"]
    ) is None:
        raise ReturnRequiredError("exact fastboot endpoint disappeared")
    intent = {
        "schema": "s20plus_g986n_fastboot_boot_support_command_intent_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "command_shape": prepared["binding"]["command_shape"],
        "boot_image_sha256": BOOT_IMAGE_SHA256,
        "attempt": 1,
        "no_replay": True,
        "at": now(),
    }
    census.base.durable_write(run_dir / "boot-intent.json", intent)
    try:
        raw_result = command(
            [
                fastboot["path"],
                "-s",
                health["serial"],
                "boot",
                str(BOOT_IMAGE),
            ],
            120,
            MAX_OUTPUT // 2,
        )
    finally:
        if (
            static_closure() != closure
            or census.require_fastboot(ROOT) != prepared["binding"]["fastboot"]
        ):
            raise ReturnRequiredError(
                "support-probe artifact, source, or tool changed after boot command"
            )
    result = classify_boot(
        raw_result,
        (health["serial"], health["devpath"], health["node"], str(BOOT_IMAGE)),
    )
    result["intent_sha256"] = census.object_sha256(intent)
    census.base.durable_write(run_dir / "boot-result.json", result)
    return result


def consumed_run() -> Path:
    value = census.load_json(CONSUMED, "support-probe consumed intent")
    if (
        set(value)
        != {
            "schema",
            "version",
            "run_dir",
            "binding_sha256",
            "operator_action",
            "host_transition_command",
            "attempt",
            "no_replay",
            "at",
        }
        or value.get("schema")
        != "s20plus_g986n_fastboot_boot_support_entry_intent_v1"
        or value.get("version") != VERSION
        or value.get("operator_action") != "select Magisk bootloader reboot"
        or value.get("host_transition_command") is not None
        or value.get("attempt") != 1
        or value.get("no_replay") is not True
        or not isinstance(value.get("binding_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", value["binding_sha256"]) is None
        or not isinstance(value.get("at"), str)
    ):
        raise SupportProbeError("support-probe consumed intent differs")
    return _bound_run(value)


def entry_observed(run_dir: Path, prepared: dict[str, Any]) -> bool:
    path = run_dir / "entry-observed.json"
    if not _lexists(path):
        return False
    value = census.load_json(path, "fastboot entry observation")
    target = prepared["binding"]["target"]
    if (
        set(value)
        != {
            "schema",
            "version",
            "binding_sha256",
            "serial_sha256",
            "topology_sha256",
            "at",
        }
        or value.get("schema") != "s20plus_g986n_fastboot_boot_support_entry_v1"
        or value.get("version") != VERSION
        or value.get("binding_sha256") != prepared["binding_sha256"]
        or value.get("serial_sha256") != target["serial_sha256"]
        or value.get("topology_sha256") != target["topology_sha256"]
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise SupportProbeError("fastboot entry observation differs")
    return True


def command_status(run_dir: Path, prepared: dict[str, Any]) -> str:
    intent_path = run_dir / "boot-intent.json"
    result_path = run_dir / "boot-result.json"
    entry_present = entry_observed(run_dir, prepared)
    intent_present = _lexists(intent_path)
    result_present = _lexists(result_path)
    if result_present and not intent_present:
        raise SupportProbeError("fastboot boot result has no intent")
    if not intent_present:
        return "NO_RESULT"
    if not entry_present:
        raise SupportProbeError("fastboot boot intent has no valid entry observation")
    intent = census.load_json(intent_path, "fastboot boot intent")
    if (
        set(intent)
        != {
            "schema",
            "version",
            "binding_sha256",
            "command_shape",
            "boot_image_sha256",
            "attempt",
            "no_replay",
            "at",
        }
        or intent.get("schema")
        != "s20plus_g986n_fastboot_boot_support_command_intent_v1"
        or intent.get("version") != VERSION
        or intent.get("binding_sha256") != prepared["binding_sha256"]
        or intent.get("command_shape") != prepared["binding"]["command_shape"]
        or intent.get("boot_image_sha256") != BOOT_IMAGE_SHA256
        or intent.get("attempt") != 1
        or intent.get("no_replay") is not True
        or not isinstance(intent.get("at"), str)
    ):
        raise SupportProbeError("fastboot boot intent differs")
    if not result_present:
        return "NO_RESULT"
    result = census.load_json(result_path, "fastboot boot result")
    if (
        set(result)
        != {
            "schema",
            "version",
            "status",
            "returncode",
            "output",
            "output_sha256",
            "replay_permitted",
            "at",
            "intent_sha256",
        }
        or result.get("schema")
        != "s20plus_g986n_fastboot_boot_support_command_result_v1"
        or result.get("version") != VERSION
        or result.get("intent_sha256") != census.object_sha256(intent)
        or result.get("replay_permitted") is not False
        or type(result.get("returncode")) is not int
        or not isinstance(result.get("output"), str)
        or len(result["output"].encode()) > MAX_OUTPUT
        or result.get("output_sha256")
        != hashlib.sha256(result["output"].encode()).hexdigest()
        or not isinstance(result.get("at"), str)
    ):
        raise SupportProbeError("fastboot boot result differs")
    derived = classify_boot(
        (result["returncode"], result["output"].encode(), b""),
        (),
    )["status"]
    if result.get("status") != derived:
        raise SupportProbeError("fastboot boot result classification differs")
    return derived


def validate_terminal(
    terminal: dict[str, Any],
    run_dir: Path,
    prepared: dict[str, Any],
) -> None:
    required = {
        "schema",
        "version",
        "binding_sha256",
        "command_status",
        "fastboot_boot_attempts",
        "returned_android",
        "fastboot_endpoint_absent_before_health",
        "ram_payload_transfer_attempts",
        "persistent_device_writes",
        "partition_writes",
        "persistent_mutation",
        "partition_access",
        "replay_permitted",
        "verdict",
        "at",
    }
    returned = terminal.get("returned_android")
    target = prepared["binding"]["target"]
    status = command_status(run_dir, prepared)
    expected_verdict = {
        "COMMAND_ACCEPTED": PASS_SUPPORTED,
        "UNSUPPORTED": PASS_UNSUPPORTED,
    }.get(status, NO_PROOF)
    if (
        set(terminal) != required
        or terminal.get("schema")
        != "s20plus_g986n_fastboot_boot_support_terminal_v1"
        or terminal.get("version") != VERSION
        or terminal.get("binding_sha256") != prepared["binding_sha256"]
        or terminal.get("command_status") != status
        or type(terminal.get("fastboot_boot_attempts")) is not int
        or terminal.get("fastboot_boot_attempts")
        != int(_lexists(run_dir / "boot-intent.json"))
        or not isinstance(returned, dict)
        or set(returned) != {
            "serial_sha256",
            "topology_sha256",
            "boot_id_sha256",
            "health",
            "adb",
        }
        or returned.get("serial_sha256") != target["serial_sha256"]
        or returned.get("topology_sha256") != target["topology_sha256"]
        or returned.get("boot_id_sha256") == target["boot_id_sha256"]
        or returned.get("health")
        != {
            "model": census.EXPECTED_MODEL,
            "device": census.EXPECTED_DEVICE,
            "product_name": census.EXPECTED_PRODUCT,
            "incremental": census.EXPECTED_INCREMENTAL,
            "boot_completed": "1",
            "bootanim": "stopped",
            "selinux": "Enforcing",
        }
        or returned.get("adb") != prepared["binding"]["adb"]
        or terminal.get("fastboot_endpoint_absent_before_health") is not True
        or terminal.get("ram_payload_transfer_attempts")
        != int(_lexists(run_dir / "boot-intent.json"))
        or terminal.get("persistent_device_writes") is not False
        or terminal.get("partition_writes") != 0
        or terminal.get("persistent_mutation") is not False
        or terminal.get("partition_access") is not False
        or terminal.get("replay_permitted") is not False
        or terminal.get("verdict") != expected_verdict
        or not isinstance(terminal.get("at"), str)
    ):
        raise SupportProbeError("support-probe terminal differs")


def finalize(
    command: Command,
    *,
    usb_inventory: UsbInventory = census.real_usb_inventory,
) -> dict[str, Any]:
    run_dir = consumed_run()
    prepared_at = validate_prepared_at(run_dir)
    consumed = census.load_json(CONSUMED, "support-probe consumed intent")
    if consumed.get("binding_sha256") != prepared_at["binding_sha256"]:
        raise SupportProbeError("consumed intent binding differs")
    terminal_path = run_dir / "final-result.json"
    if _lexists(terminal_path):
        terminal = census.load_json(terminal_path, "support-probe terminal")
        validate_terminal(terminal, run_dir, prepared_at)
        if _lexists(SHARED_GUARD):
            release_guard(run_dir)
        return terminal
    _run, prepared = load_prepared()
    if _run != run_dir or prepared != prepared_at:
        raise SupportProbeError("support-probe prepared run differs")
    validate_runtime_sources(prepared)
    if any(
        census._is_fastboot(interface)
        for row in usb_inventory()
        for interface in row.get("interfaces", ())
    ):
        raise ReturnRequiredError("phone remains in fastboot")
    health = census.collect_android_health(command, usb_inventory)
    target = prepared["binding"]["target"]
    if (
        health["serial_sha256"] != target["serial_sha256"]
        or health["topology_sha256"] != target["topology_sha256"]
        or health["other_serial_sha256"] != target["other_serial_sha256"]
        or health["boot_id_sha256"] == target["boot_id_sha256"]
        or health["adb"] != prepared["binding"]["adb"]
    ):
        raise SupportProbeError("returned Android identity or boot differs")
    status = command_status(run_dir, prepared)
    verdict = {
        "COMMAND_ACCEPTED": PASS_SUPPORTED,
        "UNSUPPORTED": PASS_UNSUPPORTED,
    }.get(status, NO_PROOF)
    terminal = {
        "schema": "s20plus_g986n_fastboot_boot_support_terminal_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "command_status": status,
        "fastboot_boot_attempts": int(_lexists(run_dir / "boot-intent.json")),
        "returned_android": {
            "serial_sha256": health["serial_sha256"],
            "topology_sha256": health["topology_sha256"],
            "boot_id_sha256": health["boot_id_sha256"],
            "health": health["health"],
            "adb": health["adb"],
        },
        "fastboot_endpoint_absent_before_health": True,
        "ram_payload_transfer_attempts": int(
            _lexists(run_dir / "boot-intent.json")
        ),
        "persistent_device_writes": False,
        "partition_writes": 0,
        "persistent_mutation": False,
        "partition_access": False,
        "replay_permitted": False,
        "verdict": verdict,
        "at": now(),
    }
    census.base.durable_write(terminal_path, terminal)
    validate_terminal(terminal, run_dir, prepared)
    release_guard(run_dir)
    return terminal


def plan() -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_fastboot_boot_support_plan_v1",
        "version": VERSION,
        "target": (
            f"{census.EXPECTED_MODEL}/{census.EXPECTED_DEVICE}/"
            f"{census.EXPECTED_INCREMENTAL}"
        ),
        "boot_image": {
            "size": BOOT_IMAGE_SIZE,
            "sha256": BOOT_IMAGE_SHA256,
        },
        "fastboot_commands": [["boot", "BOUND_BOOT_IMAGE"]],
        "command_count": 1,
        "ram_payload_transfer_attempts": 1,
        "partition_writes": 0,
        "persistent_mutation": False,
        "physical_recovery": True,
        "live_active": LIVE_ACTIVE,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    modes = result.add_mutually_exclusive_group(required=True)
    modes.add_argument("--render-plan", action="store_true")
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--abort-pre-entry", action="store_true")
    modes.add_argument("--finalize", action="store_true")
    result.add_argument("--operator-attended", action="store_true")
    result.add_argument("--approval")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.render_plan:
        print(json.dumps(plan(), indent=2, sort_keys=True))
        return 0
    if not args.operator_attended:
        print("STOP_S20PLUS_FASTBOOT_BOOT_SUPPORT: operator attendance required")
        return 2
    if not LIVE_ACTIVE:
        print("STOP_S20PLUS_FASTBOOT_BOOT_SUPPORT: reviewed activation absent")
        return 2
    if args.prepare:
        if args.approval is not None:
            print("STOP_S20PLUS_FASTBOOT_BOOT_SUPPORT: prepare accepts no approval")
            return 2
        try:
            run_dir, approval = prepare()
        except Exception:
            print("FAIL_S20PLUS_FASTBOOT_BOOT_SUPPORT_PREPARE_CLOSED")
            return 1
        print("READY_S20PLUS_FASTBOOT_BOOT_SUPPORT_F1")
        print(f"approval={approval}")
        print(f"run_dir={run_dir}")
        return 0
    if args.abort_pre_entry:
        if args.approval is not None:
            print("STOP_S20PLUS_FASTBOOT_BOOT_SUPPORT: abort accepts no approval")
            return 2
        try:
            path = abort_pre_entry()
        except Exception:
            print("FAIL_S20PLUS_FASTBOOT_BOOT_SUPPORT_PRE_ENTRY_ABORT_CLOSED")
            return 1
        print("PASS_S20PLUS_FASTBOOT_BOOT_SUPPORT_PRE_ENTRY_ABORT_ZERO_EFFECT")
        print(f"result={path}")
        return 0
    if args.execute:
        if args.approval is None:
            print("STOP_S20PLUS_FASTBOOT_BOOT_SUPPORT: execute requires approval")
            return 2
        try:
            result = execute(
                args.approval,
                ready=lambda: print(
                    "READY_FOR_OPERATOR_MAGISK_BOOTLOADER_ENTRY", flush=True
                ),
            )
        except Exception as exc:
            if _lexists(CONSUMED):
                run_dir = consumed_run()
                failure = run_dir / "failure.json"
                if not _lexists(failure):
                    census.base.durable_write(
                        failure,
                        {
                            "schema": "s20plus_g986n_fastboot_boot_support_failure_v1",
                            "version": VERSION,
                            "failure_class": type(exc).__name__,
                            "failure_sha256": hashlib.sha256(
                                f"{type(exc).__name__}:{exc}".encode()
                            ).hexdigest(),
                            "return_required": True,
                            "replay_permitted": False,
                            "at": now(),
                        },
                    )
                print("RECOVERY_PENDING_S20PLUS_FASTBOOT_BOOT_SUPPORT")
            else:
                print("FAIL_S20PLUS_FASTBOOT_BOOT_SUPPORT_PRE_ENTRY_CLOSED")
            return 1
        print("S20PLUS_FASTBOOT_BOOT_SUPPORT_RETURN_PENDING")
        print(f"command_status={result['status']}")
        print(
            "OPERATOR_ACTION_REQUIRED: wait for Android; if still in fastboot, "
            "select physical START"
        )
        return 0

    if args.approval is not None:
        print("STOP_S20PLUS_FASTBOOT_BOOT_SUPPORT: finalize accepts no approval")
        return 2
    try:
        run_dir = consumed_run()
        if _lexists(run_dir / "final-result.json"):
            def command(*_args: Any) -> tuple[int, bytes, bytes]:
                raise SupportProbeError("terminal re-emission cannot contact device")
        else:
            command = census.RawCommand(
                run_dir,
                "read",
                capture_dir=census.allocate_finalize_capture_dir(run_dir),
            )
        terminal = finalize(command)
    except ReturnRequiredError:
        print("RETURN_REQUIRED_S20PLUS_FASTBOOT_BOOT_SUPPORT: select physical START")
        return 1
    except Exception:
        print("FAIL_S20PLUS_FASTBOOT_BOOT_SUPPORT_FINALIZE_CLOSED")
        return 1
    print(terminal["verdict"])
    print(f"result={run_dir / 'final-result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
