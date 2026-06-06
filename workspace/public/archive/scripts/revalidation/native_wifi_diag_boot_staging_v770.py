#!/usr/bin/env python3
"""V770 local-only instrumented diagnostic boot image staging gate.

V769 produced an ICNSS/QCACLD-instrumented Image-dtb. V770 repacks that kernel
with the current verified native-init ramdisk/header metadata into a local
diagnostic boot image under tmp evidence. It does not flash, reboot, push to the
device, start daemons, scan/connect Wi-Fi, use credentials, DHCP, routes, or
external ping.
"""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v770-instrumented-diagnostic-boot-staging")
LATEST_POINTER = Path("tmp/wifi/latest-v770-instrumented-diagnostic-boot-staging.txt")
DEFAULT_BASE_BOOT = Path("stage3/boot_linux_v724.img")
DEFAULT_KERNEL_IMAGE = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/out/arch/arm64/boot/Image-dtb")
DEFAULT_V769_MANIFEST = Path("tmp/wifi/v769-rkp-cfp-python3-packaging/manifest.json")
BOOT_BLOCK_SIZE = 4096
INIT_MARKER = b"A90 Linux init 0.9.68 (v724)"
PATCH_MARKER = b"A90V765"


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
    parser.add_argument("--kernel-image", type=Path, default=DEFAULT_KERNEL_IMAGE)
    parser.add_argument("--v769-manifest", type=Path, default=DEFAULT_V769_MANIFEST)
    parser.add_argument("--output-boot", type=Path, default=None)
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


def count_bytes(path: Path, needle: bytes) -> int:
    if not path.exists():
        return 0
    count = 0
    overlap = max(len(needle) - 1, 0)
    previous = b""
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            data = previous + chunk
            count += data.count(needle)
            previous = data[-overlap:] if overlap else b""
    return count


