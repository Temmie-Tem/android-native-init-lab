#!/usr/bin/env python3
"""Independently audit one fixed-Image P3.03 HS-PHY observer candidate."""

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Iterator

import build_s22plus_fyg8_p303_candidate as candidate
import s22plus_fyg8_p301_candidate_static_checker as inherited
import s22plus_fyg8_p303_callsite_audit as callsite_audit
import s22plus_fyg8_p303_candidate_contract as contract
import s22plus_fyg8_p303_overlay_contract as overlay
import s22plus_fyg8_p303_telemetry_spec as spec
import s22plus_fyg8_p303_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p303_candidate_static_checker_v1"
VERDICT = "PASS_P303_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
TARGET = contract.TARGET
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_CANDIDATE_B = Path(
    "workspace/private/outputs/s22plus_fyg8_p303/candidate-b"
)
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
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p303/static-check-result.json"
)
CheckError = inherited.CheckError
base = inherited.base


class _P303StockClosureView:
    expected_init: bytes | None = None

    def __getattr__(self, name: str):
        return getattr(inherited.p300_closure, name)

    @contextmanager
    def _p286_authority_paths(self) -> Iterator[None]:
        expected = self.expected_init
        if expected is None:
            raise CheckError("P3.03 exact init authority binding is absent")
        closure = inherited.p300_closure
        required = frozenset({*closure.REQUIRED_ABSOLUTE_PATH_STRINGS, "/dev/kmsg"})
        allowed = frozenset({*closure.ALLOWED_ABSOLUTE_PATH_STRINGS, "/dev/kmsg"})
        printable = closure.p286.p282.p280.isolated_p260._printable_strings(  # noqa: SLF001
            expected
        )
        paths = closure.p286.p282._absolute_path_candidates(printable)  # noqa: SLF001
        incidental = paths - allowed
        if (
            required - paths
            or incidental != {'/E9"'}
            or any(expected.count(value.encode("ascii")) != 1 for value in incidental)
            or expected.count(b"/dev/kmsg") != 1
        ):
            raise CheckError("P3.03 exact init authority path set differs")
        scrubbed = expected
        for value in sorted(incidental):
            encoded = value.encode("ascii")
            scrubbed = scrubbed.replace(encoded, b"\0" * len(encoded))

        def validate(data: bytes) -> None:
            if data != expected:
                raise closure.ClosureError(
                    "P3.03 effective init differs from source-bound userspace"
                )
            previous_required = closure.REQUIRED_ABSOLUTE_PATH_STRINGS
            previous_allowed = closure.ALLOWED_ABSOLUTE_PATH_STRINGS
            closure.REQUIRED_ABSOLUTE_PATH_STRINGS = required
            closure.ALLOWED_ABSOLUTE_PATH_STRINGS = allowed
            try:
                with closure._p300_authority_globals():  # noqa: SLF001
                    closure._P282_VALIDATE_AUTHORITY_STRINGS(scrubbed)  # noqa: SLF001
            finally:
                closure.REQUIRED_ABSOLUTE_PATH_STRINGS = previous_required
                closure.ALLOWED_ABSOLUTE_PATH_STRINGS = previous_allowed

        previous = closure.p286.p282._validate_p282_authority_strings  # noqa: SLF001
        closure.p286.p282._validate_p282_authority_strings = validate  # noqa: SLF001
        try:
            yield
        finally:
            closure.p286.p282._validate_p282_authority_strings = previous  # noqa: SLF001


_P303_STOCK_CLOSURE_VIEW = _P303StockClosureView()


@contextmanager
def rootfs_entrypoint_context(
    closure_api, exact_contract: dict, userspace_payloads: dict[str, bytes]
) -> Iterator[None]:  # noqa: ANN001
    previous = _P303_STOCK_CLOSURE_VIEW.expected_init
    _P303_STOCK_CLOSURE_VIEW.expected_init = userspace_payloads["init"]
    try:
        with inherited._BASE_ROOTFS_ENTRYPOINT_CONTEXT(  # noqa: SLF001
            closure_api, exact_contract, userspace_payloads
        ):
            yield
    finally:
        _P303_STOCK_CLOSURE_VIEW.expected_init = previous


def _expected_userspace_source(exact_contract: dict) -> dict:
    return {
        "userspace_overlay_contract_id": overlay.CONTRACT_ID,
        "parent_overlay_contract_id": overlay.PARENT_OVERLAY_CONTRACT_ID,
        "parent_source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
        "source_receipts": exact_contract["source_receipts"],
        "generated_artifacts": exact_contract["generated_artifacts"],
        "fixed_image": exact_contract["fixed_image"],
        "callsite_audit": exact_contract["callsite_audit"],
        "telemetry": exact_contract["telemetry"],
        "verified": True,
    }


