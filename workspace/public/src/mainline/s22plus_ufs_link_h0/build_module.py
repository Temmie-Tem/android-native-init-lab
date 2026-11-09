"""Build the H0 cold-link module with an isolated copy of the retained ARM64 Kbuild."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import cold_phy_tables as tables
import late_overlay
import late_rails

HERE = Path(__file__).resolve().parent
BASE = tables.PRIVATE / "outputs/s22plus-mainline-ml028-rc-ssh-cycle-h0-20261105-1/prepare-1"
FILES = ("waipio_phy.c", "waipio_phy.h", "waipio_hci.c", "waipio_hci.h", "g0q_stage.c", "usb-admission.h")


def build(header, output, transport):
    tables.require(output.resolve().is_relative_to(tables.PRIVATE.resolve()), "private output required")
    output = output.resolve()
    output.mkdir(mode=0o700)
    transport = transport.resolve()
    tables.require(transport.is_relative_to(tables.PRIVATE.resolve()), "private transport build required")
    applied = json.loads((transport/"transport.json").read_bytes())
    kernel = Path(applied["kernel"])
    baseline = Path(applied["build"])
    tables.require(kernel == transport/"kernel-source" and baseline == transport/"kernel-build"
                   and (baseline/"source").resolve() == kernel and
                   all(tables.digest(kernel/name) == pin for name, pin in applied["files"].items())
                   and all(tables.digest(HERE/"transport"/name) == pin
                           for name, pin in applied["producer"].items()), "transport sources differ")
    patched = json.loads((transport/"guard-result.json").read_bytes())
    image = baseline/"arch/arm64/boot/Image"
    tables.require(Path(patched["image"]) == image and tables.digest(image) == patched["sha256"]
                   and patched["transport_sha256"] == tables.digest(transport/"transport.json"),
                   "transport kernel image differs")
    retained = json.loads((BASE/"build-1-result.json").read_bytes())
    tables.require(tables.digest(Path(retained["image"])) == retained["sha256"] and
                   tables.digest(baseline/".config") == retained["config_sha256"], "ML028 build identity")
    tables.validate(header, output/"parity")
    late_overlay.build(output/"overlay")
    late_rails.generate(kernel/"drivers/regulator/qcom-rpmh-regulator.c", output/"rails")
    obj = output/"module"
    obj.mkdir()
    for name in FILES:
        shutil.copyfile(HERE/name, obj/name)
    shutil.copyfile(output/"rails/rails.c", obj/"rails.c")
    shutil.copyfile(output/"parity/phy-qcom-ufs-i.h", obj/"phy-qcom-ufs-i.h")
    # This artifact permits v4/G4 only. Preserve the complete five-table parity
    # proof and remove the two unreachable declarations from this compilation.
    text = header.read_text()
    for symbol in ("phy_cal_table_rate_A_no_g4", "phy_cal_table_2nd_lane_no_g4"):
        text, count = re.subn(r"static struct ufs_qcom_phy_calibration " + symbol +
                              r"\[\] = \{[^}]*?\n\};\n", "", text)
        tables.require(count == 1, "unreachable table declaration differs")
    (obj/header.name).write_text(text)
    blob = (output/"overlay/late.dtbo").read_bytes()
    (obj/"overlay-data.h").write_text("static const unsigned char ml030_overlay[] __aligned(8) = {\n" +
        ",\n".join(", ".join(f"0x{x:02x}" for x in blob[n:n+16]) for n in range(0,len(blob),16)) +
        "\n};\n")
    (obj/"Kbuild").write_text("obj-m += g0q_ml030.o\ng0q_ml030-y := g0q_stage.o waipio_phy.o waipio_hci.o rails.o\n")
    kbuild = output/"kbuild"
    subprocess.run(["cp", "-a", "--reflink=auto", baseline, kbuild], check=True)
    shutil.copyfile(kbuild/"vmlinux.symvers", kbuild/"Module.symvers")
    env = dict(os.environ, **retained["command"]["environment"])
    cc = Path(retained["command"]["compiler"]["path"])
    tables.require(tables.digest(cc) == retained["command"]["compiler"]["sha256"], "compiler identity")
    make = ["make", "-s", "-C", str(kernel), "O="+str(kbuild), "ARCH=arm64", "CROSS_COMPILE=aarch64-linux-gnu-"]
    with (output/"compile.log").open("xb") as log:
        subprocess.run([*make,"modules_prepare"], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run([*make,"M="+str(obj),"modules"], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    module = obj/"g0q_ml030.ko"
    info = subprocess.check_output(["file", module], text=True)
    imports = subprocess.check_output(["aarch64-linux-gnu-nm", "-u", module], text=True)
    (output/"file.log").write_text(info)
    (output/"imports.log").write_text(imports)
    tables.require("ARM aarch64" in info and all(t not in imports for t in
                  ("scsi_", "ufshcd_", "qcom_scm_", "blk_mq_", "submit_bio", "request_irq")),
                  "unexpected module format or transport")
    version = subprocess.check_output(["modinfo", "-F", "vermagic", module], text=True).strip()
    tables.require(version.split()[0] == (baseline/"include/config/kernel.release").read_text().strip(),
                   "module/kernel release differs")
    receipt = dict(status="BUILT_H0_COLD_LINK_COMPONENT", source_sha256={
        str(p):tables.digest(p) for p in (HERE/"build_module.py",HERE/"late_overlay.py",HERE/"late_rails.py",
        HERE/"cold_phy_tables.py",*(HERE/n for n in FILES))}, baseline_kernel=retained["sha256"],
        selected_kernel=patched["sha256"], transport=tables.digest(transport/"transport.json"),
        inputs={p.name:tables.digest(p) for p in (kbuild/"vmlinux.symvers",kbuild/".config",header)},
        module_sha256=tables.digest(module), module_path=str(module), vermagic=version,
        physical_admitted=False, device_actions=0)
    (output/"result.json").write_text(json.dumps(receipt, indent=2)+"\n")
    return receipt


if __name__ == "__main__":
    os.umask(0o077)
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("header",type=Path)
    cli.add_argument("output",type=Path)
    cli.add_argument("--transport",required=True,type=Path)
    args=cli.parse_args()
    print(build(args.header, args.output, args.transport)["status"])
