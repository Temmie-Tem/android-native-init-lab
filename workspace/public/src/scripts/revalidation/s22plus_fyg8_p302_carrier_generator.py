#!/usr/bin/env python3
"""Generate the fixed-Image P3.02-M0 userspace carrier artifacts."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Any

import s22plus_fyg8_p301_telemetry_generator as inherited


SCHEMA = "s22plus_fyg8_p302_carrier_generator_v1"
TELEMETRY_ARTIFACT_KEYS = inherited.TELEMETRY_ARTIFACT_KEYS
P301_DELTA_KEYS = frozenset()


class CarrierGeneratorError(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def artifact_paths():
    return inherited.artifact_paths()


def generate_bytes(
    root: Path,
    *,
    run_id: bytes,
    unsat_tag: bytes,
    profile: str,
) -> dict[str, bytes]:
    baseline = inherited.generate_bytes(
        root,
        run_id=run_id,
        unsat_tag=unsat_tag,
        profile=profile,
    )
    result = dict(baseline)
    changed = {key for key in result if result[key] != baseline[key]}
    if changed != P301_DELTA_KEYS:
        raise CarrierGeneratorError(
            f"P3.02 P3.01 delta differs: {sorted(changed)}"
        )
    for key in result:
        if result[key] != baseline[key]:
            raise CarrierGeneratorError(f"P3.02 inherited artifact changed: {key}")
    return result


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
                raise CarrierGeneratorError(
                    f"short P3.02 materialized write: {path.name}"
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
        raise CarrierGeneratorError("P3.02 output already exists")
    output.mkdir(mode=0o700, parents=False)
    data = generate_bytes(
        root,
        run_id=run_id,
        unsat_tag=unsat_tag,
        profile=profile,
    )
    paths = artifact_paths()
    for key, relative in sorted(paths.items()):
        _write_regular(output / Path(relative), data[key])
    rows = {}
    for key, relative in sorted(paths.items()):
        path = output / Path(relative)
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise CarrierGeneratorError(
                f"P3.02 artifact is missing or indirect: {key}"
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
        "artifact_count": len(rows),
        "telemetry_artifact_keys": sorted(TELEMETRY_ARTIFACT_KEYS),
        "p301_delta_keys": sorted(P301_DELTA_KEYS),
        "artifacts": rows,
        "verified": True,
    }
