#!/usr/bin/env python3
"""Generate P3.14 userspace from the immutable P3.13 intent."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any

import s22plus_fyg8_p313_generator as parent
import s22plus_fyg8_p314_runtime_transform as transform
import s22plus_fyg8_p314_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p314_generator_v1"
DELTA_KEYS = frozenset({"p290_e3_runtime_include"})
P313_INTENT = Path(
    "workspace/private/outputs/s22plus_fyg8_p313/intent/overlay-intent.json"
)
EXPECTED_P313_INTENT = {
    "size": 209840,
    "sha256": "5ddbd743755ee5ec5d413741888e46d5961a8c1f82c582aadfc8f48fc0339da9",
}


class GeneratorError(ValueError):
    pass


def artifact_paths() -> dict[str, PurePosixPath]:
    return parent.artifact_paths()


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
    payload = _stable_regular(root / P313_INTENT, "P3.14 frozen P3.13 intent", 2**21)
    if {
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    } != EXPECTED_P313_INTENT:
        raise GeneratorError("P3.14 frozen P3.13 intent receipt differs")
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GeneratorError("P3.14 frozen P3.13 intent is invalid") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema") != "s22plus_fyg8_p313_userspace_overlay_intent_v1"
        or value.get("verdict") != "PASS_P313_USERSPACE_OVERLAY_INTENT_HOST_ONLY"
        or value.get("profile") != "E2"
    ):
        raise GeneratorError("P3.14 frozen P3.13 identity differs")
    return payload, value


def frozen_identity(root: Path) -> tuple[bytes, bytes, str]:
    _, value = _intent(root)
    try:
        run_id = bytes.fromhex(value["run_id"])
        unsat_tag = bytes.fromhex(value["unsat_tag_hex"])
        profile = value["profile"]
    except (KeyError, TypeError, ValueError) as exc:
        raise GeneratorError("P3.14 frozen identity is unavailable") from exc
    if len(run_id) != 16 or len(unsat_tag) != 16 or profile != "E2":
        raise GeneratorError("P3.14 frozen identity extent differs")
    return run_id, unsat_tag, profile


def _frozen_p313_bytes(
    root: Path, *, run_id: bytes, unsat_tag: bytes, profile: str
) -> dict[str, bytes]:
    _, intent = _intent(root)
    if (run_id, unsat_tag, profile) != frozen_identity(root):
        raise GeneratorError("P3.14 requested identity differs from P3.13")
    expected = intent.get("generated_artifacts")
    paths = artifact_paths()
    if not isinstance(expected, dict) or set(expected) != set(paths):
        raise GeneratorError("P3.14 frozen artifact inventory differs")
    base = root / P313_INTENT.parent
    result: dict[str, bytes] = {}
    for key, relative in paths.items():
        payload = _stable_regular(
            base / Path(relative), f"P3.14 frozen P3.13 artifact {key}", 3 * 2**20
        )
        receipt = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        if receipt != expected.get(key):
            raise GeneratorError(f"P3.14 frozen P3.13 artifact changed: {key}")
        result[key] = payload
    return result


def generate_bytes(
    root: Path, *, run_id: bytes, unsat_tag: bytes, profile: str
) -> dict[str, bytes]:
    baseline = _frozen_p313_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    result = transform.transform_artifacts(baseline)
    changed = {key for key in result if result[key] != baseline[key]}
    if changed != DELTA_KEYS:
        raise GeneratorError(f"P3.14 frozen-P3.13 delta differs: {sorted(changed)}")
    runtime = result["p290_e3_runtime_include"]
    required = (
        b"P3.14 source-normalized post-bind resume-cycle observer",
        b"P314_STOP_CLEAN_RECORDS 14U",
        b"P314_FINAL_CLEAN_RECORDS 41U",
        b"P314_FINAL_DRIFT_RECORDS 49U",
        b"P314_PAIR_MASK_DETAIL_BASE 0x6c00U",
        b"p314_parse_live_snapshot",
    )
    if any(runtime.count(token) < 1 for token in required):
        raise GeneratorError("P3.14 runtime token missing")
    if runtime.count(b"return P313_DETAIL_CYCLE_EVENT_MULTIPLICITY;") != 0:
        raise GeneratorError("P3.14 legacy 0x6712 emit survived")
    if spec.validate().get("verified") is not True:
        raise GeneratorError("P3.14 telemetry SoT did not validate")
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
        raise GeneratorError("P3.14 output already exists")
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
                    raise GeneratorError(f"short P3.14 write: {path.name}")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    rows: dict[str, Any] = {}
    for key, relative in artifact_paths().items():
        path = output / Path(relative)
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise GeneratorError(f"P3.14 artifact is indirect: {key}")
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
