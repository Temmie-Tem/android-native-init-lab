#!/usr/bin/env python3
"""Generate P3.08 userspace from immutable P3.07 sources."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Any

import s22plus_fyg8_p307_generator as parent
import s22plus_fyg8_p308_runtime_transform as transform
import s22plus_fyg8_p308_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p308_generator_v1"
DELTA_KEYS = frozenset({"p290_e3_runtime_include"})
GeneratorError = parent.GeneratorError


def artifact_paths():
    return parent.artifact_paths()


def generate_bytes(
    root: Path, *, run_id: bytes, unsat_tag: bytes, profile: str
) -> dict[str, bytes]:
    baseline = parent.generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    result = transform.transform_artifacts(baseline)
    changed = {key for key in result if result[key] != baseline[key]}
    if changed != DELTA_KEYS:
        raise GeneratorError(f"P3.08 P3.07 delta differs: {sorted(changed)}")
    runtime = result["p290_e3_runtime_include"]
    for token in (
        b"p308_kmsg_observe",
        b"body_end = p282_find_bytes",
        b"P308_DEGRADED_DETAIL_BASE 0x6100U",
        b"P308_SUMMARY_DETAIL_MAX 0x4febU",
        b"p294_publish_final_pair(\n                p308_first, p308_terminal)",
    ):
        if token not in runtime:
            raise GeneratorError(f"P3.08 runtime token differs: {token!r}")
    for key in result:
        if key != "p290_e3_runtime_include" and result[key] != baseline[key]:
            raise GeneratorError(f"P3.08 inherited artifact changed: {key}")
    if spec.validate().get("enumerated_family_value_count") != 5988:
        raise GeneratorError("P3.08 telemetry SoT did not validate")
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
        raise GeneratorError("P3.08 output already exists")
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
                    raise GeneratorError(f"short P3.08 write: {path.name}")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    rows = {}
    for key, relative in sorted(paths.items()):
        path = output / Path(relative)
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise GeneratorError(f"P3.08 artifact is indirect: {key}")
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
        "artifacts": rows,
        "verified": True,
    }
