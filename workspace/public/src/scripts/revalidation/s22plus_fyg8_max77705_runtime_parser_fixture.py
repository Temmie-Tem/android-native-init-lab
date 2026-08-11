#!/usr/bin/env python3
"""Compile and execute the exact S22+ Max77705 PID1 result parser."""

from __future__ import annotations

from dataclasses import replace
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any

import s22plus_fyg8_max77705_telemetry as telemetry


SCHEMA = "s22plus_fyg8_max77705_runtime_parser_fixture_v1"
VERDICT = "PASS_MAX77705_ACTUAL_PID1_PARSER_AND_SUMMARY_HOST_ONLY"
PARSER = Path(
    "workspace/public/src/native-init/"
    "s22plus_fyg8_max77705_result_parser.inc.c"
)
HOST_FIXTURE = Path(
    "workspace/public/src/native-init/"
    "s22plus_fyg8_max77705_result_parser_fixture.c"
)
FIXTURE_SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_max77705_runtime_parser_fixture.py"
)
TELEMETRY_SOURCE = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_max77705_telemetry.py"
)
PINNED_CLANG = Path(
    "workspace/private/work/toolchains/aosp-clang-android12-release/"
    "clang-r416183b/bin/clang"
)
DEFAULT_OUTPUT = Path(
    "workspace/private/outputs/s22plus_fyg8_max77705_gate0/"
    "runtime-parser-20260812-01.json"
)
ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


