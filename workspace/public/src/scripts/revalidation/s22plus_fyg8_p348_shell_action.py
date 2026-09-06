"""Host-owned P348 caller-command action runner.

Every invocation consumes one private command file, one authenticated tty
session, and one lease ordinal.  The command bytes are copied and fsynced
before the intent is published; the exact copy is the only command sent to
the retained shell.  No retry, descriptor reopen, or lease renewal exists in
this module.
"""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import select
import signal
import stat
import termios
import threading
import time
import tty
from typing import Any, Callable, Mapping

import device_action_raw_capture_v1 as raw_capture
import s22plus_fyg8_research_shell_exchange as shell_exchange
import s22plus_fyg8_p348_shell_session as session


SCHEMA = session.ACTION_RESULT_SCHEMA
RUN_SCHEMA = "s22plus_fyg8_p348_shell_action_run_v1"
EVIDENCE_DIRECTORY = session.EVIDENCE_DIRECTORY
MAX_COMMAND_BYTES = session.MAX_COMMAND_BYTES
MAX_OUTPUT_BYTES = session.MAX_OUTPUT_BYTES
MAX_RAW_RX_BYTES = 512 * 1024
SESSION_TIMEOUT_SEC = session.SESSION_WINDOW_SECONDS
ACTION_NAME = session.ACTION_NAME


class ActionError(RuntimeError):
    """The action could not complete a trustworthy retained session."""


def _live_error(live: Any, message: str, cause: BaseException | None = None) -> BaseException:
    error_type = getattr(live, "F1LiveError", ActionError)
    error = error_type(message)
    if cause is not None:
        error.__cause__ = cause
    return error


def _variant(live: Any) -> Any:
    variants = getattr(getattr(live, "typed_evidence", None), "SHELL_VARIANTS", {})
    value = variants.get("p348") if hasattr(variants, "get") else None
    if value is None:
        raise _live_error(live, "P348 shell variant is unavailable")
    return value


def _stable_identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _command_file_scope(prepared: Any, path: Path) -> bool:
    """Allow only a command under workspace/private or this prepared run."""

    direct = path.absolute()
    roots: list[Path] = []
    root = getattr(prepared, "root", None)
    if root is not None:
        roots.append(Path(root).absolute() / "workspace" / "private")
    run_dir = getattr(prepared, "run_dir", None)
    if run_dir is not None:
        roots.append(Path(run_dir).absolute())
    for allowed in roots:
        try:
            direct.relative_to(allowed)
        except ValueError:
            continue
        return True
    return False


def read_command_file(prepared: Any, command_file: Path | str) -> tuple[bytes, dict[str, Any]]:
    """Read exactly once, with stable metadata and P348 command validation."""

    if not isinstance(command_file, (Path, str)):
        raise ActionError("P348 command file must be a Path")
    path = Path(command_file).absolute()
    if not _command_file_scope(prepared, path):
        raise ActionError("P348 command file is outside workspace/private")
    try:
        before = path.lstat()
    except OSError as exc:
        raise ActionError("P348 command file is unavailable") from exc
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or path.resolve() != path
        or stat.S_IMODE(before.st_mode) not in (0o400, 0o600)
    ):
        raise ActionError("P348 command file identity is unsafe")
    descriptor = -1
    chunks: list[bytes] = []
    total = 0
    after_fd: os.stat_result | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        inside = os.fstat(descriptor)
        if _stable_identity(before) != _stable_identity(inside):
            raise ActionError("P348 command file changed before read")
        while True:
            chunk = os.read(descriptor, MAX_COMMAND_BYTES + 1 - total)
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_COMMAND_BYTES:
                raise ActionError("P348 command file exceeds 1023-byte bound")
        after_fd = os.fstat(descriptor)
    except OSError as exc:
        raise ActionError("P348 command file read failed") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    after = path.lstat()
    if after_fd is None or _stable_identity(before) != _stable_identity(after) or _stable_identity(before) != _stable_identity(after_fd):
        raise ActionError("P348 command file changed during read")
    command = b"".join(chunks)
    try:
        command = shell_exchange.command_bytes(command)
    except (TypeError, ValueError, UnicodeDecodeError) as exc:
        raise ActionError("P348 command bytes violate UTF-8/control-byte rules") from exc
    return command, session.identity(command)


