#!/usr/bin/env python3
"""Qualify the P3.09 tracefs-ABI correction as a host-only prerequisite."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import s22plus_fyg8_p308_overlay_contract as parent
import s22plus_fyg8_p309_generator as generator
import s22plus_fyg8_p309_tracefs_abi_audit as abi_audit


SCHEMA = "s22plus_fyg8_p309_host_contract_v1"
CONTRACT_ID = "s22plus-fyg8-p309-tracefs-abi-correction-host-only-v1"
VERDICT = "PASS_P309_TRACEFS_ABI_CORRECTION_PREREQUISITE_HOST_ONLY"
PREFIX = Path("workspace/public/src/scripts/revalidation")
SOURCE_PATHS = {
    "p309_descriptor_transform": PREFIX / "s22plus_fyg8_p309_descriptor_transform.py",
    "p309_generator": PREFIX / "s22plus_fyg8_p309_generator.py",
    "p309_tracefs_abi_audit": PREFIX / "s22plus_fyg8_p309_tracefs_abi_audit.py",
    "p309_host_contract": PREFIX / "s22plus_fyg8_p309_host_contract.py",
}


class ContractError(ValueError):
    pass


def _read(path: Path, label: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"{label} is missing or indirect")
    return path.read_bytes()


def _receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def verify(root: Path) -> dict[str, Any]:
    parent_value = parent.verify_intent(root, root / parent.DEFAULT_INTENT)
    if (
        parent_value.get("userspace_overlay_contract_id") != parent.CONTRACT_ID
        or parent_value.get("verified") is not True
    ):
        raise ContractError("P3.09 immutable P3.08 parent differs")
    generated = generator.generate_bytes(
        root,
        run_id=bytes.fromhex(parent_value["run_id"]),
        unsat_tag=bytes.fromhex(parent_value["unsat_tag_hex"]),
        profile=parent_value["profile"],
    )
    trace = abi_audit.audit(root, generated["trace_descriptor_header"])
    sources = {
        key: {"path": path.as_posix(), **_receipt(_read(root / path, key))}
        for key, path in sorted(SOURCE_PATHS.items())
    }
    artifacts = {
        key: _receipt(data) for key, data in sorted(generated.items())
    }
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "verdict": VERDICT,
        "target": parent.TARGET,
        "profile": parent.PROFILE,
        "parent_contract_id": parent.CONTRACT_ID,
        "parent_intent": {
            "path": parent.DEFAULT_INTENT.as_posix(),
            **_receipt(_read(root / parent.DEFAULT_INTENT, "P3.08 parent intent")),
        },
        "source_receipts": sources,
        "generated_artifacts": artifacts,
        "delta_keys": sorted(generator.DELTA_KEYS),
        "tracefs_abi_cross_authority": trace,
        "classification": "TRACEFS_ABI_CROSS_AUTHORITY_FAILURE",
        "scope": {
            "p308_source_or_output_modified": False,
            "descriptor_change": "rc=%w21:s32 -> rc=%x21:s32",
            "runtime_changed": False,
            "kernel_changed": False,
            "module_plan_changed": False,
            "carrier_changed": False,
            "full_lto_required": False,
            "device_contact": False,
        },
        "execution": {
            "p308_replay_permitted": False,
            "candidate_execution_permitted": False,
            "carrier_v2_required_before_next_telemetry_rich_candidate": True,
        },
        "verified": True,
    }


def main() -> int:
    try:
        result = verify(Path(__file__).resolve().parents[5])
    except (
        ContractError,
        parent.OverlayContractError,
        generator.GeneratorError,
        abi_audit.AuditError,
        OSError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
