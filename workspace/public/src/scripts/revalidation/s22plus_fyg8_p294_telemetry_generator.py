#!/usr/bin/env python3
"""Generate P2.94 value-telemetry artifacts from the P2.92 SoT output."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Any

import s22plus_fyg8_p292_repair_generator as baseline
import s22plus_fyg8_p294_telemetry_spec as spec
import s22plus_fyg8_p294_telemetry_transform as transform


SCHEMA = "s22plus_fyg8_p294_telemetry_generator_v1"
TELEMETRY_ARTIFACT_KEYS = frozenset(
    {
        "candidate_patch",
        "checkpoint_client",
        "p290_checkpoint_header",
        "p290_e3_runtime_include",
        "p290_position_header",
        "trace_descriptor_header",
    }
)


class TelemetryGeneratorError(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def artifact_paths():
    return baseline.artifact_paths()


def generate_bytes(
    root: Path,
    *,
    run_id: bytes,
    unsat_tag: bytes,
    profile: str,
) -> dict[str, bytes]:
    contract = spec.validate()
    source = baseline.generate_bytes(
        root,
        run_id=run_id,
        unsat_tag=unsat_tag,
        profile=profile,
    )
    result = transform.transform_artifacts(source)
    changed = {
        key for key in result if result[key] != source[key]
    }
    if changed != TELEMETRY_ARTIFACT_KEYS:
        raise TelemetryGeneratorError(
            f"P2.94 telemetry delta differs: {sorted(changed)}"
        )
    required = {
        "candidate_patch": (
            b"s22_p294_dwc3_state_snapshot",
            b"s22_p294_wrapper_vbus_snapshot",
            b"s22_fyg8_p290_detail_rules[] __used",
        ),
        "checkpoint_client": (
            b"s22_p294_checkpoint_progress_position",
            b"s22_p294_checkpoint_terminal_position",
        ),
        "p290_e3_runtime_include": (
            b"p294_publish_final_pair",
            b"P294_LINK_DETAIL_BASE 0xc60U",
            b"P294_FINAL_DETAIL_BASE 0xc70U",
            b"P294_MISMATCH_DETAIL_BASE 0xf40U",
        ),
        "p290_position_header": (
            b"S22_P294_POSITION_USBLNKST 105U",
            b"S22_P294_POSITION_FINAL_STATE 106U",
        ),
        "trace_descriptor_header": (
            b"wrapper_vbus_snapshot",
            b"dwc3_state_snapshot",
        ),
    }
    for key, tokens in required.items():
        for token in tokens:
            if result[key].count(token) < 1:
                raise TelemetryGeneratorError(
                    f"P2.94 telemetry token differs: {key}/{token!r}"
                )
    if contract.get("verified") is not True:
        raise TelemetryGeneratorError("P2.94 telemetry SoT did not validate")
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
                    f"short P2.94 materialized write: {path.name}"
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
        raise TelemetryGeneratorError("P2.94 output already exists")
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
                f"P2.94 artifact is missing or indirect: {key}"
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
        "artifacts": rows,
        "verified": True,
    }
