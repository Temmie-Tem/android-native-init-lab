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
    "download-return.h": "e80cf76b194004b2acd67ff6adb7c3a9d4549a13a9854b8743562f1ffb7264b7",
}
SCHEMA = "s22plus-mainline-debian-ufs-link-ram-v1"
# UFS V13 route composition: the adopted Stage 2 route observer, byte for byte.
ROUTE_HEADER = "max77705-usb-route.h"
ROUTE_HEADER_SHA256 = "6c5c3c1feb22fff799cc3cfa74322457e4cac82edbaa415c17b61c2c5edfe549"
# Witness floor (route scope only): the second challenge and witness need guest
# BOOTTIME of at least 60 s instead of 300 s after the first response.
DWELL_HEADER = "dwell.h"
DWELL_HEADER_SHA256 = "6d5238683288dba617d1210106675aa9a361bd6d098910352108ee31faad4590"
WITNESS_FLOOR_MS = 60000
# Component record status of the V18 composite (s22plus_ufs_upstream_h0/handover_build.py).
HANDOVER_STATUS = "BUILT_H0_UPSTREAM_HANDOVER_COMPONENT"


def specification():
    return ({**debian.MEMBERS, MODULE: None}, debian.INITTAB, debian.DIRS, debian.LINKS,
            {"etc/inittab": 0o644, MODULE: 0o400})


def observer_source(route=False, witness_floor=False):
    require(type(route) is bool and type(witness_floor) is bool, "explicit route composition mode required")
    require(route or not witness_floor, "the witness floor exists only in the route composition")
    code = (CANARY/"init.c").read_text()
    for anchor, addition in (("static int serve(void) {", '#include "dwell.h"\nstatic int serve(void) {'),
        ("    if(!error)error=transfer(client,fdt,fdt_size,1);",
         "    if(!error)error=transfer(client,fdt,fdt_size,1);\n    if(!error)error=ml030_dwell(client,response);"),
        ("    if(!error)error=download_finish(client,response);",
         "    if(!error) {\n        memcpy(response+40, ml030_result_digest, 32);\n"
         "        error=download_finish(client,response);\n    }"),
        ('    dprintf(2,"G0Q_RAM_PID1_BEGIN\\n");',
         '#ifdef G0Q_AUTOMATIC_RECOVERY\n    { int armed = recovery_begin(); if (armed) park(armed); }\n#endif\n'
         '    dprintf(2,"G0Q_RAM_PID1_BEGIN\\n");')):
        require(code.count(anchor) == 1, "observer insertion point differs")
        code = code.replace(anchor, addition)
    if route:
        code = compose_route(code)
    if witness_floor:
        anchor = '#include "dwell.h"\n'
        require(code.count(anchor) == 1, "dwell insertion point differs")
        code = code.replace(anchor, "/* ---- rendered " + DWELL_HEADER + " ---- */\n" + dwell_header() +
                            "/* ---- end of rendered " + DWELL_HEADER + " ---- */\n")
    return code


DWELL_RENDERING = (
    ("#define ML030_DWELL_MS 300000U\n",
     "#define ML030_DWELL_MS 300000U\n"
     "/* Witness floor composition: the 300 s dwell after the first response is\n"
     " * replaced by an absolute guest BOOTTIME floor. */\n"
     "#define ML030_FLOOR_MS " + str(WITNESS_FLOOR_MS) + "U\n"),
    ("    if (now < t0 + ML030_DWELL_MS || now >= deadline) return ETIMEDOUT;\n",
     "    if (now < ML030_FLOOR_MS || now <= t0 || now >= deadline) return ETIMEDOUT;\n"),
    ("        ml030_u64(next + 216) < t0 + ML030_DWELL_MS || now_ms() >= deadline) return EPROTO;\n",
     "        ml030_u64(next + 216) < ML030_FLOOR_MS || ml030_u64(next + 216) <= t0 ||\n"
     "        now_ms() >= deadline) return EPROTO;\n"),
)


