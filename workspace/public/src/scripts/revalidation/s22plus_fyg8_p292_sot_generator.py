#!/usr/bin/env python3
"""Materialize the phase-1 P2.92 SoT as exact P2.90 payload artifacts."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any

import s22plus_fyg8_p290_candidate_intent as p290_intent
import s22plus_fyg8_p290_source_contract as p290
import s22plus_fyg8_p292_checkpoint_sot as sot


SCHEMA = "s22plus_fyg8_p292_sot_generator_v1"
PHASE = sot.PHASE
CANDIDATE_PATCH_KEY = "candidate_patch"
CANDIDATE_PATCH_PATH = PurePosixPath("candidate.patch")


class GeneratorError(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def artifact_paths() -> dict[str, PurePosixPath]:
    paths = {CANDIDATE_PATCH_KEY: CANDIDATE_PATCH_PATH}
    paths.update(
        {
            key: PurePosixPath("materialized-sources") / filename
            for key, filename in p290.MATERIALIZED_FILENAMES.items()
        }
    )
    if len(paths) != 13 or len(set(paths.values())) != len(paths):
        raise GeneratorError("P2.92 phase-1 artifact paths drifted")
    return paths


def generate_bytes(
    root: Path,
    *,
    run_id: bytes,
    unsat_tag: bytes,
    profile: str,
) -> dict[str, bytes]:
    contract = sot.validate()
    if profile != sot.PROFILE:
        raise GeneratorError(f"unsupported P2.92 phase-1 profile: {profile}")
    if len(run_id) != sot.RUN_ID_SIZE or not any(run_id):
        raise GeneratorError("P2.92 phase-1 run ID is invalid")
    if len(unsat_tag) != sot.RUN_ID_SIZE:
        raise GeneratorError("P2.92 phase-1 unsat tag is invalid")

    source = p290.source_bytes(root)
    generated = {
        key: source[key] for key in p290.MATERIALIZED_FILENAMES
    }
    generated[CANDIDATE_PATCH_KEY] = p290_intent.build_patch(
        source["base_patch"], run_id, unsat_tag, profile
    )
    if set(generated) != set(artifact_paths()):
        raise GeneratorError("P2.92 phase-1 artifact inventory drifted")

    patch = generated[CANDIDATE_PATCH_KEY]
    checkpoint = generated["checkpoint_client"]
    required_patch = (
        b"#define S22_FYG8_E1_LONG_SIZE\t\t45U",
        b"#define S22_FYG8_E1_HEADER_SIZE\t\t25U",
        b"#define S22_FYG8_E1_SLOT_SIZE\t\t10U",
        b"#define S22_FYG8_E1_REQUEST_SIZE\t32U",
        b"+\tu8 item_index;\n+\tu32 seed_idx;",
        b"+\t\t\t\tS22_FYG8_E1_PROGRESS,\n"
        b"+\t\t\t\ts22_fyg8_e1_state.item_index, 0,",
    )
    required_client = (
        b'#include "s22plus_r4w1e_checkpoint.h"',
        b'request.magic[0] = \'S\';',
        b"long fd = sys_openat(",
        b"long written = sys_write(",
        b"long closed = sys_close(",
        b"return written < 0 ? written : -EIO;",
        b"return closed;",
    )
    if any(patch.count(token) != 1 for token in required_patch):
        raise GeneratorError(
            "P2.92 phase-1 kernel artifact is not SoT-constrained"
        )
    if any(checkpoint.count(token) != 1 for token in required_client):
        raise GeneratorError(
            "P2.92 phase-1 client artifact is not SoT-constrained"
        )

    tables = p290.linked_table_bytes()
    sequence = bytes(position.stage for position in sot.POSITIONS)
    items = bytes(position.item_index for position in sot.POSITIONS)
    kinds = bytes(
        1 if position.kind == p290.spec.KIND_GATE else
        2 if position.kind == p290.spec.KIND_TERMINAL else
        0
        for position in sot.POSITIONS
    )
    if (
        tables["s22_fyg8_e2_sequence"] != sequence
        or tables["s22_fyg8_e2_items"] != items
        or tables["s22_fyg8_e2_kinds"] != kinds
    ):
        raise GeneratorError("P2.92 phase-1 linked position data drifted")
    if not contract["verified"]:
        raise GeneratorError("P2.92 phase-1 SoT did not verify")
    return generated


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
                raise GeneratorError(f"short materialized write: {path.name}")
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
        raise GeneratorError("P2.92 phase-1 output already exists")
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
            raise GeneratorError(f"materialized artifact is indirect: {key}")
        rows[key] = {
            "path": relative.as_posix(),
            "type": "regular",
            "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
            "size": metadata.st_size,
            "sha256": _sha256(path.read_bytes()),
        }
    return {
        "schema": SCHEMA,
        "phase": PHASE,
        "sot": sot.validate(),
        "artifact_count": len(rows),
        "artifacts": rows,
        "verified": True,
    }
