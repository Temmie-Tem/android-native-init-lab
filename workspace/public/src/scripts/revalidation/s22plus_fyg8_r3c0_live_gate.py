#!/usr/bin/env python3
"""Guarded FYG8 R3C0 synthetic-carrier boot-only live gate.

The candidate preserves the exact stock kernel and ramdisk while applying only
the independently reproduced signer/footer normalization.  A live run flashes
that exact boot-only AP once, performs bounded Android identity checks, and
then restores the pinned Magisk boot AP.  The stock boot AP is cleanup-only if
the Magisk rollback transfer fails while one unambiguous Odin endpoint remains.
"""

from __future__ import annotations

import argparse
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

from s22plus_m3_observable_live_gate import (
    DEFAULT_MAGISK_ROLLBACK_AP,
    DEFAULT_ODIN,
    EXPECTED_MAGISK_AP_SHA256,
    EXPECTED_MEMBER,
    append_log,
    flash_ap,
    odin_devices,
    repo_root,
    resolve,
    sha256_file,
    tar_members,
    wait_for_odin,
)


SCHEMA = "s22plus_fyg8_r3c0_live_gate_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
SCRIPT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r3c0_live_gate.py"
)
CHECKER_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r3_static_checker.py"
)
POLICY_DRAFT = Path(
    "docs/operations/S22PLUS_FYG8_R3C0_AGENTS_EXCEPTION_DRAFT_2026-07-12.md"
)
POLICY_MARKER = "S22+ FYG8 R3C0 synthetic carrier boot-only live gate"
ACTIVE_SENTINEL = "S22PLUS_FYG8_R3C0_POLICY_STATE=ACTIVE"
PENDING_SENTINEL = "S22PLUS_FYG8_R3C0_POLICY_STATE=PENDING_OPERATOR_APPROVAL"
LIVE_ACK_TOKEN = "S22PLUS-FYG8-R3C0-SYNTHETIC-CARRIER-LIVE"
ROLLBACK_ACK_TOKEN = "S22PLUS-FYG8-R3C0-MAGISK-ROLLBACK-FROM-DOWNLOAD"

EXPECTED_CANDIDATE_BOOT_SHA256 = (
    "384efeb0f81534cbfaf3643f42e34fb6e01fe6f0b6bf80139a047a1f9a71f29f"
)
EXPECTED_CANDIDATE_BOOT_SIZE = 100_663_296
EXPECTED_CANDIDATE_LZ4_SHA256 = (
    "61f5d9f6bdf4ebba538234f8c0621c0a1219099cb213150ad3a0299c76e2212e"
)
EXPECTED_CANDIDATE_AP_SHA256 = (
    "8f2b16d3ee8932ff927e06fee8956f975ec3f9e5cc0ef16337e00ad5108d3c00"
)
EXPECTED_MANIFEST_SHA256 = (
    "febffce465ea639d4d4751170bf280ae148ca3431f560aae6ecd8ea08f12ced0"
)
EXPECTED_CHECKER_SHA256 = (
    "917b12f82dc5525b84cf2627379a80e49d921b6c33ca79fe3fc5c6a9ece6a514"
)
AUTHORIZED_LIVE_HELPER_SHA256 = (
    "921800725fa73b7d37fd8d3c46369d0015ab4a8e366111e079b5f7ce674246e3"
)
EXPECTED_MAGISK_BOOT_SHA256 = (
    "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
)
EXPECTED_STOCK_BOOT_SHA256 = (
    "4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae"
)
EXPECTED_STOCK_AP_SHA256 = (
    "2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94"
)
EXPECTED_DTBO_SHA256 = (
    "97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c"
)
EXPECTED_RECOVERY_SHA256 = (
    "93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4"
)
EXPECTED_ODIN_SHA256 = (
    "6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b"
)
EXPECTED_ODIN_SIZE = 3_746_744
EXPECTED_RELEASE = "5.10.226-android12-9-30958166-abS906NKSS7FYG8"
EXPECTED_PROC_VERSION = (
    "Linux version 5.10.226-android12-9-30958166-abS906NKSS7FYG8 "
    "(build-user@build-host) (Android (7284624, based on r416183b) clang "
    "version 12.0.5 (https://android.googlesource.com/toolchain/llvm-project "
    "c935d99d7cf2016289302412d708641d52d2f7ee), LLD 12.0.5 "
    "(/buildbot/src/android/llvm-toolchain/out/llvm-project/lld "
    "c935d99d7cf2016289302412d708641d52d2f7ee)) #1 SMP PREEMPT "
    "Fri Aug 1 05:55:56 UTC 2025"
)

