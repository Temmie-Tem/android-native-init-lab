"""Generate the fixed PID1 return probe and decode its aggregate response."""
import hashlib
import importlib.util
from pathlib import Path
import re
import shlex

HERE = Path(__file__).resolve().parent
BASE = HERE / "mainline-handoff/return_stage.py"
FILTER = HERE / "pid1-stage-filter.awk"
STAGES = ("exec_attempt", "el0_getpid")
CAPACITY = 2097136


def frames(nonce):
    if not re.fullmatch(r"[0-9a-f]{32}", nonce):
        raise ValueError("invalid trial nonce")
    result = {}
    for name in STAGES:
        prefix = f"Y2QPID1|6.18|{name}|{nonce}|".encode("ascii")
        checksum = hashlib.sha256(prefix).hexdigest().encode("ascii")
        result[name] = (prefix + checksum).ljust(127, b".") + b"\n"
    if any(len(frame) != 128 for frame in result.values()):
        raise ValueError("invalid PID1 frame width")
    return result


def shell(nonce, boot):
    raw = BASE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != "1fc37c9a3bcf1b1cc6410628a766ad8b5b0f15db9104bc4f3327a6a07ef2f8e5":
        raise ValueError("stock boot bracket changed")
    spec = importlib.util.spec_from_file_location("_pid1_retained_bracket", BASE)
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(BASE), "exec"), module.__dict__)
    script = module.shell(nonce, boot)
    previous = module.frames(nonce)
    updated = frames(nonce)
    replacements = [(old.hex(), new.hex()) for old,new in zip(previous.values(),updated.values(),strict=True)]
    replacements.append((shlex.quote(module.FILTER.read_text("ascii")), shlex.quote(FILTER.read_text("ascii"))))
    for old, new in replacements:
        if script.count(old) != 1:
            raise ValueError("unexpected retained probe template")
        script = script.replace(old, new)
    return script


def parse(rc, out, err):
    if rc or err or len(out) > 96:
        raise ValueError("incomplete PID1 return scan")
    if out in (b"y2q_log_missing\n", b"y2q_log_unreadable\n"):
        return {"state": out.decode().strip().removeprefix("y2q_log_")}
    number = rb"(0|[1-9][0-9]{0,6})"
    match = re.fullmatch(rb"y2q_pid1_v1=" + b",".join([number]*4) + rb"\n", out)
    if not match:
        raise ValueError("invalid PID1 scan")
    size, first, second, pairs = map(int, match.groups())
    if size > CAPACITY or 128*(first+second) > size or pairs > min(first,second):
        raise ValueError("inconsistent PID1 counts")
    return dict(state="complete" if first or second else "no_record", size=size,
                exec_attempt_count=first, el0_getpid_count=second, adjacent_pair_count=pairs)
