"""Build the list-aware y2q C-stage candidate with a generic serial interface."""
import argparse
import hashlib
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent / "mainline-handoff"
BUILDER = HERE / "build_stage.py"
BUILDER_SHA = "39073ecfc682b5ea2b33809fb15ada5f649864dedab9f1a666ab27fd0a92ff4c"
ACM_SHA = "af4cc45460315e7f35b5f9a5914b3a17b9d021726c103447d29a6eb787bbf02e"


def select_serial(source):
    driver = source / "drivers/usb/gadget/function/f_acm.c"
    raw = driver.read_bytes()
    assignment = b"opts->protocol = USB_CDC_ACM_PROTO_AT_V25TER;"
    if hashlib.sha256(raw).hexdigest() != ACM_SHA or raw.count(assignment) != 1:
        raise ValueError("unexpected Linux 6.18 f_acm source")
    driver.write_bytes(raw.replace(assignment, b"opts->protocol = USB_CDC_PROTO_NONE;"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    # Use the same reviewed extraction, stage instrumentation and build. The
    # source transformation is confined to the new private extraction tree.
    raw = BUILDER.read_bytes()
    site = b'    objects = output / "kernel-build"'
    if hashlib.sha256(raw).hexdigest() != BUILDER_SHA or raw.count(site) != 1:
        raise ValueError("unexpected stage builder")
    sys.path.insert(0, str(HERE))
    module = {"__name__": "_cstage_build", "__file__": str(BUILDER), "select_serial": select_serial}
    exec(compile(raw.replace(site, b"    select_serial(source)\n" + site), str(BUILDER), "exec"), module)
    module["build_stage"](args.output)


if __name__ == "__main__":
    main()
