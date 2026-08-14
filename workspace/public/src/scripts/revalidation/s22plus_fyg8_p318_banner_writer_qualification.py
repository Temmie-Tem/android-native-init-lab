#!/usr/bin/env python3
"""Qualify the actual P3.18 absolute-deadline banner writer on the host."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_p318_banner_writer_qualification_v1"
VERDICT = "PASS_P318_ABSOLUTE_DEADLINE_BANNER_WRITER_H0"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
WRITER = Path(
    "workspace/public/src/native-init/s22plus_fyg8_p318_banner_writer.inc.c"
)
FIXTURE = Path(
    "workspace/public/src/native-init/s22plus_fyg8_p318_banner_writer_fixture.c"
)
RUNTIME_FIXTURE = Path(
    "workspace/public/src/native-init/"
    "s22plus_fyg8_p318_banner_writer_runtime_fixture.c"
)
P260_RUNTIME = Path(
    "workspace/public/src/native-init/s22plus_fyg8_p260_e3_runtime.inc.c"
)
DEFAULT_OUTPUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "banner-writer-qualification-20260814-01.json"
)


class BannerQualificationError(RuntimeError):
    """Raised when the writer or its real-C qualification differs."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def stable_read(path: Path, label: str, maximum: int = 2**20) -> bytes:
    before = path.stat()
    if not path.is_file() or path.is_symlink() or before.st_size > maximum:
        raise BannerQualificationError(f"{label} is not a bounded regular file")
    payload = path.read_bytes()
    after = path.stat()
    if (
        len(payload) != before.st_size
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ino != after.st_ino
    ):
        raise BannerQualificationError(f"{label} changed while read")
    return payload


