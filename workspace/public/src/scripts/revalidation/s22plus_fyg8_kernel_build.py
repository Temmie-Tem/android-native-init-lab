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
import stat
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from s22plus_fyg8_kernel_banner import extract_linux_banner, extract_linux_release


SCHEMA = "s22plus_fyg8_kernel_build_v3"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
SOURCE_DATE_EPOCH = 1754027756
STOCK_TIMESTAMP = "Fri Aug 1 05:55:56 UTC 2025"
# Samsung's setlocalversion prepends -android12-9 and each target config may
# add CONFIG_LOCALVERSION (for example, -gki for vendor modules).  Pass only
# the common release suffix here.  BUILD_NUMBER must remain unset because this
# tree appends it separately as -ab${BUILD_NUMBER} to UTS_RELEASE.
STOCK_LOCALVERSION = "-30958166-abS906NKSS7FYG8"
STOCK_KERNEL_RELEASE = "5.10.226-android12-9-30958166-abS906NKSS7FYG8"
STOCK_BANNER_MARKERS = (
    f"Linux version {STOCK_KERNEL_RELEASE}",
    "(build-user@build-host)",
    "Android (7284624, based on r416183b) clang version 12.0.5",
    "#1 SMP PREEMPT " + STOCK_TIMESTAMP,
)
EXPECTED_CLANG_LINES = (
    "Android (7284624, based on r416183b) clang version 12.0.5",
    "c935d99d7cf2016289302412d708641d52d2f7ee",
)
DEFAULT_WORK_TREE = Path("workspace/private/work/s22plus_fyg8_kernel_rebuild_r0")
DEFAULT_CLANG_REPO = Path("workspace/private/inputs/toolchains/aosp-clang-android12-release")
DEFAULT_RESULT_DIR = Path(
    "workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/build-preflight"
)
DEFAULT_STOCK_BASELINE = Path(
    "workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/stock-baseline/"
    "stock-kernel-baseline.json"
)
DEFAULT_BASE_ARCHIVE = Path(
    "workspace/private/inputs/s22plus_kernel_source/SM-S906N_15_base_osrc/Kernel.tar.gz"
)
DEFAULT_DELTA_ARCHIVE = Path(
    "workspace/private/inputs/s22plus_kernel_source/S906NKSS7FYG8_osrc/"
    "S906NKSS7FYG8_kernel.tar.gz"
)
DEFAULT_OVERLAY_AUDIT = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_overlay_audit.py"
)
EXPECTED_BASE_SHA256 = "86e2f73412c65fadff0b15bbf0eac9140610f70250514ac0bddbf3b53fb5f7bf"
EXPECTED_DELTA_SHA256 = "23ef2b27de8843e271d41405b3c0b1a71bfa668615c8f0f12a1e5c4395ec851a"
EXPECTED_FINAL_MEMBERS_SHA256 = "946789ba7bae742893e2b9e94db76614775ce770e04aaeb4254c960c907f0b58"
EXPECTED_SOURCE_MEMBER_COUNT = 166037
MIN_PHYSICAL_MEMORY_BYTES = 30 * 1024**3
MIN_SWAP_BYTES = 8 * 1024**3
MIN_FREE_DISK_BYTES = 30 * 1024**3
GNU_TAR_PATH = Path("/usr/bin/tar")
EXPECTED_GNU_TAR_PREFIX = "tar (GNU tar)"
GNU_XARGS_PATH = Path("/usr/bin/xargs")
EXPECTED_GNU_XARGS_PREFIX = "xargs (GNU findutils)"
REQUIRED_HOST_TOOLS = (
    "git",
    "/usr/bin/time",
    str(GNU_TAR_PATH),
    str(GNU_XARGS_PATH),
)
INCREMENTAL_READONLY_DIST_TARGETS = ("merge_dtbs.py", "ufdt_apply_overlay")
SETUP_ENV_PATH = Path("kernel_platform/build/_setup_env.sh")
SETUP_ENV_TIMESTAMP_ORIGINAL = (
    "export SOURCE_DATE_EPOCH=$(git -C ${ROOT_DIR}/${KERNEL_DIR} log -1 --pretty=%ct)\n"
    'export KBUILD_BUILD_TIMESTAMP="$(date -d @${SOURCE_DATE_EPOCH})"\n'
)
SETUP_ENV_TIMESTAMP_PINNED = (
    f'export SOURCE_DATE_EPOCH="${{SOURCE_DATE_EPOCH:-{SOURCE_DATE_EPOCH}}}"\n'
    f'export KBUILD_BUILD_TIMESTAMP="${{KBUILD_BUILD_TIMESTAMP:-{STOCK_TIMESTAMP}}}"\n'
)
HOST_ENV_ALLOWLIST = ("HOME", "USER", "LOGNAME", "TMPDIR", "TERM")
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
DIST_OUTPUTS = (
    "Image",
    "Image.lz4",
    "vmlinux",
    "System.map",
    "vmlinux.symvers",
    "modules.builtin",
    "modules.builtin.modinfo",
)
PROVIDER_EXPECTED_OUTPUTS = {
    "dataipa": (
        "out/vendor/qcom/opensource/dataipa/Module.symvers",
        "out/vendor/qcom/opensource/dataipa/drivers/platform/msm/gsi/gsim.ko",
        "out/vendor/qcom/opensource/dataipa/drivers/platform/msm/ipa/ipam.ko",
        "out/vendor/qcom/opensource/dataipa/drivers/platform/msm/ipa/ipanetm.ko",
        "out/vendor/qcom/opensource/dataipa/drivers/platform/msm/ipa/ipa_clients/ipa_clientsm.ko",
        "out/vendor/qcom/opensource/dataipa/drivers/platform/msm/ipa/ipa_clients/rndisipam.ko",
    ),
    "datarmnet_shs": (
        "out/vendor/qcom/opensource/datarmnet-ext/shs/Module.symvers",
        "out/vendor/qcom/opensource/datarmnet-ext/shs/rmnet_shs.ko",
    ),
}


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


