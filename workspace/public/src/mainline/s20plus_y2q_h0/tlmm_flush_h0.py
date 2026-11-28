"""Decode the TLMM candidate's authenticated, independent RAM witnesses offline."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

ATTEMPT = ("supplier_pdc", "supplier_gic", "supplier_other", "link_defer", "link_allowed",
           "auto_request", "queue_inserted", "callback", "irq_ok", "irq_defer", "irq_error",
           "wake_found", "wake_missing", "callback_return", "before_bus", "after_bus")
FLUSH = ("opened", "call", "no_barrier", "barrier", "before_wait", "after_wait",
         "returned_false", "returned_true", "worker_exit", "pdc_published")


def digest(data, key):
    return hashlib.blake2s(data, key=key, digest_size=16).digest()


def frames(nonce):
    key = bytes.fromhex(nonce)
    if len(key) != 16:
        raise ValueError("invalid candidate nonce")
    prefix = b"TLFIXED1" + key + b"RUN-LEVEL-ONLY!!" + bytes(24)
    return {"fixed_anchor": prefix + digest(prefix, key)}


def decode(window, nonce):
    key = bytes.fromhex(nonce)
    anchor = window[:80]
    if (len(key) != 16 or len(window) != 240 or anchor[:8] not in (b"TLEPOCH1", b"TLFIXED1")
            or anchor[8:24] != key or anchor[40:64] != bytes(24)
            or (anchor[:8] == b"TLFIXED1" and anchor[24:40] != b"RUN-LEVEL-ONLY!!")
            or digest(anchor[:64], key) != anchor[64:]):
        raise ValueError("invalid candidate anchor or window")
    instance = digest(anchor[24:40], key)
    result = []
    for slot in range(4):
        frame = window[80 + slot*40:120 + slot*40]
        if frame[:4] != (b"TLP1" if slot < 2 else b"TLW1") or digest(frame[:24], instance) != frame[24:]:
            continue
        seq, initial, worker, flags, rc0, rc1 = struct.unpack("<IIIIhh", frame[4:24])
        if (not 1 <= seq <= 32 or (seq-1) % 2 != slot % 2 or (initial | worker) >> len(ATTEMPT)
                or flags >> len(FLUSH) or (rc0 and not initial & (1 << 13))
                or (rc1 and not worker & (1 << 13))):
            raise ValueError("invalid candidate slot")
        def events(value, names):
            return [name for i, name in enumerate(names) if value & (1 << i)]
        result.append(dict(publisher="pid1" if slot < 2 else "worker", sequence=seq,
                           initial=events(initial, ATTEMPT), worker=events(worker, ATTEMPT),
                           flush=events(flags, FLUSH), initial_first_rc=rc0 if initial & (1<<13) else None,
                           worker_first_rc=rc1 if worker & (1<<13) else None))
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("window", type=Path)
    p.add_argument("nonce")
    a = p.parse_args()
    if not a.window.is_file():
        p.error("expected a saved 240-byte window")
    with a.window.open("rb") as stream:
        print(json.dumps(decode(stream.read(241), a.nonce), indent=2))
