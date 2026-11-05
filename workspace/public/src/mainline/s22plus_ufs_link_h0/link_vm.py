"""Exercise ML030's compiled fixed-module receiver on an ARM64 virt guest."""
import argparse
import errno
import json
import os
from pathlib import Path
import secrets
import socket
import struct
import subprocess
import time
import uuid

import dwell_vm as base
import link_wire as wire
from link_initramfs import SCHEMA, PRIVATE, require, digest


def receive(sock, size, path):
    data = bytearray()
    with path.open("xb") as raw:
        while len(data) < size:
            chunk = sock.recv(size-len(data))
            require(chunk, "truncated frame: "+path.name)
            raw.write(chunk)
            data.extend(chunk)
    return bytes(data)


def test(kernel, init, out, case):
    kernel, init, out = (p.resolve() for p in (kernel,init,out))
    require(all(p.is_relative_to(PRIVATE.resolve()) for p in (kernel,init,out)), "private H0 inputs required")
    require(case in ("wrong-board","early","bad-permit"), "unknown VM case")
    out.mkdir(mode=0o700)
    runtime = json.loads((init/"result.json").read_bytes())
    image = json.loads((kernel/"guard-result.json").read_bytes())
    require(runtime["vm"] is True and runtime["debian_ram"]["schema"] == SCHEMA and
            image["status"] == "H0_ML030_TRANSPORT_KERNEL" and "retained_marker" not in image and
            digest(Path(image["image"])) == image["sha256"] and
            digest(Path(runtime["initramfs"]["path"])) == runtime["initramfs"]["sha256"], "wrong VM inputs")
    # ML030 shares only the first frame's layout, tag and readiness field
    # with the four-package Download observer. No historical qualification
    # or live task is used. The late frames have their own roles and checks.
    first_schema = dict(runtime,debian_ram=dict(runtime["debian_ram"],schema=base.verify.DOWNLOAD_SCHEMA))
    qroot = PRIVATE/"tools/qemu-arm64-10.2.1/root"
    serial = out/"serial.log"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1",0))
        port = listener.getsockname()[1]
    net = runtime["network"]
    import ipaddress
    prefix = ipaddress.IPv4Interface(net["device_ip"]+"/"+net["netmask"]).network
    args = [str(qroot/"usr/bin/qemu-system-aarch64"),"-machine","virt","-cpu","cortex-a76","-smp","1",
            "-m","768","-no-reboot","-display","none","-monitor","none","-serial","file:"+str(serial),
            "-kernel", image["image"], "-initrd", runtime["initramfs"]["path"],
            "-netdev", f'user,id=net0,net={prefix},host={net["host_ip"]},dhcpstart={net["device_ip"]},hostfwd=tcp:127.0.0.1:{port}-:47649',
            "-device","virtio-net-device,netdev=net0"]
    base.stored(out/"command.json",dict(argv=args,kernel=image["sha256"],archive=runtime["initramfs"],
                qemu_sha256=digest(Path(args[0])),case=case,device_actions=0))
    key = Path(runtime["key_path"]).read_bytes()
    identity = bytes.fromhex(runtime["candidate_id"])
    start = base.clock()
    with (out/"qemu.stderr").open("xb") as log:
        proc = subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=log,stdin=subprocess.DEVNULL,
                                env={**os.environ,"LD_LIBRARY_PATH":str(qroot/"usr/lib/x86_64-linux-gnu")})
        try:
            while not serial.exists() or b"G0Q_RAM_OBSERVER_READY" not in serial.read_bytes():
                require(proc.poll() is None and base.clock() < start+120_000_000_000,"initial observer window")
                time.sleep(.05)
            with socket.create_connection(("127.0.0.1",port),timeout=5) as client:
                client.settimeout(20)
                n0 = secrets.token_bytes(32)
                packet = base.verify.request(key,identity,n0,manifest=first_schema)
                base.persist(out/"first.request",packet)
                client.sendall(packet)
                prefix = receive(client,384,out/"first.prefix")
                length = struct.unpack_from("<I",prefix,248)[0]
                require(40<=length<=base.verify.FDT_LIMIT,"FDT length")
                dtb = receive(client,length,out/"first.dtb")
                base.persist(out/"first.response",prefix+dtb)
                proof = base.verify.verify(out/"first.response",first_schema,n0,vm=True)
                require(proof["download_ready"],"VM Download readiness")
                t0 = proof["uptime_ms"]
                boot = uuid.UUID(proof["boot_id"]).bytes
                anchored = base.clock()
                require(anchored<start+120_000_000_000,"first proof outside budget")
                base.stored(out/"first.json",dict(finished_ns=anchored,proof=proof))
                if case != "early":
                    while base.clock()<anchored+301_000_000_000:
                        time.sleep(min(1,max(0,(anchored+301_000_000_000-base.clock())/1e9)))
                n1 = secrets.token_bytes(32)
                issued = base.clock()
                query = wire.frame(b"G030ASK1",16,key,identity,n0,n1,boot,t0,0)
                base.persist(out/"late.request",query)
                client.sendall(query)
                t1 = None
                parsed = None
                if case!="early":
                    require(issued-anchored >= 300_000_000_000, "host gap")
                    reply = receive(client,wire.HEADER.size+32,out/"late.response")
                    t1 = wire.witness(reply,key,identity,n0,n1,boot,t0)
                    permit = wire.frame(b"G030GO01",18,key,identity,n0,n1,boot,t0,t1)
                    if case=="bad-permit":
                        permit = permit[:-1]+bytes([permit[-1]^1])
                    base.persist(out/"permit.intent",permit)
                    require(base.clock()<start+540_000_000_000,"expired permit")
                    client.sendall(permit)
                    if case=="wrong-board":
                        raw = receive(client,wire.RESULT_SIZE,out/"module.response")
                        parsed = wire.result(raw,reply,key,identity)
                        require(parsed==dict(status="NO_PROOF",load_errno=errno.ENODEV,read_errno=0,
                                             report_bytes=0,normal_return=False),"actual module did not reject virt")
                require(client.recv(1)==b"","unexpected extra bytes")
            require(proc.poll() is None and base.clock()<start+540_000_000_000,"observer window")
            for _ in range(40):
                if b"G0Q_RAM_PARK" in serial.read_bytes():
                    break
                time.sleep(.05)
            expected = {"wrong-board":errno.ENODEV, "early":errno.ETIMEDOUT, "bad-permit":errno.EACCES}
            lines = serial.read_bytes().splitlines()
            require([line for line in lines if line.startswith(b"G0Q_RAM_PARK")] ==
                    [f"G0Q_RAM_PARK error={expected[case]}".encode()] and
                    not any(b"G0Q_DOWNLOAD_RESTART2_PREPARED" in line for line in lines),
                    "negative must park with the selected errno and no Download")
            base.stored(out/"result.json",dict(status="PASS_H0_"+case.upper().replace("-","_"),first_ms=t0,
                        late_ms=t1,host_gap_s=(issued-anchored)/1e9,report=parsed,device_actions=0))
        except Exception as error:
            base.stored(out/"failure.json",dict(reason=str(error),device_actions=0))
            raise
        finally:
            proc.terminate()
            try: proc.wait(5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


if __name__=="__main__":
    os.umask(0o077)
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ("kernel","init","out"):
        cli.add_argument(name,type=Path)
    cli.add_argument("case",choices=("wrong-board","early","bad-permit"))
    args=cli.parse_args()
    test(args.kernel,args.init,args.out,args.case)
