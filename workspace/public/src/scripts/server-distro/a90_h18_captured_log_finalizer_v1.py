#!/usr/bin/env python3
"""Close the exact H18 run01 native fallback from captured read-only receipts.

The H18 arm, reboot, and handoff were already consumed.  This host-only adapter
never opens a device, USB endpoint, or network socket.  It binds the immutable
five-record predecessor journal and the already captured six-command bridge
transcript, compares only the structurally decoded log payloads, and appends at
most the original final-health and closed journal records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_h18_ufs_d1_runner_v1 as d1  # noqa: E402
import a90_h18_ufs_f1_runner_v1 as f1  # noqa: E402
import a90_observation_pipeline as observation  # noqa: E402
import a90_v3403_f1_orchestrator as base  # noqa: E402


CAPABILITY = "A90_H18_CAPTURED_LOG_PAYLOAD_NATIVE_FALLBACK_FINALIZER_V1"
INCIDENT = "H18_FRAMED_LOG_PREFIX_ENVELOPE_MISMATCH"
QUALIFICATION_SCHEMA = "a90-h18-captured-log-finalizer-qualification-v1"
REVIEW_SCHEMA = "a90-h18-captured-log-finalizer-independent-review-v1"
REVIEW_SCOPE = (
    "exact-h18-run01-captured-log-payload-native-fallback-host-only-no-replay-close"
)
REVIEWER = "/root/a90_h18_execution_review"
REVIEW_REQUIRED_INVARIANTS = (
    "exact immutable five-record H18 consumed prefix and predecessor closure",
    "exact private capture and bridge stderr byte bindings",
    "exact six outbound commands and six successful A90P1 response frames",
    "payload-only log prefix with command envelopes excluded structurally",
    "unique ordered firstboot-overlay EPERM and clean restoration evidence",
    "exact H18 health latched status same intent and unmounted userdata",
    "zero finalizer device dev USB network effect and replay contacts",
    "exclusive five-to-six-to-seven host-only journal publication and resume",
    "no Debian PID1 switch-root persistent-server display or Wi-Fi overclaim",
)

RUN_ID = "a90-h18-ufs-f1-20260812-01"
MANIFEST_SHA256 = (
    "fde5e308a5fcd7ada9c6912bb138c585b9e1e9ad1d6d4e3ae2636c5270ba02ef"
)
INSTALL_RESULT_SHA256 = (
    "e97aebb1b810edb09dd733b354434b6728f8faa6e6d83258230a547d10430804"
)
PREDECESSOR_EXECUTION_SHA256 = (
    "dcb507f5191f48831ca185fb114afc41db29aae4b3bb9af4c064cfbc9256ced8"
)
INTENT_SHA256 = (
    "1be00f1d05f2b8d8a72192577f79cbb25caa7eef8dce7c81ea2a537f50b9dd81"
)
PREFIX_SHA256 = (
    "138789fb408847475812ca3c6aab13fc3964815fdbb7e15d192bf61aaab1e9f9",
    "1be00f1d05f2b8d8a72192577f79cbb25caa7eef8dce7c81ea2a537f50b9dd81",
    "cfbf0cff2c5385d249ba855ec159746afed9018d9f78ded77c69dbec4344f8d4",
    "b399d88011fa6efd208ec2edfbf71e2640b272b259fd9ac4b7cce02c42b443fb",
    "9721047c162e09596310ccfbaaa9180c9adf9f87b25e1f0de59e13fd0d9b24c8",
)
CAPTURE_SIZE = 148626
CAPTURE_SHA256 = (
    "33c6f423b25d83ff3e4f7573d2305eb294879ee52b8f1763c98d426e12484572"
)
BRIDGE_STDERR_SIZE = 880
BRIDGE_STDERR_SHA256 = (
    "df1ee6c8399ba9bb73b90b50c743fad9c6fe585e6f0dd9257e40cbc35312d503"
)
TCP_STREAM_SHA256 = (
    "90a5f009e91edd0b39ad805809cb105fff3600f5a7a33ec42ce83dd7ab187da4"
)
TCP_STREAM_SIZE = 2668
SERIAL_STREAM_SHA256 = (
    "e4fde1427023aa0ac00ad96ca2015830cd6ed72a7642a6e273392717cba79e80"
)
SERIAL_STREAM_SIZE = 32810

PRIVATE_RUN_BASE = (REPO_ROOT / "workspace/private/runs/server-distro").resolve()
EXPECTED_MANIFEST_PATH = (PRIVATE_RUN_BASE / RUN_ID / "manifest.json").resolve()
EXPECTED_INSTALL_RESULT_PATH = (
    PRIVATE_RUN_BASE / RUN_ID / "h18-f1-live" / "result.json"
).resolve()
EXPECTED_TRANSACTION_DIR = (
    PRIVATE_RUN_BASE / RUN_ID / "h18-d1" / "run01"
).resolve()
EXPECTED_CAPTURE_PATH = (
    PRIVATE_RUN_BASE / RUN_ID / "h18-d1" / "run01-finalizer-bridge-repair.raw.log"
).resolve()
EXPECTED_BRIDGE_STDERR_PATH = (
    PRIVATE_RUN_BASE
    / RUN_ID
    / "h18-d1"
    / "run01-finalizer-bridge-repair.stderr.log"
).resolve()

ADAPTER_REL = (
    "workspace/public/src/scripts/server-distro/"
    "a90_h18_captured_log_finalizer_v1.py"
)
INCIDENT_REPORT_REL = (
    "docs/reports/A90_H18_FRAMED_LOG_PREFIX_FINALIZER_INCIDENT_2026-08-12.md"
)
REVIEW_REPORT_REL = (
    "docs/reports/"
    "A90_H18_FRAMED_LOG_PREFIX_FINALIZER_INDEPENDENT_REVIEW_2026-08-12.json"
)
QUALIFICATION_REL = (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h18/captured-log-finalizer-qualification.json"
)
EXECUTION_RELS = tuple(
    sorted(set(f1.EXECUTION_SOURCE_RELS) | {ADAPTER_REL, INCIDENT_REPORT_REL})
)
JOURNAL_NAMES = d1.JOURNAL_NAMES
JOURNAL_SCHEMA = d1.SCHEMA
RESULT_SCHEMA = d1.RESULT_SCHEMA
CAPTURE_MARKER_RE = re.compile(
    rb"\n--- (tcp->serial|serial->tcp) ---\n"
)
DIAGNOSTIC_RE = re.compile(
    r"^\[[0-9]+ms\] server-distro: D4 handoff stop "
    r"stage=(?P<stage>[a-z0-9-]+) rc=(?P<rc>-[0-9]+) "
    r"errno=(?P<errno>[1-9][0-9]*) root_mounted=(?P<root>[01]) "
    r"writable_mounted=(?P<writable>[0-9]+) "
    r"evidence_bound=(?P<evidence>[01]) "
    r"wifi_handoff_bound=(?P<wifi>[01])$",
    re.MULTILINE,
)
CLEANUP_RE = re.compile(
    r"^\[[0-9]+ms\] server-distro: D4 handoff failure "
    r"cleanup_clean=(?P<clean>[01]) root_mounted=(?P<mounted>[01]) "
    r"recovery_required=(?P<recovery>[01]) "
    r"userdata_unchanged=1 userdata_write=0$",
    re.MULTILINE,
)
UNMOUNTED_RE = re.compile(
    r"^A90H18_POST_PHYSICAL_RETURN devt=(?P<major>[0-9]+):"
    r"(?P<minor>[0-9]+) ufs_mount_count=(?P<count>[0-9]+) "
    r"userdata_write=0$"
)
SAME_INTENT_RE = re.compile(
    r"^A90H18_INTENT_BINDING intent=(?P<intent>[0-9a-f]{64}) "
    r"enable_sha256=(?P<enable>[0-9a-f]{64}) "
    r"latch_sha256=(?P<latch>[0-9a-f]{64}) "
    r"evidence_sha256=(?P<evidence>[0-9a-f]{64})$"
)
LOCAL_CLIENT_RE = re.compile(
    r"^\[bridge\] client (?P<state>connected|disconnected): "
    r"127\.0\.0\.1:(?P<port>[1-9][0-9]*)$"
)


class ContractError(RuntimeError):
    """Raised before any terminal publication or unsafe overclaim."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def execution_closure() -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    digest = hashlib.sha256()
    for relative in EXECUTION_RELS:
        path = (REPO_ROOT / relative).resolve(strict=True)
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise ContractError(f"H18 finalizer source is not regular: {relative}")
        sha = f1.sha256_file(path)
        files[relative] = {"size": info.st_size, "sha256": sha}
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(info.st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(sha.encode("ascii"))
        digest.update(b"\0")
    return {"sha256": digest.hexdigest(), "files": files}


def _require_private_regular(
    path: Path,
    expected_path: Path,
    expected_size: int,
    expected_sha256: str,
    label: str,
) -> bytes:
    lexical = path.absolute()
    if lexical != expected_path or lexical.is_symlink():
        raise ContractError(f"{label} path changed")
    resolved = lexical.resolve(strict=True)
    if resolved != expected_path:
        raise ContractError(f"{label} resolved path changed")
    info = resolved.stat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_size != expected_size
    ):
        raise ContractError(f"{label} is not one exact private regular file")
    value = resolved.read_bytes()
    if len(value) != expected_size or _sha256_bytes(value) != expected_sha256:
        raise ContractError(f"{label} bytes changed")
    return value


