#!/usr/bin/env python3
"""Measure the real P3.17 poll payload against the proposed P3.18 budget."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
import types
from typing import Any


SCHEMA = "s22plus_fyg8_p318_p317_poll_budget_measurement_v1"
VERDICT = "PASS_P318_P317_POLL_BUDGET_MEASURED_H0"
RUN_RELATIVE = Path(
    "workspace/private/runs/device-action-f1-live-v2/"
    "f1-2026-08-12T165954582328Z-1786553994582372233"
)
DEFAULT_LIVE_STATE = RUN_RELATIVE / "live-state.json"
DEFAULT_TELEMETRY_SOURCE = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_max77705_telemetry.py"
)
P317_SCHEMA = "s22plus_fyg8_p317_max77705_telemetry_v3"
EXPECTED_P317_RECORDS = 2
PROPOSED_V4_LOSSLESS_CAPACITY = 47


class MeasurementError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "AGENTS.md").is_file() and (parent / "GOAL.md").is_file():
            return parent
    raise MeasurementError("repository root not found")


def _identity(stat_result: Any) -> tuple[int, int, int, int]:
    return (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        stat_result.st_mtime_ns,
    )


def stable_read(path: Path, label: str, limit: int) -> bytes:
    try:
        with path.open("rb") as handle:
            before = _identity(path.stat())
            data = handle.read(limit + 1)
            after = _identity(path.stat())
    except OSError as exc:
        raise MeasurementError(f"unable to read {label}") from exc
    if before != after:
        raise MeasurementError(f"{label} changed while read")
    if len(data) > limit:
        raise MeasurementError(f"{label} exceeds bounded read")
    return data


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _poll_vectors(row: dict[str, Any]) -> tuple[bytes, bytes, bytes, bytes]:
    max77705 = row.get("max77705")
    if not isinstance(max77705, dict) or max77705.get("schema") != P317_SCHEMA:
        raise MeasurementError("P3.17 record schema differs")
    result = max77705.get("result")
    if not isinstance(result, dict):
        raise MeasurementError("P3.17 record lacks diagnostic result")
    encoded_vectors = result.get("poll_bytes")
    if not isinstance(encoded_vectors, list) or len(encoded_vectors) != 4:
        raise MeasurementError("P3.17 poll vector shape differs")
    vectors: list[bytes] = []
    for encoded in encoded_vectors:
        if not isinstance(encoded, dict) or encoded.get("encoding") != "hex":
            raise MeasurementError("P3.17 poll vector encoding differs")
        value = encoded.get("value")
        if not isinstance(value, str):
            raise MeasurementError("P3.17 poll vector value differs")
        try:
            vectors.append(bytes.fromhex(value))
        except ValueError as exc:
            raise MeasurementError("P3.17 poll vector is not hex") from exc
    return tuple(vectors)  # type: ignore[return-value]


def _load_packbits_authority(source_data: bytes) -> types.ModuleType:
    try:
        source = source_data.decode("utf-8", "strict")
        tree = ast.parse(source)
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise MeasurementError("PackBits authority source cannot be parsed") from exc
    selected: list[ast.stmt] = []
    encoding_value: int | None = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "TelemetryError":
            selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in {
            "packbits_encode",
            "packbits_decode",
        }:
            selected.append(node)
        elif isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "POLL_ENCODING_PACKBITS"
            for target in node.targets
        ):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError) as exc:
                raise MeasurementError("PackBits encoding constant differs") from exc
            if not isinstance(value, int):
                raise MeasurementError("PackBits encoding constant differs")
            encoding_value = value
    names = {
        node.name for node in selected if isinstance(node, (ast.ClassDef, ast.FunctionDef))
    }
    if names != {"TelemetryError", "packbits_encode", "packbits_decode"}:
        raise MeasurementError("PackBits authority definitions differ")
    if encoding_value is None:
        raise MeasurementError("PackBits encoding constant is absent")

    source_sha = hashlib.sha256(source_data).hexdigest()
    name = f"_p318_packbits_authority_{source_sha[:16]}"
    module = types.ModuleType(name)
    module.__file__ = str(repo_root() / DEFAULT_TELEMETRY_SOURCE)
    sys.modules[name] = module
    try:
        code = compile(
            ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])),
            module.__file__,
            "exec",
        )
        exec(code, module.__dict__)  # noqa: S102
    except Exception:
        sys.modules.pop(name, None)
        raise
    module.POLL_ENCODING_PACKBITS = encoding_value
    for symbol in ("packbits_encode", "packbits_decode", "POLL_ENCODING_PACKBITS"):
        if not hasattr(module, symbol):
            sys.modules.pop(name, None)
            raise MeasurementError("PackBits authority symbol differs")
    return module


def measure(
    live_state_data: bytes,
    telemetry_source_data: bytes,
    extractor_data: bytes,
    *,
    proposed_capacity: int = PROPOSED_V4_LOSSLESS_CAPACITY,
) -> dict[str, Any]:
    try:
        live_state = json.loads(live_state_data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MeasurementError("P3.17 live state is not canonical JSON") from exc
    try:
        records = live_state["final_evidence"]["observer"]["classification"]["records"]
    except (KeyError, TypeError) as exc:
        raise MeasurementError("P3.17 retained record path differs") from exc
    if not isinstance(records, list):
        raise MeasurementError("P3.17 retained records are not a list")
    p317_rows = [
        row
        for row in records
        if isinstance(row, dict)
        and isinstance(row.get("max77705"), dict)
        and row["max77705"].get("schema") == P317_SCHEMA
    ]
    if len(p317_rows) != EXPECTED_P317_RECORDS:
        raise MeasurementError("P3.17 retained record count differs")
    if not isinstance(proposed_capacity, int) or proposed_capacity < 0:
        raise MeasurementError("proposed P3.18 capacity differs")

    telemetry = _load_packbits_authority(telemetry_source_data)
    measured: list[dict[str, Any]] = []
    try:
        for row in p317_rows:
            max77705 = row["max77705"]
            vectors = _poll_vectors(row)
            raw = b"".join(vectors)
            try:
                packed = telemetry.packbits_encode(raw)
                roundtrip = telemetry.packbits_decode(
                    packed, expected_size=len(raw)
                )
            except Exception as exc:
                raise MeasurementError("actual PackBits implementation failed") from exc
            if roundtrip != raw:
                raise MeasurementError(
                    "actual PackBits implementation does not round-trip"
                )
            if (
                max77705.get("poll_lossless") is not True
                or max77705.get("poll_raw_size") != len(raw)
                or max77705.get("poll_encoded_size") != len(packed)
                or max77705.get("poll_encoding")
                != telemetry.POLL_ENCODING_PACKBITS
                or max77705["result"].get("poll_count")
                != [len(vector) for vector in vectors]
                or max77705["result"].get("poll_sha256")
                != hashlib.sha256(raw).hexdigest()
            ):
                raise MeasurementError("recorded P3.17 poll authority differs")
            measured.append(
                {
                    "poll_counts": [len(vector) for vector in vectors],
                    "raw_size": len(raw),
                    "raw_sha256": hashlib.sha256(raw).hexdigest(),
                    "packbits_size": len(packed),
                    "packbits_sha256": hashlib.sha256(packed).hexdigest(),
                    "roundtrip": True,
                    "fits_proposed_v4_lossless_capacity": len(packed)
                    <= proposed_capacity,
                    "proposed_v4_capacity_margin": proposed_capacity - len(packed),
                }
            )
    finally:
        sys.modules.pop(telemetry.__name__, None)
    if not all(row["fits_proposed_v4_lossless_capacity"] for row in measured):
        raise MeasurementError("observed P3.17 poll payload exceeds P3.18 capacity")
    if len({json.dumps(row, sort_keys=True) for row in measured}) != 1:
        raise MeasurementError("P3.17 poll measurements are not byte-identical")
    maximum = max(row["packbits_size"] for row in measured)
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "inputs": {
            "p317_live_state": receipt(live_state_data),
            "actual_packbits_source": receipt(telemetry_source_data),
            "measurement_extractor": receipt(extractor_data),
        },
        "measurement": {
            "p317_record_count": len(measured),
            "records_byte_identical_for_poll_evidence": True,
            "records": measured,
            "maximum_observed_packbits_size": maximum,
            "proposed_v4_lossless_capacity": proposed_capacity,
            "minimum_observed_margin": proposed_capacity - maximum,
            "actual_packbits_function_executed": True,
            "packbits_execution_and_receipt_use_identical_source_bytes": True,
            "future_poll_payloads_not_proven_by_this_incident_measurement": True,
            "required_boundary_preimages": [proposed_capacity, proposed_capacity + 1],
        },
        "scope": {
            "host_only": True,
            "device_actions": 0,
            "historical_evidence_unchanged": True,
            "candidate_ready": False,
            "live_authority": False,
        },
    }


def encode(value: dict[str, Any]) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=repo_root())
    parser.add_argument("--live-state", type=Path, default=DEFAULT_LIVE_STATE)
    parser.add_argument(
        "--telemetry-source", type=Path, default=DEFAULT_TELEMETRY_SOURCE
    )
    parser.add_argument("--capacity", type=int, default=PROPOSED_V4_LOSSLESS_CAPACITY)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.repo.resolve()

    def resolve(path: Path) -> Path:
        return path if path.is_absolute() else root / path

    value = measure(
        stable_read(resolve(args.live_state), "P3.17 live state", 2**24),
        stable_read(resolve(args.telemetry_source), "PackBits source", 2**20),
        stable_read(Path(__file__).resolve(), "poll budget measurement", 2**20),
        proposed_capacity=args.capacity,
    )
    payload = encode(value)
    if args.output is None:
        print(payload.decode(), end="")
    else:
        output = resolve(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
