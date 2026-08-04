#!/usr/bin/env python3
"""Generate P3.00 event-ingress/IRQ observer artifacts."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Any

import s22plus_fyg8_p298_telemetry_generator as p298
import s22plus_fyg8_p300_telemetry_spec as spec
import s22plus_fyg8_p300_telemetry_transform as transform


SCHEMA = "s22plus_fyg8_p300_telemetry_generator_v1"
TELEMETRY_ARTIFACT_KEYS = p298.TELEMETRY_ARTIFACT_KEYS
P298_DELTA_KEYS = frozenset(
    {
        "candidate_patch",
        "checkpoint_client",
        "p290_e3_runtime_include",
        "trace_descriptor_header",
    }
)


class TelemetryGeneratorError(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def artifact_paths():
    return p298.artifact_paths()


def generate_bytes(
    root: Path,
    *,
    run_id: bytes,
    unsat_tag: bytes,
    profile: str,
) -> dict[str, bytes]:
    contract = spec.validate()
    baseline = p298.generate_bytes(
        root,
        run_id=run_id,
        unsat_tag=unsat_tag,
        profile=profile,
    )
    result = transform.transform_artifacts(baseline)
    changed = {key for key in result if result[key] != baseline[key]}
    if changed != P298_DELTA_KEYS:
        raise TelemetryGeneratorError(
            f"P3.00 P2.98 delta differs: {sorted(changed)}"
        )
    required = {
        "candidate_patch": (
            b"s22_p300_dwc3_event_config_snapshot",
            b"{105, 0, 0xd00}",
            b"{105, 0, 0xdaf}",
        ),
        "checkpoint_client": (
            b"{105U, 0U, 0xd00U}",
            b"{105U, 0U, 0xdafU}",
        ),
        "p290_e3_runtime_include": (
            b"p300_parse_bind_stream",
            b"p300_profile_relations",
            b"p300_ingress_class",
            b"p300_close_recording_window",
            b"recording_window_closed",
            b"traceoff:count=0 if type == 2",
            b"P300_IRQ_RETURN_MAXACTIVE 32U",
        ),
        "trace_descriptor_header": (
            b"#define P282_BIND_EVENT_COUNT 15U",
            b"r32:p282/irq_out",
            b"s22_p300_dwc3_event_config_snapshot",
            b"type=+0(%x1):b4@8/32",
        ),
    }
    for key, tokens in required.items():
        for token in tokens:
            if token not in result[key]:
                raise TelemetryGeneratorError(
                    f"P3.00 telemetry token differs: {key}/{token!r}"
                )
    forbidden = (
        b"#define P282_BIND_EVENT_COUNT 12U",
        b"dwc3_gadget_reset_interrupt dwc=%x0:u64",
        b"dwc3_gadget_conndone_interrupt dwc=%x0:u64",
        b"event_mask * 16U",
    )
    if any(
        token in result[key]
        for key in P298_DELTA_KEYS
        for token in forbidden
    ):
        raise TelemetryGeneratorError("P3.00 superseded telemetry token remains")
    if contract.get("verified") is not True:
        raise TelemetryGeneratorError("P3.00 telemetry SoT did not validate")
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
                    f"short P3.00 materialized write: {path.name}"
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
        raise TelemetryGeneratorError("P3.00 output already exists")
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
                f"P3.00 artifact is missing or indirect: {key}"
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
        "p298_delta_keys": sorted(P298_DELTA_KEYS),
        "artifacts": rows,
        "verified": True,
    }
