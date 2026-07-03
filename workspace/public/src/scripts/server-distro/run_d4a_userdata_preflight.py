#!/usr/bin/env python3
"""Run the server-distro D4A userdata appliance preflight.

D4A is read-only: it identifies the userdata partition, checks the recovery
envelope and clean rootfs source, and records whether D4B must stage missing
tools.  It does not mount, format, flash, reboot, or write to the device.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
if str(REVAL_DIR) not in sys.path:
    sys.path.insert(0, str(REVAL_DIR))

import a90ctl  # noqa: E402


DEFAULT_RUN_BASE = REPO_ROOT / "workspace" / "private" / "runs" / "server-distro"
DEFAULT_D3_SOURCE_IMAGE = (
    REPO_ROOT / "workspace/private/builds/server-distro/d3-sysvinit-usrmerge-20260703T101657Z.img"
)
DEFAULT_D3_SOURCE_ROOTFS = (
    REPO_ROOT / "workspace/private/builds/server-distro/d3-sysvinit-usrmerge-20260703T101657Z-rootfs"
)
DEFAULT_D3_SUMMARY = (
    REPO_ROOT / "workspace/private/builds/server-distro/d3-sysvinit-usrmerge-20260703T101657Z-summary.json"
)
DEFAULT_D3B_REPORT = REPO_ROOT / "docs/reports/SERVER_DISTRO_D3B_SWITCHROOT_LIVE_PASS_2026-07-03.md"
DEFAULT_D4_PLAN = REPO_ROOT / "docs/plans/SERVER_DISTRO_D4_USERDATA_APPLIANCE_PLAN_2026-07-03.md"
ROLLBACK_IMAGES = {
    "v2321": (
        REPO_ROOT / "workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img",
        "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb",
    ),
    "v2237": (
        REPO_ROOT / "workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img",
        "b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f",
    ),
    "v48": (
        REPO_ROOT / "workspace/private/inputs/boot_images/boot_linux_v48.img",
        None,
    ),
}
EXPECTED_D3_SOURCE_SHA256 = "6f1960eb4332e1a22d5da1c98e990352c58d80157fbe6286b53ec9fe8ebe59f7"
USERDATA_MIN_BYTES = 100_000_000_000
USERDATA_MAX_BYTES = 140_000_000_000
FORBIDDEN_BY_NAMES = (
    "efs",
    "sec_efs",
    "modem",
    "modemst1",
    "modemst2",
    "fsg",
    "rpm",
    "rpmb",
    "keymaster",
    "vbmeta",
    "vbmeta_system",
    "vbmeta_vendor",
    "dsp",
    "keydata",
    "keyrefuge",
    "abl",
    "xbl",
    "xbl_config",
    "bootloader",
    "persist",
)
CURRENT_REQUIRED_APPLETS = ("mount", "tar", "switch_root", "sha256sum", "readlink", "grep", "df", "mknod")
D4B_STAGEABLE_APPLETS = ("mkfs.ext4",)


D4A_TARGET_SCRIPT = r"""
set -eu
BB=/bin/busybox
TARGET=/dev/block/by-name/userdata
echo A90D4A_BEGIN
echo no_format_performed=1
echo no_mount_performed=1
echo no_flash_performed=1
echo target_by_name=$TARGET
$BB ls -l "$TARGET" 2>/dev/null || true
REAL=$($BB readlink -f "$TARGET" 2>/dev/null || true)
BLOCK=$($BB basename "$REAL" 2>/dev/null || true)
echo target_real=$REAL
echo target_block=$BLOCK
if [ -n "$BLOCK" ] && [ -r "/sys/class/block/$BLOCK/uevent" ]; then
  $BB sed 's/^/target_uevent_/' "/sys/class/block/$BLOCK/uevent"
fi
if [ -n "$BLOCK" ] && [ -r "/sys/class/block/$BLOCK/size" ]; then
  echo target_size_sectors=$($BB cat "/sys/class/block/$BLOCK/size")
fi
if [ -n "$BLOCK" ] && [ -r "/sys/class/block/$BLOCK/dev" ]; then
  echo target_dev=$($BB cat "/sys/class/block/$BLOCK/dev")
fi
if [ -n "$BLOCK" ] && [ -r "/sys/class/block/$BLOCK/ro" ]; then
  echo target_ro=$($BB cat "/sys/class/block/$BLOCK/ro")