def inspect_stock_baseline(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "verified": False,
    }
    if not path.is_file():
        result["reason"] = "stock-baseline-missing"
        return result
    try:
        raw = path.read_bytes()
        baseline = json.loads(raw.decode("ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        result["reason"] = f"stock-baseline-invalid: {exc}"
        return result
    banner = baseline.get("linux_banner") if isinstance(baseline, dict) else None
    release = extract_linux_release(banner) if isinstance(banner, str) else None
    missing_markers = (
        [marker for marker in STOCK_BANNER_MARKERS if marker not in banner]
        if isinstance(banner, str)
        else list(STOCK_BANNER_MARKERS)
    )
    verified = (
        isinstance(baseline, dict)
        and baseline.get("target") == TARGET
        and baseline.get("kernel_release") == STOCK_KERNEL_RELEASE
        and isinstance(banner, str)
        and bool(banner)
        and "\n" not in banner
        and "\x00" not in banner
        and release == STOCK_KERNEL_RELEASE
        and not missing_markers
    )
    result.update(
        {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "target": baseline.get("target") if isinstance(baseline, dict) else None,
            "kernel_release": baseline.get("kernel_release") if isinstance(baseline, dict) else None,
            "expected_banner": banner if isinstance(banner, str) else "",
            "missing_markers": missing_markers,
            "verified": verified,
        }
    )
    if not verified:
        result["reason"] = "stock-baseline-identity-mismatch"
    return result


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


def hermetic_path(work_tree: Path, clang_repo: Path) -> str:
    candidates = (
        clang_repo / "clang-r416183b/bin",
        work_tree.parent / "host-tool-overrides",
        work_tree / "kernel_platform/prebuilts/build-tools/path/linux-x86",
        work_tree / "kernel_platform/prebuilts/kernel-build-tools/linux-x86/bin",
        Path("/usr/bin"),
        Path("/bin"),
    )
    return os.pathsep.join(str(path) for path in candidates)


def prepare_host_tool_overrides(work_tree: Path) -> dict[str, Any]:
    """Expose required GNU tools without replacing other Android host tools."""
    override_dir = work_tree.parent / "host-tool-overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    expected = {
        "tar": (GNU_TAR_PATH, EXPECTED_GNU_TAR_PREFIX),
        "xargs": (GNU_XARGS_PATH, EXPECTED_GNU_XARGS_PREFIX),
    }
    unexpected = sorted(
        path.name for path in override_dir.iterdir() if path.name not in expected
    )
    if unexpected:
        raise BuildError(f"unexpected host-tool overrides: {unexpected}")

    tools: dict[str, dict[str, Any]] = {}
    for name, (target, version_prefix) in expected.items():
        link = override_dir / name
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(target)
        version = run([str(link), "--version"])
        first_line = version.stdout.splitlines()[0] if version.stdout else ""
        tools[name] = {
            "path": str(link),
            "target": str(target),
            "version": first_line,
            "verified": (
                target.is_file()
                and link.resolve() == target.resolve()
                and version.returncode == 0
                and first_line.startswith(version_prefix)
            ),
        }
    return {
        "directory": str(override_dir),
        "tools": tools,
        "verified": all(tool["verified"] for tool in tools.values()),
    }


def prepare_incremental_dist_refresh(work_tree: Path) -> dict[str, Any]:
    """Remove only generated read-only host copies before an incremental run."""
    host_bin = work_tree / "out/msm-waipio-waipio-gki/host/bin"
    removed: list[str] = []
    for name in INCREMENTAL_READONLY_DIST_TARGETS:
        path = host_bin / name
        if path.exists() or path.is_symlink():
            if not path.is_file():
                raise BuildError(f"incremental dist target is not a file: {path}")
            path.unlink()
            removed.append(str(path))
    return {
        "host_bin": str(host_bin),
        "allowed_targets": list(INCREMENTAL_READONLY_DIST_TARGETS),
        "removed": removed,
        "verified": True,
    }


def inspect_timestamp_control(work_tree: Path) -> dict[str, Any]:
    """Verify the exact Samsung timestamp override before any temporary edit."""
    path = work_tree / SETUP_ENV_PATH
    if not path.is_file() or path.is_symlink():
        return {
            "path": str(path),
            "verified": False,
            "reason": "setup-env-missing-or-not-regular",
        }
    original_bytes = path.read_bytes()
    try:
        original = original_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return {
            "path": str(path),
            "verified": False,
            "reason": "setup-env-not-utf8",
        }
    count = original.count(SETUP_ENV_TIMESTAMP_ORIGINAL)
    patched = original.replace(
        SETUP_ENV_TIMESTAMP_ORIGINAL,
        SETUP_ENV_TIMESTAMP_PINNED,
        1,
    )
    patched_bytes = patched.encode("utf-8")
    metadata = path.stat()
    parent_writable = os.access(path.parent, os.W_OK)
    return {
        "path": str(path),
        "original_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "patched_sha256": hashlib.sha256(patched_bytes).hexdigest(),
        "original_mode": stat.S_IMODE(metadata.st_mode),
        "original_atime_ns": metadata.st_atime_ns,
        "original_mtime_ns": metadata.st_mtime_ns,
        "parent_writable": parent_writable,
        "match_count": count,
        "source_date_epoch": SOURCE_DATE_EPOCH,
        "kbuild_build_timestamp": STOCK_TIMESTAMP,
        "verified": count == 1 and patched != original and parent_writable,
    }


def atomic_replace_bytes(path: Path, data: bytes, *, mode: int) -> None:
    """Replace one regular file atomically while preserving its permission mode."""
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            os.fchmod(handle.fileno(), mode)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def apply_timestamp_control(
    work_tree: Path, control: dict[str, Any]
) -> Iterator[dict[str, Any]]:
    """Temporarily stop Samsung _setup_env.sh from replacing pinned metadata."""
    if not control.get("verified"):
        raise BuildError("timestamp control is not verified")
    path = work_tree / SETUP_ENV_PATH
    original_bytes = path.read_bytes()
    if hashlib.sha256(original_bytes).hexdigest() != control["original_sha256"]:
        raise BuildError("timestamp control source changed after preflight")
    if stat.S_IMODE(path.stat().st_mode) != control["original_mode"]:
        raise BuildError("timestamp control source mode changed after preflight")
    original = original_bytes.decode("utf-8")
    patched = original.replace(
        SETUP_ENV_TIMESTAMP_ORIGINAL,
        SETUP_ENV_TIMESTAMP_PINNED,
        1,
    )
    if patched.count(SETUP_ENV_TIMESTAMP_PINNED) != 1:
        raise BuildError("timestamp control replacement is not unique")
    atomic_replace_bytes(path, patched.encode("utf-8"), mode=control["original_mode"])
    runtime = dict(control)
    runtime.update({"applied": True, "restored": False})
    try:
        yield runtime
    finally:
        current_sha = sha256_file(path) if path.is_file() else None
        atomic_replace_bytes(path, original_bytes, mode=control["original_mode"])
        os.utime(
            path,
            ns=(control["original_atime_ns"], control["original_mtime_ns"]),
            follow_symlinks=False,
        )
        runtime["restored_sha256"] = sha256_file(path)
        runtime["restored_mode"] = stat.S_IMODE(path.stat().st_mode)
        runtime["restored"] = (
            runtime["restored_sha256"] == control["original_sha256"]
            and runtime["restored_mode"] == control["original_mode"]
        )
        runtime["patched_content_unchanged"] = (
            current_sha == control["patched_sha256"]
        )
        if not runtime["restored"]:
            raise BuildError("timestamp-controlled setup script was not restored")
        if not runtime["patched_content_unchanged"]:
            raise BuildError("timestamp-controlled setup script changed during build")


def kernel_banner_gate(work_tree: Path, *, expected_banner: str) -> dict[str, Any]:
    image = work_tree / "out/msm-waipio-waipio-gki/gki_kernel/dist/Image"
    if not image.is_file():
        return {
            "path": str(image),
            "verified": False,
            "missing_markers": list(STOCK_BANNER_MARKERS),
            "expected_banner": expected_banner,
        }
    data = image.read_bytes()
    banner = extract_linux_banner(data) or ""
    missing = [
        marker
        for marker in STOCK_BANNER_MARKERS
        if marker not in banner
    ]
    exact_banner_match = banner == expected_banner
    return {
        "path": str(image),
        "banner": banner,
        "expected_banner": expected_banner,
        "release": extract_linux_release(banner) or "",
        "required_markers": list(STOCK_BANNER_MARKERS),
        "missing_markers": missing,
        "exact_banner_match": exact_banner_match,
        "verified": exact_banner_match and not missing,
    }


def run_provider_module_closure(
    work_tree: Path,
    environment: dict[str, str],
    result_dir: Path,
    *,
    jobs: int,
) -> dict[str, Any]:
    """Build provider modules omitted by Samsung's KBUILD_EXT_MODULES list."""
    kernel_platform = work_tree / "kernel_platform"
    msm_out = work_tree / "out/msm-waipio-waipio-gki/msm-kernel"
    mixed_tree = work_tree / "out/msm-waipio-waipio-gki/gki_kernel/dist"
    common = [
        "make",
        "-C",
        "msm-kernel",
        f"O={msm_out}",
        "ARCH=arm64",
        "SUBARCH=arm64",
        "CROSS_COMPILE=aarch64-linux-gnu-",
        "LLVM=1",
        "LLVM_IAS=1",
        "DEPMOD=depmod",
        "DTC=dtc",
        f"KBUILD_MIXED_TREE={mixed_tree}",
        f"-j{jobs}",
        "modules",
    ]
    specs = (
        (
            "dataipa",
            "../../vendor/qcom/opensource/dataipa",
            [],
        ),
        (
            "datarmnet_shs",
            "../../vendor/qcom/opensource/datarmnet-ext/shs",
            [
                "RMNET_CORE_INC_DIR="
                + str(work_tree / "vendor/qcom/opensource/datarmnet/core"),
                "KBUILD_EXTRA_SYMBOLS="
                + str(
                    work_tree
                    / "out/vendor/qcom/opensource/datarmnet/core/Module.symvers"
                ),
            ],
        ),
    )
    results: list[dict[str, Any]] = []
    for name, module_path, extra in specs:
        command = [*common[:3], f"M={module_path}", *common[3:-1], *extra, "modules"]
        stdout_path = result_dir / f"provider-{name}.stdout.log"
        stderr_path = result_dir / f"provider-{name}.stderr.log"
        with stdout_path.open("w", encoding="utf-8") as stdout_log, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr_log:
            completed = subprocess.run(
                command,
                cwd=kernel_platform,
                env=environment,
                text=True,
                stdout=stdout_log,
                stderr=stderr_log,
                check=False,
            )
        artifacts = []
        missing = []
        for relative in PROVIDER_EXPECTED_OUTPUTS[name]:
            path = work_tree / relative
            if path.is_file():
                artifacts.append(
                    {
                        "path": str(path),
                        "size": path.stat().st_size,
                        "sha256": sha256_file(path),
                    }
                )
            else:
                missing.append(str(path))
        results.append(
            {
                "name": name,
                "command": command,
                "returncode": completed.returncode,
                "stdout_log": str(stdout_path),
                "stderr_log": str(stderr_path),
                "artifacts": artifacts,
                "missing": missing,
                "verified": completed.returncode == 0 and not missing,
            }
        )
    return {
        "providers": results,
        "verified": all(result["verified"] for result in results),
    }


def build_environment(
    work_tree: Path,
    *,
    lto: str,
    jobs: int,
    clang_repo: Path | None = None,
) -> dict[str, str]:
    out_dir = work_tree / "out/msm-waipio-waipio-gki"
    if clang_repo is None:
        clang_repo = DEFAULT_CLANG_REPO
    environment = {
        key: os.environ[key]
        for key in HOST_ENV_ALLOWLIST
        if key in os.environ
    }
    environment.update(
        {
            "PATH": hermetic_path(work_tree, clang_repo),
            "BUILD_TARGET": "g0q_kor_singlex",
            "MODEL": "g0q",
            "PROJECT_NAME": "g0q",
            "REGION": "kor",
            "CARRIER": "singlex",
            "TARGET_BUILD_VARIANT": "user",
            "ANDROID_BUILD_TOP": str(work_tree),
            "TARGET_PRODUCT": "gki",
            "TARGET_BOARD_PLATFORM": "gki",
            "ANDROID_KERNEL_OUT": str(work_tree / "out/android-kernel-out"),
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
            "BUILD_ID": "S906NKSS7FYG8",
            "GIT_CEILING_DIRECTORIES": str(work_tree.parent),
            "MAKEFLAGS": f"-j{jobs}",
            "LC_ALL": "C",
            "TZ": "UTC",
        }
    )
    return environment


def run_overlay_audit(
    root: Path,
    work_tree: Path,
    result_dir: Path,
    base_archive: Path,
    delta_archive: Path,
    audit_script: Path,
) -> dict[str, Any]:
    audit_out = result_dir / "source-overlay-audit"
    completed = run(
        [
            sys.executable,
            str(audit_script),
            "--base",
            str(base_archive),
            "--delta",
            str(delta_archive),
            "--resident-tree",
            str(work_tree),
            "--out",
            str(audit_out),
        ],
        cwd=root,
    )
    manifest_path = audit_out / "manifest.json"
    if completed.returncode != 0 or not manifest_path.is_file():
        return {
            "verified": False,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
            "manifest_path": display_path(root, manifest_path),
        }
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    input_hashes = {item.get("sha256") for item in manifest.get("inputs", [])}
    final_artifact = manifest.get("artifacts", {}).get(
        "reconstructed-final-members.jsonl", {}
    )
    resident = manifest.get("resident_tree", {})
    summary = manifest.get("summary", {})
    verified = (
        manifest.get("schema") == "s22plus_fyg8_kernel_overlay_audit_v1"
        and manifest.get("target") == TARGET
        and input_hashes == {EXPECTED_BASE_SHA256, EXPECTED_DELTA_SHA256}
        and final_artifact.get("sha256") == EXPECTED_FINAL_MEMBERS_SHA256
        and summary.get("final_members") == EXPECTED_SOURCE_MEMBER_COUNT
        and resident.get("checked") is True
        and resident.get("match") is True
        and resident.get("missing_count") == 0
        and resident.get("mismatch_count") == 0
    )
    return {
        "verified": verified,
        "returncode": completed.returncode,
        "manifest_path": display_path(root, manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "base_sha256": EXPECTED_BASE_SHA256,
        "delta_sha256": EXPECTED_DELTA_SHA256,
        "final_members_sha256": final_artifact.get("sha256", ""),
        "final_member_count": summary.get("final_members", 0),
        "resident_match": resident.get("match", False),
    }


def preflight(
    root: Path,
    work_tree: Path,
    clang_repo: Path,
    *,
    lto: str,
    jobs: int,
    source_overlay: dict[str, Any] | None = None,
    host_tool_overrides: dict[str, Any] | None = None,
    timestamp_control: dict[str, Any] | None = None,
    stock_baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
    environment = build_environment(
        work_tree, lto=lto, jobs=jobs, clang_repo=clang_repo
    )
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
        and bool(source_overlay and source_overlay.get("verified"))
        and bool(host_tool_overrides and host_tool_overrides.get("verified"))
        and bool(timestamp_control and timestamp_control.get("verified"))
        and bool(stock_baseline and stock_baseline.get("verified"))
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
            "source_overlay": source_overlay or {"verified": False},
            "host_tool_overrides": host_tool_overrides or {"verified": False},
            "timestamp_control": timestamp_control or {"verified": False},
            "stock_baseline": stock_baseline or {"verified": False},
            "ambient_environment_allowlist": list(HOST_ENV_ALLOWLIST),
            "effective_path": environment["PATH"],
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


def collect_generated_modules(work_tree: Path) -> list[dict[str, Any]]:
    out_root = work_tree / "out"
    if not out_root.is_dir():
        return []
    return [
        {
            "path": str(path),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(out_root.rglob("*.ko"))
        if path.is_file()
    ]


def collect_symvers(work_tree: Path) -> list[dict[str, Any]]:
    out_root = work_tree / "out"
    if not out_root.is_dir():
        return []
    paths = {
        path.resolve()
        for pattern in ("Module.symvers", "vmlinux.symvers")
        for path in out_root.rglob(pattern)
        if path.is_file()
    }
    return [
        {
            "path": str(path),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(paths)
    ]


def output_gate(outputs: list[dict[str, Any]]) -> dict[str, Any]:
    present = {item["name"] for item in outputs}
    required = set(DIST_OUTPUTS) | {".config"}
    missing = sorted(required - present)
    return {
        "required": sorted(required),
        "present": sorted(present),
        "missing": missing,
        "verified": not missing,
    }


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
    parser.add_argument("--base-archive", type=Path, default=DEFAULT_BASE_ARCHIVE)
    parser.add_argument("--delta-archive", type=Path, default=DEFAULT_DELTA_ARCHIVE)
    parser.add_argument("--overlay-audit", type=Path, default=DEFAULT_OVERLAY_AUDIT)
    parser.add_argument("--stock-baseline", type=Path, default=DEFAULT_STOCK_BASELINE)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.jobs < 1 or args.jobs > 64:
        raise BuildError("--jobs must be between 1 and 64")
    root = repo_root()
    work_tree = resolve(root, args.work_tree)
    clang_repo = resolve(root, args.clang_repo)
    result_dir = resolve(root, args.result_dir)
    host_tool_overrides = prepare_host_tool_overrides(work_tree)
    source_overlay = run_overlay_audit(
        root,
        work_tree,
        result_dir,
        resolve(root, args.base_archive),
        resolve(root, args.delta_archive),
        resolve(root, args.overlay_audit),
    )
    timestamp_control = inspect_timestamp_control(work_tree)
    stock_baseline = inspect_stock_baseline(resolve(root, args.stock_baseline))
    result = preflight(
        root,
        work_tree,
        clang_repo,
        lto=args.lto,
        jobs=args.jobs,
        source_overlay=source_overlay,
        host_tool_overrides=host_tool_overrides,
        timestamp_control=timestamp_control,
        stock_baseline=stock_baseline,
    )
    write_json(result_dir / "preflight.json", result)
    if args.mode == "preflight":
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["build_allowed"] else 2
    if not result["build_allowed"]:
        raise BuildError("build refused: preflight did not pass")

    incremental_dist_refresh = prepare_incremental_dist_refresh(work_tree)
    environment = build_environment(
        work_tree, lto=args.lto, jobs=args.jobs, clang_repo=clang_repo
    )
    command = ["./kernel_platform/build/android/prepare_vendor.sh", "sec", "gki"]
    time_file = result_dir / "time.txt"
    with apply_timestamp_control(work_tree, timestamp_control) as timestamp_runtime:
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
    provider_module_closure = (
        run_provider_module_closure(
            work_tree, environment, result_dir, jobs=args.jobs
        )
        if completed.returncode == 0
        else {"providers": [], "verified": False, "skipped": True}
    )
    outputs = collect_outputs(work_tree)
    outputs_gate = output_gate(outputs)
    generated_modules = collect_generated_modules(work_tree)
    module_gate = {
        "generated_module_count": len(generated_modules),
        "verified": bool(generated_modules),
    }
    banner_gate = kernel_banner_gate(
        work_tree, expected_banner=stock_baseline["expected_banner"]
    )
    effective_returncode = completed.returncode
    if effective_returncode == 0 and not provider_module_closure["verified"]:
        effective_returncode = 5
    if effective_returncode == 0 and not outputs_gate["verified"]:
        effective_returncode = 3
    if effective_returncode == 0 and not module_gate["verified"]:
        effective_returncode = 4
    if effective_returncode == 0 and not banner_gate["verified"]:
        effective_returncode = 6
    result.update(
        {
            "mode": "build",
            "build_command_returncode": completed.returncode,
            "returncode": effective_returncode,
            "outputs": outputs,
            "output_gate": outputs_gate,
            "generated_modules": generated_modules,
            "module_gate": module_gate,
            "kernel_banner_gate": banner_gate,
            "timestamp_control_runtime": timestamp_runtime,
            "provider_module_closure": provider_module_closure,
            "symvers_files": collect_symvers(work_tree),
            "incremental_dist_refresh": incremental_dist_refresh,
            "r1_buildability_pass": effective_returncode == 0,
            "stock_equivalent_claim": False,
            "interpretation": "build output only; R2 static equivalence and R3 live proof remain required",
        }
    )
    write_json(result_dir / "result.json", result)
    print(json.dumps({"result": "pass" if effective_returncode == 0 else "fail", "returncode": effective_returncode, "result_dir": display_path(root, result_dir), "output_count": len(result["outputs"]), "generated_module_count": len(result["generated_modules"]), "symvers_file_count": len(result["symvers_files"])}, indent=2, sort_keys=True))
    return effective_returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BuildError, OSError) as exc:
        raise SystemExit(str(exc)) from exc