def _validate_review_report(value: Any, closure: dict[str, Any]) -> dict[str, Any]:
    expected_contacts = {
        "device": 0,
        "dev": 0,
        "usb": 0,
        "network": 0,
        "workspace_private": 0,
        "s22plus_paths": 0,
        "file_modifications": 0,
    }
    if (
        not isinstance(value, dict)
        or value.get("schema") != REVIEW_SCHEMA
        or value.get("capability") != CAPABILITY
        or value.get("verdict") != "PASS_GO"
        or value.get("review_date") != "2026-08-12"
        or value.get("reviewer") != REVIEWER
        or value.get("execution_closure_sha256") != closure["sha256"]
        or value.get("execution_file_count") != len(closure["files"])
        or value.get("review_scope") != REVIEW_SCOPE
        or value.get("incident") != INCIDENT
        or value.get("new_hazard_or_incident") is not True
        or value.get("findings") != {"high": [], "medium": [], "low": []}
        or value.get("validated_invariants") != list(REVIEW_REQUIRED_INVARIANTS)
        or value.get("review_contacts") != expected_contacts
        or value.get("live_authority") is not False
    ):
        raise ContractError("H18 captured-log independent review is not current")
    return value


def _load_qualification(closure: dict[str, Any]) -> dict[str, Any]:
    path = REPO_ROOT / QUALIFICATION_REL
    report = REPO_ROOT / REVIEW_REPORT_REL
    for item, label in ((path, "qualification"), (report, "review")):
        if item.is_symlink() or not stat.S_ISREG(item.stat().st_mode):
            raise ContractError(f"H18 captured-log {label} is not regular")
    report_value = json.loads(report.read_text(encoding="utf-8"))
    _validate_review_report(report_value, closure)
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(value, dict)
        or value.get("schema") != QUALIFICATION_SCHEMA
        or value.get("capability") != CAPABILITY
        or value.get("verdict") != "PASS_GO"
        or value.get("execution_closure_sha256") != closure["sha256"]
        or value.get("execution_hashes") != closure["files"]
        or value.get("incident_run_id") != RUN_ID
        or value.get("predecessor_execution_closure_sha256")
        != PREDECESSOR_EXECUTION_SHA256
        or value.get("capture_sha256") != CAPTURE_SHA256
        or value.get("bridge_stderr_sha256") != BRIDGE_STDERR_SHA256
        or value.get("review_scope") != REVIEW_SCOPE
        or value.get("incident") != INCIDENT
        or value.get("new_hazard_or_incident") is not True
        or value.get("host_only") is not True
        or value.get("read_only_approval_required") is not False
        or value.get("review_report") != REVIEW_REPORT_REL
        or value.get("review_report_sha256") != f1.sha256_file(report)
        or value.get("live_authority") is not False
    ):
        raise ContractError("H18 captured-log qualification is not current")
    return value