DEFAULT_CANDIDATE_DIR = Path(
    "workspace/private/outputs/s22plus_fyg8_r3c0_control/reproduction-a"
)
DEFAULT_CANDIDATE_BOOT = DEFAULT_CANDIDATE_DIR / "boot.img"
DEFAULT_CANDIDATE_AP = DEFAULT_CANDIDATE_DIR / "odin4/AP.tar.md5"
DEFAULT_MANIFEST = DEFAULT_CANDIDATE_DIR / "manifest.json"
DEFAULT_STOCK_ROLLBACK_AP = Path(
    "workspace/private/outputs/s22plus_native_init/"
    "odin4_stock_rollback_fyg8_raw_repacked_20260709/AP.tar.md5"
)
RUN_ROOT = Path("workspace/private/runs")
CONSUMED_STATE = Path(
    "workspace/private/state/s22plus_fyg8_r3c0_live_exception_consumed.json"
)
TIMELINE_NAMES = (
    "live_session_start",
    "candidate_flash_start",
    "candidate_flash_done",
    "candidate_boot_ready",
    "rollback_flash_start",
    "rollback_flash_done",
    "rollback_boot_ready",
    "live_session_end",
)
SERIAL_RE = re.compile(r"\b[A-Z0-9]{10,16}\b")


class GateError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def redact(text: str) -> str:
    return SERIAL_RE.sub("<S22_SERIAL_REDACTED>", text)


def durable_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def append_event(path: Path, events: list[dict[str, str]], name: str) -> None:
    if name not in TIMELINE_NAMES:
        raise GateError(f"unknown timeline event: {name}")
    if name in {event["name"] for event in events}:
        raise GateError(f"duplicate timeline event: {name}")
    events.append({"name": name, "timestamp_utc": utc_now()})
    durable_write_json(path, {"events": events})


def run(command: list[str | Path], timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(part) for part in command],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )


def adb_serial() -> str:
    result = run(["adb", "devices", "-l"], timeout=10)
    if result.returncode != 0:
        raise GateError("adb devices failed")
    rows = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            rows.append(parts[0])
    if len(rows) != 1:
        raise GateError(f"expected one authorized Android device, found {len(rows)}")
    return rows[0]


def adb_shell(serial: str, command: str, *, root: bool = False, timeout: float = 30.0) -> str:
    argv = ["adb", "-s", serial, "shell"]
    if root:
        argv.extend(["su", "-c", shlex.quote(command)])
    else:
        argv.append(command)
    result = run(argv, timeout=timeout)
    if result.returncode != 0:
        raise GateError(f"adb shell failed: {command.split()[0]}")
    return result.stdout.strip()


def sha256_output(value: str, label: str) -> str:
    fields = value.split()
    if not fields or not re.fullmatch(r"[0-9a-f]{64}", fields[0]):
        raise GateError(f"empty or malformed sha256 output: {label}")
    return fields[0]


def current_android() -> tuple[str, dict[str, str]]:
    serial = adb_serial()
    values = {
        "model": adb_shell(serial, "getprop ro.product.model"),
        "device": adb_shell(serial, "getprop ro.product.device"),
        "bootloader": adb_shell(serial, "getprop ro.boot.bootloader"),
        "incremental": adb_shell(serial, "getprop ro.build.version.incremental"),
        "boot_completed": adb_shell(serial, "getprop sys.boot_completed"),
        "bootanim": adb_shell(serial, "getprop init.svc.bootanim"),
        "verified_boot_state": adb_shell(serial, "getprop ro.boot.verifiedbootstate"),
        "root": adb_shell(serial, "id", root=True),
        "boot_sha256": sha256_output(
            adb_shell(
                serial, "sha256sum /dev/block/by-name/boot", root=True, timeout=90
            ),
            "boot",
        ),
        "dtbo_sha256": sha256_output(
            adb_shell(
                serial, "sha256sum /dev/block/by-name/dtbo", root=True, timeout=60
            ),
            "dtbo",
        ),
        "recovery_sha256": sha256_output(
            adb_shell(
                serial,
                "sha256sum /dev/block/by-name/recovery",
                root=True,
                timeout=90,
            ),
            "recovery",
        ),
    }
    expected = {
        "model": "SM-S906N",
        "device": "g0q",
        "bootloader": "S906NKSS7FYG8",
        "incremental": "S906NKSS7FYG8",
        "boot_completed": "1",
        "bootanim": "stopped",
        "verified_boot_state": "orange",
        "boot_sha256": EXPECTED_MAGISK_BOOT_SHA256,
        "dtbo_sha256": EXPECTED_DTBO_SHA256,
        "recovery_sha256": EXPECTED_RECOVERY_SHA256,
    }
    for key, expected_value in expected.items():
        if values[key] != expected_value:
            raise GateError(f"Android baseline mismatch: {key}")
    if "uid=0(root)" not in values["root"]:
        raise GateError("Magisk root missing")
    values["root"] = "uid=0(root)"
    return serial, values


