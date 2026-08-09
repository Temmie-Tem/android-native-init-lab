#!/usr/bin/env python3
"""Localize P3.13 stop multiplicity and test incident Carrier positions."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import s22plus_fyg8_p308_cross_gate_audit as support
import s22plus_fyg8_p313_cross_gate_audit as cross_gate
import s22plus_fyg8_p313_postlive_carrier_model as carrier
import s22plus_fyg8_p313_postlive_decoder as decoder
import s22plus_fyg8_p313_runtime_fixture as runtime_fixture
import s22plus_fyg8_p313_successor_hazard_contract as successor
import s22plus_fyg8_p313_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p313_stop_multiplicity_audit_v1"
VERDICT = "PASS_P313_STOP_MULTIPLICITY_SOURCE_FORCED_TRIGGER_HOST_ONLY"
AuditError = support.AuditError

KERNEL_ROOT = Path(
    "workspace/private/work/p310-v6-dev/workspace/private/work/"
    "s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform"
)
MATERIALIZED_ROOT = Path(
    "workspace/private/outputs/s22plus_fyg8_p313/intent/materialized-sources"
)


def _definition(source: bytes, marker: bytes, *, last: bool = False) -> bytes:
    return support._definition(source, marker, last=last)  # noqa: SLF001


def _require_order(source: bytes, label: str, *needles: bytes) -> None:
    cursor = 0
    for needle in needles:
        found = source.find(needle, cursor)
        if found < 0:
            raise AuditError(f"{label} source order differs at {needle!r}")
        cursor = found + len(needle)


def _kernel_source_contract(root: Path) -> dict[str, Any]:
    kernel = root / KERNEL_ROOT / "msm-kernel/drivers/usb"
    wrapper = (kernel / "dwc3/dwc3-msm-core.c").read_bytes()
    core = (kernel / "dwc3/core.c").read_bytes()
    phy = (kernel / "phy/phy-msm-snps-hs.c").read_bytes()

    probe = _definition(wrapper, b"static int dwc3_msm_probe(", last=True)
    core_get_phy = _definition(
        core, b"static int dwc3_core_get_phy(", last=True
    )
    _require_order(
        probe,
        "wrapper-child-phy",
        b"dwc3_node = of_get_next_available_child(node, NULL);",
        b'phy_node = of_parse_phandle(dwc3_node, "usb-phy", 0);',
        b"mdwc->hs_phy = devm_usb_get_phy_by_node",
    )
    _require_order(
        core_get_phy,
        "core-child-phy",
        b'dwc->usb2_phy = devm_usb_get_phy_by_phandle(dev, "usb-phy", 0);',
    )

    core_exit = _definition(core, b"static void dwc3_core_exit(", last=True)
    suspend_common = _definition(
        core, b"static int dwc3_suspend_common(", last=True
    )
    start_peripheral = _definition(
        wrapper, b"static int dwc3_otg_start_peripheral(", last=True
    )
    state_machine = _definition(
        wrapper, b"static void dwc3_otg_sm_work(", last=True
    )
    parent_suspend = _definition(
        wrapper, b"static int dwc3_msm_suspend(", last=True
    )
    phy_suspend = _definition(
        phy, b"static int msm_hsphy_set_suspend(", last=True
    )

    _require_order(
        suspend_common,
        "child-runtime-suspend",
        b"dwc3_gadget_suspend(dwc);",
        b"dwc3_core_exit(dwc);",
    )
    _require_order(
        core_exit,
        "child-core-exit",
        b"usb_phy_set_suspend(dwc->usb2_phy, 1);",
    )
    _require_order(
        start_peripheral,
        "stop-child-pm",
        b"ret = pm_runtime_put_sync(&mdwc->dwc3->dev);",
        b"set_bit(WAIT_FOR_LPM, &mdwc->inputs);",
    )
    _require_order(
        state_machine,
        "stop-parent-pm",
        b"dwc3_otg_start_peripheral(mdwc, 0);",
        b"pm_runtime_put_sync_suspend(mdwc->dev);",
    )
    _require_order(
        parent_suspend,
        "parent-runtime-suspend",
        b"usb_phy_set_suspend(mdwc->hs_phy, 1);",
    )
    _require_order(
        phy_suspend,
        "phy-idempotent-suspend",
        b"if (phy->suspended && suspend)",
        b"return 0;",
        b"msm_hsphy_enable_power(phy, false);",
        b"phy->suspended = true;",
    )

    core_init = _definition(core, b"static int dwc3_core_init(", last=True)
    parent_resume = _definition(
        wrapper, b"static int dwc3_msm_resume(", last=True
    )
    _require_order(
        core_init,
        "child-runtime-resume",
        b"usb_phy_init(dwc->usb2_phy);",
        b"usb_phy_set_suspend(dwc->usb2_phy, 0);",
    )
    _require_order(
        parent_resume,
        "parent-runtime-resume",
        b"usb_phy_set_suspend(mdwc->hs_phy, 0);",
    )

    return {
        "shared_hs_phy_from_child_usb_phy_phandle_zero": True,
        "stop_suspend_callers": ["dwc3_core_exit", "dwc3_msm_suspend"],
        "second_suspend_is_idempotent_early_return": True,
        "restart_suspend_callers": ["dwc3_msm_resume", "dwc3_core_init"],
        "source_forced_stop_pair": "phy_suspend_off",
        "source_forced_stop_pair_count": 2,
        "source_forced_restart_pair": "phy_suspend_on",
        "source_forced_restart_pair_count": 2,
    }


def _stop_fixture_tu(runtime: bytes, descriptor: bytes) -> bytes:
    source = runtime_fixture._cycle_tu(runtime, descriptor)  # noqa: SLF001
    prefix = source[: source.rfind(b"int main(void) {")]
    return prefix + br'''
int main(void) {
    (void)p313_cycle_profile_relations;
    (void)fill_clean;
    (void)append_bounded_drift;
    (void)profile_from_result;
    struct p282_trace_control control = {0};
    struct p313_cycle_result result = {0};
    memset(fixture, 0, sizeof(fixture));
    fixture_count = 0U;
    long pid = 9;

    /* One worker stops the child, then the parent. */
    push(14U, pid);
    entry_on(0U, pid, 0);
    push(2U, pid);
    entry_suspend(6U, pid, 1);
    entry_on(8U, pid, 0);
    entry_on(19U, pid, 0);
    returned(20U, pid, 0);
    returned(9U, pid, 0);
    returned(7U, pid, 0);
    returned(3U, pid, 0);
    returned(1U, pid, 0);
    entry_suspend(6U, pid, 1);
    returned(7U, pid, 0);
    returned(15U, pid, 0);

    long rc = p313_parse_cycle(&control, &result, 0);
    if (rc != P313_DETAIL_CYCLE_EVENT_MULTIPLICITY) return 10;
    if (fixture_count != 14U || result.total_records != 14U) return 11;
    if (result.record_hits[0] != 1U || result.record_hits[1] != 1U
        || result.record_hits[2] != 1U || result.record_hits[3] != 1U
        || result.record_hits[6] != 2U || result.record_hits[7] != 2U
        || result.record_hits[8] != 1U || result.record_hits[9] != 1U
        || result.record_hits[14] != 1U || result.record_hits[15] != 1U
        || result.record_hits[19] != 1U || result.record_hits[20] != 1U)
        return 12;
    for (size_t index = 0; index < P313_CYCLE_EVENT_COUNT; ++index) {
        if (index == 0U || index == 1U || index == 2U || index == 3U
            || index == 6U || index == 7U || index == 8U || index == 9U
            || index == 14U || index == 15U || index == 19U || index == 20U)
            continue;
        if (result.record_hits[index] != 0U) return 13;
    }
    printf("stop-detail=0x%lx records=14 phy-suspend-off-pairs=2\n", rc);
    return 0;
}
'''


def _runtime_localization(root: Path) -> dict[str, Any]:
    materialized = root / MATERIALIZED_ROOT
    runtime = (materialized / "s22plus_fyg8_p290_e3_runtime.inc.c").read_bytes()
    descriptor = (
        materialized / "s22plus_fyg8_p286_trace_descriptor.h"
    ).read_bytes()
    parser = _definition(runtime, b"static long p313_parse_cycle(")
    _require_order(
        parser,
        "stop-multiplicity-parser",
        b"P313_PAIR(phy_suspend_off, 6U, 7U, 2, 1, run_pairs);",
        b"phy_suspend_off_count > 1U",
        b"return P313_DETAIL_CYCLE_EVENT_MULTIPLICITY;",
        b"if (!final) return 0;",
    )
    output = support._compile(  # noqa: SLF001
        _stop_fixture_tu(runtime, descriptor), "p313-stop-multiplicity-localization"
    )
    expected = "stop-detail=0x6712 records=14 phy-suspend-off-pairs=2\n"
    if output != expected:
        raise AuditError(f"P3.13 stop localization fixture differs: {output!r}")

    clean = int(
        re.search(rb"^#define P313_CYCLE_CLEAN_RECORDS (\d+)U$", runtime, re.M)[1]
    )
    drift = int(
        re.search(rb"^#define P313_CYCLE_DRIFT_RECORDS (\d+)U$", runtime, re.M)[1]
    )
    if (clean, drift) != (37, 45):
        raise AuditError("P3.13 frozen cycle record contract differs")
    expected_stop_pairs = 2
    expected_restart_pairs = 2
    records_per_pair = 2
    extra_records = records_per_pair * (
        (expected_stop_pairs - 1) + (expected_restart_pairs - 1)
    )
    return {
        "materialized_fixture": output.strip(),
        "frozen_clean_records": clean,
        "frozen_drift_records": drift,
        "source_derived_extra_records": extra_records,
        "source_derived_successor_clean_records": clean + extra_records,
        "source_derived_successor_drift_records": drift + extra_records,
        "record_capacity": 64,
        "successor_clean_headroom": 64 - (clean + extra_records),
        "successor_drift_headroom": 64 - (drift + extra_records),
        "raw_pair_vector_recovered": False,
        "source_forced_trigger_localized": True,
        "exclusive_pair_identity_proved": False,
    }


def _position_cross_product() -> dict[str, int]:
    run_id = bytes.fromhex("00112233445566778899aabbccddeeff")
    record = carrier.initialize_record(spec.PROFILE, run_id)
    prefixes: list[bytes] = []
    for generation, position in enumerate(spec.POSITIONS, 1):
        prefixes.append(record)
        if generation == len(spec.POSITIONS):
            break
        detail = (
            spec.encode_a(cycle_attempted=1, state_index=0, speed_index=0)
            if generation == spec.ATTR_ORDINAL + 1
            else 0
        )
        record = carrier.apply_request(
            record,
            carrier.encode_request(
                spec.PROFILE,
                position.stage,
                run_id=run_id,
                outcome=carrier.OUTCOME_PROGRESS,
                item_index=position.item_index,
                detail=detail,
            ),
        )

    accepted_failure = 0
    rejected_progress = 0
    for generation, (position, prefix) in enumerate(
        zip(spec.POSITIONS, prefixes, strict=True), 1
    ):
        for detail in spec.CONTRADICTION_DETAIL_NAMES:
            request = carrier.encode_request(
                spec.PROFILE,
                position.stage,
                run_id=run_id,
                outcome=carrier.OUTCOME_FAILURE,
                item_index=position.item_index,
                detail=detail,
            )
            candidate = carrier.apply_request(prefix, request)
            decoded = decoder.decode_record(candidate, expected_run_id=run_id)
            if (
                decoded["active"]["generation"] != generation
                or decoded["active"]["detail"] != detail
                or decoded["active"]["outcome"] != carrier.OUTCOME_FAILURE
                or decoded["fallback_used"]
                or decoded["active_semantics"]["detail_name"]
                != spec.CONTRADICTION_DETAIL_NAMES[detail]
            ):
                raise AuditError("P3.13 contradiction position round trip differs")
            accepted_failure += 1

            bad = carrier.encode_request(
                spec.PROFILE,
                position.stage,
                run_id=run_id,
                outcome=carrier.OUTCOME_PROGRESS,
                item_index=position.item_index,
                detail=detail,
            )
            try:
                carrier.apply_request(prefix, bad)
            except carrier.DesignError:
                rejected_progress += 1
            else:
                raise AuditError("P3.13 contradiction progress pair was accepted")

    expected = len(spec.POSITIONS) * len(spec.CONTRADICTION_DETAIL_NAMES)
    if accepted_failure != expected or rejected_progress != expected:
        raise AuditError("P3.13 contradiction position cross product differs")
    return {
        "generation_count": len(spec.POSITIONS),
        "contradiction_detail_count": len(spec.CONTRADICTION_DETAIL_NAMES),
        "failure_round_trips": accepted_failure,
        "progress_outcome_rejections": rejected_progress,
    }


def _pair_detail_gate_contract(root: Path) -> dict[str, Any]:
    materialized = root / MATERIALIZED_ROOT
    runtime = (materialized / "s22plus_fyg8_p290_e3_runtime.inc.c").read_bytes()
    checkpoint = (materialized / "s22plus_fyg8_p290_checkpoint.c").read_bytes()
    header = (materialized / "s22plus_r4w1e_checkpoint.h").read_bytes()
    patch = (root / "workspace/private/outputs/s22plus_fyg8_p313/intent/candidate.patch").read_bytes()
    details = tuple(
        successor.encode_pair_mask(mask)
        for mask in range(1, successor.PAIR_MASK_MAX + 1)
    )
    array = support._array("pair_mask_details", details)  # noqa: SLF001

    runtime_tu = cross_gate._runtime_gate_tu(runtime)  # noqa: SLF001
    runtime_main = br'''
int main(void) {
    (void)check_a;
    (void)check_b;
    for (size_t index = 0;
         index < sizeof(pair_mask_details) / sizeof(pair_mask_details[0]);
         ++index) {
        if (p301_terminal_detail_allowed(pair_mask_details[index])) return 10;
    }
    printf("runtime-current-reject=1023\n");
    return 0;
}
'''
    runtime_tu = (
        runtime_tu[: runtime_tu.index(b"int main(void) {")]
        + array
        + runtime_main
    )

    checkpoint_tu = cross_gate._checkpoint_gate_tu(  # noqa: SLF001
        checkpoint, header
    )
    checkpoint_main = br'''
int main(void) {
    (void)check_values;
    (void)p313_a_outputs;
    (void)p313_b_outputs;
    for (size_t ordinal = 0; ordinal < 107U; ++ordinal) {
        for (size_t index = 0;
             index < sizeof(pair_mask_details) / sizeof(pair_mask_details[0]);
             ++index) {
            if (!p288_detail_allowed(
                    ordinal, S22_P233_OUTCOME_FAILURE,
                    pair_mask_details[index])) return 20;
        }
    }
    printf("checkpoint-accept=109461\n");
    return 0;
}
'''
    checkpoint_tu = (
        checkpoint_tu[: checkpoint_tu.index(b"int main(void) {")]
        + array
        + checkpoint_main
    )

    kernel_tu = cross_gate._kernel_gate_tu(patch)  # noqa: SLF001
    kernel_main = br'''
int main(void) {
    (void)check_values;
    (void)p313_a_outputs;
    (void)p313_b_outputs;
    for (size_t ordinal = 0; ordinal < 107U; ++ordinal) {
        for (size_t index = 0;
             index < sizeof(pair_mask_details) / sizeof(pair_mask_details[0]);
             ++index) {
            if (!s22_fyg8_e1_detail_allowed(
                    3U, ordinal, 107U, 2U,
                    pair_mask_details[index])) return 30;
        }
    }
    printf("fixed-image-accept=109461\n");
    return 0;
}
'''
    kernel_tu = (
        kernel_tu[: kernel_tu.index(b"int main(void) {")]
        + array
        + kernel_main
    )

    actual = {
        "current_runtime": support._compile(  # noqa: SLF001
            runtime_tu, "p313-successor-pair-runtime-gate"
        ),
        "checkpoint": support._compile(  # noqa: SLF001
            checkpoint_tu, "p313-successor-pair-checkpoint-gate"
        ),
        "fixed_image": support._compile(  # noqa: SLF001
            kernel_tu, "p313-successor-pair-fixed-image-gate"
        ),
    }
    expected = {
        "current_runtime": "runtime-current-reject=1023\n",
        "checkpoint": "checkpoint-accept=109461\n",
        "fixed_image": "fixed-image-accept=109461\n",
    }
    if actual != expected:
        raise AuditError(f"P3.13 successor pair detail gates differ: {actual!r}")
    return {
        "pair_names": list(successor.PAIR_NAMES),
        "detail_min": successor.PAIR_MASK_DETAIL_MIN,
        "detail_max": successor.PAIR_MASK_DETAIL_MAX,
        "output_count": len(details),
        "trace_record_cost": 0,
        "historical_p311_range_disjoint": not any(
            0x6801 <= detail <= 0x680C for detail in details
        ),
        "current_runtime_guard_accepts": False,
        "successor_runtime_guard_change_required": True,
        "checkpoint_value_position_acceptances": 109_461,
        "fixed_image_value_position_acceptances": 109_461,
        "full_lto_required": False,
        "verified": True,
    }


def audit(root: Path) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "kernel_source_contract": _kernel_source_contract(root),
        "runtime_localization": _runtime_localization(root),
        "carrier_value_generation_cross_product": _position_cross_product(),
        "carrier_cross_product_scope": (
            "all-63-contradiction-values-times-all-107-generations; "
            "the successor still requires the runtime-authorized 1200-B-value "
            "accept-reject matrix through the real Process-v2 adapter"
        ),
        "pair_specific_multiplicity_detail": _pair_detail_gate_contract(root),
        "successor_hazard_registration": {
            "requirements_sha256": successor.requirements_sha256(),
            "requirements": successor.requirements(),
            "qualification_status": "registered-not-satisfied",
        },
        "device_contact": False,
        "fixed_candidate_changed": False,
        "full_lto_required_for_successor": False,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(audit(Path.cwd()), indent=2, sort_keys=True))
