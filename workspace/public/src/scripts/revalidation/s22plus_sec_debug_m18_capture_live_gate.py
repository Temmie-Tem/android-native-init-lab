#!/usr/bin/env python3
"""Guarded S22+ sec_debug/MID + M18 boot-only capture gate.

This is the Samsung-sec_debug successor to the retired DTBO/ramoops M18 path.
Host-only modes:

  --offline-check   verify pinned M18/rollback artifacts and inert draft;
  --print-plan      print the attended command sequence.

Device modes require a fresh AGENTS.md exception before Android access:

  default dry-run              verify Android/root, boot hash, and sec_debug MID;
  --live                       flash M18 boot only, observe, rollback, collect;
  --rollback-boot-from-download rollback after operator-entered Download mode.
  --collect-after-rollback     collect retained evidence after confirmed rollback.

The helper never flashes DTBO/vendor_boot/vbmeta/recovery and never writes any
partition other than the boot partition through the pinned Odin AP packages.
"""

from __future__ import annotations

import argparse
import json
import re
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
    EXPECTED_STOCK_BOOT_AP_SHA256,
    ROLLBACK_MAGISK,
    ROLLBACK_STOCK,
    adb_exec_out,
    adb_shell,
    append_log,
    flash_ap,
    host_snapshot,
    repo_root,
    require_current_android,
    resolve,
    sha256_file,
    tar_members,
    utc_now,
    wait_for_odin,
)
from s22plus_m5_usb_acm_live_gate import verify_android_stability
from s22plus_ramoops_dtbo_m18_capture_live_gate import (
    DEFAULT_M18_AP,
    DEFAULT_M18_MANIFEST,
    EXPECTED_BOOT_MEMBER,
    EXPECTED_M18_AP_SHA256,
    EXPECTED_M18_BASE_BOOT_SHA256,
    EXPECTED_M18_BOOT_SHA256,
    EXPECTED_M18_INIT_SHA256,
    EXPECTED_M18_MARKER,
    EXPECTED_M18_MODULE_COUNT,
    EXPECTED_M18_MODULE_LIST_SHA256,
    EXPECTED_M18_SOURCE_SHA256,
    observe_m18,
    reboot_android_to_download,
    verify_current_boot_hash,
    verify_m18_manifest,
    wait_for_android_root,
)
from s22plus_sec_debug_mid_sysrq_gate import (
    DEBUG_LEVEL_CONFIRM_TOKEN,
    assert_sec_debug_mid_state,
    collect_sec_debug_state,
    redact,
    safe_name,
    write_text,
)


EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
LIVE_ACK_TOKEN = "S22PLUS-SECDEBUG-M18-CAPTURE-LIVE-GATE"
ROLLBACK_BOOT_ACK_TOKEN = "S22PLUS-SECDEBUG-M18-ROLLBACK-BOOT-FROM-DOWNLOAD"
POLICY_DRAFT = Path("docs/operations/S22PLUS_SEC_DEBUG_M18_CAPTURE_AGENTS_EXCEPTION_DRAFT_2026-07-08.md")

RETAINED_GREP = (
    "S22_NATIVE_INIT|M18|S22M18FULL|panic|oops|SError|watchdog|qmp|dwc3|"
    "phy|regulator|clk|abort|BUG:|Unable to handle|sec_debug|upload|"
    "ramdump|reset|download|reboot"
)

RETAINED_PATTERNS = (
    EXPECTED_M18_MARKER,
    "S22M18FULL0001",
    "S22_NATIVE_INIT",
    "module_group=full_firststage_usb",
    "Kernel panic",
    "Oops",
    "SError",
    "watchdog",
    "qmp",
    "dwc3",
    "phy-msm",
    "regulator",
    "clk",
    "abort",
    "BUG:",
    "Unable to handle",
    "sec_upload_cause",
    "upload_cause",
    "ramdump",
)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_sec_debug_m18_capture_{stamp}")
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise SystemExit(f"could not allocate unique run directory under {base.parent}")


def verify_ap_member(path: Path, expected_sha: str, expected_member: str, label: str, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"{label} AP missing: {path}")
    actual_sha = sha256_file(path)
    members = tar_members(path)
    append_log(log_path, f"{label}_sha256={actual_sha}")
    append_log(log_path, f"{label}_members={members}")
    if actual_sha != expected_sha:
        raise SystemExit(f"{label} AP SHA mismatch: {actual_sha}")
    if members != [expected_member]:
        raise SystemExit(f"{label} AP must contain exactly {expected_member!r}, got {members!r}")


