#!/usr/bin/env python3
"""Pre-Full-LTO qualification for the P2.88 position successor."""

from __future__ import annotations

import hashlib
import importlib
from pathlib import Path
from typing import Any

import build_s22plus_fyg8_p288_candidate as candidate_builder
import s22plus_fyg8_p286_pre_lto_qualification as base
import s22plus_fyg8_p288_candidate_contract as candidate_contract
import s22plus_fyg8_p288_contract_spec as spec
import s22plus_fyg8_p288_e2_stock_closure as closure
import s22plus_fyg8_p288_source_contract as p288
import s22plus_fyg8_p288_userspace_build as userspace


# The generic qualification discovery currently looks for this attribute.
p286 = p288

SCHEMA = "s22plus_fyg8_p288_pre_lto_qualification_v1"
VERDICT = "PASS_P288_PRE_FULL_LTO_QUALIFICATION_HOST_ONLY"
LINKED_META_SCHEMA = "s22plus_fyg8_p288_linked_audit_meta_v1"
LINKED_META_VERDICT = "PASS_P288_LINKED_AUDIT_META_HOST_ONLY"
LINKED_AUDIT_MODULE_NAME = "s22plus_fyg8_p288_linked_audit"
LINKED_AUDIT_TEST = Path("tests/test_s22plus_fyg8_p288_contract.py")
DEFAULT_LINKED_AUDIT_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p288_pre_lto/"
    "linked-audit-meta.json"
)
DEFAULT_INGESTION_RESULT = base.DEFAULT_INGESTION_RESULT
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p288_pre_lto/"
    "qualification.json"
)
FOCUSED_TESTS = (
    *base.FOCUSED_TESTS,
    Path("tests/test_s22plus_fyg8_p288_contract.py"),
)
P288_GATE_NAME = "21-pair-position-and-silence-park"
GATE_IMPLEMENTATION_SOURCES = {
    **base.GATE_IMPLEMENTATION_SOURCES,
    "closure": (
        base.base.SCRIPT_DIR / "s22plus_fyg8_p288_e2_stock_closure.py"
    ),
    "p288_qualification": Path(__file__).resolve(),
    "p288_source_contract": (
        base.base.SCRIPT_DIR / "s22plus_fyg8_p288_source_contract.py"
    ),
    "p288_contract_spec": (
        base.base.SCRIPT_DIR / "s22plus_fyg8_p288_contract_spec.py"
    ),
    "p288_position_model": (
        base.base.SCRIPT_DIR
        / "s22plus_fyg8_p288_latest_stage_model.py"
    ),
    "p288_linked_audit": (
        base.base.SCRIPT_DIR / "s22plus_fyg8_p288_linked_audit.py"
    ),
    "p288_candidate_builder": (
        base.base.SCRIPT_DIR / "build_s22plus_fyg8_p288_candidate.py"
    ),
    "p288_userspace_builder": (
        base.base.SCRIPT_DIR / "s22plus_fyg8_p288_userspace_build.py"
    ),
    "p288_decoder": (
        base.base.SCRIPT_DIR / "s22plus_fyg8_p288_e1_decoder.py"
    ),
}
QualificationError = base.QualificationError
_BASE_GATE_MATRIX = base._gate_matrix


class _QualificationSourceContractAdapter:
    """Expose the inherited module paths without changing P2.88 identity."""

    DEFAULT_DWC3_MSM_MODULE = base.p286.DEFAULT_DWC3_MSM_MODULE
    DEFAULT_HSPHY_MODULE = base.p286.DEFAULT_HSPHY_MODULE

    def __getattr__(self, name: str):
        return getattr(p288, name)


QUALIFICATION_SOURCE_CONTRACT = _QualificationSourceContractAdapter()


def _load_linked_audit_module():
    try:
        module = importlib.import_module(LINKED_AUDIT_MODULE_NAME)
    except (ImportError, OSError) as exc:
        raise QualificationError(
            "P2.88 linked-audit module is unavailable"
        ) from exc
    if (
        getattr(module, "EXPECTED_SOURCE_CONTRACT_ID", None)
        != p288.CONTRACT_ID
        or getattr(module, "ADAPTER_ID", None)
        != "s22plus-fyg8-p288-linked-audit-v1"
    ):
        raise QualificationError("P2.88 linked-audit identity drifted")
    return module


