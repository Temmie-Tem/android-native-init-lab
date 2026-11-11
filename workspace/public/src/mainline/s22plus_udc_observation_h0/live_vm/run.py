"""Boot one offline ARM64 USB fixture and validate the CDC-NCM client's wire bytes."""
import argparse
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from decode import project

SIZE = 2 * 1024**2
BASE = 0x800200000 - 0x40000000
VALID_MAGIC = 0x4D474F4C
CURSOR = SIZE - 16 + 0x1081
CASES = {"bad-magic": (0, CURSOR, 3), "short-cursor": (VALID_MAGIC, 127, 4),
         "readback": (VALID_MAGIC, CURSOR, 1)}


def tag(key, identity, kind, body):
    return hmac.digest(key, b"G0Q-MAINLINE-RAM-CANARY-v1" + identity + bytes([kind]) + body, "sha256")


def build_peer(directory, build, key, identity, challenge):
    # Addresses exist only in the isolated VM and its CDC-NCM client namespace.
    subnet = ipaddress.IPv4Network((0xC0000200, 30))
    net = {"device_ip": str(subnet[2]), "host_ip": str(subnet[1]), "netmask": str(subnet.netmask),
           "serial": identity.hex()[:20], "udc": "a600000.usb"}
    for name, begin in (("device_mac", 0), ("host_mac", 5)):
        net[name] = (bytes([2]) + identity[begin:begin + 5]).hex(":")
    with (directory / "seal.h").open("x") as out:
        print("#define CANARY_PORT 47649", file=out)
        for name, value in (("key", key), ("id", identity)):
            print(f"static const unsigned char canary_{name}[] = {{" + ",".join(map(str, value)) + "};", file=out)
        for name, value in net.items():
            print(f"static const char canary_{name}[] = {json.dumps(value)};", file=out)
    binary = directory / "peer"
    subprocess.run(["aarch64-linux-gnu-gcc", "-std=c11", "-static", "-Os", "-Wall", "-Wextra",
                    "-Werror", "-Wno-unused-function", "-I", directory, HERE / "peer.c", "-o", binary], check=True)
    elf = subprocess.check_output(["file", binary], text=True)
    if "ARM aarch64" not in elf or "statically linked" not in elf:
        raise ValueError(elf)
    (directory / "file.txt").write_text(elf)
    (directory / "challenge").write_bytes(challenge)
    layout = [f"dir /{name} 0755 0 0" for name in ("dev", "proc", "sys", "config")]
    layout += ["nod /dev/ttyAMA0 0600 0 0 c 204 64", f"file /init {binary} 0755 0 0",
               f"file /challenge {directory / 'challenge'} 0400 0 0"]
    spec = directory / "init.list"
    spec.write_text("\n".join(layout) + "\n")
    with (directory / "init.cpio").open("xb") as archive:
        subprocess.run([build / "usr/gen_init_cpio", spec], stdout=archive, check=True)


def verify_frame(frame, key, identity, challenge, expected):
    if len(frame) != 140 or frame[:72] != b"UDCLIVE1" + identity + challenge[8:40]:
        raise ValueError("wrong response identity, length or nonce")
    if not hmac.compare_digest(tag(key, identity, 1, frame[:-32]), frame[-32:]):
        raise ValueError("invalid response HMAC")
    measured, state, count, bind_end, rc, attempt, reason, connect, received = struct.unpack_from("<IiIIiIIII", frame, 72)
    if not (0 < bind_end < measured <= connect < received < 120000 and 0 < attempt <= measured):
        raise ValueError("sample, bind, retained attempt or cable order")
    if (state, count, rc, reason) != (0, 1, 11, expected):
        raise ValueError(f"observed pre-connect state/bind count/bind rc/write reason: {state, count, rc, reason}")
    return dict(sample_ms=measured, udc="not attached", bind_end_ms=bind_end, bind_count=count,
                bind_rc=rc, publication_ms=attempt, publication_code=reason, before_connect_ms=connect,
                configured_response_ms=received)


