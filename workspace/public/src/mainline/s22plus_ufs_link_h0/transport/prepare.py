"""Prepare an isolated ML030 kernel with the bounded regulator transport and USB coverage checks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
PRIVATE = ROOT/"workspace/private"
BASE = PRIVATE/"outputs/s22plus-mainline-ml028-rc-ssh-cycle-h0-20261105-1/prepare-1"
PINS = {
    "arch/arm64/kernel/head.S": "d357f120435251173965bcb111c6935fddcc9f8384ad8824dae103373193bd14",
    "drivers/soc/qcom/cmd-db.c": "e6082231f11d6e85f663840ea40d4fdba36d41b76683fcdabadd002681f92f2f",
    "drivers/soc/qcom/rpmh.c": "83d958d6754d40efbed720f6bfc6c1218f28bd0c5ece39b8961226bbca04202c",
    "drivers/soc/qcom/rpmh-rsc.c": "6ddd654c5804d8c47cef1f30e1a6a25d98868f4c7d33a77ee239107857b6b87b",
    "drivers/interconnect/core.c": "177b6dc3f59862089099f8ff83015157400d023893b5616aadd6b55fbe7dca10",
    "drivers/interconnect/qcom/bcm-voter.c": "f482cad4f35ff5c144ce802baf9f8d9591770830a860feb79be9fc6a1c80aa83",
    "drivers/interconnect/qcom/sm8450.c": "24263005206c9ce869ec251c66a5853300b72b4efe0c492ee74634abdd507ee8",
    "drivers/clk/qcom/clk-rpmh.c": "b308209084b184f345d5a733bdeff8f5c081b524c20e31c6dec0b727b87178c7",
    "drivers/usb/dwc3/dwc3-qcom.c": "cf8257168ad0e8e201a003e7d2e3344cdfa08b33eb6ae6451728bc497d2ce008",
}
HEADER = "#include <soc/qcom/g0q-ml030.h>\n"
# The reduced g0q DT has no enabled client of the disjoint DISP graph.
# Its eleven providers share one apps voter. Distinct display BCM objects
# therefore overwrite normal votes at the same command-DB addresses.
NO_DISPLAY_DTB = "f918d3094e31428fa3f44fcc919934dbbcd819e48020c2bd129d952fb21346a0"
DISPLAY_BCMS = ("sh0", "sh1", "acv", "mc0", "mm0", "mm1")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(value, msg):
    if not value:
        raise ValueError(msg)


def once(text, old, new):
    require(text.count(old) == 1, "unexpected kernel insertion point: "+old[:80])
    return text.replace(old, new, 1)


def after_decls(text, signature, first_statement, check):
    start = text.index(signature)
    end = text.index("\n}\n", start) + 3
    body = text[start:end]
    body = once(body, first_statement, check + first_statement)
    return text[:start]+body+text[end:]


def integrate(path, text):
    check = "\tif (g0q_rpmh_deny_ordinary())\n\t\treturn -EPERM;\n\n"
    if path == "arch/arm64/kernel/head.S":
        clean = BASE/"original-head.S"
        require(digest(clean) == "db56887baf6cb87c24974609ffdb76ed5765a3756739c50a44384e384925977d",
                "retained uninstrumented ARM64 entry differs")
        return clean.read_text()
    if path == "drivers/soc/qcom/cmd-db.c":
        text = once(text, "static struct cmd_db_header *cmd_db_header;",
                    "static struct cmd_db_header *cmd_db_header;\nstatic size_t g0q_cmd_db_size;")
        text = once(text, '\tdebugfs_create_file("cmd-db",',
                    '\tg0q_cmd_db_size = rmem->size;\n\tdebugfs_create_file("cmd-db",')
        text += "\n" + (HERE/"cmd-db.inc.c").read_text()
    elif path == "drivers/soc/qcom/rpmh.c":
        text = once(text, '#include "rpmh-internal.h"', HEADER+'#include "rpmh-internal.h"')
        text = after_decls(text, "int rpmh_write_async(", "\trpm_msg = kzalloc_obj", check)
        text = after_decls(text, "int rpmh_write(", "\tret = __fill_rpmh_msg", check)
        text = after_decls(text, "int rpmh_write_batch(", "\tif (!cmd || !n)", check)
        text = after_decls(text, "void rpmh_invalidate(", "\tspin_lock_irqsave", check.replace("return -EPERM;", "return;"))
        text += "\n"+(HERE/"authority.inc.c").read_text()
    elif path == "drivers/soc/qcom/rpmh-rsc.c":
        text += "\n"+(HERE/"rsc-send.inc.c").read_text()
    elif path == "drivers/interconnect/core.c":
        text = once(text, '#include "internal.h"', HEADER+'#include "internal.h"')
        text = after_decls(text, "int icc_set_bw(", "\tif (!path)", check)
        text = after_decls(text, "static int __icc_enable(", "\tif (!path)", check)
        text += "\n"+(HERE/"icc-cover.inc.c").read_text()
    elif path == "drivers/clk/qcom/clk-rpmh.c":
        text = once(text, "#include <soc/qcom/rpmh.h>", HEADER+"#include <soc/qcom/rpmh.h>")
        text = after_decls(text, "static int clk_rpmh_aggregate_state_send_command(", "\tc->state = enable", check)
        text = after_decls(text, "static int clk_rpmh_bcm_send_cmd(", "\tmutex_lock(&rpmh_clk_lock)", check)
        text = after_decls(text, "static int clk_rpmh_bcm_set_rate(", "\tc->aggr_state = rate", check)
    elif path == "drivers/usb/dwc3/dwc3-qcom.c":
        text += "\n"+(HERE/"usb-cover.inc.c").read_text()
    elif path == "drivers/interconnect/qcom/sm8450.c":
        # Remove only the unused duplicate producers and their registrations.
        # Nodes, binding indices, ordinary BCMs and confirmation stay intact.
        for name in DISPLAY_BCMS:
            marker = "static struct qcom_icc_bcm bcm_"+name+"_disp = {\n"
            require(text.count(marker) == 1, "display BCM definition differs")
            start = text.index(marker)
            end = text.index("\n};\n", start) + len("\n};\n")
            text = text[:start]+text[end:]
            text = once(text, "\t&bcm_"+name+"_disp,\n", "")
    elif path == "drivers/interconnect/qcom/bcm-voter.c":
        text = once(text, "struct bcm_voter {", HEADER+"""
