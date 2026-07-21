#!/usr/bin/env python3
"""Build the FYG8 R4W1-D contiguous PID1 witness kernel host-only."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import stat
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import s22plus_fyg8_kernel_build as base  # noqa: E402
import s22plus_fyg8_r4w1b_build as engine  # noqa: E402
import s22plus_fyg8_r4w1d_witness_contract as contract  # noqa: E402


SCHEMA = "s22plus_fyg8_r4w1d_build_v1"
TARGET = base.TARGET
DEFAULT_RESULT_DIR = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1d_build/build"
)
PROOF_BYTES = contract.PROOF.encode("ascii")
PROOF_FAMILY = contract.PROOF_FAMILY.encode("ascii")
HISTORICAL_FAMILIES = (b"[[S22R4W1B|", b"[[S22R4W1|")


class BuildError(ValueError):
    pass


@contextmanager
def apply_checked_patch(work_tree: Path, patch: Path) -> Iterator[dict[str, Any]]:
    """Reuse the hardened patch lifecycle with the R4W1-D exact contract."""

    previous = engine.patch_check
    engine.patch_check = contract
    try:
        with engine.apply_checked_patch(work_tree, patch) as runtime:
            yield runtime
    finally:
        engine.patch_check = previous


def _directory_flags(*, nofollow: bool) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if nofollow and hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _open_parent_at(root_fd: int, relative: Path) -> tuple[int, str]:
    if relative.is_absolute() or ".." in relative.parts or not relative.name:
        raise BuildError(f"unsafe source symlink path: {relative}")
    current = os.dup(root_fd)
    try:
        for component in relative.parts[:-1]:
            following = os.open(
                component,
                _directory_flags(nofollow=True),
                dir_fd=current,
            )
            os.close(current)
            current = following
        return current, relative.name
    except BaseException:
        os.close(current)
        raise


def _symlink_state_at(parent_fd: int, name: str) -> tuple[str | None, os.stat_result | None]:
    try:
        metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None, None
    if not stat.S_ISLNK(metadata.st_mode):
        return None, metadata
    target = os.readlink(name, dir_fd=parent_fd)
    metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    return target, metadata


def inspect_source_symlink_control(
    work_tree: Path, source_overlay: dict[str, Any]
) -> dict[str, Any]:
    """Pin archive-owned absolute symlinks before Samsung's build rewrites them."""

    if source_overlay.get("verified") is not True:
        return {"verified": False, "reason": "source-overlay-not-verified"}
    manifest_path = Path(str(source_overlay.get("manifest_path", "")))
    if manifest_path.is_symlink() or not manifest_path.is_file():
        return {"verified": False, "reason": "overlay-manifest-missing-or-indirect"}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"verified": False, "reason": "overlay-manifest-unreadable"}
    artifact_name = "reconstructed-final-members.jsonl"
    artifact = manifest.get("artifacts", {}).get(artifact_name)
    members_path = manifest_path.parent / artifact_name
    if (
        not isinstance(artifact, dict)
        or members_path.is_symlink()
        or not members_path.is_file()
        or members_path.stat().st_size != artifact.get("bytes")
        or base.sha256_file(members_path) != artifact.get("sha256")
    ):
        return {"verified": False, "reason": "overlay-members-identity-mismatch"}

    links: list[dict[str, Any]] = []
    seen: set[str] = set()
    root_fd = os.open(work_tree, _directory_flags(nofollow=False))
    try:
        root_metadata = os.fstat(root_fd)
        with members_path.open("r", encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                expected = row.get("link_target")
                if row.get("type") != "symlink" or not str(expected).startswith("/"):
                    continue
                relative = Path(str(row.get("path", "")))
                relative_text = str(relative)
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or not relative.name
                    or relative_text in seen
                ):
                    return {"verified": False, "reason": "unsafe-overlay-member-path"}
                seen.add(relative_text)
                parent_fd, name = _open_parent_at(root_fd, relative)
                try:
                    parent_metadata = os.fstat(parent_fd)
                    actual, metadata = _symlink_state_at(parent_fd, name)
                finally:
                    os.close(parent_fd)
                links.append(
                    {
                        "relative_path": relative_text,
                        "expected_target": expected,
                        "actual_target": actual,
                        "parent_device": parent_metadata.st_dev,
                        "parent_inode": parent_metadata.st_ino,
                        "original_atime_ns": (
                            metadata.st_atime_ns if metadata is not None else None
                        ),
                        "original_mtime_ns": (
                            metadata.st_mtime_ns if metadata is not None else None
                        ),
                        "verified": actual == expected,
                    }
                )
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"verified": False, "reason": "overlay-members-unreadable"}
    finally:
        os.close(root_fd)
    return {
        "manifest_path": str(manifest_path),
        "members_path": str(members_path),
        "members_sha256": artifact["sha256"],
        "work_tree_device": root_metadata.st_dev,
        "work_tree_inode": root_metadata.st_ino,
        "absolute_symlink_count": len(links),
        "links": links,
        "verified": bool(links) and all(row["verified"] for row in links),
    }


