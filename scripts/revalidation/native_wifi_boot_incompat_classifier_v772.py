#!/usr/bin/env python3
"""V772 host-only diagnostic kernel boot incompatibility classifier.

V771 proved the V770 diagnostic boot image wrote correctly but failed to boot
native init and dropped to Download mode. This classifier compares the known-good
v724 kernel payload with the V769/V770 instrumented payload without flashing or
talking to the device.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v772-boot-incompat-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v772-boot-incompat-classifier.txt")
DEFAULT_BASE_KERNEL = Path("tmp/wifi/v770-instrumented-diagnostic-boot-staging/base-unpack/kernel")
DEFAULT_DIAG_KERNEL = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/out/arch/arm64/boot/Image-dtb")
DEFAULT_BASE_BOOT = Path("stage3/boot_linux_v724.img")
DEFAULT_DIAG_BOOT = Path("tmp/wifi/v770-instrumented-diagnostic-boot-staging/boot_linux_v770_icnss_diag.img")
DEFAULT_EXTRACT_IKCONFIG = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/scripts/extract-ikconfig")
DEFAULT_V771_REPORT = Path("docs/reports/NATIVE_INIT_V771_DIAGNOSTIC_LIVE_HANDOFF_BOOT_FAIL_2026-05-25.md")
FDT_MAGIC = b"\xd0\r\xfe\xed"
PATCH_MARKER = b"A90V765"
LINUX_VERSION_RE = re.compile(rb"Linux version [^\x00]+")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--base-kernel", type=Path, default=DEFAULT_BASE_KERNEL)
    parser.add_argument("--diag-kernel", type=Path, default=DEFAULT_DIAG_KERNEL)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--diag-boot", type=Path, default=DEFAULT_DIAG_BOOT)
    parser.add_argument("--extract-ikconfig", type=Path, default=DEFAULT_EXTRACT_IKCONFIG)
    parser.add_argument("--v771-report", type=Path, default=DEFAULT_V771_REPORT)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path.expanduser() if path.is_absolute() else repo_path(path)


def file_info(path: Path) -> dict[str, Any]:
    resolved = resolve(path)
    if not resolved.exists():
        return {"path": str(resolved), "exists": False}
    return {
        "path": str(resolved),
        "exists": True,
        "is_file": resolved.is_file(),
        "size": resolved.stat().st_size if resolved.is_file() else None,
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_offsets(path: Path, needle: bytes) -> list[int]:
    if not path.exists():
        return []
    data = path.read_bytes()
    offsets: list[int] = []
    index = data.find(needle)
    while index >= 0:
        offsets.append(index)
        index = data.find(needle, index + 1)
    return offsets


def count_bytes(path: Path, needle: bytes) -> int:
    return len(find_offsets(path, needle))


def linux_versions(path: Path) -> list[str]:
    if not path.exists():
        return []
    data = path.read_bytes()
    found: list[str] = []
    for match in LINUX_VERSION_RE.finditer(data):
        text = match.group(0).decode("utf-8", errors="replace")
        if text not in found:
            found.append(text)
        if len(found) >= 5:
            break
    return found


def extract_ikconfig(extractor: Path, kernel: Path, output: Path) -> dict[str, Any]:
    if not extractor.exists() or not kernel.exists():
        return {"rc": None, "exists": False, "output_file": str(output)}
    result = subprocess.run(
        ["bash", str(extractor), str(kernel)],
        cwd=repo_path(Path(".")),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60.0,
    )
    output.write_text(result.stdout, encoding="utf-8", errors="replace")
    if result.stderr:
        output.with_suffix(output.suffix + ".stderr").write_text(result.stderr, encoding="utf-8", errors="replace")
    return {
        "rc": result.returncode,
        "output_file": str(output),
        "line_count": len(result.stdout.splitlines()),
        "sha256": hashlib.sha256(result.stdout.encode("utf-8", errors="replace")).hexdigest(),
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def analyze(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    base_kernel = resolve(args.base_kernel)
    diag_kernel = resolve(args.diag_kernel)
    base_boot = resolve(args.base_boot)
    diag_boot = resolve(args.diag_boot)
    extractor = resolve(args.extract_ikconfig)
    v771_report = resolve(args.v771_report)
    base_fdt_offsets = find_offsets(base_kernel, FDT_MAGIC)
    diag_fdt_offsets = find_offsets(diag_kernel, FDT_MAGIC)
    logs = store.run_dir / "logs"
    logs.mkdir(parents=True, mode=0o700, exist_ok=True)
    if args.command == "run":
        base_config = extract_ikconfig(extractor, base_kernel, logs / "base-ikconfig.txt")
        diag_config = extract_ikconfig(extractor, diag_kernel, logs / "diag-ikconfig.txt")
    else:
        base_config = {"rc": None, "output_file": "", "line_count": 0, "sha256": ""}
        diag_config = {"rc": None, "output_file": "", "line_count": 0, "sha256": ""}

    first_base_fdt = base_fdt_offsets[0] if base_fdt_offsets else None
    base_dtb_tail_size = base_kernel.stat().st_size - first_base_fdt if first_base_fdt is not None and base_kernel.exists() else 0
    return {
        "paths": {
            "base_kernel": file_info(base_kernel),
            "diag_kernel": file_info(diag_kernel),
            "base_boot": file_info(base_boot),
            "diag_boot": file_info(diag_boot),
            "extract_ikconfig": file_info(extractor),
            "v771_report": file_info(v771_report),
        },
        "hashes": {
            "base_kernel_sha256": sha256(base_kernel) if base_kernel.exists() else "",
            "diag_kernel_sha256": sha256(diag_kernel) if diag_kernel.exists() else "",
            "base_boot_sha256": sha256(base_boot) if base_boot.exists() else "",
            "diag_boot_sha256": sha256(diag_boot) if diag_boot.exists() else "",
        },
        "payload": {
            "base_kernel_size": base_kernel.stat().st_size if base_kernel.exists() else 0,
            "diag_kernel_size": diag_kernel.stat().st_size if diag_kernel.exists() else 0,
            "size_delta_diag_minus_base": (
                diag_kernel.stat().st_size - base_kernel.stat().st_size
                if base_kernel.exists() and diag_kernel.exists()
                else None
            ),
            "base_fdt_count": len(base_fdt_offsets),
            "diag_fdt_count": len(diag_fdt_offsets),
            "base_fdt_offsets": base_fdt_offsets,
            "diag_fdt_offsets": diag_fdt_offsets,
            "base_first_fdt_offset": first_base_fdt,
            "base_dtb_tail_size": base_dtb_tail_size,
            "diag_patch_marker_count": count_bytes(diag_kernel, PATCH_MARKER),
            "base_patch_marker_count": count_bytes(base_kernel, PATCH_MARKER),
        },
        "version_strings": {
            "base": linux_versions(base_kernel),
            "diag": linux_versions(diag_kernel),
        },
        "ikconfig": {
            "base": base_config,
            "diag": diag_config,
            "hash_matches": bool(base_config.get("sha256")) and base_config.get("sha256") == diag_config.get("sha256"),
        },
        "device_commands_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
    }


def build_checks(manifest: dict[str, Any]) -> list[Check]:
    analysis = manifest["analysis"]
    paths = analysis["paths"]
    payload = analysis["payload"]
    checks: list[Check] = []
    add_check(
        checks,
        "base-kernel",
        "pass" if paths["base_kernel"].get("exists") and paths["base_kernel"].get("is_file") else "blocked",
        "blocker",
        f"exists={paths['base_kernel'].get('exists')} size={paths['base_kernel'].get('size')}",
        "restore or unpack the known-good v724 kernel payload",
    )
    add_check(
        checks,
        "diag-kernel",
        "pass" if paths["diag_kernel"].get("exists") and paths["diag_kernel"].get("is_file") else "blocked",
        "blocker",
        f"exists={paths['diag_kernel'].get('exists')} size={paths['diag_kernel'].get('size')}",
        "rerun V769/V770 to make the diagnostic kernel payload available",
    )
    add_check(
        checks,
        "v771-failure-report",
        "pass" if paths["v771_report"].get("exists") else "blocked",
        "blocker",
        f"exists={paths['v771_report'].get('exists')}",
        "document V771 live failure before classifying it",
    )
    add_check(
        checks,
        "base-appended-dtb",
        "pass" if payload.get("base_fdt_count", 0) > 0 else "blocked",
        "blocker",
        f"base_fdt_count={payload.get('base_fdt_count')} offsets={payload.get('base_fdt_offsets')}",
        "verify the known-good kernel has appended DTB payloads",
    )
    add_check(
        checks,
        "diag-appended-dtb",
        "blocked" if payload.get("diag_fdt_count", 0) == 0 else "pass",
        "blocker",
        f"diag_fdt_count={payload.get('diag_fdt_count')} offsets={payload.get('diag_fdt_offsets')}",
        "do not flash again until the diagnostic kernel includes a boot-compatible appended DTB tail",
    )
    add_check(
        checks,
        "ikconfig-parity",
        "pass" if analysis["ikconfig"].get("hash_matches") else "review",
        "warn",
        f"hash_matches={analysis['ikconfig'].get('hash_matches')} base_lines={analysis['ikconfig']['base'].get('line_count')} diag_lines={analysis['ikconfig']['diag'].get('line_count')}",
        "if config differs, inspect config delta before any further packaging",
    )
    add_check(
        checks,
        "instrumentation-markers",
        "pass" if payload.get("diag_patch_marker_count") == 19 else "blocked",
        "blocker",
        f"diag_patch_marker_count={payload.get('diag_patch_marker_count')}",
        "rerun V769 if instrumentation markers are not preserved",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v772-boot-incompat-classifier-plan-ready",
            True,
            "plan-only; no device command, flash, partition write, or Wi-Fi action executed",
            "run V772 host-only boot incompatibility classifier",
        )
    if analysis["payload"].get("base_fdt_count", 0) > 0 and analysis["payload"].get("diag_fdt_count", 0) == 0:
        return (
            "v772-boot-fail-likely-missing-appended-dtb",
            True,
            "known-good v724 kernel has appended FDT/DTB payloads, but the V770 diagnostic kernel payload has none",
            "V773 should create a local-only diagnostic kernel by appending the stock v724 DTB tail to the V769 instrumented Image before any flash",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v772-boot-incompat-classifier-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "fix classifier inputs before another live kernel test",
        )
    return (
        "v772-boot-incompat-not-explained",
        True,
        "host-only artifact checks did not find a decisive boot incompatibility",
        "inspect bootloader logs, AVB constraints, and production kernel build deltas before any further flash",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    analysis = manifest.get("analysis") or {}
    payload = analysis.get("payload") or {}
    return "\n".join([
        "# V772 Boot Incompatibility Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- partition_write_executed: `{manifest['partition_write_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in checks
        ]),
        "",
        "## Payload",
        "",
        markdown_table(["signal", "value"], [
            ["base_kernel_size", payload.get("base_kernel_size")],
            ["diag_kernel_size", payload.get("diag_kernel_size")],
            ["size_delta_diag_minus_base", payload.get("size_delta_diag_minus_base")],
            ["base_fdt_count", payload.get("base_fdt_count")],
            ["diag_fdt_count", payload.get("diag_fdt_count")],
            ["base_dtb_tail_size", payload.get("base_dtb_tail_size")],
            ["diag_patch_marker_count", payload.get("diag_patch_marker_count")],
        ]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = analyze(args, store)
    manifest: dict[str, Any] = {
        "cycle": "v772",
        "generated_at": now_iso(),
        "command": args.command,
        "analysis": analysis,
        "device_commands_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "host": collect_host_metadata(),
    }
    checks = build_checks(manifest)
    decision, ok, reason, next_step = decide(args.command, checks, analysis)
    manifest.update({
        "checks": [asdict(check) for check in checks],
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
    })
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(LATEST_POINTER, str(store.run_dir.relative_to(repo_path(Path(".")))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"partition_write_executed: {manifest['partition_write_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
