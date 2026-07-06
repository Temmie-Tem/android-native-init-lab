#!/usr/bin/env python3
"""Install and collect a temporary S22+ Magisk boot-time capture capsule.

The live path is intentionally narrow and data-only:

1. Verify one rooted Android S22+ target.
2. Stage two Magisk hook scripts:
   - /data/adb/post-fs-data.d/s22plus_boot_capture_m1.sh
   - /data/adb/service.d/s22plus_boot_capture_m1.sh
3. Reboot Android normally.
4. Wait for Android and Magisk root to return.
5. Pull /data/adb/s22plus_boot_capture_m1 into workspace/private/runs.
6. Remove the two hook scripts, staging files, and remote log directory.

It performs no Odin action, partition write, module load/unload, sysfs/configfs
mutation, Magisk module install, multidisabler, or data wipe.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path


EXPECTED_MODEL = "SM-S906N"
EXPECTED_DEVICE = "g0q"
EXPECTED_BUILD = "S906NKSS7FYG8"
ACK_TOKEN = "S22PLUS-MAGISK-BOOT-CAPTURE-M1"

REMOTE_DIR = "/data/adb/s22plus_boot_capture_m1"
REMOTE_POST_SCRIPT = "/data/adb/post-fs-data.d/s22plus_boot_capture_m1.sh"
REMOTE_SERVICE_SCRIPT = "/data/adb/service.d/s22plus_boot_capture_m1.sh"
REMOTE_TMP_POST = "/data/local/tmp/s22plus_boot_capture_m1_post.sh"
REMOTE_TMP_SERVICE = "/data/local/tmp/s22plus_boot_capture_m1_service.sh"
REMOTE_TMP_TAR = "/data/local/tmp/s22plus_boot_capture_m1.tar"

DEFAULT_RUN_ROOT = Path("workspace/private/runs")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run(argv: list[str | Path], *, timeout: float | None = None, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(part) for part in argv],
        input=input_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )


def adb(serial: str, *args: str, timeout: float | None = None, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return run(["adb", "-s", serial, *args], timeout=timeout, input_text=input_text)


def shell(serial: str, command: str, *, timeout: float | None = 30.0) -> subprocess.CompletedProcess[str]:
    return adb(serial, "shell", command, timeout=timeout)


def su_shell(serial: str, command: str, *, timeout: float | None = 30.0) -> subprocess.CompletedProcess[str]:
    return shell(serial, "su -c " + shlex.quote(command), timeout=timeout)


def append_log(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")


def write_result(path: Path, result: subprocess.CompletedProcess[str]) -> None:
    path.write_text(result.stdout, encoding="utf-8", errors="replace")
    if result.stderr:
        path.with_suffix(path.suffix + ".stderr").write_text(result.stderr, encoding="utf-8", errors="replace")
    path.with_suffix(path.suffix + ".rc").write_text(f"{result.returncode}\n", encoding="ascii")


def parse_adb_devices(output: str) -> list[str]:
    serials: list[str] = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            serials.append(parts[0])
    return serials


def select_serial(requested: str | None) -> str:
    if requested:
        return requested
    result = run(["adb", "devices", "-l"], timeout=10.0)
    serials = parse_adb_devices(result.stdout)
    if len(serials) != 1:
        raise SystemExit(f"expected exactly one adb device or pass --serial; found {len(serials)}")
    return serials[0]


def parse_key_values(raw: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in raw.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def verify_rooted_target(serial: str, log_path: Path) -> dict[str, str]:
    props = shell(
        serial,
        "printf 'model='; getprop ro.product.model; "
        "printf 'device='; getprop ro.product.device; "
        "printf 'build='; getprop ro.build.version.incremental; "
        "printf 'bootloader='; getprop ro.boot.bootloader; "
        "printf 'vbstate='; getprop ro.boot.verifiedbootstate; "
        "printf 'boot_recovery='; getprop ro.boot.boot_recovery; "
        "printf 'boot_completed='; getprop sys.boot_completed; "
        "printf 'su='; command -v su || true; "
        "printf 'su_v='; su -v 2>/dev/null || true",
        timeout=30.0,
    )
    append_log(log_path, "target_props:")
    append_log(log_path, props.stdout + props.stderr)
    if props.returncode != 0:
        raise SystemExit("failed to query target properties")
    values = parse_key_values(props.stdout + props.stderr)
    expected = {
        "model": EXPECTED_MODEL,
        "device": EXPECTED_DEVICE,
        "build": EXPECTED_BUILD,
        "bootloader": EXPECTED_BUILD,
        "boot_recovery": "0",
        "boot_completed": "1",
    }
    missing = {key: value for key, value in expected.items() if values.get(key) != value}
    if missing:
        raise SystemExit(f"target property mismatch: {missing}; got {values}")
    if not values.get("su"):
        raise SystemExit("su is missing on target")
    root = shell(serial, "su -c id", timeout=30.0)
    append_log(log_path, f"su_id_rc={root.returncode}")
    append_log(log_path, root.stdout + root.stderr)
    if root.returncode != 0 or "uid=0(root)" not in (root.stdout + root.stderr):
        raise SystemExit("Magisk root proof failed")
    return values


def stage_script_text(stage: str) -> str:
    return f"""#!/system/bin/sh
