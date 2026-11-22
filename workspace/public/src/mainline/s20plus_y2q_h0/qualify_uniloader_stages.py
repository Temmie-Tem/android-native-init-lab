#!/usr/bin/env python3
"""Exercise the actual y2q stage Image in AArch64 QEMU without a phone."""

import argparse
import json
from pathlib import Path
import socket
import struct
import subprocess as sp

from build_uniloader_stages import PRIVATE, STAGES, control, decode

BASE, DTB_ADDR, INITRD, ENTRY = 0x42080000, 0x50000000, 0x51000000, 0x41000000
RAMOOPS, PMSG, ZONE = 0x9FA00000, 0x9FAC0000, 0x40000
NODE = "/reserved-memory/ramoops@9FA00000"
FILL = 0x5A


def run_case(args, assets, case, source, *, level=2, failure="", interrupt=0):
    path = args.output / case
    path.mkdir()
    dtb, final, ram = (path / name for name in ("input.dtb", "final.dtb", "ramoops.bin"))
    dtb.write_bytes(source.read_bytes())

    def put(node, prop, *values):
        sp.run(["fdtput", "-t", "x", dtb, node, prop, *(f"{x:x}" for x in values)], check=True)

    if failure != "static-dtb":
        put("/memory", "reg", 0, 0x40000000, 0,
            0x20000000 if failure == "slot-outside-ram" else 0x80000000)
        initrd = PMSG if failure == "initrd-overlap" else INITRD
        put("/chosen", "linux,initrd-start", 0, initrd)
        put("/chosen", "linux,initrd-end", 0, initrd + assets["initrd"].stat().st_size)
    if failure == "ecc":
        put(NODE, "ecc-size", 16)
    if failure == "usable-memory":
        put("/memory", "linux,usable-memory", 0, 0x40000000, 0, 0x20000000)
    if failure == "reserved-overlap":
        sp.run(["fdtput", "-c", dtb, "/reserved-memory/fixture"], check=True)
        put("/reserved-memory/fixture", "reg", 0, PMSG, 0, 0x1000)

    rejected = failure == "static-dtb" or level == 3
    traced = not failure and not rejected
    handoff = BASE + assets["build"]["payload_offset"]
    stop = BASE + assets["symbols"]["y2q_rejected"] if rejected else handoff
    if interrupt:
        stop = BASE + assets["symbols"]["publish"]

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    machine = f"virt,virtualization={'on' if level > 1 else 'off'},secure={'on' if level == 3 else 'off'}"
    command = [args.qemu, "-machine", machine, "-cpu", "cortex-a76", "-nodefaults",
               "-m", "2G", "-display", "none", "-serial", "none", "-monitor", "none",
               "-S", "-gdb", f"tcp:127.0.0.1:{port}"]
    for file, address in [(assets["image"], BASE), (dtb, DTB_ADDR),
                          (assets["entry"], ENTRY), (assets["seed"], RAMOOPS),
                          (assets["initrd"], INITRD)]:
        command.extend(["-device", f"loader,file={file},addr={address},force-raw=on"])
    command.extend(["-device", f"loader,addr={ENTRY},cpu-num=0"])
    script = path / "probe.gdb"
    ignore = f"ignore $bpnum {interrupt}" if interrupt else ""
    reject_break = "" if rejected else f"hbreak *{BASE + assets['symbols']['y2q_rejected']:#x}"
    script.write_text(f"""
set pagination off
set confirm off
set tcp auto-retry on
target remote 127.0.0.1:{port}
hbreak *{stop:#x}
{ignore}
{reject_break}
continue
python
import gdb
from pathlib import Path
def reg(name):
    return int(gdb.parse_and_eval('$'+name))
assert reg('pc') == {stop}, hex(reg('pc'))
assert (reg('cpsr') >> 2) & 3 == {level}
read = gdb.selected_inferior().read_memory
original = Path({str(dtb)!r}).read_bytes()
assert read({DTB_ADDR}, len(original)).tobytes() == original
initrd = Path({str(assets['initrd'])!r}).read_bytes()
assert read({INITRD}, len(initrd)).tobytes() == initrd
if {not rejected and not interrupt!r}:
    assert [reg('x'+str(n)) for n in range(4)] == [{BASE + 0x40000},0,0,0]
    assert read({handoff}, 64).tobytes() == Path({str(assets['image'])!r}).read_bytes()[{handoff - BASE}:{handoff - BASE + 64}]
    size = int.from_bytes(read(reg('x0')+4, 4).tobytes(), 'big')
    assert 40 <= size <= 0x140000
    Path({str(final)!r}).write_bytes(read(reg('x0'), size).tobytes())
Path({str(ram)!r}).write_bytes(read({RAMOOPS}, {4 * ZONE}).tobytes())
end
detach
""")
    with (path / "qemu.log").open("wb") as qlog, (path / "gdb.log").open("wb") as glog:
        with sp.Popen(command, stderr=qlog, stdout=qlog) as process:
            try:
                sp.run([args.gdb, "-nx", "-q", "-batch", "-x", script], stdout=glog, stderr=glog,
                       check=True, timeout=25)
            finally:
                process.terminate()
                process.wait(timeout=5)
    tag = assets["build"]["marker"]
    seed, memory = assets["seed"].read_bytes(), ram.read_bytes()
    if traced:
        signature, start, size = struct.unpack_from("<III", memory, 3 * ZONE)
        assert (signature, start) == (0x43474244, 0) and 0 < size < 1024
        offset = 3 * ZONE + 12
        assert memory[:3 * ZONE] == seed[:3 * ZONE]
        assert memory[offset + size:] == seed[offset + size:]
        # Stock persistent_ram_save_old concatenates data[start:size] and data[:start].
        ring = memory[offset:offset + size]
        assert decode(tag, ring[start:] + ring[:start], None)["loader_stages"] == list(
            STAGES[:interrupt or len(STAGES)])
    else:
        assert memory == seed
    if final.exists():
        def get(kind, node, prop):
            return sp.check_output(["fdtget", "-t", kind, final, node, prop], text=True).strip()

        assert get("s", "/chosen", "codex,y2q-uniloader-android-v1") == tag
        assert get("x", NODE, "pmsg-size") == ("0" if traced else "40000")
        assert get("x", NODE, "reg").endswith(" c0000" if traced else " 100000")
        if traced:
            old = sp.check_output(["fdtget", "-t", "s", dtb, "/chosen", "bootargs"], text=True)
            assert get("s", "/chosen", "bootargs") == f"codex.y2q_trace={tag} " + old.strip()
            reserve_dt = final.read_bytes()
            pos = struct.unpack_from(">I", reserve_dt, 16)[0]
            while (entry := struct.unpack_from(">QQ", reserve_dt, pos)) != (0, 0):
                if entry == (PMSG, ZONE):
                    break
                pos += 16
            assert entry == (PMSG, ZONE)
    print(case, "PASS", flush=True)
    return {"case": case, "vendor_entry_pc": not rejected and not interrupt,
            "committed_stages": (interrupt or len(STAGES)) if traced else 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("build", "merged-dtbs", "qemu", "gdb", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    for attr in ("build", "merged_dtbs", "qemu", "gdb", "output"):
        setattr(args, attr, getattr(args, attr).resolve())
    control.require(args.output.is_relative_to(PRIVATE.resolve()) and
                    args.output != PRIVATE.resolve(), "private output required")
    args.output.mkdir(mode=0o700)
    symbols = sp.check_output([control.TOOLCHAIN + "nm", args.build / "prefix.elf"], text=True)
    assets = {
        "build": json.loads((args.build / "result.json").read_text()),
        "symbols": {row[2]: int(row[0], 16) for line in symbols.splitlines()
                    if len(row := line.split()) == 3},
        "entry": args.output / "entry.bin",
        "seed": args.output / "ramoops-seed.bin",
        "initrd": args.output / "initrd.bin",
        "image": args.build / "Image",
    }
    assets["entry"].write_bytes(struct.pack("<IIIIQQ", 0x58000080, 0x580000A1, 0xD61F0020,
                                            0xD503201F, DTB_ADDR, BASE))
    assets["seed"].write_bytes(bytes([FILL]) * (4 * ZONE))
    _, _, initrd, _ = control.split_boot((args.build / "boot.img").read_bytes())
    assets["initrd"].write_bytes(initrd)
    trees = sorted(args.merged_dtbs.glob("base[012]-overlay[01].dtb"))
    assert len(trees) == 6
    rows = [run_case(args, assets, tree.stem, tree, level=1 + i % 2)
            for i, tree in enumerate(trees)]
    for failure in ("static-dtb", "ecc", "initrd-overlap", "reserved-overlap",
                    "slot-outside-ram", "usable-memory"):
        rows.append(run_case(args, assets, failure, trees[0], failure=failure))
    rows.append(run_case(args, assets, "el3", trees[0], level=3))
    for count in (1, 2):
        rows.append(run_case(args, assets, f"interrupted-after-{count}", trees[0], interrupt=count))
    tag = assets["build"]["marker"].encode()
    printk = (b"[    0.000000]  [0:        swapper:    0] Kernel command line: "
              b"codex.y2q_trace=" + tag + b" test=1\n")
    assert decode(tag.decode(), None, printk)["vendor_kernel_command_line"]
    for wrong in (printk + printk, printk.replace(tag, b"0" * 64),
                  printk.replace(tag, tag + b"f")):
        assert not decode(tag.decode(), None, wrong)["vendor_kernel_command_line"]
    assert not decode(tag.decode(), b"Y2Q-STAGE-V1 " + tag + b" fdt-marked\n", None)["loader_stages"]
    (args.output / "result.json").write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
