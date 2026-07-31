#!/usr/bin/env python3
"""Generate P2.92 phase-2 repaired artifacts from the zero-delta SoT."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Any

import s22plus_fyg8_p292_repair_spec as spec
import s22plus_fyg8_p292_repair_transform as transform
import s22plus_fyg8_p292_sot_generator as phase1


SCHEMA = "s22plus_fyg8_p292_repair_generator_v1"


class RepairGeneratorError(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def artifact_paths():
    return phase1.artifact_paths()


def generate_bytes(
    root: Path,
    *,
    run_id: bytes,
    unsat_tag: bytes,
    profile: str,
) -> dict[str, bytes]:
    contract = spec.validate()
    baseline = phase1.generate_bytes(
        root,
        run_id=run_id,
        unsat_tag=unsat_tag,
        profile=profile,
    )
    repaired = transform.transform_artifacts(baseline)
    changed = {
        key for key in repaired if repaired[key] != baseline[key]
    }
    if changed != spec.REPAIR_ARTIFACT_KEYS:
        raise RepairGeneratorError(
            f"phase-2 repair delta differs: {sorted(changed)}"
        )
    patch = repaired["candidate_patch"]
    checkpoint = repaired["checkpoint_client"]
    header = repaired["p290_checkpoint_header"]
    wrapper = repaired["runtime_wrapper"]
    include = repaired["p290_e3_runtime_include"]
    required = {
        "candidate_patch": (
            (b"struct s22_fyg8_e1_slot active;", 1),
            (b"sizeof(s22_fyg8_e1_state.active)", 4),
            (b"s22_fyg8_e1_state.active.generation + 1U", 1),
            (b"detail > 0x4000 && detail <= 0x4fff", 1),
            (b"memcpy(&s22_fyg8_e1_state.active, &next,", 1),
        ),
        "checkpoint_client": (
            (b"p292_remember_publication_error", 4),
            (b"S22_P292_PUBLICATION_OPERATION_OPEN", 4),
            (b"S22_P292_PUBLICATION_OPERATION_WRITE", 2),
            (b"S22_P292_PUBLICATION_OPERATION_CLOSE", 4),
            (b"s22_p292_checkpoint_publication_failure_next", 1),
        ),
        "p290_checkpoint_header": (
            (b"S22_P292_PUBLICATION_OPEN_BASE 0x4000U", 1),
            (b"uint8_t publication_error_operation;", 1),
            (b"long publication_error_errno;", 1),
        ),
        "runtime_wrapper": (
            (b"struct p292_checkpoint_errno_evidence", 2),
            (b"g_p292_checkpoint_errno_evidence.valid = 1U;", 1),
            (b"p292_park_after_checkpoint_error(primary_rc);", 1),
        ),
        "p290_e3_runtime_include": (
            (b"p292_park_after_checkpoint_error(rc);", 2),
            (b"p292_park_after_checkpoint_error(primary_rc);", 1),
        ),
    }
    values = {
        "candidate_patch": patch,
        "checkpoint_client": checkpoint,
        "p290_checkpoint_header": header,
        "runtime_wrapper": wrapper,
        "p290_e3_runtime_include": include,
    }
    for key, tokens in required.items():
        for token, expected_count in tokens:
            if values[key].count(token) != expected_count:
                raise RepairGeneratorError(
                    f"phase-2 SoT token differs: {key}/{token!r}"
                )
    forbidden_patch = (
        b"s22_fyg8_e1_state.generation",
        b"s22_fyg8_e1_state.stage",
        b"s22_fyg8_e1_state.item_index",
        b"s22_fyg8_e1_build_slot(&active",
    )
    if any(token in patch for token in forbidden_patch):
        raise RepairGeneratorError("phase-2 patch retains partial active state")
    if not contract["verified"]:
        raise RepairGeneratorError("phase-2 repair SoT did not validate")
    return repaired


def _write_regular(path: Path, data: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o400,
    )
    try:
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                raise RepairGeneratorError(
                    f"short phase-2 materialized write: {path.name}"
                )
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def materialize(
    root: Path,
    output: Path,
    *,
    run_id: bytes,
    unsat_tag: bytes,
    profile: str,
) -> dict[str, Any]:
    if output.exists() or output.is_symlink():
        raise RepairGeneratorError("phase-2 output already exists")
    output.mkdir(mode=0o700, parents=False)
    data = generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    paths = artifact_paths()
    for key, relative in sorted(paths.items()):
        _write_regular(output / Path(relative), data[key])
    rows = {}
    for key, relative in sorted(paths.items()):
        path = output / Path(relative)
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
            raise RepairGeneratorError(
                f"phase-2 artifact is indirect: {key}"
            )
        rows[key] = {
            "path": relative.as_posix(),
            "type": "regular",
            "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
            "size": metadata.st_size,
            "sha256": _sha256(path.read_bytes()),
        }
    return {
        "schema": SCHEMA,
        "phase": spec.PHASE,
        "sot": spec.validate(),
        "artifact_count": len(rows),
        "repair_artifact_keys": sorted(spec.REPAIR_ARTIFACT_KEYS),
        "artifacts": rows,
        "verified": True,
    }