def _expected_commands() -> tuple[list[str], ...]:
    return (
        ["auto-handoff-status"],
        ["run", "/bin/busybox", "sh", "-c", d1._same_intent_script()],
        ["version"],
        ["selftest"],
        ["run", "/bin/busybox", "sh", "-c", d1._unmounted_script()],
        ["logcat"],
    )


def _split_capture(raw: bytes) -> tuple[bytes, bytes]:
    matches = list(CAPTURE_MARKER_RE.finditer(raw))
    if not matches or matches[0].start() != 0:
        raise ContractError("H18 bridge capture has an invalid first marker")
    streams: dict[bytes, list[bytes]] = {
        b"tcp->serial": [],
        b"serial->tcp": [],
    }
    for index, marker in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        streams[marker.group(1)].append(raw[marker.end() : end])
    tcp = b"".join(streams[b"tcp->serial"])
    serial = b"".join(streams[b"serial->tcp"])
    if (
        len(tcp) != TCP_STREAM_SIZE
        or _sha256_bytes(tcp) != TCP_STREAM_SHA256
        or len(serial) != SERIAL_STREAM_SIZE
        or _sha256_bytes(serial) != SERIAL_STREAM_SHA256
    ):
        raise ContractError("H18 bridge directional streams changed")
    return tcp, serial


