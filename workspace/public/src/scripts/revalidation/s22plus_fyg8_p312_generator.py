#!/usr/bin/env python3
"""Generate P3.12 userspace from the immutable P3.10 source."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import stat
from typing import Any

import s22plus_fyg8_p312_runtime_transform as transform
import s22plus_fyg8_p312_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p312_generator_v1"
DELTA_KEYS = frozenset({"p290_e3_runtime_include"})
P311_INTENT = Path("workspace/private/outputs/s22plus_fyg8_p311/intent/overlay-intent.json")
EXPECTED_P311_INTENT = {
    "size": 101457,
    "sha256": "33ac7eb8c50956a23a9cc3e6bb55603ea50cdd6379ca580c406f62b102480d26",
}
_ARTIFACT_PATHS = {
    "candidate_patch": PurePosixPath("candidate.patch"),
    "checkpoint_client": PurePosixPath("materialized-sources/s22plus_fyg8_p290_checkpoint.c"),
    "runtime_wrapper": PurePosixPath("materialized-sources/s22plus_fyg8_p290_e3_runtime.c"),
    "plan_header": PurePosixPath("materialized-sources/s22plus_fyg8_p286_e3_plan.h"),
    "p288_legacy_runtime": PurePosixPath("materialized-sources/s22plus_r4w1e_e1_runtime.c"),
    "p290_e3_runtime_include": PurePosixPath("materialized-sources/s22plus_fyg8_p290_e3_runtime.inc.c"),
    "p288_classifier_include": PurePosixPath("materialized-sources/s22plus_fyg8_p288_classifier.inc.c"),
    "p290_position_header": PurePosixPath("materialized-sources/s22plus_fyg8_p290_positions.h"),
    "p290_checkpoint_header": PurePosixPath("materialized-sources/s22plus_r4w1e_checkpoint.h"),
    "p286_classifier_include": PurePosixPath("materialized-sources/s22plus_fyg8_p286_classifier.inc.c"),
    "classifier_include": PurePosixPath("materialized-sources/s22plus_fyg8_p282_classifier.inc.c"),
    "p260_e3_runtime_include": PurePosixPath("materialized-sources/s22plus_fyg8_p260_e3_runtime.inc.c"),
    "trace_descriptor_header": PurePosixPath("materialized-sources/s22plus_fyg8_p286_trace_descriptor.h"),
}


class GeneratorError(ValueError):
    pass


def artifact_paths():
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


def frozen_identity(root: Path) -> tuple[bytes, bytes, str]:
    try:
        payload = _stable_regular(root / P311_INTENT, "P3.12 frozen P3.11 intent", 2 * 1024 * 1024)
        if {
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        } != EXPECTED_P311_INTENT:
            raise GeneratorError("P3.12 frozen P3.11 intent receipt differs")
        intent = json.loads(payload.decode("ascii"))
        run_id = bytes.fromhex(intent["run_id"])
        unsat_tag = bytes.fromhex(intent["unsat_tag_hex"])
        profile = intent["profile"]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise GeneratorError("P3.12 frozen P3.11 identity is unavailable") from exc
    if (
        intent.get("schema") != "s22plus_fyg8_p311_userspace_overlay_intent_v1"
        or intent.get("verdict") != "PASS_P311_USERSPACE_OVERLAY_INTENT_HOST_ONLY"
        or len(run_id) != 16
        or len(unsat_tag) != 16
        or profile != "E2"
    ):
        raise GeneratorError("P3.12 frozen P3.11 identity differs")
    return run_id, unsat_tag, profile


def _frozen_p311_bytes(root: Path, *, run_id: bytes, unsat_tag: bytes, profile: str) -> dict[str, bytes]:
    intent_path = root / P311_INTENT
    try:
        intent_payload = _stable_regular(
            intent_path, "P3.12 frozen P3.11 intent", 2 * 1024 * 1024
        )
        if {
            "size": len(intent_payload),
            "sha256": hashlib.sha256(intent_payload).hexdigest(),
        } != EXPECTED_P311_INTENT:
            raise GeneratorError("P3.12 frozen P3.11 intent receipt differs")
        intent = json.loads(intent_payload.decode("ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GeneratorError("P3.12 frozen P3.11 intent is unavailable") from exc
    frozen_run_id, frozen_unsat_tag, frozen_profile = frozen_identity(root)
    if (
        not isinstance(intent, dict)
        or intent.get("schema") != "s22plus_fyg8_p311_userspace_overlay_intent_v1"
        or intent.get("verdict") != "PASS_P311_USERSPACE_OVERLAY_INTENT_HOST_ONLY"
        or (run_id, unsat_tag, profile)
        != (frozen_run_id, frozen_unsat_tag, frozen_profile)
    ):
        raise GeneratorError("P3.12 frozen P3.11 identity differs")
    expected = intent.get("generated_artifacts")
    if not isinstance(expected, dict) or set(expected) != set(_ARTIFACT_PATHS):
        raise GeneratorError("P3.12 frozen P3.11 artifact inventory differs")
    result = {}
    for key, relative in _ARTIFACT_PATHS.items():
        path = intent_path.parent / Path(relative)
        try:
            payload = _stable_regular(
                path, f"P3.12 frozen P3.11 artifact {key}", 2 * 1024 * 1024
            )
        except OSError as exc:
            raise GeneratorError(f"P3.12 frozen P3.11 artifact unavailable: {key}") from exc
        receipt = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        if receipt != expected.get(key):
            raise GeneratorError(f"P3.12 frozen P3.11 artifact changed: {key}")
        result[key] = payload
    return result


def generate_bytes(
    root: Path, *, run_id: bytes, unsat_tag: bytes, profile: str
) -> dict[str, bytes]:
    baseline = _frozen_p311_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    result = transform.transform_artifacts(baseline)
    changed = {key for key in result if result[key] != baseline[key]}
    if changed != DELTA_KEYS:
        raise GeneratorError(f"P3.12 frozen-P3.11 delta differs: {sorted(changed)}")
    required = {
        "trace_descriptor_header": (b"P311_EARLY_EVENT_COUNT 30U", b"p311_early_events"),
        "p290_e3_runtime_include": (
            b"p311_parse_early_trace",
            b"control->profile_hits[index] < record_hits[index]",
        ),
        "runtime_wrapper": (b"p311_early_trace_begin", b"p311_early_trace_finish"),
    }
    for key, tokens in required.items():
        for token in tokens:
            if token not in result[key]:
                raise GeneratorError(f"P3.12 token differs: {key}/{token!r}")
    if spec.validate().get("verified") is not True:
        raise GeneratorError("P3.12 telemetry SoT did not validate")
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
        raise GeneratorError("P3.12 output already exists")
    output.mkdir(mode=0o700, parents=False)
    data = generate_bytes(root, run_id=run_id, unsat_tag=unsat_tag, profile=profile)
    paths = artifact_paths()
    for key, relative in sorted(paths.items()):
        path = output / Path(relative)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
        try:
            offset = 0
            while offset < len(data[key]):
                written = os.write(descriptor, data[key][offset:])
                if written <= 0:
                    raise GeneratorError(f"short P3.12 write: {path.name}")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    rows = {}
    for key, relative in sorted(paths.items()):
        path = output / Path(relative)
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise GeneratorError(f"P3.12 artifact is indirect: {key}")
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