def run(args):
    d = args.output.resolve()
    private = HERE.parents[4] / "private/outputs"
    if not d.is_relative_to(private.resolve()):
        raise ValueError("VM credentials and raw captures require private output")
    d.mkdir(mode=0o700, exist_ok=False)
    build = args.build.resolve()
    key, identity = secrets.token_bytes(32), secrets.token_bytes(32)
    body = b"G0QREQ1\0" + secrets.token_bytes(32)
    challenge = body + tag(key, identity, 0, body)
    (d / "peer.key").write_bytes(key)
    (d / "peer.id").write_bytes(identity)
    build_peer(d, build, key, identity, challenge)
    magic, cursor, expected = CASES[args.case]
    initial = struct.pack("<4I", 22, magic, cursor, 7901) + b"\xa5" * (SIZE - 16)
    ram = d / "guest.sparse"
    with ram.open("xb") as f:
        f.truncate(36 * 1024**3)
        f.seek(BASE)
        f.write(initial)
    cmd = [str(args.qemu), "-machine", "virt,memory-backend=ram,dtb-randomness=off", "-m", "36G",
           "-object", f"memory-backend-file,id=ram,size=36G,mem-path={ram},share=on,reserve=off,prealloc=off,dump=off",
           "-cpu", "cortex-a76", "-smp", "1", "-nodefaults", "-no-reboot", "-display", "none",
           "-monitor", "none", "-nic", "none", "-icount", "shift=5,sleep=off", "-serial", f"file:{d}/serial.log",
           "-dtb", str(args.dtb), "-kernel", str(build / "arch/arm64/boot/Image"), "-initrd", str(d / "init.cpio")]
    (d / "command.json").write_text(json.dumps(cmd, indent=2) + "\n")
    try:
        with (d / "qemu.log").open("xb") as log:
            proc = subprocess.Popen(cmd, stdout=log, stderr=log, stdin=subprocess.DEVNULL)
            try:
                until = time.monotonic() + 110
                while proc.poll() is None and time.monotonic() < until:
                    serial = d / "serial.log"
                    if serial.exists() and b"VM_FAIL" in serial.read_bytes():
                        raise RuntimeError(serial.read_text(errors="replace")[-500:])
                    time.sleep(0.1)
                if proc.poll() != 0:
                    raise RuntimeError(f"VM ended with {proc.poll()} or exceeded wall deadline")
            finally:
                if proc.poll() is None:
                    proc.kill()
                proc.wait()
        with ram.open("rb") as f:
            f.seek(BASE)
            region = f.read(SIZE)
    finally:
        ram.unlink(missing_ok=True)
    serial = (d / "serial.log").read_bytes()
    rows = re.findall(rb"^VM_NCM_RECEIVED ([0-9a-f]+)\r?$", serial, re.M)
    if len(rows) != 1 or b"VM_NCM_DONE" not in serial:
        raise ValueError("missing completed USB client capture")
    frame = bytes.fromhex(rows[0].decode())
    (d / "response.bin").write_bytes(frame)
    (d / "log-region.bin").write_bytes(region)
    result = verify_frame(frame, key, identity, challenge, expected)
    decoded = project(region[16:], args.candidate.read_bytes(), args.observation_key.read_bytes())
    if expected == 1:
        pos = 16 + (cursor % (SIZE - 16)) - 256
        if region[:pos] != initial[:pos] or region[pos+256:] != initial[pos+256:]:
            raise ValueError("write outside the retained slots")
        if decoded["damaged"] or decoded["foreign"] or not any(
                s["measured_ms"] == result["sample_ms"] and s["state"] == "not attached"
                for record in decoded["frames"] for s in record["samples"]):
            raise ValueError("verified live readback and independent slot evidence disagree")
    elif region != initial or decoded["frames"]:
        raise ValueError("rejected writer changed retained bytes")
    with (build / "arch/arm64/boot/Image").open("rb") as image:
        kernel_digest = hashlib.file_digest(image, "sha256").hexdigest()
    result.update(case=args.case, retained_bytes_changed=region != initial, retained_frames=len(decoded["frames"]),
                  kernel_sha256=kernel_digest,
                  response_sha256=hashlib.sha256(frame).hexdigest())
    (d / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=CASES)
    for name in ("output", "build", "qemu", "dtb", "candidate", "observation-key"):
        parser.add_argument("--" + name, type=Path, required=True)
    run(parser.parse_args())