def _receipt_from_frame(
    serial: bytes,
    frame: observation.A90P1Frame,
    command: list[str],
) -> dict[str, Any]:
    begin = frame.begin
    end = frame.end
    expected_flags = "0x2" if command[0] == "run" else "0x0"
    if (
        begin
        != {
            "seq": begin.get("seq"),
            "cmd": command[0],
            "argc": str(len(command)),
            "flags": expected_flags,
        }
        or end
        != {
            "seq": begin.get("seq"),
            "cmd": command[0],
            "rc": "0",
            "errno": "0",
            "duration_ms": end.get("duration_ms"),
            "flags": expected_flags,
            "status": "ok",
        }
        or not str(end.get("duration_ms") or "").isdigit()
        or not frame.body
        or frame.body[-1].text
        != f"[done] {command[0]} ({end['duration_ms']}ms)"
    ):
        raise ContractError("H18 captured response frame changed")
    text = serial[frame.byte_start : frame.byte_end].decode("utf-8")
    record = {
        "command": command,
        "rc": 0,
        "status": "ok",
        "trust": "A90P1_V1_STRUCTURAL_ONLY",
        "begin": begin,
        "end": end,
        "text": text,
    }
    base.require_exact_f1_command_receipt(record, command, "captured H18 receipt")
    return record


def _capture_receipts(raw: bytes) -> tuple[dict[str, Any], ...]:
    tcp, serial = _split_capture(raw)
    commands = _expected_commands()
    expected_lines = [base.a90ctl.encode_cmdv1_line(command) for command in commands]
    try:
        outbound = tcp.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError("H18 outbound capture is not UTF-8") from exc
    if not outbound.endswith("\n") or outbound.splitlines() != expected_lines:
        raise ContractError("H18 captured outbound commands changed")
    try:
        transcript = observation.parse_a90p1_transcript(serial)
    except observation.ObservationContractError as exc:
        raise ContractError("H18 captured A90P1 transcript changed") from exc
    if len(transcript.frames) != 6 or transcript.transitions:
        raise ContractError("H18 captured frame sequence changed")
    expected_outside = [expected_lines[0]] + [
        f"a90:/# {line}" for line in expected_lines[1:]
    ] + ["a90:/# "]
    if (
        [line.text for line in transcript.outside] != expected_outside
        or [line.ending.value for line in transcript.outside]
        != ["CRLF"] * 6 + ["EOF"]
    ):
        raise ContractError("H18 captured echo or prompt sequence changed")
    receipts: list[dict[str, Any]] = []
    for index, (frame, command) in enumerate(zip(transcript.frames, commands), 1):
        if frame.begin.get("seq") != str(index):
            raise ContractError("H18 captured response sequence changed")
        receipts.append(_receipt_from_frame(serial, frame, command))
    return tuple(receipts)


def _validate_bridge_stderr(raw: bytes) -> dict[str, Any]:
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ContractError("H18 bridge stderr is not UTF-8") from exc
    prefix = [
        "[bridge] tcp listener ready on 127.0.0.1:54321",
        "[bridge] press Ctrl-C to stop",
        f"[bridge] serial connected: {f1.EXACT_BRIDGE_DEVICE}",
    ]
    if lines[:3] != prefix or len(lines[3:]) != 16:
        raise ContractError("H18 bridge stderr preface changed")
    sessions: list[int] = []
    for pair in range(8):
        connected = LOCAL_CLIENT_RE.fullmatch(lines[3 + pair * 2])
        disconnected = LOCAL_CLIENT_RE.fullmatch(lines[4 + pair * 2])
        if (
            connected is None
            or disconnected is None
            or connected.group("state") != "connected"
            or disconnected.group("state") != "disconnected"
            or connected.group("port") != disconnected.group("port")
        ):
            raise ContractError("H18 bridge localhost session sequence changed")
        sessions.append(int(connected.group("port"), 10))
    if len(sessions) != len(set(sessions)):
        raise ContractError("H18 bridge localhost session port was reused")
    return {
        "proof": True,
        "listener": "127.0.0.1:54321",
        "serial_device": f1.EXACT_BRIDGE_DEVICE,
        "localhost_session_count": 8,
        "external_network_contact_count": 0,
    }


