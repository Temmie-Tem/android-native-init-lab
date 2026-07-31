#!/usr/bin/env python3
"""Pre-Full-LTO qualification for P2.94 DWC3 value telemetry."""

from __future__ import annotations

from contextlib import contextmanager
import importlib
from pathlib import Path
from typing import Iterator

import build_s22plus_fyg8_p294_candidate as candidate_builder
import s22plus_fyg8_p290_pre_lto_qualification as base
import s22plus_fyg8_p294_candidate_contract as candidate_contract
import s22plus_fyg8_p294_e2_stock_closure as closure
import s22plus_fyg8_p294_source_contract as p294
import s22plus_fyg8_p294_telemetry_spec as spec
import s22plus_fyg8_p294_userspace_build as userspace


p286 = p294
SCHEMA = "s22plus_fyg8_p294_pre_lto_qualification_v1"
VERDICT = "PASS_P294_PRE_FULL_LTO_QUALIFICATION_HOST_ONLY"
LINKED_META_SCHEMA = "s22plus_fyg8_p294_linked_audit_meta_v1"
LINKED_META_VERDICT = "PASS_P294_LINKED_AUDIT_META_HOST_ONLY"
LINKED_AUDIT_MODULE_NAME = "s22plus_fyg8_p294_linked_audit"
LINKED_AUDIT_TEST = Path("tests/test_s22plus_fyg8_p294_contract.py")
LINKED_AUDIT_PATH = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_p294_linked_audit.py"
)
DEFAULT_LINKED_AUDIT_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p294_pre_lto/linked-audit-meta.json"
)
DEFAULT_INGESTION_RESULT = base.DEFAULT_INGESTION_RESULT
DEFAULT_USERSPACE_RESULT = userspace.DEFAULT_OUT / "userspace-result.json"
DEFAULT_LIFECYCLE_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p294_pre_lto/"
    "p280-trace-lifecycle-current/result.json"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p294_pre_lto/qualification.json"
)
FOCUSED_TESTS = (
    *tuple(
        path
        for path in base.FOCUSED_TESTS
        if path
        not in {
            Path("tests/test_s22plus_fyg8_p290_contract.py"),
            Path("tests/test_s22plus_fyg8_p290_predesign_audit.py"),
        }
    ),
    Path("tests/test_s22plus_fyg8_p294_contract.py"),
    Path(
        "workspace/public/src/scripts/revalidation/"
        "test_s22plus_fyg8_p294_telemetry.py"
    ),
)
P294_GATE_NAME = "22-dwc3-value-telemetry"
GATE_IMPLEMENTATION_SOURCES = {
    **base.GATE_IMPLEMENTATION_SOURCES,
    "closure": Path(__file__).with_name("s22plus_fyg8_p294_e2_stock_closure.py"),
    "p294_qualification": Path(__file__).resolve(),
    "p294_source_contract": Path(__file__).with_name("s22plus_fyg8_p294_source_contract.py"),
    "p294_telemetry_spec": Path(__file__).with_name("s22plus_fyg8_p294_telemetry_spec.py"),
    "p294_telemetry_closure": Path(__file__).with_name("s22plus_fyg8_p294_telemetry_closure.py"),
    "p294_identity_tiers": Path(__file__).with_name("s22plus_fyg8_p294_identity_tiers.py"),
    "p294_linked_audit": Path(__file__).with_name("s22plus_fyg8_p294_linked_audit.py"),
    "p294_candidate_builder": Path(__file__).with_name("build_s22plus_fyg8_p294_candidate.py"),
    "p294_userspace_builder": Path(__file__).with_name("s22plus_fyg8_p294_userspace_build.py"),
    "p294_decoder": Path(__file__).with_name("s22plus_fyg8_p294_telemetry_decoder.py"),
}
QualificationError = base.QualificationError


class _QualificationSourceContractAdapter:
    DEFAULT_DWC3_MSM_MODULE = base.QUALIFICATION_SOURCE_CONTRACT.DEFAULT_DWC3_MSM_MODULE
    DEFAULT_HSPHY_MODULE = base.QUALIFICATION_SOURCE_CONTRACT.DEFAULT_HSPHY_MODULE

    def __getattr__(self, name: str):
        return getattr(p294, name)


QUALIFICATION_SOURCE_CONTRACT = _QualificationSourceContractAdapter()


