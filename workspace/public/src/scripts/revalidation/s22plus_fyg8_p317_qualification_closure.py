#!/usr/bin/env python3
"""Create and validate P3.17 prepackaging and final closures."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import s22plus_fyg8_max77705_custom_surface_contract as surface
import s22plus_fyg8_p316_qualification_closure as base
import s22plus_fyg8_p317_overlay_contract as overlay


PREPACKAGING_SCHEMA = "s22plus_fyg8_p317_prepackaging_closure_v1"
PREPACKAGING_VERDICT = "PASS_P317_PREPACKAGING_CLOSURE_HOST_ONLY"
FINAL_SCHEMA = "s22plus_fyg8_p317_qualification_closure_v1"
FINAL_VERDICT = "PASS_P317_QUALIFICATION_CLOSURE_HOST_ONLY"
EXPECTED_MODULE_PLAN_COUNT = 69
CANDIDATE_SCHEMA = "s22plus_fyg8_p317_candidate_artifact_result_v1"
CANDIDATE_VERDICT = "PASS_P317_DETERMINISTIC_BOOT_ONLY_CANDIDATE_HOST_ONLY"
DEFAULT_INTENT = overlay.DEFAULT_INTENT
DEFAULT_USERSPACE = Path("workspace/private/outputs/s22plus_fyg8_p317/userspace")
DEFAULT_CANDIDATE_A = Path("workspace/private/outputs/s22plus_fyg8_p317/candidate-a")
DEFAULT_CANDIDATE_B = Path("workspace/private/outputs/s22plus_fyg8_p317/candidate-b")
DEFAULT_PREPACKAGING = Path(
    "workspace/private/outputs/s22plus_fyg8_p317/qualification/prepackaging-closure.json"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p317/qualification/qualification-closure.json"
)
QualificationError = base.QualificationError
_canonical = base._canonical  # noqa: SLF001
_receipt = base._receipt  # noqa: SLF001
_read_regular = base._read_regular  # noqa: SLF001
_read_json = base._read_json  # noqa: SLF001
_write_new = base._write_new  # noqa: SLF001
_tree_receipts = base._tree_receipts  # noqa: SLF001


def _requirements(exact: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_id": overlay.CONTRACT_ID,
        "run_id": exact["run_id"],
        **{
            key: exact[key]
            for key in (
                "fixed_image", "source_receipts", "generated_artifacts",
                "max77705_surface_gate", "executability_gates",
                "runtime_fixture", "late_loader_lifecycle", "envelope_fixture",
                "process_v2_adapter_fixture", "sidecar_positive_control",
                "telemetry", "observer", "packaging_requirements",
            )
        },
        "diagnostic_module": {
            "name": "s22plus_max77705_mux_diag.ko",
            "size": surface.DIAG_MODULE_IDENTITY[0],
            "sha256": surface.DIAG_MODULE_IDENTITY[1],
            "boot_ramdisk_path": "lib/modules/s22plus_max77705_mux_diag.ko",
            "early_plan_membership": False,
            "late_load_only": True,
        },
        "packaging_validator_called_before_packaging": True,
        "missing_or_failed_proof_blocks_packaging": True,
    }


def _validate_candidate_result(value: dict[str, Any], *, prepackaging_receipt: dict[str, Any]) -> None:
    construction = value.get("construction", {})
    safety = value.get("safety", {})
    if (
        value.get("schema") != CANDIDATE_SCHEMA
        or value.get("verdict") != CANDIDATE_VERDICT
        or value.get("prepackaging_closure") != prepackaging_receipt
        or construction.get("diagnostic_staged_path")
        != "lib/modules/s22plus_max77705_mux_diag.ko"
        or construction.get("diagnostic_staged_exactly_once") is not True
        or construction.get("diagnostic_absent_from_base") is not True
        or construction.get("diagnostic_absent_from_early_plan") is not True
        or safety.get("boot_only_ap") is not True
        or safety.get("fixed_p310_image") is not True
        or safety.get("custom_module_binaries_injected") != 1
        or safety.get("early_stock_module_count") != 69
        or safety.get("device_contact") is not False
    ):
        raise QualificationError("P3.17 candidate result differs")


@contextmanager
def _configured() -> Iterator[None]:
    names = (
        "overlay", "PREPACKAGING_SCHEMA", "PREPACKAGING_VERDICT",
        "FINAL_SCHEMA", "FINAL_VERDICT", "EXPECTED_MODULE_PLAN_COUNT",
        "CANDIDATE_SCHEMA", "CANDIDATE_VERDICT", "DEFAULT_INTENT",
        "DEFAULT_USERSPACE", "DEFAULT_CANDIDATE_A", "DEFAULT_CANDIDATE_B",
        "DEFAULT_PREPACKAGING", "DEFAULT_OUT", "_requirements",
        "_validate_candidate_result",
    )
    values = {name: globals()[name] for name in names}
    previous = {name: getattr(base, name) for name in names}
    for name, value in values.items():
        setattr(base, name, value)
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(base, name, value)


def create_prepackaging_value(root: Path, intent_path: Path):
    with _configured():
        return base.create_prepackaging_value(root, intent_path)


def validate_prepackaging_artifact(value, *, root: Path, intent_path: Path | None = None):  # noqa: ANN001, ANN201
    with _configured():
        return base.validate_prepackaging_artifact(value, root=root, intent_path=intent_path)


def create_final_value(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    with _configured():
        return base.create_final_value(*args, **kwargs)


def validate_qualification_artifact(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    with _configured():
        return base.validate_qualification_artifact(*args, **kwargs)


def main() -> int:
    with _configured():
        return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