def _mkdir(path: Path) -> None:
    session._mkdir(path)  # noqa: SLF001 - same private no-clobber core


def _write_once(path: Path, payload: bytes) -> dict[str, Any]:
    return session.write_bytes_once(path, payload)


def _write_json(path: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    return _write_once(path, session.canonical_bytes(dict(value)))


def _select_endpoint(live: Any, prepared: Any, binding: Mapping[str, Any]) -> tuple[Any, dict[str, str]]:
    cdc = live.cdc_acm_observer
    source = prepared.bundle.manifest["observation"]["candidate_observer"]
    spec = {key: source[key] for key in cdc.SPEC_KEYS}
    exact: list[tuple[Any, dict[str, str]]] = []
    for identity_value, endpoint in cdc.scan_endpoints():
        if (
            cdc._matches(spec, endpoint.topology, identity_value, endpoint)
            and hashlib.sha256(endpoint.topology.encode()).hexdigest() == binding["topology"]["sha256"]
        ):
            exact.append((endpoint, identity_value))
    if len(exact) != 1:
        raise _live_error(live, "P348 exact retained-shell endpoint count differs")
    return exact[0]


def _udev_ok(live: Any, endpoint: Any, directory: Path, name: str) -> None:
    properties = live.cdc_acm_observer._udev_properties(endpoint.tty_class, directory, name)
    expected = {"ID_MM_DEVICE_IGNORE": "1", "ID_MM_PORT_IGNORE": "1", "ID_USB_INTERFACE_NUM": "00"}
    if any(properties.get(key) != value for key, value in expected.items()):
        raise _live_error(live, "P348 tty udev guard properties differ")


def _variant_codec(live: Any, variant: Any) -> tuple[Any, Any]:
    opener = getattr(live, "_open_header_initial_observer_module", None)
    if not callable(opener):
        raise _live_error(live, "P348 retained shell codec loader is unavailable")
    observer = opener(variant.runtime, variant.observer, "p348-shell-action")
    return observer, variant.runtime


def _check_lease_expiry(lease: Any, elapsed: int) -> None:
    """Stop live I/O once the durable BOOTTIME lease deadline is reached."""

    record = getattr(lease, "lease", None)
    if not isinstance(record, Mapping):
        return
    expires = record.get("expires_elapsed_ns")
    if type(expires) is int and elapsed >= expires:
        lease._terminal("EXPIRY", "P348 lease deadline expired", elapsed)  # noqa: SLF001
        raise TimeoutError("P348 lease deadline expired")


class _SuspendAwareClock:
    """Small time seam for the shared exchange's monotonic deadline."""

    def __init__(
        self, lease: session.ShellLease, *, deadline: float | None = None
    ) -> None:
        self.lease = lease
        self.deadline = deadline

    def _check(self) -> float:
        # BOOTTIME is the lease authority.  The logical deadline is the
        # shorter monotonic exchange window.  Both must be checked before a
        # shared clock value can authorize a select timeout or later I/O.
        elapsed = session.clock_now_ns()
        self.lease._check_clock(elapsed)  # noqa: SLF001
        _check_lease_expiry(self.lease, elapsed)
        value = time.monotonic()
        if self.deadline is not None and value >= self.deadline:
            raise TimeoutError("P348 logical session deadline expired")
        return value

    def monotonic(self) -> float:
        return self._check()


class _SuspendAwareOS:
    """Guard codec/shared-exchange reads and writes after select returns."""

    def __init__(
        self,
        base: Any,
        lease: session.ShellLease,
        *,
        deadline: float | None = None,
    ) -> None:
        self._base = base
        self._lease = lease
        self._deadline = deadline

    def _check(self) -> None:
        elapsed = session.clock_now_ns()
        self._lease._check_clock(elapsed)  # noqa: SLF001
        _check_lease_expiry(self._lease, elapsed)
        if self._deadline is not None and time.monotonic() >= self._deadline:
            raise TimeoutError("P348 logical session deadline expired")

    def read(self, descriptor: int, size: int) -> bytes:
        self._check()
        return self._base.read(descriptor, size)

    def write(self, descriptor: int, payload: bytes) -> int:
        self._check()
        return self._base.write(descriptor, payload)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)


