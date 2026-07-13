#!/usr/bin/env python3
"""Build the patched FYG8 R4W1-B direct-PID1-init witness kernel host-only."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import stat
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import s22plus_fyg8_kernel_build as base  # noqa: E402
import s22plus_fyg8_r4w1b_patch_check as patch_check  # noqa: E402


SCHEMA = "s22plus_fyg8_r4w1b_build_v1"
TARGET = base.TARGET
STOCK_IMAGE_SIZE = 41_490_944
FIXED_KERNEL_SLOT_CAPACITY = 41_492_480
ABSOLUTE_RAMDISK_START = 41_496_576
R4W1B_MARKER_FAMILY = b"[[S22R4W1B|"
HISTORICAL_R4W1_MARKER_FAMILY = b"[[S22R4W1|"
BUILD_SH_PATH = Path("kernel_platform/build/build.sh")
BUILD_SH_SHA256 = "4b633f5ff11920307e193019248d69e2243ba20b4b55483a6bd419910a383690"
KMI_PATH_ORIGINAL = (
    "              --set-str UNUSED_KSYMS_WHITELIST "
    "${OUT_DIR}/abi_symbollist.raw\n"
)
KMI_PATH_REPRODUCIBLE = (
    "              --set-str UNUSED_KSYMS_WHITELIST "
    "../../out/msm-waipio-waipio-gki/gki_kernel/common/abi_symbollist.raw\n"
)
KERNEL_MAKEFILE_PATH = Path("kernel_platform/common/Makefile")
KERNEL_MAKEFILE_SHA256 = (
    "9dcb6faf9709e8bc5a0d52c08611e36b14788e04e0488c88178015142e9c0c0f"
)
KERNEL_DEBUG_PATH_ORIGINAL = (
    "# change __FILE__ to the relative path from the srctree\n"
    "KBUILD_CPPFLAGS += $(call cc-option,-fmacro-prefix-map=$(srctree)/=)\n"
)
KERNEL_DEBUG_PATH_REPRODUCIBLE = (
    KERNEL_DEBUG_PATH_ORIGINAL
    + "KBUILD_AFLAGS += -fdebug-prefix-map=$(abs_objtree)=/kernel-out\n"
    + "KBUILD_CFLAGS += -fdebug-prefix-map=$(abs_objtree)=/kernel-out\n"
)
VDSO_DEBUG_CONTROLS = (
    {
        "path": Path("kernel_platform/common/arch/arm64/kernel/vdso/Makefile"),
        "sha256": "ffea25de09036567a55f0618f37c7ec71d05bed2fda57080c7018e5a67957d5a",
        "original": "ccflags-y += -DDISABLE_BRANCH_PROFILING -DBUILD_VDSO\n",
        "reproducible": (
            "ccflags-y += -DDISABLE_BRANCH_PROFILING -DBUILD_VDSO\n"
            "ccflags-y += -fdebug-prefix-map=$(abs_srctree)=/kernel-src\n"
            "ccflags-y += -fdebug-prefix-map=$(abs_objtree)=/kernel-out\n"
            "asflags-y += -fdebug-prefix-map=$(abs_srctree)=/kernel-src\n"
            "asflags-y += -fdebug-prefix-map=$(abs_objtree)=/kernel-out\n"
        ),
    },
    {
        "path": Path("kernel_platform/common/arch/arm64/kernel/vdso32/Makefile"),
        "sha256": "a0f4a9ea0f57b075d5835d0d4755e2d70eaab1c90d49105da557ff1892986393",
        "original": "VDSO_CAFLAGS += -DDISABLE_BRANCH_PROFILING\n",
        "reproducible": (
            "VDSO_CAFLAGS += -DDISABLE_BRANCH_PROFILING\n"
            "VDSO_CAFLAGS += -fdebug-prefix-map=$(abs_srctree)=/kernel-src\n"
            "VDSO_CAFLAGS += -fdebug-prefix-map=$(abs_objtree)=/kernel-out\n"
        ),
    },
)
DEFAULT_RESULT_DIR = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_build/build"
)
HOST_PACKAGING_OUTPUTS = (
    "boot.img",
    "dtbo.img",
    "super.img",
    "vendor_boot.img",
    "vendor_dlkm.img",
)


class BuildError(ValueError):
    pass


def inspect_kmi_path_control(work_tree: Path) -> dict[str, Any]:
    path = work_tree / BUILD_SH_PATH
    if path.is_symlink() or not path.is_file():
        return {"path": str(path), "verified": False, "reason": "missing-or-indirect"}
    original = path.read_bytes()
    try:
        text = original.decode("utf-8")
    except UnicodeDecodeError:
        return {"path": str(path), "verified": False, "reason": "not-utf8"}
    metadata = path.stat()
    replaced = text.replace(KMI_PATH_ORIGINAL, KMI_PATH_REPRODUCIBLE, 1).encode()
    result = {
        "path": str(path),
        "original_sha256": base.sha256_file(path),
        "expected_original_sha256": BUILD_SH_SHA256,
        "patched_sha256": __import__("hashlib").sha256(replaced).hexdigest(),
        "original_mode": stat.S_IMODE(metadata.st_mode),
        "original_atime_ns": metadata.st_atime_ns,
        "original_mtime_ns": metadata.st_mtime_ns,
        "match_count": text.count(KMI_PATH_ORIGINAL),
        "reproducible_path": KMI_PATH_REPRODUCIBLE.strip(),
        "parent_writable": os.access(path.parent, os.W_OK),
    }
    result["verified"] = (
        result["original_sha256"] == BUILD_SH_SHA256
        and result["match_count"] == 1
        and replaced != original
        and result["parent_writable"]
    )
    return result


@contextmanager
def apply_kmi_path_control(
    work_tree: Path, control: dict[str, Any]
) -> Iterator[dict[str, Any]]:
    if not control.get("verified"):
        raise BuildError("KMI path reproducibility control is not verified")
    path = work_tree / BUILD_SH_PATH
    original = path.read_bytes()
    if base.sha256_file(path) != control["original_sha256"]:
        raise BuildError("build.sh changed after KMI path preflight")
    patched = original.decode("utf-8").replace(
        KMI_PATH_ORIGINAL, KMI_PATH_REPRODUCIBLE, 1
    ).encode("utf-8")
    base.atomic_replace_bytes(path, patched, mode=control["original_mode"])
    runtime = dict(control)
    runtime.update({"applied": True, "restored": False})
    try:
        yield runtime
    finally:
        current_sha = base.sha256_file(path) if path.is_file() else None
        base.atomic_replace_bytes(path, original, mode=control["original_mode"])
        os.utime(
            path,
            ns=(control["original_atime_ns"], control["original_mtime_ns"]),
            follow_symlinks=False,
        )
        runtime["patched_content_unchanged"] = current_sha == control["patched_sha256"]
        runtime["restored_sha256"] = base.sha256_file(path)
        runtime["restored_mode"] = stat.S_IMODE(path.stat().st_mode)
        runtime["restored"] = (
            runtime["restored_sha256"] == control["original_sha256"]
            and runtime["restored_mode"] == control["original_mode"]
        )
        if not runtime["patched_content_unchanged"] or not runtime["restored"]:
            raise BuildError("KMI path control was not cleanly restored")


def inspect_vdso_debug_control(work_tree: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for spec in VDSO_DEBUG_CONTROLS:
        path = work_tree / spec["path"]
        if path.is_symlink() or not path.is_file():
            rows.append(
                {"path": str(path), "verified": False, "reason": "missing-or-indirect"}
            )
            continue
        original = path.read_bytes()
        try:
            text = original.decode("utf-8")
        except UnicodeDecodeError:
            rows.append({"path": str(path), "verified": False, "reason": "not-utf8"})
            continue
        metadata = path.stat()
        patched = text.replace(spec["original"], spec["reproducible"], 1).encode(
            "utf-8"
        )
        row = {
            "path": str(path),
            "relative_path": str(spec["path"]),
            "original_sha256": base.sha256_file(path),
            "expected_original_sha256": spec["sha256"],
            "patched_sha256": __import__("hashlib").sha256(patched).hexdigest(),
            "original_mode": stat.S_IMODE(metadata.st_mode),
            "original_atime_ns": metadata.st_atime_ns,
            "original_mtime_ns": metadata.st_mtime_ns,
            "match_count": text.count(spec["original"]),
            "source_map": "/kernel-src",
            "object_map": "/kernel-out",
            "parent_writable": os.access(path.parent, os.W_OK),
        }
        row["verified"] = (
            row["original_sha256"] == spec["sha256"]
            and row["match_count"] == 1
            and patched != original
            and row["parent_writable"]
        )
        rows.append(row)
    return {
        "files": rows,
        "expected_file_count": len(VDSO_DEBUG_CONTROLS),
        "verified": (
            len(rows) == len(VDSO_DEBUG_CONTROLS)
            and all(row.get("verified") for row in rows)
        ),
    }


def inspect_kernel_debug_control(work_tree: Path) -> dict[str, Any]:
    path = work_tree / KERNEL_MAKEFILE_PATH
    if path.is_symlink() or not path.is_file():
        return {"path": str(path), "verified": False, "reason": "missing-or-indirect"}
    original = path.read_bytes()
    try:
        text = original.decode("utf-8")
    except UnicodeDecodeError:
        return {"path": str(path), "verified": False, "reason": "not-utf8"}
    metadata = path.stat()
    patched = text.replace(
        KERNEL_DEBUG_PATH_ORIGINAL, KERNEL_DEBUG_PATH_REPRODUCIBLE, 1
    ).encode("utf-8")
    result = {
        "path": str(path),
        "original_sha256": base.sha256_file(path),
        "expected_original_sha256": KERNEL_MAKEFILE_SHA256,
        "patched_sha256": __import__("hashlib").sha256(patched).hexdigest(),
        "original_mode": stat.S_IMODE(metadata.st_mode),
        "original_atime_ns": metadata.st_atime_ns,
        "original_mtime_ns": metadata.st_mtime_ns,
        "match_count": text.count(KERNEL_DEBUG_PATH_ORIGINAL),
        "object_map": "/kernel-out",
        "parent_writable": os.access(path.parent, os.W_OK),
    }
    result["verified"] = (
        result["original_sha256"] == KERNEL_MAKEFILE_SHA256
        and result["match_count"] == 1
        and patched != original
        and result["parent_writable"]
    )
    return result


@contextmanager
def apply_kernel_debug_control(
    work_tree: Path, control: dict[str, Any]
) -> Iterator[dict[str, Any]]:
    if not control.get("verified"):
        raise BuildError("kernel debug-path reproducibility control is not verified")
    path = work_tree / KERNEL_MAKEFILE_PATH
    original = path.read_bytes()
    if base.sha256_file(path) != control["original_sha256"]:
        raise BuildError("kernel Makefile changed after debug-path preflight")
    patched = original.decode("utf-8").replace(
        KERNEL_DEBUG_PATH_ORIGINAL, KERNEL_DEBUG_PATH_REPRODUCIBLE, 1
    ).encode("utf-8")
    base.atomic_replace_bytes(path, patched, mode=control["original_mode"])
    runtime = dict(control)
    runtime.update({"applied": True, "restored": False})
    try:
        yield runtime
    finally:
        current_sha = base.sha256_file(path) if path.is_file() else None
        base.atomic_replace_bytes(path, original, mode=control["original_mode"])
        os.utime(
            path,
            ns=(control["original_atime_ns"], control["original_mtime_ns"]),
            follow_symlinks=False,
        )
        runtime["patched_content_unchanged"] = current_sha == control["patched_sha256"]
        runtime["restored_sha256"] = base.sha256_file(path)
        runtime["restored_mode"] = stat.S_IMODE(path.stat().st_mode)
        runtime["restored"] = (
            runtime["restored_sha256"] == control["original_sha256"]
            and runtime["restored_mode"] == control["original_mode"]
        )
        if not runtime["patched_content_unchanged"] or not runtime["restored"]:
            raise BuildError("kernel debug-path control was not cleanly restored")


@contextmanager
def apply_vdso_debug_control(
    work_tree: Path, control: dict[str, Any]
) -> Iterator[dict[str, Any]]:
    if not control.get("verified"):
        raise BuildError("VDSO debug-path reproducibility control is not verified")
    originals: dict[Path, bytes] = {}
    patched_hashes: dict[Path, str] = {}
    rows_by_relative = {
        row["relative_path"]: row for row in control.get("files", [])
    }
    runtime = dict(control)
    runtime["files"] = [dict(row) for row in control["files"]]
    runtime.update({"applied": False, "restored": False})
    written: list[Path] = []
    try:
        for spec in VDSO_DEBUG_CONTROLS:
            path = work_tree / spec["path"]
            row = rows_by_relative[str(spec["path"])]
            original = path.read_bytes()
            if base.sha256_file(path) != row["original_sha256"]:
                raise BuildError(f"VDSO Makefile changed after preflight: {path}")
            patched = original.decode("utf-8").replace(
                spec["original"], spec["reproducible"], 1
            ).encode("utf-8")
            originals[path] = original
            patched_hashes[path] = row["patched_sha256"]
            base.atomic_replace_bytes(path, patched, mode=row["original_mode"])
            written.append(path)
        runtime["applied"] = True
        yield runtime
    finally:
        runtime_rows = {row["relative_path"]: row for row in runtime["files"]}
        for path in reversed(written):
            relative = str(path.relative_to(work_tree))
            row = runtime_rows[relative]
            current_sha = base.sha256_file(path) if path.is_file() else None
            base.atomic_replace_bytes(path, originals[path], mode=row["original_mode"])
            os.utime(
                path,
                ns=(row["original_atime_ns"], row["original_mtime_ns"]),
                follow_symlinks=False,
            )
            row["patched_content_unchanged"] = current_sha == patched_hashes[path]
            row["restored_sha256"] = base.sha256_file(path)
            row["restored_mode"] = stat.S_IMODE(path.stat().st_mode)
            row["restored"] = (
                row["restored_sha256"] == row["original_sha256"]
                and row["restored_mode"] == row["original_mode"]
            )
        runtime["patched_content_unchanged"] = (
            len(written) == len(VDSO_DEBUG_CONTROLS)
            and all(row.get("patched_content_unchanged") for row in runtime["files"])
        )
        runtime["restored"] = (
            len(written) == len(VDSO_DEBUG_CONTROLS)
            and all(row.get("restored") for row in runtime["files"])
        )
        if written and (
            not runtime["patched_content_unchanged"] or not runtime["restored"]
        ):
            raise BuildError("VDSO debug-path control was not cleanly restored")


def witness_output_gate(work_tree: Path) -> dict[str, Any]:
    dist = work_tree / "out/msm-waipio-waipio-gki/gki_kernel/dist"
    image = dist / "Image"
    vmlinux = dist / "vmlinux"
    config = work_tree / "out/msm-waipio-waipio-gki/gki_kernel/common/.config"
    missing = [str(path) for path in (image, vmlinux, config) if not path.is_file()]
    if missing:
        return {"missing": missing, "verified": False}
    marker = patch_check.MARKER.encode("ascii")
    image_data = image.read_bytes()
    vmlinux_data = vmlinux.read_bytes()
    config_text = config.read_text(encoding="utf-8")
    aligned_image_size = (len(image_data) + 4095) & ~4095
    result = {
        "image_size": len(image_data),
        "aligned_image_size": aligned_image_size,
        "stock_image_size": STOCK_IMAGE_SIZE,
        "exact_stock_image_size": len(image_data) == STOCK_IMAGE_SIZE,
        "fixed_kernel_slot_capacity": FIXED_KERNEL_SLOT_CAPACITY,
        "absolute_ramdisk_start": ABSOLUTE_RAMDISK_START,
        "pre_ramdisk_slack_remaining": FIXED_KERNEL_SLOT_CAPACITY - len(image_data),
        "fits_fixed_ramdisk_layout": len(image_data) <= FIXED_KERNEL_SLOT_CAPACITY,
        "preserves_fixed_ramdisk_start": (
            aligned_image_size == FIXED_KERNEL_SLOT_CAPACITY
        ),
        "image_marker_count": image_data.count(marker),
        "vmlinux_marker_count": vmlinux_data.count(marker),
        "image_family_count": image_data.count(R4W1B_MARKER_FAMILY),
        "vmlinux_family_count": vmlinux_data.count(R4W1B_MARKER_FAMILY),
        "image_historical_family_count": image_data.count(
            HISTORICAL_R4W1_MARKER_FAMILY
        ),
        "vmlinux_historical_family_count": vmlinux_data.count(
            HISTORICAL_R4W1_MARKER_FAMILY
        ),
        "config_enable_count": config_text.splitlines().count(
            "CONFIG_S22PLUS_FYG8_RETAINED_WITNESS=y"
        ),
        "fips_enable_count": config_text.splitlines().count(
            "CONFIG_CRYPTO_FIPS=y"
        ),
        "missing": [],
    }
    result["verified"] = (
        result["exact_stock_image_size"]
        and result["fits_fixed_ramdisk_layout"]
        and result["preserves_fixed_ramdisk_start"]
        and result["image_marker_count"] == 1
        and result["vmlinux_marker_count"] == 1
        and result["image_family_count"] == 1
        and result["vmlinux_family_count"] == 1
        and result["image_historical_family_count"] == 0
        and result["vmlinux_historical_family_count"] == 0
        and result["config_enable_count"] == 1
        and result["fips_enable_count"] == 1
    )
    return result


def collect_host_packaging_outputs(work_tree: Path) -> dict[str, Any]:
    dist = work_tree / "out/msm-waipio-waipio-gki/dist"
    rows = []
    for name in HOST_PACKAGING_OUTPUTS:
        path = dist / name
        if path.is_file() and not path.is_symlink():
            rows.append(
                {
                    "name": name,
                    "path": str(path),
                    "size": path.stat().st_size,
                    "sha256": base.sha256_file(path),
                }
            )
    present = {row["name"] for row in rows}
    return {
        "dist": str(dist),
        "expected": list(HOST_PACKAGING_OUTPUTS),
        "outputs": rows,
        "missing": sorted(set(HOST_PACKAGING_OUTPUTS) - present),
        "generated": bool(rows),
        "complete": present == set(HOST_PACKAGING_OUTPUTS),
        "promoted_as_live_candidate": False,
        "flash_authorized": False,
    }


def apply_checked_patch(work_tree: Path, patch: Path) -> dict[str, Any]:
    before: dict[str, dict[str, Any]] = {}
    for relative, expected in patch_check.BASE_FILES.items():
        path = work_tree / relative
        actual = base.sha256_file(path)
        if actual != expected:
            raise BuildError(f"pre-apply SHA mismatch for {relative}: {actual}")
        mode = stat.S_IMODE(path.stat().st_mode)
        before[relative] = {"sha256": actual, "mode": mode}
        os.chmod(path, mode | stat.S_IWUSR)
    completed = subprocess.run(
        ["patch", "--batch", "--forward", "-p1", "-i", str(patch)],
        cwd=work_tree,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0:
        raise BuildError(f"patch apply failed: {completed.stdout[-3000:]}")
    after: dict[str, dict[str, Any]] = {}
    for relative, expected in patch_check.PATCHED_FILES.items():
        path = work_tree / relative
        actual = base.sha256_file(path)
        if actual != expected:
            raise BuildError(f"post-apply SHA mismatch for {relative}: {actual}")
        after[relative] = {
            "sha256": actual,
            "mode": stat.S_IMODE(path.stat().st_mode),
        }
    return {
        "patch_sha256": base.sha256_file(patch),
        "stdout": completed.stdout,
        "before": before,
        "after": after,
        "verified": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "build"), default="preflight")
    parser.add_argument("--jobs", type=int, default=min(os.cpu_count() or 1, 8))
    parser.add_argument("--work-tree", type=Path, default=base.DEFAULT_WORK_TREE)
    parser.add_argument("--clang-repo", type=Path, default=base.DEFAULT_CLANG_REPO)
    parser.add_argument("--result-dir", type=Path, default=DEFAULT_RESULT_DIR)
    parser.add_argument("--base-archive", type=Path, default=base.DEFAULT_BASE_ARCHIVE)
    parser.add_argument("--delta-archive", type=Path, default=base.DEFAULT_DELTA_ARCHIVE)
    parser.add_argument("--overlay-audit", type=Path, default=base.DEFAULT_OVERLAY_AUDIT)
    parser.add_argument("--stock-baseline", type=Path, default=base.DEFAULT_STOCK_BASELINE)
    parser.add_argument("--patch", type=Path, default=patch_check.DEFAULT_PATCH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.jobs < 1 or args.jobs > 64:
        raise BuildError("--jobs must be between 1 and 64")
    root = base.repo_root()
    work_tree = base.resolve(root, args.work_tree)
    clang_repo = base.resolve(root, args.clang_repo)
    result_dir = base.resolve(root, args.result_dir)
    source_patch = base.resolve(root, args.patch)
    result_dir.mkdir(parents=True, exist_ok=True)

    host_tools = base.prepare_host_tool_overrides(work_tree)
    source_overlay = base.run_overlay_audit(
        root,
        work_tree,
        result_dir,
        base.resolve(root, args.base_archive),
        base.resolve(root, args.delta_archive),
        base.resolve(root, args.overlay_audit),
    )
    timestamp = base.inspect_timestamp_control(work_tree)
    kmi_path_control = inspect_kmi_path_control(work_tree)
    kernel_debug_control = inspect_kernel_debug_control(work_tree)
    vdso_debug_control = inspect_vdso_debug_control(work_tree)
    stock = base.inspect_stock_baseline(base.resolve(root, args.stock_baseline))
    r4_contract = patch_check.run_check(work_tree, source_patch)
    preflight = base.preflight(
        root,
        work_tree,
        clang_repo,
        lto="full",
        jobs=args.jobs,
        source_overlay=source_overlay,
        host_tool_overrides=host_tools,
        timestamp_control=timestamp,
        stock_baseline=stock,
    )
    preflight["build_allowed"] = (
        preflight["build_allowed"]
        and kmi_path_control["verified"]
        and kernel_debug_control["verified"]
        and vdso_debug_control["verified"]
    )
    preflight["provenance"]["kmi_path_control"] = kmi_path_control
    preflight["provenance"]["kernel_debug_control"] = kernel_debug_control
    preflight["provenance"]["vdso_debug_control"] = vdso_debug_control
    result: dict[str, Any] = {
        **preflight,
        "schema": SCHEMA,
        "base_schema": preflight["schema"],
        "r4w1b_patch_contract": r4_contract,
        "mode": args.mode,
        "stock_equivalent_claim": False,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "boot_image_packaging": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
        },
    }
    base.write_json(result_dir / "preflight.json", result)
    if args.mode == "preflight":
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if preflight["build_allowed"] else 2
    if not preflight["build_allowed"]:
        raise BuildError("build refused: clean-source preflight did not pass")

    source_delta = apply_checked_patch(work_tree, source_patch)
    base.write_json(result_dir / "source-delta.json", source_delta)
    incremental = base.prepare_incremental_dist_refresh(work_tree)
    environment = base.build_environment(
        work_tree, lto="full", jobs=args.jobs, clang_repo=clang_repo
    )
    command = ["./kernel_platform/build/android/prepare_vendor.sh", "sec", "gki"]
    time_file = result_dir / "time.txt"
    with apply_kmi_path_control(work_tree, kmi_path_control) as kmi_path_runtime:
        with apply_kernel_debug_control(
            work_tree, kernel_debug_control
        ) as kernel_debug_runtime:
            with apply_vdso_debug_control(
                work_tree, vdso_debug_control
            ) as vdso_debug_runtime:
                with base.apply_timestamp_control(
                    work_tree, timestamp
                ) as timestamp_runtime:
                    with (result_dir / "stdout.log").open(
                        "w", encoding="utf-8"
                    ) as stdout_log, (result_dir / "stderr.log").open(
                        "w", encoding="utf-8"
                    ) as stderr_log:
                        completed = subprocess.run(
                            ["/usr/bin/time", "-v", "-o", str(time_file), *command],
                            cwd=work_tree,
                            env=environment,
                            text=True,
                            stdout=stdout_log,
                            stderr=stderr_log,
                            check=False,
                        )
    providers = (
        base.run_provider_module_closure(
            work_tree, environment, result_dir, jobs=args.jobs
        )
        if completed.returncode == 0
        else {"providers": [], "verified": False, "skipped": True}
    )
    outputs = base.collect_outputs(work_tree)
    output_gate = base.output_gate(outputs)
    modules = base.collect_generated_modules(work_tree)
    module_gate = {"generated_module_count": len(modules), "verified": bool(modules)}
    banner_gate = base.kernel_banner_gate(
        work_tree, expected_banner=stock["expected_banner"]
    )
    witness_gate = witness_output_gate(work_tree)
    host_packaging = collect_host_packaging_outputs(work_tree)
    effective = completed.returncode
    gates = (
        (providers.get("verified", False), 5),
        (output_gate["verified"], 3),
        (module_gate["verified"], 4),
        (banner_gate["verified"], 6),
        (witness_gate["verified"], 7),
    )
    if effective == 0:
        for passed, code in gates:
            if not passed:
                effective = code
                break
    result.update(
        {
            "mode": "build",
            "build_command": command,
            "build_command_returncode": completed.returncode,
            "returncode": effective,
            "source_delta": source_delta,
            "outputs": outputs,
            "output_gate": output_gate,
            "generated_modules": modules,
            "module_gate": module_gate,
            "kernel_banner_gate": banner_gate,
            "witness_output_gate": witness_gate,
            "host_packaging_outputs": host_packaging,
            "timestamp_control_runtime": timestamp_runtime,
            "kmi_path_control_runtime": kmi_path_runtime,
            "kernel_debug_control_runtime": kernel_debug_runtime,
            "vdso_debug_control_runtime": vdso_debug_runtime,
            "provider_module_closure": providers,
            "symvers_files": base.collect_symvers(work_tree),
            "incremental_dist_refresh": incremental,
            "r4w1b_build_pass": effective == 0,
            "interpretation": (
                "host build only; generated packaging side outputs are not promoted "
                "as live candidates; R4 static KMI audit, reproducibility, artifact "
                "review, and a fresh live exception remain required"
            ),
        }
    )
    result["safety"].update(
        {
            "boot_image_packaging": host_packaging["generated"],
            "packaging_outputs_promoted": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
        }
    )
    base.write_json(result_dir / "result.json", result)
    print(
        json.dumps(
            {
                "result": "pass" if effective == 0 else "fail",
                "returncode": effective,
                "result_dir": base.display_path(root, result_dir),
                "image_size": witness_gate.get("image_size"),
                "slot_slack": witness_gate.get("pre_ramdisk_slack_remaining"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return effective


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BuildError, patch_check.CheckError, base.BuildError, OSError) as exc:
        raise SystemExit(str(exc)) from exc
