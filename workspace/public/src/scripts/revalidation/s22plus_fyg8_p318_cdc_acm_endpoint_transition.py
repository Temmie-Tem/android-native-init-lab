#!/usr/bin/env python3
"""Audit the P3.17 physical-topology drift without widening live selection.

This is host-only.  The sealed sidecar proves that the approved Download path
and the later candidate path differ.  The operator separately reports moving
the cable during the run.  That human report is documented outside this
machine-derived receipt; it is not promoted to source authority here.  The
observed path pair is incident evidence only and must never authorize a live
selector transition.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import itertools
import json
import re
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "s22plus_fyg8_p318_cdc_acm_topology_drift_v3"
AUTHORITY_SCHEMA = "s22plus_fyg8_p318_topology_drift_authority_v2"
VERDICT = "PASS_P318_P317_PHYSICAL_TOPOLOGY_DRIFT_LOCALIZATION_H0"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"

RUN_RELATIVE = Path(
    "workspace/private/runs/device-action-f1-live-v2/"
    "f1-2026-08-12T165954582328Z-1786553994582372233"
)
DEFAULT_PREPARED = RUN_RELATIVE / "prepared.json"
DEFAULT_TARGET_PRIVATE = RUN_RELATIVE / "target-private.json"
DEFAULT_OBSERVER_RECEIPT = RUN_RELATIVE / "candidate-observer.json"
DEFAULT_SIDECAR_RESULT = RUN_RELATIVE / "p300-usb-trace/result.json"
DEFAULT_KERNEL_LOG = RUN_RELATIVE / "p300-usb-trace/kernel.log"
DEFAULT_UDEV_LOG = RUN_RELATIVE / "p300-usb-trace/udev.log"
DEFAULT_OBSERVER_SOURCE = Path(
    "workspace/public/src/scripts/revalidation/"
    "device_action_cdc_acm_observer_v1.py"
)
DEFAULT_F_ACM_SOURCE = Path(
    "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
    "kernel_platform/common/drivers/usb/gadget/function/f_acm.c"
)
DEFAULT_U_SERIAL_SOURCE = Path(
    "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
    "kernel_platform/common/drivers/usb/gadget/function/u_serial.c"
)

DIGEST_RE = re.compile(r"[0-9a-f]{64}")
TOPOLOGY_RE = re.compile(r"[0-9]+-[0-9]+(?:\.[0-9]+)*")
USB_DEVICE_PATH_RE = re.compile(
    r"/devices/pci[0-9a-f:]+/[0-9a-f:.]+/usb[0-9]+/"
    r"[0-9]+-[0-9]+/[0-9]+-[0-9]+(?:\.[0-9]+)*"
)
ID_PATH_RE = re.compile(
    r"pci-[0-9a-f:.]+-usb-0:[0-9]+(?:\.[0-9]+)*"
)
CONTROLLER_RE = re.compile(r"/devices/pci[0-9a-f:]+/(?P<value>[0-9a-f:.]+)/usb")

TOPOLOGY_PHASES = ("download_start", "candidate_end", "rollback_download")
TOPOLOGY_RELATIONSHIPS = ("same", "drift", "absent", "ambiguous", "unavailable")
TOPOLOGY_AUTHORITIES = (
    "candidate_approved_exact",
    "rollback_bound_exact",
    "recovery_rebound_exact",
    "not_authorized",
)
PHASE_POLICY = {
    "download_start": {
        "eligible": "pre_session_candidate_eligible",
        "stop": "pre_session_stop_no_run_proof_class",
        "observer": "pre_session_observer_failure_no_attempt",
        "contradiction": "pre_session_authority_contradiction_no_attempt",
    },
    "candidate_end": {
        "retain": "retain_experiment_terminal_classification",
        "host_silent": "retain_host_silent_device_result",
        "precondition": "NO_PROOF_EXPERIMENT_PRECONDITION_and_park",
        "observer": "NO_PROOF_OBSERVER_and_park",
        "contradiction": "NO_PROOF_OBSERVER_authority_contradiction_and_park",
    },
    "rollback_download": {
        "resume": "rollback_may_resume_no_proof_reclassification",
        "park": "recovery_park_no_experiment_proof_reclassification",
    },
}
HOST_RECEIPT_STATES = ("endpoint_present", "endpoint_absent", "unavailable")
HOST_EVENT_KINDS = ("none", "reset", "connect_done", "setup")


class TransitionError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "AGENTS.md").is_file() and (parent / "GOAL.md").is_file():
            return parent
    raise TransitionError("repository root not found")


def _identity(stat_result: Any) -> tuple[int, int, int, int]:
    return (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        stat_result.st_mtime_ns,
    )


def stable_read(path: Path, label: str, limit: int) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise TransitionError(f"{label} unavailable: {path}") from exc
    if path.is_symlink() or not path.is_file() or not 0 < before.st_size <= limit:
        raise TransitionError(f"{label} is indirect, empty, or outside bound")
    data = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    if _identity(before) != _identity(after) or len(data) != before.st_size:
        raise TransitionError(f"{label} changed while reading")
    return data


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def classify_topology_phase(
    *,
    phase: str,
    relationship: str,
    authority_state: str,
    observation_complete: bool,
    causal_terminal_ready: bool,
    policy: dict[str, dict[str, str]] = PHASE_POLICY,
) -> dict[str, Any]:
    if phase not in TOPOLOGY_PHASES:
        raise TransitionError("topology phase differs")
    if relationship not in TOPOLOGY_RELATIONSHIPS:
        raise TransitionError("topology relationship differs")
    if authority_state not in TOPOLOGY_AUTHORITIES:
        raise TransitionError("topology authority state differs")
    if not isinstance(observation_complete, bool) or not isinstance(
        causal_terminal_ready, bool
    ):
        raise TransitionError("topology phase flags differ")
    if set(policy) != set(TOPOLOGY_PHASES) or any(
        not isinstance(value, dict) for value in policy.values()
    ):
        raise TransitionError("topology phase policy shape differs")

    candidate_eligible = False
    rollback_resume = False
    park = False
    proof_class: str | None = None

    if phase == "download_start":
        values = policy[phase]
        if authority_state != "candidate_approved_exact":
            effect = values["contradiction"]
        elif not observation_complete or relationship == "unavailable":
            effect = values["observer"]
        elif relationship == "same":
            effect = values["eligible"]
            candidate_eligible = True
        else:
            effect = values["stop"]
    elif phase == "candidate_end":
        values = policy[phase]
        park = True
        if authority_state != "candidate_approved_exact":
            effect = values["contradiction"]
            proof_class = "NO_PROOF_OBSERVER"
        elif not observation_complete or relationship == "unavailable":
            effect = values["observer"]
            proof_class = "NO_PROOF_OBSERVER"
        elif relationship in ("drift", "ambiguous"):
            effect = values["precondition"]
            proof_class = "NO_PROOF_EXPERIMENT_PRECONDITION"
        elif relationship == "absent":
            if causal_terminal_ready:
                effect = values["host_silent"]
                proof_class = "DEVICE_RESULT_HOST_SILENT"
                park = False
            else:
                effect = values["observer"]
                proof_class = "NO_PROOF_OBSERVER"
        else:
            effect = values["retain"]
            proof_class = "RETAIN_EXPERIMENT_TERMINAL"
            park = False
    else:
        values = policy[phase]
        normal_resume = (
            authority_state == "rollback_bound_exact"
            and relationship == "same"
            and observation_complete
        )
        recovery_resume = (
            authority_state == "recovery_rebound_exact"
            and relationship in ("same", "drift")
            and observation_complete
        )
        if normal_resume or recovery_resume:
            effect = values["resume"]
            rollback_resume = True
        else:
            effect = values["park"]
            park = True

    return {
        "phase": phase,
        "relationship": relationship,
        "authority_state": authority_state,
        "observation_complete": observation_complete,
        "causal_terminal_ready": causal_terminal_ready,
        "effect": effect,
        "proof_class": proof_class,
        "candidate_eligible": candidate_eligible,
        "rollback_resume": rollback_resume,
        "park": park,
        "rollback_path_kind": (
            "normal"
            if rollback_resume and authority_state == "rollback_bound_exact"
            else "reviewed_recovery"
            if rollback_resume and authority_state == "recovery_rebound_exact"
            else None
        ),
        "experiment_proof_reclassified_by_rollback": False,
    }


def _decision_signature(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["effect"],
        row["proof_class"],
        row["candidate_eligible"],
        row["rollback_resume"],
        row["park"],
        row["rollback_path_kind"],
        row["experiment_proof_reclassified_by_rollback"],
    )


def _expected_topology_decision(
    *,
    phase: str,
    relationship: str,
    authority_state: str,
    observation_complete: bool,
    causal_terminal_ready: bool,
) -> tuple[Any, ...]:
    if phase == "download_start":
        if authority_state != "candidate_approved_exact":
            return (
                "pre_session_authority_contradiction_no_attempt",
                None,
                False,
                False,
                False,
                None,
                False,
            )
        if not observation_complete or relationship == "unavailable":
            effect = "pre_session_observer_failure_no_attempt"
        elif relationship == "same":
            return (
                "pre_session_candidate_eligible",
                None,
                True,
                False,
                False,
                None,
                False,
            )
        else:
            effect = "pre_session_stop_no_run_proof_class"
        return (effect, None, False, False, False, None, False)
    if phase == "candidate_end":
        if authority_state != "candidate_approved_exact":
            return (
                "NO_PROOF_OBSERVER_authority_contradiction_and_park",
                "NO_PROOF_OBSERVER",
                False,
                False,
                True,
                None,
                False,
            )
        if not observation_complete or relationship == "unavailable":
            effect = "NO_PROOF_OBSERVER_and_park"
            proof_class = "NO_PROOF_OBSERVER"
            park = True
        elif relationship in ("drift", "ambiguous"):
            effect = "NO_PROOF_EXPERIMENT_PRECONDITION_and_park"
            proof_class = "NO_PROOF_EXPERIMENT_PRECONDITION"
            park = True
        elif relationship == "absent" and causal_terminal_ready:
            effect = "retain_host_silent_device_result"
            proof_class = "DEVICE_RESULT_HOST_SILENT"
            park = False
        elif relationship == "absent":
            effect = "NO_PROOF_OBSERVER_and_park"
            proof_class = "NO_PROOF_OBSERVER"
            park = True
        else:
            effect = "retain_experiment_terminal_classification"
            proof_class = "RETAIN_EXPERIMENT_TERMINAL"
            park = False
        return (effect, proof_class, False, False, park, None, False)
    normal = (
        authority_state == "rollback_bound_exact"
        and relationship == "same"
        and observation_complete
    )
    recovery = (
        authority_state == "recovery_rebound_exact"
        and relationship in ("same", "drift")
        and observation_complete
    )
    if normal or recovery:
        return (
            "rollback_may_resume_no_proof_reclassification",
            None,
            False,
            True,
            False,
            "normal" if normal else "reviewed_recovery",
            False,
        )
    return (
        "recovery_park_no_experiment_proof_reclassification",
        None,
        False,
        False,
        True,
        None,
        False,
    )


def audit_topology_phase_classifier(
    policy: dict[str, dict[str, str]] = PHASE_POLICY,
    classifier: Any = None,
) -> dict[str, Any]:
    expected_policy_keys = {
        "download_start": {"eligible", "stop", "observer", "contradiction"},
        "candidate_end": {
            "retain",
            "host_silent",
            "precondition",
            "observer",
            "contradiction",
        },
        "rollback_download": {"resume", "park"},
    }
    if set(policy) != set(expected_policy_keys) or any(
        set(policy[phase]) != keys for phase, keys in expected_policy_keys.items()
    ):
        raise TransitionError("topology phase policy keys differ")
    classify = classify_topology_phase if classifier is None else classifier
    inputs = list(
        itertools.product(
            TOPOLOGY_PHASES,
            TOPOLOGY_RELATIONSHIPS,
            TOPOLOGY_AUTHORITIES,
            (False, True),
            (False, True),
        )
    )
    rows = [
        classify(
            phase=phase,
            relationship=relationship,
            authority_state=authority_state,
            observation_complete=observation_complete,
            causal_terminal_ready=causal_terminal_ready,
            policy=policy,
        )
        for phase, relationship, authority_state, observation_complete, causal_terminal_ready in inputs
    ]
    mismatches = []
    for input_row, row in zip(inputs, rows):
        expected = _expected_topology_decision(
            phase=input_row[0],
            relationship=input_row[1],
            authority_state=input_row[2],
            observation_complete=input_row[3],
            causal_terminal_ready=input_row[4],
        )
        if _decision_signature(row) != expected:
            mismatches.append({"input": input_row, "actual": _decision_signature(row)})
    if mismatches:
        raise TransitionError("topology decision oracle mismatch")
    decision_partitions = {_decision_signature(row) for row in rows}
    return {
        "domain_row_count": len(rows),
        "decision_partition_count": len(decision_partitions),
        "decision_partition_sha256": digest(sorted(decision_partitions, key=repr)),
        "rows_sha256": digest(rows),
        "decision_oracle_mismatch_count": 0,
        "oracle_basis": "independent_phase_input_to_decision_rules",
        "input_echo_excluded_from_partition_digest": True,
        "normal_rollback_requires_rollback_bound_exact_same_complete": True,
        "drift_recovery_requires_reviewed_recovery_rebound_exact": True,
        "rollback_never_reclassifies_experiment": True,
        "all_other_rollback_rows_park": True,
    }


def classify_host_timing_consistency(
    *,
    validity_mask: int,
    host_event_kind: str,
    latch_install_delta_us: int | None,
    armed_before_gadget_exposure: bool,
    host_receipt_state: str,
    observation_complete: bool,
) -> dict[str, Any]:
    if host_event_kind not in HOST_EVENT_KINDS:
        raise TransitionError("host event kind differs")
    if host_receipt_state not in HOST_RECEIPT_STATES:
        raise TransitionError("host receipt state differs")
    if not isinstance(validity_mask, int) or not 0 <= validity_mask <= 0xFF:
        raise TransitionError("timing validity mask differs")
    if not isinstance(armed_before_gadget_exposure, bool):
        raise TransitionError("latch arming witness differs")
    if not isinstance(observation_complete, bool):
        raise TransitionError("host receipt completeness differs")

    device_samples_valid = validity_mask & 0x0F == 0x0F
    event_valid = bool(validity_mask & 0x10)
    install_valid = bool(validity_mask & 0x20)
    unknown_bits = validity_mask & ~0x3F
    if unknown_bits or not device_samples_valid:
        classification = "timing_observer_contradiction"
    elif not observation_complete:
        classification = "host_receipt_incomplete"
    elif not install_valid or latch_install_delta_us is None:
        classification = "host_event_not_observable"
    elif not isinstance(latch_install_delta_us, int):
        raise TransitionError("latch install delta differs")
    elif latch_install_delta_us > 0 or not armed_before_gadget_exposure:
        classification = "host_event_not_observable"
    elif event_valid and host_event_kind == "none":
        classification = "timing_observer_contradiction"
    elif not event_valid and host_event_kind != "none":
        classification = "timing_observer_contradiction"
    elif host_receipt_state == "unavailable":
        classification = "host_receipt_unavailable"
    elif not event_valid and host_receipt_state == "endpoint_present":
        classification = "timing_host_receipt_contradiction"
    elif not event_valid:
        classification = "no_host_event_observed_under_complete_latch"
    elif host_receipt_state == "endpoint_absent":
        classification = "host_event_observed_without_endpoint"
    else:
        classification = "host_event_observed_consistent_with_endpoint"
    return {
        "classification": classification,
        "causal_timing_allowed": classification
        in (
            "no_host_event_observed_under_complete_latch",
            "host_event_observed_without_endpoint",
            "host_event_observed_consistent_with_endpoint",
        ),
        "no_host_event_claim_allowed": classification
        == "no_host_event_observed_under_complete_latch",
        "observer_failure": classification
        in (
            "timing_observer_contradiction",
            "timing_host_receipt_contradiction",
            "host_event_not_observable",
            "host_receipt_incomplete",
            "host_receipt_unavailable",
        ),
    }


def classify_candidate_evidence(
    *,
    relationship: str,
    authority_state: str,
    observation_complete: bool,
    causal_terminal_ready: bool,
    validity_mask: int,
    host_event_kind: str,
    latch_install_delta_us: int | None,
    armed_before_gadget_exposure: bool,
) -> dict[str, Any]:
    host_receipt_state = (
        "endpoint_present"
        if relationship in ("same", "drift", "ambiguous")
        else "endpoint_absent"
        if relationship == "absent"
        else "unavailable"
    )
    timing = classify_host_timing_consistency(
        validity_mask=validity_mask,
        host_event_kind=host_event_kind,
        latch_install_delta_us=latch_install_delta_us,
        armed_before_gadget_exposure=armed_before_gadget_exposure,
        host_receipt_state=host_receipt_state,
        observation_complete=observation_complete,
    )
    if timing["observer_failure"]:
        return {
            "timing": timing,
            "topology": None,
            "proof_class": "NO_PROOF_OBSERVER",
            "effect": "NO_PROOF_OBSERVER_timing_cross_check_and_park",
            "park": True,
        }
    topology = classify_topology_phase(
        phase="candidate_end",
        relationship=relationship,
        authority_state=authority_state,
        observation_complete=observation_complete,
        causal_terminal_ready=causal_terminal_ready,
    )
    if (
        timing["classification"] == "host_event_observed_without_endpoint"
        and topology["proof_class"] == "DEVICE_RESULT_HOST_SILENT"
    ):
        topology = dict(topology)
        topology["proof_class"] = "DEVICE_RESULT_DWC3_HOST_EVENT_NO_ENDPOINT"
        topology["effect"] = "retain_dwc3_host_event_without_endpoint_device_result"
    return {
        "timing": timing,
        "topology": topology,
        "proof_class": topology["proof_class"],
        "effect": topology["effect"],
        "park": topology["park"],
    }


def audit_candidate_timing_cross_check() -> dict[str, Any]:
    rows = []
    for mask, kind, install, armed, receipt_state, complete in itertools.product(
        range(256),
        HOST_EVENT_KINDS,
        (None, -1, 1),
        (False, True),
        HOST_RECEIPT_STATES,
        (False, True),
    ):
        row = classify_host_timing_consistency(
            validity_mask=mask,
            host_event_kind=kind,
            latch_install_delta_us=install,
            armed_before_gadget_exposure=armed,
            host_receipt_state=receipt_state,
            observation_complete=complete,
        )
        rows.append((mask, kind, install, armed, receipt_state, complete, row))
    if any(
        row[6]["causal_timing_allowed"]
        and not (
            row[0] in (0x2F, 0x3F)
            and row[2] is not None
            and row[2] <= 0
            and row[3]
            and row[5]
        )
        for row in rows
    ):
        raise TransitionError("causal timing admitted without latch authority")
    if any(
        row[6]["no_host_event_claim_allowed"]
        != (
            row[0] == 0x2F
            and row[1] == "none"
            and row[2] is not None
            and row[2] <= 0
            and row[3]
            and row[4] == "endpoint_absent"
            and row[5]
        )
        for row in rows
    ):
        raise TransitionError("no-host-event claim domain differs")
    if any(not row[6]["observer_failure"] for row in rows if row[0] == 0x0F):
        raise TransitionError("legacy no-install mask can escape observer failure")
    present_without_event = classify_candidate_evidence(
        relationship="same",
        authority_state="candidate_approved_exact",
        observation_complete=True,
        causal_terminal_ready=True,
        validity_mask=0x2F,
        host_event_kind="none",
        latch_install_delta_us=-1,
        armed_before_gadget_exposure=True,
    )
    absent_without_event = classify_candidate_evidence(
        relationship="absent",
        authority_state="candidate_approved_exact",
        observation_complete=True,
        causal_terminal_ready=True,
        validity_mask=0x2F,
        host_event_kind="none",
        latch_install_delta_us=-1,
        armed_before_gadget_exposure=True,
    )
    legacy_mask = classify_candidate_evidence(
        relationship="absent",
        authority_state="candidate_approved_exact",
        observation_complete=True,
        causal_terminal_ready=True,
        validity_mask=0x0F,
        host_event_kind="none",
        latch_install_delta_us=None,
        armed_before_gadget_exposure=False,
    )
    absent_with_event = classify_candidate_evidence(
        relationship="absent",
        authority_state="candidate_approved_exact",
        observation_complete=True,
        causal_terminal_ready=True,
        validity_mask=0x3F,
        host_event_kind="reset",
        latch_install_delta_us=-1,
        armed_before_gadget_exposure=True,
    )
    incomplete_without_event = classify_candidate_evidence(
        relationship="absent",
        authority_state="candidate_approved_exact",
        observation_complete=False,
        causal_terminal_ready=True,
        validity_mask=0x2F,
        host_event_kind="none",
        latch_install_delta_us=-1,
        armed_before_gadget_exposure=True,
    )
    if (
        present_without_event["proof_class"] != "NO_PROOF_OBSERVER"
        or absent_without_event["timing"]["no_host_event_claim_allowed"] is not True
        or legacy_mask["proof_class"] != "NO_PROOF_OBSERVER"
        or absent_with_event["proof_class"]
        != "DEVICE_RESULT_DWC3_HOST_EVENT_NO_ENDPOINT"
        or incomplete_without_event["proof_class"] != "NO_PROOF_OBSERVER"
    ):
        raise TransitionError("candidate timing/host receipt cross-check differs")
    return {
        "timing_cross_product_row_count": len(rows),
        "timing_decision_partition_count": len(
            {
                digest(row[6])
                for row in rows
            }
        ),
        "endpoint_present_plus_mask_0x2f_is_contradiction": True,
        "endpoint_absent_plus_armed_mask_0x2f_allows_no_event": True,
        "endpoint_absent_plus_mask_0x3f_is_distinct_dwc3_event_result": True,
        "incomplete_receipt_never_allows_no_event_claim": True,
        "legacy_mask_0x0f_is_not_observable_not_no_event": True,
        "candidate_result_uses_timing_topology_wrapper": True,
    }


def _utc(value: Any, label: str) -> dt.datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise TransitionError(f"{label} is not a UTC timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise TransitionError(f"{label} is not a UTC timestamp") from exc
    return parsed


def _unique_object(items: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in items:
        if key in value:
            raise TransitionError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_json(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data, object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise TransitionError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise TransitionError(f"{label} is not an object")
    return value


def _strip_udev_prefix(line: str) -> str:
    match = re.fullmatch(r"[^ ]+ source=udev ?(.*)", line)
    return match.group(1) if match is not None else line


def parse_udev_blocks(data: bytes) -> tuple[dict[str, str], ...]:
    try:
        text = data.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise TransitionError("P3.17 udev log is not UTF-8") from exc
    blocks: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for raw in text.splitlines():
        line = _strip_udev_prefix(raw)
        if not line:
            if current:
                blocks.append(current)
                current = {}
            continue
        if line.startswith(("KERNEL[", "UDEV  [", "monitor will")):
            current["_header"] = line
            continue
        key, separator, value = line.partition("=")
        if separator:
            if key in current:
                raise TransitionError(f"duplicate udev property in block: {key}")
            current[key] = value
    if current:
        blocks.append(current)
    return tuple(blocks)


def _one(rows: Iterable[dict[str, str]], label: str) -> dict[str, str]:
    values = list(rows)
    if len(values) != 1:
        raise TransitionError(f"expected one {label}, found {len(values)}")
    return values[0]


def _controller(device_path: str) -> str:
    match = CONTROLLER_RE.search(device_path)
    if match is None:
        raise TransitionError("USB device path lacks an exact PCI controller")
    return match.group("value")


def _port_suffix(topology: str) -> str:
    match = re.fullmatch(r"[0-9]+-(.+)", topology)
    if match is None:
        raise TransitionError("USB topology lacks a port suffix")
    return match.group(1)


def _usb_device_path(tty_devpath: str, topology: str) -> str:
    marker = f"/{topology}:"
    if tty_devpath.count(marker) != 1:
        raise TransitionError("tty DEVPATH does not contain one interface boundary")
    return tty_devpath.split(marker, 1)[0]


def _observer_function(source: str, name: str) -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise TransitionError("CDC ACM observer source does not parse") from exc
    nodes = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    ]
    if len(nodes) != 1:
        raise TransitionError(f"expected one observer function {name}")
    segment = ast.get_source_segment(source, nodes[0])
    if segment is None:
        raise TransitionError(f"observer function source unavailable: {name}")
    return segment


def audit_observer_source(data: bytes) -> dict[str, Any]:
    try:
        source = data.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise TransitionError("CDC ACM observer source is not UTF-8") from exc
    matches = _observer_function(source, "_matches")
    candidate_like = _observer_function(source, "_candidate_like")
    select_start = source.find("    def _select(self)")
    select_end = source.find("\n    def _raw_tty", select_start)
    if select_start < 0 or select_end < 0:
        raise TransitionError("CDC ACM observer selector body is absent")
    select = source[select_start:select_end]
    required = {
        "_matches": "endpoint.topology == topology",
        "_candidate_like": "endpoint.topology == topology",
        "_select_matches_call": "if _matches(self.spec, topology.group(1), identity, endpoint)",
        "_select_candidate_like_call": "if _candidate_like(",
        "_select_timeout_fallback": '"identity-mismatch" if mismatched else "endpoint-timeout"',
    }
    regions = {
        "_matches": matches,
        "_candidate_like": candidate_like,
        "_select_matches_call": select,
        "_select_candidate_like_call": select,
        "_select_timeout_fallback": select,
    }
    for key, token in required.items():
        if regions[key].count(token) != 1:
            raise TransitionError(f"observer selector source seam drifted: {key}")
    return {
        "topology_required_by_exact_match": True,
        "topology_required_by_candidate_like_match": True,
        "unmatched_endpoint_falls_to_timeout": True,
        "tty_open_requires_selected_endpoint": True,
    }


def audit_dtr_sources(f_acm_data: bytes, u_serial_data: bytes) -> dict[str, Any]:
    try:
        f_acm = f_acm_data.decode("utf-8", "strict")
        u_serial = u_serial_data.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise TransitionError("CDC ACM gadget sources are not UTF-8") from exc
    dtr_tokens = (
        "FIXME we should not allow data to flow until the",
        "host sets the ACM_CTRL_DTR bit; and when it clears",
        "acm->port_handshake_bits = w_value;",
    )
    if any(f_acm.count(token) != 1 for token in dtr_tokens):
        raise TransitionError("f_acm DTR source seam drifted")
    start = u_serial.find("static int gs_write(")
    end = u_serial.find("\nstatic int gs_put_char(", start)
    if start < 0 or end < 0:
        raise TransitionError("u_serial gs_write boundary drifted")
    gs_write = u_serial[start:end]
    required = (
        "count = kfifo_in(&port->port_write_buf, buf, count);",
        "if (port->port_usb)",
        "gs_start_tx(port);",
        "return count;",
    )
    if any(gs_write.count(token) != 1 for token in required):
        raise TransitionError("u_serial TX source seam drifted")
    if "ACM_CTRL_DTR" in gs_write or "port_handshake_bits" in gs_write:
        raise TransitionError("u_serial unexpectedly gates TX on DTR")
    return {
        "control_line_state_is_stored": True,
        "dtr_flow_gate_implemented": False,
        "tty_write_queues_bytes": True,
        "tty_write_starts_tx_when_port_usb_present": True,
        "dtr_hypothesis_retained": False,
    }


def validate_authority(authority: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "schema",
        "target",
        "derivation",
        "source_topology",
        "source_usb_device_path",
        "source_id_path",
        "source_controller",
        "candidate_topology",
        "candidate_usb_device_path",
        "candidate_id_path",
        "candidate_controller",
        "candidate_identity",
        "same_port_suffix",
        "same_controller",
        "generic_companion_inference_forbidden",
        "observed_transition_authorizes_selection",
        "approved_path_remains_frozen",
        "scope",
    }
    if set(authority) != expected:
        raise TransitionError("endpoint transition authority shape differs")
    identity = authority["candidate_identity"]
    if (
        authority["schema"] != AUTHORITY_SCHEMA
        or authority["target"] != TARGET
        or authority["derivation"] != "sealed_p317_sidecar_topology_drift"
        or authority["generic_companion_inference_forbidden"] is not True
        or authority["observed_transition_authorizes_selection"] is not False
        or authority["approved_path_remains_frozen"] is not True
        or authority["scope"] != "p317_topology_drift_localization_only"
        or authority["same_port_suffix"] is not True
        or authority["same_controller"] is not False
        or not isinstance(identity, dict)
        or set(identity)
        != {"vendor", "product", "serial_sha256", "driver", "interface"}
        or identity["vendor"] != "04e8"
        or identity["product"] != "6861"
        or identity["driver"] != "cdc_acm"
        or identity["interface"] != "00"
        or not isinstance(identity["serial_sha256"], str)
        or DIGEST_RE.fullmatch(identity["serial_sha256"]) is None
    ):
        raise TransitionError("endpoint transition authority semantics differ")
    for key in ("source_topology", "candidate_topology"):
        if not isinstance(authority[key], str) or TOPOLOGY_RE.fullmatch(authority[key]) is None:
            raise TransitionError(f"endpoint transition {key} is invalid")
    for key in ("source_usb_device_path", "candidate_usb_device_path"):
        if (
            not isinstance(authority[key], str)
            or USB_DEVICE_PATH_RE.fullmatch(authority[key]) is None
            or not authority[key].endswith("/" + authority[key.replace("usb_device_path", "topology")])
        ):
            raise TransitionError(f"endpoint transition {key} is invalid")
    for key in ("source_id_path", "candidate_id_path"):
        if not isinstance(authority[key], str) or ID_PATH_RE.fullmatch(authority[key]) is None:
            raise TransitionError(f"endpoint transition {key} is invalid")
    if (
        authority["source_controller"] != _controller(authority["source_usb_device_path"])
        or authority["candidate_controller"] != _controller(authority["candidate_usb_device_path"])
        or authority["source_controller"] == authority["candidate_controller"]
        or _port_suffix(authority["source_topology"])
        != _port_suffix(authority["candidate_topology"])
    ):
        raise TransitionError("endpoint transition controller/suffix facts differ")
    return json.loads(json.dumps(authority, sort_keys=True))


def validate_endpoint(value: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "tty_name",
        "topology",
        "usb_device_path",
        "vendor",
        "product",
        "serial_sha256",
        "driver",
        "interface",
    }
    if set(value) != expected:
        raise TransitionError("endpoint fact shape differs")
    if (
        re.fullmatch(r"ttyACM[0-9]+", value["tty_name"]) is None
        or TOPOLOGY_RE.fullmatch(value["topology"]) is None
        or USB_DEVICE_PATH_RE.fullmatch(value["usb_device_path"]) is None
        or not value["usb_device_path"].endswith("/" + value["topology"])
        or re.fullmatch(r"[0-9a-f]{4}", value["vendor"]) is None
        or re.fullmatch(r"[0-9a-f]{4}", value["product"]) is None
        or DIGEST_RE.fullmatch(value["serial_sha256"]) is None
        or re.fullmatch(r"[A-Za-z0-9._-]{1,64}", value["driver"]) is None
        or re.fullmatch(r"[0-9a-f]{2}", value["interface"]) is None
    ):
        raise TransitionError("endpoint fact semantics differ")
    return dict(value)


def classify_endpoints(
    authority_value: dict[str, Any], endpoints_value: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    authority = validate_authority(authority_value)
    endpoints = [validate_endpoint(value) for value in endpoints_value]
    if len(endpoints) > 256:
        raise TransitionError("endpoint inventory exceeds bound")
    identity = authority["candidate_identity"]

    def exact(value: dict[str, Any]) -> bool:
        return all(value[key] == identity[key] for key in identity)

    exact_rows = [value for value in endpoints if exact(value)]
    foreign_samsung = [
        value
        for value in endpoints
        if value["vendor"] == "04e8" and not exact(value)
    ]
    selected: dict[str, Any] | None = None
    if len(exact_rows) > 1:
        classification = "exact-candidate-ambiguous"
    elif len(exact_rows) == 1:
        row = exact_rows[0]
        if (
            row["topology"] == authority["source_topology"]
            and row["usb_device_path"] == authority["source_usb_device_path"]
        ):
            classification = "selected-exact-approved-path"
            selected = row
        elif (
            row["topology"] == authority["candidate_topology"]
            and row["usb_device_path"] == authority["candidate_usb_device_path"]
        ):
            classification = "exact-candidate-topology-drift"
        else:
            classification = "exact-candidate-unrecognized-path"
    else:
        occupied = [
            value
            for value in endpoints
            if value["topology"] == authority["source_topology"]
            and value["usb_device_path"] == authority["source_usb_device_path"]
        ]
        classification = (
            "approved-path-identity-mismatch" if occupied else "endpoint-absent"
        )
    return {
        "classification": classification,
        "selected_endpoint_sha256": digest(selected) if selected is not None else None,
        "exact_candidate_count": len(exact_rows),
        "foreign_samsung_count": len(foreign_samsung),
        "inventory_count": len(endpoints),
        "open_permitted": selected is not None,
    }


def _candidate_observer_spec(prepared: dict[str, Any]) -> dict[str, str]:
    try:
        value = prepared["approval_binding"]["base_binding"]["observation"][
            "candidate_observer"
        ]
    except (KeyError, TypeError) as exc:
        raise TransitionError("P3.17 prepared observer spec is absent") from exc
    expected = {
        "kind",
        "usb_vendor_id",
        "usb_product_id",
        "usb_serial",
        "usb_driver",
        "usb_interface_number",
        "banner_hex",
    }
    if (
        not isinstance(value, dict)
        or set(value) != expected
        or value["kind"] != "exact_cdc_acm_banner_v1"
        or value["usb_vendor_id"] != "04e8"
        or value["usb_product_id"] != "6861"
        or value["usb_driver"] != "cdc_acm"
        or value["usb_interface_number"] != "00"
        or not isinstance(value["usb_serial"], str)
        or not value["usb_serial"].startswith("S22E3")
        or len(bytes.fromhex(value["banner_hex"])) != 49
    ):
        raise TransitionError("P3.17 prepared observer spec differs")
    return value


def _sidecar_source(result: dict[str, Any], name: str, data: bytes) -> None:
    try:
        source = result["sources"][name]
    except (KeyError, TypeError) as exc:
        raise TransitionError(f"P3.17 sidecar {name} source is absent") from exc
    if (
        source.get("alive_at_arm") is not True
        or source.get("alive_before_stop") is not True
        or source.get("truncated") is not False
        or source.get("returncode") != 0
        or source.get("bytes") != len(data)
        or source.get("sha256") != hashlib.sha256(data).hexdigest()
    ):
        raise TransitionError(f"P3.17 sidecar {name} authority differs")


def build_contract(
    *,
    prepared_data: bytes,
    target_data: bytes,
    observer_receipt_data: bytes,
    sidecar_result_data: bytes,
    kernel_data: bytes,
    udev_data: bytes,
    observer_source_data: bytes,
    f_acm_data: bytes,
    u_serial_data: bytes,
    extractor_data: bytes,
) -> dict[str, Any]:
    prepared = load_json(prepared_data, "P3.17 prepared state")
    target = load_json(target_data, "P3.17 private target")
    observer_receipt = load_json(
        observer_receipt_data, "P3.17 candidate observer receipt"
    )
    sidecar = load_json(sidecar_result_data, "P3.17 USB sidecar result")
    spec = _candidate_observer_spec(prepared)
    if (
        target.get("schema") != "device_action_f1_private_target_v2"
        or set(target) != {"schema", "serial", "topology"}
        or not isinstance(target["topology"], str)
        or re.fullmatch(r"usb:[0-9]+-[0-9]+(?:\.[0-9]+)*", target["topology"])
        is None
    ):
        raise TransitionError("P3.17 private target topology differs")
    source_topology = target["topology"].removeprefix("usb:")
    expected_topology_sha = hashlib.sha256(source_topology.encode()).hexdigest()
    if (
        observer_receipt.get("schema") != "device_action_cdc_acm_receipt_v1"
        or observer_receipt.get("classification") != "endpoint-timeout"
        or observer_receipt.get("accepted") is not False
        or observer_receipt.get("endpoint_identity_sha256") is not None
        or observer_receipt.get("topology_sha256") != expected_topology_sha
        or observer_receipt.get("raw")
        != {
            "path": str(
                (repo_root() / RUN_RELATIVE / "candidate-observer.raw").resolve()
            ),
            "sha256": hashlib.sha256(b"").hexdigest(),
            "size": 0,
        }
    ):
        raise TransitionError("P3.17 endpoint-timeout receipt differs")
    if (
        sidecar.get("schema") != "device_action_usb_trace_sidecar_v1"
        or sidecar.get("phase") != "complete"
        or sidecar.get("device_actions") is not False
        or sidecar.get("opens_candidate_acm") is not False
        or sidecar.get("non_authoritative") is not True
    ):
        raise TransitionError("P3.17 USB sidecar completion differs")
    _sidecar_source(sidecar, "kernel", kernel_data)
    _sidecar_source(sidecar, "udev", udev_data)
    source_audit = audit_observer_source(observer_source_data)
    dtr_audit = audit_dtr_sources(f_acm_data, u_serial_data)

    blocks = parse_udev_blocks(udev_data)
    source = _one(
        (
            row
            for row in blocks
            if row.get("ACTION") == "add"
            and row.get("SUBSYSTEM") == "usb"
            and row.get("DEVTYPE") == "usb_device"
            and row.get("ID_MODEL_ID") == "685d"
            and row.get("DEVPATH", "").endswith("/" + source_topology)
            and row.get("_header", "").startswith("UDEV  [")
        ),
        "P3.17 Download UDEV device block",
    )
    candidate_tty = _one(
        (
            row
            for row in blocks
            if row.get("ACTION") == "add"
            and row.get("SUBSYSTEM") == "tty"
            and row.get("DEVNAME") == "/dev/ttyACM0"
            and row.get("ID_VENDOR_ID") == spec["usb_vendor_id"]
            and row.get("ID_MODEL_ID") == spec["usb_product_id"]
            and row.get("ID_SERIAL_SHORT") == spec["usb_serial"]
            and row.get("ID_USB_DRIVER") == spec["usb_driver"]
            and row.get("ID_USB_INTERFACE_NUM")
            == spec["usb_interface_number"]
            and row.get("_header", "").startswith("UDEV  [")
        ),
        "P3.17 exact candidate tty UDEV block",
    )
    candidate_topology_match = re.search(
        r"/([0-9]+-[0-9]+(?:\.[0-9]+)*):[0-9]+\.[0-9]+/tty/ttyACM[0-9]+$",
        candidate_tty["DEVPATH"],
    )
    if candidate_topology_match is None:
        raise TransitionError("P3.17 candidate tty topology is invalid")
    candidate_topology = candidate_topology_match.group(1)
    candidate_device_path = _usb_device_path(
        candidate_tty["DEVPATH"], candidate_topology
    )
    source_device_path = source["DEVPATH"]
    source_id_path = source.get("ID_PATH", "")
    candidate_id_path = candidate_tty.get("ID_PATH", "").removesuffix(":1.0")
    authority = validate_authority(
        {
            "schema": AUTHORITY_SCHEMA,
            "target": TARGET,
            "derivation": "sealed_p317_sidecar_topology_drift",
            "source_topology": source_topology,
            "source_usb_device_path": source_device_path,
            "source_id_path": source_id_path,
            "source_controller": _controller(source_device_path),
            "candidate_topology": candidate_topology,
            "candidate_usb_device_path": candidate_device_path,
            "candidate_id_path": candidate_id_path,
            "candidate_controller": _controller(candidate_device_path),
            "candidate_identity": {
                "vendor": spec["usb_vendor_id"],
                "product": spec["usb_product_id"],
                "serial_sha256": hashlib.sha256(
                    spec["usb_serial"].encode("ascii")
                ).hexdigest(),
                "driver": spec["usb_driver"],
                "interface": spec["usb_interface_number"],
            },
            "same_port_suffix": (
                _port_suffix(source_topology) == _port_suffix(candidate_topology)
            ),
            "same_controller": (
                _controller(source_device_path) == _controller(candidate_device_path)
            ),
            "generic_companion_inference_forbidden": True,
            "observed_transition_authorizes_selection": False,
            "approved_path_remains_frozen": True,
            "scope": "p317_topology_drift_localization_only",
        }
    )
    kernel_text = kernel_data.decode("utf-8", "strict")
    required_kernel = (
        f"usb {candidate_topology}: new high-speed USB device",
        f"usb {candidate_topology}: New USB device found, idVendor=04e8, idProduct=6861",
        f"usb {candidate_topology}: SerialNumber: {spec['usb_serial']}",
        f"cdc_acm {candidate_topology}:1.0: ttyACM0: USB ACM device",
    )
    if any(kernel_text.count(token) != 1 for token in required_kernel):
        raise TransitionError("P3.17 kernel exact candidate evidence differs")
    enumeration_match = re.search(
        rf"(?m)^(?P<utc>[^ ]+Z) source=kernel .*usb {re.escape(candidate_topology)}: "
        r"new high-speed USB device",
        kernel_text,
    )
    if enumeration_match is None:
        raise TransitionError("P3.17 candidate enumeration time is absent")
    enumeration_utc = _utc(
        enumeration_match.group("utc"), "P3.17 candidate enumeration"
    )
    sidecar_end_value = sidecar["sources"]["kernel"].get("ended_utc")
    sidecar_end_utc = _utc(sidecar_end_value, "P3.17 kernel sidecar end")
    capture_after_enumeration_sec = (
        sidecar_end_utc - enumeration_utc
    ).total_seconds()
    if capture_after_enumeration_sec <= 30.0:
        raise TransitionError(
            "P3.17 sidecar did not continue 30 seconds after enumeration"
        )
    endpoint = {
        "tty_name": "ttyACM0",
        "topology": candidate_topology,
        "usb_device_path": candidate_device_path,
        **authority["candidate_identity"],
    }
    drift = classify_endpoints(authority, [endpoint])
    if (
        drift["classification"] != "exact-candidate-topology-drift"
        or drift["open_permitted"] is not False
    ):
        raise TransitionError("P3.17 topology drift does not fail closed")
    old_selector_exact = candidate_topology == source_topology
    if old_selector_exact:
        raise TransitionError("P3.17 endpoint unexpectedly matches frozen topology")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "inputs": {
            "prepared": receipt(prepared_data),
            "target_private": receipt(target_data),
            "candidate_observer_receipt": receipt(observer_receipt_data),
            "sidecar_result": receipt(sidecar_result_data),
            "kernel_log": receipt(kernel_data),
            "udev_log": receipt(udev_data),
            "frozen_observer_source": receipt(observer_source_data),
            "fixed_f_acm_source": receipt(f_acm_data),
            "fixed_u_serial_source": receipt(u_serial_data),
            "extractor": receipt(extractor_data),
        },
        "authority": authority,
        "authority_sha256": digest(authority),
        "frozen_observer": {
            **source_audit,
            "bound_topology": source_topology,
            "candidate_topology": candidate_topology,
            "exact_identity_seen_by_sidecar": True,
            "selected_endpoint_count": 0,
            "tty_open_attempted": False,
            "classification": "endpoint-timeout",
            "raw_size": 0,
            "effective_classification": "exact-candidate-topology-drift",
        },
        "topology_drift_assessment": drift,
        "successor_topology_continuity": {
            "operator_rule": (
                "do_not_disconnect_move_or_reroute_data_cable_dock_or_host_port_"
                "from_download_binding_through_rollback_and_final_health_close"
            ),
            "gate": {
                "name": "S22PLUS_F1_PHYSICAL_TOPOLOGY_CONTINUITY",
                "designation": "permanent_boundary",
                "hazard": "physical_endpoint_drift_breaks_attribution_or_recovery",
                "scope": "s22plus_f1_endpoint_observation_and_recovery_only",
                "expiry": None,
                "review_trigger": (
                    "endpoint_identity_topology_controller_capture_phase_"
                    "classification_recovery_binding_or_selector_change"
                ),
            },
            "path_receipts": [
                "approved_download_start_path_and_controller",
                "candidate_observer_end_path_and_controller",
                "fresh_rollback_download_path_and_controller",
            ],
            "path_record_schema": {
                "phases": ["download_start", "candidate_end", "rollback_download"],
                "fields": [
                    "phase",
                    "relationship_to_start",
                    "authority_state",
                    "binding_id_sha256",
                    "comparison_binding_id_sha256",
                    "match_count",
                    "observation_window_complete",
                    "causal_terminal_ready",
                    "endpoint_identity_sha256",
                    "topology_sha256",
                    "controller_path_sha256",
                    "usb_device_path_sha256",
                    "immutable_raw_snapshot_size",
                    "immutable_raw_snapshot_sha256",
                ],
                "same_bytes_parsed_and_hashed": True,
                "raw_snapshot_private": True,
                "tracked_record_contains_digest_only": True,
                "literal_topology_copy_forbidden": True,
            },
            "relationship_states": [
                "same",
                "drift",
                "absent",
                "ambiguous",
                "unavailable",
            ],
            "authority_states": [
                "candidate_approved_exact",
                "rollback_bound_exact",
                "recovery_rebound_exact",
                "not_authorized",
            ],
            "phase_state_effects": {
                "download_start": {
                    "candidate_approved_exact": "pre_session_candidate_eligible",
                    "drift_absent_ambiguous": "pre_session_stop_no_run_proof_class",
                    "unavailable": "pre_session_observer_failure_no_attempt",
                },
                "candidate_end": {
                    "same_endpoint_present": "retain_experiment_terminal_classification",
                    "same_complete_absent_causal_ready_after_timing_cross_check": (
                        "mask_0x2f_retains_host_silent_but_mask_0x3f_retains_"
                        "distinct_dwc3_host_event_no_endpoint_device_result"
                    ),
                    "drift_or_ambiguous": "NO_PROOF_EXPERIMENT_PRECONDITION_and_park",
                    "absent_without_complete_causal_ready": "NO_PROOF_OBSERVER_and_park",
                    "unavailable": "NO_PROOF_OBSERVER_and_park",
                },
                "rollback_download": {
                    "rollback_bound_exact_same": (
                        "normal_predeclared_rollback_may_resume_without_new_"
                        "independent_recovery_review"
                    ),
                    "recovery_rebound_exact_same_or_drift": (
                        "reviewed_recovery_only_rollback_may_resume"
                    ),
                    "absent_ambiguous_unavailable": (
                        "recovery_park_no_experiment_proof_reclassification"
                    ),
                    "relationship_to_start": (
                        "evidence_only_not_recovery_authority_and_may_be_same_or_drift"
                    ),
                },
            },
            "phase_policy": PHASE_POLICY,
            "phase_classifier_audit": audit_topology_phase_classifier(),
            "candidate_timing_cross_check": audit_candidate_timing_cross_check(),
            "rollback_transfer_requires_state": (
                "rollback_bound_exact_for_normal_path_or_recovery_rebound_exact_"
                "under_fresh_reviewed_recovery_binding_id_after_drift"
            ),
            "drift_effective_proof_class": "NO_PROOF_EXPERIMENT_PRECONDITION",
            "widen_live_selector_on_drift": False,
            "open_unapproved_endpoint": False,
            "rollback_against_drifted_path_authorized": False,
            "park_without_new_effects_until_reestablished": True,
            "reestablishment": (
                "bounded_independently_reviewed_recovery_only_path_reestablishes_"
                "exact_current_endpoint_under_new_binding_id_for_predeclared_rollback"
            ),
            "recovery_binding_may_differ_from_start_path": True,
            "recovery_binding_never_reclassifies_experiment_result": True,
            "candidate_replay_forbidden": True,
            "physical_movement_machine_proven_by_path_mismatch": False,
        },
        "dtr_source_audit": dtr_audit,
        "causal_timing_boundary": {
            "candidate_enumeration_utc": enumeration_match.group("utc"),
            "sidecar_kernel_end_utc": sidecar_end_value,
            "capture_after_enumeration_sec": capture_after_enumeration_sec,
            "sidecar_capture_continued_after_candidate_enumeration": True,
            "usb_event_silence_after_enumeration_locates_post1_or_post2": False,
            "successor_requires_explicit_post1_or_post2_host_correlation": True,
        },
        "scope": {
            "p317_only": True,
            "prior_campaign_silence_reclassified": False,
            "effective_proof_class": "NO_PROOF_EXPERIMENT_PRECONDITION",
            "operator_physical_relocation_machine_proven": False,
            "banner_write_success_proven": False,
            "dtr_hypothesis_retained": False,
            "physical_mux_conduction_inferred_from_registers": False,
            "live_selector_wired": False,
            "observed_path_live_authority": False,
            "device_actions": 0,
        },
    }


def encode_contract(value: dict[str, Any]) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=repo_root())
    parser.add_argument("--prepared", type=Path, default=DEFAULT_PREPARED)
    parser.add_argument("--target-private", type=Path, default=DEFAULT_TARGET_PRIVATE)
    parser.add_argument("--observer-receipt", type=Path, default=DEFAULT_OBSERVER_RECEIPT)
    parser.add_argument("--sidecar-result", type=Path, default=DEFAULT_SIDECAR_RESULT)
    parser.add_argument("--kernel-log", type=Path, default=DEFAULT_KERNEL_LOG)
    parser.add_argument("--udev-log", type=Path, default=DEFAULT_UDEV_LOG)
    parser.add_argument("--observer-source", type=Path, default=DEFAULT_OBSERVER_SOURCE)
    parser.add_argument("--f-acm-source", type=Path, default=DEFAULT_F_ACM_SOURCE)
    parser.add_argument("--u-serial-source", type=Path, default=DEFAULT_U_SERIAL_SOURCE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.repo.resolve()

    def resolve(path: Path) -> Path:
        return path if path.is_absolute() else root / path

    extractor_path = Path(__file__).resolve()
    value = build_contract(
        prepared_data=stable_read(resolve(args.prepared), "P3.17 prepared", 2**24),
        target_data=stable_read(resolve(args.target_private), "P3.17 target", 2**16),
        observer_receipt_data=stable_read(
            resolve(args.observer_receipt), "P3.17 observer receipt", 2**20
        ),
        sidecar_result_data=stable_read(
            resolve(args.sidecar_result), "P3.17 sidecar result", 2**20
        ),
        kernel_data=stable_read(resolve(args.kernel_log), "P3.17 kernel log", 2**24),
        udev_data=stable_read(resolve(args.udev_log), "P3.17 udev log", 2**24),
        observer_source_data=stable_read(
            resolve(args.observer_source), "frozen CDC ACM observer", 2**20
        ),
        f_acm_data=stable_read(
            resolve(args.f_acm_source), "fixed f_acm source", 2**20
        ),
        u_serial_data=stable_read(
            resolve(args.u_serial_source), "fixed u_serial source", 2**20
        ),
        extractor_data=stable_read(extractor_path, "endpoint transition extractor", 2**20),
    )
    payload = encode_contract(value)
    if args.output is None:
        print(payload.decode(), end="")
    else:
        output = resolve(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