def _expected_nonce(runtime: Any) -> bytes:
    run_id_hex = getattr(runtime, "P348_RUN_ID_HEX", None) or getattr(runtime, "P347_RUN_ID_HEX", None) or getattr(runtime, "P345_RUN_ID_HEX", None)
    if not isinstance(run_id_hex, str):
        run_id_hex = getattr(runtime, "P335_RUN_ID_HEX")
    return b"P328-NONCE " + run_id_hex.encode("ascii") + b"\n"


def _acceptance_role(variant: Any, command: bytes, outcome: str, shell_result: Any) -> str | None:
    """Resolve only a reviewed finite command digest into a capability role.

    The P348 observer/runtime may publish ``LATER_ACCEPTANCE_COMMANDS`` as a
    mapping of role names to ``{"command": bytes|identity, "outcome": str}``.
    Arbitrary caller commands deliberately receive no role, so a return-zero
    command cannot satisfy the overall capability gate by itself.
    """

    table = getattr(variant.observer, "LATER_ACCEPTANCE_COMMANDS", None)
    if table is None:
        table = getattr(variant, "later_acceptance_commands", None)
    if not isinstance(table, Mapping):
        return None
    command_id = session.identity(command)
    for role, spec in table.items():
        if not isinstance(role, str) or not isinstance(spec, Mapping):
            continue
        expected = spec.get("command")
        if isinstance(expected, (bytes, bytearray)):
            expected = session.identity(bytes(expected))
        if expected != command_id or spec.get("outcome") != outcome:
            continue
        middle = getattr(getattr(shell_result, "session", None), "commands", (None, None, None))[1]
        checks = spec.get("middle")
        if isinstance(checks, Mapping):
            expected_output = checks.get("output")
            if isinstance(expected_output, (bytes, bytearray)):
                expected_output = session.identity(bytes(expected_output))
            actual_output = session.identity(getattr(middle, "output", b""))
            if expected_output is not None and expected_output != actual_output:
                continue
            if any(
                key in checks
                and checks[key] != value
                for key, value in {
                    "flags": getattr(middle, "flags", None),
                    "exit_code": getattr(middle, "exit_code", None),
                    "signal_number": getattr(middle, "term_signal", getattr(middle, "signal_number", None)),
                    "cancel_sent": getattr(shell_result, "cancel_sent", None),
                    "cancel_ack": getattr(shell_result, "cancel_ack", None),
                }.items()
            ):
                continue
            if "duration_ms_min" in checks and getattr(middle, "duration_ms", -1) < checks["duration_ms_min"]:
                continue
        return role
    return None


