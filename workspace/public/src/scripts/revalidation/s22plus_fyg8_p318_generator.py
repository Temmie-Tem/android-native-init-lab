#!/usr/bin/env python3
"""Materialize the P3.18 timing/latch successor from frozen P3.17 bytes.

Host-only.  P3.17 SOURCE_KEYS remain untouched.  The delta adds one first
early latch module, replaces the late diagnostic with its timed P3.18 build,
and replaces only the result parser, terminal publisher, and envelope path.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any

import s22plus_fyg8_p317_generator as parent


SCHEMA = "s22plus_fyg8_p318_generator_v1"
NATIVE_ROOT = Path("workspace/public/src/native-init")
P317_RESULT_PARSER = NATIVE_ROOT / "s22plus_fyg8_max77705_result_parser.inc.c"
P318_RESULT_PARSER = NATIVE_ROOT / "s22plus_fyg8_p318_max77705_result_parser.inc.c"
P317_ENVELOPE = NATIVE_ROOT / "s22plus_fyg8_p317_max77705_envelope.inc.c"
P318_LATCH_PARSER = NATIVE_ROOT / "s22plus_fyg8_p318_dwc3_latch_parser.inc.c"
P318_BANNER_WRITER = NATIVE_ROOT / "s22plus_fyg8_p318_banner_writer.inc.c"
P318_ENVELOPE = NATIVE_ROOT / "s22plus_fyg8_p318_max77705_envelope.inc.c"
P317_RUNTIME = NATIVE_ROOT / "s22plus_fyg8_p317_max77705_runtime.inc.c"
P318_RUNTIME = NATIVE_ROOT / "s22plus_fyg8_p318_max77705_runtime.inc.c"
DELTA_KEYS = frozenset({"plan_header", "runtime_wrapper", "p290_e3_runtime_include"})
EXPECTED_EARLY_COUNT = 70
EXPECTED_LATE_COUNT = 1
EXPECTED_EFFECTIVE_COUNT = 71
EXPECTED_PROVIDER_LAST_INDEX = 66


class GeneratorError(ValueError):
    pass


def artifact_paths() -> dict[str, PurePosixPath]:
    return parent.artifact_paths()


def frozen_identity(root: Path) -> tuple[bytes, bytes, str]:
    return parent.frozen_identity(root)


def _stable_regular(path: Path, label: str, maximum: int = 2**20) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
        if path.is_symlink() or not path.is_file() or not 0 < before.st_size <= maximum:
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


def _replace_once(value: bytes, old: bytes, new: bytes, label: str) -> bytes:
    if value.count(old) != 1:
        raise GeneratorError(f"P3.18 {label} anchor differs")
    return value.replace(old, new, 1)


def _replace_region(
    value: bytes, start: bytes, end: bytes, replacement: bytes, label: str
) -> bytes:
    if value.count(start) != 1 or value.count(end) != 1:
        raise GeneratorError(f"P3.18 {label} region differs")
    left = value.index(start)
    right = value.index(end, left)
    if right <= left:
        raise GeneratorError(f"P3.18 {label} region is reversed")
    return value[:left] + replacement + b"\n\n" + value[right:]


def _transform_plan(value: bytes) -> bytes:
    anchor = (
        b"static const struct s22plus_o2_module_plan_entry "
        b"s22plus_o2_module_plan[] = {\n"
    )
    latch = b'    {"s22plus_dwc3_event_latch.ko", "s22plus_dwc3_event_latch", ""},\n'
    return _replace_once(value, anchor, anchor + latch, "70-module early plan")


def _transform_wrapper(value: bytes) -> bytes:
    return _replace_once(
        value,
        b'_Static_assert(S22PLUS_O2_MODULE_PLAN_COUNT == 69U, "P3.17 early module count");',
        b'_Static_assert(S22PLUS_O2_MODULE_PLAN_COUNT == 70U, "P3.18 early module count");',
        "early module count",
    )


def _transform_p317_runtime(root: Path, value: bytes) -> bytes:
    replacement = _stable_regular(root / P318_RUNTIME, "P3.18 runtime replacement")
    value = _replace_region(
        value,
        b"static __attribute__((noreturn)) void p317_publish(\n",
        b"static __attribute__((noreturn)) void p317_fail_observer(\n",
        replacement,
        "terminal publisher",
    )
    value = _replace_once(
        value,
        b"#define P317_PROVIDER_CHAIN_LAST_MODULE_INDEX 65U",
        b"#define P317_PROVIDER_CHAIN_LAST_MODULE_INDEX 66U",
        "provider hook index",
    )
    value = _replace_once(
        value,
        b"observer_site > S22PLUS_MAX77705_P317_OBSERVER_SITE_WAITING)",
        b"observer_site > S22PLUS_MAX77705_P318_OBSERVER_SITE_TIMING_LATCH)",
        "observer site ceiling",
    )
    gate_anchor = b"""    p290_progress_position(S22_P313_POSITION_DIRECT_OBSERVER_READY, 0U);
    rc = p260_bind_udc();
"""
    gate_replacement = b"""    p290_progress_position(S22_P313_POSITION_DIRECT_OBSERVER_READY, 0U);
    rc = p318_arm_exposure_gate();
    if (rc != 0) p317_fail_observer(
        tty_fd, S22PLUS_MAX77705_P318_OBSERVER_SITE_EXPOSURE_GATE,
        rc, NULL);
    rc = p260_bind_udc();
