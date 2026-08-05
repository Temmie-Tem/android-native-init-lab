#!/usr/bin/env python3
"""Generate P3.03 HS-PHY userspace observer artifacts."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
from typing import Any

import s22plus_fyg8_p301_telemetry_generator as inherited
import s22plus_fyg8_p303_telemetry_spec as spec
import s22plus_fyg8_p303_telemetry_transform as transform


SCHEMA = "s22plus_fyg8_p303_telemetry_generator_v1"
TELEMETRY_ARTIFACT_KEYS = inherited.TELEMETRY_ARTIFACT_KEYS
P301_DELTA_KEYS = frozenset(
    {"runtime_wrapper", "p290_e3_runtime_include", "trace_descriptor_header"}
)
TelemetryGeneratorError = inherited.TelemetryGeneratorError


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
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    result = transform.transform_artifacts(baseline)
    changed = {key for key in result if result[key] != baseline[key]}
    if changed != P301_DELTA_KEYS:
        raise TelemetryGeneratorError(
            f"P3.03 P3.01 delta differs: {sorted(changed)}"
        )
    required = {
        "runtime_wrapper": (
            b"p303_kmsg_begin()",
            b"p303_kmsg_drain()",
        ),
        "p290_e3_runtime_include": (
            b"P303_CLOCK_CALLSITE_COUNT 12U",
            b"p303_capture_clock(",
            b"p303_clock_detail(&p303_clock)",
            b"p303_kmsg_finish()",
            b"p294_publish_final_pair(p303_clock, p303_log)",
        ),
        "trace_descriptor_header": (
            b"#define P282_CYCLE_EVENT_COUNT 28U",
            b"p303_eud_ref_src_prepare",
            b"msm_hsphy_init+0x5d0",
        ),
    }
    for key, tokens in required.items():
        for token in tokens:
            if token not in result[key]:
                raise TelemetryGeneratorError(
                    f"P3.03 telemetry token differs: {key}/{token!r}"
                )
    if result["candidate_patch"] != baseline["candidate_patch"]:
        raise TelemetryGeneratorError("P3.03 fixed kernel patch changed")
    if contract.get("verified") is not True:
        raise TelemetryGeneratorError("P3.03 telemetry SoT did not validate")
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
        raise TelemetryGeneratorError("P3.03 output already exists")
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
                    raise TelemetryGeneratorError(
                        f"short P3.03 materialized write: {path.name}"
                    )
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    rows = {}
    for key, relative in sorted(paths.items()):
        path = output / Path(relative)
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise TelemetryGeneratorError(
                f"P3.03 artifact is missing or indirect: {key}"
            )
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
        "sot": spec.validate(),
        "artifact_count": len(rows),
        "telemetry_artifact_keys": sorted(TELEMETRY_ARTIFACT_KEYS),
        "p301_delta_keys": sorted(P301_DELTA_KEYS),
        "artifacts": rows,
        "verified": True,
    }
