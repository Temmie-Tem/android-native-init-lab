#!/usr/bin/env python3
"""Independently audit one P3.11 fixed-P3.10-Image candidate."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Iterator

import build_s22plus_fyg8_p311_candidate as candidate
import s22plus_fyg8_p286_candidate_static_checker as base
import s22plus_fyg8_p310_build_repro_check as repro
import s22plus_fyg8_p310_candidate_static_checker as p310_static
import s22plus_fyg8_p310_userspace_build as parent_userspace
import s22plus_fyg8_p311_candidate_contract as contract
import s22plus_fyg8_p311_e2_stock_closure as closure
import s22plus_fyg8_p311_overlay_contract as overlay
import s22plus_fyg8_p311_runtime_fixture as runtime_fixture
import s22plus_fyg8_p311_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p311_candidate_static_checker_v1"
VERDICT = "PASS_P311_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
TARGET = contract.TARGET
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_CANDIDATE_B = Path("workspace/private/outputs/s22plus_fyg8_p311/candidate-b")
DEFAULT_IMAGE = candidate.DEFAULT_IMAGE
DEFAULT_REPRO_RESULT = candidate.DEFAULT_REPRO_RESULT
DEFAULT_USERSPACE = candidate.DEFAULT_USERSPACE
DEFAULT_BASE_BOOT = candidate.DEFAULT_BASE_BOOT
DEFAULT_VENDOR_RAMDISK = candidate.DEFAULT_VENDOR_RAMDISK
DEFAULT_VENDOR_BOOT = base.DEFAULT_VENDOR_BOOT
DEFAULT_LZ4 = candidate.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = candidate.DEFAULT_MAGISKBOOT
DEFAULT_BUILD_A = p310_static.DEFAULT_BUILD_A
DEFAULT_BUILD_B = p310_static.DEFAULT_BUILD_B
DEFAULT_SOURCE = contract.DEFAULT_SOURCE
DEFAULT_INTENT = contract.DEFAULT_INTENT
DEFAULT_PATCH = contract.DEFAULT_PATCH
DEFAULT_NM = p310_static.DEFAULT_NM
DEFAULT_OBJDUMP = p310_static.DEFAULT_OBJDUMP
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p311/static-check-result.json")
CheckError = base.CheckError


def artifact_safety(exact):  # noqa: ANN001, ANN201
    candidate._configure()  # noqa: SLF001
    return candidate.artifact_safety(exact)


class _CandidateStaticView:
    artifact_safety = staticmethod(artifact_safety)

    def __getattr__(self, name: str):
        return getattr(candidate, name)


_CANDIDATE_STATIC_VIEW = _CandidateStaticView()


def _expected_userspace_source(exact: dict) -> dict:
    return userspace._source_contract(exact)  # noqa: SLF001


def verify_userspace(root: Path, directory: Path, exact: dict, intent_path: Path):
    if directory.is_symlink() or not directory.is_dir():
        raise CheckError("P3.11 userspace directory missing or indirect")
    if {path.name for path in directory.iterdir()} != {
        "init", "s22-e1-child", "userspace-result.json"
    }:
        raise CheckError("P3.11 userspace inventory differs")
    result, result_payload = base.read_json(
        directory / "userspace-result.json", "P3.11 userspace result", 8 * 1024 * 1024
    )
    if overlay.verify_intent(root, intent_path) != exact:
        raise CheckError("P3.11 overlay contract changed")
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
        or result.get("module_plan_count") != 61
        or result.get("telemetry") != exact["telemetry"]
        or result.get("observer") != exact["observer"]
    ):
        raise CheckError("P3.11 userspace result identity differs")
    paths = {"init": directory / "init", "child": directory / "s22-e1-child"}
    payloads = {
        name: base.stable_read(path, f"P3.11 {name}", 1024 * 1024)
        for name, path in paths.items()
    }
    for name, path in paths.items():
        base.require_receipt(base.receipt(payloads[name]), result.get("outputs", {}).get(name), name)
        if path.stat(follow_symlinks=False).st_mode & 0o777 != 0o755:
            raise CheckError(f"P3.11 {name} host mode differs")
    parent_userspace._configure()  # noqa: SLF001
    module_files = parent_userspace._e2_module_files(  # noqa: SLF001
        root,
        overlay.PARENT_SOURCE_CONTRACT_ID,
        intent_path.parent / "materialized-sources",
    )
    init = payloads["init"]
    child = payloads["child"]
    run_id = bytes.fromhex(exact["run_id"])
    if (
        len(module_files) != 61
        or module_files[-3:] != ("dwc3-msm.ko", "usb_notifier_qcom.ko", "ucsi_glink.ko")
        or init.count(run_id) != 1
        or any(init.count(name.encode("ascii")) != 1 for name in module_files)
        or any(token in init for token in (b"sec_log_buf.ko", b"/dev/mem", b"/dev/block", b"/bin/sh"))
        or init.count(b"/dev/kmsg") != 1
        or init.count(b"/sys/module/eud/parameters/enable") != 1
        or init.count(b"/proc/s22_checkpoint") != 1
        or init.count(b"/s22-e1-child") != 1
        or init.count(parent_userspace.base.CHILD_TOKEN) != 1
        or child.count(parent_userspace.base.CHILD_TOKEN) != 1
    ):
        raise CheckError("P3.11 E2 binary closure differs")
    qemu_path = Path(parent_userspace.base.require_tools()["qemu-aarch64"])
    qemu = base.stable_read(qemu_path, "P3.11 qemu-aarch64", 32 * 1024 * 1024)
    with tempfile.TemporaryDirectory(prefix="s22-p311-child-audit-") as temporary:
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
        child_run.returncode != parent_userspace.base.CHILD_EXIT
        or child_run.stdout != parent_userspace.base.CHILD_TOKEN
        or child_run.stderr
    ):
        raise CheckError("P3.11 child token/exit check failed")
    if result.get("safety") != {
        "host_only": True,
        "kernel_built": False,
        "full_lto_ab_required": False,
        "fixed_p310_image": True,
        "module_binaries_injected": 0,
        "stock_vendor_ramdisk_module_reused": True,
        "boot_image_created": False,
        "candidate_packaged": False,
        "device_contact": False,
        "live_authorized": False,
    }:
        raise CheckError("P3.11 userspace safety contract differs")
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


def verify_repro(root: Path, args, exact):  # noqa: ANN001, ANN201
    value, payload = base.read_json(
        base.resolve(root, args.repro_result),
        "P3.11 fixed P3.10 independent closure",
        16 * 1024 * 1024,
    )
    parent_exact = exact.get("parent_candidate_contract")
    if (
        base.resolve(root, args.repro_result) != root / overlay.PARENT_REPRO_RESULT
        or value.get("schema") != p310_static.SCHEMA
        or value.get("verdict") != p310_static.VERDICT
        or value.get("candidate_contract") != parent_exact
        or value.get("build_repro", {}).get("image") != overlay.EXPECTED_IMAGE
        or value.get("candidate", {}).get("verified") is not True
        or value.get("safety", {}).get("host_only") is not True
    ):
        raise CheckError("P3.11 fixed P3.10 independent closure differs")
    return {
        "build_a": {"artifacts": {"Image": overlay.EXPECTED_IMAGE}},
        "fixed_parent_closure": base.receipt(payload),
        "verified": True,
    }, base.receipt(payload)


@contextmanager
def rootfs_entrypoint_context(
    _closure_api, _exact, payloads  # noqa: ANN001
) -> Iterator[None]:
    try:
        entrypoints = {
            "init": base.e1_static.inspect_static_elf(
                payloads["init"], "P3.11 exact /init"
            )["entrypoint"],
            "child": base.e1_static.inspect_static_elf(
                payloads["child"], "P3.11 exact child"
            )["entrypoint"],
        }
    except (KeyError, base.e1_static.CheckError) as exc:
        raise CheckError("P3.11 exact userspace entrypoint is invalid") from exc
    if any(
        isinstance(value, bool) or not isinstance(value, int)
        for value in entrypoints.values()
    ):
        raise CheckError("P3.11 exact userspace entrypoint is malformed")
    entrypoint_api = closure.parent.parent.p286.p282.p280
    with entrypoint_api._expected_entrypoints(entrypoints):  # noqa: SLF001
        with closure.exact_init_authority(payloads["init"]):
            yield


def _configure() -> None:
    candidate._configure()  # noqa: SLF001
    contract._configure()  # noqa: SLF001
    p310_static._configure()  # noqa: SLF001
    base.candidate = _CANDIDATE_STATIC_VIEW
    base.repro = repro
    base.contract = contract
    base.p286_closure = closure
    base.rootfs_entrypoint_context = rootfs_entrypoint_context
    base.userspace = userspace
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
    base.verify_repro = verify_repro
    base.verify_userspace = verify_userspace


def __getattr__(name: str):
    _configure()
    return getattr(base, name)


def audit(args):  # noqa: ANN001, ANN201
    _configure()
    result = base.audit(args)
    root = base.repo_root()
    exact = overlay.verify_intent(root, base.resolve(root, args.intent))
    fixture = runtime_fixture.audit(root)
    if fixture.get("verified") is not True:
        raise CheckError("P3.11 runtime fixtures differ")
    result.update({
        "p311_callsite_audit": exact["callsite_audit"],
        "p311_delayed_arm_qemu": exact["delayed_arm_qemu"],
        "p311_tracefs_abi": exact["tracefs_abi"],
        "p311_cross_gate_audit": exact["cross_gate_audit"],
        "p311_runtime_fixture": fixture,
        "p311_telemetry": exact["telemetry"],
        "p311_observer": exact["observer"],
    })
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
        contract.ContractError,
        contract.intent.IntentError,
        overlay.OverlayContractError,
        userspace.BuildError,
        base.e1_static.CheckError,
        closure.ClosureError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
