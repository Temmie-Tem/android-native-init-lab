#!/usr/bin/env python3
"""Build one P3.18 boot-only candidate after its exact closure validates."""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

import build_s22plus_fyg8_p310_candidate as p310_builder
import build_s22plus_fyg8_p316_candidate as base
import s22plus_fyg8_p318_candidate_contract as candidate_contract
import s22plus_fyg8_p318_e2_stock_closure as closure
import s22plus_fyg8_p318_overlay_contract as contract
import s22plus_fyg8_p318_qualification_closure as qualification
import s22plus_fyg8_p318_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p318_candidate_artifact_result_v1"
VERDICT = "PASS_P318_DETERMINISTIC_BOOT_ONLY_CANDIDATE_HOST_ONLY"
TARGET = contract.TARGET
P286_SOURCE_CONTRACT_ID = contract.PARENT_SOURCE_CONTRACT_ID
DEFAULT_IMAGE = contract.PARENT_IMAGE
DEFAULT_REPRO_RESULT = contract.PARENT_REPRO_RESULT
DEFAULT_USERSPACE = userspace.DEFAULT_OUT
DEFAULT_BASE_BOOT = base.DEFAULT_BASE_BOOT
DEFAULT_VENDOR_RAMDISK = base.DEFAULT_VENDOR_RAMDISK
DEFAULT_LZ4 = base.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = base.DEFAULT_MAGISKBOOT
DEFAULT_LATCH = Path(
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "dwc3-event-latch-build-20260814-01/immutable-a/s22plus_dwc3_event_latch.ko"
)
DEFAULT_DIAGNOSTIC = Path(
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "max77705-timed-diag-build-20260814-01/immutable-a/"
    "s22plus_max77705_mux_diag_p318.ko"
)
DEFAULT_PREPACKAGING = qualification.DEFAULT_PREPACKAGING
DEFAULT_OUT = qualification.DEFAULT_CANDIDATE_A
LATCH_NAME = "s22plus_dwc3_event_latch.ko"
DIAGNOSTIC_NAME = "s22plus_max77705_mux_diag_p318.ko"
OLD_DIAGNOSTIC_NAME = "s22plus_max77705_mux_diag.ko"
LATCH_RAMDISK_PATH = f"lib/modules/{LATCH_NAME}"
DIAGNOSTIC_RAMDISK_PATH = f"lib/modules/{DIAGNOSTIC_NAME}"
OLD_DIAGNOSTIC_RAMDISK_PATH = f"lib/modules/{OLD_DIAGNOSTIC_NAME}"
BOOT_SIZE = base.BOOT_SIZE
KERNEL_START = base.KERNEL_START
KERNEL_END = base.KERNEL_END
BuildError = base.BuildError
receipt = base.receipt

_PREPACKAGING_RECEIPT: dict[str, Any] | None = None
_PREPACKAGING_VALIDATION: dict[str, Any] | None = None


def _generic_base():
    return base._generic_base()  # noqa: SLF001


