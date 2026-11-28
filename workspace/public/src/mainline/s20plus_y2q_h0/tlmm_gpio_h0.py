"""Offline reader for the y2q GPIO-registration candidate's 240-byte RAM records."""
import json
import struct
from pathlib import Path

from tlmm_flush_h0 import ATTEMPT as EARLY_EVENTS, FLUSH, digest

EVENTS = EARLY_EVENTS + ("gpio_add", "directions_begin", "directions_done", "of_done",
                         "irqchip_add", "irqchip_ok", "gpio_ok", "gpio_error", "drvdata_set")
RETURN = EVENTS.index("callback_return")
BARRIER_PATH = sum(1 << FLUSH.index(name) for name in
                   ("barrier", "before_wait", "after_wait", "returned_true"))
IDLE_PATH = sum(1 << FLUSH.index(name) for name in ("no_barrier", "returned_false"))


def frames(nonce):
    key = bytes.fromhex(nonce)
    if len(key) != 16:
        raise ValueError("expected a 16-byte candidate key")
    prefix = b"TLFIXED2" + key + b"RUN-LEVEL-ONLY!!" + bytes(24)
    return {"fixed_anchor": prefix + digest(prefix, key)}


def decode(window, nonce):
    key = bytes.fromhex(nonce)
    if (len(window) != 240 or len(key) != 16 or window[8:24] != key
            or window[:8] not in (b"TLFIXED2", b"TLEPOCH2") or window[40:64] != bytes(24)
            or digest(window[:64], key) != window[64:80]
            or (window[:8] == b"TLFIXED2" and window[:80] != frames(nonce)["fixed_anchor"])):
        raise ValueError("invalid GPIO candidate window")
    instance = digest(window[24:40], key)
    rows = []
    for index in range(4):
        slot = window[80 + 40 * index:120 + 40 * index]
        if (slot[:4] != (b"TLP2" if index < 2 else b"TLW2")
                or digest(slot[:24], instance) != slot[24:]):
            continue
        seq, initial, worker, flags, initial_rc, worker_rc = struct.unpack("<IIIIhh", slot[4:24])
        if (not 1 <= seq <= 32 or (seq - 1) % 2 != index % 2
                or (initial | worker) >> len(EVENTS) or flags >> len(FLUSH)
                or (flags & BARRIER_PATH and flags & IDLE_PATH)
                or (initial_rc and not initial & (1 << RETURN))
                or (worker_rc and not worker & (1 << RETURN))):
            raise ValueError("malformed authenticated GPIO slot")
        def names(value, labels):
            return [label for bit, label in enumerate(labels) if value & (1 << bit)]
        rows.append(dict(publisher="pid1" if index < 2 else "worker", sequence=seq,
                         initial=names(initial, EVENTS), worker=names(worker, EVENTS),
                         flush=names(flags, FLUSH),
                         initial_first_rc=initial_rc if initial & (1 << RETURN) else None,
                         worker_first_rc=worker_rc if worker & (1 << RETURN) else None))
    return rows


def outcomes(rows):
    """Each required path must fit in one authenticated slot, even across fixed windows."""
    wait = {"opened", "call", "barrier", "before_wait", "after_wait"}
    return dict(worker_callback_rc=sorted({row["worker_first_rc"] for row in rows
                                           if row["worker_first_rc"] is not None}),
                wait_completed=any(wait.issubset(row["flush"]) for row in rows),
                flush_returned_true=any((wait | {"returned_true"}).issubset(row["flush"])
                                        for row in rows))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("window", type=Path)
    parser.add_argument("nonce")
    args = parser.parse_args()
    if not args.window.is_file():
        parser.error("expected a saved 240-byte RAM window")
    with args.window.open("rb") as stream:
        rows = decode(stream.read(241), args.nonce)
    print(json.dumps(dict(slots=rows, **outcomes(rows)), indent=2))
