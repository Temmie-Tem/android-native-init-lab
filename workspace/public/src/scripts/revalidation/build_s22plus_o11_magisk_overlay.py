#!/usr/bin/env python3
"""Build the S22+ O1.1 SELinux-domain-only Magisk overlay candidate.

Host-only. This wraps the proven O1 builder and requires the rc delta to be
exactly one `seclabel u:r:magisk:s0` service option. All runtime files and boot
preservation gates remain inherited from O1.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import build_s22plus_o1_magisk_overlay as o1


RUN_ID = "V3407"
VARIANT = "O1.1"
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/o11_magisk_overlay_v0_1")
DEFAULT_RC = Path("workspace/public/src/android/s22plus_o11_control.rc")
O1_RC = Path("workspace/public/src/android/s22plus_o1_control.rc")
SECLABEL_LINE = "    seclabel u:r:magisk:s0\n"
EXPECTED_SERVICE_SHA256 = "3e5c000308acaa52495c1b235b9f3e777123e3ddeb1e51f01b7461a38593be93"
EXPECTED_DAEMON_SHA256 = "a82cd32f83afc20d40fc74a9402896ae07378811f259913ed6df7cbc540f858c"
EXPECTED_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"


def require_single_seclabel_delta(o1_rc: Path, o11_rc: Path) -> dict[str, Any]:
    before = o1_rc.read_text(encoding="utf-8")
    after = o11_rc.read_text(encoding="utf-8")
    before_body = before[before.index("on property:") :].rstrip() + "\n"
    after_body = after[after.index("on property:") :].rstrip() + "\n"
    anchor = "    group root system shell\n"
    expected = before_body.replace(anchor, anchor + SECLABEL_LINE, 1)
    if after_body != expected:
        raise SystemExit("O1.1 rc must differ from O1 behavior only by the Magisk seclabel line")
    if after_body.count("seclabel ") != 1:
        raise SystemExit("O1.1 rc must contain exactly one seclabel option")
    return {
        "base_rc": o1.display_path(o1.repo_root(), o1_rc),
        "candidate_rc": o1.display_path(o1.repo_root(), o11_rc),
        "added_service_option": SECLABEL_LINE.strip(),
        "other_behavioral_delta": False,
    }


def validate_o11_manifest(manifest: dict[str, Any]) -> list[str]:
    reasons = o1.validate_manifest(manifest)
    hashes = manifest.get("hashes") or {}
    safety = manifest.get("safety") or {}
    delta = manifest.get("o11_delta") or {}
    if manifest.get("schema") != "s22plus_o11_magisk_overlay_build_v1":
        reasons.append("o11-schema-mismatch")
    if manifest.get("run_id") != RUN_ID or manifest.get("variant") != VARIANT:
        reasons.append("o11-identity-mismatch")
    if delta.get("added_service_option") != SECLABEL_LINE.strip():
        reasons.append("o11-seclabel-delta-mismatch")
    if delta.get("other_behavioral_delta") is not False:
        reasons.append("o11-extra-behavioral-delta")
    if safety.get("service_seclabel") != "u:r:magisk:s0":
        reasons.append("o11-service-seclabel-mismatch")
    if hashes.get("overlay_service") != EXPECTED_SERVICE_SHA256:
        reasons.append("o11-service-changed")
    if hashes.get("o0_daemon") != EXPECTED_DAEMON_SHA256:
        reasons.append("o11-daemon-changed")
    if hashes.get("kernel_before") != EXPECTED_KERNEL_SHA256 or hashes.get("kernel_after") != EXPECTED_KERNEL_SHA256:
        reasons.append("o11-kernel-changed")
    return reasons


def build(args: argparse.Namespace) -> dict[str, Any]:
    root = o1.repo_root()
    o1_rc = o1.resolve(root, args.o1_rc)
    o11_rc = o1.resolve(root, args.rc)
    delta = require_single_seclabel_delta(o1_rc, o11_rc)
    base_args = argparse.Namespace(
        out=args.out,
        base_boot=args.base_boot,
        magiskboot=args.magiskboot,
        magisk_apk=args.magisk_apk,
        odin=args.odin,
        rc=args.rc,
        service=args.service,
        cc=args.cc,
        force=args.force,
        no_odin_parse_gate=args.no_odin_parse_gate,
        quiet=True,
    )
    manifest = o1.build(base_args)
    manifest.update(
        {
            "schema": "s22plus_o11_magisk_overlay_build_v1",
            "run_id": RUN_ID,
            "variant": VARIANT,
            "purpose": "O1 service-domain transition while preserving stock-first-stage USB control",
            "o11_delta": delta,
        }
    )
    manifest["safety"]["service_seclabel"] = "u:r:magisk:s0"
    manifest["safety"]["selinux_policy_file_change"] = False
    manifest["runtime_contract"]["service_domain"] = "u:r:magisk:s0"
    reasons = validate_o11_manifest(manifest)
    if reasons:
        raise SystemExit(f"O1.1 manifest validation failed: {reasons}")
    out_dir = o1.resolve(root, args.out)
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-boot", type=Path, default=o1.DEFAULT_BASE_BOOT)
    parser.add_argument("--magiskboot", type=Path, default=o1.DEFAULT_MAGISKBOOT)
    parser.add_argument("--magisk-apk", type=Path, default=o1.DEFAULT_MAGISK_APK)
    parser.add_argument("--odin", type=Path, default=o1.DEFAULT_ODIN)
    parser.add_argument("--o1-rc", type=Path, default=O1_RC)
    parser.add_argument("--rc", type=Path, default=DEFAULT_RC)
    parser.add_argument("--service", type=Path, default=o1.DEFAULT_SERVICE)
    parser.add_argument("--cc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-odin-parse-gate", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    build(parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
