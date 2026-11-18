#!/usr/bin/env python3
"""Read one synthetic report via stock proxy marshalling and the stock CP reader.

The local pipe replaces Binder and the router-to-CP transport. The router's
write entry runs to mapMemory, and its close method runs to return. Fixture tags
cannot select this file reader in the real dispatcher. No device transport.
"""
import argparse
from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path
import select
import struct
import subprocess
import time

from elftools.elf.elffile import ELFFile

from build_fixture import DIGEST, START
from stock_hal import StockProxy, StockRouter, check

NAME = b"rfc/rfdevice_report.dat\0"
FIRST = bytes((255, 255, 0, len(NAME))) + NAME
LIMIT = 256 * 1024
COUNTERS = struct.Struct("<6I")


@dataclass
class Result:
    outcome: str
    content: bytes
    closed: bool
    opens: int
    reads: int
    closes: int
    unrelated_dropped: int


class Receiver:
    """One callback owner, one outstanding request, monotonically accumulated bytes."""
    def __init__(self):
        self.owner = object()
        self.contents = bytearray()
        self.total = None
        self.sequence = 0
        self.dropped = 0

    def receive(self, source, frame):
        if self.owner is None or source is not self.owner:
            self.dropped += 1
            return None
        if not self.contents and frame in (b"D", b"\xff\xff\x02"):
            return "DENIED" if frame == b"D" else "ABSENT"
        header_size = 11 if self.total is None else 7
        check(len(frame) >= header_size, "truncated reply")
        check(frame[:4] == bytes((255, 4, 0, self.sequence)), "unexpected transaction or sequence")
        if self.total is None:
            self.total, = struct.unpack_from("<I", frame, 5)
            check(self.total <= LIMIT, "file exceeds budget")
        chunk_size, = struct.unpack_from("<H", frame, header_size - 2)
        check(chunk_size <= 256 and len(frame) == header_size + chunk_size, "invalid chunk size")
        end = len(self.contents) + chunk_size
        check(end <= self.total and frame[4] == int(end < self.total), "size and EOF disagree")
        check(end == self.total or chunk_size > 0, "no progress")
        self.contents.extend(frame[header_size:])
        self.sequence = self.sequence % 255 + 1
        return "COMPLETE" if end == self.total else "MORE"


def read_exact(pipe, length, deadline):
    result = bytearray()
    while len(result) < length:
        wait = deadline - time.monotonic()
        if wait <= 0 or not select.select([pipe], [], [], wait)[0]:
            raise TimeoutError("fixture deadline")
        piece = os.read(pipe.fileno(), length - len(result))
        if not piece:
            raise EOFError("fixture ended during response")
        result.extend(piece)
    return bytes(result)


def read_report(proxy, router, guest, mode, size, fault=""):
    check(mode in (b"R", b"D", b"A") and 0 <= size <= LIMIT + 1, "fixture scenario")
    receiver = Receiver()
    opens = reads = closes = 0
    closed = False
    outcome = "INCOMPLETE"
    deadline = time.monotonic() + 30
    # Expose only QEMU, its host runtime and this fixture. No host device
    # tree, Binder endpoint, ADB socket or inherited network namespace.
    argv = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session",
            "--ro-bind", "/usr", "/usr", "--symlink", "usr/lib", "/lib",
            "--symlink", "usr/lib64", "/lib64", "--dev", "/dev", "--tmpfs", "/tmp",
            "--ro-bind", str(guest.resolve()), "/reader", "--", "/usr/bin/qemu-hexagon", "/reader"]
    with subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0) as cp:
        try:
            proxy.call("open")
            cp.stdin.write(mode + struct.pack("<I", size))
            request = FIRST
            while True:
                check(time.monotonic() < deadline, "fixture deadline")
                outbound = router.map_write(proxy.call("write", request))
                cp.stdin.write(struct.pack("<I", len(outbound)) + outbound)
                stats = read_exact(cp.stdout, COUNTERS.size, deadline)
                length, opens, reads, closes, held, checks = COUNTERS.unpack(stats)
                check(checks == 1 and 0 < length <= 320, "unbound guest response")
                body = read_exact(cp.stdout, length, deadline)
                if fault == "foreign" and reads == 1:
                    receiver.receive(object(), proxy.call("callback", b"unrelated"))
                if fault == "timeout" and reads == 1:
                    # Withhold this callback and exercise the actual expired wait.
                    read_exact(cp.stdout, 1, time.monotonic())
                if fault == "truncated" and reads == 2:
                    body = body[:-1]
                outcome = receiver.receive(receiver.owner, proxy.call("callback", body))
                if outcome == "MORE":
                    check((opens, closes, held) == (1, 0, 1), "file ownership changed")
                    request = bytes((255, 255, receiver.sequence))
                    continue
                check(not held and opens == closes, "unreleased file")
                cp.stdin.write(struct.pack("<I", 0))
                cp.stdin.close()
                check(cp.wait(timeout=max(0, deadline-time.monotonic())) == 0, "guest exit")
                if fault == "lost_close":
                    break
                proxy.call("close")
                router.close()
                # Dropping this in-process observer proves only fixture teardown.
                # The stock server's close method never accesses its receiver.
                receiver.owner = None
                closed = time.monotonic() <= deadline
                break
        except (EOFError, TimeoutError, subprocess.TimeoutExpired, ValueError) as exc:
            outcome = f"INCOMPLETE ({exc})"
        finally:
            if cp.poll() is None:
                cp.kill()
                cp.wait()
    return Result(outcome, bytes(receiver.contents), closed, opens, reads, closes, receiver.dropped)