def candidate_android_once() -> tuple[str, dict[str, str]]:
    serial = adb_serial()
    values = {
        "model": adb_shell(serial, "getprop ro.product.model"),
        "device": adb_shell(serial, "getprop ro.product.device"),
        "bootloader": adb_shell(serial, "getprop ro.boot.bootloader"),
        "incremental": adb_shell(serial, "getprop ro.build.version.incremental"),
        "boot_completed": adb_shell(serial, "getprop sys.boot_completed"),
        "bootanim": adb_shell(serial, "getprop init.svc.bootanim"),
        "verified_boot_state": adb_shell(serial, "getprop ro.boot.verifiedbootstate"),
        "uname_release": adb_shell(serial, "uname -r"),
        "proc_version": adb_shell(serial, "cat /proc/version"),
    }
    expected = {
        "model": "SM-S906N",
        "device": "g0q",
        "bootloader": "S906NKSS7FYG8",
        "incremental": "S906NKSS7FYG8",
        "boot_completed": "1",
        "bootanim": "stopped",
        "uname_release": EXPECTED_RELEASE,
        "proc_version": EXPECTED_PROC_VERSION,
    }
    for key, expected_value in expected.items():
        if values[key] != expected_value:
            raise GateError(f"candidate Android mismatch: {key}")
    if values["verified_boot_state"] != "orange":
        raise GateError("candidate verified-boot state is not expected orange")
    return serial, values


def wait_candidate_android(
    wait_sec: int, sample_count: int, sample_interval_sec: float
) -> tuple[str | None, list[dict[str, str]], str]:
    deadline = time.monotonic() + wait_sec
    last_error = "no Android observation"
    while time.monotonic() < deadline:
        try:
            serial, first = candidate_android_once()
            samples = [first]
            for _ in range(sample_count - 1):
                time.sleep(sample_interval_sec)
                next_serial, sample = candidate_android_once()
                if next_serial != serial:
                    raise GateError("candidate Android serial changed during sampling")
                samples.append(sample)
            return serial, samples, "candidate Android milestone reached"
        except (GateError, subprocess.SubprocessError) as error:
            last_error = str(error)
            time.sleep(2)
    return None, [], last_error


