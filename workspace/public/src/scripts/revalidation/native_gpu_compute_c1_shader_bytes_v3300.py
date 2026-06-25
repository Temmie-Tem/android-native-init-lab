#!/usr/bin/env python3
"""Verify the A640 CS shader words for the C1 compute rung."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root


CYCLE = "V3300"
SCOPE = "gpu-compute-c1-shader-byte-materialization"
REPO_ROOT = repo_root()
STAGED_ROOT = Path("/tmp/a90-mesa-gpu-src")
KERNEL = STAGED_ROOT / "kern_invocationid.asm"
FULL_NIR_BUILD_ROOT = Path("/tmp/a90-mesa-c1-fullnir-softpipe-v3300")
PREFERRED_IR3_DISASM = FULL_NIR_BUILD_ROOT / "src/freedreno/isa/ir3-disasm"

EXPECTED_KERNEL_SHA256 = "1e0187f2917ab504602a22f30f475716ea8ec7f7123481d371cc87b908c1a97a"
EXPECTED_BINARY_SHA256 = "7142780e5a7332c4bffdf4e0defb78450003295a9932b356140636845087285a"
EXPECTED_IR3_DISASM_SHA256 = "5fdf9cba93165bad98e9d2fe1ee92bb7cd06ef88e286454379e4943331498fc1"

EXPECTED_LOCAL_SIZE = [32, 1, 1]
EXPECTED_NUM_BUFS = 1
EXPECTED_BUF_SIZES = [32]
EXPECTED_BUF_ADDR_REGS = [252]
EXPECTED_INSTRLEN = 1
EXPECTED_SIZE_DWORDS = 32
EXPECTED_SIZE_BYTES = 128
EXPECTED_MAX_REG = 0
EXPECTED_MAX_HALF_REG = -1
EXPECTED_CONSTLEN = 4
EXPECTED_MERGEDREGS = True

EXPECTED_DWORDS = [
    0x00000000,
    0x200CC001,
    0x00000000,
    0x00000500,
    0x01674000,
    0xC0260000,
    0x00000000,
    0x03000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
]

EXPECTED_DISASM_SNIPPETS = [
    "mov.u32u32 r0.y, r0.x",
    "(rpt5)nop",
    "stib.b.untyped.1d.u32.1.imm r0.x, r0.y, 0",
    "end",
]


def _sha256_path(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dwords_to_bytes(dwords: list[int]) -> bytes:
    out = bytearray()
    for dword in dwords:
        out.extend(dword.to_bytes(4, "little"))
    return bytes(out)


def _find_ir3_disasm() -> Path | None:
    candidates = [
        PREFERRED_IR3_DISASM,
        Path("/tmp/a90-mesa-h3-build-ir3/src/freedreno/isa/ir3-disasm"),
    ]
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def _run_ir3_disasm(binary: bytes, ir3_disasm: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="a90-c1-ir3-disasm-") as tmp:
        shader_path = Path(tmp) / "kern_invocationid_a640.bin"
        shader_path.write_bytes(binary)
        proc = subprocess.run(
            [str(ir3_disasm), "-g", "FD640", str(shader_path)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    return {
        "command": [str(ir3_disasm), "-g", "FD640", "<temp-shader-bin>"],
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "lines": [line for line in proc.stdout.splitlines() if line.strip()],
    }


def _kernel_source_contract(path: Path = KERNEL) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    return {
        "path": str(path),
        "sha256": _sha256_path(path),
        "has_localsize_32_1_1": "@localsize 32, 1, 1" in text,
        "has_one_32_word_uav": "@buf 32" in text,
        "has_invocationid_r0x": "@invocationid(r0.x)" in text,
        "has_wgid_r48x": "@wgid(r48.x)" in text,
        "has_numwg_c2x": "@numwg(c2.x)" in text,
        "moves_invocation_id_to_store_value": "mov.u32u32 r0.y, r0.x" in text,
        "stores_invocation_id_to_uav": "stib.b.untyped.1d.u32.1.imm r0.x, r0.y, 0" in text,
        "expected_readback": list(range(32)),
    }


def run_verification(*, require_disasm: bool = False) -> dict[str, Any]:
    shader_binary = _dwords_to_bytes(EXPECTED_DWORDS)
    ir3_disasm = _find_ir3_disasm()
    disasm: dict[str, Any] | None = None
    if ir3_disasm is not None:
        disasm = _run_ir3_disasm(shader_binary, ir3_disasm)

    disasm_stdout = disasm["stdout"] if disasm else ""
    checks = {
        "kernel_source_present": KERNEL.is_file(),
        "kernel_source_sha256_matches": _sha256_path(KERNEL) == EXPECTED_KERNEL_SHA256,
        "shader_dword_count_matches": len(EXPECTED_DWORDS) == EXPECTED_SIZE_DWORDS,
        "shader_byte_count_matches": len(shader_binary) == EXPECTED_SIZE_BYTES,
        "shader_binary_sha256_matches": _sha256_bytes(shader_binary) == EXPECTED_BINARY_SHA256,
        "ir3_disasm_available": ir3_disasm is not None,
        "ir3_disasm_sha256_matches": (
            _sha256_path(ir3_disasm) == EXPECTED_IR3_DISASM_SHA256 if ir3_disasm else False
        ),
        "ir3_disasm_returncode_zero": disasm["returncode"] == 0 if disasm else False,
        "ir3_disasm_contains_expected_ops": (
            all(snippet in disasm_stdout for snippet in EXPECTED_DISASM_SNIPPETS)
            if disasm
            else False
        ),
    }

    mandatory_checks = [
        "kernel_source_present",
        "kernel_source_sha256_matches",
        "shader_dword_count_matches",
        "shader_byte_count_matches",
        "shader_binary_sha256_matches",
    ]
    if require_disasm:
        mandatory_checks.extend(
            [
                "ir3_disasm_available",
                "ir3_disasm_returncode_zero",
                "ir3_disasm_contains_expected_ops",
            ]
        )

    passed = all(checks[name] for name in mandatory_checks)
    ready_for_c1_live = all(
        checks[name]
        for name in [
            "kernel_source_sha256_matches",
            "shader_binary_sha256_matches",
            "ir3_disasm_returncode_zero",
            "ir3_disasm_contains_expected_ops",
        ]
    )

    return {
        "cycle": CYCLE,
        "scope": SCOPE,
        "passed": passed,
        "ready_for_c1_live": ready_for_c1_live,
        "checks": checks,
        "kernel_contract": _kernel_source_contract(),
        "shader": {
            "gpu_name": "FD640",
            "gpu_id": 640,
            "local_size": EXPECTED_LOCAL_SIZE,
            "num_bufs": EXPECTED_NUM_BUFS,
            "buf_sizes": EXPECTED_BUF_SIZES,
            "buf_addr_regs": EXPECTED_BUF_ADDR_REGS,
            "instrlen": EXPECTED_INSTRLEN,
            "sizedwords": EXPECTED_SIZE_DWORDS,
            "size_bytes": EXPECTED_SIZE_BYTES,
            "max_reg": EXPECTED_MAX_REG,
            "max_half_reg": EXPECTED_MAX_HALF_REG,
            "constlen": EXPECTED_CONSTLEN,
            "mergedregs": EXPECTED_MERGEDREGS,
            "binary_sha256": _sha256_bytes(shader_binary),
            "dwords_hex": [f"0x{dword:08x}" for dword in EXPECTED_DWORDS],
        },
        "toolchain": {
            "full_nir_build_root": str(FULL_NIR_BUILD_ROOT),
            "ir3_disasm": str(ir3_disasm) if ir3_disasm else None,
            "ir3_disasm_sha256": _sha256_path(ir3_disasm) if ir3_disasm else None,
            "libnir_sha256": _sha256_path(FULL_NIR_BUILD_ROOT / "src/compiler/nir/libnir.a"),
            "libfreedreno_ir3_sha256": _sha256_path(
                FULL_NIR_BUILD_ROOT / "src/freedreno/ir3/libfreedreno_ir3.a"
            ),
            "full_nir_meson_summary": {
                "gallium_drivers": ["softpipe"],
                "tools": ["freedreno"],
                "gfx_compute": True,
                "opengl": True,
                "runtime_blob_or_opencl_path": False,
            },
        },
        "disasm": disasm,
        "expected_disasm_snippets": EXPECTED_DISASM_SNIPPETS,
        "next": [
            "embed these verified CS shader words in the native-init C1 compute dispatch source unit",
            "bind one 32-word UAV, dispatch one 32-lane workgroup, and verify buf[i] == i after WFI/readback",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON result")
    parser.add_argument(
        "--require-disasm",
        action="store_true",
        help="fail if the local FD640 ir3-disasm verification is unavailable or mismatched",
    )
    args = parser.parse_args()

    result = run_verification(require_disasm=args.require_disasm)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{CYCLE} {SCOPE} passed={int(result['passed'])}")
        print(f"ready_for_c1_live={int(result['ready_for_c1_live'])}")
        print(f"shader_binary_sha256={result['shader']['binary_sha256']}")
        print(f"ir3_disasm={result['toolchain']['ir3_disasm']}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
