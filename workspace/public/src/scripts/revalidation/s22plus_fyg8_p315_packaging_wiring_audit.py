#!/usr/bin/env python3
"""Prove the P3.15 proof gate executes before candidate packaging."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import tempfile
from typing import Any

import build_s22plus_fyg8_p315_candidate as builder
import s22plus_fyg8_p315_design_contract as design


SCHEMA = "s22plus_fyg8_p315_packaging_wiring_audit_v1"
VERDICT = "PASS_P315_PREPACKAGING_WIRING_HOST_ONLY"
BUILDER_PATH = Path(
    "workspace/public/src/scripts/revalidation/"
    "build_s22plus_fyg8_p315_candidate.py"
)


class WiringError(ValueError):
    pass


def _call_name(node: ast.Call) -> str:
    parts: list[str] = []
    target: ast.expr = node.func
    while isinstance(target, ast.Attribute):
        parts.append(target.attr)
        target = target.value
    if isinstance(target, ast.Name):
        parts.append(target.id)
    return ".".join(reversed(parts))


def _call_graph(root: Path) -> dict[str, Any]:
    path = root / BUILDER_PATH
    source = path.read_text(encoding="utf-8")
    direct_alias = (
        'sys.modules.setdefault("build_s22plus_fyg8_p315_candidate", '
        "sys.modules[__name__])"
    )
    if (
        source.count(direct_alias) != 1
        or source.index(direct_alias)
        >= source.index("import build_s22plus_fyg8_p314_candidate as parent")
    ):
        raise WiringError("P3.15 direct-script module identity guard differs")
    tree = ast.parse(source, filename=path.as_posix())
    function = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "build_candidate"
        ),
        None,
    )
    if function is None:
        raise WiringError("P3.15 builder entrypoint is missing")
    calls: dict[str, list[int]] = {}
    validation_assignment = False
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            calls.setdefault(_call_name(node), []).append(node.lineno)
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "validation"
            and isinstance(node.value, ast.Call)
            and _call_name(node.value) == "design.validate_successor_artifact"
        ):
            validation_assignment = True
    validator = calls.get("design.validate_successor_artifact", [])
    packager = calls.get("parent.parent.parent.base.build_candidate", [])
    if (
        validator != sorted(validator)
        or packager != sorted(packager)
        or len(validator) != 1
        or len(packager) != 1
        or validator[0] >= packager[0]
        or not validation_assignment
        or source.count("design.validate_successor_artifact") != 1
    ):
        raise WiringError("P3.15 validator-to-packager call graph differs")
    return {
        "builder": BUILDER_PATH.as_posix(),
        "validator_line": validator[0],
        "packager_line": packager[0],
        "validator_precedes_packager": True,
        "validator_return_is_bound": True,
        "direct_script_module_identity_is_canonical": True,
        "verified": True,
    }


def _negative_fixture(root: Path) -> dict[str, Any]:
    builder._configure()  # noqa: SLF001
    base = builder.parent.parent.parent.base
    original = base.build_candidate
    calls = 0

    def forbidden(_args: argparse.Namespace) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise AssertionError("parent packager ran after a failed P3.15 gate")

    outcomes: dict[str, bool] = {}
    base.build_candidate = forbidden
    try:
        private = root / "workspace/private"
        private.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="p315-packaging-negative-", dir=private
        ) as name:
            directory = Path(name)
            invalid = directory / "invalid.json"
            invalid.write_text("{}\n", encoding="ascii")
            for label, closure in (
                ("missing", directory / "missing.json"),
                ("failed", invalid),
            ):
                output = directory / f"candidate-{label}"
                args = builder.parse_args(
                    [
                        "--prepackaging",
                        closure.relative_to(root).as_posix(),
                        "--out",
                        output.relative_to(root).as_posix(),
                    ]
                )
                try:
                    builder.build_candidate(args)
                except (
                    builder.BuildError,
                    design.P315DesignError,
                    OSError,
                    ValueError,
                ):
                    outcomes[label] = not output.exists() and not output.is_symlink()
                else:
                    outcomes[label] = False
    finally:
        base.build_candidate = original
    if calls != 0 or outcomes != {"missing": True, "failed": True}:
        raise WiringError("P3.15 failed-gate packaging behavior differs")
    return {
        "missing_artifact_blocks_packaging": True,
        "failed_artifact_blocks_packaging": True,
        "parent_packager_call_count": 0,
        "package_output_count": 0,
        "verified": True,
    }


def audit(root: Path | None = None) -> dict[str, Any]:
    root = (root or Path(__file__).resolve().parents[5]).resolve()
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "requirements_sha256": design.requirements_sha256(),
        "call_graph": _call_graph(root),
        "negative_fixture": _negative_fixture(root),
        "validator_called_before_parent_packager": True,
        "validator_return_controls_package_creation": True,
        "missing_or_failed_artifact_blocks_packaging": True,
        "device_contact": False,
        "verified": True,
    }


def main() -> int:
    try:
        result = audit()
    except (WiringError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