def receipt(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _text(payload: bytes, label: str) -> str:
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BannerQualificationError(f"{label} is not UTF-8") from exc


def _function(source: str, marker: str) -> str:
    start = source.find(marker)
    if start < 0:
        raise BannerQualificationError(f"missing function marker: {marker}")
    brace = source.find("{", start)
    if brace < 0:
        raise BannerQualificationError(f"missing function body: {marker}")
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise BannerQualificationError(f"unterminated function body: {marker}")


def _ordered(source: str, label: str, tokens: tuple[str, ...]) -> None:
    cursor = -1
    for token in tokens:
        found = source.find(token, cursor + 1)
        if found < 0:
            raise BannerQualificationError(f"{label} lacks {token!r}")
        cursor = found


def audit_source(writer_data: bytes, p260_data: bytes) -> dict[str, Any]:
    writer = _text(writer_data, "P3.18 banner writer")
    p260 = _text(p260_data, "P2.60 runtime")
    attempt = _function(
        writer, "static struct s22plus_p318_banner_result "
        "s22plus_p318_banner_attempt_with_ops("
    )
    _ordered(
        attempt,
        "absolute-deadline writer",
        (
            "ops->clock_gettime(ops->context, &deadline)",
            "deadline.tv_sec += S22PLUS_P318_BANNER_DEADLINE_SEC;",
            "while (written < size)",
            "ops->clock_gettime(ops->context, &now)",
            "if (!s22plus_p318_timespec_before(&now, &deadline))",
            "rc = ops->write(ops->context, fd, banner + written, size - written);",
            "if (rc == -S22PLUS_P318_ERRNO_EINTR)",
            "retry_reason = S22PLUS_P318_BANNER_RETRY_EINTR;",
            "if (rc == -S22PLUS_P318_ERRNO_EAGAIN)",
            "retry_reason = S22PLUS_P318_BANNER_RETRY_EAGAIN;",
            "ops->clock_gettime(ops->context, &now)",
            "if (!s22plus_p318_timespec_before(&now, &deadline))",
            "sleep_ns = s22plus_p318_sleep_cap_ns(&now, &deadline);",
            "sleep_rc = ops->sleep_ns(ops->context, sleep_ns);",
            "if (rc < 0)",
            "if (rc == 0)",
            "if ((size_t)rc > size - written)",
            "written += (size_t)rc;",
        ),
    )
    if attempt.count("deadline.tv_sec +=") != 1:
        raise BannerQualificationError("deadline is not initialized exactly once")
    for token in (
        "S22PLUS_P318_BANNER_ERROR_EAGAIN_DEADLINE = 1",
        "S22PLUS_P318_BANNER_ERROR_EINTR_DEADLINE = 2",
        "S22PLUS_P318_BANNER_ERROR_EPIPE = 3",
        "S22PLUS_P318_BANNER_ERROR_ENODEV = 4",
        "S22PLUS_P318_BANNER_ERROR_ETIMEDOUT = 5",
        "S22PLUS_P318_BANNER_ERROR_ZERO_WRITE = 6",
        "S22PLUS_P318_BANNER_ERROR_INVALID_WRITE = 7",
        "S22PLUS_P318_BANNER_ERROR_CLOCK = 8",
        "_Static_assert(sizeof(struct s22plus_p318_banner_result) == 3U",
        "_Static_assert(sizeof(p260_banner) - 1U == S22PLUS_P318_BANNER_SIZE",
    ):
        if token not in writer:
            raise BannerQualificationError(f"writer lacks {token!r}")
    for token in (
        "#define S22PLUS_P318_BANNER_SIZE 49U",
        "#define S22PLUS_P318_BANNER_DEADLINE_SEC 5LL",
        "#define S22PLUS_P318_BANNER_POLL_NS 100000000LL",
    ):
        if writer.count(token) != 1:
            raise BannerQualificationError(f"writer constant differs: {token}")
    if (
        "static char p260_banner[50];" not in p260
        or "tty_fd, p260_banner, sizeof(p260_banner) - 1U, 1" not in p260
    ):
        raise BannerQualificationError("P2.60 49-byte banner source differs")
    return {
        "verified": True,
        "deadline_initialized_once_before_loop": True,
        "deadline_checked_before_every_write": True,
        "eintr_and_eagain_share_absolute_deadline": True,
        "eagain_sleep_capped_to_remaining_deadline": True,
        "short_write_continuation_rechecks_deadline": True,
        "zero_and_invalid_positive_writes_classified": True,
        "eagain_epipe_enodev_distinct": True,
        "result_size": 3,
        "banner_size": 49,
        "deadline_seconds": 5,
    }


def _compile_run(root: Path, source: Path, expected: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p318-banner-qualification-") as name:
        executable = Path(name) / "fixture"
        compile_result = subprocess.run(
            [
                "/usr/bin/cc",
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-O2",
                f"-I{root / 'workspace/public/src/native-init'}",
                str(source),
                "-o",
                str(executable),
            ],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if compile_result.returncode != 0:
            raise BannerQualificationError(
                "fixture compile failed: "
                + compile_result.stderr[-4000:].decode(errors="replace")
            )
        run = subprocess.run(
            [str(executable)],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if run.returncode != 0:
            raise BannerQualificationError(
                "fixture execution failed: " + run.stderr.decode(errors="replace")
            )
        try:
            value = json.loads(run.stdout.decode("ascii"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise BannerQualificationError("fixture did not emit ASCII JSON") from exc
        if value != expected:
            raise BannerQualificationError(f"fixture result differs: {value}")
        return {
            "verified": True,
            "result": value,
            "executable": receipt(executable.read_bytes()),
        }


def build_contract(
    *, writer_data: bytes, fixture_data: bytes, runtime_fixture_data: bytes,
    p260_data: bytes, extractor_data: bytes, root: Path
) -> dict[str, Any]:
    fixture = _compile_run(
        root,
        root / FIXTURE,
        {
            "schema": "s22plus_fyg8_p318_banner_writer_fixture_v1",
            "cases": 15,
            "verdict": "PASS",
        },
    )
    runtime_fixture = _compile_run(
        root,
        root / RUNTIME_FIXTURE,
        {
            "schema": "s22plus_fyg8_p318_banner_runtime_fixture_v1",
            "bytes": 49,
            "verdict": "PASS",
        },
    )
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "inputs": {
            "writer": receipt(writer_data),
            "fixture": receipt(fixture_data),
            "runtime_fixture": receipt(runtime_fixture_data),
            "p260_runtime": receipt(p260_data),
            "extractor": receipt(extractor_data),
        },
        "source_audit": audit_source(writer_data, p260_data),
        "actual_c_fixtures": {
            "scripted_terminal_paths": fixture,
            "runtime_wrapper": runtime_fixture,
            "terminal_path_count": 15,
            "outcomes": ["written", "eagain_timeout", "failure", "partial"],
            "distinct_errors": [
                "eagain_deadline",
                "eintr_deadline",
                "epipe",
                "enodev",
                "etimedout",
                "zero_write",
                "invalid_write",
                "clock",
                "other",
            ],
        },
        "scope": {
            "host_only": True,
            "device_actions": 0,
            "runtime_integration": False,
            "envelope_v4_implemented": False,
            "candidate_ready": False,
            "live_authority": False,
        },
    }


def encode_contract(value: dict[str, Any]) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=repo_root())
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    root = args.repo.resolve()
    writer_data = stable_read(root / WRITER, "P3.18 banner writer")
    fixture_data = stable_read(root / FIXTURE, "P3.18 banner fixture")
    runtime_fixture_data = stable_read(
        root / RUNTIME_FIXTURE, "P3.18 runtime wrapper fixture"
    )
    p260_data = stable_read(root / P260_RUNTIME, "P2.60 runtime")
    extractor_data = stable_read(Path(__file__).resolve(), "qualification extractor")
    value = build_contract(
        writer_data=writer_data,
        fixture_data=fixture_data,
        runtime_fixture_data=runtime_fixture_data,
        p260_data=p260_data,
        extractor_data=extractor_data,
        root=root,
    )
    payload = encode_contract(value)
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp-{os.getpid()}")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
