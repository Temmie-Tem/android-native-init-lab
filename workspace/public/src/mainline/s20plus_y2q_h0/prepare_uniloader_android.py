#!/usr/bin/env python3
"""Package a qualified S20+ loader control and audit original boot recovery."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

from build_uniloader_android import HERE, ROOT, require, split_boot
from uniloader_android_observation import MARKER_PATH, READ_SCRIPT, marker_digest

sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
import s20plus_g986n_boot_only_f1_transport_v1 as transport
import s20plus_g986n_boot_only_odin_prep as prep
import s20plus_g986n_twrp_f1_engine_v2 as retained

PRIVATE = ROOT / "workspace/private"
LOADER_SOURCES = frozenset({
    "build_uniloader_android.py", "uniloader_entry.S", "uniloader_guard.c",
    "uniloader_fdt.c", "uniloader_prefix.lds", "uniloader_layout.h",
})


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def audit_ap(path, ap_pin, decoded_pin, scratch, label):
    with transport.pin_boot_only_ap(path, label=label, expected_size=ap_pin["size"],
                                   expected_sha256=ap_pin["sha256"]) as pinned:
        member = transport.read_boot_only_member(pinned, label=label, maximum=prep.BOOT_SIZE)
        transport.revalidate_pinned_path(pinned)
        receipt = pinned.receipt()
    frame = scratch / "member.lz4"
    decoded = scratch / "decoded.img"
    with frame.open("xb") as stream:
        stream.write(member)
    prep.run_lz4([str(prep.LZ4), "-d", "-q", str(frame), str(decoded)])
    prep.require_file(decoded, decoded_pin["size"], decoded_pin["sha256"], label + " decoded boot")
    return {
        "ap": receipt, "only_member": {"name": "boot.img.lz4", "size": len(member),
                                      "sha256": sha256(member)},
        "decoded_boot": decoded_pin,
    }


def load_qualification(artifact_root):
    build = artifact_root / "control-3"
    raw = (build / "result.json").read_bytes()
    verification = json.loads((artifact_root / "verification.json").read_bytes())
    build_result = json.loads(raw)
    require(verification["status"] == "H0_Y2Q_UNILOADER_ANDROID_HANDOFF_VERIFIED"
            and verification["build_result_sha256"] == sha256(raw)
            and verification["boot_sha256"] == build_result["boot"]["sha256"]
            and verification["vm_positive"] == 6 and verification["vm_rejections"] == 4
            and verification["physical_android_boot"] is False
            and build_result["status"] == "H0_Y2Q_UNILOADER_ANDROID_BOOT_BUILT"
            and build_result["target"] == retained.TARGET
            and build_result["payload_offset"] == 0x200000
            and build_result["boot"]["size"] == prep.BOOT_SIZE, "qualification differs")
    vm_receipt = (artifact_root / "vm-release/result.json").read_bytes()
    require(sha256(vm_receipt) == verification["vm_result_sha256"], "VM evidence differs")
    source_pins = build_result["inputs"]["sources"]
    require(set(source_pins) == LOADER_SOURCES, "loader source membership differs")
    for name, pin in source_pins.items():
        prep.require_file(HERE / name, pin["size"], pin["sha256"], name)
    boot = build / "boot.img"
    prep.require_file(boot, prep.BOOT_SIZE, build_result["boot"]["sha256"], "qualified boot")
    raw_boot = boot.read_bytes()
    require(sha256(raw_boot) == build_result["boot"]["sha256"], "boot changed while reading")
    _, image, _, _ = split_boot(raw_boot)
    marker = build_result["marker"]
    digest = marker_digest(marker)
    require(sha256(image) == build_result["image"]["sha256"]
            and image[:build_result["payload_offset"]].count(marker.encode("ascii") + b"\0") == 1,
            "marker is not uniquely embedded in the qualified loader")
    return boot, build_result["boot"], digest, sha256(raw)


def prepare(artifact_root, output):
    artifact_root, output = artifact_root.resolve(strict=True), output.resolve()
    require(all(path.is_relative_to(PRIVATE) and path != PRIVATE
                for path in (artifact_root, output)), "private artifact paths required")
    prep.require_file(prep.LZ4, prep.LZ4_SIZE, prep.LZ4_SHA256, "pinned LZ4")
    boot, candidate_pin, digest, qualification = load_qualification(artifact_root)
    original_pin = {"size": retained.ROLLBACK_BOOT_SIZE, "sha256": retained.ROLLBACK_BOOT_SHA256}
    rollback_pin = {"size": retained.ROLLBACK_AP_SIZE, "sha256": retained.ROLLBACK_AP_SHA256}

    output.mkdir(mode=0o700, parents=True)
    with tempfile.TemporaryDirectory(dir=output) as scratch_name:
        scratch = Path(scratch_name)
        rollback = audit_ap(retained.ROLLBACK_AP, rollback_pin, original_pin,
                            scratch, "resident Magisk rollback")
        require(rollback["only_member"]["size"] == retained.ROLLBACK_MEMBER_SIZE
                and rollback["only_member"]["sha256"] == retained.ROLLBACK_MEMBER_SHA256,
                "resident Magisk rollback member differs")
    ap = output / "candidate.AP.tar.md5"
    with tempfile.TemporaryDirectory(dir=output) as scratch_name:
        scratch = Path(scratch_name)
        lz4 = scratch / "candidate.lz4"
        prep.lz4_roundtrip(boot, lz4, scratch / "roundtrip.img")
        written = prep.write_boot_ap(lz4, ap)
        ap.chmod(0o400)
        candidate = audit_ap(ap, written, candidate_pin, scratch, "UniLoader candidate")
        require(candidate["only_member"]["sha256"] == prep.sha256_file(lz4),
                "candidate archive member differs from its checked frame")
    receipt = {
        "status": "H0_S20PLUS_UNILOADER_ARTIFACT_PAIR_VERIFIED",
        "target": retained.TARGET,
        "build_result_sha256": qualification,
        "candidate": candidate,
        "rollback": rollback,
        "marker": {"path": MARKER_PATH, "sha256_with_nul": digest,
                   "read_script_sha256": sha256(READ_SCRIPT.encode("ascii"))},
        "live_prepared": False,
        "device_commands": 0,
    }
    with (output / "artifact-pair.json").open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(prepare(args.artifact_root, args.output)["status"])
