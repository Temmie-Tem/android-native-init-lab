#!/usr/bin/env python3
"""Guarded S22+ M10A4 inline probe reboot native-init live gate.

Default dry-run and live modes require a SHA-pinned AGENTS.md exception plus a
recovered rooted Android baseline. --offline-check verifies only the host-built
M10A4 package and rollback APs without touching any device.

M10A4 is a lower-layer discriminator, not a module or USB proof. It keeps
inline stack work in _start, removes the separate no-syscall probe helper
call/return used by M10A3, then calls reboot("download"). A later Odin endpoint
is still manually ambiguous: the helper can observe and rollback from download
mode, but only the operator can confirm whether download mode was automatic or
manually entered.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from s22plus_m3_observable_live_gate import (
    DEFAULT_MAGISK_ROLLBACK_AP,
    DEFAULT_ODIN,
    DEFAULT_RUN_ROOT,
    DEFAULT_STOCK_ROLLBACK_AP,
    EXPECTED_MAGISK_AP_SHA256,
    EXPECTED_MEMBER,
    EXPECTED_STOCK_BOOT_AP_SHA256,
    ROLLBACK_MAGISK,
    ROLLBACK_STOCK,
    adb_rows,
    append_log,
    collect_android_pstore,
    flash_ap,
    host_snapshot,
    odin_devices,
    poll_android,
    repo_root,
    require_current_android,
    resolve,
    run,
    utc_now,
    verify_ap,
    wait_for_odin,
)
from s22plus_m5_usb_acm_live_gate import (
    verify_android_stability,
    verify_current_boot_hash,
)


LIVE_ACK_TOKEN = "S22PLUS-M10A4-INLINE-PROBE-REBOOT-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-M10A4-ROLLBACK-FROM-DOWNLOAD"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_M10A4_AP_SHA256 = "a4d7c9d05536d22c3f56bd1891a7fbc0c8fa6d3500cf8b1036e11bd0c9569c26"
EXPECTED_M10A4_BOOT_SHA256 = "38986a19454d7fd49e8860d025ad4241e2c130b5fc28956bed892c26842fb3a9"
EXPECTED_M10A4_BASE_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_M10A4_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_M10A4_INIT_SHA256 = "d70c794979bc16f12917871f5e6e7b2231569f72682a5f6ebcd87f901a11837b"
EXPECTED_M10A4_SOURCE_SHA256 = "2d168c28dbdef67bedc7d9d39250c7e61c928daf89a2b973616534453a835a84"
EXPECTED_M10A4_RETAINED_MARKER = "S22_NATIVE_INIT_M10A4_NO_RETAINED_MARKER_EXPECTED"

DEFAULT_M10A4_AP = Path("workspace/private/outputs/s22plus_native_init/inplace_m10a4_inline_probe_reboot_v0_1/odin4/AP.tar.md5")
DEFAULT_M10A4_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/inplace_m10a4_inline_probe_reboot_v0_1/manifest.json")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_m10a4_inline_probe_reboot_live_gate_{stamp}")
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise SystemExit(f"could not allocate unique run directory under {base.parent}")


def verify_agents_exception(root: Path, log_path: Path) -> None:
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    normalized = " ".join(agents.split())
    required = [
        "S22+ M10A4 inline-probe reboot native-init boot-only",
        EXPECTED_M10A4_AP_SHA256,
        EXPECTED_M10A4_BOOT_SHA256,
        EXPECTED_M10A4_BASE_BOOT_SHA256,
        EXPECTED_M10A4_KERNEL_SHA256,
        EXPECTED_M10A4_INIT_SHA256,
        EXPECTED_M10A4_SOURCE_SHA256,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        "freestanding C raw-syscall runtime",
        "inline stack probe in `_start`",
        "no separate no-syscall probe helper",
        "then one direct `reboot(2)` syscall",
        "no getpid",
        "no pathname access",
        "no VFS",
        "no mkdirat",
        "no marker",
        "no kmsg",
        "no mount",
        "manual-download ambiguity",
        "wait for the original Odin endpoint to disconnect",
        "manual download-mode rollback",
    ]
    missing = [item for item in required if item not in normalized]
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing M10A4 live authorization markers: {missing}")


def verify_m10a4_manifest(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"M10A4 manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes = data.get("hashes", {})
    safety = data.get("safety", {})
    ramdisk = data.get("ramdisk", {})
    init_info = data.get("m10a4_init", {})
    tar_members_seen = data.get("tar_members")
    append_log(log_path, f"m10a4_manifest_path={path}")
    append_log(log_path, f"m10a4_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"m10a4_manifest_safety={json.dumps(safety, sort_keys=True)}")
    append_log(log_path, f"m10a4_manifest_ramdisk={json.dumps(ramdisk, sort_keys=True)}")

    expected_hashes = {
        "ap_tar_md5": EXPECTED_M10A4_AP_SHA256,
        "boot_img": EXPECTED_M10A4_BOOT_SHA256,
        "base_boot": EXPECTED_M10A4_BASE_BOOT_SHA256,
        "kernel": EXPECTED_M10A4_KERNEL_SHA256,
        "m10a4_init": EXPECTED_M10A4_INIT_SHA256,
        "source": EXPECTED_M10A4_SOURCE_SHA256,
        "nochange_repack_boot": EXPECTED_M10A4_BASE_BOOT_SHA256,
    }
    for key, expected in expected_hashes.items():
        if hashes.get(key) != expected:
            raise SystemExit(f"M10A4 manifest hash {key} mismatch: {hashes.get(key)!r} != {expected!r}")
    if tar_members_seen != [EXPECTED_MEMBER]:
        raise SystemExit(f"M10A4 manifest tar members mismatch: {tar_members_seen!r}")

    expected_safety: dict[str, Any] = {
        "boot_only": True,
        "host_only_build": True,
        "live_flash_authorized": False,
        "requires_new_sha_pinned_agents_exception_before_flash": True,
        "base_is_known_booting_magisk_boot": True,
        "construction": "magiskboot unpack/repack; replace only ramdisk /init",
        "runtime": "freestanding-c-raw-syscall",
        "glibc_static_startup": False,
        "mkbootimg_from_scratch": False,
        "no_android_or_magisk_handoff": True,
        "pre_reboot_work": "inline-stack-probe-no-syscall",
        "pre_reboot_helper_call": False,
        "first_runtime_side_effect": "none-before-reboot",
        "first_externally_observable_action": "inline-probe-then-reboot-download",
        "intended_syscall_count": 1,
        "auto_reboot": "download-after-inline-stack-probe",
        "marker_write": False,
        "kmsg_write": False,
        "vfs_setup": "none",
        "vfs_mutation": False,
        "pathname_access": False,
        "getpid": False,
        "mkdirat": False,
        "mknodat": False,
        "mounts": False,
        "sleep_before_reboot": False,
        "host_commanded_reboot_download": False,
        "persistent_partition_mount": False,
        "block_device_writes": False,
        "module_insertions": False,
        "module_binary_injection": False,
        "module_list_files_injected_into_boot_ramdisk": 0,
        "configfs_runtime_gadget": False,
        "udc_binding": False,
        "usb_role_force": False,
        "watchdog": "not-touched",
        "on_reboot_syscall_return": "infinite-park",
    }
    for key, expected in expected_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"M10A4 manifest safety {key} mismatch: {safety.get(key)!r} != {expected!r}")
    if safety.get("intended_syscalls") != ["reboot"]:
        raise SystemExit(f"M10A4 intended syscalls mismatch: {safety.get('intended_syscalls')!r}")

    if ramdisk.get("replaced_entry") != "init":
        raise SystemExit("M10A4 manifest did not replace /init")
    if ramdisk.get("only_intended_entry_change") != "init":
        raise SystemExit("M10A4 manifest intended ramdisk change is not only /init")
    if ramdisk.get("module_files_injected_into_boot_ramdisk") != 0:
        raise SystemExit("M10A4 must not inject vendor module binaries into boot ramdisk")
    if ramdisk.get("module_list_files_injected_into_boot_ramdisk") != 0:
        raise SystemExit("M10A4 must not inject module-list files into boot ramdisk")

    required_strings = set(init_info.get("required_strings", []))
    if "download" not in required_strings:
        raise SystemExit("M10A4 required download string missing from manifest")
    if init_info.get("svc_count") != 1:
        raise SystemExit(f"M10A4 expected one svc instruction, got {init_info.get('svc_count')!r}")
    if init_info.get("branch_targets") != ["0x40010c"]:
        raise SystemExit(f"M10A4 branch target shape mismatch: {init_info.get('branch_targets')!r}")
    if init_info.get("reboot_func_start") != "0x40010c":
        raise SystemExit(f"M10A4 reboot helper start mismatch: {init_info.get('reboot_func_start')!r}")
    forbidden_strings = set(init_info.get("forbidden_strings", []))
    for forbidden in [
        "ld-linux",
        "libc.so",
        "S22_NATIVE_INIT",
        "/dev",
        "/proc",
        "/sys",
        "/run",
        "/lib/modules",
        "getpid",
        "newfstatat",
        "mkdir",
        "mknod",
        "mount",
        "finit_module",
        "modules.load",
        "ttyGS0",
        "ss_acm.0",
        "usb_gadget",
        "/config",
    ]:
        if forbidden not in forbidden_strings:
            raise SystemExit(f"M10A4 forbidden-string gate missing from manifest: {forbidden}")


def wait_for_odin_absent(odin: Path, log_path: Path, label: str, wait_sec: int) -> bool:
    deadline = time.monotonic() + wait_sec
    while True:
        devices = odin_devices(odin, log_path, label)
        if not devices:
            append_log(log_path, f"{label}_odin_absent=1")
            return True
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices while waiting for disconnect: {devices}")
        if time.monotonic() >= deadline:
            append_log(log_path, f"{label}_odin_absent=0 still_present={devices}")
            return False
        time.sleep(1.0)


def observe_until_odin(run_dir: Path, log_path: Path, seconds: int, odin: Path) -> str | None:
    host_snapshot(run_dir, log_path, "after_candidate_flash", odin)
    deadline = time.monotonic() + seconds
    iteration = 0
    while time.monotonic() < deadline:
        iteration += 1
        label = f"m10a4_download_observation_{iteration:03d}"
        host_snapshot(run_dir, log_path, label, odin)
        devices = odin_devices(odin, log_path, f"{label}-extra")
        if len(devices) == 1:
            append_log(log_path, "m10a4_download_endpoint_seen=1")
            append_log(log_path, "m10a4_manual_download_ambiguity=operator-confirmation-required")
            return devices[0]
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices during M10A4 observation: {devices}")
        rows = adb_rows(log_path, f"{label}-extra")
        if rows:
            append_log(log_path, f"m10a4_candidate_adb_rows={rows}")
        time.sleep(1.0)
    append_log(log_path, "m10a4_download_endpoint_seen=0")
    return None


def rollback_from_download(
    odin: Path,
    rollback_ap: Path,
    run_dir: Path,
    log_path: Path,
    rollback_target: str,
    android_wait_sec: int,
) -> int:
    devices = odin_devices(odin, log_path, "rollback-only")
    if len(devices) != 1:
        raise SystemExit(f"rollback-only requires exactly one Odin device, got {devices}")
    rollback_rc = flash_ap(odin, rollback_ap, devices[0], log_path, f"{rollback_target}_rollback")
    if rollback_rc != 0:
        return rollback_rc or 5
    serial = poll_android(log_path, android_wait_sec, expect_root=rollback_target == ROLLBACK_MAGISK)
    if serial is None:
        return 6
    collect_android_pstore(run_dir, log_path, "post_rollback", serial, marker=EXPECTED_M10A4_RETAINED_MARKER)
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m10a4-ap", type=Path, default=DEFAULT_M10A4_AP)
    parser.add_argument("--m10a4-manifest", type=Path, default=DEFAULT_M10A4_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial", help="ADB serial to pin before live flashing")
    parser.add_argument("--download-observation-wait-sec", type=int, default=150)
    parser.add_argument("--post-flash-disconnect-wait-sec", type=int, default=20)
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    parser.add_argument("--android-stability-samples", type=int, default=4)
    parser.add_argument("--android-stability-interval-sec", type=float, default=3.0)
    parser.add_argument("--rollback-target", choices=[ROLLBACK_MAGISK, ROLLBACK_STOCK], default=ROLLBACK_MAGISK)
    parser.add_argument("--offline-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--ack")
    args = parser.parse_args(argv)

    modes = sum(1 for enabled in (args.offline_check, args.live, args.rollback_from_download) if enabled)
    if modes > 1:
        raise SystemExit("--offline-check, --live, and --rollback-from-download are mutually exclusive")

    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_m10a4_inline_probe_reboot_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus m10a4 inline probe reboot live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")
    append_log(log_path, "manual_download_ambiguity_policy=later Odin endpoint is not automatic proof without operator confirmation")

    odin = resolve(root, args.odin)
    m10a4_ap = resolve(root, args.m10a4_ap)
    m10a4_manifest = resolve(root, args.m10a4_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    rollback_ap = magisk_rollback_ap if args.rollback_target == ROLLBACK_MAGISK else stock_rollback_ap
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_ap(m10a4_ap, EXPECTED_M10A4_AP_SHA256, "m10a4_candidate", log_path)
    verify_m10a4_manifest(m10a4_manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)

    if args.offline_check:
        append_log(log_path, "offline_check=ok device_action=0 agents_exception_checked=0 android_checked=0")
        print(f"offline-check ok: M10A4 candidate and rollback APs verified; no device action; log={log_path}")
        return 0

    verify_agents_exception(root, log_path)

    if args.rollback_from_download:
        if args.ack != ROLLBACK_ACK_TOKEN:
            raise SystemExit(f"--rollback-from-download requires --ack {ROLLBACK_ACK_TOKEN}")
        rc = rollback_from_download(odin, rollback_ap, run_dir, log_path, args.rollback_target, args.android_wait_sec)
        print(f"M10A4 rollback-from-download completed rc={rc}; log={log_path}")
        return rc

    selected_serial = require_current_android(log_path, args.serial)
    verify_android_stability(
        log_path,
        selected_serial,
        args.android_stability_samples,
        args.android_stability_interval_sec,
    )
    verify_current_boot_hash(log_path, selected_serial)
    host_snapshot(run_dir, log_path, "dryrun_current", odin)

    if not args.live:
        print(
            "dry-run ok: M10A4 candidate, rollback APs, AGENTS exception, Android stability, "
            f"and boot hash verified; log={log_path}"
        )
        return 0
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    reboot = run(["adb", "-s", selected_serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
    if odin_device is None:
        print("download mode did not appear for M10A4 candidate flash", file=sys.stderr)
        return 2

    candidate_rc = flash_ap(odin, m10a4_ap, odin_device, log_path, "candidate")
    if candidate_rc != 0:
        print(f"M10A4 candidate Odin flash failed rc={candidate_rc}; log={log_path}", file=sys.stderr)
        return candidate_rc or 3

    left_download = wait_for_odin_absent(odin, log_path, "post-candidate-disconnect", args.post_flash_disconnect_wait_sec)
    if not left_download:
        print(
            "M10A4 candidate flash completed but the original Odin device did not disconnect; "
            "rolling back without claiming candidate execution.",
            file=sys.stderr,
        )
        rollback_device = wait_for_odin(odin, log_path, "rollback-still-download-wait", 5)
        if rollback_device is None:
            print(f"rollback download mode unavailable after no-disconnect; manual recovery required. log={log_path}", file=sys.stderr)
            return 4
        rollback_rc = flash_ap(odin, rollback_ap, rollback_device, log_path, f"{args.rollback_target}_rollback_no_disconnect")
        if rollback_rc != 0:
            return rollback_rc or 5
        post_rollback_serial = poll_android(log_path, args.android_wait_sec, expect_root=args.rollback_target == ROLLBACK_MAGISK)
        if post_rollback_serial is None:
            return 6
        append_log(log_path, "m10a4_result=no-proof-original-download-never-disconnected")
        collect_android_pstore(
            run_dir,
            log_path,
            "post_rollback_no_disconnect",
            post_rollback_serial,
            marker=EXPECTED_M10A4_RETAINED_MARKER,
        )
        return 7

    print("M10A4 candidate flashed. Waiting for later download endpoint; operator manual entry would make it ambiguous.")
    rollback_device = observe_until_odin(run_dir, log_path, args.download_observation_wait_sec, odin)
    if rollback_device is None:
        print("M10A4 download endpoint did not appear; enter download mode manually and run --rollback-from-download.", file=sys.stderr)
        return 4

    rollback_rc = flash_ap(odin, rollback_ap, rollback_device, log_path, f"{args.rollback_target}_rollback")
    if rollback_rc != 0 and args.rollback_target == ROLLBACK_MAGISK:
        append_log(log_path, "magisk_rollback_failed_attempting_stock_fallback=1")
        fallback_device = wait_for_odin(odin, log_path, "stock-fallback-wait", 30)
        if fallback_device:
            rollback_rc = flash_ap(odin, stock_rollback_ap, fallback_device, log_path, "stock_fallback")
    if rollback_rc != 0:
        return rollback_rc or 5

    post_rollback_serial = poll_android(log_path, args.android_wait_sec, expect_root=args.rollback_target == ROLLBACK_MAGISK)
    if post_rollback_serial is None:
        return 6
    collect_android_pstore(run_dir, log_path, "post_rollback", post_rollback_serial, marker=EXPECTED_M10A4_RETAINED_MARKER)
    print(
        "M10A4 live gate observed a later download endpoint and rollback ok; "
        f"automatic-vs-manual classification requires operator confirmation. log={log_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
