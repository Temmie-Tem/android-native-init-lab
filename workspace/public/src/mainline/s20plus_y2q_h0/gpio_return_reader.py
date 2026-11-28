"""Decode bounded run-wide GPIO milestones and exact signed TLMM callback results."""
import hashlib
from pathlib import Path
import re
import shlex
import sys
import types

HERE = Path(__file__).resolve().parent
FILTER = HERE / "gpio-return-filter.awk"
STAGES = ("fixed_anchor",)
# Two sets of at most 4 * 256 distinct 16-bit values plus decimal summary.
MAX_STDOUT = 8288


def retained(name, pin):
    path = HERE / name
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != pin:
        raise ValueError("changed GPIO reader dependency: " + name)
    return raw


def module(name, pin):
    result = types.ModuleType(Path(name).stem)
    result.__file__ = str(HERE / name)
    exec(compile(retained(name, pin), result.__file__, "exec"), result.__dict__)
    return result


legacy = module("tlmm_return_reader.py", "62c24c00c5e09bb2baecfb3ad58267b9c5f1feba0a9e09dc970c751229c5296d")
# The offline GPIO schema imports the earlier schema by its public name.
previous = sys.modules.get("tlmm_flush_h0")
try:
    sys.modules["tlmm_flush_h0"] = legacy.offline
    offline = module("tlmm_gpio_h0.py", "9a4a8a2759f17c1150b66cd13ef95156cfc54f0b8e23522eb5261be195ef18a9")
finally:
    if previous is None:
        del sys.modules["tlmm_flush_h0"]
    else:
        sys.modules["tlmm_flush_h0"] = previous
frames = offline.frames


def program():
    common = retained("tlmm-return-filter.awk", "9c7c65e8aef2604e802f82927535e96a5291df7b5e0991761251869515628410").decode("ascii")
    crypto = common[:common.index("# Presence across authenticated slots")]
    input_loop = common[common.index("BEGIN {reserved_zeros"):common.index("END {")]
    return (crypto + FILTER.read_text("ascii") + input_loop +
            "END { if(bad || total!=expected)exit 3; if(!invalid)flush(1); report() }\n")


def shell(nonce, boot):
    original = legacy.original
    script = original.shell(nonce, boot)
    first, second = original.frames(nonce).values()
    old = f"-v first={first.hex()} -v second={second.hex()} " + shlex.quote(original.FILTER.read_text("ascii"))
    if script.count(old) != 1:
        raise ValueError("stock scan template changed")
    return script.replace(old, f"-v key={nonce} " + shlex.quote(program()))


def return_values(field, slots, mask):
    if len(field) % 4 or len(field) > 4 * slots or bool(field) != bool(mask & 8192):
        raise ValueError("inconsistent GPIO callback count")
    unsigned = [int(field[i:i+4], 16) for i in range(0, len(field), 4)]
    if len(set(unsigned)) != len(unsigned):
        raise ValueError("duplicate callback value")
    return sorted(x if x < 32768 else x - 65536 for x in unsigned)


def parse(rc, out, err):
    if rc or err or len(out) > MAX_STDOUT:
        raise ValueError("incomplete GPIO return")
    statuses = {b"GP2,invalid\n": "invalid_snapshot", b"y2q_log_missing\n": "missing",
                b"y2q_log_unreadable\n": "unreadable"}
    if out in statuses:
        return {"state": statuses[out]}
    if not re.fullmatch(rb"GP2(?:,(?:0|[1-9][0-9]{0,7})){10},[0-9a-f]*,[0-9a-f]*\n", out):
        raise ValueError("unrecognized GPIO summary")
    fields = out[:-1].split(b",")
    size, windows, slots, ignored, initial, worker, flags, wait, yes, no = map(int, fields[1:11])
    if not (240 * windows <= size <= 2097136 and windows <= 256 and slots + ignored <= 4 * windows
            and max(initial, worker) < 1 << len(offline.EVENTS) and flags < 1 << len(offline.FLUSH)
            and (slots or not (initial or worker or flags)) and max(wait, yes, no) <= 1
            and (not wait or flags & 59 == 59) and (not yes or (wait and flags & 187 == 187))
            and (not no or flags & 71 == 71)):
        raise ValueError("inconsistent GPIO summary")
    if slots == 1 and ((flags & offline.BARRIER_PATH and flags & offline.IDLE_PATH)
                       or (wait, yes, no) != tuple(int(flags & path == path) for path in (59, 187, 71))):
        raise ValueError("single GPIO slot contradicts its path witnesses")
    def events(mask, labels):
        return [name for i, name in enumerate(labels) if mask & (1 << i)]
    return dict(state="complete" if windows else ("no_record" if size >= 240 else "insufficient_bytes"),
                size=size, windows=windows, slots=slots, ignored=ignored,
                initial=events(initial, offline.EVENTS), worker=events(worker, offline.EVENTS),
                flush=events(flags, offline.FLUSH), initial_callback_rc=return_values(fields[11], slots, initial),
                worker_callback_rc=return_values(fields[12], slots, worker), wait_completed=bool(wait),
                flush_returned_true=bool(yes), flush_returned_false=bool(no))