def run_command(command: list[str],
                cwd: Path,
                output_file: Path,
                timeout: float = 180.0) -> dict[str, Any]:
    started = now_iso()
    try:
        result = subprocess.run(
            [str(item) for item in command],
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        output_file.write_text(result.stdout, encoding="utf-8", errors="replace")
        return {
            "command": [str(item) for item in command],
            "cwd": str(cwd),
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
        return {
            "command": [str(item) for item in command],
            "cwd": str(cwd),
            "rc": None,
            "timeout": True,
            "output_file": str(output_file),
            "started_at": started,
        }


def replace_arg(args: list[str], flag: str, value: Path) -> None:
    for index, item in enumerate(args):
        if item == flag and index + 1 < len(args):
            args[index + 1] = str(value)
            return
    raise RuntimeError(f"missing mkbootimg flag: {flag}")


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def stage_boot(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    logs = store.run_dir / "logs"
    logs.mkdir(parents=True, mode=0o700, exist_ok=True)
    unpack_dir = store.run_dir / "base-unpack"
    verify_dir = store.run_dir / "verify-unpack"
    unpack_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
    verify_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
    base_boot = resolve(args.base_boot)
    kernel_image = resolve(args.kernel_image)
    output_boot = resolve(args.output_boot) if args.output_boot else store.run_dir / "boot_linux_v770_icnss_diag.img"

    unpack = run_command(
        [
            sys.executable,
            repo_path("mkbootimg/unpack_bootimg.py"),
            "--boot_img",
            base_boot,
            "--out",
            unpack_dir,
            "--format=mkbootimg",
        ],
        repo_path(Path(".")),
        logs / "unpack-base.txt",
    )
    mkboot_args_text = Path(unpack["output_file"]).read_text(encoding="utf-8", errors="replace") if unpack["rc"] == 0 else ""
    mkboot_args = shlex.split(mkboot_args_text) if mkboot_args_text else []
    if unpack["rc"] == 0:
        replace_arg(mkboot_args, "--kernel", kernel_image)
        replace_arg(mkboot_args, "--ramdisk", unpack_dir / "ramdisk")
        if output_boot.exists():
            output_boot.unlink()
        mkboot = run_command(
            [
                sys.executable,
                repo_path("mkbootimg/mkbootimg.py"),
                *mkboot_args,
                "--output",
                output_boot,
            ],
            repo_path(Path(".")),
            logs / "mkbootimg.txt",
        )
    else:
        mkboot = {"command": [], "cwd": str(repo_path(Path("."))), "rc": None, "timeout": False, "output_file": ""}

    if mkboot.get("rc") == 0 and output_boot.exists():
        output_boot.chmod(0o600)

    if mkboot.get("rc") == 0 and output_boot.exists():
        verify_unpack = run_command(
            [
                sys.executable,
                repo_path("mkbootimg/unpack_bootimg.py"),
                "--boot_img",
                output_boot,
                "--out",
                verify_dir,
                "--format=mkbootimg",
            ],
            repo_path(Path(".")),
            logs / "unpack-staged.txt",
        )
    else:
        verify_unpack = {"command": [], "cwd": str(repo_path(Path("."))), "rc": None, "timeout": False, "output_file": ""}

    extracted_kernel = verify_dir / "kernel"
    return {
        "base_unpack": unpack,
        "mkbootimg": mkboot,
        "verify_unpack": verify_unpack,
        "mkboot_args_file": str(logs / "unpack-base.txt"),
        "output_boot": file_info(output_boot),
        "output_boot_sha256": sha256(output_boot) if output_boot.exists() else "",
        "base_boot_sha256": sha256(base_boot) if base_boot.exists() else "",
        "kernel_image_sha256": sha256(kernel_image) if kernel_image.exists() else "",
        "extracted_kernel": file_info(extracted_kernel),
        "extracted_kernel_sha256": sha256(extracted_kernel) if extracted_kernel.exists() else "",
        "kernel_hash_matches": extracted_kernel.exists() and kernel_image.exists() and sha256(extracted_kernel) == sha256(kernel_image),
        "output_size_aligned": output_boot.exists() and output_boot.stat().st_size % BOOT_BLOCK_SIZE == 0,
        "init_marker_count": count_bytes(output_boot, INIT_MARKER) if output_boot.exists() else 0,
        "patch_marker_count": count_bytes(output_boot, PATCH_MARKER) if output_boot.exists() else 0,
        "local_boot_image_created": output_boot.exists(),
    }


def build_analysis(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v769_manifest = load_json(args.v769_manifest)
    kernel_image = resolve(args.kernel_image)
    base_boot = resolve(args.base_boot)
    analysis: dict[str, Any] = {
        "inputs": {
            "v769": {
                "path": v769_manifest.get("path"),
                "exists": v769_manifest.get("exists", False),
                "decision": v769_manifest.get("decision", ""),
                "pass": bool(v769_manifest.get("pass")),
            },
        },
        "paths": {
            "base_boot": file_info(base_boot),
            "kernel_image": file_info(kernel_image),
            "output_boot": {"path": str(resolve(args.output_boot)) if args.output_boot else str(store.run_dir / "boot_linux_v770_icnss_diag.img")},
        },
        "kernel_patch_marker_count": count_bytes(kernel_image, PATCH_MARKER),
        "base_init_marker_count": count_bytes(base_boot, INIT_MARKER),
        "stage": {},
        "local_boot_image_created": False,
        "device_commands_executed": False,
        "partition_write_executed": False,
    }
    if args.command == "plan":
        return analysis
    stage = stage_boot(args, store)
    analysis["stage"] = stage
    analysis["local_boot_image_created"] = bool(stage.get("local_boot_image_created"))
    return analysis


def build_checks(manifest: dict[str, Any]) -> list[Check]:
    analysis = manifest["analysis"]
    checks: list[Check] = []
    v769_input = analysis["inputs"]["v769"]
    paths = analysis["paths"]
    add_check(
        checks,
        "v769-input",
        "pass" if v769_input.get("exists") and v769_input.get("pass") and v769_input.get("decision") == "v769-rkp-cfp-python3-repair-image-pass" else "blocked",
        "blocker",
        f"decision={v769_input.get('decision')} pass={v769_input.get('pass')}",
        "rerun V769 until instrumented Image-dtb is ready",
    )
    add_check(
        checks,
        "base-boot",
        "pass" if paths["base_boot"].get("exists") and paths["base_boot"].get("is_file") and analysis.get("base_init_marker_count", 0) > 0 else "blocked",
        "blocker",
        f"exists={paths['base_boot'].get('exists')} init_marker_count={analysis.get('base_init_marker_count')}",
        "provide a verified native-init base boot image",
    )
    add_check(
        checks,
        "instrumented-kernel",
        "pass" if paths["kernel_image"].get("exists") and paths["kernel_image"].get("is_file") and analysis.get("kernel_patch_marker_count") == 19 else "blocked",
        "blocker",
        f"exists={paths['kernel_image'].get('exists')} patch_marker_count={analysis.get('kernel_patch_marker_count')}",
        "rerun V769 or provide the instrumented Image-dtb",
    )
    if manifest["command"] == "plan":
        return checks
    stage = analysis.get("stage") or {}
    add_check(
        checks,
        "mkbootimg",
        "pass" if (stage.get("mkbootimg") or {}).get("rc") == 0 else "blocked",
        "blocker",
        f"rc={(stage.get('mkbootimg') or {}).get('rc')} timeout={(stage.get('mkbootimg') or {}).get('timeout')}",
        "inspect mkbootimg arguments and base boot unpack output",
    )
    add_check(
        checks,
        "staged-boot",
        "pass" if (stage.get("output_boot") or {}).get("exists") and stage.get("output_size_aligned") else "blocked",
        "blocker",
        f"exists={(stage.get('output_boot') or {}).get('exists')} aligned={stage.get('output_size_aligned')}",
        "rebuild local diagnostic boot image",
    )
    add_check(
        checks,
        "kernel-roundtrip",
        "pass" if stage.get("kernel_hash_matches") else "blocked",
        "blocker",
        f"kernel_hash_matches={stage.get('kernel_hash_matches')}",
        "unpack staged boot and verify embedded kernel hash",
    )
    add_check(
        checks,
        "markers",
        "pass" if stage.get("init_marker_count", 0) > 0 and stage.get("patch_marker_count") == 19 else "blocked",
        "blocker",
        f"init_marker_count={stage.get('init_marker_count')} patch_marker_count={stage.get('patch_marker_count')}",
        "verify native ramdisk marker and A90V765 instrumentation markers",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v770-instrumented-diagnostic-boot-staging-plan-ready",
            True,
            "plan-only; no local boot image, device command, partition write, flash, reboot, or Wi-Fi action executed",
            "run V770 local-only diagnostic boot image staging gate",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v770-instrumented-diagnostic-boot-staging-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "fix staging blocker before any live handoff",
        )
    return (
        "v770-instrumented-diagnostic-boot-staged",
        True,
        "local diagnostic boot image contains the V769 instrumented kernel and verified native-init ramdisk marker",
        "next gate may flash this local artifact under explicit live handoff rules, then capture A90V765 dmesg markers",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    analysis = manifest.get("analysis") or {}
    stage = analysis.get("stage") or {}
    return "\n".join([
        "# V770 Instrumented Diagnostic Boot Staging",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- local_boot_image_created: `{manifest['local_boot_image_created']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- partition_write_executed: `{manifest['partition_write_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in checks
        ]) if checks else "- none",
        "",
        "## Staged Boot",
        "",
        markdown_table(["signal", "value"], [
            ["output_boot", (stage.get("output_boot") or {}).get("path", "")],
            ["output_size", (stage.get("output_boot") or {}).get("size", "")],
            ["sha256", stage.get("output_boot_sha256", "")],
            ["kernel_hash_matches", stage.get("kernel_hash_matches", "")],
            ["init_marker_count", stage.get("init_marker_count", "")],
            ["patch_marker_count", stage.get("patch_marker_count", "")],
        ]) if stage else "- not run",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = build_analysis(args, store)
    manifest: dict[str, Any] = {
        "cycle": "v770",
        "generated_at": now_iso(),
        "command": args.command,
        "analysis": analysis,
        "local_boot_image_created": bool(analysis.get("local_boot_image_created")),
        "device_boot_image_write_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
        "device_commands_executed": False,
        "service_manager_start_executed": False,
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
    print(f"local_boot_image_created: {manifest['local_boot_image_created']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"partition_write_executed: {manifest['partition_write_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
