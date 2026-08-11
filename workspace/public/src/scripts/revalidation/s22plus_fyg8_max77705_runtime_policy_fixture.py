#!/usr/bin/env python3
"""Execute the exact native P3.16 EAGAIN/result classification policy."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
import subprocess
import tempfile


SCHEMA = "s22plus_fyg8_max77705_runtime_policy_fixture_v1"
VERDICT = "PASS_S22PLUS_FYG8_MAX77705_RUNTIME_POLICY_HOST_ONLY"
SOURCE = Path(
    "workspace/public/src/native-init/"
    "s22plus_fyg8_max77705_runtime_policy_fixture.c"
)
INCLUDE = Path("workspace/public/src/native-init")
CLANG = Path(
    "workspace/private/work/toolchains/aosp-clang-android12-release/"
    "clang-r416183b/bin/clang"
)


class FixtureError(ValueError):
    pass


def audit(root: Path) -> dict[str, object]:
    source = root / SOURCE
    compiler = root / CLANG
    if not source.is_file() or not compiler.is_file():
        raise FixtureError("runtime policy fixture input is missing")
    with tempfile.TemporaryDirectory(prefix="s22-max77705-policy-") as name:
        directory = Path(name)
        executable = directory / "fixture"
        command = [
            str(compiler), "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
            "-I", str(root / INCLUDE), str(source), "-o", str(executable),
        ]
        built = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=60, check=False,
        )
        if built.returncode != 0:
            raise FixtureError(f"runtime policy compile failed: {built.stderr!r}")
        ran = subprocess.run(
            [str(executable)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=10, check=False,
        )
        if ran.returncode != 0 or ran.stderr:
            raise FixtureError(
                f"runtime policy execution failed: rc={ran.returncode} "
                f"stderr={ran.stderr!r}"
            )
        lines = ran.stdout.decode("ascii").splitlines()
        expected = Counter(
            {
                "eagain:probe-in-progress:1:6": 1,
                "eagain:no-match:1:2": 1,
                "eagain:wrong-address:1:3": 1,
                "eagain:other-driver:1:4": 1,
                "eagain:post-unbound:1:8": 1,
                "eagain:bound-not-ready:1:8": 1,
                "result:identity-rejected:1:3": 1,
                "result:identity-io:1:5": 1,
                "result:dummy-client:1:5": 1,
                "result:initial-uic:1:5": 1,
                "result:command-transaction:2:5": 4,
                "negative:retention-stage-rejected": 1,
                "result:positive-return:1:8": 1,
                "result:pre-nonusb-stable:2:1": 1,
                "result:pre-usb-stable:2:2": 1,
                "result:post-reversion:2:3": 1,
                "result:complete-other:2:4": 1,
            }
        )
        if Counter(lines) != expected:
            # Five command stages deliberately share one retained semantic.
            raise FixtureError("runtime policy row geometry differs")
        cross = directory / "cross.c"
        cross.write_text(
            "#include <stddef.h>\n#include <stdint.h>\n"
            "void *memset(void *p,int v,size_t n){unsigned char*q=p;"
            "while(n--)*q++=(unsigned char)v;return p;}\n"
            f'#include "{root / INCLUDE / "s22plus_fyg8_max77705_result_parser.inc.c"}"\n'
            f'#include "{root / INCLUDE / "s22plus_fyg8_max77705_envelope.inc.c"}"\n'
            f'#include "{root / INCLUDE / "s22plus_fyg8_max77705_runtime_policy.inc.c"}"\n'
            "int policy_result(struct s22plus_max77705_binding_witness*b,"
            "struct s22plus_max77705_runtime_result*r,unsigned char*k,"
            "unsigned char*c){return "
            "p316_policy_classify_result(b,r,k,c);}\n"
            "int policy_eagain(struct s22plus_max77705_binding_witness*b,"
            "unsigned char*k,unsigned char*c){return "
            "p316_policy_classify_eagain(b,k,c);}\n"
            "int policy_parse(const char*p,size_t n,"
            "struct s22plus_max77705_runtime_result*r,"
            "struct s22plus_max77705_runtime_poll_summary*s){return "
            "s22plus_max77705_runtime_parse_result(p,n,r,s);}\n"
            "int policy_encode(struct s22plus_max77705_binding_witness*b,"
            "struct s22plus_max77705_runtime_result*r,"
            "struct s22plus_max77705_runtime_poll_summary*s,"
            "unsigned char e[128],unsigned short*d){return "
            "s22plus_max77705_encode_envelope(b,2,1,0,0,r,s,e,d);}\n",
            encoding="ascii",
        )
        crossed = subprocess.run(
            [
                str(compiler), "--target=aarch64-linux-gnu", "-std=c11",
                "-ffreestanding", "-fno-builtin", "-Wall", "-Wextra",
                "-Werror", "-c", str(cross), "-o", str(directory / "cross.o"),
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=60, check=False,
        )
        if crossed.returncode != 0:
            raise FixtureError(
                f"runtime policy AArch64 compile failed: {crossed.stderr!r}"
            )
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "eagain_rows": 6,
        "result_rows": 14,
        "unique_rows": 17,
        "shared_transaction_rows": 4,
        "negative_invariants": 1,
        "native_stdout_sha256": hashlib.sha256(ran.stdout).hexdigest(),
        "aarch64_freestanding_compile": True,
        "verified": True,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[5]
    print(json.dumps(audit(root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
