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


SCHEMA = "s22plus_fyg8_p318_cdc_acm_topology_drift_v2"
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
TOPOLOGY_AUTHORITIES = ("approved_exact", "not_authorized", "reestablished_exact")
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
        if authority_state == "reestablished_exact":
            effect = values["contradiction"]
        elif not observation_complete or relationship == "unavailable":
            effect = values["observer"]
        elif relationship == "same" and authority_state == "approved_exact":
            effect = values["eligible"]
            candidate_eligible = True
        else:
            effect = values["stop"]
    elif phase == "candidate_end":
        values = policy[phase]
        park = True
        if authority_state == "reestablished_exact":
            effect = values["contradiction"]
            proof_class = "NO_PROOF_OBSERVER"
        elif not observation_complete or relationship == "unavailable":
            effect = values["observer"]
            proof_class = "NO_PROOF_OBSERVER"
        elif relationship in ("drift", "ambiguous"):
            effect = values["precondition"]
            proof_class = "NO_PROOF_EXPERIMENT_PRECONDITION"
        elif relationship == "absent":
            if causal_terminal_ready and authority_state == "approved_exact":
                effect = values["host_silent"]
                proof_class = "DEVICE_RESULT_HOST_SILENT"
                park = False
            else:
                effect = values["observer"]
                proof_class = "NO_PROOF_OBSERVER"
        elif authority_state == "approved_exact":
            effect = values["retain"]
            proof_class = "RETAIN_EXPERIMENT_TERMINAL"
            park = False
        else:
            effect = values["contradiction"]
            proof_class = "NO_PROOF_OBSERVER"
    else:
        values = policy[phase]
        if (
            authority_state == "reestablished_exact"
            and relationship in ("same", "drift")
            and observation_complete
        ):
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
        "experiment_proof_reclassified_by_rollback": False,
    }


def audit_topology_phase_classifier(
    policy: dict[str, dict[str, str]] = PHASE_POLICY,
) -> dict[str, Any]:
    expected_policy = {
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
    if policy != expected_policy:
        raise TransitionError("topology phase policy semantics differ")
    rows = [
        classify_topology_phase(
            phase=phase,
            relationship=relationship,
            authority_state=authority_state,
            observation_complete=observation_complete,
            causal_terminal_ready=causal_terminal_ready,
            policy=policy,
        )
        for phase, relationship, authority_state, observation_complete, causal_terminal_ready
        in itertools.product(
            TOPOLOGY_PHASES,
            TOPOLOGY_RELATIONSHIPS,
            TOPOLOGY_AUTHORITIES,
            (False, True),
            (False, True),
        )
    ]
    if len(rows) != 180 or len({digest(row) for row in rows}) != 180:
        raise TransitionError("topology phase classifier is not total and unique")
    if any(
        row["candidate_eligible"]
        for row in rows
        if row["phase"] == "download_start"
        and (
            row["relationship"] == "unavailable"
            or not row["observation_complete"]
        )
    ):
        raise TransitionError("download-start unavailable can arm a candidate")
    if any(
        row["effect"] == policy["candidate_end"]["retain"]
        for row in rows
        if row["phase"] == "candidate_end"
        and row["relationship"] in ("drift", "ambiguous")
    ):
        raise TransitionError("candidate drift can retain a normal terminal")
    rollback_rows = [row for row in rows if row["phase"] == "rollback_download"]
    if any(row["experiment_proof_reclassified_by_rollback"] for row in rollback_rows):
        raise TransitionError("rollback can reclassify experiment proof")
    if any(
        row["rollback_resume"]
        for row in rollback_rows
        if row["authority_state"] != "reestablished_exact"
    ):
        raise TransitionError("rollback can resume without recovery authority")
    if any(
        not row["park"]
        for row in rollback_rows
        if row["authority_state"] != "reestablished_exact"
    ):
        raise TransitionError("unapproved rollback row does not park")
    expected_resume = [
        row
        for row in rollback_rows
        if row["authority_state"] == "reestablished_exact"
        and row["relationship"] in ("same", "drift")
        and row["observation_complete"]
    ]
    if not expected_resume or any(not row["rollback_resume"] for row in expected_resume):
        raise TransitionError("reestablished rollback cannot resume")
    return {
        "domain_row_count": len(rows),
        "unique_row_count": len({digest(row) for row in rows}),
        "rows_sha256": digest(rows),
        "download_start_unavailable_never_eligible": True,
        "candidate_drift_never_retains_normal_terminal": True,
        "rollback_requires_reestablished_exact": True,
        "rollback_never_reclassifies_experiment": True,
        "all_non_reestablished_rollback_rows_park": True,
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
                "approved_exact",
                "not_authorized",
                "reestablished_exact",
            ],
            "phase_state_effects": {
                "download_start": {
                    "approved_exact": "pre_session_candidate_eligible",
                    "drift_absent_ambiguous": "pre_session_stop_no_run_proof_class",
                    "unavailable": "pre_session_observer_failure_no_attempt",
                },
                "candidate_end": {
                    "same_endpoint_present": "retain_experiment_terminal_classification",
                    "same_complete_absent_causal_ready": (
                        "retain_device_side_result_and_classify_host_silent_"
                        "under_experiment_contract"
                    ),
                    "drift_or_ambiguous": "NO_PROOF_EXPERIMENT_PRECONDITION_and_park",
                    "absent_without_complete_causal_ready": "NO_PROOF_OBSERVER_and_park",
                    "unavailable": "NO_PROOF_OBSERVER_and_park",
                },
                "rollback_download": {
                    "reestablished_exact": "rollback_may_resume_no_proof_reclassification",
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
            "rollback_transfer_requires_state": (
                "reestablished_exact_under_fresh_recovery_binding_id"
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
