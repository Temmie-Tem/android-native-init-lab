#!/usr/bin/env python3
"""Independently audit one fixed-Image P3.01 boot-only candidate."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Iterator

import build_s22plus_fyg8_p301_candidate as candidate
import s22plus_fyg8_p286_candidate_static_checker as base
import s22plus_fyg8_p300_build_repro_check as repro
import s22plus_fyg8_p300_e2_stock_closure as p300_closure
import s22plus_fyg8_p300_postbuild_linked_audit as postbuild_audit
import s22plus_fyg8_p300_userspace_build as parent_userspace
import s22plus_fyg8_p301_candidate_contract as contract
import s22plus_fyg8_p301_overlay_contract as overlay
import s22plus_fyg8_p301_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p301_candidate_static_checker_v1"
VERDICT = "PASS_P301_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
TARGET = contract.TARGET
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_CANDIDATE_B = Path(
    "workspace/private/outputs/s22plus_fyg8_p301/candidate-b"
)
DEFAULT_IMAGE = candidate.DEFAULT_IMAGE
DEFAULT_REPRO_RESULT = candidate.DEFAULT_REPRO_RESULT
DEFAULT_USERSPACE = candidate.DEFAULT_USERSPACE
DEFAULT_BASE_BOOT = candidate.DEFAULT_BASE_BOOT
DEFAULT_VENDOR_RAMDISK = candidate.DEFAULT_VENDOR_RAMDISK
DEFAULT_VENDOR_BOOT = base.DEFAULT_VENDOR_BOOT
DEFAULT_LZ4 = candidate.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = candidate.DEFAULT_MAGISKBOOT
DEFAULT_BUILD_A = overlay.PARENT_REPRO_RESULT.parent / "artifacts-a"
DEFAULT_BUILD_B = overlay.PARENT_REPRO_RESULT.parent / "artifacts-b"
PARENT_REPRO_RESULT_RECEIPT = {
    "size": 80509,
    "sha256": "8761729443445250dee88ab2b661a1dff3c868443ed276129f7275c4a3e60226",
}
PARENT_QUALIFICATION = Path(
    "workspace/private/outputs/s22plus_fyg8_p300_pre_lto/qualification.json"
)
PARENT_QUALIFICATION_RECEIPT = {
    "size": 125025,
    "sha256": "378d6e5fe66357cb4ce2f705bd9332e3a9858e2599e0b0a60bdcdf56fed2857f",
}
DEFAULT_SOURCE = contract.DEFAULT_SOURCE
DEFAULT_INTENT = contract.DEFAULT_INTENT
DEFAULT_PATCH = contract.DEFAULT_PATCH
DEFAULT_NM = repro.DEFAULT_NM
DEFAULT_OBJDUMP = repro.DEFAULT_OBJDUMP
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p301/static-check-result.json"
)
CheckError = base.CheckError
_BASE_ROOTFS_ENTRYPOINT_CONTEXT = base.rootfs_entrypoint_context


def artifact_safety(exact_contract):  # noqa: ANN001, ANN201
    candidate._configure()
    return candidate.artifact_safety(exact_contract)


class _CandidateStaticView:
    artifact_safety = staticmethod(artifact_safety)

    def __getattr__(self, name: str):
        return getattr(candidate, name)


_CANDIDATE_STATIC_VIEW = _CandidateStaticView()


class _P301StockClosureView:
    expected_init: bytes | None = None

    def __getattr__(self, name: str):
        return getattr(p300_closure, name)

    @contextmanager
    def _p286_authority_paths(self) -> Iterator[None]:
        expected = self.expected_init
        if expected is None:
            raise CheckError("P3.01 exact init authority binding is absent")
        printable = p300_closure.p286.p282.p280.isolated_p260._printable_strings(  # noqa: SLF001
            expected
        )
        paths = p300_closure.p286.p282._absolute_path_candidates(printable)  # noqa: SLF001
        incidental = paths - p300_closure.ALLOWED_ABSOLUTE_PATH_STRINGS
        if (
            p300_closure.REQUIRED_ABSOLUTE_PATH_STRINGS - paths
            or incidental != {'/E9"', "/R9@"}
            or any(expected.count(value.encode("ascii")) != 1 for value in incidental)
        ):
            raise CheckError("P3.01 exact init authority path set differs")
        scrubbed = expected
        for value in sorted(incidental):
            encoded = value.encode("ascii")
            scrubbed = scrubbed.replace(encoded, b"\0" * len(encoded))

        def validate(data: bytes) -> None:
            if data != expected:
                raise p300_closure.ClosureError(
                    "P3.01 effective init differs from source-bound userspace"
                )
            with p300_closure._p300_authority_globals():  # noqa: SLF001
                p300_closure._P282_VALIDATE_AUTHORITY_STRINGS(scrubbed)  # noqa: SLF001

        previous = p300_closure.p286.p282._validate_p282_authority_strings  # noqa: SLF001
        p300_closure.p286.p282._validate_p282_authority_strings = validate  # noqa: SLF001
        try:
            yield
        finally:
            p300_closure.p286.p282._validate_p282_authority_strings = previous  # noqa: SLF001


_P301_STOCK_CLOSURE_VIEW = _P301StockClosureView()


@contextmanager
def rootfs_entrypoint_context(
    closure_api, exact_contract: dict, userspace_payloads: dict[str, bytes]
) -> Iterator[None]:  # noqa: ANN001
    previous = _P301_STOCK_CLOSURE_VIEW.expected_init
    _P301_STOCK_CLOSURE_VIEW.expected_init = userspace_payloads["init"]
    try:
        with _BASE_ROOTFS_ENTRYPOINT_CONTEXT(
            closure_api, exact_contract, userspace_payloads
        ):
            yield
    finally:
        _P301_STOCK_CLOSURE_VIEW.expected_init = previous


def _expected_userspace_source(exact_contract: dict) -> dict:
    return {
        "userspace_overlay_contract_id": overlay.CONTRACT_ID,
        "parent_source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
        "source_receipts": exact_contract["source_receipts"],
        "generated_artifacts": exact_contract["generated_artifacts"],
        "fixed_image": exact_contract["fixed_image"],
        "verified": True,
    }


def verify_userspace(
    root: Path,
    directory: Path,
    exact_contract: dict,
    intent_path: Path,
):
    if directory.is_symlink() or not directory.is_dir():
        raise CheckError("P3.01 userspace directory missing or indirect")
    if {path.name for path in directory.iterdir()} != {
        "init",
        "s22-e1-child",
        "userspace-result.json",
    }:
        raise CheckError("P3.01 userspace inventory mismatch")
    result, result_payload = base.read_json(
        directory / "userspace-result.json",
        "P3.01 userspace result",
        8 * 1024 * 1024,
    )
    fresh_contract = overlay.verify_intent(root, intent_path)
    if fresh_contract != exact_contract:
        raise CheckError("P3.01 userspace overlay contract changed")
    if (
        result.get("schema") != userspace.SCHEMA
        or result.get("target") != TARGET
        or result.get("verdict") != userspace.VERDICT
        or result.get("candidate_contract") != exact_contract
        or result.get("source_contract")
        != _expected_userspace_source(exact_contract)
        or result.get("run_id") != exact_contract["run_id"]
        or result.get("profile") != exact_contract["profile"]
        or result.get("two_build_byte_identical") is not True
    ):
        raise CheckError("P3.01 userspace result identity mismatch")

    paths = {"init": directory / "init", "child": directory / "s22-e1-child"}
    payloads = {
        name: base.stable_read(path, f"P3.01 {name}", 1024 * 1024)
        for name, path in paths.items()
    }
    for name, path in paths.items():
        base.require_receipt(
            base.receipt(payloads[name]), result.get("outputs", {}).get(name), name
        )
        if path.stat(follow_symlinks=False).st_mode & 0o777 != 0o755:
            raise CheckError(f"P3.01 {name} host mode mismatch")

    materialized = intent_path.parent / "materialized-sources"
    module_files = parent_userspace._e2_module_files(  # noqa: SLF001
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
        or init.count(b"/proc/s22_checkpoint") != 1
        or init.count(b"/s22-e1-child") != 1
        or init.count(parent_userspace.CHILD_TOKEN) != 1
        or child.count(parent_userspace.CHILD_TOKEN) != 1
    ):
        raise CheckError("P3.01 E2 binary closure mismatch")

    qemu_path = Path(parent_userspace.require_tools()["qemu-aarch64"])
    qemu = base.stable_read(qemu_path, "P3.01 qemu-aarch64", 32 * 1024 * 1024)
    with tempfile.TemporaryDirectory(prefix="s22-p301-child-audit-") as temporary:
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
        child_run.returncode != parent_userspace.CHILD_EXIT
        or child_run.stdout != parent_userspace.CHILD_TOKEN
        or child_run.stderr
    ):
        raise CheckError("P3.01 independent child token/exit check failed")

    if result.get("safety") != {
        "host_only": True,
        "kernel_built": False,
        "fixed_p300_image": True,
        "boot_image_created": False,
        "candidate_packaged": False,
        "device_contact": False,
        "live_authorized": False,
    }:
        raise CheckError("P3.01 userspace safety contract mismatch")
    closure = {
        "result": base.receipt(result_payload),
        "init": base.receipt(init),
        "child": base.receipt(child),
        "two_build_byte_identical": True,
        "verified": True,
    }
    return payloads, closure, base.receipt(qemu)


def _exact_parent_path(
    root: Path, supplied: Path, expected: Path, label: str
) -> Path:
    actual = base.resolve(root, supplied)
    pinned = base.resolve(root, expected)
    if actual != pinned:
        raise CheckError(f"P3.01 fixed P3.00 {label} path differs")
    return actual


def _fixed_build_directories(root: Path, args) -> dict[str, Path]:  # noqa: ANN001
    directories = {
        "build_a": _exact_parent_path(
            root, args.build_a, DEFAULT_BUILD_A, "build A"
        ),
        "build_b": _exact_parent_path(
            root, args.build_b, DEFAULT_BUILD_B, "build B"
        ),
    }
    for label, directory in directories.items():
        if directory.is_symlink() or not directory.is_dir():
            raise CheckError(
                f"P3.01 fixed P3.00 {label} directory is indirect or missing"
            )
    if (
        directories["build_a"] == directories["build_b"]
        or directories["build_a"].samefile(directories["build_b"])
    ):
        raise CheckError("P3.01 fixed P3.00 A/B build directories are not distinct")
    return directories


def _require_distinct_artifact_inodes(
    directories: dict[str, Path], names: set[str]
) -> None:
    for name in sorted(names):
        if (directories["build_a"] / name).samefile(
            directories["build_b"] / name
        ):
            raise CheckError(
                f"P3.01 fixed P3.00 A/B {name} artifacts share one inode"
            )


def verify_repro(root: Path, args, exact_contract):  # noqa: ANN001, ANN201
    result_path = _exact_parent_path(
        root,
        args.repro_result,
        overlay.PARENT_REPRO_RESULT,
        "reproducibility result",
    )
    result, payload = base.read_json(
        result_path,
        "P3.01 fixed P3.00 reproducibility result",
        16 * 1024 * 1024,
    )
    if base.receipt(payload) != PARENT_REPRO_RESULT_RECEIPT:
        raise CheckError("P3.01 fixed P3.00 reproducibility result bytes differ")
    qualification_path = _exact_parent_path(
        root,
        PARENT_QUALIFICATION,
        PARENT_QUALIFICATION,
        "pre-LTO qualification",
    )
    qualification_payload = base.stable_read(
        qualification_path,
        "P3.01 fixed P3.00 pre-LTO qualification",
        16 * 1024 * 1024,
    )
    if base.receipt(qualification_payload) != PARENT_QUALIFICATION_RECEIPT:
        raise CheckError("P3.01 fixed P3.00 pre-LTO qualification bytes differ")
    check_args = argparse.Namespace(
        build_a=DEFAULT_BUILD_A,
        build_b=DEFAULT_BUILD_B,
        source=overlay.PARENT_SOURCE,
        intent=overlay.PARENT_INTENT,
        patch=overlay.PARENT_PATCH,
        nm=args.nm,
        objdump=args.objdump,
    )
    parent_contract = exact_contract.get("parent_candidate_contract")
    if not isinstance(parent_contract, dict):
        raise CheckError("P3.01 fixed P3.00 parent candidate contract differs")
    qualification = result.get("pre_lto_qualification", {})
    qualification_receipt = qualification.get("qualification", {})
    linked = result.get("linked_audit", {})
    expected_equal = set(repro.ARTIFACT_LIMITS) - {"build-result.json"}
    if (
        result.get("schema") != repro.SCHEMA
        or result.get("target") != TARGET
        or result.get("verdict") != repro.VERDICT
        or result.get("candidate_contract") != parent_contract
        or result.get("byte_identical_artifacts")
        != {name: True for name in expected_equal}
        or linked.get("verified") is not True
        or linked.get("audit_adapter")
        != "s22plus-fyg8-p300-linked-audit-v1"
        or linked.get("postbuild_audit", {}).get("verified") is not True
        or qualification.get("verified") is not True
        or qualification.get("source_contract_id")
        != overlay.PARENT_SOURCE_CONTRACT_ID
        or qualification.get("run_id") != parent_contract.get("run_id")
        or qualification.get("qualification_repo_path")
        != PARENT_QUALIFICATION.as_posix()
        or qualification_receipt
        != {
            "path": str(qualification_path),
            **PARENT_QUALIFICATION_RECEIPT,
        }
    ):
        raise CheckError("P3.01 fixed P3.00 reproducibility identity differs")
    directories = _fixed_build_directories(root, args)
    build_payloads: dict[str, dict[str, bytes]] = {}
    for label, directory in directories.items():
        build_result = result.get(label, {})
        if (
            build_result.get("directory") != str(directory)
            or build_result.get("verified") is not True
            or build_result.get("run_id") != parent_contract.get("run_id")
            or build_result.get("pre_lto_qualification") != qualification
        ):
            raise CheckError(f"P3.01 fixed P3.00 {label} header differs")
        expected = result.get(label, {}).get("artifacts")
        if not isinstance(expected, dict) or set(expected) != set(repro.ARTIFACT_LIMITS):
            raise CheckError(f"P3.01 fixed P3.00 {label} receipt set differs")
        build_payloads[label] = {
            name: base.stable_read(
                directory / name,
                f"P3.01 fixed P3.00 {label} {name}",
                repro.ARTIFACT_LIMITS[name],
            )
            for name in sorted(repro.ARTIFACT_LIMITS)
        }
        if {
            name: base.receipt(payload)
            for name, payload in build_payloads[label].items()
        } != expected:
            raise CheckError(f"P3.01 fixed P3.00 {label} artifact differs")
    _require_distinct_artifact_inodes(directories, set(repro.ARTIFACT_LIMITS))
    for name in sorted(expected_equal):
        if build_payloads["build_a"][name] != build_payloads["build_b"][name]:
            raise CheckError(f"P3.01 fixed P3.00 A/B mismatch: {name}")

    postbuild = linked.get("postbuild_audit", {})
    try:
        current_table = postbuild_audit.linked_table_data(check_args, result)
        current_callsites = postbuild_audit.full_lto_callsite_pair(check_args)
        current_closure = postbuild_audit.closure.run_closure(root)
        current_host = postbuild_audit.host_native_exhaustive(root)
    except (
        postbuild_audit.AuditError,
        postbuild_audit.closure.ClosureError,
        repro.CheckError,
    ) as exc:
        raise CheckError(str(exc)) from exc
    if (
        postbuild.get("verified") is not True
        or postbuild.get("linked_table_data") != current_table
        or postbuild.get("full_lto_p300_probe_callsites") != current_callsites
        or postbuild.get("event_ingress_irq_telemetry") != current_closure
        or postbuild.get("host_native_exhaustive") != current_host
    ):
        raise CheckError("P3.01 fixed P3.00 postbuild proof differs")
    telemetry = (
        result.get("linked_audit", {})
        .get("postbuild_audit", {})
        .get("event_ingress_irq_telemetry", {})
    )
    fixed_image = exact_contract.get("fixed_image", {})
    if (
        result.get("build_a", {}).get("artifacts", {}).get("Image")
        != {
            "size": fixed_image.get("size"),
            "sha256": fixed_image.get("sha256"),
        }
        or telemetry.get("verified") is not True
        or telemetry.get("pair_adjacency", {}).get("verified") is not True
        or telemetry.get("delivery_lifecycle", {}).get("verified") is not True
    ):
        raise CheckError("P3.01 fixed P3.00 reproducibility result differs")
    return result, base.receipt(payload)


def _configure() -> None:
    candidate._configure()
    repro._configure()
    base.candidate = _CANDIDATE_STATIC_VIEW
    base.repro = repro
    base.contract = contract
    base.p286_closure = _P301_STOCK_CLOSURE_VIEW
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
    base.verify_repro = verify_repro
    base.verify_userspace = verify_userspace


def __getattr__(name: str):
    _configure()
    return getattr(base, name)


def audit(args):  # noqa: ANN001, ANN201
    _configure()
    return base.audit(args)


def parse_args(argv: list[str] | None = None):
    _configure()
    return base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure()
    try:
        args = base.parse_args(argv)
        result = base.audit(args)
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
        repro.CheckError,
        postbuild_audit.AuditError,
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
