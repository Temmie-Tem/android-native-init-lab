"""Bounded Magisk first-return reduction for the y2q cumulative boot witness."""
import base64
import hashlib
import importlib.util
from pathlib import Path
import re
import shlex

HERE = Path(__file__).resolve().parent
BASE = HERE / "mainline-handoff/return_stage.py"
FILTER = HERE / "consolidated-filter.awk"
CAPACITY = 2097136
STAGES = ("basic_enter",)
MILESTONES = ("basic_enter", "driver_ready", "flush1_enter", "flush1_return", "flush2_enter",
              "flush2_return", "basic_return", "initramfs_ready", "exec_attempt", "el0_getpid")
DOMAIN = b"Y2QSURV1"


def frames(nonce):
    if not re.fullmatch(r"[a-f0-9]{32}", nonce):
        raise ValueError("invalid candidate nonce")
    prefix = b"Y2QANCH1" + bytes.fromhex(nonce)
    return {"basic_enter": prefix + hashlib.sha256(prefix).digest() + b"." * 24}


def shell(nonce, boot):
    raw = BASE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != "1fc37c9a3bcf1b1cc6410628a766ad8b5b0f15db9104bc4f3327a6a07ef2f8e5":
        raise ValueError("changed original Android bracket")
    spec = importlib.util.spec_from_file_location("_consolidated_bracket", BASE)
    retained = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(BASE), "exec"), retained.__dict__)
    a, b = retained.frames(nonce).values()
    old = f"-v first={a.hex()} -v second={b.hex()} " + shlex.quote(retained.FILTER.read_text("ascii"))
    script = retained.shell(nonce, boot)
    if script.count(old) != 1:
        raise ValueError("original bracket command differs")
    args = f"-v anchor={frames(nonce)['basic_enter'].hex()} -v tag={DOMAIN.hex()}{nonce} "
    return script.replace(old, args + shlex.quote(FILTER.read_text("ascii")))


def describe(bitmap):
    if not re.fullmatch(r"[a-f0-9]{80}", bitmap):
        raise ValueError("invalid bit vector")
    bits = int.from_bytes(bytes.fromhex(bitmap), "little")
    if bits >> (306 + len(MILESTONES)):
        raise ValueError("unknown milestone bit")
    entered = [i for i in range(153) if bits & (1 << (2*i))]
    returned = [i for i in range(153) if bits & (2 << (2*i))]
    return dict(entry_count=len(entered), return_count=len(returned),
                highest_enter=max(entered, default=-1), highest_return=max(returned, default=-1),
                milestones=[name for i, name in enumerate(MILESTONES,306) if bits & (1 << i)])


def parse(rc, out, err):
    if rc or err or len(out) > 96:
        raise ValueError("incomplete consolidated evidence")
    if out in (b"y2q_log_missing\n", b"y2q_log_unreadable\n"):
        return {"state":out.decode().strip().removeprefix("y2q_log_")}
    number = rb"(0|[1-9][0-9]{0,6})"
    match = re.fullmatch(b"C1," + b",".join([number]*3) + rb",(-|[A-Za-z0-9_-]{54})\n",out)
    if not match:
        raise ValueError("invalid consolidated response")
    size, anchors, records = map(int,match.groups()[:3])
    token = match[4]
    if size > CAPACITY or (anchors+records)*80 > size or (records==0)!=(token==b"-"):
        raise ValueError("inconsistent scan")
    data = bytes(40) if not records else base64.urlsafe_b64decode(token+b"==")
    if records and (not any(data) or base64.urlsafe_b64encode(data).rstrip(b"=")!=token):
        raise ValueError("noncanonical vector")
    describe(data.hex())
    return dict(state="complete" if anchors or records else "no_record", size=size,
                anchor_count=anchors, record_count=records, bitmap=data.hex())
