"""Build the single y2q initcall/USB trial from pinned original components."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import types

import build_basic_setup_stage as retained
import consolidated_reader as reader

loader, previous, packager = retained.loader, retained.previous, retained.package_stage
HERE = retained.HERE
PROFILE = "s20plus-g986n-consolidated-f1"
TUNING = {"hs-disconnect-bp":2156, "squelch-detector-bp":-2090, "hs-amplitude-bp":2670,
          "pre-emphasis-duration-bp":20000, "pre-emphasis-amplitude-bp":30000,
          "hs-rise-fall-time-bp":-4100, "hs-crossover-voltage-microvolt":0,
          "hs-output-impedance-micro-ohms":0, "ls-fs-output-impedance-bp":0}
sub = retained.substitute
sha = loader.digest


def read_text(path, pin):
    return loader.read_bound(path, pin).decode()


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def ram_inputs(out, nonce):
    (out/"ramfs").mkdir(exist_ok=True)
    header = out/"build-id.h"
    header.write_text(f'#define Y2Q_BUILD_ID "{nonce}"\n')
    code = read_text(HERE/"init.c","516ab23fd02d61fb0fe9114ff1cdc4a9e715a3b8c6e85cd1086d8a11485a74fc")
    (out/"init.c").write_text(sub(code,"attempt < 20;","attempt < 90;"))
    elf = out/"ramfs/init"
    run(["aarch64-linux-gnu-gcc","-Os","-Wall","-Wextra","-Werror","-static","-o",elf,out/"init.c"])
    def disasm(name):
        return subprocess.check_output(["aarch64-linux-gnu-objdump","-d","--disassemble="+name,elf],text=True)
    calls=re.findall(r"^\s*([0-9a-f]+):\s+[0-9a-f]+\s+bl\s+[0-9a-f]+ <(?:__)?getpid>",disasm("main"),re.M)
    svc=re.findall(r"^\s*([0-9a-f]+):\s+[0-9a-f]+\s+svc\s+#?0x0",disasm("__getpid"),re.M)
    if len(calls)!=1 or len(svc)!=1:
        raise ValueError("cannot bind static /init getpid call and SVC")
    old=loader.BENCH
    loader.read_bound(old/"gen_init_cpio","45316da675e61ceda74e25b7f2f96e28e896fc6a116f61509f507b588fe133e7")
    manifest="dir /config 0755 0 0\ndir /dev 0755 0 0\nnod /dev/console 0600 0 0 c 5 1\nfile /init "+str(elf)+" 0755 0 0\ndir /sys 0755 0 0\n"
    (out/"initramfs.list").write_text(manifest)
    archive=subprocess.check_output([old/"gen_init_cpio","-t","0",out/"initramfs.list"])
    ramdisk=subprocess.check_output(["gzip","-5","-n","-c"],input=archive)
    (out/"initrd.gz").write_bytes(ramdisk)
    board=out/"board.dtb"
    board.write_bytes(loader.read_bound(old/"sm8250-samsung-y2q-h0.dtb","d84c08ac2d429637d0a381865d95de8a5a942f8baa554aa5f7473a9cd6934b14"))
    for key,value in TUNING.items():
        run(["fdtput","-t","i","--",board,"/soc@0/phy@88e3000","qcom,"+key,str(value)])
    return dict(init_elf=sha(elf.read_bytes()),init_bytes=elf.stat().st_size,pc=int(svc[0],16)+4,
                lr=int(calls[0],16)+4,initrd=sha(ramdisk),board=sha(board.read_bytes()),build_id=sha(header.read_bytes()))


def instrument(src,nonce,meta):
    retained.build_cstage_serial.select_serial(src)
    driver=src/"drivers/phy/qualcomm/phy-qcom-snps-femto-v2.c"
    s=read_text(driver,"b3ada16f3fce7e5600b063016dfe2e81f66d8f092d2051c01f392010a8868f92")
    driver.write_text(sub(s,"REFCLK_SEL_DEFAULT, REFCLK_SEL_MASK);","REFCLK_SEL_MASK, REFCLK_SEL_DEFAULT);"))
    inc='#include <linux/y2q-progress.h>\n'
    main=src/"init/main.c"
    s=read_text(main,"64a6b91514fb324ce41e874d7cc8312de9489c6df763873a09168bb222efa91d")
    old="\tfor (fn = initcall_levels[level]; fn < initcall_levels[level+1]; fn++)\n\t\tdo_one_initcall(initcall_from_entry(fn));"
    s=sub(s,old,"""	for (fn = initcall_levels[level]; fn < initcall_levels[level+1]; fn++) {
		unsigned int index = fn - __initcall0_start;

		if (index < 153)
			y2q_progress(2 * index);
		do_one_initcall(initcall_from_entry(fn));
		if (index < 153)
			y2q_progress(2 * index + 1);
	}""")
    s=sub(s,"\tdriver_init();","\tdriver_init();\n\ty2q_progress(307);")
    s=sub(s,"\tdo_basic_setup();","\ty2q_basic_anchor();\n\tdo_basic_setup();\n\ty2q_progress(312);")
    s=sub(s,"\twait_for_initramfs();\n\tconsole_on_rootfs();","\twait_for_initramfs();\n\ty2q_progress(313);\n\tconsole_on_rootfs();")
    old="\treturn kernel_execve(init_filename, argv_init, envp_init);"
    s=sub(s,old,'\tif (init_filename == ramdisk_execute_command && !strcmp(init_filename, "/init"))\n\t\ty2q_trial_exec();\n'+old)
    main.write_text(inc+s)
    dd=src/"drivers/base/dd.c"
    s=read_text(dd,"d7635dbed29963ce89ca9754a0a7f87f24364cdfa20b199e4177dc16c9af16d3")
    start=s.index("static int deferred_probe_initcall(void)")
    end=s.index("late_initcall(deferred_probe_initcall)",start)
    call="\tflush_work(&deferred_probe_work);"
    sections=s[start:end].split(call)
    if len(sections)!=3:
        raise ValueError("deferred work call sites changed")
    for i in (0,1):
        sections[i]+=f"\ty2q_progress({308+i*2});\n"+call+f"\n\ty2q_progress({309+i*2});"
    dd.write_text(inc+s[:start]+"".join(sections)+s[end:])
    syscalls=src/"kernel/sys.c"
    s=read_text(syscalls,"0b656f8809d781b7e684a1a4c4144d925684c69e9f6050c41c6374c5206d2c8d")
    old="SYSCALL_DEFINE0(getpid)\n{\n\treturn task_tgid_vnr(current);"
    syscalls.write_text(inc+sub(s,old,"SYSCALL_DEFINE0(getpid)\n{\n\tif (unlikely(is_global_init(current)))\n\t\ty2q_trial_getpid();\n\treturn task_tgid_vnr(current);"))
    (src/"include/linux/y2q-progress.h").write_text("void y2q_progress(unsigned int bit);\nvoid y2q_basic_anchor(void);\nvoid y2q_trial_exec(void);\nvoid y2q_trial_getpid(void);\n")
    anchor=reader.frames(nonce)["basic_enter"]
    arrays = ""
    for name,raw in (("y2q_nonce",bytes.fromhex(nonce)),("y2q_anchor",bytes(b^0xa5 for b in anchor))):
        arrays+=f"static const u8 {name}[] = {{"+", ".join(map(str,raw))+"};\n"
    (src/"init/y2q-trial-data.h").write_text(arrays+f"#define Y2Q_INIT_BYTES {meta['init_bytes']}\n#define Y2Q_GETPID_PC {meta['pc']:#x}UL\n#define Y2Q_GETPID_LR {meta['lr']:#x}UL\n")
    shutil.copyfile(HERE/"consolidated-witness.c",src/"init/y2q-progress.c")
    with (src/"init/Makefile").open("a") as f:
        f.write("\nobj-y += y2q-progress.o\n")


def local_adapter(path,pin,changes,bindings):
    raw=read_text(path,pin)
    for old,new in changes:
        raw=sub(raw,old,new)
    module=types.ModuleType("_consolidated_"+path.stem)
    module.__file__=str(path)
    module.__dict__.update(bindings)
    exec(compile(raw,str(path),"exec"),module.__dict__)
    return module


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment",type=Path)
    exp=parser.parse_args().experiment
    if exp.resolve(strict=True)!=exp or exp.parent!=loader.PRIVATE/"analysis":
        raise ValueError("canonical experiment path required")
    out=exp/"candidate"
    out.mkdir(mode=0o700)
    nonce=secrets.token_hex(16)
    meta=ram_inputs(out,nonce)
    archive=loader.BENCH/"linux-6.18.tar.xz"
    with archive.open("rb") as f:
        if hashlib.file_digest(f,"sha256").hexdigest()!=previous.ARCHIVE:
            raise ValueError("Linux source changed")
    run(["tar","-xf",archive,"-C",out])
    src=out/"linux-6.18"
    instrument(src,nonce,meta)
    objects=out/"kernel-build"
    objects.mkdir()
    config=loader.read_bound(loader.BENCH/"kernel-build/.config",previous.CONFIG)
    (objects/".config").write_bytes(config)
    env=dict(os.environ,KBUILD_BUILD_USER="lab",KBUILD_BUILD_HOST="y2q",
             KBUILD_BUILD_TIMESTAMP="2026-11-23 00:00:00 UTC",KBUILD_BUILD_VERSION="1")
    with (out/"kernel-build.log").open("xb") as log:
        for target in ("olddefconfig","Image"):
            run(["make","-C",src,f"O={objects}","ARCH=arm64","CROSS_COMPILE=aarch64-linux-gnu-","-j16",target],
                env=env,stdout=log,stderr=subprocess.STDOUT)
    finish(exp, nonce, meta)


def finish(exp, nonce, meta):
    out=exp/"candidate"
    objects=out/"kernel-build"
    config=loader.read_bound(loader.BENCH/"kernel-build/.config",previous.CONFIG)
    if (objects/".config").read_bytes()!=config:
        raise ValueError("unexpected config change")
    image=(objects/"arch/arm64/boot/Image").read_bytes()
    symbols={s[2]:int(s[0],16) for line in (objects/"System.map").read_text().splitlines() if len(s:=line.split())==3}
    if symbols["__initcall_end"]-symbols["__initcall0_start"]!=153*4:
        raise ValueError("expected exactly 153 regular PREL32 entries")
    board=(out/"board.dtb").read_bytes()
    ramdisk=(out/"initrd.gz").read_bytes()
    call="    cfg = layout(model, image, board, initrd)"
    trial=local_adapter(Path(loader.__file__),"589a304798313ad4826c6370c5745d70bedbfcfac76e498d83dc82cfc6b413c9",
                        [(call,"    board, initrd = trial_board, trial_ramdisk\n"+call)],
                        dict(trial_board=board,trial_ramdisk=ramdisk))
    trial.build(out/"handoff",stage_image=image)
    frames=reader.frames(nonce)
    meta.update(kind="HOST_ONLY_Y2Q_KERNEL_STAGE_WITNESS",profile=PROFILE,nonce=nonce,image=sha(image),
                config=previous.CONFIG,release=previous.ARCHIVE,system_map=sha((objects/"System.map").read_bytes()),
                raw=sha((out/"handoff/handoff.bin").read_bytes()),stages={k:sha(v) for k,v in frames.items()})
    (out/"stage.json").write_text(json.dumps(meta,indent=2)+"\n")
    pkg=local_adapter(Path(packager.__file__),"672ea2268c813ef009ee0c2d1fc00260d494819b5084f5840be0e662c6066f7d",
                      [('"46757f90128509a95836df46dbab0a1b66af21c10522e6497780f57c32280a46"', 'stage["initrd"]')],{})
    pkg.return_stage=reader
    pkg.package(out,exp/"packaged")
    receipt=exp/"packaged/pair.json"
    pair=json.loads(receipt.read_bytes())
    pair["profile"]=PROFILE
    receipt.write_text(json.dumps(pair,indent=2)+"\n")


if __name__=="__main__":
    main()
