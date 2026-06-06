#!/usr/bin/env python3
"""V766 disposable ICNSS/QCACLD patch apply and build-readiness gate.

V765 generated a review-only A90V765 patch. V766 applies that patch to a
disposable source tree under private tmp evidence, then runs bounded build
readiness checks. It does not mutate kernel_build, build a full kernel, write a
boot image, or talk to the device.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import tarfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text, workspace_private_input_path


DEFAULT_OUT_DIR = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build")
DEFAULT_SOURCE_ARCHIVE = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel.tar.gz')
DEFAULT_PATCH_FILE = Path("tmp/wifi/v765-icnss-qcacld-log-patch/a90-v765-icnss-qcacld-log.patch")
DEFAULT_V765_MANIFEST = Path("tmp/wifi/v765-icnss-qcacld-log-patch/manifest.json")
PATCH_PREFIX = "A90V765"
DEFCONFIG = "r3q_kor_single_defconfig"

REQUIRED_PATCH_TARGETS = (
    "drivers/soc/qcom/icnss_qmi.c",
    "drivers/soc/qcom/icnss.c",
    "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/pld/src/pld_snoc.c",
    "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_main.c",
    "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c",
)

SAMSUNG_TOOLCHAIN_FILES = (
    "toolchain/gcc/linux-x86/aarch64/aarch64-linux-android-4.9/bin/aarch64-linux-android-gcc",
    "toolchain/llvm-arm-toolchain-ship/10.0/bin/clang",
)


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
    parser.add_argument("--source-archive", type=Path, default=DEFAULT_SOURCE_ARCHIVE)
    parser.add_argument("--patch-file", type=Path, default=DEFAULT_PATCH_FILE)
    parser.add_argument("--v765-manifest", type=Path, default=DEFAULT_V765_MANIFEST)
    parser.add_argument("--defconfig-timeout", type=float, default=120.0)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve_path(path: Path) -> Path:
    return path.expanduser() if path.is_absolute() else repo_path(path)


def load_json(path: Path) -> dict[str, Any]:
    resolved = resolve_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def file_info(path: Path) -> dict[str, Any]:
    resolved = resolve_path(path)
    if not resolved.exists():
        return {"path": str(resolved), "exists": False}
    return {
        "path": str(resolved),
        "exists": True,
        "is_file": resolved.is_file(),
        "is_dir": resolved.is_dir(),
        "size": resolved.stat().st_size if resolved.is_file() else None,
    }


def safe_member_path(name: str) -> Path | None:
    parts = [part for part in PurePosixPath(name).parts if part not in ("", ".")]
    if not parts:
        return None
    if parts[0] == "/" or any(part == ".." for part in parts):
        return None
    return Path(*parts)


def safe_symlink_target(target: str) -> bool:
    pure = PurePosixPath(target)
    return not pure.is_absolute() and ".." not in pure.parts


def safe_extract_tar(archive_path: Path, dest: Path) -> dict[str, Any]:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, mode=0o700)
    counts = {"dirs": 0, "files": 0, "symlinks": 0, "skipped": 0, "rejected": 0}
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive:
            rel = safe_member_path(member.name)
            if rel is None:
                counts["rejected"] += 1
                continue
            target = dest / rel
            if not target.resolve().is_relative_to(dest.resolve()):
                counts["rejected"] += 1
                continue
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                counts["dirs"] += 1
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    counts["skipped"] += 1
                    continue
                with source, target.open("wb") as handle:
                    shutil.copyfileobj(source, handle, length=1024 * 1024)
                os.chmod(target, member.mode & 0o777)
                counts["files"] += 1
            elif member.issym():
                if not safe_symlink_target(member.linkname):
                    counts["rejected"] += 1
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    target.symlink_to(member.linkname)
                    counts["symlinks"] += 1
                except FileExistsError:
                    counts["skipped"] += 1
            else:
                counts["skipped"] += 1
    return counts


def run_command(command: list[str], cwd: Path, timeout: float, output_file: Path) -> dict[str, Any]:
    started = dt.datetime.now(dt.timezone.utc)
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        output_file.write_text(result.stdout, encoding="utf-8", errors="replace")
        return {
            "command": command,
            "cwd": str(cwd),
            "rc": result.returncode,
            "timeout": False,
            "output_file": str(output_file),
            "started_at": started.isoformat(),
        }
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        output_file.write_text(output + "\n[TIMEOUT]\n", encoding="utf-8", errors="replace")
        return {
            "command": command,
            "cwd": str(cwd),
            "rc": None,
            "timeout": True,
            "output_file": str(output_file),
            "started_at": started.isoformat(),
        }


def find_existing(root: Path, suffixes: tuple[str, ...]) -> dict[str, str]:
    found: dict[str, str] = {}
    for suffix in suffixes:
        path = root / suffix
        found[suffix] = str(path) if path.exists() else ""
    return found


def marker_summary(source_root: Path) -> dict[str, Any]:
    per_file: dict[str, int] = {}
    literal_backslash_newline = 0
    total = 0
    for suffix in REQUIRED_PATCH_TARGETS:
        path = source_root / suffix
        if not path.exists():
            per_file[suffix] = -1
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        count = text.count(PATCH_PREFIX)
        per_file[suffix] = count
        total += count
        literal_backslash_newline += text.count("\\\\n")
    return {
        "prefix": PATCH_PREFIX,
        "total": total,
        "per_file": per_file,
        "literal_backslash_newline_count": literal_backslash_newline,
    }


def tool_readiness(source_root: Path) -> dict[str, Any]:
    samsung = {path: (source_root / path).exists() for path in SAMSUNG_TOOLCHAIN_FILES}
    host = {
        "make": shutil.which("make") or "",
        "patch": shutil.which("patch") or "",
        "aarch64-linux-gnu-gcc": shutil.which("aarch64-linux-gnu-gcc") or "",
        "clang": shutil.which("clang") or "",
    }
    return {
        "samsung_toolchain": samsung,
        "samsung_toolchain_ready": all(samsung.values()),
        "host_tools": host,
        "host_defconfig_ready": bool(host["make"] and host["aarch64-linux-gnu-gcc"]),
        "build_kernel_sh": str(source_root / "build_kernel.sh") if (source_root / "build_kernel.sh").exists() else "",
        "defconfig": str(source_root / "arch/arm64/configs" / DEFCONFIG)
        if (source_root / "arch/arm64/configs" / DEFCONFIG).exists()
        else "",
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(manifest: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    inputs = manifest["analysis"]["inputs"]
    route = manifest["analysis"]["route"]
    apply_result = manifest["analysis"].get("apply", {})
    markers = manifest["analysis"].get("markers", {})
    tools = manifest["analysis"].get("tools", {})
    defconfig = manifest["analysis"].get("defconfig", {})
    required_targets = route.get("required_targets") or {}
    missing_targets = [name for name, value in required_targets.items() if not value]
    add_check(
        checks,
        "v765-input",
        "pass" if inputs["v765"]["decision"] == "v765-icnss-qcacld-log-patch-ready" and inputs["v765"]["pass"] else "blocked",
        "blocker",
        f"decision={inputs['v765']['decision']} pass={inputs['v765']['pass']}",
        "rerun V765 before apply/build gate",
    )
    add_check(
        checks,
        "source-archive",
        "pass" if route["source_archive"]["exists"] and route["source_archive"].get("is_file") else "blocked",
        "blocker",
        f"exists={route['source_archive']['exists']} size={route['source_archive'].get('size')}",
        "stage Kernel.tar.gz before V766",
    )
    add_check(
        checks,
        "patch-file",
        "pass" if route["patch_file"]["exists"] and route["patch_file"].get("is_file") else "blocked",
        "blocker",
        f"exists={route['patch_file']['exists']} size={route['patch_file'].get('size')}",
        "generate V765 patch before V766",
    )
    if manifest["command"] == "plan":
        return checks
    add_check(
        checks,
        "safe-extract",
        "pass" if route["extract_counts"]["files"] > 0 and not missing_targets else "blocked",
        "blocker",
        f"files={route['extract_counts']['files']} rejected={route['extract_counts']['rejected']} skipped={route['extract_counts']['skipped']} missing_targets={missing_targets}",
        "inspect archive safety/extraction before patch apply",
    )
    add_check(
        checks,
        "patch-dry-run",
        "pass" if apply_result.get("dry_run", {}).get("rc") == 0 else "blocked",
        "blocker",
        f"rc={apply_result.get('dry_run', {}).get('rc')} timeout={apply_result.get('dry_run', {}).get('timeout')}",
        "fix patch context before applying to source tree",
    )
    add_check(
        checks,
        "patch-apply",
        "pass" if apply_result.get("apply", {}).get("rc") == 0 else "blocked",
        "blocker",
        f"rc={apply_result.get('apply', {}).get('rc')} timeout={apply_result.get('apply', {}).get('timeout')}",
        "do not build until patch applies cleanly",
    )
    add_check(
        checks,
        "marker-count",
        "pass" if markers.get("total") == 19 else "blocked",
        "blocker",
        f"total={markers.get('total')} per_file={markers.get('per_file')}",
        "reconcile generated patch coverage before build",
    )
    add_check(
        checks,
        "samsung-toolchain",
        "pass" if tools.get("samsung_toolchain_ready") else "warn",
        "warn",
        f"ready={tools.get('samsung_toolchain_ready')} files={tools.get('samsung_toolchain')}",
        "stage Samsung/Android clang+gcc toolchain or choose a host override build gate",
    )
    add_check(
        checks,
        "defconfig",
        "pass" if defconfig.get("rc") == 0 else "warn",
        "warn",
        f"rc={defconfig.get('rc')} timeout={defconfig.get('timeout')}",
        "fix defconfig environment before full kernel build",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v766-patch-apply-build-plan-ready",
            True,
            "plan-only; no extraction, patch apply, build, or device action executed",
            "run V766 disposable apply/build-readiness gate",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v766-patch-apply-build-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "fix patch/source blockers before build handoff",
        )
    defconfig = analysis.get("defconfig", {})
    tools = analysis.get("tools", {})
    if defconfig.get("rc") == 0 and tools.get("samsung_toolchain_ready"):
        return (
            "v766-patch-applied-defconfig-pass-toolchain-ready",
            True,
            "patch applied and defconfig passed; full build can be a separate bounded gate",
            "V767 may run bounded kernel build/package check; no boot image write yet",
        )
    if defconfig.get("rc") == 0:
        return (
            "v766-patch-applied-defconfig-pass-toolchain-incomplete",
            True,
            "patch applied and defconfig passed; official Samsung toolchain path is incomplete",
            "V767 should stage/select toolchain before full kernel build; no boot image write yet",
        )
    return (
        "v766-patch-applied-build-readiness-classified",
        True,
        "patch applied; build readiness classified without full kernel build",
        "V767 should fix build environment before full kernel build; no boot image write yet",
    )


def build_analysis(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    source_archive = resolve_path(args.source_archive)
    patch_file = resolve_path(args.patch_file)
    source_root = store.run_dir / "source"
    v765 = load_json(args.v765_manifest)
    analysis: dict[str, Any] = {
        "inputs": {
            "v765": {
                "manifest": str(resolve_path(args.v765_manifest)),
                "decision": v765.get("decision", ""),
                "pass": bool(v765.get("pass")),
            },
        },
        "route": {
            "source_archive": file_info(args.source_archive),
            "patch_file": file_info(args.patch_file),
            "source_root": str(source_root),
            "source_mutation_executed": False,
            "kernel_full_build_executed": False,
            "boot_image_write_executed": False,
            "device_commands_executed": False,
        },
    }
    if args.command == "plan":
        return analysis
    extract_counts = safe_extract_tar(source_archive, source_root)
    analysis["route"]["extract_counts"] = extract_counts
    analysis["route"]["required_targets"] = find_existing(source_root, REQUIRED_PATCH_TARGETS)
    patch_logs = store.run_dir / "logs"
    patch_logs.mkdir(mode=0o700, exist_ok=True)
    dry_run = run_command(
        ["patch", "-p1", "--dry-run", "-i", str(patch_file)],
        source_root,
        60.0,
        patch_logs / "patch-dry-run.txt",
    )
    applied: dict[str, Any] = {}
    if dry_run["rc"] == 0:
        applied = run_command(
            ["patch", "-p1", "-i", str(patch_file)],
            source_root,
            60.0,
            patch_logs / "patch-apply.txt",
        )
    else:
        applied = {"command": [], "cwd": str(source_root), "rc": None, "timeout": False, "output_file": ""}
    analysis["apply"] = {"dry_run": dry_run, "apply": applied}
    analysis["markers"] = marker_summary(source_root)
    analysis["tools"] = tool_readiness(source_root)
    defconfig_result: dict[str, Any] = {
        "executed": False,
        "rc": None,
        "timeout": False,
        "output_file": "",
    }
    if analysis["tools"]["host_defconfig_ready"] and applied.get("rc") == 0:
        dtc = source_root / "tools/dtc"
        defconfig_result = run_command(
            [
                "make",
                f"O={source_root / 'out'}",
                f"DTC_EXT={dtc}",
                "CONFIG_BUILD_ARM64_DT_OVERLAY=y",
                "ARCH=arm64",
                "CROSS_COMPILE=aarch64-linux-gnu-",
                DEFCONFIG,
            ],
            source_root,
            args.defconfig_timeout,
            patch_logs / "defconfig.txt",
        )
        defconfig_result["executed"] = True
    analysis["defconfig"] = defconfig_result
    return analysis


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    analysis = manifest.get("analysis") or {}
    route = analysis.get("route", {})
    markers = analysis.get("markers", {})
    tools = analysis.get("tools", {})
    return "\n".join([
        "# V766 ICNSS/QCACLD Patch Apply Build-readiness",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- source_mutation_executed: `{manifest['source_mutation_executed']}`",
        f"- kernel_full_build_executed: `{manifest['kernel_full_build_executed']}`",
        f"- boot_image_write_executed: `{manifest['boot_image_write_executed']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        "",
        "## Route",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in route.items()]),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in checks
        ]) if checks else "- plan only",
        "",
        "## Markers",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in markers.items()]) if markers else "- not run",
        "",
        "## Tools",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in tools.items()]) if tools else "- not run",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = build_analysis(args, store)
    manifest: dict[str, Any] = {
        "cycle": "v766",
        "generated_at": now_iso(),
        "command": args.command,
        "analysis": analysis,
        "source_mutation_executed": False,
        "kernel_full_build_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "device_commands_executed": False,
        "device_mutations": False,
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
    latest = repo_path("tmp/wifi/latest-v766-icnss-qcacld-patch-apply-build.txt")
    write_private_text(latest, str(store.run_dir.relative_to(repo_path(Path(".")))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"source_mutation_executed: {manifest['source_mutation_executed']}")
    print(f"kernel_full_build_executed: {manifest['kernel_full_build_executed']}")
    print(f"boot_image_write_executed: {manifest['boot_image_write_executed']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
