#!/usr/bin/env python3
"""Prove P2.92 phase-1 SoT fidelity to retained P2.90 artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
from typing import Any, Callable

import s22plus_fyg8_p290_candidate_intent as p290_intent
import s22plus_fyg8_p292_checkpoint_sot as sot
import s22plus_fyg8_p292_sot_generator as generator


SCHEMA = "s22plus_fyg8_p292_sot_zero_delta_result_v1"
BASELINE_SCHEMA = "s22plus_fyg8_p292_sot_zero_delta_baseline_v1"
VERDICT = "PASS_CHECKPOINT_SOT_ZERO_DELTA"
BASELINE_MANIFEST = Path(__file__).with_name(
    "s22plus_fyg8_p290_sot_zero_delta_baseline.json"
)
SHA256_RE = re.compile(r"[0-9a-f]{64}")
HEX16_RE = re.compile(r"[0-9a-f]{32}")
MODE_RE = re.compile(r"0[0-7]{3}")


class ZeroDeltaError(ValueError):
    pass


Generator = Callable[..., dict[str, Any]]


def repo_root() -> Path:
    root = Path(__file__).resolve().parents[5]
    if not (root / "AGENTS.md").is_file() or not (root / "GOAL.md").is_file():
        raise ZeroDeltaError("repository root could not be resolved")
    return root


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _relative_path(value: Any, label: str) -> PurePosixPath:
    if not isinstance(value, str):
        raise ZeroDeltaError(f"{label} path is not text")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ZeroDeltaError(f"{label} path is unsafe")
    return path


def _receipt_from_row(row: Any, label: str) -> dict[str, Any]:
    required = {"key", "path", "type", "mode", "size", "sha256"}
    if not isinstance(row, dict) or set(row) != required:
        raise ZeroDeltaError(f"{label} receipt shape differs")
    if not isinstance(row["key"], str) or not row["key"]:
        raise ZeroDeltaError(f"{label} key is invalid")
    path = _relative_path(row["path"], label)
    if row["type"] != "regular":
        raise ZeroDeltaError(f"{label} type is not regular")
    if not isinstance(row["mode"], str) or MODE_RE.fullmatch(row["mode"]) is None:
        raise ZeroDeltaError(f"{label} mode is invalid")
    if (
        isinstance(row["size"], bool)
        or not isinstance(row["size"], int)
        or row["size"] <= 0
    ):
        raise ZeroDeltaError(f"{label} size is invalid")
    if (
        not isinstance(row["sha256"], str)
        or SHA256_RE.fullmatch(row["sha256"]) is None
    ):
        raise ZeroDeltaError(f"{label} SHA256 is invalid")
    return {**row, "path": path.as_posix()}


def load_manifest(path: Path = BASELINE_MANIFEST) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ZeroDeltaError("zero-delta baseline manifest is missing or indirect")
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ZeroDeltaError("zero-delta baseline manifest is invalid JSON") from exc
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "authority",
        "artifact_count",
        "artifacts",
    }:
        raise ZeroDeltaError("zero-delta baseline manifest shape differs")
    if value["schema"] != BASELINE_SCHEMA:
        raise ZeroDeltaError("zero-delta baseline schema differs")
    authority = value["authority"]
    authority_keys = {
        "path",
        "type",
        "mode",
        "size",
        "sha256",
        "run_id",
        "profile",
        "source_contract_id",
    }
    if not isinstance(authority, dict) or set(authority) != authority_keys:
        raise ZeroDeltaError("zero-delta authority shape differs")
    authority_receipt = _receipt_from_row(
        {"key": "authority", **{
            key: authority[key]
            for key in ("path", "type", "mode", "size", "sha256")
        }},
        "authority",
    )
    if HEX16_RE.fullmatch(str(authority["run_id"])) is None:
        raise ZeroDeltaError("zero-delta authority run ID differs")
    if authority["profile"] != sot.PROFILE:
        raise ZeroDeltaError("zero-delta authority profile differs")
    if authority["source_contract_id"] != p290_intent.p290.CONTRACT_ID:
        raise ZeroDeltaError("zero-delta authority contract differs")
    rows = [
        _receipt_from_row(row, f"artifact[{index}]")
        for index, row in enumerate(value["artifacts"])
    ] if isinstance(value["artifacts"], list) else []
    if (
        value["artifact_count"] != len(rows)
        or len(rows) != 13
        or len({row["key"] for row in rows}) != len(rows)
        or len({row["path"] for row in rows}) != len(rows)
        or {row["key"] for row in rows} != set(generator.artifact_paths())
    ):
        raise ZeroDeltaError("zero-delta artifact inventory differs")
    return {
        **value,
        "authority": {**authority, "path": authority_receipt["path"]},
        "artifacts": rows,
        "manifest_sha256": _sha256(raw),
    }


def _read_regular(
    path: Path,
    receipt: dict[str, Any],
    label: str,
) -> bytes:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise ZeroDeltaError(f"{label} is missing") from exc
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise ZeroDeltaError(f"{label} is indirect or not regular")
    if f"{stat.S_IMODE(metadata.st_mode):04o}" != receipt["mode"]:
        raise ZeroDeltaError(f"{label} mode differs")
    data = path.read_bytes()
    if len(data) != receipt["size"] or _sha256(data) != receipt["sha256"]:
        raise ZeroDeltaError(f"{label} bytes differ")
    return data


def _intent_receipts(intent: dict[str, Any]) -> dict[str, dict[str, Any]]:
    try:
        rows = {
            "candidate_patch": {
                "key": "candidate_patch",
                "path": "candidate.patch",
                "size": intent["patch"]["size"],
                "sha256": intent["patch"]["sha256"],
            }
        }
        rows.update(
            {
                key: {
                    "key": key,
                    "path": value["path"],
                    "size": value["size"],
                    "sha256": value["sha256"],
                }
                for key, value in intent["materialized_sources"].items()
            }
        )
    except (KeyError, TypeError, AttributeError) as exc:
        raise ZeroDeltaError("authority intent artifact receipts differ") from exc
    return rows


def verify_authority(
    root: Path, manifest: dict[str, Any]
) -> dict[str, Any]:
    authority = manifest["authority"]
    authority_path = root / Path(authority["path"])
    data = _read_regular(authority_path, authority, "authority intent")
    try:
        intent = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ZeroDeltaError("authority intent is invalid JSON") from exc
    if (
        intent.get("schema") != p290_intent.SCHEMA
        or intent.get("run_id") != authority["run_id"]
        or intent.get("profile") != authority["profile"]
        or intent.get("source_contract_id") != authority["source_contract_id"]
        or not isinstance(intent.get("unsat_tag_hex"), str)
        or HEX16_RE.fullmatch(intent["unsat_tag_hex"]) is None
    ):
        raise ZeroDeltaError("authority intent binding differs")
    intent_rows = _intent_receipts(intent)
    manifest_rows = {
        row["key"]: {
            key: row[key] for key in ("key", "path", "size", "sha256")
        }
        for row in manifest["artifacts"]
    }
    if intent_rows != manifest_rows:
        raise ZeroDeltaError("baseline manifest differs from authority intent")
    baseline_root = authority_path.parent
    for row in manifest["artifacts"]:
        _read_regular(
            baseline_root / Path(row["path"]),
            row,
            f"baseline artifact {row['key']}",
        )
    return {
        "intent_path": authority["path"],
        "intent_sha256": authority["sha256"],
        "run_id": authority["run_id"],
        "profile": authority["profile"],
        "source_contract_id": authority["source_contract_id"],
        "unsat_tag_hex": intent["unsat_tag_hex"],
        "baseline_root": baseline_root,
        "verified": True,
    }


def verify_generated_tree(
    tree: Path,
    manifest: dict[str, Any],
    label: str,
) -> dict[str, dict[str, Any]]:
    allowed_files = {row["path"] for row in manifest["artifacts"]}
    allowed_directories = {
        parent.as_posix()
        for row in manifest["artifacts"]
        for parent in PurePosixPath(row["path"]).parents
        if parent.as_posix() != "."
    }
    actual_files: set[str] = set()
    actual_directories: set[str] = set()
    for path in tree.rglob("*"):
        relative = path.relative_to(tree).as_posix()
        if path.is_symlink():
            raise ZeroDeltaError(f"{label} contains a symlink")
        if path.is_dir():
            actual_directories.add(relative)
        elif path.is_file():
            actual_files.add(relative)
        else:
            raise ZeroDeltaError(f"{label} contains a special file")
    if actual_files != allowed_files or actual_directories != allowed_directories:
        raise ZeroDeltaError(f"{label} inventory differs")
    rows = {}
    for row in manifest["artifacts"]:
        data = _read_regular(
            tree / Path(row["path"]), row, f"{label} artifact {row['key']}"
        )
        rows[row["key"]] = {
            "path": row["path"],
            "mode": row["mode"],
            "size": len(data),
            "sha256": _sha256(data),
        }
    return rows


def compare_generated_trees(
    run_a: Path,
    run_b: Path,
    manifest: dict[str, Any],
) -> None:
    for row in manifest["artifacts"]:
        relative = Path(row["path"])
        if (run_a / relative).read_bytes() != (run_b / relative).read_bytes():
            raise ZeroDeltaError(f"run A/B bytes differ: {row['key']}")


def run_zero_delta(
    root: Path,
    *,
    manifest_path: Path = BASELINE_MANIFEST,
    materialize: Generator = generator.materialize,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    authority = verify_authority(root, manifest)
    run_b_started = False
    with tempfile.TemporaryDirectory(
        prefix="s22-p292-sot-zero-delta-"
    ) as temporary:
        base = Path(temporary)
        run_a = base / "run-a"
        materialize(
            root,
            run_a,
            run_id=bytes.fromhex(authority["run_id"]),
            unsat_tag=bytes.fromhex(authority["unsat_tag_hex"]),
            profile=authority["profile"],
        )
        run_a_rows = verify_generated_tree(run_a, manifest, "run A")

        run_b = base / "run-b"
        run_b_started = True
        materialize(
            root,
            run_b,
            run_id=bytes.fromhex(authority["run_id"]),
            unsat_tag=bytes.fromhex(authority["unsat_tag_hex"]),
            profile=authority["profile"],
        )
        run_b_rows = verify_generated_tree(run_b, manifest, "run B")
        compare_generated_trees(run_a, run_b, manifest)

    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "baseline": {
            "manifest_path": str(manifest_path.relative_to(root)),
            "manifest_sha256": manifest["manifest_sha256"],
            "authority_intent_path": authority["intent_path"],
            "authority_intent_sha256": authority["intent_sha256"],
            "artifact_count": manifest["artifact_count"],
        },
        "sot": sot.validate(),
        "run_a": {
            "baseline_fidelity": True,
            "artifacts": run_a_rows,
        },
        "run_b": {
            "started_after_run_a_pass": run_b_started,
            "baseline_fidelity": True,
            "run_a_determinism": True,
            "artifacts": run_b_rows,
        },
        "scope": {
            "declared_artifact_count": manifest["artifact_count"],
            "excluded_artifact_count": 0,
            "comparison_weakened": False,
            "repair_present": False,
        },
        "safety": {
            "host_only": True,
            "intent_created": False,
            "kernel_built": False,
            "image_built": False,
            "device_contact": False,
            "live_authorized": False,
        },
    }


def _durable_write(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise ZeroDeltaError("zero-delta output already exists")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o400,
    )
    try:
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                raise ZeroDeltaError("short zero-delta result write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    try:
        result = run_zero_delta(root)
        if args.out is not None:
            output = args.out if args.out.is_absolute() else root / args.out
            _durable_write(
                output,
                json.dumps(
                    result, indent=2, sort_keys=True, allow_nan=False
                ).encode("ascii")
                + b"\n",
            )
    except (ZeroDeltaError, generator.GeneratorError, sot.SotError, OSError) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)},
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "verdict": result["verdict"],
                "baseline_artifact_count": result["baseline"]["artifact_count"],
                "run_a_fidelity": result["run_a"]["baseline_fidelity"],
                "run_b_fidelity": result["run_b"]["baseline_fidelity"],
                "run_a_b_determinism": result["run_b"]["run_a_determinism"],
                "comparison_weakened": result["scope"]["comparison_weakened"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
