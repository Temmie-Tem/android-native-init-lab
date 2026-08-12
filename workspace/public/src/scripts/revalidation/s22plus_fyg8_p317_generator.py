#!/usr/bin/env python3
"""Materialize the P3.17 executability-witness successor from P3.16.

Host-only.  The generator preserves the frozen P3.16 userspace artifacts,
inserts exactly the five modules derived by the reviewed fixed point, captures
the provider chain before the target I2C consumer can be instantiated, and
switches only the retained Max77705 envelope/runtime to P3.17 v3.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any

import s22plus_fyg8_p316_generator as parent
import s22plus_fyg8_p317_executability_fixed_point as fixed_point


SCHEMA = "s22plus_fyg8_p317_generator_v1"
NATIVE_ROOT = Path("workspace/public/src/native-init")
P317_ENVELOPE = NATIVE_ROOT / "s22plus_fyg8_p317_max77705_envelope.inc.c"
P317_RUNTIME = NATIVE_ROOT / "s22plus_fyg8_p317_max77705_runtime.inc.c"
DELTA_KEYS = frozenset({"plan_header", "runtime_wrapper", "p290_e3_runtime_include"})
EXPECTED_ADDED_MODULES = fixed_point.EXPECTED_NEW_MODULES
EXPECTED_EARLY_COUNT = fixed_point.EXPECTED_SUCCESSOR_EARLY_COUNT
EXPECTED_PROVIDER_LAST_INDEX = 65


class GeneratorError(ValueError):
    pass


def artifact_paths() -> dict[str, PurePosixPath]:
    return parent.artifact_paths()


def frozen_identity(root: Path) -> tuple[bytes, bytes, str]:
    return parent.frozen_identity(root)


def _stable_regular(path: Path, label: str, maximum: int) -> bytes:
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
        raise GeneratorError(f"P3.17 {label} anchor differs")
    return value.replace(old, new, 1)


def _transform_plan(value: bytes) -> bytes:
    anchor = b'    {"msm-geni-se.ko", "msm_geni_se", ""},\n'
    additions = (
        b'    {"spmi-pmic-arb.ko", "spmi_pmic_arb", ""},\n'
        b'    {"pinctrl-spmi-gpio.ko", "pinctrl_spmi_gpio", ""},\n'
        b'    {"qti-regmap-debugfs.ko", "qti_regmap_debugfs", ""},\n'
        b'    {"regmap-spmi.ko", "regmap_spmi", ""},\n'
        b'    {"qcom-spmi-pmic.ko", "qcom_spmi_pmic", ""},\n'
    )
    return _replace_once(value, anchor, additions + anchor, "69-module plan")


def _transform_wrapper(value: bytes) -> bytes:
    value = _replace_once(
        value,
        b'_Static_assert(S22PLUS_O2_MODULE_PLAN_COUNT == 64U, "P3.16 early module count");',
        b'_Static_assert(S22PLUS_O2_MODULE_PLAN_COUNT == 69U, "P3.17 early module count");',
        "early module count",
    )
    value = _replace_once(
        value,
        b"""        p316_fail_observer(
            -1, S22PLUS_MAX77705_OBSERVER_SITE_OVERRIDE_PREPARE,
            p316_override_rc, NULL);
""",
        b"""        p317_fail_observer(
            -1, S22PLUS_MAX77705_OBSERVER_SITE_OVERRIDE_PREPARE,
            p316_override_rc, NULL);
""",
        "pre-module observer publisher",
    )
    anchor = b"""        if (p305_folded_load_rc != 0) {
            fail_at(
                S22_P241_MODULE_STAGE_BASE + P305_FOLDED_MODULE_INDEX,
                P305_FOLDED_MODULE_INDEX,
                (long)(P305_FOLDED_FAILURE_BASE + index));
        }
"""
    replacement = anchor + b"""        if (index == P317_PROVIDER_CHAIN_LAST_MODULE_INDEX) {
            long p317_provider_rc = p317_capture_preclient_provider();
            if (p317_provider_rc != 0) {
                p317_fail_observer(
                    -1, S22PLUS_MAX77705_P317_OBSERVER_SITE_PROVIDER_PRE,
                    p317_provider_rc, NULL);
            }
            if (!p317_provider_ready(
                g_p317_exec.pre_present, g_p317_exec.pre_bound)) {
                p317_fail_precondition(
                    -1,
                    S22PLUS_MAX77705_P317_TERMINAL_PROVIDER_PRECONDITION,
                    NULL);
            }
        }
"""
    return _replace_once(value, anchor, replacement, "pre-consumer provider hook")


def _transform_runtime_include(root: Path, value: bytes) -> bytes:
    envelope = _stable_regular(root / P317_ENVELOPE, "P3.17 envelope", 2**20)
    runtime = _stable_regular(root / P317_RUNTIME, "P3.17 runtime", 2**20)
    anchor = b"""static __attribute__((noreturn)) void p290_e3_run(void) {
    p316_run();
}
"""
    replacement = (
        b"\n/* P3.17 fixed-size executability envelope v3. */\n"
        + envelope
        + b"\n/* P3.17 boot-specific executability witness. */\n"
        + runtime
        + b"\nstatic __attribute__((noreturn)) void p290_e3_run(void) {\n"
        + b"    p317_run();\n}\n"
    )
    return _replace_once(value, anchor, replacement, "runtime entrypoint")


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
        raise GeneratorError(f"P3.17 delta differs: {sorted(changed)}")
    plan = result["plan_header"]
    runtime = result["p290_e3_runtime_include"]
    wrapper = result["runtime_wrapper"]
    if plan.count(b'.ko"') != EXPECTED_EARLY_COUNT:
        raise GeneratorError("P3.17 early module plan count differs")
    for name in EXPECTED_ADDED_MODULES:
        if plan.count(name.encode("ascii")) != 1:
            raise GeneratorError(f"P3.17 derived module differs: {name}")
    if plan.count(b"s22plus_max77705_mux_diag.ko") != 0:
        raise GeneratorError("P3.17 diagnostic leaked into the early plan")
    required_runtime = (
        b"s22plus_max77705_p317_encode_envelope",
        b"p317_capture_preclient_provider",
        b"p317_capture_policy",
        b"p317_capture_post_provider",
        b"p317_capture_waiting",
        b"p317_capture_supplier",
        b"p317_publish",
        b"p317_run();",
    )
    if any(runtime.count(token) < 1 for token in required_runtime):
        raise GeneratorError("P3.17 runtime token missing")
    if wrapper.count(b"P317_PROVIDER_CHAIN_LAST_MODULE_INDEX") != 1:
        raise GeneratorError("P3.17 pre-consumer hook differs")
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
        raise GeneratorError("P3.17 output already exists")
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
                    raise GeneratorError(f"short P3.17 write: {path.name}")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    rows: dict[str, Any] = {}
    for key, relative in artifact_paths().items():
        path = output / Path(relative)
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise GeneratorError(f"P3.17 artifact is indirect: {key}")
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
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "artifact_count": len(generated),
                "delta_keys": sorted(DELTA_KEYS),
                "module_plan_count": EXPECTED_EARLY_COUNT,
                "verified": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
