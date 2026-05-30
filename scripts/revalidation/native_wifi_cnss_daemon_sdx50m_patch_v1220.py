#!/usr/bin/env python3
"""V1220: host-only private cnss-daemon SDXPRAIRIE->SDX50M patch candidate.

This script never touches the device and never modifies the vendor export in
place.  It copies `cnss-daemon` to a private evidence directory and changes only
the runtime selection literal used after `get_system_info()`:

    SDXPRAIRIE\\0 -> SDX50M\\0RIE\\0

The trailing bytes remain in the file, but the C string observed by
`strcmp()` becomes `SDX50M`.  This aligns cnss-daemon's second type-0 vote with
the real eSoC name that libmdmdetect supports, instead of faking sysfs
`esoc_name` and getting filtered out before the type-0 output entry is filled.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_json


DEFAULT_INPUT = Path("tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon")
DEFAULT_OUT_DIR = Path("tmp/wifi/v1220-cnss-daemon-sdx50m-patch")
LATEST_POINTER = Path("tmp/wifi/latest-v1220-cnss-daemon-sdx50m-patch.txt")

ORIGINAL_LITERAL = b"SDXPRAIRIE\x00"
PATCH_LITERAL = b"SDX50M\x00"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def byte_deltas(before: bytes, after: bytes) -> list[dict[str, Any]]:
    return [
        {
            "offset": index,
            "offset_hex": hex(index),
            "before": before[index],
            "after": after[index],
        }
        for index, (left, right) in enumerate(zip(before, after))
        if left != right
    ]


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    input_path = args.input
    source = input_path.read_bytes()
    occurrences = [index for index in range(len(source)) if source.startswith(ORIGINAL_LITERAL, index)]
    patched = bytearray(source)

    decision = "v1220-input-not-patched"
    passed = False
    reason = ""
    next_step = "fix host input before live planning"
    patch_offset = -1

    if len(occurrences) != 1:
        reason = f"expected exactly one SDXPRAIRIE literal, found {len(occurrences)}"
    elif len(PATCH_LITERAL) > len(ORIGINAL_LITERAL):
        reason = "patch literal is longer than original literal"
    else:
        patch_offset = occurrences[0]
        patched[patch_offset:patch_offset + len(PATCH_LITERAL)] = PATCH_LITERAL
        output_path = store.run_dir / "artifacts/cnss-daemon.sdx50m"
        output_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        output_path.write_bytes(patched)
        os.chmod(output_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

        deltas = byte_deltas(source, bytes(patched))
        patched_literal_window = bytes(patched[patch_offset:patch_offset + len(ORIGINAL_LITERAL)])
        if len(source) == len(patched) and len(deltas) == 4 and patched_literal_window.startswith(PATCH_LITERAL):
            decision = "v1220-private-cnss-daemon-sdx50m-patch-ready"
            passed = True
            reason = (
                f"single literal patched at {hex(patch_offset)}; size unchanged; "
                f"delta_count={len(deltas)}"
            )
            next_step = (
                "V1221: add helper live gate to bind/execute private patched cnss-daemon; "
                "no vendor partition write and no Wi-Fi HAL/scan/connect"
            )
        else:
            decision = "v1220-private-cnss-daemon-patch-review"
            reason = (
                f"patch produced unexpected size/delta/window: size_before={len(source)} "
                f"size_after={len(patched)} delta_count={len(deltas)} "
                f"window={patched_literal_window!r}"
            )
            next_step = "review byte-level patch before any live helper work"

    output_rel = "artifacts/cnss-daemon.sdx50m"
    output_abs = store.run_dir / output_rel
    deltas = byte_deltas(source, bytes(patched))
    manifest = {
        "cycle": "v1220",
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "input": str(input_path),
        "input_exists": input_path.exists(),
        "input_size": len(source),
        "input_sha256": sha256_bytes(source),
        "output": str(output_abs) if output_abs.exists() else "",
        "output_size": output_abs.stat().st_size if output_abs.exists() else 0,
        "output_mode": oct(stat.S_IMODE(output_abs.stat().st_mode)) if output_abs.exists() else "",
        "output_sha256": sha256_bytes(output_abs.read_bytes()) if output_abs.exists() else "",
        "original_literal": ORIGINAL_LITERAL.decode("ascii", errors="replace"),
        "patch_literal_c_string": "SDX50M",
        "occurrence_count": len(occurrences),
        "patch_offset": patch_offset,
        "patch_offset_hex": hex(patch_offset) if patch_offset >= 0 else "",
        "delta_count": len(deltas),
        "deltas": deltas,
        "host_only": True,
        "device_command_executed": False,
        "tracefs_write_executed": False,
        "cnss_daemon_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
    }
    return manifest


def write_summary(store: EvidenceStore, manifest: dict[str, Any]) -> None:
    lines = [
        "# V1220 cnss-daemon SDX50M Patch Candidate",
        "",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- input: `{manifest['input']}`",
        f"- input_sha256: `{manifest['input_sha256']}`",
        f"- output: `{manifest['output']}`",
        f"- output_sha256: `{manifest['output_sha256']}`",
        f"- patch_offset: `{manifest['patch_offset_hex']}`",
        f"- delta_count: `{manifest['delta_count']}`",
        f"- next: {manifest['next_step']}",
        "",
        "## Safety",
        "",
        "- Host-only; no device command.",
        "- No vendor partition write.",
        "- No daemon, HAL, scan/connect, credentials, DHCP/routes, or external ping.",
    ]
    store.write_text("summary.md", "\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input.exists():
        raise SystemExit(f"input not found: {args.input}")

    store = EvidenceStore(args.out_dir)
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    write_summary(store, manifest)
    try:
        LATEST_POINTER.parent.mkdir(parents=True, exist_ok=True)
        LATEST_POINTER.write_text(str(store.run_dir))
    except OSError:
        pass

    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"next:     {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
