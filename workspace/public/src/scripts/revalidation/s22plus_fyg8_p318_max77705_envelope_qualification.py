#!/usr/bin/env python3
"""Qualify the real P3.18 C envelope against the Python/Carrier authority."""

from __future__ import annotations

import argparse
import binascii
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
from typing import Any

import s22plus_fyg8_p317_max77705_telemetry as p317
import s22plus_fyg8_p318_max77705_telemetry as telemetry


SCHEMA = "s22plus_fyg8_p318_max77705_envelope_qualification_v2"
VERDICT = "PASS_P318_REAL_C_ENVELOPE_V4_HOST_ONLY"
NATIVE = Path("workspace/public/src/native-init")
SOURCES = (
    NATIVE / "s22plus_fyg8_p318_max77705_result_parser.inc.c",
    NATIVE / "s22plus_fyg8_p318_dwc3_latch_parser.inc.c",
    NATIVE / "s22plus_fyg8_max77705_envelope.inc.c",
    NATIVE / "s22plus_fyg8_max77705_runtime_policy.inc.c",
    NATIVE / "s22plus_fyg8_p317_max77705_envelope.inc.c",
    NATIVE / "s22plus_fyg8_p318_banner_writer.inc.c",
    NATIVE / "s22plus_fyg8_p318_max77705_envelope.inc.c",
    NATIVE / "s22plus_fyg8_p318_max77705_envelope_fixture.c",
    Path("workspace/public/src/scripts/revalidation/s22plus_fyg8_p318_max77705_telemetry.py"),
    Path("workspace/public/src/scripts/revalidation/s22plus_fyg8_p318_max77705_envelope_qualification.py"),
)
DEFAULT_OUTPUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "max77705-envelope-v4-qualification-20260814-01.json"
)


