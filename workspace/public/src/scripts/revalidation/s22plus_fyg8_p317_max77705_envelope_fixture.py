#!/usr/bin/env python3
"""Cross-check the actual native P3.17 envelope-v3 encoder byte-for-byte."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

import s22plus_fyg8_max77705_process_v2_adapter_fixture as vectors
import s22plus_fyg8_max77705_telemetry as inherited
import s22plus_fyg8_p317_max77705_telemetry as telemetry


SCHEMA = "s22plus_fyg8_p317_max77705_native_envelope_fixture_v1"
VERDICT = "PASS_P317_MAX77705_NATIVE_ENVELOPE_V3_HOST_ONLY"
SOURCE = Path(
    "workspace/public/src/native-init/"
    "s22plus_fyg8_p317_max77705_envelope_fixture.c"
)
INCLUDE_ROOT = Path("workspace/public/src/native-init")
CLANG = Path(
    "workspace/private/work/toolchains/aosp-clang-android12-release/"
    "clang-r416183b/bin/clang"
)
DETAIL_RE = re.compile(rb"detail=([0-9a-f]{4})\n\Z")


class FixtureError(ValueError):
    pass


def _exec(**changes: int) -> telemetry.ExecWitness:
    values = {
        "policy": telemetry.POLICY_VALID
        | telemetry.POLICY_GADGET_READY
        | telemetry.POLICY_STATES["DEFAULT_ON_STRICT"],
        "pre_present": telemetry.PROVIDER_VALID | telemetry.PROVIDER_MASK,
        "pre_bound": telemetry.PROVIDER_MASK,
        "post_present": telemetry.PROVIDER_VALID | telemetry.PROVIDER_MASK,
        "post_bound": telemetry.PROVIDER_MASK,
        "link_waiting": telemetry.LINK_VALID
        | telemetry.WAITING_STATES["ZERO"]
        | (telemetry.SUPPLIER_STATES["EXACT_ONE"] << telemetry.SUPPLIER_SHIFT),
    }
    values.update(changes)
    return telemetry.ExecWitness(**values)


def _claim_busy_binding() -> inherited.BindingWitness:
    """One impossible post-return EAGAIN binding rejected by the C policy."""

    return vectors._binding(  # noqa: SLF001
        post_diagnostic_bound_parent_count=2,
    )


def _exec_for_terminal(bucket: str) -> telemetry.ExecWitness:
    if bucket == "fw_devlink_policy_precondition":
        return _exec(
            policy=telemetry.POLICY_VALID
            | telemetry.POLICY_GADGET_READY
            | telemetry.POLICY_STATES["FW_DEVLINK_TOKEN_PRESENT"],
            post_present=0,
            post_bound=0,
            link_waiting=0,
        )
    if bucket == "provider_preclient_precondition":
        return _exec(
            policy=0,
            pre_present=telemetry.PROVIDER_VALID | 0x03,
            pre_bound=0x03,
            post_present=0,
            post_bound=0,
            link_waiting=0,
        )
    if bucket == "provider_postclient_precondition":
        return _exec(
            post_present=telemetry.PROVIDER_VALID | 0x03,
            post_bound=0x03,
            link_waiting=0,
        )
    if bucket == "supplier_link_precondition":
        return _exec(
            link_waiting=telemetry.LINK_VALID
            | telemetry.WAITING_STATES["ZERO"]
            | (
                telemetry.SUPPLIER_STATES["FOREIGN_OR_MULTIPLE"]
                << telemetry.SUPPLIER_SHIFT
            )
        )
    if bucket == "waiting_for_supplier_precondition":
        return _exec(
            link_waiting=telemetry.LINK_VALID
            | telemetry.WAITING_STATES["ONE"]
            | (
                telemetry.SUPPLIER_STATES["EXACT_ONE"]
                << telemetry.SUPPLIER_SHIFT
            )
        )
    if bucket == "executability_witness_contradiction":
        return _exec(post_present=0, post_bound=0, link_waiting=0)
    return _exec()


def _observer_exec(site: str) -> telemetry.ExecWitness:
    if site in {"override-prepare", "provider-pre"}:
        return telemetry.ExecWitness(0, 0, 0, 0, 0, 0)
    if site == "cmdline":
        return _exec(
            policy=telemetry.POLICY_GADGET_READY,
            post_present=0,
            post_bound=0,
            link_waiting=0,
        )
    if site in {"substrate-verify", "pre-topology", "provider-post"}:
        return _exec(post_present=0, post_bound=0, link_waiting=0)
    if site == "waiting":
        return _exec(link_waiting=0)
    if site == "supplier":
        return _exec(link_waiting=telemetry.WAITING_STATES["ZERO"])
    return _exec()


def _observer_binding(site: str) -> inherited.BindingWitness:
    if site in {
        "override-prepare", "provider-pre", "cmdline", "substrate-verify",
        "pre-topology", "provider-post", "waiting", "supplier",
    }:
        return vectors._binding(  # noqa: SLF001
            loader_state=inherited.LOADER_STATES["NOT_STARTED"],
            pre_exact_parent_present=0,
            pre_exact_parent_driver_state=inherited.DRIVER_STATES["ABSENT"],
            pre_matching_unbound_parent_count=0,
            post_exact_parent_driver_state=inherited.DRIVER_STATES["ABSENT"],
            post_diagnostic_bound_parent_count=0,
            post_exact_adapter_muic_0x25_client_count=0,
        )
    return vectors._observer_binding(site)  # noqa: SLF001


def _run(
    executable: Path,
    *,
    binding: inherited.BindingWitness,
    exec_witness: telemetry.ExecWitness,
    terminal_bucket: str | None = None,
    mux_class: str | None = None,
    result: inherited.DiagnosticResult | None = None,
    observer_site: str | None = None,
    observer_error_class: str | None = None,
) -> tuple[bytes, int]:
    if (terminal_bucket is None) == (mux_class is None):
        raise FixtureError("P3.17 fixture semantic selection differs")
    kind = "terminal" if terminal_bucket is not None else "mux"
    code = (
        telemetry.TERMINAL_CODE_BY_KEY[str(terminal_bucket)]
        if terminal_bucket is not None
        else telemetry.MUX_CODE_BY_NAME[str(mux_class)]
    )
    completed = subprocess.run(
        [
            str(executable),
            kind,
            str(code),
            str(telemetry.OBSERVER_SITES[observer_site or "none"]),
            str(telemetry.OBSERVER_ERROR_CLASSES[observer_error_class or "none"]),
            *(str(value) for value in binding.values()),
            *(str(value) for value in exec_witness.values()),
        ],
        input=b"" if result is None else inherited.format_module_result(result),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        raise FixtureError(
            f"P3.17 native envelope failed rc={completed.returncode}: "
            f"{completed.stderr!r}"
        )
    match = DETAIL_RE.fullmatch(completed.stderr)
    if match is None:
        raise FixtureError("P3.17 native envelope detail receipt differs")
    return completed.stdout, int(match.group(1), 16)


def _run_claim_busy(executable: Path) -> tuple[bytes, int]:
    completed = subprocess.run(
        [str(executable), "claim-busy"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        raise FixtureError(
            "P3.17 native claim-busy normalization failed "
            f"rc={completed.returncode}: {completed.stderr!r}"
        )
    match = DETAIL_RE.fullmatch(completed.stderr)
    if match is None:
        raise FixtureError("P3.17 claim-busy detail receipt differs")
    return completed.stdout, int(match.group(1), 16)


def audit(root: Path | None = None) -> dict[str, object]:
    root = (root or Path(__file__).resolve().parents[5]).resolve()
    compiler = root / CLANG
    source = root / SOURCE
    include_root = root / INCLUDE_ROOT
    if not compiler.is_file() or not source.is_file():
        raise FixtureError("P3.17 envelope fixture input is missing")

    rows: list[dict[str, object]] = []
    eagain = vectors._eagain_bindings()  # noqa: SLF001
    representative: dict[str, inherited.BindingWitness] = {}
    eagain_preimage_labels: dict[str, str] = {}
    additional_eagain: list[
        tuple[str, inherited.BindingWitness, str, str]
    ] = []
    terminal_result_buckets = {"matching_parent_identity_rejected"}
    for name, binding in eagain.items():
        bucket = inherited.eagain_terminal_bucket(name)
        if bucket not in representative:
            representative[bucket] = binding
            if bucket not in terminal_result_buckets:
                eagain_preimage_labels[name] = f"terminal:{bucket}"
            else:
                label = f"eagain:{name}"
                eagain_preimage_labels[name] = label
                additional_eagain.append((name, binding, bucket, label))
        else:
            label = f"eagain:{name}"
            eagain_preimage_labels[name] = label
            additional_eagain.append((name, binding, bucket, label))
    for bucket in telemetry.TERMINAL_BUCKET_KEYS:
        result = None
        if bucket == "probe_terminal_failure":
            result = vectors._failure_result(4)  # noqa: SLF001
        elif bucket == "matching_parent_identity_rejected":
            result = vectors._failure_result(2, rc=-19)  # noqa: SLF001
        rows.append(
            {
                "label": f"terminal:{bucket}",
                "binding": representative.get(bucket, vectors._binding()),  # noqa: SLF001
                "exec_witness": _exec_for_terminal(bucket),
                "terminal_bucket": bucket,
                "result": result,
            }
        )
    for _name, binding, bucket, label in additional_eagain:
        rows.append(
            {
                "label": label,
                "binding": binding,
                "exec_witness": _exec_for_terminal(bucket),
                "terminal_bucket": bucket,
            }
        )
    for mux_class in telemetry.MUX_DEVICE_CLASSES:
        rows.append(
            {
                "label": f"mux:{mux_class}",
                "binding": vectors._binding(),  # noqa: SLF001
                "exec_witness": _exec(),
                "mux_class": mux_class,
                "result": vectors._result_for_mux(mux_class),  # noqa: SLF001
            }
        )
    rows.append(
        {
            "label": "overflow",
            "binding": vectors._binding(),  # noqa: SLF001
            "exec_witness": _exec(),
            "mux_class": telemetry.MUX_DEVICE_CLASSES[0],
            "result": vectors._result(  # noqa: SLF001
                polls=tuple(vectors._uncompressible_poll() for _ in range(4))  # noqa: SLF001
            ),
        }
    )
    for site in tuple(telemetry.OBSERVER_SITES)[1:]:
        for error_class in tuple(telemetry.OBSERVER_ERROR_CLASSES)[1:]:
            rows.append(
                {
                    "label": f"observer:{site}:{error_class}",
                    "binding": _observer_binding(site),
                    "exec_witness": _observer_exec(site),
                    "terminal_bucket": "synchronous_probe_or_publication_contradiction",
                    "observer_site": site,
                    "observer_error_class": error_class,
                }
            )

    receipts: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="s22-p317-envelope-") as name:
        directory = Path(name)
        executable = directory / "fixture"
        host = subprocess.run(
            [
                str(compiler), "-std=c11", "-O2", "-Wall", "-Wextra",
                "-Werror", "-I", str(include_root), str(source), "-o",
                str(executable),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            check=False,
        )
        if host.returncode != 0:
            raise FixtureError(f"P3.17 envelope host compile failed: {host.stderr!r}")
        cross_source = directory / "cross.c"
        cross_source.write_text(
            "#include <stddef.h>\n#include <stdint.h>\n"
            "void *memset(void *p, int v, size_t n) { unsigned char *q = p; "
            "while (n-- != 0) *q++ = (unsigned char)v; return p; }\n"
            f'#include "{include_root / "s22plus_fyg8_max77705_result_parser.inc.c"}"\n'
            f'#include "{include_root / "s22plus_fyg8_max77705_envelope.inc.c"}"\n'
            f'#include "{include_root / "s22plus_fyg8_p317_max77705_envelope.inc.c"}"\n'
            "int cross_entry(const struct s22plus_max77705_binding_witness *b, "
            "const struct s22plus_max77705_p317_exec_witness *x, "
            "unsigned char out[128], unsigned short *d) { return "
            "s22plus_max77705_p317_encode_envelope(b, x, 2, 10, 0, 0, 0, 0, out, d); }\n"
            "int cross_old(const struct s22plus_max77705_binding_witness *b, "
            "unsigned char out[128], unsigned short *d) { return "
            "s22plus_max77705_encode_envelope(b, 2, 1, 0, 0, 0, 0, out, d); }\n"
            "int cross_parse(const char *p, size_t n, "
            "struct s22plus_max77705_runtime_result *r, "
            "struct s22plus_max77705_runtime_poll_summary *s) { return "
            "s22plus_max77705_runtime_parse_result(p, n, r, s); }\n",
            encoding="ascii",
        )
        cross = subprocess.run(
            [
                str(compiler), "--target=aarch64-linux-gnu", "-std=c11",
                "-ffreestanding", "-fno-builtin", "-Wall", "-Wextra",
                "-Werror", "-c", str(cross_source), "-o",
                str(directory / "fixture.o"),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            check=False,
        )
        if cross.returncode != 0:
            raise FixtureError(f"P3.17 envelope AArch64 compile failed: {cross.stderr!r}")
        for row in rows:
            kwargs = {key: value for key, value in row.items() if key != "label"}
            expected = telemetry.encode_envelope(**kwargs)  # type: ignore[arg-type]
            try:
                actual, detail = _run(executable, **kwargs)  # type: ignore[arg-type]
            except FixtureError as exc:
                raise FixtureError(f"{row['label']}: {exc}") from exc
            if actual != expected:
                raise FixtureError(f"P3.17 native bytes differ: {row['label']}")
            decoded = telemetry.decode_envelope(actual)
            if detail != telemetry.expected_b_detail(decoded):
                raise FixtureError(f"P3.17 native detail differs: {row['label']}")
            receipts[str(row["label"])] = hashlib.sha256(actual).hexdigest()
        claim_busy_actual, claim_busy_detail = _run_claim_busy(executable)
        claim_busy_expected = telemetry.encode_envelope(
            binding=_claim_busy_binding(),
            exec_witness=_exec(),
            terminal_bucket="synchronous_probe_or_publication_contradiction",
            observer_site="result-policy",
            observer_error_class="io-format",
        )
        if claim_busy_actual != claim_busy_expected:
            raise FixtureError("P3.17 native claim-busy envelope differs")
        claim_busy_decoded = telemetry.decode_envelope(claim_busy_actual)
        if (
            claim_busy_detail != telemetry.expected_b_detail(claim_busy_decoded)
            or claim_busy_decoded.get("observer_site") != "result-policy"
            or claim_busy_decoded.get("observer_error_class") != "io-format"
            or claim_busy_decoded.get("eagain_row") is not None
        ):
            raise FixtureError("P3.17 claim-busy normalization semantics differ")
    if len(set(receipts.values())) != len(receipts):
        raise FixtureError("P3.17 native envelope rows collide")
    if (
        len(eagain_preimage_labels) != len(eagain)
        or any(label not in receipts for label in eagain_preimage_labels.values())
    ):
        raise FixtureError("P3.17 EAGAIN native preimage map is incomplete")
    observer_rows = (
        (len(telemetry.OBSERVER_SITES) - 1)
        * (len(telemetry.OBSERVER_ERROR_CLASSES) - 1)
    )
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "row_count": len(rows),
        "terminal_rows": len(telemetry.TERMINAL_BUCKET_KEYS),
        "mux_rows": len(telemetry.MUX_DEVICE_CLASSES),
        "overflow_rows": 1,
        "observer_site_error_rows": observer_rows,
        "observable_eagain_rows": len(eagain_preimage_labels),
        "additional_eagain_rows": len(additional_eagain),
        "eagain_preimage_labels": eagain_preimage_labels,
        "claim_busy_policy_rejected": True,
        "claim_busy_decoder_preimage_empty": True,
        "claim_busy_normalized_observer_site": "result-policy",
        "claim_busy_normalized_error_class": "io-format",
        "claim_busy_negative_envelope_sha256": hashlib.sha256(
            claim_busy_actual
        ).hexdigest(),
        "byte_exact_python_authority": True,
        "aarch64_freestanding_compile": True,
        "authority_masks_decoded": True,
        "receipts": receipts,
        "verified": True,
    }


def main() -> int:
    try:
        result = audit()
    except (
        FixtureError, telemetry.TelemetryError, OSError, subprocess.TimeoutExpired
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
