"""Encode the y2q setup milestones and interpret the bounded first-return scan."""
import base64
import hashlib
import importlib.util
from pathlib import Path
import re
import shlex

HERE = Path(__file__).resolve().parent
FILTER = HERE / "basic-setup-stage-filter.awk"
STAGES = ("dt_ready", "basic_enter", "basic_return")
WIDTH = 80
CAPACITY = 2097136
BASE = HERE / "mainline-handoff/return_stage.py"


def token(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=")


def frames(nonce):
    if not re.fullmatch(r"[0-9a-f]{32}", nonce):
        raise ValueError("invalid setup trial nonce")
    records = {}
    for name, tag in zip(STAGES, b"ABC", strict=True):
        prefix = b"Y2QBS1|" + bytes([tag]) + b"|" + token(bytes.fromhex(nonce)) + b"|"
        records[name] = (prefix + token(hashlib.sha256(prefix).digest())).ljust(WIDTH - 1, b".") + b"\n"
    return records


def shell(nonce, boot):
    raw = BASE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != "1fc37c9a3bcf1b1cc6410628a766ad8b5b0f15db9104bc4f3327a6a07ef2f8e5":
        raise ValueError("restored-Android scan template changed")
    spec = importlib.util.spec_from_file_location("_basic_stock_bracket", BASE)
    retained = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(BASE), "exec"), retained.__dict__)
    script = retained.shell(nonce, boot)
    prior = list(retained.frames(nonce).values())
    current = list(frames(nonce).values())
    old_args = f"-v first={prior[0].hex()} -v second={prior[1].hex()} "
    new_args = f"-v first={current[0].hex()} -v second={current[1].hex()} -v third={current[2].hex()} "
    old = old_args + shlex.quote(retained.FILTER.read_text("ascii"))
    if script.count(old) != 1:
        raise ValueError("unexpected return scan command")
    return script.replace(old, new_args + shlex.quote(FILTER.read_text("ascii")))


def parse(rc, out, err):
    if rc or err or len(out) > 96:
        raise ValueError("incomplete setup scan")
    if out in (b"y2q_log_missing\n", b"y2q_log_unreadable\n"):
        return {"state": out.decode().strip().removeprefix("y2q_log_")}
    number = rb"(0|[1-9][0-9]{0,6})"
    match = re.fullmatch(rb"y2q_basic_v1=" + b",".join([number] * 7) + rb"\n", out)
    if not match:
        raise ValueError("invalid setup scan")
    size, a, b, c, ab, bc, abc = map(int, match.groups())
    if (size > CAPACITY or WIDTH * (a + b + c) > size or ab > min(a, b) or
            bc > min(b, c) or abc > min(ab, bc) or ab + bc - abc > b):
        raise ValueError("inconsistent setup frame counts")
    return dict(state="complete" if a or b or c else "no_record", size=size,
                dt_ready_count=a, basic_enter_count=b, basic_return_count=c,
                dt_enter_pair_count=ab, enter_return_pair_count=bc, triple_count=abc)
