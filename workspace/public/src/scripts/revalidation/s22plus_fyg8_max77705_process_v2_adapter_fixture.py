#!/usr/bin/env python3
"""Round-trip every Max77705 retained semantic through Process-v2."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import device_action_f1_evidence_v2 as evidence
import s22plus_fyg8_max77705_telemetry as telemetry
import s22plus_fyg8_max77705_telemetry_decoder as decoder


SCHEMA = "s22plus_fyg8_max77705_process_v2_adapter_fixture_v1"
VERDICT = "PASS_MAX77705_REAL_PROCESS_V2_RETAINED_SEMANTICS_HOST_ONLY"
RUN_ID = b"max77705fixture1"


class FixtureError(ValueError):
    pass


def _binding(**changes: int) -> telemetry.BindingWitness:
    values = {
        "loader_state": telemetry.LOADER_STATES["FINIT_MODULE_RETURNED_SUCCESS"],
        "pre_exact_parent_present": 1,
        "pre_exact_parent_driver_state": telemetry.DRIVER_STATES["UNBOUND"],
        "pre_matching_unbound_parent_count": 1,
        "pre_wrong_address_compatible_parent_count": 0,
        "post_exact_parent_driver_state": telemetry.DRIVER_STATES["DIAGNOSTIC"],
        "post_diagnostic_bound_parent_count": 1,
        "post_exact_adapter_muic_0x25_client_count": 1,
        "post_foreign_0x25_client_count": 0,
    }
    values.update(changes)
    return telemetry.BindingWitness(**values)


def _eagain_bindings() -> dict[str, telemetry.BindingWitness]:
    absent = telemetry.DRIVER_STATES["ABSENT"]
    unbound = telemetry.DRIVER_STATES["UNBOUND"]
    other = telemetry.DRIVER_STATES["OTHER_DRIVER"]
    diagnostic = telemetry.DRIVER_STATES["DIAGNOSTIC"]
    success = telemetry.LOADER_STATES["FINIT_MODULE_RETURNED_SUCCESS"]
    return {
        "probe_in_progress": _binding(
            loader_state=telemetry.LOADER_STATES["FINIT_MODULE_IN_PROGRESS"],
            post_exact_parent_driver_state=unbound,
            post_diagnostic_bound_parent_count=0,
            post_exact_adapter_muic_0x25_client_count=0,
        ),
        "no_matching_parent": _binding(
            loader_state=success,
            pre_exact_parent_present=0,
            pre_exact_parent_driver_state=absent,
            pre_matching_unbound_parent_count=0,
            post_exact_parent_driver_state=absent,
            post_diagnostic_bound_parent_count=0,
            post_exact_adapter_muic_0x25_client_count=0,
        ),
        "wrong_address_compatible_parent": _binding(
            loader_state=success,
            pre_exact_parent_present=0,
            pre_exact_parent_driver_state=absent,
            pre_matching_unbound_parent_count=0,
            pre_wrong_address_compatible_parent_count=1,
            post_exact_parent_driver_state=absent,
            post_diagnostic_bound_parent_count=0,
            post_exact_adapter_muic_0x25_client_count=0,
        ),
        "exact_parent_owned_by_other_driver": _binding(
            loader_state=success,
            pre_exact_parent_driver_state=other,
            post_exact_parent_driver_state=other,
            post_diagnostic_bound_parent_count=0,
            post_exact_adapter_muic_0x25_client_count=0,
        ),
        "exact_parent_unbound_after_sync_return": _binding(
            loader_state=success,
            post_exact_parent_driver_state=unbound,
            post_diagnostic_bound_parent_count=0,
            post_exact_adapter_muic_0x25_client_count=0,
        ),
        "diagnostic_binding_ready_but_result_eagain": _binding(
            loader_state=success,
            post_exact_parent_driver_state=diagnostic,
        ),
    }


def _result(
    *, polls: tuple[bytes, bytes, bytes, bytes] | None = None
) -> telemetry.DiagnosticResult:
    return telemetry.DiagnosticResult(
        stage=10,
        rc=0,
        pmic_valid_mask=3,
        pmic_id=0x15,
        pmic_rev=0x02,
        initial_uic_valid=1,
        initial_uic=0x04,
        command_issued_mask=0x0D,
        response_seen_mask=0x0D,
        response_opcode=(0x05, 0, 0x05, 0x05),
        response_value=(0x3F, 0, 0x09, 0x09),
        poll_bytes=polls or (b"\x00\x00\x80", b"", b"\x80", b"\x80"),
        write_attempted=0,
        write_ambiguous=0,
    )


def _acceptance() -> dict[str, Any]:
    artifact = {"path": "max77705-fixture", "size": 1, "sha256": "0" * 64}
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


def _persist(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


def _round_trip(envelope: bytes) -> tuple[bytes, dict[str, Any]]:
    record = telemetry.encode_carrier_record(envelope, run_id=RUN_ID)
    value = _persist(evidence.classify_e1_latest_stage(record, _acceptance()))
    if (
        value.get("foreign_count") != 0
        or value.get("exact_record_count") != 1
        or len(value.get("records", ())) != 1
        or value["records"][0].get("max77705") is None
        or value.get("telemetry_count", 0)
        + value.get("contradiction_count", 0)
        != 1
    ):
        raise FixtureError("Max77705 Process-v2 record accounting differs")
    return record, value


def audit() -> dict[str, Any]:
    selected = evidence._latest_stage_observation_decoder(  # noqa: SLF001
        decoder.PARENT_SOURCE_CONTRACT_ID,
        decoder.PROFILE,
        decoder.OVERLAY_CONTRACT_ID,
    )
    if selected is not decoder:
        raise FixtureError("Max77705 Process-v2 decoder selection differs")

    eagain = _eagain_bindings()
    eagain_receipts: dict[str, str] = {}
    for row, binding in eagain.items():
        record, classified = _round_trip(
            telemetry.encode_envelope(
                binding=binding,
                terminal_bucket=telemetry.eagain_terminal_bucket(row),
            )
        )
        decoded = classified.get("records", [{}])[0].get("max77705", {})
        if decoded.get("eagain_row") != row:
            raise FixtureError(f"Max77705 EAGAIN adapter row differs: {row}")
        eagain_receipts[row] = hashlib.sha256(record).hexdigest()
    if len(set(eagain_receipts.values())) != len(eagain):
        raise FixtureError("Max77705 observable EAGAIN retained vectors collide")

    representative_binding_by_bucket = {
        telemetry.eagain_terminal_bucket(row): binding
        for row, binding in eagain.items()
    }
    terminal_receipts: dict[str, str] = {}
    for bucket in telemetry.TERMINAL_BUCKET_KEYS:
        if bucket == "result_payload_unrepresentable":
            envelope = telemetry.encode_envelope(
                binding=_binding(),
                mux_class=telemetry.MUX_DEVICE_CLASSES[0],
                result=_result(
                    polls=tuple(bytes(range(100)) for _ in range(4))
                ),
            )
        else:
            envelope = telemetry.encode_envelope(
                binding=representative_binding_by_bucket.get(bucket, _binding()),
                terminal_bucket=bucket,
                result=(
                    _result()
                    if bucket
                    in {"probe_terminal_failure", "matching_parent_identity_rejected"}
                    else None
                ),
            )
        record, classified = _round_trip(envelope)
        decoded = classified.get("records", [{}])[0].get("max77705", {})
        if (
            decoded.get("terminal_bucket") != bucket
            or classified.get("accepted") is not False
        ):
            raise FixtureError(f"Max77705 terminal adapter row differs: {bucket}")
        terminal_receipts[bucket] = hashlib.sha256(record).hexdigest()
    if len(set(terminal_receipts.values())) != len(terminal_receipts):
        raise FixtureError("Max77705 terminal retained vectors collide")

    mux_receipts: dict[str, str] = {}
    for name in telemetry.MUX_DEVICE_CLASSES:
        record, classified = _round_trip(
            telemetry.encode_envelope(
                binding=_binding(), mux_class=name, result=_result()
            )
        )
        decoded = classified.get("records", [{}])[0].get("max77705", {})
        if (
            decoded.get("mux_class") != name
            or decoded.get("poll_lossless") is not True
            or classified.get("accepted") is not True
        ):
            raise FixtureError(f"Max77705 MUX adapter row differs: {name}")
        mux_receipts[name] = hashlib.sha256(record).hexdigest()
    if len(set(mux_receipts.values())) != len(mux_receipts):
        raise FixtureError("Max77705 MUX retained vectors collide")

    try:
        telemetry.encode_envelope(
            binding=_binding(), terminal_bucket="claim_busy_after_sync_return"
        )
    except telemetry.TelemetryError:
        negative_rejected = True
    else:
        negative_rejected = False
    if not negative_rejected:
        raise FixtureError("Max77705 claim-busy negative invariant gained a preimage")

    unknown = _acceptance()
    unknown["userspace_overlay_contract_id"] += "-unknown"
    try:
        evidence.classify_e1_latest_stage(
            telemetry.encode_carrier_record(
                telemetry.encode_envelope(
                    binding=_binding(),
                    mux_class=telemetry.MUX_DEVICE_CLASSES[0],
                    result=_result(),
                ),
                run_id=RUN_ID,
            ),
            unknown,
        )
    except evidence.EvidenceError:
        unknown_rejected = True
    else:
        unknown_rejected = False
    if not unknown_rejected:
        raise FixtureError("unknown Max77705 overlay was accepted")

    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "decoder_id": decoder.DECODER_ID,
        "decoder_policy_id": decoder.POLICY_ID,
        "observable_eagain_rows": len(eagain_receipts),
        "terminal_bucket_preimages": len(terminal_receipts),
        "mux_class_preimages": len(mux_receipts),
        "claim_busy_decoder_preimage_empty": negative_rejected,
        "unknown_overlay_rejected": unknown_rejected,
        "real_process_v2_adapter_round_trip": True,
        "persistence_round_trip": True,
        "verified": True,
    }


def main() -> int:
    try:
        result = audit()
    except (FixtureError, evidence.EvidenceError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
