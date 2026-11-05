"""Run the exact ML028 RSC slot-selection function against a controlled H0 queue."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from cold_phy_tables import PRIVATE, digest, require

SRC = PRIVATE / "outputs/s22plus-mainline-ml028-rc-ssh-cycle-h0-20261105-1/prepare-1/kernel-source/drivers/soc/qcom"
RSC_SHA = "6ddd654c5804d8c47cef1f30e1a6a25d98868f4c7d33a77ee239107857b6b87b"
RPMH_SHA = "83d958d6754d40efbed720f6bfc6c1218f28bd0c5ece39b8961226bbca04202c"


def exercise(output):
    require(output.resolve().is_relative_to(PRIVATE.resolve()), "private evidence required")
    source = SRC / "rpmh-rsc.c"
    require(digest(source) == RSC_SHA and digest(SRC / "rpmh.c") == RPMH_SHA, "RPMh source differs")
    text = source.read_text()
    pos = text.index("\nint rpmh_rsc_send_data(") + 1
    end = text.index("\n}\n", pos) + 3
    output.mkdir(mode=0o700)
    body = output / "retained-send.inc"
    body.write_text(text[pos:end])
    fixture = Path(__file__).with_name("rpmh_wait_fixture.c")
    exe = output / "wait-test"
    subprocess.run(["cc", "-O2", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                    "-Wno-unused-parameter", "-pthread", "-I", output, fixture, "-o", exe], check=True)
    results = {}
    for case in ("free", "busy"):
        raw = subprocess.check_output([exe, case], timeout=25)
        (output/(case+".raw")).write_bytes(raw)
        row = json.loads(raw)
        require(row["trigger_ns"] >= row["entry_ns"] and
                (row["trigger_ns"] >= row["deadline_ns"]) == (case == "busy"),
                "unexpected TCS submission timing")
        results[case] = row
    result = dict(status="REPRODUCED_H0_POST_DEADLINE_TCS_TRIGGER",
                  rsc_sha256=RSC_SHA, rpmh_sha256=RPMH_SHA, body_sha256=digest(body),
                  fixture_sha256=digest(fixture), cases=results, device_actions=0)
    (output/"result.json").write_text(json.dumps(result, indent=2)+"\n")
    return result


if __name__ == "__main__":
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(exercise(parser.parse_args().output)["status"])
