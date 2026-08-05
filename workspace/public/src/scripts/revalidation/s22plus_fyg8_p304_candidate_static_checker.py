#!/usr/bin/env python3
"""Independently audit the P3.04 fixed-Image 61-module candidate."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile

import build_s22plus_fyg8_p304_candidate as candidate
import s22plus_fyg8_p303_candidate_static_checker as inherited
import s22plus_fyg8_p304_candidate_contract as contract
import s22plus_fyg8_p304_e2_stock_closure as closure
import s22plus_fyg8_p304_overlay_contract as overlay
import s22plus_fyg8_p304_plan_transform as plan
import s22plus_fyg8_p304_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p304_candidate_static_checker_v1"
VERDICT = "PASS_P304_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
TARGET = contract.TARGET
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_CANDIDATE_B = Path("workspace/private/outputs/s22plus_fyg8_p304/candidate-b")
DEFAULT_IMAGE = candidate.DEFAULT_IMAGE
DEFAULT_REPRO_RESULT = candidate.DEFAULT_REPRO_RESULT
DEFAULT_USERSPACE = candidate.DEFAULT_USERSPACE
DEFAULT_BASE_BOOT = candidate.DEFAULT_BASE_BOOT
DEFAULT_VENDOR_RAMDISK = candidate.DEFAULT_VENDOR_RAMDISK
DEFAULT_VENDOR_BOOT = inherited.DEFAULT_VENDOR_BOOT
DEFAULT_LZ4 = candidate.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = candidate.DEFAULT_MAGISKBOOT
DEFAULT_BUILD_A = inherited.DEFAULT_BUILD_A
DEFAULT_BUILD_B = inherited.DEFAULT_BUILD_B
DEFAULT_SOURCE = contract.DEFAULT_SOURCE
DEFAULT_INTENT = contract.DEFAULT_INTENT
DEFAULT_PATCH = contract.DEFAULT_PATCH
DEFAULT_NM = inherited.DEFAULT_NM
DEFAULT_OBJDUMP = inherited.DEFAULT_OBJDUMP
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p304/static-check-result.json")
CheckError = inherited.CheckError
base = inherited.base
ARTIFACT_LIMITS = base.ARTIFACT_LIMITS
stable_read = base.stable_read
repo_root = base.repo_root
resolve = base.resolve


def _expected_userspace_source(exact: dict) -> dict:
    return {
        "userspace_overlay_contract_id": overlay.CONTRACT_ID,
        "parent_overlay_contract_id": overlay.PARENT_OVERLAY_CONTRACT_ID,
        "parent_source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
        "source_receipts": exact["source_receipts"],
        "generated_artifacts": exact["generated_artifacts"],
        "fixed_image": exact["fixed_image"],
        "callsite_audit": exact["callsite_audit"],
        "telemetry": exact["telemetry"],
        "module_delta": exact["module_delta"],
        "verified": True,
    }


def verify_userspace(root: Path, directory: Path, exact: dict, intent_path: Path):
    if directory.is_symlink() or not directory.is_dir():
        raise CheckError("P3.04 userspace directory missing or indirect")
    if {path.name for path in directory.iterdir()} != {
        "init", "s22-e1-child", "userspace-result.json"
    }:
        raise CheckError("P3.04 userspace inventory differs")
    result, result_payload = base.read_json(
        directory / "userspace-result.json", "P3.04 userspace result", 8 * 1024 * 1024
    )
    if overlay.verify_intent(root, intent_path) != exact:
        raise CheckError("P3.04 overlay contract changed")
    if (
        result.get("schema") != userspace.SCHEMA
        or result.get("target") != TARGET
        or result.get("verdict") != userspace.VERDICT
        or result.get("candidate_contract") != exact
        or result.get("source_contract") != _expected_userspace_source(exact)
        or result.get("run_id") != exact["run_id"]
        or result.get("profile") != exact["profile"]
        or result.get("two_build_byte_identical") is not True
        or result.get("callsite_descriptor_a_b_identical") is not True
        or result.get("module_plan_count") != plan.MODULE_PLAN_COUNT
    ):
        raise CheckError("P3.04 userspace result identity differs")
    paths = {"init": directory / "init", "child": directory / "s22-e1-child"}
    payloads = {
        name: base.stable_read(path, f"P3.04 {name}", 1024 * 1024)
        for name, path in paths.items()
    }
    for name, path in paths.items():
        base.require_receipt(base.receipt(payloads[name]), result.get("outputs", {}).get(name), name)
        if path.stat(follow_symlinks=False).st_mode & 0o777 != 0o755:
            raise CheckError(f"P3.04 {name} host mode differs")
    materialized = intent_path.parent / "materialized-sources"
    with userspace.module_count_context():
        module_files = inherited.inherited.parent_userspace._e2_module_files(  # noqa: SLF001
            root, overlay.PARENT_SOURCE_CONTRACT_ID, materialized
        )
    init = payloads["init"]
    child = payloads["child"]
    run_id = bytes.fromhex(exact["run_id"])
    if (
        len(module_files) != plan.MODULE_PLAN_COUNT
        or module_files[-3:] != ("dwc3-msm.ko", plan.MODULE_NAME, "ucsi_glink.ko")
        or init.count(run_id) != 1
        or any(init.count(name.encode("ascii")) != 1 for name in module_files)
        or any(token in init for token in (b"sec_log_buf.ko", b"/dev/mem", b"/dev/block", b"/bin/sh"))
        or init.count(b"/dev/kmsg") != 1
        or init.count(b"/proc/s22_checkpoint") != 1
        or init.count(b"/s22-e1-child") != 1
        or init.count(inherited.inherited.parent_userspace.CHILD_TOKEN) != 1
        or child.count(inherited.inherited.parent_userspace.CHILD_TOKEN) != 1
    ):
        raise CheckError("P3.04 E2 binary closure differs")
    qemu_path = Path(inherited.inherited.parent_userspace.require_tools()["qemu-aarch64"])
    qemu = base.stable_read(qemu_path, "P3.04 qemu-aarch64", 32 * 1024 * 1024)
    with tempfile.TemporaryDirectory(prefix="s22-p304-child-audit-") as temporary:
        staged_qemu = Path(temporary) / "qemu-aarch64"
        staged_child = Path(temporary) / "s22-e1-child"
        staged_qemu.write_bytes(qemu)
        staged_child.write_bytes(child)
        staged_qemu.chmod(0o700)
        staged_child.chmod(0o700)
        child_run = subprocess.run(
            [staged_qemu, staged_child],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
    if (
        child_run.returncode != inherited.inherited.parent_userspace.CHILD_EXIT
        or child_run.stdout != inherited.inherited.parent_userspace.CHILD_TOKEN
        or child_run.stderr
    ):
        raise CheckError("P3.04 child token/exit check failed")
    if result.get("safety") != {
        "host_only": True,
        "kernel_built": False,
        "full_lto_ab_required": False,
        "fixed_p300_image": True,
        "module_binaries_injected": 0,
        "stock_vendor_ramdisk_module_reused": True,
        "boot_image_created": False,
        "candidate_packaged": False,
        "device_contact": False,
        "live_authorized": False,
    }:
        raise CheckError("P3.04 userspace safety contract differs")
    return (
        payloads,
        {
            "result": base.receipt(result_payload),
            "init": base.receipt(init),
            "child": base.receipt(child),
            "two_build_byte_identical": True,
            "verified": True,
        },
        base.receipt(qemu),
    )


def rootfs_entrypoint_context(_closure_api, exact, payloads):  # noqa: ANN001, ANN201
    return inherited.rootfs_entrypoint_context(
        inherited._P303_STOCK_CLOSURE_VIEW, exact, payloads  # noqa: SLF001
    )


def _configure() -> None:
    inherited._configure()
    candidate._configure()
    inherited.candidate = candidate
    inherited.contract = contract
    inherited.overlay = overlay
    inherited.userspace = userspace
    inherited.SCHEMA = SCHEMA
    inherited.VERDICT = VERDICT
    inherited.TARGET = TARGET
    inherited.DEFAULT_CANDIDATE = DEFAULT_CANDIDATE
    inherited.DEFAULT_CANDIDATE_B = DEFAULT_CANDIDATE_B
    inherited.DEFAULT_USERSPACE = DEFAULT_USERSPACE
    inherited.DEFAULT_SOURCE = DEFAULT_SOURCE
    inherited.DEFAULT_INTENT = DEFAULT_INTENT
    inherited.DEFAULT_PATCH = DEFAULT_PATCH
    inherited.DEFAULT_OUT = DEFAULT_OUT
    base.candidate = inherited.inherited._CANDIDATE_STATIC_VIEW  # noqa: SLF001
    base.contract = contract
    base.p286_closure = closure
    base.userspace = userspace
    base.rootfs_entrypoint_context = rootfs_entrypoint_context
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT
    base.TARGET = TARGET
    base.DEFAULT_CANDIDATE = DEFAULT_CANDIDATE
    base.DEFAULT_CANDIDATE_B = DEFAULT_CANDIDATE_B
    base.DEFAULT_IMAGE = DEFAULT_IMAGE
    base.DEFAULT_REPRO_RESULT = DEFAULT_REPRO_RESULT
    base.DEFAULT_USERSPACE = DEFAULT_USERSPACE
    base.DEFAULT_BASE_BOOT = DEFAULT_BASE_BOOT
    base.DEFAULT_VENDOR_RAMDISK = DEFAULT_VENDOR_RAMDISK
    base.DEFAULT_VENDOR_BOOT = DEFAULT_VENDOR_BOOT
    base.DEFAULT_LZ4 = DEFAULT_LZ4
    base.DEFAULT_MAGISKBOOT = DEFAULT_MAGISKBOOT
    base.DEFAULT_BUILD_A = DEFAULT_BUILD_A
    base.DEFAULT_BUILD_B = DEFAULT_BUILD_B
    base.DEFAULT_SOURCE = DEFAULT_SOURCE
    base.DEFAULT_INTENT = DEFAULT_INTENT
    base.DEFAULT_PATCH = DEFAULT_PATCH
    base.DEFAULT_NM = DEFAULT_NM
    base.DEFAULT_OBJDUMP = DEFAULT_OBJDUMP
    base.DEFAULT_OUT = DEFAULT_OUT
    base.verify_repro = inherited.inherited.verify_repro
    base.verify_userspace = verify_userspace


def audit(args):  # noqa: ANN001, ANN201
    _configure()
    result = base.audit(args)
    root = base.repo_root()
    exact = overlay.verify_intent(root, base.resolve(root, args.intent))
    proved = inherited.callsite_audit.audit(
        root, Path(inherited.spec.MODULE_PATH), args.objdump, "readelf"
    )
    if proved != exact["callsite_audit"]:
        raise CheckError("P3.04 inherited post-BL callsite audit changed")
    result["p303_callsite_audit"] = proved
    result["p303_offset_probe_rule"] = {
        "p300_epilogue_rejection_preserved": True,
        "immediate_post_bl_only": True,
        "w0_immediately_consumed": True,
        "fixed_module_receipt_shared_by_candidate_a_b": True,
        "hit_zero_distinct_from_rc_zero": True,
        "verified": True,
    }
    return result


def parse_args(argv: list[str] | None = None):
    _configure()
    return base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure()
    try:
        args = base.parse_args(argv)
        result = audit(args)
        encoded = json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode("ascii") + b"\n"
        base.durable_create(base.resolve(base.repo_root(), args.out), encoded)
    except (
        CheckError,
        candidate.BuildError,
        base.carrier.BuildError,
        base.boot_verify.BootVerifyError,
        inherited.inherited.repro.CheckError,
        inherited.inherited.postbuild_audit.AuditError,
        inherited.callsite_audit.AuditError,
        contract.ContractError,
        contract.intent.IntentError,
        overlay.OverlayContractError,
        userspace.BuildError,
        base.e1_static.CheckError,
        base.e2_closure.ClosureError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
