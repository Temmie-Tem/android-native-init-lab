"""Bounded original-Android TLMM readback; fields describe run-wide presence."""
import hashlib
from pathlib import Path
import re
import shlex
import types

HERE = Path(__file__).resolve().parent
FILTER = HERE/"tlmm-return-filter.awk"
STAGES = ("fixed_anchor",)


def load(path, pin):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != pin:
        raise ValueError("changed TLMM return dependency")
    module = types.ModuleType(path.stem)
    module.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


offline = load(HERE/"tlmm_flush_h0.py", "a8a9332b64b7857288a5eb6aa0f869b5de2e0c5f9f0809306ff0ac2fe43e5236")
original = load(HERE/"mainline-handoff/return_stage.py", "1fc37c9a3bcf1b1cc6410628a766ad8b5b0f15db9104bc4f3327a6a07ef2f8e5")
frames = offline.frames


def shell(nonce, boot):
    script = original.shell(nonce, boot)
    a, b = original.frames(nonce).values()
    old = f"-v first={a.hex()} -v second={b.hex()} " + shlex.quote(original.FILTER.read_text("ascii"))
    if script.count(old) != 1:
        raise ValueError("original Android boot bracket changed")
    return script.replace(old, f"-v key={nonce} " + shlex.quote(FILTER.read_text("ascii")))


def parse(rc, out, err):
    if rc or err or len(out)>96:
        raise ValueError("incomplete TLMM return")
    statuses = {b"TL1,invalid\n":"invalid_snapshot", b"y2q_log_missing\n":"missing", b"y2q_log_unreadable\n":"unreadable"}
    if out in statuses:
        return {"state":statuses[out]}
    if not re.fullmatch(rb"TL1(?:,(?:0|[1-9][0-9]{0,6})){10}\n", out):
        raise ValueError("unrecognized TLMM summary")
    size, windows, slots, ignored, initial, worker, flush, irc, wrc, completed = map(int,out.strip().split(b",")[1:])
    if not (240*windows <= size <= 2097136 and windows <= 256 and slots+ignored <= 4*windows
            and initial <= 65535 and worker <= 65535 and flush <= 1023 and max(irc,wrc)<=7
            and bool(initial & 8192)==bool(irc) and bool(worker & 8192)==bool(wrc)
            and max(irc.bit_count(),wrc.bit_count())<=slots and (slots or not (initial or worker or flush))
            and completed in (0,1) and (not completed or flush & 187 == 187)):
        raise ValueError("inconsistent TLMM summary")
    def events(mask, names):
        return [name for i,name in enumerate(names) if mask & (1<<i)]
    state = "complete" if windows else ("no_record" if size>=240 else "insufficient_bytes")
    classes = ("zero","defer","other_error")
    return dict(state=state, size=size, windows=windows, slots=slots, ignored=ignored,
                initial=events(initial,offline.ATTEMPT), worker=events(worker,offline.ATTEMPT),
                flush=events(flush,offline.FLUSH), initial_rc_classes=events(irc,classes),
                worker_rc_classes=events(wrc,classes), completed_barrier_wait=bool(completed))
