"""Exercise actual before/after SM8450 BCM producers without device access.

Extract unchanged functions and full tables from the supplied retained trees.
The C harness models cmd-db/RPMh and kernel plumbing; it is not hardware proof.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
FUNCTIONS = {
    "drivers/interconnect/qcom/bcm-voter.c": (
        "void qcom_icc_bcm_voter_add(", "static void bcm_aggregate_mask(",
        "static void bcm_aggregate(", "static inline void tcs_cmd_gen(",
        "static void tcs_list_gen(", "static int g0q_bcm_index(",
        "static void g0q_trace_queued(", "static void g0q_trace_finish(",
        "int g0q_bcm_confirm_usb(", "int qcom_icc_bcm_voter_commit("),
    "drivers/interconnect/qcom/icc-rpmh.c": (
        "void qcom_icc_pre_aggregate(", "int qcom_icc_aggregate(",
        "int qcom_icc_set(", "int qcom_icc_bcm_init("),
    "drivers/interconnect/core.c": (
        "static int aggregate_requests(", "void icc_node_add(",
        "void icc_sync_state(", "static int apply_constraints(",
        "int icc_set_bw(", "static int __icc_enable(", "int g0q_icc_confirm_usb("),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def extract(kernel, output):
    chunks, pins = [], []
    for name, signatures in FUNCTIONS.items():
        text = (kernel/name).read_text()
        for signature in signatures:
            assert text.count(signature) == 1, signature
            start = text.index(signature)
            end = text.index("\n}\n", start) + 3
            function = text[start:end]
            chunks.append(function)
            pins.append(dict(path=name, signature=signature, sha256=sha(function.encode())))
    (output/"actual-producers.inc").write_text("\n".join(chunks))
    text = (kernel/"drivers/interconnect/qcom/sm8450.c").read_text()
    tables = text[text.index("static struct qcom_icc_node qhm_qspi;"):text.index("static const struct of_device_id")]
    binding = (kernel/"include/dt-bindings/interconnect/qcom,sm8450.h").read_text()
    (output/"actual-tables.inc").write_text(binding+"\n"+tables)
    descs = re.findall(r"static const struct qcom_icc_desc (sm8450_\w+) =", tables)
    (output/"actual-providers.inc").write_text(
        "static const struct qcom_icc_desc *descs[]={"+",".join("&"+x for x in descs)+"};\n")
    return dict(functions=pins, tables_sha256=sha(tables.encode()),
                binding_sha256=sha(binding.encode()), providers=descs)


def run(before, after, output, compiler="cc", emulator=None):
    output = output.resolve()
    assert output.is_relative_to(ROOT/"workspace/private") and not output.exists()
    output.mkdir(mode=0o700, parents=True)
    fixture = output/"fixture.c"
    fixture.write_bytes((ROOT/"tests/s22plus_ml035_bcm_fixture.c").read_bytes())
    variants = []
    for label, kernel, aliases in (("before", before, 1), ("after", after, 0)):
        directory = output/label
        directory.mkdir()
        pins = extract(kernel.resolve(), directory)
        binary = directory/"fixture"
        cmd = [compiler, "-std=gnu11", "-Wall", "-Wextra", "-Werror",
               "-Wno-sign-compare", "-Wno-unused-parameter", "-O2",
               "-DHAS_DISPLAY_BCMS="+str(aliases), "-I", str(directory),
               "-I", str(HERE/"transport"), str(fixture), "-o", str(binary)]
        if emulator:
            cmd.insert(1, "-static")
        process = subprocess.run(cmd, capture_output=True)
        (directory/"compile.log").write_bytes(process.stdout+process.stderr)
        process.check_returncode()
        file_output = subprocess.check_output(["file", str(binary)], text=True)
        (directory/"file.txt").write_text(file_output)
        cases = ["usb-before-sync", "sync-before-usb", "disabled", "send-error"]
        if aliases:
            cases.append("same-batch")
        results = []
        for case in cases:
            argv = ([emulator] if emulator else []) + [str(binary), case]
            process = subprocess.run(argv, capture_output=True, timeout=10)
            (directory/(case+".stdout")).write_bytes(process.stdout)
            (directory/(case+".stderr")).write_bytes(process.stderr)
            results.append(dict(case=case, returncode=process.returncode,
                                stdout_sha256=sha(process.stdout), stderr_sha256=sha(process.stderr)))
        variants.append(dict(label=label, kernel=str(kernel.resolve()), extracted=pins,
                             command=cmd, file=file_output, cases=results,
                             binary_sha256=sha(binary.read_bytes())))
    result = dict(status="PASS_H0_BCM_ALIAS_PRODUCERS", device_actions=0,
                  fixture_sha256=sha(fixture.read_bytes()), variants=variants,
                  limits="Modeled cmd-db/RPMh; no physical sequence or applied electrical state proof")
    if not all(case["returncode"] == 0 for variant in variants for case in variant["cases"]):
        result["status"] = "FAIL_H0_BCM_ALIAS_PRODUCERS"
    assert variants[0]["extracted"]["functions"] == variants[1]["extracted"]["functions"], "producer functions changed"
    assert variants[0]["extracted"]["binding_sha256"] == variants[1]["extracted"]["binding_sha256"], "binding indices changed"
    (output/"result.json").write_text(json.dumps(result, indent=2)+"\n")
    assert result["status"].startswith("PASS"), "actual producer case failed; inspect retained stderr"
    return result


if __name__ == "__main__":
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--compiler", default="cc")
    parser.add_argument("--emulator")
    args = parser.parse_args()
    print(run(args.before, args.after, args.output, args.compiler, args.emulator)["status"])
