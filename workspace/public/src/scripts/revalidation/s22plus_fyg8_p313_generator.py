#!/usr/bin/env python3
"""Generate P3.13 userspace from the immutable P3.12 materialized intent."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any

import s22plus_fyg8_p313_runtime_transform as transform
import s22plus_fyg8_p313_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p313_generator_v1"
DELTA_KEYS = frozenset(
    {
        "runtime_wrapper",
        "p290_e3_runtime_include",
        "trace_descriptor_header",
        "p290_position_header",
    }
)
P312_INTENT = Path(
    "workspace/private/outputs/s22plus_fyg8_p312/intent/overlay-intent.json"
)
EXPECTED_P312_INTENT = {
    "size": 110688,
    "sha256": "29ef68933346994cbccd187401a4aa7c67ebb8ff7a03a2e885008e1c5a2454fb",
}
_ARTIFACT_PATHS = {
    "candidate_patch": PurePosixPath("candidate.patch"),
    "checkpoint_client": PurePosixPath(
        "materialized-sources/s22plus_fyg8_p290_checkpoint.c"
    ),
    "runtime_wrapper": PurePosixPath(
        "materialized-sources/s22plus_fyg8_p290_e3_runtime.c"
    ),
    "plan_header": PurePosixPath(
        "materialized-sources/s22plus_fyg8_p286_e3_plan.h"
    ),
    "p288_legacy_runtime": PurePosixPath(
        "materialized-sources/s22plus_r4w1e_e1_runtime.c"
    ),
    "p290_e3_runtime_include": PurePosixPath(
        "materialized-sources/s22plus_fyg8_p290_e3_runtime.inc.c"
    ),
    "p288_classifier_include": PurePosixPath(
        "materialized-sources/s22plus_fyg8_p288_classifier.inc.c"
    ),
    "p290_position_header": PurePosixPath(
        "materialized-sources/s22plus_fyg8_p290_positions.h"
    ),
    "p290_checkpoint_header": PurePosixPath(
        "materialized-sources/s22plus_r4w1e_checkpoint.h"
    ),
    "p286_classifier_include": PurePosixPath(
        "materialized-sources/s22plus_fyg8_p286_classifier.inc.c"
    ),
    "classifier_include": PurePosixPath(
        "materialized-sources/s22plus_fyg8_p282_classifier.inc.c"
    ),
    "p260_e3_runtime_include": PurePosixPath(
        "materialized-sources/s22plus_fyg8_p260_e3_runtime.inc.c"
    ),
    "trace_descriptor_header": PurePosixPath(
        "materialized-sources/s22plus_fyg8_p286_trace_descriptor.h"
    ),
}


class GeneratorError(ValueError):
    pass


def artifact_paths() -> dict[str, PurePosixPath]:
    return dict(_ARTIFACT_PATHS)


def _stable_regular(path: Path, label: str, maximum: int) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
        if path.is_symlink() or not path.is_file() or before.st_size > maximum:
            raise GeneratorError(f"{label} is not a bounded regular file")
        payload = path.read_bytes()
        after = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise GeneratorError(f"{label} is unavailable") from exc
    if (
        len(payload) != before.st_size
        or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    ):
        raise GeneratorError(f"{label} changed while reading")
    return payload


def _intent(root: Path) -> tuple[bytes, dict[str, Any]]:
    payload = _stable_regular(
        root / P312_INTENT, "P3.13 frozen P3.12 intent", 2 * 1024 * 1024
    )
    if {
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    } != EXPECTED_P312_INTENT:
        raise GeneratorError("P3.13 frozen P3.12 intent receipt differs")
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GeneratorError("P3.13 frozen P3.12 intent is invalid") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema")
        != "s22plus_fyg8_p312_userspace_overlay_intent_v1"
        or value.get("verdict")
        != "PASS_P312_USERSPACE_OVERLAY_INTENT_HOST_ONLY"
        or value.get("profile") != "E2"
    ):
        raise GeneratorError("P3.13 frozen P3.12 identity differs")
    return payload, value


def frozen_identity(root: Path) -> tuple[bytes, bytes, str]:
    _, value = _intent(root)
    try:
        run_id = bytes.fromhex(value["run_id"])
        unsat_tag = bytes.fromhex(value["unsat_tag_hex"])
        profile = value["profile"]
    except (KeyError, TypeError, ValueError) as exc:
        raise GeneratorError("P3.13 frozen P3.12 identity is unavailable") from exc
    if len(run_id) != 16 or len(unsat_tag) != 16 or profile != "E2":
        raise GeneratorError("P3.13 frozen P3.12 identity extent differs")
    return run_id, unsat_tag, profile


def _frozen_p312_bytes(
    root: Path, *, run_id: bytes, unsat_tag: bytes, profile: str
) -> dict[str, bytes]:
    _, intent = _intent(root)
    frozen = frozen_identity(root)
    if (run_id, unsat_tag, profile) != frozen:
        raise GeneratorError("P3.13 requested identity differs from P3.12")
    expected = intent.get("generated_artifacts")
    if not isinstance(expected, dict) or set(expected) != set(_ARTIFACT_PATHS):
        raise GeneratorError("P3.13 frozen artifact inventory differs")
    base = root / P312_INTENT.parent
    result: dict[str, bytes] = {}
    for key, relative in _ARTIFACT_PATHS.items():
        payload = _stable_regular(
            base / Path(relative), f"P3.13 frozen P3.12 artifact {key}", 3 * 1024 * 1024
        )
        receipt = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        if receipt != expected.get(key):
            raise GeneratorError(f"P3.13 frozen P3.12 artifact changed: {key}")
        result[key] = payload
    return result


def generate_bytes(
    root: Path, *, run_id: bytes, unsat_tag: bytes, profile: str
) -> dict[str, bytes]:
    baseline = _frozen_p312_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    result = transform.transform_artifacts(baseline)
    changed = {key for key in result if result[key] != baseline[key]}
    if changed != DELTA_KEYS:
        raise GeneratorError(f"P3.13 frozen-P3.12 delta differs: {sorted(changed)}")
    required = {
        "runtime_wrapper": (b"p290_e3_run();",),
        "p290_e3_runtime_include": (
            b"P3.13 post-bind same-boot resume-cycle observer",
            b"p313_run();",
            b"profile_hits[index] < result->record_hits[index]",
        ),
        "trace_descriptor_header": (
            b"P282_ROLE_EVENT_COUNT 5U",
            b"P282_CYCLE_EVENT_COUNT 25U",
            b"role_qscratch",
            b"cycle_event_config",
        ),
        "p290_position_header": (b"S22_P313_POSITION_B_DETAIL 106U",),
    }
    forbidden = {
        "runtime_wrapper": (b"p311_early_trace_begin", b"p311_early_trace_finish"),
    }
    for key, tokens in required.items():
        for token in tokens:
            if token not in result[key]:
                raise GeneratorError(f"P3.13 token missing: {key}/{token!r}")
    for key, tokens in forbidden.items():
        for token in tokens:
            if token in result[key]:
                raise GeneratorError(f"P3.13 retired token survived: {key}/{token!r}")
    if spec.validate().get("verified") is not True:
        raise GeneratorError("P3.13 telemetry SoT did not validate")
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
        raise GeneratorError("P3.13 output already exists")
    output.mkdir(mode=0o700, parents=False)
    data = generate_bytes(root, run_id=run_id, unsat_tag=unsat_tag, profile=profile)
    for key, relative in artifact_paths().items():
        path = output / Path(relative)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(
            path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400
        )
        try:
            offset = 0
            while offset < len(data[key]):
                written = os.write(descriptor, data[key][offset:])
                if written <= 0:
                    raise GeneratorError(f"short P3.13 write: {path.name}")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    rows: dict[str, Any] = {}
    for key, relative in artifact_paths().items():
        path = output / Path(relative)
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise GeneratorError(f"P3.13 artifact is indirect: {key}")
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