def _session_receipt(
    live: Any,
    variant: Any,
    command: bytes,
    binding: Mapping[str, Any],
    intent: Mapping[str, Any],
    shell_result: Any,
    raw_tx: dict[str, Any],
    raw_rx: dict[str, Any],
    capture: Any,
) -> dict[str, Any]:
    runtime = variant.runtime
    session_result = getattr(shell_result, "session", None)
    audit = getattr(session_result, "audit", None)
    commands = getattr(session_result, "commands", None)
    if audit is None or not isinstance(commands, (tuple, list)) or len(commands) != 3:
        raise _live_error(live, "P348 retained shell protocol tuple is incomplete")
    required_audit = ("banner_seen", "challenge_seen", "ready_seen", "authenticated", "done_seen")
    if not all(getattr(audit, name, False) is True for name in required_audit):
        raise _live_error(live, "P348 retained shell authenticated close is incomplete")
    defaults = tuple(runtime.DEFAULT_COMMANDS)
    if len(defaults) != 3:
        raise _live_error(live, "P348 fixed identity/nonce command tuple differs")
    rows: list[dict[str, Any]] = []
    for sequence, item, expected in zip((3, 4, 5), commands, (defaults[0], command, defaults[2])):
        actual = getattr(item, "command", None)
        output = getattr(item, "output", None)
        flags = getattr(item, "flags", None)
        exit_code = getattr(item, "exit_code", None)
        signal_number = getattr(item, "term_signal", getattr(item, "signal_number", None))
        duration_ms = getattr(item, "duration_ms", None)
        if (
            getattr(item, "sequence", None) != sequence
            or actual != expected
            or type(output) is not bytes
            or any(type(value) is not int for value in (flags, exit_code, signal_number, duration_ms))
        ):
            raise _live_error(live, "P348 retained shell command identity differs")
        rows.append(
            {
                "sequence": sequence,
                "command": session.identity(expected),
                "output": session.identity(output),
                "flags": flags,
                "exit_code": exit_code,
                "signal_number": signal_number,
                "duration_ms": duration_ms,
                "forwarded_bytes": len(output),
                "ok": flags == 0 and exit_code == 0 and signal_number == 0,
            }
        )
    if not shell_exchange.parent_identity_valid(commands[0].output):
        raise _live_error(live, "P348 parent identity witness differs")
    if commands[0].flags != 0 or commands[0].exit_code != 0 or commands[0].term_signal != 0:
        raise _live_error(live, "P348 identity command failed")
    if commands[2].output != _expected_nonce(runtime) or commands[2].flags != 0 or commands[2].exit_code != 0 or commands[2].term_signal != 0:
        raise _live_error(live, "P348 session nonce witness differs")
    boot_id_sha256 = hashlib.sha256(audit.boot_id).hexdigest()
    if boot_id_sha256 != binding["per_boot_id"]:
        raise _live_error(live, "P348 per-boot identity changed")
    outcome = getattr(shell_result, "outcome", None)
    middle = commands[1]
    exec_failure = bool(middle.flags & 4) or middle.exit_code in (126, 127)
    if exec_failure:
        # EXEC_FAILURE is a stop condition even when a malformed or legacy
        # producer also sets timeout/truncation bits in the same EXIT frame.
        outcome = "exec-failed"
    elif middle.flags & getattr(runtime, "P345_CANCELLED_FLAG", getattr(runtime, "FLAG_CANCELLED", 8)):
        outcome = "cancelled"
    elif middle.flags & 1:
        outcome = "timeout"
    elif middle.flags & 2:
        outcome = "truncated"
    elif middle.exit_code != 0 or middle.term_signal != 0:
        outcome = "command-failed"
    elif outcome not in ("ok", "command-failed", "timeout", "truncated", "cancelled", "exec-failed"):
        outcome = "ok"
    continuation = outcome != "exec-failed"
    binding_digest = session.digest(binding)
    value: dict[str, Any] = {
        "schema": SCHEMA,
        "action": ACTION_NAME,
        "ordinal": intent["ordinal"],
        "binding_sha256": binding_digest,
        "intent_sha256": session.digest(intent),
        "command": session.identity(command),
        "session_complete": True,
        "command_outcome": outcome,
        "continuation_allowed": continuation,
        "commands": rows,
        "selected_output": rows[1]["output"],
        "selected_output_path": f"{EVIDENCE_DIRECTORY}/action-{intent['ordinal']:02d}/selected.stdout.bin",
        "boot_id_sha256": boot_id_sha256,
        "challenge_nonce_sha256": hashlib.sha256(audit.nonce).hexdigest(),
        "cancel_sent": bool(getattr(shell_result, "cancel_sent", False)),
        "cancel_ack": getattr(shell_result, "cancel_ack", None),
        "raw_tx": raw_tx,
        "raw_rx": raw_rx,
        "raw_capture": {
            "receipt": str(getattr(capture, "receipt_path", "")),
            "stdout": dict(getattr(capture, "stdout", {})),
            "stderr": dict(getattr(capture, "stderr", {})),
        },
        "session_result": {
            "authenticated": True,
            "clean_close": True,
            "done_seen": True,
            "forwarded_output_bytes": len(commands[1].output),
        },
        "caller_selected_command": True,
        "interactive_pty": False,
        "persistent_change": False,
        "replay_authorized": False,
    }
    role = _acceptance_role(variant, command, outcome, shell_result)
    if role is not None:
        value["acceptance_role"] = role
    return value


