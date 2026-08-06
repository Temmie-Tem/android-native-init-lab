#!/usr/bin/env python3
"""Pre-Full-LTO qualification for P3.10 Carrier v2."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import importlib
import json
from pathlib import Path
import stat
import sys
from typing import Iterator

import build_s22plus_fyg8_p310_candidate as candidate_builder
import s22plus_fyg8_p282_pre_lto_qualification as process_qualification
import s22plus_fyg8_p300_pre_lto_qualification as parent
import s22plus_fyg8_p310_candidate_contract as candidate_contract
import s22plus_fyg8_p310_e2_stock_closure as closure
import s22plus_fyg8_p310_source_contract as p310
import s22plus_fyg8_p308_telemetry_spec as spec
import s22plus_fyg8_p310_userspace_build as userspace


base = parent.base
p286 = p310
SCHEMA = "s22plus_fyg8_p310_pre_lto_qualification_v1"
VERDICT = "PASS_P310_PRE_FULL_LTO_QUALIFICATION_HOST_ONLY"
LINKED_META_SCHEMA = "s22plus_fyg8_p310_linked_audit_meta_v1"
LINKED_META_VERDICT = "PASS_P310_LINKED_AUDIT_META_HOST_ONLY"
LINKED_AUDIT_MODULE_NAME = "s22plus_fyg8_p310_linked_audit"
LINKED_AUDIT_TEST = Path("tests/test_s22plus_fyg8_p310_integration.py")
LINKED_AUDIT_PATH = Path("workspace/public/src/scripts/revalidation/s22plus_fyg8_p310_linked_audit.py")
DEFAULT_LINKED_AUDIT_RESULT = Path("workspace/private/outputs/s22plus_fyg8_p310_pre_lto/linked-audit-meta.json")
DEFAULT_INGESTION_RESULT = parent.DEFAULT_INGESTION_RESULT
DEFAULT_USERSPACE_RESULT = userspace.DEFAULT_OUT / "userspace-result.json"
DEFAULT_LIFECYCLE_RESULT = parent.DEFAULT_LIFECYCLE_RESULT
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p310_pre_lto/qualification.json")
P300_LINKED_META_PATH = Path(
    "workspace/private/outputs/s22plus_fyg8_p300_pre_lto/linked-audit-meta.json"
)
P300_LINKED_META_RECEIPT = {
    "size": 2135,
    "sha256": "78d884a230639f32a86ee6ab370e805ce7f8c6d3f1205d9f2a99e333618897cb",
}
FOCUSED_TESTS = (
    *parent.FOCUSED_TESTS,
    Path("tests/test_s22plus_fyg8_p310_carrier_v2.py"),
    Path("tests/test_s22plus_fyg8_p310_integration.py"),
    Path("tests/test_s22plus_fyg8_p309_tracefs_abi.py"),
)
P310_GATE_NAME = "25-carrier-v2-hsphy-attribution"
PROCESS_V2_TESTS = parent.PROCESS_V2_TESTS
GATE_IMPLEMENTATION_SOURCES = {
    **parent.GATE_IMPLEMENTATION_SOURCES,
    "closure": Path(__file__).with_name("s22plus_fyg8_p310_e2_stock_closure.py"),
    "p310_qualification": Path(__file__).resolve(),
    "p310_source_contract": Path(__file__).with_name("s22plus_fyg8_p310_source_contract.py"),
    "p310_carrier_model": Path(__file__).with_name("s22plus_fyg8_p310_carrier_model.py"),
    "p310_carrier_transform": Path(__file__).with_name("s22plus_fyg8_p310_carrier_transform.py"),
    "p310_generator": Path(__file__).with_name("s22plus_fyg8_p310_generator.py"),
    "p310_userspace_builder": Path(__file__).with_name("s22plus_fyg8_p310_userspace_build.py"),
    "p310_candidate_builder": Path(__file__).with_name("build_s22plus_fyg8_p310_candidate.py"),
    "p310_linked_audit": LINKED_AUDIT_PATH,
}
QualificationError = base.QualificationError


def _inherited_known_good_linked_binding(root: Path) -> dict[str, object]:
    """Reuse the exact P3.00 linked capability after its raw P2.80 input aged out."""
    path = root / P300_LINKED_META_PATH
    before = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise QualificationError("P3.00 linked-audit capability receipt is indirect")
    payload = path.read_bytes()
    after = path.stat()
    receipt = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
    if (
        receipt != P300_LINKED_META_RECEIPT
        or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
    ):
        raise QualificationError("P3.00 linked-audit capability receipt changed")
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise QualificationError("P3.00 linked-audit capability receipt is invalid") from exc
    canonical = dict(value) if isinstance(value, dict) else {}
    digest = canonical.pop("payload_sha256", None)
    known_good = value.get("known_good") if isinstance(value, dict) else None
    if (
        digest != hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("ascii")
        ).hexdigest()
        or value.get("schema") != "s22plus_fyg8_p300_linked_audit_meta_v1"
        or value.get("verdict") != "PASS_P300_LINKED_AUDIT_META_HOST_ONLY"
        or value.get("source_contract_id")
        != "s22plus-fyg8-p300-event-ingress-irq-attribution-v1"
        or value.get("adapter_id") != "s22plus-fyg8-p300-linked-audit-v1"
        or value.get("verified") is not True
        or not isinstance(known_good, dict)
        or known_good.get("linked_adapter") != "s22plus-fyg8-p280-linked-audit-v1"
        or known_good.get("verified") is not True
    ):
        raise QualificationError("P3.00 linked-audit capability semantics changed")
    return known_good


class _QualificationSourceContractAdapter:
    DEFAULT_DWC3_MSM_MODULE = base.QUALIFICATION_SOURCE_CONTRACT.DEFAULT_DWC3_MSM_MODULE
    DEFAULT_HSPHY_MODULE = base.QUALIFICATION_SOURCE_CONTRACT.DEFAULT_HSPHY_MODULE

    def __getattr__(self, name: str):
        return getattr(p310, name)


QUALIFICATION_SOURCE_CONTRACT = _QualificationSourceContractAdapter()


def _expected_safety(exact_contract: dict[str, object]) -> dict[str, object]:
    if exact_contract.get("profile") != p310.PROFILE or exact_contract.get("source_contract_id") != p310.CONTRACT_ID:
        raise QualificationError("P3.10 safety contract identity mismatch")
    actual = candidate_builder.artifact_safety(exact_contract)
    if (
        actual.get("host_only") is not True
        or actual.get("device_contact") is not False
        or actual.get("device_write") is not False
        or actual.get("boot_only_ap") is not True
        or actual.get("ap_members") != ["boot.img.lz4"]
        or actual.get("candidate_module_binaries_injected") != 0
        or actual.get("built_in_telemetry_only") is not True
        or actual.get("carrier_v2") is not True
    ):
        raise QualificationError("P3.10 safety dictionary differs")
    return actual


def _load_linked_audit_module():
    try:
        module = importlib.import_module(LINKED_AUDIT_MODULE_NAME)
    except (ImportError, OSError) as exc:
        raise QualificationError("P3.10 linked-audit module is unavailable") from exc
    if getattr(module, "EXPECTED_SOURCE_CONTRACT_ID", None) != p310.CONTRACT_ID or getattr(module, "ADAPTER_ID", None) != "s22plus-fyg8-p310-linked-audit-v1":
        raise QualificationError("P3.10 linked-audit identity drifted")
    return module


_REPLACEMENTS = {
    "candidate_builder": candidate_builder,
    "candidate_contract": candidate_contract,
    "closure": closure,
    "p286": p310,
    "p296": p310,
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
    "P296_GATE_NAME": P310_GATE_NAME,
    "GATE_IMPLEMENTATION_SOURCES": GATE_IMPLEMENTATION_SOURCES,
    "QUALIFICATION_SOURCE_CONTRACT": QUALIFICATION_SOURCE_CONTRACT,
    "_expected_safety": _expected_safety,
    "_load_linked_audit_module": _load_linked_audit_module,
}


@contextmanager
def _context() -> Iterator[None]:
    parent._validate_reused_s22_process_capability()  # noqa: SLF001
    previous = {name: getattr(base, name) for name in _REPLACEMENTS}
    previous_tests = process_qualification.HISTORICAL_PROCESS_V2_TESTS
    previous_known_good = process_qualification._known_good_linked_binding  # noqa: SLF001
    for name, value in _REPLACEMENTS.items():
        setattr(base, name, value)
    process_qualification.HISTORICAL_PROCESS_V2_TESTS = PROCESS_V2_TESTS
    process_qualification._known_good_linked_binding = (  # noqa: SLF001
        _inherited_known_good_linked_binding
    )
    try:
        yield
    finally:
        process_qualification._known_good_linked_binding = previous_known_good  # noqa: SLF001
        process_qualification.HISTORICAL_PROCESS_V2_TESTS = previous_tests
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
