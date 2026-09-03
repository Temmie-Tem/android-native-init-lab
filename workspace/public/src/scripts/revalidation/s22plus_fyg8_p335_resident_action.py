#!/usr/bin/env python3
"""Run one named, attended P3.35 resident-lease action.

The device protocol always executes the immutable three-command tuple.  One
lease action therefore owns exactly one authenticated session; the selected
catalog entry is the primary result and the other two fixed results are
retained as protocol-supporting evidence.  No caller command or path exists.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import select
import stat
import sys
import termios
import time
import tty
from typing import Any, Mapping

import device_action_cdc_acm_observer_v1 as cdc
import device_action_f1_live_v2 as live
import device_action_raw_capture_v1 as raw_capture
import s22plus_fyg8_p335_resident_session as resident
import s22plus_fyg8_p335_retained_listener_acm_observer as observer
import s22plus_fyg8_p335_retained_listener_runtime as runtime


ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve(strict=True)
MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p335_process_v2_ready_1.json"
)
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-f1-live-v2/"
    "p335-ready1-prepared-20260904-2"
)
LEASE_DIR = RUN_DIR / "p335-resident-session"
EVIDENCE_DIR = RUN_DIR / "p335-resident-action-evidence"
ACTIVATION = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p335_resident_action_v1.json"
)
SCHEMA = "s22plus_fyg8_p335_resident_action_result_v1"
ACTIVATION_SCHEMA = "s22plus_fyg8_p335_resident_action_activation_v1"
REVIEW_VERDICT = "PASS_GO_P335_RESIDENT_ACTION_RUNNER_H0_V1"
SESSION_TIMEOUT_SEC = 30
MAX_EVIDENCE_BYTES = 256 * 1024
ACTION_INDEX = {name: index for index, name in enumerate(resident.ACTION_NAMES)}


class ActionError(RuntimeError):
    """The current action cannot safely continue."""


def canonical(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ActionError("value is not canonical JSON") from exc


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _typed_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            _typed_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _typed_equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def _stable(path: Path, label: str, maximum: int) -> bytes:
    direct = path.absolute()
    try:
        if direct != path or direct.resolve(strict=True) != direct:
            raise ActionError(f"{label} path is indirect")
        descriptor = os.open(
            direct, os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0)
        )
    except OSError as exc:
        raise ActionError(f"{label} is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        payload = b""
        while chunk := os.read(descriptor, min(1024 * 1024, maximum + 1)):
            payload += chunk
            if len(payload) > maximum:
                break
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    fields = (
        "st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_uid != os.getuid()
        or any(getattr(before, key) != getattr(after, key) for key in fields)
        or len(payload) != before.st_size
        or len(payload) > maximum
    ):
        raise ActionError(f"{label} identity differs")
    return payload


def _strict_json(path: Path, label: str, maximum: int) -> tuple[dict[str, Any], bytes]:
    payload = _stable(path, label, maximum)

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ActionError(f"{label} contains a duplicate key")
            value[key] = item
        return value

    try:
        value = json.loads(payload.decode("ascii"), object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ActionError(f"{label} is invalid") from exc
    if type(value) is not dict or canonical(value) != payload:
        raise ActionError(f"{label} is not canonical")
    return value, payload


def _source_receipts() -> dict[str, dict[str, Any]]:
    paths = {
        "runner": SCRIPT,
        "live": Path(live.__file__).resolve(),
        "lease_core": Path(resident.__file__).resolve(),
        "observer": Path(observer.__file__).resolve(),
        "runtime": Path(runtime.__file__).resolve(),
        "cdc": Path(cdc.__file__).resolve(),
        "raw_capture": Path(raw_capture.__file__).resolve(),
        "manifest": MANIFEST,
    }
    return {
        name: {"path": str(path.relative_to(ROOT)), **identity(_stable(path, name, 2 * 1024 * 1024))}
        for name, path in paths.items()
    }


def _expected_activation(
    inputs: Mapping[str, Any], review: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema": ACTIVATION_SCHEMA,
        "target": dict(resident.TARGET),
        "manifest_id": "s22plus-fyg8-p335-process-v2-ready-1",
        "run_id": runtime.P335_RUN_ID_HEX,
        "run_directory": str(RUN_DIR.relative_to(ROOT)),
        "lease_directory": str(LEASE_DIR.relative_to(ROOT)),
        "evidence_directory": str(EVIDENCE_DIR.relative_to(ROOT)),
        "catalog": resident.catalog_for(runtime.P335_RUN_ID_HEX),
        "session": {
            "commands": [command.decode("ascii") for command in runtime.DEFAULT_COMMANDS],
            "commands_per_session": runtime.P335_COMMANDS_PER_SESSION,
            "session_per_action": 1,
            "timeout_sec": SESSION_TIMEOUT_SEC,
            "supporting_results_recorded": True,
        },
        "bounds": {
            "action_cap": resident.MAX_ACTIONS,
            "lease_sec": resident.MAX_LEASE_SECONDS,
            "raw_rx_max": runtime.MAX_OUTPUT_BYTES + 64 * 1024,
            "raw_tx_max": 64 * 1024,
            "retry": False,
        },
        "safety": {
            "read_only": True,
            "caller_command": False,
            "caller_path": False,
            "interactive_pty": False,
            "file_transfer": False,
            "persistent_change": False,
            "adb": False,
            "odin": False,
            "reboot": False,
            "partition_payload": False,
        },
        "inputs": dict(inputs),
        "independent_review": dict(review),
    }


def validate_activation(*, require_pass: bool) -> dict[str, Any]:
    value, payload = _strict_json(ACTIVATION, "P3.35 action activation", 256 * 1024)
    review = value.get("independent_review")
    allowed = {"status": "pass-go", "verdict": REVIEW_VERDICT}
    if review not in ({"status": "review-pending", "verdict": None}, allowed):
        raise ActionError("P3.35 action review state differs")
    if require_pass and review != allowed:
        raise ActionError("P3.35 action runner lacks independent PASS_GO")
    if not _typed_equal(value, _expected_activation(_source_receipts(), review)):
        raise ActionError("P3.35 action activation differs")
    return {"value": value, "receipt": identity(payload)}


def _write_once(path: Path, payload: bytes) -> dict[str, Any]:
    if len(payload) > MAX_EVIDENCE_BYTES:
        raise ActionError("action evidence exceeds its bound")
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o400,
    )
    try:
        written = 0
        while written < len(payload):
            written += os.write(descriptor, payload[written:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)
    return {"path": str(path.relative_to(ROOT)), **identity(payload)}


def _mkdir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=False, exist_ok=False)
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def _current_context() -> tuple[
    Any, resident.ResidentLease, dict[str, Any], bytes, set[str]
]:
    prepared = live.load_prepared(ROOT, MANIFEST, RUN_DIR)
    journal = live.core.Journal.reopen(RUN_DIR / "transaction", prepared.binding_sha256)
    state = live._state(prepared)
    if (
        journal.state() != "OBSERVED"
        or state.get("candidate_classification") != "odin_transfer_completed"
        or state.get("candidate_completed") is not True
        or state.get("candidate_observer_accepted") is not True
        or state.get("rollback_classification") is not None
        or state.get("rollback_completed") is not False
        or state.get("resident_session_active") is not True
        or state.get("resident_rollback_required") is not False
    ):
        raise ActionError("P3.35 is not in the active resident state")
    durable = live._reopen_candidate_observation(prepared)
    if durable.get("accepted") is not True or not live._p335_proof_ok(durable):
        raise ActionError("P3.35 initial resident proof cannot be reopened")
    binding = live._p335_resident_binding(prepared, durable)
    lease = resident.ResidentLease.open(LEASE_DIR)
    if resident.canonical_bytes(binding) != resident.canonical_bytes(lease.binding):
        raise ActionError("P3.35 current resident binding differs")
    key, key_sha256 = live._p328_read_auth_key(prepared)
    if key_sha256 != binding["key"]["sha256"]:
        raise ActionError("P3.35 private key identity differs")
    live._p324_typec_lane_value(prepared, revalidate=True)
    proof = durable["p335_authenticated_attended_resident"]
    initial = {
        item["challenge_nonce_sha256"] for item in proof["sessions"]
    }
    if len(initial) != observer.MAX_SESSIONS:
        raise ActionError("P3.35 initial challenge nonces are not distinct")
    return prepared, lease, binding, key, initial


def _previous_action_nonces(
    lease: resident.ResidentLease,
) -> set[str]:
    values: set[str] = set()
    for ordinal, (intent, result) in enumerate(lease.actions, 1):
        if result is None:
            raise ActionError("P3.35 prior action intent is unresolved")
        path = EVIDENCE_DIR / f"action-{ordinal:02d}" / "result.json"
        value, payload = _strict_json(
            path, f"P3.35 action {ordinal} result", MAX_EVIDENCE_BYTES
        )
        if (
            identity(payload)
            != {
                "size": result["receipt_bytes"],
                "sha256": result["receipt_sha256"],
            }
            or value.get("schema") != SCHEMA
            or value.get("action") != intent["action"]
            or value.get("ordinal") != ordinal
            or value.get("classification") != "accepted"
            or value.get("authenticated") is not True
            or value.get("clean_close") is not True
            or value.get("full_protocol_tuple") is not True
            or value.get("fixed_command_count") != runtime.P335_COMMANDS_PER_SESSION
        ):
            raise ActionError("P3.35 prior action receipt differs")
        nonce = value.get("challenge_nonce_sha256")
        if (
            type(nonce) is not str
            or len(nonce) != 64
            or any(char not in "0123456789abcdef" for char in nonce)
            or nonce == "0" * 64
            or nonce in values
        ):
            raise ActionError("P3.35 prior action nonce history differs")
        values.add(nonce)
    return values


def _select_endpoint(prepared: Any, binding: Mapping[str, Any]) -> tuple[Any, dict[str, str]]:
    source = prepared.bundle.manifest["observation"]["candidate_observer"]
    spec = {key: source[key] for key in cdc.SPEC_KEYS}
    exact = []
    for identity_value, endpoint in cdc.scan_endpoints():
        if (
            cdc._matches(spec, endpoint.topology, identity_value, endpoint)
            and hashlib.sha256(endpoint.topology.encode()).hexdigest()
            == binding["topology"]["sha256"]
        ):
            exact.append((endpoint, identity_value))
    if len(exact) != 1:
        raise ActionError("P3.35 exact resident endpoint count differs")
    return exact[0]


def _exchange_before_exec_bound(
    descriptor: int,
    key: bytes,
    writer: Any,
    expected_boot_id_sha256: str,
    seen_nonce_sha256: set[str],
) -> Any:
    """Authenticate and bind the current boot before the first EXEC frame."""
    key = observer._CODEC._validate_key(key)
    deadline = time.monotonic() + SESSION_TIMEOUT_SEC
    audit = observer.ExchangeAudit(auth_key_sha256=hashlib.sha256(key).hexdigest())

    def stage(name: str) -> None:
        audit.current_stage = name

    try:
        stage("banner-read")
        banner = observer._CODEC._read_exact(
            descriptor, len(runtime.DEVICE_BANNER), deadline, audit, writer
        )
        if banner != runtime.DEVICE_BANNER:
            raise observer.AuthObserverError("P335 action banner differs")
        audit.banner_seen = True

        stage("open-write")
        observer._CODEC._send(
            descriptor,
            runtime.FRAME_OPEN,
            0,
            runtime.P335_RUN_ID,
            deadline,
            audit,
        )
        for name, expected_stage in (
            ("entry-diagnostic-read", runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER),
            ("open-diagnostic-read", runtime.DIAGNOSTIC_STAGE_OPEN_PARSED),
            ("rng-diagnostic-read", runtime.DIAGNOSTIC_STAGE_RNG),
        ):
            stage(name)
            diagnostic = observer._P333.parse_diagnostic_frame(
                observer._CODEC._read_frame(descriptor, deadline, audit, writer),
                expected_stage,
            )
            audit.diagnostics.append(diagnostic)
        if audit.diagnostics[-1].code < 0:
            raise observer.AuthObserverError(
                "P335 action device RNG failed", code=audit.diagnostics[-1].code
            )
        audit.rng_eagain_retries = audit.diagnostics[-1].code

        stage("challenge-read")
        challenge = observer._CODEC._read_frame(
            descriptor, deadline, audit, writer
        )
        nonce = observer._CODEC._expect(challenge, runtime.FRAME_CHALLENGE, 0)
        observer._CODEC._validate_nonce(nonce)
        nonce_sha256 = hashlib.sha256(nonce).hexdigest()
        if nonce_sha256 in seen_nonce_sha256:
            raise observer.AuthObserverError(
                "P335 action challenge nonce was replayed before AUTH"
            )
        audit.nonce = nonce
        audit.challenge_seen = True

        stage("auth-write")
        observer._CODEC._send(
            descriptor,
            runtime.FRAME_AUTH,
            1,
            observer.compute_open_tag(key, runtime.P335_RUN_ID, nonce),
            deadline,
            audit,
        )
        stage("ready-read")
        ready = observer._CODEC._read_frame(descriptor, deadline, audit, writer)
        ready_tag = observer._CODEC._expect(ready, runtime.FRAME_READY, 1)
        if not observer._CODEC.constant_time_equal(
            ready_tag,
            observer.compute_ready_tag(key, runtime.P335_RUN_ID, nonce),
        ):
            raise observer.AuthObserverError("P335 action READY differs")
        audit.ready_seen = True
        audit.authenticated = True

        stage("boot-id-read")
        boot_frame = observer._CODEC._read_frame(
            descriptor, deadline, audit, writer
        )
        boot_id = observer.decode_boot_id_frame(
            boot_frame, key, runtime.P335_RUN_ID, nonce
        )
        setattr(audit, "boot_id", boot_id)
        if hashlib.sha256(boot_id).hexdigest() != expected_boot_id_sha256:
            raise observer.AuthObserverError(
                "P335 action per-boot identity changed before EXEC"
            )

        results = []
        for sequence, command in enumerate(runtime.DEFAULT_COMMANDS, start=3):
            stage("exec-write")
            observer._CODEC._send(
                descriptor,
                runtime.FRAME_EXEC,
                sequence,
                observer.compute_exec_tag(
                    key, runtime.P335_RUN_ID, nonce, sequence, command
                )
                + command,
                deadline,
                audit,
            )
            output = bytearray()
            while True:
                stage("exec-read")
                frame = observer._CODEC._read_frame(
                    descriptor, deadline, audit, writer
                )
                if frame.sequence != sequence:
                    raise observer.AuthObserverError(
                        "P335 action response sequence differs"
                    )
                if frame.frame_type == runtime.FRAME_DATA:
                    if not frame.payload:
                        raise observer.AuthObserverError(
                            "P335 action DATA is empty"
                        )
                    output.extend(frame.payload)
                    if len(output) > runtime.MAX_OUTPUT_BYTES:
                        raise observer.AuthObserverError(
                            "P335 action output exceeds bound"
                        )
                    continue
                if frame.frame_type != runtime.FRAME_EXIT:
                    raise observer.AuthObserverError(
                        "P335 action response type differs"
                    )
                flags, exit_code, signal_number, duration_ms = (
                    observer._CODEC._parse_exit(frame.payload, len(output))
                )
                results.append(
                    observer.CommandResult(
                        sequence,
                        command,
                        bytes(output),
                        flags,
                        exit_code,
                        signal_number,
                        duration_ms,
                    )
                )
                break

        close_sequence = (
            runtime.P335_BOOT_ID_SEQUENCE + runtime.P335_COMMANDS_PER_SESSION + 1
        )
        stage("close-write")
        observer._CODEC._send(
            descriptor,
            runtime.FRAME_CLOSE,
            close_sequence,
            observer.compute_close_tag(
                key, runtime.P335_RUN_ID, nonce, close_sequence
            ),
            deadline,
            audit,
        )
        stage("done-read")
        done = observer._CODEC._read_frame(descriptor, deadline, audit, writer)
        done_payload = observer._CODEC._expect(
            done, runtime.FRAME_DONE, close_sequence
        )
        if (
            len(done_payload) != observer.DONE.size
            or observer.DONE.unpack(done_payload)[0] != len(runtime.DEFAULT_COMMANDS)
        ):
            raise observer.AuthObserverError("P335 action DONE count differs")
        audit.done_seen = True
        stage("complete")
        return observer.SessionResult(tuple(results), audit)
    except Exception as exc:
        observer._raise_partial(
            exc, audit, audit.current_stage, code=getattr(exc, "code", None)
        )


def _exchange_full_tuple(
    endpoint: Any,
    expected_identity: Mapping[str, str],
    key: bytes,
    expected_boot_id_sha256: str,
    seen_nonce_sha256: set[str],
) -> tuple[Any, bytes, bytes]:
    path = Path("/dev") / endpoint.tty_name
    before = path.stat()
    if (
        not stat.S_ISCHR(before.st_mode)
        or os.major(before.st_rdev) != endpoint.major
        or os.minor(before.st_rdev) != endpoint.minor
    ):
        raise ActionError("P3.35 tty identity differs before open")
    descriptor = os.open(
        path,
        os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    writer = observer._RawWriter(None)
    try:
        fcntl.ioctl(descriptor, termios.TIOCEXCL)
        tty.setraw(descriptor, termios.TCSANOW)
        repeated_identity, repeated = cdc._resolve_endpoint(endpoint.tty_class)
        if (
            repeated.identity_sha256 != endpoint.identity_sha256
            or repeated_identity != expected_identity
            or os.fstat(descriptor).st_rdev != before.st_rdev
        ):
            raise ActionError("P3.35 tty identity changed after open")
        result = _exchange_before_exec_bound(
            descriptor,
            key,
            writer,
            expected_boot_id_sha256,
            seen_nonce_sha256,
        )
        record = observer._record_success(0, 1, descriptor, result)
        observer._validate_one_session(record, record.boot_id)
        readable, _, _ = select.select([descriptor], [], [], 0)
        if readable:
            try:
                trailing = os.read(descriptor, 1)
            except BlockingIOError:
                trailing = b""
            if trailing:
                raise ActionError("P3.35 action session has trailing bytes")
        return record, bytes(result.audit.tx), bytes(result.audit.rx)
    finally:
        os.close(descriptor)


def _session_evidence(
    action: str,
    ordinal: int,
    record: Any,
    raw_tx: bytes,
    raw_rx: bytes,
    action_dir: Path,
) -> tuple[dict[str, Any], bytes]:
    if hashlib.sha256(record.boot_id).hexdigest() == "0" * 64:
        raise ActionError("P3.35 action boot identity is zero")
    commands = []
    for name, result in zip(resident.ACTION_NAMES, record.result.commands):
        commands.append(
            {
                "name": name,
                "command": identity(result.command),
                "output": identity(result.output),
                "exit_code": result.exit_code,
                "signal_number": result.signal_number,
                "duration_ms": result.duration_ms,
                "ok": result.ok,
                "primary": name == action,
            }
        )
    tx = _write_once(action_dir / "session.tx.bin", raw_tx)
    rx = _write_once(action_dir / "session.rx.bin", raw_rx)
    value = {
        "schema": SCHEMA,
        "action": action,
        "ordinal": ordinal,
        "classification": "accepted",
        "authenticated": record.authenticated,
        "clean_close": record.clean_close,
        "boot_id_sha256": hashlib.sha256(record.boot_id).hexdigest(),
        "challenge_nonce_sha256": hashlib.sha256(record.nonce).hexdigest(),
        "fixed_command_count": len(commands),
        "full_protocol_tuple": True,
        "supporting_results_recorded": True,
        "commands": commands,
        "raw_tx": tx,
        "raw_rx": rx,
        "caller_selected_command": False,
        "interactive_pty": False,
        "file_transfer": False,
        "persistent_change": False,
        "replay_authorized": False,
    }
    payload = canonical(value)
    return value, payload


def run_action(action: str) -> dict[str, Any]:
    if action not in ACTION_INDEX:
        raise ActionError("unknown P3.35 named action")
    activation = validate_activation(require_pass=True)
    prepared, lease, binding, key, initial_nonces = _current_context()
    snapshot = lease.snapshot()
    if snapshot["state"] != "ACTIVE" or snapshot["rollback_required"]:
        raise ActionError("P3.35 resident lease is not active")
    endpoint, endpoint_identity = _select_endpoint(prepared, binding)
    seen_nonces = initial_nonces | _previous_action_nonces(lease)
    next_ordinal = snapshot["actions_started"] + 1
    if not EVIDENCE_DIR.exists():
        _mkdir(EVIDENCE_DIR)
    action_dir = EVIDENCE_DIR / f"action-{next_ordinal:02d}"
    _mkdir(action_dir)
    properties = cdc._udev_properties(
        endpoint.tty_class, action_dir, "0000-udev-properties"
    )
    if (
        properties.get("ID_MM_DEVICE_IGNORE") != "1"
        or properties.get("ID_MM_PORT_IGNORE") != "1"
        or properties.get("ID_USB_INTERFACE_NUM") != "00"
    ):
        raise ActionError("P3.35 tty udev guard properties differ")
    intent = lease.begin_action(action, binding)
    try:
        repeated, repeated_identity = _select_endpoint(prepared, binding)
        if repeated.identity_sha256 != endpoint.identity_sha256:
            raise ActionError("P3.35 endpoint changed after action intent")
        repeated_properties = cdc._udev_properties(
            repeated.tty_class,
            action_dir,
            "0001-udev-properties-post-intent",
        )
        if (
            repeated_properties.get("ID_MM_DEVICE_IGNORE") != "1"
            or repeated_properties.get("ID_MM_PORT_IGNORE") != "1"
            or repeated_properties.get("ID_USB_INTERFACE_NUM") != "00"
        ):
            raise ActionError("P3.35 tty properties changed after action intent")
        record, raw_tx, raw_rx = _exchange_full_tuple(
            repeated,
            repeated_identity,
            key,
            binding["per_boot_id"],
            seen_nonces,
        )
        if hashlib.sha256(record.boot_id).hexdigest() != binding["per_boot_id"]:
            raise ActionError("P3.35 per-boot identity changed")
        value, payload = _session_evidence(
            action, intent["ordinal"], record, raw_tx, raw_rx, action_dir
        )
        result_receipt = _write_once(action_dir / "result.json", payload)
        lease.record_action_result(
            intent,
            {
                "status": "ok",
                "receipt_bytes": result_receipt["size"],
                "receipt_sha256": result_receipt["sha256"],
            },
            binding,
        )
    except BaseException as exc:
        failure = canonical(
            {
                "schema": SCHEMA,
                "action": action,
                "ordinal": intent["ordinal"],
                "classification": "uncertain",
                "error_type": type(exc).__name__,
                "error_sha256": hashlib.sha256(str(exc).encode()).hexdigest(),
                "replay_authorized": False,
            }
        )
        try:
            failure_receipt = _write_once(action_dir / "failure.json", failure)
            lease.record_action_result(
                intent,
                {
                    "status": "uncertain",
                    "receipt_bytes": failure_receipt["size"],
                    "receipt_sha256": failure_receipt["sha256"],
                },
                binding,
            )
        except BaseException:
            pass
        raise ActionError("P3.35 action failed; rollback is required") from exc
    final = resident.ResidentLease.open(LEASE_DIR).snapshot()
    primary = value["commands"][ACTION_INDEX[action]]
    return {
        "schema": "s22plus_fyg8_p335_resident_action_run_v1",
        "verdict": "PASS_P335_RESIDENT_ACTION",
        "action": action,
        "ordinal": intent["ordinal"],
        "full_protocol_tuple": True,
        "primary": primary,
        "session_result": result_receipt,
        "activation": activation["receipt"],
        "lease": final,
        "device_contact": True,
        "read_only": True,
        "replay_authorized": False,
        "rollback_required": final["rollback_required"],
    }


def audit() -> dict[str, Any]:
    activation = validate_activation(require_pass=False)
    return {
        "schema": "s22plus_fyg8_p335_resident_action_audit_v1",
        "verdict": "PASS_P335_RESIDENT_ACTION_RUNNER_H0",
        "activation": activation["receipt"],
        "catalog": list(resident.ACTION_NAMES),
        "full_protocol_tuple": True,
        "device_contact": False,
        "live_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--audit-only", action="store_true")
    modes.add_argument("--action", choices=resident.ACTION_NAMES)
    args = parser.parse_args(argv)
    try:
        value = audit() if args.audit_only else run_action(args.action)
    except (
        ActionError,
        live.F1LiveError,
        resident.LeaseError,
        observer.AuthObserverError,
        cdc.ObserverError,
        raw_capture.RawCaptureError,
        OSError,
    ) as exc:
        print(f"P3.35 resident action error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
