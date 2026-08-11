#!/usr/bin/env python3
"""Materialize the P3.16 Max77705 userspace successor from frozen P3.15."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any

import s22plus_fyg8_max77705_checkpoint_transform as checkpoint
import s22plus_fyg8_p315_generator as parent


SCHEMA = "s22plus_fyg8_p316_generator_v1"
P315_INTENT = Path(
    "workspace/private/outputs/s22plus_fyg8_p315/intent/overlay-intent.json"
)
EXPECTED_P315_INTENT = {
    "size": 463601,
    "sha256": "db3b333351645c8dad1a421c147c30b3e83a85f75d0ad64f6ad5117d99c6c9f1",
}
NATIVE_ROOT = Path("workspace/public/src/native-init")
PARSER = NATIVE_ROOT / "s22plus_fyg8_max77705_result_parser.inc.c"
ENVELOPE = NATIVE_ROOT / "s22plus_fyg8_max77705_envelope.inc.c"
RUNTIME_CORE = NATIVE_ROOT / "s22plus_fyg8_max77705_runtime_core.inc.c"
RUNTIME_POLICY = NATIVE_ROOT / "s22plus_fyg8_max77705_runtime_policy.inc.c"
DELTA_KEYS = frozenset(
    {
        "checkpoint_client",
        "p290_checkpoint_header",
        "plan_header",
        "runtime_wrapper",
        "p290_e3_runtime_include",
    }
)


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


def _intent(root: Path) -> dict[str, Any]:
    payload = _stable_regular(
        root / P315_INTENT, "P3.16 frozen P3.15 intent", 2**21
    )
    if {
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    } != EXPECTED_P315_INTENT:
        raise GeneratorError("P3.16 frozen P3.15 intent receipt differs")
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GeneratorError("P3.16 frozen P3.15 intent is invalid") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema")
        != "s22plus_fyg8_p315_userspace_overlay_intent_v1"
        or value.get("verdict")
        != "PASS_P315_USERSPACE_OVERLAY_INTENT_HOST_ONLY"
        or value.get("contract_id")
        != "s22plus-fyg8-p315-live-profile-restart-carrier-v2-observer-v1"
    ):
        raise GeneratorError("P3.16 frozen P3.15 identity differs")
    return value


def frozen_identity(root: Path) -> tuple[bytes, bytes, str]:
    value = _intent(root)
    try:
        run_id = bytes.fromhex(value["run_id"])
        unsat_tag = bytes.fromhex(value["unsat_tag_hex"])
        profile = str(value["profile"])
    except (KeyError, TypeError, ValueError) as exc:
        raise GeneratorError("P3.16 frozen identity is unavailable") from exc
    if len(run_id) != 16 or len(unsat_tag) != 16 or profile != "E2":
        raise GeneratorError("P3.16 frozen identity extent differs")
    return run_id, unsat_tag, profile


def _frozen_bytes(
    root: Path, *, run_id: bytes, unsat_tag: bytes, profile: str
) -> dict[str, bytes]:
    intent = _intent(root)
    if (run_id, unsat_tag, profile) != frozen_identity(root):
        raise GeneratorError("P3.16 requested identity differs from P3.15")
    expected = intent.get("generated_artifacts")
    paths = artifact_paths()
    if not isinstance(expected, dict) or set(expected) != set(paths):
        raise GeneratorError("P3.16 frozen artifact inventory differs")
    base = root / P315_INTENT.parent
    result: dict[str, bytes] = {}
    for key, relative in paths.items():
        payload = _stable_regular(
            base / Path(relative),
            f"P3.16 frozen P3.15 artifact {key}",
            4 * 2**20,
        )
        receipt = {
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        if receipt != expected.get(key):
            raise GeneratorError(f"P3.16 frozen P3.15 artifact changed: {key}")
        result[key] = payload
    return result


def _replace_once(value: bytes, old: bytes, new: bytes, label: str) -> bytes:
    if value.count(old) != 1:
        raise GeneratorError(f"P3.16 {label} anchor differs")
    return value.replace(old, new, 1)


def _transform_plan(value: bytes) -> bytes:
    anchor = b'    {"ucsi_glink.ko", "ucsi_glink", ""},\n};\n'
    replacement = (
        b'    {"ucsi_glink.ko", "ucsi_glink", ""},\n'
        b'    {"msm-geni-se.ko", "msm_geni_se", ""},\n'
        b'    {"gpi.ko", "gpi", ""},\n'
        b'    {"i2c-msm-geni.ko", "i2c_msm_geni", ""},\n'
        b"};\n"
    )
    return _replace_once(value, anchor, replacement, "64-module plan")


def _transform_wrapper(value: bytes) -> bytes:
    value = _replace_once(
        value,
        b'_Static_assert(S22PLUS_O2_MODULE_PLAN_COUNT == 61U, "E2 module count");',
        b'_Static_assert(S22PLUS_O2_MODULE_PLAN_COUNT == 64U, "P3.16 early module count");',
        "early module count",
    )
    anchor = b"""    E1_REQUIRE(S22_R4W1E_STAGE_CHILD_REAPED, 0U, child_reap(&child));

    enum {
"""
    replacement = b"""    E1_REQUIRE(S22_R4W1E_STAGE_CHILD_REAPED, 0U, child_reap(&child));

    long p316_override_rc = p316_prepare_overrides();
    if (p316_override_rc != 0) {
        p316_fail_observer(
            -1, S22PLUS_MAX77705_OBSERVER_SITE_OVERRIDE_PREPARE,
            p316_override_rc, NULL);
    }

    enum {
"""
    return _replace_once(value, anchor, replacement, "pre-module override call")


def _transform_runtime_include(root: Path, value: bytes) -> bytes:
    parser = _stable_regular(root / PARSER, "P3.16 native result parser", 2**20)
    envelope = _stable_regular(root / ENVELOPE, "P3.16 native envelope", 2**20)
    policy = _stable_regular(root / RUNTIME_POLICY, "P3.16 runtime policy", 2**20)
    runtime = _stable_regular(root / RUNTIME_CORE, "P3.16 runtime core", 2**20)
    anchor = b"""static __attribute__((noreturn)) void p290_e3_run(void) {
    p313_run();
}
"""
    replacement = (
        b"\n/* P3.16 strict module-result parser. */\n"
        + parser
        + b"\n/* P3.16 native Carrier-v2 envelope encoder. */\n"
        + envelope
        + b"\n/* P3.16 pure retained-result policy. */\n"
        + policy
        + b"\n/* P3.16 target-only late diagnostic runtime. */\n"
        + runtime
        + b"\nstatic __attribute__((noreturn)) void p290_e3_run(void) {\n"
        + b"    p316_run();\n}\n"
    )
    return _replace_once(value, anchor, replacement, "runtime entrypoint")


def generate_bytes(
    root: Path, *, run_id: bytes, unsat_tag: bytes, profile: str
) -> dict[str, bytes]:
    baseline = _frozen_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    result = dict(baseline)
    result["checkpoint_client"] = checkpoint.transform_checkpoint(
        baseline["checkpoint_client"]
    )
    result["p290_checkpoint_header"] = checkpoint.transform_header(
        baseline["p290_checkpoint_header"]
    )
    result["plan_header"] = _transform_plan(baseline["plan_header"])
    result["runtime_wrapper"] = _transform_wrapper(baseline["runtime_wrapper"])
    result["p290_e3_runtime_include"] = _transform_runtime_include(
        root, baseline["p290_e3_runtime_include"]
    )
    changed = {key for key in result if result[key] != baseline[key]}
    if changed != DELTA_KEYS:
        raise GeneratorError(f"P3.16 delta differs: {sorted(changed)}")
    runtime_value = result["p290_e3_runtime_include"]
    required = (
        b"p316_prepare_overrides",
        b"p316_verify_substrate_bindings",
        b"p316_observe_diagnostic",
        b"p316_publish",
        b"s22plus_max77705_runtime_parse_result",
        b"s22plus_max77705_encode_envelope",
        b"p316_run();",
    )
    if any(runtime_value.count(token) < 1 for token in required):
        raise GeneratorError("P3.16 runtime token missing")
    if result["plan_header"].count(b"s22plus_max77705_mux_diag.ko") != 0:
        raise GeneratorError("P3.16 diagnostic leaked into the early plan")
    if result["plan_header"].count(b".ko\"") != 64:
        raise GeneratorError("P3.16 early module plan count differs")
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
        raise GeneratorError("P3.16 output already exists")
    output.mkdir(mode=0o700, parents=False)
    data = generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
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
                    raise GeneratorError(f"short P3.16 write: {path.name}")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    rows: dict[str, Any] = {}
    for key, relative in artifact_paths().items():
        path = output / Path(relative)
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise GeneratorError(f"P3.16 artifact is indirect: {key}")
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


def main() -> int:
    root = Path(__file__).resolve().parents[5]
    run_id, unsat_tag, profile = frozen_identity(root)
    generated = generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "artifact_count": len(generated),
                "delta_keys": sorted(DELTA_KEYS),
                "module_plan_count": 64,
                "verified": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
