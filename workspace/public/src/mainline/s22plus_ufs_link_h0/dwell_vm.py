"""Build and exercise ML030's non-deployable, same-boot Debian witness on QEMU."""
import argparse
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import socket
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
CANARY = HERE.parent / "s22plus_canary_h0"
sys.path.insert(0, str(CANARY))
import debian_ram
import verify
from prepare import require, digest
from vm import persist

BASE = ROOT / "workspace/private/outputs/s22plus-mainline-ml028-rc-ssh-cycle-h0-20261105-1"
WORK = ROOT / "workspace/private/outputs/s22plus-mainline-ml030-dwell-link-h0-20261105-1"
WINDOW_MS = 540000
GAP_MS = 300000
BODY = struct.Struct("<8s32s32s32s16sQQ")
DOMAIN = b"G0Q-DEBIAN-SYSVINIT-RAM-v1"


def frame(magic, kind, key, identity, first, second, boot, t0, t1):
    body = BODY.pack(magic, identity, first, second, boot, t0, t1)
    return body + hmac.digest(key, DOMAIN + identity + bytes([kind]) + body, "sha256")


def check_witness(data, key, identity, first, second, boot, t0):
    require(len(data) == BODY.size + 32, "incomplete late witness")
    t1 = BODY.unpack(data[:BODY.size])[-1]
    expected = frame(b"G030WIT1", 17, key, identity, first, second, boot, t0, t1)
    require(hmac.compare_digest(data, expected) and first != second and any(second)
            and t0 + GAP_MS <= t1 < WINDOW_MS, "late witness binding or interval differs")
    return t1


def stored(path, obj):
    persist(path, (json.dumps(obj, indent=2) + "\n").encode())


def build(out, *, emulated=False):
    out.mkdir(mode=0o700)
    orig = BASE / "init-vm-1/result.json"
    manifest = json.loads(orig.read_bytes())
    require(manifest["vm"] is True, "historical VM inputs required")
    includes = {Path(v["path"]).name:v for v in manifest["inputs"]}
    for name in ("init.c","protocol.h","s22plus_fyg8_max77705_result_parser.inc.c"):
        require(digest(includes[name]["path"]) == includes[name]["sha256"], "historical source differs")
    source = Path(includes["init.c"]["path"]).read_text()
    function = "static int serve(void) {"
    point = "    if(!error)error=transfer(client,fdt,fdt_size,1);"
    require(source.count(function) == source.count(point) == 1, "observer insertion point differs")
    source = source.replace(function, '#include "dwell.h"\n' + function)
    source = source.replace(point, point + "\n    if(!error)error=ml030_dwell(client,response);")
    (out/"observer.c").write_text(source)
    packages, lock = debian_ram.extract(ROOT/"workspace/private/outputs/s22plus-debian-bootstrap-h0-20260921-1/rootfs-d", out)
    net = json.loads((BASE/"network.json").read_bytes())
    key = secrets.token_bytes(32)
    id_inputs = [bytes.fromhex(digest(p)) for p in (out/"observer.c", HERE/"dwell.h", HERE/"dwell_vm.py",
                  orig, Path(lock["path"]))]
    identity = hashlib.sha256(b"ML030-VM-DWELL-ONLY"+key+b"".join(id_inputs)).digest()
    if emulated:
        identity = hashlib.sha256(identity + bytes.fromhex(digest(HERE/"emulated_uic.h"))).digest()
    seal = ['#define CANARY_PORT 47649']
    for name, value in (("id",identity),("key",key)):
        seal.append('static const unsigned char canary_'+name+'[32]={'+','.join(map(str,value))+'};')
    net.update(device_mac='02:'+':'.join(f'{v:02x}' for v in identity[:5]),host_mac='02:'+':'.join(f'{v:02x}' for v in identity[5:10]),
               serial='h0-'+identity.hex()[:12],udc='a600000.usb')
    for name, value in net.items():
        seal.append('static const char canary_'+name+'[]='+json.dumps(value)+';')
    (out/"seal.h").write_text("\n".join(seal)+"\n")
    exe = out/"observer"
    cmd = ["aarch64-linux-gnu-gcc","-std=c11","-Os","-static","-Wall","-Wextra","-Werror","-Wno-unused-function",
           "-Wno-unused-const-variable","-ffunction-sections","-fdata-sections","-Wl,--gc-sections","-Wl,--build-id=none",
           "-DCANARY_H0_VM","-DCANARY_DEBIAN_RAM","-I",HERE,"-I",CANARY,out/"observer.c","-o",exe]
    if emulated:cmd.insert(1,"-DML030_QEMU_UFS")
    with (out/"compile.log").open("xb") as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
    info=subprocess.check_output(["file",exe]);persist(out/"file.log",info);require(b"ARM aarch64" in info,"wrong observer")
    packages[debian_ram.OBSERVER]=exe.read_bytes();packages["etc/inittab"]=debian_ram.INITTAB
    tree=out/"tree";tree.mkdir();debian_ram.populate(tree,packages)
    import gzip
    archive=out/"fixture.cpio.gz";persist(archive,gzip.compress(debian_ram.pack(packages,True),mtime=0))
    persist(out/"key.bin",key)
    result=dict(vm=True,candidate_id=identity.hex(),key_path=str(out/"key.bin"),network=net,port=47649,
                init=debian_ram.pin(tree/"usr/sbin/init"),initramfs=debian_ram.pin(archive),
                kernel_release=manifest["kernel_release"],dtb=manifest["dtb"],initrd_address=manifest["initrd_address"],
                debian_ram=debian_ram.declaration(packages,exe,lock),device_actions=0,physical_candidate=False,emulated_hci=emulated)
    stored(out/"fixture.json",result)
    stored(out/"inputs.json",dict(original=debian_ram.pin(orig),sources={str(p):digest(p) for p in
        (HERE/"dwell.h",HERE/"dwell_vm.py",*((HERE/"emulated_uic.h",) if emulated else ()),out/"observer.c",CANARY/"protocol.h",Path(includes["s22plus_fyg8_max77705_result_parser.inc.c"]["path"]))},
        compile_command=list(map(str,cmd)),package_lock=lock))
    return result