class RuntimeParserFixtureError(ValueError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _result(
    *, polls: tuple[bytes, bytes, bytes, bytes] | None = None
) -> telemetry.DiagnosticResult:
    selected = polls or (
        b"\x00\x00\x80",
        b"\x80",
        b"\x80",
        b"\x80",
    )
    write_present = bool(selected[1])
    return telemetry.DiagnosticResult(
        stage=telemetry.STAGE_COMPLETE,
        rc=0,
        pmic_valid_mask=3,
        pmic_id=0x15,
        pmic_rev=0x02,
        initial_uic_valid=1,
        initial_uic=0x04,
        command_issued_mask=0x0F if write_present else 0x0D,
        response_seen_mask=0x0F if write_present else 0x0D,
        response_opcode=(0x05, 0x06 if write_present else 0, 0x05, 0x05),
        response_value=(0x3F if write_present else 0x09, 0, 0x09, 0x09),
        poll_bytes=selected,
        write_attempted=1 if write_present else 0,
        write_ambiguous=0,
    )


def _parse_fixture_output(output: str) -> dict[str, str]:
    if not output.startswith("OK "):
        raise RuntimeParserFixtureError(f"PID1 parser output differs: {output!r}")
    fields: dict[str, str] = {}
    for item in output.strip().split()[1:]:
        if "=" not in item:
            raise RuntimeParserFixtureError("PID1 parser emitted a malformed field")
        name, value = item.split("=", 1)
        if name in fields:
            raise RuntimeParserFixtureError("PID1 parser emitted a duplicate field")
        fields[name] = value
    return fields


def _run(binary: Path, payload: bytes, *, valid: bool) -> dict[str, str] | None:
    completed = subprocess.run(
        [str(binary)],
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if valid:
        if completed.returncode != 0 or completed.stderr:
            raise RuntimeParserFixtureError(
                "valid PID1 parser vector failed: "
                f"rc={completed.returncode}, stderr={completed.stderr!r}"
            )
        return _parse_fixture_output(completed.stdout.decode("ascii"))
    if completed.returncode != 2 or not completed.stdout.startswith(b"ERR rc=-"):
        raise RuntimeParserFixtureError(
            "invalid PID1 parser vector did not fail closed: "
            f"rc={completed.returncode}, stdout={completed.stdout!r}"
        )
    return None


def _assert_summary(fields: dict[str, str], result: telemetry.DiagnosticResult) -> None:
    summary = telemetry.summarize_poll_vectors(result.poll_bytes)
    expected = {
        "stage": str(result.stage),
        "rc": str(result.rc),
        "raw": str(sum(len(value) for value in result.poll_bytes)),
        "sha": summary.sha256.hex(),
        "or": bytes(summary.or_mask).hex(),
        "poll0": bytes(summary.poll0).hex(),
        "nz": bytes(summary.nonzero_count).hex(),
        "issued": f"{result.command_issued_mask:02x}",
        "seen": f"{result.response_seen_mask:02x}",
        "val": bytes(result.response_value).hex(),
    }
    if fields != expected:
        raise RuntimeParserFixtureError(
            f"actual PID1 parser summary differs: {fields!r} != {expected!r}"
        )


def audit(repo_root: Path | None = None) -> dict[str, Any]:
    root = (repo_root or Path(__file__).resolve().parents[5]).resolve()
    parser = root / PARSER
    host_fixture = root / HOST_FIXTURE
    fixture_script = root / FIXTURE_SCRIPT
    telemetry_source = root / TELEMETRY_SOURCE
    clang = root / PINNED_CLANG
    host_cc = shutil.which("cc")
    file_tool = shutil.which("file")
    if not all(
        path.is_file()
        for path in (parser, host_fixture, fixture_script, telemetry_source)
    ):
        raise RuntimeParserFixtureError("PID1 parser source closure is missing")
    if host_cc is None or file_tool is None or not clang.is_file():
        raise RuntimeParserFixtureError("PID1 parser compiler closure is missing")

    with tempfile.TemporaryDirectory(prefix="s22plus-max77705-parser-") as temporary:
        temp = Path(temporary)
        binary = temp / "parser-fixture"
        subprocess.run(
            [
                host_cc,
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-I",
                str(host_fixture.parent),
                str(host_fixture),
                "-o",
                str(binary),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        host_cc_version = subprocess.run(
            [host_cc, "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout.splitlines()[0]
        clang_version = subprocess.run(
            [str(clang), "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout.splitlines()[0]
        abc = subprocess.run(
            [str(binary), "--sha-abc"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        if abc != ABC_SHA256:
            raise RuntimeParserFixtureError("PID1 SHA-256 self-test differs")

        long_poll = bytes((*range(99), 0x80))
        valid_results = (
            _result(),
            _result(polls=(long_poll, long_poll, long_poll, long_poll)),
            replace(
                _result(),
                response_value=(0x3F, 0, 0x09, 0x09),
                poll_bytes=(b"\x80", b"\x80", b"\x80", b"\x88"),
            ),
            replace(
                _result(),
                stage=telemetry.STAGE_PRE,
                rc=telemetry.RC_ETIMEDOUT,
                command_issued_mask=0x01,
                response_seen_mask=0,
                write_attempted=0,
                response_opcode=(0, 0, 0, 0),
                response_value=(0, 0, 0, 0),
                poll_bytes=(b"\x01" * 100, b"", b"", b""),
            ),
        )
        valid_receipts: list[str] = []
        for result in valid_results:
            payload = telemetry.format_module_result(result)
            fields = _run(binary, payload, valid=True)
            if fields is None:
                raise RuntimeParserFixtureError("valid parser result disappeared")
            _assert_summary(fields, result)
            valid_receipts.append(hashlib.sha256(payload).hexdigest())

        canonical = telemetry.format_module_result(_result())
        valid_timeout = telemetry.format_module_result(valid_results[-1])
        timeout_with_apcmd = valid_timeout.replace(
            b"p0=" + b"01" * 100,
            b"p0=" + b"01" * 99 + b"80",
            1,
        )
        mutations = {
            "missing_newline": canonical[:-1],
            "extra_newline": canonical + b"\n",
            "trailing_nul": canonical + b"\0",
            "uppercase_hex": canonical.replace(b"val=3f", b"val=3F", 1),
            "leading_zero_stage": canonical.replace(b"stage=10", b"stage=010", 1),
            "negative_zero_rc": canonical.replace(b"rc=0", b"rc=-0", 1),
            "reordered_masks": canonical.replace(
                b"issued=0f seen=0f", b"seen=0f issued=0f", 1
            ),
            "poll_count_mismatch": canonical.replace(b"p0n=3", b"p0n=4", 1),
            "poll_count_over_bound": canonical.replace(b"p0n=3", b"p0n=101", 1),
            "response_not_issued": canonical.replace(b"issued=0f", b"issued=0e", 1),
            "response_without_apcmd": canonical.replace(b"p0=000080", b"p0=000001", 1),
            "complete_write_flag_drift": canonical.replace(
                b"wr_attempt=1", b"wr_attempt=0", 1
            ),
            "timeout_slot_contains_apcmd": timeout_with_apcmd,
        }
        for payload in mutations.values():
            _run(binary, payload, valid=False)

        cross_source = temp / "cross.c"
        cross_object = temp / "cross.o"
        cross_source.write_text(
            "#include <stddef.h>\n#include <stdint.h>\n"
            f'#include "{parser}"\n'
            "int s22plus_max77705_parser_cross_entry(const char *p, size_t n, "
            "struct s22plus_max77705_runtime_result *r, "
            "struct s22plus_max77705_runtime_poll_summary *s) { "
            "return s22plus_max77705_runtime_parse_result(p, n, r, s); }\n",
            encoding="ascii",
        )
        subprocess.run(
            [
                str(clang),
                "--target=aarch64-linux-gnu",
                "-ffreestanding",
                "-fno-builtin",
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-c",
                str(cross_source),
                "-o",
                str(cross_object),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        cross_file_output = subprocess.run(
            [file_tool, str(cross_object)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        if not re.search(
            r"ELF 64-bit LSB relocatable, ARM aarch64", cross_file_output
        ):
            raise RuntimeParserFixtureError("PID1 parser cross object is not AArch64")
        cross_file = cross_file_output.split(": ", 1)[-1]

    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "host_only": True,
        "device_contact": False,
        "parser_source": {
            "path": str(PARSER),
            "size": parser.stat().st_size,
            "sha256": _sha256(parser),
        },
        "host_fixture_source": {
            "path": str(HOST_FIXTURE),
            "size": host_fixture.stat().st_size,
            "sha256": _sha256(host_fixture),
        },
        "fixture_driver_source": {
            "path": str(FIXTURE_SCRIPT),
            "size": fixture_script.stat().st_size,
            "sha256": _sha256(fixture_script),
        },
        "telemetry_authority_source": {
            "path": str(TELEMETRY_SOURCE),
            "size": telemetry_source.stat().st_size,
            "sha256": _sha256(telemetry_source),
        },
        "host_compiler_version": host_cc_version,
        "pinned_aarch64_clang": {
            "path": str(PINNED_CLANG),
            "size": clang.stat().st_size,
            "sha256": _sha256(clang),
            "version": clang_version,
        },
        "valid_vector_count": len(valid_results),
        "invalid_mutation_count": len(mutations),
        "valid_vector_sha256": valid_receipts,
        "sha256_abc": abc,
        "python_summary_matches_actual_c": True,
        "strict_module_string_grammar": True,
        "aarch64_freestanding_compile": True,
        "aarch64_object_file": cross_file,
        "sysfs_path_or_driver_override_integrated": False,
        "fresh_d0_still_required": True,
        "verified": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    try:
        result = audit(args.repo_root)
    except (RuntimeParserFixtureError, OSError, subprocess.SubprocessError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        output = args.output.resolve()
    else:
        root = (args.repo_root or Path(__file__).resolve().parents[5]).resolve()
        output = root / DEFAULT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(output)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