def _read_json(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    payload = candidate_contract.stable_read(path, label, 64 * 1024 * 1024)
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BuildError(f"{label} is not ASCII JSON") from exc
    if not isinstance(value, dict):
        raise BuildError(f"{label} root differs")
    return payload, value


def verify_repro_result(
    result_path: Path,
    image_receipt: dict[str, Any],
    exact_contract: dict[str, Any],
    **_ignored: Any,
) -> dict[str, Any]:
    return base.parent.verify_repro_result(result_path, image_receipt, exact_contract)


def artifact_safety(exact_contract: dict[str, Any]) -> dict[str, Any]:
    if _PREPACKAGING_RECEIPT is None or _PREPACKAGING_VALIDATION is None:
        raise BuildError("P3.18 prepackaging gate was not established")
    result = p310_builder._BASE_ARTIFACT_SAFETY(exact_contract)  # noqa: SLF001
    result.update({
        "fixed_p310_image": True,
        "p318_kernel_rebuild": False,
        "p318_full_lto_ab": False,
        "stock_early_module_count": 69,
        "custom_early_module_count": 1,
        "effective_early_module_count": 70,
        "custom_module_binaries_injected": 2,
        "latch_early_plan_and_boot_ramdisk": True,
        "diagnostic_late_load_only": True,
        "diagnostic_absent_from_early_plan": True,
        "p318_prepackaging_closure": _PREPACKAGING_RECEIPT,
        "p318_prepackaging_validation": _PREPACKAGING_VALIDATION,
        "p318_runtime_qualification": exact_contract["runtime_qualification"],
        "p318_envelope_qualification": exact_contract["envelope_qualification"],
        "p318_topology_receipt": exact_contract["topology_receipt"],
        "fixed_image_sha256": contract.EXPECTED_IMAGE["sha256"],
    })
    return result


def _configure() -> None:
    base.parent._configure()  # noqa: SLF001
    candidate_contract._configure()  # noqa: SLF001
    generic = _generic_base()
    generic.candidate_contract = candidate_contract
    generic.userspace = userspace
    generic.p286_closure = closure
    generic.SCHEMA = SCHEMA
    generic.VERDICT = VERDICT
    generic.TARGET = TARGET
    generic.P286_SOURCE_CONTRACT_ID = P286_SOURCE_CONTRACT_ID
    generic.DEFAULT_IMAGE = DEFAULT_IMAGE
    generic.DEFAULT_REPRO_RESULT = DEFAULT_REPRO_RESULT
    generic.DEFAULT_USERSPACE = DEFAULT_USERSPACE
    generic.DEFAULT_OUT = DEFAULT_OUT
    generic.verify_repro_result = verify_repro_result
    generic.artifact_safety = artifact_safety


def _exists(base_api, magiskboot: Path, ramdisk: Path, member: str, cwd: Path) -> bool:  # noqa: ANN001
    completed = base_api.carrier.run(
        [magiskboot, "cpio", ramdisk, f"exists {member}"], cwd=cwd
    )
    if completed.returncode not in (0, 1):
        raise BuildError(f"P3.18 ramdisk existence check failed: {member}")
    return completed.returncode == 0


def _inject_custom_modules(
    *,
    base_candidate: Path,
    staging: Path,
    latch: bytes,
    diagnostic: bytes,
    magiskboot: bytes,
    lz4: bytes,
    image: bytes,
    userspace_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    generic = _generic_base()
    audit = staging / "audit"
    work = staging / "work"
    final_unpack = staging / "final-unpack"
    for directory in (audit, work, final_unpack):
        directory.mkdir()
    pinned_magiskboot = audit / "magiskboot"
    pinned_lz4 = audit / "lz4"
    latch_path = audit / LATCH_NAME
    diagnostic_path = audit / DIAGNOSTIC_NAME
    generic.carrier.stage_file(pinned_magiskboot, magiskboot, executable=True)
    generic.carrier.stage_file(pinned_lz4, lz4, executable=True)
    generic.carrier.stage_file(latch_path, latch)
    generic.carrier.stage_file(diagnostic_path, diagnostic)
    source_boot = base_candidate / "boot.img"
    source_boot_bytes = candidate_contract.stable_read(
        source_boot, "P3.18 base candidate boot", BOOT_SIZE
    )
    if len(source_boot_bytes) != BOOT_SIZE:
        raise BuildError("P3.18 base candidate boot size differs")
    generic.carrier.run_in_dir(
        [pinned_magiskboot, "unpack", "-h", source_boot],
        work,
        "P3.18 unpack base candidate",
    )
    ramdisk = work / "ramdisk.cpio"
    if any(
        _exists(generic, pinned_magiskboot, ramdisk, member, work)
        for member in (
            LATCH_RAMDISK_PATH,
            DIAGNOSTIC_RAMDISK_PATH,
            OLD_DIAGNOSTIC_RAMDISK_PATH,
        )
    ):
        raise BuildError("P3.18 custom or predecessor diagnostic exists in base")
    for member, source in (
        (LATCH_RAMDISK_PATH, latch_path),
        (DIAGNOSTIC_RAMDISK_PATH, diagnostic_path),
    ):
        generic.carrier.run_in_dir(
            [pinned_magiskboot, "cpio", ramdisk, f"add 644 {member} {source}"],
            work,
            f"P3.18 add {member}",
        )
    boot_path = staging / "boot.img"
    generic.carrier.run_in_dir(
        [pinned_magiskboot, "repack", source_boot, boot_path],
        work,
        "P3.18 repack custom module carrier",
    )
    candidate = boot_path.read_bytes()
    if len(candidate) != BOOT_SIZE:
        raise BuildError("P3.18 custom module candidate boot size differs")
    generic.carrier.run_in_dir(
        [pinned_magiskboot, "unpack", "-h", boot_path],
        final_unpack,
        "P3.18 unpack final candidate",
    )
    final_ramdisk = final_unpack / "ramdisk.cpio"
    extracted = {
        "init": ("init", audit / "init.final"),
        "child": ("s22-e1-child", audit / "child.final"),
        "latch": (LATCH_RAMDISK_PATH, audit / "latch.final"),
        "diagnostic": (DIAGNOSTIC_RAMDISK_PATH, audit / "diag.final"),
    }
    for label, (member, target) in extracted.items():
        generic.carrier.run_in_dir(
            [pinned_magiskboot, "cpio", final_ramdisk, f"extract {member} {target}"],
            final_unpack,
            f"P3.18 extract final {label}",
        )
    expected_init = candidate_contract.stable_read(
        userspace_dir / "init", "P3.18 exact init", 1024 * 1024
    )
    expected_child = candidate_contract.stable_read(
        userspace_dir / "s22-e1-child", "P3.18 exact child", 1024 * 1024
    )
    if (
        extracted["init"][1].read_bytes() != expected_init
        or extracted["child"][1].read_bytes() != expected_child
        or extracted["latch"][1].read_bytes() != latch
        or extracted["diagnostic"][1].read_bytes() != diagnostic
        or (final_unpack / "kernel").read_bytes() != image
        or _exists(
            generic, pinned_magiskboot, final_ramdisk,
            OLD_DIAGNOSTIC_RAMDISK_PATH, final_unpack,
        )
    ):
        raise BuildError("P3.18 final candidate content differs")
    try:
        package_result = generic.packager.package(
            boot_path=boot_path,
            lz4_path=pinned_lz4,
            output_dir=staging,
            audit_dir=audit,
        )
    except (generic.packager.PackageError, generic.carrier.BuildError) as exc:
        raise BuildError(str(exc)) from exc
    construction = {
        "parent_boot": receipt(source_boot_bytes),
        "latch_module": receipt(latch),
        "diagnostic_module": receipt(diagnostic),
        "latch_staged_path": LATCH_RAMDISK_PATH,
        "diagnostic_staged_path": DIAGNOSTIC_RAMDISK_PATH,
        "both_custom_modules_absent_from_base": True,
        "old_p317_diagnostic_absent": True,
        "latch_staged_exactly_once": True,
        "diagnostic_staged_exactly_once": True,
        "latch_present_in_early_plan": True,
        "diagnostic_absent_from_early_plan": True,
        "ramdisk_custom_module_mode": "0644",
        "kernel_exact_fixed_image": True,
        "init_and_child_exact_userspace": True,
    }
    outputs = {
        "boot_img": receipt(candidate),
        "boot_img_lz4": package_result["boot_img_lz4"],
        "ap_tar_md5": package_result["ap_tar_md5"],
        "ap_structure": package_result["ap_structure"],
        "packager": package_result,
    }
    shutil.rmtree(work)
    shutil.rmtree(final_unpack)
    shutil.rmtree(audit)
    return construction, outputs


def build_candidate(args: argparse.Namespace) -> dict[str, Any]:
    global _PREPACKAGING_RECEIPT, _PREPACKAGING_VALIDATION

    root = candidate_contract.intent.repo_root()
    output = candidate_contract.intent.resolve(root, args.out)
    if output.exists() or output.is_symlink():
        raise BuildError(f"P3.18 candidate output exists: {output}")
    intent_path = candidate_contract.intent.resolve(root, args.intent)
    exact = contract.verify_intent(root, intent_path)
    pre_path = candidate_contract.intent.resolve(root, args.prepackaging)
    pre_payload, pre = _read_json(pre_path, "P3.18 prepackaging closure")
    validation = qualification.validate_prepackaging_artifact(
        pre, root=root, intent_path=intent_path
    )
    latch = candidate_contract.stable_read(
        candidate_contract.intent.resolve(root, args.latch),
        "P3.18 exact early latch module",
        4 * 1024 * 1024,
    )
    diagnostic = candidate_contract.stable_read(
        candidate_contract.intent.resolve(root, args.diagnostic),
        "P3.18 exact late diagnostic module",
        4 * 1024 * 1024,
    )
    for label, payload, key in (
        ("latch", latch, "early_latch"),
        ("diagnostic", diagnostic, "late_diagnostic"),
    ):
        expected = {
            name: exact["module_identities"][key][name]
            for name in ("size", "sha256")
        }
        if receipt(payload) != expected:
            raise BuildError(f"P3.18 {label} module identity differs")
    image = candidate_contract.stable_read(
        candidate_contract.intent.resolve(root, args.image),
        "P3.18 fixed Image",
        KERNEL_END - KERNEL_START,
    )
    if receipt(image) != contract.EXPECTED_IMAGE:
        raise BuildError("P3.18 fixed Image identity differs")
    lz4 = candidate_contract.stable_read(
        candidate_contract.intent.resolve(root, args.lz4),
        "P3.18 pinned lz4",
        8 * 1024 * 1024,
    )
    magiskboot = candidate_contract.stable_read(
        candidate_contract.intent.resolve(root, args.magiskboot),
        "P3.18 pinned magiskboot",
        32 * 1024 * 1024,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    _PREPACKAGING_RECEIPT = receipt(pre_payload)
    _PREPACKAGING_VALIDATION = validation
    try:
        _configure()
        with tempfile.TemporaryDirectory(prefix=f".{output.name}.", dir=output.parent) as name:
            temporary = Path(name)
            base_output = temporary / "base-candidate"
            final_output = temporary / "final-candidate"
            base_args = copy.copy(args)
            base_args.out = base_output
            base_result = _generic_base().build_candidate(base_args)
            final_output.mkdir()
            construction, outputs = _inject_custom_modules(
                base_candidate=base_output,
                staging=final_output,
                latch=latch,
                diagnostic=diagnostic,
                magiskboot=magiskboot,
                lz4=lz4,
                image=image,
                userspace_dir=candidate_contract.intent.resolve(root, args.userspace),
            )
            result = {
                **base_result,
                "schema": SCHEMA,
                "verdict": VERDICT,
                "construction": {
                    **base_result["construction"],
                    **construction,
                    "module_binaries_injected": 2,
                    "vendor_ramdisk_modules_reused": True,
                },
                "outputs": outputs,
                "prepackaging_closure": receipt(pre_payload),
                "prepackaging_validation": validation,
                "safety": artifact_safety(base_result["candidate_contract"]),
            }
            (final_output / "artifact-result.json").write_text(
                json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
                encoding="ascii",
            )
            os.replace(final_output, output)
    finally:
        _PREPACKAGING_RECEIPT = None
        _PREPACKAGING_VALIDATION = None
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    _configure()
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--latch", type=Path, default=DEFAULT_LATCH)
    parser.add_argument("--diagnostic", type=Path, default=DEFAULT_DIAGNOSTIC)
    parser.add_argument("--prepackaging", type=Path, default=DEFAULT_PREPACKAGING)
    selected, remaining = parser.parse_known_args(argv)
    args = _generic_base().parse_args(remaining)
    args.latch = selected.latch
    args.diagnostic = selected.diagnostic
    args.prepackaging = selected.prepackaging
    return args


def main(argv: list[str] | None = None) -> int:
    try:
        result = build_candidate(parse_args(argv))
    except (
        BuildError, qualification.QualificationError,
        candidate_contract.ContractError, candidate_contract.intent.IntentError,
        subprocess.TimeoutExpired, OSError, ValueError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({
        "schema": SCHEMA,
        "verdict": result["verdict"],
        "boot_sha256": result["outputs"]["boot_img"]["sha256"],
        "ap_sha256": result["outputs"]["ap_tar_md5"]["sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
