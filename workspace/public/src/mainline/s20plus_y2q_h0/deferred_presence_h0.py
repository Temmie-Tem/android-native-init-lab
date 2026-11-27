"""Offline existential evidence from complete y2q R4 windows in one saved snapshot."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re

import deferred_reader as r4

ANCHORS = re.compile(b"H0UNATR3|H0EPOCH3")
WINDOW = 240
FLUSH_RETURN = 1 << r4.MILESTONES.index("flush1_return")


def digest(body, key):
    return hashlib.blake2s(body, key=key, digest_size=16).digest()


def presence(snapshot, nonce):
    """Sets contain directly recorded device IDs. Missing evidence stays unproved."""
    if len(snapshot) > r4.CAPACITY:
        raise ValueError("snapshot exceeds the R4 byte limit")
    expected = r4.frames(nonce)["run_anchor"]
    key = bytes.fromhex(nonce)
    if b"Y2QANCH1" in snapshot or b"Y2QSURV1" in snapshot:
        raise ValueError("legacy signature in snapshot")
    entered, returned = set(), set()
    flush = False
    count = ignored = end = 0
    for match in ANCHORS.finditer(snapshot):
        start = match.start()
        if count == 256 or start < end or start + WINDOW > len(snapshot):
            raise ValueError("oversubscribed, overlapping or incomplete R4 windows")
        end = start + WINDOW
        anchor = snapshot[start:start + 80]
        if (anchor[8:24] != key or anchor[40:64] != bytes(24)
                or digest(anchor[:64], key) != anchor[64:]
                or (match.group() == b"H0UNATR3" and anchor != expected)):
            raise ValueError("foreign or invalid R4 anchor")
        count += 1
        instance = digest(anchor[24:40], key)
        for slot in range(4):
            offset = start + 80 + 40 * slot
            frame = snapshot[offset:offset + 40]
            worker = slot >= 2
            if frame[:4] != (b"HLW2" if worker else b"HLP2"):
                continue
            if digest(frame[:24], instance) != frame[24:]:
                ignored += 1
                continue
            token = base64.urlsafe_b64encode(frame[4:24]).rstrip(b"=")
            sample = r4.sample(token, worker)
            if (sample["sequence"] - 1) % 2 != slot % 2:
                raise ValueError("authenticated slot parity mismatch")
            if worker:
                ids = entered if sample["operation"] == "enter" else returned
                ids.add(sample["device_id"])
            else:
                flush |= bool(sample["milestones"] & FLUSH_RETURN)
    return dict(valid_windows=count, unauthenticated_slots=ignored,
                before_bus_probe_device="observed" if entered else "unproved",
                before_call_device_ids=sorted(entered), return_device_ids=sorted(returned),
                first_flush_return="observed" if flush else "unproved")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("nonce")
    args = parser.parse_args()
    if not args.snapshot.is_file():
        parser.error("expected a saved snapshot file")
    with args.snapshot.open("rb") as stream:
        data = stream.read(r4.CAPACITY + 1)
    print(json.dumps(presence(data, args.nonce), sort_keys=True))
