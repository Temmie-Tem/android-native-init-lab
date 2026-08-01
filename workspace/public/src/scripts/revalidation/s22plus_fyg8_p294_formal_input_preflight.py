#!/usr/bin/env python3
"""Validate the exact P2.94 formal invocation shape without running formal."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any

import s22plus_fyg8_p294_build_repro_check as formal


SCHEMA = "s22plus_fyg8_p294_formal_input_preflight_v1"
VERDICT = "PASS_P294_FORMAL_INPUT_SHAPE_HOST_ONLY"


class PreflightError(ValueError):
    pass


def _resolve(root: Path, value: Path) -> Path:
    return value.resolve() if value.is_absolute() else (root / value).resolve()


def _regular(path: Path, label: str) -> bytes:
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise PreflightError(f"{label} is missing or indirect")
    value = path.read_bytes()
    if not value:
        raise PreflightError(f"{label} is empty")
    return value


def _receipt(path: Path, label: str) -> dict[str, Any]:
    value = _regular(path, label)
    return {
        "size": len(value),
        "sha256": hashlib.sha256(value).hexdigest(),
    }


def _build_directory(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_dir():
        raise PreflightError(f"{label} is missing or indirect")
    expected = set(formal.ARTIFACT_LIMITS)
    observed = {entry.name for entry in path.iterdir()}
    if observed != expected:
        raise PreflightError(
            f"{label} inventory mismatch: expected={sorted(expected)}; "
            f"observed={sorted(observed)}"
        )
    result_data = _regular(path / "build-result.json", f"{label} result")
    try:
        result = json.loads(result_data)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PreflightError(f"{label} result is not JSON") from exc
    if (
        not isinstance(result, dict)
        or result.get("schema") != formal.build.SCHEMA
        or not isinstance(result.get("outputs"), list)
    ):
        raise PreflightError(f"{label} result shape differs")
    rows = {
        row.get("name"): row
        for row in result["outputs"]
        if isinstance(row, dict) and row.get("name") in expected
    }
    required = expected - {"build-result.json"}
    if set(rows) != required:
        raise PreflightError(f"{label} output receipt inventory differs")
    receipts = {
        "build-result.json": {
            "size": len(result_data),
            "sha256": hashlib.sha256(result_data).hexdigest(),
        }
    }
    for name in sorted(required):
        receipt = _receipt(path / name, f"{label} {name}")
        row = rows[name]
        if any(row.get(field) != receipt[field] for field in ("size", "sha256")):
            raise PreflightError(f"{label} output receipt differs: {name}")
        receipts[name] = receipt
    return {
        "path": str(path),
        "inventory": sorted(observed),
        "receipts": receipts,
        "verified": True,
    }


def validate(
    root: Path,
    *,
    build_a: Path,
    build_b: Path,
    intent: Path,
    patch: Path,
    nm: Path,
    objdump: Path,
    formal_result: Path,
) -> dict[str, Any]:
    repository = root.resolve()
    argv = [
        "--build-a", str(build_a),
        "--build-b", str(build_b),
        "--intent", str(intent),
        "--patch", str(patch),
        "--nm", str(nm),
        "--objdump", str(objdump),
    ]
    parsed = formal.parse_args(argv)
    if parsed.source != formal.DEFAULT_SOURCE or "--source" in argv:
        raise PreflightError("formal source is not the producer default")
    source = _resolve(repository, parsed.source)
    if source.is_symlink() or not source.is_dir():
        raise PreflightError("formal producer source is missing or indirect")
    directory_a = _resolve(repository, parsed.build_a)
    directory_b = _resolve(repository, parsed.build_b)
    if directory_a == directory_b:
        raise PreflightError("formal build directories are not distinct")
    selected_result = _resolve(repository, formal_result)
    if selected_result.exists() or selected_result.is_symlink():
        raise PreflightError("formal result path already exists")
    tools = {}
    for name, selected in (("nm", parsed.nm), ("objdump", parsed.objdump)):
        path = _resolve(repository, selected)
        metadata = path.lstat()
        if (
            path.is_symlink()
            or not stat.S_ISREG(metadata.st_mode)
            or not os.access(path, os.X_OK)
        ):
            raise PreflightError(f"formal {name} is missing, indirect, or not executable")
        tools[name] = {"path": str(path), **_receipt(path, f"formal {name}")}
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "source_mode": "producer-default",
        "source_argument_omitted": True,
        "resolved_source": str(source),
        "build_a": _build_directory(directory_a, "formal build A"),
        "build_b": _build_directory(directory_b, "formal build B"),
        "intent": _receipt(_resolve(repository, parsed.intent), "formal intent"),
        "patch": _receipt(_resolve(repository, parsed.patch), "formal patch"),
        "tools": tools,
        "formal_result": str(selected_result),
        "formal_result_absent": True,
        "formal_invoked": False,
        "verified": True,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[5])
    parser.add_argument("--build-a", type=Path, required=True)
    parser.add_argument("--build-b", type=Path, required=True)
    parser.add_argument("--intent", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--nm", type=Path, required=True)
    parser.add_argument("--objdump", type=Path, required=True)
    parser.add_argument("--formal-result", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = validate(
            args.repo_root,
            build_a=args.build_a,
            build_b=args.build_b,
            intent=args.intent,
            patch=args.patch,
            nm=args.nm,
            objdump=args.objdump,
            formal_result=args.formal_result,
        )
    except (PreflightError, OSError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
