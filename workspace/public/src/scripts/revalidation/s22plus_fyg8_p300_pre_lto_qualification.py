#!/usr/bin/env python3
"""Pre-Full-LTO qualification for P3.00 gadget-start telemetry."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import importlib
from pathlib import Path
import stat
import sys
from typing import Iterator

import build_s22plus_fyg8_p300_candidate as candidate_builder
import s22plus_fyg8_p282_pre_lto_qualification as process_qualification
import s22plus_fyg8_p296_pre_lto_qualification as base
import s22plus_fyg8_p300_candidate_contract as candidate_contract
import s22plus_fyg8_p300_e2_stock_closure as closure
import s22plus_fyg8_p300_source_contract as p300
import s22plus_fyg8_p300_telemetry_spec as spec
import s22plus_fyg8_p300_userspace_build as userspace


p286 = p300
SCHEMA = "s22plus_fyg8_p300_pre_lto_qualification_v1"
VERDICT = "PASS_P300_PRE_FULL_LTO_QUALIFICATION_HOST_ONLY"
LINKED_META_SCHEMA = "s22plus_fyg8_p300_linked_audit_meta_v1"
LINKED_META_VERDICT = "PASS_P300_LINKED_AUDIT_META_HOST_ONLY"
LINKED_AUDIT_MODULE_NAME = "s22plus_fyg8_p300_linked_audit"
LINKED_AUDIT_TEST = Path("tests/test_s22plus_fyg8_p300_contract.py")
LINKED_AUDIT_PATH = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_p300_linked_audit.py"
)
DEFAULT_LINKED_AUDIT_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p300_pre_lto/linked-audit-meta.json"
)
DEFAULT_INGESTION_RESULT = base.DEFAULT_INGESTION_RESULT
DEFAULT_USERSPACE_RESULT = userspace.DEFAULT_OUT / "userspace-result.json"
DEFAULT_LIFECYCLE_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p298_pre_lto/"
    "p280-trace-lifecycle-current/result.json"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p300_pre_lto/qualification.json"
)
FOCUSED_TESTS = (
    *tuple(
        path
        for path in base.FOCUSED_TESTS
        if "p296" not in path.as_posix()
    ),
    Path("tests/test_s22plus_fyg8_p300_contract.py"),
    Path(
        "workspace/public/src/scripts/revalidation/"
        "test_s22plus_fyg8_p300_telemetry.py"
    ),
)
P300_GATE_NAME = "24-gadget-start-event-attribution"
PROCESS_V2_TESTS = tuple(
    path
    for path in process_qualification.HISTORICAL_PROCESS_V2_TESTS
    if path != Path("tests/test_device_action_process_v2_docs.py")
)
REUSED_S22_POLICY_RECEIPTS = {
    "AGENTS.md": "3289aedf8b55c2d74e3252c72e7b6b9bc003ef62379fc6e7b192a845c80dd747",
    "docs/operations/DEVICE_ACTION_PROCESS_V2.md": (
        "9b61af3ef7ee6f82f529dc18a21946eff3e4fa92597448f11f8aa738c93523c0"
    ),
    "docs/operations/DEVICE_ACTION_RISK_TIERS.md": (
        "c2bc3b99b364ec3d08419dc83cca14f35ea9edc1d03173e237740b786ecf8a96"
    ),
    "docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md": (
        "03c9e6303fccc1d54c22ed6d03d5aa31bcbfb2032fe28bb5fd24928664a3c03a"
    ),
}
INHERITED_P280_LIFECYCLE_RESULT = True
GATE_IMPLEMENTATION_SOURCES = {
    **base.GATE_IMPLEMENTATION_SOURCES,
    "closure": Path(__file__).with_name("s22plus_fyg8_p300_e2_stock_closure.py"),
    "p300_qualification": Path(__file__).resolve(),
    "p300_source_contract": Path(__file__).with_name("s22plus_fyg8_p300_source_contract.py"),
    "p300_telemetry_spec": Path(__file__).with_name("s22plus_fyg8_p300_telemetry_spec.py"),
    "p300_telemetry_closure": Path(__file__).with_name("s22plus_fyg8_p300_telemetry_closure.py"),
    "p300_identity_tiers": Path(__file__).with_name("s22plus_fyg8_p300_identity_tiers.py"),
    "p300_linked_audit": Path(__file__).with_name("s22plus_fyg8_p300_linked_audit.py"),
    "p300_candidate_builder": Path(__file__).with_name("build_s22plus_fyg8_p300_candidate.py"),
    "p300_userspace_builder": Path(__file__).with_name("s22plus_fyg8_p300_userspace_build.py"),
    "p300_decoder": Path(__file__).with_name("s22plus_fyg8_p300_telemetry_decoder.py"),
}
QualificationError = base.QualificationError


def _validate_reused_s22_process_capability() -> None:
    root = Path(__file__).resolve().parents[5]
    for relative, expected in REUSED_S22_POLICY_RECEIPTS.items():
        path = root / relative
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise QualificationError(f"reused S22 policy path is indirect: {relative}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise QualificationError(f"reused S22 policy receipt changed: {relative}")


class _QualificationSourceContractAdapter:
    DEFAULT_DWC3_MSM_MODULE = base.QUALIFICATION_SOURCE_CONTRACT.DEFAULT_DWC3_MSM_MODULE
    DEFAULT_HSPHY_MODULE = base.QUALIFICATION_SOURCE_CONTRACT.DEFAULT_HSPHY_MODULE

    def __getattr__(self, name: str):
        return getattr(p300, name)


QUALIFICATION_SOURCE_CONTRACT = _QualificationSourceContractAdapter()


def _expected_safety(exact_contract: dict[str, object]) -> dict[str, object]:
    if (
        exact_contract.get("profile") != p300.PROFILE
        or exact_contract.get("source_contract_id") != p300.CONTRACT_ID
    ):
        raise QualificationError("P3.00 safety contract identity mismatch")
    expected = {
        "host_only": True,
        "device_contact": False,
        "device_write": False,
        "odin_invoked": False,
        "flash": False,
        "partition_write": False,
        "live_authorized": False,
        "boot_only_ap": True,
        "ap_members": ["boot.img.lz4"],
        "no_shell": True,
        "no_block_write": True,
        "no_reboot_syscall": True,
        "userspace_sysfs_configfs_write_scope": spec.SAFETY_USERSPACE_WRITE_SCOPE,
        "usb_scope": spec.SAFETY_USB_SCOPE,
        "module_init_probe_authority": "active-live-unproved",
        **spec.RUNTIME_AUTHORITY,
        "candidate_module_binaries_injected": 0,
        "built_in_telemetry_only": True,
    }
    actual = candidate_builder.artifact_safety(exact_contract)
    if actual != expected:
        raise QualificationError("P3.00 safety dictionary is not exact")
    return actual


def _load_linked_audit_module():
    try:
        module = importlib.import_module(LINKED_AUDIT_MODULE_NAME)
    except (ImportError, OSError) as exc:
        raise QualificationError("P3.00 linked-audit module is unavailable") from exc
    if (
        getattr(module, "EXPECTED_SOURCE_CONTRACT_ID", None) != p300.CONTRACT_ID
        or getattr(module, "ADAPTER_ID", None)
        != "s22plus-fyg8-p300-linked-audit-v1"
    ):
        raise QualificationError("P3.00 linked-audit identity drifted")
    return module


_REPLACEMENTS = {
    "candidate_builder": candidate_builder,
    "candidate_contract": candidate_contract,
    "closure": closure,
    "p286": p300,
    "p296": p300,
    "spec": spec,
    "userspace": userspace,
    "SCHEMA": SCHEMA,
    "VERDICT": VERDICT,
    "LINKED_META_SCHEMA": LINKED_META_SCHEMA,
    "LINKED_META_VERDICT": LINKED_META_VERDICT,
    "LINKED_AUDIT_MODULE_NAME": LINKED_AUDIT_MODULE_NAME,
    "LINKED_AUDIT_TEST": LINKED_AUDIT_TEST,
    "LINKED_AUDIT_PATH": LINKED_AUDIT_PATH,
    "DEFAULT_LINKED_AUDIT_RESULT": DEFAULT_LINKED_AUDIT_RESULT,
    "DEFAULT_USERSPACE_RESULT": DEFAULT_USERSPACE_RESULT,
    "DEFAULT_LIFECYCLE_RESULT": DEFAULT_LIFECYCLE_RESULT,
    "DEFAULT_OUT": DEFAULT_OUT,
    "FOCUSED_TESTS": FOCUSED_TESTS,
    "P296_GATE_NAME": P300_GATE_NAME,
    "GATE_IMPLEMENTATION_SOURCES": GATE_IMPLEMENTATION_SOURCES,
    "QUALIFICATION_SOURCE_CONTRACT": QUALIFICATION_SOURCE_CONTRACT,
    "_expected_safety": _expected_safety,
    "_load_linked_audit_module": _load_linked_audit_module,
}


@contextmanager
def _context() -> Iterator[None]:
    _validate_reused_s22_process_capability()
    previous = {name: getattr(base, name) for name in _REPLACEMENTS}
    previous_process_tests = process_qualification.HISTORICAL_PROCESS_V2_TESTS
    for name, value in _REPLACEMENTS.items():
        setattr(base, name, value)
    process_qualification.HISTORICAL_PROCESS_V2_TESTS = PROCESS_V2_TESTS
    try:
        yield
    finally:
        process_qualification.HISTORICAL_PROCESS_V2_TESTS = previous_process_tests
        for name, value in previous.items():
            setattr(base, name, value)


def create(**kwargs):  # noqa: ANN003, ANN201
    with _context():
        return base.create(**kwargs)


def verify_receipt(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    with _context():
        return base.verify_receipt(*args, **kwargs)


def _argv_with_source(argv: list[str] | None) -> list[str]:
    values = list(sys.argv[1:] if argv is None else argv)
    if not any(value == "--source" or value.startswith("--source=") for value in values):
        values.extend(("--source", str(candidate_contract.DEFAULT_SOURCE)))
    return values


def parse_args(argv: list[str] | None = None):
    with _context():
        return base.parse_args(_argv_with_source(argv))


def main(argv: list[str] | None = None) -> int:
    with _context():
        return base.main(_argv_with_source(argv))


if __name__ == "__main__":
    raise SystemExit(main())
