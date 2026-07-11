#!/usr/bin/env python3
"""Preflight or run the pinned S22+ FYG8 stock-configuration kernel build.

The default action is preflight only. A build never packages a boot image and
never contacts a device. Full LTO is refused unless the host has nominal 32 GiB
physical RAM (at least 30 GiB visible) plus swap headroom.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_kernel_build_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
SOURCE_DATE_EPOCH = 1754027756
STOCK_TIMESTAMP = "Fri Aug 1 05:55:56 UTC 2025"
STOCK_LOCALVERSION = "-android12-9-30958166-abS906NKSS7FYG8"
STOCK_KERNEL_RELEASE = "5.10.226-android12-9-30958166-abS906NKSS7FYG8"
EXPECTED_CLANG_LINES = (
    "Android (7284624, based on r416183b) clang version 12.0.5",
    "c935d99d7cf2016289302412d708641d52d2f7ee",
)
DEFAULT_WORK_TREE = Path("workspace/private/work/s22plus_fyg8_kernel_rebuild_r0")
DEFAULT_CLANG_REPO = Path("workspace/private/inputs/toolchains/aosp-clang-android12-release")
DEFAULT_RESULT_DIR = Path(
    "workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/build-preflight"
)
MIN_PHYSICAL_MEMORY_BYTES = 30 * 1024**3
MIN_SWAP_BYTES = 8 * 1024**3
MIN_FREE_DISK_BYTES = 30 * 1024**3
REQUIRED_HOST_TOOLS = ("git", "/usr/bin/time")
PINNED_REPOS = {
    "clang": (
        DEFAULT_CLANG_REPO,
        "6e3223f76384455acde43affde3df0ea9df66c0d",
    ),
    "build_tools": (
        Path("kernel_platform/prebuilts/build-tools"),
        "cfedc16ec3deb680fca6fe2aff44a1837a97b50d",
    ),
    "glibc_sysroot": (
        Path("kernel_platform/prebuilts/gcc/linux-x86/host/x86_64-linux-glibc2.17-4.8"),
        "4e6f66acf138d40d9a80be24b275abb9c6eed729",
    ),
    "kernel_build_tools": (
        Path("kernel_platform/prebuilts/kernel-build-tools"),
        "ca5b087f88c0302ff66f59a6f26be663e92baf15",
    ),
}
EXT_MODULES = (
    "../vendor/qcom/opensource/datarmnet-ext/wlan",
    "../vendor/qcom/opensource/datarmnet/core",
    "../vendor/qcom/opensource/mmrm-driver",
    "../vendor/qcom/opensource/audio-kernel",
    "../vendor/qcom/opensource/camera-kernel",
    "../vendor/qcom/opensource/display-drivers/msm",
)
DIST_OUTPUTS = ("Image", "Image.lz4", "vmlinux", "System.map", "vmlinux.symvers")


class BuildError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise BuildError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(command, 127, "", str(exc))


def meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    for raw in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        key, value = raw.split(":", 1)
        fields = value.split()
        if fields:
            values[key] = int(fields[0]) * 1024
    return values


def host_resources(path: Path) -> dict[str, Any]:
    memory = meminfo()
    disk = shutil.disk_usage(path)
    physical = memory.get("MemTotal", 0)
    swap = memory.get("SwapTotal", 0)
    return {
        "physical_memory_bytes": physical,
        "swap_bytes": swap,
        "free_disk_bytes": disk.free,
        "full_lto_memory_ok": physical >= MIN_PHYSICAL_MEMORY_BYTES,
        "swap_recommended_ok": swap >= MIN_SWAP_BYTES,
        "disk_ok": disk.free >= MIN_FREE_DISK_BYTES,
        "requirements": {
            "min_physical_memory_bytes": MIN_PHYSICAL_MEMORY_BYTES,
            "min_swap_bytes": MIN_SWAP_BYTES,
            "min_free_disk_bytes": MIN_FREE_DISK_BYTES,
        },
    }


def git_identity(path: Path, expected: str) -> dict[str, Any]:
    head = run(["git", "-C", str(path), "rev-parse", "HEAD"])
    status = run(["git", "-C", str(path), "status", "--porcelain"])
    actual = head.stdout.strip() if head.returncode == 0 else ""
    clean = status.returncode == 0 and not status.stdout.strip()
    return {
        "path": str(path),
        "expected_commit": expected,
        "actual_commit": actual,
        "commit_match": actual == expected,
        "clean": clean,
        "verified": actual == expected and clean,
    }


def build_environment(work_tree: Path, *, lto: str, jobs: int) -> dict[str, str]:
    out_dir = work_tree / "out/msm-waipio-waipio-gki"
    environment = os.environ.copy()
    environment.update(
        {
            "BUILD_TARGET": "g0q_kor_singlex",
            "MODEL": "g0q",
            "PROJECT_NAME": "g0q",
            "REGION": "kor",
            "CARRIER": "singlex",
            "TARGET_BUILD_VARIANT": "user",
            "ANDROID_BUILD_TOP": str(work_tree),
            "TARGET_PRODUCT": "gki",
            "TARGET_BOARD_PLATFORM": "gki",
            "ANDROID_PRODUCT_OUT": str(work_tree / "out/target/product/g0q"),
            "OUT_DIR": str(out_dir),
            "KBUILD_EXTRA_SYMBOLS": str(
                work_tree / "out/vendor/qcom/opensource/mmrm-driver/Module.symvers"
            ),
            "MODNAME": "audio_dlkm",
            "KBUILD_EXT_MODULES": " ".join(EXT_MODULES),
            "RECOMPILE_KERNEL": "1",
            "LTO": lto,
            "LOCALVERSION": STOCK_LOCALVERSION,
            "SOURCE_DATE_EPOCH": str(SOURCE_DATE_EPOCH),
            "KBUILD_BUILD_TIMESTAMP": STOCK_TIMESTAMP,
            "KBUILD_BUILD_USER": "build-user",
            "KBUILD_BUILD_HOST": "build-host",
            "KBUILD_BUILD_VERSION": "1",
            "BUILD_NUMBER": "30958166",
            "BUILD_ID": "S906NKSS7FYG8",
            "GIT_CEILING_DIRECTORIES": str(work_tree.parent),
            "MAKEFLAGS": f"-j{jobs}",
            "LC_ALL": "C",
            "TZ": "UTC",
        }
    )
    return environment


def preflight(root: Path, work_tree: Path, clang_repo: Path, *, lto: str, jobs: int) -> dict[str, Any]:
    required_paths = (
        work_tree / "kernel_platform/build/android/prepare_vendor.sh",
        work_tree / "kernel_platform/common/Makefile",
        work_tree / "kernel_platform/msm-kernel/Makefile",
        work_tree / "vendor/qcom/opensource",
    )
    missing = [display_path(root, path) for path in required_paths if not path.exists()]
    repositories: dict[str, dict[str, Any]] = {}
    for name, (configured, commit) in PINNED_REPOS.items():
        repo_path = resolve(root, configured) if name == "clang" else work_tree / configured
        if name == "clang":
            repo_path = clang_repo
        repositories[name] = git_identity(repo_path, commit)

    clang = clang_repo / "clang-r416183b/bin/clang"
    clang_result = run([str(clang), "--version"]) if clang.is_file() else None
    clang_text = clang_result.stdout if clang_result is not None else ""
    clang_verified = bool(
        clang_result is not None
        and clang_result.returncode == 0
        and all(value in clang_text for value in EXPECTED_CLANG_LINES)
    )
    environment = build_environment(work_tree, lto=lto, jobs=jobs)
    parent_git = run(
        ["git", "-C", str(work_tree), "rev-parse", "--show-toplevel"],
        env=environment,
    )
    parent_git_isolated = parent_git.returncode != 0
    resources = host_resources(work_tree)
    missing_host_tools = [
        tool
        for tool in REQUIRED_HOST_TOOLS
        if not (Path(tool).is_file() if tool.startswith("/") else shutil.which(tool))
    ]
    build_allowed = (
        not missing
        and not missing_host_tools
        and all(repo["verified"] for repo in repositories.values())
        and clang_verified
        and parent_git_isolated
        and resources["disk_ok"]
        and (lto != "full" or resources["full_lto_memory_ok"])
    )
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "generated_epoch": SOURCE_DATE_EPOCH,
        "host_only": True,
        "mode": "preflight",
        "lto_mode": lto,
        "work_tree": display_path(root, work_tree),
        "missing_paths": missing,
        "missing_host_tools": missing_host_tools,
        "toolchain": {
            "clang_path": display_path(root, clang),
            "clang_identity": clang_text.strip(),
            "clang_verified": clang_verified,
            "repositories": repositories,
        },
        "provenance": {
            "source_date_epoch": SOURCE_DATE_EPOCH,
            "kbuild_build_timestamp": STOCK_TIMESTAMP,
            "kbuild_build_user": "build-user",
            "kbuild_build_host": "build-host",
            "localversion": STOCK_LOCALVERSION,
            "expected_kernel_release": STOCK_KERNEL_RELEASE,
            "git_ceiling_directories": environment["GIT_CEILING_DIRECTORIES"],
            "parent_git_isolated": parent_git_isolated,
        },
        "environment": {
            key: environment[key]
            for key in (
                "BUILD_TARGET",
                "MODEL",
                "PROJECT_NAME",
                "REGION",
                "CARRIER",
                "TARGET_BUILD_VARIANT",
                "TARGET_PRODUCT",
                "TARGET_BOARD_PLATFORM",
                "LTO",
                "LOCALVERSION",
                "MAKEFLAGS",
            )
        },
        "resources": resources,
        "build_command": ["./kernel_platform/build/android/prepare_vendor.sh", "sec", "gki"],
        "build_allowed": build_allowed,
        "stock_equivalent_claim": False,
        "safety": {
            "device_contact": False,
            "boot_image_packaging": False,
            "flash": False,
            "partition_write": False,
        },
    }


def collect_outputs(work_tree: Path) -> list[dict[str, Any]]:
    dist = work_tree / "out/msm-waipio-waipio-gki/gki_kernel/dist"
    outputs: list[dict[str, Any]] = []
    for name in DIST_OUTPUTS:
        path = dist / name
        if path.is_file():
            outputs.append({"name": name, "path": str(path), "size": path.stat().st_size, "sha256": sha256_file(path)})
    config = work_tree / "out/msm-waipio-waipio-gki/gki_kernel/common/.config"
    if config.is_file():
        outputs.append({"name": ".config", "path": str(config), "size": config.stat().st_size, "sha256": sha256_file(config)})
    return outputs


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="ascii")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "build"), default="preflight")
    parser.add_argument("--lto", choices=("full", "thin", "none"), default="full")
    parser.add_argument("--jobs", type=int, default=min(os.cpu_count() or 1, 8))
    parser.add_argument("--work-tree", type=Path, default=DEFAULT_WORK_TREE)
    parser.add_argument("--clang-repo", type=Path, default=DEFAULT_CLANG_REPO)
    parser.add_argument("--result-dir", type=Path, default=DEFAULT_RESULT_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.jobs < 1 or args.jobs > 64:
        raise BuildError("--jobs must be between 1 and 64")
    root = repo_root()
    work_tree = resolve(root, args.work_tree)
    clang_repo = resolve(root, args.clang_repo)
    result_dir = resolve(root, args.result_dir)
    result = preflight(root, work_tree, clang_repo, lto=args.lto, jobs=args.jobs)
    write_json(result_dir / "preflight.json", result)
    if args.mode == "preflight":
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["build_allowed"] else 2
    if not result["build_allowed"]:
        raise BuildError("build refused: preflight did not pass")

    environment = build_environment(work_tree, lto=args.lto, jobs=args.jobs)
    command = ["./kernel_platform/build/android/prepare_vendor.sh", "sec", "gki"]
    time_file = result_dir / "time.txt"
    with (result_dir / "stdout.log").open("w", encoding="utf-8") as stdout_log, (
        result_dir / "stderr.log"
    ).open("w", encoding="utf-8") as stderr_log:
        completed = subprocess.run(
            ["/usr/bin/time", "-v", "-o", str(time_file), *command],
            cwd=work_tree,
            env=environment,
            text=True,
            stdout=stdout_log,
            stderr=stderr_log,
            check=False,
        )
    result.update(
        {
            "mode": "build",
            "returncode": completed.returncode,
            "outputs": collect_outputs(work_tree),
            "stock_equivalent_claim": False,
            "interpretation": "build output only; R2 static equivalence and R3 live proof remain required",
        }
    )
    write_json(result_dir / "result.json", result)
    print(json.dumps({"result": "pass" if completed.returncode == 0 else "fail", "returncode": completed.returncode, "result_dir": display_path(root, result_dir), "output_count": len(result["outputs"])}, indent=2, sort_keys=True))
    return completed.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BuildError, OSError) as exc:
        raise SystemExit(str(exc)) from exc
