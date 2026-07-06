#!/usr/bin/env python3
"""Guarded S22+ TWRP refresh plus Magisk boot-capture root restore window.

This helper is intentionally narrow.  It only accepts the SHA-pinned artifacts
authorized for the 2026-07-07 S22+ boot-capture measurement restore window:

1. Flash the pinned g0q TWRP recovery tar with auto-reboot disabled.
2. Wait for the operator to boot directly into TWRP and prove TWRP via ADB.
3. Reboot to download mode and flash the pinned Magisk boot-only AP.
4. Wait for Android, then check Magisk/su state for the upcoming capture unit.

Dry-run is the default.  Live mode requires an explicit ack token.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path


ACK_TOKEN = "S22PLUS-TWRP-MAGISK-RESTORE-WINDOW"

EXPECTED_TWRP_TAR_SHA256 = "0914c68a5353c367216805a3a2fdeb4982c6629368dc021c7fefc10d3d3bd034"
EXPECTED_TWRP_MEMBER = "recovery.img"

EXPECTED_MAGISK_AP_SHA256 = "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56"
EXPECTED_MAGISK_MEMBER = "boot.img.lz4"

EXPECTED_STOCK_RECOVERY_AP_SHA256 = "8d3647313d2e100134f77984d13c7e5dc9946510ab57d8e34dd0cd192ca8586d"
EXPECTED_STOCK_RECOVERY_MEMBER = "recovery.img.lz4"

EXPECTED_STOCK_BOOT_AP_SHA256 = "1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e"
EXPECTED_STOCK_BOOT_MEMBER = "boot.img.lz4"

EXPECTED_FULL_FW_SHA256 = "f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8"

DEFAULT_TWRP_TAR = Path("workspace/private/inputs/s22plus_twrp/g0q/twrp-3.7.0_12-1_afaneh92-g0q.tar")
DEFAULT_MAGISK_AP = Path("workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5")
DEFAULT_STOCK_RECOVERY_AP = Path("workspace/private/outputs/s22plus_twrp/stock_recovery_rollback/AP.tar.md5")
DEFAULT_STOCK_BOOT_AP = Path("workspace/private/outputs/s22plus_native_init/odin4_stock_rollback_short/AP.tar.md5")
DEFAULT_FULL_FW = Path("workspace/private/inputs/firmware/SAMFW.COM_SM-S906N_SKC_S906NKSS7FYG8_fac.zip")
DEFAULT_ODIN = Path("/usr/bin/odin4")

ODIN_DEVICE_RE = re.compile(r"/dev/bus/usb/\d+/\d+")


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").is_dir():
            return parent
    raise RuntimeError(f"could not locate repo root from {current}")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def run(argv: list[str | Path], *, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(part) for part in argv],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tar_members(path: Path) -> list[str]:
    with tarfile.open(path) as tar:
        return [member.name for member in tar.getmembers()]


def append_log(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = requested
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = Path("workspace/private/runs") / f"s22plus_twrp_magisk_restore_{stamp}"
    run_dir = resolve(root, run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def verify_tar(path: Path, expected_sha: str, expected_member: str, label: str, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"{label} missing: {path}")
    actual_sha = sha256_file(path)
    members = tar_members(path)
    append_log(log_path, f"{label}_sha256={actual_sha}")
    append_log(log_path, f"{label}_members={members}")
    if actual_sha != expected_sha:
        raise SystemExit(f"{label} SHA mismatch: {actual_sha}")
    if members != [expected_member]:
        raise SystemExit(f"{label} must contain exactly {expected_member!r}, got {members!r}")


def verify_file_sha(path: Path, expected_sha: str, label: str, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"{label} missing: {path}")
    actual_sha = sha256_file(path)
    append_log(log_path, f"{label}_sha256={actual_sha}")
    if actual_sha != expected_sha:
        raise SystemExit(f"{label} SHA mismatch: {actual_sha}")


def odin_devices(odin: Path, log_path: Path, label: str) -> list[str]:
    result = run([odin, "-l"], timeout=10.0)
    output = result.stdout + result.stderr
    devices = sorted(set(ODIN_DEVICE_RE.findall(output)))
    append_log(log_path, f"[{utc_now()}] {label} odin4 -l rc={result.returncode} devices={devices}")
    append_log(log_path, output)
    return devices


def wait_for_odin(odin: Path, wait_sec: int, log_path: Path) -> str | None:
    deadline = time.monotonic() + wait_sec
    while True:
        devices = odin_devices(odin, log_path, "wait")
        if len(devices) == 1:
            return devices[0]
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices: {devices}")
        if time.monotonic() >= deadline:
            return None
        time.sleep(1.0)


def adb_rows(log_path: Path, label: str) -> list[tuple[str, str, str]]:
    result = run(["adb", "devices", "-l"], timeout=10.0)
    output = result.stdout + result.stderr
    append_log(log_path, f"[{utc_now()}] {label} adb devices -l rc={result.returncode}")
    append_log(log_path, output)
    rows: list[tuple[str, str, str]] = []
    for line in output.splitlines()[1:]:
        parts = line.split(maxsplit=2)
        if len(parts) >= 2:
            rows.append((parts[0], parts[1], parts[2] if len(parts) > 2 else ""))
    return rows


def adb_shell(command: str, *, timeout: float = 20.0) -> subprocess.CompletedProcess[str]:
    return run(["adb", "shell", command], timeout=timeout)


def require_single_android_preflight(log_path: Path) -> None:
    rows = adb_rows(log_path, "preflight")
    if len(rows) != 1:
        raise SystemExit(f"expected exactly one ADB device for Android preflight, got {len(rows)}")
    _serial, state, detail = rows[0]
    if state != "device":
        raise SystemExit(f"ADB preflight state must be 'device', got {state!r}: {detail}")
    props = adb_shell(
        "printf 'model='; getprop ro.product.model; "
        "printf 'device='; getprop ro.product.device; "
        "printf 'bootloader='; getprop ro.boot.bootloader; "
        "printf 'incremental='; getprop ro.build.version.incremental; "
        "printf 'vbstate='; getprop ro.boot.verifiedbootstate; "
        "printf 'boot_recovery='; getprop ro.boot.boot_recovery; "
        "printf 'boot_completed='; getprop sys.boot_completed; "
        "printf 'su='; command -v su || true",
        timeout=20.0,
    )
    text = props.stdout + props.stderr
    append_log(log_path, "preflight_props:")
    append_log(log_path, text)
    required = {
        "model=SM-S906N",
        "device=g0q",
        "bootloader=S906NKSS7FYG8",
        "incremental=S906NKSS7FYG8",
        "vbstate=orange",
        "boot_recovery=0",
        "boot_completed=1",
    }
    missing = sorted(item for item in required if item not in text)
    if missing:
        raise SystemExit(f"S22+ Android preflight missing expected props: {missing}")


def wait_for_twrp(wait_sec: int, log_path: Path) -> bool:
    deadline = time.monotonic() + wait_sec
    while True:
        rows = adb_rows(log_path, "wait-twrp")
        if len(rows) > 1:
            raise SystemExit(f"refusing ambiguous ADB rows while waiting for TWRP: {rows}")
        if len(rows) == 1:
            _serial, state, detail = rows[0]
            append_log(log_path, f"twrp_candidate_state={state} detail={detail}")
            if state == "unauthorized":
                raise SystemExit("TWRP/recovery ADB is unauthorized; cannot prove recovery")
            if state in {"device", "recovery", "sideload"}:
                props = adb_shell(
                    "printf 'twrp='; getprop ro.twrp.version; "
                    "printf 'model='; getprop ro.product.model; "
                    "printf 'device='; getprop ro.product.device; "
                    "printf 'vbstate='; getprop ro.boot.verifiedbootstate",
                    timeout=20.0,
                )
                text = props.stdout + props.stderr
                append_log(log_path, "twrp_props:")
                append_log(log_path, text)
                if "twrp=3.7.0_12-1_afaneh92" in text and "device=g0q" in text:
                    return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(1.0)


def poll_android_after_magisk(wait_sec: int, log_path: Path) -> int:
    deadline = time.monotonic() + wait_sec
    while True:
        rows = adb_rows(log_path, "wait-android")
        if len(rows) > 1:
            raise SystemExit(f"refusing ambiguous ADB rows while waiting for Android: {rows}")
        if len(rows) == 1 and rows[0][1] == "device":
            props = adb_shell(
                "printf 'boot_completed='; getprop sys.boot_completed; "
                "printf 'model='; getprop ro.product.model; "
                "printf 'device='; getprop ro.product.device; "
                "printf 'bootloader='; getprop ro.boot.bootloader; "
                "printf 'incremental='; getprop ro.build.version.incremental; "
                "printf 'vbstate='; getprop ro.boot.verifiedbootstate; "
                "printf 'boot_recovery='; getprop ro.boot.boot_recovery; "
                "printf 'su='; command -v su || true; "
                "printf 'su_v='; su -v 2>/dev/null || true",
                timeout=20.0,
            )
            text = props.stdout + props.stderr
            append_log(log_path, "post_magisk_props:")
            append_log(log_path, text)
            if all(
                item in text
                for item in (
                    "boot_completed=1",
                    "model=SM-S906N",
                    "device=g0q",
                    "bootloader=S906NKSS7FYG8",
                    "incremental=S906NKSS7FYG8",
                    "boot_recovery=0",
                )
            ):
                root = adb_shell("su -c id", timeout=20.0)
                append_log(log_path, f"su_id_rc={root.returncode}")
                append_log(log_path, root.stdout + root.stderr)
                if root.returncode == 0 and "uid=0(root)" in (root.stdout + root.stderr):
                    return 0
                return 10
        if time.monotonic() >= deadline:
            return 20
        time.sleep(1.0)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--twrp-tar", type=Path, default=DEFAULT_TWRP_TAR)
    parser.add_argument("--magisk-ap", type=Path, default=DEFAULT_MAGISK_AP)
    parser.add_argument("--stock-recovery-ap", type=Path, default=DEFAULT_STOCK_RECOVERY_AP)
    parser.add_argument("--stock-boot-ap", type=Path, default=DEFAULT_STOCK_BOOT_AP)
    parser.add_argument("--full-fw", type=Path, default=DEFAULT_FULL_FW)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--twrp-wait-sec", type=int, default=240)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--ack", help=f"required with --live: {ACK_TOKEN}")
    args = parser.parse_args(argv)

    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_twrp_magisk_restore_window.txt"
    append_log(log_path, f"=== {utc_now()} s22plus twrp magisk restore window ===")

    twrp_tar = resolve(root, args.twrp_tar)
    magisk_ap = resolve(root, args.magisk_ap)
    stock_recovery_ap = resolve(root, args.stock_recovery_ap)
    stock_boot_ap = resolve(root, args.stock_boot_ap)
    full_fw = resolve(root, args.full_fw)
    odin = resolve(root, args.odin)

    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")
    verify_tar(twrp_tar, EXPECTED_TWRP_TAR_SHA256, EXPECTED_TWRP_MEMBER, "twrp_tar", log_path)
    verify_tar(magisk_ap, EXPECTED_MAGISK_AP_SHA256, EXPECTED_MAGISK_MEMBER, "magisk_ap", log_path)
    verify_tar(
        stock_recovery_ap,
        EXPECTED_STOCK_RECOVERY_AP_SHA256,
        EXPECTED_STOCK_RECOVERY_MEMBER,
        "stock_recovery_ap",
        log_path,
    )
    verify_tar(stock_boot_ap, EXPECTED_STOCK_BOOT_AP_SHA256, EXPECTED_STOCK_BOOT_MEMBER, "stock_boot_ap", log_path)
    verify_file_sha(full_fw, EXPECTED_FULL_FW_SHA256, "full_firmware_zip", log_path)
    require_single_android_preflight(log_path)

    if not args.live:
        print(f"dry-run ok: artifacts and Android preflight verified; log={log_path}")
        return 0
    if args.ack != ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {ACK_TOKEN}")

    reboot_download = run(["adb", "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_1_rc={reboot_download.returncode}")
    append_log(log_path, reboot_download.stdout + reboot_download.stderr)
    odin_device = wait_for_odin(odin, args.odin_wait_sec, log_path)
    if odin_device is None:
        print("download mode did not appear before TWRP flash", file=sys.stderr)
        return 2

    twrp_cmd = [odin, "-a", twrp_tar, "-d", odin_device]
    append_log(log_path, f"twrp_cmd={' '.join(str(part) for part in twrp_cmd)}")
    twrp = run(twrp_cmd, timeout=180.0)
    append_log(log_path, f"twrp_odin_rc={twrp.returncode}")
    append_log(log_path, twrp.stdout + twrp.stderr)
    if twrp.returncode != 0:
        print(f"TWRP Odin flash failed rc={twrp.returncode}; see {log_path}", file=sys.stderr)
        return twrp.returncode or 3

    print("TWRP transfer complete. Boot the phone directly into recovery now; waiting for TWRP ADB...")
    twrp_ok = wait_for_twrp(args.twrp_wait_sec, log_path)
    append_log(log_path, f"twrp_proof={int(twrp_ok)}")
    if not twrp_ok:
        print(f"TWRP proof did not appear; stopping before Magisk. log={log_path}", file=sys.stderr)
        return 4

    reboot_download_2 = run(["adb", "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_2_rc={reboot_download_2.returncode}")
    append_log(log_path, reboot_download_2.stdout + reboot_download_2.stderr)
    odin_device = wait_for_odin(odin, args.odin_wait_sec, log_path)
    if odin_device is None:
        print("download mode did not appear before Magisk flash", file=sys.stderr)
        return 5

    magisk_cmd = [odin, "--reboot", "-a", magisk_ap, "-d", odin_device]
    append_log(log_path, f"magisk_cmd={' '.join(str(part) for part in magisk_cmd)}")
    magisk = run(magisk_cmd, timeout=180.0)
    append_log(log_path, f"magisk_odin_rc={magisk.returncode}")
    append_log(log_path, magisk.stdout + magisk.stderr)
    if magisk.returncode != 0:
        print(f"Magisk Odin flash failed rc={magisk.returncode}; see {log_path}", file=sys.stderr)
        return magisk.returncode or 6

    android_result = poll_android_after_magisk(args.android_wait_sec, log_path)
    append_log(log_path, f"post_magisk_result={android_result}")
    if android_result == 0:
        print(f"TWRP proof and Magisk root proof passed; log={log_path}")
        return 0
    if android_result == 10:
        print(f"Android booted with Magisk/su present, but su root policy is pending; log={log_path}")
        return 10
    print(f"Android boot proof failed after Magisk flash; log={log_path}", file=sys.stderr)
    return android_result


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