def _log_payload_lines(
    record: dict[str, Any],
    label: str,
) -> tuple[tuple[str, str], ...]:
    exact = base.require_exact_f1_command_receipt(record, ["logcat"], label)
    try:
        transcript = observation.parse_a90p1_transcript(exact["text"])
    except observation.ObservationContractError as exc:
        raise ContractError(f"{label} framing changed") from exc
    if len(transcript.frames) != 1 or transcript.transitions:
        raise ContractError(f"{label} does not contain one exact frame")
    frame = transcript.frames[0]
    if frame.begin != exact["begin"] or frame.end != exact["end"] or not frame.body:
        raise ContractError(f"{label} receipt and frame disagree")
    done = f"[done] logcat ({frame.end['duration_ms']}ms)"
    if frame.body[-1].text != done:
        raise ContractError(f"{label} completion line changed")
    payload = list(frame.body[:-1])
    if payload and payload[-1].text == "" and payload[-1].ending.value == "CRLF":
        payload.pop()
    return tuple((line.text, line.ending.value) for line in payload)


def _log_payload(record: dict[str, Any], label: str) -> str:
    lines = _log_payload_lines(record, label)
    return "".join(text + "\n" for text, _ in lines)


def _attribution(
    opening_log: dict[str, Any],
    final_log: dict[str, Any],
) -> dict[str, Any]:
    before_lines = _log_payload_lines(opening_log, "H18 captured opening log")
    after_lines = _log_payload_lines(final_log, "H18 captured final log")
    if (
        not before_lines
        or len(after_lines) <= len(before_lines)
        or after_lines[: len(before_lines)] != before_lines
    ):
        raise ContractError("H18 log payload history is not an exact prefix")
    appended_lines = after_lines[len(before_lines) :]
    before = "".join(text + "\n" for text, _ in before_lines)
    after = "".join(text + "\n" for text, _ in after_lines)
    appended = "".join(text + "\n" for text, _ in appended_lines)
    diagnostic_candidates = [
        (index, text)
        for index, (text, _) in enumerate(appended_lines)
        if "server-distro: D4 handoff stop " in text
    ]
    cleanup_candidates = [
        (index, text)
        for index, (text, _) in enumerate(appended_lines)
        if "server-distro: D4 handoff failure " in text
    ]
    if len(diagnostic_candidates) != 1 or len(cleanup_candidates) != 1:
        raise ContractError("H18 appended diagnostic or cleanup is not unique")
    diagnostic_index, diagnostic_text = diagnostic_candidates[0]
    cleanup_index, cleanup_text = cleanup_candidates[0]
    diagnostic = DIAGNOSTIC_RE.fullmatch(diagnostic_text)
    cleanup = CLEANUP_RE.fullmatch(cleanup_text)
    if diagnostic is None or cleanup is None:
        raise ContractError("H18 appended diagnostic or cleanup shape changed")
    facts = diagnostic.groupdict()
    if (
        diagnostic_index >= cleanup_index
        or facts
        != {
            "stage": "firstboot-overlay",
            "rc": "-1",
            "errno": "1",
            "root": "1",
            "writable": "4",
            "evidence": "0",
            "wifi": "0",
        }
        or cleanup.groupdict()
        != {"clean": "1", "mounted": "0", "recovery": "0"}
    ):
        raise ContractError("H18 exact firstboot-overlay failure facts changed")
    return {
        "proof": True,
        "status": "PROVED_H18_FAILURE_ATTRIBUTION",
        "stage": "firstboot-overlay",
        "rc": -1,
        "errno": 1,
        "root_mounted_at_failure": True,
        "writable_mounted": 4,
        "evidence_bound": False,
        "wifi_handoff_bound": False,
        "incident_window_match": True,
        "cleanup_proof": True,
        "cleanup_clean": True,
        "root_unmounted": True,
        "recovery_required": False,
        "record_persistence": "observed-a90-log-only",
        "power_loss_durable_journal": False,
        "payload_prefix": {
            "proof": True,
            "opening_payload_size": len(before.encode("utf-8")),
            "opening_payload_sha256": hashlib.sha256(before.encode("utf-8")).hexdigest(),
            "final_payload_size": len(after.encode("utf-8")),
            "final_payload_sha256": hashlib.sha256(after.encode("utf-8")).hexdigest(),
            "appended_payload_size": len(appended.encode("utf-8")),
            "appended_payload_sha256": hashlib.sha256(appended.encode("utf-8")).hexdigest(),
            "command_envelope_compared": False,
        },
        "final_log_record": final_log,
    }


