"""Failure classification helpers for mixed-soak evidence."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FailureClassification:
    source: str
    kind: str
    severity: str
    summary: str
    detail: str
    action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _module_name(event: dict[str, Any]) -> str:
    return _text(event.get("workload") or event.get("name") or "unknown")


def _event_detail(event: dict[str, Any]) -> str:
    parts = [_text(event.get("detail"))]
    module = event.get("module")
    if isinstance(module, dict):
        for step in module.get("steps", []):
            if isinstance(step, dict):
                parts.append(_text(step.get("detail")))
                parts.append(_text(step.get("error")))
    return " ".join(part for part in parts if part)


def classify_workload_event(event: dict[str, Any]) -> FailureClassification | None:
    workload = _module_name(event)
    detail = _event_detail(event)
    gate = event.get("gate") if isinstance(event.get("gate"), dict) else {}
    reasons = " ".join(_text(reason) for reason in gate.get("reasons", []))
    metadata = gate.get("metadata") if isinstance(gate.get("metadata"), dict) else {}
    requires_ncm = metadata.get("requires_ncm") is True or "ncm" in event.get("resource_locks", [])

    if event.get("status") == "blocked":
        if requires_ncm and "requires host USB NCM precondition" in reasons:
            return FailureClassification(
                source=f"workload:{workload}",
                kind="policy-blocked",
                severity="deferred",
                summary="workload blocked by explicit NCM safety gate",
                detail=reasons,
                action="rerun with --allow-ncm only after host NCM is configured",
            )
        return FailureClassification(
            source=f"workload:{workload}",
            kind="policy-blocked",
            severity="deferred",
            summary="workload blocked by safety policy",
            detail=reasons or detail,
            action="inspect required_flags and rerun only when the precondition is intentionally satisfied",
        )

    if event.get("skipped") is True and re.search(r"NCM path .*not reachable|192\\.168\\.7\\.2", detail):
        return FailureClassification(
            source=f"workload:{workload}",
            kind="env-ncm-missing",
            severity="deferred",
            summary="NCM workload skipped because host-to-device NCM path is absent",
            detail=detail,
            action="run ncm_host_setup.py setup and confirm ping 192.168.7.2 before full NCM validation",
        )

    if event.get("ok") is not True:
        lower = detail.lower()
        if "connection reset" in lower or "connection refused" in lower:
            kind = "bridge-disconnect"
            action = "check serial bridge, USB ACM state, and external bridge-client locking"
        elif "timeout" in lower:
            kind = "bridge-timeout"
            action = "check bridge responsiveness and last observer sample"
        elif "memory-mismatch" in lower or "sha" in lower:
            kind = "storage-mismatch"
            action = "inspect storage workload report and SD health before continuing"
        else:
            kind = "workload-failed"
            action = "inspect module failed_steps and command transcripts"
        return FailureClassification(
            source=f"workload:{workload}",
            kind=kind,
            severity="fail",
            summary="workload failed",
            detail=detail,
            action=action,
        )
    return None


def classify_observer_sample(sample: dict[str, Any]) -> FailureClassification | None:
    if sample.get("ok") is True:
        return None
    name = _text(sample.get("name") or "unknown")
    detail = _text(sample.get("error") or sample.get("text_excerpt"))
    lower = detail.lower()
    if "connection reset" in lower or "connection refused" in lower:
        kind = "serial-disconnect"
        action = "verify ACM bridge and device USB state"
    elif "timeout" in lower:
        kind = "bridge-timeout"
        action = "inspect bridge logs and device status around the timeout"
    elif sample.get("rc") not in (0, None) or sample.get("status") not in ("ok", None):
        kind = "device-command-failed"
        action = "inspect observer command transcript and device rc/status"
    else:
        kind = "observer-failed"
        action = "inspect observer sample excerpt"
    return FailureClassification(
        source=f"observer:{name}",
        kind=kind,
        severity="fail",
        summary="observer sample failed",
        detail=detail[:4096],
        action=action,
    )


def load_observer_samples(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    samples: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("type") == "observer_sample":
            samples.append(payload)
    return samples


def summarize_classifications(classifications: list[FailureClassification]) -> dict[str, Any]:
    by_kind: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for item in classifications:
        by_kind[item.kind] = by_kind.get(item.kind, 0) + 1
        by_severity[item.severity] = by_severity.get(item.severity, 0) + 1
    return {
        "count": len(classifications),
        "by_kind": by_kind,
        "by_severity": by_severity,
        "has_failures": any(item.severity == "fail" for item in classifications),
        "has_deferred": any(item.severity == "deferred" for item in classifications),
    }


def classify_mixed_soak(events: list[dict[str, Any]], observer_samples: list[dict[str, Any]]) -> dict[str, Any]:
    classifications: list[FailureClassification] = []
    for event in events:
        item = classify_workload_event(event)
        if item is not None:
            classifications.append(item)
    for sample in observer_samples:
        item = classify_observer_sample(sample)
        if item is not None:
            classifications.append(item)

    last_ok_sample: dict[str, Any] | None = None
    for sample in observer_samples:
        if sample.get("ok") is True:
            last_ok_sample = {
                "cycle": sample.get("cycle"),
                "seq": sample.get("seq"),
                "name": sample.get("name"),
                "host_ts": sample.get("host_ts"),
                "duration_sec": sample.get("duration_sec"),
            }
    return {
        "schema": "a90-failure-classification-v182",
        "summary": summarize_classifications(classifications),
        "classifications": [item.to_dict() for item in classifications],
        "last_ok_observer_sample": last_ok_sample,
    }
