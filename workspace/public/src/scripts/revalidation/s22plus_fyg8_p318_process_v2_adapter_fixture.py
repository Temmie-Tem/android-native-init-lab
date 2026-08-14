#!/usr/bin/env python3
"""Round-trip P3.18 actual-C envelope-v4 rows through Process-v2."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import device_action_f1_evidence_v2 as evidence
import s22plus_fyg8_p318_max77705_envelope_qualification as boundary
import s22plus_fyg8_p318_max77705_preimage_fixture as native_fixture
import s22plus_fyg8_p318_max77705_telemetry as telemetry
import s22plus_fyg8_p318_max77705_telemetry_decoder as decoder
import s22plus_fyg8_p318_topology_receipt as topology


SCHEMA = "s22plus_fyg8_p318_process_v2_adapter_fixture_v1"
VERDICT = "PASS_P318_REAL_PROCESS_V2_ENVELOPE_V4_HOST_ONLY"
RUN_ID = b"p318max77705fix1"


class FixtureError(ValueError):
    pass


def _acceptance() -> dict[str, Any]:
    artifact = {"path": "p318-max77705-fixture", "size": 1, "sha256": "0" * 64}
    return {
        "kind": evidence.E1_LATEST_STAGE_KIND,
        "source": evidence.CHECKPOINT_SOURCE,
        "decoder": decoder.DECODER_ID,
        "policy_id": decoder.POLICY_ID,
        "profile": decoder.PROFILE,
        "run_id": RUN_ID.hex(),
        "source_contract_id": decoder.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": decoder.OVERLAY_CONTRACT_ID,
        "long_family_hex": decoder.model.LONG_FAMILY.hex(),
        "unsat_family_hex": decoder.model.UNSAT_FAMILY.hex(),
        "terminal_stage": evidence._latest_stage_terminal(  # noqa: SLF001
            decoder, decoder.PROFILE
        ),
        "minimum_success_count": 1,
        "clean_baseline_required": True,
        "contract": {
            "candidate_static": artifact,
            "run_manifest": artifact,
            "static_check": artifact,
        },
    }


def _round_trip(envelope: bytes) -> tuple[bytes, dict[str, Any]]:
    record = telemetry.encode_carrier_record(envelope, run_id=RUN_ID)
    value = json.loads(json.dumps(
        evidence.classify_e1_latest_stage(record, _acceptance()),
        sort_keys=True,
        allow_nan=False,
    ))
    if (
        value.get("foreign_count") != 0
        or value.get("exact_record_count") != 1
        or len(value.get("records", ())) != 1
        or value["records"][0].get("max77705") is None
        or value.get("telemetry_count", 0)
        + value.get("contradiction_count", 0) != 1
    ):
        raise FixtureError("P3.18 Process-v2 record accounting differs")
    return record, value


def _boundary_rows() -> list[tuple[str, bytes]]:
    lossless = (bytes(range(1, 43)) + b"\x80", b"\x81", b"\x82", b"\x83")
    overflow = (bytes(range(1, 44)) + b"\x80", b"\x81", b"\x82", b"\x83")
    cases = (
        ("lossless47_event_written", lossless, 1, "written", "none", 49),
        ("lossless47_no_event_eagain", lossless, 0, "eagain_timeout", "eagain_deadline", 0),
        ("lossless47_event_epipe", lossless, 3, "failure", "epipe", 0),
        ("lossless47_event_enodev", lossless, 2, "failure", "enodev", 0),
        ("overflow48_event_partial", overflow, 1, "partial", "eintr_deadline", 48),
    )
    return [
        (
            name,
            boundary._python_envelope(  # noqa: SLF001
                boundary._result(polls),  # noqa: SLF001
                boundary._latch(kind),  # noqa: SLF001
                boundary._banner(outcome, error, count),  # noqa: SLF001
            ),
        )
        for name, polls, kind, outcome, error, count in cases
    ]


def _assert_correlation(
    classified: dict[str, Any], *, relationship: str, expected: str, accepted: bool
) -> None:
    identity = {
        "vendor": "04e8", "product_id": "6861", "product": "fixture",
        "manufacturer": "fixture", "serial": "S22E3fixture",
        "driver": "cdc_acm", "interface": "00", "tty_name": "ttyACM0",
        "endpoint_node": "/dev/ttyACM0",
    }
    start_endpoint = topology._endpoint_row(  # noqa: SLF001
        mode="download",
        identity={
            "vendor": "04e8", "product_id": "685d", "product": "ODIN",
            "manufacturer": "SAMSUNG", "serial": "", "driver": "",
            "interface": "", "tty_name": "",
            "endpoint_node": "/dev/bus/usb/002/003",
        },
        topology="2-1.3", controller_path="/controller0",
        usb_device_path="/controller0/usb2/2-1/2-1.3",
    )
    candidate_endpoint = topology._endpoint_row(  # noqa: SLF001
        mode="candidate", identity=identity,
        topology="2-1.3" if relationship == "same" else "3-1.3",
        controller_path="/controller0" if relationship == "same" else "/controller1",
        usb_device_path=(
            "/controller0/usb2/2-1/2-1.3"
            if relationship == "same"
            else "/controller1/usb3/3-1/3-1.3"
        ),
    )
    endpoints = [] if relationship == "absent" else [candidate_endpoint]
    raw = topology.raw_snapshot(
        phase="candidate_end", capture_complete=True, endpoints=endpoints
    )
    device_rows = [
        row for row in classified.get("records", ())
        if isinstance(row, dict) and isinstance(row.get("max77705"), dict)
    ]
    causal_ready = (
        len(device_rows) == 1
        and device_rows[0]["max77705"].get(
            "diagnostic_causal_prerequisites_ready"
        )
        is True
    )
    phase_record = topology.build_phase_record(
        raw,
        phase="candidate_end",
        target_identity={
            "vendor": "04e8", "product_id": "6861", "serial": "S22E3fixture",
            "driver": "cdc_acm", "interface": "00",
        },
        binding_id_sha256="a" * 64,
        comparison_binding_id_sha256="a" * 64,
        authority_state="candidate_approved_exact",
        causal_terminal_ready=causal_ready,
        start_path=topology._path_tuple(start_endpoint),  # noqa: SLF001
        host_observer={
            "classification": (
                "read-timeout" if relationship == "same" else "endpoint-timeout"
            ),
            "endpoint_identity_sha256": (
                candidate_endpoint["endpoint_identity_sha256"]
                if relationship == "same"
                else None
            ),
            "receipt_sha256": "b" * 64,
            "topology_sha256": start_endpoint["topology_sha256"],
            "bounded": True,
            "valid_receipt": True,
            "download_endpoint_absent": True,
        },
    )
    value = evidence.correlate_p318_candidate_topology(classified, phase_record)
    if value.get("classification") != expected or value.get("accepted") is not accepted:
        raise FixtureError(
            f"P3.18 host correlation differs: {relationship}/{expected}"
        )


def audit() -> dict[str, Any]:
    selected = evidence._latest_stage_observation_decoder(  # noqa: SLF001
        decoder.PARENT_SOURCE_CONTRACT_ID,
        decoder.PROFILE,
        decoder.OVERLAY_CONTRACT_ID,
    )
    if selected is not decoder:
        raise FixtureError("P3.18 Process-v2 decoder selection differs")

    native = native_fixture.audit()
    native_receipts = native.get("receipts")
    if not isinstance(native_receipts, dict) or len(native_receipts) != 121:
        raise FixtureError("P3.18 native preimage receipt map differs")
    adapter_envelopes: dict[str, str] = {}
    retained: dict[str, str] = {}
    pending_mux = 0
    terminal_rows = 0
    observer_rows = 0
    mux_rows = 0
    overflow_rows = 0

    for row in native_fixture._rows()[0]:  # noqa: SLF001
        label = str(row["label"])
        kwargs = {key: value for key, value in row.items() if key != "label"}
        envelope = telemetry.encode_envelope(**kwargs)
        envelope_sha = hashlib.sha256(envelope).hexdigest()
        if native_receipts.get(label) != envelope_sha:
            raise FixtureError(f"P3.18 actual-C and adapter input differ: {label}")
        adapter_envelopes[label] = envelope_sha
        record, classified = _round_trip(envelope)
        decoded = classified["records"][0]["max77705"]
        if classified.get("accepted") is not False:
            raise FixtureError(f"P3.18 row accepted before host receipt: {label}")
        if label.startswith("terminal:") or label.startswith("eagain:"):
            terminal_rows += 1
            if decoded.get("terminal_bucket") != kwargs["terminal_bucket"]:
                raise FixtureError(f"P3.18 terminal row differs: {label}")
        elif label.startswith("observer:"):
            observer_rows += 1
            if (
                decoded.get("observer_site") != kwargs["observer_site"]
                or decoded.get("observer_error_class")
                != kwargs["observer_error_class"]
            ):
                raise FixtureError(f"P3.18 observer row differs: {label}")
        elif label.startswith("mux:"):
            mux_rows += 1
            if decoded.get("mux_class") != kwargs["mux_class"]:
                raise FixtureError(f"P3.18 MUX row differs: {label}")
            if decoded.get("causal_pending_complete_host_receipt") is True:
                pending_mux += 1
                _assert_correlation(
                    classified,
                    relationship="same",
                    expected="RETAIN_EXPERIMENT_TERMINAL",
                    accepted=True,
                )
                _assert_correlation(
                    classified,
                    relationship="absent",
                    expected="DEVICE_RESULT_DWC3_HOST_EVENT_NO_ENDPOINT",
                    accepted=True,
                )
                _assert_correlation(
                    classified,
                    relationship="drift",
                    expected="NO_PROOF_EXPERIMENT_PRECONDITION",
                    accepted=False,
                )
        else:
            overflow_rows += 1
            if decoded.get("terminal_bucket") != "result_payload_unrepresentable":
                raise FixtureError("P3.18 overflow semantic differs")
        retained[label] = hashlib.sha256(record).hexdigest()

    if adapter_envelopes != native_receipts:
        raise FixtureError("P3.18 native preimage reverse map is incomplete")

    boundary_audit = boundary.audit()
    boundary_receipts = {
        str(row["name"]): str(row["sha256"])
        for row in boundary_audit["actual_c_python_byte_identity_cases"]
    }
    boundary_retained: dict[str, str] = {}
    for name, envelope in _boundary_rows():
        if hashlib.sha256(envelope).hexdigest() != boundary_receipts.get(name):
            raise FixtureError(f"P3.18 boundary actual-C bytes differ: {name}")
        record, classified = _round_trip(envelope)
        decoded = classified["records"][0]["max77705"]
        if name == "lossless47_no_event_eagain":
            _assert_correlation(
                classified,
                relationship="absent",
                expected="DEVICE_RESULT_HOST_SILENT",
                accepted=True,
            )
            _assert_correlation(
                classified,
                relationship="same",
                expected="NO_PROOF_OBSERVER",
                accepted=False,
            )
        elif name == "overflow48_event_partial":
            if decoded.get("payload_overflow") is not True:
                raise FixtureError("P3.18 48-byte overflow disappeared")
        else:
            _assert_correlation(
                classified,
                relationship="same",
                expected="RETAIN_EXPERIMENT_TERMINAL",
                accepted=True,
            )
        boundary_retained[name] = hashlib.sha256(record).hexdigest()

    all_retained = {**retained, **{
        f"boundary:{name}": value for name, value in boundary_retained.items()
    }}
    if len(all_retained) != 126 or len(set(all_retained.values())) != 126:
        raise FixtureError("P3.18 retained vectors collide")

    claim_envelope = telemetry.encode_envelope(
        binding=native_fixture.p317_vectors._claim_busy_binding(),  # noqa: SLF001
        exec_witness=native_fixture.p317_vectors._exec(),  # noqa: SLF001
        banner=boundary._banner("not_attempted", "none", 0),  # noqa: SLF001
        terminal_bucket="synchronous_probe_or_publication_contradiction",
        observer_site="result-policy",
        observer_error_class="io-format",
    )
    if (
        hashlib.sha256(claim_envelope).hexdigest()
        != native["claim_busy_negative_envelope_sha256"]
    ):
        raise FixtureError("P3.18 claim-busy actual-C bytes differ")
    _claim_record, claim = _round_trip(claim_envelope)
    claim_decoded = claim["records"][0]["max77705"]
    if claim_decoded.get("eagain_row") is not None or claim.get("accepted") is not False:
        raise FixtureError("P3.18 claim-busy gained a decoder preimage")

    unknown = _acceptance()
    unknown["userspace_overlay_contract_id"] += "-unknown"
    try:
        evidence.classify_e1_latest_stage(
            telemetry.encode_carrier_record(_boundary_rows()[0][1], run_id=RUN_ID),
            unknown,
        )
    except evidence.EvidenceError:
        unknown_rejected = True
    else:
        unknown_rejected = False
    if not unknown_rejected:
        raise FixtureError("unknown P3.18 overlay was accepted")

    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "actual_c_base_preimages": len(adapter_envelopes),
        "actual_c_boundary_preimages": len(boundary_retained),
        "retained_vector_preimages": len(all_retained),
        "terminal_and_eagain_rows": terminal_rows,
        "observer_site_error_rows": observer_rows,
        "mux_rows": mux_rows,
        "pending_mux_rows": pending_mux,
        "overflow_rows": overflow_rows,
        "observable_eagain_rows": native["observable_eagain_rows"],
        "native_envelope_adapter_input_byte_identity": True,
        "native_envelope_reverse_map_complete": True,
        "retained_vector_cross_group_unique": True,
        "event_present_same_accepted": True,
        "event_present_absent_distinct": True,
        "no_event_absent_host_silent_accepted": True,
        "no_event_present_rejected": True,
        "drift_never_accepted": True,
        "claim_busy_decoder_preimage_empty": True,
        "unknown_overlay_rejected": True,
        "verified": True,
    }


def main() -> int:
    try:
        value = audit()
    except (FixtureError, evidence.EvidenceError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