def dwell_header():
    """The adopted dwell header, byte for byte, with its two 300 s comparisons
    replaced by the 60 s BOOTTIME floor. Everything else is unchanged."""
    require(digest(HERE/DWELL_HEADER) == DWELL_HEADER_SHA256, "dwell header differs")
    text = (HERE/DWELL_HEADER).read_text()
    for anchor, replacement in DWELL_RENDERING:
        require(text.count(anchor) == 1, "dwell rendering point differs")
        text = text.replace(anchor, replacement)
    return text


ROUTE_DISPATCH_ANCHOR = ("    uint64_t dispatch = mx_now();\n"
                         "    if (dispatch - sampled > MX_GATE_FRESH_MS) {\n")
ROUTE_DISPATCH_GUARD = ("    uint64_t dispatch = mx_now();\n"
                        "    /* V13 route composition: never dispatch on a failed clock read or at\n"
                        "     * or after the end of the 120 s first-connection window. */\n"
                        "    if (dispatch == UINT64_MAX || dispatch >= deadline) {\n"
                        "        mx.gate = MX_GATE_STALE;\n"
                        "        return;\n"
                        "    }\n"
                        "    if (dispatch - sampled > MX_GATE_FRESH_MS) {\n")


ROUTE_STROBE_ANCHOR = ("    if (mx_write_route() || mx_write(MX_USBC_ADDR, MX_AP_DATAOUT_END, 0x00))\n"
                       "        mx.write_status = MX_IO;\n"
                       "    else\n"
                       "        mx.write_status = mx_await(MX_CTRL1_WRITE, &echo_value, &wseen);\n")
ROUTE_STROBE_GUARD = ("    uint64_t strobe = 0;\n"
                      "    if (mx_write_route())\n"
                      "        mx.write_status = MX_IO;\n"
                      "    else if ((strobe = mx_now()) == UINT64_MAX || strobe >= deadline) {\n"
                      "        /* V13 route composition: the payload alone starts nothing. No start\n"
                      "         * strobe on a failed clock read or at or after the window's end. */\n"
                      "        mx.gate = MX_GATE_STALE;\n"
                      "        return;\n"
                      "    } else if (mx_write(MX_USBC_ADDR, MX_AP_DATAOUT_END, 0x00))\n"
                      "        mx.write_status = MX_IO;\n"
                      "    else\n"
                      "        mx.write_status = mx_await(MX_CTRL1_WRITE, &echo_value, &wseen);\n")


def route_header():
    """The adopted route observer, byte for byte, plus two window checks: at the
    write's dispatch sample and again directly before its mailbox start strobe.

    The shared header file is unchanged; this composition renders its own copy into
    the observer source, which candidate reproduction compares byte for byte.
    """
    require(digest(CANARY/ROUTE_HEADER) == ROUTE_HEADER_SHA256, "route observer header differs")
    text = (CANARY/ROUTE_HEADER).read_text()
    require(text.count(ROUTE_DISPATCH_ANCHOR) == 1 and text.count(ROUTE_STROBE_ANCHOR) == 1,
            "route dispatch point differs")
    return text.replace(ROUTE_DISPATCH_ANCHOR, ROUTE_DISPATCH_GUARD).replace(ROUTE_STROBE_ANCHOR, ROUTE_STROBE_GUARD)