def create_linked_audit_receipt(root: Path) -> dict[str, Any]:
    _configure()
    module = _load_linked_audit_module()
    test = base.base._run_test_command(
        root, (LINKED_AUDIT_TEST,), "P2.88 linked audit"
    )
    payload = base.base._portable_repo_paths(
        root,
        {
            "schema": LINKED_META_SCHEMA,
            "verdict": LINKED_META_VERDICT,
            "source_contract_id": p288.CONTRACT_ID,
            "adapter_id": module.ADAPTER_ID,
            "module": base.base._material(
                root
                / "workspace/public/src/scripts/revalidation/"
                "s22plus_fyg8_p288_linked_audit.py",
                "P2.88 linked-audit module",
            ),
            "known_good": base.base._known_good_linked_binding(root),
            "test": test,
            "verified": True,
        },
    )
    return {
        **payload,
        "payload_sha256": hashlib.sha256(
            base.base._canonical(payload)
        ).hexdigest(),
    }


def _verify_linked_audit_receipt(path: Path) -> dict[str, Any]:
    _configure()
    root = candidate_contract.intent.repo_root()
    module = _load_linked_audit_module()
    value, receipt = base.base._load_json(
        path, "P2.88 linked-audit receipt"
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
            "P2.88 linked-audit receipt shape drifted"
        )
    payload = dict(value)
    digest = payload.pop("payload_sha256", None)
    if digest != hashlib.sha256(
        base.base._canonical(payload)
    ).hexdigest():
        raise QualificationError(
            "P2.88 linked-audit receipt digest mismatch"
        )
    expected_module = base.base._repo_material(
        root,
        root
        / "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p288_linked_audit.py",
        "P2.88 linked-audit module",
    )
    test = value.get("test")
    expected_command = [
        base.base.sys.executable,
        "-m",
        "unittest",
        "-v",
        str(LINKED_AUDIT_TEST),
    ]
    expected_sources = {
        str(LINKED_AUDIT_TEST): base.base._repo_material(
            root,
            root / LINKED_AUDIT_TEST,
            "P2.88 linked-audit test",
        )
    }
    if (
        value.get("schema") != LINKED_META_SCHEMA
        or value.get("verdict") != LINKED_META_VERDICT
        or value.get("source_contract_id") != p288.CONTRACT_ID
        or value.get("adapter_id") != module.ADAPTER_ID
        or value.get("module") != expected_module
        or value.get("known_good")
        != base.base._known_good_linked_binding(root)
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
        or base.base.HEX64_RE.fullmatch(test["output_sha256"])
        is None
        or test.get("verified") is not True
    ):
        raise QualificationError(
            "P2.88 linked-audit receipt is stale"
        )
    return {
        **base.base._result_binding(
            root, path, receipt, "P2.88 linked audit"
        ),
        "semantics": {
            "adapter_id": module.ADAPTER_ID,
            "source_contract_id": p288.CONTRACT_ID,
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
    rows = _BASE_GATE_MATRIX(evidence)
    return [
        *rows,
        {
            "ordinal": 21,
            "name": P288_GATE_NAME,
            "evidence": ["implementation"],
            "verified": True,
        },
    ]


def _configure() -> None:
    candidate_contract._configure()
    userspace._configure()
    base.candidate_builder = candidate_builder
    base.candidate_contract = candidate_contract
    base.spec = spec
    base.closure = closure
    base.p286 = QUALIFICATION_SOURCE_CONTRACT
    base.userspace = userspace
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT
    base.LINKED_META_SCHEMA = LINKED_META_SCHEMA
    base.LINKED_META_VERDICT = LINKED_META_VERDICT
    base.LINKED_AUDIT_MODULE_NAME = LINKED_AUDIT_MODULE_NAME
    base.LINKED_AUDIT_TEST = LINKED_AUDIT_TEST
    base.DEFAULT_LINKED_AUDIT_RESULT = DEFAULT_LINKED_AUDIT_RESULT
    base.DEFAULT_OUT = DEFAULT_OUT
    base.FOCUSED_TESTS = FOCUSED_TESTS
    base.GATE_IMPLEMENTATION_SOURCES = dict(
        GATE_IMPLEMENTATION_SOURCES
    )
    base._load_linked_audit_module = _load_linked_audit_module
    base.create_linked_audit_receipt = create_linked_audit_receipt
    base._verify_linked_audit_receipt = (
        _verify_linked_audit_receipt
    )
    base._gate_matrix = _gate_matrix


def __getattr__(name: str):
    _configure()
    return getattr(base, name)


def create(**kwargs):  # noqa: ANN003, ANN201
    _configure()
    return base.create(**kwargs)


def verify_receipt(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    _configure()
    result = dict(base.verify_receipt(*args, **kwargs))
    result["gate_count"] = 21
    return result


def parse_args(argv: list[str] | None = None):
    _configure()
    return base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