STAGE={shlex.quote(stage)}
BASE={shlex.quote(REMOTE_DIR)}
KEY_RE='usb|dwc3|gadget|configfs|adbd|ffs|mtp|rndis|ncm|drm|dsi|panel|sde|display|kgsl|adreno|gpu|dispcc|gpucc|module|insmod|dlkm|firmware|pstore|ramoops'
mkdir -p "$BASE" 2>/dev/null
STAMP="$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null || echo no_date)"
OUT="$BASE/${{STAGE}}_${{STAMP}}.txt"
(
  echo "S22PLUS_BOOT_CAPTURE_M1 stage=$STAGE stamp=$STAMP"
  echo "### identity"
  id 2>/dev/null || true
  date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || true
  cat /proc/uptime 2>/dev/null || true
  uname -a 2>/dev/null || true
  echo "### props"
  getprop ro.product.model 2>/dev/null || true
  getprop ro.product.device 2>/dev/null || true
  getprop ro.build.version.incremental 2>/dev/null || true
  getprop ro.boot.bootloader 2>/dev/null || true
  getprop ro.boot.verifiedbootstate 2>/dev/null || true
  getprop sys.boot_completed 2>/dev/null || true
  getprop init.svc.adbd 2>/dev/null || true
  getprop sys.usb.config 2>/dev/null || true
  getprop sys.usb.state 2>/dev/null || true
  echo "### proc_modules"
  cat /proc/modules 2>/dev/null || true
  echo "### module_metadata"
  for f in /vendor_dlkm/lib/modules/modules.load /vendor_dlkm/lib/modules/modules.dep /vendor_dlkm/lib/modules/modules.alias /vendor/lib/modules/modules.load /vendor/lib/modules/modules.dep /vendor/lib/modules/modules.alias /odm/lib/modules/modules.load /odm/lib/modules/modules.dep; do
    [ -f "$f" ] || continue
    echo "--- $f"
    cat "$f" 2>/dev/null || true
  done
  echo "### usb_configfs_tree"
  for p in /config/usb_gadget /sys/kernel/config/usb_gadget /sys/class/udc /sys/class/android_usb; do
    [ -e "$p" ] || continue
    echo "---TREE $p"
    find "$p" -maxdepth 4 2>/dev/null | sort | head -n 500
  done
  echo "### usb_function_values"
  for f in /config/usb_gadget/*/UDC /config/usb_gadget/*/functions/ncm.*/ifname /config/usb_gadget/*/configs/*/f*; do
    [ -e "$f" ] || continue
    echo "--- $f"
    if [ -L "$f" ]; then ls -l "$f"; else head -c 512 "$f" 2>/dev/null; echo; fi
  done
  echo "### net_state"
  ip addr 2>/dev/null || true
  echo "### display_state"
  for p in /sys/class/drm /sys/class/graphics /sys/class/backlight /dev/dri /dev/kgsl; do
    [ -e "$p" ] || continue
    echo "--- $p"
    ls -lR "$p" 2>/dev/null | head -n 500
  done
  echo "### pstore_state"
  mount 2>/dev/null | grep -i pstore || true
  ls -la /sys/fs/pstore 2>/dev/null || true
  echo "### dmesg_key"
  dmesg 2>/dev/null | grep -Ei "$KEY_RE" | head -n 1000 || true
  echo "### dmesg_full"
  dmesg 2>/dev/null || true
) > "$OUT" 2>&1
chmod 0600 "$OUT" 2>/dev/null || true
sync 2>/dev/null || true
exit 0
"""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def install_capsule(serial: str, run_dir: Path, log_path: Path) -> dict[str, str]:
    post_text = stage_script_text("post_fs_data")
    service_text = stage_script_text("service")
    post_local = run_dir / "s22plus_boot_capture_m1_post.sh"
    service_local = run_dir / "s22plus_boot_capture_m1_service.sh"
    post_local.write_text(post_text, encoding="utf-8")
    service_local.write_text(service_text, encoding="utf-8")
    os.chmod(post_local, 0o700)
    os.chmod(service_local, 0o700)
    script_hashes = {
        "post_script_sha256": sha256_text(post_text),
        "service_script_sha256": sha256_text(service_text),
    }
    append_log(log_path, json.dumps(script_hashes, sort_keys=True))

    for local, remote in ((post_local, REMOTE_TMP_POST), (service_local, REMOTE_TMP_SERVICE)):
        result = adb(serial, "push", str(local), remote, timeout=30.0)
        append_log(log_path, f"adb_push {local.name} rc={result.returncode}")
        append_log(log_path, result.stdout + result.stderr)
        if result.returncode != 0:
            raise SystemExit(f"failed to push {local}")

    install_cmd = (
        "set -e; "
        "mkdir -p /data/adb/post-fs-data.d /data/adb/service.d " + shlex.quote(REMOTE_DIR) + "; "
        "cp " + shlex.quote(REMOTE_TMP_POST) + " " + shlex.quote(REMOTE_POST_SCRIPT) + "; "
        "cp " + shlex.quote(REMOTE_TMP_SERVICE) + " " + shlex.quote(REMOTE_SERVICE_SCRIPT) + "; "
        "chmod 0700 " + shlex.quote(REMOTE_POST_SCRIPT) + " " + shlex.quote(REMOTE_SERVICE_SCRIPT) + "; "
        "rm -f " + shlex.quote(REMOTE_TMP_POST) + " " + shlex.quote(REMOTE_TMP_SERVICE) + "; "
        "echo installed"
    )
    result = su_shell(serial, install_cmd, timeout=30.0)
    append_log(log_path, f"install_capsule_rc={result.returncode}")
    append_log(log_path, result.stdout + result.stderr)
    if result.returncode != 0 or "installed" not in (result.stdout + result.stderr):
        raise SystemExit("failed to install remote capsule scripts")
    return script_hashes


def cleanup_capsule(serial: str, log_path: Path, *, remove_logs: bool = True) -> bool:
    parts = [
        "rm -f " + shlex.quote(REMOTE_POST_SCRIPT),
        "rm -f " + shlex.quote(REMOTE_SERVICE_SCRIPT),
        "rm -f " + shlex.quote(REMOTE_TMP_POST),
        "rm -f " + shlex.quote(REMOTE_TMP_SERVICE),
    ]
    if remove_logs:
        parts.append("rm -rf " + shlex.quote(REMOTE_DIR))
    parts.append("echo cleaned")
    result = su_shell(serial, "; ".join(parts), timeout=30.0)
    append_log(log_path, f"cleanup_rc={result.returncode}")
    append_log(log_path, result.stdout + result.stderr)
    return result.returncode == 0 and "cleaned" in (result.stdout + result.stderr)


def wait_for_android(serial: str, wait_sec: int, log_path: Path) -> bool:
    deadline = time.monotonic() + wait_sec
    while True:
        devices = run(["adb", "devices", "-l"], timeout=10.0)
        append_log(log_path, f"[{utc_now()}] adb devices rc={devices.returncode}")
        append_log(log_path, devices.stdout + devices.stderr)
        if serial in devices.stdout and "\tdevice" in devices.stdout.replace(" ", "\t"):
            props = shell(serial, "getprop sys.boot_completed; getprop ro.product.model; getprop ro.product.device", timeout=10.0)
            append_log(log_path, "boot_poll_props:")
            append_log(log_path, props.stdout + props.stderr)
            lines = props.stdout.splitlines()
            if len(lines) >= 3 and lines[0] == "1" and lines[1] == EXPECTED_MODEL and lines[2] == EXPECTED_DEVICE:
                return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(2.0)


def safe_extract_tar(tar_path: Path, out_dir: Path) -> None:
    out_resolved = out_dir.resolve()
    with tarfile.open(tar_path) as archive:
        for member in archive.getmembers():
            target = (out_dir / member.name).resolve()
            if out_resolved not in target.parents and target != out_resolved:
                raise SystemExit(f"refusing unsafe tar member path: {member.name}")
        archive.extractall(out_dir)


def pull_capture(serial: str, run_dir: Path, log_path: Path) -> Path:
    out_dir = run_dir / "device_capture"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = adb(serial, "pull", REMOTE_DIR, str(out_dir), timeout=120.0)
    append_log(log_path, f"adb_pull_rc={result.returncode}")
    append_log(log_path, result.stdout + result.stderr)
    if result.returncode == 0:
        return out_dir

    tar_cmd = (
        "rm -f " + shlex.quote(REMOTE_TMP_TAR) + "; "
        "tar -cf " + shlex.quote(REMOTE_TMP_TAR) + " -C /data/adb s22plus_boot_capture_m1 && "
        "chmod 0644 " + shlex.quote(REMOTE_TMP_TAR) + " && "
        "echo tar_ok"
    )
    tar_result = su_shell(serial, tar_cmd, timeout=60.0)
    append_log(log_path, f"root_tar_rc={tar_result.returncode}")
    append_log(log_path, tar_result.stdout + tar_result.stderr)
    if tar_result.returncode != 0 or "tar_ok" not in (tar_result.stdout + tar_result.stderr):
        raise SystemExit("failed to create root-readable remote capture tar")

    local_tar = run_dir / "s22plus_boot_capture_m1.tar"
    pull_tar = adb(serial, "pull", REMOTE_TMP_TAR, str(local_tar), timeout=120.0)
    append_log(log_path, f"adb_pull_tar_rc={pull_tar.returncode}")
    append_log(log_path, pull_tar.stdout + pull_tar.stderr)
    su_shell(serial, "rm -f " + shlex.quote(REMOTE_TMP_TAR), timeout=20.0)
    if pull_tar.returncode != 0:
        raise SystemExit("failed to pull remote capture tar")
    safe_extract_tar(local_tar, out_dir)
    return out_dir


def summarize_capture(capture_root: Path, script_hashes: dict[str, str]) -> dict[str, object]:
    files = sorted(path for path in capture_root.rglob("*.txt") if path.is_file())
    stages: dict[str, dict[str, object]] = {}
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        stage = "unknown"
        first = text.splitlines()[0] if text.splitlines() else ""
        if "stage=post_fs_data" in first:
            stage = "post_fs_data"
        elif "stage=service" in first:
            stage = "service"
        stages[stage] = {
            "file": path.name,
            "bytes": path.stat().st_size,
            "proc_modules_lines": section_line_count(text, "### proc_modules"),
            "module_load_mentions": text.count("modules.load"),
            "usb_function_mentions": sum(text.count(token) for token in ("ffs.adb", "ncm.0", "rndis.rndis")),
            "display_mentions": sum(text.count(token) for token in ("card0", "renderD128", "panel0-backlight")),
            "dmesg_lines": section_line_count(text, "### dmesg_full"),
        }
    return {
        "script_hashes": script_hashes,
        "capture_file_count": len(files),
        "stages": stages,
    }


def section_line_count(text: str, header: str) -> int:
    lines = text.splitlines()
    count = 0
    in_section = False
    for line in lines:
        if line == header:
            in_section = True
            continue
        if in_section and line.startswith("### "):
            break
        if in_section and line.strip():
            count += 1
    return count


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", help="adb serial to pin; required if multiple devices are connected")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wait-sec", type=int, default=300)
    parser.add_argument("--dry-run", action="store_true", help="verify target and print generated script hashes")
    parser.add_argument("--cleanup", action="store_true", help="remove remote scripts/staging/log directory only")
    parser.add_argument("--collect-existing", action="store_true", help="pull an already-created remote capture and cleanup")
    parser.add_argument("--live-run", action="store_true", help="install, reboot, collect, and cleanup")
    parser.add_argument("--ack", help=f"required with --live-run: {ACK_TOKEN}")
    args = parser.parse_args(argv)

    serial = select_serial(args.serial)
    run_dir = args.run_dir or (DEFAULT_RUN_ROOT / f"s22plus_magisk_boot_time_capture_m1_{stamp_now()}")
    run_dir.mkdir(parents=True, exist_ok=False)
    log_path = run_dir / "s22plus_magisk_boot_time_capture_m1.txt"
    append_log(log_path, f"=== {utc_now()} s22plus magisk boot-time capture m1 ===")
    append_log(log_path, f"serial_redacted=1")

    verify_rooted_target(serial, log_path)

    post_hash = sha256_text(stage_script_text("post_fs_data"))
    service_hash = sha256_text(stage_script_text("service"))
    script_hashes = {"post_script_sha256": post_hash, "service_script_sha256": service_hash}
    (run_dir / "script_hashes.json").write_text(json.dumps(script_hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.cleanup:
        ok = cleanup_capsule(serial, log_path)
        print(f"cleanup={'ok' if ok else 'failed'} log={log_path}")
        return 0 if ok else 2

    if args.collect_existing:
        capture_root = pull_capture(serial, run_dir, log_path)
        summary = summarize_capture(capture_root, script_hashes)
        cleanup_ok = cleanup_capsule(serial, log_path)
        summary["remote_cleanup_ok"] = cleanup_ok
        (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(run_dir)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if cleanup_ok else 4

    if args.dry_run or not args.live_run:
        print(f"dry-run ok: rooted target verified; script_hashes={json.dumps(script_hashes, sort_keys=True)}; log={log_path}")
        return 0

    if args.ack != ACK_TOKEN:
        raise SystemExit(f"--live-run requires --ack {ACK_TOKEN}")

    script_hashes = install_capsule(serial, run_dir, log_path)
    reboot = adb(serial, "reboot", timeout=20.0)
    append_log(log_path, f"adb_reboot_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    if reboot.returncode != 0:
        raise SystemExit("adb reboot failed after capsule install")

    if not wait_for_android(serial, args.wait_sec, log_path):
        print(f"Android did not return before timeout; leaving capsule for manual recovery. log={log_path}")
        return 3

    verify_rooted_target(serial, log_path)
    capture_root = pull_capture(serial, run_dir, log_path)
    summary = summarize_capture(capture_root, script_hashes)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    cleanup_ok = cleanup_capsule(serial, log_path)
    summary["remote_cleanup_ok"] = cleanup_ok
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(run_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if cleanup_ok else 4


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
