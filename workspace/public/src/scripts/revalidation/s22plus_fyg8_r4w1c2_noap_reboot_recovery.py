#!/usr/bin/env python3
"""One-shot no-AP reboot recovery for the consumed R4W1-C2 parse failure."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import selectors
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

import s22plus_fyg8_r4w1c2_measured_live_gate as measured
import s22plus_fyg8_r4w1c_connected_gate as connected
import s22plus_odin_transition_core as odin_core
import s22plus_boot_only_live_core as core


TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
SCRIPT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1c2_noap_reboot_recovery.py"
)
TEST_RELATIVE = Path("tests/test_s22plus_fyg8_r4w1c2_noap_reboot_recovery.py")
POLICY_BEGIN = "BEGIN_S22PLUS_FYG8_R4W1C2_NOAP_REBOOT_RECOVERY_POLICY_V1"
POLICY_END = "END_S22PLUS_FYG8_R4W1C2_NOAP_REBOOT_RECOVERY_POLICY_V1"
POLICY_STATE = "S22PLUS_FYG8_R4W1C2_NOAP_REBOOT_RECOVERY_POLICY_STATE=ACTIVE"
LIVE_ACK = "S22PLUS-FYG8-R4W1C2-NOAP-REBOOT-RECOVERY-LIVE"
PASS_VERDICT = "PASS_R4W1C2_NOAP_REBOOT_RECOVERY_EXACT_MAGISK_ANDROID"
FAIL_VERDICT = "FAIL_R4W1C2_NOAP_REBOOT_RECOVERY_REQUIRED"

INCIDENT_RUN = Path(
    "workspace/private/runs/s22plus-r4w1c2-measured-live-20260720T164444Z"
)
RECOVERY_RUN_ROOT = Path("workspace/private/runs")
RECOVERY_STATE = Path(
    "workspace/private/state/"
    "s22plus_fyg8_r4w1c2_noap_reboot_recovery_consumed.json"
)

EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
PARSE_FAILURE_STDOUT = b"Reboot into normal mode\nFail parse /proc/self/fd/7\n"
PARSE_FAILURE_SHA256 = hashlib.sha256(PARSE_FAILURE_STDOUT).hexdigest()
ODIN_SUCCESS_LINES = (
    "Reboot into normal mode",
    "Setup Connection",
    "initializeConnection",
    "Receive PIT Info",
    "success getpit",
    "Upload Binaries",
    "Close Connection",
)
MAX_ODIN_OUTPUT = 1024 * 1024
UTC_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z"
)

PINNED_FILES: dict[str, tuple[Path, int, str]] = {
    "consumed": (
        measured.CONSUMED_STATE,
        2680,
        "64d15cb2fab8dc7ea5ca0b569832cc15c32c7623e05cfbe6a60924cbf02ec477",
    ),
    "live_result": (
        INCIDENT_RUN / "result-live.json",
        108695,
        "74aa8f0a03b033299b2af5a6c97d9cba819ce671b04666549be3da45b38d9728",
    ),
    "recovery_result": (
        INCIDENT_RUN / "result-recovery-attempt-01.json",
        190297,
        "aabf8323dd4d78451c3378f968a2bb1900625a6705cba2122cb261b9aaab5456",
    ),
    "stock_intent": (
        INCIDENT_RUN / measured.STOCK_CLEANUP_INTENT_NAME,
        1290,
        "50d48adc1ad9710628d5282978ca8f984e2d1478192ccec2b75185628363f23c",
    ),
    "candidate_log": (
        INCIDENT_RUN / "odin-candidate.json",
        462,
        "84523c1d488f51c936a1d62fa832b0640e30f92d8544cb5c41e1dc70cfbc4757",
    ),
    "magisk_log": (
        INCIDENT_RUN / "odin-magisk-attempt-01.json",
        468,
        "12eef1ec931c2052196ca64d5930a23fc25cbfceb19530565b36eefadeadcc1d",
    ),
    "stock_log": (
        INCIDENT_RUN / "odin-stock-attempt-01.json",
        466,
        "175794cbe076165a41e171e6c5af8defb4c36158e651926af1871c44f810585d",
    ),
    "transaction": (
        INCIDENT_RUN / "transaction.jsonl",
        6971,
        "2811364fada46d840e8787f8947491688df1f3065d6be75e670b0a923561e97b",
    ),
    "recovery_timeline": (
        INCIDENT_RUN / "recovery-attempt-01-timeline.json",
        536,
        "48226674518c975f3d9d866834222e6f4217593cffb25b0e6700d6308c7df239",
    ),
}

FAILED_LOGS = {
    "candidate_log": ("r4w1c-candidate", connected.EXPECTED_CANDIDATE_AP_SHA256),
    "magisk_log": (
        "r4w1c-magisk-rollback",
        connected.EXPECTED_MAGISK_AP_SHA256,
    ),
    "stock_log": ("r4w1c-stock-cleanup", connected.EXPECTED_STOCK_AP_SHA256),
}


class RecoveryError(RuntimeError):
    pass


class BoundedOdinError(RecoveryError):
    def __init__(self, message: str, stdout: bytes, stderr: bytes):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def stable_bytes(path: Path, *, maximum: int = 4 * 1024 * 1024) -> bytes:
    try:
        return core.read_stable_file(path, maximum=maximum)
    except (OSError, core.LiveCoreError) as exc:
        raise RecoveryError(f"pinned file is unavailable: {path}") from exc


def durable_create_bytes(path: Path, payload: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise RecoveryError(f"evidence already exists: {path}") from exc
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise RecoveryError(f"evidence write stalled: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)
    return {"path": str(path), "size": len(payload), "sha256": sha256_bytes(payload)}


def pinned_file(root: Path, key: str) -> tuple[Path, bytes]:
    relative, size, digest = PINNED_FILES[key]
    path = root / relative
    if path.is_symlink() or not path.is_file() or path.resolve() != path.absolute():
        raise RecoveryError(f"pinned incident file is missing or indirect: {relative}")
    payload = stable_bytes(path, maximum=max(size + 1, 4 * 1024 * 1024))
    if len(payload) != size or sha256_bytes(payload) != digest:
        raise RecoveryError(f"pinned incident file identity changed: {relative}")
    return path, payload


def parse_json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RecoveryError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise RecoveryError(f"{label} is not a JSON object")
    return value


def helper_identity(root: Path) -> dict[str, Any]:
    path = root / SCRIPT_RELATIVE
    return {"path": str(SCRIPT_RELATIVE), **core.hash_stable_file(path)}


def test_identity(root: Path) -> dict[str, Any]:
    path = root / TEST_RELATIVE
    return {"path": str(TEST_RELATIVE), **core.hash_stable_file(path)}


def extract_policy(text: str) -> str | None:
    start = text.find(POLICY_BEGIN)
    end = text.find(POLICY_END)
    if start < 0 and end < 0:
        return None
    if start < 0 or end < start or text.find(POLICY_BEGIN, start + 1) >= 0:
        raise RecoveryError("no-AP recovery policy markers are malformed")
    end += len(POLICY_END)
    if text.find(POLICY_END, end) >= 0:
        raise RecoveryError("duplicate no-AP recovery policy marker")
    return text[start:end]


def policy_status(root: Path) -> dict[str, Any]:
    text = stable_bytes(root / "AGENTS.md", maximum=2 * 1024 * 1024).decode("utf-8")
    clause = extract_policy(text)
    if clause is None:
        return {"active": False, "clause": None, "sha256": None}
    helper = helper_identity(root)
    test = test_identity(root)
    required = (
        POLICY_STATE,
        LIVE_ACK,
        helper["sha256"],
        test["sha256"],
        PINNED_FILES["consumed"][2],
        PINNED_FILES["stock_intent"][2],
        PARSE_FAILURE_SHA256,
        connected.EXPECTED_ODIN_SHA256,
    )
    if any(value not in clause for value in required):
        raise RecoveryError("active no-AP recovery policy does not bind exact inputs")
    return {
        "active": True,
        "clause": clause,
        "sha256": sha256_bytes(clause.encode("utf-8")),
    }


def validate_failed_log(value: dict[str, Any], *, label: str, ap_sha256: str) -> None:
    expected = {
        "label": label,
        "returncode": 1,
        "stdout_bytes": len(PARSE_FAILURE_STDOUT),
        "stderr_bytes": 0,
        "stdout_sha256": PARSE_FAILURE_SHA256,
        "stderr_sha256": EMPTY_SHA256,
        "odin_sha256": connected.EXPECTED_ODIN_SHA256,
        "ap_sha256": ap_sha256,
        "sealed_inputs": True,
    }
    if value != expected:
        raise RecoveryError(f"{label} is not the exact sealed-path parse failure")


def validate_incident(root: Path) -> dict[str, Any]:
    opened: dict[str, dict[str, Any]] = {}
    bindings: dict[str, dict[str, Any]] = {}
    for key, (relative, size, digest) in PINNED_FILES.items():
        path, payload = pinned_file(root, key)
        bindings[key] = {"path": str(relative), "size": size, "sha256": digest}
        if path.suffix == ".json":
            opened[key] = parse_json(payload, key)

    consumed = opened["consumed"]
    if (
        consumed.get("schema") != "s22plus_fyg8_r4w1c2_measured_consumed_v1"
        or consumed.get("target") != TARGET
        or consumed.get("run_dir") != str(INCIDENT_RUN)
        or consumed.get("usb_binding")
        != {
            "topology": "2-1.3",
            "serial_sha256": measured.android_serial_sha256("RFCT519XWGK"),
            "download_serial_state": measured.DOWNLOAD_USB_SERIAL_STATE,
        }
        or consumed.get("android_serial") != "RFCT519XWGK"
    ):
        raise RecoveryError("consumed incident binding is not exact")

    live_result = opened["live_result"]
    recovery_result = opened["recovery_result"]
    if (
        live_result.get("verdict")
        != "FAIL_R4W1C2_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED"
        or live_result.get("candidate_transfer_ok") is not False
        or live_result.get("candidate_transfer_error")
        != "r4w1c-candidate Odin flash failed rc=1"
        or recovery_result.get("verdict")
        != "FAIL_R4W1C2_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED"
        or recovery_result.get("error")
        != "r4w1c-stock-cleanup Odin flash failed rc=1"
        or recovery_result.get("rollback_ok") is not False
        or recovery_result.get("final_android") is not None
    ):
        raise RecoveryError("incident result contract does not describe failed rollback")

    for key, (label, ap_sha256) in FAILED_LOGS.items():
        validate_failed_log(opened[key], label=label, ap_sha256=ap_sha256)

    intent = opened["stock_intent"]
    if (
        intent.get("schema") != "s22plus_fyg8_r4w1c_stock_cleanup_intent_v1"
        or intent.get("target") != "stock"
        or intent.get("magisk_failure") != "definite-nonzero"
        or intent.get("stock_ap_sha256") != connected.EXPECTED_STOCK_AP_SHA256
        or intent.get("usb_binding", {}).get("topology") != "2-1.3"
        or intent.get("usb_binding", {}).get("serial_state") != "absent"
        or intent.get("ticket", {}).get("device_identity")
        != intent.get("usb_binding", {}).get("device_identity")
    ):
        raise RecoveryError("stock cleanup intent binding is not exact")

    transaction = stable_bytes(root / PINNED_FILES["transaction"][0])
    if b'"phase":"rollback_transfer_finished"' in transaction:
        raise RecoveryError("incident unexpectedly contains a completed rollback transfer")
    if PARSE_FAILURE_SHA256 != "7f6162459d49213e9d36485eaa1e7748492b484f4538db45ef50ab4d9f31adb4":
        raise RecoveryError("parse-failure preimage is not exact")

    return {
        "target": TARGET,
        "run_dir": str(INCIDENT_RUN),
        "android_serial": consumed["android_serial"],
        "usb_binding": consumed["usb_binding"],
        "parse_failure_stdout": {
            "bytes": len(PARSE_FAILURE_STDOUT),
            "sha256": PARSE_FAILURE_SHA256,
            "text": PARSE_FAILURE_STDOUT.decode("ascii").splitlines(),
            "meaning": "AP parse stopped before Setup Connection",
        },
        "files": bindings,
        "no_completed_transfer_receipt": True,
    }


def offline_check(root: Path) -> dict[str, Any]:
    incident = validate_incident(root)
    policy = policy_status(root)
    state_path = root / RECOVERY_STATE
    return {
        "schema": "s22plus_fyg8_r4w1c2_noap_reboot_recovery_offline_v1",
        "verdict": "PASS_R4W1C2_NOAP_REBOOT_RECOVERY_SOURCE_HOST_ONLY",
        "target": TARGET,
        "helper": helper_identity(root),
        "test": test_identity(root),
        "incident": incident,
        "policy": {key: value for key, value in policy.items() if key != "clause"},
        "recovery_consumed": state_path.exists() or state_path.is_symlink(),
        "device_contact": False,
        "device_writes": False,
        "reboot": False,
        "odin_transfer": False,
        "flash": False,
    }


def exact_timeline(started: str, reboot_start: str, reboot_done: str, ready: str) -> list[dict[str, str]]:
    return [
        {"name": "live_session_start", "timestamp_utc": started},
        {"name": "candidate_flash_start", "timestamp_utc": started},
        {"name": "candidate_flash_done", "timestamp_utc": started},
        {"name": "candidate_boot_ready", "timestamp_utc": started},
        {"name": "rollback_flash_start", "timestamp_utc": reboot_start},
        {"name": "rollback_flash_done", "timestamp_utc": reboot_done},
        {"name": "rollback_boot_ready", "timestamp_utc": ready},
        {"name": "live_session_end", "timestamp_utc": ready},
    ]


def validate_reboot_stdout(stdout: bytes, stderr: bytes, device: str) -> list[str]:
    if stderr:
        raise RecoveryError("no-AP Odin reboot produced stderr")
    try:
        text = stdout.decode("utf-8")
    except UnicodeError as exc:
        raise RecoveryError("no-AP Odin reboot stdout is not UTF-8") from exc
    lines = text.splitlines()
    if (
        not stdout
        or len(stdout) > MAX_ODIN_OUTPUT
        or device not in lines
        or any(required not in lines for required in ODIN_SUCCESS_LINES)
        or any("fail" in line.lower() for line in lines)
    ):
        raise RecoveryError("no-AP Odin reboot output lacks the exact success shape")
    positions = [lines.index(value) for value in ODIN_SUCCESS_LINES]
    if positions != sorted(positions):
        raise RecoveryError("no-AP Odin reboot success lines are out of order")
    return lines


def bounded_odin_runner(
    command: list[str],
    *,
    stdout: int,
    stderr: int,
    pass_fds: tuple[int, ...],
    timeout: float,
    check: bool,
) -> subprocess.CompletedProcess[bytes]:
    if stdout != subprocess.PIPE or stderr != subprocess.PIPE or check:
        raise RecoveryError("bounded Odin runner contract is invalid")
    if not math.isfinite(timeout) or timeout <= 0:
        raise RecoveryError("bounded Odin timeout is invalid")
    process: subprocess.Popen[bytes] | None = None
    selector: selectors.BaseSelector | None = None
    streams: dict[str, list[bytes]] = {"stdout": [], "stderr": []}
    total = 0
    deadline = time.monotonic() + timeout
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            pass_fds=pass_fds,
        )
        selector = selectors.DefaultSelector()
        assert process.stdout is not None
        assert process.stderr is not None
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise BoundedOdinError(
                    "no-AP Odin reboot timed out",
                    b"".join(streams["stdout"]),
                    b"".join(streams["stderr"]),
                )
            events = selector.select(remaining)
            if not events:
                raise BoundedOdinError(
                    "no-AP Odin reboot timed out",
                    b"".join(streams["stdout"]),
                    b"".join(streams["stderr"]),
                )
            for key, _mask in events:
                chunk = os.read(key.fd, 8192)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                total += len(chunk)
                streams[str(key.data)].append(chunk)
                if total > MAX_ODIN_OUTPUT:
                    raise BoundedOdinError(
                        "no-AP Odin reboot output exceeded its bound",
                        b"".join(streams["stdout"]),
                        b"".join(streams["stderr"]),
                    )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BoundedOdinError(
                "no-AP Odin reboot timed out",
                b"".join(streams["stdout"]),
                b"".join(streams["stderr"]),
            )
        returncode = process.wait(timeout=remaining)
        return subprocess.CompletedProcess(
            command,
            returncode,
            stdout=b"".join(streams["stdout"]),
            stderr=b"".join(streams["stderr"]),
        )
    except subprocess.TimeoutExpired as exc:
        raise BoundedOdinError(
            "no-AP Odin reboot timed out",
            b"".join(streams["stdout"]),
            b"".join(streams["stderr"]),
        ) from exc
    except BaseException:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        raise
    finally:
        if selector is not None:
            selector.close()
        if process is not None:
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()


def run_noap_odin(
    odin_fd: int,
    device: str,
    *,
    stdout_path: Path,
    stderr_path: Path,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = bounded_odin_runner,
) -> tuple[subprocess.CompletedProcess[bytes], list[str], list[str]]:
    command = [f"/proc/self/fd/{odin_fd}", "--reboot", "-d", device]
    forbidden = {"-a", "-b", "-c", "-s", "-u", "-e", "-V", "--redownload"}
    if any(argument in forbidden for argument in command):
        raise RecoveryError("no-AP reboot command contains a transfer option")
    try:
        completed = runner(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            pass_fds=(odin_fd,),
            timeout=60,
            check=False,
        )
        stdout = completed.stdout or b""
        stderr = completed.stderr or b""
    except (subprocess.TimeoutExpired, BoundedOdinError) as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        durable_create_bytes(stdout_path, stdout)
        durable_create_bytes(stderr_path, stderr)
        raise RecoveryError(str(exc)) from exc
    if len(stdout) + len(stderr) > MAX_ODIN_OUTPUT:
        raise RecoveryError("no-AP Odin reboot output exceeded its bound")
    durable_create_bytes(stdout_path, stdout)
    durable_create_bytes(stderr_path, stderr)
    if completed.returncode != 0:
        raise RecoveryError(f"no-AP Odin reboot failed rc={completed.returncode}")
    lines = validate_reboot_stdout(stdout, stderr, device)
    return completed, command, lines


def create_recovery_state(
    root: Path,
    *,
    policy: dict[str, Any],
    incident: dict[str, Any],
    run_dir: Path,
    ticket: odin_core.EndpointTicket,
    usb: dict[str, str],
) -> dict[str, Any]:
    path = root / RECOVERY_STATE
    if path.exists() or path.is_symlink():
        raise RecoveryError("no-AP reboot recovery was already consumed")
    record = {
        "schema": "s22plus_fyg8_r4w1c2_noap_reboot_recovery_consumed_v1",
        "created_at_utc": core.utc_now(),
        "target": TARGET,
        "ack": LIVE_ACK,
        "helper_sha256": helper_identity(root)["sha256"],
        "test_sha256": test_identity(root)["sha256"],
        "policy_clause_sha256": policy["sha256"],
        "incident_consumed_sha256": incident["files"]["consumed"]["sha256"],
        "stock_intent_sha256": incident["files"]["stock_intent"]["sha256"],
        "run_dir": str(run_dir.relative_to(root)),
        "ticket": measured._ticket_payload(ticket),
        "usb_binding": usb,
        "action": "odin4 --reboot only; no AP and no partition payload",
    }
    core.durable_create_json(path, record)
    return record


def live_run(root: Path, args: argparse.Namespace) -> int:
    offline = offline_check(root)
    policy = policy_status(root)
    if not policy["active"] or args.ack != LIVE_ACK:
        raise RecoveryError("no-AP reboot recovery policy or acknowledgement is inactive")
    if offline["recovery_consumed"]:
        raise RecoveryError("no-AP reboot recovery one-shot is already consumed")

    started = core.utc_now()
    run_dir = root / RECOVERY_RUN_ROOT / (
        "s22plus-r4w1c2-noap-reboot-recovery-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    )
    run_dir.mkdir(mode=0o700, parents=False, exist_ok=False)
    result_path = run_dir / "result.json"
    timeline_path = run_dir / "timeline.json"
    stdout_path = run_dir / "odin-reboot.stdout"
    stderr_path = run_dir / "odin-reboot.stderr"
    result: dict[str, Any] = {
        "schema": "s22plus_fyg8_r4w1c2_noap_reboot_recovery_live_v1",
        "target": TARGET,
        "mode": "no-ap-reboot-only",
        "verdict": "INCOMPLETE",
        "incident": offline["incident"],
        "device_writes": False,
        "partition_write": False,
        "odin_transfer": False,
        "flash": False,
        "reboot": False,
    }

    odin = (root / args.odin).resolve() if not args.odin.is_absolute() else args.odin
    try:
        with measured.pinned_odin_session(odin) as (odin_fd, external_odin):
            with odin_core.transaction_session(run_dir) as lease:
                ticket, sequence = measured.wait_for_endpoint(
                    external_odin,
                    run_dir,
                    timeout_sec=args.endpoint_wait_sec,
                    sequence=0,
                    lease=lease,
                    expected_usb_binding=dict(offline["incident"]["usb_binding"]),
                )
                usb = measured.require_ticket_usb_binding(
                    ticket, dict(offline["incident"]["usb_binding"])
                )
                if offline_check(root) != offline:
                    raise RecoveryError("host evidence changed before recovery consumption")
                state = create_recovery_state(
                    root,
                    policy=policy,
                    incident=offline["incident"],
                    run_dir=run_dir,
                    ticket=ticket,
                    usb=usb,
                )
                device, sequence, revalidation = measured.revalidate_ticket(
                    external_odin,
                    run_dir,
                    ticket,
                    sequence=sequence,
                    lease=lease,
                )
                if measured.require_ticket_usb_binding(
                    ticket, dict(offline["incident"]["usb_binding"])
                ) != usb:
                    raise RecoveryError("Download USB binding changed before reboot")
                reboot_start = core.utc_now()
                completed, command, lines = run_noap_odin(
                    odin_fd,
                    device,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                )
                reboot_done = core.utc_now()
                serial, android = measured.wait_magisk_android(
                    args.android_wait_sec,
                    expected_serial=str(offline["incident"]["android_serial"]),
                    expected_usb_binding=dict(offline["incident"]["usb_binding"]),
                )
                absence = odin_core.wait_for_no_live_endpoint(
                    external_odin,
                    run_dir,
                    timeout_sec=args.odin_absence_wait_sec,
                    sequence_start=sequence,
                    poll_sec=0.1,
                    lease=lease,
                    endpoint_observer_factory=odin_core.measured_usbfs_observer,
                )
                if not absence.absent or absence.timed_out:
                    raise RecoveryError("exact Android return retained an Odin endpoint")
                ready = core.utc_now()
                timeline = exact_timeline(started, reboot_start, reboot_done, ready)
                result.update(
                    {
                        "verdict": PASS_VERDICT,
                        "device_writes": False,
                        "partition_write": False,
                        "odin_transfer": False,
                        "flash": False,
                        "reboot": True,
                        "recovery_state": state,
                        "ticket": measured._ticket_payload(ticket),
                        "usb_binding": usb,
                        "endpoint_revalidation": revalidation,
                        "command_shape": ["<sealed-odin-fd>", "--reboot", "-d", device],
                        "command_argument_count": len(command),
                        "ap_argument_present": False,
                        "odin": {
                            "returncode": completed.returncode,
                            "stdout": {"path": str(stdout_path.relative_to(root)), **core.hash_stable_file(stdout_path)},
                            "stderr": {"path": str(stderr_path.relative_to(root)), **core.hash_stable_file(stderr_path)},
                            "lines": lines,
                        },
                        "android_serial": serial,
                        "final_android": android,
                        "no_odin_endpoint": True,
                        "timeline_phase_semantics": {
                            "candidate_flash_start": "zero-action recovery placeholder",
                            "candidate_flash_done": "zero-action recovery placeholder",
                            "candidate_boot_ready": "zero-action recovery placeholder",
                            "rollback_flash_start": "no-AP reboot command start; no flash",
                            "rollback_flash_done": "no-AP reboot command return; no flash",
                        },
                    }
                )
                core.durable_create_json(timeline_path, {"events": timeline})
                result["timeline"] = {
                    "path": str(timeline_path.relative_to(root)),
                    "events": timeline,
                }
                core.durable_create_json(result_path, result)
                print(json.dumps({"run_dir": str(run_dir), "verdict": PASS_VERDICT}, indent=2))
                return 0
    except (
        RecoveryError,
        measured.GateError,
        connected.GateError,
        odin_core.OdinTransitionError,
        core.LiveCoreError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        result["verdict"] = FAIL_VERDICT
        result["error"] = str(exc)
        result["recovery_consumed"] = (root / RECOVERY_STATE).exists()
        core.durable_create_json(result_path, result)
        print(json.dumps({"run_dir": str(run_dir), "verdict": FAIL_VERDICT}, indent=2))
        return 20


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline-check", action="store_true")
    modes.add_argument("--live", action="store_true")
    parser.add_argument("--ack")
    parser.add_argument("--odin", type=Path, default=connected.DEFAULT_ODIN)
    parser.add_argument("--endpoint-wait-sec", type=float, default=120.0)
    parser.add_argument("--android-wait-sec", type=float, default=300.0)
    parser.add_argument("--odin-absence-wait-sec", type=float, default=15.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    try:
        if args.offline_check:
            print(json.dumps(offline_check(root), indent=2, sort_keys=True))
            return 0
        return live_run(root, args)
    except (RecoveryError, measured.GateError, connected.GateError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