def exact(client, size):
    data=bytearray()
    while len(data)<size:
        chunk=client.recv(size-len(data))
        require(bool(chunk),"guest closed the original socket")
        data.extend(chunk)
    return bytes(data)


def clock():
    return time.clock_gettime_ns(time.CLOCK_BOOTTIME)


def verify_emulated_trace(trace, expected):
    lines = trace.splitlines()
    commands = [line for line in lines if line.startswith(b"ufs_process_uiccmd")]
    require(commands == [b"ufs_process_uiccmd uiccmd 0x16, ucmdarg1 0x0, ucmdarg2 0x0, ucmdarg3 0x0"] * expected,
            "emulator UIC trace differs")
    require(not any(line.startswith(b"ufs_exec_scsi_cmd") for line in lines),
            "unexpected emulated SCSI execution")


def exercise(manifest, out, case):
    out.mkdir(mode=0o700)
    archive = manifest["initramfs"]
    require(manifest["vm"] is True and manifest["physical_candidate"] is False
            and digest(archive["path"]) == archive["sha256"], "H0 initramfs identity")
    cmd=json.loads((BASE/"vm-1/command.json").read_bytes())["command"]
    qroot=Path(cmd[0]).parents[2]
    kernel=json.loads((BASE/"prepare-1/build-1-result.json").read_bytes())
    require(cmd[cmd.index("-kernel")+1]==kernel["image"] and digest(kernel["image"])==kernel["sha256"],"ML028 kernel identity")
    with socket.socket() as s:
        s.bind(("127.0.0.1",0)); port=s.getsockname()[1]
    serial=out/"serial.log"; ram=out/"guest.sparse"
    idx=cmd.index("-qmp");del cmd[idx:idx+2]
    cmd[cmd.index("-serial")+1]="file:"+str(serial)
    idx=cmd.index("-object")+1;cmd[idx]=re.sub(r"mem-path=[^,]+","mem-path="+str(ram),cmd[idx])
    cmd[cmd.index("-initrd")+1]=manifest["initramfs"]["path"]
    net=manifest["network"];prefix=ipaddress.IPv4Interface(net["device_ip"]+"/"+net["netmask"]).network
    cmd[cmd.index("-netdev")+1]=f'user,id=net0,net={prefix},host={net["host_ip"]},dhcpstart={net["device_ip"]},hostfwd=tcp:127.0.0.1:{port}-:47649'
    if manifest.get("emulated_hci",False):
        cmd += ["-device","ufs,id=ml030,addr=02.0,serial=ml030-h0"]
        cmd += ["-trace","enable=ufs_process_uiccmd", "-trace","enable=ufs_exec_scsi_cmd"]
    stored(out/"command.json",dict(argv=cmd,kernel_sha=kernel["sha256"],initramfs=manifest["initramfs"],case=case))
    start=clock();deadline=start+WINDOW_MS*1000000
    key=Path(manifest["key_path"]).read_bytes();ident=bytes.fromhex(manifest["candidate_id"])
    def sleep_until(at):
        while True:
            remaining = at - clock()
            if remaining <= 0:
                return
            time.sleep(min(0.2, remaining / 1e9))
    with (out/"qemu.stderr").open("xb") as stderr:
        proc=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=stderr,
            env=dict(os.environ,LD_LIBRARY_PATH=str(qroot/"usr/lib/x86_64-linux-gnu")))
        try:
            while not serial.exists() or b"G0Q_RAM_OBSERVER_READY" not in serial.read_bytes():
                require(proc.poll() is None and clock()<start+120_000_000_000,"initial observation window")
                time.sleep(.1)
            with socket.create_connection(("127.0.0.1",port),timeout=10) as client:
                client.settimeout(12)
                n0=secrets.token_bytes(32);request=verify.request(key,ident,n0,manifest=manifest)
                persist(out/"first.request",request);client.sendall(request)
                prefix=exact(client,384);size=struct.unpack_from("<I",prefix,248)[0]
                require(40<=size<=verify.FDT_LIMIT,"first FDT length")
                persist(out/"first.response",prefix+exact(client,size));first=verify.verify(out/"first.response",manifest,n0,vm=True)
                t0=first["uptime_ms"];boot=prefix[72:88]
                anchored=clock();require(anchored<start+120_000_000_000,"initial window expired")
                stored(out/"first.json",dict(finished_ns=anchored,proof=first));print(case,"first frame sealed",flush=True)
                if case!="early":sleep_until(anchored+(GAP_MS+1000)*1_000_000)
                n1=secrets.token_bytes(32);require(n1!=n0 and any(n1),"fresh challenge required")
                issued=clock()
                query=frame(b"G030ASK1",16,key,ident,n0,n1,boot,t0,0)
                persist(out/"late.request",query);client.sendall(query)
                if case=="early":
                    require(client.recv(1)==b"","early challenge obtained a witness")
                    t1=None
                else:
                    require(issued>=anchored+GAP_MS*1_000_000 and clock()<deadline,"host dwell or deadline")
                    witness=exact(client,BODY.size+32);persist(out/"late.response",witness)
                    t1=check_witness(witness,key,ident,n0,n1,boot,t0)
                    stored(out/"witness.json",dict(issued_ns=issued,sealed_ns=clock(),same_boot=True,uptime_ms=t1))
                    permit=frame(b"G030GO01",18,key,ident,n0,n1,boot,t0,t1)
                    if case=="bad-permit":permit=permit[:-1]+bytes([permit[-1]^1])
                    persist(out/"permit.intent",permit);require(clock()<deadline,"original deadline expired");client.sendall(permit)
                    if case=="positive":
                        ack=exact(client,BODY.size+32);persist(out/"handoff.response",ack)
                        require(hmac.compare_digest(ack,frame(b"G030EMU1" if manifest.get("emulated_hci",False) else b"G030H001",19,key,ident,n0,n1,boot,t0,t1)),
                                "VM-only boundary receipt differs")
                    require(client.recv(1)==b"","unexpected data after single handoff")
            for _ in range(60):
                if b"G0Q_RAM_PARK" in serial.read_bytes():break
                time.sleep(.05)
            log=serial.read_bytes();count=log.count(b"ML030_VM_HANDOFF_ONCE NO_UFS_BACKEND")
            uic=log.count(b"ML030_VM_UIC_COMPLETE")
            if manifest.get("emulated_hci",False):
                require(count==0 and uic==int(case=="positive") and log.count(b"ML030_VM_UIC_INTENT")==uic,
                        "emulated UIC receipt differs")
            else:require(count==int(case=="positive") and not uic,"handoff count differs")
            require(proc.poll() is None,"unexpected guest exit")
            park = {"positive": 0, "early": 110, "bad-permit": 13}[case]
            require(("G0Q_RAM_PARK error=" + str(park) + "\r\n").encode() in log,
                    "guest terminal result differs")
            if manifest.get("emulated_hci",False):
                verify_emulated_trace((out/"qemu.stderr").read_bytes(),uic)
            stored(out/"result.json",dict(status="PASS_H0_SAME_BOOT_DWELL" if case=="positive" else "PASS_H0_REJECTED_"+case,
                  kernel_sha=kernel["sha256"],initial_uptime_ms=t0,late_uptime_ms=t1,
                  host_gap_seconds=(issued-anchored)/1e9,handoff_count=count,emulated_uic_completions=uic,real_ufs_attempts=0,device_actions=0))
        except Exception as error:
            # The peer can close just before its terminal serial message arrives.
            for _ in range(40):
                if serial.exists() and b"G0Q_RAM_PARK" in serial.read_bytes(): break
                time.sleep(.05)
            stored(out/"failure.json",dict(reason=str(error),case=case,device_actions=0))
            raise
        finally:
            proc.terminate()
            try:proc.wait(5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
            ram.unlink(missing_ok=True)


if __name__ == "__main__":
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["build", "positive", "early", "bad-permit"])
    parser.add_argument("--name", required=True)
    parser.add_argument("--emulated-hci", action="store_true")
    parser.add_argument("--fixture", help="the private --name used for the build")
    args = parser.parse_args()
    require(re.fullmatch(r"[a-z0-9-]+", args.name), "private output name")
    WORK.mkdir(mode=0o700, exist_ok=True)
    out = WORK / args.name
    if args.action == "build":
        require(args.fixture is None, "build takes an output name only")
        build(out, emulated=args.emulated_hci)
    else:
        require(args.fixture and re.fullmatch(r"[a-z0-9-]+", args.fixture),
                "select the built fixture with --fixture")
        manifest = json.loads((WORK / args.fixture / "fixture.json").read_bytes())
        require(manifest.get("emulated_hci", False) == args.emulated_hci,
                "fixture backend differs")
        exercise(manifest, out, args.action)
