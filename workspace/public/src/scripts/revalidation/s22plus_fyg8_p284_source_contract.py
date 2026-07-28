#!/usr/bin/env python3
"""Versioned P2.84 sysfs-ingestion correction over P2.82."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

import s22plus_fyg8_p243_rpmh_dependency_audit as p243
import s22plus_fyg8_p252_source_contract as p252
import s22plus_fyg8_p282_source_contract as p282
import s22plus_fyg8_p284_contract_spec as spec


CONTRACT_ID = "s22plus-fyg8-p284-sysfs-ingestion-correction-v1"
PROFILE = spec.PROFILE
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P284-SYSFS-INGESTION-RUN-ID-V1\0"
INTENT_SCHEMA = "s22plus_fyg8_p284_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p284_candidate_identity_preimage_v1"
INTENT_VERDICT = "PASS_P284_CANDIDATE_INTENT_HOST_ONLY"
CONTRACT_SCHEMA = "s22plus_fyg8_p284_candidate_contract_v1"
CONTRACT_VERDICT = "PASS_P284_CANDIDATE_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P284_E3_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
IMPLEMENTATION_VERDICT = (
    "PASS_P284_SYSFS_INGESTION_CORRECTION_IMPLEMENTATION_HOST_ONLY"
)
SOURCE_CHECK_RUN_ID = hashlib.sha256(
    b"S22PLUS-FYG8-P284-SOURCE-CHECK-V1"
).digest()[:16]

DEFAULT_DWC3_MSM_MODULE = p282.DEFAULT_DWC3_MSM_MODULE
DEFAULT_HSPHY_MODULE = p282.DEFAULT_HSPHY_MODULE
MODULE_PLAN_COUNT = p282.MODULE_PLAN_COUNT
GENERATED_KEYS = p282.GENERATED_KEYS
GENERATED_OUTPUT_NAMES = p282.GENERATED_OUTPUT_NAMES
MATERIALIZED_FILENAMES = dict(p282.MATERIALIZED_FILENAMES)
STAGE_SEQUENCE = p282.STAGE_SEQUENCE
REACHABLE_VARIANTS = p282.REACHABLE_VARIANTS
INHERITED_ROLE_DETAILS = p282.INHERITED_ROLE_DETAILS
decoder = p282.decoder
trace_contract = p282.trace_contract

OVERLAY_SOURCE_PATHS = {
    "p284_source_contract": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p284_source_contract.py"
    ),
    "p284_contract_spec": Path(
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p284_contract_spec.py"
    ),
}
SOURCE_KEYS = frozenset((*p282.SOURCE_KEYS, *OVERLAY_SOURCE_PATHS))


class SourceContractError(ValueError):
    pass


SourceContract = p252.SourceContract
P284 = SourceContract(
    contract_id=CONTRACT_ID,
    profile=PROFILE,
    run_id_domain=RUN_ID_DOMAIN,
    stage_sequence=STAGE_SEQUENCE,
    terminal_stage=spec.TERMINAL_STAGE,
    reachable_variants=REACHABLE_VARIANTS,
    source_keys=SOURCE_KEYS,
)


def receipt(data: bytes) -> dict[str, Any]:
    return p282.receipt(data)


def require(contract_id: str | None, profile: str) -> SourceContract:
    if contract_id != CONTRACT_ID or profile != PROFILE:
        raise SourceContractError(
            f"unsupported source contract/profile: {contract_id!r}/{profile}"
        )
    return P284


def candidate_observer(run_id: bytes) -> dict[str, str]:
    return p282.candidate_observer(run_id)


def generate(root: Path | None = None) -> dict[str, bytes]:
    return p282.generate(root)


def _correct_descriptor(header: bytes) -> bytes:
    result = header
    replacements = {
        b'#define P282_ROLE_NONE_READBACK "none\\n"':
            b'#define P282_ROLE_NONE_READBACK "none"',
        b'#define P282_ROLE_PERIPHERAL_READBACK "peripheral\\n"':
            b'#define P282_ROLE_PERIPHERAL_READBACK "peripheral"',
        b'#define P282_CHILD_SUSPENDED_READBACK "suspended\\n"':
            b'#define P282_CHILD_SUSPENDED_READBACK "suspended"',
        b'#define P282_CHILD_ACTIVE_READBACK "active\\n"':
            b'#define P282_CHILD_ACTIVE_READBACK "active"',
    }
    for old, new in replacements.items():
        if result.count(old) != 1:
            raise SourceContractError(
                f"P2.84 descriptor replacement cardinality drifted: {old!r}"
            )
        result = result.replace(old, new)
    return result


def trace_descriptor_header(root: Path) -> bytes:
    return _correct_descriptor(p282.trace_descriptor_header(root))


def source_bytes(root: Path) -> dict[str, bytes]:
    result = dict(p282.source_bytes(root))
    result["trace_descriptor_header"] = _correct_descriptor(
        result["trace_descriptor_header"]
    )
    for name, path in OVERLAY_SOURCE_PATHS.items():
        result[name] = p252.p233.read_direct(
            root / path, f"P2.84 source {name}"
        )
    if set(result) != SOURCE_KEYS:
        raise SourceContractError("P2.84 source inventory changed")
    _validate_descriptor(result["trace_descriptor_header"])
    return result


def source_receipts(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    data = source_bytes(root)
    return data, {
        name: receipt(value) for name, value in sorted(data.items())
    }


def _validate_descriptor(header: bytes) -> None:
    for name, value in spec.RUNTIME_STRING_CONSTANTS:
        escaped = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
        )
        token = f'#define {name} "{escaped}"'.encode("ascii")
        if header.count(token) != 1:
            raise SourceContractError(
                f"P2.84 descriptor string {name} differs"
            )
    for name in (
        "P282_ROLE_NONE_READBACK",
        "P282_ROLE_PERIPHERAL_READBACK",
        "P282_CHILD_SUSPENDED_READBACK",
        "P282_CHILD_ACTIVE_READBACK",
    ):
        prefix = f"#define {name} ".encode("ascii")
        lines = tuple(
            line for line in header.splitlines() if line.startswith(prefix)
        )
        if len(lines) != 1 or b"\\n" in lines[0]:
            raise SourceContractError(
                f"P2.84 normalized descriptor {name} is invalid"
            )


def _audit_userspace(
    root: Path,
    generated: dict[str, bytes],
    source: dict[str, bytes],
    directory: Path,
) -> dict[str, Any]:
    for key in (
        "e3_runtime_include",
        "classifier_include",
        "p260_e3_runtime_include",
        "trace_descriptor_header",
    ):
        (directory / MATERIALIZED_FILENAMES[key]).write_bytes(source[key])
    return p252._audit_userspace(
        root,
        generated,
        directory,
        materialized_filenames=MATERIALIZED_FILENAMES,
        source_check_run_id=SOURCE_CHECK_RUN_ID,
    )


def implementation_result(root: Path) -> dict[str, Any]:
    first = generate(root)
    second = generate(root)
    if first != second:
        raise SourceContractError("P2.84 generation is not deterministic")
    historical = p282.generate(root)
    if first != historical:
        raise SourceContractError("P2.84 changed P2.82 generated kernel inputs")
    source = source_bytes(root)
    with tempfile.TemporaryDirectory(prefix="s22-p284-") as temporary:
        directory = Path(temporary)
        try:
            patch = p252._audit_patch(root, first["patch"], directory)
            userspace = _audit_userspace(root, first, source, directory)
        except p252.SourceContractError as exc:
            raise SourceContractError(str(exc)) from exc
    return {
        "schema": "s22plus_fyg8_p284_implementation_v1",
        "verdict": IMPLEMENTATION_VERDICT,
        "contract_id": CONTRACT_ID,
        "generated": {
            name: receipt(data) for name, data in sorted(first.items())
        },
        "p282_generated_byte_identical": True,
        "patch": patch,
        "linked_userspace": userspace,
        "trace_descriptor": receipt(source["trace_descriptor_header"]),
        "runtime_authority": dict(spec.RUNTIME_AUTHORITY),
        "descriptor": {
            "step_count": len(spec.STEPS),
            "gate_count": spec.GATE_COUNT,
            "terminal_ordinal": spec.TERMINAL_ORDINAL,
            "terminal_stage": spec.TERMINAL_STAGE,
            "diagnostic_detail_count": len(spec.DIAGNOSTIC_DETAILS),
        },
        "safety": {
            "host_only": True,
            "kernel_built": False,
            "image_built": False,
            "candidate_created": False,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        },
    }


def validate_reachable_records(run_id: bytes) -> dict[str, Any]:
    return p282.validate_reachable_records(run_id)


def linked_table_bytes() -> dict[str, bytes]:
    return p282.linked_table_bytes()


def audit_linked_tables(actual: dict[str, bytes]) -> dict[str, Any]:
    return p282.audit_linked_tables(actual)


LINKED_VALIDATOR_SYMBOLS = p282.LINKED_VALIDATOR_SYMBOLS


def main() -> int:
    try:
        result = implementation_result(p243.repo_root())
    except (SourceContractError, p252.SourceContractError, OSError) as exc:
        print(json.dumps({"verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
