#!/usr/bin/env python3
"""Pre-Full-LTO qualification for P2.98 gadget-start telemetry."""

from __future__ import annotations

from contextlib import contextmanager
import importlib
from pathlib import Path
import sys
from typing import Iterator

import build_s22plus_fyg8_p298_candidate as candidate_builder
import s22plus_fyg8_p296_pre_lto_qualification as base
import s22plus_fyg8_p298_candidate_contract as candidate_contract
import s22plus_fyg8_p298_e2_stock_closure as closure
import s22plus_fyg8_p298_source_contract as p298
import s22plus_fyg8_p298_telemetry_spec as spec
import s22plus_fyg8_p298_userspace_build as userspace


p286 = p298
SCHEMA = "s22plus_fyg8_p298_pre_lto_qualification_v1"
VERDICT = "PASS_P298_PRE_FULL_LTO_QUALIFICATION_HOST_ONLY"
LINKED_META_SCHEMA = "s22plus_fyg8_p298_linked_audit_meta_v1"
LINKED_META_VERDICT = "PASS_P298_LINKED_AUDIT_META_HOST_ONLY"
LINKED_AUDIT_MODULE_NAME = "s22plus_fyg8_p298_linked_audit"
LINKED_AUDIT_TEST = Path("tests/test_s22plus_fyg8_p298_contract.py")
LINKED_AUDIT_PATH = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_p298_linked_audit.py"
)
DEFAULT_LINKED_AUDIT_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p298_pre_lto/linked-audit-meta.json"
)
DEFAULT_INGESTION_RESULT = base.DEFAULT_INGESTION_RESULT
DEFAULT_USERSPACE_RESULT = userspace.DEFAULT_OUT / "userspace-result.json"
DEFAULT_LIFECYCLE_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p298_pre_lto/"
    "p280-trace-lifecycle-current/result.json"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p298_pre_lto/qualification.json"
)
FOCUSED_TESTS = (
    *tuple(
        path
        for path in base.FOCUSED_TESTS
        if "p296" not in path.as_posix()
    ),
    Path("tests/test_s22plus_fyg8_p298_contract.py"),
    Path(
        "workspace/public/src/scripts/revalidation/"
        "test_s22plus_fyg8_p298_telemetry.py"
    ),
)
P298_GATE_NAME = "24-gadget-start-event-attribution"
GATE_IMPLEMENTATION_SOURCES = {
    **base.GATE_IMPLEMENTATION_SOURCES,
    "closure": Path(__file__).with_name("s22plus_fyg8_p298_e2_stock_closure.py"),
    "p298_qualification": Path(__file__).resolve(),
    "p298_source_contract": Path(__file__).with_name("s22plus_fyg8_p298_source_contract.py"),
    "p298_telemetry_spec": Path(__file__).with_name("s22plus_fyg8_p298_telemetry_spec.py"),
    "p298_telemetry_closure": Path(__file__).with_name("s22plus_fyg8_p298_telemetry_closure.py"),
    "p298_identity_tiers": Path(__file__).with_name("s22plus_fyg8_p298_identity_tiers.py"),
    "p298_linked_audit": Path(__file__).with_name("s22plus_fyg8_p298_linked_audit.py"),
    "p298_candidate_builder": Path(__file__).with_name("build_s22plus_fyg8_p298_candidate.py"),
    "p298_userspace_builder": Path(__file__).with_name("s22plus_fyg8_p298_userspace_build.py"),
    "p298_decoder": Path(__file__).with_name("s22plus_fyg8_p298_telemetry_decoder.py"),
}
QualificationError = base.QualificationError


class _QualificationSourceContractAdapter:
    DEFAULT_DWC3_MSM_MODULE = base.QUALIFICATION_SOURCE_CONTRACT.DEFAULT_DWC3_MSM_MODULE
    DEFAULT_HSPHY_MODULE = base.QUALIFICATION_SOURCE_CONTRACT.DEFAULT_HSPHY_MODULE

    def __getattr__(self, name: str):
        return getattr(p298, name)


QUALIFICATION_SOURCE_CONTRACT = _QualificationSourceContractAdapter()


def _expected_safety(exact_contract: dict[str, object]) -> dict[str, object]:
    if (
        exact_contract.get("profile") != p298.PROFILE
        or exact_contract.get("source_contract_id") != p298.CONTRACT_ID
    ):
        raise QualificationError("P2.98 safety contract identity mismatch")
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
        raise QualificationError("P2.98 safety dictionary is not exact")
    return actual


def _load_linked_audit_module():
    try:
        module = importlib.import_module(LINKED_AUDIT_MODULE_NAME)
    except (ImportError, OSError) as exc:
        raise QualificationError("P2.98 linked-audit module is unavailable") from exc
    if (
        getattr(module, "EXPECTED_SOURCE_CONTRACT_ID", None) != p298.CONTRACT_ID
        or getattr(module, "ADAPTER_ID", None)
        != "s22plus-fyg8-p298-linked-audit-v1"
    ):
        raise QualificationError("P2.98 linked-audit identity drifted")
    return module


_REPLACEMENTS = {
    "candidate_builder": candidate_builder,
    "candidate_contract": candidate_contract,
    "closure": closure,
    "p286": p298,
    "p296": p298,
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
    "P296_GATE_NAME": P298_GATE_NAME,
    "GATE_IMPLEMENTATION_SOURCES": GATE_IMPLEMENTATION_SOURCES,
    "QUALIFICATION_SOURCE_CONTRACT": QUALIFICATION_SOURCE_CONTRACT,
    "_expected_safety": _expected_safety,
    "_load_linked_audit_module": _load_linked_audit_module,
}


@contextmanager
def _context() -> Iterator[None]:
    previous = {name: getattr(base, name) for name in _REPLACEMENTS}
    for name, value in _REPLACEMENTS.items():
        setattr(base, name, value)
    try:
        yield
    finally:
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
