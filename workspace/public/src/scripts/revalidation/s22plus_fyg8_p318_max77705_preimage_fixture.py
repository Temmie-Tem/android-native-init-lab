#!/usr/bin/env python3
"""Execute every P3.18 retained semantic through the actual C v4 encoder."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any

import s22plus_fyg8_max77705_process_v2_adapter_fixture as vectors
import s22plus_fyg8_max77705_telemetry as inherited
import s22plus_fyg8_p317_max77705_envelope_fixture as p317_vectors
import s22plus_fyg8_p317_max77705_telemetry as p317
import s22plus_fyg8_p318_max77705_envelope_qualification as qualified
import s22plus_fyg8_p318_max77705_telemetry as telemetry


SCHEMA = "s22plus_fyg8_p318_max77705_native_preimage_fixture_v1"
VERDICT = "PASS_P318_MAX77705_NATIVE_ENVELOPE_V4_PREIMAGES_HOST_ONLY"
SOURCE = Path(
    "workspace/public/src/native-init/"
    "s22plus_fyg8_p318_max77705_preimage_fixture.c"
)
INCLUDE_ROOT = Path("workspace/public/src/native-init")
CLANG = Path(
    "workspace/private/work/toolchains/aosp-clang-android12-release/"
    "clang-r416183b/bin/clang"
)
DETAIL_RE = re.compile(rb"detail=([0-9a-f]{4})\n\Z")


class FixtureError(ValueError):
    pass


def _timing_mask(stage: int, attempted: int) -> int:
    if stage in {2, 3, 4, 5}:
        return 0
    if stage == 6:
        return 0x03
    if stage == 7:
        return 0x03 if attempted else 0x01
    if stage == 9:
        return 0x07 if attempted else 0x05
    if stage == 10:
        return 0x0F if attempted else 0x0D
    raise FixtureError(f"P3.18 source-unreachable result stage: {stage}")


def _timed(result: inherited.DiagnosticResult) -> telemetry.TimedDiagnosticResult:
    mask = _timing_mask(result.stage, result.write_attempted)
    return telemetry.TimedDiagnosticResult(
        stage=result.stage,
        rc=result.rc,
        pmic_valid_mask=result.pmic_valid_mask,
        pmic_id=result.pmic_id,
        pmic_rev=result.pmic_rev,
        initial_uic_valid=result.initial_uic_valid,
        initial_uic=result.initial_uic,
        command_issued_mask=result.command_issued_mask,
        response_seen_mask=result.response_seen_mask,
        response_opcode=result.response_opcode,
        response_value=result.response_value,
        poll_bytes=result.poll_bytes,
        write_attempted=result.write_attempted,
        write_ambiguous=result.write_ambiguous,
        timing_valid_mask=mask,
        pre_ns=1_000_000_000 if mask & 0x01 else 0,
        write_ns=1_000_100_000 if mask & 0x02 else 0,
        post1_ns=1_001_000_000 if mask & 0x04 else 0,
        post2_ns=31_001_000_000 if mask & 0x08 else 0,
    )


def _format_result(result: telemetry.TimedDiagnosticResult) -> bytes:
    head = (
        f"v=2 stage={result.stage} rc={result.rc} "
        f"pmic_v={result.pmic_valid_mask:02x} pmic_id={result.pmic_id:02x} "
        f"pmic_rev={result.pmic_rev:02x} uic0_v={result.initial_uic_valid} "
        f"uic0={result.initial_uic:02x} issued={result.command_issued_mask:02x} "
        f"seen={result.response_seen_mask:02x} wr_attempt={result.write_attempted} "
        f"wr_amb={result.write_ambiguous} tm={result.timing_valid_mask:02x} "
        f"tpre={result.pre_ns} twrite={result.write_ns} "
        f"tpost1={result.post1_ns} tpost2={result.post2_ns} "
        f"rsp={bytes(result.response_opcode).hex()} "
        f"val={bytes(result.response_value).hex()}"
    )
    polls = " ".join(
        f"p{index}n={len(poll)} p{index}={poll.hex()}"
        for index, poll in enumerate(result.poll_bytes)
    )
    return f"{head} {polls}\n".encode("ascii")


def _latch_for(result: telemetry.TimedDiagnosticResult | None) -> telemetry.LatchSnapshot | None:
    if result is None or not result.timing_valid_mask & telemetry.TIME_PRE:
        return None
    return qualified._latch(1)  # noqa: SLF001


def _latch_text(latch: telemetry.LatchSnapshot | None) -> str:
    if latch is None:
        return "-"
    return (
        f"v=1 install_v={latch.install_valid} install_ns={latch.install_ns} "
        f"gate_v={latch.exposure_valid} gate_ns={latch.exposure_ns} "
        f"event_v={latch.event_valid} event_ns={latch.event_ns} "
        f"kind={latch.event_kind} raw={latch.event_raw:08x}\n"
    )


def _banner() -> telemetry.BannerResult:
    return qualified._banner("written", "none", 49)  # noqa: SLF001


def _observer_binding(site: str) -> inherited.BindingWitness:
    if site == "exposure-gate":
        return qualified._gate_binding()  # noqa: SLF001
    if site == "timing-latch":
        return qualified._binding()  # noqa: SLF001
    return p317_vectors._observer_binding(site)  # noqa: SLF001


def _observer_exec(site: str) -> p317.ExecWitness:
    if site == "exposure-gate":
        return qualified._gate_exec()  # noqa: SLF001
    if site == "timing-latch":
        return qualified._exec()  # noqa: SLF001
    return p317_vectors._observer_exec(site)  # noqa: SLF001


def _run(
    executable: Path,
    *,
    binding: inherited.BindingWitness,
    exec_witness: p317.ExecWitness,
    banner: telemetry.BannerResult,
    terminal_bucket: str | None = None,
    mux_class: str | None = None,
    result: telemetry.TimedDiagnosticResult | None = None,
    latch: telemetry.LatchSnapshot | None = None,
    observer_site: str | None = None,
    observer_error_class: str | None = None,
) -> tuple[bytes, int]:
    if (terminal_bucket is None) == (mux_class is None):
        raise FixtureError("P3.18 fixture semantic selection differs")
    kind = "terminal" if terminal_bucket is not None else "mux"
    code = (
        p317.TERMINAL_CODE_BY_KEY[str(terminal_bucket)]
        if terminal_bucket is not None
        else p317.MUX_CODE_BY_NAME[str(mux_class)]
    )
    command = [
        str(executable),
        kind,
        str(code),
        str(telemetry.OBSERVER_SITES[observer_site or "none"]),
        str(p317.OBSERVER_ERROR_CLASSES[observer_error_class or "none"]),
        *(str(value) for value in binding.values()),
        *(str(value) for value in exec_witness.values()),
        str(banner.outcome),
        str(banner.error_class),
        str(banner.bytes_written),
        _latch_text(latch),
    ]
    completed = subprocess.run(
        command,
        input=b"" if result is None else _format_result(result),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        raise FixtureError(
            f"P3.18 native envelope failed rc={completed.returncode}: "
            f"{completed.stderr!r}"
        )
    match = DETAIL_RE.fullmatch(completed.stderr)
    if match is None or len(completed.stdout) != telemetry.ENVELOPE_SIZE:
        raise FixtureError("P3.18 native envelope output differs")
    return completed.stdout, int(match.group(1), 16)


def _run_claim_busy(executable: Path) -> tuple[bytes, int]:
    completed = subprocess.run(
        [str(executable), "claim-busy"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )
    match = DETAIL_RE.fullmatch(completed.stderr)
    if (
        completed.returncode != 0
        or match is None
        or len(completed.stdout) != telemetry.ENVELOPE_SIZE
    ):
        raise FixtureError(
            "P3.18 native claim-busy normalization failed "
            f"rc={completed.returncode}: {completed.stderr!r}"
        )
    return completed.stdout, int(match.group(1), 16)


def _rows() -> tuple[list[dict[str, Any]], dict[str, str], int]:
    rows: list[dict[str, Any]] = []
    eagain = vectors._eagain_bindings()  # noqa: SLF001
    representative: dict[str, inherited.BindingWitness] = {}
    labels: dict[str, str] = {}
    additional: list[tuple[str, inherited.BindingWitness, str, str]] = []
    result_buckets = {"matching_parent_identity_rejected"}
    for name, binding in eagain.items():
        bucket = inherited.eagain_terminal_bucket(name)
        if bucket not in representative:
            representative[bucket] = binding
            if bucket not in result_buckets:
                labels[name] = f"terminal:{bucket}"
            else:
                label = f"eagain:{name}"
                labels[name] = label
                additional.append((name, binding, bucket, label))
        else:
            label = f"eagain:{name}"
            labels[name] = label
            additional.append((name, binding, bucket, label))

    for bucket in p317.TERMINAL_BUCKET_KEYS:
        base_result = None
        if bucket == "probe_terminal_failure":
            base_result = vectors._failure_result(4)  # noqa: SLF001
        elif bucket == "matching_parent_identity_rejected":
            base_result = vectors._failure_result(2, rc=-19)  # noqa: SLF001
        result = None if base_result is None else _timed(base_result)
        rows.append({
            "label": f"terminal:{bucket}",
            "binding": representative.get(bucket, vectors._binding()),  # noqa: SLF001
            "exec_witness": p317_vectors._exec_for_terminal(bucket),  # noqa: SLF001
            "banner": _banner(),
            "terminal_bucket": bucket,
            "result": result,
            "latch": _latch_for(result),
        })
    for _name, binding, bucket, label in additional:
        rows.append({
            "label": label,
            "binding": binding,
            "exec_witness": p317_vectors._exec_for_terminal(bucket),  # noqa: SLF001
            "banner": _banner(),
            "terminal_bucket": bucket,
        })
    for mux_class in p317.MUX_DEVICE_CLASSES:
        result = _timed(vectors._result_for_mux(mux_class))  # noqa: SLF001
        rows.append({
            "label": f"mux:{mux_class}",
            "binding": vectors._binding(),  # noqa: SLF001
            "exec_witness": p317_vectors._exec(),  # noqa: SLF001
            "banner": _banner(),
            "mux_class": mux_class,
            "result": result,
            "latch": _latch_for(result),
        })
    overflow = _timed(vectors._result(  # noqa: SLF001
        polls=tuple(vectors._uncompressible_poll() for _ in range(4))  # noqa: SLF001
    ))
    rows.append({
        "label": "overflow",
        "binding": vectors._binding(),  # noqa: SLF001
        "exec_witness": p317_vectors._exec(),  # noqa: SLF001
        "banner": _banner(),
        "mux_class": p317.MUX_DEVICE_CLASSES[0],
        "result": overflow,
        "latch": _latch_for(overflow),
    })
    for site in tuple(telemetry.OBSERVER_SITES)[1:]:
        for error_class in tuple(p317.OBSERVER_ERROR_CLASSES)[1:]:
            rows.append({
                "label": f"observer:{site}:{error_class}",
                "binding": _observer_binding(site),
                "exec_witness": _observer_exec(site),
                "banner": _banner(),
                "terminal_bucket": "synchronous_probe_or_publication_contradiction",
                "observer_site": site,
                "observer_error_class": error_class,
            })
    return rows, labels, len(additional)


def audit(root: Path | None = None) -> dict[str, Any]:
    root = (root or Path(__file__).resolve().parents[5]).resolve()
    compiler = root / CLANG
    source = root / SOURCE
    include_root = root / INCLUDE_ROOT
    if not compiler.is_file() or not source.is_file():
        raise FixtureError("P3.18 preimage fixture input is missing")
    rows, eagain_labels, additional_eagain = _rows()
    receipts: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="s22-p318-preimages-") as name:
        directory = Path(name)
        executable = directory / "fixture"
        compiled = subprocess.run(
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
        if compiled.returncode != 0:
            raise FixtureError(
                f"P3.18 preimage host compile failed: {compiled.stderr!r}"
            )
        for row in rows:
            kwargs = {key: value for key, value in row.items() if key != "label"}
            expected = telemetry.encode_envelope(**kwargs)
            actual, detail = _run(executable, **kwargs)
            if actual != expected:
                raise FixtureError(f"P3.18 native bytes differ: {row['label']}")
            decoded = telemetry.decode_envelope(actual)
            if detail != telemetry.expected_b_detail(decoded):
                raise FixtureError(f"P3.18 native detail differs: {row['label']}")
            receipts[str(row["label"])] = hashlib.sha256(actual).hexdigest()

        claim_actual, claim_detail = _run_claim_busy(executable)
        claim_expected = telemetry.encode_envelope(
            binding=p317_vectors._claim_busy_binding(),  # noqa: SLF001
            exec_witness=p317_vectors._exec(),  # noqa: SLF001
            banner=qualified._banner("not_attempted", "none", 0),  # noqa: SLF001
            terminal_bucket="synchronous_probe_or_publication_contradiction",
            observer_site="result-policy",
            observer_error_class="io-format",
        )
        claim_decoded = telemetry.decode_envelope(claim_actual)
        if (
            claim_actual != claim_expected
            or claim_detail != telemetry.expected_b_detail(claim_decoded)
            or claim_decoded.get("eagain_row") is not None
        ):
            raise FixtureError("P3.18 claim-busy negative preimage differs")

    if len(receipts) != 121 or len(set(receipts.values())) != len(receipts):
        raise FixtureError("P3.18 native preimage count or uniqueness differs")
    if set(eagain_labels.values()) - set(receipts):
        raise FixtureError("P3.18 EAGAIN preimage map is incomplete")
    observer_rows = (
        (len(telemetry.OBSERVER_SITES) - 1)
        * (len(p317.OBSERVER_ERROR_CLASSES) - 1)
    )
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "row_count": len(rows),
        "terminal_rows": len(p317.TERMINAL_BUCKET_KEYS),
        "mux_rows": len(p317.MUX_DEVICE_CLASSES),
        "overflow_rows": 1,
        "observer_site_error_rows": observer_rows,
        "observable_eagain_rows": len(eagain_labels),
        "additional_eagain_rows": additional_eagain,
        "eagain_preimage_labels": eagain_labels,
        "claim_busy_policy_rejected": True,
        "claim_busy_decoder_preimage_empty": True,
        "claim_busy_negative_envelope_sha256": hashlib.sha256(
            claim_actual
        ).hexdigest(),
        "actual_c_python_byte_identity": True,
        "retained_vector_cross_group_unique": True,
        "receipts": receipts,
        "verified": True,
    }


def main() -> int:
    try:
        value = audit()
    except (FixtureError, telemetry.TelemetryV4Error, OSError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
