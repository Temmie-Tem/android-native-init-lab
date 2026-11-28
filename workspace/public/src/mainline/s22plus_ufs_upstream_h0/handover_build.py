"""Roadmap step 4b (H0): build the composite g0q_ml030.ko (report V18) against the unchanged floor kernel.

Inputs are pinned: the floor transport build (Image 5139aab5, symvers fb83fba4) and its 7.2.11 sources,
the retained ML028 toolchain environment, and the route DT 51b58a40 for the overlay. The composite holds
the gated ufshcd core (gate_render + combine_render), ufshcd-pltfrm, ufs-qcom, the g0q QMP UFS PHY and
the stage g0q_handover.c with the embedded upstream overlay. The receipt is the component record that
candidate qualification binds. Host-only, no device action.

usage: python3 -I handover_build.py <private output dir>
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
PRIVATE = ROOT / "workspace/private"
sys.path.insert(0, str(HERE))
import combine_render  # noqa: E402
import upstream_overlay  # noqa: E402

FLOOR = PRIVATE / "outputs/s22plus-ufs-route-h0-20261127-1/transport-build-floor"
FLOOR_RECORD = PRIVATE / "outputs/s22plus-ufs-route-h0-20261127-1/kernel-floor.json"
RETAINED = PRIVATE / "outputs/s22plus-mainline-ml028-rc-ssh-cycle-h0-20261105-1/prepare-1/build-1-result.json"
IMAGE_SHA256 = "5139aab548d194bc078f1cfdcff5f8273eb7613a674c7e6f0ba6ae42d15c42a5"
REPORT_VERSION = 18
STATUS = "BUILT_H0_UPSTREAM_HANDOVER_COMPONENT"
KS = FLOOR / "kernel-source"
COPY = {  # unchanged pinned upstream files copied beside the rendered ones
    "drivers/ufs/core": ("ufs-sysfs.c", "ufs-mcq.c", "ufs-txeq.c", "ufs-debugfs.c", "ufshcd-priv.h",
                         "ufs-sysfs.h", "ufs-debugfs.h", "ufs-fault-injection.h", "ufs_bsg.h",
                         "ufshcd-crypto.h", "ufs_trace.h", "ufs_trace_types.h"),
    "drivers/ufs/host": ("ufshcd-pltfrm.c", "ufshcd-pltfrm.h", "ufs-qcom.h"),
}
OBJECTS = ("g0q_handover.o", "ufshcd.o", "ufs-sysfs.o", "ufs-mcq.o", "ufs-txeq.o", "ufs-debugfs.o",
           "ufshcd-pltfrm.o", "ufs-qcom.o", "phy-qcom-qmp-ufs.o")
SOURCES = ("g0q_handover.c", "g0q_ufs_gate.h", "gate_render.py", "phy_render.py", "combine_render.py",
           "upstream_overlay.py", "handover_build.py")
BANNED_IMPORTS = ("qcom_scm_", "qcom_ice_", "blk_crypto_", "g0q_rpmh_", "g0q_icc_", "g0q_usb_")


def digest(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def require(cond, msg):
    if not cond:
        raise ValueError(msg)


def phy_headers():
    qc = KS / "drivers/phy/qualcomm"
    names, todo = set(), ["phy-qcom-qmp-ufs.c"]
    while todo:
        for line in (qc / todo.pop()).read_text().splitlines():
            if line.startswith('#include "'):
                n = line.split('"')[1]
                if n not in names:
                    names.add(n)
                    todo.append(n)
    return sorted(names)


def build(out):
    out = out.resolve()
    require(out.is_relative_to(PRIVATE.resolve()), "private output required")
    floor = json.loads(FLOOR_RECORD.read_bytes())
    require(digest(FLOOR / "kernel-build/arch/arm64/boot/Image") == floor["image_sha256"] == IMAGE_SHA256 and
            digest(FLOOR / "kernel-build/vmlinux.symvers") == floor["symvers_sha256"], "floor kernel differs")
    guard = json.loads((FLOOR / "guard-result.json").read_bytes())
    require(guard["sha256"] == IMAGE_SHA256 and guard["transport_sha256"] == digest(FLOOR / "transport.json"),
            "floor guard record differs")
    retained = json.loads(RETAINED.read_bytes())
    cc = Path(retained["command"]["compiler"]["path"])
    require(digest(cc) == retained["command"]["compiler"]["sha256"], "compiler identity")
    out.mkdir(mode=0o700)
    overlay = upstream_overlay.build(out / "overlay")
    obj = out / "module"
    obj.mkdir()
    pinned = {}
    for sub, names in COPY.items():
        for n in names:
            shutil.copyfile(KS / sub / n, obj / n)
            pinned[f"{sub}/{n}"] = digest(KS / sub / n)
    for n in phy_headers():
        shutil.copyfile(KS / "drivers/phy/qualcomm" / n, obj / n)
        pinned[f"drivers/phy/qualcomm/{n}"] = digest(KS / "drivers/phy/qualcomm" / n)
    for rel, fn, name in (("drivers/ufs/core/ufshcd.c", combine_render.ufshcd, "ufshcd.c"),
                          ("drivers/ufs/host/ufs-qcom.c", combine_render.ufs_qcom, "ufs-qcom.c"),
                          ("drivers/phy/qualcomm/phy-qcom-qmp-ufs.c", combine_render.qmp_ufs, "phy-qcom-qmp-ufs.c")):
        pinned[rel] = digest(KS / rel)
        (obj / name).write_text(fn((KS / rel).read_text()))
    for n in ("g0q_handover.c", "g0q_ufs_gate.h"):
        shutil.copyfile(HERE / n, obj / n)
    blob = (out / "overlay/upstream.dtbo").read_bytes()
    (obj / "overlay-data.h").write_text("static const unsigned char ml030_overlay[] __aligned(8) = {\n" +
        ",\n".join(", ".join(f"0x{x:02x}" for x in blob[n:n + 16]) for n in range(0, len(blob), 16)) + "\n};\n")
    (obj / "Kbuild").write_text("obj-m += g0q_ml030.o\ng0q_ml030-y := " + " ".join(OBJECTS) +
                                "\nCFLAGS_ufshcd.o += -I$(src)\n")
    kbuild = out / "kbuild"
    subprocess.run(["cp", "-a", str(FLOOR / "kernel-build"), str(kbuild)], check=True)
    shutil.copyfile(kbuild / "vmlinux.symvers", kbuild / "Module.symvers")
    env = dict(os.environ, **retained["command"]["environment"])
    make = ["make", "-s", "-C", str(KS), "O=" + str(kbuild), "ARCH=arm64", "CROSS_COMPILE=aarch64-linux-gnu-"]
    with (out / "compile.log").open("xb") as log:
        subprocess.run([*make, "modules_prepare"], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run([*make, "M=" + str(obj), "-j12", "modules"], env=env, stdout=log,
                       stderr=subprocess.STDOUT, check=True)
    require(not any(w in (out / "compile.log").read_text() for w in ("warning:", "undefined!", "ERROR")),
            "compiler or modpost diagnostics")
    module = obj / "g0q_ml030.ko"
    info = subprocess.check_output(["file", module], text=True)
    imports = sorted(s for s in subprocess.check_output(["aarch64-linux-gnu-nm", "-u", module], text=True).split()
                     if s != "U")
    (out / "imports.log").write_text("\n".join(imports) + "\n")
    require("ARM aarch64" in info and not [s for s in imports if s.startswith(BANNED_IMPORTS)],
            "unexpected module format or import")
    vermagic = subprocess.check_output(["modinfo", "-F", "vermagic", module], text=True).strip()
    require(vermagic.split()[0] == (kbuild / "include/config/kernel.release").read_text().strip(),
            "module/kernel release differs")
    require(module.stat().st_size <= 4 * 1024 * 1024, "module exceeds the observer's 4 MiB bound")
    receipt = dict(status=STATUS, report_version=REPORT_VERSION, pre_effect_return=True,
                   physical_admitted=False, device_actions=0, selected_kernel=IMAGE_SHA256,
                   transport=guard["transport_sha256"], module_path=str(module), module_sha256=digest(module),
                   module_bytes=module.stat().st_size, vermagic=vermagic, overlay=overlay,
                   pinned_upstream=pinned, rendered={p.name: digest(p) for p in sorted(obj.glob("*.[ch]"))},
                   source_sha256={n: digest(HERE / n) for n in SOURCES},
                   compiler=retained["command"]["compiler"], imports=len(imports))
    (out / "result.json").write_text(json.dumps(receipt, indent=1) + "\n")
    return receipt


if __name__ == "__main__":
    os.umask(0o077)
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    r = build(cli.parse_args().output)
    print(json.dumps({k: r[k] for k in ("status", "module_sha256", "module_bytes", "vermagic", "imports")}, indent=1))