class EnvelopeQualificationError(ValueError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _binding() -> p317.inherited.BindingWitness:
    return p317.inherited.BindingWitness(
        loader_state=p317.inherited.LOADER_STATES["FINIT_MODULE_RETURNED_SUCCESS"],
        pre_exact_parent_present=1,
        pre_exact_parent_driver_state=p317.inherited.DRIVER_STATES["UNBOUND"],
        pre_matching_unbound_parent_count=1,
        pre_wrong_address_compatible_parent_count=0,
        post_exact_parent_driver_state=p317.inherited.DRIVER_STATES["DIAGNOSTIC"],
        post_diagnostic_bound_parent_count=1,
        post_exact_adapter_muic_0x25_client_count=1,
        post_foreign_0x25_client_count=0,
    )


def _exec() -> p317.ExecWitness:
    return p317.ExecWitness(
        policy=p317.POLICY_VALID | p317.POLICY_GADGET_READY | p317.POLICY_STATES["DEFAULT_ON_STRICT"],
        pre_present=p317.PROVIDER_VALID | p317.PROVIDER_MASK,
        pre_bound=p317.PROVIDER_MASK,
        post_present=p317.PROVIDER_VALID | p317.PROVIDER_MASK,
        post_bound=p317.PROVIDER_MASK,
        link_waiting=p317.LINK_VALID | p317.WAITING_STATES["ZERO"] | (p317.SUPPLIER_STATES["EXACT_ONE"] << p317.SUPPLIER_SHIFT),
    )


def _gate_binding() -> p317.inherited.BindingWitness:
    return p317.inherited.BindingWitness(
        loader_state=p317.inherited.LOADER_STATES["NOT_STARTED"],
        pre_exact_parent_present=0,
        pre_exact_parent_driver_state=p317.inherited.DRIVER_STATES["ABSENT"],
        pre_matching_unbound_parent_count=0,
        pre_wrong_address_compatible_parent_count=0,
        post_exact_parent_driver_state=p317.inherited.DRIVER_STATES["ABSENT"],
        post_diagnostic_bound_parent_count=0,
        post_exact_adapter_muic_0x25_client_count=0,
        post_foreign_0x25_client_count=0,
    )


def _gate_exec() -> p317.ExecWitness:
    # The provider-pre hook has run before p318_run(), but the gate precedes
    # UDC exposure and all later policy/post/supplier observations.  The v3
    # override-prepare authority row intentionally treats every exec field as
    # unavailable even though the already captured pre mask is retained raw.
    return p317.ExecWitness(
        policy=0,
        pre_present=p317.PROVIDER_VALID | p317.PROVIDER_MASK,
        pre_bound=p317.PROVIDER_MASK,
        post_present=0,
        post_bound=0,
        link_waiting=0,
    )


def _result(polls: tuple[bytes, bytes, bytes, bytes]) -> telemetry.TimedDiagnosticResult:
    return telemetry.TimedDiagnosticResult(
        stage=10,
        rc=0,
        pmic_valid_mask=3,
        pmic_id=0x15,
        pmic_rev=0x02,
        initial_uic_valid=1,
        initial_uic=0x04,
        command_issued_mask=0x0F,
        response_seen_mask=0x0F,
        response_opcode=(0x05, 0x06, 0x05, 0x05),
        response_value=(0x3F, 0, 0x09, 0x09),
        poll_bytes=polls,
        write_attempted=1,
        write_ambiguous=0,
        timing_valid_mask=0x0F,
        pre_ns=1_000_000_000,
        write_ns=1_000_100_000,
        post1_ns=1_001_000_000,
        post2_ns=31_001_000_000,
    )


def _format_result(result: telemetry.TimedDiagnosticResult) -> bytes:
    values = (
        f"v=2 stage={result.stage} rc={result.rc} pmic_v={result.pmic_valid_mask:02x} "
        f"pmic_id={result.pmic_id:02x} pmic_rev={result.pmic_rev:02x} "
        f"uic0_v={result.initial_uic_valid} uic0={result.initial_uic:02x} "
        f"issued={result.command_issued_mask:02x} seen={result.response_seen_mask:02x} "
        f"wr_attempt={result.write_attempted} wr_amb={result.write_ambiguous} "
        f"tm={result.timing_valid_mask:02x} tpre={result.pre_ns} "
        f"twrite={result.write_ns} tpost1={result.post1_ns} tpost2={result.post2_ns} "
        f"rsp={bytes(result.response_opcode).hex()} val={bytes(result.response_value).hex()}"
    )
    polls = " ".join(
        f"p{index}n={len(poll)} p{index}={poll.hex()}"
        for index, poll in enumerate(result.poll_bytes)
    )
    return f"{values} {polls}\n".encode("ascii")


def _latch(event_kind: int) -> telemetry.LatchSnapshot:
    raw = {0: 0, 1: 0x01FF0101, 2: 0x00000201, 3: 0xABCD3040}[event_kind]
    return telemetry.LatchSnapshot(
        install_valid=1,
        exposure_valid=1,
        event_valid=1 if event_kind else 0,
        event_kind=event_kind,
        install_ns=500_000_000,
        exposure_ns=900_000_000,
        event_ns=1_000_500_000 if event_kind else 0,
        event_raw=raw,
    )


def _banner(outcome: str, error: str, count: int) -> telemetry.BannerResult:
    return telemetry.BannerResult(
        telemetry.BANNER_OUTCOMES[outcome], telemetry.BANNER_ERRORS[error], count
    )


def _semantic(result: telemetry.TimedDiagnosticResult) -> tuple[str | None, str | None]:
    return p317.inherited.classify_diagnostic_result(_binding(), result.base())


def _python_envelope(
    result: telemetry.TimedDiagnosticResult,
    latch: telemetry.LatchSnapshot | None,
    banner: telemetry.BannerResult,
) -> bytes:
    terminal, mux = _semantic(result)
    return telemetry.encode_envelope(
        binding=_binding(), exec_witness=_exec(), result=result, latch=latch,
        banner=banner, terminal_bucket=terminal, mux_class=mux,
    )


def _c_envelope(
    binary: Path,
    result: telemetry.TimedDiagnosticResult,
    latch: telemetry.LatchSnapshot,
    banner: telemetry.BannerResult,
) -> tuple[bytes, str]:
    snapshot = (
        f"v=1 install_v={latch.install_valid} install_ns={latch.install_ns} "
        f"gate_v={latch.exposure_valid} gate_ns={latch.exposure_ns} "
        f"event_v={latch.event_valid} event_ns={latch.event_ns} "
        f"kind={latch.event_kind} raw={latch.event_raw:08x}\n"
    )
    command = [
        str(binary), str(banner.outcome), str(banner.error_class),
        str(banner.bytes_written), snapshot, "1\n",
    ]
    completed = subprocess.run(
        command, input=_format_result(result), stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode != 0 or len(completed.stdout) != telemetry.ENVELOPE_SIZE:
        raise EnvelopeQualificationError(
            f"actual C v4 encoder failed: rc={completed.returncode}, "
            f"stderr={completed.stderr!r}"
        )
    return completed.stdout, completed.stderr.decode("ascii").strip()


def _python_observer_envelope(
    *, site: str, error_class: str, banner: telemetry.BannerResult
) -> bytes:
    gate = site == "exposure-gate"
    return telemetry.encode_envelope(
        binding=_gate_binding() if gate else _binding(),
        exec_witness=_gate_exec() if gate else _exec(),
        banner=banner,
        terminal_bucket="synchronous_probe_or_publication_contradiction",
        observer_site=site,
        observer_error_class=error_class,
    )


def _c_observer_envelope(
    binary: Path,
    *,
    site: str,
    error_class: str,
    banner: telemetry.BannerResult,
) -> tuple[bytes, str]:
    mode = {
        "exposure-gate": "observer-gate",
        "timing-latch": "observer-latch",
    }[site]
    command = [
        str(binary), mode, str(banner.outcome), str(banner.error_class),
        str(banner.bytes_written), str(p317.OBSERVER_ERROR_CLASSES[error_class]),
    ]
    completed = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    if completed.returncode != 0 or len(completed.stdout) != telemetry.ENVELOPE_SIZE:
        raise EnvelopeQualificationError(
            f"actual C v4 observer encoder failed: site={site}, "
            f"rc={completed.returncode}, stderr={completed.stderr!r}"
        )
    return completed.stdout, completed.stderr.decode("ascii").strip()


def _recrc(value: bytearray) -> bytes:
    crc = binascii.crc32(telemetry.CRC_DOMAIN + value[:telemetry.CRC_OFFSET]) & 0xFFFFFFFF
    struct.pack_into("<I", value, telemetry.CRC_OFFSET, crc)
    return bytes(value)


def audit(repo_root: Path | None = None) -> dict[str, Any]:
    root = (repo_root or Path(__file__).resolve().parents[5]).resolve()
    sources = [root / path for path in SOURCES]
    cc = shutil.which("cc")
    if cc is None or not all(path.is_file() for path in sources):
        raise EnvelopeQualificationError("P3.18 envelope source closure is missing")
    with tempfile.TemporaryDirectory(prefix="s22plus-p318-envelope-") as tmp:
        temporary = Path(tmp)
        binary = temporary / "envelope-fixture"
        subprocess.run(
            [cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
             "-I", str(root / NATIVE), str(root / NATIVE / "s22plus_fyg8_p318_max77705_envelope_fixture.c"),
             "-o", str(binary)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

        lossless_polls = (bytes(range(1, 43)) + b"\x80", b"\x81", b"\x82", b"\x83")
        overflow_polls = (bytes(range(1, 44)) + b"\x80", b"\x81", b"\x82", b"\x83")
        cases = (
            ("lossless47_event_written", _result(lossless_polls), _latch(1), _banner("written", "none", 49)),
            ("lossless47_no_event_eagain", _result(lossless_polls), _latch(0), _banner("eagain_timeout", "eagain_deadline", 0)),
            ("lossless47_event_epipe", _result(lossless_polls), _latch(3), _banner("failure", "epipe", 0)),
            ("lossless47_event_enodev", _result(lossless_polls), _latch(2), _banner("failure", "enodev", 0)),
            ("overflow48_event_partial", _result(overflow_polls), _latch(1), _banner("partial", "eintr_deadline", 48)),
        )
        receipts: list[dict[str, Any]] = []
        decoded_by_name: dict[str, dict[str, Any]] = {}
        for name, result, latch, banner in cases:
            actual, detail = _c_envelope(binary, result, latch, banner)
            expected = _python_envelope(result, latch, banner)
            if actual != expected:
                raise EnvelopeQualificationError(f"actual C/Python v4 bytes differ: {name}")
            decoded = telemetry.decode_envelope(actual)
            run_id = hashlib.sha256(name.encode("ascii")).digest()[:16]
            carrier = telemetry.encode_carrier_record(actual, run_id=run_id)
            carrier_decoded = telemetry.decode_carrier_record(carrier, run_id=run_id)
            if carrier_decoded["timing"] != decoded["timing"] or carrier_decoded["banner"] != decoded["banner"]:
                raise EnvelopeQualificationError(
                    f"actual C v4 evidence changed through Carrier: {name}"
                )
            decoded_by_name[name] = decoded
            receipts.append({
                "name": name,
                "sha256": hashlib.sha256(actual).hexdigest(),
                "carrier_sha256": hashlib.sha256(carrier).hexdigest(),
                "detail": detail,
                "payload_used": decoded["payload_used_size"],
                "poll_encoded": decoded["poll_encoded_size"],
                "overflow": decoded["payload_overflow"],
                "timing_mask": decoded["timing"]["valid_mask"],
                "banner": decoded["banner"],
            })

        observer_cases = (
            ("exposure_gate_io_format", "exposure-gate", "io-format", _banner("written", "none", 49)),
            ("timing_latch_timeout", "timing-latch", "timeout-retry", _banner("eagain_timeout", "eagain_deadline", 0)),
        )
        observer_receipts: list[dict[str, Any]] = []
        for name, site, error_class, banner in observer_cases:
            actual, detail = _c_observer_envelope(
                binary, site=site, error_class=error_class, banner=banner
            )
            expected = _python_observer_envelope(
                site=site, error_class=error_class, banner=banner
            )
            if actual != expected:
                raise EnvelopeQualificationError(
                    f"actual C/Python v4 observer bytes differ: {site}"
                )
            decoded = telemetry.decode_envelope(actual)
            run_id = hashlib.sha256(name.encode("ascii")).digest()[:16]
            carrier = telemetry.encode_carrier_record(actual, run_id=run_id)
            carrier_decoded = telemetry.decode_carrier_record(carrier, run_id=run_id)
            if (
                carrier_decoded["observer_site"] != site
                or carrier_decoded["observer_error_class"] != error_class
                or carrier_decoded["terminal_bucket"]
                != "synchronous_probe_or_publication_contradiction"
            ):
                raise EnvelopeQualificationError(
                    f"P3.18 observer row changed through Carrier: {site}"
                )
            if site == "exposure-gate":
                if any(decoded["executability_authority"].values()) or any(
                    value for key, value in decoded["binding_authority"].items()
                    if key != "loader_state"
                ):
                    raise EnvelopeQualificationError(
                        "P3.18 pre-UDC gate observer gained unavailable authority"
                    )
            elif not all(decoded["executability_authority"].values()) or not all(
                decoded["binding_authority"].values()
            ):
                raise EnvelopeQualificationError(
                    "P3.18 terminal latch observer lost captured authority"
                )
            observer_receipts.append({
                "name": name,
                "observer_site": site,
                "observer_error_class": error_class,
                "sha256": hashlib.sha256(actual).hexdigest(),
                "carrier_sha256": hashlib.sha256(carrier).hexdigest(),
                "detail": detail,
                "binding_authority": decoded["binding_authority"],
                "executability_authority": decoded["executability_authority"],
                "banner": decoded["banner"],
            })
        if receipts[0]["poll_encoded"] != 47 or receipts[0]["payload_used"] != 76:
            raise EnvelopeQualificationError("P3.18 lossless-47 boundary differs")
        if receipts[-1]["poll_encoded"] != 44 or receipts[-1]["payload_used"] != 73 or not receipts[-1]["overflow"]:
            raise EnvelopeQualificationError("P3.18 overflow-48 boundary differs")

        overflow = bytearray(_python_envelope(_result(overflow_polls), _latch(1), _banner("partial", "eintr_deadline", 48)))
        overflow[telemetry.PAYLOAD_OFFSET + telemetry.OVERFLOW_USED] = 1
        try:
            telemetry.decode_envelope(_recrc(overflow))
        except telemetry.TelemetryV4Error:
            spare_rejected = True
        else:
            spare_rejected = False
        if not spare_rejected:
            raise EnvelopeQualificationError("P3.18 nonzero overflow spare was accepted")

        no_event = decoded_by_name["lossless47_no_event_eagain"]
        event = decoded_by_name["lossless47_event_written"]
        correlations = {
            "no_event_endpoint_absent": telemetry.correlate_host_receipt(no_event, receipt_complete=True, endpoint_present=False)["correlation_class"],
            "no_event_endpoint_present": telemetry.correlate_host_receipt(no_event, receipt_complete=True, endpoint_present=True)["correlation_class"],
            "event_endpoint_present": telemetry.correlate_host_receipt(event, receipt_complete=True, endpoint_present=True)["correlation_class"],
            "event_endpoint_absent": telemetry.correlate_host_receipt(event, receipt_complete=True, endpoint_present=False)["correlation_class"],
            "incomplete_receipt": telemetry.correlate_host_receipt(event, receipt_complete=False, endpoint_present=True)["correlation_class"],
        }
        expected_correlations = {
            "no_event_endpoint_absent": "DEVICE_RESULT_HOST_SILENT",
            "no_event_endpoint_present": "NO_PROOF_OBSERVER_LATCHED_EVENT_MISSING",
            "event_endpoint_present": "DEVICE_RESULT_HOST_EVENT_AND_ENDPOINT",
            "event_endpoint_absent": "DEVICE_RESULT_DWC3_HOST_EVENT_NO_ENDPOINT",
            "incomplete_receipt": "NO_PROOF_OBSERVER_HOST_RECEIPT_INCOMPLETE",
        }
        if correlations != expected_correlations:
            raise EnvelopeQualificationError("P3.18 host-receipt cross product differs")

        incomplete_latch = telemetry.LatchSnapshot(1, 0, 0, 0, 500_000_000, 0, 0, 0)
        incomplete = _python_envelope(_result(lossless_polls), incomplete_latch, _banner("written", "none", 49))
        incomplete_decoded = telemetry.decode_envelope(incomplete)
        if incomplete_decoded["timing"]["valid_mask"] != 0x2F or incomplete_decoded["causal_pending_complete_host_receipt"]:
            raise EnvelopeQualificationError("P3.18 missing exposure bit gained causal authority")

        invalid_banners = (
            telemetry.BannerResult(1, 0, 48),
            telemetry.BannerResult(2, 3, 0),
            telemetry.BannerResult(3, 1, 0),
            telemetry.BannerResult(4, 3, 0),
            telemetry.BannerResult(4, 3, 49),
        )
        for banner in invalid_banners:
            try:
                _python_envelope(_result(lossless_polls), _latch(1), banner)
            except telemetry.TelemetryV4Error:
                continue
            raise EnvelopeQualificationError("P3.18 invalid banner tuple was accepted")

    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "host_only": True,
        "device_contact": False,
        "source_identities": [
            {"path": str(path.relative_to(root)), "size": path.stat().st_size, "sha256": _sha256(path)}
            for path in sources
        ],
        "actual_c_python_byte_identity_cases": receipts,
        "actual_c_python_case_count": len(receipts),
        "actual_c_python_observer_cases": observer_receipts,
        "actual_c_python_observer_case_count": len(observer_receipts),
        "observer_sites_qualified": [
            row["observer_site"] for row in observer_receipts
        ],
        "lossless_boundary_encoded_bytes": 47,
        "overflow_boundary_encoded_bytes": 48,
        "overflow_summary_bytes": 44,
        "overflow_spare_bytes": 3,
        "nonzero_overflow_spare_rejected_after_valid_crc": spare_rejected,
        "host_receipt_cross_product": correlations,
        "missing_exposure_mask": 0x2F,
        "missing_exposure_causal_authority": False,
        "invalid_banner_tuple_count": len(invalid_banners),
        "actual_c_bytes_pass_real_carrier_and_host_decoder": True,
        "carrier_integration": True,
        "process_v2_integration": False,
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
    except (EnvelopeQualificationError, telemetry.TelemetryV4Error, OSError, subprocess.SubprocessError, ValueError) as exc:
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
