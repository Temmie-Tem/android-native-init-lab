#!/usr/bin/env python3
"""Qualify the actual P3.18 generated runtime and pre-UDC latch seam."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

import s22plus_fyg8_p317_userspace_build as userspace
import s22plus_fyg8_p318_generator as generator


SCHEMA = "s22plus_fyg8_p318_runtime_qualification_v1"
VERDICT = "PASS_P318_RUNTIME_GATE_AND_V4_PUBLISH_H0"
NATIVE = Path("workspace/public/src/native-init")
PREFIX = Path("workspace/public/src/scripts/revalidation")
SOURCES = (
    NATIVE / "s22plus_fyg8_p318_max77705_result_parser.inc.c",
    NATIVE / "s22plus_fyg8_p318_dwc3_latch_parser.inc.c",
    NATIVE / "s22plus_fyg8_p318_banner_writer.inc.c",
    NATIVE / "s22plus_fyg8_p318_max77705_envelope.inc.c",
    NATIVE / "s22plus_fyg8_p318_max77705_runtime.inc.c",
    NATIVE / "s22plus_fyg8_p318_runtime_gate_fixture.c",
    PREFIX / "s22plus_fyg8_p318_generator.py",
    PREFIX / "s22plus_fyg8_p318_runtime_qualification.py",
)
DEFAULT_OUTPUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "runtime-qualification-20260814-01.json"
)


class RuntimeQualificationError(RuntimeError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _receipt(path: Path) -> dict[str, Any]:
    value = path.read_bytes()
    return {"path": str(path), "size": len(value), "sha256": _sha256_bytes(value)}


def _function(value: bytes, marker: bytes) -> bytes:
    if value.count(marker) != 1:
        raise RuntimeQualificationError(f"runtime marker differs: {marker!r}")
    start = value.index(marker)
    brace = value.index(b"{", start)
    depth = 0
    for index in range(brace, len(value)):
        if value[index] == ord("{"):
            depth += 1
        elif value[index] == ord("}"):
            depth -= 1
            if depth == 0:
                return value[start : index + 1]
    raise RuntimeQualificationError(f"runtime function is unterminated: {marker!r}")


def _ordered(value: bytes, label: str, tokens: tuple[bytes, ...]) -> None:
    cursor = -1
    for token in tokens:
        cursor = value.find(token, cursor + 1)
        if cursor < 0:
            raise RuntimeQualificationError(f"{label} lacks ordered token {token!r}")


def _run_gate_fixture(root: Path, directory: Path) -> dict[str, Any]:
    cc = shutil.which("cc")
    if cc is None:
        raise RuntimeQualificationError("host C compiler is unavailable")
    binary = directory / "p318-runtime-gate-fixture"
    completed = subprocess.run(
        [
            cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
            "-I", str(root / NATIVE),
            str(root / NATIVE / "s22plus_fyg8_p318_runtime_gate_fixture.c"),
            "-o", str(binary),
        ],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeQualificationError(
            f"runtime gate fixture compile failed: {completed.stderr!r}"
        )
    executed = subprocess.run(
        [str(binary)], cwd=root, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if executed.returncode != 0:
        raise RuntimeQualificationError(
            f"runtime gate fixture failed: {executed.stderr!r}"
        )
    try:
        result = json.loads(executed.stdout.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeQualificationError("runtime gate fixture output differs") from exc
    expected = {
        "schema": "s22plus_fyg8_p318_runtime_gate_fixture_v1",
        "positive": 2,
        "negative": 5,
        "verdict": "PASS",
    }
    if result != expected:
        raise RuntimeQualificationError(f"runtime gate fixture result differs: {result}")
    return {
        "result": result,
        "binary_size": binary.stat().st_size,
        "binary_sha256": _sha256_bytes(binary.read_bytes()),
        "actual_gate_helper_executed": True,
    }


def _compile_userspace(
    root: Path, materialized: Path, run_id: bytes, profile: str, directory: Path
) -> tuple[dict[str, Any], dict[str, bytes]]:
    previous = userspace._P317SourceModule.MODULE_PLAN_COUNT  # noqa: SLF001
    userspace._P317SourceModule.MODULE_PLAN_COUNT = 70  # noqa: SLF001
    try:
        result = userspace._compile(  # noqa: SLF001
            root,
            directory,
            {"run_id": run_id.hex(), "profile": profile},
            materialized,
            userspace.base.require_tools(),
        )
    finally:
        userspace._P317SourceModule.MODULE_PLAN_COUNT = previous  # noqa: SLF001
    return result, {
        "init": (directory / "init").read_bytes(),
        "child": (directory / "s22-e1-child").read_bytes(),
    }


def audit(repo_root: Path | None = None) -> dict[str, Any]:
    root = (repo_root or Path(__file__).resolve().parents[5]).resolve()
    run_id, unsat_tag, profile = generator.frozen_identity(root)
    generated = generator.generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    plan = generated["plan_header"]
    runtime = generated["p290_e3_runtime_include"]
    selected = _function(
        runtime, b"static __attribute__((noreturn)) void p318_run(void)"
    )
    publisher = _function(
        runtime,
        b"static __attribute__((noreturn)) void p317_publish(\n",
    )
    if selected.count(b"p260_bind_udc();") != 1:
        raise RuntimeQualificationError("selected P3.18 UDC bind count differs")
    _ordered(
        selected,
        "selected P3.18 UDC seam",
        (
            b"p282_trace_setup(P282_PHASE_BIND, &direct_control)",
            b"p318_arm_exposure_gate();",
            b"S22PLUS_MAX77705_P318_OBSERVER_SITE_EXPOSURE_GATE",
            b"p260_bind_udc();",
            b"S22_P313_POSITION_DIRECT_BIND_RETURNED",
        ),
    )
    _ordered(
        publisher,
        "selected P3.18 terminal path",
        (
            b"banner = p318_terminal_banner(tty_fd);",
            b"p318_capture_terminal_latch(&latch)",
            b"S22PLUS_MAX77705_P318_OBSERVER_SITE_TIMING_LATCH",
            b"s22plus_max77705_p318_encode_envelope(",
            b"s22_max77705_checkpoint_payload_progress_position(",
            b"s22_max77705_checkpoint_payload_terminal_position(",
            b"p290_park_after_confirmed_publication();",
        ),
    )
    if b"p260_write_banner" in publisher:
        raise RuntimeQualificationError("P3.18 selected publisher discards old banner rc")
    if plan.count(b'.ko"') != 70 or plan.count(
        b's22plus_dwc3_event_latch.ko'
    ) != 1:
        raise RuntimeQualificationError("P3.18 70-module early plan differs")
    if runtime.count(b"s22plus_max77705_mux_diag_p318.ko") != 1 or runtime.count(
        b"/sys/module/s22plus_max77705_mux_diag_p318/parameters/result"
    ) != 1:
        raise RuntimeQualificationError("P3.18 late diagnostic identity differs")

    with tempfile.TemporaryDirectory(prefix="s22-p318-runtime-qualification-") as name:
        temporary = Path(name)
        fixture = _run_gate_fixture(root, temporary)
        trees = []
        for side in ("a", "b"):
            tree = temporary / f"intent-{side}"
            generator.materialize(
                root, tree, run_id=run_id, unsat_tag=unsat_tag, profile=profile
            )
            trees.append(tree)
        for key, relative in generator.artifact_paths().items():
            if (trees[0] / relative).read_bytes() != (trees[1] / relative).read_bytes():
                raise RuntimeQualificationError(
                    f"P3.18 materialized A/B source differs: {key}"
                )
        compiled: list[dict[str, Any]] = []
        binaries: list[dict[str, bytes]] = []
        for side, tree in zip(("a", "b"), trees, strict=True):
            output = temporary / f"compile-{side}"
            output.mkdir()
            metadata, payload = _compile_userspace(
                root, tree / "materialized-sources", run_id, profile, output
            )
            compiled.append(metadata)
            binaries.append(payload)
        if compiled[0] != compiled[1] or binaries[0] != binaries[1]:
            raise RuntimeQualificationError("P3.18 userspace A/B differs")

    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "host_only": True,
        "device_contact": False,
        "source_identities": [_receipt(root / path) for path in SOURCES],
        "generator": {
            "schema": generator.SCHEMA,
            "delta_keys": sorted(generator.DELTA_KEYS),
            "early_module_count": generator.EXPECTED_EARLY_COUNT,
            "late_diagnostic_payload_count": generator.EXPECTED_LATE_COUNT,
            "effective_module_count": generator.EXPECTED_EFFECTIVE_COUNT,
            "provider_last_index": generator.EXPECTED_PROVIDER_LAST_INDEX,
            "materialized_a_b_byte_identical": True,
        },
        "runtime": {
            "gate_readback_precedes_selected_sole_udc_bind": True,
            "exposure_gate_observer_site_distinct": True,
            "timing_latch_observer_site_distinct": True,
            "banner_attempt_precedes_terminal_envelope": True,
            "old_unchecked_banner_call_absent_from_selected_publisher": True,
            "late_timed_diagnostic_path_exact": True,
        },
        "gate_fixture": fixture,
        "userspace_a_b": {
            "byte_identical": True,
            "init": {
                "size": len(binaries[0]["init"]),
                "sha256": _sha256_bytes(binaries[0]["init"]),
                "static_aarch64": compiled[0]["init"]["static_aarch64"],
            },
            "child": {
                "size": len(binaries[0]["child"]),
                "sha256": _sha256_bytes(binaries[0]["child"]),
                "static_aarch64": compiled[0]["child"]["static_aarch64"],
            },
        },
        "process_v2_integration": False,
        "candidate_packaged": False,
        "candidate_ready": False,
        "live_authority": False,
        "verified": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        value = audit(args.repo_root)
    except (RuntimeQualificationError, generator.GeneratorError, OSError,
            subprocess.SubprocessError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    rendered = json.dumps(value, indent=2, sort_keys=True) + "\n"
    root = (args.repo_root or Path(__file__).resolve().parents[5]).resolve()
    output = args.output.resolve() if args.output else root / DEFAULT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(output)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
