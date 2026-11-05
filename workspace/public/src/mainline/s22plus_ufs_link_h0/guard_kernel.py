"""Build the isolated transport Image and bind the actual ARM64 link outputs."""
import argparse
import json
import os
from pathlib import Path
import sys

from cold_phy_tables import PRIVATE, digest, require

CANARY = Path(__file__).resolve().parent.parent/"s22plus_canary_h0"
sys.path.insert(0,str(CANARY))
import build_kernel

BASE = PRIVATE / "outputs/s22plus-mainline-ml028-rc-ssh-cycle-h0-20261105-1/prepare-1"


def build(directory):
    directory = directory.resolve()
    require(directory.is_relative_to(PRIVATE.resolve()), "private build required")
    receipt = directory/"transport.json"
    sources = json.loads(receipt.read_bytes())
    kernel, output = Path(sources["kernel"]), Path(sources["build"])
    require(kernel == directory/"kernel-source" and output == directory/"kernel-build" and
            all(digest(kernel/name) == pin for name, pin in sources["files"].items()),
            "transport source binding differs")
    retained = json.loads((BASE/"build-1-result.json").read_bytes())
    compiler = retained["command"]["compiler"]
    require(digest(Path(compiler["path"])) == compiler["sha256"] and
            digest(output/".config") == retained["config_sha256"], "toolchain or config differs")
    require(sources["prepared_sha256"] == digest(directory/"prepared.json") and
            digest(kernel/"arch/arm64/kernel/head.S") == digest(BASE/"original-head.S") and
            not (directory/"marker-source.json").exists(), "consumed marker must be absent")
    deps = Path(retained["command"]["environment"]["PKG_CONFIG_SYSROOT_DIR"])
    build_kernel.build(directory,deps,"unmarked",8)
    linked = json.loads((directory/"unmarked-result.json").read_bytes())
    require("retained_marker" not in linked and linked["command"]["compiler"] == compiler,
            "unmarked kernel build identity differs")
    image = output/"arch/arm64/boot/Image"
    require((output/"source").resolve() == kernel and image.stat().st_size > 32*1024**2 and
            digest(image) != retained["sha256"], "patched kernel output differs")
    symbols = (output/"vmlinux.symvers").read_text().splitlines()
    for name in ("g0q_rpmh_vrm", "g0q_usb_cover", "g0q_rpmh_begin", "g0q_rpmh_status"):
        require(sum(row.split()[1] == name for row in symbols) == 1, "missing kernel export "+name)
    result = dict(linked, status="H0_ML030_TRANSPORT_KERNEL", image=str(image), sha256=digest(image),
                  transport_sha256=digest(receipt), vmlinux_sha256=digest(output/"vmlinux"),
                  symvers_sha256=digest(output/"vmlinux.symvers"),
                  build_receipt=digest(directory/"unmarked-result.json"))
    with (directory/"guard-result.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    return result


if __name__ == "__main__":
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    print(build(parser.parse_args().directory)["sha256"])