def _atomic_restore_symlink_at(parent_fd: int, name: str, target: str) -> None:
    temporary: str | None = None
    for _ in range(16):
        candidate = f".{name}.r4w1d-restore-{os.getpid()}-{secrets.token_hex(8)}"
        try:
            os.symlink(target, candidate, dir_fd=parent_fd)
            temporary = candidate
            break
        except FileExistsError:
            continue
    if temporary is None:
        raise BuildError(f"cannot reserve source symlink restore name: {name}")
    try:
        os.replace(
            temporary,
            name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
    finally:
        try:
            os.unlink(temporary, dir_fd=parent_fd)
        except FileNotFoundError:
            pass


@contextmanager
def preserve_source_symlinks(
    work_tree: Path, control: dict[str, Any]
) -> Iterator[dict[str, Any]]:
    """Restore source-archive symlinks even when the vendor build rewrites them."""

    if control.get("verified") is not True:
        raise BuildError("source symlink control is not verified")
    runtime = {
        **control,
        "links": [dict(row) for row in control["links"]],
        "applied": True,
        "restored": False,
    }
    root_fd = os.open(work_tree, _directory_flags(nofollow=False))
    root_metadata = os.fstat(root_fd)
    if (
        root_metadata.st_dev != control.get("work_tree_device")
        or root_metadata.st_ino != control.get("work_tree_inode")
    ):
        os.close(root_fd)
        raise BuildError("source work-tree identity changed before build")
    handles: list[tuple[int, str, dict[str, Any]]] = []
    try:
        for row in runtime["links"]:
            parent_fd, name = _open_parent_at(root_fd, Path(row["relative_path"]))
            parent_metadata = os.fstat(parent_fd)
            target, _ = _symlink_state_at(parent_fd, name)
            if (
                parent_metadata.st_dev != row["parent_device"]
                or parent_metadata.st_ino != row["parent_inode"]
                or target != row["expected_target"]
            ):
                os.close(parent_fd)
                raise BuildError(
                    f"source symlink changed before build: {row['relative_path']}"
                )
            handles.append((parent_fd, name, row))
    except BaseException:
        for parent_fd, _, _ in handles:
            os.close(parent_fd)
        os.close(root_fd)
        raise

    body_error: BaseException | None = None
    try:
        yield runtime
    except BaseException as exc:
        body_error = exc

    cleanup_errors: list[str] = []
    mutation_count = 0
    target_mutation_count = 0
    metadata_mutation_count = 0
    try:
        # Restore every held source location before reporting any cleanup error.
        for parent_fd, name, row in handles:
            try:
                observed, observed_metadata = _symlink_state_at(parent_fd, name)
                row["post_build_target"] = observed
                target_mutated = observed != row["expected_target"]
                metadata_mutated = (
                    observed_metadata is None
                    or observed_metadata.st_atime_ns != row["original_atime_ns"]
                    or observed_metadata.st_mtime_ns != row["original_mtime_ns"]
                )
                row["target_mutated_by_build"] = target_mutated
                row["metadata_mutated_by_build"] = metadata_mutated
                row["mutated_by_build"] = target_mutated or metadata_mutated
                mutation_count += int(row["mutated_by_build"])
                target_mutation_count += int(target_mutated)
                metadata_mutation_count += int(metadata_mutated)
                if target_mutated:
                    _atomic_restore_symlink_at(
                        parent_fd, name, row["expected_target"]
                    )
                restored_target, _ = _symlink_state_at(parent_fd, name)
                if restored_target != row["expected_target"]:
                    raise BuildError("restored target mismatch")
                os.utime(
                    name,
                    ns=(row["original_atime_ns"], row["original_mtime_ns"]),
                    dir_fd=parent_fd,
                    follow_symlinks=False,
                )
                restored_metadata = os.stat(
                    name, dir_fd=parent_fd, follow_symlinks=False
                )
                row["restored_target"] = restored_target
                row["restored_atime_ns"] = restored_metadata.st_atime_ns
                row["restored_mtime_ns"] = restored_metadata.st_mtime_ns
                row["restored"] = (
                    stat.S_ISLNK(restored_metadata.st_mode)
                    and restored_metadata.st_atime_ns == row["original_atime_ns"]
                    and restored_metadata.st_mtime_ns == row["original_mtime_ns"]
                )
                if not row["restored"]:
                    raise BuildError("restored metadata mismatch")
            except BaseException as exc:
                row["restored"] = False
                row["restore_error"] = f"{type(exc).__name__}: {exc}"
                cleanup_errors.append(
                    f"{row['relative_path']}: {row['restore_error']}"
                )

        # Reopen through the pinned root without following replaced parents.
        for row in runtime["links"]:
            reopened_fd: int | None = None
            try:
                reopened_fd, name = _open_parent_at(
                    root_fd, Path(row["relative_path"])
                )
                parent_metadata = os.fstat(reopened_fd)
                if (
                    parent_metadata.st_dev != row["parent_device"]
                    or parent_metadata.st_ino != row["parent_inode"]
                ):
                    raise BuildError("source parent identity changed")
                target, _ = _symlink_state_at(reopened_fd, name)
                if target != row["expected_target"]:
                    raise BuildError("source path target mismatch")
                os.utime(
                    name,
                    ns=(row["original_atime_ns"], row["original_mtime_ns"]),
                    dir_fd=reopened_fd,
                    follow_symlinks=False,
                )
                metadata = os.stat(
                    name, dir_fd=reopened_fd, follow_symlinks=False
                )
                row["path_identity_verified"] = (
                    stat.S_ISLNK(metadata.st_mode)
                    and metadata.st_atime_ns == row["original_atime_ns"]
                    and metadata.st_mtime_ns == row["original_mtime_ns"]
                )
                if not row["path_identity_verified"]:
                    raise BuildError("source path metadata mismatch")
            except BaseException as exc:
                row["path_identity_verified"] = False
                row["path_verification_error"] = f"{type(exc).__name__}: {exc}"
                cleanup_errors.append(
                    f"{row['relative_path']}: {row['path_verification_error']}"
                )
            finally:
                if reopened_fd is not None:
                    os.close(reopened_fd)

        runtime["mutation_count"] = mutation_count
        runtime["target_mutation_count"] = target_mutation_count
        runtime["metadata_mutation_count"] = metadata_mutation_count
        runtime["cleanup_errors"] = cleanup_errors
        runtime["restored"] = (
            not cleanup_errors
            and all(row.get("restored") for row in runtime["links"])
            and all(row.get("path_identity_verified") for row in runtime["links"])
        )
        runtime["verified"] = runtime["restored"]
    finally:
        for parent_fd, _, _ in handles:
            os.close(parent_fd)
        os.close(root_fd)

    if cleanup_errors:
        cleanup_error = BuildError(
            "source symlink cleanup failed: " + "; ".join(cleanup_errors)
        )
        if body_error is not None:
            raise BuildError(
                "source symlink guarded body failed "
                f"({type(body_error).__name__}: {body_error}); {cleanup_error}"
            ) from body_error
        raise cleanup_error
    if body_error is not None:
        raise body_error


def witness_output_gate(work_tree: Path) -> dict[str, Any]:
    dist = work_tree / "out/msm-waipio-waipio-gki/gki_kernel/dist"
    image = dist / "Image"
    vmlinux = dist / "vmlinux"
    config = work_tree / "out/msm-waipio-waipio-gki/gki_kernel/common/.config"
    missing = [str(path) for path in (image, vmlinux, config) if not path.is_file()]
    if missing:
        return {"missing": missing, "verified": False}
    image_data = image.read_bytes()
    vmlinux_data = vmlinux.read_bytes()
    config_lines = config.read_text(encoding="utf-8").splitlines()
    aligned_image_size = (len(image_data) + 4095) & ~4095
    result = {
        "image_path": str(image),
        "vmlinux_path": str(vmlinux),
        "image_size": len(image_data),
        "aligned_image_size": aligned_image_size,
        "stock_image_size": engine.STOCK_IMAGE_SIZE,
        "exact_stock_image_size": len(image_data) == engine.STOCK_IMAGE_SIZE,
        "fixed_kernel_slot_capacity": engine.FIXED_KERNEL_SLOT_CAPACITY,
        "absolute_ramdisk_start": engine.ABSOLUTE_RAMDISK_START,
        "pre_ramdisk_slack_remaining": (
            engine.FIXED_KERNEL_SLOT_CAPACITY - len(image_data)
        ),
        "fits_fixed_ramdisk_layout": (
            len(image_data) <= engine.FIXED_KERNEL_SLOT_CAPACITY
        ),
        "preserves_fixed_ramdisk_start": (
            aligned_image_size == engine.FIXED_KERNEL_SLOT_CAPACITY
        ),
        "image_proof_count": image_data.count(PROOF_BYTES),
        "vmlinux_proof_count": vmlinux_data.count(PROOF_BYTES),
        "image_proof_family_count": image_data.count(PROOF_FAMILY),
        "vmlinux_proof_family_count": vmlinux_data.count(PROOF_FAMILY),
        "historical_family_counts": {
            family.decode("ascii"): {
                "image": image_data.count(family),
                "vmlinux": vmlinux_data.count(family),
            }
            for family in HISTORICAL_FAMILIES
        },
        "config_enable_count": config_lines.count(f"{contract.CONFIG}=y"),
        "legacy_config_enable_count": config_lines.count(
            "CONFIG_S22PLUS_FYG8_RETAINED_WITNESS=y"
        ),
        "fips_enable_count": config_lines.count("CONFIG_CRYPTO_FIPS=y"),
        "missing": [],
    }
    result["verified"] = (
        result["exact_stock_image_size"]
        and result["fits_fixed_ramdisk_layout"]
        and result["preserves_fixed_ramdisk_start"]
        and result["image_proof_count"] == 1
        and result["vmlinux_proof_count"] == 1
        and result["image_proof_family_count"] == 1
        and result["vmlinux_proof_family_count"] == 1
        and all(
            row["image"] == 0 and row["vmlinux"] == 0
            for row in result["historical_family_counts"].values()
        )
        and result["config_enable_count"] == 1
        and result["legacy_config_enable_count"] == 0
        and result["fips_enable_count"] == 1
    )
    return result


def sec_log_buf_timing_gate(work_tree: Path) -> dict[str, Any]:
    config = work_tree / "out/msm-waipio-waipio-gki/msm-kernel/.config"
    module = work_tree / "out/msm-waipio-waipio-gki/dist/sec_log_buf.ko"
    if config.is_symlink() or not config.is_file():
        return {
            "config_path": str(config),
            "module_path": str(module),
            "verified": False,
            "reason": "vendor-config-missing-or-indirect",
        }
    values = [
        line.split("=", 1)[1]
        for line in config.read_text(encoding="utf-8").splitlines()
        if line.startswith("CONFIG_SEC_LOG_BUF=")
    ]
    module_regular = module.is_file() and not module.is_symlink()
    module_size = module.stat().st_size if module_regular else None
    module_elf_magic = False
    if module_regular:
        with module.open("rb") as stream:
            module_elf_magic = stream.read(4) == b"\x7fELF"
    result = {
        "config_path": str(config),
        "config_values": values,
        "module_path": str(module),
        "module_regular": module_regular,
        "module_size": module_size,
        "module_elf_magic": module_elf_magic,
        "module_sha256": base.sha256_file(module) if module_regular else None,
        "pid1_timing_interpretation": (
            "sec_log_buf is a loadable module and cannot execute before the first "
            "successful /init transition"
        ),
    }
    result["verified"] = (
        values == ["m"]
        and module_regular
        and bool(module_size)
        and module_elf_magic
    )
    return result


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
    parser.add_argument("--patch", type=Path, default=contract.DEFAULT_PATCH)
    parser.add_argument(
        "--inherited-result", type=Path, default=contract.DEFAULT_INHERITED_RESULT
    )
    parser.add_argument(
        "--carrier-boot", type=Path, default=contract.DEFAULT_CARRIER_BOOT
    )
    parser.add_argument(
        "--carrier-init", type=Path, default=contract.DEFAULT_CARRIER_INIT
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.jobs < 1 or args.jobs > 64:
        raise BuildError("--jobs must be between 1 and 64")
    root = base.repo_root()
    path_arguments = (
        args.work_tree,
        args.clang_repo,
        args.result_dir,
        args.base_archive,
        args.delta_archive,
        args.overlay_audit,
        args.stock_baseline,
        args.patch,
        args.inherited_result,
        args.carrier_boot,
        args.carrier_init,
    )
    if any(path.is_absolute() for path in path_arguments):
        raise BuildError("R4W1-D isolated execution requires repo-relative paths")
    reexecuted = engine.reexec_in_private_repo_namespace(
        root,
        script=Path(__file__),
        arguments=sys.argv[1:],
        compatibility_work_tree=args.work_tree,
    )
    if reexecuted is not None:
        return reexecuted
    private_namespace = engine.inspect_private_namespace(root)
    if not private_namespace["verified"]:
        raise BuildError("R4W1-D private repository namespace is not verified")
    recorded_root = Path(private_namespace["recorded_repo"])
    work_tree = base.resolve(root, args.work_tree)
    clang_repo = base.resolve(root, args.clang_repo)
    result_dir = base.resolve(root, args.result_dir)
    source_patch = base.resolve(root, args.patch)
    inherited_result = base.resolve(root, args.inherited_result)
    carrier_boot = base.resolve(root, args.carrier_boot)
    carrier_init = base.resolve(root, args.carrier_init)
    engine.create_exclusive_result_dir(result_dir)
    clean_output = engine.inspect_clean_output_precondition(work_tree)
    if not clean_output["verified"]:
        raise BuildError(f"clean build requires absent output tree: {clean_output['path']}")

    host_tools = base.prepare_host_tool_overrides(work_tree)
    source_overlay = base.run_overlay_audit(
        root,
        work_tree,
        result_dir,
        base.resolve(root, args.base_archive),
        base.resolve(root, args.delta_archive),
        base.resolve(root, args.overlay_audit),
    )
    source_symlink_control = inspect_source_symlink_control(work_tree, source_overlay)
    timestamp = base.inspect_timestamp_control(work_tree)
    kmi_path_control = engine.inspect_kmi_path_control(work_tree)
    kernel_debug_control = engine.inspect_kernel_debug_control(work_tree)
    vdso_debug_control = engine.inspect_vdso_debug_control(work_tree)
    stock = base.inspect_stock_baseline(base.resolve(root, args.stock_baseline))
    witness_contract = contract.run_check(
        work_tree,
        source_patch,
        inherited_result,
        carrier_boot,
        carrier_init,
    )
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
        and clean_output["verified"]
        and kmi_path_control["verified"]
        and kernel_debug_control["verified"]
        and vdso_debug_control["verified"]
        and source_symlink_control["verified"]
        and witness_contract["verdict"] == contract.VERDICT
    )
    preflight["provenance"].update(
        {
            "kmi_path_control": kmi_path_control,
            "kernel_debug_control": kernel_debug_control,
            "vdso_debug_control": vdso_debug_control,
            "clean_output_precondition": clean_output,
            "source_symlink_control": source_symlink_control,
            "private_namespace": private_namespace,
        }
    )
    result: dict[str, Any] = {
        **preflight,
        "schema": SCHEMA,
        "base_schema": preflight["schema"],
        "r4w1d_witness_contract": witness_contract,
        "mode": args.mode,
        "result_directory": {
            "path": str(result_dir),
            "created_exclusively": True,
        },
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
    base.write_json(
        result_dir / "preflight.json",
        engine.rebase_recorded_paths(
            result,
            observed_root=root,
            recorded_root=recorded_root,
            embedded=True,
        ),
    )
    if args.mode == "preflight":
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if preflight["build_allowed"] else 2
    if not preflight["build_allowed"]:
        raise BuildError("build refused: clean-source preflight did not pass")

    with engine.create_exclusive_output_root(
        work_tree, expected_work_tree=clean_output
    ) as output_root_runtime:
        bound_work_tree = Path(output_root_runtime["_work_tree_fd_path"])
        with preserve_source_symlinks(
            bound_work_tree, source_symlink_control
        ) as source_symlink_runtime:
            with apply_checked_patch(bound_work_tree, source_patch) as source_delta:
                incremental = base.prepare_incremental_dist_refresh(bound_work_tree)
                if incremental.get("removed"):
                    raise BuildError("clean build unexpectedly removed incremental outputs")
                incremental["clean_output_tree"] = output_root_runtime["empty_at_creation"]
                environment = base.build_environment(
                    work_tree, lto="full", jobs=args.jobs, clang_repo=clang_repo
                )
                environment = {
                    key: value.replace(str(work_tree), str(bound_work_tree))
                    for key, value in environment.items()
                }
                command = [
                    "./kernel_platform/build/android/prepare_vendor.sh",
                    "sec",
                    "gki",
                ]
                time_file = result_dir / "time.txt"
                with engine.apply_kmi_path_control(
                    bound_work_tree, kmi_path_control
                ) as kmi_path_runtime:
                    with engine.apply_kernel_debug_control(
                        bound_work_tree, kernel_debug_control
                    ) as kernel_debug_runtime:
                        with engine.apply_vdso_debug_control(
                            bound_work_tree, vdso_debug_control
                        ) as vdso_debug_runtime:
                            with base.apply_timestamp_control(
                                bound_work_tree, timestamp
                            ) as timestamp_runtime:
                                with (result_dir / "stdout.log").open(
                                    "w", encoding="utf-8"
                                ) as stdout_log, (result_dir / "stderr.log").open(
                                    "w", encoding="utf-8"
                                ) as stderr_log:
                                    completed = subprocess.run(
                                        [
                                            "/usr/bin/time",
                                            "-v",
                                            "-o",
                                            str(time_file),
                                            *command,
                                        ],
                                        cwd=bound_work_tree,
                                        env=environment,
                                        text=True,
                                        stdout=stdout_log,
                                        stderr=stderr_log,
                                        check=False,
                                    )
                providers = (
                    base.run_provider_module_closure(
                        bound_work_tree, environment, result_dir, jobs=args.jobs
                    )
                    if completed.returncode == 0
                    else {"providers": [], "verified": False, "skipped": True}
                )
            outputs = engine.rebase_recorded_paths(
                base.collect_outputs(bound_work_tree),
                observed_root=bound_work_tree,
                recorded_root=work_tree,
            )
            output_gate = base.output_gate(outputs)
            modules = engine.rebase_recorded_paths(
                base.collect_generated_modules(bound_work_tree),
                observed_root=bound_work_tree,
                recorded_root=work_tree,
            )
            module_gate = {
                "generated_module_count": len(modules),
                "verified": bool(modules),
            }
            banner_gate = engine.rebase_recorded_paths(
                base.kernel_banner_gate(
                    bound_work_tree, expected_banner=stock["expected_banner"]
                ),
                observed_root=bound_work_tree,
                recorded_root=work_tree,
            )
            witness_gate = engine.rebase_recorded_paths(
                witness_output_gate(bound_work_tree),
                observed_root=bound_work_tree,
                recorded_root=work_tree,
            )
            writer_timing_gate = engine.rebase_recorded_paths(
                sec_log_buf_timing_gate(bound_work_tree),
                observed_root=bound_work_tree,
                recorded_root=work_tree,
            )
            host_packaging = engine.rebase_recorded_paths(
                engine.collect_host_packaging_outputs(bound_work_tree),
                observed_root=bound_work_tree,
                recorded_root=work_tree,
            )
            symvers_files = engine.rebase_recorded_paths(
                engine.collect_bound_symvers(bound_work_tree),
                observed_root=bound_work_tree,
                recorded_root=work_tree,
            )
    output_root_runtime.pop("_work_tree_fd_path", None)
    base.write_json(
        result_dir / "source-delta.json",
        engine.rebase_recorded_paths(
            source_delta,
            observed_root=root,
            recorded_root=recorded_root,
            embedded=True,
        ),
    )
    effective = completed.returncode
    gates = (
        (source_delta.get("verified", False), 8),
        (
            clean_output["verified"]
            and output_root_runtime.get("verified") is True
            and not incremental.get("removed")
            and incremental.get("clean_output_tree") is True,
            9,
        ),
        (providers.get("verified", False), 5),
        (output_gate["verified"], 3),
        (module_gate["verified"], 4),
        (banner_gate["verified"], 6),
        (witness_gate["verified"], 7),
        (writer_timing_gate["verified"], 10),
        (source_symlink_runtime["verified"], 11),
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
            "source_symlink_control_runtime": source_symlink_runtime,
            "clean_output_precondition": clean_output,
            "exclusive_output_root": output_root_runtime,
            "outputs": outputs,
            "output_gate": output_gate,
            "generated_modules": modules,
            "module_gate": module_gate,
            "kernel_banner_gate": banner_gate,
            "witness_output_gate": witness_gate,
            "sec_log_buf_timing_gate": writer_timing_gate,
            "host_packaging_outputs": host_packaging,
            "timestamp_control_runtime": timestamp_runtime,
            "kmi_path_control_runtime": kmi_path_runtime,
            "kernel_debug_control_runtime": kernel_debug_runtime,
            "vdso_debug_control_runtime": vdso_debug_runtime,
            "provider_module_closure": providers,
            "symvers_files": symvers_files,
            "incremental_dist_refresh": incremental,
            "r4w1d_build_pass": effective == 0,
            "interpretation": (
                "host build only; the contiguous proof is not reset-atomic; generated "
                "packaging outputs are not promoted; reproducibility, static audit, "
                "candidate construction, and fresh Process v2 approval remain required"
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
    base.write_json(
        result_dir / "result.json",
        engine.rebase_recorded_paths(
            result,
            observed_root=root,
            recorded_root=recorded_root,
            embedded=True,
        ),
    )
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
    except (BuildError, contract.CheckError, engine.BuildError, base.BuildError, OSError) as exc:
        raise SystemExit(str(exc)) from exc
