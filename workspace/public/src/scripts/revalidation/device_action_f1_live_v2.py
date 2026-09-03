#!/usr/bin/env python3
"""Reusable attended boot-only F1 adapter for Device Action Process v2."""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import math
import os
import re
import select
import signal
import stat
import subprocess
import sys
import termios
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, ContextManager, Iterator, Mapping, Protocol

import device_action_d0_v2 as d0
import device_action_raw_capture_v1 as raw_capture
import device_action_cdc_acm_observer_v1 as cdc_acm_observer
import device_action_f1_evidence_v2 as typed_evidence
import consumed_candidate_registry_v1 as consumed_registry
import device_action_f1_v2 as core
import device_action_usb_trace_sidecar_v1 as usb_trace_sidecar
import s22plus_fyg8_p300_usb_trace_binding as p300_usb_trace
import s22plus_fyg8_p313_guard_lifetime as p313_guard_lifetime
import s22plus_fyg8_p318_topology_receipt as p318_topology
import s22plus_fyg8_p324_cdc_acm_observer as p324_cdc_observer
import s22plus_fyg8_p324_typec_lane_binding as p324_typec_lane
import s22plus_fyg8_p325_cdc_acm_guard_adapter as p325_guard_adapter
import s22plus_fyg8_p326_bidirectional_acm_observer as p326_console_observer
import s22plus_fyg8_p327_framed_acm_observer as p327_framed_observer
import s22plus_fyg8_p327_framed_exec_runtime as p327_framed_runtime
import s22plus_fyg8_p328_artifact_identity as p328_artifact_identity
import s22plus_fyg8_p328_auth_acm_observer as p328_auth_observer
import s22plus_fyg8_p328_auth_exec_runtime as p328_auth_runtime
import s22plus_fyg8_p328_stock_process_v2_adapter as p328_stock_adapter
import s22plus_fyg8_p329_artifact_identity as p329_artifact_identity
import s22plus_fyg8_p329_auth_acm_observer as p329_auth_observer
import s22plus_fyg8_p329_auth_exec_runtime as p329_auth_runtime
import s22plus_fyg8_p329_stock_process_v2_adapter as p329_stock_adapter
import s22plus_fyg8_p330_auth_acm_observer as p330_auth_observer
import s22plus_fyg8_p330_auth_exec_runtime as p330_auth_runtime
import s22plus_fyg8_p330_artifact_identity as p330_artifact_identity
import s22plus_fyg8_p331_resident_acm_observer as p331_resident_observer
import s22plus_fyg8_p331_resident_exec_runtime as p331_resident_runtime
import s22plus_fyg8_p331_artifact_identity as p331_artifact_identity
import s22plus_fyg8_p332_logical_resident_acm_observer as p332_logical_resident_observer
import s22plus_fyg8_p332_logical_resident_exec_runtime as p332_logical_resident_runtime
import s22plus_fyg8_p332_artifact_identity as p332_artifact_identity
import s22plus_fyg8_p333_open_entry_diag_acm_observer as p333_open_entry_observer
import s22plus_fyg8_p333_open_entry_diag_runtime as p333_open_entry_runtime
import s22plus_fyg8_p333_artifact_identity as p333_artifact_identity
import s22plus_fyg8_p334_first_read_rc_acm_observer as p334_first_read_observer
import s22plus_fyg8_p334_first_read_rc_runtime as p334_first_read_runtime
import s22plus_fyg8_p334_artifact_identity as p334_artifact_identity
import s22plus_fyg8_p335_retained_listener_acm_observer as p335_retained_observer
import s22plus_fyg8_p335_retained_listener_runtime as p335_retained_runtime
import s22plus_fyg8_p335_artifact_identity as p335_artifact_identity
import s22plus_fyg8_p335_resident_session as p335_resident_session
import s22plus_boot_only_f1_transport as transport
import s22plus_boot_only_live_core as live_core
import s22plus_odin_transition_core as odin_core
import s22plus_odin_usbfs_identity as usbfs_identity


ADAPTER_VERSION = "device-action-f1-live-v2-9"
PREPARED_SCHEMA = "device_action_f1_prepared_v2"
PRIVATE_TARGET_SCHEMA = "device_action_f1_private_target_v2"
LIVE_STATE_SCHEMA = "device_action_f1_live_state_v2"
LIVE_RESULT_SCHEMA = "device_action_f1_live_result_v2"
APPROVAL_PREFIX = "DEVICE-ACTION-F1-V2-APPROVE:"
DEFAULT_RUN_ROOT = Path("workspace/private/runs/device-action-f1-live-v2")
DEFAULT_USB_ROOT = Path("/sys/bus/usb/devices")
DEFAULT_TYPEC_ROOT = Path("/sys/class/typec")
MAX_PRIVATE_JSON = 1024 * 1024
MAX_ODIN_OUTPUT = 8 * 1024 * 1024
MAX_OBSERVER_BYTES = 64 * 1024 * 1024
MAX_ATTEMPTS = 2
DOWNLOAD_REQUEST_TIMEOUT_SEC = 20
DOWNLOAD_WAIT_SEC = 180
ROLLBACK_WAIT_SEC = 600
ANDROID_WAIT_SEC = 420
DISCONNECT_WAIT_SEC = 120
ODIN_TIMEOUT_SEC = 240
ENDPOINT_REVALIDATE_SEC = 20
NON_TAINTING_GUARD_WARNINGS = {
    "guard-expired",
    "guard-exited-uncommanded",
}
P300_PROCESS_OWNER_SCHEMA = "s22plus_fyg8_p300_usb_trace_process_owner_v1"
P300_PROCESS_CLEANUP_SCHEMA = "s22plus_fyg8_p300_usb_trace_process_cleanup_v1"
P300_OWNER_ARM_TIMEOUT_SEC = 2.0
P300_OWNER_ARM_POLL_SEC = 0.01
P300_PROCESS_WAIT_SEC = 10.0
DOWNLOAD_REQUEST_INTENT_SCHEMA = "device_action_f1_download_request_intent_v2"
DOWNLOAD_REQUEST_RECOVERY_ACTIONS = {
    "download_request_cut_recovery_exact",
    "download_request_cut_recovery_parked",
}
P319_OUTCOME_BY_PROOF_CLASS = {
    "NONCAUSAL_SUCCESS_PATH": "p319_noncausal_success_path_rollback_verified",
    "NO_PROOF_EXPERIMENT_PRECONDITION": "p319_experiment_precondition_unproved_rollback_verified",
    "NO_PROOF_OBSERVER": "p319_observer_no_proof_rollback_verified",
}
P320_OUTCOME_BY_PROOF_CLASS = {
    "NONCAUSAL_SUCCESS_PATH": "p320_noncausal_success_path_rollback_verified",
    "NO_PROOF_EXPERIMENT_PRECONDITION": "p320_experiment_precondition_unproved_rollback_verified",
    "NO_PROOF_OBSERVER": "p320_observer_no_proof_rollback_verified",
}
P321_OUTCOME_BY_PROOF_CLASS = {
    "NONCAUSAL_SUCCESS_PATH": "p321_noncausal_success_path_rollback_verified",
    "NO_PROOF_EXPERIMENT_PRECONDITION": "p321_experiment_precondition_unproved_rollback_verified",
    "NO_PROOF_OBSERVER": "p321_observer_no_proof_rollback_verified",
}
P322_OUTCOME_BY_PROOF_CLASS = {
    "NONCAUSAL_SUCCESS_PATH": "p322_noncausal_success_path_rollback_verified",
    "NO_PROOF_EXPERIMENT_PRECONDITION": "p322_experiment_precondition_unproved_rollback_verified",
    "NO_PROOF_OBSERVER": "p322_observer_no_proof_rollback_verified",
}
P325_OUTCOME_BY_PROOF_CLASS = {
    "NONCAUSAL_SUCCESS_PATH": "p325_noncausal_success_path_rollback_verified",
    "NO_PROOF_EXPERIMENT_PRECONDITION": "p325_experiment_precondition_unproved_rollback_verified",
    "NO_PROOF_OBSERVER": "p325_observer_no_proof_rollback_verified",
}
P326_OUTCOME_BY_PROOF_CLASS = {
    "NONCAUSAL_SUCCESS_PATH": "p326_noncausal_success_path_rollback_verified",
    "NO_PROOF_EXPERIMENT_PRECONDITION": "p326_experiment_precondition_unproved_rollback_verified",
    "NO_PROOF_OBSERVER": "p326_observer_no_proof_rollback_verified",
}
P327_OUTCOME_BY_PROOF_CLASS = {
    "NONCAUSAL_SUCCESS_PATH": "p327_noncausal_success_path_rollback_verified",
    "NO_PROOF_EXPERIMENT_PRECONDITION": "p327_experiment_precondition_unproved_rollback_verified",
    "NO_PROOF_OBSERVER": "p327_observer_no_proof_rollback_verified",
}
P328_AUTH_KEY_PATH = p328_artifact_identity.DEFAULT_AUTH_KEY_PATH
P328_AUTH_KEY_IDENTITY = dict(typed_evidence.P328_AUTH_EXEC_AUTH_KEY_IDENTITY)
P328_OBSERVER_RECEIPT_SCHEMA = "s22plus_fyg8_p328_auth_acm_receipt_v1"
P328_MAX_RAW_BYTES = 512 * 1024
P328_CLASSIFICATIONS = {
    "accepted",
    "endpoint-timeout",
    "endpoint-ambiguous",
    "identity-mismatch",
    "open-failed",
    "exclusive-failed",
    "guard-lost",
    "read-timeout",
    "extra-byte",
    "authenticated-session-error",
}
P328_SUCCESS_VERDICT = typed_evidence.P328_AUTH_EXEC_VERDICT
P328_SUCCESS_OUTCOME = typed_evidence.P328_AUTH_EXEC_OUTCOME
P328_NO_PROOF_OUTCOME = typed_evidence.P328_AUTH_EXEC_NO_PROOF_OUTCOME
P329_OBSERVER_RECEIPT_SCHEMA = "s22plus_fyg8_p329_auth_acm_receipt_v1"
P329_UDEV_SETTLE_SEC = 0.5
P329_UDEV_SETTLE_POLL_SEC = 0.025
P329_CLASSIFICATIONS = P328_CLASSIFICATIONS | {"guard-property-timeout"}
P329_SUCCESS_VERDICT = typed_evidence.P329_AUTH_EXEC_VERDICT
P329_SUCCESS_OUTCOME = typed_evidence.P329_AUTH_EXEC_OUTCOME
P329_NO_PROOF_OUTCOME = typed_evidence.P329_AUTH_EXEC_NO_PROOF_OUTCOME
P330_OBSERVER_RECEIPT_SCHEMA = "s22plus_fyg8_p330_auth_acm_receipt_v1"
P330_CLASSIFICATIONS = set(P329_CLASSIFICATIONS)
P330_SUCCESS_VERDICT = typed_evidence.P330_AUTH_EXEC_VERDICT
P330_SUCCESS_OUTCOME = typed_evidence.P330_AUTH_EXEC_OUTCOME
P330_NO_PROOF_OUTCOME = typed_evidence.P330_AUTH_EXEC_NO_PROOF_OUTCOME
P331_OBSERVER_RECEIPT_SCHEMA = "s22plus_fyg8_p331_resident_acm_receipt_v1"
P331_CLASSIFICATIONS = set(P330_CLASSIFICATIONS)
P331_SUCCESS_VERDICT = typed_evidence.P331_AUTH_EXEC_VERDICT
P331_SUCCESS_OUTCOME = typed_evidence.P331_AUTH_EXEC_OUTCOME
P331_NO_PROOF_OUTCOME = typed_evidence.P331_AUTH_EXEC_NO_PROOF_OUTCOME
P332_OBSERVER_RECEIPT_SCHEMA = "s22plus_fyg8_p332_logical_resident_acm_receipt_v1"
P332_CLASSIFICATIONS = set(P330_CLASSIFICATIONS)
P332_SUCCESS_VERDICT = typed_evidence.P332_AUTH_EXEC_VERDICT
P332_SUCCESS_OUTCOME = typed_evidence.P332_AUTH_EXEC_OUTCOME
P332_NO_PROOF_OUTCOME = typed_evidence.P332_AUTH_EXEC_NO_PROOF_OUTCOME
P333_OBSERVER_RECEIPT_SCHEMA = "s22plus_fyg8_p333_open_entry_diag_acm_receipt_v1"
P333_CLASSIFICATIONS = set(P332_CLASSIFICATIONS)
P333_SUCCESS_VERDICT = typed_evidence.P333_AUTH_EXEC_VERDICT
P333_SUCCESS_OUTCOME = typed_evidence.P333_AUTH_EXEC_OUTCOME
P333_NO_PROOF_OUTCOME = typed_evidence.P333_AUTH_EXEC_NO_PROOF_OUTCOME
P334_OBSERVER_RECEIPT_SCHEMA = "s22plus_fyg8_p334_first_read_rc_acm_receipt_v1"
P334_CLASSIFICATIONS = set(P333_CLASSIFICATIONS)
P334_SUCCESS_VERDICT = typed_evidence.P334_AUTH_EXEC_VERDICT
P334_SUCCESS_OUTCOME = typed_evidence.P334_AUTH_EXEC_OUTCOME
P334_NO_PROOF_OUTCOME = typed_evidence.P334_AUTH_EXEC_NO_PROOF_OUTCOME
P335_OBSERVER_RECEIPT_SCHEMA = "s22plus_fyg8_p335_retained_listener_acm_receipt_v1"
P335_CLASSIFICATIONS = set(P334_CLASSIFICATIONS)
P335_SUCCESS_VERDICT = typed_evidence.P335_AUTH_EXEC_VERDICT
P335_SUCCESS_OUTCOME = typed_evidence.P335_AUTH_EXEC_OUTCOME
P335_NO_PROOF_OUTCOME = typed_evidence.P335_AUTH_EXEC_NO_PROOF_OUTCOME
MAX_LIVE_RESULT_RECORD = core.MAX_RESULT_RECORD


def _p323_stock_error(payload: bytes, error: BaseException) -> dict[str, Any]:
    """Retain a Carrier parser fault without making it an ACM fault."""
    detail = f"{type(error).__name__}:{error}".encode("utf-8", "replace")
    return {
        "schema": "device_action_f1_p323_stock_error_v1",
        "classification": "P323_STOCK_PARSER_EXCEPTION",
        "supplemental": True,
        "accepted": False,
        "candidate_success": False,
        "causal_result_allowed": False,
        "payload_bytes": len(payload),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "error_type": type(error).__name__,
        "error_sha256": hashlib.sha256(detail).hexdigest(),
    }


def _p323_parser_failure_classification(
    payload: bytes, error: BaseException
) -> dict[str, Any]:
    diagnostic = _p323_stock_error(payload, error)
    return {
        "classification": diagnostic["classification"],
        "accepted": False,
        "integrity_issue": True,
        "integrity_issues": ["p323-stock-parser-exception"],
        "exact_count": 0,
        "family_count": 0,
        "foreign_count": 0,
        "p323_stock_error": diagnostic,
    }


def _p324_stock_error(payload: bytes, error: BaseException) -> dict[str, Any]:
    detail = f"{type(error).__name__}:{error}".encode("utf-8", "replace")
    return {
        "schema": "device_action_f1_p324_stock_error_v1",
        "classification": "P324_STOCK_PARSER_EXCEPTION",
        "supplemental": True,
        "accepted": False,
        "candidate_success": False,
        "causal_result_allowed": False,
        "payload_bytes": len(payload),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "error_type": type(error).__name__,
        "error_sha256": hashlib.sha256(detail).hexdigest(),
    }


def _p324_parser_failure_classification(
    payload: bytes, error: BaseException
) -> dict[str, Any]:
    diagnostic = _p324_stock_error(payload, error)
    return {
        "classification": diagnostic["classification"],
        "accepted": False,
        "integrity_issue": True,
        "integrity_issues": ["p324-stock-parser-exception"],
        "exact_count": 0,
        "family_count": 0,
        "foreign_count": 0,
        "p324_stock_error": diagnostic,
    }


def _p325_stock_error(payload: bytes, error: BaseException) -> dict[str, Any]:
    detail = f"{type(error).__name__}:{error}".encode("utf-8", "replace")
    return {
        "schema": "device_action_f1_p325_stock_error_v1",
        "classification": "P325_STOCK_PARSER_EXCEPTION",
        "supplemental": True,
        "accepted": False,
        "candidate_success": False,
        "causal_result_allowed": False,
        "payload_bytes": len(payload),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "error_type": type(error).__name__,
        "error_sha256": hashlib.sha256(detail).hexdigest(),
    }


def _p325_parser_failure_classification(
    payload: bytes, error: BaseException
) -> dict[str, Any]:
    diagnostic = _p325_stock_error(payload, error)
    return {
        "classification": diagnostic["classification"],
        "accepted": False,
        "integrity_issue": True,
        "integrity_issues": ["p325-stock-parser-exception"],
        "exact_count": 0,
        "family_count": 0,
        "foreign_count": 0,
        "p325_stock_error": diagnostic,
    }


def _p326_stock_error(payload: bytes, error: BaseException) -> dict[str, Any]:
    detail = f"{type(error).__name__}:{error}".encode("utf-8", "replace")
    return {
        "schema": "device_action_f1_p326_stock_error_v1",
        "classification": "P326_STOCK_PARSER_EXCEPTION",
        "supplemental": True,
        "accepted": False,
        "candidate_success": False,
        "causal_result_allowed": False,
        "payload_bytes": len(payload),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "error_type": type(error).__name__,
        "error_sha256": hashlib.sha256(detail).hexdigest(),
    }


def _p326_parser_failure_classification(
    payload: bytes, error: BaseException
) -> dict[str, Any]:
    diagnostic = _p326_stock_error(payload, error)
    return {
        "classification": diagnostic["classification"],
        "accepted": False,
        "integrity_issue": True,
        "integrity_issues": ["p326-stock-parser-exception"],
        "exact_count": 0,
        "family_count": 0,
        "foreign_count": 0,
        "p326_stock_error": diagnostic,
    }


def _p327_stock_error(payload: bytes, error: BaseException) -> dict[str, Any]:
    """Retain a P327 Carrier parser fault without weakening ACM proof."""
    detail = f"{type(error).__name__}:{error}".encode("utf-8", "replace")
    return {
        "schema": "device_action_f1_p327_stock_error_v1",
        "classification": "P327_STOCK_PARSER_EXCEPTION",
        "supplemental": True,
        "accepted": False,
        "candidate_success": False,
        "causal_result_allowed": False,
        "payload_bytes": len(payload),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "error_type": type(error).__name__,
        "error_sha256": hashlib.sha256(detail).hexdigest(),
    }


def _p327_parser_failure_classification(
    payload: bytes, error: BaseException
) -> dict[str, Any]:
    diagnostic = _p327_stock_error(payload, error)
    return {
        "classification": diagnostic["classification"],
        "integrity_issue": True,
        "integrity_issues": ["p327-stock-parser-exception"],
        "exact_count": 0,
        "family_count": 0,
        "foreign_count": 0,
        "p327_stock_error": diagnostic,
        "accepted": False,
    }


def _p328_stock_error(payload: bytes, error: BaseException) -> dict[str, Any]:
    """Retain a P328 Carrier parser fault as supplemental evidence."""
    detail = f"{type(error).__name__}:{error}".encode("utf-8", "replace")
    return {
        "schema": "device_action_f1_p328_stock_error_v1",
        "classification": "P328_STOCK_PARSER_EXCEPTION",
        "supplemental": True,
        "accepted": False,
        "candidate_success": False,
        "causal_result_allowed": False,
        "payload_bytes": len(payload),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "error_type": type(error).__name__,
        "error_sha256": hashlib.sha256(detail).hexdigest(),
    }


def _p328_parser_failure_classification(
    payload: bytes, error: BaseException
) -> dict[str, Any]:
    diagnostic = _p328_stock_error(payload, error)
    return {
        "classification": diagnostic["classification"],
        "integrity_issue": True,
        "integrity_issues": ["p328-stock-parser-exception"],
        "exact_count": 0,
        "family_count": 0,
        "foreign_count": 0,
        "p328_stock_error": diagnostic,
        "accepted": False,
    }


def _p329_stock_error(payload: bytes, error: BaseException) -> dict[str, Any]:
    value = _p328_stock_error(payload, error)
    value.update(
        {
            "schema": "device_action_f1_p329_stock_error_v1",
            "classification": "P329_STOCK_PARSER_EXCEPTION",
        }
    )
    return value


def _p329_parser_failure_classification(
    payload: bytes, error: BaseException
) -> dict[str, Any]:
    diagnostic = _p329_stock_error(payload, error)
    return {
        "classification": diagnostic["classification"],
        "integrity_issue": True,
        "integrity_issues": ["p329-stock-parser-exception"],
        "exact_count": 0,
        "family_count": 0,
        "foreign_count": 0,
        "p329_stock_error": diagnostic,
        "accepted": False,
    }


def _p330_stock_error(payload: bytes, error: BaseException) -> dict[str, Any]:
    value = _p328_stock_error(payload, error)
    value.update(
        {
            "schema": "device_action_f1_p330_stock_error_v1",
            "classification": "P330_STOCK_PARSER_EXCEPTION",
        }
    )
    return value


def _p330_parser_failure_classification(
    payload: bytes, error: BaseException
) -> dict[str, Any]:
    diagnostic = _p330_stock_error(payload, error)
    return {
        "classification": diagnostic["classification"],
        "integrity_issue": True,
        "integrity_issues": ["p330-stock-parser-exception"],
        "exact_count": 0,
        "family_count": 0,
        "foreign_count": 0,
        "p330_stock_error": diagnostic,
        "accepted": False,
    }


def _p331_stock_error(payload: bytes, error: BaseException) -> dict[str, Any]:
    value = _p328_stock_error(payload, error)
    value.update(
        {
            "schema": "device_action_f1_p331_stock_error_v1",
            "classification": "P331_STOCK_PARSER_EXCEPTION",
        }
    )
    return value


def _p331_parser_failure_classification(
    payload: bytes, error: BaseException
) -> dict[str, Any]:
    diagnostic = _p331_stock_error(payload, error)
    return {
        "classification": diagnostic["classification"],
        "integrity_issue": True,
        "integrity_issues": ["p331-stock-parser-exception"],
        "exact_count": 0,
        "family_count": 0,
        "foreign_count": 0,
        "p331_stock_error": diagnostic,
        "accepted": False,
    }


def _p332_stock_error(payload: bytes, error: BaseException) -> dict[str, Any]:
    value = _p328_stock_error(payload, error)
    value.update(
        {
            "schema": "device_action_f1_p332_stock_error_v1",
            "classification": "P332_STOCK_PARSER_EXCEPTION",
        }
    )
    return value


def _p332_parser_failure_classification(
    payload: bytes, error: BaseException
) -> dict[str, Any]:
    diagnostic = _p332_stock_error(payload, error)
    return {
        "classification": diagnostic["classification"],
        "integrity_issue": True,
        "integrity_issues": ["p332-stock-parser-exception"],
        "exact_count": 0,
        "family_count": 0,
        "foreign_count": 0,
        "p332_stock_error": diagnostic,
        "accepted": False,
    }


def _p333_stock_error(payload: bytes, error: BaseException) -> dict[str, Any]:
    value = _p328_stock_error(payload, error)
    value.update(
        {
            "schema": "device_action_f1_p333_stock_error_v1",
            "classification": "P333_STOCK_PARSER_EXCEPTION",
        }
    )
    return value


def _p333_parser_failure_classification(
    payload: bytes, error: BaseException
) -> dict[str, Any]:
    diagnostic = _p333_stock_error(payload, error)
    return {
        "classification": diagnostic["classification"],
        "integrity_issue": True,
        "integrity_issues": ["p333-stock-parser-exception"],
        "exact_count": 0,
        "family_count": 0,
        "foreign_count": 0,
        "p333_stock_error": diagnostic,
        "accepted": False,
    }


def _p334_stock_error(payload: bytes, error: BaseException) -> dict[str, Any]:
    value = _p328_stock_error(payload, error)
    value.update(
        {
            "schema": "device_action_f1_p334_stock_error_v1",
            "classification": "P334_STOCK_PARSER_EXCEPTION",
        }
    )
    return value


def _p334_parser_failure_classification(
    payload: bytes, error: BaseException
) -> dict[str, Any]:
    diagnostic = _p334_stock_error(payload, error)
    return {
        "classification": diagnostic["classification"],
        "integrity_issue": True,
        "integrity_issues": ["p334-stock-parser-exception"],
        "exact_count": 0,
        "family_count": 0,
        "foreign_count": 0,
        "p334_stock_error": diagnostic,
        "accepted": False,
    }


def _p335_stock_error(payload: bytes, error: BaseException) -> dict[str, Any]:
    value = _p334_stock_error(payload, error)
    value.update(
        {
            "schema": "device_action_f1_p335_stock_error_v1",
            "classification": "P335_STOCK_PARSER_EXCEPTION",
        }
    )
    return value


def _p335_parser_failure_classification(
    payload: bytes, error: BaseException
) -> dict[str, Any]:
    diagnostic = _p335_stock_error(payload, error)
    return {
        "classification": diagnostic["classification"],
        "integrity_issue": True,
        "integrity_issues": ["p335-stock-parser-exception"],
        "exact_count": 0,
        "family_count": 0,
        "foreign_count": 0,
        "p335_stock_error": diagnostic,
        "accepted": False,
    }


class F1LiveError(RuntimeError):
    pass


class P318TopologyPark(F1LiveError):
    """A durable P3.18 topology receipt forbids the next transfer."""


@dataclass(frozen=True)
class PreparedRun:
    root: Path
    run_dir: Path
    bundle: core.Bundle
    prepared: dict[str, Any]
    private_target: dict[str, str]

    @property
    def binding_sha256(self) -> str:
        return str(self.prepared["approval_binding_sha256"])

    @property
    def approval_token(self) -> str:
        return APPROVAL_PREFIX + self.binding_sha256


@dataclass(frozen=True)
class Endpoint:
    device: str
    sequence: int
    identity_sha256: str


@dataclass(frozen=True)
class TransferOutcome:
    classification: str
    completed: bool
    possible_device_session: bool
    receipt: dict[str, Any]


class LiveBackend(Protocol):
    def recheck_android(
        self, prepared: PreparedRun, destination: Path
    ) -> dict[str, Any]: ...

    def request_download(self, prepared: PreparedRun) -> None: ...

    def endpoint_session(self, run_dir: Path) -> ContextManager[Any]: ...

    def candidate_observer_session(
        self, prepared: PreparedRun
    ) -> ContextManager[Any]: ...

    def wait_download(
        self,
        prepared: PreparedRun,
        run_dir: Path,
        lease: Any,
        timeout_sec: float,
    ) -> Endpoint: ...

    def revalidate_candidate_lane(self, prepared: PreparedRun) -> None: ...

    def transfer(
        self,
        prepared: PreparedRun,
        endpoint: Endpoint,
        kind: str,
        destination: Path,
        attempt: int,
        prefix: str,
    ) -> TransferOutcome: ...

    def observe_candidate(
        self,
        prepared: PreparedRun,
        run_dir: Path,
        lease: Any,
        observer_session: Any,
    ) -> dict[str, Any]: ...

    def verify_final(
        self,
        prepared: PreparedRun,
        run_dir: Path,
        lease: Any,
        destination: Path,
    ) -> dict[str, Any]: ...


def _receipt(path: Path, label: str, maximum: int = MAX_PRIVATE_JSON) -> dict[str, Any]:
    payload, value = core._stable_read(path, label, maximum)
    return {**value, "sha256": hashlib.sha256(payload).hexdigest()}


def _read_json(path: Path, label: str) -> dict[str, Any]:
    payload, _value = core._stable_read(path, label, MAX_PRIVATE_JSON)
    try:
        parsed = json.loads(payload, object_pairs_hook=core._unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise F1LiveError(f"{label} is not canonical JSON") from exc
    if not isinstance(parsed, dict):
        raise F1LiveError(f"{label} must be an object")
    return parsed


def _write_exclusive(path: Path, value: Any) -> None:
    try:
        core._write_exclusive(path, value)
    except core.F1V2Error as exc:
        raise F1LiveError(str(exc)) from exc


def _write_atomic(path: Path, value: Any) -> None:
    try:
        core._write_atomic(path, value)
    except core.F1V2Error as exc:
        raise F1LiveError(str(exc)) from exc


def _write_live_result(path: Path, value: Any) -> None:
    try:
        core._write_live_result(path, value)
    except core.F1V2Error as exc:
        raise F1LiveError(str(exc)) from exc


def _closure(root: Path, bundle: core.Bundle | None = None) -> dict[str, Any]:
    scripts = Path(__file__).resolve().parent
    paths = {
        "adapter": Path(__file__).resolve(),
        "cdc_acm_observer": Path(cdc_acm_observer.__file__).resolve(),
        "raw_capture": scripts / "device_action_raw_capture_v1.py",
        "usb_trace_sidecar": Path(usb_trace_sidecar.__file__).resolve(),
        "p300_usb_trace_binding": Path(p300_usb_trace.__file__).resolve(),
        "f1_core": scripts / "device_action_f1_v2.py",
        "typed_evidence": scripts / "device_action_f1_evidence_v2.py",
        "checkpoint_decoder": scripts / "s22plus_fyg8_r4w1e_checkpoint_contract.py",
        "d0_adapter": scripts / "device_action_d0_v2.py",
        "regular_path_transport": scripts / "s22plus_boot_only_f1_transport.py",
        "live_core": scripts / "s22plus_boot_only_live_core.py",
        "odin_transition_core": scripts / "s22plus_odin_transition_core.py",
        "usbfs_identity": scripts / "s22plus_odin_usbfs_identity.py",
        "p313_guard_lifetime": scripts / "s22plus_fyg8_p313_guard_lifetime.py",
        "p319_stock_adapter": Path(
            typed_evidence.p319_stock_adapter.__file__
        ).resolve(),
        "p319_carrier_model": Path(
            typed_evidence.p319_stock_adapter.model.__file__
        ).resolve(),
        "p319_telemetry_spec": Path(
            typed_evidence.p319_stock_adapter.spec.__file__
        ).resolve(),
        "consumed_candidate_registry": Path(consumed_registry.__file__).resolve(),
        "legacy_consumed_candidate_authority": Path(consumed_registry.LEGACY_AUTHORITY_PATH).resolve(),
    }
    if bundle is not None and (
        _p320_bundle(bundle)
        or _p321_bundle(bundle)
        or _p322_bundle(bundle)
        or _p323_bundle(bundle)
        or _p324_bundle(bundle)
        or _p325_bundle(bundle)
        or _p327_bundle(bundle)
        or _p326_bundle(bundle)
        or _p328_bundle(bundle)
        or _p332_bundle(bundle)
        or _p333_bundle(bundle)
        or _p334_bundle(bundle)
        or _p335_bundle(bundle)
    ):
        stock_adapter = typed_evidence.STOCK_ADAPTERS[
            _userspace_overlay_contract_id(bundle)
        ]
        prefix = (
            "p335"
            if _p335_bundle(bundle)
            else "p334"
            if _p334_bundle(bundle)
            else "p333"
            if _p333_bundle(bundle)
            else "p332"
            if _p332_bundle(bundle)
            else "p331"
            if _p331_bundle(bundle)
            else "p330"
            if _p330_bundle(bundle)
            else "p329"
            if _p329_bundle(bundle)
            else "p328"
            if _p328_bundle(bundle)
            else "p327"
            if _p327_bundle(bundle)
            else "p326"
            if _p326_bundle(bundle)
            else "p325"
            if _p325_bundle(bundle)
            else
            "p324"
            if _p324_bundle(bundle)
            else "p323"
            if _p323_bundle(bundle)
            else "p322"
            if _p322_bundle(bundle)
            else (
                "p321"
                if _p321_bundle(bundle)
                else "p320"
            )
        )
        paths.update(
            {
                f"{prefix}_stock_adapter": Path(stock_adapter.__file__).resolve(),
                f"{prefix}_carrier_model": Path(stock_adapter.model.__file__).resolve(),
                f"{prefix}_telemetry_spec": Path(stock_adapter.spec.__file__).resolve(),
                f"{prefix}_observer_contract": Path(
                    stock_adapter.P320_OBSERVER_SOURCE
                ).resolve(),
            }
        )
    candidate_arrival_role = (
        bundle.manifest["observation"].get(
            typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY
        )
        if bundle is not None
        else None
    )
    if candidate_arrival_role is not None:
        try:
            typed_evidence.validate_candidate_arrival_proof_role(
                candidate_arrival_role,
                bundle.manifest["observation"].get("candidate_observer"),
                expected_run_id=bundle.manifest["observation"]["acceptance"].get(
                    "run_id"
                ),
            )
        except typed_evidence.EvidenceError as exc:
            raise F1LiveError(str(exc)) from exc
        if _p328_bundle(bundle):
            auth_prefix = (
                "p335"
                if _p335_bundle(bundle)
                else "p334"
                if _p334_bundle(bundle)
                else "p333"
                if _p333_bundle(bundle)
                else "p332"
                if _p332_bundle(bundle)
                else "p331"
                if _p331_bundle(bundle)
                else "p330"
                if _p330_bundle(bundle)
                else "p329"
                if _p329_bundle(bundle)
                else "p328"
            )
            artifact_module = (
                p335_artifact_identity
                if _p335_bundle(bundle)
                else p334_artifact_identity
                if _p334_bundle(bundle)
                else p333_artifact_identity
                if _p333_bundle(bundle)
                else p332_artifact_identity
                if _p332_bundle(bundle)
                else p331_artifact_identity
                if _p331_bundle(bundle)
                else p330_artifact_identity
                if _p330_bundle(bundle)
                else p329_artifact_identity
                if _p329_bundle(bundle)
                else p328_artifact_identity
            )
            runtime_module = (
                p335_retained_runtime
                if _p335_bundle(bundle)
                else p334_first_read_runtime
                if _p334_bundle(bundle)
                else p333_open_entry_runtime
                if _p333_bundle(bundle)
                else p332_logical_resident_runtime
                if _p332_bundle(bundle)
                else p331_resident_runtime
                if _p331_bundle(bundle)
                else p330_auth_runtime
                if _p330_bundle(bundle)
                else p329_auth_runtime
                if _p329_bundle(bundle)
                else p328_auth_runtime
            )
            observer_module = (
                p335_retained_observer
                if _p335_bundle(bundle)
                else p334_first_read_observer
                if _p334_bundle(bundle)
                else p333_open_entry_observer
                if _p333_bundle(bundle)
                else p332_logical_resident_observer
                if _p332_bundle(bundle)
                else p331_resident_observer
                if _p331_bundle(bundle)
                else p330_auth_observer
                if _p330_bundle(bundle)
                else p329_auth_observer
                if _p329_bundle(bundle)
                else p328_auth_observer
            )
            paths[f"{auth_prefix}_artifact_identity"] = Path(
                artifact_module.__file__
            ).resolve()
            paths[f"{auth_prefix}_auth_exec_runtime"] = Path(
                runtime_module.__file__
            ).resolve()
            paths[f"{auth_prefix}_auth_acm_observer"] = Path(
                observer_module.__file__
            ).resolve()
            if _p335_bundle(bundle):
                paths["p335_resident_session"] = Path(
                    p335_resident_session.__file__
                ).resolve()
            paths["p326_bidirectional_console_runtime"] = scripts / (
                "s22plus_fyg8_p326_bidirectional_console_runtime.py"
            )
            paths["p324_typec_lane_binding"] = Path(
                p324_typec_lane.__file__
            ).resolve()
            paths["p324_cdc_acm_observer"] = Path(
                p324_cdc_observer.__file__
            ).resolve()
            paths["p325_cdc_acm_guard_adapter"] = Path(
                p325_guard_adapter.__file__
            ).resolve()
            paths["p326_bidirectional_acm_observer"] = Path(
                p326_console_observer.__file__
            ).resolve()
        elif _p327_bundle(bundle):
            paths["p327_framed_exec_runtime"] = Path(
                p327_framed_runtime.__file__
            ).resolve()
            paths["p327_framed_acm_observer"] = Path(
                p327_framed_observer.__file__
            ).resolve()
            paths["p326_bidirectional_console_runtime"] = scripts / (
                "s22plus_fyg8_p326_bidirectional_console_runtime.py"
            )
            paths["p324_typec_lane_binding"] = Path(
                p324_typec_lane.__file__
            ).resolve()
            paths["p324_cdc_acm_observer"] = Path(
                p324_cdc_observer.__file__
            ).resolve()
            paths["p325_cdc_acm_guard_adapter"] = Path(
                p325_guard_adapter.__file__
            ).resolve()
            paths["p326_bidirectional_acm_observer"] = Path(
                p326_console_observer.__file__
            ).resolve()
        elif _p326_bundle(bundle):
            paths["p326_bidirectional_console_runtime"] = scripts / (
                "s22plus_fyg8_p326_bidirectional_console_runtime.py"
            )
            paths["p324_typec_lane_binding"] = Path(
                p324_typec_lane.__file__
            ).resolve()
            paths["p324_cdc_acm_observer"] = Path(
                p324_cdc_observer.__file__
            ).resolve()
            paths["p325_cdc_acm_guard_adapter"] = Path(
                p325_guard_adapter.__file__
            ).resolve()
            paths["p326_bidirectional_acm_observer"] = Path(
                p326_console_observer.__file__
            ).resolve()
        elif _p325_bundle(bundle):
            paths["p324_acm_primary_runtime"] = scripts / (
                "s22plus_fyg8_p324_acm_primary_runtime.py"
            )
            paths["p324_typec_lane_binding"] = Path(
                p324_typec_lane.__file__
            ).resolve()
            paths["p324_cdc_acm_observer"] = Path(
                p324_cdc_observer.__file__
            ).resolve()
            paths["p325_cdc_acm_guard_adapter"] = Path(
                p325_guard_adapter.__file__
            ).resolve()
        elif _p324_bundle(bundle):
            paths["p324_acm_primary_runtime"] = scripts / (
                "s22plus_fyg8_p324_acm_primary_runtime.py"
            )
            paths["p324_typec_lane_binding"] = Path(
                p324_typec_lane.__file__
            ).resolve()
            paths["p324_cdc_acm_observer"] = Path(
                p324_cdc_observer.__file__
            ).resolve()
        else:
            paths["p323_acm_primary_runtime"] = scripts / (
                "s22plus_fyg8_p323_acm_primary_runtime.py"
            )
            paths["p323_predecessor_baseline"] = Path(
                typed_evidence.p323_predecessor_baseline.__file__
            ).resolve()
    values = {
        name: _receipt(path.resolve(), f"execution source {name}")
        for name, path in paths.items()
    }
    closure = {
        "schema": "device_action_f1_execution_closure_v2",
        "sources": values,
        "sha256": core.json_sha256(values),
        "repo_root": str(root),
    }
    if candidate_arrival_role is not None:
        closure[typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY] = (
            candidate_arrival_role
        )
        if _p328_bundle(bundle):
            auth_prefix = (
                "p335"
                if _p335_bundle(bundle)
                else "p334"
                if _p334_bundle(bundle)
                else "p333"
                if _p333_bundle(bundle)
                else "p332"
                if _p332_bundle(bundle)
                else "p331"
                if _p331_bundle(bundle)
                else "p330"
                if _p330_bundle(bundle)
                else "p329"
                if _p329_bundle(bundle)
                else "p328"
            )
            closure[f"{auth_prefix}_auth_exec_runtime_contract_id"] = (
                typed_evidence.P335_AUTH_EXEC_RUNTIME_CONTRACT_ID
                if _p335_bundle(bundle)
                else typed_evidence.P334_AUTH_EXEC_RUNTIME_CONTRACT_ID
                if _p334_bundle(bundle)
                else typed_evidence.P333_AUTH_EXEC_RUNTIME_CONTRACT_ID
                if _p333_bundle(bundle)
                else typed_evidence.P332_AUTH_EXEC_RUNTIME_CONTRACT_ID
                if _p332_bundle(bundle)
                else typed_evidence.P331_AUTH_EXEC_RUNTIME_CONTRACT_ID
                if _p331_bundle(bundle)
                else typed_evidence.P330_AUTH_EXEC_RUNTIME_CONTRACT_ID
                if _p330_bundle(bundle)
                else typed_evidence.P329_AUTH_EXEC_RUNTIME_CONTRACT_ID
                if _p329_bundle(bundle)
                else typed_evidence.P328_AUTH_EXEC_RUNTIME_CONTRACT_ID
            )
            closure[f"{auth_prefix}_auth_acm_observer_contract_id"] = (
                typed_evidence.P335_AUTH_EXEC_OBSERVER_CONTRACT_ID
                if _p335_bundle(bundle)
                else typed_evidence.P334_AUTH_EXEC_OBSERVER_CONTRACT_ID
                if _p334_bundle(bundle)
                else typed_evidence.P333_AUTH_EXEC_OBSERVER_CONTRACT_ID
                if _p333_bundle(bundle)
                else typed_evidence.P332_AUTH_EXEC_OBSERVER_CONTRACT_ID
                if _p332_bundle(bundle)
                else typed_evidence.P331_AUTH_EXEC_OBSERVER_CONTRACT_ID
                if _p331_bundle(bundle)
                else typed_evidence.P330_AUTH_EXEC_OBSERVER_CONTRACT_ID
                if _p330_bundle(bundle)
                else typed_evidence.P329_AUTH_EXEC_OBSERVER_CONTRACT_ID
                if _p329_bundle(bundle)
                else typed_evidence.P328_AUTH_EXEC_OBSERVER_CONTRACT_ID
            )
            closure["p324_typec_lane_contract_id"] = p324_typec_lane.CONTRACT_ID
            closure["p324_cdc_acm_observer_contract_id"] = (
                p324_cdc_observer.CONTRACT_ID
            )
            closure["p325_cdc_acm_guard_contract_id"] = (
                p325_guard_adapter.CONTRACT_ID
            )
            closure["p326_bidirectional_acm_contract_id"] = (
                p326_console_observer.CONTRACT_ID
            )
        elif _p327_bundle(bundle):
            closure["p327_framed_exec_runtime_contract_id"] = (
                typed_evidence.P327_FRAMED_EXEC_RUNTIME_CONTRACT_ID
            )
            closure["p324_typec_lane_contract_id"] = p324_typec_lane.CONTRACT_ID
            closure["p324_cdc_acm_observer_contract_id"] = (
                p324_cdc_observer.CONTRACT_ID
            )
            closure["p325_cdc_acm_guard_contract_id"] = (
                p325_guard_adapter.CONTRACT_ID
            )
            closure["p327_framed_acm_contract_id"] = (
                p327_framed_observer.CONTRACT_ID
            )
        elif _p326_bundle(bundle):
            closure["p326_console_runtime_contract_id"] = (
                typed_evidence.P326_CONSOLE_RUNTIME_CONTRACT_ID
            )
            closure["p324_typec_lane_contract_id"] = p324_typec_lane.CONTRACT_ID
            closure["p324_cdc_acm_observer_contract_id"] = (
                p324_cdc_observer.CONTRACT_ID
            )
            closure["p325_cdc_acm_guard_contract_id"] = (
                p325_guard_adapter.CONTRACT_ID
            )
            closure["p326_bidirectional_acm_contract_id"] = (
                p326_console_observer.CONTRACT_ID
            )
        elif _p325_bundle(bundle):
            closure["p325_acm_primary_runtime_contract_id"] = (
                typed_evidence.P325_ACM_PRIMARY_RUNTIME_CONTRACT_ID
            )
            closure["p324_typec_lane_contract_id"] = p324_typec_lane.CONTRACT_ID
            closure["p324_cdc_acm_observer_contract_id"] = (
                p324_cdc_observer.CONTRACT_ID
            )
            closure["p325_cdc_acm_guard_contract_id"] = (
                p325_guard_adapter.CONTRACT_ID
            )
        elif _p324_bundle(bundle):
            closure["p324_acm_primary_runtime_contract_id"] = (
                typed_evidence.P324_ACM_PRIMARY_RUNTIME_CONTRACT_ID
            )
            closure["p324_typec_lane_contract_id"] = p324_typec_lane.CONTRACT_ID
            closure["p324_cdc_acm_observer_contract_id"] = (
                p324_cdc_observer.CONTRACT_ID
            )
        else:
            closure["p323_acm_primary_runtime_contract_id"] = (
                typed_evidence.P323_ACM_PRIMARY_RUNTIME_CONTRACT_ID
            )
        closure["sha256"] = core.json_sha256(
            {key: value for key, value in closure.items() if key != "sha256"}
        )
    return closure


def _private_root(root: Path) -> Path:
    direct = (root / "workspace/private").absolute()
    if (
        direct.is_symlink()
        or not direct.is_dir()
        or direct.resolve(strict=True) != direct
    ):
        raise F1LiveError("workspace/private is unavailable or indirect")
    return direct


def allocate_run_dir(root: Path, requested: Path | None = None) -> Path:
    root = root.resolve()
    private = _private_root(root)
    base_direct = (root / DEFAULT_RUN_ROOT).absolute()
    if base_direct.exists() and base_direct.resolve(strict=True) != base_direct:
        raise F1LiveError("F1 run root has an indirect path component")
    base_direct.mkdir(parents=True, exist_ok=True)
    base = base_direct.resolve(strict=True)
    try:
        base.relative_to(private)
    except ValueError as exc:
        raise F1LiveError("F1 run root escaped workspace/private") from exc
    if base.is_symlink() or not base.is_dir() or base != base_direct:
        raise F1LiveError("F1 run root is indirect")
    candidate = requested or base / f"f1-{core.utc_now().replace(':', '').replace('.', '')}-{time.time_ns()}"
    candidate = candidate if candidate.is_absolute() else root / candidate
    candidate = candidate.absolute()
    if candidate.parent != base:
        raise F1LiveError("F1 run directory must be a direct child of its private root")
    if candidate.exists() or candidate.is_symlink():
        raise F1LiveError("F1 run directory already exists")
    candidate.mkdir(mode=0o700)
    if candidate.resolve(strict=True) != candidate:
        raise F1LiveError("F1 run directory became indirect")
    core._fsync_dir(candidate.parent)
    return candidate


def _validate_private_run_dir(root: Path, run_dir: Path) -> Path:
    root = root.resolve()
    private = _private_root(root)
    base = (root / DEFAULT_RUN_ROOT).absolute()
    run_dir = run_dir.absolute()
    if (
        base.is_symlink()
        or not base.is_dir()
        or base.resolve(strict=True) != base
        or run_dir.parent != base
        or run_dir.is_symlink()
        or not run_dir.is_dir()
        or run_dir.resolve(strict=True) != run_dir
        or private not in run_dir.parents
    ):
        raise F1LiveError("F1 run directory is unavailable or indirect")
    return run_dir


def _private_target(
    client: d0.AdbReadOnlyClient, result: dict[str, Any]
) -> dict[str, str]:
    serial = client.one_serial()
    topology = client.topology(serial)
    target = result["target_evidence"]["targets"][0]
    if (
        hashlib.sha256(serial.encode()).hexdigest() != target["adb_serial_sha256"]
        or hashlib.sha256(topology.encode()).hexdigest()
        != target["usb_topology_sha256"]
    ):
        raise F1LiveError("post-D0 private target continuity mismatch")
    return {
        "schema": PRIVATE_TARGET_SCHEMA,
        "serial": serial,
        "topology": topology,
    }


def _binding(
    bundle: core.Bundle,
    d0_result: dict[str, Any],
    d0_receipt: dict[str, Any],
    private_receipt: dict[str, Any],
    closure: dict[str, Any],
    p324_lane_receipt: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str]:
    base, base_sha256 = core.approval_binding(
        bundle, d0_result["target_evidence"]
    )
    value = {
        "schema": "device_action_f1_live_approval_binding_v2",
        "adapter_version": ADAPTER_VERSION,
        "base_binding": base,
        "base_binding_sha256": base_sha256,
        "d0_result": d0_receipt,
        "private_target": private_receipt,
        "execution_closure_sha256": closure["sha256"],
        "mandatory_rollback_preapproved": True,
        "recovery_requires_second_approval": False,
    }
    if _p328_bundle(bundle):
        # Bind only the public identity.  The credential is opened later by
        # the live observer and is never copied into this record.
        value["p328_auth_key_identity"] = dict(P328_AUTH_KEY_IDENTITY)
    if (
        _p324_bundle(bundle)
        or _p325_bundle(bundle)
        or _p327_bundle(bundle)
        or _p326_bundle(bundle)
        or _p328_bundle(bundle)
    ):
        if not isinstance(p324_lane_receipt, dict):
            raise F1LiveError("P3.24 Type-C lane binding receipt is absent")
        value["p324_typec_lane_binding"] = p324_lane_receipt
    elif p324_lane_receipt is not None:
        raise F1LiveError("foreign P3.24 Type-C lane binding receipt")
    derivation = _p313_guard_derivation(bundle)
    if derivation is not None:
        value["candidate_observer_guard_lifetime"] = {
            "derivation": derivation,
            "derivation_sha256": p313_guard_lifetime.digest(derivation),
        }
    return value, core.json_sha256(value)


P324_TYPEC_LANE_NAME = "p324-typec-lane-binding.json"


def _prepare_p324_typec_lane(
    bundle: core.Bundle,
    run_dir: Path,
    private_target: dict[str, str],
    *,
    usb_root: Path,
    typec_root: Path,
) -> dict[str, Any] | None:
    if not (
        _p324_bundle(bundle)
        or _p325_bundle(bundle)
        or _p327_bundle(bundle)
        or _p326_bundle(bundle)
        or _p328_bundle(bundle)
    ):
        return None
    try:
        value = p324_typec_lane.capture_binding(
            private_target["topology"],
            usb_root=usb_root,
            typec_root=typec_root,
        )
        p324_typec_lane.validate_binding(
            value, source_topology=private_target["topology"]
        )
    except p324_typec_lane.LaneBindingError as exc:
        raise F1LiveError(str(exc)) from exc
    path = run_dir / P324_TYPEC_LANE_NAME
    _write_exclusive(path, value)
    return _receipt(path, "P3.24 Type-C lane binding")


def _p324_typec_lane_value(
    prepared: PreparedRun,
    *,
    revalidate: bool = False,
    usb_root: Path = DEFAULT_USB_ROOT,
    typec_root: Path = DEFAULT_TYPEC_ROOT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not (
        _p324_bundle(prepared.bundle)
        or _p325_bundle(prepared.bundle)
        or _p326_bundle(prepared.bundle)
        or _p327_bundle(prepared.bundle)
        or _p328_bundle(prepared.bundle)
    ):
        raise F1LiveError("P3.24 Type-C lane binding requested for another run")
    path = prepared.run_dir / P324_TYPEC_LANE_NAME
    value = _read_json(path, "P3.24 Type-C lane binding")
    receipt = _receipt(path, "P3.24 Type-C lane binding")
    expected_receipt = prepared.prepared.get("p324_typec_lane_binding")
    if receipt != expected_receipt:
        raise F1LiveError("P3.24 Type-C lane binding receipt changed")
    try:
        if revalidate:
            p324_typec_lane.revalidate_binding(
                value,
                source_topology=prepared.private_target["topology"],
                usb_root=usb_root,
                typec_root=typec_root,
            )
        else:
            p324_typec_lane.validate_binding(
                value, source_topology=prepared.private_target["topology"]
            )
    except p324_typec_lane.LaneBindingError as exc:
        raise F1LiveError(str(exc)) from exc
    return value, receipt


def _userspace_overlay_contract_id(bundle: core.Bundle) -> Any:
    observation = bundle.manifest.get("observation")
    if not isinstance(observation, dict):
        return None
    acceptance = observation.get("acceptance")
    if not isinstance(acceptance, dict):
        return None
    return acceptance.get("userspace_overlay_contract_id")


def _p313_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        in {
            p313_guard_lifetime.OVERLAY_CONTRACT_ID,
            typed_evidence.P314_OVERLAY_CONTRACT_ID,
            typed_evidence.P315_OVERLAY_CONTRACT_ID,
            typed_evidence.MAX77705_OVERLAY_CONTRACT_ID,
            typed_evidence.P317_MAX77705_OVERLAY_CONTRACT_ID,
            typed_evidence.P318_MAX77705_OVERLAY_CONTRACT_ID,
        }
    )


def _p313_guard_derivation(bundle: core.Bundle) -> dict[str, Any] | None:
    if not _p313_bundle(bundle):
        return None
    observation = bundle.manifest["observation"]
    if observation.get("candidate_observer") is None:
        raise F1LiveError("P3.13 requires the exact CDC ACM observer")
    try:
        return p313_guard_lifetime.derive(
            download_request_sec=DOWNLOAD_REQUEST_TIMEOUT_SEC,
            download_wait_sec=DOWNLOAD_WAIT_SEC,
            endpoint_revalidate_sec=ENDPOINT_REVALIDATE_SEC,
            odin_timeout_sec=ODIN_TIMEOUT_SEC,
            download_departure_wait_sec=DISCONNECT_WAIT_SEC,
            candidate_observation_sec=observation["timeout_sec"],
            guard_default_sec=cdc_acm_observer.GUARD_DEFAULT_MAX_SEC,
            guard_limit_sec=cdc_acm_observer.GUARD_MAX_SEC_LIMIT,
        )
    except (KeyError, p313_guard_lifetime.GuardLifetimeError) as exc:
        raise F1LiveError("P3.13 guard lifetime derivation failed") from exc


def _p300_bundle(bundle: core.Bundle) -> bool:
    return (
        bundle.manifest["observation"]["acceptance"].get("source_contract_id")
        in {
            typed_evidence.P300_SOURCE_CONTRACT_ID,
            typed_evidence.P310_SOURCE_CONTRACT_ID,
        }
    )


def _p318_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        == typed_evidence.P318_MAX77705_OVERLAY_CONTRACT_ID
    )


def _p319_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        == typed_evidence.P319_STOCK_OVERLAY_CONTRACT_ID
    )


def _p320_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        == typed_evidence.P320_STOCK_OVERLAY_CONTRACT_ID
    )


def _p321_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        == typed_evidence.P321_STOCK_OVERLAY_CONTRACT_ID
    )


def _p322_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        == typed_evidence.P322_STOCK_OVERLAY_CONTRACT_ID
    )


def _p323_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        == typed_evidence.P323_STOCK_OVERLAY_CONTRACT_ID
        and _candidate_arrival_proof_role(bundle) is not None
    )


def _p324_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        == typed_evidence.P324_STOCK_OVERLAY_CONTRACT_ID
        and _candidate_arrival_proof_role(bundle) is not None
    )


def _p325_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        == typed_evidence.P325_STOCK_OVERLAY_CONTRACT_ID
        and _candidate_arrival_proof_role(bundle) is not None
    )


def _p326_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        == typed_evidence.P326_STOCK_OVERLAY_CONTRACT_ID
        and _candidate_arrival_proof_role(bundle) is not None
    )


def _p327_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        == typed_evidence.P327_STOCK_OVERLAY_CONTRACT_ID
        and _candidate_arrival_proof_role(bundle) is not None
    )


def _p328_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        in {
            typed_evidence.P328_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P329_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P330_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P331_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P332_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P333_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P334_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P335_STOCK_OVERLAY_CONTRACT_ID,
        }
        and _candidate_arrival_proof_role(bundle) is not None
    )


def _p329_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        == typed_evidence.P329_STOCK_OVERLAY_CONTRACT_ID
        and _candidate_arrival_proof_role(bundle) is not None
    )


def _p330_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        == typed_evidence.P330_STOCK_OVERLAY_CONTRACT_ID
        and _candidate_arrival_proof_role(bundle) is not None
    )


def _p331_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        == typed_evidence.P331_STOCK_OVERLAY_CONTRACT_ID
        and _candidate_arrival_proof_role(bundle) is not None
    )


def _p332_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        == typed_evidence.P332_STOCK_OVERLAY_CONTRACT_ID
        and _candidate_arrival_proof_role(bundle) is not None
    )


def _p333_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        == typed_evidence.P333_STOCK_OVERLAY_CONTRACT_ID
        and _candidate_arrival_proof_role(bundle) is not None
    )


def _p334_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        == typed_evidence.P334_STOCK_OVERLAY_CONTRACT_ID
        and _candidate_arrival_proof_role(bundle) is not None
    )


def _p335_bundle(bundle: core.Bundle) -> bool:
    return (
        _userspace_overlay_contract_id(bundle)
        == typed_evidence.P335_STOCK_OVERLAY_CONTRACT_ID
        and _candidate_arrival_proof_role(bundle) is not None
    )


def _p328_bound_auth_key_identity(prepared: PreparedRun) -> dict[str, Any]:
    """Return the prepared, path-free P328 key identity.

    This helper deliberately reads only already-bound JSON.  The credential
    itself is opened by :func:`_p328_read_auth_key` at session open and is
    never consulted by receipt reopening or rollback recovery.
    """
    containers: list[Mapping[str, Any]] = [prepared.prepared]
    approval = prepared.prepared.get("approval_binding")
    if isinstance(approval, dict):
        containers.append(approval)
    observation = prepared.bundle.manifest.get("observation")
    if isinstance(observation, dict):
        acceptance = observation.get("acceptance")
        if isinstance(acceptance, dict):
            containers.append(acceptance)
    candidates: list[Any] = []
    for container in containers:
        for key in (
            "p328_auth_key_identity",
            "p328_auth_key",
            "auth_key_identity",
            "auth_key",
        ):
            if key in container:
                candidates.append(container[key])
        for key in ("p328_auth_key_sha256", "auth_key_sha256"):
            if key in container:
                candidates.append({"size": 32, "sha256": container[key]})
    artifact_module = (
        p335_artifact_identity
        if _p335_bundle(prepared.bundle)
        else p334_artifact_identity
        if _p334_bundle(prepared.bundle)
        else p333_artifact_identity
        if _p333_bundle(prepared.bundle)
        else p332_artifact_identity
        if _p332_bundle(prepared.bundle)
        else p331_artifact_identity
        if _p331_bundle(prepared.bundle)
        else p330_artifact_identity
        if _p330_bundle(prepared.bundle)
        else p329_artifact_identity
        if _p329_bundle(prepared.bundle)
        else p328_artifact_identity
    )
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if (
            set(candidate) != {"size", "sha256"}
            or type(candidate["size"]) is not int
            or candidate["size"] != artifact_module.AUTH_KEY_SIZE
            or not isinstance(candidate["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", candidate["sha256"]) is None
        ):
            continue
        return {"size": 32, "sha256": candidate["sha256"]}
    raise F1LiveError("P3.28 prepared auth-key identity is absent")


def _p328_read_auth_key(prepared: PreparedRun) -> tuple[bytes, str]:
    """Open the one fixed key only at observer-session entry.

    The returned bytes remain an in-memory argument to the P328 observer.  No
    caller path is accepted and the public projection contains only size and
    digest.
    """
    bound = _p328_bound_auth_key_identity(prepared)
    artifact_module = (
        p335_artifact_identity
        if _p335_bundle(prepared.bundle)
        else p334_artifact_identity
        if _p334_bundle(prepared.bundle)
        else p333_artifact_identity
        if _p333_bundle(prepared.bundle)
        else p332_artifact_identity
        if _p332_bundle(prepared.bundle)
        else p331_artifact_identity
        if _p331_bundle(prepared.bundle)
        else p330_artifact_identity
        if _p330_bundle(prepared.bundle)
        else p329_artifact_identity
        if _p329_bundle(prepared.bundle)
        else p328_artifact_identity
    )
    try:
        key_path = (
            P328_AUTH_KEY_PATH
            if artifact_module is p328_artifact_identity
            else artifact_module.DEFAULT_AUTH_KEY_PATH
        )
        key = artifact_module.read_auth_key(key_path)
        actual = artifact_module.validate_auth_key(key)
    except (
        p328_artifact_identity.ArtifactIdentityError,
        p329_artifact_identity.ArtifactIdentityError,
        p330_artifact_identity.ArtifactIdentityError,
        p331_artifact_identity.ArtifactIdentityError,
        p332_artifact_identity.ArtifactIdentityError,
        p333_artifact_identity.ArtifactIdentityError,
        p334_artifact_identity.ArtifactIdentityError,
        p335_artifact_identity.ArtifactIdentityError,
    ) as exc:
        raise F1LiveError("bound auth-key identity is unavailable") from exc
    if actual != bound:
        raise F1LiveError("P3.28 auth-key identity differs from preparation")
    return key, actual["sha256"]


P328_PROOF_FIELDS = (
    "hmac_authenticated",
    "pid1_authenticated_framed_exec_proof",
    "busybox_ash_command_proof",
    "framed_session_closed",
    "interactive_pty_proof",
    "caller_selected_command",
    "command_count",
    "max_commands",
    "auth_key_sha256",
    "challenge_nonce_sha256",
)


def _p328_proof_ok(value: Mapping[str, Any]) -> bool:
    return (
        value.get("hmac_authenticated") is True
        and value.get("pid1_authenticated_framed_exec_proof") is True
        and value.get("busybox_ash_command_proof") is True
        and value.get("framed_session_closed") is True
        and value.get("caller_selected_command") is True
        and value.get("command_count") == 3
        and value.get("max_commands") == p328_auth_runtime.MAX_COMMANDS
    )


def _p328_proof_state(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value.get(key) for key in P328_PROOF_FIELDS}


def _p324_lane_bundle(bundle: core.Bundle) -> bool:
    return (
        _p324_bundle(bundle)
        or _p325_bundle(bundle)
        or _p326_bundle(bundle)
        or _p327_bundle(bundle)
        or _p328_bundle(bundle)
        or _p335_bundle(bundle)
    )


def _acm_primary_bundle(bundle: core.Bundle) -> bool:
    return (
        _p323_bundle(bundle)
        or _p324_bundle(bundle)
        or _p325_bundle(bundle)
        or _p326_bundle(bundle)
        or _p327_bundle(bundle)
        or _p328_bundle(bundle)
        or _p335_bundle(bundle)
    )


def _candidate_arrival_proof_role(bundle: core.Bundle) -> str | None:
    role = bundle.manifest["observation"].get(
        typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY
    )
    if role is None:
        return None
    acceptance = bundle.manifest["observation"]["acceptance"]
    identity = (
        acceptance.get("userspace_overlay_contract_id"),
        acceptance.get("run_id"),
    )
    if identity not in {
        (
            typed_evidence.P323_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P323_RUN_ID,
        ),
        (
            typed_evidence.P324_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P324_RUN_ID,
        ),
        (
            typed_evidence.P325_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P325_RUN_ID,
        ),
        (
            typed_evidence.P326_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P326_RUN_ID,
        ),
        (
            typed_evidence.P327_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P327_RUN_ID,
        ),
        (
            typed_evidence.P328_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P328_RUN_ID,
        ),
        (
            typed_evidence.P329_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P329_RUN_ID,
        ),
        (
            typed_evidence.P330_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P330_RUN_ID,
        ),
        (
            typed_evidence.P331_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P331_RUN_ID,
        ),
        (
            typed_evidence.P332_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P332_RUN_ID,
        ),
        (
            typed_evidence.P333_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P333_RUN_ID,
        ),
        (
            typed_evidence.P334_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P334_RUN_ID,
        ),
        (
            typed_evidence.P335_STOCK_OVERLAY_CONTRACT_ID,
            typed_evidence.P335_RUN_ID,
        ),
    }:
        raise F1LiveError(
            "candidate arrival proof role requires the exact P3.23 stock binding "
            "through the exact P3.35 stock binding"
        )
    try:
        typed_evidence.validate_candidate_arrival_proof_role(
            role,
            bundle.manifest["observation"].get("candidate_observer"),
            expected_run_id=identity[1],
        )
        candidate_observer = bundle.manifest["observation"].get(
            "candidate_observer"
        )
        if (
            role
            in {
                typed_evidence.CANDIDATE_FRAMED_FIXED_COMMAND_ROLE,
                typed_evidence.CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE,
                typed_evidence.CANDIDATE_AUTHENTICATED_SETTLED_EXEC_ROLE,
                typed_evidence.CANDIDATE_AUTHENTICATED_DIAGNOSTIC_EXEC_ROLE,
                typed_evidence.CANDIDATE_AUTHENTICATED_RESIDENT_EXEC_ROLE,
                typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE,
            }
            and isinstance(candidate_observer, dict)
        ):
            inherited_observer = {
                key: candidate_observer[key]
                for key in cdc_acm_observer.SPEC_KEYS
            }
            inherited_observer["kind"] = cdc_acm_observer.KIND
        else:
            inherited_observer = candidate_observer
        cdc_acm_observer.validate_spec(inherited_observer)
    except (typed_evidence.EvidenceError, cdc_acm_observer.ObserverError) as exc:
        raise F1LiveError(str(exc)) from exc
    return role


def _p318_phase_paths(prepared: PreparedRun, phase: str) -> tuple[Path, Path]:
    if phase not in p318_topology.transition.TOPOLOGY_PHASES:
        raise F1LiveError("P3.18 topology phase differs")
    prefix = prepared.run_dir / f"p318-topology-{phase.replace('_', '-')}"
    return prefix.with_suffix(".raw.json"), prefix.with_suffix(".record.json")


def _p318_download_target(prepared: PreparedRun) -> dict[str, str]:
    download = prepared.bundle.profile["target"]["download"]
    return {
        "vendor": download["usb_vendor_id"],
        "product_id": download["usb_product_id"],
        "product": download["product"],
        "manufacturer": download["manufacturer"],
        "serial": "",
    }


def _p318_candidate_target(prepared: PreparedRun) -> dict[str, str]:
    spec = prepared.bundle.manifest["observation"].get("candidate_observer")
    if not isinstance(spec, dict):
        raise F1LiveError("P3.18 candidate observer is absent")
    return {
        "vendor": spec["usb_vendor_id"],
        "product_id": spec["usb_product_id"],
        "serial": spec["usb_serial"],
        "driver": spec["usb_driver"],
        "interface": spec["usb_interface_number"],
    }


def _p318_read_phase(
    prepared: PreparedRun, phase: str
) -> tuple[bytes, dict[str, Any]]:
    raw_path, record_path = _p318_phase_paths(prepared, phase)
    try:
        raw = p318_topology.stable_read(raw_path)
        record = _read_json(record_path, f"P3.18 {phase} topology record")
        start = None
        target = _p318_download_target(prepared)
        if phase == "candidate_end":
            target = _p318_candidate_target(prepared)
        if phase != "download_start":
            start = p318_topology.start_path(
                _p318_read_phase(prepared, "download_start")[1]
            )
        return raw, p318_topology.validate_phase_record(
            record,
            raw_payload=raw,
            target_identity=target,
            start_path=start,
        )
    except p318_topology.TopologyReceiptError as exc:
        raise F1LiveError(str(exc)) from exc


def _p318_publish_or_reopen_phase(
    prepared: PreparedRun, phase: str, payload: bytes, **record_args: Any
) -> dict[str, Any]:
    raw_path, record_path = _p318_phase_paths(prepared, phase)
    expected = p318_topology.validate_phase_record(
        p318_topology.build_phase_record(payload, phase=phase, **record_args),
        raw_payload=payload,
    )
    if raw_path.exists() or record_path.exists():
        if not raw_path.is_file() or not record_path.is_file():
            raise F1LiveError("P3.18 topology phase evidence is partial")
        reopened_raw, reopened = _p318_read_phase(prepared, phase)
        if reopened_raw != payload or reopened != expected:
            raise F1LiveError("P3.18 topology phase evidence changed")
        return reopened
    try:
        record, _receipts = p318_topology.publish_phase(
            raw_path, record_path, payload, phase=phase, **record_args
        )
    except p318_topology.TopologyReceiptError as exc:
        raise F1LiveError(str(exc)) from exc
    return record


def _p318_publish_candidate_raw(
    prepared: PreparedRun, payload: bytes
) -> dict[str, Any]:
    raw_path, record_path = _p318_phase_paths(prepared, "candidate_end")
    if record_path.exists() or record_path.is_symlink():
        raise F1LiveError("P3.18 candidate phase record exists before final decode")
    try:
        if raw_path.exists() or raw_path.is_symlink():
            reopened = p318_topology.stable_read(raw_path)
            if reopened != payload:
                raise F1LiveError("P3.18 candidate topology raw snapshot changed")
            receipt = {"size": len(reopened), "sha256": hashlib.sha256(reopened).hexdigest()}
        else:
            receipt = p318_topology.publish_raw(
                raw_path, payload, phase="candidate_end"
            )
    except p318_topology.TopologyReceiptError as exc:
        raise F1LiveError(str(exc)) from exc
    return receipt


def _p318_candidate_raw_receipt(prepared: PreparedRun) -> dict[str, Any]:
    raw_path, record_path = _p318_phase_paths(prepared, "candidate_end")
    if record_path.exists() or record_path.is_symlink():
        raw, record = _p318_read_phase(prepared, "candidate_end")
        return {
            "size": record["immutable_raw_snapshot_size"],
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    try:
        raw = p318_topology.stable_read(raw_path)
        p318_topology.parse_raw_snapshot(raw, phase="candidate_end")
    except p318_topology.TopologyReceiptError as exc:
        raise F1LiveError(str(exc)) from exc
    return {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _p318_interrupted_candidate_raw(prepared: PreparedRun) -> dict[str, Any]:
    raw_path, record_path = _p318_phase_paths(prepared, "candidate_end")
    if record_path.exists() or record_path.is_symlink():
        _raw, record = _p318_read_phase(prepared, "candidate_end")
        return {
            "size": record["immutable_raw_snapshot_size"],
            "sha256": record["immutable_raw_snapshot_sha256"],
        }
    if raw_path.exists() or raw_path.is_symlink():
        return _p318_candidate_raw_receipt(prepared)
    payload = p318_topology.raw_snapshot(
        phase="candidate_end", capture_complete=False, endpoints=[]
    )
    return _p318_publish_candidate_raw(prepared, payload)


def _p318_finalize_candidate_phase(
    prepared: PreparedRun, classified: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_path, record_path = _p318_phase_paths(prepared, "candidate_end")
    raw = p318_topology.stable_read(raw_path)
    start = p318_topology.start_path(
        _p318_read_phase(prepared, "download_start")[1]
    )
    durable = _reopen_candidate_observation(prepared)
    host_observer = _p318_host_observer(prepared, durable)
    causal_ready = typed_evidence.p318_candidate_causal_ready(classified)
    arguments = {
        "phase": "candidate_end",
        "target_identity": _p318_candidate_target(prepared),
        "binding_id_sha256": prepared.binding_sha256,
        "comparison_binding_id_sha256": prepared.binding_sha256,
        "authority_state": "candidate_approved_exact",
        "causal_terminal_ready": causal_ready,
        "start_path": start,
        "host_observer": host_observer,
    }
    expected = p318_topology.validate_phase_record(
        p318_topology.build_phase_record(raw, **arguments),
        raw_payload=raw,
        target_identity=arguments["target_identity"],
        start_path=start,
    )
    if record_path.exists() or record_path.is_symlink():
        _reopened_raw, phase_record = _p318_read_phase(
            prepared, "candidate_end"
        )
        if phase_record != expected:
            raise F1LiveError("P3.18 candidate topology phase changed")
    else:
        try:
            phase_record, _record_receipt = (
                p318_topology.publish_record_for_existing_raw(
                    raw_path, record_path, raw, **arguments
                )
            )
        except p318_topology.TopologyReceiptError as exc:
            raise F1LiveError(str(exc)) from exc
    try:
        correlated = typed_evidence.correlate_p318_candidate_topology(
            classified, phase_record
        )
    except typed_evidence.EvidenceError as exc:
        raise F1LiveError(str(exc)) from exc
    evidence = {
        "raw": {
            "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
        "record": _receipt(record_path, "P3.18 candidate topology record"),
        "phase": phase_record,
    }
    return correlated, evidence


def _private_relative(root: Path, path: Path, label: str) -> str:
    try:
        relative = path.absolute().relative_to(root.resolve())
    except ValueError as exc:
        raise F1LiveError(f"{label} escaped the repository") from exc
    if relative.parts[:2] != ("workspace", "private"):
        raise F1LiveError(f"{label} is not private")
    return relative.as_posix()


def _p300_owner_token(binding: dict[str, Any]) -> str:
    return p300_usb_trace.owner_token(binding)


def _p300_owner_sha256(token: str) -> str:
    return hashlib.sha256(token.encode("ascii", "strict")).hexdigest()


def _p300_process_owner_path(prepared: PreparedRun) -> Path:
    return prepared.run_dir / "p300-usb-trace-process.json"


def _p300_process_owner_value(
    prepared: PreparedRun,
    binding: dict[str, Any],
    identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    verified = p300_usb_trace.verify_binding(binding)
    value: dict[str, Any] = {
        "schema": P300_PROCESS_OWNER_SCHEMA,
        "binding_sha256": verified["binding_sha256"],
        "approval_binding_sha256": prepared.binding_sha256,
        "owner_token_sha256": _p300_owner_sha256(_p300_owner_token(binding)),
        "status": "launch-intent" if identity is None else "launched",
        "leader": None,
    }
    if identity is not None:
        value["leader"] = {
            name: identity[name]
            for name in (
                "pid",
                "parent_pid",
                "process_group_id",
                "session_id",
                "start_ticks",
            )
        }
    return value


def _validate_p300_process_owner(
    prepared: PreparedRun, binding: dict[str, Any], value: Any
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise F1LiveError("P3.00 observer process owner is not an object")
    status = value.get("status")
    expected = _p300_process_owner_value(prepared, binding)
    if status == "launched":
        leader = value.get("leader")
        if (
            not isinstance(leader, dict)
            or set(leader)
            != {
                "pid",
                "parent_pid",
                "process_group_id",
                "session_id",
                "start_ticks",
            }
            or any(
                isinstance(leader[name], bool)
                or not isinstance(leader[name], int)
                or leader[name] <= 0
                for name in leader
            )
            or leader["pid"] != leader["process_group_id"]
            or leader["pid"] != leader["session_id"]
        ):
            raise F1LiveError("P3.00 observer process leader differs")
        expected = _p300_process_owner_value(prepared, binding, leader)
    elif status != "launch-intent":
        raise F1LiveError("P3.00 observer process owner status differs")
    if value != expected:
        raise F1LiveError("P3.00 observer process owner binding differs")
    return dict(value)


def _proc_identity(pid: int) -> dict[str, Any] | None:
    try:
        payload = (Path("/proc") / str(pid) / "stat").read_bytes()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None
    marker = payload.rfind(b") ")
    if marker < 0:
        raise F1LiveError("P3.00 observer process stat is malformed")
    fields = payload[marker + 2 :].split()
    if len(fields) < 20:
        raise F1LiveError("P3.00 observer process stat is truncated")
    try:
        return {
            "pid": pid,
            "state": fields[0].decode("ascii", "strict"),
            "parent_pid": int(fields[1]),
            "process_group_id": int(fields[2]),
            "session_id": int(fields[3]),
            "start_ticks": int(fields[19]),
        }
    except (UnicodeError, ValueError) as exc:
        raise F1LiveError("P3.00 observer process stat fields differ") from exc


def _proc_has_owner(pid: int, token: str) -> bool:
    try:
        payload = (Path("/proc") / str(pid) / "environ").read_bytes()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return False
    expected = (
        usb_trace_sidecar.OWNER_ENV.encode("ascii")
        + b"="
        + token.encode("ascii", "strict")
    )
    return expected in payload.split(b"\0")


def _p300_wait_owned_identity(
    process: subprocess.Popen[bytes],
    token: str,
    *,
    timeout_sec: float = P300_OWNER_ARM_TIMEOUT_SEC,
) -> dict[str, Any]:
    """Wait briefly for setsid/exec and the child environment to reach /proc.

    Immediately after ``Popen`` Linux may still expose the pre-exec child or
    an empty ``/proc/<pid>/environ``.  That is a host scheduling race, not a
    sidecar failure.  The bounded poll owns no device action and still rejects
    a child that exits, never enters its own session/group, or never exposes
    the exact owner token.
    """
    if (
        not isinstance(token, str)
        or not token
        or isinstance(timeout_sec, bool)
        or not isinstance(timeout_sec, (int, float))
        or not 0 < timeout_sec <= P300_OWNER_ARM_TIMEOUT_SEC
    ):
        raise F1LiveError("P3.00 USB trace ownership wait is invalid")
    deadline = time.monotonic() + float(timeout_sec)
    while True:
        if process.poll() is not None:
            raise F1LiveError("P3.00 USB trace process exited before ownership")
        identity = _proc_identity(process.pid)
        if (
            identity is not None
            and identity["state"] != "Z"
            and identity["process_group_id"] == process.pid
            and identity["session_id"] == process.pid
            and _proc_has_owner(process.pid, token)
        ):
            return identity
        if time.monotonic() >= deadline:
            raise F1LiveError("P3.00 USB trace process ownership did not arm")
        time.sleep(P300_OWNER_ARM_POLL_SEC)


def _proc_has_any_p300_owner(pid: int) -> bool:
    try:
        payload = (Path("/proc") / str(pid) / "environ").read_bytes()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return False
    prefix = usb_trace_sidecar.OWNER_ENV.encode("ascii") + b"="
    return any(item.startswith(prefix) for item in payload.split(b"\0"))


def _p300_any_owned_processes() -> list[dict[str, Any]]:
    result = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        pid = int(path.name)
        if not _proc_has_any_p300_owner(pid):
            continue
        identity = _proc_identity(pid)
        if identity is not None and identity["state"] != "Z":
            result.append(identity)
    return result


def _p300_owned_processes(token: str) -> list[dict[str, Any]]:
    result = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        pid = int(path.name)
        if not _proc_has_owner(pid, token):
            continue
        identity = _proc_identity(pid)
        if identity is not None and identity["state"] != "Z":
            result.append(identity)
    return sorted(result, key=lambda value: value["pid"])


def _p300_group_members(group_ids: set[int]) -> list[dict[str, Any]]:
    result = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        identity = _proc_identity(int(path.name))
        if (
            identity is not None
            and identity["state"] != "Z"
            and identity["process_group_id"] in group_ids
        ):
            result.append(identity)
    return result


def _p300_wait_owner_absent(token: str, timeout_sec: float) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if not _p300_owned_processes(token):
            return True
        time.sleep(0.05)
    return not _p300_owned_processes(token)


def _p300_revalidate_group_before_kill(
    token: str, group: int
) -> list[dict[str, Any]]:
    """Re-read the complete owned process group before a group signal."""
    remaining = _p300_owned_processes(token)
    groups = {value["process_group_id"] for value in remaining}
    sessions = {value["session_id"] for value in remaining}
    if groups != {group} or sessions != {group}:
        raise F1LiveError("P3.00 observer process group changed during cleanup")
    group_members = _p300_group_members({group})
    if any(not _proc_has_owner(value["pid"], token) for value in group_members):
        raise F1LiveError("P3.00 observer process group has a foreign member")
    return remaining


def _p300_validate_expected_group_absent(token: str, group: int) -> None:
    """Confirm an expected PGID has no live member after owner disappearance."""
    group_members = _p300_group_members({group})
    if not group_members:
        return
    sessions = {value["session_id"] for value in group_members}
    if sessions != {group}:
        raise F1LiveError("P3.00 observer process group changed during cleanup")
    if any(not _proc_has_owner(value["pid"], token) for value in group_members):
        raise F1LiveError("P3.00 observer process group has a foreign member")
    # An owned live member that was not returned by _p300_owned_processes is
    # an inconsistent observation.  Do not claim group absence or signal it.
    raise F1LiveError("P3.00 observer process group changed during cleanup")


def _p300_cleanup_owned_processes(
    binding: dict[str, Any], *, expected_group: int | None = None
) -> dict[str, Any]:
    token = _p300_owner_token(binding)
    token_sha256 = _p300_owner_sha256(token)
    members = _p300_owned_processes(token)
    initial_count = len(members)
    signals: list[str] = []
    if not members and expected_group is not None:
        _p300_validate_expected_group_absent(token, expected_group)
    if members:
        groups = {value["process_group_id"] for value in members}
        sessions = {value["session_id"] for value in members}
        if (
            len(groups) != 1
            or sessions != groups
            or (expected_group is not None and groups != {expected_group})
        ):
            raise F1LiveError("P3.00 observer process ownership differs")
        group_members = _p300_group_members(groups)
        if any(
            not _proc_has_owner(value["pid"], token)
            for value in group_members
        ):
            raise F1LiveError("P3.00 observer process group has a foreign member")
        group = next(iter(groups))
        # Prefer the sidecar leader's private SIGTERM path.  The sidecar then
        # stops its source children one by one, preserving their clean
        # ``alive_before_stop`` receipts.  Escalate to the whole verified
        # group only if the leader is already gone or does not finish.
        leader = next(
            (value for value in members if value["pid"] == group), None
        )
        if leader is not None and _proc_has_owner(leader["pid"], token):
            try:
                os.kill(leader["pid"], signal.SIGTERM)
                signals.append("SIGTERM")
            except ProcessLookupError:
                pass
        else:
            try:
                os.killpg(group, signal.SIGTERM)
                signals.append("SIGTERM")
            except ProcessLookupError:
                pass
        if not _p300_wait_owner_absent(token, P300_PROCESS_WAIT_SEC):
            _p300_revalidate_group_before_kill(token, group)
            try:
                os.killpg(group, signal.SIGTERM)
                signals.append("SIGTERM")
            except ProcessLookupError:
                pass
            if not _p300_wait_owner_absent(token, P300_PROCESS_WAIT_SEC):
                _p300_revalidate_group_before_kill(token, group)
                try:
                    os.killpg(group, signal.SIGKILL)
                    signals.append("SIGKILL")
                except ProcessLookupError:
                    pass
                if not _p300_wait_owner_absent(token, P300_PROCESS_WAIT_SEC):
                    raise F1LiveError("P3.00 observer process group survived cleanup")
    return {
        "schema": P300_PROCESS_CLEANUP_SCHEMA,
        "owner_token_sha256": token_sha256,
        "matching_processes_before": initial_count,
        "matching_processes_after": 0,
        "signals": signals,
        "checked_utc": core.utc_now(),
        "group_absent": True,
        "verified": True,
        "error_type": None,
    }


def _p300_cleanup_failure(
    binding: dict[str, Any], exc: Exception
) -> dict[str, Any]:
    token = _p300_owner_token(binding)
    try:
        count: int | None = len(_p300_owned_processes(token))
    except Exception:
        count = None
    return {
        "schema": P300_PROCESS_CLEANUP_SCHEMA,
        "owner_token_sha256": _p300_owner_sha256(token),
        "matching_processes_before": count,
        "matching_processes_after": count,
        "signals": [],
        "checked_utc": core.utc_now(),
        "group_absent": False,
        "verified": False,
        "error_type": type(exc).__name__,
    }


def _validate_p300_process_cleanup(
    binding: dict[str, Any], value: Any, *, require_verified: bool
) -> dict[str, Any]:
    token = _p300_owner_token(binding)
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "schema",
            "owner_token_sha256",
            "matching_processes_before",
            "matching_processes_after",
            "signals",
            "checked_utc",
            "group_absent",
            "verified",
            "error_type",
        }
        or value.get("schema") != P300_PROCESS_CLEANUP_SCHEMA
        or value.get("owner_token_sha256") != _p300_owner_sha256(token)
        or not isinstance(value.get("signals"), list)
        or any(item not in {"SIGTERM", "SIGKILL"} for item in value["signals"])
        or not isinstance(value.get("checked_utc"), str)
        or not value["checked_utc"].endswith("Z")
    ):
        raise F1LiveError("P3.00 observer process cleanup proof differs")
    if value.get("verified") is True:
        if (
            isinstance(value.get("matching_processes_before"), bool)
            or not isinstance(value.get("matching_processes_before"), int)
            or value["matching_processes_before"] < 0
            or value.get("matching_processes_after") != 0
            or value.get("group_absent") is not True
            or value.get("error_type") is not None
            or _p300_owned_processes(token)
        ):
            raise F1LiveError("P3.00 observer cleanup success proof differs")
    elif (
        value.get("verified") is not False
        or value.get("group_absent") is not False
        or not isinstance(value.get("error_type"), str)
        or not value["error_type"]
    ):
        raise F1LiveError("P3.00 observer cleanup failure proof differs")
    if require_verified and value.get("verified") is not True:
        raise F1LiveError("P3.00 verified trace lacks process cleanup")
    return dict(value)


def _p300_usb_binding_value(
    root: Path,
    bundle: core.Bundle,
    run_dir: Path,
    approval_binding_sha256: str,
) -> dict[str, Any] | None:
    if not _p300_bundle(bundle):
        return None
    return p300_usb_trace.create_binding(
        campaign_id=bundle.manifest["manifest_id"],
        attempt_id=bundle.manifest["run_id"],
        candidate_ap={
            "size": bundle.manifest["candidate_ap"]["size"],
            "sha256": bundle.manifest["candidate_ap"]["sha256"],
        },
        approval_binding_sha256=approval_binding_sha256,
        transaction_path=_private_relative(
            root, run_dir / "transaction", "P3.00 transaction"
        ),
        sidecar_result_path=_private_relative(
            root,
            run_dir / "p300-usb-trace/result.json",
            "P3.00 sidecar result",
        ),
        observation_witness_path=_private_relative(
            root,
            run_dir / "p300-candidate-observation-durable.json",
            "P3.00 observation witness",
        ),
    )


def _prepare_p300_usb_binding(
    root: Path,
    bundle: core.Bundle,
    run_dir: Path,
    approval_binding_sha256: str,
) -> dict[str, Any] | None:
    value = _p300_usb_binding_value(
        root, bundle, run_dir, approval_binding_sha256
    )
    if value is None:
        return None
    path = run_dir / "p300-usb-trace-binding.json"
    _write_exclusive(path, value)
    return _receipt(path, "P3.00 USB trace binding")


def _p300_observation_witness_path(prepared: PreparedRun) -> Path:
    return prepared.run_dir / "p300-candidate-observation-durable.json"


def _write_p300_observation_witness(
    prepared: PreparedRun, current: dict[str, Any]
) -> dict[str, Any]:
    binding = p300_usb_trace.verify_binding(
        _read_json(
            prepared.run_dir / "p300-usb-trace-binding.json",
            "P3.00 USB trace binding",
        )
    )
    durable_state = _state(prepared)
    expected_state = {**current, "schema": LIVE_STATE_SCHEMA}
    if durable_state != expected_state:
        raise F1LiveError("P3.00 observation state was not durable")
    value = {
        "schema": p300_usb_trace.OBSERVATION_WITNESS_SCHEMA,
        "binding_sha256": binding["binding_sha256"],
        "approval_binding_sha256": prepared.binding_sha256,
        "candidate_ap": binding["candidate_ap"],
        "timestamp_utc": core.utc_now(),
        "live_state_sha256": core.json_sha256(durable_state),
        "durable": True,
        "device_actions": False,
    }
    path = _p300_observation_witness_path(prepared)
    expected_path = prepared.root / binding["observation_witness_path"]
    if path.absolute() != expected_path.absolute():
        raise F1LiveError("P3.00 observation witness path differs")
    _write_exclusive(path, value)
    reopened = p300_usb_trace.verify_observation_witness(
        binding, _read_json(path, "P3.00 observation witness")
    )
    if reopened != value:
        raise F1LiveError("P3.00 observation witness changed")
    return _receipt(path, "P3.00 observation witness")


def _read_p300_observation_witness(
    prepared: PreparedRun, binding: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = _p300_observation_witness_path(prepared)
    expected_path = prepared.root / binding["observation_witness_path"]
    if path.absolute() != expected_path.absolute():
        raise F1LiveError("P3.00 observation witness path differs")
    value = p300_usb_trace.verify_observation_witness(
        binding, _read_json(path, "P3.00 observation witness")
    )
    return value, _receipt(path, "P3.00 observation witness")


def prepare_connected(
    root: Path,
    bundle: core.Bundle,
    run_dir: Path,
    client: d0.AdbReadOnlyClient,
    usb_root: Path = DEFAULT_USB_ROOT,
    typec_root: Path = DEFAULT_TYPEC_ROOT,
) -> dict[str, Any]:
    if bundle.manifest["status"] != "ready-for-f1-approval":
        raise F1LiveError("manifest is not ready for F1 approval")
    if _p300_bundle(bundle) and _p300_any_owned_processes():
        raise F1LiveError("stale P3.00 USB trace process is still present")
    run_dir = _validate_private_run_dir(root, run_dir)
    preflight = run_dir / "preflight"
    preflight.mkdir(mode=0o700)
    result = d0.collect_connected(bundle, preflight, client, usb_root)
    d0.validate_result(result, bundle, preflight)
    private_target = _private_target(client, result)
    private_path = run_dir / "target-private.json"
    _write_exclusive(private_path, private_target)
    d0_path = preflight / "result.json"
    d0_receipt = _receipt(d0_path, "prepared D0 result")
    private_receipt = _receipt(private_path, "private target")
    p324_lane_receipt = _prepare_p324_typec_lane(
        bundle,
        run_dir,
        private_target,
        usb_root=usb_root,
        typec_root=typec_root,
    )
    closure = _closure(root, bundle)
    binding, binding_sha256 = _binding(
        bundle,
        result,
        d0_receipt,
        private_receipt,
        closure,
        p324_lane_receipt,
    )
    p300_binding = _prepare_p300_usb_binding(
        root, bundle, run_dir, binding_sha256
    )
    prepared = {
        "schema": PREPARED_SCHEMA,
        "adapter_version": ADAPTER_VERSION,
        "manifest_id": bundle.manifest["manifest_id"],
        "bundle_sha256": bundle.sha256,
        "manifest_status": bundle.manifest["status"],
        "d0_result": d0_receipt,
        "private_target": private_receipt,
        "execution_closure": closure,
        "approval_binding": binding,
        "approval_binding_sha256": binding_sha256,
        "approval_token": APPROVAL_PREFIX + binding_sha256,
        "p300_usb_trace_binding": p300_binding,
        "device_contact": True,
        "device_writes": False,
        "reboot_requested": False,
        "odin_invoked": False,
        "partition_transfer": False,
        "f1_authorized": False,
        "live_authorized": False,
    }
    if _p328_bundle(bundle):
        prepared["p328_auth_key_identity"] = dict(P328_AUTH_KEY_IDENTITY)
    if p324_lane_receipt is not None:
        prepared["p324_typec_lane_binding"] = p324_lane_receipt
    candidate_arrival_role = bundle.manifest["observation"].get(
        typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY
    )
    if candidate_arrival_role is not None:
        _candidate_arrival_proof_role(bundle)
        prepared[typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY] = (
            candidate_arrival_role
        )
    _write_exclusive(run_dir / "prepared.json", prepared)
    return prepared


def load_prepared(root: Path, manifest_path: Path, run_dir: Path) -> PreparedRun:
    root = root.resolve()
    run_dir = _validate_private_run_dir(root, run_dir)
    bundle = core.verify_bundle(root, manifest_path, runtime_bound=True)
    prepared = _read_json(run_dir / "prepared.json", "prepared F1 record")
    expected_keys = {
        "schema",
        "adapter_version",
        "manifest_id",
        "bundle_sha256",
        "manifest_status",
        "d0_result",
        "private_target",
        "execution_closure",
        "approval_binding",
        "approval_binding_sha256",
        "approval_token",
        "p300_usb_trace_binding",
        "device_contact",
        "device_writes",
        "reboot_requested",
        "odin_invoked",
        "partition_transfer",
        "f1_authorized",
        "live_authorized",
    }
    candidate_arrival_role = bundle.manifest["observation"].get(
        typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY
    )
    if candidate_arrival_role is not None:
        expected_keys.add(typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY)
    if _p328_bundle(bundle):
        expected_keys.add("p328_auth_key_identity")
    if _p324_lane_bundle(bundle):
        expected_keys.add("p324_typec_lane_binding")
    if set(prepared) != expected_keys:
        raise F1LiveError("prepared F1 record shape mismatch")
    if (
        prepared["schema"] != PREPARED_SCHEMA
        or prepared["adapter_version"] != ADAPTER_VERSION
        or prepared["manifest_id"] != bundle.manifest["manifest_id"]
        or prepared["bundle_sha256"] != bundle.sha256
        or prepared["manifest_status"] != "ready-for-f1-approval"
        or bundle.manifest["status"] != "ready-for-f1-approval"
        or prepared["approval_token"]
        != APPROVAL_PREFIX + prepared["approval_binding_sha256"]
        or prepared["device_contact"] is not True
        or any(
            prepared[key] is not False
            for key in (
                "device_writes",
                "reboot_requested",
                "odin_invoked",
                "partition_transfer",
                "f1_authorized",
                "live_authorized",
            )
        )
    ):
        raise F1LiveError("prepared F1 record header mismatch")
    if _p328_bundle(bundle) and (
        prepared.get("p328_auth_key_identity")
        != P328_AUTH_KEY_IDENTITY
        or prepared.get("p328_auth_key_identity")
        != prepared.get("approval_binding", {}).get("p328_auth_key_identity")
    ):
        raise F1LiveError("P3.28 prepared auth-key identity differs")
    if candidate_arrival_role is not None:
        if (
            prepared.get(typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY)
            != candidate_arrival_role
        ):
            raise F1LiveError("prepared candidate arrival proof role mismatch")
        _candidate_arrival_proof_role(bundle)
    closure = _closure(root, bundle)
    if prepared["execution_closure"] != closure:
        raise F1LiveError("execution-critical source closure changed")
    d0_path = run_dir / "preflight/result.json"
    private_path = run_dir / "target-private.json"
    if prepared["d0_result"] != _receipt(d0_path, "prepared D0 result"):
        raise F1LiveError("prepared D0 result identity changed")
    if prepared["private_target"] != _receipt(private_path, "private target"):
        raise F1LiveError("private target identity changed")
    d0_result = _read_json(d0_path, "prepared D0 result")
    d0.validate_result(d0_result, bundle, run_dir / "preflight")
    private_target = _read_json(private_path, "private target")
    if set(private_target) != {"schema", "serial", "topology"} or private_target[
        "schema"
    ] != PRIVATE_TARGET_SCHEMA:
        raise F1LiveError("private target shape mismatch")
    target = d0_result["target_evidence"]["targets"][0]
    if (
        hashlib.sha256(private_target["serial"].encode()).hexdigest()
        != target["adb_serial_sha256"]
        or hashlib.sha256(private_target["topology"].encode()).hexdigest()
        != target["usb_topology_sha256"]
    ):
        raise F1LiveError("private target no longer matches D0 evidence")
    p324_lane_receipt = None
    if _p324_lane_bundle(bundle):
        temporary_prepared = PreparedRun(
            root, run_dir, bundle, prepared, private_target
        )
        _lane_value, p324_lane_receipt = _p324_typec_lane_value(
            temporary_prepared,
            revalidate=True,
        )
    binding, binding_sha256 = _binding(
        bundle,
        d0_result,
        prepared["d0_result"],
        prepared["private_target"],
        closure,
        p324_lane_receipt,
    )
    if (
        prepared["approval_binding"] != binding
        or prepared["approval_binding_sha256"] != binding_sha256
    ):
        raise F1LiveError("prepared approval binding mismatch")
    expected_p300 = _p300_usb_binding_value(
        root, bundle, run_dir, binding_sha256
    )
    binding_receipt = prepared["p300_usb_trace_binding"]
    if expected_p300 is None:
        if binding_receipt is not None:
            raise F1LiveError("non-P3.00 run has a USB trace binding")
    else:
        binding_path = run_dir / "p300-usb-trace-binding.json"
        if (
            not isinstance(binding_receipt, dict)
            or binding_receipt
            != _receipt(binding_path, "prepared P3.00 USB trace binding")
            or _read_json(binding_path, "prepared P3.00 USB trace binding")
            != expected_p300
        ):
            raise F1LiveError("prepared P3.00 USB trace binding mismatch")
        try:
            p300_usb_trace.verify_binding(expected_p300)
        except p300_usb_trace.BindingError as exc:
            raise F1LiveError(str(exc)) from exc
    return PreparedRun(root, run_dir, bundle, prepared, private_target)


def _read_sysfs(path: Path, label: str) -> str | None:
    try:
        payload = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise F1LiveError(f"Download sysfs read failed: {label}") from exc
    if len(payload) > 512:
        raise F1LiveError(f"Download sysfs value is oversized: {label}")
    try:
        return payload.decode("utf-8", "strict").strip()
    except UnicodeError as exc:
        raise F1LiveError(f"Download sysfs value is invalid: {label}") from exc


def validate_download_endpoint(
    device: str,
    topology: str,
    profile: dict[str, Any],
    usb_root: Path = DEFAULT_USB_ROOT,
) -> dict[str, Any]:
    if transport.ODIN_DEVICE_RE.fullmatch(device) is None:
        raise F1LiveError("Download endpoint path is not canonical")
    match = re.fullmatch(r"usb:([0-9]+)-([0-9]+(?:\.[0-9]+)*)", topology)
    if match is None:
        raise F1LiveError("prepared Android USB topology is malformed")
    node_name = f"{match.group(1)}-{match.group(2)}"
    node = usb_root / node_name
    if not node.exists():
        raise F1LiveError("prepared USB topology has no Download sysfs node")
    coordinates = re.fullmatch(r"/dev/bus/usb/([0-9]{3})/([0-9]{3})", device)
    assert coordinates is not None
    download = profile["target"]["download"]
    names = (
        "busnum",
        "devnum",
        "idVendor",
        "idProduct",
        "product",
        "manufacturer",
        "serial",
    )
    values = {
        name: _read_sysfs(node / name, name)
        for name in names
    }
    repeated = {name: _read_sysfs(node / name, name) for name in names}
    if (
        values != repeated
        or values["busnum"] != str(int(coordinates.group(1)))
        or values["devnum"] != str(int(coordinates.group(2)))
        or values["idVendor"] != download["usb_vendor_id"]
        or values["idProduct"] != download["usb_product_id"]
        or values["product"] != download["product"]
        or values["manufacturer"] != download["manufacturer"]
        or values["serial"] not in {None, ""}
    ):
        raise F1LiveError("Download endpoint does not match the prepared target")
    return {
        "endpoint_sha256": hashlib.sha256(device.encode()).hexdigest(),
        "topology_sha256": hashlib.sha256(topology.encode()).hexdigest(),
        "identity": {
            "vendor": values["idVendor"],
            "product_id": values["idProduct"],
            "product": values["product"],
            "manufacturer": values["manufacturer"],
            "serial_absent": True,
        },
    }


def classify_acceptance(payload: bytes, acceptance: dict[str, Any]) -> dict[str, Any]:
    if acceptance.get("kind") == typed_evidence.SAME_RING_KIND:
        try:
            return typed_evidence.classify_same_ring(payload, acceptance)
        except typed_evidence.EvidenceError as exc:
            raise F1LiveError(str(exc)) from exc
    if acceptance.get("kind") == typed_evidence.SAME_RING_MULTIBOOT_KIND:
        try:
            return typed_evidence.classify_same_ring_multiboot(payload, acceptance)
        except typed_evidence.EvidenceError as exc:
            raise F1LiveError(str(exc)) from exc
    if acceptance.get("kind") == typed_evidence.E1_LATEST_STAGE_KIND:
        try:
            return typed_evidence.classify_e1_latest_stage(payload, acceptance)
        except typed_evidence.EvidenceError as exc:
            raise F1LiveError(str(exc)) from exc
    if acceptance.get("kind") == typed_evidence.PID1_USERSPACE_KIND:
        try:
            return typed_evidence.classify_pid1_userspace(payload, acceptance)
        except typed_evidence.EvidenceError as exc:
            raise F1LiveError(str(exc)) from exc
    if acceptance.get("kind") == typed_evidence.CHECKPOINT_KIND:
        try:
            return typed_evidence.classify_checkpoint(payload, acceptance)
        except typed_evidence.EvidenceError as exc:
            raise F1LiveError(str(exc)) from exc
    marker = acceptance["marker"].encode()
    family = acceptance["family"].encode()
    classification = live_core.classify_marker_family(
        payload,
        exact_marker=b"\n" + marker + b"\n",
        family_prefix=family,
    )
    classification["accepted"] = (
        classification["acceptance_present"] is True
        and classification["exact_count"] == acceptance["exact_count"]
        and classification["family_count"] == acceptance["exact_count"]
        and classification["foreign_count"] == 0
        and classification["integrity_issue"] is False
    )
    return classification


def _p319_terminal_projection(classified: dict[str, Any]) -> dict[str, Any]:
    """Validate and retain the P319 stock proof/runtime projection."""
    if not isinstance(classified, dict):
        raise F1LiveError("P3.19 stock classification is not an object")
    try:
        proof = typed_evidence.p319_stock_adapter._proof_class_for_value(  # noqa: SLF001
            classified
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise F1LiveError("P3.19 stock proof class is invalid") from exc
    if classified.get("proof_class") != proof:
        raise F1LiveError("P3.19 stock proof class differs from decoded predicates")
    required_false = (
        "causal_result_allowed",
        "candidate_success",
        "mux_result_claimable",
        "host_silent_claimable",
    )
    if any(classified.get(name) is not False for name in required_false):
        raise F1LiveError("P3.19 stock classification exposes a causal claim")
    if classified.get("acm_supplemental") is not True or classified.get(
        "acm_required_for_acceptance"
    ) is not False:
        raise F1LiveError("P3.19 ACM boundary is not supplemental")
    stock = classified.get("p319_stock")
    if not isinstance(stock, list) or len(stock) > 1:
        raise F1LiveError("P3.19 stock runtime projection is incomplete")
    if proof != "NO_PROOF_OBSERVER" and len(stock) != 1:
        raise F1LiveError("P3.19 stock runtime projection is incomplete")
    return {
        "proof_class": proof,
        "classification": classified.get("classification"),
        "stock": stock,
        "causal_result_allowed": False,
        "candidate_success": False,
        "mux_result_claimable": False,
        "host_silent_claimable": False,
        "acm_supplemental": True,
        "acm_required_for_acceptance": False,
    }


def _p319_exact_equal(left: Any, right: Any) -> bool:
    """Compare the retained JSON domain without Python bool/number coercion."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            _p319_exact_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _p319_exact_equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def _p319_durable_projection(state: dict[str, Any]) -> dict[str, Any]:
    projection = state.get("p319_stock")
    final = state.get("final_evidence")
    observer = final.get("observer") if isinstance(final, dict) else None
    retained = observer.get("p319_stock") if isinstance(observer, dict) else None

    if not isinstance(projection, dict) or not _p319_exact_equal(
        projection, retained
    ):
        raise F1LiveError("P3.19 durable stock projection differs from final evidence")
    if state.get("p319_proof_class") != projection.get("proof_class"):
        raise F1LiveError("P3.19 durable proof class projection differs")
    return projection


def _p320_terminal_projection(classified: dict[str, Any]) -> dict[str, Any]:
    """Validate and retain the ABI-v4 stock projection for P320-P335."""
    if not isinstance(classified, dict):
        raise F1LiveError("P3.20 stock classification is not an object")
    overlay = classified.get("overlay_contract_id")
    is_p335 = overlay == typed_evidence.P335_STOCK_OVERLAY_CONTRACT_ID
    is_p334 = overlay == typed_evidence.P334_STOCK_OVERLAY_CONTRACT_ID
    is_p333 = overlay == typed_evidence.P333_STOCK_OVERLAY_CONTRACT_ID
    is_p332 = overlay == typed_evidence.P332_STOCK_OVERLAY_CONTRACT_ID
    is_p331 = overlay == typed_evidence.P331_STOCK_OVERLAY_CONTRACT_ID
    is_p330 = overlay == typed_evidence.P330_STOCK_OVERLAY_CONTRACT_ID
    is_p329 = overlay == typed_evidence.P329_STOCK_OVERLAY_CONTRACT_ID
    is_p328 = overlay == typed_evidence.P328_STOCK_OVERLAY_CONTRACT_ID
    is_p327 = overlay == typed_evidence.P327_STOCK_OVERLAY_CONTRACT_ID
    is_p326 = overlay == typed_evidence.P326_STOCK_OVERLAY_CONTRACT_ID
    is_p325 = overlay == typed_evidence.P325_STOCK_OVERLAY_CONTRACT_ID
    is_p324 = overlay == typed_evidence.P324_STOCK_OVERLAY_CONTRACT_ID
    is_p323 = overlay == typed_evidence.P323_STOCK_OVERLAY_CONTRACT_ID
    is_p322 = overlay == typed_evidence.P322_STOCK_OVERLAY_CONTRACT_ID
    is_p321 = overlay == typed_evidence.P321_STOCK_OVERLAY_CONTRACT_ID
    adapter = (
        typed_evidence.p335_stock_adapter
        if is_p335
        else typed_evidence.p334_stock_adapter
        if is_p334
        else typed_evidence.p333_stock_adapter
        if is_p333
        else typed_evidence.p332_stock_adapter
        if is_p332
        else typed_evidence.p331_stock_adapter
        if is_p331
        else typed_evidence.p330_stock_adapter
        if is_p330
        else typed_evidence.p329_stock_adapter
        if is_p329
        else typed_evidence.p328_stock_adapter
        if is_p328
        else typed_evidence.p327_stock_adapter
        if is_p327
        else
        typed_evidence.p326_stock_adapter
        if is_p326
        else typed_evidence.p325_stock_adapter
        if is_p325
        else
        typed_evidence.p324_stock_adapter
        if is_p324
        else typed_evidence.p323_stock_adapter
        if is_p323
        else
        typed_evidence.p322_stock_adapter
        if is_p322
        else typed_evidence.p321_stock_adapter
        if is_p321
        else typed_evidence.p320_stock_adapter
    )
    label = (
        "P3.35"
        if is_p335
        else "P3.34"
        if is_p334
        else "P3.33"
        if is_p333
        else "P3.32"
        if is_p332
        else "P3.31"
        if is_p331
        else "P3.30"
        if is_p330
        else "P3.29"
        if is_p329
        else "P3.28"
        if is_p328
        else "P3.27"
        if is_p327
        else
        "P3.26"
        if is_p326
        else "P3.25"
        if is_p325
        else
        "P3.24"
        if is_p324
        else "P3.23"
        if is_p323
        else "P3.22"
        if is_p322
        else "P3.21"
        if is_p321
        else "P3.20"
    )
    stock_key = (
        "p335_stock"
        if is_p335
        else "p334_stock"
        if is_p334
        else "p333_stock"
        if is_p333
        else "p332_stock"
        if is_p332
        else "p331_stock"
        if is_p331
        else "p330_stock"
        if is_p330
        else "p329_stock"
        if is_p329
        else "p328_stock"
        if is_p328
        else "p327_stock"
        if is_p327
        else
        "p326_stock"
        if is_p326
        else "p325_stock"
        if is_p325
        else
        "p324_stock"
        if is_p324
        else "p323_stock"
        if is_p323
        else "p322_stock"
        if is_p322
        else "p321_stock"
        if is_p321
        else "p320_stock"
    )
    try:
        if (
            (is_p335 or is_p334 or is_p333 or is_p332)
            and classified.get("proof_class") == "NO_PROOF_OBSERVER"
            and classified.get("candidate_success") is False
        ):
            proof = "NO_PROOF_OBSERVER"
        elif is_p335 or is_p334 or is_p333 or is_p332 or is_p331 or is_p330 or is_p329 or is_p328:
            proof = adapter.proof_class(classified)
        elif is_p327:
            proof = adapter._proof_class_for_value(classified)  # noqa: SLF001
        elif (
            (is_p323 or is_p324 or is_p325 or is_p326)
            and classified.get("proof_class")
            == (
                "P326_STOCK_ENCODER_FAILURE"
                if is_p326
                else "P325_STOCK_ENCODER_FAILURE"
                if is_p325
                else "P324_STOCK_ENCODER_FAILURE"
                if is_p324
                else "P323_STOCK_ENCODER_FAILURE"
            )
            and adapter._encoder_failure_shape(classified)  # noqa: SLF001
            and classified.get("producer_failure") is True
            and classified.get("stock_encoder_failure") is True
        ):
            proof = (
                "P326_STOCK_ENCODER_FAILURE"
                if is_p326
                else "P325_STOCK_ENCODER_FAILURE"
                if is_p325
                else "P324_STOCK_ENCODER_FAILURE"
                if is_p324
                else "P323_STOCK_ENCODER_FAILURE"
            )
        else:
            proof = adapter._proof_class_for_value(classified)  # noqa: SLF001
    except (AttributeError, TypeError, ValueError) as exc:
        raise F1LiveError(f"{label} stock proof class is invalid") from exc
    if classified.get("proof_class") != proof:
        raise F1LiveError(f"{label} stock proof class differs from decoded predicates")
    required_false = (
        "causal_result_allowed",
        "candidate_success",
        "mux_result_claimable",
        "host_silent_claimable",
    )
    if any(classified.get(name) is not False for name in required_false):
        raise F1LiveError(f"{label} stock classification exposes a causal claim")
    acm_primary = (
        is_p335
        or is_p323
        or is_p324
        or is_p325
        or is_p326
        or is_p327
        or is_p328
        or is_p329
        or is_p330
        or is_p331
        or is_p332
        or is_p333
        or is_p334
    )
    expected_acm_supplemental = not acm_primary
    expected_acm_required = acm_primary
    if classified.get("acm_supplemental") is not expected_acm_supplemental or classified.get(
        "acm_required_for_acceptance"
    ) is not expected_acm_required:
        raise F1LiveError(f"{label} ACM boundary is not supplemental")
    stock = classified.get(stock_key)
    if not isinstance(stock, list) or len(stock) > 1:
        raise F1LiveError(f"{label} stock runtime projection is incomplete")
    if proof not in {
        "NO_PROOF_OBSERVER",
        "P323_STOCK_ENCODER_FAILURE",
        "P324_STOCK_ENCODER_FAILURE",
        "P325_STOCK_ENCODER_FAILURE",
        "P326_STOCK_ENCODER_FAILURE",
        "P327_STOCK_ENCODER_FAILURE",
        "P328_STOCK_ENCODER_FAILURE",
        "P329_STOCK_ENCODER_FAILURE",
        "P330_STOCK_ENCODER_FAILURE",
        "P331_STOCK_ENCODER_FAILURE",
        "P332_STOCK_ENCODER_FAILURE",
        "P333_STOCK_ENCODER_FAILURE",
        "P334_STOCK_ENCODER_FAILURE",
        "P335_STOCK_ENCODER_FAILURE",
    } and len(stock) != 1:
        raise F1LiveError(f"{label} stock runtime projection is incomplete")
    result = {
        "proof_class": proof,
        "classification": classified.get("classification"),
        "stock": stock,
        "causal_result_allowed": False,
        "candidate_success": False,
        "mux_result_claimable": False,
        "host_silent_claimable": False,
        "acm_supplemental": expected_acm_supplemental,
        "acm_required_for_acceptance": expected_acm_required,
        **(
            {
                "acm_primary": True,
                "carrier_supplemental": True,
                "acm_required_for_arrival_proof": True,
            }
            if acm_primary
            else {}
        ),
    }
    if acm_primary and proof in {
        "P323_STOCK_ENCODER_FAILURE",
        "P324_STOCK_ENCODER_FAILURE",
        "P325_STOCK_ENCODER_FAILURE",
        "P326_STOCK_ENCODER_FAILURE",
        "P327_STOCK_ENCODER_FAILURE",
        "P328_STOCK_ENCODER_FAILURE",
        "P329_STOCK_ENCODER_FAILURE",
        "P330_STOCK_ENCODER_FAILURE",
        "P331_STOCK_ENCODER_FAILURE",
        "P332_STOCK_ENCODER_FAILURE",
        "P333_STOCK_ENCODER_FAILURE",
        "P334_STOCK_ENCODER_FAILURE",
        "P335_STOCK_ENCODER_FAILURE",
    }:
        result["producer_failure"] = True
        result["max77705_scientific_result"] = "NOT_PRODUCED"
        result["exact_encoder_predicate"] = "UNKNOWN_NOT_RETAINED"
    return result


def _p320_durable_projection(state: dict[str, Any]) -> dict[str, Any]:
    is_p334 = "p334_proof_class" in state
    is_p333 = "p333_proof_class" in state
    is_p332 = "p332_proof_class" in state
    is_p331 = "p331_proof_class" in state
    is_p330 = "p330_stock" in state
    is_p329 = "p329_stock" in state
    is_p328 = "p328_stock" in state
    is_p327 = "p327_stock" in state
    is_p326 = "p326_stock" in state
    is_p325 = "p325_stock" in state
    is_p324 = "p324_stock" in state
    is_p322 = "p322_stock" in state
    is_p321 = "p321_stock" in state
    label = (
        "P3.34"
        if is_p334
        else "P3.33"
        if is_p333
        else "P3.32"
        if is_p332
        else "P3.31"
        if is_p331
        else "P3.30"
        if is_p330
        else "P3.29"
        if is_p329
        else "P3.28"
        if is_p328
        else "P3.27"
        if is_p327
        else
        "P3.26"
        if is_p326
        else "P3.25"
        if is_p325
        else
        "P3.24"
        if is_p324
        else "P3.22"
        if is_p322
        else "P3.21"
        if is_p321
        else "P3.20"
    )
    stock_key = (
        "p334_stock"
        if is_p334
        else "p333_stock"
        if is_p333
        else "p332_stock"
        if is_p332
        else "p331_stock"
        if is_p331
        else "p330_stock"
        if is_p330
        else "p329_stock"
        if is_p329
        else "p328_stock"
        if is_p328
        else "p327_stock"
        if is_p327
        else
        "p326_stock"
        if is_p326
        else "p325_stock"
        if is_p325
        else
        "p324_stock"
        if is_p324
        else "p322_stock"
        if is_p322
        else "p321_stock"
        if is_p321
        else "p320_stock"
    )
    final = state.get("final_evidence")
    observer = final.get("observer") if isinstance(final, dict) else None
    retained = observer.get(stock_key) if isinstance(observer, dict) else None
    projection = retained if is_p331 else state.get(stock_key)
    if not isinstance(projection, dict) or (
        not is_p331 and not _p319_exact_equal(projection, retained)
    ):
        raise F1LiveError(f"{label} durable stock projection differs from final evidence")
    proof_key = (
        "p334_proof_class"
        if is_p334
        else "p333_proof_class"
        if is_p333
        else "p332_proof_class"
        if is_p332
        else "p331_proof_class"
        if is_p331
        else "p330_proof_class"
        if is_p330
        else "p329_proof_class"
        if is_p329
        else "p328_proof_class"
        if is_p328
        else "p327_proof_class"
        if is_p327
        else
        "p326_proof_class"
        if is_p326
        else "p325_proof_class"
        if is_p325
        else
        "p324_proof_class"
        if is_p324
        else "p322_proof_class"
        if is_p322
        else "p321_proof_class"
        if is_p321
        else "p320_proof_class"
    )
    if state.get(proof_key) != projection.get("proof_class"):
        raise F1LiveError(f"{label} durable proof class projection differs")
    return projection


def _persist_bytes(path: Path, payload: bytes) -> dict[str, Any]:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o400,
    )
    try:
        if os.write(descriptor, payload) != len(payload):
            raise F1LiveError(f"short evidence write: {path.name}")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    core._fsync_dir(path.parent)
    return _receipt(path, path.name, max(len(payload), 1) + 1)


def _reconcile_transfer_attempts(
    prepared: PreparedRun,
    journal: core.Journal,
    kind: str,
    *,
    repair_orphan_start: bool,
) -> int:
    if kind not in {"candidate", "rollback"}:
        raise F1LiveError("unknown F1 transfer kind")
    action = f"{kind}_transfer_attempt"
    paths = sorted(prepared.run_dir.glob(f"{kind}-attempt-*.start.json"))
    if len(paths) > MAX_ATTEMPTS or any(
        path.name != f"{kind}-attempt-{index:02d}.start.json"
        for index, path in enumerate(paths, 1)
    ):
        raise F1LiveError(f"{kind} transfer evidence sequence is invalid")
    receipts: list[dict[str, Any]] = []
    for index, path in enumerate(paths, 1):
        prefix = f"{kind}-attempt-{index:02d}"
        value = _read_json(path, f"{kind} transfer attempt start")
        if value != {
            "schema": "device_action_f1_transfer_attempt_start_v2",
            "kind": kind,
            "attempt": index,
            "prefix": prefix,
            "approval_binding_sha256": prepared.binding_sha256,
        }:
            raise F1LiveError(f"{kind} transfer attempt start is malformed")
        try:
            receipts.append(_receipt(path, f"{kind} transfer attempt start"))
        except core.F1V2Error as exc:
            raise F1LiveError(f"{kind} transfer attempt start is unavailable") from exc
    checkpoints = [
        record
        for record in journal.records()
        if record["kind"] == "checkpoint" and record["action"] == action
    ]
    if len(checkpoints) > len(paths) or len(paths) - len(checkpoints) > 1:
        raise F1LiveError(f"{kind} transfer attempt ledger is inconsistent")
    for index, record in enumerate(checkpoints, 1):
        if record["details"] != {"attempt": index, "start": receipts[index - 1]}:
            raise F1LiveError(f"{kind} transfer checkpoint does not bind its start")
    if len(paths) == len(checkpoints) + 1:
        if not repair_orphan_start:
            raise F1LiveError(f"{kind} transfer start lacks its checkpoint")
        attempt = len(paths)
        journal.checkpoint(
            action,
            "attempt_started",
            {"attempt": attempt, "start": receipts[-1]},
        )
    return len(paths)


def _begin_transfer_attempt(
    prepared: PreparedRun, journal: core.Journal, kind: str
) -> tuple[int, str, dict[str, Any]]:
    consumed = _reconcile_transfer_attempts(
        prepared, journal, kind, repair_orphan_start=True
    )
    if consumed >= MAX_ATTEMPTS:
        raise F1LiveError(f"{kind} transfer attempt bound exceeded")
    attempt = consumed + 1
    prefix = f"{kind}-attempt-{attempt:02d}"
    value = {
        "schema": "device_action_f1_transfer_attempt_start_v2",
        "kind": kind,
        "attempt": attempt,
        "prefix": prefix,
        "approval_binding_sha256": prepared.binding_sha256,
    }
    path = prepared.run_dir / f"{prefix}.start.json"
    _write_exclusive(path, value)
    start = _receipt(path, f"{kind} transfer attempt start")
    journal.checkpoint(
        f"{kind}_transfer_attempt",
        "attempt_started",
        {"attempt": attempt, "start": start},
    )
    return attempt, prefix, start


def _candidate_registry_identity(prepared: PreparedRun) -> dict[str, Any]:
    """Reopen the verified candidate AP and derive its global identity."""

    item = prepared.bundle.manifest["candidate_ap"]
    expected = prepared.bundle.receipt.get("candidate_ap")
    if not isinstance(expected, dict):
        raise F1LiveError("candidate AP verification receipt is absent")
    path = core._artifact_path(prepared.root, item, "candidate_ap")
    try:
        with core.pin_boot_only_ap(
            path,
            label="candidate_ap at global registry boundary",
            expected_size=item["size"],
            expected_sha256=item["sha256"],
            require_deterministic_metadata=True,
        ) as pinned:
            frame = core.read_boot_only_member(pinned, label="candidate_ap")
            receipt = {
                **pinned.receipt(),
                "member": {
                    "name": core.BOOT_MEMBER,
                    "size": len(frame),
                    "sha256": hashlib.sha256(frame).hexdigest(),
                },
            }
    except (core.F1V2Error, transport.F1TransportError, OSError) as exc:
        raise F1LiveError("candidate AP cannot be reverified at registry boundary") from exc
    if receipt != expected:
        raise F1LiveError("candidate AP verification receipt changed")
    try:
        return consumed_registry.derive_candidate_identity(
            prepared.bundle.profile,
            prepared.bundle.manifest,
            item["sha256"],
            approval_binding_sha256=prepared.binding_sha256,
            candidate_receipt=receipt,
        )
    except consumed_registry.RegistryError as exc:
        raise F1LiveError("candidate global identity is not verified") from exc


def _bound_candidate_registry_identity(prepared: PreparedRun) -> dict[str, Any]:
    """Re-derive identity from the already-bound manifest and AP receipt."""

    candidate = prepared.bundle.manifest.get("candidate_ap")
    receipt = prepared.bundle.receipt.get("candidate_ap")
    if not isinstance(candidate, Mapping) or not isinstance(receipt, Mapping):
        raise F1LiveError("bound candidate identity is unavailable")
    try:
        return consumed_registry.derive_candidate_identity(
            prepared.bundle.profile,
            prepared.bundle.manifest,
            str(candidate.get("sha256")),
            approval_binding_sha256=prepared.binding_sha256,
            candidate_receipt=receipt,
        )
    except consumed_registry.RegistryError as exc:
        raise F1LiveError("bound candidate identity is invalid") from exc


def _registry_path_receipt(path: Path, label: str) -> dict[str, Any]:
    value = _read_json(path, label)
    receipt = _receipt(path, label)
    return {"value": value, "receipt": receipt}


def _candidate_registry_intent_path(prepared: PreparedRun, kind: str) -> Path:
    if kind not in {"claim", "release"}:
        raise F1LiveError("unknown candidate registry evidence kind")
    return prepared.run_dir / f"candidate-global-{kind}-intent.json"


def _candidate_registry_receipt_path(prepared: PreparedRun, kind: str) -> Path:
    if kind not in {"claim", "release"}:
        raise F1LiveError("unknown candidate registry receipt kind")
    return prepared.run_dir / f"candidate-global-{kind}.json"


def _registry_intent_value(kind: str, identity: Mapping[str, Any]) -> dict[str, Any]:
    if kind not in {"claim", "release"}:
        raise F1LiveError("unknown candidate registry evidence kind")
    return {
        "schema": "device_action_f1_global_registry_intent_v1",
        "kind": kind,
        "candidate_key": identity["candidate_key"],
        "target_profile_sha256": identity["target_profile_sha256"],
        "target_key": identity["target_key"],
        "candidate_ap_sha256": identity["candidate_ap_sha256"],
        "candidate_ap_size": identity["candidate_ap_size"],
        "boot_member_name": identity["boot_member_name"],
        "boot_member_size": identity["boot_member_size"],
        "boot_member_sha256": identity["boot_member_sha256"],
        "manifest_id": identity["manifest_id"],
        "run_id": identity["run_id"],
        "approval_binding_sha256": identity["approval_binding_sha256"],
    }


def _write_registry_intent(prepared: PreparedRun, kind: str, identity: Mapping[str, Any]) -> dict[str, Any]:
    value = _registry_intent_value(kind, identity)
    path = _candidate_registry_intent_path(prepared, kind)
    if path.exists() or path.is_symlink():
        existing = _read_json(path, f"candidate global {kind} intent")
        if existing != value:
            raise F1LiveError(f"candidate global {kind} intent differs")
        return _receipt(path, f"candidate global {kind} intent")
    _write_exclusive(path, value)
    return _receipt(path, f"candidate global {kind} intent")


def _persist_registry_event(prepared: PreparedRun, kind: str, event: Mapping[str, Any]) -> dict[str, Any]:
    path = _candidate_registry_receipt_path(prepared, kind)
    value = dict(event)
    value["schema"] = "device_action_f1_global_registry_receipt_v1"
    if path.exists() or path.is_symlink():
        current = _read_json(path, f"candidate global {kind} receipt")
        if current != value:
            raise F1LiveError(f"candidate global {kind} receipt differs")
        return _receipt(path, f"candidate global {kind} receipt")
    _write_exclusive(path, value)
    return _receipt(path, f"candidate global {kind} receipt")


def _preflight_candidate_global(prepared: PreparedRun, identity: Mapping[str, Any]) -> None:
    """Check the immutable activation deny-list and active claims before Download."""

    try:
        consumed_registry.preflight_candidate(prepared.root, identity)
    except consumed_registry.DuplicateCandidateClaim as exc:
        raise F1LiveError("candidate was already consumed; replay is forbidden") from exc
    except consumed_registry.RegistryError as exc:
        raise F1LiveError("global candidate preflight failed closed") from exc


def _claim_candidate_global(prepared: PreparedRun, identity: Mapping[str, Any]) -> dict[str, Any]:
    _write_registry_intent(prepared, "claim", identity)
    try:
        event = consumed_registry.claim(prepared.root, identity)
    except consumed_registry.DuplicateCandidateClaim as exc:
        raise F1LiveError("candidate global claim is already active or consumed") from exc
    except consumed_registry.RegistryError as exc:
        raise F1LiveError("global candidate claim failed closed") from exc
    receipt = _persist_registry_event(prepared, "claim", event)
    return {"event": event, "receipt": receipt}


def _release_candidate_global(prepared: PreparedRun) -> dict[str, Any]:
    claim_path = _candidate_registry_receipt_path(prepared, "claim")
    if not claim_path.exists() or claim_path.is_symlink():
        raise F1LiveError("candidate global claim receipt is absent")
    claim_value = _read_json(claim_path, "candidate global claim receipt")
    expected_identity = _candidate_registry_identity(prepared)
    claim_record = claim_value.get("record") if isinstance(claim_value, dict) else None
    identity_fields = (
        "candidate_key", "target_profile_sha256", "target_key",
        "candidate_ap_sha256", "candidate_ap_size", "boot_member_name",
        "boot_member_size", "boot_member_sha256", "manifest_id", "run_id",
        "approval_binding_sha256",
    )
    if not isinstance(claim_record, dict) or any(
        claim_record.get(field) != expected_identity.get(field)
        for field in identity_fields
    ):
        raise F1LiveError("candidate global claim owner differs from prepared identity")
    # A release is permitted only after the durable local parser has reopened
    # the exact raw result and classified it as the pre-session exception.
    state = _state(prepared)
    if state.get("candidate_classification") != "odin_local_parse_failure" or state.get("candidate_possible_device_session") is not False:
        raise F1LiveError("candidate global release lacks exact pre-session proof")
    try:
        event = consumed_registry.release(prepared.root, claim_value)
    except consumed_registry.RegistryError as exc:
        raise F1LiveError("candidate global release is pending and remains consumed") from exc
    return _persist_registry_event(prepared, "release", event)


def _next_execute_preflight(run_dir: Path) -> Path:
    paths = sorted(run_dir.glob("execute-preflight-*"))
    expected = [
        f"execute-preflight-{index:02d}" for index in range(1, len(paths) + 1)
    ]
    if [path.name for path in paths] != expected or any(
        path.is_symlink() or not path.is_dir() for path in paths
    ):
        raise F1LiveError("execution preflight evidence sequence is invalid")
    if len(paths) >= MAX_ATTEMPTS:
        raise F1LiveError("execution preflight fails-twice bound exceeded")
    return run_dir / f"execute-preflight-{len(paths) + 1:02d}"


def _classify_odin_capture(
    handle: raw_capture.RawCaptureHandle,
) -> tuple[str, bytes, bytes]:
    if not isinstance(handle, raw_capture.RawCaptureHandle):
        raise F1LiveError("Odin parser input is not a raw capture handle")
    try:
        stdout = raw_capture.read_stdout(handle, maximum=MAX_ODIN_OUTPUT)
        stderr = raw_capture.read_stderr(handle, maximum=MAX_ODIN_OUTPUT)
    except raw_capture.RawCaptureError as exc:
        raise F1LiveError("Odin raw capture cannot be reopened") from exc
    classification = (
        "odin_device_session_failure_or_unknown"
        if (
            handle.producer_error_type is not None
            or handle.timed_out
            or handle.output_exceeded
            or type(handle.returncode) is not int
        )
        else core.classify_odin_output(handle.returncode, stdout, stderr)
    )
    return classification, stdout, stderr


class SamsungOdinBackend:
    def __init__(
        self,
        root: Path,
        bundle: core.Bundle,
        adb: Path,
        usb_root: Path = DEFAULT_USB_ROOT,
        typec_root: Path = DEFAULT_TYPEC_ROOT,
    ):
        self.root = root.resolve()
        self.bundle = bundle
        self.adb = adb.resolve(strict=True)
        self.client = d0.adb_client_for_bundle(adb, bundle)
        self.usb_root = usb_root
        self.typec_root = typec_root
        self.odin = core._artifact_path(
            self.root, bundle.profile["transport"]["odin"], "odin"
        )

    def recheck_android(
        self, prepared: PreparedRun, destination: Path
    ) -> dict[str, Any]:
        destination.mkdir(mode=0o700)
        result = d0.collect_connected(
            prepared.bundle, destination, self.client, self.usb_root
        )
        if result["target_evidence"] != _read_json(
            prepared.run_dir / "preflight/result.json", "prepared D0 result"
        )["target_evidence"]:
            raise F1LiveError("execution-time D0 target differs from preparation")
        serial = self.client.one_serial()
        topology = self.client.topology(serial)
        if (
            serial != prepared.private_target["serial"]
            or topology != prepared.private_target["topology"]
        ):
            raise F1LiveError("execution-time private target continuity changed")
        if _p324_lane_bundle(prepared.bundle):
            _p324_typec_lane_value(
                prepared,
                revalidate=True,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
        return {
            "d0_result_sha256": _receipt(
                destination / "result.json", "execution D0 result"
            )["sha256"],
            "target_evidence_sha256": core.json_sha256(result["target_evidence"]),
            "healthy": True,
        }

    def request_download(self, prepared: PreparedRun) -> None:
        try:
            handle = self.client.capture_command(
                [
                    "-s",
                prepared.private_target["serial"],
                "reboot",
                "download",
                ],
                "download-request",
                timeout=DOWNLOAD_REQUEST_TIMEOUT_SEC,
                maximum=d0.MAX_TEXT_OUTPUT,
            )
            raw_capture.require_success(handle)
        except (d0.D0Error, raw_capture.RawCaptureError) as exc:
            raise F1LiveError("Android Download request raw capture failed") from exc

    def endpoint_session(self, run_dir: Path) -> ContextManager[Any]:
        return odin_core.transaction_session(run_dir)

    def candidate_observer_session(
        self, prepared: PreparedRun
    ) -> ContextManager[Any]:
        spec = prepared.bundle.manifest["observation"].get(
            "candidate_observer"
        )
        if spec is None:
            return contextlib.nullcontext(None)
        if _p335_bundle(prepared.bundle):
            lane_value, lane_receipt = _p324_typec_lane_value(
                prepared,
                revalidate=True,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
            return _p335_candidate_observer_session(
                prepared,
                spec,
                lane_value=lane_value,
                lane_receipt=lane_receipt,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
        if _p331_bundle(prepared.bundle):
            lane_value, lane_receipt = _p324_typec_lane_value(
                prepared,
                revalidate=True,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
            return _p331_candidate_observer_session(
                prepared,
                spec,
                lane_value=lane_value,
                lane_receipt=lane_receipt,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
        # Keep the exact P329 selector first for its established test seam;
        # P330 is still checked before the generic P328 family fallback.
        if _p329_bundle(prepared.bundle):
            lane_value, lane_receipt = _p324_typec_lane_value(
                prepared,
                revalidate=True,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
            return _p329_candidate_observer_session(
                prepared,
                spec,
                lane_value=lane_value,
                lane_receipt=lane_receipt,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
        if _p330_bundle(prepared.bundle):
            lane_value, lane_receipt = _p324_typec_lane_value(
                prepared,
                revalidate=True,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
            return _p330_candidate_observer_session(
                prepared,
                spec,
                lane_value=lane_value,
                lane_receipt=lane_receipt,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
        if _p332_bundle(prepared.bundle):
            lane_value, lane_receipt = _p324_typec_lane_value(
                prepared,
                revalidate=True,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
            return _p332_candidate_observer_session(
                prepared,
                spec,
                lane_value=lane_value,
                lane_receipt=lane_receipt,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
        if _p334_bundle(prepared.bundle):
            lane_value, lane_receipt = _p324_typec_lane_value(
                prepared,
                revalidate=True,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
            return _p334_candidate_observer_session(
                prepared,
                spec,
                lane_value=lane_value,
                lane_receipt=lane_receipt,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
        if _p333_bundle(prepared.bundle):
            lane_value, lane_receipt = _p324_typec_lane_value(
                prepared,
                revalidate=True,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
            return _p333_candidate_observer_session(
                prepared,
                spec,
                lane_value=lane_value,
                lane_receipt=lane_receipt,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
        if _p328_bundle(prepared.bundle) and not _p335_bundle(prepared.bundle):
            lane_value, lane_receipt = _p324_typec_lane_value(
                prepared,
                revalidate=True,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
            return _p328_candidate_observer_session(
                prepared,
                spec,
                lane_value=lane_value,
                lane_receipt=lane_receipt,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
        if _p327_bundle(prepared.bundle):
            lane_value, lane_receipt = _p324_typec_lane_value(
                prepared,
                revalidate=True,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
            return _p327_candidate_observer_session(
                prepared,
                spec,
                lane_value=lane_value,
                lane_receipt=lane_receipt,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
        if _p326_bundle(prepared.bundle):
            lane_value, lane_receipt = _p324_typec_lane_value(
                prepared,
                revalidate=True,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
            return p326_console_observer.observer_session(
                spec,
                prepared.private_target["topology"],
                prepared.run_dir,
                _candidate_observer_binding(prepared),
                lane_value,
                lane_receipt,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
        if _p325_bundle(prepared.bundle):
            lane_value, lane_receipt = _p324_typec_lane_value(
                prepared,
                revalidate=True,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
            return p325_guard_adapter.observer_session(
                spec,
                prepared.private_target["topology"],
                prepared.run_dir,
                _candidate_observer_binding(prepared),
                lane_value,
                lane_receipt,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
        if _p324_lane_bundle(prepared.bundle):
            lane_value, lane_receipt = _p324_typec_lane_value(
                prepared,
                revalidate=True,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
            return p324_cdc_observer.observer_session(
                spec,
                prepared.private_target["topology"],
                prepared.run_dir,
                _candidate_observer_binding(prepared),
                lane_value,
                lane_receipt,
                usb_root=self.usb_root,
                typec_root=self.typec_root,
            )
        if _p313_bundle(prepared.bundle):
            return _p313_candidate_observer_session(
                prepared,
                spec,
                usb_root=self.usb_root,
            )
        return cdc_acm_observer.observer_session(
            spec,
            prepared.private_target["topology"],
            prepared.run_dir,
            _candidate_observer_binding(prepared),
            usb_root=self.usb_root,
        )

    def revalidate_candidate_lane(self, prepared: PreparedRun) -> None:
        if not _p324_lane_bundle(prepared.bundle):
            raise F1LiveError(
                "P3.24 Type-C lane revalidation requested for another run"
            )
        _p324_typec_lane_value(
            prepared,
            revalidate=True,
            usb_root=self.usb_root,
            typec_root=self.typec_root,
        )

    def wait_download(
        self,
        prepared: PreparedRun,
        run_dir: Path,
        lease: Any,
        timeout_sec: float,
    ) -> Endpoint:
        sequence = len(odin_core.list_snapshot_receipts(run_dir))
        result = odin_core.wait_for_single_live_endpoint(
            self.odin,
            run_dir,
            timeout_sec=timeout_sec,
            lease=lease,
            sequence_start=sequence,
            poll_sec=0.5,
            endpoint_observer_factory=odin_core.measured_usbfs_observer,
        )
        if result.timed_out or result.ticket is None:
            raise F1LiveError("bounded wait for Download endpoint expired")
        if _p318_bundle(prepared.bundle):
            start_raw_path, start_record_path = _p318_phase_paths(
                prepared, "download_start"
            )
            start_exists = start_raw_path.exists() and start_record_path.exists()
            if (start_raw_path.exists() or start_record_path.exists()) and not start_exists:
                raise F1LiveError("P3.18 Download-start topology evidence is partial")
            phase = "rollback_download" if start_exists else "download_start"
            try:
                topology_raw = p318_topology.capture_download_inventory_raw(
                    phase=phase,
                    profile=prepared.bundle.profile,
                    usb_root=self.usb_root,
                )
                target = _p318_download_target(prepared)
                matching = p318_topology.matching_endpoints(
                    topology_raw, phase=phase, target_identity=target
                )
                if len(matching) == 1 and (
                    matching[0]["identity"]["endpoint_node"]
                    != result.ticket.device
                ):
                    raise P318TopologyPark(
                        "P3.18 Odin ticket and topology snapshot differ"
                    )
                start = (
                    None
                    if phase == "download_start"
                    else p318_topology.start_path(
                        _p318_read_phase(prepared, "download_start")[1]
                    )
                )
                phase_record = _p318_publish_or_reopen_phase(
                    prepared,
                    phase,
                    topology_raw,
                    target_identity=target,
                    binding_id_sha256=prepared.binding_sha256,
                    comparison_binding_id_sha256=prepared.binding_sha256,
                    authority_state=(
                        "candidate_approved_exact"
                        if phase == "download_start"
                        else "rollback_bound_exact"
                    ),
                    causal_terminal_ready=False,
                    start_path=start,
                )
            except P318TopologyPark:
                raise
            except (p318_topology.TopologyReceiptError, F1LiveError) as exc:
                raise P318TopologyPark(str(exc)) from exc
            decision = phase_record["decision"]
            if phase == "download_start" and decision["candidate_eligible"] is not True:
                raise P318TopologyPark("P3.18 Download-start topology is not eligible")
            if phase == "rollback_download" and decision["rollback_resume"] is not True:
                raise P318TopologyPark("P3.18 rollback topology requires reviewed rebinding")
        identity = validate_download_endpoint(
            result.ticket.device,
            prepared.private_target["topology"],
            prepared.bundle.profile,
            self.usb_root,
        )
        revalidated = odin_core.revalidate_endpoint_ticket(
            self.odin,
            run_dir,
            result.ticket,
            sequence=result.next_sequence,
            lease=lease,
            timeout_sec=ENDPOINT_REVALIDATE_SEC,
            endpoint_observer_factory=odin_core.measured_usbfs_observer,
        )
        return Endpoint(
            result.ticket.device,
            result.next_sequence + 1,
            hashlib.sha256(
                (identity["endpoint_sha256"] + revalidated["device_identity"]).encode()
            ).hexdigest(),
        )

    def transfer(
        self,
        prepared: PreparedRun,
        endpoint: Endpoint,
        kind: str,
        destination: Path,
        attempt: int,
        prefix: str,
    ) -> TransferOutcome:
        if kind not in {"candidate", "rollback"}:
            raise F1LiveError("unknown F1 transfer kind")
        item = (
            prepared.bundle.manifest["candidate_ap"]
            if kind == "candidate"
            else prepared.bundle.manifest["rollback_ap"]
        )
        journal = core.Journal.reopen(
            prepared.run_dir / "transaction", prepared.binding_sha256
        )
        consumed = _reconcile_transfer_attempts(
            prepared, journal, kind, repair_orphan_start=False
        )
        start = _read_json(
            prepared.run_dir / f"{prefix}.start.json",
            f"{kind} transfer attempt start",
        )
        if (
            consumed != attempt
            or prefix != f"{kind}-attempt-{attempt:02d}"
            or start.get("attempt") != attempt
            or start.get("kind") != kind
            or start.get("approval_binding_sha256") != prepared.binding_sha256
        ):
            raise F1LiveError(f"{kind} transfer attempt is not durably armed")
        ap = core._artifact_path(self.root, item, f"{kind}_ap")
        odin = prepared.bundle.profile["transport"]["odin"]
        try:
            receipt, raw_handle = transport.execute_odin_boot_only(
                self.odin,
                ap,
                endpoint.device,
                odin_size=odin["size"],
                odin_sha256=odin["sha256"],
                ap_size=item["size"],
                ap_sha256=item["sha256"],
                label=kind,
                require_deterministic_metadata=kind == "candidate",
                timeout=ODIN_TIMEOUT_SEC,
                maximum_output=MAX_ODIN_OUTPUT,
                capture_dir=destination,
                capture_name=f"{prefix}-odin",
                stdout_name=f"{prefix}.stdout",
                stderr_name=f"{prefix}.stderr",
            )
        except (transport.F1TransportError, subprocess.SubprocessError, OSError) as exc:
            failure = {
                "schema": "device_action_f1_transfer_failure_v2",
                "kind": kind,
                "attempt": attempt,
                "prefix": prefix,
                "possible_device_session": True,
                "error_type": type(exc).__name__,
            }
            _write_exclusive(destination / f"{prefix}.result.json", failure)
            return TransferOutcome(
                "odin_device_session_failure_or_unknown", False, True, failure
            )
        classification, stdout, stderr = _classify_odin_capture(raw_handle)
        stdout_receipt = {
            "path": str(raw_handle.stdout_path),
            "size": len(stdout),
            "sha256": hashlib.sha256(stdout).hexdigest(),
        }
        stderr_receipt = {
            "path": str(raw_handle.stderr_path),
            "size": len(stderr),
            "sha256": hashlib.sha256(stderr).hexdigest(),
        }
        value = {
            "schema": "device_action_f1_transfer_receipt_v2",
            "kind": kind,
            "attempt": attempt,
            "prefix": prefix,
            "classification": classification,
            "transport": receipt,
            "stdout": stdout_receipt,
            "stderr": stderr_receipt,
        }
        _write_exclusive(destination / f"{prefix}.result.json", value)
        return TransferOutcome(
            classification,
            classification == "odin_transfer_completed",
            classification != "odin_local_parse_failure",
            value,
        )

    def observe_candidate(
        self,
        prepared: PreparedRun,
        run_dir: Path,
        lease: Any,
        observer_session: Any,
    ) -> dict[str, Any]:
        sequence = len(odin_core.list_snapshot_receipts(run_dir))
        absent = odin_core.wait_for_no_live_endpoint(
            self.odin,
            run_dir,
            timeout_sec=DISCONNECT_WAIT_SEC,
            lease=lease,
            sequence_start=sequence,
            poll_sec=0.5,
            endpoint_observer_factory=odin_core.measured_usbfs_observer,
            allow_live_departure=True,
        )
        timeout = prepared.bundle.manifest["observation"]["timeout_sec"]
        started = time.monotonic()
        departure = {
            "download_endpoint_absent": absent.absent,
            "absence_timed_out": absent.timed_out,
            "sequence": absent.next_sequence,
        }
        spec = prepared.bundle.manifest["observation"].get(
            "candidate_observer"
        )
        if spec is not None:
            if observer_session is not None:
                try:
                    observer_session.observe(
                        timeout_sec=timeout,
                        download_departure=departure,
                    )
                except (
                    cdc_acm_observer.ObserverError,
                    p324_cdc_observer.P324ObserverError,
                    p325_guard_adapter.P325ObserverError,
                    p326_console_observer.P326ObserverError,
                    p327_framed_observer.FramedObserverError,
                    p328_auth_observer.AuthObserverError,
                    p330_auth_observer.AuthObserverError,
                    p331_resident_observer.AuthObserverError,
                    p332_logical_resident_observer.AuthObserverError,
                    p333_open_entry_observer.AuthObserverError,
                    p334_first_read_observer.AuthObserverError,
                    p335_retained_observer.AuthObserverError,
                    OSError,
                ):
                    pass
            durable = _reopen_candidate_observation(prepared)
            result = {
                "bounded": True,
                "download_endpoint_absent": absent.absent,
                "absence_timed_out": absent.timed_out,
                "requested_sec": timeout,
                "elapsed_sec": round(time.monotonic() - started, 6),
                "candidate_execution_proven": durable["accepted"],
                "candidate_observer_classification": durable[
                    "classification"
                ],
                "candidate_observer_accepted": durable["accepted"],
                "candidate_observer_receipt_sha256": durable[
                    "receipt_sha256"
                ],
            }
            if _p327_bundle(prepared.bundle):
                result.update(
                    {
                        "pid1_framed_exec_proof": durable[
                            "pid1_framed_exec_proof"
                        ],
                        "busybox_ash_command_proof": durable[
                            "busybox_ash_command_proof"
                        ],
                        "framed_session_closed": durable[
                            "framed_session_closed"
                        ],
                        "interactive_pty_proof": durable[
                            "interactive_pty_proof"
                        ],
                        "caller_selected_command": durable[
                            "caller_selected_command"
                        ],
                    }
                )
            if (
                _p335_bundle(prepared.bundle)
                or _p334_bundle(prepared.bundle)
                or _p333_bundle(prepared.bundle)
                or _p332_bundle(prepared.bundle)
            ):
                result.update(_p332_proof_state(durable))
                result.update(
                    {
                        "preauth_diagnostics": durable[
                            "preauth_diagnostics"
                        ],
                        "rng_eagain_retries": durable[
                            "rng_eagain_retries"
                        ],
                        "partial_sessions": durable["partial_sessions"],
                    }
                )
                if _p335_bundle(prepared.bundle):
                    result["p335_authenticated_attended_resident"] = durable[
                        "p335_authenticated_attended_resident"
                    ]
                elif _p334_bundle(prepared.bundle):
                    result.update(
                        {
                            "first_console_return_checkpoint_only": durable[
                                "first_console_return_checkpoint_only"
                            ],
                            "first_read_attribution_requires_stage0_without_stage1": durable[
                                "first_read_attribution_requires_stage0_without_stage1"
                            ],
                        }
                    )
            elif _p331_bundle(prepared.bundle):
                result.update(_p331_proof_state(durable))
                result.update(
                    {
                        "preauth_diagnostics": durable[
                            "preauth_diagnostics"
                        ],
                        "rng_eagain_retries": durable[
                            "rng_eagain_retries"
                        ],
                        "partial_sessions": durable["partial_sessions"],
                    }
                )
            elif _p328_bundle(prepared.bundle):
                result.update(
                    {
                        "hmac_authenticated": durable["hmac_authenticated"],
                        "pid1_authenticated_framed_exec_proof": durable[
                            "pid1_authenticated_framed_exec_proof"
                        ],
                        "busybox_ash_command_proof": durable[
                            "busybox_ash_command_proof"
                        ],
                        "framed_session_closed": durable[
                            "framed_session_closed"
                        ],
                        "caller_selected_command": durable[
                            "caller_selected_command"
                        ],
                        "command_count": durable["command_count"],
                        "max_commands": durable["max_commands"],
                        "auth_key_sha256": durable.get("auth_key_sha256"),
                        "challenge_nonce_sha256": durable.get(
                            "challenge_nonce_sha256"
                        ),
                    }
                )
            if _p318_bundle(prepared.bundle):
                try:
                    topology_raw = p318_topology.capture_candidate_raw(
                        phase="candidate_end"
                    )
                except (p318_topology.TopologyReceiptError, OSError):
                    topology_raw = p318_topology.raw_snapshot(
                        phase="candidate_end",
                        capture_complete=False,
                        endpoints=[],
                    )
                topology_receipt = _p318_publish_candidate_raw(
                    prepared, topology_raw
                )
                result["p318_candidate_topology_raw"] = topology_receipt
            return result
        if absent.absent:
            time.sleep(timeout)
        return {
            "bounded": True,
            "download_endpoint_absent": absent.absent,
            "absence_timed_out": absent.timed_out,
            "requested_sec": timeout,
            "elapsed_sec": round(time.monotonic() - started, 6),
            "candidate_execution_proven": False,
        }

    def _wait_final_health(
        self,
        prepared: PreparedRun,
        client: d0.AdbReadOnlyClient,
    ) -> tuple[str, dict[str, Any]]:
        deadline = time.monotonic() + ANDROID_WAIT_SEC
        last_error = "final Android not observed"
        while time.monotonic() < deadline:
            try:
                snapshot = d0.usb_snapshot(
                    self.usb_root, prepared.bundle.profile["target"]["download"]
                )
                if snapshot["download_endpoint_count"]:
                    raise F1LiveError("Download endpoint remains during final health")
                serial = client.one_serial()
                topology = client.topology(serial)
                if (
                    serial != prepared.private_target["serial"]
                    or topology != prepared.private_target["topology"]
                ):
                    raise F1LiveError("final target continuity mismatch")
                properties = client.properties(serial)
                root_health = client.root_health(serial)
                health = d0.validate_health(
                    prepared.bundle,
                    properties,
                    root_health,
                    True,
                    "final_health",
                )
                return serial, health
            except (d0.D0Error, F1LiveError, OSError) as exc:
                last_error = str(exc)
                time.sleep(2)
        raise F1LiveError(f"final Android health wait expired: {last_error}")

    def verify_final(
        self,
        prepared: PreparedRun,
        run_dir: Path,
        lease: Any,
        destination: Path,
    ) -> dict[str, Any]:
        sequence = len(odin_core.list_snapshot_receipts(run_dir))
        absent = odin_core.wait_for_no_live_endpoint(
            self.odin,
            run_dir,
            timeout_sec=DISCONNECT_WAIT_SEC,
            lease=lease,
            sequence_start=sequence,
            poll_sec=0.5,
            endpoint_observer_factory=odin_core.measured_usbfs_observer,
            allow_live_departure=True,
        )
        if not absent.absent:
            raise F1LiveError("rollback Odin endpoint did not disappear")
        final_client = d0.adb_client_for_bundle(self.adb, prepared.bundle)
        final_client.bind_raw_capture_dir(destination)
        serial, health = self._wait_final_health(prepared, final_client)
        acceptance = prepared.bundle.manifest["observation"]["acceptance"]
        payloads: list[bytes] = []
        receipts: list[dict[str, Any]] = []
        for index in (1, 2):
            path = destination / f"rollback-observer-{index}.bin"
            capture = final_client.capture(
                serial, acceptance["source"], path
            )
            try:
                payload = raw_capture.read_stdout(
                    capture.handle, maximum=MAX_OBSERVER_BYTES
                )
                stderr = raw_capture.read_stderr(
                    capture.handle, maximum=d0.MAX_TEXT_OUTPUT
                )
            except raw_capture.RawCaptureError as exc:
                raise F1LiveError(
                    "rollback observer raw handle cannot be reopened"
                ) from exc
            if stderr:
                raise F1LiveError("rollback observer produced stderr")
            payloads.append(payload)
            receipts.append(capture.receipt)
            time.sleep(0.25)
        if not payloads[0] or payloads[0] != payloads[1]:
            raise F1LiveError("rollback observer reads are not stable and identical")
        final_serial = final_client.one_serial()
        final_topology = final_client.topology(final_serial)
        if (
            final_serial != serial
            or final_serial != prepared.private_target["serial"]
            or final_topology != prepared.private_target["topology"]
        ):
            raise F1LiveError("final target changed during observer collection")
        stock_error = None
        try:
            marker_result = classify_acceptance(payloads[0], acceptance)
        except F1LiveError as exc:
            if not _acm_primary_bundle(prepared.bundle):
                raise
            if _p335_bundle(prepared.bundle):
                stock_error = _p335_stock_error(payloads[0], exc)
                marker_result = _p335_parser_failure_classification(
                    payloads[0], exc
                )
            elif _p334_bundle(prepared.bundle):
                stock_error = _p334_stock_error(payloads[0], exc)
                marker_result = _p334_parser_failure_classification(
                    payloads[0], exc
                )
            elif _p333_bundle(prepared.bundle):
                stock_error = _p333_stock_error(payloads[0], exc)
                marker_result = _p333_parser_failure_classification(
                    payloads[0], exc
                )
            elif _p332_bundle(prepared.bundle):
                stock_error = _p332_stock_error(payloads[0], exc)
                marker_result = _p332_parser_failure_classification(
                    payloads[0], exc
                )
            elif _p331_bundle(prepared.bundle):
                stock_error = _p331_stock_error(payloads[0], exc)
                marker_result = _p331_parser_failure_classification(
                    payloads[0], exc
                )
            elif _p330_bundle(prepared.bundle):
                stock_error = _p330_stock_error(payloads[0], exc)
                marker_result = _p330_parser_failure_classification(
                    payloads[0], exc
                )
            elif _p329_bundle(prepared.bundle):
                stock_error = _p329_stock_error(payloads[0], exc)
                marker_result = _p329_parser_failure_classification(
                    payloads[0], exc
                )
            elif _p328_bundle(prepared.bundle):
                stock_error = _p328_stock_error(payloads[0], exc)
                marker_result = _p328_parser_failure_classification(
                    payloads[0], exc
                )
            elif _p327_bundle(prepared.bundle):
                stock_error = _p327_stock_error(payloads[0], exc)
                marker_result = _p327_parser_failure_classification(
                    payloads[0], exc
                )
            elif _p326_bundle(prepared.bundle):
                stock_error = _p326_stock_error(payloads[0], exc)
                marker_result = _p326_parser_failure_classification(
                    payloads[0], exc
                )
            elif _p325_bundle(prepared.bundle):
                stock_error = _p325_stock_error(payloads[0], exc)
                marker_result = _p325_parser_failure_classification(
                    payloads[0], exc
                )
            elif _p324_bundle(prepared.bundle):
                stock_error = _p324_stock_error(payloads[0], exc)
                marker_result = _p324_parser_failure_classification(
                    payloads[0], exc
                )
            else:
                stock_error = _p323_stock_error(payloads[0], exc)
                marker_result = _p323_parser_failure_classification(
                    payloads[0], exc
                )
        p318_topology_evidence = None
        if _p318_bundle(prepared.bundle):
            marker_result, p318_topology_evidence = (
                _p318_finalize_candidate_phase(prepared, marker_result)
            )
        p319_projection = (
            _p319_terminal_projection(marker_result)
            if _p319_bundle(prepared.bundle)
            else None
        )
        p320_projection = (
            _p320_terminal_projection(marker_result)
            if (
                stock_error is None
                and (
                    _p320_bundle(prepared.bundle)
                    or _p321_bundle(prepared.bundle)
                    or _p322_bundle(prepared.bundle)
                    or _p323_bundle(prepared.bundle)
                    or _p324_bundle(prepared.bundle)
                    or _p325_bundle(prepared.bundle)
                    or _p326_bundle(prepared.bundle)
                    or _p327_bundle(prepared.bundle)
                    or _p328_bundle(prepared.bundle)
                    or _p333_bundle(prepared.bundle)
                    or _p334_bundle(prepared.bundle)
                    or _p335_bundle(prepared.bundle)
                )
            )
            else None
        )
        accepted = marker_result["accepted"] is True
        result = {
            "health": health,
            "target_evidence_sha256": core.json_sha256(
                {
                    "serial": hashlib.sha256(serial.encode()).hexdigest(),
                    "topology": hashlib.sha256(
                        prepared.private_target["topology"].encode()
                    ).hexdigest(),
                }
            ),
            "observer": {
                "reads": receipts,
                "byte_identical": True,
                "bytes": len(payloads[0]),
                "sha256": hashlib.sha256(payloads[0]).hexdigest(),
                "exact_marker_count": marker_result["exact_count"],
                "marker_family_count": marker_result["family_count"],
                "classification": marker_result,
                "accepted": accepted,
            },
            "rollback_verified": True,
        }
        if p318_topology_evidence is not None:
            result["p318_candidate_topology"] = p318_topology_evidence
        if p319_projection is not None:
            result["observer"]["p319_stock"] = p319_projection
        if p320_projection is not None:
            result["observer"][
                "p335_stock"
                if _p335_bundle(prepared.bundle)
                else "p334_stock"
                if _p334_bundle(prepared.bundle)
                else "p333_stock"
                if _p333_bundle(prepared.bundle)
                else "p332_stock"
                if _p332_bundle(prepared.bundle)
                else "p331_stock"
                if _p331_bundle(prepared.bundle)
                else "p330_stock"
                if _p330_bundle(prepared.bundle)
                else "p329_stock"
                if _p329_bundle(prepared.bundle)
                else "p328_stock"
                if _p328_bundle(prepared.bundle)
                else "p327_stock"
                if _p327_bundle(prepared.bundle)
                else "p326_stock"
                if _p326_bundle(prepared.bundle)
                else "p325_stock"
                if _p325_bundle(prepared.bundle)
                else "p324_stock"
                if _p324_bundle(prepared.bundle)
                else "p323_stock"
                if _p323_bundle(prepared.bundle)
                else "p322_stock"
                if _p322_bundle(prepared.bundle)
                else "p321_stock"
                if _p321_bundle(prepared.bundle)
                else "p320_stock"
            ] = p320_projection
        if stock_error is not None:
            key = (
                "p335_stock_error"
                if _p335_bundle(prepared.bundle)
                else "p334_stock_error"
                if _p334_bundle(prepared.bundle)
                else "p333_stock_error"
                if _p333_bundle(prepared.bundle)
                else "p332_stock_error"
                if _p332_bundle(prepared.bundle)
                else "p331_stock_error"
                if _p331_bundle(prepared.bundle)
                else "p330_stock_error"
                if _p330_bundle(prepared.bundle)
                else "p329_stock_error"
                if _p329_bundle(prepared.bundle)
                else "p328_stock_error"
                if _p328_bundle(prepared.bundle)
                else "p327_stock_error"
                if _p327_bundle(prepared.bundle)
                else "p326_stock_error"
                if _p326_bundle(prepared.bundle)
                else "p325_stock_error"
                if _p325_bundle(prepared.bundle)
                else
                "p324_stock_error"
                if _p324_bundle(prepared.bundle)
                else "p323_stock_error"
            )
            result["observer"][key] = stock_error
            result["observer"].pop(
                "p335_stock"
                if _p335_bundle(prepared.bundle)
                else "p334_stock"
                if _p334_bundle(prepared.bundle)
                else "p333_stock"
                if _p333_bundle(prepared.bundle)
                else "p332_stock"
                if _p332_bundle(prepared.bundle)
                else "p331_stock"
                if _p331_bundle(prepared.bundle)
                else "p330_stock"
                if _p330_bundle(prepared.bundle)
                else "p329_stock"
                if _p329_bundle(prepared.bundle)
                else "p328_stock"
                if _p328_bundle(prepared.bundle)
                else "p327_stock"
                if _p327_bundle(prepared.bundle)
                else "p326_stock"
                if _p326_bundle(prepared.bundle)
                else "p325_stock"
                if _p325_bundle(prepared.bundle)
                else "p324_stock"
                if _p324_bundle(prepared.bundle)
                else "p323_stock",
                None,
            )
        return result


def _live_state_path(prepared: PreparedRun) -> Path:
    return prepared.run_dir / "live-state.json"


def _candidate_observer_binding(prepared: PreparedRun) -> dict[str, str]:
    value: dict[str, str] = {
        "approval_binding_sha256": prepared.binding_sha256,
        "bundle_sha256": prepared.bundle.sha256,
        "manifest_id": prepared.bundle.manifest["manifest_id"],
        "candidate_ap_sha256": prepared.bundle.manifest["candidate_ap"][
            "sha256"
        ],
    }
    if _p328_bundle(prepared.bundle):
        value["p328_auth_key_sha256"] = _p328_bound_auth_key_identity(
            prepared
        )["sha256"]
    return value


P313_GUARD_LIFETIME_ARM = "candidate-observer-guard-lifetime-arm.json"
P313_GUARD_LIFETIME_RELEASE = "candidate-observer-guard-lifetime-release.json"


def _p313_bound_guard_derivation(prepared: PreparedRun) -> dict[str, Any]:
    derivation = _p313_guard_derivation(prepared.bundle)
    if derivation is None:
        raise F1LiveError("P3.13 guard lifetime requested for another overlay")
    expected = {
        "derivation": derivation,
        "derivation_sha256": p313_guard_lifetime.digest(derivation),
    }
    approval = prepared.prepared.get("approval_binding")
    if (
        not isinstance(approval, dict)
        or approval.get("candidate_observer_guard_lifetime") != expected
    ):
        raise F1LiveError("P3.13 guard lifetime is not approval-bound")
    return derivation


@contextlib.contextmanager
def _p313_candidate_observer_session(
    prepared: PreparedRun,
    spec: dict[str, str],
    *,
    usb_root: Path,
):
    derivation = _p313_bound_guard_derivation(prepared)
    started_ns = time.monotonic_ns()
    lifetime_arm_path = prepared.run_dir / P313_GUARD_LIFETIME_ARM
    lifetime_release_path = prepared.run_dir / P313_GUARD_LIFETIME_RELEASE
    arm_receipt: dict[str, Any] | None = None
    try:
        with cdc_acm_observer.observer_session(
            spec,
            prepared.private_target["topology"],
            prepared.run_dir,
            _candidate_observer_binding(prepared),
            usb_root=usb_root,
            max_sec=derivation["max_sec"],
        ) as session:
            v2_arm = _receipt(
                prepared.run_dir / "candidate-observer-guard.json",
                "candidate observer v2 guard arm",
            )
            arm_value = p313_guard_lifetime.arm_value(
                approval_binding_sha256=prepared.binding_sha256,
                derivation=derivation,
                v2_arm_receipt_sha256=v2_arm["sha256"],
            )
            _write_exclusive(lifetime_arm_path, arm_value)
            arm_receipt = _receipt(
                lifetime_arm_path, "P3.13 guard lifetime arm"
            )
            yield session
    finally:
        # Candidate-side exceptions must never suppress mandatory rollback.
        # Missing or malformed lifetime release evidence is detected by reopen.
        if arm_receipt is not None:
            try:
                v2_release = _receipt(
                    prepared.run_dir / "candidate-observer-guard-release.json",
                    "candidate observer v2 guard release",
                )
                elapsed_upper_millis = (
                    time.monotonic_ns() - started_ns + 999_999
                ) // 1_000_000
                _write_exclusive(
                    lifetime_release_path,
                    p313_guard_lifetime.release_value(
                        lifetime_arm_sha256=arm_receipt["sha256"],
                        v2_release_receipt_sha256=v2_release["sha256"],
                        elapsed_upper_millis=elapsed_upper_millis,
                        max_sec=derivation["max_sec"],
                    ),
                )
            except Exception:
                pass


P327_OBSERVER_RECEIPT_SCHEMA = "s22plus_fyg8_p327_framed_acm_receipt_v1"
P327_MAX_RAW_BYTES = 512 * 1024
P327_CLASSIFICATIONS = {
    "accepted",
    "endpoint-timeout",
    "endpoint-ambiguous",
    "identity-mismatch",
    "open-failed",
    "exclusive-failed",
    "guard-lost",
    "read-timeout",
    "extra-byte",
    "framed-session-error",
}


def _p327_identity(payload: bytes) -> dict[str, Any]:
    return {
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _p327_trailing_probe(
    descriptor: int,
    writer: raw_capture.RawCaptureWriter,
) -> bytes:
    """Capture one immediately readable trailing byte before rejecting.

    The probe is intentionally nonblocking and reads at most one byte.  That
    byte is forwarded to the inherited raw writer before the caller classifies
    the session, so a trailing protocol violation remains durable evidence.
    """
    readable, _, _ = select.select([descriptor], [], [], 0)
    if not readable:
        return b""
    try:
        trailing = os.read(descriptor, 1)
    except BlockingIOError:
        return b""
    if trailing:
        writer.write_stdout(trailing)
    return trailing


@dataclass
class _P327ObserverSession:
    """P327 framed session over the exact P324/P325 observer stack."""

    delegate: Any
    base: Any
    spec: dict[str, str]
    run_dir: Path
    lane_binding: dict[str, Any]
    lane_binding_receipt: dict[str, Any]
    usb_root: Path
    typec_root: Path
    exchange: Any | None = None
    proof: dict[str, Any] | None = None
    trailing_rx: bytes = b""
    endpoint: Any | None = None
    endpoint_classification: str | None = None
    protocol_error: str | None = None

    def _raw_argv0_name(self) -> str:
        return "tty-cdc-acm-p327"

    def _read_endpoint(
        self,
        endpoint: Any,
        deadline: float,
        writer: raw_capture.RawCaptureWriter,
    ) -> str:
        path = self.base.dev_root / endpoint.tty_name
        self.endpoint = endpoint
        if not self.base.guard.healthy(recheck=True):
            return "guard-lost"
        # P325's two-property repair is bound to the tty class node.  Keep the
        # exact node here rather than allowing the inherited USB interface
        # fallback used by the pre-P325 observer.
        if not self.base.guard.matches_node(endpoint.tty_class):
            return "identity-mismatch"
        try:
            info = path.stat()
            if (
                not stat.S_ISCHR(info.st_mode)
                or os.major(info.st_rdev) != endpoint.major
                or os.minor(info.st_rdev) != endpoint.minor
            ):
                return "identity-mismatch"
            descriptor = os.open(
                path,
                os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC,
            )
        except OSError:
            return "open-failed"
        try:
            try:
                fcntl.ioctl(descriptor, termios.TIOCEXCL)
            except OSError:
                return "exclusive-failed"
            if not self.base.guard.healthy(recheck=True):
                return "guard-lost"
            try:
                self.base._raw_tty(descriptor)
            except Exception as exc:  # pragma: no cover - tty fault
                self.protocol_error = type(exc).__name__
                return "open-failed"
            try:
                exchange = p327_framed_observer.exchange_commands(
                    descriptor,
                    p327_framed_observer.DEFAULT_COMMANDS,
                    timeout_sec=min(
                        120.0,
                        max(0.001, deadline - time.monotonic()),
                    ),
                    writer=writer,
                )
            except p327_framed_observer.FramedObserverError as exc:
                self.protocol_error = str(exc)[:160]
                return "framed-session-error"
            self.exchange = exchange
            # DONE is the terminal frame.  Probe immediately, with no quiet
            # wait or second read, and forward a detected byte before reject.
            self.trailing_rx = _p327_trailing_probe(descriptor, writer)
            if self.trailing_rx:
                exchange.audit.rx.extend(self.trailing_rx)
            try:
                self.proof = p327_framed_observer.validate_default_proof(
                    exchange
                )
            except p327_framed_observer.FramedObserverError as exc:
                self.protocol_error = str(exc)[:160]
                return (
                    "extra-byte"
                    if self.trailing_rx
                    else "framed-session-error"
                )
            if self.trailing_rx:
                return "extra-byte"
            guard_healthy = self.base.guard.healthy(recheck=True)
            guard_matches = (
                self.base.guard.matches_node(endpoint.tty_class)
                if guard_healthy
                else False
            )
            identity, repeated = cdc_acm_observer._resolve_endpoint(  # noqa: SLF001
                endpoint.tty_class
            )
            topology = cdc_acm_observer.TOPOLOGY_RE.fullmatch(
                p324_typec_lane.CANDIDATE_TOPOLOGY
            )
            assert topology is not None
            if (
                repeated.identity_sha256 != endpoint.identity_sha256
                or not cdc_acm_observer._matches(  # noqa: SLF001
                    self.spec, topology.group(1), identity, repeated
                )
                or os.fstat(descriptor).st_rdev != info.st_rdev
            ):
                return "identity-mismatch"
            if not guard_healthy:
                return "guard-lost"
            if not guard_matches:
                return "identity-mismatch"
            return "accepted"
        finally:
            os.close(descriptor)

    def _lane_supplement(self, accepted: bool) -> dict[str, Any]:
        """Retain the inherited P324 lane/partner end-state for P327."""
        p324_session = self.delegate.delegate
        partner_before = p324_session.partner_before
        partner_after = p324_cdc_observer._partner(self.typec_root)  # noqa: SLF001
        end_inventory = p324_cdc_observer._inventory(  # noqa: SLF001
            self.spec, p324_session.class_tty, self.usb_root
        )
        p324_cdc_observer._validate_inventory(end_inventory, label="P327 end")  # noqa: SLF001
        source_row = end_inventory["rows"][p324_typec_lane.SOURCE_TOPOLOGY]
        candidate_row = end_inventory["rows"][p324_typec_lane.CANDIDATE_TOPOLOGY]
        same_partner = (
            partner_after == partner_before
            and p324_session.partner_continuous
            and p324_session.partner_poll_count > 0
        )
        accepted_inventory = (
            accepted
            and source_row["exact_candidate_count"] == 0
            and candidate_row["exact_candidate_count"] == 1
            and candidate_row["candidate_like_count"] == 1
            and end_inventory["foreign_candidate_like_count"] == 0
        )
        current_lane = p324_typec_lane.revalidate_binding(
            self.lane_binding,
            source_topology=p324_typec_lane.SOURCE_TOPOLOGY,
            usb_root=self.usb_root,
            typec_root=self.typec_root,
        )
        return {
            "schema": p324_cdc_observer.SCHEMA,
            "contract_id": p324_cdc_observer.CONTRACT_ID,
            "target": p324_cdc_observer.TARGET,
            "lane_binding": self.lane_binding_receipt,
            "lane_binding_sha256": p324_cdc_observer._digest(current_lane),  # noqa: SLF001
            "arm": p324_session.arm_receipt,
            "source_topology": p324_typec_lane.SOURCE_TOPOLOGY,
            "candidate_topology": p324_typec_lane.CANDIDATE_TOPOLOGY,
            "selector_topology_count": 1,
            "partner_before": partner_before,
            "partner_after": partner_after,
            "partner_poll_count": p324_session.partner_poll_count,
            "partner_continuous": p324_session.partner_continuous,
            "end_inventory": end_inventory,
            "both_topologies_inventory_complete": True,
            "accepted_inventory_exact": accepted_inventory,
            "same_run_typec_partner_continuity": same_partner,
            "accepted_for_p324": accepted_inventory and same_partner,
            "opens_only_candidate_topology": True,
            "device_commands": False,
        }

    def _observe_value(
        self,
        *,
        timeout_sec: int,
        download_departure: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if (
            type(timeout_sec) is not int
            or timeout_sec <= 0
            or not isinstance(download_departure, dict)
            or set(download_departure)
            != {
                "download_endpoint_absent",
                "absence_timed_out",
                "sequence",
            }
            or type(download_departure["download_endpoint_absent"]) is not bool
            or type(download_departure["absence_timed_out"]) is not bool
            or type(download_departure["sequence"]) is not int
            or download_departure["sequence"] < 0
        ):
            raise p327_framed_observer.FramedObserverError(
                "P327 observer departure is invalid"
            )
        departure_receipt = cdc_acm_observer.persist_json(
            self.run_dir / "candidate-observer-download-departure.json",
            download_departure,
        )
        started = time.monotonic()
        deadline = started + timeout_sec
        classification = "endpoint-timeout"
        endpoint = None
        mismatch_seen = False
        if download_departure["download_endpoint_absent"] is True:
            while time.monotonic() < deadline:
                if not self.base.guard.healthy():
                    classification = "guard-lost"
                    break
                classification, endpoint = self.delegate._select()
                if classification == "identity-mismatch":
                    mismatch_seen = True
                if endpoint is not None or classification == "endpoint-ambiguous":
                    break
                time.sleep(0.05)
            if endpoint is None and classification == "endpoint-timeout" and mismatch_seen:
                classification = "identity-mismatch"
        writer = raw_capture.RawCaptureWriter(
            self.run_dir,
            "candidate-observer",
            stdout_maximum=P327_MAX_RAW_BYTES,
            stderr_maximum=1,
            argv0_name=self._raw_argv0_name(),
            stdout_name="candidate-observer.raw",
            stderr_name="candidate-observer.raw.stderr",
        )
        acquisition = classification
        try:
            if endpoint is not None:
                acquisition = self._read_endpoint(endpoint, deadline, writer)
            raw_handle = writer.finalize(returncode=0)
        except BaseException as exc:
            if not writer.finished:
                try:
                    writer.finalize(
                        returncode=None,
                        producer_error_type=type(exc).__name__,
                    )
                except (OSError, raw_capture.RawCaptureError):
                    pass
            raise
        raw_payload = raw_capture.read_stdout(raw_handle, maximum=P327_MAX_RAW_BYTES)
        endpoint_identity = (
            endpoint.identity_sha256 if endpoint is not None else None
        )
        accepted = acquisition == "accepted"
        # The P327 proof must remain false if the inherited lane itself lost
        # continuity, even if the wire exchange happened to be exact.
        lane_supplement = self._lane_supplement(accepted)
        accepted = accepted and lane_supplement["accepted_for_p324"] is True
        if acquisition == "accepted" and not accepted:
            acquisition = "identity-mismatch"
        proof = self.proof or {}
        exchange = self.exchange
        if exchange is None:
            tx = b""
            rx = b""
            banner_seen = ready_seen = done_seen = False
        else:
            tx = bytes(exchange.audit.tx)
            rx = bytes(exchange.audit.rx)
            banner_seen = exchange.audit.banner_seen
            ready_seen = exchange.audit.ready_seen
            done_seen = exchange.audit.done_seen
        p327_value = {
            "schema": P327_OBSERVER_RECEIPT_SCHEMA,
            "contract_id": p327_framed_observer.CONTRACT_ID,
            "target": p327_framed_observer.TARGET,
            "binding": dict(self.base.binding),
            "spec_sha256": cdc_acm_observer.digest(self.spec),
            "baseline_sha256": _receipt(
                self.run_dir / "candidate-observer-baseline.json",
                "P327 candidate observer baseline",
            )["sha256"],
            "download_departure_sha256": departure_receipt["sha256"],
            "download_endpoint_absent": download_departure[
                "download_endpoint_absent"
            ],
            "topology_sha256": hashlib.sha256(
                p324_typec_lane.CANDIDATE_TOPOLOGY.removeprefix("usb:").encode()
            ).hexdigest(),
            "endpoint_identity_sha256": endpoint_identity,
            "guard_sha256": _receipt(
                self.run_dir / "candidate-observer-guard.json",
                "P327 candidate observer guard",
            )["sha256"],
            "raw": {
                "path": str(raw_handle.stdout_path),
                "size": len(raw_payload),
                "sha256": hashlib.sha256(raw_payload).hexdigest(),
                "capture_receipt": {
                    "path": str(raw_handle.receipt_path),
                    "size": raw_handle.receipt_path.stat().st_size,
                    "sha256": hashlib.sha256(
                        raw_handle.receipt_path.read_bytes()
                    ).hexdigest(),
                },
            },
            "banner_hex": p327_framed_runtime.DEVICE_BANNER.hex(),
            "tx_hex": tx.hex(),
            "tx": _p327_identity(tx),
            "rx": _p327_identity(rx),
            "trailing_rx": _p327_identity(self.trailing_rx),
            "trailing_bytes_seen": len(self.trailing_rx),
            "banner_seen": banner_seen,
            "ready_seen": ready_seen,
            "done_seen": done_seen,
            "proof": proof,
            "pid1_framed_exec_proof": proof.get(
                "pid1_framed_exec_proof"
            ) is True and not self.trailing_rx,
            "busybox_ash_command_proof": proof.get(
                "busybox_ash_command_proof"
            ) is True and not self.trailing_rx,
            "framed_session_closed": (
                banner_seen and ready_seen and done_seen
            ),
            "interactive_pty_proof": False,
            "caller_selected_command": False,
            "command_count": len(p327_framed_observer.DEFAULT_COMMANDS),
            "lane": lane_supplement,
            "expected_size": len(p327_framed_runtime.DEVICE_BANNER),
            "exact": accepted,
            "extra_byte": bool(self.trailing_rx),
            "classification": acquisition,
            "accepted": accepted,
            "bounded": True,
            "elapsed_sec": round(time.monotonic() - started, 6),
        }
        return p327_value, lane_supplement

    def _publish_value(
        self,
        value: dict[str, Any],
        lane_supplement: dict[str, Any],
        *,
        label: str,
    ) -> None:
        cdc_acm_observer.persist_json(
            self.run_dir / "candidate-observer.json", value
        )
        # The P324 lane adapter normally emits this after its delegate's
        # observe call. Publish the same bounded lane supplement only after
        # the final raw-first framed receipt exists.
        lane_value = dict(lane_supplement)
        lane_value["base_observer"] = _receipt(
            self.run_dir / "candidate-observer.json",
            label,
        )
        cdc_acm_observer.persist_json(
            self.run_dir / p324_cdc_observer.SUPPLEMENT_NAME, lane_value
        )

    def observe(
        self,
        *,
        timeout_sec: int,
        download_departure: dict[str, Any],
    ) -> dict[str, Any]:
        p327_value, lane_supplement = self._observe_value(
            timeout_sec=timeout_sec,
            download_departure=download_departure,
        )
        self._publish_value(
            p327_value,
            lane_supplement,
            label="P327 framed observer receipt",
        )
        return p327_value

    def __getattr__(self, name: str) -> Any:
        return getattr(self.delegate, name)


@contextlib.contextmanager
def _p327_candidate_observer_session(
    prepared: PreparedRun,
    spec: dict[str, str],
    *,
    lane_value: dict[str, Any],
    lane_receipt: dict[str, Any],
    usb_root: Path,
    typec_root: Path,
) -> Iterator[_P327ObserverSession]:
    """Arm P324/P325 exactly once, then run the P327 framed exchange."""
    if spec.get("protocol_contract") != p327_framed_observer.CONTRACT_ID:
        raise F1LiveError("P3.27 framed observer contract differs")
    # The P327 manifest has a distinct protocol ``kind``.  The inherited
    # P324/P325 selector and guard intentionally consume the older banner
    # observer grammar, so only this private delegate copy is normalized.
    inherited_spec = _p327_inherited_spec(spec)
    with p325_guard_adapter.observer_session(
        inherited_spec,
        prepared.private_target["topology"],
        prepared.run_dir,
        _candidate_observer_binding(prepared),
        lane_value,
        lane_receipt,
        usb_root=usb_root,
        typec_root=typec_root,
    ) as inherited:
        base = inherited.delegate.delegate
        session = _P327ObserverSession(
            inherited,
            base,
            inherited_spec,
            prepared.run_dir,
            lane_value,
            lane_receipt,
            usb_root,
            typec_root,
        )
        yield session


def _p327_inherited_spec(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict) or not cdc_acm_observer.SPEC_KEYS <= set(spec):
        raise F1LiveError("P3.27 inherited observer projection is incomplete")
    value = {
        key: spec[key]
        for key in cdc_acm_observer.SPEC_KEYS
    }
    value["kind"] = cdc_acm_observer.KIND
    return value


def _p327_validate_receipt(
    prepared: PreparedRun,
    path: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    """Reopen one P327 raw-first framed receipt without a device call."""
    value = _read_json(path, "P327 framed observer receipt")
    expected_keys = {
        "schema",
        "contract_id",
        "target",
        "binding",
        "spec_sha256",
        "baseline_sha256",
        "download_departure_sha256",
        "download_endpoint_absent",
        "topology_sha256",
        "endpoint_identity_sha256",
        "guard_sha256",
        "raw",
        "banner_hex",
        "tx_hex",
        "tx",
        "rx",
        "trailing_rx",
        "trailing_bytes_seen",
        "banner_seen",
        "ready_seen",
        "done_seen",
        "proof",
        "pid1_framed_exec_proof",
        "busybox_ash_command_proof",
        "framed_session_closed",
        "interactive_pty_proof",
        "caller_selected_command",
        "command_count",
        "lane",
        "expected_size",
        "exact",
        "extra_byte",
        "classification",
        "accepted",
        "bounded",
        "elapsed_sec",
    }
    if set(value) != expected_keys:
        raise p327_framed_observer.FramedObserverError(
            "P327 framed observer receipt shape differs"
        )
    inherited_spec = _p327_inherited_spec(spec)
    topology = hashlib.sha256(
        p324_typec_lane.CANDIDATE_TOPOLOGY.removeprefix("usb:").encode()
    ).hexdigest()
    baseline = _receipt(
        prepared.run_dir / "candidate-observer-baseline.json",
        "P327 candidate observer baseline",
    )
    departure = _receipt(
        prepared.run_dir / "candidate-observer-download-departure.json",
        "P327 candidate observer departure",
    )
    guard = _receipt(
        prepared.run_dir / "candidate-observer-guard.json",
        "P327 candidate observer guard",
    )
    if (
        value["schema"] != P327_OBSERVER_RECEIPT_SCHEMA
        or value["contract_id"] != p327_framed_observer.CONTRACT_ID
        or value["target"] != p327_framed_observer.TARGET
        or value["binding"] != _candidate_observer_binding(prepared)
        or value["spec_sha256"] != cdc_acm_observer.digest(inherited_spec)
        or value["baseline_sha256"] != baseline["sha256"]
        or value["download_departure_sha256"] != departure["sha256"]
        or value["guard_sha256"] != guard["sha256"]
        or type(value["download_endpoint_absent"]) is not bool
        or value["topology_sha256"] != topology
        or value["expected_size"] != len(p327_framed_runtime.DEVICE_BANNER)
        or value["interactive_pty_proof"] is not False
        or value["caller_selected_command"] is not False
        or value["command_count"] != p327_framed_runtime.MAX_COMMANDS
        or value["bounded"] is not True
        or not isinstance(value["classification"], str)
        or value["classification"] not in P327_CLASSIFICATIONS
        or value["exact"] is not (value["accepted"] is True)
        or value["extra_byte"] is not (value["trailing_bytes_seen"] > 0)
        or value["accepted"] is not (value["classification"] == "accepted")
        or (
            value["accepted"] is True
            and value["download_endpoint_absent"] is not True
        )
        or type(value["trailing_bytes_seen"]) is not int
        or value["trailing_bytes_seen"] not in {0, 1}
        or type(value["banner_seen"]) is not bool
        or type(value["ready_seen"]) is not bool
        or type(value["done_seen"]) is not bool
        or value["framed_session_closed"] is not (
            value["banner_seen"]
            and value["ready_seen"]
            and value["done_seen"]
        )
        or value["framed_session_closed"] is not True
        or isinstance(value["elapsed_sec"], bool)
        or not isinstance(value["elapsed_sec"], (int, float))
        or not math.isfinite(float(value["elapsed_sec"]))
        or not 0 <= value["elapsed_sec"] <= 600
    ):
        raise p327_framed_observer.FramedObserverError(
            "P327 framed observer receipt semantics differ"
        )
    endpoint_identity = value["endpoint_identity_sha256"]
    if endpoint_identity is not None and (
        not isinstance(endpoint_identity, str)
        or re.fullmatch(r"[0-9a-f]{64}", endpoint_identity) is None
    ):
        raise p327_framed_observer.FramedObserverError(
            "P327 endpoint identity differs"
        )
    raw = value["raw"]
    if not isinstance(raw, dict) or set(raw) != {
        "path",
        "size",
        "sha256",
        "capture_receipt",
    }:
        raise p327_framed_observer.FramedObserverError(
            "P327 raw receipt shape differs"
        )
    raw_path = Path(raw["path"])
    capture_receipt = raw["capture_receipt"]
    expected_raw_path = prepared.run_dir / "candidate-observer.raw"
    expected_capture_path = prepared.run_dir / "candidate-observer.capture.json"
    if (
        raw_path != expected_raw_path
        or type(raw["size"]) is not int
        or raw["size"] < 0
        or raw["size"] > P327_MAX_RAW_BYTES
        or not isinstance(raw["sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", raw["sha256"]) is None
        or not isinstance(capture_receipt, dict)
        or set(capture_receipt) != {"path", "size", "sha256"}
        or type(capture_receipt["size"]) is not int
        or not isinstance(capture_receipt["sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", capture_receipt["sha256"]) is None
        or Path(capture_receipt["path"]) != expected_capture_path
    ):
        raise p327_framed_observer.FramedObserverError(
            "P327 raw receipt binding differs"
        )
    try:
        raw_payload = raw_path.read_bytes()
        capture_payload = expected_capture_path.read_bytes()
        handle = raw_capture.load_handle(expected_capture_path)
    except (OSError, raw_capture.RawCaptureError) as exc:
        raise p327_framed_observer.FramedObserverError(
            "P327 raw evidence cannot be reopened"
        ) from exc
    if (
        len(raw_payload) != raw["size"]
        or hashlib.sha256(raw_payload).hexdigest() != raw["sha256"]
        or len(capture_payload) != capture_receipt["size"]
        or hashlib.sha256(capture_payload).hexdigest()
        != capture_receipt["sha256"]
        or handle.stdout_path != expected_raw_path
        or handle.stderr_path != prepared.run_dir / "candidate-observer.raw.stderr"
        or handle.returncode != 0
        or handle.timed_out
        or handle.output_exceeded
        or handle.producer_error_type is not None
        or raw_capture.read_stdout(handle, maximum=P327_MAX_RAW_BYTES)
        != raw_payload
        or raw_capture.read_stderr(handle, maximum=1) != b""
    ):
        raise p327_framed_observer.FramedObserverError(
            "P327 raw evidence changed"
        )
    try:
        tx = bytes.fromhex(value["tx_hex"])
    except (TypeError, ValueError) as exc:
        raise p327_framed_observer.FramedObserverError(
            "P327 tx encoding differs"
        ) from exc
    trailing = value["trailing_rx"]
    if not isinstance(trailing, dict) or set(trailing) != {"size", "sha256"}:
        raise p327_framed_observer.FramedObserverError(
            "P327 trailing receipt shape differs"
        )
    if (
        value["tx"] != _p327_identity(tx)
        or type(trailing["size"]) is not int
        or not isinstance(trailing["sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", trailing["sha256"]) is None
        or trailing["size"] != value["trailing_bytes_seen"]
        or trailing["size"] not in {0, 1}
        or trailing["sha256"]
        != hashlib.sha256(raw_payload[-trailing["size"] :] if trailing["size"] else b"").hexdigest()
    ):
        raise p327_framed_observer.FramedObserverError(
            "P327 tx/trailing accounting differs"
        )
    rx = value["rx"]
    if not isinstance(rx, dict) or set(rx) != {"size", "sha256"}:
        raise p327_framed_observer.FramedObserverError(
            "P327 rx receipt shape differs"
        )
    rx_payload = raw_payload
    # TX bytes are not part of the device-to-host raw stream.  The exchange
    # audit includes the banner and frames; the receipt binds that identity
    # directly and only admits a one-byte trailing suffix.
    if (
        type(rx["size"]) is not int
        or not isinstance(rx["sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", rx["sha256"]) is None
        or rx["size"] != len(rx_payload)
        or rx["sha256"] != hashlib.sha256(rx_payload).hexdigest()
    ):
        raise p327_framed_observer.FramedObserverError(
            "P327 rx accounting differs"
        )
    proof = value["proof"]
    if not isinstance(proof, dict) or proof.get("command_count") != 3:
        raise p327_framed_observer.FramedObserverError(
            "P327 proof receipt is incomplete"
        )
    proof_flags = {
        "pid1_framed_exec_proof": value["pid1_framed_exec_proof"],
        "busybox_ash_command_proof": value["busybox_ash_command_proof"],
        "framed_session_closed": value["framed_session_closed"],
    }
    if any(type(item) is not bool for item in proof_flags.values()):
        raise p327_framed_observer.FramedObserverError(
            "P327 proof flags are malformed"
        )
    if value["accepted"] is True and not all(proof_flags.values()):
        raise p327_framed_observer.FramedObserverError(
            "P327 accepted receipt lacks framed proof"
        )
    lane = value["lane"]
    if not isinstance(lane, dict):
        raise p327_framed_observer.FramedObserverError(
            "P327 lane receipt is absent"
        )
    if (
        lane.get("source_topology") != p324_typec_lane.SOURCE_TOPOLOGY
        or lane.get("candidate_topology")
        != p324_typec_lane.CANDIDATE_TOPOLOGY
        or lane.get("selector_topology_count") != 1
        or lane.get("opens_only_candidate_topology") is not True
        or lane.get("device_commands") is not False
    ):
        raise p327_framed_observer.FramedObserverError(
            "P327 lane topology receipt differs"
        )
    end_inventory = lane.get("end_inventory")
    try:
        p324_cdc_observer._validate_inventory(end_inventory, label="P327 reopen")  # noqa: SLF001
    except (p324_cdc_observer.P324ObserverError, TypeError, AttributeError) as exc:
        raise p327_framed_observer.FramedObserverError(
            "P327 lane inventory is incomplete"
        ) from exc
    assert isinstance(end_inventory, dict)
    source_row = end_inventory["rows"][p324_typec_lane.SOURCE_TOPOLOGY]
    candidate_row = end_inventory["rows"][p324_typec_lane.CANDIDATE_TOPOLOGY]
    source_topology_sha256 = hashlib.sha256(
        p324_typec_lane.SOURCE_TOPOLOGY.removeprefix("usb:").encode()
    ).hexdigest()
    candidate_topology_sha256 = hashlib.sha256(
        p324_typec_lane.CANDIDATE_TOPOLOGY.removeprefix("usb:").encode()
    ).hexdigest()
    if (
        source_row["topology_sha256"] != source_topology_sha256
        or candidate_row["topology_sha256"] != candidate_topology_sha256
    ):
        raise p327_framed_observer.FramedObserverError(
            "P327 lane topology digest differs"
        )
    lane_flags = (
        "both_topologies_inventory_complete",
        "accepted_inventory_exact",
        "same_run_typec_partner_continuity",
        "accepted_for_p324",
    )
    if any(type(lane.get(key)) is not bool for key in lane_flags):
        raise p327_framed_observer.FramedObserverError(
            "P327 lane flags are malformed"
        )
    if lane["accepted_for_p324"] is not (
        lane["accepted_inventory_exact"]
        and lane["same_run_typec_partner_continuity"]
    ):
        raise p327_framed_observer.FramedObserverError(
            "P327 lane acceptance is inconsistent"
        )
    return {
        "classification": value["classification"],
        "accepted": value["accepted"],
        "receipt_sha256": _receipt(path, "P327 framed observer receipt")["sha256"],
        "valid_receipt": True,
        "download_endpoint_absent": value["download_endpoint_absent"],
        "endpoint_identity_sha256": endpoint_identity,
        "topology_sha256": value["topology_sha256"],
        "bounded": value["bounded"],
        "source_topology_sha256": source_topology_sha256,
        "candidate_topology_sha256": candidate_topology_sha256,
        "both_topologies_inventory_complete": lane[
            "both_topologies_inventory_complete"
        ],
        "accepted_inventory_exact": lane["accepted_inventory_exact"],
        "same_run_typec_partner_continuity": lane[
            "same_run_typec_partner_continuity"
        ],
        "accepted_for_p324": lane["accepted_for_p324"],
        "pid1_framed_exec_proof": value["pid1_framed_exec_proof"],
        "busybox_ash_command_proof": value["busybox_ash_command_proof"],
        "framed_session_closed": value["framed_session_closed"],
        "interactive_pty_proof": value["interactive_pty_proof"],
        "caller_selected_command": value["caller_selected_command"],
        "p327_framed_exec": proof,
    }


@dataclass
class _P328ObserverSession(_P327ObserverSession):
    """P328 authentication wrapper retaining the reviewed P327 lane writer."""

    auth_key: bytes = b""
    auth_key_sha256: str = ""
    auth_observer: Any = p328_auth_observer
    auth_runtime: Any = p328_auth_runtime
    receipt_schema: str = P328_OBSERVER_RECEIPT_SCHEMA
    receipt_label: str = "P328 authenticated observer receipt"

    def _raw_argv0_name(self) -> str:
        return "tty-cdc-acm-p328"

    def _receipt_additions(self, audit: Any | None) -> dict[str, Any]:
        """Return candidate-specific receipt fields; P328/P329 add none."""
        return {}

    def _read_endpoint(
        self,
        endpoint: Any,
        deadline: float,
        writer: raw_capture.RawCaptureWriter,
    ) -> str:
        path = self.base.dev_root / endpoint.tty_name
        self.endpoint = endpoint
        guard_healthy = self.base.guard.healthy(recheck=True)
        if not guard_healthy or not self.base.guard.matches_node(endpoint.tty_class):
            return "guard-lost" if not guard_healthy else "identity-mismatch"
        try:
            info = path.stat()
            if (
                not stat.S_ISCHR(info.st_mode)
                or os.major(info.st_rdev) != endpoint.major
                or os.minor(info.st_rdev) != endpoint.minor
            ):
                return "identity-mismatch"
            descriptor = os.open(
                path,
                os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC,
            )
        except OSError:
            return "open-failed"
        try:
            try:
                fcntl.ioctl(descriptor, termios.TIOCEXCL)
            except OSError:
                return "exclusive-failed"
            if not self.base.guard.healthy(recheck=True):
                return "guard-lost"
            try:
                self.base._raw_tty(descriptor)
                exchange = self.auth_observer.exchange_commands(
                    descriptor,
                    self.auth_key,
                    self.auth_observer.DEFAULT_COMMANDS,
                    timeout_sec=min(120.0, max(0.001, deadline - time.monotonic())),
                    writer=writer,
                )
            except (
                p328_auth_observer.AuthObserverError,
                p329_auth_observer.AuthObserverError,
                p330_auth_observer.AuthObserverError,
            ) as exc:
                partial = getattr(exc, "audit", None)
                if isinstance(partial, p330_auth_observer.ExchangeAudit):
                    self.exchange = p330_auth_observer.SessionResult((), partial)
                self.protocol_error = str(exc)[:160]
                return "authenticated-session-error"
            except Exception as exc:  # pragma: no cover - tty fault
                self.protocol_error = type(exc).__name__
                return "open-failed"
            self.exchange = exchange
            self.trailing_rx = _p327_trailing_probe(descriptor, writer)
            if self.trailing_rx:
                exchange.audit.rx.extend(self.trailing_rx)
            try:
                proof = self.auth_observer.validate_default_proof(exchange)
            except (
                p328_auth_observer.AuthObserverError,
                p329_auth_observer.AuthObserverError,
                p330_auth_observer.AuthObserverError,
            ) as exc:
                self.protocol_error = str(exc)[:160]
                return "extra-byte" if self.trailing_rx else "authenticated-session-error"
            self.proof = {
                **proof,
                "pid1_framed_exec_proof": proof[
                    "pid1_authenticated_framed_exec_proof"
                ],
            }
            if self.trailing_rx:
                return "extra-byte"
            guard_healthy = self.base.guard.healthy(recheck=True)
            identity, repeated = cdc_acm_observer._resolve_endpoint(  # noqa: SLF001
                endpoint.tty_class
            )
            topology = cdc_acm_observer.TOPOLOGY_RE.fullmatch(
                p324_typec_lane.CANDIDATE_TOPOLOGY
            )
            assert topology is not None
            if (
                repeated.identity_sha256 != endpoint.identity_sha256
                or not cdc_acm_observer._matches(  # noqa: SLF001
                    self.spec, topology.group(1), identity, repeated
                )
                or os.fstat(descriptor).st_rdev != info.st_rdev
            ):
                return "identity-mismatch"
            if not guard_healthy or not self.base.guard.matches_node(endpoint.tty_class):
                return "guard-lost" if not guard_healthy else "identity-mismatch"
            return "accepted"
        finally:
            os.close(descriptor)

    def observe(
        self,
        *,
        timeout_sec: int,
        download_departure: dict[str, Any],
    ) -> dict[str, Any]:
        # P327 contributes only the reviewed raw-first writer, trailing probe,
        # and lane receipt.  P328 rewrites its in-memory projection before
        # the final receipt is published.
        base_value, lane_supplement = super()._observe_value(
            timeout_sec=timeout_sec,
            download_departure=download_departure,
        )
        value = dict(base_value)
        value.pop("tx_hex", None)
        value.pop("pid1_framed_exec_proof", None)
        exchange = self.exchange
        audit = exchange.audit if exchange is not None else None
        proof = dict(self.proof or {})
        proof.pop("pid1_framed_exec_proof", None)
        hmac_authenticated = audit is not None and audit.authenticated is True
        challenge_seen = audit is not None and audit.challenge_seen is True
        framed_closed = bool(
            audit is not None
            and audit.banner_seen
            and audit.challenge_seen
            and audit.ready_seen
            and audit.done_seen
        )
        accepted = bool(
            base_value.get("accepted") is True
            and hmac_authenticated
            and proof.get("pid1_authenticated_framed_exec_proof") is True
            and proof.get("busybox_ash_command_proof") is True
            and framed_closed
            and not self.trailing_rx
        )
        classification = base_value["classification"]
        if classification == "accepted" and not accepted:
            classification = "authenticated-session-error"
        value.update(
            {
                "schema": self.receipt_schema,
                "contract_id": self.auth_observer.CONTRACT_ID,
                "target": self.auth_observer.TARGET,
                "banner_hex": self.auth_runtime.DEVICE_BANNER.hex(),
                "challenge_seen": challenge_seen,
                "proof": proof,
                "auth_algorithm": "hmac-sha256",
                "auth_tag_size": self.auth_runtime.AUTH_TAG_SIZE,
                "nonce_size": self.auth_runtime.NONCE_SIZE,
                "auth_key_sha256": self.auth_key_sha256,
                "challenge_nonce_sha256": proof.get("challenge_nonce_sha256"),
                "hmac_authenticated": hmac_authenticated,
                "pid1_authenticated_framed_exec_proof": proof.get(
                    "pid1_authenticated_framed_exec_proof"
                )
                is True
                and not self.trailing_rx,
                "busybox_ash_command_proof": proof.get(
                    "busybox_ash_command_proof"
                )
                is True
                and not self.trailing_rx,
                "framed_session_closed": framed_closed,
                "interactive_pty_proof": False,
                "caller_selected_command": True,
                "command_count": len(self.auth_observer.DEFAULT_COMMANDS),
                "max_commands": self.auth_runtime.MAX_COMMANDS,
                "exact": accepted,
                "classification": classification,
                "accepted": accepted,
            }
        )
        value.update(self._receipt_additions(audit))
        self._publish_value(
            value,
            lane_supplement,
            label=self.receipt_label,
        )
        return value


@dataclass
class _P329ObserverSession(_P328ObserverSession):
    """Wait briefly for exact tty udev properties, then run P3.28 protocol."""

    auth_observer: Any = p329_auth_observer
    auth_runtime: Any = p329_auth_runtime
    receipt_schema: str = P329_OBSERVER_RECEIPT_SCHEMA
    receipt_label: str = "P329 authenticated observer receipt"

    def _raw_argv0_name(self) -> str:
        return "tty-cdc-acm-p329"

    def _settle_guard_properties(self, endpoint: Any, deadline: float) -> str | None:
        settle_deadline = min(deadline, time.monotonic() + P329_UDEV_SETTLE_SEC)
        topology = cdc_acm_observer.TOPOLOGY_RE.fullmatch(
            p324_typec_lane.CANDIDATE_TOPOLOGY
        )
        assert topology is not None
        path = self.base.dev_root / endpoint.tty_name
        while True:
            if not self.base.guard.healthy(recheck=True):
                return "guard-lost"
            if self.base.guard.matches_node(endpoint.tty_class):
                return None
            try:
                identity, repeated = cdc_acm_observer._resolve_endpoint(  # noqa: SLF001
                    endpoint.tty_class
                )
                info = path.stat()
            except (OSError, cdc_acm_observer.ObserverError):
                return "identity-mismatch"
            if (
                repeated.identity_sha256 != endpoint.identity_sha256
                or not cdc_acm_observer._matches(  # noqa: SLF001
                    self.spec, topology.group(1), identity, repeated
                )
                or not stat.S_ISCHR(info.st_mode)
                or os.major(info.st_rdev) != endpoint.major
                or os.minor(info.st_rdev) != endpoint.minor
            ):
                return "identity-mismatch"
            remaining = settle_deadline - time.monotonic()
            if remaining <= 0:
                return "guard-property-timeout"
            time.sleep(min(P329_UDEV_SETTLE_POLL_SEC, remaining))

    def _read_endpoint(
        self,
        endpoint: Any,
        deadline: float,
        writer: raw_capture.RawCaptureWriter,
    ) -> str:
        self.endpoint = endpoint
        stopped = self._settle_guard_properties(endpoint, deadline)
        if stopped is not None:
            return stopped
        return super()._read_endpoint(endpoint, deadline, writer)


@dataclass
class _P330ObserverSession(_P329ObserverSession):
    """P329 exact-endpoint settle plus P330 pre-auth diagnostics."""

    auth_observer: Any = p330_auth_observer
    auth_runtime: Any = p330_auth_runtime
    receipt_schema: str = P330_OBSERVER_RECEIPT_SCHEMA
    receipt_label: str = "P330 diagnostic authenticated observer receipt"

    def _raw_argv0_name(self) -> str:
        return "tty-cdc-acm-p330"

    def _receipt_additions(self, audit: Any | None) -> dict[str, Any]:
        diagnostics = []
        current_stage = failure_stage = exception_type = exception_sha256 = None
        failure_code = rng_eagain_retries = None
        if isinstance(audit, p330_auth_observer.ExchangeAudit):
            diagnostics = [
                {"stage": item.stage, "code": item.code}
                for item in audit.diagnostics
            ]
            current_stage = audit.current_stage
            failure_stage = audit.failure_stage
            failure_code = audit.failure_code
            exception_type = audit.exception_type
            exception_sha256 = audit.exception_sha256
            rng_eagain_retries = audit.rng_eagain_retries
        return {
            "diagnostics": diagnostics,
            "rng_eagain_retries": rng_eagain_retries,
            "partial_exchange": {
                "current_stage": current_stage,
                "failure_stage": failure_stage,
                "failure_code": failure_code,
                "exception_type": exception_type,
                "exception_sha256": exception_sha256,
            },
        }


@dataclass
class _P331ObserverSession(_P330ObserverSession):
    """Two exact P330-authenticated heartbeat sessions over one tty identity."""

    auth_observer: Any = p331_resident_observer
    auth_runtime: Any = p331_resident_runtime
    receipt_schema: str = P331_OBSERVER_RECEIPT_SCHEMA
    receipt_label: str = "P331 bounded resident observer receipt"
    resident_result: Any | None = None
    session_trailing_rx: tuple[bytes, ...] = ()

    def _raw_argv0_name(self) -> str:
        return "tty-cdc-acm-p331"

    def _endpoint_exact(self, endpoint: Any, descriptor: int | None = None) -> bool:
        path = self.base.dev_root / endpoint.tty_name
        try:
            identity, repeated = cdc_acm_observer._resolve_endpoint(  # noqa: SLF001
                endpoint.tty_class
            )
            info = path.stat()
        except (OSError, cdc_acm_observer.ObserverError):
            return False
        topology = cdc_acm_observer.TOPOLOGY_RE.fullmatch(
            p324_typec_lane.CANDIDATE_TOPOLOGY
        )
        if topology is None:
            return False
        return bool(
            self.base.guard.healthy(recheck=True)
            and self.base.guard.matches_node(endpoint.tty_class)
            and repeated.identity_sha256 == endpoint.identity_sha256
            and cdc_acm_observer._matches(  # noqa: SLF001
                self.spec, topology.group(1), identity, repeated
            )
            and stat.S_ISCHR(info.st_mode)
            and os.major(info.st_rdev) == endpoint.major
            and os.minor(info.st_rdev) == endpoint.minor
            and (
                descriptor is None
                or os.fstat(descriptor).st_rdev == info.st_rdev
            )
        )

    def _failed_resident_result(
        self,
        records: list[Any],
        index: int,
        terminal: str,
        error_type: str,
        error_message: str,
        audit: Any | None = None,
    ) -> Any:
        records.append(
            p331_resident_observer.ResidentSession(
                index,
                index,
                None,
                audit,
                bytes(audit.tx) if audit is not None else b"",
                bytes(audit.rx) if audit is not None else b"",
                error_type,
                error_message[:160],
            )
        )
        return p331_resident_observer.ResidentResult(
            tuple(records),
            p331_resident_runtime.MAX_SESSIONS,
            p331_resident_runtime.MAX_RECONNECTS,
            min(index, p331_resident_runtime.MAX_RECONNECTS),
            terminal,
        )

    def _read_endpoint(
        self,
        endpoint: Any,
        deadline: float,
        writer: raw_capture.RawCaptureWriter,
    ) -> str:
        self.endpoint = endpoint
        path = self.base.dev_root / endpoint.tty_name
        records: list[Any] = []
        trailing_records: list[bytes] = []
        seen_nonces: set[bytes] = set()
        for index in range(p331_resident_runtime.MAX_SESSIONS):
            stopped = self._settle_guard_properties(endpoint, deadline)
            if stopped is not None:
                self.resident_result = self._failed_resident_result(
                    records, index, "reconnect-failed", stopped, stopped
                )
                return stopped
            if not self._endpoint_exact(endpoint):
                self.resident_result = self._failed_resident_result(
                    records,
                    index,
                    "reconnect-failed",
                    "identity-mismatch",
                    "exact endpoint changed before resident open",
                )
                return "identity-mismatch"
            try:
                descriptor = os.open(
                    path,
                    os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC,
                )
            except OSError as exc:
                self.resident_result = self._failed_resident_result(
                    records, index, "reconnect-failed", type(exc).__name__, str(exc)
                )
                return "open-failed"
            try:
                try:
                    fcntl.ioctl(descriptor, termios.TIOCEXCL)
                except OSError as exc:
                    self.resident_result = self._failed_resident_result(
                        records,
                        index,
                        "reconnect-failed",
                        type(exc).__name__,
                        str(exc),
                    )
                    return "exclusive-failed"
                if not self._endpoint_exact(endpoint, descriptor):
                    self.resident_result = self._failed_resident_result(
                        records,
                        index,
                        "reconnect-failed",
                        "identity-mismatch",
                        "exact endpoint changed after resident open",
                    )
                    return "identity-mismatch"
                self.base._raw_tty(descriptor)
                try:
                    session = p331_resident_observer.exchange_session(
                        descriptor,
                        self.auth_key,
                        timeout_sec=min(
                            p331_resident_runtime.RESIDENT_SESSION_TIMEOUT_SEC,
                            max(0.001, deadline - time.monotonic()),
                        ),
                        writer=writer,
                        seen_nonces=seen_nonces,
                    )
                except p331_resident_observer.AuthObserverError as exc:
                    audit = getattr(exc, "audit", None)
                    self.resident_result = self._failed_resident_result(
                        records,
                        index,
                        "session-failed",
                        type(exc).__name__,
                        str(exc),
                        audit,
                    )
                    self.protocol_error = str(exc)[:160]
                    return "authenticated-session-error"
                trailing = (
                    _p327_trailing_probe(descriptor, writer)
                    if index + 1 == p331_resident_runtime.MAX_SESSIONS
                    else b""
                )
                if trailing:
                    session.audit.rx.extend(trailing)
                trailing_records.append(trailing)
                record = p331_resident_observer.ResidentSession(
                    index,
                    index,
                    session if not trailing else None,
                    session.audit,
                    bytes(session.audit.tx),
                    bytes(session.audit.rx),
                    "extra-byte" if trailing else None,
                    "trailing byte after DONE" if trailing else None,
                )
                records.append(record)
                if trailing:
                    self.resident_result = p331_resident_observer.ResidentResult(
                        tuple(records),
                        p331_resident_runtime.MAX_SESSIONS,
                        p331_resident_runtime.MAX_RECONNECTS,
                        min(index, p331_resident_runtime.MAX_RECONNECTS),
                        "session-failed",
                    )
                    self.session_trailing_rx = tuple(trailing_records)
                    self.trailing_rx = b"".join(trailing_records)
                    return "extra-byte"
                if not self._endpoint_exact(endpoint, descriptor):
                    self.resident_result = p331_resident_observer.ResidentResult(
                        tuple(records),
                        p331_resident_runtime.MAX_SESSIONS,
                        p331_resident_runtime.MAX_RECONNECTS,
                        min(index, p331_resident_runtime.MAX_RECONNECTS),
                        "session-failed",
                    )
                    return "identity-mismatch"
                self.exchange = session
            except Exception as exc:  # pragma: no cover - tty fault
                if self.resident_result is None:
                    self.resident_result = self._failed_resident_result(
                        records,
                        index,
                        "session-failed",
                        type(exc).__name__,
                        str(exc),
                    )
                self.protocol_error = type(exc).__name__
                return "open-failed"
            finally:
                os.close(descriptor)

        result = p331_resident_observer.ResidentResult(
            tuple(records),
            p331_resident_runtime.MAX_SESSIONS,
            p331_resident_runtime.MAX_RECONNECTS,
            p331_resident_runtime.MAX_RECONNECTS,
            "session-cap",
        )
        try:
            proof = p331_resident_observer.validate_resident_proof(result)
        except p331_resident_observer.ResidentObserverError as exc:
            self.resident_result = result
            self.protocol_error = str(exc)[:160]
            return "authenticated-session-error"
        self.resident_result = result
        self.proof = proof
        self.session_trailing_rx = tuple(trailing_records)
        self.trailing_rx = b"".join(trailing_records)
        return "accepted"

    def observe(
        self,
        *,
        timeout_sec: int,
        download_departure: dict[str, Any],
    ) -> dict[str, Any]:
        base_value, lane_supplement = super()._observe_value(
            timeout_sec=timeout_sec,
            download_departure=download_departure,
        )
        resident = self.resident_result
        proof = dict(self.proof or {})
        sessions = () if resident is None else resident.sessions
        tx = b"".join(item.raw_tx for item in sessions)
        rx = b"".join(item.raw_rx for item in sessions)
        diagnostics = [
            [
                {"stage": item.stage, "code": item.code}
                for item in session.audit.diagnostics
            ]
            if session.audit is not None
            else []
            for session in sessions
        ]
        retries = [
            session.audit.rng_eagain_retries
            if session.audit is not None
            else None
            for session in sessions
        ]
        partial = [
            {
                "session_index": session.index,
                "current_stage": (
                    session.audit.current_stage if session.audit is not None else None
                ),
                "failure_stage": (
                    session.audit.failure_stage if session.audit is not None else None
                ),
                "failure_code": (
                    session.audit.failure_code if session.audit is not None else None
                ),
                "exception_type": (
                    session.audit.exception_type if session.audit is not None else session.error_type
                ),
                "exception_sha256": (
                    session.audit.exception_sha256 if session.audit is not None else None
                ),
            }
            for session in sessions
        ]
        resident_complete = bool(
            resident is not None
            and resident.complete
            and proof.get("resident_loop_proof") is True
            and proof.get("fixed_heartbeat_status") is True
            and proof.get("session_count") == p331_resident_runtime.MAX_SESSIONS
            and proof.get("reconnect_count") == p331_resident_runtime.MAX_RECONNECTS
            and not self.trailing_rx
        )
        accepted = bool(base_value.get("accepted") is True and resident_complete)
        classification = base_value["classification"]
        if classification == "accepted" and not accepted:
            classification = "authenticated-session-error"
        value = dict(base_value)
        value.pop("tx_hex", None)
        value.pop("pid1_framed_exec_proof", None)
        value.update(
            {
                "schema": self.receipt_schema,
                "contract_id": self.auth_observer.CONTRACT_ID,
                "target": self.auth_observer.runtime.TARGET,
                "banner_hex": self.auth_runtime.DEVICE_BANNER.hex(),
                "tx": _p327_identity(tx),
                "session_tx_hex": [item.raw_tx.hex() for item in sessions],
                "rx": _p327_identity(rx),
                "trailing_rx": _p327_identity(self.trailing_rx),
                "trailing_bytes_seen": len(self.trailing_rx),
                "diagnostics": diagnostics,
                "rng_eagain_retries": retries,
                "partial_sessions": partial,
                "proof": proof,
                "auth_algorithm": "hmac-sha256",
                "auth_tag_size": self.auth_runtime.AUTH_TAG_SIZE,
                "auth_key_sha256": self.auth_key_sha256,
                "hmac_authenticated": resident_complete,
                "pid1_authenticated_framed_exec_proof": resident_complete,
                "busybox_ash_command_proof": resident_complete,
                "framed_session_closed": resident_complete,
                "resident_loop_proof": resident_complete,
                "fixed_heartbeat_status": resident_complete,
                "session_count": len(sessions),
                "successful_sessions": (
                    0 if resident is None else resident.successful_sessions
                ),
                "session_cap": p331_resident_runtime.MAX_SESSIONS,
                "reconnect_count": (
                    0 if resident is None else resident.reconnect_count
                ),
                "reconnect_cap": p331_resident_runtime.MAX_RECONNECTS,
                "commands_per_session": 1,
                "command_count": len(sessions),
                "max_commands": self.auth_runtime.MAX_COMMANDS,
                "interactive_pty_proof": False,
                "caller_selected_command": False,
                "arbitrary_file_transfer": False,
                "persistent_state": False,
                "expected_size": (
                    len(self.auth_runtime.DEVICE_BANNER)
                    * p331_resident_runtime.MAX_SESSIONS
                ),
                "exact": accepted,
                "extra_byte": bool(self.trailing_rx),
                "classification": classification,
                "accepted": accepted,
            }
        )
        self._publish_value(
            value,
            lane_supplement,
            label=self.receipt_label,
        )
        return value


@dataclass
class _P332ObserverSession(_P331ObserverSession):
    """Run two P330 exchanges on one already-open exact tty descriptor."""

    auth_observer: Any = p332_logical_resident_observer
    auth_runtime: Any = p332_logical_resident_runtime
    receipt_schema: str = P332_OBSERVER_RECEIPT_SCHEMA
    receipt_label: str = "P332 same-fd logical resident observer receipt"
    campaign_label: str = "P3.32"
    proof_key: str = "p332_authenticated_logical_resident"
    raw_argv0_name: str = "tty-cdc-acm-p332"

    def _raw_argv0_name(self) -> str:
        return self.raw_argv0_name

    def _read_endpoint(
        self,
        endpoint: Any,
        deadline: float,
        writer: raw_capture.RawCaptureWriter,
    ) -> str:
        self.endpoint = endpoint
        stopped = self._settle_guard_properties(endpoint, deadline)
        if stopped is not None:
            return stopped
        if not self._endpoint_exact(endpoint):
            return "identity-mismatch"
        path = self.base.dev_root / endpoint.tty_name
        try:
            descriptor = os.open(
                path,
                os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC,
            )
        except OSError:
            return "open-failed"
        try:
            try:
                fcntl.ioctl(descriptor, termios.TIOCEXCL)
            except OSError:
                return "exclusive-failed"
            if not self._endpoint_exact(endpoint, descriptor):
                return "identity-mismatch"
            self.base._raw_tty(descriptor)
            try:
                resident = self.auth_observer.exchange_resident(
                    descriptor,
                    self.auth_key,
                    timeout_sec=min(
                        self.auth_observer.SESSION_TIMEOUT_SEC,
                        max(0.001, deadline - time.monotonic()),
                    ),
                    writer=writer,
                )
            except self.auth_observer.LogicalResidentObserverError as exc:
                self.resident_result = exc.result
                self.protocol_error = str(exc)[:160]
                return "authenticated-session-error"
            self.resident_result = resident
            self.exchange = resident.sessions[-1].result
            self.trailing_rx = _p327_trailing_probe(descriptor, writer)
            if self.trailing_rx:
                return "extra-byte"
            if not self._endpoint_exact(endpoint, descriptor):
                return "identity-mismatch"
            try:
                self.proof = self.auth_observer.validate_resident_proof(
                    resident
                )
            except self.auth_observer.LogicalResidentObserverError as exc:
                self.protocol_error = str(exc)[:160]
                return "authenticated-session-error"
            return "accepted"
        except Exception as exc:  # pragma: no cover - tty fault
            self.protocol_error = type(exc).__name__
            return "open-failed"
        finally:
            os.close(descriptor)

    def observe(
        self,
        *,
        timeout_sec: int,
        download_departure: dict[str, Any],
    ) -> dict[str, Any]:
        base_value, lane_supplement = super(_P331ObserverSession, self)._observe_value(
            timeout_sec=timeout_sec,
            download_departure=download_departure,
        )
        resident = self.resident_result
        sessions = () if resident is None else resident.sessions
        proof = dict(self.proof or {})
        tx = b"".join(item.raw_tx for item in sessions)
        rx = b"".join(item.raw_rx for item in sessions)
        diagnostics = [
            [
                {"stage": item.stage, "code": item.code}
                for item in session.audit.diagnostics
            ]
            if session.audit is not None
            else []
            for session in sessions
        ]
        retries = [
            session.audit.rng_eagain_retries
            if session.audit is not None
            else None
            for session in sessions
        ]
        partial = [
            {
                "session_index": session.index,
                "current_stage": (
                    session.audit.current_stage if session.audit is not None else None
                ),
                "failure_stage": (
                    session.audit.failure_stage if session.audit is not None else None
                ),
                "failure_code": (
                    session.audit.failure_code if session.audit is not None else None
                ),
                "exception_type": (
                    session.audit.exception_type
                    if session.audit is not None
                    else session.error_type
                ),
                "exception_sha256": (
                    session.audit.exception_sha256
                    if session.audit is not None
                    else None
                ),
            }
            for session in sessions
        ]
        complete = bool(
            resident is not None
            and resident.complete
            and proof.get("logical_resident_proof") is True
            and proof.get("same_tty_fd") is True
            and proof.get("physical_reopen_count") == 0
            and proof.get("session_count")
            == self.auth_runtime.MAX_SESSIONS
            and not self.trailing_rx
        )
        accepted = bool(base_value.get("accepted") is True and complete)
        classification = base_value["classification"]
        if classification == "accepted" and not accepted:
            classification = "authenticated-session-error"
        value = dict(base_value)
        value.pop("tx_hex", None)
        value.pop("pid1_framed_exec_proof", None)
        value.update(
            {
                "schema": self.receipt_schema,
                "contract_id": self.auth_observer.CONTRACT_ID,
                "target": self.auth_runtime.TARGET,
                "banner_hex": self.auth_runtime.DEVICE_BANNER.hex(),
                "tx": _p327_identity(tx),
                "session_tx_hex": [item.raw_tx.hex() for item in sessions],
                "rx": _p327_identity(rx),
                "trailing_rx": _p327_identity(self.trailing_rx),
                "trailing_bytes_seen": len(self.trailing_rx),
                "diagnostics": diagnostics,
                "rng_eagain_retries": retries,
                "partial_sessions": partial,
                "proof": proof,
                "auth_algorithm": "hmac-sha256",
                "auth_tag_size": self.auth_runtime.AUTH_TAG_SIZE,
                "auth_key_sha256": self.auth_key_sha256,
                "hmac_authenticated": complete,
                "pid1_authenticated_framed_exec_proof": complete,
                "busybox_ash_command_proof": complete,
                "framed_session_closed": complete,
                "logical_resident_proof": complete,
                "same_tty_fd": complete,
                "physical_reopen_count": 0,
                "fixed_p330_commands": complete,
                "session_count": len(sessions),
                "successful_sessions": (
                    0 if resident is None else resident.successful_sessions
                ),
                "session_cap": self.auth_runtime.MAX_SESSIONS,
                "reconnect_count": 0,
                "reconnect_cap": 0,
                "commands_per_session": len(
                    self.auth_runtime.DEFAULT_COMMANDS
                ),
                "command_count": len(sessions)
                * len(self.auth_runtime.DEFAULT_COMMANDS),
                "max_commands": self.auth_runtime.MAX_COMMANDS,
                "interactive_pty_proof": False,
                "caller_selected_command": False,
                "arbitrary_file_transfer": False,
                "persistent_state": False,
                "expected_size": len(self.auth_runtime.DEVICE_BANNER)
                * self.auth_runtime.MAX_SESSIONS,
                "exact": accepted,
                "extra_byte": bool(self.trailing_rx),
                "classification": classification,
                "accepted": accepted,
            }
        )
        self._publish_value(value, lane_supplement, label=self.receipt_label)
        return value


@dataclass
class _P333ObserverSession(_P332ObserverSession):
    """P3.32 same-FD session with one stage-0 frame before each OPEN."""

    auth_observer: Any = p333_open_entry_observer
    auth_runtime: Any = p333_open_entry_runtime
    receipt_schema: str = P333_OBSERVER_RECEIPT_SCHEMA
    receipt_label: str = "P333 OPEN-entry logical resident observer receipt"
    campaign_label: str = "P3.33"
    proof_key: str = "p333_authenticated_logical_resident"
    raw_argv0_name: str = "tty-cdc-acm-p333"


@dataclass
class _P334ObserverSession(_P333ObserverSession):
    """P3.33 same-FD session rebound to P3.34 without protocol changes."""

    auth_observer: Any = p334_first_read_observer
    auth_runtime: Any = p334_first_read_runtime
    receipt_schema: str = P334_OBSERVER_RECEIPT_SCHEMA
    receipt_label: str = "P334 first-read logical resident observer receipt"
    campaign_label: str = "P3.34"
    proof_key: str = "p334_authenticated_logical_resident"
    raw_argv0_name: str = "tty-cdc-acm-p334"


@dataclass
class _P335ObserverSession(_P334ObserverSession):
    """Prove two same-FD sessions and one exact host close/reopen session."""

    auth_observer: Any = p335_retained_observer
    auth_runtime: Any = p335_retained_runtime
    receipt_schema: str = P335_OBSERVER_RECEIPT_SCHEMA
    receipt_label: str = "P335 attended resident listener observer receipt"
    campaign_label: str = "P3.35"
    proof_key: str = "p335_authenticated_attended_resident"
    raw_argv0_name: str = "tty-cdc-acm-p335"

    def _read_endpoint(
        self,
        endpoint: Any,
        deadline: float,
        writer: raw_capture.RawCaptureWriter,
    ) -> str:
        self.endpoint = endpoint
        stopped = self._settle_guard_properties(endpoint, deadline)
        if stopped is not None:
            return stopped
        if not self._endpoint_exact(endpoint):
            return "identity-mismatch"
        path = self.base.dev_root / endpoint.tty_name

        def open_exact() -> int:
            settled = self._settle_guard_properties(endpoint, deadline)
            if settled is not None or not self._endpoint_exact(endpoint):
                raise self.auth_observer.AuthObserverError(
                    "P335 exact endpoint changed before reopen"
                )
            descriptor = os.open(
                path,
                os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC,
            )
            try:
                fcntl.ioctl(descriptor, termios.TIOCEXCL)
                if not self._endpoint_exact(endpoint, descriptor):
                    raise self.auth_observer.AuthObserverError(
                        "P335 exact endpoint changed after reopen"
                    )
                self.base._raw_tty(descriptor)
                return descriptor
            except BaseException:
                os.close(descriptor)
                raise

        try:
            descriptor = open_exact()
        except OSError:
            return "open-failed"
        except self.auth_observer.AuthObserverError:
            return "identity-mismatch"
        try:
            resident = self.auth_observer.exchange_retained(
                descriptor,
                self.auth_key,
                reopen=open_exact,
                timeout_sec=min(
                    self.auth_observer.SESSION_TIMEOUT_SEC,
                    max(0.001, deadline - time.monotonic()),
                ),
                writer=writer,
            )
        except self.auth_observer.RetainedListenerObserverError as exc:
            self.resident_result = exc.result
            self.protocol_error = str(exc)[:160]
            return "authenticated-session-error"
        except Exception as exc:  # pragma: no cover - tty fault
            self.protocol_error = type(exc).__name__
            return "open-failed"
        self.resident_result = resident
        self.exchange = resident.sessions[-1].result
        if not self._endpoint_exact(endpoint):
            return "identity-mismatch"
        try:
            self.proof = self.auth_observer.validate_retained_proof(resident)
        except self.auth_observer.AuthObserverError as exc:
            self.protocol_error = str(exc)[:160]
            return "authenticated-session-error"
        self.trailing_rx = b""
        return "accepted"

    def observe(
        self,
        *,
        timeout_sec: int,
        download_departure: dict[str, Any],
    ) -> dict[str, Any]:
        base_value, lane_supplement = super(
            _P331ObserverSession, self
        )._observe_value(
            timeout_sec=timeout_sec,
            download_departure=download_departure,
        )
        resident = self.resident_result
        sessions = () if resident is None else resident.sessions
        proof = dict(self.proof or {})
        tx = b"".join(item.raw_tx for item in sessions)
        rx = b"".join(item.raw_rx for item in sessions)
        diagnostics = [
            [
                {"stage": item.stage, "code": item.code}
                for item in session.audit.diagnostics
            ]
            if session.audit is not None
            else []
            for session in sessions
        ]
        retries = [
            session.audit.rng_eagain_retries
            if session.audit is not None
            else None
            for session in sessions
        ]
        partial = [
            {
                "session_index": session.index,
                "current_stage": (
                    session.audit.current_stage if session.audit is not None else None
                ),
                "failure_stage": (
                    session.audit.failure_stage if session.audit is not None else None
                ),
                "failure_code": (
                    session.audit.failure_code if session.audit is not None else None
                ),
                "exception_type": (
                    session.audit.exception_type
                    if session.audit is not None
                    else session.error_type
                ),
                "exception_sha256": (
                    session.audit.exception_sha256
                    if session.audit is not None
                    else None
                ),
            }
            for session in sessions
        ]
        complete = bool(
            resident is not None
            and resident.complete
            and proof.get("retained_listener_proof") is True
            and proof.get("per_boot_identity_proof") is True
            and proof.get("same_boot_id") is True
            and proof.get("same_initial_fd") is True
            and proof.get("descriptor_reopened") is True
            and proof.get("physical_reopen_count") == 1
            and proof.get("session_count") == self.auth_observer.MAX_SESSIONS
        )
        accepted = bool(base_value.get("accepted") is True and complete)
        classification = base_value["classification"]
        if classification == "accepted" and not accepted:
            classification = "authenticated-session-error"
        value = dict(base_value)
        value.pop("tx_hex", None)
        value.pop("pid1_framed_exec_proof", None)
        value.update(
            {
                "schema": self.receipt_schema,
                "contract_id": self.auth_observer.CONTRACT_ID,
                "target": self.auth_runtime.TARGET,
                "banner_hex": self.auth_runtime.DEVICE_BANNER.hex(),
                "tx": _p327_identity(tx),
                "session_tx_hex": [item.raw_tx.hex() for item in sessions],
                "rx": _p327_identity(rx),
                "trailing_rx": _p327_identity(b""),
                "trailing_bytes_seen": 0,
                "diagnostics": diagnostics,
                "rng_eagain_retries": retries,
                "partial_sessions": partial,
                "proof": proof,
                "auth_algorithm": "hmac-sha256",
                "auth_tag_size": self.auth_runtime.AUTH_TAG_SIZE,
                "auth_key_sha256": self.auth_key_sha256,
                "hmac_authenticated": complete,
                "pid1_authenticated_framed_exec_proof": complete,
                "busybox_ash_command_proof": complete,
                "framed_session_closed": complete,
                "logical_resident_proof": complete,
                "same_tty_fd": complete,
                "physical_reopen_count": 1 if complete else 0,
                "fixed_p330_commands": complete,
                "session_count": len(sessions),
                "successful_sessions": (
                    0 if resident is None else resident.successful_sessions
                ),
                "session_cap": self.auth_observer.MAX_SESSIONS,
                "reconnect_count": (
                    0 if resident is None else resident.reconnect_count
                ),
                "reconnect_cap": self.auth_observer.MAX_RECONNECTS,
                "commands_per_session": len(self.auth_runtime.DEFAULT_COMMANDS),
                "command_count": len(sessions)
                * len(self.auth_runtime.DEFAULT_COMMANDS),
                "max_commands": self.auth_runtime.MAX_COMMANDS,
                "interactive_pty_proof": False,
                "caller_selected_command": False,
                "arbitrary_file_transfer": False,
                "persistent_state": False,
                "expected_size": len(self.auth_runtime.DEVICE_BANNER)
                * self.auth_observer.MAX_SESSIONS,
                "exact": accepted,
                "extra_byte": False,
                "classification": classification,
                "accepted": accepted,
            }
        )
        self._publish_value(value, lane_supplement, label=self.receipt_label)
        return value


@contextlib.contextmanager
def _p328_candidate_observer_session(
    prepared: PreparedRun,
    spec: dict[str, str],
    *,
    lane_value: dict[str, Any],
    lane_receipt: dict[str, Any],
    usb_root: Path,
    typec_root: Path,
) -> Iterator[_P328ObserverSession]:
    """Arm the inherited lane only after the fixed credential is checked."""
    if spec.get("protocol_contract") != p328_auth_observer.CONTRACT_ID:
        raise F1LiveError("P3.28 authenticated observer contract differs")
    key, key_sha256 = _p328_read_auth_key(prepared)
    inherited_spec = _p327_inherited_spec(spec)
    with p325_guard_adapter.observer_session(
        inherited_spec,
        prepared.private_target["topology"],
        prepared.run_dir,
        _candidate_observer_binding(prepared),
        lane_value,
        lane_receipt,
        usb_root=usb_root,
        typec_root=typec_root,
    ) as inherited:
        base = inherited.delegate.delegate
        yield _P328ObserverSession(
            inherited,
            base,
            inherited_spec,
            prepared.run_dir,
            lane_value,
            lane_receipt,
            usb_root,
            typec_root,
            auth_key=key,
            auth_key_sha256=key_sha256,
        )


@contextlib.contextmanager
def _p329_candidate_observer_session(
    prepared: PreparedRun,
    spec: dict[str, str],
    *,
    lane_value: dict[str, Any],
    lane_receipt: dict[str, Any],
    usb_root: Path,
    typec_root: Path,
) -> Iterator[_P329ObserverSession]:
    """Arm the exact inherited lane, then apply only the bounded settle."""
    if spec.get("protocol_contract") != p329_auth_observer.CONTRACT_ID:
        raise F1LiveError("P3.29 authenticated observer contract differs")
    if (
        spec.get("udev_guard_settle_timeout_ms") != 500
        or spec.get("udev_guard_settle_poll_ms") != 25
        or spec.get("guard_properties_required")
        != ["ID_MM_DEVICE_IGNORE=1", "ID_MM_PORT_IGNORE=1"]
    ):
        raise F1LiveError("P3.29 bounded udev settle contract differs")
    key, key_sha256 = _p328_read_auth_key(prepared)
    inherited_spec = _p327_inherited_spec(spec)
    with p325_guard_adapter.observer_session(
        inherited_spec,
        prepared.private_target["topology"],
        prepared.run_dir,
        _candidate_observer_binding(prepared),
        lane_value,
        lane_receipt,
        usb_root=usb_root,
        typec_root=typec_root,
    ) as inherited:
        base = inherited.delegate.delegate
        yield _P329ObserverSession(
            inherited,
            base,
            inherited_spec,
            prepared.run_dir,
            lane_value,
            lane_receipt,
            usb_root,
            typec_root,
            auth_key=key,
            auth_key_sha256=key_sha256,
        )


@contextlib.contextmanager
def _p330_candidate_observer_session(
    prepared: PreparedRun,
    spec: dict[str, Any],
    *,
    lane_value: dict[str, Any],
    lane_receipt: dict[str, Any],
    usb_root: Path,
    typec_root: Path,
) -> Iterator[_P330ObserverSession]:
    """Arm P329's exact settled lane with P330's diagnostic codec."""
    if spec.get("protocol_contract") != p330_auth_observer.CONTRACT_ID:
        raise F1LiveError("P3.30 authenticated observer contract differs")
    expected = {
        "udev_guard_settle_timeout_ms": 500,
        "udev_guard_settle_poll_ms": 25,
        "guard_properties_required": [
            "ID_MM_DEVICE_IGNORE=1",
            "ID_MM_PORT_IGNORE=1",
        ],
        "diagnostic_frame_type": p330_auth_runtime.DIAGNOSTIC_FRAME_TYPE,
        "diagnostic_payload_size": p330_auth_runtime.DIAGNOSTIC_PAYLOAD_SIZE,
        "diagnostic_stages": [
            {"stage": p330_auth_runtime.DIAGNOSTIC_STAGE_OPEN_PARSED, "name": "open-parsed"},
            {"stage": p330_auth_runtime.DIAGNOSTIC_STAGE_RNG, "name": "rng"},
        ],
        "rng_eagain_retry_limit": p330_auth_runtime.RNG_EAGAIN_RETRY_LIMIT,
        "open_diagnostic_timeout_ms": int(
            p330_auth_observer.OPEN_DIAGNOSTIC_TIMEOUT_SEC * 1000
        ),
        "rng_diagnostic_timeout_ms": int(
            p330_auth_observer.RNG_DIAGNOSTIC_TIMEOUT_SEC * 1000
        ),
        "partial_exchange_durable": True,
    }
    if any(spec.get(key) != value for key, value in expected.items()):
        raise F1LiveError("P3.30 bounded diagnostic contract differs")
    key, key_sha256 = _p328_read_auth_key(prepared)
    inherited_spec = _p327_inherited_spec(spec)
    with p325_guard_adapter.observer_session(
        inherited_spec,
        prepared.private_target["topology"],
        prepared.run_dir,
        _candidate_observer_binding(prepared),
        lane_value,
        lane_receipt,
        usb_root=usb_root,
        typec_root=typec_root,
    ) as inherited:
        base = inherited.delegate.delegate
        yield _P330ObserverSession(
            inherited,
            base,
            inherited_spec,
            prepared.run_dir,
            lane_value,
            lane_receipt,
            usb_root,
            typec_root,
            auth_key=key,
            auth_key_sha256=key_sha256,
        )


@contextlib.contextmanager
def _p331_candidate_observer_session(
    prepared: PreparedRun,
    spec: dict[str, Any],
    *,
    lane_value: dict[str, Any],
    lane_receipt: dict[str, Any],
    usb_root: Path,
    typec_root: Path,
) -> Iterator[_P331ObserverSession]:
    """Arm the exact P329 lane for two bounded P331 heartbeat sessions."""
    if spec.get("protocol_contract") != p331_resident_observer.CONTRACT_ID:
        raise F1LiveError("P3.31 resident observer contract differs")
    expected = {
        "udev_guard_settle_timeout_ms": 500,
        "udev_guard_settle_poll_ms": 25,
        "guard_properties_required": [
            "ID_MM_DEVICE_IGNORE=1",
            "ID_MM_PORT_IGNORE=1",
        ],
        "diagnostic_frame_type": p331_resident_runtime.DIAGNOSTIC_FRAME_TYPE,
        "diagnostic_payload_size": p331_resident_runtime.DIAGNOSTIC_PAYLOAD_SIZE,
        "diagnostic_stages": [
            {
                "stage": p331_resident_runtime.DIAGNOSTIC_STAGE_OPEN_PARSED,
                "name": "open-parsed",
            },
            {
                "stage": p331_resident_runtime.DIAGNOSTIC_STAGE_RNG,
                "name": "rng",
            },
        ],
        "rng_eagain_retry_limit": p331_resident_runtime.RNG_EAGAIN_RETRY_LIMIT,
        "partial_exchange_durable": True,
        "session_cap": p331_resident_runtime.MAX_SESSIONS,
        "reconnect_cap": p331_resident_runtime.MAX_RECONNECTS,
        "clean_close_required": True,
        "clean_reconnect_required": True,
        "fresh_distinct_nonce_hashes": True,
        "diagnostics_per_session": True,
        "fixed_heartbeat_only": True,
        "caller_selected_command": False,
        "interactive_pty": False,
        "arbitrary_file_transfer": False,
        "persistent_state": False,
    }
    if any(spec.get(key) != value for key, value in expected.items()):
        raise F1LiveError("P3.31 bounded resident contract differs")
    key, key_sha256 = _p328_read_auth_key(prepared)
    inherited_spec = _p327_inherited_spec(spec)
    with p325_guard_adapter.observer_session(
        inherited_spec,
        prepared.private_target["topology"],
        prepared.run_dir,
        _candidate_observer_binding(prepared),
        lane_value,
        lane_receipt,
        usb_root=usb_root,
        typec_root=typec_root,
    ) as inherited:
        base = inherited.delegate.delegate
        yield _P331ObserverSession(
            inherited,
            base,
            inherited_spec,
            prepared.run_dir,
            lane_value,
            lane_receipt,
            usb_root,
            typec_root,
            auth_key=key,
            auth_key_sha256=key_sha256,
        )


@contextlib.contextmanager
def _logical_resident_candidate_observer_session(
    prepared: PreparedRun,
    spec: dict[str, Any],
    *,
    lane_value: dict[str, Any],
    lane_receipt: dict[str, Any],
    usb_root: Path,
    typec_root: Path,
    observer_module: Any,
    runtime_module: Any,
    session_type: type[_P332ObserverSession],
    label: str,
    entry_diagnostic: bool,
) -> Iterator[_P332ObserverSession]:
    """Arm one exact tty for a bounded same-FD logical-session campaign."""
    if spec.get("protocol_contract") != observer_module.CONTRACT_ID:
        raise F1LiveError(f"{label} logical resident observer contract differs")
    diagnostic_stages = [
        {
            "stage": runtime_module.DIAGNOSTIC_STAGE_OPEN_PARSED,
            "name": "open-parsed",
        },
        {"stage": runtime_module.DIAGNOSTIC_STAGE_RNG, "name": "rng"},
    ]
    if entry_diagnostic:
        diagnostic_stages.insert(0, {"stage": 0, "name": "console-enter"})
    retained_reopen = label == "P3.35"
    expected = {
        "udev_guard_settle_timeout_ms": 500,
        "udev_guard_settle_poll_ms": 25,
        "guard_properties_required": [
            "ID_MM_DEVICE_IGNORE=1",
            "ID_MM_PORT_IGNORE=1",
        ],
        "diagnostic_frame_type": runtime_module.DIAGNOSTIC_FRAME_TYPE,
        "diagnostic_payload_size": runtime_module.DIAGNOSTIC_PAYLOAD_SIZE,
        "diagnostic_stages": diagnostic_stages,
        "rng_eagain_retry_limit": runtime_module.RNG_EAGAIN_RETRY_LIMIT,
        "partial_exchange_durable": True,
        "session_cap": (
            observer_module.MAX_SESSIONS
            if retained_reopen
            else runtime_module.MAX_SESSIONS
        ),
        "reconnect_cap": observer_module.MAX_RECONNECTS if retained_reopen else 0,
        "clean_close_required": True,
        "fresh_distinct_nonce_hashes": True,
        "diagnostics_per_session": True,
        "fixed_p330_commands": True,
        "same_tty_fd_required": True,
        "host_tty_close_reopen": retained_reopen,
        "transport_reconnect": retained_reopen,
        "caller_selected_command": False,
        "interactive_pty": False,
        "arbitrary_file_transfer": False,
        "persistent_state": False,
    }
    if entry_diagnostic:
        expected.update(
            {
                "entry_diagnostic_stage": 0,
                "entry_diagnostic_before_console": True,
            }
        )
    if retained_reopen:
        expected.update(
            {
                "physical_reopen_count": 1,
                "per_boot_identity_required": True,
                "listener_wait_after_proof": True,
                "resident_lease_schema": p335_resident_session.SCHEMA,
                "resident_lease_duration_sec": p335_resident_session.MAX_LEASE_SECONDS,
                "resident_lease_action_cap": p335_resident_session.MAX_ACTIONS,
                "action_retry": False,
            }
        )
    if any(spec.get(key) != value for key, value in expected.items()):
        raise F1LiveError(f"{label} bounded logical resident contract differs")
    key, key_sha256 = _p328_read_auth_key(prepared)
    inherited_spec = _p327_inherited_spec(spec)
    with p325_guard_adapter.observer_session(
        inherited_spec,
        prepared.private_target["topology"],
        prepared.run_dir,
        _candidate_observer_binding(prepared),
        lane_value,
        lane_receipt,
        usb_root=usb_root,
        typec_root=typec_root,
    ) as inherited:
        base = inherited.delegate.delegate
        yield session_type(
            inherited,
            base,
            inherited_spec,
            prepared.run_dir,
            lane_value,
            lane_receipt,
            usb_root,
            typec_root,
            auth_key=key,
            auth_key_sha256=key_sha256,
        )


@contextlib.contextmanager
def _p332_candidate_observer_session(
    prepared: PreparedRun,
    spec: dict[str, Any],
    *,
    lane_value: dict[str, Any],
    lane_receipt: dict[str, Any],
    usb_root: Path,
    typec_root: Path,
) -> Iterator[_P332ObserverSession]:
    with _logical_resident_candidate_observer_session(
        prepared,
        spec,
        lane_value=lane_value,
        lane_receipt=lane_receipt,
        usb_root=usb_root,
        typec_root=typec_root,
        observer_module=p332_logical_resident_observer,
        runtime_module=p332_logical_resident_runtime,
        session_type=_P332ObserverSession,
        label="P3.32",
        entry_diagnostic=False,
    ) as session:
        yield session


@contextlib.contextmanager
def _p333_candidate_observer_session(
    prepared: PreparedRun,
    spec: dict[str, Any],
    *,
    lane_value: dict[str, Any],
    lane_receipt: dict[str, Any],
    usb_root: Path,
    typec_root: Path,
) -> Iterator[_P333ObserverSession]:
    with _logical_resident_candidate_observer_session(
        prepared,
        spec,
        lane_value=lane_value,
        lane_receipt=lane_receipt,
        usb_root=usb_root,
        typec_root=typec_root,
        observer_module=p333_open_entry_observer,
        runtime_module=p333_open_entry_runtime,
        session_type=_P333ObserverSession,
        label="P3.33",
        entry_diagnostic=True,
    ) as session:
        yield session


@contextlib.contextmanager
def _p334_candidate_observer_session(
    prepared: PreparedRun,
    spec: dict[str, Any],
    *,
    lane_value: dict[str, Any],
    lane_receipt: dict[str, Any],
    usb_root: Path,
    typec_root: Path,
) -> Iterator[_P334ObserverSession]:
    with _logical_resident_candidate_observer_session(
        prepared,
        spec,
        lane_value=lane_value,
        lane_receipt=lane_receipt,
        usb_root=usb_root,
        typec_root=typec_root,
        observer_module=p334_first_read_observer,
        runtime_module=p334_first_read_runtime,
        session_type=_P334ObserverSession,
        label="P3.34",
        entry_diagnostic=True,
    ) as session:
        yield session


@contextlib.contextmanager
def _p335_candidate_observer_session(
    prepared: PreparedRun,
    spec: dict[str, Any],
    *,
    lane_value: dict[str, Any],
    lane_receipt: dict[str, Any],
    usb_root: Path,
    typec_root: Path,
) -> Iterator[_P335ObserverSession]:
    with _logical_resident_candidate_observer_session(
        prepared,
        spec,
        lane_value=lane_value,
        lane_receipt=lane_receipt,
        usb_root=usb_root,
        typec_root=typec_root,
        observer_module=p335_retained_observer,
        runtime_module=p335_retained_runtime,
        session_type=_P335ObserverSession,
        label="P3.35",
        entry_diagnostic=True,
    ) as session:
        yield session


def _p328_receipt_secret_free(item: Any) -> None:
    if isinstance(item, dict):
        if any(
            key in item
            for key in (
                "auth_key",
                "auth_key_path",
                "auth_key_bytes",
                "auth_key_hex",
                "key_path",
                "nonce",
                "nonce_bytes",
                "nonce_hex",
                "challenge_nonce",
                "challenge_nonce_bytes",
            )
        ):
            raise p328_auth_observer.AuthObserverError(
                "P328 receipt contains credential or nonce bytes"
            )
        for nested in item.values():
            _p328_receipt_secret_free(nested)
    elif isinstance(item, list):
        for nested in item:
            _p328_receipt_secret_free(nested)


def _p328_receipt_identity(item: Any, label: str) -> dict[str, Any]:
    if (
        not isinstance(item, dict)
        or set(item) != {"size", "sha256"}
        or type(item["size"]) is not int
        or item["size"] < 0
        or not isinstance(item["sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is None
    ):
        raise p328_auth_observer.AuthObserverError(
            f"P328 {label} identity differs"
        )
    return item


def _p328_validate_common_receipt(
    prepared: PreparedRun,
    value: dict[str, Any],
    spec: dict[str, Any],
) -> tuple[dict[str, Any], str, str | None]:
    inherited_spec = _p327_inherited_spec(spec)
    baseline = _receipt(
        prepared.run_dir / "candidate-observer-baseline.json",
        "P328 candidate observer baseline",
    )
    departure = _receipt(
        prepared.run_dir / "candidate-observer-download-departure.json",
        "P328 candidate observer departure",
    )
    guard = _receipt(
        prepared.run_dir / "candidate-observer-guard.json",
        "P328 candidate observer guard",
    )
    topology = hashlib.sha256(
        p324_typec_lane.CANDIDATE_TOPOLOGY.removeprefix("usb:").encode()
    ).hexdigest()
    endpoint = value["endpoint_identity_sha256"]
    bound = _p328_bound_auth_key_identity(prepared)
    if (
        value["binding"] != _candidate_observer_binding(prepared)
        or value["spec_sha256"] != cdc_acm_observer.digest(inherited_spec)
        or value["baseline_sha256"] != baseline["sha256"]
        or value["download_departure_sha256"] != departure["sha256"]
        or value["guard_sha256"] != guard["sha256"]
        or value["topology_sha256"] != topology
        or value["auth_key_sha256"] != bound["sha256"]
        or value["accepted"] is True
        and value["download_endpoint_absent"] is not True
        or endpoint is not None
        and (
            not isinstance(endpoint, str)
            or re.fullmatch(r"[0-9a-f]{64}", endpoint) is None
        )
    ):
        raise p328_auth_observer.AuthObserverError(
            "P328 retained receipt binding differs"
        )

    raw = value["raw"]
    if not isinstance(raw, dict) or set(raw) != {
        "path",
        "size",
        "sha256",
        "capture_receipt",
    }:
        raise p328_auth_observer.AuthObserverError("P328 raw receipt shape differs")
    capture = raw["capture_receipt"]
    if not isinstance(capture, dict) or set(capture) != {"path", "size", "sha256"}:
        raise p328_auth_observer.AuthObserverError(
            "P328 capture receipt shape differs"
        )
    try:
        raw_path = Path(raw["path"])
        capture_path = Path(capture["path"])
    except (TypeError, ValueError) as exc:
        raise p328_auth_observer.AuthObserverError(
            "P328 raw receipt paths differ"
        ) from exc
    expected_raw = prepared.run_dir / "candidate-observer.raw"
    expected_capture = prepared.run_dir / "candidate-observer.capture.json"
    if (
        raw_path != expected_raw
        or capture_path != expected_capture
        or type(raw["size"]) is not int
        or not 0 <= raw["size"] <= P328_MAX_RAW_BYTES
        or not isinstance(raw["sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", raw["sha256"]) is None
        or type(capture["size"]) is not int
        or not isinstance(capture["sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", capture["sha256"]) is None
    ):
        raise p328_auth_observer.AuthObserverError("P328 raw receipt binding differs")
    try:
        raw_payload = raw_path.read_bytes()
        capture_payload = capture_path.read_bytes()
        handle = raw_capture.load_handle(capture_path)
    except (OSError, raw_capture.RawCaptureError) as exc:
        raise p328_auth_observer.AuthObserverError(
            "P328 raw evidence cannot be reopened"
        ) from exc
    if (
        len(raw_payload) != raw["size"]
        or hashlib.sha256(raw_payload).hexdigest() != raw["sha256"]
        or len(capture_payload) != capture["size"]
        or hashlib.sha256(capture_payload).hexdigest() != capture["sha256"]
        or handle.stdout_path != expected_raw
        or handle.stderr_path != prepared.run_dir / "candidate-observer.raw.stderr"
        or handle.returncode != 0
        or handle.timed_out
        or handle.output_exceeded
        or handle.producer_error_type is not None
        or raw_capture.read_stdout(handle, maximum=P328_MAX_RAW_BYTES) != raw_payload
        or raw_capture.read_stderr(handle, maximum=1) != b""
    ):
        raise p328_auth_observer.AuthObserverError("P328 raw evidence changed")

    tx = _p328_receipt_identity(value["tx"], "tx")
    rx = _p328_receipt_identity(value["rx"], "rx")
    trailing = _p328_receipt_identity(value["trailing_rx"], "trailing")
    if (
        rx["size"] != len(raw_payload)
        or rx["sha256"] != hashlib.sha256(raw_payload).hexdigest()
        or trailing["size"] != value["trailing_bytes_seen"]
        or trailing["size"] not in {0, 1}
        or trailing["sha256"]
        != hashlib.sha256(
            raw_payload[-trailing["size"] :] if trailing["size"] else b""
        ).hexdigest()
    ):
        raise p328_auth_observer.AuthObserverError(
            "P328 rx/trailing accounting differs"
        )

    lane = value["lane"]
    if not isinstance(lane, dict):
        raise p328_auth_observer.AuthObserverError("P328 lane receipt is absent")
    if (
        lane.get("source_topology") != p324_typec_lane.SOURCE_TOPOLOGY
        or lane.get("candidate_topology") != p324_typec_lane.CANDIDATE_TOPOLOGY
        or lane.get("selector_topology_count") != 1
        or lane.get("opens_only_candidate_topology") is not True
        or lane.get("device_commands") is not False
    ):
        raise p328_auth_observer.AuthObserverError(
            "P328 lane topology receipt differs"
        )
    inventory = lane.get("end_inventory")
    try:
        p324_cdc_observer._validate_inventory(inventory, label="P328 reopen")  # noqa: SLF001
        source_row = inventory["rows"][p324_typec_lane.SOURCE_TOPOLOGY]
        candidate_row = inventory["rows"][p324_typec_lane.CANDIDATE_TOPOLOGY]
        source_digest = hashlib.sha256(
            p324_typec_lane.SOURCE_TOPOLOGY.removeprefix("usb:").encode()
        ).hexdigest()
        if (
            source_row["topology_sha256"] != source_digest
            or candidate_row["topology_sha256"] != topology
            or any(
                type(lane.get(key)) is not bool
                for key in (
                    "both_topologies_inventory_complete",
                    "accepted_inventory_exact",
                    "same_run_typec_partner_continuity",
                    "accepted_for_p324",
                )
            )
            or lane["accepted_for_p324"]
            is not (
                lane["accepted_inventory_exact"]
                and lane["same_run_typec_partner_continuity"]
            )
        ):
            raise p328_auth_observer.AuthObserverError(
                "P328 lane receipt semantics differ"
            )
    except p328_auth_observer.AuthObserverError:
        raise
    except (KeyError, TypeError, AttributeError, p324_cdc_observer.P324ObserverError) as exc:
        raise p328_auth_observer.AuthObserverError(
            "P328 lane inventory is incomplete"
        ) from exc
    return lane, topology, endpoint


def _p328_validate_receipt(
    prepared: PreparedRun,
    path: Path,
    spec: dict[str, Any],
    *,
    auth_observer: Any = p328_auth_observer,
    auth_runtime: Any = p328_auth_runtime,
    receipt_schema: str = P328_OBSERVER_RECEIPT_SCHEMA,
    classifications: set[str] = P328_CLASSIFICATIONS,
    label: str = "P328",
    proof_key: str = "p328_authenticated_exec",
    extra_keys: frozenset[str] = frozenset(),
    extra_validator: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    "Reopen an authenticated receipt using retained hashes; never reread its key."
    value = _read_json(path, f"{label} authenticated observer receipt")
    expected_keys = set(
        """
        schema contract_id target binding spec_sha256 baseline_sha256
        download_departure_sha256 download_endpoint_absent topology_sha256
        endpoint_identity_sha256 guard_sha256 raw banner_hex tx rx trailing_rx
        trailing_bytes_seen banner_seen challenge_seen ready_seen done_seen
        proof auth_algorithm auth_tag_size nonce_size auth_key_sha256
        challenge_nonce_sha256 hmac_authenticated
        pid1_authenticated_framed_exec_proof busybox_ash_command_proof
        framed_session_closed interactive_pty_proof caller_selected_command
        command_count max_commands lane expected_size exact extra_byte
        classification accepted bounded elapsed_sec
        """.split()
    )
    expected_keys.update(extra_keys)
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise p328_auth_observer.AuthObserverError(
            "P328 authenticated observer receipt shape differs"
        )
    _p328_receipt_secret_free(value)
    classification = value["classification"]
    accepted = value["accepted"]
    nonce_hash = value["challenge_nonce_sha256"]
    proof = value["proof"]
    if (
        value["schema"] != receipt_schema
        or value["contract_id"] != auth_observer.CONTRACT_ID
        or value["target"] != auth_observer.TARGET
        or value["banner_hex"] != auth_runtime.DEVICE_BANNER.hex()
        or value["expected_size"] != len(auth_runtime.DEVICE_BANNER)
        or value["auth_algorithm"] != "hmac-sha256"
        or value["auth_tag_size"] != auth_runtime.AUTH_TAG_SIZE
        or value["nonce_size"] != auth_runtime.NONCE_SIZE
        or type(value["download_endpoint_absent"]) is not bool
        or type(value["hmac_authenticated"]) is not bool
        or type(value["challenge_seen"]) is not bool
        or type(value["interactive_pty_proof"]) is not bool
        or value["interactive_pty_proof"] is not False
        or value["caller_selected_command"] is not True
        or value["command_count"] != len(auth_observer.DEFAULT_COMMANDS)
        or value["max_commands"] != auth_runtime.MAX_COMMANDS
        or type(value["bounded"]) is not bool
        or value["bounded"] is not True
        or type(accepted) is not bool
        or not isinstance(classification, str)
        or classification not in classifications
        or value["exact"] is not accepted
        or accepted is not (classification == "accepted")
        or type(value["trailing_bytes_seen"]) is not int
        or value["trailing_bytes_seen"] not in {0, 1}
        or value["extra_byte"] is not (value["trailing_bytes_seen"] > 0)
        or any(type(value[key]) is not bool for key in ("banner_seen", "ready_seen", "done_seen"))
        or value["framed_session_closed"]
        is not (value["banner_seen"] and value["challenge_seen"] and value["ready_seen"] and value["done_seen"])
        or isinstance(value["elapsed_sec"], bool)
        or not isinstance(value["elapsed_sec"], (int, float))
        or not math.isfinite(float(value["elapsed_sec"]))
        or not 0 <= value["elapsed_sec"] <= 600
        or (
            nonce_hash is not None
            and (
                not isinstance(nonce_hash, str)
                or re.fullmatch(r"[0-9a-f]{64}", nonce_hash) is None
            )
        )
        or not isinstance(proof, dict)
    ):
        raise p328_auth_observer.AuthObserverError(
            "P328 authenticated observer receipt semantics differ"
        )
    lane, topology, endpoint = _p328_validate_common_receipt(prepared, value, spec)
    bound = _p328_bound_auth_key_identity(prepared)
    if accepted:
        if (
            not all(
                value[key] is True
                for key in (
                    "hmac_authenticated",
                    "pid1_authenticated_framed_exec_proof",
                    "busybox_ash_command_proof",
                    "framed_session_closed",
                )
            )
            or nonce_hash is None
            or value["auth_key_sha256"] != bound["sha256"]
            or proof.get("auth_key_sha256") != bound["sha256"]
            or proof.get("challenge_nonce_sha256") != nonce_hash
            or proof.get("command_count") != 3
        ):
            raise p328_auth_observer.AuthObserverError(
                "P328 accepted receipt lacks authenticated proof"
            )
    elif any(
        type(value[key]) is not bool
        for key in (
            "hmac_authenticated",
            "pid1_authenticated_framed_exec_proof",
            "busybox_ash_command_proof",
            "framed_session_closed",
        )
    ):
        raise p328_auth_observer.AuthObserverError(
            "P328 no-proof flags are malformed"
        )
    result = {
        "classification": classification,
        "accepted": accepted,
        "receipt_sha256": _receipt(path, f"{label} authenticated observer receipt")["sha256"],
        "valid_receipt": True,
        "download_endpoint_absent": value["download_endpoint_absent"],
        "endpoint_identity_sha256": endpoint,
        "topology_sha256": value["topology_sha256"],
        "bounded": True,
        "source_topology_sha256": hashlib.sha256(
            p324_typec_lane.SOURCE_TOPOLOGY.removeprefix("usb:").encode()
        ).hexdigest(),
        "candidate_topology_sha256": topology,
        "both_topologies_inventory_complete": lane["both_topologies_inventory_complete"],
        "accepted_inventory_exact": lane["accepted_inventory_exact"],
        "same_run_typec_partner_continuity": lane["same_run_typec_partner_continuity"],
        "accepted_for_p324": lane["accepted_for_p324"],
        "hmac_authenticated": value["hmac_authenticated"],
        "pid1_authenticated_framed_exec_proof": value[
            "pid1_authenticated_framed_exec_proof"
        ],
        "busybox_ash_command_proof": value["busybox_ash_command_proof"],
        "framed_session_closed": value["framed_session_closed"],
        "interactive_pty_proof": value["interactive_pty_proof"],
        "caller_selected_command": value["caller_selected_command"],
        "command_count": value["command_count"],
        "max_commands": value["max_commands"],
        "auth_key_sha256": value["auth_key_sha256"],
        "challenge_nonce_sha256": value["challenge_nonce_sha256"],
        proof_key: proof,
    }
    if extra_validator is not None:
        result.update(extra_validator(value))
    return result


def _p329_validate_receipt(
    prepared: PreparedRun,
    path: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    return _p328_validate_receipt(
        prepared,
        path,
        spec,
        auth_observer=p329_auth_observer,
        auth_runtime=p329_auth_runtime,
        receipt_schema=P329_OBSERVER_RECEIPT_SCHEMA,
        classifications=P329_CLASSIFICATIONS,
        label="P329",
        proof_key="p329_authenticated_exec",
    )


P330_EXCHANGE_STAGES = frozenset(
    {
        "banner-read",
        "open-write",
        "open-diagnostic-read",
        "rng-diagnostic-read",
        "challenge-read",
        "auth-write",
        "ready-read",
        "exec-write",
        "exec-read",
        "close-write",
        "done-read",
        "complete",
    }
)
P330_RECEIPT_EXTRA_KEYS = frozenset(
    {"diagnostics", "rng_eagain_retries", "partial_exchange"}
)


def _p330_validate_receipt_extras(value: dict[str, Any]) -> dict[str, Any]:
    diagnostics = value["diagnostics"]
    retries = value["rng_eagain_retries"]
    partial = value["partial_exchange"]
    if (
        not isinstance(diagnostics, list)
        or len(diagnostics) > 2
        or not isinstance(partial, dict)
        or set(partial)
        != {
            "current_stage",
            "failure_stage",
            "failure_code",
            "exception_type",
            "exception_sha256",
        }
    ):
        raise p330_auth_observer.AuthObserverError(
            "P330 partial exchange receipt shape differs"
        )
    normalized: list[dict[str, int]] = []
    for item in diagnostics:
        if (
            not isinstance(item, dict)
            or set(item) != {"stage", "code"}
            or type(item["stage"]) is not int
            or type(item["code"]) is not int
        ):
            raise p330_auth_observer.AuthObserverError(
                "P330 diagnostic receipt differs"
            )
        normalized.append(dict(item))
    expected_stages = [
        p330_auth_runtime.DIAGNOSTIC_STAGE_OPEN_PARSED,
        p330_auth_runtime.DIAGNOSTIC_STAGE_RNG,
    ][: len(normalized)]
    if (
        [item["stage"] for item in normalized] != expected_stages
        or normalized
        and normalized[0]["code"] != 0
        or len(normalized) == 2
        and not -4095
        <= normalized[1]["code"]
        <= p330_auth_runtime.RNG_EAGAIN_RETRY_LIMIT
    ):
        raise p330_auth_observer.AuthObserverError(
            "P330 diagnostic receipt semantics differ"
        )
    rng_code = normalized[1]["code"] if len(normalized) == 2 else None
    expected_retries = rng_code if isinstance(rng_code, int) and rng_code >= 0 else None
    current_stage = partial["current_stage"]
    failure_stage = partial["failure_stage"]
    failure_code = partial["failure_code"]
    exception_type = partial["exception_type"]
    exception_sha256 = partial["exception_sha256"]
    if (
        retries != expected_retries
        or retries is not None
        and (
            type(retries) is not int
            or not 0 <= retries <= p330_auth_runtime.RNG_EAGAIN_RETRY_LIMIT
        )
        or current_stage is not None
        and current_stage not in P330_EXCHANGE_STAGES
        or failure_stage is not None
        and failure_stage not in P330_EXCHANGE_STAGES - {"complete"}
        or failure_code is not None
        and (type(failure_code) is not int or not -4095 <= failure_code <= 0)
    ):
        raise p330_auth_observer.AuthObserverError(
            "P330 partial exchange scalar differs"
        )
    if exception_type is None:
        if any(
            item is not None
            for item in (failure_stage, failure_code, exception_sha256)
        ) or current_stage not in {None, "complete"}:
            raise p330_auth_observer.AuthObserverError(
                "P330 partial exchange completion differs"
            )
    elif (
        not isinstance(exception_type, str)
        or re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", exception_type) is None
        or not isinstance(exception_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", exception_sha256) is None
        or current_stage != failure_stage
        or failure_stage is None
    ):
        raise p330_auth_observer.AuthObserverError(
            "P330 partial exchange failure differs"
        )
    if isinstance(rng_code, int) and rng_code < 0:
        if failure_stage != "rng-diagnostic-read" or failure_code != rng_code:
            raise p330_auth_observer.AuthObserverError(
                "P330 terminal RNG diagnostic differs"
            )
    if value["accepted"] is True and (
        current_stage != "complete"
        or normalized
        != [
            {
                "stage": p330_auth_runtime.DIAGNOSTIC_STAGE_OPEN_PARSED,
                "code": 0,
            },
            {
                "stage": p330_auth_runtime.DIAGNOSTIC_STAGE_RNG,
                "code": retries,
            },
        ]
        or exception_type is not None
    ):
        raise p330_auth_observer.AuthObserverError(
            "P330 accepted receipt lacks diagnostic completion"
        )
    return {
        "preauth_diagnostics": normalized,
        "rng_eagain_retries": retries,
        "partial_exchange": dict(partial),
    }


def _p330_validate_receipt(
    prepared: PreparedRun,
    path: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    return _p328_validate_receipt(
        prepared,
        path,
        spec,
        auth_observer=p330_auth_observer,
        auth_runtime=p330_auth_runtime,
        receipt_schema=P330_OBSERVER_RECEIPT_SCHEMA,
        classifications=P330_CLASSIFICATIONS,
        label="P330",
        proof_key="p330_authenticated_exec",
        extra_keys=P330_RECEIPT_EXTRA_KEYS,
        extra_validator=_p330_validate_receipt_extras,
    )


P331_PROOF_FIELDS = (
    "hmac_authenticated",
    "pid1_authenticated_framed_exec_proof",
    "busybox_ash_command_proof",
    "framed_session_closed",
    "resident_loop_proof",
    "fixed_heartbeat_status",
    "interactive_pty_proof",
    "caller_selected_command",
    "arbitrary_file_transfer",
    "persistent_state",
    "session_count",
    "successful_sessions",
    "session_cap",
    "reconnect_count",
    "reconnect_cap",
    "commands_per_session",
    "command_count",
    "max_commands",
    "auth_key_sha256",
)


def _p331_proof_state(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value.get(key) for key in P331_PROOF_FIELDS}


def _p331_proof_ok(value: Mapping[str, Any]) -> bool:
    return (
        all(
            value.get(key) is True
            for key in (
                "hmac_authenticated",
                "pid1_authenticated_framed_exec_proof",
                "busybox_ash_command_proof",
                "framed_session_closed",
                "resident_loop_proof",
                "fixed_heartbeat_status",
            )
        )
        and value.get("interactive_pty_proof") is False
        and value.get("caller_selected_command") is False
        and value.get("arbitrary_file_transfer") is False
        and value.get("persistent_state") is False
        and all(
            type(value.get(key)) is int
            for key in (
                "session_count",
                "successful_sessions",
                "session_cap",
                "reconnect_count",
                "reconnect_cap",
                "commands_per_session",
                "command_count",
                "max_commands",
            )
        )
        and value.get("session_count") == p331_resident_runtime.MAX_SESSIONS
        and value.get("successful_sessions") == p331_resident_runtime.MAX_SESSIONS
        and value.get("session_cap") == p331_resident_runtime.MAX_SESSIONS
        and value.get("reconnect_count") == p331_resident_runtime.MAX_RECONNECTS
        and value.get("reconnect_cap") == p331_resident_runtime.MAX_RECONNECTS
        and value.get("commands_per_session") == 1
        and value.get("command_count") == p331_resident_runtime.MAX_SESSIONS
        and value.get("max_commands") == p331_resident_runtime.MAX_COMMANDS
    )


P332_PROOF_FIELDS = (
    "hmac_authenticated",
    "pid1_authenticated_framed_exec_proof",
    "busybox_ash_command_proof",
    "framed_session_closed",
    "logical_resident_proof",
    "same_tty_fd",
    "physical_reopen_count",
    "fixed_p330_commands",
    "interactive_pty_proof",
    "caller_selected_command",
    "arbitrary_file_transfer",
    "persistent_state",
    "session_count",
    "successful_sessions",
    "session_cap",
    "reconnect_count",
    "reconnect_cap",
    "commands_per_session",
    "command_count",
    "max_commands",
    "auth_key_sha256",
)


def _p332_proof_state(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value.get(key) for key in P332_PROOF_FIELDS}


def _p332_proof_ok(value: Mapping[str, Any]) -> bool:
    return (
        all(
            value.get(key) is True
            for key in (
                "hmac_authenticated",
                "pid1_authenticated_framed_exec_proof",
                "busybox_ash_command_proof",
                "framed_session_closed",
                "logical_resident_proof",
                "same_tty_fd",
                "fixed_p330_commands",
            )
        )
        and value.get("physical_reopen_count") == 0
        and value.get("interactive_pty_proof") is False
        and value.get("caller_selected_command") is False
        and value.get("arbitrary_file_transfer") is False
        and value.get("persistent_state") is False
        and all(
            type(value.get(key)) is int
            for key in (
                "physical_reopen_count",
                "session_count",
                "successful_sessions",
                "session_cap",
                "reconnect_count",
                "reconnect_cap",
                "commands_per_session",
                "command_count",
                "max_commands",
            )
        )
        and value.get("session_count") == p332_logical_resident_runtime.MAX_SESSIONS
        and value.get("successful_sessions")
        == p332_logical_resident_runtime.MAX_SESSIONS
        and value.get("session_cap") == p332_logical_resident_runtime.MAX_SESSIONS
        and value.get("reconnect_count") == 0
        and value.get("reconnect_cap") == 0
        and value.get("commands_per_session")
        == len(p332_logical_resident_runtime.DEFAULT_COMMANDS)
        and value.get("command_count")
        == p332_logical_resident_runtime.MAX_SESSIONS
        * len(p332_logical_resident_runtime.DEFAULT_COMMANDS)
        and value.get("max_commands") == p332_logical_resident_runtime.MAX_COMMANDS
    )


def _p335_proof_ok(value: Mapping[str, Any]) -> bool:
    proof_value = value.get(
        "proof", value.get("p335_authenticated_attended_resident")
    )
    try:
        proof = typed_evidence.validate_p335_attended_resident_proof(proof_value)
    except typed_evidence.EvidenceError:
        return False
    return (
        all(
            value.get(key) is True
            for key in (
                "hmac_authenticated",
                "pid1_authenticated_framed_exec_proof",
                "busybox_ash_command_proof",
                "framed_session_closed",
                "logical_resident_proof",
                "same_tty_fd",
                "fixed_p330_commands",
            )
        )
        and value.get("physical_reopen_count") == 1
        and value.get("interactive_pty_proof") is False
        and value.get("caller_selected_command") is False
        and value.get("arbitrary_file_transfer") is False
        and value.get("persistent_state") is False
        and value.get("session_count") == p335_retained_observer.MAX_SESSIONS
        and value.get("successful_sessions") == p335_retained_observer.MAX_SESSIONS
        and value.get("session_cap") == p335_retained_observer.MAX_SESSIONS
        and value.get("reconnect_count") == p335_retained_observer.MAX_RECONNECTS
        and value.get("reconnect_cap") == p335_retained_observer.MAX_RECONNECTS
        and value.get("commands_per_session")
        == len(p335_retained_runtime.DEFAULT_COMMANDS)
        and value.get("command_count")
        == p335_retained_observer.MAX_SESSIONS
        * len(p335_retained_runtime.DEFAULT_COMMANDS)
        and value.get("max_commands") == p335_retained_runtime.MAX_COMMANDS
        and proof.get("retained_listener_proof") is True
        and proof.get("per_boot_identity_proof") is True
        and proof.get("same_boot_id") is True
        and proof.get("descriptor_reopened") is True
        and proof.get("listener_replays_commands") is False
    )


def _p331_nonce_from_raw_session(payload: bytes, index: int) -> str:
    """Decode one retained RX slice and return its exact challenge digest."""

    banner = p331_resident_runtime.DEVICE_BANNER
    if not payload.startswith(banner):
        raise p331_resident_observer.AuthObserverError(
            f"P331 resident session {index} banner differs"
        )
    cursor = len(banner)
    challenge: bytes | None = None
    while cursor < len(payload):
        remaining = len(payload) - cursor
        if remaining < p331_resident_observer.HEADER.size:
            raise p331_resident_observer.AuthObserverError(
                f"P331 resident session {index} frame is truncated"
            )
        header = payload[cursor : cursor + p331_resident_observer.HEADER.size]
        try:
            _magic, _version, _kind, size, _sequence, _crc = (
                p331_resident_observer.HEADER.unpack(header)
            )
        except (TypeError, ValueError) as exc:
            raise p331_resident_observer.AuthObserverError(
                f"P331 resident session {index} frame header differs"
            ) from exc
        end = cursor + p331_resident_observer.HEADER.size + size
        if end > len(payload):
            raise p331_resident_observer.AuthObserverError(
                f"P331 resident session {index} frame payload is truncated"
            )
        try:
            frame = p331_resident_observer.decode_frame(payload[cursor:end])
        except p331_resident_observer.AuthObserverError:
            raise
        except (TypeError, ValueError) as exc:
            raise p331_resident_observer.AuthObserverError(
                f"P331 resident session {index} frame differs"
            ) from exc
        if frame.frame_type == p331_resident_runtime.FRAME_CHALLENGE:
            if (
                challenge is not None
                or frame.sequence != 0
                or len(frame.payload) != p331_resident_runtime.NONCE_SIZE
            ):
                raise p331_resident_observer.AuthObserverError(
                    f"P331 resident session {index} challenge differs"
                )
            challenge = frame.payload
        cursor = end
    if challenge is None:
        raise p331_resident_observer.AuthObserverError(
            f"P331 resident session {index} challenge is absent"
        )
    return hashlib.sha256(challenge).hexdigest()


def _p331_validate_raw_session_bindings(
    prepared: PreparedRun,
    value: dict[str, Any],
    proof: dict[str, Any],
) -> None:
    """Bind both compact sessions back to retained RX and bounded TX bytes."""

    raw = value["raw"]
    raw_path = Path(raw["path"])
    raw_payload, _identity = core._stable_read(
        raw_path, "P331 resident raw RX", P328_MAX_RAW_BYTES
    )
    if (
        len(raw_payload) != raw["size"]
        or hashlib.sha256(raw_payload).hexdigest() != raw["sha256"]
    ):
        raise p331_resident_observer.AuthObserverError(
            "P331 resident raw RX changed during reopen"
        )
    sessions = proof["sessions"]
    tx_hex = value["session_tx_hex"]
    if not isinstance(tx_hex, list) or len(tx_hex) != len(sessions):
        raise p331_resident_observer.AuthObserverError(
            "P331 resident TX segment count differs"
        )
    rx_cursor = 0
    tx_segments: list[bytes] = []
    for index, (row, encoded_tx) in enumerate(zip(sessions, tx_hex)):
        rx_identity = _p328_receipt_identity(
            row["rx"], f"P331 resident session {index} RX"
        )
        end = rx_cursor + rx_identity["size"]
        if end > len(raw_payload):
            raise p331_resident_observer.AuthObserverError(
                f"P331 resident session {index} RX slice exceeds raw evidence"
            )
        rx_segment = raw_payload[rx_cursor:end]
        if _p327_identity(rx_segment) != rx_identity:
            raise p331_resident_observer.AuthObserverError(
                f"P331 resident session {index} RX identity differs"
            )
        if (
            _p331_nonce_from_raw_session(rx_segment, index)
            != row["challenge_nonce_sha256"]
        ):
            raise p331_resident_observer.AuthObserverError(
                f"P331 resident session {index} nonce digest differs"
            )
        if (
            not isinstance(encoded_tx, str)
            or len(encoded_tx) > P328_MAX_RAW_BYTES * 2
            or re.fullmatch(r"(?:[0-9a-f]{2})*", encoded_tx) is None
        ):
            raise p331_resident_observer.AuthObserverError(
                f"P331 resident session {index} TX encoding differs"
            )
        segment = bytes.fromhex(encoded_tx)
        if _p327_identity(segment) != row["tx"]:
            raise p331_resident_observer.AuthObserverError(
                f"P331 resident session {index} TX identity differs"
            )
        tx_segments.append(segment)
        rx_cursor = end
    if (
        rx_cursor != len(raw_payload)
        or _p327_identity(b"".join(tx_segments)) != value["tx"]
    ):
        raise p331_resident_observer.AuthObserverError(
            "P331 resident ordered raw accounting differs"
        )


def _p331_validate_receipt_unchecked(
    prepared: PreparedRun,
    path: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    """Reopen the bounded two-session receipt without reopening its key."""
    value = _read_json(path, "P331 bounded resident observer receipt")
    expected_keys = set(
        """
        schema contract_id target binding spec_sha256 baseline_sha256
        download_departure_sha256 download_endpoint_absent topology_sha256
        endpoint_identity_sha256 guard_sha256 raw banner_hex tx session_tx_hex
        rx trailing_rx
        trailing_bytes_seen banner_seen ready_seen done_seen proof lane
        expected_size exact extra_byte classification accepted bounded elapsed_sec
        diagnostics rng_eagain_retries partial_sessions auth_algorithm
        auth_tag_size auth_key_sha256 hmac_authenticated
        pid1_authenticated_framed_exec_proof busybox_ash_command_proof
        framed_session_closed resident_loop_proof fixed_heartbeat_status
        session_count successful_sessions session_cap reconnect_count
        reconnect_cap commands_per_session command_count max_commands
        interactive_pty_proof caller_selected_command arbitrary_file_transfer
        persistent_state
        """.split()
    )
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise p331_resident_observer.AuthObserverError(
            "P331 bounded resident receipt shape differs"
        )
    _p328_receipt_secret_free(value)
    classification = value["classification"]
    accepted = value["accepted"]
    scalar_bools = (
        "download_endpoint_absent",
        "banner_seen",
        "ready_seen",
        "done_seen",
        "hmac_authenticated",
        "pid1_authenticated_framed_exec_proof",
        "busybox_ash_command_proof",
        "framed_session_closed",
        "resident_loop_proof",
        "fixed_heartbeat_status",
        "interactive_pty_proof",
        "caller_selected_command",
        "arbitrary_file_transfer",
        "persistent_state",
        "exact",
        "extra_byte",
        "accepted",
        "bounded",
    )
    if (
        value["schema"] != P331_OBSERVER_RECEIPT_SCHEMA
        or value["contract_id"] != p331_resident_observer.CONTRACT_ID
        or value["target"] != p331_resident_runtime.TARGET
        or value["banner_hex"] != p331_resident_runtime.DEVICE_BANNER.hex()
        or value["expected_size"]
        != len(p331_resident_runtime.DEVICE_BANNER)
        * p331_resident_runtime.MAX_SESSIONS
        or value["auth_algorithm"] != "hmac-sha256"
        or value["auth_tag_size"] != p331_resident_runtime.AUTH_TAG_SIZE
        or any(type(value[key]) is not bool for key in scalar_bools)
        or not isinstance(classification, str)
        or classification not in P331_CLASSIFICATIONS
        or value["exact"] is not accepted
        or accepted is not (classification == "accepted")
        or value["bounded"] is not True
        or type(value["trailing_bytes_seen"]) is not int
        or value["trailing_bytes_seen"] not in {0, 1}
        or value["extra_byte"] is not (value["trailing_bytes_seen"] > 0)
        or isinstance(value["elapsed_sec"], bool)
        or not isinstance(value["elapsed_sec"], (int, float))
        or not math.isfinite(float(value["elapsed_sec"]))
        or not 0 <= value["elapsed_sec"] <= 600
        or value["interactive_pty_proof"] is not False
        or value["caller_selected_command"] is not False
        or value["arbitrary_file_transfer"] is not False
        or value["persistent_state"] is not False
        or any(
            type(value[key]) is not int
            for key in (
                "session_cap",
                "reconnect_cap",
                "commands_per_session",
                "max_commands",
            )
        )
        or value["session_cap"] != p331_resident_runtime.MAX_SESSIONS
        or value["reconnect_cap"] != p331_resident_runtime.MAX_RECONNECTS
        or value["commands_per_session"] != 1
        or value["max_commands"] != p331_resident_runtime.MAX_COMMANDS
    ):
        raise p331_resident_observer.AuthObserverError(
            "P331 bounded resident receipt semantics differ"
        )
    lane, topology, endpoint = _p328_validate_common_receipt(
        prepared, value, spec
    )
    bound = _p328_bound_auth_key_identity(prepared)
    if value["auth_key_sha256"] != bound["sha256"]:
        raise p331_resident_observer.AuthObserverError(
            "P331 resident auth-key identity differs"
        )

    session_count = value["session_count"]
    successful = value["successful_sessions"]
    reconnect_count = value["reconnect_count"]
    command_count = value["command_count"]
    diagnostics = value["diagnostics"]
    retries = value["rng_eagain_retries"]
    partial = value["partial_sessions"]
    if (
        type(session_count) is not int
        or not 0 <= session_count <= p331_resident_runtime.MAX_SESSIONS
        or type(successful) is not int
        or not 0 <= successful <= session_count
        or type(reconnect_count) is not int
        or not 0 <= reconnect_count <= p331_resident_runtime.MAX_RECONNECTS
        or type(command_count) is not int
        or command_count != session_count
        or not isinstance(diagnostics, list)
        or not isinstance(retries, list)
        or not isinstance(partial, list)
        or not len(diagnostics) == len(retries) == len(partial) == session_count
    ):
        raise p331_resident_observer.AuthObserverError(
            "P331 resident session accounting differs"
        )
    for index, (session_diagnostics, session_retries, session_partial) in enumerate(
        zip(diagnostics, retries, partial)
    ):
        if (
            not isinstance(session_diagnostics, list)
            or len(session_diagnostics) > 2
            or session_retries is not None
            and (
                type(session_retries) is not int
                or not 0
                <= session_retries
                <= p331_resident_runtime.RNG_EAGAIN_RETRY_LIMIT
            )
            or not isinstance(session_partial, dict)
            or set(session_partial)
            != {
                "session_index",
                "current_stage",
                "failure_stage",
                "failure_code",
                "exception_type",
                "exception_sha256",
            }
            or type(session_partial["session_index"]) is not int
            or session_partial["session_index"] != index
        ):
            raise p331_resident_observer.AuthObserverError(
                "P331 resident partial-session receipt differs"
            )
        for diagnostic_index, diagnostic in enumerate(session_diagnostics):
            expected_stage = (
                p331_resident_runtime.DIAGNOSTIC_STAGE_OPEN_PARSED
                if diagnostic_index == 0
                else p331_resident_runtime.DIAGNOSTIC_STAGE_RNG
            )
            if (
                not isinstance(diagnostic, dict)
                or set(diagnostic) != {"stage", "code"}
                or type(diagnostic["stage"]) is not int
                or diagnostic["stage"] != expected_stage
                or type(diagnostic["code"]) is not int
                or diagnostic_index == 0
                and diagnostic["code"] != 0
            ):
                raise p331_resident_observer.AuthObserverError(
                    "P331 resident diagnostic receipt differs"
                )
        rng_code = (
            session_diagnostics[1]["code"]
            if len(session_diagnostics) == 2
            else None
        )
        expected_retries = (
            rng_code if isinstance(rng_code, int) and rng_code >= 0 else None
        )
        if (
            session_retries != expected_retries
            or isinstance(rng_code, int)
            and not -4095
            <= rng_code
            <= p331_resident_runtime.RNG_EAGAIN_RETRY_LIMIT
        ):
            raise p331_resident_observer.AuthObserverError(
                "P331 resident RNG diagnostic differs"
            )

    proof = value["proof"]
    validated_proof = None
    try:
        validated_proof = typed_evidence.validate_p331_resident_proof(proof)
    except typed_evidence.EvidenceError:
        if accepted:
            raise p331_resident_observer.AuthObserverError(
                "P331 accepted receipt lacks resident proof"
            )
    proof_ok = validated_proof is not None
    if (
        proof_ok
        and sum(row["tx"]["size"] for row in validated_proof["sessions"])
        != value["tx"]["size"]
        or proof_ok
        and sum(row["rx"]["size"] for row in validated_proof["sessions"])
        != value["rx"]["size"]
        or accepted
        and (
            not proof_ok
            or not _p331_proof_ok(value)
            or value["download_endpoint_absent"] is not True
            or not all(value[key] for key in ("banner_seen", "ready_seen", "done_seen"))
            or any(len(row) != 2 for row in diagnostics)
            or any(row["current_stage"] != "complete" for row in partial)
            or any(
                row[key] is not None
                for row in partial
                for key in (
                    "failure_stage",
                    "failure_code",
                    "exception_type",
                    "exception_sha256",
                )
            )
        )
    ):
        raise p331_resident_observer.AuthObserverError(
            "P331 resident proof accounting differs"
        )
    if proof_ok:
        assert validated_proof is not None
        _p331_validate_raw_session_bindings(prepared, value, validated_proof)
    return {
        "classification": classification,
        "accepted": accepted,
        "receipt_sha256": _receipt(
            path, "P331 bounded resident observer receipt"
        )["sha256"],
        "valid_receipt": True,
        "download_endpoint_absent": value["download_endpoint_absent"],
        "endpoint_identity_sha256": endpoint,
        "topology_sha256": value["topology_sha256"],
        "bounded": True,
        "source_topology_sha256": hashlib.sha256(
            p324_typec_lane.SOURCE_TOPOLOGY.removeprefix("usb:").encode()
        ).hexdigest(),
        "candidate_topology_sha256": topology,
        "both_topologies_inventory_complete": lane[
            "both_topologies_inventory_complete"
        ],
        "accepted_inventory_exact": lane["accepted_inventory_exact"],
        "same_run_typec_partner_continuity": lane[
            "same_run_typec_partner_continuity"
        ],
        "accepted_for_p324": lane["accepted_for_p324"],
        **_p331_proof_state(value),
        "preauth_diagnostics": diagnostics,
        "rng_eagain_retries": retries,
        "partial_sessions": partial,
        "p331_authenticated_resident": proof,
    }


def _p331_validate_receipt(
    prepared: PreparedRun,
    path: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    """Normalize malformed nested values into the bounded parser failure."""

    try:
        return _p331_validate_receipt_unchecked(prepared, path, spec)
    except (
        p331_resident_observer.AuthObserverError,
        p328_auth_observer.AuthObserverError,
        core.F1V2Error,
    ):
        raise
    except (AttributeError, IndexError, KeyError, OverflowError, TypeError, ValueError) as exc:
        raise p331_resident_observer.AuthObserverError(
            "P331 bounded resident receipt is malformed"
        ) from exc


def _p332_nonce_from_raw_session(
    payload: bytes,
    index: int,
    *,
    observer_module: Any = p332_logical_resident_observer,
    runtime_module: Any = p332_logical_resident_runtime,
    label: str = "P332",
) -> str:
    banner = runtime_module.DEVICE_BANNER
    if not payload.startswith(banner):
        raise observer_module.AuthObserverError(
            f"{label} logical session {index} banner differs"
        )
    cursor = len(banner)
    challenge: bytes | None = None
    while cursor < len(payload):
        if len(payload) - cursor < observer_module.HEADER.size:
            raise observer_module.AuthObserverError(
                f"{label} logical session {index} frame is truncated"
            )
        header = payload[cursor : cursor + observer_module.HEADER.size]
        _magic, _version, _kind, size, _sequence, _crc = (
            observer_module.HEADER.unpack(header)
        )
        end = cursor + observer_module.HEADER.size + size
        if end > len(payload):
            raise observer_module.AuthObserverError(
                f"{label} logical session {index} payload is truncated"
            )
        frame = observer_module.decode_frame(payload[cursor:end])
        if frame.frame_type == runtime_module.FRAME_CHALLENGE:
            if (
                challenge is not None
                or frame.sequence != 0
                or len(frame.payload) != runtime_module.NONCE_SIZE
            ):
                raise observer_module.AuthObserverError(
                    f"{label} logical session {index} challenge differs"
                )
            challenge = frame.payload
        cursor = end
    if challenge is None:
        raise observer_module.AuthObserverError(
            f"{label} logical session {index} challenge is absent"
        )
    return hashlib.sha256(challenge).hexdigest()


def _p332_validate_raw_session_bindings(
    value: dict[str, Any],
    proof: dict[str, Any],
    *,
    observer_module: Any = p332_logical_resident_observer,
    runtime_module: Any = p332_logical_resident_runtime,
    label: str = "P332",
) -> None:
    raw = value["raw"]
    raw_payload, _identity = core._stable_read(
        Path(raw["path"]), f"{label} logical resident raw RX", P328_MAX_RAW_BYTES
    )
    if _p327_identity(raw_payload) != {
        "size": raw["size"],
        "sha256": raw["sha256"],
    }:
        raise observer_module.AuthObserverError(
            f"{label} logical resident raw RX changed during reopen"
        )
    tx_hex = value["session_tx_hex"]
    sessions = proof["sessions"]
    if not isinstance(tx_hex, list) or len(tx_hex) != len(sessions):
        raise observer_module.AuthObserverError(
            f"{label} logical resident TX segment count differs"
        )
    rx_cursor = 0
    tx_segments: list[bytes] = []
    for index, (row, encoded_tx) in enumerate(zip(sessions, tx_hex)):
        rx_identity = _p328_receipt_identity(
            row["rx"], f"{label} logical session {index} RX"
        )
        end = rx_cursor + rx_identity["size"]
        rx_segment = raw_payload[rx_cursor:end]
        if end > len(raw_payload) or _p327_identity(rx_segment) != rx_identity:
            raise observer_module.AuthObserverError(
                f"{label} logical session {index} RX identity differs"
            )
        if _p332_nonce_from_raw_session(
            rx_segment,
            index,
            observer_module=observer_module,
            runtime_module=runtime_module,
            label=label,
        ) != row[
            "challenge_nonce_sha256"
        ]:
            raise observer_module.AuthObserverError(
                f"{label} logical session {index} nonce digest differs"
            )
        if (
            not isinstance(encoded_tx, str)
            or len(encoded_tx) > P328_MAX_RAW_BYTES * 2
            or re.fullmatch(r"(?:[0-9a-f]{2})*", encoded_tx) is None
        ):
            raise observer_module.AuthObserverError(
                f"{label} logical session {index} TX encoding differs"
            )
        segment = bytes.fromhex(encoded_tx)
        if _p327_identity(segment) != row["tx"]:
            raise observer_module.AuthObserverError(
                f"{label} logical session {index} TX identity differs"
            )
        tx_segments.append(segment)
        rx_cursor = end
    if (
        rx_cursor != len(raw_payload)
        or _p327_identity(b"".join(tx_segments)) != value["tx"]
        or _p327_identity(raw_payload) != value["rx"]
    ):
        raise observer_module.AuthObserverError(
            f"{label} logical resident ordered raw accounting differs"
        )


def _p332_validate_receipt(
    prepared: PreparedRun,
    path: Path,
    spec: dict[str, Any],
    *,
    observer_module: Any = p332_logical_resident_observer,
    runtime_module: Any = p332_logical_resident_runtime,
    receipt_schema: str = P332_OBSERVER_RECEIPT_SCHEMA,
    classifications: set[str] = P332_CLASSIFICATIONS,
    proof_validator: Callable[[Any], dict[str, Any]] = typed_evidence.validate_p332_logical_resident_proof,
    proof_checker: Callable[[Mapping[str, Any]], bool] = _p332_proof_ok,
    expected_physical_reopens: int = 0,
    expected_reconnects: int = 0,
    expected_session_count: int | None = None,
    proof_key: str = "p332_authenticated_logical_resident",
    label: str = "P332",
) -> dict[str, Any]:
    session_count = (
        runtime_module.MAX_SESSIONS
        if expected_session_count is None
        else expected_session_count
    )
    value = _read_json(path, f"{label} logical resident observer receipt")
    expected_keys = set(
        """
        schema contract_id target binding spec_sha256 baseline_sha256
        download_departure_sha256 download_endpoint_absent topology_sha256
        endpoint_identity_sha256 guard_sha256 raw banner_hex tx session_tx_hex
        rx trailing_rx trailing_bytes_seen banner_seen ready_seen done_seen proof
        lane expected_size exact extra_byte classification accepted bounded elapsed_sec
        diagnostics rng_eagain_retries partial_sessions auth_algorithm auth_tag_size
        auth_key_sha256 hmac_authenticated pid1_authenticated_framed_exec_proof
        busybox_ash_command_proof framed_session_closed logical_resident_proof
        same_tty_fd physical_reopen_count fixed_p330_commands session_count
        successful_sessions session_cap reconnect_count reconnect_cap
        commands_per_session command_count max_commands interactive_pty_proof
        caller_selected_command arbitrary_file_transfer persistent_state
        """.split()
    )
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise observer_module.AuthObserverError(
            f"{label} logical resident receipt shape differs"
        )
    _p328_receipt_secret_free(value)
    classification = value["classification"]
    accepted = value["accepted"]
    scalar_bools = (
        "download_endpoint_absent",
        "banner_seen",
        "ready_seen",
        "done_seen",
        "hmac_authenticated",
        "pid1_authenticated_framed_exec_proof",
        "busybox_ash_command_proof",
        "framed_session_closed",
        "logical_resident_proof",
        "same_tty_fd",
        "fixed_p330_commands",
        "interactive_pty_proof",
        "caller_selected_command",
        "arbitrary_file_transfer",
        "persistent_state",
        "exact",
        "extra_byte",
        "accepted",
        "bounded",
    )
    if (
        value["schema"] != receipt_schema
        or value["contract_id"] != observer_module.CONTRACT_ID
        or value["target"] != runtime_module.TARGET
        or value["banner_hex"] != runtime_module.DEVICE_BANNER.hex()
        or value["expected_size"]
        != len(runtime_module.DEVICE_BANNER)
        * session_count
        or value["auth_algorithm"] != "hmac-sha256"
        or value["auth_tag_size"] != runtime_module.AUTH_TAG_SIZE
        or any(type(value[key]) is not bool for key in scalar_bools)
        or classification not in classifications
        or value["exact"] is not accepted
        or accepted is not (classification == "accepted")
        or value["bounded"] is not True
        or type(value["physical_reopen_count"]) is not int
        or value["physical_reopen_count"] != expected_physical_reopens
        or value["interactive_pty_proof"] is not False
        or value["caller_selected_command"] is not False
        or value["arbitrary_file_transfer"] is not False
        or value["persistent_state"] is not False
    ):
        raise observer_module.AuthObserverError(
            f"{label} logical resident receipt semantics differ"
        )
    lane, topology, endpoint = _p328_validate_common_receipt(prepared, value, spec)
    bound = _p328_bound_auth_key_identity(prepared)
    if value["auth_key_sha256"] != bound["sha256"]:
        raise observer_module.AuthObserverError(
            f"{label} logical resident auth-key identity differs"
        )
    proof: dict[str, Any] | None = None
    try:
        proof = proof_validator(value["proof"])
    except typed_evidence.EvidenceError:
        if accepted:
            raise observer_module.AuthObserverError(
                f"{label} accepted receipt lacks logical resident proof"
            )
    if accepted and (
        proof is None
        or not proof_checker(value)
        or value["download_endpoint_absent"] is not True
        or not all(value[key] for key in ("banner_seen", "ready_seen", "done_seen"))
        or value["session_count"] != session_count
        or value["successful_sessions"] != session_count
        or value["reconnect_count"] != expected_reconnects
        or value["reconnect_cap"] != expected_reconnects
    ):
        raise observer_module.AuthObserverError(
            f"{label} logical resident proof accounting differs"
        )
    if proof is not None:
        _p332_validate_raw_session_bindings(
            value,
            proof,
            observer_module=observer_module,
            runtime_module=runtime_module,
            label=label,
        )
    return {
        "classification": classification,
        "accepted": accepted,
        "receipt_sha256": _receipt(
            path, f"{label} logical resident observer receipt"
        )["sha256"],
        "valid_receipt": True,
        "download_endpoint_absent": value["download_endpoint_absent"],
        "endpoint_identity_sha256": endpoint,
        "topology_sha256": value["topology_sha256"],
        "bounded": True,
        "source_topology_sha256": hashlib.sha256(
            p324_typec_lane.SOURCE_TOPOLOGY.removeprefix("usb:").encode()
        ).hexdigest(),
        "candidate_topology_sha256": topology,
        "both_topologies_inventory_complete": lane[
            "both_topologies_inventory_complete"
        ],
        "accepted_inventory_exact": lane["accepted_inventory_exact"],
        "same_run_typec_partner_continuity": lane[
            "same_run_typec_partner_continuity"
        ],
        "accepted_for_p324": lane["accepted_for_p324"],
        **_p332_proof_state(value),
        "preauth_diagnostics": value["diagnostics"],
        "rng_eagain_retries": value["rng_eagain_retries"],
        "partial_sessions": value["partial_sessions"],
        proof_key: value["proof"],
    }


def _p333_validate_receipt(
    prepared: PreparedRun,
    path: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    return _p332_validate_receipt(
        prepared,
        path,
        spec,
        observer_module=p333_open_entry_observer,
        runtime_module=p333_open_entry_runtime,
        receipt_schema=P333_OBSERVER_RECEIPT_SCHEMA,
        classifications=P333_CLASSIFICATIONS,
        proof_validator=typed_evidence.validate_p333_logical_resident_proof,
        proof_key="p333_authenticated_logical_resident",
        label="P333",
    )


def _p334_validate_receipt(
    prepared: PreparedRun,
    path: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    value = _p332_validate_receipt(
        prepared,
        path,
        spec,
        observer_module=p334_first_read_observer,
        runtime_module=p334_first_read_runtime,
        receipt_schema=P334_OBSERVER_RECEIPT_SCHEMA,
        classifications=P334_CLASSIFICATIONS,
        proof_validator=typed_evidence.validate_p334_logical_resident_proof,
        proof_key="p334_authenticated_logical_resident",
        label="P334",
    )
    value.update(
        {
            "first_console_return_checkpoint_only": True,
            "first_read_attribution_requires_stage0_without_stage1": True,
        }
    )
    return value


def _p335_validate_receipt(
    prepared: PreparedRun,
    path: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    return _p332_validate_receipt(
        prepared,
        path,
        spec,
        observer_module=p335_retained_observer,
        runtime_module=p335_retained_runtime,
        receipt_schema=P335_OBSERVER_RECEIPT_SCHEMA,
        classifications=P335_CLASSIFICATIONS,
        proof_validator=typed_evidence.validate_p335_attended_resident_proof,
        proof_checker=_p335_proof_ok,
        expected_physical_reopens=1,
        expected_reconnects=1,
        expected_session_count=p335_retained_observer.MAX_SESSIONS,
        proof_key="p335_authenticated_attended_resident",
        label="P335",
    )


def _reopen_candidate_observation(prepared: PreparedRun) -> dict[str, Any]:
    def unavailable(classification: str) -> dict[str, Any]:
        result = {
            "classification": classification,
            "accepted": False,
            "receipt_sha256": None,
            "valid_receipt": False,
            "download_endpoint_absent": False,
            "endpoint_identity_sha256": None,
            "topology_sha256": None,
            "bounded": False,
        }
        if _p324_lane_bundle(prepared.bundle):
            result.update(
                {
                    "source_topology_sha256": None,
                    "candidate_topology_sha256": None,
                    "both_topologies_inventory_complete": False,
                    "accepted_inventory_exact": False,
                    "same_run_typec_partner_continuity": False,
                    "accepted_for_p324": False,
                }
            )
        if _p335_bundle(prepared.bundle):
            result.update(
                {
                    **{key: False for key in P332_PROOF_FIELDS[:12]},
                    "physical_reopen_count": 0,
                    "session_count": 0,
                    "successful_sessions": 0,
                    "session_cap": p335_retained_observer.MAX_SESSIONS,
                    "reconnect_count": 0,
                    "reconnect_cap": p335_retained_observer.MAX_RECONNECTS,
                    "commands_per_session": len(
                        p335_retained_runtime.DEFAULT_COMMANDS
                    ),
                    "command_count": 0,
                    "max_commands": p335_retained_runtime.MAX_COMMANDS,
                    "auth_key_sha256": None,
                    "preauth_diagnostics": [],
                    "rng_eagain_retries": [],
                    "partial_sessions": [],
                    "p335_authenticated_attended_resident": None,
                    "caller_selected_command": False,
                }
            )
        if _p327_bundle(prepared.bundle):
            result.update(
                {
                    "pid1_framed_exec_proof": False,
                    "busybox_ash_command_proof": False,
                    "framed_session_closed": False,
                    "interactive_pty_proof": False,
                    "caller_selected_command": False,
                }
            )
        if _p328_bundle(prepared.bundle):
            result.update(
                {
                    "hmac_authenticated": False,
                    "pid1_authenticated_framed_exec_proof": False,
                    "busybox_ash_command_proof": False,
                    "framed_session_closed": False,
                    "interactive_pty_proof": False,
                    "caller_selected_command": True,
                    "command_count": 3,
                    "max_commands": p328_auth_runtime.MAX_COMMANDS,
                    "auth_key_sha256": None,
                    "challenge_nonce_sha256": None,
                }
            )
        if _p330_bundle(prepared.bundle):
            result.update(
                {
                    "preauth_diagnostics": [],
                    "rng_eagain_retries": None,
                    "partial_exchange": {
                        "current_stage": None,
                        "failure_stage": None,
                        "failure_code": None,
                        "exception_type": None,
                        "exception_sha256": None,
                    },
                }
            )
        if _p331_bundle(prepared.bundle):
            result.update(
                {
                    **{key: False for key in P331_PROOF_FIELDS[:10]},
                    "session_count": 0,
                    "successful_sessions": 0,
                    "session_cap": p331_resident_runtime.MAX_SESSIONS,
                    "reconnect_count": 0,
                    "reconnect_cap": p331_resident_runtime.MAX_RECONNECTS,
                    "commands_per_session": 1,
                    "command_count": 0,
                    "max_commands": p331_resident_runtime.MAX_COMMANDS,
                    "auth_key_sha256": None,
                    "preauth_diagnostics": [],
                    "rng_eagain_retries": [],
                    "partial_sessions": [],
                    "p331_authenticated_resident": None,
                }
            )
        if _p334_bundle(prepared.bundle):
            result.update(
                {
                    **{key: False for key in P332_PROOF_FIELDS[:12]},
                    "physical_reopen_count": 0,
                    "session_count": 0,
                    "successful_sessions": 0,
                    "session_cap": p334_first_read_runtime.MAX_SESSIONS,
                    "reconnect_count": 0,
                    "reconnect_cap": 0,
                    "commands_per_session": len(
                        p334_first_read_runtime.DEFAULT_COMMANDS
                    ),
                    "command_count": 0,
                    "max_commands": p334_first_read_runtime.MAX_COMMANDS,
                    "auth_key_sha256": None,
                    "preauth_diagnostics": [],
                    "rng_eagain_retries": [],
                    "partial_sessions": [],
                    "p334_authenticated_logical_resident": None,
                    "first_console_return_checkpoint_only": True,
                    "first_read_attribution_requires_stage0_without_stage1": True,
                }
            )
        if _p333_bundle(prepared.bundle):
            result.update(
                {
                    **{key: False for key in P332_PROOF_FIELDS[:12]},
                    "physical_reopen_count": 0,
                    "session_count": 0,
                    "successful_sessions": 0,
                    "session_cap": p333_open_entry_runtime.MAX_SESSIONS,
                    "reconnect_count": 0,
                    "reconnect_cap": 0,
                    "commands_per_session": len(
                        p333_open_entry_runtime.DEFAULT_COMMANDS
                    ),
                    "command_count": 0,
                    "max_commands": p333_open_entry_runtime.MAX_COMMANDS,
                    "auth_key_sha256": None,
                    "preauth_diagnostics": [],
                    "rng_eagain_retries": [],
                    "partial_sessions": [],
                    "p333_authenticated_logical_resident": None,
                }
            )
        if _p332_bundle(prepared.bundle):
            result.update(
                {
                    **{key: False for key in P332_PROOF_FIELDS[:12]},
                    "physical_reopen_count": 0,
                    "session_count": 0,
                    "successful_sessions": 0,
                    "session_cap": p332_logical_resident_runtime.MAX_SESSIONS,
                    "reconnect_count": 0,
                    "reconnect_cap": 0,
                    "commands_per_session": len(
                        p332_logical_resident_runtime.DEFAULT_COMMANDS
                    ),
                    "command_count": 0,
                    "max_commands": p332_logical_resident_runtime.MAX_COMMANDS,
                    "auth_key_sha256": None,
                    "preauth_diagnostics": [],
                    "rng_eagain_retries": [],
                    "partial_sessions": [],
                    "p332_authenticated_logical_resident": None,
                }
            )
        return result

    spec = prepared.bundle.manifest["observation"].get("candidate_observer")
    if spec is None:
        return unavailable("not-required")
    path = prepared.run_dir / "candidate-observer.json"
    if not path.is_file() or path.is_symlink():
        return unavailable("interrupted-before-receipt")
    try:
        if _p335_bundle(prepared.bundle):
            value = _p335_validate_receipt(prepared, path, spec)
            receipt_sha256 = value["receipt_sha256"]
        elif _p334_bundle(prepared.bundle):
            value = _p334_validate_receipt(prepared, path, spec)
            receipt_sha256 = value["receipt_sha256"]
        elif _p333_bundle(prepared.bundle):
            value = _p333_validate_receipt(prepared, path, spec)
            receipt_sha256 = value["receipt_sha256"]
        elif _p332_bundle(prepared.bundle):
            value = _p332_validate_receipt(prepared, path, spec)
            receipt_sha256 = value["receipt_sha256"]
        elif _p331_bundle(prepared.bundle):
            value = _p331_validate_receipt(
                prepared,
                path,
                spec,
            )
            receipt_sha256 = value["receipt_sha256"]
        elif _p330_bundle(prepared.bundle):
            value = _p330_validate_receipt(
                prepared,
                path,
                spec,
            )
            receipt_sha256 = value["receipt_sha256"]
        elif _p329_bundle(prepared.bundle):
            value = _p329_validate_receipt(
                prepared,
                path,
                spec,
            )
            receipt_sha256 = value["receipt_sha256"]
        elif _p328_bundle(prepared.bundle):
            value = _p328_validate_receipt(
                prepared,
                path,
                spec,
            )
            receipt_sha256 = value["receipt_sha256"]
        elif _p327_bundle(prepared.bundle):
            value = _p327_validate_receipt(
                prepared,
                path,
                spec,
            )
            receipt_sha256 = value["receipt_sha256"]
        elif _p326_bundle(prepared.bundle):
            lane_value, lane_receipt = _p324_typec_lane_value(prepared)
            value = p326_console_observer.validate_receipt(
                prepared.run_dir,
                spec=spec,
                binding=_candidate_observer_binding(prepared),
                source_topology=prepared.private_target["topology"],
                lane_binding=lane_value,
                lane_binding_receipt=lane_receipt,
            )
            receipt_sha256 = value["lane_receipt_sha256"]
        elif _p325_bundle(prepared.bundle):
            lane_value, lane_receipt = _p324_typec_lane_value(prepared)
            value = p325_guard_adapter.validate_receipt(
                prepared.run_dir,
                spec=spec,
                binding=_candidate_observer_binding(prepared),
                source_topology=prepared.private_target["topology"],
                lane_binding=lane_value,
                lane_binding_receipt=lane_receipt,
            )
            receipt_sha256 = value["lane_receipt_sha256"]
        elif _p324_bundle(prepared.bundle):
            lane_value, lane_receipt = _p324_typec_lane_value(prepared)
            value = p324_cdc_observer.validate_receipt(
                prepared.run_dir,
                spec=spec,
                binding=_candidate_observer_binding(prepared),
                source_topology=prepared.private_target["topology"],
                lane_binding=lane_value,
                lane_binding_receipt=lane_receipt,
            )
            receipt_sha256 = value["lane_receipt_sha256"]
        else:
            value = cdc_acm_observer.validate_receipt(
                path,
                spec=spec,
                binding=_candidate_observer_binding(prepared),
                topology=prepared.private_target["topology"],
            )
            receipt_sha256 = _receipt(
                path, "candidate observer receipt"
            )["sha256"]
    except (
        cdc_acm_observer.ObserverError,
        p324_cdc_observer.P324ObserverError,
        p325_guard_adapter.P325ObserverError,
        p326_console_observer.P326ObserverError,
        p327_framed_observer.FramedObserverError,
        p328_auth_observer.AuthObserverError,
        p329_auth_observer.AuthObserverError,
        p330_auth_observer.AuthObserverError,
        p331_resident_observer.AuthObserverError,
        p332_logical_resident_observer.AuthObserverError,
        p333_open_entry_observer.AuthObserverError,
        p334_first_read_observer.AuthObserverError,
        p335_retained_observer.AuthObserverError,
        F1LiveError,
        core.F1V2Error,
    ):
        return unavailable("interrupted-before-receipt")
    result = {
        "classification": value["classification"],
        "accepted": value["accepted"],
        "receipt_sha256": receipt_sha256,
        "valid_receipt": True,
        "download_endpoint_absent": value["download_endpoint_absent"],
        "endpoint_identity_sha256": value["endpoint_identity_sha256"],
        "topology_sha256": value["topology_sha256"],
        "bounded": value["bounded"],
    }
    if _p324_lane_bundle(prepared.bundle):
        result.update(
            {
                name: value[name]
                for name in (
                    "source_topology_sha256",
                    "candidate_topology_sha256",
                    "both_topologies_inventory_complete",
                    "accepted_inventory_exact",
                    "same_run_typec_partner_continuity",
                    "accepted_for_p324",
                )
            }
        )
    if _p335_bundle(prepared.bundle):
        result.update(_p332_proof_state(value))
        result.update(
            {
                "preauth_diagnostics": value["preauth_diagnostics"],
                "rng_eagain_retries": value["rng_eagain_retries"],
                "partial_sessions": value["partial_sessions"],
                "p335_authenticated_attended_resident": value[
                    "p335_authenticated_attended_resident"
                ],
            }
        )
    elif _p334_bundle(prepared.bundle):
        result.update(_p332_proof_state(value))
        result.update(
            {
                "preauth_diagnostics": value["preauth_diagnostics"],
                "rng_eagain_retries": value["rng_eagain_retries"],
                "partial_sessions": value["partial_sessions"],
                "p334_authenticated_logical_resident": value[
                    "p334_authenticated_logical_resident"
                ],
                "first_console_return_checkpoint_only": True,
                "first_read_attribution_requires_stage0_without_stage1": True,
            }
        )
    elif _p333_bundle(prepared.bundle):
        result.update(_p332_proof_state(value))
        result.update(
            {
                "preauth_diagnostics": value["preauth_diagnostics"],
                "rng_eagain_retries": value["rng_eagain_retries"],
                "partial_sessions": value["partial_sessions"],
                "p333_authenticated_logical_resident": value[
                    "p333_authenticated_logical_resident"
                ],
            }
        )
    elif _p332_bundle(prepared.bundle):
        result.update(_p332_proof_state(value))
        result.update(
            {
                "preauth_diagnostics": value["preauth_diagnostics"],
                "rng_eagain_retries": value["rng_eagain_retries"],
                "partial_sessions": value["partial_sessions"],
                "p332_authenticated_logical_resident": value[
                    "p332_authenticated_logical_resident"
                ],
            }
        )
    elif _p331_bundle(prepared.bundle):
        result.update(_p331_proof_state(value))
        result.update(
            {
                "preauth_diagnostics": value["preauth_diagnostics"],
                "rng_eagain_retries": value["rng_eagain_retries"],
                "partial_sessions": value["partial_sessions"],
                "p331_authenticated_resident": value[
                    "p331_authenticated_resident"
                ],
            }
        )
    elif _p328_bundle(prepared.bundle):
        result.update(_p328_proof_state(value))
        proof_key = (
            "p330_authenticated_exec"
            if _p330_bundle(prepared.bundle)
            else "p329_authenticated_exec"
            if _p329_bundle(prepared.bundle)
            else "p328_authenticated_exec"
        )
        result[proof_key] = value.get(proof_key)
        if _p330_bundle(prepared.bundle):
            result.update(
                {
                    "preauth_diagnostics": value["preauth_diagnostics"],
                    "rng_eagain_retries": value["rng_eagain_retries"],
                    "partial_exchange": value["partial_exchange"],
                }
            )
    elif _p327_bundle(prepared.bundle):
        result.update(
            {
                "pid1_framed_exec_proof": value.get(
                    "pid1_framed_exec_proof"
                )
                is True,
                "busybox_ash_command_proof": value.get(
                    "busybox_ash_command_proof"
                )
                is True,
                "framed_session_closed": value.get(
                    "framed_session_closed"
                )
                is True,
                "interactive_pty_proof": value.get(
                    "interactive_pty_proof"
                )
                is False,
                "caller_selected_command": value.get(
                    "caller_selected_command"
                )
                is False,
                "p327_framed_exec": value.get("p327_framed_exec"),
            }
        )
    elif _p326_bundle(prepared.bundle):
        result.update(
            {
                "pid1_bidirectional_proof": value.get(
                    "pid1_bidirectional_proof"
                )
                is True,
                "busybox_shell_roundtrip_proof": value.get(
                    "busybox_shell_roundtrip_proof"
                )
                is True,
                "p326_roundtrip": value.get("p326_roundtrip"),
            }
        )
    return result


def _p318_host_observer(
    prepared: PreparedRun, durable: dict[str, Any]
) -> dict[str, Any]:
    topology_sha256 = durable["topology_sha256"]
    if topology_sha256 is None:
        topology_sha256 = hashlib.sha256(
            prepared.private_target["topology"].removeprefix("usb:").encode()
        ).hexdigest()
    return {
        "classification": durable["classification"],
        "endpoint_identity_sha256": durable["endpoint_identity_sha256"],
        "receipt_sha256": durable["receipt_sha256"],
        "topology_sha256": topology_sha256,
        "bounded": durable["bounded"],
        "valid_receipt": durable["valid_receipt"],
        "download_endpoint_absent": durable["download_endpoint_absent"],
    }


def _guard_warning(status: Any) -> str | None:
    return status if status in NON_TAINTING_GUARD_WARNINGS else None


def _observer_guard_supports_result(
    *,
    accepted: bool,
    status: Any,
    released: bool,
) -> bool:
    return released is True or (
        accepted is True and status in NON_TAINTING_GUARD_WARNINGS
    )


def _reopen_candidate_guard_release(prepared: PreparedRun) -> dict[str, Any]:
    if (
        prepared.bundle.manifest["observation"].get("candidate_observer")
        is None
    ):
        return {
            "status": "not-required",
            "released": True,
            "warning": None,
            "receipt_sha256": None,
        }
    path = prepared.run_dir / "candidate-observer-guard-release.json"
    arm_path = prepared.run_dir / "candidate-observer-guard.json"
    try:
        value = cdc_acm_observer.read_guard_release(path, arm_path)
        receipt = _receipt(path, "candidate observer guard release")
        lifetime_paths = (
            prepared.run_dir / P313_GUARD_LIFETIME_ARM,
            prepared.run_dir / P313_GUARD_LIFETIME_RELEASE,
        )
        if _p313_bundle(prepared.bundle):
            derivation = _p313_bound_guard_derivation(prepared)
            v2_arm = _receipt(arm_path, "candidate observer v2 guard arm")
            lifetime_arm_value = _read_json(
                lifetime_paths[0], "P3.13 guard lifetime arm"
            )
            p313_guard_lifetime.validate_arm(
                lifetime_arm_value,
                approval_binding_sha256=prepared.binding_sha256,
                derivation=derivation,
                v2_arm_receipt_sha256=v2_arm["sha256"],
            )
            lifetime_arm = _receipt(
                lifetime_paths[0], "P3.13 guard lifetime arm"
            )
            lifetime_release_value = _read_json(
                lifetime_paths[1], "P3.13 guard lifetime release"
            )
            elapsed = lifetime_release_value.get("elapsed_upper_millis")
            p313_guard_lifetime.validate_release(
                lifetime_release_value,
                lifetime_arm_sha256=lifetime_arm["sha256"],
                v2_release_receipt_sha256=receipt["sha256"],
                elapsed_upper_millis=elapsed,
                max_sec=derivation["max_sec"],
            )
            if value["released"] is True and (
                lifetime_release_value["released_within_lifetime"] is not True
            ):
                raise F1LiveError("P3.13 normal guard release exceeded lifetime")
        elif any(path.exists() or path.is_symlink() for path in lifetime_paths):
            raise F1LiveError("non-P3.13 run has lifetime guard receipts")
    except (
        cdc_acm_observer.ObserverError,
        p313_guard_lifetime.GuardLifetimeError,
        F1LiveError,
        core.F1V2Error,
        KeyError,
        TypeError,
        OSError,
    ):
        return {
            "status": "invalid-or-failed",
            "released": False,
            "warning": None,
            "receipt_sha256": None,
        }
    return {
        "status": value["status"],
        "released": value["released"],
        "warning": _guard_warning(value["status"]),
        "receipt_sha256": receipt["sha256"],
    }


def _candidate_arrival_proof_projection(
    prepared: PreparedRun, state: dict[str, Any]
) -> dict[str, Any] | None:
    """Derive the opt-in ACM-primary proof and bounded Carrier supplemental."""
    role = _candidate_arrival_proof_role(prepared.bundle)
    if role is None:
        return None
    durable = _reopen_candidate_observation(prepared)
    guard_release = _reopen_candidate_guard_release(prepared)
    p335 = _p335_bundle(prepared.bundle)
    p334 = _p334_bundle(prepared.bundle)
    p333 = _p333_bundle(prepared.bundle)
    p332 = _p332_bundle(prepared.bundle)
    p331 = _p331_bundle(prepared.bundle)
    p330 = _p330_bundle(prepared.bundle)
    p328 = _p328_bundle(prepared.bundle)
    p327 = _p327_bundle(prepared.bundle)
    p326 = _p326_bundle(prepared.bundle)
    p325 = _p325_bundle(prepared.bundle)
    p324 = _p324_bundle(prepared.bundle)
    lane_bound = p324 or p325 or p326 or p327 or p328
    expected_topology = hashlib.sha256(
        (
            p324_typec_lane.CANDIDATE_TOPOLOGY
            if lane_bound
            else prepared.private_target["topology"]
        ).removeprefix("usb:").encode()
    ).hexdigest()
    observer_valid = durable["valid_receipt"] is True
    observer_accepted = (
        observer_valid
        and durable["accepted"] is True
        and durable["classification"] == "accepted"
    )
    if p335:
        observer_accepted = observer_accepted and _p335_proof_ok(durable)
    elif p334 or p333 or p332:
        observer_accepted = observer_accepted and _p332_proof_ok(durable)
    elif p331:
        observer_accepted = observer_accepted and _p331_proof_ok(durable)
    elif p328:
        observer_accepted = observer_accepted and _p328_proof_ok(durable)
    elif p327:
        observer_accepted = (
            observer_accepted
            and durable.get("pid1_framed_exec_proof") is True
            and durable.get("busybox_ash_command_proof") is True
            and durable.get("framed_session_closed") is True
        )
    elif p326:
        observer_accepted = (
            observer_accepted
            and durable.get("pid1_bidirectional_proof") is True
            and durable.get("busybox_shell_roundtrip_proof") is True
        )
    topology_continuous = (
        observer_accepted
        and durable["topology_sha256"] == expected_topology
        and isinstance(durable["endpoint_identity_sha256"], str)
        and re.fullmatch(r"[0-9a-f]{64}", durable["endpoint_identity_sha256"])
        is not None
    )
    if lane_bound:
        topology_continuous = (
            topology_continuous
            and durable["candidate_topology_sha256"] == expected_topology
            and durable["both_topologies_inventory_complete"] is True
            and durable["accepted_inventory_exact"] is True
            and durable["same_run_typec_partner_continuity"] is True
            and durable["accepted_for_p324"] is True
        )
    candidate_completed = (
        state.get("candidate_classification") == "odin_transfer_completed"
        and state.get("candidate_completed") is True
    )
    download_departure = (
        state.get("download_endpoint_absent") is True
        and durable["download_endpoint_absent"] is True
    )
    guard_released = (
        guard_release["status"] == "released"
        and guard_release["released"] is True
    )
    rollback_completed = (
        state.get("rollback_classification") == "odin_transfer_completed"
        and state.get("rollback_completed") is True
    )
    final_healthy = state.get("final_verified") is True
    supplemental = None
    final = state.get("final_evidence")
    final_observer = final.get("observer") if isinstance(final, dict) else None
    if isinstance(final_observer, dict):
        key = (
            "p335_stock"
            if p335
            else "p334_stock"
            if p334
            else "p333_stock"
            if p333
            else "p332_stock"
            if p332
            else "p331_stock"
            if p331
            else "p330_stock"
            if p330
            else "p329_stock"
            if _p329_bundle(prepared.bundle)
            else "p328_stock"
            if _p328_bundle(prepared.bundle)
            else "p327_stock"
            if _p327_bundle(prepared.bundle)
            else "p326_stock"
            if _p326_bundle(prepared.bundle)
            else "p325_stock"
            if _p325_bundle(prepared.bundle)
            else "p324_stock"
            if _p324_bundle(prepared.bundle)
            else "p323_stock"
            if _p323_bundle(prepared.bundle)
            else "p322_stock"
            if _p322_bundle(prepared.bundle)
            else "p321_stock"
            if _p321_bundle(prepared.bundle)
            else "p320_stock"
            if _p320_bundle(prepared.bundle)
            else "p319_stock"
        )
        carrier = final_observer.get(key)
        if isinstance(carrier, dict):
            supplemental = {
                "source": "retained_carrier",
                "field": key,
                "projection": carrier,
                "marker_accepted": state.get("marker_accepted") is True,
            }
        else:
            error_key = (
                "p335_stock_error"
                if p335
                else "p334_stock_error"
                if p334
                else "p333_stock_error"
                if p333
                else "p332_stock_error"
                if p332
                else "p331_stock_error"
                if p331
                else "p330_stock_error"
                if p330
                else "p329_stock_error"
                if _p329_bundle(prepared.bundle)
                else "p328_stock_error"
                if _p328_bundle(prepared.bundle)
                else "p327_stock_error"
                if _p327_bundle(prepared.bundle)
                else "p326_stock_error"
                if _p326_bundle(prepared.bundle)
                else "p325_stock_error"
                if _p325_bundle(prepared.bundle)
                else "p324_stock_error"
                if _p324_bundle(prepared.bundle)
                else "p323_stock_error"
            )
            error = final_observer.get(error_key)
            if isinstance(error, dict):
                supplemental = {
                    "source": error_key,
                    "field": error_key,
                    "projection": error,
                    "marker_accepted": state.get("marker_accepted") is True,
                }
    # P3.25 already retains the complete Carrier projection in final_evidence.
    # Repeating it here makes the durable live-state record exceed MAX_RECORD.
    if p325 or p326 or p327 or p328:
        supplemental = None
    proof = all(
        (
            candidate_completed,
            download_departure,
            observer_accepted,
            topology_continuous,
            guard_released,
            rollback_completed,
            final_healthy,
        )
    )
    result = {
        "schema": typed_evidence.CANDIDATE_ARRIVAL_PROOF_SCHEMA,
        "role": role,
        "primary_source": "candidate_observer",
        "banner_size": (
            len(p335_retained_runtime.DEVICE_BANNER)
            * p335_retained_observer.MAX_SESSIONS
            if p335
            else len(p334_first_read_runtime.DEVICE_BANNER)
            * p334_first_read_runtime.MAX_SESSIONS
            if p334
            else len(p333_open_entry_runtime.DEVICE_BANNER)
            * p333_open_entry_runtime.MAX_SESSIONS
            if p333
            else len(p332_logical_resident_runtime.DEVICE_BANNER)
            * p332_logical_resident_runtime.MAX_SESSIONS
            if p332
            else len(p331_resident_runtime.DEVICE_BANNER)
            * p331_resident_runtime.MAX_SESSIONS
            if p331
            else len(p330_auth_runtime.DEVICE_BANNER)
            if p330
            else len(p328_auth_runtime.DEVICE_BANNER)
            if p328
            else len(p327_framed_runtime.DEVICE_BANNER)
            if p327
            else typed_evidence.P326_CONSOLE_TRANSCRIPT_SIZE
            if p326
            else typed_evidence.P325_ACM_PRIMARY_BANNER_SIZE
            if p325
            else typed_evidence.P324_ACM_PRIMARY_BANNER_SIZE
            if p324
            else typed_evidence.P323_ACM_PRIMARY_BANNER_SIZE
        ),
        "candidate_transfer_completed": candidate_completed,
        "download_departure": download_departure,
        "observer_receipt_valid": observer_valid,
        "observer_receipt_accepted": observer_accepted,
        "observer_receipt_classification": durable["classification"],
        "observer_receipt_sha256": durable["receipt_sha256"],
        "target_topology_continuity": topology_continuous,
        "guard_released": guard_released,
        "rollback_transfer_completed": rollback_completed,
        "final_healthy_return": final_healthy,
        "proof": proof,
        "supplemental_carrier": supplemental,
    }
    if p335:
        result.update(_p332_proof_state(durable))
        result.update(
            {
                "per_boot_identity_required": True,
                "listener_wait_after_proof": True,
                "resident_lease_schema": p335_resident_session.SCHEMA,
            }
        )
    elif p334 or p333 or p332:
        result.update(_p332_proof_state(durable))
        if p334:
            result.update(
                {
                    "first_console_return_checkpoint_only": True,
                    "first_read_attribution_requires_stage0_without_stage1": True,
                }
            )
    elif p331:
        result.update(_p331_proof_state(durable))
    elif p328:
        result.update(_p328_proof_state(durable))
        if p330:
            result.update(
                {
                    "preauth_diagnostics": durable["preauth_diagnostics"],
                    "rng_eagain_retries": durable["rng_eagain_retries"],
                    "partial_exchange": durable["partial_exchange"],
                }
            )
    elif p327:
        result.update(
            {
                "pid1_framed_exec_proof": durable.get(
                    "pid1_framed_exec_proof"
                )
                is True,
                "busybox_ash_command_proof": durable.get(
                    "busybox_ash_command_proof"
                )
                is True,
                "framed_session_closed": durable.get(
                    "framed_session_closed"
                )
                is True,
                "interactive_pty_proof": durable.get(
                    "interactive_pty_proof"
                )
                is False,
                "caller_selected_command": durable.get(
                    "caller_selected_command"
                )
                is False,
            }
        )
    elif p326:
        result.update(
            {
                "pid1_bidirectional_proof": durable.get(
                    "pid1_bidirectional_proof"
                )
                is True,
                "busybox_shell_roundtrip_proof": durable.get(
                    "busybox_shell_roundtrip_proof"
                )
                is True,
            }
        )
    if lane_bound:
        result.update(
            {
                "same_run_typec_partner_continuity": durable.get(
                    "same_run_typec_partner_continuity"
                ),
                "candidate_lane_inventory_exact": durable.get(
                    "accepted_inventory_exact"
                ),
            }
        )
    return result


def _save_candidate_arrival_proof(
    prepared: PreparedRun, state: dict[str, Any]
) -> None:
    projection = _candidate_arrival_proof_projection(prepared, state)
    if projection is not None:
        state[typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY] = projection


def _validate_candidate_arrival_proof_state(
    prepared: PreparedRun, state: dict[str, Any]
) -> None:
    if not (
        _p323_bundle(prepared.bundle)
        or _p324_bundle(prepared.bundle)
        or _p325_bundle(prepared.bundle)
        or _p326_bundle(prepared.bundle)
        or _p327_bundle(prepared.bundle)
        or _p328_bundle(prepared.bundle)
        or _p335_bundle(prepared.bundle)
    ):
        return
    expected = _candidate_arrival_proof_projection(prepared, state)
    if state.get(typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY) != expected:
        raise F1LiveError("candidate arrival proof durable state mismatch")


def _guard_release_failure_outcome(status: Any) -> str:
    if status == "guard-expired":
        return "candidate_observer_guard_expired_rollback_verified"
    return "candidate_observer_guard_release_failed_rollback_verified"


def _state(prepared: PreparedRun) -> dict[str, Any]:
    path = _live_state_path(prepared)
    if not path.exists():
        return {
            "schema": LIVE_STATE_SCHEMA,
            "candidate_classification": "not-attempted",
            "candidate_completed": False,
            "rollback_completed": False,
            "final_verified": False,
        }
    value = _read_json(path, "F1 live state")
    if value.get("schema") != LIVE_STATE_SCHEMA:
        raise F1LiveError("F1 live state schema mismatch")
    return value


def _save_state(prepared: PreparedRun, value: dict[str, Any]) -> None:
    value = {**value, "schema": LIVE_STATE_SCHEMA}
    _write_atomic(_live_state_path(prepared), value)


def _result(
    prepared: PreparedRun,
    journal: core.Journal,
    verdict: str,
    outcome: str,
    recovery_required: bool,
) -> dict[str, Any]:
    state = _state(prepared)
    if _acm_primary_bundle(prepared.bundle) and state.get("final_verified") is True:
        _save_candidate_arrival_proof(prepared, state)
        if state != _state(prepared):
            _save_state(prepared, state)
    elif (
        _acm_primary_bundle(prepared.bundle)
        and typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY in state
    ):
        raise F1LiveError("candidate arrival proof precedes final health")
    value = {
        "schema": LIVE_RESULT_SCHEMA,
        "adapter_version": ADAPTER_VERSION,
        "manifest_id": prepared.bundle.manifest["manifest_id"],
        "bundle_sha256": prepared.bundle.sha256,
        "approval_binding_sha256": prepared.binding_sha256,
        "journal": journal.receipt(),
        "current_state": journal.state(),
        "timeline": core.timeline(journal.records()),
        "live_state": state,
        "verdict": verdict,
        "outcome_class": outcome,
        "recovery_required": recovery_required,
    }
    validate_live_result(value, prepared)
    _write_live_result(prepared.run_dir / "live-result.json", value)
    return value


def _validate_transfer_result(
    prepared: PreparedRun, kind: str, attempt: int
) -> dict[str, Any] | None:
    prefix = f"{kind}-attempt-{attempt:02d}"
    result_path = prepared.run_dir / f"{prefix}.result.json"
    if not result_path.exists():
        return None
    value = _read_json(result_path, f"{kind} transfer receipt")
    if value.get("schema") == "device_action_f1_transfer_failure_v2":
        if set(value) != {
            "schema",
            "kind",
            "attempt",
            "prefix",
            "possible_device_session",
            "error_type",
        } or (
            value["kind"] != kind
            or value["attempt"] != attempt
            or value["prefix"] != prefix
            or value["possible_device_session"] is not True
            or not isinstance(value["error_type"], str)
            or not value["error_type"]
        ):
            raise F1LiveError(f"{kind} transfer failure evidence is malformed")
        return {**value, "classification": "odin_device_session_failure_or_unknown"}
    if (
        value.get("schema") != "device_action_f1_transfer_receipt_v2"
        or value.get("kind") != kind
        or value.get("attempt") != attempt
        or value.get("prefix") != prefix
        or value.get("classification")
        not in {
            "odin_local_parse_failure",
            "odin_transfer_completed",
            "odin_device_session_failure_or_unknown",
        }
        or not isinstance(value.get("stdout"), dict)
        or not isinstance(value.get("stderr"), dict)
        or not isinstance(value.get("transport"), dict)
    ):
        raise F1LiveError(f"{kind} transfer evidence is malformed")
    transport_value = value["transport"]
    transport_keys = {
        "label",
        "returncode",
        "timed_out",
        "output_exceeded",
        "producer_error_type",
        "command_shape",
        "regular_path_inputs",
        "anonymous_proc_fd_inputs",
        "odin",
        "ap",
        "stdout_bytes",
        "stderr_bytes",
        "stdout_sha256",
        "stderr_sha256",
        "raw_capture_receipt",
    }
    item = (
        prepared.bundle.manifest["candidate_ap"]
        if kind == "candidate"
        else prepared.bundle.manifest["rollback_ap"]
    )
    expected_odin = prepared.bundle.profile["transport"]["odin"]
    expected_ap = {
        "path": str(core._artifact_path(prepared.root, item, f"{kind}_ap")),
        "size": item["size"],
        "sha256": item["sha256"],
    }
    raw_value = transport_value.get("raw_capture_receipt")
    if (
        set(transport_value) != transport_keys
        or transport_value["label"] != kind
        or (
            transport_value["returncode"] is not None
            and type(transport_value["returncode"]) is not int
        )
        or type(transport_value["timed_out"]) is not bool
        or type(transport_value["output_exceeded"]) is not bool
        or (
            transport_value["producer_error_type"] is not None
            and not isinstance(transport_value["producer_error_type"], str)
        )
        or transport_value["command_shape"]
        != ["odin4", "--reboot", "-a", "AP.tar.md5", "-d", "USBFS"]
        or transport_value["regular_path_inputs"] is not True
        or transport_value["anonymous_proc_fd_inputs"] is not False
        or transport_value["odin"] != expected_odin
        or transport_value["ap"] != expected_ap
        or not isinstance(raw_value, dict)
        or set(raw_value) != {"path", "sha256", "size"}
    ):
        raise F1LiveError(f"{kind} transport receipt is malformed")
    for stream in ("stdout", "stderr"):
        path = prepared.run_dir / f"{prefix}.{stream}"
        if value[stream] != _receipt(
            path,
            f"{kind} {stream}",
            MAX_ODIN_OUTPUT,
        ):
            raise F1LiveError(f"{kind} {stream} evidence changed")
    raw_path = prepared.run_dir / f"{prefix}-odin.capture.json"
    try:
        handle = raw_capture.load_handle(raw_path)
        raw_payload = raw_path.read_bytes()
        expected_classification, stdout, stderr = _classify_odin_capture(handle)
    except (OSError, raw_capture.RawCaptureError, F1LiveError) as exc:
        raise F1LiveError(f"{kind} raw transport evidence changed") from exc
    if (
        raw_value
        != {
            "path": str(raw_path),
            "size": len(raw_payload),
            "sha256": hashlib.sha256(raw_payload).hexdigest(),
        }
        or handle.stdout_path != prepared.run_dir / f"{prefix}.stdout"
        or handle.stderr_path != prepared.run_dir / f"{prefix}.stderr"
        or handle.returncode != transport_value["returncode"]
        or handle.timed_out is not transport_value["timed_out"]
        or handle.output_exceeded is not transport_value["output_exceeded"]
        or handle.producer_error_type != transport_value["producer_error_type"]
        or transport_value["stdout_bytes"] != len(stdout)
        or transport_value["stderr_bytes"] != len(stderr)
        or transport_value["stdout_sha256"] != hashlib.sha256(stdout).hexdigest()
        or transport_value["stderr_sha256"] != hashlib.sha256(stderr).hexdigest()
    ):
        raise F1LiveError(f"{kind} raw transport binding differs")
    if value["classification"] != expected_classification:
        raise F1LiveError(f"{kind} transfer classification differs from raw")
    return value


def _validate_transfer_evidence(prepared: PreparedRun, kind: str) -> dict[str, Any]:
    journal = core.Journal.reopen(
        prepared.run_dir / "transaction", prepared.binding_sha256
    )
    count = _reconcile_transfer_attempts(
        prepared, journal, kind, repair_orphan_start=False
    )
    if not count:
        raise F1LiveError(f"{kind} transfer evidence count is invalid")
    last: dict[str, Any] | None = None
    for index in range(1, count + 1):
        result = _validate_transfer_result(prepared, kind, index)
        if index == count:
            last = result
    if last is None:
        attempt = count
        return {
            "schema": "device_action_f1_transfer_interrupted_v2",
            "kind": kind,
            "attempt": attempt,
            "prefix": f"{kind}-attempt-{attempt:02d}",
            "classification": "odin_device_session_failure_or_unknown",
        }
    return last


def _validate_final_observer(prepared: PreparedRun, state: dict[str, Any]) -> None:
    evidence = state.get("final_evidence")
    if not isinstance(evidence, dict) or evidence.get("rollback_verified") is not True:
        raise F1LiveError("final evidence is missing rollback verification")
    observer = evidence.get("observer")
    if not isinstance(observer, dict) or observer.get("byte_identical") is not True:
        raise F1LiveError("final observer evidence is malformed")
    health = evidence.get("health")
    expected_health = prepared.bundle.profile["final_health"]
    if (
        not isinstance(health, dict)
        or set(health)
        != {
            "android_boot_completed",
            "boot_animation_stopped",
            "verified_boot_state",
            "root_verified",
            "boot_sha256",
            "supporting_partition_sha256",
            "odin_endpoint_absent",
            "kernel_release",
            "boot_id_sha256",
        }
        or health.get("android_boot_completed") is not True
        or health.get("boot_animation_stopped") is not True
        or health.get("verified_boot_state")
        != expected_health["verified_boot_state"]
        or health.get("root_verified") is not True
        or health.get("boot_sha256") != expected_health["boot_sha256"]
        or health.get("supporting_partition_sha256")
        != expected_health["supporting_partition_sha256"]
        or health.get("odin_endpoint_absent") is not True
        or not isinstance(health.get("kernel_release"), str)
        or not health.get("kernel_release")
        or re.fullmatch(r"[0-9a-f]{64}", str(health.get("boot_id_sha256")))
        is None
    ):
        raise F1LiveError("final health evidence does not match the profile")
    expected_target = core.json_sha256(
        {
            "serial": hashlib.sha256(
                prepared.private_target["serial"].encode()
            ).hexdigest(),
            "topology": hashlib.sha256(
                prepared.private_target["topology"].encode()
            ).hexdigest(),
        }
    )
    if evidence.get("target_evidence_sha256") != expected_target:
        raise F1LiveError("final target continuity evidence mismatch")
    payloads: list[bytes] = []
    for index, receipt in enumerate(observer.get("reads", []), 1):
        if index > 2 or not isinstance(receipt, dict):
            raise F1LiveError("final observer receipt count is invalid")
        path = prepared.run_dir / f"rollback-observer-{index}.bin"
        raw_value = receipt.get("raw_capture")
        if (
            set(receipt)
            != {
                "path",
                "bytes",
                "sha256",
                "raw_capture",
                "read_to_eof",
                "stderr_bytes",
                "elapsed_sec",
            }
            or not isinstance(raw_value, dict)
            or set(raw_value) != {"path", "size", "sha256"}
            or not isinstance(raw_value.get("path"), str)
            or not isinstance(raw_value.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", raw_value["sha256"]) is None
            or type(raw_value.get("size")) is not int
            or not 0 < raw_value["size"] <= 64 * 1024
            or isinstance(receipt.get("elapsed_sec"), bool)
            or not isinstance(receipt.get("elapsed_sec"), (int, float))
            or not math.isfinite(float(receipt["elapsed_sec"]))
            or not 0 < receipt["elapsed_sec"] <= 185
        ):
            raise F1LiveError("final observer raw receipt shape differs")
        raw_path = Path(raw_value["path"])
        if (
            raw_path.parent != prepared.run_dir
            or re.fullmatch(
                r"[0-9]{4}-observer-eof\.capture\.json", raw_path.name
            )
            is None
        ):
            raise F1LiveError("final observer raw receipt path differs")
        raw_receipt_payload, _raw_receipt_identity = core._stable_read(
            raw_path, "final observer raw receipt", 64 * 1024
        )
        if (
            len(raw_receipt_payload) != raw_value["size"]
            or hashlib.sha256(raw_receipt_payload).hexdigest()
            != raw_value["sha256"]
        ):
            raise F1LiveError("final observer raw receipt changed")
        try:
            handle = raw_capture.load_handle(raw_path)
            payload = raw_capture.read_stdout(
                handle, maximum=MAX_OBSERVER_BYTES
            )
            stderr = raw_capture.read_stderr(
                handle, maximum=d0.MAX_TEXT_OUTPUT
            )
        except raw_capture.RawCaptureError as exc:
            raise F1LiveError("final observer raw handle differs") from exc
        if (
            stderr
            or handle.stdout_path != path
            or handle.stderr_path
            != path.with_suffix(path.suffix + ".stderr")
            or handle.returncode != 0
            or handle.timed_out
            or handle.output_exceeded
            or handle.producer_error_type is not None
            or receipt.get("path") != str(path)
            or receipt.get("bytes") != len(payload)
            or receipt.get("sha256") != hashlib.sha256(payload).hexdigest()
            or receipt.get("read_to_eof") is not True
            or receipt.get("stderr_bytes") != 0
        ):
            raise F1LiveError("final observer raw evidence changed")
        payloads.append(payload)
    if len(payloads) != 2 or not payloads[0] or payloads[0] != payloads[1]:
        raise F1LiveError("final observer raw reads are not identical")
    acceptance = prepared.bundle.manifest["observation"]["acceptance"]
    stock_error = None
    try:
        marker_result = classify_acceptance(payloads[0], acceptance)
    except F1LiveError as exc:
        if not _acm_primary_bundle(prepared.bundle):
            raise
        if _p335_bundle(prepared.bundle):
            stock_error = _p335_stock_error(payloads[0], exc)
            marker_result = _p335_parser_failure_classification(
                payloads[0], exc
            )
        elif _p334_bundle(prepared.bundle):
            stock_error = _p334_stock_error(payloads[0], exc)
            marker_result = _p334_parser_failure_classification(
                payloads[0], exc
            )
        elif _p333_bundle(prepared.bundle):
            stock_error = _p333_stock_error(payloads[0], exc)
            marker_result = _p333_parser_failure_classification(
                payloads[0], exc
            )
        elif _p332_bundle(prepared.bundle):
            stock_error = _p332_stock_error(payloads[0], exc)
            marker_result = _p332_parser_failure_classification(
                payloads[0], exc
            )
        elif _p331_bundle(prepared.bundle):
            stock_error = _p331_stock_error(payloads[0], exc)
            marker_result = _p331_parser_failure_classification(
                payloads[0], exc
            )
        elif _p330_bundle(prepared.bundle):
            stock_error = _p330_stock_error(payloads[0], exc)
            marker_result = _p330_parser_failure_classification(
                payloads[0], exc
            )
        elif _p329_bundle(prepared.bundle):
            stock_error = _p329_stock_error(payloads[0], exc)
            marker_result = _p329_parser_failure_classification(
                payloads[0], exc
            )
        elif _p328_bundle(prepared.bundle):
            stock_error = _p328_stock_error(payloads[0], exc)
            marker_result = _p328_parser_failure_classification(
                payloads[0], exc
            )
        elif _p327_bundle(prepared.bundle):
            stock_error = _p327_stock_error(payloads[0], exc)
            marker_result = _p327_parser_failure_classification(
                payloads[0], exc
            )
        elif _p326_bundle(prepared.bundle):
            stock_error = _p326_stock_error(payloads[0], exc)
            marker_result = _p326_parser_failure_classification(
                payloads[0], exc
            )
        elif _p325_bundle(prepared.bundle):
            stock_error = _p325_stock_error(payloads[0], exc)
            marker_result = _p325_parser_failure_classification(
                payloads[0], exc
            )
        elif _p324_bundle(prepared.bundle):
            stock_error = _p324_stock_error(payloads[0], exc)
            marker_result = _p324_parser_failure_classification(
                payloads[0], exc
            )
        else:
            stock_error = _p323_stock_error(payloads[0], exc)
            marker_result = _p323_parser_failure_classification(
                payloads[0], exc
            )
    if _p318_bundle(prepared.bundle):
        marker_result, topology_evidence = _p318_finalize_candidate_phase(
            prepared, marker_result
        )
        if evidence.get("p318_candidate_topology") != topology_evidence:
            raise F1LiveError("P3.18 final topology evidence changed")
    elif "p318_candidate_topology" in evidence:
        raise F1LiveError("foreign P3.18 final topology evidence")
    if _p319_bundle(prepared.bundle):
        if not _p319_exact_equal(
            observer.get("p319_stock"), _p319_terminal_projection(marker_result)
        ):
            raise F1LiveError("P3.19 final stock projection changed")
    elif "p319_stock" in observer:
        raise F1LiveError("foreign P3.19 final stock evidence")
    if _p320_bundle(prepared.bundle):
        if not _p319_exact_equal(
            observer.get("p320_stock"), _p320_terminal_projection(marker_result)
        ):
            raise F1LiveError("P3.20 final stock projection changed")
    elif "p320_stock" in observer:
        raise F1LiveError("foreign P3.20 final stock evidence")
    if _p321_bundle(prepared.bundle):
        if not _p319_exact_equal(
            observer.get("p321_stock"), _p320_terminal_projection(marker_result)
        ):
            raise F1LiveError("P3.21 final stock projection changed")
    elif "p321_stock" in observer:
        raise F1LiveError("foreign P3.21 final stock evidence")
    if _p322_bundle(prepared.bundle):
        if not _p319_exact_equal(
            observer.get("p322_stock"), _p320_terminal_projection(marker_result)
        ):
            raise F1LiveError("P3.22 final stock projection changed")
    elif "p322_stock" in observer:
        raise F1LiveError("foreign P3.22 final stock evidence")
    if _p323_bundle(prepared.bundle):
        if stock_error is not None:
            if (
                observer.get("p323_stock_error") != stock_error
                or "p323_stock" in observer
            ):
                raise F1LiveError("P3.23 supplemental parser failure changed")
        elif not _p319_exact_equal(
            observer.get("p323_stock"), _p320_terminal_projection(marker_result)
        ):
            raise F1LiveError("P3.23 final stock projection changed")
    elif "p323_stock" in observer or "p323_stock_error" in observer:
        raise F1LiveError("foreign P3.23 final stock evidence")
    if _p324_bundle(prepared.bundle):
        if stock_error is not None:
            if (
                observer.get("p324_stock_error") != stock_error
                or "p324_stock" in observer
            ):
                raise F1LiveError("P3.24 supplemental parser failure changed")
        elif not _p319_exact_equal(
            observer.get("p324_stock"),
            _p320_terminal_projection(marker_result),
        ):
            raise F1LiveError("P3.24 final stock projection changed")
    elif "p324_stock" in observer or "p324_stock_error" in observer:
        raise F1LiveError("foreign P3.24 final stock evidence")
    if _p325_bundle(prepared.bundle):
        if stock_error is not None:
            if (
                observer.get("p325_stock_error") != stock_error
                or "p325_stock" in observer
            ):
                raise F1LiveError("P3.25 supplemental parser failure changed")
        elif not _p319_exact_equal(
            observer.get("p325_stock"), _p320_terminal_projection(marker_result)
        ):
            raise F1LiveError("P3.25 final stock projection changed")
    elif "p325_stock" in observer or "p325_stock_error" in observer:
        raise F1LiveError("foreign P3.25 final stock evidence")
    if _p335_bundle(prepared.bundle):
        if stock_error is not None:
            if (
                observer.get("p335_stock_error") != stock_error
                or "p335_stock" in observer
            ):
                raise F1LiveError("P3.35 supplemental parser failure changed")
        elif not _p319_exact_equal(
            observer.get("p335_stock"), _p320_terminal_projection(marker_result)
        ):
            raise F1LiveError("P3.35 final stock projection changed")
    elif "p335_stock" in observer or "p335_stock_error" in observer:
        raise F1LiveError("foreign P3.35 final stock evidence")
    elif _p334_bundle(prepared.bundle):
        if stock_error is not None:
            if (
                observer.get("p334_stock_error") != stock_error
                or "p334_stock" in observer
            ):
                raise F1LiveError("P3.34 supplemental parser failure changed")
        elif not _p319_exact_equal(
            observer.get("p334_stock"), _p320_terminal_projection(marker_result)
        ):
            raise F1LiveError("P3.34 final stock projection changed")
    elif "p334_stock" in observer or "p334_stock_error" in observer:
        raise F1LiveError("foreign P3.34 final stock evidence")
    elif _p333_bundle(prepared.bundle):
        if stock_error is not None:
            if (
                observer.get("p333_stock_error") != stock_error
                or "p333_stock" in observer
            ):
                raise F1LiveError("P3.33 supplemental parser failure changed")
        elif not _p319_exact_equal(
            observer.get("p333_stock"), _p320_terminal_projection(marker_result)
        ):
            raise F1LiveError("P3.33 final stock projection changed")
    elif "p333_stock" in observer or "p333_stock_error" in observer:
        raise F1LiveError("foreign P3.33 final stock evidence")
    elif _p332_bundle(prepared.bundle):
        if stock_error is not None:
            if (
                observer.get("p332_stock_error") != stock_error
                or "p332_stock" in observer
            ):
                raise F1LiveError("P3.32 supplemental parser failure changed")
        elif not _p319_exact_equal(
            observer.get("p332_stock"), _p320_terminal_projection(marker_result)
        ):
            raise F1LiveError("P3.32 final stock projection changed")
    elif "p332_stock" in observer or "p332_stock_error" in observer:
        raise F1LiveError("foreign P3.32 final stock evidence")
    elif _p331_bundle(prepared.bundle):
        if stock_error is not None:
            if (
                observer.get("p331_stock_error") != stock_error
                or "p331_stock" in observer
            ):
                raise F1LiveError("P3.31 supplemental parser failure changed")
        elif not _p319_exact_equal(
            observer.get("p331_stock"), _p320_terminal_projection(marker_result)
        ):
            raise F1LiveError("P3.31 final stock projection changed")
    elif "p331_stock" in observer or "p331_stock_error" in observer:
        raise F1LiveError("foreign P3.31 final stock evidence")
    elif _p330_bundle(prepared.bundle):
        if stock_error is not None:
            if (
                observer.get("p330_stock_error") != stock_error
                or "p330_stock" in observer
            ):
                raise F1LiveError("P3.30 supplemental parser failure changed")
        elif not _p319_exact_equal(
            observer.get("p330_stock"), _p320_terminal_projection(marker_result)
        ):
            raise F1LiveError("P3.30 final stock projection changed")
    elif _p329_bundle(prepared.bundle):
        if stock_error is not None:
            if (
                observer.get("p329_stock_error") != stock_error
                or "p329_stock" in observer
            ):
                raise F1LiveError("P3.29 supplemental parser failure changed")
        elif not _p319_exact_equal(
            observer.get("p329_stock"), _p320_terminal_projection(marker_result)
        ):
            raise F1LiveError("P3.29 final stock projection changed")
    elif _p328_bundle(prepared.bundle):
        if stock_error is not None:
            if (
                observer.get("p328_stock_error") != stock_error
                or "p328_stock" in observer
            ):
                raise F1LiveError("P3.28 supplemental parser failure changed")
        elif not _p319_exact_equal(
            observer.get("p328_stock"), _p320_terminal_projection(marker_result)
        ):
            raise F1LiveError("P3.28 final stock projection changed")
    elif _p327_bundle(prepared.bundle):
        if stock_error is not None:
            if (
                observer.get("p327_stock_error") != stock_error
                or "p327_stock" in observer
            ):
                raise F1LiveError("P3.27 supplemental parser failure changed")
        elif not _p319_exact_equal(
            observer.get("p327_stock"), _p320_terminal_projection(marker_result)
        ):
            raise F1LiveError("P3.27 final stock projection changed")
    elif _p326_bundle(prepared.bundle):
        if stock_error is not None:
            if (
                observer.get("p326_stock_error") != stock_error
                or "p326_stock" in observer
            ):
                raise F1LiveError("P3.26 supplemental parser failure changed")
        elif not _p319_exact_equal(
            observer.get("p326_stock"), _p320_terminal_projection(marker_result)
        ):
            raise F1LiveError("P3.26 final stock projection changed")
    elif "p326_stock" in observer or "p326_stock_error" in observer:
        raise F1LiveError("foreign P3.26 final stock evidence")
    exact = marker_result["exact_count"]
    family = marker_result["family_count"]
    accepted = marker_result["accepted"] is True
    if (
        observer.get("bytes") != len(payloads[0])
        or observer.get("sha256") != hashlib.sha256(payloads[0]).hexdigest()
        or observer.get("exact_marker_count") != exact
        or observer.get("marker_family_count") != family
        or observer.get("classification") != marker_result
        or observer.get("accepted") is not accepted
        or state.get("marker_accepted") is not accepted
    ):
        raise F1LiveError("final observer semantics mismatch")


def _validate_candidate_observer_state(
    prepared: PreparedRun, state: dict[str, Any]
) -> None:
    spec = prepared.bundle.manifest["observation"].get("candidate_observer")
    if spec is None:
        return
    durable = _reopen_candidate_observation(prepared)
    guard_release = _reopen_candidate_guard_release(prepared)
    if (
        state.get("candidate_observer_classification")
        != durable["classification"]
        or state.get("candidate_observer_accepted") is not durable["accepted"]
        or state.get("candidate_observer_receipt_sha256")
        != durable["receipt_sha256"]
        or state.get("download_endpoint_absent")
        is not durable["download_endpoint_absent"]
        or state.get("candidate_observer_guard_release_status")
        != guard_release["status"]
        or state.get("candidate_observer_guard_released")
        is not guard_release["released"]
        or state.get("candidate_observer_guard_warning")
        != guard_release["warning"]
        or state.get("candidate_observer_guard_release_receipt_sha256")
        != guard_release["receipt_sha256"]
    ):
        raise F1LiveError("candidate observer durable state mismatch")
    if _p328_bundle(prepared.bundle) and any(
        state.get(key) != durable.get(key)
        for key in P328_PROOF_FIELDS
    ) and not (
        _p331_bundle(prepared.bundle)
        or _p332_bundle(prepared.bundle)
        or _p333_bundle(prepared.bundle)
        or _p334_bundle(prepared.bundle)
        or _p335_bundle(prepared.bundle)
    ):
        raise F1LiveError("P3.28 authenticated proof durable state mismatch")
    if (
        _p332_bundle(prepared.bundle)
        or _p333_bundle(prepared.bundle)
        or _p334_bundle(prepared.bundle)
        or _p335_bundle(prepared.bundle)
    ) and any(
        state.get(key) != durable.get(key)
        for key in P332_PROOF_FIELDS
    ):
        raise F1LiveError("logical resident proof durable state mismatch")
    if (
        _p332_bundle(prepared.bundle)
        or _p333_bundle(prepared.bundle)
        or _p334_bundle(prepared.bundle)
        or _p335_bundle(prepared.bundle)
    ) and any(
        state.get(key) != durable.get(key)
        for key in (
            "preauth_diagnostics",
            "rng_eagain_retries",
            "partial_sessions",
        )
    ):
        raise F1LiveError("logical resident audit durable state mismatch")
    if _p335_bundle(prepared.bundle) and state.get(
        "p335_authenticated_attended_resident"
    ) != durable.get("p335_authenticated_attended_resident"):
        raise F1LiveError("P3.35 attended resident proof durable state mismatch")
    if _p331_bundle(prepared.bundle) and any(
        state.get(key) != durable.get(key)
        for key in P331_PROOF_FIELDS
    ):
        raise F1LiveError("P3.31 resident proof durable state mismatch")
    if _p331_bundle(prepared.bundle) and any(
        state.get(key) != durable.get(key)
        for key in (
            "preauth_diagnostics",
            "rng_eagain_retries",
            "partial_sessions",
        )
    ):
        raise F1LiveError("P3.31 resident audit durable state mismatch")
    if _p330_bundle(prepared.bundle) and any(
        state.get(key) != durable.get(key)
        for key in (
            "preauth_diagnostics",
            "rng_eagain_retries",
            "partial_exchange",
        )
    ):
        raise F1LiveError("P3.30 partial exchange durable state mismatch")
    if _p327_bundle(prepared.bundle) and any(
        state.get(key) != durable.get(key)
        for key in (
            "pid1_framed_exec_proof",
            "busybox_ash_command_proof",
            "framed_session_closed",
            "interactive_pty_proof",
            "caller_selected_command",
        )
    ):
        raise F1LiveError("P3.27 framed proof durable state mismatch")
    if _acm_primary_bundle(prepared.bundle) and state.get("final_verified") is True:
        _validate_candidate_arrival_proof_state(prepared, state)
    elif (
        _acm_primary_bundle(prepared.bundle)
        and typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY in state
    ):
        raise F1LiveError("candidate arrival proof precedes final health")
    if durable["accepted"] is True and (
        state.get("candidate_completed") is not True
        or durable["download_endpoint_absent"] is not True
    ):
        raise F1LiveError("candidate observer acceptance lacks transfer continuity")
    if _p318_bundle(prepared.bundle) and state.get(
        "p318_candidate_topology_raw"
    ) != _p318_candidate_raw_receipt(prepared):
        raise F1LiveError("P3.18 candidate topology raw durable state mismatch")


def validate_live_result(
    result: dict[str, Any], prepared: PreparedRun
) -> dict[str, Any]:
    expected_keys = {
        "schema",
        "adapter_version",
        "manifest_id",
        "bundle_sha256",
        "approval_binding_sha256",
        "journal",
        "current_state",
        "timeline",
        "live_state",
        "verdict",
        "outcome_class",
        "recovery_required",
    }
    if set(result) != expected_keys:
        raise F1LiveError("live result shape mismatch")
    journal = core.Journal.reopen(
        prepared.run_dir / "transaction", prepared.binding_sha256
    )
    state = _state(prepared)
    _validate_p300_usb_trace_state(prepared, state, journal.records())
    if (
        result["schema"] != LIVE_RESULT_SCHEMA
        or result["adapter_version"] != ADAPTER_VERSION
        or result["manifest_id"] != prepared.bundle.manifest["manifest_id"]
        or result["bundle_sha256"] != prepared.bundle.sha256
        or result["approval_binding_sha256"] != prepared.binding_sha256
        or result["journal"] != journal.receipt()
        or result["current_state"] != journal.state()
        or result["timeline"] != core.timeline(journal.records())
        or result["live_state"] != state
    ):
        raise F1LiveError("live result does not reopen against durable state")
    candidate_classification = state.get("candidate_classification")
    if candidate_classification not in {
        "not-attempted",
        "odin_local_parse_failure",
        "odin_transfer_completed",
        "odin_device_session_failure_or_unknown",
    }:
        raise F1LiveError("live candidate classification is invalid")
    if _acm_primary_bundle(prepared.bundle) and state.get("final_verified") is True:
        _validate_candidate_arrival_proof_state(prepared, state)
    elif (
        _acm_primary_bundle(prepared.bundle)
        and typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY in state
    ):
        raise F1LiveError("candidate arrival proof precedes final health")
    if candidate_classification != "not-attempted":
        evidence = _validate_transfer_evidence(prepared, "candidate")
        if evidence["classification"] != candidate_classification:
            raise F1LiveError("candidate transfer classification mismatch")
    if state.get("candidate_completed") is not (
        candidate_classification == "odin_transfer_completed"
    ):
        raise F1LiveError("candidate completion semantics mismatch")
    if candidate_classification not in {
        "not-attempted",
        "odin_local_parse_failure",
    }:
        _validate_candidate_observer_state(prepared, state)
    rollback_classification = state.get("rollback_classification")
    if rollback_classification is not None:
        rollback = _validate_transfer_evidence(prepared, "rollback")
        if rollback["classification"] != rollback_classification:
            raise F1LiveError("rollback transfer classification mismatch")
    if state.get("rollback_completed") is not (
        rollback_classification == "odin_transfer_completed"
    ):
        raise F1LiveError("rollback completion semantics mismatch")
    if state.get("final_verified") is True:
        if state.get("rollback_completed") is not True:
            raise F1LiveError("final verification precedes completed rollback")
        _validate_final_observer(prepared, state)
    verdict = result["verdict"]
    names = [event["name"] for event in result["timeline"]["events"]]
    request_cut = _request_cut_transition(journal)
    if request_cut is not None:
        request_cut_exact = (
            request_cut["outcome"] == "download_request_cut_recovery_exact"
        )
        _validate_stored_request_cut_details(
            request_cut["details"], exact=request_cut_exact
        )
        if _request_cut_has_candidate_evidence(prepared, journal):
            raise F1LiveError("Download request recovery invented candidate evidence")
        if names == list(core.RECOVERY_TIMELINE) and not request_cut_exact:
            raise F1LiveError("parked Download request recovery reached a terminal")
    if _acm_primary_bundle(prepared.bundle) and state.get("final_verified") is True:
        p335 = _p335_bundle(prepared.bundle)
        p334 = _p334_bundle(prepared.bundle)
        p333 = _p333_bundle(prepared.bundle)
        p332 = _p332_bundle(prepared.bundle)
        p331 = _p331_bundle(prepared.bundle)
        p330 = _p330_bundle(prepared.bundle)
        p329 = _p329_bundle(prepared.bundle)
        p328 = _p328_bundle(prepared.bundle)
        p327 = _p327_bundle(prepared.bundle)
        p326 = _p326_bundle(prepared.bundle)
        p325 = _p325_bundle(prepared.bundle)
        p324 = _p324_bundle(prepared.bundle)
        label = (
            "P3.35"
            if p335
            else "P3.34"
            if p334
            else "P3.33"
            if p333
            else "P3.32"
            if p332
            else "P3.31"
            if p331
            else "P3.30"
            if p330
            else "P3.29"
            if p329
            else "P3.28"
            if p328
            else "P3.27"
            if p327
            else "P3.26"
            if p326
            else "P3.25"
            if p325
            else "P3.24"
            if p324
            else "P3.23"
        )
        success_verdict = (
            P335_SUCCESS_VERDICT
            if p335
            else P334_SUCCESS_VERDICT
            if p334
            else P333_SUCCESS_VERDICT
            if p333
            else P332_SUCCESS_VERDICT
            if p332
            else P331_SUCCESS_VERDICT
            if p331
            else P330_SUCCESS_VERDICT
            if p330
            else P329_SUCCESS_VERDICT
            if p329
            else P328_SUCCESS_VERDICT
            if p328
            else typed_evidence.P327_FRAMED_EXEC_VERDICT
            if p327
            else
            typed_evidence.P326_CONSOLE_VERDICT
            if p326
            else typed_evidence.P325_ACM_PRIMARY_VERDICT
            if p325
            else
            typed_evidence.P324_ACM_PRIMARY_VERDICT
            if p324
            else typed_evidence.P323_ACM_PRIMARY_VERDICT
        )
        success_outcome = (
            P335_SUCCESS_OUTCOME
            if p335
            else P334_SUCCESS_OUTCOME
            if p334
            else P333_SUCCESS_OUTCOME
            if p333
            else P332_SUCCESS_OUTCOME
            if p332
            else P331_SUCCESS_OUTCOME
            if p331
            else P330_SUCCESS_OUTCOME
            if p330
            else P329_SUCCESS_OUTCOME
            if p329
            else P328_SUCCESS_OUTCOME
            if p328
            else typed_evidence.P327_FRAMED_EXEC_OUTCOME
            if p327
            else
            typed_evidence.P326_CONSOLE_OUTCOME
            if p326
            else typed_evidence.P325_ACM_PRIMARY_OUTCOME
            if p325
            else
            typed_evidence.P324_ACM_PRIMARY_OUTCOME
            if p324
            else typed_evidence.P323_ACM_PRIMARY_OUTCOME
        )
        no_proof_outcome = (
            P335_NO_PROOF_OUTCOME
            if p335
            else P334_NO_PROOF_OUTCOME
            if p334
            else P333_NO_PROOF_OUTCOME
            if p333
            else P332_NO_PROOF_OUTCOME
            if p332
            else P331_NO_PROOF_OUTCOME
            if p331
            else P330_NO_PROOF_OUTCOME
            if p330
            else P329_NO_PROOF_OUTCOME
            if p329
            else P328_NO_PROOF_OUTCOME
            if p328
            else typed_evidence.P327_FRAMED_EXEC_NO_PROOF_OUTCOME
            if p327
            else
            typed_evidence.P326_CONSOLE_NO_PROOF_OUTCOME
            if p326
            else typed_evidence.P325_ACM_PRIMARY_NO_PROOF_OUTCOME
            if p325
            else
            typed_evidence.P324_ACM_PRIMARY_NO_PROOF_OUTCOME
            if p324
            else typed_evidence.P323_ACM_PRIMARY_NO_PROOF_OUTCOME
        )
        projection = state.get(
            typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY
        )
        if not isinstance(projection, dict):
            raise F1LiveError(f"{label} candidate arrival proof is missing")
        proof = projection.get("proof") is True
        if proof:
            if (
                result["verdict"] != success_verdict
                or result["outcome_class"] != success_outcome
                or journal.state() != "CLOSED"
                or names != list(core.TIMELINE)
                or state.get("candidate_completed") is not True
                or state.get("rollback_completed") is not True
                or result["recovery_required"] is not False
            ):
                raise F1LiveError(
                    f"{label} ACM-primary terminal semantics are incomplete"
                )
        elif (
            result["verdict"] != "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
            or result["outcome_class"]
            != no_proof_outcome
            or journal.state() != "CLOSED"
            or names != list(core.TIMELINE)
            or state.get("rollback_completed") is not True
            or result["recovery_required"] is not False
        ):
            raise F1LiveError(
                f"{label} ACM-primary no-proof semantics are incomplete"
            )
        return result
    if _p320_bundle(prepared.bundle) and state.get("final_verified") is True:
        projection = _p320_durable_projection(state)
        proof = projection.get("proof_class")
        if proof not in P320_OUTCOME_BY_PROOF_CLASS:
            raise F1LiveError("P3.20 durable proof class is invalid")
        if result["verdict"] != "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK":
            raise F1LiveError("P3.20 stock result cannot claim candidate proof")
        if result["outcome_class"] != P320_OUTCOME_BY_PROOF_CLASS[proof]:
            raise F1LiveError("P3.20 stock outcome class differs from proof class")
        if (
            journal.state() != "CLOSED"
            or names != list(core.TIMELINE)
            or state.get("candidate_completed") is not True
            or state.get("rollback_completed") is not True
            or result["recovery_required"] is not False
        ):
            raise F1LiveError("P3.20 stock terminal semantics are incomplete")
        return result
    if _p321_bundle(prepared.bundle) and state.get("final_verified") is True:
        projection = _p320_durable_projection(state)
        proof = projection.get("proof_class")
        if proof not in P321_OUTCOME_BY_PROOF_CLASS:
            raise F1LiveError("P3.21 durable proof class is invalid")
        if result["verdict"] != "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK":
            raise F1LiveError("P3.21 stock result cannot claim candidate proof")
        if result["outcome_class"] != P321_OUTCOME_BY_PROOF_CLASS[proof]:
            raise F1LiveError("P3.21 stock outcome class differs from proof class")
        if (
            journal.state() != "CLOSED"
            or names != list(core.TIMELINE)
            or state.get("candidate_completed") is not True
            or state.get("rollback_completed") is not True
            or result["recovery_required"] is not False
        ):
            raise F1LiveError("P3.21 stock terminal semantics are incomplete")
        return result
    if _p322_bundle(prepared.bundle) and state.get("final_verified") is True:
        projection = _p320_durable_projection(state)
        proof = projection.get("proof_class")
        if proof not in P322_OUTCOME_BY_PROOF_CLASS:
            raise F1LiveError("P3.22 durable proof class is invalid")
        if result["verdict"] != "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK":
            raise F1LiveError("P3.22 stock result cannot claim candidate proof")
        if result["outcome_class"] != P322_OUTCOME_BY_PROOF_CLASS[proof]:
            raise F1LiveError("P3.22 stock outcome class differs from proof class")
        if (
            journal.state() != "CLOSED"
            or names != list(core.TIMELINE)
            or state.get("candidate_completed") is not True
            or state.get("rollback_completed") is not True
            or result["recovery_required"] is not False
        ):
            raise F1LiveError("P3.22 stock terminal semantics are incomplete")
        return result
    if _p319_bundle(prepared.bundle) and state.get("final_verified") is True:
        projection = _p319_durable_projection(state)
        proof = projection.get("proof_class")
        if proof not in P319_OUTCOME_BY_PROOF_CLASS:
            raise F1LiveError("P3.19 durable proof class is invalid")
        if result["verdict"] != "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK":
            raise F1LiveError("P3.19 stock result cannot claim candidate proof")
        if result["outcome_class"] != P319_OUTCOME_BY_PROOF_CLASS[proof]:
            raise F1LiveError("P3.19 stock outcome class differs from proof class")
        if (
            journal.state() != "CLOSED"
            or names != list(core.TIMELINE)
            or state.get("candidate_completed") is not True
            or state.get("rollback_completed") is not True
            or result["recovery_required"] is not False
        ):
            raise F1LiveError("P3.19 stock terminal semantics are incomplete")
        return result
    observer_required = (
        prepared.bundle.manifest["observation"].get("candidate_observer")
        is not None
    )
    acm = state.get("candidate_observer_accepted") is True
    departed = state.get("download_endpoint_absent") is True
    guard_released = (
        state.get("candidate_observer_guard_released") is True
    )
    guard_status = state.get("candidate_observer_guard_release_status")
    guard_warning = state.get("candidate_observer_guard_warning")
    guard_supports_result = _observer_guard_supports_result(
        accepted=acm,
        status=guard_status,
        released=guard_released,
    )
    if observer_required and guard_warning != _guard_warning(guard_status):
        raise F1LiveError("F1 observer guard warning is inconsistent")
    if verdict == "PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK":
        if (
            journal.state() != "CLOSED"
            or names != list(core.TIMELINE)
            or state.get("candidate_completed") is not True
            or state.get("rollback_completed") is not True
            or state.get("final_verified") is not True
            or state.get("marker_accepted") is not True
            or result["recovery_required"] is not False
            or (
                observer_required
                and (
                    acm is not True
                    or departed is not True
                    or guard_supports_result is not True
                )
            )
        ):
            raise F1LiveError("F1 PASS semantics are incomplete")
    elif verdict == "DIAGNOSTIC_F1_V2_RETAINED_ONLY_ROLLED_BACK":
        if (
            not observer_required
            or journal.state() != "CLOSED"
            or names != list(core.TIMELINE)
            or state.get("candidate_completed") is not True
            or departed is not True
            or acm is not False
            or guard_released is not True
            or state.get("marker_accepted") is not True
            or state.get("rollback_completed") is not True
            or state.get("final_verified") is not True
            or result["recovery_required"] is not False
        ):
            raise F1LiveError("F1 retained-only diagnostic semantics are incomplete")
    elif verdict == "DIAGNOSTIC_F1_V2_ACM_ONLY_ROLLED_BACK":
        if (
            not observer_required
            or journal.state() != "CLOSED"
            or names != list(core.TIMELINE)
            or state.get("candidate_completed") is not True
            or departed is not True
            or acm is not True
            or guard_supports_result is not True
            or state.get("marker_accepted") is not False
            or state.get("rollback_completed") is not True
            or state.get("final_verified") is not True
            or result["recovery_required"] is not False
        ):
            raise F1LiveError("F1 ACM-only diagnostic semantics are incomplete")
    elif verdict == "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK":
        recovery_timeline = names == list(core.RECOVERY_TIMELINE)
        if (
            journal.state() != "CLOSED"
            or names not in (list(core.TIMELINE), list(core.RECOVERY_TIMELINE))
            or state.get("rollback_completed") is not True
            or state.get("final_verified") is not True
            or result["recovery_required"] is not False
            or (
                recovery_timeline
                and (
                    candidate_classification != "not-attempted"
                    or state.get("candidate_completed") is not False
                )
            )
            or (
                observer_required
                and guard_supports_result is True
                and state.get("candidate_completed") is True
                and departed is True
                and (
                    state.get("marker_accepted") is True
                    or acm is True
                )
            )
            or (
                not observer_required
                and state.get("candidate_completed") is True
                and state.get("marker_accepted") is True
            )
        ):
            raise F1LiveError("F1 no-proof semantics are incomplete")
        if observer_required and not guard_supports_result and result[
            "outcome_class"
        ] != _guard_release_failure_outcome(
            guard_status
        ):
            raise F1LiveError("F1 guard failure outcome is inconsistent")
    elif verdict == "RECOVERY_REQUIRED_F1_V2_ROLLBACK_NOT_VERIFIED":
        if journal.state() != "RECOVERY_DOWNLOAD" or result[
            "recovery_required"
        ] is not True:
            raise F1LiveError("F1 recovery-required semantics are invalid")
    elif verdict in {
        "FAIL_F1_V2_ODIN_LOCAL_PARSE_NO_DEVICE_SESSION",
        "FAIL_F1_V2_PRE_CANDIDATE_DOWNLOAD",
    }:
        if journal.state() != "ABORTED" or result["recovery_required"] is not False:
            raise F1LiveError("F1 pre-candidate abort semantics are invalid")
    else:
        raise F1LiveError("unknown F1 live verdict")
    return result


def _events(journal: core.Journal) -> list[str]:
    return [
        item["action"] for item in journal.records() if item["kind"] == "event"
    ]


def _p300_recovery_process_cleanup(
    prepared: PreparedRun,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    binding_path = prepared.run_dir / "p300-usb-trace-binding.json"
    binding = p300_usb_trace.verify_binding(
        _read_json(binding_path, "P3.00 USB trace binding")
    )
    owner_path = _p300_process_owner_path(prepared)
    owner_receipt = None
    expected_group = None
    if owner_path.exists() or owner_path.is_symlink():
        owner = _validate_p300_process_owner(
            prepared,
            binding,
            _read_json(owner_path, "P3.00 USB trace process owner"),
        )
        owner_receipt = _receipt(owner_path, "P3.00 USB trace process owner")
        if owner["status"] == "launched":
            expected_group = owner["leader"]["process_group_id"]
    cleanup = _p300_cleanup_owned_processes(
        binding, expected_group=expected_group
    )
    return owner_receipt, cleanup


def _global_registry_recovery_state(
    prepared: PreparedRun,
    *,
    journal_state: str | None = None,
    request_identity: Mapping[str, Any] | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """Read global evidence without making registry repair a rollback gate."""

    claim_path = _candidate_registry_receipt_path(prepared, "claim")
    claim_intent = _candidate_registry_intent_path(prepared, "claim")
    local_claim = None
    if claim_path.exists() and not claim_path.is_symlink():
        local_claim = _read_json(claim_path, "candidate global claim receipt")
    local_claim_evidence = local_claim is not None
    local_claim_intent = claim_intent.exists() and not claim_intent.is_symlink()
    identity_fields = (
        "candidate_key", "target_profile_sha256", "target_key",
        "candidate_ap_sha256", "candidate_ap_size", "boot_member_name",
        "boot_member_size", "boot_member_sha256", "manifest_id", "run_id",
        "approval_binding_sha256",
    )
    try:
        identity = (
            dict(request_identity)
            if request_identity is not None
            else _candidate_registry_identity(prepared)
        )
        active = consumed_registry.active_claim(prepared.root, identity["candidate_key"])
    except (F1LiveError, consumed_registry.RegistryError):
        if local_claim_evidence or local_claim_intent:
            return "claimed-uncertain", local_claim
        if journal_state in {"CANDIDATE_FLASHED", "OBSERVED", "RECOVERY_DOWNLOAD", "ROLLBACK_FLASHED", "HEALTH_VERIFIED"}:
            return "claimed-uncertain", None
        return "registry-unavailable-preclaim", None
    if active is not None:
        if any(active.get(field) != identity.get(field) for field in identity_fields):
            return "foreign-claim", active
        return "claimed", active
    if local_claim is not None:
        record = local_claim.get("record") if isinstance(local_claim, dict) else None
        if not isinstance(record, dict) or any(
            record.get(field) != identity.get(field) for field in identity_fields
        ):
            return "foreign-claim", record
        return "claimed-uncertain", local_claim
    if local_claim_intent:
        return "claim-intent-only", None
    return "none", None


def _download_request_intent(
    prepared: PreparedRun,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    path = prepared.run_dir / "candidate-download-request-intent.json"
    if path.is_symlink():
        raise F1LiveError("candidate Download request intent is indirect")
    if not path.exists():
        return None
    expected_identity = _bound_candidate_registry_identity(prepared)
    value = _read_json(path, "candidate Download request intent")
    expected = {
        "schema": DOWNLOAD_REQUEST_INTENT_SCHEMA,
        "candidate_identity": expected_identity,
    }
    if value != expected:
        raise F1LiveError("candidate Download request intent differs from its binding")
    return expected_identity, _receipt(path, "candidate Download request intent")


def _validate_request_claim_intent(
    prepared: PreparedRun, identity: Mapping[str, Any]
) -> bool:
    path = _candidate_registry_intent_path(prepared, "claim")
    if path.is_symlink():
        raise F1LiveError("candidate global claim intent is indirect")
    if not path.exists():
        return False
    if _read_json(path, "candidate global claim intent") != _registry_intent_value(
        "claim", identity
    ):
        raise F1LiveError("candidate global claim intent differs")
    return True


def _request_cut_has_candidate_evidence(
    prepared: PreparedRun, journal: core.Journal
) -> bool:
    if any(prepared.run_dir.glob("candidate-attempt-*")):
        return True
    return any(
        record["action"] in {"candidate_transfer_attempt", "candidate_flash_start"}
        for record in journal.records()
        if record["kind"] in {"checkpoint", "event"}
    )


def _request_cut_transition(journal: core.Journal) -> dict[str, Any] | None:
    matches = [
        record
        for record in journal.records()
        if record["kind"] == "transition"
        and record["state"] == "RECOVERY_DOWNLOAD"
        and record["outcome"] in DOWNLOAD_REQUEST_RECOVERY_ACTIONS
    ]
    if len(matches) > 1:
        raise F1LiveError("Download request recovery transition is duplicated")
    return matches[0] if matches else None


def _request_cut_revalidation_park(journal: core.Journal) -> dict[str, Any] | None:
    matches = [
        record
        for record in journal.records()
        if record["kind"] == "checkpoint"
        and record["action"] == "download_request_revalidation"
    ]
    if len(matches) > 1:
        raise F1LiveError("Download request revalidation park is duplicated")
    return matches[0] if matches else None


def _request_cut_error(reason: str, exc: Exception) -> dict[str, Any]:
    error_type = type(exc).__name__
    encoded = f"{error_type}:{exc}".encode("utf-8", "replace")
    return {
        "reason": reason,
        "error_type": error_type,
        "error_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _request_intent_reason(exc: Exception) -> str:
    message = str(exc).lower()
    if "indirect" in message or "symlink" in message:
        return "request_intent_indirect"
    if "differs" in message or "binding" in message:
        return "request_intent_foreign"
    return "request_intent_malformed"


def _registry_reason(exc: Exception) -> str:
    message = str(exc).lower()
    if "indirect" in message or "symlink" in message:
        return "registry_evidence_indirect"
    if "differs" in message or "foreign" in message:
        return "registry_evidence_foreign"
    if "unavailable" in message:
        return "registry_unavailable"
    return "registry_evidence_malformed"


def _endpoint_reason(exc: Exception) -> str:
    message = str(exc).lower()
    if "ambiguous" in message:
        return "endpoint_ambiguous"
    if any(token in message for token in ("partial", "truncated", "incomplete")):
        return "endpoint_partial"
    if any(token in message for token in ("malformed", "invalid")):
        return "endpoint_malformed"
    if any(token in message for token in ("expired", "timed out", "timeout")):
        return "endpoint_absent"
    if any(token in message for token in ("foreign", "does not match", "canonical")):
        return "endpoint_foreign"
    if any(token in message for token in ("stale", "changed", "revalidation")):
        return "endpoint_stale"
    return "endpoint_observation_failed"


def _request_recovery_endpoint(endpoint: Endpoint) -> dict[str, Any]:
    if not isinstance(endpoint, Endpoint):
        raise F1LiveError("Download recovery endpoint is malformed")
    if transport.ODIN_DEVICE_RE.fullmatch(endpoint.device) is None:
        raise F1LiveError("Download recovery endpoint path is not canonical")
    if type(endpoint.sequence) is not int or endpoint.sequence < 1:
        raise F1LiveError("Download recovery endpoint sequence is invalid")
    if re.fullmatch(r"[0-9a-f]{64}", endpoint.identity_sha256) is None:
        raise F1LiveError("Download recovery endpoint identity is invalid")
    return {
        "device": endpoint.device,
        "sequence": endpoint.sequence,
        "identity_sha256": endpoint.identity_sha256,
    }


def _request_cut_details(
    *,
    request_receipt: Mapping[str, Any],
    identity: Mapping[str, Any] | None,
    global_state: str,
    endpoint: Mapping[str, Any] | None,
    failure: Mapping[str, Any] | None,
) -> dict[str, Any]:
    exact = endpoint is not None
    if exact is (failure is not None):
        raise F1LiveError("Download request recovery observation is incomplete")
    return {
        "recovery_only": True,
        "request_intent": dict(request_receipt),
        "candidate_identity_sha256": (
            core.json_sha256(dict(identity)) if identity is not None else None
        ),
        "global_state": global_state,
        "endpoint_authorized": exact,
        "endpoint": dict(endpoint) if endpoint is not None else None,
        "failure": dict(failure) if failure is not None else None,
        "candidate_claim_created_by_recovery": False,
        "candidate_attempt_synthesized_by_recovery": False,
    }


def _validate_stored_request_cut_details(
    details: Mapping[str, Any], *, exact: bool
) -> None:
    if set(details) != {
        "recovery_only",
        "request_intent",
        "candidate_identity_sha256",
        "global_state",
        "endpoint_authorized",
        "endpoint",
        "failure",
        "candidate_claim_created_by_recovery",
        "candidate_attempt_synthesized_by_recovery",
    }:
        raise F1LiveError("Download request recovery details are malformed")
    digest = details.get("candidate_identity_sha256")
    if (
        details.get("recovery_only") is not True
        or not isinstance(details.get("request_intent"), dict)
        or not isinstance(details.get("global_state"), str)
        or not details["global_state"]
        or details.get("endpoint_authorized") is not exact
        or details.get("candidate_claim_created_by_recovery") is not False
        or details.get("candidate_attempt_synthesized_by_recovery") is not False
        or (
            digest is not None
            and re.fullmatch(r"[0-9a-f]{64}", str(digest)) is None
        )
    ):
        raise F1LiveError("Download request recovery details differ")
    endpoint = details.get("endpoint")
    failure = details.get("failure")
    if exact:
        if digest is None or not isinstance(endpoint, dict) or failure is not None:
            raise F1LiveError("exact Download request recovery details differ")
        try:
            _request_recovery_endpoint(Endpoint(**endpoint))
        except (TypeError, F1LiveError) as exc:
            raise F1LiveError("exact Download request endpoint differs") from exc
        return
    if endpoint is not None or not isinstance(failure, dict) or set(failure) != {
        "reason",
        "error_type",
        "error_sha256",
    }:
        raise F1LiveError("parked Download request recovery details differ")
    if (
        not isinstance(failure.get("reason"), str)
        or not failure["reason"]
        or not isinstance(failure.get("error_type"), str)
        or not failure["error_type"]
        or re.fullmatch(r"[0-9a-f]{64}", str(failure.get("error_sha256"))) is None
    ):
        raise F1LiveError("parked Download request recovery failure differs")


def _validate_request_cut_details(
    details: Mapping[str, Any],
    *,
    exact: bool,
    request_receipt: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> None:
    _validate_stored_request_cut_details(details, exact=exact)
    if (
        details.get("request_intent") != dict(request_receipt)
        or details.get("candidate_identity_sha256")
        != core.json_sha256(dict(identity))
    ):
        raise F1LiveError("Download request recovery binding differs")


def _park_download_request_cut(
    prepared: PreparedRun,
    journal: core.Journal,
    *,
    details: Mapping[str, Any],
) -> dict[str, Any]:
    journal.transition(
        "RECOVERY_DOWNLOAD",
        "download_request_cut_recovery_parked",
        dict(details),
    )
    return _result(
        prepared,
        journal,
        "RECOVERY_REQUIRED_F1_V2_ROLLBACK_NOT_VERIFIED",
        "download_request_cut_recovery_parked",
        True,
    )


def _recover_download_request_cut(
    prepared: PreparedRun,
    backend: LiveBackend,
    journal: core.Journal,
) -> dict[str, Any] | None:
    state = journal.state()
    if state not in {
        "APPROVED",
        "DOWNLOAD_IDENTIFIED",
        "RECOVERY_DOWNLOAD",
        "ROLLBACK_FLASHED",
        "HEALTH_VERIFIED",
    }:
        return None
    if _p300_bundle(prepared.bundle):
        _p300_reconcile_before_candidate(prepared, journal)
    transition = _request_cut_transition(journal)
    has_candidate_evidence = _request_cut_has_candidate_evidence(
        prepared, journal
    )
    if transition is not None and has_candidate_evidence:
        raise F1LiveError(
            "durable Download request recovery has candidate evidence"
        )
    if has_candidate_evidence:
        return None
    if state == "RECOVERY_DOWNLOAD" and transition is None:
        return None
    if (
        transition is not None
        and transition["outcome"] == "download_request_cut_recovery_parked"
    ):
        _validate_stored_request_cut_details(transition["details"], exact=False)
        return _result(
            prepared,
            journal,
            "RECOVERY_REQUIRED_F1_V2_ROLLBACK_NOT_VERIFIED",
            "download_request_cut_recovery_parked",
            True,
        )
    revalidation_park = _request_cut_revalidation_park(journal)
    if revalidation_park is not None:
        if (
            transition is None
            or transition["outcome"]
            != "download_request_cut_recovery_exact"
        ):
            raise F1LiveError(
                "Download request revalidation park lacks an exact transition"
            )
        _validate_stored_request_cut_details(transition["details"], exact=True)
        return _result(
            prepared,
            journal,
            "RECOVERY_REQUIRED_F1_V2_ROLLBACK_NOT_VERIFIED",
            "download_request_cut_endpoint_revalidation_parked",
            True,
        )
    if (
        transition is not None
        and transition["outcome"] == "download_request_cut_recovery_exact"
        and (
            state in {"ROLLBACK_FLASHED", "HEALTH_VERIFIED"}
            or "rollback_flash_start" in _events(journal)
        )
    ):
        _validate_stored_request_cut_details(transition["details"], exact=True)
        endpoint_dir = prepared.run_dir / "odin-endpoints"
        with backend.endpoint_session(endpoint_dir) as lease:
            return _finish_rollback(
                prepared, backend, journal, endpoint_dir, lease
            )

    request_path = prepared.run_dir / "candidate-download-request-intent.json"
    if not request_path.exists() and not request_path.is_symlink():
        if transition is not None:
            raise F1LiveError(
                "durable Download request recovery lost its request intent"
            )
        return None

    try:
        request = _download_request_intent(prepared)
        if request is None:
            return None
        identity, request_receipt = request
    except Exception as exc:
        if state == "RECOVERY_DOWNLOAD":
            raise F1LiveError(
                "durable Download request recovery lost its request binding"
            ) from exc
        witness = {
            "schema": "device_action_f1_download_request_intent_observation_v1",
            "path": str(request_path),
            **_request_cut_error(_request_intent_reason(exc), exc),
        }
        return _park_download_request_cut(
            prepared,
            journal,
            details=_request_cut_details(
                request_receipt=witness,
                identity=None,
                global_state="request-intent-invalid",
                endpoint=None,
                failure=_request_cut_error(_request_intent_reason(exc), exc),
            ),
        )

    try:
        claim_receipt = _candidate_registry_receipt_path(prepared, "claim")
        if claim_receipt.is_symlink():
            raise F1LiveError("candidate global claim receipt is indirect")
        _validate_request_claim_intent(prepared, identity)
        global_state, _global_receipt = _global_registry_recovery_state(
            prepared,
            journal_state=state,
            request_identity=identity,
        )
        if global_state == "foreign-claim":
            raise F1LiveError("foreign global candidate claim owner")
        if global_state == "registry-unavailable-preclaim":
            raise F1LiveError("global candidate registry is unavailable")
    except Exception as exc:
        if state == "RECOVERY_DOWNLOAD":
            raise F1LiveError(
                "durable Download request recovery lost its registry binding"
            ) from exc
        return _park_download_request_cut(
            prepared,
            journal,
            details=_request_cut_details(
                request_receipt=request_receipt,
                identity=identity,
                global_state="registry-evidence-invalid",
                endpoint=None,
                failure=_request_cut_error(_registry_reason(exc), exc),
            ),
        )

    if transition is not None:
        exact = transition["outcome"] == "download_request_cut_recovery_exact"
        _validate_request_cut_details(
            transition["details"],
            exact=exact,
            request_receipt=request_receipt,
            identity=identity,
        )
        if not exact:
            return _result(
                prepared,
                journal,
                "RECOVERY_REQUIRED_F1_V2_ROLLBACK_NOT_VERIFIED",
                "download_request_cut_recovery_parked",
                True,
            )

    endpoint_dir = prepared.run_dir / "odin-endpoints"
    with backend.endpoint_session(endpoint_dir) as lease:
        if transition is not None and "rollback_flash_start" in _events(journal):
            return _finish_rollback(
                prepared, backend, journal, endpoint_dir, lease
            )
        try:
            endpoint = backend.wait_download(
                prepared, endpoint_dir, lease, ROLLBACK_WAIT_SEC
            )
            endpoint_value = _request_recovery_endpoint(endpoint)
        except Exception as exc:
            failure = _request_cut_error(_endpoint_reason(exc), exc)
            if transition is not None:
                journal.checkpoint(
                    "download_request_revalidation", "parked", failure
                )
                return _result(
                    prepared,
                    journal,
                    "RECOVERY_REQUIRED_F1_V2_ROLLBACK_NOT_VERIFIED",
                    "download_request_cut_endpoint_revalidation_parked",
                    True,
                )
            return _park_download_request_cut(
                prepared,
                journal,
                details=_request_cut_details(
                    request_receipt=request_receipt,
                    identity=identity,
                    global_state=global_state,
                    endpoint=None,
                    failure=failure,
                ),
            )
        if transition is None:
            details = _request_cut_details(
                request_receipt=request_receipt,
                identity=identity,
                global_state=global_state,
                endpoint=endpoint_value,
                failure=None,
            )
            journal.transition(
                "RECOVERY_DOWNLOAD",
                "download_request_cut_recovery_exact",
                details,
            )
        return _finish_rollback(
            prepared,
            backend,
            journal,
            endpoint_dir,
            lease,
            initial_endpoint=endpoint,
        )


def _normalize_recovery(prepared: PreparedRun, journal: core.Journal) -> bool:
    p300_lifecycle = None
    p300_session = None
    if _p300_bundle(prepared.bundle):
        p300_session, p300_lifecycle = _p300_recovery_session(
            prepared, journal
        )
    global_state, global_receipt = _global_registry_recovery_state(
        prepared, journal_state=journal.state()
    )
    if global_state == "foreign-claim":
        raise F1LiveError("foreign global candidate claim owner; recovery is blocked")
    current_before = _state(prepared)
    candidate_result_path = prepared.run_dir / "candidate-attempt-01.result.json"
    if candidate_result_path.exists() and not candidate_result_path.is_symlink():
        try:
            durable_candidate = _validate_transfer_result(prepared, "candidate", 1)
        except F1LiveError:
            durable_candidate = None
        if isinstance(durable_candidate, dict) and durable_candidate.get("classification") == "odin_local_parse_failure":
            current_before.update(
                {
                    "candidate_classification": "odin_local_parse_failure",
                    "candidate_completed": False,
                    "candidate_possible_device_session": False,
                }
            )
            _save_state(prepared, current_before)
    if current_before.get("candidate_classification") == "odin_local_parse_failure":
        # This is the only release path.  If the registry is unavailable,
        # retain the claim and continue rollback-only; never replay or wait.
        try:
            _validate_transfer_result(prepared, "candidate", 1)
            if current_before.get("candidate_possible_device_session") is False:
                _release_candidate_global(prepared)
                if journal.state() != "ABORTED":
                    journal.transition(
                        "ABORTED",
                        "odin_local_parse_failure",
                        {"device_session_started": False, "partition_transfer": False},
                    )
                return False
        except (F1LiveError, consumed_registry.RegistryError):
            global_state = "claimed-uncertain"
    if global_state in {"claimed", "claimed-uncertain"}:
        if not _reconcile_transfer_attempts(
            prepared, journal, "candidate", repair_orphan_start=True
        ):
            attempt, _prefix, _start = _begin_transfer_attempt(
                prepared, journal, "candidate"
            )
            current = _state(prepared)
            current.update(
                {
                    "candidate_classification": "odin_device_session_failure_or_unknown",
                    "candidate_completed": False,
                    "candidate_global_claim_recovered": True,
                }
            )
            _save_state(prepared, current)
            if journal.state() == "DOWNLOAD_IDENTIFIED":
                journal.event(
                    "candidate_flash_start",
                    {"attempt": attempt, "recovery_only": True},
                )
                journal.transition(
                    "CANDIDATE_FLASHED",
                    "global_candidate_claim_recovered_without_local_attempt",
                    {"recovery_only": True, "proof": False},
                )
                journal.event("candidate_flash_done", {"proof": False, "recovery_only": True})
                journal.transition(
                    "OBSERVED",
                    "global_candidate_claim_recovery_observation_skipped",
                    {"proof": False, "recovery_only": True},
                )
                journal.event("candidate_boot_ready", {"proof": False, "recovery_only": True})
            if _p300_bundle(prepared.bundle) and p300_session is not None:
                owner_receipt, cleanup = p300_lifecycle
                current = _state(prepared)
                if (
                    p300_session.result is not None
                    and p300_session.integrity is not None
                ):
                    current["p300_usb_trace"] = p300_session.captured_state()
                    _save_state(prepared, current)
                    p300_session.finalize()
                else:
                    current["p300_usb_trace"] = {
                        "status": "unknown",
                        "reason": "recovery:interrupted-candidate-window",
                        "binding": prepared.prepared["p300_usb_trace_binding"],
                        "process_owner": owner_receipt,
                        "process_cleanup": cleanup,
                        "host_axis": "UNKNOWN",
                        "device_result_authoritative": True,
                    }
                    _save_state(prepared, current)
            return True
    attempt_count = _reconcile_transfer_attempts(
        prepared, journal, "candidate", repair_orphan_start=True
    )
    if global_state == "claim-intent-only":
        # A claim intent is not a claim.  Never synthesize a consumed attempt
        # from an intent-only cut; the next recovery remains pre-candidate.
        return False
    if attempt_count and global_state not in {"claimed", "claimed-uncertain"}:
        claim_path = _candidate_registry_receipt_path(prepared, "claim")
        claim_intent = _candidate_registry_intent_path(prepared, "claim")
        if not (claim_path.exists() or claim_intent.exists()):
            # The local attempt was durable, but the global consumed boundary
            # was never reached; no backend call may be inferred or replayed.
            return False
    if _p300_bundle(prepared.bundle):
        assert p300_lifecycle is not None
        owner_receipt, cleanup = p300_lifecycle
        current = _state(prepared)
        trace = current.get("p300_usb_trace")
        if not isinstance(trace, dict) or trace.get("status") != "verified":
            adopted = (
                p300_session is not None
                and p300_session.result is not None
                and p300_session.integrity is not None
                and attempt_count > 0
                and p300_session.failure_reason is None
            )
            if adopted:
                current["p300_usb_trace"] = p300_session.captured_state()
            else:
                current["p300_usb_trace"] = {
                    "status": "unknown",
                    "reason": (
                        p300_session.failure_reason
                        if p300_session is not None
                        and p300_session.failure_reason is not None
                        else "recovery:interrupted-candidate-window"
                    ),
                    "binding": prepared.prepared["p300_usb_trace_binding"],
                    "process_owner": owner_receipt,
                    "process_cleanup": cleanup,
                    "host_axis": "UNKNOWN",
                    "device_result_authoritative": True,
                }
            try:
                _save_state(prepared, current)
            except Exception:
                pass
    events = _events(journal)
    if not attempt_count:
        if "candidate_flash_start" in events:
            raise F1LiveError("candidate event exists without an attempt ledger")
        return False
    if _p318_bundle(prepared.bundle):
        topology_receipt = _p318_interrupted_candidate_raw(prepared)
        topology_state = _state(prepared)
        retained = topology_state.get("p318_candidate_topology_raw")
        if retained is not None and retained != topology_receipt:
            raise F1LiveError("P3.18 recovered topology raw receipt differs")
        if retained is None:
            topology_state["p318_candidate_topology_raw"] = topology_receipt
            _save_state(prepared, topology_state)
    if "candidate_flash_start" not in events:
        if journal.state() != "DOWNLOAD_IDENTIFIED":
            raise F1LiveError("candidate attempt lacks its timeline start")
        journal.event(
            "candidate_flash_start", {"attempt": attempt_count, "resumed": True}
        )
    current = _state(prepared)
    if current.get("candidate_classification") == "not-attempted":
        current.update(
            {
                "candidate_classification": "odin_device_session_failure_or_unknown",
                "candidate_completed": False,
            }
        )
        _save_state(prepared, current)
    state = journal.state()
    if state == "DOWNLOAD_IDENTIFIED":
        journal.transition(
            "CANDIDATE_FLASHED",
            "interrupted_candidate_outcome_unknown",
            {"partition_transfer_possible": True, "proof": False},
        )
        journal.event("candidate_flash_done", {"proof": False, "resumed": True})
        state = "CANDIDATE_FLASHED"
    if state == "CANDIDATE_FLASHED":
        if "candidate_flash_done" not in _events(journal):
            journal.event("candidate_flash_done", {"proof": False, "resumed": True})
        observer_spec = prepared.bundle.manifest["observation"].get(
            "candidate_observer"
        )
        proof = False
        details: dict[str, Any] = {"proof": False}
        if observer_spec is not None:
            durable = _reopen_candidate_observation(prepared)
            guard_release = _reopen_candidate_guard_release(prepared)
            current = _state(prepared)
            current.update(
                {
                    "download_endpoint_absent": durable[
                        "download_endpoint_absent"
                    ],
                    "candidate_observer_classification": durable[
                        "classification"
                    ],
                    "candidate_observer_accepted": durable["accepted"],
                    "candidate_observer_receipt_sha256": durable[
                        "receipt_sha256"
                    ],
                    "candidate_observer_guard_release_status": guard_release[
                        "status"
                    ],
                    "candidate_observer_guard_released": guard_release[
                        "released"
                    ],
                    "candidate_observer_guard_warning": guard_release[
                        "warning"
                    ],
                    "candidate_observer_guard_release_receipt_sha256": (
                        guard_release["receipt_sha256"]
                    ),
                }
            )
            if _p335_bundle(prepared.bundle):
                current.update(_p332_proof_state(durable))
                current.update(
                    {
                        "preauth_diagnostics": durable["preauth_diagnostics"],
                        "rng_eagain_retries": durable["rng_eagain_retries"],
                        "partial_sessions": durable["partial_sessions"],
                        "p335_authenticated_attended_resident": durable[
                            "p335_authenticated_attended_resident"
                        ],
                    }
                )
            elif _p334_bundle(prepared.bundle) or _p333_bundle(prepared.bundle) or _p332_bundle(prepared.bundle):
                current.update(_p332_proof_state(durable))
                current.update(
                    {
                        "preauth_diagnostics": durable["preauth_diagnostics"],
                        "rng_eagain_retries": durable["rng_eagain_retries"],
                        "partial_sessions": durable["partial_sessions"],
                    }
                )
            elif _p331_bundle(prepared.bundle):
                current.update(_p331_proof_state(durable))
                current.update(
                    {
                        "preauth_diagnostics": durable["preauth_diagnostics"],
                        "rng_eagain_retries": durable["rng_eagain_retries"],
                        "partial_sessions": durable["partial_sessions"],
                    }
                )
            elif _p328_bundle(prepared.bundle):
                current.update(_p328_proof_state(durable))
                if _p330_bundle(prepared.bundle):
                    current.update(
                        {
                            "preauth_diagnostics": durable["preauth_diagnostics"],
                            "rng_eagain_retries": durable["rng_eagain_retries"],
                            "partial_exchange": durable["partial_exchange"],
                        }
                    )
            elif _p327_bundle(prepared.bundle):
                current.update(
                    {
                        "pid1_framed_exec_proof": durable[
                            "pid1_framed_exec_proof"
                        ],
                        "busybox_ash_command_proof": durable[
                            "busybox_ash_command_proof"
                        ],
                        "framed_session_closed": durable[
                            "framed_session_closed"
                        ],
                        "interactive_pty_proof": durable[
                            "interactive_pty_proof"
                        ],
                        "caller_selected_command": durable[
                            "caller_selected_command"
                        ],
                    }
                )
            _save_state(prepared, current)
            proof = (
                current.get("candidate_completed") is True
                and durable["download_endpoint_absent"] is True
                and durable["accepted"] is True
                and _observer_guard_supports_result(
                    accepted=True,
                    status=guard_release["status"],
                    released=guard_release["released"],
                )
                and (
                    _p335_proof_ok(durable)
                    if _p335_bundle(prepared.bundle)
                    else _p332_proof_ok(durable)
                    if _p334_bundle(prepared.bundle) or _p333_bundle(prepared.bundle) or _p332_bundle(prepared.bundle)
                    else _p331_proof_ok(durable)
                    if _p331_bundle(prepared.bundle)
                    else _p328_proof_ok(durable)
                    if _p328_bundle(prepared.bundle)
                    else not _p327_bundle(prepared.bundle)
                    or (
                        durable.get("pid1_framed_exec_proof") is True
                        and durable.get("busybox_ash_command_proof") is True
                        and durable.get("framed_session_closed") is True
                    )
                )
            )
            details = {
                "proof": proof,
                "candidate_observer_classification": durable[
                    "classification"
                ],
                "candidate_observer_receipt_sha256": durable[
                    "receipt_sha256"
                ],
                "candidate_observer_guard_release_status": guard_release[
                    "status"
                ],
                "candidate_observer_guard_released": guard_release[
                    "released"
                ],
                "candidate_observer_guard_warning": guard_release["warning"],
            }
        journal.transition(
            "OBSERVED",
            (
                "recovered_candidate_observation"
                if observer_spec is not None
                else "interrupted_candidate_no_proof"
            ),
            details,
        )
        journal.event(
            "candidate_boot_ready", {"proof": proof, "resumed": True}
        )
        state = "OBSERVED"
    if state == "OBSERVED" and "candidate_boot_ready" not in _events(journal):
        current = _state(prepared)
        proof = (
            current.get("candidate_completed") is True
            and current.get("download_endpoint_absent") is True
            and current.get("candidate_observer_accepted") is True
            and _observer_guard_supports_result(
                accepted=True,
                status=current.get(
                    "candidate_observer_guard_release_status"
                ),
                released=(
                    current.get("candidate_observer_guard_released") is True
                ),
            )
            and (
                _p335_proof_ok(current)
                if _p335_bundle(prepared.bundle)
                else _p332_proof_ok(current)
                if _p334_bundle(prepared.bundle) or _p333_bundle(prepared.bundle) or _p332_bundle(prepared.bundle)
                else _p331_proof_ok(current)
                if _p331_bundle(prepared.bundle)
                else _p328_proof_ok(current)
                if _p328_bundle(prepared.bundle)
                else not _p327_bundle(prepared.bundle)
                or (
                    current.get("pid1_framed_exec_proof") is True
                    and current.get("busybox_ash_command_proof") is True
                    and current.get("framed_session_closed") is True
                )
            )
        )
        journal.event(
            "candidate_boot_ready", {"proof": proof, "resumed": True}
        )
    if (
        p300_session is not None
        and p300_session.result is not None
        and p300_session.integrity is not None
    ):
        # The sidecar was adopted and sealed before candidate_boot_ready.  A
        # recovery finalizer may now verify the immutable witness/window; it
        # does not start a second sidecar or replay any device action.
        p300_session.finalize()
    return True


def _closed_terminal_classification(prepared: PreparedRun) -> tuple[str, str]:
    """Recompute a CLOSED terminal without reopening any backend."""

    current = _state(prepared)
    if _acm_primary_bundle(prepared.bundle):
        p335 = _p335_bundle(prepared.bundle)
        p334 = _p334_bundle(prepared.bundle)
        p333 = _p333_bundle(prepared.bundle)
        p332 = _p332_bundle(prepared.bundle)
        p331 = _p331_bundle(prepared.bundle)
        p330 = _p330_bundle(prepared.bundle)
        p329 = _p329_bundle(prepared.bundle)
        p328 = _p328_bundle(prepared.bundle)
        p327 = _p327_bundle(prepared.bundle)
        p326 = _p326_bundle(prepared.bundle)
        p325 = _p325_bundle(prepared.bundle)
        p324 = _p324_bundle(prepared.bundle)
        projection = current.get(
            typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY
        )
        if not isinstance(projection, dict):
            projection = _candidate_arrival_proof_projection(prepared, current)
        if isinstance(projection, dict) and projection.get("proof") is True:
            return (
                (
                    P335_SUCCESS_VERDICT
                    if p335
                    else P334_SUCCESS_VERDICT
                    if p334
                    else P333_SUCCESS_VERDICT
                    if p333
                    else P332_SUCCESS_VERDICT
                    if p332
                    else P331_SUCCESS_VERDICT
                    if p331
                    else P330_SUCCESS_VERDICT
                    if p330
                    else P329_SUCCESS_VERDICT
                    if p329
                    else P328_SUCCESS_VERDICT
                    if p328
                    else typed_evidence.P327_FRAMED_EXEC_VERDICT
                    if p327
                    else
                    typed_evidence.P326_CONSOLE_VERDICT
                    if p326
                    else typed_evidence.P325_ACM_PRIMARY_VERDICT
                    if p325
                    else
                    typed_evidence.P324_ACM_PRIMARY_VERDICT
                    if p324
                    else typed_evidence.P323_ACM_PRIMARY_VERDICT
                ),
                (
                    P335_SUCCESS_OUTCOME
                    if p335
                    else P334_SUCCESS_OUTCOME
                    if p334
                    else P333_SUCCESS_OUTCOME
                    if p333
                    else P332_SUCCESS_OUTCOME
                    if p332
                    else P331_SUCCESS_OUTCOME
                    if p331
                    else P330_SUCCESS_OUTCOME
                    if p330
                    else P329_SUCCESS_OUTCOME
                    if p329
                    else P328_SUCCESS_OUTCOME
                    if p328
                    else typed_evidence.P327_FRAMED_EXEC_OUTCOME
                    if p327
                    else
                    typed_evidence.P326_CONSOLE_OUTCOME
                    if p326
                    else typed_evidence.P325_ACM_PRIMARY_OUTCOME
                    if p325
                    else
                    typed_evidence.P324_ACM_PRIMARY_OUTCOME
                    if p324
                    else typed_evidence.P323_ACM_PRIMARY_OUTCOME
                ),
            )
        return (
            "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK",
            (
                P335_NO_PROOF_OUTCOME
                if p335
                else P334_NO_PROOF_OUTCOME
                if p334
                else P333_NO_PROOF_OUTCOME
                if p333
                else P332_NO_PROOF_OUTCOME
                if p332
                else P331_NO_PROOF_OUTCOME
                if p331
                else P330_NO_PROOF_OUTCOME
                if p330
                else P329_NO_PROOF_OUTCOME
                if p329
                else P328_NO_PROOF_OUTCOME
                if p328
                else typed_evidence.P327_FRAMED_EXEC_NO_PROOF_OUTCOME
                if p327
                else
                typed_evidence.P326_CONSOLE_NO_PROOF_OUTCOME
                if p326
                else typed_evidence.P325_ACM_PRIMARY_NO_PROOF_OUTCOME
                if p325
                else
                typed_evidence.P324_ACM_PRIMARY_NO_PROOF_OUTCOME
                if p324
                else typed_evidence.P323_ACM_PRIMARY_NO_PROOF_OUTCOME
            ),
        )
    if _p320_bundle(prepared.bundle):
        projection = _p320_durable_projection(current)
        proof = projection.get("proof_class")
        outcome = P320_OUTCOME_BY_PROOF_CLASS.get(proof)
        if outcome is not None:
            return "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK", outcome
        raise F1LiveError("P3.20 durable proof class is invalid")
    if _p321_bundle(prepared.bundle):
        projection = _p320_durable_projection(current)
        proof = projection.get("proof_class")
        outcome = P321_OUTCOME_BY_PROOF_CLASS.get(proof)
        if outcome is not None:
            return "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK", outcome
        raise F1LiveError("P3.21 durable proof class is invalid")
    if _p322_bundle(prepared.bundle):
        projection = _p320_durable_projection(current)
        proof = projection.get("proof_class")
        outcome = P322_OUTCOME_BY_PROOF_CLASS.get(proof)
        if outcome is not None:
            return "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK", outcome
        raise F1LiveError("P3.22 durable proof class is invalid")
    if _p319_bundle(prepared.bundle):
        projection = _p319_durable_projection(current)
        proof = projection.get("proof_class")
        outcome = P319_OUTCOME_BY_PROOF_CLASS.get(proof)
        if outcome is not None:
            return "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK", outcome
        raise F1LiveError("P3.19 durable proof class is invalid")
    marker = current.get("marker_accepted") is True
    candidate = current.get("candidate_completed") is True
    observer_required = (
        prepared.bundle.manifest["observation"].get("candidate_observer")
        is not None
    )
    acm = current.get("candidate_observer_accepted") is True
    departed = current.get("download_endpoint_absent") is True
    guard_released = current.get("candidate_observer_guard_released") is True
    guard_status = current.get("candidate_observer_guard_release_status")
    guard_supports_result = _observer_guard_supports_result(
        accepted=acm,
        status=guard_status,
        released=guard_released,
    )
    if observer_required and not guard_supports_result:
        return "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK", _guard_release_failure_outcome(guard_status)
    if marker and candidate and (not observer_required or (departed and acm)):
        return "PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK", "candidate_proven_rollback_verified"
    if observer_required and candidate and departed and marker and not acm:
        return "DIAGNOSTIC_F1_V2_RETAINED_ONLY_ROLLED_BACK", "retained_only_rollback_verified"
    if observer_required and candidate and departed and acm and not marker:
        return "DIAGNOSTIC_F1_V2_ACM_ONLY_ROLLED_BACK", "acm_only_rollback_verified"
    return "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK", "candidate_not_proven_rollback_verified"


def _finish_rollback(
    prepared: PreparedRun,
    backend: LiveBackend,
    journal: core.Journal,
    endpoint_dir: Path,
    lease: Any,
    *,
    initial_endpoint: Endpoint | None = None,
) -> dict[str, Any]:
    state = journal.state()
    rollback_endpoint: Endpoint | None = initial_endpoint
    if state == "OBSERVED":
        print(
            "Candidate observation is closed. Enter physical Download mode for "
            "the preapproved exact Magisk rollback.",
            file=os.sys.stderr,
            flush=True,
        )
        try:
            rollback_endpoint = backend.wait_download(
                prepared, endpoint_dir, lease, ROLLBACK_WAIT_SEC
            )
        except P318TopologyPark as exc:
            current = _state(prepared)
            current["p318_rollback_topology_parked"] = True
            current["p318_rollback_topology_error_sha256"] = hashlib.sha256(
                str(exc).encode("utf-8", "replace")
            ).hexdigest()
            _save_state(prepared, current)
            journal.transition(
                "RECOVERY_DOWNLOAD",
                "rollback_topology_rebind_required",
                {
                    "endpoint_authorized": False,
                    "rollback_transfer_started": False,
                },
            )
            return _result(
                prepared,
                journal,
                "RECOVERY_REQUIRED_F1_V2_ROLLBACK_NOT_VERIFIED",
                "rollback_topology_rebind_required",
                True,
            )
        journal.transition(
            "RECOVERY_DOWNLOAD",
            "rollback_endpoint_identified",
            {"endpoint_identity_sha256": rollback_endpoint.identity_sha256},
        )
        journal.event("rollback_flash_start", {"preapproved": True})
        state = "RECOVERY_DOWNLOAD"
    if state == "RECOVERY_DOWNLOAD":
        current = _state(prepared)
        topology_parked = (
            _p318_bundle(prepared.bundle)
            and current.get("p318_rollback_topology_parked") is True
        )
        if (
            _p318_bundle(prepared.bundle)
            and rollback_endpoint is None
            and "rollback_flash_start" not in _events(journal)
        ):
            try:
                rollback_endpoint = backend.wait_download(
                    prepared, endpoint_dir, lease, ROLLBACK_WAIT_SEC
                )
            except P318TopologyPark as exc:
                current["p318_rollback_topology_error_sha256"] = hashlib.sha256(
                    str(exc).encode("utf-8", "replace")
                ).hexdigest()
                _save_state(prepared, current)
                return _result(
                    prepared,
                    journal,
                    "RECOVERY_REQUIRED_F1_V2_ROLLBACK_NOT_VERIFIED",
                    "rollback_topology_rebind_required",
                    True,
                )
            if topology_parked:
                current["p318_rollback_topology_parked"] = False
                current.pop("p318_rollback_topology_error_sha256", None)
                _save_state(prepared, current)
        if "rollback_flash_start" not in _events(journal):
            journal.event(
                "rollback_flash_start", {"preapproved": True, "resumed": True}
            )
        consumed = _reconcile_transfer_attempts(
            prepared, journal, "rollback", repair_orphan_start=True
        )
        durable = (
            _validate_transfer_result(prepared, "rollback", consumed)
            if consumed
            else None
        )
        durable_completed = (
            durable is not None
            and durable.get("classification") == "odin_transfer_completed"
        )
        if durable_completed:
            current = _state(prepared)
            current.update(
                {
                    "rollback_classification": "odin_transfer_completed",
                    "rollback_completed": True,
                }
            )
            _save_state(prepared, current)
            journal.transition(
                "ROLLBACK_FLASHED",
                "rollback_transfer_completed",
                {"exact": True, "resumed_from_durable_result": True},
            )
            state = "ROLLBACK_FLASHED"
        else:
            if consumed >= MAX_ATTEMPTS:
                raise F1LiveError("rollback transfer attempt bound exceeded")
            try:
                endpoint = rollback_endpoint or backend.wait_download(
                    prepared, endpoint_dir, lease, ROLLBACK_WAIT_SEC
                )
            except P318TopologyPark as exc:
                current = _state(prepared)
                current["p318_rollback_topology_parked"] = True
                current["p318_rollback_topology_error_sha256"] = hashlib.sha256(
                    str(exc).encode("utf-8", "replace")
                ).hexdigest()
                _save_state(prepared, current)
                return _result(
                    prepared,
                    journal,
                    "RECOVERY_REQUIRED_F1_V2_ROLLBACK_NOT_VERIFIED",
                    "rollback_topology_rebind_required",
                    True,
                )
            attempt, prefix, _start = _begin_transfer_attempt(
                prepared, journal, "rollback"
            )
            rollback = backend.transfer(
                prepared,
                endpoint,
                "rollback",
                prepared.run_dir,
                attempt,
                prefix,
            )
            current = _state(prepared)
            current.update(
                {
                    "rollback_classification": rollback.classification,
                    "rollback_completed": rollback.completed,
                }
            )
            _save_state(prepared, current)
            if not rollback.completed:
                return _result(
                    prepared,
                    journal,
                    "RECOVERY_REQUIRED_F1_V2_ROLLBACK_NOT_VERIFIED",
                    "rollback_transfer_failed_or_unknown",
                    True,
                )
            journal.transition(
                "ROLLBACK_FLASHED", "rollback_transfer_completed", {"exact": True}
            )
            state = "ROLLBACK_FLASHED"
    if state == "ROLLBACK_FLASHED":
        if "rollback_flash_done" not in _events(journal):
            journal.event("rollback_flash_done", {"exact": True, "resumed": True})
        final = backend.verify_final(
            prepared, endpoint_dir, lease, prepared.run_dir
        )
        current = _state(prepared)
        current.update(
            {
                "final_verified": True,
                "marker_accepted": final["observer"]["accepted"],
                "final_evidence": final,
            }
        )
        if _p319_bundle(prepared.bundle):
            projection = final["observer"].get("p319_stock")
            if not isinstance(projection, dict):
                raise F1LiveError("P3.19 final stock projection is missing")
            current["p319_proof_class"] = projection["proof_class"]
            current["p319_stock"] = projection
        if _p320_bundle(prepared.bundle):
            projection = final["observer"].get("p320_stock")
            if not isinstance(projection, dict):
                raise F1LiveError("P3.20 final stock projection is missing")
            current["p320_proof_class"] = projection["proof_class"]
            current["p320_stock"] = projection
        if _p321_bundle(prepared.bundle):
            projection = final["observer"].get("p321_stock")
            if not isinstance(projection, dict):
                raise F1LiveError("P3.21 final stock projection is missing")
            current["p321_proof_class"] = projection["proof_class"]
            current["p321_stock"] = projection
        if _p322_bundle(prepared.bundle):
            projection = final["observer"].get("p322_stock")
            if not isinstance(projection, dict):
                raise F1LiveError("P3.22 final stock projection is missing")
            current["p322_proof_class"] = projection["proof_class"]
            current["p322_stock"] = projection
        if _p323_bundle(prepared.bundle):
            error = final["observer"].get("p323_stock_error")
            projection = final["observer"].get("p323_stock")
            if error is not None:
                if not isinstance(error, dict) or projection is not None:
                    raise F1LiveError("P3.23 supplemental parser failure is malformed")
                current["p323_stock_error"] = error
            else:
                if not isinstance(projection, dict):
                    raise F1LiveError("P3.23 final stock projection is missing")
                current["p323_proof_class"] = projection["proof_class"]
                current["p323_stock"] = projection
        if _p324_bundle(prepared.bundle):
            error = final["observer"].get("p324_stock_error")
            projection = final["observer"].get("p324_stock")
            if error is not None:
                if not isinstance(error, dict) or projection is not None:
                    raise F1LiveError(
                        "P3.24 supplemental parser failure is malformed"
                    )
                current["p324_stock_error"] = error
            else:
                if not isinstance(projection, dict):
                    raise F1LiveError("P3.24 final stock projection is missing")
                current["p324_proof_class"] = projection["proof_class"]
                current["p324_stock"] = projection
        if _p325_bundle(prepared.bundle):
            error = final["observer"].get("p325_stock_error")
            projection = final["observer"].get("p325_stock")
            if error is not None:
                if not isinstance(error, dict) or projection is not None:
                    raise F1LiveError(
                        "P3.25 supplemental parser failure is malformed"
                    )
                current["p325_stock_error"] = error
            else:
                if not isinstance(projection, dict):
                    raise F1LiveError("P3.25 final stock projection is missing")
                current["p325_proof_class"] = projection["proof_class"]
                current["p325_stock"] = projection
        if _p335_bundle(prepared.bundle):
            error = final["observer"].get("p335_stock_error")
            projection = final["observer"].get("p335_stock")
            if error is not None:
                if not isinstance(error, dict) or projection is not None:
                    raise F1LiveError(
                        "P3.35 supplemental parser failure is malformed"
                    )
                current["p335_stock_error"] = error
            else:
                if not isinstance(projection, dict):
                    raise F1LiveError("P3.35 final stock projection is missing")
                current["p335_proof_class"] = projection["proof_class"]
                current["p335_stock"] = projection
        if _p334_bundle(prepared.bundle):
            error = final["observer"].get("p334_stock_error")
            projection = final["observer"].get("p334_stock")
            if error is not None:
                if not isinstance(error, dict) or projection is not None:
                    raise F1LiveError(
                        "P3.34 supplemental parser failure is malformed"
                    )
                current["p334_stock_error"] = error
            else:
                if not isinstance(projection, dict):
                    raise F1LiveError("P3.34 final stock projection is missing")
                current["p334_proof_class"] = projection["proof_class"]
                current["p334_stock"] = projection
        if _p333_bundle(prepared.bundle):
            error = final["observer"].get("p333_stock_error")
            projection = final["observer"].get("p333_stock")
            if error is not None:
                if not isinstance(error, dict) or projection is not None:
                    raise F1LiveError(
                        "P3.33 supplemental parser failure is malformed"
                    )
                current["p333_stock_error"] = error
            else:
                if not isinstance(projection, dict):
                    raise F1LiveError("P3.33 final stock projection is missing")
                current["p333_proof_class"] = projection["proof_class"]
                current["p333_stock"] = projection
        if _p332_bundle(prepared.bundle):
            error = final["observer"].get("p332_stock_error")
            projection = final["observer"].get("p332_stock")
            if error is not None:
                if not isinstance(error, dict) or projection is not None:
                    raise F1LiveError(
                        "P3.32 supplemental parser failure is malformed"
                    )
                current["p332_stock_error"] = error
            else:
                if not isinstance(projection, dict):
                    raise F1LiveError("P3.32 final stock projection is missing")
                current["p332_proof_class"] = projection["proof_class"]
                current["p332_stock"] = projection
        if _p331_bundle(prepared.bundle):
            error = final["observer"].get("p331_stock_error")
            projection = final["observer"].get("p331_stock")
            if error is not None:
                if not isinstance(error, dict) or projection is not None:
                    raise F1LiveError(
                        "P3.31 supplemental parser failure is malformed"
                    )
                current["p331_stock_error"] = error
            else:
                if not isinstance(projection, dict):
                    raise F1LiveError("P3.31 final stock projection is missing")
                current["p331_proof_class"] = projection["proof_class"]
                current["p331_stock"] = projection
        if _p330_bundle(prepared.bundle):
            error = final["observer"].get("p330_stock_error")
            projection = final["observer"].get("p330_stock")
            if error is not None:
                if not isinstance(error, dict) or projection is not None:
                    raise F1LiveError(
                        "P3.30 supplemental parser failure is malformed"
                    )
                current["p330_stock_error"] = error
            else:
                if not isinstance(projection, dict):
                    raise F1LiveError("P3.30 final stock projection is missing")
                current["p330_proof_class"] = projection["proof_class"]
                current["p330_stock"] = projection
        if _p329_bundle(prepared.bundle):
            error = final["observer"].get("p329_stock_error")
            projection = final["observer"].get("p329_stock")
            if error is not None:
                if not isinstance(error, dict) or projection is not None:
                    raise F1LiveError(
                        "P3.29 supplemental parser failure is malformed"
                    )
                current["p329_stock_error"] = error
            else:
                if not isinstance(projection, dict):
                    raise F1LiveError("P3.29 final stock projection is missing")
                current["p329_proof_class"] = projection["proof_class"]
                current["p329_stock"] = projection
        if (
            _p328_bundle(prepared.bundle)
            and not _p329_bundle(prepared.bundle)
            and not _p330_bundle(prepared.bundle)
            and not _p331_bundle(prepared.bundle)
            and not _p332_bundle(prepared.bundle)
            and not _p333_bundle(prepared.bundle)
            and not _p334_bundle(prepared.bundle)
            and not _p335_bundle(prepared.bundle)
        ):
            error = final["observer"].get("p328_stock_error")
            projection = final["observer"].get("p328_stock")
            if error is not None:
                if not isinstance(error, dict) or projection is not None:
                    raise F1LiveError(
                        "P3.28 supplemental parser failure is malformed"
                    )
                current["p328_stock_error"] = error
            else:
                if not isinstance(projection, dict):
                    raise F1LiveError("P3.28 final stock projection is missing")
                current["p328_proof_class"] = projection["proof_class"]
                current["p328_stock"] = projection
        if _p327_bundle(prepared.bundle):
            error = final["observer"].get("p327_stock_error")
            projection = final["observer"].get("p327_stock")
            if error is not None:
                if not isinstance(error, dict) or projection is not None:
                    raise F1LiveError(
                        "P3.27 supplemental parser failure is malformed"
                    )
                current["p327_stock_error"] = error
            else:
                if not isinstance(projection, dict):
                    raise F1LiveError("P3.27 final stock projection is missing")
                current["p327_proof_class"] = projection["proof_class"]
                current["p327_stock"] = projection
        elif _p326_bundle(prepared.bundle):
            error = final["observer"].get("p326_stock_error")
            projection = final["observer"].get("p326_stock")
            if error is not None:
                if not isinstance(error, dict) or projection is not None:
                    raise F1LiveError(
                        "P3.26 supplemental parser failure is malformed"
                    )
                current["p326_stock_error"] = error
            else:
                if not isinstance(projection, dict):
                    raise F1LiveError("P3.26 final stock projection is missing")
                current["p326_proof_class"] = projection["proof_class"]
                current["p326_stock"] = projection
        _save_state(prepared, current)
        journal.transition(
            "HEALTH_VERIFIED",
            "final_health_and_rollback_verified",
            {"marker_accepted": final["observer"]["accepted"]},
        )
        journal.event("rollback_boot_ready", {"healthy": True})
        journal.event("live_session_end", {"rollback_verified": True})
        state = "HEALTH_VERIFIED"
    if state == "HEALTH_VERIFIED":
        events = _events(journal)
        if "rollback_boot_ready" not in events:
            journal.event("rollback_boot_ready", {"healthy": True, "resumed": True})
            events = _events(journal)
        if "live_session_end" not in events:
            journal.event(
                "live_session_end", {"rollback_verified": True, "resumed": True}
            )
        current = _state(prepared)
        marker = current.get("marker_accepted") is True
        candidate = current.get("candidate_completed") is True
        observer_required = prepared.bundle.manifest["observation"].get("candidate_observer") is not None
        acm = current.get("candidate_observer_accepted") is True
        departed = current.get("download_endpoint_absent") is True
        guard_released = current.get("candidate_observer_guard_released") is True
        guard_status = current.get("candidate_observer_guard_release_status")
        guard_supports_result = _observer_guard_supports_result(accepted=acm, status=guard_status, released=guard_released)
        if observer_required and acm and (not candidate or not departed):
            raise F1LiveError(
                "candidate observer acceptance lacks transfer continuity"
            )
        journal.transition(
            "CLOSED",
            "run_complete",
            {
                "marker_accepted": marker,
                "candidate_observer_accepted": (
                    acm if observer_required else None
                ),
                "candidate_observer_guard_released": (
                    guard_released if observer_required else None
                ),
                "candidate_observer_guard_warning": (
                    current.get("candidate_observer_guard_warning")
                    if observer_required
                    else None
                ),
            },
        )
        verdict, outcome = _closed_terminal_classification(prepared)
        return _result(prepared, journal, verdict, outcome, False)
    raise F1LiveError(f"unsupported rollback resume state: {state}")


class _P300UsbTraceSession:
    def __init__(self, prepared: PreparedRun, journal: core.Journal):
        self.prepared = prepared
        self.journal = journal
        self.enabled = _p300_bundle(prepared.bundle)
        self.binding: dict[str, Any] | None = None
        self.process: subprocess.Popen[bytes] | None = None
        self.result: dict[str, Any] | None = None
        self.integrity: dict[str, Any] | None = None
        self.owner_token: str | None = None
        self.owner_receipt: dict[str, Any] | None = None
        self.cleanup: dict[str, Any] | None = None
        self.process_output: dict[str, Any] | None = None
        self.failure_reason: str | None = None
        self.closed = False
        # The observer ExitStack normally closes before the durable
        # candidate_boot_ready boundary.  Once the bounded observation is
        # durable, defer that cleanup callback so the trace can span the guard
        # release and be sealed immediately before candidate_boot_ready.
        self.defer_stack_close = False

    @property
    def output_dir(self) -> Path:
        return self.prepared.run_dir / "p300-usb-trace"

    def _save(self, value: dict[str, Any]) -> None:
        current = _state(self.prepared)
        current["p300_usb_trace"] = value
        _save_state(self.prepared, current)

    def _unknown(self, reason: str) -> None:
        if not self.enabled:
            return
        self.failure_reason = reason[:160]
        try:
            binding = self._binding()
            if self.cleanup is None:
                try:
                    self.cleanup = _p300_cleanup_owned_processes(binding)
                except Exception as exc:
                    self.cleanup = _p300_cleanup_failure(binding, exc)
            try:
                self._refresh_owner_receipt()
            except Exception:
                pass
            try:
                self._save(
                    {
                        "status": "unknown",
                        "reason": self.failure_reason,
                        "binding": self.prepared.prepared[
                            "p300_usb_trace_binding"
                        ],
                        "process_owner": self.owner_receipt,
                        "process_cleanup": self.cleanup,
                        "host_axis": "UNKNOWN",
                        "device_result_authoritative": True,
                    }
                )
            except Exception:
                pass
        except Exception:
            pass

    def observation_durable(self, current: dict[str, Any]) -> None:
        if not self.enabled:
            return
        try:
            _write_p300_observation_witness(self.prepared, current)
        except Exception as exc:
            self.failure_reason = f"witness:{type(exc).__name__}"

    def close_from_observer_stack(
        self,
        exc_type: type[BaseException] | None = None,
        _exc_value: BaseException | None = None,
        _traceback: Any = None,
    ) -> bool:
        if exc_type is not None or not self.defer_stack_close:
            self.close()
        return False

    def _binding(self) -> dict[str, Any]:
        if self.binding is None:
            self.binding = p300_usb_trace.verify_binding(
                _read_json(
                    self.prepared.run_dir / "p300-usb-trace-binding.json",
                    "P3.00 USB trace binding",
                )
            )
        return self.binding

    def _refresh_owner_receipt(self) -> None:
        path = _p300_process_owner_path(self.prepared)
        if path.is_file() and not path.is_symlink():
            self.owner_receipt = _receipt(
                path, "P3.00 USB trace process owner"
            )

    def _load_completed_capture(self) -> None:
        """Reopen a completed sidecar without making a device call.

        Recovery can run in a new host process, so it cannot use the original
        ``Popen`` object.  The binding and capture-directory verifier are the
        durable handoff in that case; the process owner/cleanup proof is
        supplied by the caller before this method is reached.
        """
        result_path = self.output_dir / "result.json"
        if not result_path.is_file() or result_path.is_symlink():
            raise F1LiveError("P3.00 USB trace result is not complete")
        self.result = _read_json(result_path, "P3.00 USB trace result")
        self.integrity = p300_usb_trace.verify_capture_directory(
            self._binding(),
            self.result,
            root=self.prepared.root,
            output_dir=self.output_dir,
        )

    def captured_state(self) -> dict[str, Any]:
        if self.result is None or self.integrity is None:
            raise F1LiveError("P3.00 USB trace capture is not loaded")
        value = {
            "status": "captured",
            "binding": self.prepared.prepared["p300_usb_trace_binding"],
            "result": _receipt(
                self.output_dir / "result.json",
                "P3.00 USB trace result",
            ),
            "capture_integrity": self.integrity,
            "process_owner": self.owner_receipt,
            "process_cleanup": self.cleanup,
            "host_axis": "PENDING",
            "device_result_authoritative": True,
        }
        if self.process_output is not None:
            value["process_output"] = self.process_output
        return value

    def adopt_completed_capture(
        self,
        owner_receipt: dict[str, Any] | None,
        cleanup: dict[str, Any],
    ) -> bool:
        """Adopt a sidecar that was stopped by recovery or a prior cut.

        Adoption is only a host-evidence operation.  It never re-arms the
        sidecar and never touches the device.  A failed cleanup proof is not a
        safe handoff because the result could still be changing underneath
        the verifier.
        """
        if not self.enabled:
            return False
        result_path = self.output_dir / "result.json"
        if not result_path.is_file() or result_path.is_symlink():
            return False
        if cleanup.get("verified") is not True:
            raise F1LiveError("P3.00 sidecar cleanup is not verified")
        self.owner_receipt = owner_receipt
        self.cleanup = cleanup
        self.binding = p300_usb_trace.verify_binding(
            _read_json(
                self.prepared.run_dir / "p300-usb-trace-binding.json",
                "P3.00 USB trace binding",
            )
        )
        self.owner_token = _p300_owner_token(self.binding)
        self._load_completed_capture()
        self.closed = True
        return True

    def start(self) -> None:
        if not self.enabled:
            return
        phase = "bind"
        try:
            binding_path = self.prepared.run_dir / "p300-usb-trace-binding.json"
            binding = _read_json(binding_path, "P3.00 USB trace binding")
            self.binding = p300_usb_trace.verify_binding(binding)
            self.owner_token = _p300_owner_token(self.binding)
            owner_path = _p300_process_owner_path(self.prepared)
            phase = "owner"
            _write_exclusive(
                owner_path,
                _p300_process_owner_value(self.prepared, self.binding),
            )
            self._refresh_owner_receipt()
            duration = min(
                usb_trace_sidecar.MAX_DURATION_SEC,
                max(
                    900,
                    self.prepared.bundle.manifest["observation"]["timeout_sec"]
                    + ODIN_TIMEOUT_SEC
                    + DOWNLOAD_WAIT_SEC
                    + 180,
                ),
            )
            phase = "spawn"
            self.process = subprocess.Popen(
                [
                    sys.executable,
                    str(Path(usb_trace_sidecar.__file__).resolve()),
                    "--output-dir",
                    str(self.output_dir),
                    "--duration-sec",
                    str(duration),
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.prepared.root,
                env={
                    "LC_ALL": "C",
                    "PATH": "/usr/bin:/bin",
                    usb_trace_sidecar.OWNER_ENV: self.owner_token,
                },
                start_new_session=True,
            )
            identity = _p300_wait_owned_identity(
                self.process, self.owner_token
            )
            owner_value = _p300_process_owner_value(
                self.prepared, self.binding, identity
            )
            _write_atomic(owner_path, owner_value)
            _validate_p300_process_owner(
                self.prepared,
                self.binding,
                _read_json(owner_path, "P3.00 USB trace process owner"),
            )
            self._refresh_owner_receipt()
            phase = "arm-receipt"
            deadline = time.monotonic() + 20
            required = (
                self.output_dir / "start.json",
                self.output_dir / "armed.json",
                self.output_dir / "kernel.log",
                self.output_dir / "udev.log",
            )
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise F1LiveError("P3.00 USB trace sidecar exited while arming")
                if all(path.is_file() and not path.is_symlink() for path in required):
                    start = _read_json(required[0], "P3.00 USB trace start")
                    armed = _read_json(required[1], "P3.00 USB trace armed")
                    owner_sha256 = _p300_owner_sha256(self.owner_token)
                    if (
                        start.get("schema") != usb_trace_sidecar.SCHEMA
                        or start.get("phase") != "start"
                        or start.get("owner_token_sha256") != owner_sha256
                        or start.get("device_actions") is not False
                        or start.get("opens_candidate_acm") is not False
                        or armed.get("schema") != usb_trace_sidecar.SCHEMA
                        or armed.get("phase") != "armed"
                        or armed.get("owner_token_sha256") != owner_sha256
                        or armed.get("process_group_id") != self.process.pid
                        or armed.get("session_id") != self.process.pid
                        or armed.get("device_actions") is not False
                        or armed.get("opens_candidate_acm") is not False
                        or not isinstance(armed.get("sources"), dict)
                        or set(armed["sources"]) != set(usb_trace_sidecar.SOURCE_COMMANDS)
                        or any(
                            not isinstance(value, dict)
                            or value.get("alive") is not True
                            or value.get("process_group_id") != self.process.pid
                            or value.get("session_id") != self.process.pid
                            for value in armed["sources"].values()
                        )
                    ):
                        raise F1LiveError("P3.00 USB trace start receipt differs")
                    self._save(
                        {
                            "status": "capturing",
                            "binding": self.prepared.prepared[
                                "p300_usb_trace_binding"
                            ],
                            "start": _receipt(
                                required[0], "P3.00 USB trace start"
                            ),
                            "armed": _receipt(
                                required[1], "P3.00 USB trace armed"
                            ),
                            "process_owner": self.owner_receipt,
                            "host_axis": "PENDING",
                            "device_result_authoritative": True,
                        }
                    )
                    return
                time.sleep(0.05)
            raise F1LiveError("P3.00 USB trace sidecar arm timed out")
        except Exception as exc:
            self.close()
            self._unknown(f"arm:{phase}:{type(exc).__name__}")

    def close(self) -> None:
        if self.closed or not self.enabled:
            return
        self.closed = True
        try:
            self._close_impl()
        except Exception as exc:
            self._unknown(f"close:{type(exc).__name__}")

    def _close_impl(self) -> None:
        capture_error: Exception | None = None
        stdout = b""
        stderr = b""
        try:
            if self.process is not None:
                if self.process.poll() is None:
                    self.process.terminate()
                try:
                    stdout, stderr = self.process.communicate(timeout=30)
                except subprocess.TimeoutExpired:
                    # A timed-out sidecar is still a live process-group
                    # boundary.  Bind the owner token and re-read the full
                    # group/session immediately before the destructive
                    # SIGKILL; a foreign-member race must record UNKNOWN and
                    # leave the group untouched for recovery.
                    try:
                        binding = self._binding()
                        token = _p300_owner_token(binding)
                        _p300_revalidate_group_before_kill(
                            token, self.process.pid
                        )
                    except Exception as exc:
                        capture_error = exc
                    else:
                        try:
                            os.killpg(self.process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        stdout, stderr = self.process.communicate(timeout=10)
                        raise F1LiveError(
                            "P3.00 USB trace sidecar did not stop"
                        )
            if self.process is not None and self.process.returncode != 0:
                raise F1LiveError(
                    "P3.00 USB trace sidecar process failed: "
                    f"{self.process.returncode}"
                )
        except (
            OSError,
            ValueError,
            F1LiveError,
            subprocess.SubprocessError,
        ) as exc:
            capture_error = exc
        try:
            binding = self._binding()
            try:
                self.cleanup = _p300_cleanup_owned_processes(
                    binding,
                    expected_group=(
                        self.process.pid if self.process is not None else None
                    ),
                )
            except Exception as exc:
                self.cleanup = _p300_cleanup_failure(binding, exc)
                if capture_error is None:
                    capture_error = exc
            try:
                self._refresh_owner_receipt()
            except Exception as exc:
                if capture_error is None:
                    capture_error = exc
        except Exception as exc:
            if capture_error is None:
                capture_error = exc
        if capture_error is not None or self.failure_reason is not None:
            reason = self.failure_reason or f"capture:{type(capture_error).__name__}"
            self._unknown(reason)
            return
        if self.process is None:
            # A recovery process may have stopped the durable sidecar group
            # without owning its Popen handle.  Reuse the completed capture
            # if it is present; do not invent a new capture or device action.
            result_path = self.output_dir / "result.json"
            if not result_path.is_file() or result_path.is_symlink():
                return
            try:
                self._load_completed_capture()
                self.process_output = None
                self._save(self.captured_state())
            except Exception as exc:
                self._unknown(f"capture:{type(exc).__name__}")
            return
        try:
            self._load_completed_capture()
            self.process_output = {
                "stdout_size": len(stdout),
                "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
                "stderr_size": len(stderr),
                "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            }
            self._save(self.captured_state())
        except Exception as exc:
            self._unknown(f"capture:{type(exc).__name__}")

    def finalize(self) -> None:
        if not self.enabled:
            return
        try:
            self.close()
        except Exception as exc:
            self._unknown(f"finalize-close:{type(exc).__name__}")
            return
        if self.failure_reason is not None:
            self._unknown(self.failure_reason)
            return
        if self.binding is None or self.result is None or self.integrity is None:
            return
        try:
            observation_witness, observation_witness_receipt = (
                _read_p300_observation_witness(self.prepared, self.binding)
            )
            same_attempt = p300_usb_trace.verify_same_attempt(
                self.binding,
                self.result,
                self.journal.records(),
                observation_witness,
            )
            self._save(
                {
                    "status": "verified",
                    "binding": self.prepared.prepared[
                        "p300_usb_trace_binding"
                    ],
                    "result": _receipt(
                        self.output_dir / "result.json",
                        "P3.00 USB trace result",
                    ),
                    "capture_integrity": self.integrity,
                    "same_attempt": same_attempt,
                    "observation_witness": observation_witness_receipt,
                    "process_owner": self.owner_receipt,
                    "process_cleanup": self.cleanup,
                    "host_axis": "AVAILABLE",
                    "device_result_authoritative": True,
                }
            )
        except Exception as exc:
            self._unknown(f"binding:{type(exc).__name__}")


def _p300_recovery_session(
    prepared: PreparedRun, journal: core.Journal
) -> tuple[_P300UsbTraceSession, tuple[dict[str, Any] | None, dict[str, Any]]]:
    """Stop/reopen a surviving P3.00 sidecar during host-only recovery."""
    try:
        lifecycle = _p300_recovery_process_cleanup(prepared)
    except Exception as exc:
        binding = p300_usb_trace.verify_binding(
            _read_json(
                prepared.run_dir / "p300-usb-trace-binding.json",
                "P3.00 USB trace binding",
            )
        )
        owner_path = _p300_process_owner_path(prepared)
        owner_receipt = None
        try:
            if owner_path.is_file() and not owner_path.is_symlink():
                owner_receipt = _receipt(
                    owner_path, "P3.00 USB trace process owner"
                )
        except Exception:
            pass
        lifecycle = (owner_receipt, _p300_cleanup_failure(binding, exc))
    session = _P300UsbTraceSession(prepared, journal)
    owner_receipt, cleanup = lifecycle
    previous_trace = _state(prepared).get("p300_usb_trace")
    if isinstance(previous_trace, dict) and isinstance(
        previous_trace.get("process_output"), dict
    ):
        session.process_output = previous_trace["process_output"]
    try:
        session.adopt_completed_capture(owner_receipt, cleanup)
    except Exception as exc:
        session.failure_reason = f"adopt:{type(exc).__name__}"
    return session, lifecycle


def _p300_reconcile_before_candidate(
    prepared: PreparedRun, journal: core.Journal
) -> None:
    """Reap a pre-candidate sidecar without treating it as a same-attempt proof."""
    session, lifecycle = _p300_recovery_session(prepared, journal)
    current = _state(prepared)
    trace = current.get("p300_usb_trace")
    if isinstance(trace, dict) and trace.get("status") == "verified":
        return
    owner_receipt, cleanup = lifecycle
    current["p300_usb_trace"] = {
        "status": "unknown",
        "reason": "recovery:before-candidate-window",
        "binding": prepared.prepared["p300_usb_trace_binding"],
        "process_owner": owner_receipt,
        "process_cleanup": cleanup,
        "host_axis": "UNKNOWN",
        "device_result_authoritative": True,
    }
    _save_state(prepared, current)


def _validate_p300_usb_trace_state(
    prepared: PreparedRun,
    state: dict[str, Any],
    records: list[dict[str, Any]],
) -> None:
    trace = state.get("p300_usb_trace")
    if not _p300_bundle(prepared.bundle):
        if trace is not None:
            raise F1LiveError("non-P3.00 run has USB trace state")
        return
    events = {
        record["action"] for record in records if record["kind"] == "event"
    }
    if not isinstance(trace, dict):
        if "candidate_flash_start" in events:
            raise F1LiveError("P3.00 candidate attempt lacks USB trace state")
        return
    status = trace.get("status")
    if status in {"capturing", "captured"}:
        if "candidate_boot_ready" in events:
            raise F1LiveError("P3.00 completed candidate lacks final USB trace state")
        return
    binding = p300_usb_trace.verify_binding(
        _read_json(
            prepared.run_dir / "p300-usb-trace-binding.json",
            "P3.00 USB trace binding",
        )
    )
    owner_receipt = trace.get("process_owner")
    owner_path = _p300_process_owner_path(prepared)
    if owner_receipt is None:
        if owner_path.exists() or owner_path.is_symlink():
            raise F1LiveError("P3.00 observer owner receipt is missing")
    else:
        if owner_receipt != _receipt(
            owner_path, "P3.00 USB trace process owner"
        ):
            raise F1LiveError("P3.00 observer owner receipt changed")
        _validate_p300_process_owner(
            prepared,
            binding,
            _read_json(owner_path, "P3.00 USB trace process owner"),
        )
    cleanup = _validate_p300_process_cleanup(
        binding,
        trace.get("process_cleanup"),
        require_verified=status == "verified",
    )
    if status == "unknown":
        if (
            set(trace)
            != {
                "status",
                "reason",
                "binding",
                "process_owner",
                "process_cleanup",
                "host_axis",
                "device_result_authoritative",
            }
            or not isinstance(trace["reason"], str)
            or not trace["reason"]
            or trace["binding"]
            != prepared.prepared["p300_usb_trace_binding"]
            or trace["host_axis"] != "UNKNOWN"
            or trace["device_result_authoritative"] is not True
        ):
            raise F1LiveError("P3.00 unknown USB trace state differs")
        return
    if status != "verified":
        raise F1LiveError("P3.00 USB trace status is invalid")
    if (
        set(trace)
        != {
            "status",
            "binding",
            "result",
            "capture_integrity",
            "same_attempt",
            "observation_witness",
            "process_owner",
            "process_cleanup",
            "host_axis",
            "device_result_authoritative",
        }
        or trace["binding"] != prepared.prepared["p300_usb_trace_binding"]
        or trace["host_axis"] != "AVAILABLE"
        or trace["device_result_authoritative"] is not True
        or "candidate_boot_ready" not in events
    ):
        raise F1LiveError("P3.00 verified USB trace state differs")
    result_path = prepared.run_dir / "p300-usb-trace/result.json"
    result = _read_json(result_path, "P3.00 USB trace result")
    if trace["result"] != _receipt(result_path, "P3.00 USB trace result"):
        raise F1LiveError("P3.00 USB trace result receipt changed")
    observation_witness, observation_witness_receipt = (
        _read_p300_observation_witness(prepared, binding)
    )
    if trace["observation_witness"] != observation_witness_receipt:
        raise F1LiveError("P3.00 observation witness receipt changed")
    try:
        integrity = p300_usb_trace.verify_capture_directory(
            binding,
            result,
            root=prepared.root,
            output_dir=prepared.run_dir / "p300-usb-trace",
        )
        same_attempt = p300_usb_trace.verify_same_attempt(
            binding, result, records, observation_witness
        )
    except p300_usb_trace.BindingError as exc:
        raise F1LiveError(str(exc)) from exc
    if (
        trace["capture_integrity"] != integrity
        or trace["same_attempt"] != same_attempt
        or trace["process_cleanup"] != cleanup
    ):
        raise F1LiveError("P3.00 USB trace durable verification changed")


def _seal_p300_before_candidate_boot_ready(
    trace_session: _P300UsbTraceSession,
    journal: core.Journal,
    proof: bool,
) -> None:
    """Close the passive sidecar before recording the window's end event."""
    trace_session.close()
    journal.event("candidate_boot_ready", {"proof": proof})
    trace_session.finalize()


def _run_deferred_p300_segment(
    trace_session: _P300UsbTraceSession,
    operation: Callable[[], Any],
) -> Any:
    """Run the post-observation segment with an exception cleanup fallback."""
    try:
        return operation()
    except BaseException:
        if trace_session.defer_stack_close:
            trace_session.defer_stack_close = False
            try:
                trace_session.close()
            except BaseException:
                # Preserve the original failure.  Recovery will re-open the
                # durable owner/capture state and perform the same bounded
                # cleanup without replaying a device action.
                pass
        raise


def _p335_resident_binding(
    prepared: PreparedRun, observation: Mapping[str, Any]
) -> dict[str, Any]:
    verification = prepared.bundle.receipt.get("observation_contract", {}).get(
        "verification"
    )
    closure = verification.get("ap_payload_closure") if isinstance(verification, dict) else None
    proof = observation.get("p335_authenticated_attended_resident")
    sessions = proof.get("sessions") if isinstance(proof, dict) else None
    if (
        not isinstance(closure, dict)
        or not isinstance(closure.get("boot_image"), dict)
        or not isinstance(sessions, list)
        or len(sessions) != p335_retained_observer.MAX_SESSIONS
        or not isinstance(sessions[0], dict)
    ):
        raise F1LiveError("P3.35 resident binding inputs are incomplete")
    topology_sha256 = observation.get("candidate_topology_sha256")
    if not isinstance(topology_sha256, str):
        raise F1LiveError("P3.35 resident topology binding is absent")
    return {
        "target": dict(p335_resident_session.TARGET),
        "topology": {"sha256": topology_sha256},
        "candidate": {
            "run_id": typed_evidence.P335_RUN_ID,
            "boot_sha256": closure["boot_image"]["sha256"],
            "ap_sha256": prepared.bundle.manifest["candidate_ap"]["sha256"],
        },
        "key": dict(typed_evidence.P335_AUTH_EXEC_AUTH_KEY_IDENTITY),
        "catalog": p335_resident_session.catalog_for(typed_evidence.P335_RUN_ID),
        "recovery": {
            "kind": "magisk_boot_only",
            "owner": "s22plus-fyg8-p335",
            "rollback_ap_sha256": prepared.bundle.manifest["rollback_ap"]["sha256"],
        },
        "per_boot_id": sessions[0]["boot_id_sha256"],
    }


def _finish_p335_candidate_window_before_guard_release(
    prepared: PreparedRun,
    journal: core.Journal,
    candidate: TransferOutcome,
    observation: dict[str, Any],
    trace_session: _P300UsbTraceSession,
) -> dict[str, Any]:
    """Durably reach OBSERVED, then publish the current-boot resident lease."""
    journal.transition(
        "OBSERVED", "bounded_candidate_observation_closed", observation
    )
    durable = _reopen_candidate_observation(prepared)
    proof = bool(
        candidate.completed
        and durable.get("download_endpoint_absent") is True
        and durable.get("accepted") is True
        and _p335_proof_ok(durable)
    )
    _seal_p300_before_candidate_boot_ready(trace_session, journal, proof)
    if not proof:
        return {"proof": False, "resident_session_active": False}

    resident_root = prepared.run_dir / "p335-resident-session"
    try:
        resident_root.mkdir(mode=0o700)
        descriptor = os.open(
            prepared.run_dir,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_CLOEXEC,
        )
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        records = journal.records()
        lease = p335_resident_session.ResidentLease.publish(
            resident_root,
            _p335_resident_binding(prepared, durable),
            {
                "state": "OBSERVED",
                "candidate_boot_ready": True,
                "journal_sha256": records[-1]["record_sha256"],
            },
        )
    except (OSError, p335_resident_session.LeaseError) as exc:
        raise F1LiveError("P3.35 resident lease publication failed") from exc
    snapshot = lease.snapshot()
    current = _state(prepared)
    current.update(
        {
            "resident_session_state": snapshot["state"],
            "resident_session_active": snapshot["state"] == "ACTIVE",
            "resident_lease_id": snapshot["lease_id"],
            "resident_lease_receipt": _receipt(
                resident_root / "lease.json", "P3.35 resident lease"
            ),
            "resident_guard_receipt": _receipt(
                resident_root / "lease.guard.json", "P3.35 resident guard"
            ),
            "resident_rollback_required": snapshot["rollback_required"],
        }
    )
    _save_state(prepared, current)
    return {
        "proof": True,
        "resident_session_active": True,
        "snapshot": snapshot,
    }


def _finish_p335_after_guard_release(
    prepared: PreparedRun,
    backend: LiveBackend,
    journal: core.Journal,
    endpoint_dir: Path,
    endpoint_lease: Any,
    pending: dict[str, Any],
) -> dict[str, Any]:
    guard_release = _reopen_candidate_guard_release(prepared)
    current = _state(prepared)
    current.update(
        {
            "candidate_observer_guard_release_status": guard_release["status"],
            "candidate_observer_guard_released": guard_release["released"],
            "candidate_observer_guard_warning": guard_release["warning"],
            "candidate_observer_guard_release_receipt_sha256": guard_release[
                "receipt_sha256"
            ],
        }
    )
    supported = _observer_guard_supports_result(
        accepted=pending["proof"],
        status=guard_release["status"],
        released=guard_release["released"] is True,
    )
    if pending["proof"] and not supported:
        try:
            p335_resident_session.ResidentLease.open(
                prepared.run_dir / "p335-resident-session"
            ).mark_drift("candidate observer guard release failed")
        except p335_resident_session.LeaseError:
            pass
        current["resident_session_active"] = False
        current["resident_rollback_required"] = True
    _save_state(prepared, current)
    if not pending["proof"] or not supported:
        return _finish_rollback(
            prepared, backend, journal, endpoint_dir, endpoint_lease
        )
    snapshot = p335_resident_session.ResidentLease.open(
        prepared.run_dir / "p335-resident-session"
    ).snapshot()
    return {
        "schema": "device_action_f1_p335_resident_active_v1",
        "verdict": "P335_RESIDENT_SESSION_ACTIVE",
        "outcome_class": "p335_current_boot_attended_resident_active",
        "manifest_id": prepared.bundle.manifest["manifest_id"],
        "run_id": prepared.bundle.manifest["run_id"],
        "ordinary_f1_state": "OBSERVED",
        "candidate_boot_ready": True,
        "resident_session": snapshot,
        "f1_closed": False,
        "rollback_completed": False,
        "recovery_required": False,
    }


def _p335_mark_resident_rollback_required(prepared: PreparedRun) -> None:
    resident_root = prepared.run_dir / "p335-resident-session"
    if not resident_root.exists() or resident_root.is_symlink():
        return
    try:
        lease = p335_resident_session.ResidentLease.open(resident_root)
        if lease.snapshot()["rollback_required"] is not True:
            lease.stop("F1 recovery requested")
    except p335_resident_session.LeaseError:
        # A partial or changed lease never blocks the already preapproved
        # exact rollback.  It only removes resident-action authority.
        pass
    current = _state(prepared)
    current["resident_session_active"] = False
    current["resident_rollback_required"] = True
    _save_state(prepared, current)


def _finish_candidate_window(
    prepared: PreparedRun,
    backend: LiveBackend,
    journal: core.Journal,
    endpoint_dir: Path,
    lease: Any,
    candidate: TransferOutcome,
    observation: dict[str, Any],
    trace_session: _P300UsbTraceSession,
) -> dict[str, Any]:
    if (
        prepared.bundle.manifest["observation"].get("candidate_observer")
        is not None
    ):
        guard_release = _reopen_candidate_guard_release(prepared)
        current = _state(prepared)
        current.update(
            {
                "candidate_observer_guard_release_status": guard_release[
                    "status"
                ],
                "candidate_observer_guard_released": guard_release[
                    "released"
                ],
                "candidate_observer_guard_warning": guard_release[
                    "warning"
                ],
                "candidate_observer_guard_release_receipt_sha256": (
                    guard_release["receipt_sha256"]
                ),
            }
        )
        _save_state(prepared, current)
        observation["candidate_observer_guard_released"] = guard_release[
            "released"
        ]
        observation["candidate_observer_guard_warning"] = guard_release[
            "warning"
        ]
        observation[
            "candidate_observer_guard_release_status"
        ] = guard_release["status"]
    journal.transition(
        "OBSERVED",
        "bounded_candidate_observation_closed",
        observation,
    )
    proof = (
        candidate.completed
        and observation.get("download_endpoint_absent") is True
        and (
            prepared.bundle.manifest["observation"].get(
                "candidate_observer"
            )
            is None
            or (
                observation.get("candidate_observer_accepted") is True
                and _observer_guard_supports_result(
                    accepted=True,
                    status=observation.get(
                        "candidate_observer_guard_release_status"
                    ),
                    released=(
                        observation.get("candidate_observer_guard_released")
                        is True
                    ),
                )
                and (
                    _p332_proof_ok(observation)
                    if _p334_bundle(prepared.bundle) or _p333_bundle(prepared.bundle) or _p332_bundle(prepared.bundle)
                    else _p331_proof_ok(observation)
                    if _p331_bundle(prepared.bundle)
                    else _p328_proof_ok(observation)
                    if _p328_bundle(prepared.bundle)
                    else not _p327_bundle(prepared.bundle)
                    or (
                        observation.get("pid1_framed_exec_proof") is True
                        and observation.get("busybox_ash_command_proof") is True
                        and observation.get("framed_session_closed") is True
                    )
                )
            )
        )
    )
    # Seal the passive trace immediately before the durable boot-ready event.
    # This keeps the capture alive through the complete bounded observation
    # while preserving the binding's end <= boot-ready ordering.  ``finalize``
    # only verifies the already sealed capture and cannot re-arm it.
    _seal_p300_before_candidate_boot_ready(trace_session, journal, proof)
    return _finish_rollback(
        prepared, backend, journal, endpoint_dir, lease
    )


def _execute_prepared_locked(
    prepared: PreparedRun,
    approval: str,
    backend: LiveBackend,
) -> dict[str, Any]:
    if approval != prepared.approval_token:
        raise F1LiveError("fresh F1 approval token mismatch")
    transaction = prepared.run_dir / "transaction"
    if transaction.exists() or transaction.is_symlink():
        raise F1LiveError("prepared run already has a transaction; use recovery")
    candidate_identity = _candidate_registry_identity(prepared)
    _preflight_candidate_global(prepared, candidate_identity)
    recheck = backend.recheck_android(
        prepared, _next_execute_preflight(prepared.run_dir)
    )
    journal = core.Journal.create(
        transaction,
        prepared.binding_sha256,
        {"host_only": False, "device_contact": True, "device_writes": False},
    )
    journal.event("live_session_start", {"prepared_recheck": recheck})
    journal.transition(
        "APPROVED",
        "fresh_exact_binding",
        {
            "approval_binding_sha256": prepared.binding_sha256,
            "rollback_preapproved": True,
        },
    )
    endpoint_dir = prepared.run_dir / "odin-endpoints"
    with backend.endpoint_session(endpoint_dir) as lease:
        p335_pending: dict[str, Any] | None = None
        with contextlib.ExitStack() as observer_stack:
            trace_session = _P300UsbTraceSession(prepared, journal)
            # Push the failure-aware cleanup before the observer context is
            # entered, so an observer __exit__ fault is still visible to the
            # sidecar cleanup callback after durable observation.
            observer_stack.push(trace_session.close_from_observer_stack)
            try:
                observer_session = observer_stack.enter_context(
                    backend.candidate_observer_session(prepared)
                )
            except Exception as exc:
                journal.transition(
                    "ABORTED",
                    "candidate_observer_arm_failed_before_candidate",
                    {
                        "error_type": type(exc).__name__,
                        "candidate_attempted": False,
                    },
                )
                trace_session.close()
                return _result(
                    prepared,
                    journal,
                    "FAIL_F1_V2_PRE_CANDIDATE_DOWNLOAD",
                    "candidate_observer_arm_failed_before_candidate",
                    False,
                )
            trace_session.start()
            try:
                request_intent = {
                    "schema": DOWNLOAD_REQUEST_INTENT_SCHEMA,
                    "candidate_identity": candidate_identity,
                }
                request_intent_path = prepared.run_dir / "candidate-download-request-intent.json"
                if request_intent_path.exists() or request_intent_path.is_symlink():
                    if _read_json(request_intent_path, "candidate Download request intent") != request_intent:
                        raise F1LiveError("candidate Download request intent differs")
                else:
                    _write_exclusive(request_intent_path, request_intent)
                backend.request_download(prepared)
            except Exception as exc:
                raise F1LiveError("BLOCKED_DOWNLOAD_REQUEST_CUT_RECOVERY: Download request outcome is uncertain; recovery is required") from exc
            try:
                endpoint = backend.wait_download(
                    prepared, endpoint_dir, lease, DOWNLOAD_WAIT_SEC
                )
            except Exception as exc:
                raise F1LiveError("BLOCKED_DOWNLOAD_REQUEST_CUT_RECOVERY: Download endpoint outcome is uncertain; recovery is required") from exc
            if _p324_lane_bundle(prepared.bundle):
                try:
                    backend.revalidate_candidate_lane(prepared)
                except Exception as exc:
                    raise F1LiveError(
                        "BLOCKED_DOWNLOAD_REQUEST_CUT_RECOVERY: P3.24 Type-C lane "
                        "changed before the candidate effect; recovery is required"
                    ) from exc
            endpoint_details = {
                "endpoint_identity_sha256": endpoint.identity_sha256
            }
            if _p324_lane_bundle(prepared.bundle):
                endpoint_details.update(
                    {
                        "p324_typec_lane_pre_effect_revalidated": True,
                        "p324_typec_lane_receipt_sha256": prepared.prepared[
                            "p324_typec_lane_binding"
                        ]["sha256"],
                    }
                )
            journal.transition(
                "DOWNLOAD_IDENTIFIED",
                "candidate_endpoint_identified",
                endpoint_details,
            )
            # Claim before allocating a local transfer attempt.  A cut after
            # the durable claim intent but before the registry claim therefore
            # remains claim-intent-only and cannot invent an attempt.
            _claim_candidate_global(prepared, candidate_identity)
            attempt, prefix, _start = _begin_transfer_attempt(
                prepared, journal, "candidate"
            )
            journal.event("candidate_flash_start", {"attempt": attempt})
            candidate = backend.transfer(
                prepared,
                endpoint,
                "candidate",
                prepared.run_dir,
                attempt,
                prefix,
            )
            current = _state(prepared)
            current.update(
                {
                    "candidate_classification": candidate.classification,
                    "candidate_completed": candidate.completed,
                    "candidate_possible_device_session": candidate.possible_device_session,
                    "rollback_completed": False,
                    "final_verified": False,
                }
            )
            _save_state(prepared, current)
            if candidate.classification == "odin_local_parse_failure":
                # Reopen/validate the durable raw receipt before allowing the
                # sole release exception.  Any failure leaves the global claim
                # active and therefore forces recovery-only handling.
                _validate_transfer_result(prepared, "candidate", attempt)
                _release_candidate_global(prepared)
                journal.transition(
                    "ABORTED",
                    "odin_local_parse_failure",
                    {
                        "device_session_started": False,
                        "partition_transfer": False,
                    },
                )
                return _result(
                    prepared,
                    journal,
                    "FAIL_F1_V2_ODIN_LOCAL_PARSE_NO_DEVICE_SESSION",
                    "odin_local_parse_failure",
                    False,
                )
            journal.transition(
                "CANDIDATE_FLASHED",
                candidate.classification,
                {
                    "completed": candidate.completed,
                    "possible_device_session": candidate.possible_device_session,
                },
            )
            journal.event(
                "candidate_flash_done", {"completed": candidate.completed}
            )
            observation = backend.observe_candidate(
                prepared, endpoint_dir, lease, observer_session
            )
            current = _state(prepared)
            current["download_endpoint_absent"] = observation.get(
                "download_endpoint_absent"
            )
            if (
                prepared.bundle.manifest["observation"].get(
                    "candidate_observer"
                )
                is not None
            ):
                durable = _reopen_candidate_observation(prepared)
                current.update(
                    {
                        "download_endpoint_absent": durable[
                            "download_endpoint_absent"
                        ],
                        "candidate_observer_classification": durable[
                            "classification"
                        ],
                        "candidate_observer_accepted": durable["accepted"],
                        "candidate_observer_receipt_sha256": durable[
                            "receipt_sha256"
                        ],
                    }
                )
                if _p335_bundle(prepared.bundle):
                    current.update(_p332_proof_state(durable))
                    current.update(
                        {
                            "preauth_diagnostics": durable["preauth_diagnostics"],
                            "rng_eagain_retries": durable["rng_eagain_retries"],
                            "partial_sessions": durable["partial_sessions"],
                            "p335_authenticated_attended_resident": durable[
                                "p335_authenticated_attended_resident"
                            ],
                        }
                    )
                elif _p334_bundle(prepared.bundle) or _p333_bundle(prepared.bundle) or _p332_bundle(prepared.bundle):
                    current.update(_p332_proof_state(durable))
                    current.update(
                        {
                            "preauth_diagnostics": durable[
                                "preauth_diagnostics"
                            ],
                            "rng_eagain_retries": durable[
                                "rng_eagain_retries"
                            ],
                            "partial_sessions": durable[
                                "partial_sessions"
                            ],
                        }
                    )
                elif _p331_bundle(prepared.bundle):
                    current.update(_p331_proof_state(durable))
                    current.update(
                        {
                            "preauth_diagnostics": durable[
                                "preauth_diagnostics"
                            ],
                            "rng_eagain_retries": durable[
                                "rng_eagain_retries"
                            ],
                            "partial_sessions": durable[
                                "partial_sessions"
                            ],
                        }
                    )
                elif _p328_bundle(prepared.bundle):
                    current.update(_p328_proof_state(durable))
                    if _p330_bundle(prepared.bundle):
                        current.update(
                            {
                                "preauth_diagnostics": durable[
                                    "preauth_diagnostics"
                                ],
                                "rng_eagain_retries": durable[
                                    "rng_eagain_retries"
                                ],
                                "partial_exchange": durable[
                                    "partial_exchange"
                                ],
                            }
                        )
                elif _p327_bundle(prepared.bundle):
                    current.update(
                        {
                            "pid1_framed_exec_proof": durable[
                                "pid1_framed_exec_proof"
                            ],
                            "busybox_ash_command_proof": durable[
                                "busybox_ash_command_proof"
                            ],
                            "framed_session_closed": durable[
                                "framed_session_closed"
                            ],
                            "interactive_pty_proof": durable[
                                "interactive_pty_proof"
                            ],
                            "caller_selected_command": durable[
                                "caller_selected_command"
                            ],
                        }
                    )
                if _p318_bundle(prepared.bundle):
                    topology_receipt = observation.get(
                        "p318_candidate_topology_raw"
                    )
                    if topology_receipt != _p318_candidate_raw_receipt(prepared):
                        raise F1LiveError(
                            "P3.18 candidate topology raw receipt differs"
                        )
                    current["p318_candidate_topology_raw"] = topology_receipt
            _save_state(prepared, current)
            if _p300_bundle(prepared.bundle):
                trace_session.observation_durable(current)
                trace_session.defer_stack_close = True
            if _p335_bundle(prepared.bundle):
                p335_pending = _finish_p335_candidate_window_before_guard_release(
                    prepared,
                    journal,
                    candidate,
                    observation,
                    trace_session,
                )
        if p335_pending is not None:
            return _finish_p335_after_guard_release(
                prepared,
                backend,
                journal,
                endpoint_dir,
                lease,
                p335_pending,
            )
        return _run_deferred_p300_segment(
            trace_session,
            lambda: _finish_candidate_window(
                prepared,
                backend,
                journal,
                endpoint_dir,
                lease,
                candidate,
                observation,
                trace_session,
            ),
        )


def execute_prepared(
    prepared: PreparedRun,
    approval: str,
    backend: LiveBackend,
) -> dict[str, Any]:
    if approval != prepared.approval_token:
        raise F1LiveError("fresh F1 approval token mismatch")
    try:
        with consumed_registry.target_session_lease(prepared.root):
            with odin_core.transaction_session(prepared.run_dir / "f1-session"):
                return _execute_prepared_locked(prepared, approval, backend)
    except consumed_registry.RegistryError as exc:
        raise F1LiveError("global target-session lease unavailable or replaced") from exc


def _recover_prepared_locked(
    prepared: PreparedRun,
    backend: LiveBackend,
) -> dict[str, Any]:
    transaction = prepared.run_dir / "transaction"
    if not transaction.is_dir() or transaction.is_symlink():
        raise F1LiveError("recovery has no approved transaction")
    journal = core.Journal.reopen(transaction, prepared.binding_sha256)
    if journal.state() == "CLOSED":
        # Terminal-only host finalization may re-emit a result after a
        # publication cut.  The target-session flock is the only durable
        # physical-target serialization; it is never represented as a
        # candidate-consumption record.
        result_path = prepared.run_dir / "live-result.json"
        if result_path.exists() and not result_path.is_symlink():
            value = _read_json(result_path, "closed F1 live result")
            return _result(
                prepared,
                journal,
                value["verdict"],
                value["outcome_class"],
                value["recovery_required"],
            )
        verdict, outcome = _closed_terminal_classification(prepared)
        return _result(prepared, journal, verdict, outcome, False)
    if journal.state() == "ABORTED":
        current = _state(prepared)
        if current.get("candidate_classification") != "odin_local_parse_failure" or current.get("candidate_possible_device_session") is not False:
            raise F1LiveError("transaction is not recoverable")
        _validate_transfer_result(prepared, "candidate", 1)
        _release_candidate_global(prepared)
        return _result(
            prepared,
            journal,
            "FAIL_F1_V2_ODIN_LOCAL_PARSE_NO_DEVICE_SESSION",
            "odin_local_parse_failure",
            False,
        )
    request_cut_result = _recover_download_request_cut(
        prepared, backend, journal
    )
    if request_cut_result is not None:
        return request_cut_result
    if not _normalize_recovery(prepared, journal):
        if journal.state() != "ABORTED":
            journal.transition(
                "ABORTED",
                "interrupted_before_candidate_attempt",
                {"candidate_attempted": False, "partition_transfer": False},
            )
        return _result(
            prepared,
            journal,
            "FAIL_F1_V2_PRE_CANDIDATE_DOWNLOAD",
            "interrupted_before_candidate_attempt",
            False,
        )
    if _p335_bundle(prepared.bundle) and journal.state() == "OBSERVED":
        _p335_mark_resident_rollback_required(prepared)
    endpoint_dir = prepared.run_dir / "odin-endpoints"
    with backend.endpoint_session(endpoint_dir) as lease:
        return _finish_rollback(prepared, backend, journal, endpoint_dir, lease)


def recover_prepared(
    prepared: PreparedRun,
    backend: LiveBackend,
) -> dict[str, Any]:
    try:
        with consumed_registry.target_session_lease(prepared.root):
            with odin_core.transaction_session(prepared.run_dir / "f1-session"):
                return _recover_prepared_locked(prepared, backend)
    except consumed_registry.RegistryError as exc:
        raise F1LiveError("global target-session lease unavailable or replaced") from exc


def render_plan(root: Path, bundle: core.Bundle) -> dict[str, Any]:
    return {
        "schema": "device_action_f1_live_plan_v2",
        "adapter_version": ADAPTER_VERSION,
        "manifest_id": bundle.manifest["manifest_id"],
        "manifest_status": bundle.manifest["status"],
        "bundle_sha256": bundle.sha256,
        "execution_closure": _closure(root, bundle),
        "commands": ["validate", "render-plan", "prepare", "execute", "recover"],
        "prepare_is_d0_only": True,
        "execute_requires_fresh_exact_approval": True,
        "rollback_preapproved": True,
        "recover_can_transfer_candidate": False,
        "device_contact": False,
        "device_writes": False,
        "f1_authorized": False,
        "live_authorized": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--render-plan", action="store_true")
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--recover", action="store_true")
    parser.add_argument("--manifest", type=Path, default=core.DEFAULT_MANIFEST)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--approval")
    parser.add_argument("--adb", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = core.repo_root()
    try:
        if args.validate or args.render_plan:
            bundle = core.verify_bundle(root, args.manifest)
            result = render_plan(root, bundle)
            if args.validate:
                result = {
                    **result,
                    "schema": "device_action_f1_live_offline_check_v2",
                    "verdict": "PASS_DEVICE_ACTION_F1_LIVE_V2_HOST_READY",
                }
        elif args.prepare:
            bundle = core.verify_bundle(root, args.manifest)
            if bundle.manifest["status"] != "ready-for-f1-approval":
                raise F1LiveError("manifest is not ready for F1 preparation")
            run_dir = allocate_run_dir(root, args.run_dir)
            adb = args.adb or d0.default_adb()
            result = prepare_connected(
                root, bundle, run_dir, d0.adb_client_for_bundle(adb, bundle)
            )
            result = {**result, "run_dir": str(run_dir)}
        else:
            if args.run_dir is None:
                raise F1LiveError("execute/recover requires --run-dir")
            if args.recover and args.approval is not None:
                raise F1LiveError("recovery must not require a second approval")
            prepared = load_prepared(root, args.manifest, args.run_dir)
            adb = args.adb or d0.default_adb()
            backend = SamsungOdinBackend(root, prepared.bundle, adb)
            if args.execute:
                if not args.approval:
                    raise F1LiveError("execute requires --approval")
                result = execute_prepared(prepared, args.approval, backend)
            else:
                result = recover_prepared(prepared, backend)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (
        F1LiveError,
        core.F1V2Error,
        core.F1TransportError,
        d0.D0Error,
        odin_core.OdinTransitionError,
        usbfs_identity.UsbfsIdentityError,
        live_core.LiveCoreError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"Device Action F1 live v2 error: {exc}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
