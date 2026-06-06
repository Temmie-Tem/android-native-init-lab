#!/usr/bin/env python3
"""V773 local-only stock-DTB-tail diagnostic boot repack gate."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v773-stock-dtb-tail-repack")
LATEST_POINTER = Path("tmp/wifi/latest-v773-stock-dtb-tail-repack.txt")
DEFAULT_BASE_BOOT = Path("stage3/boot_linux_v724.img")
DEFAULT_BASE_KERNEL = Path("tmp/wifi/v770-instrumented-diagnostic-boot-staging/base-unpack/kernel")
DEFAULT_DIAG_KERNEL = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/out/arch/arm64/boot/Image-dtb")
DEFAULT_V772_MANIFEST = Path("tmp/wifi/v772-boot-incompat-classifier/manifest.json")
FDT_MAGIC = b"\xd0\r\xfe\xed"
PATCH_MARKER = b"A90V765"
INIT_MARKER = b"A90 Linux init 0.9.68 (v724)"
BOOT_BLOCK_SIZE = 4096


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
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--base-kernel", type=Path, default=DEFAULT_BASE_KERNEL)
    parser.add_argument("--diag-kernel", type=Path, default=DEFAULT_DIAG_KERNEL)
    parser.add_argument("--v772-manifest", type=Path, default=DEFAULT_V772_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path.expanduser() if path.is_absolute() else repo_path(path)


def load_json(path: Path) -> dict[str, Any]:
    resolved = resolve(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "error": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "error": "not-json-object"}
    data["exists"] = True
    data["path"] = str(resolved)
    return data


def file_info(path: Path) -> dict[str, Any]:
    resolved = resolve(path)
    if not resolved.exists():
        return {"path": str(resolved), "exists": False}
    return {
        "path": str(resolved),
        "exists": True,
        "is_file": resolved.is_file(),
        "is_dir": resolved.is_dir(),
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


def run_command(command: list[str], output_file: Path, timeout: float = 180.0) -> dict[str, Any]:
    started = now_iso()
    try:
        result = subprocess.run(
            [str(item) for item in command],
            cwd=repo_path(Path(".")),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        output_file.write_text(result.stdout, encoding="utf-8", errors="replace")
        return {
            "command": [str(item) for item in command],
            "rc": result.returncode,
            "timeout": False,
            "output_file": str(output_file),
            "started_at": started,
        }
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        output_file.write_text(output + "\n[TIMEOUT]\n", encoding="utf-8", errors="replace")
        return {"command": [str(item) for item in command], "rc": None, "timeout": True, "output_file": str(output_file), "started_at": started}


def replace_arg(args: list[str], flag: str, value: Path) -> None:
    for index, item in enumerate(args):
        if item == flag and index + 1 < len(args):
            args[index + 1] = str(value)
            return
    raise RuntimeError(f"missing mkbootimg flag: {flag}")


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def stage(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    logs = store.run_dir / "logs"
    logs.mkdir(parents=True, mode=0o700, exist_ok=True)
    base_boot = resolve(args.base_boot)
    base_kernel = resolve(args.base_kernel)
    diag_kernel = resolve(args.diag_kernel)
    base_offsets = find_offsets(base_kernel, FDT_MAGIC)
    first_fdt = base_offsets[0] if base_offsets else None
    combined_kernel = store.run_dir / "instrumented-image-with-stock-dtb-tail.bin"
    output_boot = store.run_dir / "boot_linux_v773_icnss_diag_stockdtb.img"
    base_unpack = store.run_dir / "base-unpack"
    verify_unpack = store.run_dir / "verify-unpack"
    base_unpack.mkdir(parents=True, mode=0o700, exist_ok=True)
    verify_unpack.mkdir(parents=True, mode=0o700, exist_ok=True)

    if first_fdt is not None and base_kernel.exists() and diag_kernel.exists():
        tail = base_kernel.read_bytes()[first_fdt:]
        combined_kernel.write_bytes(diag_kernel.read_bytes() + tail)
        combined_kernel.chmod(0o600)

    unpack = run_command(
        [
            sys.executable,
            repo_path("mkbootimg/unpack_bootimg.py"),
            "--boot_img",
            base_boot,
            "--out",
            base_unpack,
            "--format=mkbootimg",
        ],
        logs / "unpack-base.txt",
    )
    mkboot_args_text = Path(unpack["output_file"]).read_text(encoding="utf-8", errors="replace") if unpack["rc"] == 0 else ""
    mkboot_args = shlex.split(mkboot_args_text) if mkboot_args_text else []
    if unpack["rc"] == 0 and combined_kernel.exists():
        replace_arg(mkboot_args, "--kernel", combined_kernel)
        replace_arg(mkboot_args, "--ramdisk", base_unpack / "ramdisk")
        mkboot = run_command(
            [sys.executable, repo_path("mkbootimg/mkbootimg.py"), *mkboot_args, "--output", output_boot],
            logs / "mkbootimg.txt",
        )
        if output_boot.exists():
            output_boot.chmod(0o600)
    else:
        mkboot = {"command": [], "rc": None, "timeout": False, "output_file": ""}

    if mkboot.get("rc") == 0 and output_boot.exists():
        verify = run_command(
            [
                sys.executable,
                repo_path("mkbootimg/unpack_bootimg.py"),
                "--boot_img",
                output_boot,
                "--out",
                verify_unpack,
                "--format=mkbootimg",
            ],
            logs / "unpack-staged.txt",
        )
    else:
        verify = {"command": [], "rc": None, "timeout": False, "output_file": ""}
    extracted_kernel = verify_unpack / "kernel"
    return {
        "base_fdt_offsets": base_offsets,
        "base_first_fdt_offset": first_fdt,
        "stock_dtb_tail_size": base_kernel.stat().st_size - first_fdt if first_fdt is not None and base_kernel.exists() else 0,
        "combined_kernel": file_info(combined_kernel),
        "combined_kernel_sha256": sha256(combined_kernel) if combined_kernel.exists() else "",
        "combined_fdt_offsets": find_offsets(combined_kernel, FDT_MAGIC),
        "combined_fdt_count": count_bytes(combined_kernel, FDT_MAGIC),
        "combined_patch_marker_count": count_bytes(combined_kernel, PATCH_MARKER),
        "unpack_base": unpack,
        "mkbootimg": mkboot,
        "verify_unpack": verify,
        "output_boot": file_info(output_boot),
        "output_boot_sha256": sha256(output_boot) if output_boot.exists() else "",
        "output_size_aligned": output_boot.exists() and output_boot.stat().st_size % BOOT_BLOCK_SIZE == 0,
        "output_init_marker_count": count_bytes(output_boot, INIT_MARKER),
        "output_patch_marker_count": count_bytes(output_boot, PATCH_MARKER),
        "extracted_kernel": file_info(extracted_kernel),
        "extracted_kernel_sha256": sha256(extracted_kernel) if extracted_kernel.exists() else "",
        "kernel_roundtrip_hash_matches": extracted_kernel.exists() and combined_kernel.exists() and sha256(extracted_kernel) == sha256(combined_kernel),
    }


def analyze(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v772 = load_json(args.v772_manifest)
    analysis: dict[str, Any] = {
        "inputs": {
            "v772": {"path": v772.get("path"), "exists": v772.get("exists", False), "decision": v772.get("decision", ""), "pass": bool(v772.get("pass"))},
        },
        "paths": {
            "base_boot": file_info(args.base_boot),
            "base_kernel": file_info(args.base_kernel),
            "diag_kernel": file_info(args.diag_kernel),
        },
        "stage": {},
        "device_commands_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
    }
    if args.command == "run":
        analysis["stage"] = stage(args, store)
    return analysis


def build_checks(manifest: dict[str, Any]) -> list[Check]:
    analysis = manifest["analysis"]
    stage_data = analysis.get("stage") or {}
    checks: list[Check] = []
    v772 = analysis["inputs"]["v772"]
    add_check(checks, "v772-input", "pass" if v772.get("exists") and v772.get("pass") and v772.get("decision") == "v772-boot-fail-likely-missing-appended-dtb" else "blocked", "blocker", f"decision={v772.get('decision')} pass={v772.get('pass')}", "rerun V772 before V773")
    add_check(checks, "base-kernel", "pass" if analysis["paths"]["base_kernel"].get("exists") else "blocked", "blocker", f"exists={analysis['paths']['base_kernel'].get('exists')}", "restore known-good v724 kernel payload")
    add_check(checks, "diag-kernel", "pass" if analysis["paths"]["diag_kernel"].get("exists") else "blocked", "blocker", f"exists={analysis['paths']['diag_kernel'].get('exists')}", "rerun V769/V770 source build")
    if manifest["command"] == "plan":
        return checks
    add_check(checks, "combined-kernel", "pass" if (stage_data.get("combined_kernel") or {}).get("exists") else "blocked", "blocker", f"exists={(stage_data.get('combined_kernel') or {}).get('exists')} size={(stage_data.get('combined_kernel') or {}).get('size')}", "create combined kernel payload")
    add_check(checks, "combined-fdt", "pass" if stage_data.get("combined_fdt_count") == 3 else "blocked", "blocker", f"count={stage_data.get('combined_fdt_count')} offsets={stage_data.get('combined_fdt_offsets')}", "append stock DTB tail and verify FDT magic")
    add_check(checks, "instrumentation-markers", "pass" if stage_data.get("combined_patch_marker_count") == 19 else "blocked", "blocker", f"markers={stage_data.get('combined_patch_marker_count')}", "preserve A90V765 markers in combined payload")
    add_check(checks, "mkbootimg", "pass" if (stage_data.get("mkbootimg") or {}).get("rc") == 0 else "blocked", "blocker", f"rc={(stage_data.get('mkbootimg') or {}).get('rc')}", "repack local boot image")
    add_check(checks, "roundtrip", "pass" if stage_data.get("kernel_roundtrip_hash_matches") else "blocked", "blocker", f"kernel_roundtrip_hash_matches={stage_data.get('kernel_roundtrip_hash_matches')}", "unpack staged boot and verify kernel hash")
    add_check(checks, "boot-markers", "pass" if stage_data.get("output_init_marker_count", 0) > 0 and stage_data.get("output_patch_marker_count") == 19 else "blocked", "blocker", f"init={stage_data.get('output_init_marker_count')} patch={stage_data.get('output_patch_marker_count')}", "verify native-init and instrumentation markers in staged boot")
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return ("v773-stock-dtb-tail-repack-plan-ready", True, "plan-only; no device command, flash, partition write, or Wi-Fi action executed", "run V773 local-only stock-DTB-tail repack")
    blockers = blocking(checks)
    if blockers:
        return ("v773-stock-dtb-tail-repack-blocked", False, "blocked by " + ", ".join(blockers), "fix local repack blocker before live handoff")
    return ("v773-stock-dtb-tail-diagnostic-boot-staged", True, "local diagnostic boot image now includes stock v724 appended DTB tail and preserves A90V765 markers", "review V773 evidence before considering a separate live flash gate")


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    stage_data = (manifest.get("analysis") or {}).get("stage") or {}
    return "\n".join([
        "# V773 Stock DTB Tail Repack",
        "",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- partition_write_executed: `{manifest['partition_write_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in checks]),
        "",
        "## Stage",
        "",
        markdown_table(["signal", "value"], [
            ["combined_kernel", (stage_data.get("combined_kernel") or {}).get("path", "")],
            ["combined_fdt_count", stage_data.get("combined_fdt_count", "")],
            ["stock_dtb_tail_size", stage_data.get("stock_dtb_tail_size", "")],
            ["combined_patch_marker_count", stage_data.get("combined_patch_marker_count", "")],
            ["output_boot", (stage_data.get("output_boot") or {}).get("path", "")],
            ["output_boot_sha256", stage_data.get("output_boot_sha256", "")],
            ["kernel_roundtrip_hash_matches", stage_data.get("kernel_roundtrip_hash_matches", "")],
        ]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = analyze(args, store)
    manifest: dict[str, Any] = {
        "cycle": "v773",
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
    decision, ok, reason, next_step = decide(args.command, checks)
    manifest.update({"checks": [asdict(check) for check in checks], "decision": decision, "pass": ok, "reason": reason, "next_step": next_step})
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