def verify_manifest(path: Path) -> dict[str, Any]:
    if sha256_file(path) != EXPECTED_MANIFEST_SHA256:
        raise GateError("R3C0 manifest SHA mismatch")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "s22plus_fyg8_r3c0_control_build_v1":
        raise GateError("R3C0 manifest schema mismatch")
    if data.get("target") != TARGET:
        raise GateError("R3C0 manifest target mismatch")
    if data.get("verdict") != "PASS_R3C0_ARTIFACT_BUILT_HOST_ONLY":
        raise GateError("R3C0 manifest verdict mismatch")
    hashes = data.get("artifacts", {}).get("hashes", {})
    expected_hashes = {
        "boot_img": EXPECTED_CANDIDATE_BOOT_SHA256,
        "boot_img_lz4": EXPECTED_CANDIDATE_LZ4_SHA256,
        "ap_tar_md5": EXPECTED_CANDIDATE_AP_SHA256,
    }
    for key, expected in expected_hashes.items():
        if hashes.get(key) != expected:
            raise GateError(f"R3C0 manifest artifact mismatch: {key}")
    construction = data.get("construction", {})
    required_construction = {
        "magiskboot_executed": False,
        "patch_vbmeta_flag": False,
        "stock_kernel_preserved": True,
        "stock_ramdisk_preserved": True,
        "stock_vbmeta_preserved": True,
        "exact_expected_normalization": True,
    }
    for key, expected in required_construction.items():
        if construction.get(key) != expected:
            raise GateError(f"R3C0 manifest construction mismatch: {key}")
    safety = data.get("safety", {})
    required_safety = {
        "boot_only_ap": True,
        "device_contact": False,
        "flash": False,
        "host_only": True,
        "live_authorized": False,
        "odin_transfer": False,
        "r3c1_authorized": False,
        "usb_enumeration": False,
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise GateError(f"R3C0 manifest safety mismatch: {key}")
    return data


def verify_odin(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise GateError("pinned Odin executable missing")
    if path.stat().st_size != EXPECTED_ODIN_SIZE:
        raise GateError("Odin size mismatch")
    if sha256_file(path) != EXPECTED_ODIN_SHA256:
        raise GateError("Odin SHA mismatch")
    return {"path": str(path), "size": EXPECTED_ODIN_SIZE, "sha256": EXPECTED_ODIN_SHA256}


def run_static_checker(root: Path, boot: Path, ap: Path) -> dict[str, Any]:
    checker = root / CHECKER_RELATIVE
    if sha256_file(checker) != EXPECTED_CHECKER_SHA256:
        raise GateError("R3 static checker SHA mismatch")
    result = run(
        [
            sys.executable,
            checker,
            "--stage",
            "r3c0",
            "--r3c0-boot",
            boot,
            "--r3c0-ap",
            ap,
            "--r3c0-boot-sha256",
            EXPECTED_CANDIDATE_BOOT_SHA256,
            "--r3c0-ap-sha256",
            EXPECTED_CANDIDATE_AP_SHA256,
        ],
        timeout=180,
    )
    if result.returncode != 0:
        raise GateError("R3 static checker failed closed")
    report = json.loads(result.stdout)
    if report.get("verdict") != "PASS_R3C0_STATIC_CONTRACT":
        raise GateError("R3 static checker verdict mismatch")
    return {
        "source_sha256": EXPECTED_CHECKER_SHA256,
        "verdict": report["verdict"],
        "scope": report.get("scope", {}),
    }


def verify_artifacts(
    root: Path, boot: Path, ap: Path, manifest: Path, odin: Path
) -> dict[str, Any]:
    if boot.stat().st_size != EXPECTED_CANDIDATE_BOOT_SIZE:
        raise GateError("candidate boot size mismatch")
    if sha256_file(boot) != EXPECTED_CANDIDATE_BOOT_SHA256:
        raise GateError("candidate boot SHA mismatch")
    if sha256_file(ap) != EXPECTED_CANDIDATE_AP_SHA256:
        raise GateError("candidate AP SHA mismatch")
    if tar_members(ap) != [EXPECTED_MEMBER]:
        raise GateError("candidate AP is not exactly boot-only")
    manifest_data = verify_manifest(manifest)
    magisk = resolve(root, DEFAULT_MAGISK_ROLLBACK_AP)
    stock = resolve(root, DEFAULT_STOCK_ROLLBACK_AP)
    if sha256_file(magisk) != EXPECTED_MAGISK_AP_SHA256:
        raise GateError("Magisk rollback AP SHA mismatch")
    if tar_members(magisk) != [EXPECTED_MEMBER]:
        raise GateError("Magisk rollback AP is not boot-only")
    if sha256_file(stock) != EXPECTED_STOCK_AP_SHA256:
        raise GateError("stock cleanup AP SHA mismatch")
    if tar_members(stock) != [EXPECTED_MEMBER]:
        raise GateError("stock cleanup AP is not boot-only")
    checker = run_static_checker(root, boot, ap)
    return {
        "candidate_boot_sha256": EXPECTED_CANDIDATE_BOOT_SHA256,
        "candidate_ap_sha256": EXPECTED_CANDIDATE_AP_SHA256,
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "manifest_schema": manifest_data["schema"],
        "magisk_rollback_ap_sha256": EXPECTED_MAGISK_AP_SHA256,
        "stock_cleanup_ap_sha256": EXPECTED_STOCK_AP_SHA256,
        "checker": checker,
        "odin": verify_odin(odin),
    }


def policy_active(root: Path) -> bool:
    text = (root / "AGENTS.md").read_text(encoding="utf-8")
    source_sha = sha256_file(root / SCRIPT_RELATIVE)
    active_line = re.compile(
        rf"(?m)^\s*`?{re.escape(ACTIVE_SENTINEL)}`?\s*$"
    )
    required = (
        POLICY_MARKER,
        str(SCRIPT_RELATIVE),
        source_sha,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        EXPECTED_CANDIDATE_BOOT_SHA256,
        EXPECTED_CANDIDATE_AP_SHA256,
        EXPECTED_MAGISK_AP_SHA256,
        EXPECTED_STOCK_AP_SHA256,
    )
    return bool(active_line.search(text)) and all(item in text for item in required)


def consumed_state_path(root: Path) -> Path:
    return root / CONSUMED_STATE


def ensure_not_consumed(root: Path) -> None:
    path = consumed_state_path(root)
    if path.exists():
        raise GateError(f"R3C0 one-shot exception already consumed: {path}")


def consume_exception(root: Path, run_dir: Path) -> None:
    path = consumed_state_path(root)
    if path.exists():
        raise GateError(f"R3C0 one-shot exception already consumed: {path}")
    durable_write_json(
        path,
        {
            "schema": "s22plus_fyg8_r3c0_consumed_state_v1",
            "consumed_at_utc": utc_now(),
            "reason": "candidate_flash_start",
            "run_dir": str(run_dir.relative_to(root)),
            "candidate_ap_sha256": EXPECTED_CANDIDATE_AP_SHA256,
        },
    )


def verify_policy_draft(root: Path) -> dict[str, Any]:
    path = root / POLICY_DRAFT
    if not path.is_file():
        raise GateError("R3C0 policy draft missing")
    text = path.read_text(encoding="utf-8")
    source_sha = sha256_file(root / SCRIPT_RELATIVE)
    if "DRAFT_INACTIVE" not in text and "RETIRED_AFTER_PASS" not in text:
        raise GateError("R3C0 policy document state is neither draft nor retired")
    required = (
        POLICY_MARKER,
        str(SCRIPT_RELATIVE),
        AUTHORIZED_LIVE_HELPER_SHA256,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        EXPECTED_CANDIDATE_BOOT_SHA256,
        EXPECTED_CANDIDATE_AP_SHA256,
        EXPECTED_MAGISK_AP_SHA256,
        EXPECTED_STOCK_AP_SHA256,
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise GateError(f"policy draft missing pins: {missing}")
    return {
        "path": str(POLICY_DRAFT),
        "sha256": sha256_file(path),
        "authorized_live_helper_sha256": AUTHORIZED_LIVE_HELPER_SHA256,
        "current_source_sha256": source_sha,
        "active": policy_active(root),
    }


def wait_odin_absent(odin: Path, log_path: Path, label: str, seconds: int) -> bool:
    deadline = time.monotonic() + seconds
    while True:
        devices = odin_devices(odin, log_path, label)
        if not devices:
            append_log(log_path, f"{label}_odin_absent=1")
            return True
        if len(devices) > 1:
            raise GateError(f"ambiguous Odin devices while waiting for disconnect: {devices}")
        if time.monotonic() >= deadline:
            append_log(log_path, f"{label}_odin_absent=0 still_present={devices}")
            return False
        time.sleep(0.5)


def flash_exact(odin: Path, ap: Path, device: str, log_path: Path, label: str) -> None:
    rc = flash_ap(odin, ap, device, log_path, label)
    if rc != 0:
        raise GateError(f"{label} Odin flash failed rc={rc}")


def wait_android(seconds: int) -> tuple[str, dict[str, str]]:
    deadline = time.monotonic() + seconds
    last_error = "no Android observation"
    while time.monotonic() < deadline:
        try:
            return current_android()
        except (GateError, subprocess.SubprocessError) as error:
            last_error = str(error)
            time.sleep(2)
    raise GateError(f"Magisk Android did not return: {last_error}")


def current_stock_android() -> dict[str, str]:
    serial = adb_serial()
    values = {
        "model": adb_shell(serial, "getprop ro.product.model"),
        "device": adb_shell(serial, "getprop ro.product.device"),
        "bootloader": adb_shell(serial, "getprop ro.boot.bootloader"),
        "incremental": adb_shell(serial, "getprop ro.build.version.incremental"),
        "boot_completed": adb_shell(serial, "getprop sys.boot_completed"),
        "bootanim": adb_shell(serial, "getprop init.svc.bootanim"),
        "verified_boot_state": adb_shell(serial, "getprop ro.boot.verifiedbootstate"),
    }
    expected = {
        "model": "SM-S906N",
        "device": "g0q",
        "bootloader": "S906NKSS7FYG8",
        "incremental": "S906NKSS7FYG8",
        "boot_completed": "1",
        "bootanim": "stopped",
        "verified_boot_state": "orange",
    }
    for key, expected_value in expected.items():
        if values[key] != expected_value:
            raise GateError(f"stock cleanup Android mismatch: {key}")
    values["expected_flashed_stock_boot_sha256"] = EXPECTED_STOCK_BOOT_SHA256
    return values


def wait_stock_android(seconds: int) -> dict[str, str]:
    deadline = time.monotonic() + seconds
    last_error = "no stock Android observation"
    while time.monotonic() < deadline:
        try:
            return current_stock_android()
        except (GateError, subprocess.SubprocessError) as error:
            last_error = str(error)
            time.sleep(2)
    raise GateError(f"stock cleanup Android did not return: {last_error}")


def flash_rollback(root: Path, odin: Path, device: str, log_path: Path) -> str:
    try:
        flash_exact(
            odin,
            resolve(root, DEFAULT_MAGISK_ROLLBACK_AP),
            device,
            log_path,
            "magisk-rollback",
        )
        return "magisk"
    except GateError:
        devices = odin_devices(odin, log_path, "r3c0-stock-cleanup")
        if len(devices) != 1:
            raise
        flash_exact(
            odin,
            resolve(root, DEFAULT_STOCK_ROLLBACK_AP),
            devices[0],
            log_path,
            "stock-cleanup",
        )
        return "stock"


def wait_final_android(
    rollback_target: str, android_wait_sec: int, odin: Path, log_path: Path
) -> tuple[dict[str, str], str, int]:
    if rollback_target == "stock":
        final = wait_stock_android(android_wait_sec)
        verdict = "STOCK_CLEANUP_MAGISK_BASELINE_NOT_RESTORED"
        rc = 30
    else:
        _, final = wait_android(android_wait_sec)
        verdict = "PASS_MAGISK_ROLLBACK"
        rc = 0
    devices = odin_devices(odin, log_path, "r3c0-final-no-odin")
    if devices:
        raise GateError(f"Odin endpoint remains after rollback: {devices}")
    return final, verdict, rc


def classify_live_verdict(
    rollback_target: str,
    rollback_verdict: str,
    rollback_rc: int,
    candidate_transfer_ok: bool,
    samples: list[dict[str, str]],
) -> tuple[str, int]:
    if rollback_target != "magisk":
        return rollback_verdict, rollback_rc
    if samples:
        return "PASS_R3C0_NORMALIZED_STOCK_CARRIER_AND_ROLLED_BACK", 0
    if not candidate_transfer_ok:
        return "NO_PROOF_CANDIDATE_TRANSFER_FAILED_MAGISK_ROLLED_BACK", 31
    return "NO_PROOF_NO_CANDIDATE_ANDROID_MILESTONE_MAGISK_ROLLED_BACK", 32


def request_download_if_android() -> bool:
    try:
        serial = adb_serial()
    except GateError:
        return False
    result = run(["adb", "-s", serial, "reboot", "download"], timeout=20)
    return result.returncode == 0


def rollback_from_download(root: Path, odin: Path, run_dir: Path) -> dict[str, Any]:
    timeline: list[dict[str, str]] = []
    timeline_path = run_dir / "timeline.json"
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "mode": "rollback-from-download",
        "timeline_phase_semantics": {
            "candidate_flash_start": "recovery-only-session-no-candidate-flash",
            "candidate_flash_done": "recovery-only-session-no-candidate-flash",
            "candidate_boot_ready": "operator-entered-download-before-session",
        },
        "verdict": "INCOMPLETE",
    }
    append_event(timeline_path, timeline, "live_session_start")
    append_event(timeline_path, timeline, "candidate_flash_start")
    append_event(timeline_path, timeline, "candidate_flash_done")
    append_event(timeline_path, timeline, "candidate_boot_ready")
    durable_write_json(run_dir / "result.json", result)
    devices = odin_devices(odin, run_dir / "rollback.log", "r3c0-recovery")
    if len(devices) != 1:
        raise GateError(f"rollback requires exactly one Odin device, got {len(devices)}")
    append_event(timeline_path, timeline, "rollback_flash_start")
    target = flash_rollback(root, odin, devices[0], run_dir / "rollback.log")
    append_event(timeline_path, timeline, "rollback_flash_done")
    final, verdict, rc = wait_final_android(target, 300, odin, run_dir / "rollback.log")
    if target == "magisk":
        verdict = "PASS_MAGISK_ROLLBACK_FROM_DOWNLOAD"
    append_event(timeline_path, timeline, "rollback_boot_ready")
    append_event(timeline_path, timeline, "live_session_end")
    result.update(
        {
            "rollback_target": target,
            "final": final,
            "verdict": verdict,
            "exit_code": rc,
        }
    )
    durable_write_json(run_dir / "result.json", result)
    return result


def live_run(root: Path, args: argparse.Namespace, artifacts: dict[str, Any]) -> int:
    if not policy_active(root):
        raise GateError("R3C0 live policy is inactive")
    if args.ack != LIVE_ACK_TOKEN:
        raise GateError("live acknowledgement mismatch")
    ensure_not_consumed(root)
    serial, baseline = current_android()
    odin = resolve(root, args.odin)
    run_dir = root / RUN_ROOT / f"s22plus_fyg8_r3c0_live_{utc_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    timeline: list[dict[str, str]] = []
    timeline_path = run_dir / "timeline.json"
    log_path = run_dir / "live.log"
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "target": TARGET,
        "baseline": baseline,
        "artifacts": artifacts,
        "candidate_flash_attempted": False,
        "candidate_milestone_reached": False,
        "verdict": "INCOMPLETE",
    }
    append_event(timeline_path, timeline, "live_session_start")
    durable_write_json(run_dir / "result.json", result)

    reboot = run(["adb", "-s", serial, "reboot", "download"], timeout=20)
    if reboot.returncode != 0:
        raise GateError("Android failed to request Download mode")
    candidate_device = wait_for_odin(odin, log_path, "r3c0-candidate", args.download_wait_sec)
    if candidate_device is None:
        raise GateError("Download mode did not appear before candidate flash")

    append_event(timeline_path, timeline, "candidate_flash_start")
    consume_exception(root, run_dir)
    result["candidate_flash_attempted"] = True
    durable_write_json(run_dir / "result.json", result)
    candidate_transfer_ok = False
    try:
        flash_exact(
            odin,
            resolve(root, args.candidate_ap),
            candidate_device,
            log_path,
            "r3c0-candidate",
        )
        candidate_transfer_ok = True
    except GateError as error:
        result["candidate_flash_error"] = str(error)
    append_event(timeline_path, timeline, "candidate_flash_done")
    durable_write_json(run_dir / "result.json", result)

    samples: list[dict[str, str]] = []
    candidate_error = "candidate transfer failed"
    if candidate_transfer_ok and wait_odin_absent(
        odin, log_path, "r3c0-candidate-disconnect", args.disconnect_wait_sec
    ):
        _, samples, candidate_error = wait_candidate_android(
            args.candidate_wait_sec,
            args.sample_count,
            args.sample_interval_sec,
        )
        result["candidate_samples"] = samples
        result["candidate_milestone_reached"] = bool(samples)
        result["candidate_observation"] = candidate_error
    elif candidate_transfer_ok:
        candidate_error = "original Odin endpoint stayed; candidate boot not proven"
        result["candidate_observation"] = candidate_error
    else:
        result["candidate_observation"] = candidate_error
    result["candidate_boot_ready_semantics"] = (
        "candidate Android milestone reached"
        if samples
        else f"bounded observation closed without milestone: {candidate_error}"
    )
    append_event(timeline_path, timeline, "candidate_boot_ready")
    durable_write_json(run_dir / "result.json", result)

    rollback_device: str | None = None
    existing = odin_devices(odin, log_path, "r3c0-pre-rollback")
    if len(existing) > 1:
        raise GateError(f"ambiguous Odin endpoints before rollback: {existing}")
    if existing:
        rollback_device = existing[0]
    else:
        request_download_if_android()
        print(
            "R3C0 observation is complete. If Download mode does not appear "
            "automatically, enter physical Download mode now for mandatory rollback.",
            flush=True,
        )
        rollback_device = wait_for_odin(
            odin, log_path, "r3c0-mandatory-rollback", args.manual_wait_sec
        )
    if rollback_device is None:
        result.update(
            {
                "verdict": "FAIL_ROLLBACK_NOT_VERIFIED_MANUAL_DOWNLOAD_REQUIRED",
                "timeline_phase_semantics": {
                    "rollback_flash_start": "bounded wait closed; no rollback flash started",
                    "rollback_flash_done": "no rollback flash occurred",
                    "rollback_boot_ready": "rollback Android not observed",
                    "live_session_end": "recovery required through rollback-from-download mode",
                },
            }
        )
        append_event(timeline_path, timeline, "rollback_flash_start")
        append_event(timeline_path, timeline, "rollback_flash_done")
        append_event(timeline_path, timeline, "rollback_boot_ready")
        append_event(timeline_path, timeline, "live_session_end")
        durable_write_json(run_dir / "result.json", result)
        return 20

    append_event(timeline_path, timeline, "rollback_flash_start")
    rollback_target = flash_rollback(root, odin, rollback_device, log_path)
    append_event(timeline_path, timeline, "rollback_flash_done")
    final, rollback_verdict, rollback_rc = wait_final_android(
        rollback_target, args.android_wait_sec, odin, log_path
    )
    append_event(timeline_path, timeline, "rollback_boot_ready")
    verdict, rollback_rc = classify_live_verdict(
        rollback_target,
        rollback_verdict,
        rollback_rc,
        candidate_transfer_ok,
        samples,
    )
    result.update(
        {
            "rollback_target": rollback_target,
            "final": final,
            "verdict": verdict,
        }
    )
    append_event(timeline_path, timeline, "live_session_end")
    durable_write_json(run_dir / "result.json", result)
    print(json.dumps({"run_dir": str(run_dir), "verdict": verdict}, indent=2))
    return rollback_rc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline-check", action="store_true")
    modes.add_argument("--connected-dry-run", action="store_true")
    modes.add_argument("--live", action="store_true")
    modes.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--ack")
    parser.add_argument("--candidate-boot", type=Path, default=DEFAULT_CANDIDATE_BOOT)
    parser.add_argument("--candidate-ap", type=Path, default=DEFAULT_CANDIDATE_AP)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--download-wait-sec", type=int, default=120)
    parser.add_argument("--disconnect-wait-sec", type=int, default=30)
    parser.add_argument("--candidate-wait-sec", type=int, default=300)
    parser.add_argument("--manual-wait-sec", type=int, default=300)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    parser.add_argument("--sample-count", type=int, default=3)
    parser.add_argument("--sample-interval-sec", type=float, default=5.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    try:
        if args.sample_count < 1 or args.sample_count > 5:
            raise GateError("sample count must be between 1 and 5")
        odin = resolve(root, args.odin)
        artifacts = verify_artifacts(
            root,
            resolve(root, args.candidate_boot),
            resolve(root, args.candidate_ap),
            resolve(root, args.manifest),
            odin,
        )
        draft = verify_policy_draft(root)
        if args.offline_check:
            print(
                json.dumps(
                    {
                        "schema": SCHEMA,
                        "artifacts": artifacts,
                        "policy": draft,
                        "device_contact": False,
                    },
                    indent=2,
                )
            )
            return 0
        if args.connected_dry_run:
            _, baseline = current_android()
            devices = odin_devices(odin, Path(os.devnull), "r3c0-connected-dry-run")
            if devices:
                raise GateError(f"connected dry-run requires no Odin endpoint: {devices}")
            print(
                json.dumps(
                    {
                        "schema": SCHEMA,
                        "artifacts": artifacts,
                        "baseline": baseline,
                        "policy_active": draft["active"],
                        "one_shot_consumed": consumed_state_path(root).exists(),
                        "device_writes": False,
                    },
                    indent=2,
                )
            )
            return 0
        if not policy_active(root):
            raise GateError("R3C0 live policy is inactive")
        if args.rollback_from_download:
            if args.ack != ROLLBACK_ACK_TOKEN:
                raise GateError("rollback acknowledgement mismatch")
            run_dir = root / RUN_ROOT / f"s22plus_fyg8_r3c0_rollback_{utc_stamp()}"
            run_dir.mkdir(parents=True, exist_ok=False)
            recovery = rollback_from_download(root, odin, run_dir)
            print(json.dumps(recovery, indent=2))
            return int(recovery["exit_code"])
        return live_run(root, args, artifacts)
    except (
        GateError,
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as error:
        print(f"R3C0 gate error: {redact(str(error))}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
