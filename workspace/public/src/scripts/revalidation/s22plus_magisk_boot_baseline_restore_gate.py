#!/usr/bin/env python3
"""Guarded S22+ Magisk boot-baseline restore gate.

This helper is intentionally narrower than the older TWRP+Magisk restore
window.  It restores only the pinned Magisk boot-only AP, then verifies Android
and Magisk root.  It never writes recovery, vbmeta, vendor_boot, dtbo, BL, CP,
CSC, userdata, EFS, or any non-boot partition.

Dry-run/offline mode verifies host artifacts only.  Live mode requires an
active AGENTS.md exception plus an explicit ack token.
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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ACK_TOKEN = "S22PLUS-MAGISK-BOOT-BASELINE-RESTORE-GATE"
EXPECTED_SCHEMA = "s22plus_magisk_boot_baseline_restore_result_v1"
EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_MAGISK_AP_SHA256 = "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56"
EXPECTED_MAGISK_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_MAGISK_LZ4_SHA256 = "b33b63d9d2c56cbe10170820e88cf136be8fe9ad621a21752da19fdd9b642d31"
EXPECTED_MAGISK_MEMBER = "boot.img.lz4"
DISPLAY_SERIAL_REDACTED = "<S22_SERIAL_REDACTED>"

DEFAULT_MAGISK_AP = Path("workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5")
DEFAULT_RUN_ROOT = Path("workspace/private/runs")
DEFAULT_ODIN = Path("/usr/bin/odin4")
ODIN_DEVICE_RE = re.compile(r"/dev/bus/usb/\d+/\d+")
ANDROID_MODEL = "SM-S906N"
ANDROID_DEVICE = "g0q"
ANDROID_INCREMENTAL = "S906NKSS7FYG8"
ANDROID_VBSTATE = "orange"


@dataclass(frozen=True)
class AndroidProof:
    serial: str
    root_path: str
    boot_sha256: str


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").is_dir():
            return parent
    raise RuntimeError(f"could not locate repo root from {current}")


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


def append_log(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_magisk_boot_baseline_restore_{utc_stamp()}")
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise SystemExit(f"could not allocate unique run directory under {base.parent}")


def verify_magisk_ap(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"Magisk boot AP missing: {path}")
    actual_ap_sha = sha256_file(path)
    append_log(log_path, f"magisk_ap_sha256={actual_ap_sha}")
    if actual_ap_sha != EXPECTED_MAGISK_AP_SHA256:
        raise SystemExit(f"Magisk boot AP SHA mismatch: {actual_ap_sha}")
    with tarfile.open(path) as tar:
        members = tar.getmembers()
        names = [member.name for member in members]
        append_log(log_path, f"magisk_ap_members={names}")
        if names != [EXPECTED_MAGISK_MEMBER]:
            raise SystemExit(f"Magisk boot AP must contain exactly {EXPECTED_MAGISK_MEMBER!r}, got {names!r}")
        extracted = tar.extractfile(members[0])
        if extracted is None:
            raise SystemExit(f"could not read {EXPECTED_MAGISK_MEMBER} from {path}")
        member_sha = sha256_bytes(extracted.read())
    append_log(log_path, f"magisk_member_sha256={member_sha}")
    if member_sha != EXPECTED_MAGISK_LZ4_SHA256:
        raise SystemExit(f"Magisk boot AP member SHA mismatch: {member_sha}")


def policy_required_markers() -> list[str]:
    return [
        "S22+ Magisk boot-baseline restore boot-only gate",
        "workspace/public/src/scripts/revalidation/s22plus_magisk_boot_baseline_restore_gate.py",
        ACK_TOKEN,
        EXPECTED_MAGISK_AP_SHA256,
        EXPECTED_MAGISK_BOOT_SHA256,
        EXPECTED_MAGISK_LZ4_SHA256,
        "boot partition only",
        "does not authorize recovery, vendor_boot, vbmeta",
        "dtbo, BL, CP, CSC, super, userdata, EFS, sec_efs, RPMB, keymaster",
        "bootloader, raw host `dd`, fastboot",
    ]


def active_exception_template() -> str:
    return f"""   **Narrow operator-authorized exception (2026-07-10, S22+ Magisk boot-baseline restore boot-only gate):**
   after the M34 S10C0 live HIT was recovered to stock boot and before any
   further S22+ native-init live gate, Codex may perform one bounded attended
   boot-partition-only Magisk measurement-baseline restore on the Samsung S22+
   `SM-S906N`/`g0q` `S906NKSS7FYG8` using only
   `workspace/public/src/scripts/revalidation/s22plus_magisk_boot_baseline_restore_gate.py`.
   Live ack token: `{ACK_TOKEN}`. The helper may flash exactly the pinned
   single-member Magisk boot-only AP.tar.md5 SHA256
   `{EXPECTED_MAGISK_AP_SHA256}` via Odin AP slot; the AP must contain exactly
   one tar member, `boot.img.lz4`, with member SHA256
   `{EXPECTED_MAGISK_LZ4_SHA256}`, and the restored boot partition must verify
   as SHA256 `{EXPECTED_MAGISK_BOOT_SHA256}` after Android/Magisk root returns.
   This is boot partition only and exists solely to restore the rooted
   measurement baseline. It does not authorize recovery, vendor_boot, vbmeta,
   dtbo, BL, CP, CSC, super, userdata, EFS, sec_efs, RPMB, keymaster, modem,
   bootloader, raw host `dd`, fastboot, Magisk modules, multidisabler, format
   data, native-init candidates, kernel rebuilds, or any A90 action. If Android
   or Magisk root does not return, stop and require a separately authorized
   boot-only recovery path."""


def verify_agents_exception(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"AGENTS.md missing: {path}")
    text = path.read_text(encoding="utf-8")
    if "DRAFT ONLY" in text and "S22+ Magisk boot-baseline restore boot-only gate" in text:
        raise SystemExit("AGENTS contains draft-only Magisk baseline restore text")
    missing = [marker for marker in policy_required_markers() if marker not in text]
    if missing:
        raise SystemExit(f"AGENTS missing Magisk baseline restore authorization markers: {missing}")
    append_log(log_path, "agents_exception=ok")


def odin_devices(odin: Path, log_path: Path, label: str) -> list[str]:
    result = run([odin, "-l"], timeout=10.0)
    output = result.stdout + result.stderr
    devices = sorted(set(ODIN_DEVICE_RE.findall(output)))
    append_log(log_path, f"[{utc_now()}] {label} odin4 -l rc={result.returncode} devices={devices}")
    append_log(log_path, output)
    return devices


def wait_for_odin(odin: Path, log_path: Path, wait_sec: int) -> str | None:
    deadline = time.monotonic() + wait_sec
    while True:
        devices = odin_devices(odin, log_path, "wait_for_odin")
        if len(devices) == 1:
            return devices[0]
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices: {devices}")
        if time.monotonic() >= deadline:
            return None
        time.sleep(1.0)


def flash_magisk_boot(odin: Path, magisk_ap: Path, odin_device: str, log_path: Path) -> int:
    cmd = [odin, "--reboot", "-a", magisk_ap, "-d", odin_device]
    append_log(log_path, f"magisk_restore_cmd={' '.join(str(part) for part in cmd)}")
    result = run(cmd, timeout=180.0)
    append_log(log_path, f"magisk_restore_odin_rc={result.returncode}")
    append_log(log_path, result.stdout)
    append_log(log_path, result.stderr)
    return result.returncode


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


def adb_shell(serial: str, command: str, *, timeout: float = 20.0) -> subprocess.CompletedProcess[str]:
    return run(["adb", "-s", serial, "shell", command], timeout=timeout)


def parse_props(text: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        props[key.strip()] = value.strip()
    return props


def android_props(serial: str, log_path: Path, label: str) -> dict[str, str]:
    result = adb_shell(
        serial,
        "printf 'boot_completed='; getprop sys.boot_completed; "
        "printf 'model='; getprop ro.product.model; "
        "printf 'device='; getprop ro.product.device; "
        "printf 'bootloader='; getprop ro.bootloader; "
        "printf 'incremental='; getprop ro.build.version.incremental; "
        "printf 'vbstate='; getprop ro.boot.verifiedbootstate",
        timeout=20.0,
    )
    text = result.stdout + result.stderr
    append_log(log_path, f"{label}_props:")
    append_log(log_path, text)
    return parse_props(text)


def android_identity_errors(props: dict[str, str]) -> list[str]:
    expected = {
        "boot_completed": "1",
        "model": ANDROID_MODEL,
        "device": ANDROID_DEVICE,
        "incremental": ANDROID_INCREMENTAL,
        "vbstate": ANDROID_VBSTATE,
    }
    return [f"{key}={props.get(key)!r} != {value!r}" for key, value in expected.items() if props.get(key) != value]


def require_current_android_identity(serial: str, log_path: Path, label: str) -> None:
    props = android_props(serial, log_path, label)
    errors = android_identity_errors(props)
    if errors:
        raise SystemExit(f"current Android identity check failed before Magisk restore: {errors}")
    append_log(log_path, f"{label}_identity=ok")


def find_root(serial: str, log_path: Path) -> str | None:
    for root_path in ("/debug_ramdisk/su", "su"):
        result = adb_shell(serial, f"{shlex.quote(root_path)} -c id", timeout=20.0)
        text = result.stdout + result.stderr
        append_log(log_path, f"root_probe_{root_path}_rc={result.returncode}")
        append_log(log_path, text)
        if result.returncode == 0 and "uid=0(root)" in text:
            return root_path
    return None


def verify_boot_hash(serial: str, root_path: str, log_path: Path) -> str | None:
    command = (
        f"{shlex.quote(root_path)} -c "
        "'dd if=/dev/block/by-name/boot bs=1048576 2>/dev/null | sha256sum'"
    )
    result = adb_shell(serial, command, timeout=60.0)
    text = result.stdout + result.stderr
    append_log(log_path, f"boot_hash_rc={result.returncode}")
    append_log(log_path, text)
    if result.returncode != 0:
        return None
    first = text.split()
    return first[0] if first else None


def poll_android_magisk(log_path: Path, wait_sec: int) -> AndroidProof | None:
    deadline = time.monotonic() + wait_sec
    while True:
        rows = adb_rows(log_path, "post_magisk_android")
        device_rows = [row for row in rows if row[1] == "device"]
        if len(device_rows) == 1:
            serial = device_rows[0][0]
            props = android_props(serial, log_path, "post_magisk")
            if (
                not android_identity_errors(props)
            ):
                root_path = find_root(serial, log_path)
                if root_path is not None:
                    boot_sha = verify_boot_hash(serial, root_path, log_path)
                    if boot_sha == EXPECTED_MAGISK_BOOT_SHA256:
                        return AndroidProof(serial=serial, root_path=root_path, boot_sha256=boot_sha)
                    append_log(log_path, f"boot_hash_mismatch={boot_sha}")
        elif len(device_rows) > 1:
            raise SystemExit(f"refusing ambiguous Android devices: {device_rows}")
        if time.monotonic() >= deadline:
            return None
        time.sleep(2.0)


def write_result_summary(
    run_dir: Path,
    log_path: Path,
    *,
    result: str,
    rc: int,
    android: AndroidProof | None = None,
    rollback_device: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "schema": EXPECTED_SCHEMA,
        "timestamp_utc": utc_now(),
        "target": EXPECTED_TARGET,
        "result": result,
        "rc": rc,
        "magisk_ap_sha256": EXPECTED_MAGISK_AP_SHA256,
        "magisk_boot_sha256": EXPECTED_MAGISK_BOOT_SHA256,
        "magisk_member_sha256": EXPECTED_MAGISK_LZ4_SHA256,
    }
    if android is not None:
        payload["android_serial"] = DISPLAY_SERIAL_REDACTED
        payload["root_path"] = android.root_path
        payload["verified_boot_sha256"] = android.boot_sha256
    if rollback_device is not None:
        payload["odin_device"] = rollback_device
    path = run_dir / "result.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_log(log_path, f"result_json={path}")
    append_log(log_path, f"result_summary={json.dumps(payload, sort_keys=True)}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--magisk-ap", type=Path, default=DEFAULT_MAGISK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--android-wait-sec", type=int, default=240)
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--ack")
    parser.add_argument("--offline-check", action="store_true")
    parser.add_argument("--check-current-android", action="store_true")
    parser.add_argument("--print-agents-exception-active-template", action="store_true")
    parser.add_argument("--verify-agents-candidate", type=Path)
    parser.add_argument("--live-from-download", action="store_true")
    parser.add_argument("--live-from-android", action="store_true")
    args = parser.parse_args(argv)

    if args.print_agents_exception_active_template:
        print(active_exception_template())
        return 0

    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_magisk_boot_baseline_restore_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus Magisk boot-baseline restore gate ===")
    magisk_ap = resolve(root, args.magisk_ap)
    verify_magisk_ap(magisk_ap, log_path)

    if args.verify_agents_candidate is not None:
        verify_agents_exception(resolve(root, args.verify_agents_candidate), log_path)
        print(f"verify-agents-candidate ok: Magisk boot baseline restore exception is present; log={log_path}")
        return 0

    if args.check_current_android:
        rows = adb_rows(log_path, "check_current_android")
        device_rows = [row for row in rows if row[1] == "device"]
        if len(device_rows) != 1:
            raise SystemExit(f"expected exactly one Android device for --check-current-android, got {device_rows}")
        require_current_android_identity(device_rows[0][0], log_path, "check_current_android")
        append_log(log_path, "check_current_android=ok device_action=0")
        print(f"check-current-android ok: S22+ stock Android identity verified; no device action; log={log_path}")
        return 0

    if args.offline_check or (not args.live_from_download and not args.live_from_android):
        append_log(log_path, "offline_check=ok device_action=0 agents_exception_checked=0")
        print(f"offline-check ok: Magisk boot baseline restore artifact verified; no device action; log={log_path}")
        return 0

    if args.live_from_download and args.live_from_android:
        raise SystemExit("choose only one live mode")
    if args.ack != ACK_TOKEN:
        raise SystemExit(f"live mode requires --ack {ACK_TOKEN}")
    verify_agents_exception(root / "AGENTS.md", log_path)

    odin = resolve(root, args.odin)
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    if args.live_from_android:
        rows = adb_rows(log_path, "pre_reboot_android")
        device_rows = [row for row in rows if row[1] == "device"]
        if len(device_rows) != 1:
            raise SystemExit(f"expected exactly one Android device for --live-from-android, got {device_rows}")
        android_serial = device_rows[0][0]
        require_current_android_identity(android_serial, log_path, "pre_restore")
        result = run(["adb", "-s", android_serial, "reboot", "download"], timeout=20.0)
        append_log(log_path, f"adb_reboot_download_rc={result.returncode}")
        append_log(log_path, result.stdout + result.stderr)
        odin_device = wait_for_odin(odin, log_path, args.odin_wait_sec)
        if odin_device is None:
            write_result_summary(run_dir, log_path, result="odin-not-seen-after-adb-reboot", rc=2)
            return 2
    else:
        devices = odin_devices(odin, log_path, "live_from_download")
        if len(devices) != 1:
            raise SystemExit(f"expected exactly one Odin device for --live-from-download, got {devices}")
        odin_device = devices[0]

    rc = flash_magisk_boot(odin, magisk_ap, odin_device, log_path)
    if rc != 0:
        write_result_summary(run_dir, log_path, result="magisk-flash-failed", rc=rc, rollback_device=odin_device)
        return rc or 3
    android = poll_android_magisk(log_path, args.android_wait_sec)
    if android is None:
        write_result_summary(run_dir, log_path, result="magisk-android-or-root-not-verified", rc=5, rollback_device=odin_device)
        return 5
    write_result_summary(
        run_dir,
        log_path,
        result="magisk-baseline-restored",
        rc=0,
        android=android,
        rollback_device=odin_device,
    )
    print(f"Magisk boot baseline restore completed rc=0; log={log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
