#!/usr/bin/env python3
"""Audit the P3.07 EUD/QSCRATCH boot-only candidate."""

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
from typing import Iterator

import build_s22plus_fyg8_p307_candidate as candidate
import s22plus_fyg8_p304_e2_stock_closure as closure
import s22plus_fyg8_p304_userspace_build as parent_userspace
import s22plus_fyg8_p305_candidate_static_checker as parent
import s22plus_fyg8_p307_candidate_contract as contract
import s22plus_fyg8_p307_overlay_contract as overlay
import s22plus_fyg8_p307_qscratch_audit as qscratch_audit
import s22plus_fyg8_p307_telemetry_spec as spec
import s22plus_fyg8_p307_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p307_candidate_static_checker_v1"
VERDICT = "PASS_P307_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
TARGET = contract.TARGET
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_CANDIDATE_B = Path("workspace/private/outputs/s22plus_fyg8_p307/candidate-b")
DEFAULT_IMAGE = candidate.DEFAULT_IMAGE
DEFAULT_REPRO_RESULT = candidate.DEFAULT_REPRO_RESULT
DEFAULT_USERSPACE = candidate.DEFAULT_USERSPACE
DEFAULT_BASE_BOOT = candidate.DEFAULT_BASE_BOOT
DEFAULT_VENDOR_RAMDISK = candidate.DEFAULT_VENDOR_RAMDISK
DEFAULT_VENDOR_BOOT = parent.DEFAULT_VENDOR_BOOT
DEFAULT_LZ4 = candidate.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = candidate.DEFAULT_MAGISKBOOT
DEFAULT_BUILD_A = parent.DEFAULT_BUILD_A
DEFAULT_BUILD_B = parent.DEFAULT_BUILD_B
DEFAULT_SOURCE = contract.DEFAULT_SOURCE
DEFAULT_INTENT = contract.DEFAULT_INTENT
DEFAULT_PATCH = contract.DEFAULT_PATCH
DEFAULT_NM = parent.DEFAULT_NM
DEFAULT_OBJDUMP = parent.DEFAULT_OBJDUMP
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p307/static-check-result.json")
CheckError = parent.CheckError
base = parent.base
ARTIFACT_LIMITS = parent.ARTIFACT_LIMITS
stable_read = parent.stable_read
repo_root = parent.repo_root
resolve = parent.resolve


class _P307StockClosureView:
    expected_init: bytes | None = None

    def __getattr__(self, name: str):
        return getattr(parent.parent.inherited._P303_STOCK_CLOSURE_VIEW, name)  # noqa: SLF001

    @contextmanager
    def _p286_authority_paths(self) -> Iterator[None]:
        expected = self.expected_init
        if expected is None:
            raise CheckError("P3.07 exact init authority binding is absent")
        authority = parent.parent.inherited.inherited.p300_closure
        additions = {"/dev/kmsg", spec.EUD_CACHE_PATH}
        required = frozenset({*authority.REQUIRED_ABSOLUTE_PATH_STRINGS, *additions})
        allowed = frozenset({*authority.ALLOWED_ABSOLUTE_PATH_STRINGS, *additions})
        printable = authority.p286.p282.p280.isolated_p260._printable_strings(  # noqa: SLF001
            expected
        )
        paths = authority.p286.p282._absolute_path_candidates(printable)  # noqa: SLF001
        incidental = paths - allowed
        if (
            required - paths
            or incidental != {'/E9"'}
            or any(expected.count(value.encode("ascii")) != 1 for value in incidental)
            or expected.count(b"/dev/kmsg") != 1
            or expected.count(spec.EUD_CACHE_PATH.encode("ascii")) != 1
        ):
            raise CheckError("P3.07 exact init authority path set differs")
        scrubbed = expected
        for value in sorted(incidental):
            encoded = value.encode("ascii")
            scrubbed = scrubbed.replace(encoded, b"\0" * len(encoded))

        def validate(data: bytes) -> None:
            if data != expected:
                raise authority.ClosureError(
                    "P3.07 effective init differs from source-bound userspace"
                )
            previous_required = authority.REQUIRED_ABSOLUTE_PATH_STRINGS
            previous_allowed = authority.ALLOWED_ABSOLUTE_PATH_STRINGS
            authority.REQUIRED_ABSOLUTE_PATH_STRINGS = required
            authority.ALLOWED_ABSOLUTE_PATH_STRINGS = allowed
            try:
                with authority._p300_authority_globals():  # noqa: SLF001
                    authority._P282_VALIDATE_AUTHORITY_STRINGS(scrubbed)  # noqa: SLF001
            finally:
                authority.REQUIRED_ABSOLUTE_PATH_STRINGS = previous_required
                authority.ALLOWED_ABSOLUTE_PATH_STRINGS = previous_allowed

        previous = authority.p286.p282._validate_p282_authority_strings  # noqa: SLF001
        authority.p286.p282._validate_p282_authority_strings = validate  # noqa: SLF001
        try:
            yield
        finally:
            authority.p286.p282._validate_p282_authority_strings = previous  # noqa: SLF001