fi
echo __A90D4A_USERDATA_SCAN__
for u in /sys/class/block/*/uevent; do
  [ -r "$u" ] || continue
  $BB grep -q '^PARTNAME=userdata$' "$u" || continue
  d=${u#/sys/class/block/}; d=${d%/uevent}
  echo scan_block=$d
  echo scan_node=/dev/block/$d
  if [ -e "/dev/block/$d" ]; then echo scan_node_exists=1; else echo scan_node_exists=0; fi
  $BB sed 's/^/scan_uevent_/' "$u"
  [ -r "/sys/class/block/$d/size" ] && echo scan_size_sectors=$($BB cat "/sys/class/block/$d/size")
  [ -r "/sys/class/block/$d/dev" ] && echo scan_dev=$($BB cat "/sys/class/block/$d/dev")
  [ -r "/sys/class/block/$d/ro" ] && echo scan_ro=$($BB cat "/sys/class/block/$d/ro")
done
echo __A90D4A_BY_NAME__
for name in userdata efs sec_efs modem modemst1 modemst2 fsg rpm rpmb keymaster vbmeta vbmeta_system vbmeta_vendor dsp keydata keyrefuge abl xbl xbl_config bootloader persist; do
  p=/dev/block/by-name/$name
  if [ -e "$p" ]; then
    r=$($BB readlink -f "$p" 2>/dev/null || true)
    echo byname_$name=$r
  fi
done
echo __A90D4A_MOUNTS__
$BB cat /proc/mounts
echo A90D4A_TARGET_DONE
""".strip()


D4A_SYSTEM_SCRIPT = r"""
set -eu
BB=/bin/busybox
echo __A90D4A_DF_K__
$BB df -k
echo __A90D4A_APPLETS__
$BB --list
echo __A90D4A_FILESYSTEMS__
$BB cat /proc/filesystems
echo A90D4A_DONE
""".strip()
D4A_DEVICE_SCRIPTS = (D4A_TARGET_SCRIPT, D4A_SYSTEM_SCRIPT)
D4A_DEVICE_SCRIPT = "\n".join(D4A_DEVICE_SCRIPTS)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, sort_keys=True, ensure_ascii=False)
        fp.write("\n")
        fp.flush()
        os.fsync(fp.fileno())
    tmp.replace(path)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def normalize_run_dir(run_dir: Path) -> Path:
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    return run_dir.resolve()


def run_cmd(host: str,
            port: int,
            timeout: float,
            command: list[str],
            *,
            retry_unsafe: bool = False,
            allow_error: bool = False) -> dict[str, Any]:
    result = a90ctl.run_cmdv1_command(
        host,
        port,
        timeout,
        command,
        retry_unsafe=retry_unsafe,
        require_prompt_after_end=True,
    )
    payload = {
        "command": command,
        "rc": result.rc,
        "status": result.status,
        "begin": result.begin,
        "end": result.end,
        "text": result.text,
    }
    if not allow_error and result.rc != 0:
        raise RuntimeError(f"device command failed rc={result.rc}: {command}\n{result.text}")
    return payload


def run_shell(host: str,
              port: int,
              timeout: float,
              script: str,
              *,
              allow_error: bool = False) -> dict[str, Any]:
    return run_cmd(
        host,
        port,
        timeout,
        ["run", "/bin/busybox", "sh", "-c", script],
        retry_unsafe=True,
        allow_error=allow_error,
    )


def clean_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip("\r")
        if not line or line.startswith("A90P1 BEGIN ") or line.startswith("A90P1 END "):
            continue
        if line.startswith("a90:/#") or line in {"AT", "T"}:
            continue
        if line.startswith("cmdv1 ") or line.startswith("cmdv1x "):
            continue
        lines.append(line)
    return lines


def section(text: str, marker: str) -> str:
    lines = clean_lines(text)
    start_marker = marker
    try:
        start = lines.index(start_marker) + 1
    except ValueError:
        return ""
    end = len(lines)
    for idx in range(start, len(lines)):
        if lines[idx].startswith("__A90D4A_") or lines[idx] == "A90D4A_DONE":
            end = idx
            break
    return "\n".join(lines[start:end])


def parse_key_values(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in clean_lines(text):
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if re.fullmatch(r"[A-Za-z0-9_.:-]+", key):
            out[key] = value.strip()
    return out


def parse_applets(text: str) -> dict[str, bool]:
    applets = {line.strip() for line in text.splitlines() if line.strip()}
    names = (*CURRENT_REQUIRED_APPLETS, *D4B_STAGEABLE_APPLETS)
    return {name: name in applets for name in names}


def parse_filesystems(text: str) -> dict[str, bool]:
    fs = {line.split()[-1] for line in text.splitlines() if line.strip()}
    return {"ext4": "ext4" in fs, "tmpfs": "tmpfs" in fs}


def parse_mounts(text: str, target_real: str, target_block: str) -> dict[str, Any]:
    matches: list[str] = []
    target_sources = {
        target_real,
        f"/dev/block/{target_block}" if target_block else "",
        "/dev/block/by-name/userdata",
    }
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        source, mountpoint = parts[0], parts[1]
        if source in target_sources or mountpoint in {"/data", "/userdata", "/mnt/a90-userdata-root"}:
            matches.append(line)
    return {"mounted": bool(matches), "matches": matches}


def parse_by_name(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("byname_") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        out[name.removeprefix("byname_")] = value.strip()
    return out


def parse_df_sd(text: str) -> dict[str, Any]:
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 6 or parts[0].lower().startswith("filesystem"):
            continue
        if parts[5] == "/mnt/sdext":
            try:
                return {
                    "filesystem": parts[0],
                    "blocks_1k": int(parts[1]),
                    "used_1k": int(parts[2]),
                    "available_1k": int(parts[3]),
                    "mountpoint": parts[5],
                }
            except ValueError:
                return {"mountpoint": parts[5]}
    return {}


def host_file_record(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    record = {"path": rel(path), "exists": path.is_file()}
    if path.is_file():
        actual = sha256_file(path)
        record["sha256"] = actual
        if expected_sha256 is not None:
            record["expected_sha256"] = expected_sha256
            record["sha256_match"] = actual == expected_sha256
    return record


def host_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    rollback = {
        name: host_file_record(path, expected)
        for name, (path, expected) in ROLLBACK_IMAGES.items()
    }
    rootfs_summary = {}
    if args.d3_summary.is_file():
        rootfs_summary = json.loads(args.d3_summary.read_text(encoding="utf-8"))
    d3b_text = args.d3b_report.read_text(encoding="utf-8") if args.d3b_report.is_file() else ""
    d4_plan_text = args.d4_plan.read_text(encoding="utf-8") if args.d4_plan.is_file() else ""
    adb_record = subprocess.run(
        [args.adb, "devices", "-l"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=10.0,
        check=False,
    )
    return {
        "rollback_images": rollback,
        "d3_source_image": host_file_record(args.d3_source_image, EXPECTED_D3_SOURCE_SHA256),
        "d3_source_rootfs": {
            "path": rel(args.d3_source_rootfs),
            "exists": args.d3_source_rootfs.is_dir(),
            "sbin_init_exists": (args.d3_source_rootfs / "sbin/init").exists(),
            "stage_marker_exists": (args.d3_source_rootfs / "etc/a90-d3-firstboot").is_file(),
        },
        "d3_summary": {"path": rel(args.d3_summary), "exists": args.d3_summary.is_file(), "content": rootfs_summary},
        "d3b_report": {
            "path": rel(args.d3b_report),
            "exists": args.d3b_report.is_file(),
            "switchroot_pass_evidence": "server-distro-d3b-switchroot-live-pass" in d3b_text,
            "twrp_recovery_evidence": "TWRP recovery" in d3b_text and "v2321" in d3b_text,
        },
        "d4_plan": {
            "path": rel(args.d4_plan),
            "exists": args.d4_plan.is_file(),
            "mentions_d4a": "D4A - Read-Only Preflight" in d4_plan_text,
        },
        "adb_devices": {
            "command": [args.adb, "devices", "-l"],
            "returncode": adb_record.returncode,
            "stdout": adb_record.stdout,
            "stderr": adb_record.stderr,
            "recovery_currently_connected": "\trecovery" in adb_record.stdout,
        },
    }


def classify(raw: dict[str, Any]) -> dict[str, Any]:
    text = str(raw["device_observation"].get("text") or "")
    kv = parse_key_values(text)
    by_name = parse_by_name(section(text, "__A90D4A_BY_NAME__"))
    scan_text = section(text, "__A90D4A_USERDATA_SCAN__")
    scan_kv = parse_key_values(scan_text)
    scan_blocks = re.findall(r"(?m)^scan_block=([^\s]+)$", scan_text)
    by_name_userdata = by_name.get("userdata", "")
    target_source = "by-name"
    target_real = kv.get("target_real", "")
    target_block = kv.get("target_block", "")
    target_devname = kv.get("target_uevent_DEVNAME", "")
    target_partname = kv.get("target_uevent_PARTNAME", "")
    target_dev = kv.get("target_dev", "")
    target_ro = kv.get("target_ro", "")
    target_node_exists = bool(target_real)
    sectors = int(kv.get("target_size_sectors", "0") or "0")
    if not target_real and len(scan_blocks) == 1:
        target_source = "partname-scan"
        target_block = scan_blocks[0]
        target_real = f"/dev/block/{target_block}"
        target_devname = scan_kv.get("scan_uevent_DEVNAME", "")
        target_partname = scan_kv.get("scan_uevent_PARTNAME", "")
        target_dev = scan_kv.get("scan_dev", "")
        target_ro = scan_kv.get("scan_ro", "")
        target_node_exists = scan_kv.get("scan_node_exists") == "1"
        sectors = int(scan_kv.get("scan_size_sectors", "0") or "0")
    target_bytes = sectors * 512
    target = {
        "by_name": kv.get("target_by_name", "/dev/block/by-name/userdata"),
        "by_name_present": bool(by_name_userdata),
        "source": target_source,
        "realpath": target_real,
        "block": target_block,
        "node_exists": target_node_exists,
        "dev": target_dev,
        "ro": target_ro,
        "partname": target_partname,
        "devname": target_devname,
        "sectors_512": sectors,
        "bytes": target_bytes,
        "gib": round(target_bytes / (1024 ** 3), 2) if target_bytes else 0,
    }
    mounts = parse_mounts(section(text, "__A90D4A_MOUNTS__"), target_real, target_block)
    applets = parse_applets(section(text, "__A90D4A_APPLETS__"))
    filesystems = parse_filesystems(section(text, "__A90D4A_FILESYSTEMS__"))
    sd = parse_df_sd(section(text, "__A90D4A_DF_K__"))
    forbidden_reals = {name: by_name[name] for name in FORBIDDEN_BY_NAMES if name in by_name}
    forbidden_collision = {
        name: value for name, value in forbidden_reals.items()
        if value and target_real and value == target_real
    }
    host = raw["host_artifacts"]
    rollback_ok = all(
        item.get("exists") and item.get("sha256_match", True)
        for item in host["rollback_images"].values()
    )
    rootfs_ok = bool(
        host["d3_source_image"].get("exists")
        and host["d3_source_image"].get("sha256_match")
        and host["d3_source_rootfs"].get("exists")
        and host["d3_source_rootfs"].get("sbin_init_exists")
    )
    d3b_ok = bool(host["d3b_report"].get("exists") and host["d3b_report"].get("switchroot_pass_evidence"))
    recovery_evidence_ok = bool(
        host["adb_devices"].get("recovery_currently_connected")
        or host["d3b_report"].get("twrp_recovery_evidence")
    )
    target_ok = bool(
        target_real
        and target_block
        and target["partname"] == "userdata"
        and target["devname"] == target_block
        and target["ro"] == "0"
        and USERDATA_MIN_BYTES <= target_bytes <= USERDATA_MAX_BYTES
        and scan_blocks == [target_block]
        and (not by_name_userdata or by_name_userdata == target_real)
        and not mounts["mounted"]
        and not forbidden_collision
    )
    current_tools_ok = all(applets.get(name) for name in CURRENT_REQUIRED_APPLETS) and filesystems.get("ext4")
    d4b_must_stage = [name for name in D4B_STAGEABLE_APPLETS if not applets.get(name)]
    d4b_must_materialize = [] if target_node_exists else ["userdata-block-node"]
    preflight_ok = bool(
        raw["baseline_ok"]
        and rollback_ok
        and recovery_evidence_ok
        and d3b_ok
        and rootfs_ok
        and target_ok
        and current_tools_ok
    )
    blockers: list[str] = []
    if not raw["baseline_ok"]:
        blockers.append("resident-not-v2321-or-selftest-fail")
    if not rollback_ok:
        blockers.append("rollback-image-check-failed")
    if not recovery_evidence_ok:
        blockers.append("recovery-twrp-evidence-missing")
    if not d3b_ok:
        blockers.append("d3b-pass-report-missing")
    if not rootfs_ok:
        blockers.append("clean-rootfs-source-check-failed")
    if not target_ok:
        blockers.append("userdata-target-identity-check-failed")
    if not current_tools_ok:
        blockers.append("current-readonly-or-copy-tools-missing")
    return {
        "decision": (
            "server-distro-d4a-userdata-preflight-pass"
            if preflight_ok else "server-distro-d4a-userdata-preflight-blocked"
        ),
        "preflight_ok": preflight_ok,
        "blockers": blockers,
        "read_only": True,
        "no_format_performed": "no_format_performed=1" in text,
        "no_mount_performed": "no_mount_performed=1" in text,
        "no_flash_performed": "no_flash_performed=1" in text,
        "target": target,
        "target_scan_blocks": scan_blocks,
        "by_name_userdata": by_name_userdata,
        "forbidden_collision": forbidden_collision,
        "userdata_mounted": mounts["mounted"],
        "userdata_mount_matches": mounts["matches"],
        "sd": sd,
        "applets": applets,
        "filesystems": filesystems,
        "d4b_must_stage": d4b_must_stage,
        "d4b_must_materialize": d4b_must_materialize,
        "rollback_ok": rollback_ok,
        "recovery_evidence_ok": recovery_evidence_ok,
        "rootfs_source_ok": rootfs_ok,
        "d3b_report_ok": d3b_ok,
        "d4c_allowed_now": False,
        "next": (
            "D4B native-init fail-closed surface"
            if preflight_ok else "fix D4A blockers before D4B/D4C"
        ),
    }


def collect(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    now_utc = _dt.datetime.now(_dt.UTC).replace(microsecond=0)
    run_id = args.run_id or "d4a-userdata-preflight-" + now_utc.strftime("%Y%m%dT%H%M%SZ")
    run_dir = normalize_run_dir(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    run_dir.mkdir(parents=True, exist_ok=True)

    try:
        a90ctl.bridge_exchange(
            args.host,
            args.port,
            "hide",
            min(args.timeout, 8.0),
            markers=(b"[busy]", b"[done]", b"[err]"),
        )
    except OSError:
        pass

    baseline = {
        "version": run_cmd(args.host, args.port, args.timeout, ["version"]),
        "status": run_cmd(args.host, args.port, args.timeout, ["status"]),
        "selftest": run_cmd(args.host, args.port, args.timeout, ["selftest"]),
    }
    baseline_ok = (
        "v2321-usb-clean-identity-rodata" in baseline["version"]["text"]
        and "fail=0" in baseline["selftest"]["text"]
    )
    if not baseline_ok:
        raise RuntimeError("resident device is not clean v2321; refusing D4A")

    observations = [
        run_shell(args.host, args.port, args.observation_timeout, script)
        for script in D4A_DEVICE_SCRIPTS
    ]
    observation = {
        "text": "\n".join(str(item.get("text") or "") for item in observations),
        "parts": observations,
    }

    final = {
        "version": run_cmd(args.host, args.port, args.timeout, ["version"]),
        "selftest": run_cmd(args.host, args.port, args.timeout, ["selftest"]),
    }
    final_ok = (
        "v2321-usb-clean-identity-rodata" in final["version"]["text"]
        and "fail=0" in final["selftest"]["text"]
    )
    if not final_ok:
        raise RuntimeError("D4A final device health is not clean v2321")

    raw = {
        "run_id": run_id,
        "run_dir": rel(run_dir),
        "timestamp_utc": now_utc.isoformat().replace("+00:00", "Z"),
        "scope": "server-distro D4A userdata read-only preflight",
        "safety": {
            "read_only": True,
            "no_flash": True,
            "no_mount": True,
            "no_format": True,
            "no_reboot": True,
            "userdata_identify_only": True,
        },
        "baseline": baseline,
        "baseline_ok": baseline_ok,
        "host_artifacts": host_artifacts(args),
        "device_observations": observations,
        "device_observation": observation,
        "final": final,
        "final_ok": final_ok,
    }
    summary = classify(raw)
    summary["run_dir"] = raw["run_dir"]
    summary["final_v2321"] = final_ok
    summary["final_selftest_fail0"] = final_ok

    write_json(run_dir / "d4a_private.json", raw)
    write_json(run_dir / "d4a_public_summary.json", summary)
    return raw, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=a90ctl.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=a90ctl.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--observation-timeout", type=float, default=60.0)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--d3-source-image", type=Path, default=DEFAULT_D3_SOURCE_IMAGE)
    parser.add_argument("--d3-source-rootfs", type=Path, default=DEFAULT_D3_SOURCE_ROOTFS)
    parser.add_argument("--d3-summary", type=Path, default=DEFAULT_D3_SUMMARY)
    parser.add_argument("--d3b-report", type=Path, default=DEFAULT_D3B_REPORT)
    parser.add_argument("--d4-plan", type=Path, default=DEFAULT_D4_PLAN)
    args = parser.parse_args(argv)
    args.d3_source_image = args.d3_source_image.resolve()
    args.d3_source_rootfs = args.d3_source_rootfs.resolve()
    args.d3_summary = args.d3_summary.resolve()
    args.d3b_report = args.d3b_report.resolve()
    args.d4_plan = args.d4_plan.resolve()
    _raw, summary = collect(args)
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
