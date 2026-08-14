#!/usr/bin/env python3
"""Compile and execute the exact P3.18 timed Max77705 result parser."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any


SCHEMA = "s22plus_fyg8_p318_max77705_runtime_parser_fixture_v1"
VERDICT = "PASS_P318_TIMED_MAX77705_ACTUAL_PID1_PARSER_HOST_ONLY"
PARSER = Path(
    "workspace/public/src/native-init/"
    "s22plus_fyg8_p318_max77705_result_parser.inc.c"
)
HOST_FIXTURE = Path(
    "workspace/public/src/native-init/"
    "s22plus_fyg8_p318_max77705_result_parser_fixture.c"
)
FIXTURE_SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_max77705_runtime_parser_fixture.py"
)
MODULE_SOURCE = Path(
    "workspace/public/src/kernel-modules/s22plus_max77705_mux_diag_p318/"
    "s22plus_max77705_mux_diag_p318.c"
)
PINNED_CLANG = Path(
    "workspace/private/work/toolchains/aosp-clang-android12-release/"
    "clang-r416183b/bin/clang"
)
DEFAULT_OUTPUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "max77705-runtime-parser-20260814-01.json"
)
ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
RETENTION_NS = 30_000_000_000


class TimedParserFixtureError(ValueError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _result(
    *,
    write: bool = True,
    timing_mask: int | None = None,
    pre_ns: int = 1_000_000_000,
    write_ns: int = 1_000_100_000,
    post1_ns: int = 1_001_000_000,
    post2_ns: int = 31_001_000_000,
    polls: tuple[bytes, bytes, bytes, bytes] | None = None,
) -> bytes:
    selected = polls or (
        b"\x00\x00\x80",
        b"\x80" if write else b"",
        b"\x80",
        b"\x80",
    )
    mask = timing_mask if timing_mask is not None else (0x0F if write else 0x0D)
    issued = 0x0F if write else 0x0D
    rsp = (0x05, 0x06 if write else 0, 0x05, 0x05)
    values = (0x3F if write else 0x09, 0, 0x09, 0x09)
    if not write:
        write_ns = 0
    fields = [
        "v=2 stage=10 rc=0 pmic_v=03 pmic_id=15 pmic_rev=02",
        f"uic0_v=1 uic0=04 issued={issued:02x} seen={issued:02x}",
        f"wr_attempt={1 if write else 0} wr_amb=0 tm={mask:02x}",
        f"tpre={pre_ns} twrite={write_ns} tpost1={post1_ns} tpost2={post2_ns}",
        "rsp=" + bytes(rsp).hex(),
        "val=" + bytes(values).hex(),
    ]
    for index, poll in enumerate(selected):
        fields.append(f"p{index}n={len(poll)} p{index}={poll.hex()}")
    return (" ".join(fields) + "\n").encode("ascii")


def _timeout_pre() -> bytes:
    poll = b"\x01" * 100
    return (
        "v=2 stage=5 rc=-110 pmic_v=03 pmic_id=15 pmic_rev=02 "
        "uic0_v=1 uic0=04 issued=01 seen=00 wr_attempt=0 wr_amb=0 "
        "tm=00 tpre=0 twrite=0 tpost1=0 tpost2=0 "
        "rsp=00000000 val=00000000 "
        f"p0n=100 p0={poll.hex()} p1n=0 p1= p2n=0 p2= p3n=0 p3=\n"
    ).encode("ascii")


def _expected(payload: bytes) -> dict[str, str]:
    text = payload.decode("ascii")
    values: dict[str, str] = {}
    polls: list[bytes] = []
    for token in text.strip().split():
        if "=" in token:
            name, value = token.split("=", 1)
            values[name] = value
    for index in range(4):
        polls.append(bytes.fromhex(values[f"p{index}"]))
    raw = b"".join(polls)
    or_masks = bytes(
        0 if not poll else __import__("functools").reduce(lambda a, b: a | b, poll)
        for poll in polls
    )
    poll0 = bytes(poll[0] if poll else 0 for poll in polls)
    nonzero = bytes(sum(value != 0 for value in poll) for poll in polls)
    return {
        "stage": values["stage"],
        "rc": values["rc"],
        "raw": str(len(raw)),
        "sha": hashlib.sha256(raw).hexdigest(),
        "or": or_masks.hex(),
        "poll0": poll0.hex(),
        "nz": nonzero.hex(),
        "issued": values["issued"],
        "seen": values["seen"],
        "val": values["val"],
        "tm": values["tm"],
        "tpre": values["tpre"],
        "twrite": values["twrite"],
        "tpost1": values["tpost1"],
        "tpost2": values["tpost2"],
    }


def _parse_output(output: bytes) -> dict[str, str]:
    if not output.startswith(b"OK "):
        raise TimedParserFixtureError(f"timed parser output differs: {output!r}")
    fields: dict[str, str] = {}
    for item in output.decode("ascii").strip().split()[1:]:
        name, value = item.split("=", 1)
        if name in fields:
            raise TimedParserFixtureError("timed parser emitted a duplicate field")
        fields[name] = value
    return fields


def _run(binary: Path, payload: bytes, *, valid: bool) -> dict[str, str] | None:
    completed = subprocess.run(
        [str(binary)], input=payload, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if valid:
        if completed.returncode != 0 or completed.stderr:
            raise TimedParserFixtureError(
                "valid timed parser vector failed: "
                f"rc={completed.returncode}, stdout={completed.stdout!r}, "
                f"stderr={completed.stderr!r}"
            )
        return _parse_output(completed.stdout)
    if completed.returncode != 2 or not completed.stdout.startswith(b"ERR rc=-"):
        raise TimedParserFixtureError(
            "invalid timed parser vector did not fail closed: "
            f"rc={completed.returncode}, stdout={completed.stdout!r}"
        )
    return None


def audit(repo_root: Path | None = None) -> dict[str, Any]:
    root = (repo_root or Path(__file__).resolve().parents[5]).resolve()
    paths = {
        "parser": root / PARSER,
        "fixture": root / HOST_FIXTURE,
        "script": root / FIXTURE_SCRIPT,
        "module": root / MODULE_SOURCE,
    }
    clang = root / PINNED_CLANG
    cc = shutil.which("cc")
    file_tool = shutil.which("file")
    if not all(path.is_file() for path in paths.values()):
        raise TimedParserFixtureError("timed parser source closure is missing")
    if cc is None or file_tool is None or not clang.is_file():
        raise TimedParserFixtureError("timed parser compiler closure is missing")
    module_text = paths["module"].read_text(encoding="utf-8")
    for token in (
        '"v=2 stage=%u rc=%d pmic_v=%02x pmic_id=%02x "',
        '"seen=%02x wr_attempt=%u wr_amb=%u tm=%02x "',
        '"tpre=%llu twrite=%llu tpost1=%llu tpost2=%llu "',
        "result->pre_ns = ktime_get_ns();",
        "result->write_ns = ktime_get_ns();",
        "result->post1_ns = ktime_get_ns();",
        "result->post2_ns = ktime_get_ns();",
    ):
        if token not in module_text:
            raise TimedParserFixtureError(f"timed module source lacks {token!r}")

    with tempfile.TemporaryDirectory(prefix="s22plus-p318-timed-parser-") as tmp:
        temporary = Path(tmp)
        binary = temporary / "parser"
        subprocess.run(
            [cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
             "-I", str(paths["fixture"].parent), str(paths["fixture"]),
             "-o", str(binary)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        abc = subprocess.run(
            [str(binary), "--sha-abc"], check=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        ).stdout.strip()
        if abc != ABC_SHA256:
            raise TimedParserFixtureError("timed parser SHA-256 self-test differs")

        long_poll = bytes((*range(99), 0x80))
        valid = (
            _result(),
            _result(write=False),
            _result(polls=(long_poll, b"\x80", b"\x80", b"\x80")),
            _timeout_pre(),
        )
        valid_hashes: list[str] = []
        for payload in valid:
            output = _run(binary, payload, valid=True)
            if output != _expected(payload):
                raise TimedParserFixtureError("actual timed parser output differs")
            valid_hashes.append(hashlib.sha256(payload).hexdigest())

        canonical = _result()
        mutations = {
            "legacy_version": canonical.replace(b"v=2", b"v=1", 1),
            "leading_zero_u64": canonical.replace(b"tpre=1000000000", b"tpre=01000000000", 1),
            "u64_overflow": canonical.replace(b"tpre=1000000000", b"tpre=18446744073709551616", 1),
            "unknown_mask_bit": canonical.replace(b"tm=0f", b"tm=1f", 1),
            "missing_pre_bit": canonical.replace(b"tm=0f", b"tm=0e", 1),
            "missing_write_bit": canonical.replace(b"tm=0f", b"tm=0d", 1),
            "zero_pre_with_bit": canonical.replace(b"tpre=1000000000", b"tpre=0", 1),
            "nonzero_write_without_bit": _result(write=False).replace(b"twrite=0", b"twrite=1000100000", 1),
            "pre_after_write": canonical.replace(b"tpre=1000000000", b"tpre=1000200000", 1),
            "write_after_post1": canonical.replace(b"twrite=1000100000", b"twrite=1002000000", 1),
            "post1_after_post2": canonical.replace(b"tpost1=1001000000", b"tpost1=32000000000", 1),
            "retention_short": canonical.replace(b"tpost2=31001000000", b"tpost2=31000999999", 1),
            "complete_stage_partial_mask": canonical.replace(b"tm=0f", b"tm=07", 1),
            "trailing_byte": canonical + b"x",
        }
        for payload in mutations.values():
            _run(binary, payload, valid=False)

        cross = temporary / "cross.c"
        cross_obj = temporary / "cross.o"
        cross.write_text(
            "#include <stddef.h>\n#include <stdint.h>\n"
            f'#include "{paths["parser"]}"\n'
            "int p318_timed_parse(const char *p, size_t n, "
            "struct s22plus_max77705_runtime_result *r, "
            "struct s22plus_max77705_runtime_poll_summary *s) {"
            "return s22plus_max77705_runtime_parse_result(p,n,r,s);}\n",
            encoding="ascii",
        )
        subprocess.run(
            [str(clang), "--target=aarch64-linux-gnu", "-ffreestanding",
             "-fno-builtin", "-std=c11", "-O2", "-Wall", "-Wextra",
             "-Werror", "-c", str(cross), "-o", str(cross_obj)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        cross_file = subprocess.run(
            [file_tool, str(cross_obj)], check=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        ).stdout.strip().split(": ", 1)[-1]
        if not re.search(r"ELF 64-bit LSB relocatable, ARM aarch64", cross_file):
            raise TimedParserFixtureError("timed parser cross object is not AArch64")

    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "host_only": True,
        "device_contact": False,
        "source_identities": {
            name: {"path": str(path.relative_to(root)), "size": path.stat().st_size,
                   "sha256": _sha256(path)}
            for name, path in paths.items()
        },
        "pinned_aarch64_clang": {
            "path": str(PINNED_CLANG), "size": clang.stat().st_size,
            "sha256": _sha256(clang),
        },
        "valid_vector_count": len(valid),
        "invalid_mutation_count": len(mutations),
        "valid_vector_sha256": valid_hashes,
        "timing_mask_and_value_bijection": True,
        "source_reachable_stage_masks": True,
        "monotonic_sample_order_enforced": True,
        "retention_minimum_ns": RETENTION_NS,
        "aarch64_freestanding_compile": True,
        "aarch64_object_file": cross_file,
        "sysfs_integration": False,
        "candidate_ready": False,
        "verified": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    try:
        result = audit(args.repo_root)
    except (TimedParserFixtureError, OSError, subprocess.SubprocessError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    root = (args.repo_root or Path(__file__).resolve().parents[5]).resolve()
    output = args.output.resolve() if args.output is not None else root / DEFAULT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(output)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