_P307_STOCK_CLOSURE_VIEW = _P307StockClosureView()


def _expected_userspace_source(exact: dict) -> dict:
    return userspace._source_contract(exact)  # noqa: SLF001


@contextmanager
def rootfs_entrypoint_context(
    _closure_api, exact, payloads  # noqa: ANN001
) -> Iterator[None]:
    previous = _P307_STOCK_CLOSURE_VIEW.expected_init
    _P307_STOCK_CLOSURE_VIEW.expected_init = payloads["init"]
    try:
        with parent.parent.inherited.rootfs_entrypoint_context(
            _P307_STOCK_CLOSURE_VIEW, exact, payloads
        ):
            yield
    finally:
        _P307_STOCK_CLOSURE_VIEW.expected_init = previous


def _configure() -> None:
    parent._configure()
    candidate._configure()
    candidate.parent.packager = candidate.parent.parent.packager
    userspace.module_count_context = parent_userspace.module_count_context
    parent.candidate = candidate
    parent.contract = contract
    parent.overlay = overlay
    parent.userspace = userspace
    parent.SCHEMA = SCHEMA
    parent.VERDICT = VERDICT
    parent.TARGET = TARGET
    parent.DEFAULT_CANDIDATE = DEFAULT_CANDIDATE
    parent.DEFAULT_CANDIDATE_B = DEFAULT_CANDIDATE_B
    parent.DEFAULT_USERSPACE = DEFAULT_USERSPACE
    parent.DEFAULT_SOURCE = DEFAULT_SOURCE
    parent.DEFAULT_INTENT = DEFAULT_INTENT
    parent.DEFAULT_PATCH = DEFAULT_PATCH
    parent.DEFAULT_OUT = DEFAULT_OUT
    parent._expected_userspace_source = _expected_userspace_source  # noqa: SLF001

    inherited = parent.parent.inherited
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
    base.verify_userspace = parent.parent.verify_userspace


def audit(args):  # noqa: ANN001, ANN201
    _configure()
    result = base.audit(args)
    root = base.repo_root()
    exact = overlay.verify_intent(root, base.resolve(root, args.intent))
    clock = parent.parent.inherited.callsite_audit.audit(
        root, Path(parent.parent.inherited.spec.MODULE_PATH), args.objdump, "readelf"
    )
    qscratch = qscratch_audit.audit(
        root, Path(spec.DWC3_MODULE_PATH), args.objdump, "readelf"
    )
    if clock != exact["callsite_audit"]:
        raise CheckError("P3.07 inherited post-BL clock audit changed")
    if qscratch != exact["qscratch_audit"]:
        raise CheckError("P3.07 QSCRATCH callsite audit changed")
    if exact["telemetry"].get("verified") is not True:
        raise CheckError("P3.07 telemetry contract differs")
    if exact["observer"].get("eud_cache_read_count") != 1:
        raise CheckError("P3.07 EUD cache read cardinality differs")
    result["p303_callsite_audit"] = clock
    result["p307_qscratch_audit"] = qscratch
    result["p307_telemetry"] = exact["telemetry"]
    result["p307_observer"] = exact["observer"]
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
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode("ascii")
            + b"\n"
        )
        base.durable_create(base.resolve(base.repo_root(), args.out), encoded)
    except (
        CheckError,
        candidate.BuildError,
        base.carrier.BuildError,
        base.boot_verify.BootVerifyError,
        parent.parent.inherited.inherited.repro.CheckError,
        parent.parent.inherited.inherited.postbuild_audit.AuditError,
        parent.parent.inherited.callsite_audit.AuditError,
        qscratch_audit.AuditError,
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