def _same_intent(record: dict[str, Any]) -> dict[str, Any]:
    command = _expected_commands()[1]
    exact = base.require_exact_f1_command_receipt(
        record, command, "captured H18 same-intent binding"
    )
    lines = [
        line.strip()
        for line in str(exact["text"]).replace("\r", "").splitlines()
        if line.strip().startswith("A90H18_INTENT_BINDING ")
    ]
    match = SAME_INTENT_RE.fullmatch(lines[0]) if len(lines) == 1 else None
    expected = {
        "intent": INTENT_SHA256,
        "enable": hashlib.sha256(
            d1._expected_h18_state(INTENT_SHA256, "armed-after-native-health")
        ).hexdigest(),
        "latch": hashlib.sha256(
            d1._expected_h18_state(
                INTENT_SHA256, "automatic-handoff-dispatched-no-replay"
            )
        ).hexdigest(),
        "evidence": hashlib.sha256((INTENT_SHA256 + "\n").encode("ascii")).hexdigest(),
    }
    if match is None or match.groupdict() != expected:
        raise ContractError("H18 captured same-intent binding changed")
    return {
        "proof": True,
        "intent_sha256": INTENT_SHA256,
        "enable_sha256": expected["enable"],
        "latch_sha256": expected["latch"],
        "evidence_sha256": expected["evidence"],
        "userdata_write_count": 0,
        "record": record,
    }


def _unmounted(record: dict[str, Any]) -> dict[str, Any]:
    command = _expected_commands()[4]
    exact = base.require_exact_f1_command_receipt(
        record, command, "captured H18 unmounted userdata"
    )
    lines = [
        line.strip()
        for line in str(exact["text"]).replace("\r", "").splitlines()
        if line.strip().startswith("A90H18_POST_PHYSICAL_RETURN ")
    ]
    match = UNMOUNTED_RE.fullmatch(lines[0]) if len(lines) == 1 else None
    if match is None or int(match.group("count"), 10) != 0:
        raise ContractError("H18 captured userdata identity is not unmounted")
    return {
        "proof": True,
        "device": f"{int(match.group('major'))}:{int(match.group('minor'))}",
        "devt_policy": "runtime-resolved-same-session",
        "mount_count": 0,
        "userdata_write_count": 0,
        "command_sha256": hashlib.sha256(d1._unmounted_script().encode()).hexdigest(),
        "record": record,
    }


