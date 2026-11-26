"""Build an offline y2q loader-to-original-kernel marker control."""
import argparse
import hashlib
import importlib.util
import json
import secrets
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
PRIVATE = ROOT / "workspace/private"
HISTORY = "e6dcf2a313c5e36429cac9f009141c240a6e30e9"
SOURCES = HERE.parent.relative_to(ROOT) / "mainline-handoff"
BENCH = PRIVATE / "outputs/s20plus-y2q-mainline-h0-20261122.yy9l1A"
MODEL = PRIVATE / "analysis/s20plus-y2q-boot-map-20261123/fixture-inputs.json"
sys.path.insert(0, str(HERE.parent))
from build_uniloader_android import resident, require, split_boot
import prepare_uniloader_android as transport


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(source, name):
    spec = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stock_inputs():
    original = resident.BASE_BOOT.read_bytes()
    require(digest(original) == resident.BASE_BOOT_SHA256 and len(original) == resident.BASE_BOOT_SIZE,
            "original Magisk boot changed")
    header, kernel, ramdisk, dtb = split_boot(original)
    require(digest(kernel) == resident.BASE_KERNEL_SHA256 and digest(dtb) == resident.BASE_DTB_SHA256,
            "original kernel or stock DTB differs")
    return header, kernel, ramdisk, dtb


def source_tree(out):
    src = out / "control-src"
    src.mkdir(mode=0o700)
    names = ("build.py","compose.c","early-memory.c","early-pair.S.inc","entry.S","guard.c",
             "link.lds.S","stage-geometry.h","return_stage.py","return-stage.awk")
    for name in names:
        data = subprocess.check_output(["git","-C",ROOT,"show",f"{HISTORY}:{SOURCES/name}"])
        (src/name).write_bytes(data)
    subprocess.run(["patch","--batch","--fuzz=0","-p1","-i",HERE/"handoff.patch"],cwd=src,check=True)
    (src/"stock-control-fdt.h").write_bytes((HERE/"stock-control-fdt.h").read_bytes())
    return src


def build(out):
    require(out.resolve()==out and out.is_relative_to(PRIVATE) and out!=PRIVATE,"new private path required")
    out.mkdir(mode=0o700)
    src = source_tree(out)
    loader = load(src/"build.py","_stock_direct_layout")
    loader.PRIVATE,loader.MODEL,loader.BENCH=PRIVATE,MODEL,BENCH
    loader.SOURCE=PRIVATE/"outputs/s20plus-y2q-uniloader-proca-h0-20261123/control-3/upstream.tar"
    reader = load(src/"return_stage.py","_stock_direct_reader")
    _,kernel,ramdisk,dtb=stock_inputs()
    nonce=secrets.token_hex(16)
    frames=reader.frames(nonce,reader.EARLY_STAGES)
    board=loader.read_bound(BENCH/"sm8250-samsung-y2q-h0.dtb","d84c08ac2d429637d0a381865d95de8a5a942f8baa554aa5f7473a9cd6934b14")
    model=json.loads(loader.read_bound(MODEL,"7866183bf68ba52b9268a8e88e24be5a3db04625f40208d9f9d3aa48326a309c"))
    cfg=loader.layout(model,kernel,board,ramdisk)
    # The writer remains byte-for-byte the previous assembly template. Its only
    # loader output is the new prebranch frame. Stock Linux has no second hook.
    fdt=cfg["OUT_FDT"]
    cookie=int.from_bytes(hashlib.sha256(("y2q-pair:"+nonce).encode()).digest()[:8],"little")
    require(cookie!=0 and fdt<2**32,"unsupported layout or cookie")
    lines=[f"#define PAIR_C{i} {(cookie>>(i*16)) & 65535}" for i in range(4)]
    lines += [f"#define PAIR_FDT_LO {fdt & 65535}", f"#define PAIR_FDT_HI {fdt >> 16}"]
    lines.append(f'#define STOCK_CONTROL_NONCE "{nonce}"')
    for stage,key in zip(reader.EARLY_STAGES,("PRE","ENTRY"),strict=True):
        require(len(frames[stage])==128,"wrong frame length")
        lines.append(f"#define PAIR_{key}_BYTES "+",".join(str(v^0xa5) for v in frames[stage]))
    loader.build(out/"handoff",stage_image=kernel,pair_data=(fdt,"\n".join(lines)+"\n"),resident_ramdisk=ramdisk)
    raw=(out/"handoff/handoff.bin").read_bytes()
    require(raw[cfg["KERNEL_OFF"]:] == kernel and raw.endswith(kernel) and len(raw)==cfg["FILE_END"],"stock payload changed")
    enc=lambda data:bytes(b^0xa5 for b in data)
    require(all(frame not in raw for frame in frames.values()) and raw.count(enc(frames["prebranch"]))==1
            and enc(frames["primary_entry"]) not in raw,"wrong frame ownership")
    (out/"nonce").write_text(nonce+"\n")
    stage=dict(kind="HOST_ONLY_Y2Q_STOCK_DIRECT_CONTROL",nonce=nonce,raw=digest(raw),image=digest(kernel),
               ramdisk=digest(ramdisk),dtb=digest(dtb),stages={k:digest(v) for k,v in frames.items()},
               single_producer="prebranch",base_revision=HISTORY,source_patch=digest((HERE/"handoff.patch").read_bytes()),
               writer=digest((src/"early-pair.S.inc").read_bytes()),device_commands=0)
    (out/"stage.json").write_text(json.dumps(stage,indent=2)+"\n")
    return stage


