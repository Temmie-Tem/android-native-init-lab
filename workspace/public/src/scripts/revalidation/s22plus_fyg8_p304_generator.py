#!/usr/bin/env python3
"""Generate the P3.04 userspace artifacts from exact P3.03."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Any

import s22plus_fyg8_p303_telemetry_generator as parent
import s22plus_fyg8_p304_plan_transform as plan


SCHEMA = "s22plus_fyg8_p304_generator_v1"
DELTA_KEYS = frozenset({"plan_header", "runtime_wrapper"})
GeneratorError = parent.TelemetryGeneratorError
_COUNT_ASSERT_60 = (
    b'_Static_assert(S22PLUS_O2_MODULE_PLAN_COUNT == 60U, "E2 module count");'
)
_COUNT_ASSERT_61 = (
    b'_Static_assert(S22PLUS_O2_MODULE_PLAN_COUNT == 61U, "E2 module count");'
)


def artifact_paths():
    return parent.artifact_paths()


def generate_bytes(
    root: Path, *, run_id: bytes, unsat_tag: bytes, profile: str
) -> dict[str, bytes]:
    baseline = parent.generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    result = dict(baseline)
    result["plan_header"] = plan.transform(baseline["plan_header"])
    runtime = baseline["runtime_wrapper"]
    if runtime.count(_COUNT_ASSERT_60) != 1 or _COUNT_ASSERT_61 in runtime:
        raise GeneratorError("P3.03 runtime module-count assertion differs")
    result["runtime_wrapper"] = runtime.replace(
        _COUNT_ASSERT_60, _COUNT_ASSERT_61, 1
    )
    changed = {key for key in result if result[key] != baseline[key]}
    if changed != DELTA_KEYS:
        raise GeneratorError(f"P3.04 P3.03 delta differs: {sorted(changed)}")
    if result["candidate_patch"] != baseline["candidate_patch"]:
        raise GeneratorError("P3.04 fixed kernel patch changed")
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
        raise GeneratorError("P3.04 output already exists")
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
                    raise GeneratorError(f"short P3.04 write: {path.name}")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    rows = {}
    for key, relative in sorted(paths.items()):
        path = output / Path(relative)
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise GeneratorError(f"P3.04 artifact is indirect: {key}")
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
