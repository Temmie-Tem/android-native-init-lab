#!/usr/bin/env python3
"""Cross-check the actual native Max77705 envelope encoder byte-for-byte."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

import s22plus_fyg8_max77705_process_v2_adapter_fixture as vectors
import s22plus_fyg8_max77705_telemetry as telemetry


SCHEMA = "s22plus_fyg8_max77705_native_envelope_fixture_v1"
VERDICT = "PASS_S22PLUS_FYG8_MAX77705_NATIVE_ENVELOPE_HOST_ONLY"
SOURCE = Path(
    "workspace/public/src/native-init/"
    "s22plus_fyg8_max77705_envelope_fixture.c"
)
INCLUDE_ROOT = Path("workspace/public/src/native-init")
CLANG = Path(
    "workspace/private/work/toolchains/aosp-clang-android12-release/"
    "clang-r416183b/bin/clang"
)
DETAIL_RE = re.compile(rb"detail=([0-9a-f]{4})\n\Z")


class FixtureError(ValueError):
    pass


def _binding_args(binding: telemetry.BindingWitness) -> list[str]:
    return [str(value) for value in binding.values()]


def _run(
    executable: Path,
    *,
    binding: telemetry.BindingWitness,
    terminal_bucket: str | None = None,
    mux_class: str | None = None,
    result: telemetry.DiagnosticResult | None = None,
    observer_site: str | None = None,
    observer_error_class: str | None = None,
) -> tuple[bytes, int]:
    if (terminal_bucket is None) == (mux_class is None):
        raise FixtureError("fixture semantic selection differs")
    if terminal_bucket is not None:
        kind = "terminal"
        code = telemetry.TERMINAL_CODE_BY_KEY[terminal_bucket]
    else:
        kind = "mux"
        code = telemetry.MUX_CODE_BY_NAME[str(mux_class)]
    completed = subprocess.run(
        [
            str(executable),
            kind,
            str(code),
            str(telemetry.OBSERVER_SITES[observer_site or "none"]),
            str(
                telemetry.OBSERVER_ERROR_CLASSES[
                    observer_error_class or "none"
                ]
            ),
            *_binding_args(binding),
        ],
        input=b"" if result is None else telemetry.format_module_result(result),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        raise FixtureError(
            f"native envelope fixture failed: rc={completed.returncode} "
            f"stderr={completed.stderr!r}"
        )
    match = DETAIL_RE.fullmatch(completed.stderr)
    if match is None:
        raise FixtureError("native envelope detail receipt differs")
    return completed.stdout, int(match.group(1), 16)


def audit(root: Path) -> dict[str, object]:
    compiler = root / CLANG
    source = root / SOURCE
    include_root = root / INCLUDE_ROOT
    if not compiler.is_file() or not source.is_file():
        raise FixtureError("native envelope fixture input is missing")

    rows: list[
        tuple[
            str,
            telemetry.BindingWitness,
            str | None,
            str | None,
            telemetry.DiagnosticResult | None,
            str | None,
            str | None,
        ]
    ] = []
    eagain = vectors._eagain_bindings()  # noqa: SLF001
    representative = {
        telemetry.eagain_terminal_bucket(name): binding
        for name, binding in eagain.items()
    }
    for bucket in telemetry.TERMINAL_BUCKET_KEYS:
        result = None
        if bucket == "probe_terminal_failure":
            result = vectors._failure_result(4)  # noqa: SLF001
        elif bucket == "matching_parent_identity_rejected":
            result = vectors._failure_result(2, rc=-19)  # noqa: SLF001
        rows.append(
            (
                f"terminal:{bucket}",
                representative.get(bucket, vectors._binding()),  # noqa: SLF001
                bucket,
                None,
                result,
                None,
                None,
            )
        )
    for mux_class in telemetry.MUX_DEVICE_CLASSES:
        rows.append(
            (
                f"mux:{mux_class}",
                vectors._binding(),  # noqa: SLF001
                None,
                mux_class,
                vectors._result_for_mux(mux_class),  # noqa: SLF001
                None,
                None,
            )
        )
    rows.append(
        (
            "overflow",
            vectors._binding(),  # noqa: SLF001
            None,
            telemetry.MUX_DEVICE_CLASSES[0],
            vectors._result(  # noqa: SLF001
                polls=tuple(vectors._uncompressible_poll() for _ in range(4))  # noqa: SLF001
            ),
            None,
            None,
        )
    )
    for site in tuple(telemetry.OBSERVER_SITES)[1:]:
        for error_class in tuple(telemetry.OBSERVER_ERROR_CLASSES)[1:]:
            rows.append(
                (
                    f"observer:{site}:{error_class}",
                    vectors._observer_binding(site),  # noqa: SLF001
                    "synchronous_probe_or_publication_contradiction",
                    None,
                    None,
                    site,
                    error_class,
                )
            )

    receipts: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="s22-max77705-envelope-") as name:
        directory = Path(name)
        executable = directory / "fixture"
        host = subprocess.run(
            [
                str(compiler),
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-I",
                str(include_root),
                str(source),
                "-o",
                str(executable),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            check=False,
        )
        if host.returncode != 0:
            raise FixtureError(f"native envelope host compile failed: {host.stderr!r}")
        cross_source = directory / "cross.c"
        cross_source.write_text(
            "#include <stddef.h>\n#include <stdint.h>\n"
            "void *memset(void *p, int v, size_t n) { "
            "unsigned char *q = p; while (n-- != 0) *q++ = (unsigned char)v; "
            "return p; }\n"
            f'#include "{root / INCLUDE_ROOT / "s22plus_fyg8_max77705_result_parser.inc.c"}"\n'
            f'#include "{root / INCLUDE_ROOT / "s22plus_fyg8_max77705_envelope.inc.c"}"\n'
            "int cross_entry(const struct s22plus_max77705_binding_witness *b, "
            "const struct s22plus_max77705_runtime_result *r, "
            "const struct s22plus_max77705_runtime_poll_summary *s, "
            "unsigned char out[128], unsigned short *d) { "
            "return s22plus_max77705_encode_envelope(b, 2, 1, 0, 0, r, s, out, d); }\n"
            "int cross_parse(const char *p, size_t n, "
            "struct s22plus_max77705_runtime_result *r, "
            "struct s22plus_max77705_runtime_poll_summary *s) { "
            "return s22plus_max77705_runtime_parse_result(p, n, r, s); }\n",
            encoding="ascii",
        )
        aarch64 = subprocess.run(
            [
                str(compiler),
                "--target=aarch64-linux-gnu",
                "-std=c11",
                "-ffreestanding",
                "-fno-builtin",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-c",
                str(cross_source),
                "-o",
                str(directory / "fixture.o"),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            check=False,
        )
        if aarch64.returncode != 0:
            raise FixtureError(
                f"native envelope AArch64 compile failed: {aarch64.stderr!r}"
            )
        for (
            label,
            binding,
            terminal_bucket,
            mux_class,
            result,
            observer_site,
            observer_error_class,
        ) in rows:
            expected = telemetry.encode_envelope(
                binding=binding,
                terminal_bucket=terminal_bucket,
                mux_class=mux_class,
                result=result,
                observer_site=observer_site,
                observer_error_class=observer_error_class,
            )
            actual, detail = _run(
                executable,
                binding=binding,
                terminal_bucket=terminal_bucket,
                mux_class=mux_class,
                result=result,
                observer_site=observer_site,
                observer_error_class=observer_error_class,
            )
            if actual != expected:
                raise FixtureError(f"native envelope bytes differ: {label}")
            decoded = telemetry.decode_envelope(actual)
            if detail != telemetry.expected_b_detail(decoded):
                raise FixtureError(f"native envelope detail differs: {label}")
            receipts[label] = hashlib.sha256(actual).hexdigest()

    if len(set(receipts.values())) != len(receipts):
        raise FixtureError("native envelope fixture rows collide")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "row_count": len(rows),
        "terminal_rows": len(telemetry.TERMINAL_BUCKET_KEYS),
        "mux_rows": len(telemetry.MUX_DEVICE_CLASSES),
        "overflow_rows": 1,
        "observer_site_error_rows": (
            (len(telemetry.OBSERVER_SITES) - 1)
            * (len(telemetry.OBSERVER_ERROR_CLASSES) - 1)
        ),
        "byte_exact_python_authority": True,
        "aarch64_freestanding_compile": True,
        "receipts": receipts,
        "verified": True,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[5]
    try:
        result = audit(root)
    except (FixtureError, telemetry.TelemetryError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
