#!/usr/bin/env python3
"""Host-qualify the exact P3.18 latch snapshot/readback parser."""

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


SCHEMA = "s22plus_fyg8_p318_dwc3_latch_parser_qualification_v1"
VERDICT = "PASS_P318_ACTUAL_DWC3_LATCH_PARSER_HOST_ONLY"
NATIVE = Path("workspace/public/src/native-init")
PARSER = NATIVE / "s22plus_fyg8_p318_dwc3_latch_parser.inc.c"
FIXTURE = NATIVE / "s22plus_fyg8_p318_dwc3_latch_parser_fixture.c"
MODULE = Path(
    "workspace/public/src/kernel-modules/s22plus_dwc3_event_latch/"
    "s22plus_dwc3_event_latch.c"
)
SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_dwc3_latch_parser_qualification.py"
)
CLANG = Path(
    "workspace/private/work/toolchains/aosp-clang-android12-release/"
    "clang-r416183b/bin/clang"
)
DEFAULT_OUTPUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "dwc3-latch-parser-qualification-20260814-01.json"
)


class LatchParserError(ValueError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(binary: Path, value: bytes, valid: bool) -> bytes:
    completed = subprocess.run(
        [str(binary)], input=value, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if valid:
        if completed.returncode != 0 or not completed.stdout.startswith(b"OK "):
            raise LatchParserError(f"valid latch snapshot failed: {completed.stdout!r}")
    elif completed.returncode != 2 or completed.stdout != b"ERR\n":
        raise LatchParserError(f"invalid latch snapshot did not fail: {completed.stdout!r}")
    return completed.stdout


def audit(repo_root: Path | None = None) -> dict[str, Any]:
    root = (repo_root or Path(__file__).resolve().parents[5]).resolve()
    paths = [root / item for item in (PARSER, FIXTURE, MODULE, SCRIPT)]
    clang = root / CLANG
    cc = shutil.which("cc")
    file_tool = shutil.which("file")
    if cc is None or file_tool is None or not clang.is_file() or not all(path.is_file() for path in paths):
        raise LatchParserError("P3.18 latch parser closure is missing")
    module = (root / MODULE).read_text(encoding="utf-8")
    for token in (
        '"v=1 install_v=1 install_ns=%llu gate_v=%u gate_ns=%llu "',
        '"event_v=%u event_ns=%llu kind=%u raw=%08x\\n"',
        "smp_load_acquire(&s22plus_latch.gate_ready)",
        "smp_load_acquire(&s22plus_latch.event_ready)",
    ):
        if token not in module:
            raise LatchParserError(f"latch producer source lacks {token!r}")
    with tempfile.TemporaryDirectory(prefix="s22plus-p318-latch-parser-") as tmp:
        temporary = Path(tmp)
        binary = temporary / "fixture"
        subprocess.run(
            [cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
             "-I", str(root / NATIVE), str(root / FIXTURE), "-o", str(binary)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        valid = (
            b"v=1 install_v=1 install_ns=500 gate_v=0 gate_ns=0 event_v=0 event_ns=0 kind=0 raw=00000000\n",
            b"v=1 install_v=1 install_ns=500 gate_v=1 gate_ns=600 event_v=0 event_ns=0 kind=0 raw=00000000\n",
            b"v=1 install_v=1 install_ns=500 gate_v=1 gate_ns=600 event_v=1 event_ns=700 kind=1 raw=01ff0101\n",
            b"v=1 install_v=1 install_ns=500 gate_v=1 gate_ns=600 event_v=1 event_ns=700 kind=2 raw=00000201\n",
            b"v=1 install_v=1 install_ns=500 gate_v=1 gate_ns=600 event_v=1 event_ns=700 kind=3 raw=abcd3040\n",
        )
        valid_outputs = [hashlib.sha256(_run(binary, item, True)).hexdigest() for item in valid]
        base = valid[-1]
        invalid = {
            "legacy_or_future_version": base.replace(b"v=1", b"v=2", 1),
            "missing_newline": base[:-1],
            "extra_byte": base + b"x",
            "leading_zero_time": base.replace(b"install_ns=500", b"install_ns=0500", 1),
            "uppercase_hex": base.replace(b"abcd3040", b"ABCD3040", 1),
            "install_not_valid": base.replace(b"install_v=1", b"install_v=0", 1),
            "exposure_before_install": base.replace(b"gate_ns=600", b"gate_ns=400", 1),
            "event_without_gate": base.replace(b"gate_v=1 gate_ns=600", b"gate_v=0 gate_ns=0", 1),
            "event_before_gate": base.replace(b"event_ns=700", b"event_ns=550", 1),
            "reset_kind_setup_raw": base.replace(b"kind=3", b"kind=1", 1),
            "carkit_raw": base.replace(b"abcd3040", b"00000107", 1),
            "i2c_raw": base.replace(b"abcd3040", b"00000209", 1),
            "ep1_complete": base.replace(b"abcd3040", b"00000042", 1),
            "xfer_not_ready": base.replace(b"abcd3040", b"000000c0", 1),
        }
        for item in invalid.values():
            _run(binary, item, False)
        for gate, accepted in ((b"1\n", True), (b"0\n", False), (b"1", False), (b"1\n\n", False)):
            completed = subprocess.run([str(binary), "--gate"], input=gate, check=False)
            if (completed.returncode == 0) != accepted:
                raise LatchParserError("exposure gate readback grammar differs")
        cross = temporary / "cross.c"
        obj = temporary / "cross.o"
        cross.write_text(
            "#include <stddef.h>\n#include <stdint.h>\n"
            f'#include "{root / PARSER}"\n'
            "int entry(const char *p,size_t n,struct s22plus_max77705_p318_latch_snapshot *s){return s22plus_p318_parse_latch_snapshot(p,n,s);}\n"
            "int gate(const char *p,size_t n){return s22plus_p318_exposure_gate_readback_valid(p,n);}\n",
            encoding="ascii",
        )
        subprocess.run(
            [str(clang), "--target=aarch64-linux-gnu", "-ffreestanding", "-fno-builtin",
             "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-c", str(cross), "-o", str(obj)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        object_file = subprocess.run(
            [file_tool, str(obj)], check=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        ).stdout.strip().split(": ", 1)[-1]
        if not re.search(r"ELF 64-bit LSB relocatable, ARM aarch64", object_file):
            raise LatchParserError("latch parser cross object is not AArch64")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "host_only": True,
        "device_contact": False,
        "source_identities": [
            {"path": str(path.relative_to(root)), "size": path.stat().st_size, "sha256": _sha256(path)}
            for path in paths
        ],
        "valid_snapshot_count": len(valid),
        "invalid_snapshot_count": len(invalid),
        "valid_output_sha256": valid_outputs,
        "masked_raw_kind_cross_check": True,
        "gate_readback_exact_one_newline": True,
        "aarch64_freestanding_compile": True,
        "aarch64_object_file": object_file,
        "runtime_integration": False,
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
    except (LatchParserError, OSError, subprocess.SubprocessError, ValueError) as exc:
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
