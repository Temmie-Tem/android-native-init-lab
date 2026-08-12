#!/usr/bin/env python3
"""Round-trip every P3.17 retained semantic through the real Process-v2 path."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import device_action_f1_evidence_v2 as evidence
import s22plus_fyg8_max77705_process_v2_adapter_fixture as vectors
import s22plus_fyg8_max77705_telemetry as inherited
import s22plus_fyg8_p317_max77705_envelope_fixture as envelope_vectors
import s22plus_fyg8_p317_max77705_telemetry as telemetry
import s22plus_fyg8_p317_max77705_telemetry_decoder as decoder


SCHEMA = "s22plus_fyg8_p317_process_v2_adapter_fixture_v1"
VERDICT = "PASS_P317_REAL_PROCESS_V2_RETAINED_SEMANTICS_HOST_ONLY"
RUN_ID = b"p317max77705fix1"


class FixtureError(ValueError):
    pass


def _acceptance() -> dict[str, Any]:
    artifact = {"path": "p317-max77705-fixture", "size": 1, "sha256": "0" * 64}
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
    value = json.loads(
        json.dumps(
            evidence.classify_e1_latest_stage(record, _acceptance()),
            sort_keys=True,
            allow_nan=False,
        )
    )
    if (
        value.get("foreign_count") != 0
        or value.get("exact_record_count") != 1
        or len(value.get("records", ())) != 1
        or value["records"][0].get("max77705") is None
        or value.get("telemetry_count", 0) + value.get("contradiction_count", 0) != 1
    ):
        raise FixtureError("P3.17 Process-v2 record accounting differs")
    return record, value


def _expected_exec_groups(site: str) -> set[str]:
    return {
        "override-prepare": set(),
        "provider-pre": set(),
        "cmdline": {"gadget", "pre"},
        "substrate-verify": {"policy", "gadget", "pre"},
        "pre-topology": {"policy", "gadget", "pre"},
        "provider-post": {"policy", "gadget", "pre"},
        "waiting": {"policy", "gadget", "pre", "post"},
        "supplier": {"policy", "gadget", "pre", "post", "waiting"},
        "late-loader": {"policy", "gadget", "pre", "post", "waiting", "supplier"},
        "post-topology": {"policy", "gadget", "pre", "post", "waiting", "supplier"},
        "result-policy": {"policy", "gadget", "pre", "post", "waiting", "supplier"},
        "result-read": {"policy", "gadget", "pre", "post", "waiting", "supplier"},
    }[site]


def audit() -> dict[str, Any]:
    selected = evidence._latest_stage_observation_decoder(  # noqa: SLF001
        decoder.PARENT_SOURCE_CONTRACT_ID,
        decoder.PROFILE,
        decoder.OVERLAY_CONTRACT_ID,
    )
    if selected is not decoder:
        raise FixtureError("P3.17 Process-v2 decoder selection differs")

    observer_receipts: dict[str, str] = {}
    for site in tuple(telemetry.OBSERVER_SITES)[1:]:
        for error_class in tuple(telemetry.OBSERVER_ERROR_CLASSES)[1:]:
            record, classified = _round_trip(
                telemetry.encode_envelope(
                    binding=envelope_vectors._observer_binding(site),  # noqa: SLF001
                    exec_witness=envelope_vectors._observer_exec(site),  # noqa: SLF001
                    terminal_bucket="synchronous_probe_or_publication_contradiction",
                    observer_site=site,
                    observer_error_class=error_class,
                )
            )
            decoded = classified["records"][0]["max77705"]
            authority = {
                name
                for name, present in decoded["executability_authority"].items()
                if present
            }
            if (
                decoded.get("observer_site") != site
                or decoded.get("observer_error_class") != error_class
                or authority != _expected_exec_groups(site)
                or classified.get("accepted") is not False
            ):
                raise FixtureError(f"P3.17 observer row differs: {site}/{error_class}")
            observer_receipts[f"{site}:{error_class}"] = hashlib.sha256(record).hexdigest()
    if len(set(observer_receipts.values())) != len(observer_receipts):
        raise FixtureError("P3.17 observer retained vectors collide")

    representative = {
        inherited.eagain_terminal_bucket(name): binding
        for name, binding in vectors._eagain_bindings().items()  # noqa: SLF001
    }
    terminal_receipts: dict[str, str] = {}
    precondition_rows = 0
    for bucket in telemetry.TERMINAL_BUCKET_KEYS:
        result = None
        binding = representative.get(bucket, vectors._binding())  # noqa: SLF001
        if bucket == "probe_terminal_failure":
            result = vectors._failure_result(4)  # noqa: SLF001
        elif bucket == "matching_parent_identity_rejected":
            result = vectors._failure_result(2, rc=-19)  # noqa: SLF001
        if bucket == "result_payload_unrepresentable":
            envelope = telemetry.encode_envelope(
                binding=vectors._binding(),  # noqa: SLF001
                exec_witness=envelope_vectors._exec(),  # noqa: SLF001
                mux_class=telemetry.MUX_DEVICE_CLASSES[0],
                result=vectors._result(  # noqa: SLF001
                    polls=tuple(vectors._uncompressible_poll() for _ in range(4))  # noqa: SLF001
                ),
            )
        else:
            envelope = telemetry.encode_envelope(
                binding=binding,
                exec_witness=envelope_vectors._exec_for_terminal(bucket),  # noqa: SLF001
                terminal_bucket=bucket,
                result=result,
            )
        record, classified = _round_trip(envelope)
        decoded = classified["records"][0]["max77705"]
        if decoded.get("terminal_bucket") != bucket or classified.get("accepted") is not False:
            raise FixtureError(f"P3.17 terminal row differs: {bucket}")
        if bucket in {
            "fw_devlink_policy_precondition",
            "provider_preclient_precondition",
            "provider_postclient_precondition",
            "supplier_link_precondition",
            "waiting_for_supplier_precondition",
        }:
            if not str(decoded.get("terminal_classification", "")).startswith(
                "NO_PROOF_EXPERIMENT_PRECONDITION_"
            ):
                raise FixtureError(f"P3.17 precondition class differs: {bucket}")
            precondition_rows += 1
        terminal_receipts[bucket] = hashlib.sha256(record).hexdigest()
    if len(set(terminal_receipts.values())) != len(terminal_receipts):
        raise FixtureError("P3.17 terminal retained vectors collide")

    mux_receipts: dict[str, str] = {}
    for mux_class in telemetry.MUX_DEVICE_CLASSES:
        record, classified = _round_trip(
            telemetry.encode_envelope(
                binding=vectors._binding(),  # noqa: SLF001
                exec_witness=envelope_vectors._exec(),  # noqa: SLF001
                mux_class=mux_class,
                result=vectors._result_for_mux(mux_class),  # noqa: SLF001
            )
        )
        decoded = classified["records"][0]["max77705"]
        if (
            decoded.get("mux_class") != mux_class
            or decoded.get("causal_result_allowed") is not True
            or decoded.get("executability", {}).get("causal_ready") is not True
            or classified.get("accepted") is not True
        ):
            raise FixtureError(f"P3.17 MUX row differs: {mux_class}")
        mux_receipts[mux_class] = hashlib.sha256(record).hexdigest()
    if len(set(mux_receipts.values())) != len(mux_receipts):
        raise FixtureError("P3.17 MUX retained vectors collide")

    try:
        telemetry.encode_envelope(
            binding=vectors._binding(),  # noqa: SLF001
            exec_witness=envelope_vectors._exec(  # noqa: SLF001
                link_waiting=telemetry.LINK_VALID
                | telemetry.WAITING_STATES["FILE_ABSENT"]
                | (
                    telemetry.SUPPLIER_STATES["EXACT_ONE"]
                    << telemetry.SUPPLIER_SHIFT
                )
            ),
            mux_class=telemetry.MUX_DEVICE_CLASSES[0],
            result=vectors._result_for_mux(telemetry.MUX_DEVICE_CLASSES[0]),  # noqa: SLF001
        )
    except telemetry.TelemetryError:
        noncausal_mux_rejected = True
    else:
        noncausal_mux_rejected = False
    if not noncausal_mux_rejected:
        raise FixtureError("P3.17 noncausal MUX row gained a preimage")

    unknown = _acceptance()
    unknown["userspace_overlay_contract_id"] += "-unknown"
    try:
        evidence.classify_e1_latest_stage(
            telemetry.encode_carrier_record(
                telemetry.encode_envelope(
                    binding=vectors._binding(),  # noqa: SLF001
                    exec_witness=envelope_vectors._exec(),  # noqa: SLF001
                    mux_class=telemetry.MUX_DEVICE_CLASSES[0],
                    result=vectors._result_for_mux(telemetry.MUX_DEVICE_CLASSES[0]),  # noqa: SLF001
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
        raise FixtureError("unknown P3.17 overlay was accepted")

    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "decoder_id": decoder.DECODER_ID,
        "decoder_policy_id": decoder.POLICY_ID,
        "observer_site_error_preimages": len(observer_receipts),
        "observer_site_error_cross_product_complete": True,
        "terminal_bucket_preimages": len(terminal_receipts),
        "precondition_terminal_preimages": precondition_rows,
        "mux_class_preimages": len(mux_receipts),
        "noncausal_mux_preimage_empty": noncausal_mux_rejected,
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
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