def required_policy_markers() -> list[str]:
    return [
        "S22+ sec_debug MID M18 capture boot-only",
        "workspace/public/src/scripts/revalidation/s22plus_sec_debug_m18_capture_live_gate.py",
        EXPECTED_TARGET,
        EXPECTED_M18_AP_SHA256,
        EXPECTED_M18_BOOT_SHA256,
        EXPECTED_M18_BASE_BOOT_SHA256,
        EXPECTED_M18_MARKER,
        EXPECTED_MAGISK_AP_SHA256,
        EXPECTED_STOCK_BOOT_AP_SHA256,
        LIVE_ACK_TOKEN,
        ROLLBACK_BOOT_ACK_TOKEN,
        DEBUG_LEVEL_CONFIRM_TOKEN,
        "debug_level=MID",
        "sec_debug",
        "/proc/last_kmsg",
        "boot.img.lz4",
        "boot partition only",
        "manual download-mode",
        "no DTBO",
        "no vendor_boot",
        "no vbmeta",
    ]


def verify_text_markers(text: str, source: str, log_path: Path) -> None:
    normalized = " ".join(text.split())
    missing = [item for item in required_policy_markers() if item not in normalized]
    append_log(log_path, f"{source}_missing={missing}")
    if missing:
        raise SystemExit(f"{source} missing sec_debug M18 capture markers: {missing}")


def verify_policy_draft(root: Path, log_path: Path) -> None:
    draft = root / POLICY_DRAFT
    if not draft.is_file():
        raise SystemExit(f"inert policy draft missing: {draft}")
    verify_text_markers(draft.read_text(encoding="utf-8"), "policy_draft", log_path)


def verify_agents_exception(root: Path, log_path: Path) -> None:
    verify_text_markers((root / "AGENTS.md").read_text(encoding="utf-8"), "agents_exception", log_path)


def scan_payload(payload: bytes) -> dict[str, Any]:
    text = payload.decode("utf-8", errors="replace")
    lower = text.lower()
    hits = {pattern: lower.count(pattern.lower()) for pattern in RETAINED_PATTERNS}
    hits = {key: value for key, value in hits.items() if value}
    marker_found = EXPECTED_M18_MARKER.encode("ascii") in payload
    sysrq_only_panic = "sysrq triggered crash" in lower and not marker_found and "s22_native_init" not in lower
    fatal_without_prior_sysrq = any(
        needle in lower
        for needle in ("kernel panic", "oops", "serror", "unable to handle")
    ) and not sysrq_only_panic
    native_marker_found = bool(marker_found or "s22_native_init" in lower or "s22m18full" in lower)
    native_signal_found = bool(native_marker_found or fatal_without_prior_sysrq)
    return {
        "bytes": len(payload),
        "hit_counts": hits,
        "marker_found": marker_found,
        "native_marker_found": native_marker_found,
        "fatal_without_prior_sysrq": fatal_without_prior_sysrq,
        "sysrq_only_panic": sysrq_only_panic,
        "native_signal_found": native_signal_found,
    }


