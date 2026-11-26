"""Build the compatible-list stock control from the retained stock-direct recipe."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / "build_control.py"
GUARD = HERE.parent / "mainline-handoff/guard.c"
TAG = "codex,y2q-stock-list-v1"


def checked(path, digest):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("changed build input: " + path.name)
    return raw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("packaged", type=Path)
    args = parser.parse_args()
    src = checked(BASE, "2ad5cc9ebfd5fdeecb74e0699c3c69f3096c18347c42a86486b4ee0371b462b5")
    spec = importlib.util.spec_from_file_location("_retained_stock_builder", BASE)
    base = importlib.util.module_from_spec(spec)
    exec(compile(src, str(BASE), "exec"), base.__dict__)
    old_tree = base.source_tree

    def list_tree(out):
        tree = old_tree(out)
        guard = tree / "guard.c"
        checked(guard, "769f07a969849b3c86c9679113dd650333c0cf493759f0bcdd43cc25d42d880d")
        guard.write_bytes(checked(GUARD, "131483342a5ec40a6378d16c6b1241f0cb3d319b281c78e43e373c8516ffe0fc"))
        header = tree / "stock-control-fdt.h"
        raw = checked(header, "a198510941265062d691980315ac03fb7a650a4a423f695685a124167e74b62b")
        old_tag = b"codex,y2q-stock-direct-v1"
        if raw.count(old_tag) != 1:
            raise ValueError("unexpected chosen property")
        header.write_bytes(raw.replace(old_tag, TAG.encode("ascii")))
        return tree

    base.source_tree = list_tree
    stage = base.build(args.candidate)
    tree = args.candidate / "control-src"
    stage.update(guard=base.digest((tree / "guard.c").read_bytes()), property=TAG,
                 fdt_header=base.digest((tree / "stock-control-fdt.h").read_bytes()))
    (args.candidate / "stage.json").write_text(json.dumps(stage, indent=2) + "\n")
    base.package(args.candidate, args.packaged)


if __name__ == "__main__":
    main()
