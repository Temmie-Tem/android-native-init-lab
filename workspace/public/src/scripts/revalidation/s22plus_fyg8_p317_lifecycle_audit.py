#!/usr/bin/env python3
"""Audit inherited late-loader bytes and P3.17 immediate callers."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

import s22plus_fyg8_p316_lifecycle_audit as inherited
import s22plus_fyg8_p316_generator as parent_generator
import s22plus_fyg8_p308_cross_gate_audit as support
import s22plus_fyg8_p317_generator as generator


SCHEMA = "s22plus_fyg8_p317_lifecycle_audit_v1"
VERDICT = "PASS_P317_LATE_LOADER_LIFECYCLE_HOST_ONLY"
LifecycleError = inherited.LifecycleError


def audit(root: Path | None = None) -> dict[str, object]:
    root = (root or Path(__file__).resolve().parents[5]).resolve()
    inherited_value = inherited.audit(root)
    if inherited_value.get("verified") is not True:
        raise LifecycleError("P3.17 inherited lifecycle audit differs")

    run_id, unsat_tag, profile = generator.frozen_identity(root)
    current = generator.generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    parent = parent_generator.generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    runtime = current["p290_e3_runtime_include"]
    parent_runtime = parent["p290_e3_runtime_include"]
    wrapper = current["runtime_wrapper"]

    inherited_helpers = (
        b"static long p316_observe_diagnostic(",
        b"static long p316_abort_and_reap_child(",
        b"static __attribute__((noreturn)) void p316_diag_child(",
        b"static long p316_drain_helper_pipe(",
        b"static uint8_t p316_observer_error_class(",
        b"static uint8_t p316_late_evidence_priority(",
    )
    inherited_hashes: dict[str, str] = {}
    for marker in inherited_helpers:
        current_definition = support._definition(runtime, marker)  # noqa: SLF001
        parent_definition = support._definition(  # noqa: SLF001
            parent_runtime, marker
        )
        if current_definition != parent_definition:
            raise LifecycleError(
                f"P3.17 inherited helper differs: {marker.decode()}"
            )
        inherited_hashes[marker.decode()] = hashlib.sha256(
            current_definition
        ).hexdigest()

    run = support._definition(  # noqa: SLF001
        runtime, b"static __attribute__((noreturn)) void p317_run("
    )
    if run.count(b"p317_fail_observer(") != 7:
        raise LifecycleError("P3.17 runtime observer caller cardinality differs")
    inherited._ordered(  # noqa: SLF001
        run,
        (
            b"p317_capture_policy();",
            b"S22PLUS_MAX77705_P317_OBSERVER_SITE_CMDLINE, rc, NULL",
            b"p316_verify_substrate_bindings();",
            b"S22PLUS_MAX77705_OBSERVER_SITE_SUBSTRATE_VERIFY, rc, NULL",
            b"p316_scan_i2c_topology(&topology);",
            b"S22PLUS_MAX77705_OBSERVER_SITE_PRE_TOPOLOGY, rc, NULL",
            b"p317_capture_post_provider();",
            b"S22PLUS_MAX77705_P317_OBSERVER_SITE_PROVIDER_POST, rc, NULL",
            b"p317_capture_waiting(topology.parent_path, &waiting_state);",
            b"S22PLUS_MAX77705_P317_OBSERVER_SITE_WAITING, rc, NULL",
            b"p317_capture_supplier(topology.parent_path, &supplier_state);",
            b"S22PLUS_MAX77705_P317_OBSERVER_SITE_SUPPLIER, rc, NULL",
            b"p316_observe_diagnostic(tty_fd, &topology, &observation);",
            b"observation.observer_site != S22PLUS_MAX77705_OBSERVER_SITE_NONE",
            b"S22PLUS_MAX77705_OBSERVER_SITE_LATE_LOADER",
            b"rc, &observation",
        ),
        "P3.17 observer-failure immediate callers",
    )
    if wrapper.count(b"p317_fail_observer(") != 2:
        raise LifecycleError("P3.17 wrapper observer caller cardinality differs")
    inherited._ordered(  # noqa: SLF001
        wrapper,
        (
            b"long p316_override_rc = p316_prepare_overrides();",
            b"S22PLUS_MAX77705_OBSERVER_SITE_OVERRIDE_PREPARE",
            b"p316_override_rc, NULL",
            b"index == P317_PROVIDER_CHAIN_LAST_MODULE_INDEX",
            b"p317_capture_preclient_provider();",
            b"S22PLUS_MAX77705_P317_OBSERVER_SITE_PROVIDER_PRE",
            b"p317_provider_rc, NULL",
        ),
        "P3.17 pre-module observer callers",
    )
    if wrapper.count(b"p317_fail_precondition(") != 1:
        raise LifecycleError("P3.17 wrapper precondition cardinality differs")
    inherited._ordered(  # noqa: SLF001
        wrapper,
        (
            b"p317_provider_ready(",
            b"g_p317_exec.pre_present, g_p317_exec.pre_bound",
            b"S22PLUS_MAX77705_P317_TERMINAL_PROVIDER_PRECONDITION",
        ),
        "P3.17 provider precondition caller",
    )
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "materialized_runtime_sha256": hashlib.sha256(runtime).hexdigest(),
        "p316_lifecycle_verdict": inherited_value["verdict"],
        "p316_materialized_runtime_sha256": inherited_value[
            "materialized_runtime_sha256"
        ],
        "inherited_helper_definitions_byte_identical": True,
        "inherited_helper_sha256": inherited_hashes,
        "p317_runtime_observer_callers": 7,
        "p317_wrapper_observer_callers": 2,
        "p317_wrapper_precondition_callers": 1,
        "observer_failure_immediate_callers_verified": True,
        "device_contact": False,
        "verified": True,
    }


def main() -> int:
    try:
        value = audit()
    except (LifecycleError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
