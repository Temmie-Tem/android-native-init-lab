#!/usr/bin/env python3
"""Create and validate P3.18 prepackaging and final closures."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import s22plus_fyg8_p316_qualification_closure as base
import s22plus_fyg8_p318_overlay_contract as overlay


PREPACKAGING_SCHEMA = "s22plus_fyg8_p318_prepackaging_closure_v1"
PREPACKAGING_VERDICT = "PASS_P318_PREPACKAGING_CLOSURE_HOST_ONLY"
FINAL_SCHEMA = "s22plus_fyg8_p318_qualification_closure_v1"
FINAL_VERDICT = "PASS_P318_QUALIFICATION_CLOSURE_HOST_ONLY"
EXPECTED_MODULE_PLAN_COUNT = 70
CANDIDATE_SCHEMA = "s22plus_fyg8_p318_candidate_artifact_result_v1"
CANDIDATE_VERDICT = "PASS_P318_DETERMINISTIC_BOOT_ONLY_CANDIDATE_HOST_ONLY"
DEFAULT_INTENT = overlay.DEFAULT_INTENT
DEFAULT_USERSPACE = Path("workspace/private/outputs/s22plus_fyg8_p318/userspace")
DEFAULT_CANDIDATE_A = Path("workspace/private/outputs/s22plus_fyg8_p318/candidate-a")
DEFAULT_CANDIDATE_B = Path("workspace/private/outputs/s22plus_fyg8_p318/candidate-b")
DEFAULT_PREPACKAGING = Path(
    "workspace/private/outputs/s22plus_fyg8_p318/qualification/prepackaging-closure.json"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p318/qualification/qualification-closure.json"
)
QualificationError = base.QualificationError
_read_json = base._read_json  # noqa: SLF001
_tree_receipts = base._tree_receipts  # noqa: SLF001


def _requirements(exact: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_id": overlay.CONTRACT_ID,
        "run_id": exact["run_id"],
        **{
            key: exact[key]
            for key in (
                "fixed_image", "source_receipts", "generated_artifacts",
                "module_builds", "module_identities", "runtime_qualification",
                "envelope_qualification", "native_preimages",
                "process_v2_adapter_fixture", "runtime_parser",
                "topology_receipt", "telemetry", "observer",
                "packaging_requirements",
            )
        },
        "latch_module": exact["module_identities"]["early_latch"],
        "diagnostic_module": exact["module_identities"]["late_diagnostic"],
        "packaging_validator_called_before_packaging": True,
        "missing_or_failed_proof_blocks_packaging": True,
    }


def _validate_candidate_result(
    value: dict[str, Any], *, prepackaging_receipt: dict[str, Any]
) -> None:
    construction = value.get("construction", {})
    safety = value.get("safety", {})
    identities = value.get("candidate_contract", {}).get("module_identities", {})
    if (
        value.get("schema") != CANDIDATE_SCHEMA
        or value.get("verdict") != CANDIDATE_VERDICT
        or value.get("prepackaging_closure") != prepackaging_receipt
        or construction.get("latch_staged_path")
        != "lib/modules/s22plus_dwc3_event_latch.ko"
        or construction.get("diagnostic_staged_path")
        != "lib/modules/s22plus_max77705_mux_diag_p318.ko"
        or construction.get("latch_staged_exactly_once") is not True
        or construction.get("diagnostic_staged_exactly_once") is not True
        or construction.get("both_custom_modules_absent_from_base") is not True
        or construction.get("diagnostic_absent_from_early_plan") is not True
        or construction.get("old_p317_diagnostic_absent") is not True
        or construction.get("latch_module") != {
            key: identities.get("early_latch", {}).get(key)
            for key in ("size", "sha256")
        }
        or construction.get("diagnostic_module") != {
            key: identities.get("late_diagnostic", {}).get(key)
            for key in ("size", "sha256")
        }
        or safety.get("boot_only_ap") is not True
        or safety.get("fixed_p310_image") is not True
        or safety.get("custom_module_binaries_injected") != 2
        or safety.get("effective_early_module_count") != 70
        or safety.get("device_contact") is not False
    ):
        raise QualificationError("P3.18 candidate result differs")


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