@contextmanager
def _locks(live: Any, prepared: Any):
    registry = getattr(live, "consumed_registry", None)
    if registry is None or not callable(getattr(registry, "target_session_lease", None)):
        raise _live_error(live, "P348 target-session lock is unavailable")
    registry_lock = registry.target_session_lease(prepared.root)
    odin = getattr(live, "odin_core", None)
    if odin is None or not callable(getattr(odin, "transaction_session", None)):
        raise _live_error(live, "P348 transaction lock is unavailable")
    transaction = odin.transaction_session(prepared.run_dir / "f1-session")
    with registry_lock:
        with transaction:
            yield


@contextmanager
def _cancel_owner(external: Callable[[], bool]):
    """Install one owner-local SIGINT request without killing the exchange."""

    requested = threading.Event()
    previous = None
    installed = False
    if threading.current_thread() is threading.main_thread():
        try:
            previous = signal.getsignal(signal.SIGINT)

            def handler(_signum: int, _frame: Any) -> None:
                requested.set()

            signal.signal(signal.SIGINT, handler)
            installed = True
        except (ValueError, OSError):
            installed = False

    def is_requested() -> bool:
        if requested.is_set():
            return True
        try:
            return bool(external())
        except Exception:
            # A broken cancel callback cannot silently change the command
            # stream; the owner treats it as a cancellation request.
            return True

    try:
        yield is_requested
    finally:
        if installed:
            signal.signal(signal.SIGINT, previous)


def _current_context(live: Any, prepared: Any):
    if not live._p348_bundle(prepared.bundle):
        raise _live_error(live, "not the exact P348 retained-shell candidate")
    journal = live.core.Journal.reopen(prepared.run_dir / "transaction", prepared.binding_sha256)
    state = live._state(prepared)
    if (
        journal.state() != "OBSERVED"
        or state.get("candidate_completed") is not True
        or state.get("candidate_classification") != "odin_transfer_completed"
        or state.get("p348_shell_session_active") is not True
        or state.get("p348_shell_rollback_required") is not False
        or state.get("rollback_completed") is not False
    ):
        raise _live_error(live, "P348 retained shell state is not active")
    durable = live._reopen_candidate_observation(prepared)
    if durable.get("accepted") is not True or not live._p348_proof_ok(durable):
        raise _live_error(live, "P348 initial proof cannot be reopened")
    binding = session.binding_for(live, prepared, durable)
    lease = session.ShellLease.open(prepared.run_dir / session.DIRECTORY)
    if session.canonical_bytes(binding) != session.canonical_bytes(lease.binding):
        raise _live_error(live, "P348 current lease binding differs")
    # Publication marks the lease active before the observer guard is released
    # so the normal F1 owner can perform that release as a separate durable
    # step.  A crash in that gap must never authorize a later tty OPEN.
    guard_release = live._reopen_candidate_guard_release(prepared)
    if (
        state.get("candidate_observer_guard_release_status") != guard_release.get("status")
        or state.get("candidate_observer_guard_released") is not guard_release.get("released")
        or state.get("candidate_observer_guard_warning") != guard_release.get("warning")
        or state.get("candidate_observer_guard_release_receipt_sha256")
        != guard_release.get("receipt_sha256")
        or guard_release.get("released") is not True
        or guard_release.get("status") != "released"
    ):
        raise _live_error(live, "P348 observer guard release is not durably verified")
    key, key_sha = live._p328_read_auth_key(prepared)
    if key_sha != binding["key"]["sha256"]:
        raise _live_error(live, "P348 private key identity differs")
    live._p324_typec_lane_value(prepared, revalidate=True)
    proof = durable[session.PROOF_KEY]
    initial_nonces = {
        row["nonce_sha256"]
        for row in proof["sessions"]
        if isinstance(row, Mapping) and isinstance(row.get("nonce_sha256"), str)
    }
    if len(initial_nonces) != 6:
        raise _live_error(live, "P348 initial nonce history differs")
    try:
        nonces = session.validate_previous_actions(live, prepared, lease, initial_nonces)
    except session.LeaseError as exc:
        raise _live_error(live, "P348 prior retained action evidence is not replayable", exc)
    return lease, binding, key, nonces, durable


