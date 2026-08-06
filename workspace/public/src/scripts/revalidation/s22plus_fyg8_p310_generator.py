#!/usr/bin/env python3
"""Generate the P3.10 Carrier v2 candidate sources from immutable P3.09."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Any

import s22plus_fyg8_p309_generator as parent
import s22plus_fyg8_p310_carrier_model as carrier
import s22plus_fyg8_p310_carrier_transform as transform


SCHEMA = "s22plus_fyg8_p310_generator_v1"
DELTA_KEYS = frozenset({"candidate_patch"})
GeneratorError = parent.GeneratorError


def artifact_paths():
    return parent.artifact_paths()


def generate_bytes(
    root: Path, *, run_id: bytes, unsat_tag: bytes, profile: str
) -> dict[str, bytes]:
    baseline = parent.generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    expected_unsat = carrier.unsat_record(profile, run_id)[len(carrier.UNSAT_FAMILY) :]
    if unsat_tag != expected_unsat:
        raise GeneratorError("P3.10 Carrier v2 UNSAT tag differs")
    result = dict(baseline)
    result["candidate_patch"] = transform.transform(baseline["candidate_patch"])
    changed = {key for key in result if result[key] != baseline[key]}
    if changed != DELTA_KEYS:
        raise GeneratorError(f"P3.10 P3.09 delta differs: {sorted(changed)}")
    if (
        result["trace_descriptor_header"].count(b"rc=%x21:s32") != 1
        or b"rc=%w21:s32" in result["trace_descriptor_header"]
    ):
        raise GeneratorError("P3.10 did not inherit the P3.09 descriptor correction")
    if carrier.validate().get("verified") is not True:
        raise GeneratorError("P3.10 Carrier v2 model did not validate")
    return result


def materialize(
    root: Path,
    output: Path,
    *,
    run_id: bytes,
    unsat_tag: bytes,
    profile: str,
) -> dict[str, Any]:
    if output.exists() or output.is_symlink():
        raise GeneratorError("P3.10 output already exists")
    output.mkdir(mode=0o700, parents=False)
    data = generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    paths = artifact_paths()
    for key, relative in sorted(paths.items()):
        path = output / Path(relative)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o400,
        )
        try:
            offset = 0
            while offset < len(data[key]):
                written = os.write(descriptor, data[key][offset:])
                if written <= 0:
                    raise GeneratorError(f"short P3.10 write: {path.name}")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    rows = {}
    for key, relative in sorted(paths.items()):
        path = output / Path(relative)
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise GeneratorError(f"P3.10 artifact is indirect: {key}")
        payload = path.read_bytes()
        rows[key] = {
            "path": relative.as_posix(),
            "type": "regular",
            "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    return {
        "schema": SCHEMA,
        "artifact_count": len(rows),
        "delta_keys": sorted(DELTA_KEYS),
        "carrier": carrier.validate(),
        "artifacts": rows,
        "verified": True,
    }
