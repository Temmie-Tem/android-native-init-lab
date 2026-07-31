#!/usr/bin/env python3
"""Catalog private A90 evidence and extract allowlisted redacted fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

import a90_observation_pipeline as pipeline


REPO_ROOT = Path(__file__).resolve().parents[5]
PRIVATE_RUNS = REPO_ROOT / "workspace" / "private" / "runs"
PUBLIC_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "a90_observation"
MAX_TEXT_BYTES = 20 * 1024 * 1024
TEXT_SUFFIXES = frozenset(
    {".json", ".jsonl", ".log", ".out", ".stderr", ".stdout", ".txt"}
)
CATALOG_SCHEMA = "a90-private-observation-corpus-v3"
FIXTURE_SCHEMA = "a90-observation-redacted-fixture-v1"
ONE_WAY_COMMANDS = frozenset({"switch-root-to-distro"})


class CorpusError(RuntimeError):
    """Raised when corpus input/output violates its private/public boundary."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _regular(path: Path, *, label: str) -> Path:
    lexical = path.lstat()
    if stat.S_ISLNK(lexical.st_mode):
        raise CorpusError(f"{label} must be a regular non-symlink file")
    resolved = path.resolve(strict=True)
    info = resolved.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise CorpusError(f"{label} must be a regular non-symlink file")
    return resolved


def _under(path: Path, root: Path, *, label: str) -> Path:
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(root.resolve(strict=True))
    except ValueError as exc:
        raise CorpusError(f"{label} escapes its allowed root") from exc
    return resolved


def require_private_source(path: Path) -> Path:
    resolved = _regular(path, label="source")
    _under(resolved, PRIVATE_RUNS, label="source")
    if resolved.suffix != ".json" or resolved.stat().st_size > MAX_TEXT_BYTES:
        raise CorpusError("source must be bounded private JSON")
    return resolved


def _line_ending_counts(data: bytes) -> dict[str, int]:
    crlf = data.count(b"\r\n")
    return {
        "crlf": crlf,
        "bare_lf": data.count(b"\n") - crlf,
        "bare_cr": data.count(b"\r") - crlf,
    }


def _replay_a90p1(data: bytes) -> dict[str, Any]:
    try:
        transcript = pipeline.parse_a90p1_transcript(
            data,
            require_frames=False,
            one_way_commands=ONE_WAY_COMMANDS,
        )
    except pipeline.ObservationContractError as exc:
        return {
            "status": "REJECT",
            "frames": 0,
            "transitions": 0,
            "error": str(exc),
        }
    return {
        "status": "PASS",
        "frames": len(transcript.frames),
        "transitions": len(transcript.transitions),
        "error": None,
    }


def build_private_catalog(root: Path = PRIVATE_RUNS) -> dict[str, Any]:
    selected_root = _under(root, PRIVATE_RUNS, label="catalog root")
    entries: list[dict[str, Any]] = []
    for path in sorted(selected_root.rglob("*")):
        try:
            info = path.lstat()
        except OSError:
            continue
        if (
            path.is_symlink()
            or not stat.S_ISREG(info.st_mode)
            or path.suffix not in TEXT_SUFFIXES
            or info.st_size > MAX_TEXT_BYTES
        ):
            continue
        data = path.read_bytes()
        raw_log = path.name.endswith(".raw.log")
        a90p1 = b"A90P1 BEGIN" in data or b"A90P1 END" in data
        replay = _replay_a90p1(data) if raw_log and a90p1 else None
        entries.append(
            {
                "path": str(path.relative_to(PRIVATE_RUNS)),
                "size": len(data),
                "sha256": sha256_bytes(data),
                "raw_log": raw_log,
                "a90p1": a90p1,
                "a90p1_replay": replay,
                "end_marker_missing": b"A90P1 END marker not found" in data,
                "line_endings": _line_ending_counts(data),
            }
        )
    replayed = [item["a90p1_replay"] for item in entries if item["a90p1_replay"]]
    return {
        "schema": CATALOG_SCHEMA,
        "root": "workspace/private/runs",
        "max_text_bytes": MAX_TEXT_BYTES,
        "entries": entries,
        "summary": {
            "files": len(entries),
            "raw_logs": sum(item["raw_log"] for item in entries),
            "a90p1_files": sum(item["a90p1"] for item in entries),
            "a90p1_raw_replay_files": len(replayed),
            "a90p1_raw_replay_pass": sum(
                item["status"] == "PASS" for item in replayed
            ),
            "a90p1_raw_replay_reject": sum(
                item["status"] == "REJECT" for item in replayed
            ),
            "a90p1_complete_frames": sum(item["frames"] for item in replayed),
            "a90p1_one_way_transitions": sum(
                item["transitions"] for item in replayed
            ),
            "end_marker_missing_files": sum(
                item["end_marker_missing"] for item in entries
            ),
            "mixed_line_ending_files": sum(
                item["line_endings"]["crlf"] > 0
                and (
                    item["line_endings"]["bare_lf"] > 0
                    or item["line_endings"]["bare_cr"] > 0
                )
                for item in entries
            ),
        },
    }