def verify_userspace(
    root: Path,
    directory: Path,
    exact_contract: dict,
    intent_path: Path,
):
    if directory.is_symlink() or not directory.is_dir():
        raise CheckError("P3.03 userspace directory missing or indirect")
    if {path.name for path in directory.iterdir()} != {
        "init",
        "s22-e1-child",
        "userspace-result.json",
    }:
        raise CheckError("P3.03 userspace inventory mismatch")
    result, result_payload = base.read_json(
        directory / "userspace-result.json",
        "P3.03 userspace result",
        8 * 1024 * 1024,
    )
    fresh_contract = overlay.verify_intent(root, intent_path)
    if fresh_contract != exact_contract:
        raise CheckError("P3.03 userspace overlay contract changed")
    if (
        result.get("schema") != userspace.SCHEMA
        or result.get("target") != TARGET
        or result.get("verdict") != userspace.VERDICT
        or result.get("candidate_contract") != exact_contract
        or result.get("source_contract") != _expected_userspace_source(exact_contract)
        or result.get("run_id") != exact_contract["run_id"]
        or result.get("profile") != exact_contract["profile"]
        or result.get("two_build_byte_identical") is not True
        or result.get("callsite_descriptor_a_b_identical") is not True
    ):
        raise CheckError("P3.03 userspace result identity mismatch")

    paths = {"init": directory / "init", "child": directory / "s22-e1-child"}
    payloads = {
        name: base.stable_read(path, f"P3.03 {name}", 1024 * 1024)
        for name, path in paths.items()
    }
    for name, path in paths.items():
        base.require_receipt(
            base.receipt(payloads[name]), result.get("outputs", {}).get(name), name
        )
        if path.stat(follow_symlinks=False).st_mode & 0o777 != 0o755:
            raise CheckError(f"P3.03 {name} host mode mismatch")

    materialized = intent_path.parent / "materialized-sources"
    module_files = inherited.parent_userspace._e2_module_files(  # noqa: SLF001
        root,
        overlay.PARENT_SOURCE_CONTRACT_ID,
        materialized,
    )
    init = payloads["init"]
    child = payloads["child"]
    run_id = bytes.fromhex(exact_contract["run_id"])
    if (
        init.count(run_id) != 1
        or any(init.count(name.encode("ascii")) != 1 for name in module_files)
        or any(token in init for token in (b"sec_log_buf.ko", b"/dev/mem", b"/dev/block", b"/bin/sh"))
        or init.count(b"/dev/kmsg") != 1
        or init.count(b"/proc/s22_checkpoint") != 1
        or init.count(b"/s22-e1-child") != 1
        or init.count(inherited.parent_userspace.CHILD_TOKEN) != 1
        or child.count(inherited.parent_userspace.CHILD_TOKEN) != 1
    ):
        raise CheckError("P3.03 E2 binary closure mismatch")

    qemu_path = Path(inherited.parent_userspace.require_tools()["qemu-aarch64"])
    qemu = base.stable_read(qemu_path, "P3.03 qemu-aarch64", 32 * 1024 * 1024)
    with tempfile.TemporaryDirectory(prefix="s22-p303-child-audit-") as temporary:
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
        child_run.returncode != inherited.parent_userspace.CHILD_EXIT
        or child_run.stdout != inherited.parent_userspace.CHILD_TOKEN
        or child_run.stderr
    ):
        raise CheckError("P3.03 independent child token/exit check failed")

    if result.get("safety") != {
        "host_only": True,
        "kernel_built": False,
        "full_lto_ab_required": False,
        "fixed_p300_image": True,
        "module_binaries_injected": 0,
        "boot_image_created": False,
        "candidate_packaged": False,
        "device_contact": False,
        "live_authorized": False,
    }:
        raise CheckError("P3.03 userspace safety contract mismatch")
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


def _configure() -> None:
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
    inherited.DEFAULT_IMAGE = DEFAULT_IMAGE
    inherited.DEFAULT_REPRO_RESULT = DEFAULT_REPRO_RESULT
    inherited.DEFAULT_USERSPACE = DEFAULT_USERSPACE
    inherited.DEFAULT_SOURCE = DEFAULT_SOURCE
    inherited.DEFAULT_INTENT = DEFAULT_INTENT
    inherited.DEFAULT_PATCH = DEFAULT_PATCH
    inherited.DEFAULT_OUT = DEFAULT_OUT
    base.candidate = inherited._CANDIDATE_STATIC_VIEW  # noqa: SLF001
    base.repro = inherited.repro
    base.contract = contract
    base.p286_closure = _P303_STOCK_CLOSURE_VIEW
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
    base.verify_repro = inherited.verify_repro
    base.verify_userspace = verify_userspace


def __getattr__(name: str):
    _configure()
    return getattr(base, name)


def audit(args):  # noqa: ANN001, ANN201
    _configure()
    result = base.audit(args)
    root = base.repo_root()
    exact = overlay.verify_intent(root, base.resolve(root, args.intent))
    proved = callsite_audit.audit(
        root, Path(spec.MODULE_PATH), args.objdump, "readelf"
    )
    if proved != exact["callsite_audit"]:
        raise CheckError("P3.03 exact post-BL callsite audit changed")
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
        encoded = (
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode(
                "ascii"
            )
            + b"\n"
        )
        base.durable_create(base.resolve(base.repo_root(), args.out), encoded)
    except (
        CheckError,
        candidate.BuildError,
        base.carrier.BuildError,
        base.boot_verify.BootVerifyError,
        inherited.repro.CheckError,
        inherited.postbuild_audit.AuditError,
        callsite_audit.AuditError,
        contract.ContractError,
        contract.intent.IntentError,
        overlay.OverlayContractError,
        userspace.BuildError,
        base.e1_static.CheckError,
        base.e2_closure.ClosureError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}
            )
        )
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
