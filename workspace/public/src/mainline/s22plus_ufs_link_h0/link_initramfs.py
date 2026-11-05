"""Create the ML030 fixed module RAM archive. No transport or live admission."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

from cold_phy_tables import PRIVATE, digest, require

HERE = Path(__file__).resolve().parent
CANARY = HERE.parent/"s22plus_canary_h0"
sys.path.insert(0, str(CANARY))
import debian_ram as debian

MODULE = "usr/lib/g0q_ml030.ko"
PINNED = {
    "init.c": "9ef8279659596de9120f6a7424476f76648b6fca5f975bb560727f1906fd5cfd",
    "protocol.h": "a38f17316c469f6fb3ae5e0e81a3d34e682f076141a8d4972322d0ef9d562ad5",
    "download-return.h": "69809bba9c959d51c3d69f11be95b6dd45ecd68ea0ca048804fa190a7c6486c5",
}
SCHEMA = "s22plus-mainline-debian-ufs-link-ram-v1"


def specification():
    return ({**debian.MEMBERS, MODULE: None}, debian.INITTAB, debian.DIRS, debian.LINKS,
            {"etc/inittab": 0o644, MODULE: 0o400})


def build(kernel_dir, component, out, *, vm):
    kr = kernel_dir.resolve()
    out = out.resolve()
    require(all(p.is_relative_to(PRIVATE.resolve()) for p in (kr, component.resolve(), out)),
            "private ML030 artifact paths required")
    for name, pin in PINNED.items():
        require(digest(CANARY/name) == pin, "baseline source changed: "+name)
    kernel = json.loads((kr/"guard-result.json").read_bytes())
    record = json.loads(component.read_bytes())
    mod = Path(record["module_path"])
    require(kernel["sha256"] == digest(Path(kernel["image"])) == record["selected_kernel"] and
            record["transport"] == kernel["transport_sha256"] == digest(kr/"transport.json") and
            digest(mod) == record["module_sha256"] and 0 < mod.stat().st_size <= 4*1024**2,
            "module/kernel identity differs")
    out.mkdir(mode=0o700)
    packages, lock = debian.extract(PRIVATE/"outputs/s22plus-debian-bootstrap-h0-20260921-1/rootfs-d", out)
    code = (CANARY/"init.c").read_text()
    for anchor, addition in (("static int serve(void) {", '#include "dwell.h"\nstatic int serve(void) {'),
        ("    if(!error)error=transfer(client,fdt,fdt_size,1);",
         "    if(!error)error=transfer(client,fdt,fdt_size,1);\n    if(!error)error=ml030_dwell(client,response);"),
        ("    if(!error)error=download_finish(client,response);",
         "    if(!error) {\n        memcpy(response+40, ml030_result_digest, 32);\n"
         "        error=download_finish(client,response);\n    }")):
        require(code.count(anchor) == 1, "observer insertion point differs")
        code = code.replace(anchor, addition)
    (out/"observer.c").write_text(code)
    key = secrets.token_bytes(32)
    net_file = PRIVATE/"outputs/s22plus-mainline-ml028-rc-ssh-cycle-h0-20261105-1/network.json"
    dtb = kr/"sm8450-samsung-g0q-ram.dtb"
    inputs = [debian.pin(p) for p in (Path(__file__), HERE/"dwell.h", HERE/"link-runtime.h",
        *(CANARY/n for n in PINNED), CANARY/"debian_ram.py", CANARY/"../../native-init/s22plus_fyg8_max77705_result_parser.inc.c",
        out/"observer.c", Path(lock["path"]), component, mod, kr/"guard-result.json", kr/"kernel-build/.config", dtb, net_file)]
    recipe = dict(schema=SCHEMA, vm=vm, inputs=inputs, key_digest=hashlib.sha256(key).hexdigest())
    identity = hashlib.sha256(json.dumps(recipe,sort_keys=True,separators=(",",":")).encode()).digest()
    net = json.loads(net_file.read_bytes())
    net.update(device_mac="02:"+":".join(f"{v:02x}" for v in identity[:5]),
               host_mac="02:"+":".join(f"{v:02x}" for v in identity[5:10]),
               serial="g0q-"+identity.hex()[:20], udc="a600000.usb")
    def array(name, data):
        return "static const unsigned char "+name+"[32]={"+",".join(map(str,data))+"};"
    seal = ["#define CANARY_PORT 47649", "#define ML030_MODULE_SIZE "+str(mod.stat().st_size),
            array("canary_id",identity), array("canary_key",key),
            array("ml030_module_sha256",bytes.fromhex(digest(mod)))]
    seal += ["static const char canary_"+name+"[]="+json.dumps(val)+";" for name,val in net.items()]
    (out/"seal.h").write_text("\n".join(seal)+"\n")
    with (out/"key.bin").open("xb") as file: file.write(key)
    exe = out/"observer"
    cmd = ["aarch64-linux-gnu-gcc", "-std=c11","-Os","-static","-Wall","-Wextra","-Werror",
           "-Wno-unused-function","-Wno-unused-const-variable","-ffunction-sections","-fdata-sections",
           "-Wl,--gc-sections","-Wl,--build-id=none","-DCANARY_DEBIAN_RAM","-DCANARY_DOWNLOAD_RAM",
           "-DML030_G0Q_MODULE",*(["-DCANARY_H0_VM"] if vm else []),"-I",out,"-I",HERE,"-I",CANARY,
           out/"observer.c","-o",exe]
    with (out/"compile.log").open("xb") as log:
        subprocess.run(cmd,check=True,stdout=log,stderr=subprocess.STDOUT)
    info = subprocess.check_output(["file",exe])
    require(b"ARM aarch64" in info and b"statically linked" in info, "observer format")
    (out/"file.log").write_bytes(info)
    packages.update({debian.OBSERVER:exe.read_bytes(), "etc/inittab":debian.INITTAB, MODULE:mod.read_bytes()})
    tree = out/"tree"
    tree.mkdir()
    debian.populate(tree,packages,specification=specification())
    archive = out/"initramfs.cpio.gz"
    archive.write_bytes(gzip.compress(debian.pack(packages,vm,specification=specification()),mtime=0))
    declaration = debian.declaration(packages,tree/debian.OBSERVER,lock)
    declaration.update(schema=SCHEMA,module=debian.pin(tree/MODULE))
    manifest = dict(status="H0_ML030_FIXED_RAM_ARCHIVE", vm=vm, candidate_id=identity.hex(),
                    key_path=str(out/"key.bin"), network=net, port=47649, inputs=inputs,
                    init=debian.pin(tree/"usr/sbin/init"), initramfs=debian.pin(archive),
                    kernel_release=(kr/"kernel-build/include/config/kernel.release").read_text().strip(),
                    dtb=debian.pin(dtb), initrd_address=0xb6915000, debian_ram=declaration,
                    device_actions=0, physical_admitted=False)
    (out/"result.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (out/"producer.json").write_text(json.dumps(dict(compile_command=list(map(str,cmd)),
        recipe=recipe,seal=debian.pin(out/"seal.h")),indent=2)+"\n")
    return manifest


if __name__ == "__main__":
    os.umask(0o077)
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("kernel",type=Path)
    cli.add_argument("component",type=Path)
    cli.add_argument("out",type=Path)
    cli.add_argument("--vm",action="store_true")
    args = cli.parse_args()
    print(build(args.kernel,args.component,args.out,vm=args.vm)["status"])