def _load_linked_audit_module():
    try:
        module = importlib.import_module(LINKED_AUDIT_MODULE_NAME)
    except (ImportError, OSError) as exc:
        raise QualificationError("P2.94 linked-audit module is unavailable") from exc
    if (
        getattr(module, "EXPECTED_SOURCE_CONTRACT_ID", None) != p294.CONTRACT_ID
        or getattr(module, "ADAPTER_ID", None) != "s22plus-fyg8-p294-linked-audit-v1"
    ):
        raise QualificationError("P2.94 linked-audit identity drifted")
    return module


def _configure() -> None:
    base.candidate_builder = candidate_builder
    base.candidate_contract = candidate_contract
    base.spec = spec
    base.closure = closure
    base.p290 = p294
    base.userspace = userspace
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT
    base.LINKED_META_SCHEMA = LINKED_META_SCHEMA
    base.LINKED_META_VERDICT = LINKED_META_VERDICT
    base.LINKED_AUDIT_MODULE_NAME = LINKED_AUDIT_MODULE_NAME
    base.LINKED_AUDIT_TEST = LINKED_AUDIT_TEST
    base.LINKED_AUDIT_PATH = LINKED_AUDIT_PATH
    base.DEFAULT_LINKED_AUDIT_RESULT = DEFAULT_LINKED_AUDIT_RESULT
    base.DEFAULT_OUT = DEFAULT_OUT
    base.FOCUSED_TESTS = FOCUSED_TESTS
    base.P290_GATE_NAME = P294_GATE_NAME
    base.GATE_IMPLEMENTATION_SOURCES = GATE_IMPLEMENTATION_SOURCES
    base.QUALIFICATION_SOURCE_CONTRACT = QUALIFICATION_SOURCE_CONTRACT
    base._load_linked_audit_module = _load_linked_audit_module  # noqa: SLF001
    base._REPLACEMENTS = {  # noqa: SLF001
        "candidate_builder": candidate_builder,
        "candidate_contract": candidate_contract,
        "spec": spec,
        "closure": closure,
        "p288": p294,
        "userspace": userspace,
        "SCHEMA": SCHEMA,
        "VERDICT": VERDICT,
        "LINKED_META_SCHEMA": LINKED_META_SCHEMA,
        "LINKED_META_VERDICT": LINKED_META_VERDICT,
        "LINKED_AUDIT_MODULE_NAME": LINKED_AUDIT_MODULE_NAME,
        "LINKED_AUDIT_TEST": LINKED_AUDIT_TEST,
        "DEFAULT_LINKED_AUDIT_RESULT": DEFAULT_LINKED_AUDIT_RESULT,
        "DEFAULT_OUT": DEFAULT_OUT,
        "FOCUSED_TESTS": FOCUSED_TESTS,
        "P288_GATE_NAME": P294_GATE_NAME,
        "GATE_IMPLEMENTATION_SOURCES": GATE_IMPLEMENTATION_SOURCES,
        "QUALIFICATION_SOURCE_CONTRACT": QUALIFICATION_SOURCE_CONTRACT,
        "_load_linked_audit_module": _load_linked_audit_module,
        "create_linked_audit_receipt": base.create_linked_audit_receipt,
        "_verify_linked_audit_receipt": base._verify_linked_audit_receipt,  # noqa: SLF001
        "_gate_matrix": base._gate_matrix,  # noqa: SLF001
    }


@contextmanager
def _context() -> Iterator[None]:
    _configure()
    inherited_defaults = base.inherited.base.base
    previous_defaults = {
        "DEFAULT_USERSPACE_RESULT": inherited_defaults.DEFAULT_USERSPACE_RESULT,
        "DEFAULT_LIFECYCLE_RESULT": inherited_defaults.DEFAULT_LIFECYCLE_RESULT,
    }
    inherited_defaults.DEFAULT_USERSPACE_RESULT = DEFAULT_USERSPACE_RESULT
    inherited_defaults.DEFAULT_LIFECYCLE_RESULT = DEFAULT_LIFECYCLE_RESULT
    try:
        yield
    finally:
        for name, value in previous_defaults.items():
            setattr(inherited_defaults, name, value)


def create(**kwargs):  # noqa: ANN003, ANN201
    with _context():
        return base.create(**kwargs)


def verify_receipt(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    with _context():
        return base.verify_receipt(*args, **kwargs)


def _argv_with_source(argv: list[str] | None) -> list[str]:
    values = [] if argv is None else list(argv)
    if not any(
        value == "--source" or value.startswith("--source=")
        for value in values
    ):
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