def compose_route(code):
    """Add the adopted route observer's three sampling insertions to the V13 observer.

    The timer child is already armed above G0Q_RAM_PID1_BEGIN. mx_begin() samples
    before USB setup; the first-connection wait polls in 200 ms steps and calls
    mx_tick(), which may issue the one gated CONTROL1_W(COM_USB). A tick starts
    only while at least MX_TICK_GUARD_MS of the 120 s window remains, and the
    write is never dispatched at or after the window's end. The response layout
    is unchanged: mx_final()/mx_fill() are not called.
    """
    header = route_header()
    for anchor, addition in (
        ("static int proof(", "/* ---- rendered " + ROUTE_HEADER + " ---- */\n" + header +
         "/* ---- end of rendered " + ROUTE_HEADER + " ---- */\n"
         "/* No tick starts in the last second of the window. */\n"
         "#define MX_TICK_GUARD_MS 1000U\nstatic int proof("),
        ('    dprintf(2,"G0Q_RAM_PID1_BEGIN\\n");\n', '    dprintf(2,"G0Q_RAM_PID1_BEGIN\\n");\n    mx_begin();\n'),
        ("        struct pollfd p={fd,POLLIN,0};int rc=poll(&p,1,(int)(deadline-now));\n"
         "        if(rc<0) {if(errno==EINTR)continue;error=errno;break;}\n"
         "        if(!rc) {error=ETIMEDOUT;break;}\n",
         "        struct pollfd p={fd,POLLIN,0};uint64_t wait=deadline-now;if(wait>MX_TICK_MS)wait=MX_TICK_MS;\n"
         "        int rc=poll(&p,1,(int)wait);\n"
         "        if(rc<0) {if(errno==EINTR)continue;error=errno;break;}\n"
         "        if(!rc) {uint64_t tick=now_ms();\n"
         "            if(tick!=UINT64_MAX&&tick<deadline&&deadline-tick>=MX_TICK_GUARD_MS)mx_tick();\n"
         "            continue;}\n")):
        require(code.count(anchor) == 1, "route insertion point differs")
        code = code.replace(anchor, addition)
    return code


def seal_text(identity, key, net, mod):
    def array(name, data):
        return "static const unsigned char "+name+"[32]={"+",".join(map(str,data))+"};"
    seal = ["#define CANARY_PORT 47649", "#define ML030_MODULE_SIZE "+str(mod.stat().st_size),
            array("canary_id",identity), array("canary_key",key),
            array("ml030_module_sha256",bytes.fromhex(digest(mod)))]
    seal += ["static const char canary_"+name+"[]="+json.dumps(val)+";" for name,val in net.items()]
    return "\n".join(seal)+"\n"


import report_modes


def compile_command(out, *, vm, destination=None, **modes):
    try:
        version = report_modes.version_of(**modes)
    except ValueError as error:
        require(False, str(error))
    exe = destination or out/"observer"
    cmd = ["aarch64-linux-gnu-gcc", "-std=c11","-Os","-static","-Wall","-Wextra","-Werror",
           "-Wno-unused-function","-Wno-unused-const-variable","-ffunction-sections","-fdata-sections",
           "-Wl,--gc-sections","-Wl,--build-id=none","-DCANARY_DEBIAN_RAM","-DCANARY_DOWNLOAD_RAM",
           "-DML030_G0Q_MODULE",*("-D" + name for name in report_modes.defines(version, observer=True)),
           *(["-DCANARY_H0_VM"] if vm else []),"-I",out,"-I",HERE,"-I",CANARY,
           out/"observer.c","-o",exe]
    return list(map(str, cmd))