struct g0q_bcm_confirmation {
	bool seen, known;
	u64 x[QCOM_ICC_NUM_BUCKETS], y[QCOM_ICC_NUM_BUCKETS];
};
struct bcm_voter {
	bool g0q_primary;
	struct g0q_bcm_confirmation g0q_applied[2];""")
        text = once(text, "int qcom_icc_bcm_voter_commit(struct bcm_voter *voter)\n{",
                    (HERE/"bcm-cover.inc.c").read_text()+"\nint qcom_icc_bcm_voter_commit(struct bcm_voter *voter)\n{\n"
                    "\tstruct g0q_bcm_confirmation pending[2] = {};")
        text = after_decls(text, "int qcom_icc_bcm_voter_commit(", "\tif (!voter)", check)
        text = once(text, "\trpmh_invalidate(voter->dev);",
                    "\tg0q_trace_queued(voter, cmds, commit_idx, pending);\n\trpmh_invalidate(voter->dev);")
        text = after_decls(text, "int qcom_icc_bcm_voter_commit(", "\tmutex_unlock(&voter->lock);",
                           "\tg0q_trace_finish(voter, pending, ret);\n")
        text = after_decls(text, "static int qcom_icc_bcm_voter_probe(", "\tmutex_init(&voter->lock);",
                           """	if (of_machine_is_compatible("samsung,g0q")) {
		struct device_node *primary __free(device_node) =
			of_find_node_by_path("/soc@0/rsc@17a00000/bcm-voter");
		voter->g0q_primary = primary && primary == voter->dev->of_node;
	}
""")
    else:
        raise ValueError("unexpected kernel file")
    return text


def prepare(output):
    output = output.resolve()
    require(output.is_relative_to(PRIVATE.resolve()) and not output.exists(), "fresh private directory required")
    source = BASE/"kernel-source"
    for name, expected in PINS.items():
        require(digest(source/name) == expected, "kernel input differs: "+name)
    replacements = {name:integrate(name, (source/name).read_text()) for name in PINS}
    output.mkdir(mode=0o700)
    target, kbuild = output/"kernel-source", output/"kernel-build"
    subprocess.run(["cp","-a","--reflink=auto",source,target], check=True)
    subprocess.run(["cp","-a","--reflink=auto",BASE/"kernel-build",kbuild], check=True)
    for name, data in replacements.items():
        (target/name).write_text(data)
    hdr = target/"include/soc/qcom/g0q-ml030.h"
    require(not hdr.exists(), "new kernel header already present")
    shutil.copyfile(HERE/"g0q_rpmh.h", hdr)
    prepared = json.loads((BASE/"prepared.json").read_bytes())
    dt_name = "sm8450-samsung-g0q-ram.dtb"
    require(digest(BASE/dt_name) == NO_DISPLAY_DTB,
            "reviewed no-display interconnect DT differs")
    require(digest(BASE/dt_name) == prepared["dtb_sha256"] and
            digest(kbuild/".config") == prepared["config_sha256"], "retained kernel inputs differ")
    shutil.copyfile(BASE/dt_name, output/dt_name)
    prepared.update(kernel=str(target), kernel_build=str(kbuild))
    prepared.pop("retained_preparation", None)
    (output/"prepared.json").write_text(json.dumps(prepared, indent=2)+"\n")
    receipt = dict(status="H0_TRANSPORT_KERNEL_SOURCE", originals=PINS,
                   files={name:digest(target/name) for name in [*PINS, str(hdr.relative_to(target))]},
                   producer={f.name:digest(f) for f in HERE.iterdir() if f.is_file()},
                   config_sha256=digest(kbuild/".config"), prepared_sha256=digest(output/"prepared.json"),
                   baseline_prepared_sha256=digest(BASE/"prepared.json"),
                   kernel=str(target), build=str(kbuild), device_actions=0)
    (output/"transport.json").write_text(json.dumps(receipt,indent=2)+"\n")
    return receipt


if __name__=="__main__":
    os.umask(0o077)
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("output",type=Path)
    print(prepare(p.parse_args().output)["status"])