def _capture_evidence(
    raw_capture: bytes,
    raw_stderr: bytes,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    receipts = _capture_receipts(raw_capture)
    bridge = _validate_bridge_stderr(raw_stderr)
    status = d1.parse_status(receipts[0])
    if status != {
        "binding": 1,
        "enable": 1,
        "latch": 1,
        "build": f1.CANDIDATE_BUILD,
    }:
        raise ContractError("H18 captured auto-handoff state is not exact 1,1")
    native = {
        "exact_bridge": True,
        "selected_realpath": manifest["target"]["bridge_realpath"],
        "version": receipts[2],
        "selftest": receipts[3],
    }
    f1.validate_candidate_native_health(native, manifest)
    return {
        "receipts": receipts,
        "bridge": bridge,
        "auto_handoff_status": status,
        "auto_handoff_status_record": receipts[0],
        "same_intent_binding": _same_intent(receipts[1]),
        "native_health": native,
        "native_fallback_userdata": _unmounted(receipts[4]),
        "final_log_record": receipts[5],
    }


def _capture_binding(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "proof": True,
        "capture_path": str(EXPECTED_CAPTURE_PATH),
        "capture_size": CAPTURE_SIZE,
        "capture_sha256": CAPTURE_SHA256,
        "bridge_stderr_path": str(EXPECTED_BRIDGE_STDERR_PATH),
        "bridge_stderr_size": BRIDGE_STDERR_SIZE,
        "bridge_stderr_sha256": BRIDGE_STDERR_SHA256,
        "tcp_stream_size": TCP_STREAM_SIZE,
        "tcp_stream_sha256": TCP_STREAM_SHA256,
        "serial_stream_size": SERIAL_STREAM_SIZE,
        "serial_stream_sha256": SERIAL_STREAM_SHA256,
        "outbound_command_count": 6,
        "successful_response_frame_count": 6,
        "localhost_session_count": evidence["bridge"]["localhost_session_count"],
        "external_network_contact_count": 0,
        "capture_read_only": True,
    }


def _load_predecessor(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    if (
        args.manifest.resolve(strict=True) != EXPECTED_MANIFEST_PATH
        or args.install_result.resolve(strict=True) != EXPECTED_INSTALL_RESULT_PATH
        or args.transaction_dir.resolve(strict=True) != EXPECTED_TRANSACTION_DIR
        or args.expect_manifest_sha256 != MANIFEST_SHA256
        or args.expect_install_result_sha256 != INSTALL_RESULT_SHA256
        or args.expect_predecessor_execution_closure_sha256
        != PREDECESSOR_EXECUTION_SHA256
    ):
        raise ContractError("H18 finalizer predecessor binding changed")
    predecessor_args = argparse.Namespace(
        manifest=args.manifest,
        expect_manifest_sha256=args.expect_manifest_sha256,
        install_result=args.install_result,
        expect_install_result_sha256=args.expect_install_result_sha256,
        expect_execution_closure_sha256=args.expect_predecessor_execution_closure_sha256,
    )
    manifest, _, _ = d1.load_inputs(predecessor_args)
    transaction_dir = d1._require_transaction_dir(
        manifest, args.transaction_dir, must_be_absent=False
    )
    records = d1._read_records(transaction_dir)
    if len(records) not in (5, 6, 7):
        raise ContractError("H18 finalizer requires the exact five-to-seven prefix")
    if tuple(f1.sha256_file(transaction_dir / name) for name in JOURNAL_NAMES[:5]) != PREFIX_SHA256:
        raise ContractError("H18 consumed five-record prefix changed")
    intent = d1._validate_records(records[:5], transaction_dir, predecessor_args, manifest)
    if intent != INTENT_SHA256:
        raise ContractError("H18 consumed intent changed")
    return manifest, records, intent


def _build_result(
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    closure: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    attribution = _attribution(
        records[0]["opening_log"], evidence["final_log_record"]
    )
    return {
        "schema": RESULT_SCHEMA,
        "status": "REFUTED_H18_POST_ROOT_FAILURE_ATTRIBUTED_NATIVE_FALLBACK_HEALTHY",
        "incident": INCIDENT,
        "intent_sha256": INTENT_SHA256,
        "prior_current_result_sha256": records[4]["result_sha256"],
        "predecessor_execution_closure_sha256": PREDECESSOR_EXECUTION_SHA256,
        "finalizer_execution_closure_sha256": closure["sha256"],
        "device_safety_state": "RESIDENT_HEALTHY",
        "resident_healthy": True,
        "ordinal_closed": True,
        "inter_effect_health_barrier_satisfied": True,
        "new_device_effect_authority": False,
        "experiment_proof": "REFUTED",
        "native_fallback": True,
        "automatic_native_fallback": True,
        "automatic_native_return": False,
        "operator_physical_return": False,
        "persistent_debian_reached": False,
        "switch_root_exec_proven": False,
        "persistent_server_proven": False,
        "authenticated_ssh_proven": False,
        "debian_pid1_proven": False,
        "persistent_hud_proven": False,
        "display_visible_proven": False,
        "final_wifi_proven": False,
        "server_proven": False,
        "candidate_replay": False,
        "arm_dispatch_count": 1,
        "reboot_dispatch_count": 1,
        "handoff_dispatch_count": 1,
        "physical_return_reboot_dispatch_count": 0,
        "payload_transfer_count": 0,
        "partition_write_count": 0,
        "flash_count": 0,
        "sd_rootfs_stage_count": 0,
        "userdata_write_count": 0,
        "finalizer_device_contact_count": 0,
        "finalizer_dev_contact_count": 0,
        "finalizer_usb_contact_count": 0,
        "finalizer_network_contact_count": 0,
        "finalizer_device_effect_count": 0,
        "effect_replay_count": 0,
        "auto_handoff_status": evidence["auto_handoff_status"],
        "auto_handoff_status_record": evidence["auto_handoff_status_record"],
        "same_intent_binding": evidence["same_intent_binding"],
        "native_health": evidence["native_health"],
        "native_fallback_userdata": evidence["native_fallback_userdata"],
        "diagnostic_attribution": attribution,
        "capture_binding": _capture_binding(evidence),
        "original_observation": records[3]["observation"],
    }


def _validate_result(
    value: Any,
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    closure: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    expected = _build_result(manifest, records, closure, evidence)
    if value != expected:
        raise ContractError("H18 captured-log terminal result changed")
    if (
        not d1._valid_auto_handoff_11(value)
        or not d1._valid_same_intent(value["same_intent_binding"], INTENT_SHA256)
        or not d1._valid_native_health(value["native_health"], manifest)
        or not d1._valid_unmounted_userdata(value["native_fallback_userdata"])
        or _attribution(records[0]["opening_log"], value["diagnostic_attribution"]["final_log_record"])
        != value["diagnostic_attribution"]
    ):
        raise ContractError("H18 captured-log terminal evidence changed")
    return value


def _validate_successor_tail(
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    closure: dict[str, Any],
    evidence: dict[str, Any],
) -> None:
    if len(records) >= 6:
        result = _validate_result(records[5].get("result"), manifest, records, closure, evidence)
        if records[5].get("result_sha256") != f1.json_sha256(result):
            raise ContractError("H18 captured-log final-health hash changed")
    if len(records) == 7 and (
        records[6].get("result") != records[5].get("result")
        or records[6].get("result_sha256") != records[5].get("result_sha256")
    ):
        raise ContractError("H18 captured-log closed result changed")


def _load_static_inputs(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    manifest, records, _ = _load_predecessor(args)
    raw_capture = _require_private_regular(
        args.capture,
        EXPECTED_CAPTURE_PATH,
        CAPTURE_SIZE,
        CAPTURE_SHA256,
        "H18 bridge capture",
    )
    raw_stderr = _require_private_regular(
        args.bridge_stderr,
        EXPECTED_BRIDGE_STDERR_PATH,
        BRIDGE_STDERR_SIZE,
        BRIDGE_STDERR_SHA256,
        "H18 bridge stderr",
    )
    evidence = _capture_evidence(raw_capture, raw_stderr, manifest)
    closure = execution_closure()
    if args.expect_finalizer_execution_closure_sha256 != closure["sha256"]:
        raise ContractError("H18 finalizer execution closure changed")
    _load_qualification(closure)
    _validate_successor_tail(manifest, records, closure, evidence)
    return manifest, records, closure, evidence


def _write_record(index: int, action: str, payload: dict[str, Any]) -> None:
    value = {
        "schema": JOURNAL_SCHEMA,
        "sequence": index,
        "action": action,
        **payload,
    }
    f1.write_json_exclusive(EXPECTED_TRANSACTION_DIR / JOURNAL_NAMES[index], value)


def close(args: argparse.Namespace) -> dict[str, Any]:
    manifest, records, closure, evidence = _load_static_inputs(args)
    if len(records) == 7:
        return _validate_result(records[6]["result"], manifest, records, closure, evidence)
    if len(records) == 6:
        result = _validate_result(records[5]["result"], manifest, records, closure, evidence)
        result_sha = records[5]["result_sha256"]
        _write_record(6, "closed", {"result_sha256": result_sha, "result": result})
        final_manifest, final_records, final_closure, final_evidence = _load_static_inputs(args)
        if len(final_records) != 7:
            raise ContractError("H18 closed publication did not become durable")
        return _validate_result(
            final_records[6]["result"],
            final_manifest,
            final_records,
            final_closure,
            final_evidence,
        )

    result = _build_result(manifest, records, closure, evidence)
    _validate_result(result, manifest, records, closure, evidence)
    fresh_manifest, fresh_records, fresh_closure, fresh_evidence = _load_static_inputs(args)
    if (
        fresh_manifest != manifest
        or fresh_records != records
        or fresh_closure != closure
        or fresh_evidence != evidence
        or len(fresh_records) != 5
    ):
        raise ContractError("H18 captured-log inputs changed before publication")
    _validate_result(result, fresh_manifest, fresh_records, fresh_closure, fresh_evidence)
    result_sha = f1.json_sha256(result)
    _write_record(5, "final-health", {"result_sha256": result_sha, "result": result})
    after_manifest, after_records, after_closure, after_evidence = _load_static_inputs(args)
    if len(after_records) != 6:
        raise ContractError("H18 final-health publication did not become durable")
    _validate_result(result, after_manifest, after_records, after_closure, after_evidence)
    _write_record(6, "closed", {"result_sha256": result_sha, "result": result})
    final_manifest, final_records, final_closure, final_evidence = _load_static_inputs(args)
    if len(final_records) != 7:
        raise ContractError("H18 closed publication did not become durable")
    return _validate_result(
        final_records[6]["result"],
        final_manifest,
        final_records,
        final_closure,
        final_evidence,
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--manifest", type=Path, required=True)
    result.add_argument("--expect-manifest-sha256", required=True)
    result.add_argument("--install-result", type=Path, required=True)
    result.add_argument("--expect-install-result-sha256", required=True)
    result.add_argument("--transaction-dir", type=Path, required=True)
    result.add_argument("--expect-predecessor-execution-closure-sha256", required=True)
    result.add_argument("--capture", type=Path, required=True)
    result.add_argument("--bridge-stderr", type=Path, required=True)
    result.add_argument("--expect-finalizer-execution-closure-sha256", required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = close(args)
    except (ContractError, d1.ContractError, f1.ContractError, OSError, ValueError) as exc:
        print(f"H18_CAPTURED_LOG_FINALIZER_ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
