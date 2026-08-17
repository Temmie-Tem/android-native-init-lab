#!/usr/bin/env python3
"""Bind the passive host USB trace to one future P3.00 F1 attempt."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping, Sequence

import device_action_raw_capture_v1 as raw_capture
import device_action_usb_trace_sidecar_v1 as sidecar
import s22plus_fyg8_p300_source_contract as contract


SCHEMA = "s22plus_fyg8_p300_usb_trace_binding_v1"
OBSERVATION_WITNESS_SCHEMA = (
    "s22plus_fyg8_p300_candidate_observation_durable_v1"
)
VERDICT = "PASS_P300_USB_TRACE_SAME_ATTEMPT_BINDING_HOST_ONLY"
TARGET = {
    "model": "SM-S906N",
    "device": "g0q",
    "firmware": "S906NKSS7FYG8",
}
EVENT_WINDOW = {
    "start_after_or_at": "live_session_start",
    "start_before_or_at": "candidate_flash_start",
    "end_after_or_at": "candidate_flash_done",
    "end_before_or_at": "candidate_boot_ready",
}
WINDOW = {
    **EVENT_WINDOW,
    "observation_durable_witness_required": True,
}
IDENTIFIER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}")
DIGEST_RE = re.compile(r"[0-9a-f]{64}")


class BindingError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
        + b"\n"
    )


def _digest(value: str, label: str) -> str:
    if DIGEST_RE.fullmatch(value) is None:
        raise BindingError(f"{label} is not a lowercase SHA-256")
    return value


def _identifier(value: str, label: str) -> str:
    if IDENTIFIER_RE.fullmatch(value) is None:
        raise BindingError(f"{label} is not canonical")
    return value


def _private_relative(value: str, label: str) -> str:
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or len(path.parts) < 3
        or path.parts[:2] != ("workspace", "private")
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise BindingError(f"{label} is not a canonical private path")
    return path.as_posix()


def _artifact(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    if set(value) != {"sha256", "size"}:
        raise BindingError(f"{label} receipt fields differ")
    size = value["size"]
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise BindingError(f"{label} size is invalid")
    return {"sha256": _digest(str(value["sha256"]), label), "size": size}


def _source_receipt() -> dict[str, Any]:
    payload = Path(sidecar.__file__).resolve().read_bytes()
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def create_binding(
    *,
    campaign_id: str,
    attempt_id: str,
    candidate_ap: Mapping[str, Any],
    approval_binding_sha256: str,
    transaction_path: str,
    sidecar_result_path: str,
    observation_witness_path: str,
) -> dict[str, Any]:
    value = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "contract_id": contract.CONTRACT_ID,
        "campaign_id": _identifier(campaign_id, "campaign ID"),
        "attempt_id": _identifier(attempt_id, "attempt ID"),
        "candidate_transfer_attempt": 1,
        "candidate_ap": _artifact(candidate_ap, "candidate AP"),
        "approval_binding_sha256": _digest(
            approval_binding_sha256, "approval binding"
        ),
        "transaction_path": _private_relative(
            transaction_path, "transaction path"
        ),
        "sidecar_result_path": _private_relative(
            sidecar_result_path, "sidecar result path"
        ),
        "observation_witness_path": _private_relative(
            observation_witness_path, "observation witness path"
        ),
        "sidecar_source": _source_receipt(),
        "window": WINDOW,
        "prepared_manifest_receipt_binding_required": True,
        "same_attempt_runtime_verification_required": True,
        "non_authoritative": True,
        "device_actions": False,
        "live_authority_created": False,
    }
    value["binding_sha256"] = hashlib.sha256(_canonical(value)).hexdigest()
    return value


def verify_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    expected_keys = {
        "schema",
        "verdict",
        "target",
        "contract_id",
        "campaign_id",
        "attempt_id",
        "candidate_transfer_attempt",
        "candidate_ap",
        "approval_binding_sha256",
        "transaction_path",
        "sidecar_result_path",
        "observation_witness_path",
        "sidecar_source",
        "window",
        "prepared_manifest_receipt_binding_required",
        "same_attempt_runtime_verification_required",
        "non_authoritative",
        "device_actions",
        "live_authority_created",
        "binding_sha256",
    }
    if set(value) != expected_keys:
        raise BindingError("sidecar binding fields differ")
    recreated = create_binding(
        campaign_id=str(value["campaign_id"]),
        attempt_id=str(value["attempt_id"]),
        candidate_ap=_artifact(value["candidate_ap"], "candidate AP"),
        approval_binding_sha256=str(value["approval_binding_sha256"]),
        transaction_path=str(value["transaction_path"]),
        sidecar_result_path=str(value["sidecar_result_path"]),
        observation_witness_path=str(value["observation_witness_path"]),
    )
    if dict(value) != recreated:
        raise BindingError("sidecar binding content or source receipt differs")
    return recreated


def owner_token(value: Mapping[str, Any]) -> str:
    bound = verify_binding(value)
    return hashlib.sha256(
        _canonical(
            {
                "domain": "S22PLUS-FYG8-P300-USB-TRACE-OWNER-V1",
                "binding_sha256": bound["binding_sha256"],
                "approval_binding_sha256": bound["approval_binding_sha256"],
                "transaction_path": bound["transaction_path"],
            }
        )
    ).hexdigest()


def owner_token_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(owner_token(value).encode("ascii")).hexdigest()


def verify_observation_witness(
    binding: Mapping[str, Any], value: Mapping[str, Any]
) -> dict[str, Any]:
    bound = verify_binding(binding)
    expected_keys = {
        "schema",
        "binding_sha256",
        "approval_binding_sha256",
        "candidate_ap",
        "timestamp_utc",
        "live_state_sha256",
        "durable",
        "device_actions",
    }
    if (
        set(value) != expected_keys
        or value.get("schema") != OBSERVATION_WITNESS_SCHEMA
        or value.get("binding_sha256") != bound["binding_sha256"]
        or value.get("approval_binding_sha256")
        != bound["approval_binding_sha256"]
        or value.get("candidate_ap") != bound["candidate_ap"]
        or not isinstance(value.get("timestamp_utc"), str)
        or not value["timestamp_utc"].endswith("Z")
        or DIGEST_RE.fullmatch(str(value.get("live_state_sha256"))) is None
        or value.get("durable") is not True
        or value.get("device_actions") is not False
    ):
        raise BindingError("candidate observation witness differs")
    return dict(value)


def _read_bound_file(
    path: Path,
    expected: Mapping[str, Any],
    label: str,
    maximum: int,
) -> tuple[bytes, dict[str, Any]]:
    direct = path.absolute()
    if (
        direct.is_symlink()
        or not direct.is_file()
        or direct.resolve(strict=True) != direct
    ):
        raise BindingError(f"{label} is missing or indirect")
    payload = direct.read_bytes()
    if len(payload) > maximum:
        raise BindingError(f"{label} exceeds its bound")
    actual = {
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    if {name: expected.get(name) for name in actual} != actual:
        raise BindingError(f"{label} receipt differs")
    return payload, actual


def _load_bound_raw_capture(
    destination: Path,
    value: Any,
    name: str,
    *,
    maximum: int,
) -> tuple[raw_capture.RawCaptureHandle, bytes, bytes, dict[str, Any]]:
    path = destination / f"{name}.capture.json"
    if (
        not isinstance(value, dict)
        or set(value) != {"path", "size", "sha256"}
        or value.get("path") != str(path)
    ):
        raise BindingError(f"sidecar {name} raw receipt shape differs")
    _payload, receipt = _read_bound_file(
        path, value, f"sidecar {name} raw receipt", 64 * 1024
    )
    try:
        handle = raw_capture.load_handle(path)
        stdout = raw_capture.read_stdout(handle, maximum=maximum)
        stderr = raw_capture.read_stderr(handle, maximum=maximum)
    except raw_capture.RawCaptureError as exc:
        raise BindingError(f"sidecar {name} raw capture differs") from exc
    if handle.name != name:
        raise BindingError(f"sidecar {name} raw capture name differs")
    return handle, stdout, stderr, receipt


def verify_capture_directory(
    binding: Mapping[str, Any],
    sidecar_result: Mapping[str, Any],
    *,
    root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    bound = verify_binding(binding)
    repository = root.resolve(strict=True)
    destination = output_dir.absolute()
    expected_result = repository / bound["sidecar_result_path"]
    if (
        destination.is_symlink()
        or not destination.is_dir()
        or destination.resolve(strict=True) != destination
        or destination / "result.json" != expected_result
    ):
        raise BindingError("sidecar result directory differs from binding")
    result_payload, result_receipt = _read_bound_file(
        expected_result,
        {
            "size": expected_result.stat().st_size,
            "sha256": hashlib.sha256(expected_result.read_bytes()).hexdigest(),
        },
        "sidecar result",
        sidecar.MAX_SNAPSHOT_BYTES,
    )
    try:
        reopened = json.loads(result_payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BindingError("sidecar result is not JSON") from exc
    if reopened != dict(sidecar_result):
        raise BindingError("sidecar result changed after capture")
    expected_result_keys = {
        "schema",
        "phase",
        "started_utc",
        "ended_utc",
        "elapsed_sec",
        "requested_duration_sec",
        "stop_reason",
        "non_authoritative",
        "device_actions",
        "opens_candidate_acm",
        "contains_private_usb_identifiers",
        "public_raw_export_forbidden",
        "owner_token_sha256",
        "process_group_id",
        "session_id",
        "supporting",
        "sources",
    }
    if (
        set(reopened) != expected_result_keys
        or reopened.get("schema") != sidecar.SCHEMA
        or reopened.get("phase") != "complete"
        or reopened.get("non_authoritative") is not True
        or reopened.get("device_actions") is not False
        or reopened.get("opens_candidate_acm") is not False
        or reopened.get("contains_private_usb_identifiers") is not True
        or reopened.get("public_raw_export_forbidden") is not True
        or reopened.get("owner_token_sha256") != owner_token_sha256(bound)
        or isinstance(reopened.get("process_group_id"), bool)
        or not isinstance(reopened.get("process_group_id"), int)
        or reopened.get("process_group_id") <= 0
        or reopened.get("session_id") != reopened.get("process_group_id")
        or reopened.get("stop_reason") != "signal:SIGTERM"
    ):
        raise BindingError("sidecar result safety fields differ")

    supporting = reopened.get("supporting")
    expected_support = {
        "start": "start.json",
        "armed": "armed.json",
        "lsusb_start": "lsusb-start.json",
        "lsusb_end": "lsusb-end.json",
    }
    if not isinstance(supporting, dict) or set(supporting) != set(expected_support):
        raise BindingError("sidecar supporting receipt set differs")
    supporting_receipts: dict[str, Any] = {}
    for name, filename in expected_support.items():
        expected = supporting[name]
        if not isinstance(expected, dict) or expected.get("name") != filename:
            raise BindingError(f"sidecar {name} receipt shape differs")
        payload, actual = _read_bound_file(
            destination / filename,
            expected,
            f"sidecar {name}",
            sidecar.MAX_SNAPSHOT_BYTES,
        )
        supporting_receipts[name] = actual
        if name == "start":
            try:
                start = json.loads(payload.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise BindingError("sidecar start receipt is not JSON") from exc
            if (
                start.get("schema") != sidecar.SCHEMA
                or start.get("phase") != "start"
                or start.get("started_utc") != reopened["started_utc"]
                or start.get("non_authoritative") is not True
                or start.get("device_actions") is not False
                or start.get("opens_candidate_acm") is not False
                or start.get("owner_token_sha256")
                != owner_token_sha256(bound)
            ):
                raise BindingError("sidecar start receipt differs")
        elif name == "armed":
            try:
                armed = json.loads(payload.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise BindingError("sidecar armed receipt is not JSON") from exc
            source_arms = armed.get("sources")
            if (
                set(armed)
                != {
                    "schema",
                    "phase",
                    "armed_utc",
                    "owner_token_sha256",
                    "process_group_id",
                    "session_id",
                    "non_authoritative",
                    "device_actions",
                    "opens_candidate_acm",
                    "sources",
                }
                or armed.get("schema") != sidecar.SCHEMA
                or armed.get("phase") != "armed"
                or armed.get("owner_token_sha256")
                != owner_token_sha256(bound)
                or armed.get("process_group_id")
                != reopened["process_group_id"]
                or armed.get("session_id") != reopened["session_id"]
                or armed.get("non_authoritative") is not True
                or armed.get("device_actions") is not False
                or armed.get("opens_candidate_acm") is not False
                or not isinstance(source_arms, dict)
                or set(source_arms) != set(sidecar.SOURCE_COMMANDS)
            ):
                raise BindingError("sidecar armed receipt differs")
            for source_arm in source_arms.values():
                if (
                    not isinstance(source_arm, dict)
                    or set(source_arm)
                    != {
                        "pid",
                        "process_group_id",
                        "session_id",
                        "alive",
                        "started_utc",
                    }
                    or isinstance(source_arm.get("pid"), bool)
                    or not isinstance(source_arm.get("pid"), int)
                    or source_arm["pid"] <= 0
                    or source_arm.get("process_group_id")
                    != reopened["process_group_id"]
                    or source_arm.get("session_id") != reopened["session_id"]
                    or source_arm.get("alive") is not True
                    or not isinstance(source_arm.get("started_utc"), str)
                ):
                    raise BindingError("sidecar source did not arm alive")
        else:
            try:
                snapshot = json.loads(payload.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise BindingError(f"sidecar {name} snapshot is not JSON") from exc
            capture_name = name.replace("_", "-") + "-raw"
            raw_value = snapshot.get("raw_capture_receipt")
            if raw_value is None:
                if (
                    set(snapshot) != {"available", "command", "error_type"}
                    or snapshot.get("available") is not False
                    or not isinstance(snapshot.get("command"), list)
                    or not isinstance(snapshot.get("error_type"), str)
                ):
                    raise BindingError(
                        f"sidecar {name} unavailable snapshot differs"
                    )
            else:
                handle, stdout, stderr, raw_receipt = _load_bound_raw_capture(
                    destination,
                    raw_value,
                    capture_name,
                    maximum=sidecar.MAX_SNAPSHOT_BYTES,
                )
                expected_snapshot_keys = {
                    "available",
                    "command",
                    "returncode",
                    "stdout_text",
                    "stderr_text",
                    "stdout_truncated",
                    "stderr_truncated",
                    "raw_capture_receipt",
                }
                if snapshot.get("available") is False:
                    expected_snapshot_keys.add("error_type")
                expected_available = (
                    handle.returncode == 0
                    and handle.producer_error_type is None
                    and not handle.timed_out
                    and not handle.output_exceeded
                )
                expected_error_type = None
                if not expected_available:
                    expected_error_type = (
                        handle.producer_error_type
                        or (
                            "TimeoutExpired"
                            if handle.timed_out
                            else (
                                "OutputLimit"
                                if handle.output_exceeded
                                else "CommandFailed"
                            )
                        )
                    )
                if (
                    set(snapshot) != expected_snapshot_keys
                    or not isinstance(snapshot.get("command"), list)
                    or snapshot.get("available") is not expected_available
                    or handle.returncode != snapshot.get("returncode")
                    or snapshot.get("error_type") != expected_error_type
                    or handle.output_exceeded
                    is not snapshot.get("stdout_truncated")
                    or snapshot.get("stderr_truncated")
                    is not handle.output_exceeded
                    or snapshot.get("stdout_text")
                    != stdout.decode("utf-8", "backslashreplace")
                    or snapshot.get("stderr_text")
                    != stderr.decode("utf-8", "backslashreplace")
                ):
                    raise BindingError(f"sidecar {name} snapshot semantics differ")
                supporting_receipts[name] = {
                    "outer": actual,
                    "raw_capture_receipt": raw_receipt,
                }

    sources = reopened.get("sources")
    if not isinstance(sources, dict) or set(sources) != set(sidecar.SOURCE_COMMANDS):
        raise BindingError("sidecar source receipt set differs")
    source_receipts: dict[str, Any] = {}
    for name, command in sidecar.SOURCE_COMMANDS.items():
        expected = sources[name]
        if (
            not isinstance(expected, dict)
            or set(expected)
            != {
                "command",
                "returncode",
                "bytes",
                "sha256",
                "truncated",
                "error_type",
                "started_utc",
                "ended_utc",
                "alive_at_arm",
                "alive_before_stop",
                "stop_requested_utc",
                "raw_capture_receipt",
            }
            or expected.get("command") != list(command)
            or expected.get("truncated") is not False
            or expected.get("error_type") is not None
            or not sidecar.clean_requested_stop_returncode(
                expected.get("returncode")
            )
            or expected.get("alive_at_arm") is not True
            or expected.get("alive_before_stop") is not True
            or any(
                not isinstance(expected.get(field), str)
                for field in (
                    "started_utc",
                    "ended_utc",
                    "stop_requested_utc",
                )
            )
        ):
            raise BindingError(f"sidecar {name} capture is not integrity-clean")
        handle, raw_payload, raw_stderr, raw_receipt = _load_bound_raw_capture(
            destination,
            expected["raw_capture_receipt"],
            f"{name}-stream",
            maximum=sidecar.MAX_LOG_BYTES,
        )
        if (
            handle.name != f"{name}-stream"
            or handle.stdout_path != destination / f"{name}.log"
            or handle.stderr_path != destination / f"{name}.log.stderr"
            or handle.returncode != expected.get("returncode")
            or handle.timed_out is not False
            or handle.output_exceeded is not expected.get("truncated")
            or handle.producer_error_type != expected.get("error_type")
            or raw_stderr != b""
            or len(raw_payload) != expected.get("bytes")
            or hashlib.sha256(raw_payload).hexdigest()
            != expected.get("sha256")
        ):
            raise BindingError(f"sidecar {name} raw capture semantics differ")
        _payload, actual = _read_bound_file(
            destination / f"{name}.log",
            {"size": expected.get("bytes"), "sha256": expected.get("sha256")},
            f"sidecar {name} log",
            sidecar.MAX_LOG_BYTES,
        )
        source_receipts[name] = {
            "log": actual,
            "raw_capture_receipt": raw_receipt,
        }
    return {
        "schema": "s22plus_fyg8_p300_usb_trace_capture_integrity_v1",
        "result": result_receipt,
        "supporting": supporting_receipts,
        "sources": source_receipts,
        "integrity_clean": True,
        "verified": True,
    }


def _utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise BindingError(f"{label} timestamp is invalid")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise BindingError(f"{label} timestamp is invalid") from exc


def verify_same_attempt(
    binding: Mapping[str, Any],
    sidecar_result: Mapping[str, Any],
    journal_records: Sequence[Mapping[str, Any]],
    observation_witness: Mapping[str, Any],
) -> dict[str, Any]:
    bound = verify_binding(binding)
    witness = verify_observation_witness(bound, observation_witness)
    if (
        sidecar_result.get("schema") != sidecar.SCHEMA
        or sidecar_result.get("phase") != "complete"
        or sidecar_result.get("non_authoritative") is not True
        or sidecar_result.get("device_actions") is not False
        or sidecar_result.get("opens_candidate_acm") is not False
        or sidecar_result.get("stop_reason") != "signal:SIGTERM"
        or sidecar_result.get("owner_token_sha256")
        != owner_token_sha256(bound)
    ):
        raise BindingError("sidecar result safety or completion differs")
    events: dict[str, Mapping[str, Any]] = {}
    previous_sequence = -1
    for record in journal_records:
        sequence = record.get("sequence")
        if (
            isinstance(sequence, bool)
            or not isinstance(sequence, int)
            or sequence != previous_sequence + 1
            or record.get("binding_sha256")
            != bound["approval_binding_sha256"]
        ):
            raise BindingError("journal sequence or approval binding differs")
        previous_sequence = sequence
        if record.get("kind") == "event":
            name = record.get("action")
            if not isinstance(name, str) or name in events:
                raise BindingError("journal event set is ambiguous")
            events[name] = record
    required = tuple(EVENT_WINDOW.values())
    if any(name not in events for name in required):
        raise BindingError("sidecar window journal events are incomplete")
    start = _utc(sidecar_result.get("started_utc"), "sidecar start")
    end = _utc(sidecar_result.get("ended_utc"), "sidecar end")
    times = {
        name: _utc(events[name].get("timestamp_utc"), f"journal {name}")
        for name in required
    }
    observation_time = _utc(
        witness.get("timestamp_utc"), "observation durable witness"
    )
    sources = sidecar_result.get("sources")
    if not isinstance(sources, dict) or set(sources) != set(sidecar.SOURCE_COMMANDS):
        raise BindingError("sidecar source result set differs")
    source_stop_times = []
    source_end_times = []
    for name in sidecar.SOURCE_COMMANDS:
        source = sources[name]
        if (
            not isinstance(source, dict)
            or not sidecar.clean_requested_stop_returncode(
                source.get("returncode")
            )
            or source.get("alive_at_arm") is not True
            or source.get("alive_before_stop") is not True
        ):
            raise BindingError(f"sidecar {name} did not span the live window")
        source_stop = _utc(
            source.get("stop_requested_utc"), f"sidecar {name} stop"
        )
        source_end = _utc(source.get("ended_utc"), f"sidecar {name} end")
        if source_stop > source_end:
            raise BindingError(f"sidecar {name} ended before stop request")
        source_stop_times.append(source_stop)
        source_end_times.append(source_end)
    if not (
        times["live_session_start"] <= start
        <= times["candidate_flash_start"]
        <= times["candidate_flash_done"]
        <= observation_time
        <= min(source_stop_times)
        <= max(source_end_times)
        <= end
        <= times["candidate_boot_ready"]
    ):
        raise BindingError("sidecar capture does not cover the candidate window")
    flash_attempt = events["candidate_flash_start"].get("details", {}).get(
        "attempt"
    )
    if flash_attempt != bound["candidate_transfer_attempt"]:
        raise BindingError("candidate transfer attempt differs")
    return {
        "schema": "s22plus_fyg8_p300_usb_trace_same_attempt_result_v1",
        "verdict": VERDICT,
        "binding_sha256": bound["binding_sha256"],
        "campaign_id": bound["campaign_id"],
        "attempt_id": bound["attempt_id"],
        "candidate_ap": bound["candidate_ap"],
        "window": WINDOW,
        "same_attempt_verified": True,
        "non_authoritative": True,
        "device_actions": False,
        "verified": True,
    }
