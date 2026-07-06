#!/usr/bin/env python3
"""Guarded S22+ M3 observable native-init live gate.

Dry-run is the default.  Live mode requires:

- the exact SHA-pinned M3 AGENTS.md exception;
- exact M3 boot-only AP hash and single `boot.img.lz4` tar member;
- exact pinned Magisk boot-only rollback AP and stock boot-only fallback AP;
- a single normal Android ADB target matching SM-S906N/g0q/S906NKSS7FYG8;
- an explicit ack token.

The live path is attended by design: after the M3 candidate is flashed, the
helper observes host-side USB/ADB/Odin state for a bounded window. M3 v0.2 then
attempts a software `download` reboot itself; if that does not appear, the
operator must put the phone back into download mode for rollback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ACK_TOKEN = "S22PLUS-M3-OBSERVABLE-LIVE-GATE"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_MODEL = "SM-S906N"
EXPECTED_DEVICE = "g0q"
EXPECTED_BUILD = "S906NKSS7FYG8"
EXPECTED_MEMBER = "boot.img.lz4"

EXPECTED_M3_AP_SHA256 = "4a07a5b24101db6e74e102498c557d457c751e13d932f9f5604125629f06ce3b"
EXPECTED_M3_BOOT_SHA256 = "aa66602e49045de5666b390ef7b434e07cd234d59a4503f9bac021d11383f6d0"
EXPECTED_M3_MARKER = "S22_NATIVE_INIT_OBSERVABLE_M3"

EXPECTED_MAGISK_AP_SHA256 = "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56"
EXPECTED_STOCK_BOOT_AP_SHA256 = "1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e"

DEFAULT_M3_AP = Path("workspace/private/outputs/s22plus_native_init/observable_m3_v0_2/odin4/AP.tar.md5")
DEFAULT_M3_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/observable_m3_v0_2/manifest.json")
DEFAULT_MAGISK_ROLLBACK_AP = Path("workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5")
DEFAULT_STOCK_ROLLBACK_AP = Path("workspace/private/outputs/s22plus_native_init/odin4_stock_rollback_short/AP.tar.md5")
DEFAULT_ODIN = Path("/usr/bin/odin4")
DEFAULT_RUN_ROOT = Path("workspace/private/runs")
ROLLBACK_MAGISK = "magisk"
ROLLBACK_STOCK = "stock"
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


def run_bytes(argv: list[str | Path], *, timeout: float | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(part) for part in argv],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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
        run_dir = DEFAULT_RUN_ROOT / f"s22plus_m3_observable_live_gate_{stamp}"
    run_dir = resolve(root, run_dir)
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def verify_ap(path: Path, expected_sha: str, label: str, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"{label} AP missing: {path}")
    actual_sha = sha256_file(path)
    members = tar_members(path)
    append_log(log_path, f"{label}_sha256={actual_sha}")
    append_log(log_path, f"{label}_members={members}")
    if actual_sha != expected_sha:
        raise SystemExit(f"{label} AP SHA mismatch: {actual_sha}")
    if members != [EXPECTED_MEMBER]:
        raise SystemExit(f"{label} AP must contain exactly {EXPECTED_MEMBER!r}, got {members!r}")


def verify_m3_manifest(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"M3 manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes = data.get("hashes", {})
    safety = data.get("safety", {})
    tar_members_seen = data.get("tar_members")
    append_log(log_path, f"m3_manifest_path={path}")
    append_log(log_path, f"m3_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"m3_manifest_safety={json.dumps(safety, sort_keys=True)}")
    if hashes.get("ap_tar_md5") != EXPECTED_M3_AP_SHA256:
        raise SystemExit("M3 manifest AP hash does not match expected M3 AP")
    if hashes.get("boot_img") != EXPECTED_M3_BOOT_SHA256:
        raise SystemExit("M3 manifest boot image hash does not match expected M3 boot image")
    if tar_members_seen != [EXPECTED_MEMBER]:
        raise SystemExit(f"M3 manifest tar members mismatch: {tar_members_seen!r}")
    if safety.get("auto_reboot") != "download-after-observation":
        raise SystemExit(f"M3 manifest auto_reboot mismatch: {safety.get('auto_reboot')!r}")
    module_summary = data.get("module_summary", {})
    if module_summary.get("module_count") != 26:
        raise SystemExit(f"M3 manifest module count mismatch: {module_summary.get('module_count')!r}")


def verify_agents_exception(root: Path, log_path: Path) -> None:
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    normalized = " ".join(agents.split())
    required = [
        "S22+ M3 observable native-init boot-only",
        EXPECTED_M3_AP_SHA256,
        EXPECTED_M3_BOOT_SHA256,
        ACK_TOKEN,
        "ncm.0 link-only",
        "`download` reboot",
    ]
    missing = [item for item in required if item not in normalized]
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing M3 live authorization markers: {missing}")


def odin_devices(odin: Path, log_path: Path, label: str) -> list[str]:
    result = run([odin, "-l"], timeout=10.0)
    output = result.stdout + result.stderr
    devices = sorted(set(ODIN_DEVICE_RE.findall(output)))
    append_log(log_path, f"[{utc_now()}] {label} odin4 -l rc={result.returncode} devices={devices}")
    append_log(log_path, output)
    return devices


def adb_rows(log_path: Path, label: str, serial: str | None = None) -> list[tuple[str, str, str]]:
    argv: list[str | Path] = ["adb"]
    if serial:
        argv.extend(["-s", serial])
    argv.extend(["devices", "-l"])
    result = run(argv, timeout=10.0)
    output = result.stdout + result.stderr
    append_log(log_path, f"[{utc_now()}] {label} {' '.join(str(a) for a in argv)} rc={result.returncode}")
    append_log(log_path, output)
    rows: list[tuple[str, str, str]] = []
    for line in output.splitlines()[1:]:
        parts = line.split(maxsplit=2)
        if len(parts) >= 2:
            rows.append((parts[0], parts[1], parts[2] if len(parts) > 2 else ""))
    return rows


def adb_shell(command: str, *, serial: str | None = None, timeout: float = 20.0) -> subprocess.CompletedProcess[str]:
    argv: list[str | Path] = ["adb"]
    if serial:
        argv.extend(["-s", serial])
    argv.extend(["shell", command])
    return run(argv, timeout=timeout)


def adb_exec_out(command: str, *, serial: str | None = None, timeout: float = 20.0) -> subprocess.CompletedProcess[bytes]:
    argv: list[str | Path] = ["adb"]
    if serial:
        argv.extend(["-s", serial])
    argv.extend(["exec-out", "su", "-c", command])
    return run_bytes(argv, timeout=timeout)


def require_current_android(log_path: Path, serial: str | None) -> str:
    rows = adb_rows(log_path, "android-preflight", serial)
    usable = [row for row in rows if row[1] == "device"]
    if serial:
        usable = [row for row in usable if row[0] == serial]
    if len(usable) != 1:
        raise SystemExit(f"expected exactly one Android ADB device, got {usable!r}")
    selected_serial = usable[0][0]
    props = adb_shell(
        "printf 'model='; getprop ro.product.model; "
        "printf 'device='; getprop ro.product.device; "
        "printf 'bootloader='; getprop ro.boot.bootloader; "
        "printf 'incremental='; getprop ro.build.version.incremental; "
        "printf 'vbstate='; getprop ro.boot.verifiedbootstate; "
        "printf 'boot_recovery='; getprop ro.boot.boot_recovery; "
        "printf 'boot_completed='; getprop sys.boot_completed; "
        "printf 'su_id='; su -c id 2>/dev/null || true",
        serial=selected_serial,
        timeout=25.0,
    )
    text = props.stdout + props.stderr
    append_log(log_path, "android_preflight_props:")
    append_log(log_path, text)
    required = [
        f"model={EXPECTED_MODEL}",
        f"device={EXPECTED_DEVICE}",
        f"bootloader={EXPECTED_BUILD}",
        f"incremental={EXPECTED_BUILD}",
        "vbstate=orange",
        "boot_recovery=0",
        "boot_completed=1",
    ]
    missing = [item for item in required if item not in text]
    if missing:
        raise SystemExit(f"Android preflight mismatch: {missing}")
    return selected_serial


def host_snapshot(run_dir: Path, log_path: Path, label: str, odin: Path) -> dict[str, Any]:
    snapshot_dir = run_dir / "host_observation"
    snapshot_dir.mkdir(exist_ok=True)
    result: dict[str, Any] = {"label": label, "timestamp_utc": utc_now()}
    commands: list[tuple[str, list[str | Path], float]] = [
        ("ip_link_json", ["ip", "-j", "link"], 10.0),
        ("ip_addr_json", ["ip", "-j", "addr"], 10.0),
        ("adb_devices_l", ["adb", "devices", "-l"], 10.0),
        ("odin_l", [odin, "-l"], 10.0),
        ("dmesg_tail", ["bash", "-lc", "dmesg -T 2>/dev/null | tail -n 240 || true"], 10.0),
    ]
    for name, argv, timeout in commands:
        if name == "odin_l":
            odin_path = Path(argv[0])
            if not odin_path.exists():
                continue
        completed = run(argv, timeout=timeout)
        text = completed.stdout + completed.stderr
        (snapshot_dir / f"{label}_{name}.txt").write_text(text, encoding="utf-8", errors="replace")
        result[name] = {"rc": completed.returncode, "bytes": len(text.encode("utf-8", errors="replace"))}
    append_log(log_path, f"host_snapshot={json.dumps(result, sort_keys=True)}")
    return result


def collect_android_pstore(
    run_dir: Path,
    log_path: Path,
    label: str,
    serial: str | None = None,
    marker: str = EXPECTED_M3_MARKER,
) -> bool:
    pstore_dir = run_dir / "android_pstore"
    pstore_dir.mkdir(exist_ok=True)
    listing = adb_shell(
        "su -c 'for f in /sys/fs/pstore/*; do [ -f \"$f\" ] && echo \"${f##*/}\"; done' 2>/dev/null || true",
        serial=serial,
        timeout=20.0,
    )
    raw_names = [line.strip() for line in listing.stdout.splitlines() if line.strip()]
    names = [name for name in raw_names if re.fullmatch(r"[A-Za-z0-9._+-]+", name)]
    append_log(log_path, f"{label}_pstore_files={names}")
    if raw_names != names:
        append_log(log_path, f"{label}_pstore_rejected_names={raw_names}")

    marker_found = False
    for name in names:
        remote = f"/sys/fs/pstore/{name}"
        result = adb_exec_out(f"cat {shlex.quote(remote)} 2>/dev/null", serial=serial, timeout=20.0)
        payload = result.stdout + result.stderr
        out_path = pstore_dir / f"{label}_{name}.bin"
        out_path.write_bytes(payload)
        if marker.encode("ascii") in payload:
            marker_found = True
    append_log(log_path, f"{label}_pstore_marker_found={int(marker_found)}")

    last_kmsg = adb_exec_out("cat /proc/last_kmsg 2>/dev/null || true", serial=serial, timeout=45.0)
    last_kmsg_payload = last_kmsg.stdout + last_kmsg.stderr
    (pstore_dir / f"{label}_last_kmsg.bin").write_bytes(last_kmsg_payload)
    last_kmsg_marker_found = marker.encode("ascii") in last_kmsg_payload
    append_log(log_path, f"{label}_last_kmsg_rc={last_kmsg.returncode}")
    append_log(log_path, f"{label}_last_kmsg_bytes={len(last_kmsg_payload)}")
    append_log(log_path, f"{label}_last_kmsg_marker_found={int(last_kmsg_marker_found)}")
    marker_found = marker_found or last_kmsg_marker_found
    append_log(log_path, f"{label}_retained_marker_found={int(marker_found)}")
    return marker_found


def ip_link_names(run_dir: Path, label: str) -> set[str]:
    path = run_dir / "host_observation" / f"{label}_ip_link_json.txt"
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return set()
    names = set()
    for item in data:
        name = item.get("ifname")
        if isinstance(name, str):
            names.add(name)
    return names


def observe_candidate(run_dir: Path, log_path: Path, seconds: int, odin: Path) -> None:
    host_snapshot(run_dir, log_path, "before_candidate", odin)
    before = ip_link_names(run_dir, "before_candidate")
    deadline = time.monotonic() + seconds
    iteration = 0
    while time.monotonic() < deadline:
        iteration += 1
        label = f"candidate_{iteration:03d}"
        host_snapshot(run_dir, log_path, label, odin)
        current = ip_link_names(run_dir, label)
        added = sorted(current - before)
        if added:
            append_log(log_path, f"candidate_new_links={added}")
        time.sleep(2.0)


def wait_for_odin(odin: Path, log_path: Path, label: str, wait_sec: int) -> str | None:
    deadline = time.monotonic() + wait_sec
    while True:
        devices = odin_devices(odin, log_path, label)
        if len(devices) == 1:
            return devices[0]
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices: {devices}")
        if time.monotonic() >= deadline:
            return None
        time.sleep(1.0)


def flash_ap(odin: Path, ap: Path, device: str, log_path: Path, label: str) -> int:
    cmd = [odin, "--reboot", "-a", ap, "-d", device]
    append_log(log_path, f"{label}_cmd={' '.join(str(part) for part in cmd)}")
    result = run(cmd, timeout=240.0)
    append_log(log_path, f"{label}_odin_rc={result.returncode}")
    append_log(log_path, result.stdout + result.stderr)
    return result.returncode


def poll_android(log_path: Path, wait_sec: int, expect_root: bool, serial: str | None = None) -> str | None:
    deadline = time.monotonic() + wait_sec
    while True:
        rows = adb_rows(log_path, "post-rollback-android", serial)
        usable = [row for row in rows if row[1] == "device"]
        if len(usable) == 1:
            selected = usable[0][0]
            props = adb_shell(
                "printf 'boot_completed='; getprop sys.boot_completed; "
                "printf 'model='; getprop ro.product.model; "
                "printf 'device='; getprop ro.product.device; "
                "printf 'bootloader='; getprop ro.boot.bootloader; "
                "printf 'incremental='; getprop ro.build.version.incremental; "
                "printf 'vbstate='; getprop ro.boot.verifiedbootstate; "
                "printf 'boot_recovery='; getprop ro.boot.boot_recovery; "
                "printf 'su_id='; su -c id 2>/dev/null || true",
                serial=selected,
                timeout=25.0,
            )
            text = props.stdout + props.stderr
            append_log(log_path, "post_rollback_props:")
            append_log(log_path, text)
            required = [
                "boot_completed=1",
                f"model={EXPECTED_MODEL}",
                f"device={EXPECTED_DEVICE}",
                f"bootloader={EXPECTED_BUILD}",
                f"incremental={EXPECTED_BUILD}",
                "boot_recovery=0",
            ]
            if all(item in text for item in required):
                if expect_root and "uid=0(root)" not in text:
                    append_log(log_path, "post_rollback_root_missing=1")
                    return None
                return selected
        if time.monotonic() >= deadline:
            return None
        time.sleep(2.0)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m3-ap", type=Path, default=DEFAULT_M3_AP)
    parser.add_argument("--m3-manifest", type=Path, default=DEFAULT_M3_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial", help="ADB serial to pin before live flashing")
    parser.add_argument("--candidate-observe-sec", type=int, default=110)
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--rollback-wait-sec", type=int, default=240)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    parser.add_argument("--rollback-target", choices=[ROLLBACK_MAGISK, ROLLBACK_STOCK], default=ROLLBACK_MAGISK)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--ack", help=f"required with --live: {ACK_TOKEN}")
    args = parser.parse_args(argv)

    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_m3_observable_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus m3 observable live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    odin = resolve(root, args.odin)
    m3_ap = resolve(root, args.m3_ap)
    m3_manifest = resolve(root, args.m3_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_agents_exception(root, log_path)
    verify_ap(m3_ap, EXPECTED_M3_AP_SHA256, "m3_candidate", log_path)
    verify_m3_manifest(m3_manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)
    selected_serial = require_current_android(log_path, args.serial)
    host_snapshot(run_dir, log_path, "dryrun_current", odin)

    if not args.live:
        print(f"dry-run ok: M3 candidate, rollback APs, AGENTS exception, and Android preflight verified; log={log_path}")
        return 0
    if args.ack != ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {ACK_TOKEN}")

    reboot = run(["adb", "-s", selected_serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
    if odin_device is None:
        print("download mode did not appear for candidate flash", file=sys.stderr)
        return 2

    candidate_rc = flash_ap(odin, m3_ap, odin_device, log_path, "candidate")
    if candidate_rc != 0:
        print(f"M3 candidate Odin flash failed rc={candidate_rc}; log={log_path}", file=sys.stderr)
        return candidate_rc or 3

    observe_candidate(run_dir, log_path, args.candidate_observe_sec, odin)
    print(
        "M3 observation window ended. Waiting for M3's software download reboot; "
        "if it does not appear, put the phone into download mode for rollback."
    )
    rollback_device = wait_for_odin(odin, log_path, "rollback-wait", args.rollback_wait_sec)
    if rollback_device is None:
        print(f"rollback download mode did not appear; manual recovery required. log={log_path}", file=sys.stderr)
        return 4

    rollback_ap = magisk_rollback_ap if args.rollback_target == ROLLBACK_MAGISK else stock_rollback_ap
    rollback_label = f"{args.rollback_target}_rollback"
    rollback_rc = flash_ap(odin, rollback_ap, rollback_device, log_path, rollback_label)
    if rollback_rc != 0 and args.rollback_target == ROLLBACK_MAGISK:
        append_log(log_path, "magisk_rollback_failed_attempting_stock_fallback=1")
        fallback_device = wait_for_odin(odin, log_path, "stock-fallback-wait", 30)
        if fallback_device:
            rollback_rc = flash_ap(odin, stock_rollback_ap, fallback_device, log_path, "stock_fallback")
    if rollback_rc != 0:
        print(f"rollback Odin flash failed rc={rollback_rc}; log={log_path}", file=sys.stderr)
        return rollback_rc or 5

    expect_root = args.rollback_target == ROLLBACK_MAGISK
    post_rollback_serial = poll_android(log_path, args.android_wait_sec, expect_root=expect_root)
    android_ok = post_rollback_serial is not None
    append_log(log_path, f"post_rollback_android_ok={int(android_ok)} expect_root={int(expect_root)}")
    if not android_ok:
        print(f"rollback transferred but Android/root verification failed; log={log_path}", file=sys.stderr)
        return 6
    collect_android_pstore(run_dir, log_path, "post_rollback", post_rollback_serial)
    print(f"M3 live gate completed with rollback ok; log={log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
