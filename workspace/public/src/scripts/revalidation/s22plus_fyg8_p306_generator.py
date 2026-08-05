#!/usr/bin/env python3
"""Generate P3.06 IPC telemetry userspace from exact P3.05."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Any

import s22plus_fyg8_p305_generator as parent
import s22plus_fyg8_p306_ipc_spec as spec
import s22plus_fyg8_p306_runtime_transform as transform


SCHEMA = "s22plus_fyg8_p306_generator_v1"
DELTA_KEYS = frozenset({"runtime_wrapper", "p290_e3_runtime_include"})
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
        raise GeneratorError(f"P3.06 P3.05 delta differs: {sorted(changed)}")
    required = {
        "runtime_wrapper": (
            b"p306_ipc_begin()",
            b"p306_ipc_drain()",
        ),
        "p290_e3_runtime_include": (
            b"P306_IPC_PATH",
            b"p306_ipc_finish()",
            b"p294_publish_final_pair(p306_chain, p306_summary)",
        ),
    }
    for key, tokens in required.items():
        for token in tokens:
            if token not in result[key]:
                raise GeneratorError(f"P3.06 token differs: {key}/{token!r}")
    if result["candidate_patch"] != baseline["candidate_patch"]:
        raise GeneratorError("P3.06 fixed kernel patch changed")
    if result["plan_header"] != baseline["plan_header"]:
        raise GeneratorError("P3.06 exact 61-module plan changed")
    if spec.validate().get("verified") is not True:
        raise GeneratorError("P3.06 telemetry SoT did not validate")
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
        raise GeneratorError("P3.06 output already exists")
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
                    raise GeneratorError(f"short P3.06 write: {path.name}")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    rows = {}
    for key, relative in sorted(paths.items()):
        path = output / Path(relative)
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise GeneratorError(f"P3.06 artifact is indirect: {key}")
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

