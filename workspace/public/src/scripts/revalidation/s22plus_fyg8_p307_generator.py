#!/usr/bin/env python3
"""Generate P3.07 userspace from immutable P3.05."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Any

import s22plus_fyg8_p305_generator as parent
import s22plus_fyg8_p307_runtime_transform as transform
import s22plus_fyg8_p307_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p307_generator_v1"
DELTA_KEYS = frozenset({
    "trace_descriptor_header",
    "p290_e3_runtime_include",
    "runtime_wrapper",
})
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
        raise GeneratorError(f"P3.07 P3.05 delta differs: {sorted(changed)}")
    required = {
        "trace_descriptor_header": (
            b"P282_CYCLE_EVENT_COUNT 29U",
            b"p307_qscratch",
            b"dwc3_otg_start_peripheral+0x4cc",
            b"rc=%w21:s32",
        ),
        "p290_e3_runtime_include": (
            spec.EUD_CACHE_PATH.encode("ascii"),
            b"p307_kmsg_observe",
            b"p307_capture_qscratch",
            b"p294_publish_final_pair(p307_attr, p307_summary)",
        ),
        "runtime_wrapper": (
            b"index == P307_EUD_MODULE_INDEX",
            b"p307_read_eud_cache()",
        ),
    }
    for key, tokens in required.items():
        for token in tokens:
            if token not in result[key]:
                raise GeneratorError(f"P3.07 token differs: {key}/{token!r}")
    if result["candidate_patch"] != baseline["candidate_patch"]:
        raise GeneratorError("P3.07 fixed kernel patch changed")
    if result["plan_header"] != baseline["plan_header"]:
        raise GeneratorError("P3.07 exact 61-module plan changed")
    if spec.validate().get("verified") is not True:
        raise GeneratorError("P3.07 telemetry SoT did not validate")
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
        raise GeneratorError("P3.07 output already exists")
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
                    raise GeneratorError(f"short P3.07 write: {path.name}")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    rows = {}
    for key, relative in sorted(paths.items()):
        path = output / Path(relative)
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise GeneratorError(f"P3.07 artifact is indirect: {key}")
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
