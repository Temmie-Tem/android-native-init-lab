#!/usr/bin/env python3
"""Generate P3.11 userspace from the immutable P3.10 Carrier v2 source."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Any

import s22plus_fyg8_p310_generator as parent
import s22plus_fyg8_p311_runtime_transform as transform
import s22plus_fyg8_p311_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p311_generator_v1"
DELTA_KEYS = frozenset(
    {"trace_descriptor_header", "p290_e3_runtime_include", "runtime_wrapper"}
)
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
        raise GeneratorError(f"P3.11 P3.10 delta differs: {sorted(changed)}")
    required = {
        "trace_descriptor_header": (
            b"P311_EARLY_EVENT_COUNT 30U",
            b"p311_early_events",
            b"p311_suspend_ref_src_prepare",
        ),
        "p290_e3_runtime_include": (
            b"P282_PHASE_P311_EARLY",
            b"p311_parse_early_trace",
            b"p311_summary_detail",
        ),
        "runtime_wrapper": (
            b"index == 55U",
            b"p311_early_trace_begin",
            b"p311_early_trace_finish",
        ),
    }
    for key, tokens in required.items():
        for token in tokens:
            if token not in result[key]:
                raise GeneratorError(f"P3.11 token differs: {key}/{token!r}")
    for key in result:
        if key not in DELTA_KEYS and result[key] != baseline[key]:
            raise GeneratorError(f"P3.11 inherited artifact changed: {key}")
    if spec.validate().get("verified") is not True:
        raise GeneratorError("P3.11 telemetry SoT did not validate")
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
        raise GeneratorError("P3.11 output already exists")
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
                    raise GeneratorError(f"short P3.11 write: {path.name}")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    rows = {}
    for key, relative in sorted(paths.items()):
        path = output / Path(relative)
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise GeneratorError(f"P3.11 artifact is indirect: {key}")
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
