#!/usr/bin/env python3
"""Guarded S22+ M18 P00 prefix-download live gate.

Default/offline mode performs no device action.  Live mode is inert until a
fresh SHA-pinned AGENTS.md exception is promoted.

M18 P00 loads no modules.  It only proves whether the minimal native-init
runtime reaches the checkpoint and can request Samsung download mode.  The host
must not count the original candidate Odin endpoint as proof; live mode waits
for the original endpoint to disconnect, then treats a later Odin endpoint as
the candidate's self-download result.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    append_log,
    collect_android_pstore,
    flash_ap,
    host_snapshot,
    poll_android,
    repo_root,
    require_current_android,
    resolve,
    run,
    utc_now,
    verify_ap,
    wait_for_odin,
)
from s22plus_m4t3_raw_reboot_live_gate import (
    observe_until_odin,
    rollback_from_download,
    wait_for_odin_absent,
)


LIVE_ACK_TOKEN = "S22PLUS-M18-P00-PREFIX-DOWNLOAD-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-M18-P00-ROLLBACK-FROM-DOWNLOAD"
POLICY_DRAFT = Path("docs/operations/S22PLUS_M18_P00_PREFIX_DOWNLOAD_AGENTS_EXCEPTION_DRAFT_2026-07-08.md")

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_P00_AP_SHA256 = "b79ac94aac341ab5e4c08cb3c568c20be28bb71ccd4f1b047f712bd1dcf5225b"
EXPECTED_P00_BOOT_SHA256 = "f8f362bdd0d0f75ae9ae0ce69d86bcfe47362f246504b02fc6175a4aa0a83133"
EXPECTED_P00_BASE_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_P00_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_P00_INIT_SHA256 = "467947f7ba0c4b4088c9a21a19e5202609b833298f2e95256b1f011eb9af034e"
EXPECTED_P00_SOURCE_SHA256 = "c3a5b970f2d88cb03f10820ce095ed1ad24be75891b8d3cd0dd5b471d8746ccf"
EXPECTED_P00_MODULE_TEXT_SHA256 = "1e00da43ae2b22c56855a28967201733b66b65ec4e91086faa67a4d9b3177fb8"
EXPECTED_P00_MARKER = "S22_NATIVE_INIT_M18_PREFIX_DOWNLOAD"

DEFAULT_P00_AP = Path("workspace/private/outputs/s22plus_native_init/inplace_m18_prefix_download_v0_1/P00/odin4/AP.tar.md5")
DEFAULT_P00_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/inplace_m18_prefix_download_v0_1/P00/manifest.json")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    else:
        stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
        base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_m18_p00_prefix_download_live_gate_{stamp}")
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise SystemExit(f"could not allocate unique run directory under {base.parent}")


def policy_markers() -> list[str]:
    return [
        "S22+ M18 P00 prefix-download native-init boot-only",
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        "workspace/public/src/scripts/revalidation/s22plus_m18_p00_prefix_download_live_gate.py",
        EXPECTED_P00_AP_SHA256,
        EXPECTED_P00_BOOT_SHA256,
        EXPECTED_P00_BASE_BOOT_SHA256,
        EXPECTED_P00_KERNEL_SHA256,
        EXPECTED_P00_INIT_SHA256,
        "P00 loads no modules",
        "wait for the original Odin endpoint to disconnect",
        "later Odin endpoint as the candidate self-download proof",
        "manual download-mode rollback",
        "no ACM",
        "no configfs",
        "no module binary injection",
        "no EUD sysfs write",
    ]


def missing_policy_markers(text: str) -> list[str]:
    normalized = " ".join(text.split())
    return [marker for marker in policy_markers() if marker not in normalized]


def verify_policy_draft(root: Path, log_path: Path) -> None:
    draft = resolve(root, POLICY_DRAFT)
    if not draft.is_file():
        raise SystemExit(f"M18 P00 policy draft missing: {draft}")
    missing = missing_policy_markers(draft.read_text(encoding="utf-8"))
    append_log(log_path, f"policy_draft_missing={missing}")
    if missing:
        raise SystemExit(f"M18 P00 policy draft missing markers: {missing}")


def verify_agents_exception(root: Path, log_path: Path) -> None:
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    missing = missing_policy_markers(agents)
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing M18 P00 live authorization markers: {missing}")


def verify_p00_manifest(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"M18 P00 manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes = data.get("hashes", {})
    safety = data.get("safety", {})
    ramdisk = data.get("ramdisk", {})
    prefix = data.get("prefix", {})
    tar_members_seen = data.get("tar_members")
    append_log(log_path, f"p00_manifest_path={path}")
    append_log(log_path, f"p00_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"p00_manifest_safety={json.dumps(safety, sort_keys=True)}")

    expected_hashes = {
        "ap_tar_md5": EXPECTED_P00_AP_SHA256,
        "boot_img": EXPECTED_P00_BOOT_SHA256,
        "base_boot": EXPECTED_P00_BASE_BOOT_SHA256,
        "kernel": EXPECTED_P00_KERNEL_SHA256,
        "m18_init": EXPECTED_P00_INIT_SHA256,
        "source": EXPECTED_P00_SOURCE_SHA256,
        "m18_power_qmp": EXPECTED_P00_MODULE_TEXT_SHA256,
        "nochange_repack_boot": EXPECTED_P00_BASE_BOOT_SHA256,
    }
    for key, expected in expected_hashes.items():
        if hashes.get(key) != expected:
            raise SystemExit(f"M18 P00 manifest hash {key} mismatch: {hashes.get(key)!r} != {expected!r}")
    if tar_members_seen != [EXPECTED_MEMBER]:
        raise SystemExit(f"M18 P00 tar members mismatch: {tar_members_seen!r}")
    if data.get("target") != EXPECTED_TARGET:
        raise SystemExit("M18 P00 target mismatch")
    if prefix.get("label") != "P00" or prefix.get("count") != 0 or prefix.get("expected_loaded_modules") != []:
        raise SystemExit(f"M18 P00 prefix metadata mismatch: {prefix!r}")

    expected_safety = {
        "boot_only": True,
        "host_only_build": True,
        "live_flash_authorized": False,
        "requires_new_sha_pinned_agents_exception_before_flash": True,
        "base_is_known_booting_magisk_boot": True,
        "construction": "magiskboot unpack/repack; replace ramdisk /init and add one text module list",
        "runtime": "freestanding-raw-syscall",
        "glibc_static_startup": False,
        "mkbootimg_from_scratch": False,
        "no_android_or_magisk_handoff": True,
        "auto_reboot": True,
        "persistent_partition_mount": False,
        "block_device_writes": False,
        "module_binary_injection": False,
        "configfs_runtime_gadget": False,
        "usb_role_force": False,
        "reboot_request": "download",
    }
    for key, expected in expected_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"M18 P00 manifest safety {key} mismatch: {safety.get(key)!r} != {expected!r}")
    if ramdisk.get("replaced_entry") != "init":
        raise SystemExit("M18 P00 did not replace /init")
    if ramdisk.get("added_subset_entry") != "s22plus_m18_power_qmp.modules":
        raise SystemExit("M18 P00 module-list entry mismatch")
    if ramdisk.get("module_files_injected_into_boot_ramdisk") != 0:
        raise SystemExit("M18 P00 must not inject module binaries")
    if ramdisk.get("module_list_files_injected_into_boot_ramdisk") != 1:
        raise SystemExit("M18 P00 must inject exactly one module-list text file")


def verify_offline(root: Path, args: argparse.Namespace, log_path: Path) -> None:
    p00_ap = resolve(root, args.p00_ap)
    p00_manifest = resolve(root, args.p00_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    verify_policy_draft(root, log_path)
    verify_ap(p00_ap, EXPECTED_P00_AP_SHA256, "m18_p00_candidate", log_path)
    verify_p00_manifest(p00_manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p00-ap", type=Path, default=DEFAULT_P00_AP)
    parser.add_argument("--p00-manifest", type=Path, default=DEFAULT_P00_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial")
    parser.add_argument("--self-download-wait-sec", type=int, default=45)
    parser.add_argument("--post-flash-disconnect-wait-sec", type=int, default=20)
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--android-wait-sec", type=int, default=300)
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
    log_path = run_dir / "s22plus_m18_p00_prefix_download_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus m18 p00 prefix-download live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    verify_offline(root, args, log_path)
    if args.offline_check or not args.live and not args.rollback_from_download:
        print(f"offline-check ok: M18 P00 candidate and rollback APs verified; no device action; log={log_path}")
        return 0

    verify_agents_exception(root, log_path)

    odin = resolve(root, args.odin)
    p00_ap = resolve(root, args.p00_ap)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    rollback_ap = magisk_rollback_ap if args.rollback_target == ROLLBACK_MAGISK else stock_rollback_ap
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    if args.rollback_from_download:
        if args.ack != ROLLBACK_ACK_TOKEN:
            raise SystemExit(f"--rollback-from-download requires --ack {ROLLBACK_ACK_TOKEN}")
        rc = rollback_from_download(odin, rollback_ap, run_dir, log_path, args.rollback_target, args.android_wait_sec)
        print(f"M18 P00 rollback-from-download completed rc={rc}; log={log_path}")
        return rc

    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    selected_serial = require_current_android(log_path, args.serial)
    host_snapshot(run_dir, log_path, "pre_live_current", odin)

    reboot = run(["adb", "-s", selected_serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
    if odin_device is None:
        print("download mode did not appear for M18 P00 candidate flash", file=sys.stderr)
        return 2

    candidate_rc = flash_ap(odin, p00_ap, odin_device, log_path, "candidate")
    if candidate_rc != 0:
        print(f"M18 P00 candidate Odin flash failed rc={candidate_rc}; log={log_path}", file=sys.stderr)
        return candidate_rc or 3

    left_download = wait_for_odin_absent(odin, log_path, "post-candidate-disconnect", args.post_flash_disconnect_wait_sec)
    if not left_download:
        print(
            "M18 P00 candidate flash completed but the original Odin device did not disconnect; "
            "rolling back without claiming self-download proof.",
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
        append_log(log_path, "m18_p00_result=no-proof-original-download-never-disconnected")
        collect_android_pstore(run_dir, log_path, "post_rollback_no_disconnect", post_rollback_serial, marker=EXPECTED_P00_MARKER)
        return 7

    print("M18 P00 candidate flashed. Waiting for checkpoint self-download.")
    rollback_device = observe_until_odin(run_dir, log_path, args.self_download_wait_sec, odin)
    if rollback_device is None:
        print("M18 P00 self-download did not appear; enter download mode manually and run --rollback-from-download.", file=sys.stderr)
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
    collect_android_pstore(run_dir, log_path, "post_rollback", post_rollback_serial, marker=EXPECTED_P00_MARKER)
    print(f"M18 P00 live gate completed with self-download and rollback ok; log={log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
