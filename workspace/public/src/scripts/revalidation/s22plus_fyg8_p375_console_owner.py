"""Finite operator command plan for one already-running P375 console.

This module never opens a device, listener, or transport.  The F1 observer
passes the one authenticated Session it already owns.  An absent plan means
qualification-only; it does not create a standing or retained console.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import time
from typing import Any

import device_action_f1_v2 as core
import s22plus_root_console_v1 as wire

SCHEMA = "s22plus_fyg8_p375_root_console_plan_v1"
SEALED_NAME = "p375-root-console-plan.json"
MAX_PLAN_BYTES = 1024 * 1024
MAX_COMMANDS = 64
RETURN_RESERVE_SEC = 10.0


class ConsolePlanError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _decode_command(row: Any, ordinal: int) -> tuple[bytes, bytes, int]:
    fields = {"command_base64", "cwd", "timeout_ms"}
    if type(row) is not dict or set(row) != fields:
        raise ConsolePlanError(f"command {ordinal} fields differ")
    encoded, cwd, timeout = row["command_base64"], row["cwd"], row["timeout_ms"]
    if type(encoded) is not str or type(cwd) is not str or type(timeout) is not int:
        raise ConsolePlanError(f"command {ordinal} types differ")
    try:
        command = base64.b64decode(encoded, validate=True)
        cwd_bytes = cwd.encode("utf-8")
    except (ValueError, UnicodeError) as exc:
        raise ConsolePlanError(f"command {ordinal} encoding differs") from exc
    wire.command(command, cwd=cwd_bytes, timeout_ms=timeout)
    return command, cwd_bytes, timeout


def validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {"schema", "commands"}:
        raise ConsolePlanError("console plan fields differ")
    commands = value["commands"]
    if value["schema"] != SCHEMA or type(commands) is not list or len(commands) > MAX_COMMANDS:
        raise ConsolePlanError("console plan schema or command bound differs")
    for ordinal, row in enumerate(commands, 1):
        _decode_command(row, ordinal)
    if len(_canonical(value)) > MAX_PLAN_BYTES:
        raise ConsolePlanError("console plan exceeds byte bound")
    return value


def load(path: Path) -> dict[str, Any]:
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_uid != os.getuid() or not 0 < before.st_size <= MAX_PLAN_BYTES):
            raise ConsolePlanError("console plan metadata differs")
        raw = os.read(fd, MAX_PLAN_BYTES + 1)
        after = os.fstat(fd)
        if (len(raw) != before.st_size
                or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                    before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size,
                                            after.st_mtime_ns, after.st_ctime_ns)):
            raise ConsolePlanError("console plan changed while reading")
    finally:
        os.close(fd)
    try:
        value = json.loads(raw, object_pairs_hook=core._unique_object)
    except (UnicodeError, json.JSONDecodeError, core.F1V2Error) as exc:
        raise ConsolePlanError("console plan JSON differs") from exc
    validate(value)
    if raw != _canonical(value):
        raise ConsolePlanError("console plan is not canonical JSON")
    return value


def seal(source: Path | None, run_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    value = {"schema": SCHEMA, "commands": []} if source is None else load(source)
    path = Path(run_dir) / SEALED_NAME
    if path.exists() or path.is_symlink():
        existing = load(path)
        if existing != value:
            raise ConsolePlanError("sealed console plan differs; replay forbidden")
    else:
        raw = _canonical(value)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
                     0o400)
        try:
            used = 0
            while used < len(raw):
                amount = os.write(fd, raw[used:])
                if amount <= 0:
                    raise OSError("short console plan write")
                used += amount
            os.fsync(fd)
            os.fchmod(fd, 0o400)
        finally:
            os.close(fd)
        parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    raw = _canonical(value)
    return value, {"path": str(path), "size": len(raw),
                   "sha256": hashlib.sha256(raw).hexdigest(),
                   "command_count": len(value["commands"])}


def _terminal_outcome(terminal: list[int]) -> str:
    flags,status,error,_,_,_=terminal[1:]
    if flags & 16:return "setup-failure"
    if flags & 32:return "control-interrupted"
    if flags & 8:return "cleanup-incomplete"
    if flags & 2:return "timeout"
    if flags & 1:return "cancelled"
    if flags & 4:return "output-truncated"
    return "ok" if status == 0 and error == 0 else "command-failed"


def execution_projection(plan: dict[str, Any], command_rows: list[dict[str, Any]]) -> dict[str, Any]:
    validate(plan)
    if type(command_rows) is not list or len(command_rows) > len(plan["commands"]):
        raise ConsolePlanError("executed command count differs from sealed plan")
    results=[]
    for ordinal,row in enumerate(plan["commands"],1):
        command,cwd,timeout_ms=_decode_command(row,ordinal)
        result={"ordinal":ordinal,"command":_identity(command),"cwd":_identity(cwd),
            "timeout_ms":timeout_ms,"sequence":None,"accepted":False,"rejected":False,
            "terminal":None,"outcome":"not-executed"}
        if ordinal <= len(command_rows):
            actual=command_rows[ordinal-1]
            if (type(actual) is not dict or actual.get("command")!=result["command"]
                    or actual.get("cwd")!=result["cwd"]
                    or actual.get("timeout_ms")!=timeout_ms
                    or type(actual.get("sequence")) is not int
                    or type(actual.get("accepted")) is not bool
                    or type(actual.get("rejected")) is not bool):
                raise ConsolePlanError(f"command {ordinal} raw execution differs from sealed plan")
            terminal=actual.get("terminal")
            if terminal is not None and (type(terminal) is not list or len(terminal)!=7):
                raise ConsolePlanError(f"command {ordinal} terminal shape differs")
            result.update(sequence=actual["sequence"],accepted=actual["accepted"],
                rejected=actual["rejected"],terminal=terminal,
                outcome=_terminal_outcome(terminal) if terminal is not None
                    else "admission-rejected" if actual["rejected"] else "unresolved")
        results.append(result)
    terminal_count=sum(row["terminal"] is not None for row in results)
    return {"schema":"s22plus_fyg8_p375_plan_execution_v1",
        "planned_command_count":len(results),"executed_request_count":len(command_rows),
        "terminal_command_count":terminal_count,
        "unexecuted_command_count":sum(row["sequence"] is None for row in results),
        "all_planned_terminal":terminal_count==len(results),"results":results}


def _identity(payload: bytes) -> dict[str, Any]:
    return {"size":len(payload),"sha256":hashlib.sha256(payload).hexdigest()}


def run(session: wire.Session, events: list[tuple[int, int, bytes]], deadline: float,
        plan: dict[str, Any]) -> None:
    validate(plan)

    def wait(kinds: tuple[int, ...], sequence: int) -> tuple[int, bytes]:
        while time.monotonic() < deadline:
            for seen_kind, seen_sequence, body in events:
                if seen_sequence == sequence and seen_kind in kinds:
                    return seen_kind,body
            events.extend(session.poll())
            time.sleep(0.001)
        raise TimeoutError("P375 command plan exceeded original session deadline")

    for ordinal, row in enumerate(plan["commands"], 1):
        command, cwd, timeout_ms = _decode_command(row, ordinal)
        if time.monotonic()+timeout_ms/1000+RETURN_RESERVE_SEC > deadline:
            break
        if (session.raw_count+wire.MAX_COMMAND_RX_BYTES
                +wire.CONTROL_RX_RESERVE_BYTES > wire.SESSION_RX_LIMIT):
            break
        sequence = session.send(wire.EXEC, wire.command(
            command, cwd=cwd, timeout_ms=timeout_ms))
        kind,body=wait((wire.ACK,wire.EXIT),sequence)
        if kind==wire.ACK:
            acknowledgement=struct.unpack("<8I",body)
            if acknowledgement[1] != 0:break
            _,body=wait((wire.EXIT,),sequence)
        terminal=list(struct.unpack("<7I",body))
        if terminal[0] != sequence:
            raise ConsolePlanError(f"command {ordinal} terminal identity differs")
        if terminal[1] & (16|8|32|64|128|256):break


def audit() -> dict[str, Any]:
    return {"schema": SCHEMA, "maximum_commands": MAX_COMMANDS,
            "maximum_plan_bytes": MAX_PLAN_BYTES, "transport_owner": False,
            "return_reserve_sec":RETURN_RESERVE_SEC,
            "aggregate_raw_maximum":wire.RAW_CAPTURE_MAXIMUM,
            "reconnect": False, "session_renewal": False,
            "command_allowlist": False, "device_contact": False,
            "live_authorized": False}