def _exchange_once(
    live: Any,
    variant: Any,
    endpoint: Any,
    expected_identity: Mapping[str, str],
    key: bytes,
    command: bytes,
    binding: Mapping[str, Any],
    seen_nonces: set[str],
    writer: Any,
    expires_elapsed_ns: int,
    lease: session.ShellLease,
    cancel_requested: Callable[[], bool],
) -> tuple[Any, Any]:
    path = Path("/dev") / endpoint.tty_name
    before = path.stat()
    if not stat.S_ISCHR(before.st_mode) or (os.major(before.st_rdev), os.minor(before.st_rdev)) != (endpoint.major, endpoint.minor):
        raise _live_error(live, "P348 tty identity differs before open")
    descriptor = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        fcntl.ioctl(descriptor, termios.TIOCEXCL)
        tty.setraw(descriptor, termios.TCSANOW)
        repeated_identity, repeated = live.cdc_acm_observer._resolve_endpoint(endpoint.tty_class)
        if repeated.identity_sha256 != endpoint.identity_sha256 or repeated_identity != expected_identity or os.fstat(descriptor).st_rdev != before.st_rdev:
            raise _live_error(live, "P348 tty changed after open")
        remaining = (expires_elapsed_ns - session.clock_now_ns()) / 1_000_000_000
        if remaining < SESSION_TIMEOUT_SEC:
            raise _live_error(live, "P348 lease lacks a full session window before OPEN")
        observer, _runtime = _variant_codec(live, variant)
        # shell_exchange uses CLOCK_MONOTONIC internally for the logical I/O
        # timeout.  BOOTTIME admission is checked again immediately after the
        # exchange, so suspend cannot turn a stale action into continuation.
        deadline = time.monotonic() + min(SESSION_TIMEOUT_SEC, remaining)
        previous_clock = shell_exchange.time
        previous_observer_clock = getattr(observer, "time", None)
        codec = getattr(observer, "_CODEC", None)
        previous_codec_clock = getattr(codec, "time", None)
        previous_codec_os = getattr(codec, "os", None)
        previous_exchange_os = shell_exchange.os
        suspend_clock = _SuspendAwareClock(lease, deadline=deadline)
        suspend_os = _SuspendAwareOS(
            previous_codec_os or os, lease, deadline=deadline
        )
        shell_exchange.time = suspend_clock
        shell_exchange.os = suspend_os
        if previous_observer_clock is not None:
            observer.time = suspend_clock
        if codec is not None:
            codec.time = suspend_clock
            if previous_codec_os is not None:
                codec.os = suspend_os
        try:
            result = shell_exchange.exchange(
                observer,
                descriptor,
                key,
                command,
                binding["per_boot_id"],
                seen_nonces,
                writer,
                deadline=deadline,
                cancel_requested=cancel_requested,
            )
        finally:
            shell_exchange.time = previous_clock
            shell_exchange.os = previous_exchange_os
            if previous_observer_clock is not None:
                observer.time = previous_observer_clock
            if codec is not None:
                if previous_codec_clock is not None:
                    codec.time = previous_codec_clock
                if previous_codec_os is not None:
                    codec.os = previous_codec_os
        # The exchange may return immediately after its final DONE read.  A
        # final proxy check prevents that return from becoming a receipt after
        # either the logical window or durable BOOTTIME lease has elapsed.
        suspend_clock._check()
        if select.select([descriptor], [], [], 0)[0]:
            try:
                trailing = suspend_os.read(descriptor, 1)
            except BlockingIOError:
                trailing = b""
            if trailing:
                writer.write_stdout(trailing)
                audit = getattr(getattr(result, "session", None), "audit", None)
                if audit is not None:
                    audit.rx.extend(trailing)
                raise _live_error(live, "P348 trailing bytes after DONE")
        return result, observer
    except BaseException as exc:
        if not hasattr(exc, "audit"):
            result = locals().get("result")
            audit = getattr(getattr(result, "session", None), "audit", None)
            if audit is not None:
                exc.audit = audit
        raise
    finally:
        os.close(descriptor)


