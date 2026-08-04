#!/usr/bin/env python3
"""Generate the P3.01 userspace-only subtype telemetry artifacts."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Any

import s22plus_fyg8_p300_telemetry_generator as inherited
import s22plus_fyg8_p301_telemetry_spec as spec
import s22plus_fyg8_p301_telemetry_transform as transform


SCHEMA = "s22plus_fyg8_p301_telemetry_generator_v1"
TELEMETRY_ARTIFACT_KEYS = inherited.TELEMETRY_ARTIFACT_KEYS
P300_DELTA_KEYS = frozenset({"p290_e3_runtime_include"})


class TelemetryGeneratorError(ValueError):
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
    contract = spec.validate()
    baseline = inherited.generate_bytes(
        root,
        run_id=run_id,
        unsat_tag=unsat_tag,
        profile=profile,
    )
    result = transform.transform_artifacts(baseline)
    changed = {key for key in result if result[key] != baseline[key]}
    if changed != P300_DELTA_KEYS:
        raise TelemetryGeneratorError(
            f"P3.01 P3.00 delta differs: {sorted(changed)}"
        )
    for key in ("candidate_patch", "checkpoint_client", "trace_descriptor_header"):
        if result[key] != baseline[key]:
            raise TelemetryGeneratorError(
                f"P3.01 fixed-Image artifact changed: {key}"
            )
    runtime = result["p290_e3_runtime_include"]
    required = (
        b"S22_P294_POSITION_USBLNKST == 105U",
        b"S22_P294_POSITION_FINAL_STATE == 106U",
        b"g_checkpoint.generation != 105U",
        b"s22_p294_checkpoint_progress_position(",
        b"P301_UNKNOWN_SUBTYPE_DETAIL 0x4fc1U",
        b"if (result->unknown_subtype_seen)",
        b"if (result->other_type_mask == 0U)",
        b"((unsigned int)result->other_type_mask - 1U)",
        b"p301_terminal_detail(\n                &final_result",
    )
    if any(token not in runtime for token in required):
        raise TelemetryGeneratorError("P3.01 runtime contract token differs")
    mask_guard = runtime.find(b"if (result->other_type_mask == 0U)")
    mask_subtract = runtime.find(
        b"((unsigned int)result->other_type_mask - 1U)"
    )
    if not 0 <= mask_guard < mask_subtract:
        raise TelemetryGeneratorError("P3.01 mask-zero guard ordering differs")
    if contract.get("verified") is not True:
        raise TelemetryGeneratorError("P3.01 telemetry SoT did not validate")
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
                raise TelemetryGeneratorError(
                    f"short P3.01 materialized write: {path.name}"
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
        raise TelemetryGeneratorError("P3.01 output already exists")
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
            raise TelemetryGeneratorError(
                f"P3.01 artifact is missing or indirect: {key}"
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
        "sot": spec.validate(),
        "artifact_count": len(rows),
        "telemetry_artifact_keys": sorted(TELEMETRY_ARTIFACT_KEYS),
        "p300_delta_keys": sorted(P300_DELTA_KEYS),
        "artifacts": rows,
        "verified": True,
    }
