#!/usr/bin/env python3
"""Audit the append-only S22+ campaign ledger on orthogonal axes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "s22plus-fyg8-campaign-ledger-taxonomy-v2"
DERIVATION_VERSION = 2
VERDICT = "PASS_P318_CAMPAIGN_LEDGER_TAXONOMY_H0_V2"
STATUS = "IMPLEMENTED_REVIEW_PENDING"
MARKER = b"<!-- append below; never edit or remove an earlier line -->\n"
TAXONOMY_ACTION = "P318_CAMPAIGN_LEDGER_TAXONOMY_IMPLEMENTED_REVIEW_PENDING"
HISTORICAL_ROW_COUNT = 181
HISTORICAL_BYTE_COUNT = 103274
HISTORICAL_SHA256 = "3c0cca0feea9259a0107cc9c9bfa021579707595afa15b6bf9371529f1fe06e1"

ROOT = Path(__file__).resolve().parents[5]
DEFAULT_LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p318_ledger_taxonomy/"
    "ledger-taxonomy-20260815-01.json"
)

HEALTH_STATES = {
    "HEALTHY",
    "HEALTH_PENDING",
    "HOST_OBSERVER_FAILURE",
    "RECOVERY_PENDING_PARKED",
    "RECOVERY_REQUIRED",
}
TIERS = {"H0", "D0", "D1", "F1"}
RAW_EVIDENCE_OUTCOMES = {
    "PROVED",
    "REFUTED",
    "NO_PROOF_EXPERIMENT_PRECONDITION",
    "NO_PROOF_OBSERVER",
    "N/A",
    "NO_PROOF",
    "NO_PROOF_SUBTYPE",
    "NO_PROOF_LOG_BASELINE",
}
EXPERIMENT_PROOF_CLASSES = {
    "PROVED",
    "REFUTED",
    "NO_PROOF_EXPERIMENT_PRECONDITION",
    "NO_PROOF_OBSERVER",
}
CORRECTION_SCOPES = {"CAMPAIGN_PROOF", "SUBRESULT_ONLY"}
CORRECTION_EFFECTS = {"APPLY_TO_METRICS", "EXCLUDE_FROM_CAMPAIGN_METRICS"}

LEGACY_MISSING_TRANSFER_ROWS = {
    (
        "2026-08-04T15:52:43Z",
        "s22plus-fyg8-p300",
        "connected-d0-1",
        "D0",
        "CONNECTED_BASELINE_STOP",
    ),
    (
        "2026-08-04T15:55:57Z",
        "s22plus-fyg8-p300",
        "baseline-rotation-1",
        "D1",
        "NORMAL_REBOOT_BASELINE_ROTATION",
    ),
    (
        "2026-08-04T15:56:39Z",
        "s22plus-fyg8-p300",
        "process-v2-prepare-1",
        "D0",
        "PROCESS_V2_PREPARE",
    ),
    (
        "2026-08-13T16:37:52Z",
        "s22plus-fyg8-p317",
        "h0-recovery-repair-1",
        "H0",
        "HISTORICAL_ENDPOINT_REPLAY_RECOVERY_ONLY_IMPLEMENTED_REVIEW_PENDING",
    ),
}

LEGACY_EVIDENCE_ROWS = {
    (
        "2026-08-03T12:56:57Z",
        "s22plus-fyg8-p298",
        "h0-2",
        "H0",
        "PRE_FULL_LTO_GATE_STOP",
        "HEALTHY",
        "NO_PROOF",
    ),
    (
        "2026-08-04T17:41:06Z",
        "s22plus-fyg8-post-p300-subtype",
        "h0-1",
        "H0",
        "DEVICE_OTHER_SUBTYPE_REDUCTION",
        "HEALTHY",
        "NO_PROOF_SUBTYPE",
    ),
    (
        "2026-08-05T00:30:08Z",
        "s22plus-fyg8-post-p301-r1",
        "connected-d0-1",
        "D0",
        "STOCK_HSPHY_DMESG_BASELINE",
        "HEALTHY",
        "NO_PROOF_LOG_BASELINE",
    ),
    (
        "2026-08-05T02:53:31Z",
        "s22plus-fyg8-p303",
        "stock-log-d0-3",
        "D0",
        "STOCK_BOOT_HEAD_EMPIRICALLY_UNAVAILABLE",
        "HEALTHY",
        "NO_PROOF_LOG_BASELINE",
    ),
}
LEGACY_EVIDENCE_OUTCOMES = {"NO_PROOF", "NO_PROOF_SUBTYPE", "NO_PROOF_LOG_BASELINE"}

LEGACY_REVIEW_RESOLUTIONS = {
    (
        "s22plus-fyg8-p306",
        "h0-1",
        "IPC_OBSERVER_READY_PENDING_REVIEW",
    ): (
        "ipc-observer",
        "h0-review-1",
        "PASS_GO_IPC_OBSERVER_CAPABILITY",
    ),
    (
        "s22plus-fyg8-p307",
        "h0-1",
        "EUD_QSCRATCH_OBSERVER_READY_PENDING_REVIEW",
    ): (
        "eud-qscratch-observer",
        "h0-review-1",
        "PASS_GO_EUD_QSCRATCH_OBSERVER_CAPABILITY",
    ),
    (
        "s22plus-fyg8-p308",
        "h0-1",
        "LOSS_RESISTANT_OBSERVER_READY_PENDING_REVIEW",
    ): (
        "loss-resistant-observer",
        "h0-review-1",
        "PASS_GO_LOSS_RESISTANT_OBSERVER_CAPABILITY",
    ),
    (
        "s22plus-fyg8-p317",
        "h0-implementation-1",
        "P317_RUNTIME_PACKAGING_OFFLINE_BUNDLE_READY_REVIEW_PENDING",
    ): (
        "runtime-packaging",
        "h0-final-review-1",
        "PASS_GO_P317_CUSTOM70_PROCESS_V2_OFFLINE_READY_CAPABILITY_V1",
    ),
    (
        "s22plus-fyg8-p317",
        "h0-recovery-repair-1",
        "HISTORICAL_ENDPOINT_REPLAY_RECOVERY_ONLY_IMPLEMENTED_REVIEW_PENDING",
    ): (
        "historical-endpoint-replay-recovery-only",
        "h0-recovery-review-1",
        "PASS_GO_P317_HISTORICAL_ENDPOINT_REPLAY_RECOVERY_ONLY_V1",
    ),
    (
        "s22plus-fyg8-p317",
        "h0-postclose-audit-1",
        "P317_RECOVERY_CLOSE_AUDIT_IMPLEMENTED_REVIEW_PENDING",
    ): (
        "recovery-close-audit",
        "h0-postclose-review-1",
        "PASS_GO_P317_RECOVERY_CLOSE_AUDIT_V1",
    ),
}
LEGACY_REVIEW_PASSES = {
    (campaign, resolution_ordinal, resolution_action): topic
    for (campaign, _pending_ordinal, _pending_action), (
        topic,
        resolution_ordinal,
        resolution_action,
    ) in LEGACY_REVIEW_RESOLUTIONS.items()
}

EXPECTED_CORRECTIONS = (
    {
        "original_campaign": "s22plus-fyg8-p316",
        "original_ordinal": "1",
        "correction_campaign": "s22plus-fyg8-p317",
        "correction_ordinal": "h0-design-1",
        "scope": "CAMPAIGN_PROOF",
        "subject": "experiment",
        "effective_class": "NO_PROOF_EXPERIMENT_PRECONDITION",
        "metric_effect": "APPLY_TO_METRICS",
        "correction_action": (
            "P316_PROOF_CLASS_CORRECTION_AND_"
            "EXPERIMENT_EXECUTABILITY_CLOSURE_DESIGN"
        ),
    },
    {
        "original_campaign": "s22plus-fyg8-p317",
        "original_ordinal": "1",
        "correction_campaign": "s22plus-fyg8-p317",
        "correction_ordinal": "h0-endpoint-topology-correction-2",
        "scope": "SUBRESULT_ONLY",
        "subject": "endpoint-selection",
        "effective_class": "NO_PROOF_EXPERIMENT_PRECONDITION",
        "metric_effect": "EXCLUDE_FROM_CAMPAIGN_METRICS",
        "correction_action": (
            "P317_PHYSICAL_TOPOLOGY_PRECONDITION_POSTCLOSE_CORRECTION"
        ),
    },
)
CORRECTION_ROW_IDENTITIES = {
    (
        item["correction_campaign"],
        item["correction_ordinal"],
        item["correction_action"],
    )
    for item in EXPECTED_CORRECTIONS
}

EXPECTED_ATTEMPTS = {
    "s22plus-fyg8-p310": "NO_PROOF_OBSERVER",
    "s22plus-fyg8-p311": "NO_PROOF_OBSERVER",
    "s22plus-fyg8-p312": "REFUTED",
    "s22plus-fyg8-p313": "NO_PROOF_OBSERVER",
    "s22plus-fyg8-p314": "NO_PROOF_OBSERVER",
    "s22plus-fyg8-p315": "REFUTED",
    "s22plus-fyg8-p316": "NO_PROOF_EXPERIMENT_PRECONDITION",
    "s22plus-fyg8-p317": "NO_PROOF_OBSERVER",
}

LOCALIZATION_REQUIREMENTS = (
    (
        "s22plus-fyg8-p310",
        "CAMPAIGN_CLOSED",
        "nested-bytes JSON serialization incident",
    ),
    (
        "s22plus-fyg8-p311",
        "CAMPAIGN_CLOSED",
        "observer incorrectly required 24-event kprobe profile hits",
    ),
    (
        "s22plus-fyg8-p313",
        "INTERMEDIATE_CONTRADICTION_DECODER_RECOVERY",
        "frozen decoder verified but semantically rejected",
    ),
    (
        "s22plus-fyg8-p313",
        "STOP_MULTIPLICITY_SOURCE_TRIGGER_LOCALIZED",
        "actual materialized parser reproduces 0x6712",
    ),
    (
        "s22plus-fyg8-p314",
        "LIVE_PROFILE_SNAPSHOT_ORDERING_LOCALIZED",
        "zero-initialized profile_hits",
    ),
    (
        "s22plus-fyg8-p317",
        "CAMPAIGN_CLOSED",
        "MAX77705_RESULT_MULTIPLICITY",
    ),
)

CORRECTION_PATTERN = re.compile(
    r"^`CORRECTION \| ([^|`]+) \| ([^|`]+) \| ([^|`]+) \| "
    r"([^|`]+) \| ([^|`]+) \| ([^|`]+) \| ([^|`]+) \| "
    r"([^|`]+)`$",
    re.MULTILINE,
)
TIMESTAMP_PATTERN = re.compile(r"^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
TRANSFER_PATTERN = re.compile(r"^(0|[1-9]\d*)/(0|[1-9]\d*)$")
ATTEMPT_ORDINAL_PATTERN = re.compile(r"^([1-9]\d*)(?:-recovery-close)?$")
CAMPAIGN_PATTERN = re.compile(r"^s22plus-fyg8-[a-z0-9][a-z0-9-]*$")
ORDINAL_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
ACTION_PATTERN = re.compile(r"^[A-Z0-9_]+$")
REVIEW_ORDINAL_PATTERN = re.compile(
    r"^h0-([a-z0-9]+(?:-[a-z0-9]+)*)-review-([1-9]\d*)$"
)


class TaxonomyError(RuntimeError):
    """Fail-closed taxonomy audit error."""


def identity(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def stable_read(path: Path, label: str, limit: int) -> bytes:
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise TaxonomyError(f"{label} is not one direct regular file")
    if before.st_size <= 0 or before.st_size > limit:
        raise TaxonomyError(f"{label} size is outside the closed bound")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino, opened.st_size) != (
            before.st_dev,
            before.st_ino,
            before.st_size,
        ):
            raise TaxonomyError(f"{label} changed before read")
        chunks: list[bytes] = []
        remaining = opened.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 65536))
            if not chunk:
                raise TaxonomyError(f"{label} ended before its stated size")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise TaxonomyError(f"{label} grew during read")
        after_open = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after_path = path.lstat()
    closed = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    if closed != (
        after_open.st_dev,
        after_open.st_ino,
        after_open.st_size,
        after_open.st_mtime_ns,
    ) or closed != (
        after_path.st_dev,
        after_path.st_ino,
        after_path.st_size,
        after_path.st_mtime_ns,
    ):
        raise TaxonomyError(f"{label} changed during read")
    return b"".join(chunks)


def _legacy_key(fields: list[str]) -> tuple[str, str, str, str, str]:
    return tuple(fields[:5])  # type: ignore[return-value]


def parse_log_rows(
    lines: Iterable[bytes],
) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, str]]]:
    rows: list[dict[str, Any]] = []
    legacy_transfers: list[dict[str, str]] = []
    legacy_evidence: list[dict[str, str]] = []
    seen_legacy_transfers: set[tuple[str, str, str, str, str]] = set()
    seen_legacy_evidence: set[tuple[str, str, str, str, str, str, str]] = set()
    seen_actions: set[tuple[str, str, str]] = set()
    attempt_states: dict[tuple[str, str], tuple[int, int, bool]] = {}
    previous_timestamp: datetime | None = None
    for line_number, raw_line in enumerate(lines, 1):
        if not raw_line.endswith(b"\n"):
            raise TaxonomyError(f"log row {line_number} is not LF terminated")
        try:
            line = raw_line[:-1].decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise TaxonomyError(f"log row {line_number} is not UTF-8") from exc
        if not line:
            raise TaxonomyError(f"blank line {line_number} is not a log row")
        fields = line.split(" | ")
        if len(fields) == 8:
            key = _legacy_key(fields)
            if key not in LEGACY_MISSING_TRANSFER_ROWS:
                raise TaxonomyError(
                    f"log row {line_number} is missing transfer accounting"
                )
            if key in seen_legacy_transfers:
                raise TaxonomyError("legacy missing-transfer exception is duplicated")
            seen_legacy_transfers.add(key)
            fields.insert(7, "0/0")
            legacy_transfers.append(
                {
                    "timestamp": key[0],
                    "campaign": key[1],
                    "ordinal": key[2],
                    "action": key[4],
                    "normalized_transfers": "0/0",
                }
            )
        elif len(fields) != 9:
            raise TaxonomyError(
                f"log row {line_number} has {len(fields)} fields instead of 9"
            )
        (
            timestamp,
            campaign,
            ordinal,
            tier,
            action,
            health,
            raw_proof,
            transfers,
            finding,
        ) = fields
        if not TIMESTAMP_PATTERN.fullmatch(timestamp):
            raise TaxonomyError(f"log row {line_number} has an invalid timestamp")
        try:
            parsed_timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as exc:
            raise TaxonomyError(
                f"log row {line_number} has an invalid UTC calendar timestamp"
            ) from exc
        if previous_timestamp is not None and parsed_timestamp < previous_timestamp:
            raise TaxonomyError(f"log row {line_number} regresses UTC ordering")
        previous_timestamp = parsed_timestamp
        if not CAMPAIGN_PATTERN.fullmatch(campaign):
            raise TaxonomyError(f"log row {line_number} has an invalid S22 campaign token")
        if not ORDINAL_PATTERN.fullmatch(ordinal):
            raise TaxonomyError(f"log row {line_number} has an invalid ordinal token")
        if not ACTION_PATTERN.fullmatch(action):
            raise TaxonomyError(f"log row {line_number} has an invalid action token")
        if not finding.strip() or finding != finding.strip():
            raise TaxonomyError(f"log row {line_number} has an empty required field")
        action_key = (campaign, ordinal, action)
        if action_key in seen_actions:
            raise TaxonomyError(f"log row {line_number} duplicates one ledger action")
        seen_actions.add(action_key)
        if tier not in TIERS:
            raise TaxonomyError(f"log row {line_number} has an unknown tier")
        if health not in HEALTH_STATES:
            raise TaxonomyError(f"log row {line_number} has an unknown health state")
        if raw_proof not in RAW_EVIDENCE_OUTCOMES:
            raise TaxonomyError(f"log row {line_number} has an unknown evidence outcome")
        reserved_review_label = (
            action.startswith("PASS_GO_")
            or action.endswith("_REVIEW_PENDING")
            or action.endswith("_PENDING_REVIEW")
        )
        if tier != "H0" and reserved_review_label:
            raise TaxonomyError(
                f"log row {line_number} uses an H0 review label outside H0"
            )
        if raw_proof in LEGACY_EVIDENCE_OUTCOMES:
            legacy_key = (
                timestamp,
                campaign,
                ordinal,
                tier,
                action,
                health,
                raw_proof,
            )
            if legacy_key not in LEGACY_EVIDENCE_ROWS:
                raise TaxonomyError(
                    f"log row {line_number} reuses a legacy evidence outcome"
                )
            if legacy_key in seen_legacy_evidence:
                raise TaxonomyError("legacy evidence exception is duplicated")
            seen_legacy_evidence.add(legacy_key)
            legacy_evidence.append(
                {
                    "timestamp": timestamp,
                    "campaign": campaign,
                    "ordinal": ordinal,
                    "action": action,
                    "raw_evidence_outcome": raw_proof,
                }
            )
        match = TRANSFER_PATTERN.fullmatch(transfers)
        if match is None:
            raise TaxonomyError(f"log row {line_number} has invalid transfer accounting")
        candidate_transfers = int(match.group(1))
        rollback_transfers = int(match.group(2))
        if action == "CAMPAIGN_CLOSED" and tier != "F1":
            raise TaxonomyError(
                f"log row {line_number} assigns CAMPAIGN_CLOSED outside F1"
            )
        if tier != "F1" and (candidate_transfers != 0 or rollback_transfers != 0):
            raise TaxonomyError(
                f"log row {line_number} assigns a boot transfer to non-F1 work"
            )
        attempt_match = (
            ATTEMPT_ORDINAL_PATTERN.fullmatch(ordinal) if tier == "F1" else None
        )
        if tier == "F1":
            if candidate_transfers > 1 or rollback_transfers > 1:
                raise TaxonomyError(
                    f"log row {line_number} violates one-shot F1 transfer accounting"
                )
            if rollback_transfers > candidate_transfers:
                raise TaxonomyError(
                    f"log row {line_number} records rollback without candidate transfer"
                )
            if (
                candidate_transfers == 1
                and attempt_match is None
            ):
                raise TaxonomyError(
                    f"log row {line_number} has a noncanonical F1 attempt ordinal"
                )
            if action == "CAMPAIGN_CLOSED" and candidate_transfers != 1:
                raise TaxonomyError(
                    f"log row {line_number} closes a campaign without one candidate transfer"
                )
            if action == "CAMPAIGN_CLOSED":
                if health not in {"HEALTHY", "RECOVERY_REQUIRED"}:
                    raise TaxonomyError(
                        f"log row {line_number} closes a campaign in a nonterminal health state"
                    )
                if health == "HEALTHY" and rollback_transfers != 1:
                    raise TaxonomyError(
                        f"log row {line_number} claims healthy close without exact rollback"
                    )
        if (
            tier == "F1"
            and action == "CAMPAIGN_CLOSED"
            and candidate_transfers > 0
            and raw_proof not in EXPERIMENT_PROOF_CLASSES
        ):
            raise TaxonomyError(
                f"log row {line_number} terminal attempt lacks an experiment proof class"
            )
        if attempt_match is not None:
            attempt_key = (campaign, attempt_match.group(1))
            previous_attempt = attempt_states.get(attempt_key)
            if ordinal.endswith("-recovery-close") and previous_attempt is None:
                raise TaxonomyError(
                    f"log row {line_number} records recovery close without prior attempt state"
                )
            if previous_attempt is not None:
                previous_candidate, previous_rollback, previous_closed = previous_attempt
                if previous_closed:
                    if action == "CAMPAIGN_CLOSED":
                        raise TaxonomyError(
                            f"log row {line_number} adds a second terminal to one F1 attempt"
                        )
                    raise TaxonomyError(
                        f"log row {line_number} resumes a closed F1 attempt"
                    )
                if (
                    candidate_transfers < previous_candidate
                    or rollback_transfers < previous_rollback
                ):
                    raise TaxonomyError(
                        f"log row {line_number} regresses one F1 attempt's transfer accounting"
                    )
            attempt_states[attempt_key] = (
                candidate_transfers,
                rollback_transfers,
                action == "CAMPAIGN_CLOSED",
            )
        rows.append(
            {
                "timestamp": timestamp,
                "campaign": campaign,
                "ordinal": ordinal,
                "tier": tier,
                "action": action,
                "health": health,
                "raw_evidence_outcome": raw_proof,
                "candidate_transfers": candidate_transfers,
                "rollback_transfers": rollback_transfers,
                "finding": finding,
                "line_number_after_marker": line_number,
            }
        )
    if seen_legacy_transfers != LEGACY_MISSING_TRANSFER_ROWS:
        raise TaxonomyError("the exact legacy missing-transfer exception set changed")
    if seen_legacy_evidence != LEGACY_EVIDENCE_ROWS:
        raise TaxonomyError("the exact legacy evidence exception set changed")
    return rows, legacy_transfers, legacy_evidence


def capability_review_state(tier: str, action: str) -> str:
    if tier != "H0":
        return "NOT_APPLICABLE"
    pass_go = action.startswith("PASS_GO_")
    pending = action.endswith("_REVIEW_PENDING") or action.endswith("_PENDING_REVIEW")
    if pass_go and pending:
        raise TaxonomyError("one action cannot be PASS_GO and REVIEW_PENDING")
    if pass_go:
        return "PASS_GO"
    if pending:
        return "IMPLEMENTED_REVIEW_PENDING"
    if "REVIEW" in action:
        return "LEGACY_UNSCOPED_REVIEW_LABEL"
    return "NOT_APPLICABLE"


def row_kind(row: dict[str, Any]) -> str:
    if (
        row["tier"] == "F1"
        and row["action"] == "CAMPAIGN_CLOSED"
        and row["candidate_transfers"] > 0
    ):
        return "TERMINAL_DEVICE_ATTEMPT"
    if row["tier"] == "F1":
        if row["candidate_transfers"] == 0:
            return "PRESESSION_OR_ZERO_TRANSFER_F1_STOP"
        return "INTERMEDIATE_DEVICE_ATTEMPT_OR_RECOVERY"
    if row["tier"] == "D0":
        return "CONNECTED_READ_ONLY"
    if row["tier"] == "D1":
        return "CONNECTED_CONTROL"
    if (row["campaign"], row["ordinal"], row["action"]) in CORRECTION_ROW_IDENTITIES:
        return "H0_ANALYSIS_OR_CORRECTION"
    return "H0_HOST_ONLY_NONCORRECTION"


def pending_review_topic(row: dict[str, Any]) -> str:
    legacy = LEGACY_REVIEW_RESOLUTIONS.get(
        (row["campaign"], row["ordinal"], row["action"])
    )
    if legacy is not None:
        return legacy[0]
    parts = row["ordinal"].split("-")
    if (
        len(parts) < 3
        or parts[0] != "h0"
        or not re.fullmatch(r"[1-9]\d*", parts[-1])
    ):
        raise TaxonomyError("pending review ordinal has no closed topic key")
    topic_parts = parts[1:-1]
    if topic_parts and topic_parts[-1] == "followup":
        topic_parts = topic_parts[:-1]
    if not topic_parts or "review" in topic_parts:
        raise TaxonomyError("pending review ordinal has no closed topic key")
    return "-".join(topic_parts)


def resolution_review_topic(row: dict[str, Any]) -> str | None:
    legacy = LEGACY_REVIEW_PASSES.get(
        (row["campaign"], row["ordinal"], row["action"])
    )
    if legacy is not None:
        return legacy
    match = REVIEW_ORDINAL_PATTERN.fullmatch(row["ordinal"])
    return match.group(1) if match is not None else None


def audit_review_obligations(rows: list[dict[str, Any]]) -> dict[str, Any]:
    open_by_topic: dict[tuple[str, str], dict[str, Any]] = {}
    resolved: list[dict[str, str]] = []
    pass_go_resolving_no_obligation: list[dict[str, str]] = []
    for row in rows:
        state = capability_review_state(row["tier"], row["action"])
        campaign = row["campaign"]
        if state == "IMPLEMENTED_REVIEW_PENDING":
            topic = pending_review_topic(row)
            key = (campaign, topic)
            if key in open_by_topic:
                raise TaxonomyError(
                    f"campaign {campaign} opens a second {topic} review obligation"
                )
            open_by_topic[key] = row
        elif state == "PASS_GO":
            topic = resolution_review_topic(row)
            key = (campaign, topic) if topic is not None else None
            if key is not None and key in open_by_topic:
                pending = open_by_topic.pop(key)
                resolved.append(
                    {
                        "campaign": campaign,
                        "review_topic": topic,
                        "pending_ordinal": pending["ordinal"],
                        "pending_action": pending["action"],
                        "resolution_ordinal": row["ordinal"],
                        "resolution_action": row["action"],
                    }
                )
            else:
                pass_go_resolving_no_obligation.append(
                    {
                        "campaign": campaign,
                        "ordinal": row["ordinal"],
                        "action": row["action"],
                        "review_topic": topic,
                    }
                )
    unresolved = [
        {
            "campaign": campaign,
            "review_topic": topic,
            "pending_ordinal": row["ordinal"],
            "pending_action": row["action"],
        }
        for (campaign, topic), row in open_by_topic.items()
    ]
    return {
        "total": len(resolved) + len(unresolved),
        "resolved_count": len(resolved),
        "unresolved_count": len(unresolved),
        "resolved": resolved,
        "unresolved": unresolved,
        "pass_go_resolving_no_obligation_count": len(
            pass_go_resolving_no_obligation
        ),
        "pass_go_resolving_no_obligation": pass_go_resolving_no_obligation,
    }


def parse_corrections(header: str, rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    parsed: list[dict[str, str]] = []
    for match in CORRECTION_PATTERN.finditer(header):
        values = [value.strip() for value in match.groups()]
        (
            original_campaign,
            original_ordinal,
            correction_campaign,
            correction_ordinal,
            scope,
            subject,
            effective_class,
            metric_effect,
        ) = values
        if scope not in CORRECTION_SCOPES:
            raise TaxonomyError("correction registry contains an unknown scope")
        if effective_class not in EXPERIMENT_PROOF_CLASSES:
            raise TaxonomyError("correction registry contains an unknown proof class")
        if metric_effect not in CORRECTION_EFFECTS:
            raise TaxonomyError("correction registry contains an unknown metric effect")
        if (scope == "CAMPAIGN_PROOF") != (metric_effect == "APPLY_TO_METRICS"):
            raise TaxonomyError("correction scope and metric effect disagree")
        parsed.append(
            {
                "original_campaign": original_campaign,
                "original_ordinal": original_ordinal,
                "correction_campaign": correction_campaign,
                "correction_ordinal": correction_ordinal,
                "scope": scope,
                "subject": subject,
                "effective_class": effective_class,
                "metric_effect": metric_effect,
            }
        )
    expected_public = [
        {key: value for key, value in item.items() if key != "correction_action"}
        for item in EXPECTED_CORRECTIONS
    ]
    if parsed != expected_public:
        raise TaxonomyError("correction registry differs from the reviewed two-row authority")
    for correction, expected in zip(parsed, EXPECTED_CORRECTIONS, strict=True):
        matches = [
            row
            for row in rows
            if row["campaign"] == correction["correction_campaign"]
            and row["ordinal"] == correction["correction_ordinal"]
        ]
        if len(matches) != 1:
            raise TaxonomyError("correction registry does not resolve to one ledger row")
        if matches[0]["action"] != expected["correction_action"]:
            raise TaxonomyError("correction registry resolves to the wrong action")
    return parsed


def normalized_attempt_ordinal(value: str) -> str:
    match = ATTEMPT_ORDINAL_PATTERN.fullmatch(value)
    if match is None:
        raise TaxonomyError(f"terminal attempt ordinal is not canonical: {value}")
    return match.group(1)


def audit_attempt_inventory(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    states: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        if row["tier"] != "F1":
            continue
        match = ATTEMPT_ORDINAL_PATTERN.fullmatch(row["ordinal"])
        if match is None:
            continue
        key = (row["campaign"], match.group(1))
        state = states.setdefault(
            key,
            {
                "campaign": row["campaign"],
                "ordinal": match.group(1),
                "candidate_transfers": 0,
                "rollback_transfers": 0,
                "last_health": row["health"],
                "terminal_ordinal": None,
                "terminal_proof": None,
            },
        )
        state["candidate_transfers"] = max(
            state["candidate_transfers"], row["candidate_transfers"]
        )
        state["rollback_transfers"] = max(
            state["rollback_transfers"], row["rollback_transfers"]
        )
        state["last_health"] = row["health"]
        if row["action"] == "CAMPAIGN_CLOSED":
            state["terminal_ordinal"] = row["ordinal"]
            state["terminal_proof"] = row["raw_evidence_outcome"]
    inventory: list[dict[str, Any]] = []
    for state in states.values():
        if state["candidate_transfers"] == 0:
            continue
        state["attempt_state"] = (
            "CLOSED" if state["terminal_ordinal"] is not None else "ATTEMPT_OPEN"
        )
        inventory.append(state)
    inventory.sort(key=lambda item: (item["campaign"], int(item["ordinal"])))
    return inventory


def _find_exact_row(
    rows: list[dict[str, Any]], campaign: str, action: str
) -> dict[str, Any]:
    matches = [
        row for row in rows if row["campaign"] == campaign and row["action"] == action
    ]
    if len(matches) != 1:
        raise TaxonomyError(f"expected one {campaign}/{action} row")
    return matches[0]


def audit_localizations(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    audited: list[dict[str, str]] = []
    for campaign, action, token in LOCALIZATION_REQUIREMENTS:
        row = _find_exact_row(rows, campaign, action)
        if token not in row["finding"]:
            raise TaxonomyError(f"localization evidence missing for {campaign}")
        audited.append({"campaign": campaign, "action": action, "evidence_token": token})
    return audited


def derive_attempt_outcomes(
    rows: list[dict[str, Any]], corrections: list[dict[str, str]]
) -> list[dict[str, Any]]:
    terminal_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        if row["tier"] != "F1" or row["action"] != "CAMPAIGN_CLOSED":
            continue
        key = (row["campaign"], normalized_attempt_ordinal(row["ordinal"]))
        if key in terminal_by_key:
            raise TaxonomyError("one campaign attempt has multiple terminal rows")
        terminal_by_key[key] = row

    outcomes: list[dict[str, Any]] = []
    for item in audit_attempt_inventory(rows):
        key = (item["campaign"], item["ordinal"])
        terminal = terminal_by_key.get(key)
        raw_class: str | None = None
        effective_class: str | None = None
        applied: list[str] = []
        if item["attempt_state"] == "CLOSED":
            if terminal is None:
                raise TaxonomyError("closed attempt has no terminal row")
            raw_class = terminal["raw_evidence_outcome"]
            if raw_class not in EXPERIMENT_PROOF_CLASSES:
                raise TaxonomyError(
                    "a metrics-eligible terminal has a non-experiment proof label"
                )
            effective_class = raw_class
            for correction in corrections:
                if (
                    correction["scope"] == "CAMPAIGN_PROOF"
                    and correction["original_campaign"] == item["campaign"]
                    and correction["original_ordinal"] == item["ordinal"]
                ):
                    effective_class = correction["effective_class"]
                    applied.append(
                        correction["correction_campaign"]
                        + "/"
                        + correction["correction_ordinal"]
                    )
            if len(applied) > 1:
                raise TaxonomyError("one campaign attempt has multiple metric corrections")
        elif terminal is not None:
            raise TaxonomyError("open attempt unexpectedly has a terminal row")
        outcomes.append(
            {
                "campaign": item["campaign"],
                "ordinal": item["ordinal"],
                "attempt_state": item["attempt_state"],
                "terminal_ordinal": (
                    terminal["ordinal"] if terminal is not None else None
                ),
                "health": item["last_health"],
                "transfers": (
                    f"{item['candidate_transfers']}/{item['rollback_transfers']}"
                ),
                "raw_experiment_proof": raw_class,
                "effective_experiment_proof": effective_class,
                "campaign_correction": applied[0] if applied else None,
            }
        )
    return outcomes


def audit_attempts(
    rows: list[dict[str, Any]], corrections: list[dict[str, str]]
) -> list[dict[str, Any]]:
    all_outcomes = derive_attempt_outcomes(rows, corrections)
    attempts = [
        item for item in all_outcomes if item["campaign"] in EXPECTED_ATTEMPTS
    ]
    if len(attempts) != len(EXPECTED_ATTEMPTS):
        raise TaxonomyError("P3.10-P3.17 does not contain exactly eight attempts")
    for item in attempts:
        if item["effective_experiment_proof"] != EXPECTED_ATTEMPTS[item["campaign"]]:
            raise TaxonomyError(f"effective proof drift for {item['campaign']}")
    attempts.sort(key=lambda item: item["campaign"])
    if {item["campaign"] for item in attempts} != set(EXPECTED_ATTEMPTS):
        raise TaxonomyError("P3.10-P3.17 campaign membership drifted")

    presession = _find_exact_row(rows, "s22plus-fyg8-p314", "PRE_CANDIDATE_DOWNLOAD_PRESENT")
    if row_kind(presession) != "PRESESSION_OR_ZERO_TRANSFER_F1_STOP":
        raise TaxonomyError("P3.14 pre-session stop became a device attempt")
    parked = _find_exact_row(rows, "s22plus-fyg8-p317", "ROLLBACK_ENDPOINT_AMBIGUITY_PARK")
    if row_kind(parked) != "INTERMEDIATE_DEVICE_ATTEMPT_OR_RECOVERY":
        raise TaxonomyError("P3.17 parked row classification drifted")
    return attempts


def cohort(attempts: list[dict[str, Any]], campaigns: list[str]) -> dict[str, Any]:
    selected = [item for item in attempts if item["campaign"] in campaigns]
    if len(selected) != len(campaigns):
        raise TaxonomyError("cohort campaign membership is incomplete")
    counts = Counter(item["effective_experiment_proof"] for item in selected)
    state_counts = Counter(item["attempt_state"] for item in selected)
    result = {
        "attempt_count": len(selected),
        "campaigns": campaigns,
        "effective_class_counts": {
            "PROVED": counts["PROVED"],
            "REFUTED": counts["REFUTED"],
            "NO_PROOF_EXPERIMENT_PRECONDITION": counts[
                "NO_PROOF_EXPERIMENT_PRECONDITION"
            ],
            "NO_PROOF_OBSERVER": counts["NO_PROOF_OBSERVER"],
        },
        "attempt_state_counts": {
            "CLOSED": state_counts["CLOSED"],
            "ATTEMPT_OPEN": state_counts["ATTEMPT_OPEN"],
        },
        "conclusive_information_yield": {
            "numerator": counts["PROVED"] + counts["REFUTED"],
            "denominator": len(selected),
        },
        "diagnostic_bearing_yield": {
            "numerator": (
                counts["PROVED"]
                + counts["REFUTED"]
                + counts["NO_PROOF_EXPERIMENT_PRECONDITION"]
            ),
            "denominator": len(selected),
        },
    }
    return result


def encode_receipt(value: dict[str, Any]) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n"


def audit_ledger_bytes(ledger_data: bytes, script_data: bytes) -> dict[str, Any]:
    if ledger_data.count(MARKER) != 1:
        raise TaxonomyError("append-only marker is absent or duplicated")
    header_bytes, log_body = ledger_data.split(MARKER, 1)
    try:
        header = header_bytes.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise TaxonomyError("ledger header is not UTF-8") from exc
    lines = log_body.splitlines(keepends=True)
    taxonomy_indexes = [
        index
        for index, line in enumerate(lines)
        if b" | " + TAXONOMY_ACTION.encode() + b" | " in line
    ]
    if len(taxonomy_indexes) != 1:
        raise TaxonomyError("taxonomy implementation row is absent or duplicated")
    taxonomy_index = taxonomy_indexes[0]
    historical_bytes = b"".join(lines[:taxonomy_index])
    scoped_lines = lines[: taxonomy_index + 1]
    all_rows, legacy_transfers, legacy_evidence = parse_log_rows(lines)
    for row in all_rows:
        row_kind(row)
    audit_review_obligations(all_rows)
    audit_attempt_inventory(all_rows)
    rows = all_rows[: taxonomy_index + 1]
    historical_identity = identity(historical_bytes)
    if taxonomy_index != HISTORICAL_ROW_COUNT:
        raise TaxonomyError("historical log row count changed")
    if historical_identity != {
        "size": HISTORICAL_BYTE_COUNT,
        "sha256": HISTORICAL_SHA256,
    }:
        raise TaxonomyError("historical append-only log bytes changed")
    taxonomy_row = rows[-1]
    if (
        taxonomy_row["campaign"] != "s22plus-fyg8-p318"
        or taxonomy_row["ordinal"] != "h0-ledger-taxonomy-7"
        or taxonomy_row["tier"] != "H0"
        or taxonomy_row["action"] != TAXONOMY_ACTION
        or taxonomy_row["health"] != "HEALTHY"
        or taxonomy_row["raw_evidence_outcome"] != "PROVED"
        or taxonomy_row["candidate_transfers"] != 0
        or taxonomy_row["rollback_transfers"] != 0
    ):
        raise TaxonomyError("taxonomy implementation row changed")

    corrections = parse_corrections(header, rows)
    attempt_inventory = audit_attempt_inventory(rows)
    attempts = audit_attempts(rows, corrections)
    p310_p316 = cohort(
        attempts, [f"s22plus-fyg8-p{number}" for number in range(310, 317)]
    )
    p310_p317 = cohort(
        attempts, [f"s22plus-fyg8-p{number}" for number in range(310, 318)]
    )
    if p310_p316["effective_class_counts"] != {
        "PROVED": 0,
        "REFUTED": 2,
        "NO_PROOF_EXPERIMENT_PRECONDITION": 1,
        "NO_PROOF_OBSERVER": 4,
    }:
        raise TaxonomyError("P3.10-P3.16 audited 4:1:2 accounting changed")
    if p310_p317["effective_class_counts"] != {
        "PROVED": 0,
        "REFUTED": 2,
        "NO_PROOF_EXPERIMENT_PRECONDITION": 1,
        "NO_PROOF_OBSERVER": 5,
    }:
        raise TaxonomyError("P3.10-P3.17 audited 5:1:2 accounting changed")

    row_kinds = Counter(row_kind(row) for row in rows)
    review_states = Counter(
        capability_review_state(row["tier"], row["action"]) for row in rows
    )
    scoped_review_obligations = audit_review_obligations(rows)
    subresult_corrections = [
        correction for correction in corrections if correction["scope"] == "SUBRESULT_ONLY"
    ]
    scope_bytes = header_bytes + MARKER + b"".join(scoped_lines)
    return {
        "schema": SCHEMA,
        "derivation_version": DERIVATION_VERSION,
        "verdict": VERDICT,
        "status": STATUS,
        "authority": {
            "ledger_taxonomy_scope": identity(scope_bytes),
            "historical_log_prefix": {
                **historical_identity,
                "row_count": taxonomy_index,
            },
            "script": identity(script_data),
            "scope_ends_at": {
                "timestamp": taxonomy_row["timestamp"],
                "campaign": taxonomy_row["campaign"],
                "ordinal": taxonomy_row["ordinal"],
                "action": taxonomy_row["action"],
            },
        },
        "axes": {
            "device_health": "independent ledger health field",
            "row_kind": (
                "derived from tier, transfer phase, and the exact correction registry; "
                "H0 review labels and action substrings are excluded"
            ),
            "raw_evidence_outcome": "immutable row-local proof spelling",
            "effective_experiment_proof": (
                "terminal device attempt plus CAMPAIGN_PROOF correction only"
            ),
            "capability_review_state": "independent H0 action-name state",
            "review_obligation_state": (
                "campaign-serialized pending to next PASS_GO resolution"
            ),
        },
        "correction_registry": corrections,
        "subresult_only_corrections": subresult_corrections,
        "attempts": attempts,
        "attempt_inventory": {
            "eligibility": "maximum candidate_transfers is at least one",
            "open_attempts_enter_metric_denominators": True,
            "state_counts": dict(
                sorted(Counter(item["attempt_state"] for item in attempt_inventory).items())
            ),
            "items": attempt_inventory,
        },
        "cohorts": {
            "p310_through_p316": p310_p316,
            "p310_through_p317": p310_p317,
        },
        "localization_audit": audit_localizations(rows),
        "legacy_missing_transfer_rows": legacy_transfers,
        "legacy_evidence_rows": legacy_evidence,
        "post_scope_validation": (
            "all appended rows, review obligations, and attempt states are validated "
            "without changing scoped receipt bytes"
        ),
        "scoped_review_obligations": scoped_review_obligations,
        "predecessor": {
            "derivation_version": 1,
            "approved_receipt": {
                "size": 10118,
                "sha256": (
                    "4214ea5393ed2ec9f1bdef2357e711494050d483cf39b18c46fc9324bf94a153"
                ),
            },
            "approved_auditor": {
                "size": 34654,
                "sha256": (
                    "80faa898e23f96d95437bd13c1c87fe8906b1b12802123db53f44fed61c1c06c"
                ),
            },
            "reproducible_from_current_header_and_auditor": False,
        },
        "scoped_row_counts": {
            "total": len(rows),
            "by_kind": dict(sorted(row_kinds.items())),
            "by_capability_review_state": dict(sorted(review_states.items())),
        },
        "safety": {
            "host_only": True,
            "device_actions": 0,
            "candidate_or_rollback_transfers": 0,
            "p318_execution_critical_bytes_changed": False,
            "live_authority_created": False,
            "candidate_artifact_identity_present_in_ledger": False,
            "candidate_identity_replay_audited": False,
            "independent_review_required": True,
            "a90_actions": 0,
            "s20plus_actions": 0,
        },
    }


def build_receipt(ledger: Path = DEFAULT_LEDGER) -> dict[str, Any]:
    ledger_data = stable_read(ledger, "campaign ledger", 2**20)
    script_data = stable_read(Path(__file__), "taxonomy auditor", 2**20)
    return audit_ledger_bytes(ledger_data, script_data)


def publish_exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o400,
    )
    try:
        written = 0
        while written < len(data):
            count = os.write(descriptor, data[written:])
            if count <= 0:
                raise TaxonomyError("receipt write made no progress")
            written += count
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.link(temporary, path, follow_symlinks=False)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--out", type=Path)
    arguments = parser.parse_args()
    try:
        value = build_receipt(arguments.ledger)
        data = encode_receipt(value)
        if arguments.out is not None:
            publish_exclusive(arguments.out, data)
    except (OSError, TaxonomyError, UnicodeError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(value, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
