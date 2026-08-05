#!/usr/bin/env python3
"""Audit the P3.06 passive IPC-observer boot-only candidate."""

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
from typing import Iterator

import build_s22plus_fyg8_p306_candidate as candidate
import s22plus_fyg8_p304_candidate_static_checker as parent
import s22plus_fyg8_p304_e2_stock_closure as closure
import s22plus_fyg8_p304_userspace_build as parent_userspace
import s22plus_fyg8_p306_candidate_contract as contract
import s22plus_fyg8_p306_overlay_contract as overlay
import s22plus_fyg8_p306_userspace_build as userspace


SCHEMA = "s22plus_fyg8_p306_candidate_static_checker_v1"
VERDICT = "PASS_P306_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
TARGET = contract.TARGET
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_CANDIDATE_B = Path("workspace/private/outputs/s22plus_fyg8_p306/candidate-b")
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
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p306/static-check-result-v2.json")
CheckError = parent.CheckError
base = parent.base
ARTIFACT_LIMITS = parent.ARTIFACT_LIMITS
stable_read = parent.stable_read
repo_root = parent.repo_root
resolve = parent.resolve


class _P306StockClosureView:
    expected_init: bytes | None = None

    def __getattr__(self, name: str):
        return getattr(parent.inherited._P303_STOCK_CLOSURE_VIEW, name)  # noqa: SLF001

    @contextmanager
    def _p286_authority_paths(self) -> Iterator[None]:
        expected = self.expected_init
        if expected is None:
            raise CheckError("P3.06 exact init authority binding is absent")
        closure = parent.inherited.inherited.p300_closure
        additions = {
            "/dev/kmsg",
            "/sys/kernel/debug",
            "/sys/kernel/debug/ipc_logging/a600000_ssusb/log",
        }
        required = frozenset({*closure.REQUIRED_ABSOLUTE_PATH_STRINGS, *additions})
        allowed = frozenset({*closure.ALLOWED_ABSOLUTE_PATH_STRINGS, *additions})
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
            or expected.count(b"/sys/kernel/debug/ipc_logging/a600000_ssusb/log") != 1
        ):
            raise CheckError("P3.06 exact init authority path set differs")
        scrubbed = expected
        for value in sorted(incidental):
            encoded = value.encode("ascii")
            scrubbed = scrubbed.replace(encoded, b"\0" * len(encoded))

        def validate(data: bytes) -> None:
            if data != expected:
                raise closure.ClosureError(
                    "P3.06 effective init differs from source-bound userspace"
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


_P306_STOCK_CLOSURE_VIEW = _P306StockClosureView()


def _expected_userspace_source(exact: dict) -> dict:
    return userspace._source_contract(exact)  # noqa: SLF001


@contextmanager
def rootfs_entrypoint_context(
    _closure_api, exact, payloads  # noqa: ANN001
) -> Iterator[None]:
    previous = _P306_STOCK_CLOSURE_VIEW.expected_init
    _P306_STOCK_CLOSURE_VIEW.expected_init = payloads["init"]
    try:
        with parent.inherited.rootfs_entrypoint_context(
            _P306_STOCK_CLOSURE_VIEW, exact, payloads
        ):
            yield
    finally:
        _P306_STOCK_CLOSURE_VIEW.expected_init = previous


def _configure() -> None:
    parent._configure()
    candidate._configure()
    candidate.packager = candidate.parent.packager
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

    inherited = parent.inherited
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
    base.verify_userspace = parent.verify_userspace


def audit(args):  # noqa: ANN001, ANN201
    _configure()
    result = base.audit(args)
    root = base.repo_root()
    exact = overlay.verify_intent(root, base.resolve(root, args.intent))
    proved = parent.inherited.callsite_audit.audit(
        root, Path(parent.inherited.spec.MODULE_PATH), args.objdump, "readelf"
    )
    if proved != exact["callsite_audit"]:
        raise CheckError("P3.06 inherited post-BL callsite audit changed")
    if exact["ipc_telemetry"].get("verified") is not True:
        raise CheckError("P3.06 IPC telemetry contract differs")
    if exact["observer"] != {
        "path": "/sys/kernel/debug/ipc_logging/a600000_ssusb/log",
        "armed_after_module_index": 58,
        "armed_before_module_index": 59,
        "kernel_changed": False,
        "module_plan_changed": False,
        "log_level_changed": False,
        "passive_read_only": True,
        "verified": True,
    }:
        raise CheckError("P3.06 IPC observer boundary differs")
    result["p303_callsite_audit"] = proved
    result["p306_ipc_telemetry"] = exact["ipc_telemetry"]
    result["p306_observer"] = exact["observer"]
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
        parent.inherited.inherited.repro.CheckError,
        parent.inherited.inherited.postbuild_audit.AuditError,
        parent.inherited.callsite_audit.AuditError,
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
