#!/usr/bin/env python3
"""Host-only S22+ native-init observability frontier audit.

This is a decision helper, not a live helper.  It does not use ADB, does not
write sysfs, does not run OpenOCD init, does not flash, and does not reboot.

It answers the next practical question after the EUD/OpenOCD setup work:

  Given the current host state, is the next observation channel EUD, UART, or
  the no-UART M18 prefix-download fallback?
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import s22plus_eud_openocd_init_probe_gate as eud_gate


DEFAULT_RUN_ROOT = Path("workspace/private/runs")
DEFAULT_M18_PREFIX_ROOT = Path("workspace/private/outputs/s22plus_native_init/inplace_m18_prefix_download_v0_1")
EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_P00_AP_SHA256 = "b79ac94aac341ab5e4c08cb3c568c20be28bb71ccd4f1b047f712bd1dcf5225b"
EXPECTED_P10_AP_SHA256 = "ee46e5eef52d85f6bbfecbede8b7a2d374cce47140f900c2bbb57ce07beddca8"
SAMSUNG_ANDROID_RE = re.compile(r"SAMSUNG|Samsung|Android|05c6:|04e8:", re.IGNORECASE)
UART_HINT_RE = re.compile(
    r"FTDI|FT232|CP210|Silicon Labs|QinHeng|CH340|wch|Prolific|PL2303|USB Serial|UART|TTL|Debug Cable",
    re.IGNORECASE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").is_dir():
            return parent
    raise RuntimeError(f"could not locate repo root from {current}")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_native_init_observability_frontier_{stamp}")
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise SystemExit(f"could not allocate unique run directory under {base.parent}")


def redact(text: str) -> str:
    text = re.sub(r"RFCT[0-9A-Z]+", "<REDACTED_SERIAL>", text)
    text = re.sub(r"usb-SAMSUNG_SAMSUNG_Android_[^/\s]+", "usb-SAMSUNG_SAMSUNG_Android_<REDACTED_SERIAL>", text)
    text = re.sub(r"([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", "<REDACTED_MAC>", text)
    return text


def run_command(argv: list[str], timeout: float = 10.0) -> dict[str, Any]:
    try:
        completed = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        return {
            "argv": argv,
            "returncode": completed.returncode,
            "stdout": redact(completed.stdout),
            "stderr": redact(completed.stderr),
            "timeout": False,
        }
    except FileNotFoundError as exc:
        return {"argv": argv, "returncode": 127, "stdout": "", "stderr": str(exc), "timeout": False}
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv,
            "returncode": 124,
            "stdout": redact(exc.stdout or ""),
            "stderr": redact(exc.stderr or ""),
            "timeout": True,
        }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def classify_tty_candidate(path: str, properties: str) -> dict[str, Any]:
    text = f"{path}\n{properties}"
    android_serial = bool(SAMSUNG_ANDROID_RE.search(text))
    uart_hint = bool(UART_HINT_RE.search(text))
    return {
        "path": path,
        "android_serial_hint": android_serial,
        "uart_adapter_hint": uart_hint,
        "usable_uart_candidate": bool(uart_hint and not android_serial),
    }


def inspect_host_uart(run_dir: Path) -> dict[str, Any]:
    listing = run_command(
        [
            "bash",
            "-lc",
            "find /dev/serial/by-id /dev/serial/by-path -maxdepth 1 -type l -print 2>/dev/null; "
            "ls -1 /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || true",
        ],
        timeout=10.0,
    )
    paths = sorted(set(re.findall(r"/dev/(?:ttyUSB|ttyACM)\d+|/dev/serial/by-(?:id|path)/\S+", listing["stdout"])))
    candidates: list[dict[str, Any]] = []
    udev_text_parts: list[str] = []
    for path in paths:
        prop = run_command(["bash", "-lc", f"udevadm info -q property -n {path!r} 2>/dev/null || true"], timeout=10.0)
        text = prop["stdout"] + prop["stderr"]
        udev_text_parts.append(f"## {path}\n{text}")
        candidates.append(classify_tty_candidate(path, text))
    write_text(run_dir / "host_uart_devices.txt", listing["stdout"] + listing["stderr"])
    write_text(run_dir / "host_uart_udev.txt", "\n".join(udev_text_parts))
    return {
        "tty_paths": paths,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "external_uart_candidate_count": sum(1 for item in candidates if item["usable_uart_candidate"]),
        "external_uart_ready": any(item["usable_uart_candidate"] for item in candidates),
    }


def prefix_manifest_ok(manifest: dict[str, Any], label: str, expected_count: int, expected_ap_sha: str, prefix_dir: Path) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    prefix = manifest.get("prefix") or {}
    safety = manifest.get("safety") or {}
    hashes = manifest.get("hashes") or {}
    paths = manifest.get("paths") or {}
    if manifest.get("target") != EXPECTED_TARGET:
        reasons.append("target-mismatch")
    if prefix.get("label") != label:
        reasons.append("label-mismatch")
    if prefix.get("count") != expected_count:
        reasons.append("prefix-count-mismatch")
    if hashes.get("ap_tar_md5") != expected_ap_sha:
        reasons.append("manifest-ap-sha-mismatch")
    if manifest.get("tar_members") != ["boot.img.lz4"]:
        reasons.append("tar-members-not-boot-only")
    required_safety = {
        "boot_only": True,
        "base_is_known_booting_magisk_boot": True,
        "block_device_writes": False,
        "configfs_runtime_gadget": False,
        "acm": False,
        "module_binary_injection": False,
        "persistent_partition_mount": False,
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            reasons.append(f"safety-{key}-mismatch")
    ap_path = prefix_dir / "odin4" / "AP.tar.md5"
    manifest_path = Path(paths.get("ap_tar_md5", ""))
    if not ap_path.is_file():
        reasons.append("ap-missing")
    else:
        actual = sha256_file(ap_path)
        if actual != expected_ap_sha:
            reasons.append("ap-file-sha-mismatch")
    if paths.get("ap_tar_md5") and manifest_path.name != "AP.tar.md5":
        reasons.append("manifest-ap-path-unexpected")
    return not reasons, reasons


def inspect_m18_prefix_artifacts(root: Path, requested: Path) -> dict[str, Any]:
    base = resolve(root, requested)
    top = load_json(base / "manifest.json")
    result: dict[str, Any] = {
        "path": str(base),
        "present": base.is_dir(),
        "top_manifest_present": top is not None,
        "prefixes": {},
    }
    if top is None:
        result["ready"] = False
        result["reasons"] = ["top-manifest-missing"]
        return result
    reasons: list[str] = []
    safety = top.get("safety") or {}
    if top.get("target") != EXPECTED_TARGET:
        reasons.append("top-target-mismatch")
    if safety.get("host_only_build") is not True:
        reasons.append("top-host-only-missing")
    if safety.get("live_flash_authorized") is not False:
        reasons.append("top-live-authorized-not-false")
    if safety.get("requires_fresh_sha_pinned_agents_exception_before_any_live_flash") is not True:
        reasons.append("top-fresh-exception-gate-missing")
    for label, count, sha in (("P00", 0, EXPECTED_P00_AP_SHA256), ("P10", 10, EXPECTED_P10_AP_SHA256)):
        prefix_dir = base / label
        manifest = load_json(prefix_dir / "manifest.json")
        if manifest is None:
            result["prefixes"][label] = {"ready": False, "reasons": ["manifest-missing"]}
            reasons.append(f"{label}-manifest-missing")
            continue
        ok, prefix_reasons = prefix_manifest_ok(manifest, label, count, sha, prefix_dir)
        result["prefixes"][label] = {
            "ready": ok,
            "count": count,
            "expected_ap_sha256": sha,
            "reasons": prefix_reasons,
        }
        reasons.extend(f"{label}-{reason}" for reason in prefix_reasons)
    result["ready"] = not reasons
    result["reasons"] = reasons
    return result


def build_eud_preflight(root: Path) -> dict[str, Any]:
    args = argparse.Namespace(
        run_dir=None,
        openocd=resolve(root, eud_gate.DEFAULT_OPENOCD),
        private_script_dir=resolve(root, eud_gate.DEFAULT_PRIVATE_SCRIPT_DIR),
        public_script_dir=resolve(root, eud_gate.DEFAULT_PUBLIC_SCRIPT_DIR),
        target_cfg=resolve(root, eud_gate.cfg_audit.DEFAULT_CFG),
        dtb=resolve(root, eud_gate.cfg_audit.DEFAULT_DTB),
        dtc=None,
        phase_b_summary=None,
        openocd_timeout_sec=20.0,
        offline_check=False,
        print_plan=False,
        require_ready=False,
        live=False,
        ack="",
    )
    run_dir, summary = eud_gate.build_preflight_report(root, args)
    return {
        "summary_path": str(run_dir / "summary.json"),
        "classification": summary["classification"],
        "ready": bool(summary["classification"]["ready"]),
    }


def choose_next(eud: dict[str, Any], uart: dict[str, Any], m18: dict[str, Any]) -> dict[str, Any]:
    if eud["ready"]:
        return {
            "recommended_next": "promote-eud-openocd-init-probe-live-gate",
            "reason": "EUD/OpenOCD is the strongest live observability path and host audit is ready.",
        }
    if uart["external_uart_ready"]:
        return {
            "recommended_next": "run-uart-console-capture-readiness",
            "reason": "A non-Android external UART adapter is visible on the host.",
        }
    if m18["ready"]:
        return {
            "recommended_next": "prepare-m18-prefix-p00-live-gate-source",
            "reason": "EUD is not enumerated and no external UART is visible; P00/P10 prefix artifacts are host-ready.",
        }
    return {
        "recommended_next": "blocked-no-observation-channel-ready",
        "reason": "EUD is not ready, no external UART candidate is visible, and M18 prefix artifacts did not validate.",
    }


def build_report(root: Path, args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    run_dir = resolve_run_dir(root, args.run_dir)
    eud = build_eud_preflight(root)
    uart = inspect_host_uart(run_dir)
    m18 = inspect_m18_prefix_artifacts(root, args.m18_prefix_root)
    decision = choose_next(eud, uart, m18)
    summary = {
        "generated_at_utc": utc_now(),
        "target": EXPECTED_TARGET,
        "device_action": False,
        "writes_performed": False,
        "reboots_performed": False,
        "flashes_performed": False,
        "sysfs_writes_performed": False,
        "openocd_init_performed": False,
        "eud_openocd": eud,
        "host_uart": uart,
        "m18_prefix": m18,
        "decision": decision,
    }
    write_text(run_dir / "summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return run_dir, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--m18-prefix-root", type=Path, default=DEFAULT_M18_PREFIX_ROOT)
    parser.add_argument("--require-actionable", action="store_true")
    args = parser.parse_args(argv)

    root = repo_root()
    run_dir, summary = build_report(root, args)
    decision = summary["decision"]
    print(
        "S22+ native-init observability frontier: "
        f"{decision['recommended_next']}; "
        f"eud_ready={int(summary['eud_openocd']['ready'])} "
        f"uart_ready={int(summary['host_uart']['external_uart_ready'])} "
        f"m18_prefix_ready={int(summary['m18_prefix']['ready'])}; "
        f"log={display_path(run_dir / 'summary.json')}"
    )
    if args.require_actionable and decision["recommended_next"] == "blocked-no-observation-channel-ready":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