def _load_object(path: Path) -> tuple[dict[str, Any], bytes]:
    data = path.read_bytes()
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CorpusError("source is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise CorpusError("source JSON must be an object")
    return value, data


def _selected_release_log(text: Any) -> str:
    if not isinstance(text, str):
        raise CorpusError("handoff text is absent")
    decoded = pipeline.decode_lines(
        text,
        label="private handoff text",
        allow_unterminated=True,
    )
    selected = [
        line
        for line in decoded.lines
        if (
            pipeline.NATIVE_RELEASE_SUCCESS_RE.fullmatch(line.text) is not None
            or line.text in pipeline.NATIVE_RELEASE_EXACT_LINES
        )
    ]
    if len(selected) != 5 or any(
        line.ending is not pipeline.LineEnding.CRLF for line in selected
    ):
        raise CorpusError("source lacks the exact V3406 CRLF release shape")
    return "".join(line.text + "\r\n" for line in selected)


def extract_v3406_redacted_fixture(source: Path) -> dict[str, Any]:
    resolved = require_private_source(source)
    value, raw = _load_object(resolved)
    handoff = value.get("handoff")
    ssh = value.get("ssh")
    if not isinstance(handoff, dict) or not isinstance(ssh, dict):
        raise CorpusError("source lacks handoff/SSH objects")
    release_log = _selected_release_log(handoff.get("text"))
    release_marker = ssh.get("native_release_marker_text")
    failure_marker = ssh.get("display_marker_text")
    if not isinstance(release_marker, str) or not isinstance(failure_marker, str):
        raise CorpusError("source lacks exact display markers")
    pipeline.validate_native_release_evidence(release_log, release_marker)
    pipeline.validate_bounded_failure_marker(
        failure_marker,
        max_attempts=3,
        ready_absent=True,
    )
    ssh_facts = {
        "pid1_comm_init": ssh.get("pid1_comm_init") is True,
        "proc1_exe_init": ssh.get("proc1_exe_init") is True,
        "dropbear_started": ssh.get("dropbear_started") is True,
        "display_status": ssh.get("display_status"),
    }
    if ssh_facts != {
        "pid1_comm_init": True,
        "proc1_exe_init": True,
        "dropbear_started": True,
        "display_status": "bounded-failure",
    }:
        raise CorpusError("source SSH facts are not the V3406 boundary")
    facts = pipeline.classify_phase2_display_facts(
        handoff_log=release_log,
        native_release_marker=release_marker,
        **ssh_facts,
    )
    return {
        "schema": FIXTURE_SCHEMA,
        "redaction": "allowlisted-fields-only-v1",
        "source": {"size": len(raw), "sha256": sha256_bytes(raw)},
        "native_release_log": release_log,
        "native_release_marker": release_marker,
        "ssh_facts": ssh_facts,
        "candidate_return_present": isinstance(value.get("candidate_return"), dict),
        "expected_facts": {
            name: fact.state.value for name, fact in sorted(facts.items())
        },
        "expected_atomic_result": "NO_PROOF",
    }


def _output_path(path: Path, *, private: bool) -> Path:
    root = PRIVATE_RUNS if private else PUBLIC_FIXTURES
    parent = root.resolve(strict=True)
    resolved_parent = path.parent.resolve(strict=True)
    try:
        resolved_parent.relative_to(parent)
    except ValueError as exc:
        raise CorpusError("output escapes its allowed root") from exc
    if path.exists() or path.is_symlink():
        raise CorpusError("output must be absent")
    return path


def write_json_exclusive(path: Path, value: dict[str, Any], *, private: bool) -> None:
    selected = _output_path(path, private=private)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(selected, flags, 0o600 if private else 0o644)
    try:
        payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
        remaining = memoryview(payload.encode("utf-8"))
        while remaining:
            written = os.write(fd, remaining)
            if written <= 0:
                raise CorpusError("exclusive JSON write did not make progress")
            remaining = remaining[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--catalog-output", type=Path)
    mode.add_argument("--extract-v3406", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.catalog_output is not None:
        if args.output is not None:
            raise CorpusError("catalog mode does not accept --output")
        value = build_private_catalog()
        write_json_exclusive(args.catalog_output, value, private=True)
    else:
        if args.output is None:
            raise CorpusError("extract mode requires --output")
        value = extract_v3406_redacted_fixture(args.extract_v3406)
        write_json_exclusive(args.output, value, private=False)
    print(json.dumps({"schema": value["schema"], "status": "PASS"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
