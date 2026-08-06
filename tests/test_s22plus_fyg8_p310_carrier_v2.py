#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p232_e1_latest_stage_design as v1  # noqa: E402
import s22plus_fyg8_p308_telemetry_spec as spec  # noqa: E402
import s22plus_fyg8_p310_carrier_model as model  # noqa: E402


def _run_id() -> bytes:
    return model.model_run_id()


def _first_request(run_id: bytes, **kwargs) -> bytes:
    position = spec.POSITIONS[0]
    return model.encode_request(
        spec.PROFILE,
        position.stage,
        run_id=run_id,
        item_index=position.item_index,
        **kwargs,
    )


def test_carrier_v2_contract_and_boundary_matrix() -> None:
    result = model.validate()
    assert result["verified"] is True
    assert result["record_size"] == 192
    assert result["header_size"] == 32
    assert result["slot_size"] == 80
    assert result["raw_excerpt_max"] == 64


def test_v2_request_compatibility_and_v3_payload() -> None:
    run_id = _run_id()
    record = model.initialize_record(spec.PROFILE, run_id)
    request_v2 = _first_request(run_id)
    assert len(request_v2) == 32
    assert model.decode_request(request_v2).version == 2
    request_v3 = _first_request(
        run_id,
        payload_kind=model.PAYLOAD_RAW_EXCERPT,
        payload=b"bounded raw line",
        version=3,
    )
    assert len(request_v3) == 100
    advanced = model.apply_request(record, request_v3)
    assert model.decode_record(advanced)["active"]["payload"] == b"bounded raw line"


def test_embedded_evidence_families_do_not_self_increment_foreign_count() -> None:
    run_id = _run_id()
    excerpt = b"|".join(model.ALL_FAMILIES)
    assert len(excerpt) <= model.REQUEST_PAYLOAD_SIZE
    record = model.apply_request(
        model.initialize_record(spec.PROFILE, run_id),
        _first_request(
            run_id,
            payload_kind=model.PAYLOAD_RAW_EXCERPT,
            payload=excerpt,
            version=3,
        ),
    )
    result = model.classify_observation(
        b"prefix" + record + b"suffix",
        expected_profile=spec.PROFILE,
        expected_run_id=run_id,
    )
    assert result["embedded_family_count"] >= len(model.ALL_FAMILIES)
    assert result["foreign_count"] == 0
    assert result["integrity_issue"] is False


def test_invalid_outer_record_does_not_shield_nested_family() -> None:
    run_id = _run_id()
    record = bytearray(model.initialize_record(spec.PROFILE, run_id))
    record[28] ^= 0x80
    record[48 : 48 + len(model.LEGACY_FAMILIES[0])] = model.LEGACY_FAMILIES[0]
    result = model.classify_observation(
        bytes(record),
        expected_profile=spec.PROFILE,
        expected_run_id=run_id,
    )
    assert result["integrity_issue"] is True
    assert "foreign-or-malformed-v2-long-record" in result["integrity_issues"]
    assert "legacy-or-foreign-evidence-family" in result["integrity_issues"]


def test_torn_second_update_falls_back_to_first_committed_generation() -> None:
    run_id = _run_id()
    record = model.apply_request(
        model.initialize_record(spec.PROFILE, run_id),
        _first_request(run_id),
    )
    second = spec.POSITIONS[1]
    request = model.encode_request(
        spec.PROFILE,
        second.stage,
        run_id=run_id,
        item_index=second.item_index,
    )
    for phase in ("invalidate", "body"):
        decoded = model.decode_record(model.apply_request(record, request, stop_after=phase))
        assert decoded["active"]["generation"] == 1
        assert decoded["fallback_used"] is True


def test_header_crc_is_independent_from_slot_crc() -> None:
    run_id = _run_id()
    record = bytearray(model.initialize_record(spec.PROFILE, run_id))
    record[12] ^= 1
    with pytest.raises(model.DesignError, match="header CRC"):
        model.decode_record(bytes(record))


def test_historical_v1_decoder_remains_usable_but_v2_rejects_v1() -> None:
    run_id = v1.model_run_id("E2")
    old = v1.initialize_record("E2", run_id)
    assert v1.decode_record(old, expected_profile="E2")["active"]["generation"] == 0
    with pytest.raises(model.DesignError):
        model.decode_record(old)


def test_only_bounded_precursor_region_changes() -> None:
    run_id = _run_id()
    for idx, expected in ((24, model.UNSAT_SIZE), (191, model.UNSAT_SIZE), (192, model.LONG_RECORD_SIZE), (513, model.LONG_RECORD_SIZE)):
        row = model.simulate_initial_visibility(spec.PROFILE, run_id, idx=idx)
        assert row["changed_bytes"] == expected
