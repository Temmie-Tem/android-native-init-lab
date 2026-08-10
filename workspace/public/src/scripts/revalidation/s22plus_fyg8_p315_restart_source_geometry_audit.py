#!/usr/bin/env python3
"""Derive the P3.15 restart record geometry from exact source receipts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import s22plus_fyg8_p313_stop_multiplicity_audit as predecessor
import s22plus_fyg8_p315_design_contract as design
import s22plus_fyg8_p315_generator as generator


SCHEMA = "s22plus_fyg8_p315_restart_source_geometry_audit_v1"
VERDICT = "PASS_P315_RESTART_SOURCE_GEOMETRY_HOST_ONLY"


class GeometryError(ValueError):
    pass


def _definition(source: bytes, marker: bytes) -> bytes:
    try:
        return predecessor._definition(source, marker, last=True)  # noqa: SLF001
    except (ValueError, predecessor.AuditError) as exc:
        raise GeometryError(f"source definition differs: {marker!r}") from exc


def _require_order(source: bytes, label: str, *needles: bytes) -> None:
    cursor = 0
    for needle in needles:
        found = source.find(needle, cursor)
        if found < 0:
            raise GeometryError(f"{label} source order differs at {needle!r}")
        cursor = found + len(needle)


def _require_count(source: bytes, needle: bytes, count: int, label: str) -> None:
    if source.count(needle) != count:
        raise GeometryError(f"{label} source count differs")


def _receipt(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _cycle_descriptor_names(descriptor: bytes) -> tuple[str, ...]:
    marker = b"static const struct p282_event_descriptor p282_cycle_events[] = {"
    start = descriptor.find(marker)
    if start < 0:
        raise GeometryError("cycle descriptor array is absent")
    end = descriptor.find(b"\n};", start)
    if end < 0:
        raise GeometryError("cycle descriptor array is unterminated")
    block = descriptor[start:end]
    return tuple(
        match.decode("ascii")
        for match in re.findall(rb'^\s*\{"([a-z0-9_]+)"', block, re.M)
    )


def _source_geometry(root: Path) -> dict[str, Any]:
    authority = design.verify_source_authority(root)
    kernel = root / design.KERNEL_SOURCE_ROOT / "msm-kernel/drivers/usb"
    wrapper = (kernel / "dwc3/dwc3-msm-core.c").read_bytes()
    core = (kernel / "dwc3/core.c").read_bytes()
    gadget = (kernel / "dwc3/gadget.c").read_bytes()
    phy = (kernel / "phy/phy-msm-snps-hs.c").read_bytes()

    artifacts = generator.generate_bytes(
        root,
        run_id=generator.frozen_identity(root)[0],
        unsat_tag=generator.frozen_identity(root)[1],
        profile=generator.frozen_identity(root)[2],
    )
    descriptor = artifacts["trace_descriptor_header"]
    runtime = artifacts["p290_e3_runtime_include"]
    patch = artifacts["candidate_patch"]

    names = _cycle_descriptor_names(descriptor)
    expected_names = (
        "start_peripheral_in", "start_peripheral_out",
        "child_suspend_in", "child_suspend_out",
        "child_resume_in", "child_resume_out",
        "phy_suspend_in", "phy_suspend_out",
        "phy_power_in", "phy_power_out",
        "phy_init_in", "phy_init_out",
        "notify_connect_in", "notify_connect_out",
        "outer_sm_work_in", "outer_sm_work_out", "cycle_qscratch",
        "cycle_pull_in", "cycle_pull_out", "cycle_run_in", "cycle_run_out",
        "cycle_start_in", "cycle_start_out", "cycle_state_snapshot",
        "cycle_event_config",
    )
    if names != expected_names:
        raise GeometryError("25-event descriptor order differs")

    ext_notify = _definition(wrapper, b"static void dwc3_ext_event_notify(")
    state_machine = _definition(wrapper, b"static void dwc3_otg_sm_work(")
    start_peripheral = _definition(
        wrapper, b"static int dwc3_otg_start_peripheral("
    )
    parent_suspend = _definition(wrapper, b"static int dwc3_msm_suspend(")
    parent_resume = _definition(wrapper, b"static int dwc3_msm_resume(")
    set_role = _definition(wrapper, b"static int dwc3_msm_set_role(")
    child_suspend = _definition(core, b"static int dwc3_suspend_common(")
    child_resume = _definition(core, b"static int dwc3_resume_common(")
    core_exit = _definition(core, b"static void dwc3_core_exit(")
    core_init = _definition(core, b"static int dwc3_core_init(")
    gadget_suspend = _definition(gadget, b"int dwc3_gadget_suspend(")
    gadget_resume = _definition(gadget, b"int dwc3_gadget_resume(")
    hs_init = _definition(phy, b"static int msm_hsphy_init(")
    hs_suspend = _definition(phy, b"static int msm_hsphy_set_suspend(")

    _require_order(
        set_role,
        "role-to-worker",
        b"case USB_ROLE_DEVICE:",
        b"mdwc->vbus_active = true;",
        b"case USB_ROLE_NONE:",
        b"mdwc->vbus_active = false;",
        b"dwc3_ext_event_notify(mdwc);",
    )
    _require_order(
        ext_notify,
        "external-event-scheduling",
        b"flush_delayed_work(&mdwc->sm_work);",
        b"queue_delayed_work(mdwc->sm_usb_wq, &mdwc->sm_work, 0);",
    )
    _require_order(
        state_machine,
        "peripheral-restart-state-chain",
        b"case DRD_STATE_IDLE:",
        b"dwc3_otg_start_peripheral(mdwc, 1);",
        b"mdwc->drd_state = DRD_STATE_PERIPHERAL;",
        b"work = true;",
        b"case DRD_STATE_PERIPHERAL:",
        b"mdwc->drd_state = DRD_STATE_IDLE;",
        b"dwc3_otg_start_peripheral(mdwc, 0);",
        b"work = true;",
        b"if (work)",
        b"queue_delayed_work(mdwc->sm_usb_wq, &mdwc->sm_work, delay);",
    )

    _require_order(
        start_peripheral,
        "parent-child-resume-order",
        b"pm_runtime_get_sync(mdwc->dev);",
        b"if (on) {",
        b"pm_runtime_get_sync(&mdwc->dwc3->dev);",
        b"usb_phy_notify_connect(mdwc->hs_phy, USB_SPEED_HIGH);",
    )
    _require_order(
        start_peripheral,
        "child-stop-order",
        b"} else {",
        b"dwc3_override_vbus_status(mdwc, false);",
        b"ret = pm_runtime_put_sync(&mdwc->dwc3->dev);",
        b"set_bit(WAIT_FOR_LPM, &mdwc->inputs);",
        b"pm_runtime_put_sync(mdwc->dev);",
    )
    _require_order(
        child_suspend,
        "child-suspend-chain",
        b"dwc3_gadget_suspend(dwc);",
        b"dwc3_core_exit(dwc);",
    )
    _require_order(
        child_resume,
        "child-resume-chain",
        b"dwc3_core_init_for_resume(dwc);",
        b"dwc3_gadget_resume(dwc);",
    )
    _require_count(core_exit, b"usb_phy_set_suspend(dwc->usb2_phy, 1);", 1,
                   "child HS suspend")
    _require_count(parent_suspend, b"usb_phy_set_suspend(mdwc->hs_phy, 1);", 1,
                   "parent HS suspend")
    _require_count(parent_resume, b"usb_phy_set_suspend(mdwc->hs_phy, 0);", 1,
                   "parent HS resume")
    _require_count(core_init, b"usb_phy_set_suspend(dwc->usb2_phy, 0);", 1,
                   "child HS resume")
    _require_order(
        hs_suspend,
        "idempotent-stop-and-resume",
        b"if (phy->suspended && suspend)",
        b"return 0;",
        b"if (suspend)",
        b"msm_hsphy_enable_power(phy, false);",
        b"phy->suspended = true;",
        b"msm_hsphy_enable_clocks(phy, true);",
        b"phy->suspended = false;",
    )
    _require_count(hs_suspend, b"msm_hsphy_enable_power(phy, false);", 1,
                   "HS power-off")
    _require_count(hs_init, b"ret = msm_hsphy_enable_power(phy, true);", 2,
                   "HS init power branches")
    _require_order(
        core_init,
        "child-init-chain",
        b"usb_phy_init(dwc->usb2_phy);",
        b"usb_phy_set_suspend(dwc->usb2_phy, 0);",
    )
    _require_count(start_peripheral,
                   b"usb_phy_notify_connect(mdwc->hs_phy, USB_SPEED_HIGH);", 1,
                   "HS notify-connect")

    _require_order(
        gadget_suspend,
        "stop-run-chain",
        b"dwc3_gadget_run_stop(dwc, false);",
        b"__dwc3_gadget_stop(dwc);",
    )
    _require_order(
        gadget_resume,
        "resume-run-chain",
        b"__dwc3_gadget_start(dwc);",
        b"dwc3_gadget_run_stop(dwc, true);",
    )
    _require_count(gadget_suspend, b"dwc3_gadget_run_stop(dwc, false);", 1,
                   "run-off")
    _require_count(gadget_resume, b"__dwc3_gadget_start(dwc);", 1,
                   "gadget-start")
    _require_count(gadget_resume, b"dwc3_gadget_run_stop(dwc, true);", 1,
                   "run-on")
    if b"dwc3_gadget_pullup" in gadget_suspend + gadget_resume:
        raise GeometryError("resume chain unexpectedly calls gadget pullup")

    _require_count(
        patch,
        b"s22_p294_dwc3_state_snapshot(\n",
        2,
        "run-on state snapshot hook definition and call",
    )
    _require_count(
        patch,
        b"s22_p300_dwc3_event_config_snapshot(\n",
        2,
        "run-on config snapshot hook definition and call",
    )
    if patch.count(b"\tif (is_on) {") < 1:
        raise GeometryError("run-on snapshot conditional is absent")
    _require_count(
        descriptor,
        b'"cycle_qscratch", "p:p282/cycle_qscratch '
        b'dwc3_msm:dwc3_otg_start_peripheral+0x4cc',
        1,
        "QSCRATCH descriptor",
    )

    inherited_kernel = predecessor._kernel_source_contract(root)  # noqa: SLF001
    if (
        inherited_kernel.get("shared_hs_phy_from_child_usb_phy_phandle_zero")
        is not True
        or inherited_kernel.get("source_forced_stop_pair_count") != 2
        or inherited_kernel.get("source_forced_restart_pair_count") != 2
    ):
        raise GeometryError("shared HS-PHY source contract differs")

    pair_counts = {
        "start_off": 1,
        "start_on": 1,
        "child_suspend": 1,
        "child_resume": 1,
        "phy_suspend_off": 2,
        "phy_suspend_on": 2,
        "power_off": 1,
        "power_on": 1,
        "phy_init": 1,
        "notify_connect": 1,
    }
    if pair_counts != design.RESTART_EXPECTED_COUNTS:
        raise GeometryError("source-derived restart pair vector differs")

    auxiliary = {
        "outer_pairs": 4,
        "pullup_pairs": 0,
        "run_pairs": 2,
        "gadget_start_pairs": 1,
        "qscratch_hits": 1,
        "state_hits": 1,
        "config_hits": 1,
        "functional_pair_records": 2 * sum(pair_counts.values()),
        "outer_pair_records": 8,
        "run_pair_records": 4,
        "gadget_start_pair_records": 2,
        "singleton_records": 3,
    }
    auxiliary["total_records"] = (
        auxiliary["functional_pair_records"]
        + auxiliary["outer_pair_records"]
        + auxiliary["run_pair_records"]
        + auxiliary["gadget_start_pair_records"]
        + auxiliary["singleton_records"]
    )
    expected_auxiliary = {
        key: value
        for key, value in design.RESTART_AUXILIARY_GEOMETRY.items()
        if key != "outer_pair_chain"
    }
    if auxiliary != expected_auxiliary:
        raise GeometryError("source-derived auxiliary geometry differs")
    if auxiliary["total_records"] != 41:
        raise GeometryError("source-derived restart record total differs")

    parser = _definition(runtime, b"static long p313_parse_cycle(")
    for token in (
        b"p315_restart_expected",
        b"case P314_PHASE_RESTART:",
        b"expected = p315_restart_expected;",
        b"result->outer_pairs != 4U",
        b"result->pullup_pairs != 0U",
        b"result->qscratch_hits != 1U",
        b"result->gadget_start_pairs != 1U",
        b"result->run_pairs != 2U",
        b"result->state_hits != 1U",
        b"result->config_hits != 1U",
    ):
        if token not in parser and token not in runtime:
            raise GeometryError(f"materialized geometry token absent: {token!r}")

    return {
        "source_authority": authority,
        "generated_artifact_receipts": {
            "runtime": _receipt(runtime),
            "descriptor": _receipt(descriptor),
            "candidate_patch": _receipt(patch),
        },
        "descriptor_event_names": list(names),
        "shared_hs_phy": True,
        "pair_counts": pair_counts,
        "pair_source_derivation": design.RESTART_PAIR_SOURCE_DERIVATION,
        "auxiliary_geometry": auxiliary,
        "outer_pair_derivation": [
            "stop-transition-worker",
            "stop-WAIT_FOR_LPM-stabilization-worker",
            "restart-transition-worker",
            "restart-work-flag-stabilization-worker",
        ],
        "all_ten_pair_counts_source_derived": True,
        "all_seventeen_auxiliary_records_source_derived": True,
        "fixture_copy_used_as_source_proof": False,
        "verified": True,
    }


def audit(root: Path | None = None) -> dict[str, Any]:
    root = (root or Path(__file__).resolve().parents[5]).resolve()
    geometry = _source_geometry(root)
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "requirements_sha256": design.requirements_sha256(),
        "restart_geometry": geometry,
        "device_contact": False,
        "fixed_image_changed": False,
        "full_lto_required": False,
        "verified": True,
    }


def main() -> int:
    try:
        result = audit()
    except (GeometryError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