def _failure_value(
    live: Any,
    binding: Mapping[str, Any],
    intent: Mapping[str, Any],
    command: bytes,
    exc: BaseException,
    audit: Any | None,
    raw_tx: dict[str, Any] | None,
    raw_rx: dict[str, Any] | None,
) -> dict[str, Any]:
    rx = bytes(getattr(audit, "rx", b"")) if audit is not None else b""
    tx = bytes(getattr(audit, "tx", b"")) if audit is not None else b""
    return {
        "schema": SCHEMA,
        "action": ACTION_NAME,
        "ordinal": intent["ordinal"],
        "binding_sha256": session.digest(binding),
        "intent_sha256": session.digest(intent),
        "command": session.identity(command),
        "session_complete": False,
        "command_outcome": "uncertain",
        "continuation_allowed": False,
        "commands": [],
        "raw_tx": raw_tx or session.identity(tx),
        "raw_rx": raw_rx or session.identity(rx),
        "failure_stage": getattr(audit, "failure_stage", None) or getattr(audit, "current_stage", None),
        "error_type": type(exc).__name__,
        "error_sha256": hashlib.sha256(str(exc).encode("utf-8", "replace")).hexdigest(),
        "replay_authorized": False,
    }


def _run_locked(
    live: Any,
    prepared: Any,
    command: bytes,
    command_identity: Mapping[str, Any],
    *,
    cancel_requested: Callable[[], bool],
) -> dict[str, Any]:
    lease, binding, key, seen_nonces, _durable = _current_context(live, prepared)
    snapshot = lease.snapshot()
    if snapshot["rollback_required"]:
        raise _live_error(live, "P348 lease requires rollback")
    remaining = lease.lease["expires_elapsed_ns"] - session.clock_now_ns()
    if remaining < session.SESSION_WINDOW_NS:
        lease.expire()
        raise _live_error(live, "P348 lease has less than one session window remaining")
    variant = _variant(live)
    endpoint, endpoint_identity = _select_endpoint(live, prepared, binding)
    evidence = prepared.run_dir / EVIDENCE_DIRECTORY
    if not evidence.exists():
        _mkdir(evidence)
    ordinal = snapshot["actions_started"] + 1
    directory = evidence / f"action-{ordinal:02d}"
    _mkdir(directory)
    _udev_ok(live, endpoint, directory, "udev-before-intent")
    command_path = f"{EVIDENCE_DIRECTORY}/action-{ordinal:02d}/command.bin"
    _write_once(prepared.run_dir / command_path, command)
    intent = lease.begin_action(command_identity, binding, command_path=command_path)
    writer = None
    result = None
    observer = None
    raw_tx = raw_rx = None
    try:
        repeated, repeated_identity = _select_endpoint(live, prepared, binding)
        if repeated.identity_sha256 != endpoint.identity_sha256 or repeated_identity != endpoint_identity:
            raise _live_error(live, "P348 endpoint changed after command intent")
        _udev_ok(live, repeated, directory, "udev-after-intent")
        writer = raw_capture.RawCaptureWriter(
            directory,
            "session-rx",
            stdout_maximum=MAX_RAW_RX_BYTES,
            stderr_maximum=4096,
            argv0_name="tty-cdc-acm-p348-shell",
        )
        result, observer = _exchange_once(
            live,
            variant,
            repeated,
            repeated_identity,
            key,
            command,
            binding,
            seen_nonces,
            writer,
            lease.lease["expires_elapsed_ns"],
            lease,
            cancel_requested,
        )
        # BOOTTIME-MONOTONIC drift is a durable stop condition.  The shared
        # exchange has a monotonic logical I/O deadline, so revalidate the
        # lease clock before interpreting any command outcome.
        lease._check_clock(session.clock_now_ns())  # noqa: SLF001
        audit = getattr(getattr(result, "session", None), "audit", None)
        if audit is None:
            raise _live_error(live, "P348 exchange audit is absent")
        handle = writer.finalize(returncode=0)
        captured_rx = raw_capture.read_stdout(handle, maximum=MAX_RAW_RX_BYTES)
        if captured_rx != bytes(audit.rx):
            raise _live_error(live, "P348 raw-first RX differs from exchange audit")
        raw_rx = _write_once(directory / "session.rx.bin", bytes(audit.rx))
        raw_tx = _write_once(directory / "session.tx.bin", bytes(audit.tx))
        _write_once(directory / "selected.stdout.bin", bytes(result.session.commands[1].output))
        value = _session_receipt(live, variant, command, binding, intent, result, raw_tx, raw_rx, handle)
        # Retain exact command bytes and frame streams before JSON parsing or
        # lease-result publication.  The close reader reparses these streams.
        receipt = _write_json(directory / "result.json", value)
        status = "completed" if value["continuation_allowed"] is True else "failed"
        lease.record_action_result(
            intent,
            {
                "status": status,
                "command": value["command"],
                "session_complete": value["session_complete"],
                "command_outcome": value["command_outcome"],
                "continuation_allowed": value["continuation_allowed"],
                "receipt_bytes": receipt["size"],
                "receipt_sha256": receipt["sha256"],
            },
            binding,
        )
        final = session.ShellLease.open(prepared.run_dir / session.DIRECTORY).snapshot()
        response = {
            "schema": RUN_SCHEMA,
            "verdict": "PASS_P348_RETAINED_SHELL_ACTION" if value["continuation_allowed"] else "STOP_P348_RETAINED_SHELL_ACTION",
            "action": ACTION_NAME,
            "ordinal": intent["ordinal"],
            "command": value["command"],
            "session_complete": value["session_complete"],
            "command_outcome": value["command_outcome"],
            "continuation_allowed": value["continuation_allowed"],
            "selected_output": value["selected_output"],
            "result": receipt,
            "lease": final,
            "device_contact": True,
            "read_only": True,
            "caller_selected_command": True,
            "replay_authorized": False,
            "rollback_required": final["rollback_required"],
        }
        return response
    except BaseException as exc:
        audit = getattr(exc, "audit", None)
        if audit is None and result is not None:
            audit = getattr(getattr(result, "session", None), "audit", None)
        retention_errors: list[str] = []
        if writer is not None and not writer.finished:
            try:
                handle = writer.finalize(returncode=None, producer_error_type=type(exc).__name__)
                captured = raw_capture.read_stdout(handle, maximum=MAX_RAW_RX_BYTES)
                raw_rx = _write_once(directory / "failure.rx.bin", captured)
            except Exception as retention_error:
                retention_errors.append(type(retention_error).__name__)
        if raw_rx is None:
            try:
                raw_rx = _write_once(directory / "failure.rx.bin", bytes(getattr(audit, "rx", b"")))
            except Exception as retention_error:
                retention_errors.append(type(retention_error).__name__)
        if raw_tx is None:
            try:
                raw_tx = _write_once(directory / "failure.tx.bin", bytes(getattr(audit, "tx", b"")))
            except Exception as retention_error:
                retention_errors.append(type(retention_error).__name__)
        failure = _failure_value(live, binding, intent, command, exc, audit, raw_tx, raw_rx)
        failure["retention_errors"] = retention_errors
        try:
            receipt = _write_json(directory / "failure.json", failure)
            lease.record_action_result(
                intent,
                {
                    "status": "uncertain",
                    "command": failure["command"],
                    "session_complete": False,
                    "command_outcome": "uncertain",
                    "continuation_allowed": False,
                    "receipt_bytes": receipt["size"],
                    "receipt_sha256": receipt["sha256"],
                },
                binding,
            )
        except Exception as publication_error:
            retention_errors.append(type(publication_error).__name__)
        if isinstance(exc, ActionError):
            raise
        raise _live_error(live, "P348 action uncertain; only exact rollback may follow", exc)


def run_action(
    live: Any,
    prepared: Any,
    command_file: Path | str,
    *,
    cancel_requested: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Execute one caller-command action under the exact retained lease."""

    command, command_identity = read_command_file(prepared, command_file)
    callback = cancel_requested or (lambda: False)
    if not callable(callback):
        raise ActionError("P348 cancel callback is not callable")
    with _cancel_owner(callback) as owner_cancel:
        with _locks(live, prepared):
            return _run_locked(
                live,
                prepared,
                command,
                command_identity,
                cancel_requested=owner_cancel,
            )


def status(live: Any, prepared: Any) -> dict[str, Any]:
    """Host-only status; it never opens a device endpoint."""

    return session.ShellLease.open(prepared.run_dir / session.DIRECTORY).snapshot()


__all__ = [
    "ACTION_NAME", "ActionError", "EVIDENCE_DIRECTORY", "MAX_COMMAND_BYTES", "MAX_OUTPUT_BYTES",
    "RUN_SCHEMA", "SCHEMA", "read_command_file", "run_action", "status",
]
