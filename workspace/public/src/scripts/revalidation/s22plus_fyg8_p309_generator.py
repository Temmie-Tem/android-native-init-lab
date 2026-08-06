#!/usr/bin/env python3
"""Generate the host-only P3.09 descriptor correction from immutable P3.08."""

from __future__ import annotations

from pathlib import Path

import s22plus_fyg8_p308_generator as parent
import s22plus_fyg8_p309_descriptor_transform as transform


SCHEMA = "s22plus_fyg8_p309_descriptor_generator_v1"
DELTA_KEYS = frozenset({"trace_descriptor_header"})
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
        raise GeneratorError(f"P3.09 P3.08 delta differs: {sorted(changed)}")
    descriptor = result["trace_descriptor_header"]
    if (
        descriptor.count(b"p307_qscratch") != 2
        or descriptor.count(b"rc=%x21:s32") != 1
        or b"rc=%w21:s32" in descriptor
    ):
        raise GeneratorError("P3.09 corrected descriptor premise differs")
    for key in result:
        if key != "trace_descriptor_header" and result[key] != baseline[key]:
            raise GeneratorError(f"P3.09 inherited artifact changed: {key}")
    return result