def package(out, directory):
    stage=json.loads((out/"stage.json").read_bytes())
    header,kernel,ramdisk,dtb=stock_inputs()
    raw=(out/"handoff/handoff.bin").read_bytes()
    require(stage["kind"]=="HOST_ONLY_Y2Q_STOCK_DIRECT_CONTROL" and digest(raw)==stage["raw"] and raw.endswith(kernel),
            "not the exact control image")
    require(directory==directory.resolve() and directory.is_relative_to(PRIVATE),"private packaging path required")
    directory.mkdir(mode=0o700)
    boot=directory/"boot.img"
    ap=directory/"AP.tar.md5"
    resident.exact_receipt(resident.MAGISKBOOT,"magiskboot",size=resident.MAGISKBOOT_SIZE,sha256=resident.MAGISKBOOT_SHA256)
    rollback=transport.retained.ROLLBACK_AP
    original_pin=resident.exact_receipt(rollback,"original rollback AP",size=transport.retained.ROLLBACK_AP_SIZE,sha256=transport.retained.ROLLBACK_AP_SHA256)
    reader=load(out/"control-src/return_stage.py","_stock_direct_package_reader")
    with tempfile.TemporaryDirectory(dir=directory) as temp:
        scratch=Path(temp)
        with (directory/"container.log").open("xb") as log:
            def tool(*args):
                subprocess.run([resident.MAGISKBOOT,*args],cwd=scratch,stdout=log,stderr=log,check=True)
            tool("unpack","-n","-h",resident.BASE_BOOT)
            require({p.name for p in scratch.iterdir()}=={"kernel","ramdisk.cpio","dtb","header"},"unexpected boot components")
            (scratch/"kernel").write_bytes(raw)
            tool("repack","-n",resident.BASE_BOOT,boot)
        new=boot.read_bytes()
        h,k,r,t=split_boot(new)
        mutable=set(range(8,12))|set(range(576,608))
        require(len(new)==resident.BASE_BOOT_SIZE and (k,r,t)==(raw,ramdisk,dtb) and
                all(i in mutable or a==b for i,(a,b) in enumerate(zip(header,h,strict=True))),"repacked boot differs")
        require(all(frame not in new for frame in reader.frames(stage["nonce"],reader.EARLY_STAGES).values()),"clear frame in boot")
        boot.chmod(0o400)
        lz=scratch/"candidate.lz4"
        transport.prep.lz4_roundtrip(boot,lz,scratch/"roundtrip.img")
        candidate_pin=transport.prep.write_boot_ap(lz,ap)
        ap.chmod(0o400)
        archives={}
        for role,path,pin,sha in (("candidate",ap,candidate_pin,digest(new)),("rollback",rollback,original_pin,resident.BASE_BOOT_SHA256)):
            sub=scratch/role;sub.mkdir()
            archives[role]=transport.audit_ap(path,pin,{"size":len(new),"sha256":sha},sub,role)
    pair=dict(kind="HOST_ONLY_S20PLUS_STOCK_DIRECT_AP_PAIR",target="SM-G986N/y2q/G986NKSS8IYC2",
              raw=stage["raw"],nonce=stage["nonce"],archives=archives,clear_frames_absent_from_both_boots=True,
              return_template=digest(reader.shell(stage["nonce"],"0"*64,reader.EARLY_STAGES).encode()),device_commands=0)
    (directory/"pair.json").write_text(json.dumps(pair,indent=2)+"\n")
    print(pair["kind"],archives["candidate"]["ap"]["sha256"],flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build_dir",type=Path)
    parser.add_argument("package_dir",type=Path)
    a=parser.parse_args()
    build(a.build_dir)
    package(a.build_dir,a.package_dir)
