"""Build a fresh mainline early-pair Image with the stock-tested y2q FDT guard."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
PRIVATE = ROOT / "workspace/private"
HISTORY = "e6dcf2a313c5e36429cac9f009141c240a6e30e9"
BASE = HERE / "mainline-handoff"
GUARD_SHA = "131483342a5ec40a6378d16c6b1241f0cb3d319b281c78e43e373c8516ffe0fc"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    exp = parser.parse_args().output
    if exp.resolve() != exp or not exp.is_relative_to(PRIVATE) or exp == PRIVATE:
        raise ValueError("new absolute private output required")
    exp.mkdir(mode=0o700)
    source = exp / "source"
    source.mkdir(mode=0o700)
    tree = f"{HISTORY}:{BASE.relative_to(ROOT)}"
    for name in subprocess.check_output(["git", "-C", ROOT, "ls-tree", "--name-only", tree], text=True).splitlines():
        if Path(name).name != name:
            raise ValueError("unexpected source entry")
        raw = subprocess.check_output(["git", "-C", ROOT, "show", tree + "/" + name])
        if name == "guard.c":
            if hashlib.sha256(raw).hexdigest() != "769f07a969849b3c86c9679113dd650333c0cf493759f0bcdd43cc25d42d880d":
                raise ValueError("unexpected original guard")
            raw = (BASE / name).read_bytes()
            if hashlib.sha256(raw).hexdigest() != GUARD_SHA:
                raise ValueError("wrong compatible-list guard")
        (source / name).write_bytes(raw)
    view = ["/usr/bin/bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc",
            "--unshare-net", "--tmpfs", "/tmp", "--bind", exp, exp, "--ro-bind", source, BASE,
            "--chdir", ROOT, "--", sys.executable, "-B"]
    cand = exp / "candidate"
    for label, args in (("build", [BASE / "build_stage.py", cand, "--early-pair"]),
                        ("package", [BASE / "package_stage.py", cand, exp / "packaged"])):
        with (exp / (label + ".log")).open("xb") as log:
            subprocess.run([*view, *args], stdout=log, stderr=subprocess.STDOUT, check=True)
    stage = json.loads((cand / "stage.json").read_bytes())
    if stage["kind"] != "HOST_ONLY_Y2Q_EARLY_PAIR" or set(stage["stages"]) != {"prebranch", "primary_entry"}:
        raise ValueError("expected two early markers")
    print(json.loads((exp / "packaged/pair.json").read_bytes())["archives"]["candidate"]["ap"]["sha256"])


if __name__ == "__main__":
    main()