"""
    value = _replace_once(
        value, gate_anchor, gate_replacement, "readback-before-sole-bind seam"
    )
    value = _replace_once(
        value,
        b"static __attribute__((noreturn)) void p317_run(void)",
        b"static __attribute__((noreturn)) void p318_run(void)",
        "runtime entry definition",
    )
    return value


def _transform_runtime_include(root: Path, value: bytes) -> bytes:
    old_parser = _stable_regular(root / P317_RESULT_PARSER, "P3.17 result parser")
    new_parser = _stable_regular(root / P318_RESULT_PARSER, "P3.18 result parser")
    p317_envelope = _stable_regular(root / P317_ENVELOPE, "P3.17 envelope")
    latch_parser = _stable_regular(root / P318_LATCH_PARSER, "P3.18 latch parser")
    banner_writer = _stable_regular(root / P318_BANNER_WRITER, "P3.18 banner writer")
    p318_envelope = _stable_regular(root / P318_ENVELOPE, "P3.18 envelope")
    p317_runtime = _stable_regular(root / P317_RUNTIME, "P3.17 runtime")
    transformed_runtime = _transform_p317_runtime(root, p317_runtime)
    if transformed_runtime.count(b"p260_bind_udc();") != 1:
        raise GeneratorError("P3.18 selected runtime UDC bind is not unique")

    value = _replace_once(value, old_parser, new_parser, "timed result parser")
    value = _replace_once(
        value,
        p317_envelope,
        p317_envelope
        + b"\n/* P3.18 exact latch/readback parser. */\n"
        + latch_parser
        + b"\n/* P3.18 absolute-deadline banner writer. */\n"
        + banner_writer
        + b"\n/* P3.18 fixed 128-byte timing envelope v4. */\n"
        + p318_envelope,
        "v4 envelope closure",
    )
    value = _replace_once(
        value, p317_runtime, transformed_runtime, "runtime replacement"
    )
    if value.count(b"s22plus_max77705_mux_diag") != 3:
        raise GeneratorError("P3.18 predecessor diagnostic identity differs")
    value = value.replace(
        b"s22plus_max77705_mux_diag",
        b"s22plus_max77705_mux_diag_p318",
    )
    value = _replace_once(
        value, b"    p317_run();\n", b"    p318_run();\n", "runtime entry call"
    )
    return value


def generate_bytes(
    root: Path, *, run_id: bytes, unsat_tag: bytes, profile: str
) -> dict[str, bytes]:
    baseline = parent.generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    result = dict(baseline)
    result["plan_header"] = _transform_plan(baseline["plan_header"])
    result["runtime_wrapper"] = _transform_wrapper(baseline["runtime_wrapper"])
    result["p290_e3_runtime_include"] = _transform_runtime_include(
        root, baseline["p290_e3_runtime_include"]
    )
    changed = {key for key in result if result[key] != baseline[key]}
    if changed != DELTA_KEYS:
        raise GeneratorError(f"P3.18 delta differs: {sorted(changed)}")
    plan = result["plan_header"]
    runtime = result["p290_e3_runtime_include"]
    wrapper = result["runtime_wrapper"]
    if plan.count(b'.ko"') != EXPECTED_EARLY_COUNT:
        raise GeneratorError("P3.18 early module plan count differs")
    if not plan.startswith(b"#ifndef") or plan.count(
        b'{"s22plus_dwc3_event_latch.ko", "s22plus_dwc3_event_latch", ""}'
    ) != 1:
        raise GeneratorError("P3.18 early latch plan differs")
    if plan.count(b"s22plus_max77705_mux_diag_p318.ko") != 0:
        raise GeneratorError("P3.18 late diagnostic leaked into the early plan")
    required_runtime = (
        b"p318_arm_exposure_gate();",
        b"p260_bind_udc();",
        b"s22plus_p318_parse_latch_snapshot",
        b"s22plus_p318_banner_attempt",
        b"s22plus_max77705_p318_encode_envelope",
        b"s22plus_max77705_mux_diag_p318.ko",
        b"/sys/module/s22plus_max77705_mux_diag_p318/parameters/result",
        b"p318_run();",
    )
    if any(runtime.count(token) < 1 for token in required_runtime):
        raise GeneratorError("P3.18 runtime token missing")
    ordered_gate = b"p318_arm_exposure_gate();\n    if (rc != 0) p317_fail_observer("
    ordered_bind = b"        rc, NULL);\n    rc = p260_bind_udc();"
    if runtime.count(ordered_gate) != 1 or runtime.count(ordered_bind) != 1:
        raise GeneratorError("P3.18 exposure gate/sole selected bind order differs")
    if wrapper.count(b"P317_PROVIDER_CHAIN_LAST_MODULE_INDEX") != 1:
        raise GeneratorError("P3.18 provider hook differs")
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
        raise GeneratorError("P3.18 output already exists")
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
                    raise GeneratorError(f"short P3.18 write: {path.name}")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    rows: dict[str, Any] = {}
    for key, relative in artifact_paths().items():
        path = output / Path(relative)
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise GeneratorError(f"P3.18 artifact is indirect: {key}")
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
        "early_module_count": EXPECTED_EARLY_COUNT,
        "late_diagnostic_payload_count": EXPECTED_LATE_COUNT,
        "effective_module_count": EXPECTED_EFFECTIVE_COUNT,
        "provider_last_index": EXPECTED_PROVIDER_LAST_INDEX,
        "artifacts": rows,
        "verified": True,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[5]
    run_id, unsat_tag, profile = frozen_identity(root)
    generated = generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    print(json.dumps({
        "schema": SCHEMA,
        "artifact_count": len(generated),
        "delta_keys": sorted(DELTA_KEYS),
        "early_module_count": EXPECTED_EARLY_COUNT,
        "late_diagnostic_payload_count": EXPECTED_LATE_COUNT,
        "effective_module_count": EXPECTED_EFFECTIVE_COUNT,
        "verified": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
