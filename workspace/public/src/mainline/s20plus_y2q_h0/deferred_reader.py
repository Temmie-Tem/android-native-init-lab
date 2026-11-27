"""Decode y2q's two independent producers from an original Magisk return."""
import base64
import hashlib
import importlib.util
from pathlib import Path
import re
import shlex
import struct

HERE = Path(__file__).resolve().parent
_LEGACY = HERE / "consolidated_reader.py"
_spec = importlib.util.spec_from_file_location("_y2q_deferred_legacy", _LEGACY)
legacy = importlib.util.module_from_spec(_spec)
exec(compile(_LEGACY.read_bytes(), str(_LEGACY), "exec"), legacy.__dict__)

FILTER = HERE / "deferred-filter.awk"
STAGES = ("run_anchor",)
MILESTONES = legacy.MILESTONES
CAPACITY = legacy.CAPACITY
NUMBER = rb"(0|[1-9][0-9]{0,6})"
SAMPLE = rb"(-|[A-Za-z0-9_-]{27})"
RESPONSE = re.compile(b"R4," + b",".join([NUMBER] * 4 + [SAMPLE] * 2) + b"\n")


def frames(nonce):
    legacy.frames(nonce)  # Validate the fixed-width build identity.
    key = bytes.fromhex(nonce)
    body = b"H0UNATR3" + key + b"RUN-LEVEL-ONLY!!" + bytes(24)
    return {"run_anchor": body + hashlib.blake2s(body, key=key, digest_size=16).digest()}


def shell(nonce, boot):
    command = legacy.shell(nonce, boot)
    anchor = legacy.frames(nonce)["basic_enter"].hex()
    old = f"-v anchor={anchor} -v tag={legacy.DOMAIN.hex()}{nonce} " + shlex.quote(legacy.FILTER.read_text("ascii"))
    if command.count(old) != 1:
        raise ValueError("stock Android bracket differs")
    return command.replace(old, f"-v key={nonce} -v legacy={anchor} " + shlex.quote(FILTER.read_text("ascii")))


def sample(token, worker):
    if token == b"-":
        return None
    raw = base64.urlsafe_b64decode(token + b"=")
    if len(raw) != 20 or base64.urlsafe_b64encode(raw).rstrip(b"=") != token:
        raise ValueError("noncanonical progress sample")
    seq, current, returned, packed, ms = struct.unpack("<5I", raw)
    phase = packed >> 21
    if not 1 <= seq <= (128 if worker else 328):
        raise ValueError("producer counter outside the qualified budget")
    common = dict(sequence=seq, provider_flags=(packed >> 16) & 31,
                  command_db_rc=struct.unpack_from("<h", raw, 12)[0], boot_ms=ms)
    if worker:
        if phase not in (1, 2) or (phase == 2 and current != returned):
            raise ValueError("inconsistent deferred work sample")
        return dict(**common, device_id=f"{current:08x}", last_return_device_id=f"{returned:08x}",
                    operation="enter" if phase == 1 else "return")
    if max(current, returned) > 159 or phase >= 1 << len(MILESTONES):
        raise ValueError("invalid PID 1 milestone or initcall")
    return dict(**common, enter_plus_one=current, return_plus_one=returned, milestones=phase)


def parse(rc, out, err):
    if rc or err or len(out) > 96:
        raise ValueError("unclean first-return capture")
    if out in (b"y2q_log_missing\n", b"y2q_log_unreadable\n"):
        return {"state": out.decode().strip().removeprefix("y2q_log_")}
    if out.startswith(b"C1,"):
        legacy.parse(0, out, b"")
        return {"state": "format_mismatch"}
    m = RESPONSE.fullmatch(out)
    if m is None:
        raise ValueError("unexpected first-return format")
    size, epochs, runs, flags = map(int, m.groups()[:4])
    count = epochs + runs
    if flags == 128 and count == 0 and m[5] == m[6] == b"-" and 24 <= size <= CAPACITY:
        return {"state": "signature_limit", "size": size}
    if (size > CAPACITY or flags > 127 or count * 80 > size or
            (flags and size < 4) or (flags & 1 and size < 8) or
            (flags & (2 | 8 | 64) and size < 80) or (flags & 32 and count)):
        raise ValueError("inconsistent marker counts")
    pid, worker = sample(m[5], False), sample(m[6], True)
    if (pid or worker) and (count != 1 or flags & (8 | 16 | 64) or size < (200 if worker else 120)):
        raise ValueError("unbound samples")
    if flags & 16:
        state = "inconsistent_fields"
    elif flags & (8 | 64) and count:
        state = "mixed_format"
    elif count > 1:
        state = "multiple_windows"
    elif count:
        state = "epoch_window" if epochs else "run_window"
    elif flags & 8:
        state = "format_mismatch"
    elif flags & 64:
        state = "foreign_format"
    elif flags:
        state = "partial_or_invalid"
    elif size == 0:
        state = "empty_snapshot"
    else:
        state = "insufficient_bytes" if size < 24 else "no_record"
    return dict(state=state, size=size, epochs=epochs, run_windows=runs, flags=flags,
                pid_sample=pid, worker_sample=worker, recency="candidate_recency_unknown")


def describe(log, transfer_proved):
    """Producer-local positive evidence, with no ranking of boot attempts."""
    state = log["state"]
    usable = transfer_proved and state in ("epoch_window", "run_window")
    pid = log.get("pid_sample") if usable else None
    worker = log.get("worker_sample") if usable else None
    marks = [name for bit, name in enumerate(MILESTONES) if pid and pid["milestones"] & (1 << bit)]
    return dict(first_return=state, flags=log.get("flags"), snapshot_bytes=log.get("size"),
                cohort=("shared_epoch" if state == "epoch_window" else "individual_run_samples") if usable else None,
                last_candidate_attempt="unknown", pid_sample=pid, worker_sample=worker, milestones=marks,
                first_flush_return_observed="flush1_return" in marks, el0_getpid_entry_observed="el0_getpid" in marks)