def build(kernel_dir, component, out, *, vm, pre_effect_return=False, route=False, witness_floor=False):
    require(type(pre_effect_return) is bool, "explicit observer return mode required")
    require(type(route) is bool and (not route or (pre_effect_return and not vm)),
            "route composition requires the board V13 observer")
    require(type(witness_floor) is bool and (route or not witness_floor),
            "the witness floor requires the route composition")
    kr = kernel_dir.resolve()
    out = out.resolve()
    require(all(p.is_relative_to(PRIVATE.resolve()) for p in (kr, component.resolve(), out)),
            "private ML030 artifact paths required")
    for name, pin in PINNED.items():
        require(digest(CANARY/name) == pin, "baseline source changed: "+name)
    kernel = json.loads((kr/"guard-result.json").read_bytes())
    record = json.loads(component.read_bytes())
    version = record.get('report_version', 3)
    require(record.get('pre_effect_return', False) is pre_effect_return and
            (not pre_effect_return or 4 <= version <= report_modes.LATEST), 'module/observer return mode differs')
    if pre_effect_return and version >= report_modes.FIRST['upstream_handover']:
        # V18: the composite upstream handover module checks its own 60 s floor and never opens
        # the kernel's RPMh arena, so only the floor route observer may carry it.
        require(record.get('status') == HANDOVER_STATUS and route and witness_floor,
                "the V18 handover module pairs only with the witness-floor route observer")
    else:
        import boot_floor
        require(boot_floor.component_floor(record, kernel) is witness_floor,
                "module/kernel boot floor must match the witness floor")
    selected = report_modes.modes(version if pre_effect_return else 3)
    hci_snapshot, hce_handoff = selected['hci_snapshot'], selected['hce_handoff']
    mod = Path(record["module_path"])
    require(kernel["sha256"] == digest(Path(kernel["image"])) == record["selected_kernel"] and
            record["transport"] == kernel["transport_sha256"] == digest(kr/"transport.json") and
            digest(mod) == record["module_sha256"] and 0 < mod.stat().st_size <= 4*1024**2,
            "module/kernel identity differs")
    out.mkdir(mode=0o700)
    packages, lock = debian.extract(PRIVATE/"outputs/s22plus-debian-bootstrap-h0-20260921-1/rootfs-d", out)
    code = observer_source(route, witness_floor)
    (out/"observer.c").write_text(code)
    key = secrets.token_bytes(32)
    net_file = PRIVATE/"outputs/s22plus-mainline-ml028-rc-ssh-cycle-h0-20261105-1/network.json"
    dtb = kr/"sm8450-samsung-g0q-ram.dtb"
    inputs = [debian.pin(p) for p in (Path(__file__), HERE/"build_evidence.py", HERE/"dwell.h", HERE/"link-runtime.h",
        *(CANARY/n for n in PINNED), CANARY/"debian_ram.py", CANARY/"../../native-init/s22plus_fyg8_max77705_result_parser.inc.c",
        out/"observer.c", Path(lock["path"]), component, mod, kr/"guard-result.json", kr/"kernel-build/.config", dtb, net_file)]
    if pre_effect_return:
        inputs.append(debian.pin(HERE/'link-report.h'))
    if route:
        inputs.append(debian.pin(CANARY/ROUTE_HEADER))
    if hce_handoff:
        inputs.append(debian.pin(HERE/'recovery.h'))
    recipe = dict(schema=SCHEMA, vm=vm, inputs=inputs, key_digest=hashlib.sha256(key).hexdigest())
    if pre_effect_return:
        recipe['pre_effect_return'] = True
    if route:
        recipe['usb_route'] = True
    if witness_floor:
        recipe['witness_floor_ms'] = WITNESS_FLOOR_MS
    if hci_snapshot or hce_handoff:
        recipe['report_version'] = record['report_version']
    identity = hashlib.sha256(json.dumps(recipe,sort_keys=True,separators=(",",":")).encode()).digest()
    net = json.loads(net_file.read_bytes())
    net.update(device_mac="02:"+":".join(f"{v:02x}" for v in identity[:5]),
               host_mac="02:"+":".join(f"{v:02x}" for v in identity[5:10]),
               serial="g0q-"+identity.hex()[:20], udc="a600000.usb")
    (out/"seal.h").write_text(seal_text(identity, key, net, mod))
    with (out/"key.bin").open("xb") as file: file.write(key)
    exe = out/"observer"
    cmd = compile_command(out, vm=vm, **selected)
    import build_evidence
    provenance = build_evidence.compile_observer(cmd, out)
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
    if pre_effect_return:
        manifest.update(report_version=record['report_version'], pre_effect_return=True)
    if route:
        manifest.update(usb_route=True)
    if witness_floor:
        manifest.update(witness_floor_ms=WITNESS_FLOOR_MS)
    (out/"result.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (out/"producer.json").write_text(json.dumps(dict(compile_command=list(map(str,cmd)),
        recipe=recipe,seal=debian.pin(out/"seal.h"),provenance=provenance),indent=2)+"\n")
    return manifest


if __name__ == "__main__":
    os.umask(0o077)
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("kernel",type=Path)
    cli.add_argument("component",type=Path)
    cli.add_argument("out",type=Path)
    cli.add_argument("--vm",action="store_true")
    cli.add_argument("--pre-effect-return",action="store_true")
    cli.add_argument("--route",action="store_true")
    cli.add_argument("--witness-floor",action="store_true")
    args = cli.parse_args()
    print(build(args.kernel,args.component,args.out,vm=args.vm,pre_effect_return=args.pre_effect_return,
                route=args.route,witness_floor=args.witness_floor)["status"])
