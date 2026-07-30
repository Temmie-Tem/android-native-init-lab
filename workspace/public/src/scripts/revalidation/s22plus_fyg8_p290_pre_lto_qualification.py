#!/usr/bin/env python3
"""Pre-Full-LTO qualification for the P2.90 park-repair successor."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import importlib
from pathlib import Path
from typing import Any, Iterator

import build_s22plus_fyg8_p290_candidate as candidate_builder
import s22plus_fyg8_p288_pre_lto_qualification as inherited
import s22plus_fyg8_p290_candidate_contract as candidate_contract
import s22plus_fyg8_p290_contract_spec as spec
import s22plus_fyg8_p290_e2_stock_closure as closure
import s22plus_fyg8_p290_source_contract as p290
import s22plus_fyg8_p290_userspace_build as userspace


# Generic qualification discovery reads this attribute.
p286 = p290

SCHEMA = "s22plus_fyg8_p290_pre_lto_qualification_v1"
VERDICT = "PASS_P290_PRE_FULL_LTO_QUALIFICATION_HOST_ONLY"
LINKED_META_SCHEMA = "s22plus_fyg8_p290_linked_audit_meta_v1"
LINKED_META_VERDICT = "PASS_P290_LINKED_AUDIT_META_HOST_ONLY"
LINKED_AUDIT_MODULE_NAME = "s22plus_fyg8_p290_linked_audit"
LINKED_AUDIT_TEST = Path("tests/test_s22plus_fyg8_p290_contract.py")
LINKED_AUDIT_PATH = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p290_linked_audit.py"
)
DEFAULT_LINKED_AUDIT_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p290_pre_lto/"
    "linked-audit-meta.json"
)
DEFAULT_INGESTION_RESULT = inherited.DEFAULT_INGESTION_RESULT
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p290_pre_lto/"
    "qualification.json"
)
FOCUSED_TESTS = (
    *tuple(
        path
        for path in inherited.FOCUSED_TESTS
        if path != Path("tests/test_s22plus_fyg8_p288_contract.py")
    ),
    Path("tests/test_s22plus_fyg8_p290_contract.py"),
    Path("tests/test_s22plus_fyg8_p290_predesign_audit.py"),
)
P290_GATE_NAME = "21-checked-park-and-adjacent-corridor"
GATE_IMPLEMENTATION_SOURCES = {
    **inherited.GATE_IMPLEMENTATION_SOURCES,
    "closure": (
        inherited.base.base.SCRIPT_DIR
        / "s22plus_fyg8_p290_e2_stock_closure.py"
    ),
    "p290_qualification": Path(__file__).resolve(),
    "p290_source_contract": (
        inherited.base.base.SCRIPT_DIR
        / "s22plus_fyg8_p290_source_contract.py"
    ),
    "p290_contract_spec": (
        inherited.base.base.SCRIPT_DIR
        / "s22plus_fyg8_p290_contract_spec.py"
    ),
    "p290_position_model": (
        inherited.base.base.SCRIPT_DIR
        / "s22plus_fyg8_p290_latest_stage_model.py"
    ),
    "p290_linked_audit": (
        inherited.base.base.SCRIPT_DIR
        / "s22plus_fyg8_p290_linked_audit.py"
    ),
    "p290_candidate_builder": (
        inherited.base.base.SCRIPT_DIR
        / "build_s22plus_fyg8_p290_candidate.py"
    ),
    "p290_userspace_builder": (
        inherited.base.base.SCRIPT_DIR
        / "s22plus_fyg8_p290_userspace_build.py"
    ),
    "p290_decoder": (
        inherited.base.base.SCRIPT_DIR
        / "s22plus_fyg8_p290_e1_decoder.py"
    ),
}
QualificationError = inherited.QualificationError
_BASE_GATE_MATRIX = inherited._BASE_GATE_MATRIX


class _QualificationSourceContractAdapter:
    DEFAULT_DWC3_MSM_MODULE = (
        inherited.QUALIFICATION_SOURCE_CONTRACT.DEFAULT_DWC3_MSM_MODULE
    )
    DEFAULT_HSPHY_MODULE = (
        inherited.QUALIFICATION_SOURCE_CONTRACT.DEFAULT_HSPHY_MODULE
    )

    def __getattr__(self, name: str):
        return getattr(p290, name)


QUALIFICATION_SOURCE_CONTRACT = _QualificationSourceContractAdapter()


def _load_linked_audit_module():
    try:
        module = importlib.import_module(LINKED_AUDIT_MODULE_NAME)
    except (ImportError, OSError) as exc:
        raise QualificationError(
            "P2.90 linked-audit module is unavailable"
        ) from exc
    if (
        getattr(module, "EXPECTED_SOURCE_CONTRACT_ID", None)
        != p290.CONTRACT_ID
        or getattr(module, "ADAPTER_ID", None)
        != "s22plus-fyg8-p290-linked-audit-v1"
    ):
        raise QualificationError("P2.90 linked-audit identity drifted")
    return module


def create_linked_audit_receipt(root: Path) -> dict[str, Any]:
    module = _load_linked_audit_module()
    test = inherited.base.base._run_test_command(  # noqa: SLF001
        root, (LINKED_AUDIT_TEST,), "P2.90 linked audit"
    )
    payload = inherited.base.base._portable_repo_paths(  # noqa: SLF001
        root,
        {
            "schema": LINKED_META_SCHEMA,
            "verdict": LINKED_META_VERDICT,
            "source_contract_id": p290.CONTRACT_ID,
            "adapter_id": module.ADAPTER_ID,
            "module": inherited.base.base._material(  # noqa: SLF001
                root / LINKED_AUDIT_PATH,
                "P2.90 linked-audit module",
            ),
            "known_good": inherited.base.base._known_good_linked_binding(  # noqa: SLF001
                root
            ),
            "test": test,
            "verified": True,
        },
    )
    return {
        **payload,
        "payload_sha256": hashlib.sha256(
            inherited.base.base._canonical(payload)  # noqa: SLF001
        ).hexdigest(),
    }


def _verify_linked_audit_receipt(path: Path) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    module = _load_linked_audit_module()
    value, receipt = inherited.base.base._load_json(  # noqa: SLF001
        path, "P2.90 linked-audit receipt"
    )
    if set(value) != {
        "adapter_id",
        "known_good",
        "module",
        "payload_sha256",
        "schema",
        "source_contract_id",
        "test",
        "verified",
        "verdict",
    }:
        raise QualificationError(
            "P2.90 linked-audit receipt shape drifted"
        )
    payload = dict(value)
    digest = payload.pop("payload_sha256", None)
    if digest != hashlib.sha256(
        inherited.base.base._canonical(payload)  # noqa: SLF001
    ).hexdigest():
        raise QualificationError(
            "P2.90 linked-audit receipt digest mismatch"
        )
    expected_module = inherited.base.base._repo_material(  # noqa: SLF001
        root,
        root / LINKED_AUDIT_PATH,
        "P2.90 linked-audit module",
    )
    test = value.get("test")
    expected_command = [
        inherited.base.base.sys.executable,
        "-m",
        "unittest",
        "-v",
        str(LINKED_AUDIT_TEST),
    ]
    expected_sources = {
        str(LINKED_AUDIT_TEST): inherited.base.base._repo_material(  # noqa: SLF001
            root,
            root / LINKED_AUDIT_TEST,
            "P2.90 linked-audit test",
        )
    }
    if (
        value.get("schema") != LINKED_META_SCHEMA
        or value.get("verdict") != LINKED_META_VERDICT
        or value.get("source_contract_id") != p290.CONTRACT_ID
        or value.get("adapter_id") != module.ADAPTER_ID
        or value.get("module") != expected_module
        or value.get("known_good")
        != inherited.base.base._known_good_linked_binding(root)  # noqa: SLF001
        or value.get("verified") is not True
        or not isinstance(test, dict)
        or set(test)
        != {
            "command",
            "output_sha256",
            "sources",
            "test_count",
            "verified",
        }
        or test.get("command") != expected_command
        or test.get("sources") != expected_sources
        or isinstance(test.get("test_count"), bool)
        or not isinstance(test.get("test_count"), int)
        or test["test_count"] < 1
        or not isinstance(test.get("output_sha256"), str)
        or inherited.base.base.HEX64_RE.fullmatch(  # noqa: SLF001
            test["output_sha256"]
        )
        is None
        or test.get("verified") is not True
    ):
        raise QualificationError(
            "P2.90 linked-audit receipt is stale"
        )
    return {
        **inherited.base.base._result_binding(  # noqa: SLF001
            root, path, receipt, "P2.90 linked audit"
        ),
        "semantics": {
            "adapter_id": module.ADAPTER_ID,
            "source_contract_id": p290.CONTRACT_ID,
            "test_count": test["test_count"],
            "output_sha256": test["output_sha256"],
            "known_good_vmlinux_sha256": value["known_good"][
                "vmlinux"
            ]["sha256"],
            "known_good_config_sha256": value["known_good"][
                "config"
            ]["sha256"],
        },
        "verified": True,
    }


def _gate_matrix(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        *_BASE_GATE_MATRIX(evidence),
        {
            "ordinal": 21,
            "name": P290_GATE_NAME,
            "evidence": ["implementation"],
            "verified": True,
        },
    ]


_REPLACEMENTS = {
    "candidate_builder": candidate_builder,
    "candidate_contract": candidate_contract,
    "spec": spec,
    "closure": closure,
    "p288": p290,
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
    "P288_GATE_NAME": P290_GATE_NAME,
    "GATE_IMPLEMENTATION_SOURCES": GATE_IMPLEMENTATION_SOURCES,
    "QUALIFICATION_SOURCE_CONTRACT": QUALIFICATION_SOURCE_CONTRACT,
    "_load_linked_audit_module": _load_linked_audit_module,
    "create_linked_audit_receipt": create_linked_audit_receipt,
    "_verify_linked_audit_receipt": _verify_linked_audit_receipt,
    "_gate_matrix": _gate_matrix,
}


@contextmanager
def _context() -> Iterator[None]:
    previous = {
        name: getattr(inherited, name) for name in _REPLACEMENTS
    }
    for name, value in _REPLACEMENTS.items():
        setattr(inherited, name, value)
    inherited._configure()  # noqa: SLF001
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(inherited, name, value)
        inherited._configure()  # noqa: SLF001


def create(**kwargs):  # noqa: ANN003, ANN201
    with _context():
        return inherited.create(**kwargs)


def verify_receipt(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    with _context():
        result = dict(inherited.verify_receipt(*args, **kwargs))
    result["gate_count"] = 21
    return result


def parse_args(argv: list[str] | None = None):
    with _context():
        return inherited.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    with _context():
        return inherited.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