def exercise(elf, router_elf, guest):
    guest_elf = ELFFile(io.BytesIO(guest.read_bytes()))
    section = guest_elf.get_section_by_name(".reader")
    check(section is not None and section["sh_addr"] == START and
          hashlib.sha256(section.data()).hexdigest() == DIGEST, "wrong linked CP reader")
    proxy, router = StockProxy(elf), StockRouter(router_elf)
    cases = [("empty", b"R", 0, ""), ("exact_chunk", b"R", 256, ""),
             ("multi_chunk", b"R", 513, ""), ("max_size", b"R", LIMIT, ""),
             ("absent", b"A", 0, ""), ("denied", b"D", 0, ""),
             ("foreign", b"R", 257, "foreign"), ("truncated", b"R", 513, "truncated"),
             ("timeout", b"R", 257, "timeout"), ("lost_close", b"R", 10, "lost_close"),
             ("oversize", b"R", LIMIT+1, "")]
    results = {}
    for title, mode, size, fault in cases:
        r = read_report(proxy, router, guest, mode, size, fault)
        expected = {"absent": "ABSENT", "denied": "DENIED",
                    "truncated": "INCOMPLETE (invalid chunk size)",
                    "timeout": "INCOMPLETE (fixture deadline)",
                    "oversize": "INCOMPLETE (file exceeds budget)"}.get(title, "COMPLETE")
        check(r.outcome == expected, f"{title}: {r.outcome}, expected {expected}")
        expected_closed = not expected.startswith("INCOMPLETE") and fault != "lost_close"
        check(r.closed == expected_closed, f"{title}: closure")
        accepted = size if expected == "COMPLETE" else 0
        if title == "truncated":
            accepted = 256
        check(r.content == bytes(i % 251 for i in range(accepted)), f"{title}: content")
        check(r.unrelated_dropped == int(title == "foreign"), f"{title}: callback ownership")
        if mode == b"R" and expected == "COMPLETE":
            check((r.opens, r.reads, r.closes) == (1, max(1, (size+255)//256), 1), title)
        if mode != b"R":
            check((r.opens, r.reads, r.closes) == (0, 0, 0), title)
        results[title] = {"outcome": r.outcome, "bytes": len(r.content), "fixture_closed": r.closed,
                          "opens": r.opens, "reads": r.reads, "closes": r.closes,
                          "sha256": hashlib.sha256(r.content).hexdigest(),
                          "unrelated_dropped": r.unrelated_dropped}
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock_hal", type=Path)
    parser.add_argument("stock_router", type=Path)
    parser.add_argument("efs_fixture", type=Path)
    args = parser.parse_args()
    print(json.dumps(exercise(args.stock_hal, args.stock_router, args.efs_fixture), indent=2))
