#!/usr/bin/env python3
"""Build the patched FYG8 R4W1 retained-init witness kernel host-only."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import s22plus_fyg8_kernel_build as base  # noqa: E402
import s22plus_fyg8_r4w1_patch_check as patch_check  # noqa: E402


SCHEMA = "s22plus_fyg8_r4w1_build_v1"
TARGET = base.TARGET
STOCK_IMAGE_SIZE = 41_490_944
FIXED_KERNEL_SLOT_CAPACITY = 41_492_480
DEFAULT_RESULT_DIR = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1_build/build"
)


class BuildError(ValueError):
    pass


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
    result = {
        "image_size": len(image_data),
        "stock_image_size": STOCK_IMAGE_SIZE,
        "fixed_kernel_slot_capacity": FIXED_KERNEL_SLOT_CAPACITY,
        "pre_ramdisk_slack_remaining": FIXED_KERNEL_SLOT_CAPACITY - len(image_data),
        "fits_fixed_ramdisk_layout": len(image_data) <= FIXED_KERNEL_SLOT_CAPACITY,
        "image_marker_count": image_data.count(marker),
        "vmlinux_marker_count": vmlinux_data.count(marker),
        "config_enable_count": config_text.splitlines().count(
            "CONFIG_S22PLUS_FYG8_RETAINED_WITNESS=y"
        ),
        "missing": [],
    }
    result["verified"] = (
        result["fits_fixed_ramdisk_layout"]
        and result["image_marker_count"] == 1
        and result["vmlinux_marker_count"] == 1
        and result["config_enable_count"] == 1
    )
    return result


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
    result: dict[str, Any] = {
        **preflight,
        "schema": SCHEMA,
        "base_schema": preflight["schema"],
        "r4w1_patch_contract": r4_contract,
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
    with base.apply_timestamp_control(work_tree, timestamp) as timestamp_runtime:
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
            "timestamp_control_runtime": timestamp_runtime,
            "provider_module_closure": providers,
            "symvers_files": base.collect_symvers(work_tree),
            "incremental_dist_refresh": incremental,
            "r4w1_build_pass": effective == 0,
            "interpretation": (
                "host build only; R4 static KMI audit, reproducibility, artifact "
                "review, and a fresh live exception remain required"
            ),
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
