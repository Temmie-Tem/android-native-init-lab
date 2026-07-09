#!/usr/bin/env python3
"""Classify S22+ M34 S10C0 direct-finit loader-audit result.json.

This is host-only post-processing. It never talks to a device and never
authorizes a live run. The purpose is to turn the S10C0 one-bit beacon result
into the next S10/S11 loader-mechanism decision without relying on ad-hoc
text-log parsing.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from s22plus_m34_s10c0_direct_finit_loader_audit_live_gate import (
    EXPECTED_M34_AP_SHA256,
    EXPECTED_M34_BASE_BOOT_SHA256,
    EXPECTED_M34_BOOT_SHA256,
    EXPECTED_M34_INIT_SHA256,
    EXPECTED_PROBE,
    EXPECTED_PROBE_MODULE,
    EXPECTED_PROBE_PROC_NAME,
    EXPECTED_STAGE,
    EXPECTED_TARGET,
    ROLLBACK_MAGISK,
    ROLLBACK_STOCK,
)


EXPECTED_SCHEMA = "s22plus_m34_s10c0_result_v1"
ANALYSIS_SCHEMA = "s22plus_m34_s10c0_result_analysis_v1"
VALID_ROLLBACK_TARGETS = {ROLLBACK_MAGISK, ROLLBACK_STOCK}
DISPLAY_SERIAL_REDACTED = "<S22_SERIAL_REDACTED>"

DECISION_FINIT_ACCEPTED_PROCEED_S11 = "s22plus-m34-s10c0-cmd-db-finit-accepted-proceed-s11"
DECISION_FINIT_MISS_PROCEED_S11 = "s22plus-m34-s10c0-cmd-db-finit-miss-proceed-s11-errno-capture"
DECISION_ROLLBACK_ONLY = "s22plus-m34-s10c0-rollback-only-no-direct-finit-proof"
DECISION_RECOVERY_REQUIRED = "s22plus-m34-s10c0-rollback-incomplete-recovery-required"
DECISION_NO_PROOF = "s22plus-m34-s10c0-no-direct-finit-proof"
DECISION_INVALID = "s22plus-m34-s10c0-invalid-result-evidence"

REQUIRED_LIVE_PROOF_EVENTS = (
    "live_session_start",
    "candidate_flash_start",
    "candidate_flash_done",
    "candidate_boot_ready",
    "rollback_flash_start",
    "rollback_flash_done",
    "rollback_boot_ready",
    "live_session_end",
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"missing JSON file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"JSON top-level must be object: {path}")
    return data


def parse_utc_timestamp(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def validate_result_payload(payload: dict[str, Any]) -> list[str]:
    expected = {
        "schema": EXPECTED_SCHEMA,
        "target": EXPECTED_TARGET,
        "stage": EXPECTED_STAGE,
        "candidate_ap_sha256": EXPECTED_M34_AP_SHA256,
        "candidate_boot_sha256": EXPECTED_M34_BOOT_SHA256,
        "candidate_init_sha256": EXPECTED_M34_INIT_SHA256,
        "base_boot_sha256": EXPECTED_M34_BASE_BOOT_SHA256,
        "module_load_probe": EXPECTED_PROBE,
        "probe_module": EXPECTED_PROBE_MODULE,
        "probe_proc_name": EXPECTED_PROBE_PROC_NAME,
    }
    errors: list[str] = []
    for key, value in expected.items():
        if payload.get(key) != value:
            errors.append(f"{key} mismatch: {payload.get(key)!r} != {value!r}")
    if not isinstance(payload.get("result"), str) or not payload.get("result"):
        errors.append("result must be a non-empty string")
    if not isinstance(payload.get("rc"), int):
        errors.append("rc must be an integer")
    rollback_target = payload.get("rollback_target")
    if rollback_target not in VALID_ROLLBACK_TARGETS:
        errors.append(f"rollback_target must be one of {sorted(VALID_ROLLBACK_TARGETS)!r}")
    if payload.get("rc") == 0 and not isinstance(payload.get("android_serial"), str):
        errors.append("android_serial must be present when rc is 0")
    elif isinstance(payload.get("android_serial"), str) and not payload.get("android_serial"):
        errors.append("android_serial must be non-empty when present")
    return errors


def validate_timeline_payload(payload: dict[str, Any] | None) -> tuple[list[str], list[str]]:
    if payload is None:
        return [], ["timeline.json missing"]
    if set(payload.keys()) != {"events"}:
        return [], ["timeline top-level keys must be exactly ['events']"]
    events = payload.get("events")
    if not isinstance(events, list):
        return [], ["timeline events must be a list"]
    names: list[str] = []
    errors: list[str] = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            errors.append(f"timeline event {index} must be an object")
            continue
        if set(event.keys()) != {"name", "timestamp_utc"}:
            errors.append(f"timeline event {index} keys must be name,timestamp_utc")
            continue
        name = event.get("name")
        timestamp = event.get("timestamp_utc")
        if not isinstance(name, str) or not name:
            errors.append(f"timeline event {index} has invalid name")
        else:
            names.append(name)
        if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
            errors.append(f"timeline event {index} has invalid timestamp_utc")
        else:
            try:
                parse_utc_timestamp(timestamp)
            except ValueError:
                errors.append(f"timeline event {index} has unparsable timestamp_utc")
    return names, errors


def missing_required_live_events(names: list[str]) -> list[str]:
    present = set(names)
    return [name for name in REQUIRED_LIVE_PROOF_EVENTS if name not in present]


def duplicate_required_live_events(names: list[str]) -> list[str]:
    return [name for name in REQUIRED_LIVE_PROOF_EVENTS if names.count(name) > 1]


def required_live_events_in_order(names: list[str]) -> bool:
    required_index = 0
    for name in names:
        if name == REQUIRED_LIVE_PROOF_EVENTS[required_index]:
            required_index += 1
            if required_index == len(REQUIRED_LIVE_PROOF_EVENTS):
                return True
    return False


def required_live_event_timestamps_monotonic(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    events = payload.get("events")
    if not isinstance(events, list):
        return False
    required_index = 0
    previous: datetime | None = None
    for event in events:
        if not isinstance(event, dict):
            continue
        if event.get("name") != REQUIRED_LIVE_PROOF_EVENTS[required_index]:
            continue
        timestamp = event.get("timestamp_utc")
        if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
            return False
        try:
            current = parse_utc_timestamp(timestamp)
        except ValueError:
            return False
        if previous is not None and current < previous:
            return False
        previous = current
        required_index += 1
        if required_index == len(REQUIRED_LIVE_PROOF_EVENTS):
            return True
    return False


def timeline_timestamps_monotonic(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    events = payload.get("events")
    if not isinstance(events, list):
        return False
    previous: datetime | None = None
    for event in events:
        if not isinstance(event, dict):
            return False
        timestamp = event.get("timestamp_utc")
        if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
            return False
        try:
            current = parse_utc_timestamp(timestamp)
        except ValueError:
            return False
        if previous is not None and current < previous:
            return False
        previous = current
    return True


def classify_result(payload: dict[str, Any], timeline: dict[str, Any] | None = None) -> dict[str, Any]:
    result_errors = validate_result_payload(payload)
    timeline_names, timeline_errors = validate_timeline_payload(timeline)
    result = payload.get("result")
    rc = payload.get("rc")
    rollback_target = payload.get("rollback_target")
    android_serial = payload.get("android_serial")
    display_android_serial = DISPLAY_SERIAL_REDACTED if isinstance(android_serial, str) else android_serial
    magisk_baseline_restored = rollback_target == ROLLBACK_MAGISK and isinstance(android_serial, str) and bool(android_serial)
    analysis: dict[str, Any] = {
        "schema": ANALYSIS_SCHEMA,
        "input_schema": payload.get("schema"),
        "target": payload.get("target"),
        "stage": payload.get("stage"),
        "result": result,
        "rc": rc,
        "rollback_target": rollback_target,
        "android_serial": display_android_serial,
        "ok_to_advance": False,
        "ok_to_live_next_stage": False,
        "magisk_baseline_restored": magisk_baseline_restored,
        "requires_magisk_baseline_restore": False,
        "cmd_db_direct_finit_observed": False,
        "cmd_db_direct_finit_accepted": None,
        "next_stage": None,
        "next_probe": None,
        "decision": DECISION_INVALID if result_errors else DECISION_NO_PROOF,
        "errors": result_errors,
        "timeline_errors": timeline_errors,
        "missing_required_live_events": [],
        "duplicate_required_live_events": [],
        "required_live_events_in_order": False,
        "required_live_event_timestamps_monotonic": False,
        "timeline_timestamps_monotonic": False,
    }
    if result_errors:
        analysis["next_action"] = "fix result.json evidence before interpreting S10C0"
        return analysis

    live_result = result in {
        "download-beacon-hit",
        "download-beacon-miss-parked-manual-download-required",
    }
    if live_result:
        analysis["cmd_db_direct_finit_observed"] = True
        analysis["cmd_db_direct_finit_accepted"] = result == "download-beacon-hit"
        missing = missing_required_live_events(timeline_names)
        duplicates = duplicate_required_live_events(timeline_names)
        analysis["missing_required_live_events"] = missing
        analysis["duplicate_required_live_events"] = duplicates
        analysis["required_live_events_in_order"] = not missing and not duplicates and required_live_events_in_order(timeline_names)
        analysis["required_live_event_timestamps_monotonic"] = (
            not missing and not duplicates and required_live_event_timestamps_monotonic(timeline)
        )
        analysis["timeline_timestamps_monotonic"] = not timeline_errors and timeline_timestamps_monotonic(timeline)
        if rc != 0:
            analysis["decision"] = DECISION_RECOVERY_REQUIRED
            analysis["next_action"] = "recover/rollback and re-establish Android baseline before any S10 follow-up"
            return analysis
        if (
            timeline_errors
            or missing
            or duplicates
            or not analysis["required_live_events_in_order"]
            or not analysis["required_live_event_timestamps_monotonic"]
            or not analysis["timeline_timestamps_monotonic"]
        ):
            analysis["decision"] = DECISION_NO_PROOF
            analysis["next_action"] = "do not advance; preserve run directory and inspect timeline/result evidence"
            return analysis
        if result == "download-beacon-hit":
            analysis.update(
                {
                    "decision": DECISION_FINIT_ACCEPTED_PROCEED_S11,
                    "ok_to_advance": True,
                    "ok_to_live_next_stage": magisk_baseline_restored,
                    "requires_magisk_baseline_restore": not magisk_baseline_restored,
                    "next_stage": "S11",
                    "next_probe": "per_module_rc_positive_control",
                }
            )
            if magisk_baseline_restored:
                analysis["next_action"] = (
                    "S10C0 HIT: cmd-db.ko direct finit was accepted; build S11 host-only "
                    "to distinguish load-loop skip vs /proc/modules observation artifact"
                )
            else:
                analysis["next_action"] = (
                    "S10C0 HIT proof is valid; restore/verify Magisk baseline before any S11 live gate"
                )
            return analysis
        analysis.update(
            {
                "decision": DECISION_FINIT_MISS_PROCEED_S11,
                "ok_to_advance": True,
                "ok_to_live_next_stage": magisk_baseline_restored,
                "requires_magisk_baseline_restore": not magisk_baseline_restored,
                "next_stage": "S11",
                "next_probe": "cmd_db_direct_finit_errno_capture",
            }
        )
        if magisk_baseline_restored:
            analysis["next_action"] = (
                "S10C0 MISS: cmd-db.ko direct finit was not accepted or not reached; "
                "build S11 host-only to surface attempted/rc/errno and a positive-control module"
            )
        else:
            analysis["next_action"] = (
                "S10C0 MISS evidence is valid; restore/verify Magisk baseline before any S11 live gate"
            )
        return analysis

    if result == "rollback-from-download-completed":
        analysis["decision"] = DECISION_ROLLBACK_ONLY
        analysis["next_action"] = "rollback-only evidence does not prove cmd-db direct finit; rerun or locate the original live result"
        return analysis

    if rc != 0:
        analysis["decision"] = DECISION_RECOVERY_REQUIRED
        analysis["next_action"] = "recover/rollback and re-establish Android baseline before interpreting cmd-db direct finit"
        return analysis

    analysis["next_action"] = "no S10C0 beacon proof; inspect run logs before designing S11"
    return analysis


def default_timeline_for(result_json: Path) -> Path | None:
    candidate = result_json.parent / "timeline.json"
    return candidate if candidate.is_file() else None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_json", type=Path)
    parser.add_argument("--timeline-json", type=Path)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--json", action="store_true", help="print full JSON analysis")
    parser.add_argument(
        "--require-advance",
        action="store_true",
        help="exit nonzero unless the evidence is sufficient to advance the S10 loader-mechanism",
    )
    parser.add_argument(
        "--require-live-next-stage",
        action="store_true",
        help="exit nonzero unless the evidence and rollback state are sufficient for the next live gate",
    )
    args = parser.parse_args(argv)

    result_json = args.result_json
    timeline_json = args.timeline_json if args.timeline_json is not None else default_timeline_for(result_json)
    result_payload = load_json(result_json)
    timeline_payload = load_json(timeline_json) if timeline_json is not None else None
    analysis = classify_result(result_payload, timeline_payload)
    analysis["result_json"] = str(result_json)
    analysis["timeline_json"] = str(timeline_json) if timeline_json is not None else None

    if args.write_report:
        report_path = result_json.parent / "s22plus_m34_s10c0_result_analysis.json"
        report_path.write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        analysis["analysis_json"] = str(report_path)

    if args.json or args.write_report:
        print(json.dumps(analysis, indent=2, sort_keys=True))
    else:
        print(analysis["decision"])
    if analysis["decision"] == DECISION_INVALID:
        return 1
    if args.require_live_next_stage and not analysis["ok_to_live_next_stage"]:
        return 3
    if args.require_advance and not analysis["ok_to_advance"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