def collect_m18_retained_evidence(run_dir: Path, log_path: Path, serial: str, label: str) -> dict[str, Any]:
    retained_dir = run_dir / "retained_evidence" / label
    retained_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {
        "label": label,
        "timestamp_utc": utc_now(),
        "pstore": {},
        "last_kmsg": {},
        "marker_found": False,
        "native_signal_found": False,
    }

    listing = adb_shell(
        "su -c 'for f in /sys/fs/pstore/*; do [ -f \"$f\" ] && echo \"${f##*/}\"; done' 2>/dev/null || true",
        serial=serial,
        timeout=20.0,
    )
    raw_names = [line.strip() for line in listing.stdout.splitlines() if line.strip()]
    names = [name for name in raw_names if re.fullmatch(r"[A-Za-z0-9._+-]+", name)]
    append_log(log_path, f"{label}_pstore_files={names}")
    summary["pstore"]["files"] = names
    summary["pstore"]["rejected_files"] = raw_names if raw_names != names else []

    for name in names:
        remote = f"/sys/fs/pstore/{name}"
        result = adb_exec_out(f"cat {remote!r} 2>/dev/null", serial=serial, timeout=20.0)
        payload = result.stdout + result.stderr
        (retained_dir / f"pstore_{safe_name(name)}.bin").write_bytes(payload)
        scan = scan_payload(payload)
        summary["pstore"][name] = {"rc": result.returncode, **scan}
        summary["marker_found"] = bool(summary["marker_found"] or scan["marker_found"])
        summary["native_signal_found"] = bool(summary["native_signal_found"] or scan["native_signal_found"])

    last_kmsg = adb_exec_out("cat /proc/last_kmsg 2>/dev/null || true", serial=serial, timeout=60.0)
    payload = last_kmsg.stdout + last_kmsg.stderr
    (retained_dir / "last_kmsg.bin").write_bytes(payload)
    scan = scan_payload(payload)
    summary["last_kmsg"] = {"rc": last_kmsg.returncode, **scan}
    summary["marker_found"] = bool(summary["marker_found"] or scan["marker_found"])
    summary["native_signal_found"] = bool(summary["native_signal_found"] or scan["native_signal_found"])

    grep = adb_shell(
        f"su -c \"cat /proc/last_kmsg 2>/dev/null | grep -Eai '{RETAINED_GREP}' | head -600 || true\"",
        serial=serial,
        timeout=60.0,
    )
    grep_text = redact(grep.stdout + grep.stderr)
    write_text(retained_dir / "last_kmsg_grep.txt", grep_text)
    summary["last_kmsg_grep"] = {
        "rc": grep.returncode,
        "bytes": len(grep_text.encode("utf-8", errors="replace")),
        "line_count": len([line for line in grep_text.splitlines() if line.strip()]),
    }

    write_text(retained_dir / "summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
    append_log(log_path, f"{label}_retained_summary={json.dumps(summary, sort_keys=True)}")
    return summary


def rollback_boot_and_collect(
    odin: Path,
    boot_rollback_ap: Path,
    stock_rollback_ap: Path,
    run_dir: Path,
    log_path: Path,
    rollback_target: str,
    android_wait_sec: int,
    serial: str | None = None,
) -> tuple[int, str | None, dict[str, Any] | None]:
    device = wait_for_odin(odin, log_path, "secdebug-m18-boot-rollback-wait", 10)
    if device is None:
        raise SystemExit("boot rollback requires exactly one Odin/Download device")
    rc = flash_ap(odin, boot_rollback_ap, device, log_path, f"{rollback_target}_boot_rollback")
    if rc != 0 and rollback_target == ROLLBACK_MAGISK:
        append_log(log_path, "magisk_rollback_failed_attempting_stock_fallback=1")
        fallback = wait_for_odin(odin, log_path, "stock-boot-fallback-wait", 30)
        if fallback:
            rc = flash_ap(odin, stock_rollback_ap, fallback, log_path, "stock_boot_fallback")
    if rc != 0:
        return (rc or 5, None, None)

    android = wait_for_android_root(log_path, android_wait_sec, serial)
    if android is None:
        return (6, None, None)
    verify_current_boot_hash(log_path, android)
    state = collect_sec_debug_state(run_dir, log_path, android, "post_m18_boot_rollback")
    retained = collect_m18_retained_evidence(run_dir, log_path, android, "post_m18_boot_rollback")
    append_log(log_path, f"post_m18_sec_debug_state={json.dumps(state, sort_keys=True)}")
    return (0, android, retained)


def preflight_common(args: argparse.Namespace) -> tuple[Path, Path, Path, Path, Path, Path, Path, Path]:
    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_sec_debug_m18_capture_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus sec_debug MID M18 capture live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    odin = resolve(root, args.odin)
    m18_ap = resolve(root, args.m18_ap)
    m18_manifest = resolve(root, args.m18_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_ap_member(m18_ap, EXPECTED_M18_AP_SHA256, EXPECTED_BOOT_MEMBER, "m18_candidate", log_path)
    verify_m18_manifest(m18_manifest, log_path)
    verify_ap_member(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, EXPECTED_BOOT_MEMBER, "magisk_boot_rollback", log_path)
    verify_ap_member(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, EXPECTED_BOOT_MEMBER, "stock_boot_fallback", log_path)
    return root, run_dir, log_path, odin, m18_ap, m18_manifest, magisk_rollback_ap, stock_rollback_ap


def print_plan(args: argparse.Namespace) -> None:
    print(
        "\n".join(
            [
                "S22+ sec_debug MID M18 capture plan:",
                "1. Ensure SysDump DEBUG LEVEL is MID and device is on the known Magisk boot baseline.",
                "2. Activate the narrow AGENTS.md exception for this helper and hashes only.",
                "3. Dry-run:",
                "   PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_sec_debug_m18_capture_live_gate.py",
                "4. Live boot-only flash:",
                "   PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_sec_debug_m18_capture_live_gate.py \\",
                f"     --live --ack {LIVE_ACK_TOKEN} --confirm-debug-level-mid {DEBUG_LEVEL_CONFIRM_TOKEN}",
                "5. If M18 leaves the phone in panic/upload or no transport, enter Download mode manually, then:",
                "   PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_sec_debug_m18_capture_live_gate.py \\",
                f"     --rollback-boot-from-download --ack {ROLLBACK_BOOT_ACK_TOKEN}",
                "6. Expected artifact after rollback: retained_evidence/post_m18_boot_rollback/last_kmsg.bin.",
                "Scope: boot partition only; no DTBO, no vendor_boot, no vbmeta, no recovery.",
                f"M18 AP SHA256: {EXPECTED_M18_AP_SHA256}",
                f"M18 boot SHA256: {EXPECTED_M18_BOOT_SHA256}",
                f"base Magisk boot SHA256: {EXPECTED_M18_BASE_BOOT_SHA256}",
                f"M18 init SHA256: {EXPECTED_M18_INIT_SHA256}",
                f"M18 module-list SHA256: {EXPECTED_M18_MODULE_LIST_SHA256}",
                f"M18 source SHA256: {EXPECTED_M18_SOURCE_SHA256}",
                f"M18 module count: {EXPECTED_M18_MODULE_COUNT}",
                f"Magisk rollback AP SHA256: {EXPECTED_MAGISK_AP_SHA256}",
                f"stock boot fallback AP SHA256: {EXPECTED_STOCK_BOOT_AP_SHA256}",
                f"observe timeout: {args.m18_observe_sec}s",
            ]
        )
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m18-ap", type=Path, default=DEFAULT_M18_AP)
    parser.add_argument("--m18-manifest", type=Path, default=DEFAULT_M18_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial", help="ADB serial to pin before live flashing")
    parser.add_argument("--m18-observe-sec", type=int, default=180)
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    parser.add_argument("--android-stability-samples", type=int, default=4)
    parser.add_argument("--android-stability-interval-sec", type=float, default=3.0)
    parser.add_argument("--rollback-target", choices=[ROLLBACK_MAGISK, ROLLBACK_STOCK], default=ROLLBACK_MAGISK)
    parser.add_argument("--offline-check", action="store_true")
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--rollback-boot-from-download", action="store_true")
    parser.add_argument("--collect-after-rollback", action="store_true")
    parser.add_argument("--ack")
    parser.add_argument("--confirm-debug-level-mid")
    args = parser.parse_args(argv)

    modes = sum(
        1
        for enabled in (
            args.offline_check,
            args.print_plan,
            args.live,
            args.rollback_boot_from_download,
            args.collect_after_rollback,
        )
        if enabled
    )
    if modes > 1:
        raise SystemExit(
            "--offline-check, --print-plan, --live, --rollback-boot-from-download, "
            "and --collect-after-rollback are mutually exclusive"
        )

    root, run_dir, log_path, odin, m18_ap, _m18_manifest, magisk_rollback_ap, stock_rollback_ap = preflight_common(args)

    if args.offline_check:
        verify_policy_draft(root, log_path)
        append_log(log_path, "offline_check=ok device_action=0 agents_exception_checked=0 android_checked=0")
        print(f"offline-check ok: M18 candidate, rollback APs, and inert policy draft verified; log={display_path(log_path)}")
        return 0

    if args.print_plan:
        verify_policy_draft(root, log_path)
        print_plan(args)
        append_log(log_path, "print_plan=ok device_action=0")
        return 0

    verify_agents_exception(root, log_path)

    boot_rollback_ap = magisk_rollback_ap if args.rollback_target == ROLLBACK_MAGISK else stock_rollback_ap

    if args.rollback_boot_from_download:
        if args.ack != ROLLBACK_BOOT_ACK_TOKEN:
            raise SystemExit(f"--rollback-boot-from-download requires --ack {ROLLBACK_BOOT_ACK_TOKEN}")
        rc, android, retained = rollback_boot_and_collect(
            odin,
            boot_rollback_ap,
            stock_rollback_ap,
            run_dir,
            log_path,
            args.rollback_target,
            args.android_wait_sec,
            args.serial,
        )
        signal = bool(retained and retained.get("native_signal_found"))
        print(
            f"M18 rollback-from-download completed rc={rc} android={android} "
            f"native_signal_found={int(signal)}; log={display_path(log_path)}"
        )
        if rc != 0:
            return rc
        return 0 if signal else 10

    if args.collect_after_rollback:
        selected_serial = require_current_android(log_path, args.serial)
        verify_android_stability(
            log_path,
            selected_serial,
            args.android_stability_samples,
            args.android_stability_interval_sec,
        )
        verify_current_boot_hash(log_path, selected_serial)
        state = collect_sec_debug_state(run_dir, log_path, selected_serial, "post_m18_manual_recovery")
        retained = collect_m18_retained_evidence(run_dir, log_path, selected_serial, "post_m18_manual_recovery")
        append_log(log_path, f"post_m18_manual_recovery_sec_debug_state={json.dumps(state, sort_keys=True)}")
        signal = bool(retained.get("native_signal_found"))
        print(
            "M18 post-rollback retained collection completed; "
            f"native_signal_found={int(signal)} marker_found={int(retained.get('marker_found', False))}; "
            f"log={display_path(log_path)}"
        )
        return 0 if signal else 10

    selected_serial = require_current_android(log_path, args.serial)
    verify_android_stability(
        log_path,
        selected_serial,
        args.android_stability_samples,
        args.android_stability_interval_sec,
    )
    verify_current_boot_hash(log_path, selected_serial)
    state = collect_sec_debug_state(run_dir, log_path, selected_serial, "pre_m18_capture")
    assert_sec_debug_mid_state(state, "pre_m18_capture")
    host_snapshot(run_dir, log_path, "dryrun_current", odin)

    if not args.live:
        print(
            "dry-run ok: M18 candidate, rollback APs, AGENTS exception, Android stability, "
            f"boot hash, and sec_debug MID verified; log={display_path(log_path)}"
        )
        return 0

    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")
    if args.confirm_debug_level_mid != DEBUG_LEVEL_CONFIRM_TOKEN:
        raise SystemExit(f"--live requires --confirm-debug-level-mid {DEBUG_LEVEL_CONFIRM_TOKEN}")

    reboot_android_to_download(selected_serial, log_path, "m18_candidate")
    device = wait_for_odin(odin, log_path, "m18-candidate-wait", args.odin_wait_sec)
    if device is None:
        print("download mode did not appear for M18 candidate flash", file=sys.stderr)
        return 2
    rc = flash_ap(odin, m18_ap, device, log_path, "m18_candidate")
    if rc != 0:
        print(f"M18 candidate Odin flash failed rc={rc}; log={display_path(log_path)}", file=sys.stderr)
        return rc or 3

    observed, endpoint = observe_m18(run_dir, log_path, args.m18_observe_sec, odin)
    if observed == "adb" and endpoint:
        append_log(log_path, f"m18_unexpected_adb_returned={endpoint}")
        reboot_android_to_download(endpoint, log_path, "m18_unexpected_adb_rollback")
        endpoint = wait_for_odin(odin, log_path, "m18-unexpected-adb-rollback-wait", args.odin_wait_sec)
        observed = "odin" if endpoint else "none"
    if observed == "acm":
        append_log(log_path, f"m18_result=acm_seen endpoint={endpoint}")
        print(
            "M18 ACM appeared. Enter Download mode manually for boot rollback, then run "
            "--rollback-boot-from-download.",
            file=sys.stderr,
        )
        return 4
    if observed != "odin" or endpoint is None:
        append_log(log_path, "m18_result=no_rollback_transport_manual_download_required")
        print(
            "M18 did not expose rollback transport. Enter Download mode manually and run "
            "--rollback-boot-from-download.",
            file=sys.stderr,
        )
        return 4

    rc = flash_ap(odin, boot_rollback_ap, endpoint, log_path, f"{args.rollback_target}_boot_rollback")
    if rc != 0 and args.rollback_target == ROLLBACK_MAGISK:
        append_log(log_path, "magisk_rollback_failed_attempting_stock_fallback=1")
        fallback = wait_for_odin(odin, log_path, "stock-boot-fallback-wait", 30)
        if fallback:
            rc = flash_ap(odin, stock_rollback_ap, fallback, log_path, "stock_boot_fallback")
    if rc != 0:
        return rc or 5

    android = wait_for_android_root(log_path, args.android_wait_sec)
    if android is None:
        return 6
    verify_current_boot_hash(log_path, android)
    post_state = collect_sec_debug_state(run_dir, log_path, android, "post_m18_boot_rollback")
    retained = collect_m18_retained_evidence(run_dir, log_path, android, "post_m18_boot_rollback")
    append_log(log_path, f"post_m18_sec_debug_state={json.dumps(post_state, sort_keys=True)}")
    signal = bool(retained.get("native_signal_found"))
    print(
        "sec_debug MID M18 capture live gate completed; "
        f"native_signal_found={int(signal)} marker_found={int(retained.get('marker_found', False))}; "
        f"log={display_path(log_path)}"
    )
    return 0 if signal else 10


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
