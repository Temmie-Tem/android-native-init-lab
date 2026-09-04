#!/usr/bin/env python3
"""Host-only P3.36 named later-action wrapper.

The wrapper owns only a P336 private evidence namespace.  A caller selects an
immutable action name and supplies an already-open, exact host endpoint; the
wrapper sends no command string and accepts no path.  It writes one intent
before the single P336 resynchronized exchange.  Success and failure are
published with no-clobber files, including the observer's partial TX/RX and
audit exception digest.  An uncertain intent is never replayed.
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
import types
import tty
from typing import Any, Mapping

import device_action_cdc_acm_observer_v1 as cdc
import device_action_f1_live_v2 as live
import device_action_raw_capture_v1 as raw_capture
import s22plus_fyg8_p336_long_idle_acm_observer as observer
import s22plus_fyg8_p336_long_idle_runtime as runtime


ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve(strict=True)
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-f1-live-v2/"
    "p336-ready1-prepared-20260904-1"
)
LEASE_DIR = RUN_DIR / "p336-long-idle-session"
EVIDENCE_DIR = RUN_DIR / "p336-long-idle-action-evidence"
ACTIVATION = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p336_long_idle_action_v1.json"
)
SCHEMA = "s22plus_fyg8_p336_long_idle_action_result_v1"
ACTIVATION_SCHEMA = "s22plus_fyg8_p336_long_idle_action_activation_v1"
REVIEW_VERDICT = "PASS_GO_P336_LONG_IDLE_ACTION_H0_V1"
SESSION_TIMEOUT_SEC = 30.0
MAX_EVIDENCE_BYTES = 256 * 1024
P335_LEASE_SOURCE = Path(__file__).with_name(
    "s22plus_fyg8_p335_resident_session.py"
)
P335_LEASE_SOURCE_IDENTITY = {
    "size": 27_483,
    "sha256": "58e507f5932b988e701c2311da0c406784fcc76f9873ce98676c4858caf1f6a1",
}
P336_LEASE_SCHEMA = "s22plus_fyg8_p336_long_idle_lease_v1"
P336_LEASE_OWNER = "s22plus-fyg8-p336-long-idle"
P335_ACTION_SOURCE = Path(__file__).with_name(
    "s22plus_fyg8_p335_resident_action.py"
)
P335_ACTION_SOURCE_IDENTITY = {
    "size": 29_081,
    "sha256": "1580d18068097b31dbc97795631496fa40338b7610b2e3de1a5cee83a7c4198c",
}
P336_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p336_process_v2_ready_1.json"
)


class ActionError(RuntimeError):
    """The bounded P3.36 action cannot safely continue."""


def _inode(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _load_lease_core() -> types.ModuleType:
    direct = P335_LEASE_SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(P335_LEASE_SOURCE_IDENTITY["size"] + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise ActionError("P3.35 lease source is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or identity(payload) != P335_LEASE_SOURCE_IDENTITY
    ):
        raise ActionError("P3.35 lease source identity differs")
    # The lease implementation is the finalized P335 journal machinery.  A
    # textual identity substitution creates an isolated P336 owner/schema and
    # leaves no object or file shared with the consumed P335 namespace.
    transformed = payload.replace(b"s22plus_fyg8_p335", b"s22plus_fyg8_p336")
    transformed = transformed.replace(b"s22plus-fyg8-p335", b"s22plus-fyg8-p336")
    transformed = transformed.replace(
        b'"s22plus-fyg8-p336"', f'"{P336_LEASE_OWNER}"'.encode("ascii")
    )
    transformed = transformed.replace(
        b'SCHEMA = "s22plus_fyg8_p336_resident_lease_v1"',
        f'SCHEMA = "{P336_LEASE_SCHEMA}"'.encode("ascii"),
    )
    transformed = transformed.replace(b"P3.35", b"P3.36")
    module = types.ModuleType("s22plus_fyg8_p336_long_idle_lease_bound")
    module.__file__ = str(P335_LEASE_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(transformed, str(P335_LEASE_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except BaseException as exc:
        raise ActionError("P336 lease source failed to load") from exc
    if (
        module.SCHEMA != P336_LEASE_SCHEMA
        or module.validate_binding.__globals__.get("SCHEMA") != P336_LEASE_SCHEMA
        or b"s22plus-fyg8-p335" in transformed
    ):
        # The owner check is a literal in the predecessor source.  It is
        # replaced below before this module is used; this guard catches a
        # future source-shape drift rather than silently reusing P335.
        raise ActionError("P336 lease owner/schema substitution differs")
    return module


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


# Build the isolated lease module only after the strict source and JSON
# helpers above exist.  Its schema/owner/path are distinct from consumed P335.
resident = _load_lease_core()
ACTION_NAMES = tuple(resident.ACTION_NAMES)
ACTION_INDEX = {name: index for index, name in enumerate(ACTION_NAMES)}


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
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, min(1024 * 1024, maximum + 1)):
            chunks.append(chunk)
            if sum(map(len, chunks)) > maximum:
                break
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    fields = (
        "st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    payload = b"".join(chunks)
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
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ActionError(f"{label} contains a duplicate key")
            result[key] = value
        return result

    try:
        value = json.loads(payload.decode("ascii"), object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ActionError(f"{label} is invalid") from exc
    if type(value) is not dict or canonical(value) != payload:
        raise ActionError(f"{label} is not canonical")
    return value, payload


def _load_bound_action_core() -> types.ModuleType:
    payload = _stable(
        P335_ACTION_SOURCE, "P3.35 resident action source", 2 * 1024 * 1024
    )
    if identity(payload) != P335_ACTION_SOURCE_IDENTITY:
        raise ActionError("P3.35 resident action source receipt differs")
    module = types.ModuleType("s22plus_fyg8_p335_resident_action_bound_for_p336")
    module.__file__ = str(P335_ACTION_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P335_ACTION_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except BaseException as exc:
        raise ActionError("P3.35 resident action source failed to load") from exc
    # Every function below resolves these globals dynamically.  Rebinding the
    # exact finalized machinery keeps endpoint/lease/closure checks unchanged
    # while selecting only the P336 namespaces and observer.
    module.ROOT = ROOT
    module.SCRIPT = SCRIPT
    module.MANIFEST = P336_MANIFEST
    module.RUN_DIR = RUN_DIR
    module.LEASE_DIR = LEASE_DIR
    module.EVIDENCE_DIR = EVIDENCE_DIR
    module.ACTIVATION = ACTIVATION
    module.SCHEMA = SCHEMA
    module.runtime = runtime
    module.observer = observer
    module.resident = resident
    module.ACTION_INDEX = ACTION_INDEX
    module.SESSION_TIMEOUT_SEC = SESSION_TIMEOUT_SEC
    return module


_BOUND_ACTION = _load_bound_action_core()


def _source_receipts() -> dict[str, dict[str, Any]]:
    paths = {
        "runner": SCRIPT,
        "runtime": Path(runtime.__file__).resolve(),
        "observer": Path(observer.__file__).resolve(),
        "lease_core": P335_LEASE_SOURCE,
        "action_core": P335_ACTION_SOURCE,
        "p335_runtime": runtime.SOURCE,
        "p335_observer": observer.SOURCE,
        "cdc": Path(cdc.__file__).resolve(),
        "live": Path(live.__file__).resolve(),
        "raw_capture": Path(raw_capture.__file__).resolve(),
    }
    return {
        name: {
            "path": str(path.relative_to(ROOT)),
            **identity(_stable(path, name, 2 * 1024 * 1024)),
        }
        for name, path in paths.items()
    }


def _expected_activation(
    inputs: Mapping[str, Any], review: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema": ACTIVATION_SCHEMA,
        "contract_id": observer.CONTRACT_ID,
        "target": dict(resident.TARGET),
        "run_id": runtime.P336_RUN_ID_HEX,
        "manifest": str(P336_MANIFEST.relative_to(ROOT)),
        "run_directory": str(RUN_DIR.relative_to(ROOT)),
        "lease_directory": str(LEASE_DIR.relative_to(ROOT)),
        "evidence_directory": str(EVIDENCE_DIR.relative_to(ROOT)),
        "lease_schema": resident.SCHEMA,
        "lease_owner": P336_LEASE_OWNER,
        "catalog": {
            "identity": {"argv": ["/bin/busybox", "id"]},
            "kernel": {"argv": ["/bin/busybox", "uname", "-a"]},
            "session-nonce": {
                "argv": [
                    "/bin/busybox", "echo", "P328-NONCE", runtime.P336_RUN_ID_HEX
                ]
            },
        },
        "session": {
            "open_before_resync": True,
            "terminator": "exact_stage_1_open_parsed",
            "max_preamble_pairs": observer.MAX_PREAMBLE_PAIRS,
            "max_resync_bytes": observer.MAX_RESYNC_BYTES,
            "commands": [command.decode("ascii") for command in runtime.DEFAULT_COMMANDS],
            "commands_per_session": len(runtime.DEFAULT_COMMANDS),
            "session_per_action": 1,
            "timeout_sec": SESSION_TIMEOUT_SEC,
        },
        "bounds": {
            "action_cap": resident.MAX_ACTIONS,
            "lease_sec": resident.MAX_LEASE_SECONDS,
            "raw_rx_max": MAX_EVIDENCE_BYTES,
            "raw_tx_max": MAX_EVIDENCE_BYTES,
            "retry": False,
        },
        "safety": {
            "read_only": True,
            "caller_command": False,
            "caller_path": False,
            "interactive_pty": False,
            "file_transfer": False,
            "persistent_change": False,
            "reboot": False,
            "device_contact_in_audit": False,
        },
        "inputs": dict(inputs),
        "independent_review": dict(review),
    }


def validate_activation(*, require_pass: bool) -> dict[str, Any]:
    value, payload = _strict_json(
        ACTIVATION, "P3.36 long-idle action activation", MAX_EVIDENCE_BYTES
    )
    review = value.get("independent_review")
    allowed = {"status": "pass-go", "verdict": REVIEW_VERDICT}
    if review not in ({"status": "review-pending", "verdict": None}, allowed):
        raise ActionError("P3.36 action review state differs")
    if require_pass and review != allowed:
        raise ActionError("P3.36 action runner lacks independent PASS_GO")
    expected = _expected_activation(_source_receipts(), review)
    if not _typed_equal(value, expected):
        raise ActionError("P3.36 action activation differs")
    return {"value": value, "receipt": identity(payload)}


def _mkdir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=False, exist_ok=False)
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def _write_once(path: Path, payload: bytes) -> dict[str, Any]:
    if len(payload) > MAX_EVIDENCE_BYTES:
        raise ActionError("P3.36 action evidence exceeds its bound")
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


# Reuse the finalized P335 context machinery after its globals were rebound to
# P336.  This retains exact OBSERVED/candidate proof, endpoint/topology, key,
# Type-C, udev, lease, and nonce-history checks without editing common live.
_current_context = _BOUND_ACTION._current_context
_previous_action_nonces = _BOUND_ACTION._previous_action_nonces
_select_endpoint = _BOUND_ACTION._select_endpoint


def _exchange_full_tuple(
    endpoint: Any,
    expected_identity: Mapping[str, str],
    key: bytes,
    expected_boot_id_sha256: str,
    seen_nonce_sha256: set[str],
) -> tuple[observer.LongIdleSession, bytes, bytes]:
    path = Path("/dev") / endpoint.tty_name
    try:
        before = path.stat()
    except OSError as exc:
        raise ActionError("P3.36 tty identity is unavailable before open") from exc
    if (
        not stat.S_ISCHR(before.st_mode)
        or os.major(before.st_rdev) != endpoint.major
        or os.minor(before.st_rdev) != endpoint.minor
    ):
        raise ActionError("P3.36 tty identity differs before open")
    descriptor = os.open(
        path,
        os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    try:
        fcntl.ioctl(descriptor, termios.TIOCEXCL)
        tty.setraw(descriptor, termios.TCSANOW)
        repeated_identity, repeated = cdc._resolve_endpoint(endpoint.tty_class)
        if (
            repeated.identity_sha256 != endpoint.identity_sha256
            or repeated_identity != expected_identity
            or os.fstat(descriptor).st_rdev != before.st_rdev
        ):
            raise ActionError("P3.36 tty identity changed after open")
        result = observer.exchange_late_action(
            descriptor,
            key,
            expected_boot_id_sha256=expected_boot_id_sha256,
            seen_nonce_sha256=seen_nonce_sha256,
            timeout_sec=SESSION_TIMEOUT_SEC,
        )
        session = result.session
        observer.validate_late_result(result)
        readable, _, _ = select.select([descriptor], [], [], 0)
        if readable:
            try:
                trailing = os.read(descriptor, 1)
            except BlockingIOError:
                trailing = b""
            if trailing:
                raise ActionError("P3.36 action session has trailing bytes")
        return session, session.raw_tx, session.raw_rx
    finally:
        os.close(descriptor)


def _session_evidence(
    action: str,
    ordinal: int,
    session: observer.LongIdleSession,
    action_dir: Path,
) -> tuple[dict[str, Any], bytes]:
    observer.validate_late_result(observer.LongIdleResult(session, "accepted"))
    if hashlib.sha256(session.boot_id).hexdigest() == "0" * 64:
        raise ActionError("P3.36 action boot identity is zero")
    assert session.result is not None
    assert session.audit is not None
    commands = []
    for name, item in zip(resident.ACTION_NAMES, session.result.commands):
        commands.append(
            {
                "name": name,
                "command": identity(item.command),
                "output": identity(item.output),
                "exit_code": item.exit_code,
                "signal_number": item.term_signal,
                "duration_ms": item.duration_ms,
                "ok": item.ok,
                "primary": name == action,
            }
        )
    tx = _write_once(action_dir / "session.tx.bin", session.raw_tx)
    rx = _write_once(action_dir / "session.rx.bin", session.raw_rx)
    value = {
        "schema": SCHEMA,
        "action": action,
        "ordinal": ordinal,
        "classification": "accepted",
        "authenticated": session.authenticated,
        "clean_close": session.clean_close,
        "boot_id_sha256": hashlib.sha256(session.boot_id).hexdigest(),
        "challenge_nonce_sha256": hashlib.sha256(session.nonce).hexdigest(),
        "fixed_command_count": len(commands),
        "full_protocol_tuple": True,
        "supporting_results_recorded": True,
        "open_sent_before_resync": True,
        "open_parsed_seen": True,
        "resync_preamble_count": session.preamble_count,
        "commands": commands,
        "raw_tx": tx,
        "raw_rx": rx,
        "audit": {
            "current_stage": session.audit.current_stage,
            "failure_stage": session.audit.failure_stage,
            "failure_code": session.audit.failure_code,
            "exception_type": session.audit.exception_type,
            "exception_sha256": session.audit.exception_sha256,
            "nested_exception_sha256": getattr(
                session.audit, "nested_exception_sha256", None
            ),
        },
        "caller_selected_command": False,
        "interactive_pty": False,
        "file_transfer": False,
        "persistent_change": False,
        "replay_authorized": False,
    }
    return value, canonical(value)


def _action_dir(action: str) -> Path:
    if action not in ACTION_INDEX:
        raise ActionError("unknown P3.36 named action")
    return EVIDENCE_DIR / action


def _intent(action: str, expected_boot_id: bytes) -> bytes:
    return canonical(
        {
            "schema": "s22plus_fyg8_p336_long_idle_intent_v1",
            "action": action,
            "ordinal": ACTION_INDEX[action] + 1,
            "run_id_hex": runtime.P336_RUN_ID_HEX,
            "expected_boot_id_sha256": hashlib.sha256(expected_boot_id).hexdigest(),
            "one_session": True,
            "open_before_resync": True,
            "retry": False,
            "replay_authorized": False,
        }
    )


def run_action(action: str) -> dict[str, Any]:
    """Run one named P336 action through the exact bound resident lease.

    The CLI supplies only one of the immutable names below.  Endpoint, key,
    boot identity, and nonce history are reopened from the P336 prepared
    closure before the durable action intent; no caller command/path exists.
    """

    if action not in ACTION_INDEX:
        raise ActionError("unknown P3.36 named action")
    activation = validate_activation(require_pass=True)
    prepared, lease, binding, key, initial_nonces = _current_context()
    snapshot = lease.snapshot()
    if snapshot["state"] != "ACTIVE" or snapshot["rollback_required"]:
        raise ActionError("P3.36 resident lease is not active")
    endpoint, endpoint_identity = _select_endpoint(prepared, binding)
    seen_nonce_sha256 = initial_nonces | _previous_action_nonces(lease)
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
        raise ActionError("P3.36 tty udev guard properties differ")
    intent = lease.begin_action(action, binding)
    session: observer.LongIdleSession | None = None
    runner_stage = "post-intent"
    try:
        runner_stage = "post-intent-endpoint"
        repeated, repeated_identity = _select_endpoint(prepared, binding)
        if repeated.identity_sha256 != endpoint.identity_sha256:
            raise ActionError("P3.36 endpoint changed after action intent")
        runner_stage = "post-intent-udev"
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
            raise ActionError("P3.36 tty properties changed after action intent")
        runner_stage = "exchange"
        session, raw_tx, raw_rx = _exchange_full_tuple(
            repeated,
            repeated_identity,
            key,
            binding["per_boot_id"],
            seen_nonce_sha256,
        )
        if hashlib.sha256(session.boot_id).hexdigest() != binding["per_boot_id"]:
            raise ActionError("P3.36 per-boot identity changed")
        runner_stage = "receipt"
        value, payload = _session_evidence(
            action, intent["ordinal"], session, action_dir
        )
        result_receipt = _write_once(action_dir / "result.json", payload)
        runner_stage = "lease-result"
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
        audit = getattr(exc, "audit", None)
        if session is not None:
            audit = session.audit
        raw_tx = b"" if audit is None else bytes(audit.tx)
        raw_rx = b"" if audit is None else bytes(audit.rx)
        try:
            tx_receipt = _write_once(action_dir / "failure.tx.bin", raw_tx)
            rx_receipt = _write_once(action_dir / "failure.rx.bin", raw_rx)
            failure = observer.render_failure(exc)
            failure.update(
                {
                    "action": action,
                    "ordinal": intent["ordinal"],
                    "intent": {
                        "schema": resident.SCHEMA,
                        "ordinal": intent["ordinal"],
                        "action": intent["action"],
                    },
                    "raw_tx": tx_receipt,
                    "raw_rx": rx_receipt,
                    "replay_authorized": False,
                    "runner_stage": runner_stage,
                }
            )
            if failure.get("failure_stage") is None:
                failure["failure_stage"] = runner_stage
            if failure.get("nested_exception_sha256") is None:
                failure["nested_exception_sha256"] = failure["exception_sha256"]
            failure_receipt = _write_once(
                action_dir / "failure.json", canonical(failure)
            )
            lease.record_action_result(
                intent,
                {
                    "status": "uncertain",
                    "receipt_bytes": failure_receipt["size"],
                    "receipt_sha256": failure_receipt["sha256"],
                },
                binding,
            )
        except BaseException as persist_exc:
            raise ActionError(
                "P3.36 uncertain action evidence or lease result could not be retained"
            ) from persist_exc
        raise ActionError(
            "P3.36 action failed; no replay is permitted and recovery is required"
        ) from exc
    final = resident.ResidentLease.open(LEASE_DIR).snapshot()
    primary = value["commands"][ACTION_INDEX[action]]
    return {
        "schema": SCHEMA,
        "verdict": "PASS_P336_LONG_IDLE_ACTION",
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
        "schema": "s22plus_fyg8_p336_long_idle_action_audit_v1",
        "verdict": "PASS_P336_LONG_IDLE_ACTION_H0",
        "activation": activation["receipt"],
        "catalog": list(ACTION_NAMES),
        "open_before_resync": True,
        "max_preamble_pairs": observer.MAX_PREAMBLE_PAIRS,
        "partial_raw_retention": True,
        "nested_exception_digest": True,
        "device_contact": False,
        "live_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--audit-only", action="store_true")
    modes.add_argument("--action", choices=ACTION_NAMES)
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        args = parser.parse_args(arguments)
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
        print(f"P3.36 long-idle action blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
