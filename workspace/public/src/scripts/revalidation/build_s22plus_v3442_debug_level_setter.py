#!/usr/bin/env python3
"""Build the host-only S22+ V3442 raw debug-level setter."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from build_s22plus_direct_p3_boot import repo_root, resolve, sha256_file


DEFAULT_SOURCE = Path(
    "workspace/public/src/native-init/s22plus_reboot_debug_level_v3442.S"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_native_init/v3442_debug_level_setter_v0_1"
)


def run(command: list[str | Path]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(part) for part in command],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def require_ok(result: subprocess.CompletedProcess[str], label: str) -> str:
    if result.returncode != 0:
        raise SystemExit(f"{label} failed rc={result.returncode}:\n{result.stdout}")
    return result.stdout


def compile_setter(source: Path, output: Path) -> dict[str, str]:
    require_ok(
        run(
            [
                "aarch64-linux-gnu-gcc",
                "-nostdlib",
                "-static",
                "-Wl,--build-id=none",
                "-Wl,-e,_start",
                "-Wl,-z,noexecstack",
                "-o",
                output,
                source,
            ]
        ),
        "compile V3442 setter",
    )
    require_ok(run(["aarch64-linux-gnu-strip", "-s", output]), "strip V3442 setter")
    file_text = require_ok(run(["file", output]), "file V3442 setter")
    readelf = require_ok(
        run(["aarch64-linux-gnu-readelf", "-h", "-l", output]),
        "readelf V3442 setter",
    )
    objdump = require_ok(
        run(["aarch64-linux-gnu-objdump", "-d", output]),
        "objdump V3442 setter",
    )
    if "INTERP" in readelf or "AArch64" not in readelf:
        raise SystemExit("V3442 setter ELF shape mismatch")
    if objdump.count("svc\t#0x0") != 3:
        raise SystemExit("V3442 setter must have reboot plus two exit svc sites")
    reboot_number = objdump.find("#0x8e")
    first_svc = objdump.find("svc\t#0x0")
    first_exit_number = objdump.find("#0x5d", first_svc)
    second_svc = objdump.find("svc\t#0x0", first_svc + 1)
    if not (0 <= reboot_number < first_svc < first_exit_number < second_svc):
        raise SystemExit("V3442 valid path reboot/exit syscall shape mismatch")
    first_svc_prefix = objdump[:first_svc]
    if any(token in first_svc_prefix for token in ("str\t", "stp\t", "bl\t")):
        raise SystemExit("V3442 valid path stores or calls before reboot syscall")
    binary = output.read_bytes()
    for required in (b"S22_V3442_RAW_DEBUG_LEVEL_SETTER", b"debug0x4948\0", b"debug0x494d\0"):
        if required not in binary:
            raise SystemExit(f"V3442 setter missing string: {required!r}")
    for forbidden in (b"/dev/", b"/sys/", b"/proc/", b"/data/", b"download"):
        if forbidden in binary:
            raise SystemExit(f"V3442 setter forbidden string: {forbidden!r}")
    return {"file": file_text.strip(), "readelf": readelf, "objdump": objdump}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    root = repo_root()
    source = resolve(root, args.source)
    out = resolve(root, args.out)
    if out.exists():
        if not args.force:
            raise SystemExit(f"output exists; pass --force: {out}")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    setter = out / "s22plus_v3442_debug_level_setter"
    audit = compile_setter(source, setter)
    manifest = {
        "schema": "s22plus_v3442_debug_level_setter_build_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "hashes": {"source": sha256_file(source), "setter": sha256_file(setter)},
        "safety": {
            "host_only_build": True,
            "live_authorized": False,
            "valid_arguments": ["high", "mid"],
            "high_reboot_arg": "debug0x4948",
            "mid_reboot_arg": "debug0x494d",
            "valid_path_first_syscall": "reboot",
            "filesystem_syscalls": False,
            "block_write": False,
            "flash": False,
            "panic": False,
            "rdx_protocol": False,
        },
        "audit": audit,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
