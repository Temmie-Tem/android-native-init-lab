#!/usr/bin/env python3
"""Bind the P3.10 Carrier v2 payload identity."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import stat
from typing import Any, Mapping

import s22plus_fyg8_p300_source_contract as inherited_contract
import s22plus_fyg8_p310_carrier_model as carrier
import s22plus_fyg8_p310_generator as generator


SCHEMA = "s22plus_fyg8_p310_payload_identity_v1"
PROFILE = "E2"
SOURCE_CHECK_RUN_ID = hashlib.sha256(b"S22PLUS-FYG8-P310-SOURCE-CHECK-V1").digest()[:16]
SOURCE_CHECK_UNSAT_TAG = carrier.unsat_record(PROFILE, SOURCE_CHECK_RUN_ID)[len(carrier.UNSAT_FAMILY) :]
PREFIX = Path("workspace/public/src/scripts/revalidation")
SCRIPTS_DIRECTORY = Path(__file__).resolve().parent
DIRECT_PATHS = {
    "p310_carrier_model": PREFIX / "s22plus_fyg8_p310_carrier_model.py",
    "p310_carrier_transform": PREFIX / "s22plus_fyg8_p310_carrier_transform.py",
    "p310_generator": PREFIX / "s22plus_fyg8_p310_generator.py",
    "p310_telemetry_decoder": PREFIX / "s22plus_fyg8_p310_telemetry_decoder.py",
    "p310_identity_tiers": PREFIX / "s22plus_fyg8_p310_identity_tiers.py",
    "p310_source_contract": PREFIX / "s22plus_fyg8_p310_source_contract.py",
    "p310_candidate_intent": PREFIX / "s22plus_fyg8_p310_candidate_intent.py",
    "p310_candidate_contract": PREFIX / "s22plus_fyg8_p310_candidate_contract.py",
    "p310_userspace_build": PREFIX / "s22plus_fyg8_p310_userspace_build.py",
    "p310_build": PREFIX / "s22plus_fyg8_p310_build.py",
    "p310_build_repro_check": PREFIX / "s22plus_fyg8_p310_build_repro_check.py",
    "p310_candidate_builder": PREFIX / "build_s22plus_fyg8_p310_candidate.py",
    "p310_boot_only_packager": PREFIX / "s22plus_fyg8_p310_boot_only_packager.py",
    "p310_stock_closure": PREFIX / "s22plus_fyg8_p310_e2_stock_closure.py",
    "p310_pre_lto_qualification": PREFIX / "s22plus_fyg8_p310_pre_lto_qualification.py",
    "p310_linked_audit": PREFIX / "s22plus_fyg8_p310_linked_audit.py",
    "p310_postbuild_linked_audit": PREFIX / "s22plus_fyg8_p310_postbuild_linked_audit.py",
}


def _local_import_names(module_name: str) -> set[str]:
    path = SCRIPTS_DIRECTORY / f"{module_name}.py"
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        raise RuntimeError(f"cannot resolve P3.10 semantic dependency {module_name}") from exc
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module)
    return {
        name
        for name in names
        if name.startswith("s22plus_fyg8_")
        and (SCRIPTS_DIRECTORY / f"{name}.py").is_file()
    }


def _semantic_dependency_modules() -> tuple[str, ...]:
    """Resolve the actual local import closure used by the selected decoder."""
    roots = ("s22plus_fyg8_p310_telemetry_decoder",)
    pending = list(roots)
    visited: set[str] = set()
    while pending:
        module_name = pending.pop()
        if module_name in visited:
            continue
        visited.add(module_name)
        pending.extend(sorted(_local_import_names(module_name) - visited))
    return tuple(sorted(visited - set(roots)))


_DIRECT_PATH_SET = frozenset(DIRECT_PATHS.values())
SEMANTIC_DEPENDENCY_PATHS = {
    f"p310_semantic__{module_name}": PREFIX / f"{module_name}.py"
    for module_name in _semantic_dependency_modules()
    if PREFIX / f"{module_name}.py" not in _DIRECT_PATH_SET
}
INHERITED_KEYS = {
    f"p300_input__{key}": key for key in sorted(inherited_contract.SOURCE_KEYS)
}
GENERATED_KEYS = {
    key: ("base_patch" if key == "candidate_patch" else key)
    for key in sorted(generator.artifact_paths())
}
SOURCE_KEYS = frozenset(
    (*INHERITED_KEYS, *DIRECT_PATHS, *SEMANTIC_DEPENDENCY_PATHS, *GENERATED_KEYS.values())
)


class IdentityError(ValueError):
    pass


def _read(root: Path, path: Path, label: str) -> bytes:
    target = root / path
    metadata = target.lstat()
    if target.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise IdentityError(f"{label} is missing or indirect")
    data = target.read_bytes()
    if not data:
        raise IdentityError(f"{label} is empty")
    return data


def receipt_set(materials: Mapping[str, bytes]) -> dict[str, dict[str, Any]]:
    return {
        key: {"size": len(value), "sha256": hashlib.sha256(value).hexdigest()}
        for key, value in sorted(materials.items())
    }


def tier1_materials(root: Path) -> dict[str, bytes]:
    inherited = inherited_contract.source_bytes(root)
    generated = generator.generate_bytes(
        root,
        run_id=SOURCE_CHECK_RUN_ID,
        unsat_tag=SOURCE_CHECK_UNSAT_TAG,
        profile=PROFILE,
    )
    result = {
        **{
            source_key: inherited[old_key]
            for source_key, old_key in sorted(INHERITED_KEYS.items())
        },
        **{
            key: _read(root, path, f"P3.10 Tier-1 {key}")
            for key, path in sorted(DIRECT_PATHS.items())
        },
        **{
            key: _read(root, path, f"P3.10 semantic dependency {key}")
            for key, path in sorted(SEMANTIC_DEPENDENCY_PATHS.items())
        },
        **{
            GENERATED_KEYS[key]: value
            for key, value in sorted(generated.items())
        },
    }
    if set(result) != SOURCE_KEYS:
        raise IdentityError("P3.10 Tier-1 source key set differs")
    return result


def descriptor() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "inherited_contract_id": inherited_contract.CONTRACT_ID,
        "inherited_source_keys": dict(INHERITED_KEYS),
        "direct_paths": {key: path.as_posix() for key, path in sorted(DIRECT_PATHS.items())},
        "semantic_dependency_paths": {
            key: path.as_posix()
            for key, path in sorted(SEMANTIC_DEPENDENCY_PATHS.items())
        },
        "generated_keys": dict(GENERATED_KEYS),
        "source_keys": sorted(SOURCE_KEYS),
        "source_check_run_id": SOURCE_CHECK_RUN_ID.hex(),
        "source_check_unsat_tag": SOURCE_CHECK_UNSAT_TAG.hex(),
        "carrier": carrier.validate(),
    }


def descriptor_sha256() -> str:
    return hashlib.sha256(
        json.dumps(descriptor(), sort_keys=True, separators=(",", ":")).encode("ascii")
    ).hexdigest()


def payload_identity(materials: Mapping[str, bytes]) -> str:
    return hashlib.sha256(
        json.dumps(
            {
                "domain": "S22PLUS-FYG8-P310-PAYLOAD-IDENTITY-V1",
                "descriptor_sha256": descriptor_sha256(),
                "receipts": receipt_set(materials),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    ).hexdigest()


def validate() -> dict[str, Any]:
    expected = (
        len(INHERITED_KEYS)
        + len(DIRECT_PATHS)
        + len(SEMANTIC_DEPENDENCY_PATHS)
        + len(GENERATED_KEYS)
    )
    if len(SOURCE_KEYS) != expected or carrier.validate().get("verified") is not True:
        raise IdentityError("P3.10 payload identity scope differs")
    return {
        "schema": SCHEMA,
        "source_key_count": len(SOURCE_KEYS),
        "inherited_key_count": len(INHERITED_KEYS),
        "direct_key_count": len(DIRECT_PATHS),
        "semantic_dependency_key_count": len(SEMANTIC_DEPENDENCY_PATHS),
        "generated_key_count": len(GENERATED_KEYS),
        "descriptor_sha256": descriptor_sha256(),
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
